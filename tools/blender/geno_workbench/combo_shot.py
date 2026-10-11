"""Render one frame of a played combo string (a screenshot for review; the .blend is never saved).

    blender -b <fighter.blend> --python tools/blender/geno_workbench/combo_shot.py -- <string_plan.json> <out.png> [frame] [armature]

<string_plan.json> is the Workbench server's ``string_plan`` reply (the Qt test with WB_COMBO_PROJECT writes them).
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from geno_workbench import combo_play as C, combo_play_bpy as CB  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
reply = json.loads(Path(args[0]).read_text(encoding="utf-8"))
out = args[1]
frame = int(args[2]) if len(args) > 2 else 1
scene = bpy.context.scene
arm = bpy.data.objects[args[3]] if len(args) > 3 else CB.find_armature(scene)
summary = CB.build(scene, reply, add_buffer=False, hitboxes=True, arm=arm)
print("PLAN", [(s["move"], s["cut"]) for s in summary["plan"]], "frames", summary["frames"], "strips", len(summary["strips"]),
      "missing", summary["missing_clips"], "spheres", len(summary["hit_spheres"]), "missing bones", summary["missing_bones"])
scene.frame_set(frame)
shown = C.locate(summary["plan"], frame)
print("FRAME", frame, "-> segment/move frame", shown)
cam_data = bpy.data.cameras.new("ComboCam")
cam_data.type = "ORTHO"
k = CB.scale_of(arm)
total_w = summary["frames"] * CB.FRAME_W * k
cam_data.ortho_scale = max(total_w * 1.1, 3.0 * k)
cam = bpy.data.objects.new("ComboCam", cam_data)
scene.collection.objects.link(cam)
height = CB.height_of(arm)
cam.location = (arm.location.x, arm.location.y - 10.0 * k, arm.location.z + height * 0.95)
cam_data.clip_end = 1000 * k
cam.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam
world = scene.world or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.04, 0.045, 0.06, 1)
for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"):
    try:
        scene.render.engine = engine
        break
    except TypeError:
        continue
scene.view_settings.view_transform = "Standard"
scene.render.resolution_x, scene.render.resolution_y = 1800, 800
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("SHOT", out, scene.render.engine)
