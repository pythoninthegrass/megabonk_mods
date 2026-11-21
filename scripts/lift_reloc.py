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

R_X86_64_64, R_X86_64_GLOB_DAT, R_X86_64_JUMP_SLOT, R_X86_64_RELATIVE = 1, 6, 7, 8
R_X86_64_DTPMOD64, R_X86_64_DTPOFF64 = 16, 17
PT_LOAD, PT_TLS, PT_GNU_RELRO = 1, 7, 0x6474E552
PF_W, PF_X = 2, 1
STB_WEAK, STT_OBJECT = 2, 1
# Ghidra's block for unresolved imports: not an ELF section and holds no file bytes.
GHIDRA_EXTERNAL = "EXTERNAL"
# The image has one TLS module, and the lifted `__tls_get_addr` ignores the module word of its argument.
TLS_MODULE_ID = 1
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
    weak: bool = False
    data: bool = False


@dataclass
class Image:
    """What relocation needs from one ELF: its sections (lifter dicts), relocations, dynamic symbols and file words."""

    sections: list
    relocs: dict
    symbols: list
    words: dict = field(default_factory=dict)
    duplicates: set = field(default_factory=set)
    protection: dict = field(default_factory=dict)

    def section_of(self, address: int) -> dict | None:
        return next((s for s in self.sections if s["va"] <= address < s["va"] + s["size"]), None)

    def word(self, address: int) -> int:
        return self.words.get(address, 0)

    def vtable_symbol(self, address: int) -> Sym | None:
        return next((s for s in self.symbols if s.defined and s.value == address and s.name.startswith("_ZTV")), None)


@dataclass(frozen=True)
class Patch:
    """One relocated word: where it lies, and its value as a dispatchable guest code address, a (section, offset) target, the lifted body (`function`) at a guest address, a `literal` or the address of a named `host` variable."""

    section: str
    offset: int
    code: int | None
    target: tuple | None
    function: int | None = None
    literal: int | None = None
    host: str | None = None


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


@dataclass
class ImagePlan:
    """Every relocated word of an image: patches ordered by section and offset, plus what cannot be patched, by site address.

    `unbound` holds words naming an undefined symbol and `plt` words naming a PLT entry; both wait for `lift_bind.bind_words`.
    """

    patches: list = field(default_factory=list)
    unbound: dict = field(default_factory=dict)
    plt: dict = field(default_factory=dict)
    rejected: dict = field(default_factory=dict)
    protection: dict = field(default_factory=dict)


def _plan_target(image: Image, reloc: Reloc) -> tuple[int | None, str | None]:
    """The address a word relocates to, or the undefined symbol's name when only the embedder can bind it."""
    if reloc.type == R_X86_64_RELATIVE:
        return reloc.addend, None
    if reloc.type in (R_X86_64_64, R_X86_64_GLOB_DAT, R_X86_64_JUMP_SLOT):
        symbol = image.symbols[reloc.sym]
        if not symbol.defined:
            return None, symbol.name
        return symbol.value + (reloc.addend if reloc.type == R_X86_64_64 else 0), None
    raise RelocError(f"RELOC_TYPE:{RELOC_NAMES.get(reloc.type, reloc.type)}")


def plan_image(image: Image, bodies: frozenset | set) -> ImagePlan:
    """Plans a patch for every relocated word, pointing code at the lifted body (`bodies`, by start address) and data at its section.

    An undefined symbol is recorded in `unbound` and a PLT entry in `plt`, for `lift_bind.bind_words`. A word that targets
    the middle of a body, an unmapped address, or uses a relocation type not handled here is rejected by site address.
    """
    plan = ImagePlan(protection=image.protection)
    for address, reloc in image.relocs.items():
        try:
            if address in image.duplicates:
                raise RelocError(f"RELOC_AMBIGUOUS:{address:x}")
            site = image.section_of(address)
            if site is None:
                raise RelocError(f"RELOC_SITE_UNMAPPED:{address:x}")
            if reloc.type == R_X86_64_DTPMOD64:
                plan.patches.append(Patch(site["name"], address - site["va"], None, None, literal=TLS_MODULE_ID))
                continue
            target, name = _plan_target(image, reloc)
            if name is not None:
                plan.unbound[address] = name
                continue
            destination = image.section_of(target)
            if destination is None:
                destination = next((s for s in image.sections if not s["exec"] and s["va"] + s["size"] == target), None)
                if destination is None:
                    raise RelocError(f"RELOC_TARGET_UNMAPPED:{target:x}")
            offset = address - site["va"]
            if not destination["exec"]:
                plan.patches.append(Patch(site["name"], offset, None, (destination["name"], target - destination["va"])))
            elif target in bodies:
                plan.patches.append(Patch(site["name"], offset, None, None, function=target))
            elif destination["name"].lstrip("._").startswith("plt"):
                plan.plt[address] = target
            else:
                raise RelocError(f"RELOC_MID_BODY:{target:x}")
        except RelocError as error:
            plan.rejected[address] = str(error)
    plan.patches.sort(key=lambda p: (p.section, p.offset))
    return plan


def require_complete(plan: ImagePlan) -> None:
    """Refuses a plan with a word that was rejected, left unbound or left naming a PLT entry, listing the first sites."""
    for field_name in ("rejected", "unbound", "plt"):
        left = getattr(plan, field_name)
        if left:
            first = ", ".join(f"{a:x}: {left[a]}" for a in sorted(left)[:5])
            raise RelocError(f"{field_name.upper()}:{len(left)} relocated words are unaccounted for ({first})")


def protection(segments, sections: list) -> dict[str, str]:
    """Each section's protection after load: `rx`, `ro`, `rw`, `relro` (writable only until relocation is done), `tls` or `external`.

    A `tls` section lies inside the TLS segment, a per-thread template that occupies no loaded memory. Any other section
    must lie wholly inside one loaded segment and, when it touches the RELRO range, wholly inside that range.
    """
    loads = [g for g in segments if g.type == PT_LOAD]
    relro = next((g for g in segments if g.type == PT_GNU_RELRO), None)
    tls = [g for g in segments if g.type == PT_TLS]
    result = {}
    for section in sections:
        start, end, name = section["va"], section["va"] + section["size"], section["name"]
        if name == GHIDRA_EXTERNAL:
            result[name] = "external"
            continue
        if any(g.vaddr <= start and end <= g.vaddr + g.memsz for g in tls):
            result[name] = "tls"
            continue
        segment = next((g for g in loads if g.vaddr <= start and end <= g.vaddr + g.memsz), None)
        if segment is None:
            raise RelocError(f"SECTION_UNMAPPED:{name}")
        if relro and start < relro.vaddr + relro.memsz and end > relro.vaddr:
            if start < relro.vaddr or end > relro.vaddr + relro.memsz:
                raise RelocError(f"SECTION_SPLIT_BY_RELRO:{name}")
            result[name] = "relro"
        else:
            result[name] = "rx" if segment.flags & PF_X else "rw" if segment.flags & PF_W else "ro"
    return result


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
        symbols.append(Sym(named.name, value, size, bool(shndx), named.bind == STB_WEAK, named.type == STT_OBJECT))
    return Image(sections, relocs, symbols, FileWords(elf, raw), duplicates)
