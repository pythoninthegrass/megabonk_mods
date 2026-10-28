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


def test_ring_cells_are_raised_flat_and_inner_cells_are_flat_below_the_warehouse_floor() -> None:
    edits = b.tile_edits()
    heights = {(payload(e)["x"], payload(e)["z"]): payload(e)["height"] for e in ops_of(edits, "tile.setHeight")}
    slopes = {(payload(e)["x"], payload(e)["z"]): payload(e)["direction"] for e in ops_of(edits, "tile.setSlope")}
    for cell in b.ring_cells():
        assert heights[cell] == b.WALL_LEVELS
    for cell in b.inner_cells():
        assert heights[cell] == b.INNER_LEVEL
    for cell in set(b.ring_cells()) | set(b.inner_cells()):
        assert slopes[cell] == b.SLOPE_NONE


def test_every_kept_cell_is_made_flat_before_slopes_are_applied() -> None:
    edits = b.tile_edits()
    slopes = {(payload(e)["x"], payload(e)["z"]): payload(e)["direction"] for e in ops_of(edits, "tile.setSlope")}
    for cell in set(b.ring_cells()) | set(b.inner_cells()):
        assert cell in slopes


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


def test_generated_player_spawn_cell_is_an_inner_cell() -> None:
    assert b.GENERATED_SPAWN_CELL in b.inner_cells()


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


def test_rail_placements_use_the_rail_catalog_ids_with_the_big_rail_at_a_block_local_position() -> None:
    rails = ops_of(b.rail_edits(), "object.place")
    ids = [payload(r)["catalogId"] for r in rails]
    assert ids == ["interactable/rail/1"] + ["interactable/rail/0"] * 4
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
    assert set(b.STRUCTURE_ASSETS) | {b.WAREHOUSE_ASSET} == set(manifest["assets"])
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


def test_build_level_disables_grass_so_it_does_not_grow_through_the_warehouse_floor() -> None:
    assert b.build_level()["noGrass"] is True


def test_build_level_places_no_hand_built_structures_inside_the_warehouse() -> None:
    placed = {payload(e)["catalogId"] for e in b.build_level()["edits"] if e["opType"] == "object.place"}
    assert placed.isdisjoint(f"bundle:{b.PACK_ID}/{a}" for a in b.STRUCTURE_ASSETS)


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
            assert c.y == 0, c.code
        else:
            assert inside == [c.stands_on], c.code
            assert c.y == b.surface_height(by_code[c.stands_on]), c.code


def test_surface_height_is_a_block_top_or_a_corridor_floor() -> None:
    by_code = {s.code: s for s in b.STRUCTURES}
    assert b.surface_height(by_code["M2"]) == 5.5
    assert b.surface_height(by_code["M5"]) == 13


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
        assert rot["x"] == b.UPRIGHT_PITCH, c.code
        assert rot["z"] == 0, c.code


def warehouse_place() -> dict:
    places = [payload(e) for e in b.warehouse_edits()]
    assert len(places) == 1
    return places[0]


def test_warehouse_scale_is_four_point_four_units_per_metre_at_eighteen_metres_per_unit() -> None:
    assert pytest.approx(4.4 * 18) == b.WAREHOUSE_SCALE


def test_warehouse_is_one_uniformly_scaled_thps_pack_placement() -> None:
    edits = b.warehouse_edits()
    assert [e["opType"] for e in edits] == ["object.place"]
    place = payload(edits[0])
    assert place["catalogId"] == f"bundle:{b.PACK_ID}/{b.WAREHOUSE_ASSET}"
    assert place["scale"] == {"x": b.WAREHOUSE_SCALE, "y": b.WAREHOUSE_SCALE, "z": b.WAREHOUSE_SCALE}
    assert place["rotation"] == {"x": 0.0, "y": 0.0, "z": 0.0}
    assert place["position"]["y"] == b.WAREHOUSE_LIFT


def test_inner_tiles_sit_below_the_warehouse_pit() -> None:
    assert b.INNER_LEVEL < 0


def test_warehouse_is_lifted_above_the_ground_level_tiles_but_below_the_player_spawn() -> None:
    assert 0 < b.WAREHOUSE_LIFT < 1.925


def test_warehouse_is_centred_in_the_inner_arena() -> None:
    place = payload(b.warehouse_edits()[0])
    cx, cz = b.local_to_world(b.INNER_X * b.TILE / 2, b.INNER_Z * b.TILE / 2)
    assert (place["position"]["x"], place["position"]["z"]) == (cx, cz)


def test_warehouse_footprint_fits_the_inner_arena() -> None:
    width, depth = b.warehouse_footprint()
    assert width <= b.INNER_X * b.TILE
    assert depth <= b.INNER_Z * b.TILE


def test_inner_arena_is_no_larger_than_the_warehouse_needs_by_a_tile() -> None:
    width, depth = b.warehouse_footprint()
    assert width > (b.INNER_X - 1) * b.TILE
    assert depth > (b.INNER_Z - 1) * b.TILE


def test_the_arena_and_its_ring_fit_the_grid() -> None:
    x0, z0 = b.INNER_ORIGIN
    assert x0 - 1 >= 0 and x0 + b.INNER_X + 1 <= b.GRID_SIZE
    assert z0 - 1 >= 0 and z0 + b.INNER_Z + 1 <= b.GRID_SIZE


def test_build_level_places_the_warehouse_after_the_clutter_removals() -> None:
    kinds = [(e["opType"], json.loads(e["payload"]).get("catalogId", "")) for e in b.build_level()["edits"]]
    warehouse = next(i for i, k in enumerate(kinds) if k[1] == f"bundle:{b.PACK_ID}/{b.WAREHOUSE_ASSET}")
    last_remove = max(i for i, k in enumerate(kinds) if k[0] == "object.remove")
    assert last_remove < warehouse


def test_pack_version_is_the_warehouse_release() -> None:
    assert b.PACK_VERSION == "2.0.9"


def test_player_starts_at_tonys_chosen_position() -> None:
    assert b.build_level()["playerStart"] == [109, 38, -120]


def boss_move() -> dict:
    return next(e for e in b.spawn_moves() if e["target"] == "gen:object:BossSpawner:0000")


def test_boss_spawner_sits_inside_the_hanging_box_above_the_main_half_pipe() -> None:
    position = payload(boss_move())["newTransform"]["position"]
    assert (position["x"], position["y"], position["z"]) == (170, 15.6, 27)


def test_boss_spawner_is_scaled_down_to_fit_inside_the_hanging_box() -> None:
    scale = payload(boss_move())["newTransform"]["scale"]
    assert scale == {"x": 0.4, "y": 0.4, "z": 0.4}


def test_boss_spawner_arch_faces_along_the_hanging_box() -> None:
    assert payload(boss_move())["newTransform"]["rotation"] == {"x": 0.0, "y": 90.0, "z": 0.0}


def test_boss_spawner_hides_the_pillar_mesh_and_its_collider() -> None:
    assert payload(boss_move())["hiddenChildren"] == ["BottomPiece", "Collider"]


def test_the_mesh_rail_gets_hidden_game_rails_along_its_run_and_its_bend() -> None:
    hidden = [payload(e) for e in b.rail_edits() if payload(e).get("hidden")]
    assert len(hidden) == len(b.MESH_RAILS) == 2
    for place, ((x, y, z), yaw, scale) in zip(hidden, b.MESH_RAILS, strict=True):
        assert place["catalogId"] == b.MESH_RAIL_CATALOG_ID
        assert (place["position"]["x"], place["position"]["y"], place["position"]["z"]) == (x, y, z)
        assert place["rotation"]["y"] == yaw
        assert place["scale"] == {"x": scale, "y": scale, "z": scale}


def test_the_hidden_rails_cover_the_whole_bar_from_the_run_through_the_bend() -> None:
    (run_pos, _, run_scale), (bend_pos, bend_yaw, bend_scale) = b.MESH_RAILS
    run_half = b.RAIL0_LENGTH * run_scale / 2
    assert run_pos[2] - run_half == pytest.approx(3.13, abs=0.1)
    assert run_pos[2] + run_half == pytest.approx(53.13, abs=0.1)
    half = b.RAIL0_LENGTH * bend_scale / 2
    direction = (math.cos(math.radians(bend_yaw)), -math.sin(math.radians(bend_yaw)))
    start = (bend_pos[0] - direction[0] * half, bend_pos[2] - direction[1] * half)
    end = (bend_pos[0] + direction[0] * half, bend_pos[2] + direction[1] * half)
    ends = sorted([start, end], key=lambda p: p[1])
    assert ends[0] == pytest.approx((75.1, 53.1), abs=0.3)
    assert ends[1] == pytest.approx((81.5, 60.6), abs=0.3)


def test_the_mesh_rail_bar_is_kept_and_stands_on_posts_in_the_pack() -> None:
    source = (Path(__file__).resolve().parent.parent / "unity" / "pack-authoring" / "Assets" / "Editor" / "ThpsPack.cs").read_text()
    assert "RailPosts" in source
    assert "IsMeshRailBar" not in source


def test_the_pack_opens_the_intact_secret_room_windows_by_position_only() -> None:
    source = (Path(__file__).resolve().parent.parent / "unity" / "pack-authoring" / "Assets" / "Editor" / "ThpsPack.cs").read_text()
    assert "PassThroughInRoomMaterials" in source
    assert "F2184063" in source


def test_the_pack_opens_the_start_slope_windows_by_position_only() -> None:
    source = (Path(__file__).resolve().parent.parent / "unity" / "pack-authoring" / "Assets" / "Editor" / "ThpsPack.cs").read_text()
    assert "StartSlopeWindowBounds" in source
