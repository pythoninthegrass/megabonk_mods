#!/usr/bin/env -S uv run --script
"""Classifies the computed jumps the lift probe could not resolve.

Reads bodies.jsonl from the lift probe, takes the bodies whose holes include BRANCHIND or
JUMPTABLE_TARGET, redumps their pcode through Ghidra, and gives each indirect-jump site a
category backed by the instruction sequence that leads to it: the x86 text from llvm-objdump,
the traced pcode, the section the target was loaded from, any relocation on that slot, and
whatever jump tables Ghidra's decompiler recovered. It records only; nothing here changes how
a body is lifted.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lift_probe as lp  # noqa: E402

CATEGORIES = ("unrecovered switch", "indirect tail call", "indirect call target", "other")
JUMP_HOLES = ("BRANCHIND", "JUMPTABLE_TARGET")
ADDRESS_SPACES = ("ram", "const", "cptr")
MEMORY_SPACES = ("ram",)
ADDRESS_FLOOR = 0x1000
SCALE_OPS = {"INT_MULT", "INT_LEFT", "INT_RIGHT", "INT_SRIGHT"}
FOLD_OPS = SCALE_OPS | {
    "COPY",
    "INT_ADD",
    "INT_SUB",
    "INT_AND",
    "INT_OR",
    "INT_XOR",
    "INT_ABS",
    "INT_NEGATE",
    "INT_2COMP",
    "SUBPIECE",
    "PIECE",
    "INT_ZEXT",
    "INT_SEXT",
}
EPILOGUE = re.compile(r"\b(pop|leave|ret)\b|add rsp")
CMP_IMMEDIATE = re.compile(r"\bcmp\b.*,\s*(?:0x)?[0-9a-f]+\s*$")
JCC_ABOVE_BELOW = re.compile(r"\bj(ae?|be?)\b")
RELOC_LINE = re.compile(r"^([0-9a-f]{8,16})\s+([0-9a-f]{8,16})\s+(R_X86_64_\w+)\s+([0-9a-f]+)\b")
OBJDUMP_LINE = re.compile(r"^\s*([0-9a-f]+):\s+(.*)$")
TRACE_HOPS = 12
EXPRESSION_BUDGET = 24
SEQUENCE_LIMIT = 12


@dataclass
class Trace:
    """What the pcode backward walk learned about an indirect jump target."""

    kind: str = "unresolved"
    path: list[str] = field(default_factory=list)
    ops: list[str] = field(default_factory=list)
    slot: int | None = None
    base: int | None = None
    base_space: str | None = None
    base_rank: tuple = ()
    scaled: bool = False
    register_relative: bool = False


@dataclass
class SiteFacts:
    """Structural facts about one indirect jump site, the input to the category rules."""

    addr: int
    kind: str = "unresolved"
    slot: int | None = None
    slot_section: str | None = None
    slot_reloc: int | None = None
    base: int | None = None
    base_section: str | None = None
    scaled_index: bool = False
    register_relative: bool = False
    ends_body: bool = False
    epilogue: bool = False
    bounds_check: bool = False
    arms: int = 0
    cases_in_body: int = 0
    cases_outside: int = 0


def select_hole_rows(rows: list[dict], kinds: tuple[str, ...] = JUMP_HOLES) -> list[dict]:
    """Keeps the probe rows carrying one of `kinds`, which identify the unresolved computed jumps."""
    return [row for row in rows if any(hole in kinds for hole in row.get("holes", []))]


def varnode(text: str | None) -> tuple[str, int, int] | None:
    space, offset, size = (text or "").split(",")
    if not text or not size:
        return None
    return space, int(offset, 16), int(size)


def render(op: dict) -> str:
    operands = ", ".join(v for v in op["in"] if v)
    out = "" if op["out"] is None else f"{op['out']} <- "
    return f"{op['op']} {out}{operands}"


def flatten(fn: dict) -> list[dict]:
    """Every pcode op of a body in execution order, tagged with its instruction address."""
    return [{**op, "a": insn["a"], "k": k} for insn in fn["insns"] for k, op in enumerate(insn["ops"])]


def branchind_sites(fn: dict) -> list[dict]:
    """The BRANCHIND ops of a body: the sites the emitter could not turn into a switch."""
    return [
        {"a": op["a"], "k": op["k"], "index": index, "target": op["in"][0]}
        for index, op in enumerate(flatten(fn))
        if op["op"] == "BRANCHIND"
    ]


def last_def(ops: list[dict], index: int, target: str) -> int | None:
    """Index of the nearest op before `index` that writes `target`."""
    for i in range(index - 1, -1, -1):
        if ops[i]["out"] == target:
            return i
    return None


def _better_base(trace: Trace, space: str, offset: int, size: int) -> None:
    """Keeps the likeliest table base: a memory space beats a constant, an address-sized
    value beats a scale factor."""
    if space == "const" and size < 8:
        return
    rank = (space != "const", offset >= ADDRESS_FLOOR, size)
    if trace.base is None or rank > trace.base_rank:
        trace.base, trace.base_space, trace.base_rank = offset, space, rank


def _walk_expression(ops: list[dict], index: int, target: str | None, trace: Trace, budget: int) -> None:
    """Collects constants, registers and scaling from the expression feeding a load address.

    A register keeps its name as a relative pointer but is still followed to a constant
    base, since a position-independent table reaches the jump through one (`lea rdx, [rip]`).
    """
    parsed = varnode(target)
    if parsed is None or budget <= 0:
        return
    space, offset, size = parsed
    if space in ADDRESS_SPACES:
        _better_base(trace, space, offset, size)
        return
    if space == "register":
        trace.register_relative = True
    defining = last_def(ops, index, target)
    if defining is None:
        return
    op = ops[defining]
    if op["op"] not in FOLD_OPS or memory_read(op) is not None:
        return
    trace.scaled |= op["op"] in SCALE_OPS
    for operand in op["in"]:
        _walk_expression(ops, defining, operand, trace, budget - 1)


def memory_read(op: dict) -> str | None:
    """The pointer operand when an op reads memory: LOAD carries it after the space id, a
    folded fixed-address read is a COPY from the ram space (a `lea` in cptr space is a value)."""
    operands = [v for v in op["in"] if v]
    if op["op"] == "LOAD":
        return operands[-1] if operands else None
    if op["op"] == "COPY":
        written = varnode(op["out"])
        if written and written[0] in ADDRESS_SPACES:
            return None
        reads = [v for v in operands if (varnode(v) or ("", 0, 0))[0] in MEMORY_SPACES]
        return reads[0] if reads else None
    return None


def trace_load(ops: list[dict], index: int, target: str) -> Trace:
    """Walks `target` back through the ops before `index` to the load that produced it."""
    trace = Trace(path=[ops[index]["op"]], ops=[render(ops[index])])
    current, at, hops = target, index, 0
    while hops < TRACE_HOPS:
        hops += 1
        defining = last_def(ops, at, current)
        if defining is None:
            break
        op = ops[defining]
        trace.path.append(op["op"])
        trace.ops.append(render(op))
        pointer = memory_read(op)
        if pointer is not None:
            trace.kind = "load"
            parsed = varnode(pointer)
            if parsed and parsed[0] in ADDRESS_SPACES:
                trace.slot = parsed[1]
            else:
                _walk_expression(ops, defining, pointer, trace, EXPRESSION_BUDGET)
            break
        if op["op"] not in FOLD_OPS:
            break
        trace.scaled |= op["op"] in SCALE_OPS
        operands = [v for v in op["in"] if varnode(v)]
        follow = next((v for v in operands if varnode(v)[0] not in ADDRESS_SPACES), None)
        if follow is None:
            break
        current, at = follow, defining
    trace.ops.reverse()
    return trace


def section_of(sections: list[dict], offset: int | None) -> dict | None:
    if offset is None:
        return None
    return next((sec for sec in sections if sec["va"] <= offset < sec["va"] + sec["size"]), None)


def table_cases(fn: dict) -> tuple[int, int]:
    """Cases of the decompiler-recovered tables, split by whether they land inside the body."""
    end = fn["start"] + fn["size"]
    inside = outside = 0
    for table in fn.get("jt", []):
        for case in table["cases"]:
            if fn["start"] <= case < end:
                inside += 1
            else:
                outside += 1
    return inside, outside


def branch_arms(fn: dict) -> int:
    """Distinct in-body branch targets, the arm count a switch would have."""
    addrs = {insn["a"] for insn in fn["insns"]}
    targets = set()
    for op in flatten(fn):
        if op["op"] in ("BRANCH", "CBRANCH"):
            pointer = varnode(op["in"][0])
            if pointer and pointer[0] == "ram" and pointer[1] in addrs:
                targets.add(pointer[1])
    return len(targets)


def has_bounds_check(sequence: list[str]) -> bool:
    """A compare against an immediate followed by a below-or-above jump: a switch bounds check."""
    compared = False
    for line in sequence:
        if compared and JCC_ABOVE_BELOW.search(line):
            return True
        compared = bool(CMP_IMMEDIATE.search(line))
    return False


def has_epilogue(sequence: list[str]) -> bool:
    """Frame teardown in the x86 text, which is what a tail jump follows."""
    return any(EPILOGUE.search(line) for line in sequence)


def ends_body(fn: dict, site_addr: int) -> bool:
    """True when the indirect jump is the last thing in the body, so nothing returns to it."""
    for insn in fn["insns"]:
        if insn["a"] == site_addr:
            return insn["a"] + insn["len"] >= fn["start"] + fn["size"]
    return False


def classify_facts(facts: SiteFacts) -> str:
    """Names a site from its structure; the first matching rule wins."""
    if facts.slot is not None and facts.slot_reloc is not None and not facts.scaled_index:
        return "indirect call target"
    if facts.base_section is not None and (facts.scaled_index or (facts.arms >= 2 and facts.bounds_check)):
        return "unrecovered switch"
    if facts.cases_in_body >= 2:
        return "unrecovered switch"
    if facts.kind == "load" and not facts.scaled_index and (facts.register_relative or facts.slot is not None):
        return "indirect tail call"
    return "other"


def site_evidence(fn: dict, facts: SiteFacts, trace: Trace) -> list[str]:
    """The lines that justify a category, in the order a reader should check them."""
    lines = [f"target chain: {' <- '.join([op for op in trace.path] or ['none'])}"]
    tables = fn.get("jt", [])
    if tables:
        for table in tables:
            lines.append(
                f"decompiler jump table at 0x{table['at']:x} with {len(table['cases'])} cases, "
                f"{facts.cases_outside} outside the body"
            )
    else:
        lines.append("no decompiler jump table recovered for the body")
    if facts.slot is not None:
        where = facts.slot_section or "unmapped"
        lines.append(f"target loaded from fixed slot 0x{facts.slot:x} in {where}")
        if facts.slot_reloc is not None:
            lines.append(f"slot 0x{facts.slot:x} carries R_X86_64_RELATIVE into code at 0x{facts.slot_reloc:x}")
    if facts.base is not None and facts.base_section:
        lines.append(f"load address base 0x{facts.base:x} in {facts.base_section}")
    elif facts.base is not None:
        lines.append(f"load address constant 0x{facts.base:x} (no section)")
    lines.append(
        f"shape: scaled_index={facts.scaled_index} register_relative={facts.register_relative} "
        f"arms={facts.arms} bounds_check={facts.bounds_check} ends_body={facts.ends_body} "
        f"epilogue={facts.epilogue}"
    )
    return lines


def classify_body(fn: dict, sections: list[dict], relocs: dict[int, int], disasm: dict[int, str]) -> dict:
    """Categorises every indirect jump site of a body; the body takes the first named category."""
    ops = flatten(fn)
    inside, outside = table_cases(fn)
    sites = []
    for site in branchind_sites(fn):
        trace = trace_load(ops, site["index"], site["target"])
        base_sec = section_of(sections, trace.base)
        slot_sec = section_of(sections, trace.slot)
        addend = relocs.get(trace.slot) if trace.slot is not None else None
        addend_sec = section_of(sections, addend)
        facts = SiteFacts(
            addr=site["a"],
            kind=trace.kind,
            slot=trace.slot,
            slot_section=slot_sec["name"] if slot_sec else None,
            slot_reloc=addend if addend_sec and addend_sec["exec"] else None,
            base=trace.base,
            base_section=base_sec["name"] if base_sec and not base_sec["exec"] else None,
            scaled_index=trace.scaled,
            register_relative=trace.register_relative,
            ends_body=ends_body(fn, site["a"]),
            epilogue=has_epilogue(x86_sequence(disasm, fn["start"], site["a"])),
            bounds_check=has_bounds_check(x86_sequence(disasm, fn["start"], site["a"], limit=None)),
            arms=branch_arms(fn),
            cases_in_body=inside,
            cases_outside=outside,
        )
        sites.append(
            {
                "a": site["a"],
                "category": classify_facts(facts),
                "x86": x86_sequence(disasm, fn["start"], site["a"]),
                "pcode": trace.ops,
                "evidence": site_evidence(fn, facts, trace),
                "facts": vars(facts),
            }
        )
    named = [site["category"] for site in sites if site["category"] != "other"]
    category = min(named, key=CATEGORIES.index) if named else "other"
    return {"start": fn["start"], "size": fn["size"], "category": category, "sites": sites}


def parse_objdump(text: str) -> dict[int, str]:
    """Address to instruction text from `llvm-objdump -d --no-show-raw-insn` output."""
    disasm = {}
    for line in text.splitlines():
        match = OBJDUMP_LINE.match(line)
        if match and not line.lstrip().startswith(("0000", "Disassembly", ".")):
            disasm[int(match.group(1), 16)] = " ".join(match.group(2).split())
    return disasm


def parse_relocs(text: str) -> dict[int, int]:
    """Slot to target for the R_X86_64_RELATIVE rows of `llvm-readelf -r`; other types carry symbols."""
    relocs = {}
    for line in text.splitlines():
        match = RELOC_LINE.match(line.strip())
        if match and match.group(3) == "R_X86_64_RELATIVE":
            relocs[int(match.group(1), 16)] = int(match.group(4), 16)
    return relocs


def x86_sequence(disasm: dict[int, str], start: int, site: int, limit: int = SEQUENCE_LIMIT) -> list[str]:
    """The instructions from the body up to and including the site, newest `limit` of them."""
    window = [text for addr, text in sorted(disasm.items()) if start <= addr <= site]
    return window if limit is None else window[-limit:]


def disassemble(so: Path, start: int, size: int) -> dict[int, str]:
    return parse_objdump(
        lp.run_tool(
            [
                lp.LLVM / "llvm-objdump",
                "-d",
                "--no-show-raw-insn",
                "--x86-asm-syntax=intel",
                f"--start-address=0x{start:x}",
                f"--stop-address=0x{start + size:x}",
                so,
            ],
            text=True,
        ).stdout
    )


def read_relocs(so: Path) -> dict[int, int]:
    return parse_relocs(lp.run_tool([lp.LLVM / "llvm-readelf", "-r", so], text=True).stdout)


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
    holes = select_hole_rows(rows)
    if not holes:
        print(f"no {JUMP_HOLES} holes in {bodies_path}")
        return 0

    fdes = [lp.Fde(row["start"], row["size"]) for row in holes]
    with tempfile.TemporaryDirectory() as tmp:
        dumped, sections = lp.dump_pcode(args.so, fdes, Path(tmp))
    by_start = {fn["start"]: fn for fn in dumped}
    relocs = read_relocs(args.so)

    results = []
    for row in holes:
        fn = by_start.get(row["start"])
        if fn is None:
            results.append({"start": row["start"], "size": row["size"], "category": "other", "sites": [], "note": "not dumped"})
            continue
        result = classify_body(fn, sections, relocs, disassemble(args.so, fn["start"], fn["size"]))
        result["holes"] = row["holes"]
        results.append(result)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "jump_holes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in results))
    counts = Counter(result["category"] for result in results)
    if args.json:
        for result in results:
            print(json.dumps(result))
    else:
        for result in results:
            print(f"0x{result['start']:x} {result['size']:>6} B  {result['category']}")
            for site in result["sites"]:
                for line in site["x86"]:
                    print(f"    {line}")
                for line in site["evidence"]:
                    print(f"    | {line}")
    print(json.dumps({"bodies": len(results), "by_category": {name: counts.get(name, 0) for name in CATEGORIES}}, indent=2))
    print(f"wrote {args.out / 'jump_holes.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
