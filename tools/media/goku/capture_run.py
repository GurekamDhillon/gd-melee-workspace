"""Run one Goku capture script in the LAB (off-screen, muted to the speakers) and collect its frames and audio.

    python tools/media/goku/capture_run.py lua/clips_kame.lua --name kame1 [--stage fd] [--vs mario] [--res 1280x720]
        [--exe E:/.../melee-pc.exe] [--mods <mods dir>] [--game <game checkout>] [--cfg k=v ...] [--no-audio]

The script gets `CFG` and the `CAP` helper (lua/cap.lua) prepended. CAP.wait(n) waits n logic frames and screenshots each
(gd.screenshot, GX-only, so the game's own HUD and ki bar are in, the host overlay is not). Frames land in
<out>/<name>/frames/c<clip>_f<NNNNN>.png; CAP.clip("label") starts a clip. MELEE_AUDIO_DUMP writes the mix to <out>/<name>/audio.wav
(MELEE_VOLUME=0 keeps the speakers silent; the dump is full scale). The run is realtime (60 Hz) so audio and frames agree.
Reads the exe and mods; it copies the exe into its own build root (_build/agents/gokumedia), never touching another lane's.
Everything lands under _build/goku-media (git-ignored).
"""
import argparse, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = Path(os.environ.get('GW_ROOT') or 'E:/Projects/Melee Workspace')
STAGE_WT = MAIN / 'worktrees/gokustage'
GAME = os.environ.get('GW_MELEE') or str(MAIN / 'worktrees/gokustage-game')
BROOT = Path(os.environ.get('GW_BUILD_ROOT') or MAIN / '_build/agents/gokumedia')
OUT = MAIN / '_build/goku-media'
GIT_BASH = os.environ.get('GW_GIT_BASH', 'C:/Program Files/Git/bin/bash.exe')


def iso():
    for line in (MAIN / '.env').read_text(encoding='utf-8').splitlines():
        m = re.match(r'\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*(.+)', line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise SystemExit('GW_ISO_VANILLA missing')


def sync_exe(exe):
    exe = Path(exe)
    BROOT.mkdir(parents=True, exist_ok=True)
    for f in ('melee-pc.exe', 'melee-pc.map', 'SDL3.dll', 'webgpu_dawn.dll'):
        s = exe.parent / f
        d = BROOT / f
        if s.exists() and (not d.exists() or s.stat().st_mtime != d.stat().st_mtime or s.stat().st_size != d.stat().st_size):
            shutil.copy2(s, d)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('script'); ap.add_argument('--name', required=True)
    ap.add_argument('--vs', default='mario'); ap.add_argument('--stage', default='fd'); ap.add_argument('--p1', default='geno:goku-xv2/hu')
    ap.add_argument('--res', default='1280x720'); ap.add_argument('--max-seconds', default='600')
    ap.add_argument('--exe', default=str(MAIN / '_build/agents/gokustage/melee-pc.exe'))
    ap.add_argument('--mods', default=str(STAGE_WT / '_build/goku-xv2/combo-package/mods'))
    ap.add_argument('--cfg', action='append', default=[]); ap.add_argument('--no-audio', action='store_true')
    ap.add_argument('--visible', action='store_true')
    ap.add_argument('--hitboxes', action='store_true', help='keep the LAB hitbox/hurtbox overlay (default: the CLEAN display)')
    a = ap.parse_args()
    sync_exe(a.exe)
    if not a.hitboxes:   # the LAB starts in the hitbox display; a throwaway copy of the package starts it CLEAN (as ports/goku-xv2/tools/kame_run.py --clean)
        dst = OUT / '_mods_clean'
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(a.mods, dst)
        lab = dst / 'geno-lab/scripts/lab.lua'
        t = lab.read_text(encoding='utf-8')
        assert 'mode = 2, hidden' in t or 'mode = 1, hidden' in t, 'lab.lua start mode not found'
        lab.write_text(t.replace('mode = 2, hidden', 'mode = 1, hidden', 1), encoding='utf-8')
        a.mods = str(dst)
    kv = dict(c.split('=', 1) for c in a.cfg)
    w, h = a.res.split('x')
    gen = HERE / 'lua' / ('_gen_' + a.name + '.lua')
    src = Path(a.script) if Path(a.script).is_absolute() else HERE / a.script
    gen.write_text('CFG={' + ','.join('%s=%r' % (k, v) for k, v in kv.items()) + '}\n' + (HERE / 'lua/cap.lua').read_text(encoding='utf-8')
                   + '\n' + src.read_text(encoding='utf-8'), encoding='utf-8')
    dest = OUT / a.name
    if dest.exists():
        shutil.rmtree(dest)
    (dest / 'frames').mkdir(parents=True)
    p2 = a.vs if '/' in a.vs else a.vs + '/cpu0'
    off = '100' if a.visible else '30000'
    env = dict(os.environ)
    env.update({'GW_ROOT': str(MAIN), 'GW_MELEE': GAME, 'GW_BUILD_ROOT': str(BROOT), 'MELEE_MODS_DIR': a.mods,
                'MELEE_SCENE': f'mode=lab;p1={a.p1};p2={p2};stage={a.stage};items=off;time=0',
                'MELEE_PAD_SCRIPT': gen.as_posix(), 'MELEE_UNATTENDED': '1', 'MELEE_MAX_SECONDS': a.max_seconds,
                'MELEE_LAB_UI': '0', 'MELEE_TURBO': '0', 'MELEE_WINDOW_X': off, 'MELEE_WINDOW_Y': off,
                'MELEE_WINDOW_W': w, 'MELEE_WINDOW_H': h, 'MELEE_BIND_DUMMY': '1', 'MELEE_VOLUME': '0',
                'MELEE_RUN_LABEL': 'Goku media ' + a.name})
    runname = 'm-' + a.name + '-' + time.strftime('%H%M%S')
    run = BROOT / 'runs' / runname
    if not a.no_audio:
        env['MELEE_AUDIO_DUMP'] = (run / 'audio.wav').as_posix()
    with open(dest / 'run.txt', 'w', encoding='utf-8') as fh:
        r = subprocess.run([GIT_BASH, (MAIN / 'tools/port/run.sh').as_posix(), '--max-seconds', a.max_seconds, runname, '--iso', iso()],
                           cwd=GAME, env=env, stdout=fh, stderr=subprocess.STDOUT)
    gen.unlink(missing_ok=True)
    log = run / 'melee-pc.log'
    text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
    (dest / 'melee-pc.log').write_text(text, encoding='utf-8')
    n = 0
    for p in list(run.rglob('c*_f*.png')):
        shutil.move(str(p), dest / 'frames' / p.name); n += 1
    if (run / 'audio.wav').exists():
        shutil.move(str(run / 'audio.wav'), dest / 'audio.wav')
    marks = re.findall(r'CAP (.*)', text)
    (dest / 'marks.txt').write_text('\n'.join(marks), encoding='utf-8')
    print(f'run={run}\nframes={n} marks={len(marks)} audio={(dest / "audio.wav").exists()} exit={r.returncode}\nout={dest}')
    print('\n'.join(l for l in marks if 'FAIL' in l or 'DONE' in l))


if __name__ == '__main__':
    main()
