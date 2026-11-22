"""
Find which blocked lift bodies the pinned Linux game actually executes.

A blocked body links into the lifted image as a trap that aborts by name when
reached, so a hole only matters if the reference build runs it. This tool
attaches gdb to the running Linux game, plants one-shot breakpoints on every
blocked body's entry, and records which ones fire during a scenario.

  uv run scripts/lift_reach.py script --bodies .tools/lift-image-full-v9/bodies.jsonl \\
      --so <GameAssembly.so> --log /tmp/hits.log > probe.py
  sudo gdb -p <pid> -batch -x probe.py          # attach, then play the scenario
  gdb -batch -x probe.py --args ./Megabonk.x86_64    # with --launch: probes from boot
  uv run scripts/lift_reach.py report --bodies ... --so ... --log /tmp/hits.log \\
      --scenario forest-run --out .tools/lift-reach/reach.json

The body starts are ELF virtual addresses, the same ones dump.cs lists as RVAs.
"""

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BODIES = REPO_ROOT / ".tools" / "lift-image-full-v9" / "bodies.jsonl"
DEFAULT_DUMP = REPO_ROOT / ".tools" / "il2cpp_dump_linux" / "dump.cs"
PT_LOAD = 1
PAGE = 0x1000
HIT_LINE = re.compile(r"^HIT 0x([0-9a-fA-F]+)$", re.MULTILINE)

GDB_TEMPLATE = '''import gdb

STARTS = {starts}
LOWEST_VADDR = {lowest}
LOG = {log}


def image_base():
    pid = gdb.selected_inferior().pid
    lows = [
        int(line.split("-")[0], 16)
        for line in open("/proc/%d/maps" % pid)
        if line.rstrip().endswith("GameAssembly.so")
    ]
    if not lows:
        raise gdb.GdbError("GameAssembly.so is not mapped in pid %d" % pid)
    return min(lows)


class Probe(gdb.Breakpoint):
    def __init__(self, bias, start):
        super().__init__("*0x%x" % (bias + start), internal=True)
        self.start = start

    def stop(self):
        with open(LOG, "a") as out:
            out.write("HIT 0x%x\\n" % self.start)
        self.enabled = False
        return False


gdb.execute("handle all nostop noprint pass")
{start}bias = image_base() - (LOWEST_VADDR & ~{page})
probes = [Probe(bias, start) for start in STARTS]
gdb.write("lift_reach: %d probes at bias 0x%x\\n" % (len(probes), bias))
try:
    while True:
        gdb.execute("continue")
except gdb.error:
    pass
'''


def lowest_load_vaddr(elf: bytes) -> int:
    """Smallest p_vaddr among the PT_LOAD program headers of a little-endian ELF64."""
    if elf[:4] != b"\x7fELF" or len(elf) < 64 or elf[4] != 2 or elf[5] != 1:
        raise ValueError("not a little-endian ELF64 image")
    phoff = struct.unpack_from("<Q", elf, 0x20)[0]
    phentsize, phnum = struct.unpack_from("<HH", elf, 0x36)
    vaddrs = []
    for index in range(phnum):
        offset = phoff + index * phentsize
        p_type = struct.unpack_from("<I", elf, offset)[0]
        if p_type == PT_LOAD:
            vaddrs.append(struct.unpack_from("<Q", elf, offset + 16)[0])
    if not vaddrs:
        raise ValueError("ELF image has no PT_LOAD segment")
    return min(vaddrs)


def blocked_starts(bodies: Path) -> list[int]:
    """Entry address of every body the scorer did not lift cleanly, in file order."""
    starts = []
    for line in bodies.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not row["stages"]["clean"]:
            starts.append(row["start"])
    return starts


LAUNCH_START = 'gdb.execute("catch load GameAssembly")\ngdb.execute("run")\ngdb.execute("delete")\n'


def gdb_script(starts: list[int], lowest_vaddr: int, log: str, launch: bool = False) -> str:
    """gdb Python script that logs the first entry into each start, then continues.

    With launch, run the program under gdb and plant the probes the moment GameAssembly
    loads, so a body that runs during boot is seen; otherwise attach to a running process.
    """
    return GDB_TEMPLATE.format(
        start=LAUNCH_START if launch else "",
        starts="[" + ", ".join(hex(start) for start in starts) + "]",
        lowest=hex(lowest_vaddr),
        log=repr(log),
        page=hex(PAGE - 1),
    )


def parse_hits(log: str) -> set[int]:
    """Starts named by HIT lines; any other gdb output is ignored."""
    return {int(match, 16) for match in HIT_LINE.findall(log)}


def classify(probed: list[int], hits: set[int]) -> dict[str, list[int]]:
    """Split the probed starts into hot (hit) and cold; a hit nobody probed is an error."""
    stray = sorted(hits - set(probed))
    if stray:
        raise ValueError("hit at unprobed start " + ", ".join(hex(start) for start in stray))
    return {
        "hot": [start for start in probed if start in hits],
        "cold": [start for start in probed if start not in hits],
    }


def report(sha256: str, scenario: str, probed: list[int], hits: set[int], names: dict[int, list[str]]) -> dict:
    """Hot and cold sets, keyed on the image hash, with each body's metadata names."""
    split = classify(probed, hits)
    return {
        "binary_sha256": sha256,
        "scenario": scenario,
        "probed": len(probed),
        **{kind: [{"start": hex(start), "names": names.get(start, [])} for start in starts] for kind, starts in split.items()},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("script", "report"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--bodies", type=Path, default=DEFAULT_BODIES, help="scored bodies.jsonl")
        cmd.add_argument("--so", type=Path, required=True, help="the pinned GameAssembly.so")
        cmd.add_argument("--log", required=True, help="file the gdb script appends HIT lines to")
    sub.choices["script"].add_argument(
        "--launch", action="store_true", help="for gdb --args <game>: probe from the library load, not an attach"
    )
    sub.choices["report"].add_argument("--scenario", required=True, help="label for what was played")
    sub.choices["report"].add_argument("--dump", type=Path, default=DEFAULT_DUMP, help="dump.cs for names")
    sub.choices["report"].add_argument("--out", type=Path, help="write the report JSON here")
    args = parser.parse_args(argv)

    for path in (args.bodies, args.so):
        if not path.is_file():
            print(f"missing {path}", file=sys.stderr)
            return 1
    starts = blocked_starts(args.bodies)

    if args.command == "script":
        print(gdb_script(starts, lowest_load_vaddr(args.so.read_bytes()), args.log, args.launch))
        return 0

    import lift_names

    log = Path(args.log)
    if not log.is_file():
        print(f"missing {log}: no probe has fired, or the script never ran", file=sys.stderr)
        return 1
    names = lift_names.rva_map(args.dump.read_text()) if args.dump.is_file() else {}
    sha256 = hashlib.sha256(args.so.read_bytes()).hexdigest()
    result = report(sha256, args.scenario, starts, parse_hits(log.read_text()), names)
    print(f"{result['scenario']}: {len(result['hot'])} hot, {len(result['cold'])} cold of {result['probed']}")
    for entry in result["hot"]:
        print(f"  hot {entry['start']} {entry['names'][0] if entry['names'] else '(unnamed)'}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
