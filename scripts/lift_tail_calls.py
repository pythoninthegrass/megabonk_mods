#!/usr/bin/env -S uv run --script
"""Checks the emitter's indirect tail-call rule against Ghidra's decompiler for the bodies it fired on.

Reads bodies.jsonl from the lift probe, keeps the rows counted as indirect tail calls, redumps their
pcode through Ghidra, and compares what `scripts/pcode_lift.py` decided at each `BRANCHIND` site with
the jump tables, the `switch` and the abandoned jumptable warnings its own decompiler pass recovered.
Recovering no table at a site is not evidence about that site, so only a table inside the body, or a
switch its cases anchor there, counts as a second opinion. It records only: no lifting rule is added.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lift_holes as lh  # noqa: E402
import lift_probe as lp  # noqa: E402
import pcode_lift as pl  # noqa: E402

VERDICTS = ("agrees", "disagrees", "mixed", "no tail call", "switch beyond body", "not decompiled")
NO_VIEW = {
    "tables": 0,
    "cases": 0,
    "cases_in_body": 0,
    "tables_in_body": 0,
    "switch_in_c": False,
    "unrecoverable": [],
    "decompiled": False,
}


def select_tail_rows(rows: list[dict]) -> list[dict]:
    """Keeps the probe rows the emitter counted as containing an indirect tail call."""
    return [row for row in rows if row.get("tail_calls")]


def decompiler_view(fn: dict) -> dict:
    """What the decompiler pass of LiftDump.java said about this body.

    Tables and cases outside the body belong to code the decompiler pulled in past the
    `.eh_frame` bounds, so they are counted but never treated as evidence about this body.
    """
    tables = fn.get("jt", [])
    start, end = fn["start"], fn["start"] + fn["size"]
    return {
        "tables": len(tables),
        "cases": sum(len(table["cases"]) for table in tables),
        "cases_in_body": sum(1 for table in tables for case in table["cases"] if start <= case < end),
        "tables_in_body": sum(1 for table in tables if start <= table["at"] < end),
        "switch_in_c": bool(fn.get("sw")),
        "unrecoverable": sorted(fn.get("uw", [])),
        "decompiled": bool(fn.get("dc")),
    }


def emitter_sites(fn: dict, sections: list[dict]) -> list[dict]:
    """Per indirect jump site, whether the emitter itself lowers it as a tail call or a switch."""
    lifter = pl.BodyLifter(fn, sections)
    at = {insn["a"]: insn for insn in fn["insns"]}
    return [
        {
            "a": site["a"],
            "tail_call": site["a"] not in lifter.tables and lifter.defined_by_load(at[site["a"]], site["k"], site["target"]),
            "table": site["a"] in lifter.tables,
        }
        for site in lh.branchind_sites(fn)
    ]


def switch_in_body(view: dict, sites: list[dict]) -> bool:
    """Whether the decompiler claimed a switch for code inside this body."""
    return bool(view["tables_in_body"] or view["cases_in_body"] or any(site["table"] for site in sites))


def verdict(view: dict, sites: list[dict]) -> str:
    """Names the body from what the decompiler recovered against what the emitter called a tail call.

    The decompiler's `Could not recover jumptable` warning fires on any indirect jump whose targets it
    cannot enumerate, which is 190 of the 198 sites in the sample, so it is recorded as evidence and never
    decides a verdict. Only a recovered table, or a switch in the decompiled C, is a second opinion.
    """
    if not view["decompiled"]:
        return "not decompiled"
    tail = [site for site in sites if site["tail_call"]]
    if not tail:
        return "no tail call"
    if any(site["table"] for site in tail):
        return "disagrees"
    if switch_in_body(view, sites):
        return "mixed"
    if view["switch_in_c"]:
        return "switch beyond body"
    return "agrees"


def verdict_reasons(view: dict, sites: list[dict], tables: list[dict], tail_calls: int, bounds: tuple[int, int]) -> list[str]:
    """The sentences that justify the verdict, one per contradiction the decompiler found."""
    start, end = bounds
    tail = [site for site in sites if site["tail_call"]]
    tabled = [site for site in sites if site["table"]]
    reasons = []
    if tabled:
        at = ", ".join(f"0x{site['a']:x}" for site in tabled)
        reasons.append(f"jump tables were recovered at {at}, which the emitter lowers as switches, not tail calls")
    if switch_in_body(view, sites) and tail and not tabled:
        where = ", ".join(f"0x{site['a']:x}" for site in tail)
        at = ", ".join(
            f"0x{table['at']:x} with {len(table['cases'])} cases"
            for table in tables
            if any(start <= case < end for case in table["cases"]) or start <= table["at"] < end
        )
        reasons.append(f"the decompiler recovered a switch at {at} while the emitter tail jumps at {where}")
    if view["switch_in_c"] and not switch_in_body(view, sites):
        where = ", ".join(f"0x{site['a']:x}" for site in tail)
        recovered = (
            f"none of the {view['tables']} recovered table(s) has an address or a case in this body"
            if view["tables"]
            else "no jump table was recovered"
        )
        reasons.append(f"the switch in the decompiled C is beyond the body, {recovered}; the tail call sits at {where}")
    if not tail and tables:
        at = ", ".join(f"0x{table['at']:x} with {len(table['cases'])} cases" for table in tables)
        reasons.append(f"the probe counted {tail_calls} tail call(s); this dump recovers the table at {at} instead")
    given_up = [site for site in tail if site["a"] in view["unrecoverable"]]
    if given_up:
        where = ", ".join(f"0x{site['a']:x}" for site in given_up)
        reasons.append(f"the decompiler declined to rebuild a table at {where} and treated the jump as a call")
    return reasons


def audit_body(fn: dict, row: dict, sections: list[dict], relocs: dict[int, int], disasm: dict[int, str]) -> dict:
    """One body: the emitter's decision, the decompiler's view, and the verdict between them."""
    classified = {site["a"]: site for site in lh.classify_body(fn, sections, relocs, disasm)["sites"]}
    tables = fn.get("jt", [])
    sites = [{**site, **classified.get(site["a"], {})} for site in emitter_sites(fn, sections)]
    view = decompiler_view(fn)
    return {
        "start": row["start"],
        "size": row["size"],
        "tail_calls": row.get("tail_calls", 0),
        "holes": row.get("holes", []),
        "decompiler": view,
        "verdict": verdict(view, sites),
        "reasons": verdict_reasons(
            view, sites, tables, row.get("tail_calls", 0), (fn["start"], fn["start"] + fn["size"])
        ),
        "sites": sites,
    }


def missing_body(row: dict) -> dict:
    """The record for a body Ghidra did not return, kept out of the agreeing tally."""
    return {
        "start": row["start"],
        "size": row["size"],
        "tail_calls": row.get("tail_calls", 0),
        "holes": row.get("holes", []),
        "decompiler": dict(NO_VIEW),
        "verdict": "not decompiled",
        "reasons": ["body missing from the pcode dump"],
        "sites": [],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("so", nargs="?", type=Path, default=lp.DEFAULT_SO)
    ap.add_argument("--out", type=Path, default=lp.DEFAULT_OUT)
    ap.add_argument("--bodies", type=Path, default=None, help="probe bodies.jsonl; defaults to <out>/bodies.jsonl")
    ap.add_argument("--json", action="store_true", help="print the rows as JSON lines instead of a table")
    args = ap.parse_args(argv)

    bodies_path = args.bodies or args.out / "bodies.jsonl"
    if not bodies_path.exists():
        raise SystemExit(f"no probe output at {bodies_path}; run task re:lift-probe first")
    if not args.so.exists():
        raise SystemExit(f"no ELF at {args.so}")
    rows = [json.loads(line) for line in bodies_path.read_text().splitlines()]
    tail = select_tail_rows(rows)
    if not tail:
        print(f"no bodies with tail_calls in {bodies_path}")
        return 0

    fdes = [lp.Fde(row["start"], row["size"]) for row in tail]
    with tempfile.TemporaryDirectory() as tmp:
        dumped, sections = lp.dump_pcode(args.so, fdes, Path(tmp))
    by_start = {fn["start"]: fn for fn in dumped}
    relocs = lh.read_relocs(args.so)

    results = []
    for row in tail:
        fn = by_start.get(row["start"])
        if fn is None:
            results.append(missing_body(row))
            continue
        disasm = lh.disassemble(args.so, fn["start"], fn["size"])
        results.append(audit_body(fn, row, sections, relocs, disasm))

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "tail_calls.jsonl").write_text("".join(json.dumps(r) + "\n" for r in results))
    counts = Counter(result["verdict"] for result in results)
    tail_sites = [site for result in results for site in result["sites"] if site["tail_call"]]
    summary = {
        "bodies": len(results),
        "tail_call_sites": len(tail_sites),
        "by_verdict": {name: counts.get(name, 0) for name in VERDICTS},
        "sites_the_decompiler_declined_on": sum(
            1 for result in results for site in result["sites"] if site["tail_call"] and site["a"] in result["decompiler"]["unrecoverable"]
        ),
        "disagreeing_starts": [f"0x{result['start']:x}" for result in results if result["verdict"] == "disagrees"],
        "mixed_starts": [f"0x{result['start']:x}" for result in results if result["verdict"] == "mixed"],
        "beyond_body_starts": [
            f"0x{result['start']:x}" for result in results if result["verdict"] == "switch beyond body"
        ],
        "no_tail_call_starts": [f"0x{result['start']:x}" for result in results if result["verdict"] == "no tail call"],
    }
    (args.out / "tail_calls_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if args.json:
        for result in results:
            print(json.dumps(result))
    else:
        for result in results:
            if result["verdict"] == "agrees":
                continue
            print(f"0x{result['start']:x} {result['size']:>6} B  {result['verdict']}")
            for reason in result["reasons"]:
                print(f"    | {reason}")
            for site in result["sites"]:
                for line in site["x86"]:
                    print(f"    {line}")
                for line in site["evidence"]:
                    print(f"    | {line}")
    print(json.dumps(summary, indent=2))
    print(f"wrote {args.out / 'tail_calls.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
