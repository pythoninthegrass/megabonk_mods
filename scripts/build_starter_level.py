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
WIDTH, DEPTH = 13, 12
CENTER = 6
SPAWN_CELL = (6, 1)
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
    (5, 4): (0, "west"), (4, 5): (1, "north"), (5, 8): (2, "east"), (8, 7): (3, "south"),
    (2, 2): (-1, "east"), (1, 4): (-1, "north"), (1, 8): (0, "north"), (3, 8): (0, "north"),
    (9, 2): (0, "east"), (10, 7): (1, "north"), (9, 10): (1, "east"), (11, 11): (2, "east"),
    (11, 5): (0, "north"), (12, 5): (0, "north"),
    (11, 3): (0, "west"), (12, 1): (0, "south"),
}
# Flat cells of the hill's spiral ring; the summit sits inside it.
HILL = {
    (4, 4): 1, (6, 4): 0, (7, 4): 0, (8, 4): 0, (4, 6): 2, (4, 7): 2, (4, 8): 2,
    (6, 8): 3, (7, 8): 3, (8, 8): 3, (8, 6): 4, (8, 5): 4,
}
SUMMIT_CELLS = [(x, z) for x in (5, 6, 7) for z in (5, 6, 7)]
DISTRICTS = {
    "spawn meadow": (3, 9, 0, 3), "west gully": (0, 2, 0, 4), "west ridge": (0, 2, 5, 11),
    "north ruins": (3, 9, 9, 11), "east highland": (10, 12, 8, 11), "east pen": (10, 12, 0, 7),
    "spiral": (4, 8, 4, 8),
}
ZONE_DISTRICTS = {"graveyard": "west gully", "dungeon": "north ruins", "hell": "east pen", "desert": "east highland"}
# Terrain materials of the game's own biomes, painted over the Forest ground of the matching district.
GROUND_MATERIAL = {"desert": "m_1_TerrainDesert", "dungeon": "m_crypt_Floor", "hell": "m_TerrainHell"}
LAVA_BANDS = [(11, 11, 2, 2), (11, 11, 4, 4)]
COURT_CELLS = (11, 12, 1, 4)
LAVA_DAMAGE, LAVA_INTERVAL = 3, 0.5
# Enemy names (EEnemy) a stage boss or miniboss spawn is replaced by, drawn from every map's roster.
BOSS_POOL = ["Ent1", "Ent2", "Ent3", "Pharaoh1", "Pharaoh2", "Pharaoh3"]
MINIBOSS_POOL = ["MinibossPig", "MinibossGolem", "MinibossGolemSand", "MinibossScorpion", "Ghostham", "CalciumDad"]
CHESTS = [(0, 0), (0, 11), (6, 11), (12, 11), (12, 0), (4, 7), (12, 9), (8, 1)]
FREE_CHEST = (4, 1)
SHRINE_CELLS = [
    (8, 3), (3, 3), (4, 0), (9, 0),
    (0, 2), (1, 0), (0, 4), (2, 3), (1, 2),
    (0, 6), (2, 6), (1, 10), (2, 11), (0, 8),
    (4, 10), (8, 10), (6, 9), (8, 11),
    (10, 9), (10, 11), (11, 8), (12, 10),
    (10, 0), (10, 4), (10, 6), (11, 6), (12, 7),
]
GUARANTEED_CHARGE_SHRINES = 5
MOAI_RANGE = [3, 5]
SHADY_GUY_RANGE = [2, 3]


def height(x: int, z: int) -> int:
    if (x, z) in SUMMIT_CELLS:
        return 4
    if (x, z) == (10, 1) or COURT_CELLS[0] <= x <= COURT_CELLS[1] and COURT_CELLS[2] <= z <= COURT_CELLS[3]:
        return 0
    if (x, z) in HILL:
        return HILL[x, z]
    if x <= 2:
        return -1 if z <= 4 else int(z >= 9)
    if x >= 10:
        if z <= 7:
            return 1
        return 3 if x == 12 and z == 11 else 2
    return int(z >= 9)


def meadow_rect() -> dict:
    x0, x1, z0, z1 = DISTRICTS["spawn meadow"]
    return {"minX": 40 * (x0 - CENTER) - 20, "maxX": 40 * (x1 - CENTER) + 20, "minZ": 40 * (z0 - CENTER) - 20, "maxZ": 40 * (z1 - CENTER) + 20}


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

    for z in range(2, 4):
        for dz in (-10, 10):
            for side in (-20, 20):
                catalog = ROCK if (z + (dz > 0) + (side > 0)) % 2 else BUSH
                add(catalog, point(6, z, side, dz), rng.randrange(360), 1.5 if catalog == ROCK else 1.8)
    for ruin, x, z, dx, dz, yaw in [(2, 5, 7, 4, -4, 90), (1, 7, 7, -4, -4, 0), (0, 5, 5, 4, 4, 270)]:
        add(RUIN + str(ruin), point(x, z, dx, dz), yaw)
    for x, z, dx, dz in [(3, 7, 0, 0), (9, 7, 0, 0), (4, 3, 12, -12), (8, 3, -12, -12)]:
        add(BUSH, point(x, z, dx, dz), rng.randrange(360), 1.8)

    # North plateau: dungeon sets, one per quarter of the plateau.
    for tile, (x, z) in zip((DUNGEON_TILES[1], DUNGEON_TILES[3]), [(8, 9), (4, 11)], strict=True):
        add(tile, point(x, z), rng.choice((0, 90, 180, 270)), 1, 26)
    # East highland: desert landmarks and houses.
    add(DESERT_LANDMARKS[0], point(10, 11), 200, 0.7 * 6, 30)
    add(DESERT_LANDMARKS[3], point(12, 8), 90, 0.7 * 5, 26)
    add(DESERT_HOUSES[0], point(11, 9, dx=-8), 90, 1.3, 26)
    add(DESERT_HOUSES[1], point(11, 10, dx=-8), 270, 1.3, 26)
    add(DESERT + "3/0", point(10, 8, dx=-12, dz=-12), 0, 3.5, 12)
    add(DESERT + "3/1", point(12, 10, dx=12, dz=12), 0, 3.5, 12)
    for i, z in enumerate((1, 2, 3, 4)):
        for x, dx in ((11, -19.5), (12, 19.5)):
            if (x, z) in ((11, 1), (11, 3), (12, 1)):
                continue
            add(HELL_WALLS[i % 4], point(x, z, dx=dx), 90, 5.5, 14)
    add(HELL_LANDMARK, point(10, 3, dx=-10), 270, 0.8 * 4, 20)
    for x in (11, 12):
        add(HELL_COLUMN, point(x, 6, dx=-14), 0, 5, 14)
    for x, z in [(10, 0), (12, 6), (10, 6)]:
        add(FIRE, point(x, z, dx=10, dz=10), 0, 3.5, 14)
    # West gully: a graveyard gate at the ramp, cobble patches, and the coffin tile.
    add(ARCH, point(1, 3), 90, 2.5, 25)
    add(COFFIN_TILE, point(1, 1), 0, 1, 40)
    for tile, (x, z) in zip(GRAVE_TILES, [(0, 3), (2, 4), (2, 1), (0, 4), (2, 0), (0, 1)], strict=True):
        add(tile, point(x, z, dx=10, dz=10), 0, 1, 12)

    for x in range(WIDTH):
        for z in range(DEPTH):
            if (x, z) in RAMPS or (x, z) == (10, 1) or 4 <= x <= 8 and 4 <= z <= 8 or 4 <= x <= 8 and z <= 3 or COURT_CELLS[0] <= x <= COURT_CELLS[1] and COURT_CELLS[2] <= z <= COURT_CELLS[3]:
                continue
            zone = zone_of(x, z)
            edge = x in (0, WIDTH - 1) or z in (0, DEPTH - 1)
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
    for x in range(WIDTH):
        for z in range(DEPTH):
            cell = {"x": x, "z": z, "height": height(x, z)}
            if (x, z) in RAMPS:
                cell["height"], cell["slope"] = RAMPS[x, z]
            cells.append(cell)

    spawn = point(*SPAWN_CELL, lift=1.925)
    boss = point(6, 6)
    shrine_spots = [point(x, z) for x, z in SHRINE_CELLS]
    return {
        "schemaVersion": 4,
        "gameBuildId": "21750826",
        "title": "Bramblecrown Hill",
        "description": "A bramble-ringed hill with a ruined watchpost on its crown. Follow the fence line to the foot of the hill and climb the spiral path.",
        "mapDescription": "Five visual districts around one tall hill, with Forest gameplay throughout. Explore compact loops for chests and shrines, a walled lava court, or the spiral to the summit. The seed fixes custom shrine plans and boss picks, not combat or loot. No extra packs needed.",
        "baseline": "none", "map": 1, "stageIndex": 0, "tier": 0, "seed": 0, "packs": {},
        "fallDamageFreeHeight": 40,
        "grid": {"width": WIDTH, "depth": DEPTH, "cells": cells},
        "spawn": {"position": spawn, "rotation": [0, 0, 0]},
        "bossSpawner": {"position": boss, "rotation": [0, 180, 0]},
        "shrineSpots": shrine_spots,
        "guaranteedShrineKinds": ["charge"] * GUARANTEED_CHARGE_SHRINES,
        "extraShrines": 2, "extraShrinesMax": 3,
        "extraShrineKinds": ["charge", "magnet", "greed"],
        "shrineKindRanges": {"moai": MOAI_RANGE, "shadyGuy": SHADY_GUY_RANGE},
        "shrineGuarantees": [{"kind": kind, **meadow_rect(), "outside": True} for kind in ("moai", "shadyGuy")],
        "shrineKindSpacing": {"moai": 120},
        "groundZones": [
            {"material": material, "minX": x0, "maxX": x1, "minZ": z0, "maxZ": z1}
            for biome, material in GROUND_MATERIAL.items()
            for x0, x1, z0, z1 in [DISTRICTS[ZONE_DISTRICTS[biome]]]
        ]
        + [dict(zip(("material", "minX", "maxX", "minZ", "maxZ"), ("m_crypt_Floor", *COURT_CELLS), strict=True))]
        + [dict(zip(("material", "minX", "maxX", "minZ", "maxZ"), ("LavaCrypt", *band), strict=True)) for band in LAVA_BANDS],
        "lavaZones": [dict(zip(("minX", "maxX", "minZ", "maxZ", "damage", "interval"), (*band, LAVA_DAMAGE, LAVA_INTERVAL), strict=True)) for band in LAVA_BANDS],
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
    draw.polygon([(790, 650), (810, 570), (950, 570), (970, 650)], fill="#808b83")
    for y in (600, 630):
        draw.rectangle((820, y, 900, y + 12), fill="#ee6731")
    draw.line([(790, 650), (810, 570), (810, 548)], fill="#404c4b", width=12)
    draw.line([(970, 650), (950, 570), (950, 548)], fill="#404c4b", width=12)
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
