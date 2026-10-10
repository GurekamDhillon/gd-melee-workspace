"""Animation splice recipes for the Goku XV2 port (owner-approved 2026-10-10).

A recipe (ports/goku-xv2/splices.json) names an engine row, or a move that maps to rows, and builds its clip out of
SEGMENTS cut from XV2 clips or from cross-port (retargeted retail Melee) clips, joined with blend frames. The recipes hold
clip names and frame numbers only, no animation data. They are baked into the clip in xv2_to_artist.animations(), BEFORE the
hover / ground logic, so ground_blend, the lift envelope and the exit-to-Wait ease still apply to the result.

    python ports/goku-xv2/tools/splice.py list                  # every recipe, target rows, segments, wired or not
    python ports/goku-xv2/tools/splice.py check [recipe]        # bake and validate (seams, loop, mirror, lengths); needs the XV2 IR
    python ports/goku-xv2/tools/splice.py preview <recipe>      # quick package with only that clip, then the LAB CLIPS command

Recipe (splices.json -> recipes.<name>):
  row | move     target engine row (AttackHi3) or move name (utilt: every row of the move in gameplay.json)
  wired          true: the recipe REPLACES the target row(s) in the build. false/absent: the clip is only built
                 as the CLIPS library row `s<name>` for viewing. Shipped rows never change unless a recipe is wired.
  example        true marks an EXAMPLE the owner has not picked
  frames         optional total retime (the whole spliced sequence is resampled to exactly this many frames)
  blend          default blend frames at every seam (3)
  loop           true: the last frames ease back toward frame 0 (loop_blend frames, default 4) and the loop seam is reported
  segments       [{clip, from, to, speed?, mirror?, root_yaw?, yaw_ramp?, hold?, blend?, marks?}]
      clip       an XV2 clip name (GOK_ATC_027) or a cross-port ref `melee:<fighter>/<action>` (melee:captain/AttackAirLw)
      from, to   source frames, inclusive; from > to plays the crop backwards
      speed      source frames per output frame (default 1; 2 = twice as fast)
      mirror     swap left/right limbs (names pair as L<->R) and mirror across the sagittal plane (x -> -x)
      root_yaw   degrees about Y on the root bone (180 = a turnaround); yaw_ramp eases it in from 0 (smoothstep) over the segment
      hold       extra frames holding the segment's last pose
      blend      frames inserted between the previous segment and this one (overrides the recipe default)
      marks      {label: source frame}: the label's frame in the output is reported (`hit` is checked against the move's windows)

Seams: `blend` transition frames are INSERTED between the previous segment's last pose and this segment's first pose
(smoothstep weight, slerp rotations, lerp translations and bone scales), so source frames are never altered and a strike frame
keeps its offset: output index = segment start + (source frame - from) / speed. The incoming segment's pelvis x/z and root
translation are shifted to the previous pose first (no translation pop). Everything is deterministic.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

PORT = Path(__file__).resolve().parents[1]
ROOT = PORT.parents[1]
SPLICES = PORT / 'splices.json'
SCHEMA = 'goku-splices/1'
DEFAULT_BLEND = 3
DEFAULT_LOOP_BLEND = 4
POP_MIN_DEG = 20.0      # a seam step above this AND above 1.5x the largest per-frame step within SEAM_REF_FRAMES of the seam is reported as a pop
LOOP_TOL_DEG = 8.0
SEAM_REF_FRAMES = 4     # frames either side of a seam that set the local speed a seam step is judged against
ROOT_BONE = 'b_C_Base'
HIPS_BONE = 'b_C_Pelvis'


# ---------------------------------------------------------------- data model

@dataclass
class Clip:
    """n frames of local bone rotations (xyzw quaternions), pelvis translation (hips), root translation and optional bone scales."""
    rot: dict
    hips: np.ndarray
    root: np.ndarray
    scl: dict = field(default_factory=dict)

    @property
    def n(self):
        return len(self.hips)

    def copy(self):
        return Clip({k: v.copy() for k, v in self.rot.items()}, self.hips.copy(), self.root.copy(), {k: v.copy() for k, v in self.scl.items()})


@dataclass
class Rig:
    names: list
    parents: list          # index or -1
    rest_q: np.ndarray     # (B,4) local rest rotations
    hips: str = HIPS_BONE
    root: str = ROOT_BONE

    @property
    def index(self):
        return {n: i for i, n in enumerate(self.names)}


class SpliceError(ValueError):
    pass


def smooth(w):
    w = np.clip(w, 0., 1.)
    return w * w * (3. - 2. * w)


def qnorm(q):
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


def qslerp(a, b, w):
    """Vectorised slerp of xyzw quaternions a, b (..., 4) by w (...), shortest arc."""
    a, b = qnorm(np.asarray(a, float)), qnorm(np.asarray(b, float))
    w = np.asarray(w, float)
    d = np.sum(a * b, axis=-1)
    b = np.where(d[..., None] < 0, -b, b)
    d = np.abs(d)
    th = np.arccos(np.clip(d, -1., 1.))
    s = np.sin(th)
    near = s < 1e-6
    sa = np.where(near, 1. - w, np.sin((1. - w) * th) / np.where(near, 1., s))
    sb = np.where(near, w, np.sin(w * th) / np.where(near, 1., s))
    return qnorm(sa[..., None] * a + sb[..., None] * b)


def angle_between(a, b):
    """Rotation angle in degrees between xyzw quaternions (..., 4)."""
    d = np.abs(np.sum(qnorm(a) * qnorm(b), axis=-1))
    return np.degrees(2. * np.arccos(np.clip(d, -1., 1.)))


def fill(clip, rig):
    """A copy of `clip` with every rig bone present (rest rotation where the clip has none) and float arrays."""
    out = Clip({}, np.asarray(clip.hips, float).copy(), np.asarray(clip.root, float).copy(), {k: np.asarray(v, float).copy() for k, v in clip.scl.items()})
    n = clip.n
    for i, name in enumerate(rig.names):
        out.rot[name] = np.asarray(clip.rot[name], float).copy() if name in clip.rot else np.repeat(rig.rest_q[i][None], n, axis=0)
    return out


def take(clip, idx):
    """Pose list of `clip` at integer indices."""
    idx = np.asarray(idx, int)
    return Clip({k: v[idx] for k, v in clip.rot.items()}, clip.hips[idx], clip.root[idx], {k: v[idx] for k, v in clip.scl.items()})


def concat(parts):
    names = list(parts[0].rot)
    scl = {k for p in parts for k in p.scl}
    return Clip({k: np.concatenate([p.rot[k] for p in parts]) for k in names},
                np.concatenate([p.hips for p in parts]), np.concatenate([p.root for p in parts]),
                {k: np.concatenate([p.scl.get(k, np.ones((p.n, 3))) for p in parts]) for k in sorted(scl)})


def mix(a, b, w):
    """Per-frame blend of two equal-length clips: slerp rotations, lerp translations and scales (w: (n,))."""
    w = np.asarray(w, float)
    scl = {k for p in (a, b) for k in p.scl}
    return Clip({k: qslerp(a.rot[k], b.rot[k], w) for k in a.rot}, a.hips + (b.hips - a.hips) * w[:, None], a.root + (b.root - a.root) * w[:, None],
                {k: a.scl.get(k, np.ones_like(b.scl.get(k, np.ones((a.n, 3))))) + (b.scl.get(k, np.ones((a.n, 3))) - a.scl.get(k, np.ones((a.n, 3)))) * w[:, None] for k in sorted(scl)})


def repeat_pose(clip, i, count):
    return take(clip, [i] * count)


# ---------------------------------------------------------------- sources

class ArraySource:
    """A Clip held as per-frame arrays, sampled at fractional frames by slerp/lerp (cross-port npz, tests)."""

    def __init__(self, clip, label='array'):
        self.clip, self.label = clip, label
        self.length = clip.n - 1

    def sample(self, tm):
        tm = np.clip(np.asarray(tm, float), 0., self.length)
        lo = np.floor(tm).astype(int)
        hi = np.minimum(lo + 1, self.length)
        w = tm - lo
        return mix(take(self.clip, lo), take(self.clip, hi), w)


def npz_clip(path):
    """A cross-port clip.npz (retarget tool: names, q (frames, bones, 4), hips_t (frames, 3)) plus its scale.json bone-scale tracks."""
    z = np.load(path)
    names = [str(x) for x in z['names']]
    q = z['q']
    n = len(q)
    clip = Clip({nm: q[:, i, :].copy() for i, nm in enumerate(names)}, z['hips_t'].astype(float).copy(), np.zeros((n, 3)))
    sj = Path(path).with_name('scale.json')
    if sj.exists():
        for bone, sc in json.loads(sj.read_text())['bones'].items():
            v = np.ones((n, 3))
            vals = np.asarray(sc['values'], float)
            v[:len(vals), sc['axis']] = vals[:n]
            clip.scl[bone] = v
    return clip


def lr_partner(name):
    """The mirror bone name: the first L/R token swapped (b_L_Arm1 <-> b_R_Arm1, item_socket.R <-> item_socket.L), else the same name."""
    toks = re.split(r'([_.])', name)
    for i, t in enumerate(toks):
        if t in ('L', 'R'):
            toks[i] = 'R' if t == 'L' else 'L'
            return ''.join(toks)
    return name


# ---------------------------------------------------------------- operations

def mirror(clip, rig, axis=0):
    """Mirror across the plane whose normal is `axis` (0: x = character-left/right, the sagittal plane; the rigs are Y-up).

    World rotations are mirrored as M R M with M = diag(-1,1,1) on the DELTA from the rest pose, and the left/right partner bone
    receives the mirrored delta of its partner (centre bones their own). Local rotations are rebuilt down the hierarchy; the pelvis and
    root translations are mirrored in their parent frames. mirror(mirror(c)) == c."""
    clip = fill(clip, rig)
    B, n = len(rig.names), clip.n
    M = np.eye(3)
    M[axis, axis] = -1.
    idx = rig.index
    partner = np.array([idx.get(lr_partner(nm), i) for i, nm in enumerate(rig.names)])
    L = np.stack([Rotation.from_quat(clip.rot[nm]).as_matrix() for nm in rig.names], axis=1)       # (n,B,3,3)
    RL = Rotation.from_quat(rig.rest_q).as_matrix()                                                 # (B,3,3)
    W = np.empty_like(L)
    RW = np.empty_like(RL)
    for b in range(B):                                                                               # parents precede children in a skeleton
        p = rig.parents[b]
        W[:, b] = L[:, b] if p < 0 else W[:, p] @ L[:, b]
        RW[b] = RL[b] if p < 0 else RW[p] @ RL[b]
    D = W @ np.swapaxes(RW, -1, -2)[None]
    Dm = M @ D @ M
    Wn = Dm[:, partner] @ RW[None]
    Ln = np.empty_like(L)
    for b in range(B):
        p = rig.parents[b]
        Ln[:, b] = Wn[:, b] if p < 0 else np.swapaxes(Wn[:, p], -1, -2) @ Wn[:, b]
    out = Clip({nm: Rotation.from_matrix(Ln[:, i]).as_quat() for i, nm in enumerate(rig.names)}, np.empty_like(clip.hips), np.empty_like(clip.root), {})
    # translations: parent-frame vector -> world (parent world rotation), mirror, -> new parent frame
    for arr_name, bone in (('hips', rig.hips), ('root', rig.root)):
        src = getattr(clip, arr_name)
        p = rig.parents[idx[bone]] if bone in idx else -1
        if p < 0:
            res = src @ M.T
        else:
            res = np.einsum('nij,nj->ni', np.swapaxes(Wn[:, p], -1, -2), np.einsum('ij,nj->ni', M, np.einsum('nij,nj->ni', W[:, p], src)))
        setattr(out, arr_name, res)
    for bone, v in clip.scl.items():                                                                 # a stretch follows its limb to the partner
        out.scl[nm_partner(bone, rig)] = v.copy()
    return out


def nm_partner(name, rig):
    p = lr_partner(name)
    return p if p in rig.index else name


def apply_yaw(clip, deg, ramp=False, root=ROOT_BONE):
    """Rotate the body about Y by `deg` on the root bone (left-multiplied, as the existing Turn row does); ramp eases it in from 0."""
    if not deg:
        return clip
    w = smooth(np.linspace(0., 1., clip.n)) if ramp and clip.n > 1 else np.ones(clip.n)
    ry = Rotation.from_euler('y', (np.radians(deg) * w)[:, None])
    out = clip.copy()
    out.rot[root] = (ry * Rotation.from_quat(out.rot[root])).as_quat()
    return out


def seg_times(frm, to, speed):
    if speed <= 0:
        raise SpliceError('speed must be > 0')
    n = int(math.floor(abs(to - frm) / speed + 1e-9)) + 1
    return frm + (1. if to >= frm else -1.) * speed * np.arange(n)


def retime(clip, count):
    """Resample to exactly `count` frames over the whole span (first and last pose kept)."""
    if count == clip.n:
        return clip
    if count < 2:
        raise SpliceError('retime needs at least 2 frames')
    return ArraySource(clip).sample(np.linspace(0., clip.n - 1., count))


def max_step(clip, bones=None):
    """Largest per-frame joint rotation change (degrees) over the clip, and the bone."""
    best, who = 0., ''
    for k, q in clip.rot.items():
        if clip.n < 2:
            break
        s = float(angle_between(q[:-1], q[1:]).max())
        if s > best:
            best, who = s, k
    return best, who


def pose_jump(a, i, b, j):
    """(degrees, bone) of the largest joint rotation difference between a's frame i and b's frame j."""
    best, who = 0., ''
    for k in a.rot:
        d = float(angle_between(a.rot[k][i], b.rot[k][j]))
        if d > best:
            best, who = d, k
    return best, who


# ---------------------------------------------------------------- bake

def segment_summary(seg):
    s = '%s f%g-%g' % (seg['clip'], seg['from'], seg['to'])
    if seg.get('speed', 1) != 1:
        s += ' x%g' % seg['speed']
    if seg.get('mirror'):
        s += ' mirrored'
    if seg.get('root_yaw'):
        s += ' yaw %g%s' % (seg['root_yaw'], ' ramped' if seg.get('yaw_ramp') else '')
    if seg.get('hold'):
        s += ' hold %d' % seg['hold']
    return s


def validate_recipe(name, r):
    segs = r.get('segments')
    if not segs:
        raise SpliceError('%s: a recipe needs segments' % name)
    if not (r.get('row') or r.get('move')):
        raise SpliceError('%s: a recipe needs `row` or `move`' % name)
    for i, s in enumerate(segs):
        for k in ('clip', 'from', 'to'):
            if k not in s:
                raise SpliceError('%s segment %d: missing `%s`' % (name, i, k))
        bad = set(s) - {'clip', 'from', 'to', 'speed', 'mirror', 'root_yaw', 'yaw_ramp', 'hold', 'blend', 'marks', 'note'}
        if bad:
            raise SpliceError('%s segment %d: unknown keys %s' % (name, i, sorted(bad)))


def recipe_length(r, default_blend=DEFAULT_BLEND):
    """The output length from the recipe alone (no animation data needed), before any gameplay minimum padding."""
    if r.get('frames'):
        return int(r['frames'])
    n = 0
    for i, s in enumerate(r['segments']):
        n += len(seg_times(s['from'], s['to'], s.get('speed', 1.))) + int(s.get('hold', 0))
        if i:
            n += int(s.get('blend', r.get('blend', default_blend)))
    return n


def bake(name, recipe, resolve, rig):
    """Bake one recipe. resolve(ref) -> a source with .length and .sample(times) -> Clip. Returns (Clip, report)."""
    validate_recipe(name, recipe)
    default_blend = int(recipe.get('blend', DEFAULT_BLEND))
    pieces, seams, segrep, notes = [], [], [], []
    start = 0
    for i, seg in enumerate(recipe['segments']):
        src = resolve(seg['clip'])
        times = seg_times(seg['from'], seg['to'], seg.get('speed', 1.))
        lo, hi = float(min(times[0], times[-1])), float(max(times[0], times[-1]))
        clamped = lo < -1e-9 or hi > src.length + 1e-9
        if clamped:
            notes.append('segment %d (%s): frames %g-%g outside the source 0-%g, held at the ends' % (i, seg['clip'], lo, hi, src.length))
        c = fill(src.sample(np.clip(times, 0., src.length)), rig)
        if seg.get('mirror'):
            c = mirror(c, rig)
        c = apply_yaw(c, seg.get('root_yaw', 0.), bool(seg.get('yaw_ramp')), rig.root)
        if seg.get('hold'):
            c = concat([c, repeat_pose(c, c.n - 1, int(seg['hold']))])
        blend = int(seg.get('blend', default_blend)) if i else 0
        seam = None
        if i:
            prev = pieces[-1]
            shift = prev.hips[-1] - c.hips[0]
            raw_t = dict(hips_xz=float(np.hypot(shift[0], shift[2])), hips_y=float(abs(shift[1])), root=float(np.linalg.norm(prev.root[-1] - c.root[0])))
            c.hips[:, [0, 2]] += shift[[0, 2]]
            c.root += prev.root[-1] - c.root[0]
            raw_deg, raw_bone = pose_jump(prev, prev.n - 1, c, 0)
            if blend:
                w = smooth((np.arange(blend) + 1.) / (blend + 1.))
                tr = mix(repeat_pose(prev, prev.n - 1, blend), repeat_pose(c, 0, blend), w)
                pieces.append(tr)
                start += blend
            seam = dict(between=[i - 1, i], blend=blend, raw_jump_deg=round(raw_deg, 2), raw_jump_bone=raw_bone, translation_before_fix=raw_t)
            seams.append(seam)
            seam['_prev'], seam['_next'], seam['_tr'] = pieces[-2] if blend else prev, c, pieces[-1] if blend else None
        marks = {lab: start + int(round((sf - seg['from']) / (seg.get('speed', 1.) * (1. if seg['to'] >= seg['from'] else -1.)))) for lab, sf in seg.get('marks', {}).items()}
        segrep.append(dict(index=i, clip=seg['clip'], summary=segment_summary(seg), out_start=start, out_end=start + c.n - 1, frames=c.n, marks=marks))
        pieces.append(c)
        start += c.n
    # per-seam pop check: the largest per-frame step across the seam against the segments' own largest per-frame step
    for s in seams:
        a, b, tr = s.pop('_prev'), s.pop('_next'), s.pop('_tr')
        chain = concat([take(a, [a.n - 1])] + ([tr] if tr is not None else []) + [take(b, [0])])
        step, who = max_step(chain)
        ref = max(max_step(a)[0], max_step(b)[0])
        # Judge the seam against the motion right beside it, not the whole segments: a fast strike elsewhere in a segment
        # (80 deg/frame) used to raise the bar to 120 and hide a 35-40 deg snap between a slow windup and that strike.
        local = max(max_step(take(a, range(max(0, a.n - SEAM_REF_FRAMES), a.n)))[0], max_step(take(b, range(min(b.n, SEAM_REF_FRAMES))))[0])
        s.update(max_step_deg=round(step, 2), max_step_bone=who, segment_step_deg=round(ref, 2), local_step_deg=round(local, 2),
                 pop=bool(step > max(POP_MIN_DEG, 1.5 * local)))
    out = concat(pieces)
    raw_frames = out.n
    if recipe.get('frames'):
        out = retime(out, int(recipe['frames']))
        k = (out.n - 1.) / max(raw_frames - 1., 1.)
        for sr in segrep:
            sr['out_start'], sr['out_end'] = int(round(sr['out_start'] * k)), int(round(sr['out_end'] * k))
            sr['marks'] = {m: int(round(f * k)) for m, f in sr['marks'].items()}
    loop_rep = None
    if recipe.get('loop'):
        lb = int(recipe.get('loop_blend', DEFAULT_LOOP_BLEND))
        if lb:
            lb = min(lb, out.n - 1)
            tail = take(out, range(out.n - lb, out.n))
            w = smooth((np.arange(lb) + 1.) / (lb + 1.))
            eased = mix(tail, repeat_pose(out, 0, lb), w)
            out = concat([take(out, range(out.n - lb)), eased])
        deg, bone = pose_jump(out, out.n - 1, out, 0)
        step, who = max_step(concat([take(out, [out.n - 1]), take(out, [0])]))
        loop_rep = dict(loop_blend=lb, last_to_first_deg=round(deg, 2), bone=bone, hips_y_step=round(float(abs(out.hips[-1][1] - out.hips[0][1])), 3),
                        ok=bool(deg <= LOOP_TOL_DEG))
    report = dict(recipe=name, frames=out.n, frames_before_retime=raw_frames, segments=segrep, seams=seams, loop=loop_rep, notes=notes,
                  max_step_deg=round(max_step(out)[0], 2), summary=' + '.join(sr['summary'] for sr in segrep),
                  ok=not any(s['pop'] for s in seams) and (loop_rep is None or loop_rep['ok']))
    return out, report


def pad_to(clip, count):
    """Hold the last pose up to `count` frames (the build's gameplay minimum clip length); never crops."""
    if count <= clip.n:
        return clip
    return concat([clip, repeat_pose(clip, clip.n - 1, count - clip.n)])


# ---------------------------------------------------------------- recipe file

def load(path=None):
    p = Path(path) if path else SPLICES
    if not p.exists():
        return {'schema': SCHEMA, 'recipes': {}}
    doc = json.loads(p.read_text(encoding='utf-8'))
    if doc.get('schema') != SCHEMA:
        raise SpliceError('%s: schema must be %s' % (p, SCHEMA))
    for k, r in doc['recipes'].items():
        validate_recipe(k, r)
    return doc


def library_name(recipe_name):
    """The CLIPS library row name of a recipe's clip (bank names are <= 31 chars)."""
    return re.sub(r'[^A-Za-z0-9_]', '_', 's' + recipe_name)[:31]


def target_rows(recipe, move_motions=None, motion_row=None):
    """Engine rows a recipe targets: its `row`, or every row of its `move` (move_motions: {move: [motion ids]}, motion_row: {motion id: row})."""
    if recipe.get('row'):
        return [recipe['row']]
    if move_motions is None or motion_row is None:
        return []
    return [motion_row[m] for m in move_motions.get(recipe['move'], []) if m in motion_row]


def native_range(row):
    """(min, median, max, mario, goku_now) frames for an engine row from tools/timing_audit data (native roster) and row-lengths.json; None where absent."""
    out = dict(min=None, median=None, max=None, mario=None, goku=None)
    td = ROOT / '_build/timing-audit/data.json'
    if td.exists():
        vals = [v[row] for v in json.loads(td.read_text())['native'].values() if isinstance(v, dict) and isinstance(v.get(row), (int, float))]
        if vals:
            out.update(min=min(vals), median=float(np.median(vals)), max=max(vals))
    rl = PORT / 'row-lengths.json'
    if rl.exists():
        e = json.loads(rl.read_text()).get(row)
        if e:
            out.update(mario=e.get('mario'), goku=e.get('goku'))
    return out


def length_check(frames, row):
    r = native_range(row)
    flag = None
    if r['min'] is not None and not (r['min'] - 1 <= frames <= r['max'] + 1):
        flag = 'length %d outside the native roster range %g-%g' % (frames, r['min'], r['max'])
    return dict(row=row, frames=frames, native=r, flag=flag)


def hit_check(report, windows):
    """Warn when a `hit` mark misses every hitbox window [[start, length], ...] of the move by more than 1 frame."""
    warns = []
    for sr in report['segments']:
        if 'hit' in sr['marks'] and windows:
            f = sr['marks']['hit']
            if not any(s - 1 <= f <= s + l for s, l in windows):
                warns.append('mark hit at f%d is outside the move windows %s' % (f, windows))
    return warns


def move_windows(recipe, motion_row, moves):
    """Hitbox windows [[start, length], ...] of the move a recipe targets (its `move`, or the move owning its `row`); [] when unknown."""
    out = []
    for m in moves:
        rows = [motion_row.get(x) for x in m.get('motions', [])]
        if m.get('name') == recipe.get('move') or (recipe.get('row') and recipe['row'] in rows):
            out += [list(w) for w in m.get('windows', [])]
    return out


def mirror_sanity(clip, rig):
    """Mirror report: partner pairs found, bones with an L/R name but no partner, and the involution error (degrees) of mirror(mirror(c))."""
    pairs = sorted({tuple(sorted((n, lr_partner(n)))) for n in rig.names if lr_partner(n) != n and lr_partner(n) in rig.index})
    lonely = sorted(n for n in rig.names if lr_partner(n) != n and lr_partner(n) not in rig.index)
    back = mirror(mirror(clip, rig), rig)
    c = fill(clip, rig)
    err = max(float(angle_between(back.rot[k], c.rot[k]).max()) for k in c.rot)
    return dict(pairs=len(pairs), unpaired=lonely, involution_error_deg=round(err, 4))


# ---------------------------------------------------------------- CLI

def cmd_list(args):
    doc = load(args.file)
    gp = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import strip_gameplay as SG
        gp = SG.load()
    except Exception:  # noqa: BLE001
        pass
    for name, r in doc['recipes'].items():
        wired = 'WIRED' if r.get('wired') else 'preview-only'
        ex = ' EXAMPLE' if r.get('example') else ''
        tgt = r.get('row') or ('move ' + r['move'])
        print('%s  [%s%s]  target %s  frames %d  library row %s' % (name, wired, ex, tgt, recipe_length(r), library_name(name)))
        for s in r['segments']:
            print('    ' + segment_summary(s) + ('  blend %s' % s['blend'] if 'blend' in s else ''))
        if r.get('note'):
            print('    note: ' + r['note'])
    return 0


def cmd_check(args):
    """Bake every recipe (or one) against the real XV2 data and print the seam / loop / length report. Writes _build/goku-xv2/splice-report.json."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import xv2_to_artist as X
    doc = load(args.file)
    names = [args.recipe] if args.recipe else list(doc['recipes'])
    source = X.Source(PORT / 'ir/goku.xv2.ir.json')
    mesh = X.build_mesh(source, 20.)
    ctx = X.splice_context(source, mesh)
    gp = PORT / 'gameplay.json'
    moves = json.loads(gp.read_text(encoding='utf-8')).get('moves', []) if gp.exists() else []
    out = {}
    bad = 0
    for n in names:
        clip, rep = bake(n, doc['recipes'][n], ctx['resolve'], ctx['rig'])
        rep['mirror_sanity'] = mirror_sanity(clip, ctx['rig']) if any(s.get('mirror') for s in doc['recipes'][n]['segments']) else None
        rep['length'] = [length_check(rep['frames'], r) for r in target_rows(doc['recipes'][n], *ctx['move_rows'])]
        rep['hit_check'] = hit_check(rep, move_windows(doc['recipes'][n], ctx['move_rows'][1], moves))
        print(json.dumps({k: v for k, v in rep.items() if k != 'segments'}, indent=1, default=str))
        out[n] = rep
        bad += 0 if rep['ok'] else 1
    dst = ROOT / '_build/goku-xv2/splice-report.json'
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1, default=str) + '\n', encoding='utf-8')
    return 1 if bad else 0


def cmd_preview(args):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import xv2_to_artist as X
    return X.splice_preview(args.recipe, args.file)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--file', default=None, help='recipe file (default ports/goku-xv2/splices.json)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list').set_defaults(fn=cmd_list)
    c = sub.add_parser('check')
    c.add_argument('recipe', nargs='?')
    c.set_defaults(fn=cmd_check)
    p = sub.add_parser('preview')
    p.add_argument('recipe')
    p.set_defaults(fn=cmd_preview)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == '__main__':
    raise SystemExit(main())
