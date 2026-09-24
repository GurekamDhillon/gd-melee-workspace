"""Which of MK's bank sounds are audible in a game capture (MELEE_AUDIO_DUMP WAV, 32 kHz stereo).

    python sound/tools/wav_detect.py <capture.wav> [--ingame sound/work/ingame_geno.json] [--out ...json]

Each bank sound (brawlmk.ssm sample at its script pitch) is decoded, resampled to 32 kHz and matched against the
capture by normalized cross-correlation (FFT; score 1.0 = the waveform exactly, at any gain). A sound counts as heard
when its best score passes --thr. Sounds sharing one wave (the drill's 011..018 pitches) are told apart by pitch,
since a different pitch is a different waveform at 32 kHz. With --ingame: the sounds the driven plans should have
played (the pass's placed events in the rows MK went through) against those heard."""
import argparse, json, os, sys, wave, struct
import numpy as np
from scipy.signal import fftconvolve
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import ssm as SSM, brsar as BR

ap = argparse.ArgumentParser()
ap.add_argument("wav")
ap.add_argument("--bank", default=None)
ap.add_argument("--report", default=os.path.join(MK, "sound", "work", "sound_report.json"))
ap.add_argument("--ingame", default=None)
ap.add_argument("--thr", type=float, default=0.6)
ap.add_argument("--out", default=None)
a = ap.parse_args()
REP = json.load(open(a.report))
bank = a.bank or os.path.join(MK, "mods-slot", "metaknight-slot", "files", "audio", "us", "brawlmk.ssm")
S = SSM.read_ssm(open(bank, "rb").read())

w = wave.open(a.wav, "rb"); n = w.getnframes(); ch = w.getnchannels(); sr = w.getframerate()
raw = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float64)
x = raw.reshape(-1, ch).mean(axis=1) if ch > 1 else raw
print("capture: %.1f s at %d Hz, rms %.0f" % (len(x) / sr, sr, np.sqrt(np.mean(x ** 2)) if len(x) else 0))

def template(si, pitch, secs=0.35):
    c = S["samples"][si]["chans"][0]; rate = S["samples"][si]["rate"]
    st = (c["cur_addr"] - 2) // 2; nb = c["end_addr"] // 2 - st + 8
    ns = (c["end_addr"] - c["cur_addr"] + 1) * 7 // 8
    pcm = np.array(BR.decode_dsp(S["data"][st:st + nb], c["coefs"], ns), dtype=np.float64)
    step = rate * pitch / sr
    t = np.arange(0, len(pcm) - 1, step)
    y = np.interp(t, np.arange(len(pcm)), pcm)
    # skip leading near-silence, keep the loudest-onset part
    nz = np.nonzero(np.abs(y) > 0.05 * np.max(np.abs(y)))[0]
    y = y[nz[0]:] if len(nz) else y
    return y[:int(secs * sr)]

def ncc(x, t):
    t = t - t.mean(); tn = np.sqrt(np.sum(t ** 2))
    if tn == 0 or len(t) > len(x): return 0.0, 0
    num = fftconvolve(x, t[::-1], mode="valid")
    e = np.cumsum(np.concatenate([[0.0], x ** 2])); m = np.cumsum(np.concatenate([[0.0], x]))
    L = len(t); en = e[L:] - e[:-L]; mu = (m[L:] - m[:-L]) / L
    den = np.sqrt(np.maximum(en - L * mu ** 2, 1e-9)) * tn
    r = num / den
    r[den < 1e-3 * tn * np.sqrt(L) * 30] = 0          # ignore digital silence
    i = int(np.argmax(r)); return float(r[i]), i

res = {}
for s in REP["sounds"]:
    t = template(s["sample"], s["pitch"])
    sc, at = ncc(x, t)
    hits = 0
    res[s["name"]] = {"rel_id": s["rel_id"], "score": round(sc, 3), "at_s": round(at / sr, 2), "heard": sc >= a.thr}
heard = sorted(k for k, v in res.items() if v["heard"])
print("heard %d of %d bank sounds (thr %.2f)" % (len(heard), len(res), a.thr))
out = {"capture_s": len(x) / sr, "sounds": res, "heard": heard}
if a.ingame:
    G = json.load(open(a.ingame))
    exp = set()
    for plan, v in G.items():
        for row, m, f, lab in v["expected"]:
            if lab.startswith(("play ", "trans ")): exp.add(lab.split()[1])
    grunts = {"snd_vc_metaknight_atk01", "snd_vc_metaknight_atk02", "snd_vc_metaknight_atk04", "snd_vc_metaknight_atk06"}
    missing = sorted(exp - set(heard)); extra = sorted(set(heard) - exp - grunts)
    out.update({"expected": sorted(exp), "expected_heard": sorted(exp & set(heard)), "expected_missing": missing,
                "heard_not_expected": extra, "grunts_heard": sorted(grunts & set(heard))})
    print("expected %d, heard %d, missing %s" % (len(exp), len(exp & set(heard)), [(m, res[m]["score"]) for m in missing]))
    print("heard but not expected (other than the random grunts): %s" % [(e, res[e]["score"]) for e in extra])
    print("random attack grunts heard: %s" % out["grunts_heard"])
for k in sorted(res, key=lambda k: -res[k]["score"]):
    print("  %-38s %5.3f @%7.2fs %s" % (k, res[k]["score"], res[k]["at_s"], "HEARD" if res[k]["heard"] else ""))
json.dump(out, open(a.out or os.path.join(MK, "sound", "work", "wav_detect.json"), "w"), indent=1)
