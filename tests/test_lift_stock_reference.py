"""The shipped libsupc++, lifted, against the outcomes a stock libstdc++ gives the same unwind.cpp."""

import pytest
import test_lift_shipped_runtime as shipped
import test_lift_unwind_exec as base
from test_lift_shipped_runtime import shipped_executable  # noqa: F401


def reference_cases():
    lines = (base.REPO / "tests/fixtures/lift/unwind_reference.txt").read_text().splitlines()
    return [tuple(line.split("|")) for line in lines if line and not line.startswith("#")]


@shipped.requires_image
@base.requires_arm64
@pytest.mark.parametrize("mode, status, stdout", reference_cases())
def test_lifted_unwind_matches_the_stock_libstdcxx_reference(shipped_executable, mode, status, stdout):  # noqa: F811
    result = base.execute(shipped_executable, mode)
    code = result.returncode if result.returncode >= 0 else 128 - result.returncode
    assert (code, result.stdout.strip()) == (int(status), stdout)
