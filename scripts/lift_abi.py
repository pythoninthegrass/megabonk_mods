"""Generate typed native adapters for lifted Linux x86-64 SysV functions.

The compiler lowers the native side; this module only models the source SysV
register/stack layout. Signatures are explicit and intentionally exclude aggregates,
variadic calls and extended vectors until their ABI classification is implemented.
"""

import re
from dataclasses import dataclass
from pcode_lift import EH_PENDING_PAD


class AbiError(ValueError):
    pass


TYPES = {
    "void": ("void", 0),
    "u8": ("uint8_t", 1),
    "i8": ("int8_t", 1),
    "u16": ("uint16_t", 2),
    "i16": ("int16_t", 2),
    "u32": ("uint32_t", 4),
    "i32": ("int32_t", 4),
    "u64": ("uint64_t", 8),
    "i64": ("int64_t", 8),
    "ptr": ("void *", 8),
    "f32": ("float", 4),
    "f64": ("double", 8),
    "v4f32": ("lift_v4f32", 16),
    "v2f64": ("lift_v2f64", 16),
    "v4u32": ("lift_v4u32", 16),
}
EH_TLS_BASE = 0x1F10
PT_TLS = 7
INTEGER_REGS = (0x38, 0x30, 0x10, 0x8, 0x80, 0x88)
SSE_REGS = tuple(0x1200 + i * 0x40 for i in range(8))


@dataclass(frozen=True)
class Signature:
    args: tuple[str, ...]
    result: str
    variadic: bool = False

    def __post_init__(self):
        if self.variadic:
            raise AbiError("variadic signatures are unsupported")
        if len(self.args) > 256:
            raise AbiError("unsupported signature: more than 256 arguments")
        for kind in self.args:
            if kind not in TYPES or kind == "void":
                raise AbiError(f"unsupported argument type: {kind}")
        if self.result not in TYPES:
            raise AbiError(f"unsupported result type: {self.result}")


@dataclass(frozen=True)
class Slot:
    space: str
    offset: int
    size: int


C_KEYWORDS = frozenset(
    [
        "auto",
        "break",
        "case",
        "char",
        "const",
        "continue",
        "default",
        "do",
        "double",
        "else",
        "enum",
        "extern",
        "float",
        "for",
        "goto",
        "if",
        "inline",
        "int",
        "long",
        "register",
        "restrict",
        "return",
        "short",
        "signed",
        "sizeof",
        "static",
        "struct",
        "switch",
        "typedef",
        "union",
        "unsigned",
        "void",
        "volatile",
        "while",
    ]
)
# Host symbols the generated translation unit defines or declares itself.
RESERVED_NAMES = frozenset(["abort", "memcpy", "lift_dispatch"])
IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


@dataclass(frozen=True)
class Binding:
    address: int
    name: str
    signature: Signature
    declared_name: str | None = None

    def __post_init__(self):
        if type(self.address) is not int or not 0 < self.address < 1 << 64:
            raise AbiError("binding address must be a nonzero uint64")
        if (
            not IDENTIFIER.fullmatch(self.name)
            or self.name in C_KEYWORDS
            or self.name in RESERVED_NAMES
            or self.name.startswith(("sub_", "lift_"))
        ):
            raise AbiError(f"invalid or reserved C identifier: {self.name!r}")
        if self.declared_name is not None and (not IDENTIFIER.fullmatch(self.declared_name) or self.declared_name in C_KEYWORDS):
            raise AbiError(f"invalid host symbol name: {self.declared_name!r}")


@dataclass(frozen=True)
class RawBinding:
    """A native function that takes the guest register file and owns the guest RSP, such as the unwinder."""

    address: int
    name: str

    def __post_init__(self):
        Binding(self.address, self.name, Signature((), "void"))


@dataclass(frozen=True)
class Tls:
    """The one TLS module of the image: its `__tls_get_addr` and the initial contents of a thread's block."""

    get_addr: int
    image: bytes
    per_thread: bool = False

    def __post_init__(self):
        if not self.image:
            raise AbiError("TLS image is empty")
        RawBinding(self.get_addr, "tls_get_addr")


def tls_image(elf, raw: bytes) -> bytes | None:
    """Initial TLS block of an ELF: the initialised data from the file, then zeros up to the segment's memory size."""
    segments = [s for s in elf.segments if s.type == PT_TLS]
    if not segments:
        return None
    if len(segments) > 1:
        raise AbiError("more than one TLS segment")
    seg = segments[0]
    if seg.filesz > seg.memsz or seg.offset + seg.filesz > len(raw):
        raise AbiError("TLS segment runs past the end of the file")
    return raw[seg.offset : seg.offset + seg.filesz] + bytes(seg.memsz - seg.filesz)


def argument_layout(kinds: tuple[str, ...]) -> tuple[Slot, ...]:
    Signature(kinds, "void")
    integer = sse = stack = 0
    slots = []
    for kind in kinds:
        size = TYPES[kind][1]
        floating = kind.startswith(("f", "v"))
        bank, index = (SSE_REGS, sse) if floating else (INTEGER_REGS, integer)
        if index < len(bank):
            slots.append(Slot("reg", bank[index], size))
            if floating:
                sse += 1
            else:
                integer += 1
        else:
            alignment = max(8, size)
            stack = (stack + alignment - 1) // alignment * alignment
            slots.append(Slot("stack", stack + 8, size))
            stack += max(8, size)
    return tuple(slots)


def location(slot: Slot) -> str:
    return f"{'reg' if slot.space == 'reg' else 'sp'} + {slot.offset}"


def result_slot(kind: str) -> Slot:
    return Slot("reg", 0x1200 if kind.startswith(("f", "v")) else 0, TYPES[kind][1])


# Runtime symbols lifted bodies call for instructions the host cannot execute; weak so an embedder can supply a measured one.
HOST_HELPERS = [
    "typedef struct { uint32_t eax, ebx, ecx, edx; } lift_cpuid_leaf;",
    "__attribute__((weak)) int lift_cpuid_leaf_at(uint64_t leaf, lift_cpuid_leaf *out) {",
    "  (void)leaf; (void)out;",
    "  return 0;",
    "}",
    "__attribute__((weak)) void lift_cpuid(uint64_t leaf, uint32_t *out) {",
    "  lift_cpuid_leaf v = {0, 0, 0, 0};",
    "  if (!lift_cpuid_leaf_at(leaf, &v)) { v.eax = v.ebx = v.ecx = v.edx = 0; }",
    "  out[0] = v.eax; out[1] = v.ebx; out[2] = v.edx; out[3] = v.ecx;",
    "}",
    "__attribute__((weak)) _Bool lift_rdrand(uint64_t *out) {",
    "  static uint64_t state = UINT64_C(0x2545F4914F6CDD1D);",
    "  uint64_t z = state += UINT64_C(0x9E3779B97F4A7C15);",
    "  z = (z ^ (z >> 30)) * UINT64_C(0xBF58476D1CE4E5B9);",
    "  z = (z ^ (z >> 27)) * UINT64_C(0x94D049BB133111EB);",
    "  *out = z ^ (z >> 31);",
    "  return 1;",
    "}",
    "__attribute__((weak, noreturn)) void lift_hole(uint64_t body, uint64_t site) {",
    '  const char *path = getenv("LIFT_HOLE_LOG");',
    '  fprintf(stderr, "lift_hole: body 0x%llx site 0x%llx\\n", (unsigned long long)body, (unsigned long long)site);',
    "  if (path) {",
    '    FILE *log = fopen(path, "a");',
    "    if (log) {",
    '      fprintf(log, "lift_hole: body 0x%llx site 0x%llx\\n", (unsigned long long)body, (unsigned long long)site);',
    "      fclose(log);",
    "    }",
    "  }",
    "  abort();",
    "}",
]


def generate(
    exports: list[Binding],
    imports: list[Binding],
    raw: list[RawBinding] = (),
    callable_bodies: list[int] = (),
    tls: Tls | None = None,
    aliases: dict[int, int] | None = None,
) -> str:
    """`aliases` maps an address to the lifted body or binding it forwards to, such as a PLT stub of an image function."""
    raw = list(raw)
    callable_bodies = list(callable_bodies)
    if any(b.declared_name for b in exports):
        raise AbiError("only an import can name a host symbol")
    typed = exports + imports
    bindings = typed + raw + ([RawBinding(tls.get_addr, "tls_get_addr")] if tls else [])
    if len({b.address for b in bindings}) != len(bindings) or len({b.name for b in bindings}) != len(bindings):
        raise AbiError("duplicate binding address or name")
    if len(set(callable_bodies) | {b.address for b in bindings}) != len(bindings) + len(set(callable_bodies)):
        raise AbiError("duplicate binding address or name")
    aliases = dict(aliases or {})
    known = {b.address for b in bindings} | set(callable_bodies)
    if any(a in known for a in aliases):
        raise AbiError("duplicate binding address or name")
    if any(t not in known for t in aliases.values()):
        raise AbiError("alias target is not a lifted body or binding")
    lines = [
        "#include <stdint.h>",
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "#include <string.h>",
        '_Static_assert(sizeof(void *) == 8, "the lifted ABI requires 64-bit pointers");',
        "typedef float lift_v4f32 __attribute__((vector_size(16)));",
        "typedef double lift_v2f64 __attribute__((vector_size(16)));",
        "typedef uint32_t lift_v4u32 __attribute__((vector_size(16)));",
    ]
    for address in [b.address for b in bindings if not (tls and b.address == tls.get_addr)] + callable_bodies:
        lines.append(f"extern void sub_{address:x}(unsigned char *reg);")
    if tls:
        image = ", ".join(str(b) for b in tls.image)
        if tls.per_thread:
            lines.append(f"_Alignas(16) static _Thread_local unsigned char lift_tls[{len(tls.image)}] = {{{image}}};")
        else:
            lines.append(f"static const unsigned char lift_tls_image[{len(tls.image)}] = {{{image}}};")
    for binding in typed:
        sig = binding.signature
        params = ", ".join(f"{TYPES[k][0]} a{i}" for i, k in enumerate(sig.args)) or "void"
        label = f' __asm__("_{binding.declared_name}")' if binding.declared_name else ""
        lines.append(f"{TYPES[sig.result][0]} {binding.name}({params}){label};")
    for binding in raw:
        lines.append(f"extern void {binding.name}(unsigned char *reg);")
    for binding in exports:
        sig = binding.signature
        params = ", ".join(f"{TYPES[k][0]} a{i}" for i, k in enumerate(sig.args)) or "void"
        slots = argument_layout(sig.args)
        spill = max((s.offset - 8 + max(8, s.size) for s in slots if s.space == "stack"), default=0)
        spill = (spill + 15) // 16 * 16
        lines += [
            f"{TYPES[sig.result][0]} {binding.name}({params}) {{",
            "  _Alignas(16) unsigned char reg[8192] = {0};",
            "  _Alignas(16) unsigned char stack[65536] = {0};",
            f"  unsigned char *sp = stack + sizeof stack - {spill + 8};",
            "  uintptr_t rsp = (uintptr_t)sp;",
            "  memcpy(reg + 32, &rsp, 8);",
        ]
        if tls and not tls.per_thread:
            lines += [
                f"  _Alignas(16) unsigned char tls[{len(tls.image)}];",
                "  memcpy(tls, lift_tls_image, sizeof tls);",
                "  uintptr_t tls_base = (uintptr_t)tls;",
                f"  memcpy(reg + {EH_TLS_BASE}, &tls_base, 8);",
            ]
        for i, slot in enumerate(slots):
            lines.append(f"  memcpy({location(slot)}, &a{i}, {slot.size});")
        lines += [
            f"  sub_{binding.address:x}(reg);",
            "  uintptr_t returned_rsp;",
            "  memcpy(&returned_rsp, reg + 32, 8);",
            "  if (returned_rsp != rsp + 8) abort();",
            "  uint64_t pending;",
            f"  memcpy(&pending, reg + {EH_PENDING_PAD}, 8);",
            "  if (pending) abort();",
        ]
        if sig.result != "void":
            slot = result_slot(sig.result)
            lines += [
                f"  {TYPES[sig.result][0]} result;",
                f"  memcpy(&result, {location(slot)}, {slot.size});",
                "  return result;",
            ]
        lines.append("}")
    for binding in imports:
        sig = binding.signature
        lines += [
            f"void sub_{binding.address:x}(unsigned char *reg) {{",
            "  uintptr_t rsp;",
            "  memcpy(&rsp, reg + 32, 8);",
            "  unsigned char *sp = (unsigned char *)rsp;",
            "  (void)sp;",
        ]
        for i, (kind, slot) in enumerate(zip(sig.args, argument_layout(sig.args))):
            lines += [
                f"  {TYPES[kind][0]} a{i};",
                f"  memcpy(&a{i}, {location(slot)}, {slot.size});",
            ]
        call = f"{binding.name}({', '.join(f'a{i}' for i in range(len(sig.args)))})"
        if sig.result == "void":
            lines.append(f"  {call};")
        else:
            slot = result_slot(sig.result)
            lines += [
                f"  {TYPES[sig.result][0]} result = {call};",
                f"  memcpy({location(slot)}, &result, {slot.size});",
            ]
        lines += ["  rsp += 8;", "  memcpy(reg + 32, &rsp, 8);", "}"]
    for binding in raw:
        lines += [f"void sub_{binding.address:x}(unsigned char *reg) {{", f"  {binding.name}(reg);", "}"]
    if tls:
        lines += [
            f"void sub_{tls.get_addr:x}(unsigned char *reg) {{",
            "  uint64_t index, base, offset, rsp;",
            "  memcpy(&index, reg + 0x38, 8);",
        ]
        if tls.per_thread:
            lines += [
                "  uint64_t module;",
                '  if (!index) { fputs("lift_tls: missing TLS index\\n", stderr); abort(); }',
                "  memcpy(&module, (const unsigned char *)(uintptr_t)index, 8);",
                '  if (module != 1) { fputs("lift_tls: unsupported TLS module\\n", stderr); abort(); }',
                "  base = (uintptr_t)lift_tls;",
            ]
        else:
            lines.append(f"  memcpy(&base, reg + {EH_TLS_BASE}, 8);")
        lines.append("  memcpy(&offset, (const unsigned char *)(uintptr_t)index + 8, 8);")
        if tls.per_thread:
            lines.append(
                f'  if (offset >= {len(tls.image)}) {{ fputs("lift_tls: TLS offset out of bounds\\n", stderr); abort(); }}'
            )
        else:
            lines.append(f"  if (!base || offset >= {len(tls.image)}) abort();")
        lines += [
            "  base += offset;",
            "  memcpy(reg, &base, 8);",
            "  memcpy(&rsp, reg + 32, 8);",
            "  rsp += 8;",
            "  memcpy(reg + 32, &rsp, 8);",
            "}",
        ]
    for alias, target in aliases.items():
        lines += [f"void sub_{alias:x}(unsigned char *reg) {{", f"  sub_{target:x}(reg);", "}"]
    lines += HOST_HELPERS
    lines += ["void lift_dispatch(uint64_t target, unsigned char *reg) {", "  switch (target) {"]
    lines += [
        f"  case UINT64_C({a}): sub_{a:x}(reg); return;" for a in [b.address for b in bindings] + callable_bodies + list(aliases)
    ]
    lines += ["  default: abort();", "  }", "}"]
    return "\n".join(lines) + "\n"
