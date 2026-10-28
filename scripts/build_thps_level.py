#!/usr/bin/env python3
"""
Generate levels/thps.mblevel.json: the THPS Warehouse base level on Forest stage 0.

The edit list is derived from docs/thps-warehouse-layout.md. Block-local coordinates are
units from the south-west corner of the inner arena, x east and z north.
"""

import argparse
import json
import math
from pathlib import Path
from typing import NamedTuple

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

PLAYER_SPAWN_LOCAL = (100, 137)
SPAWN_CLEARANCE = 10
BIG_RAIL_LOCAL = (66, 55)
BIG_RAIL_YAW = 90.0
BIG_RAIL_SCALE = 0.75
LEDGE_RAIL_LOCAL = (12, 33)
LEDGE_RAIL_SCALE = 0.4
HIGH_RAIL_LOCAL = (3, 12)
HIGH_RAIL_SCALE = 0.5

PACK_ID = "thps"
PACK_VERSION = "1.0.0"
MANIFEST_PATH = Path(__file__).resolve().parent.parent / "unity" / "pack-authoring" / "packs" / PACK_ID / "manifest.json"
STRUCTURE_ASSETS = ("QuarterPipe", "Kicker", "Block", "Taxi", "Corridor")

# Fraction of a quarter pipe's run that is the curved transition; the rest is a straight slope. Mirrors ThpsPack.cs.
QUARTER_PIPE_TRANSITION = 0.4
# The player's jump apex above the floor (the highest sample was 7.8), and PlayerMovement.maxSlopeAngle (45) less a margin.
PLAYER_JUMP_APEX = 7.8
MAX_RAMP_SLOPE_DEGREES = 41

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


class Structure(NamedTuple):
    code: str
    asset: str
    x: float
    z: float
    yaw: float
    width: float
    rise: float
    depth: float
    base_y: float = 0.0


# Positions are block-local centres of the footprint at its base. width, rise and depth scale the unit prefab; a ramp rises toward its local +z, so yaw 0 climbs north, 90 east, 180 south and 270 west.
STRUCTURES = (
    Structure("M1", "QuarterPipe", 9, 12, 270, 24, 12, 18),
    Structure("M2", "Block", 7, 33, 0, 14, 5.5, 14),
    Structure("M3", "Taxi", 34, 25, 90, 8, 5, 20),
    Structure("M4a", "QuarterPipe", 33, 35.5, 180, 30, 6, 9),
    Structure("M4b", "QuarterPipe", 33, 54.5, 0, 30, 6, 9),
    Structure("M5", "Corridor", 10, 66, 0, 18, 13, 28, 13),
    Structure("M6", "QuarterPipe", 34, 71, 0, 20, 12, 18),
    Structure("M7", "QuarterPipe", 58, 74, 0, 12, 8, 12),
    Structure("M8", "QuarterPipe", 77, 72.5, 0, 18, 10, 15),
    Structure("M9", "Block", 101, 103, 0, 38, 6, 24),
    Structure("M9b", "QuarterPipe", 111, 103, 90, 24, 12, 18, 6),
    Structure("M10", "QuarterPipe", 67, 4.5, 180, 20, 6, 9),
    Structure("M10b", "Block", 60, 15, 0, 22, 4, 10),
    Structure("M11", "Block", 99, 67, 0, 18, 4, 12),
    Structure("M12a", "Kicker", 87, 46, 180, 12, 4.4, 6.3),
    Structure("M12b", "Kicker", 87, 32, 0, 12, 2.6, 3.7),
)


class Collectible(NamedTuple):
    code: str
    catalog_id: str
    x: float
    z: float
    y: float
    stands_on: str | None = None


# Block-local positions; y is the surface the item stands on. Items on a lane cell use the lane's slope height.
COLLECTIBLES = (
    Collectible("R1", "interactable/chest", 8, 34, 5.5, "M2"),
    Collectible("R2", "interactable/chest", 61, 16, 4, "M10b"),
    Collectible("R3", "interactable/chest", 98, 67, 4, "M11"),
    Collectible("R4", "interactable/chest", 86, 100, 6, "M9"),
    Collectible("R5", "interactable/chest", 20, 88, 4),
    Collectible("S", "forest/shrines/0", 84, 40, 0),
    Collectible("K", "forest/shrines/1", 33, 2, 0),
    Collectible("A", "forest/shrines/2", 34, 26, 5, "M3"),
    Collectible("T", "forest/shrines/3", 27, 60.5, 0),
    Collectible("E", "forest/shrines/4", 86, 108, 6, "M9"),
    Collectible("Tape", "interactable/chestFree", 11, 67, 13, "M5"),
    Collectible("100N", "interactable/chestFree", 31, 99, 9.5),
    Collectible("100E", "interactable/chestFree", 56, 99, 9.5),
    Collectible("100S", "interactable/chestFree", 82, 13, 0),
)
HIGH_RAIL_HEIGHT = next(s.rise for s in STRUCTURES if s.code == "M1")
LEDGE_RAIL_HEIGHT = next(s.rise for s in STRUCTURES if s.code == "M2")


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
    return [(x, z) for z in range(z0 - 1, z0 + INNER_Z + 1) for x in range(x0 - 1, x0 + INNER_X + 1) if (x, z) not in inner]


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
        place_rail("interactable/rail/0", LEDGE_RAIL_LOCAL, LEDGE_RAIL_HEIGHT, 0.0, LEDGE_RAIL_SCALE),
        place_rail("interactable/rail/0", HIGH_RAIL_LOCAL, HIGH_RAIL_HEIGHT, 0.0, HIGH_RAIL_SCALE),
    ]


def footprint(s: Structure) -> tuple[float, float, float, float]:
    """Block-local (x0, x1, z0, z1) bounds of a structure whose yaw is a multiple of 90."""
    half_x, half_z = (s.width / 2, s.depth / 2) if s.yaw % 180 == 0 else (s.depth / 2, s.width / 2)
    return s.x - half_x, s.x + half_x, s.z - half_z, s.z + half_z


def end_slope_degrees(s: Structure) -> float:
    """Steepest slope of a QuarterPipe or Kicker after scaling."""
    run_ratio = s.rise / s.depth
    if s.asset == "QuarterPipe":
        run_ratio /= 1 - QUARTER_PIPE_TRANSITION / 2
    return math.degrees(math.atan(run_ratio))


def structure_edits() -> list[dict]:
    edits = []
    for s in STRUCTURES:
        wx, wz = local_to_world(s.x, s.z)
        edits.append(
            edit(
                "object.place",
                {
                    "catalogId": f"bundle:{PACK_ID}/{s.asset}",
                    "position": {"x": wx, "y": s.base_y, "z": wz},
                    "rotation": {"x": 0.0, "y": s.yaw, "z": 0.0},
                    "scale": {"x": s.width, "y": s.rise, "z": s.depth},
                },
            )
        )
    return edits


def surface_height(s: Structure) -> float:
    """Height of the surface an item stands on: a block or taxi top, or a corridor floor."""
    return s.base_y if s.asset == "Corridor" else s.base_y + s.rise


def ground_height(z: float, x: float) -> float:
    """Ground height at a block-local point: the north lanes slope up one level, everything else is flat."""
    lane_start = LANE_Z * TILE
    if x < (LANE_X[-1] + 1) * TILE and lane_start <= z < lane_start + TILE:
        return HEIGHT_STEP * (z - lane_start) / TILE
    return 0.0


def collectible_edits() -> list[dict]:
    edits = []
    for c in COLLECTIBLES:
        wx, wz = local_to_world(c.x, c.z)
        edits.append(
            edit(
                "object.place",
                {
                    "catalogId": c.catalog_id,
                    "position": {"x": wx, "y": c.y, "z": wz},
                    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
                },
            )
        )
    return edits


def build_level() -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "gameBuildId": GAME_BUILD_ID,
        "map": 1,
        "stageIndex": 0,
        "tier": 0,
        "seed": SEED,
        "packs": {PACK_ID: PACK_VERSION},
        "edits": tile_edits() + clutter_removals() + spawn_moves() + rail_edits() + structure_edits() + collectible_edits(),
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
