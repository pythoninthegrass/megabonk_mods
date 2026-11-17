"""Lifted C++ exception propagation executed natively on arm64 against the guest unwinder."""

import eh_probe
import elf_shim_probe
import lift_abi as abi
import lift_eh as eh
import lift_probe as lp
import lift_unwind as lu
import os
import pcode_lift as pl
import pytest
import subprocess
import sys
from pathlib import Path

LLVM = Path("/opt/homebrew/opt/llvm/bin")
GHIDRA = next(iter(sorted(Path("/opt/homebrew/Cellar/ghidra").glob("*/libexec/support/analyzeHeadless"))), None)
REPO = Path(__file__).resolve().parents[1]
RUNTIME = REPO / "scripts/unwind_runtime"
requires_arm64 = pytest.mark.skipif(
    sys.platform != "darwin" or os.uname().machine != "arm64" or not (LLVM / "clang").exists() or GHIDRA is None,
    reason="needs native arm64 macOS, LLVM and Ghidra",
)

STUBS = {
    "_Unwind_RaiseException",
    "_Unwind_Resume",
    "_Unwind_Resume_or_Rethrow",
    "_Unwind_GetLanguageSpecificData",
    "_Unwind_GetRegionStart",
    "_Unwind_GetIPInfo",
    "_Unwind_SetGR",
    "_Unwind_SetIP",
    "native_note",
    "native_abort",
    "poison",
    "__tls_get_addr",
}
REENTER_STUBS = {"native_reenter"}
REENTER_TYPED = {"native_reenter": ("native_reenter", abi.Signature(("i32",), "i32"))}
REENTER_EXPORTS = {"f_reenter": abi.Signature(("i32",), "i32")}
RAW = {
    "_Unwind_RaiseException": "lu_raise_exception",
    "_Unwind_Resume": "lu_resume",
    "_Unwind_Resume_or_Rethrow": "lu_resume_or_rethrow",
    "poison": "lu_poison",
}
TYPED = {
    "_Unwind_GetLanguageSpecificData": ("lu_get_language_specific_data", abi.Signature(("ptr",), "ptr")),
    "_Unwind_GetRegionStart": ("lu_get_region_start", abi.Signature(("ptr",), "u64")),
    "_Unwind_GetIPInfo": ("lu_get_ip_info", abi.Signature(("ptr", "ptr"), "u64")),
    "_Unwind_SetGR": ("lu_set_gr", abi.Signature(("ptr", "i32", "u64"), "void")),
    "_Unwind_SetIP": ("lu_set_ip", abi.Signature(("ptr", "u64"), "void")),
    "native_note": ("native_note", abi.Signature(("i32",), "void")),
    "native_abort": ("native_abort", abi.Signature((), "void")),
}
EXPORTS = {
    "f_catch": abi.Signature(("i32",), "i32"),
    "f_nested": abi.Signature(("i32",), "i32"),
    "f_rethrow": abi.Signature(("i32",), "i32"),
    "f_regs": abi.Signature(("i64",), "i64"),
    "f_uncaught": abi.Signature((), "i32"),
    "f_depth": abi.Signature((), "i32"),
    "f_leak": abi.Signature((), "i32"),
    "f_tls": abi.Signature((), "i32"),
}

HARNESS = """
#include "adapters.c"
#include <stdio.h>
static int notes[64], count;
void native_note(int32_t id) { notes[count++] = id; }
static void print_notes(void) {
    for (int i = 0; i < count; i++) printf("%s%d", i ? "," : "", notes[i]);
}
void native_abort(void) {
    printf("ABORT N ");
    print_notes();
    printf("\\n");
    fflush(stdout);
    abort();
}
void lu_poison(unsigned char *reg) {
    uint64_t pending = 1, rsp;
    memcpy(reg + 0x1F00, &pending, 8);
    memcpy(&rsp, reg + 0x20, 8);
    rsp += 8;
    memcpy(reg + 0x20, &rsp, 8);
}
int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "";
    long result = 0;
    if (!strcmp(mode, "catch0")) result = e_catch(0);
    else if (!strcmp(mode, "catch1")) result = e_catch(1);
    else if (!strcmp(mode, "nested0")) result = e_nested(0);
    else if (!strcmp(mode, "nested1")) result = e_nested(1);
    else if (!strcmp(mode, "rethrow1")) result = e_rethrow(1);
    else if (!strcmp(mode, "regs")) result = e_regs(7);
    else if (!strcmp(mode, "uncaught")) result = e_uncaught();
    else if (!strcmp(mode, "leak")) result = e_leak();
    else if (!strcmp(mode, "tls")) { result = e_tls(); printf("R %ld ", result); result = e_tls(); }
    else return 2;
    printf("R %ld N ", result);
    print_notes();
    printf(" D %d\\n", e_depth());
    return 0;
}
"""

# Extra harness code for the re-entry fixture only; the other fixtures share HARNESS.
REENTER_HARNESS = HARNESS.replace(
    "void lu_poison(",
    "int32_t native_reenter(int32_t x) { return x == 2 ? e_uncaught() : e_catch(x); }\nvoid lu_poison(",
).replace(
    '    else if (!strcmp(mode, "tls"))',
    """    else if (!strcmp(mode, "reenter0")) result = e_reenter(0);
    else if (!strcmp(mode, "reenter1")) result = e_reenter(1);
    else if (!strcmp(mode, "reenter2")) result = e_reenter(2);
    else if (!strcmp(mode, "tls"))""",
)


def run(command, **kwargs):
    result = subprocess.run([str(c) for c in command], capture_output=True, text=True, **kwargs)
    assert result.returncode == 0, f"{command}: {result.stdout[-1000:]} {result.stderr[-2000:]}"
    return result.stdout


def section_images(elf, raw, sections, bodies):
    """Initial bytes of every data section the lifted bodies touch: file contents, or zeros for NOBITS."""
    images = {}
    for name in set().union(*(b.data_sections for b in bodies)):
        section = next(s for s in sections if s["name"] == name)
        header = next(h for h in elf.sections if h.addr == section["va"] and h.size == section["size"])
        images[name] = bytes(header.size) if header.type == 8 else raw[header.offset : header.offset + header.size]
    return images


@pytest.fixture(scope="module")
def unwind_executable(tmp_path_factory):
    work = tmp_path_factory.mktemp("lift-unwind")
    so = work / "unwind.so"
    run(
        [
            LLVM / "clang++",
            "--target=x86_64-linux-gnu",
            "-O1",
            "-fPIC",
            "-ffreestanding",
            "-nostdlib",
            "-nostdinc++",
            "-fno-rtti",
            "-fexceptions",
            "-funwind-tables",
            "-ftls-model=local-dynamic",
            "-shared",
            "-fuse-ld=lld",
            "-fno-stack-protector",
            "-Wl,-Bsymbolic",
            REPO / "tests/fixtures/lift/unwind.cpp",
            REPO / "tests/fixtures/lift/unwind_runtime.cpp",
            REPO / "tests/fixtures/lift/unwind_stubs.cpp",
            REPO / "tests/fixtures/lift/unwind_reenter.cpp",
            REPO / "tests/fixtures/lift/unwind_reenter_stub.cpp",
            "-o",
            so,
        ]
    )
    symbols = {}
    for line in run([LLVM / "llvm-nm", "--print-size", "--defined-only", so]).splitlines():
        fields = line.split()
        if len(fields) == 4 and fields[2] in "TtWw" and int(fields[1], 16):
            symbols[fields[3]] = (int(fields[0], 16), int(fields[1], 16))
    assert symbols.keys() >= STUBS | REENTER_STUBS
    lifted = {n: v for n, v in symbols.items() if n not in STUBS | REENTER_STUBS}
    elf = elf_shim_probe.parse_elf(so)
    raw = so.read_bytes()
    frames = eh.parse_frames(*eh_probe.read_section(elf, raw, ".eh_frame"))
    except_table, except_base = eh_probe.read_section(elf, raw, ".gcc_except_table")
    by_start = {f.pc_begin: f for f in frames}
    functions = [lp.Fde(address, size) for address, size in lifted.values()]
    rows, sections = lp.dump_pcode(so, functions, work)
    leaves = {row["start"] for row in rows if lu.is_leaf(row)}
    table = lu.build_entries(frames, {a for a, _ in lifted.values()}, lu.personality_resolver(elf, raw), leaves)
    assert table.problems == []
    bodies = []
    for row in rows:
        frame = by_start[row["start"]]
        pads = frozenset()
        if frame.lsda:
            lsda = eh.parse_lsda(except_table, frame.lsda - except_base, row["start"])
            assert eh.pad_holes(row, lsda) == []
            pads = lsda.pads
        bodies.append(pl.lift_body(row, sections, call_dispatch=True, unwind=True, pads=pads))
    assert all(not body.holes for body in bodies), [(hex(b.start), b.holes) for b in bodies if b.holes]
    ir = work / "unwind.ll"
    ir.write_text(pl.module_for(bodies, section_images(elf, raw, sections, bodies)))
    run([LLVM / "opt", "-passes=verify", "-disable-output", ir])
    obj = work / "unwind.o"
    run([LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", ir, "-o", obj])
    exports = [abi.Binding(symbols[n][0], n.replace("f_", "e_", 1), sig) for n, sig in {**EXPORTS, **REENTER_EXPORTS}.items()]
    imports = [abi.Binding(symbols[n][0], native, sig) for n, (native, sig) in {**TYPED, **REENTER_TYPED}.items()]
    raw_imports = [abi.RawBinding(symbols[n][0], native) for n, native in RAW.items()]
    (work / "adapters.c").write_text(
        abi.generate(
            exports,
            imports,
            raw_imports,
            sorted({e.personality for e in table.entries if e.personality}),
            tls=abi.Tls(symbols["__tls_get_addr"][0], abi.tls_image(elf, raw)),
        )
    )
    (work / "tables.c").write_text(lu.render_c(table, except_table, except_base, lu.address_bias(rows)))
    (work / "harness.c").write_text(REENTER_HARNESS)
    exe = work / "unwind"
    run(
        [
            LLVM / "clang",
            "-arch",
            "arm64",
            "-O1",
            f"-I{RUNTIME}",
            f"-I{work}",
            work / "harness.c",
            work / "tables.c",
            RUNTIME / "runtime.c",
            obj,
            "-o",
            exe,
        ]
    )
    return exe


def execute(exe, mode):
    return subprocess.run([str(exe), mode], capture_output=True, text=True, timeout=30)


@requires_arm64
@pytest.mark.parametrize(
    "mode, expected",
    [
        ("catch0", "R 7 N 100,2,1 D 0"),
        ("catch1", "R 5 N 2,200,1 D 0"),
        ("nested0", "R 0 N 21,20,11,10 D 0"),
        ("nested1", "R 1 N 20,10,99 D 0"),
        ("rethrow1", "R 9 N 300,301,3 D 0"),
        ("regs", "R 273 N  D 0"),
        ("reenter0", "R 7 N 100,2,1,7,101,60 D 0"),
        ("reenter1", "R 105 N 2,200,1,5,61,60 D 0"),
    ],
)
def test_lifted_exceptions_match_the_expected_unwind(unwind_executable, mode, expected):
    result = execute(unwind_executable, mode)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


@requires_arm64
def test_an_uncaught_exception_terminates_without_running_cleanups(unwind_executable):
    result = execute(unwind_executable, "uncaught")
    assert result.returncode == -6
    assert result.stdout.strip() == "ABORT N"


@requires_arm64
def test_a_pending_exception_that_reaches_an_export_aborts(unwind_executable):
    result = execute(unwind_executable, "leak")
    assert result.returncode == -6
    assert result.stdout.strip() == ""


@requires_arm64
def test_each_export_call_gets_its_own_initialised_tls_block(unwind_executable):
    result = execute(unwind_executable, "tls")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "R 2042 R 2042 N  D 0"


@requires_arm64
def test_an_exception_uncaught_in_a_reentered_export_terminates_without_unwinding_the_outer_frame(unwind_executable):
    result = execute(unwind_executable, "reenter2")
    assert result.returncode == -6
    assert result.stdout.strip() == "ABORT N"
