"""A code address a lifted body materialises must be a value lift_dispatch can switch on."""

import pcode_lift as pl
import pytest

TEXT = {"name": "text", "va": 0x1000, "size": 0x1000, "exec": True}


def body():
    return {
        "start": 0x1000,
        "size": 3,
        "insns": [
            {"a": 0x1000, "len": 1, "ops": [{"op": "COPY", "out": "register,0,8", "in": ["cptr,1800,8"]}]},
            {"a": 0x1001, "len": 1, "ops": [{"op": "CALLIND", "out": None, "in": ["register,0,8"]}]},
            {"a": 0x1002, "len": 1, "ops": [{"op": "RETURN", "out": None, "in": ["register,288,8"]}]},
        ],
    }


@pytest.mark.xfail(
    strict=True,
    reason="a code address constant lowers to the host address of @sub_X, while lift_dispatch switches on the file address X",
)
def test_a_code_address_constant_is_the_file_address_when_calls_go_through_dispatch():
    lifted = pl.lift_body(body(), [TEXT], call_dispatch=True)
    assert "ptrtoint (ptr @sub_1800" not in lifted.ir
