"""Iterate on the Kamehameha effects without a full package rebuild: regenerate the XV2 conversions, copy them into the built package,
run the offscreen frame-strip scenario and tile the screenshots into one contact sheet (all local, git-ignored _build / .omo output).

    python ports/goku-xv2/tools/kame_try.py [--tag NAME] [--hold 62] [--gap 4] [--every 2] [--skip-fx] [--cfg k=v ...]

Needs GW_MELEE / GW_BUILD_ROOT exported like kame_run.py (see KAMEHAMEHA.md). Sheet: _build/xv2-kame/sheets/<tag>.png.
"""
import argparse, shutil, subprocess, sys
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
WT = PORT.parents[1]
PKG = WT / '_build/goku-xv2/author-source/package/mods/goku-xv2/fx'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='try'); ap.add_argument('--hold', default='62'); ap.add_argument('--gap', default='4')
    ap.add_argument('--tail', default='110'); ap.add_argument('--every', type=int, default=1); ap.add_argument('--skip-fx', action='store_true'); ap.add_argument('--sheet-only', action='store_true'); ap.add_argument('--from', dest='frm', type=int, default=0); ap.add_argument('--to', dest='to', type=int, default=9999)
    ap.add_argument('--cols', type=int, default=4); ap.add_argument('--cell', type=int, default=480); ap.add_argument('--crop', default='0.12,0.28,0.78,0.78')
    ap.add_argument('--cfg', action='append', default=[]); ap.add_argument('--super', action='store_true', help='run a copy of the package whose full charge fires the Super (the ki gate is a combo-package feature)')
    a = ap.parse_args()
    if not a.skip_fx and not a.sheet_only:
        subprocess.run([sys.executable, str(PORT / 'tools/xv2_fx.py')], check=True)
        for d in (WT / '_build/goku-xv2/fx').glob('P_TrailGokuXKame*'):
            shutil.rmtree(PKG / d.name, ignore_errors=True)
            shutil.copytree(d, PKG / d.name)
    import os
    if a.super:
        mods = WT / '_build/goku-xv2/author-source/package/mods'
        cp = WT / '_build/xv2-kame/modcopy'
        shutil.rmtree(cp, ignore_errors=True)
        shutil.copytree(mods, cp)
        shutil.rmtree(cp / 'goku-xv2/fx', ignore_errors=True)
        shutil.copytree(PKG, cp / 'goku-xv2/fx')
        lua = cp / 'goku-xv2/lua/goku.lua'
        t = lua.read_text(encoding='utf-8')
        key = '  if c >= MID then ctx.go("KameFull"); return end'
        assert key in t
        lua.write_text(t.replace(key, '  if c >= FULL then ctx.go("KameSuper") return end' + chr(10) + key), encoding='utf-8')
        os.environ['KAME_MODS'] = str(cp)
    name = 'kame-' + a.tag
    cfg = ['hold=' + a.hold, 'gap=' + a.gap, 'tail=' + a.tail, 'tag=' + a.tag] + a.cfg
    cmd = [sys.executable, str(PORT / 'tools/kame_run.py'), 'kame_shots', 'KAME', '--name', name] + [x for c in cfg for x in ('--cfg', c)]
    if not a.sheet_only:
        r = subprocess.run(cmd, capture_output=True, text=True)
        print((r.stdout or '')[-1500:], (r.stderr or '')[-600:])
    ev = WT / '.omo/evidence' / name
    shots = sorted(ev.glob('*.png'))
    print(len(shots), 'screenshots in', ev)
    if not shots:
        return
    from PIL import Image, ImageDraw, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    pick = [p for p in shots if a.frm <= int(p.stem.split('_t')[1].split('_')[0]) <= a.to][::a.every]
    rows = (len(pick) + a.cols - 1) // a.cols
    fx0, fy0, fx1, fy1 = [float(x) for x in a.crop.split(',')]
    cw = a.cell; ch = int(cw * (fy1 - fy0) / (fx1 - fx0) * 9 / 16)
    sheet = Image.new('RGB', (a.cols * cw, rows * (ch + 12)), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    for i, p in enumerate(pick):
        im = Image.open(p).convert('RGB'); w, h = im.size
        im = im.crop((int(w * fx0), int(h * fy0), int(w * fx1), int(h * fy1))).resize((cw, ch), Image.LANCZOS)
        x, y = (i % a.cols) * cw, (i // a.cols) * (ch + 12)
        sheet.paste(im, (x, y + 12))
        d.text((x + 2, y), p.stem.split('_', 2)[-1][:48], fill=(255, 255, 0))
    out = WT / '_build/xv2-kame/sheets'; out.mkdir(parents=True, exist_ok=True)
    sheet.save(out / (a.tag + '.png'))
    print('sheet', out / (a.tag + '.png'))


if __name__ == '__main__':
    main()
