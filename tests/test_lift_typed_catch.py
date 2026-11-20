"""Typed catches over real RTTI, matched by the shipped image's own lifted type_info code and run natively on arm64.

The fixture cannot link libstdc++, so its typeinfo objects carry R_X86_64_64 relocations against the type_info
vtables as undefined symbols. The test binds each name to the shipped image's definition of the same symbol, so
the vtable dispatched through is the shipped one, lifted.
"""

import eh_probe
import elf_shim_probe
import lift_abi as abi
import lift_eh as eh
import lift_probe as lp
import lift_reloc as rl
import lift_runtime as rt
import lift_unwind as lu
import pcode_lift as pl
import pytest
import test_lift_shipped_runtime as shipped
import test_lift_unwind_exec as base
from dataclasses import replace

PROVEN = rl.PROVEN_CLASSES
# The vtable slots the personality (is_pointer_p, do_catch) and do_catch/do_upcast (upcast overloads) call through.
DISPATCHED_SLOTS = (4, 6, 7, 8)
EXPORTS = {
    name: abi.Signature(("i32",), "i32")
    for name in ("f_upcast", "f_exact", "f_same", "f_skip", "f_downcast_misses", "f_unmatched")
}
TYPED_PLT = {**shipped.TYPED_PLT, "strcmp": ("native_strcmp", abi.Signature(("ptr", "ptr"), "i32"))}
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
int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "";
    long result = 0;
    if (!strcmp(mode, "upcast")) result = e_upcast(5);
    else if (!strcmp(mode, "exact")) result = e_exact(5);
    else if (!strcmp(mode, "same")) result = e_same(5);
    else if (!strcmp(mode, "skip")) result = e_skip(5);
    else if (!strcmp(mode, "downcast_misses")) result = e_downcast_misses(5);
    else if (!strcmp(mode, "unmatched")) result = e_unmatched(5);
    else return 2;
    printf("R %ld N ", result);
    print_notes();
    printf("\\n");
    return 0;
}
"""
EXTRA_HARNESS = shipped.EXTRA_HARNESS + "int32_t native_strcmp(void *a, void *b) { return strcmp(a, b); }\n"


def build_typed_fixture(work):
    so = work / "typed.so"
    base.run(
        [
            base.LLVM / "clang++",
            "--target=x86_64-linux-gnu",
            "-O1",
            "-fPIC",
            "-ffreestanding",
            "-nostdlib",
            "-nostdinc++",
            "-fexceptions",
            "-funwind-tables",
            "-ftls-model=local-dynamic",
            "-shared",
            "-fuse-ld=lld",
            "-fno-stack-protector",
            "-Wl,-Bsymbolic",
            base.REPO / "tests/fixtures/lift/typed.cpp",
            base.REPO / "tests/fixtures/lift/shipped_stubs.cpp",
            "-o",
            so,
        ]
    )
    return so


def section_bytes(elf, raw, sections, names):
    """File contents of the named sections, zeros for NOBITS."""
    images = {}
    for name in names:
        section = next(s for s in sections if s["name"] == name)
        header = next(h for h in elf.sections if h.addr == section["va"] and h.size == section["size"])
        images[name] = bytes(header.size) if header.type == 8 else raw[header.offset : header.offset + header.size]
    return images


def lift_all(rows, frames, table, base_address, sections, extra_pads=None):
    by_start = {f.pc_begin: f for f in frames}
    bodies = []
    for row in rows:
        pads = frozenset()
        if by_start[row["start"]].lsda:
            lsda = eh.parse_lsda(table, by_start[row["start"]].lsda - base_address, row["start"])
            assert eh.pad_holes(row, lsda) == []
            pads = lsda.pads
        bodies.append(pl.lift_body(row, sections, call_dispatch=True, unwind=True, pads=pads))
    return bodies


@pytest.fixture(scope="module")
def typed_build(tmp_path_factory):
    work = tmp_path_factory.mktemp("lift-typed")
    for name in ("ghidra-shipped", "ghidra-fixture"):
        (work / name).mkdir()
    selfelf = elf_shim_probe.parse_elf(shipped.SHIPPED)
    sraw = shipped.SHIPPED.read_bytes()
    sframes = eh.parse_frames(*eh_probe.read_section(selfelf, sraw, ".eh_frame"))
    sexcept, sexcept_base = eh_probe.read_section(selfelf, sraw, ".gcc_except_table")
    s_by_start = {f.pc_begin: f for f in sframes}

    so = build_typed_fixture(work)
    symbols = shipped.defined_symbols(so)
    elf = elf_shim_probe.parse_elf(so)
    raw = so.read_bytes()
    frames = eh.parse_frames(*eh_probe.read_section(elf, raw, ".eh_frame"))
    except_table, except_base = eh_probe.read_section(elf, raw, ".gcc_except_table")
    f_by_start = {f.pc_begin: f for f in frames}
    lifted = {n: v for n, v in symbols.items() if n not in base.STUBS and n not in shipped.FIXTURE_ONLY}
    rows, sections = lp.dump_pcode(so, [lp.Fde(a, n) for a, n in lifted.values()], work / "ghidra-fixture")
    leaves = {row["start"] for row in rows if lu.is_leaf(row)}

    roots = shipped.symbol_addresses(shipped.SHIPPED, shipped.ROOT_SYMBOLS)
    vtables = shipped.symbol_addresses(shipped.SHIPPED, tuple(PROVEN))
    # The vtable slots are read from the shipped section list, which the first dump supplies.
    first = rt.closure(shipped.SHIPPED, sframes, list(roots.values()), shipped.exported_symbols(shipped.SHIPPED))
    _, first_sections = rt.dump_cached(shipped.SHIPPED, first.bodies, shipped.CACHE, work / "ghidra-shipped")
    simage = rl.load_image(selfelf, sraw, shipped.rename_sections(first_sections))
    vroots = []
    for vtable in vtables.values():
        for slot in DISPATCHED_SLOTS:
            vroots.append(rl.word_patch(simage, vtable + 8 * slot).code)
    reached = rt.closure(shipped.SHIPPED, sframes, list(roots.values()) + vroots, shipped.exported_symbols(shipped.SHIPPED))
    assert not reached.no_frame
    srows, ssections = rt.dump_cached(shipped.SHIPPED, reached.bodies, shipped.CACHE, work / "ghidra-shipped")
    ssections_named = shipped.rename_sections(ssections)
    simage = rl.load_image(selfelf, sraw, ssections_named)
    fimage = rl.load_image(elf, raw, sections)
    linker = {name: (simage, address) for name, address in vtables.items()}

    plan = rl.plan_types(
        fimage,
        except_table,
        except_base,
        [f.lsda for f in frames if f.lsda and f.pc_begin in f_by_start and f.pc_begin in {a for a, _ in lifted.values()}],
        PROVEN,
        linker,
    )
    splan = rl.plan_types(simage, sexcept, sexcept_base, [f.lsda for a in reached.bodies if (f := s_by_start[a]).lsda], PROVEN)
    assert plan.rejected == {} and splan.rejected == {}

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
        typed_ok=plan.proven | splan.proven,
    )
    assert table.problems == []
    bias = lu.address_bias(rows + srows)

    bodies = lift_all(rows, frames, except_table, except_base, sections)
    shipped_bodies = lift_all(srows, sframes, sexcept, sexcept_base, ssections_named)
    assert [(hex(b.start), b.holes) for b in bodies + shipped_bodies if b.holes] == []

    patches = list({**plan.patches, **splan.patches}.values())
    needed = {p.section for p in patches} | {p.target[0] for p in patches if p.target}
    images = base.section_images(elf, raw, sections, bodies)
    simages = base.section_images(selfelf, sraw, ssections_named, shipped_bodies)
    images.update(section_bytes(elf, raw, sections, {n for n in needed if any(s["name"] == n for s in sections)} - images.keys()))
    simages.update(
        section_bytes(
            selfelf, sraw, ssections_named, {n for n in needed if any(s["name"] == n for s in ssections_named)} - simages.keys()
        )
    )
    ir = work / "module.ll"
    ir.write_text(pl.module_for(bodies + shipped_bodies, {**images, **simages}, patches))
    base.run([base.LLVM / "opt", "-passes=verify", "-disable-output", ir])
    obj = work / "module.o"
    base.run([base.LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", ir, "-o", obj])

    plt_address = {name: a for a, name in reached.imports.items()}
    exports = [abi.Binding(symbols[n][0], n.replace("f_", "e_", 1), sig) for n, sig in EXPORTS.items()]
    imports = [abi.Binding(symbols[n][0], native, sig) for n, (native, sig) in base.TYPED.items() if not n.startswith("_Unwind")]
    raw_imports = [abi.RawBinding(symbols[n][0], base.RAW[n]) for n in ("_Unwind_Resume",)]
    unsupported = []
    for name, address in sorted(plt_address.items()):
        if name in shipped.RAW_PLT:
            raw_imports.append(abi.RawBinding(address, shipped.RAW_PLT[name]))
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
    aliases = {symbols[n][0]: roots[n] for n in shipped.FIXTURE_ALIASES}
    aliases[symbols["_ZSt9terminatev"][0]] = plt_address["_ZSt9terminatev"]
    aliases.update(reached.resolved)
    unsupported_c = "".join(
        f'void native_unsupported_{i}(void) {{ fprintf(stderr, "unsupported import {n}\\n"); abort(); }}\n'
        for i, n in enumerate(unsupported, 1)
    )
    callable_bodies = sorted(
        (set(reached.bodies) | {a for a, _ in lifted.values()}) - {b.address for b in exports + imports + raw_imports}
    )
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
    slots = [(s.entry - except_base + fixture_offset, *s.cell, s.size) for s in plan.slots]
    slots += [(s.entry - sexcept_base + shipped_offset, *s.cell, s.size) for s in splan.slots]
    (work / "tables.c").write_text(lu.render_c(combined, bytes(fixture_offset) + except_table + sexcept, 0, bias, slots))
    (work / "harness.c").write_text("#include <stdint.h>\n" + HARNESS + EXTRA_HARNESS + unsupported_c)
    exe = work / "typed"
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
    return exe, plan


@shipped.requires_image
@base.requires_arm64
@pytest.mark.parametrize(
    "mode, expected",
    [
        ("upcast", "R 50 N 105,1"),
        ("exact", "R 6 N"),
        ("same", "R 1005 N"),
        ("skip", "R 5 N 3,2,205"),
        ("downcast_misses", "R 77 N 300"),
    ],
)
def test_typed_catch_matches_through_the_shipped_lifted_type_info(typed_build, mode, expected):
    exe, _ = typed_build
    result = base.execute(exe, mode)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


@shipped.requires_image
@base.requires_arm64
def test_an_unmatched_typed_catch_propagates_to_terminate_without_running_cleanups(typed_build):
    exe, _ = typed_build
    result = base.execute(exe, "unmatched")
    assert result.returncode == -6
    assert result.stdout.strip() == "ABORT N"


def reference_cases():
    lines = (base.REPO / "tests/fixtures/lift/typed_reference.txt").read_text().splitlines()
    return [tuple(line.split("|")) for line in lines if line and not line.startswith("#")]


@shipped.requires_image
@base.requires_arm64
@pytest.mark.parametrize("mode, status, stdout", reference_cases())
def test_lifted_typed_catch_matches_the_stock_libstdcxx_reference(typed_build, mode, status, stdout):
    exe, _ = typed_build
    result = base.execute(exe, mode)
    code = result.returncode if result.returncode >= 0 else 128 - result.returncode
    assert (code, result.stdout.strip()) == (int(status), stdout)
