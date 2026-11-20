"""Load-time relocations for the data words a lifted typed catch reads.

The lifted module keeps an image's data sections as unrelocated file bytes. A typed catch reads a
type-table cell, the typeinfo it points at, that typeinfo's vtable and name; each is a word the
dynamic loader would have relocated. `plan_types` resolves exactly those words, and anything it
cannot prove (a relocation type it does not handle, a typeinfo class it was not told is lifted)
rejects the body by name instead of leaving a word that only looks relocated.
"""

from __future__ import annotations

import lift_eh as eh
from dataclasses import dataclass, field

R_X86_64_64, R_X86_64_RELATIVE = 1, 8
RELOC_NAMES = {
    0: "NONE",
    1: "64",
    2: "PC32",
    3: "GOT32",
    4: "PLT32",
    5: "COPY",
    6: "GLOB_DAT",
    7: "JUMP_SLOT",
    8: "RELATIVE",
    9: "GOTPCREL",
    16: "DTPMOD64",
    17: "DTPOFF64",
    18: "TPOFF64",
    37: "IRELATIVE",
}
PCREL_INDIRECT = 0x90 | 0x10
WORD = 8
SI_WORDS = 3
# Typeinfo classes whose lifted type_info methods run correctly under the guest unwinder, by vtable symbol, with the typeinfo size in words.
PROVEN_CLASSES = {"_ZTVN10__cxxabiv117__class_type_infoE": 2, "_ZTVN10__cxxabiv120__si_class_type_infoE": SI_WORDS}


class RelocError(RuntimeError):
    """A relocated word the lifted module cannot represent."""


@dataclass(frozen=True)
class Reloc:
    type: int
    sym: int
    addend: int


@dataclass(frozen=True)
class Sym:
    name: str
    value: int
    size: int
    defined: bool


@dataclass
class Image:
    """What relocation needs from one ELF: its sections (lifter dicts), relocations, dynamic symbols and file words."""

    sections: list
    relocs: dict
    symbols: list
    words: dict = field(default_factory=dict)
    duplicates: set = field(default_factory=set)

    def section_of(self, address: int) -> dict | None:
        return next((s for s in self.sections if s["va"] <= address < s["va"] + s["size"]), None)

    def word(self, address: int) -> int:
        return self.words.get(address, 0)

    def vtable_symbol(self, address: int) -> Sym | None:
        return next((s for s in self.symbols if s.defined and s.value == address and s.name.startswith("_ZTV")), None)


@dataclass(frozen=True)
class Patch:
    """One relocated word: where it lies, and its value as a dispatchable guest code address or a (section, offset) target."""

    section: str
    offset: int
    code: int | None
    target: tuple | None


@dataclass(frozen=True)
class Slot:
    """A type-table entry (by its address in the exception table) that must point at the cell holding a typeinfo pointer."""

    entry: int
    cell: tuple
    size: int = 8


@dataclass
class TypePlan:
    patches: dict = field(default_factory=dict)
    slots: list = field(default_factory=list)
    rejected: dict = field(default_factory=dict)
    proven: set = field(default_factory=set)


def _resolve(image: Image, address: int, linker: dict | None) -> tuple[Image, int]:
    reloc = image.relocs.get(address)
    if reloc is None:
        raise RelocError(f"RELOC_MISSING:{address:x}")
    if address in image.duplicates:
        raise RelocError(f"RELOC_AMBIGUOUS:{address:x}")
    if reloc.type == R_X86_64_RELATIVE:
        return image, reloc.addend
    if reloc.type == R_X86_64_64:
        symbol = image.symbols[reloc.sym]
        if symbol.defined:
            return image, symbol.value + reloc.addend
        if linker and symbol.name in linker:
            other, value = linker[symbol.name]
            return other, value + reloc.addend
        raise RelocError(f"RELOC_UNDEFINED:{symbol.name}")
    raise RelocError(f"RELOC_TYPE:{RELOC_NAMES.get(reloc.type, reloc.type)}")


def word_patch(image: Image, address: int, linker: dict | None = None) -> Patch:
    """The relocated value of the 8-byte word at `address`; `linker` maps an undefined symbol to (image, address)."""
    section = image.section_of(address)
    if section is None:
        raise RelocError(f"RELOC_SITE_UNMAPPED:{address:x}")
    target_image, target = _resolve(image, address, linker)
    destination = target_image.section_of(target)
    if destination is None:
        raise RelocError("RELOC_TARGET_UNMAPPED")
    offset = address - section["va"]
    if destination["exec"]:
        return Patch(section["name"], offset, target, None)
    return Patch(section["name"], offset, None, (destination["name"], target - destination["va"]))


def _words(image: Image, base: int, count: int, linker: dict | None, patches: dict) -> None:
    """Relocates `count` words from `base`; a word with no relocation must be zero in the file."""
    for index in range(count):
        address = base + index * WORD
        if address in image.relocs:
            patch = word_patch(image, address, linker)
            patches[(patch.section, patch.offset)] = patch
        elif image.word(address):
            raise RelocError(f"WORD_UNRELOCATED:{address:x}")


def _typeinfo(image: Image, address: int, linker: dict | None, proven: dict, patches: dict) -> None:
    """Relocates a typeinfo object whose vtable is one the caller proved, with that vtable; a base class recurses."""
    vtable_image, target = _resolve(image, address, linker)
    symbol = vtable_image.vtable_symbol(target - 2 * WORD)
    if symbol is None or symbol.name not in proven:
        raise eh.EhUnsupported("EH_TYPED_CATCH")
    words = proven[symbol.name]
    _words(image, address, words, linker, patches)
    _words(vtable_image, symbol.value, symbol.size // WORD, linker, patches)
    if words == SI_WORDS:
        base_image, base = _resolve(image, address + 2 * WORD, linker)
        _typeinfo(base_image, base, linker, proven, patches)


def plan_types(image: Image, table: bytes, base: int, lsdas: list[int], proven: dict, linker: dict | None = None) -> TypePlan:
    """Plans the relocated words and type-table slots for each LSDA; a body that cannot be proven is rejected whole.

    `proven` maps a vtable symbol name to its typeinfo object's size in words (2 for a class, 3 with one base),
    for the classes whose lifted methods the caller has shown to be complete. Only the pcrel, indirect encodings the lifted personality reads are accepted.
    """
    plan = TypePlan()
    for lsda in lsdas:
        patches, slots = {}, []
        try:
            for entry in eh.type_entries(table, lsda - base):
                if entry.encoding & 0xF0 != 0x90 or entry.encoding & 0x70 != 0x10:
                    raise eh.EhUnsupported("EH_TTYPE_ENCODING")
                address = base + entry.offset
                cell = address + entry.value
                _words(image, cell, 1, linker, patches)
                _, typeinfo = _resolve(image, cell, linker)
                _typeinfo(image, typeinfo, linker, proven, patches)
                slot = image.section_of(cell)
                slots.append(Slot(address, (slot["name"], cell - slot["va"]), entry.size))
        except RelocError as error:
            plan.rejected[lsda] = f"EH_TYPEINFO_RELOC:{error}"
            continue
        except eh.EhUnsupported as error:
            plan.rejected[lsda] = str(error)
            continue
        plan.proven.add(lsda)
        plan.patches.update(patches)
        plan.slots.extend(slots)
    return plan


class FileWords:
    """File-backed 8-byte words of an ELF by virtual address; an address with no file bytes (NOBITS) reads as zero."""

    def __init__(self, elf, raw: bytes):
        self.elf, self.raw = elf, raw

    def get(self, address: int, default: int = 0) -> int:
        try:
            at = self.elf.offset_of(address)
        except Exception:
            return default
        return int.from_bytes(self.raw[at : at + WORD], "little")


def load_image(elf, raw: bytes, sections: list) -> Image:
    """An Image of a parsed ELF: its relocations (a second one at an offset marks it ambiguous), dynamic symbols and words."""
    import struct

    relocs, duplicates = {}, set()
    for r in elf.relocs:
        if r.offset in relocs:
            duplicates.add(r.offset)
        relocs.setdefault(r.offset, Reloc(r.type, r.sym, r.addend))
    dynsym = next(s for s in elf.sections if s.name == ".dynsym")
    symbols = []
    for index, named in enumerate(elf.dynsyms):
        _, _, _, shndx, value, size = struct.unpack_from("<IBBHQQ", raw, dynsym.offset + index * 24)
        symbols.append(Sym(named.name, value, size, bool(shndx)))
    return Image(sections, relocs, symbols, FileWords(elf, raw), duplicates)
