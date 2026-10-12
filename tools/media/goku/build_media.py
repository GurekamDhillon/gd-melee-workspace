"""Goku alpha media pipeline: capture (video + audio passes), clips with overlays, GIFs, the highlight reel.

    python tools/media/goku/build_media.py capture [--only kame,ground,flight,ki] [--exe E] [--mods M]
    python tools/media/goku/build_media.py clips   [--only kame_tap,rush]       # needs capture + overlays (atlas_overlay.py)
    python tools/media/goku/build_media.py gifs
    python tools/media/goku/build_media.py reel
    python tools/media/goku/build_media.py all

Everything lands under _build/goku-media (git-ignored): <script>/ (video pass: frames), <script>_audio/ (audio pass: audio.wav),
clips/<id>.mp4, gifs/<id>.gif, reel/. Frames come from a turbo pass (every logic frame shot once), sound from a realtime pass of
the same Lua (identical logic, checked by comparing the P1 motion trace), joined by the game clock: wav time = (ms - 2000) / 1000
where ms is the "[frame=N ms=M]" stamp on the CLIP mark (measured with gd.play_sound at known frames).
Discord's per-file limit is 10 MiB on this server (boost tier 0): clips are rate-fitted under TARGET_MB.
"""
import argparse, json, re, subprocess, sys, shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from atlas_style import MEDIA  # noqa: E402

SCRIPTS = {'kame': 'lua/clips_kame.lua', 'ground': 'lua/clips_ground.lua', 'flight': 'lua/clips_flight.lua', 'ki': 'lua/clips_ki.lua'}
VS = 'captain'
TARGET_MB = 9.3
AUDIO_START_MS = 2000      # wav t=0 is game clock ms 2000 (measured)
FFMPEG = shutil.which('ffmpeg') or 'ffmpeg'


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise SystemExit('FAILED: %s\n%s' % (' '.join(map(str, cmd))[:300], r.stderr[-1500:]))
    return r


def capture(only, extra):
    names = [n for n in SCRIPTS if not only or n in only]
    def go(n, kind):
        cmd = [sys.executable, str(HERE / 'capture_run.py'), SCRIPTS[n], '--name', n, '--vs', VS, '--pass', kind] + extra
        r = subprocess.run(cmd, capture_output=True, text=True)
        print('[%s %s] %s' % (n, kind, ' '.join(r.stdout.strip().splitlines()[-3:])))
        return r.returncode
    for kind in ('video', 'audio'):
        import time
        def staggered(i_n):
            time.sleep(6 * i_n[0])      # run.sh prunes and stamps sandboxes at start; stagger the launches
            return go(i_n[1], kind)
        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(staggered, list(enumerate(names))))


def clip_index():
    """label -> dict(script, n, frames, ms0, wav) from the marks of every captured script."""
    idx = {}
    for n in SCRIPTS:
        v, a = MEDIA / n / 'marks.txt', MEDIA / (n + '_audio') / 'marks.txt'
        if not v.exists():
            continue
        vm = {}
        for l in v.read_text(encoding='utf-8').splitlines():
            m = re.match(r'ms=(\d+) CLIP (\d+) (\S+)', l)
            if m:
                vm[m.group(2)] = m.group(3)
            m = re.match(r'ms=(\d+) ENDCLIP (\d+) frames=(\d+)', l)
            if m:
                idx.setdefault(vm.get(m.group(2)), {}).update(frames=int(m.group(3)))
        for k, lab in vm.items():
            d = idx.setdefault(lab, {})
            d.update(script=n, n=int(k), dir=MEDIA / n / 'frames')
        if a.exists():
            for l in a.read_text(encoding='utf-8').splitlines():
                m = re.match(r'ms=(\d+) CLIP (\d+) (\S+)', l)
                if m and m.group(3) in idx:
                    idx[m.group(3)].update(ms0=int(m.group(1)), wav=MEDIA / (n + '_audio') / 'audio.wav')
    return idx


def verify():
    """The audio pass must replay the video pass exactly: compare every P1/P2 motion line (clip, frame, name, position)."""
    bad = 0
    for n in SCRIPTS:
        v, a = MEDIA / n / 'marks.txt', MEDIA / (n + '_audio') / 'marks.txt'
        if not (v.exists() and a.exists()):
            print('verify %s: missing pass' % n); bad += 1; continue
        f = lambda p: [re.sub(r'^ms=\d+ ', '', l) for l in p.read_text(encoding='utf-8').splitlines() if ' MOT ' in l or l.startswith('ms=') and 'FAIL' in l]
        fv, fa = f(v), f(a)
        ok = fv == fa
        print('verify %s: %d motion lines, passes %s%s' % (n, len(fv), 'IDENTICAL' if ok else 'DIFFER',
              '' if ok else ' (first diff: %s | %s)' % next(((x, y) for x, y in zip(fv, fa) if x != y), ('len', 'len'))))
        bad += not ok
    return bad


def probe_mb(p):
    return Path(p).stat().st_size / 1048576


def encode(cmd_in, out, dur, w, h, fps, target_mb):
    """Encode, then re-encode at a fitted bitrate when over target."""
    abr = 128
    for attempt in range(3):
        if attempt == 0:
            vopts = ['-crf', '21', '-maxrate', '14M', '-bufsize', '28M']
        else:
            kbps = int((target_mb * 8192 / dur) - abr) * (0.93 ** attempt)
            vopts = ['-b:v', '%dk' % kbps, '-maxrate', '%dk' % (kbps * 1.2), '-bufsize', '%dk' % (kbps * 2)]
        run([FFMPEG, '-v', 'error', '-y'] + cmd_in + ['-c:v', 'libx264', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-r', str(fps)] + vopts
            + ['-c:a', 'aac', '-b:a', '%dk' % abr, '-movflags', '+faststart', str(out)])
        if probe_mb(out) <= target_mb:
            return
    print('WARNING: %s is %.1f MB (> %.1f)' % (Path(out).name, probe_mb(out), target_mb))


def clips(only):
    spec = json.loads((HERE / 'shots.json').read_text(encoding='utf-8'))
    idx = clip_index()
    ov = MEDIA / 'overlays'
    out = MEDIA / 'clips'
    out.mkdir(parents=True, exist_ok=True)
    for s in spec['shots']:
        if only and s['id'] not in only:
            continue
        lab = s.get('clip', s['id'])
        c = idx.get(lab)
        if not c or 'dir' not in c:
            print('skip %s: no capture for clip %s' % (s['id'], lab)); continue
        f0, f1 = s.get('trim', [1, c.get('frames', 0)])
        n = f1 - f0 + 1
        dur = n / 60
        ltf = ov / ('lt_%s.png' % s['id'])
        fi = 0.35
        lt_in, lt_out = s.get('lt', [0.3, dur - 0.4])
        inputs = ['-framerate', '60', '-start_number', str(f0), '-i', str(c['dir'] / ('c%02d_f%%05d.png' % c['n'])),
                  '-loop', '1', '-i', str(ov / 'corner.png'), '-loop', '1', '-i', str(ltf)]
        fc = ('[0:v]trim=end_frame=%d,scale=1920:1080:flags=lanczos,setsar=1,fade=t=in:st=0:d=0.15,fade=t=out:st=%.3f:d=0.25[b];'
              '[1:v]format=rgba[c];[2:v]format=rgba,fade=t=in:st=%.2f:d=%.2f:alpha=1,fade=t=out:st=%.2f:d=%.2f:alpha=1[l];'
              '[b][c]overlay=0:0:shortest=1[x];[x][l]overlay=0:0:shortest=1,format=yuv420p[v]') % (n, dur - 0.25, lt_in, fi, lt_out, fi)
        amap = []
        if 'wav' in c:
            t0 = (c['ms0'] - AUDIO_START_MS) / 1000 + (f0 - 1) / 60
            inputs += ['-ss', '%.3f' % t0, '-t', '%.3f' % dur, '-i', str(c['wav'])]
            fc += ';[3:a]aresample=44100,afade=t=in:st=0:d=0.1,afade=t=out:st=%.3f:d=0.25[a]' % (dur - 0.25)
            amap = ['-map', '[a]']
        enc_in = inputs + ['-filter_complex', fc, '-map', '[v]'] + amap + ['-t', '%.3f' % dur]
        encode(enc_in, out / (s['id'] + '.mp4'), dur, 1920, 1080, 60, TARGET_MB)
        print('%s: %.1f s %.1f MB' % (s['id'], dur, probe_mb(out / (s['id'] + '.mp4'))))


def gifs():
    out = MEDIA / 'gifs'
    out.mkdir(exist_ok=True)
    for p in sorted((MEDIA / 'clips').glob('*.mp4')):
        g = out / (p.stem + '.gif')
        run([FFMPEG, '-v', 'error', '-y', '-i', str(p), '-vf',
             'fps=20,scale=640:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4', str(g)])
        print('%s: %.1f MB' % (g.name, probe_mb(g)))


def reel():
    """Title card, the best clips, end card: 720p30 under the Discord limit, plus a 1080p60 copy to host elsewhere."""
    spec = json.loads((HERE / 'shots.json').read_text(encoding='utf-8'))
    ids = spec.get('reel', [])
    out = MEDIA / 'reel'
    out.mkdir(exist_ok=True)
    ov = MEDIA / 'overlays'
    parts = []
    def card_part(png, secs, name):
        p = out / (name + '.mp4')
        run([FFMPEG, '-v', 'error', '-y', '-loop', '1', '-framerate', '60', '-t', str(secs), '-i', str(png), '-f', 'lavfi', '-t', str(secs),
             '-i', 'anullsrc=r=44100:cl=stereo', '-vf', 'scale=1920:1080,fade=t=in:st=0:d=0.3,fade=t=out:st=%.2f:d=0.3,format=yuv420p' % (secs - 0.3),
             '-c:v', 'libx264', '-crf', '20', '-r', '60', '-c:a', 'aac', '-b:a', '128k', '-shortest', str(p)])
        return p
    parts.append(card_part(ov / 'card_title.png', 3.5, 'p_title'))
    for i in ids:
        p = MEDIA / 'clips' / (i + '.mp4')
        if p.exists():
            parts.append(p)
    parts.append(card_part(ov / 'card_end.png', 4.5, 'p_end'))
    lst = out / 'list.txt'
    lst.write_text(''.join("file '%s'\n" % str(p).replace('\\', '/') for p in parts), encoding='utf-8')
    hq = out / 'goku_alpha_reel_1080p60.mp4'
    run([FFMPEG, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c:v', 'libx264', '-crf', '20', '-preset', 'slow',
         '-pix_fmt', 'yuv420p', '-r', '60', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(hq)])
    dur = float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(hq)]).stdout.strip())
    small = out / 'goku_alpha_reel_720p30.mp4'
    encode(['-i', str(hq), '-vf', 'scale=1280:720:flags=lanczos'], small, dur, 1280, 720, 30, TARGET_MB)
    print('reel: %.1f s; 1080p60 %.1f MB; 720p30 %.1f MB' % (dur, probe_mb(hq), probe_mb(small)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=['capture', 'verify', 'clips', 'gifs', 'reel', 'all'])
    ap.add_argument('--only', default='')
    ap.add_argument('--exe'); ap.add_argument('--mods')
    a = ap.parse_args()
    only = [x for x in a.only.split(',') if x]
    extra = (['--exe', a.exe] if a.exe else []) + (['--mods', a.mods] if a.mods else [])
    if a.step in ('capture', 'all'):
        capture(only, extra)
    if a.step in ('verify', 'all'):
        verify()
    if a.step in ('clips', 'all'):
        clips(only)
    if a.step in ('gifs', 'all'):
        gifs()
    if a.step in ('reel', 'all'):
        reel()


if __name__ == '__main__':
    main()
