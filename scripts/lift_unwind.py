"""Build the unwind tables the guest unwinder reads, from the exception metadata of a lifted set.

Every lifted body must have a frame description the unwinder can interpret. A body or frame that
does not is reported as a problem, and `render_c` refuses to emit tables for a set with problems,
so a lifted module is never linked against tables that silently stop at the wrong frame.
"""

from __future__ import annotations

import lift_eh as eh
import struct
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

CFA_REGISTERS = (6, 7)
SAVED_REGISTER_LIMIT = 17
R_X86_64_64, R_X86_64_RELATIVE = 1, 8


class UnwindTableError(RuntimeError):
    """The lifted set has frames the guest unwinder cannot represent."""


@dataclass(frozen=True)
class Entry:
    pc_begin: int
    pc_end: int
    lsda: int
    personality: int
    rows: tuple


@dataclass
class Table:
    entries: list = field(default_factory=list)
    problems: list = field(default_factory=list)


def is_leaf(fn: dict) -> bool:
    """True when the body calls nothing and leaves only by returning, so it can never sit between a throw and its handler."""
    lo, hi = fn["start"], fn["start"] + fn["size"]
    for insn in fn["insns"]:
        for op in insn["ops"]:
            name = op["op"]
            if name in ("CALL", "CALLIND", "BRANCHIND"):
                return False
            if name in ("BRANCH", "CBRANCH"):
                space, offset = op["in"][0].split(",")[:2]
                if space == "ram" and not lo <= int(offset, 16) < hi:
                    return False
    return True


def address_bias(rows: list[dict]) -> int:
    """The constant the dump adds to every return address a CALL pushes, as the gap to the real next address.

    Raw pcode pushes the Ghidra-space address, while the exception tables use file addresses, so the
    unwinder subtracts this before looking a frame up. All calls must agree, or the tables are refused.
    """
    gaps = set()
    for row in rows:
        for insn in row["insns"]:
            ops = insn["ops"]
            for before, op in zip(ops, ops[1:]):
                if before["op"] == "STORE" and op["op"] in ("CALL", "CALLIND"):
                    space, value = before["in"][2].split(",")[:2]
                    if space == "const":
                        gaps.add(int(value, 16) - (insn["a"] + insn["len"]))
    if len(gaps) > 1:
        raise UnwindTableError(f"return address bias is inconsistent: {sorted(hex(g) for g in gaps)}")
    return gaps.pop() if gaps else 0


def build_entries(
    frames: list[eh.Frame],
    lifted_starts: set[int],
    personality_of: Callable[[eh.Cie], int | None],
    leaves: frozenset | set = frozenset(),
) -> Table:
    table = Table()
    by_start = {frame.pc_begin: frame for frame in frames}
    for start in sorted(lifted_starts):
        frame = by_start.get(start)
        if frame is None:
            if start not in leaves:
                table.problems.append(f"EH_NO_FDE:{start:x}")
            continue
        try:
            rows = eh.cfi_rows(frame)
        except eh.EhUnsupported as error:
            table.problems.append(f"EH_CFI:{start:x}:{error}")
            continue
        if any(row.cfa_register not in CFA_REGISTERS for row in rows):
            table.problems.append(f"EH_CFA_REGISTER:{start:x}")
            continue
        if any(reg >= SAVED_REGISTER_LIMIT for row in rows for reg in row.saved):
            table.problems.append(f"EH_SAVED_REGISTER:{start:x}")
            continue
        personality = personality_of(frame.cie)
        if frame.lsda and not personality:
            table.problems.append(f"EH_NO_PERSONALITY:{start:x}")
            continue
        table.entries.append(Entry(start, start + frame.pc_range, frame.lsda or 0, personality or 0, tuple(rows)))
    return table


def account(
    frames: list[eh.Frame],
    except_table: bytes,
    except_base: int,
    personality_of: Callable[[eh.Cie], int | None],
    allowed_personalities: set[int],
    lo: int,
    hi: int,
) -> dict:
    """Accounts for every frame in [lo, hi): supported, or rejected under the first reason that applies."""
    rejected: Counter = Counter()
    personalities: Counter = Counter()
    report = {"bodies": 0, "supported": 0, "with_lsda": 0, "pad_entries": 0, "distinct_pads": 0}
    for frame in frames:
        if not lo <= frame.pc_begin < hi:
            continue
        report["bodies"] += 1
        try:
            rows = eh.cfi_rows(frame)
        except eh.EhUnsupported:
            rejected["EH_CFI"] += 1
            continue
        if any(row.cfa_register not in CFA_REGISTERS for row in rows):
            rejected["EH_CFA_REGISTER"] += 1
            continue
        if any(reg >= SAVED_REGISTER_LIMIT for row in rows for reg in row.saved):
            rejected["EH_SAVED_REGISTER"] += 1
            continue
        if not frame.lsda:
            report["supported"] += 1
            continue
        report["with_lsda"] += 1
        try:
            personality = personality_of(frame.cie)
        except eh.EhUnsupported:
            personality = None
        if not personality:
            rejected["EH_NO_PERSONALITY"] += 1
            continue
        if personality not in allowed_personalities:
            rejected["EH_PERSONALITY_UNKNOWN"] += 1
            continue
        try:
            lsda = eh.parse_lsda(except_table, frame.lsda - except_base, frame.pc_begin)
        except eh.EhUnsupported:
            rejected["EH_LSDA"] += 1
            continue
        if any(not frame.pc_begin <= pad < frame.pc_begin + frame.pc_range for pad in lsda.pads):
            rejected["EH_PAD_OUTSIDE"] += 1
            continue
        personalities[hex(personality)] += 1
        report["pad_entries"] += sum(1 for site in lsda.sites if site.pad)
        report["distinct_pads"] += len(lsda.pads)
        report["supported"] += 1
    report["rejected"] = dict(rejected)
    report["personalities"] = dict(personalities)
    return report


def dumped_pad_check(rows: list[dict], frames: list[eh.Frame], except_table: bytes, except_base: int) -> dict:
    """Counts landing pads that are not instruction starts in dumped pcode rows, over the bodies that have an LSDA."""
    by_start = {frame.pc_begin: frame for frame in frames}
    report = {"bodies": 0, "with_lsda": 0, "pads": 0, "missing": 0, "bodies_with_missing": 0}
    for row in rows:
        report["bodies"] += 1
        frame = by_start.get(row["start"])
        if frame is None or not frame.lsda:
            continue
        report["with_lsda"] += 1
        lsda = eh.parse_lsda(except_table, frame.lsda - except_base, row["start"])
        missing = len(eh.pad_holes(row, lsda))
        report["pads"] += len(lsda.pads)
        report["missing"] += missing
        report["bodies_with_missing"] += bool(missing)
    return report


def personality_resolver(elf, raw: bytes):
    """Maps a CIE to the guest address of its personality routine through the slot's relocation."""
    dynsym = next((s for s in elf.sections if s.name == ".dynsym"), None)
    relocs = {r.offset: r for r in elf.relocs}

    def resolve(cie: eh.Cie) -> int | None:
        if cie.personality_slot is None:
            return None
        reloc = relocs.get(cie.personality_slot)
        if reloc is None:
            raise eh.EhUnsupported(f"personality slot {cie.personality_slot:#x} has no relocation")
        if reloc.type == R_X86_64_RELATIVE:
            return reloc.addend
        if reloc.type == R_X86_64_64 and dynsym is not None:
            value = struct.unpack_from("<Q", raw, dynsym.offset + reloc.sym * 24 + 8)[0]
            return value + reloc.addend if value else None
        raise eh.EhUnsupported(f"personality relocation type {reloc.type} is not supported")

    return resolve


def render_c(table: Table, lsda_bytes: bytes, lsda_va: int, address_bias: int = 0) -> str:
    if table.problems:
        raise UnwindTableError(f"unwind tables have {len(table.problems)} problems: {table.problems[:5]}")
    rows, fdes = [], []
    for entry in table.entries:
        fdes.append(
            f"  {{0x{entry.pc_begin:x}ULL, 0x{entry.pc_end:x}ULL, 0x{entry.lsda:x}ULL, 0x{entry.personality:x}ULL, "
            f"{len(rows)}, {len(entry.rows)}}},"
        )
        for row in entry.rows:
            mask = sum(1 << reg for reg in row.saved)
            saved = ", ".join(str(row.saved.get(reg, 0)) for reg in range(SAVED_REGISTER_LIMIT))
            rows.append(f"  {{0x{row.pc:x}ULL, {row.cfa_offset}, {row.cfa_register}, 0x{mask:x}, {{{saved}}}}},")
    data = ", ".join(f"0x{b:02x}" for b in lsda_bytes) or "0"
    return "\n".join(
        [
            '#include "lift_unwind.h"',
            f"const uint32_t lu_fde_count = {len(fdes)};",
            "const lu_fde lu_fdes[] = {" + ("\n" + "\n".join(fdes) + "\n" if fdes else "{0}") + "};",
            "const lu_row lu_rows[] = {" + ("\n" + "\n".join(rows) + "\n" if rows else "{0}") + "};",
            f"const uint64_t lu_address_bias = 0x{address_bias:x}ULL;",
            f"const uint64_t lu_lsda_va = 0x{lsda_va:x}ULL;",
            f"const uint64_t lu_lsda_size = {len(lsda_bytes)};",
            f"const unsigned char lu_lsda_bytes[] = {{{data}}};",
            "",
        ]
    )
