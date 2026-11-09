import check_thps_piece_inventory as inventory
import hashlib
import pytest
from pathlib import Path

needs_extract = pytest.mark.skipif(not inventory.OBJ_PATH.exists(), reason="needs the extraction under .tools/thps1/warehouse")

OBJ = "o WALL\nv 0 0 0\nv 1 0 0\nv 1 0 1\nusemtl brick\nf 1 2 3\no EMPTY\no WINDOW\nf 1 3 2\n"


def document(rows: str, obj: str = OBJ) -> str:
    digest = hashlib.sha256(obj.encode()).hexdigest()
    return f"Source SHA-256: `{digest}`\nEmpty objects: `EMPTY`\n\n| ID | Element | Groups | Faces | Module |\n| --- | --- | --- | --- | --- |\n{rows}"


ROWS = "| piece-wall | Wall panel | WALL | 1 | wall |\n| piece-window | Individual window | WINDOW | 2 | window |\n"


def test_valid_inventory_preserves_polygon_ordinals_and_empty_objects() -> None:
    assert inventory.validate(OBJ, document(ROWS)) == []


@pytest.mark.parametrize(
    ("rows", "diagnostic"),
    [
        (ROWS.splitlines()[0], "unassigned face 2"),
        (ROWS + "| piece-extra | Extra wall | WALL | 1 | wall |\n", "face 1 assigned more than once"),
        (ROWS.replace("WINDOW | 2", "WALL | 2"), "face 2 belongs to WINDOW"),
        (ROWS.replace("WINDOW | 2", "WINDOW | 3"), "unknown face 3"),
        (ROWS.replace("piece-window", "piece-wall"), "duplicate piece ID piece-wall"),
        (ROWS.replace("| 2 |", "| 2-1 |"), "invalid face range"),
        (ROWS.replace("WINDOW |", "MISSING |"), "unknown group MISSING"),
    ],
)
def test_invalid_inventory_reports_actionable_errors(rows: str, diagnostic: str) -> None:
    assert any(diagnostic in error for error in inventory.validate(OBJ, document(rows)))


def test_source_drift_and_empty_object_drift_are_detected() -> None:
    errors = inventory.validate(OBJ + "o NEW_EMPTY\n", document(ROWS))
    assert any("SHA-256" in error for error in errors)
    assert any("NEW_EMPTY" in error for error in errors)


def test_ranges_cover_each_polygon_not_each_triangle() -> None:
    obj = OBJ.replace("f 1 2 3", "f 1 2 3 1")
    rows = "| piece-shell | Wall and window | WALL, WINDOW | 1-2 | shell |\n"
    assert inventory.validate(obj, document(rows, obj)) == []


def test_all_declared_groups_must_contribute_faces() -> None:
    errors = inventory.validate(OBJ, document(ROWS.replace("WALL |", "WALL, WINDOW |")))
    assert any("unused group WINDOW" in error for error in errors)


@needs_extract
def test_committed_inventory_covers_the_extraction() -> None:
    assert inventory.check() == []
    pieces = inventory.read_pieces(inventory.DOC_PATH.read_text())
    assert len(pieces) > 150
    assert any(p.name == "Taxi funbox" for p in pieces)
    assert sum(p.module == "window" for p in pieces) == 7


def test_missing_source_is_not_silently_skipped(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        inventory.check(tmp_path / "absent.obj")


@needs_extract
def test_flat_modules_do_not_include_sloping_rollin_or_hip_faces() -> None:
    vertices = []
    faces = []
    for line in inventory.OBJ_PATH.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append(tuple(float(value) for value in parts[1:4]))
        elif parts[0] == "f":
            faces.append([vertices[int(token.split("/")[0]) - 1] for token in parts[1:]])
    for piece in inventory.read_pieces(inventory.DOC_PATH.read_text()):
        if piece.module != "flat":
            continue
        heights = {vertex[1] for ordinal in piece.faces for vertex in faces[ordinal - 1]}
        assert len(heights) == 1, piece.id
