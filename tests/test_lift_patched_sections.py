"""Relocated words in a lifted module's section globals, and the type-table slots the unwinder's LSDA copy carries."""

import lift_reloc as rl
import lift_unwind as lu
import pcode_lift as pl
import pytest
import subprocess
from pathlib import Path

LLVM = Path("/opt/homebrew/opt/llvm/bin")
IMAGES = {"data": bytes(range(32)), "rodata": bytes(16)}
PATCHES = [rl.Patch("data", 16, 0x1234, None), rl.Patch("data", 8, None, ("rodata", 4))]


def test_a_patched_section_holds_data_pointers_and_code_addresses_where_the_words_lie():
    module = pl.module_for([], IMAGES, PATCHES)
    assert "ptr getelementptr (i8, ptr @sec_rodata, i64 4)" in module
    assert "i64 4660" in module
    assert "@sec_rodata = global [16 x i8]" in module


def test_the_bytes_around_a_patched_word_are_kept():
    module = pl.module_for([], IMAGES, PATCHES)
    assert 'c"\\00\\01\\02\\03\\04\\05\\06\\07"' in module
    assert 'c"\\18\\19\\1A\\1B\\1C\\1D\\1E\\1F"' in module


def test_overlapping_patches_are_refused():
    with pytest.raises(ValueError, match="overlap"):
        pl.module_for([], IMAGES, [rl.Patch("data", 8, 1, None), rl.Patch("data", 12, 2, None)])


def test_a_patch_past_the_end_of_its_section_is_refused():
    with pytest.raises(ValueError, match="past the end"):
        pl.module_for([], IMAGES, [rl.Patch("data", 28, 1, None)])


def test_a_patch_in_a_section_with_no_image_is_refused():
    with pytest.raises(ValueError, match="no image"):
        pl.module_for([], {}, [rl.Patch("data", 0, 1, None)])


@pytest.mark.skipif(not (LLVM / "opt").exists(), reason="needs LLVM")
def test_a_patched_module_verifies(tmp_path):
    ir = tmp_path / "m.ll"
    ir.write_text(pl.module_for([], IMAGES, PATCHES))
    subprocess.run([LLVM / "opt", "-passes=verify", "-disable-output", ir], check=True)


def test_render_c_carries_each_type_slot_as_an_lsda_offset_and_a_section_cell():
    table = lu.Table()
    source = lu.render_c(table, bytes(64), 0x100, 0, type_slots=[(0x120, "sdata", 0x300, 4)])
    assert "extern unsigned char sec_sdata[];" in source
    assert "const lu_type_slot lu_type_slots[] = {\n  {0x20ULL, sec_sdata + 0x300, 4},\n};" in source
    assert "const uint32_t lu_type_slot_count = 1;" in source
    assert "unsigned char lu_lsda_bytes[]" in source and "const unsigned char lu_lsda_bytes" not in source


def test_render_c_without_slots_has_an_empty_slot_table():
    source = lu.render_c(lu.Table(), bytes(8), 0, 0)
    assert "const uint32_t lu_type_slot_count = 0;" in source


def test_a_function_patch_holds_the_host_function_and_declares_it():
    module = pl.module_for([], IMAGES, [rl.Patch("data", 8, None, None, function=0x1234)])
    assert "ptr @sub_1234" in module
    assert "declare void @sub_1234(ptr)" in module


def test_a_function_patch_to_a_body_in_the_module_is_not_redeclared():
    body = pl.lift_body({"start": 0x1234, "size": 1, "insns": [{"a": 0x1234, "len": 1, "m": "x", "ops": []}]})
    module = pl.module_for([body], IMAGES, [rl.Patch("data", 8, None, None, function=0x1234)])
    assert "declare void @sub_1234(ptr)" not in module


@pytest.mark.skipif(not (LLVM / "opt").exists(), reason="needs LLVM")
def test_a_module_with_a_function_patch_verifies(tmp_path):
    ir = tmp_path / "m.ll"
    ir.write_text(pl.module_for([], IMAGES, [rl.Patch("data", 8, None, None, function=0x1234)]))
    subprocess.run([LLVM / "opt", "-passes=verify", "-disable-output", ir], check=True)


def test_a_zero_filled_section_is_a_zeroinitializer_not_a_byte_literal():
    module = pl.module_for([], {"bss": bytes(4096)}, sections=["bss"])
    assert "@sec_bss = global [4096 x i8] zeroinitializer, align 16" in module


def test_a_zero_run_between_patched_words_is_a_zeroinitializer_chunk():
    module = pl.module_for([], {"data": bytes(64)}, [rl.Patch("data", 0, None, None, function=0x10)])
    assert "[56 x i8] zeroinitializer" in module


def test_a_requested_section_is_defined_without_a_body_or_patch_naming_it():
    module = pl.module_for([], IMAGES, sections=["rodata"])
    assert "@sec_rodata = global [16 x i8]" in module
    assert "@sec_data" not in module


def test_a_requested_section_with_no_image_stays_external():
    assert "@sec_tbss = external global i8" in pl.module_for([], {}, sections=["tbss"])


def test_a_read_only_section_is_a_constant_global():
    module = pl.module_for([], IMAGES, sections=["rodata"], readonly={"rodata"})
    assert "@sec_rodata = constant [16 x i8]" in module


def test_a_patched_read_only_section_is_a_constant_global():
    module = pl.module_for([], IMAGES, [rl.Patch("data", 8, 1, None)], readonly={"data"})
    assert "@sec_data = constant <{" in module


def test_a_section_not_named_read_only_stays_a_writable_global():
    assert "@sec_data = global" in pl.module_for([], IMAGES, sections=["data"], readonly={"rodata"})


def test_a_literal_patch_holds_the_literal_word():
    module = pl.module_for([], IMAGES, [rl.Patch("data", 8, None, None, literal=1)])
    assert "i64 1" in module


def test_a_host_patch_points_at_a_declared_external_host_variable():
    module = pl.module_for([], IMAGES, [rl.Patch("data", 8, None, None, host="lift_data_stderr")])
    assert "ptr @lift_data_stderr" in module and "@lift_data_stderr = external global i8" in module


@pytest.mark.skipif(not (LLVM / "opt").exists(), reason="needs LLVM")
def test_a_module_with_read_only_literal_and_host_patches_verifies(tmp_path):
    patches = [rl.Patch("data", 0, None, None, literal=0), rl.Patch("data", 8, None, None, host="lift_data_x")]
    ir = tmp_path / "m.ll"
    ir.write_text(pl.module_for([], IMAGES, patches, readonly={"data"}))
    subprocess.run([LLVM / "opt", "-passes=verify", "-disable-output", ir], check=True)
