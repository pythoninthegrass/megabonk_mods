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


def test_a_call_free_body_without_a_frame_is_accepted_as_a_leaf():
    table = lu.build_entries(frames_for((0x1000, PROLOGUE, None)), {0x1000, 0x2000}, PERSONALITY, leaves={0x2000})
    assert table.problems == []
    assert [e.pc_begin for e in table.entries] == [0x1000]


def test_a_body_with_calls_is_not_excused_by_the_leaf_set_when_it_is_missing_from_it():
    table = lu.build_entries(frames_for((0x1000, PROLOGUE, None)), {0x1000, 0x2000}, PERSONALITY, leaves={0x3000})
    assert table.problems == ["EH_NO_FDE:2000"]


def fn(*ops, start=0x1000, size=0x10):
    return {"start": start, "size": size, "insns": [{"a": start, "len": 1, "ops": list(ops)}]}


def op(name, *ins):
    return {"op": name, "out": None, "in": list(ins)}


@pytest.mark.parametrize(
    "ops, leaf",
    [
        ([op("COPY")], True),
        ([op("BRANCH", "ram,1005,8")], True),
        ([op("CBRANCH", "ram,1008,8", "register,0,1")], True),
        ([op("CALL", "ram,2000,8")], False),
        ([op("CALLIND", "register,0,8")], False),
        ([op("BRANCHIND", "register,0,8")], False),
        ([op("BRANCH", "ram,3000,8")], False),
        ([op("CBRANCH", "ram,3000,8", "register,0,1")], False),
    ],
)
def test_leaf_detection_needs_no_call_and_no_branch_leaving_the_body(ops, leaf):
    assert lu.is_leaf(fn(*ops)) is leaf


def call_row(address, length, pushed):
    return {
        "a": address,
        "len": length,
        "ops": [
            op("INT_SUB"),
            {"op": "STORE", "out": None, "in": ["const,1b1,8", "register,20,8", f"const,{pushed:x},8"]},
            op("CALL", "ram,2000,8"),
        ],
    }


def test_return_address_bias_is_the_gap_between_pushed_constants_and_real_addresses():
    rows = [
        {"start": 0x1000, "size": 0x20, "insns": [call_row(0x1000, 5, 0x101005), call_row(0x1010, 5, 0x101015)]},
        {"start": 0x2000, "size": 0x20, "insns": [call_row(0x2004, 5, 0x102009)]},
    ]
    assert lu.address_bias(rows) == 0x100000


def test_bias_is_zero_when_no_body_calls():
    assert lu.address_bias([fn(op("COPY"))]) == 0


def test_inconsistent_return_address_bias_is_an_error():
    rows = [{"start": 0x1000, "size": 0x20, "insns": [call_row(0x1000, 5, 0x101005), call_row(0x1010, 5, 0x1015)]}]
    with pytest.raises(lu.UnwindTableError, match="bias"):
        lu.address_bias(rows)


def test_rendered_tables_carry_the_address_bias():
    table = lu.build_entries(frames_for((0x1000, PROLOGUE, None)), {0x1000}, PERSONALITY)
    source = lu.render_c(table, lsda_bytes=b"", lsda_va=0, address_bias=0x100000)
    assert "const uint64_t lu_address_bias = 0x100000ULL;" in source


def lsda_table(sites):
    from test_lift_eh import lsda_bytes

    return lsda_bytes(sites)


def test_accounting_counts_bodies_pads_and_personalities():
    frames = frames_for((0x1000, PROLOGUE, 0x0), (0x2000, PROLOGUE, 0x40))
    table = lsda_table([(0, 4, 0x10, 0), (4, 4, 0x20, 1), (8, 2, 0, 0)])
    report = lu.account(frames, table, 0x40, PERSONALITY, allowed_personalities={0x9000}, lo=0x1000, hi=0x3000)
    assert report["bodies"] == 2
    assert report["with_lsda"] == 1
    assert (report["pad_entries"], report["distinct_pads"]) == (2, 2)
    assert report["personalities"] == {"0x9000": 1}
    assert report["rejected"] == {}
    assert report["supported"] == 2


def test_accounting_rejects_an_unlisted_personality_and_a_pad_outside_the_body():
    frames = frames_for((0x2000, PROLOGUE, 0x40), (0x3000, PROLOGUE, 0x40))
    table = lsda_table([(0, 4, 0x10, 0)])
    outside = lsda_table([(0, 4, 0x900, 0)])
    report = lu.account(frames, table, 0x40, lambda cie: 0x7777, {0x9000}, 0x2000, 0x4000)
    assert report["rejected"] == {"EH_PERSONALITY_UNKNOWN": 2}
    report = lu.account(frames_for((0x2000, PROLOGUE, 0x40)), outside, 0x40, PERSONALITY, {0x9000}, 0x2000, 0x3000)
    assert report["rejected"] == {"EH_PAD_OUTSIDE": 1}
    assert report["supported"] == 0


def test_accounting_ignores_frames_outside_the_section():
    frames = frames_for((0x500, PROLOGUE, None), (0x2000, PROLOGUE, None))
    report = lu.account(frames, b"", 0, PERSONALITY, {0x9000}, 0x1000, 0x3000)
    assert report["bodies"] == 1


def test_dumped_pad_check_counts_bodies_pads_and_holes():
    frames = frames_for((0x1000, PROLOGUE, 0x40), (0x2000, PROLOGUE, 0x40))
    table = lsda_table([(0, 4, 0x10, 0), (4, 4, 0x20, 0)])
    good = {"start": 0x1000, "size": 0x40, "insns": [{"a": 0x1010, "len": 1, "ops": []}, {"a": 0x1020, "len": 1, "ops": []}]}
    bad = {"start": 0x2000, "size": 0x40, "insns": [{"a": 0x2010, "len": 1, "ops": []}]}
    report = lu.dumped_pad_check([good, bad, fn(op("COPY"), start=0x3000)], frames, table, 0x40)
    assert report == {"bodies": 3, "with_lsda": 2, "pads": 4, "missing": 1, "bodies_with_missing": 1}


def typed_table(entry, filter_=1):
    from test_lift_eh import hand_lsda, sleb

    return hand_lsda(1, sleb(filter_) + bytes([0]), entry.to_bytes(4, "little", signed=True))


def test_a_typed_catch_is_rejected_when_the_lsda_tables_are_given():
    table = lu.build_entries(
        frames_for((0x1000, PROLOGUE, 0x40)), {0x1000}, PERSONALITY, lsda_tables=[(typed_table(0x100), 0x40)]
    )
    assert table.problems == ["EH_TYPED_CATCH:1000"]
    assert table.entries == []


def test_an_exception_specification_is_rejected():
    table = lu.build_entries(
        frames_for((0x1000, PROLOGUE, 0x40)), {0x1000}, PERSONALITY, lsda_tables=[(typed_table(0x100, -1), 0x40)]
    )
    assert table.problems == ["EH_EXC_SPEC:1000"]


def test_a_catch_all_is_accepted_when_the_lsda_tables_are_given():
    table = lu.build_entries(
        frames_for((0x1000, PROLOGUE, 0x40)), {0x1000}, PERSONALITY, lsda_tables=[(typed_table(0), 0x40)]
    )
    assert table.problems == []
    assert [e.pc_begin for e in table.entries] == [0x1000]


def test_an_lsda_outside_every_given_table_is_a_problem():
    table = lu.build_entries(frames_for((0x1000, PROLOGUE, 0x9000)), {0x1000}, PERSONALITY, lsda_tables=[(b"\0" * 8, 0x40)])
    assert table.problems == ["EH_LSDA:1000"]


def test_filter_report_counts_bodies_by_the_catch_clauses_they_need():
    from test_lift_eh import hand_lsda, sleb

    def at(base, filter_, entry):
        return hand_lsda(1, sleb(filter_) + bytes([0]), entry.to_bytes(4, "little", signed=True))

    tables = [at(0, 1, 0), at(0, 1, 0x100), at(0, -1, 0x100)]
    data = b"".join(tables)
    offsets = [0x40, 0x40 + len(tables[0]), 0x40 + len(tables[0]) + len(tables[1])]
    frames = frames_for((0x1000, PROLOGUE, offsets[0]), (0x2000, PROLOGUE, offsets[1]), (0x3000, PROLOGUE, offsets[2]), (0x4000, PROLOGUE, None))
    report = lu.filter_report(frames, data, 0x40, 0x1000, 0x5000)
    assert report == {"with_lsda": 3, "catch_all_only": 1, "typed_catch": 1, "exception_spec": 1, "unreadable": 0}
