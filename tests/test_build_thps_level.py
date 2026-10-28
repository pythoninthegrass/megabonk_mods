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
    expected = sum(b.SEED_OBJECT_COUNTS.values()) - kept + b.SEED_TILE_OBJECTS + sum(b.SEED_SCENERY_COUNTS.values())
    assert len(b.clutter_removals()) == expected


def test_clutter_removals_include_every_uncloned_scenery_root_but_not_the_fog_of_war_sphere() -> None:
    ids = {e["target"] for e in b.clutter_removals()}
    assert sum(b.SEED_SCENERY_COUNTS.values()) == 82
    assert "gen:scenery:Castle:0013" in ids
    assert "gen:scenery:Castle:0014" not in ids
    assert "gen:scenery:Crate (2):0009" in ids
    assert not any("FogOfWarSphere" in i for i in ids)


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
    assert level["schemaVersion"] == 3
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


def test_the_only_rails_are_the_hidden_game_rails_along_the_mesh_bars() -> None:
    rails = ops_of(b.rail_edits(), "object.place")
    assert len(rails) == len(b.MESH_RAILS)
    for rail in rails:
        assert payload(rail)["catalogId"] == b.MESH_RAIL_CATALOG_ID
        assert payload(rail)["hidden"] is True


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


def test_build_level_disables_grass_so_it_does_not_grow_through_the_warehouse_floor() -> None:
    assert b.build_level()["noGrass"] is True


def test_build_level_raises_the_slope_limit_so_the_player_can_ride_the_half_pipes() -> None:
    angle = b.build_level()["maxSlopeAngle"]
    assert angle == b.MAX_SLOPE_ANGLE
    assert angle > 45


def test_build_level_names_the_pack_clip_as_its_music() -> None:
    assert b.build_level()["music"] == "bundle:thps/04_Superman"


def test_the_radio_is_one_boombox_placed_in_the_arena_beside_the_player_spawn() -> None:
    places = [payload(e) for e in b.build_level()["edits"] if e["opType"] == "object.place" and payload(e)["catalogId"] == "interactable/boombox"]
    assert len(places) == 1
    pos = places[0]["position"]
    assert "hidden" not in places[0]
    assert max(abs(pos["x"] - b.PLAYER_START[0]), abs(pos["z"] - b.PLAYER_START[2])) <= b.RADIO_REACH


def test_the_pack_manifest_lists_only_the_warehouse_at_the_pack_version() -> None:
    manifest = json.loads(Path(b.MANIFEST_PATH).read_text())
    assert manifest["assets"] == [b.WAREHOUSE_ASSET]
    assert manifest["id"] == b.PACK_ID
    assert manifest["version"] == b.PACK_VERSION


def test_the_warehouse_is_the_only_pack_asset_the_level_places() -> None:
    placed = {payload(e)["catalogId"] for e in b.build_level()["edits"] if e["opType"] == "object.place"}
    assert {c for c in placed if c.startswith("bundle:")} == {f"bundle:{b.PACK_ID}/{b.WAREHOUSE_ASSET}"}


needs_extract = pytest.mark.skipif(
    not (b.NODES_PATH.exists() and b.OBJ_PATH.exists()), reason="needs the extraction under .tools/thps1/warehouse"
)

LETTER_SHRINES = {
    "S": "forest/shrines/0",
    "K": "forest/shrines/1",
    "A": "forest/shrines/2",
    "T": "forest/shrines/3",
    "E": "forest/shrines/4",
}


def collectible_places() -> list[dict]:
    return [payload(e) for e in ops_of(b.collectible_edits(), "object.place")]


def source_nodes() -> list[dict]:
    return json.loads(b.NODES_PATH.read_text())["nodes"]


def anchored() -> list[b.Collectible]:
    return [c for c in b.collectibles() if not c.overridden]


@needs_extract
def test_collectibles_cover_the_spec_with_the_confirmed_item_mapping() -> None:
    ids = [c.catalog_id for c in b.collectibles()]
    assert len(ids) == 14
    assert ids.count("interactable/chest") == 5
    assert ids.count("interactable/chestFree") == 4
    assert sorted(i for i in ids if i.startswith("forest/shrines/")) == [f"forest/shrines/{n}" for n in range(5)]
    assert len({c.code for c in b.collectibles()}) == 14


@needs_extract
def test_collectibles_come_from_the_extracted_nodes_with_the_confirmed_mapping() -> None:
    nodes = {n["node"]: n for n in source_nodes()}
    for c in b.collectibles():
        node = nodes[c.node]
        if node["type"] == "letter":
            assert c.catalog_id == LETTER_SHRINES[node["name"]], c.code
        elif node["type"] == "box_pile":
            assert c.catalog_id == "interactable/chest", c.code
        else:
            assert node["type"] in ("tape", "bonus") and node["name"] in ("tape", "100"), c.code
            assert c.catalog_id == "interactable/chestFree", c.code
    assert {n["node"] for n in source_nodes() if n["type"] in ("letter", "box_pile", "tape")} <= {
        c.node for c in b.collectibles()
    }
    assert len({c.node for c in b.collectibles()}) == 14


@needs_extract
def test_each_collectible_stays_within_the_stated_distance_of_its_source_node() -> None:
    nodes = {n["node"]: n for n in source_nodes()}
    for c in anchored():
        nx, _, nz = b.node_world(nodes[c.node]["position"])
        bx, _, bz = b.base_point(c)
        assert math.hypot(bx - nx, bz - nz) <= b.MAX_NODE_SHIFT, c.code


@needs_extract
def test_every_collectible_base_is_on_the_surface_below_it() -> None:
    triangles = b.warehouse_triangles()
    for c in anchored():
        bx, by, bz = b.base_point(c)
        hit = b.ws.drop(triangles, bx, by + 1.0, bz)
        assert hit is not None, c.code
        assert abs(by - hit.y) <= 0.1, c.code


@needs_extract
def test_every_collectible_is_tilted_onto_the_surface_normal() -> None:
    triangles = b.warehouse_triangles()
    for c in anchored():
        bx, by, bz = b.base_point(c)
        assert c.normal == pytest.approx(b.ws.drop(triangles, bx, by + 1.0, bz).normal, abs=1e-6), c.code
        assert c.normal[1] >= math.cos(math.radians(b.MAX_SURFACE_TILT)), c.code


@needs_extract
def test_no_collectible_overlaps_collider_triangles_other_than_the_one_it_stands_on() -> None:
    triangles = b.warehouse_triangles()
    for c in anchored():
        bx, by, bz = b.base_point(c)
        support = b.ws.drop(triangles, bx, by + 1.0, bz)
        assert set(b.item_overlaps(c, triangles)) <= {support.index}, c.code


@needs_extract
def test_collectible_edits_place_each_item_at_its_pivot_with_the_surface_tilt() -> None:
    places = collectible_places()
    assert [p["catalogId"] for p in places] == [c.catalog_id for c in b.collectibles()]
    for c, p in zip(b.collectibles(), places, strict=True):
        assert (p["position"]["x"], p["position"]["y"], p["position"]["z"]) == (c.x, c.y, c.z), c.code
        assert (p["rotation"]["x"], p["rotation"]["y"], p["rotation"]["z"]) == pytest.approx(c.euler), c.code


@needs_extract
def test_overrides_replace_the_anchored_transform_of_the_items_they_name() -> None:
    overrides = b.load_overrides()
    assert overrides
    by_code = {c.code: c for c in b.collectibles()}
    assert set(overrides) <= set(by_code)
    for code, override in overrides.items():
        c = by_code[code]
        assert c.overridden
        assert [c.x, c.y, c.z] == override["position"]
        assert list(c.euler) == override["rotation"]
    assert {c.code for c in b.collectibles() if c.overridden} == set(overrides)


@needs_extract
def test_an_override_for_an_unknown_item_is_refused(tmp_path, monkeypatch) -> None:
    path = tmp_path / "overrides.json"
    path.write_text(json.dumps({"nope": {"position": [0, 0, 0], "rotation": [270, 0, 0]}}))
    monkeypatch.setattr(b, "OVERRIDES_PATH", path)
    b.collectibles.cache_clear()
    try:
        with pytest.raises(ValueError, match="nope"):
            b.collectibles()
    finally:
        monkeypatch.undo()
        b.collectibles.cache_clear()


@needs_extract
def test_collectibles_stay_inside_the_arena_and_clear_of_the_player_spawn() -> None:
    sx, sz = b.local_to_world(*b.PLAYER_SPAWN_LOCAL)
    x0, z0 = b.local_to_world(0, 0)
    for c in b.collectibles():
        assert x0 <= c.x <= x0 + b.INNER_X * b.TILE and z0 <= c.z <= z0 + b.INNER_Z * b.TILE, c.code
        assert max(abs(c.x - sx), abs(c.z - sz)) >= b.SPAWN_CLEARANCE, c.code


@needs_extract
def test_build_level_includes_collectibles_after_the_clutter_removals() -> None:
    edits = b.build_level()["edits"]
    ids = {c.catalog_id for c in b.collectibles()}
    placed = [i for i, e in enumerate(edits) if e["opType"] == "object.place" and payload(e)["catalogId"] in ids]
    assert len(placed) == len(b.collectibles())
    assert max(i for i, e in enumerate(edits) if e["opType"] == "object.remove") < min(placed)


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
    assert b.PACK_VERSION == "2.0.21"


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
    assert len(hidden) == len(b.MESH_RAILS) == 4
    for place, ((x, y, z), yaw, scale) in zip(hidden, b.MESH_RAILS, strict=True):
        assert place["catalogId"] == b.MESH_RAIL_CATALOG_ID
        assert (place["position"]["x"], place["position"]["y"], place["position"]["z"]) == (x, y, z)
        assert place["rotation"]["y"] == yaw
        assert place["scale"] == {"x": scale, "y": scale, "z": scale}


def test_the_hidden_rails_cover_the_whole_bar_from_the_run_through_the_bend() -> None:
    (run_pos, _, run_scale), (bend_pos, bend_yaw, bend_scale), *_ = b.MESH_RAILS
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


def rail_ends(rail: tuple) -> list[tuple[float, float]]:
    (x, _, z), yaw, scale = rail
    half = b.RAIL0_LENGTH * scale / 2
    direction = (math.cos(math.radians(yaw)), -math.sin(math.radians(yaw)))
    return sorted([(x - direction[0] * half, z - direction[1] * half), (x + direction[0] * half, z + direction[1] * half)])


def test_the_hidden_rail_over_the_bend_sits_at_the_bar_height() -> None:
    rail = b.MESH_RAILS[1]
    assert rail[0][1] == pytest.approx(3.3 - b.RAIL0_BAR_HEIGHT * rail[2], abs=0.05)


def test_the_hidden_rail_over_the_wall_rod_spans_the_rod_at_its_height() -> None:
    rail = b.MESH_RAILS[2]
    assert [c for end in rail_ends(rail) for c in end] == pytest.approx([116.28, 120.84, 143.0, 120.84], abs=0.3)
    assert rail[0][1] == pytest.approx(27.43 - b.RAIL0_BAR_HEIGHT * rail[2], abs=0.05)


def test_the_hidden_rail_over_the_deck_rail_spans_the_bar_at_its_height() -> None:
    rail = b.MESH_RAILS[3]
    assert [c for end in rail_ends(rail) for c in end] == pytest.approx([175.66, 47.92, 175.66, 74.67], abs=0.3)
    assert rail[0][1] == pytest.approx(8.43 - b.RAIL0_BAR_HEIGHT * rail[2], abs=0.05)


def test_the_pack_removes_the_floating_rail_leftovers_and_posts_the_deck_rail() -> None:
    source = (
        Path(__file__).resolve().parent.parent / "unity" / "pack-authoring" / "Assets" / "Editor" / "ThpsPack.cs"
    ).read_text()
    assert "RailLeftoverBounds" in source
    assert "A53322CF" in source


def test_the_mesh_rail_bar_is_kept_and_stands_on_posts_in_the_pack() -> None:
    source = (
        Path(__file__).resolve().parent.parent / "unity" / "pack-authoring" / "Assets" / "Editor" / "ThpsPack.cs"
    ).read_text()
    assert "RailPosts" in source
    assert "IsMeshRailBar" not in source


def test_the_pack_opens_the_intact_secret_room_windows_by_position_only() -> None:
    source = (
        Path(__file__).resolve().parent.parent / "unity" / "pack-authoring" / "Assets" / "Editor" / "ThpsPack.cs"
    ).read_text()
    assert "PassThroughInRoomMaterials" in source
    assert "F2184063" in source


def test_the_pack_opens_the_start_slope_windows_by_position_only() -> None:
    source = (
        Path(__file__).resolve().parent.parent / "unity" / "pack-authoring" / "Assets" / "Editor" / "ThpsPack.cs"
    ).read_text()
    assert "StartSlopeWindowBounds" in source
