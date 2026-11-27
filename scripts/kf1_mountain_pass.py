#!/usr/bin/env python3
import argparse
import hashlib
import json
import level_geometry as geometry
import math
import re
import struct
from build_thps_level import CHEST_LUCK_RANGE, GUARANTEED_SHRINE_KINDS, SHRINE_COUNT, SHRINE_KINDS
from pathlib import Path
from warehouse_surface import UPRIGHT_PITCH

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".tools/kf1"
T3D_SHA256 = "87acc038e2e67c6176ea2396b7ffa20ce4bc91f6f27bd99a6546013380c5b02c"
ORIGIN = (0, 0, 0)
SCALE = 0.028
SAMPLE_UNITS = 64
FLAT_HEIGHT = 32768
KILL_FLOOR_Y = -200.0
SPAWN_CLEARANCE = 2.0
CHEST_CLEARANCE = 0.5
REACH = 100
TERRAIN_RGBA = (96, 110, 70, 255)
MESH_UNITS = 100
ACTOR_CLASSES = frozenset(
    {"StaticMeshActor", "PlayerStart", "ZombieVolume", "ShopVolume", "KFRandomItemSpawn", "KFAmmoPickup", "BlockingVolume"}
)
LEVEL_FIELDS = frozenset(
    {
        "schemaVersion",
        "baseline",
        "map",
        "stageIndex",
        "tier",
        "title",
        "description",
        "mapDescription",
        "grid",
        "spawn",
        "bossSpawner",
        "killFloorY",
        "noGrass",
        "extraShrines",
        "extraShrinesMax",
        "extraShrineKinds",
        "guaranteedShrineKinds",
        "chestLuckRange",
        "shrineSpots",
        "powerupSpots",
        "edits",
    }
)
ACTOR_START = re.compile(r"^Begin Actor Class=(\w+) Name=(\S+)")
ACTOR_PROPERTY = re.compile(r"^    (Location|Rotation|DrawScale3D|StaticMesh)=(.*)$")
ACTOR_MESH = re.compile(r"StaticMesh'([^']+)'")


def verify_export(t3d):
    actual = hashlib.sha256(t3d.read_bytes()).hexdigest()
    if actual != T3D_SHA256:
        raise ValueError(f"{t3d}: expected the KF-MountainPass level export with SHA-256 {T3D_SHA256}, got {actual}")


def _vector(text, keys, default):
    found = {key: float(value) for key, value in re.findall(r"(\w+)=(-?[\d.]+)", text)}
    return tuple(found.get(key, fallback) for key, fallback in zip(keys, default, strict=True))


def parse_actors(text, classes=ACTOR_CLASSES):
    """The top-level properties of each wanted T3D actor; brush polygons are indented deeper and never match."""
    actors, current = [], None
    for line in text.splitlines():
        if (start := ACTOR_START.match(line)) is not None:
            current = {
                "class": start[1],
                "name": start[2],
                "location": (0, 0, 0),
                "rotation": (0, 0, 0),
                "scale": (1, 1, 1),
                "mesh": None,
            }
        elif line.startswith("End Actor"):
            if current is not None and current["class"] in classes:
                actors.append(current)
            current = None
        elif current is not None and (match := ACTOR_PROPERTY.match(line)) is not None:
            key, value = match.groups()
            if key == "Location":
                current["location"] = _vector(value, "XYZ", (0, 0, 0))
            elif key == "Rotation":
                current["rotation"] = tuple(int(n) for n in _vector(value, ("Pitch", "Yaw", "Roll"), (0, 0, 0)))
            elif key == "DrawScale3D":
                current["scale"] = _vector(value, "XYZ", (1, 1, 1))
            elif (mesh := ACTOR_MESH.search(value)) is not None:
                current["mesh"] = mesh[1]
    return actors


def world_point(point, origin, scale):
    """Unreal X (forward), Y (right), Z (up) onto Megabonk Z, X, Y: a cyclic permutation, so handedness is kept."""
    x, y, z = (a - b for a, b in zip(point, origin, strict=True))
    return [scale * y, scale * z, scale * x]


def rotation_matrix(pitch, yaw, roll):
    """Unreal's rotator in 65536ths of a turn, as rows: roll about X, then pitch about Y, then yaw about Z."""
    (sp, cp), (sy, cy), (sr, cr) = ((math.sin(a), math.cos(a)) for a in (n * math.tau / 65536 for n in (pitch, yaw, roll)))
    return (
        (cy * cp, cy * sp * sr - sy * cr, -cy * sp * cr - sy * sr),
        (sy * cp, sy * sp * sr + cy * cr, -sy * sp * cr + cy * sr),
        (sp, -cp * sr, cp * cr),
    )


def mesh_point(vertex, rotation, scale, location):
    """A umodel glTF vertex (Y up, metres, Y and Z swapped) back in Unreal units, then scaled, rotated and moved."""
    x, y, z = vertex
    local = (x * MESH_UNITS * scale[0], z * MESH_UNITS * scale[1], y * MESH_UNITS * scale[2])
    matrix = rotation_matrix(*rotation)
    return tuple(sum(row[i] * local[i] for i in range(3)) + offset for row, offset in zip(matrix, location, strict=True))


def read_heightmap(data):
    """The raw words of a 16-bit uncompressed BMP, top row first."""
    offset, width, height, planes, bits, compression = struct.unpack_from("<I4xii", data, 10)[:3] + struct.unpack_from(
        "<HHI", data, 26
    )
    if bits != 16 or compression != 0:
        raise ValueError(f"Expected an uncompressed 16-bit heightmap, got {bits} bits per pixel, compression {compression}")
    rows = [list(struct.unpack_from(f"<{width}H", data, offset + 2 * width * row)) for row in range(height)]
    return rows[::-1]


def terrain_height(value):
    return (value - FLAT_HEIGHT) / 256 * SAMPLE_UNITS


def terrain_points(heights):
    """Unreal-space samples, 64 units apart, with the grid centered on the origin."""
    half = len(heights) // 2
    return [
        [
            ((column - half) * SAMPLE_UNITS, (row - half) * SAMPLE_UNITS, terrain_height(value))
            for column, value in enumerate(line)
        ]
        for row, line in enumerate(heights)
    ]


def terrain_mesh(heights, origin, scale):
    """Shared world vertices and up-facing indices for the heightmap."""
    grid = terrain_points(heights)
    size = len(heights)
    positions = [n for line in grid for point in line for n in world_point(point, origin, scale)]
    indices = []
    for row in range(size - 1):
        for column in range(size - 1):
            a, b, c, d = row * size + column, row * size + column + 1, (row + 1) * size + column, (row + 1) * size + column + 1
            indices.extend((a, b, c, c, b, d))
    return positions, indices


def terrain_triangles(heights, origin, scale):
    positions, indices = terrain_mesh(heights, origin, scale)
    vertex = [positions[i : i + 3] for i in range(0, len(positions), 3)]
    return [(tuple(vertex[i] for i in indices[start : start + 3]), None) for start in range(0, len(indices), 3)]


def floor_placement(terrain, point, origin, scale, clearance=0, reach=REACH):
    """A Megabonk position on the terrain below or near an Unreal point."""
    x, y, z = world_point(point, origin, scale)
    floor = geometry.floor_height(terrain, (x, y + scale * reach, z))
    if floor is None or abs(floor - y) > scale * reach:
        raise ValueError(f"No floor within {reach} units of {point}: {floor}")
    return [round(n, 4) for n in (x, floor + clearance, z)]


def walls(terrain):
    return geometry.perimeter([points for points, _surface in terrain], kill_floor=KILL_FLOOR_Y)


def make_level(terrain, actors, skipped=None):
    """The level JSON; anchors with no terrain floor (BSP floors) are left out and described in `skipped`."""
    skipped = [] if skipped is None else skipped

    def named(cls):
        return [actor for actor in actors if actor["class"] == cls]

    def place(actor, clearance=0):
        return floor_placement(terrain, actor["location"], ORIGIN, SCALE, clearance)

    def place_each(cls, clearance=0):
        spots = []
        for actor in named(cls):
            try:
                spots.append(place(actor, clearance))
            except ValueError as error:
                skipped.append(f"{cls} {actor['name']}: {error}")
        return spots

    starts, volumes = named("PlayerStart"), named("ZombieVolume")
    for cls, found in (("PlayerStart", starts), ("ZombieVolume", volumes)):
        if not found:
            raise ValueError(f"The level export has no {cls} actor")
    start = starts[0]
    spawn = place(start, SPAWN_CLEARANCE)
    grounded = []
    for volume in volumes:
        try:
            grounded.append((math.dist(volume["location"][:2], start["location"][:2]), place(volume)))
        except ValueError as error:
            skipped.append(f"ZombieVolume {volume['name']}: {error}")
    if not grounded:
        raise ValueError("No ZombieVolume has a terrain floor for the boss spawner")
    return {
        "schemaVersion": 4,
        "baseline": "none",
        "map": 1,
        "stageIndex": 0,
        "tier": 0,
        "title": "Killing Floor: Mountain Pass",
        "description": "Survive in the Mountain Pass valley from Killing Floor.",
        "mapDescription": "Hold the valley between the trader pods.",
        "grid": {"width": 15, "depth": 15, "cells": [{"x": 7, "z": 7, "height": -3}]},
        "spawn": {"position": spawn, "rotation": [0, (start["rotation"][1] * 360 / 65536) % 360, 0]},
        "bossSpawner": {"position": max(grounded)[1], "rotation": [0, 0, 0]},
        "killFloorY": KILL_FLOOR_Y,
        "noGrass": True,
        "extraShrines": SHRINE_COUNT[0],
        "extraShrinesMax": SHRINE_COUNT[1],
        "extraShrineKinds": SHRINE_KINDS,
        "guaranteedShrineKinds": list(GUARANTEED_SHRINE_KINDS),
        "chestLuckRange": list(CHEST_LUCK_RANGE),
        "shrineSpots": place_each("ShopVolume"),
        "powerupSpots": place_each("KFAmmoPickup"),
        "edits": [
            geometry.object_edit("interactable/chest", spot, UPRIGHT_PITCH)
            for spot in place_each("KFRandomItemSpawn", CHEST_CLEARANCE)
        ],
    }


def mesh_path(meshes, reference):
    package, *_group, name = reference.split(".")
    return meshes / package / "StaticMesh" / f"{name}.gltf"


def render_primitive(gltf, data, primitive, rotation, scale3, location, origin, scale, material):
    def attr(name):
        index = primitive["attributes"].get(name)
        return [] if index is None else geometry.read_accessor(gltf, data, index)

    positions = [
        round(n, 4)
        for vertex in attr("POSITION")
        for n in world_point(mesh_point(vertex, rotation, scale3, location), origin, scale)
    ]
    return {
        "positions": positions,
        "indices": geometry.reverse_winding(i for (i,) in geometry.read_accessor(gltf, data, primitive["indices"])),
        "uv": [n for u, v in attr("TEXCOORD_0") for n in (u, 1 - v)],
        "rgba": [n for color in attr("COLOR_0") for n in color],
        "material": material,
    }


def terrain_primitive(heights, material):
    positions, indices = terrain_mesh(heights, ORIGIN, SCALE)
    return {
        "positions": [round(n, 4) for n in positions],
        "indices": indices,
        "uv": [],
        "rgba": list(TERRAIN_RGBA) * (len(positions) // 3),
        "material": material,
    }


def unpack_map(meshes, actors, heights, terrain):
    materials = [{"alphaMode": "OPAQUE", "doubleSided": False}]
    lookup, loaded, rendered = {}, {}, [{"name": "Terrain", "primitives": [terrain_primitive(heights, 0)]}]
    for actor in actors:
        if actor["mesh"] is None:
            continue
        path = mesh_path(meshes, actor["mesh"])
        if path not in loaded:
            gltf = json.loads(path.read_bytes().decode("utf-8", errors="replace"))
            loaded[path] = gltf, (path.parent / gltf["buffers"][0]["uri"]).read_bytes()
        gltf, data = loaded[path]
        primitives = []
        for primitive in gltf["meshes"][0]["primitives"]:
            key = path, primitive.get("material")
            if key not in lookup:
                source = gltf.get("materials", [{}])[key[1] or 0]
                color = source.get("pbrMetallicRoughness", {}).get("baseColorFactor", [1, 1, 1, 1])
                lookup[key] = len(materials)
                materials.append({"name": source.get("name", ""), "alphaMode": "OPAQUE", "doubleSided": True, "baseColor": color})
            primitives.append(
                render_primitive(
                    gltf, data, primitive, actor["rotation"], actor["scale"], actor["location"], ORIGIN, SCALE, lookup[key]
                )
            )
        rendered.append({"name": actor["name"], "primitives": primitives})
    positions, indices = terrain_mesh(heights, ORIGIN, SCALE)
    return {
        "meshes": rendered,
        "materials": materials,
        "perimeter": walls(terrain),
        "collision": {"positions": [round(n, 4) for n in positions], "indices": indices},
    }


def prepare(source, meshes, output):
    t3d = source / "KF-MountainPass.t3d"
    verify_export(t3d)
    actors = parse_actors(t3d.read_text(encoding="latin-1"))
    heights = read_heightmap((source / "Terrain_Main.bmp").read_bytes())
    terrain = terrain_triangles(heights, ORIGIN, SCALE)
    skipped = []
    level = make_level(terrain, actors, skipped)
    (output / "mesh.json").write_text(json.dumps(unpack_map(meshes, actors, heights, terrain), separators=(",", ":")))
    (output / "kf1-mountain-pass.mblevel.json").write_text(json.dumps(level, indent=2) + "\n")
    return level, skipped


def main():
    parser = argparse.ArgumentParser(description="Prepare the local Killing Floor 1 Mountain Pass survival level")
    parser.add_argument("command", choices=("verify-export", "prepare"))
    parser.add_argument("--work", type=Path, default=WORK)
    args = parser.parse_args()
    try:
        source = args.work / "export"
        if args.command == "verify-export":
            verify_export(source / "KF-MountainPass.t3d")
            print(f"Verified the KF-MountainPass level export: {source}")
        else:
            level, skipped = prepare(source, args.work / "out", args.work)
            for item in skipped:
                print(f"Skipped {item}")
            print(f"Prepared Mountain Pass: spawn {level['spawn']['position']}, boss spawner {level['bossSpawner']['position']}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
