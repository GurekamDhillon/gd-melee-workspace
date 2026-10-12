"""Assemble the final Goku package: the gameplay package (combo, effects, sounds) plus the art lead's costumes and presentation.

    python tools/media/goku/assemble_package.py --base <gameplay combo-package/mods> --art <art author-source/package/mods>
        [--out _build/goku-media/final/mods]

Why: the art lead's build tree has no generated effects or sounds, so its package/mods has Goku's costumes, portraits, stock and
results art but no fx/ and no .gnsnd files (and no combo block), while the gameplay lane's combo-package/mods has everything but
the new art. geno.json of the two differs only in fighters[0].fighter.costumes, presentation (portrait, stock, results) and the
fx/audio sections the art tree lacks (checked below), so the result is the base package with the art files and those two geno.json
fields taken from the art package. Read-only on both inputs; the output goes under _build (git-ignored). Goku is never committed.
"""
import argparse, json, shutil, sys
from pathlib import Path

MAIN = Path('E:/Projects/Melee Workspace')


def diff(x, y, p=''):
    out = []
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x:
                out.append(('+', p + '/' + k))
            elif k not in y:
                out.append(('-', p + '/' + k))
            else:
                out += diff(x[k], y[k], p + '/' + k)
    elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
        for i, (u, v) in enumerate(zip(x, y)):
            out += diff(u, v, p + '[%d]' % i)
    elif x != y:
        out.append(('~', p))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', default=str(MAIN / 'worktrees/gokustage/_build/goku-xv2/combo-package/mods'))
    ap.add_argument('--art', default=str(MAIN / 'worktrees/gokuart/_build/goku-xv2/author-source/package/mods'))
    ap.add_argument('--out', default=str(MAIN / '_build/goku-media/final/mods'))
    a = ap.parse_args()
    base, art, out = Path(a.base), Path(a.art), Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(base, out)
    gb = json.loads((base / 'goku-xv2/geno.json').read_text(encoding='utf-8'))
    ga = json.loads((art / 'goku-xv2/geno.json').read_text(encoding='utf-8'))
    # the art package must not change anything else about the fighter definition
    allowed = ('/fighters[0]/fighter/costumes', '/fighters[0]/presentation')
    other = [(k, p) for k, p in diff(gb, ga) if not p.startswith(allowed)
             and not any(s in p for s in ('/fx', '/audio', 'show_model', 'fx_bindings', 'combo', 'meter', 'states', 'articles', 'special_adaptation', '/subactions', '/geno'))]
    if other:
        print('WARNING: geno.json differs beyond costumes/presentation and the generated sections:', other[:10])
    fb, fa = gb['fighters'][0], ga['fighters'][0]
    fb['fighter']['costumes'] = fa['fighter']['costumes']
    fb['presentation'] = fa['presentation']
    (out / 'goku-xv2/geno.json').write_text(json.dumps(gb, indent=2, ensure_ascii=False), encoding='utf-8')
    n = 0
    for p in sorted((art / 'goku-xv2/files').iterdir()):
        shutil.copy2(p, out / 'goku-xv2/files' / p.name)
        n += 1
    left = [m for m in fb['fighter']['costumes']]
    print('assembled %s: base %s + %d art files; costumes %d; presentation keys %s' % (out, base.parent.parent.name, n, len(left), sorted(fb['presentation'])))


if __name__ == '__main__':
    main()
