#!/usr/bin/env python3
"""Two scripted offline matches on the SAME Windows build, differing only in disc (and optionally a loose-mod
folder), digests compared per frame. Answers "can these two installs play each other?" without a second PC.

    disc_pair.py NAME FRAMES SEED "SCENE" --package DIR [--a vanilla] [--b ace] [--mods-a DIR] [--mods-b DIR] [--dump 5243,5244]

--package  a release-layout folder (melee-pc.exe, ui\, scripts\, ...: an unzipped GDMelee-*-win64). It is copied to
           <repo>/_build/xplat/NAME/{a,b}/ so the two games do not share a log or a cache.
--a/--b    vanilla|ace|akaneia (GW_ISO_VANILLA / GW_ISO_ACE / GW_ISO_AKANEIA from .env)
--mods-a/b MELEE_MODS_DIR for that side (default: an empty folder). A folder holding mods/<id>/files/PlCo.dat mounts that
           file over the disc's: that is how "vanilla disc + ACE's PlCo.dat" is built.

Same environment as tools/xplat/run_win.sh gives pair.py (det_input.lua, turbo, MELEE_XHASH_LOG), WITHOUT tools/port/run.sh:
run.sh adds widescreen, a 1920x1080 window and a render scale, and the match it plays is not the match pair.py plays
(rb differs from frame 0); use the same route on both sides, never mix. The column that matters is `rb`, the netplay checksum.

2026-10-08 finding this tool was written for: with `mode=vs;at=match;p1=falco/c0/hu/stocks99;p2=sheik/c0/hu/stocks99;stage=fd;time=0`
seed 777, the vanilla and the ACE disc agree for 5243 frames and then rb differs (5D935CC9 v 7B26BF6F at 5244); so does the vanilla disc
with only ACE's PlCo.dat mounted. See docs/xplat-netplay.md, "Different discs".
"""
import argparse, os, shutil, subprocess, sys, threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('GW_ROOT_ENV', 'E:/Projects/Melee Workspace')
ISO = {'vanilla': 'GW_ISO_VANILLA', 'ace': 'GW_ISO_ACE', 'akaneia': 'GW_ISO_AKANEIA'}


def load_env(path):
    out = {}
    for line in open(path, errors='replace'):
        line = line.strip()
        if line.startswith('export '):
            line = line[7:]
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name'); ap.add_argument('frames'); ap.add_argument('seed'); ap.add_argument('scene')
    ap.add_argument('--package', required=True)
    ap.add_argument('--a', default='vanilla'); ap.add_argument('--b', default='ace')
    ap.add_argument('--mods-a', default=''); ap.add_argument('--mods-b', default='')
    ap.add_argument('--ports', default='2'); ap.add_argument('--dump', default='')
    a = ap.parse_args()
    dot = load_env(os.path.join(ROOT, '.env'))
    out = os.path.join(ROOT, '_build', 'xplat', a.name)
    nomods = os.path.join(out, 'nomods')
    os.makedirs(nomods, exist_ok=True)

    def run(tag, disc, mods):
        d = os.path.join(out, tag)
        shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(a.package, d, ignore=shutil.ignore_patterns('melee-pc.log', 'crashlogs', 'exit.json', 'heartbeat.json', 'perf.json'))
        det = 'DET = {frames=%s, seed=%s, bias=55, ports=%s}\n' % (a.frames, a.seed, a.ports)
        det += open(os.path.join(HERE, 'det_input.lua')).read()
        open(os.path.join(d, 'det.lua'), 'w').write(det)
        env = dict(os.environ)
        env.update(MELEE_SCENE=a.scene, MELEE_PAD_SCRIPT=os.path.join(d, 'det.lua'), MELEE_XHASH_LOG=os.path.join(d, 'xh.csv'),
                   MELEE_TURBO='1', MELEE_TURBO_RENDER='120', MELEE_VOLUME='0', MELEE_TEST_SEED='777', MELEE_MAX_SECONDS='1500',
                   MELEE_PAD_IGNORE_ADAPTER='1', MELEE_SKIP_INTRO='1', MELEE_XHASH_MEM_EVERY='600',
                   MELEE_MODS_DIR=mods or nomods)
        if a.dump:
            dd = os.path.join(d, 'dump'); os.makedirs(dd, exist_ok=True)
            env.update(MELEE_XHASH_DUMP_FRAMES=a.dump, MELEE_XHASH_DUMP_DIR=dd)
        with open(os.path.join(d, 'run.out'), 'w') as fo:
            subprocess.run([os.path.join(d, 'melee-pc.exe'), '--iso', dot[ISO[disc]]], env=env, cwd=d, stdout=fo, stderr=subprocess.STDOUT)

    ts = [threading.Thread(target=run, args=('a', a.a, a.mods_a)), threading.Thread(target=run, args=('b', a.b, a.mods_b))]
    for t in ts: t.start()
    for t in ts: t.join()
    r = subprocess.run([sys.executable, os.path.join(HERE, 'cmp_xhash.py'), os.path.join(out, 'a', 'xh.csv'),
                        os.path.join(out, 'b', 'xh.csv'), '--cols', 'rb'])
    print('rb compare exit', r.returncode, '(0 = the two installs simulate the same match)')
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
