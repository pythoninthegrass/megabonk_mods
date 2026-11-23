"""Execute a rebuilt image: relocated data, vtable dispatch and function-pointer identity across linked shards."""

import ctypes
import elf_shim_probe as elf
import lift_abi as abi
import lift_bind as bind
import lift_imports as imports
import lift_link as ll
import lift_reloc as rl
import os
import pytest
import subprocess
import sys
import test_lift_link as tl
import test_pcode_lift as t

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or os.uname().machine != "arm64" or not (tl.lp.LLVM / "llc").exists(),
    reason="needs native arm64 macOS and LLVM",
)

SECTIONS = [
    {"name": "text", "va": 0x1000, "size": 0x2000, "exec": True},
    {"name": "plt", "va": 0x3000, "size": 0x40, "exec": True},
    {"name": "rodata", "va": 0x4000, "size": 0x20, "exec": False},
    {"name": "relro", "va": 0x4100, "size": 0x20, "exec": False},
    {"name": "data", "va": 0x5000, "size": 0x40, "exec": False},
    {"name": "bss", "va": 0x6000, "size": 0x10, "exec": False},
]
SEGMENTS = [
    elf.Segment(rl.PT_LOAD, 5, 0, 0x1000, 0x2040, 0x2040, 0x1000),
    elf.Segment(rl.PT_LOAD, 4, 0, 0x4000, 0x120, 0x120, 0x1000),
    elf.Segment(rl.PT_GNU_RELRO, 4, 0, 0x4100, 0x20, 0x20, 0x1000),
    elf.Segment(rl.PT_LOAD, 6, 0, 0x5000, 0x40, 0x40, 0x1000),
    elf.Segment(rl.PT_LOAD, 6, 0, 0x6000, 0x0, 0x10, 0x1000),
]
SEVEN, NINE, SLOT_NINE, SLOT_SEVEN, STORE = 0x1000, 0x1100, 0x2000, 0x2100, 0x2200
VTABLE, DATA, BSS, RELRO = 0x4000, 0x5000, 0x6000, 0x4100
STUB, PLT0 = 0x3010, 0x3000
RELOCS = {
    VTABLE: rl.Reloc(rl.R_X86_64_RELATIVE, 0, SEVEN),
    VTABLE + 8: rl.Reloc(rl.R_X86_64_RELATIVE, 0, NINE),
    VTABLE + 0x10: rl.Reloc(rl.R_X86_64_RELATIVE, 0, DATA + 8),
    RELRO: rl.Reloc(rl.R_X86_64_RELATIVE, 0, SEVEN),
    DATA: rl.Reloc(rl.R_X86_64_RELATIVE, 0, SEVEN),
    DATA + 0x10: rl.Reloc(rl.R_X86_64_JUMP_SLOT, 0, 0),
    DATA + 0x18: rl.Reloc(rl.R_X86_64_GLOB_DAT, 1, 0),
    DATA + 0x20: rl.Reloc(rl.R_X86_64_DTPMOD64, 0, 0),
    DATA + 0x28: rl.Reloc(rl.R_X86_64_64, 2, 0),
    DATA + 0x30: rl.Reloc(rl.R_X86_64_RELATIVE, 0, PLT0),
}
SYMBOLS = [rl.Sym("seven", SEVEN, 0, True), rl.Sym("stderr", 0, 0, False, False, True), rl.Sym("imported", 0, 0, False)]


def returns(value, start):
    return {
        **t.body(
            t.insn(start, 2, t.op("COPY", "register,0,8", f"const,{value},8")),
            t.insn(start + 2, 1, t.op("RETURN", None, "register,288,8")),
            start=start,
        ),
        "undecoded": 0,
    }


def dispatches_through(slot, start):
    return {
        **t.body(
            t.insn(start, 7, t.op("COPY", "register,0,8", f"ram,{slot:x},8")),
            t.insn(start + 7, 2, t.op("CALLIND", None, "register,0,8")),
            t.insn(start + 9, 1, t.op("RETURN", None, "register,288,8")),
            start=start,
        ),
        "undecoded": 0,
    }


def stores_into_data(start):
    return {
        **t.body(
            t.insn(start, 8, t.op("COPY", f"ram,{DATA + 8:x},8", "const,0x1234,8")),
            t.insn(start + 8, 7, t.op("COPY", "register,8,8", f"ram,{BSS:x},8")),
            t.insn(start + 15, 1, t.op("RETURN", None, "register,288,8")),
            start=start,
        ),
        "undecoded": 0,
    }


@pytest.fixture(scope="module")
def image(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("image")
    shards = [
        [returns(7, SEVEN), returns(9, NINE), dispatches_through(VTABLE + 8, SLOT_NINE)],
        [dispatches_through(VTABLE, SLOT_SEVEN), stores_into_data(STORE)],
    ]
    parts = tl.write_baseline(tmp_path, shards, SECTIONS)
    img = rl.Image(SECTIONS, RELOCS, SYMBOLS, protection=rl.protection(SEGMENTS, SECTIONS))
    plan = rl.plan_image(img, frozenset(b["start"] for shard in shards for b in shard))
    bound = bind.bind_words(plan, img, {STUB: "imported"})
    host = abi.generate([], [], callable_bodies=[SEVEN], aliases={STUB: SEVEN})
    host += imports.abort_source(bound.aborts) + imports.abort_stubs(bound.aborts) + bound.source
    sizes = {s["name"]: bytes(s["size"]) for s in SECTIONS}
    summary = ll.link_image(tl.context(tmp_path, host_source=host), parts, plan, lambda names: sizes)
    return ctypes.CDLL(summary["dylib"]), summary["dylib"]


def run(lib, symbol):
    reg, stack = (ctypes.c_ubyte * 8192)(), (ctypes.c_ubyte * 4096)()
    ctypes.c_uint64.from_buffer(reg, 32).value = ctypes.addressof(stack) + 2048
    getattr(lib, symbol)(reg)
    return ctypes.c_uint64.from_buffer(reg, 0).value


def word(lib, section, size, offset):
    return ctypes.c_uint64.from_buffer((ctypes.c_ubyte * size).in_dll(lib, f"sec_{section}"), offset)


def pointer(lib, name):
    return ctypes.cast(getattr(lib, name), ctypes.c_void_p).value


def test_a_vtable_slot_dispatches_to_the_function_its_relocated_word_names(image):
    lib, _ = image
    assert run(lib, f"sub_{SLOT_NINE:x}") == 9
    assert run(lib, f"sub_{SLOT_SEVEN:x}") == 7


def test_a_lifted_store_into_a_relocated_section_is_visible_and_leaves_its_neighbors(image):
    lib, _ = image
    run(lib, f"sub_{STORE:x}")
    assert word(lib, "data", 0x40, 8).value == 0x1234
    assert word(lib, "data", 0x40, 0).value == pointer(lib, "sub_1000")


def test_the_zero_filled_section_starts_zero_and_takes_a_write(image):
    lib, _ = image
    cells = (ctypes.c_ubyte * 0x10).in_dll(lib, "sec_bss")
    assert not any(cells)
    cells[3] = 5
    assert cells[3] == 5


def test_two_words_naming_one_body_hold_the_same_pointer_as_the_symbol(image):
    lib, _ = image
    assert word(lib, "rodata", 0x20, 0).value == word(lib, "data", 0x40, 0).value == pointer(lib, "sub_1000")


def test_a_slot_resolved_against_an_image_symbol_holds_the_body_pointer_not_its_stub(image):
    lib, _ = image
    assert word(lib, "data", 0x40, 0x10).value == pointer(lib, "sub_1000") != pointer(lib, f"sub_{STUB:x}")


def test_a_word_naming_an_import_holds_the_pointer_of_that_imports_stub(image):
    lib, _ = image
    assert word(lib, "data", 0x40, 0x28).value == pointer(lib, f"sub_{STUB:x}")
    assert run(lib, f"sub_{STUB:x}") == 7


def test_a_word_naming_the_plt_resolver_holds_a_defined_abort_entry(image):
    lib, _ = image
    assert word(lib, "data", 0x40, 0x30).value == pointer(lib, f"sub_{PLT0:x}")


def test_a_data_pointer_word_points_into_the_section_it_names(image):
    lib, _ = image
    assert word(lib, "rodata", 0x20, 0x10).value == ctypes.addressof(ctypes.c_ubyte.in_dll(lib, "sec_data")) + 8


def test_a_data_import_word_points_at_the_host_variable_holding_the_process_stream(image):
    lib, _ = image
    variable = ctypes.c_void_p.in_dll(lib, "lift_data_stderr")
    assert word(lib, "data", 0x40, 0x18).value == ctypes.addressof(variable)
    assert variable.value == ctypes.c_void_p.in_dll(ctypes.CDLL(None), "__stderrp").value


def test_the_tls_module_word_holds_the_single_module_id(image):
    lib, _ = image
    assert word(lib, "data", 0x40, 0x20).value == rl.TLS_MODULE_ID


def write_to(dylib, section):
    code = (
        "import ctypes,sys;lib=ctypes.CDLL(sys.argv[1]);"
        f"ctypes.memmove(ctypes.addressof(ctypes.c_ubyte.in_dll(lib,'sec_{section}')),b'\\x01',1)"
    )
    return subprocess.run([sys.executable, "-I", "-c", code, dylib], capture_output=True, timeout=60).returncode


def test_a_write_into_the_read_only_section_faults_while_a_writable_section_takes_it(image):
    _, dylib = image
    assert write_to(dylib, "data") == 0
    assert write_to(dylib, "rodata") < 0


def test_a_relro_word_is_relocated_then_enforced_read_only_in_the_loaded_image(image):
    lib, dylib = image
    assert word(lib, "relro", 0x20, 0).value == pointer(lib, "sub_1000")
    assert write_to(dylib, "relro") < 0
