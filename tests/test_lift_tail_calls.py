"""Tests for the audit that checks the emitter's tail-call rule against Ghidra's decompiler.

Bodies are hand-built pcode records in the shape LiftDump.java writes, so the verdict rules are
checkable without Ghidra, the ELF, or the LLVM toolchain.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import lift_tail_calls as lt  # noqa: E402

SECTIONS = [
    {"name": "il2cpp", "va": 0x216_2000, "size": 0x2CC_3AB0, "exec": True},
    {"name": "rodata", "va": 0xB3_0A80, "size": 0x48_98F8, "exec": False},
    {"name": "bss", "va": 0x53_60000, "size": 0x1_0000, "exec": False},
]


def op(name, out, *ins):
    return {"op": name, "out": out, "in": list(ins)}


def insn(addr, length, *ops):
    return {"a": addr, "len": length, "m": "x", "ops": list(ops)}


def body(*insns, start=0x216_3000, size=None, jt=(), sw=None, dc=None, uw=()):
    total = size if size is not None else sum(i["len"] for i in insns)
    fn = {"start": start, "size": total, "undecoded": 0, "insns": list(insns), "jt": list(jt)}
    if sw is not None:
        fn["sw"] = sw
    if dc is not None:
        fn["dc"] = dc
    if uw:
        fn["uw"] = list(uw)
    return fn


def load_jump_body(**decompiler):
    """`jmp [rip + slot]` as the emitter sees it: the target's nearest definition is a LOAD."""
    return body(
        insn(0x216_3000, 7, op("LOAD", "register,0,8", "ram,0x53_67070,8")),
        insn(0x216_3007, 6, op("BRANCHIND", None, "register,0,8")),
        **decompiler,
    )


def scaled_table_body(**decompiler):
    """`jmp [rodata + idx*8]`: a load-defined target the tail-call rule cannot tell from a table."""
    return body(
        insn(0x216_3000, 4, op("INT_LESS", "unique,210,1", "register,208,4", "const,6,4")),
        insn(0x216_3004, 6, op("CBRANCH", None, "ram,2163040,8", "unique,210,1")),
        insn(0x216_3010, 5, op("INT_ZEXT", "unique,220,8", "register,208,4")),
        insn(0x216_3015, 4, op("INT_LEFT", "unique,228,8", "unique,220,8", "const,3,1")),
        insn(0x216_3019, 8, op("INT_ADD", "unique,230,8", "cptr,0xb3_1000,8", "unique,228,8")),
        insn(0x216_3021, 3, op("LOAD", "unique,240,8", "unique,230,8")),
        insn(0x216_3024, 3, op("BRANCHIND", None, "unique,240,8")),
        **decompiler,
    )


def two_site_body(**decompiler):
    """Two load-defined jump sites, so a table can name one and leave the other a tail call."""
    return body(
        insn(0x216_3000, 3, op("LOAD", "unique,800,8", "const,1b1,8", "register,20,8")),
        insn(0x216_3003, 3, op("BRANCHIND", None, "unique,800,8")),
        insn(0x216_3010, 7, op("LOAD", "unique,810,8", "ram,0x53_67070,8")),
        insn(0x216_3017, 6, op("BRANCHIND", None, "unique,810,8")),
        size=0x1D,
        **decompiler,
    )


def probe_row(start=0x216_3000, size=0x10, tail_calls=1, **extra):
    return {"start": start, "size": size, "holes": [], "tail_calls": tail_calls, **extra}


def table(at, *cases):
    return {"at": at, "cases": list(cases)}


def view(tables=0, cases=0, in_body=0, tables_in_body=0, switch=False, unrecoverable=(), decompiled=True):
    return {
        "tables": tables,
        "cases": cases,
        "cases_in_body": in_body,
        "tables_in_body": tables_in_body,
        "switch_in_c": switch,
        "unrecoverable": list(unrecoverable),
        "decompiled": decompiled,
    }


TAIL_SITE = [{"a": 0x216_3007, "tail_call": True, "table": False}]


def test_select_tail_rows_keeps_bodies_the_probe_counted_as_tail_calls():
    rows = [probe_row(1), probe_row(2, tail_calls=2), probe_row(3, tail_calls=0), probe_row(4)]
    rows[3].pop("tail_calls")
    assert [row["start"] for row in lt.select_tail_rows(rows)] == [1, 2]


def test_decompiler_view_counts_tables_cases_and_reads_the_switch_flag():
    fn = load_jump_body(jt=[table(0x216_3007, 0x216_3000, 0x216_3007)], sw=True, dc=True)
    assert lt.decompiler_view(fn) == view(tables=1, cases=2, in_body=2, tables_in_body=1, switch=True)


def test_decompiler_view_counts_only_the_tables_and_cases_inside_the_body():
    fn = load_jump_body(jt=[table(0x216_3900, 0x216_3900, 0x216_3908, 0x216_3000)], dc=True)
    assert lt.decompiler_view(fn) == view(tables=1, cases=3, in_body=1)


def test_decompiler_view_keeps_a_table_outside_the_body_out_of_the_evidence():
    fn = load_jump_body(jt=[table(0x216_9000, 0x216_9000, 0x216_9008)], sw=True, dc=True)
    assert lt.decompiler_view(fn) == view(tables=1, cases=2, switch=True)


def test_decompiler_view_reads_the_addresses_the_decompiler_gave_up_on():
    fn = load_jump_body(dc=True, uw=[0x216_3007, 0x216_9000])
    assert lt.decompiler_view(fn)["unrecoverable"] == [0x216_3007, 0x216_9000]


def test_decompiler_view_reads_a_dump_that_never_decompiled_the_body():
    assert lt.decompiler_view(load_jump_body()) == view(decompiled=False)


def test_verdict_agrees_when_the_decompiler_recovered_no_switch():
    assert lt.verdict(view(), TAIL_SITE) == "agrees"


def test_the_decompiler_declining_to_rebuild_a_table_is_recorded_but_not_a_verdict():
    assert lt.verdict(view(switch=False, unrecoverable=[0x216_3007]), TAIL_SITE) == "agrees"
    assert lt.verdict(view(switch=False, unrecoverable=[0x216_3007]), TAIL_SITE) != "disagrees"


def test_verdict_is_switch_beyond_body_when_only_the_keyword_points_at_a_switch():
    assert lt.verdict(view(tables=3, cases=44, switch=True), TAIL_SITE) == "switch beyond body"


def test_verdict_is_switch_beyond_body_when_no_table_was_recovered_at_all():
    assert lt.verdict(view(switch=True), TAIL_SITE) == "switch beyond body"


def test_verdict_disagrees_when_a_recovered_table_sits_on_the_tail_call_site():
    sites = [{"a": 0x216_3007, "tail_call": True, "table": True}]
    assert lt.verdict(view(tables=1, cases=6, in_body=6, tables_in_body=1, switch=True), sites) == "disagrees"


def test_positive_switch_evidence_outranks_the_decompiler_declining():
    sites = [
        {"a": 0x216_3003, "tail_call": False, "table": True},
        {"a": 0x216_3017, "tail_call": True, "table": False},
    ]
    given_up = view(tables=1, cases=4, in_body=4, tables_in_body=1, switch=True, unrecoverable=[0x216_3017])
    assert lt.verdict(given_up, sites) == "mixed"


def test_verdict_is_mixed_when_the_table_belongs_to_another_site():
    sites = [
        {"a": 0x216_3003, "tail_call": False, "table": True},
        {"a": 0x216_3017, "tail_call": True, "table": False},
    ]
    assert lt.verdict(view(tables=1, cases=4, in_body=4, tables_in_body=1, switch=True), sites) == "mixed"


def test_verdict_is_mixed_when_a_recovered_table_reaches_into_the_body():
    assert lt.verdict(view(tables=1, cases=6, in_body=6, switch=True), TAIL_SITE) == "mixed"


def test_verdict_reports_no_tail_call_when_every_site_became_a_switch():
    sites = [{"a": 0x216_3003, "tail_call": False, "table": True}]
    assert lt.verdict(view(tables=1, cases=4, in_body=4, tables_in_body=1, switch=True), sites) == "no tail call"


def test_verdict_reports_a_body_the_decompiler_never_answered():
    assert lt.verdict(view(decompiled=False), TAIL_SITE) == "not decompiled"


def test_verdicts_are_the_documented_set():
    assert lt.VERDICTS == (
        "agrees",
        "disagrees",
        "mixed",
        "no tail call",
        "switch beyond body",
        "not decompiled",
    )


def test_emitter_sites_calls_a_load_defined_target_a_tail_call():
    assert lt.emitter_sites(load_jump_body(), SECTIONS) == [
        {"a": 0x216_3007, "tail_call": True, "table": False}
    ]


def test_emitter_sites_honours_a_recovered_table_at_the_site():
    sites = lt.emitter_sites(load_jump_body(jt=[table(0x216_3007, 0x216_3010)]), SECTIONS)
    assert sites == [{"a": 0x216_3007, "tail_call": False, "table": True}]


def test_emitter_sites_calls_an_unrecovered_scaled_table_load_a_tail_call():
    assert [site["tail_call"] for site in lt.emitter_sites(scaled_table_body(), SECTIONS)] == [True]


def test_emitter_sites_counts_every_load_defined_site_of_a_body():
    assert [site["tail_call"] for site in lt.emitter_sites(two_site_body(), SECTIONS)] == [True, True]


def test_emitter_sites_excludes_sites_the_emitter_cannot_trace_to_a_load():
    fn = body(
        insn(0x216_3000, 7, op("COPY", "register,0,8", "ram,0x53_67070,8")),
        insn(0x216_3007, 6, op("BRANCHIND", None, "register,0,8")),
    )
    assert [site["tail_call"] for site in lt.emitter_sites(fn, SECTIONS)] == [False]


def test_audit_body_records_the_probe_row_and_the_decompiler_view():
    result = lt.audit_body(load_jump_body(dc=True), probe_row(), SECTIONS, {}, {})
    assert result["start"] == 0x216_3000
    assert result["size"] == 0x10
    assert result["tail_calls"] == 1
    assert result["decompiler"] == view(decompiled=True)
    assert result["verdict"] == "agrees"
    assert result["reasons"] == []
    site = result["sites"][0]
    assert site["a"] == 0x216_3007
    assert site["tail_call"] is True and site["table"] is False
    assert site["pcode"][-1].startswith("BRANCHIND")


def test_audit_body_is_mixed_when_the_recovered_switch_is_at_the_other_site():
    fn = two_site_body(jt=[table(0x216_3003, 0x216_3010, 0x216_3017)], sw=True, dc=True)
    result = lt.audit_body(fn, probe_row(tail_calls=2), SECTIONS, {}, {})
    assert result["verdict"] == "mixed"
    assert result["decompiler"]["tables_in_body"] == 1
    assert any("0x2163003" in reason for reason in result["reasons"])


def test_audit_body_names_the_site_the_decompiler_gave_up_on():
    fn = load_jump_body(dc=True, sw=True, uw=[0x216_3007])
    result = lt.audit_body(fn, probe_row(), SECTIONS, {}, {})
    assert result["verdict"] == "switch beyond body"
    assert any("0x2163007" in reason for reason in result["reasons"])
    assert any("as a call" in reason for reason in result["reasons"])


def test_audit_body_explains_a_switch_that_lies_beyond_the_body():
    fn = load_jump_body(jt=[table(0x216_9000, 0x216_9000, 0x216_9008)], sw=True, dc=True)
    result = lt.audit_body(fn, probe_row(), SECTIONS, {}, {})
    assert result["verdict"] == "switch beyond body"
    assert any("beyond the body" in reason for reason in result["reasons"])


def test_audit_body_names_the_probe_count_a_recovered_table_no_longer_supports():
    fn = load_jump_body(jt=[table(0x216_3007, 0x216_3000, 0x216_3007, 0x216_3020)], sw=True, dc=True)
    result = lt.audit_body(fn, probe_row(), SECTIONS, {}, {})
    assert result["verdict"] == "no tail call"
    assert any("0x2163007" in reason for reason in result["reasons"])


def test_audit_body_keeps_a_body_the_decompiler_never_answered_out_of_the_tally():
    result = lt.audit_body(load_jump_body(), probe_row(), SECTIONS, {}, {})
    assert result["verdict"] == "not decompiled"
    assert result["decompiler"]["decompiled"] is False


def test_audit_body_carries_evidence_for_every_site():
    fn = two_site_body(jt=[table(0x216_3003, 0x216_3010, 0x216_3017)], sw=True, dc=True)
    result = lt.audit_body(fn, probe_row(tail_calls=2), SECTIONS, {}, {})
    assert [site["a"] for site in result["sites"]] == [0x216_3003, 0x216_3017]
    assert [site["tail_call"] for site in result["sites"]] == [False, True]
    assert all(site["category"] for site in result["sites"])
