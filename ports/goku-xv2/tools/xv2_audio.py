"""Convert Xenoverse 2's Kamehameha voice and sound effects into Geno .gnsnd clips, LOCALLY (nothing here is committed).

    python ports/goku-xv2/tools/xv2_audio.py [--lang jp|en]   -> _build/goku-xv2/audio/Gn*.gnsnd

Inputs: the WAVs written by tools/xv2x/audio (`Xv2Audio acb ...`) under _build/xv2-kame/audio/wav/, decoded from the game's own ACBs:
  sound/SE/Battle/Skill/CAR_BTL_S000_KMH_SE.acb       cue 0 kamehame_Charge -> 4_charge (waveform 2),  cue 1 kamehame_shot -> 4_shot (waveform 3)
  sound/VOX/Battle/Skill/[en/]CAR_BTL_S000_KMH_GOK_VOX.acb   cue 0 BDB_GOK_071 (the "ka-me-ha-me" charge line), cue 1 BDB_GOK_072 (the release shout)
  sound/SE/Battle/Skill/CAR_BTL_U000_CKM_SE.acb        cue 0 Superkamehame_charge, cue 1 Superkamehame_shot
  sound/VOX/Battle/Skill/[en/]CAR_BTL_U000_CKM_GOK_VOX.acb   cue 0 BDB_GOK_071 (same line), cue 1 L1_GOK_M1_088 (the Super Kamehameha shout)
The two SE sequence cues of the KMH ACB (0 and 1) carry no waveform of their own; they are named for the waveforms 2 and 3 (4_charge, 4_shot).
BAC timing (skill 000_GOK_KMH entry 0): SE cue 0 and VOX cue 0 at frame 0, VOX cue 1 at frame 58 (2 frames after the projectile).
Japanese is the default (the owner's rule); --lang en uses the English ACBs. Each clip is peak-normalised to -1 dBFS and written mono 32 kHz.
The clips are bound as audio.voice rows on retail sound ids the Kamehameha scripts play (BINDINGS; they are Mewtwo Shadow Ball ids, which Goku never plays).
"""
import argparse
import struct
import sys
import wave
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
ROOT = PORT.parents[1]
WAV = ROOT / '_build/xv2-kame/audio/wav'
OUT = ROOT / '_build/goku-xv2/audio'
sys.path.insert(0, str(ROOT))

# clip name -> (folder, file) ; {v} = '' (Japanese) or '_en'
CLIPS = {
    'GnKameSeCharge':       ('CAR_BTL_S000_KMH_SE', '2_4_charge.wav'),
    'GnKameVoxFire':        ('CAR_BTL_S000_KMH_GOK_VOX{v}', '1_BDB_GOK_072.wav'),
    'GnKameSeShot':         ('CAR_BTL_S000_KMH_SE', '3_4_shot.wav'),
    'GnKameSuperSeCharge':  ('CAR_BTL_U000_CKM_SE', '0_Superkamehame_charge.wav'),
    'GnKameSuperVoxFire':   ('CAR_BTL_U000_CKM_GOK_VOX{v}', '1_L1_GOK_M1_088.wav'),
    'GnKameSuperSeShot':    ('CAR_BTL_U000_CKM_SE', '1_Superkamehame_shot.wav'),
}
# retail sound id -> clip (the scripts in moves/kame_*.genoasm play these ids)
# The chant (VOX cue 0, BDB_GOK_071, 0.90 s "ka-me-ha-me") is cut into its four syllables at the energy minima so the charge can say "ka... me... ha... me..." across its
# length (SYLLABLES: seconds in the source clip); XV2 plays it in one go while it holds the pose. Cue 1 (BDB_GOK_072) is the "HA!" on release.
SYLLABLES = {'GnKameVox1': (0.0, 0.205), 'GnKameVox2': (0.205, 0.325), 'GnKameVox3': (0.325, 0.51), 'GnKameVox4': (0.51, 0.905)}
BINDINGS = {200121: 'GnKameVox1', 200124: 'GnKameVox2', 200127: 'GnKameVox3', 200130: 'GnKameVox4', 200115: 'GnKameVoxFire', 200118: 'GnKameSeShot', 200100: 'GnKameSeCharge', 200133: 'GnKameHum2', 200136: 'GnKameHum3', 200139: 'GnKameHum4',
            200103: 'GnKameSuperSeCharge', 200106: 'GnKameSuperVoxFire', 200109: 'GnKameSuperSeShot'}


# the charge hum rises in pitch between the chant beats (owner, 2026-10-10: a 10 s charge): the SE 4_charge played back faster, i.e. resampled up by these ratios
HUM = {'GnKameHum2': 1.15, 'GnKameHum3': 1.32, 'GnKameHum4': 1.52}
PEAK = {'Vox': 0.55, 'Se': 0.40}   # peak (fraction of full scale) per clip kind: a voice and an SE start together, their sum must not clip the mix


def read_wav(p):
    with wave.open(str(p), 'rb') as w:
        assert w.getsampwidth() == 2 and w.getnchannels() in (1, 2), p
        n, ch, rate = w.getnframes(), w.getnchannels(), w.getframerate()
        data = struct.unpack('<%dh' % (n * ch), w.readframes(n))
    if ch == 2:
        data = [(data[i] + data[i + 1]) / 2 for i in range(0, len(data), 2)]
    return list(data), rate


def resample(data, rate, target=32000):
    """Band-limited polyphase resample (Kaiser, beta 8.6). The old path (tools/geno/audio.py) linearly interpolated with no low-pass,
    which aliased: measured 16 to 31 dB below the signal as error against this resample."""
    import numpy as np
    from math import gcd
    from scipy.signal import resample_poly
    if rate == target:
        return np.array(data, float)
    g = gcd(target, rate)
    return resample_poly(np.array(data, float), target // g, rate // g, window=('kaiser', 8.6))


def convert(lang='jp', out=OUT):
    import numpy as np
    from tools.geno.audio import convert_wav
    out.mkdir(parents=True, exist_ok=True)
    done = {}
    for name, (folder, f) in CLIPS.items():
        src = WAV / folder.format(v='_en' if lang == 'en' else '') / f
        if not src.exists():
            print('missing', src)
            continue
        data, rate = read_wav(src)
        x = resample(data, rate)
        x = x - x.mean()
        kind = 'Vox' if 'Vox' in name else 'Se'
        n = len(x); fade = 160
        x[-fade:] *= np.linspace(1, 0, fade)   # a 5 ms fade-out so a clip never ends on a click
        x *= PEAK[kind] * 32767 / max(1.0, np.abs(x).max())
        tmp = out / (name + '.wav')
        with wave.open(str(tmp), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(32000)
            w.writeframes(np.round(x).astype('<i2').tobytes())
        convert_wav(tmp, out / (name + '.gnsnd'))   # already 32 kHz: stored as is, no second resample
        done[name] = round(n / 32000, 2)
    src = WAV / 'CAR_BTL_S000_KMH_SE' / '2_4_charge.wav'
    if src.exists():
        from scipy.signal import resample_poly
        data, rate = read_wav(src)
        base = resample(data, rate)
        base = base - base.mean()
        for name, ratio in HUM.items():
            x = resample_poly(base, 100, int(round(ratio * 100)))
            x[-160:] *= np.linspace(1, 0, 160)
            x *= PEAK['Se'] * 32767 / max(1.0, np.abs(x).max())
            tmp = out / (name + '.wav')
            with wave.open(str(tmp), 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(32000)
                w.writeframes(np.round(x).astype('<i2').tobytes())
            convert_wav(tmp, out / (name + '.gnsnd'))
            done[name] = round(len(x) / 32000, 2)
    src = WAV / 'CAR_BTL_S000_KMH_GOK_VOX{v}'.format(v='_en' if lang == 'en' else '') / '0_BDB_GOK_071.wav'
    data, rate = read_wav(src)
    x = resample(data, rate)
    x = x - x.mean()
    x *= PEAK['Vox'] * 32767 / max(1.0, np.abs(x).max())     # one gain for all four, so the syllables keep their relative levels
    for name, (a, b) in SYLLABLES.items():
        seg = x[int(a * 32000):int(b * 32000)].copy()
        k = 256   # 8 ms fades at both cuts: no click
        seg[:k] *= np.linspace(0, 1, k); seg[-k:] *= np.linspace(1, 0, k)
        tmp = out / (name + '.wav')
        with wave.open(str(tmp), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(32000)
            w.writeframes(np.round(seg).astype('<i2').tobytes())
        convert_wav(tmp, out / (name + '.gnsnd'))
        done[name] = round(len(seg) / 32000, 3)
    return done


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--lang', choices=('jp', 'en'), default='jp')
    a = ap.parse_args()
    print(a.lang, convert(a.lang))
