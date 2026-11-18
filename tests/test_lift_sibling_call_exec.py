"""Execute a shipped register-handover tail jump as a sibling call on arm64."""

import lift_abi as abi
import lift_image as li
import lift_probe as lp
import lift_runtime as rt
import pcode_lift as pl
import pytest
import test_lift_unwind_exec as base

SHIPPED = lp.DEFAULT_SO
FIXTURES = base.REPO / "tests/fixtures/lift"
# `mov rax,rdi; mov rdi,rdx; jmp rax`: the handover shape the sibling-call gate unblocks.
THUNK = 0x1EF48C0
CALLEE = 0x90000000
ARGUMENT = 0x99AABBCC

pytestmark = [base.requires_arm64, pytest.mark.skipif(not SHIPPED.exists(), reason="needs the pinned Linux image")]


@pytest.fixture(scope="module")
def sibling_executable(tmp_path_factory):
    assert lp.sha256(SHIPPED) == li.PINNED_SHA256
    work = tmp_path_factory.mktemp("lift-sibling")
    rows, sections = rt.dump_cached(SHIPPED, {THUNK: 8}, base.REPO / ".tools/lift-runtime-cache", work)
    bodies = [pl.lift_body(row, sections) for row in rows]
    assert not any(body.holes for body in bodies)
    assert bodies[0].proven_tail_calls == 1
    ir = work / "sibling.ll"
    ir.write_text(pl.module_for(bodies, {}))
    shim = work / "shim.c"
    shim.write_text(
        abi.generate(
            [abi.Binding(THUNK, "lifted_handover", abi.Signature(("ptr", "u64", "u64"), "u64"))],
            [abi.Binding(CALLEE, "handover_callee", abi.Signature(("u64",), "u64"))],
        )
    )
    exe = work / "sibling"
    base.run([base.LLVM / "opt", "-passes=verify", "-disable-output", ir])
    base.run([base.LLVM / "clang", "-arch", "arm64", "-O2", ir, shim, FIXTURES / "handover.c", "-o", exe])
    return exe


def test_a_handed_over_register_is_the_target_and_the_handover_survives(sibling_executable):
    """The jump goes to the pointer rdi held, while rdi carries the third argument to the callee.

    The two moves have to be applied in order, and the callee's return has to reach the thunk's own
    caller: the wrapper aborts if the callee's return does not leave the frame balanced.
    """
    result = base.execute(sibling_executable, "run")
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"callee 0x{ARGUMENT:x}\nresult 0x{ARGUMENT * 3 + 1:x}\n"
