#!/usr/bin/env python3
"""
Extract the THPS1 Warehouse (mesh, textures, collectible nodes) from a PS1 disc image you own.

Geometry, texture decoding and TRG disassembly use JayFoxRox/thps2-tools (MIT); this script
reads the disc, applies the THPS1 texture-height fix to a copy of its converter, and
post-processes the output. Input and output stay under gitignored directories.
"""

import argparse
import hashlib
import json
import math
import mmap
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

RAW_SECTOR = 2352
RAW_HEADER = 24
USER_DATA = 2048
PVD_LBA = 16
ROOT_RECORD_OFFSET = 156
DISC_SHA256 = (Path(__file__).resolve().parents[1] / "tools/thps1.sha256").read_text().split()[0]

WAREHOUSE_FILES = ["skware.psx", "skware_l.psx", "skware_t.trg"]
MESH_FILE = "skware.psx"
TEXTURE_FILE = "skware_l.psx"
TRG_FILE = "skware_t.trg"

ALIGNED_HEIGHT_LINE = "self.aligned_height = (self.height + alignment) & ~alignment"
TRUE_HEIGHT_LINE = "self.aligned_height = self.height"

LETTER_PICKUPS = {"SPickup": "S", "KPickup": "K", "APickup": "A", "TPickup": "T", "EPickup": "E"}
BONUS_PICKUP = re.compile(r"BonusPickup(\d+)$")

NODE_HEADER = re.compile(r"^# node (\d+) at", re.MULTILINE)
POWRUP_LINE = re.compile(r"PowrUp:.*\['(-?[\d.]+) (-?[\d.]+) (-?[\d.]+)'.*# (\w+)\s*$", re.MULTILINE)
BADDY_POSITION = re.compile(r"Script-garbage:.*?'0xFF\w\w', (-?[\d.]+), (-?[\d.]+), (-?[\d.]+),")

UNIT_NOTE = "THPS model units as written by convert-psx.py; y negative is up; metres per unit is in docs/thps-warehouse.md"


class Entry(NamedTuple):
    name: str
    offset: int
    size: int


def parse_hed(data: bytes) -> list[Entry]:
    """Parse CD.HED: NUL-terminated name padded to 4 bytes, then u32 offset and u32 size, ended by 0xFF."""
    entries = []
    pos = 0
    while pos < len(data) and data[pos] != 0xFF:
        end = data.index(b"\0", pos)
        name = data[pos:end].decode()
        field = (end + 1 + 3) & ~3
        offset, size = struct.unpack_from("<II", data, field)
        entries.append(Entry(name, offset, size))
        pos = field + 8
    return entries


def slice_entry(wad: bytes, entry: Entry) -> bytes:
    if entry.offset + entry.size > len(wad):
        raise ValueError(f"{entry.name} runs past the end of the archive")
    return wad[entry.offset : entry.offset + entry.size]


def read_extent(raw: bytes, lba: int, size: int) -> bytes:
    """Read size bytes starting at a logical block of a raw MODE2/2352 image."""
    sectors = math.ceil(size / USER_DATA)
    chunks = []
    for index in range(sectors):
        start = (lba + index) * RAW_SECTOR + RAW_HEADER
        chunks.append(raw[start : start + USER_DATA])
    return b"".join(chunks)[:size]


def find_iso_file(raw: bytes, name: str) -> tuple[int, int]:
    """Return (lba, size) of a file in the ISO9660 root directory of a raw image."""
    pvd = read_extent(raw, PVD_LBA, USER_DATA)
    root = pvd[ROOT_RECORD_OFFSET : ROOT_RECORD_OFFSET + 34]
    (root_lba,) = struct.unpack_from("<I", root, 2)
    (root_size,) = struct.unpack_from("<I", root, 10)
    directory = read_extent(raw, root_lba, root_size)
    pos = 0
    while pos < len(directory):
        length = directory[pos]
        if length == 0:
            pos = (pos // USER_DATA + 1) * USER_DATA
            continue
        record = directory[pos : pos + length]
        ident = record[33 : 33 + record[32]].decode(errors="replace").split(";")[0]
        if ident == name:
            (lba,) = struct.unpack_from("<I", record, 2)
            (size,) = struct.unpack_from("<I", record, 10)
            return lba, size
        pos += length
    raise FileNotFoundError(name)


def patch_converter(source: str) -> str:
    """THPS1 textures align only the width, so the converter must not round the height up."""
    if source.count(ALIGNED_HEIGHT_LINE) != 1:
        raise ValueError("convert-psx.py does not contain the expected aligned_height line")
    return source.replace(ALIGNED_HEIGHT_LINE, TRUE_HEIGHT_LINE)


def normalise_obj(obj: str, texture_sizes: dict[str, tuple[int, int]]) -> str:
    """Turn the converter's pixel UVs into 0..1 UVs with v pointing up, per current material."""
    material = None
    lines = []
    for line in obj.splitlines(keepends=True):
        parts = line.split()
        if parts and parts[0] == "usemtl":
            material = parts[1]
        elif parts and parts[0] == "vt":
            width, height = texture_sizes[material]
            u, v = float(parts[1]), float(parts[2])
            line = f"vt {u / width:.6f} {1 - v / height:.6f}\n"
        lines.append(line)
    return "".join(lines)


def use_single_material_library(obj: str, library: str) -> str:
    kept = [line for line in obj.splitlines() if not line.startswith("mtllib ")]
    return "\n".join([f"mtllib {library}", *kept]) + "\n"


def build_mtl(hashes: list[str]) -> str:
    return "\n".join(f"newmtl {h}\nmap_Kd {h}-0.png\n" for h in sorted(hashes))


def parse_trg_nodes(text: str) -> list[dict]:
    """Collect pickups and the goal-counting Baddy nodes (the five box piles) from trg.txt."""
    headers = list(NODE_HEADER.finditer(text))
    nodes = []
    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        block = text[header.start() : end]
        number = int(header.group(1))
        powrup = POWRUP_LINE.search(block)
        if powrup:
            position = [round(float(powrup.group(k)), 6) for k in (1, 2, 3)]
            nodes.append({"node": number, **classify_pickup(powrup.group(4)), "position": position})
        elif "Baddy:" in block and "C_GOALCOUNTER" in block:
            found = BADDY_POSITION.search(block)
            position = [round(float(found.group(k)), 6) for k in (1, 2, 3)]
            nodes.append({"node": number, "type": "box_pile", "name": "pile", "position": position})
    return nodes


def classify_pickup(comment: str) -> dict:
    if comment in LETTER_PICKUPS:
        return {"type": "letter", "name": LETTER_PICKUPS[comment]}
    if comment == "TapePickup":
        return {"type": "tape", "name": "tape"}
    bonus = BONUS_PICKUP.match(comment)
    if bonus:
        return {"type": "bonus", "name": bonus.group(1)}
    return {"type": "pickup", "name": comment}


def nodes_document(nodes: list[dict]) -> dict:
    return {"unit": UNIT_NOTE, "nodes": nodes}


def texture_sizes(texture_dir: Path) -> dict[str, tuple[int, int]]:
    from PIL import Image

    sizes = {}
    for png in texture_dir.glob("*-0.png"):
        with Image.open(png) as image:
            sizes[png.name.removesuffix("-0.png")] = image.size
    return sizes


def run_tool(script: Path, args: list[str], cwd: Path, stdout: Path) -> None:
    cwd.mkdir(parents=True, exist_ok=True)
    (cwd / "out").mkdir(exist_ok=True)
    with stdout.open("w") as log:
        subprocess.run([sys.executable, str(script), *args], cwd=cwd, stdout=log, check=True)


def extract_sources(disc: Path, source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    with disc.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        hed_lba, hed_size = find_iso_file(raw, "CD.HED")
        wad_lba, wad_size = find_iso_file(raw, "CD.WAD")
        entries = {e.name: e for e in parse_hed(read_extent(raw, hed_lba, hed_size))}
        wad = read_extent(raw, wad_lba, wad_size)
    for name in WAREHOUSE_FILES:
        (source_dir / name).write_bytes(slice_entry(wad, entries[name]))


def verify_disc(disc: Path) -> None:
    with disc.open("rb") as handle:
        actual = hashlib.file_digest(handle, "sha256").hexdigest()
    if actual != DISC_SHA256:
        raise ValueError(f"disc SHA-256 mismatch: expected {DISC_SHA256}, got {actual}; use the supported USA MODE2/2352 image")


def build(disc: Path, converter_dir: Path, out: Path) -> None:
    disc, converter_dir, out = disc.resolve(), converter_dir.resolve(), out.resolve()
    verify_disc(disc)
    source = out / "source"
    tools = out / "converter"
    textures = out / "textures"
    mesh = out / "mesh"
    warehouse = out / "warehouse"
    extract_sources(disc, source)

    tools.mkdir(parents=True, exist_ok=True)
    shutil.copy(converter_dir / "common.py", tools / "common.py")
    shutil.copy(converter_dir / "disassemble-trg.py", tools / "disassemble-trg.py")
    patched = tools / "convert-psx-thps1.py"
    patched.write_text(patch_converter((converter_dir / "convert-psx.py").read_text()))

    run_tool(patched, [str(source / TEXTURE_FILE)], textures, textures / "convert.log")
    run_tool(patched, [str(source / MESH_FILE)], mesh, mesh / "convert.log")
    run_tool(tools / "disassemble-trg.py", [str(source / TRG_FILE)], out / "trg", out / "trg.txt")

    warehouse.mkdir(parents=True, exist_ok=True)
    sizes = texture_sizes(textures / "out")
    for png in (textures / "out").glob("*-0.png"):
        shutil.copy(png, warehouse / png.name)
    obj = (mesh / "out" / "world.obj").read_text()
    used = {line.split()[1] for line in obj.splitlines() if line.startswith("usemtl ") and line.split()[1] != "None"}
    (warehouse / "warehouse.mtl").write_text(build_mtl(sorted(used)))
    obj = use_single_material_library(normalise_obj(obj, sizes), "warehouse.mtl")
    (warehouse / "warehouse.obj").write_text(obj)

    nodes = parse_trg_nodes((out / "trg.txt").read_text())
    (warehouse / "warehouse_nodes.json").write_text(json.dumps(nodes_document(nodes), indent=2) + "\n")
    print(f"wrote {warehouse} ({len(nodes)} nodes, {len(used)} materials)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disc", type=Path, required=True, help="raw MODE2/2352 .bin of the USA disc")
    parser.add_argument("--converter-dir", type=Path, help="checkout of JayFoxRox/thps2-tools")
    parser.add_argument("--verify-only", action="store_true", help="verify the pinned disc checksum without extracting")
    parser.add_argument("--out", type=Path, default=Path(".tools/thps1"))
    args = parser.parse_args()
    if args.verify_only:
        verify_disc(args.disc)
        print("disc SHA-256 verified")
        return
    if args.converter_dir is None:
        parser.error("--converter-dir is required unless --verify-only is used")
    build(args.disc, args.converter_dir, args.out)


if __name__ == "__main__":
    main()
