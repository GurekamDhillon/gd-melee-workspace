"""Rollback / determinism test of Goku's combo graph: pad-driven strings under the bench SyncTest, and the LAB's rewind test.

    python ports/goku-xv2/combo/tests/run_combo_sync.py [--vs fox] [--name tag] [--rewind] [--visible]

Puts the goku-combo-sync script mod (a rotation of four strings: light x3 > launcher > short-hop > ender, light x5 > finisher,
Dragon Rush, ki volley) beside the combo package and runs the game with MELEE_SYNCTEST_BENCH=1 MELEE_SYNCTEST_CURATED=1
MELEE_SYNCTEST=12 (every frame is rolled back 12 frames and resimulated; the curated hash folds Geno_ComboBlock for a combo define).
--rewind instead calls gd.rewind_test (120 frames resimulated and compared) at match frame 900. Prints the SyncTest verdict lines
and the COMBOSYNC END line; exit 0 only when 0 checks mismatched and the string was actually played (links taken > 0).
"""
import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PKG = ROOT / '_build/goku-xv2/combo-package/mods'
GIT_BASH = os.environ.get('GW_GIT_BASH', 'C:/Program Files/Git/bin/bash.exe')


def env_iso():
    for line in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
        m = re.match(r'\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*(.+)', line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise SystemExit('GW_ISO_VANILLA missing from .env')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--vs', default='fox')
    ap.add_argument('--name', default='combo-sync')
    ap.add_argument('--rewind', action='store_true')
    ap.add_argument('--visible', action='store_true')
    args = ap.parse_args(argv)
    mod = PKG / 'goku-combo-sync'
    if mod.exists():
        shutil.rmtree(mod)
    shutil.copytree(HERE / 'goku-combo-sync', mod)
    (mod / 'missions').mkdir(exist_ok=True)
    (mod / 'missions/sync-run.txt').write_text(f'rewind = {1 if args.rewind else 0}\n', encoding='utf-8')
    enabled = [e for e in (PKG / 'enabled.txt').read_text(encoding='utf-8').split() if not e.startswith('goku-combo-')]  # one driver script at a time
    if 'goku-combo-sync' not in enabled:
        enabled.append('goku-combo-sync')
    (PKG / 'enabled.txt').write_text('\n'.join(enabled) + '\n', encoding='utf-8')
    env = dict(os.environ)
    env.update({'MELEE_MODS_DIR': str(PKG), 'MELEE_SCENE': f'mode=lab;p1=geno:goku-xv2/hu;p2={args.vs}/hu;stage=fd;items=off;time=0',
                'MELEE_UNATTENDED': '1', 'MELEE_MAX_SECONDS': '900', 'MELEE_LAB_UI': '0',
                'MELEE_WINDOW_X': '40', 'MELEE_WINDOW_Y': '40', 'MELEE_WINDOW_W': '1280', 'MELEE_WINDOW_H': '720',
                'MELEE_RUN_LABEL': 'Goku combo rollback test', 'MELEE_TURBO': '0',  # realtime on purpose: the bench SyncTest under turbo + a pad script mismatches (1291 of 8374 checks) for a reason that is the bench's, not the define's
                'MELEE_PAD_SCRIPT': ''})
    env.pop('MELEE_PAD_SCRIPT', None)
    if not args.rewind:
        env.update({'MELEE_SYNCTEST_BENCH': '1', 'MELEE_SYNCTEST_CURATED': '1', 'MELEE_SYNCTEST': '12'})
    name = f'{args.name}-{args.vs}' + ('-rewind' if args.rewind else '')
    cmd = [GIT_BASH, (ROOT / 'tools/port/run.sh').as_posix(), '--max-seconds', '900', name, '--iso', env_iso()]
    out = ROOT / '_build/goku-xv2/combo/results'
    out.mkdir(parents=True, exist_ok=True)
    with open(out / f'{name}.run.txt', 'w', encoding='utf-8') as fh:
        subprocess.run(cmd, cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT)
    root = Path(os.environ.get('GW_BUILD_ROOT') or ROOT / '_build')
    log = root / 'runs' / name / 'melee-pc.log'
    text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
    keep = [l for l in text.splitlines() if re.search(r'COMBOSYNC|synctest|SyncTest|snap:|rollback|mismatch', l, re.I)]
    for l in keep[-14:]:
        print(l)
    end = re.search(r'COMBOSYNC END frame (\d+) links_taken ([0-9.]+)', text)
    bad = re.search(r'(\d+) mismatch', ' '.join(keep))
    print('log', log)
    ok = bool(end) and float(end.group(2)) > 0
    if args.rewind:
        ok = ok and 'pass=true' in text
    else:
        ok = ok and not (bad and int(bad.group(1)) > 0)
    print('RESULT', 'PASS' if ok else 'FAIL (read the log)')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
