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
    'GnKameVoxCharge':      ('CAR_BTL_S000_KMH_GOK_VOX{v}', '0_BDB_GOK_071.wav'),
    'GnKameSeCharge':       ('CAR_BTL_S000_KMH_SE', '2_4_charge.wav'),
    'GnKameVoxFire':        ('CAR_BTL_S000_KMH_GOK_VOX{v}', '1_BDB_GOK_072.wav'),
    'GnKameSeShot':         ('CAR_BTL_S000_KMH_SE', '3_4_shot.wav'),
    'GnKameSuperSeCharge':  ('CAR_BTL_U000_CKM_SE', '0_Superkamehame_charge.wav'),
    'GnKameSuperVoxFire':   ('CAR_BTL_U000_CKM_GOK_VOX{v}', '1_L1_GOK_M1_088.wav'),
    'GnKameSuperSeShot':    ('CAR_BTL_U000_CKM_SE', '1_Superkamehame_shot.wav'),
}
# retail sound id -> clip (the scripts in moves/kame_*.genoasm play these ids)
BINDINGS = {200121: 'GnKameVoxCharge', 200124: 'GnKameSeCharge', 200115: 'GnKameVoxFire', 200118: 'GnKameSeShot',
            200127: 'GnKameSuperSeCharge', 200130: 'GnKameSuperVoxFire', 200112: 'GnKameSuperSeShot'}


def read_wav(p):
    with wave.open(str(p), 'rb') as w:
        assert w.getsampwidth() == 2 and w.getnchannels() in (1, 2), p
        n, ch, rate = w.getnframes(), w.getnchannels(), w.getframerate()
        data = struct.unpack('<%dh' % (n * ch), w.readframes(n))
    if ch == 2:
        data = [(data[i] + data[i + 1]) // 2 for i in range(0, len(data), 2)]
    return list(data), rate


def convert(lang='jp', out=OUT):
    from tools.geno.audio import convert_wav
    out.mkdir(parents=True, exist_ok=True)
    done = {}
    for name, (folder, f) in CLIPS.items():
        src = WAV / folder.format(v='_en' if lang == 'en' else '') / f
        if not src.exists():
            print('missing', src)
            continue
        data, rate = read_wav(src)
        peak = max(1, max(abs(x) for x in data))
        g = 0.89 * 32767 / peak
        tmp = out / (name + '.wav')
        with wave.open(str(tmp), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
            w.writeframes(struct.pack('<%dh' % len(data), *[int(max(-32768, min(32767, x * g))) for x in data]))
        convert_wav(tmp, out / (name + '.gnsnd'))
        done[name] = round(len(data) / rate, 2)
    return done


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--lang', choices=('jp', 'en'), default='jp')
    a = ap.parse_args()
    print(a.lang, convert(a.lang))
