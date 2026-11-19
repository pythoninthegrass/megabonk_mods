"""
Name the scored lift bodies from Il2CppDumper's dump.cs for the pinned Linux
GameAssembly.so.

The scored body map keys every body by its address; the ELF's .symtab defines
only the two il2cpp section bounds there, so names come from the metadata dump.
dump.cs lists each managed method with its RVA, so an RVA equal to a body start
names that body.

  uv run scripts/lift_names.py [--dump .tools/il2cpp_dump_linux/dump.cs]
      [--bodies .tools/lift-image-full-v5/bodies.jsonl] [--out names.jsonl]

The dump must be the one taken over the same build as the scored image: the
image name beside each TypeDefIndex is metadata, not ELF, so a mismatched
global-metadata.dat yields confident wrong names.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DUMP = REPO_ROOT / ".tools" / "il2cpp_dump_linux" / "dump.cs"
DEFAULT_BODIES = REPO_ROOT / ".tools" / "lift-image-full-v5" / "bodies.jsonl"

IMAGE_LINE = re.compile(r"^// Image (\d+): (\S+) - (\d+)$")
TYPE_LINE = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|sealed|abstract|static|readonly|partial)\s+)*"
    r"(?:class|struct|enum|interface)\s+([A-Za-z_][\w.]*)"
)
TYPE_INDEX = re.compile(r"// TypeDefIndex: (\d+)")
RVA_LINE = re.compile(r"// RVA: 0x([0-9A-Fa-f]+) ")
MODIFIER = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|static|virtual|override|abstract|sealed|"
    r"extern|readonly|unsafe|async|new|partial)\s+)+"
)
TRAILING_NAME = re.compile(r"(\.?[A-Za-z_]\w*)\s*$")


def image_of(images: list[tuple[int, str]], type_index: int) -> str:
    """Image whose TypeDefIndex range contains type_index, or "?" before the first."""
    if not images or type_index < images[0][0]:
        return "?"
    lo, hi = 0, len(images) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        lo, hi = (mid, hi) if images[mid][0] <= type_index else (lo, mid - 1)
    return images[lo][1]


def method_name(signature: str) -> str | None:
    """Declared name on a method signature line, or None when it is not one."""
    if not MODIFIER.match(signature) or "(" not in signature:
        return None
    head = re.sub(r"<[^<>]*>", "", signature.split("(", 1)[0])
    found = TRAILING_NAME.search(head)
    return found.group(1) if found else None


def rva_map(dump: str) -> dict[int, list[str]]:
    """Map each method RVA in dump.cs to its "image:Class::Method" labels."""
    lines = dump.splitlines()
    images: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        match = IMAGE_LINE.match(lines[index])
        if not match:
            break
        images.append((int(match.group(3)), match.group(2)))
        index += 1
    images.sort()

    names: dict[int, list[str]] = {}
    klass, type_index, pending = "?", -1, None
    for line in lines[index:]:
        match = TYPE_LINE.match(line)
        if match:
            klass = match.group(1)
            found = TYPE_INDEX.search(line)
            type_index = int(found.group(1)) if found else type_index
            pending = None
            continue
        match = RVA_LINE.search(line)
        if match:
            pending = (int(match.group(1), 16), image_of(images, type_index), klass)
            continue
        if line.startswith("//") or not line.strip():
            continue
        if pending:
            name = method_name(line)
            if name:
                rva, image, owner = pending
                names.setdefault(rva, []).append(f"{image}:{owner}::{name}")
            pending = None
    return names


def name_bodies(dump: str, bodies: Path) -> list[dict]:
    """One row per scored body: address, size, clean flag, branchind sites, names."""
    names = rva_map(dump)
    rows = []
    for line in bodies.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows.append(
            {
                "start": hex(row["start"]),
                "size": row["size"],
                "clean": bool(row["stages"]["clean"]),
                "sites": len(row.get("unproven_branchind") or []),
                "names": names.get(row["start"], []),
            }
        )
    return rows


def summarise(rows: list[dict]) -> dict:
    """Counts a caller reports on: how many bodies the dump names, clean or not."""
    named = [row for row in rows if row["names"]]
    blocked = [row for row in rows if not row["clean"]]
    return {
        "bodies": len(rows),
        "named": len(named),
        "clean": sum(1 for row in rows if row["clean"]),
        "blocked": len(blocked),
        "blocked_named": sum(1 for row in blocked if row["names"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--dump", type=Path, default=DEFAULT_DUMP, help="Il2CppDumper dump.cs")
    parser.add_argument("--bodies", type=Path, default=DEFAULT_BODIES, help="scored bodies.jsonl")
    parser.add_argument("--out", type=Path, help="write one JSON line per body here")
    parser.add_argument("--blocked-only", action="store_true", help="restrict --out to non-clean bodies")
    args = parser.parse_args(argv)

    for path in (args.dump, args.bodies):
        if not path.is_file():
            print(f"missing {path}", file=sys.stderr)
            return 1

    rows = name_bodies(args.dump.read_text(), args.bodies)
    counts = summarise(rows)
    print(json.dumps(counts))
    for row in rows:
        if not row["clean"]:
            print(
                f"  {row['start']} {row['size']:>6} B  sites {row['sites']:>2}  "
                f"{row['names'][0] if row['names'] else '(unnamed)'}"
            )

    if args.out:
        selected = [row for row in rows if not row["clean"]] if args.blocked_only else rows
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(json.dumps(row) for row in selected))
        print(f"wrote {len(selected)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
