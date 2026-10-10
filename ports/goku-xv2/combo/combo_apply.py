"""Goku's combo graph (geno 11) on top of the maintained Goku package, in a SEPARATE copy.

    python ports/goku-xv2/combo/combo_apply.py [--src _build/goku-xv2/combo-src/mods]
                                               [--out _build/goku-xv2/combo-package/mods]

Copies the built mods folder (goku-xv2 + geno-lab) to --out, then ADDS: the combo states (combo.json "states", appended after
the package's own states so their indices are unchanged), their subaction overlays on the clip-library rows, the KiBlast
article, HBSTUN on the jab1/jab2 overlays, the "combo" block, and "geno": 11. The source package is never modified (the
other Goku lane builds and runs it with an engine that reads geno 10). Run after ports/goku-xv2/tools/build.py.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = HERE.parent
ROOT = PORT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PORT / 'tools'))
sys.path.insert(0, str(ROOT / 'ports/ir/tools'))
import build as G  # noqa: E402  the Goku builder's role binding and scale
from tools.geno import script  # noqa: E402

STUN_LINE = 'HBSTUN 15 {n}  # COMBO (combo_apply.py): +{n} hitstun frames, see combo.json "jab_stun"'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--src', type=Path, default=ROOT / '_build/goku-xv2/combo-src/mods')
    ap.add_argument('--out', type=Path, default=ROOT / '_build/goku-xv2/combo-package/mods')
    args = ap.parse_args(argv)
    final = G.generated(args.out)
    # build into a sibling temp folder; the target is replaced only after everything validated (never emptied first)
    out = final.with_name(final.name + '.new')
    if out.exists():
        shutil.rmtree(out)
    if not (args.src / 'goku-xv2/geno.json').exists():
        raise SystemExit(f'source {args.src} has no goku-xv2/geno.json')
    shutil.copytree(args.src, out)
    pkg = out / 'goku-xv2'
    # the LAB script of the engine checkout in use (its COMBO mode draws the routes, geno.md 25); the package's missions stay
    game = Path(__import__('os').environ.get('GW_MELEE') or ROOT / 'melee')
    lab = game / 'pc/geno/mods/geno-lab/scripts/lab.lua'
    if lab.exists() and (out / 'geno-lab/scripts').exists():
        shutil.copy2(lab, out / 'geno-lab/scripts/lab.lua')
    spec = json.loads((HERE / 'combo.json').read_text(encoding='utf-8'))
    doc = json.loads((pkg / 'geno.json').read_text(encoding='utf-8'))
    f = doc['fighters'][0]
    plan = json.loads((pkg / 'files/plan.json').read_text(encoding='utf-8'))
    height = json.loads((ROOT / '_build/goku-xv2/author-source/art-report.json').read_text(encoding='utf-8'))['geometry']['height']
    scale = height / json.loads((PORT / 'gameplay.json').read_text(encoding='utf-8'))['geometry_reference_height']
    if 'rows' not in f.get('fighter', {}):
        raise SystemExit(f'{pkg}/geno.json has no fighter.rows: the source build did not finish (rebuild with build.py and check its rc); {final} is untouched')
    rows = f['fighter']['rows']
    names = [s['name'] for s in f['states']]
    overlays = {o['index']: o for o in f['subactions']}
    # 1. states and their overlays on the library rows (row = 303 + index of the clip in fighter.rows)
    for st in spec['states']:
        if st['name'] in names:
            raise SystemExit(f"state {st['name']} already exists in the package")
        if st['clip'] not in rows:
            raise SystemExit(f"clip {st['clip']} is not a library row")
        row = 303 + rows.index(st['clip'])
        f['states'].append({'name': st['name'], 'behavior': 'geno.ground', 'subaction': row, 'like': st['like'], 'phys': 'auto',
                            'coll': 'both', 'iasa': 'interrupt', 'move_tag': st['move_tag']})
        names.append(st['name'])
    for st in spec['states']:
        row = 303 + rows.index(st['clip'])
        text = G.bind((HERE / st['script']).read_text(encoding='utf-8'), plan, scale)
        # KiBlast is appended after the package's own articles; the script says 3 (the count before the specials pass added more)
        text = text.replace('geno.article.spawn 3', f"geno.article.spawn {len(f['articles'])}")
        words = script.assemble(text, names)
        name = Path(st['script']).stem
        (pkg / 'moves').mkdir(exist_ok=True)
        (pkg / 'moves' / f'combo_{name}.genoasm').write_text(text, encoding='utf-8')
        (pkg / 'moves' / f'combo_{name}.words').write_text(' '.join(f'0x{x:08X}' for x in words) + '\n', encoding='utf-8')
        if row in overlays:
            raise SystemExit(f'row {row} already has an overlay')
        overlays[row] = {'index': row, 'file': f'moves/combo_{name}.words', 'move_tag': st['move_tag']}
    # 2. HBSTUN on the jab overlays (rows of motions 44 / 45), in this copy only
    motion_rows = {c['motion']: c['subaction'] for c in f.get('common_states', [])}
    for move, n in ((k, v) for k, v in spec['jab_stun'].items() if k in ('jab1', 'jab2')):
        motion = {'jab1': 44, 'jab2': 45}[move]
        row = motion_rows[motion]
        o = overlays[row]
        src = (pkg / o['file'].replace('.words', '.genoasm'))
        text = src.read_text(encoding='utf-8')
        if spec.get('jab_set_kb'):
            # any knockback the Goku package gave the jab (it retunes them: kbg=40 bkb=10, later kbg=50 bkb=8, ...) becomes the fixed one
            text, nsub = re.subn(r'kbg=\d+ fkb=\d+ bkb=\d+', spec['jab_set_kb'], text)
            if not nsub:
                raise SystemExit(f'{move}: no "kbg= fkb= bkb=" in the jab script to set knockback on (combo.json jab_set_kb)')
        # the Goku package may carry its own HBSTUN on the jab hit (attack-feel pass: HBSTUN 15 2): the combo package's value wins
        stun = STUN_LINE.format(n=n).split('  #')[0]
        if re.search(r'^HBSTUN \d+ \d+', text, re.M):
            text = re.sub(r'^HBSTUN \d+ \d+', stun, text, flags=re.M)
        else:
            text = re.sub(r'(hitbox slot=0[^' + chr(92) + 'n]*' + chr(92) + 'n)', lambda m: m[1] + stun + chr(10), text, count=1)
        words = script.assemble(text, names)
        (pkg / f'moves/combo_{move}.genoasm').write_text(text, encoding='utf-8')
        (pkg / f'moves/combo_{move}.words').write_text(' '.join(f'0x{x:08X}' for x in words) + '\n', encoding='utf-8')
        overlays[row] = dict(o, file=f'moves/combo_{move}.words')
    f['subactions'] = [overlays[k] for k in sorted(overlays)]
    # 3. articles (appended: the package's article indices are unchanged); the model is the package's ki model
    model = f['articles'][0].get('model') if f.get('articles') else None
    for a in spec['articles']:
        a = json.loads(json.dumps(a))
        a['spawn'] = [v * scale for v in a['spawn']]
        for h in a['hitboxes']:
            h['size'] = round(h['size'] * scale, 4)
        if model:
            a['model'] = model
        f['articles'].append(a)
    # 4. the combo block; "source" stays in the routes (provenance; in the content id)
    f['combo'] = spec['combo']
    if spec.get('meter'):
        f['meter'] = spec['meter']  # the HUD bar for the ki value (geno 11 'meter'); position defaults under the port's plate
    ki_lua = pkg / 'lua/goku_ki.lua'  # the full module (ki costs, the Super Kamehameha, the ki charge), built by build.py
    if ki_lua.exists():
        shutil.copy2(ki_lua, pkg / 'lua/goku.lua')
    doc['geno'] = 11
    (pkg / 'geno.json').write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')
    if final.exists():
        old = final.with_name(final.name + '.old')
        if old.exists():
            shutil.rmtree(old)
        final.rename(old)
    out.rename(final)
    out = final
    print(f"combo package: {out} ({len(spec['states'])} states, {len(spec['combo']['routes'])} routes, geno 11)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
