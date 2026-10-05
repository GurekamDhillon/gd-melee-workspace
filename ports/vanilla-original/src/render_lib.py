"""Headless Workbench rendering helpers (Blender Python). Import from other Blender scripts."""
import bpy, math, os
from mathutils import Vector

BG = (0.80, 0.82, 0.85)

def setup(res=(512, 512), bg=BG, flat=False, silhouette=False):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.view_settings.view_transform = "Standard"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("W")
    sc.world.color = bg
    sh = sc.display.shading
    sc.display.render_aa = "8"
    sh.show_cavity = False
    sh.show_shadows = False
    sh.show_object_outline = not silhouette
    sh.object_outline_color = (0.05, 0.05, 0.08)
    if silhouette:
        sh.light = "FLAT"; sh.color_type = "SINGLE"; sh.single_color = (0, 0, 0)
    else:
        sh.light = "FLAT" if flat else "STUDIO"
        sh.studio_light = "studio.sl" if "studio.sl" in [l.name for l in bpy.context.preferences.studio_lights] else sh.studio_light
        sh.color_type = "TEXTURE"
    sh.background_type = "WORLD"
    return sc

def get_cam(ortho=True):
    sc = bpy.context.scene
    cam = sc.camera
    if cam is None:
        cd = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cd)
        sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO" if ortho else "PERSP"
    return cam

def look(cam, loc, target):
    cam.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

VIEWS = {   # direction FROM the target TO the camera (authoring space: character faces -Y, left is +X)
    "front": (0, -1, 0), "back": (0, 1, 0), "left": (1, 0, 0), "right": (-1, 0, 0),
    "three_quarter": (0.62, -0.78, 0.18), "three_quarter_back": (-0.62, 0.78, 0.18), "top": (0, -0.01, 1),
}

def render_view(path, view="front", target=(0, 0, 5.6), scale=13.0, cam_dist=40, res=None, dirv=None):
    sc = bpy.context.scene
    cam = get_cam(True)
    d = Vector(dirv if dirv else VIEWS[view]).normalized()
    look(cam, Vector(target) + d * cam_dist, target)
    cam.data.ortho_scale = scale
    cam.data.clip_start = 0.1; cam.data.clip_end = 200
    if res: sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

def set_costume(ob, name):
    for i, m in enumerate(bpy.data.materials):
        if m.name == f"mat_{name}":
            ob.data.materials[0] = m
            return
    raise KeyError(name)

def courier():
    return bpy.data.objects["Courier"], bpy.data.objects["Courier_Armature"]
