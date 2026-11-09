"""Bake construction-piece ownership of the legacy Warehouse's rails and supports."""

import json
import math
from build_thps_level import COPING_LIPS, MESH_RAILS, RAIL0_BAR_HEIGHT, RAIL0_LENGTH, rail_along
from check_thps_piece_inventory import DOC_PATH, OBJ_PATH, ROOT, read_pieces
from warehouse_surface import dot, euler_matrix, matmul, sub, unity_euler

PIECES = ROOT / "unity/pack-authoring/packs/thps/pieces.json"
OUTPUT = PIECES.with_name("attachments.json")
SCALE = 79.2
MESH_OWNERS = ("piece-rail-big-straight", "piece-rail-big-bend", "piece-rail-sign", "piece-rail-deck")
COPING_OWNERS = (
    ("piece-main-north-01", "piece-main-north-02", "piece-main-north-03"),
    ("piece-main-south-01", "piece-main-south-02", "piece-main-south-03"),
    ("piece-main-hip-north",),
    ("piece-main-hip-south",),
    ("piece-north-transition-west-01", "piece-north-transition-west-02"),
    ("piece-north-transition-middle",),
    ("piece-north-transition-east",),
    ("piece-north-upper-transition",),
    ("piece-south-transition-end", "piece-south-transition-west"),
    ("piece-pocket-side-west",),
    ("piece-pocket-side-west",),
    ("piece-pocket-side-west",),
    ("piece-pocket-tip-west",),
    ("piece-pocket-tip-east",),
    ("piece-pocket-side-east",),
    ("piece-pocket-return",),
    ("piece-pocket-return",),
    ("piece-pocket-return",),
    ("piece-south-transition-return", "piece-south-transition-middle", "piece-south-transition-east"),
    ("piece-southeast-corner",),
    ("piece-southeast-corner",),
    ("piece-southeast-corner",),
    ("piece-east-transition",),
    ("piece-ledge-west",),
    ("piece-ledge-west",),
    ("piece-ledge-west",),
    ("piece-ledge-west",),
    ("piece-start-transition-west", "piece-start-transition-east"),
)
SUPPORTS = {
    "piece-rail-big-straight": tuple(f"added-post-{i}" for i in range(5)),
    "piece-rail-big-bend": ("added-post-5", "added-post-6"),
    "piece-rail-deck": ("added-post-7", "added-post-8", "added-post-9"),
    "piece-kicker-north-board": ("piece-kicker-north-frame",),
    "piece-kicker-south-board": ("piece-kicker-south-frame",),
    "piece-room-floor": ("piece-room-underside-box",),
    "piece-room-roof": ("piece-room-chain-north", "piece-room-chain-south", "piece-room-brace-north-outer", "piece-room-brace-south-outer"),
}


def split_path(start, end, cuts, axis):
    parameters = [0.0] + [(cut - start[axis]) / (end[axis] - start[axis]) for cut in cuts] + [1.0]
    if parameters != sorted(parameters) or len(set(parameters)) != len(parameters) or parameters[0] != 0 or parameters[-1] != 1:
        raise ValueError("path cuts must lie strictly inside the ordered path")
    points = [tuple(a + (b - a) * t for a, b in zip(start, end, strict=True)) for t in parameters]
    segments = list(zip(points, points[1:]))
    if any(math.dist(a, b) <= 3.5 for a, b in segments):
        raise ValueError("a split creates a path too short for the 3.5-unit handoff radius")
    return segments


def local_transform(owner, position, rotation, scale):
    matrix = euler_matrix(*owner.get("rotation", [0, owner["yaw"], 0]))
    inverse = tuple(zip(*matrix, strict=True))
    owner_scale = owner.get("scale", [SCALE] * 3)
    child_scale = [scale] * 3 if isinstance(scale, (float, int)) else scale
    local_position = [dot(row, sub(position, owner["position"])) / size for row, size in zip(inverse, owner_scale, strict=True)]
    local_rotation = unity_euler(matmul(inverse, euler_matrix(*rotation)))
    return {"position": dict(zip("xyz", local_position, strict=True)), "rotation": dict(zip("xyz", local_rotation, strict=True)), "scale": dict(zip("xyz", [a / b for a, b in zip(child_scale, owner_scale, strict=True)], strict=True))}


def world_transform(owner, local):
    rotation = euler_matrix(*owner.get("rotation", [0, owner["yaw"], 0]))
    owner_scale = owner.get("scale", [SCALE] * 3)
    position = tuple(local["position"][axis] * size for axis, size in zip("xyz", owner_scale, strict=True))
    angles = unity_euler(matmul(rotation, euler_matrix(*(local["rotation"][axis] for axis in "xyz"))))
    return {"position": [dot(row, position) + offset for row, offset in zip(rotation, owner["position"], strict=True)], "rotation": angles, "scale": [local["scale"][axis] * size for axis, size in zip("xyz", owner_scale, strict=True)]}


def source_bounds():
    vertices, faces = [], []
    for line in OBJ_PATH.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            x, y, z = map(float, parts[1:4])
            vertices.append(((x - 1.519043) * SCALE + 100, -y * SCALE + 0.5, (z - 1.9661865) * SCALE))
        elif parts[0] == "f":
            faces.append([int(corner.split("/")[0]) - 1 for corner in parts[1:]])
    result = {}
    for piece in read_pieces(DOC_PATH.read_text()):
        points = [vertices[index] for ordinal in piece.faces for index in faces[ordinal - 1]]
        result[piece.id] = [(min(p[axis] for p in points), max(p[axis] for p in points)) for axis in range(3)]
    return result


def build():
    sidecar = json.loads(PIECES.read_text())
    pieces = {piece["asset"]: piece for piece in sidecar["pieces"]}
    bounds = source_bounds()
    assets = {}

    def add(owner, name, catalog, position, rotation, scale, hidden=False, start=None, end=None):
        child = {"name": name, "catalogId": catalog, "localTransform": local_transform(pieces[owner], position, rotation, scale), "hidden": hidden}
        if start is not None:
            child.update(start=list(start), end=list(end))
        assets.setdefault(owner, []).append(child)

    for i, (owner, (position, yaw, scale)) in enumerate(zip(MESH_OWNERS, MESH_RAILS, strict=True)):
        rotation = euler_matrix(0, yaw, 0)
        centre = [position[k] + rotation[k][1] * RAIL0_BAR_HEIGHT * scale for k in range(3)]
        endpoints = [tuple(centre[k] + sign * rotation[k][0] * RAIL0_LENGTH * scale / 2 for k in range(3)) for sign in (-1, 1)]
        add(owner, f"added-grind-mesh-{i}", "interactable/rail/0", position, (0, yaw, 0), scale, True, *endpoints)

    for i, ((start, end), owners) in enumerate(zip(COPING_LIPS, COPING_OWNERS, strict=True)):
        cuts = [bounds[owner][0][1] for owner in owners[:-1]]
        segments = split_path(start, end, cuts, axis=0) if cuts else [(start, end)]
        for n, (owner, (a, b)) in enumerate(zip(owners, segments, strict=True)):
            position, yaw, scale, pitch = rail_along(a, b)
            add(owner, f"added-grind-coping-{i}/{n}", "interactable/rail/0", position, (0, yaw, pitch), scale, True, a, b)

    for owner, supports in SUPPORTS.items():
        for support in supports:
            piece = pieces[support]
            add(owner, support, f"bundle:thps/{piece['catalogAsset']}", piece["position"], piece["rotation"], piece["scale"])
            assets[owner][-1]["sourceInstance"] = support
    canonical = {}
    for owner, children in assets.items():
        canonical.setdefault(pieces[owner]["catalogAsset"], children)
    return {"schema": "pack-attachments/1", "assets": canonical, "instances": assets}


def main():
    data = build()
    OUTPUT.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Warehouse attachments: {sum(map(len, data['assets'].values()))} attachments on {len(data['assets'])} pieces")


if __name__ == "__main__":
    main()
