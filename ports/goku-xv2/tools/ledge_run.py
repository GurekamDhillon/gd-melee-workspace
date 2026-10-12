"""Run lua/ledge_check.lua (Up B reverse ledge catch gate) on Battlefield, headless/offscreen/muted/turbo, and print its LEDGECHK lines.

    python ports/goku-xv2/tools/ledge_run.py [--mods DIR] [--stage bf] [--name tag]

GW_MELEE / GW_BUILD_ROOT select the game checkout and its build root (the lane's own); --mods is a Goku combo package's mods dir
(default: this worktree's _build/goku-xv2/pkg-mods). Exit 1 unless 'LEDGECHK RESULT PASS' is in the log.
"""
import argparse, os, re, subprocess
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
WT = PORT.parents[1]
MAIN = Path(os.environ.get('GW_ROOT') or 'E:/Projects/Melee Workspace')
GIT_BASH = os.environ.get('GW_GIT_BASH', 'C:/Program Files/Git/bin/bash.exe')


def iso():
    for line in (MAIN / '.env').read_text(encoding='utf-8').splitlines():
        m = re.match(r'\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*(.+)', line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise SystemExit('GW_ISO_VANILLA missing')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mods', default=str(WT / '_build/goku-xv2/pkg-mods')); ap.add_argument('--stage', default='bf')
    ap.add_argument('--name', default='goku-ledge-check'); ap.add_argument('--max-seconds', default='900')
    a = ap.parse_args()
    game, broot = os.environ['GW_MELEE'], os.environ['GW_BUILD_ROOT']
    env = dict(os.environ)
    env.update({'GW_ROOT': str(MAIN), 'MELEE_MODS_DIR': a.mods,
                'MELEE_SCENE': f'mode=lab;p1=geno:goku-xv2/hu;p2=mario/cpu0;stage={a.stage};items=off;time=0',
                'MELEE_PAD_SCRIPT': (PORT / 'lua/ledge_check.lua').as_posix(), 'MELEE_UNATTENDED': '1',
                'MELEE_MAX_SECONDS': a.max_seconds, 'MELEE_LAB_UI': '0', 'MELEE_TURBO': '1',
                'MELEE_WINDOW_X': '30000', 'MELEE_WINDOW_Y': '30000', 'MELEE_WINDOW_W': '1280', 'MELEE_WINDOW_H': '720',
                'MELEE_BIND_DUMMY': '1', 'MELEE_VOLUME': '0', 'MELEE_NETPLAY_BIND': '127.0.0.1', 'MELEE_RUN_LABEL': 'Goku ledge check'})
    out = WT / '.omo/evidence'; out.mkdir(parents=True, exist_ok=True)
    with open(out / f'{a.name}.run.txt', 'w', encoding='utf-8') as fh:
        subprocess.run([GIT_BASH, (MAIN / 'tools/port/run.sh').as_posix(), '--max-seconds', a.max_seconds, a.name, '--iso', iso()],
                       cwd=game, env=env, stdout=fh, stderr=subprocess.STDOUT)
    log = Path(broot) / 'runs' / a.name / 'melee-pc.log'
    text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
    for l in re.findall(r'LEDGECHK (.*)', text):
        print('LEDGECHK', l)
    print('log:', log)
    raise SystemExit(0 if 'LEDGECHK RESULT PASS' in text else 1)


if __name__ == '__main__':
    main()
