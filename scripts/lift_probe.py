#!/usr/bin/env -S uv run --script
"""Score whether shipped x86-64 il2cpp code can be lifted to rebuildable arm64.

Draws a size-stratified sample of function bodies from the shipped Linux GameAssembly.so
(bounded by its .eh_frame records, since the game code carries no symbols), dumps their raw
pcode and jump tables through headless Ghidra, lifts each body to LLVM IR with
scripts/pcode_lift.py, and records a pass/fail per stage: fully decoded, lifted with no
holes, accepted by the LLVM verifier, compiled to an arm64 object. A radare2 leg scores its
function extents and whether its decompiler output compiles. Every body the run asked for is
accounted for: a body the dump never emitted, or one whose lift or LLVM tool crashed, is
recorded with its address rather than dropped from the totals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pcode_lift  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SO = REPO / ".tools/megabonk-linux-native/Megabonk/GameAssembly.so"
DEFAULT_OUT = REPO / ".tools/lift-probe"
LLVM = Path(os.environ.get("LLVM_BIN", "/opt/homebrew/opt/llvm/bin"))
DUMP_SCRIPT_DIR = Path(__file__).resolve().parent / "lift_probe"
SECTION_LINE = re.compile(
    r"\[\s*\d+\]\s+(\S+)\s+\S+\s+([0-9a-f]+)\s+[0-9a-f]+\s+([0-9a-f]+)\s+[0-9a-f]+\s+([A-Za-z]*)\s+\d+\s+\d+\s+\d+"
)

FDE_LINE = re.compile(r"\sFDE\s.*pc=([0-9a-fA-F]+)\.\.\.([0-9a-fA-F]+)")
TINY_MAX, SMALL_MAX = 63, 512
TOOL_TIMEOUT = 120
# Extra opt/llc arguments from --extra, set once by main() and appended to every scoring tool call.
EXTRA_ARGS: list[str] = []
# PcodeCache the run reads and extends, or None to always ask Ghidra for every body.
PCODE_CACHE: PcodeCache | None = None
GHIDRA_TIMEOUT = 3600
MISSING_DUMP = "no pcode row from Ghidra"
CACHE_SCHEMA = "pcode-cache/2"


@dataclass(frozen=True)
class Fde:
    start: int
    size: int


def parse_fdes(text: str) -> list[Fde]:
    """Reads function ranges from `llvm-dwarfdump --eh-frame` output."""
    fdes = []
    for line in text.splitlines():
        m = FDE_LINE.search(line)
        if m:
            start, end = int(m.group(1), 16), int(m.group(2), 16)
            fdes.append(Fde(start, end - start))
    return fdes


def size_class(size: int) -> str:
    if size <= TINY_MAX:
        return "tiny"
    return "small" if size <= SMALL_MAX else "large"


def stratified_sample(fdes: list[Fde], per_class: int, seed: int, lo: int = 0, hi: int = 1 << 64) -> list[Fde]:
    """Picks up to `per_class` bodies from each size class inside [lo, hi), reproducibly."""
    rng = random.Random(seed)
    by_class: dict[str, list[Fde]] = {"tiny": [], "small": [], "large": []}
    for fde in fdes:
        if lo <= fde.start < hi:
            by_class[size_class(fde.size)].append(fde)
    picked = []
    for name in ("tiny", "small", "large"):
        pool = sorted(by_class[name], key=lambda f: f.start)
        picked.extend(rng.sample(pool, min(per_class, len(pool))))
    return picked


def summarize(results: list[dict]) -> dict[str, dict[str, int]]:
    """Counts bodies and per-stage passes for each size class and overall."""
    summary: dict[str, dict[str, int]] = {}
    for result in results:
        for key in (size_class(result["size"]), "all"):
            row = summary.setdefault(key, {"n": 0})
            row["n"] += 1
            for stage, ok in result["stages"].items():
                row[stage] = row.get(stage, 0) + int(ok)
    return summary


def tally_holes(results: list[dict]) -> dict[str, int]:
    """Counts the bodies each kind of hole occurs in."""
    counts: Counter[str] = Counter()
    for result in results:
        counts.update(set(result["holes"]))
    return dict(counts)


def tally_tables(results: list[dict]) -> dict[str, int]:
    """Counts bodies whose switch was lowered over decoded table bytes rather than Ghidra's case list."""
    bodies = tables = 0
    for result in results:
        audited = result.get("tables_audited", 0)
        bodies += int(audited > 0)
        tables += audited
    return {"bodies": bodies, "tables": tables}


def tally_atomics(results: list[dict]) -> dict[str, int]:
    """Counts bodies carrying a lowered `lock` region and the locked sites rewritten as atomics."""
    bodies = sites = 0
    for result in results:
        atomics = result.get("atomics", 0)
        bodies += int(atomics > 0)
        sites += atomics
    return {"bodies": bodies, "sites": sites}


def tally_branchind(results: list[dict]) -> dict:
    """Counts BRANCHIND sites by the stack-balance verdict: proven, or unproven grouped by reason.

    `untracked_rsp` is the subset the pass could not read a frame delta for at all, which is the
    class that keeps an indirect jump from ever being recognised as a tail call.
    """
    tally: dict = {"proven": 0, "unproven": 0, "untracked_rsp": 0}
    reasons: Counter[str] = Counter()
    for result in results:
        tally["proven"] += result.get("proven_tail_calls", 0)
        for site in result.get("unproven_branchind", []):
            tally["unproven"] += 1
            reasons[site["reason"]] += 1
            if site["rsp_delta"] is None:
                tally["untracked_rsp"] += 1
    tally["unproven_reasons"] = dict(reasons)
    return tally


def failed_row(start: int, size: int, error: str, missing_dump: bool = False) -> dict:
    """A body the pipeline could not score, recorded so it still counts in the totals."""
    return {
        "start": start,
        "size": size,
        "holes": [],
        "unmapped_refs": 0,
        "indirect_calls": 0,
        "tail_calls": 0,
        "proven_tail_calls": 0,
        "unproven_branchind": [],
        "atomics": 0,
        "jump_tables": 0,
        "obj_bytes": 0,
        "error": error,
        "missing_dump": missing_dump,
        "stages": {"decoded": False, "clean": False, "verify": False, "pipeline": False, "arm64": False, "arm64_pipeline": False},
    }


def reconcile(fdes: list[Fde], rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Pairs the requested sample with the dumped rows so no body can vanish from the totals.

    Returns one row per sampled body in sample order, and the rows that matched none of them.
    """
    by_start: dict[int, list[dict]] = {}
    for row in rows:
        by_start.setdefault(row["start"], []).append(row)
    aligned, extras = [], []
    for fde in fdes:
        matches = by_start.pop(fde.start, [])
        if matches:
            aligned.append(matches[0])
            extras.extend(matches[1:])
        else:
            aligned.append(failed_row(fde.start, fde.size, MISSING_DUMP, missing_dump=True))
    for duplicates in by_start.values():
        extras.extend(duplicates)
    return aligned, extras


def tally_failures(results: list[dict]) -> dict[str, int]:
    """Counts the bodies the pipeline could not score, grouped by what stopped them."""
    return dict(Counter(row["error"] for row in results if row.get("error")))


def failure_rows(results: list[dict]) -> list[dict]:
    """Every body the pipeline could not score, with its address so it can be examined again."""
    return [
        {
            "start": row["start"],
            "hex": hex(row["start"]),
            "size": row["size"],
            "class": size_class(row["size"]),
            "error": row["error"],
        }
        for row in results
        if row.get("error")
    ]


def parse_exec_sections(text: str) -> dict[str, tuple[int, int]]:
    """Reads executable section ranges from `llvm-readelf -S` output."""
    sections = {}
    for line in text.splitlines():
        m = SECTION_LINE.search(line)
        if m and "X" in m.group(4):
            start = int(m.group(2), 16)
            sections[m.group(1)] = (start, start + int(m.group(3), 16))
    return sections


def run_tool(cmd: list, timeout: float | None = None, input=None, check: bool = False, **kw) -> subprocess.CompletedProcess:
    """Run a tool in its own process group so a timeout kills its descendants, not only the launcher."""
    argv = [str(c) for c in cmd]
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE if input is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        **kw,
    )
    try:
        out, err = proc.communicate(input, timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = proc.communicate()
        raise subprocess.TimeoutExpired(argv, timeout, output=out, stderr=err) from None
    result = subprocess.CompletedProcess(argv, proc.returncode, out, err)
    if check:
        result.check_returncode()
    return result


def as_text(value) -> str:
    """Reads a subprocess stream as text whether the run finished or timed out."""
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value


def find_ghidra() -> Path:
    override = os.environ.get("GHIDRA_HEADLESS")
    if override:
        return Path(override)
    found = sorted(Path("/opt/homebrew/Cellar/ghidra").glob("*/libexec/support/analyzeHeadless"))
    if not found:
        raise SystemExit("analyzeHeadless not found; install Ghidra or set GHIDRA_HEADLESS")
    return found[-1]


def ghidra_env() -> dict[str, str]:
    env = {**os.environ, "GHIDRA_HEADLESS_MAXMEM": os.environ.get("GHIDRA_HEADLESS_MAXMEM", "6G")}
    if "JAVA_HOME" not in env:
        mise = Path.home() / ".local/bin/mise"
        env["JAVA_HOME"] = run_tool([mise, "where", "java"], text=True).stdout.strip()
    return env


def dump_pcode(
    so: Path, fdes: list[Fde], work: Path, timeout: int | None = None, diag: Path | None = None
) -> tuple[list[dict], list[dict]]:
    """Returns the sampled bodies' pcode records and the ELF's loaded sections.

    A Ghidra run that dies partway leaves a short pcode file: the rows it wrote are kept and
    `reconcile` records the bodies it never reached, so the run names them instead of losing them.
    A run that times out or exits nonzero leaves its console output under `diag`.
    """
    ranges, pcode, sections = work / "ranges.txt", work / "pcode.jsonl", work / "sections.json"
    ranges.write_text("".join(f"{f.start:x} {f.size}\n" for f in fdes))
    project = work / "ghidra"
    project.mkdir()
    note, timed_out = "", False
    try:
        proc = run_tool(
            [
                find_ghidra(),
                project,
                "probe",
                "-import",
                so,
                "-noanalysis",
                "-scriptPath",
                DUMP_SCRIPT_DIR,
                "-postScript",
                "LiftDump.java",
                ranges,
                pcode,
                sections,
            ],
            env=ghidra_env(),
            text=True,
            timeout=timeout,
        )
        note = "" if proc.returncode == 0 else f"Ghidra exited {proc.returncode}\n"
        stdout = note + proc.stdout + as_text(proc.stderr)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        tail = as_text(exc.stdout) + as_text(exc.stderr)
        stdout = f"Ghidra timed out after {exc.timeout}s\n{tail[-1500:]}"
    if diag is not None and (note or timed_out):
        diag.mkdir(parents=True, exist_ok=True)
        (diag / "ghidra-stdout.txt").write_text(stdout)
    if not pcode.exists():
        raise SystemExit(f"Ghidra produced no pcode:\n{stdout[-1500:]}")
    if not sections.exists():
        raise SystemExit(f"Ghidra produced pcode but no section table:\n{stdout[-1500:]}")
    try:
        rows = []
        with pcode.open() as stream:
            for line in stream:
                if not line.endswith("\n") and (timed_out or note):
                    break
                rows.append(json.loads(line))
        sections_table = json.loads(sections.read_text())
    except ValueError as exc:
        raise SystemExit(f"Ghidra wrote pcode that is not valid JSON ({exc}):\n{stdout[-1500:]}") from exc
    return rows, sections_table


def score_tool(name: str, cmd: list, ir: str, timeout: int) -> tuple[bool, int, str | None]:
    """Return acceptance, raw output byte count, and any diagnostic."""
    accepted, payload, error = run_tool_body(name, cmd, ir, timeout)
    return accepted, 0 if payload is None else len(payload), error


def run_tool_body(name: str, cmd: list, ir: str, timeout: int) -> tuple[bool, bytes | None, str | None]:
    """Run LLVM on stdin, retaining binary stdout and rejection diagnostics."""
    argv = [*cmd, "-"]
    try:
        proc = run_tool(argv, input=ir.encode(), timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, None, f"{name} timed out after {timeout}s"
    except OSError as exc:
        return False, None, f"{name} could not run: {exc}"
    if proc.returncode == 0:
        return True, _as_bytes(proc.stdout), None
    if proc.returncode < 0:
        return False, None, f"{name} was killed by signal {-proc.returncode}"
    if proc.returncode > 1:
        return False, None, f"{name} exited {proc.returncode}"
    detail = _as_bytes(proc.stderr).decode(errors="replace").strip()
    return False, None, f"{name} rejected IR: {detail}" if detail else None


def _as_bytes(value) -> bytes:
    """Reads a subprocess stream as bytes whether the run finished or timed out."""
    if value is None:
        return b""
    return value.encode() if isinstance(value, str) else bytes(value)


def ghidra_version() -> str:
    """The Ghidra build whose analysis produced the cache, so another build recomputes."""
    try:
        props = find_ghidra().parent.parent / "Ghidra" / "application.properties"
        for line in props.read_text().splitlines():
            if line.startswith("application.version="):
                return line.split("=", 1)[1].strip()
    except (OSError, ValueError):
        pass
    return "unknown"


def dump_script_fingerprint() -> str:
    """Digest over the dump script's bytes, so an edited LiftDump.java invalidates the cache."""
    digest = hashlib.sha256()
    try:
        for script in sorted(DUMP_SCRIPT_DIR.glob("*.java")):
            digest.update(script.name.encode())
            digest.update(script.read_bytes())
    except OSError:
        return "unknown"
    return digest.hexdigest()[:16]


def cache_key(digest: str, fdes: list[Fde]) -> str:
    """Identify an exact sample; Ghidra recovery depends on the whole analysis."""
    stamp = hashlib.sha256()
    stamp.update(digest.encode())
    for fde in fdes:
        stamp.update(f"{fde.start:x}:{fde.size}\n".encode())
    return stamp.hexdigest()[:24]


def section_record(digest: str, sections: list[dict], key: str | None = None) -> dict:
    """Bind the companion ELF section table to the same analysis as the bodies."""
    record = {"sha256": digest, "kind": "sections", "sections": sections}
    if key is not None:
        record["cache"] = key
    return record


def cache_header(key: str, digest: str, fingerprint: str, ghidra: str) -> dict:
    """The record that says which toolchain produced a cache under this key."""
    return {
        "kind": "header",
        "cache": key,
        "sha256": digest,
        "schema": CACHE_SCHEMA,
        "script_fingerprint": fingerprint,
        "ghidra": ghidra,
    }


def _valid_body(record: dict) -> bool:
    """Schema check for one pcode record: a malformed row is a miss, never a silent hit."""
    if not isinstance(record.get("start"), int) or not isinstance(record.get("size"), int):
        return False
    if not isinstance(record.get("insns"), list):
        return False
    for key in ("undecoded", "sw", "dc"):
        if key in record and not isinstance(record[key], (int, bool)):
            return False
    for key in ("uw", "jt"):
        if key in record and not isinstance(record[key], list):
            return False
    return True


class PcodeCache:
    """Persist one exact Ghidra analysis, never a mixture of partial samples."""

    def __init__(self, path: Path | None, digest: str, by_start: dict[int, dict], key: str | None):
        self.path, self.digest, self.by_start, self.key = path, digest, by_start, key
        self.matched: list[int] = []
        self.missing: list[int] = []
        self.fresh: list[dict] = []
        self.sections: list[dict] | None = None
        self.header: dict | None = None
        self.rejected = 0

    @classmethod
    def load(
        cls,
        path: Path | None,
        digest: str,
        want_key: str | None = None,
        want_fingerprint: str | None = None,
        want_ghidra: str | None = None,
    ) -> PcodeCache:
        cache = cls(path, digest, {}, want_key)
        if path is None or not path.exists():
            return cache
        try:
            lines = path.read_text().splitlines()
        except OSError:
            return cache
        for line in lines:
            try:
                record = json.loads(line)
            except ValueError:
                cache.rejected += 1
                continue
            if not isinstance(record, dict) or record.get("sha256") != digest:
                continue
            kind = record.get("kind")
            if want_key is not None and record.get("cache") != want_key:
                continue
            if kind == "header":
                if cache.header is None:
                    cache.header = record
                continue
            if kind == "sections":
                if cache.sections is None and isinstance(record.get("sections"), list):
                    cache.sections = record["sections"]
                continue
            if _valid_body(record):
                cache.by_start.setdefault(record["start"], record)
            else:
                cache.rejected += 1
        if not cache._header_matches(want_fingerprint, want_ghidra):
            cache.by_start, cache.sections, cache.rejected = {}, None, cache.rejected + 1
        return cache

    def _header_matches(self, want_fingerprint: str | None, want_ghidra: str | None) -> bool:
        if self.header is None:
            return False
        if self.header.get("schema") != CACHE_SCHEMA:
            return False
        if want_fingerprint is not None and self.header.get("script_fingerprint") != want_fingerprint:
            return False
        if want_ghidra is not None and self.header.get("ghidra") != want_ghidra:
            return False
        return True

    @property
    def complete(self) -> bool:
        """A hit needs bodies and the section table; a partial cache is never a complete hit."""
        return bool(self.by_start) and bool(self.sections) and not self.rejected

    def lookup(self, fdes: list[Fde]) -> list[dict]:
        """Returns the cached records for these bodies, recording the addresses it could not answer."""
        usable = (
            self.complete
            and len(self.by_start) == len(fdes)
            and all(self.by_start.get(f.start, {}).get("size") == f.size for f in fdes)
        )
        if not usable:
            self.by_start = {}
        rows = []
        for fde in fdes:
            record = self.by_start.get(fde.start) if usable else None
            if record is None:
                self.missing.append(fde.start)
            else:
                self.matched.append(fde.start)
                rows.append({key: value for key, value in record.items() if key not in ("sha256", "cache", "kind")})
        return rows

    def remember(self, rows: list[dict], sections: list[dict] | None = None) -> None:
        """Keep fresh rows for scoring and persistence."""
        if sections is not None:
            self.sections = sections
        for row in rows:
            start = row.get("start")
            if start in self.missing and start not in self.by_start and _valid_body(row):
                self.by_start[start] = row
        self.fresh += [row for row in rows if row.get("start") in self.missing]

    def save(self) -> None:
        if self.path is None or self.key is None or not self.missing:
            return
        records = [cache_header(self.key, self.digest, dump_script_fingerprint(), ghidra_version())]
        if self.sections is not None:
            records.append(section_record(self.digest, self.sections, self.key))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        records += [{"cache": self.key, "sha256": self.digest, **row} for row in self.by_start.values()]
        with tempfile.NamedTemporaryFile(mode="w", dir=self.path.parent, delete=False) as sink:
            temporary = Path(sink.name)
            try:
                for record in records:
                    sink.write(json.dumps(record) + "\n")
                sink.close()
                temporary.replace(self.path)
            finally:
                temporary.unlink(missing_ok=True)

    def summary(self) -> dict:
        return {
            "hits": len(self.matched),
            "misses": len(self.missing),
            "rejected_records": self.rejected,
            "sections": len(self.sections) if self.sections is not None else None,
            "key": self.key,
        }


def dump_pcode_cached(
    so: Path,
    fdes: list[Fde],
    work: Path,
    cache: PcodeCache | None,
    timeout: int | None = None,
    diag: Path | None = None,
    dump=None,
) -> tuple[list[dict], list[dict]]:
    """Reuse a complete analysis or dump the entire exact sample in one invocation."""
    dump = dump or globals()["dump_pcode"]
    if cache is None:
        return dump(so, fdes, work, timeout=timeout, diag=diag)
    rows = cache.lookup(fdes)
    sections = list(cache.sections) if cache.sections is not None else []
    if cache.missing:
        dumped, dumped_sections = dump(so, fdes, work, timeout=timeout, diag=diag)
        sections = list(dumped_sections)
        cache.remember(dumped, dumped_sections)
    if not sections and rows:
        raise SystemExit("pcode cache carried bodies but no ELF section table; refusing to score against no sections")
    return rows + cache.fresh, sections


def llc_arm64(ir: str, tool_timeout: int) -> tuple[bool, int, str | None]:
    """Assembles a body's IR into an arm64 object, returning its size."""
    return score_tool(
        "llc",
        [LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", "-"] + EXTRA_ARGS,
        ir,
        tool_timeout,
    )


def verify_body(ir: str, tool_timeout: int) -> tuple[bool, str | None]:
    accepted, _, error = score_tool("opt", [LLVM / "opt", "-passes=verify", "-disable-output"] + EXTRA_ARGS, ir, tool_timeout)
    return accepted, error


def optimise_body(ir: str, pipeline: str, tool_timeout: int) -> tuple[bool, bytes | None, str | None]:
    return run_tool_body("opt", [LLVM / "opt", f"-passes={pipeline}", "-S", "-o", "-"] + EXTRA_ARGS, ir, tool_timeout)


def score_body(fn: dict, sections: list[dict], tool_timeout: int = TOOL_TIMEOUT, pipeline: str = "", evidence=None) -> dict:
    """Record each stage; rejected pipelines never compile fallback unoptimized IR."""
    try:
        lifted = pcode_lift.lift_body(fn, sections, evidence=evidence)
        ir = pcode_lift.module_for([lifted])
    except Exception as exc:
        return failed_row(fn["start"], fn["size"], f"lift raised {type(exc).__name__}: {exc}")
    verified, error = verify_body(ir, tool_timeout)
    ran_pipeline = False
    if pipeline:
        passed, optimised, pipeline_error = optimise_body(ir, pipeline, tool_timeout)
        if not passed or optimised is None:
            return {
                **failed_row(fn["start"], fn["size"], pipeline_error or f"opt rejected the pipeline {pipeline}"),
                "pipeline": pipeline,
                "holes": lifted.holes,
                "unmapped_refs": lifted.unmapped_refs,
                "indirect_calls": lifted.indirect_calls,
                "tail_calls": lifted.tail_calls,
                "proven_tail_calls": lifted.proven_tail_calls,
                "unproven_branchind": lifted.unproven_branchind,
                "atomics": lifted.atomics,
                "jump_tables": len(fn.get("jt", [])),
                "stages": {
                    "decoded": fn["undecoded"] == 0,
                    "clean": not lifted.holes,
                    "verify": verified,
                    "pipeline": False,
                    "arm64": False,
                    "arm64_pipeline": False,
                },
            }
        ir = optimised.decode(errors="replace")
        ran_pipeline = True
        after, post_error = verify_body(ir, tool_timeout)
        verified = verified and after
        if not after:
            return {
                **failed_row(fn["start"], fn["size"], post_error or f"{pipeline} produced IR that fails verify"),
                "pipeline": pipeline,
                "holes": lifted.holes,
                "unmapped_refs": lifted.unmapped_refs,
                "indirect_calls": lifted.indirect_calls,
                "tail_calls": lifted.tail_calls,
                "proven_tail_calls": lifted.proven_tail_calls,
                "unproven_branchind": lifted.unproven_branchind,
                "atomics": lifted.atomics,
                "jump_tables": len(fn.get("jt", [])),
                "stages": {
                    "decoded": fn["undecoded"] == 0,
                    "clean": not lifted.holes,
                    "verify": verified,
                    "pipeline": True,
                    "arm64": False,
                    "arm64_pipeline": False,
                },
            }
        accepted, obj_bytes, obj_error = llc_arm64(ir, tool_timeout)
        error = error or obj_error
    else:
        accepted, obj_bytes, obj_error = llc_arm64(ir, tool_timeout)
        error = error or obj_error
    return {
        "start": fn["start"],
        "size": fn["size"],
        "holes": lifted.holes,
        "unmapped_refs": lifted.unmapped_refs,
        "indirect_calls": lifted.indirect_calls,
        "tail_calls": lifted.tail_calls,
        "proven_tail_calls": lifted.proven_tail_calls,
        "unproven_branchind": lifted.unproven_branchind,
        "atomics": lifted.atomics,
        "jump_tables": len(fn.get("jt", [])),
        "tables_audited": lifted.tables_audited,
        "obj_bytes": obj_bytes,
        "error": error,
        "pipeline": pipeline or None,
        "stages": {
            "decoded": fn["undecoded"] == 0,
            "clean": not lifted.holes,
            "verify": verified,
            "pipeline": ran_pipeline,
            "arm64": accepted,
            "arm64_pipeline": accepted and ran_pipeline,
        },
    }


def score_row(row: dict, sections: list[dict], tool_timeout: int, pipeline: str = "", evidence=None) -> dict:
    """Scores one reconciled row, turning anything that escapes the scorer into a recorded failure."""
    if row.get("error"):
        return row
    try:
        return score_body(row, sections, tool_timeout, pipeline, evidence)
    except Exception as exc:
        return failed_row(row["start"], row["size"], f"scoring raised {type(exc).__name__}: {exc}")


def r2_leg(so: Path, fdes: list[Fde], work: Path) -> list[dict]:
    """Scores radare2's function extents against the frame records and whether its pdc output compiles as C."""
    base = ["r2", "-q", "-e", "bin.relocs.apply=true", "-e", "scr.color=0"]
    rows = []
    for fde in fdes:
        at = f"s 0x{fde.start:x}; af"
        info = run_tool([*base, "-c", f"{at}; afij", so], text=True).stdout
        sizes = json.loads(info[info.index("[") :])[0]["size"] if "[" in info else None
        pseudo = run_tool([*base, "-c", f"{at}; pdc", so], text=True).stdout
        source = work / f"r2_{fde.start:x}.c"
        source.write_text(pseudo)
        compiled = run_tool([LLVM / "clang", "-fsyntax-only", "-x", "c", source]).returncode == 0
        rows.append({"start": fde.start, "size": fde.size, "r2_size": sizes, "pdc_compiles": compiled})
    return rows


def r2_summary(rows: list[dict]) -> dict:
    return {
        "n": len(rows),
        "extent_matches_frame": sum(r["r2_size"] == r["size"] for r in rows),
        "pdc_compiles": sum(r["pdc_compiles"] for r in rows),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    started_at = time.monotonic()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("so", nargs="?", type=Path, default=DEFAULT_SO)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--per-class", type=int, default=300)
    ap.add_argument("--seed", type=int, default=80)
    ap.add_argument("--section", default="il2cpp", help="executable section the sample is drawn from")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--tool-timeout", type=int, default=TOOL_TIMEOUT, help="seconds an opt or llc run may take per body")
    ap.add_argument("--ghidra-timeout", type=int, default=GHIDRA_TIMEOUT, help="seconds the whole pcode dump may take")
    ap.add_argument("--r2-per-class", type=int, default=10, help="bodies per class for the radare2 leg; 0 skips it")
    ap.add_argument(
        "--extra",
        default="",
        help="arguments appended to every opt and llc call, e.g. --extra '--mcpu=neoverse-n1'",
    )
    ap.add_argument(
        "--pipeline",
        default="",
        help="opt pass pipeline run on each body before llc, e.g. --pipeline 'default<O2>'; empty is today's verify-only behaviour",
    )
    ap.add_argument(
        "--pcode-cache",
        type=Path,
        default=None,
        help="JSONL of Ghidra pcode records keyed on the binary digest, reused across pipeline runs",
    )
    args = ap.parse_args(argv)
    global PCODE_CACHE
    EXTRA_ARGS[:] = shlex.split(args.extra)

    if not args.so.exists():
        raise SystemExit(f"no ELF at {args.so}")
    digest = sha256(args.so)
    readelf = run_tool([LLVM / "llvm-readelf", "-S", args.so], text=True).stdout
    window = parse_exec_sections(readelf)[args.section]
    frames = parse_fdes(run_tool([LLVM / "llvm-dwarfdump", "--eh-frame", args.so], text=True).stdout)
    in_section = [f for f in frames if window[0] <= f.start < window[1]]
    sample = stratified_sample(frames, args.per_class, args.seed, *window)
    args.out.mkdir(parents=True, exist_ok=True)
    # The cache unit is the whole exact sample: same ordered addresses, sizes, dump script and Ghidra build.
    want_key = cache_key(digest, sample)
    PCODE_CACHE = PcodeCache.load(args.pcode_cache, digest, want_key, dump_script_fingerprint(), ghidra_version())
    cache = PCODE_CACHE
    wanted_cache = cache if cache.path is not None else None

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        pcode_at = time.monotonic()
        bodies, sections = dump_pcode_cached(args.so, sample, work, wanted_cache, timeout=args.ghidra_timeout, diag=args.out)
        pcode_seconds = round(time.monotonic() - pcode_at, 1)
        rows, extras = reconcile(sample, bodies)
        scored: list[dict] = []
        scored_at = time.monotonic()
        with ThreadPoolExecutor(args.jobs) as pool, (args.out / "bodies.jsonl").open("w") as sink:
            pending = [pool.submit(score_row, row, sections, args.tool_timeout, args.pipeline) for row in rows]
            for future in as_completed(pending):
                row = future.result()
                scored.append(row)
                sink.write(json.dumps(row) + "\n")
                sink.flush()
        scoring_seconds = round(time.monotonic() - scored_at, 1)
        scored.sort(key=lambda row: row["start"])
        (args.out / "bodies.jsonl").write_text("".join(json.dumps(row) + "\n" for row in scored))
        if wanted_cache is not None:
            (args.out / "pcode.jsonl").write_text("".join(json.dumps(row) + "\n" for row in bodies))
            wanted_cache.save()
        r2 = None
        if args.r2_per_class:
            r2_sample = stratified_sample(frames, args.r2_per_class, args.seed, *window)
            r2 = r2_summary(r2_leg(args.so, r2_sample, work))

    scored_ok = [row for row in scored if not row.get("error")]
    failures = failure_rows(scored)
    dropped = [row for row in failures if row["error"] == MISSING_DUMP]
    x86_bytes = sum(row["size"] for row in scored_ok)
    obj_ratio = round(sum(row["obj_bytes"] for row in scored_ok) / x86_bytes, 2) if x86_bytes else 0
    summary = {
        "binary_sha256": digest,
        "section": args.section,
        "pipeline": args.pipeline or "none",
        "section_bodies": {name: sum(size_class(f.size) == name for f in in_section) for name in ("tiny", "small", "large")},
        "sample": {"per_class": args.per_class, "seed": args.seed, "requested": len(sample), "n": len(scored)},
        "stages": summarize(scored),
        "holes": tally_holes(scored),
        "branchind": tally_branchind(scored),
        "failures": tally_failures(scored),
        "failed_bodies": failures,
        "unsampled_rows": [hex(row["start"]) for row in extras],
        "obj_bytes_per_x86_byte": obj_ratio,
        "object_bytes": sum(row["obj_bytes"] for row in scored_ok),
        "x86_bytes": sum(fde.size for fde in sample),
        "compiled_x86_bytes": x86_bytes,
        "scoring_seconds": scoring_seconds,
        "pcode_seconds": pcode_seconds,
        "wall_seconds": round(time.monotonic() - started_at, 1),
        "pcode_cache": wanted_cache.summary() if wanted_cache is not None else None,
        "unmapped_refs": sum(row["unmapped_refs"] for row in scored),
        "atomics": tally_atomics(scored),
        "bodies_with_tail_calls": sum(bool(row["tail_calls"]) for row in scored),
        "bodies_with_indirect_calls": sum(bool(row["indirect_calls"]) for row in scored),
        "r2": r2,
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if failures:
        print(f"{len(failures)} of {len(scored)} sampled bodies could not be scored:", file=sys.stderr)
        for row in failures[:20]:
            print(f"  {row['hex']} {row['size']} B {row['class']}: {row['error']}", file=sys.stderr)
    if extras:
        print(f"{len(extras)} dumped rows matched no sampled body: {', '.join(summary['unsampled_rows'][:20])}", file=sys.stderr)
    if dropped:
        print(f"{len(dropped)} sampled bodies never reached the scorer: the census is incomplete", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
