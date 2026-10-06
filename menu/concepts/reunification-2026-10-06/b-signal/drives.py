"""Renders the REAL Envoy drive models to transparent PNGs, headlessly, from the committed generator's geometry.

It imports `melee/pc/scripts/examples/envoy_drives/tools/make_drives.py` (read only), takes the very same triangles and the
very same atlas colour ramps (body colour plus emissive glow), flat-shades them with one fixed light and a painter sort,
which is what `gd.kit.model` does in the engine (orthographic camera, fixed light, painter sort). No game, no window.
Pillow only. Deterministic.
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]  # .../menu/concepts/reunification-2026-10-06/b-signal -> repo root of the workspace
TOOLS = ROOT / "melee" / "pc" / "scripts" / "examples" / "envoy_drives" / "tools"

sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS))
import make_drives as md  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

BASE, GLOW = md.atlas_pixels()
LIGHT = md.norm((0.25, 1.0, 0.55))
BODIES = ["red", "green", "blue", "yellow", "purple", "white"]
RARITY = ["magic", "rare", "unique"]


def _tex(buf, u, v):
    x = min(md.W - 1, max(0, int(u * md.W)))
    y = min(md.H - 1, max(0, int(v * md.H)))
    o = (y * md.W + x) * 4
    return buf[o], buf[o + 1], buf[o + 2]


def render(mesh, size=256, yaw=22, pitch=20, margin=0.04):
    S = 3
    n = size * S
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    verts, idx = md.vertices(mesh)
    ya, pa = math.radians(yaw), math.radians(pitch)

    def xf(p):
        x = p[0] * math.cos(ya) + p[2] * math.sin(ya)
        z = -p[0] * math.sin(ya) + p[2] * math.cos(ya)
        y = p[1] * math.cos(pa) - z * math.sin(pa)
        z2 = p[1] * math.sin(pa) + z * math.cos(pa)
        return x, y, z2

    sc = n * (1 - 2 * margin) / 2 / md.HALF
    tris = []
    for i in range(0, len(idx), 3):
        vs = [verts[j] for j in idx[i:i + 3]]
        nn = vs[0][5:8]
        nx = nn[0] * math.cos(ya) + nn[2] * math.sin(ya)
        nz = -nn[0] * math.sin(ya) + nn[2] * math.cos(ya)
        ny = nn[1] * math.cos(pa) - nz * math.sin(pa)
        nz2 = nn[1] * math.sin(pa) + nz * math.cos(pa)
        lam = max(0.0, nx * LIGHT[0] + ny * LIGHT[1] + nz2 * LIGHT[2])
        ps = [xf(v[:3]) for v in vs]
        area = (ps[1][0] - ps[0][0]) * (ps[2][1] - ps[0][1]) - (ps[2][0] - ps[0][0]) * (ps[1][1] - ps[0][1])
        if abs(area) < 1e-9:
            continue
        c = [0.0, 0.0, 0.0]
        for v in vs:
            b = _tex(BASE, v[3], v[4])
            g = _tex(GLOW, v[3], v[4])
            for k in range(3):
                c[k] += min(255, (b[k] + g[k]) * (0.36 + 0.64 * lam)) / 3
        depth = sum(p[2] for p in ps) / 3
        tris.append((depth, ps, tuple(int(min(255, x)) for x in c)))
    tris.sort(key=lambda t: t[0])
    for depth, ps, c in tris:
        d.polygon([(n / 2 + p[0] * sc, n / 2 - p[1] * sc) for p in ps], fill=c + (255,),
                  outline=c + (255,))
    return im.resize((size, size), Image.LANCZOS)


def build(out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    models = md.build_all()
    for b in BODIES:
        body = models["drive_" + b][0]
        render(body).save(out_dir / ("drive_%s.png" % b), optimize=True)
        for r in RARITY:
            m = md.Mesh()
            m.extend(body)
            m.extend(models["drive_ring_" + r][0])
            render(m).save(out_dir / ("drive_%s_%s.png" % (b, r)), optimize=True)
    return sorted(p.name for p in out_dir.glob("*.png"))


if __name__ == "__main__":
    print(build(HERE / "assets" / "drives"))
