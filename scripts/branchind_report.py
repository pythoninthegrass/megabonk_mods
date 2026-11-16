#!/usr/bin/env -S uv run --script
"""Records the stack-balance verdict for the indirect jumps a lift probe left unresolved.

Reads a probe run's bodies.jsonl (the emitter already ran the proof on each body), and writes a
proven / unproven / untracked-rsp census with one reason per unproven site. It only reads what the
probe already recorded, so re-running it needs no Ghidra.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

UNTRACKED = "rsp untrackable on a path into the site"


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"no probe bodies at {path}; run scripts/lift_probe.py --out {path.parent} first")
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not row.get("error"):
            rows.append(row)
    return rows


def census(rows: list[dict]) -> dict:
    """Counts proven tail calls and the unproven indirect jumps, each unproven one carrying its reason."""
    sites: list[dict] = []
    for row in rows:
        for site in row.get("unproven_branchind", []):
            sites.append({"body": row["start"], "at": site["a"], "reason": site["reason"], "rsp_delta": site["rsp_delta"]})
    reasons = Counter(site["reason"] for site in sites)
    untracked = sum(1 for site in sites if site["rsp_delta"] is None)
    return {
        "bodies": len(rows),
        "proven_tail_calls": sum(row.get("proven_tail_calls", 0) for row in rows),
        "unproven_sites": len(sites),
        "untracked_rsp_sites": untracked,
        "unproven_reasons": dict(reasons),
        "unproven_by_body": [
            {
                "body": hex(start),
                "sites": [{"at": hex(s["at"]), "reason": s["reason"], "rsp_delta": s["rsp_delta"]} for s in group],
            }
            for start, group in _group(sites)
        ],
    }


def _group(sites: list[dict]) -> list[tuple[int, list[dict]]]:
    """One entry per body that has an unproven site, with every such site under it, in body order."""
    order: list[int] = []
    buckets: dict[int, list[dict]] = {}
    for site in sites:
        body = site["body"]
        if body not in buckets:
            buckets[body] = []
            order.append(body)
        buckets[body].append(site)
    return [(body, buckets[body]) for body in order]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out", type=Path, help="a lift probe output directory holding bodies.jsonl")
    ap.add_argument("--write", action="store_true", help="write branchind.json beside bodies.jsonl")
    args = ap.parse_args(argv)
    rows = read_rows(args.out / "bodies.jsonl")
    report = census(rows)
    text = json.dumps(report, indent=2) + "\n"
    if args.write:
        (args.out / "branchind.json").write_text(text)
        print(f"wrote {args.out / 'branchind.json'}", file=sys.stderr)
    print(text, end="")
    if report["proven_tail_calls"] == 0 and report["bodies"]:
        print("no BRANCHIND site was proven balanced", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
