"""Contract and execution tests for typed Linux SysV / native call adapters."""

import json
import lift_abi as abi
import lift_probe as lp
import os
import pcode_lift as pl
import pytest
import subprocess
import sys
from pathlib import Path


def test_integer_and_sse_banks_are_independent():
    layout = abi.argument_layout(("u64", "f64", "ptr", "f32", "v4f32"))
    assert [(slot.space, slot.offset, slot.size) for slot in layout] == [
        ("reg", 0x38, 8),
        ("reg", 0x1200, 8),
        ("reg", 0x30, 8),
        ("reg", 0x1240, 4),
        ("reg", 0x1280, 16),
    ]


def test_stack_arguments_include_return_slot_and_vector_alignment():
    kinds = ("u64",) * 7 + ("f64",) * 9 + ("v4f32", "u32")
    slots = abi.argument_layout(kinds)
    assert [(s.space, s.offset) for s in slots[:6]] == [("reg", offset) for offset in (0x38, 0x30, 0x10, 0x8, 0x80, 0x88)]
    assert [(s.offset, s.size) for s in slots if s.space == "stack"] == [(8, 8), (16, 8), (24, 16), (40, 4)]


@pytest.mark.parametrize("kind", ["struct:8", "f80", "v8f32", "...", "void", "bogus"])
def test_unsupported_arguments_rejected_before_generation(kind):
    with pytest.raises(abi.AbiError, match="unsupported"):
        abi.Signature((kind,), "u64")


@pytest.mark.parametrize("result", ["struct:16", "f80", "..."])
def test_unsupported_results_rejected(result):
    with pytest.raises(abi.AbiError, match="unsupported"):
        abi.Signature((), result)


def test_variadic_manifest_is_rejected():
    with pytest.raises(abi.AbiError, match="variadic"):
        abi.Signature(("u64",), "u64", variadic=True)


def test_manifest_rejects_duplicate_targets_and_invalid_names():
    sig = abi.Signature(("u64",), "u64")
    with pytest.raises(abi.AbiError, match="duplicate"):
        abi.generate([abi.Binding(0x1000, "entry", sig)], [abi.Binding(0x1000, "native", sig)])
    with pytest.raises(abi.AbiError, match="identifier"):
        abi.Binding(0x1000, "injected();", sig)
    with pytest.raises(abi.AbiError, match="address"):
        abi.Binding(-1, "entry", sig)


def test_generated_entries_use_private_state_and_checked_dispatch():
    sig = abi.Signature(("u64", "f64"), "f64")
    source = abi.generate([abi.Binding(0x1000, "entry", sig)], [abi.Binding(0x2000, "native", sig)])
    assert "unsigned char reg[8192]" in source
    assert "static unsigned char reg" not in source
    assert "case UINT64_C(4096): sub_1000(reg);" in source
    assert "case UINT64_C(8192): sub_2000(reg);" in source
    assert "default: abort();" in source


def test_indirect_lift_can_use_checked_dispatch_without_native_pointer_cast():
    fn = {
        "start": 0x1000,
        "size": 2,
        "insns": [
            {"a": 0x1000, "len": 1, "ops": [{"op": "CALLIND", "out": None, "in": ["register,0,8"]}]},
            {"a": 0x1001, "len": 1, "ops": [{"op": "RETURN", "out": None, "in": ["register,288,8"]}]},
        ],
    }
    lifted = pl.lift_body(fn, call_dispatch=True)
    module = pl.module_for([lifted])
    assert "declare void @lift_dispatch(i64, ptr)" in module
    assert "call void @lift_dispatch(" in module
    assert "inttoptr" not in lifted.ir


def test_loaded_indirect_tail_call_uses_same_checked_dispatch():
    fn = {
        "start": 0x1000,
        "size": 2,
        "insns": [
            {
                "a": 0x1000,
                "len": 1,
                "ops": [
                    {"op": "LOAD", "out": "register,0,8", "in": ["const,1b1,8", "register,38,8"]},
                ],
            },
            {"a": 0x1001, "len": 1, "ops": [{"op": "BRANCHIND", "out": None, "in": ["register,0,8"]}]},
        ],
    }
    lifted = pl.lift_body(fn, call_dispatch=True)
    assert lifted.holes == []
    assert lifted.tail_calls == 1
    assert "call void @lift_dispatch(" in lifted.ir
    assert "call void %t" not in lifted.ir


LLVM = Path("/opt/homebrew/opt/llvm/bin")
GHIDRA = next(iter(sorted(Path("/opt/homebrew/Cellar/ghidra").glob("*/libexec/support/analyzeHeadless"))), None)
REPO = Path(__file__).resolve().parents[1]
MIX = abi.Signature(("u64",) * 7 + ("f64",) * 9 + ("v4f32", "ptr"), "f64")
UNARY = abi.Signature(("u64",), "u64")
SIGNATURES = {
    "f_mix": MIX,
    "f_import_mix": MIX,
    "native_mix": MIX,
    "f_vector": abi.Signature(("v4f32", "v4f32"), "v4f32"),
    "native_vector": abi.Signature(("v4f32", "v4f32"), "v4f32"),
    "f_pointer": abi.Signature(("ptr",), "ptr"),
    "native_pointer": abi.Signature(("ptr",), "ptr"),
    "f_inner": UNARY,
    "f_nested": UNARY,
    "f_callback": UNARY,
    "native_callback": UNARY,
    "f_indirect": abi.Signature(("ptr", "u64"), "u64"),
    "f_indirect_tail": abi.Signature(("ptr", "u64"), "u64"),
    "f_store": abi.Signature(("ptr", "u64"), "void"),
    "native_store": abi.Signature(("ptr", "u64"), "void"),
}
for kind in ("i8", "u8", "i16", "u16", "i32", "u32", "i64", "u64", "f32", "f64", "v2f64", "v4u32"):
    for prefix in ("f_", "native_"):
        SIGNATURES[prefix + kind] = abi.Signature((kind,), kind)
requires_arm64 = pytest.mark.skipif(
    sys.platform != "darwin" or os.uname().machine != "arm64" or not (LLVM / "clang").exists() or GHIDRA is None,
    reason="needs native arm64 macOS, LLVM and Ghidra",
)


def run(command, **kwargs):
    result = subprocess.run([str(c) for c in command], capture_output=True, text=True, **kwargs)
    assert result.returncode == 0, f"{command}: {result.stdout[-1000:]} {result.stderr[-2000:]}"
    return result.stdout


@pytest.fixture(scope="module")
def call_executable(tmp_path_factory):
    work = tmp_path_factory.mktemp("lift-calls")
    source = REPO / "tests/fixtures/lift/calls.c"
    so = work / "calls.so"
    run(
        [
            LLVM / "clang",
            "--target=x86_64-linux-gnu",
            "-O1",
            "-fPIC",
            "-ffreestanding",
            "-nostdlib",
            "-shared",
            "-fuse-ld=lld",
            "-fno-stack-protector",
            "-Wl,-Bsymbolic",
            source,
            "-o",
            so,
        ]
    )
    symbols = {}
    for line in run([LLVM / "llvm-nm", "--print-size", "--defined-only", so]).splitlines():
        fields = line.split()
        if len(fields) == 4 and fields[3] in SIGNATURES:
            symbols[fields[3]] = (int(fields[0], 16), int(fields[1], 16))
    assert symbols.keys() == SIGNATURES.keys()
    functions = [lp.Fde(address, size) for name, (address, size) in symbols.items() if name.startswith("f_")]
    rows, sections = lp.dump_pcode(so, functions, work)
    bodies = [pl.lift_body(row, sections, call_dispatch=True) for row in rows]
    assert all(not body.holes for body in bodies), [(b.start, b.holes) for b in bodies]
    ir = work / "calls.ll"
    rodata = work / "rodata.bin"
    run([LLVM / "llvm-objcopy", f"--dump-section=.rodata={rodata}", so])
    ir.write_text(pl.module_for(bodies, {"_rodata": rodata.read_bytes()}))
    run([LLVM / "opt", "-passes=verify", "-disable-output", ir])
    obj = work / "calls.o"
    run([LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", ir, "-o", obj])
    exports = [abi.Binding(symbols[n][0], n.replace("f_", "e_", 1), sig) for n, sig in SIGNATURES.items() if n.startswith("f_")]
    imports = [abi.Binding(symbols[n][0], n, sig) for n, sig in SIGNATURES.items() if n.startswith("native_")]
    adapters = work / "adapters.c"
    adapters.write_text(abi.generate(exports, imports))
    harness = work / "harness.c"
    harness.write_text(call_harness(symbols))
    exe = work / "calls"
    run([LLVM / "clang", "-arch", "arm64", "-O1", "-ffp-contract=off", "-DABI_HOST", harness, obj, "-o", exe])
    return exe


def call_harness(symbols):
    inner = symbols["f_inner"][0]
    native = symbols["native_callback"][0]
    nested = symbols["f_nested"][0]
    callback = symbols["f_callback"][0]
    return f"""
#include "{REPO / 'tests/fixtures/lift/calls.c'}"
#include "adapters.c"
#include <stdio.h>
#include <sys/sysctl.h>
int main(int argc, char **argv) {{
    if (argc > 1) {{
        unsigned char reg[8192] = {{0}};
        lift_dispatch(UINT64_C(0xdeadbeef), reg);
        return 99;
    }}
    uint64_t q[2] = {{37, 41}};
    v4f32 v = {{1, 2, 3, 4}}, w = {{5, 6, 7, 8}};
    int bad = 0;
    for (uint64_t x = 0; x < 100; x++) {{
        double want = f_mix(x, 2, 3, 4, 5, 6, 7, 1, 2, 3, 4, 5, 6, 7, 8, 9, v, q);
        bad += e_mix(x, 2, 3, 4, 5, 6, 7, 1, 2, 3, 4, 5, 6, 7, 8, 9, v, q) != want;
        bad += e_import_mix(x, 2, 3, 4, 5, 6, 7, 1, 2, 3, 4, 5, 6, 7, 8, 9, v, q) != want + 1;
        v4f32 got = e_vector(v, w), expected = f_vector(v, w);
        bad += memcmp(&got, &expected, 16) != 0;
        bad += e_pointer(q) != q + 1;
        bad += e_nested(x) != f_nested(x);
        bad += e_callback(x) != f_callback(x);
        bad += e_indirect((void *)(uintptr_t){inner}, x) != f_inner(x) + 3;
        bad += e_indirect((void *)(uintptr_t){native}, x) != native_callback(x) + 3;
        uintptr_t target = {inner};
        bad += e_indirect_tail(&target, x) != f_inner(x);
        target = {native};
        bad += e_indirect_tail(&target, x) != native_callback(x);
        bad += e_i8(-123) != -123 || e_u8(251) != 251;
        bad += e_i16(-31000) != -31000 || e_u16(65000) != 65000;
        bad += e_i32(-2000000000) != -2000000000 || e_u32(4000000000u) != 4000000000u;
        bad += e_i64(INT64_MIN + x) != INT64_MIN + (int64_t)x;
        bad += e_u64(UINT64_MAX - x) != UINT64_MAX - x;
        float float_value = x % 2 ? -0.0f : -3.25f, float_result = e_f32(float_value);
        double double_value = x % 2 ? -0.0 : -3.125, double_result = e_f64(double_value);
        bad += memcmp(&float_value, &float_result, 4) != 0;
        bad += memcmp(&double_value, &double_result, 8) != 0;
        v2f64 doubles = {{-3.125, 17}}, doubles_result = e_v2f64(doubles);
        v4u32 integers = {{0, UINT32_MAX, 0x80000000, 17}}, integers_result = e_v4u32(integers);
        bad += memcmp(&doubles, &doubles_result, 16) != 0;
        bad += memcmp(&integers, &integers_result, 16) != 0;
        uint64_t stored = 0;
        e_store(&stored, x + 23);
        bad += stored != x + 23;
        _Alignas(16) unsigned char reg[8192] = {{0}}, stack[65536] = {{0}};
        const size_t saved[] = {{0x18, 0x28, 0xa0, 0xa8, 0xb0, 0xb8}};
        for (size_t i = 0; i < 6; i++) {{
            uint64_t sentinel = UINT64_C(0x1234567800000000) + i + x;
            memcpy(reg + saved[i], &sentinel, 8);
        }}
        uintptr_t rsp = (uintptr_t)(stack + sizeof stack - 8);
        uint64_t sentinel_return = UINT64_C(0x9876543212345678);
        memcpy((void *)rsp, &sentinel_return, 8);
        memcpy(reg + 32, &rsp, 8);
        memcpy(reg + 0x38, &x, 8);
        if (x % 2) sub_{nested:x}(reg); else sub_{callback:x}(reg);
        uintptr_t returned_rsp;
        memcpy(&returned_rsp, reg + 32, 8);
        bad += returned_rsp != rsp + 8;
        bad += memcmp((void *)rsp, &sentinel_return, 8) != 0;
        for (size_t i = 0; i < 6; i++) {{
            uint64_t sentinel = UINT64_C(0x1234567800000000) + i + x;
            bad += memcmp(reg + saved[i], &sentinel, 8) != 0;
        }}
    }}
    int translated = -1;
    size_t size = sizeof translated;
    sysctlbyname("sysctl.proc_translated", &translated, &size, NULL, 0);
    printf("{{\\"bad\\":%d,\\"translated\\":%d}}\\n", bad, translated);
    return bad != 0;
}}
"""


@requires_arm64
def test_native_lifted_calls_execute_on_arm64(call_executable):
    assert run(["/usr/bin/lipo", "-archs", call_executable]).strip() == "arm64"
    assert json.loads(run([call_executable], timeout=30)) == {"bad": 0, "translated": 0}


@requires_arm64
def test_unregistered_indirect_target_is_not_invoked(call_executable):
    result = subprocess.run([str(call_executable), "unknown"], capture_output=True, timeout=30)
    assert result.returncode == -6
