"""Finds the functions of a shipped runtime that a root set reaches by direct calls, and the PLT stubs they call."""

from __future__ import annotations

import bisect
import lift_eh as eh
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

OBJDUMP = Path("/opt/homebrew/opt/llvm/bin/llvm-objdump")
DIRECT = re.compile(r"\t(call|jmp)q?\s+(0x[0-9a-f]+)")
INDIRECT = re.compile(r"\t(call|jmp)q?\s+\*")
TAKEN = re.compile(r"\tleaq?\s.*#\s+(0x[0-9a-f]+)")
PLT_LABEL = re.compile(r"^([0-9a-f]+) <(.+)@plt>:", re.M)


@dataclass
class Closure:
    bodies: dict[int, int] = field(default_factory=dict)
    imports: dict[int, str] = field(default_factory=dict)
    resolved: dict[int, int] = field(default_factory=dict)
    taken: set[int] = field(default_factory=set)
    indirect: dict[int, list[str]] = field(default_factory=dict)
    no_frame: set[int] = field(default_factory=set)


def disassemble(so: Path, lo: int, hi: int, extra: tuple = ()) -> str:
    cmd = [OBJDUMP, "-d", "--no-show-raw-insn", f"--start-address={lo:#x}", f"--stop-address={hi:#x}", *extra, so]
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, check=True).stdout


def plt_names(so: Path) -> dict[int, str]:
    return {int(a, 16): name for a, name in PLT_LABEL.findall(disassemble(so, 0, 1 << 63, ("--section=.plt",)))}


def closure(so: Path, frames: list[eh.Frame], roots: list[int], exported: dict[str, int] | None = None) -> Closure:
    """Direct calls and jumps are followed through the frame descriptions; indirect ones are recorded, not followed.

    A PLT stub whose name the image itself exports is followed to that definition and recorded in `resolved`;
    the others stay in `imports` for the caller to bind. A function whose address is taken is recorded in
    `taken` and not followed: it is only reachable through a pointer, which the caller must bind or refuse.
    """
    by_start = {frame.pc_begin: frame for frame in frames}
    starts = sorted(by_start)
    names = plt_names(so)
    result, work = Closure(), list(roots)
    while work:
        address = work.pop()
        if address in result.bodies or address in result.no_frame:
            continue
        index = bisect.bisect_right(starts, address) - 1
        frame = by_start[starts[index]] if index >= 0 else None
        if frame is None or not frame.pc_begin <= address < frame.pc_begin + frame.pc_range:
            result.no_frame.add(address)
            continue
        lo, hi = frame.pc_begin, frame.pc_begin + frame.pc_range
        result.bodies[lo] = frame.pc_range
        for line in disassemble(so, lo, hi).splitlines():
            direct = DIRECT.search(line)
            if direct:
                target = int(direct.group(2), 16)
                if target in names and names[target] in (exported or {}):
                    result.resolved[target] = exported[names[target]]
                    work.append(exported[names[target]])
                elif target in names:
                    result.imports[target] = names[target]
                elif not lo <= target < hi:
                    work.append(target)
            taken = TAKEN.search(line)
            if taken and int(taken.group(1), 16) in by_start:
                result.taken.add(int(taken.group(1), 16))
            if not direct and INDIRECT.search(line):
                result.indirect.setdefault(lo, []).append(line.strip())
    result.taken -= set(result.bodies)
    return result


def dump_cached(so: Path, bodies: dict[int, int], cache_dir: Path, work: Path) -> tuple[list[dict], list[dict]]:
    """Pcode rows and ELF sections for a closure; the Ghidra run is kept per image, body set and dump script."""
    import hashlib
    import json
    import lift_probe as lp

    key = hashlib.sha256(
        json.dumps([lp.sha256(so), sorted(bodies.items()), lp.dump_script_fingerprint()]).encode()
    ).hexdigest()[:24]
    cached = cache_dir / f"{key}.json"
    if cached.exists():
        record = json.loads(cached.read_text())
        return record["rows"], record["sections"]
    rows, sections = lp.dump_pcode(so, [lp.Fde(a, n) for a, n in sorted(bodies.items())], work)
    if len(rows) != len(bodies) or any(row["undecoded"] for row in rows):
        raise RuntimeError(f"Ghidra dumped {len(rows)} of {len(bodies)} bodies, or left some undecoded")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps({"rows": rows, "sections": sections}))
    return rows, sections
