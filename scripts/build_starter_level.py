#!/usr/bin/env python3
"""Build Bramblecrown Hill and its original selection artwork using no extracted assets."""

import argparse
import json
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SLUG = "bramblecrown-hill"
SIZE = 15
CENTER = 7
SPAWN_CELL = (7, 1)
# Euler X each placeable prefab is authored with, read from the game's own prefabs: most props are authored lying down at 270.
NATIVE_ROTATION_X: dict[str, float] = {}


def prop(catalog: str, rotation_x: float = 270) -> str:
    NATIVE_ROTATION_X[catalog] = rotation_x
    return catalog


FOREST, DESERT, DUNGEON, GRAVEYARD, HELL = (f"{biome}/stage0/randomMapObjects/" for biome in ("forest", "desert", "dungeon", "graveyard", "hell"))
TREE, LOG, BUSH, ROCK = prop(FOREST + "0/0"), prop(FOREST + "1/0"), prop(FOREST + "2/0"), prop(FOREST + "3/1", 0)
RUIN = "forest/stage0/stageTilePrefabs/flat/"
for _i in range(3):
    prop(RUIN + str(_i), 0)
CHEST, CHEST_FREE = prop("interactable/chest"), prop("interactable/chestFree")
DESERT_LANDMARKS = [prop(DESERT + f"0/{i}") for i in range(4)]
DESERT_HOUSES = [prop(DESERT + f"1/{i}") for i in range(2)]
DUNGEON_TILES = [prop(f"dungeon/stage0/stageTilePrefabs/flat/{i}", 0) for i in range(4)]
GRAVE_TILES = [prop(f"graveyard/stage0/stageTilePrefabs/flat/{i}", 0) for i in (0, 2, 4, 6, 9, 11)]
COFFIN_TILE = prop("graveyard/stage0/stageTilePrefabs/specific/0", 0)
ARCH = prop(GRAVEYARD + "6/2")
FIRE = prop(HELL + "3/0", 0)
HELL_LANDMARK = prop(HELL + "0/1")
HELL_COLUMN = prop(HELL + "4/1")
HELL_WALLS = [prop(HELL + f"7/{i}") for i in range(4)]
# Per-zone scatter as (catalog, scale); a scale is the prefab's native scale times a factor chosen so the prop reads at this level's cell size.
SCATTER = {
    "forest": [(TREE, 2.5), (BUSH, 1.8), (ROCK, 1.8)],
    "desert": [(prop(DESERT + "3/0"), 3.5), (prop(DESERT + "3/1"), 3.5), (prop(DESERT + "5/0"), 3), (prop(DESERT + "5/1"), 3), (prop(DESERT + "6/0"), 3)]
    + [(prop(DESERT + f"2/{i}"), 4) for i in (0, 1, 2, 3, 5, 6)],
    "dungeon": [(prop(DUNGEON + "0/0"), 4), (prop(DUNGEON + "0/1"), 4), (prop(DUNGEON + "1/0"), 4), (prop(DUNGEON + "2/0"), 4), (prop(DUNGEON + "2/1", 0), 6)]
    + [(prop(DUNGEON + "3/0"), 3.5), (prop(DUNGEON + "3/0"), 3.5), (prop(DUNGEON + "4/0", 0), 3)],
    "graveyard": [(prop(GRAVEYARD + f"0/{i}"), 2.5) for i in range(3)]
    + [(prop("graveyard/randomObjectsOverride/5/0"), 2.5), (prop("graveyard/randomObjectsOverride/5/0"), 2.5), (prop("graveyard/randomObjectsOverride/1/0"), 2.5),
       (prop("graveyard/randomObjectsOverride/2/0"), 2.2), (prop("graveyard/randomObjectsOverride/3/0"), 2.5), (prop("graveyard/randomObjectsOverride/4/0"), 2.5),
       (prop(GRAVEYARD + "4/0"), 2), (prop(GRAVEYARD + "6/0"), 2), (prop(GRAVEYARD + "6/1"), 2), (prop(GRAVEYARD + "7/0"), 2.5), (prop(GRAVEYARD + "5/0"), 2.5)],
    "hell": [(prop(HELL + f"2/{i}", 0), 4) for i in (0, 1, 2, 3, 4, 5)]
    + [(FIRE, 3.5), (FIRE, 3.5)] + [(prop(HELL + f"4/{i}"), 5) for i in range(3)] + [(prop(HELL + f"5/{i}"), 5) for i in range(2)] + [(prop(HELL + "6/0"), 5)]
    + [(prop(HELL + f"6/{i}"), 6) for i in (1, 2, 3)],
}
# Each zone's density per interior cell; the map's perimeter cells always get two props so the island is framed.
DENSITY = {"forest": 0.4, "desert": 0.9, "dungeon": 1.0, "graveyard": 1.0, "hell": 1.0}
# The first prop on each perimeter cell, as (catalog, scale).
EDGE_LEAD = {"forest": (TREE, 2.5), "desert": (DESERT + "5/0", 3), "dungeon": (DUNGEON + "4/0", 3), "graveyard": (GRAVEYARD + "0/0", 2.5), "hell": (HELL + "4/0", 5)}
# Ramp cells: (height at the low edge, uphill side).
RAMPS = {
    (6, 6): (0, "west"), (5, 7): (1, "north"), (6, 10): (2, "east"), (9, 9): (3, "south"),
    (3, 2): (-1, "east"), (1, 6): (-1, "north"), (2, 10): (0, "north"), (10, 10): (0, "north"),
    (11, 2): (0, "east"), (12, 8): (1, "north"), (10, 13): (1, "east"), (13, 12): (2, "north"),
    (13, 5): (0, "north"),
}
# Flat cells of the hill's spiral ring; the summit sits inside it.
HILL = {
    (5, 6): 1, (7, 6): 0, (8, 6): 0, (9, 6): 0, (5, 8): 2, (5, 9): 2, (5, 10): 2,
    (7, 10): 3, (8, 10): 3, (9, 10): 3, (9, 8): 4, (9, 7): 4,
}
SUMMIT_CELLS = [(x, z) for x in (6, 7, 8) for z in (7, 8, 9)]
DISTRICTS = {
    "spawn meadow": (4, 10, 0, 5), "west gully": (0, 3, 0, 6), "west ridge": (0, 3, 7, 14),
    "north ruins": (4, 10, 11, 14), "east highland": (11, 14, 9, 14), "east pen": (11, 14, 0, 8),
    "spiral": (5, 9, 6, 10),
}
ZONE_DISTRICTS = {"graveyard": "west gully", "dungeon": "north ruins", "hell": "east pen", "desert": "east highland"}
# Terrain materials of the game's own biomes, painted over the Forest ground of the matching district.
GROUND_MATERIAL = {"desert": "m_1_TerrainDesert", "dungeon": "m_crypt_Floor", "hell": "m_TerrainHell"}
# Cells (min x, max x, min z, max z) of the lava pool in the hell pen, sunk one level below the pen floor that rings it, with a ramp at (13, 5) to climb out; and what standing in it costs.
LAVA_CELLS = (12, 13, 3, 4)
LAVA_DAMAGE, LAVA_INTERVAL = 3, 0.5
# Enemy names (EEnemy) a stage boss or miniboss spawn is replaced by, drawn from every map's roster.
BOSS_POOL = ["Ent1", "Ent2", "Ent3", "Pharaoh1", "Pharaoh2", "Pharaoh3", "Bandit", "Bush"]
MINIBOSS_POOL = ["MinibossPig", "MinibossGolem", "MinibossGolemSand", "MinibossScorpion", "Ghostham", "CalciumDad"]
CHESTS = [(0, 0), (0, 14), (7, 13), (14, 14), (14, 0), (5, 9), (12, 11), (10, 4)]
FREE_CHEST = (5, 2)
SHRINE_CELLS = [
    (9, 3), (4, 4), (5, 0), (10, 1),
    (1, 3), (2, 0), (0, 5), (3, 4), (0, 2), (2, 4),
    (1, 9), (3, 8), (1, 12), (3, 13), (0, 7),
    (5, 13), (9, 12), (7, 11),
    (12, 10), (12, 13), (13, 10), (11, 12), (14, 12),
    (14, 5), (13, 2), (14, 7), (12, 6),
]
GUARANTEED_CHARGE_SHRINES = 5
MERCHANT_AND_MOAI_RANGE = [3, 8]


def height(x: int, z: int) -> int:
    if (x, z) in SUMMIT_CELLS:
        return 4
    if LAVA_CELLS[0] <= x <= LAVA_CELLS[1] and LAVA_CELLS[2] <= z <= LAVA_CELLS[3]:
        return 0
    if (x, z) in HILL:
        return HILL[x, z]
    if x <= 3:
        return -1 if z <= 6 else int(z >= 11)
    if x >= 11:
        if z <= 8:
            return 1
        return 3 if x >= 13 and z >= 13 else 2
    return int(z >= 11)


def point(x: int, z: int, dx: float = 0, dz: float = 0, lift: float = 0) -> list[float]:
    return [40 * (x - CENTER) + dx, 20 * height(x, z) + lift, 40 * (z - CENTER) + dz]


def placement(index: int, catalog: str, position: list[float], yaw: float = 0, scale: float = 1) -> dict:
    payload = {
        "catalogId": catalog,
        "position": dict(zip(("x", "y", "z"), position, strict=True)),
        "rotation": {"x": NATIVE_ROTATION_X[catalog], "y": yaw, "z": 0},
        "scale": dict.fromkeys(("x", "y", "z"), scale),
    }
    return {"opType": "object.place", "target": f"placement:{index}", "payload": json.dumps(payload, separators=(",", ":"))}


def zone_of(x: int, z: int) -> str:
    for zone, district in ZONE_DISTRICTS.items():
        x0, x1, z0, z1 = DISTRICTS[district]
        if x0 <= x <= x1 and z0 <= z <= z1:
            return zone
    return "forest"


def build_edits(spawn: list[float], boss: list[float], shrine_spots: list[list[float]]) -> list[dict]:
    edits = []
    reserved = []

    def add(catalog, position, yaw=0, scale=1, radius=19):
        edits.append(placement(len(edits), catalog, position, yaw, scale))
        reserved.append((position[0], position[2], radius))

    rng = random.Random(481)
    add(ROCK, point(*SPAWN_CELL, dx=12, dz=12), 20, 2.5)
    for x, z in CHESTS:
        add(CHEST, point(x, z, lift=0.5), (x * 47 + z * 13) % 360)
    add(CHEST_FREE, point(*FREE_CHEST, lift=0.5), 135)
    reserved += [(p[0], p[2], 19) for p in (spawn, boss, *shrine_spots)]

    for z in range(2, 6):
        for dz in (-10, 10):
            for side in (-20, 20):
                catalog = ROCK if (z + (dz > 0) + (side > 0)) % 2 else BUSH
                add(catalog, point(7, z, side, dz), rng.randrange(360), 1.5 if catalog == ROCK else 1.8)
    for ruin, x, z, dx, dz, yaw in [(2, 6, 9, -8, 8, 90), (1, 8, 9, 8, 8, 0), (0, 6, 7, -8, -8, 270)]:
        add(RUIN + str(ruin), point(x, z, dx, dz), yaw)
    for x, z, dx, dz in [(4, 9, 0, 0), (10, 9, 0, 0), (5, 5, 12, -12), (9, 5, -12, -12)]:
        add(BUSH, point(x, z, dx, dz), rng.randrange(360), 1.8)

    # North plateau: dungeon sets, one per quarter of the plateau.
    for tile, (x, z) in zip(DUNGEON_TILES, [(5, 12), (8, 12), (9, 14), (6, 14)], strict=True):
        add(tile, point(x, z), rng.choice((0, 90, 180, 270)), 1, 26)
    # East highland: desert landmarks and houses.
    add(DESERT_LANDMARKS[0], point(11, 14), 200, 0.7 * 6, 45)
    add(DESERT_LANDMARKS[3], point(14, 9), 90, 0.7 * 5, 40)
    add(DESERT_HOUSES[0], point(11, 10, dx=-8), 90, 1.3, 26)
    add(DESERT_HOUSES[1], point(11, 13, dx=-8), 270, 1.3, 26)
    # East pen: a hell wall along the west side with a gap at the ramp, a landmark in the far corner.
    for i, z in enumerate((0, 1, 3, 4, 5, 6, 7, 8)):
        add(HELL_WALLS[i % 4], point(11, z, dx=-14), 90, 5.5, 22)
    add(HELL_LANDMARK, point(14, 3), 270, 0.8 * 4, 40)
    for z, dz in ((1, 14), (3, -14)):
        add(HELL_COLUMN, point(11, z, dx=-14, dz=dz), 0, 5, 14)
    for x, z in [(12, 0), (14, 8), (12, 7)]:
        add(FIRE, point(x, z, dx=10, dz=10), 0, 3.5, 14)
    # West gully: a graveyard gate at the ramp, cobble patches, and the coffin tile.
    add(ARCH, point(2, 2), 90, 2.5, 30)
    add(COFFIN_TILE, point(1, 1), 0, 1, 40)
    for tile, (x, z) in zip(GRAVE_TILES, [(0, 3), (3, 5), (2, 6), (0, 4), (3, 0), (1, 5)], strict=True):
        add(tile, point(x, z, dx=10, dz=10), 0, 1, 12)

    for x in range(SIZE):
        for z in range(SIZE):
            if (x, z) in RAMPS or 5 <= x <= 9 and 6 <= z <= 10 or 5 <= x <= 9 and z <= 5 or LAVA_CELLS[0] <= x <= LAVA_CELLS[1] and LAVA_CELLS[2] <= z <= LAVA_CELLS[3]:
                continue
            zone = zone_of(x, z)
            edge = x in (0, SIZE - 1) or z in (0, SIZE - 1)
            count = 2 if edge else int(rng.random() < DENSITY[zone]) if zone != "graveyard" else 1
            for n in range(count):
                dx, dz = rng.choice((-12, 12)), rng.choice((-12, 12))
                position = point(x, z, dx, dz)
                if any(math.dist((position[0], position[2]), (rx, rz)) < radius for rx, rz, radius in reserved):
                    continue
                if edge and n == 0:
                    catalog, scale = EDGE_LEAD[zone]
                else:
                    catalog, scale = rng.choice(SCATTER[zone])
                add(catalog, position, rng.randrange(360), round(scale * rng.uniform(0.8, 1.25), 3))
    return edits


def build_level() -> dict:
    cells = []
    for x in range(SIZE):
        for z in range(SIZE):
            cell = {"x": x, "z": z, "height": height(x, z)}
            if (x, z) in RAMPS:
                cell["height"], cell["slope"] = RAMPS[x, z]
            cells.append(cell)

    spawn = point(*SPAWN_CELL, lift=1.925)
    boss = point(7, 8)
    shrine_spots = [point(x, z) for x, z in SHRINE_CELLS]
    return {
        "schemaVersion": 4,
        "gameBuildId": "21750826",
        "title": "Bramblecrown Hill",
        "description": "A bramble-ringed hill with a ruined watchpost on its crown. Follow the fence line to the foot of the hill and climb the spiral path.",
        "mapDescription": "A handcrafted woodland of meadows, ridges and mossy ruins around one tall hill. Wander the districts for chests and shrines, or climb the spiral to the summit. A first adventure, and a first level to make your own. No extra packs needed.",
        "baseline": "none", "map": 1, "stageIndex": 0, "tier": 0, "seed": 0, "packs": {},
        "grid": {"width": SIZE, "depth": SIZE, "cells": cells},
        "spawn": {"position": spawn, "rotation": [0, 0, 0]},
        "bossSpawner": {"position": boss, "rotation": [0, 180, 0]},
        "shrineSpots": shrine_spots,
        "guaranteedShrineKinds": ["charge"] * GUARANTEED_CHARGE_SHRINES,
        "extraShrines": 2, "extraShrinesMax": 3,
        "extraShrineKinds": ["charge", "magnet", "greed"],
        "shrineKindRanges": {"moai": MERCHANT_AND_MOAI_RANGE, "shadyGuy": MERCHANT_AND_MOAI_RANGE},
        "groundZones": [
            {"material": material, "minX": x0, "maxX": x1, "minZ": z0, "maxZ": z1}
            for biome, material in GROUND_MATERIAL.items()
            for x0, x1, z0, z1 in [DISTRICTS[ZONE_DISTRICTS[biome]]]
        ]
        + [dict(zip(("material", "minX", "maxX", "minZ", "maxZ"), ("Lava", *LAVA_CELLS), strict=True))],
        "lavaZones": [dict(zip(("minX", "maxX", "minZ", "maxZ", "damage", "interval"), (*LAVA_CELLS, LAVA_DAMAGE, LAVA_INTERVAL), strict=True))],
        "bossPool": BOSS_POOL,
        "minibossPool": MINIBOSS_POOL,
        "edits": build_edits(spawn, boss, shrine_spots),
    }


def artwork() -> Image.Image:
    image = Image.new("RGB", (1080, 720), "#102d31")
    draw = ImageDraw.Draw(image)
    draw.ellipse((730, 70, 990, 330), fill="#d9d6a0")
    draw.polygon([(0, 270), (170, 180), (340, 270), (570, 200), (850, 290), (1080, 205), (1080, 720), (0, 720)], fill="#305c56")
    draw.polygon([(0, 440), (260, 340), (500, 430), (780, 330), (1080, 420), (1080, 720), (0, 720)], fill="#548267")
    draw.polygon([(0, 560), (260, 480), (500, 550), (760, 470), (1080, 530), (1080, 720), (0, 720)], fill="#80a375")
    tiers = [(120, 640, 960, 620, "#4d7a60"), (210, 560, 870, 540, "#5f9068"), (300, 480, 780, 460, "#72a574"), (390, 400, 690, 380, "#86b67e")]
    for left, base, right, _, colour in tiers:
        top = base - 95
        draw.polygon([(left, base), (left + 55, top), (right - 55, top), (right, base)], fill=colour)
        draw.polygon([(left, base), (left + 55, top), (left + 55, top + 22), (left + 18, base)], fill="#3b6450")
    draw.polygon([(465, 305), (615, 305), (640, 400), (440, 400)], fill="#9bc58a")
    path = [(540, 700), (540, 640), (360, 600), (330, 560), (700, 540), (760, 470), (420, 455), (400, 400), (650, 385), (640, 330)]
    draw.line(path, fill="#d0c795", width=14, joint="curve")
    draw.polygon([(505, 305), (505, 215), (518, 215), (518, 232), (534, 232), (534, 210), (550, 210), (550, 232), (568, 232), (568, 222), (582, 222), (582, 305)], fill="#bec6b0")
    draw.polygon([(550, 232), (568, 232), (568, 222), (582, 222), (582, 305), (550, 305)], fill="#899f8d")
    draw.rounded_rectangle((525, 262, 546, 304), radius=10, fill="#24483f")
    for x, y, scale in [(70, 430, 1.4), (200, 470, 1), (990, 480, 1.3), (1050, 410, 1.6), (90, 670, 1.8), (1000, 680, 1.7)]:
        draw.rectangle((x - 8 * scale, y - 30 * scale, x + 8 * scale, y + 65 * scale), fill="#345244")
        draw.polygon([(x, y - 150 * scale), (x - 65 * scale, y - 15 * scale), (x - 38 * scale, y - 24 * scale), (x - 82 * scale, y + 32 * scale), (x + 75 * scale, y + 32 * scale), (x + 38 * scale, y - 25 * scale), (x + 58 * scale, y - 15 * scale)], fill="#214f43")
        draw.polygon([(x, y - 150 * scale), (x, y + 32 * scale), (x - 82 * scale, y + 32 * scale), (x - 38 * scale, y - 24 * scale), (x - 65 * scale, y - 15 * scale)], fill="#386b51")
    draw.rectangle((0, 0, 1080, 140), fill="#102d31")
    draw.text((54, 31), "BRAMBLECROWN HILL", font=ImageFont.load_default(size=56), fill="#f3edcf")
    draw.text((57, 100), "MEADOWS / RIDGES / ONE SPIRAL PATH TO THE SUMMIT", font=ImageFont.load_default(size=18), fill="#a3c5ac")
    return image


def write_assets(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{SLUG}.mblevel.json").write_text(json.dumps(build_level(), indent=2) + "\n", encoding="utf-8")
    image = artwork()
    image.save(output / f"{SLUG}.png")
    image.crop((340, 190, 740, 590)).resize((256, 256), Image.Resampling.LANCZOS).save(output / f"{SLUG}.biome.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "levels")
    write_assets(parser.parse_args().output)


if __name__ == "__main__":
    main()
