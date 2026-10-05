"""Stage 1: the Courier's mesh, textures, materials and armature, built procedurally (headless Blender).

    blender --background --python build_model.py -- [out_dir]

Writes <out>/stage1_model.blend and <out>/tex/costume_<name>.png. Everything here is original geometry made
from primitives in bmesh: ellipse-section tubes (limbs, torso, boots), ellipsoid patches (head, fists, shoulder
caps), prisms (crest fin) and boxes. No outside meshes, textures or add-ons.
Technique credit: Blender (blender.org); the bmesh and glTF-exporter documentation.
"""
import bpy, bmesh, sys, os, math, json
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else C.OUT
os.makedirs(os.path.join(OUT, "tex"), exist_ok=True)

# ---------------------------------------------------------------- palette
CELLS = ["helmet", "helmet_dark", "tunic", "trouser", "trim", "glove", "boot", "accent",
         "accent_stripe", "emblem", "metal", "pauldron", "leather", "sole", "white", "shadow"]
CI = {n: i for i, n in enumerate(CELLS)}
def rgb(h): return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
PAL = {
    "default": dict(helmet="#e8dcc0", helmet_dark="#5c6670", tunic="#1f7f86", trouser="#27353f", trim="#d9a441",
                    glove="#f0e6cf", boot="#3b2e2a", accent="#f08a24", accent_stripe="#fff1c9", emblem="#ffd36b",
                    metal="#aeb7bd", pauldron="#e8dcc0", leather="#7a4a2a", sole="#171313", white="#ffffff",
                    shadow="#101820", eye="#ffb02e"),
    "red": dict(helmet="#e8dcc0", helmet_dark="#5c6670", tunic="#c0282d", trouser="#3a2428", trim="#f1c34a",
                glove="#f0e6cf", boot="#3b2427", accent="#f4c542", accent_stripe="#ffffff", emblem="#ffe27a",
                metal="#aeb7bd", pauldron="#e8dcc0", leather="#7a4a2a", sole="#171313", white="#ffffff",
                shadow="#201014", eye="#ff5a3c"),
    "blue": dict(helmet="#e8dcc0", helmet_dark="#5c6670", tunic="#2754c9", trouser="#222c46", trim="#e9eef7",
                 glove="#f0e6cf", boot="#2a2f3f", accent="#f2f6ff", accent_stripe="#7ab8ff", emblem="#bfe0ff",
                 metal="#aeb7bd", pauldron="#e8dcc0", leather="#6f4a30", sole="#131318", white="#ffffff",
                 shadow="#0e1426", eye="#6fd6ff"),
    "green": dict(helmet="#e8dcc0", helmet_dark="#5c6670", tunic="#2f8f3c", trouser="#233426", trim="#d7e65a",
                  glove="#f0e6cf", boot="#2f2e20", accent="#b6ef3a", accent_stripe="#fff7b0", emblem="#e4ff7a",
                  metal="#aeb7bd", pauldron="#e8dcc0", leather="#6f5030", sole="#131610", white="#ffffff",
                  shadow="#10200f", eye="#a6ff5c"),
}
AW, AH = 128, 64   # atlas: 4x4 flat cells of 16 px at the left (64x64), the visor face panel at the right (64x64)
VISOR_PART = 99

def cell_uv(i):
    col, row = i % 4, i // 4          # row counted from the bottom of the image (Blender v up)
    return ((col + 0.5) * 16 / AW, (row + 0.5) * 16 / AH)

def make_texture(name):
    p = PAL[name]
    img = np.zeros((AH, AW, 4), np.float32); img[..., 3] = 1     # row 0 = bottom of the image
    for i, n in enumerate(CELLS):
        col, row = i % 4, i // 4
        img[row * 16:(row + 1) * 16, col * 16:(col + 1) * 16, :3] = rgb(p[n])
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    top = np.array(rgb(p["shadow"])) * 2.2; bot = np.array(rgb(p["shadow"]))
    g = (1.0 - yy / 63.0)[..., None]       # top of the panel (high rows) is lighter
    panel = top * (1 - g) + bot * g
    eye = np.array(rgb(p["eye"]))
    for cx in (19, 45):          # two slit eyes, tilted toward the nose
        tilt = (cx - 32) * 0.16
        d = ((xx - cx) / 9.0) ** 2 + ((yy - 31 + tilt) / 4.6) ** 2
        core = np.clip(1.4 - d * 1.2, 0, 1)[..., None]
        glow = np.clip(1.0 - d / 3.5, 0, 1)[..., None] * 0.35
        panel = panel * (1 - core) + eye * core
        panel = panel + eye * glow * 0.6
    sweep = np.clip(1 - np.abs((xx + yy * 0.6) - 38) / 5.0, 0, 1)[..., None] * 0.10
    img[:, 64:, :3] = np.clip(panel + sweep, 0, 1)
    return img

# ---------------------------------------------------------------- mesh builder
class MB:
    def __init__(self):
        self.bm = bmesh.new()
        self.dl = self.bm.verts.layers.deform.verify()
        self.cl = self.bm.faces.layers.int.new("cell")
        self.part = self.bm.faces.layers.int.new("part")
        self.gidx = {n: i for i, n in enumerate(C.DEFORM)}
    def vert(self, co, w):
        v = self.bm.verts.new(co)
        tot = sum(w.values())
        for b, x in w.items():
            v[self.dl][self.gidx[b]] = x / tot
        return v
    def face(self, vs, cell, part=0):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f[self.cl] = CI[cell]; f[self.part] = part
        return f
    def setw(self, v, w):
        for b, x in w.items(): v[self.dl][self.gidx[b]] = x

def sup(c, p):
    return math.copysign(abs(c) ** p, c)

def frame_for(d, hint=None):
    d = d.normalized()
    h = Vector((0, -1, 0)) if hint is None else Vector(hint)
    if abs(d.dot(h)) > 0.9:
        h = Vector((0, 0, 1))
    side = d.cross(h).normalized()
    fwd = side.cross(d).normalized()
    return side, fwd

def tube(mb, rings, cell, nseg=8, p=0.85, cap0=None, cap1=None, hint=None, part=0, cell_of_seg=None, phase=0.0):
    """rings: list of (center, rx, ry, weights). cap0/cap1: None, 'flat' or ('dome', frac)."""
    P = [Vector(r[0]) for r in rings]
    rv = []
    for i, (c, rx, ry, w) in enumerate(rings):
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)])
        side, fwd = frame_for(d, hint)
        vs = []
        for k in range(nseg):
            a = 2 * math.pi * k / nseg + phase
            co = P[i] + side * rx * sup(math.cos(a), p) + fwd * ry * sup(math.sin(a), p)
            vs.append(mb.vert(co, w))
        rv.append(vs)
    for i in range(len(rv) - 1):
        cl = cell_of_seg[i] if cell_of_seg else cell
        for k in range(nseg):
            mb.face([rv[i][k], rv[i][(k + 1) % nseg], rv[i + 1][(k + 1) % nseg], rv[i + 1][k]], cl, part)
    for ring_i, cap in ((0, cap0), (len(rv) - 1, cap1)):
        if cap is None: continue
        c, rx, ry, w = rings[ring_i]
        nb = P[ring_i + (1 if ring_i == 0 else -1)]
        outward = (P[ring_i] - nb).normalized()
        frac = 0 if cap == "flat" else cap[1]
        cv = mb.vert(P[ring_i] + outward * max(rx, ry) * frac, w)
        for k in range(nseg):
            a, b = rv[ring_i][k], rv[ring_i][(k + 1) % nseg]
            mb.face([a, b, cv] if ring_i == len(rv) - 1 else [b, a, cv], cell, part)
    return rv

def ellipsoid(mb, center, radii, cell, wfunc, nlon=12, nlat=8, lon=(-180, 180), lat=(-90, 90), part=0):
    """UV-sphere patch. lon 0 = front (-Y), positive lon toward +X (the character's left); lat 0 = equator."""
    cx, cy, cz = center; rx, ry, rz = radii
    full = (lon[1] - lon[0]) >= 359.9
    nl = nlon if full else nlon + 1
    grid = []
    for j in range(nlat + 1):
        la = math.radians(lat[0] + (lat[1] - lat[0]) * j / nlat)
        pole = abs(abs(la) - math.pi / 2) < 1e-6
        row = []
        for i in range(1 if pole else nl):
            lo = math.radians(lon[0] + (lon[1] - lon[0]) * i / nlon)
            q = Vector((cx + rx * math.cos(la) * math.sin(lo), cy - ry * math.cos(la) * math.cos(lo), cz + rz * math.sin(la)))
            row.append(mb.vert(q, wfunc(q)))
        grid.append(row)
    def at(j, i):
        row = grid[j]
        return row[0] if len(row) == 1 else row[(i % nlon) if full else i]
    for j in range(nlat):
        for i in range(nlon):
            vs = [at(j, i), at(j, i + 1), at(j + 1, i + 1), at(j + 1, i)]
            uniq = []
            for v in vs:
                if v not in uniq: uniq.append(v)
            if len(uniq) >= 3:
                mb.face(uniq, cell, part)
    return grid

def box(mb, center, size, cell, w, bevel=0.0, rot=None, part=0):
    bm = mb.bm
    res = bmesh.ops.create_cube(bm, size=1.0)
    vs = res["verts"]
    m = Matrix.Translation(center) @ (rot.to_4x4() if rot else Matrix.Identity(4)) @ Matrix.Diagonal(Vector((size[0], size[1], size[2], 1)))
    for v in vs:
        v.co = m @ v.co
        mb.setw(v, w)
    for f in set(f for v in vs for f in v.link_faces):
        f[mb.cl] = CI[cell]; f[mb.part] = part
    if bevel > 0:
        edges = list(set(e for v in vs for e in v.link_edges))
        r = bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=1, affect="EDGES")
        for v in r["verts"]: mb.setw(v, w)
        for f in r["faces"]:
            f[mb.cl] = CI[cell]; f[mb.part] = part
    return vs

def cylinder(mb, center, axis, radius, depth, cell, w, seg=10, part=0):
    res = bmesh.ops.create_cone(mb.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=radius, radius2=radius, depth=depth)
    vs = res["verts"]
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    m = Matrix.Translation(center) @ q.to_matrix().to_4x4()
    for v in vs:
        v.co = m @ v.co
        mb.setw(v, w)
    for f in set(f for v in vs for f in v.link_faces):
        f[mb.cl] = CI[cell]; f[mb.part] = part
    return vs

def prism(mb, poly_yz, x0, x1, cell, w, part=0):
    A = [mb.vert((x0, y, z), w) for y, z in poly_yz]
    B = [mb.vert((x1, y, z), w) for y, z in poly_yz]
    n = len(A)
    for i in range(n):
        mb.face([A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]], cell, part)
    for ring, rev in ((A, True), (B, False)):
        f = mb.face(list(reversed(ring)) if rev else ring, cell, part)
        if f: bmesh.ops.triangulate(mb.bm, faces=[f])

# ---------------------------------------------------------------- weights helpers
def ssm(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)

def chain_weights(joints, bones, p, r):
    """Weights at arc position p along a chain; bones[i] owns [joints[i], joints[i+1]]; blend half-width r at inner joints."""
    for k in range(1, len(joints) - 1):
        s = joints[k]
        if abs(p - s) < r:
            t = ssm((p - s) / (2 * r) + 0.5)
            return {bones[k - 1]: 1 - t, bones[k]: t}
    for i in range(len(bones)):
        if joints[i] - 1e-6 <= p <= joints[i + 1] + 1e-6:
            return {bones[i]: 1.0}
    return {bones[-1]: 1.0}

def limb(mb, pts, bones, specs, cell, r=0.55, nseg=8, p=0.9, cap0=None, cap1=None, first=None):
    P = [Vector(x) for x in pts]
    L = [0.0]
    for i in range(1, len(P)): L.append(L[-1] + (P[i] - P[i - 1]).length)
    rings = []
    for n, (s, rx, ry) in enumerate(specs):
        s = max(0.0, min(L[-1], s))
        i = max(k for k in range(len(L) - 1) if L[k] <= s) if s < L[-1] else len(L) - 2
        pos = P[i].lerp(P[i + 1], (s - L[i]) / (L[i + 1] - L[i]))
        w = first if (n == 0 and first) else chain_weights(L, bones, s, r)
        rings.append((pos, rx, ry, w))
    return tube(mb, rings, cell, nseg=nseg, p=p, cap0=cap0, cap1=cap1)

# ---------------------------------------------------------------- build
def build():
    mb = MB()
    for side, sx in (("L", 1), ("R", -1)):
        V = lambda x, y, z: Vector((x * sx, y, z))
        # legs: trouser tube thigh+shin down into the boot shaft
        limb(mb, [V(1.05, 0, 5.6), V(1.05, 0, 3.3), V(1.05, 0, 1.25)], [f"thigh_{side}", f"shin_{side}"],
             [(0.0, .95, .95), (0.6, .9, .92), (1.4, 0.82, 0.82), (2.0, 0.78, 0.78), (2.3, 0.76, 0.76), (2.6, 0.75, 0.74),
              (3.0, 0.74, 0.72), (3.5, 0.74, 0.74), (4.3, 0.76, 0.76)],
             "trouser", r=0.6, nseg=8, cap0="flat", first={"hips": 0.5, f"thigh_{side}": 0.5})
        # boot shaft (shin, blended to the foot at the ankle) and cuff
        rings = [(V(1.05, .05, 2.75), 1.1, 1.05, {f"shin_{side}": 1}), (V(1.05, .05, 2.4), 1.03, 1.0, {f"shin_{side}": 1}),
                 (V(1.05, .05, 1.75), 0.98, 0.98, {f"shin_{side}": 1}),
                 (V(1.05, .05, 1.2), 1.0, 1.0, {f"shin_{side}": .5, f"foot_{side}": .5}),
                 (V(1.05, .05, 0.9), 1.0, 1.0, {f"foot_{side}": 1})]
        tube(mb, rings, "boot", nseg=8, p=0.8, cap0="flat")
        tube(mb, [(V(1.05, .05, 2.95), 1.16, 1.12, {f"shin_{side}": 1}), (V(1.05, .05, 2.55), 1.1, 1.06, {f"shin_{side}": 1})],
             "trim", nseg=8, p=0.8, cap0="flat", cap1="flat")
        # foot: ellipse tube along -Y, heel -> toe, foot/toe blend at the ball
        fr = []
        for (y, rxv, rz, cz) in ((0.95, .86, .62, .66), (0.45, 1.0, .68, .68), (-0.3, 1.05, .66, .66), (-1.1, 1.05, .6, .6),
                                 (-1.7, 1.0, .52, .54), (-2.3, .82, .42, .45), (-2.62, .5, .3, .4)):
            t = ssm((-y - 1.2) / 0.9)
            w = {f"foot_{side}": 1 - t, f"toe_{side}": t} if t > 0 else {f"foot_{side}": 1}
            fr.append((V(1.05, y, cz), rxv, rz, w))
        tube(mb, fr, "boot", nseg=8, p=0.8, cap0="flat", cap1="flat", hint=(0, 0, 1))
        sr = [(V(1.05, 0.95, 0.12), .9, .14, {f"foot_{side}": 1}), (V(1.05, -1.2, 0.12), 1.08, .14, {f"foot_{side}": .5, f"toe_{side}": .5}),
              (V(1.05, -2.5, 0.1), .55, .1, {f"toe_{side}": 1})]
        tube(mb, sr, "sole", nseg=8, p=0.7, cap0="flat", cap1="flat", hint=(0, 0, 1))
        # arms: sleeve tube, glove cuff, fist (palm + finger block + thumb), pauldron
        limb(mb, [V(1.9, 0, 7.75), V(3.07, 0, 6.25), V(4.18, 0, 4.83)], [f"upperarm_{side}", f"forearm_{side}"],
             [(0.0, .72, .7), (0.5, .72, .7), (1.0, .66, .64), (1.5, .64, .62), (1.8, .6, .58), (2.1, .58, .56), (2.4, .56, .54),
              (2.7, .56, .54), (3.0, .6, .58)],
             "tunic", r=0.55, nseg=8, cap0="flat", first={f"clavicle_{side}": .5, f"upperarm_{side}": .5})
        tube(mb, [(V(3.72, 0, 5.42), .72, .7, {f"forearm_{side}": 1}), (V(4.05, 0, 5.0), .9, .88, {f"forearm_{side}": .7, f"hand_{side}": .3}),
                  (V(4.3, 0, 4.68), .9, .88, {f"hand_{side}": 1})], "trim", nseg=8, cap0="flat", cap1="flat")
        ellipsoid(mb, V(4.52, 0, 4.4), (1.08, 1.0, 1.1), "glove", lambda q: {f"hand_{side}": 1}, nlon=8, nlat=5)
        ellipsoid(mb, V(4.72, -0.6, 4.1), (0.85, 0.7, 0.88), "glove", lambda q: {f"fingers_{side}": 1}, nlon=8, nlat=5)
        ellipsoid(mb, V(3.9, -0.7, 4.55), (0.38, 0.42, 0.5), "glove", lambda q: {f"thumb_{side}": 1}, nlon=6, nlat=4)
        ellipsoid(mb, V(2.1, 0, 7.8), (0.95, 1.0, 0.85), "pauldron", lambda q: {f"upperarm_{side}": .6, f"clavicle_{side}": .4},
                  nlon=10, nlat=5, lat=(-10, 90))
        tube(mb, [(V(2.1, 0, 7.5), 0.94, .98, {f"upperarm_{side}": 1}), (V(2.25, 0, 7.35), 0.86, .9, {f"upperarm_{side}": 1})],
             "trim", nseg=10, p=.9, cap0="flat", cap1="flat")
        cylinder(mb, V(1.86, 0.05, 9.95), (1, 0, 0), 0.72, 0.34, "helmet_dark", {"head": 1}, seg=10)
    # torso
    def bw(z): return chain_weights([5.0, 6.2, 7.2, 8.4], ["hips", "spine", "chest"], z, 0.55)
    torso = [(5.2, 1.45, 1.05), (5.65, 1.6, 1.12), (6.2, 1.35, 1.0), (6.7, 1.3, 0.98), (7.2, 1.55, 1.1), (7.7, 1.8, 1.2), (8.15, 1.45, 1.0)]
    rings = [(Vector((0, 0, z)), rx, ry, bw(z)) for z, rx, ry in torso]
    rings[-1] = (rings[-1][0], rings[-1][1], rings[-1][2], {"chest": .85, "neck": .15})
    tube(mb, rings, "tunic", nseg=10, p=0.8, cap0="flat", cap1=("dome", .25))
    tube(mb, [(Vector((0, 0, 5.85)), 1.68, 1.24, {"hips": 1}), (Vector((0, 0, 6.2)), 1.5, 1.12, {"hips": .6, "spine": .4})],
         "trim", nseg=10, p=.8, cap0="flat", cap1="flat")
    box(mb, (0, -1.33, 6.02), (.8, .28, .62), "metal", {"hips": 1}, bevel=0.07)
    box(mb, (0, -1.5, 6.02), (.4, .1, .32), "emblem", {"hips": 1}, bevel=0.03)
    box(mb, (0, -1.3, 7.6), (.85, .1, .85), "emblem", {"chest": 1}, rot=Matrix.Rotation(math.pi / 4, 3, "Y"))
    box(mb, (-1.95, 0.35, 5.35), (.9, 1.3, 1.1), "leather", {"hips": 1}, bevel=.12)
    box(mb, (-1.97, 0.35, 5.75), (1.0, 1.4, .35), "trim", {"hips": 1}, bevel=.07)
    tube(mb, [(Vector((0, 0, 7.95)), 1.25, 1.1, {"chest": 1}), (Vector((0, 0, 8.3)), 1.05, .95, {"neck": 1}), (Vector((0, 0, 8.65)), 1.0, .92, {"neck": 1})],
         "accent", nseg=10, p=.9, cap0="flat", cap1="flat")
    # head: helmet shell, visor patch (face panel), ear discs (above), crest fin
    hc = (0, -0.05, 10.05); hr = (1.8, 1.7, 1.65)
    def hw(q):
        t = ssm((q.z - 8.45) / 0.55)
        return {"head": t, "neck": 1 - t} if t < 1 else {"head": 1}
    ellipsoid(mb, hc, hr, "helmet", hw, nlon=14, nlat=8)
    ellipsoid(mb, hc, tuple(x * 1.035 for x in hr), "helmet_dark", lambda q: {"head": 1}, nlon=8, nlat=4,
              lon=(-56, 56), lat=(-22, 24), part=VISOR_PART)
    prism(mb, [(-1.1, 11.3), (-0.2, 11.9), (1.2, 12.25), (2.7, 12.05), (1.7, 11.2), (1.3, 10.4), (0.0, 11.0)], -0.13, 0.13, "accent", {"head": 1})
    # scarf: 4-bone ribbon, rectangular section (phase 45 degrees so the 4 corners make a rectangle)
    sb = ["scarf1", "scarf2", "scarf3", "scarf4"]
    SP = [Vector(C.BONE["scarf1"]["head"]), Vector(C.BONE["scarf1"]["tail"]), Vector(C.BONE["scarf2"]["tail"]),
          Vector(C.BONE["scarf3"]["tail"]), Vector(C.BONE["scarf4"]["tail"])]
    wid = [1.0, 1.15, 1.3, 1.4, 1.5]
    rr = []
    for i in range(5):
        w = {"neck": .5, "scarf1": .5} if i == 0 else ({"scarf4": 1} if i == 4 else {sb[i - 1]: .5, sb[i]: .5})
        rr.append((SP[i] + Vector((0, 0.05, 0)), wid[i] * 0.5 * 1.414, 0.28, w))
    tube(mb, rr, "accent", nseg=4, p=1.0, cap0="flat", cap1="flat", cell_of_seg=["accent", "accent_stripe", "accent", "accent_stripe"], phase=math.pi / 4)
    return mb, Vector(hc), hr

def finalize(mb, hc, hr):
    bm = mb.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # visor faces must point out of the head
    for f in bm.faces:
        if f[mb.part] == VISOR_PART and f.normal.dot(f.calc_center_median() - hc) < 0:
            f.normal_flip()
    for v in bm.verts:     # at most 4 influences, normalised
        d = v[mb.dl]
        items = sorted(((g, w) for g, w in d.items() if w > 1e-4), key=lambda t: -t[1])[:4]
        tot = sum(w for _, w in items)
        for g in list(d.keys()): del d[g]
        for g, w in items: d[g] = w / tot
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        if f[mb.part] == VISOR_PART:
            for l in f.loops:
                q = l.vert.co - hc
                lo = math.atan2(q.x, -q.y)
                la = math.atan2(q.z / hr[2], math.hypot(q.x / hr[0], q.y / hr[1]))
                uu = 0.5 + 0.5 * lo / math.radians(56)           # viewer's right = the character's left (+X)
                vv = 0.5 + 0.5 * la / math.radians(24)
                l[uvl].uv = (0.5 + 0.5 * (0.03 + 0.94 * uu), 0.03 + 0.94 * vv)
        else:
            cu = cell_uv(f[mb.cl])
            for l in f.loops: l[uvl].uv = cu
    me = bpy.data.meshes.new("CourierMesh")
    bm.to_mesh(me)
    bm.free()
    return me

def make_materials(me):
    mats = []
    for cos in C.COSTUMES:
        name = cos["name"]
        img = make_texture(name)
        path = os.path.join(OUT, "tex", f"costume_{name}.png")
        im = bpy.data.images.new(f"tex_{name}", AW, AH, alpha=False)
        im.pixels = img.ravel().tolist()
        im.filepath_raw = path; im.file_format = "PNG"; im.save()
        m = bpy.data.materials.new(f"mat_{name}")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = im; tex.interpolation = "Linear"
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.9
        bsdf.inputs["Metallic"].default_value = 0.0
        m.diffuse_color = (*rgb(PAL[name]["tunic"]), 1)
        m.use_fake_user = True
        mats.append(m)
    me.materials.append(mats[0])
    return mats

def make_armature():
    arm = bpy.data.armatures.new("CourierArmature")
    ob = bpy.data.objects.new("Courier_Armature", arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for b in C.BONES:
        e = arm.edit_bones.new(b["name"])
        e.head = b["head"]; e.tail = b["tail"]; e.roll = 0.0
        e.use_deform = b["deform"]
        eb[b["name"]] = e
    for b in C.BONES:
        if b["parent"]: eb[b["name"]].parent = eb[b["parent"]]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.display_type = "STICK"
    return ob

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = C.FPS
    mb, hc, hr = build()
    me = finalize(mb, hc, hr)
    mats = make_materials(me)
    ob = bpy.data.objects.new("Courier", me)
    sc.collection.objects.link(ob)
    for n in C.DEFORM: ob.vertex_groups.new(name=n)
    arm = make_armature()
    ob.parent = arm
    md = ob.modifiers.new("Armature", "ARMATURE"); md.object = arm
    bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(50))
    except Exception as e:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons)); print("smooth-by-angle unavailable:", e)
    arm["geno_roles"] = json.dumps({b["name"]: b["role"] for b in C.BONES})
    arm["geno_units"] = "1 unit = 1 Melee unit; authoring Z-up facing -Y; glTF Y-up facing +Z"
    sc.render.engine = "BLENDER_WORKBENCH"
    path = os.path.join(OUT, "stage1_model.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    print("STAGE1 verts", len(me.vertices), "tris", tris, "polys", len(me.polygons), "bones", len(C.BONES), "->", path)

main()
