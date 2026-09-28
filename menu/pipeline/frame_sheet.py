"""Contact sheet of the 9-slice frame at several panel sizes (reference only, not a deliverable).

    python pipeline/frame_sheet.py [--before DIR]      -> out/preview/frame_sheet.png

Composes panels as a 9-slice: the fill over the centre cells (never the corner cells), the edges stretched between the corners with the bottom and right ones mirrored, then
the four corners. Rows: the old pieces (from --before, a copy of an earlier out/2x), the new
square corners, the new cut corners. Sizes are 1x panel units, drawn at 2x.
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SIZES = ((136, 136), (240, 150), (360, 210), (560, 140))  # 1x units; 128 is the minimum (two corners)
BG = (10, 14, 24, 255)


def load(d, name):
    p = os.path.join(d, name + ".png")
    return Image.open(p).convert("RGBA") if os.path.exists(p) else None


def panel(d, w, h, corner="frame_corner_"):
    W, H = w * 2, h * 2
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c = {t: load(d, corner + t) for t in ("tl", "tr", "bl", "br")}
    eh, ev, fill = load(d, "frame_edge_h"), load(d, "frame_edge_v"), load(d, "frame_fill")
    cs = c["tl"].width
    if fill is not None:
        # the centre cells only (a plus shape): corner cells carry their own face
        img.alpha_composite(fill.resize((W - 2 * cs, H), Image.NEAREST), (cs, 0))
        img.alpha_composite(fill.resize((W, H - 2 * cs), Image.NEAREST), (0, cs))
    top = eh.resize((W - 2 * cs, eh.height), Image.NEAREST)
    img.alpha_composite(top, (cs, 0))
    img.alpha_composite(top.transpose(Image.FLIP_TOP_BOTTOM), (cs, H - eh.height))
    left = ev.resize((ev.width, H - 2 * cs), Image.NEAREST)
    img.alpha_composite(left, (0, cs))
    img.alpha_composite(left.transpose(Image.FLIP_LEFT_RIGHT), (W - ev.width, cs))
    img.alpha_composite(c["tl"], (0, 0))
    img.alpha_composite(c["tr"], (W - cs, 0))
    img.alpha_composite(c["bl"], (0, H - cs))
    img.alpha_composite(c["br"], (W - cs, H - cs))
    return img


def font(size):
    for name in (os.path.join(ROOT, "SourceSans3", "SourceSans3-Semibold.ttf"),
                 os.path.join(ROOT, "SourceSans3", "SourceSans3-Regular.ttf"), "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", help="a copy of an earlier out/2x (old frame pieces)")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "preview", "frame_sheet.png"))
    a = ap.parse_args()
    new = os.path.join(ROOT, "out", "2x")
    rows = []
    if a.before:
        rows.append(("before", a.before, "frame_corner_"))
    rows += [("after: square corners", new, "frame_corner_"),
             ("after: cut corners", new, "frame_cut_corner_")]
    gap, label_h = 48, 56
    row_h = max(h for _, h in SIZES) * 2
    W = gap + sum(w * 2 + gap for w, _ in SIZES)
    H = gap + len(rows) * (label_h + row_h + gap)
    sheet = Image.new("RGBA", (W, H), BG)
    dr = ImageDraw.Draw(sheet)
    f, fs = font(34), font(22)
    y = gap
    for title, d, corner in rows:
        dr.text((gap, y), title, fill=(242, 239, 228, 255), font=f)
        x = gap
        for w, h in SIZES:
            sheet.alpha_composite(panel(d, w, h, corner), (x, y + label_h))
            dr.text((x, y + label_h + h * 2 + 6), "%dx%d" % (w, h), fill=(125, 136, 166, 255), font=fs)
            x += w * 2 + gap
        y += label_h + row_h + gap
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    sheet.save(a.out)
    print("frame sheet ->", a.out)


if __name__ == "__main__":
    main()
