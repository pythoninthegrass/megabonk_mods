"""Unit tests for applying an image's relocations to the data words a lifted typed catch reads."""

import lift_eh as eh
import lift_reloc as rl
import pytest
import struct
from test_lift_eh import hand_lsda

SECTIONS = [
    {"name": "text", "va": 0x1000, "size": 0x1000, "exec": True},
    {"name": "rodata", "va": 0x3000, "size": 0x100, "exec": False},
    {"name": "data", "va": 0x4000, "size": 0x1000, "exec": False},
]
CLASS_VTABLE = 0x4100
TYPEINFO = 0x4200
CELL = 0x4300
NAME = 0x3010
LSDA_BASE = 0x6000


def image(relocs=(), symbols=(), words=None):
    return rl.Image(
        sections=SECTIONS,
        relocs={offset: rl.Reloc(*rest) for offset, *rest in relocs},
        symbols=list(symbols),
        words=words or {},
    )


def test_a_relative_word_to_data_becomes_a_section_offset():
    patch = rl.word_patch(image([(0x4300, rl.R_X86_64_RELATIVE, 0, 0x4208)]), 0x4300)
    assert patch == rl.Patch("data", 0x300, None, ("data", 0x208))


def test_a_relative_word_to_code_becomes_the_dispatchable_file_address():
    patch = rl.word_patch(image([(0x4300, rl.R_X86_64_RELATIVE, 0, 0x1234)]), 0x4300)
    assert patch == rl.Patch("data", 0x300, 0x1234, None)


def test_a_64_word_against_a_defined_symbol_adds_the_addend():
    symbols = [rl.Sym("", 0, 0, False), rl.Sym("vt", CLASS_VTABLE, 88, True)]
    patch = rl.word_patch(image([(TYPEINFO, rl.R_X86_64_64, 1, 16)], symbols), TYPEINFO)
    assert patch == rl.Patch("data", 0x200, None, ("data", 0x110))


def test_a_64_word_against_an_undefined_symbol_resolves_through_the_linker():
    other = image(symbols=[])
    symbols = [rl.Sym("", 0, 0, False), rl.Sym("vt", 0, 0, False)]
    patch = rl.word_patch(image([(TYPEINFO, rl.R_X86_64_64, 1, 16)], symbols), TYPEINFO, {"vt": (other, 0x3010)})
    assert patch == rl.Patch("data", 0x200, None, ("rodata", 0x10 + 16))


def test_an_undefined_symbol_the_linker_does_not_know_is_rejected_by_name():
    symbols = [rl.Sym("", 0, 0, False), rl.Sym("vt", 0, 0, False)]
    with pytest.raises(rl.RelocError, match="RELOC_UNDEFINED:vt"):
        rl.word_patch(image([(TYPEINFO, rl.R_X86_64_64, 1, 0)], symbols), TYPEINFO)


@pytest.mark.parametrize("kind, name", [(6, "GLOB_DAT"), (7, "JUMP_SLOT"), (16, "DTPMOD64")])
def test_a_relocation_type_that_is_not_handled_is_rejected_by_name(kind, name):
    with pytest.raises(rl.RelocError, match=f"RELOC_TYPE:{name}"):
        rl.word_patch(image([(0x4300, kind, 0, 0x4208)]), 0x4300)


def test_a_word_with_no_relocation_is_rejected():
    with pytest.raises(rl.RelocError, match="RELOC_MISSING"):
        rl.word_patch(image(), 0x4300)


def test_a_target_outside_every_section_is_rejected():
    with pytest.raises(rl.RelocError, match="RELOC_TARGET_UNMAPPED"):
        rl.word_patch(image([(0x4300, rl.R_X86_64_RELATIVE, 0, 0x9000)]), 0x4300)


CLASS_SYMBOLS = [rl.Sym("", 0, 0, False), rl.Sym("_ZTVN10__cxxabiv117__class_type_infoE", CLASS_VTABLE, 24, True)]


def typed_lsda(entry_to_cell):
    """An LSDA whose one type entry is a pcrel, indirect sdata8 pointer to CELL."""
    body = bytes([0x01, 0x04, 0, 5, 5, 1]) + bytes([1, 0]) + struct.pack("<q", entry_to_cell)
    return bytes([0xFF, 0x9C, len(body)]) + body


def typed_image(class_relocs=None):
    entry_address = LSDA_BASE + len(typed_lsda(0)) - 8
    table = typed_lsda(CELL - entry_address)
    relocs = [
        (CELL, rl.R_X86_64_RELATIVE, 0, TYPEINFO),
        (TYPEINFO, rl.R_X86_64_64, 1, 16),
        (TYPEINFO + 8, rl.R_X86_64_RELATIVE, 0, NAME),
        (CLASS_VTABLE + 8, rl.R_X86_64_RELATIVE, 0, 0x1100),
        (CLASS_VTABLE + 16, rl.R_X86_64_RELATIVE, 0, 0x1200),
    ]
    return table, image(class_relocs or relocs, CLASS_SYMBOLS, words={CLASS_VTABLE: 0})


PROVEN = {"_ZTVN10__cxxabiv117__class_type_infoE": 2}


def test_a_class_type_info_catch_is_planned_with_every_word_it_reads():
    table, img = typed_image()
    plan = rl.plan_types(img, table, LSDA_BASE, [LSDA_BASE], PROVEN)
    assert plan.rejected == {} and plan.proven == {LSDA_BASE}
    assert plan.patches == {
        ("data", 0x300): rl.Patch("data", 0x300, None, ("data", 0x200)),
        ("data", 0x200): rl.Patch("data", 0x200, None, ("data", 0x110)),
        ("data", 0x208): rl.Patch("data", 0x208, None, ("rodata", 0x10)),
        ("data", 0x108): rl.Patch("data", 0x108, 0x1100, None),
        ("data", 0x110): rl.Patch("data", 0x110, 0x1200, None),
    }
    assert plan.slots == [rl.Slot(LSDA_BASE + len(table) - 8, ("data", 0x300))]


def test_a_typeinfo_of_an_unproven_class_rejects_the_body_as_a_typed_catch():
    table, img = typed_image()
    plan = rl.plan_types(img, table, LSDA_BASE, [LSDA_BASE], {})
    assert plan.rejected == {LSDA_BASE: "EH_TYPED_CATCH"}
    assert plan.patches == {} and plan.slots == []


def test_an_unhandled_relocation_under_a_typeinfo_rejects_the_body_by_name():
    table, img = typed_image()
    img.relocs[TYPEINFO + 8] = rl.Reloc(6, 0, 0)
    plan = rl.plan_types(img, table, LSDA_BASE, [LSDA_BASE], PROVEN)
    assert plan.rejected == {LSDA_BASE: "EH_TYPEINFO_RELOC:RELOC_TYPE:GLOB_DAT"}
    assert plan.patches == {} and plan.slots == []


def test_a_type_table_with_another_encoding_is_rejected():
    table, img = typed_image()
    table = table.replace(bytes([0x9C]), bytes([0x1C]), 1)
    plan = rl.plan_types(img, table, LSDA_BASE, [LSDA_BASE], PROVEN)
    assert plan.rejected == {LSDA_BASE: "EH_TTYPE_ENCODING"}


def test_a_catch_all_only_body_needs_no_patches():
    table = hand_lsda(1, bytes([1, 0]), struct.pack("<q", 0))
    plan = rl.plan_types(image(), table, LSDA_BASE, [LSDA_BASE], PROVEN)
    assert plan.rejected == {} and plan.proven == {LSDA_BASE} and plan.patches == {} and plan.slots == []


def test_type_entries_report_each_nonzero_filter_with_the_entry_offset():
    lsda = hand_lsda(1, bytes([1, 1]) + bytes([2, 0]), struct.pack("<ii", 0x200, 0))
    entries = eh.type_entries(lsda, 0)
    assert [e.filter for e in entries] == [2]
    assert entries[0].value == 0x200 and entries[0].offset == len(lsda) - 8


PLAN_SECTIONS = SECTIONS + [{"name": "plt", "va": 0x2000, "size": 0x100, "exec": True}]
BODIES = frozenset({0x1234, 0x1800})


def plan_of(relocs, symbols=(), sections=PLAN_SECTIONS):
    img = rl.Image(
        sections=sections,
        relocs={offset: rl.Reloc(*rest) for offset, *rest in relocs},
        symbols=list(symbols),
    )
    return rl.plan_image(img, BODIES)


def test_a_relative_word_to_a_body_start_becomes_a_function_patch():
    plan = plan_of([(0x4300, rl.R_X86_64_RELATIVE, 0, 0x1234)])
    assert plan.patches == [rl.Patch("data", 0x300, None, None, function=0x1234)]
    assert plan.rejected == {} and plan.unbound == {}


def test_a_relative_word_to_data_becomes_a_section_patch():
    plan = plan_of([(0x4300, rl.R_X86_64_RELATIVE, 0, 0x4208)])
    assert plan.patches == [rl.Patch("data", 0x300, None, ("data", 0x208))]


def test_a_relative_word_into_the_middle_of_a_body_is_rejected_by_address():
    plan = plan_of([(0x4300, rl.R_X86_64_RELATIVE, 0, 0x1235)])
    assert plan.patches == []
    assert plan.rejected == {0x4300: "RELOC_MID_BODY:1235"}


def test_a_relative_word_to_a_plt_stub_is_left_for_binding():
    plan = plan_of([(0x4300, rl.R_X86_64_RELATIVE, 0, 0x2010)])
    assert plan.plt == {0x4300: 0x2010} and plan.rejected == {}


def test_a_relative_word_to_a_ghidra_named_plt_stub_is_left_for_binding():
    sections = [s if s["name"] != "plt" else {**s, "name": "_plt"} for s in PLAN_SECTIONS]
    plan = plan_of([(0x4300, rl.R_X86_64_RELATIVE, 0, 0x2010)], sections=sections)
    assert plan.plt == {0x4300: 0x2010} and plan.rejected == {}


def test_a_64_word_against_a_defined_code_symbol_adds_the_addend_and_names_the_body():
    symbols = [rl.Sym("", 0, 0, False), rl.Sym("fn", 0x1200, 8, True)]
    plan = plan_of([(0x4300, rl.R_X86_64_64, 1, 0x34)], symbols)
    assert plan.patches == [rl.Patch("data", 0x300, None, None, function=0x1234)]


@pytest.mark.parametrize("kind", [rl.R_X86_64_64, rl.R_X86_64_GLOB_DAT, rl.R_X86_64_JUMP_SLOT])
def test_an_undefined_symbol_is_left_unbound_not_patched_or_rejected(kind):
    symbols = [rl.Sym("", 0, 0, False), rl.Sym("memcpy", 0, 0, False)]
    plan = plan_of([(0x4300, kind, 1, 0)], symbols)
    assert plan.unbound == {0x4300: "memcpy"}
    assert plan.patches == [] and plan.rejected == {}


def test_a_glob_dat_word_against_a_defined_symbol_takes_the_symbol_value():
    symbols = [rl.Sym("", 0, 0, False), rl.Sym("vt", 0x4100, 88, True)]
    plan = plan_of([(0x4300, rl.R_X86_64_GLOB_DAT, 1, 0)], symbols)
    assert plan.patches == [rl.Patch("data", 0x300, None, ("data", 0x100))]


def test_an_unhandled_relocation_type_is_rejected_by_name():
    plan = plan_of([(0x4300, 37, 0, 0)])
    assert plan.rejected == {0x4300: "RELOC_TYPE:IRELATIVE"}


def test_a_word_with_a_second_relocation_is_rejected_as_ambiguous():
    img = rl.Image(PLAN_SECTIONS, {0x4300: rl.Reloc(rl.R_X86_64_RELATIVE, 0, 0x4208)}, [], duplicates={0x4300})
    assert rl.plan_image(img, BODIES).rejected == {0x4300: "RELOC_AMBIGUOUS:4300"}


def test_a_site_outside_every_section_is_rejected():
    plan = plan_of([(0x9000, rl.R_X86_64_RELATIVE, 0, 0x4208)])
    assert plan.rejected == {0x9000: "RELOC_SITE_UNMAPPED:9000"}


def test_a_target_outside_every_section_is_rejected():
    plan = plan_of([(0x4300, rl.R_X86_64_RELATIVE, 0, 0x9000)])
    assert plan.rejected == {0x4300: "RELOC_TARGET_UNMAPPED:9000"}


def test_a_target_one_past_the_end_of_a_data_section_points_at_that_end():
    plan = plan_of([(0x4300, rl.R_X86_64_RELATIVE, 0, 0x5000)])
    assert plan.patches == [rl.Patch("data", 0x300, None, ("data", 0x1000))]


def test_a_target_one_past_the_end_of_a_code_section_is_still_rejected():
    plan = plan_of([(0x4300, rl.R_X86_64_RELATIVE, 0, 0x2000)], sections=SECTIONS)
    assert plan.rejected == {0x4300: "RELOC_TARGET_UNMAPPED:2000"}


def test_the_patches_come_out_ordered_by_section_then_offset():
    plan = plan_of([(0x4310, rl.R_X86_64_RELATIVE, 0, 0x1234), (0x4300, rl.R_X86_64_RELATIVE, 0, 0x4208)])
    assert [p.offset for p in plan.patches] == [0x300, 0x310]
