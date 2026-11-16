"""Tests for the pcode-to-LLVM-IR emitter used by the liftability spike.

Ghidra's raw per-instruction pcode is translated to textual LLVM IR with the register
file as a byte array. The structural contract is testable on hand-written pcode; the
verifier and arm64 backend are exercised only when the LLVM toolchain is present.
"""

import pytest
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pcode_lift as pl

LLVM = Path("/opt/homebrew/opt/llvm/bin")
requires_llvm = pytest.mark.skipif(not (LLVM / "opt").exists(), reason="LLVM toolchain absent")


def op(name, out, *ins, **extra):
    return {"op": name, "out": out, "in": list(ins), **extra}


def insn(addr, length, *ops):
    return {"a": addr, "len": length, "m": "x", "ops": list(ops)}


def body(*insns, start=0x1000, size=None):
    size = size if size is not None else sum(i["len"] for i in insns)
    return {"start": start, "size": size, "insns": list(insns)}


REG_EAX, REG_EDI = "register,0,4", "register,38,4"


def verify(ir):
    return subprocess.run(
        [LLVM / "opt", "-passes=verify", "-disable-output", "-"],
        input=ir,
        text=True,
        capture_output=True,
    )


def test_simple_copy_and_return_lifts_clean():
    fn = body(
        insn(0x1000, 2, op("COPY", REG_EAX, REG_EDI)),
        insn(0x1002, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn)
    assert "define void @sub_1000(ptr %reg)" in result.ir
    assert result.holes == []


@requires_llvm
def test_simple_body_verifies_and_compiles_for_arm64(tmp_path):
    fn = body(
        insn(0x1000, 2, op("COPY", REG_EAX, REG_EDI)),
        insn(0x1002, 1, op("RETURN", None, "register,288,8")),
    )
    ir = pl.module_for([pl.lift_body(fn)])
    assert verify(ir).returncode == 0
    obj = tmp_path / "o.o"
    proc = subprocess.run(
        [LLVM / "llc", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, "-"],
        input=ir,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0 and obj.stat().st_size > 0


@requires_llvm
def test_conditional_branch_to_instruction_address_verifies():
    fn = body(
        insn(
            0x1000,
            2,
            op("INT_EQUAL", "unique,100,1", REG_EDI, "const,0,4"),
            op("CBRANCH", None, "ram,1006,8", "unique,100,1"),
        ),
        insn(0x1002, 4, op("INT_ADD", REG_EAX, REG_EDI, "const,1,4")),
        insn(0x1006, 1, op("RETURN", None, "register,288,8")),
    )
    ir = pl.module_for([pl.lift_body(fn)])
    assert verify(ir).returncode == 0, verify(ir).stderr


@requires_llvm
def test_load_store_and_call_verify():
    fn = body(
        insn(
            0x1000,
            3,
            op("LOAD", REG_EAX, "const,1,8", "register,38,8"),
            op("STORE", None, "const,1,8", "register,38,8", REG_EAX),
        ),
        insn(0x1003, 5, op("CALL", None, "ram,2000,8")),
        insn(0x1008, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn)
    assert "declare void @sub_2000(ptr)" in pl.module_for([result])
    assert verify(pl.module_for([result])).returncode == 0


def test_branchind_is_recorded_as_a_hole():
    fn = body(insn(0x1000, 2, op("BRANCHIND", None, "register,0,8")))
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


def test_callother_is_recorded_as_a_hole_with_its_name():
    fn = body(
        insn(0x1000, 4, op("CALLOTHER", None, "const,5,4", REG_EDI, user="divps")),
        insn(0x1004, 1, op("RETURN", None, "register,288,8")),
    )
    assert pl.lift_body(fn).holes == ["CALLOTHER:divps"]


def test_unknown_opcode_is_a_hole_not_a_crash():
    fn = body(insn(0x1000, 1, op("NOSUCHOP", REG_EAX, REG_EDI)))
    assert pl.lift_body(fn).holes == ["NOSUCHOP"]


def test_branch_out_of_body_is_a_tail_call_not_a_hole():
    fn = body(insn(0x1000, 5, op("BRANCH", None, "ram,9000,8")))
    result = pl.lift_body(fn)
    assert result.holes == []
    assert "@sub_9000" in result.ir


@requires_llvm
def test_float_and_flag_ops_verify():
    fn = body(
        insn(
            0x1000,
            4,
            op("FLOAT_ADD", "register,1200,4", "register,1200,4", "register,1240,4"),
            op("INT_CARRY", "register,200,1", REG_EDI, REG_EAX),
            op("INT_SBORROW", "register,201,1", REG_EDI, REG_EAX),
            op("POPCOUNT", "register,202,1", "register,0,1"),
            op("INT_ZEXT", "register,8,8", REG_EAX),
            op("SUBPIECE", "register,10,1", "register,8,8", "const,0,4"),
        ),
        insn(0x1004, 1, op("RETURN", None, "register,288,8")),
    )
    assert verify(pl.module_for([pl.lift_body(fn)])).returncode == 0


@requires_llvm
def test_direct_ram_varnodes_read_and_write_memory():
    fn = body(
        insn(0x1000, 6, op("COPY", REG_EAX, "ram,5000,4")),
        insn(0x1006, 6, op("COPY", "ram,5004,4", REG_EAX)),
        insn(0x100C, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == []
    assert verify(pl.module_for([result])).returncode == 0


RODATA = {"name": "rodata", "va": 0x5000, "size": 0x100, "exec": False}
TEXT = {"name": "il2cpp", "va": 0x1000, "size": 0x1000, "exec": True}


def test_data_pointer_constant_becomes_section_symbol_offset():
    fn = body(
        insn(0x1000, 7, op("COPY", "register,0,8", "cptr,5010,8")),
        insn(0x1007, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn, [RODATA, TEXT])
    assert "@sec_rodata, i64 16" in result.ir
    assert result.data_sections == {"rodata"}
    assert result.unmapped_refs == 0
    assert "@sec_rodata = external global i8" in pl.module_for([result])


def test_code_pointer_constant_becomes_function_symbol():
    fn = body(
        insn(0x1000, 7, op("COPY", "register,0,8", "cptr,1800,8")),
        insn(0x1007, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn, [RODATA, TEXT])
    assert "ptrtoint (ptr @sub_1800 to i64)" in result.ir
    assert 0x1800 in result.externs


def test_ram_varnode_inside_a_section_uses_the_section_symbol():
    fn = body(
        insn(0x1000, 6, op("COPY", REG_EAX, "ram,5004,4")),
        insn(0x1006, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn, [RODATA, TEXT])
    assert "@sec_rodata, i64 4" in result.ir


def test_address_outside_every_section_is_counted_unmapped():
    fn = body(
        insn(0x1000, 7, op("COPY", "register,0,8", "cptr,9000,8")),
        insn(0x1007, 1, op("RETURN", None, "register,288,8")),
    )
    assert pl.lift_body(fn, [RODATA, TEXT]).unmapped_refs == 1


@requires_llvm
def test_jump_table_becomes_a_switch_over_the_rebased_target():
    table = {"at": 0x1004, "cases": [0x1006, 0x1008]}
    fn = body(
        insn(0x1000, 4, op("COPY", "register,0,8", "cptr,5000,8")),
        insn(0x1004, 2, op("BRANCHIND", None, "register,0,8")),
        insn(0x1006, 2, op("COPY", REG_EAX, "const,1,4"), op("RETURN", None, "register,288,8")),
        insn(0x1008, 2, op("COPY", REG_EAX, "const,2,4"), op("RETURN", None, "register,288,8")),
    )
    fn["jt"] = [table]
    result = pl.lift_body(fn, [RODATA, TEXT])
    assert result.holes == []
    assert "switch i64" in result.ir
    assert verify(pl.module_for([result])).returncode == 0


def test_jump_table_case_outside_the_body_is_a_hole():
    fn = body(
        insn(0x1000, 4, op("COPY", "register,0,8", "cptr,5000,8")),
        insn(0x1004, 2, op("BRANCHIND", None, "register,0,8")),
    )
    fn["jt"] = [{"at": 0x1004, "cases": [0x7000]}]
    assert pl.lift_body(fn, [RODATA, TEXT]).holes == ["JUMPTABLE_TARGET"]


def test_sparse_unique_offsets_are_compacted_into_a_small_frame():
    fn = body(
        insn(
            0x1000,
            4,
            op("INT_AND", "unique,58300,4", REG_EDI, "const,ff,4"),
            op("POPCOUNT", "unique,58400,1", "unique,58300,4"),
        ),
        insn(0x1004, 1, op("RETURN", None, "register,288,8")),
    )
    ir = pl.lift_body(fn).ir
    assert "alloca [64 x i8]" in ir
    assert "i64 361216" not in ir


@requires_llvm
def test_branchind_through_a_loaded_pointer_is_an_indirect_tail_call():
    fn = body(
        insn(
            0x1000,
            3,
            op("LOAD", "unique,100,8", "const,1,8", "register,0,8"),
            op("BRANCHIND", None, "unique,100,8"),
        ),
    )
    result = pl.lift_body(fn)
    assert result.holes == []
    assert result.indirect_calls == 1
    assert verify(pl.module_for([result])).returncode == 0


def test_branchind_on_a_computed_register_without_a_table_stays_a_hole():
    fn = body(
        insn(0x1000, 3, op("INT_ADD", "register,0,8", "register,0,8", "const,8,8")),
        insn(0x1003, 2, op("BRANCHIND", None, "register,0,8")),
    )
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


@requires_llvm
def test_branchind_on_a_register_loaded_by_an_earlier_instruction_is_a_tail_call():
    fn = body(
        insn(0x1000, 4, op("LOAD", "register,8,8", "const,1,8", "register,38,8")),
        insn(0x1004, 3, op("COPY", "register,38,8", "register,0,8")),
        insn(0x1007, 2, op("BRANCHIND", None, "register,8,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == []
    assert result.tail_calls == 1
    assert verify(pl.module_for([result])).returncode == 0


def test_branchind_on_a_register_defined_by_arithmetic_stays_a_hole():
    fn = body(
        insn(0x1000, 4, op("LOAD", "register,8,8", "const,1,8", "register,38,8")),
        insn(0x1004, 3, op("INT_ADD", "register,8,8", "register,8,8", "register,10,8")),
        insn(0x1007, 2, op("BRANCHIND", None, "register,8,8")),
    )
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


@requires_llvm
def test_branchind_follows_a_copy_from_a_loaded_temporary():
    fn = body(
        insn(
            0x1000,
            4,
            op("INT_ADD", "unique,8e00,8", "register,38,8", "const,18,8"),
            op("LOAD", "unique,23d00,8", "const,1b1,4", "unique,8e00,8"),
            op("COPY", "register,8,8", "unique,23d00,8"),
        ),
        insn(0x1004, 2, op("BRANCHIND", None, "register,8,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == []
    assert result.tail_calls == 1
    assert verify(pl.module_for([result])).returncode == 0
