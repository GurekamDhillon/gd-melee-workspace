#!/usr/bin/env python3
"""The Courier's menu and HUD art, rendered from its own model. ORIGINAL art: nothing here reads a disc or any third-party asset.

    python ports/vanilla-original/ui_art.py <courier build dir> <out dir>

<courier build dir> is the output of tools/geno/build_courier.sh (it holds mesh_<costume>.json, the model the engine files are built from).
For every costume this writes, as PNG:

    GnCourier_icon.png              64x56    the character select tile (the default costume's head and shoulders)
    GnCourier_csp_<costume>.png     136x188  the portrait, a three-quarter view
    GnCourier_stock_<costume>.png   32x32    the HUD stock icon (the head)

then the caller turns them into .gxtex with pc/tools/png2gx.py (build_courier.sh does). It is a small z-buffered software renderer
(numpy): flat lights, nearest texels, 4x4 supersampling. It is placeholder-grade by design: the owner is to choose the real look.
"""
import base64
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SS = 4  # supersampling per axis


def load(mesh_path):
    m = json.loads(Path(mesh_path).read_text())
    tex = m["textures"][0]
    rgba = np.frombuffer(base64.b64decode(tex["rgba"]), dtype=np.uint8).reshape(tex["h"], tex["w"], 4)
    tris = []
    for d in m["dobjs"]:
        for t in d["tris"]:
            tris.append([(v["p"], v["n"], v["uv"]) for v in t])
    return rgba, tris


def rotate_y(p, angle):
    c, s = math.cos(angle), math.sin(angle)
    return (c * p[0] + s * p[2], p[1], -s * p[0] + c * p[2])


def render(rgba, tris, yaw_deg, view, size, margin=0.06):
    """view: (xmin, xmax, ymin, ymax) in model units that the canvas shows; size: (w, h) in pixels. Returns RGBA uint8 (h, w, 4)."""
    w, h = size
    W, H = w * SS, h * SS
    zbuf = np.full((H, W), -1e9, dtype=np.float32)
    color = np.zeros((H, W, 4), dtype=np.float32)
    xmin, xmax, ymin, ymax = view
    sx, sy = W / (xmax - xmin), H / (ymax - ymin)
    scale = min(sx, sy)
    ox = (W - (xmax - xmin) * scale) / 2.0
    oy = (H - (ymax - ymin) * scale) / 2.0
    yaw = math.radians(yaw_deg)
    light = np.array([0.35, 0.55, 0.75], dtype=np.float32)
    light /= np.linalg.norm(light)
    th, tw = rgba.shape[:2]
    for tri in tris:
        pts = []
        for p, n, uv in tri:
            q = rotate_y(p, yaw)
            nn = rotate_y(n, yaw)
            pts.append(((q[0] - xmin) * scale + ox, (ymax - q[1]) * scale + oy, q[2], nn, uv))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1 = max(int(math.floor(min(xs))), 0), min(int(math.ceil(max(xs))), W - 1)
        y0, y1 = max(int(math.floor(min(ys))), 0), min(int(math.ceil(max(ys))), H - 1)
        if x1 < x0 or y1 < y0:
            continue
        ax, ay = pts[0][0], pts[0][1]
        bx, by = pts[1][0], pts[1][1]
        cx, cy = pts[2][0], pts[2][1]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        l0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        l1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        l2 = 1.0 - l0 - l1
        inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        if not inside.any():
            continue
        z = l0 * pts[0][2] + l1 * pts[1][2] + l2 * pts[2][2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        win = inside & (z > sub)
        if not win.any():
            continue
        u = l0 * pts[0][4][0] + l1 * pts[1][4][0] + l2 * pts[2][4][0]
        v = l0 * pts[0][4][1] + l1 * pts[1][4][1] + l2 * pts[2][4][1]
        tx = np.clip((u * tw).astype(np.int32), 0, tw - 1)
        ty = np.clip((v * th).astype(np.int32), 0, th - 1)
        texel = rgba[ty, tx].astype(np.float32)
        nrm = l0[..., None] * np.array(pts[0][3], dtype=np.float32) + l1[..., None] * np.array(pts[1][3], dtype=np.float32) + \
            l2[..., None] * np.array(pts[2][3], dtype=np.float32)
        length = np.linalg.norm(nrm, axis=-1, keepdims=True)
        nrm = nrm / np.maximum(length, 1e-6)
        shade = (0.55 + 0.45 * np.clip(np.abs(nrm @ light), 0.0, 1.0))[..., None]  # two-sided: the model is single-sided and the view is a pose
        texel[..., :3] *= shade
        texel[..., 3] = 255.0
        region = color[y0:y1 + 1, x0:x1 + 1]
        region[win] = texel[win]
        sub[win] = z[win]
    img = color.reshape(h, SS, w, SS, 4).mean(axis=(1, 3))
    cov = (color[..., 3] > 0).reshape(h, SS, w, SS).mean(axis=(1, 3))
    out = np.zeros((h, w, 4), dtype=np.uint8)
    rgb = np.where(cov[..., None] > 0, img[..., :3] / np.maximum(cov[..., None], 1e-6), 0.0)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(cov * 255.0, 0, 255).astype(np.uint8)
    return out


def bounds(tris, yaw_deg):
    yaw = math.radians(yaw_deg)
    pts = np.array([rotate_y(p, yaw) for t in tris for p, _, _ in t])
    return pts[:, 0].min(), pts[:, 0].max(), pts[:, 1].min(), pts[:, 1].max()


def fit(view_box, aspect, pad):
    """grow (xmin, xmax, ymin, ymax) to the canvas aspect (w/h) and add a margin of `pad` of the height."""
    xmin, xmax, ymin, ymax = view_box
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    hh = (ymax - ymin) * (1 + pad)
    ww = (xmax - xmin) * (1 + pad)
    if ww / hh < aspect:
        ww = hh * aspect
    else:
        hh = ww / aspect
    return (cx - ww / 2, cx + ww / 2, cy - hh / 2, cy + hh / 2)


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    src, out = Path(argv[1]), Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for mesh in sorted(src.glob("mesh_*.json")):
        costume = mesh.stem[len("mesh_"):]
        rgba, tris = load(mesh)
        yaw = -28.0
        xmin, xmax, ymin, ymax = bounds(tris, yaw)
        height = ymax - ymin
        # portrait: the whole figure
        view = fit((xmin, xmax, ymin, ymax), 136.0 / 188.0, 0.06)
        Image.fromarray(render(rgba, tris, yaw, view, (136, 188))).save(out / ("GnCourier_csp_%s.png" % costume))
        # stock icon: the head (the top quarter of the figure), a little turned. The crop is the head's own bounds at that turn.
        head_bot = ymax - 0.25 * height
        pts = np.array([rotate_y(p, math.radians(-18.0)) for t in tris for p, _, _ in t])
        pts = pts[pts[:, 1] >= head_bot]
        hb = (pts[:, 0].min(), pts[:, 0].max(), pts[:, 1].min(), pts[:, 1].max())
        view = fit(hb, 1.0, 0.08)
        Image.fromarray(render(rgba, tris, -18.0, view, (32, 32))).save(out / ("GnCourier_stock_%s.png" % costume))
        if costume == "default":
            # select tile: head and shoulders
            pts = np.array([rotate_y(p, math.radians(-18.0)) for t in tris for p, _, _ in t])
            pts = pts[pts[:, 1] >= ymax - 0.42 * height]
            tb = (pts[:, 0].min(), pts[:, 0].max(), pts[:, 1].min(), pts[:, 1].max())
            view = fit(tb, 64.0 / 56.0, 0.06)
            Image.fromarray(render(rgba, tris, -18.0, view, (64, 56))).save(out / "GnCourier_icon.png")
        made.append(costume)
    print("ui_art: costumes %s -> %s" % (", ".join(made), out))
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
