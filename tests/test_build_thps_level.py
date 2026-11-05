"""
Self-test for scripts/build_thps_level.py.
"""

import build_thps_level as b
import json
import math
import pytest
import warehouse_surface as ws
from pathlib import Path

# The handoff searches this far from a rail end (RailHandoff.SearchRadius), so a rail shorter than it has several neighbours in reach.
MIN_COPING_LIP = 3.5

needs_extract = pytest.mark.skipif(
    not (b.NODES_PATH.exists() and b.OBJ_PATH.exists()), reason="needs the extraction under .tools/thps1/warehouse"
)



def ops_of(edits: list[dict], op_type: str) -> list[dict]:
    return [e for e in edits if e["opType"] == op_type]


def payload(edit: dict) -> dict:
    return json.loads(edit["payload"])


@needs_extract
def test_build_level_is_a_from_scratch_file_with_a_spawn_and_a_boss_spawner() -> None:
    level = b.build_level()
    assert level["schemaVersion"] == 4
    assert level["baseline"] == "none"
    assert level["packs"] == {b.PACK_ID: b.PACK_VERSION}
    assert (level["map"], level["stageIndex"], level["tier"]) == (1, 0, 0)
    assert level["spawn"] == {"position": b.PLAYER_START, "rotation": [0.0, 0.0, 0.0]}
    assert level["bossSpawner"] == b.boss_spawner()
    assert "playerStart" not in level
    assert "seed" not in level


@needs_extract
def test_build_level_keeps_the_boss_redirect_on_because_the_portal_stands_in_a_closed_room() -> None:
    assert b.build_level()["bossRedirect"] is True


@needs_extract
def test_build_level_has_no_tile_ops_and_no_generated_targets() -> None:
    edits = b.build_level()["edits"]
    assert not [e for e in edits if e["opType"].startswith("tile.")]
    assert not [e for e in edits if e["target"].startswith("gen:")]
    assert {e["opType"] for e in edits} == {"object.place"}


def test_the_game_keeps_the_authored_kill_floor_because_the_floor_tile_puts_its_catch_floor_far_enough_below() -> None:
    # The game derives the catch floor one level under the lowest tile and raises the kill floor to at least 8 above it.
    catch_floor = (b.INNER_LEVEL - 1) * b.HEIGHT_STEP
    assert catch_floor + 8 <= b.KILL_FLOOR_Y


def test_the_authored_grid_is_one_hidden_floor_tile_under_the_mesh_on_the_stock_size_grid() -> None:
    # The game derives its catch floor from the tiles, so a level with none arms its kill floor at int.MaxValue and
    # kills the player on spawn. The grid keeps the stock size so the tile lands where the old kept tile did.
    grid = b.authored_grid()
    assert (grid["width"], grid["depth"]) == (b.GRID_SIZE, b.GRID_SIZE)
    [cell] = grid["cells"]
    x0, z0 = b.INNER_ORIGIN
    assert x0 <= cell["x"] < x0 + b.INNER_X and z0 <= cell["z"] < z0 + b.INNER_Z
    assert cell["height"] == b.INNER_LEVEL < 0
    assert "slope" not in cell


@needs_extract
def test_the_level_authors_the_kill_floor_it_always_had() -> None:
    assert b.build_level()["killFloorY"] == b.KILL_FLOOR_Y == -35.0


@needs_extract
def test_the_level_keeps_the_mesh_object_and_the_radio_ahead_of_the_collectibles() -> None:
    places = [payload(e)["catalogId"] for e in b.build_level()["edits"]]
    assert places.index(f"bundle:{b.PACK_ID}/{b.WAREHOUSE_ASSET}") < places.index("interactable/boombox") < places.index("interactable/chest")


def test_local_to_world_maps_block_corner_to_cell_corner() -> None:
    assert b.local_to_world(0, 0) == (20, -140)
    assert b.local_to_world(120, 160) == (140, 20)


def test_cell_of_local_returns_block_cell_index() -> None:
    assert b.cell_of_local(8, 34) == (0, 0)
    assert b.cell_of_local(98, 67) == (2, 1)



































@needs_extract
def test_write_level_round_trips_through_json(tmp_path: Path) -> None:
    out = tmp_path / "thps.mblevel.json"
    b.write_level(out)
    assert json.loads(out.read_text()) == b.build_level()


def test_the_only_rails_are_the_hidden_game_rails_along_the_mesh_bars() -> None:
    rails = ops_of(b.rail_edits(), "object.place")
    assert len(rails) == len(b.MESH_RAILS) + len(b.COPING_RAILS)
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





@needs_extract
def test_build_level_disables_grass_so_it_does_not_grow_through_the_warehouse_floor() -> None:
    assert b.build_level()["noGrass"] is True


@needs_extract
def test_build_level_raises_the_slope_limit_so_the_player_can_ride_the_half_pipes() -> None:
    angle = b.build_level()["maxSlopeAngle"]
    assert angle == b.MAX_SLOPE_ANGLE
    assert angle > 45


@needs_extract
def test_build_level_names_the_pack_clip_as_its_music() -> None:
    assert b.build_level()["music"] == "bundle:thps/04_Superman"


@needs_extract
def test_build_level_is_titled_warehouse_on_tier_one() -> None:
    level = b.build_level()
    assert level["title"] == "Warehouse"
    assert level["description"] == "I'm trying to sleep"
    assert level["tier"] == 0


@needs_extract
def test_build_level_has_a_map_selection_description_apart_from_the_banner() -> None:
    level = b.build_level()
    assert level["mapDescription"] == "A warehouse built for grinding"
    assert level["mapDescription"] != level["description"]


@needs_extract
def test_build_level_allows_only_calcium_and_tony_mczoom() -> None:
    assert b.build_level()["allowedCharacters"] == ["calcium", "tonymczoom"]


@needs_extract
def test_the_radio_is_one_boombox_placed_in_the_arena_beside_the_player_spawn() -> None:
    places = [payload(e) for e in b.build_level()["edits"] if e["opType"] == "object.place" and payload(e)["catalogId"] == "interactable/boombox"]
    assert len(places) == 1
    pos = places[0]["position"]
    assert "hidden" not in places[0]
    assert max(abs(pos["x"] - b.PLAYER_START[0]), abs(pos["z"] - b.PLAYER_START[2])) <= b.RADIO_REACH


def test_the_radio_stands_against_the_back_wall_clear_of_the_start_lip() -> None:
    lip_z = b.START_PIPE_LIPS[0][0][2]
    platform_back_z = -124.13
    assert b.RADIO_POSITION[2] <= lip_z - 2.5
    assert b.RADIO_POSITION[2] >= platform_back_z


def test_the_pack_manifest_leads_with_the_warehouse_at_the_pack_version() -> None:
    manifest = json.loads(Path(b.MANIFEST_PATH).read_text())
    assert manifest["assets"][0] == b.WAREHOUSE_ASSET
    assert manifest["id"] == b.PACK_ID
    assert manifest["version"] == b.PACK_VERSION


@needs_extract
def test_the_warehouse_is_the_only_pack_asset_the_level_places() -> None:
    placed = {payload(e)["catalogId"] for e in b.build_level()["edits"] if e["opType"] == "object.place"}
    assert {c for c in placed if c.startswith("bundle:")} == {f"bundle:{b.PACK_ID}/{b.WAREHOUSE_ASSET}"}


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








def test_pack_version_is_the_warehouse_release() -> None:
    assert b.PACK_VERSION == "2.0.21"





def boss_spawner() -> dict:
    return b.boss_spawner()


# Between the box's interior floor (15.64) and the underside of its roof (25.42), so a drop from here finds the floor
# the portal stands on rather than the top of the box.
PORTAL_ROOF_PROBE_Y = 24.0


def test_boss_portal_stands_on_the_floor_inside_the_glass_box() -> None:
    position = dict(zip("xyz", boss_spawner()["position"], strict=True))
    x0, x1, z0, z1 = b.BOSS_PORTAL_FOOTPRINT
    assert (position["x"], position["z"]) == b.local_to_world(*b.BOSS_SPAWN_LOCAL)
    assert b.BOSS_PORTAL_INTERIOR_FLOOR_Y - 0.1 <= position["y"] < b.BOSS_PORTAL_UNDERSIDE_Y, (
        "the portal must stand inside the box, on its floor, not on the roof"
    )
    assert x0 + 1.0 <= position["x"] <= x1 - 1.0, "clear of the box's end walls"
    assert z0 + 1.0 <= position["z"] <= z1 - 1.0, "clear of the box's long walls"


@needs_extract
def test_boss_portal_rests_on_the_box_floor_under_the_roof() -> None:
    position = dict(zip("xyz", boss_spawner()["position"], strict=True))
    # Dropped from between the interior floor and the roof underside: 25.75 would be the top of the box, which is where
    # the portal must not sit.
    hit = ws.drop(b.warehouse_triangles(), position["x"], PORTAL_ROOF_PROBE_Y, position["z"])
    assert hit is not None
    assert position["y"] == pytest.approx(hit.y, abs=0.1)
    assert hit.y == pytest.approx(b.BOSS_PORTAL_INTERIOR_FLOOR_Y, abs=0.1)


@needs_extract
def test_boss_drops_on_the_pipe_floor_outside_the_box() -> None:
    x, y, z = b.boss_spawn_position()
    assert (x, z) == b.local_to_world(*b.BOSS_GROUND_LOCAL)
    assert y < b.BOSS_PORTAL_FLOOR_UNDERSIDE_Y, "the boss must not spawn inside the hanging box"
    assert y > b.KILL_FLOOR_Y
    # Below the box's floor slab there is nothing left to catch the drop but the room's floor.
    under_box = ws.drop(b.warehouse_triangles(), x, b.BOSS_PORTAL_FLOOR_UNDERSIDE_Y - 0.5, z)
    assert under_box is not None and y == under_box.y


@needs_extract
def test_boss_spawn_sits_on_the_mesh_surface_it_drops_to() -> None:
    x, y, z = b.boss_spawn_position()
    hit = ws.drop(b.warehouse_triangles(), x, b.BOSS_GROUND_DROP_FROM, z)
    assert hit is not None
    assert y == hit.y


def test_the_boss_spawn_drop_starts_under_the_box_so_the_box_cannot_catch_it() -> None:
    assert b.BOSS_GROUND_DROP_FROM < b.BOSS_PORTAL_FLOOR_UNDERSIDE_Y


@needs_extract
def test_the_boss_shares_the_portals_column_so_it_comes_out_at_its_foot() -> None:
    portal = dict(zip("xyz", boss_spawner()["position"], strict=True))
    boss_x, _, boss_z = b.boss_spawn_position()
    assert boss_x == portal["x"]
    assert boss_z < portal["z"], "the boss comes out on the near side of the box, by the quarter pipe"


def test_boss_spawner_is_scaled_down_to_fit_the_room() -> None:
    assert boss_spawner()["scale"] == [0.4, 0.4, 0.4]


def test_boss_spawner_arch_faces_across_the_floor() -> None:
    assert boss_spawner()["rotation"] == [0.0, 90.0, 0.0]


def test_boss_spawner_hides_the_pillar_mesh_and_its_collider() -> None:
    assert boss_spawner()["hiddenChildren"] == ["BottomPiece", "Collider"]





@needs_extract
def test_the_level_asks_for_the_slide_button_to_start_a_grind() -> None:
    # The coping lips are rails, so a grind that starts on contact hijacks every ollie off a lip.
    assert b.build_level()["grindRequiresSlide"] is True


@needs_extract
def test_the_level_scores_fall_damage_with_the_reference_character() -> None:
    # Calcium carries no FallDamageReduction, so an ollie off a half pipe costs him his whole health bar.
    level = b.build_level()
    assert level["fallDamageCharacter"] == b.FALL_DAMAGE_CHARACTER == "tonymczoom"
    assert b.FALL_DAMAGE_CHARACTER in b.ALLOWED_CHARACTERS


@needs_extract
def test_the_kill_floor_is_above_the_meshs_lowest_point() -> None:
    # Above the Warehouse's lowest geometry so anything that ends up under the mesh dies instead of resting there
    # out of reach of the game's own catch floor.
    triangles = b.warehouse_triangles()
    lowest = min(min(p[1] for p in t) for t in triangles)
    assert lowest < b.KILL_FLOOR_Y


def test_the_mesh_rail_gets_hidden_game_rails_along_its_run_and_its_bend() -> None:
    hidden = [payload(e) for e in b.rail_edits() if payload(e).get("hidden")][: len(b.MESH_RAILS)]
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


def rail_axis_ends(rail: tuple) -> list[tuple[float, float, float]]:
    (x, y, z), yaw, scale, pitch = rail
    half = b.RAIL0_LENGTH * scale / 2
    yaw_r, pitch_r = math.radians(yaw), math.radians(pitch)
    along = (math.cos(pitch_r) * math.cos(yaw_r), math.sin(pitch_r), -math.cos(pitch_r) * math.sin(yaw_r))
    up = (-math.sin(pitch_r) * math.cos(yaw_r), math.cos(pitch_r), math.sin(pitch_r) * math.sin(yaw_r))
    bar = b.RAIL0_BAR_HEIGHT * scale
    centre = tuple(c + u * bar for c, u in zip((x, y, z), up, strict=True))
    return [tuple(c + sign * a * half for c, a in zip(centre, along, strict=True)) for sign in (-1, 1)]


def test_rail_along_spans_a_level_lip_with_its_bar_on_the_lip_height() -> None:
    rail = b.rail_along((119.78, 5.76, 8.59), (178.95, 5.76, 8.59))
    (x, y, z), yaw, scale, pitch = rail
    assert (yaw, pitch) == pytest.approx((0.0, 0.0))
    assert (x, z) == pytest.approx((149.365, 8.59))
    assert scale == pytest.approx(59.17 / b.RAIL0_LENGTH, abs=0.001)
    assert y == pytest.approx(5.76 - b.RAIL0_BAR_HEIGHT * scale)
    assert [c for end in rail_axis_ends(rail) for c in end] == pytest.approx([119.78, 5.76, 8.59, 178.95, 5.76, 8.59], abs=0.01)


def test_rail_along_turns_to_a_lip_running_along_z() -> None:
    _, yaw, _, _ = b.rail_along((10, 3, 0), (10, 3, 28))
    assert yaw == pytest.approx(270.0)


def test_rail_along_pitches_a_falling_lip_and_keeps_its_bar_on_the_lip() -> None:
    start, end = (119.78, 5.76, 8.59), (100.06, 0.5, 3.51)
    rail = b.rail_along(start, end)
    _, yaw, scale, pitch = rail
    assert scale == pytest.approx(math.dist(start, end) / b.RAIL0_LENGTH, abs=0.001)
    assert pitch == pytest.approx(-14.48, abs=0.05)
    assert [c for e in rail_axis_ends(rail) for c in e] == pytest.approx([*start, *end], abs=0.01)


def test_each_coping_rail_is_a_hidden_game_rail_after_the_mesh_rails() -> None:
    placed = [payload(e) for e in b.rail_edits()]
    assert [(p["position"]["x"], p["position"]["y"], p["position"]["z"]) for p in placed[len(b.MESH_RAILS) :]] == [r[0] for r in b.COPING_RAILS]
    assert [p["rotation"]["z"] for p in placed[len(b.MESH_RAILS) :]] == [r[3] for r in b.COPING_RAILS]


@needs_extract
def test_every_coping_lip_runs_between_corners_of_the_mesh_lip() -> None:
    runs = ws.lip_runs(b.warehouse_triangles()) + ws.ledge_runs(b.warehouse_triangles())
    corners = [p for run in runs for p in run]
    for start, end in b.COPING_LIPS:
        assert min(math.dist(start, c) for c in corners) < 0.1, start
        assert min(math.dist(end, c) for c in corners) < 0.1, end


@needs_extract
def test_a_coping_lip_that_is_one_whole_run_matches_it() -> None:
    runs = ws.lip_runs(b.warehouse_triangles()) + ws.ledge_runs(b.warehouse_triangles())
    whole = [lip for lip in b.COPING_LIPS if math.dist(*lip) > MIN_COPING_LIP]
    for start, end in whole:
        assert any(
            min(math.dist(start, a) + math.dist(end, c), math.dist(start, c) + math.dist(end, a)) < 0.1 for a, c in runs
        ) or any(math.dist(start, a) < 0.1 for a, _ in runs), (start, end)


def test_no_coping_rail_is_short_enough_for_the_handoff_to_bounce_between_neighbours() -> None:
    for lip in b.COPING_LIPS:
        assert math.dist(*lip) >= MIN_COPING_LIP, lip


def test_the_coping_lips_are_the_main_half_pipe_edges_and_the_diagonals_at_their_west_ends() -> None:
    level = [(s, e) for s, e in b.MAIN_PIPE_LIPS if s[1] == e[1]]
    assert sorted((s[2], s[1]) for s, _ in level) == [(8.59, 5.76), (43.81, 5.76)]
    diagonals = [(s, e) for s, e in b.MAIN_PIPE_LIPS if s[1] != e[1]]
    assert sorted(e for _, e in diagonals) == [(100.06, 0.5, 3.51), (100.06, 0.5, 48.87)]


def test_each_diagonal_lip_starts_where_a_level_lip_ends() -> None:
    level_ends = {end for start, end in b.MAIN_PIPE_LIPS if start[1] == end[1] for end in (start, end)}
    for start, end in b.MAIN_PIPE_LIPS:
        if start[1] != end[1]:
            assert start in level_ends


def test_the_shortys_ledge_edge_runs_from_the_kicker_end_to_the_west_wall() -> None:
    assert b.LEDGE_LIPS[0][0] == (40.89, 3.79, 3.51)
    assert b.LEDGE_LIPS[-1][1] == (21.17, 3.79, 58.73)


def test_the_ledge_lips_join_end_to_end_with_gentle_turns() -> None:
    for (_, end), (start, nxt) in zip(b.LEDGE_LIPS, b.LEDGE_LIPS[1:], strict=False):
        assert end == start
    for (a, mid), (_, c) in zip(b.LEDGE_LIPS, b.LEDGE_LIPS[1:], strict=False):
        before = math.atan2(mid[2] - a[2], mid[0] - a[0])
        after = math.atan2(c[2] - mid[2], c[0] - mid[0])
        turn = abs((math.degrees(after - before) + 180) % 360 - 180)
        assert turn <= 50


def test_the_ledge_lips_are_coping_lips() -> None:
    assert set(b.LEDGE_LIPS) <= set(b.COPING_LIPS)


def test_the_start_pipe_lip_runs_along_the_platform_edge_above_the_spawn() -> None:
    [(start, end)] = b.START_PIPE_LIPS
    assert (start, end) == ((80.34, 35.85, -120.84), (139.5, 35.85, -120.84))
    assert b.PLAYER_START[0] in range(int(start[0]), int(end[0]))
    assert set(b.START_PIPE_LIPS) <= set(b.COPING_LIPS)


def test_every_coping_rail_runs_edge_to_edge_along_its_lip() -> None:
    for lip, rail in zip(b.COPING_LIPS, b.COPING_RAILS, strict=True):
        ends = rail_axis_ends(rail)
        assert [c for end in ends for c in end] == pytest.approx([*lip[0], *lip[1]], abs=0.01), lip


@needs_extract
def test_the_hand_placed_merchant_stands_on_the_floor_rather_than_hovering() -> None:
    merchant = next(c for c in b.collectibles() if c.code == "T")
    hit = ws.drop(b.warehouse_triangles(), merchant.x, merchant.y + 1, merchant.z)
    base_offset = b.ITEM_METRICS[merchant.catalog_id].base_offset
    assert merchant.y - base_offset - hit.y == pytest.approx(0, abs=0.1)


@needs_extract
def test_the_player_lands_on_the_start_pipe_slope_clear_of_the_lip_rail() -> None:
    x, y, z = b.PLAYER_START
    assert z - b.START_PIPE_LIPS[0][0][2] >= 3
    hit = ws.drop(b.warehouse_triangles(), x, y, z)
    assert hit is not None
    assert math.degrees(math.acos(hit.normal[1])) < 45


GROUNDED_OVERRIDES = ("E", "Tape", "100/15")
LEANING_OVERRIDES = ("100/30", "A")


@needs_extract
def test_hand_placed_items_rest_on_the_surface_without_hovering() -> None:
    triangles = b.warehouse_triangles()
    items = {c.code: c for c in b.collectibles()}
    for code in GROUNDED_OVERRIDES:
        assert b.lowest_clearance(items[code], triangles) == pytest.approx(0, abs=0.1), code
    for code in LEANING_OVERRIDES:
        assert b.lowest_clearance(items[code], triangles) <= 0.1, code


def test_lowest_clearance_of_a_level_item_is_its_height_above_the_floor() -> None:
    floor = [((-50, 0, -50), (50, 0, -50), (-50, 0, 50)), ((50, 0, -50), (50, 0, 50), (-50, 0, 50))]
    item = b.Collectible("X", "interactable/chest", 0, 0.0, 1.5, 0.0, (0.0, 1.0, 0.0), (270, 0, 0), 0.0, True)
    assert b.lowest_clearance(item, floor) == pytest.approx(1.5 - b.ITEM_METRICS["interactable/chest"].base_offset)
