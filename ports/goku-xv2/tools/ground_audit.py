"""Ground audit: does every GROUND row keep Goku's feet on the floor, frame by frame?

python ports/goku-xv2/tools/ground_audit.py [--rows Name,Name] [--json out.json]

Samples every frame of each ground row's bank clip through the installed FigaTree (the same path audit_gameplay.py uses), skins the mesh
(two influences per vertex) and measures, in fighter space (TopN origin = the floor, Y up):
  min_y     lowest posed vertex of the whole body                   -> BELOW    when < baseline - BELOW_EPS (sinking into the floor)
  foot_y    lower of (lowest vertex of the left foot/toe, same for the right) -> FLOATING when both feet are > baseline + FLOAT_EPS
baseline = the same measurement on Wait frame 0 (the rest stance on the floor). Units are model units (20 = his height).
Result per row: frames, worst min_y, worst foot height, BELOW / FLOATING frame ranges. Rows that are not meant to be on the floor
(aerials, jumps, falls, flight/IT, launches) are not audited. Output: _build/goku-xv2/ground-audit.json; FIDELITY.md reads it.
"""
import argparse
import json
import os
from pathlib import Path
import sys

import numpy as np

PORT = Path(__file__).resolve().parents[1]
ROOT = PORT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'ports/ir/tools'))
sys.path.insert(0, str(PORT / 'tools'))

import check_hitbox_positions as HP  # noqa: E402
import figatree  # noqa: E402
from audit_gameplay import rest_context, mesh_points  # noqa: E402

PKG = ROOT / '_build/goku-xv2' / os.environ.get('GOKU_AUTHOR', 'author-source') / 'package/mods/goku-xv2'
ART = ROOT / '_build/goku-xv2' / os.environ.get('GOKU_AUTHOR', 'author-source') / 'package/build'
OUT = ROOT / '_build/goku-xv2/ground-audit.json'
BELOW_EPS = 0.35   # model units (1.75% of his height)
FLOAT_EPS = 1.6    # both feet above the baseline by this = floating (8% of his height)

# rows the engine plays with the fighter on the floor
GROUND_PREFIX = ('Wait', 'Walk', 'Dash', 'Run', 'Turn', 'Squat', 'Attack11', 'Attack12', 'Attack13', 'Attack100', 'AttackS3', 'AttackHi3',
                 'AttackLw3', 'AttackS4', 'AttackHi4', 'AttackLw4', 'AttackDash', 'Catch', 'Throw', 'Guard', 'Escape', 'Landing',
                 'Cliff', 'Down', 'Passive', 'Appeal', 'Kame', 'Rush', 'Counter', 'Riposte', 'KiCharge', 'Entry', 'Ottotto', 'Rebirth')
SKIP_EXACT = {'EscapeAir', 'LandingFallSpecial', 'CliffJumpQuick2', 'CliffJumpSlow2'}


def ground_rows(rows):
    out = []
    for r in rows:
        name, clip = r['row'], r.get('clip')
        if not clip or name in SKIP_EXACT or name.startswith('LandingAir'):
            continue
        if name.startswith(GROUND_PREFIX) and not name.startswith(('AirCatch',)):
            out.append((name, clip))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rows', help='comma list of row names (default: every ground row)')
    ap.add_argument('--json', type=Path, default=OUT)
    ap.add_argument('--files', type=Path, default=PKG / 'files', help='dir with plan.json and the bank (default: the built package)')
    ap.add_argument('--mesh', type=Path, default=None)
    ap.add_argument('--before', action='store_true', help='evidence: audit a GOKU_GROUND=0 build; rows chosen by name (ground_rows), mode unknown')
    args = ap.parse_args()
    plan = json.loads((args.files / 'plan.json').read_text(encoding='utf-8'))
    mesh = json.loads((args.mesh or next(ART.glob('mesh_*.json'))).read_text(encoding='utf-8'))
    bank = (args.files / plan['bank']['file']).read_bytes()
    rest, native, worlds = rest_context(mesh, plan)
    points, weights = mesh_points(mesh)
    n = len(points)
    J = np.zeros((n, 2), dtype=int)
    W = np.zeros((n, 2))
    for i, ww in enumerate(weights):
        for k, (j, w) in enumerate(ww[:2]):
            J[i, k], W[i, k] = j, w
    # bind-pose inverse per joint
    bind_inv = [np.linalg.inv(w) for w in worlds]
    roles = plan['roles']
    foot_joints = {side: {roles['foot.' + side][0], roles['toe.' + side][0]} for side in 'LR'}
    foot_mask = {side: np.array([any(J[i, k] in foot_joints[side] and W[i, k] > 0.5 for k in range(2)) for i in range(n)]) for side in 'LR'}
    points_h = np.hstack([points, np.ones((n, 1))])

    def sample_clip(clip):
        rec = plan['bank']['clips'][clip]
        _, tree = figatree.parse_archive(bank[rec['offset']:rec['offset'] + rec['bytes']])
        frames = int(tree['frames'])
        res = []
        for f in range(0, frames + 1):
            pose = HP.pose_matrices(tree, native, rest, f)
            skin = np.array([pose[i] @ bind_inv[i] for i in range(len(pose))])
            y = np.zeros(n)
            for k in range(2):
                m = skin[J[:, k]]
                y += W[:, k] * np.einsum('nj,nj->n', m[:, 1, :], points_h)
            feet = [float(y[foot_mask[s]].min()) if foot_mask[s].any() else float(y.min()) for s in 'LR']
            res.append((float(y.min()), min(feet), max(feet)))
        return res

    rows = json.loads((PORT / 'ANIM-ROWS.json').read_text(encoding='utf-8'))['rows']
    targets = [(r['row'], r['clip'], (r.get('source') or {}).get('ground_mode')) for r in rows
               if r.get('clip') and (r.get('source') or {}).get('ground_mode')]
    if args.before:
        after = {n for n, _, _ in targets}
        targets = [(n, c, 'BEFORE') for n, c in ground_rows(rows) if n in after]
    if args.rows:
        want = set(args.rows.split(','))
        targets = [t for t in targets if t[0] in want]
    hover = 2.0
    result = {'below_eps': BELOW_EPS, 'hover_y': hover, 'float_eps': FLOAT_EPS,
              'method': 'FigaTree pose of every frame of the built bank clip, 2-influence skinning of the mesh; heights in model units above the floor (TopN origin), 20 = his height',
              'rows': {}}
    seen = {}
    for name, clip, mode in targets:
        if clip not in seen:
            seen[clip] = sample_clip(clip)
        s_ = seen[clip]
        below = [i for i, (mn, fl, fh) in enumerate(s_) if mn < -BELOW_EPS]
        # HOVER rows: the lowest point must stay within hover +- eps; ANCHOR rows are only measured (flight-stance legs may hang above the floor)
        off = [i for i, (mn, fl, fh) in enumerate(s_) if mode == 'HOVER' and mn > hover + 6.0]
        feet_up = [i for i, (mn, fl, fh) in enumerate(s_) if fl > FLOAT_EPS]
        ledge = name.startswith('Cliff')
        result['rows'][name] = {'clip': clip, 'mode': mode, 'frames': len(s_), 'min_y': min(x[0] for x in s_), 'max_lowest': max(x[0] for x in s_),
                                'below': _ranges(below), 'hover_off': _ranges(off), 'feet_up': _ranges(feet_up),
                                'below_frames': len(below), 'hover_off_frames': len(off), 'feet_up_frames': len(feet_up), 'ledge': ledge}
    R = result['rows'].values()
    result['counts'] = {'rows': len(result['rows']), 'hover': sum(1 for r in R if r['mode'] == 'HOVER'), 'anchor': sum(1 for r in R if r['mode'] == 'ANCHOR'),
                        'below_rows': sum(1 for r in R if r['below_frames'] and not r['ledge']), 'hover_off_rows': sum(1 for r in R if r['hover_off_frames']),
                        'ledge_rows_below': sum(1 for r in R if r['below_frames'] and r['ledge'])}
    args.json.write_text(json.dumps(result, indent=1), encoding='utf-8')
    print(json.dumps(result['counts']))
    return 1 if result['counts']['below_rows'] else 0


def _ranges(idx):
    out, start, prev = [], None, None
    for i in idx:
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            out.append([start, prev])
            start = prev = i
    if start is not None:
        out.append([start, prev])
    return out


if __name__ == '__main__':
    raise SystemExit(main())
