#!/usr/bin/env python3
"""Run ONE benchmark scene through run.sh, measure a fixed window of frames, and judge it.

    tools/port/bench.sh <scene> [--fps 60|u] [--mods DIR] [--warm N] [--frames N] [--name RUN]
                        [--port N] [--summary on|off|full] [--judge-noisy] [--update-baseline] [--keep]
    scenes: retail2 | ported1 | ported2 (tools/port/perfjudge.py BENCH), or a raw scene token
            "mode=lab;p1=...;p2=..." (then there is no baseline, only the budget checks)

The window is `--frames` frames (default 1800 = 30 s at 60 Hz) starting `--warm` frames (default 900)
after the scene loads, so first-use hitches never count. The game is the build's own exe, started by
run.sh (own sandbox, own copy of the exe) with the profiler's SUMMARY on and a console port; this
script polls `prof perf`, asks the game to quit through its console (`gd.quit()`) when the window is
complete, then judges perf.json. Ported-fighter scenes need a mods dir holding the fighter's slot mod
(--mods, or GW_BENCH_MODS) and are skipped without one.

Rules it keeps: never kills by name (the game's own PID is read from run.json and waited on; a stuck
run is stopped only through its console), refuses to start below 2.5 GB of free memory, prints no
disc path. Exit: 0 PASS/WARN, 3 FAIL, 4 NOISY, 2 skipped, 1 error.
"""
import argparse
import ctypes
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import perfjudge  # noqa: E402


class Console:
    def __init__(self, port, timeout=60):
        self.s = socket.create_connection(('127.0.0.1', port), timeout=timeout)
        self.f = self.s.makefile('r', encoding='utf-8', errors='replace')
        self.f.readline()

    def __call__(self, line):
        self.s.sendall((line + '\n').encode())
        out = []
        while True:
            r = self.f.readline()
            if not r:
                return '\n'.join(out)
            r = r.rstrip('\n')
            if r in ('>>> ok', '>>> error'):
                return '\n'.join(out)
            if r.startswith('> '):
                continue
            out.append(r)

    def ev(self, expr):
        return self(f'= {expr}').strip()


def free_memory_gb():
    class MS(ctypes.Structure):
        _fields_ = [('l', ctypes.c_ulong), ('load', ctypes.c_ulong), ('tp', ctypes.c_ulonglong), ('ap', ctypes.c_ulonglong),
                    ('tv', ctypes.c_ulonglong), ('av', ctypes.c_ulonglong), ('te', ctypes.c_ulonglong), ('ae', ctypes.c_ulonglong),
                    ('x', ctypes.c_ulonglong)]
    m = MS()
    m.l = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ap / 2**30


def git_bash():
    for p in (r'C:\Program Files\Git\bin\bash.exe', r'C:\Program Files (x86)\Git\bin\bash.exe'):
        if os.path.exists(p):
            return p
    return 'bash'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('scene')
    ap.add_argument('--fps', default='60')
    ap.add_argument('--mods')
    ap.add_argument('--warm', type=int, default=900)
    ap.add_argument('--frames', type=int, default=1800)
    ap.add_argument('--name')
    ap.add_argument('--port', type=int, default=int(os.environ.get('MELEE_CONSOLE_PORT', '53599')))
    ap.add_argument('--summary', default='on', choices=('on', 'off', 'full'))
    ap.add_argument('--judge-noisy', action='store_true')
    ap.add_argument('--update-baseline', action='store_true')
    ap.add_argument('--keep', action='store_true', help='keep the run folder (default: keep; --no-keep deletes a passing one)')
    ap.add_argument('--no-keep', action='store_true')
    ap.add_argument('--setup', help='console commands run once the match is up, ";;" separated (overrides the scene default)')
    a = ap.parse_args()

    spec = perfjudge.BENCH.get(a.scene)
    key = a.scene if spec else None
    scene = spec['scene'] if spec else a.scene
    setup = a.setup if a.setup is not None else (spec['setup'] if spec else '')
    mods = a.mods or os.environ.get('GW_BENCH_MODS')
    if spec and spec['ported'] and not mods:
        print('SKIP | %s needs a ported-fighter mods dir: pass --mods DIR or set GW_BENCH_MODS' % a.scene)
        return 2
    if free_memory_gb() < 2.5:
        print('ERROR | less than 2.5 GB of memory free: not starting a measurement run')
        return 1
    iso = os.environ.get('GW_ISO_VANILLA')
    if not iso:
        print('ERROR | GW_ISO_VANILLA is not set (source .env)')
        return 1
    build_root = Path(os.environ.get('GW_BUILD_ROOT') or ROOT / '_build')
    name = a.name or time.strftime('bench-%Y%m%d-%H%M%S')
    sandbox = build_root / 'runs' / name
    env = dict(os.environ)
    env.update(MELEE_SCENE=scene, MELEE_FPS=a.fps, MELEE_CONSOLE_PORT=str(a.port),
               MELEE_PERF_WINDOW=f'{a.warm},{a.frames}', MELEE_PERF_SUMMARY='0' if a.summary == 'off' else '1',
               MELEE_PROFILER='1' if a.summary == 'full' else '0', MELEE_PAD_IGNORE_ADAPTER='1')
    env.setdefault('MELEE_VOLUME', '0')
    env.setdefault('MELEE_WINDOW_W', '1280')
    env.setdefault('MELEE_WINDOW_H', '720')
    if mods:
        env['MELEE_MODS_DIR'] = mods
    cmd = [git_bash(), str(ROOT / 'tools' / 'port' / 'run.sh'), '--realtime', name, '--iso', iso]
    proc = subprocess.Popen(cmd, env=env, cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f'bench {a.scene} fps={a.fps} summary={a.summary} window={a.warm}+{a.frames} run={name} (launcher pid {proc.pid})', flush=True)
    c = None
    t0 = time.time()
    while time.time() - t0 < 240 and proc.poll() is None:
        try:
            c = Console(a.port)
            break
        except OSError:
            time.sleep(1)
    if not c:
        print('ERROR | no console: the game did not start (see ' + str(sandbox / 'melee-pc.log') + ')')
        return 1
    try:
        t0 = time.time()
        while time.time() - t0 < 240:
            try:
                if c.ev('gd.match().active') == 'true' and c.ev('gd.player(1) and gd.player(2) and 1') == '1':
                    break
            except OSError:
                break
            time.sleep(0.5)
        for cmdline in [x.strip() for x in setup.split(';;') if x.strip()]:
            c(cmdline)
        limit = (a.warm + a.frames) / 60.0 * (3 if a.fps == '60' else 6) + 180
        t0 = time.time()
        status = ''
        while time.time() - t0 < limit:
            status = c('prof perf')
            if 'window=done' in status:
                break
            time.sleep(2)
        else:
            print('ERROR | bench window did not complete in %.0f s (%s)' % (limit, status.strip()))
        try:
            c('= gd.quit()')
        except OSError:
            pass
    except OSError as e:
        print('ERROR | console lost:', e)
    try:
        proc.wait(timeout=90)
    except subprocess.TimeoutExpired:
        try:
            c('= gd.quit()')
            proc.wait(timeout=60)
        except Exception:
            print('ERROR | the game did not exit; stop it through its console or by the PID in', sandbox / 'run.json', '(not by name)')
            return 1
    (sandbox / 'bench.json').write_text(json.dumps(dict(bench=key, scene=scene, fps=a.fps, warm=a.warm, frames=a.frames,
                                                       summary=a.summary, setup=setup, mods=mods and Path(mods).name)))
    perf = perfjudge.load_json(sandbox / 'perf.json')
    if not perf:
        print('ERROR | no perf.json was written (see ' + str(sandbox / 'melee-pc.log') + ')')
        return 1
    if a.update_baseline:
        print('baseline written:', perfjudge.update_baseline(sandbox, key, a.fps))
    res = perfjudge.judge(perf, key, a.fps, a.judge_noisy)
    print('perf ' + perfjudge.line(res))
    print('run folder:', sandbox)
    return {'PASS': 0, 'WARN': 0, 'FAIL': 3, 'NOISY': 4}.get(res['verdict'].rstrip('*'), 0)


if __name__ == '__main__':
    sys.exit(main())
