"""Emission of the pending-unwind check and the landing-pad switch."""

import pcode_lift as pl
import pytest
import subprocess
from pathlib import Path

LLVM = Path("/opt/homebrew/opt/llvm/bin")
requires_llvm = pytest.mark.skipif(not (LLVM / "opt").exists(), reason="LLVM toolchain absent")


def op(name, out, *ins):
    return {"op": name, "out": out, "in": list(ins)}


def insn(addr, length, *ops):
    return {"a": addr, "len": length, "m": "x", "ops": list(ops)}


def caller(call):
    return {
        "start": 0x1000,
        "size": 0x20,
        "insns": [
            insn(0x1000, 5, call),
            insn(0x1005, 1, op("RETURN", None, "register,288,8")),
            insn(0x1010, 1, op("RETURN", None, "register,288,8")),
        ],
    }


DIRECT = op("CALL", None, "ram,2000,8")
INDIRECT = op("CALLIND", None, "register,0,8")
PENDING_PAD_OFFSET = pl.EH_PENDING_PAD
PENDING_CFA_OFFSET = pl.EH_PENDING_CFA


def verify(ir_text):
    module = pl.module_for([ir_text])
    result = subprocess.run(
        [str(LLVM / "opt"), "-passes=verify", "-disable-output", "-"], input=module, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_default_lift_has_no_pending_check():
    ir = pl.lift_body(caller(DIRECT)).ir
    assert str(PENDING_PAD_OFFSET) not in ir


def test_unwind_lift_checks_the_pending_word_after_a_direct_call():
    lifted = pl.lift_body(caller(DIRECT), unwind=True)
    assert lifted.holes == []
    ir = lifted.ir
    assert f"i64 {PENDING_PAD_OFFSET}" in ir
    assert ir.index("call void @sub_2000") < ir.index(f"i64 {PENDING_PAD_OFFSET}")
    assert "switch" not in ir


def test_unwind_lift_without_pads_propagates_by_returning():
    ir = pl.lift_body(caller(DIRECT), unwind=True).ir
    assert "EH_RET:" in ir
    assert "EH_DISPATCH" not in ir


def test_unwind_lift_checks_dispatch_calls_too():
    ir = pl.lift_body(caller(INDIRECT), call_dispatch=True, unwind=True).ir
    assert ir.index("@lift_dispatch(i64") < ir.index(f"i64 {PENDING_PAD_OFFSET}")


def test_a_pad_gets_a_dispatch_switch_guarded_by_the_frame_identity():
    lifted = pl.lift_body(caller(DIRECT), unwind=True, pads=frozenset({0x1010}))
    assert lifted.holes == []
    ir = lifted.ir
    assert "EH_DISPATCH:" in ir
    assert f"i64 {PENDING_CFA_OFFSET}" in ir
    assert "i64 4112, label %L1010_0" in ir
    assert "call void @abort()" in ir
    assert "declare void @abort()" in pl.module_for([lifted])


def test_a_pad_that_is_not_an_instruction_start_is_a_hole():
    lifted = pl.lift_body(caller(DIRECT), unwind=True, pads=frozenset({0x1011}))
    assert "EH_PAD_NOT_INSN" in lifted.holes


def test_pads_without_unwind_mode_are_a_hole():
    lifted = pl.lift_body(caller(DIRECT), pads=frozenset({0x1010}))
    assert "EH_PAD_WITHOUT_UNWIND" in lifted.holes


@requires_llvm
@pytest.mark.parametrize("pads", [frozenset(), frozenset({0x1010})])
def test_unwind_ir_passes_the_llvm_verifier(pads):
    verify(pl.lift_body(caller(DIRECT), unwind=True, pads=pads))
