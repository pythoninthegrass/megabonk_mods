"""Tests for the base-relative relocation census.

The driver reads the shipped Linux GameAssembly.so, takes every R_X86_64_RELATIVE it
carries, and classifies what each one points at: a function entry, the inside of a
function, read-only data, writable data, bss, other loaded memory, or nothing loaded at
all. Function bounds come from .eh_frame, the same records the lift probe cuts bodies
from, so an entry is a real body start rather than a guess from a byte pattern.

These tests build the ELF records by hand, the way tests/test_elf_shim_probe.py does, so
every bucket is reachable at a known address.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import eh_probe as ep
import elf_shim_probe as esp
import reloc_probe as rp

SHIPPED_SO = esp.REPO / ".tools/megabonk-linux-native/Megabonk/GameAssembly.so"
requires_shipped_so = pytest.mark.skipif(
    not SHIPPED_SO.exists(), reason=f"shipped Linux runtime absent at {SHIPPED_SO}"
)

RO, RW, RX, RWX = rp.SHF_ALLOC, rp.SHF_ALLOC | rp.SHF_WRITE, rp.SHF_ALLOC | rp.SHF_EXECINSTR, (
    rp.SHF_ALLOC | rp.SHF_WRITE | rp.SHF_EXECINSTR)

TEXT_BASE = 0x1400
BODY_ONE = rp.Body(0x1400, 0x1440)
BODY_TWO = rp.Body(0x1500, 0x1580)


def section(name, type_, flags, addr, size):
    return esp.Section(name, type_, flags, addr, addr, size, 0, 0)


def segment(flags, vaddr, filesz, memsz=None):
    return esp.Segment(esp.PT_LOAD, flags, vaddr, vaddr, filesz, filesz if memsz is None else memsz, 0x1000)


def rela(offset, addend, type_=8):
    return esp.Rela(offset, type_, 0, addend, ".rela.dyn")


def frame(start, size):
    return ep.Frame(start, size, None, "zR", 0)


LOADS = (segment(rp.PF_R, 0x1000, 0x1000), segment(rp.PF_R | rp.PF_W, 0x2000, 0x1000))

SECTIONS = (
    section(".rodata", rp.SHT_PROGBITS, RO, 0x1000, 0x400),
    section(".text", rp.SHT_PROGBITS, RX, TEXT_BASE, 0x400),
    section(".data", rp.SHT_PROGBITS, RW, 0x2000, 0x200),
    section(".data.rel.ro", rp.SHT_PROGBITS, RW, 0x2200, 0x100),
    section(".got", rp.SHT_PROGBITS, RW, 0x2300, 0x40),
    section(".bss", rp.SHT_NOBITS, RW, 0x2400, 0x200),
)


def address_map(bodies=(BODY_TWO, BODY_ONE), sections=SECTIONS, loads=LOADS):
    return rp.AddressMap(sections, loads, tuple(sorted(bodies, key=lambda b: b.start)))


def test_an_exact_body_start_is_a_function_entry():
    assert address_map().bucket(0x1400) == "function_entry"
    assert address_map().bucket(0x1500) == "function_entry"


def test_an_address_inside_a_body_is_a_function_interior():
    assert address_map().bucket(0x1420) == "function_interior"
    assert address_map().bucket(0x157f) == "function_interior"


def test_a_body_end_is_not_inside_the_body_it_ends():
    """The end is exclusive: the byte past a function is someone else's code."""
    assert address_map().bucket(0x1440) == "other_loaded"


def test_code_no_frame_covers_is_other_loaded_memory():
    """Ghidra and the unwinder see different things, so a gap in the frames is its own case."""
    assert address_map().bucket(0x1600) == "other_loaded"
    assert address_map().bucket(0x1800) == "other_loaded"


def test_a_read_only_section_is_read_only_data():
    assert address_map().bucket(0x1010) == "read_only_data"


def test_writable_sections_are_writable_data():
    amap = address_map()
    assert amap.bucket(0x2010) == "writable_data"
    assert amap.bucket(0x2210) == "writable_data"
    assert amap.bucket(0x2310) == "writable_data"


def test_a_no_bits_section_is_bss():
    assert address_map().bucket(0x2410) == "bss"


def test_memory_in_a_segment_with_no_section_is_other_loaded():
    assert address_map().bucket(0x2f00) == "other_loaded"


def test_an_address_in_no_segment_is_outside():
    assert address_map().bucket(0x9000) == "outside"
    assert address_map().bucket(0) == "outside"


def test_writable_wins_over_executable_for_a_shared_section():
    """A W+X section holds data the program writes, which is the case that matters here."""
    amap = address_map(sections=(section(".shm", rp.SHT_PROGBITS, RWX, 0x3000, 0x100),),
                       loads=(segment(rp.PF_R | rp.PF_W, 0x3000, 0x100),), bodies=())
    assert amap.bucket(0x3010) == "writable_data"


def test_the_smallest_containing_section_decides():
    """Sections can overlap, so a wrapper cannot swallow the section it wraps."""
    wide = section(".whole", rp.SHT_PROGBITS, rp.SHF_WRITE, 0x1000, 0x1000)
    amap = address_map(sections=(wide,) + SECTIONS)
    assert amap.bucket(0x1010) == "read_only_data"


def test_a_section_outside_every_segment_still_classifies():
    """A section header can describe memory no PT_LOAD covers; the address is still not loaded."""
    stray = section(".stray", rp.SHT_PROGBITS, RO, 0x9000, 0x100)
    assert address_map(sections=SECTIONS + (stray,)).bucket(0x9010) == "read_only_data"


def test_bodies_sorts_and_drops_empty_frames():
    got = rp.bodies([frame(0x1500, 0x80), frame(0x1400, 0x40), frame(0x2000, 0)])
    assert got == (rp.Body(0x1400, 0x1440), rp.Body(0x1500, 0x1580))


def test_bodies_folds_records_that_share_a_start_onto_their_widest_range():
    """Two FDEs for one function must not read as two overlapping functions."""
    assert rp.bodies([frame(0x10, 0x20), frame(0x10, 0x40)]) == (rp.Body(0x10, 0x50),)


def test_bodies_keeps_a_nested_record_as_an_overlap():
    got = rp.bodies([frame(0x10, 0x40), frame(0x20, 0x10)])
    assert got == (rp.Body(0x10, 0x50), rp.Body(0x20, 0x30))


def test_classify_pairs_each_relocation_with_its_slot_and_bucket():
    amap = address_map()
    got = rp.classify([rela(0x2010, 0x1400), rela(0x2310, 0x2410)], amap)
    assert [(t.slot, t.slot_section, t.address, t.bucket) for t in got] == [
        (0x2010, ".data", 0x1400, "function_entry"),
        (0x2310, ".got", 0x2410, "bss"),
    ]


def test_classify_names_an_unknown_slot_section_as_none():
    got = rp.classify([rela(0x2f00, 0x1010)], address_map())
    assert [(t.slot_section, t.bucket) for t in got] == [(None, "read_only_data")]


def build_elf(relocs):
    return esp.Elf(Path("fixture.so"), esp.ET_DYN, esp.EM_X86_64, 0, list(SECTIONS),
                   list(LOADS), {}, {}, [], relocs, {}, "fixture.so")


def test_measure_counts_every_relative_relocation_once_per_bucket():
    relocs = [rela(0x2010, 0x1400), rela(0x2018, 0x1520), rela(0x2020, 0x1010),
              rela(0x2028, 0x2410), rela(0x2030, 0x1600), rela(0x2038, 0x2f00),
              rela(0x2040, 0x9000)]
    report = rp.measure(build_elf(relocs), rp.bodies([frame(0x1400, 0x40), frame(0x1500, 0x80)]))
    assert report["relative_relocs"] == 7
    assert report["buckets"] == {
        "function_entry": 1, "function_interior": 1, "read_only_data": 1,
        "writable_data": 0, "bss": 1, "other_loaded": 2, "outside": 1,
    }
    assert sum(report["buckets"].values()) == report["relative_relocs"]


def test_measure_counts_only_relative_relocations():
    relocs = [rela(0x2010, 0x1400), rela(0x2018, 0x1400, type_=1), rela(0x2020, 0x1400, type_=7)]
    report = rp.measure(build_elf(relocs), rp.bodies(()))
    assert report["relative_relocs"] == 1
    assert report["relocations_excluded"] == 2


def test_measure_breaks_the_relocations_down_by_the_slot_section():
    relocs = [rela(0x2010, 0x1400), rela(0x2018, 0x1400), rela(0x2210, 0x1500),
              rela(0x2310, 0x1010)]
    report = rp.measure(build_elf(relocs), rp.bodies([frame(0x1400, 0x40), frame(0x1500, 0x80)]))
    assert report["by_slot_section"] == {".data": 2, ".data.rel.ro": 1, ".got": 1}


def test_measure_splits_other_loaded_between_code_without_a_frame_and_unsectioned():
    relocs = [rela(0x2010, 0x1600), rela(0x2018, 0x1700), rela(0x2020, 0x2f00)]
    report = rp.measure(build_elf(relocs), rp.bodies([frame(0x1400, 0x40)]))
    assert report["buckets"]["other_loaded"] == 3
    assert report["other_loaded_detail"] == {"executable_no_frame": 2, "unsectioned": 1}


def test_measure_reports_a_total_that_disagrees_with_the_documented_figure():
    report = rp.measure(build_elf([rela(0x2010, 0x1400)]), rp.bodies(()))
    assert report["documented_relative"] == rp.DOCUMENTED_RELATIVE
    assert report["checks"]["total_matches_documented"] is False


def test_measure_checks_hold_over_a_fixture_covering_every_bucket():
    relocs = [rela(0x2010 + 8 * i, target) for i, target in
              enumerate((0x1400, 0x1520, 0x1010, 0x2010, 0x2410, 0x1600, 0x2f00, 0x9000))]
    report = rp.measure(build_elf(relocs), rp.bodies([frame(0x1400, 0x40), frame(0x1500, 0x80)]))
    assert report["checks"]["every_relocation_classified"] is True
    assert report["checks"]["entry_targets_are_body_starts"] is True
    assert report["checks"]["interior_targets_are_not_body_starts"] is True
    assert report["checks"]["slots_all_in_known_sections"] is True


def test_measure_flags_buckets_that_do_not_account_for_every_relocation(monkeypatch):
    """The invariant is the sum, not the classifier's good mood: a lost row has to show."""
    monkeypatch.setattr(rp.AddressMap, "bucket", lambda self, addr: "bogus")
    report = rp.measure(build_elf([rela(0x2010, 0x1400)]), rp.bodies(()))
    assert report["checks"]["every_relocation_classified"] is False


def test_measure_flags_a_code_slot_no_section_describes():
    report = rp.measure(build_elf([rela(0x2f00, 0x1400)]), rp.bodies([frame(0x1400, 0x40)]))
    assert report["checks"]["slots_all_in_known_sections"] is False
    assert report["slots_without_section"] == 1


def test_measure_counts_overlapping_bodies_rather_than_hiding_them():
    bodies = (rp.Body(0x100, 0x200), rp.Body(0x180, 0x300))
    report = rp.measure(build_elf([rela(0x2010, 0x190)]), bodies)
    assert report["overlapping_bodies"] == 1
    assert report["buckets"]["function_interior"] == 1


def test_measure_counts_distinct_targets():
    relocs = [rela(0x2010, 0x1400), rela(0x2018, 0x1400), rela(0x2020, 0x1500)]
    report = rp.measure(build_elf(relocs), rp.bodies([frame(0x1400, 0x40), frame(0x1500, 0x80)]))
    assert report["distinct_targets"] == 2


def test_render_reports_the_total_and_every_bucket():
    relocs = [rela(0x2010, 0x1400), rela(0x2018, 0x9000)]
    text = rp.render(rp.measure(build_elf(relocs), rp.bodies([frame(0x1400, 0x40)])))
    assert "466320" in text
    for bucket in rp.BUCKETS:
        assert bucket in text


@requires_shipped_so
def test_the_shipped_relative_total_matches_the_documented_figure():
    report = rp.run_probe(SHIPPED_SO)
    assert report["relative_relocs"] == rp.DOCUMENTED_RELATIVE == 466_320
    assert sum(report["buckets"].values()) == report["relative_relocs"]
    assert all(report["checks"].values())


@requires_shipped_so
def test_the_shipped_census_finds_pointers_into_every_kind_of_memory():
    """The claim being made is that the split is mixed, so each bucket has to be populated."""
    report = rp.run_probe(SHIPPED_SO)
    assert report["buckets"]["function_entry"] > 0
    assert report["buckets"]["function_interior"] >= 0
    assert report["buckets"]["read_only_data"] > 0
    assert report["buckets"]["writable_data"] > 0
    assert report["buckets"]["bss"] >= 0
    assert set(report["by_slot_section"]) >= {".data.rel.ro", ".data", ".got"}


@requires_shipped_so
def test_the_shipped_entry_targets_open_with_instruction_bytes():
    """An independent check on the entry bucket: an entry on zero padding would mean the
    frame table is being read wrong, and unexplained first bytes have to stay a rounding
    error rather than most of the bucket."""
    report = rp.run_probe(SHIPPED_SO)
    shapes = report["entry_prologue_shapes"]
    entries = report["buckets"]["function_entry"]
    assert shapes["targets"] == entries
    assert shapes["zero_padding_targets"] == 0
    assert sum(shapes["unexplained_first_bytes"].values()) < entries * 0.05


@requires_shipped_so
def test_an_address_inside_a_shipped_body_is_an_interior():
    """The census reports no interior targets at all, which is a finding about the binary
    rather than the classifier, so containment has to be shown live on real bodies."""
    elf, raw, mapping, _ = rp.load(SHIPPED_SO)
    body = next(b for b in mapping.bodies if b.end - b.start > 64)
    assert mapping.bucket(body.start) == "function_entry"
    assert mapping.bucket(body.start + 32) == "function_interior"
    assert mapping.bucket(body.end - 1) == "function_interior"


@requires_shipped_so
def test_the_shipped_bodies_agree_with_the_exception_census_within_il2cpp():
    """Both probes bound functions from the same .eh_frame records, so the counts the
    exception census documents have to fall out of this one when it is scoped the same way."""
    report = rp.run_probe(SHIPPED_SO)
    elf, _, mapping, _ = rp.load(SHIPPED_SO)
    section = next(s for s in elf.sections if s.name == "il2cpp")
    bodies = mapping.bodies
    inside = sum(1 for b in bodies if section.addr <= b.start < section.addr + section.size)
    assert inside == 196_137
    assert report["bodies"] == len(bodies) == 259_095
    assert report["frame_records"] == 259_101
