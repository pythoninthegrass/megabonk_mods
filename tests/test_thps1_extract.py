"""
Self-test for scripts/thps1_extract.py.
"""

import json
import pytest
import struct
import thps1_extract as t


def hed_entry(name: str, offset: int, size: int) -> bytes:
    raw = name.encode() + b"\0"
    raw += b"\0" * (-len(raw) % 4)
    return raw + struct.pack("<II", offset, size)


def test_parse_hed_reads_names_offsets_and_sizes() -> None:
    data = hed_entry("sprites.pre", 0, 14356) + hed_entry("skware_t.trg", 17217536, 10590) + b"\xff"

    assert t.parse_hed(data) == [
        t.Entry("sprites.pre", 0, 14356),
        t.Entry("skware_t.trg", 17217536, 10590),
    ]


def test_parse_hed_handles_names_that_fill_the_padding_exactly() -> None:
    data = hed_entry("abc", 4, 8) + hed_entry("abcdefg", 12, 16) + b"\xff"

    assert [e.name for e in t.parse_hed(data)] == ["abc", "abcdefg"]


def test_slice_entry_cuts_the_archive() -> None:
    wad = bytes(range(16))

    assert t.slice_entry(wad, t.Entry("x", 4, 3)) == bytes([4, 5, 6])


def test_slice_entry_rejects_an_entry_past_the_end() -> None:
    with pytest.raises(ValueError):
        t.slice_entry(b"\0" * 8, t.Entry("x", 4, 8))


def make_raw_sector(payload: bytes) -> bytes:
    return b"\0" * 24 + payload.ljust(2048, b"\0") + b"\0" * 280


def test_read_extent_returns_user_data_of_raw_sectors() -> None:
    raw = make_raw_sector(b"A" * 2048) + make_raw_sector(b"B" * 100)

    assert t.read_extent(raw, 0, 2148) == b"A" * 2048 + b"B" * 100


def dir_record(name: str, lba: int, size: int) -> bytes:
    ident = name.encode()
    record = bytearray(33 + len(ident))
    record[2:6] = struct.pack("<I", lba)
    record[10:14] = struct.pack("<I", size)
    record[32] = len(ident)
    record[33:] = ident
    if len(record) % 2:
        record.append(0)
    record[0] = len(record)
    return bytes(record)


def test_find_iso_file_walks_primary_volume_descriptor_and_root_directory() -> None:
    pvd = bytearray(2048)
    pvd[156 : 156 + 34] = dir_record("\0", 20, 2048)[:34].ljust(34, b"\0")
    pvd[156] = 34
    pvd[156 + 2 : 156 + 6] = struct.pack("<I", 20)
    pvd[156 + 10 : 156 + 14] = struct.pack("<I", 2048)
    directory = dir_record("SYSTEM.CNF;1", 30, 10) + dir_record("CD.WAD;1", 40, 5000)
    sectors = [make_raw_sector(b"")] * 16 + [make_raw_sector(bytes(pvd))] + [make_raw_sector(b"")] * 3
    sectors += [make_raw_sector(directory)]
    raw = b"".join(sectors)

    assert t.find_iso_file(raw, "CD.WAD") == (40, 5000)


def test_find_iso_file_raises_for_a_missing_name() -> None:
    pvd = bytearray(2048)
    pvd[156] = 34
    pvd[156 + 2 : 156 + 6] = struct.pack("<I", 20)
    pvd[156 + 10 : 156 + 14] = struct.pack("<I", 2048)
    sectors = [make_raw_sector(b"")] * 16 + [make_raw_sector(bytes(pvd))] + [make_raw_sector(b"")] * 3
    sectors += [make_raw_sector(dir_record("X;1", 30, 1))]

    with pytest.raises(FileNotFoundError):
        t.find_iso_file(b"".join(sectors), "CD.WAD")


CONVERTER_SNIPPET = """
          self.aligned_width = (self.width + alignment) & ~alignment
          self.aligned_height = (self.height + alignment) & ~alignment
"""


def test_patch_converter_keeps_the_true_texture_height() -> None:
    patched = t.patch_converter(CONVERTER_SNIPPET)

    assert "self.aligned_height = self.height\n" in patched
    assert "self.aligned_width = (self.width + alignment) & ~alignment" in patched


def test_patch_converter_fails_when_the_line_is_missing() -> None:
    with pytest.raises(ValueError):
        t.patch_converter("nothing to patch")


def test_normalise_obj_divides_uvs_by_the_current_material_size_and_flips_v() -> None:
    obj = "usemtl AAAA\nvt 64 32\nvt 0 0\nf 1/1 2/2\nusemtl BBBB\nvt 8 8\n"

    out = t.normalise_obj(obj, {"AAAA": (128, 64), "BBBB": (16, 32)})

    assert out.splitlines() == [
        "usemtl AAAA",
        "vt 0.500000 0.500000",
        "vt 0.000000 1.000000",
        "f 1/1 2/2",
        "usemtl BBBB",
        "vt 0.500000 0.750000",
    ]


def test_normalise_obj_leaves_other_lines_untouched() -> None:
    obj = "o 1234\nmtllib AAAA.mtl\nv 1 2 3\n"

    assert t.normalise_obj(obj, {}) == obj


def test_normalise_obj_rejects_uvs_without_a_known_texture() -> None:
    with pytest.raises(KeyError):
        t.normalise_obj("usemtl None\nvt 1 1\n", {})


TRG_TEXT = """\
# node 5 at 100 (assumed size: 20): type 2
skware_t.trg 0 PowrUp:      05 ['0.828857 -0.103760 2.661621', '0x0000:0x0001', '0xFFFF', '0xFFFF'] # SPickup

# node 6 at 120 (assumed size: 20): type 2
skware_t.trg 6 PowrUp: 0000 16 ['2.237793 -0.250732 2.296875', '0x0000:0x0001', '0xFFFF', '0xFFFF'] # TapePickup

# node 7 at 140 (assumed size: 20): type 2
skware_t.trg 2 PowrUp: 0000 21 ['1.893311 -0.255371 1.632080', '0x0000:0x0001', '0xFFFF', '0xFFFF'] # BonusPickup100

# node 8 at 160 (assumed size: 20): type 2
skware_t.trg 2 PowrUp: 0000 23 ['1.594238 -0.385986 0.915771', '0x0000:0x0001', '0xFFFF', '0xFFFF'] # BonusPickup500

# node 43 at 2550 (assumed size: 74): type 1
 43: skware_t.trg 0 Baddy: ['0x00CB', '0x1000'] 6
Script-garbage: 0000 ['0x0200', '0xFF04', 2.023193359375, -0.381103515625, 0.924072265625, '0x0C00', '0x0000', '0x0000'] # []
1   2584 C_READ_LABELS()
1   2622 C_GOALCOUNTER(0)
1   2624 C_DONE()

# node 44 at 2624 (assumed size: 74): type 1
 44: skware_t.trg 0 Baddy: ['0x00CB', '0x1000'] 6
Script-garbage: 0000 ['0x0200', '0xFF05', 0.766, -0.0197, 2.6665, '0x0C00', '0x0000', '0x0000'] # []
1   2700 C_DONE()

# node 177 at 7692 (assumed size: 8): type 2
Crate 0x0000      0xBB7DC2A2
"""


def test_parse_trg_nodes_reads_letters_tape_and_bonus_pickups() -> None:
    nodes = t.parse_trg_nodes(TRG_TEXT)

    assert nodes[0] == {"node": 5, "type": "letter", "name": "S", "position": [0.828857, -0.10376, 2.661621]}
    assert nodes[1] == {"node": 6, "type": "tape", "name": "tape", "position": [2.237793, -0.250732, 2.296875]}
    assert nodes[2]["type"] == "bonus" and nodes[2]["name"] == "100"
    assert nodes[3]["type"] == "bonus" and nodes[3]["name"] == "500"


def test_parse_trg_nodes_treats_goal_counter_baddies_as_box_piles() -> None:
    piles = [n for n in t.parse_trg_nodes(TRG_TEXT) if n["type"] == "box_pile"]

    assert piles == [{"node": 43, "type": "box_pile", "name": "pile", "position": [2.023193, -0.381104, 0.924072]}]


def test_parse_trg_nodes_ignores_baddies_without_a_goal_counter_and_crates() -> None:
    nodes = t.parse_trg_nodes(TRG_TEXT)

    assert {n["node"] for n in nodes} == {5, 6, 7, 8, 43}


def test_nodes_json_is_serialisable_with_the_unit_note() -> None:
    doc = t.nodes_document(t.parse_trg_nodes(TRG_TEXT))

    assert json.loads(json.dumps(doc))["nodes"][0]["name"] == "S"
    assert "unit" in doc


def test_use_single_material_library_replaces_per_face_mtllib_lines() -> None:
    obj = "o 1\nmtllib AAAA.mtl\nusemtl AAAA\nf 1 2 3\nmtllib None\nusemtl None\n"

    assert t.use_single_material_library(obj, "warehouse.mtl").splitlines() == [
        "mtllib warehouse.mtl",
        "o 1",
        "usemtl AAAA",
        "f 1 2 3",
        "usemtl None",
    ]


def test_build_mtl_maps_each_hash_to_its_png_without_a_scale_option() -> None:
    mtl = t.build_mtl(["BBBB", "AAAA"])

    assert mtl == "newmtl AAAA\nmap_Kd AAAA-0.png\n\nnewmtl BBBB\nmap_Kd BBBB-0.png\n"
