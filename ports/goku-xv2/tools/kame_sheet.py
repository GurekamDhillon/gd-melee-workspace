"""Tile screenshots of a kame_strip run into one contact sheet, optionally cropped (zoomed crops of the hands / the beam).

    python ports/goku-xv2/tools/kame_sheet.py RUN_DIR OUT.png [--cols 6] [--scale 0.5] [--crop x0,y0,x1,y1] [--from N] [--to N] [--step K] [--min-t T]

RUN_DIR holds the PNGs (.omo/evidence/<name>/ after kame_run.py). Frames are labelled with the state and frame in the file name. --crop is in pixels of the
source image (1280x720 by default). Local evidence only; the sheets are not committed.
"""
import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True   # the last screenshot of a run can be cut off when the game quits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run'); ap.add_argument('out')
    ap.add_argument('--cols', type=int, default=6); ap.add_argument('--scale', type=float, default=0.5)
    ap.add_argument('--crop'); ap.add_argument('--step', type=int, default=1)
    ap.add_argument('--min-t', type=int, default=0, help='only shots with t >= this (the number after _t in the name)')
    ap.add_argument('--max-t', type=int, default=10 ** 9)
    ap.add_argument('--from', dest='lo', type=int, default=0); ap.add_argument('--to', dest='hi', type=int, default=10 ** 9)
    a = ap.parse_args()
    files = sorted(Path(a.run).glob('*.png'))
    sel = []
    for f in files:
        m = re.search(r'_t(\d+)_', f.name)
        t = int(m.group(1)) if m else 0
        if a.min_t <= t <= a.max_t:
            sel.append((t, f))
    sel = sel[a.lo:a.hi:a.step]
    if not sel:
        raise SystemExit('no frames')
    crop = tuple(int(v) for v in a.crop.split(',')) if a.crop else None
    tiles = []
    for t, f in sel:
        im = Image.open(f).convert('RGB')
        if crop:
            im = im.crop(crop)
        im = im.resize((max(1, int(im.width * a.scale)), max(1, int(im.height * a.scale))), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        label = re.sub(r'^.*?_t', 't', f.stem)
        d.rectangle((0, 0, im.width, 12), fill=(0, 0, 0))
        d.text((2, 0), label[:60], fill=(255, 255, 255))
        tiles.append(im)
    w, h = tiles[0].size
    rows = (len(tiles) + a.cols - 1) // a.cols
    sheet = Image.new('RGB', (w * a.cols, h * rows), (0, 0, 0))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % a.cols) * w, (i // a.cols) * h))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out)
    print(a.out, sheet.size, len(tiles), 'frames')


if __name__ == '__main__':
    main()
