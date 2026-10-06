"""Draws the REAL Envoy drive models as flat SVG tokens, headless, from the committed model data.

Reads melee/pc/scripts/examples/envoy_drives/models/*.gxmesh (GXMS v2) and the two atlases (GXTX v1 RGBA8),
projects the triangles orthographically (painter sort, one fixed light, like gd.kit.model), colours each face from
the atlas ramp (base * light + glow, like the in-game screen model), and writes assets/drive_<name>.svg.
No outside data. Run by build.py.
"""
import math
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
MODELS = os.path.join(ROOT, "melee", "pc", "scripts", "examples", "envoy_drives", "models")
W = H = 128


def load_atlas(name):
    b = open(os.path.join(MODELS, name), "rb").read()
    img = b[64:]
    px = [[(0, 0, 0)] * W for _ in range(H)]
    o = 0
    for ty in range(0, H, 4):
        for tx in range(0, W, 4):
            ar = img[o:o + 32]
            gb = img[o + 32:o + 64]
            o += 64
            for i in range(16):
                x, y = tx + (i % 4), ty + (i // 4)
                px[y][x] = (ar[i * 2 + 1], gb[i * 2], gb[i * 2 + 1])
    return px


def load_mesh(name):
    b = open(os.path.join(MODELS, name + ".gxmesh"), "rb").read()
    _, _, nv, ni, ex, ey, ez, voff, ioff = struct.unpack(">4sIIIfffII", b[:36])
    verts = [struct.unpack(">8f", b[voff + i * 32: voff + i * 32 + 32]) for i in range(nv)]
    idx = struct.unpack(">%dH" % ni, b[ioff: ioff + ni * 2])
    return verts, idx


def render(body, ring=None, yaw=30.0, pitch=24.0, size=100.0, atlas=None):
    base, glow = atlas
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    light = (-0.45, 0.75, 0.5)
    ln = math.sqrt(sum(c * c for c in light))
    light = tuple(c / ln for c in light)
    polys = []

    def add(name, bias):
        verts, idx = load_mesh(name)
        for t in range(0, len(idx), 3):
            vs = [verts[idx[t + k]] for k in range(3)]
            pts = []
            for v in vs:
                x, y, z = v[0], v[1], v[2]
                x1, z1 = x * cy + z * sy, -x * sy + z * cy
                y2, z2 = y * cp - z1 * sp, y * sp + z1 * cp
                pts.append((x1, y2, z2))
            nx, ny, nz = vs[0][5], vs[0][6], vs[0][7]
            n1x, n1z = nx * cy + nz * sy, -nx * sy + nz * cy
            n2y, n2z = ny * cp - n1z * sp, ny * sp + n1z * cp
            # triangle area on screen (skip degenerate padding tris)
            ax, ay = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
            bx, by = pts[2][0] - pts[0][0], pts[2][1] - pts[0][1]
            if abs(ax * by - ay * bx) < 1e-5:
                continue
            u = sum(v[3] for v in vs) / 3
            vv = sum(v[4] for v in vs) / 3
            tx_, ty_ = min(W - 1, int(u * W)), min(H - 1, int(vv * H))
            bc, gc = base[ty_][tx_], glow[ty_][tx_]
            lit = max(0.0, n1x * light[0] + n2y * light[1] + n2z * light[2])
            sh = 0.50 + 0.50 * lit
            col = tuple(min(255, int(bc[k] * sh + gc[k] * 0.85)) for k in range(3))
            depth = sum(p[2] for p in pts) / 3 + bias
            polys.append((depth, pts, col))

    if ring:
        add(ring, -50.0)       # the overlay is drawn FIRST: depth bias pushes it behind the body
    add(body, 0.0)
    polys.sort(key=lambda p: p[0])
    k = size / 2.0 / 2.9
    out = []
    for _, pts, col in polys:
        d = " ".join("%.2f,%.2f" % (50 + p[0] * k, 50 - p[1] * k) for p in pts)
        c = "#%02x%02x%02x" % col
        out.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="0.5" stroke-linejoin="round"/>' % (d, c, c))
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">%s</svg>' % "".join(out)


def build(assets_dir):
    atlas = (load_atlas("drive_atlas.gxtex"), load_atlas("drive_atlas.glow.gxtex"))
    done = []
    for fam in ("red", "green", "blue", "yellow", "purple", "white"):
        svg = render("drive_" + fam, atlas=atlas)
        open(os.path.join(assets_dir, "drive_%s.svg" % fam), "w", encoding="utf-8").write(svg)
        done.append(fam)
    for fam, ring, tag in (("red", "drive_ring_magic", "magic"), ("blue", "drive_ring_rare", "rare"),
                           ("yellow", "drive_ring_unique", "unique"), ("purple", "drive_ring_magic", "magic"),
                           ("green", "drive_ring_rare", "rare")):
        svg = render("drive_" + fam, ring=ring, atlas=atlas)
        open(os.path.join(assets_dir, "drive_%s_%s.svg" % (fam, tag)), "w", encoding="utf-8").write(svg)
    return done


if __name__ == "__main__":
    print(build(os.path.join(HERE, "assets")))
