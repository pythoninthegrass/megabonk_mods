"""Render the 32x32 character-select icon and export Squeaker.fbx and StaleCookie.fbx.

Run inside Blender after the model, animation and cookie scripts: exec(open(path).read()).
Set REPO to the checkout root first.
"""

import bpy
import os
from mathutils import Vector

REPO = globals().get("REPO") or os.path.expanduser("~/git/megabonk_mods")
OUT = os.path.join(REPO, "unity/pack-authoring/Assets/Squeaker")
ICON_SIZE = 32
ICON_SAMPLES = 64
HEAD_MIN_Z, HEAD_MAX_Y = 0.9, -0.1
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene


def select_only(*objs):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def head_bounds(body):
    """Bounds of the head and ears in the rest pose, found by position on the mesh."""
    points = [v.co for v in body.data.vertices if v.co.z > HEAD_MIN_Z and v.co.y < HEAD_MAX_Y]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return low, high


def render_icon(body):
    low, high = head_bounds(body)
    center = (low + high) / 2
    cam_data = bpy.data.cameras.new("SqueakerIconCam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(high.x - low.x, high.z - low.z) * 1.08
    cam = bpy.data.objects.new("SqueakerIconCam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (center.x, -8.0, center.z)
    cam.rotation_euler = (1.5707963, 0, 0)
    render = scene.render
    saved = (
        scene.camera,
        render.resolution_x,
        render.resolution_y,
        render.resolution_percentage,
        render.film_transparent,
        render.filepath,
        scene.cycles.samples,
    )
    scene.camera = cam
    render.resolution_x = render.resolution_y = ICON_SIZE
    render.resolution_percentage = 100
    render.film_transparent = True
    render.filepath = os.path.join(OUT, "squeaker_icon.png")
    scene.cycles.samples = ICON_SAMPLES
    hidden = [bpy.data.objects["Backdrop"], bpy.data.objects["StaleCookie"]]
    for ob in hidden:
        ob.hide_render = True
    bpy.ops.render.render(write_still=True)
    for ob in hidden:
        ob.hide_render = False
    (
        scene.camera,
        render.resolution_x,
        render.resolution_y,
        render.resolution_percentage,
        render.film_transparent,
        render.filepath,
        scene.cycles.samples,
    ) = saved
    bpy.data.objects.remove(cam)


def export_fbx(path, objs, animations):
    select_only(*objs)
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z",
        axis_up="Y",
        add_leaf_bones=False,
        bake_anim=animations,
        bake_anim_use_all_actions=animations,
        bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,
        bake_anim_simplify_factor=0.0,
        path_mode="COPY",
    )


rig = bpy.data.objects["SqueakerRig"]
body = bpy.data.objects["Squeaker"]
cookie = bpy.data.objects["StaleCookie"]

rig.animation_data.action = bpy.data.actions["Idle"]
scene.frame_set(1)
render_icon(body)
export_fbx(os.path.join(OUT, "Squeaker.fbx"), [rig, body], animations=True)
home = cookie.location.copy()
cookie.location = Vector((0, 0, 0))
export_fbx(os.path.join(OUT, "StaleCookie.fbx"), [cookie], animations=False)
cookie.location = home
print(sorted(os.listdir(OUT)))
