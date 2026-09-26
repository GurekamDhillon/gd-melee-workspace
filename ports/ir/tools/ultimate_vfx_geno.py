#!/usr/bin/env python3
"""ultimate_vfx_geno.py - an Ultimate effect (eft2 / VFXB, as in fighter/<x>/ef_<x>.eff) -> a Geno effect package
(melee docs/geno.md section 20, "Geno effects"), for the native effect runtime (_research/geno-effects-runtime.md).

    python ports/ir/tools/ultimate_vfx_geno.py --dump <EffectLibrary dump dir of the .eff> \
        [--set P_TrailFireBullet ...] [--envydis <envydis_min.exe>] -o <out dir>

GENERAL: any emitter set of any Ultimate effect file; nothing here is Sora's. Firaga (P_TrailFireBullet) is the
first test case.

INPUT: an EffectLibrary (MIT, github.com/KillzXGaming/EffectLibrary) dump of the user's own .eff:
<dump>/<set>/EmitterOrder.txt, <dump>/<set>/<emitter>/EmitterData.json (the emitter record, EffectLibrary's
field names), <id>.bntx (textures), <id>.bfres (primitive meshes), Shader.bnsh (the emitter's compiled vertex +
fragment programs), <MAGIC>.bin (emitter sub-sections: plugins EPxx, fields Fxxx).

OUTPUT (never committed - it is derived from the game): <out>/<set>.gfx.json + <out>/tex/*.png +
<out>/mesh/*.json + <out>/shader/*.txt (the disassembly, for review). What the format holds and what the runtime
does with it: geno.md 20. What this tool does per part:

  emitter record    -> "emitters"[] with every field the runtime uses, renamed to the format's names; values 1:1
  curves            -> 8-key (x, y, z, t) tables as they are ("keys"), with their loop settings
  textures          -> PNG (BNTX decoded: Tegra block linear + BCn), the BNTX component selector recorded
                       ("swizzle": which source channel feeds r, g, b, a) - the runtime samples exactly as the GPU did
  primitives        -> mesh JSON (positions, normals, uvs, colours, indices) from the emitter's bfres
  shader            -> "material.shader": the nearest type of the Geno effect shader library (sprite / warp /
                       distortion; geno.md 20.2) + its parameters, CHOSEN by reading the emitter's compiled programs
                       (envytools envydis): no source program is carried into the IR. The disassembly is written
                       beside the package for review (shader/*.txt); --keep-programs also puts the fragment op list
                       and the vertex-output map in "program" (reference only; the runtime never reads them)
  HDR colour        -> "material.bloom" {intensity, threshold}: the effect-only bloom's parameters
  sub-sections      -> "extensions"{magic: raw float/int words} (plugins / fields whose layouts are not mapped yet)
"""
import argparse
import base64
import json
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
NONE_ID = 18446744073709551615
FORMAT_VERSION = 1

# eft2 enums (EffectLibrary Enums.cs / the emitter record)
VOLUME = {0: "point", 1: "circle", 2: "circle_same_divide", 3: "circle_fill", 4: "sphere", 5: "sphere_same_divide",
          6: "sphere_same_divide64", 7: "sphere_fill", 8: "cylinder", 9: "cylinder_fill", 10: "box", 11: "box_fill",
          12: "line", 13: "line_same_divide", 14: "rectangle", 15: "primitive"}
PATTERN = {0: "none", 1: "fit_life", 2: "clamp", 3: "loop", 4: "random"}
BLEND = {0: "alpha", 1: "add", 2: "sub", 3: "mul", 4: "screen"}
BILLBOARD = {0: "billboard", 1: "plate_xy", 2: "plate_xz", 3: "directional_y", 4: "directional_polygon",
             5: "stripe", 6: "complex_stripe", 7: "primitive", 8: "y_billboard"}
CURVE_KIND = {"Constant": "constant", "Random": "random", "Animated8Key": "keys", "Key4Value3": "keys"}
FOLLOW = {0: "srt", 1: "none", 2: "translate"}
SHADER_KIND = {0: "normal", 1: "user_macro1", 2: "user_macro2"}


def keys(S, table, count):
    return [[k['X'], k['Y'], k['Z'], k['Time']] for k in S[table]['Keys'][:S[count]]]


def curve(C, S, name, table, count, const):
    kind = CURVE_KIND.get(C[name + "Type"], C[name + "Type"])
    out = {"kind": kind, "value": const}
    if kind == "keys":
        out["keys"] = keys(S, table, count)
    return out


# ---- textures ----------------------------------------------------------------------------------------------
def texture_png(path, out_dir):
    import trail_vfx_melee as V
    name, img = V.bntx(path)
    d = open(path, 'rb').read()
    i = d.find(b'BRTI')
    comp = list(d[i + 0x58:i + 0x5c])        # component selector per output channel r, g, b, a
    fmt = struct.unpack_from('<I', d, i + 0x1c)[0]
    os.makedirs(out_dir, exist_ok=True)
    img.save(os.path.join(out_dir, name + ".png"))
    # selector codes: 0 zero, 1 one, 2 red, 3 green, 4 blue, 5 alpha (NVN)
    sel = {0: "0", 1: "1", 2: "r", 3: "g", 4: "b", 5: "a"}
    return {"name": name, "file": "tex/%s.png" % name, "w": img.width, "h": img.height,
            "source_format": hex(fmt), "swizzle": "".join(sel.get(c, "?") for c in comp)}


# ---- primitive meshes -------------------------------------------------------------------------------------
def mesh_json(bfres, bfdump, out_dir, name):
    r = subprocess.run(["dotnet", bfdump, bfres], capture_output=True, text=True)
    if r.returncode:
        return None
    shapes = json.loads(r.stdout)
    os.makedirs(out_dir, exist_ok=True)
    s = shapes[0]
    m = {"name": name, "model": s["model"], "shape": s["shape"], "indices": s["indices"],
         "position": [v[:3] for v in s["attrs"].get("_p0", [])], "normal": [v[:3] for v in s["attrs"].get("_n0", [])],
         "uv0": [v[:2] for v in s["attrs"].get("_u0", [])], "color0": s["attrs"].get("_c0")}
    json.dump(m, open(os.path.join(out_dir, name + ".json"), "w"))
    return {"name": name, "file": "mesh/%s.json" % name, "verts": len(m["position"]), "tris": len(m["indices"]) // 3}


# ---- fragment program ---------------------------------------------------------------------------------------
def nvn_blocks(bnsh):
    d = open(bnsh, 'rb').read()
    out = []
    for m in re.finditer(b'\x78\x56\x34\x12', d):
        o = m.start() + 0x80
        e = o
        while e + 32 <= len(d) and d[e:e + 32] != bytes(32):
            e += 32
        out.append(d[o:e])
    return out


OPERAND = re.compile(r'(neg |abs |not )*(\$r\d+|\$p\d+|c\d+\[0x[0-9a-f]+\]|a\[0x[0-9a-f]+\]|0x[0-9a-f]+)')


def translate_fragment(listing):
    """Straight-line Maxwell fragment code -> [{"op", "dst", "src": [...], "mod": [...]}], or None when the code has
    control flow or instructions this translator does not know (then the listing is kept for review).
    Register $r0..$r3 at `exit` are the output colour (NVN fragment output 0)."""
    ops = []
    for line in listing:
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        ins = parts[3]
        if ins.startswith("sched") or not ins.strip():
            continue
        if ins.startswith("exit"):
            ops.append({"op": "exit"})
            break
        pred = None
        m = re.match(r'(not )?\$p(\d) (.*)', ins)
        if m:
            pred, ins = ("!" if m.group(1) else "") + "p" + m.group(2), m.group(3)
        head = ins.split()[0]
        words = ins.split()
        mods = [w for w in words[1:] if w in ("ftz", "sat", "pass", "nodep", "bf", "rcp", "rsq", "floor", "m2",
                                              "le", "ge", "lt", "gt", "eq", "and", "t2d")]
        if head == "texs":   # texs [nodep] <lod> $dst0 $u $v <handle> t2d <components>
            mods.append("mask=" + words[-1])
        srcs = [("-" if "neg" in (g[0] or "") else "") + ("|" if "abs" in (g[0] or "") else "") + g[1]
                for g in OPERAND.findall(ins)]
        op = {"op": head, "mod": mods, "args": srcs}
        if pred:
            op["pred"] = pred
        if head not in ("ipa", "mufu", "texs", "fmul", "ffma", "fadd", "mov", "mov32i", "fset", "fsetp", "kil",
                        "fmnmx", "f2f"):
            return None
        ops.append(op)
    return ops


# c9 = the emitter's static uniform block: a 0x50-byte header + the emitter record's EmitterStatic block (v22
# layout, EffectLibrary's field order). Confirmed on the programs: c9[0x5e8] = AlphaThreshold (the alpha-test
# kill), c9[0x5c8/0x5cc] = FresnelAlphaParam1/2, c9[0x100/0x104] = Coefficient0/1 (the UV warp strength),
# c9[0x3c0..] = the Color0 keys.
STATIC_V22 = [("Flags", 16), ("NumKeys", 32), ("LoopRates", 20), ("LoopRandoms", 20), ("Unknown34", 8),
              ("GravityDir", 12), ("GravityScale", 4), ("AirRes", 4), ("val_0x74", 12), ("Center", 8), ("Offset", 4),
              ("Padding", 4), ("Amplitude", 8), ("Cycle", 8), ("PhaseRnd", 8), ("PhaseInit", 8), ("Coefficient", 8),
              ("val_0xB8", 8), ("TexPatternAnim0", 144), ("TexPatternAnim1", 144), ("TexPatternAnim2", 144),
              ("TexScrollAnim0", 80), ("TexScrollAnim1", 80), ("TexScrollAnim2", 80), ("ColorScale", 4), ("val_0x364", 12),
              ("Color0", 128), ("Alpha0", 128), ("Color1", 128), ("Alpha1", 128), ("SoftEdgeParam", 8),
              ("FresnelAlphaParam", 8), ("NearDistAlphaParam", 8), ("FarDistAlphaParam", 8), ("DecalParam", 8),
              ("AlphaThreshold", 4), ("Padding2", 4), ("AddVelToScale", 4), ("SoftParticle", 8), ("Padding3", 4),
              ("ScaleAnim", 128), ("ParamAnim", 128), ("RotateInit", 16), ("RotateInitRand", 16), ("RotateAdd", 16),
              ("RotateAddRand", 16), ("ScaleLimitDist", 16)]


def c9_field(off):
    o, at = off - 0x50, 0
    for name, size in STATIC_V22:
        if at <= o < at + size:
            return name, o - at
        at += size
    return None, off


def vertex_outputs(listing):
    """What each varying the vertex program writes is made of: a backward slice from every `st a[X] $rN` to the
    c9 fields (the emitter record) and vertex inputs it reads. Classified as color0.r/g/b, alpha0, color1.*,
    alpha1, uv<k>.u/v (TexScrollAnim<k>: even words = u, odd = v), param (ParamAnim), vertex_color (vertex
    inputs only), position / view (rotation, scale, centre, wave), constant (nothing)."""
    ins = []
    for l in listing:
        p = l.split(None, 3)
        if len(p) == 4 and not p[3].startswith("sched"):
            ins.append(p[3])
    out = {}
    for i, s_ in enumerate(ins):
        m = re.match(r'st b32 a\[(0x[0-9a-f]+)\] (\$r\d+)', s_)
        if not m:
            continue
        addr, reg = m.group(1), m.group(2)
        need, fields, inputs, j = {reg}, {}, set(), i - 1
        while j >= 0 and need and i - j < 400:
            w = ins[j].split()
            dst = next((x for x in w[1:] if x.startswith("$r")), None)
            if dst in need and not w[0].startswith("st"):
                need.discard(dst)
                for x in w[w.index(dst) + 1:]:
                    if x.startswith("$r") and x != "$r255":
                        need.add(x)
                for c in re.findall(r'c9\[(0x[0-9a-f]+)\]', ins[j]):
                    n, rel = c9_field(int(c, 16))
                    if n:
                        fields.setdefault(n, set()).add(rel)
                inputs |= set(re.findall(r'a\[(0x[0-9a-f]+)\]', ins[j]))
            j -= 1
        keys_ = set(fields)
        comp = None
        if keys_ == {"ColorScale"}:
            comp = "color_scale"
        elif keys_ and keys_ <= {"Color0", "ColorScale"} or keys_ and keys_ <= {"Color1", "ColorScale"}:
            nm = "color0" if "Color0" in keys_ else "color1"
            k = min(r for r in fields[nm.capitalize()]) % 16 // 4
            comp = "%s.%s" % (nm, "rgba"[k])
        elif keys_ and keys_ <= {"Alpha0"}:
            comp = "alpha0"
        elif keys_ and keys_ <= {"Alpha1"}:
            comp = "alpha1"
        elif any(k.startswith("TexScrollAnim") for k in keys_):
            # the sampler whose scroll block feeds it most; u / v by the varying pair (x at +0, y at +4)
            k = max((k for k in keys_ if k.startswith("TexScrollAnim")), key=lambda k: len(fields[k]))
            comp = "uv%s.%s" % (k[-1], "v" if int(addr, 16) % 8 else "u")
        elif keys_ == {"ParamAnim"}:
            comp = "param"
        elif not keys_ and inputs:
            comp = "vertex_input " + ",".join(sorted(inputs))
        elif not keys_:
            comp = "constant"
        else:
            comp = "position/view (%s)" % ",".join(sorted(keys_)[:6])
        out[addr] = comp
    return out


def shader_type(d, samplers, frag, vouts):
    """The Geno effect shader library type for an emitter (geno.md 20.2), from what its programs read:
      distortion  samples more textures than the emitter has samplers (the extra one is the frame copy) or reads
                  the screen-size bank c1: a heat haze / refraction over the frame
      warp        reads c9 Coefficient0/1 (c9[0x100/0x104]): texture 1 offsets texture 0's UVs by that strength
      sprite      everything else: texture(s) x colour ramps
    colour: "lerp" (lerp(color1, color0, tex), when the vertex program feeds color1) or "modulate" (color0 x tex);
    fresnel when it reads c9[0x5c8] (FresnelAlphaParam). None when no program could be read (the runtime then
    uses sprite + modulate)."""
    if frag is None:
        return None
    args = {a.lstrip("-|") for o in frag for a in o.get("args", [])}
    ntex = sum(o["op"] == "texs" for o in frag)
    S = d['EmitterStatic']
    if ntex > len(samplers) or any(a.startswith("c1[") for a in args):
        t = {"type": "distortion", "strength": [S.get('Coefficient0', 0.0), S.get('Coefficient1', 0.0)]}
    elif "c9[0x100]" in args or "c9[0x104]" in args:
        t = {"type": "warp", "strength": [S.get('Coefficient0', 0.0), S.get('Coefficient1', 0.0)],
             "base": 0, "offset": 1 if len(samplers) > 1 else 0}
    else:
        t = {"type": "sprite"}
    t["color"] = "lerp" if any(str(v).startswith("color1") for v in (vouts or {}).values()) else "modulate"
    t["alpha"] = "texture_product" if len(samplers) > 1 else "texture"
    t["fresnel"] = "c9[0x5c8]" in args
    t["alpha_test"] = "c9[0x5e8]" in args
    return t


def bloom(d):
    """Effect-only bloom: what of this emitter's colour is over 1.0 (HDR). Ultimate's ColorScale multiplies the
    particle colour; the part above the threshold goes to the bloom buffer at `intensity`."""
    S, C = d['EmitterStatic'], d['ParticleColor']
    peak = max([C['Color0R'], C['Color0G'], C['Color0B']] + [0.0]) * S['ColorScale']
    return {"threshold": 1.0, "intensity": round(max(0.0, peak - 1.0), 4)}


def disassemble(envydis, code, tmp):
    open(tmp, 'wb').write(code)
    return subprocess.run([envydis, tmp], capture_output=True, text=True).stdout.splitlines()


# ---- emitters ---------------------------------------------------------------------------------------------
def emitter(d, name, order, tex_ids, mesh_ref, program, ext):
    S, I, Em, Sh, R, P, V, C, Sc, CI = (d['EmitterStatic'], d['EmitterInfo'], d['Emission'], d['ShapeInfo'],
                                        d['RenderState'], d['ParticleData'], d['ParticleVelocity'], d['ParticleColor'],
                                        d['ParticleScale'], d['ChildInheritance'])
    samplers = []
    for k in range(6):
        smp = d.get('Sampler%d' % k)
        if not smp or smp['TextureID'] == NONE_ID:
            continue
        ta = d.get('TextureAnim%d' % k) or {}
        tp, ts = S.get('TexPatternAnim%d' % k), S.get('TexScrollAnim%d' % k)
        samplers.append({"slot": k, "texture": tex_ids.get(smp['TextureID']), "wrap": [smp['WrapU'], smp['WrapV']],
                         "filter": "nearest" if smp['Filter'] else "linear", "sphere_map": bool(smp['IsSphereMap']),
                         "uv_channel": ta.get('UvChannel', 0),
                         "pattern": {"mode": PATTERN.get(ta.get('PatternAnimType', 0)), "count": tp and tp['Num'],
                                     "frequency": tp and tp['Frequency'], "count_random": tp and tp['NumRandom'],
                                     "table": tp and tp['Table'][:max(1, int(tp['Num']))],
                                     "loop_random_start": bool(ta.get('IsPatAnimLoopRandom'))},
                         "uv": ts and {"scroll": [ts['ScrollX'], ts['ScrollY']], "scroll_add": [ts['ScrollAddX'], ts['ScrollAddY']],
                                       "scroll_random": [ts['ScrollRandomX'], ts['ScrollRandomY']],
                                       "scale": [ts['ScaleX'], ts['ScaleY']], "scale_add": [ts['ScaleAddX'], ts['ScaleAddY']],
                                       "scale_random": [ts['ScaleRandomX'], ts['ScaleRandomY']],
                                       "rotate": ts['Rotation'], "rotate_add": ts['RotationAdd'],
                                       "rotate_random": ts['RotationRandom'], "divide": [ts['UVDivX'], ts['UVDivY']],
                                       "enable": {"scroll": ta.get('IsScroll'), "scale": ta.get('IsScale'),
                                                  "rotate": ta.get('IsRotate')},
                                       "invert_random": [ta.get('InvRandU'), ta.get('InvRandV')]}})
    return {
        "name": name, "order": order,
        "kind": "mesh" if P['PrimitiveID'] != NONE_ID else "particle",
        "mesh": mesh_ref,
        "follow": FOLLOW.get(I['FollowType'], I['FollowType']),
        "transform": {"translate": [I['TransX'], I['TransY'], I['TransZ']],
                      "translate_random": [I['TransRandX'], I['TransRandY'], I['TransRandZ']],
                      "rotate": [I['RotateX'], I['RotateY'], I['RotateZ']],
                      "rotate_random": [I['RotateRandX'], I['RotateRandY'], I['RotateRandZ']],
                      "scale": [I['ScaleX'], I['ScaleY'], I['ScaleZ']]},
        "emission": {"start": Em['Start'], "duration": Em['Duration'], "one_time": Em['isOneTime'],
                     "rate": Em['Rate'], "rate_random": Em['RateRandom'], "interval": Em['Interval'],
                     "interval_random": Em['IntervalRandom'], "position_random": Em['PositionRandom'],
                     "by_distance": Em['IsEmitDistEnabled'] and {
                         "unit": Em['EmitterDistUnit'], "min": Em['EmitterDistMin'], "max": Em['EmitterDistMax'],
                         "margin": Em['EmitterDistMarg'], "max_particles": Em['EmitterDistParticlesMax']},
                     "fade": {"on_stop": bool(I['IsFadeEmit']), "alpha_frames": I['AlphaFadeTime'],
                              "fade_in_frames": I['FadeInTime'], "alpha_fade_in": bool(I['IsAlphaFadeIn']),
                              "scale_fade_in": bool(I['IsScaleFadeIn'])}},
        "shape": {"type": VOLUME.get(Sh['VolumeType'], Sh['VolumeType']),
                  "radius": [Sh['VolumeRadiusX'], Sh['VolumeRadiusY'], Sh['VolumeRadiusZ']],
                  "form_scale": [Sh['VolumeFormScaleX'], Sh['VolumeFormScaleY'], Sh['VolumeFormScaleZ']],
                  "caliber": Sh['CaliberRatio'], "sweep": [Sh['SweepStart'], Sh['SweepLongitude'], Sh['SweepLatitude']],
                  "sweep_start_random": bool(Sh['SweepStartRandom']), "surface_random": Sh['VolumeSurfacePosRand'],
                  "line": [Sh['LineCenter'], Sh['LineLength']],
                  "divide": [Sh['NumDivideCircle'], Sh['NumDivideCircleRandom'], Sh['NumDivideLine'], Sh['NumDivideLineRandom']]},
        "particle": {
            "life": P['Life'], "life_random_pct": P['LifeRandom'], "infinite": bool(P['InfiniteLife']),
            "shape": BILLBOARD.get(P['BillboardType'], P['BillboardType']),
            "velocity": {"all_direction": V['AllDirection'], "direction": [V['DesignatedDirX'], V['DesignatedDirY'], V['DesignatedDirZ']],
                         "direction_scale": V['DesignatedDirScale'], "diffusion_angle": V['DiffusionDirAngle'],
                         "xz_diffusion": V['XZDiffusion'], "diffusion": [V['DiffusionX'], V['DiffusionY'], V['DiffusionZ']],
                         "random_pct": V['VelRandom'], "inherit": V['EmVelInherit'], "momentum_random": P['MomentumRandom']},
            "forces": {"gravity_dir": [S['GravityDirX'], S['GravityDirY'], S['GravityDirZ']], "gravity": S['GravityScale'],
                       "gravity_world": Em['IsWorldGravity'], "air_resistance": S['AirRes']},
            "rotation": {"axes": [P['IsRotateX'], P['IsRotateY'], P['IsRotateZ']],
                         "init": [S['RotateInitX'], S['RotateInitY'], S['RotateInitZ']],
                         "init_random": [S['RotateInitRandX'], S['RotateInitRandY'], S['RotateInitRandZ']],
                         "add": [S['RotateAddX'], S['RotateAddY'], S['RotateAddZ']],
                         "add_random": [S['RotateAddRandX'], S['RotateAddRandY'], S['RotateAddRandZ']],
                         "regist": S['RotateRegist'], "reverse_random": [P['RotRevRandX'], P['RotRevRandY'], P['RotRevRandZ']]},
            "scale": {"base": [Sc['ScaleX'], Sc['ScaleY'], Sc['ScaleZ']],
                      "random_pct": [Sc['ScaleRandomX'], Sc['ScaleRandomY'], Sc['ScaleRandomZ']],
                      "keys": keys(S, 'ScaleAnim', 'NumScaleKeys'), "loop": bool(P['ScaleLoop']),
                      "loop_rate": P['ScaleLoopRate'], "add_velocity": S['AddVelToScale'],
                      "limit_distance": [S['ScaleLimitDistNear'], S['ScaleLimitDistFar']]},
            "param_keys": keys(S, 'ParamAnim', 'NumParamKeys'),
        },
        "color": {"scale": S['ColorScale'],
                  "emitter": {"color0": [I['Color0R'], I['Color0G'], I['Color0B'], I['Color0A']],
                              "color1": [I['Color1R'], I['Color1G'], I['Color1B'], I['Color1A']]},
                  "color0": curve(C, S, "Color0", "Color0", "NumColor0Keys", [C['Color0R'], C['Color0G'], C['Color0B']]),
                  "alpha0": curve(C, S, "Alpha0", "Alpha0", "NumAlpha0Keys", C['Alpha0']),
                  "color1": curve(C, S, "Color1", "Color1", "NumColor1Keys", [C['Color1R'], C['Color1G'], C['Color1B']]),
                  "alpha1": curve(C, S, "Alpha1", "Alpha1", "NumAlpha1Keys", C['Alpha1']),
                  "loop": {"color0": [bool(P['LoopColor0']), P['Color0LoopRate']], "alpha0": [bool(P['LoopAlpha0']), P['Alpha0LoopRate']],
                           "color1": [bool(P['LoopColor1']), P['Color1LoopRate']], "alpha1": [bool(P['LoopAlpha1']), P['Alpha1LoopRate']]}},
        "samplers": samplers,
        "material": {"blend": BLEND.get(R['BlendType'], R['BlendType']), "blend_enable": R['IsBlendEnable'],
                     "depth_test": R['IsDepthTest'], "depth_write": R['IsDepthMask'], "depth_func": R['DepthFunc'],
                     "alpha_test": R['IsAlphaTest'] and {"func": R['AlphaFunc'], "threshold": R['AlphaThreshold']},
                     "display_side": R['DisplaySide'], "draw_path": I['DrawPath'], "sort": I['SortType'],
                     "soft_particle": C['IsSoftParticle'] and {"distance": S['SoftPartcileDist'], "volume": S['SoftParticleVolume']},
                     "fresnel_alpha": C['IsFresnelAlpha'] and [S['FresnelAlphaParam1'], S['FresnelAlphaParam2']],
                     "near_alpha": C['IsNearDistAlpha'] and [S['NearDistAlphaParam1'], S['NearDistAlphaParam2']],
                     "far_alpha": C['IsFarDistAlpha'] and [S['FarDistAlphaParam1'], S['FarDistAlphaParam2']],
                     "decal": C['IsDecal'] and [S['DecalParam1'], S['DecalParam2']]},
        "wave": {"type": d['ParticleFluctuation']['IsWaveType'], "amplitude": [S['AmplitudeX'], S['AmplitudeY']],
                 "cycle": [S['CycleX'], S['CycleY']], "phase_random": [S['PhaseRndX'], S['PhaseRndY']],
                 "phase_init": [S['PhaseInitX'], S['PhaseInitY']], "apply": [d['ParticleFluctuation']['IsApplyAlpha'],
                                                                             d['ParticleFluctuation']['IsApplayScale'],
                                                                             d['ParticleFluctuation']['IsApplayScaleY']]},
        "inherit": {k: CI[k] for k in ("Velocity", "Scale", "Rotate", "ColorScale", "Color0", "Color1", "Alpha0", "Alpha1",
                                        "VelocityRate", "ScaleRate")},
        "program": program,
        "extensions": ext,
        "_bloom": bloom(d),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--set", action="append", help="emitter set(s); default every set in the dump")
    ap.add_argument("--envydis", help="envytools disassembler (envydis_min.exe) for the fragment programs")
    ap.add_argument("--bfdump", help="the BfresLibrary mesh dumper (bfdump.dll) for primitive meshes")
    ap.add_argument("--keep-programs", action="store_true",
                    help="also put the fragment op list + vertex-output map in each emitter's program (reference)")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    sets = a.set or sorted(x for x in os.listdir(a.dump) if os.path.isdir(os.path.join(a.dump, x)))
    os.makedirs(a.out, exist_ok=True)
    tmp = os.path.join(a.out, "_code.bin")
    summary = {}
    for st in sets:
        sd = os.path.join(a.dump, st)
        order = json.load(open(os.path.join(sd, "EmitterOrder.txt")))["Order"]
        textures, meshes, emitters, tex_ids = [], [], [], {}
        report = {"emitters": 0, "translated_programs": 0, "kept_listings": 0, "meshes": 0, "extensions": [],
                  "shader_types": {}}
        for n, em in enumerate(order):
            ed = os.path.join(sd, em)
            d = json.load(open(os.path.join(ed, "EmitterData.json")))
            for f in os.listdir(ed):
                if f.endswith(".bntx"):
                    tid = int(f[:-5])
                    if tid not in tex_ids:
                        t = texture_png(os.path.join(ed, f), os.path.join(a.out, "tex"))
                        tex_ids[tid] = t["name"]
                        if all(x["name"] != t["name"] for x in textures):
                            textures.append(t)
            mesh_ref = None
            bf = [f for f in os.listdir(ed) if f.endswith(".bfres")]
            if bf and a.bfdump and d['ParticleData']['PrimitiveID'] != NONE_ID:
                mr = mesh_json(os.path.join(ed, bf[0]), a.bfdump, os.path.join(a.out, "mesh"), "%s_%s" % (st, em))
                if mr:
                    meshes.append(mr)
                    mesh_ref = mr["name"]
                    report["meshes"] += 1
            program = {"kind": SHADER_KIND.get(d['Combiner']['ShaderType'], d['Combiner']['ShaderType']),
                       "shader_index": d['ShaderReferences']['ShaderIndex']}
            frag, vouts = None, None
            sh = os.path.join(ed, "Shader.bnsh")
            if a.envydis and os.path.exists(sh):
                blocks = nvn_blocks(sh)
                if len(blocks) >= 2:
                    vouts = vertex_outputs(disassemble(a.envydis, blocks[0], tmp))
                if blocks:
                    listing = disassemble(a.envydis, blocks[-1], tmp)
                    os.makedirs(os.path.join(a.out, "shader"), exist_ok=True)
                    lp = "shader/%s_%s.frag.txt" % (st, em)
                    open(os.path.join(a.out, lp), "w").write("\n".join(listing))
                    ir = translate_fragment(listing)
                    program["fragment_listing"] = lp
                    if ir is not None:
                        frag = ir
                        report["translated_programs"] += 1
                    else:
                        report["kept_listings"] += 1
            ext = {}
            for f in os.listdir(ed):
                if f.endswith(".bin") and f != "EmitterData.bin":
                    raw = open(os.path.join(ed, f), "rb").read()
                    ext[f[:-4]] = {"words_hex": raw.hex(), "as_float": [round(x, 6) for x in
                                   struct.unpack("<%df" % (len(raw) // 4), raw[:len(raw) // 4 * 4])]}
                    report["extensions"].append(f[:-4])
            if a.keep_programs:
                if frag is not None:
                    program["fragment"] = frag
                if vouts is not None:
                    program["vertex_outputs"] = vouts
            e = emitter(d, em, n, tex_ids, mesh_ref, program, ext)
            e["material"]["shader"] = shader_type(d, e["samplers"], frag, vouts) or {
                "type": "sprite", "color": "modulate", "alpha": "texture", "fresnel": False, "alpha_test": False}
            e["material"]["bloom"] = e.pop("_bloom")
            ty = e["material"]["shader"]["type"]
            report["shader_types"][ty] = report["shader_types"].get(ty, 0) + 1
            emitters.append(e)
            report["emitters"] += 1
        pkg = {"geno_fx": FORMAT_VERSION, "name": st,
               "source": {"format": "eft2/VFXB (Nintendo), via EffectLibrary", "set": st},
               "textures": textures, "meshes": meshes, "emitters": emitters}
        json.dump(pkg, open(os.path.join(a.out, st + ".gfx.json"), "w"), indent=1)
        summary[st] = report
        print("%s: %d emitters, %d textures, %d meshes, %d fragment programs translated, %d kept as listings, "
              "shader types %s, extensions %s" % (st, report["emitters"], len(textures), report["meshes"],
                                 report["translated_programs"], report["kept_listings"], report["shader_types"],
                                 sorted(set(report["extensions"]))))
    if os.path.exists(tmp):
        os.remove(tmp)
    json.dump(summary, open(os.path.join(a.out, "summary.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
