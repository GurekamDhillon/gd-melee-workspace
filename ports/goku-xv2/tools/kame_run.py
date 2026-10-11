"""Run one Kamehameha Lua scenario headless/offscreen against the lane build (agent/goku-kamehameha) and print its tag lines.

    python ports/goku-xv2/tools/kame_run.py kame_shots KAME [--vs mario] [--name tag] [--turbo] [--visible]

Environment it sets (override by exporting first): GW_ROOT = the main workspace (toolchain, .env), GW_MELEE = the game worktree,
GW_BUILD_ROOT = its build root, MELEE_MODS_DIR = this worktree's package. Windows are parked off screen (MELEE_WINDOW_X/Y=30000)
unless --visible. Screenshots (gd.screenshot) land in the run's script data folder; the tool copies *.png to .omo/evidence/<name>/.
"""
import argparse, os, re, shutil, subprocess
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
WT = PORT.parents[1]                       # the workspace worktree
MAIN = Path(os.environ.get('GW_ROOT') or 'E:/Projects/Melee Workspace')
GAME = os.environ.get('GW_MELEE') or str(MAIN / 'worktrees/kame-game')
BROOT = os.environ.get('GW_BUILD_ROOT') or str(MAIN / '_build/agents/goku-kamehameha')
GIT_BASH = os.environ.get('GW_GIT_BASH', 'C:/Program Files/Git/bin/bash.exe')


def iso():
    for line in (MAIN / '.env').read_text(encoding='utf-8').splitlines():
        m = re.match(r'\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*(.+)', line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise SystemExit('GW_ISO_VANILLA missing')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('script'); ap.add_argument('tag')
    ap.add_argument('--vs', default='mario'); ap.add_argument('--p1', default='geno:goku-xv2/hu'); ap.add_argument('--name')
    ap.add_argument('--turbo', action='store_true'); ap.add_argument('--clean', action='store_true', help='run a copy of the package whose LAB starts in the CLEAN display (no hitbox / hurtbox overlay)'); ap.add_argument('--visible', action='store_true')
    ap.add_argument('--max-seconds', default='300'); ap.add_argument('--cfg', action='append', default=[])
    a = ap.parse_args()
    name = a.name or f'kame-{a.script}'
    kv = dict(c.split('=', 1) for c in a.cfg)
    gen = PORT / 'lua' / ('_gen_' + name + '.lua')   # untracked scratch copy with CFG prepended
    gen.write_text('CFG={' + ','.join('%s=%r' % (k, v) for k, v in kv.items()) + '}' + chr(10) + (PORT / 'lua' / (a.script + '.lua')).read_text(encoding='utf-8'), encoding='utf-8')
    mods = os.environ.get('KAME_MODS') or str(WT / '_build/goku-xv2/author-source/package/mods')
    if a.clean:   # the LAB starts in CLEAN: lab.lua 'mode = 2, hidden' (HITBOXES) -> 'mode = 1, hidden' in a throwaway copy
        dst = WT / ('_build/xv2-kame/mods_clean_' + name)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(mods, dst)
        lab = dst / 'geno-lab/scripts/lab.lua'
        t = lab.read_text(encoding='utf-8')
        assert 'mode = 2, hidden' in t or 'mode = 1, hidden' in t, 'lab.lua start mode not found'
        lab.write_text(t.replace('mode = 2, hidden', 'mode = 1, hidden', 1), encoding='utf-8')
        mods = str(dst)
    p2 = a.vs if '/' in a.vs else a.vs + '/cpu0'
    off = '100' if a.visible else '30000'
    env = dict(os.environ)
    env.update({'GW_ROOT': str(MAIN), 'GW_MELEE': GAME, 'GW_BUILD_ROOT': BROOT,
                'MELEE_MODS_DIR': mods,
                'MELEE_SCENE': f'mode=lab;p1={a.p1};p2={p2};stage=fd;items=off;time=0',
                'MELEE_PAD_SCRIPT': gen.as_posix(), 'MELEE_UNATTENDED': '1',
                'MELEE_MAX_SECONDS': a.max_seconds, 'MELEE_LAB_UI': '0', 'MELEE_TURBO': '1' if a.turbo else '0',
                'MELEE_WINDOW_X': off, 'MELEE_WINDOW_Y': off, 'MELEE_WINDOW_W': '1280', 'MELEE_WINDOW_H': '720',
                'MELEE_BIND_DUMMY': '1', 'MELEE_RUN_LABEL': f'Kamehameha {a.script}'})
    out = WT / '.omo/evidence'; out.mkdir(parents=True, exist_ok=True)
    with open(out / f'{name}.run.txt', 'w', encoding='utf-8') as fh:
        subprocess.run([GIT_BASH, (MAIN / 'tools/port/run.sh').as_posix(), '--max-seconds', a.max_seconds, name, '--iso', iso()],
                       cwd=GAME, env=env, stdout=fh, stderr=subprocess.STDOUT)
    run = Path(BROOT) / 'runs' / name
    log = run / 'melee-pc.log'
    text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
    for l in re.findall(a.tag + r' (.*)', text):
        print(a.tag, l)
    gen.unlink(missing_ok=True)
    shots = list(run.rglob('*.png'))
    if shots:
        dst = out / name; dst.mkdir(exist_ok=True)
        for s in shots:
            shutil.copy2(s, dst / s.name)
        print(f'{len(shots)} screenshots -> {dst}')
    print('log:', log)


if __name__ == '__main__':
    main()
