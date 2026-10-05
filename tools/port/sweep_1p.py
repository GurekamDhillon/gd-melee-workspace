"""Direct-launch sweep of the 1P stages: every Classic step (and Adventure step) is booted with
`MELEE_SCENE="mode=<mode>;p1=<fighter>;difficulty=2;step=<n>"`, left for --frames (600) logic frames, and the
run's log is scanned for an assertion, panic or crash. Prints a table (stage load = the scene
reached GS_VS and 600 frames passed). No disc path is ever printed.

  python tools/port/sweep_1p.py [--modes classic,adventure] [--steps 0-11] [--fighter mario]
Needs a built game (tools/port/build.sh) and GW_ISO_VANILLA in the environment (.env).
"""
import argparse, os, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BAD = re.compile(r'assertion "[^"]*" failed in [^\s]+ on line \d+|gw: PANIC[^\n]*|FATAL[^\n]*|unhandled exception[^\n]*|couldn t get[^\n]*')


def parse_steps(text):
    out = []
    for part in text.split(','):
        if '-' in part:
            a, b = part.split('-'); out += list(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def run_one(mode, step, fighter, timeout, frames):
    name = f'sweep-{mode}-{step}'
    env = dict(os.environ)
    env['MELEE_SCENE'] = f'mode={mode};p1={fighter}/stocks3;difficulty=2;step={step}'
    quit_lua = Path(env.get('GW_BUILD_ROOT') or ROOT / '_build') / 'tmp' / f'sweep_quit_{frames}.lua'
    quit_lua.parent.mkdir(parents=True, exist_ok=True)
    quit_lua.write_text((HERE / 'sweep_1p_quit.lua').read_text().replace('600', str(frames)))
    env['MELEE_PAD_SCRIPT'] = str(quit_lua)
    env.setdefault('MELEE_TURBO', '1')
    env.setdefault('MELEE_VOLUME', '0')
    env['MELEE_PAD_IGNORE_ADAPTER'] = '1'
    iso = env.get('GW_ISO_VANILLA')
    if not iso:
        sys.exit('GW_ISO_VANILLA is not set (source .env)')
    bash = env.get('GW_BASH', r'C:\Program Files\Git\bin\bash.exe')
    cmd = [bash, str(HERE / 'run.sh'), name, '--iso', iso]
    try:
        subprocess.run(cmd, env=env, cwd=str(ROOT), timeout=timeout, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        pass
    root = Path(env.get('GW_BUILD_ROOT') or ROOT / '_build') / 'runs' / name / 'melee-pc.log'
    if not root.exists():
        return 'no log', ''
    text = root.read_text(encoding='utf-8', errors='replace')
    text = '\n'.join(l for l in text.splitlines() if 'disc image' not in l.lower() and '.iso' not in l.lower())
    bad = BAD.search(text)
    reached = f'sweep: reached {frames} frames' in text
    entered = re.findall(r'scene: enter mode=\S+ state=(\d+) screen=(\S+)', text)
    last = entered[-1][1] if entered else '-'
    if bad:
        return 'FAIL', bad.group(0)[:110]
    return ('ok' if reached else 'no-600'), f'last screen {last}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--modes', default='classic,adventure')
    ap.add_argument('--steps', default='0-11')
    ap.add_argument('--fighter', default='mario')
    ap.add_argument('--timeout', type=int, default=150)
    ap.add_argument('--frames', type=int, default=600, help='logic frames to let each scene run')
    a = ap.parse_args()
    rows = []
    for mode in a.modes.split(','):
        for step in parse_steps(a.steps):
            t = time.time()
            res, note = run_one(mode, step, a.fighter, a.timeout, a.frames)
            rows.append((mode, step, res, note))
            print(f'{mode:10} step {step:2}  {res:7} {note}  ({time.time()-t:.0f}s)', flush=True)
    bad = [r for r in rows if r[2] != 'ok']
    print(f'\n{len(rows) - len(bad)} of {len(rows)} loaded and ran the requested frames')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
