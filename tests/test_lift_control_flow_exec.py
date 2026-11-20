"""Execute a shipped indirect tail jump across two lifted body boundaries."""

import elf_shim_probe
import lift_abi as abi
import lift_image as li
import lift_probe as lp
import lift_runtime as rt
import pcode_lift as pl
import pytest
import signal
import test_lift_unwind_exec as base

SHIPPED = lp.DEFAULT_SO
FIXTURES = base.REPO / "tests/fixtures/lift"
THUNK = 0x1D35190
TARGET = 0x1D41DB0
SWITCH = 0x4BD70F0

pytestmark = [base.requires_arm64, pytest.mark.skipif(not SHIPPED.exists(), reason="needs the pinned Linux image")]


@pytest.fixture(scope="module")
def control_flow_executable(tmp_path_factory):
    assert lp.sha256(SHIPPED) == li.PINNED_SHA256
    work = tmp_path_factory.mktemp("lift-control-flow")
    rows, sections = rt.dump_cached(SHIPPED, {THUNK: 12, TARGET: 4, SWITCH: 29}, base.REPO / ".tools/lift-runtime-cache", work)
    bodies = {row["start"]: pl.lift_body(row, sections, call_dispatch=True) for row in rows}
    assert not any(body.holes for body in bodies.values())
    assert bodies[THUNK].proven_tail_calls == 1
    assert "switch i64" in bodies[SWITCH].ir
    ir = work / "control_flow.ll"
    images = base.section_images(elf_shim_probe.parse_elf(SHIPPED), SHIPPED.read_bytes(), sections, bodies.values())
    ir.write_text(pl.module_for(list(bodies.values()), images))
    shim = work / "shim.c"
    shim.write_text(
        abi.generate(
            [
                abi.Binding(THUNK, "lifted_thunk", abi.Signature(("ptr", "ptr", "u64"), "u32")),
                abi.Binding(SWITCH, "lifted_switch", abi.Signature(("u32",), "u8")),
            ],
            [],
            callable_bodies=[TARGET],
        )
    )
    exe = work / "control_flow"
    base.run([base.LLVM / "opt", "-passes=verify", "-disable-output", ir])
    base.run([base.LLVM / "clang", "-arch", "arm64", "-O2", ir, shim, FIXTURES / "control_flow.c", "-o", exe])
    return exe


def test_indirect_tail_jump_to_another_body_matches_shipped_x86(control_flow_executable):
    result = base.execute(control_flow_executable, "valid")
    assert result.returncode == 0, result.stderr
    assert result.stdout == (FIXTURES / "control_flow_reference.txt").read_text()


@pytest.mark.parametrize("mode", ["unknown", "interior"])
def test_indirect_tail_jump_rejects_unresolved_or_malformed_target(control_flow_executable, mode):
    result = base.execute(control_flow_executable, mode)
    assert result.returncode == -signal.SIGABRT
    assert result.stdout == ""
