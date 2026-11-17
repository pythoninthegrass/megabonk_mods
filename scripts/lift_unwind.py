"""Build the unwind tables the guest unwinder reads, from the exception metadata of a lifted set.

Every lifted body must have a frame description the unwinder can interpret. A body or frame that
does not is reported as a problem, and `render_c` refuses to emit tables for a set with problems,
so a lifted module is never linked against tables that silently stop at the wrong frame.
"""

from __future__ import annotations

import lift_eh as eh
import struct
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


def build_entries(frames: list[eh.Frame], lifted_starts: set[int], personality_of: Callable[[eh.Cie], int | None]) -> Table:
    table = Table()
    by_start = {frame.pc_begin: frame for frame in frames}
    for start in sorted(lifted_starts):
        frame = by_start.get(start)
        if frame is None:
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


def render_c(table: Table, lsda_bytes: bytes, lsda_va: int) -> str:
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
            f"const uint64_t lu_lsda_va = 0x{lsda_va:x}ULL;",
            f"const uint64_t lu_lsda_size = {len(lsda_bytes)};",
            f"const unsigned char lu_lsda_bytes[] = {{{data}}};",
            "",
        ]
    )
