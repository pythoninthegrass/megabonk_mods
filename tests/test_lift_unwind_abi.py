"""Adapter generation for raw unwinder imports and the export-side pending-exception guard."""

import lift_abi as abi
import pcode_lift as pl
import pytest

SIG = abi.Signature(("u64",), "u64")


def test_raw_import_calls_the_named_function_with_the_register_file():
    source = abi.generate([abi.Binding(0x1000, "entry", SIG)], [], raw=[abi.RawBinding(0x2000, "lu_resume")])
    assert "extern void lu_resume(unsigned char *reg);" in source
    assert "void sub_2000(unsigned char *reg) {\n  lu_resume(reg);\n}" in source
    assert "case UINT64_C(8192): sub_2000(reg);" in source


def test_raw_import_does_not_push_or_pop_the_guest_return_slot():
    source = abi.generate([], [], raw=[abi.RawBinding(0x2000, "lu_resume")])
    body = source[source.index("void sub_2000") : source.index("void lift_dispatch")]
    assert "rsp" not in body


def test_raw_binding_shares_the_duplicate_and_reserved_name_checks():
    with pytest.raises(abi.AbiError, match="duplicate"):
        abi.generate([abi.Binding(0x1000, "entry", SIG)], [], raw=[abi.RawBinding(0x1000, "lu_resume")])
    with pytest.raises(abi.AbiError, match="identifier"):
        abi.RawBinding(0x1000, "bad();")
    with pytest.raises(abi.AbiError, match="address"):
        abi.RawBinding(0, "lu_resume")


def test_export_aborts_when_an_exception_is_still_pending_on_return():
    source = abi.generate([abi.Binding(0x1000, "entry", SIG)], [])
    assert f"memcpy(&pending, reg + {pl.EH_PENDING_PAD}, 8);" in source
    assert "if (pending) abort();" in source
    assert source.index("if (returned_rsp != rsp + 8) abort();") < source.index("if (pending) abort();")
