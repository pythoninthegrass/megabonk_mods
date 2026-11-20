"""The shipped image's own libsupc++, lifted and run natively on arm64 under the guest unwinder."""

import eh_probe
import elf_shim_probe
import lift_abi as abi
import lift_eh as eh
import lift_probe as lp
import lift_runtime as rt
import lift_unwind as lu
import pcode_lift as pl
import pytest
import test_lift_unwind_exec as base
from dataclasses import replace
from pathlib import Path

SHIPPED = base.REPO / ".tools/megabonk-linux-native/Megabonk/GameAssembly.so"
CACHE = base.REPO / ".tools/lift-runtime-cache"
requires_image = pytest.mark.skipif(
    not SHIPPED.exists() or not base.LLVM.exists() or base.GHIDRA is None,
    reason="needs the shipped Linux GameAssembly.so, LLVM and Ghidra",
)

ROOT_SYMBOLS = (
    "__gxx_personality_v0",
    "__cxa_throw",
    "__cxa_rethrow",
    "__cxa_begin_catch",
    "__cxa_end_catch",
    "__cxa_allocate_exception",
    "__cxa_get_globals",
)
# Fixture stubs that the lifted shipped function of the same name replaces.
FIXTURE_ALIASES = ("__cxa_throw", "__cxa_rethrow", "__cxa_begin_catch", "__cxa_end_catch", "__cxa_allocate_exception")
FIXTURE_ONLY = {"_ZSt9terminatev", "__gxx_personality_v0", "__tls_get_addr", "f_tls", *FIXTURE_ALIASES}
RAW_PLT = {"_Unwind_RaiseException": "lu_raise_exception", "_Unwind_Resume_or_Rethrow": "lu_resume_or_rethrow"}
TYPED_PLT = {
    "_Unwind_GetLanguageSpecificData": base.TYPED["_Unwind_GetLanguageSpecificData"],
    "_Unwind_GetRegionStart": base.TYPED["_Unwind_GetRegionStart"],
    "_Unwind_GetIPInfo": base.TYPED["_Unwind_GetIPInfo"],
    "_Unwind_SetGR": base.TYPED["_Unwind_SetGR"],
    "_Unwind_SetIP": base.TYPED["_Unwind_SetIP"],
    "malloc": ("native_malloc", abi.Signature(("u64",), "ptr")),
    "free": ("native_free", abi.Signature(("ptr",), "void")),
    "abort": ("native_abort_import", abi.Signature((), "void")),
    "_ZSt9terminatev": ("native_terminate", abi.Signature((), "void")),
    "_ZSt14get_unexpectedv": ("native_get_unexpected", abi.Signature((), "ptr")),
    "_ZSt13get_terminatev": ("native_get_terminate", abi.Signature((), "ptr")),
    "_Unwind_DeleteException": ("native_delete_exception", abi.Signature(("ptr",), "void")),
}
EXTRA_HARNESS = """
void *native_malloc(uint64_t size) { return calloc(1, size); }
void native_free(void *p) { (void)p; }
void native_delete_exception(void *p) { (void)p; }
int32_t e_tls(void) { abort(); }
void *native_get_unexpected(void) { return 0; }
void *native_get_terminate(void) { return 0; }
void native_abort_import(void) { native_abort(); }
void native_terminate(void) { native_abort(); }
"""


def symbol_addresses(so, names):
    found = {}
    for line in base.run([base.LLVM / "llvm-nm", "-D", "--defined-only", so]).splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] in names:
            found[fields[2]] = int(fields[0], 16)
    assert found.keys() == set(names), set(names) - found.keys()
    return found


# These stay native imports. The terminate and unexpected handlers are function pointers in unrelocated data;
# the mutex helpers are only reached when malloc fails, and one carries an exception specification.
NATIVE_BOUNDARY = {
    "_ZN9__gnu_cxx7__mutex4lockEv",
    "_ZN9__gnu_cxx13__scoped_lockD1Ev",
    "_ZSt9terminatev",
    "_ZSt10unexpectedv",
    "__cxa_call_terminate",
    "_ZN10__cxxabiv111__terminateEPFvvE",
    "_ZN10__cxxabiv112__unexpectedEPFvvE",
    "_ZSt13get_terminatev",
    "_ZSt14get_unexpectedv",
}


def exported_symbols(so):
    exported = {}
    for line in base.run([base.LLVM / "llvm-nm", "-D", "--defined-only", so]).splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[1] in "TtWw":
            exported[fields[2]] = int(fields[0], 16)
    return {n: a for n, a in exported.items() if n not in NATIVE_BOUNDARY}


def rename_sections(sections):
    return [{**s, "name": "s" + s["name"]} for s in sections]


def build_fixture(work):
    so = work / "fixture.so"
    base.run(
        [
            base.LLVM / "clang++",
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
            base.REPO / "tests/fixtures/lift/unwind.cpp",
            base.REPO / "tests/fixtures/lift/shipped_stubs.cpp",
            "-o",
            so,
        ]
    )
    return so


def defined_symbols(so):
    symbols = {}
    for line in base.run([base.LLVM / "llvm-nm", "--print-size", "--defined-only", so]).splitlines():
        fields = line.split()
        if len(fields) == 4 and fields[2] in "TtWw" and int(fields[1], 16):
            symbols[fields[3]] = (int(fields[0], 16), int(fields[1], 16))
    return symbols


@pytest.fixture(scope="module")
def shipped_executable(tmp_path_factory):
    work = tmp_path_factory.mktemp("lift-shipped")
    for name in ("ghidra-shipped", "ghidra-fixture"):
        (work / name).mkdir()
    selfelf = elf_shim_probe.parse_elf(SHIPPED)
    sraw = SHIPPED.read_bytes()
    sframes = eh.parse_frames(*eh_probe.read_section(selfelf, sraw, ".eh_frame"))
    roots = symbol_addresses(SHIPPED, ROOT_SYMBOLS)
    reached = rt.closure(SHIPPED, sframes, list(roots.values()), exported_symbols(SHIPPED))
    assert not reached.no_frame
    by_start = {f.pc_begin: f for f in sframes}
    sexcept, sexcept_base = eh_probe.read_section(selfelf, sraw, ".gcc_except_table")
    srows, ssections = rt.dump_cached(SHIPPED, reached.bodies, CACHE, work / "ghidra-shipped")
    ssections_named = rename_sections(ssections)

    so = build_fixture(work)
    symbols = defined_symbols(so)
    elf = elf_shim_probe.parse_elf(so)
    raw = so.read_bytes()
    frames = eh.parse_frames(*eh_probe.read_section(elf, raw, ".eh_frame"))
    except_table, except_base = eh_probe.read_section(elf, raw, ".gcc_except_table")
    f_by_start = {f.pc_begin: f for f in frames}
    lifted = {n: v for n, v in symbols.items() if n not in base.STUBS and n not in FIXTURE_ONLY}
    rows, sections = lp.dump_pcode(so, [lp.Fde(a, n) for a, n in lifted.values()], work / "ghidra-fixture")
    leaves = {row["start"] for row in rows if lu.is_leaf(row)}

    personality = symbols["__gxx_personality_v0"][0]
    shipped_personality = roots["__gxx_personality_v0"]
    fixture_resolver = lu.personality_resolver(elf, raw)
    shipped_resolver = lu.personality_resolver(selfelf, sraw)
    fixture_cies = {id(f.cie) for f in frames}

    def resolve(cie):
        if id(cie) not in fixture_cies:
            return shipped_resolver(cie)
        address = fixture_resolver(cie)
        return shipped_personality if address == personality else address

    table = lu.build_entries(
        frames + sframes,
        {a for a, _ in lifted.values()} | set(reached.bodies),
        resolve,
        leaves,
        lsda_tables=[(except_table, except_base), (sexcept, sexcept_base)],
    )
    assert table.problems == []
    bias = lu.address_bias(rows + srows)

    bodies = []
    for row in rows:
        frame = f_by_start[row["start"]]
        pads = frozenset()
        if frame.lsda:
            lsda = eh.parse_lsda(except_table, frame.lsda - except_base, row["start"])
            assert eh.pad_holes(row, lsda) == []
            pads = lsda.pads
        bodies.append(pl.lift_body(row, sections, call_dispatch=True, unwind=True, pads=pads))
    shipped_bodies = []
    for row in srows:
        pads = frozenset()
        if by_start[row["start"]].lsda:
            lsda = eh.parse_lsda(sexcept, by_start[row["start"]].lsda - sexcept_base, row["start"])
            assert eh.pad_holes(row, lsda) == []
            pads = lsda.pads
        shipped_bodies.append(pl.lift_body(row, ssections_named, call_dispatch=True, unwind=True, pads=pads))
    holes = [(hex(b.start), b.holes) for b in bodies + shipped_bodies if b.holes]
    assert holes == []

    images = base.section_images(elf, raw, sections, bodies)
    simages = base.section_images(selfelf, sraw, ssections_named, shipped_bodies)
    ir = work / "module.ll"
    ir.write_text(pl.module_for(bodies + shipped_bodies, {**images, **simages}))
    base.run([base.LLVM / "opt", "-passes=verify", "-disable-output", ir])
    obj = work / "module.o"
    base.run([base.LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", ir, "-o", obj])

    plt = reached.imports
    plt_address = {name: a for a, name in plt.items()}
    exports = [abi.Binding(symbols[n][0], n.replace("f_", "e_", 1), sig) for n, sig in base.EXPORTS.items() if n != "f_tls"]
    imports = [abi.Binding(symbols[n][0], native, sig) for n, (native, sig) in base.TYPED.items() if not n.startswith("_Unwind")]
    raw_imports = [abi.RawBinding(symbols[n][0], base.RAW[n]) for n in ("_Unwind_Resume", "poison")]
    unsupported = []
    for name, address in sorted(plt_address.items()):
        if name in RAW_PLT:
            raw_imports.append(abi.RawBinding(address, RAW_PLT[name]))
        elif name in TYPED_PLT:
            native, sig = TYPED_PLT[name]
            imports.append(abi.Binding(address, native, sig))
        elif name == "__tls_get_addr":
            continue
        else:
            unsupported.append(name)
            imports.append(abi.Binding(address, f"native_unsupported_{len(unsupported)}", abi.Signature((), "void")))
    for address in sorted(reached.taken):
        unsupported.append(f"function pointer {address:#x}")
        imports.append(abi.Binding(address, f"native_unsupported_{len(unsupported)}", abi.Signature((), "void")))
    aliases = {symbols[n][0]: roots[n] for n in FIXTURE_ALIASES}
    aliases[symbols["_ZSt9terminatev"][0]] = plt_address["_ZSt9terminatev"]
    aliases.update(reached.resolved)
    unsupported_c = "".join(
        f'void native_unsupported_{i}(void) {{ fprintf(stderr, "unsupported import {n}\\n"); abort(); }}\n'
        for i, n in enumerate(unsupported, 1)
    )
    callable_bodies = sorted(set(reached.bodies) - {b.address for b in exports + imports + raw_imports})
    (work / "adapters.c").write_text(
        abi.generate(
            exports,
            imports,
            raw_imports,
            callable_bodies,
            tls=abi.Tls(plt_address["__tls_get_addr"], abi.tls_image(selfelf, sraw)),
            aliases=aliases,
        )
    )
    # One LSDA address space with the fixture's table after a pad, so no LSDA sits at the address 0 that means none.
    fixture_offset = 16
    shipped_offset = fixture_offset + len(except_table)
    combined = lu.Table(
        [
            replace(
                e,
                lsda=e.lsda - except_base + fixture_offset
                if e.pc_begin in f_by_start
                else e.lsda - sexcept_base + shipped_offset,
            )
            if e.lsda
            else e
            for e in table.entries
        ]
    )
    (work / "tables.c").write_text(lu.render_c(combined, bytes(fixture_offset) + except_table + sexcept, 0, bias))
    (work / "harness.c").write_text("#include <stdint.h>\nint32_t e_tls(void);\n" + base.HARNESS + EXTRA_HARNESS + unsupported_c)
    exe = work / "shipped"
    base.run(
        [
            base.LLVM / "clang",
            "-arch",
            "arm64",
            "-O1",
            f"-I{base.RUNTIME}",
            f"-I{work}",
            work / "harness.c",
            work / "tables.c",
            base.RUNTIME / "runtime.c",
            obj,
            "-o",
            exe,
        ]
    )
    return exe


@requires_image
@base.requires_arm64
@pytest.mark.parametrize(
    "mode, expected",
    [
        ("catch0", "R 7 N 100,2,1 D 0"),
        ("catch1", "R 5 N 2,200,1 D 0"),
        ("nested0", "R 0 N 21,20,11,10 D 0"),
        ("nested1", "R 1 N 20,10,99 D 0"),
        ("rethrow1", "R 9 N 300,301,3 D 0"),
        ("regs", "R 273 N  D 0"),
    ],
)
def test_shipped_libsupc_lifted_matches_the_expected_unwind(shipped_executable, mode, expected):
    result = base.execute(shipped_executable, mode)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


@requires_image
@base.requires_arm64
def test_shipped_libsupc_lifted_terminates_on_an_uncaught_exception(shipped_executable):
    result = base.execute(shipped_executable, "uncaught")
    assert result.returncode == -6
    assert result.stdout.strip() == "ABORT N"
