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
