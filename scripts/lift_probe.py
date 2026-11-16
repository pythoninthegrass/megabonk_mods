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
import subprocess
import sys
import tempfile
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
GHIDRA_TIMEOUT = 3600
MISSING_DUMP = "no pcode row from Ghidra"


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


def failed_row(start: int, size: int, error: str, missing_dump: bool = False) -> dict:
    """A body the pipeline could not score, recorded so it still counts in the totals."""
    return {
        "start": start,
        "size": size,
        "holes": [],
        "unmapped_refs": 0,
        "indirect_calls": 0,
        "tail_calls": 0,
        "jump_tables": 0,
        "obj_bytes": 0,
        "error": error,
        "missing_dump": missing_dump,
        "stages": {"decoded": False, "clean": False, "verify": False, "arm64": False},
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


def run_tool(cmd: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, **kw)


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


def dump_pcode(so: Path, fdes: list[Fde], work: Path, timeout: int | None = None, diag: Path | None = None) -> tuple[list[dict], list[dict]]:
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
    return [json.loads(line) for line in pcode.read_text().splitlines()], json.loads(sections.read_text())


def score_tool(name: str, cmd: list, ir: str, timeout: int) -> tuple[bool, int, str | None]:
    """Runs one LLVM tool over a body's IR: whether it accepted the body, its object size, and any run failure.

    A tool that rejects the IR (exit 1) is a measurement; a hang or a crash is a failure and is named.
    """
    try:
        proc = run_tool(cmd, input=ir.encode(), timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, 0, f"{name} timed out after {timeout}s"
    except OSError as exc:
        return False, 0, f"{name} could not run: {exc}"
    if proc.returncode == 0:
        return True, len(proc.stdout), None
    if proc.returncode < 0:
        return False, 0, f"{name} was killed by signal {-proc.returncode}"
    if proc.returncode > 1:
        return False, 0, f"{name} exited {proc.returncode}"
    return False, 0, None


def score_body(fn: dict, sections: list[dict], tool_timeout: int = TOOL_TIMEOUT) -> dict:
    """Lifts one body and records each stage's outcome; anything that breaks is recorded against the body."""
    try:
        lifted = pcode_lift.lift_body(fn, sections)
        ir = pcode_lift.module_for([lifted])
    except Exception as exc:
        return failed_row(fn["start"], fn["size"], f"lift raised {type(exc).__name__}: {exc}")
    verified, _, verify_error = score_tool(
        "opt", [LLVM / "opt", "-passes=verify", "-disable-output", "-"] + EXTRA_ARGS, ir, tool_timeout
    )
    accepted, obj_bytes, obj_error = score_tool(
        "llc",
        [LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", "-", "-"] + EXTRA_ARGS,
        ir,
        tool_timeout,
    )
    return {
        "start": fn["start"],
        "size": fn["size"],
        "holes": lifted.holes,
        "unmapped_refs": lifted.unmapped_refs,
        "indirect_calls": lifted.indirect_calls,
        "tail_calls": lifted.tail_calls,
        "jump_tables": len(fn.get("jt", [])),
        "obj_bytes": obj_bytes,
        "error": verify_error or obj_error,
        "stages": {
            "decoded": fn["undecoded"] == 0,
            "clean": not lifted.holes,
            "verify": verified,
            "arm64": accepted,
        },
    }


def score_row(row: dict, sections: list[dict], tool_timeout: int) -> dict:
    """Scores one reconciled row, turning anything that escapes the scorer into a recorded failure."""
    if row.get("error"):
        return row
    try:
        return score_body(row, sections, tool_timeout)
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
    args = ap.parse_args(argv)
    EXTRA_ARGS[:] = shlex.split(args.extra)

    if not args.so.exists():
        raise SystemExit(f"no ELF at {args.so}")
    readelf = run_tool([LLVM / "llvm-readelf", "-S", args.so], text=True).stdout
    window = parse_exec_sections(readelf)[args.section]
    frames = parse_fdes(run_tool([LLVM / "llvm-dwarfdump", "--eh-frame", args.so], text=True).stdout)
    in_section = [f for f in frames if window[0] <= f.start < window[1]]
    sample = stratified_sample(frames, args.per_class, args.seed, *window)
    args.out.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        bodies, sections = dump_pcode(args.so, sample, work, timeout=args.ghidra_timeout, diag=args.out)
        rows, extras = reconcile(sample, bodies)
        scored: list[dict] = []
        with ThreadPoolExecutor(args.jobs) as pool, (args.out / "bodies.jsonl").open("w") as sink:
            pending = [pool.submit(score_row, row, sections, args.tool_timeout) for row in rows]
            for future in as_completed(pending):
                row = future.result()
                scored.append(row)
                sink.write(json.dumps(row) + "\n")
                sink.flush()
        scored.sort(key=lambda row: row["start"])
        (args.out / "bodies.jsonl").write_text("".join(json.dumps(row) + "\n" for row in scored))
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
        "binary_sha256": sha256(args.so),
        "section": args.section,
        "section_bodies": {name: sum(size_class(f.size) == name for f in in_section) for name in ("tiny", "small", "large")},
        "sample": {"per_class": args.per_class, "seed": args.seed, "requested": len(sample), "n": len(scored)},
        "stages": summarize(scored),
        "holes": tally_holes(scored),
        "failures": tally_failures(scored),
        "failed_bodies": failures,
        "unsampled_rows": [hex(row["start"]) for row in extras],
        "obj_bytes_per_x86_byte": obj_ratio,
        "unmapped_refs": sum(row["unmapped_refs"] for row in scored),
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
