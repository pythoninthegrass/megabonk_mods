#!/usr/bin/env -S uv run --script
"""Account for every byte of the shipped image's executable sections.

A complete lift starts from knowing what the image holds: the `.eh_frame` bodies, the bytes between
them (alignment padding, zero fill, or code no frame record covers) and the frame-less stub sections.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from lift_probe import Fde
from pathlib import Path

NOP_PREFIXES = {0x66, 0x2E}
SINGLE_BYTE_PADDING = {0x90, 0xCC}


def _nop_length(gap: bytes, i: int) -> int:
    """Length of the nop instruction at `i`, or 0 when the bytes there are not a nop."""
    if gap[i] in SINGLE_BYTE_PADDING:
        return 1
    j = i
    while j < len(gap) and gap[j] in NOP_PREFIXES:
        j += 1
    if j < len(gap) and gap[j] == 0x90:
        return j - i + 1
    if j + 2 < len(gap) and gap[j] == 0x0F and gap[j + 1] == 0x1F:
        modrm = gap[j + 2]
        mod, rm = modrm >> 6, modrm & 7
        if mod == 3:
            return 0
        length = j - i + 3
        if rm == 4:
            length += 1
        length += {0: 4 if rm == 5 else 0, 1: 1, 2: 4}[mod]
        sib_base_disp = 4 if rm == 4 and mod == 0 and j + 3 < len(gap) and gap[j + 3] & 7 == 5 else 0
        length += sib_base_disp
        return length if i + length <= len(gap) else 0
    return 0


def classify_gap(gap: bytes) -> str:
    """`padding` when the gap decodes to nops only, `zero_fill` when all zero, else `other`."""
    if gap and not any(gap):
        return "zero_fill"
    i = 0
    while i < len(gap):
        n = _nop_length(gap, i)
        if n == 0:
            return "other"
        i += n
    return "padding"


def gaps(fdes: list[Fde], start: int, end: int) -> list[tuple[int, int]]:
    """Byte ranges of [start, end) that no body covers, as (address, size)."""
    out = []
    pos = start
    for fde in sorted(fdes, key=lambda f: f.start):
        if fde.start >= end:
            break
        if fde.start > pos:
            out.append((pos, fde.start - pos))
        pos = max(pos, min(fde.start + fde.size, end))
    if pos < end:
        out.append((pos, end - pos))
    return out


def account_section(name: str, start: int, end: int, data: bytes, fdes: list[Fde], stubs: bool) -> dict:
    """Every byte of one executable section: body, padding, zero fill, stub or unaccounted."""
    inside = [f for f in fdes if start <= f.start < end]
    gap_list = gaps(inside, start, end)
    acct = {
        "name": name,
        "start": start,
        "size": end - start,
        "bodies": len(inside),
        "body_bytes": sum(min(f.start + f.size, end) - f.start for f in inside),
        "gap_bytes": {"padding": 0, "zero_fill": 0, "other": 0},
        "stub_bytes": 0,
        "unaccounted": [],
    }
    for addr, size in gap_list:
        if stubs:
            acct["stub_bytes"] += size
            continue
        kind = classify_gap(data[addr - start : addr - start + size])
        acct["gap_bytes"][kind] += size
        if kind == "other":
            acct["unaccounted"].append({"start": addr, "size": size})
    return acct


def coverage_complete(sections: dict[str, dict]) -> bool:
    return not any(acct["unaccounted"] for acct in sections.values())


# Frame-less functions of the pinned image, named from its disassembly; the CRT range is four functions.
PINNED_SHA256 = "a86fd434619dafb328ec741b6bc285992ee1f52e69533b2db8f35185c2ed5ba1"
UNFRAMED = {
    PINNED_SHA256: [
        {"name": "_init", "start": 0x1D35000, "size": 0x24},
        {"name": "_fini", "start": 0x1D35024, "size": 0x0E},
        {"name": "deregister_tm_clones", "start": 0x1D35040, "size": 0x22},
        {"name": "register_tm_clones", "start": 0x1D35062, "size": 0x39},
        {"name": "__do_global_dtors_aux", "start": 0x1D3509B, "size": 0x6F},
        {"name": "frame_dummy", "start": 0x1D3510A, "size": 0x05},
        {"name": "ctor_array_walker", "start": 0x216295F, "size": 0x22},
    ]
}


def resolve_unframed(unaccounted: list[dict], table: list[dict], base: int, data: bytes) -> list[Fde]:
    """Bodies for the frame-less ranges; raises when a range has no entry or leaves code uncovered."""
    out = []
    for rng in unaccounted:
        start, end = rng["start"], rng["start"] + rng["size"]
        entries = sorted((e for e in table if start <= e["start"] < end), key=lambda e: e["start"])
        if not entries:
            raise ValueError(f"no recorded function for unaccounted range {start:#x}")
        for lo, size in gaps([Fde(e["start"], e["size"]) for e in entries], start, end):
            if classify_gap(data[lo - base : lo - base + size]) != "padding":
                raise ValueError(f"code at {lo:#x} is covered by no recorded function")
        out.extend(Fde(e["start"], e["size"]) for e in entries)
    return out


def build_inventory(ranges: dict, data: bytes, frames: list[Fde], unframed_table: list[dict]) -> tuple[dict, list[Fde]]:
    body_ranges = [bounds for name, bounds in ranges.items() if name != ".plt"]
    for f in frames:
        if not any(lo <= f.start < f.start + f.size <= hi for lo, hi in body_ranges):
            raise ValueError(f"frame {f.start:#x} is outside an executable body section")
    sections, unframed = {}, []
    for name, (lo, hi) in ranges.items():
        stub = name == ".plt"
        acct = account_section(name, lo, hi, data[lo:hi], frames, stub)
        extra = resolve_unframed(acct["unaccounted"], unframed_table, 0, data)
        if extra:
            acct = account_section(name, lo, hi, data[lo:hi], frames + extra, stub)
            unframed.extend(extra)
        if stub:
            acct["excluded"] = [{"start": lo, "size": hi - lo, "reason": "lazy-binding import stubs"}]
        sections[name] = acct
    return sections, unframed


def shards(bodies: list[Fde], size: int) -> list[list[Fde]]:
    return [bodies[i : i + size] for i in range(0, len(bodies), size)]


def body_shards(records: list[Fde], size: int) -> list[list[Fde]]:
    """Drop empty FDEs without shifting the cache boundaries of later shards."""
    return [[f for f in part if f.size != 0] for part in shards(records, size)]


def shard_identity(sha: str, fingerprint: str, ghidra: str, bodies: list[Fde], pipeline: str) -> str:
    stamp = hashlib.sha256()
    for part in (sha, fingerprint, ghidra, pipeline):
        stamp.update(part.encode() + b"\0")
    for b in bodies:
        stamp.update(f"{b.start:x}:{b.size}\n".encode())
    return stamp.hexdigest()


def write_shard(path: Path, identity: str, rows: list[dict]) -> None:
    lines = [json.dumps({"identity": identity, "count": len(rows)})] + [json.dumps(r) for r in rows]
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n")
    tmp.replace(path)


def matches_bodies(rows: list[dict], bodies: list[Fde]) -> bool:
    actual = {
        (r.get("start"), r.get("size"))
        for r in rows
        if isinstance(r, dict) and type(r.get("start")) is int and type(r.get("size")) is int
    }
    return len(actual) == len(rows) == len(bodies) and actual == {(b.start, b.size) for b in bodies}


def read_shard(path: Path, identity: str, bodies: list[Fde] | None = None, *, pcode: bool = False) -> list[dict] | None:
    """Return rows only when the identity, count and requested body inventory match."""
    try:
        lines = path.read_text().splitlines()
        header = json.loads(lines[0])
        rows = [json.loads(line) for line in lines[1:]]
    except (OSError, ValueError, IndexError):
        return None
    if not isinstance(header, dict) or header.get("identity") != identity or header.get("count") != len(rows):
        return None
    if pcode and (
        not rows
        or not isinstance(rows[0], dict)
        or rows[0].get("kind") != "sections"
        or not isinstance(rows[0].get("sections"), list)
    ):
        return None
    if bodies is not None and not matches_bodies(rows[1:] if pcode else rows, bodies):
        return None
    return rows


def build_verdict(rows: list[dict], coverage: bool) -> dict:
    """Runnable only when the image is fully accounted and every body decoded, lifted, verified and compiled."""
    stages = ("decoded", "clean", "verify", "arm64")
    blocking = sorted(r["start"] for r in rows if r.get("error") or not all(r["stages"][k] for k in stages))
    return {"runnable": coverage and bool(rows) and not blocking, "coverage_complete": coverage, "blocking": blocking}


def dump_bisecting(part, dump, failure, timeout, retry_base=300, retry_per_body=2):
    """Dump `part`, halving on failure so one bad body costs its neighbors little.

    Returns the pcode rows, the section table, and {start: message} for bodies that fail alone.
    """
    rows, sections = [], []
    try:
        rows, sections = dump(part, timeout)
        sizes = {f.start: f.size for f in part}
        counts = Counter(r["start"] for r in rows)
        rows = [r for r in rows if counts[r["start"]] == 1 and sizes.get(r["start"]) == r["size"]]
        done = {r["start"] for r in rows}
        remaining = [f for f in part if f.start not in done]
        if not remaining:
            return rows, sections, {}
        reason = "Ghidra did not return a unique row for the requested range"
    except failure as exc:
        reason = str(exc)
        remaining = part
    if len(part) == 1:
        return [], sections, {part[0].start: reason}
    mid = max(1, len(remaining) // 2)
    failed = {}
    for half in (remaining[:mid], remaining[mid:]):
        if not half:
            continue
        sub_rows, sub_sections, sub_failed = dump_bisecting(
            half, dump, failure, retry_base + retry_per_body * len(half), retry_base, retry_per_body
        )
        rows += sub_rows
        sections = sections or sub_sections
        failed |= sub_failed
    return rows, sections, failed


def scored_shard_identity(
    sha: str, fingerprint: str, ghidra: str, bodies: list[Fde], pipeline: str, tool_timeout: int, scorer: str
) -> str:
    """Identity of scored rows: the dump's identity plus everything `score_row` reads beyond the pcode.

    The pcode shard survives a lifter edit; scores must not, or a whole-image verdict can be assembled from
    rows an older lifter wrote. The tool timeout is part of it too, because a clang or llc timeout is a hole.
    """
    return shard_identity(sha, fingerprint, ghidra, bodies, json.dumps([pipeline, tool_timeout, scorer]))


def build_shard(index: int, part: list[Fde], ctx: dict) -> list[dict]:
    """Scored rows for one shard, reusing its pcode and scores when their identities still match."""
    import lift_probe as lp
    import tempfile

    out, sha = ctx["out"], ctx["sha"]
    pcode_id = shard_identity(sha, ctx["fingerprint"], ctx["ghidra"], part, "")
    scored_id = scored_shard_identity(
        sha,
        ctx["fingerprint"],
        ctx["ghidra"],
        part,
        ctx["pipeline"],
        ctx["tool_timeout"],
        ctx.get("scorer") or scoring_fingerprint(),
    )
    scored = read_shard(out / f"scored-{index:04d}.jsonl", scored_id, part)
    retry = ctx.get("retry_missing_dump", False)
    if scored is not None and not (retry and any(r.get("missing_dump") for r in scored)):
        return scored
    cached = read_shard(out / f"pcode-{index:04d}.jsonl", pcode_id, part, pcode=True)
    sections, bodies = (cached[0]["sections"], cached[1:]) if cached else ([], [])
    if retry:
        bodies = [r for r in bodies if not r.get("missing_dump")]
    present = {r["start"] for r in bodies}
    missing = [f for f in part if f.start not in present]
    if missing:
        print(f"shard {index}: dumping {len(missing)} bodies", flush=True)

        class DumpFailed(Exception):
            pass

        def dump(sub, timeout):
            with tempfile.TemporaryDirectory() as tmp:
                try:
                    rows, sections = lp.dump_pcode(ctx["so"], sub, Path(tmp), timeout=timeout, diag=out / f"diag-{index:04d}")
                except SystemExit as exc:
                    raise DumpFailed(f"Ghidra dump failed: {str(exc).splitlines()[0]}") from exc
            return rows, sections

        dumped, dump_sections, failed = dump_bisecting(missing, dump, DumpFailed, ctx["ghidra_timeout"])
        sections = sections or dump_sections
        bodies += dumped
        bodies += [lp.failed_row(f.start, f.size, failed[f.start], missing_dump=True) for f in missing if f.start in failed]
        write_shard(out / f"pcode-{index:04d}.jsonl", pcode_id, [{"kind": "sections", "sections": sections}, *bodies])
    rows, _extras = lp.reconcile(part, bodies)
    previous = {r["start"]: r for r in (scored or []) if not r.get("missing_dump")}

    def score(row):
        if row["start"] in previous:
            return previous[row["start"]]
        return lp.score_row(row, sections, ctx["tool_timeout"], ctx["pipeline"], table_evidence(ctx))

    with lp.ThreadPoolExecutor(ctx["score_jobs"]) as pool:
        scored = list(pool.map(score, rows))
    write_shard(out / f"scored-{index:04d}.jsonl", scored_id, scored)
    print(f"shard {index} done: {len(scored)} bodies", flush=True)
    return scored


def select_blockers(report: dict, sha: str, parts: list[list[Fde]]) -> list[tuple[int, list[Fde], list[Fde]]]:
    verdict = report["verdict"]
    count = sum(map(len, parts))
    if (
        report["binary_sha256"] != sha
        or report["bodies"] != count
        or report["scored"] != count
        or verdict["coverage_complete"] is not True
    ):
        raise ValueError("baseline must be a complete report for this image")
    blocked = verdict["blocking"]
    starts = set(blocked)
    selected = []
    for index, part in enumerate(parts):
        wanted = [f for f in part if f.start in starts]
        if wanted:
            selected.append((index, part, wanted))
    if sum(len(wanted) for _, _, wanted in selected) != len(starts) or len(starts) != len(blocked):
        raise ValueError("baseline contains duplicate or unknown blocking addresses")
    return selected


def table_evidence(ctx: dict):
    """One lazily-loaded jump-table byte reader per run, shared by every body this shard scores."""
    if "evidence" not in ctx:
        import lift_probe as lp
        from lift_tables import TableEvidence

        ctx["evidence"] = TableEvidence(ctx["so"], lp.LLVM / "llvm-objdump") if ctx.get("so") else None
    return ctx["evidence"]


def scoring_fingerprint() -> str:
    import lift_probe as lp
    import lift_tables

    stamp = hashlib.sha256()
    for path in (__file__, lp.__file__, lp.pcode_lift.__file__, lift_tables.__file__):
        stamp.update(Path(path).read_bytes())
    for tool in ("opt", "llc"):
        stamp.update(lp.run_tool([lp.LLVM / tool, "--version"], check=True).stdout)
    return stamp.hexdigest()


def score_blocker_shard(index, part, wanted, baseline, ctx, scorer):
    import lift_probe as lp

    dump_id = shard_identity(ctx["sha"], ctx["fingerprint"], ctx["ghidra"], part, "")
    cached = read_shard(baseline / f"pcode-{index:04d}.jsonl", dump_id, part, pcode=True)
    if cached is None:
        raise ValueError(f"missing or invalid baseline pcode shard {index}; check --shard-size and dump identity")
    starts = {f.start for f in wanted}
    rows, sections = [r for r in cached[1:] if r["start"] in starts], cached[0]["sections"]
    payload = hashlib.sha256(json.dumps([rows, sections], sort_keys=True).encode()).hexdigest()
    score_id = shard_identity(
        ctx["sha"],
        f"{dump_id}:{payload}:{scorer}",
        ctx["ghidra"],
        wanted,
        json.dumps([ctx["pipeline"], ctx["tool_timeout"]]),
    )
    path = ctx["out"] / f"blockers-scored-{index:04d}.jsonl"
    scored = read_shard(path, score_id, wanted)
    if scored is not None:
        return scored
    with lp.ThreadPoolExecutor(ctx["score_jobs"]) as pool:
        scored = list(
            pool.map(lambda r: lp.score_row(r, sections, ctx["tool_timeout"], ctx["pipeline"], table_evidence(ctx)), rows)
        )
    write_shard(path, score_id, scored)
    return scored


def score_blockers(baseline: Path, parts: list[list[Fde]], ctx: dict) -> int:
    import lift_probe as lp

    out = ctx["out"]
    if out.resolve() == baseline.resolve():
        raise ValueError("blocker-only output must be separate from the baseline")
    report = json.loads((baseline / "summary.json").read_text())
    jobs = select_blockers(report, ctx["sha"], parts)
    scorer = scoring_fingerprint()
    rows = sorted(
        (r for index, part, wanted in jobs for r in score_blocker_shard(index, part, wanted, baseline, ctx, scorer)),
        key=lambda r: r["start"],
    )
    blocking = build_verdict(rows, coverage=False)["blocking"]
    summary = {
        "scope": "baseline_blockers_only",
        "binary_sha256": ctx["sha"],
        "scorer": scorer,
        "scored": len(rows),
        "stages": lp.summarize(rows).get("all", {}),
        "holes": lp.tally_holes(rows),
        "atomics": lp.tally_atomics(rows),
        "evidence_switches": lp.tally_evidence_switches(rows),
        "failures": lp.tally_failures(rows),
        "blocking": blocking,
    }
    (out / "blockers.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "blockers-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Rescored {len(rows)} baseline blockers; {len(blocking)} still block. No full-image verdict.")
    return int(bool(blocking))


def build(args) -> int:
    import lift_probe as lp
    import time

    started = time.monotonic()
    sha = lp.sha256(args.so)
    if sha not in UNFRAMED:
        raise SystemExit(f"no recorded frame-less functions for image {sha}")
    readelf = lp.run_tool([lp.LLVM / "llvm-readelf", "-S", args.so], text=True, check=True).stdout
    frames = lp.parse_fdes(lp.run_tool([lp.LLVM / "llvm-dwarfdump", "--eh-frame", args.so], text=True, check=True).stdout)
    data = args.so.read_bytes()
    empty_frames = [f for f in frames if f.size == 0]
    nonempty_frames = [f for f in frames if f.size != 0]
    sections, unframed = build_inventory(lp.parse_exec_sections(readelf), data, nonempty_frames, UNFRAMED[sha])
    parts = body_shards(sorted(frames + unframed, key=lambda f: f.start), args.shard_size)
    bodies = [f for part in parts for f in part]
    args.out.mkdir(parents=True, exist_ok=True)
    ctx = {
        "so": args.so,
        "out": args.out,
        "sha": sha,
        "fingerprint": lp.dump_script_fingerprint(),
        "ghidra": lp.ghidra_version(),
        "pipeline": args.pipeline,
        "scorer": scoring_fingerprint(),
        "ghidra_timeout": args.ghidra_timeout,
        "retry_missing_dump": args.retry_missing_dump,
        "tool_timeout": args.tool_timeout,
        "score_jobs": args.score_jobs,
    }
    if args.blockers_from is not None:
        try:
            return score_blockers(args.blockers_from, parts, ctx)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise SystemExit(f"invalid blocker run: {exc}") from exc
    with lp.ThreadPoolExecutor(args.ghidra_jobs) as pool:
        results = list(pool.map(lambda item: build_shard(item[0], item[1], ctx), enumerate(parts)))
    rows = sorted((r for shard in results for r in shard), key=lambda r: r["start"])
    verdict = build_verdict(rows, coverage=coverage_complete(sections) and matches_bodies(rows, bodies))
    ok = [r for r in rows if not r.get("error")]
    summary = {
        "binary_sha256": sha,
        "bodies": len(bodies),
        "frame_bodies": len(nonempty_frames),
        "empty_frames": [{"start": f.start, "reason": "zero-length FDE, no executable bytes"} for f in empty_frames],
        "unframed_bodies": len(unframed),
        "sections": sections,
        "unframed": UNFRAMED[sha],
        "scored": len(rows),
        "stages": lp.summarize(rows)["all"] if rows else {},
        "holes": lp.tally_holes(rows),
        "branchind": lp.tally_branchind(rows),
        "tables": lp.tally_tables(rows),
        "evidence_switches": lp.tally_evidence_switches(rows),
        "atomics": lp.tally_atomics(rows),
        "failures": lp.tally_failures(rows),
        "object_bytes": sum(r["obj_bytes"] for r in ok),
        "x86_bytes": sum(r["size"] for r in ok),
        "verdict": verdict,
        "wall_seconds": round(time.monotonic() - started, 1),
    }
    (args.out / "bodies.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "verdict"}, indent=2))
    print(f"runnable: {verdict['runnable']}; blocking bodies: {len(verdict['blocking'])}")
    return 0 if verdict["runnable"] else 1


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import lift_probe as lp
    import subprocess

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("so", nargs="?", type=lp.Path, default=lp.DEFAULT_SO)
    ap.add_argument("--out", type=lp.Path)
    ap.add_argument("--build", action="store_true", help="dump, lift and score every body, resuming finished shards")
    ap.add_argument("--blockers-from", type=lp.Path, help="rescore only blockers from a completed build using its pcode")
    ap.add_argument("--shard-size", type=int, default=4000)
    ap.add_argument("--ghidra-jobs", type=int, default=5)
    ap.add_argument("--score-jobs", type=int, default=3)
    ap.add_argument("--tool-timeout", type=int, default=lp.TOOL_TIMEOUT)
    ap.add_argument("--ghidra-timeout", type=int, default=lp.GHIDRA_TIMEOUT)
    ap.add_argument("--retry-missing-dump", action="store_true", help="retry only cached bodies missing from a pcode dump")
    ap.add_argument("--pipeline", default="")
    args = ap.parse_args(argv)
    if args.blockers_from and (not args.build or args.out is None or args.retry_missing_dump):
        ap.error("--blockers-from requires --build and a separate --out, and cannot retry missing dumps")
    if args.out is None:
        args.out = lp.REPO / ".tools/lift-image"
    if not args.so.exists():
        raise SystemExit(f"no ELF at {args.so}")
    if args.build:
        return build(args)
    readelf = lp.run_tool([lp.LLVM / "llvm-readelf", "-S", args.so], text=True).stdout
    frames = lp.parse_fdes(lp.run_tool([lp.LLVM / "llvm-dwarfdump", "--eh-frame", args.so], text=True).stdout)
    data = args.so.read_bytes()
    stub_sections = {".plt"}
    report = {"binary_sha256": lp.sha256(args.so), "sections": {}}
    for name, (start, end) in lp.parse_exec_sections(readelf).items():
        report["sections"][name] = account_section(name, start, end, data[start:end], frames, name in stub_sections)
    outside = [f for f in frames if not any(s["start"] <= f.start < s["start"] + s["size"] for s in report["sections"].values())]
    report["bodies_outside_executable_sections"] = [hex(f.start) for f in outside]
    report["coverage_complete"] = coverage_complete(report["sections"]) and not outside
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "coverage.json").write_text(json.dumps(report, indent=2) + "\n")
    for acct in report["sections"].values():
        print(
            f"{acct['name']:8} {acct['size']:>10} B  bodies {acct['bodies']:>7}  body {acct['body_bytes']:>10}  "
            f"padding {acct['gap_bytes']['padding']:>8}  stub {acct['stub_bytes']:>6}  unaccounted {len(acct['unaccounted'])}"
        )
    return 0 if report["coverage_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
