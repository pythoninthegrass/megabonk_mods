"""Execute a lifted body that reaches an unresolved jump: it logs the body and site, then aborts."""

import lift_abi as abi
import os
import pcode_lift as pl
import pytest
import signal
import subprocess
import sys
import test_pcode_lift as t
from pathlib import Path

LLVM = Path("/opt/homebrew/opt/llvm/bin")
BODY = 0x1000

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or os.uname().machine != "arm64" or not (LLVM / "clang").exists(),
    reason="needs native arm64 macOS and LLVM",
)

HARNESS = """
#include <stdint.h>
uint32_t lifted_hole(void);
int main(void) { return (int)lifted_hole(); }
"""


@pytest.fixture(scope="module")
def hole_executable(tmp_path_factory):
    work = tmp_path_factory.mktemp("lift-hole")
    fn = t.body(t.insn(BODY, 2, t.op("BRANCHIND", None, "register,0,8")))
    lifted = pl.lift_body(fn, trap_holes=True)
    assert lifted.holes == ["BRANCHIND"]
    ir, shim, main, exe = work / "hole.ll", work / "shim.c", work / "main.c", work / "hole"
    ir.write_text(pl.module_for([lifted]))
    shim.write_text(abi.generate([abi.Binding(BODY, "lifted_hole", abi.Signature((), "u32"))], []))
    main.write_text(HARNESS)
    subprocess.run(
        [LLVM / "clang", "-arch", "arm64", "-O2", ir, shim, main, "-o", exe], check=True, capture_output=True, text=True
    )
    return exe


def test_unresolved_jump_logs_body_and_site_then_aborts(hole_executable, tmp_path):
    log = tmp_path / "holes.log"
    result = subprocess.run(
        [hole_executable], capture_output=True, text=True, timeout=30, env={**os.environ, "LIFT_HOLE_LOG": str(log)}
    )
    assert result.returncode == -signal.SIGABRT
    assert "lift_hole: body 0x1000 site 0x1000" in result.stderr
    assert log.read_text() == "lift_hole: body 0x1000 site 0x1000\n"


def test_unresolved_jump_aborts_without_a_log_file(hole_executable):
    env = {k: v for k, v in os.environ.items() if k != "LIFT_HOLE_LOG"}
    result = subprocess.run([hole_executable], capture_output=True, text=True, timeout=30, env=env)
    assert result.returncode == -signal.SIGABRT
    assert "lift_hole: body 0x1000 site 0x1000" in result.stderr
