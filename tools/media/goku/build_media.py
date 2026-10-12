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
        for attempt in range(3):          # the game can still die under load (screenshot readback): rerun the whole script
            r = subprocess.run(cmd, capture_output=True, text=True)
            ok = 'exit=0' in r.stdout
            print('[%s %s try %d] %s' % (n, kind, attempt + 1, ' '.join(r.stdout.strip().splitlines()[-3:])), flush=True)
            if ok:
                break
        return r.returncode
    for kind in ('video', 'audio'):
        import time
        def staggered(i_n):
            time.sleep(6 * i_n[0])      # run.sh prunes and stamps sandboxes at start; stagger the launches
            return go(i_n[1], kind)
        # video passes shoot every frame through a PNG writer thread: two games at once can overflow it (crash), so one at a time
        with ThreadPoolExecutor(max_workers=1 if kind == 'video' else 4) as ex:
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


def motions(path):
    """clip number -> [(frame, port, name)] from a marks file."""
    out = {}
    for l in Path(path).read_text(encoding='utf-8').splitlines():
        m = re.match(r'ms=\d+ MOT c(\d+) f(\d+) P(\d) (\w+)', l)
        if m:
            out.setdefault(m.group(1), []).append((int(m.group(2)), int(m.group(3)), m.group(4)))
    return out


def audio_shift(vm, am):
    """Frames by which the audio pass reaches P1's first non-Wait motion before (negative) / after the video pass does.
    The stepped video pass sees an input one or two logic frames later than the realtime audio pass; the sound is shifted to match."""
    fv = next((f for f, p, n in vm if p == 1 and n != 'Wait'), None)
    fa = next((f for f, p, n in am if p == 1 and n != 'Wait'), None)
    return 0 if fv is None or fa is None else fa - fv


def verify():
    """The audio pass replays the video pass's input timing; the state sequence of every clip must match (frames may be 1-2 off)."""
    bad = 0
    for n in SCRIPTS:
        v, a = MEDIA / n / 'marks.txt', MEDIA / (n + '_audio') / 'marks.txt'
        if not (v.exists() and a.exists()):
            print('verify %s: missing pass' % n); bad += 1; continue
        mv, ma = motions(v), motions(a)
        seq = lambda m: {c: [(p, nm) for _, p, nm in l] for c, l in m.items()}
        same = seq(mv) == seq(ma)
        worst = max([abs(x[0] - y[0]) for c in mv for x, y in zip(mv[c], ma.get(c, [])) if x[1:] == y[1:]] or [0])
        shifts = {c: audio_shift(mv[c], ma.get(c, [])) for c in mv}
        print('verify %s: %d clips, state sequences %s, worst frame offset %d, audio shifts %s' % (
            n, len(mv), 'IDENTICAL' if same else 'DIFFER', worst, shifts))
        bad += not same
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


def ki_values(script, clip_n):
    """Per-frame ki (1-based list) of a clip from the KIS lines of the video pass."""
    vals = {}
    for l in (MEDIA / script / 'marks.txt').read_text(encoding='utf-8').splitlines():
        m = re.match(r'ms=\d+ KIS (\d+) (\d+) ([\d,]+)', l)
        if m and int(m.group(1)) == clip_n:
            for i, v in enumerate(m.group(3).split(',')):
                vals[int(m.group(2)) + i] = int(v)
    return vals


def ki_bar_png(v, path):
    """The ki bar for the compositor (the game's own bar is a host overlay and is not in the screenshots): Atlas plate, sun fill,
    white frame when full."""
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(str(HERE.parents[2] / 'menu/Barlow/BarlowCondensed-Bold.ttf'), 30)
    im = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x, y, w, h = 72, 1000, 400, 24
    d.rectangle([x - 14, y - 44, x + w + 14, y + h + 12], fill=(13, 16, 21, 190))
    d.text((x, y - 40), 'KI', font=f, fill=(241, 235, 220, 255))
    d.text((x + w, y - 40), str(v), font=f, fill=(242, 193, 78, 255), anchor='ra')
    d.rectangle([x, y, x + w, y + h], fill=(26, 31, 41, 255))
    d.rectangle([x, y, x + int(w * v / 100), y + h], fill=(242, 193, 78, 255))
    d.rectangle([x, y, x + w, y + h], outline=(241, 235, 220, 255) if v >= 100 else (74, 85, 112, 255), width=3)
    im.save(path)


def ki_overlay_list(script, clip_n, f0, f1, out):
    """A concat list of bar PNGs, one run per ki value, one 60th of a second per frame."""
    vals = ki_values(script, clip_n)
    d = out / 'kibars'
    d.mkdir(parents=True, exist_ok=True)
    runs, last = [], None
    for f in range(f0, f1 + 1):
        v = vals.get(f, last if last is not None else 0)
        if runs and runs[-1][0] == v:
            runs[-1][1] += 1
        else:
            runs.append([v, 1])
        last = v
    lines = []
    for v, n in runs:
        p = d / ('k%03d.png' % v)
        if not p.exists():
            ki_bar_png(v, p)
        lines.append("file '%s'\nduration %.5f\n" % (str(p).replace(chr(92), '/'), n / 60))
    lines.append("file '%s'\n" % str(d / ('k%03d.png' % runs[-1][0])).replace(chr(92), '/'))
    lst = out / ('ki_%s_%02d_%d.txt' % (script, clip_n, f0))
    lst.write_text(''.join(lines), encoding='utf-8')
    return lst


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
        kil = ki_overlay_list(c['script'], c['n'], f0, f1, out)
        inputs = ['-framerate', '60', '-start_number', str(f0), '-i', str(c['dir'] / ('c%02d_f%%05d.png' % c['n'])),
                  '-loop', '1', '-i', str(ov / 'corner.png'), '-loop', '1', '-i', str(ltf)]
        fw, fh = [int(x) for x in run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0',
                                       str(c['dir'] / ('c%02d_f%05d.png' % (c['n'], f0)))]).stdout.strip().split(',')]
        if fw / fh > 1.7:        # 16:9 capture
            base = '[0:v]trim=end_frame=%d,scale=1920:1080:flags=lanczos,setsar=1[b0];' % n
        else:                    # 4:3 capture: centred 1440x1080 over a darkened, blurred copy of itself
            base = ('[0:v]trim=end_frame=%d,setsar=1,split[s1][s2];[s1]scale=1920:-2,crop=1920:1080,boxblur=28:4,eq=brightness=-0.32:saturation=0.8[bg];'
                    '[s2]scale=1440:1080:flags=lanczos[fg];[bg][fg]overlay=240:0[b0];') % n
        fc = (base + '[b0]fade=t=in:st=0:d=0.15,fade=t=out:st=%.3f:d=0.25[b];'
              '[1:v]format=rgba[c];[2:v]format=rgba,fade=t=in:st=%.2f:d=%.2f:alpha=1,fade=t=out:st=%.2f:d=%.2f:alpha=1[l];'
              '[b][c]overlay=0:0:shortest=1[x];[x][l]overlay=0:0:shortest=1,format=yuv420p[v]') % (dur - 0.25, lt_in, fi, lt_out, fi)
        amap = []
        if 'wav' in c:
            sh = audio_shift(motions(MEDIA / c['script'] / 'marks.txt').get('%02d' % c['n'], []),
                             motions(MEDIA / (c['script'] + '_audio') / 'marks.txt').get('%02d' % c['n'], []))
            t0 = (c['ms0'] - AUDIO_START_MS) / 1000 + (f0 - 1 + sh) / 60
            inputs += ['-ss', '%.3f' % t0, '-t', '%.3f' % dur, '-i', str(c['wav'])]
            fc += ';[3:a]aresample=44100,afade=t=in:st=0:d=0.1,afade=t=out:st=%.3f:d=0.25[a]' % (dur - 0.25)
            amap = ['-map', '[a]']
        kidx = sum(1 for x in inputs if x == '-i')
        inputs += ['-f', 'concat', '-safe', '0', '-i', str(kil)]
        fc = fc.replace('[x][l]overlay=0:0:shortest=1,format=yuv420p[v]', '[x][l]overlay=0:0:shortest=1[y];[%d:v]fps=60,format=rgba[ki];[y][ki]overlay=0:0:shortest=1,format=yuv420p[v]' % kidx)
        enc_in = inputs + ['-filter_complex', fc, '-map', '[v]'] + amap + ['-t', '%.3f' % dur]
        encode(enc_in, out / (s['id'] + '.mp4'), dur, 1920, 1080, 60, TARGET_MB)
        print('%s: %.1f s %.1f MB' % (s['id'], dur, probe_mb(out / (s['id'] + '.mp4'))))


def stills():
    """In-game screenshots at 1920x1080 (4:3 captures on a blurred backdrop) with the corner mark: shots.json 'stills' = [{name, clip, at}], at = 0..1 of the clip."""
    spec = json.loads((HERE / 'shots.json').read_text(encoding='utf-8'))
    idx = clip_index()
    out = MEDIA / 'stills'
    out.mkdir(exist_ok=True)
    for s in spec.get('stills', []):
        c = idx.get(s['clip'])
        if not c or 'dir' not in c:
            print('skip still %s: no capture' % s['name']); continue
        f = max(1, min(c['frames'], int(c['frames'] * s['at'])))
        src = c['dir'] / ('c%02d_f%05d.png' % (c['n'], f))
        fc = ('[0:v]split[s1][s2];[s1]scale=1920:-2,crop=1920:1080,boxblur=28:4,eq=brightness=-0.32:saturation=0.8[bg];'
              '[s2]scale=1440:1080:flags=lanczos[fg];[bg][fg]overlay=240:0[b];[b][1:v]overlay=0:0')
        run([FFMPEG, '-v', 'error', '-y', '-i', str(src), '-i', str(MEDIA / 'overlays/corner.png'), '-filter_complex', fc, '-frames:v', '1', str(out / (s['name'] + '.png'))])
        print('still %s <- %s frame %d' % (s['name'], s['clip'], f))


def css_still():
    """The art lead's character-select screenshot (Goku, costume 5/5) as a 1920x1080 still: _build/goku-art/css-shots/css-goku-final-c4.png."""
    src = MEDIA.parent / 'goku-art/css-shots/css-goku-final-c4.png'
    if src.exists():
        (MEDIA / 'stills').mkdir(exist_ok=True)
        run([FFMPEG, '-v', 'error', '-y', '-i', str(src), '-vf', 'scale=1920:1080:flags=lanczos', '-frames:v', '1', str(MEDIA / 'stills/css_character_select.png')])
        print('still css_character_select <-', src.name)


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
    if (ov / 'card_costumes.png').exists():
        parts.append(card_part(ov / 'card_costumes.png', 3.0, 'p_costumes'))
    parts.append(card_part(ov / 'card_end.png', 4.0, 'p_end'))
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
    ap.add_argument('step', choices=['capture', 'verify', 'clips', 'stills', 'gifs', 'reel', 'all'])
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
    if a.step in ('stills', 'all'):
        stills()
        css_still()
    if a.step in ('gifs', 'all'):
        gifs()
    if a.step in ('reel', 'all'):
        reel()


if __name__ == '__main__':
    main()
