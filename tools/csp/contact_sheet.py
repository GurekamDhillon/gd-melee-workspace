"""Contact sheets of rendered UI previews (the `final/` folders `render_ui.py` writes).

    python tools/csp/contact_sheet.py OUT.png LABEL=RUN_DIR [LABEL=RUN_DIR ...] [--costume 0]

One row per label, one column per package field (stock, icon, portrait, results), each
drawn at the retail pixel size scaled by a whole factor so a 24x24 stock icon is visible,
on a mid-grey checker so transparency and outlines read. RUN_DIR is the folder holding
`final/` (or `final/` itself). Output stays under _build; nothing is published.
"""
import argparse
from pathlib import Path
import sys

FIELDS = ('stock', 'icon', 'portrait', 'results')
SCALE = {'stock': 5, 'icon': 3, 'portrait': 2, 'results': 3}


def final_dir(path):
    path = Path(path)
    return path / 'final' if (path / 'final').is_dir() else path


def sheet(rows, costume=0, extra=()):
    """rows: list of (label, run_dir). extra: list of (label, {field: png path}) for reference images."""
    from PIL import Image, ImageDraw
    entries = []
    for label, run in rows:
        base = final_dir(run)
        entries.append((label, {f: base / ('c%03d-%s.png' % (costume, f)) for f in FIELDS}))
    entries.extend(extra)
    pad, label_w, head = 12, 150, 22
    widths = {f: Image.open(next(p[f] for _, p in entries if p.get(f) and Path(p[f]).is_file())).width * SCALE[f]
              for f in FIELDS}
    heights = {f: Image.open(next(p[f] for _, p in entries if p.get(f) and Path(p[f]).is_file())).height * SCALE[f]
               for f in FIELDS}
    row_h = max(heights.values()) + pad
    width = label_w + sum(widths.values()) + pad * (len(FIELDS) + 1)
    out = Image.new('RGB', (width, head + row_h * len(entries) + pad), (96, 96, 100))
    draw = ImageDraw.Draw(out)
    x = label_w + pad
    for f in FIELDS:
        draw.text((x, 4), f, fill=(255, 255, 255))
        x += widths[f] + pad
    for r, (label, paths) in enumerate(entries):
        y = head + r * row_h
        draw.text((6, y + 6), label, fill=(255, 255, 255))
        x = label_w + pad
        for f in FIELDS:
            w, h = widths[f], heights[f]
            tile = Image.new('RGB', (w, h), (140, 140, 146))
            for ty in range(0, h, 16):
                for tx in range(0, w, 16):
                    if (tx // 16 + ty // 16) % 2:
                        tile.paste((120, 120, 126), (tx, ty, min(tx + 16, w), min(ty + 16, h)))
            p = paths.get(f)
            if p and Path(p).is_file():
                image = Image.open(p).convert('RGBA')
                image = image.resize((image.width * SCALE[f], image.height * SCALE[f]), Image.Resampling.NEAREST)
                tile.paste(image, (0, 0), image)
            out.paste(tile, (x, y))
            x += w + pad
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out', type=Path)
    ap.add_argument('rows', nargs='+', help='LABEL=RUN_DIR')
    ap.add_argument('--costume', type=int, default=0)
    args = ap.parse_args(argv)
    rows = []
    for item in args.rows:
        label, _, run = item.partition('=')
        if not run:
            ap.error('rows are LABEL=RUN_DIR')
        rows.append((label, run))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet(rows, args.costume).save(args.out)
    print(args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
