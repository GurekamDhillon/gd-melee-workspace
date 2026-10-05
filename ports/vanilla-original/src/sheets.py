"""Contact-sheet helpers (system Python + Pillow). Usage: python sheets.py static <raw_dir> <out_dir>"""
import sys, os
from PIL import Image, ImageDraw

def grid(files, labels, cols, out, cell=None, pad=4, bg=(205, 208, 214), label_h=14, maxw=1024):
    ims = [Image.open(f).convert("RGB") for f in files]
    if cell is None: cell = ims[0].size
    cw, ch = cell
    rows = (len(ims) + cols - 1) // cols
    W, H = cols * (cw + pad) + pad, rows * (ch + label_h + pad) + pad
    sheet = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        if im.size != (cw, ch): im = im.resize((cw, ch), Image.LANCZOS)
        x, y = pad + (i % cols) * (cw + pad), pad + (i // cols) * (ch + label_h + pad)
        sheet.paste(im, (x, y + label_h))
        d.text((x + 2, y + 1), labels[i] if labels else "", fill=(20, 20, 30))
    if W > maxw:
        sheet = sheet.resize((maxw, int(H * maxw / W)), Image.LANCZOS)
    sheet.save(out, optimize=True)
    return out

def static(raw, out):
    os.makedirs(out, exist_ok=True)
    j = lambda n: os.path.join(raw, n)
    grid([j(f"turn_{v}.png") for v in ("front", "left", "back", "three_quarter")], ["front", "side (left)", "back", "three-quarter"], 4,
         os.path.join(out, "turnaround.png"), maxw=1024)
    grid([j(f"cos_{n}.png") for n in ("default", "red", "blue", "green")], ["default", "red", "blue", "green"], 4,
         os.path.join(out, "colourways.png"), maxw=1024)
    grid([j(f"sil_{v}.png") for v in ("front", "left", "three_quarter")], ["front", "side", "3/4"], 3, os.path.join(out, "silhouettes.png"), maxw=1024)
    grid([j("wire_front.png"), j("wire_three_quarter.png")], ["wire front", "wire 3/4"], 2, os.path.join(out, "wireframe.png"), maxw=1024)
    grid([j("small_front.png"), j("small_three_quarter.png")], ["~120px front", "~120px 3/4"], 2, os.path.join(out, "small_size.png"), cell=(160, 160), maxw=640)

def index(raw, name, out, cols=6, cell=None, maxw=1600, a=0, b=None):
    import json
    ix = json.load(open(os.path.join(raw, f"index_{name}.json")))[a:b]
    return grid([os.path.join(raw, e["file"]) for e in ix], [e["label"] for e in ix], cols, out, cell=cell, maxw=maxw)

if __name__ == "__main__":
    if sys.argv[1] == "static": static(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "index": index(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 6, a=int(sys.argv[6]) if len(sys.argv) > 6 else 0, b=int(sys.argv[7]) if len(sys.argv) > 7 else None)
