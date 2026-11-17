"""Exception metadata for lifted code: frame descriptions, call-frame rows and landing pads.

Reads the same `.eh_frame` and `.gcc_except_table` bytes as `eh_probe.py`, but keeps what the
census discards: each frame's call-frame instructions and each call-site's landing pad and action.
Anything outside the shapes the guest unwinder implements raises `EhUnsupported`, so a caller
rejects the body instead of emitting code that only looks runnable.
"""

from __future__ import annotations

import eh_probe as eh
import struct
from dataclasses import dataclass, field

SUPPORTED_AUGMENTATIONS = ("zR", "zPLR")
DW_CFA_ADVANCE_LOC, DW_CFA_OFFSET, DW_CFA_RESTORE = 0x40, 0x80, 0xC0
CFA_OPCODE_NAMES = {
    0x0F: "def_cfa_expression",
    0x10: "expression",
    0x16: "val_expression",
    0x2F: "GNU_negative_offset_extended",
    0x11: "offset_extended_sf",
    0x12: "def_cfa_sf",
    0x13: "def_cfa_offset_sf",
    0x14: "val_offset",
    0x15: "val_offset_sf",
}


class EhUnsupported(RuntimeError):
    """The metadata uses a shape the lifted unwinder does not implement."""


@dataclass(frozen=True)
class Cie:
    offset: int
    augmentation: str
    code_alignment: int
    data_alignment: int
    return_register: int
    lsda_encoding: int | None
    pointer_encoding: int
    personality_slot: int | None
    initial: bytes


@dataclass(frozen=True)
class Frame:
    pc_begin: int
    pc_range: int
    lsda: int | None
    cie: Cie
    instructions: bytes


@dataclass(frozen=True)
class Row:
    pc: int
    cfa_register: int
    cfa_offset: int
    saved: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Site:
    start: int
    length: int
    pad: int
    action: int


@dataclass(frozen=True)
class Lsda:
    sites: tuple
    pads: frozenset
    has_ttype: bool


def _guard(call, *args, **kwargs):
    try:
        return call(*args, **kwargs)
    except eh.EhError as error:
        raise EhUnsupported(str(error)) from None


def _parse_cie(offset: int, body: bytes, base: int) -> Cie:
    pos = 5
    end = body.index(0, pos)
    augmentation = body[pos:end].decode("ascii", "replace")
    pos = end + 1
    if augmentation not in SUPPORTED_AUGMENTATIONS:
        raise EhUnsupported(f"CIE augmentation {augmentation!r} is not supported")
    code_alignment, pos = _guard(eh.read_uleb128, body, pos)
    data_alignment, pos = _guard(eh.read_sleb128, body, pos)
    return_register = body[pos]
    pos += 1
    aug_len, pos = _guard(eh.read_uleb128, body, pos)
    aug, initial = body[pos : pos + aug_len], body[pos + aug_len :]
    cursor = 0
    lsda_encoding = pointer_encoding = personality_slot = None
    for char in augmentation[1:]:
        if char == "P":
            encoding = aug[cursor]
            cursor += 1
            personality_slot, cursor = _guard(
                eh.read_encoded_pointer, aug, cursor, encoding, base=base + offset + 4 + pos + cursor, resolve=False
            )
        elif char == "L":
            lsda_encoding = aug[cursor]
            cursor += 1
        else:
            pointer_encoding = aug[cursor]
            cursor += 1
    return Cie(
        offset,
        augmentation,
        code_alignment,
        data_alignment,
        return_register,
        lsda_encoding,
        pointer_encoding,
        personality_slot,
        initial,
    )


def parse_frames(section: bytes, base: int = 0) -> list[Frame]:
    """Every FDE in an `.eh_frame` section, each with its CIE and call-frame instructions."""
    entries = list(_guard(lambda: list(eh._entries(section))))
    cies = {}
    for offset, body in entries:
        if struct.unpack_from("<I", body, 0)[0] == 0:
            cies[offset] = _parse_cie(offset, body, base)
    frames = []
    for offset, body in entries:
        field_value = struct.unpack_from("<I", body, 0)[0]
        if field_value == 0:
            continue
        cie = cies.get(eh.cie_offset_of(offset, field_value))
        if cie is None:
            raise EhUnsupported(f"FDE at {offset:#x} names an absent CIE")
        pos = 4
        pc_begin, pos = _guard(eh.read_encoded_pointer, body, pos, cie.pointer_encoding, base=base + offset + 4 + pos)
        pc_range, pos = _guard(eh.read_encoded_pointer, body, pos, cie.pointer_encoding & 0x0F)
        aug_len, pos = _guard(eh.read_uleb128, body, pos)
        lsda = None
        if aug_len and cie.lsda_encoding not in (None, eh.DW_EH_PE_omit):
            lsda, _ = _guard(eh.read_encoded_pointer, body, pos, cie.lsda_encoding, base=base + offset + 4 + pos)
            lsda = lsda or None
        frames.append(Frame(pc_begin, pc_range, lsda, cie, body[pos + aug_len :]))
    return frames


def _run(instructions: bytes, cie: Cie, state: dict, stack: list, initial: dict | None, pc: int, rows: list | None) -> int:
    pos = 0
    while pos < len(instructions):
        op = instructions[pos]
        pos += 1
        high, low = op & 0xC0, op & 0x3F
        if high == DW_CFA_ADVANCE_LOC:
            delta = low
        elif op == 0x02:
            delta, pos = instructions[pos], pos + 1
        elif op == 0x03:
            delta, pos = struct.unpack_from("<H", instructions, pos)[0], pos + 2
        elif op == 0x04:
            delta, pos = struct.unpack_from("<I", instructions, pos)[0], pos + 4
        else:
            delta = None
        if delta is not None:
            if rows is not None:
                rows.append(Row(pc, state["reg"], state["off"], dict(state["saved"])))
            pc += delta * cie.code_alignment
            continue
        if high == DW_CFA_OFFSET:
            value, pos = _guard(eh.read_uleb128, instructions, pos)
            state["saved"][low] = value * cie.data_alignment
        elif high == DW_CFA_RESTORE:
            _restore(state, low, initial)
        elif op == 0x00:
            pass
        elif op == 0x2E:
            _, pos = _guard(eh.read_uleb128, instructions, pos)
        elif op == 0x05:
            reg, pos = _guard(eh.read_uleb128, instructions, pos)
            value, pos = _guard(eh.read_uleb128, instructions, pos)
            state["saved"][reg] = value * cie.data_alignment
        elif op == 0x06:
            reg, pos = _guard(eh.read_uleb128, instructions, pos)
            _restore(state, reg, initial)
        elif op in (0x07, 0x08):
            reg, pos = _guard(eh.read_uleb128, instructions, pos)
            state["saved"].pop(reg, None)
        elif op == 0x0A:
            stack.append((state["reg"], state["off"], dict(state["saved"])))
        elif op == 0x0B:
            state["reg"], state["off"], saved = stack.pop()
            state["saved"] = dict(saved)
        elif op == 0x0C:
            state["reg"], pos = _guard(eh.read_uleb128, instructions, pos)
            state["off"], pos = _guard(eh.read_uleb128, instructions, pos)
        elif op == 0x0D:
            state["reg"], pos = _guard(eh.read_uleb128, instructions, pos)
        elif op == 0x0E:
            state["off"], pos = _guard(eh.read_uleb128, instructions, pos)
        else:
            name = CFA_OPCODE_NAMES.get(op, f"opcode_{op:#04x}")
            raise EhUnsupported(f"call-frame instruction {name} is not supported")
    return pc


def _restore(state: dict, reg: int, initial: dict | None) -> None:
    if initial is not None and reg in initial:
        state["saved"][reg] = initial[reg]
    else:
        state["saved"].pop(reg, None)


def cfi_rows(frame: Frame) -> list[Row]:
    """The frame's unwind rules as rows, each valid from its pc to the next row's pc."""
    cie = frame.cie
    state = {"reg": 7, "off": 8, "saved": {}}
    _run(cie.initial, cie, state, [], None, frame.pc_begin, None)
    initial = dict(state["saved"])
    rows: list[Row] = []
    pc = _run(frame.instructions, cie, state, [], initial, frame.pc_begin, rows)
    rows.append(Row(pc, state["reg"], state["off"], dict(state["saved"])))
    if not rows or rows[0].pc != frame.pc_begin:
        raise EhUnsupported("call-frame rows do not start at the function start")
    return rows


def row_at(rows: list[Row], pc: int) -> Row:
    if pc < rows[0].pc:
        raise EhUnsupported(f"pc {pc:#x} is outside the frame")
    chosen = rows[0]
    for row in rows:
        if row.pc <= pc:
            chosen = row
    return chosen


def parse_lsda(table: bytes, at: int, func_start: int) -> Lsda:
    """Reads one LSDA: call-site records with landing pads resolved against the function start."""
    pos = at
    lpstart, pos = _guard(eh._byte, table, pos)
    if lpstart != eh.DW_EH_PE_omit:
        raise EhUnsupported("an explicit LPStart is not supported")
    ttype, pos = _guard(eh._byte, table, pos)
    if ttype != eh.DW_EH_PE_omit:
        _, pos = _guard(eh.read_uleb128, table, pos)
    encoding, pos = _guard(eh._byte, table, pos)
    length, pos = _guard(eh.read_uleb128, table, pos)
    end = pos + length
    if end > len(table):
        raise EhUnsupported("call-site table runs past the end of the exception table")
    sites = []
    while pos < end:
        start, pos = _guard(eh.read_call_site_field, table, pos, encoding)
        size, pos = _guard(eh.read_call_site_field, table, pos, encoding)
        pad, pos = _guard(eh.read_call_site_field, table, pos, encoding)
        action, pos = _guard(eh.read_uleb128, table, pos)
        if pos > end:
            raise EhUnsupported("call-site table's last record runs past its length")
        sites.append(Site(func_start + start, size, func_start + pad if pad else 0, action))
    if pos != end:
        raise EhUnsupported("call-site table does not fill its length")
    return Lsda(tuple(sites), frozenset(s.pad for s in sites if s.pad), ttype != eh.DW_EH_PE_omit)


def pad_holes(fn: dict, lsda: Lsda) -> list[str]:
    """Hole names for landing pads that are not instruction starts inside the body."""
    starts = {insn["a"] for insn in fn["insns"]}
    lo, hi = fn["start"], fn["start"] + fn["size"]
    holes = []
    for pad in sorted(lsda.pads):
        if not lo <= pad < hi:
            holes.append("EH_PAD_OUTSIDE")
        elif pad not in starts:
            holes.append("EH_PAD_NOT_INSN")
    return holes
