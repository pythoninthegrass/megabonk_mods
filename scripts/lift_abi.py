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


@dataclass(frozen=True)
class Binding:
    address: int
    name: str
    signature: Signature

    def __post_init__(self):
        if type(self.address) is not int or not 0 < self.address < 1 << 64:
            raise AbiError("binding address must be a nonzero uint64")
        if (
            not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", self.name)
            or self.name
            in {
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
                "abort",
                "memcpy",
                "lift_dispatch",
            }
            or self.name.startswith(("sub_", "lift_"))
        ):
            raise AbiError(f"invalid or reserved C identifier: {self.name!r}")


@dataclass(frozen=True)
class RawBinding:
    """A native function that takes the guest register file and owns the guest RSP, such as the unwinder."""

    address: int
    name: str

    def __post_init__(self):
        Binding(self.address, self.name, Signature((), "void"))


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


def generate(exports: list[Binding], imports: list[Binding], raw: list[RawBinding] = ()) -> str:
    raw = list(raw)
    typed = exports + imports
    bindings = typed + raw
    if len({b.address for b in bindings}) != len(bindings) or len({b.name for b in bindings}) != len(bindings):
        raise AbiError("duplicate binding address or name")
    lines = [
        "#include <stdint.h>",
        "#include <stdlib.h>",
        "#include <string.h>",
        '_Static_assert(sizeof(void *) == 8, "the lifted ABI requires 64-bit pointers");',
        "typedef float lift_v4f32 __attribute__((vector_size(16)));",
        "typedef double lift_v2f64 __attribute__((vector_size(16)));",
        "typedef uint32_t lift_v4u32 __attribute__((vector_size(16)));",
    ]
    for binding in bindings:
        lines.append(f"extern void sub_{binding.address:x}(unsigned char *reg);")
    for binding in typed:
        sig = binding.signature
        params = ", ".join(f"{TYPES[k][0]} a{i}" for i, k in enumerate(sig.args)) or "void"
        lines.append(f"{TYPES[sig.result][0]} {binding.name}({params});")
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
    lines += ["void lift_dispatch(uint64_t target, unsigned char *reg) {", "  switch (target) {"]
    lines += [f"  case UINT64_C({b.address}): sub_{b.address:x}(reg); return;" for b in bindings]
    lines += ["  default: abort();", "  }", "}"]
    return "\n".join(lines) + "\n"
