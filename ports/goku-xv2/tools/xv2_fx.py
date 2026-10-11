"""Convert Xenoverse 2's Kamehameha effects (skill 000_GOK_KMH) into Geno effect packages, LOCALLY.

    python ports/goku-xv2/tools/xv2_fx.py            -> _build/goku-xv2/fx/P_TrailGokuXKame*/ (+ _build/xv2-kame/fx/summary.json)

Inputs (never committed): the local dumps written by tools/xv2x/fx (`Xv2Fx`: .emp/.emo JSON, DDS -> PNG) under _build/xv2-kame/fx/000_GOK_KMH/,
and the decoded material tables of the shallow export (README.md: "Read-only source package"). Output: git-ignored _build packages in the
format of melee/docs/geno.md section 20, bound by tools/build.py (FX_ARTICLES / FX_STATES). Only this converter and its numbers are committed.

What is converted (EEPK 000_GOK_KMH.eepk, BAC entry 0/1/2 effect ids):
  charge    effect 0   Kmh_Crg.emp (ball sprite stack), Kmh_CrgON.emp (step flash), Kmh_tsubu.emp (motes), at the hand
  muzzle    effect 1   Kmh_Fire.emo (flare dome) + Kmh_Ring.emp, once at release
  beam      effect 3-5 Kmh_Bas.emo (core + 2 shells, UV-scrolling textures from the material table), Kmh_Hand.emo (head ball), and the
                       particle files Kmh_Fireptcl / Kmh_Wav / Kmh_4ptcl / Kmh_LineAll at the beam's head
Every approximation is listed in _research/xv2-kamehameha-2026-10-10.md.
"""
import base64
import json
import math
import re
import sys
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
WT = PORT.parents[1]
sys.path.insert(0, str(PORT / 'tools'))
from kame_geom import ROT as RISE, along, D  # noqa: E402  (the beam's direction in the hand frame)

EXPORT_ROOT = Path('E:/Torrents/Dragon.Ball.Xenoverse.2.Future.Saga.Chapter.4-RUNE/modding/exports/goku-base-shallow-v0.1/decoded/skill')
SKILLS = {'KMH': dict(code='000_GOK_KMH', px='Kmh', kind='SPA'), 'CKM': dict(code='000_GOK_CKM', px='Ckm', kind='ULT')}
SK = SKILLS['KMH']
XV2 = WT / '_build/xv2-kame/fx/000_GOK_KMH'
EXPORT = EXPORT_ROOT / 'SPA/000_GOK_KMH'
OUT = WT / '_build/goku-xv2/fx'
TEMPLATE = json.loads((PORT / 'tools/fx_emitter_template.json').read_text(encoding='utf-8'))
FPS = 60.0
ALPHA_ONLY = {'Wev00', 'Wev01', 'wev02', 'smk00', 'tsubu00'}   # white-on-black masks: the source reads the alpha channel; PNG already has it


# ---------------------------------------------------------------- small math (rotations are applied X, then Y, then Z, as in geno.md 20.3)
def rot_mat(rx, ry, rz):
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    X = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    Y = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    Z = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    return mm(Z, mm(Y, X))


def mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mv(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def euler_of(m):
    """Inverse of rot_mat (M = Z Y X): returns (rx, ry, rz)."""
    sy = max(-1.0, min(1.0, -m[2][0]))
    ry = math.asin(sy)
    if abs(sy) < 0.99999:
        return math.atan2(m[2][1], m[2][2]), ry, math.atan2(m[1][0], m[0][0])
    return math.atan2(-m[1][2], m[1][1]), ry, 0.0


R_RISE = rot_mat(*RISE)   # takes a mesh/emitter +Z onto the beam direction D in the hand's frame

# XV2's TRS frame (the projectile) has forward = -Z: Kmh_Bas.obj.ema rotates the mesh by TRS Rotation X = -90, which lays its tube (which extends along -Y
# from the dome) toward +Z, behind the dome; the particle files' own -90 degrees about X sends their 'up' emission to -Z, forward. Turning that frame 180 degrees
# about Y gives forward = +Z, then RISE puts +Z on the beam direction in the hand's frame.
EMP_ROT = list(RISE)   # decided: the particle files keep forward = +Z (their offsets of -4 m sit behind the head, their -90 degree emitters spray back from it)


# ---------------------------------------------------------------- reading the XV2 dumps
def kv_const(o, dflt=0.0):
    """A KeyframedValue/Vector's constant as a list (vectors) or float."""
    if o is None:
        return dflt
    c = o.get('Constant')
    return c.get('Values', c) if isinstance(c, dict) else c


def kv_keys(o):
    """[(t, value)] of an animated value (t = life ratio), or [] if constant."""
    ks = o.get('Keyframes') or []
    if not (o.get('IsAnimated') or len(ks) > 1):
        return []
    out = []
    for k in ks:
        v = k['Value']
        out.append((k['Time'], v.get('Values', v) if isinstance(v, dict) else v))
    return sorted(out, key=lambda kk: kk[0])


def sample(o, t, comp=None):
    """Value of a key curve at life ratio t (linear)."""
    ks = kv_keys(o)
    if not ks:
        v = kv_const(o)
        return v[comp] if (comp is not None and isinstance(v, list)) else v

    def pick(v):
        return v[comp] if (comp is not None and isinstance(v, list)) else v
    if t <= ks[0][0]:
        return pick(ks[0][1])
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1:
            f = (t - t0) / max(t1 - t0, 1e-9)
            a, b = pick(v0), pick(v1)
            return [x + (y - x) * f for x, y in zip(a, b)] if isinstance(a, list) else a + (b - a) * f
    return pick(ks[-1][1])


def curve_times(*objs):
    ts = {0.0, 1.0}
    for o in objs:
        for t, _ in kv_keys(o):
            ts.add(min(1.0, max(0.0, float(t))))
    ts = sorted(ts)
    while len(ts) > 8:   # the runtime keeps 8 keys: drop the interior time with the smallest change
        ts.pop(len(ts) // 2)
    return ts


def load_emp(name):
    return json.loads((XV2 / (SK['code'] + '.pbind.emb') / (name + '.emp.json')).read_text(encoding='utf-8'))


def emm(path):
    d = json.loads(path.read_text(encoding='utf-8'))
    return {m['Index']: m for m in d['Materials']}


def use_skill(key):
    """Select the XV2 skill whose dumps the converter reads: KMH (Kamehameha) or CKM (Super Kamehameha)."""
    global SK, XV2, EXPORT, PTCL_MATS, PTCL_TEX
    SK = SKILLS[key]
    XV2 = WT / '_build/xv2-kame/fx' / SK['code']
    EXPORT = EXPORT_ROOT / SK['kind'] / SK['code']
    PTCL_MATS = emm(EXPORT / (SK['code'] + '.ptcl.emm.json'))
    PTCL_TEX = {e['index']: Path(e['name']).stem for e in json.loads((XV2 / (SK['code'] + '.ptcl.emb/index.json')).read_text(encoding='utf-8'))}


use_skill('KMH')


def mat_param(m, name, dflt=None):
    for p in m['Parameters']:
        if p['Name'] == name:
            try:
                return float(p['Value'])
            except ValueError:
                return p['Value']
    return dflt


# ---------------------------------------------------------------- texture registry (per package)
class Pkg:
    def __init__(self, name):
        self.name = name
        self.emitters = []
        self.textures = []   # {name, file, w, h}
        self.meshes = []
        self.dir = OUT / name
        self.files = {}      # relative path -> source png / mesh json text

    def texture(self, stem, src_png):
        if not any(t['name'] == stem for t in self.textures):
            from PIL import Image
            with Image.open(src_png) as im:
                w, h = im.size
            self.textures.append({'name': stem, 'file': 'tex/%s.png' % stem, 'w': w, 'h': h, 'source_format': 'dxt5', 'swizzle': 'rgba'})
            self.files['tex/%s.png' % stem] = ('copy', src_png)
        return stem

    def mesh(self, name, m):
        if not any(x['name'] == name for x in self.meshes):
            self.meshes.append({'name': name, 'file': 'mesh/%s.json' % name, 'verts': len(m['position']), 'tris': len(m['indices']) // 3})
            self.files['mesh/%s.json' % name] = ('text', json.dumps(m))

    def write(self):
        import shutil
        if self.dir.exists():
            shutil.rmtree(self.dir)
        for rel, (kind, v) in self.files.items():
            p = self.dir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if kind == 'copy':
                shutil.copyfile(v, p)
            else:
                p.write_text(v, encoding='utf-8')
        import os
        drop = [x for x in os.environ.get('XKAME_DROP', '').split(',') if x]   # debugging: drop emitters whose name starts with one of these
        if drop:
            self.emitters = [e for e in self.emitters if not any(e['name'].startswith(x) for x in drop)]
        for i, e in enumerate(self.emitters):
            e['order'] = i
        doc = {'geno_fx': 1, 'name': self.name, 'source': {'format': 'Xenoverse 2 EMP/EMO via tools/xv2_fx.py (local conversion, not committed)', 'set': self.name},
               'space': {'forward': [0, 0, 1], 'up': [0, 1, 0]}, 'textures': self.textures, 'meshes': self.meshes, 'emitters': self.emitters}
        (self.dir / (self.name + '.gfx.json')).write_text(json.dumps(doc, indent=1), encoding='utf-8')


def base_emitter():
    import copy
    e = copy.deepcopy(TEMPLATE)
    for k in ('program', 'approx'):
        e.pop(k, None)
    e['mesh'] = None
    e['wave']['apply'] = [0, 0, 0]
    # the template (an Ultimate effect's) carries a type-8 wave of 0.8 / 1.0 units that the runtime applies to the particle POSITION along the attachment's x / y axes whatever
    # 'apply' says (gw_fx.c fx_visual_update): every converted emitter wandered +-1 unit, so nothing sat where it was placed. XV2's own particle data has no such wave.
    e['wave'].update(type=0, amplitude=[0.0, 0.0], phase_random=[0.0, 0.0])
    e['extensions'] = {}
    return e


# ---------------------------------------------------------------- EMP -> emitters
def tex_sampler(pkg, ref, mat):
    """Sampler for one TextureEntryRef; the XV2 sprite-sheet keys become a divide + pattern."""
    r = ref.get('TextureRef') or {}
    idx = r.get('EmbIndex')
    stem = PTCL_TEX.get(idx)
    if stem is None:
        return None
    png = XV2 / (SK['code'] + '.ptcl.emb') / (stem + '.png')
    pkg.texture(stem, png)
    ss = r.get('ScrollState') or {}
    ks = ss.get('Keyframes') or []
    kind = (r.get('KeyframeType') or {}).get('name', 'Sequential')
    wrap = lambda n: 'Repeat' if n == 'Wrap' else ('Mirror' if n == 'Mirror' else 'Clamp')
    s = {'slot': 0, 'texture': stem, 'wrap': [wrap((r.get('RepetitionU') or {}).get('name')), wrap((r.get('RepetitionV') or {}).get('name'))],
         'filter': 'linear', 'sphere_map': False, 'uv_channel': 0,
         'pattern': {'mode': 'none', 'count': 0.0, 'frequency': 1.0, 'count_random': 0.0, 'table': [0], 'loop_random_start': False},
         'uv': {'scroll': [0.0, 0.0], 'scroll_add': [0.0, 0.0], 'scroll_random': [0.0, 0.0], 'scale': [1.0, 1.0], 'scale_add': [0.0, 0.0], 'scale_random': [0.0, 0.0],
                'rotate': 0.0, 'rotate_add': 0.0, 'rotate_random': 0.0, 'divide': [1.0, 1.0], 'enable': {'scroll': True, 'scale': True, 'rotate': False}, 'invert_random': [0, 0]}}
    if (ss.get('ScrollType') or {}).get('name') == 'SpriteSheet' and len(ks) > 1:
        su, sv = ks[0].get('ScaleU') or 1.0, ks[0].get('ScaleV') or 1.0
        s['uv']['divide'] = [float(round(1.0 / su)), float(round(1.0 / sv))]
        step = float(ks[0].get('Time') or 1)
        mode = {'Sequential': 'fit_life', 'SequentialLoop': 'loop', 'Random': 'random'}.get(kind, 'fit_life')
        s['pattern'].update(mode=mode, count=float(len(ks)), frequency=max(1.0, step if step < 50 else 1.0))
    elif (ss.get('ScrollType') or {}).get('name') in ('Speed',):
        s['uv']['scroll_add'] = [float(ss.get('ScrollSpeed_U') or 0) / FPS, float(ss.get('ScrollSpeed_V') or 0) / FPS]
    return s


def emission_to_emitter(pkg, em, parents, S, part_scale, start0, loop_end, *, rot=(0.0, 0.0, 0.0), offset=(0.0, 0.0, 0.0), depth_test=True, name=None, mul=1.0):
    """One XV2 Emission node (a particle layer) with its Emitter parent chain -> a Geno emitter dict. S = model units per XV2 metre."""
    e = base_emitter()
    mn = em['EmissionNode']
    tx = mn['Texture']
    emitter_node = next((p for p in reversed(parents) if p['IsEmitter']), None)
    e['name'] = name or em['Name']
    e['follow'] = 'srt'
    k = S * part_scale
    # --- timing
    start = start0 + em['StartTime'] + sum(p['StartTime'] for p in parents)
    life = max(1, em['Lifetime'])
    if emitter_node is not None:
        looping = 'Loop' in (emitter_node['NodeFlags']['name'] or '')
        dur = 0 if looping else max(1, emitter_node['Lifetime'])
        if loop_end:
            dur = loop_end if (looping or dur > loop_end) else dur
        burst = max(1, emitter_node['Burst'])
        freq = emitter_node['BurstFrequency']
        if freq > 0:
            rate = burst / float(freq)
            one_time = False
        else:
            rate, one_time = float(burst), True
            dur = 1
        maxi = em['MaxInstances']
        if maxi > 0:
            rate = min(rate, maxi / float(life)) if not one_time else min(rate, float(maxi))
    else:
        dur, rate, one_time = 1, 1.0, True
        if em['BurstFrequency'] > 0:
            rate, one_time, dur = em['Burst'] / float(em['BurstFrequency']), False, loop_end
    rate *= mul
    e['emission'].update(start=int(start), duration=int(dur), one_time=one_time, rate=rate, rate_random=0.0, interval=0, interval_random=0.0, position_random=0.0)
    e['particle']['life'] = life
    e['particle']['life_random_pct'] = (100.0 * em['Lifetime_Variance'] / life) if em['Lifetime_Variance'] else 0.0
    # --- frame
    pos = [0.0, 0.0, 0.0]
    node_rot = [0.0, 0.0, 0.0]
    for p in parents + [em]:
        pv = sample(p['Position'], 0.0) if kv_keys(p['Position']) else kv_const(p['Position'])   # an animated position starts at its first key
        pos = [a + b * k for a, b in zip(pos, pv[:3])]
        rv = sample(p['Rotation'], 0.0) if kv_keys(p['Rotation']) else kv_const(p['Rotation'])
        if any(abs(x) > 1e-6 for x in rv[:3]):
            node_rot = [math.radians(x) for x in rv[:3]]
    base_rot = rot_mat(*rot)
    local = rot_mat(*node_rot)
    ax_off = [0.0, 0.0, 0.0]
    shape = 'point'
    radius = [0.0, 0.0, 0.0]
    vel0 = 0.0
    spread = 0.0
    vel_var = 0.0
    if emitter_node is not None:
        en = emitter_node['EmitterNode']
        sname = (en['Shape'] or {}).get('name', 'Point')
        area = bool(en.get('EmitFromArea'))
        size = kv_const(en['Size'], 0.0)
        pos_axis = kv_const(en['Position'], 0.0)
        ax_off = [0.0, pos_axis * k, 0.0]
        if sname == 'Sphere':
            shape = 'sphere_fill' if area else 'sphere'
            radius = [size * k] * 3
        elif sname == 'Circle':
            shape = 'circle_fill' if area else 'circle'
            radius = [size * k, 0.0, size * k]
        vel0 = (sample(en['Velocity'], 0.0) if kv_keys(en['Velocity']) else kv_const(en['Velocity'], 0.0)) or 0.0
        vel_var = en.get('Velocity_Variance') or 0.0
        spread = math.radians(kv_const(en['Angle'], 0.0) or 0.0)
        # emitter-node frame (rotation of the Emitter node itself, applied before the Emission's own)
        er = kv_const(emitter_node['Rotation'])
        if any(abs(x) > 1e-6 for x in er[:3]):
            local = mm(rot_mat(*[math.radians(x) for x in er[:3]]), local)
    total = mm(base_rot, local)
    lo = mv(local, ax_off)
    off = mv(base_rot, [pos[0] + lo[0], pos[1] + lo[1], pos[2] + lo[2]])
    off = [off[0] + offset[0], off[1] + offset[1], off[2] + offset[2]]   # `offset` is already in the hand's frame
    # the runtime adds `translate` to the shape point and THEN rotates both by the emitter rotation (gw_fx.c fx_spawn/fx_erot): give it in the emitter's frame
    tT = [[total[j][i] for j in range(3)] for i in range(3)]
    off = mv(tT, off)
    e['transform']['translate'] = [round(x, 4) for x in off]
    e['transform']['rotate'] = [round(x, 5) for x in euler_of(total)]
    e['shape'].update(type=shape, radius=[round(x, 4) for x in radius])
    v = e['particle']['velocity']
    vscale = vel0 * k / FPS
    if shape.startswith('sphere'):
        v.update(all_direction=vscale, direction=[0, 1, 0], direction_scale=0.0, random_pct=100.0 * vel_var / vel0 if vel0 else 0.0, diffusion_angle=0.0, inherit=0.0)
    else:
        v.update(all_direction=0.0, direction=[0, 1, 0], direction_scale=vscale, random_pct=min(100.0, 100.0 * vel_var / vel0) if vel0 else 0.0,
                 diffusion_angle=spread if shape != 'point' or spread > 0.05 else 0.0, inherit=0.0)
    e['particle']['forces'].update(gravity=0.0, air_resistance=1.0)
    for m in em.get('Modifiers', []) + [mm_ for p in parents for mm_ in p.get('Modifiers', [])]:
        if m.get('TypeStr') == 'Drag' and m.get('KeyframedValues') and m['KeyframedValues'][0].get('Keyframes'):
            d = m['KeyframedValues'][0]['Keyframes'][0]['Value']
            e['particle']['forces']['air_resistance'] = round(max(0.5, 1.0 - d / FPS), 4)
        elif m.get('TypeStr') == 'Acceleration':
            for kvd in m['KeyframedValues']:
                if kvd.get('Parameter') == 1 and kvd.get('Component') == 0:
                    pass   # per-axis acceleration (Vortex-like drift) is not mapped: listed in the research note
    # --- shape of the quad
    nflags = (em['NodeSpecificType'] or {}).get('name', '')
    vel_or = bool(mn.get('VelocityOriented'))
    etype = (mn['EmissionType'] or {}).get('name', 'Plane')
    if etype == 'ShapeDraw':
        e['particle']['shape'] = 'plate_xz'
    elif vel_or or etype == 'ConeExtrude':   # ConeExtrude (ribbon trail) approximated by a velocity-stretched streak
        e['particle']['shape'] = 'directional_y'
    else:
        e['particle']['shape'] = 'billboard'
    # --- size over life: width = 2 * ScaleBase * ScaleXY.x, height = 2 * ScaleBase * ScaleXY.y (metres -> model units)
    sb, sxy = tx['ScaleBase'], tx['ScaleXY']
    ts = curve_times(sb, sxy)
    pts = []
    for t in ts:
        b = sample(sb, t)
        xy = sample(sxy, t)
        xy = xy if isinstance(xy, list) else [xy, xy, 1, 1]
        pts.append((2.0 * b * xy[0] * k, 2.0 * b * xy[1] * k))
    ref0 = max(pts[0][0], max(p[0] for p in pts), 1e-6), max(pts[0][1], max(p[1] for p in pts), 1e-6)
    if etype == 'ShapeDraw':
        ref0 = (ref0[0], ref0[0])
        pts = [(p[0], p[0]) for p in pts]
    e['particle']['scale']['base'] = [round(ref0[0], 4), round(ref0[1], 4), round(ref0[0], 4)]
    e['particle']['scale']['keys'] = [[round(p[0] / ref0[0], 4), round(p[1] / ref0[1], 4), round(p[0] / ref0[0], 4), t] for p, t in zip(pts, ts)]
    var = tx.get('ScaleBase_Variance') or 0.0
    sbc = sample(sb, 0.0)
    e['particle']['scale']['random_pct'] = [min(90.0, 100.0 * var / max(sbc, 1e-6))] * 2 + [0.0] if var else [0.0, 0.0, 0.0]
    # --- rotation
    sr, srv = mn.get('StartRotation') or 0.0, mn.get('StartRotation_Variance') or 0.0
    ar = kv_const(mn['ActiveRotation'], 0.0) or 0.0
    arv = mn.get('ActiveRotation_Variance') or 0.0
    r = e['particle']['rotation']
    r.update(axes=[False, False, 1], init=[0.0, 0.0, math.radians(sr)], init_random=[0.0, 0.0, math.radians(srv)], add=[0.0, 0.0, math.radians(ar)],
             add_random=[0.0, 0.0, math.radians(arv)], regist=1.0)
    if etype == 'ShapeDraw':
        r['init_random'] = [0.0, 0.0, 0.0]
    # --- colour: Color1 over life (RGB), Color1_Transparency over life (alpha); additive materials get an HDR push
    c1, a1 = tx['Color1'], tx['Color1_Transparency']
    cts = curve_times(c1)
    ats = curve_times(a1)
    mat = PTCL_MATS.get(tx['MaterialID'])
    add = bool(mat) and mat['Name'].lower().startswith('add')
    cc = e['color']
    cc['scale'] = 1.8 if add else 1.0
    cc['color0'] = {'kind': 'keys', 'value': [round(x, 4) for x in sample(c1, 0.0)[:3]], 'keys': [[*[round(x, 4) for x in sample(c1, t)[:3]], t] for t in cts]} if kv_keys(c1) else \
        {'kind': 'constant', 'value': [round(x, 4) for x in kv_const(c1)[:3]]}
    av = lambda t: float(sample(a1, t))
    if kv_keys(a1):
        cc['alpha0'] = {'kind': 'keys', 'value': av(0.0), 'keys': [[round(av(t), 4), 0.0, 0.0, t] for t in ats]}
    else:
        cc['alpha0'] = {'kind': 'constant', 'value': round(float(kv_const(a1)), 4)}
    cc['color1'] = dict(cc['color0'])
    cc['alpha1'] = dict(cc['alpha0'])
    cc['emitter'] = {'color0': [1, 1, 1, 1], 'color1': [1, 1, 1, 1]}
    # --- material
    refs = tx.get('TextureEntryRef') or []
    smp = None
    for ref in refs:
        smp = tex_sampler(pkg, ref, mat)
        if smp:
            break
    e['samplers'] = [smp] if smp else []
    mt = e['material']
    mt['blend'] = 'add' if add else 'alpha'
    mt['depth_test'] = depth_test
    mt['depth_write'] = False
    mt['bloom'] = {'threshold': 0.8, 'intensity': 1.2 if add else 0.0}
    mt['shader'].update(type='sprite', color='modulate', color_textures=[0], alpha_textures=[0], fresnel=False, alpha_test=False)
    return e


def walk(node, parents, out):
    """Collect (emission node, [ancestors]) for every Emission leaf of an EMP tree."""
    if node['IsEmission']:
        out.append((node, list(parents)))
    for c in node.get('ChildParticleNodes', []):
        walk(c, parents + [node], out)


def emp_emitters(pkg, emp_name, S, part_scale, start0=0, loop_end=0, **kw):
    out = []
    for root in load_emp(emp_name)['ParticleNodes']:
        walk(root, [], out)
    es = []
    for i, (em, parents) in enumerate(out):
        if (em['EmissionNode']['EmissionType'] or {}).get('name') == 'ShapeDraw':
            continue   # custom polygon bands (the shock rings): not convertible to a billboard plate without looking wrong; listed in the research note
        try:
            es.append(emission_to_emitter(pkg, em, parents, S, part_scale, start0, loop_end, name='%s_%s' % (emp_name.replace(SK['px'] + '_', '').lower(), em['Name']), **kw))
        except Exception as ex:   # a node the converter cannot read is reported, never silently dropped
            print('  SKIP %s/%s: %s' % (emp_name, em['Name'], ex))
    return es


# ---------------------------------------------------------------- EMO -> mesh emitters
def emo_parts(emo_name):
    return json.loads((XV2 / (emo_name + '.emo.json')).read_text(encoding='utf-8'))


def emb_png(emb_dir, idx):
    ix = json.loads((XV2 / emb_dir / 'index.json').read_text(encoding='utf-8'))
    return XV2 / emb_dir / (Path(ix[idx]['name']).stem + '.png')


def ema_bones(name):
    """obj.ema -> {bone: {(param, comp): [(frame, value)]}} (the pose animation of the effect's bones)."""
    d = json.loads((XV2 / (name + '.obj.ema.json')).read_text(encoding='utf-8'))
    out = {}
    for a in d.get('Animations', []):
        for n in a['Nodes']:
            for c in n['Commands']:
                out.setdefault(n['BoneName'], {})[(c['ParameterXmlBinding'], c['ComponentXmlBinding'])] = [(k['Time'], k['Value']) for k in c['Keyframes']]
    return out


def ema_mean(bone, param, comp, dflt, t0=10, t1=59):
    """Mean of a bone channel over the sustained part of the loop (frames t0..t1)."""
    ks = (bone or {}).get((param, comp))
    if not ks:
        return dflt
    v = [x for t, x in ks if t0 <= t <= t1] or [ks[-1][1]]
    return sum(v) / len(v)


def bone_matrix(bone, dflt_scale=1.0):
    """(scale xyz, rotation X degrees, position xyz) of an EMA bone at its sustained pose."""
    sc = [ema_mean(bone, 'Scale', c, dflt_scale) for c in 'XYZ']
    rx = ema_mean(bone, 'Rotation', 'X', 0.0)
    ps = [ema_mean(bone, 'Position', c, 0.0) for c in 'XYZ']
    return sc, rx, ps


def emo_meshes(pkg, emo_name, emm_json, part_scale):
    """Per EMO part: (name, mesh dict in XV2 metres in the beam frame, material row, sampler def).
    The part's bone pose from obj.ema (scale, rotation about X, position) and the TRS bone are baked into the vertices, then the XV2 projectile frame
    (forward -Z) is turned 180 degrees about Y so the beam runs along +Z with the dome at the front and the tube trailing behind it."""
    d = emo_parts(emo_name)
    mats = emm(emm_json)
    by_name = {m['Name']: m for m in mats.values()}
    bones = ema_bones(emo_name)
    trs_sc, trs_rx, _ = bone_matrix(bones.get('TRS'))
    res = []
    for part in d['parts']:
        for f in part['emgFiles']:
            for me in f['meshes']:
                v = me['vertices']
                grp = me['submeshGroups'][0]
                mat = by_name.get(grp['materialName'])
                sc, rx, ps = bone_matrix(bones.get(part['name']))
                Rb, Rt = rot_mat(math.radians(rx), 0, 0), rot_mat(math.radians(trs_rx), 0, 0)
                Ry = rot_mat(0.0, math.pi, 0.0)
                pos, nor, uv = [], [], []
                for p, n, t in zip(v['position'], v['normal'], v['uv']):
                    q = mv(Rb, [p[0] * sc[0], p[1] * sc[1], p[2] * sc[2]])
                    q = [q[0] + ps[0], q[1] + ps[1], q[2] + ps[2]]
                    q = mv(Ry, mv(Rt, [q[0] * trs_sc[0], q[1] * trs_sc[1], q[2] * trs_sc[2]]))
                    q = [x * part_scale for x in q]
                    nn = mv(Ry, mv(Rt, mv(Rb, n)))
                    pos.append([round(x, 5) for x in q])
                    nor.append([round(x, 4) for x in nn])
                    uv.append([round(t[0], 5), round(t[1], 5)])
                idx = []
                for sm in grp['submeshes']:
                    for a, b, c in sm['triangles']:
                        idx += [a, c, b]
                m = {'name': '%s_%s' % (emo_name, part['name']), 'position': pos, 'normal': nor, 'uv0': uv, 'color0': None, 'indices': idx}
                res.append((part['name'], m, mat, grp['textureSamplerDefs'][0]))
    return res


def ribbon_mesh(name='ribbon_x'):
    """Two crossing quads along +Z (z 0..1, half width 1): the XV2 trail ribbons are camera-oriented; a cross reads from the side camera and from above."""
    pos, nor, uv, idx = [], [], [], []
    for dx, dy in ((1.0, 0.0), (0.0, 1.0)):
        b = len(pos)
        for z in (0.0, 1.0):
            for sgn in (-1.0, 1.0):
                pos.append([dx * sgn, dy * sgn, z])
                nor.append([-dy, dx, 0.0])
                uv.append([0.5 + 0.5 * sgn, z])
        idx += [b, b + 1, b + 2, b + 1, b + 3, b + 2, b, b + 2, b + 1, b + 1, b + 2, b + 3]
    return {'name': name, 'position': pos, 'normal': nor, 'uv0': uv, 'color0': None, 'indices': idx}


def mesh_emitter(pkg, name, m, samp, emb_dir, *, life, base, keys, tint, alpha, blend, scale, rotate, translate, start=0, bloom=1.0, scroll=(0.0, 0.0), stem=None,
                 uv_scale=None):
    pkg.mesh(m['name'], m)
    png = emb_png(emb_dir, samp['EmbIndex'])
    stem = stem or '%s_%d' % (emb_dir.split('.')[0], samp['EmbIndex'])
    pkg.texture(stem, png)
    e = base_emitter()
    e.update(name=name, kind='mesh', mesh=m['name'], follow='srt')
    e['transform'].update(translate=[round(x, 4) for x in translate], rotate=[round(x, 5) for x in rotate])
    e['emission'].update(start=start, duration=1, one_time=True, rate=1.0, rate_random=0.0, interval=0, interval_random=0.0, position_random=0.0)
    e['shape'].update(type='point', radius=[0.0, 0.0, 0.0])
    p = e['particle']
    p.update(life=life, life_random_pct=0, shape='billboard')
    p['velocity'].update(all_direction=0.0, direction_scale=0.0, random_pct=0.0, inherit=0.0, diffusion_angle=0.0)
    p['forces'].update(gravity=0.0, air_resistance=1.0)
    p['scale']['base'] = [round(x, 4) for x in base]
    p['scale']['random_pct'] = [0.0, 0.0, 0.0]
    p['scale']['keys'] = keys
    p['rotation'].update(init=[0, 0, 0], init_random=[0, 0, 0], add=[0, 0, 0])
    c = e['color']
    c['scale'] = scale
    c['color0'] = {'kind': 'constant', 'value': [round(x, 4) for x in tint]}
    c['color1'] = dict(c['color0'])
    c['alpha0'] = {'kind': 'constant', 'value': alpha}
    c['alpha1'] = dict(c['alpha0'])
    c['emitter'] = {'color0': [1, 1, 1, 1], 'color1': [1, 1, 1, 1]}
    wrap = lambda n: 'Repeat' if n == 'Wrap' else ('Mirror' if n == 'Mirror' else 'Clamp')
    us = uv_scale or [float(samp.get('ScaleU') or 1), float(samp.get('ScaleV') or 1)]
    e['samplers'] = [{'slot': 0, 'texture': stem, 'wrap': [wrap(samp['AddressModeU']['name']), wrap(samp['AddressModeV']['name'])], 'filter': 'linear', 'sphere_map': False,
                      'uv_channel': 0, 'pattern': {'mode': 'none', 'count': 0.0, 'frequency': 1.0, 'count_random': 0.0, 'table': [0], 'loop_random_start': False},
                      'uv': {'scroll': [0.0, 0.0], 'scroll_add': [scroll[0] / FPS, scroll[1] / FPS], 'scroll_random': [0.0, 0.0], 'scale': us,
                             'scale_add': [0.0, 0.0], 'scale_random': [0.0, 0.0], 'rotate': 0.0, 'rotate_add': 0.0, 'rotate_random': 0.0, 'divide': [1.0, 1.0],
                             'enable': {'scroll': True, 'scale': True, 'rotate': False}, 'invert_random': [0, 0]}}]
    mt = e['material']
    mt.update(blend=blend, depth_test=True, depth_write=False)
    mt['bloom'] = {'threshold': 0.7, 'intensity': bloom}
    mt['shader'].update(type='sprite', color='modulate', color_textures=[0], alpha_textures=[0], fresnel=False, alpha_test=False)
    mt['display_side'] = 0
    return e


def grow_keys(life, ramp, tail_frames=6, r=1.0, z0=0.04):
    c = max(1, life - tail_frames)
    return [[r, r, z0, 0.0], [r, r, 1.0, ramp / life], [r * 1.04, r * 1.04, 1.0, 0.5], [r, r, 1.0, c / life], [0.25 * r, 0.25 * r, 1.0, 1.0]]


def pop_keys(life, ramp, tail_frames=6):
    """Uniform grow-in over `ramp` frames, hold, shrink away in the last frames (head pieces: a sphere/dome must not stretch)."""
    return [[0.05, 0.05, 0.05, 0.0], [1, 1, 1, ramp / life], [1.04, 1.04, 1.04, 0.5], [1, 1, 1, max(1, life - tail_frames) / life], [0.25, 0.25, 0.25, 1.0]]


# ---------------------------------------------------------------- engine FX features (ribbon span + width curve, rings, dissolve, glare, soft particles)
GLARE = ((0.55, 0.8, 1.0), 2.5)        # bloom tint / radius of every additive emitter with bloom (R1)
SOFT = {'distance': 1.5, 'volume': 1}   # soft particles on alpha-blended billboards (R3)
EMIT_FADE = {'on_stop': True, 'alpha_frames': 0, 'fade_in_frames': 0, 'alpha_fade_in': False, 'scale_fade_in': False}
TAIL_FRAMES = 22      # XV2 ribbon width/alpha are curves over segment AGE (frames); the beam maps age = (1 - position) x this, the head being the newest segment
HAND_FLOOR = 0.42     # ...but the beam must start AT the hands: the width never falls below this fraction of the head's (XV2's own tail fades to a point; approximation)


def synth_png(name, w, h, px):
    """A small generated mask/ring texture (not XV2 data): px(x, y) -> (r, g, b, a) 0..255. Written once under _build/xv2-kame/fx/synth."""
    from PIL import Image
    p = WT / '_build/xv2-kame/fx/synth' / (name + '.png')
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        im = Image.new('RGBA', (w, h))
        im.putdata([tuple(px(x, y)) for y in range(h) for x in range(w)])
        im.save(p)
    return p


def ring_png():
    def px(x, y):   # u around the band, v inner -> outer: a soft peak with faint ticks
        u, v = x / 128.0, y / 128.0
        a = math.exp(-((v - 0.55) * 4.2) ** 2) * (0.85 + 0.15 * math.sin(u * 6.2832 * 24))
        return (255, 255, 255, int(max(0.0, min(1.0, a)) * 255))
    return synth_png('rx_ring', 128, 128, px)


def noise_png():
    import random
    rnd = random.Random(7)
    g = [[rnd.random() for _ in range(8)] for _ in range(8)]

    def px(x, y):   # tileable value noise (dissolve mask, red channel)
        fx, fy = x / 128.0 * 8, y / 128.0 * 8
        x0, y0 = int(fx) % 8, int(fy) % 8
        x1, y1 = (x0 + 1) % 8, (y0 + 1) % 8
        tx, ty = fx - int(fx), fy - int(fy)
        sx, sy = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        n = (g[y0][x0] * (1 - sx) + g[y0][x1] * sx) * (1 - sy) + (g[y1][x0] * (1 - sx) + g[y1][x1] * sx) * sy
        return (int(n * 255), int(n * 255), int(n * 255), 255)
    return synth_png('rx_noise', 128, 128, px)


def fx_sampler(slot, tex, scroll_add=(0.0, 0.0), wrap='Repeat', rotate=0.0):
    return {'slot': slot, 'texture': tex, 'wrap': [wrap, wrap], 'filter': 'linear', 'sphere_map': False, 'uv_channel': 0,
            'pattern': {'mode': 'none', 'count': 0.0, 'frequency': 1.0, 'count_random': 0.0, 'table': [0], 'loop_random_start': False},
            'uv': {'scroll': [0.0, 0.0], 'scroll_add': list(scroll_add), 'scroll_random': [0.0, 0.0], 'scale': [1.0, 1.0], 'scale_add': [0.0, 0.0],
                   'scale_random': [0.0, 0.0], 'divide': [1, 1], 'rotate': rotate, 'rotate_add': 0.0, 'rotate_random': 0.0,
                   'enable': {'scroll': 1, 'scale': 1, 'rotate': 1}}}


def fx_particle(name, life, size, rgb, hdr, rot, translate, emission, samplers, *, alpha_keys, scale_keys=None, param=None, shader=None, bloom=None,
                ribbon=None, ring=None, blend='add'):
    """One engine-feature emitter built on the template: a ribbon strip (beam layer) or a ring band. size = particle size (the strip's width / ring diameter)."""
    e = base_emitter()
    e.update(name=name, kind='particle', follow='srt')
    e['transform'] = {'translate': list(translate), 'translate_random': [0.0, 0.0, 0.0], 'rotate': list(rot), 'rotate_random': [0.0, 0.0, 0.0], 'scale': [1.0, 1.0, 1.0]}
    em = {'start': 0, 'duration': 1, 'one_time': True, 'rate': 1.0, 'rate_random': 0.0, 'interval': 0, 'interval_random': 0.0, 'position_random': 0.0,
          'by_distance': False, 'fade': dict(EMIT_FADE)}
    em.update(emission)
    e['emission'] = em
    p = e['particle']
    p.update(life=life, life_random_pct=0, shape='billboard')
    p['velocity'] = {'all_direction': 0.0, 'direction': [0, 1, 0], 'direction_scale': 0.0, 'diffusion_angle': 0.0, 'xz_diffusion': 0.0, 'diffusion': [0.0, 0.0, 0.0],
                     'random_pct': 0.0, 'inherit': 0.0, 'momentum_random': 0.0}
    p['forces'].update(gravity=0.0, air_resistance=1.0)
    p['rotation'] = {'axes': [False, False, 1], 'init': [0, 0, 0], 'init_random': [0, 0, 0], 'add': [0, 0, 0], 'add_random': [0, 0, 0], 'regist': 1.0,
                     'reverse_random': [False, False, False]}
    p['scale'] = {'base': [size] * 3, 'random_pct': [0.0, 0.0, 0.0], 'keys': scale_keys or [[1, 1, 1, 0.0], [1, 1, 1, 1.0]], 'loop': False, 'loop_rate': 1,
                  'add_velocity': 0.0, 'limit_distance': [200.0, 200.0]}
    p['param_keys'] = param or [[0.0, 0.0, 0.0, 0.0]]
    c = e['color']
    c['scale'] = hdr
    c['color0'] = {'kind': 'constant', 'value': list(rgb)}
    c['color1'] = {'kind': 'constant', 'value': list(rgb)}
    c['alpha0'] = {'kind': 'keys', 'value': alpha_keys[0][0], 'keys': alpha_keys}
    c['alpha1'] = {'kind': 'constant', 'value': 1.0}
    e['samplers'] = samplers
    m = e['material']
    m.update(blend=blend, depth_test=True, depth_write=False)
    m['shader'] = shader or {'type': 'sprite', 'color': 'modulate'}
    m['bloom'] = bloom or {'threshold': 0.5, 'intensity': 1.0, 'tint': list(GLARE[0]), 'radius': GLARE[1]}
    m.pop('alpha_test', None)
    if ribbon:
        e['ribbon'] = ribbon
    if ring:
        e['ring'] = ring
    return e


def xv2_age_curves(skill, set_idx):
    """{texture stem: [(age frames, width m)]} of the skill's ETR ribbon set number set_idx (3 ribbons a set; the refraction ribbon is skipped)."""
    from xv2_lane_params import params
    rib = [r for r in params(skill)['ribbons'] if r['shader'] != 'T1_VFX_TRC_RI' and r['material'] != 'Ref']
    sets = [rib[i:i + 3] for i in range(0, len(rib), 3)]
    sets = [x for x in sets if x]
    out = {}
    for r in sets[min(set_idx, len(sets) - 1)]:
        w = r['width_m']
        out[Path(r['texture']).stem] = [(k[0], k[1]) for k in w['keys']] or [(0, w['const']), (TAIL_FRAMES, w['const'])]
    return out


def width_keys(age_keys, floor=HAND_FLOOR, tail=TAIL_FRAMES):
    """XV2 width over segment age -> the engine's width multiplier over the strip position (0 = hand/origin, 1 = head): age = (1 - t) x tail, normalised to the
    head's width, never below `floor` (the beam stays attached to the hands)."""
    ks = sorted(age_keys)

    def w(a):
        if a <= ks[0][0]:
            return ks[0][1]
        for (a0, v0), (a1, v1) in zip(ks, ks[1:]):
            if a <= a1:
                return v0 + (v1 - v0) * (a - a0) / (a1 - a0)
        return ks[-1][1]
    w0 = max(w(0.0), 1e-6)
    ts = (0.0, 0.3, 0.5, 0.65, 0.78, 0.88, 0.95, 1.0)
    return [[t, round(floor + (1.0 - floor) * max(0.0, min(1.0, w((1.0 - t) * tail) / w0)), 4)] for t in ts]


def ring_emitter(pkg, name, size, rgb, hdr, rot, translate, emission, *, life=18, sc=(0.25, 1.7), dissolve=True, contract=False):
    """A ring band (engine ring mesh; XV2's Kmh_Ring is a custom polygon band, ShapeDraw, which has no converter: approximated). contract = gathers instead of leaving."""
    pkg.texture('rx_ring', ring_png())
    pkg.texture('rx_noise', noise_png())
    shader = {'type': 'dissolve', 'mask': 1, 'edge': 0.25, 'edge_color': [0.7, 0.95, 1.0]} if dissolve else None
    sm = [fx_sampler(0, 'rx_ring')] + ([fx_sampler(1, 'rx_noise', (0.015, -0.02))] if dissolve else [])
    a, b = (sc[1], sc[0]) if contract else (sc[0], sc[1])
    return fx_particle(name, life, size, rgb, hdr, rot, translate, emission, sm,
                       scale_keys=[[a, a, a, 0.0], [(a + b) / 2, (a + b) / 2, (a + b) / 2, 0.45], [b, b, b, 1.0]],
                       alpha_keys=[[0.0, 0, 0, 0.0], [1.0, 0, 0, 0.15], [0.8, 0, 0, 0.6], [0.0, 0, 0, 1.0]], shader=shader,
                       param=[[0.05, 0, 0, 0.0], [0.9, 0, 0, 1.0]], ring={'inner': 0.62, 'segments': 56})


def finish_package(pkg):
    """Glare tint / radius on every additive emitter with bloom (R1) and soft depth fade on alpha-blended billboards (R3), set once at the end."""
    for e in pkg.emitters:
        m = e.setdefault('material', {})
        b = m.get('bloom') or {}
        if m.get('blend') == 'add' and b.get('intensity', 0) > 0:
            b.setdefault('tint', list(GLARE[0]))
            b.setdefault('radius', GLARE[1])
            if e['kind'] == 'mesh':
                b['threshold'] = min(b.get('threshold', 0.7), 0.35)
                b['intensity'] = max(b['intensity'], 0.9)
            m['bloom'] = b
        elif m.get('blend') != 'add' and e['kind'] == 'particle' and e['particle'].get('shape') == 'billboard' and 'soft_particle' not in m:
            m['soft_particle'] = dict(SOFT)


# ---------------------------------------------------------------- the packages
def part_style(name, mat):
    """tint / blend / scroll of one EMO part from its XV2 material row (T1_VFX_MTN_DIS_ALPHA: MatCol, AlphaBlendType, TexScrl)."""
    add = bool(mat) and mat_param(mat, 'AlphaBlendType', 0) == 1
    col = lambda i: [mat_param(mat, 'MatCol%d%s' % (i, c), 1.0) for c in 'RGB']
    tint = col(1) if name.lower() in ('cor', 'acor') else col(2)
    if max(tint) < 0.05:   # a parallax shader's secondary colour can be black: fall back to the base colour
        tint = col(0)
    scroll = (mat_param(mat, 'TexScrl0U', 0.0), mat_param(mat, 'TexScrl0V', 0.0)) if mat else (0.0, 0.0)
    return tint, add, scroll


def etr_ribbons():
    """The ETR trail ribbons of the skill's beam: [(texture stem, texture index in trc.emb, half width m, scroll V per second, blend, alpha, tint)].
    The refraction ('Ref') ribbon is skipped; each blend comes from the trail material's AlphaBlendType."""
    etr = next((XV2 / (SK['code'] + '.tbind.emb')).glob('*Beam.etr.json'))
    d = json.loads(etr.read_text(encoding='utf-8'))
    mats = emm(EXPORT / (SK['code'] + '.trc.emm.json'))
    ix = json.loads((XV2 / (SK['code'] + '.trc.emb/index.json')).read_text(encoding='utf-8'))
    out = []
    for n in d['Nodes']:
        m = mats.get(n['MaterialID'])
        if m is None or m['ShaderProgram'] == 'T1_VFX_TRC_RI':   # the refraction ribbon ('Ref') has no billboard equivalent
            continue
        t = n['TextureEntryRef'][0]['TextureRef']
        c1 = kv_const(n['Color1'])
        stem = Path(ix[t['EmbIndex']]['name']).stem
        add = mat_param(m, 'AlphaBlendType', 0) == 1
        out.append((stem, t['EmbIndex'], float(kv_const(n['Scale'])), float(t['ScrollState']['ScrollSpeed_V'] or 0) * FPS,
                    'add' if add else 'alpha', 0.9, tuple(c1[:3])))
    return out


LOOK = {   # per-tier look: name -> head size S (model units per XV2 metre), beam length L, life, ramp (frames), XV2 ribbon set, layers, tint, glow, rings, muzzle package
    # S, L, life, ramp follow tools/gen_kame.py (the gameplay: hit spheres are the same hand anchor and direction); widths scale with S
    'Tap':   dict(S=2.0, L=18, life=12, ramp=3, set=0, layers=('core',), glow=(0.25, 0.55, 1.0), core=(0.8, 0.95, 1.0), hdr=1.3, rings=(), fire=None),
    'Thin':  dict(S=2.6, L=24, life=24, ramp=3, set=0, layers=('glow', 'core'), glow=(0.2, 0.5, 1.0), core=(0.85, 0.96, 1.0), hdr=1.5, rings=(), fire=None),
    'Mid':   dict(S=3.5, L=28, life=34, ramp=4, set=0, layers=('glow', 'streaks', 'core'), glow=(0.12, 0.45, 1.0), core=(0.9, 0.97, 1.0), hdr=1.6, rings=((14, 1.0),), fire='Muzzle'),
    'Full':  dict(S=4.6, L=36, life=46, ramp=5, set=1, layers=('glow', 'streaks', 'cloud', 'core'), glow=(0.1, 0.55, 1.0), core=(0.92, 0.98, 1.0), hdr=1.8,
                  rings=((10, 1.0), (14, 1.35)), fire='Muzzle'),
    'Max':   dict(S=5.8, L=48, life=62, ramp=6, set=2, layers=('glow', 'streaks', 'cloud', 'core'), glow=(0.3, 0.65, 1.0), core=(1.0, 1.0, 1.0), hdr=2.3,
                  rings=((7, 1.0), (9, 1.4), (12, 1.9)), fire='MuzzleMax'),
}
# a layer: (xv2 texture stem, relative width, tint source, hdr factor, alpha, rotate texture 90 degrees, scroll per frame (u along, v across), uv tiles per unit, ends, bloom intensity)
LAYERS = {
    'glow':    ('beam00',       2.6, 'glow', 1.0, 0.9, True,  (0.0, -0.02), 0.06, (0.02, 0.10), 1.0),
    'streaks': ('ring_beamCor', 1.9, 'glow', 1.1, 0.8, True,  (0.0, 0.10),  0.07, (0.02, 0.08), 0.6),
    'cloud':   ('T2_UV01',      1.5, 'glow', 1.0, 0.7, False, (0.04, 0.02), 0.05, (0.02, 0.08), 0.5),
    'core':    ('beam00',       0.6, 'core', 1.2, 1.0, True,  (0.0, -0.05), 0.09, (0.0, 0.05), 0.8),
}


def beam_layers(pkg, skill_key, look, rot, S, L, life, ramp, *, width=1.0):
    """The beam body as camera-facing ribbon-span emitters on the SAME anchor as the hit spheres (the hand joint, emitter rotation RISE, so +Z is the beam direction
    D): each runs from the hand (strip position 0) to the head (1). XV2's widths over segment age become a width curve over position (wide at the head, tapering
    toward the hand, never below HAND_FLOOR), the scroll speeds are XV2's, the ends ease in/out, alpha fades in and out over the life."""
    use = skill_key
    curves = xv2_age_curves(use, look['set'])
    trc = SK['code'] + '.trc.emb'
    ix = json.loads((XV2 / trc / 'index.json').read_text(encoding='utf-8'))
    idx = {Path(x['name']).stem: i for i, x in enumerate(ix)}
    grow = [[0.0, 0, 0, 0.0], [1.0, 0, 0, ramp / life], [1.0, 0, 0, 1.0]]
    fade = [[0.0, 0, 0, 0.0], [1.0, 0, 0, 0.06], [1.0, 0, 0, 0.82], [0.0, 0, 0, 1.0]]
    order = [n for n in ('glow', 'streaks', 'cloud', 'core') if n in look['layers']]
    for n in order:
        stem, k, tsrc, hf, al, r90, scroll, upu, ends, bi = LAYERS[n]
        pkg.texture('trc_' + stem, emb_png(trc, idx[stem]))
        wk = width_keys(curves.get(stem) or curves.get('beam00') or [(0, 1), (TAIL_FRAMES, 1)])
        fa = [[a[0] * al, 0, 0, a[3]] for a in fade]
        sm = [fx_sampler(0, 'trc_' + stem, scroll, rotate=math.pi / 2 if r90 else 0.0)]
        pkg.emitters.append(fx_particle(
            'ribbon_' + n, life, k * S * width, look[tsrc], look['hdr'] * hf, rot, (0.0, 0.0, 0.0), {}, sm, alpha_keys=fa, param=grow,
            bloom={'threshold': 0.5, 'intensity': bi, 'tint': list(look[tsrc]) if n == 'core' else list(GLARE[0]), 'radius': GLARE[1]},
            ribbon={'taper': 1.0, 'uv_per_unit': upu, 'span': {'length': L, 'segments': 32, 'width': wk}, 'ends': list(ends)}))


def beam_package(name, S, L, life, ramp, *, bas_scale, hand_scale, particles, look, skill_key='KMH', rings_rgb=(0.45, 0.8, 1.0)):
    """XV2's beam: the head (<px>_Bas.emo dome + shells and <px>_Hand.emo ball, baked with their obj.ema poses) at the beam's end, the body as ribbon layers
    (beam_layers) from the hand to the head, shock rings leaving the head, and the head particles. S = model units per XV2 metre; L = beam length (model units)."""
    px = SK['px']
    pkg = Pkg(name)
    rot = list(RISE)
    beam_layers(pkg, skill_key, look, rot, S, L, life, ramp)
    for pname, m, mat, samp in emo_meshes(pkg, px + '_Bas', EXPORT / (px + '_Bas.emm.json'), bas_scale):
        tint, add, scroll = part_style(pname, mat)
        a0 = mat_param(mat, 'MatCol0A', 1.0) if mat else 1.0
        pkg.emitters.append(mesh_emitter(pkg, 'bas_' + pname, m, samp, px + '_Bas.emb', life=life, base=(S, S, S), keys=pop_keys(life, ramp), tint=tint,
                                         alpha=(1.0 if (add or pname.lower() == 'acor') else 0.55) * a0, blend='add' if add else 'alpha', scale=1.0, bloom=0.5,
                                         rotate=rot, translate=(0, 0, L), scroll=scroll))
    for pname, m, mat, samp in emo_meshes(pkg, px + '_Hand', EXPORT / (px + '_Hand.emm.json'), hand_scale):
        tint, add, scroll = part_style(pname, mat)
        pkg.emitters.append(mesh_emitter(pkg, 'hand_' + pname, m, samp, px + '_Hand.emb', life=life, base=(S, S, S), keys=pop_keys(life, ramp), tint=tint,
                                         alpha=0.8 if add else 0.6, blend='add' if add else 'alpha', scale=1.2, bloom=0.6, rotate=rot, translate=(0, 0, L), scroll=scroll))
    head = along(L)
    for emp, sc in particles:
        pkg.emitters.extend(emp_emitters(pkg, px + '_' + emp, S, sc, start0=0, loop_end=life, rot=EMP_ROT, offset=head))
    for i, (every, mul) in enumerate(look['rings']):
        pkg.emitters.append(ring_emitter(pkg, 'rx_ring_head%d' % i, 2.4 * S * mul, rings_rgb, 3.0, rot, (0.0, 0.0, L),
                                         {'start': 4 + 2 * i, 'duration': life, 'one_time': False, 'interval': every}))
    finish_package(pkg)
    return pkg


# the chant beats (game frames of the charge state, lua/goku.lua CHARGE: "ka" 1 s, "me" 3 s, "ha" 6 s, the last "me" 9 s, max 10 s) and the ball size at each
BALL_OFF = (0.0, 0.0, 0.0)   # the charge effects sit at the MIDPOINT of the hands (the binding's joint2, build.py FX_STATES): no offset of their own
CHANT_AT = (60, 180, 360, 540)
BALL = ((0, 0.25), (30, 0.30), (60, 0.45), (120, 0.52), (180, 0.65), (270, 0.75), (360, 0.85), (450, 0.95), (540, 1.1), (590, 1.25))   # (frame, size): grows between the beats, steps at them


def charge_package(name, S=11.4, crg_scale=1.0, motes=True, chant=CHANT_AT, ball=BALL, rate=1.0, ring_rate=None):
    """Effect 0 of the EEPK: <px>_Crg (the ball's sprite stack), <px>_CrgON (a flash) and Kmh_tsubu (motes), stepped with the chant: the stack grows continuously
    and jumps at each syllable beat, a flash fires on each beat (bigger every time), a gathering ring contracts into the ball faster at each tier, and the
    motes are soft particles. `rate` stretches the time axis (the Super's chant is compressed)."""
    px = SK['px']
    pkg = Pkg(name)
    steps = [(int(f * rate), sc) for f, sc in ball]
    for i, (st, sc) in enumerate(steps):
        nxt = steps[i + 1][0] if i + 1 < len(steps) else 0
        es = emp_emitters(pkg, px + '_Crg', S, sc * crg_scale, start0=st, loop_end=(nxt - st) if nxt else 0, depth_test=False, offset=BALL_OFF)
        for e in es:
            e['name'] = '%s_s%d' % (e['name'], i)
        pkg.emitters.extend(es)
    if (XV2 / (SK['code'] + '.pbind.emb') / (px + '_CrgON.emp.json')).exists():
        for i, (st, sc) in enumerate(zip(chant, (0.6, 0.85, 1.15, 1.6))):
            es = emp_emitters(pkg, px + '_CrgON', S, sc * crg_scale, start0=int(st * rate), loop_end=0, depth_test=False, offset=BALL_OFF)
            for e in es:
                e['name'] = '%s_f%d' % (e['name'], i)
            pkg.emitters.extend(es)
    if motes and (XV2 / (SK['code'] + '.pbind.emb') / (px + '_tsubu.emp.json')).exists():
        pkg.emitters.extend(emp_emitters(pkg, px + '_tsubu', S, 1.0, start0=0, loop_end=0, depth_test=False, offset=BALL_OFF))
    # gathering rings: five phases, each starting at a beat and repeating faster, a little bigger
    rr = rate if ring_rate is None else ring_rate
    phases = [(int(a * rr), max(int(b * rr), int(a * rr) + 2), max(3, int(iv * rr / rate)) if ring_rate else iv, sz) for a, b, iv, sz in ((20, 60, 40, 7.0), (60, 180, 30, 8.0), (180, 360, 22, 9.5), (360, 540, 15, 11.0), (540, 700, 9, 13.0))]
    for i, (a, b, iv, sz) in enumerate(phases):
        pkg.emitters.append(ring_emitter(pkg, 'rx_ring_gather%d' % i, sz * crg_scale, (0.45, 0.8, 1.0), 3.0, [0.0, 0.0, 0.0], BALL_OFF,
                                         {'start': a, 'duration': 0 if i == len(phases) - 1 else b - a, 'one_time': False, 'interval': iv}, life=14, sc=(0.2, 1.7), contract=True))   # the last phase never ends: the Max hold
    finish_package(pkg)
    return pkg


def pressure_package(name, rate=1.0):
    """Ground pressure: flat rings spreading from the feet at each beat, bigger every time (bound to the floor joint)."""
    pkg = Pkg(name)
    flat = [math.pi / 2, 0.0, 0.0]
    for i, (st, sz, iv) in enumerate(((CHANT_AT[0], 14.0, 0), (CHANT_AT[1], 20.0, 0), (CHANT_AT[2], 28.0, 0), (CHANT_AT[3], 40.0, 0))):
        pkg.emitters.append(ring_emitter(pkg, 'rx_pressure%d' % i, sz, (0.55, 0.8, 1.0), 2.2, flat, (0.0, 0.5, 0.0),
                                         {'start': int(st * rate), 'duration': 1, 'one_time': True}, life=26, sc=(0.3, 1.5), dissolve=True))
    # a faint continuous pulse underneath, quickening
    for i, (a, b, iv, sz) in enumerate(((20, 180, 34, 12.0), (180, 360, 24, 16.0), (360, 700, 14, 22.0))):
        pkg.emitters.append(ring_emitter(pkg, 'rx_pulse%d' % i, sz, (0.4, 0.7, 1.0), 1.4, flat, (0.0, 0.5, 0.0),
                                         {'start': int(a * rate), 'duration': 0 if i == 2 else int((b - a) * rate), 'one_time': False, 'interval': iv}, life=22, sc=(0.3, 1.2), dissolve=False))   # the last pulse never ends (the Max hold)
    finish_package(pkg)
    return pkg


def store_package(name, tier, S=11.4):
    """The stored-charge flash for the 9 frames of a KameStore<tier> state (the natives' Cancel states last 8: traced): the ball stack, a CrgON flash and a ring at the
    tier's chant size (x0.45 / 0.65 / 0.85 / 1.1) so the player reads the stored tier."""
    pkg = Pkg(name)
    px = SK['px']
    sc = (0.45, 0.65, 0.85, 1.1)[tier - 1]
    pkg.emitters.extend(emp_emitters(pkg, px + '_Crg', S, sc, start0=0, loop_end=9, depth_test=False, offset=BALL_OFF))
    pkg.emitters.extend(emp_emitters(pkg, px + '_CrgON', S, sc * 1.5, start0=0, loop_end=0, depth_test=False, offset=BALL_OFF))
    for i in range(tier):
        pkg.emitters.append(ring_emitter(pkg, 'rx_store%d' % i, (7.0 + 3.0 * tier) * (1 + 0.35 * i), (0.5, 0.82, 1.0), 3.0, [0.0, 0.0, 0.0], BALL_OFF,
                                         {'start': 2 * i, 'duration': 1, 'one_time': True}, life=14, sc=(0.3, 1.8)))
    finish_package(pkg)
    return pkg


def muzzle_package(name, S, fire_scale=1.0, alpha=0.5, life=9, rings=1):
    """The flare at release: kept SHORT and subtle (the owner saw a pale haze): a dome of `alpha` for `life` frames and `rings` shock rings along the beam."""
    px = SK['px']
    pkg = Pkg(name)
    rot = list(RISE)
    for pname, m, mat, samp in emo_meshes(pkg, px + '_Fire', EXPORT / (px + '_Fire.emm.json'), fire_scale):
        tint, add, scroll = part_style(pname, mat)
        pkg.emitters.append(mesh_emitter(pkg, 'fire_' + pname, m, samp, px + '_Fire.emb', life=life, base=(S, S, S),
                                         keys=[[0.2, 0.2, 0.2, 0.0], [1.0, 1.0, 1.0, 0.35], [1.1, 1.1, 1.1, 1.0]], tint=tint, alpha=alpha, blend='add', scale=1.6,
                                         rotate=rot, translate=(0, 0, 2.0), scroll=scroll))
    for i in range(rings):
        pkg.emitters.append(ring_emitter(pkg, 'rx_muzzle%d' % i, (1.1 + 0.5 * i) * S * 1.6, (0.7, 0.9, 1.0), 2.6, rot, (0.0, 0.0, 2.0 + 3 * i),
                                         {'start': 2 * i, 'duration': 1, 'one_time': True}, life=14, sc=(0.2, 1.8)))
    finish_package(pkg)
    return pkg


KMH_PARTICLES = (('Fireptcl', 1.6), ('4ptcl', 1.6), ('LineAll', 1.6), ('Wav', 1.8))
CKM_PARTICLES = (('Tail', 2.0), ('Wav', 2.0), ('Last', 1.0), ('FireLine', 2.8), ('4ptcl', 1.5), ('LineAll', 3.0))
SUPER_LOOK = dict(S=3.2, L=52, life=64, ramp=6, set=0, layers=('glow', 'streaks', 'cloud', 'core'), glow=(0.35, 0.65, 1.0), core=(1.0, 1.0, 1.0), hdr=2.4,
                  rings=((7, 1.0), (9, 1.5), (12, 2.0)), fire='MuzzleSuper')


def probe_package(name, translate):
    """Measurement only (xv2_fx.py --probe): ONE tiny additive point at `translate` in the attachment frame, re-spawned every frame, so gd.fx() bbox = where that point is."""
    pkg = Pkg(name)
    pkg.texture('rx_ring', ring_png())
    pkg.emitters.append(fx_particle('probe', 2, 0.3, (1, 0, 0), 1.0, [0.0, 0.0, 0.0], translate, {'start': 0, 'duration': 0, 'one_time': False, 'interval': 1},
                                    [fx_sampler(0, 'rx_ring')], alpha_keys=[[1.0, 0, 0, 0.0], [1.0, 0, 0, 1.0]]))
    pkg.emitters[-1]['emission']['position_random'] = 0.0   # the template jitters every spawn by 2 units: a probe must not
    pkg.emitters[-1]['shape']['radius'] = [0.0, 0.0, 0.0]; pkg.emitters[-1]['shape']['type'] = 'point'
    return pkg


def main():
    pk = []
    if '--probe' in sys.argv:
        pk += [probe_package('P_TrailGokuXKameBallProbe0', (0.0, 0.0, 0.0)), probe_package('P_TrailGokuXKameBallProbeM', (0.0, 0.0, 0.0))]
    use_skill('KMH')
    for t, lk in LOOK.items():
        pk.append(beam_package('P_TrailGokuXKame%s' % t, lk['S'], lk['L'], lk['life'], lk['ramp'], bas_scale=1.6, hand_scale=0.45, particles=KMH_PARTICLES, look=lk))
    pk.append(charge_package('P_TrailGokuXKameCharge'))
    pk.append(pressure_package('P_TrailGokuXKamePressure'))
    pk.append(muzzle_package('P_TrailGokuXKameMuzzle', 3.0, alpha=0.42, life=8, rings=1))
    pk.append(muzzle_package('P_TrailGokuXKameMuzzleMax', 3.6, alpha=0.7, life=12, rings=2))
    for t in range(1, 5):
        pk.append(store_package('P_TrailGokuXKameStore%d' % t, t))
    # Super Kamehameha (ULT 000_GOK_CKM): effect 0 (charge at the hand, Ckm_Crg x2) and effect 1 (the beam: Bas x2.5, Hand x0.9, the particle files); S 3.2 keeps the
    # head a little wider than the Super hit spheres (8.6 world) without swallowing the screen
    use_skill('CKM')
    pk.append(beam_package('P_TrailGokuXKameSuper', 3.2, 52, 64, 6, bas_scale=2.5, hand_scale=0.9, particles=CKM_PARTICLES, look=SUPER_LOOK, skill_key='CKM'))
    pk.append(charge_package('P_TrailGokuXKameSuperCharge', crg_scale=2.0, motes=False, chant=(8, 22, 36, 48),
                                   ball=((0, 0.3), (22, 0.65), (48, 1.1)), ring_rate=0.09))   # the Super's chant is compressed into its 54 frames
    pk.append(muzzle_package('P_TrailGokuXKameSuperMuzzle', 4.5, fire_scale=2.0, alpha=0.8, life=14, rings=3))
    summ = {}
    for p in pk:
        p.write()
        summ[p.name] = {'emitters': len(p.emitters), 'textures': len(p.textures), 'meshes': len(p.meshes)}
        print('%-28s %3d emitters %2d textures %2d meshes' % (p.name, len(p.emitters), len(p.textures), len(p.meshes)))
    (WT / '_build/xv2-kame').mkdir(parents=True, exist_ok=True)
    (WT / '_build/xv2-kame/fx/summary.json').write_text(json.dumps(summ, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
