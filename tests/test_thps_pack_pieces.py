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


def roof_sections() -> list[str]:
    return [entry["asset"] for entry in sidecar()["pieces"] if entry["module"] == "roof-panel"]


def test_manifest_keeps_the_pinned_version_and_warehouse_first() -> None:
    data = manifest()
    assert data["id"] == "thps"
    assert data["version"] == "2.0.21"
    assert data["kitVersion"] == "2"
    assert data["assets"][0] == "Warehouse"


@needs_sidecar
def test_manifest_lists_unique_canonical_assets_in_instance_order() -> None:
    expected = ["Warehouse"] + list(dict.fromkeys(piece["catalogAsset"] for piece in sidecar()["pieces"] if piece["catalogAsset"]))
    assert manifest()["assets"] == expected


@needs_sidecar
def test_sidecar_accounts_for_source_instances_and_added_sections() -> None:
    assets = [entry["asset"] for entry in sidecar()["pieces"]]
    source = [piece for piece in sidecar()["pieces"] if piece["kind"] == "source"]
    assert list(dict.fromkeys(piece["sourceId"] for piece in source)) == [piece.id for piece in inventory_pieces()]
    assert assets[len(source):] == ADDED_ASSETS + roof_sections()
    assert len(set(assets)) == len(assets)
    assert not any(asset.startswith("added-roof-quad-") for asset in manifest()["assets"])


@needs_sidecar
def test_source_entries_match_the_inventory_rows() -> None:
    for piece in inventory_pieces():
        entries = [entry for entry in sidecar()["pieces"] if entry.get("sourceId") == piece.id]
        assert entries
        assert all(entry["module"] == piece.module and entry["groups"] == list(piece.groups) for entry in entries)
        assert sorted(face for entry in entries for face in entry["faces"]) == sorted(piece.faces)


@needs_sidecar
def test_only_window_pieces_are_render_only() -> None:
    for entry in sidecar()["pieces"]:
        if entry["kind"] != "source":
            assert entry["collider"] is True, entry["asset"]
            continue
        row = next(piece for piece in inventory_pieces() if piece.id == entry["sourceId"])
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
    for asset in roof_sections():
        assert by_asset[asset]["source"] == "WarehouseRoof.Quads"
        assert by_asset[asset]["module"] == "roof-panel"


@needs_sidecar
def test_positions_are_the_recorded_pivots_in_world_space() -> None:
    for entry in sidecar()["pieces"]:
        position, pivot = entry["position"], entry["pivot"]
        for axis in range(3):
            assert position[axis] == pytest.approx(pivot[axis] * WAREHOUSE_SCALE + WAREHOUSE_POSITION[axis], abs=1e-3), entry["asset"]


@needs_sidecar
def test_placements_record_finite_rotations_and_positive_scales() -> None:
    riding = {"main-transition", "wall-transition", "outer-bank", "bank-end", "hip", "hip-apron", "roll-in", "kicker", "convex-tip"}
    for entry in sidecar()["pieces"]:
        assert all(math.isfinite(value) for value in entry["rotation"])
        assert all(math.isfinite(value) and value > 0 for value in entry["scale"])
        if entry["kind"] == "source" and entry["module"] in riding and entry["module"] != "kicker":
            assert -180.0 <= entry["yaw"] <= 180.0 and math.isfinite(entry["yaw"])


PREFAB_DIR = ROOT / "unity/pack-authoring/Assets/Thps"


def has_piece_prefabs(directory: Path) -> bool:
    return any(directory.glob("piece-*.prefab"))


needs_prefabs = pytest.mark.skipif(not has_piece_prefabs(PREFAB_DIR), reason="piece prefabs are emitted by the Unity pack build")


def test_stale_prefab_directory_with_only_the_warehouse_is_not_treated_as_built(tmp_path: Path) -> None:
    assert not has_piece_prefabs(tmp_path)
    (tmp_path / "Warehouse.prefab").write_text("")
    assert not has_piece_prefabs(tmp_path)
    (tmp_path / "piece-crane-hook.prefab").write_text("")
    assert has_piece_prefabs(tmp_path)


@needs_sidecar
@needs_prefabs
def test_piece_prefab_roots_carry_the_mesh_to_world_scale() -> None:
    scale = sidecar()["meshToWorld"]["scale"]
    expected = re.compile(r"m_LocalScale: \{x: ([\d.eE+-]+), y: ([\d.eE+-]+), z: ([\d.eE+-]+)\}")
    for entry in sidecar()["pieces"]:
        if not entry["catalogAsset"]:
            assert entry["module"] == "suppressed-post"
            continue
        prefab = PREFAB_DIR / f"{entry['catalogAsset']}.prefab"
        assert prefab.exists(), entry["asset"]
        matches = expected.findall(prefab.read_text())
        assert len(matches) == 1, entry["asset"]
        for value in matches[0]:
            assert float(value) == pytest.approx(scale), entry["asset"]


def test_palette_deduplicates_props_and_roof_sections_are_larger():
    pieces = sidecar()["pieces"]
    for module in ("sign", "prop"):
        instances = [p for p in pieces if p["module"] == module]
        assert len({p["catalogAsset"] for p in instances}) < len(instances), module
    roofs = [p for p in pieces if p["module"] == "roof-panel"]
    assert len(roofs) < 80
    assert len(manifest()["assets"]) < 300
    planks = [p for p in pieces if p["asset"].startswith("piece-board-")]
    assert len(planks) == 24
    assert len({p["catalogAsset"] for p in planks}) == 6
    kickers = [p for p in pieces if p["asset"] in {"piece-kicker-north-board", "piece-kicker-south-board"}]
    assert len({p["catalogAsset"] for p in kickers}) == 2


@needs_prefabs
def test_built_prefabs_contain_no_obsolete_kit_or_alias_entries():
    assert {path.stem for path in PREFAB_DIR.glob("*.prefab")} == set(manifest()["assets"])
    assert "aliases" not in manifest()
    assert not list(PREFAB_DIR.glob("added-roof-quad-*"))
