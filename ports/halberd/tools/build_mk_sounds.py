"""Meta Knight's Brawl sounds on the metaknight-slot: his own sound bank + the script commands that play it.

    python tools/build_mk_sounds.py [--mod mods-slot/metaknight-slot] [--dry]

Run by build_mk_slot.py as its last step (after effects), on the finished mod folder. Owns:
  files/audio/us/brawlmk.ssm   MK's bank: every Brawl wave his scripts / ftData voices use, copied from
                               smashbros_sound.brsar as DSP-ADPCM (no re-encode, no resampling: native rates, loop
                               points and ADPCM loop context kept). Waves shared by several Brawl sounds (the drill's
                               011..018, the tornado's 023..029 are one wave at different pitches) are stored once.
  files/audio/us/smash2.sem    the disc's sound-script file + one bank appended (bank = MxDt's next ssm index): one
                               script per Brawl sound = sample + volume (Brawl's, scaled to Melee's level) + pitch
                               (Brawl's wave-sound pitch, in cents) + priority
  files/MxDt.dat               mexData.ssm grown by one row (brawlmk.ssm: size, group 4 fighter, priorities as the
                               fighter banks, no voice-pitch variants); fighter.ssm_files[MK external] -> it
  files/PlBm.dat               - every motion row whose clip is a Brawl subaction with sound events: its SFX
                                 (0x11) and random-voice (0x12) commands replaced by Brawl's events at Brawl's frames,
                                 ids relative (5000 + index: m-ex's own-bank convention, the port resolves them)
                               - Kirby-bank sounds left in any other row -> "no sound" (Kirby's bank is not loaded)
                               - ftData sfx struct (+0x4C): MK's KO / star KO / teeter / damage-fly voices, random
                                 attack grunts (RandomSmashSFX, Brawl's Low Voice Clip), crowd chant
  geno.json                    the same edits on the v1 overlays of those rows
Brawl -> Melee command mapping (Melee channels: ft_0881.c; 3/4/6 stop on action change, fighter.c):
  Sound Effect / SE2 / Other SE 1+2 / Sounds 05+07 -> behavior 0 (fire and forget); a sound that some row stops
      -> a persistent channel (1, then 5) when stopped from another row, else an action channel (3/4)
  Sound Effect (Transient) -> action channel 3/4; voices (snd_vc_*, transient or not) -> 2 (the voice channel: a new
      voice replaces the last one, as Melee's own voices; not 6, which stops at every action change)
  Stop Sound Effect -> stop that channel (0x11 behavior 10..15); a stop of a sound no MK row plays is dropped
  Low Voice Clip -> RandomSmashSFX; Damage Voice Clip -> damage_l on the voice channel; Ottotto Voice Clip -> dropped
      (Melee's teeter code plays ftData sfx x18 = otto)
Scripts are matched by clip, not by move key, as the effects pass. Report: sound/work/sound_report.json."""
import argparse, json, os, struct, sys, hashlib, math, collections
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE)
SND = os.path.join(MK, "sound"); SNDT = os.path.join(SND, "tools"); SNDW = os.path.join(SND, "work")
ROOT = os.path.dirname(os.path.dirname(MK))
sys.path.insert(0, SNDT); sys.path.insert(0, os.path.join(MK, "model", "tools")); sys.path.insert(0, os.path.join(ROOT, "tools", "mex_port"))
import brsar as BR
import brawl_sfx as BS
import ssm as SSM
import sfxscript as FS
import install_mk as IM
import mex_hsd

BRSAR = r"C:\iso\brawl-extract\files\sound\smashbros_sound.brsar"
ISO = "C:/iso/SSBM ACE Build v2.0.0.iso"
BANK_FILE = "brawlmk.ssm"
MK_INTERNAL, MK_EXTERNAL = 52, 51
REL = 5000                      # m-ex relative id base: 5000 + index in the owner's bank
# loudness: Melee level = Brawl level * K (median loudest-50 ms RMS x volume of Fox/Kirby/Marth/Mario's banks vs MK's
# Brawl sounds, sound/work/calibration in the report); Melee script volume is 0..255, Brawl's 0..127
K = {"se": 1.40, "vc": 0.93}
PRIO = {"se": 0x0E, "vc": 0x11}
AUX = 0x0A                      # reverb send, as every Melee fighter-bank script
BUDGET_RULE = "4th-largest fighter (group 4) bank on the disc: a bank no larger leaves the ARAM budget (lbAudioAx_8002838C) unchanged"

# ftData sfx (+0x4C) fields -> Brawl voice names (snd_vc_metaknight_*). None = Melee's "no sound" (540000).
FTSFX = {
    "smash": ["atk01", "atk02", "atk04", "atk06"],   # RandomSmashSFX pool = Brawl's Low Voice Clip grunts (the four
                                                      # atk voices no script names directly)
    "x4": "miss01",          # blast-zone KO scream
    "x8": None,
    "xC": "hoshikie",        # star / screen KO
    "x10": None,             # ground jump voice: Brawl's JumpF/JumpB scripts play it
    "x14": None,
    "x18": "otto",           # teeter (ftCo_Ottotto)
    "x1C": ["damage_s", "damage_l"],      # damage fly (medium knockback)
    "x20": ["futtobi_l01", "futtobi_l02"],  # damage fly (strong knockback)
    "x24": None,             # tech: Brawl's Passive / PassiveWall / PassiveCeil scripts play ukemi
    "x28": None,             # ledge catch: Brawl's CliffCatch script plays gake
    "x2C": None,             # heavy item lift: Brawl's HeavyGet script plays mochiage
    "x30": "keep",           # grab (main.ssm 81)
    "x34": "ouen",           # crowd chant (snd_vc_ouen_Metaknight)
}
VDMG = "damage_l"

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=os.path.join(MK, "mods-slot", "metaknight-slot"))
ap.add_argument("--dry", action="store_true", help="build and report, write nothing into the mod")
A = ap.parse_args()
FILES = os.path.join(A.mod, "files")
REP = {"bank": {}, "sounds": [], "rows": {}, "overlays": {}, "neutralized": {}, "ftsfx": {}, "notes": [], "dropped_stops": []}


# ------------------------------------------------------------------ 1. rows -> Brawl events
def clip_parts(clip, subs):
    out = []; off = 0
    for n in clip.split("+"):
        out.append((n, off))
        x = subs.get(n); off += int(x["engine"]["brawl.psa"].get("anim_frames") or 0) if x else 0
    return out


def row_table(w):
    fd = w.ar.public([s for s, _ in w.ar.publics if s.startswith("ftData")][0]); mt = w.u32(fd + 0xC)
    MR = json.load(open(os.path.join(MK, "anim", "out", "motion_rows.json")))
    by_off = {(c["offset"], c["size"]): c for c in MR["clips"] + MR["extras"]}
    rows = []; r = 0
    while True:
        o = mt + r * 0x18
        if o + 0x18 > len(w.data) or r > 600: break
        sc = w.u32(o + 0xC) if (o + 0xC) in w.relocs else 0
        c = by_off.get((w.u32(o + 4), w.u32(o + 8)))
        if w.u32(o) == 0 and sc == 0 and c is None and r > 480: break
        rows.append((r, o, sc, c)); r += 1
    return fd, rows


def row_events(clip, frames, subs, scripts, at):
    evs = []; notes = []
    for n, off in clip_parts(clip, subs):
        e, nt = BS.events(n, subs, scripts, at, frames - off)
        evs += [(f + off, k, i, nm) for f, k, i, nm in e if f + off < frames]
        notes += ["%s: %s" % (n, x) for x in nt]
    return evs, notes


# ------------------------------------------------------------------ 2. the bank
def vname(R, i): return R.sounds[i]["name"]


def is_voice(name): return name.startswith("snd_vc_")


def voice_index(R, short):
    n = "snd_vc_metaknight_" + short if short != "ouen" else "snd_vc_ouen_Metaknight"
    return R.sound_by_name(n)["index"]


def build_bank(R, ids, base):
    """ids: ordered Brawl sound indices -> (ssm bytes, sem scripts, per-sound report)."""
    waves = {}; samples = []; scripts = []; rep = []
    for k, i in enumerate(ids):
        s = R.sounds[i]; w = R.wave_sound(s); wv = w["wave"]
        assert wv["format"] == 2 and wv["channels"] == 1, (s["name"], wv["format"], wv["channels"])
        c = wv["chans"][0]
        key = (s["file"], w["note"]["wave"], c["data"])
        if key not in waves:
            nb = wv["end"] // 2 + 1
            adpcm = R.b[c["data"]:c["data"] + nb]
            assert adpcm[0] == c["ps"], (s["name"], "first frame header != predictor/scale")
            adpcm += bytes((-len(adpcm)) % 8)
            waves[key] = len(samples)
            samples.append({"rate": wv["rate"], "loop": wv["loop"], "loop_start_nibble": wv["loop_start"], "end_nibble": wv["end"],
                            "adpcm": adpcm, "coefs": c["coefs"], "gain": c["gain"], "ps": c["ps"], "yn1": c["yn1"], "yn2": c["yn2"],
                            "lps": c["lps"], "lyn1": c["lyn1"], "lyn2": c["lyn2"], "brawl": s["name"]})
        si = waves[key]
        cat = "vc" if is_voice(s["name"]) else "se"
        pitch = w["info"]["pitch"] * w["note"]["pitch"] * 2 ** ((w["note"]["key"] - 60) / 12.0)
        cents = int(round(1200 * math.log2(pitch))) if pitch > 0 else 0
        cents = max(-0x2A30, min(0x960, cents))
        vol = min(255, int(round(s["volume"] / 127.0 * (w["note"]["volume"] / 127.0) * K[cat] * 255)))
        sc = [(0x01 << 24) | (base + si), (0x10 << 24) | AUX]
        if cents: sc.append((0x0C << 24) | (cents & 0xFFFF))
        sc += [(0x04 << 24) | PRIO[cat], (0x06 << 24) | vol, 0x0E000000]
        scripts.append(sc)
        dur = (wv["end"] - 1) * 7 / 8 / wv["rate"] / (pitch if pitch > 0 else 1)
        rep.append({"k": k, "rel_id": REL + k, "brawl_id": i, "name": s["name"], "sample": si, "rate": wv["rate"],
                    "loop": wv["loop"], "loop_start_nibble": wv["loop_start"], "end_nibble": wv["end"],
                    "samples": (wv["end"] - 1) * 7 // 8, "seconds": round(dur, 3), "brawl_volume": s["volume"],
                    "volume": vol, "pitch": round(pitch, 4), "cents": cents, "cat": cat,
                    "attack_decay_sustain_release": [w["note"][x] for x in ("attack", "decay", "sustain", "release")]})
    return SSM.write_ssm(samples, base), scripts, rep, samples


def disc_banks():
    G = mex_hsd.Gcm(ISO); f = open(ISO, "rb"); out = {}
    for n, e in G.files.items():
        if n.startswith("audio/us/") and n.endswith(".ssm"):
            f.seek(e[0]); hs, ds, c, b = struct.unpack(">4I", f.read(16)); out[n[9:]] = (b, c, ds)
    return out, G


# ------------------------------------------------------------------ 3. MxDt
def mxdt(path, n_bytes, write):
    w = IM.Writer(open(path, "rb").read())
    root = w.ar.public("mexData")
    md = w.u32(root); fgm = w.u32(root + 0x10); fighter = w.u32(root + 0x08)
    n = w.u32(md + 0x1C)
    files, flags, look, rt = (w.u32(fgm + 4 * k) for k in range(4))
    names = [w.str_at(w.u32(files + 4 * i)) if w.u32(files + 4 * i) else None for i in range(n)]
    idx = names.index(BANK_FILE) if BANK_FILE in names else None
    if idx is None:
        idx = n
        nf = w.alloc(bytes(4 * (n + 1)), 4)
        for i in range(n):
            if (files + 4 * i) in w.relocs: w.ptr(nf + 4 * i, w.u32(files + 4 * i))
        w.ptr(nf + 4 * n, w.cstr(BANK_FILE))
        nfl = w.alloc(bytes(w.data[flags:flags + 8 * n]) + bytes(8), 4)
        nl = w.alloc(bytes(w.data[look:look + 4 * n]) + bytes(4), 4)
        w.ptr(fgm + 0, nf); w.ptr(fgm + 4, nfl); w.ptr(fgm + 8, nl)
        # m-ex's runtime arrays (ssm_count + 1 words each; the port keeps its own, m-ex's loops run to count + 1)
        for k in range(6):
            a = w.u32(rt + 4 * k)
            if a:
                na = w.alloc(bytes(w.data[a:a + 4 * (n + 1)]) + bytes(4), 4)
                w.ptr(rt + 4 * k, na)
        w.put(md + 0x1C, n + 1)
        flags, look = nfl, nl
    w.put(flags + 8 * idx, n_bytes); w.put(flags + 8 * idx + 4, 0)
    w.data[look + 4 * idx:look + 4 * idx + 4] = bytes([4, 2, 3, 127])   # fighter group, load/unload prio as the
    #                                                                     fighter banks, no tiny/giant voice variants
    tbl = w.u32(fighter + 0x38); e = tbl + 16 * MK_EXTERNAL
    old = (w.data[e], w.u32(e + 8), w.u32(e + 12))
    w.data[e] = idx; w.put(e + 8, 0); w.put(e + 12, 0)
    REP["bank"]["mxdt"] = {"ssm_count_before": n, "bank": idx, "ssm_files_ext51_before": {"ssm_id": old[0], "mask": "0x%08X%08X" % old[1:]},
                           "lookup": [4, 2, 3, 127], "size": n_bytes}
    if write: w.save(path)
    return idx


# ------------------------------------------------------------------ 4. commands
def plan_row(evs, sid_of, chan_of_id, R):
    """Brawl events of one row -> [(counter, words, label)], notes. sid_of: brawl id -> relative id."""
    out = []; notes = []; rr = [3, 4]; nrr = 0; played = {}; last = {}
    for f, k, i, nm in sorted(evs, key=lambda t: t[0]):
        if k == "vlow":
            out.append((f, FS.smash_word(), "Low Voice Clip -> RandomSmashSFX")); continue
        if k == "votto":
            notes.append("f%d Ottotto Voice Clip dropped: Melee's teeter code plays ftData sfx x18 (otto)" % f); continue
        if k == "vdmg":
            i = voice_index(R, VDMG); k = "play"
        if i is None: continue
        name = vname(R, i); voice = is_voice(name)
        if k == "stop":
            ch = chan_of_id.get(i) or played.get(i)
            if ch is None:
                REP["dropped_stops"].append(name); notes.append("f%d stop %s dropped (no MK row plays it)" % (f, name)); continue
            out.append((f, FS.stop_words(ch), "stop %s (channel %d)" % (name, ch))); continue
        if voice and i in last and f - last[i] < DUR_FRAMES.get(i, 0):
            notes.append("f%d %s re-trigger while playing skipped" % (f, name)); continue
        if voice:
            b = 2         # the voice channel, also for Brawl's transient voices: channel 6 stops at every Melee action
            #               change, and Melee splits Brawl subactions into several actions (Attack100Start ->
            #               Attack100Loop, SpecialHi -> UpBLoop): the rapid-jab / up-B voices were cut after a few frames
        elif i in chan_of_id:
            b = chan_of_id[i]
        elif k == "trans" or i in STOPPED_IN_ROW:
            b = rr[nrr % 2]; nrr += 1
        else:
            b = 0
        played[i] = b; last[i] = f
        out.append((f, FS.sfx_words(sid_of[i], b), "%s %s (behavior %d)" % (k, name, b)))
    return out, notes


def rewrite(w, rows, geno_path, subs, scripts, at, sid_of, chan_of_id, R, write):
    G = json.load(open(geno_path)) if os.path.exists(geno_path) else None
    ovl = {s["index"]: s for s in (G["fighters"][0].get("subactions", []) if G else [])}
    done = {}
    global STOPPED_IN_ROW
    kirby_lo, kirby_hi = 140000, 149999

    def is_sound(c): return c[0] == FS.SMASH or (c[0] == FS.SFX)

    for r, o, sc, c in rows:
        if not sc or c is None: continue
        clip = c["brawl_clip"]; frames = int(c["frames"])
        evs, notes = row_events(clip, frames, subs, scripts, at)
        if not evs: continue
        STOPPED_IN_ROW = {i for f, k, i, nm in evs if k == "stop"}
        enc, n2 = plan_row(evs, sid_of, chan_of_id, R)
        notes += n2
        key = (sc, clip)
        cmds = FS.parse_at(w.u32, sc)
        if key not in done:
            new, rep = FS.insert(cmds, enc, strip=is_sound, clip=frames, u32=w.u32)
            pos = []; p = 0
            for cc in new: pos.append(p); p += 4 * len(cc[1])
            at_ = w.alloc(bytes(p), 4)
            old_off = {i: cmds[i][2] for i in range(len(cmds))}
            new_of_old = {cc[2]: at_ + pos[j] for j, cc in enumerate(new) if cc[2] is not None}
            first_orig = next((at_ + pos[j] for j, cc in enumerate(new) if cc[2] == 0), at_)
            for j, cc in enumerate(new):
                for k2, word in enumerate(cc[1]): w.put(at_ + pos[j] + 4 * k2, word)
                if cc[0] in (FS.GOTO, FS.SUB) and cc[2] is not None:
                    t = w.u32(old_off[cc[2]] + 4)
                    oi = next((i for i in old_off if old_off[i] == t), None)
                    if cc[0] == FS.GOTO and t == sc: nt = first_orig
                    elif oi is not None:
                        nt = new_of_old.get(oi)
                        while nt is None and oi is not None and oi + 1 < len(cmds):      # target was a stripped sound
                            oi += 1; nt = new_of_old.get(oi)
                        nt = nt or t
                    else: nt = t
                    w.ptr(at_ + pos[j] + 4, nt)
            done[key] = (at_, rep)
        at_, rep = done[key]
        w.ptr(o + 0xC, at_)
        REP["rows"][r] = {"clip": clip, "frames": frames, "script": [hex(sc), hex(at_)], "stripped": rep["stripped"],
                          "placed": rep["placed"], "dropped": rep["dropped"], "notes": notes}
        if r in ovl and "words" in ovl[r]:
            old = [int(x, 16) if isinstance(x, str) else int(x) for x in ovl[r]["words"]]
            oc = FS.parse_words(old)
            if any(c2[0] == FS.GENO and ((c2[1][0] >> 20) & 0x3F) == 0x13 for c2 in oc):
                REP["overlays"][r] = "ORIG overlay (runs the Pl script after its escapes): left alone"
            elif any(c2[0] == FS.GOTO for c2 in oc): REP["notes"].append("overlay row %d has a Goto: left alone" % r)
            else:
                nw, rp = FS.insert(oc, enc, strip=is_sound, clip=frames, u32=w.u32)
                nw, fixed = FS.fix_overlay_skips(oc, nw)
                ovl[r]["words"] = ["0x%08X" % x for x in FS.to_words(nw)]
                REP["overlays"][r] = {"placed": rp["placed"], "dropped": rp["dropped"], "stripped": rp["stripped"], "skips_fixed": fixed}

    # Kirby's bank is not loaded for MK any more: any Kirby-bank sound left (rows with no Brawl sound events) -> none
    seen = set()
    for r, o, sc0, c in rows:
        sc = w.u32(o + 0xC) if (o + 0xC) in w.relocs else 0          # (the row may have been rewritten above)
        if not sc or sc in seen: continue
        seen.add(sc)
        for op, words, off in FS.parse_at(w.u32, sc):
            if op == FS.SFX and kirby_lo <= words[1] <= kirby_hi and ((words[0] >> 18) & 0xFF) <= 6:
                w.put(off, (FS.SFX << 26) | (2 << 18)); w.put(off + 4, FS.NONE_ID)
                REP["neutralized"].setdefault(r, []).append(words[1])
    for r, s in ovl.items():
        if "words" not in s: continue
        ws = [int(x, 16) if isinstance(x, str) else int(x) for x in s["words"]]
        i = 0; ch = False
        while i < len(ws):
            L = FS.cmd_len(ws[i])
            if ws[i] >> 26 == FS.SFX and i + 1 < len(ws) and kirby_lo <= ws[i + 1] <= kirby_hi and ((ws[i] >> 18) & 0xFF) <= 6:
                ws[i] = (FS.SFX << 26) | (2 << 18); ws[i + 1] = FS.NONE_ID; ch = True
            i += L
        if ch:
            s["words"] = ["0x%08X" % x for x in ws]; REP["neutralized"].setdefault("overlay %d" % r, []).append("kirby")

    # overlay == Pl script minus Geno escapes (the check the effects pass runs)
    bad = []
    fd = w.ar.public([s for s, _ in w.ar.publics if s.startswith("ftData")][0]); mt = w.u32(fd + 0xC)
    for r2, o2 in ovl.items():
        if "words" not in o2: continue
        ws = [int(x, 16) if isinstance(x, str) else int(x) for x in o2["words"]]
        if any(((x >> 26) == FS.GENO and ((x >> 20) & 0x3F) == 0x13) for x in ws): continue
        plain = [c for c in FS.parse_words(ws) if c[0] != FS.GENO]
        pl = [(c[0], c[1]) for c in FS.parse_at(w.u32, w.u32(mt + r2 * 0x18 + 0xC))]

        def timed(cs):
            tl, _ = FS.timeline(cs)
            return [(f, c[1]) for f, c in zip(tl, cs) if c[0] not in (FS.SYNC, FS.ASYNC)]
        if timed(plain) != timed(pl): bad.append(r2)
    REP["overlay_check"] = {"overlays_equal_to_pl_minus_escapes": len([k for k in ovl if "words" in ovl[k]]) - len(bad), "mismatch": bad}
    if bad: REP["notes"].append("overlay != Pl script (minus escapes) for rows %s" % bad)
    if write and G is not None: json.dump(G, open(geno_path, "w"), indent=1)
    return bad


def write_ftsfx(w, fd, rel_of_voice):
    old = w.u32(fd + 0x4C)
    fields = ["smash", "x4", "x8", "xC", "x10", "x14", "x18", "x1C", "x20", "x24", "x28", "x2C", "x30", "x34"]
    st = w.alloc(bytes(0x38), 4)
    for k, f in enumerate(fields):
        v = FTSFX[f]; o = st + 4 * k
        if isinstance(v, list):
            ids = [rel_of_voice[x] for x in v]
            arr = w.alloc(b"".join(struct.pack(">I", x) for x in ids), 4)
            hdr = w.alloc(struct.pack(">2I", len(ids), 0), 4); w.ptr(hdr + 4, arr); w.ptr(o, hdr)
            REP["ftsfx"][f] = ids
        elif v == "keep":
            w.put(o, w.u32(old + 4 * k)); REP["ftsfx"][f] = w.u32(old + 4 * k)
        elif v is None:
            w.put(o, FS.NONE_ID); REP["ftsfx"][f] = FS.NONE_ID
        else:
            w.put(o, rel_of_voice[v]); REP["ftsfx"][f] = rel_of_voice[v]
    w.ptr(fd + 0x4C, st)


# ------------------------------------------------------------------ main
DUR_FRAMES = {}
STOPPED_IN_ROW = set()


def main():
    write = not A.dry
    os.makedirs(SNDW, exist_ok=True)
    R = BR.Brsar(BRSAR)
    subs, scripts, at = BS.load_ir()
    pl_path = os.path.join(FILES, "PlBm.dat")
    w = IM.Writer(open(pl_path, "rb").read())
    fd, rows = row_table(w)

    # which Brawl sounds the rows play, which get stopped, from where
    used = []; plays_by_row = {}; stops_by_row = {}
    for r, o, sc, c in rows:
        if not sc or c is None: continue
        evs, _ = row_events(c["brawl_clip"], int(c["frames"]), subs, scripts, at)
        plays_by_row[r] = {i for f, k, i, nm in evs if k in ("play", "trans") and i is not None}
        stops_by_row[r] = {i for f, k, i, nm in evs if k == "stop" and i is not None}
        for f, k, i, nm in evs:
            if k in ("play", "trans") and i is not None and i not in used: used.append(i)
            if k == "vdmg":
                v = voice_index(R, VDMG)
                if v not in used: used.append(v)
    played_any = set().union(*plays_by_row.values())
    cross = sorted({i for r in stops_by_row for i in stops_by_row[r] if i in played_any and i not in plays_by_row[r]})
    persistent = [1, 5]
    if len(cross) > len(persistent): raise SystemExit("more cross-row stopped sounds (%s) than persistent channels" % cross)
    chan_of_id = {i: persistent[k] for k, i in enumerate(cross)}
    REP["channels"] = {vname(R, i): ch for i, ch in chan_of_id.items()}
    for f in FTSFX.values():
        for v in (f if isinstance(f, list) else [f]):
            if v and v != "keep":
                i = voice_index(R, v)
                if i not in used: used.append(i)
    used.sort(key=lambda i: (is_voice(vname(R, i)), i))        # SE first, then voices

    banks, G = disc_banks()
    base = int(math.ceil(max(b + c for b, c, _ in banks.values()) / 100.0) * 100)
    ssm_bytes, sem_scripts, srep, samples = build_bank(R, used, base)
    REP["sounds"] = srep
    for s in srep: DUR_FRAMES[s["brawl_id"]] = int(math.ceil(s["seconds"] * 60))
    sid_of = {s["brawl_id"]: s["rel_id"] for s in srep}
    rel_of_voice = {}
    for f in FTSFX.values():
        for v in (f if isinstance(f, list) else [f]):
            if v and v != "keep": rel_of_voice[v] = sid_of[voice_index(R, v)]
    rel_of_voice[VDMG] = sid_of[voice_index(R, VDMG)]

    REP["bank"].update({"file": BANK_FILE, "bytes": len(ssm_bytes), "aram_bytes": struct.unpack_from(">I", ssm_bytes, 4)[0],
                        "samples": len(samples), "scripts": len(sem_scripts), "first_sample_id": base,
                        "sha1": hashlib.sha1(ssm_bytes).hexdigest()[:12]})

    # MxDt row, sem bank
    idx = mxdt(os.path.join(FILES, "MxDt.dat"), REP["bank"]["aram_bytes"], write)
    sem_old = G.read("audio/us/smash2.sem")
    T, _ = SSM.read_sem(sem_old)
    if len(T[2]) > idx: raise SystemExit("disc smash2.sem has %d banks, MxDt's next is %d" % (len(T[2]), idx))
    while len(T[2]) < idx:                    # (never on ACE: 103 = 103) pad missing banks with empty ones
        raise SystemExit("disc smash2.sem has %d banks < MxDt ssm_count %d" % (len(T[2]), idx))
    sem_new = SSM.write_sem(sem_old, sem_scripts, idx)
    REP["bank"].update({"ssm_index": idx, "sfx_ids": [idx * 10000, idx * 10000 + len(sem_scripts) - 1],
                        "sem": {"disc_bytes": len(sem_old), "bytes": len(sem_new), "banks": len(T[2]) + 1,
                                "scripts": len(T[3]) + len(sem_scripts)}})

    # scripts
    bad = rewrite(w, rows, os.path.join(A.mod, "geno.json"), subs, scripts, at, sid_of, chan_of_id, R, write)
    write_ftsfx(w, fd, rel_of_voice)
    if write:
        w.save(pl_path)
        au = os.path.join(FILES, "audio", "us"); os.makedirs(au, exist_ok=True)
        open(os.path.join(au, BANK_FILE), "wb").write(ssm_bytes)
        open(os.path.join(au, "smash2.sem"), "wb").write(sem_new)
    else:
        open(os.path.join(SNDW, BANK_FILE), "wb").write(ssm_bytes); open(os.path.join(SNDW, "smash2.sem"), "wb").write(sem_new)
    REP["summary"] = {"sounds": len(srep), "samples": len(samples), "rows_rewritten": len(REP["rows"]),
                      "overlays_rewritten": len(REP["overlays"]),
                      "events_placed": sum(len(v["placed"]) for v in REP["rows"].values()),
                      "events_dropped": sum(len(v["dropped"]) for v in REP["rows"].values()),
                      "rows_neutralized": len(REP["neutralized"]), "overlay_mismatch": bad}
    json.dump(REP, open(os.path.join(SNDW, "sound_report.json"), "w"), indent=1, default=str)
    print("   sounds: bank %d (%s, %s bytes, %d samples, %d sounds, ids %d..%d), %d rows rewritten, %d overlays, %d events placed, %d dropped%s" % (
        idx, BANK_FILE, format(len(ssm_bytes), ","), len(samples), len(sem_scripts), REP["bank"]["sfx_ids"][0], REP["bank"]["sfx_ids"][1],
        len(REP["rows"]), len(REP["overlays"]), REP["summary"]["events_placed"], REP["summary"]["events_dropped"], "" if write else " (dry run)"))
    if bad: raise SystemExit("overlay check failed for rows %s" % bad)


if __name__ == "__main__":
    main()
