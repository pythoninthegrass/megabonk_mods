"""
The Warehouse collider as world-space triangles, with the ray, overlap and rotation helpers that anchor items to it.

The mesh is read the way unity/pack-authoring/Assets/Editor/ThpsPack.cs imports it, so a point here is the same point the game's MeshCollider has. Rotations are 3x3 row tuples in Unity's frame, with euler angles applied as Rz, then Rx, then Ry.
"""

import math
from pathlib import Path
from typing import NamedTuple

Vec = tuple[float, float, float]
Triangle = tuple[Vec, Vec, Vec]
Matrix = tuple[Vec, Vec, Vec]

EPSILON = 1e-9
# A ridge edge rises or falls at most this much per unit of horizontal length.
RIDGE_MAX_GRADE = 0.3
# A face is flat below this many degrees and a wall from this many.
FLAT_SLOPE = 15.0
WALL_SLOPE = 89.0
IDENTITY: Matrix = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
# Chest, shrine and merchant prefabs are authored lying down with their up along +z, so they stand up at pitch 270.
UPRIGHT_PITCH = 270.0


class Hit(NamedTuple):
    y: float
    normal: Vec
    index: int


def sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def normalize(v: Vec) -> Vec:
    length = math.sqrt(dot(v, v))
    return (v[0] / length, v[1] / length, v[2] / length)


def triangle_normal(t: Triangle) -> Vec:
    return normalize(cross(sub(t[1], t[0]), sub(t[2], t[0])))


def drop(triangles: list[Triangle], x: float, y: float, z: float) -> Hit | None:
    """The highest triangle at or below (x, y, z), as its height at x and z and its upward-facing normal."""
    best: Hit | None = None
    for index, (a, b, c) in enumerate(triangles):
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < EPSILON:
            continue
        l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
        l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) < -EPSILON:
            continue
        height = l1 * a[1] + l2 * b[1] + l3 * c[1]
        if height > y + EPSILON or (best is not None and height <= best.y):
            continue
        normal = triangle_normal((a, b, c))
        best = Hit(height, normal if normal[1] >= 0 else (-normal[0], -normal[1], -normal[2]), index)
    return best


def box_hits(triangles: list[Triangle], center: Vec, rotation: Matrix, half: Vec) -> list[int]:
    """Indices of the triangles that intersect the oriented box, by separating axes."""
    axes = [(rotation[0][i], rotation[1][i], rotation[2][i]) for i in range(3)]
    reach = max(half) * math.sqrt(3)
    hits = []
    for index, t in enumerate(triangles):
        if any(min(v[k] for v in t) > center[k] + reach or max(v[k] for v in t) < center[k] - reach for k in range(3)):
            continue
        if _box_meets_triangle(center, axes, half, t):
            hits.append(index)
    return hits


def _box_meets_triangle(center: Vec, axes: list[Vec], half: Vec, t: Triangle) -> bool:
    points = [sub(v, center) for v in t]
    edges = [sub(points[1], points[0]), sub(points[2], points[1]), sub(points[0], points[2])]
    candidates = list(axes) + [cross(edges[0], edges[1])] + [cross(e, a) for e in edges for a in axes]
    for axis in candidates:
        if dot(axis, axis) < EPSILON:
            continue
        radius = sum(half[i] * abs(dot(axes[i], axis)) for i in range(3))
        projected = [dot(p, axis) for p in points]
        if min(projected) > radius or max(projected) < -radius:
            return False
    return True


def euler_matrix(x: float, y: float, z: float) -> Matrix:
    """Unity's Quaternion.Euler as a matrix: Rz, then Rx, then Ry, angles in degrees."""
    return matmul(matmul(_ry(y), _rx(x)), _rz(z))


def unity_euler(rotation: Matrix) -> Vec:
    pitch = math.asin(max(-1.0, min(1.0, -rotation[1][2])))
    if abs(rotation[1][2]) > 1 - 1e-9:
        yaw, roll = math.atan2(-rotation[2][0], rotation[0][0]), 0.0
    else:
        yaw, roll = math.atan2(rotation[0][2], rotation[2][2]), math.atan2(rotation[1][0], rotation[1][1])
    return tuple(math.degrees(angle) % 360 for angle in (pitch, yaw, roll))


def tilt_rotation(normal: Vec, yaw: float) -> Matrix:
    """Yaw about the up axis, then the shortest turn from up to the surface normal."""
    up = (0.0, 1.0, 0.0)
    axis = cross(up, normal)
    cosine = dot(up, normal)
    k = ((0, -axis[2], axis[1]), (axis[2], 0, -axis[0]), (-axis[1], axis[0], 0))
    k2 = matmul(k, k)
    turn = tuple(tuple(IDENTITY[r][c] + k[r][c] + k2[r][c] / (1 + cosine) for c in range(3)) for r in range(3))
    return matmul(turn, _ry(yaw))


def item_rotation(normal: Vec, yaw: float) -> Matrix:
    """A prefab authored lying down, stood up and then tilted onto the surface."""
    return matmul(tilt_rotation(normal, yaw), _rx(UPRIGHT_PITCH))


def matmul(a: Matrix, b: Matrix) -> Matrix:
    return tuple(tuple(sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)) for r in range(3))


def _rx(degrees: float) -> Matrix:
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return ((1, 0, 0), (0, c, -s), (0, s, c))


def _ry(degrees: float) -> Matrix:
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return ((c, 0, s), (0, 1, 0), (-s, 0, c))


def _rz(degrees: float) -> Matrix:
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return ((c, -s, 0), (s, c, 0), (0, 0, 1))


def read_obj(path: Path) -> tuple[list[Triangle], tuple[float, float]]:
    """Triangles in OBJ units with y up, quads split the way the pack importer splits them, and the x and z centre of every vertex."""
    positions: list[Vec] = []
    triangles: list[Triangle] = []
    for line in path.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            positions.append((float(parts[1]), -float(parts[2]), float(parts[3])))
        elif parts[0] == "f":
            corners = [positions[int(token.split("/")[0]) - 1] for token in parts[1:]]
            triangles.extend((corners[0], corners[i + 1], corners[i]) for i in range(1, len(corners) - 1))
    xs = [p[0] for p in positions]
    zs = [p[2] for p in positions]
    return triangles, ((min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2)


class Placement(NamedTuple):
    """Where the Warehouse prefab sits in the level: the OBJ x and z centre it is centred on, its scale, and its world x, lift and z."""

    centre: tuple[float, float]
    scale: float
    world_x: float
    lift: float
    world_z: float

    def point(self, v: Vec) -> Vec:
        return (
            (v[0] - self.centre[0]) * self.scale + self.world_x,
            v[1] * self.scale + self.lift,
            (v[2] - self.centre[1]) * self.scale + self.world_z,
        )

    def triangles(self, triangles: list[Triangle]) -> list[Triangle]:
        return [tuple(self.point(v) for v in t) for t in triangles]


def _upward_normal(t: Triangle) -> Vec:
    n = triangle_normal(t)
    return n if n[1] >= 0 else (-n[0], -n[1], -n[2])


def _slope_degrees(normal: Vec) -> float:
    return math.degrees(math.acos(min(1.0, normal[1])))


def _round_point(p: Vec) -> Vec:
    return (round(p[0], 2), round(p[1], 2), round(p[2], 2))


def _extends(run: tuple[Vec, Vec], edge: tuple[Vec, Vec]) -> tuple[Vec, Vec] | None:
    """The run grown by `edge` when they share an end and point the same way, else None."""
    for i in (0, 1):
        for j in (0, 1):
            if math.dist(run[i], edge[j]) > 0.02:
                continue
            a, b = sub(run[1 - i], run[i]), sub(edge[1 - j], edge[j])
            if math.dist(cross(a, b), (0, 0, 0)) > 0.02 * math.sqrt(dot(a, a) * dot(b, b)) or dot(a, b) > 0:
                continue
            return run[1 - i], edge[1 - j]
    return None


def _below_edge(p: Vec, q: Vec, v: Vec) -> bool:
    """Whether v lies lower than the edge p-q at the edge's point nearest v in plan."""
    dx, dz = q[0] - p[0], q[2] - p[2]
    t = max(0.0, min(1.0, ((v[0] - p[0]) * dx + (v[2] - p[2]) * dz) / (dx * dx + dz * dz)))
    return v[1] < p[1] + t * (q[1] - p[1]) - 0.05


Face = tuple[Vec, Vec]


def _is_ridge(p: Vec, q: Vec, a: Face, b: Face, min_slope: float) -> bool:
    (n1, o1), (n2, o2) = a, b
    falls_away = _below_edge(p, q, o1) and _below_edge(p, q, o2) and n1[0] * n2[0] + n1[2] * n2[2] < 0
    return falls_away and max(_slope_degrees(n1), _slope_degrees(n2)) > min_slope


def _is_deck_lip(p: Vec, q: Vec, a: Face, b: Face, min_slope: float) -> bool:
    ramp, deck = (a, b) if _slope_degrees(a[0]) >= _slope_degrees(b[0]) else (b, a)
    return _slope_degrees(ramp[0]) > min_slope and _slope_degrees(ramp[0]) < WALL_SLOPE and _slope_degrees(deck[0]) < FLAT_SLOPE and _below_edge(p, q, ramp[1]) and not _below_edge(p, q, deck[1])


def _edges_where(triangles: list[Triangle], max_grade: float, min_slope: float, tests: tuple) -> list[tuple[Vec, Vec]]:
    shared: dict[tuple[Vec, Vec], list[Face]] = {}
    for t in triangles:
        normal = _upward_normal(t)
        for a, b, other in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
            edge = tuple(sorted((_round_point(t[a]), _round_point(t[b]))))
            shared.setdefault(edge, []).append((normal, t[other]))
    edges = []
    for (p, q), faces in shared.items():
        run = math.hypot(q[0] - p[0], q[2] - p[2])
        if len(faces) == 2 and run >= 0.1 and abs(p[1] - q[1]) <= max_grade * run and any(test(p, q, *faces, min_slope) for test in tests):
            edges.append((p, q))
    return edges


def _merged(edges: list[tuple[Vec, Vec]], min_length: float) -> list[tuple[Vec, Vec]]:
    runs = list(edges)
    merged = True
    while merged:
        merged = False
        for i, run in enumerate(runs):
            for j in range(i + 1, len(runs)):
                grown = _extends(run, runs[j])
                if grown:
                    runs[i] = grown
                    del runs[j]
                    merged = True
                    break
            if merged:
                break
    return [r for r in runs if math.dist(*r) >= min_length]


def ridge_runs(triangles: list[Triangle], min_length: float = 2.0, min_slope: float = 20.0, max_grade: float = RIDGE_MAX_GRADE) -> list[tuple[Vec, Vec]]:
    """Edges rising or falling at most `max_grade` where two faces fall away from each other, one at least `min_slope` degrees steep, merged into straight runs of at least `min_length`."""
    return _merged(_edges_where(triangles, max_grade, min_slope, (_is_ridge,)), min_length)


def lip_runs(triangles: list[Triangle], min_length: float = 2.0, min_slope: float = 20.0, max_grade: float = RIDGE_MAX_GRADE) -> list[tuple[Vec, Vec]]:
    """Ridge edges plus the top of a ramp that meets a flat deck, merged into straight runs of at least `min_length`."""
    return _merged(_edges_where(triangles, max_grade, min_slope, (_is_ridge, _is_deck_lip)), min_length)
