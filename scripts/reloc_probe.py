#!/usr/bin/env -S uv run --script
"""Classify every base-relative relocation in the shipped Linux runtime by what it points at.

The 466,320 R_X86_64_RELATIVE fixups are the pointers the game carries in data: vtables,
method tables, string and metadata tables. Each one holds a pre-relocation x86 address, so
rebuilding the code for arm64 means turning those into references to lifted functions and to
rebuilt data sections. This census says how mechanical that can be: how many name a function
entry, how many land inside a function, and how many point at memory that is not code at all.

A relative relocation's addend is the target as linked, and a DSO is linked at base zero, so
the addend is the address to classify. Function bounds are the .eh_frame records the lift
probe cuts bodies from. It reads bytes only: nothing is loaded or run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eh_probe  # noqa: E402  .eh_frame walk shared with the exception census
import elf_shim_probe  # noqa: E402  stdlib ELF reader, reused for sections and relocations

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SO = REPO / ".tools/megabonk-linux-native/Megabonk/GameAssembly.so"
DEFAULT_OUT = REPO / ".tools/reloc-probe"

R_X86_64_RELATIVE = 8
PT_LOAD = 1
SHT_PROGBITS = 1
SHT_NOBITS = 8
SHF_WRITE = 0x1
SHF_ALLOC = 0x2
SHF_EXECINSTR = 0x4
PF_R = 0x4
PF_W = 0x2

DOCUMENTED_RELATIVE = 466_320
BUCKETS = ("function_entry", "function_interior", "read_only_data", "writable_data", "bss", "other_loaded", "outside")
OTHER_LOADED_KINDS = ("executable_no_frame", "unsectioned")

# Bytes a compiler puts at the start of a body: REX and push/pop, the ALU and mov forms,
# test, jmp/call, ret, int3, SSE and x87 escapes, and the prefixes (66 operand size, f2/f3
# string and scalar SSE). The census reports the full first-byte histogram alongside the
# bytes this set does not explain, so the list is something a reader can audit, not a
# number the probe quietly trusts.
INSTRUCTION_STARTS = frozenset(
    set(range(0x40, 0x60))  # REX, push, pop
    | {
        0x00,
        0x01,
        0x02,
        0x03,
        0x08,
        0x09,
        0x0A,
        0x0B,
        0x10,
        0x11,
        0x18,
        0x19,
        0x20,
        0x21,
        0x28,
        0x29,
        0x30,
        0x31,
        0x38,
        0x39,
        0x3B,
        0x3D,
        0x3E,
        0x3F,
    }  # add/or/adc/sbb/and/sub/xor/cmp
    | {0x63, 0x68, 0x69, 0x6A, 0x6B, 0x6D, 0x70, 0x74, 0x75, 0x7C, 0x7D}  # movsx, push, imul, jcc
    | {0x80, 0x81, 0x83, 0x84, 0x85, 0x88, 0x89, 0x8A, 0x8B, 0x8D, 0x8F}  # group, test, mov, lea
    | {0x90, 0x98, 0x9C, 0xB0, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xBB, 0xBE, 0xBF}  # nop, mov imm
    | {0xC0, 0xC1, 0xC3, 0xC6, 0xC7, 0xC9, 0xCC, 0xD7, 0xE8, 0xE9, 0xEB}  # shifts, ret, leave, call, jmp
    | {0xF2, 0xF3, 0xF4, 0xF6, 0xF7, 0xFF}  # prefixes, hlt, test group, jmp/call group
    | {0x0F, 0x66}  # two-byte escapes, operand size
)


@dataclass(frozen=True)
class Body:
    start: int
    end: int


@dataclass(frozen=True)
class Target:
    slot: int
    address: int
    bucket: str
    slot_section: str | None


def bodies(frames) -> tuple[Body, ...]:
    """Body ranges from .eh_frame records: one per distinct start, at its widest range.

    A function can be described by more than one FDE, so records are folded by start the way
    the exception census folds them; that keeps both probes counting the same 196,137 bodies.
    """
    widest: dict[int, int] = {}
    for frame in frames:
        if frame.pc_range <= 0:
            continue
        end = frame.pc_begin + frame.pc_range
        if end > widest.get(frame.pc_begin, 0):
            widest[frame.pc_begin] = end
    return tuple(Body(start, end) for start, end in sorted(widest.items()))


def count_overlaps(ranges: tuple[Body, ...]) -> int:
    """How many records start before everything before them has ended, nesting included."""
    count = 0
    highest = 0
    for body in ranges:
        if body.start < highest:
            count += 1
        highest = max(highest, body.end)
    return count


def merge(ranges: tuple[Body, ...]) -> tuple[Body, ...]:
    """Overlapping records as one covered span, so containment does not depend on nesting."""
    merged: list[Body] = []
    for body in ranges:
        if merged and body.start <= merged[-1].end:
            if body.end > merged[-1].end:
                merged[-1] = Body(merged[-1].start, body.end)
        else:
            merged.append(body)
    return tuple(merged)


class AddressMap:
    """Answers what a virtual address is: code the unwinder knows, data, or nothing."""

    def __init__(self, sections, loads, ranges: tuple[Body, ...]):
        self.sections = tuple(sections)
        self.loads = tuple(loads)
        self.bodies = tuple(ranges)
        self.starts = frozenset(body.start for body in self.bodies)
        self._merged = merge(self.bodies)
        self._merged_starts = [body.start for body in self._merged]
        self._alloc = [s for s in self.sections if s.flags & SHF_ALLOC and s.size]
        self._names: dict[int, str | None] = {}

    def covered(self, addr: int) -> bool:
        at = bisect_right(self._merged_starts, addr) - 1
        return at >= 0 and addr < self._merged[at].end

    def section_at(self, addr: int):
        """The tightest allocated section holding the address, so a wrapper cannot swallow one."""
        best = None
        for section in self._alloc:
            if section.addr <= addr < section.addr + section.size:
                if best is None or section.size < best.size:
                    best = section
        return best

    def section_name(self, addr: int) -> str | None:
        if addr not in self._names:
            section = self.section_at(addr)
            self._names[addr] = None if section is None else section.name
        return self._names[addr]

    def in_segment(self, addr: int) -> bool:
        return any(seg.vaddr <= addr < seg.vaddr + seg.memsz for seg in self.loads if seg.type == PT_LOAD)

    def bucket(self, addr: int) -> str:
        if addr in self.starts:
            return "function_entry"
        if self.covered(addr):
            return "function_interior"
        section = self.section_at(addr)
        if section is not None:
            if section.type == SHT_NOBITS:
                return "bss"
            if section.flags & SHF_WRITE:
                return "writable_data"
            if section.flags & SHF_EXECINSTR:
                return "other_loaded"
            return "read_only_data"
        if self.in_segment(addr):
            return "other_loaded"
        return "outside"

    def other_loaded_kind(self, addr: int) -> str:
        section = self.section_at(addr)
        if section is not None and section.flags & SHF_EXECINSTR:
            return "executable_no_frame"
        return "unsectioned"


def classify(relocs, mapping: AddressMap) -> list[Target]:
    """One row per relocation: the slot it writes, the address it names, and what that is."""
    bucket_cache: dict[int, str] = {}
    slot_cache: dict[int, str | None] = {}
    rows: list[Target] = []
    for reloc in relocs:
        bucket = bucket_cache.get(reloc.addend)
        if bucket is None:
            bucket = mapping.bucket(reloc.addend)
            bucket_cache[reloc.addend] = bucket
        if reloc.offset in slot_cache:
            slot_section = slot_cache[reloc.offset]
        else:
            slot_section = mapping.section_name(reloc.offset)
            slot_cache[reloc.offset] = slot_section
        rows.append(Target(reloc.offset, reloc.addend, bucket, slot_section))
    return rows


def entry_prologue_shapes(rows, elf, raw: bytes | None) -> dict:
    """What the bytes at the entry targets actually are, as a check on the entry bucket.

    An entry that opens on zero padding would mean the frame table, not the classifier, is
    wrong, so the census names the padding count and the first bytes it cannot explain.
    """
    first_bytes: Counter[int] = Counter()
    padding = 0
    unreadable = 0
    for row in rows:
        if row.bucket != "function_entry":
            continue
        if raw is None:
            unreadable += 1
            continue
        try:
            at = elf.offset_of(row.address)
        except elf_shim_probe.ElfError:
            unreadable += 1
            continue
        head = raw[at : at + 4]
        if head == b"\x00\x00\x00\x00":
            padding += 1
        first_bytes[head[0]] += 1
    unexplained = {f"{byte:02x}": count for byte, count in first_bytes.items() if byte not in INSTRUCTION_STARTS}
    return {
        "targets": sum(first_bytes.values()),
        "distinct_first_bytes": len(first_bytes),
        "zero_padding_targets": padding,
        "unreadable": unreadable,
        "unexplained_first_bytes": dict(sorted(unexplained.items(), key=lambda kv: -kv[1])),
        "top_first_bytes": {f"{byte:02x}": count for byte, count in first_bytes.most_common(8)},
    }


def measure(elf, ranges: tuple[Body, ...], raw: bytes | None = None) -> dict:
    """The census: every relative relocation, bucketed, plus the invariants that bound it."""
    mapping = AddressMap(elf.sections, elf.loads, ranges)
    relative = [r for r in elf.relocs if r.type == R_X86_64_RELATIVE]
    rows = classify(relative, mapping)
    report_shapes = entry_prologue_shapes(rows, elf, raw)
    buckets = Counter(row.bucket for row in rows)
    other_kinds = Counter(mapping.other_loaded_kind(row.address) for row in rows if row.bucket == "other_loaded")
    slots_without_section = sum(1 for row in rows if row.slot_section is None)
    starts = frozenset(body.start for body in ranges)
    return {
        "binary": str(elf.path),
        "relative_relocs": len(relative),
        "relocations_excluded": len(elf.relocs) - len(relative),
        "documented_relative": DOCUMENTED_RELATIVE,
        "buckets": {name: buckets.get(name, 0) for name in BUCKETS},
        "other_loaded_detail": {name: other_kinds.get(name, 0) for name in OTHER_LOADED_KINDS},
        "by_slot_section": dict(Counter(row.slot_section for row in rows if row.slot_section).most_common()),
        "by_target_section": dict(Counter(name for row in rows if (name := mapping.section_name(row.address))).most_common()),
        "distinct_targets": len({row.address for row in rows}),
        "bodies": len(ranges),
        "overlapping_bodies": count_overlaps(ranges),
        "slots_without_section": slots_without_section,
        "entry_prologue_shapes": report_shapes,
        "checks": {
            "total_matches_documented": len(relative) == DOCUMENTED_RELATIVE,
            "every_relocation_classified": sum(buckets.get(n, 0) for n in BUCKETS) == len(relative),
            "entry_targets_are_body_starts": all(row.address in starts for row in rows if row.bucket == "function_entry"),
            "interior_targets_are_not_body_starts": all(
                row.address not in starts for row in rows if row.bucket == "function_interior"
            ),
            "slots_all_in_known_sections": slots_without_section == 0,
            "entry_targets_are_not_padding": report_shapes["zero_padding_targets"] == 0,
        },
    }


def load(path: Path) -> tuple[elf_shim_probe.Elf, bytes, AddressMap, int]:
    """The ELF, its bytes, the address map that answers what a target is, and the FDE count."""
    raw = path.read_bytes()
    elf = elf_shim_probe.parse_elf(path)
    eh_frame, base = eh_probe.read_section(elf, raw, ".eh_frame")
    frames = eh_probe.parse_frames(eh_frame, base)
    mapping = AddressMap(elf.sections, elf.loads, bodies(frames))
    return elf, raw, mapping, len(frames)


def run_probe(path: Path) -> dict:
    elf, raw, mapping, frame_records = load(path)
    report = measure(elf, mapping.bodies, raw)
    report["binary_sha256"] = hashlib.sha256(elf.path.read_bytes()).hexdigest()
    report["frame_records"] = frame_records
    return report


def render(report: dict) -> str:
    lines = [
        f"{report['relative_relocs']} relative relocations "
        f"(documented {report['documented_relative']}) of "
        f"{report['relative_relocs'] + report['relocations_excluded']} total in "
        f"{report['binary']}"
    ]
    for name, count in report["buckets"].items():
        share = count / report["relative_relocs"] if report["relative_relocs"] else 0.0
        lines.append(f"  {name:18s} {count:8d}  {share:6.1%}")
    detail = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in report["other_loaded_detail"].items())
    lines.append(f"  other loaded: {detail}")
    shapes = report["entry_prologue_shapes"]
    lines.append(
        f"  entry targets open on {shapes['distinct_first_bytes']} distinct first "
        f"bytes, {shapes['zero_padding_targets']} of them zero padding"
        + (", unreadable " + str(shapes["unreadable"]) if shapes["unreadable"] else "")
        + (f", unexplained {shapes['unexplained_first_bytes']}" if shapes["unexplained_first_bytes"] else "")
    )
    lines.append(
        "  slots by holding section: "
        + ", ".join(f"{name} {count}" for name, count in list(report["by_slot_section"].items())[:6])
    )
    lines.append(
        "  targets by section: " + ", ".join(f"{name} {count}" for name, count in list(report["by_target_section"].items())[:6])
    )
    lines.append(
        f"  {report.get('frame_records', report['bodies'])} .eh_frame records fold to "
        f"{report['bodies']} function bodies, "
        f"{report['overlapping_bodies']} overlap, "
        f"{report['distinct_targets']} distinct target addresses"
    )
    failed = [name for name, ok in report["checks"].items() if not ok]
    lines.append(f"  checks: {'all passed' if not failed else 'FAILED ' + ', '.join(failed)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("so", type=Path, nargs="?", default=DEFAULT_SO, help="Linux GameAssembly.so to analyse")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="artifact directory")
    ap.add_argument("--json", action="store_true", help="print the report as JSON instead of a table")
    args = ap.parse_args(argv)
    if not args.so.exists():
        print(f"no such ELF: {args.so}", file=sys.stderr)
        return 2
    report = run_probe(args.so)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render(report))
    print(f"-> {args.out / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
