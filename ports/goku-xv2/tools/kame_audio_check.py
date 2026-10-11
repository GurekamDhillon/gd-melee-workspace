"""Read a Kamehameha audio capture (the engine's final-mix WAV, kame_audio.lua) and its log: when each charge sound started, the loudness per second, and what is audible
after the release. Numbers only (nothing is played).

    python ports/goku-xv2/tools/kame_audio_check.py RUN_NAME WAV [--fps 60]
"""
import re, sys, wave
from pathlib import Path


def main():
    run, wav = sys.argv[1], sys.argv[2]
    import numpy as np
    root = Path(__import__('os').environ.get('GW_BUILD_ROOT') or 'E:/Projects/Melee Workspace/_build/agents/kamepol')
    log = (root / 'runs' / run / 'melee-pc.log').read_text(encoding='utf-8', errors='replace')
    with wave.open(wav, 'rb') as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float64)
    if ch == 2:
        x = x.reshape(-1, 2).mean(axis=1)
    x /= 32768.0
    ev = []
    for m in re.finditer(r'\[frame=(\d+)[^\]]*\] geno: Goku: plays its own voice line \((\w+)\.gnsnd\)', log):
        ev.append((int(m.group(1)), m.group(2)))
    stops = [(int(m.group(1)), m.group(2)) for m in re.finditer(r'\[frame=(\d+)[^\]]*\] geno: Goku: stop id 540001 cut (\d+)', log)]
    start = int(re.search(r'KAMEAUDIO start=(\d+)', log).group(1)); fire = int(re.search(r'KAMEAUDIO fire=(\d+)', log).group(1))
    print('wav %.1f s %d Hz; B at frame %d, fire press at frame %d (%.1f s after B)' % (len(x) / sr, sr, start, fire, (fire - start) / 60.0))
    print('sounds (frames after B): ' + ' '.join('%s@%d' % (n, f - start) for f, n in ev if f >= start)[:1500])
    print('stop ids: ' + (', '.join('frame %d (+%d) cut %s' % (f, f - start, c) for f, c in stops) or 'none'))
    # the WAV starts with the process: find the sample offset of the first Hum clip by the log's frame clock (60 fps game frames since process start; the dump
    # runs on the mixer clock) - the loudness per second is relative to the dump's own start, the hum starts within the first charge frames
    win = sr // 2
    rms = [20 * np.log10(max(1e-6, float(np.sqrt(np.mean(x[i:i + win] ** 2))))) for i in range(0, len(x) - win, win)]
    print('loudness dBFS per 0.5 s: ' + ' '.join('%d' % r for r in rms))


if __name__ == '__main__':
    main()
