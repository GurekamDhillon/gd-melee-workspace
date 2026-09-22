"""Simulate GX texture quantisation on the built PNGs, before a converter exists.

    python pipeline/quantise_check.py

This is a *format* simulation, not a converter: it answers "does this art
survive RGB5A3 / CI8" so the art can be fixed while it is still cheap.

RGB5A3 is per-texel, two encodings chosen by the top bit:
    MSB=1 -> opaque,      RGB555   (32 levels per channel, no alpha)
    MSB=0 -> translucent, RGB444 + A3 (16 levels per channel, 8 alpha levels)
So opaque interiors quantise to 5 bits and only alpha-blended texels drop to
4 bits. That split is why RGB5A3 is the right call for panel_bg and the wrong
one for anything whose soft edge matters.

Deliberately NOT applied: any sRGB->linear transform. GX samples texels raw;
a converter that colour-manages on the way in will wash the art out.
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")


def _q(chan, levels):
    """Quantise 0-255 to `levels` steps and expand back, as hardware does."""
    n = levels - 1
    return np.round(np.round(chan / 255.0 * n) / n * 255.0)


def rgb5a3(img):
    a = np.asarray(img.convert("RGBA")).astype("float64")
    out = a.copy()
    opaque = a[..., 3] == 255

    # opaque texels: RGB555
    for c in range(3):
        out[..., c] = np.where(opaque, _q(a[..., c], 32), _q(a[..., c], 16))
    out[..., 3] = np.where(opaque, 255.0, _q(a[..., 3], 8))
    return Image.fromarray(out.clip(0, 255).astype("uint8"), "RGBA")


def ci8(img):
    """256-colour palette, as CI8 would. Alpha kept separately (IA-style
    palettes exist; this measures the colour loss, which is the real risk)."""
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    pal = rgba.convert("RGB").quantize(colors=256, method=Image.MEDIANCUT,
                                       dither=Image.NONE).convert("RGB")
    pal.putalpha(alpha)
    return pal


def report(name, orig, quant, amp=8):
    o = np.asarray(orig.convert("RGBA")).astype("int16")
    q = np.asarray(quant.convert("RGBA")).astype("int16")
    opaque = o[..., 3] == 255
    d = np.abs(o[..., :3] - q[..., :3])
    dmax = int(d.max())
    dmean = float(d[opaque].mean()) if opaque.any() else 0.0
    cols_o = len(np.unique(o.reshape(-1, 4), axis=0))
    cols_q = len(np.unique(q.reshape(-1, 4), axis=0))
    print("  %-10s max delta %3d   mean delta %5.2f   colours %5d -> %-5d"
          % (name, dmax, dmean, cols_o, cols_q))
    return dmax, dmean, cols_q


def hatch_contrast(img, box):
    """The hatch is a ~14/255 white overlay on cobalt. If quantisation
    collapses that delta the stripes vanish; if it rounds it apart unevenly
    the stripes band. Measure the surviving separation inside a flat area."""
    a = np.asarray(img.convert("RGB")).astype("float64")
    x0, y0, x1, y1 = box
    patch = a[y0:y1, x0:x1].reshape(-1, 3)
    lum = patch @ np.array([0.2126, 0.7152, 0.0722])
    lo, hi = np.percentile(lum, 10), np.percentile(lum, 90)
    uniq = len(np.unique(patch, axis=0))
    return hi - lo, uniq


def main():
    checks = [
        ("panel_bg", "RGB5A3", rgb5a3),
        ("panel_bg", "CI8", ci8),
        ("btn_play_hover", "RGB5A3", rgb5a3),   # shows why text wants RGBA8
        ("frame_corner_tl", "RGB5A3", rgb5a3),
        ("cursor_hand", "RGB5A3", rgb5a3),
    ]
    dst = os.path.join(OUT, "quantise")
    os.makedirs(dst, exist_ok=True)

    # flat interior of the panel, away from trim/rivets/tab
    HATCH_BOX = (480, 260, 780, 420)

    print("Simulated GX quantisation (no sRGB transform, straight alpha):\n")
    last = None
    for name, fmt, fn in checks:
        src = os.path.join(OUT, "2x", name + ".png")
        orig = Image.open(src).convert("RGBA")
        quant = fn(orig)
        print("%s  ->  %s" % (name, fmt))
        report(fmt, orig, quant)

        if name == "panel_bg":
            sep_o, u_o = hatch_contrast(orig, HATCH_BOX)
            sep_q, u_q = hatch_contrast(quant, HATCH_BOX)
            print("  hatch      luma separation %.2f -> %.2f   "
                  "distinct colours in patch %d -> %d"
                  % (sep_o, sep_q, u_o, u_q))

        quant.save(os.path.join(dst, "%s_%s.png" % (name, fmt.lower())))

        # amplified difference, so banding is visible rather than argued about
        o = np.asarray(orig.convert("RGB")).astype("int16")
        q = np.asarray(quant.convert("RGB")).astype("int16")
        diff = (np.abs(o - q) * 8).clip(0, 255).astype("uint8")
        Image.fromarray(diff, "RGB").save(
            os.path.join(dst, "%s_%s_diff8x.png" % (name, fmt.lower())))
        print()

    print("wrote %s" % os.path.relpath(dst, ROOT))


if __name__ == "__main__":
    sys.exit(main())
