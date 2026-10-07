#!/usr/bin/env python3
"""Run one scripted offline match on the Windows build and on the Linux build (WSL, Ubuntu 22.04
rootfs, WSLg), in parallel, and compare their per-frame digests (MELEE_XHASH_LOG).

    pair.py NAME FRAMES SEED "SCENE" [--env K=V ...] [--dump 0,300] [--skip a-b,c-d] [--only win|linux]
            [--linux-dir outD] [--bias 55]

Results land in <out>/NAME/{win,linux}/ (xh.csv, dumps, melee-pc.log) and cmp_xhash.py is run on them.
Env for the Windows side: GW_MELEE, GW_BUILD_ROOT, GW_ROOT_ENV (see env_win.sh).
"""
import argparse, os, shutil, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('GW_ROOT_ENV', 'E:/Projects/Melee Workspace')
DISC_WSL = '/mnt/c/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso'


def q(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name'); ap.add_argument('frames'); ap.add_argument('seed'); ap.add_argument('scene')
    ap.add_argument('--env', action='append', default=[])
    ap.add_argument('--dump', default='')
    ap.add_argument('--skip', default='')
    ap.add_argument('--only', default='')
    ap.add_argument('--out', default=os.path.join(ROOT, '_build', 'xplat'))
    ap.add_argument('--linux-dir', default='outD')
    ap.add_argument('--bias', default='55')
    ap.add_argument('--ports', default='2')
    ap.add_argument('--disc', default='vanilla')
    ap.add_argument('--mem-every', default='30')
    a = ap.parse_args()
    out = os.path.join(a.out, a.name)
    os.makedirs(out, exist_ok=True)
    extra = list(a.env)
    if a.dump:
        extra.append('MELEE_XHASH_DUMP_FRAMES=' + a.dump)
    if a.skip:
        extra.append('MELEE_XHASH_SKIP=' + a.skip)
    extra.append('DET_BIAS=' + a.bias)
    extra.append('DET_PORTS=' + a.ports)
    extra.append('XP_DISC=' + a.disc)
    extra.append('MELEE_XHASH_MEM_EVERY=' + a.mem_every)
    procs = {}

    def run_win():
        env = dict(os.environ)
        env.setdefault('GW_ROOT_ENV', ROOT)
        script = os.path.join(HERE, 'run_win.sh').replace(os.sep, '/')
        cmd = [os.environ.get('GIT_BASH', 'C:/Program Files/Git/bin/bash.exe'), script, 'x_' + a.name, a.frames, a.seed, a.scene] + extra
        with open(os.path.join(out, 'win.out'), 'w') as fo:
            procs['win'] = subprocess.run(cmd, env=env, stdout=fo, stderr=subprocess.STDOUT, cwd=env['GW_MELEE'])

    def run_lin():
        inner = ('cd ~/lb2; export MELEE_VANILLA_ISO={v} MELEE_ACE_ISO={ace} MELEE_AKANEIA_ISO={ak}; '
                 './enterD.sh env SDL_VIDEODRIVER=wayland XP_DISC={disc} '
                 'bash /mnt/h/wsD/tools/xplat/run_linux.sh /mnt/h/{ld}/linux {name} {frames} {seed} {scene} {extra}').format(
            v=q(DISC_WSL), ace=q('/mnt/c/iso/SSBM ACE Build v2.0.0.iso'), ak=q('/mnt/c/iso/Akaneia.iso'), disc=a.disc,
            ld=a.linux_dir, name='x_' + a.name, frames=a.frames, seed=a.seed, scene=q(a.scene), extra=' '.join(q(e) for e in extra))
        env = dict(os.environ)
        env['MSYS_NO_PATHCONV'] = '1'
        with open(os.path.join(out, 'linux.out'), 'w') as fo:
            procs['linux'] = subprocess.run(['wsl', '-d', 'Debian', '--', 'bash', '-lc', inner], env=env,
                                            stdout=fo, stderr=subprocess.STDOUT)

    ts = []
    if a.only in ('', 'win'):
        ts.append(threading.Thread(target=run_win))
    if a.only in ('', 'linux'):
        ts.append(threading.Thread(target=run_lin))
    t0 = time.time()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    print('ran in %.0f s' % (time.time() - t0))
    wsrc = os.path.join(os.environ['GW_BUILD_ROOT'], 'runs', 'x_' + a.name)
    lsrc = '//wsl.localhost/Debian/home/gd/lb2/%s/xp-x_%s' % (a.linux_dir, a.name)
    for side, src in (('win', wsrc), ('linux', lsrc)):
        if a.only not in ('', side):
            continue
        d = os.path.join(out, side)
        os.makedirs(d, exist_ok=True)
        for fn in os.listdir(src):
            if fn.startswith('xh') or fn == 'melee-pc.log':
                shutil.copy2(os.path.join(src, fn), d)
    if a.only == '':
        r = subprocess.run([sys.executable, os.path.join(HERE, 'cmp_xhash.py'),
                            os.path.join(out, 'win', 'xh.csv'), os.path.join(out, 'linux', 'xh.csv')])
        print('compare exit', r.returncode)
        return r.returncode
    return 0


if __name__ == '__main__':
    sys.exit(main())
