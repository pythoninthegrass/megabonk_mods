"""Tests for the exception-handling census over the shipped Linux GameAssembly.so.

The census walks .eh_frame to get every function body and its LSDA pointer, then reads the
call-site table of each LSDA in .gcc_except_table. Both parsers are pure functions over
bytes, so the fixtures here are hand-built rather than taken from the binary.
"""

import eh_probe as ep
import pytest
import struct

EH_BASE = 0x4000
TABLE_BASE = 0x9000
OMIT = 0xFF
ULEB128 = 0x01
UDATA4 = 0x03
PCREL_SDATA4 = 0x1B
INDIRECT_PCREL_SDATA4 = 0x9B


class Builder:
    """Appends the fixed-width fields of a hand-built .eh_frame entry or LSDA."""

    def __init__(self) -> None:
        self.bytes = bytearray()

    @property
    def pos(self) -> int:
        return len(self.bytes)

    def u8(self, value: int) -> "Builder":
        self.bytes.append(value)
        return self

    def u32(self, value: int) -> "Builder":
        self.bytes += struct.pack("<I", value)
        return self

    def s32(self, value: int) -> "Builder":
        self.bytes += struct.pack("<i", value)
        return self

    def uleb(self, value: int) -> "Builder":
        while True:
            byte = value & 0x7F
            value >>= 7
            self.bytes.append(byte | (0x80 if value else 0))
            if not value:
                return self

    def raw(self, data: bytes) -> "Builder":
        self.bytes += data
        return self


def cie(augmentation: str, lsda_encoding: int | None, pointer_encoding: int,
        personality: int = 0x11223344, personality_encoding: int = INDIRECT_PCREL_SDATA4) -> bytes:
    """A version 1 CIE whose augmentation data follows the order of the augmentation string."""
    body = Builder().u8(1).raw(augmentation.encode() + b"\0").uleb(1).u8(0x78).u8(16)
    aug = bytearray()
    if "P" in augmentation:
        aug += bytes([personality_encoding]) + struct.pack("<i", personality)
    if "L" in augmentation:
        aug += bytes([lsda_encoding])
    if "R" in augmentation:
        aug += bytes([pointer_encoding])
    body.uleb(len(aug)).raw(bytes(aug)).raw(b"\0" * 4)
    return struct.pack("<I", len(body.bytes) + 4) + struct.pack("<I", 0) + bytes(body.bytes)


def fde(cie_at: int, entry_at: int, pc_range: int, lsda: int | None,
        lsda_encoding: int = UDATA4) -> bytes:
    """An FDE with a pcrel code pointer of zero delta and, if any, one LSDA pointer field."""
    body = Builder().u32(entry_at + 4 - cie_at).s32(0).u32(pc_range)
    if lsda is None:
        body.uleb(0)
    elif lsda_encoding == UDATA4:
        body.uleb(4).u32(lsda)
    else:
        body.uleb(4).s32(lsda)
    body.raw(b"\0" * ((8 - body.pos % 8) % 8))
    return struct.pack("<I", len(body.bytes)) + bytes(body.bytes)


def entry_bytes(fields: int, start: int, length: int, pad: int, action: int) -> bytes:
    """One call-site entry: three range fields in the table's encoding, then a ULEB action."""
    out = Builder()
    for value in (start, length, pad):
        out.uleb(value) if fields == ULEB128 else out.u32(value)
    return (out.uleb(action)).bytes


def call_site_table(entries: list[tuple[int, int, int]], *, ttype: int = OMIT, ttype_offset: int = 0x40,
                    lpstart: int = OMIT, action: int = 0, fields: int = ULEB128,
                    terminated: bool = False) -> bytes:
    """A complete LSDA as libgcc writes it: two encodings and a TType offset, then the call-site
    encoding and length, then entries that each carry an action field and a final zero entry."""
    header = Builder().u8(lpstart)
    if lpstart != OMIT:
        header.u32(0)
    header.u8(ttype)
    if ttype != OMIT:
        header.uleb(ttype_offset)
    header.u8(fields)
    body = bytearray()
    for start, length, pad in entries:
        body += entry_bytes(fields, start, length, pad, action)
    if terminated:
        body += entry_bytes(fields, 0, 0, 0, 0)
    return header.bytes + uleb_bytes(len(body)) + bytes(body)


def uleb_bytes(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def lsda_at(table: Builder, at: int, entries: list[tuple[int, int, int]], **kw) -> int:
    """Pads a table up to an offset, appends an LSDA there and returns its virtual address."""
    while table.pos < at:
        table.u8(0)
    table.raw(call_site_table(entries, **kw))
    return TABLE_BASE + at


TABLE = Builder()
LSDA_ONE_PAD = lsda_at(TABLE, 0, [(4, 4, 0x20), (10, 4, 0)])
LSDA_THREE_PADS = lsda_at(TABLE, 0x20, [(1, 4, 0x30), (8, 4, 0x34), (20, 4, 0x40)], ttype=0x02)
LSDA_FIVE_PADS = lsda_at(TABLE, 0x40, [(i, 4, pad) for i, pad in
                                       zip((2, 9, 16, 23, 30), (0x50, 0x58, 0x60, 0x68, 0x70))],
                         lpstart=UDATA4)
LSDA_WIDE_FIELDS = lsda_at(TABLE, 0x80, [(4, 4, 0x60), (12, 4, 0x64)], fields=UDATA4)
LSDA_REPEAT_PAD = lsda_at(TABLE, 0xC0, [(2, 4, 0x70), (9, 4, 0x70), (16, 4, 0x70)])
LSDA_BYTES = bytes(TABLE.bytes)

CIE_R = cie("zR", None, PCREL_SDATA4)
CIE_PLR = cie("zPLR", UDATA4, PCREL_SDATA4)
CIE_PLR_AT = len(CIE_R)
FDE_NO_LSDA_AT = len(CIE_R) + len(CIE_PLR)
FDE_NO_LSDA = fde(0, FDE_NO_LSDA_AT, 0x10, None)
FDE_WITH_LSDA_AT = FDE_NO_LSDA_AT + len(FDE_NO_LSDA)
FDE_WITH_LSDA = fde(CIE_PLR_AT, FDE_WITH_LSDA_AT, 0x40, LSDA_ONE_PAD)
FDE_ZERO_LSDA_AT = FDE_WITH_LSDA_AT + len(FDE_WITH_LSDA)
FDE_ZERO_LSDA = fde(CIE_PLR_AT, FDE_ZERO_LSDA_AT, 0x400, 0)
FRAMES = CIE_R + CIE_PLR + FDE_NO_LSDA + FDE_WITH_LSDA + FDE_ZERO_LSDA
# length, CIE pointer, version, "zPLR" + NUL, both factors, return-address register, aug length, P encoding
PERSONALITY_PLACE = CIE_PLR_AT + 4 + 4 + 1 + 5 + 1 + 1 + 1 + 1 + 1


def test_read_uleb128_reads_single_and_multi_byte_values():
    data = bytes([0x05, 0x82, 0x01, 0xFF, 0xFF, 0x03])
    assert ep.read_uleb128(data, 0) == (5, 1)
    assert ep.read_uleb128(data, 1) == (130, 3)
    assert ep.read_uleb128(data, 3) == (0xFFFF, 6)


def test_read_sleb128_reads_negative_values():
    assert ep.read_sleb128(bytes([0x78]), 0) == (-8, 1)
    assert ep.read_sleb128(bytes([0x00]), 0) == (0, 1)
    assert ep.read_sleb128(bytes([0xC0, 0x7F]), 0) == (-64, 2)


def test_read_uleb128_rejects_a_truncated_value():
    with pytest.raises(ep.EhError):
        ep.read_uleb128(bytes([0x82]), 0)
    with pytest.raises(ep.EhError):
        ep.read_uleb128(b"", 0)


def test_read_encoded_pointer_absolute_forms():
    data = struct.pack("<I", 0x1234) + struct.pack("<Q", 0x1122334455667788)
    assert ep.read_encoded_pointer(data, 0, UDATA4) == (0x1234, 4)
    assert ep.read_encoded_pointer(data, 4, 0x04) == (0x1122334455667788, 12)
    assert ep.read_encoded_pointer(bytes([0x82, 0x01]), 0, ULEB128) == (130, 2)


def test_read_encoded_pointer_pcrel_is_relative_to_its_own_place():
    data = b"\0\0\0\0" + struct.pack("<i", -8)
    assert ep.read_encoded_pointer(data, 4, PCREL_SDATA4) == (4 - 8, 8)
    assert ep.read_encoded_pointer(data, 4, PCREL_SDATA4, base=0x1000) == (0xFF8, 8)


def test_read_encoded_pointer_refuses_to_resolve_an_indirect_pointer():
    with pytest.raises(ep.EhError):
        ep.read_encoded_pointer(struct.pack("<i", 0x40), 0, INDIRECT_PCREL_SDATA4)


def test_read_encoded_pointer_reports_the_slot_of_an_indirect_pointer_when_asked():
    data = struct.pack("<i", 0x40)
    got = ep.read_encoded_pointer(data, 0, INDIRECT_PCREL_SDATA4, base=0x1000, resolve=False)
    assert got == (0x1040, 4)


def test_read_encoded_pointer_rejects_omit():
    with pytest.raises(ep.EhError):
        ep.read_encoded_pointer(b"", 0, OMIT)


def test_read_encoded_pointer_needs_a_base_for_section_relative_forms():
    with pytest.raises(ep.EhError):
        ep.read_encoded_pointer(struct.pack("<I", 0x40), 0, 0x33)  # datarel udata4
    assert ep.read_encoded_pointer(struct.pack("<I", 0x40), 0, 0x33, base=0x8000) == (0x8040, 4)


def test_pointer_size_sizes_each_encoding():
    assert ep.pointer_size(UDATA4) == 4
    assert ep.pointer_size(0x04) == 8
    assert ep.pointer_size(PCREL_SDATA4) == 4
    assert ep.pointer_size(0x00) == 8
    assert ep.pointer_size(ULEB128) is None
    assert ep.pointer_size(OMIT) is None
    with pytest.raises(ep.EhError):
        ep.pointer_size(0x06)


def test_cie_offset_of_undoes_the_backward_cie_pointer():
    assert ep.cie_offset_of(0x18, 0x1C) == 0
    assert ep.cie_offset_of(0x100, 0x104 - 0x40) == 0x40


def test_parse_cies_reads_augmentation_and_encodings():
    cies = ep.parse_cies(FRAMES, EH_BASE)
    assert cies[0].augmentation == "zR"
    assert cies[0].lsda_encoding is None
    assert cies[0].pointer_encoding == PCREL_SDATA4
    assert cies[0].personality_slot is None
    plr = cies[CIE_PLR_AT]
    assert plr.augmentation == "zPLR"
    assert plr.lsda_encoding == UDATA4
    assert plr.pointer_encoding == PCREL_SDATA4
    assert plr.personality_slot == EH_BASE + PERSONALITY_PLACE + 0x11223344


def test_parse_cies_rejects_an_unknown_augmentation_character():
    with pytest.raises(ep.EhError):
        ep.parse_cies(cie("zRLR", UDATA4, PCREL_SDATA4))


def test_parse_cies_rejects_a_dwarf64_entry():
    with pytest.raises(ep.EhError):
        ep.parse_cies(struct.pack("<I", 0xFFFFFFFF) + bytes(16))


def test_parse_frames_reads_pc_and_lsda():
    frames = ep.parse_frames(FRAMES, EH_BASE)
    assert len(frames) == 3
    assert frames[0] == ep.Frame(EH_BASE + FDE_NO_LSDA_AT + 8, 0x10, None, "zR", 0)
    assert frames[1] == ep.Frame(EH_BASE + FDE_WITH_LSDA_AT + 8, 0x40, LSDA_ONE_PAD, "zPLR",
                                 CIE_PLR_AT)
    assert frames[2].lsda is None


def test_parse_frames_resolves_a_pcrel_lsda_against_its_own_field():
    plr = cie("zPLR", PCREL_SDATA4, PCREL_SDATA4)
    entry_at = len(plr)
    entry = fde(0, entry_at, 0x20, 0x100, lsda_encoding=PCREL_SDATA4)
    frames = ep.parse_frames(plr + entry, EH_BASE)
    lsda_field_at = entry_at + 4 + 4 + 4 + 4 + 1  # length, CIE pointer, pc, range, aug length
    assert frames[0].lsda == EH_BASE + lsda_field_at + 0x100


def test_parse_frames_reads_the_range_as_a_fixed_width_field():
    """The FDE range is the code pointer's own width, not the ULEB128 .debug_frame uses."""
    wide = fde(0, len(CIE_R), 0x100, None)
    frames = ep.parse_frames(CIE_R + wide, EH_BASE)
    assert [f.pc_range for f in frames] == [0x100]


def test_parse_frames_rejects_a_cie_without_an_r_augmentation():
    no_r = cie("zL", UDATA4, PCREL_SDATA4)
    with pytest.raises(ep.EhError):
        ep.parse_frames(no_r + fde(0, len(no_r), 0x10, None), EH_BASE)


def test_parse_frames_rejects_an_fde_naming_an_absent_cie():
    broken = CIE_R + CIE_PLR + FDE_NO_LSDA[:4] + struct.pack("<I", 0xFFFFFFF0) + FDE_NO_LSDA[8:]
    with pytest.raises(ep.EhError):
        ep.parse_frames(broken, EH_BASE)


def test_parse_lsda_counts_call_sites_and_landing_pads():
    got = ep.parse_lsda(LSDA_BYTES, LSDA_ONE_PAD - TABLE_BASE)
    assert (got.call_sites, got.landing_pads, got.has_ttype) == (2, 1, False)


def test_parse_lsda_reads_the_ttype_encoding_that_follows_the_lpstart():
    got = ep.parse_lsda(LSDA_BYTES, LSDA_THREE_PADS - TABLE_BASE)
    assert (got.call_sites, got.landing_pads, got.has_ttype) == (3, 3, True)


def test_parse_lsda_skips_the_lpstart_value_when_its_encoding_is_not_omit():
    got = ep.parse_lsda(LSDA_BYTES, LSDA_FIVE_PADS - TABLE_BASE)
    assert (got.call_sites, got.landing_pads) == (5, 5)


def test_parse_lsda_reads_fixed_width_call_site_fields():
    got = ep.parse_lsda(LSDA_BYTES, LSDA_WIDE_FIELDS - TABLE_BASE)
    assert (got.call_sites, got.landing_pads) == (2, 2)


def test_parse_lsda_counts_entries_by_the_tables_own_length():
    """The length in the header bounds the table, so trailing bytes are never entries."""
    padded = call_site_table([(4, 4, 0x20)]) + bytes([0x04, 0x04, 0x20, 0x00])
    got = ep.parse_lsda(padded, 0)
    assert (got.call_sites, got.landing_pads, got.distinct_pads) == (1, 1, 1)


def test_parse_lsda_stops_at_a_zero_entry_when_the_producer_wrote_one():
    terminated = call_site_table([(4, 4, 0x20), (10, 4, 0x24)], terminated=True)
    got = ep.parse_lsda(terminated, 0)
    assert (got.call_sites, got.landing_pads, got.distinct_pads) == (2, 2, 2)


def test_parse_lsda_counts_a_repeated_landing_pad_once():
    """The emitter needs one block per distinct pad, so two entries into one pad count once."""
    got = ep.parse_lsda(LSDA_BYTES, LSDA_REPEAT_PAD - TABLE_BASE)
    assert (got.call_sites, got.landing_pads, got.distinct_pads) == (3, 3, 1)


def test_parse_lsda_rejects_a_table_whose_length_runs_past_the_end():
    truncated = call_site_table([(4, 4, 0x20)])[:-2]
    with pytest.raises(ep.EhError):
        ep.parse_lsda(truncated, 0)


def test_parse_lsda_rejects_a_last_entry_running_past_its_length():
    """Entries pack four fields each: a table that ends mid-entry is a parse failure."""
    body = call_site_table([(4, 4, 0x20)])
    broken = body[:-1] + bytes([0x80, 0x00])  # a two-byte action field, one past the length
    with pytest.raises(ep.EhError):
        ep.parse_lsda(broken, 0)


def test_parse_lsda_rejects_a_call_site_encoding_that_is_not_a_number():
    table = bytes([OMIT, OMIT, OMIT, 0x91, 0x00])
    with pytest.raises(ep.EhError):
        ep.parse_lsda(table, 0)


def test_pad_buckets_name_the_ranges_the_report_uses():
    assert ep.pad_bucket(0) == "none"
    assert ep.pad_bucket(1) == "one"
    assert ep.pad_bucket(4) == "two-four"
    assert ep.pad_bucket(5) == "five-plus"
    assert ep.pad_bucket(600) == "five-plus"


def test_bodies_keeps_only_frames_starting_in_the_section():
    frames = [ep.Frame(0x100, 0x10, None, "zR", 0), ep.Frame(0x200, 0x10, 0x9000, "zPLR", 0),
              ep.Frame(0x300, 0, None, "zR", 0)]
    assert ep.bodies(frames, 0x200, 0x300) == [ep.Body(0x200, 0x10, 0x9000, "zPLR")]


def test_measure_breaks_lsda_presence_down_by_size_class():
    bodies = [
        ep.Body(0x100, 10, LSDA_ONE_PAD, "zPLR"),
        ep.Body(0x200, 100, LSDA_THREE_PADS, "zPLR"),
        ep.Body(0x300, 1000, LSDA_FIVE_PADS, "zPLR"),
        ep.Body(0x400, 10, None, "zR"),
        ep.Body(0x500, 100, 0, "zPLR"),
    ]
    got = ep.measure(bodies, LSDA_BYTES, TABLE_BASE)
    assert got["bodies"] == 5
    assert got["by_class"]["tiny"] == {"bodies": 2, "with_lsda": 1, "with_pads": 1}
    assert got["by_class"]["small"] == {"bodies": 2, "with_lsda": 1, "with_pads": 1}
    assert got["by_class"]["large"] == {"bodies": 1, "with_lsda": 1, "with_pads": 1}
    assert got["pad_distribution"] == {"none": 0, "one": 1, "two-four": 1, "five-plus": 1}
    assert got["call_sites"] == 10
    assert got["landing_pads"] == 9
    assert got["distinct_pads"] == 9
    assert got["max_pads"] == 5


def test_measure_flags_an_lsda_pointer_outside_the_except_table():
    got = ep.measure([ep.Body(0x100, 10, TABLE_BASE + len(LSDA_BYTES) + 8, "zPLR")],
                     LSDA_BYTES, TABLE_BASE)
    assert got["lsda_outside_table"] == 1
    assert got["with_lsda"] == 1
    assert got["pad_distribution"] == {"none": 0, "one": 0, "two-four": 0, "five-plus": 0}


def test_measure_counts_a_shared_lsda_once():
    """Two bodies can be described by one table, so tables and bodies are counted apart."""
    got = ep.measure([ep.Body(0x100, 10, LSDA_ONE_PAD, "zPLR"),
                      ep.Body(0x200, 20, LSDA_ONE_PAD, "zPLR")], LSDA_BYTES, TABLE_BASE)
    assert (got["with_lsda"], got["distinct_lsdas"]) == (2, 1)


def test_measure_counts_frames_per_cie_augmentation():
    bodies = [ep.Body(0x100, 10, LSDA_ONE_PAD, "zPLR"), ep.Body(0x200, 10, None, "zR")]
    got = ep.measure(bodies, LSDA_BYTES, TABLE_BASE)
    assert got["by_augmentation"] == {"zR": 1, "zPLR": 1}


def test_measure_over_the_hand_built_tables():
    frames = ep.parse_frames(FRAMES, EH_BASE)
    got = ep.measure(ep.bodies(frames, EH_BASE, EH_BASE + len(FRAMES)), LSDA_BYTES, TABLE_BASE)
    assert got["bodies"] == 3
    assert got["by_class"] == {
        "tiny": {"bodies": 1, "with_lsda": 0, "with_pads": 0},
        "small": {"bodies": 1, "with_lsda": 1, "with_pads": 1},
        "large": {"bodies": 1, "with_lsda": 0, "with_pads": 0},
    }
    assert got["call_sites"] == 2
    assert got["landing_pads"] == 1
    assert got["distinct_pads"] == 1
    assert got["by_augmentation"] == {"zR": 1, "zPLR": 2}
