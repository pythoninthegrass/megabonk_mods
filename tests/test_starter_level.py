import importlib
import json
import math
from collections import deque
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def starter():
    return importlib.import_module("build_starter_level")


def edges(cell):
    height = cell["height"]
    slope = cell.get("slope")
    directions = {"north": (0, 1), "east": (1, 0), "south": (0, -1), "west": (-1, 0)}
    if not slope:
        return dict.fromkeys(directions.values(), height)
    dx, dz = directions[slope]
    return {(dx, dz): height + 1, (-dx, -dz): height}


def test_starter_is_native_forest_with_stock_rules():
    level = starter().build_level()
    assert (level["schemaVersion"], level["baseline"], level["map"], level["stageIndex"], level["tier"]) == (4, "none", 1, 0, 0)
    assert level["title"] == "Bramblecrown Hill"
    assert level["packs"] == {}
    assert not any(key in level for key in ("music", "allowedCharacters", "maxSlopeAngle", "fallDamageCharacter"))
    assert all(edit["opType"] == "object.place" for edit in level["edits"])
    assert all(not json.loads(edit["payload"])["catalogId"].startswith("bundle:") for edit in level["edits"])


def test_two_level_drop_is_free_without_borrowing_tonys_blanket_immunity():
    level = starter().build_level()
    assert level["fallDamageFreeHeight"] == 40
    assert not level.get("fallDamageCharacter")


def test_every_tile_is_walkable_from_spawn_without_jumping():
    level = starter().build_level()
    grid = level["grid"]
    assert (grid["width"], grid["depth"], len(grid["cells"])) == (13, 12, 156)
    cells = {(cell["x"], cell["z"]): cell for cell in grid["cells"]}
    assert len(cells) == 156
    assert {cell["height"] for cell in cells.values()} == {-1, 0, 1, 2, 3, 4}
    assert sum("slope" in cell for cell in cells.values()) >= 12
    assert starter().SPAWN_CELL == (6, 1)
    assert set(walk_distances(cells, starter().SPAWN_CELL)) == set(cells)


def walk_distances(cells, start):
    distances = {start: 0}
    queue = deque([start])
    while queue:
        x, z = queue.popleft()
        for (dx, dz), height in edges(cells[x, z]).items():
            target = (x + dx, z + dz)
            if target in cells and target not in distances and edges(cells[target]).get((-dx, -dz)) == height:
                distances[target] = distances[x, z] + 1
                queue.append(target)
    return distances


def test_summit_is_only_reachable_by_the_long_spiral():
    module = starter()
    level = module.build_level()
    cells = {(cell["x"], cell["z"]): cell for cell in level["grid"]["cells"]}
    distances = walk_distances(cells, module.SPAWN_CELL)
    top = max(cell["height"] for cell in cells.values())
    summit = {pos for pos, cell in cells.items() if cell["height"] == top and "slope" not in cell}
    assert set(module.SUMMIT_CELLS) <= summit
    boss = level["bossSpawner"]["position"]
    assert (round(boss[0] / 40 + module.CENTER), round(boss[2] / 40 + module.CENTER)) in summit
    assert len(module.SUMMIT_CELLS) == 9
    assert min(distances[pos] for pos in summit) >= 15


def test_every_district_has_a_chest_and_shrines_spread_across_districts():
    module = starter()
    level = module.build_level()
    payloads = [json.loads(edit["payload"]) for edit in level["edits"]]
    chests = [p["position"] for p in payloads if p["catalogId"].startswith("interactable/chest")]

    def cell_of(position):
        return round(position["x"] / 40 + module.CENTER), round(position["z"] / 40 + module.CENTER)

    def inside(cell, box):
        x0, x1, z0, z1 = box
        return x0 <= cell[0] <= x1 and z0 <= cell[1] <= z1

    for name, box in module.DISTRICTS.items():
        assert any(inside(cell_of(c), box) for c in chests), f"no chest in {name}"
    spots = [(round(s[0] / 40 + module.CENTER), round(s[2] / 40 + module.CENTER)) for s in level["shrineSpots"]]
    assert len(spots) >= 6
    assert sum(any(inside(spot, box) for spot in spots) for box in module.DISTRICTS.values()) >= 5


def test_landmarks_and_rewards_have_ground_support():
    module = starter()
    level = module.build_level()
    cells = {(cell["x"], cell["z"]): cell for cell in level["grid"]["cells"]}
    positions = [level["spawn"]["position"], level["bossSpawner"]["position"]]
    payloads = [json.loads(edit["payload"]) for edit in level["edits"]]
    positions += [list(payload["position"].values()) for payload in payloads]
    for x, y, z in positions:
        cell = cells[round(x / 40 + module.CENTER), round(z / 40 + module.CENTER)]
        assert "slope" not in cell
        assert abs(y - cell["height"] * 20) <= 3
    ids = [payload["catalogId"] for payload in payloads]
    assert ids.count("interactable/chest") >= 8
    assert ids.count("interactable/chestFree") == 1
    targets = [edit["target"] for edit in level["edits"]]
    assert targets[0] == "placement:0"
    assert len(targets) == len(set(targets))


def test_large_map_has_many_charge_shrines_on_well_spaced_spots():
    level = starter().build_level()
    spots = level["shrineSpots"]
    assert level["guaranteedShrineKinds"].count("charge") >= 5
    assert set(level["guaranteedShrineKinds"]) == {"charge"}
    assert level["shrineKindRanges"] == {"moai": [3, 5], "shadyGuy": [2, 3]}
    assert (level["extraShrines"], level["extraShrinesMax"]) == (2, 3)
    planned = [len(level["guaranteedShrineKinds"]) + level["extraShrines"] + sum(low for low, _ in level["shrineKindRanges"].values()),
               len(level["guaranteedShrineKinds"]) + level["extraShrinesMax"] + sum(high for _, high in level["shrineKindRanges"].values())]
    assert planned == [12, 16]
    most = len(level["guaranteedShrineKinds"]) + level["extraShrinesMax"] + sum(high for _, high in level["shrineKindRanges"].values())
    assert len(spots) >= most + 2
    cells = {(cell["x"], cell["z"]): cell for cell in level["grid"]["cells"]}
    assert all("slope" not in cells[round(x / 40 + starter().CENTER), round(z / 40 + starter().CENTER)] for x, _, z in spots)
    assert all(math.dist((a[0], a[2]), (b[0], b[2])) >= 40 for i, a in enumerate(spots) for b in spots[i + 1 :])
    assert "balance" not in level["extraShrineKinds"]


def test_moai_and_shady_guy_are_guaranteed_outside_the_spawn_meadow():
    level = starter().build_level()
    assert level["shrineGuarantees"] == [
        {"kind": kind, "minX": -140, "maxX": 140, "minZ": -260, "maxZ": -100, "outside": True} for kind in ("moai", "shadyGuy")
    ]
    spots = level["shrineSpots"]
    outside = [s for s in spots if not (-140 <= s[0] <= 140 and -260 <= s[2] <= -100)]
    assert len(outside) >= 18


def test_moai_have_a_three_cell_horizontal_spacing_rule():
    assert starter().build_level()["shrineKindSpacing"] == {"moai": 120}


def test_every_placed_prop_uses_its_native_upright_rotation():
    module = starter()
    payloads = [json.loads(edit["payload"]) for edit in module.build_level()["edits"]]
    assert {p["catalogId"] for p in payloads} <= set(module.NATIVE_ROTATION_X)
    assert all(p["rotation"]["x"] == module.NATIVE_ROTATION_X[p["catalogId"]] and p["rotation"]["z"] == 0 for p in payloads)
    chests = [p for p in payloads if p["catalogId"].startswith("interactable/chest")]
    assert len(chests) >= 9
    assert all(p["rotation"]["x"] == 270 for p in chests)
    assert all(module.NATIVE_ROTATION_X[p["catalogId"]] == 270 for p in payloads if p["catalogId"] in (module.TREE, module.LOG, module.BUSH))


def test_level_is_a_composite_of_all_five_biomes_one_per_zone():
    module = starter()
    level = module.build_level()
    placed = [(json.loads(edit["payload"])["catalogId"], json.loads(edit["payload"])["position"]) for edit in level["edits"]]
    assert {catalog.split("/")[0] for catalog, _ in placed} >= {"forest", "desert", "dungeon", "graveyard", "hell"}
    for biome, district in module.ZONE_DISTRICTS.items():
        x0, x1, z0, z1 = module.DISTRICTS[district]
        inside = [c for c, pos in placed if x0 <= round(pos["x"] / 40 + module.CENTER) <= x1 and z0 <= round(pos["z"] / 40 + module.CENTER) <= z1]
        native = [c for c in inside if c.startswith(biome + "/")]
        assert len(native) >= 6, f"{district} has {len(native)} {biome} props"
        assert len(native) >= len(inside) / 2 - 2, f"{district} is mostly not {biome}"
    assert any(catalog == module.COFFIN_TILE for catalog, _ in placed)


def test_desert_dungeon_and_hell_districts_have_their_own_ground():
    module = starter()
    zones = starter().build_level()["groundZones"]
    assert set(module.GROUND_MATERIAL) == {"desert", "dungeon", "hell"}
    for biome, material in module.GROUND_MATERIAL.items():
        x0, x1, z0, z1 = module.DISTRICTS[module.ZONE_DISTRICTS[biome]]
        assert {"material": material, "minX": x0, "maxX": x1, "minZ": z0, "maxZ": z1} in zones
    assert {"material": "m_crypt_Floor", "minX": 11, "maxX": 12, "minZ": 1, "maxZ": 4} in zones
    assert len(zones) == 6


def test_lava_pool_sits_in_the_hell_pen_clear_of_everything_placed_or_walked():
    module = starter()
    level = module.build_level()
    zones = level["lavaZones"]
    assert len(zones) == 2
    cells = set()
    x0, x1, z0, z1 = module.DISTRICTS["east pen"]
    for zone in zones:
        assert x0 <= zone["minX"] <= zone["maxX"] <= x1 and z0 <= zone["minZ"] <= zone["maxZ"] <= z1
        cells |= {(x, z) for x in range(zone["minX"], zone["maxX"] + 1) for z in range(zone["minZ"], zone["maxZ"] + 1)}
        assert {"material": "LavaCrypt", "minX": zone["minX"], "maxX": zone["maxX"], "minZ": zone["minZ"], "maxZ": zone["maxZ"]} in level["groundZones"]
    keep_clear = set(module.RAMPS) | set(module.CHESTS) | {module.FREE_CHEST, module.SPAWN_CELL} | set(module.SHRINE_CELLS)
    assert not cells & keep_clear
    for edit in level["edits"]:
        payload = json.loads(edit["payload"])
        pos = payload["position"]
        if payload["catalogId"] in module.HELL_WALLS:
            assert abs(pos["x"] - 200) >= 19, "court wall intrudes into the crossing"
            continue
        assert (round(pos["x"] / 40 + module.CENTER), round(pos["z"] / 40 + module.CENTER)) not in cells


def test_lava_court_has_dry_landings_bypass_walls_and_walkable_escape():
    module = starter()
    level = module.build_level()
    cells = {(cell["x"], cell["z"]): cell for cell in level["grid"]["cells"]}
    lava = {(x, z) for x0, x1, z0, z1 in module.LAVA_BANDS for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)}
    assert lava == {(11, 2), (11, 4)}
    assert all(cells[c]["height"] == 0 and "slope" not in cells[c] for c in lava | {(11, 1)})
    for cell in lava:
        assert module.SPAWN_CELL in walk_distances(cells, cell), "no walkable lava escape"
    dry = {pos: cell for pos, cell in cells.items() if pos not in lava}
    reached = walk_distances(dry, module.SPAWN_CELL)
    assert all(pos in reached for pos in module.CHESTS)
    assert (11, 1) in reached and (11, 3) in reached, "landings lack dry bypass"
    walls = [json.loads(e["payload"])["position"] for e in level["edits"] if json.loads(e["payload"])["catalogId"] in module.HELL_WALLS]
    for z in (1, 2, 3, 4):
        for x in (10.5, 12.5):
            if (x, z) in ((10.5, 1), (10.5, 3), (12.5, 1)):
                continue
            assert any(abs(p["x"] - 40 * (x - module.CENTER)) < 1 and abs(p["z"] - 40 * (z - module.CENTER)) < 1 for p in walls)


def test_buried_dungeon_pillar_assemblies_are_removed():
    module = starter()
    ids = [json.loads(e["payload"])["catalogId"] for e in module.build_level()["edits"]]
    assert module.DUNGEON_TILES[0] not in ids
    assert module.DUNGEON_TILES[2] not in ids


def test_lava_court_has_west_and_south_exits_with_no_wall_across_them():
    module = starter()
    level = module.build_level()
    cells = {(c["x"], c["z"]): c for c in level["grid"]["cells"]}
    assert cells[11, 3].get("slope") == "west"
    assert cells[12, 1].get("slope") == "south"
    assert edges(cells[11, 3]) == {(-1, 0): 1, (1, 0): 0}
    assert edges(cells[12, 1]) == {(0, -1): 1, (0, 1): 0}
    for edit in level["edits"]:
        payload = json.loads(edit["payload"])
        if payload["catalogId"] not in module.HELL_WALLS:
            continue
        p = payload["position"]
        assert not (abs(p["x"] - 180) < 2 and abs(p["z"] + 120) < 20)
        assert not (abs(p["x"] - 260) < 2 and abs(p["z"] + 200) < 20)


def test_boss_and_miniboss_pools_mix_enemies_from_every_map():
    level = starter().build_level()
    bosses, minis = level["bossPool"], level["minibossPool"]
    assert len(bosses) == len(set(bosses)) == 6
    assert len(minis) == len(set(minis)) >= 6
    assert bosses == ["Ent1", "Ent2", "Ent3", "Pharaoh1", "Pharaoh2", "Pharaoh3"]
    assert minis == ["MinibossPig", "MinibossGolem", "MinibossGolemSand", "MinibossScorpion", "Ghostham", "CalciumDad"]


def test_fire_burns_only_on_ground_a_biome_has_repainted():
    module = starter()
    level = module.build_level()
    painted = [(z["minX"], z["maxX"], z["minZ"], z["maxZ"]) for z in level["groundZones"]]
    fires = [json.loads(e["payload"])["position"] for e in level["edits"] if json.loads(e["payload"])["catalogId"] == module.FIRE]
    assert fires
    for pos in fires:
        cell = (round(pos["x"] / 40 + module.CENTER), round(pos["z"] / 40 + module.CENTER))
        assert any(x0 <= cell[0] <= x1 and z0 <= cell[1] <= z1 for x0, x1, z0, z1 in painted), f"fire on forest ground at {cell}"


def test_boss_arena_stays_clear():
    level = starter().build_level()
    boss = level["bossSpawner"]["position"]
    for edit in level["edits"]:
        payload = json.loads(edit["payload"])
        pos = payload["position"]
        if abs(pos["y"] - boss[1]) < 3:
            assert math.dist((pos["x"], pos["z"]), (boss[0], boss[2])) >= 40


def test_summit_tower_bases_stay_two_units_inside_the_supported_plateau():
    module = starter()
    # Conservative live renderer footprints relative to each ruin's origin at its authored yaw.
    footprints = {"0": (-15.7, 1.4, -16.5, 0.5, 270), "1": (-21.3, 21.6, -23.4, 20.2, 0), "2": (-10.1, 20.2, -11.8, 18.5, 90)}
    towers = [json.loads(e["payload"]) for e in module.build_level()["edits"] if json.loads(e["payload"])["catalogId"].startswith(module.RUIN)]
    assert len(towers) == 3
    for tower in towers:
        min_x, max_x, min_z, max_z, yaw = footprints[tower["catalogId"].rsplit("/", 1)[1]]
        assert tower["rotation"]["y"] == yaw
        x, z = tower["position"]["x"], tower["position"]["z"]
        assert -58 <= x + min_x <= x + max_x <= 58
        assert -58 <= z + min_z <= z + max_z <= 58


def test_checked_in_level_matches_builder():
    assert json.loads((ROOT / "levels/bramblecrown-hill.mblevel.json").read_text()) == starter().build_level()


def test_original_selection_art_is_reproducible_and_small(tmp_path):
    starter().write_assets(tmp_path)
    for name, size in (("bramblecrown-hill.png", (1080, 720)), ("bramblecrown-hill.biome.png", (256, 256))):
        generated = tmp_path / name
        shipped = ROOT / "levels" / name
        with Image.open(generated) as image:
            assert image.size == size
            assert image.mode == "RGB"
        assert generated.read_bytes() == shipped.read_bytes()
        assert generated.stat().st_size < 1024 * 1024


def test_selection_art_shows_the_rectangular_lava_court():
    image = starter().artwork()
    assert image.getpixel((840, 605)) == (238, 103, 49)
    assert image.getpixel((840, 620)) != (238, 103, 49)
