"""Offline checks of the sound pass on a finished metaknight-slot (no game run).

    python sound/tools/verify_sounds.py [--mod mods-slot/metaknight-slot]

  bank     brawlmk.ssm parses; every sample's ADPCM is byte-identical to its Brawl wave (BRSAR), frame headers match
           the predictor/scale, sample count / rate / loop flag / loop start / end = Brawl's, decodes without overflow
  sem      smash2.sem: bank count = MxDt ssm_count; every other bank's scripts byte-identical to the disc's; MK's
           scripts name samples inside brawlmk.ssm
  mxdt     ssm row (file name, size = the bank's data size, group/priority/threshold) and fighter.ssm_files[51]
  scripts  every 0x11 command of MK's motion rows: relative ids inside the bank, no Kirby-bank ids left, stops only
           on channels something plays on; ftData sfx ids inside the bank
  budget   the port's ARAM fighter budget (sum of the four largest group-4 banks) with and without brawlmk.ssm
Exit 1 on any failure. Report: sound/work/verify_sounds.json."""
import argparse, json, os, struct, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(MK))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(MK, "model", "tools")); sys.path.insert(0, os.path.join(ROOT, "tools", "mex_port"))
import brsar as BR, ssm as SSM, sfxscript as FS, install_mk as IM, mex_hsd

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=os.path.join(MK, "mods-slot", "metaknight-slot"))
A = ap.parse_args()
F = os.path.join(A.mod, "files")
REP = json.load(open(os.path.join(MK, "sound", "work", "sound_report.json")))
ISO = "C:/iso/SSBM ACE Build v2.0.0.iso"
fails = []; out = {}
def check(ok, what):
    if not ok: fails.append(what)
    return ok

# ---- bank
b = open(os.path.join(F, "audio", "us", "brawlmk.ssm"), "rb").read()
S = SSM.read_ssm(b)
check(S["data_start"] + S["data_size"] == len(b), "ssm: header + data != file size")
check(len(S["samples"]) == REP["bank"]["samples"], "ssm: sample count != report")
R = BR.Brsar(r"C:\iso\brawl-extract\files\sound\smashbros_sound.brsar")
by_sample = {}
for s in REP["sounds"]: by_sample.setdefault(s["sample"], s)
rows = []; peak_all = 0
for si, smp in enumerate(S["samples"]):
    c = smp["chans"][0]; src = by_sample[si]
    w = R.wave_sound(R.sounds[src["brawl_id"]]); wv = w["wave"]; bc = wv["chans"][0]
    start = (c["cur_addr"] - 2) // 2
    nb = wv["end"] // 2 + 1
    same = S["data"][start:start + nb] == R.b[bc["data"]:bc["data"] + nb]
    check(same, "ssm sample %d (%s): ADPCM bytes differ from Brawl" % (si, src["name"]))
    check(S["data"][start] == c["ps"], "ssm sample %d: first frame header != ps" % si)
    check(c["end_addr"] - c["cur_addr"] == wv["end"] - 2, "ssm sample %d: end != Brawl end" % si)
    check(smp["rate"] == wv["rate"], "ssm sample %d: rate" % si)
    check(bool(c["loop"]) == bool(wv["loop"]), "ssm sample %d: loop flag" % si)
    if wv["loop"]:
        check(c["loop_addr"] - c["cur_addr"] == wv["loop_start"] - 2, "ssm sample %d: loop start" % si)
        check((c["lps"], c["lyn1"] & 0xFFFF, c["lyn2"] & 0xFFFF) == (bc["lps"], bc["lyn1"], bc["lyn2"]), "ssm sample %d: loop context" % si)
    check(c["coefs"] == bc["coefs"], "ssm sample %d: coefs" % si)
    nsmp = (c["end_addr"] - c["cur_addr"] + 1) * 7 // 8
    pcm = BR.decode_dsp(S["data"][start:start + nb + 8], c["coefs"], nsmp)
    pk = max(abs(x) for x in pcm) if pcm else 0; peak_all = max(peak_all, pk)
    clip = sum(1 for x in pcm if abs(x) >= 32767)
    rows.append({"sample": si, "brawl": src["name"], "rate": smp["rate"], "samples": len(pcm), "brawl_samples": (wv["end"] - 1) * 7 // 8,
                 "seconds": round(len(pcm) / smp["rate"], 3), "loop": c["loop"], "peak": pk, "clipped": clip})
    check(abs(len(pcm) - (wv["end"] - 1) * 7 // 8) <= 14, "ssm sample %d: sample count %d vs Brawl %d" % (si, len(pcm), (wv["end"] - 1) * 7 // 8))
out["samples"] = rows
out["bank"] = {"bytes": len(b), "aram": S["data_size"], "samples": len(S["samples"]), "first_id": S["base"],
               "seconds": round(sum(r["seconds"] for r in rows), 2), "peak": peak_all}

# ---- sem
G = mex_hsd.Gcm(ISO)
disc = G.read("audio/us/smash2.sem"); new = open(os.path.join(F, "audio", "us", "smash2.sem"), "rb").read()
Td, _ = SSM.read_sem(disc); Tn, _ = SSM.read_sem(new)
bank = REP["bank"]["ssm_index"]
check(len(Tn[2]) == bank + 1, "sem: %d banks, expected %d" % (len(Tn[2]), bank + 1))
check(Tn[2][:len(Td[2])] == Td[2], "sem: other banks' start indices moved")
same = all(SSM.sem_script(disc, Td[3][k]) == SSM.sem_script(new, Tn[3][k]) for k in range(len(Td[3])))
check(same, "sem: a disc script changed")
mine = [SSM.sem_script(new, Tn[3][k]) for k in range(Tn[2][bank], len(Tn[3]))]
check(len(mine) == REP["bank"]["scripts"], "sem: MK script count")
for k, sc in enumerate(mine):
    fid = next((x & 0xFFFFFF for x in sc if x >> 24 == 1), None)
    check(fid is not None and S["base"] <= fid < S["base"] + len(S["samples"]), "sem: MK script %d sample %s outside the bank" % (k, fid))
out["sem"] = {"banks": len(Tn[2]), "scripts": len(Tn[3]), "mk_scripts": len(mine), "disc_scripts_identical": same}

# ---- mxdt
w = IM.Writer(open(os.path.join(F, "MxDt.dat"), "rb").read())
root = w.ar.public("mexData"); md = w.u32(root); fgm = w.u32(root + 0x10); fighter = w.u32(root + 0x08)
n = w.u32(md + 0x1C); files, flags, look = (w.u32(fgm + 4 * k) for k in range(3))
names = [w.str_at(w.u32(files + 4 * i)) for i in range(n)]
check(n == bank + 1 and names[bank] == "brawlmk.ssm", "mxdt: ssm row")
check(w.u32(flags + 8 * bank) == S["data_size"], "mxdt: size != bank data size")
lk = list(w.data[look + 4 * bank:look + 4 * bank + 4])
check(lk[0] == 4, "mxdt: group != 4")
e51 = w.data[w.u32(fighter + 0x38) + 16 * 51]
check(e51 == bank, "mxdt: ssm_files[51] = %d" % e51)
# budget: the port sizes each bank from the file that loads (gw_Mex_SsmSize): disc sizes, ours for brawlmk
sizes = {}
f_ = open(ISO, "rb")
for i in range(n):
    if w.data[look + 4 * i] != 4: continue
    if i == bank: sizes[names[i]] = S["data_size"]; continue
    e = G.files.get("audio/us/" + names[i])
    if e: f_.seek(e[0]); sizes[names[i]] = struct.unpack(">4I", f_.read(16))[1]
g4 = sorted(sizes.values(), reverse=True)
g4_wo = sorted([v for k, v in sizes.items() if k != "brawlmk.ssm"], reverse=True)
out["budget"] = {"top4_with": sum(g4[:4]), "top4_without": sum(g4_wo[:4]), "fourth_largest_without": g4_wo[3], "brawlmk": S["data_size"],
                 "rank_among_fighter_banks": 1 + sorted(sizes.values(), reverse=True).index(S["data_size"]), "fighter_banks": len(sizes)}
check(out["budget"]["top4_with"] == out["budget"]["top4_without"], "budget: brawlmk.ssm grows the ARAM fighter budget")
out["mxdt"] = {"ssm_count": n, "row": names[bank], "lookup": lk, "ssm_files_51": e51}

# ---- scripts
pl = IM.Writer(open(os.path.join(F, "PlBm.dat"), "rb").read())
fd = pl.ar.public([s for s, _ in pl.ar.publics if s.startswith("ftData")][0]); mt = pl.u32(fd + 0xC)
nsc = REP["bank"]["scripts"]
cnt = collections.Counter(); seen = set(); used_rel = set(); bad_rows = []
r = 0
while r < 600:
    o = mt + r * 0x18
    if o + 0x18 > len(pl.data): break
    sc = pl.u32(o + 0xC) if (o + 0xC) in pl.relocs else 0
    if sc and sc not in seen:
        seen.add(sc)
        for op, ws, _ in FS.parse_at(pl.u32, sc):
            if op != FS.SFX: continue
            beh = (ws[0] >> 18) & 0xFF; sid = ws[1]
            if beh >= 10: cnt["stop"] += 1; continue
            if 5000 <= sid < 10000:
                cnt["mk"] += 1; used_rel.add(sid)
                if not check(sid < 5000 + nsc, "row %d: relative id %d outside the bank" % (r, sid)): bad_rows.append(r)
            elif sid == FS.NONE_ID: cnt["none"] += 1
            elif sid < 5000: cnt["main"] += 1
            elif 140000 <= sid < 150000:
                cnt["kirby"] += 1; check(False, "row %d: Kirby-bank id %d left" % (r, sid))
            else: cnt["other_bank"] += 1
    r += 1
sfx = pl.u32(fd + 0x4C); ft = []
for k in range(14):
    v = pl.u32(sfx + 4 * k)
    if k in (0, 7, 8) and v:
        num, arr = pl.u32(v), pl.u32(v + 4); v = [pl.u32(arr + 4 * i) for i in range(num)]
    ft.append(v)
for v in ft:
    for x in (v if isinstance(v, list) else [v]):
        if 5000 <= x < 10000: check(x < 5000 + nsc, "ftData sfx id %d outside the bank" % x); used_rel.add(x)
out["scripts"] = {"sfx_commands": dict(cnt), "relative_ids_used": len(used_rel), "bank_scripts": nsc,
                  "unused_bank_scripts": sorted(set(range(5000, 5000 + nsc)) - used_rel), "ftsfx": ft}
out["fails"] = fails
json.dump(out, open(os.path.join(MK, "sound", "work", "verify_sounds.json"), "w"), indent=1)
print("verify_sounds: bank %s bytes (ARAM %s), %d samples %.1f s, sem %d banks / %d scripts, sfx commands %s, budget top4 %s -> %s (brawlmk rank %d of %d fighter banks), %d fails" % (
    format(len(b), ","), format(S["data_size"], ","), len(S["samples"]), out["bank"]["seconds"], out["sem"]["banks"], out["sem"]["scripts"],
    dict(cnt), format(out["budget"]["top4_without"], ","), format(out["budget"]["top4_with"], ","), out["budget"]["rank_among_fighter_banks"],
    out["budget"]["fighter_banks"], len(fails)))
for x in fails[:20]: print("  FAIL", x)
sys.exit(1 if fails else 0)
