#!/usr/bin/env python3
"""
Generate levels/thps.mblevel.json: the THPS Warehouse base level on Forest stage 0.

The edit list is derived from docs/thps-warehouse-layout.md. Block-local coordinates are
units from the south-west corner of the inner arena, x east and z north.
"""

import argparse
import json
import math
import warehouse_surface as ws
from functools import cache
from pathlib import Path
from typing import NamedTuple

GRID_SIZE = 15
TILE = 40
HEIGHT_STEP = 20
GRID_ORIGIN = -280

# The Warehouse footprint: 4 tiles east by 7 tiles north. The tile grid keeps only the generated
# spawn cell (the player is placed there before the edits apply); everything else is removed, so the
# Warehouse mesh floats like a native island and its own walls enclose the arena.
INNER_ORIGIN = (8, 4)
INNER_X = 4
INNER_Z = 7
# The kept tile sits below the Warehouse's sunken floor areas so it cannot show through.
INNER_LEVEL = -1

SLOPE_NONE = 0

# The player is placed at the generated spawn before edits apply, so that cell has to stay floor.
GENERATED_SPAWN_CELL = (10, 7)
# Authored rather than derived: with one hidden tile left, the mod's tile-derived floor would sit 40 under
# it, deep enough for a body to rest on the mesh's outer skirt above it and stay unkillable.
KILL_FLOOR_MARGIN_BELOW_KEPT_TILE = 15.0
KILL_FLOOR_Y = INNER_LEVEL * HEIGHT_STEP - KILL_FLOOR_MARGIN_BELOW_KEPT_TILE
# The boss portal stands on the flat Warehouse floor at the south deck of the main half pipe, so the boss
# spawns where the player can reach it. Its drop starts under the hanging box above the pipe, so the box
# that used to hold the portal can never catch it.
BOSS_SPAWN_LOCAL = (130, 205)
BOSS_SPAWN_DROP_FROM = 12.0
BOSS_SPAWN_SCALE = 0.4
BOSS_SPAWN_YAW = 90.0
BOSS_HIDDEN_CHILDREN = ["BottomPiece", "Collider"]
PLAYER_START = [109, 38, -116]

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

# Coping edges, each (start, end) on a run from warehouse_surface.lip_runs: the main half pipe's two lips and the diagonal each turns into at its west end, then the tops of the wall quarter pipes. A rail/0 is laid along each so the lips grind.
MAIN_PIPE_LIPS = (
    ((119.78, 5.76, 8.59), (178.95, 5.76, 8.59)),
    ((119.78, 5.76, 43.81), (178.95, 5.76, 43.81)),
    ((119.78, 5.76, 8.59), (100.06, 0.5, 3.51)),
    ((119.78, 5.76, 43.81), (100.06, 0.5, 48.87)),
)
# The tiered quarter pipes along the north wall, then the curved ones along the south and east walls, which wind round a U-shaped pocket near (80, 8.56, 86); the pocket's rounded tip is two chords, since the mesh's four 2.5 unit edges there are shorter than the handoff's search radius.
WALL_PIPE_LIPS = (
    ((40.89, 8.56, -27.1), (80.34, 8.56, -27.1)),
    ((100.06, 8.56, -27.1), (119.78, 8.56, -27.1)),
    ((139.5, 8.56, -27.1), (178.95, 8.56, -27.1)),
    ((40.89, 16.63, -70.03), (80.34, 16.63, -70.03)),
    ((21.17, 8.56, 101.06), (64.48, 8.56, 101.06)),
    ((64.48, 8.56, 101.06), (70.13, 8.56, 100.29)),
    ((70.13, 8.56, 100.29), (76.43, 8.56, 93.98)),
    ((76.43, 8.56, 93.98), (77.05, 8.56, 88.32)),
    ((77.05, 8.56, 88.32), (80.34, 8.56, 85.03)),
    ((80.34, 8.56, 85.03), (83.62, 8.56, 88.32)),
    ((83.62, 8.56, 88.32), (83.62, 8.56, 107.88)),
    ((83.62, 8.56, 107.88), (84.24, 8.56, 113.7)),
    ((84.24, 8.56, 113.7), (90.54, 8.56, 120.01)),
    ((90.54, 8.56, 120.01), (96.19, 8.56, 120.63)),
    ((96.19, 8.56, 120.63), (162.92, 8.56, 120.63)),
    ((162.92, 8.56, 120.63), (168.74, 8.56, 120.01)),
    ((168.74, 8.56, 120.01), (175.04, 8.56, 113.7)),
    ((175.04, 8.56, 113.7), (175.66, 8.56, 108.04)),
    ((175.66, 8.56, 79.77), (175.66, 8.56, 108.04)),
)
# The top edge of the Shorty's ledge along the west wall, from the kicker end near (44, 2, 5) round its diagonal to the wall near (22, 2, 60); it is a deck over a vertical face, not a ramp lip.
LEDGE_LIPS = (
    ((40.89, 3.79, 3.51), (40.89, 3.79, 8.11)),
    ((40.89, 3.79, 8.11), (25.77, 3.79, 26.19)),
    ((25.77, 3.79, 26.19), (25.77, 3.79, 48.87)),
    ((25.77, 3.79, 48.87), (21.17, 3.79, 58.73)),
)
# The edge of the platform the player starts on, where it drops into the start half pipe.
START_PIPE_LIPS = (((80.34, 35.85, -120.84), (139.5, 35.85, -120.84)),)
COPING_LIPS = MAIN_PIPE_LIPS + WALL_PIPE_LIPS + LEDGE_LIPS + START_PIPE_LIPS


def rail_along(start: tuple[float, float, float], end: tuple[float, float, float]) -> tuple[tuple[float, float, float], float, float, float]:
    """The (position, yaw, scale, pitch) of a rail/0 whose bar runs from start to end."""
    dx, dy, dz = end[0] - start[0], end[1] - start[1], end[2] - start[2]
    run = math.hypot(dx, dz)
    yaw = math.degrees(math.atan2(-dz, dx)) % 360
    pitch = math.degrees(math.atan2(dy, run))
    scale = math.sqrt(run * run + dy * dy) / RAIL0_LENGTH
    yaw_r, pitch_r = math.radians(yaw), math.radians(pitch)
    up = (-math.sin(pitch_r) * math.cos(yaw_r), math.cos(pitch_r), math.sin(pitch_r) * math.sin(yaw_r))
    bar = RAIL0_BAR_HEIGHT * scale
    middle = tuple((a + c) / 2 for a, c in zip(start, end, strict=True))
    return tuple(m - u * bar for m, u in zip(middle, up, strict=True)), yaw, scale, pitch


COPING_RAILS = tuple(rail_along(start, end) for start, end in COPING_LIPS)

# The half pipe lips reach 85 degrees, past the game's 45 degree slope limit.
MAX_SLOPE_ANGLE = 88

PACK_ID = "thps"
PACK_VERSION = "2.0.21"
MANIFEST_PATH = Path(__file__).resolve().parent.parent / "unity" / "pack-authoring" / "packs" / PACK_ID / "manifest.json"
WAREHOUSE_ASSET = "Warehouse"
# The default track is the soundtrack AudioClip ThpsPack.cs builds from tools/ost/04 Superman.mp3, named by the file name with each run of other characters made an underscore.
MUSIC = f"bundle:{PACK_ID}/04_Superman"
TITLE = "Warehouse"
DESCRIPTION = "I'm trying to sleep"
MAP_DESCRIPTION = "A warehouse built for grinding"
ALLOWED_CHARACTERS = ["calcium", "tonymczoom"]
# The game's boombox, placed as the radio on the top platform of the start half pipe (surface height 35.85), at its left end looking down the pipe, within this distance of the player spawn.
RADIO_CATALOG_ID = "interactable/boombox"
RADIO_POSITION = (90, 35.9, -123.5)
RADIO_REACH = 20
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
SCHEMA_VERSION = 3

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


# Items the level author moved by hand in the editor, as saved by scripts/extract_thps_item_overrides.py.
OVERRIDES_PATH = Path(__file__).resolve().parent / "thps_item_overrides.json"
EXTRACT_DIR = Path(__file__).resolve().parent.parent / ".tools" / "thps1" / "warehouse"
NODES_PATH = EXTRACT_DIR / "warehouse_nodes.json"
OBJ_PATH = EXTRACT_DIR / "warehouse.obj"

# Letters map to the five Forest shrine prefabs one to one; box piles are chests; the tape and the lane 100 pickups are free chests.
LETTER_SHRINES = {
    "S": "forest/shrines/0",
    "K": "forest/shrines/1",
    "A": "forest/shrines/2",
    "T": "forest/shrines/3",
    "E": "forest/shrines/4",
}
# The three 100 pickups spread along the lanes; nodes 148 to 150 are a 100/200/500 cluster the confirmed mapping leaves out.
LANE_BONUS_NODES = (15, 30, 31)

# An item may slide this far in x and z from its node to find a supported, clear spot (a node can sit on a platform edge or over a quarter pipe).
MAX_NODE_SHIFT = 10.5
# An item never stands on a surface steeper than this.
MAX_SURFACE_TILT = 45.0
SHIFT_STEP = 0.5
# Footprint corners must land within this of the surface plane under the item.
SUPPORT_TOLERANCE = 0.3
# The supported footprint is this fraction of the bounds' half extents, because a shrine's base is narrower than its bounds.
SUPPORT_FOOTPRINT = 0.5
# The overlap box starts this far above the base so the surface the item stands on does not count.
BASE_CLEARANCE = 0.1


class ItemMetrics(NamedTuple):
    base_offset: float
    half: tuple[float, float, float]


# Pivot-to-base distance and upright half extents (x, y, z) of each prefab, read from the placed items' mesh bounds in the running game with query_objects.
ITEM_METRICS = {
    "interactable/chest": ItemMetrics(0.5, (1.7, 1.25, 1.6)),
    "interactable/chestFree": ItemMetrics(0.5, (1.5, 1.3, 1.5)),
    "forest/shrines/0": ItemMetrics(0.12, (2.64, 3.69, 2.53)),
    "forest/shrines/1": ItemMetrics(0.05, (2.63, 3.43, 2.63)),
    "forest/shrines/2": ItemMetrics(0.05, (2.2, 4.22, 1.78)),
    "forest/shrines/3": ItemMetrics(0.02, (2.42, 2.45, 0.56)),
    "forest/shrines/4": ItemMetrics(0.13, (2.6, 4.41, 2.53)),
}


class Collectible(NamedTuple):
    code: str
    catalog_id: str
    node: int
    x: float
    y: float
    z: float
    normal: tuple[float, float, float]
    euler: tuple[float, float, float]
    yaw: float = 0.0
    overridden: bool = False


def warehouse_footprint() -> tuple[float, float]:
    """Width (x) and depth (z) of the scaled Warehouse in level units."""
    return WAREHOUSE_OBJ_WIDTH * WAREHOUSE_SCALE, WAREHOUSE_OBJ_DEPTH * WAREHOUSE_SCALE


def local_to_world(x: float, z: float) -> tuple[float, float]:
    x0, z0 = INNER_ORIGIN
    return (
        GRID_ORIGIN + TILE * x0 - TILE // 2 + x,
        GRID_ORIGIN + TILE * z0 - TILE // 2 + z,
    )


def warehouse_placement() -> ws.Placement:
    wx, wz = local_to_world(INNER_X * TILE / 2, INNER_Z * TILE / 2)
    _, centre = obj_mesh()
    return ws.Placement(centre, WAREHOUSE_SCALE, wx, WAREHOUSE_LIFT, wz)


@cache
def obj_mesh() -> tuple[list[ws.Triangle], tuple[float, float]]:
    return ws.read_obj(OBJ_PATH)


@cache
def warehouse_triangles() -> list[ws.Triangle]:
    return warehouse_placement().triangles(obj_mesh()[0])


def node_world(position: list[float]) -> ws.Vec:
    """A node's (x, y down) OBJ position as a world point, y up."""
    x, y, z = position
    return warehouse_placement().point((x, -y, z))


def base_point(c: Collectible) -> ws.Vec:
    off = ITEM_METRICS[c.catalog_id].base_offset
    return (c.x - c.normal[0] * off, c.y - c.normal[1] * off, c.z - c.normal[2] * off)


def lowest_clearance(c: Collectible, triangles: list[ws.Triangle]) -> float:
    """Height of the item's lowest footprint corner above the surface under it: positive hovers, negative sinks."""
    hx, _, hz = ITEM_METRICS[c.catalog_id].half
    rotation = ws.tilt_rotation(c.normal, c.yaw)
    bx, by, bz = base_point(c)
    clearances = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            ox, oz = sx * hx * SUPPORT_FOOTPRINT, sz * hz * SUPPORT_FOOTPRINT
            cx = bx + rotation[0][0] * ox + rotation[0][2] * oz
            cy = by + rotation[1][0] * ox + rotation[1][2] * oz
            cz = bz + rotation[2][0] * ox + rotation[2][2] * oz
            hit = ws.drop(triangles, cx, cy + 3.0, cz)
            if hit is not None:
                clearances.append(cy - hit.y)
    return min(clearances)


def item_overlaps(c: Collectible, triangles: list[ws.Triangle]) -> list[int]:
    """Triangles that cut into the item's box, which starts BASE_CLEARANCE above its base."""
    metrics = ITEM_METRICS[c.catalog_id]
    hx, hy, hz = metrics.half
    height = hy - BASE_CLEARANCE / 2
    bx, by, bz = base_point(c)
    lift = BASE_CLEARANCE + height
    centre = (bx + c.normal[0] * lift, by + c.normal[1] * lift, bz + c.normal[2] * lift)
    return ws.box_hits(triangles, centre, ws.tilt_rotation(c.normal, c.yaw), (hx, height, hz))


def anchor(code: str, catalog_id: str, node: int, position: list[float]) -> Collectible:
    """Drop the item from its node onto the surface below, sliding the least distance that leaves it supported and clear."""
    triangles = warehouse_triangles()
    nx, ny, nz = node_world(position)
    off = ITEM_METRICS[catalog_id].base_offset
    hx, _, hz = ITEM_METRICS[catalog_id].half
    steps = range(-int(MAX_NODE_SHIFT / SHIFT_STEP), int(MAX_NODE_SHIFT / SHIFT_STEP) + 1)
    shifts = sorted(((i * SHIFT_STEP, k * SHIFT_STEP) for i in steps for k in steps), key=lambda d: math.hypot(*d))
    for dx, dz in shifts:
        if math.hypot(dx, dz) > MAX_NODE_SHIFT:
            break
        ax, az = nx + dx, nz + dz
        hit = ws.drop(triangles, ax, ny, az)
        if hit is None or hit.normal[1] < math.cos(math.radians(MAX_SURFACE_TILT)):
            continue
        rotation = ws.tilt_rotation(hit.normal, 0.0)
        corners = [(sx * hx * SUPPORT_FOOTPRINT, sz * hz * SUPPORT_FOOTPRINT) for sx in (-1, 1) for sz in (-1, 1)]
        if not all(supported(triangles, hit, ax, az, rotation, ox, oz) for ox, oz in corners):
            continue
        item = Collectible(
            code,
            catalog_id,
            node,
            ax + hit.normal[0] * off,
            hit.y + hit.normal[1] * off,
            az + hit.normal[2] * off,
            hit.normal,
            ws.unity_euler(ws.item_rotation(hit.normal, 0.0)),
        )
        if set(item_overlaps(item, triangles)) <= {hit.index}:
            return item
    raise ValueError(f"no supported spot for {code} within {MAX_NODE_SHIFT} units of node {node}")


def supported(triangles: list[ws.Triangle], hit: ws.Hit, ax: float, az: float, rotation: ws.Matrix, ox: float, oz: float) -> bool:
    """Whether the surface under a footprint corner lies on the plane through the anchor."""
    dx, _, dz = (rotation[0][0] * ox + rotation[0][2] * oz, 0.0, rotation[2][0] * ox + rotation[2][2] * oz)
    expected = hit.y - (hit.normal[0] * dx + hit.normal[2] * dz) / hit.normal[1]
    below = ws.drop(triangles, ax + dx, expected + 1.0, az + dz)
    return below is not None and abs(below.y - expected) <= SUPPORT_TOLERANCE


@cache
def anchored_collectibles() -> tuple[Collectible, ...]:
    nodes = {n["node"]: n for n in json.loads(NODES_PATH.read_text())["nodes"]}

    def by_type(kind: str) -> list[dict]:
        return sorted((n for n in nodes.values() if n["type"] == kind), key=lambda n: n["node"])

    items = [anchor(f"R{i}", "interactable/chest", n["node"], n["position"]) for i, n in enumerate(by_type("box_pile"), 1)]
    items += [
        anchor(n["name"], LETTER_SHRINES[n["name"]], n["node"], n["position"])
        for n in sorted(by_type("letter"), key=lambda n: "SKATE".index(n["name"]))
    ]
    items += [anchor("Tape", "interactable/chestFree", n["node"], n["position"]) for n in by_type("tape")]
    items += [anchor(f"100/{i}", "interactable/chestFree", i, nodes[i]["position"]) for i in LANE_BONUS_NODES]
    return tuple(items)


def load_overrides(path: Path | None = None) -> dict[str, dict]:
    path = path or OVERRIDES_PATH
    return json.loads(path.read_text()) if path.exists() else {}


@cache
def collectibles() -> tuple[Collectible, ...]:
    """The anchored items, with the hand-arranged ones in the overrides file replaced by their saved transform."""
    overrides = load_overrides()
    items = anchored_collectibles()
    unknown = set(overrides) - {c.code for c in items}
    if unknown:
        raise ValueError(f"overrides for unknown items: {sorted(unknown)}")
    return tuple(overridden(c, overrides[c.code]) if c.code in overrides else c for c in items)


def overridden(c: Collectible, override: dict) -> Collectible:
    x, y, z = override["position"]
    euler = tuple(override["rotation"])
    rotation = ws.euler_matrix(*euler)
    return c._replace(x=x, y=y, z=z, euler=euler, normal=(rotation[0][2], rotation[1][2], rotation[2][2]), overridden=True)


def cell_of_local(x: float, z: float) -> tuple[int, int]:
    return int(x // TILE), int(z // TILE)


def inner_cells() -> list[tuple[int, int]]:
    x0, z0 = INNER_ORIGIN
    return [(x0 + dx, z0 + dz) for dz in range(INNER_Z) for dx in range(INNER_X)]


def kept_cells() -> list[tuple[int, int]]:
    return [GENERATED_SPAWN_CELL]


def edit(op_type: str, payload: dict, target: str = "") -> dict:
    return {"opType": op_type, "target": target, "payload": json.dumps(payload, separators=(",", ":"))}


def tile_edits() -> list[dict]:
    kept = set(kept_cells())
    edits = []
    for z in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            if (x, z) not in kept:
                edits.append(edit("tile.remove", {"x": x, "z": z}))
                continue
            edits.append(edit("tile.setHeight", {"x": x, "z": z, "height": INNER_LEVEL}))
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


def boss_spawn_position() -> tuple[float, float, float]:
    """The boss portal's world position, standing on the Warehouse surface under it.

    The drop starts below the hanging box (BOSS_SPAWN_DROP_FROM) so it finds the room's floor rather
    than the box the portal used to hang in. A portal in the air spawns its boss in the air, and the
    physics-chase boss cannot climb out of a closed box, which left the boss unreachable."""
    bx, bz = local_to_world(*BOSS_SPAWN_LOCAL)
    hit = ws.drop(warehouse_triangles(), bx, BOSS_SPAWN_DROP_FROM, bz)
    if hit is None:
        raise ValueError(f"no Warehouse surface under the boss spawner at ({bx}, {bz})")
    return (bx, hit.y, bz)


def spawn_moves() -> list[dict]:
    bx, by, bz = boss_spawn_position()
    payload = {
        "newTransform": transform(bx, by, bz, BOSS_SPAWN_SCALE, BOSS_SPAWN_YAW),
        "hiddenChildren": BOSS_HIDDEN_CHILDREN,
    }
    return [edit("object.move", payload, "gen:object:BossSpawner:0000")]


def hidden_rail_edit(position: tuple[float, float, float], yaw: float, scale: float, pitch: float = 0.0) -> dict:
    x, y, z = position
    return edit(
        "object.place",
        {
            "catalogId": MESH_RAIL_CATALOG_ID,
            "position": {"x": x, "y": y, "z": z},
            "rotation": {"x": 0.0, "y": yaw, "z": pitch},
            "scale": {"x": scale, "y": scale, "z": scale},
            "hidden": True,
        },
    )


def mesh_rail_edits() -> list[dict]:
    return [hidden_rail_edit(*rail) for rail in MESH_RAILS + COPING_RAILS]


def rail_edits() -> list[dict]:
    return mesh_rail_edits()


def radio_edits() -> list[dict]:
    x, y, z = RADIO_POSITION
    return [
        edit(
            "object.place",
            {
                "catalogId": RADIO_CATALOG_ID,
                "position": {"x": x, "y": y, "z": z},
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            },
        )
    ]


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
    for c in collectibles():
        pitch, yaw, roll = c.euler
        edits.append(
            edit(
                "object.place",
                {
                    "catalogId": c.catalog_id,
                    "position": {"x": c.x, "y": c.y, "z": c.z},
                    "rotation": {"x": pitch, "y": yaw, "z": roll},
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
        "killFloorY": KILL_FLOOR_Y,
        "music": MUSIC,
        "title": TITLE,
        "description": DESCRIPTION,
        "mapDescription": MAP_DESCRIPTION,
        "allowedCharacters": ALLOWED_CHARACTERS,
        "edits": tile_edits() + clutter_removals() + spawn_moves() + rail_edits() + warehouse_edits() + radio_edits() + collectible_edits(),
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
