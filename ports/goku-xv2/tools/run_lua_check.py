"""Run one of Goku's Lua gates (lua/grab_check.lua, lua/ground_check.lua, lua/preview_check.lua) against a victim, in turbo, and print its tag lines.

    python ports/goku-xv2/tools/run_lua_check.py grab_check GRABCHECK [--vs mario] [--name tag] [--mods DIR] [--visible]

Uses GW_BUILD_ROOT / GW_MELEE from the environment (run.sh). Exit 0 when a '<TAG> RESULT PASS' line (or 'connected N of N' for ground_check) is printed.
"""
import argparse, os, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PORT = ROOT / 'ports/goku-xv2'
GIT_BASH = os.environ.get('GW_GIT_BASH', 'C:/Program Files/Git/bin/bash.exe')


def env_iso():
    for line in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
        m = re.match(r'\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*(.+)', line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise SystemExit('GW_ISO_VANILLA missing from .env')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('script'); ap.add_argument('tag')
    ap.add_argument('--vs', default='mario'); ap.add_argument('--name')
    ap.add_argument('--mods', default=str(ROOT / '_build/goku-xv2/author-source/package/mods'))
    ap.add_argument('--visible', action='store_true')
    ap.add_argument('--max-seconds', default='600')
    a = ap.parse_args()
    name = a.name or f'goku-{a.script}-{a.vs}'
    env = dict(os.environ)
    env.update({'MELEE_MODS_DIR': a.mods, 'MELEE_SCENE': f'mode=lab;p1=geno:goku-xv2/hu;p2={a.vs}/cpu0;stage=fd;items=off;time=0',
                'MELEE_PAD_SCRIPT': (PORT / 'lua' / (a.script + '.lua')).as_posix(), 'MELEE_UNATTENDED': '1',
                'MELEE_MAX_SECONDS': a.max_seconds, 'MELEE_LAB_UI': '0', 'MELEE_TURBO': '0' if a.visible else '1',
                'MELEE_WINDOW_X': '40', 'MELEE_WINDOW_Y': '40', 'MELEE_WINDOW_W': '1280', 'MELEE_WINDOW_H': '720',
                'MELEE_RUN_LABEL': f'Goku {a.script} vs {a.vs}'})
    out = ROOT / '_build/goku-xv2/checks'; out.mkdir(parents=True, exist_ok=True)
    with open(out / f'{name}.run.txt', 'w', encoding='utf-8') as fh:
        subprocess.run([GIT_BASH, (ROOT / 'tools/port/run.sh').as_posix(), '--max-seconds', a.max_seconds, name, '--iso', env_iso()],
                       cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT)
    root = Path(os.environ.get('GW_BUILD_ROOT') or ROOT / '_build')
    log = root / 'runs' / name / 'melee-pc.log'
    text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
    lines = re.findall(a.tag + r' (.*)', text)
    for l in lines:
        print(a.tag, l)
    if a.script == 'pad_check':
        seg = text.split('PADCHECK released', 1)[-1].split('PADCHECK END', 1)[0] if 'PADCHECK END' in text else None
        leaked = [l for l in (seg or '').splitlines() if 'script release (owner' in l]
        for l in leaked:
            print('PADCHECK LEAK', l.strip())
        ok = seg is not None and not leaked
        print('RESULT', 'PASS' if ok else 'FAIL (leaked claim or no END marker; read ' + str(log) + ')')
        return 0 if ok else 1
    ok = any(l.startswith('RESULT PASS') or l.startswith('PASS') or re.search(r'RESULT.*connected (\d+) of \1\b', l) for l in lines)
    print('RESULT', 'PASS' if ok else 'FAIL (read ' + str(log) + ')')
    return 0 if ok else 1


raise SystemExit(main())
