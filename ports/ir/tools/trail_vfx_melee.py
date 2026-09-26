#!/usr/bin/env python3
"""trail_vfx_melee.py - an Ultimate effect (an eft2 / VFXB emitter set of ef_trail.eff) as a Melee particle
bank: the route-(c) pilot of _research/ultimate-particles.md, on Firaga's in-flight effect.

    python ports/ir/tools/trail_vfx_melee.py --dump <EffectLibrary dump of ef_trail.eff>
        --set P_TrailFireBullet --bank-file EfUsData.dat --bank-sym effUsDataTable -o <out dir>

INPUT. `--dump` is KillzXGaming's EffectLibrary (MIT, github.com/KillzXGaming/EffectLibrary) run on GD's own
ef_trail.eff: EffectConverter.exe ef_trail.eff -> ef_trail/<set>/<emitter>/EmitterData.json + <id>.bntx. The
library is the field map of the v22 emitter record (names below are its names); nothing of it is copied here.
The BNTX textures are decoded here (Tegra block-linear deswizzle + BCn through texture2ddecoder).

OUTPUT. <out>/<bank file> (efbuild: HSD ptcl generators + texture groups + m-ex effBehaviorTable), the efbuild
spec, and <out>/vfx_report.json: every emitter's decoded values next to what the Melee generator got.

THE MAPPING (per particle emitter; one Melee generator each, behaviour 5 = follows the article's joint):
  ParticleData.Life                   -> generator life (frames)
  Emission (dist mode: Rate per EmitterDistUnit of travel at --speed; else Rate per Interval frames)
                                      -> generator random = -(particles a frame) (generator.c: a negative
                                         random is an exact per-frame count, fractions accumulate)
  ShapeInfo.VolumeRadius              -> disc radius (particles start anywhere inside it)
  ParticleVelocity.DesignatedDir*Scale-> generator velocity; AllDirection -> the disc's spread angle
  EmitterStatic.GravityScale/Dir      -> gravity (Melee: vel.y -= grav, so an upward pull is negative)
  EmitterStatic.AirRes                -> friction (Melee: vel *= fric)
  ParticleScale.Scale x ScaleAnim     -> size keys (Melee's size is the quad's half width) -> 0xA0 size interps
  ParticleColor Color0 x ColorScale, Alpha0 (constant or 8-key curves)
                                      -> EnvCol keys (0xD0) = the flame colour, PrimCol (0xC0) = its hot core
                                         (Color0 lifted toward white), alpha on PrimCol; PrimEnv on (0xAD):
                                         colour = lerp(env, prim, texture I), alpha = prim.a x texture A
  Sampler1 + TexPatternAnim1 (4x4 atlas, Table, 1 frame each)
                                      -> a texture group of the atlas cells (IA8: I = the BC5 red "heat",
                                         A = green "shape"), one 0x40 pose per frame from the Table
  RenderState.BlendType 1 (add)       -> ParticleKind BlendOne
DROPPED (what route (c)'s shader variants would add): Sampler0 = ef_cmn_indirect00 (UV distortion),
Sampler2 = ef_cmn_grade05 (the heat -> colour ramp; approximated by the prim/env pair), soft-particle
depth fade, ScaleRandom / LifeRandom (%), EmVelInherit, the emission start delay, ParticleFluctuation.
PRIMITIVE emitters (a G3PR mesh: sphere1, spherering1, circle2) are not particles: the article's own
model carries the core (trail_magic_models.py, recoloured with sphere1's decoded colours). flare1 is a
screen-facing quad -> one short-lived additive particle a frame.
"""
import argparse
import base64
import glob
import json
import math
import os
import struct
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EFBUILD = os.path.join(ROOT, "ports", "halberd", "effects", "tools", "efbuild", "bin", "Release", "net8.0", "efbuild.exe")
NONE_ID = 18446744073709551615

# ---- BNTX ------------------------------------------------------------------------------------------
FMT = {0x0b: (1, 4, 'rgba8'), 0x1a: (4, 8, 'bc1'), 0x1c: (4, 16, 'bc3'), 0x1d: (4, 8, 'bc4'),
       0x1e: (4, 16, 'bc5'), 0x20: (4, 16, 'bc7')}


def _gob(x, y, wbytes, bpp, bh):
    wg = (wbytes + 63) // 64
    a = (y // (8 * bh)) * 512 * bh * wg + (x * bpp // 64) * 512 * bh + (y % (8 * bh) // 8) * 512
    x *= bpp
    return a + ((x % 64) // 32) * 256 + ((y % 8) // 2) * 64 + ((x % 32) // 16) * 32 + (y % 2) * 16 + (x % 16)


def bntx(path):
    import texture2ddecoder as T
    d = open(path, 'rb').read()
    i = d.find(b'BRTI')
    fmt = struct.unpack_from('<I', d, i + 0x1c)[0]
    w, h = struct.unpack_from('<II', d, i + 0x24)
    layout = struct.unpack_from('<I', d, i + 0x34)[0]
    name_off, _, ptrs = struct.unpack_from('<QQQ', d, i + 0x60)
    name = d[name_off + 2:name_off + 2 + struct.unpack_from('<H', d, name_off)[0]].decode()
    mip0 = struct.unpack_from('<Q', d, ptrs)[0]
    bw, bpb, kind = FMT[fmt >> 8]
    wb, hb = (w + bw - 1) // bw, (h + bw - 1) // bw
    bh = 1 << (layout & 7)
    while bh > 1 and hb <= (bh // 2) * 8:
        bh //= 2
    lin = bytearray(wb * hb * bpb)
    for y in range(hb):
        for x in range(wb):
            s = mip0 + _gob(x, y, wb * bpb, bpb, bh)
            lin[(y * wb + x) * bpb:(y * wb + x + 1) * bpb] = d[s:s + bpb]
    if kind == 'rgba8':
        return name, Image.frombytes('RGBA', (w, h), bytes(lin))
    raw = getattr(T, 'decode_' + kind)(bytes(lin), wb * 4, hb * 4)
    return name, Image.frombytes('RGBA', (wb * 4, hb * 4), raw, 'raw', 'BGRA').crop((0, 0, w, h))


def ia_frames(img, div, size):
    """atlas (div x div cells) -> IA frames as RGBA (rgb = the red 'heat', a = the green 'shape')."""
    a = np.asarray(img)
    cw, ch = img.width // div, img.height // div
    out = []
    for cy in range(div):
        for cx in range(div):
            cell = a[cy * ch:(cy + 1) * ch, cx * cw:(cx + 1) * cw]
            r, g = cell[..., 0], cell[..., 1]
            rgba = np.stack([r, r, r, g], -1).astype(np.uint8)
            im = Image.fromarray(rgba, 'RGBA').resize((size, size), Image.LANCZOS)
            out.append(base64.b64encode(im.tobytes()).decode())
    return out


# ---- curves -------------------------------------------------------------------------------------
def keys(S, table, count):
    return [(k['X'], k['Y'], k['Z'], k['Time']) for k in S[table]['Keys'][:S[count]]]


def curve_at(ks, t):
    if not ks:
        return None
    if t <= ks[0][3]:
        return ks[0][:3]
    for a, b in zip(ks, ks[1:]):
        if t <= b[3]:
            f = (t - a[3]) / max(1e-6, b[3] - a[3])
            return tuple(a[i] + (b[i] - a[i]) * f for i in range(3))
    return ks[-1][:3]


def emitter_generator(name, d, texg, frames_of, speed, report):
    S, P, Em, Sh, V, C, Sc, R = (d['EmitterStatic'], d['ParticleData'], d['Emission'], d['ShapeInfo'],
                                 d['ParticleVelocity'], d['ParticleColor'], d['ParticleScale'], d['RenderState'])
    life = int(P['Life'])
    if Em['IsEmitDistEnabled']:
        per_frame = Em['Rate'] * speed / max(1e-3, Em['EmitterDistUnit'])
    else:
        per_frame = Em['Rate'] / max(1, Em['Interval'])
    per_frame = min(per_frame, 3.0)
    c_ks = keys(S, 'Color0', 'NumColor0Keys') if C['Color0Type'] != 'Constant' else [(C['Color0R'], C['Color0G'], C['Color0B'], 0.0)]
    a_ks = keys(S, 'Alpha0', 'NumAlpha0Keys') if C['Alpha0Type'] != 'Constant' else [(C['Alpha0'],) * 3 + (0.0,)]
    s_ks = keys(S, 'ScaleAnim', 'NumScaleKeys') or [(1.0, 1.0, 1.0, 0.0)]
    cs = S['ColorScale']
    size0 = Sc['ScaleX'] * 0.5
    pat = S['TexPatternAnim1'] if d['Sampler1']['TextureID'] != NONE_ID else S['TexPatternAnim0']
    table = [t for t in pat['Table'][:max(1, int(pat['Num']))]] if pat['Num'] > 1 else [0]
    # events at particle frames
    times = sorted({0.0, 1.0} | {k[3] for k in c_ks} | {k[3] for k in a_ks} | {k[3] for k in s_ks})
    ev = {}
    def at(f):
        return ev.setdefault(max(0, min(life, int(round(f)))), [])

    def colours(t):
        c = curve_at(c_ks, t) or (1, 1, 1)
        a = (curve_at(a_ks, t) or (1, 1, 1))[0]
        env = [min(255, int(255 * x * cs)) for x in c]
        prim = [min(255, int(e + (255 - e) * 0.6)) for e in env]
        return prim + [max(0, min(255, int(255 * a)))], env + [0]
    p0, e0 = colours(0.0)
    at(0)[:0] = [[0xAD, ""], [0xC0, "ebbbb", 0] + p0, [0xD0, "ebbbb", 0] + e0]
    for a, b in zip(times, times[1:]):
        fa, fb = a * life, b * life
        p1, e1 = colours(b)
        s1 = (curve_at(s_ks, b) or (1,))[0] * size0
        dur = max(1, int(round(fb - fa)))
        at(fa).extend([[0xC0, "ebbbb", dur] + p1, [0xD0, "ebbbb", dur] + e1, [0xA0, "ef", dur, round(s1, 3)]])
    for f in range(life):
        at(f).append([0x40, "b", table[f % len(table)] if frames_of > 1 else 0])
    ops, now = [], 0
    for f in sorted(ev):
        if f > now:
            ops.append([0x00, "s", f - now])
            now = f
        ops += ev[f]
    if life > now:
        ops.append([0x00, "s", life - now])
    ops.append([0xFF, ""])
    gdir = S['GravityDirY'] if S['GravityScale'] else 0.0
    grav = -S['GravityScale'] * gdir          # Melee: vel.y -= grav
    kind = 0x1 | 0x2                          # Gravity | Friction
    if R['BlendType'] == 1:
        kind |= 0x400000                       # BlendOne (additive)
    dirv = (V['DesignatedDirX'] * V['DesignatedDirScale'], V['DesignatedDirY'] * V['DesignatedDirScale'],
            V['DesignatedDirZ'] * V['DesignatedDirScale'])
    hdr = {"type": 0, "gflags": 0, "texg": texg, "genlife": 90, "life": life, "kind": kind, "gravity": round(grav, 4),
           "friction": round(S['AirRes'], 4), "vel": [round(x, 4) for x in dirv],
           "radius": round(Sh['VolumeRadiusX'], 3), "angle": round(min(math.pi, V['AllDirection'] * math.pi * 2), 3),
           "random": round(-per_frame, 3), "size": round(size0 * s_ks[0][0], 3), "param": [0, 0, 0]}
    report[name] = {"decoded": {"life": life, "life_random_pct": P['LifeRandom'], "emission": {
        "dist": Em['IsEmitDistEnabled'], "unit": Em['EmitterDistUnit'], "rate": Em['Rate'], "interval": Em['Interval'],
        "start": Em['Start']}, "volume_radius": Sh['VolumeRadiusX'], "velocity_dir": dirv, "all_direction": V['AllDirection'],
        "gravity": S['GravityScale'], "air_res": S['AirRes'], "scale": [Sc['ScaleX'], Sc['ScaleY']],
        "scale_keys": s_ks, "color0_keys": c_ks, "alpha0_keys": a_ks, "color_scale": cs,
        "blend": R['BlendType'], "pattern": table},
        "melee": {"header": hdr, "ops": len(ops), "particles_per_frame": round(per_frame, 3)}}
    return {"name": name, "behavior": 5, "header": hdr, "ops": ops}


# ---- v2 mapping (after the audit, _research/ultimate-particles.md section 5; the fragment shaders were
# disassembled with envytools: 5.4) --------------------------------------------------------------------
VARIANTS = 4          # random roll / scale are quantised into this many generators per emitter


def rot_x(v, a):
    c, s = math.cos(a), math.sin(a)
    return (v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c)


def ultimate_frames(img, div, size, mask=None):
    """the fire atlas cells as Melee frames: rgb white, alpha = the cell's G ('a' through the BNTX
    component selector 2,2,2,3) x the grade05 border mask (the shader's second texture, quad uv)."""
    a = np.asarray(img).astype(np.float32) / 255.0
    cw, ch = img.width // div, img.height // div
    m = None
    if mask is not None:
        m = np.asarray(mask.convert('RGBA').resize((size, size), Image.LANCZOS)).astype(np.float32)[..., 0] / 255.0
    out = []
    for cy in range(div):
        for cx in range(div):
            g = Image.fromarray((a[cy * ch:(cy + 1) * ch, cx * cw:(cx + 1) * cw, 1] * 255).astype(np.uint8), 'L')
            g = np.asarray(g.resize((size, size), Image.LANCZOS)).astype(np.float32) / 255.0
            if m is not None:
                g = g * m
            rgba = np.stack([np.ones_like(g), np.ones_like(g), np.ones_like(g), g], -1)
            out.append(base64.b64encode((rgba * 255).astype(np.uint8).tobytes()).decode())
    return out


def plain_frames(img, size):
    """a single texture as IA: rgb = R, a = G (the component selector)."""
    a = np.asarray(img.resize((size, size), Image.LANCZOS))
    rgba = np.stack([a[..., 0], a[..., 0], a[..., 0], a[..., 1]], -1).astype(np.uint8)
    return [base64.b64encode(rgba.tobytes()).decode()]


def pattern_table(S, anim_type_key, d):
    pat = S['TexPatternAnim1']
    n = max(1, int(pat['Num']))
    return [t for t in pat['Table'][:n]], d['TextureAnim1']['PatternAnimType']


def emitter_generators(name, d, texg, speed, report):
    """v2: one Ultimate emitter -> VARIANTS Melee generators (roll k x 90 deg + 0.4 rad, scale factor spread
    over the ScaleRandom range), direction in the emitter frame (EmitterInfo.RotateX applied; the generator
    follows the article's joint, whose rotation is the facing), EmVelInherit folded in, gravity world,
    volume filled with a random offset, randomised life (0xA6) and speed (0xBD), pattern by its mode,
    colour / alpha per the disassembled shader."""
    S, P, Em, Sh, V, C, Sc, R, I = (d['EmitterStatic'], d['ParticleData'], d['Emission'], d['ShapeInfo'],
                                    d['ParticleVelocity'], d['ParticleColor'], d['ParticleScale'], d['RenderState'],
                                    d['EmitterInfo'])
    life = int(P['Life'])
    lrand = P['LifeRandom'] / 100.0
    if Em['IsEmitDistEnabled']:
        per_frame = Em['Rate'] * speed / max(1e-3, Em['EmitterDistUnit'])
    else:
        per_frame = Em['Rate'] / max(1, Em['Interval'])
    c_ks = keys(S, 'Color0', 'NumColor0Keys') if C['Color0Type'] != 'Constant' else [(C['Color0R'], C['Color0G'], C['Color0B'], 0.0)]
    c1_ks = keys(S, 'Color1', 'NumColor1Keys') if C['Color1Type'] != 'Constant' else [(C['Color1R'], C['Color1G'], C['Color1B'], 0.0)]
    a_ks = keys(S, 'Alpha0', 'NumAlpha0Keys') if C['Alpha0Type'] != 'Constant' else [(C['Alpha0'],) * 3 + (0.0,)]
    s_ks = keys(S, 'ScaleAnim', 'NumScaleKeys') or [(1.0, 1.0, 1.0, 0.0)]
    cs = S['ColorScale']
    user_shader = d['Combiner']['ShaderType'] == 2          # flat Color0, alpha = atlas G x grade mask
    size0 = Sc['ScaleX'] * 0.5
    srand = Sc['ScaleRandomX'] / 100.0
    table, mode = pattern_table(S, None, d)
    # direction: DesignatedDir x scale, in the emitter frame (RotateX), + the ball's velocity x EmVelInherit
    dv = (V['DesignatedDirX'] * V['DesignatedDirScale'], V['DesignatedDirY'] * V['DesignatedDirScale'],
          V['DesignatedDirZ'] * V['DesignatedDirScale'])
    dv = rot_x(dv, I['RotateX'])
    dv = (dv[0], dv[1], dv[2] + V['EmVelInherit'] * speed)
    spd = math.sqrt(sum(x * x for x in dv))
    spread = math.atan2(V['AllDirection'], max(1e-4, spd)) if V['AllDirection'] else 0.0
    vrand = V['VelRandom'] / 100.0
    radius = Sh['VolumeRadiusX']
    gens = []
    for k in range(VARIANTS):
        f = 1.0 - srand * (k + 0.5) / VARIANTS          # Ultimate scales DOWN by up to ScaleRandom %
        roll = k * (math.pi / 2) + 0.4
        ev = {}
        def at(fr):
            return ev.setdefault(max(0, min(life, int(round(fr)))), [])

        def col(t):
            c = [min(255, int(round(255 * x * cs))) for x in (curve_at(c_ks, t) or (1, 1, 1))]
            a = max(0, min(255, int(round(255 * (curve_at(a_ks, t) or (1, 1, 1))[0]))))
            return c + [a]
        head = [[0xA6, "ss", int(round(life * (1 - lrand))), int(round(life * lrand))]] if lrand else []
        if vrand and spd > 0:
            head.append([0xBD, "ff", round(spd * (1 - vrand), 4), round(spd * vrand, 4)])
        if radius > 0:
            r = radius * 0.8
            head.append([0xA8, "fff", round(r, 3), round(r, 3), round(r, 3)])
        head.append([0xB6, "ef", 0, round(roll, 4)])
        c0 = col(0.0)
        head.append([0xC0, "ebbbb", 0] + c0)
        if not user_shader:                               # lerp(Color1, Color0, tex): PrimEnv
            e1 = [min(255, int(round(255 * x * cs))) for x in (curve_at(c1_ks, 0.0) or (1, 1, 1))] + [0]
            head += [[0xAD, ""], [0xD0, "ebbbb", 0] + e1]
        at(0)[:0] = head
        times = sorted({0.0, 1.0} | {kk[3] for kk in c_ks} | {kk[3] for kk in a_ks} | {kk[3] for kk in s_ks})
        for a_, b_ in zip(times, times[1:]):
            fa, fb = a_ * life, b_ * life
            dur = max(1, int(round(fb - fa)))
            s1 = (curve_at(s_ks, b_) or (1,))[0] * size0 * f
            at(fa).extend([[0xC0, "ebbbb", dur] + col(b_), [0xA0, "ef", dur, round(s1, 3)]])
        n = len(table)
        for fr in range(life):
            if mode == 1:        # FitLifespan
                idx = table[min(n - 1, fr * n // max(1, life))]
            elif mode == 2:      # Clamp
                idx = table[min(fr, n - 1)]
            elif mode == 3:      # Loop
                idx = table[fr % n]
            else:
                idx = table[0] if n > 1 else 0
            at(fr).append([0x40, "b", idx])
        ops, now = [], 0
        for fr in sorted(ev):
            if fr > now:
                ops.append([0x00, "s", fr - now])
                now = fr
            ops += ev[fr]
        if life > now:
            ops.append([0x00, "s", life - now])
        ops.append([0xFF, ""])
        grav = -S['GravityScale'] * S['GravityDirY'] if S['GravityScale'] else 0.0
        kind = 0x1 | 0x2
        if R['BlendType'] == 1:
            kind |= 0x400000
        hdr = {"type": 0, "gflags": 0, "texg": texg, "genlife": 90, "life": life, "kind": kind,
               "gravity": round(grav, 4), "friction": round(S['AirRes'], 4),
               "vel": [round(dv[0], 4), round(dv[1], 4), round(dv[2], 4)],
               "radius": 0.0, "angle": round(spread, 4), "random": round(-per_frame / VARIANTS, 4),
               "size": round(size0 * f * s_ks[0][0], 3), "param": [0, 0, 0]}
        gens.append({"name": "%s#%d" % (name, k), "behavior": 5, "header": hdr, "ops": ops})
    report[name] = {"decoded": {"life": life, "life_random_pct": P['LifeRandom'], "per_frame": round(per_frame, 3),
                                "start": Em['Start'], "trans_z": I['TransZ'], "rotate_x": I['RotateX'],
                                "velocity_local": [round(x, 4) for x in dv], "spread_rad": round(spread, 4),
                                "vel_random_pct": V['VelRandom'], "volume": [Sh['VolumeType'], radius],
                                "scale": size0 * 2, "scale_random_pct": Sc['ScaleRandomX'], "scale_keys": s_ks,
                                "color0_keys": c_ks, "color_scale": cs, "alpha0_keys": a_ks,
                                "pattern": [mode, table], "user_shader": user_shader, "blend": R['BlendType']},
                    "melee": {"generators": VARIANTS, "per_frame_each": round(per_frame / VARIANTS, 4),
                              "sizes": [g["header"]["size"] for g in gens]}}
    return gens


def slot_bank(mxdt, internal, bank_file, bank_sym):
    """The fighter slot's MxDt.dat gets an effect-bank row for the bank file and its effect_index -> it
    (the same edit ports/halberd/tools/build_mk_effects.py makes for Meta Knight). Returns (bank, old index)."""
    sys.path.insert(0, os.path.join(ROOT, "ports", "halberd", "model", "tools"))
    sys.path.insert(0, os.path.join(ROOT, "tools", "mex_port"))
    import install_mk as IM
    w = IM.Writer(open(mxdt, "rb").read())
    root = w.ar.public("mexData")
    md = w.u32(root); eff = w.u32(root + 0x18); tbl = w.u32(eff); n = w.u32(md + 0x24)
    effidx = w.u32(w.u32(root + 0x08) + 0x24)
    rows = [(w.str_at(w.u32(tbl + 12 * i)) if w.u32(tbl + 12 * i) else None) for i in range(n)]
    bank = rows.index(bank_file) if bank_file in rows else None
    if bank is None:
        bank = n
        if n + 1 > 65:
            sys.exit("MxDt has %d effect banks; the port's particle arrays hold 65" % n)
        new = w.alloc(bytes(12 * (n + 1)), 4)
        for i in range(n):
            for k in range(3):
                o = tbl + 12 * i + 4 * k
                (w.ptr if o in w.relocs else w.put)(new + 12 * i + 4 * k, w.u32(o))
        w.ptr(new + 12 * n, w.cstr(bank_file)); w.ptr(new + 12 * n + 4, w.cstr(bank_sym))
        w.ptr(eff, new); w.put(md + 0x24, n + 1)
    old = w.data[effidx + internal]
    w.data[effidx + internal] = bank
    w.save(mxdt)
    return bank, old


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--set", default="P_TrailFireBullet")
    ap.add_argument("--speed", type=float, default=1.65, help="the article's travel speed (dist-mode emission)")
    ap.add_argument("--bank-file", default="EfUsData.dat")
    ap.add_argument("--bank-sym", default="effUsDataTable")
    ap.add_argument("--frame-size", type=int, default=64)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--slot", help="a fighter slot mod's files/ dir: copy the bank there and give its MxDt row the bank")
    ap.add_argument("--internal", type=int, default=52, help="the slot's m-ex internal fighter row (install log)")
    ap.add_argument("--bank", type=int, default=0, help="without --slot: the bank index the ids start from")
    a = ap.parse_args()
    sd = os.path.join(a.dump, a.set)
    order = json.load(open(os.path.join(sd, "EmitterOrder.txt")))["Order"]
    report, gens, texgroups, texidx = {}, [], [], {}
    skipped, effects = {}, []
    joints = {0.0: 0, 2.3: 2, 6.0: 3}      # the FireCore model's emit joints (trail_magic_models.py)
    for em in order:
        d = json.load(open(os.path.join(sd, em, "EmitterData.json")))
        P = d['ParticleData']
        if P['PrimitiveID'] != NONE_ID:
            skipped[em] = "primitive (bfres mesh): an effect model, not particles"
            continue
        if d['Combiner']['ShaderType'] == 1:
            # fire_rif1 (shader 207): rgb = 2 x the FRAME BUFFER (sampled at screen coordinates) x Color0 -
            # a heat-haze refraction of what is behind the ball. Melee's particle path cannot sample the
            # frame buffer; it is left out, not faked.
            skipped[em] = "screen-space heat haze (samples the frame buffer): needs a renderer feature"
            continue
        emdir = os.path.join(sd, em)
        user = d['Combiner']['ShaderType'] == 2
        s1 = d['Sampler1']['TextureID']
        if user and s1 != NONE_ID:
            key = (s1, d['Sampler2']['TextureID'])
            if key not in texidx:
                atlas = bntx(os.path.join(emdir, "%d.bntx" % s1))[1]
                mask = bntx(os.path.join(emdir, "%d.bntx" % d['Sampler2']['TextureID']))[1]                     if d['Sampler2']['TextureID'] != NONE_ID else None
                div = int(d['EmitterStatic']['TexScrollAnim1']['UVDivX'])
                texidx[key] = len(texgroups)
                texgroups.append({"name": "fire atlas x grade mask", "w": a.frame_size, "h": a.frame_size,
                                  "fmt": "IA8", "frames": ultimate_frames(atlas, div, a.frame_size, mask)})
        else:
            key = (d['Sampler0']['TextureID'], None)
            if key not in texidx:
                nm, img = bntx(os.path.join(emdir, "%d.bntx" % key[0]))
                texidx[key] = len(texgroups)
                texgroups.append({"name": nm, "w": a.frame_size, "h": a.frame_size, "fmt": "IA8",
                                  "frames": plain_frames(img, a.frame_size)})
        first = len(gens)
        gens += emitter_generators(em, d, texidx[key], a.speed, report)
        tz = round(d['EmitterInfo']['TransZ'], 1)
        ids = list(range(6000 + first, 6000 + len(gens)))
        effects.append({"id": 6000 + first, "count": len(gens) - first, "frame": int(d['Emission']['Start']),
                        "joint": joints.get(tz, 0)})
        report[em]["melee"]["effect_ids"] = ids
        report[em]["melee"]["attach"] = {"frame": int(d['Emission']['Start']), "joint": joints.get(tz, 0)}
    os.makedirs(a.out, exist_ok=True)
    # the bank's generator ids start at bank * 1000 (efAsync_MexResolve's final id; hsd_8039F05C indexes the
    # bank's command lists by id - EffectIDStart), so the slot's bank row is settled first
    bank, old = (slot_bank(os.path.join(a.slot, "MxDt.dat"), a.internal, a.bank_file, a.bank_sym)
                 if a.slot else (a.bank, None))
    spec = {"symbol": a.bank_sym, "models": [], "ptcl": {"id_start": bank * 1000, "generators": gens, "texgroups": texgroups}}
    sp = os.path.join(a.out, "vfx_spec.json")
    json.dump(spec, open(sp, "w"))
    efj = os.path.join(a.out, "vfx_ef_empty.json")
    json.dump({"textures": [], "reft": [], "models": []}, open(efj, "w"))
    out = os.path.join(a.out, a.bank_file)
    r = subprocess.run([EFBUILD, "build", efj, sp, out], capture_output=True, text=True)
    if r.returncode:
        sys.exit("efbuild failed: " + r.stdout[-800:] + r.stderr[-800:])
    rep = {"set": a.set, "bank_file": a.bank_file, "bytes": os.path.getsize(out), "generators": [g["name"] for g in gens],
           "texgroups": [(t["name"], len(t["frames"]), t["w"]) for t in texgroups], "skipped": skipped, "emitters": report}
    json.dump(rep, open(os.path.join(a.out, "vfx_report.json"), "w"), indent=1)
    json.dump(effects, open(os.path.join(a.out, "vfx_effects.json"), "w"))
    for i, g in enumerate(gens):
        h = g["header"]
        print("gen %d %-10s life %3d  %.2f/frame  size %5.2f  radius %4.1f  texg %d  ops %d" % (
            i, g["name"], h["life"], -h["random"], h["size"], h["radius"], h["texg"], len(g["ops"])))
    print("skipped:", skipped)
    print("wrote", out, os.path.getsize(out), "bytes")
    if a.slot:
        import shutil
        shutil.copyfile(out, os.path.join(a.slot, a.bank_file))
        print("slot: MxDt effect bank %d = %s / %s, internal %d effect_index %d -> %d; generators are ids 6000-%d" % (
            bank, a.bank_file, a.bank_sym, a.internal, old, bank, 6000 + len(gens) - 1))


if __name__ == "__main__":
    main()
