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

# Inner arena of 4 tiles east by 7 tiles north, wrapped by a one-cell raised ring.
INNER_ORIGIN = (8, 4)
INNER_X = 4
INNER_Z = 7
WALL_LEVELS = 2
# Inner tiles sit below the Warehouse's sunken floor areas so they do not show through.
INNER_LEVEL = -1

SLOPE_NONE = 0

# The player is placed at the generated spawn before edits apply, so that cell has to stay floor.
GENERATED_SPAWN_CELL = (10, 7)
BOSS_SPAWN_LOCAL = (150, 167)
BOSS_SPAWN_Y = 15.6
BOSS_SPAWN_SCALE = 0.4
BOSS_SPAWN_YAW = 90.0
BOSS_HIDDEN_CHILDREN = ["BottomPiece", "Collider"]
PLAYER_START = [109, 38, -120]

PLAYER_SPAWN_LOCAL = (100, 137)
SPAWN_CLEARANCE = 10
BIG_RAIL_LOCAL = (66, 55)
BIG_RAIL_YAW = 90.0
BIG_RAIL_SCALE = 0.75
LEDGE_RAIL_LOCAL = (12, 33)
LEDGE_RAIL_SCALE = 0.4
HIGH_RAIL_LOCAL = (3, 12)
HIGH_RAIL_SCALE = 0.5

# Game rails laid hidden along the Warehouse mesh's own rail bar (the straight run, then the bend), so the bar keeps its look and the game rails supply the grind. Each is (world position, yaw, scale), tuned against the bar.
MESH_RAIL_CATALOG_ID = "interactable/rail/0"
# rail/0 is a straight bar this long at scale 1.
RAIL0_LENGTH = 28
MESH_RAIL_HEIGHT = -1.25
MESH_RAILS = (
    ((75, MESH_RAIL_HEIGHT, 28.13), 90.0, 1.786),
    ((78.3, MESH_RAIL_HEIGHT, 56.85), 310.5, 0.352),
    # The rod the SKATEBOARDING banner hangs from, then the rail on the deck at the east wall.
    ((129.64, 22.88, 120.84), 0.0, 0.954),
    ((175.66, 3.88, 61.295), 90.0, 0.955),
)

# The half pipe lips reach 85 degrees, past the game's 45 degree slope limit.
MAX_SLOPE_ANGLE = 88

PACK_ID = "thps"
PACK_VERSION = "2.0.10"
MANIFEST_PATH = Path(__file__).resolve().parent.parent / "unity" / "pack-authoring" / "packs" / PACK_ID / "manifest.json"
STRUCTURE_ASSETS = ("QuarterPipe", "Kicker", "Block", "Taxi", "Corridor")
WAREHOUSE_ASSET = "Warehouse"
# The Warehouse floor sits this far above the level-0 tiles so it covers them.
WAREHOUSE_LIFT = 0.5

# 4.4 level units per metre, and the 18 m per OBJ unit calibration in docs/thps-warehouse.md.
UNITS_PER_METRE = 4.4
METRES_PER_OBJ_UNIT = 18
WAREHOUSE_SCALE = UNITS_PER_METRE * METRES_PER_OBJ_UNIT
# Horizontal extent of warehouse.obj in OBJ units; the prefab is centred on it.
WAREHOUSE_OBJ_WIDTH = 2.518555 - 0.519531
WAREHOUSE_OBJ_DEPTH = 3.533447 - 0.398926

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
    yaw: float = 0.0


# Chest, shrine and merchant prefabs are authored lying down, so they stand up at pitch 270 (a lane tilts them back by its slope).
UPRIGHT_PITCH = 270.0

# Block-local positions; y is the surface the item stands on. Items on a lane cell use the lane's slope height.
COLLECTIBLES = (
    Collectible("R1", "interactable/chest", 8, 34, 5.5, "M2"),
    Collectible("R2", "interactable/chest", 61, 16, 4, "M10b"),
    Collectible("R3", "interactable/chest", 98, 67, 4, "M11"),
    Collectible("R4", "interactable/chest", 86, 100, 6, "M9"),
    Collectible("R5", "interactable/chest", 20, 88, 0),
    Collectible("S", "forest/shrines/0", 84, 40, 0),
    Collectible("K", "forest/shrines/1", 33, 2, 0),
    Collectible("A", "forest/shrines/2", 34, 26, 5, "M3"),
    Collectible("T", "forest/shrines/3", 27, 60.5, 0),
    Collectible("E", "forest/shrines/4", 86, 108, 6, "M9"),
    Collectible("Tape", "interactable/chestFree", 11, 67, 13, "M5"),
    Collectible("100N", "interactable/chestFree", 31, 99, 0),
    Collectible("100E", "interactable/chestFree", 56, 99, 0),
    Collectible("100S", "interactable/chestFree", 82, 13, 0),
)
HIGH_RAIL_HEIGHT = next(s.rise for s in STRUCTURES if s.code == "M1")
LEDGE_RAIL_HEIGHT = next(s.rise for s in STRUCTURES if s.code == "M2")


def warehouse_footprint() -> tuple[float, float]:
    """Width (x) and depth (z) of the scaled Warehouse in level units."""
    return WAREHOUSE_OBJ_WIDTH * WAREHOUSE_SCALE, WAREHOUSE_OBJ_DEPTH * WAREHOUSE_SCALE


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


def tile_edits() -> list[dict]:
    ring = set(ring_cells())
    inner = set(inner_cells())
    edits = []
    for z in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            cell = (x, z)
            if cell in ring:
                height = WALL_LEVELS
            elif cell in inner:
                height = INNER_LEVEL
            else:
                edits.append(edit("tile.remove", {"x": x, "z": z}))
                continue
            edits.append(edit("tile.setHeight", {"x": x, "z": z, "height": height}))
            edits.append(edit("tile.setSlope", {"x": x, "z": z, "direction": SLOPE_NONE}))
    return edits


def clutter_removals() -> list[dict]:
    ids = [f"gen:tileObject:{i:04d}" for i in range(SEED_TILE_OBJECTS)]
    for name, count in SEED_OBJECT_COUNTS.items():
        if name in KEPT_OBJECT_CATEGORIES:
            continue
        ids.extend(f"gen:object:{name}:{i:04d}" for i in range(count))
    return [edit("object.remove", {}, target) for target in ids]


def transform(x: float, y: float, z: float, scale: float = 1.0, yaw: float = 0.0) -> dict:
    return {
        "position": {"x": x, "y": y, "z": z},
        "rotation": {"x": 0.0, "y": yaw, "z": 0.0},
        "scale": {"x": scale, "y": scale, "z": scale},
    }


def spawn_moves() -> list[dict]:
    bx, bz = local_to_world(*BOSS_SPAWN_LOCAL)
    payload = {"newTransform": transform(bx, BOSS_SPAWN_Y, bz, BOSS_SPAWN_SCALE, BOSS_SPAWN_YAW), "hiddenChildren": BOSS_HIDDEN_CHILDREN}
    return [edit("object.move", payload, "gen:object:BossSpawner:0000")]


def mesh_rail_edits() -> list[dict]:
    return [
        edit(
            "object.place",
            {
                "catalogId": MESH_RAIL_CATALOG_ID,
                "position": {"x": x, "y": y, "z": z},
                "rotation": {"x": 0.0, "y": yaw, "z": 0.0},
                "scale": {"x": scale, "y": scale, "z": scale},
                "hidden": True,
            },
        )
        for (x, y, z), yaw, scale in MESH_RAILS
    ]


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
        *mesh_rail_edits(),
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


def warehouse_edits() -> list[dict]:
    wx, wz = local_to_world(INNER_X * TILE / 2, INNER_Z * TILE / 2)
    return [
        edit(
            "object.place",
            {
                "catalogId": f"bundle:{PACK_ID}/{WAREHOUSE_ASSET}",
                "position": {"x": wx, "y": WAREHOUSE_LIFT, "z": wz},
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                "scale": {"x": WAREHOUSE_SCALE, "y": WAREHOUSE_SCALE, "z": WAREHOUSE_SCALE},
            },
        )
    ]


def surface_height(s: Structure) -> float:
    """Height of the surface an item stands on: a block or taxi top, or a corridor floor."""
    return s.base_y if s.asset == "Corridor" else s.base_y + s.rise


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
                    "rotation": {"x": UPRIGHT_PITCH, "y": c.yaw, "z": 0.0},
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
        "noGrass": True,
        "playerStart": PLAYER_START,
        "maxSlopeAngle": MAX_SLOPE_ANGLE,
        "edits": tile_edits() + clutter_removals() + spawn_moves() + rail_edits() + warehouse_edits() + collectible_edits(),
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
