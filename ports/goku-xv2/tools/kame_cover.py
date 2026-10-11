"""How much do the effects cover Goku? Numbers from clean strips of the SAME frames with and without the Kamehameha effects.

    python ports/goku-xv2/tools/kame_cover.py TAG [--hold 620] [--gap 60] [--cfg k=v ...] [--face left]

Three strips of the charge (no fire): `fx` (the package as built), `nofx` (a copy whose Kamehameha / aura calls are removed) and `bg` (Goku parked off screen, same fixed camera).
Goku's mask = pixels where nofx differs from bg; the cover numbers are over that mask: mean |fx - nofx| (0-255, grey) and the share of mask pixels the effects change by more than 40.
Lower is better. Prints a table per shot, the mean over shots, and writes <evidence>/cover_<TAG>.txt. Silent (MELEE_VOLUME=0 via kame_run.py).
"""
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
WT = PORT.parents[1]
EV = WT / '.omo/evidence'


def strip(name, mods, cfg):
    env = dict(os.environ, KAME_MODS=str(mods))
    cmd = [sys.executable, str(PORT / 'tools/kame_run.py'), 'kame_strip', 'KAME', '--name', name, '--clean'] + [x for c in cfg for x in ('--cfg', c)]
    subprocess.run(cmd, env=env, capture_output=True, text=True)
    return sorted((EV / name).glob('*.png'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tag'); ap.add_argument('--hold', default='620'); ap.add_argument('--gap', default='60'); ap.add_argument('--face', default='')
    ap.add_argument('--cfg', action='append', default=[])
    a = ap.parse_args()
    import numpy as np
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    mods = Path(os.environ.get('KAME_MODS') or WT / '_build/goku-xv2/combo-kame/mods')
    nofx = WT / ('_build/xv2-kame/mods_nofx_' + a.tag)
    shutil.rmtree(nofx, ignore_errors=True)
    shutil.copytree(mods, nofx)
    fb = nofx / 'goku-xv2/fx/fx_bindings.json'
    d = json.loads(fb.read_text(encoding='utf-8'))
    for st in d['states']:
        st['calls'] = []
    fb.write_text(json.dumps(d), encoding='utf-8')
    base = ['hold=' + a.hold, 'fire=0', 'tail=0', 'hgap=' + a.gap, 'zoom=1', 'camx=2'] + ([] if not a.face else ['face=' + a.face]) + a.cfg
    sets = {}
    for tag, m, extra in (('fx', mods, []), ('nofx', nofx, []), ('bg', nofx, ['away=1'])):
        sets[tag] = strip('cov_%s_%s' % (a.tag, tag), m, base + extra + ['tag=' + tag])
    n = min(len(v) for v in sets.values())
    lines = ['%s: %d shots, hold %s gap %s %s' % (a.tag, n, a.hold, a.gap, ' '.join(a.cfg))]
    tot = []
    for i in range(n):
        im = {k: np.asarray(Image.open(sets[k][i]).convert('RGB'), dtype=np.int16) for k in sets}
        mask = np.abs(im['nofx'] - im['bg']).sum(axis=2) > 48
        if mask.sum() < 500:
            continue
        diff = np.abs(im['fx'] - im['nofx']).mean(axis=2)
        mean, frac = float(diff[mask].mean()), float((diff[mask] > 40).mean())
        tot.append((mean, frac))
        lines.append('  shot %02d (%s): body %d px, effects change body pixels by mean %.1f, %.1f%% of them by > 40' % (i + 1, sets['fx'][i].stem.split('_', 2)[-1][:28], mask.sum(), mean, 100 * frac))
    if tot:
        lines.append('MEAN over %d shots: change %.1f, share > 40: %.1f%%' % (len(tot), sum(t[0] for t in tot) / len(tot), 100 * sum(t[1] for t in tot) / len(tot)))
    (EV / ('cover_%s.txt' % a.tag)).write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
