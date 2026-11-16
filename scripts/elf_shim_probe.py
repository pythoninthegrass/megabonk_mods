#!/usr/bin/env -S uv run --script
"""Score whether the shipped Linux ELF runtime could be loaded and shimmed on macOS.

Route B is chosen over Route C only because its ELF-load-and-shim step was assumed to
work, so this measures it instead: a stdlib-only ELF reader, the real macOS loader as
the oracle for what a host can resolve, and one pass/fail leg per question the route
notes leave open. Nothing here launches the runtime.
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SO = REPO / ".tools/megabonk-linux-native/Megabonk/GameAssembly.so"
SYMPROBE_SOURCE = Path(__file__).resolve().parent / "native_bind_probe" / "symprobe.c"

ET_DYN = 3
EM_X86_64 = 62
# Apple silicon uses 16 KB pages, which is what decides whether the ELF segments can be
# mapped straight from the file or have to be copied.
PAGE_SIZE_BY_ARCH = {"x86_64": 4096, "arm64": 16384}
PT_LOAD, PT_DYNAMIC, PT_TLS, PT_GNU_RELRO, PT_GNU_STACK = 1, 2, 7, 0x6474E550, 0x6474E552
SHT_RELA, SHT_REL = 4, 9
DT_NAMES = {
    1: "NEEDED", 2: "PLTRELSZ", 3: "PLTGOT", 5: "STRTAB", 6: "SYMTAB", 7: "RELA",
    8: "RELASZ", 9: "RELAENT", 10: "STRSZ", 11: "SYMENT", 12: "INIT", 13: "FINI",
    14: "SONAME", 17: "REL", 18: "RELSZ", 20: "PLTREL", 23: "JMPREL", 24: "BIND_NOW",
    25: "INIT_ARRAY", 26: "FINI_ARRAY", 27: "INIT_ARRAYSZ", 28: "FINI_ARRAYSZ",
    29: "RUNPATH", 30: "FLAGS", 0x6FFFFFFB: "FLAGS_1", 0x6FFFFEF5: "GNU_HASH",
    0x6FFFFFFE: "VERNEED", 0x6FFFFFFF: "VERNEEDNUM",
}
R_X86_64_NAMES = {
    0: "NONE", 1: "64", 2: "PC32", 3: "GOT32", 4: "PLT32", 5: "COPY", 6: "GLOB_DAT",
    7: "JUMP_SLOT", 8: "RELATIVE", 9: "GOTPCREL", 10: "32", 11: "32S", 12: "16",
    13: "PC16", 14: "8", 15: "PC8", 16: "DTPMOD64", 17: "DTPOFF64", 18: "TPOFF64",
    19: "TLSGD", 20: "TLSLD", 21: "DTPOFF32", 22: "GOTTPOFF", 23: "TPOFF32",
    24: "PC64", 25: "GOTOFF64", 26: "GOTPC32", 27: "GOT64", 28: "GOTPCREL64",
    29: "GOTPC64", 30: "GOTPLT64", 31: "PLTOFF64", 32: "SIZE32", 33: "SIZE64",
    34: "GOTPC32_TLSDESC", 35: "TLSDESC_CALL", 36: "REX_GOTPCRELX", 37: "IRELATIVE",
}

# glibc spellings that exist on macOS under another name, or with no 64-bit suffix
# because the native call is already 64-bit. Each is a trampoline, not a rewrite.
ALIAS_SYMBOLS = {
    "open64": "open", "fopen64": "fopen", "ftruncate64": "ftruncate", "lseek64": "lseek",
    "mmap64": "mmap", "readdir64": "readdir",
    "getrlimit64": "getrlimit", "stat64": "stat", "fstat64": "fstat", "lstat64": "lstat",
}
# glibc reserves the underscored _l spelling; macOS exports the POSIX one without it.
LOCALE_ALIAS_SYMBOLS = {
    "__iswctype_l": "iswctype_l", "__strcoll_l": "strcoll_l", "__strxfrm_l": "strxfrm_l",
    "__wcscoll_l": "wcscoll_l", "__wcsxfrm_l": "wcsxfrm_l", "__strftime_l": "strftime_l",
    "__wcsftime_l": "wcsftime_l", "__strtod_l": "strtod_l", "__strtof_l": "strtof_l",
    "__strtold_l": "strtold_l", "__towlower_l": "towlower_l", "__towupper_l": "towupper_l",
    "__wctype_l": "wctype_l", "__nl_langinfo_l": "nl_langinfo_l",
    "__newlocale": "newlocale", "__freelocale": "freelocale", "__duplocale": "duplocale",
}
# Present in the macOS loader but not interchangeable with the Linux contract.
ABI_DIVERGENT = {
    "select": "kernel-2.0 fd_set is baked in at 1024 fds with 8-byte words",
    "pselect": "same fd_set layout as select",
    "__fdelt_chk": "fortified fd_set bounds check tied to that layout",
    "sigaction": "Linux sigaction has sa_restorer and a different flags set",
    "uname": "Linux struct utsname fields differ from the macOS xuname form",
    "getcontext": "Linux mcontext layout is architecture-specific and larger",
    "backtrace": "glibc backtrace is not in libSystem; needs a libunwind walk",
    "backtrace_symbols": "symbolisation reads /proc/self/maps on Linux",
    "pthread_getattr_np": "non-portable glibc extension with no macOS twin",
    "pthread_setname_np": "macOS takes one argument and cannot rename other threads",
    "pthread_kill": "Linux semantics for signal delivery to a thread differ",
    "pthread_sigmask": "sigset_t width differs between the two ABIs",
    "pthread_setcancelstate": "macOS has no thread cancellation",
    "__register_atfork": "glibc pthread_atfork with an extra dso handle argument",
    "syscall": "Linux-only: dispatches by syscall number into the Linux kernel",
    "sem_timedwait": "macOS has no sem_timedwait; absolute-time variant needed",
    "sem_getvalue": "macOS named semaphores only and no value query until 10.11",
    "tcflush": "Linux queue-selector constants differ from the macOS ones",
    "tcgetattr": "Linux struct termios has extra c_ispeed and c_ospeed fields",
    "tcsetattr": "Linux optional-queue actions have no macOS equivalent",
    "iconv": "macOS libiconv lacks several glibc encoding names",
    "getifaddrs": "macOS getifaddrs returns a different if_data payload",
    "if_nametoindex": "same call, but Linux if_nameindex ordering assumptions differ",
    "sendfile64": "Linux sendfile has no offset argument on some architectures",
    "poll": "same call but Linux revents flags and POLL* values differ",
    "ioctl": "Linux ioctl request numbers are not the macOS ones",
    "fcntl": "Linux F_SETLK structures differ from struct flock on macOS",
    "environ": "Linux exports the vector itself; macOS gives ___NSGetEnviron",
    "stderr": "Linux exports stderr as a data symbol; macOS is ___stderrp",
    "__cxa_atexit": "on macOS the runtime installs these itself via __cxa_atexit",
    "__errno_location": "macOS uses __error for the same slot",
    "__ctype_b_loc": "glibc's table has no macOS twin; needs a generated table",
    "__ctype_get_mb_cur_max": "glibc reads the current locale's mb_cur_max",
    "gcvt": "removed from glibc and absent on macOS",
}
# Absent on macOS outright, but a compat layer can honour the contract. Each entry
# states the work, because "needs a shim" is only useful if it says what the shim does.
COMPAT_REQUIRED = {
    "__xstat64": "trampoline onto stat() translating struct stat64 to struct stat",
    "__lxstat64": "trampoline onto lstat() translating struct stat64 to struct stat",
    "__fxstat64": "trampoline onto fstat() translating struct stat64 to struct stat",
    "gettext": "macOS has no libintl; a passthrough is valid only if no catalog loads",
    "dgettext": "passthrough with the domain argument ignored",
    "bindtextdomain": "record and ignore: valid only while no .mo file is opened",
    "bind_textdomain_codeset": "record and ignore: valid only while no .mo file is opened",
    "__pthread_key_create": "glibc internal spelling of pthread_key_create",
    "__sigsetjmp": "glibc internal spelling of sigsetjmp",
    "__uselocale": "glibc internal spelling of uselocale",
    "iconv_open": "not in the default dlsym scope; dlopen libiconv and forward",
    "iconv_close": "not in the default dlsym scope; dlopen libiconv and forward",
}
# A compat claim that names a library is only honest if the symbol is proven to be in
# it, so these are dlopened by the loader probe and the bucket fails if they are not.
COMPAT_LIBS = {
    "iconv_open": "/usr/lib/libiconv.2.dylib",
    "iconv_close": "/usr/lib/libiconv.2.dylib",
}
# Normally satisfied by glibc's dynamic loader. A hand-written loader either provides
# them or must provably never trigger them.
LOADER_OWNED = {
    "__libc_start_main": "glibc's entry point; a self-loader never calls it",
    "__libc_stack_end": "glibc publishes the initial stack top here",
    "__data_start": "link-editor symbol marking the start of .data",
    "data_start": "the unadorned twin of __data_start",
    "__tls_get_addr": "glibc's dynamic TLS accessor; one DTPMOD64 site, 16 B of TLS",
    "__gmon_start__": "weak profiling hook, absent in normal builds",
    "__cxa_finalize": "called by the unload path the host controls",
}
# Weak and optional by ABI: absent is a legal answer on Linux too, so a stub is honest.
WEAK_NOOP = {
    "_ITM_RU1", "_ITM_RU8", "_ITM_addUserCommitAction", "_ITM_deregisterTMCloneTable",
    "_ITM_memcpyRnWt", "_ITM_memcpyRtWn", "_ITM_registerTMCloneTable",
    "_ZGTtdlPv", "_ZGTtnam", "__gcc_personality_v0",
}
# No macOS answer and no shim that could honestly stand in. Anything live here fails
# the spike, so this list is the route's kill switch and stays short on purpose.
UNIMPLEMENTABLE: dict[str, str] = {}

MATH_SYMBOLS = {
    "acos", "acosf", "asin", "asinf", "atan", "atan2", "atan2f", "atanf", "cabs", "ceil",
    "ceilf", "cos", "cosf", "cosh", "difftime", "div", "exp", "exp2f", "expf", "floor",
    "floorf", "fmod", "fmodf", "ldexpf", "log", "log10", "log10f", "logf", "modf", "pow",
    "powf", "sin", "sinf", "sinh", "sqrt", "sqrtf", "tan", "tanf", "tanh", "isnan",
    "__divdc3",
}
RELOC_HANDLERS = {
    "64": "store base + addend, or the resolved symbol value",
    "32": "store the low 32 bits of base + addend with a range check",
    "32S": "same as 32 with a signed range check",
    "RELATIVE": "store base + addend; the whole segment is base-relative",
    "GLOB_DAT": "store the resolved symbol value into a GOT slot",
    "JUMP_SLOT": "resolve the PLT callee eagerly or lazily into a GOT slot",
    "GOTPCREL": "store resolved symbol minus load base into a GOT slot",
    "REX_GOTPCRELX": "linker relaxation: may become PC32 plus a load of the GOT slot",
    "PC32": "resolved symbol minus the place; local after translation so static",
    "PLT32": "call target: rewrite to the translated callee or a PLT stub",
    "NONE": "no-op entry emitted by the linker; advance and skip it",
    # Dynamic TLS. One DTPMOD64 site and 16 B of TLS in this binary, so a fixed module
    # token plus a hand-written __tls_get_addr covers it; recorded, not hand-waved.
    "DTPMOD64": "store the self-loaded module's token; one module so one constant",
    "DTPOFF64": "store the symbol's offset within the module's TLS block",
    "DTPOFF32": "same as DTPOFF64 truncated to 32 bits",
    "TPOFF64": "negative offset from the host TCB; only for static TLS",
    "TPOFF32": "same as TPOFF64 truncated to 32 bits",
    "TLSGD": "emit a call to the TLS accessor with the module and offset pair",
    "TLSLD": "emit a call to the TLS accessor with the local module and offset",
    "GOTTPOFF": "store the TPOFF value into a GOT slot for a mov to read",
    "GOTPC32_TLSDESC": "emit a TLS descriptor pair next to the GOT slot",
    "TLSDESC_CALL": "call through the TLS descriptor pair",
}
COPY_RELOC = "COPY"


class ElfError(RuntimeError):
    """The file is not the ELF shared object the spike expects."""


@dataclass(frozen=True)
class Section:
    name: str
    type: int
    flags: int
    addr: int
    offset: int
    size: int
    entsize: int
    link: int


@dataclass(frozen=True)
class Segment:
    type: int
    flags: int
    offset: int
    vaddr: int
    filesz: int
    memsz: int
    align: int


@dataclass(frozen=True)
class Dynsym:
    name: str
    bind: int
    type: int
    shndx: int
    version: int


@dataclass(frozen=True)
class Rela:
    offset: int
    type: int
    sym: int
    addend: int
    section: str


@dataclass
class Elf:
    path: Path
    e_type: int
    machine: int
    entry: int
    sections: list[Section]
    segments: list[Segment]
    dynamic: dict[str, int]
    dynamic_list: dict[str, list[int]]
    dynsyms: list[Dynsym]
    relocs: list[Rela]
    verneed: dict[int, str]
    soname: str

    @property
    def loads(self) -> list[Segment]:
        return [s for s in self.segments if s.type == PT_LOAD]

    def offset_of(self, vaddr: int) -> int:
        for seg in self.loads:
            if seg.vaddr <= vaddr < seg.vaddr + seg.filesz:
                return seg.offset + (vaddr - seg.vaddr)
        raise ElfError(f"virtual address {hex(vaddr)} is not covered by a PT_LOAD")

    def name_of(self, sym_index: int) -> str | None:
        if sym_index >= len(self.dynsyms):
            return None
        return self.dynsyms[sym_index].name

    def undefined(self) -> list[Dynsym]:
        return [s for s in self.dynsyms if s.shndx == 0 and s.bind in (1, 2)]


def parse_elf(path: Path) -> Elf:
    data = path.read_bytes()
    if data[:4] != b"\x7fELF":
        raise ElfError(f"{path} is not an ELF file")
    if data[4] != 2 or data[5] != 1:
        raise ElfError(f"{path} is not 64-bit little-endian")
    e_type, machine = struct.unpack_from("<HH", data, 16)
    entry, phoff, shoff = struct.unpack_from("<QQQ", data, 24)
    _, _, phentsize, phnum, shentsize, shnum, shstrndx = struct.unpack_from("<IHHHHHH", data, 48)

    segments = []
    for i in range(phnum):
        t, flags, off, va, _, filesz, memsz, align = struct.unpack_from(
            "<IIQQQQQQ", data, phoff + i * phentsize
        )
        segments.append(Segment(t, flags, off, va, filesz, memsz, align))
    loads = [s for s in segments if s.type == PT_LOAD]

    def to_off(vaddr: int) -> int:
        for seg in loads:
            if seg.vaddr <= vaddr < seg.vaddr + seg.filesz:
                return seg.offset + (vaddr - seg.vaddr)
        raise ElfError(f"virtual address {hex(vaddr)} is not mapped")

    def cstr(at: int) -> str:
        end = data.index(b"\0", at)
        return data[at:end].decode("utf-8", "replace")

    raw_sections = []
    for i in range(shnum):
        nm, ty, flags, addr, off, size, entsize, link, _info, _ent = struct.unpack_from(
            "<IIQQQQIIQQ", data, shoff + i * shentsize
        )
        raw_sections.append((nm, ty, flags, addr, off, size, entsize, link))
    strtab_off = to_off(raw_sections[shstrndx][3]) if raw_sections[shstrndx][3] else raw_sections[shstrndx][4]
    sections = [
        Section(cstr(strtab_off + nm), ty, flags, addr, off, size, entsize, link)
        for nm, ty, flags, addr, off, size, entsize, link in raw_sections
    ]
    by_name = {s.name: s for s in sections}

    dynamic_list: dict[str, list[int]] = {}
    dyn_sec = by_name.get(".dynamic")
    if dyn_sec is None:
        raise ElfError(f"{path} has no .dynamic section")
    for i in range(dyn_sec.size // 16):
        tag, val = struct.unpack_from("<Qq", data, dyn_sec.offset + i * 16)
        if tag == 0:
            break
        key = DT_NAMES.get(tag, f"TAG_{tag:#x}")
        dynamic_list.setdefault(key, []).append(val)
    dynamic = {k: v[0] for k, v in dynamic_list.items()}

    symtab = by_name[".dynsym"]
    str_off = to_off(dynamic["STRTAB"])
    ver_sec = by_name.get(".gnu.version")
    nver = ver_sec.size // 2 if ver_sec else 0
    vers = [struct.unpack_from("<H", data, ver_sec.offset + 2 * i)[0] for i in range(nver)] if ver_sec else []

    verneed: dict[int, str] = {}
    if "VERNEED" in dynamic:
        off = to_off(dynamic["VERNEED"])
        for _ in range(64):
            # Elf64_Verneed: half version, half cnt, word file, word aux, word next
            _vn_version, _vn_cnt, _vn_file, vn_aux, vn_next = struct.unpack_from("<HHIII", data, off)
            a = off + vn_aux
            for _ in range(256):
                # Elf64_Vernaux: word hash, half flags, half other, word name, word next
                if not a:
                    break
                _vna_hash, _vna_flags, vna_other, vna_name, vna_next = struct.unpack_from("<IHHII", data, a)
                if vna_name:
                    verneed[vna_other] = cstr(str_off + vna_name)
                a = a + vna_next if vna_next else 0
            if not vn_next:
                break
            off += vn_next

    dynsyms: list[Dynsym] = []
    for i in range(symtab.size // 24):
        nm, info, _other, shndx = struct.unpack_from("<IBBH", data, symtab.offset + i * 24)
        dynsyms.append(
            Dynsym(cstr(str_off + nm), info >> 4, info & 0xF, shndx, vers[i] if i < len(vers) else 0)
        )

    relocs: list[Rela] = []
    for sec in sections:
        if sec.type == SHT_RELA and sec.size:
            for i in range(sec.size // 24):
                off, info, addend = struct.unpack_from("<QQq", data, sec.offset + i * 24)
                relocs.append(Rela(off, info & 0xFFFFFFFF, info >> 32, addend, sec.name))
        elif sec.type == SHT_REL and sec.size:
            for i in range(sec.size // 16):
                off, info = struct.unpack_from("<QQ", data, sec.offset + i * 16)
                relocs.append(Rela(off, info & 0xFFFFFFFF, info >> 32, 0, sec.name))

    soname = ""
    if "SONAME" in dynamic:
        soname = cstr(str_off + dynamic["SONAME"])
    return Elf(path, e_type, machine, entry, sections, segments, dynamic, dynamic_list,
               dynsyms, relocs, verneed, soname)


def build_symprobe(cc: str = "cc") -> Path:
    out = REPO / ".tools/elf-shim/symprobe"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([cc, "-O1", "-o", str(out), str(SYMPROBE_SOURCE)], check=True)
    return out


def probe_macos_loader(
    symprobe: Path, names: list[str], libs: tuple[str, ...] = ()
) -> dict[str, dict[str, str | None]]:
    """Ask the macOS loader which spellings of each name actually resolve.

    dyld's dlsym accepts the unadorned ELF name, so the underscore Mach-O adds is a
    dyld convenience rather than a rewrite a resolver has to perform; the reported
    source says which spelling won. Images named in ``libs`` are dlopened first, which
    proves a recipe that depends on a library outside the default search scope.
    """
    if not names:
        return {}
    out: dict[str, dict[str, str | None]] = {}
    pre = [arg for lib in libs for arg in ("--lib", lib)]
    chunk = 400
    for start in range(0, len(names), chunk):
        batch = names[start:start + chunk]
        query: list[str] = []
        for n in batch:
            query.append(n)
        proc = subprocess.run(
            [str(symprobe), *pre, *query], capture_output=True, text=True, check=True
        )
        found: dict[str, tuple[str, str]] = {}
        for line in proc.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[1] and parts[1] != "0x0":
                found[parts[0]] = (parts[1], parts[2])
        for n in batch:
            hit = found.get(n)
            out[n] = {"addr": hit[0], "source": hit[1]} if hit else {"addr": None, "source": "none"}
    return out


def classify(
    elf: Elf,
    resolved: dict[str, dict[str, str | None]],
    *,
    loader_probed: bool = True,
) -> dict[str, Any]:
    """Bucket every undefined symbol, cross-referenced against relocation references.

    An import no relocation names is unreachable, so a shim for it would be theatre.
    """
    live: set[str] = set()
    undefined_names = {s.name for s in elf.undefined()}
    for r in elf.relocs:
        if r.sym:
            name = elf.name_of(r.sym)
            if name in undefined_names:
                live.add(name)

    undefined = elf.undefined()
    names = sorted({s.name for s in undefined})
    buckets: dict[str, list[str]] = {
        "system": [], "alias": [], "locale-alias": [], "compat-required": [],
        "abi-divergent": [], "weak-noop": [], "loader-owned": [], "unclassified": [],
        "not-probed": [],
    }
    detail: dict[str, dict[str, Any]] = {}
    for name in names:
        hit = resolved.get(name) or {"addr": None, "source": "none"}
        addr, source = hit["addr"], hit["source"]
        live_ref = name in live
        if name in UNIMPLEMENTABLE:
            bucket, why = "unclassified", UNIMPLEMENTABLE[name]
        elif name in WEAK_NOOP:
            bucket, why = "weak-noop", "weak and optional by ABI; a stub is a legal answer"
        elif name in LOADER_OWNED:
            bucket, why = "loader-owned", LOADER_OWNED[name]
        elif name in ALIAS_SYMBOLS:
            bucket, why = "alias", f"thin trampoline onto macOS {ALIAS_SYMBOLS[name]}"
        elif name in LOCALE_ALIAS_SYMBOLS:
            bucket, why = "locale-alias", f"thin trampoline onto POSIX {LOCALE_ALIAS_SYMBOLS[name]}"
        elif name in COMPAT_REQUIRED:
            wanted = COMPAT_LIBS.get(name)
            if wanted and loader_probed and source != wanted:
                bucket, why = "unclassified", f"recipe unverified: {name} not found in {wanted}"
            elif wanted:
                bucket, why = "compat-required", f"{COMPAT_REQUIRED[name]} (recipe not consulted)"
            else:
                bucket, why = "compat-required", COMPAT_REQUIRED[name]
        elif name in ABI_DIVERGENT:
            bucket, why = "abi-divergent", ABI_DIVERGENT[name]
        elif name in MATH_SYMBOLS:
            bucket, why = "system", "libm function, provided by libSystem"
        elif addr:
            bucket, why = "system", f"resolved by the macOS loader via {source}"
        elif loader_probed:
            bucket, why = "unclassified", "no macOS answer and no rule covers it"
        else:
            bucket, why = ("not-probed",
                           "no curated rule and the loader was never asked, so it is unscored")
        buckets[bucket].append(name)
        detail[name] = {"bucket": bucket, "live": live_ref, "macos_addr": addr,
                        "source": source, "why": why}
    live_counts = Counter(detail[n]["bucket"] for n in names if detail[n]["live"])
    live_symbols = sum(1 for n in names if detail[n]["live"])
    return {
        "undefined_unique": len(names),
        "undefined_entries": len(undefined),
        "weak_entries": sum(1 for s in undefined if s.bind == 2),
        "resolved_by_loader": sum(1 for n in names if detail[n]["macos_addr"]),
        "resolved_by_underscore_only": sum(
            1 for n in names if detail[n]["source"] == "underscore"),
        "referenced_by_reloc": live_symbols,
        "loader_probed": loader_probed,
        "unconsulted_recipes": sorted(
            n for n in names if n in COMPAT_LIBS and not loader_probed),
        "buckets": {k: sorted(v) for k, v in buckets.items()},
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
        "live_bucket_counts": dict(live_counts),
        "live_unclassified": sorted(n for n in buckets["unclassified"] if detail[n]["live"]),
        "live_not_probed": sorted(n for n in buckets["not-probed"] if detail[n]["live"]),
        "dead_unclassified": sorted(n for n in buckets["unclassified"] if not detail[n]["live"]),
        "detail": detail,
    }


def leg_imports(elf: Elf, cls: dict[str, Any]) -> dict[str, Any]:
    blockers = cls["live_unclassified"]
    unprobed = cls["live_not_probed"]
    shim_work = (cls["bucket_counts"]["alias"] + cls["bucket_counts"]["locale-alias"]
                 + cls["bucket_counts"]["compat-required"] + cls["bucket_counts"]["abi-divergent"])
    checks = {
        "e_type_is_dynamically_loaded": elf.e_type == ET_DYN,
        "machine_is_x86_64": elf.machine == EM_X86_64,
        "imports_were_measured_against_the_loader": cls["loader_probed"],
        "every_live_import_has_a_named_answer": not blockers and not unprobed,
    }
    return {
        "checks": checks,
        "metrics": {
            "undefined_unique": cls["undefined_unique"],
            "resolved_by_loader": cls["resolved_by_loader"],
            "resolved_by_underscore_only": cls["resolved_by_underscore_only"],
            "referenced_by_reloc": cls["referenced_by_reloc"],
            "shim_work_symbols": shim_work,
            "free_symbols": cls["bucket_counts"]["system"],
            "loader_probed": cls["loader_probed"],
            "unconsulted_recipes": cls["unconsulted_recipes"],
            "not_probed": sorted(cls["buckets"]["not-probed"]),
            "bucket_counts": cls["bucket_counts"],
            "live_bucket_counts": cls["live_bucket_counts"],
        },
        "blockers": (
            sorted(set(blockers)) if cls["loader_probed"]
            else [f"{len(unprobed)} live imports were never offered to the loader: "
                  "run without --skip-dyld-probe"]
        ),
        "dead_but_unclassified": cls["dead_unclassified"],
        "pass": all(checks.values()),
        "conclusion": (
            f"{cls['referenced_by_reloc']} imports are reachable through a relocation, "
            f"{cls['bucket_counts']['system']} resolve free and {shim_work} need a shim; "
            f"{len(blockers)} have no named answer"
            if cls["loader_probed"]
            else f"{cls['referenced_by_reloc']} imports counted without the loader: not scored"
        ),
    }


def leg_abi_nodes(elf: Elf, cls: dict[str, Any]) -> dict[str, Any]:
    """Does glibc symbol versioning constrain a macOS shim?

    Version references are a contract between the binary and the *Linux* loader. A
    macOS build resolves imports by name in code we control, and Mach-O has no symbol
    versioning to satisfy, so binding is a fact to report rather than an obstacle. What
    would be an obstacle is a live import whose versioned name has no macOS answer at
    all, so that is what this leg scores.
    """
    per_node: Counter[str] = Counter()
    live_per_node: Counter[str] = Counter()
    stranded: list[str] = []
    for sym in elf.undefined():
        node = elf.verneed.get(sym.version, "unversioned")
        per_node[node] += 1
        if cls["detail"][sym.name]["live"]:
            live_per_node[node] += 1
            if cls["detail"][sym.name]["bucket"] == "unclassified":
                stranded.append(f"{sym.name}@{node}")
    named = {k: v for k, v in per_node.items() if k != "unversioned"}
    live_named = {k: v for k, v in live_per_node.items() if k != "unversioned"}
    stack = [s for s in elf.segments if s.type == PT_GNU_STACK]
    checks = {
        "version_nodes_recorded": bool(elf.verneed),
        "no_live_versioned_import_lacks_an_answer": not stranded,
    }
    return {
        "checks": checks,
        "metrics": {
            "nodes": elf.verneed,
            "node_names": sorted(set(elf.verneed.values())),
            "imports_per_node": dict(per_node),
            "live_imports_per_node": dict(live_named),
            "live_bound_to_a_node": sum(live_named.values()),
            "needed": elf.dynamic_list.get("NEEDED", []),
            "gnu_stack_executable": bool(stack and stack[0].flags & 1),
        },
        "blockers": sorted(set(stranded)),
        "pass": all(checks.values()),
        "conclusion": (
            f"{len(set(elf.verneed.values()))} distinct version nodes; "
            f"{sum(live_named.values())} live imports bind to one and none of them is stranded"
            if not stranded
            else f"{len(set(stranded))} live versioned imports have no macOS answer"
        ),
    }


def leg_relocs(elf: Elf, cls: dict[str, Any]) -> dict[str, Any]:
    census = Counter(R_X86_64_NAMES.get(r.type, f"UNKNOWN_{r.type}") for r in elf.relocs)
    by_section = Counter(r.section for r in elf.relocs)
    missing = sorted(t for t in census if t not in RELOC_HANDLERS and not t.startswith("UNKNOWN"))
    unknown = sorted(t for t in census if t.startswith("UNKNOWN"))
    sym_named = sum(1 for r in elf.relocs if r.sym and elf.name_of(r.sym))
    undefined_names = {s.name for s in elf.undefined()}
    referenced_imports = sorted({
        elf.name_of(r.sym) for r in elf.relocs
        if r.sym and elf.name_of(r.sym) in undefined_names
    })
    unclassified_refs = sorted(
        name for name in referenced_imports
        if cls["detail"].get(name, {}).get("bucket") == "unclassified"
    )
    checks = {
        "every_reloc_type_has_a_handler": not missing and not unknown,
        "no_copy_relocations": census.get(COPY_RELOC, 0) == 0,
        "every_referenced_import_is_classified": not unclassified_refs,
    }
    blockers = []
    if census.get(COPY_RELOC, 0):
        blockers.append(f"{census[COPY_RELOC]} COPY relocations need the linker to allocate in the host")
    for t in unknown:
        blockers.append(f"relocation type {t} is not classified")
    for t in missing:
        blockers.append(f"relocation type {t} has no handler strategy")
    for name in unclassified_refs:
        blockers.append(f"relocation references unclassified import {name}")
    return {
        "checks": checks,
        "metrics": {
            "total": len(elf.relocs),
            "by_type": dict(census),
            "by_section": dict(by_section),
            "with_symbol_reference": sym_named,
            "relocs_referencing_imports": sum(
                1 for r in elf.relocs if r.sym and elf.name_of(r.sym) in undefined_names),
            "distinct_imports_referenced": len(referenced_imports),
            "handlers": {t: RELOC_HANDLERS[t] for t in sorted(RELOC_HANDLERS)},
            "unclassified_types": unknown,
        },
        "blockers": blockers,
        "pass": all(checks.values()),
        "conclusion": f"{len(elf.relocs)} relocations in {len(census)} types; {len(blockers)} blockers",
    }


def leg_load_strategy(
    elf: Elf, cls: dict[str, Any], reloc_leg: dict[str, Any], target_arch: str = "x86_64"
) -> dict[str, Any]:
    tls = [s for s in elf.segments if s.type == PT_TLS]
    relro = [s for s in elf.segments if s.type == PT_GNU_RELRO]
    aligns = sorted({s.align for s in elf.loads})
    init_arraysz = elf.dynamic.get("INIT_ARRAYSZ", 0)
    fini_arraysz = elf.dynamic.get("FINI_ARRAYSZ", 0)
    by_type = reloc_leg["metrics"]["by_type"]
    tls_relocs = {t: c for t, c in by_type.items() if t.startswith(("TLS", "DTPMOD", "DTPOFF", "TPOFF"))}
    ifunc = by_type.get("IRELATIVE", 0)
    relative = by_type.get("RELATIVE", 0)
    text = next((s for s in elf.sections if s.name == ".text"), None)
    il2cpp = next((s for s in elf.sections if s.name == "il2cpp"), None)
    code_bytes = (text.size if text else 0) + (il2cpp.size if il2cpp else 0)
    page = PAGE_SIZE_BY_ARCH.get(target_arch, 4096)
    align_ok = all(a <= page for a in aligns)
    congruent = [
        {"segment": hex(s.vaddr), "congruent": (s.vaddr - s.offset) % page == 0}
        for s in elf.loads
    ]
    all_congruent = all(c["congruent"] for c in congruent)
    direct = sum(1 for s in elf.loads if s.offset % page == 0 and s.vaddr % page == 0)
    exports = sum(
        1 for s in elf.dynsyms if s.shndx and s.bind in (1, 2) and s.name.startswith("il2cpp_")
    )

    checks = {
        "position_independent": elf.e_type == ET_DYN,
        "segment_alignment_fits_the_target_page": align_ok,
        "segments_are_mappable_without_copying": align_ok and all_congruent,
        "tls_is_small_enough_to_emulate": bool(tls) and tls[0].memsz <= 4096,
        "init_hooks_are_enumerable": init_arraysz % 8 == 0,
        "relocs_classified": reloc_leg["pass"],
    }
    self_relocate = checks["position_independent"] and checks["relocs_classified"]
    strategy = (
        "map the PT_LOAD segments and self-relocate" if self_relocate
        else "translate to a Mach-O dylib and dlopen"
    )
    if self_relocate and not checks["segments_are_mappable_without_copying"]:
        strategy += " by copying pages into anonymous mappings, not mapping the file"
    facts = {
        "target_arch": target_arch,
        "target_page_size": page,
        "load_segments": len(elf.loads),
        "alignments": [hex(a) for a in aligns],
        "vaddr_offset_congruence": congruent,
        "segments_directly_page_aligned": direct,
        "segments_needing_a_down_aligned_map": len(elf.loads) - direct,
        "code_bytes": code_bytes,
        "code_sections": {s.name: s.size for s in (text, il2cpp) if s},
        "tls_memsz": tls[0].memsz if tls else 0,
        "tls_relocs": tls_relocs,
        "irelative_relocs": ifunc,
        "relative_relocations": relative,
        "relro": bool(relro),
        "init_array_entries": init_arraysz // 8,
        "fini_array_entries": fini_arraysz // 8,
        "has_dt_init": "INIT" in elf.dynamic,
        "soname": elf.soname,
        "exported_il2cpp_symbols": exports,
        "imports_resolved_only_by_the_underscored_spelling": cls["resolved_by_underscore_only"],
    }
    blockers = []
    if not align_ok:
        blockers.append(
            f"PT_LOAD alignment {[hex(a) for a in aligns]} exceeds the {target_arch} page size {page}"
        )
    elif not all_congruent:
        blockers.append(
            f"p_vaddr and p_offset diverge mod {page}, so the segments cannot be mapped "
            "from the file and must be copied into anonymous pages"
        )
    if ifunc:
        blockers.append(f"{ifunc} IRELATIVE relocations run resolvers that need a working libc first")
    if tls and tls[0].memsz > 4096:
        blockers.append(f"PT_TLS of {tls[0].memsz} B is too large to fake in a TCB slot")
    return {
        "checks": checks,
        "metrics": facts,
        "strategy": strategy,
        "blockers": blockers,
        "pass": all(checks.values()),
        "conclusion": (
            f"{strategy}; {len(elf.loads)} segments aligned {aligns[0]:#x} on a {page} B page, "
            f"{code_bytes} B of code, {relative} RELATIVE fixups, TLS {facts['tls_memsz']} B, "
            f"{facts['init_array_entries']} init hooks"
        ),
    }


def run_probe(
    so: Path = DEFAULT_SO,
    out: Path | None = None,
    cc: str = "cc",
    skip_dyld: bool = False,
    symprobe: Path | None = None,
    target_arch: str = "x86_64",
) -> dict[str, Any]:
    out = out or REPO / ".tools/elf-shim"
    out.mkdir(parents=True, exist_ok=True)
    elf = parse_elf(so)
    names = sorted({s.name for s in elf.undefined()})
    if skip_dyld:
        resolved = {n: {"addr": None, "source": "none"} for n in names}
    else:
        resolved = probe_macos_loader(
            symprobe or build_symprobe(cc), names, tuple(sorted(set(COMPAT_LIBS.values()))))
    cls = classify(elf, resolved, loader_probed=not skip_dyld)
    legs = {
        "leg1_imports": leg_imports(elf, cls),
        "leg2_abi_nodes": leg_abi_nodes(elf, cls),
        "leg3_relocs": leg_relocs(elf, cls),
    }
    legs["leg4_load_strategy"] = leg_load_strategy(elf, cls, legs["leg3_relocs"], target_arch)
    failed = [k for k, v in legs.items() if not v["pass"]]
    return {
        "binary": str(so),
        "binary_bytes": so.stat().st_size,
        "elf": {
            "e_type": elf.e_type, "machine": elf.machine, "entry": hex(elf.entry),
            "soname": elf.soname, "sections": len(elf.sections), "segments": len(elf.segments),
            "dynsyms": len(elf.dynsyms), "needed": elf.dynamic_list.get("NEEDED", []),
        },
        "host": {"platform": sys.platform, "python": sys.version.split()[0]},
        "target_arch": target_arch,
        "dyld_probe": "skipped" if skip_dyld else "dlsym against RTLD_DEFAULT",
        "legs": legs,
        "failed_legs": failed,
        "classification": cls,
        "pass": not failed,
        "conclusion": (
            "elf-load-and-shim=feasible"
            if not failed
            else "elf-load-and-shim=not-scored: the import legs need the loader probe"
            if skip_dyld and failed == ["leg1_imports"]
            else "elf-load-and-shim=blocked: " + ", ".join(failed)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--so", type=Path, default=DEFAULT_SO, help="Linux GameAssembly.so to analyse")
    ap.add_argument("--out", type=Path, default=REPO / ".tools/elf-shim", help="artifact directory")
    ap.add_argument("--cc", default="cc", help="C compiler for the loader probe")
    ap.add_argument("--skip-dyld-probe", action="store_true", help="analyse without consulting the loader")
    ap.add_argument("--symprobe", type=Path, default=None, help="prebuilt symprobe binary")
    ap.add_argument("--target-arch", choices=sorted(PAGE_SIZE_BY_ARCH), default="x86_64",
                    help="architecture the loaded image would run on (page size differs)")
    args = ap.parse_args(argv)
    if not args.so.exists():
        print(f"no such ELF: {args.so}", file=sys.stderr)
        return 2
    report = run_probe(args.so, args.out, args.cc, args.skip_dyld_probe, args.symprobe,
                       args.target_arch)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for name, leg in report["legs"].items():
        mark = "pass" if leg["pass"] else "FAIL"
        print(f"{mark:4s} {name:20s} {leg['conclusion']}")
        for blocker in leg["blockers"]:
            print(f"       ! {blocker}")
    print(f"{report['conclusion']} -> {args.out / 'summary.json'}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
