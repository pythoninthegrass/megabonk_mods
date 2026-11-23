"""Bind the relocated words that name an import or a PLT entry, and audit every relocation of the rebuilt image.

`lift_reloc.plan_image` leaves two kinds of word for the embedder: those naming an undefined symbol and those naming
a PLT entry. A function import points at the PLT stub of the same name, so a GOT slot and a call through the PLT reach
one definition; a data import points at a named host variable; a weak import nothing defines is null, as ELF specifies.
Anything else is rejected by site, and the link refuses a plan with a rejected word.
"""

from __future__ import annotations

import hashlib
import lift_reloc as rl
from dataclasses import dataclass, field

NO_HOST_IMPLEMENTATION = "function import with no host implementation"
PLT_RESOLVER = "PLT0 lazy-binding resolver; reaching it means a stub ran unbound"
ABSENT_WEAK_IMPORTS = frozenset({"__gmon_start__"})
# Data imports the host defines, by symbol name: C type, initializer run at load, and the header the initializer needs.
HOST_DATA = {
    "stderr": ("FILE *", "stderr", "stdio.h"),
    "environ": ("char **", "*_NSGetEnviron()", "crt_externs.h"),
    "__libc_stack_end": ("void *", "0", None),
}
SYMBOL_KINDS = (rl.R_X86_64_64, rl.R_X86_64_GLOB_DAT, rl.R_X86_64_JUMP_SLOT)


@dataclass
class Bound:
    rows: list = field(default_factory=list)
    aborts: list = field(default_factory=list)
    source: str = ""


def host_variable(name: str) -> str:
    return f"lift_data_{name}"


def abort_entry(name: str) -> str:
    """A reg-ABI entry for an import nothing implements; calling it names the import and aborts."""
    return (
        f"void {abort_name(name)}(unsigned char *reg) {{\n  (void)reg;\n"
        f'  fprintf(stderr, "lift_import_refused: {name}: {NO_HOST_IMPLEMENTATION}\\n");\n  abort();\n}}\n'
    )


def abort_name(name: str) -> str:
    return f"lift_import_{name}"


def host_source(names: set, aborts: list) -> str:
    """C source defining each named host variable, set once at load, and an abort entry per unimplemented import.

    It starts on a new line so it can follow any source.
    """
    if not names and not aborts:
        return ""
    headers = sorted({HOST_DATA[n][2] for n in names if HOST_DATA[n][2]} | ({"stdio.h", "stdlib.h"} if aborts else set()))
    lines = [f"#include <{h}>" for h in headers]
    lines += [f"{HOST_DATA[n][0]}{host_variable(n)};" for n in sorted(names)]
    if names:
        lines.append("__attribute__((constructor)) static void lift_data_init(void) {")
        lines += [f"  {host_variable(n)} = {HOST_DATA[n][1]};" for n in sorted(names)]
        lines.append("}")
    return "\n" + "\n".join(lines) + "\n" + "".join(abort_entry(n) for n in sorted(aborts))


def bind_words(plan: rl.ImagePlan, image: rl.Image, stubs: dict[int, str]) -> Bound:
    """Turns every `unbound` and `plt` word of the plan into a patch, or rejects it; `stubs` maps a PLT stub address to its import."""
    first: dict[str, int] = {}
    for address in sorted(stubs):
        first.setdefault(stubs[address], address)
    symbols = {s.name: s for s in image.symbols if not s.defined}
    plt0 = next((s["va"] for s in image.sections if s["name"].lstrip("._").startswith("plt")), None)
    result, used, refused = Bound(), set(), set()

    def patch(address: int, binding: str, name: str, **target) -> None:
        site = image.section_of(address)
        plan.patches.append(rl.Patch(site["name"], address - site["va"], None, None, **target))
        result.rows.append({"site": address, "name": name, "binding": binding})

    for address, name in sorted(plan.unbound.items()):
        if symbols[name].weak and name in ABSENT_WEAK_IMPORTS:
            patch(address, "weak null", name, literal=0)
        elif name in first:
            patch(address, "stub", name, function=first[name])
        elif name in HOST_DATA:
            used.add(name)
            patch(address, "host data", name, host=host_variable(name))
        elif symbols[name].weak:
            patch(address, "weak null", name, literal=0)
        elif not symbols[name].data:
            refused.add(name)
            patch(address, "named abort", name, host=abort_name(name))
        else:
            plan.rejected[address] = f"RELOC_UNBOUND:{name}"
    for address, target in sorted(plan.plt.items()):
        if target in stubs:
            patch(address, "stub", stubs[target], function=target)
        elif target == plt0:
            if not any(row["address"] == target for row in result.aborts):
                result.aborts.append(
                    {"address": target, "name": "plt_resolver", "disposition": "abort", "reason": PLT_RESOLVER, "host": None}
                )
            patch(address, "stub", "plt_resolver", function=target)
        else:
            plan.rejected[address] = f"RELOC_PLT_TARGET:{target:x}"
    plan.unbound.clear()
    plan.plt.clear()
    plan.patches.sort(key=lambda p: (p.section, p.offset))
    result.source = host_source(used, refused)
    return result


def _target(patch: rl.Patch) -> dict:
    if patch.function is not None:
        return {"function": patch.function}
    if patch.target is not None:
        return {"section": patch.target[0], "offset": patch.target[1]}
    if patch.host is not None:
        return {"host": patch.host}
    if patch.literal is not None:
        return {"literal": patch.literal}
    return {"code": patch.code}


def mapping(image: rl.Image, plan: rl.ImagePlan) -> list[dict]:
    """One row per patched word: its address, original relocation kind and symbol, and the rebuilt target it now holds."""
    start = {s["name"]: s["va"] for s in image.sections}
    rows = []
    for patch in plan.patches:
        site = start[patch.section] + patch.offset
        reloc = image.relocs[site]
        row = {"site": site, "kind": rl.RELOC_NAMES.get(reloc.type, str(reloc.type))}
        if reloc.type in SYMBOL_KINDS:
            row["symbol"] = image.symbols[reloc.sym].name
        rows.append(row | {"target": _target(patch)})
    return sorted(rows, key=lambda r: r["site"])


def report(image: rl.Image, plan: rl.ImagePlan, images: dict[str, bytes]) -> dict:
    """Relocation totals by kind and one row per section; fails when a relocation of the image has no patch.

    `images` holds the initial, unpatched bytes of each section the build defined (the rest are marked undefined); their
    zero-fill and digest are recorded.
    """
    start = {s["name"]: s["va"] for s in image.sections}
    sites = {start[p.section] + p.offset for p in plan.patches}
    missing = sorted(set(image.relocs) - sites)
    if missing:
        raise rl.RelocError(f"UNACCOUNTED:{len(missing)} relocations have no patch (first: {missing[0]:x})")
    kinds: dict[str, int] = {}
    for site in sites:
        name = rl.RELOC_NAMES.get(image.relocs[site].type, str(image.relocs[site].type))
        kinds[name] = kinds.get(name, 0) + 1
    words: dict[str, int] = {}
    for patch in plan.patches:
        words[patch.section] = words.get(patch.section, 0) + 1
    sections = []
    for section in image.sections:
        row = {
            "name": section["name"],
            "va": section["va"],
            "size": section["size"],
            "protection": image.protection.get(section["name"]),
            "relocated_words": words.get(section["name"], 0),
            "defined": section["name"] in images,
        }
        if section["name"] in images:
            data = images[section["name"]]
            row |= {"zero_filled": not any(data), "sha256": hashlib.sha256(data).hexdigest()}
        sections.append(row)
    return {"relocations": {"total": len(image.relocs), "patched": len(plan.patches), "kinds": kinds}, "sections": sections}
