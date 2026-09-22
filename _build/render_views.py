import bpy
import math
import sys
from mathutils import Vector

_argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OBJ = _argv[0] if len(_argv) > 0 else r"C:\gdm\_build\grTFx.obj"
PREFIX = _argv[1] if len(_argv) > 1 else "grTFx"
OUT = r"C:\gdm\_build"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=OBJ)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
ctx = bpy.context
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
ctx.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
obj = ctx.active_object

co = [v.co for v in obj.data.vertices]


def pcts(axis, lo=0.005, hi=0.995):
    vals = sorted(c[axis] for c in co)
    n = len(vals)
    return vals[int(n * lo)], vals[min(n - 1, int(n * hi))]


bx, by, bz = pcts(0), pcts(1), pcts(2)
print("robust bbox x", [round(v, 1) for v in bx])
print("robust bbox y", [round(v, 1) for v in by])
print("robust bbox z", [round(v, 1) for v in bz])

cx = (bx[0] + bx[1]) / 2.0
cy = (by[0] + by[1]) / 2.0
cz = (bz[0] + bz[1]) / 2.0
w = bx[1] - bx[0]
h = by[1] - by[0]
d = bz[1] - bz[0]
center = Vector((cx, cy, cz))
print(f"size w={w:.1f} h={h:.1f} d={d:.1f}")

mat = bpy.data.materials.new("stage")
mat.use_backface_culling = False
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.75, 0.72, 0.66, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.6
obj.data.materials.append(mat)
for p in obj.data.polygons:
    p.use_smooth = False

scene = ctx.scene
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.lens = 50.0

sun_data = bpy.data.lights.new("sun", type="SUN")
sun_data.energy = 4.0
sun = bpy.data.objects.new("sun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(55), math.radians(10), math.radians(-35))

world = bpy.data.worlds.new("world")
scene.world = world
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.10, 0.11, 0.13, 1.0)
    bg.inputs[1].default_value = 1.0

scene.render.resolution_x = 1100
scene.render.resolution_y = 800
scene.render.image_settings.file_format = "PNG"
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    scene.render.engine = "BLENDER_EEVEE"

# distance so the WIDEST extent fits with margin (fit longest axis)
longest = max(w, h, d)
dist = longest * 1.45
cam_data.clip_end = dist * 6.0
cam_data.clip_start = 1.0

views = {
    "top": Vector((0.0, 0.0, 1.0)),
    "front": Vector((0.0, -1.0, 0.0)),
    "side": Vector((1.0, 0.0, 0.0)),
    "iso": Vector((-0.75, -1.0, 0.55)).normalized(),
}

for name, vdir in views.items():
    eye = center + vdir * dist
    cam.location = eye
    cam.rotation_euler = (center - eye).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = OUT + "\\" + PREFIX + "_" + name + ".png"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name)

print(f"DONE verts={len(obj.data.vertices)} tris={len(obj.data.polygons)}")
