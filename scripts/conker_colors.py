#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
import os
import struct
import subprocess
import warehouse_surface as ws
from build_thps_level import CHEST_LUCK_RANGE, GUARANTEED_SHRINE_KINDS, SHRINE_COUNT, SHRINE_KINDS
from pathlib import Path
from warehouse_surface import UPRIGHT_PITCH

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".tools/conker"
ROM_SHA256 = "32e6a8b970ec12ac5f782344945aa0c98a193832eefb687529d03bab6948714b"
EXTRACTOR_REV = "9eaf19e4624f058b58b0a63b8cc2fecf4f22f8ef"
ORIGIN = (200, -1000, 1200)
SCALE = 0.028
PIT_SOURCE_Y = -2050
KILL_FLOOR_Y = -46
PIT_FLOOR_Y = -30.0
CELL_SIZE = 2.0
WALL_HEADROOM = 1000.0
WALL_DROP = 28.0
STEP_TOLERANCE = 12.0
IDENTITY = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
CHESTS = (
    ("interactable/chestFree", (-200, -450, 9500)),
    ("interactable/chest", (800, -480, 4500)),
    ("interactable/chest", (-1168, 285, 2198)),
    ("interactable/chest", (-450, 285, -350)),
    ("interactable/chest", (-1200, -1398, -3350)),
    ("interactable/chest", (-70, -1400, -7090)),
)
SHRINE_ANCHORS = (
    (800, -444, 5800),
    (-2000, -364, 4550),
    (-400, -220, 4550),
    (600, -218, 4550),
    (-400, -365, 3900),
    (-1600, 318, 2100),
    (-800, 244, 2100),
    (1400, -268, 400),
    (400, -305, 400),
    (-1600, -577, 400),
    (1000, -682, -1550),
    (600, -729, -2300),
    (-1400, -1404, -3600),
    (-1000, -1390, -3200),
    (600, -1390, -3200),
    (-400, -1402, -6600),
)
POWERUP_ANCHORS = ((-1400, -399, 5250), (-1000, 277, 2600), (-2200, -558, 1200), (2200, -665, -2300), (800, -1402, -3600))
MINIBOSS_ANCHORS = (
    (800, -444, 5800),
    (-400, -365, 3900),
    (400, -305, 400),
    (1000, -682, -1550),
    (-1000, -1390, -3200),
    (800, -1402, -3600),
)


def verify_rom(rom):
    with rom.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != ROM_SHA256:
        raise ValueError(f"{rom}: expected US retail .z64 SHA-256 {ROM_SHA256}, got {actual}")


def world_point(point, origin, scale):
    x, y, z = (a - b for a, b in zip(point, origin, strict=True))
    return [scale * x, scale * y, -scale * z]


def reverse_winding(indices):
    return [index for a, b, c in zip(*[iter(indices)] * 3, strict=True) for index in (a, c, b)]


def collision_mesh(runs, origin, scale):
    vertices, indices = [], []
    lookup = {}
    for run in runs:
        for points, _surface in run["triangles"]:
            for point in points:
                key = tuple(point)
                if key not in lookup:
                    lookup[key] = len(vertices)
                    vertices.append(world_point(key, origin, scale))
                indices.append(lookup[key])
    return vertices, reverse_winding(indices)


def arena_collision(runs):
    return [
        {**run, "triangles": [face for face in run["triangles"] if max(p[1] for p in face[0]) >= PIT_SOURCE_Y]} for run in runs
    ]


def _plane(a, b, c):
    """A face's edge vectors and plan cross product, or None where it has no plan area to cover."""
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    span = ux * vz - uz * vx
    return None if abs(span) <= ws.EPSILON else (ux, uy, uz, vx, vy, vz, span)


def _covered(a, b, c, plane, cell):
    """The grid cells whose centre falls inside a face's plan projection, with the surface height at each."""
    ux, uy, uz, vx, vy, vz, span = plane
    for i in range(math.floor(min(a[0], b[0], c[0]) / cell), math.floor(max(a[0], b[0], c[0]) / cell) + 1):
        for j in range(math.floor(min(a[2], b[2], c[2]) / cell), math.floor(max(a[2], b[2], c[2]) / cell) + 1):
            p, q = (i + 0.5) * cell - a[0], (j + 0.5) * cell - a[2]
            w, t = (p * vz - q * vx) / span, (ux * q - uz * p) / span
            if w < -1e-6 or t < -1e-6 or w + t > 1 + 1e-6:
                continue
            yield i, j, a[1] + w * uy + t * vy


def _slope(plane):
    """The cosine of a face's normal from straight up, ignoring which way it is wound."""
    ux, uy, uz, vx, vy, vz, span = plane
    reach = math.hypot(uy * vz - uz * vy, span, ux * vy - uy * vx)
    return 0.0 if reach <= ws.EPSILON else abs(span) / reach


def walkable_cells(triangles, cell=CELL_SIZE, max_slope_degrees=45.0):
    """Grid cells the player can stand on, keyed by plan index and holding the highest walkable surface in each."""
    gentle = math.cos(math.radians(max_slope_degrees))
    cells = {}
    for a, b, c in triangles:
        if max(a[1], b[1], c[1]) < KILL_FLOOR_Y:
            continue
        plane = _plane(a, b, c)
        if plane is None or _slope(plane) < gentle:
            continue
        for i, j, height in _covered(a, b, c, plane, cell):
            if cells.get((i, j), float("-inf")) < height:
                cells[(i, j)] = height
    return cells


def _reachable(cells, seeds):
    """The walkable cells 8-connected to a seed: everything else is a scan artifact or a ledge the player cannot reach."""
    reached, frontier = set(seeds), list(seeds)
    while frontier:
        i, j = frontier.pop()
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                neighbour = (i + di, j + dj)
                if neighbour in reached or neighbour not in cells:
                    continue
                reached.add(neighbour)
                frontier.append(neighbour)
    return reached


def _anchor_cells(cell=CELL_SIZE):
    """The cells holding the level's own chest, shrine, power-up and miniboss anchors."""
    anchors = [position for _name, position in CHESTS]
    anchors += list(SHRINE_ANCHORS) + list(POWERUP_ANCHORS) + list(MINIBOSS_ANCHORS)
    return {(math.floor(x / cell), math.floor(z / cell)) for x, _y, z in (world_point(list(a), ORIGIN, SCALE) for a in anchors)}


def playable_cells(triangles, cell=CELL_SIZE, max_slope_degrees=45.0, seeds=None):
    """The top surface as the player can actually use it: walkable cells above the pit floor, connected to a level anchor."""
    cells = {key: height for key, height in walkable_cells(triangles, cell, max_slope_degrees).items() if height > PIT_FLOOR_Y}
    if seeds is None:
        seeds = {key for key in _anchor_cells(cell) if key in cells} or set(cells)
    return {key: cells[key] for key in _reachable(cells, seeds)}


def _beyond(cells):
    """Cells outside the walkable mask that are reachable from off the map: the arena's border, as opposed to its pits."""
    low_i, high_i = min(i for i, _ in cells), max(i for i, _ in cells)
    low_j, high_j = min(j for _, j in cells), max(j for _, j in cells)
    reachable = {(low_i - 1, low_j - 1)}
    frontier = list(reachable)
    while frontier:
        i, j = frontier.pop()
        for step in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbour = (i + step[0], j + step[1])
            if neighbour in reachable or neighbour in cells:
                continue
            if not (low_i - 1 <= neighbour[0] <= high_i + 1 and low_j - 1 <= neighbour[1] <= high_j + 1):
                continue
            reachable.add(neighbour)
            frontier.append(neighbour)
    return reachable


def _stretches(positions):
    """The contiguous index ranges of a run's exposed cells."""
    ordered = sorted(positions)
    start = previous = ordered[0]
    for position in ordered[1:]:
        if position != previous + 1:
            yield start, previous
            start = position
        previous = position
    yield start, previous


def perimeter(triangles, cell=CELL_SIZE, max_slope_degrees=90.0, seeds=None):
    """Walls around the top terrain, including steep slopes that are part of the arena."""
    cells = playable_cells(triangles, cell, max_slope_degrees, seeds)
    if not cells:
        return []
    open_air = _beyond(cells)
    ceiling = max(point[1] for face in triangles for point in face) + WALL_HEADROOM
    runs = {}
    for (i, j), height in cells.items():
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbour = (i + di, j + dj)
            if neighbour in cells or neighbour not in open_air:
                continue
            axis, line, position = ("x", j + max(dj, 0), i) if dj else ("z", i + max(di, 0), j)
            runs.setdefault((axis, line), {})[position] = height

    walls = []
    for (axis, line), heights in sorted(runs.items()):
        for first, last in _stretches(heights):
            walls.extend(_fence(axis, line, first, last, heights, ceiling, cell))
    return walls


def _fence(axis, line, first, last, heights, ceiling, cell):
    """A wall to the shared ceiling, split where the ground steps."""
    ground = [heights[position] for position in range(first, last + 1)]
    if last > first and max(ground) - min(ground) > STEP_TOLERANCE:
        middle = (first + last) // 2
        return _fence(axis, line, first, middle, heights, ceiling, cell) + _fence(
            axis, line, middle + 1, last, heights, ceiling, cell
        )
    centre = (first + last + 1) / 2 * cell
    offset = line * cell
    x, z, yaw = (centre, offset, 0.0) if axis == "x" else (offset, centre, -90.0)
    floor = min(ground) - WALL_DROP
    return [{"center": [x, (ceiling + floor) / 2, z], "size": [(last - first + 1) * cell + 2, ceiling - floor, 2], "yaw": yaw}]


def cull_pit_floor(primitive):
    """Drop the pit's floor faces so a fall through it reaches the kill floor instead of landing."""
    positions, indices = primitive["positions"], primitive["indices"]
    primitive["indices"] = [
        vertex
        for start in range(0, len(indices), 3)
        if not all(positions[3 * vertex + 1] <= PIT_FLOOR_Y for vertex in indices[start : start + 3])
        for vertex in indices[start : start + 3]
    ]
    return primitive


def pit_backdrop(material):
    return {
        "positions": [-66, -55, 42, 0, -55, 42, 0, -55, 118, -66, -55, 118],
        "indices": [0, 2, 1, 0, 3, 2],
        "uv": [],
        "rgba": [9, 11, 10, 255] * 4,
        "material": material,
    }


def floor_height(triangles, point):
    x, ceiling, z = point
    result = None
    for ((ax, ay, az), (bx, by, bz), (cx, cy, cz)), _surface in triangles:
        dx, dz = x - ax, z - az
        ux, uz = bx - ax, bz - az
        vx, vz = cx - ax, cz - az
        normal_y = uz * vx - ux * vz
        if normal_y <= 0:
            continue
        u = (dz * vx - dx * vz) / normal_y
        v = (dx * uz - dz * ux) / normal_y
        if min(u, v) < -1e-6 or u + v > 1 + 1e-6:
            continue
        height = ay + u * (by - ay) + v * (cy - ay)
        if height <= ceiling and (result is None or height > result):
            result = height
    return result


def read_accessor(gltf, data, index):
    accessor = gltf["accessors"][index]
    view = gltf["bufferViews"][accessor["bufferView"]]
    width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[accessor["type"]]
    component = {5121: "B", 5125: "I", 5126: "f"}[accessor["componentType"]]
    item = struct.Struct("<" + component * width)
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    stride = view.get("byteStride", item.size)
    return [item.unpack_from(data, offset + i * stride) for i in range(accessor["count"])]


def render_primitive(gltf, data, primitive, matrix, origin, scale):
    def attr(name):
        index = primitive["attributes"].get(name)
        return [] if index is None else read_accessor(gltf, data, index)

    positions = []
    for x, y, z in attr("POSITION"):
        point = [matrix[i] * x + matrix[i + 4] * y + matrix[i + 8] * z + matrix[i + 12] for i in range(3)]
        positions.extend(world_point(point, origin, scale))
    return {
        "positions": positions,
        "indices": reverse_winding(i for (i,) in read_accessor(gltf, data, primitive["indices"])),
        "uv": [n for u, v in attr("TEXCOORD_0") for n in (u, 1 - v)],
        "rgba": [n for color in attr("COLOR_0") for n in color],
        "material": primitive["material"],
    }


def unpack_map(source, runs):
    gltf = json.loads((source / "level.gltf").read_text())
    data = (source / gltf["buffers"][0]["uri"]).read_bytes()
    pickups = {item["placement"] for item in json.loads((source / "pickups.json").read_text())}
    materials = []
    for material in gltf["materials"]:
        texture_ref = material["pbrMetallicRoughness"].get("baseColorTexture")
        entry = {
            "alphaMode": material["alphaMode"],
            "alphaCutoff": material.get("alphaCutoff", 0.5),
            "doubleSided": material.get("doubleSided", False),
        }
        if texture_ref is not None:
            texture = gltf["textures"][texture_ref["index"]]
            entry.update(gltf["samplers"][texture["sampler"]], texture=gltf["images"][texture["source"]]["uri"])
        materials.append(entry)

    meshes = []
    for node in gltf["nodes"]:
        if node["extras"]["placement"] in pickups:
            continue
        primitives = gltf["meshes"][node["mesh"]]["primitives"]
        meshes.append(
            {
                "name": node["name"],
                "primitives": [
                    converted
                    for p in primitives
                    if (
                        converted := cull_pit_floor(render_primitive(gltf, data, p, node.get("matrix", IDENTITY), ORIGIN, SCALE))
                    )["indices"]
                ],
            }
        )
    rock = next(material for material in materials if material.get("texture", "").startswith("textures/0063-"))
    materials.append({**rock, "alphaMode": "OPAQUE", "doubleSided": True, "wrapS": 10497, "wrapT": 10497})
    meshes.append({"name": "PitBackdrop", "primitives": [pit_backdrop(len(materials))]})
    materials.append({"alphaMode": "OPAQUE", "doubleSided": True})
    vertices, indices = collision_mesh(arena_collision(runs), ORIGIN, SCALE)
    faces = [
        tuple(world_point(point, ORIGIN, SCALE) for point in points) for run in runs for points, _surface in run["triangles"]
    ]
    return {
        "meshes": meshes,
        "materials": materials,
        "perimeter": perimeter(faces),
        "collision": {"positions": [n for v in vertices for n in v], "indices": indices},
    }


def make_level(runs, spawns, manifest):
    terrain = [triangle for run in runs for triangle in run["triangles"]]

    def placement(point, yaw, clearance):
        x, y, z = point
        floor = floor_height(terrain, (x, y + 30, z))
        if floor is None or abs(floor - y) > 100:
            raise ValueError(f"No nearby walkable floor for {point}: {floor}")
        position = world_point((x, floor, z), ORIGIN, SCALE)
        position[1] += clearance
        return {"position": [round(n, 4) for n in position], "rotation": [0, yaw, 0]}

    def object_edit(catalog_id, position, pitch=0):
        payload = {
            "catalogId": catalog_id,
            "position": dict(zip("xyz", position, strict=True)),
            "rotation": {"x": pitch, "y": 0, "z": 0},
            "scale": dict.fromkeys("xyz", 1),
        }
        return {"opType": "object.place", "target": "", "payload": json.dumps(payload, separators=(",", ":"))}

    start = spawns[12]
    edits = [object_edit("bundle:conker/Colors", (0, 0, 0))]
    edits.extend(object_edit(asset, placement(point, 0, 0.5)["position"], UPRIGHT_PITCH) for asset, point in CHESTS)
    boss = placement((0, -1399, -3450), 0, 0)
    boss["hiddenChildren"] = ["BottomPiece"]
    return {
        "schemaVersion": 4,
        "baseline": "none",
        "map": 1,
        "stageIndex": 0,
        "tier": 0,
        "title": "Conker: Colors",
        "description": "Survive in the Colors arena from Conker's Bad Fur Day.",
        "mapDescription": "Cross the valley from the SHC base and summon the boss near the Tediz base.",
        "packs": {"conker": manifest["version"]},
        "grid": {"width": 15, "depth": 15, "cells": [{"x": 7, "z": 7, "height": -3}]},
        "spawn": placement(start["position"], (90 - start["yaw"] * 360 / 256) % 360, 2),
        "bossSpawner": boss,
        "killFloorY": KILL_FLOOR_Y,
        "pitRecoveryDamage": 15,
        "noGrass": True,
        "extraShrines": SHRINE_COUNT[0],
        "extraShrinesMax": SHRINE_COUNT[1],
        "extraShrineKinds": SHRINE_KINDS,
        "guaranteedShrineKinds": ["shadyGuy", *GUARANTEED_SHRINE_KINDS],
        "shrineKindRanges": {"microwave": [0, 1]},
        "chestLuckRange": list(CHEST_LUCK_RANGE),
        "minibossGroundSpots": [placement(point, 0, 0)["position"] for point in MINIBOSS_ANCHORS],
        "shrineSpots": [placement(point, 0, 0)["position"] for point in SHRINE_ANCHORS],
        "strictShrineSpots": True,
        "powerupSpots": [placement(point, 0, 0)["position"] for point in POWERUP_ANCHORS],
        "randomizePlacementsEachRun": True,
        "edits": edits,
    }


def extract(rom, checkout, output):
    result = subprocess.check_output(["git", "-C", checkout, "rev-parse", "HEAD"], text=True).strip()
    if result != EXTRACTOR_REV:
        raise ValueError(f"Check out conker.wtf revision {EXTRACTOR_REV} in {checkout}; found {result}")
    if subprocess.check_output(["git", "-C", checkout, "status", "--porcelain", "--untracked-files=no"], text=True):
        raise ValueError(f"Expected a clean conker.wtf checkout at {checkout}")
    subprocess.run(
        [
            "cargo",
            "run",
            "--locked",
            "--release",
            "--target-dir",
            WORK / "target",
            "-p",
            "conker-extract",
            "--",
            "--rom",
            rom.resolve(),
            "--out",
            output,
            "--force",
            "pack",
            "--map",
            "30",
        ],
        cwd=checkout,
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Prepare the local ROM-backed Conker Colors survival level")
    parser.add_argument("command", choices=("verify-rom", "extract", "prepare"))
    parser.add_argument("--rom", type=Path, default=os.getenv("CONKER_ROM") or ROOT / "tools/conker/rom/baserom.us.z64")
    parser.add_argument("--extractor", type=Path, default=os.getenv("CONKER_EXTRACTOR_DIR") or ROOT.parent / "conker_wtf")
    args = parser.parse_args()
    try:
        verify_rom(args.rom)
        source = WORK / "export/maps/30"
        if args.command == "extract":
            extract(args.rom, args.extractor, WORK / "export")
        elif args.command == "prepare":
            runs = json.loads((source / "collision.json").read_text())
            spawns = json.loads((source / "spawns.json").read_text())
            manifest = json.loads((ROOT / "unity/pack-authoring/packs/conker/manifest.json").read_text())
            level = make_level(runs, spawns, manifest)
            (WORK / "mesh.json").write_text(json.dumps(unpack_map(source, runs), separators=(",", ":")))
            (WORK / "conker-colors.mblevel.json").write_text(json.dumps(level, indent=2) + "\n")
            print(f"Prepared Colors: spawn {level['spawn']['position']}, boss spawner {level['bossSpawner']['position']}")
        else:
            print(f"Verified Conker US retail ROM: {args.rom}")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
