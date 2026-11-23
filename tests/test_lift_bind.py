"""Section protection, the binding of imported words, the completeness gate and the audit report of a relocated image."""

import elf_shim_probe as elf
import json
import lift_bind as bind
import lift_reloc as rl
import pytest
import struct
from types import SimpleNamespace

SECTIONS = [
    {"name": "rodata", "va": 0x1000, "size": 0x100, "exec": False},
    {"name": "text", "va": 0x2000, "size": 0x100, "exec": True},
    {"name": "plt", "va": 0x3000, "size": 0x40, "exec": True},
    {"name": "relro", "va": 0x4000, "size": 0x100, "exec": False},
    {"name": "data", "va": 0x4800, "size": 0x100, "exec": False},
    {"name": "bss", "va": 0x4900, "size": 0x100, "exec": False},
]
SEGMENTS = [
    elf.Segment(rl.PT_LOAD, 4, 0, 0x1000, 0x100, 0x100, 0x1000),
    elf.Segment(rl.PT_LOAD, 5, 0, 0x2000, 0x1040, 0x1040, 0x1000),
    elf.Segment(rl.PT_LOAD, 6, 0, 0x4000, 0x900, 0x1000, 0x1000),
    elf.Segment(rl.PT_GNU_RELRO, 4, 0, 0x4000, 0x100, 0x100, 1),
]
BODIES = frozenset({0x2000, 0x2010})
STUBS = {0x3010: "malloc", 0x3020: "malloc", 0x3030: "stderr_hook"}


def sym(name, value=0, defined=False, weak=False, data=False):
    return rl.Sym(name, value, 0, defined, weak, data)


def plan_for(relocs, symbols=()):
    image = rl.Image(SECTIONS, {a: rl.Reloc(*r) for a, r in relocs.items()}, list(symbols))
    return image, rl.plan_image(image, BODIES)


def test_a_section_takes_the_protection_of_the_segment_that_loads_it():
    result = rl.protection(SEGMENTS, SECTIONS)
    assert result["rodata"] == "ro" and result["text"] == "rx" and result["data"] == "rw"


def test_a_section_inside_the_relro_range_is_read_only_after_relocation():
    assert rl.protection(SEGMENTS, SECTIONS)["relro"] == "relro"


def test_memory_past_the_file_bytes_of_a_writable_segment_stays_writable():
    assert rl.protection(SEGMENTS, SECTIONS)["bss"] == "rw"


def test_a_section_inside_the_tls_segment_is_a_thread_template_not_loaded_memory():
    segments = [*SEGMENTS, elf.Segment(rl.PT_TLS, 4, 0, 0x7000, 0, 0x10, 8)]
    template = [{"name": "tbss", "va": 0x7000, "size": 0x10, "exec": False}]
    assert rl.protection(segments, template) == {"tbss": "tls"}


def test_ghidras_external_block_is_marked_external_not_refused_as_unmapped():
    block = [{"name": "EXTERNAL", "va": 0x9000, "size": 0x10, "exec": False}]
    assert rl.protection(SEGMENTS, block) == {"EXTERNAL": "external"}


def test_a_section_no_loaded_segment_covers_is_refused():
    stray = [*SECTIONS, {"name": "stray", "va": 0x9000, "size": 0x10, "exec": False}]
    with pytest.raises(rl.RelocError, match="SECTION_UNMAPPED:stray"):
        rl.protection(SEGMENTS, stray)


def test_a_section_that_straddles_the_end_of_the_relro_range_is_refused():
    split = [{"name": "split", "va": 0x4080, "size": 0x100, "exec": False}]
    with pytest.raises(rl.RelocError, match="SECTION_SPLIT_BY_RELRO:split"):
        rl.protection(SEGMENTS, split)


def test_a_section_that_runs_past_its_segment_is_refused():
    long = [{"name": "long", "va": 0x4F80, "size": 0x100, "exec": False}]
    with pytest.raises(rl.RelocError, match="SECTION_UNMAPPED:long"):
        rl.protection(SEGMENTS, long)


def test_the_image_plan_carries_the_protection_of_its_image():
    image = rl.Image(SECTIONS, {}, [], protection={"rodata": "ro"})
    assert rl.plan_image(image, BODIES).protection == {"rodata": "ro"}


def test_a_word_naming_a_plt_entry_is_recorded_for_binding_not_rejected():
    _, plan = plan_for({0x4800: (rl.R_X86_64_RELATIVE, 0, 0x3000)})
    assert plan.plt == {0x4800: 0x3000} and plan.rejected == {}


def test_the_tls_module_id_word_is_a_literal_one_for_the_single_module():
    _, plan = plan_for({0x4808: (rl.R_X86_64_DTPMOD64, 0, 0)})
    assert plan.patches == [rl.Patch("data", 8, None, None, literal=1)] and plan.rejected == {}


def test_a_tls_offset_relocation_is_still_rejected_by_name():
    _, plan = plan_for({0x4808: (rl.R_X86_64_DTPOFF64, 0, 0)})
    assert plan.rejected == {0x4808: "RELOC_TYPE:DTPOFF64"}


def test_a_complete_plan_passes_the_gate():
    rl.require_complete(plan_for({0x4800: (rl.R_X86_64_RELATIVE, 0, 0x2000)})[1])


@pytest.mark.parametrize("field", ["rejected", "unbound", "plt"])
def test_a_plan_with_an_unaccounted_word_fails_the_gate(field):
    plan = rl.ImagePlan()
    getattr(plan, field)[0x4800] = "x" if field != "plt" else 0x3000
    with pytest.raises(rl.RelocError, match=f"{field.upper()}:1"):
        rl.require_complete(plan)


def test_the_gate_names_the_first_sites_it_refuses():
    plan = rl.ImagePlan(rejected={0x4800: "RELOC_AMBIGUOUS:4800", 0x4808: "RELOC_TARGET_UNMAPPED:9"})
    with pytest.raises(rl.RelocError, match="4800.*RELOC_AMBIGUOUS"):
        rl.require_complete(plan)


def test_a_function_import_word_points_at_the_lowest_stub_of_that_name():
    image, plan = plan_for({0x4800: (rl.R_X86_64_64, 0, 0)}, [sym("malloc")])
    result = bind.bind_words(plan, image, STUBS)
    assert plan.patches == [rl.Patch("data", 0, None, None, function=0x3010)]
    assert plan.unbound == {} and result.rows[0]["binding"] == "stub"


def test_a_data_import_word_points_at_a_named_host_variable():
    image, plan = plan_for({0x4800: (rl.R_X86_64_GLOB_DAT, 0, 0)}, [sym("stderr", data=True)])
    result = bind.bind_words(plan, image, {})
    assert plan.patches == [rl.Patch("data", 0, None, None, host="lift_data_stderr")]
    assert "lift_data_stderr" in result.source and "stderr" in result.source
    assert result.rows[0]["binding"] == "host data"


def test_the_host_source_defines_only_the_data_the_image_imports():
    image, plan = plan_for({0x4800: (rl.R_X86_64_GLOB_DAT, 0, 0)}, [sym("stderr", data=True)])
    assert "environ" not in bind.bind_words(plan, image, {}).source


def test_a_weak_import_nothing_defines_resolves_to_null():
    image, plan = plan_for({0x4800: (rl.R_X86_64_GLOB_DAT, 0, 0)}, [sym("__gmon_start__", weak=True)])
    result = bind.bind_words(plan, image, {})
    assert plan.patches == [rl.Patch("data", 0, None, None, literal=0)] and result.rows[0]["binding"] == "weak null"


@pytest.mark.parametrize("kind", [rl.R_X86_64_GLOB_DAT, rl.R_X86_64_JUMP_SLOT])
def test_unprovided_weak_profiling_hook_is_null_even_with_a_plt_stub(kind):
    image, plan = plan_for({0x4800: (kind, 0, 0)}, [sym("__gmon_start__", weak=True)])
    result = bind.bind_words(plan, image, {0x1100: "__gmon_start__"})
    assert plan.patches == [rl.Patch("data", 0, None, None, literal=0)]
    assert result.rows[0]["binding"] == "weak null"


def test_a_weak_import_with_a_stub_binds_to_the_stub_not_to_null():
    image, plan = plan_for({0x4800: (rl.R_X86_64_GLOB_DAT, 0, 0)}, [sym("malloc", weak=True)])
    bind.bind_words(plan, image, STUBS)
    assert plan.patches[0].function == 0x3010


def test_a_strong_data_import_nothing_defines_is_rejected_by_name():
    image, plan = plan_for({0x4800: (rl.R_X86_64_64, 0, 0)}, [sym("mystery", data=True)])
    bind.bind_words(plan, image, STUBS)
    assert plan.rejected == {0x4800: "RELOC_UNBOUND:mystery"} and plan.patches == []


def test_a_strong_function_import_with_no_stub_gets_a_named_abort_entry():
    image, plan = plan_for({0x4800: (rl.R_X86_64_64, 0, 0)}, [sym("mystery")])
    result = bind.bind_words(plan, image, STUBS)
    assert plan.patches == [rl.Patch("data", 0, None, None, host="lift_import_mystery")] and plan.rejected == {}
    assert result.rows[0]["binding"] == "named abort"
    assert "void lift_import_mystery(unsigned char *reg)" in result.source and "mystery" in result.source


def test_the_plt_resolver_word_gets_a_named_abort_entry():
    image, plan = plan_for({0x4800: (rl.R_X86_64_RELATIVE, 0, 0x3000)})
    result = bind.bind_words(plan, image, STUBS)
    assert plan.patches == [rl.Patch("data", 0, None, None, function=0x3000)]
    assert result.aborts == [
        {"address": 0x3000, "name": "plt_resolver", "disposition": "abort", "reason": bind.PLT_RESOLVER, "host": None}
    ]


def test_a_word_naming_a_stub_entry_points_at_that_stub():
    image, plan = plan_for({0x4800: (rl.R_X86_64_RELATIVE, 0, 0x3010)})
    result = bind.bind_words(plan, image, STUBS)
    assert plan.patches[0].function == 0x3010 and result.aborts == []


def test_a_word_naming_the_middle_of_the_plt_is_rejected():
    image, plan = plan_for({0x4800: (rl.R_X86_64_RELATIVE, 0, 0x3018)})
    bind.bind_words(plan, image, STUBS)
    assert plan.rejected == {0x4800: "RELOC_PLT_TARGET:3018"}


def test_every_patched_word_has_a_mapping_row_with_its_original_kind_and_target():
    relocs = {
        0x4800: (rl.R_X86_64_RELATIVE, 0, 0x2000),
        0x4808: (rl.R_X86_64_RELATIVE, 0, 0x4810),
        0x4810: (rl.R_X86_64_64, 0, 0),
    }
    image, plan = plan_for(relocs, [sym("malloc")])
    bind.bind_words(plan, image, STUBS)
    rows = {r["site"]: r for r in bind.mapping(image, plan)}
    assert rows[0x4800] == {"site": 0x4800, "kind": "RELATIVE", "target": {"function": 0x2000}}
    assert rows[0x4808]["target"] == {"section": "data", "offset": 0x10}
    assert rows[0x4810] == {"site": 0x4810, "kind": "64", "symbol": "malloc", "target": {"function": 0x3010}}


def test_the_report_accounts_for_every_relocation_by_kind_and_target():
    relocs = {0x4800: (rl.R_X86_64_RELATIVE, 0, 0x2000), 0x4810: (rl.R_X86_64_64, 0, 0), 0x4818: (rl.R_X86_64_DTPMOD64, 0, 0)}
    image, plan = plan_for(relocs, [sym("malloc")])
    bind.bind_words(plan, image, STUBS)
    report = bind.report(image, plan, {"data": bytes(0x100)})
    assert report["relocations"] == {"total": 3, "patched": 3, "kinds": {"64": 1, "DTPMOD64": 1, "RELATIVE": 1}}
    assert json.dumps(report)


def test_the_report_fails_when_a_relocation_is_not_in_the_plan():
    image, plan = plan_for({0x4800: (rl.R_X86_64_RELATIVE, 0, 0x2000)})
    image.relocs[0x4808] = rl.Reloc(rl.R_X86_64_RELATIVE, 0, 0x2000)
    with pytest.raises(rl.RelocError, match="UNACCOUNTED:1"):
        bind.report(image, plan, {})


def test_the_report_lists_each_section_with_its_protection_and_whether_it_is_zero_filled():
    image = rl.Image(SECTIONS, {}, [], protection=rl.protection(SEGMENTS, SECTIONS))
    plan = rl.plan_image(image, BODIES)
    rows = {r["name"]: r for r in bind.report(image, plan, {"bss": bytes(0x100), "data": b"\1" * 0x100})["sections"]}
    assert rows["bss"]["zero_filled"] is True and rows["data"]["zero_filled"] is False
    assert rows["relro"]["protection"] == "relro" and rows["data"]["protection"] == "rw"
    assert len(rows["data"]["sha256"]) == 64 and "sha256" not in rows["text"]
    assert rows["data"]["defined"] is True and rows["text"]["defined"] is False


def dynsym_elf(entries):
    raw = b"".join(struct.pack("<IBBHQQ", 0, 0, 0, shndx, value, 0) for _, _, _, shndx, value in entries)
    named = [SimpleNamespace(name=n, bind=b, type=t) for n, b, t, _, _ in entries]
    return SimpleNamespace(relocs=[], sections=[SimpleNamespace(name=".dynsym", offset=0)], dynsyms=named), raw


def test_a_loaded_symbol_records_whether_it_is_weak_and_whether_it_is_data():
    fake, raw = dynsym_elf([("stderr", 1, 1, 0, 0), ("__gmon_start__", 2, 0, 0, 0), ("f", 1, 2, 7, 0x2000)])
    image = rl.load_image(fake, raw, SECTIONS)
    stderr, gmon, f = image.symbols
    assert (stderr.weak, stderr.data, stderr.defined) == (False, True, False)
    assert (gmon.weak, gmon.data) == (True, False) and f.defined and f.value == 0x2000
