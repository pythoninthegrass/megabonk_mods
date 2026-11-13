"""Build the StaleCookie projectile mesh as its own object in the Squeaker collection.

Run inside Blender: exec(open(path).read()). Origin is the cookie centre; the face points along +Z.
"""

import bmesh
import bpy
import math
import random
from mathutils import Matrix

DOUGH, CHIP = "Stale Cookie Dough", "Stale Cookie Chip"
COLORS = {DOUGH: (0.72, 0.52, 0.26, 1), CHIP: (0.20, 0.10, 0.06, 1)}
RADIUS, THICKNESS = 0.16, 0.05
SCALE = 2.2  # the mouse is about 2.4 units tall, so the cookie is scaled up to read as a thrown snack

random.seed(7)
for ob in [o for o in bpy.data.objects if o.name == "StaleCookie"]:
    bpy.data.objects.remove(ob, do_unlink=True)


def material(name):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    node = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    node.inputs["Base Color"].default_value = COLORS[name]
    node.inputs["Roughness"].default_value = 1.0
    mat.diffuse_color = COLORS[name]
    return mat


bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=RADIUS, radius2=RADIUS, depth=THICKNESS)
bm.verts.ensure_lookup_table()
for v in bm.verts:
    v.co.x *= 1 + random.uniform(-0.06, 0.06)
    v.co.y *= 1 + random.uniform(-0.06, 0.06)
bite_center, bite_radius = RADIUS * 0.95, RADIUS * 0.45
for v in bm.verts:
    d = math.hypot(v.co.x - bite_center, v.co.y)
    if d < bite_radius:
        v.co.x -= (1 - d / bite_radius) * RADIUS * 0.3
for chip in ((-0.05, 0.05), (0.03, -0.07), (-0.07, -0.04), (0.02, 0.07)):
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=5,
        radius1=0.026,
        radius2=0.018,
        depth=0.012,
        matrix=Matrix.Translation((chip[0], chip[1], THICKNESS / 2)),
    )
for f in bm.faces:
    f.smooth = False
    center = f.calc_center_median()
    f.material_index = (
        1
        if center.z > THICKNESS / 2 - 0.001 and center.length < RADIUS * 0.9 and abs(f.normal.z) > 0.5 and f.calc_area() < 0.002
        else 0
    )
mesh = bpy.data.meshes.new("StaleCookie")
bm.to_mesh(mesh)
bm.free()
mesh.transform(Matrix.Scale(SCALE, 4))
for name in (DOUGH, CHIP):
    mesh.materials.append(material(name))
cookie = bpy.data.objects.new("StaleCookie", mesh)
bpy.data.collections["Squeaker"].objects.link(cookie)
cookie.location = (2.2, -1.0, 0.2)
print("cookie faces", len(mesh.polygons), "size", tuple(round(d, 3) for d in cookie.dimensions))
