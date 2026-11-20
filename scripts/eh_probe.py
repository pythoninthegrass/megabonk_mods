#!/usr/bin/env -S uv run --script
"""Count how much of the shipped il2cpp section uses C++ exception handling.

Walks .eh_frame to bound every function body and take its LSDA pointer, then reads each
LSDA's call-site table in .gcc_except_table to count landing pads. The emitter lifts none of
it, so this is the size of what that costs. It reads bytes only: nothing is loaded or run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import elf_shim_probe  # noqa: E402  stdlib ELF reader, reused for section bytes
import lift_probe  # noqa: E402  size classes shared with the liftability probe

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SO = REPO / ".tools/megabonk-linux-native/Megabonk/GameAssembly.so"
DEFAULT_OUT = REPO / ".tools/eh-probe"

DW_EH_PE_omit = 0xFF
DW_EH_PE_uleb128 = 0x01
DW_EH_PE_sleb128 = 0x09
DW_EH_PE_indirect = 0x80
DW_EH_PE_pcrel = 0x10
DW_EH_PE_textrel = 0x20
DW_EH_PE_datarel = 0x30
DW_EH_PE_funcrel = 0x40
FIXED_FORMS = {0x02: 2, 0x03: 4, 0x04: 8, 0x0A: 2, 0x0B: 4, 0x0C: 8}
PAD_BUCKETS = ("none", "one", "two-four", "five-plus")
SIZE_CLASSES = ("tiny", "small", "large")


class EhError(RuntimeError):
    """The bytes are not the .eh_frame or .gcc_except_table format the census expects."""


def read_uleb128(data: bytes, at: int) -> tuple[int, int]:
    """Reads an unsigned LEB128 value, returning it and the next offset."""
    value = shift = 0
    while True:
        if at >= len(data):
            raise EhError("a LEB128 value runs past the end of the table")
        byte = data[at]
        at += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, at
        shift += 7
        if shift > 70:
            raise EhError("a LEB128 value is too wide")


def read_sleb128(data: bytes, at: int) -> tuple[int, int]:
    """Reads a signed LEB128 value, returning it and the next offset."""
    value = shift = 0
    while True:
        if at >= len(data):
            raise EhError("a LEB128 value runs past the end of the table")
        byte = data[at]
        at += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            if byte & 0x40:
                value -= 1 << shift
            return value, at


def pointer_size(encoding: int, address_size: int = 8) -> int | None:
    """Bytes an encoded pointer occupies, or None when its form is a varint or absent."""
    if encoding == DW_EH_PE_omit:
        return None
    form = encoding & 0x0F
    if form in (DW_EH_PE_uleb128, DW_EH_PE_sleb128):
        return None
    if form == 0x00:
        return address_size
    try:
        return FIXED_FORMS[form]
    except KeyError:
        raise EhError(f"unknown pointer encoding {encoding:#04x}") from None


def read_encoded_pointer(
    data: bytes, at: int, encoding: int, *, base: int | None = None, address_size: int = 8, resolve: bool = True
) -> tuple[int, int]:
    """Decodes an encoded pointer at `at`; `base` replaces the address it is relative to.

    An indirect encoding names a slot holding the pointer. Without a loaded image that slot
    cannot be read, so `resolve` refuses it for a code or LSDA pointer and accepts it where
    the slot's own address is the answer.
    """
    if encoding == DW_EH_PE_omit:
        raise EhError("DW_EH_PE_omit carries no value to read")
    indirect = bool(encoding & DW_EH_PE_indirect)
    if indirect and resolve:
        raise EhError("an indirect pointer needs the image loaded, which the census does not do")
    place = at
    form = encoding & 0x0F
    if form == DW_EH_PE_uleb128:
        value, at = read_uleb128(data, at)
    elif form == DW_EH_PE_sleb128:
        value, at = read_sleb128(data, at)
    else:
        size = pointer_size(encoding, address_size)
        if at + size > len(data):
            raise EhError("an encoded pointer runs past the end of the table")
        fmt = {2: "<h", 4: "<i", 8: "<q"}[size] if form & 0x08 else {2: "<H", 4: "<I", 8: "<Q"}[size]
        value = struct.unpack_from(fmt, data, at)[0]
        at += size
    application = encoding & 0x70
    if application == DW_EH_PE_pcrel:
        value += place if base is None else base
    elif application == 0x00:
        pass
    elif application in (DW_EH_PE_textrel, DW_EH_PE_datarel, DW_EH_PE_funcrel):
        if base is None:
            raise EhError(f"pointer encoding {encoding:#04x} needs a base the census does not have")
        value += base
    else:
        raise EhError(f"unknown pointer application {application:#04x}")
    return value, at


@dataclass(frozen=True)
class Cie:
    offset: int
    version: int
    augmentation: str
    lsda_encoding: int | None
    pointer_encoding: int | None
    personality_slot: int | None


@dataclass(frozen=True)
class Frame:
    pc_begin: int
    pc_range: int
    lsda: int | None
    augmentation: str
    cie_offset: int


@dataclass(frozen=True)
class Body:
    start: int
    size: int
    lsda: int | None
    augmentation: str


@dataclass(frozen=True)
class Lsda:
    call_sites: int
    landing_pads: int
    distinct_pads: int
    has_ttype: bool


def _entries(eh_frame: bytes):
    """Yields each .eh_frame entry as its section offset and body bytes."""
    at = 0
    while at < len(eh_frame):
        if at + 4 > len(eh_frame):
            raise EhError(".eh_frame ends inside an entry length")
        (length,) = struct.unpack_from("<I", eh_frame, at)
        if length == 0:
            return
        if length == 0xFFFFFFFF:
            raise EhError("DWARF64 .eh_frame is not supported")
        if length < 8:
            raise EhError(f"an .eh_frame entry of {length} bytes cannot hold its header")
        body = at + 4
        if body + length > len(eh_frame):
            raise EhError("an .eh_frame entry runs past the end of the section")
        yield at, eh_frame[body : body + length]
        at = body + length


def _cstr(data: bytes, at: int) -> tuple[str, int]:
    try:
        end = data.index(0, at)
    except ValueError:
        raise EhError("a CIE augmentation string runs past the end") from None
    return data[at:end].decode("ascii", "replace"), end + 1


def _parse_cie(offset: int, body: bytes, base: int, address_size: int) -> Cie:
    """Reads a CIE header: the augmentation string and the encodings its augmentation data names."""
    pos = 4
    version = body[pos]
    pos += 1
    augmentation, pos = _cstr(body, pos)
    if version not in (1, 2, 3):
        raise EhError(f"unhandled .eh_frame CIE version {version}")
    _, pos = read_uleb128(body, pos)  # code alignment factor: no CFA instructions are read
    _, pos = read_sleb128(body, pos)  # data alignment factor
    pos += 1  # return address register, a one-byte register number in .eh_frame
    if not augmentation.startswith("z"):
        return Cie(offset, version, augmentation, None, None, None)
    aug_len, pos = read_uleb128(body, pos)
    if pos + aug_len > len(body):
        raise EhError("a CIE augmentation data length runs past the end")
    aug = body[pos : pos + aug_len]
    cursor = 0
    lsda_encoding = None
    pointer_encoding = None
    personality_slot = None
    for char in augmentation[1:]:
        if cursor >= len(aug):
            raise EhError(f"augmentation '{augmentation}' names {char} with no data left")
        if char == "P":
            encoding = aug[cursor]
            cursor += 1
            personality_slot, cursor = read_encoded_pointer(
                aug, cursor, encoding, base=base + offset + 4 + pos + cursor, address_size=address_size, resolve=False
            )
        elif char == "L":
            lsda_encoding = aug[cursor]
            cursor += 1
        elif char == "R":
            pointer_encoding = aug[cursor]
            cursor += 1
        else:
            raise EhError(f"unhandled CIE augmentation character '{char}'")
    return Cie(offset, version, augmentation, lsda_encoding, pointer_encoding, personality_slot)


def parse_cies(eh_frame: bytes, base: int = 0, address_size: int = 8) -> dict[int, Cie]:
    """Every CIE in the section, keyed by the offset an FDE's backward pointer resolves to."""
    cies = {
        offset: _parse_cie(offset, body, base, address_size)
        for offset, body in _entries(eh_frame)
        if struct.unpack_from("<I", body, 0)[0] == 0
    }
    if not cies:
        raise EhError(".eh_frame holds no CIE")
    return cies


def cie_offset_of(entry: int, field: int) -> int:
    """Resolves an FDE's CIE pointer, which .eh_frame stores as its own address minus the CIE's."""
    return entry + 4 - field


def parse_frames(eh_frame: bytes, base: int = 0, address_size: int = 8) -> list[Frame]:
    """Every FDE in the section: its code range and the LSDA pointer its CIE's layout says it has."""
    cies = parse_cies(eh_frame, base, address_size)
    frames = []
    for entry, body in _entries(eh_frame):
        field = struct.unpack_from("<I", body, 0)[0]
        if field == 0:
            continue
        cie = cies.get(cie_offset_of(entry, field))
        if cie is None:
            raise EhError(f"an FDE at {entry:#x} names absent CIE {field:#x}")
        if cie.pointer_encoding is None:
            raise EhError(f"CIE {cie.offset:#x} carries no R augmentation, so its pointer width is unknown")
        pos = 4
        pc_begin, pos = read_encoded_pointer(
            body, pos, cie.pointer_encoding, base=base + entry + 4 + pos, address_size=address_size
        )
        # The range is the code pointer's own fixed-width form without its application bits:
        # .eh_frame does not use the ULEB128 range of .debug_frame.
        pc_range, pos = read_encoded_pointer(body, pos, cie.pointer_encoding & 0x0F, address_size=address_size)
        lsda = None
        if cie.augmentation.startswith("z"):
            aug_len, pos = read_uleb128(body, pos)
            if cie.lsda_encoding not in (None, DW_EH_PE_omit) and aug_len:
                lsda, _ = read_encoded_pointer(
                    body, pos, cie.lsda_encoding, base=base + entry + 4 + pos, address_size=address_size
                )
                if lsda == 0:
                    lsda = None
        frames.append(Frame(pc_begin, pc_range, lsda, cie.augmentation, cie.offset))
    return frames


def bodies(frames: list[Frame], lo: int, hi: int) -> list[Body]:
    """The function bodies of one section: FDEs whose first instruction lies in [lo, hi)."""
    return [Body(f.pc_begin, f.pc_range, f.lsda, f.augmentation) for f in frames if lo <= f.pc_begin < hi and f.pc_range > 0]


def read_call_site_field(data: bytes, at: int, encoding: int) -> tuple[int, int]:
    """One call-site field: the compact numeric forms only, since these are offsets, not addresses."""
    if encoding == DW_EH_PE_omit:
        raise EhError("a call-site table needs a field encoding")
    if encoding & 0xF0:
        raise EhError(f"call-site fields cannot use pointer application {encoding & 0xF0:#04x}")
    return read_encoded_pointer(data, at, encoding)


def _byte(data: bytes, at: int) -> tuple[int, int]:
    if at >= len(data):
        raise EhError("an LSDA header runs past the end of .gcc_except_table")
    return data[at], at + 1


def parse_lsda(table: bytes, at: int) -> Lsda:
    """Counts the call-site entries and landing pads of the LSDA at `at` in a .gcc_except_table.

    The header is the one libgcc's `parse_lsda_header` reads: an LPStart encoding with a value
    when it is not omitted, a TType encoding with a ULEB offset past the table, then the
    call-site encoding and the table's byte length. Every entry carries an action field.
    """
    pos = at
    lpstart_encoding, pos = _byte(table, pos)
    if lpstart_encoding != DW_EH_PE_omit:
        _, pos = read_encoded_pointer(table, pos, lpstart_encoding)
    ttype_encoding, pos = _byte(table, pos)
    if ttype_encoding != DW_EH_PE_omit:
        _, pos = read_uleb128(table, pos)  # TType offset: it names a place after the table
    site_encoding, pos = _byte(table, pos)
    table_len, pos = read_uleb128(table, pos)
    end = pos + table_len
    if end > len(table):
        raise EhError("a call-site table runs past the end of .gcc_except_table")
    sites = pads = 0
    seen: set[int] = set()
    while pos < end:
        start, pos = read_call_site_field(table, pos, site_encoding)
        length, pos = read_call_site_field(table, pos, site_encoding)
        pad, pos = read_call_site_field(table, pos, site_encoding)
        _, pos = read_uleb128(table, pos)  # action offset into the action table
        if pos > end:
            raise EhError("a call-site table's last entry runs past its length")
        if (start, length, pad) == (0, 0, 0):
            break
        sites += 1
        pads += int(pad != 0)
        seen.update([pad] if pad else [])
    if pos != end:
        raise EhError("a call-site table does not fill its length")
    return Lsda(sites, pads, len(seen), ttype_encoding != DW_EH_PE_omit)


def pad_bucket(count: int) -> str:
    """Names the landing-pad-count range a body falls into in the report."""
    if count == 0:
        return "none"
    if count == 1:
        return "one"
    if count <= 4:
        return "two-four"
    return "five-plus"


def measure(bodies: list[Body], except_table: bytes, except_base: int) -> dict:
    """Censuses LSDA presence by size class and landing pads by distribution over one section."""
    table_end = except_base + len(except_table)
    by_class = {name: dict.fromkeys(("bodies", "with_lsda", "with_pads"), 0) for name in SIZE_CLASSES}
    by_augmentation: Counter[str] = Counter()
    distribution = dict.fromkeys(PAD_BUCKETS, 0)
    with_lsda = outside = call_sites = landing_pads = distinct_pads = max_pads = 0
    lsdas_seen: set[int] = set()
    for body in bodies:
        row = by_class[lift_probe.size_class(body.size)]
        row["bodies"] += 1
        by_augmentation[body.augmentation] += 1
        if not body.lsda:
            continue
        with_lsda += 1
        row["with_lsda"] += 1
        lsdas_seen.add(body.lsda)
        if not except_base <= body.lsda < table_end:
            outside += 1
            continue
        lsda = parse_lsda(except_table, body.lsda - except_base)
        distribution[pad_bucket(lsda.distinct_pads)] += 1
        row["with_pads"] += int(lsda.distinct_pads > 0)
        call_sites += lsda.call_sites
        landing_pads += lsda.landing_pads
        distinct_pads += lsda.distinct_pads
        max_pads = max(max_pads, lsda.distinct_pads)
    return {
        "bodies": len(bodies),
        "with_lsda": with_lsda,
        "distinct_lsdas": len(lsdas_seen),
        "without_lsda": len(bodies) - with_lsda,
        "lsda_outside_table": outside,
        "by_class": by_class,
        "by_augmentation": dict(by_augmentation),
        "pad_distribution": distribution,
        "call_sites": call_sites,
        "landing_pads": landing_pads,
        "distinct_pads": distinct_pads,
        "max_pads": max_pads,
    }


def read_section(elf: elf_shim_probe.Elf, raw: bytes, name: str) -> tuple[bytes, int]:
    """The bytes of a section and the virtual address it will be loaded at."""
    section = next((s for s in elf.sections if s.name == name), None)
    if section is None or not section.size:
        raise EhError(f"{elf.path} has no {name} section")
    if section.offset + section.size > len(raw):
        raise EhError(f"{name} runs past the end of the file")
    return raw[section.offset : section.offset + section.size], section.addr


def run_probe(so: Path, section: str = "il2cpp") -> dict:
    """Censuses the exception-handling use of one code section of a Linux GameAssembly.so."""
    elf = elf_shim_probe.parse_elf(so)
    raw = so.read_bytes()
    eh_frame, eh_base = read_section(elf, raw, ".eh_frame")
    except_table, except_base = read_section(elf, raw, ".gcc_except_table")
    target = next((s for s in elf.sections if s.name == section), None)
    if target is None or not target.size:
        raise EhError(f"{elf.path} has no {section} section")
    cies = parse_cies(eh_frame, eh_base)
    frames = parse_frames(eh_frame, eh_base)
    per_cie = Counter(f.cie_offset for f in frames)
    sampled = bodies(frames, target.addr, target.addr + target.size)
    report = measure(sampled, except_table, except_base)
    report.update(
        {
            "binary": str(so),
            "binary_sha256": hashlib.sha256(raw).hexdigest(),
            "section": section,
            "section_addr": hex(target.addr),
            "section_bytes": target.size,
            "eh_frame_bytes": len(eh_frame),
            "eh_frame_fdes": len(frames),
            "except_table_bytes": len(except_table),
            "cies": [
                {
                    "offset": hex(cie.offset),
                    "version": cie.version,
                    "augmentation": cie.augmentation,
                    "lsda_encoding": None if cie.lsda_encoding is None else hex(cie.lsda_encoding),
                    "pointer_encoding": hex(cie.pointer_encoding),
                    "personality_slot": None if cie.personality_slot is None else hex(cie.personality_slot),
                    "fdes": per_cie[cie.offset],
                }
                for cie in sorted(cies.values(), key=lambda c: c.offset)
            ],
        }
    )
    return report


def render(report: dict) -> str:
    """The census as lines a person reads: per-class presence, then the landing-pad spread."""
    lines = [f"{report['section']}: {report['bodies']} bodies ({report['section_bytes']} B) in {report['binary']}"]
    for name in SIZE_CLASSES:
        row = report["by_class"][name]
        share = 100.0 * row["with_lsda"] / row["bodies"] if row["bodies"] else 0.0
        lines.append(
            f"  {name:6s} bodies {row['bodies']:8d}  with LSDA {row['with_lsda']:8d} "
            f"({share:5.1f}%)  with landing pads {row['with_pads']:8d}"
        )
    lines.append(
        f"  {'all':6s} bodies {report['bodies']:8d}  with LSDA {report['with_lsda']:8d} "
        f"({report['distinct_lsdas']} distinct tables)  without {report['without_lsda']:8d} "
        f"  outside the table {report['lsda_outside_table']}"
    )
    spread = "  ".join(f"{name} {report['pad_distribution'][name]}" for name in PAD_BUCKETS)
    lines.append(f"  landing pads per body: {spread}")
    lines.append(
        f"  call sites {report['call_sites']}, landing pad entries {report['landing_pads']}, "
        f"distinct pads {report['distinct_pads']}, largest body {report['max_pads']} pads"
    )
    for cie in report["cies"]:
        lines.append(
            f"  CIE {cie['offset']} \"{cie['augmentation']}\" LSDA encoding "
            f"{cie['lsda_encoding'] or '-'} R {cie['pointer_encoding']} "
            f"personality slot {cie['personality_slot'] or '-'}: {cie['fdes']} FDEs"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("so", type=Path, nargs="?", default=DEFAULT_SO, help="Linux GameAssembly.so to analyse")
    ap.add_argument("--section", default="il2cpp", help="code section to census (default il2cpp)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="artifact directory")
    ap.add_argument("--json", action="store_true", help="print the report as JSON instead of a table")
    args = ap.parse_args(argv)
    if not args.so.exists():
        print(f"no such ELF: {args.so}", file=sys.stderr)
        return 2
    try:
        report = run_probe(args.so, args.section)
    except EhError as error:
        print(f"cannot census {args.so}: {error}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render(report))
    print(f"-> {args.out / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
