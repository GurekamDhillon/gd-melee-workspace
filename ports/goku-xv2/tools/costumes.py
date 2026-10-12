"""Goku costume atlases: recolours of the converted atlas (colour classes, no new art).

The converted atlas is a 5x5 grid of 192px tiles (xv2_to_artist.build_mesh). XV2 gives one exportable model (partset 0); the other BCS
partsets name models that are not in the export, so costumes here are palette recolours of the gi (orange class) and undershirt, belt,
wristbands and boots (navy class). Skin, hair and eyes never change. Config: ports/goku-xv2/costumes.json (colours only, no art).
Output atlases stay under _build (never committed):
    python ports/goku-xv2/tools/costumes.py _build/goku-xv2/author-source          # writes atlas_<name>.png, patches fighter.json
"""
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

CONFIG = Path(__file__).resolve().parents[1] / 'costumes.json'
TILE, STEP, OFF = 192, 204, 6


def tile_box(i):
    x, y = (i % 5) * STEP + OFF, (i // 5) * STEP + OFF
    return x, y, x + TILE, y + TILE


def classify(rgb):
    """orange / navy / other, from a tile's mean colour (opaque pixels, ink excluded by the median)."""
    r, g, b = (float(c) / 255 for c in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s > 0.7 and 0.04 < h < 0.12:
        return 'orange'
    if s > 0.5 and 0.55 < h < 0.7 and v < 0.5:
        return 'navy'
    return 'other'


def tile_classes(atlas):
    px = np.asarray(atlas.convert('RGB'))
    out = {}
    for i in range(25):
        x0, y0, x1, y1 = tile_box(i)
        t = px[y0:y1, x0:x1].reshape(-1, 3)
        med = np.median(t, axis=0)
        out[i] = classify(med)
    return out


def recolour(atlas, classes, ops):
    a = np.asarray(atlas.convert('RGBA')).astype(np.float32) / 255
    res = a.copy()
    for cls, op in ops.items():
        idx = [i for i, c in classes.items() if c == cls]
        if not idx:
            continue
        lums = []
        for i in idx:
            x0, y0, x1, y1 = tile_box(i)
            t = a[y0:y1, x0:x1, :3]
            lums.append((t * [0.299, 0.587, 0.114]).sum(-1).mean())
        class_lum = float(np.mean(lums))
        for i in idx:
            x0, y0, x1, y1 = tile_box(i)
            t = a[y0:y1, x0:x1, :3]
            if 'tint' in op:
                lum = (t * [0.299, 0.587, 0.114]).sum(-1, keepdims=True)
                o = np.asarray(op['tint'], np.float32) / 255 * (lum / max(class_lum, 1e-4))
            else:
                hsv = np.stack(np.vectorize(colorsys.rgb_to_hsv)(t[..., 0], t[..., 1], t[..., 2]), -1)
                hsv[..., 0] = op['hue'] / 360.0
                hsv[..., 1] = np.clip(hsv[..., 1] * op.get('sat', 1.0), 0, 1)
                hsv[..., 2] = np.clip(hsv[..., 2] * op.get('val', 1.0), 0, 1)
                o = np.stack(np.vectorize(colorsys.hsv_to_rgb)(hsv[..., 0], hsv[..., 1], hsv[..., 2]), -1)
            res[y0:y1, x0:x1, :3] = np.clip(o, 0, 1)
    return Image.fromarray((res * 255 + 0.5).astype(np.uint8), 'RGBA')


def build(author_dir):
    author = Path(author_dir)
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    base = Image.open(author / 'atlas.png')
    classes = tile_classes(base)
    entries = []
    for c in cfg['costumes']:
        name = c['name']
        if c.get('ops'):
            img = recolour(base, classes, c['ops'])
            fname = 'atlas_%s.png' % name
            img.save(author / fname)
        else:
            fname = 'atlas.png'
        e = {'name': name, 'label': c['label'], 'texture': fname}
        if c.get('team'):
            e['team'] = c['team']
        entries.append(e)
    return entries, classes


def apply(author):
    author = Path(author)
    entries, classes = build(author)
    fj = author / 'fighter.json'
    d = json.loads(fj.read_text(encoding='utf-8'))
    d['costumes'] = entries
    fj.write_text(json.dumps(d, indent=1), encoding='utf-8')
    print('costumes:', [e['name'] for e in entries], 'classes:', {k: sum(1 for v in classes.values() if v == k) for k in ('orange', 'navy', 'other')})


def main(argv):
    apply(argv[0])


if __name__ == '__main__':
    main(sys.argv[1:])
