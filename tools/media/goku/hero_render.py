"""Hero render of Goku from the author blend (Blender Workbench, studio light, transparent background).

    blender -b _build/goku-xv2/author-source/goku.blend --python tools/media/goku/hero_render.py -- OUT.png
        [--action KameCharge] [--frame 40] [--azimuth 35] [--elev 8] [--size 1400x1750] [--fov 28] [--side 1]

Run with the Blender install (Steam: D:/SteamLibrary/steamapps/common/Blender/blender.exe). The blend is only read. The result is a
transparent PNG: atlas_overlay.py puts it on the title card (the ember glow behind him is CSS). Workbench, not Eevee, so it
matches the project's Workbench viewer; flat texture colour, studio lighting, a thin object outline and cavity for form.
"""
import math, sys
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
out = argv[0]
opt = {'--action': 'KameCharge', '--frame': '40', '--azimuth': '35', '--elev': '8', '--size': '1400x1750', '--fov': '28', '--side': '1'}
for i in range(1, len(argv) - 1, 2):
    opt[argv[i]] = argv[i + 1]
W, H = map(int, opt['--size'].split('x'))

arm = bpy.data.objects['GokuExport']
mesh = bpy.data.objects['Goku']
act = bpy.data.actions[opt['--action']]
arm.animation_data_create().action = act
sc = bpy.context.scene
sc.frame_set(int(opt['--frame']))
bpy.context.view_layer.update()

# bounds of the posed mesh in world space
dg = bpy.context.evaluated_depsgraph_get()
ev = mesh.evaluated_get(dg)
me = ev.to_mesh()
pts = [ev.matrix_world @ v.co for v in me.vertices]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
ev.to_mesh_clear()
mid = (lo + hi) / 2
height = hi.z - lo.z                                     # the blend is Z-up

for o in bpy.data.objects:
    if o.type == 'CAMERA':
        o.hide_render = True
cam_data = bpy.data.cameras.new('HeroCam')
cam_data.angle = math.radians(float(opt['--fov']))
cam = bpy.data.objects.new('HeroCam', cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
dist = height * 0.5 / math.tan(cam_data.angle / 2) * 1.35 + max(hi.x - lo.x, hi.y - lo.y) * 0.5
az, el = math.radians(float(opt['--azimuth'])), math.radians(float(opt['--elev']))
side = float(opt['--side'])
cam.location = mid + Vector((math.sin(az) * math.cos(el) * dist, -side * math.cos(az) * math.cos(el) * dist, math.sin(el) * dist))
look = (mid - cam.location).normalized()
cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()

sc.render.engine = 'BLENDER_WORKBENCH'
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.render.film_transparent = True
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'
sc.display.render_aa = '32'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'TEXTURE'
sh.show_cavity = True
sh.cavity_type = 'BOTH'
sh.show_object_outline = True
sh.object_outline_color = (0.043, 0.051, 0.071)
sh.show_specular_highlight = True
sc.display.matcap_ssao_samples = 32 if hasattr(sc.display, 'matcap_ssao_samples') else 0
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('HERO', out, 'bounds', tuple(lo), tuple(hi), 'cam', tuple(cam.location))
