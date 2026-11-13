"""Create the five stock-named clips (Idle, Run, Jump, Falling, Grind) on SqueakerRig.

Run inside Blender after squeaker_model.py: exec(open(path).read()).
"""

import bpy
import math

FPS = 60
CLIPS = ("Idle", "Run", "Jump", "Falling", "Grind")
rig = bpy.data.objects["SqueakerRig"]
rig.rotation_mode = "XYZ"
for pb in rig.pose.bones:
    pb.rotation_mode = "XYZ"
for old in [a for a in bpy.data.actions if a.name in CLIPS]:
    bpy.data.actions.remove(old)

R = (0, 0, 0)


def clip(name, seconds, keys):
    """keys: {bone: [(t in 0..1, (rx, ry, rz) degrees, optional (x, y, z) location)]}; first and last rows match so it loops."""
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = action
    frames = round(seconds * FPS)
    for bone, rows in keys.items():
        pb = rig.pose.bones[bone]
        for row in rows:
            frame = 1 + round(row[0] * frames)
            pb.rotation_euler = [math.radians(a) for a in row[1]]
            pb.keyframe_insert("rotation_euler", frame=frame)
            if len(row) > 2:
                pb.location = row[2]
                pb.keyframe_insert("location", frame=frame)
        pb.rotation_euler = R
        pb.location = R
    action.frame_range = (1, 1 + frames)


def cycle(values, times=None):
    times = times or [i / (len(values) - 1) for i in range(len(values))]
    return [(t, v) for t, v in zip(times, values)]


def bob(*heights):
    """Root location rows; the root bone points up, so local Y is vertical."""
    n = len(heights) - 1
    return [(i / n, R, (0, h, 0)) for i, h in enumerate(heights)]


def swing(angle, offset=0.0, rows=5):
    """Leg swing about X as a sine, shifted by offset (0..1) of a cycle; rows keys including the closing one."""
    return cycle([(angle * math.sin(2 * math.pi * (i / (rows - 1) + offset)), 0, 0) for i in range(rows)])


clip(
    "Idle",
    2.0,
    {
        "torso": cycle([(0, 0, 0), (2, 0, 0), (0, 0, 0)]),
        "head": cycle([(0, 0, 0), (-3, 0, 4), (0, 0, 0)]),
        "ear.L": cycle([R, R, (0, 0, 10), R], [0, 0.6, 0.7, 1]),
        "ear.R": cycle([R, R, R], [0, 0.5, 1]),
        "tail.1": cycle([(0, 0, -6), (0, 0, 6), (0, 0, -6)]),
        "tail.2": cycle([(0, 0, 8), (0, 0, -8), (0, 0, 8)]),
        "tail.3": cycle([(0, 0, -10), (0, 0, 10), (0, 0, -10)]),
    },
)
clip(
    "Run",
    0.6,
    {
        "root": bob(0, 0.12, 0, 0.12, 0),
        "torso": cycle([(-6, 0, 0), (6, 0, 0), (-6, 0, 0)]),
        "head": cycle([(4, 0, 0), (-4, 0, 0), (4, 0, 0)]),
        "leg.FL": swing(35, 0),
        "leg.BR": swing(35, 0),
        "leg.FR": swing(35, 0.5),
        "leg.BL": swing(35, 0.5),
        "tail.1": cycle([(0, 0, 12), (0, 0, -12), (0, 0, 12)]),
        "tail.2": cycle([(0, 0, -15), (0, 0, 15), (0, 0, -15)]),
        "ear.L": cycle([(-12, 0, 0), (-20, 0, 0), (-12, 0, 0)]),
        "ear.R": cycle([(-12, 0, 0), (-20, 0, 0), (-12, 0, 0)]),
    },
)
clip(
    "Jump",
    0.5,
    {
        "root": bob(-0.25, 0.1, 0.05),
        "torso": cycle([(10, 0, 0), (-12, 0, 0), (-5, 0, 0)]),
        "head": cycle([(8, 0, 0), (-10, 0, 0), (-4, 0, 0)]),
        "leg.FL": cycle([(-10, 0, 0), (30, 0, 0), (20, 0, 0)]),
        "leg.FR": cycle([(-10, 0, 0), (30, 0, 0), (20, 0, 0)]),
        "leg.BL": cycle([(15, 0, 0), (-35, 0, 0), (-20, 0, 0)]),
        "leg.BR": cycle([(15, 0, 0), (-35, 0, 0), (-20, 0, 0)]),
        "tail.1": cycle([(15, 0, 0), (-20, 0, 0), (-8, 0, 0)]),
        "ear.L": cycle([(-10, 0, 0), (25, 0, 0), (15, 0, 0)]),
        "ear.R": cycle([(-10, 0, 0), (25, 0, 0), (15, 0, 0)]),
    },
)
clip(
    "Falling",
    0.8,
    {
        "torso": cycle([(-6, 0, 3), (-6, 0, -3), (-6, 0, 3)]),
        "head": cycle([(-8, 0, 0)] * 2),
        "leg.FL": cycle([(40, 0, -15), (30, 0, -20), (40, 0, -15)]),
        "leg.FR": cycle([(30, 0, 20), (40, 0, 15), (30, 0, 20)]),
        "leg.BL": cycle([(-30, 0, -15), (-40, 0, -10), (-30, 0, -15)]),
        "leg.BR": cycle([(-40, 0, 10), (-30, 0, 15), (-40, 0, 10)]),
        "tail.1": cycle([(-25, 0, 0), (-35, 0, 0), (-25, 0, 0)]),
        "tail.2": cycle([(-15, 0, 5), (-15, 0, -5), (-15, 0, 5)]),
        "ear.L": cycle([(35, 0, 0), (45, 0, 0), (35, 0, 0)]),
        "ear.R": cycle([(45, 0, 0), (35, 0, 0), (45, 0, 0)]),
    },
)
clip(
    "Grind",
    0.6,
    {
        "root": bob(-0.3, -0.32, -0.3),
        "torso": cycle([(6, 0, 0), (8, 0, 0), (6, 0, 0)]),
        "head": cycle([(-8, 0, 0)] * 2),
        "leg.FL": cycle([(0, 0, -45), (0, 0, -50), (0, 0, -45)]),
        "leg.FR": cycle([(0, 0, 45), (0, 0, 50), (0, 0, 45)]),
        "leg.BL": cycle([(0, 0, -45), (0, 0, -50), (0, 0, -45)]),
        "leg.BR": cycle([(0, 0, 45), (0, 0, 50), (0, 0, 45)]),
        "tail.1": cycle([(-10, 0, 14), (-10, 0, -14), (-10, 0, 14)]),
        "tail.2": cycle([(0, 0, -16), (0, 0, 16), (0, 0, -16)]),
    },
)
rig.animation_data.action = bpy.data.actions["Idle"]
bpy.context.scene.render.fps = FPS
print({a.name: tuple(a.frame_range) for a in bpy.data.actions if a.use_fake_user})
