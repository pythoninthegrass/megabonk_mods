"""
Self-test for scripts/build_thps_level.py.
"""

import build_thps_level as b
import json
import math
import pytest
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
    assert level["packs"] == {b.PACK_ID: b.PACK_VERSION}


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


def structure_places() -> list[dict]:
    return [payload(e) for e in ops_of(b.structure_edits(), "object.place")]


def test_every_structure_is_a_thps_pack_asset_listed_in_the_manifest() -> None:
    manifest = json.loads(Path(b.MANIFEST_PATH).read_text())
    assets = {p["catalogId"] for p in structure_places()}
    assert assets == {f"bundle:{b.PACK_ID}/{a}" for a in b.STRUCTURE_ASSETS}
    assert set(b.STRUCTURE_ASSETS) == set(manifest["assets"])
    assert manifest["id"] == b.PACK_ID
    assert manifest["version"] == b.PACK_VERSION


def test_structures_cover_every_spec_feature_that_needs_a_new_asset() -> None:
    codes = {s.code for s in b.STRUCTURES}
    assert {"M1", "M2", "M3", "M4a", "M4b", "M5", "M6", "M7", "M8", "M9", "M9b", "M10", "M11", "M12a", "M12b"} <= codes
    assert len(structure_places()) == len(b.STRUCTURES)


def test_half_pipe_is_two_opposed_quarter_pipes_with_a_flat_between() -> None:
    by_code = {s.code: s for s in b.STRUCTURES}
    a, c = by_code["M4a"], by_code["M4b"]
    assert a.asset == c.asset == "QuarterPipe"
    assert (a.yaw - c.yaw) % 360 == 180
    assert a.x == c.x
    near, far = sorted((a, c), key=lambda s: s.z)
    assert far.z - near.z > near.depth / 2 + far.depth / 2


def test_structures_stay_inside_the_inner_arena() -> None:
    for s in b.STRUCTURES:
        x0, x1, z0, z1 = b.footprint(s)
        assert x0 >= 0 and x1 <= b.INNER_X * b.TILE, s.code
        assert z0 >= 0 and z1 <= b.INNER_Z * b.TILE, s.code


def test_structures_leave_the_player_spawn_area_clear() -> None:
    sx, sz = b.PLAYER_SPAWN_LOCAL
    for s in b.STRUCTURES:
        x0, x1, z0, z1 = b.footprint(s)
        assert not (
            x0 - b.SPAWN_CLEARANCE < sx < x1 + b.SPAWN_CLEARANCE and z0 - b.SPAWN_CLEARANCE < sz < z1 + b.SPAWN_CLEARANCE
        ), s.code


def test_ramp_end_slopes_stay_under_the_player_max_slope_angle() -> None:
    ramps = [s for s in b.STRUCTURES if s.asset in ("QuarterPipe", "Kicker")]
    assert ramps
    for s in ramps:
        assert b.end_slope_degrees(s) <= b.MAX_RAMP_SLOPE_DEGREES, s.code
    assert b.MAX_RAMP_SLOPE_DEGREES < 45


def test_structures_that_hold_items_or_rails_are_no_taller_than_the_jump_apex() -> None:
    for s in b.STRUCTURES:
        if s.asset == "Block":
            assert s.rise <= b.PLAYER_JUMP_APEX, s.code


def test_structures_are_placed_after_the_clutter_removals() -> None:
    kinds = [(e["opType"], e["target"]) for e in b.build_level()["edits"]]
    structures = {payload(e)["catalogId"] for e in b.structure_edits()}
    ids = [
        (i, json.loads(e["payload"]).get("catalogId"))
        for i, e in enumerate(b.build_level()["edits"])
        if e["opType"] == "object.place"
    ]
    first_structure = min(i for i, cid in ids if cid in structures)
    last_remove = max(i for i, k in enumerate(kinds) if k[0] == "object.remove")
    assert last_remove < first_structure


def test_ledge_and_high_rails_sit_on_the_structures_they_belong_to() -> None:
    by_code = {s.code: s for s in b.STRUCTURES}
    assert by_code["M1"].rise == b.HIGH_RAIL_HEIGHT
    assert by_code["M2"].rise == b.LEDGE_RAIL_HEIGHT
    rails = ops_of(b.rail_edits(), "object.place")
    assert payload(rails[1])["position"]["y"] == by_code["M2"].rise
    assert payload(rails[2])["position"]["y"] == by_code["M1"].rise


def test_structure_placements_use_non_uniform_scale_of_width_rise_depth() -> None:
    by_code = {s.code: s for s in b.STRUCTURES}
    m1 = by_code["M1"]
    place = next(p for p in structure_places() if p["scale"]["y"] == m1.rise and p["scale"]["x"] == m1.width)
    assert place["scale"]["z"] == m1.depth
    assert place["rotation"]["y"] == m1.yaw


def collectible_places() -> list[dict]:
    return [payload(e) for e in ops_of(b.collectible_edits(), "object.place")]


def test_collectibles_cover_the_spec_with_the_confirmed_item_mapping() -> None:
    ids = [c.catalog_id for c in b.COLLECTIBLES]
    assert len(ids) == 14
    assert ids.count("interactable/chest") == 5
    assert ids.count("interactable/chestFree") == 4
    assert sorted(i for i in ids if i.startswith("forest/shrines/")) == [f"forest/shrines/{n}" for n in range(5)]
    assert len({c.code for c in b.COLLECTIBLES}) == 14


def test_collectible_edits_place_each_item_at_its_world_position() -> None:
    places = collectible_places()
    assert [p["catalogId"] for p in places] == [c.catalog_id for c in b.COLLECTIBLES]
    for c, p in zip(b.COLLECTIBLES, places, strict=True):
        wx, wz = b.local_to_world(c.x, c.z)
        assert (p["position"]["x"], p["position"]["y"], p["position"]["z"]) == (wx, c.y, wz), c.code


def test_collectibles_stay_inside_the_arena_and_clear_of_the_player_spawn() -> None:
    sx, sz = b.PLAYER_SPAWN_LOCAL
    for c in b.COLLECTIBLES:
        assert 0 <= c.x <= b.INNER_X * b.TILE and 0 <= c.z <= b.INNER_Z * b.TILE, c.code
        assert max(abs(c.x - sx), abs(c.z - sz)) >= b.SPAWN_CLEARANCE, c.code


def test_collectibles_inside_a_structure_footprint_stand_on_its_surface() -> None:
    by_code = {s.code: s for s in b.STRUCTURES}
    for c in b.COLLECTIBLES:
        inside = []
        for s in b.STRUCTURES:
            x0, x1, z0, z1 = b.footprint(s)
            if x0 <= c.x <= x1 and z0 <= c.z <= z1:
                inside.append(s.code)
        if c.stands_on is None:
            assert not inside, c.code
            assert c.y == b.ground_height(c.z, c.x), c.code
        else:
            assert inside == [c.stands_on], c.code
            assert c.y == b.surface_height(by_code[c.stands_on]), c.code


def test_surface_height_is_a_block_top_or_a_corridor_floor() -> None:
    by_code = {s.code: s for s in b.STRUCTURES}
    assert b.surface_height(by_code["M2"]) == 5.5
    assert b.surface_height(by_code["M5"]) == 13


def test_ground_height_follows_the_north_lanes_and_is_zero_elsewhere() -> None:
    assert b.ground_height(40, 20) == 0
    assert b.ground_height(80, 20) == 0
    assert b.ground_height(100, 20) == 10
    assert b.ground_height(100, 100) == 0


def test_collectibles_on_structures_are_reachable_by_a_jump_or_ramp_or_listed_as_trick_only() -> None:
    by_code = {s.code: s for s in b.STRUCTURES}
    for c in b.COLLECTIBLES:
        if c.stands_on and by_code[c.stands_on].asset == "Block":
            assert c.y <= b.PLAYER_JUMP_APEX, c.code


def test_build_level_includes_collectibles_after_the_clutter_removals() -> None:
    edits = b.build_level()["edits"]
    ids = {c.catalog_id for c in b.COLLECTIBLES}
    placed = [i for i, e in enumerate(edits) if e["opType"] == "object.place" and payload(e)["catalogId"] in ids]
    assert len(placed) == len(b.COLLECTIBLES)
    assert max(i for i, e in enumerate(edits) if e["opType"] == "object.remove") < min(placed)


def test_collectibles_are_rotated_upright_because_the_prefabs_lie_on_their_side_at_zero() -> None:
    for c, p in zip(b.COLLECTIBLES, collectible_places(), strict=True):
        rot = p["rotation"]
        on_lane = b.lane_slope_degrees(c.z, c.x) > 0
        expected_pitch = b.UPRIGHT_PITCH - b.lane_slope_degrees(c.z, c.x)
        assert rot["x"] == pytest.approx(expected_pitch), c.code
        assert rot["z"] == 0, c.code
        assert on_lane == (c.code in {"R5", "100N", "100E"}), c.code


def test_lane_slope_is_the_lane_rise_over_the_tile_width() -> None:
    assert b.lane_slope_degrees(100, 20) == pytest.approx(math.degrees(math.atan(b.HEIGHT_STEP / b.TILE)))
    assert b.lane_slope_degrees(100, 100) == 0
    assert b.lane_slope_degrees(40, 20) == 0
