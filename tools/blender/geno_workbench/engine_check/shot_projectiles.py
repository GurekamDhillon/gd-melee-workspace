"""Render Goku with a projectile and its ghost path (background Blender, Workbench engine).

    blender -b GOKU.blend --python shot_projectiles.py -- --geno GENO_JSON --out shot.png [--frame 10]
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from geno_workbench import projectiles as P, projectiles_bpy as PB  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--geno", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--frame", type=int, default=10)
args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])

doc = json.loads(Path(args.geno).read_text(encoding="utf-8"))
arts = [dict(a, index=i) for i, a in enumerate(P.articles_of(doc))]
scene = bpy.context.scene
PB.import_articles(arts, scene)
ki = next(a for a in arts if a["name"] == "KiBlast")
spawns = [{"row": "ki_volley", "ordinal": 0, "frame": 6, "article": ki["index"], "variant": 0, "angle": 0},
          {"row": "ki_volley", "ordinal": 1, "frame": 14, "article": ki["index"], "variant": 0, "angle": 18}]
# a faster, falling shot as the artist's edit, to make the path readable
root = bpy.data.objects["Proj.KiBlast"]
root["gp_gravity"] = 0.06
root["gp_velocity_0"] = 3.0
edited = PB.export_article(root)
arts_edit = [dict(edited, index=ki["index"]) if a["index"] == ki["index"] else a for a in arts]
info = PB.update_ghost(arts_edit, spawns, "ki_volley", args.frame, scene, base=(0.0, 0.0))
print("GHOST", info)
for o in scene.objects:
    if o.name.startswith("Proj.") and not o.name.startswith("Proj.KiBlast"):
        o.hide_render = True          # one projectile in the picture
    if o.name.startswith("Proj.KiBlast.hb"):
        o.display_type = "WIRE"
    if o.name.startswith("Ghost."):
        o.hide_render = False
    if o.name.startswith("Ghost.path"):
        # edge-only meshes do not render: draw the same points as a bevelled curve (viewport shows the edges itself)
        pts = [v.co.copy() for v in o.data.vertices]
        cu = bpy.data.curves.new("ghostcurve", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = 0.22
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for pnt, co in zip(sp.points, pts):
            pnt.co = (co.x, co.y, co.z, 1.0)
        tube = bpy.data.objects.new("GhostTube", cu)
        scene.collection.objects.link(tube)
        tube.color = (1.0, 0.85, 0.2, 1.0)
        o.hide_render = True
    if o.name.startswith("Ghost.hb") or o.name.startswith("Ghost.root"):
        mod = o.modifiers.new("lines", "WIREFRAME")
        mod.thickness = 0.12
# camera: side view along +Y (Melee x -> Blender x), centred on the fighter and the shots
cam = bpy.data.objects.new("ShotCam", bpy.data.cameras.new("ShotCam"))
scene.collection.objects.link(cam)
cam.data.type = "ORTHO"
cam.data.ortho_scale = 62
cam.location = (22, -120, 8)
cam.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "OBJECT"
for o in scene.objects:
    if o.name.startswith("Ghost.path"):
        o.color = (1.0, 0.85, 0.2, 1.0)
    if o.name.startswith("Ghost.hb"):
        o.color = (1.0, 0.3, 0.3, 1.0)
    if o.name.startswith("Ghost.root"):
        o.color = (1.0, 1.0, 1.0, 1.0)
scene.display.shading.show_object_outline = True
scene.render.resolution_x, scene.render.resolution_y = 1600, 800
scene.render.filepath = args.out
scene.world = scene.world or bpy.data.worlds.new("W")
scene.world.color = (0.08, 0.09, 0.12)
bpy.ops.render.render(write_still=True)
print("SHOT", args.out)
