"""Side-by-side Blender preview of Goku's Turn / TurnRun / RunBrake: his current clips and the cross-ported candidate sets, on his mesh.

    GW_SITE=... blender -b _build/goku-xv2/turn-preview/current/goku.blend --python ports/goku-xv2/tools/turn_preview_blend.py -- \
        --project ports/goku-xv2 --sets falcon,marth,fox --save _build/goku-xv2/turn-preview/goku_turn_preview.blend [--sheets DIR]

Each set is a full artist bake (GOKU_LOCO_SET=<set> + GOKU_AUTHOR=turn-preview/<set> xv2_to_artist.py --blend; tools/turn_preview.sh runs all of them),
so the candidate rows carry the same HOVER / PLANT stance rules and row-length fit as the shipped build. The set blends are read from
_build/goku-xv2/turn-preview/<set>/goku.blend and their Turn / TurnRun / RunBrake actions are appended as <Set>_<Row>.

The scene is a grid: one row per move (Turn, TurnRun, RunBrake), one column per set (Current first), each a copy of the rig with a text label.
Also writes a foot-slide metric (turn_preview_metrics.json next to the blend): per rig, frames, and the horizontal travel of the planted foot per frame.
Everything written is disc-derived (retargeted retail animation): keep it under _build (git-ignored).
"""
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

for extra in filter(None, os.environ.get('GW_SITE', '').split(os.pathsep)):
    sys.path.insert(0, extra)
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/blender'))
from geno_workbench import nla  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


ROWS = ['Turn', 'TurnRun', 'RunBrake']
SETS = [s for s in opt('--sets', 'falcon,marth,fox').split(',') if s]
PREVIEW = ROOT / '_build/goku-xv2/turn-preview'
LABEL = {'current': 'CURRENT', 'falcon': 'FALCON', 'marth': 'MARTH', 'fox': 'FOX'}
DX, DZ = 22.0, 30.0

# 1. append the candidates' actions
for s in SETS:
    src = PREVIEW / s / 'goku.blend'
    with bpy.data.libraries.load(str(src), link=False) as (data_from, data_to):
        data_to.actions = [r for r in ROWS if r in data_from.actions]
    for a in data_to.actions:
        if a is None:
            continue
        a.name = '%s_%s' % (s.capitalize(), a.name.split('.')[0])
        a.use_fake_user = True
for r in ROWS:   # the current clips keep their names; alias them as Current_<row>
    a = bpy.data.actions[r]
    a.name = 'Current_' + r
    a.use_fake_user = True

base_arm = bpy.data.objects['GokuExport']
base_mesh = bpy.data.objects['Goku']
coll = bpy.context.scene.collection
cam_old = bpy.data.objects.get('ArtReviewCamera')
sets = ['current'] + SETS
rigs = {}


def clone(col, row_i, s, r):
    arm = base_arm.copy()
    arm.name = 'rig_%s_%s' % (s, r)
    arm.animation_data_clear()
    mesh = base_mesh.copy()
    mesh.name = 'mesh_%s_%s' % (s, r)
    mesh.modifiers.clear()
    mesh.parent = arm
    mod = mesh.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    for o in (arm, mesh):
        coll.objects.link(o)
    arm.location = (col * DX, 0.0, -row_i * DZ)
    act = bpy.data.actions['%s_%s' % (s.capitalize(), r)]
    ad = arm.animation_data_create()
    ad.action = act
    nla.bind_slot(ad, act)
    return arm


for ri, r in enumerate(ROWS):
    for ci, s in enumerate(sets):
        rigs[(s, r)] = clone(ci, ri, s, r)
        act = bpy.data.actions['%s_%s' % (s.capitalize(), r)]
        txt = bpy.data.objects.new('label_%s_%s' % (s, r), bpy.data.curves.new('label_%s_%s' % (s, r), 'FONT'))
        txt.data.body = '%s  %s  (%d f)' % (LABEL.get(s, s.upper()), r, int(act.frame_range[1]) + 1)
        txt.data.size = 1.6
        txt.data.align_x = 'CENTER'
        txt.rotation_euler = (math.pi / 2, 0, 0)
        txt.location = (ci * DX, 0, -ri * DZ - 3.0)
        coll.objects.link(txt)
for o in (base_arm, base_mesh):
    bpy.data.objects.remove(o, do_unlink=True)
if cam_old:
    bpy.data.objects.remove(cam_old, do_unlink=True)

sc = bpy.context.scene
last = max(int(a.frame_range[1]) for a in bpy.data.actions if a.name.split('_')[0] in {x.capitalize() for x in sets})
sc.frame_start, sc.frame_end = 0, last

# 2. foot-slide metric
metrics = {}
bpy.context.view_layer.update()
for (s, r), arm in rigs.items():
    foot_xy, lowest, pelvis = [], [], []
    for f in range(0, int(arm.animation_data.action.frame_range[1]) + 1):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        mw = arm.matrix_world
        feet = {n: mw @ arm.pose.bones[n].head for n in ('b_L_Foot', 'b_R_Foot')}
        toes = {n: mw @ arm.pose.bones[n].tail for n in ('b_L_Toe', 'b_R_Toe')}
        pts = list(feet.values()) + list(toes.values())
        foot_xy.append({k: (v.x, v.y, v.z) for k, v in list(feet.items()) + list(toes.items())})
        pelvis.append(tuple(mw @ arm.pose.bones['b_C_Pelvis'].head))
        lowest.append(min(p.z for p in pts))
    # planted foot: per frame the lower of the two ankles; slide = its horizontal travel to the next frame, counted when it is within 0.6 units of the lowest point of the clip
    floor = min(lowest)
    slides = []
    for i in range(len(foot_xy) - 1):
        for n in ('b_L_Foot', 'b_R_Foot'):
            a, b = foot_xy[i][n], foot_xy[i + 1][n]
            if min(a[2], b[2]) - floor < 0.6 + 1.0:   # ankle bone sits ~1 unit over the sole
                slides.append(math.hypot(a[0] - b[0], a[1] - b[1]))
    metrics['%s/%s' % (s, r)] = {
        'frames': len(foot_xy),
        'planted_foot_slide_mean': round(sum(slides) / max(len(slides), 1), 4),
        'planted_foot_slide_max': round(max(slides) if slides else 0.0, 4),
        'planted_samples': len(slides),
        'lowest_point_min': round(floor - arm.location.z, 3),
        'lowest_point_max': round(max(lowest) - arm.location.z, 3),
        'pelvis_height_range': [round(min(p[2] for p in pelvis) - arm.location.z, 3), round(max(p[2] for p in pelvis) - arm.location.z, 3)],
        'pelvis_xy_travel': round(max(math.hypot(p[0] - pelvis[0][0], p[1] - pelvis[0][1]) for p in pelvis), 3),
    }
sc.frame_set(0)

# 3. camera, light, render setup
cam = bpy.data.objects.new('TurnPreviewCam', bpy.data.cameras.new('TurnPreviewCam'))
sc.collection.objects.link(cam)
cam.data.type = 'ORTHO'
cam.data.clip_end = 1000
w, h = len(sets) * DX, len(ROWS) * DZ
cam.data.ortho_scale = max(w, h * 16 / 9) + 4
cam.location = ((len(sets) - 1) * DX / 2, -150, -(len(ROWS) - 1) * DZ / 2 + 8)
cam.rotation_euler = (math.pi / 2, 0, 0)
sc.camera = cam
sc.render.engine = 'BLENDER_WORKBENCH'
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'SINGLE'
sc.display.shading.single_color = (0.85, 0.7, 0.4)
sc.world.color = (0.1, 0.1, 0.12) if sc.world else None

sheets = opt('--sheets')
if sheets:
    out = Path(sheets)
    out.mkdir(parents=True, exist_ok=True)
    for f in range(0, last + 1, 3):
        sc.frame_set(f)
        sc.render.filepath = str((out / ('grid_%02d.png' % f)).resolve())
        sc.render.image_settings.file_format = 'PNG'
        bpy.ops.render.render(write_still=True)
    print('TURN_PREVIEW sheets ->', out)

save = opt('--save')
if save:
    Path(save).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(save).resolve()))
    Path(save).with_name('turn_preview_metrics.json').write_text(json.dumps(metrics, indent=1), encoding='utf-8')
    print('TURN_PREVIEW saved', save)
print('TURN_PREVIEW metrics', json.dumps(metrics))
