import json
import math
import struct
import warehouse_surface as ws

CELL_SIZE = 2.0
WALL_HEADROOM = 1000.0
WALL_DROP = 28.0
STEP_TOLERANCE = 12.0


def reverse_winding(indices):
    return [index for a, b, c in zip(*[iter(indices)] * 3, strict=True) for index in (a, c, b)]


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


def walkable_cells(triangles, cell=CELL_SIZE, max_slope_degrees=45.0, kill_floor=float("-inf")):
    """Grid cells the player can stand on, keyed by plan index and holding the highest walkable surface in each."""
    gentle = math.cos(math.radians(max_slope_degrees))
    cells = {}
    for a, b, c in triangles:
        if max(a[1], b[1], c[1]) < kill_floor:
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


def playable_cells(
    triangles,
    cell=CELL_SIZE,
    max_slope_degrees=45.0,
    seeds=None,
    anchors=(),
    kill_floor=float("-inf"),
    pit_floor=float("-inf"),
):
    """The top surface as the player can use it: walkable cells above the pit floor, connected to a seed or anchor cell."""
    cells = {
        key: height
        for key, height in walkable_cells(triangles, cell, max_slope_degrees, kill_floor).items()
        if height > pit_floor
    }
    if seeds is None:
        seeds = {key for key in anchors if key in cells} or set(cells)
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


def perimeter(
    triangles,
    cell=CELL_SIZE,
    max_slope_degrees=90.0,
    seeds=None,
    anchors=(),
    kill_floor=float("-inf"),
    pit_floor=float("-inf"),
    headroom=WALL_HEADROOM,
    drop=WALL_DROP,
    step_tolerance=STEP_TOLERANCE,
):
    """Walls around the top terrain, including steep slopes that are part of the arena."""
    cells = playable_cells(triangles, cell, max_slope_degrees, seeds, anchors, kill_floor, pit_floor)
    if not cells:
        return []
    open_air = _beyond(cells)
    ceiling = max(point[1] for face in triangles for point in face) + headroom
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
            walls.extend(_fence(axis, line, first, last, heights, ceiling, cell, drop, step_tolerance))
    return walls


def _fence(axis, line, first, last, heights, ceiling, cell, drop, step_tolerance):
    """A wall to the shared ceiling, split where the ground steps."""
    ground = [heights[position] for position in range(first, last + 1)]
    if last > first and max(ground) - min(ground) > step_tolerance:
        middle = (first + last) // 2
        return _fence(axis, line, first, middle, heights, ceiling, cell, drop, step_tolerance) + _fence(
            axis, line, middle + 1, last, heights, ceiling, cell, drop, step_tolerance
        )
    centre = (first + last + 1) / 2 * cell
    offset = line * cell
    x, z, yaw = (centre, offset, 0.0) if axis == "x" else (offset, centre, -90.0)
    floor = min(ground) - drop
    return [{"center": [x, (ceiling + floor) / 2, z], "size": [(last - first + 1) * cell + 2, ceiling - floor, 2], "yaw": yaw}]


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
    component = {5121: "B", 5123: "H", 5125: "I", 5126: "f"}[accessor["componentType"]]
    item = struct.Struct("<" + component * width)
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    stride = view.get("byteStride", item.size)
    return [item.unpack_from(data, offset + i * stride) for i in range(accessor["count"])]


def object_edit(catalog_id, position, pitch=0):
    payload = {
        "catalogId": catalog_id,
        "position": dict(zip("xyz", position, strict=True)),
        "rotation": {"x": pitch, "y": 0, "z": 0},
        "scale": dict.fromkeys("xyz", 1),
    }
    return {"opType": "object.place", "target": "", "payload": json.dumps(payload, separators=(",", ":"))}
