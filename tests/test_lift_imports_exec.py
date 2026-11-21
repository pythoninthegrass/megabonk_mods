"""Execute lifted bodies that call generated import stubs; every binary runs as a subprocess with a timeout."""

import lift_abi as abi
import lift_imports as li
import lift_probe as lp
import lift_sdk as sdk
import os
import pcode_lift as pl
import pytest
import signal
import subprocess
import sys
import test_pcode_lift as t

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or os.uname().machine != "arm64" or not (lp.LLVM / "clang").exists(),
    reason="needs native arm64 macOS and LLVM",
)

CALLER = 0x2000
STUB = 0x5000
IMAGE_BODY = 0x3000
IMAGE_STUB = 0x5800


@pytest.fixture(scope="module")
def measured():
    return sdk.load()


def caller(start, stub):
    """A lifted body that calls one stub and returns, the shape a PLT call has in lifted code."""
    return {
        **t.body(
            t.insn(start, 5, t.op("CALL", None, f"ram,{stub:x},8")),
            t.insn(start + 5, 1, t.op("RETURN", None, "register,288,8")),
            start=start,
        ),
        "undecoded": 0,
    }


def returns_seven(start):
    """An image function: rax = 7, then the pop of the return address a `ret` performs."""
    ops = [
        t.op("COPY", "register,0,8", "const,7,8"),
        t.op("INT_ADD", "register,20,8", "register,20,8", "const,8,8"),
        t.op("RETURN", None, "register,288,8"),
    ]
    return {**t.body(t.insn(start, 6, *ops), start=start), "undecoded": 0}


def build(tmp_path, view, imports, driver, shared=False):
    """Lift one caller per export, define every stub, and link them with a driver; returns the output path.

    `imports` is (export name, signature, import name); each gets its own caller body and stub address.
    """
    stubs = {STUB + 0x10 * i: name for i, (_, _, name) in enumerate(imports)}
    stubs[IMAGE_STUB] = "il2cpp_seven"
    plan = li.plan_stubs(view, stubs, {"il2cpp_seven": IMAGE_BODY}, {IMAGE_BODY})
    exports, bodies = [], [returns_seven(IMAGE_BODY)]
    for i, (export, signature, _) in enumerate(imports):
        exports.append(abi.Binding(CALLER + 0x10 * i, export, signature))
        bodies.append(caller(CALLER + 0x10 * i, STUB + 0x10 * i))
    exports.append(abi.Binding(CALLER + 0x10 * len(imports), "call_seven", abi.Signature((), "u64")))
    bodies.append(caller(CALLER + 0x10 * len(imports), IMAGE_STUB))
    lifted = [pl.lift_body(row) for row in bodies]
    ir, shim, source = tmp_path / "lifted.ll", tmp_path / "shim.c", tmp_path / "driver.c"
    ir.write_text(pl.module_for(lifted))
    shim.write_text(
        abi.generate(exports, plan.imports, callable_bodies=[IMAGE_BODY], aliases=plan.aliases)
        + li.abort_source(plan.rows)
        + "\n"
        + li.abort_stubs(plan.rows)
        + "\n"
    )
    source.write_text(driver)
    out = tmp_path / ("libimports.dylib" if shared else "imports")
    flags = ["-dynamiclib", "-Wl,-undefined,error"] if shared else []
    subprocess.run(
        [lp.LLVM / "clang", "-arch", "arm64", "-O2", *flags, ir, shim, source, "-o", out],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return out, plan


def run(exe, *args):
    return subprocess.run([str(exe), *args], capture_output=True, text=True, timeout=30)


FORWARDING = [
    ("call_abs", abi.Signature(("i32",), "i32"), "abs"),
    ("call_strlen", abi.Signature(("ptr",), "u64"), "strlen"),
    ("call_atan2", abi.Signature(("f64", "f64"), "f64"), "atan2"),
    ("call_memchr", abi.Signature(("ptr", "i32", "u64"), "ptr"), "memchr"),
    ("call_sinf", abi.Signature(("f32",), "f32"), "sinf"),
]
DRIVER = """
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
int32_t call_abs(int32_t);
uint64_t call_strlen(void *);
double call_atan2(double, double);
void *call_memchr(void *, int32_t, uint64_t);
float call_sinf(float);
uint64_t call_seven(void);
int main(void) {
  char text[] = "hello";
  printf("%d %llu %.6f %d %.6f %llu\\n", call_abs(-5), (unsigned long long)call_strlen(text), call_atan2(1.0, 1.0),
         (int)((char *)call_memchr(text, 'l', 5) - text), call_sinf(0.5f), (unsigned long long)call_seven());
  return 0;
}
"""


@pytest.fixture(scope="module")
def forwarding(tmp_path_factory, measured):
    exe, plan = build(tmp_path_factory.mktemp("forward"), measured, FORWARDING, DRIVER)
    return exe, plan


def test_a_bound_import_forwards_integer_pointer_double_and_float_arguments_and_results(forwarding):
    result = run(forwarding[0])
    assert result.returncode == 0, result.stderr
    assert result.stdout.split()[:5] == ["5", "5", "0.785398", "2", f"{__import__('math').sin(0.5):.6f}"]


def test_a_stub_of_a_function_the_image_defines_forwards_to_that_body(forwarding):
    assert run(forwarding[0]).stdout.split()[5] == "7"
    assert forwarding[1].aliases == {IMAGE_STUB: IMAGE_BODY}


REFUSED = [
    ("call_fseek", "fseek", "record parameter"),
    ("call_sprintf", "sprintf", "variadic"),
    ("call_read", "read", sdk.OUTSIDE),
    ("call_ctype", "__ctype_b_loc", sdk.ABSENT),
]
REFUSED_DRIVER = """
#include <stdint.h>
#include <string.h>
uint64_t call_fseek(void);
uint64_t call_sprintf(void);
uint64_t call_read(void);
uint64_t call_ctype(void);
uint64_t call_seven(void);
int main(int argc, char **argv) {
  if (!strcmp(argv[1], "fseek")) return (int)call_fseek();
  if (!strcmp(argv[1], "sprintf")) return (int)call_sprintf();
  if (!strcmp(argv[1], "read")) return (int)call_read();
  if (!strcmp(argv[1], "ctype")) return (int)call_ctype();
  return 0;
}
"""


@pytest.fixture(scope="module")
def refused(tmp_path_factory, measured):
    imports = [(export, abi.Signature((), "u64"), name) for export, name, _ in REFUSED]
    return build(tmp_path_factory.mktemp("refused"), measured, imports, REFUSED_DRIVER)[0]


@pytest.mark.parametrize(
    "mode, name, reason",
    [
        ("fseek", "fseek", "record parameter"),
        ("sprintf", "sprintf", "variadic"),
        ("read", "read", sdk.OUTSIDE),
        ("ctype", "__ctype_b_loc", sdk.ABSENT),
    ],
)
def test_a_refused_import_aborts_naming_the_symbol_and_the_reason(refused, mode, name, reason):
    result = run(refused, mode)
    assert result.returncode == -signal.SIGABRT
    assert f"lift_import_refused: {name}: {reason}" in result.stderr


def test_a_dylib_defines_every_stub_and_loads_in_a_fresh_process(tmp_path_factory, measured):
    work = tmp_path_factory.mktemp("dylib")
    dylib, _ = build(work, measured, FORWARDING, "int unused_main_marker;\n", shared=True)
    undefined = subprocess.run([lp.LLVM / "llvm-nm", "-u", dylib], capture_output=True, text=True, check=True).stdout
    assert not [line for line in undefined.split() if line.lstrip("_").startswith("sub_")]
    arch = subprocess.run(["lipo", "-archs", str(dylib)], capture_output=True, text=True, check=True).stdout.split()
    assert arch == ["arm64"]
    loader = work / "loader.c"
    loader.write_text(
        '#include <dlfcn.h>\n#include <stdio.h>\nint main(int c, char **v) { return dlopen(v[1], RTLD_NOW) ? 0 : (puts(dlerror()), 1); }\n'
    )
    program = work / "loader"
    subprocess.run([lp.LLVM / "clang", "-arch", "arm64", loader, "-o", program], check=True, capture_output=True, timeout=60)
    result = run(program, str(dylib))
    assert result.returncode == 0, result.stdout + result.stderr
