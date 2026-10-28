#!/usr/bin/env python3
"""
Generate levels/thps.mblevel.json: the THPS Warehouse base level on Forest stage 0.

The edit list is derived from docs/thps-warehouse-layout.md. Block-local coordinates are
units from the south-west corner of the inner arena, x east and z north.
"""

import argparse
import json
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

# Game rails laid hidden along the Warehouse mesh's own rail bar (the straight run, then the bend), so the bar keeps its look and the game rails supply the grind. Each is (world position, yaw, scale), tuned against the bar.
MESH_RAIL_CATALOG_ID = "interactable/rail/0"
# rail/0 is a straight bar this long at scale 1.
RAIL0_LENGTH = 28
MESH_RAIL_HEIGHT = -1.25
# Height of rail/0's bar above its pivot per unit of scale, from the first mesh rail: bar centre 3.3 at pivot -1.25 and scale 1.786.
RAIL0_BAR_HEIGHT = 2.55
MESH_RAILS = (
    ((75, MESH_RAIL_HEIGHT, 28.13), 90.0, 1.786),
    ((78.3, 3.3 - RAIL0_BAR_HEIGHT * 0.352, 56.85), 310.5, 0.352),
    # The rod the SKATEBOARDING banner hangs from, then the rail on the deck at the east wall.
    ((129.64, 27.43 - RAIL0_BAR_HEIGHT * 0.954, 120.84), 0.0, 0.954),
    ((175.66, 8.43 - RAIL0_BAR_HEIGHT * 0.955, 61.295), 90.0, 0.955),
)

# The half pipe lips reach 85 degrees, past the game's 45 degree slope limit.
MAX_SLOPE_ANGLE = 88

PACK_ID = "thps"
PACK_VERSION = "2.0.19"
MANIFEST_PATH = Path(__file__).resolve().parent.parent / "unity" / "pack-authoring" / "packs" / PACK_ID / "manifest.json"
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
# Uncloned decoration roots (ruined towers, crates, pillars, dead trees) the tile prefabs spawn at the seed above, indexed as gen:scenery:<name>:<n>.
SEED_SCENERY_COUNTS = {
    "Castle": 14,
    "Castle (1)": 6,
    "CastleLying": 3,
    "Crate (1)": 12,
    "Crate (2)": 10,
    "Cube": 2,
    "Cube (1)": 4,
    "Cube (3)": 9,
    "Pillar": 4,
    "Pillar (1)": 4,
    "Ruins (1)": 8,
    "Tree": 6,
}
KEPT_OBJECT_CATEGORIES = ("BossSpawner", "PlayerSpawnPortal", "ForestParticles")


class Collectible(NamedTuple):
    code: str
    catalog_id: str
    x: float
    z: float
    y: float
    yaw: float = 0.0


# Chest, shrine and merchant prefabs are authored lying down, so they stand up at pitch 270 (a lane tilts them back by its slope).
UPRIGHT_PITCH = 270.0

# Block-local positions and heights from the old hand-built layout; they are not yet anchored to the Warehouse mesh.
COLLECTIBLES = (
    Collectible("R1", "interactable/chest", 8, 34, 5.5),
    Collectible("R2", "interactable/chest", 61, 16, 4),
    Collectible("R3", "interactable/chest", 98, 67, 4),
    Collectible("R4", "interactable/chest", 86, 100, 6),
    Collectible("R5", "interactable/chest", 20, 88, 0),
    Collectible("S", "forest/shrines/0", 84, 40, 0),
    Collectible("K", "forest/shrines/1", 33, 2, 0),
    Collectible("A", "forest/shrines/2", 34, 26, 5),
    Collectible("T", "forest/shrines/3", 27, 60.5, 0),
    Collectible("E", "forest/shrines/4", 86, 108, 6),
    Collectible("Tape", "interactable/chestFree", 11, 67, 13),
    Collectible("100N", "interactable/chestFree", 31, 99, 0),
    Collectible("100E", "interactable/chestFree", 56, 99, 0),
    Collectible("100S", "interactable/chestFree", 82, 13, 0),
)


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
    for name, count in SEED_SCENERY_COUNTS.items():
        ids.extend(f"gen:scenery:{name}:{i:04d}" for i in range(count))
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


def rail_edits() -> list[dict]:
    return mesh_rail_edits()


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
