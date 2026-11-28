"""Ordered additive and subtractive CSG for the KF1 brush world.

Brushes are folded in T3D actor order, the way Unreal Engine 2 compiles a level: an additive brush
joins the solid geometry and a subtractive brush only cuts solid geometry that already exists.
"""

import manifold3d
import math
import numpy as np
import typing

ADD = "CSG_Add"
WELD = 4
ANGLE = 1e-3
PLANE = 0.05


class Compiled(typing.NamedTuple):
    """The boolean result, plus the brushes that could not take part in it."""

    triangles: list
    uncarved: list
    cutters: list
    estimated: int


def _placed(brush):
    """A brush's polygons moved into the shared map space the boolean runs in."""
    offset = brush["offset"]
    faces = []
    for face in brush["faces"]:
        vertices = [tuple(a + b for a, b in zip(vertex, offset, strict=True)) for vertex in face["Vertex"]]
        faces.append({"texture": face["texture"], "Normal": face.get("Normal"), "Vertex": vertices})
    return faces


def _ring(face):
    """A polygon's vertex ring, without a vertex repeated at the seam."""
    ring = list(face["Vertex"])
    while len(ring) > 3 and all(abs(a - b) < 1e-6 for a, b in zip(ring[0], ring[-1], strict=True)):
        ring.pop()
    return ring


def _cross(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def _dot(u, v):
    return sum(a * b for a, b in zip(u, v, strict=True))


def _fan(face):
    """A polygon as triangles, wound so their normals follow the exported Normal."""
    ring = _ring(face)
    if len(ring) < 3:
        return []
    fan = [(ring[0], ring[index], ring[index + 1]) for index in range(1, len(ring) - 1)]
    first = fan[0]
    normal = face.get("Normal")
    if normal and any(normal):
        span = [[first[j][axis] - first[0][axis] for axis in range(3)] for j in (1, 2)]
        if _dot(_cross(*span), normal) < 0:
            fan = [(a, c, b) for a, b, c in fan]
    return fan


def _solid(faces):
    """The closed solid a brush's polygons enclose, or None when they do not enclose a volume."""
    fan = [point for face in faces for triangle in _fan(face) for point in triangle]
    if len(fan) < 9:
        return None
    corners = np.asarray(fan, dtype=np.float64).reshape(-1, 3)
    unique, inverse = np.unique(np.round(corners, WELD), axis=0, return_inverse=True)
    inverse = inverse.reshape(-1)
    properties = np.concatenate([unique.astype(np.float32), np.zeros((len(unique), 1), np.float32)], axis=1)
    mesh = manifold3d.Mesh(vert_properties=properties, tri_verts=inverse.reshape(-1, 3).astype(np.uint32))
    try:
        solid = manifold3d.Manifold(mesh)
    except (ValueError, RuntimeError):
        return None
    if solid.status() != manifold3d.Error.NoError or solid.volume() <= 0:
        return None
    return solid


def _bounds(faces):
    """The box a brush's polygons occupy, for deciding which booleans are worth running."""
    points = np.asarray([point for face in faces for point in face["Vertex"]], dtype=np.float64)
    return points.min(axis=0), points.max(axis=0)


def _grown_bounds(spans):
    """The box around a set of boxes."""
    lows, highs = zip(*spans, strict=True)
    return np.minimum.reduce(lows), np.maximum.reduce(highs)


def _touching(a, b):
    """Whether two boxes meet: unioning solids that only touch still merges the skin between them."""
    return all(a[0][axis] <= b[1][axis] and b[0][axis] <= a[1][axis] for axis in range(3))


def _overlapping(a, b):
    """Whether two boxes share volume: a cutter that only touches a solid removes nothing."""
    return all(a[0][axis] < b[1][axis] and b[0][axis] < a[1][axis] for axis in range(3))


def _join(parts):
    """One solid for a set of solids, or None when the union cannot be formed."""
    try:
        joined = parts[0] if len(parts) == 1 else manifold3d.Manifold.batch_boolean(parts, manifold3d.OpType.Add)
    except (ValueError, RuntimeError):
        return None
    return joined if joined.status() == manifold3d.Error.NoError else None


def _cut(solid, cutter):
    """A solid with the cutter removed, or None when the boolean cannot be formed."""
    try:
        carved = solid - cutter
    except (ValueError, RuntimeError):
        return None
    return carved if carved.status() == manifold3d.Error.NoError else None


def _add(components, brush, placed, solid, bounds):
    """Join a brush into the components it touches, leaving everything as it was if the union fails."""
    touched = [component for component in components if _touching(component["bounds"], bounds)]
    joined = _join([component["solid"] for component in touched] + [solid])
    if joined is None:
        return False
    for component in touched:
        components.remove(component)
    faces = [face for component in touched for face in component["faces"]]
    faces += [(brush["name"], index, face, True) for index, face in enumerate(placed)]
    span = _grown_bounds([component["bounds"] for component in touched] + [bounds])
    components.append({"solid": joined, "bounds": span, "faces": faces})
    return True


def _subtract(components, brush, placed, cutter, bounds):
    """Carve a brush out of every component it overlaps; False when any carve could not be formed.

    A cutter's own faces are recorded too: the surface it leaves behind is its polygon, so that is
    the face whose texture the exposed surface should carry.
    """
    applied = True
    for component in components:
        if not _overlapping(component["bounds"], bounds):
            continue
        carved = _cut(component["solid"], cutter)
        if carved is None:
            applied = False
            continue
        component["solid"] = carved
        component["faces"] += [(brush["name"], index, face, False) for index, face in enumerate(placed)]
    return applied


def compile_brushes(brushes):
    """Fold additive and subtractive brushes in level order into watertight components."""
    components, uncarved, cutters = [], [], []
    for brush in brushes:
        placed = _placed(brush)
        solid = _solid(placed)
        if solid is None:
            (uncarved if brush["op"] == ADD else cutters).append(brush)
            continue
        bounds = _bounds(placed)
        if brush["op"] == ADD:
            if not _add(components, brush, placed, solid, bounds):
                uncarved.append(brush)
        elif not _subtract(components, brush, placed, solid, bounds):
            cutters.append(brush)
    triangles, estimated = [], 0
    for component in components:
        for name, face, triangle in _surface(component):
            triangles.append((name, face, triangle))
            estimated += face is None
    return Compiled(triangles, uncarved, cutters, estimated)


def _surface(component):
    """The component's skin, every triangle tagged with the brush face that produced it."""
    try:
        mesh = component["solid"].to_mesh()
    except (ValueError, RuntimeError):
        return []
    if not len(mesh.tri_verts):
        return []
    positions = mesh.vert_properties[:, :3].astype(np.float64)
    normals, offsets, additive = _planes(component["faces"])
    triangles = []
    for a, b, c in positions[np.asarray(mesh.tri_verts, dtype=np.int64)]:
        matched = _matching(a, b, c, component["faces"], normals, offsets, additive)
        corners = tuple(tuple(round(n, 4) for n in point) for point in (a, b, c))
        name, face = matched if matched else (component["faces"][0][0], None)
        triangles.append((name, face, corners))
    return triangles


def _planes(faces):
    """Unit normal, plane offset and additive flag for every face that could have produced a triangle."""
    normals, offsets, additive = [], [], []
    for _, _, face, is_additive in faces:
        points = np.asarray(face["Vertex"], dtype=np.float64)
        normal = np.asarray(face["Normal"] or (0.0, 0.0, 0.0), dtype=np.float64)
        if not normal.any() and len(points) > 2:
            normal = np.cross(points[1] - points[0], points[2] - points[0])
        length = float(np.linalg.norm(normal))
        if length == 0:
            normals.append((0.0, 0.0, 0.0))
            offsets.append(math.inf)
        else:
            normals.append(normal / length)
            offsets.append(float((normal / length) @ points[0]))
        additive.append(is_additive)
    return (
        np.asarray(normals, dtype=np.float64),
        np.asarray(offsets, dtype=np.float64),
        np.asarray(additive, dtype=bool),
    )


def _matching(a, b, c, faces, normals, offsets, additive):
    """The source face a triangle lies in, judged by its plane first and the polygon's outline second.

    An additive face wins over a subtractive one on the same plane: a surface that existed before the
    cut keeps its own texture, and only the geometry the cut created takes the cutter's texture.
    """
    corners = np.asarray((a, b, c), dtype=np.float64)
    normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
    length = float(np.linalg.norm(normal))
    if length == 0:
        return None
    normal /= length
    centroid = corners.mean(axis=0)
    parallel = np.abs(normals @ normal) > 1 - ANGLE
    coplanar = np.abs(normals @ centroid - offsets) < PLANE
    candidates = sorted(np.flatnonzero(parallel & coplanar).tolist(), key=lambda index: not additive[index])
    for index in candidates:
        if _inside(centroid, faces[index][2]):
            return faces[index][:2]
    if candidates:
        return faces[candidates[0]][:2]
    scale = max(1.0, float(np.abs(corners).max()))
    scores = np.abs(normals @ normal - 1) + np.abs(normals @ centroid - offsets) / scale + np.where(additive, 0.0, 1.0)
    return faces[int(np.argmin(scores))][:2]


def _inside(point, face):
    """Whether a point in a polygon's plane falls inside that polygon's outline."""
    points = np.asarray(face["Vertex"], dtype=np.float64)
    if len(points) < 3:
        return False
    normal = np.asarray(face["Normal"] or (0.0, 0.0, 0.0), dtype=np.float64)
    axis = int(np.argmax(np.abs(normal))) if normal.any() else 2
    u, v = (n for n in range(3) if n != axis)
    x, y = points[:, u], points[:, v]
    target, height = point[u], point[v]
    if (x.max() - x.min()) * (y.max() - y.min()) == 0:
        return False
    within = x.min() - PLANE <= target <= x.max() + PLANE and y.min() - PLANE <= height <= y.max() + PLANE
    inside = False
    for index in range(len(points)):
        xa, ya = x[index], y[index]
        xb, yb = x[(index + 1) % len(points)], y[(index + 1) % len(points)]
        if (ya > height) != (yb > height) and target < (xb - xa) * (height - ya) / (yb - ya) + xa:
            inside = not inside
    return within and inside
