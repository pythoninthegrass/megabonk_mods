"""
Self-test for scripts/build_thps_level.py.
"""

import build_thps_level as b
import json
from pathlib import Path


def ops_of(edits: list[dict], op_type: str) -> list[dict]:
    return [e for e in edits if e["opType"] == op_type]


def payload(edit: dict) -> dict:
    return json.loads(edit["payload"])


def test_local_to_world_maps_block_corner_to_cell_corner() -> None:
    assert b.local_to_world(0, 0) == (20, -140)
    assert b.local_to_world(120, 160) == (140, 20)


def test_cell_of_local_returns_block_cell_index() -> None:
    assert b.cell_of_local(8, 34) == (0, 0)
    assert b.cell_of_local(98, 67) == (2, 1)


def test_tile_edits_remove_every_cell_outside_ring_and_inner() -> None:
    edits = b.tile_edits()
    removed = {(payload(e)["x"], payload(e)["z"]) for e in ops_of(edits, "tile.remove")}
    keep = set(b.ring_cells()) | set(b.inner_cells())
    assert len(removed) == b.GRID_SIZE**2 - len(keep)
    assert removed.isdisjoint(keep)


def test_ring_is_one_cell_wide_around_the_inner_block() -> None:
    ring = set(b.ring_cells())
    inner = set(b.inner_cells())
    assert len(inner) == b.INNER_X * b.INNER_Z
    assert ring.isdisjoint(inner)
    assert len(ring) == (b.INNER_X + 2) * (b.INNER_Z + 2) - len(inner)


def test_ring_cells_are_raised_flat_and_inner_cells_pinned() -> None:
    edits = b.tile_edits()
    heights = {(payload(e)["x"], payload(e)["z"]): payload(e)["height"] for e in ops_of(edits, "tile.setHeight")}
    for cell in b.ring_cells():
        assert heights[cell] == b.WALL_LEVELS
    for cell in b.inner_cells():
        assert cell in heights


def test_every_kept_cell_is_made_flat_before_slopes_are_applied() -> None:
    edits = b.tile_edits()
    slopes = {(payload(e)["x"], payload(e)["z"]): payload(e)["direction"] for e in ops_of(edits, "tile.setSlope")}
    for cell in set(b.ring_cells()) | set(b.inner_cells()):
        assert cell in slopes


def test_lane_cells_slope_north_up_to_the_raised_block() -> None:
    edits = b.tile_edits()
    heights = {(payload(e)["x"], payload(e)["z"]): payload(e)["height"] for e in ops_of(edits, "tile.setHeight")}
    slopes = {(payload(e)["x"], payload(e)["z"]): payload(e)["direction"] for e in ops_of(edits, "tile.setSlope")}
    x0, z0 = b.INNER_ORIGIN
    for dx in b.LANE_X:
        lane = (x0 + dx, z0 + b.LANE_Z)
        top = (x0 + dx, z0 + b.LANE_Z + 1)
        assert heights[lane] == 0
        assert slopes[lane] == b.SLOPE_NORTH
        assert heights[top] == 1
        assert slopes[top] == 0


def test_clutter_removals_skip_spawn_portal_boss_spawner_and_particles() -> None:
    ids = [e["target"] for e in b.clutter_removals()]
    for kept in b.KEPT_OBJECT_CATEGORIES:
        assert not any(i.startswith(f"gen:object:{kept}:") for i in ids)
    assert "gen:object:Tree0:0299" in ids
    assert "gen:object:Tree0:0300" not in ids
    assert "gen:tileObject:0038" in ids
    assert len(ids) == len(set(ids))


def test_clutter_removal_count_matches_the_seed_index() -> None:
    kept = sum(b.SEED_OBJECT_COUNTS[c] for c in b.KEPT_OBJECT_CATEGORIES)
    expected = sum(b.SEED_OBJECT_COUNTS.values()) - kept + b.SEED_TILE_OBJECTS
    assert len(b.clutter_removals()) == expected


def test_spawn_moves_only_relocate_the_boss_spawner_with_a_full_transform() -> None:
    moves = b.spawn_moves()
    assert [m["target"] for m in moves] == ["gen:object:BossSpawner:0000"]
    p = payload(moves[0])["newTransform"]
    assert set(p) == {"position", "rotation", "scale"}
    assert p["scale"] == {"x": 1.0, "y": 1.0, "z": 1.0}


def test_generated_player_spawn_cell_is_an_inner_flat_cell_at_ground_level() -> None:
    assert b.GENERATED_SPAWN_CELL in b.inner_cells()
    assert b.inner_height_and_slope(b.GENERATED_SPAWN_CELL) == (0, b.SLOPE_NONE)


def test_build_level_has_the_forest_stage_zero_header() -> None:
    level = b.build_level()
    assert level["map"] == 1
    assert level["stageIndex"] == 0
    assert level["tier"] == 0
    assert level["seed"] == 20261007
    assert level["schemaVersion"] == 2
    assert level["packs"] == {}


def test_build_level_orders_tiles_before_object_edits() -> None:
    kinds = [e["opType"] for e in b.build_level()["edits"]]
    last_tile = max(i for i, k in enumerate(kinds) if k.startswith("tile."))
    first_object = min(i for i, k in enumerate(kinds) if k.startswith("object."))
    assert last_tile < first_object


def test_write_level_round_trips_through_json(tmp_path: Path) -> None:
    out = tmp_path / "thps.mblevel.json"
    b.write_level(out)
    assert json.loads(out.read_text()) == b.build_level()


def test_rail_placements_use_the_rail_catalog_ids_at_block_local_positions() -> None:
    rails = ops_of(b.rail_edits(), "object.place")
    ids = [payload(r)["catalogId"] for r in rails]
    assert ids == ["interactable/rail/1", "interactable/rail/0", "interactable/rail/0"]
    big = payload(rails[0])
    wx, wz = b.local_to_world(*b.BIG_RAIL_LOCAL)
    assert (big["position"]["x"], big["position"]["z"]) == (wx, wz)
    assert big["rotation"]["y"] == b.BIG_RAIL_YAW
    assert 0 < big["scale"]["x"] <= 1


def test_rails_sit_inside_the_inner_arena() -> None:
    x0, z0 = b.INNER_ORIGIN
    for rail in ops_of(b.rail_edits(), "object.place"):
        pos = payload(rail)["position"]
        cx = round((pos["x"] - b.local_to_world(0, 0)[0]) / b.TILE - 0.5)
        cz = round((pos["z"] - b.local_to_world(0, 0)[1]) / b.TILE - 0.5)
        assert 0 <= cx < b.INNER_X
        assert 0 <= cz < b.INNER_Z


def test_build_level_includes_the_rails_after_the_clutter_removals() -> None:
    kinds = [(e["opType"], e["target"]) for e in b.build_level()["edits"]]
    first_place = min(i for i, k in enumerate(kinds) if k[0] == "object.place")
    last_remove = max(i for i, k in enumerate(kinds) if k[0] == "object.remove")
    assert last_remove < first_place
