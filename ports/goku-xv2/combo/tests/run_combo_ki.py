"""The ki-gated Goku moves under the combo meter (geno 11): ki charge fill, the vanish counter's cost and gate, the Super Kamehameha at ki 100.

    python ports/goku-xv2/combo/tests/run_combo_ki.py [--name tag] [--visible]

Puts the goku-combo-ki script mod beside the combo package and runs the LAB (Goku vs Mario, FD) once; prints the KITEST lines. Exit 0 on PASS.
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
    ap.add_argument('--name', default='combo-ki')
    ap.add_argument('--visible', action='store_true')
    args = ap.parse_args(argv)
    mod = PKG / 'goku-combo-ki'
    if mod.exists():
        shutil.rmtree(mod)
    shutil.copytree(HERE / 'goku-combo-ki', mod)
    enabled = [e for e in (PKG / 'enabled.txt').read_text(encoding='utf-8').split() if not e.startswith('goku-combo-')]  # one driver script at a time
    if 'goku-combo-ki' not in enabled:
        enabled.append('goku-combo-ki')
    (PKG / 'enabled.txt').write_text('\n'.join(enabled) + '\n', encoding='utf-8')
    env = dict(os.environ)
    env.update({'MELEE_MODS_DIR': str(PKG), 'MELEE_SCENE': 'mode=lab;p1=geno:goku-xv2/hu;p2=mario/hu;stage=fd;items=off;time=0',
                'MELEE_UNATTENDED': '1', 'MELEE_MAX_SECONDS': '300', 'MELEE_LAB_UI': '0',
                'MELEE_WINDOW_X': '40', 'MELEE_WINDOW_Y': '40', 'MELEE_WINDOW_W': '1280', 'MELEE_WINDOW_H': '720',
                'MELEE_RUN_LABEL': 'Goku ki gates', 'MELEE_TURBO': '0' if args.visible else '1',
                'MELEE_PAD_SCRIPT': '' if args.visible else (HERE / 'turbo_pad.lua').as_posix()})
    out = ROOT / '_build/goku-xv2/combo/results'
    out.mkdir(parents=True, exist_ok=True)
    cmd = [GIT_BASH, (ROOT / 'tools/port/run.sh').as_posix(), '--max-seconds', '300', args.name, '--iso', env_iso()]
    with open(out / f'{args.name}.run.txt', 'w', encoding='utf-8') as fh:
        subprocess.run(cmd, cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT)
    root = Path(os.environ.get('GW_BUILD_ROOT') or ROOT / '_build')
    log = root / 'runs' / args.name / 'melee-pc.log'
    text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
    lines = re.findall(r'KITEST (.*)', text)
    for l in lines:
        print(l)
    ok = any(l.startswith('RESULT: PASS') for l in lines)
    print('RESULT', 'PASS' if ok else 'FAIL (read ' + str(log) + ')')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
