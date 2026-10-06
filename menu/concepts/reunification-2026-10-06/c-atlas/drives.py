"""The real drive models as flat-shaded SVG, from the committed generator's own geometry.

make_drives.py (melee/pc/scripts/examples/envoy_drives/tools) builds each mesh from plain geometry and an atlas of colour
ramps. We import it read-only, take its triangles (build_all) and its ramp table (ROW_LIST), rotate to a three-quarter
view, light them (lit material, emission 1.0 as in the mod's material.json) and write one SVG <g> per model, painter
sorted. Nothing is traced or captured: this is the mod's own data drawn headlessly in 2D.
"""
import importlib.util
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _load():
    # walk up until we find melee/pc/scripts/examples/envoy_drives
    p = HERE
    for _ in range(8):
        cand = os.path.join(p, "melee", "pc", "scripts", "examples", "envoy_drives", "tools", "make_drives.py")
        if os.path.exists(cand):
            spec = importlib.util.spec_from_file_location("make_drives", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod, cand
        p = os.path.dirname(p)
    raise SystemExit("make_drives.py not found")


def _rot(p, yaw, pitch):
    x, y, z = p
    c, s = math.cos(yaw), math.sin(yaw)
    x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(pitch), math.sin(pitch)
    y, z = y * c - z * s, y * s + z * c
    return (x, y, z)


def _lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def shade(md, mesh, yaw=0.55, pitch=0.32, ring=False):
    light = (-0.45, 0.75, 0.55)
    ln = math.sqrt(sum(v * v for v in light))
    light = tuple(v / ln for v in light)
    polys = []
    for p0, p1, p2, ts, rw in mesh.tris:
        if rw == "glass":
            continue
        a, b, c = (_rot(p, yaw, pitch) for p in (p0, p1, p2))
        ux, uy, uz = (b[i] - a[i] for i in range(3))
        vx, vy, vz = (c[i] - a[i] for i in range(3))
        n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
        nl = math.sqrt(sum(v * v for v in n))
        if nl < 1e-9:
            continue
        n = tuple(v / nl for v in n)
        # camera looks down -z in this frame (+z toward viewer): drop faces turned away
        if n[2] < -0.02 and not ring:
            continue
        dark, main, glow, gpow = md.ROW_LIST[md.ROWS[rw]]
        t = sum(ts) / 3.0
        base = _lerp(dark, main, min(1.0, (t * 1.15) ** 0.8))
        ndl = max(0.0, n[0] * light[0] + n[1] * light[1] + n[2] * light[2])
        k = 0.52 + 0.62 * ndl
        g = tuple(v * (t ** gpow) for v in glow)
        col = tuple(min(255, int(base[i] * k + g[i] * 0.85)) for i in range(3))
        z = (a[2] + b[2] + c[2]) / 3
        polys.append((z, col, (a, b, c)))
    polys.sort(key=lambda q: q[0])
    out = []
    for z, col, pts in polys:
        d = " ".join("%.3f,%.3f" % (p[0], -p[1]) for p in pts)
        hx = "#%02x%02x%02x" % col
        out.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="0.03"/>' % (d, hx, hx))
    return "".join(out)


def build_defs():
    """Returns (svg defs string, info dict). One <g id="drv-<family>"> per family plus <g id="ring-*"> rarity overlays."""
    md, path = _load()
    models = md.build_all()
    parts = []
    tris = {}
    for name, (mesh, alpha) in models.items():
        if name == "drive_glass":
            continue
        short = name.replace("drive_", "")
        if short.startswith("ring_"):
            gid = "ring-" + short[5:]
            parts.append('<g id="%s">%s</g>' % (gid, shade(md, mesh, ring=True)))
        else:
            gid = "drv-" + short
            parts.append('<g id="%s">%s</g>' % (gid, shade(md, mesh)))
        tris[gid] = len(mesh.tris)
    return "".join(parts), {"source": path, "tris": tris}


if __name__ == "__main__":
    d, info = build_defs()
    print(len(d), info)
