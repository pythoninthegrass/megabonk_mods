"""Unit tests for the exception metadata the lifter and guest unwinder consume."""

import lift_eh as eh
import pytest
import struct


def uleb(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def sleb(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        done = (value == 0 and not byte & 0x40) or (value == -1 and byte & 0x40)
        out.append(byte if done else byte | 0x80)
        if done:
            return bytes(out)


def pad8(body):
    body += b"\0" * (-(len(body) + 4) % 8)
    return struct.pack("<I", len(body)) + body


CIE_INITIAL = bytes([0x0C, 7, 8, 0x90, 1])  # def_cfa rsp+8; return address at cfa-8


def build_cie(augmentation=b"zR", initial=CIE_INITIAL, personality_slot=None):
    aug_data = b""
    for char in augmentation[1:]:
        if char == ord("P"):
            aug_data += bytes([0x1B]) + struct.pack("<i", personality_slot)
        elif char == ord("L") or char == ord("R"):
            aug_data += bytes([0x1B])
    body = struct.pack("<I", 0) + b"\x01" + augmentation + b"\0" + uleb(1) + sleb(-8) + b"\x10"
    body += uleb(len(aug_data)) + aug_data + initial
    return pad8(body)


def build_fde(cie_offset, entry_offset, pc_begin, pc_range, instructions, lsda=None, base=0):
    field = entry_offset + 4
    body = struct.pack("<I", field - cie_offset)
    body += struct.pack("<i", pc_begin - (base + field + 4))
    body += struct.pack("<I", pc_range)
    if lsda is None:
        body += uleb(0)
    else:
        lsda_field = base + field + len(body) + 1
        body += uleb(4) + struct.pack("<i", lsda - lsda_field)
    return pad8(body + instructions)


PROLOGUE = (
    bytes([0x41, 0x0E, 16, 0x86, 2])  # advance 1: cfa=rsp+16, rbp saved at cfa-16
    + bytes([0x43, 0x0D, 6])  # advance 3: cfa=rbp+16
    + bytes([0x45, 0x83, 3])  # advance 5: rbx saved at cfa-24
    + bytes([0x44, 0x0C, 7, 8])  # advance 4: cfa=rsp+8 (epilogue)
)


def section_with(instructions, pc_begin=0x1000, pc_range=0x40, augmentation=b"zR", lsda=None, slot=0x2000):
    cie = build_cie(augmentation, personality_slot=None if b"P" not in augmentation else slot)
    fde = build_fde(0, len(cie), pc_begin, pc_range, instructions, lsda)
    return cie + fde


def test_frame_carries_range_lsda_and_the_personality_slot():
    data = section_with(PROLOGUE, augmentation=b"zPLR", lsda=0x3000)
    (frame,) = eh.parse_frames(data, 0)
    assert (frame.pc_begin, frame.pc_range, frame.lsda) == (0x1000, 0x40, 0x3000)
    assert frame.cie.augmentation == "zPLR"
    assert frame.cie.personality_slot is not None
    assert (frame.cie.code_alignment, frame.cie.data_alignment, frame.cie.return_register) == (1, -8, 16)


def test_cfi_rows_follow_the_prologue_and_epilogue():
    (frame,) = eh.parse_frames(section_with(PROLOGUE), 0)
    rows = eh.cfi_rows(frame)
    assert [r.pc for r in rows] == [0x1000, 0x1001, 0x1004, 0x1009, 0x100D]
    assert (rows[0].cfa_register, rows[0].cfa_offset, rows[0].saved) == (7, 8, {16: -8})
    assert (rows[1].cfa_register, rows[1].cfa_offset, rows[1].saved) == (7, 16, {16: -8, 6: -16})
    assert (rows[2].cfa_register, rows[2].cfa_offset) == (6, 16)
    assert rows[3].saved == {16: -8, 6: -16, 3: -24}
    assert (rows[4].cfa_register, rows[4].cfa_offset) == (7, 8)
    assert rows[4].saved == {16: -8, 6: -16, 3: -24}


def test_row_lookup_uses_the_last_row_at_or_before_pc():
    (frame,) = eh.parse_frames(section_with(PROLOGUE), 0)
    rows = eh.cfi_rows(frame)
    assert eh.row_at(rows, 0x1000).cfa_offset == 8
    assert eh.row_at(rows, 0x1003).cfa_offset == 16
    assert eh.row_at(rows, 0x1005).cfa_register == 6
    with pytest.raises(eh.EhUnsupported, match="outside"):
        eh.row_at(rows, 0xFFF)


def test_remember_and_restore_state_bracket_a_nested_epilogue():
    insns = bytes([0x41, 0x0E, 16, 0x86, 2, 0x0A, 0x42, 0x0E, 8, 0x41, 0x0B, 0x41, 0x0E, 24])
    (frame,) = eh.parse_frames(section_with(insns), 0)
    rows = eh.cfi_rows(frame)
    assert eh.row_at(rows, 0x1001).cfa_offset == 16
    assert eh.row_at(rows, 0x1003).cfa_offset == 8
    assert eh.row_at(rows, 0x1004).cfa_offset == 16
    assert eh.row_at(rows, 0x1005).cfa_offset == 24


def test_restore_reverts_a_register_to_the_cie_rule():
    insns = bytes([0x41, 0x86, 2, 0x41, 0xC6])  # offset rbp, then restore rbp
    (frame,) = eh.parse_frames(section_with(insns), 0)
    rows = eh.cfi_rows(frame)
    assert 6 in eh.row_at(rows, 0x1001).saved
    assert 6 not in eh.row_at(rows, 0x1002).saved


@pytest.mark.parametrize(
    "instructions, name",
    [
        (bytes([0x0F, 1, 0x00]), "def_cfa_expression"),
        (bytes([0x10, 3, 1, 0x00]), "expression"),
        (bytes([0x16, 3, 1, 0x00]), "val_expression"),
        (bytes([0x2F, 3, 1]), "GNU_negative_offset_extended"),
    ],
)
def test_unsupported_cfi_opcodes_are_rejected_by_name(instructions, name):
    (frame,) = eh.parse_frames(section_with(instructions), 0)
    with pytest.raises(eh.EhUnsupported, match=name):
        eh.cfi_rows(frame)


def test_args_size_is_accepted_because_it_does_not_move_the_cfa():
    (frame,) = eh.parse_frames(section_with(bytes([0x2E, 8])), 0)
    assert eh.cfi_rows(frame)[0].cfa_offset == 8


def test_unknown_augmentation_is_rejected():
    data = build_cie(b"zRS") + b""
    with pytest.raises(eh.EhUnsupported, match="augmentation"):
        eh.parse_frames(data, 0)


def lsda_bytes(sites, call_site_encoding=0x01, ttype=False, lpstart=None):
    table = b"".join(uleb(s) + uleb(n) + uleb(p) + uleb(a) for s, n, p, a in sites)
    header = bytes([0xFF if lpstart is None else 0x01]) + (b"" if lpstart is None else uleb(lpstart))
    header += bytes([0xFF]) if not ttype else bytes([0x9C]) + uleb(0)
    return header + bytes([call_site_encoding]) + uleb(len(table)) + table


def test_lsda_sites_resolve_pads_from_the_function_start():
    table = lsda_bytes([(0, 4, 0x20, 0), (4, 6, 0x30, 1), (10, 2, 0, 0), (12, 3, 0x20, 0)])
    lsda = eh.parse_lsda(table, 0, func_start=0x1000)
    assert [(s.start, s.length, s.pad, s.action) for s in lsda.sites] == [
        (0x1000, 4, 0x1020, 0),
        (0x1004, 6, 0x1030, 1),
        (0x100A, 2, 0, 0),
        (0x100C, 3, 0x1020, 0),
    ]
    assert lsda.pads == {0x1020, 0x1030}


def test_lsda_rejects_an_explicit_lpstart():
    table = lsda_bytes([(0, 4, 0x20, 0)], lpstart=0x10)
    with pytest.raises(eh.EhUnsupported, match="LPStart"):
        eh.parse_lsda(table, 0, func_start=0x1000)


def test_lsda_rejects_a_table_that_overruns_its_bytes():
    table = lsda_bytes([(0, 4, 0x20, 0)])[:-1]
    with pytest.raises(eh.EhUnsupported, match="call-site table"):
        eh.parse_lsda(table, 0, func_start=0x1000)


def insn_rows(*addresses):
    return {
        "start": min(addresses),
        "size": max(addresses) - min(addresses) + 0x40,
        "insns": [{"a": a, "len": 1, "ops": []} for a in addresses],
    }


def test_pad_validation_names_a_pad_that_is_not_an_instruction_start():
    fn = insn_rows(0x1000, 0x1001, 0x1020)
    table = lsda_bytes([(0, 1, 0x20, 0), (1, 1, 0x21, 0)])
    lsda = eh.parse_lsda(table, 0, func_start=0x1000)
    assert eh.pad_holes(fn, lsda) == ["EH_PAD_NOT_INSN"]


def test_pad_validation_names_a_pad_outside_the_body():
    fn = insn_rows(0x1000, 0x1001)
    lsda = eh.parse_lsda(lsda_bytes([(0, 1, 0x500, 0)]), 0, func_start=0x1000)
    assert eh.pad_holes(fn, lsda) == ["EH_PAD_OUTSIDE"]


def test_pad_validation_is_clean_when_every_pad_is_an_instruction_start():
    fn = insn_rows(0x1000, 0x1001, 0x1020)
    lsda = eh.parse_lsda(lsda_bytes([(0, 1, 0x20, 0)]), 0, func_start=0x1000)
    assert eh.pad_holes(fn, lsda) == []


def test_a_zero_length_terminator_between_objects_does_not_end_the_section():
    cie = build_cie()
    first = build_fde(0, len(cie), 0x1000, 0x40, PROLOGUE)
    second_offset = len(cie) + len(first) + 4
    second = build_fde(0, second_offset, 0x2000, 0x20, PROLOGUE)
    frames = eh.parse_frames(cie + first + b"\0\0\0\0" + second, 0)
    assert [f.pc_begin for f in frames] == [0x1000, 0x2000]


def hand_lsda(action: int, action_records: bytes, ttype_entries: bytes) -> bytes:
    """One call site (start 0, size 5, pad 5, `action`), then the action records and the type table."""
    body = bytes([0x01, 0x04, 0, 5, 5, action]) + action_records + ttype_entries
    return bytes([0xFF, 0x9B, len(body)]) + body


def test_a_catch_all_filter_has_a_null_type_entry_and_is_not_typed():
    lsda = hand_lsda(1, bytes([1, 0]), struct.pack("<i", 0))
    assert eh.type_filters(lsda, 0) == eh.TypeFilters(frozenset(), frozenset())


def test_a_filter_with_a_nonzero_type_entry_is_a_typed_catch():
    lsda = hand_lsda(1, bytes([1, 0]), struct.pack("<i", 0x100))
    assert eh.type_filters(lsda, 0) == eh.TypeFilters(frozenset({1}), frozenset())


def test_a_cleanup_only_site_has_no_filters():
    lsda = hand_lsda(0, b"", b"")
    assert eh.type_filters(lsda, 0) == eh.TypeFilters(frozenset(), frozenset())


def test_a_negative_filter_is_an_exception_specification():
    lsda = hand_lsda(1, sleb(-1) + bytes([0]), struct.pack("<i", 0x100))
    assert eh.type_filters(lsda, 0) == eh.TypeFilters(frozenset(), frozenset({-1}))


def test_a_chain_of_records_is_followed_to_its_end():
    records = bytes([1, 1]) + bytes([2, 0])
    lsda = hand_lsda(1, records, struct.pack("<ii", 0x200, 0))
    assert eh.type_filters(lsda, 0) == eh.TypeFilters(frozenset({2}), frozenset())
