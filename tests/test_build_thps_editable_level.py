"""The editable Warehouse is a complete, nonduplicated assembly of the kit."""

import build_thps_editable_level as kit
import build_thps_level as legacy
import copy
import json
import pytest


def placements(edits):
    return [json.loads(op["payload"]) for op in edits if op["opType"] == "object.place"]


def test_assembly_covers_geometry_once_and_snapshots_paths():
    pieces, defaults = kit.read_inputs()
    roots = placements(kit.piece_edits(pieces, defaults))
    children = [child for root in roots for child in root.get("attachments", [])]
    geometry = [root["catalogId"].split("/", 1)[1] for root in roots]
    geometry += [child["catalogId"].split("/", 1)[1] for child in children if child["catalogId"].startswith("bundle:thps/")]
    expected = [piece["catalogAsset"] for piece in pieces["pieces"] if piece["module"] != "suppressed-post"]
    assert sorted(geometry) == sorted(expected)
    assert len(roots) < 600
    assert len(children) == 58
    assert sum(child["catalogId"] == "interactable/rail/0" for child in children) == 41
    assert not any(asset.startswith("added-roof-quad-") for asset in geometry)


def test_recorded_transforms_and_monotonic_reserved_ids():
    pieces, defaults = kit.read_inputs()
    supports = {child["sourceInstance"] for children in defaults["instances"].values() for child in children if child["catalogId"].startswith("bundle:thps/")}
    entries = [piece for piece in pieces["pieces"] if piece["module"] != "suppressed-post" and piece["asset"] not in supports]
    next_id = 0
    for root, piece in zip(placements(kit.piece_edits(pieces, defaults)), entries, strict=True):
        assert root["catalogId"] == f"bundle:thps/{piece['catalogAsset']}"
        assert root["placementId"] == next_id
        assert list(root["position"].values()) == piece["position"]
        assert list(root["rotation"].values()) == piece["rotation"]
        assert list(root["scale"].values()) == piece["scale"]
        next_id += 1 + len(root.get("attachments", []))
    assert next_id == len(entries) + 58


@pytest.mark.parametrize("failure", ["duplicate", "missing_owner", "missing_support", "double_owner", "schema", "nonfinite", "child_scale", "suppressed_owner"])
def test_invalid_sidecars_fail_explicitly(failure):
    pieces, defaults = copy.deepcopy(kit.read_inputs())
    assets = defaults["instances"]
    if failure == "duplicate":
        pieces["pieces"].append(pieces["pieces"][0])
    elif failure == "missing_owner":
        assets["not-a-piece"] = []
    elif failure == "missing_support":
        assets["piece-room-floor"][0]["catalogId"] = "bundle:thps/missing"
    elif failure == "double_owner":
        assets["piece-room-roof"].append(assets["piece-room-floor"][0])
    elif failure == "schema":
        pieces["schema"] = "unknown"
    elif failure == "child_scale":
        assets["piece-room-floor"][0]["localTransform"]["scale"]["x"] = 0
    elif failure == "suppressed_owner":
        assets["piece-post-remnant-01"] = assets.pop("piece-room-floor")
    else:
        pieces["pieces"][0]["position"][0] = float("nan")
    with pytest.raises(ValueError):
        kit.piece_edits(pieces, defaults)


def test_level_keeps_legacy_arena_without_monolith_or_duplicate_rails():
    level = kit.build_level()
    shipped = legacy.build_level()
    for key, value in shipped.items():
        if key not in {"edits", "title"}:
            assert level[key] == value, key
    assert level["packKitVersions"] == {"thps": "2"}
    placed = placements(level["edits"])
    assert not any(p["catalogId"] in {"bundle:thps/Warehouse", "interactable/rail/0"} for p in placed)
    assert level["edits"][-15:] == legacy.radio_edits() + legacy.collectible_edits()
    assert level == kit.build_level()


def test_level_is_from_scratch_with_no_tile_ops_or_generated_targets():
    level = kit.build_level()
    assert level["baseline"] == "none"
    assert level["schemaVersion"] == 4
    assert level["spawn"] == legacy.build_level()["spawn"]
    assert level["bossSpawner"] == legacy.boss_spawner()
    assert level["bossRedirect"] is True
    assert not [op for op in level["edits"] if op["opType"].startswith("tile.")]
    assert not [op for op in level["edits"] if op["target"].startswith("gen:")]
    assert {op["opType"] for op in level["edits"]} == {"object.place"}


def test_writer_refuses_shipped_path_and_is_reproducible(tmp_path):
    with pytest.raises(ValueError, match="shipped"):
        kit.write_level(kit.ROOT / "levels/thps.mblevel.json")
    output = tmp_path / "editable.json"
    kit.write_level(output)
    first = output.read_bytes()
    kit.write_level(output)
    assert output.read_bytes() == first
    assert json.loads(first) == kit.build_level()
