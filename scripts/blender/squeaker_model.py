"""Build the Squeaker mesh and armature from tools/simple_mouse.blend in the open Blender scene.

Run inside Blender: exec(open(path).read()). Appends the original mouse parts, joins them into one
skinned mesh named "Squeaker" and builds the quadruped rig "SqueakerRig". Rebuilds the collection each run.
"""

import bpy
import os
import shutil
import tempfile
from mathutils import Matrix, Vector

REPO = globals().get("REPO") or os.path.expanduser("~/git/megabonk_mods")
SOURCE = os.path.join(REPO, "tools/simple_mouse.blend")
COLLECTION = "Squeaker"
SCENE_ONLY = {"Backdrop", "Mouse Portrait Camera", "Key Softbox", "Fill Softbox", "Rim Softbox"}
WHISKERS = [f"{side} Whisker {i}" for side in ("Left", "Right") for i in (1, 2, 3)]
SLOT_ORDER = ["Mouse - warm gray", "Mouse - pink", "Mouse - shiny eyes", "Mouse - eye sparkle", "Mouse - whiskers"]

# bone name -> (parent, head, tail); the mouse faces -Y, Z up, as in the source
BONES = {
    "root": (None, (0, 0, 0), (0, 0, 0.3)),
    "hips": ("root", (0, 1.0, 0.8), (0, 0.35, 0.8)),
    "torso": ("hips", (0, 0.35, 0.8), (0, -0.4, 0.9)),
    "head": ("torso", (0, -0.3, 1.0), (0, -1.2, 1.15)),
    "ear.L": ("head", (-0.52, -0.64, 1.5), (-0.52, -0.64, 2.4)),
    "ear.R": ("head", (0.52, -0.64, 1.5), (0.52, -0.64, 2.4)),
    "leg.FL": ("torso", (-0.44, -0.62, 0.5), (-0.44, -0.62, 0.18)),
    "leg.FR": ("torso", (0.44, -0.62, 0.5), (0.44, -0.62, 0.18)),
    "leg.BL": ("hips", (-0.55, 0.81, 0.5), (-0.55, 0.81, 0.18)),
    "leg.BR": ("hips", (0.55, 0.81, 0.5), (0.55, 0.81, 0.18)),
    "tail.1": ("hips", (0.0, 1.19, 0.51), (0.75, 2.02, 0.15)),
    "tail.2": ("tail.1", (0.75, 2.02, 0.15), (1.54, 1.29, 0.14)),
    "tail.3": ("tail.2", (1.54, 1.29, 0.14), (1.26, 1.13, 0.15)),
}
TAIL_POINTS = [
    (0.0, 1.19, 0.51),
    (0.14, 1.67, 0.25),
    (0.75, 2.02, 0.15),
    (1.42, 1.8, 0.14),
    (1.54, 1.29, 0.14),
    (1.26, 1.13, 0.15),
]
TAIL_BONE_FOR_POINT = ["tail.1", "tail.1", "tail.2", "tail.2", "tail.3", "tail.3"]
BODY_BLEND_CENTER_Y, BODY_BLEND_WIDTH = 0.3, 1.0

PART_BONE = {
    "Mouse Head": "head",
    "Mouse Snout": "head",
    "Mouse Nose": "head",
    "Left Ear": "ear.L",
    "Left Inner Ear": "ear.L",
    "Right Ear": "ear.R",
    "Right Inner Ear": "ear.R",
    "Left Eye": "head",
    "Left Eye Sparkle": "head",
    "Right Eye": "head",
    "Right Eye Sparkle": "head",
    "Left Front Paw": "leg.FL",
    "Right Front Paw": "leg.FR",
    "Left Back Paw": "leg.BL",
    "Right Back Paw": "leg.BR",
}


PART_NAMES = set(PART_BONE) | set(WHISKERS) | {"Mouse Body", "Mouse Curly Tail"}


def clear_previous():
    for name in (COLLECTION, "Codex Mouse"):
        col = bpy.data.collections.get(name)
        if col:
            for ob in list(col.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.collections.remove(col)
    for ob in [o for o in bpy.data.objects if o.name.startswith(("Squeaker", "Mouse", "Left ", "Right "))]:
        if ob.name not in SCENE_ONLY:
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.orphans_purge(do_recursive=True)


def append_parts(col):
    # Blender cannot append from the file it has open, so read a copy
    with tempfile.TemporaryDirectory() as tmp:
        copy = shutil.copy(SOURCE, os.path.join(tmp, "source.blend"))
        with bpy.data.libraries.load(copy, link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n in PART_NAMES]
    parts = []
    for ob in dst.objects:
        col.objects.link(ob)
        parts.append(ob)
    bpy.context.view_layer.update()
    return parts


def bake_to_mesh_object(ob, col):
    """Return a mesh object holding the part's world-space evaluated geometry with smooth shading."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(depsgraph))
    mesh.transform(ob.matrix_world)
    mesh.shade_smooth()
    slot = SLOT_ORDER.index(mesh.materials[0].name)
    mesh.materials.clear()
    for material_name in SLOT_ORDER:
        mesh.materials.append(bpy.data.materials[material_name])
    mesh.polygons.foreach_set("material_index", [slot] * len(mesh.polygons))
    name = ob.name
    bpy.data.objects.remove(ob, do_unlink=True)
    new = bpy.data.objects.new(name, mesh)
    col.objects.link(new)
    return new


def assign_weights(ob):
    groups = {name: ob.vertex_groups.new(name=name) for name in BONES}
    verts = ob.data.vertices
    if ob.name == "Mouse Body":
        for v in verts:
            torso = min(max(0.5 + (BODY_BLEND_CENTER_Y - v.co.y) / BODY_BLEND_WIDTH, 0.0), 1.0)
            groups["torso"].add([v.index], torso, "REPLACE")
            groups["hips"].add([v.index], 1.0 - torso, "REPLACE")
    elif ob.name == "Mouse Curly Tail":
        for v in verts:
            nearest = min(range(len(TAIL_POINTS)), key=lambda i: (v.co - Vector(TAIL_POINTS[i])).length)
            groups[TAIL_BONE_FOR_POINT[nearest]].add([v.index], 1.0, "REPLACE")
    elif "Whisker" in ob.name:
        groups["head"].add([v.index for v in verts], 1.0, "REPLACE")
    else:
        groups[PART_BONE[ob.name]].add([v.index for v in verts], 1.0, "REPLACE")


def join(objs):
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs):
        bpy.ops.object.join()
    body = objs[0]
    body.name = body.data.name = "Squeaker"
    return body


def build_rig(col, body):
    data = bpy.data.armatures.new("SqueakerRig")
    rig = bpy.data.objects.new("SqueakerRig", data)
    col.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (_, head, tail) in BONES.items():
        bone = data.edit_bones.new(name)
        bone.head, bone.tail = head, tail
    for name, (parent, _, _) in BONES.items():
        if parent:
            data.edit_bones[name].parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    body.parent = rig
    body.matrix_parent_inverse = Matrix.Identity(4)
    modifier = body.modifiers.new("Armature", "ARMATURE")
    modifier.object = rig
    return rig


clear_previous()
collection = bpy.data.collections.new(COLLECTION)
bpy.context.scene.collection.children.link(collection)
sources = append_parts(collection)
meshes = [bake_to_mesh_object(ob, collection) for ob in sources]
for part in meshes:
    assign_weights(part)
squeaker = join(meshes)
rig = build_rig(collection, squeaker)
print("faces", len(squeaker.data.polygons), "verts", len(squeaker.data.vertices), "bones", len(rig.data.bones))
