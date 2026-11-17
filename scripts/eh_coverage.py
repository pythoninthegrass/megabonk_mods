#!/usr/bin/env -S uv run --script
"""Account for every exception-bearing body of the shipped il2cpp section against the guest unwinder.

Reads .eh_frame and .gcc_except_table only. Each body is supported or rejected under a named
reason, and when a pcode cache is given the bodies it holds are checked for landing pads that
are missing from the dumped instructions. Nothing is loaded or run.
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eh_probe  # noqa: E402
import elf_shim_probe  # noqa: E402
import lift_eh  # noqa: E402
import lift_probe  # noqa: E402
import lift_reloc  # noqa: E402
import lift_unwind  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SO = REPO / ".tools/megabonk-linux-native/Megabonk/GameAssembly.so"
DEFAULT_OUT = REPO / ".tools/eh-coverage"
ALLOWED_PERSONALITY = "__gxx_personality_v0"
SHF_ALLOC, SHF_EXECINSTR = 2, 4


def defined_symbol(elf, raw: bytes, name: str) -> int:
    dynsym = next(s for s in elf.sections if s.name == ".dynsym")
    for index, symbol in enumerate(elf.dynsyms):
        if symbol.name == name and symbol.shndx:
            return struct.unpack_from("<Q", raw, dynsym.offset + index * 24 + 8)[0]
    raise SystemExit(f"{elf.path} defines no {name}")


def loaded_sections(elf) -> list[dict]:
    """The allocated sections as the lifter names them: name, address, size and whether they hold code."""
    return [
        {"name": s.name, "va": s.addr, "size": s.size, "exec": bool(s.flags & SHF_EXECINSTR)}
        for s in elf.sections
        if s.addr and s.flags & SHF_ALLOC
    ]


def cached_rows(path: Path) -> list[dict]:
    rows = []
    with path.open() as handle:
        for line in handle:
            record = json.loads(line)
            if "insns" in record:
                rows.append(record)
    return rows


def pad_dump(so: Path, bodies: list[tuple[int, int]], work: Path) -> Path:
    """Dumps pcode for the given bodies in one Ghidra run, or reuses the dump already in `work`."""
    pcode = work / "pcode.jsonl"
    if pcode.exists():
        return pcode
    work.mkdir(parents=True, exist_ok=True)
    # Ghidra rejects a project path with a dot-prefixed element, so the run happens outside .tools.
    with tempfile.TemporaryDirectory(prefix="eh-pad-dump-") as run_dir:
        lift_probe.dump_pcode(so, [lift_probe.Fde(a, n) for a, n in bodies], Path(run_dir))
        shutil.copyfile(Path(run_dir) / "pcode.jsonl", pcode)
    return pcode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("so", type=Path, nargs="?", default=DEFAULT_SO)
    ap.add_argument("--section", default="il2cpp")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pcode-cache", type=Path, help="validated pcode cache whose bodies are checked for missing pads")
    ap.add_argument(
        "--dump-pads",
        action="store_true",
        help="dump pcode for every LSDA body with Ghidra (reused from <out>/pad-dump when present) and check its pads",
    )
    args = ap.parse_args(argv)
    elf = elf_shim_probe.parse_elf(args.so)
    raw = args.so.read_bytes()
    eh_frame, eh_base = eh_probe.read_section(elf, raw, ".eh_frame")
    except_table, except_base = eh_probe.read_section(elf, raw, ".gcc_except_table")
    section = next(s for s in elf.sections if s.name == args.section)
    frames = lift_eh.parse_frames(eh_frame, eh_base)
    resolver = lift_unwind.personality_resolver(elf, raw)
    allowed = {defined_symbol(elf, raw, ALLOWED_PERSONALITY)}
    report = lift_unwind.account(frames, except_table, except_base, resolver, allowed, section.addr, section.addr + section.size)
    lo, hi = section.addr, section.addr + section.size
    image = lift_reloc.load_image(elf, raw, loaded_sections(elf))
    lsdas = sorted({f.lsda for f in frames if f.lsda and lo <= f.pc_begin < hi})
    plan = lift_reloc.plan_types(image, except_table, except_base, lsdas, lift_reloc.PROVEN_CLASSES)
    report["filters"] = lift_unwind.filter_report(frames, except_table, except_base, lo, hi, plan)
    report["type_words"] = {"patched_words": len(plan.patches), "type_slots": len(plan.slots)}
    report["allowed_personalities"] = sorted(hex(a) for a in allowed)
    if args.dump_pads:
        args.pcode_cache = pad_dump(args.so, lift_unwind.lsda_bodies(frames, lo, hi), args.out / "pad-dump")
    if args.pcode_cache:
        rows = cached_rows(args.pcode_cache)
        report["dumped_pads"] = lift_unwind.dumped_pad_check(rows, frames, except_table, except_base)
        report["dumped_pads"]["lsda_bodies"] = len(lift_unwind.lsda_bodies(frames, lo, hi))
        report["dumped_pads"]["not_dumped"] = len(lift_unwind.undumped_lsda_bodies(rows, frames, lo, hi))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not report["rejected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
