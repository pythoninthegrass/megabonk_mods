"""Tests for the classifier that names the unresolved computed jumps in the lift sample.

Bodies are hand-built Ghidra pcode records in the shape LiftDump.java writes, so the
classification rules are checkable without Ghidra, the ELF, or the LLVM toolchain.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import lift_holes as lh

SECTIONS = [
    {"name": "il2cpp", "va": 0x216_2000, "size": 0x2CC_3AB0, "exec": True},
    {"name": "rodata", "va": 0xB3_0A80, "size": 0x48_98F8, "exec": False},
    {"name": "data_rel_ro", "va": 0x4E_2E000, "size": 0x1_0000, "exec": False},
]


def op(name, out, *ins, **extra):
    return {"op": name, "out": out, "in": list(ins), **extra}


def insn(addr, length, *ops):
    return {"a": addr, "len": length, "m": "x", "ops": list(ops)}


def body(*insns, start=0x216_2990, size=None, jt=()):
    total = size if size is not None else sum(i["len"] for i in insns)
    return {"start": start, "size": total, "undecoded": 0, "insns": list(insns), "jt": list(jt)}


REG, IDX, PTR, TMP = "register,38,8", "register,208,4", "unique,200,8", "unique,210,8"


def switch_body(start=0x216_2990):
    """`if (idx > 6) goto out; jmp [rodata_table + idx*8]` with no decompiler table."""
    return body(
        insn(start, 4, op("INT_LESS", TMP, IDX, "const,6,4")),
        insn(start + 4, 6, op("CBRANCH", None, f"ram,{start + 0x40:x},8", TMP)),
        insn(start + 0x10, 5, op("INT_ZEXT", "unique,220,8", IDX)),
        insn(start + 0x15, 4, op("INT_LEFT", "unique,228,8", "unique,220,8", "const,3,1")),
        insn(start + 0x19, 8, op("INT_ADD", PTR, "cptr,0xb3_1000,8", "unique,228,8")),
        insn(start + 0x21, 3, op("LOAD", "unique,240,8", PTR)),
        insn(start + 0x24, 3, op("BRANCHIND", None, "unique,240,8")),
        insn(start + 0x40, 1, op("RETURN", None, "register,288,8")),
        start=start,
        size=0x41,
    )


def tail_call_body(start=0x216_3000):
    """`jmp [rdi + 0x20]` after a frame teardown, with the pointer masked before the jump."""
    return body(
        insn(start, 4, op("INT_ADD", "unique,300,8", REG, "const,0x20,8")),
        insn(start + 4, 3, op("LOAD", "unique,308,8", "unique,300,8")),
        insn(start + 7, 4, op("INT_AND", "unique,316,8", "unique,308,8", "const,0xfffffffffffffff8,8")),
        insn(start + 0xb, 6, op("BRANCHIND", None, "unique,316,8")),
        start=start,
    )


def got_slot_body(start=0x216_4000):
    """`jmp [rip + disp]` where the slot is a relocated pointer into the code section."""
    return body(
        insn(start, 7, op("LOAD", "unique,400,8", "ram,0x4e_2e008,8")),
        insn(start + 7, 6, op("BRANCHIND", None, "unique,400,8")),
        start=start,
    )


def untraceable_body(start=0x216_5000, jt=()):
    """Target produced by an op the walker does not follow, so no load definition exists."""
    return body(
        insn(start, 5, op("POPCOUNT", "unique,500,8", IDX)),
        insn(start + 5, 4, op("INT_EQUAL", "unique,508,1", IDX, "const,0,4")),
        insn(start + 9, 6, op("CBRANCH", None, f"ram,{start + 0x15:x},8", "unique,508,1")),
        insn(start + 0xf, 2, op("BRANCHIND", None, "unique,500,8")),
        insn(start + 0x15, 1, op("RETURN", None, "register,288,8")),
        start=start,
        size=0x16,
        jt=jt,
    )


BSS = {"name": "bss", "va": 0x53_60000, "size": 0x1_0000, "exec": False}


def thunk_body(start=0x216_6000):
    """The shipped invoke thunk: cached pointer in a global slot, resolver call, then `jmp rax`."""
    return body(
        insn(start, 7, op("LOAD", "register,0,8", "ram,0x53_67070,8")),
        insn(start + 7, 3, op("INT_EQUAL", "unique,600,1", "register,0,8", "const,0,8")),
        insn(start + 0xA, 2, op("CBRANCH", None, f"ram,{start + 0x14:x},8", "unique,600,1")),
        insn(start + 0xC, 4, op("INT_ADD", "register,288,8", "register,288,8", "const,8,8")),
        insn(start + 0x10, 1, op("LOAD", "register,38,8", "register,288,8")),
        insn(start + 0x11, 6, op("BRANCHIND", None, "register,0,8")),
        insn(start + 0x14, 5, op("CALLOTHER", "register,0,8", "cptr,0x205_6380,8")),
        start=start,
        size=0x19,
    )


def ghidra_slot_copy_body(start=0x216_7000):
    """How Ghidra really writes a fixed-address read: COPY from ram, not LOAD."""
    return body(
        insn(start, 7, op("COPY", "register,0,8", "ram,0x53_67070,8")),
        insn(start + 7, 3, op("INT_AND", "unique,700,8", "register,0,8", "register,0,8")),
        insn(start + 0xA, 6, op("BRANCHIND", None, "register,0,8")),
        start=start,
    )


def stack_pop_body(start=0x216_8000):
    """A pop: LOAD with a space-id operand and the stack pointer as the real address."""
    return body(
        insn(start, 3, op("LOAD", "unique,800,8", "const,1b1,8", "register,20,8")),
        insn(start + 3, 6, op("BRANCHIND", None, "unique,800,8")),
        start=start,
    )


def hole_row(start, size, *holes):
    return {"start": start, "size": size, "holes": list(holes)}


def test_select_hole_rows_keeps_bodies_with_a_computed_jump_hole():
    rows = [
        hole_row(1, 8, "BRANCHIND"),
        hole_row(2, 8, "JUMPTABLE_TARGET"),
        hole_row(3, 8, "CALLOTHER:divps"),
        hole_row(4, 8),
    ]
    assert [r["start"] for r in lh.select_hole_rows(rows)] == [1, 2]


def test_select_hole_rows_accepts_other_hole_kinds():
    rows = [hole_row(1, 8, "BRANCHIND"), hole_row(2, 8, "CALLOTHER:divps")]
    assert [r["start"] for r in lh.select_hole_rows(rows, kinds=("CALLOTHER:divps",))] == [2]


def test_parse_objdump_maps_addresses_to_instruction_text():
    text = """
.tools/x/GameAssembly.so:\tfile format elf64-x86-64

Disassembly of section il2cpp:

0000000002162990 <__start_il2cpp>:
 2162990:      	push	rbp
 2162991:      	jmp	qword ptr [rax + 0x20]
 2162997:      	mov	rax, qword ptr [rip + 0x2f09df0] # 0x506c7a8
"""
    assert lh.parse_objdump(text) == {
        0x216_2990: "push rbp",
        0x216_2991: "jmp qword ptr [rax + 0x20]",
        0x216_2997: "mov rax, qword ptr [rip + 0x2f09df0] # 0x506c7a8",
    }


def test_parse_relocs_reads_relative_addends_only():
    text = """
Relocation section '.rela.dyn' at offset 0x6c040 contains 4 entries:
    Offset             Info             Type               Symbol's Value  Symbol's Name + Addend
0000000004e2e008  0000000000000008 R_X86_64_RELATIVE                 21106fb
0000000004e2e010  0000000000000008 R_X86_64_RELATIVE                 212bc11
0000000004e2e018  0000000000000008 R_X86_64_JUMP_SLOT                0
0000000004e2e020  0000000000000007 R_X86_64_64                       0   memcpy + 0
"""
    assert lh.parse_relocs(text) == {0x4E_2E008: 0x211_06FB, 0x4E_2E010: 0x212_BC11}


def test_x86_sequence_covers_the_instructions_up_to_the_site():
    disasm = {0x100: "push rbp", 0x102: "pop rbx", 0x104: "jmp rax", 0x106: "nop"}
    assert lh.x86_sequence(disasm, 0x100, 0x104) == ["push rbp", "pop rbx", "jmp rax"]
    assert lh.x86_sequence({}, 0x100, 0x104) == []


def test_x86_sequence_without_a_limit_keeps_the_whole_body():
    disasm = {0x100 + 4 * i: f"nop {i}" for i in range(30)}
    last = 0x100 + 4 * 29
    assert len(lh.x86_sequence(disasm, 0x100, last, limit=None)) == 30
    assert len(lh.x86_sequence(disasm, 0x100, last)) == lh.SEQUENCE_LIMIT
    assert len(lh.x86_sequence(disasm, 0x100, last, limit=5)) == 5


def test_branchind_sites_reports_the_target_and_flat_op_index():
    fn = switch_body()
    sites = lh.branchind_sites(fn)
    assert len(sites) == 1
    site = sites[0]
    assert site["a"] == 0x216_2990 + 0x24
    assert site["target"] == "unique,240,8"
    assert lh.flatten(fn)[site["index"]]["op"] == "BRANCHIND"


def test_trace_load_follows_a_copy_chain_to_the_load():
    fn = body(
        insn(0x1000, 4, op("INT_ADD", "unique,20,8", REG, "const,0x20,8")),
        insn(0x1004, 3, op("LOAD", "unique,30,8", "unique,20,8")),
        insn(0x1007, 3, op("COPY", "unique,40,8", "unique,30,8")),
        insn(0x100a, 6, op("BRANCHIND", None, "unique,40,8")),
    )
    trace = lh.trace_load(lh.flatten(fn), 3, "unique,40,8")
    assert trace.kind == "load"
    assert trace.register_relative and not trace.scaled and trace.slot is None


def test_trace_load_reports_a_scaled_constant_base_as_a_table():
    fn = switch_body()
    sites = lh.branchind_sites(fn)
    trace = lh.trace_load(lh.flatten(fn), sites[0]["index"], sites[0]["target"])
    assert trace.kind == "load"
    assert trace.scaled and trace.slot is None
    assert trace.base == 0xB3_1000
    assert trace.base_space in ("cptr", "ram", "const")


def test_trace_load_reports_a_fixed_slot_for_a_relocated_pointer():
    fn = got_slot_body()
    sites = lh.branchind_sites(fn)
    trace = lh.trace_load(lh.flatten(fn), sites[0]["index"], sites[0]["target"])
    assert trace.kind == "load"
    assert trace.slot == 0x4E_2E008
    assert not trace.scaled and trace.base is None


def test_trace_load_gives_up_when_no_op_defines_the_target():
    fn = untraceable_body()
    sites = lh.branchind_sites(fn)
    trace = lh.trace_load(lh.flatten(fn), sites[0]["index"], sites[0]["target"])
    assert trace.kind == "unresolved"
    assert not trace.register_relative and trace.slot is None


def test_has_epilogue_recognises_frame_teardown():
    assert lh.has_epilogue(["add rsp, 0x28", "pop rbx", "jmp qword ptr [rax + 0x20]"])
    assert lh.has_epilogue(["leave", "jmp rax"])
    assert not lh.has_epilogue(["mov rax, rdi", "jmp rax"])


def test_has_bounds_check_needs_a_below_or_above_jump_after_an_immediate_compare():
    assert lh.has_bounds_check(["mov ecx, dword ptr [rbx]", "cmp rcx, 0x8", "ja 0x4dd8b4c", "xor eax, eax"])
    assert not lh.has_bounds_check(["test rax, rax", "je 0x4b0f794", "add rsp, 0x8", "jmp rax"])
    assert not lh.has_bounds_check(["cmp qword ptr [rdi + 0x38], 0x0", "je 0x4a8148d"])
    assert not lh.has_bounds_check(["ja 0x4dd8b4c", "cmp rcx, 0x8"])


def test_classify_facts_names_a_scaled_table_load_a_switch():
    facts = lh.SiteFacts(addr=0x100, kind="load", scaled_index=True, base_section="rodata")
    assert lh.classify_facts(facts) == "unrecovered switch"


def test_classify_facts_needs_a_scaled_index_or_arms_with_a_bounds_check_for_a_switch():
    base = {"addr": 0x100, "kind": "load", "base_section": "rodata"}
    assert lh.classify_facts(lh.SiteFacts(**base)) == "other"
    assert lh.classify_facts(lh.SiteFacts(**base, arms=4)) == "other"
    assert lh.classify_facts(lh.SiteFacts(**base, arms=4, bounds_check=True)) == "unrecovered switch"
    assert lh.classify_facts(lh.SiteFacts(**base, scaled_index=True)) == "unrecovered switch"


def test_classify_facts_names_a_relocated_code_slot_an_indirect_call_target():
    facts = lh.SiteFacts(addr=0x100, kind="load", slot=0x4E_2E008, slot_section="data_rel_ro", slot_reloc=0x221_0A30)
    assert lh.classify_facts(facts) == "indirect call target"


def test_classify_facts_calls_an_unrelocated_fixed_slot_a_tail_call():
    facts = lh.SiteFacts(addr=0x100, kind="load", slot=0x4E_2E008, slot_section="bss")
    assert lh.classify_facts(facts) == "indirect tail call"


def test_classify_facts_names_a_register_dispatch_a_tail_call():
    facts = lh.SiteFacts(addr=0x100, kind="load", register_relative=True, ends_body=True, epilogue=True)
    assert lh.classify_facts(facts) == "indirect tail call"


def test_classify_facts_keeps_a_target_that_is_not_loaded_as_other():
    assert lh.classify_facts(lh.SiteFacts(addr=0x100, kind="unresolved")) == "other"


def test_classify_facts_keeps_a_scaled_slot_out_of_the_tail_call_bucket():
    facts = lh.SiteFacts(addr=0x100, kind="load", slot=0x4E_2E008, scaled_index=True)
    assert lh.classify_facts(facts) == "other"


def test_classify_facts_uses_a_recovered_table_even_without_a_traced_load():
    facts = lh.SiteFacts(addr=0x100, kind="unresolved", cases_in_body=5)
    assert lh.classify_facts(facts) == "unrecovered switch"


def test_classify_facts_prefers_the_relocated_slot_over_the_tail_call_shape():
    facts = lh.SiteFacts(
        addr=0x100,
        kind="load",
        slot=0x4E_2E008,
        slot_section="data_rel_ro",
        slot_reloc=0x221_0A30,
        register_relative=True,
        ends_body=True,
    )
    assert lh.classify_facts(facts) == "indirect call target"


def test_classify_body_calls_a_scaled_table_load_an_unrecovered_switch():
    disasm = {0x216_2990: "cmp eax, 6", 0x216_2994: "ja 0x21629d0", 0x216_29B4: "jmp qword ptr [rax*8 + 0xb31000]"}
    result = lh.classify_body(switch_body(), SECTIONS, {}, disasm)
    assert result["category"] == "unrecovered switch"
    site = result["sites"][0]
    assert site["x86"] == ["cmp eax, 6", "ja 0x21629d0", "jmp qword ptr [rax*8 + 0xb31000]"]
    assert site["pcode"][-1].startswith("BRANCHIND")
    assert any("rodata" in line for line in site["evidence"])


def test_classify_body_calls_a_terminated_register_dispatch_a_tail_call():
    disasm = {
        0x216_3000: "add rsp, 0x28",
        0x216_3004: "pop rbx",
        0x216_3007: "and rax, -8",
        0x216_300B: "jmp qword ptr [rdi + 0x20]",
    }
    result = lh.classify_body(tail_call_body(), SECTIONS, {}, disasm)
    assert result["category"] == "indirect tail call"
    assert result["sites"][0]["facts"]["epilogue"] is True
    assert result["sites"][0]["x86"] == list(disasm.values())


def test_classify_body_calls_a_relocated_slot_an_indirect_call_target():
    disasm = {0x216_4000: "jmp qword ptr [rip + 0x4ccfa80] # 0x4e2e008"}
    relocs = {0x4E_2E008: 0x221_0A30}
    result = lh.classify_body(got_slot_body(), SECTIONS, relocs, disasm)
    assert result["category"] == "indirect call target"
    assert any("R_X86_64_RELATIVE" in line for line in result["sites"][0]["evidence"])


def test_classify_body_keeps_an_untraceable_target_as_other_and_records_the_sequence():
    disasm = {0x216_5000: "popcnt rax, ecx", 0x216_500f: "jmp rax"}
    result = lh.classify_body(untraceable_body(), SECTIONS, {}, disasm)
    assert result["category"] == "other"
    assert result["sites"][0]["x86"] == ["popcnt rax, ecx", "jmp rax"]


def test_classify_body_needs_a_reloc_into_code_for_an_indirect_call_target():
    disasm = {0x216_4000: "jmp qword ptr [rip + 0x4ccfa80] # 0x4e2e008"}
    result = lh.classify_body(got_slot_body(), SECTIONS, {0x4E_2E008: 0x4E_2E100}, disasm)
    assert result["category"] == "indirect tail call"


def test_trace_load_follows_a_rip_relative_lea_in_cptr_space():
    fn = body(
        insn(0x1000, 7, op("COPY", "register,10,8", "cptr,0xbfd278,8")),
        insn(0x1007, 5, op("INT_MULT", "unique,20,8", "register,8,8", "const,4,8")),
        insn(0x100C, 8, op("INT_ADD", "unique,30,8", "register,10,8", "unique,20,8")),
        insn(0x1014, 4, op("LOAD", "unique,40,4", "const,1b1,4", "unique,30,8")),
        insn(0x1018, 4, op("INT_SEXT", "register,30,8", "unique,40,4")),
        insn(0x101C, 3, op("BRANCHIND", None, "register,30,8")),
    )
    trace = lh.trace_load(lh.flatten(fn), 5, "register,30,8")
    assert trace.kind == "load"
    assert trace.base == 0xBFD_278 and trace.base_space == "cptr"
    assert trace.scaled and trace.slot is None


def test_trace_load_follows_a_register_to_its_constant_base():
    fn = body(
        insn(0x1000, 7, op("COPY", "register,10,8", "const,0xbfd278,8")),
        insn(0x1007, 5, op("INT_LEFT", "unique,20,8", "unique,10,8", "const,2,8")),
        insn(0x100C, 8, op("INT_ADD", "unique,30,8", "unique,20,8", "register,10,8")),
        insn(0x1014, 4, op("LOAD", "unique,40,4", "const,1b1,4", "unique,30,8")),
        insn(0x1018, 4, op("INT_SEXT", "register,30,8", "unique,40,4")),
        insn(0x101C, 3, op("BRANCHIND", None, "register,30,8")),
    )
    trace = lh.trace_load(lh.flatten(fn), 5, "register,30,8")
    assert trace.kind == "load"
    assert trace.base == 0xBFD_278 and trace.scaled and trace.register_relative


def test_trace_load_stops_at_a_register_loaded_from_memory():
    fn = body(
        insn(0x1000, 7, op("COPY", "register,10,8", "ram,0x50d6018,8")),
        insn(0x1007, 8, op("INT_ADD", "unique,30,8", "unique,20,8", "register,10,8")),
        insn(0x100F, 4, op("LOAD", "unique,40,8", "const,1b1,4", "unique,30,8")),
        insn(0x1013, 3, op("BRANCHIND", None, "unique,40,8")),
    )
    trace = lh.trace_load(lh.flatten(fn), 3, "unique,40,8")
    assert trace.kind == "load" and trace.register_relative
    assert trace.base is None


def test_trace_load_prefers_a_wide_constant_base_over_a_scale_factor():
    fn = body(
        insn(0x1000, 5, op("INT_LEFT", "unique,20,8", "unique,10,8", "const,2,8")),
        insn(0x1005, 8, op("INT_ADD", "unique,30,8", "unique,20,8", "const,0xbfd278,8")),
        insn(0x100D, 3, op("LOAD", "unique,40,8", "unique,30,8")),
        insn(0x1010, 2, op("BRANCHIND", None, "unique,40,8")),
    )
    trace = lh.trace_load(lh.flatten(fn), 3, "unique,40,8")
    assert trace.kind == "load"
    assert trace.base == 0xBFD_278 and trace.scaled and trace.slot is None


def test_trace_load_prefers_a_memory_space_base_over_a_constant():
    fn = body(
        insn(0x1000, 5, op("INT_LEFT", "unique,20,8", "unique,10,8", "const,3,8")),
        insn(0x1005, 8, op("INT_ADD", "unique,30,8", "unique,20,8", "ram,0xb3_1000,8")),
        insn(0x100D, 3, op("LOAD", "unique,40,8", "unique,30,8")),
        insn(0x1010, 2, op("BRANCHIND", None, "unique,40,8")),
    )
    trace = lh.trace_load(lh.flatten(fn), 3, "unique,40,8")
    assert trace.base == 0xB3_1000 and trace.base_space == "ram"


def test_trace_load_reads_a_copy_from_ram_as_a_slot_load():
    fn = ghidra_slot_copy_body()
    sites = lh.branchind_sites(fn)
    trace = lh.trace_load(lh.flatten(fn), sites[0]["index"], sites[0]["target"])
    assert trace.kind == "load"
    assert trace.slot == 0x53_67070
    assert not trace.register_relative and not trace.scaled


def test_trace_load_takes_the_pointer_not_the_space_id_of_a_stack_load():
    fn = stack_pop_body()
    sites = lh.branchind_sites(fn)
    trace = lh.trace_load(lh.flatten(fn), sites[0]["index"], sites[0]["target"])
    assert trace.kind == "load"
    assert trace.register_relative
    assert trace.slot is None and trace.base is None


def test_trace_load_does_not_call_a_copy_to_memory_a_load():
    fn = body(
        insn(0x1000, 7, op("COPY", "ram,0x53_67070,8", "register,0,8")),
        insn(0x1007, 6, op("BRANCHIND", None, "ram,0x53_67070,8")),
    )
    trace = lh.trace_load(lh.flatten(fn), 1, "ram,0x53_67070,8")
    assert trace.kind == "unresolved"
    assert trace.slot is None


def test_classify_body_calls_a_ram_copy_slot_a_tail_call():
    disasm = {
        0x216_7000: "mov rax, qword ptr [rip + 0x8578e1] # 0x5367070",
        0x216_700A: "jmp rax",
    }
    result = lh.classify_body(ghidra_slot_copy_body(), [*SECTIONS, BSS], {}, disasm)
    assert result["category"] == "indirect tail call"
    assert result["sites"][0]["facts"]["slot"] == 0x53_67070
    assert result["sites"][0]["facts"]["slot_section"] == "bss"


def test_classify_body_calls_a_lazy_invoke_thunk_a_tail_call():
    disasm = {
        0x216_6000: "mov rax, qword ptr [rip + 0x8578e1] # 0x5367070",
        0x216_6007: "test rax, rax",
        0x216_600A: "je 0x2166014",
        0x216_600C: "add rsp, 0x8",
        0x216_6010: "pop rbx",
        0x216_6011: "jmp rax",
    }
    result = lh.classify_body(thunk_body(), [*SECTIONS, BSS], {}, disasm)
    assert result["category"] == "indirect tail call"
    site = result["sites"][0]
    assert site["facts"]["slot"] == 0x53_67070
    assert site["facts"]["slot_section"] == "bss"
    assert site["facts"]["epilogue"] is True
    assert any("fixed slot" in line for line in site["evidence"])


def test_classify_body_uses_the_decompiler_table_when_the_load_cannot_be_traced():
    fn = untraceable_body(jt=[{"at": 0x216_500F, "cases": [0x216_5000, 0x216_500F, 0x216_9000]}])
    result = lh.classify_body(fn, SECTIONS, {}, {})
    assert result["category"] == "unrecovered switch"
    assert any("jump table" in line for line in result["sites"][0]["evidence"])


def test_categories_are_the_documented_set():
    assert lh.CATEGORIES == ("unrecovered switch", "indirect tail call", "indirect call target", "other")
