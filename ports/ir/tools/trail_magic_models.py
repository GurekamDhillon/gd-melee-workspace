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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True, help="a Melee costume .dat (material setup only)")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    fb = glob.glob(os.path.join(HERE, "fighterbuild", "bin", "**", "fighterbuild.exe"), recursive=True)
    if not fb:
        sys.exit("build ports/ir/tools/fighterbuild first (dotnet build -c Release)")
    os.makedirs(a.out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, m in models().items():
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
