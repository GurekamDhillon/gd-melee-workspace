import bpy
import math
from mathutils import Vector

OUT = r"C:\gdm\_build"
GLBS = [
    OUT + r"\gltf\grTFx_0.glb",
    OUT + r"\gltf\grTFx_1.glb",
    OUT + r"\gltf\grTFx_2.glb",
]

bpy.ops.wm.read_factory_settings(use_empty=True)

for g in GLBS:
    bpy.ops.import_scene.gltf(filepath=g)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
tris = 0
for o in meshes:
    tris += len(o.data.polygons)
print("mesh objects:", len(meshes), [o.name for o in meshes])
print("total polys:", tris)

pts = []
for o in meshes:
    mw = o.matrix_world
    for v in o.data.vertices:
        pts.append(mw @ v.co)

xs = [p.x for p in pts]
ys = [p.y for p in pts]
zs = [p.z for p in pts]
minx, maxx = min(xs), max(xs)
miny, maxy = min(ys), max(ys)
minz, maxz = min(zs), max(zs)
cx, cy, cz = (minx + maxx) / 2, (miny + maxy) / 2, (minz + maxz) / 2
w, h, d = maxx - minx, maxy - miny, maxz - minz
center = Vector((cx, cy, cz))
print(f"bbox x[{minx:.1f},{maxx:.1f}] y[{miny:.1f},{maxy:.1f}] z[{minz:.1f},{maxz:.1f}]")
print(f"size {w:.1f} x {h:.1f} x {d:.1f}  verts={len(pts)}")

scene = bpy.context.scene
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.lens = 50.0

sun_data = bpy.data.lights.new("sun", type="SUN")
sun_data.energy = 4.0
sun = bpy.data.objects.new("sun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-40))

world = bpy.data.worlds.new("world")
scene.world = world
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.10, 0.11, 0.13, 1.0)
    bg.inputs[1].default_value = 1.3

scene.render.resolution_x = 1200
scene.render.resolution_y = 850
scene.render.image_settings.file_format = "PNG"
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    scene.render.engine = "BLENDER_EEVEE"

longest = max(w, h, d)
dist = longest * 1.35
cam_data.clip_end = dist * 8.0
cam_data.clip_start = 0.5

views = {
    "iso": Vector((-0.8, -1.0, 0.5)).normalized(),
    "top": Vector((0.0, 0.0, 1.0)),
    "front": Vector((0.0, -1.0, 0.0)),
    "side": Vector((1.0, 0.0, 0.0)),
}

for name, vdir in views.items():
    eye = center + vdir * dist
    cam.location = eye
    cam.rotation_euler = (center - eye).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = OUT + "\\foxstage_" + name + ".png"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name)

print("DONE")
