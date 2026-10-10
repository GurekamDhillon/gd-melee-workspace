"""Blender script: render Goku's select icon, portrait and stock icon from his own converted model (transparent background).

blender -b _build/goku-xv2/author-source/goku.blend --python ports/goku-xv2/tools/presentation_art.py -- _build/goku-xv2/presentation
Writes icon.png (64x56), portrait.png (136x188), stock.png (24x24). build.py turns them into .gxtex (pc/tools/png2gx.py) and declares
fighters[].presentation. Pose: the Kamehameha charge (XV2 xGOK_SPA_KMH, frame 40) for the portrait, Wait for the head crops.
The art is the game's own converted mesh and atlas: nothing disc-derived is committed, outputs stay under _build.
"""
import sys
from pathlib import Path

import bpy
from mathutils import Vector

out = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
for ob in bpy.data.objects:
    if ob.type == 'CAMERA':
        bpy.data.objects.remove(ob, do_unlink=True)


def pose(action, frame):
    act = bpy.data.actions.get(action)
    if act is None:
        raise SystemExit('missing action ' + action)
    arm.animation_data.action = act
    if hasattr(act, 'slots') and len(act.slots):
        arm.animation_data.action_slot = act.slots[0]
    scene.frame_set(int(frame))


def render(name, w, h, centre, scale, loc_dir, action, frame):
    pose(action, frame)
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = scale
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    target = Vector(centre)
    cam.location = target + Vector(loc_dir) * 40
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = w, h, 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.engine = 'BLENDER_EEVEE'
    scene.view_settings.view_transform = 'Standard'
    scene.render.filepath = str(out / (name + '.png'))
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    print('PRESENTATION', name, w, h, action, frame)


# Blender space: Z up, the model faces -Y; the camera sits front-left (x -, y -) looking at the body.
render('portrait', 136, 188, (0, 0, 9.6), 19.0, (-0.45, -1.0, 0.18), 'xGOK_SPA_KMH', 40)
render('icon', 64, 56, (0, 0, 15.6), 11.0, (-0.35, -1.0, 0.08), 'Wait', 0)
render('stock', 24, 24, (0, 0, 17.4), 6.2, (-0.3, -1.0, 0.05), 'Wait', 0)
