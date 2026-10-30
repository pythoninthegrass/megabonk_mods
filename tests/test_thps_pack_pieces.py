"""Cross-check the committed thps manifest and pieces.json against the inventory tables."""

import check_thps_piece_inventory as inventory
import json
import math
import pytest
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "unity/pack-authoring/packs/thps/manifest.json"
PIECES_PATH = ROOT / "unity/pack-authoring/packs/thps/pieces.json"

WAREHOUSE_SCALE = 79.2
WAREHOUSE_POSITION = (100.0, 0.5, 0.0)
ADDED_ASSETS = ["added-floor-patch-0"] + [f"added-post-{i}" for i in range(10)]

needs_sidecar = pytest.mark.skipif(not PIECES_PATH.exists(), reason="pieces.json is emitted by the Unity pack build")


def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


def sidecar() -> dict:
    return json.loads(PIECES_PATH.read_text())


def inventory_pieces() -> list[inventory.Piece]:
    return inventory.read_pieces(inventory.DOC_PATH.read_text())


def roof_quads() -> list[str]:
    return [entry["asset"] for entry in sidecar()["pieces"] if entry["asset"].startswith("added-roof-quad-")]


def test_manifest_keeps_the_pinned_version_and_warehouse_first() -> None:
    data = manifest()
    assert data["id"] == "thps"
    assert data["version"] == "2.0.21"
    assert data["assets"][0] == "Warehouse"


@needs_sidecar
def test_manifest_lists_every_inventory_piece_and_added_asset_in_order() -> None:
    expected = ["Warehouse"] + [piece.id for piece in inventory_pieces()] + ADDED_ASSETS + roof_quads()
    assert manifest()["assets"] == expected


@needs_sidecar
def test_sidecar_covers_exactly_the_manifest_pieces_in_order() -> None:
    assets = [entry["asset"] for entry in sidecar()["pieces"]]
    assert assets == manifest()["assets"][1:]


@needs_sidecar
def test_source_entries_match_the_inventory_rows() -> None:
    by_asset = {entry["asset"]: entry for entry in sidecar()["pieces"]}
    for piece in inventory_pieces():
        entry = by_asset[piece.id]
        assert entry["kind"] == "source"
        assert entry["module"] == piece.module
        assert entry["groups"] == list(piece.groups)
        assert entry["faces"] == list(piece.faces)


@needs_sidecar
def test_only_window_pieces_are_render_only() -> None:
    for entry in sidecar()["pieces"]:
        if entry["kind"] != "source":
            assert entry["collider"] is True, entry["asset"]
            continue
        row = next(piece for piece in inventory_pieces() if piece.id == entry["asset"])
        assert entry["collider"] is (row.module != "window"), entry["asset"]


@needs_sidecar
def test_added_entries_name_their_generating_source() -> None:
    by_asset = {entry["asset"]: entry for entry in sidecar()["pieces"]}
    assert by_asset["added-floor-patch-0"]["source"] == "FloorPatches[0]"
    assert by_asset["added-floor-patch-0"]["module"] == "floor"
    for i in range(10):
        entry = by_asset[f"added-post-{i}"]
        assert entry["source"] == f"RailPosts[{i}]"
        assert entry["module"] == "prop"
    for asset in roof_quads():
        assert by_asset[asset]["source"] == "WarehouseRoof.Quads"
        assert by_asset[asset]["module"] == "roof"


@needs_sidecar
def test_positions_are_the_recorded_pivots_in_world_space() -> None:
    for entry in sidecar()["pieces"]:
        position, pivot = entry["position"], entry["pivot"]
        for axis in range(3):
            assert position[axis] == pytest.approx(pivot[axis] * WAREHOUSE_SCALE + WAREHOUSE_POSITION[axis], abs=1e-3), entry["asset"]


@needs_sidecar
def test_yaw_is_recorded_only_for_convention_riding_modules() -> None:
    riding = {"main-transition", "wall-transition", "outer-bank", "bank-end", "hip", "hip-apron", "roll-in", "kicker", "convex-tip"}
    for entry in sidecar()["pieces"]:
        if entry["kind"] == "source" and entry["module"] in riding:
            assert -180.0 <= entry["yaw"] <= 180.0 and math.isfinite(entry["yaw"])
        else:
            assert entry["yaw"] == 0.0, entry["asset"]


PREFAB_DIR = ROOT / "unity/pack-authoring/Assets/Thps"
needs_prefabs = pytest.mark.skipif(not PREFAB_DIR.is_dir(), reason="piece prefabs are emitted by the Unity pack build")


@needs_sidecar
@needs_prefabs
def test_piece_prefab_roots_carry_the_mesh_to_world_scale() -> None:
    scale = sidecar()["meshToWorld"]["scale"]
    expected = re.compile(r"m_LocalScale: \{x: ([\d.eE+-]+), y: ([\d.eE+-]+), z: ([\d.eE+-]+)\}")
    for entry in sidecar()["pieces"]:
        prefab = PREFAB_DIR / f"{entry['asset']}.prefab"
        assert prefab.exists(), entry["asset"]
        matches = expected.findall(prefab.read_text())
        assert len(matches) == 1, entry["asset"]
        for value in matches[0]:
            assert float(value) == pytest.approx(scale), entry["asset"]
