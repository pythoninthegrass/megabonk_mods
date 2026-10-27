#!/usr/bin/env python3
"""
Generate levels/thps.mblevel.json: the THPS Warehouse base level on Forest stage 0.

The edit list is derived from docs/thps-warehouse-layout.md. Block-local coordinates are
units from the south-west corner of the inner arena, x east and z north.
"""

import argparse
import json
from pathlib import Path

GRID_SIZE = 15
TILE = 40
HEIGHT_STEP = 20
GRID_ORIGIN = -280

# Inner arena of 3 tiles east by 4 tiles north, wrapped by a one-cell raised ring.
INNER_ORIGIN = (8, 4)
INNER_X = 3
INNER_Z = 4
WALL_LEVELS = 2

# Raised north-east block and the two sloped lanes that climb to it, in inner-cell offsets.
RAISED_X = (0, 1)
RAISED_Z = 3
RAISED_LEVEL = 1
LANE_X = (0, 1)
LANE_Z = 2

SLOPE_NONE = 0
SLOPE_NORTH = 1

# The player is placed at the generated spawn before edits apply, so that cell has to stay floor.
GENERATED_SPAWN_CELL = (10, 7)
BOSS_SPAWN_LOCAL = (100, 120)

BIG_RAIL_LOCAL = (66, 55)
BIG_RAIL_YAW = 90.0
BIG_RAIL_SCALE = 0.75
LEDGE_RAIL_LOCAL = (20, 34)
LEDGE_RAIL_SCALE = 0.4
HIGH_RAIL_LOCAL = (14, 14)
HIGH_RAIL_HEIGHT = 12.0
HIGH_RAIL_SCALE = 0.5

SEED = 20261007
GAME_BUILD_ID = "21750826"
SCHEMA_VERSION = 2

# Object categories and counts the generator spawns on Forest stage 0 at the seed above.
SEED_OBJECT_COUNTS = {
    "BossSpawner": 1,
    "PlayerSpawnPortal": 1,
    "Tree0": 300,
    "Log0": 40,
    "Bush0": 100,
    "rock_small_01": 25,
    "rock_small_05": 24,
    "rock_medium_01": 27,
    "rock_medium_02": 26,
    "rock_medium_03": 28,
    "rock_small_02": 20,
    "Bush1": 100,
    "Boulder": 8,
    "ChargeShrine": 15,
    "GreedShrine": 8,
    "Microwave": 2,
    "PotSmall": 40,
    "PotBig": 15,
    "PotSmallSilver": 6,
    "PotBigSilver": 1,
    "Chest": 46,
    "ShrineMaoi": 4,
    "CursedShrine": 4,
    "MagnetShrine": 3,
    "ChallengeShrine": 3,
    "ForestParticles": 1,
}
SEED_TILE_OBJECTS = 39
KEPT_OBJECT_CATEGORIES = ("BossSpawner", "PlayerSpawnPortal", "ForestParticles")


def local_to_world(x: float, z: float) -> tuple[float, float]:
    x0, z0 = INNER_ORIGIN
    return (
        GRID_ORIGIN + TILE * x0 - TILE // 2 + x,
        GRID_ORIGIN + TILE * z0 - TILE // 2 + z,
    )


def cell_of_local(x: float, z: float) -> tuple[int, int]:
    return int(x // TILE), int(z // TILE)


def inner_cells() -> list[tuple[int, int]]:
    x0, z0 = INNER_ORIGIN
    return [(x0 + dx, z0 + dz) for dz in range(INNER_Z) for dx in range(INNER_X)]


def ring_cells() -> list[tuple[int, int]]:
    x0, z0 = INNER_ORIGIN
    inner = set(inner_cells())
    return [
        (x, z)
        for z in range(z0 - 1, z0 + INNER_Z + 1)
        for x in range(x0 - 1, x0 + INNER_X + 1)
        if (x, z) not in inner
    ]


def edit(op_type: str, payload: dict, target: str = "") -> dict:
    return {"opType": op_type, "target": target, "payload": json.dumps(payload, separators=(",", ":"))}


def inner_height_and_slope(cell: tuple[int, int]) -> tuple[int, int]:
    x0, z0 = INNER_ORIGIN
    dx, dz = cell[0] - x0, cell[1] - z0
    if dz == RAISED_Z and dx in RAISED_X:
        return RAISED_LEVEL, SLOPE_NONE
    if dz == LANE_Z and dx in LANE_X:
        return 0, SLOPE_NORTH
    return 0, SLOPE_NONE


def tile_edits() -> list[dict]:
    ring = set(ring_cells())
    inner = set(inner_cells())
    edits = []
    for z in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            cell = (x, z)
            if cell in ring:
                height, slope = WALL_LEVELS, SLOPE_NONE
            elif cell in inner:
                height, slope = inner_height_and_slope(cell)
            else:
                edits.append(edit("tile.remove", {"x": x, "z": z}))
                continue
            edits.append(edit("tile.setHeight", {"x": x, "z": z, "height": height}))
            edits.append(edit("tile.setSlope", {"x": x, "z": z, "direction": slope}))
    return edits


def clutter_removals() -> list[dict]:
    ids = [f"gen:tileObject:{i:04d}" for i in range(SEED_TILE_OBJECTS)]
    for name, count in SEED_OBJECT_COUNTS.items():
        if name in KEPT_OBJECT_CATEGORIES:
            continue
        ids.extend(f"gen:object:{name}:{i:04d}" for i in range(count))
    return [edit("object.remove", {}, target) for target in ids]


def transform(x: float, y: float, z: float) -> dict:
    return {
        "position": {"x": x, "y": y, "z": z},
        "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
        "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
    }


def spawn_moves() -> list[dict]:
    bx, bz = local_to_world(*BOSS_SPAWN_LOCAL)
    return [edit("object.move", {"newTransform": transform(bx, 0.0, bz)}, "gen:object:BossSpawner:0000")]


def place_rail(catalog_id: str, local: tuple[float, float], y: float, yaw: float, scale: float) -> dict:
    wx, wz = local_to_world(*local)
    return edit(
        "object.place",
        {
            "catalogId": catalog_id,
            "position": {"x": wx, "y": y, "z": wz},
            "rotation": {"x": 0.0, "y": yaw, "z": 0.0},
            "scale": {"x": scale, "y": scale, "z": scale},
        },
    )


def rail_edits() -> list[dict]:
    return [
        place_rail("interactable/rail/1", BIG_RAIL_LOCAL, 0.0, BIG_RAIL_YAW, BIG_RAIL_SCALE),
        place_rail("interactable/rail/0", LEDGE_RAIL_LOCAL, 0.0, 0.0, LEDGE_RAIL_SCALE),
        place_rail("interactable/rail/0", HIGH_RAIL_LOCAL, HIGH_RAIL_HEIGHT, 0.0, HIGH_RAIL_SCALE),
    ]


def build_level() -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "gameBuildId": GAME_BUILD_ID,
        "map": 1,
        "stageIndex": 0,
        "tier": 0,
        "seed": SEED,
        "packs": {},
        "edits": tile_edits() + clutter_removals() + spawn_moves() + rail_edits(),
    }


def write_level(path: Path) -> None:
    path.write_text(json.dumps(build_level(), indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", nargs="?", type=Path, default=Path("levels/thps.mblevel.json"))
    args = parser.parse_args()
    write_level(args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
