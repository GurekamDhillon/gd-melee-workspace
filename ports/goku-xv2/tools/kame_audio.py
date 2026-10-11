"""Original Kamehameha sounds (synthesised here, nothing sampled): charge steps, release blast, super blast.

    python ports/goku-xv2/tools/kame_audio.py   -> _build/goku-xv2/audio/*.gnsnd (build.py copies them to the package's files/ and
                                                  binds them as audio.voice rows on retail sound ids the Kamehameha scripts play)
"""
import math
import random
import struct
import sys
import wave
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
ROOT = PORT.parents[1]
OUT = ROOT / '_build/goku-xv2/audio'
RATE = 32000
sys.path.insert(0, str(ROOT))

# retail sound ids the Kamehameha scripts play (they are Mewtwo's Shadow Ball ids, which Goku never plays otherwise): id -> clip
BINDINGS = {200121: 'GnKameStep1', 200124: 'GnKameStep2', 200127: 'GnKameStep3', 200130: 'GnKameStep4',
            200115: 'GnKameFire', 200118: 'GnKameSuper'}


def tone(freqs, ms, amp=0.5, sweep=1.0, attack=0.02, release=0.3, noise=0.0, seed=1):
    rnd = random.Random(seed)
    n = int(RATE * ms / 1000)
    out = []
    ph = [0.0] * len(freqs)
    lp = 0.0
    for i in range(n):
        t = i / n
        env = min(1.0, t / max(attack, 1e-4)) * (1.0 if t < 1 - release else (1 - t) / release)
        s = 0.0
        for k, f in enumerate(freqs):
            ph[k] += 2 * math.pi * f * (1 + (sweep - 1) * t) / RATE
            s += math.sin(ph[k]) / (k + 1)
        if noise:
            lp += 0.15 * ((rnd.random() * 2 - 1) - lp)   # low-passed noise: a rumble
            s += noise * lp * 6
        out.append(int(max(-1, min(1, s * amp * env)) * 32767))
    return out


def write(name, samples):
    OUT.mkdir(parents=True, exist_ok=True)
    wav = OUT / (name + '.wav')
    with wave.open(str(wav), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(struct.pack('<%dh' % len(samples), *samples))
    from tools.geno.audio import convert_wav  # noqa: E402
    convert_wav(wav, OUT / (name + '.gnsnd'))


def main():
    for i, f in enumerate((330, 392, 494, 659)):   # four rising steps; the last is a fuller chord
        write('GnKameStep%d' % (i + 1), tone([f, f * 2, f * 3] if i == 3 else [f, f * 2], 350 + 150 * i, amp=0.35 + 0.1 * i, sweep=1.12, release=0.6, noise=0.05 * i, seed=i))
    write('GnKameFire', tone([110, 220, 330], 900, amp=0.55, sweep=0.7, attack=0.01, release=0.7, noise=0.5, seed=7))
    write('GnKameSuper', tone([73, 146, 220, 440], 1500, amp=0.6, sweep=0.6, attack=0.01, release=0.75, noise=0.7, seed=9))
    print('audio ->', OUT)


if __name__ == '__main__':
    main()
