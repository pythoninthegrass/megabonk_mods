"""Unwind table construction from parsed frames, and the problems that reject a lifted set."""

import lift_eh as eh
import lift_unwind as lu
import pytest
from test_lift_eh import PROLOGUE, build_cie, build_fde, section_with


def frames_for(*specs):
    cie = build_cie(b"zPLR", personality_slot=0x2000)
    data, offsets = cie, []
    for pc_begin, instructions, lsda in specs:
        fde = build_fde(0, len(data), pc_begin, 0x40, instructions, lsda)
        data += fde
    return eh.parse_frames(data, 0)


PERSONALITY = lambda cie: 0x9000  # noqa: E731


def test_entries_cover_only_lifted_bodies_in_address_order():
    frames = frames_for((0x3000, PROLOGUE, None), (0x1000, PROLOGUE, 0x5000), (0x2000, PROLOGUE, None))
    table = lu.build_entries(frames, {0x1000, 0x3000}, PERSONALITY)
    assert table.problems == []
    assert [e.pc_begin for e in table.entries] == [0x1000, 0x3000]
    first = table.entries[0]
    assert (first.pc_end, first.lsda, first.personality) == (0x1040, 0x5000, 0x9000)


def test_rows_carry_the_cfa_rule_and_saved_register_offsets():
    (entry,) = lu.build_entries(frames_for((0x1000, PROLOGUE, None)), {0x1000}, PERSONALITY).entries
    last = entry.rows[-1]
    assert (last.cfa_register, last.cfa_offset) == (7, 8)
    assert last.saved == {16: -8, 6: -16, 3: -24}


def test_a_lifted_body_without_a_frame_is_a_problem():
    table = lu.build_entries(frames_for((0x1000, PROLOGUE, None)), {0x1000, 0x2000}, PERSONALITY)
    assert table.problems == ["EH_NO_FDE:2000"]


def test_a_frame_with_an_lsda_needs_a_resolvable_personality():
    table = lu.build_entries(frames_for((0x1000, PROLOGUE, 0x5000)), {0x1000}, lambda cie: None)
    assert table.problems == ["EH_NO_PERSONALITY:1000"]


def test_a_cfa_register_other_than_rsp_or_rbp_is_a_problem():
    insns = bytes([0x41, 0x0D, 3])  # cfa from rbx
    table = lu.build_entries(frames_for((0x1000, insns, None)), {0x1000}, PERSONALITY)
    assert table.problems == ["EH_CFA_REGISTER:1000"]


def test_an_unsupported_cfi_opcode_is_reported_with_its_name():
    insns = bytes([0x0F, 1, 0x00])
    (problem,) = lu.build_entries(frames_for((0x1000, insns, None)), {0x1000}, PERSONALITY).problems
    assert problem.startswith("EH_CFI:1000:") and "def_cfa_expression" in problem


def test_rendered_tables_declare_counts_rows_and_lsda_bytes():
    table = lu.build_entries(frames_for((0x1000, PROLOGUE, 0x5000)), {0x1000}, PERSONALITY)
    source = lu.render_c(table, lsda_bytes=b"\x01\x02\x03", lsda_va=0x5000)
    assert "const uint32_t lu_fde_count = 1;" in source
    assert "{0x1000ULL, 0x1040ULL, 0x5000ULL, 0x9000ULL, 0, 5}" in source
    assert "const uint64_t lu_lsda_va = 0x5000ULL;" in source
    assert "0x01, 0x02, 0x03" in source


def test_rendering_refuses_a_table_with_problems():
    table = lu.build_entries(frames_for((0x1000, PROLOGUE, None)), {0x1000, 0x2000}, PERSONALITY)
    with pytest.raises(lu.UnwindTableError, match="EH_NO_FDE"):
        lu.render_c(table, lsda_bytes=b"", lsda_va=0)
