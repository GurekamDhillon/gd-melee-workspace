import sys, glob, os, json
from PIL import Image
d = sys.argv[1]; names = sys.argv[2].split(","); crop = tuple(int(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 else (280, 180, 1000, 680)
out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(d, "grid.png")
rows = []
for n in names:
    fs = sorted(glob.glob(os.path.join(d, n + "_[0-9]*.png")))
    ims = [Image.open(f).convert("RGB").crop(crop) for f in fs]
    if ims: rows.append(ims)
w = crop[2] - crop[0]; h = crop[3] - crop[1]; cols = max(len(r) for r in rows)
c = Image.new("RGB", (w * cols, h * len(rows)))
for y, r in enumerate(rows):
    for x, i in enumerate(r): c.paste(i, (x * w, y * h))
sc = min(1.0, 1600 / c.width); c = c.resize((int(c.width * sc), int(c.height * sc)))
c.save(out); print(out, c.size)
