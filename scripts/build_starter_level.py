#!/usr/bin/env python3
"""Build Mosswatch Hollow and its original selection artwork using no extracted assets."""

import argparse
import json
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SPAWN_CELL = (5, 1)
TREE = "forest/stage0/randomMapObjects/0/0"
LOG = "forest/stage0/randomMapObjects/1/0"
BUSH = "forest/stage0/randomMapObjects/2/0"
ROCK = "forest/stage0/randomMapObjects/3/1"
RUIN = "forest/stage0/stageTilePrefabs/flat/"
RAMPS = {
    (1, 2): (0, "north"), (2, 2): (0, "north"),
    (3, 4): (0, "west"), (3, 6): (0, "west"),
    (5, 7): (0, "north"), (8, 7): (0, "north"),
    (1, 7): (1, "north"), (2, 7): (1, "north"),
    (3, 9): (1, "west"), (3, 10): (1, "west"),
}


def height(x: int, z: int) -> int:
    if x <= 2 and z >= 8:
        return 2
    return int((x <= 2 and z >= 3) or z >= 8)


def point(x: int, z: int, dx: float = 0, dz: float = 0, lift: float = 0) -> list[float]:
    return [40 * (x - 5) + dx, 20 * height(x, z) + lift, 40 * (z - 5) + dz]


def placement(index: int, catalog: str, position: list[float], yaw: float = 0, scale: float = 1) -> dict:
    payload = {
        "catalogId": catalog,
        "position": dict(zip(("x", "y", "z"), position, strict=True)),
        "rotation": {"x": 270 if catalog in (TREE, LOG, BUSH) else 0, "y": yaw, "z": 0},
        "scale": dict.fromkeys(("x", "y", "z"), scale),
    }
    return {"opType": "object.place", "target": f"placement:{index}", "payload": json.dumps(payload, separators=(",", ":"))}


def build_level() -> dict:
    cells = []
    for x in range(11):
        for z in range(11):
            cell = {"x": x, "z": z, "height": height(x, z)}
            if (x, z) in RAMPS:
                cell["height"], cell["slope"] = RAMPS[x, z]
            cells.append(cell)

    edits = []

    def add(catalog, position, yaw=0, scale=1):
        edits.append(placement(len(edits), catalog, position, yaw, scale))

    spawn = point(*SPAWN_CELL, lift=1.925)
    boss = point(2, 8)
    add(ROCK, point(5, 1, dx=12, dz=12), 20, 2.5)
    chest_cells = [(5, 2), (1, 5), (6, 5), (9, 4), (9, 9), (5, 9), (0, 9), (8, 1)]
    for x, z in chest_cells:
        add("interactable/chest", point(x, z, lift=0.5), (x * 47 + z * 13) % 360)
    add("interactable/chestFree", point(4, 1, lift=0.5), 135)
    shrine_cells = [(2, 4), (4, 5), (7, 3), (9, 6), (7, 9), (1, 9)]
    shrine_spots = [point(x, z) for x, z in shrine_cells]
    add(RUIN + "0", point(0, 10, dx=-5, dz=0), 90)
    add(RUIN + "1", point(2, 10, dx=5, dz=2), 180)
    add(RUIN + "2", point(0, 8, dx=-6, dz=-4), 0)
    add(RUIN + "1", point(6, 10, dx=10, dz=0), 45)
    reserved = [spawn, boss, *shrine_spots, *[point(x, z) for x, z in chest_cells], point(4, 1), point(5, 1, dx=12, dz=12)]
    rng = random.Random(481)
    for x in range(11):
        for z in range(11):
            if (x, z) in RAMPS or (x <= 2 and z >= 8):
                continue
            if 3 <= x <= 8 and z <= 2 or 4 <= x <= 7 and 3 <= z <= 6 or x >= 8 and 3 <= z <= 6:
                continue
            for n in range(3 if x == 0 or z == 10 else 2):
                dx, dz = rng.choice((-12, 12)), rng.choice((-12, 12))
                position = point(x, z, dx, dz)
                if any(math.dist((position[0], position[2]), (p[0], p[2])) < 19 for p in reserved):
                    continue
                catalog = TREE if n == 0 else rng.choice((TREE, BUSH, ROCK))
                scale = 2.5 if catalog == TREE else 1.8
                add(catalog, position, rng.randrange(360), round(scale * rng.uniform(0.8, 1.25), 3))
                reserved.append(position)
    for x, z, dx, dz, yaw in [(4, 3, -12, 12, 30), (7, 6, 12, -12, 120), (9, 2, 0, 8, 65)]:
        add(LOG, point(x, z, dx, dz), yaw)
    for x, z, dx, dz in [(4, 4, -12, -12), (7, 5, 12, 10), (9, 5, -10, -10), (6, 2, 10, 12)]:
        add(ROCK, point(x, z, dx, dz), 35 * x, 3)
    for x, z, dx, dz in [(4, 3, -18, -10), (6, 3, 18, -10), (4, 5, -18, 10), (6, 5, 18, 10)]:
        add(TREE, point(x, z, dx, dz), rng.randrange(360), 2.3)
        add(BUSH, point(x, z, dx + 8, dz - 6), rng.randrange(360), 1.8)

    return {
        "schemaVersion": 4,
        "gameBuildId": "21750826",
        "title": "Mosswatch Hollow",
        "description": "A quiet hollow beneath a ruined watchpost. Follow the ridges, find the shrines, and leave yourself a way out.",
        "mapDescription": "A handcrafted woodland of open clearings, wooded ridges and mossy ruins. A first adventure, and a first level to make your own. No extra packs needed.",
        "baseline": "none", "map": 1, "stageIndex": 0, "tier": 0, "seed": 0, "packs": {},
        "grid": {"width": 11, "depth": 11, "cells": cells},
        "spawn": {"position": spawn, "rotation": [0, 0, 0]},
        "bossSpawner": {"position": boss, "rotation": [0, 180, 0]},
        "shrineSpots": shrine_spots,
        "guaranteedShrineKinds": ["charge", "charge"],
        "extraShrines": 2, "extraShrinesMax": 3,
        "extraShrineKinds": ["charge", "magnet", "balance", "greed"],
        "edits": edits,
    }


def artwork() -> Image.Image:
    image = Image.new("RGB", (1080, 720), "#102d31")
    draw = ImageDraw.Draw(image)
    draw.ellipse((650, 58, 950, 358), fill="#d9d6a0")
    draw.polygon([(0, 240), (170, 140), (340, 240), (570, 165), (850, 270), (1080, 175), (1080, 720), (0, 720)], fill="#305c56")
    draw.polygon([(0, 390), (260, 280), (500, 380), (780, 280), (1080, 380), (1080, 720), (0, 720)], fill="#548267")
    draw.polygon([(0, 520), (260, 410), (500, 505), (760, 390), (1080, 460), (1080, 720), (0, 720)], fill="#80a375")
    draw.polygon([(380, 720), (530, 530), (700, 450), (820, 435), (750, 490), (640, 570), (580, 720)], fill="#d0c795")
    draw.polygon([(693, 352), (693, 206), (711, 206), (711, 226), (731, 226), (731, 200), (750, 200), (750, 226), (772, 226), (772, 212), (790, 212), (790, 369)], fill="#bec6b0")
    draw.polygon([(750, 226), (772, 226), (772, 212), (790, 212), (790, 369), (750, 359)], fill="#899f8d")
    draw.rounded_rectangle((722, 285, 749, 358), radius=13, fill="#24483f")
    draw.rectangle((708, 253, 719, 272), fill="#30584a")
    draw.line([(697, 326), (718, 310), (714, 285)], fill="#4b7658", width=8)
    for x, y, scale in [(100, 400, 1.4), (245, 430, 1), (375, 350, 0.8), (940, 480, 1.3), (1040, 410, 1.6), (100, 670, 1.8)]:
        draw.rectangle((x - 8 * scale, y - 30 * scale, x + 8 * scale, y + 65 * scale), fill="#345244")
        draw.polygon([(x, y - 150 * scale), (x - 65 * scale, y - 15 * scale), (x - 38 * scale, y - 24 * scale), (x - 82 * scale, y + 32 * scale), (x + 75 * scale, y + 32 * scale), (x + 38 * scale, y - 25 * scale), (x + 58 * scale, y - 15 * scale)], fill="#214f43")
        draw.polygon([(x, y - 150 * scale), (x, y + 32 * scale), (x - 82 * scale, y + 32 * scale), (x - 38 * scale, y - 24 * scale), (x - 65 * scale, y - 15 * scale)], fill="#386b51")
    draw.rectangle((0, 0, 1080, 140), fill="#102d31")
    draw.text((54, 31), "MOSSWATCH HOLLOW", font=ImageFont.load_default(size=56), fill="#f3edcf")
    draw.text((57, 100), "WOODLAND RIDGES / OPEN CLEARINGS / FORGOTTEN RUINS", font=ImageFont.load_default(size=18), fill="#a3c5ac")
    return image


def write_assets(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "mosswatch-hollow.mblevel.json").write_text(json.dumps(build_level(), indent=2) + "\n", encoding="utf-8")
    image = artwork()
    image.save(output / "mosswatch-hollow.png")
    image.crop((600, 145, 1000, 545)).resize((256, 256), Image.Resampling.LANCZOS).save(output / "mosswatch-hollow.biome.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "levels")
    write_assets(parser.parse_args().output)


if __name__ == "__main__":
    main()
