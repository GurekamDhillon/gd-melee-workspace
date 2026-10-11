"""Read a Kamehameha audio capture (the engine's final-mix WAV, kame_audio.lua) and its log: when each charge sound started, the loudness per second, and what is audible
after the release. Numbers only (nothing is played).

    python ports/goku-xv2/tools/kame_audio_check.py RUN_NAME WAV [--hum-exit --clips PACKAGE/files]
"""
import argparse, json, re, wave
from pathlib import Path


def hum_exit_check(log, x, sr, clips):
    """Measure the source hum in the final mix, including music, without playing it.

    kame_interrupt leaves >200 ms of Hum4 before exit. Align that prefix by matched
    filtering, then project the post-stop mix onto the remaining source samples.
    A ringing clip has gain near 1; a stopped clip leaves only uncorrelated music.
    """
    import numpy as np
    from scipy.signal import correlate
    marker = re.search(r'\[frame=(\d+)[^\]]*\].*KAMEHUM exit=\d+ act=(\w+) state=(\w+)', log)
    if not marker or 'KAMEHUM FAIL' in log:
        raise ValueError('interruption scenario did not reach its asserted exit')
    exit_frame, act, state = int(marker[1]), marker[2], marker[3]
    starts = [(int(m[1]), m[2]) for m in re.finditer(r'\[frame=(\d+)[^\]]*\] geno: Goku: plays its own voice line \((GnKame(?:Hum\d|SeCharge))\.gnsnd\)', log) if int(m[1]) <= exit_frame]
    if not starts:
        raise ValueError('no hum started')
    hum_frame, name = starts[-1]
    ref = np.frombuffer((Path(clips) / (name + '.gnsnd')).read_bytes()[32:], dtype='>i2').astype(float) / 32768
    prefix = ref[:sr // 5]
    at = int(correlate(x, prefix, mode='valid', method='fft').argmax())
    pre_gain = float(x[at:at + len(prefix)] @ prefix / (prefix @ prefix))
    stops = [(int(m[1]), int(m[2])) for m in re.finditer(r'\[frame=(\d+)[^\]]*\] geno: Goku: (?:state exit to -?\d+|stop id 540001) cut (\d+)', log)
             if int(m[1]) >= hum_frame and int(m[2]) > 0]
    cut_frame = stops[0][0] if stops else exit_frame
    # Stay in the high-energy portion of the clip; its final fade is too quiet to measure.
    lo = round(((cut_frame - hum_frame) / 60 + 0.08) * sr)
    hi = min(lo + sr // 2, round(1.1 * sr), len(ref))
    if hi - lo < sr // 5 or at + hi > len(x):
        raise ValueError('capture has too little hum after the exit to measure')
    tail = ref[lo:hi]
    post_gain = float(x[at + lo:at + hi] @ tail / (tail @ tail))
    shot = re.search(r'\[frame=(\d+)[^\]]*\].*own voice line \(GnKameSeShot.gnsnd\)', log)
    shout = re.search(r'\[frame=(\d+)[^\]]*\].*own voice line \(GnKameVoxFire.gnsnd\)', log)
    timing_ok = bool(stops) and (cut_frame <= exit_frame if act != 'fire' else
                                shot is not None and shout is not None and cut_frame == int(shot[1]) < int(shout[1]))
    result = dict(action=act, state=state, hum=name, hum_sample_start=at, sample_rate=sr,
                  hum_start_frame=hum_frame, exit_frame=exit_frame, stop_frame=stops[0][0] if stops else None,
                  pre_gain=round(pre_gain, 4), post_gain=round(post_gain, 4),
                  shot_after_exit=int(shot[1]) - exit_frame if shot else None,
                  shout_after_exit=int(shout[1]) - exit_frame if shout else None,
                  pass_=bool(timing_ok and 0.6 < pre_gain < 1.4 and abs(post_gain) < 0.12))
    print('HUMCHECK ' + json.dumps(result, sort_keys=True))
    return result['pass_']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('run'); ap.add_argument('wav')
    ap.add_argument('--hum-exit', action='store_true', help='assert a kame_interrupt.lua capture actually cuts the hum')
    ap.add_argument('--clips', type=Path, help='package files/ directory containing the source .gnsnd clips')
    a = ap.parse_args()
    run, wav = a.run, a.wav
    import numpy as np
    root = Path(__import__('os').environ.get('GW_BUILD_ROOT') or 'E:/Projects/Melee Workspace/_build/agents/kamepol')
    log = (root / 'runs' / run / 'melee-pc.log').read_text(encoding='utf-8', errors='replace')
    with wave.open(wav, 'rb') as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float64)
    if ch == 2:
        x = x.reshape(-1, 2).mean(axis=1)
    x /= 32768.0
    if a.hum_exit:
        if not a.clips:
            ap.error('--hum-exit needs --clips')
        try:
            return 0 if hum_exit_check(log, x, sr, a.clips) else 1
        except ValueError as e:
            print('HUMCHECK FAIL ' + str(e))
            return 1
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
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
