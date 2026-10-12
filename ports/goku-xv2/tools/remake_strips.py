"""Join lua/remake_strip.lua screenshots into one strip per move and one sheet per group (local, XV2-derived art: never committed).

    python ports/goku-xv2/tools/remake_strips.py [EVIDENCE_ROOT]    default .omo/evidence (kame_run.py copies the shots there)
Writes _build/goku-xv2/remake-strips/<group>_<move>.png and <group>.png (the move strips stacked, with the move names).
"""
import re
import sys
from pathlib import Path
from PIL import Image, ImageDraw

PORT = Path(__file__).resolve().parents[1]
ROOT = PORT.parents[1]
src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / '.omo/evidence'
out = ROOT / '_build/goku-xv2/remake-strips'
out.mkdir(parents=True, exist_ok=True)
CROP = (0.28, 0.12, 0.72, 0.88)   # the middle of the frame where Goku is
shots = {}
for p in src.rglob('rs_*_*.png'):
    m = re.match(r'rs_([a-z]+)_(.+)_(\d\d)\.png', p.name)
    if m:
        shots.setdefault((m[1], m[2]), {})[int(m[3])] = p
groups = {}
for (g, mv), frames in sorted(shots.items()):
    ims = []
    for i in sorted(frames):
        im = Image.open(frames[i]).convert('RGB')
        w, h = im.size
        ims.append(im.crop((int(w * CROP[0]), int(h * CROP[1]), int(w * CROP[2]), int(h * CROP[3]))).resize((220, 300)))
    strip = Image.new('RGB', (220 * len(ims), 300), (20, 20, 24))
    for k, im in enumerate(ims):
        strip.paste(im, (220 * k, 0))
    strip.save(out / f'{g}_{mv}.png')
    groups.setdefault(g, []).append((mv, strip))
for g, items in groups.items():
    sheet = Image.new('RGB', (max(s.width for _, s in items), 318 * len(items)), (20, 20, 24))
    d = ImageDraw.Draw(sheet)
    for k, (mv, s) in enumerate(items):
        sheet.paste(s, (0, 318 * k + 18))
        d.text((6, 318 * k + 2), mv, fill=(240, 220, 120))
    sheet.save(out / f'{g}.png')
    print(g, len(items), 'moves ->', out / f'{g}.png')
