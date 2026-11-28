#!/usr/bin/env python3
import argparse
import hashlib
import json
import kf1_bsp
import level_geometry as geometry
import math
import re
import struct
from build_thps_level import (
    BOSS_HIDDEN_CHILDREN,
    BOSS_SPAWN_SCALE,
    CHEST_LUCK_RANGE,
    GUARANTEED_SHRINE_KINDS,
    SHRINE_COUNT,
    SHRINE_KINDS,
)
from pathlib import Path
from PIL import Image
from warehouse_surface import UPRIGHT_PITCH

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".tools/kf1"
T3D_NAME = "KF-MountainPass.t3d"
MESH_NAME = "mesh.json"
LEVEL_NAME = "kf1-mountain-pass.mblevel.json"
PACK_ID = "kf1"
PACK_ASSET = "MountainPass"
PACK_VERSION = "1.0.0"
T3D_SHA256 = "87acc038e2e67c6176ea2396b7ffa20ce4bc91f6f27bd99a6546013380c5b02c"
TERRAIN_ACTOR = "TerrainInfo1"
ORIGIN = (0, 0, 0)
SCALE = 3.85 / 100  # Match Megabonk's standing capsule to the KFHumanPawn cylinder.
SAMPLE_UNITS = 64
VEHICLE_SCALE = 1.2  # KF1's vehicles read too small against Megabonk's player.
VEHICLE_MESHES = frozenset(
    {
        "KillingFloorStatics.London_police_car",
        "KillingFloorStatics.LanciaStatic1",
        "KillingFloorStatics.LondonCabASE",
        "KillingFloorStatics.ArmyTruck",
        "KillingFloorStatics.TWBus",
        "KillingFloorStatics.Ambulance",
        "KF-MountainPass.GUP-Lorry1",
        "KF-MountainPass.GUP-CamperTrailer",
    }
)
LORRY_PART_MESHES = frozenset(
    {"KF-MountainPass.GUP-LorryDoorLeft", "KF-MountainPass.GUP-LorryDoorRight", "KF-MountainPass.GUP-LorryCargoDoor"}
)
FLAT_HEIGHT = 32768
KILL_FLOOR_Y = -200.0
SPAWN_CLEARANCE = 2.0
CHEST_CLEARANCE = 0.5
REACH = 100
TERRAIN_RGBA = (96, 110, 70, 255)
MESH_UNITS = 100
ACTOR_CLASSES = frozenset(
    {
        "StaticMeshActor",
        "PlayerStart",
        "ZombieVolume",
        "ShopVolume",
        "KFRandomItemSpawn",
        "KFAmmoPickup",
        "BlockingVolume",
    }
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
        "packs",
        "edits",
    }
)
ACTOR_START = re.compile(r"^Begin Actor Class=(\w+) Name=(\S+)")
ACTOR_PROPERTY = re.compile(r"^    (Location|Rotation|DrawScale3D|DrawScale|StaticMesh|Skins\(\d+\))=(.*)$")
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
                "skins": {},
            }
            scalar = 1.0
        elif line.startswith("End Actor"):
            if current is not None and current["class"] in classes:
                current["scale"] = tuple(scalar * component for component in current["scale"])
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
            elif key == "DrawScale":
                scalar = float(value)
            elif key.startswith("Skins"):
                if skin := re.fullmatch(r"\w+'([^']+)'", value):
                    current["skins"][int(key[6:-1])] = skin[1]
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
    """A umodel glTF vertex (Y up, meters, Y and Z swapped) back in Unreal units, then scaled, rotated and moved."""
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
    return collision_triangles({"positions": positions, "indices": indices})


def collision_triangles(collision):
    positions, indices = collision["positions"], collision["indices"]
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


def bundle_placement_edit():
    """The edit that places the pack's one bundle asset, the whole map, at the origin."""
    placement = {
        "catalogId": f"bundle:{PACK_ID}/{PACK_ASSET}",
        "position": {"x": 0, "y": 0, "z": 0},
        "rotation": {"x": 0, "y": 0, "z": 0},
        "scale": {"x": 1, "y": 1, "z": 1},
    }
    return {"opType": "object.place", "target": "", "payload": json.dumps(placement, separators=(",", ":"))}


def make_level(terrain, actors, skipped=None):
    """Build level JSON from grounded anchors and report placements with no floor within reach."""
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
    shrine_spots = place_each("ShopVolume")
    nodes = named("PathNode")
    occupied = [spawn, max(grounded)[1], *shrine_spots]
    while nodes and len(shrine_spots) <= SHRINE_COUNT[1] + len(GUARANTEED_SHRINE_KINDS):

        def spacing(node):
            x, _, z = world_point(node["location"], ORIGIN, SCALE)
            return min(math.hypot(x - px, z - pz) for px, _, pz in occupied)

        node = max(nodes, key=spacing)
        nodes.remove(node)
        try:
            spot = place(node)
        except ValueError:
            continue
        if spot not in occupied:
            shrine_spots.append(spot)
            occupied.append(spot)
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
        "bossSpawner": {
            "position": max(grounded)[1],
            "rotation": [0, 0, 0],
            "hiddenChildren": geometry.BOSS_PORTAL_HIDDEN_CHILDREN,
        },
        "killFloorY": KILL_FLOOR_Y,
        "noGrass": True,
        "extraShrines": SHRINE_COUNT[0],
        "extraShrinesMax": SHRINE_COUNT[1],
        "extraShrineKinds": SHRINE_KINDS,
        "guaranteedShrineKinds": list(GUARANTEED_SHRINE_KINDS),
        "chestLuckRange": list(CHEST_LUCK_RANGE),
        "shrineSpots": shrine_spots,
        "powerupSpots": place_each("KFAmmoPickup"),
        "packs": {PACK_ID: PACK_VERSION},
        "edits": [
            bundle_placement_edit(),
            *(
                geometry.object_edit("interactable/chest", spot, UPRIGHT_PITCH)
                for spot in place_each("KFRandomItemSpawn", CHEST_CLEARANCE)
            ),
        ],
    }


def enlarge_vehicles(actors):
    """Copies of the actors with every car and truck scaled by VEHICLE_SCALE; lorry doors also move out from their lorry."""
    lorries = [actor["location"] for actor in actors if actor["mesh"] == "KF-MountainPass.GUP-Lorry1"]
    enlarged = []
    for actor in actors:
        if actor["mesh"] not in VEHICLE_MESHES | LORRY_PART_MESHES:
            enlarged.append(actor)
            continue
        location = actor["location"]
        if actor["mesh"] in LORRY_PART_MESHES and lorries:
            pivot = min(lorries, key=lambda lorry: math.dist(lorry, location))
            location = tuple(p + VEHICLE_SCALE * (c - p) for p, c in zip(pivot, location, strict=True))
        enlarged.append({**actor, "location": location, "scale": tuple(VEHICLE_SCALE * n for n in actor["scale"])})
    return enlarged


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


def parse_qualified(reference):
    """Split a Package.Group.Object reference; a two-part name has no group."""
    parts = reference.split(".")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], "", parts[1]
    raise ValueError(f"{reference} is not a qualified Unreal object name")


def exported_file(meshes, reference, kind="Texture"):
    """umodel's export for a qualified object, preferring the group folder so same-named objects stay distinct."""
    package, group, name = parse_qualified(reference)
    extension = ".gltf" if kind == "StaticMesh" else ".tga"
    candidates = [meshes / package / group / f"{name}{extension}"] if group else []
    candidates.append(meshes / package / kind / f"{name}{extension}")
    return next((path for path in candidates if path.is_file()), None)


def exported_asset(meshes, reference, kind="Texture"):
    """An exported object with its path and, for a texture, its pixel dimensions."""
    path = exported_file(meshes, reference, kind)
    if path is None:
        raise ValueError(f"{reference} is not exported under {meshes}")
    asset = {"reference": reference, "file": str(path.relative_to(meshes))}
    if kind == "Texture":
        with Image.open(path) as image:
            asset["width"], asset["height"] = image.size
    return asset


def mask_summary(path):
    """Which exported channel carries the layer weight, with that channel's statistics."""
    with Image.open(path) as image:
        red, green, blue, alpha = image.convert("RGBA").split()
    channels = {"alpha": alpha, "red": red, "green": green, "blue": blue}
    stats = {}
    for name, channel in channels.items():
        histogram = channel.histogram()
        total = sum(histogram)
        stats[name] = {
            "distinct": sum(1 for count in histogram if count),
            "mean": round(sum(value * count for value, count in enumerate(histogram)) / (255 * total), 3),
            "covered": round(sum(histogram[129:]) / total, 3),
        }
    weight = next((name for name in channels if stats[name]["distinct"] > 1), None)
    return {"channel": weight or "constant", **(stats[weight or "alpha"])}


def search_reference(fields, pattern):
    """The qualified object a T3D property names, empty when the property is absent."""
    match = re.search(pattern, fields)
    return match[1] if match else ""


def parse_terrain_layers(text):
    """TerrainInfo1's terrain and decoration layers, keyed by the numeric slots the export uses."""
    actor = re.search(rf"^Begin Actor Class=TerrainInfo Name={TERRAIN_ACTOR}\n(.*?)^End Actor\n", text, re.M | re.S)
    if not actor:
        raise ValueError(f"{TERRAIN_ACTOR} is missing from {T3D_NAME}")
    body = actor[1]

    def bounds(fields, pattern):
        match = re.search(pattern, fields)
        return [float(match[1]), float(match[2])] if match else [1.0, 1.0]

    layers = {}
    for slot, fields in re.findall(r"^    Layers\((\d+)\)=(.*)$", body, re.M):
        matrix = re.search(r"TerrainMatrix=\(XPlane=\(X=([-\d.]+)\),YPlane=\(Y=([-\d.]+)\)", fields)
        layers[int(slot)] = {
            "slot": int(slot),
            "diffuse": search_reference(fields, r"Texture=Texture'([^']+)'"),
            "mask": search_reference(fields, r"AlphaMap=Texture'([^']+)'"),
            "uscale": float(re.search(r"UScale=([-\d.]+)", fields)[1]),
            "vscale": float(re.search(r"VScale=([-\d.]+)", fields)[1]),
            "matrix": {"u": float(matrix[1]), "v": float(matrix[2])} if matrix else {"u": 0.0, "v": 0.0},
        }
    deco_layers = {}
    for slot, fields in re.findall(r"^    DecoLayers\((\d+)\)=(.*)$", body, re.M):
        deco_layers[int(slot)] = {
            "slot": int(slot),
            "mesh": search_reference(fields, r"StaticMesh=StaticMesh'([^']+)'"),
            "density_map": search_reference(fields, r"DensityMap=Texture'([^']+)'"),
            "align_to_terrain": "AlignToTerrain=1" in fields,
            "density": bounds(fields, r"DensityMultiplier=\(Min=([-\d.]+),Max=([-\d.]+)\)"),
            "scale": {axis.lower(): bounds(fields, rf"{axis}=\(Min=([-\d.]+),Max=([-\d.]+)\)") for axis in "XYZ"},
        }
    heightmap = re.search(r"^    TerrainMap=Texture'([^']+)'$", body, re.M)
    offset = re.search(r"^    DecoLayerOffset=([-\d.]+)$", body, re.M)
    return {
        "heightmap": heightmap[1] if heightmap else "",
        "deco_offset": float(offset[1]) if offset else 0.0,
        "layers": layers,
        "deco_layers": deco_layers,
    }


def terrain_inventory(meshes, text):
    """One row per occupied terrain slot with its exported sources, mask channel, dimensions and UV settings."""
    terrain = parse_terrain_layers(text)
    masks = {layer["mask"] for layer in terrain["layers"].values()} | {
        layer["density_map"] for layer in terrain["deco_layers"].values()
    }
    rows = []
    for slot, layer in sorted(terrain["layers"].items()):
        mask = exported_asset(meshes, layer["mask"]) if layer["mask"] else None
        if mask:
            mask.update(mask_summary(meshes / mask["file"]))
        rows.append(
            {
                "slot": slot,
                "role": "mask-as-diffuse" if layer["diffuse"] in masks else "ground",
                "diffuse": exported_asset(meshes, layer["diffuse"]),
                "mask": mask,
                "uscale": layer["uscale"],
                "vscale": layer["vscale"],
                "units_per_tile": [SAMPLE_UNITS * layer["uscale"], SAMPLE_UNITS * layer["vscale"]],
                "deco_layers": [
                    slot for slot, deco in sorted(terrain["deco_layers"].items()) if deco["density_map"] == layer["mask"]
                ],
            }
        )
    deco = [
        {
            "slot": slot,
            "mesh": exported_asset(meshes, layer["mesh"], "StaticMesh"),
            "density_map": exported_asset(meshes, layer["density_map"]),
            "align_to_terrain": layer["align_to_terrain"],
            "density": layer["density"],
            "scale": layer["scale"],
        }
        for slot, layer in sorted(terrain["deco_layers"].items())
    ]
    return {
        "heightmap": terrain["heightmap"],
        "deco_offset": terrain["deco_offset"],
        "layers": rows,
        "deco_layers": deco,
    }


def terrain_table(inventory):
    """The markdown terrain layer table for docs/kf1-mountain-pass.md, one row per occupied slot."""
    columns = (
        "slot",
        "role",
        "diffuse",
        "mask",
        "weight channel",
        "diffuse size",
        "mask size",
        "UScale",
        "VScale",
        "units per tile",
    )
    lines = ["| " + " | ".join(columns) + " |", "|" + " --- |" * len(columns)]
    for row in inventory["layers"]:
        mask = row["mask"] or {}
        u, v = row["units_per_tile"]
        lines.append(
            "| "
            + " | ".join(
                (
                    str(row["slot"]),
                    row["role"],
                    row["diffuse"]["reference"],
                    mask.get("reference", ""),
                    mask.get("channel", ""),
                    f'{row["diffuse"]["width"]}x{row["diffuse"]["height"]}',
                    f'{mask.get("width", 0)}x{mask.get("height", 0)}',
                    f'{row["uscale"]:g}',
                    f'{row["vscale"]:g}',
                    f"{u:g}" if u == v else f"{u:g}x{v:g}",
                )
            )
            + " |"
        )
    return lines


def parse_brushes(text):
    """Every CSG brush in level order, with the polygon data the boolean pass needs."""
    brushes = []
    for actor in re.finditer(r"^Begin Actor Class=Brush Name=(\S+)(.*?)^End Actor", text, re.M | re.S):
        name, body = actor.groups()
        operation = re.search(r"^    CsgOper=(CSG_Add|CSG_Subtract)$", body, re.M)
        if not operation:
            continue
        vectors = {key: _vector(value, "XYZ", ORIGIN) for key, value in re.findall(r"^    (Location|PrePivot)=(.*)$", body, re.M)}
        offset = tuple(a - b for a, b in zip(vectors.get("Location", ORIGIN), vectors.get("PrePivot", ORIGIN), strict=True))
        faces = []
        for header, lines in re.findall(r"Begin Polygon([^\n]*)\n(.*?)End Polygon", body, re.S):
            reference = re.search(r"\bTexture=(\S+)", header)
            face = {"texture": reference[1] if reference else "", "Vertex": []}
            for key, value in re.findall(r"^\s*(Origin|TextureU|TextureV|Vertex|Normal)\s+([^\n]+)", lines, re.M):
                vector = tuple(map(float, value.split(",")))
                if key == "Vertex":
                    face[key].append(vector)
                else:
                    face[key] = vector
            faces.append(face)
        if faces:
            brushes.append({"name": name, "op": operation[1], "offset": offset, "faces": faces})
    return brushes


def brush_material(meshes, reference):
    package, *groups, name = reference.split(".") if reference else ("", "")
    folder = meshes / package
    shader = folder / "Shader" / f"{name}.mat"
    if shader.exists() and (diffuse := re.search(r"^Diffuse=(.+)$", shader.read_text(), re.M)):
        name = diffuse[1]
    texture = folder / "Texture" / f"{name}.tga"
    if groups and (grouped := folder / groups[-1] / f"{name}.tga").is_file():
        texture = grouped
    material = {"name": reference, "alphaMode": "OPAQUE", "doubleSided": False}
    if texture.is_file():
        with Image.open(texture) as image:
            size = image.size
        material.update(texture=str(texture.relative_to(meshes.parent)), wrapS=10497, wrapT=10497)
    else:
        size = (1, 1)
        material["baseColor"] = [0.32, 0.31, 0.29, 1]
        if reference.endswith(".LondonStreetTarmac"):
            material["baseColor"] = [0.16, 0.15, 0.14, 1]
        if reference == "Engine.BlackTexture":
            material["baseColor"] = [0, 0, 0, 1]
    return material, size


def append_brushes(meshes, brushes, materials, rendered, positions, indices):
    """The approximate pass: every additive brush as its own shell of polygons."""
    lookup = {}
    for brush in brushes:
        name, offset, faces = brush["name"], brush["offset"], brush["faces"]
        if brush["op"] != kf1_bsp.ADD:
            continue
        if all(face["texture"] == "Engine.BlackTexture" for face in faces):
            continue
        primitives = {}
        for face in faces:
            reference = face["texture"]
            if reference not in lookup:
                material, size = brush_material(meshes, reference)
                lookup[reference] = len(materials), size
                materials.append(material)
            index, (width, height) = lookup[reference]
            primitive = primitives.setdefault(index, {"positions": [], "indices": [], "uv": [], "rgba": [], "material": index})
            first = len(primitive["positions"]) // 3
            collision_start = len(positions) // 3
            for vertex in face["Vertex"]:
                world = [a + b for a, b in zip(vertex, offset, strict=True)]
                point = [round(n, 4) for n in world_point(world, ORIGIN, SCALE)]
                positions.extend(point)
                primitive["positions"].extend(point)
                if color := materials[index].get("baseColor"):
                    primitive["rgba"].extend(round(v * 255) for v in color)
                delta = [a - b for a, b in zip(vertex, face["Origin"], strict=True)]
                primitive["uv"].extend(
                    (math.sumprod(delta, face["TextureU"]) / width, 1 - math.sumprod(delta, face["TextureV"]) / height)
                )
            for i in range(1, len(face["Vertex"]) - 1):
                indices.extend((collision_start, collision_start + i, collision_start + i + 1))
                primitive["indices"].extend((first, first + i, first + i + 1))
        rendered.append({"name": name, "primitives": list(primitives.values())})


def append_compiled(meshes, compiled, sources, materials, rendered, positions, indices):
    """The boolean skin: each triangle keeps the texture and UV basis of the brush face it came from."""
    lookup, hidden, groups = {}, {}, {}
    for name, face_index, triangle in compiled.triangles:
        if name not in hidden:
            hidden[name] = all(face["texture"] == "Engine.BlackTexture" for face in sources[name]["faces"])
        if hidden[name]:
            continue
        face = sources[name]["faces"][face_index] if face_index is not None else None
        reference = face["texture"] if face else ""
        if reference not in lookup:
            material, size = brush_material(meshes, reference)
            lookup[reference] = len(materials), size
            materials.append(material)
        index, (width, height) = lookup[reference]
        group = groups.setdefault(name, {})
        primitive = group.setdefault(index, {"positions": [], "indices": [], "uv": [], "rgba": [], "material": index})
        first = len(primitive["positions"]) // 3
        collision_start = len(positions) // 3
        origin = [a + b for a, b in zip(face["Origin"], sources[name]["offset"], strict=True)] if face else (0, 0, 0)
        axis_u, axis_v = (face["TextureU"], face["TextureV"]) if face else ((1, 0, 0), (0, 1, 0))
        for vertex in triangle:
            point = [round(n, 4) for n in world_point(vertex, ORIGIN, SCALE)]
            positions.extend(point)
            primitive["positions"].extend(point)
            if color := materials[index].get("baseColor"):
                primitive["rgba"].extend(round(v * 255) for v in color)
            delta = [a - b for a, b in zip(vertex, origin, strict=True)]
            primitive["uv"].extend((math.sumprod(delta, axis_u) / width, 1 - math.sumprod(delta, axis_v) / height))
        indices.extend((collision_start, collision_start + 1, collision_start + 2))
        primitive["indices"].extend((first, first + 1, first + 2))
    for name, primitives in groups.items():
        rendered.append({"name": name, "primitives": list(primitives.values())})


def material_index(meshes):
    index = {}
    for pattern in ("*/*/*.tga", "*/*/*.mat"):
        for path in meshes.glob(pattern):
            index.setdefault(path.stem.casefold(), []).append(path)
    return index


def static_material(index, meshes, reference, source, explicit_skin=False):
    package, *_, name = reference.split(".")
    material = {"name": reference, "doubleSided": True, "alphaMode": "OPAQUE"}
    visited = set()
    while name.casefold() not in visited:
        visited.add(name.casefold())
        candidates = index.get(name.casefold(), [])
        local = [p for p in candidates if p.parents[1].name.casefold() == package.casefold()]
        if not local and (explicit_skin or len(candidates) != 1):
            break
        path = (local or candidates)[0]
        if path.suffix == ".tga":
            material.update(texture=str(path.relative_to(meshes.parent)), wrapS=10497, wrapT=10497)
            with Image.open(path) as image:
                if "A" in image.getbands() and image.getextrema()[-1][0] < 128 <= image.getextrema()[-1][1]:
                    material.update(alphaMode="MASK", alphaCutoff=0.5)
            return material
        diffuse = re.search(r"^Diffuse=(.+)$", path.read_text(errors="replace"), re.M)
        if not diffuse:
            break
        package, name = path.parents[1].name, diffuse[1].strip()
    material["baseColor"] = source.get("pbrMetallicRoughness", {}).get("baseColorFactor", [0.3, 0.3, 0.3, 1])
    return material


def unpack_map(meshes, actors, heights, terrain, brushes=(), csg=False, compiled=None):
    """The survival level's mesh document: terrain, static meshes and the brush world."""
    if compiled is None and csg:
        compiled = kf1_bsp.compile_brushes(brushes)
    materials = [{"alphaMode": "OPAQUE", "doubleSided": False}]
    index = material_index(meshes)
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
            slot = primitive.get("material", 0)
            source = gltf.get("materials", [{}])[slot]
            skins = actor.get("skins", {})
            reference = skins.get(slot, f"{path.parents[1].name}.{source.get('name', '')}")
            key = path, slot, reference
            if key not in lookup:
                lookup[key] = len(materials)
                materials.append(static_material(index, meshes, reference, source, explicit_skin=slot in skins))
            primitives.append(
                render_primitive(
                    gltf, data, primitive, actor["rotation"], actor["scale"], actor["location"], ORIGIN, SCALE, lookup[key]
                )
            )
            converted = primitives[-1]
            color = materials[lookup[key]].get("baseColor")
            if color and not converted["rgba"]:
                converted["rgba"] = [round(v * 255) for v in color] * (len(converted["positions"]) // 3)
        rendered.append({"name": actor["name"], "primitives": primitives})
    positions, indices = terrain_mesh(heights, ORIGIN, SCALE)
    if compiled is not None:
        append_compiled(meshes, compiled, {brush["name"]: brush for brush in brushes}, materials, rendered, positions, indices)
    append_brushes(meshes, compiled.uncarved if compiled is not None else brushes, materials, rendered, positions, indices)
    return {
        "meshes": rendered,
        "materials": materials,
        "perimeter": walls(terrain),
        "collision": {"positions": [round(n, 4) for n in positions], "indices": indices},
    }


def pack_textures(work):
    """The textures the pack build reads, deduplicated; names the material when one is missing."""
    path = work / MESH_NAME
    if not path.is_file():
        raise ValueError(f"{path} is missing: run uv run scripts/kf1_mountain_pass.py prepare first")
    found = []
    for material in json.loads(path.read_text()).get("materials", ()):
        texture = material.get("texture")
        if not texture:
            continue
        if not (work / texture).is_file():
            name = material.get("name") or "<unnamed material>"
            raise ValueError(f"material {name} needs texture {texture}, which is not under {work}")
        if texture not in found:
            found.append(texture)
    return [Path(texture) for texture in found]


def prepare(source, meshes, output, csg=False):
    t3d = source / "KF-MountainPass.t3d"
    verify_export(t3d)
    text = t3d.read_text(encoding="latin-1")
    actors = parse_actors(text, ACTOR_CLASSES | {"PathNode"})
    heights = read_heightmap((source / "Terrain_Main.bmp").read_bytes())
    terrain = terrain_triangles(heights, ORIGIN, SCALE)
    skipped = []
    brushes = parse_brushes(text)
    compiled = kf1_bsp.compile_brushes(brushes) if csg else None
    mesh = unpack_map(meshes, enlarge_vehicles(actors), heights, terrain, brushes, compiled=compiled)
    level = make_level(collision_triangles(mesh["collision"]), actors, skipped)
    (output / MESH_NAME).write_text(json.dumps(mesh, separators=(",", ":")))
    (output / LEVEL_NAME).write_text(json.dumps(level, indent=2) + "\n")
    return level, skipped, compiled


def terrain_inventory_command(work):
    """Write the terrain layer inventory and print its table; returns the inventory."""
    t3d = work / "export" / T3D_NAME
    verify_export(t3d)
    inventory = terrain_inventory(work / "out", t3d.read_text(encoding="latin-1"))
    (work / "terrain_layers.json").write_text(json.dumps(inventory, indent=2) + "\n")
    return inventory


def main():
    parser = argparse.ArgumentParser(description="Prepare the local Killing Floor 1 Mountain Pass survival level")
    parser.add_argument("command", choices=("verify-export", "prepare", "terrain-inventory", "verify-pack"))
    parser.add_argument("--work", type=Path, default=WORK)
    parser.add_argument("--csg", action="store_true", help="build the brush world with ordered additive and subtractive CSG")
    args = parser.parse_args()
    try:
        source = args.work / "export"
        if args.command == "verify-export":
            verify_export(source / T3D_NAME)
            print(f"Verified the KF-MountainPass level export: {source}")
        elif args.command == "terrain-inventory":
            inventory = terrain_inventory_command(args.work)
            print("\n".join(terrain_table(inventory)))
            print(f"{len(inventory['layers'])} terrain layers, {len(inventory['deco_layers'])} decoration layers")
        elif args.command == "verify-pack":
            textures = pack_textures(args.work)
            print(f"Pack inputs ready: {args.work / MESH_NAME} with {len(textures)} textures")
        else:
            level, skipped, compiled = prepare(source, args.work / "out", args.work, csg=args.csg)
            for item in skipped:
                print(f"Skipped {item}")
            if compiled is not None:
                print(
                    f"Compiled BSP: {len(compiled.triangles)} triangles, {compiled.estimated} matched by the nearest face, "
                    f"{len(compiled.uncarved)} brushes approximate, {len(compiled.cutters)} cutters dropped"
                )
            print(f"Prepared Mountain Pass: spawn {level['spawn']['position']}, boss spawner {level['bossSpawner']['position']}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
