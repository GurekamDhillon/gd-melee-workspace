"""Preview montages and motion metrics for every XV2 clip (x* actions) in goku.blend.

Run from the workspace root:
  blender --background <goku.blend> --python THIS -- --out <dir> [--clips a,b] [--limit N]

Writes <out>/<clip>.png (6 frames side by side, 256 px each, grey background, no text)
and <out>/metrics.json. The .blend is read only; it is never saved.

Conventions: model (x,y,z) -> Blender (x,-z,y); character forward is -Y, up is +Z.
Camera is orthographic at -X looking toward +X, so -Y (forward) points to the image right.
Metrics are in Blender world units; speeds are world units per frame.
"""
import argparse
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


ARMATURE = 'GokuExport'
MESH = 'Goku'
PELVIS = 'b_C_Pelvis'
EFFECTORS = ['b_L_Hand', 'b_R_Hand', 'b_L_Foot', 'b_R_Foot']
PREFIX = 'x'
N_FRAMES = 6
METRIC_STEP = 2
PX = 256
MARGIN = 1.15
BG = 0.85


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--clips', default='')
    ap.add_argument('--limit', type=int, default=0)
    return ap.parse_args(argv)


def setup_scene():
    scene = bpy.context.scene
    arm = bpy.data.objects[ARMATURE]
    mesh = bpy.data.objects[MESH]
    if arm.animation_data is None:
        arm.animation_data_create()
    for track in arm.animation_data.nla_tracks:
        track.mute = True
    r = scene.render
    r.engine = 'BLENDER_WORKBENCH'
    r.resolution_x = PX
    r.resolution_y = PX
    r.resolution_percentage = 100
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGBA'
    r.film_transparent = True
    sh = scene.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'SINGLE'
    sh.single_color = (0.55, 0.6, 0.7)
    sh.show_object_outline = False
    cam_data = bpy.data.cameras.new('RemakePreviewCam')
    cam_data.type = 'ORTHO'
    cam_data.clip_start = 0.01
    cam_data.clip_end = 5000.0
    cam = bpy.data.objects.new('RemakePreviewCam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return scene, arm, mesh, cam


def set_frame(scene, frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    return bpy.context.evaluated_depsgraph_get()


def bone_world(arm, deps, name):
    ev = arm.evaluated_get(deps)
    pb = ev.pose.bones[name]
    return (ev.matrix_world @ pb.matrix).translation.copy()


def assign_action(arm, action):
    ad = arm.animation_data
    ad.action = action
    if getattr(action, 'slots', None) and len(action.slots) > 0:
        ad.action_slot = action.slots[0]


def sample_frames(f0, f1, n):
    if f1 <= f0:
        return [f0] * n
    return [int(round(f0 + i * (f1 - f0) / (n - 1))) for i in range(n)]


def render_clip(scene, arm, mesh, cam, action, out_png):
    f0 = int(math.floor(action.frame_range[0]))
    f1 = int(math.ceil(action.frame_range[1]))
    assign_action(arm, action)
    frames = sample_frames(f0, f1, N_FRAMES)

    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    for fr in frames:
        deps = set_frame(scene, fr)
        ev = mesh.evaluated_get(deps)
        for corner in ev.bound_box:
            w = ev.matrix_world @ Vector(corner)
            for k in range(3):
                lo[k] = min(lo[k], w[k])
                hi[k] = max(hi[k], w[k])
    span = max(hi[1] - lo[1], hi[2] - lo[2]) * MARGIN
    if not span > 0:
        span = 1.0
    cy = (lo[1] + hi[1]) / 2
    cz = (lo[2] + hi[2]) / 2
    loc = Vector((lo[0] - 2 * span, cy, cz))
    target = Vector((lo[0], cy, cz))
    cam.location = loc
    cam.rotation_euler = (target - loc).to_track_quat('-Z', 'Z').to_euler()
    cam.data.ortho_scale = span

    tmp_dir = tempfile.mkdtemp(prefix='remake_preview_')
    panels = []
    try:
        for i, fr in enumerate(frames):
            set_frame(scene, fr)
            tmp_png = os.path.join(tmp_dir, f'f{i}.png')
            scene.render.filepath = tmp_png
            bpy.ops.render.render(write_still=True)
            img = bpy.data.images.load(tmp_png, check_existing=False)
            flat = np.empty(PX * PX * 4, dtype=np.float32)
            img.pixels.foreach_get(flat)
            bpy.data.images.remove(img)
            os.remove(tmp_png)
            arr = flat.reshape(PX, PX, 4)[::-1]  # Blender rows are bottom-up
            rgb = arr[..., :3]
            a = arr[..., 3:4]
            rgb = rgb * a + BG * (1.0 - a)
            panels.append(np.concatenate([rgb, np.ones_like(a)], axis=2))
    finally:
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

    montage = np.concatenate(panels, axis=1)  # (PX, PX*N, 4), top-down
    h, w = montage.shape[0], montage.shape[1]
    flipped = np.ascontiguousarray(montage[::-1]).astype(np.float32).ravel()
    out = bpy.data.images.new('remake_montage', width=w, height=h, alpha=True)
    out.pixels.foreach_set(flipped)
    out.filepath_raw = str(out_png)
    out.file_format = 'PNG'
    out.save()
    bpy.data.images.remove(out)
    return frames


def measure_clip(scene, arm, action):
    f0 = int(math.floor(action.frame_range[0]))
    f1 = int(math.ceil(action.frame_range[1]))
    samples = list(range(f0, f1 + 1, METRIC_STEP))
    if not samples:
        samples = [f0]
    pelvis = []
    eff = {e: [] for e in EFFECTORS}
    for fr in samples:
        deps = set_frame(scene, fr)
        pelvis.append((fr, bone_world(arm, deps, PELVIS)))
        for e in EFFECTORS:
            eff[e].append((fr, bone_world(arm, deps, e)))

    # Forward is -Y. Reach is measured from the pelvis position projected on the floor.
    best_reach = None
    best_above = None
    best_low = None
    for e in EFFECTORS:
        for (fr, pos), (_, pp) in zip(eff[e], pelvis):
            reach = -(pos.y - pp.y)
            above = pos.z - pp.z
            if best_reach is None or reach > best_reach[0]:
                best_reach = (reach, e, fr)
            if best_above is None or above > best_above[0]:
                best_above = (above, e, fr)
            if best_low is None or pos.z < best_low[0]:
                best_low = (pos.z, e, fr)

    pz = [(fr, p.z) for fr, p in pelvis]
    pz_min = min(pz, key=lambda t: t[1])
    pz_max = max(pz, key=lambda t: t[1])

    def path_len(vals):
        return sum(abs(vals[i + 1] - vals[i]) for i in range(len(vals) - 1))

    px = [p.x for _, p in pelvis]
    py = [p.y for _, p in pelvis]
    pzs = [p.z for _, p in pelvis]
    fwd = [-y for y in py]

    best_speed = None
    for e in EFFECTORS:
        seq = eff[e]
        for i in range(1, len(seq)):
            (f_a, a), (f_b, b) = seq[i - 1], seq[i]
            dt = f_b - f_a
            if dt <= 0:
                continue
            speed = (b - a).length / dt
            if best_speed is None or speed > best_speed[0]:
                best_speed = (speed, e, f_b)

    def r(v):
        return None if v is None else round(v, 4)

    return {
        'frames': f1 - f0 + 1,
        'source_first': f0,
        'source_last': f1,
        'sampled_frames': len(samples),
        'metric_step': METRIC_STEP,
        'max_forward_reach': {'value': r(best_reach[0]), 'bone': best_reach[1], 'frame': best_reach[2]},
        'max_height_above_pelvis': {'value': r(best_above[0]), 'bone': best_above[1], 'frame': best_above[2]},
        'lowest_effector_height': {'value': r(best_low[0]), 'bone': best_low[1], 'frame': best_low[2]},
        'pelvis_height_min': {'value': r(pz_min[1]), 'frame': pz_min[0]},
        'pelvis_height_max': {'value': r(pz_max[1]), 'frame': pz_max[0]},
        'pelvis_travel_path': {
            'forward': r(path_len(fwd)),
            'sideways': r(path_len(px)),
            'vertical': r(path_len(pzs)),
        },
        'pelvis_travel_net': {
            'forward': r(fwd[-1] - fwd[0]),
            'sideways': r(px[-1] - px[0]),
            'vertical': r(pzs[-1] - pzs[0]),
        },
        'fastest_effector': {
            'units_per_frame': r(best_speed[0]) if best_speed else None,
            'bone': best_speed[1] if best_speed else None,
            'frame': best_speed[2] if best_speed else None,
        },
    }


def main():
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()

    scene, arm, mesh, cam = setup_scene()
    for name in (ARMATURE, MESH):
        if name not in bpy.data.objects:
            raise SystemExit(f'missing object {name}')
    for bone in EFFECTORS + [PELVIS]:
        if bone not in arm.data.bones:
            raise SystemExit(f'missing bone {bone}')

    if args.clips.strip():
        wanted = [c.strip() for c in args.clips.split(',') if c.strip()]
    else:
        wanted = sorted(a.name for a in bpy.data.actions if a.name.startswith(PREFIX))
    if args.limit:
        wanted = wanted[:args.limit]

    metrics = {'clips': {}, 'failed': {}}
    rendered = 0
    for name in wanted:
        try:
            action = bpy.data.actions.get(name)
            if action is None:
                raise KeyError('action not found in blend')
            png = out / f'{name}.png'
            render_frames = render_clip(scene, arm, mesh, cam, action, png)
            if not png.exists() or png.stat().st_size == 0:
                raise RuntimeError('PNG missing or empty after save')
            assign_action(arm, action)
            m = measure_clip(scene, arm, action)
            m['render_frames'] = render_frames
            metrics['clips'][name] = m
            rendered += 1
        except Exception as exc:  # log and continue
            metrics['failed'][name] = f'{type(exc).__name__}: {exc}'
            print(f'FAILED {name}: {type(exc).__name__}: {exc}', flush=True)
        (out / 'metrics.json').write_text(json.dumps(metrics, indent=1), encoding='utf-8')

    metrics['summary'] = {
        'requested': len(wanted),
        'rendered': rendered,
        'failed': len(metrics['failed']),
        'seconds': round(time.time() - started, 1),
    }
    (out / 'metrics.json').write_text(json.dumps(metrics, indent=1), encoding='utf-8')
    print('REMAKE_PREVIEW', metrics['summary'], str(out), flush=True)


if __name__ == '__main__':
    main()
