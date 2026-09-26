#!/usr/bin/env python3
"""trail_magic_models.py - models for Sora's magic articles (Firaga, Blizzaga, Thundaga's cloud and bolt).

    python ports/ir/tools/trail_magic_models.py --template <a Melee costume .dat> -o <mod>/files

WHY PROCEDURAL. Ultimate draws the magic with PARTICLE EFFECTS, not models: trail_fire / _ice /
_cloud / _thunder have no model folder, their effect scripts are EFFECT_FOLLOW of .eff emitters
(checked in our acmd dump), and the only trail weapon meshes are the taunt's `flower` and the Final
Smash `box` (the gate). So these are ORIGINAL shapes made here (no game data in the meshes or the
textures), sized from the dump's numbers: the fireball's radius is its hitbox size 3.8, the shard
its 2.0 / map-collision 1.4, the bolt its capsule height 10. They go through fighterbuild like any
exported mesh (neutral mesh JSON -> a costume-style .dat whose root joint is the article's symbol);
the template costume only lends its material setup (lighting / TEV) and is read at build time.

Writes GnTrailFire.dat, GnTrailIce.dat, GnTrailCloud.dat, GnTrailBolt.dat (symbols
GnTrail<Name>_joint) and prints what it built. The article's travel is +X in the world; an item
faces with its Y rotation (HSD_JObjSetFacingDirItem), so the model's forward is +Z.
"""
import argparse
import base64
import glob
import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
IDENT_IBM = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]


def texture(name, inner, outer, size=32, alpha_edge=255):
    """A radial gradient (inner colour at the centre of the UV square -> outer at its edge)."""
    px = bytearray()
    for y in range(size):
        for x in range(size):
            d = min(1.0, math.hypot(x + 0.5 - size / 2, y + 0.5 - size / 2) / (size / 2))
            c = [int(inner[k] + (outer[k] - inner[k]) * d) for k in range(3)]
            px += bytes(c + [int(255 + (alpha_edge - 255) * d)])
    return {"name": name, "w": size, "h": size, "fmt": "CMPR" if alpha_edge >= 250 else "RGBA8",
            "rgba": base64.b64encode(bytes(px)).decode()}


def icosphere(r, sx=1.0, sy=1.0, sz=1.0, sub=2, center=(0, 0, 0)):
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    v = [tuple(c / math.sqrt(sum(x * x for x in p)) for c in p) for p in v for _ in [0]]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
         (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5),
         (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(sub):
        nf, cache = [], {}
        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                p = [(v[a][i] + v[b][i]) / 2 for i in range(3)]
                l = math.sqrt(sum(x * x for x in p))
                v.append(tuple(x / l for x in p))
                cache[k] = len(v) - 1
            return cache[k]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    tris = []
    for tri in f:
        tv = []
        for i in tri:
            n = v[i]
            p = [center[0] + n[0] * r * sx, center[1] + n[1] * r * sy, center[2] + n[2] * r * sz]
            nn = [n[0] / sx, n[1] / sy, n[2] / sz]
            l = math.sqrt(sum(x * x for x in nn))
            tv.append({"p": p, "n": [x / l for x in nn], "w": [[1, 1.0]], "uv": [0.5 + n[0] * 0.45, 0.5 + n[1] * 0.45]})
        tris.append(tv)
    return tris


def prism(points_bottom, y0, y1, taper=1.0):
    """A vertical prism / spike over a polygon (the bolt)."""
    tris = []
    n = len(points_bottom)
    for i in range(n):
        a, b = points_bottom[i], points_bottom[(i + 1) % n]
        pa0, pb0 = [a[0], y0, a[1]], [b[0], y0, b[1]]
        pa1, pb1 = [a[0] * taper, y1, a[1] * taper], [b[0] * taper, y1, b[1] * taper]
        nx, nz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        l = math.hypot(nx, nz) or 1
        nrm = [nx / l, 0, nz / l]
        mk = lambda p, u, vv: {"p": p, "n": nrm, "w": [[1, 1.0]], "uv": [u, vv]}
        tris.append([mk(pa0, 0.1, 0.9), mk(pb0, 0.9, 0.9), mk(pb1, 0.9, 0.1)])
        tris.append([mk(pa0, 0.1, 0.9), mk(pb1, 0.9, 0.1), mk(pa1, 0.1, 0.1)])
    return tris


def mesh(name, dobjs, textures):
    return {"fighter": "trail_" + name, "costume": "c00",
            "joints": [{"name": "TopN", "parent": -1, "scale": [1, 1, 1], "rot": [0, 0, 0], "trans": [0, 0, 0], "ibm": IDENT_IBM},
                       {"name": "Body", "parent": 0, "scale": [1, 1, 1], "rot": [0, 0, 0], "trans": [0, 0, 0], "ibm": IDENT_IBM}],
            "dobjs": [dict({"index": i, "object": name, "subindex": i, "material": name, "group": None,
                            "rigid_bone": None, "coords": ["TexCoord0"], "maps": ["TexCoord"],
                            "wrap": [["ClampToEdge", "ClampToEdge"]], "lit": True, "spec": None, "env": None,
                            "cull": "Cull_Outside", "layers": []}, **d) for i, d in enumerate(dobjs)],
            "textures": textures, "stats": {}}


def models():
    out = {}
    # Firaga: the fireball, radius = its hitbox size 3.8; a hot core fading to red
    out["Fire"] = mesh("Fire", [{"textures": ["fire"], "xlu": False, "tris": icosphere(3.8)}],
                       [texture("fire", (255, 250, 170), (230, 70, 10))])
    # Blizzaga: a shard 2.0 wide (the first hitbox), 5 long along the travel (+Z)
    out["Ice"] = mesh("Ice", [{"textures": ["ice"], "xlu": True, "tris": icosphere(2.0, 0.6, 0.6, 1.4, sub=0)}],
                      [texture("ice", (240, 255, 255), (90, 170, 255), alpha_edge=170)])
    # Thundaga's cloud: three flattened puffs, 13 wide
    puffs = icosphere(4.0, 1.0, 0.55, 0.8, 1, (-4.5, 0, 0)) + icosphere(5.0, 1.0, 0.6, 0.9, 1, (0, 0.8, 0)) + \
        icosphere(4.0, 1.0, 0.55, 0.8, 1, (4.5, 0, 0))
    out["Cloud"] = mesh("Cloud", [{"textures": ["cloud"], "xlu": False, "tris": puffs}],
                        [texture("cloud", (150, 150, 165), (70, 70, 85))])
    # the bolt: a tapering column from the article (its origin, the hitbox) up 10 (the capsule's y2)
    hexa = [(math.cos(k * math.pi / 3) * 1.8, math.sin(k * math.pi / 3) * 1.8) for k in range(6)]
    out["Bolt"] = mesh("Bolt", [{"textures": ["bolt"], "xlu": True, "tris": prism(hexa, 0.0, 12.0, 1.8)}],
                       [texture("bolt", (255, 255, 230), (255, 230, 60), alpha_edge=150)])
    return out


def fire_core(dump):
    """Firaga's core from Ultimate's own primitive emitter `sphere1` (P_TrailFireBullet, decoded by
    EffectLibrary): its texture (ef_brave_mask02, BNTX) and colours - Color0 (1.00, 0.59, 0.15) where the mask
    is bright, Color1 (1.00, 0.13, 0.04) where it is dark, x ColorScale 1.5 - baked into the sphere's texture.
    The primitive mesh itself (G3PR) is not decoded: the sphere stands in for it (radius 3.0, INFERRED)."""
    import numpy as np
    from PIL import Image
    import trail_vfx_melee as V
    em = os.path.join(dump, "P_TrailFireBullet", "sphere1")
    d = json.load(open(os.path.join(em, "EmitterData.json")))
    C, S = d["ParticleColor"], d["EmitterStatic"]
    c0 = np.array([C["Color0R"], C["Color0G"], C["Color0B"]]) * S["ColorScale"]
    c1 = np.array([C["Color1R"], C["Color1G"], C["Color1B"]]) * S["ColorScale"]
    name, img = V.bntx(os.path.join(em, "%d.bntx" % d["Sampler1"]["TextureID"]))
    a = np.asarray(img.resize((32, 32), Image.LANCZOS)).astype(float) / 255.0
    m = a[..., 0:1]
    rgb = np.clip((c1 * (1 - m) + c0 * m) * 255, 0, 255).astype(np.uint8)
    px = np.concatenate([rgb, np.full((32, 32, 1), 255, np.uint8)], -1)
    tex = {"name": "fire_core", "w": 32, "h": 32, "fmt": "CMPR", "rgba": base64.b64encode(px.tobytes()).decode()}
    m = mesh("FireCore", [{"textures": ["fire_core"], "xlu": False, "tris": icosphere(3.0)}], [tex])
    # emit joints (depth-first 2 and 3): P_TrailFireBullet's EmitterInfo.TransZ 2.3 (fire1, flare1) and 6.0
    # (fireline1), forward along the travel (+Z) - Geno's "effects" attach generators to them
    for nm, z in (("Emit23", 2.3), ("Emit60", 6.0)):
        m["joints"].append({"name": nm, "parent": 0, "scale": [1, 1, 1], "rot": [0, 0, 0], "trans": [0, 0, z],
                            "ibm": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, -z]})
    return m, name


def fire_core_real(dump, prims):
    """Firaga's core as Ultimate draws it: P_TrailFireBullet's four PRIMITIVE emitters, their own meshes
    (the emitters' bfres, dumped to <prims>/<emitter>.prim.json by the BfresLibrary dumper - see
    _research/ultimate-particles.md 5.5), each on its own billboarded joint (VertexTransformMode 0 =
    billboard), scaled by ParticleScale, coloured / faded the way each emitter's disassembled fragment
    shader combines (5.4), baked into the texture and the vertex colour:
      sphere1 (210)      rgb = lerp(Color1, Color0, mask02.R) x ColorScale; alpha = smoothstep(0.1, 0.5,
                         |n.z|) x Alpha0 (the view-facing fresnel term, n.z in billboard space)
      spherering1 (208)  rgb = vertex x Color0 x ColorScale; alpha = brave_fire00.G x Alpha0
      circle2 (214)      rgb = lerp(Color1, Color0, line12.R) x vertex x ColorScale; alpha = line12.G x vertex a
      flare1 (215)       rgb = lerp(Color1, Color0, grade00.R) x vertex; alpha = grade00.G x vertex a x Alpha0
                         x Alpha1; ADDITIVE (BlendType 1)
    NOT carried: the UV distortion by the indirect textures, the ring's colour-key animation (its key at
    t = 0.5 is baked), the vertex-alpha animation. The spins (RotateAddZ) are Geno "spins" on these joints."""
    import numpy as np
    from PIL import Image
    import trail_vfx_melee as V
    fx = os.path.join(dump, "P_TrailFireBullet")

    def em(n):
        return json.load(open(os.path.join(fx, n, "EmitterData.json")))

    def tex(n, sampler):
        d = em(n)
        return V.bntx(os.path.join(fx, n, "%d.bntx" % d["Sampler%d" % sampler]["TextureID"]))[1]

    def b64(rgba):
        return base64.b64encode(np.clip(rgba, 0, 255).astype(np.uint8).tobytes()).decode()
    joints = [{"name": "TopN", "parent": -1, "scale": [1, 1, 1], "rot": [0, 0, 0], "trans": [0, 0, 0], "ibm": IDENT_IBM},
              {"name": "Body", "parent": 0, "scale": [1, 1, 1], "rot": [0, 0, 0], "trans": [0, 0, 0], "ibm": IDENT_IBM}]
    for nm, z in (("Emit23", 2.3), ("Emit60", 6.0)):
        joints.append({"name": nm, "parent": 0, "scale": [1, 1, 1], "rot": [0, 0, 0], "trans": [0, 0, z],
                       "ibm": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, -z]})
    dobjs, textures, spins, rep = [], [], [], {}
    for name in ("sphere1", "spherering1", "circle2", "flare1"):
        d = em(name)
        S, C, Sc, I = d["EmitterStatic"], d["ParticleColor"], d["ParticleScale"], d["EmitterInfo"]
        cs = S["ColorScale"]
        c0 = np.array(V.curve_at(V.keys(S, "Color0", "NumColor0Keys"), 0.5) if C["Color0Type"] != "Constant"
                      else (C["Color0R"], C["Color0G"], C["Color0B"]))
        c1 = np.array((C["Color1R"], C["Color1G"], C["Color1B"]))
        prim = json.load(open(os.path.join(prims, name + ".prim.json")))[0]
        pos = np.array(prim["attrs"]["_p0"])[:, :3]
        nrm = np.array(prim["attrs"]["_n0"])[:, :3]
        uv = np.array(prim["attrs"]["_u0"])[:, :2]
        vc = np.array(prim["attrs"]["_c0"]) if "_c0" in prim["attrs"] else np.ones((len(pos), 4))
        size = 64
        if name == "sphere1":
            m = np.asarray(tex(name, 1).resize((size, size), Image.LANCZOS)).astype(float)[..., 0:1] / 255.0
            rgb = (c1 * (1 - m) + c0 * m) * cs * 255
            a = np.full((size, size, 1), 255.0)
            nz = np.abs(nrm[:, 2] / np.maximum(1e-6, np.linalg.norm(nrm, axis=1)))
            lo, hi = S["FresnelAlphaParam1"], S["FresnelAlphaParam2"]
            t = np.clip((nz - lo) / max(1e-6, hi - lo), 0, 1)
            va = np.clip(t * t * (3 - 2 * t) * min(1.0, C["Alpha0"]), 0, 1)
            vcols = np.stack([np.ones(len(pos))] * 3 + [va], 1)
        elif name == "spherering1":
            g = np.asarray(tex(name, 1).resize((size, size), Image.LANCZOS)).astype(float)[..., 1:2] / 255.0
            rgb = np.ones((size, size, 3)) * c0 * cs * 255
            a = g * min(1.0, C["Alpha0"]) * 255
            vcols = vc
        else:
            arr = np.asarray(tex(name, 1 if name == "circle2" else 0).resize((size, size), Image.LANCZOS)).astype(float) / 255.0
            r, g = arr[..., 0:1], arr[..., 1:2]
            rgb = (c1 * (1 - r) + c0 * r) * cs * 255
            a = g * (C["Alpha0"] * C["Alpha1"] if name == "flare1" else 1.0) * 255
            vcols = vc
        textures.append({"name": name, "w": size, "h": size, "fmt": "RGBA8", "rgba": b64(np.concatenate([rgb, a], -1))})
        j = len(joints)
        sc = Sc["ScaleX"]
        tz = I["TransZ"]
        joints.append({"name": name, "parent": 0, "scale": [sc, sc, sc], "rot": [0, 0, 0], "trans": [0, 0, tz],
                       "billboard": True,
                       "ibm": [1 / sc, 0, 0, 0, 0, 1 / sc, 0, 0, 0, 0, 1 / sc, -tz / sc]})
        idx = prim["indices"]
        tris = []
        for k in range(0, len(idx), 3):
            tv = []
            for q in idx[k:k + 3]:
                tv.append({"p": [float(pos[q][0] * sc), float(pos[q][1] * sc), float(pos[q][2] * sc + tz)],
                           "n": [float(x) for x in nrm[q]], "w": [[j, 1.0]],
                           "uv": [float(uv[q][0]), float(uv[q][1])], "c": [float(x) for x in vcols[q]]})
            tris.append(tv)
        smp = d["Sampler1" if name in ("spherering1", "circle2") else "Sampler0"]
        wrap = {"Mirror": "MirroredRepeat", "Repeat": "Repeat"}.get(smp["WrapU"], "ClampToEdge")
        dobjs.append({"textures": [name], "xlu": True, "tris": tris, "vcolor": True, "lit": False,
                      "blend": "add" if d["RenderState"]["BlendType"] == 1 else "normal",
                      "wrap": [[wrap, wrap]], "cull": "Cull_None"})
        if S["RotateAddZ"]:
            spins.append({"joint": j, "z": round(S["RotateAddZ"], 6)})
        rep[name] = {"joint": j, "verts": len(pos), "tris": len(tris), "scale": sc, "trans_z": tz,
                     "radius": float(np.abs(pos[:, :2]).max() * sc), "spin": S["RotateAddZ"]}
    m = mesh("FireCore", dobjs, textures)
    m["joints"] = joints
    return m, spins, rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True, help="a Melee costume .dat (material setup only)")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--vfx-dump", help="EffectLibrary dump of ef_trail.eff: also build GnTrailFireCore.dat from sphere1")
    ap.add_argument("--prims", help="dir of <emitter>.prim.json (bfres dumps): FireCore from Ultimate's primitive meshes")
    a = ap.parse_args()
    fb = glob.glob(os.path.join(HERE, "fighterbuild", "bin", "**", "fighterbuild.exe"), recursive=True)
    if not fb:
        sys.exit("build ports/ir/tools/fighterbuild first (dotnet build -c Release)")
    os.makedirs(a.out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        todo = models()
        if a.vfx_dump and a.prims:
            todo["FireCore"], spins, rep = fire_core_real(a.vfx_dump, a.prims)
            json.dump(spins, open(os.path.join(a.out, "..", "firecore_spins.json"), "w"))
            print("FireCore from Ultimate's primitive meshes: %s" % json.dumps(rep))
        elif a.vfx_dump:
            todo["FireCore"], src = fire_core(a.vfx_dump)
            print("FireCore: sphere1's colours and texture %s" % src)
        for name, m in todo.items():
            mp = os.path.join(tmp, name + ".json")
            json.dump(m, open(mp, "w"))
            dat = os.path.join(a.out, "GnTrail%s.dat" % name)
            sym = "GnTrail%s_joint" % name
            r = subprocess.run([fb[0], "build", mp, a.template, dat, sym], capture_output=True, text=True)
            if r.returncode:
                sys.exit("fighterbuild failed for %s: %s%s" % (name, r.stdout[-600:], r.stderr[-600:]))
            ntri = sum(len(d["tris"]) for d in m["dobjs"])
            print("%-6s %4d tris -> %s (%d bytes, symbol %s)" % (name, ntri, dat, os.path.getsize(dat), sym))


if __name__ == "__main__":
    main()
