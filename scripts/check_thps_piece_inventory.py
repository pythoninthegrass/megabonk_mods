"""Check the documented piece partition against the unmodified extracted OBJ."""

import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
OBJ_PATH = ROOT / ".tools/thps1/warehouse/warehouse.obj"
DOC_PATH = ROOT / "docs/thps-warehouse-pieces.md"


class Piece(NamedTuple):
    id: str
    name: str
    groups: tuple[str, ...]
    faces: tuple[int, ...]
    module: str


def face_numbers(text: str) -> tuple[int, ...]:
    result = []
    for token in text.split(","):
        match = re.fullmatch(r"\s*(\d+)(?:-(\d+))?\s*", token)
        if not match:
            raise ValueError(f"invalid face range {token!r}")
        start = int(match[1])
        end = int(match[2] or match[1])
        if start < 1 or end < start:
            raise ValueError(f"invalid face range {token!r}")
        result.extend(range(start, end + 1))
    return tuple(result)


def read_pieces(document: str) -> list[Piece]:
    pieces = []
    for line in document.splitlines():
        if not line.startswith("| piece-"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) != 5 or not all(cells):
            raise ValueError(f"invalid piece row: {line}")
        id_, name, groups, faces, module = cells
        pieces.append(Piece(id_, name, tuple(g.strip() for g in groups.split(",")), face_numbers(faces), module))
    return pieces


def validate(obj: str, document: str) -> list[str]:
    errors = []
    digest = hashlib.sha256(obj.encode()).hexdigest()
    if f"Source SHA-256: `{digest}`" not in document:
        errors.append("source SHA-256 differs from the documented extraction")
    groups: Counter[str] = Counter()
    owners: dict[int, str] = {}
    group = ""
    for line in obj.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "o":
            group = parts[1]
            if group in groups:
                errors.append(f"duplicate source group {group}")
            groups[group] = 0
        elif parts[0] == "f":
            owners[len(owners) + 1] = group
            groups[group] += 1
    empty_line = re.search(r"^Empty objects: (.+)$", document, re.MULTILINE)
    declared_empty = set(re.findall(r"`([^`]+)`", empty_line[1])) if empty_line else set()
    actual_empty = {g for g, count in groups.items() if count == 0}
    for g in sorted(declared_empty ^ actual_empty):
        errors.append(f"empty object declaration differs: {g}")
    try:
        pieces = read_pieces(document)
    except ValueError as error:
        return errors + [str(error)]
    ids: set[str] = set()
    names: set[str] = set()
    assigned: Counter[int] = Counter()
    for piece in pieces:
        if piece.id in ids:
            errors.append(f"duplicate piece ID {piece.id}")
        if piece.name in names:
            errors.append(f"duplicate piece name {piece.name}")
        ids.add(piece.id)
        names.add(piece.name)
        used = set()
        for g in piece.groups:
            if g not in groups:
                errors.append(f"{piece.id}: unknown group {g}")
        for face in piece.faces:
            assigned[face] += 1
            if face not in owners:
                errors.append(f"{piece.id}: unknown face {face}")
            elif owners[face] not in piece.groups:
                errors.append(f"{piece.id}: face {face} belongs to {owners[face]}")
            else:
                used.add(owners[face])
        for g in set(piece.groups) - used:
            errors.append(f"{piece.id}: unused group {g}")
    for face in owners:
        if assigned[face] == 0:
            errors.append(f"unassigned face {face} ({owners[face]})")
        elif assigned[face] > 1:
            errors.append(f"face {face} assigned more than once")
    return errors


def check(obj_path: Path = OBJ_PATH, doc_path: Path = DOC_PATH) -> list[str]:
    return validate(obj_path.read_text(), doc_path.read_text())


def main() -> None:
    errors = check()
    if errors:
        raise SystemExit("\n".join(errors))
    print("Warehouse piece inventory: every source face assigned exactly once")


if __name__ == "__main__":
    main()
