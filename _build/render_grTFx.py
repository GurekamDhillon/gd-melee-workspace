import bpy
import math
from mathutils import Vector

OBJ = r"C:\gdm\_build\grTFx.obj"
PNG = r"C:\gdm\_build\grTFx_blender.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=OBJ)
obj = [o for o in bpy.data.objects if o.type == "MESH"][0]
ctx = bpy.context
ctx.view_layer.objects.active = obj

wv = [obj.matrix_world @ v.co for v in obj.data.vertices]
minx = min(v.x for v in wv); maxx = max(v.x for v in wv)
miny = min(v.y for v in wv); maxy = max(v.y for v in wv)
minz = min(v.z for v in wv); maxz = max(v.z for v in wv)
cx = (minx + maxx) / 2.0
cz = (minz + maxz) / 2.0
w = maxx - minx
h = maxz - minz
print(f"world bbox x[{minx:.0f},{maxx:.0f}] y[{miny:.0f},{maxy:.0f}] z[{minz:.0f},{maxz:.0f}]")

mat = bpy.data.materials.new("stage")
mat.use_backface_culling = False
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.72, 0.72, 0.76, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.55
obj.data.materials.append(mat)
for p in obj.data.polygons:
    p.use_smooth = True

scene = ctx.scene
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.type = "ORTHO"
aspect = 1280.0 / 720.0
cam_data.ortho_scale = max(w, h * aspect) * 1.06
cam_data.clip_start = 1.0
cam_data.clip_end = 100000.0
cam.location = (cx, miny - 400.0, cz)
cam.rotation_euler = Vector((0.0, 1.0, 0.0)).to_track_quat("-Z", "Y").to_euler()

sun_data = bpy.data.lights.new("sun", type="SUN")
sun_data.energy = 3.0
sun = bpy.data.objects.new("sun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(55), math.radians(15), math.radians(-25))

world = bpy.data.worlds.new("world")
scene.world = world
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.15, 0.15, 0.17, 1.0)

scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = PNG
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    scene.render.engine = "BLENDER_EEVEE"

bpy.ops.render.render(write_still=True)
print(f"RENDERED {PNG} ortho_scale={cam_data.ortho_scale:.0f}")
