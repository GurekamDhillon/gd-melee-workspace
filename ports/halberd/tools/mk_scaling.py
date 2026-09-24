"""Meta Knight Phase 1: cast-scaled physics attributes (the Brawl Kirby method, tools/scaling.py) and the full
185-attribute map.

    python tools/mk_scaling.py    -> analysis/scaling_mk.json, analysis/attributes_185.json

Scaling = experiment/brawl-kirby/tools/scaling.py applied to Meta Knight instead of Kirby (same Melee cast of 26,
same Brawl cast of 39, same variants and the same recommendation rules). The attribute list (ATTRS) and the Brawl
reader are imported unchanged from that file's source; only the subject fighter differs.
The 185-row map pairs every Brawl common attribute with its Melee ftCo_DatAttrs field through Brawl Kirby's
hand-made pairing table (brawl-kirby/tools/mapping_spec.py ATTRS: the Brawl attribute layout is the same for
every fighter), marking what Phase 1 writes, what is a Brawl-only mechanic, and what is unmapped."""
import sys, os, json, re, struct, statistics
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE)
BKT = os.path.join(os.path.dirname(os.path.dirname(MK)), "experiment", "brawl-kirby", "tools")
ROOT = r"C:/Users/Gurek/Desktop/GD's Melee"
sys.path.insert(0, ROOT + "/tools/mex_port"); sys.path.insert(0, BKT)
import mex_hsd
from mapping_spec import ATTRS as PAIRS

# --- reuse scaling.py's tables and readers without running its Kirby main body: exec only its definitions
src = open(os.path.join(BKT, "scaling.py"), encoding="utf-8").read()
defs = src[:src.index("# ------------------------------------------------ Melee cast")]
defs = defs.replace("HERE = os.path.dirname(os.path.abspath(__file__)); BK = os.path.dirname(HERE)", "")
g = {"__file__": os.path.join(BKT, "scaling.py")}
exec(compile(defs, "scaling.py(defs)", "exec"), g)
ATTRS, MELEE, BRAWL, INT_BRAWL, ISO, BR = g["ATTRS"], g["MELEE"], g["BRAWL"], g["INT_BRAWL"], g["ISO"], g["BR"]
brawl_fn = src[src.index("def brawl_attrs(name):"):src.index("brawl = {n: brawl_attrs(n) for n in BRAWL}")]
exec(compile(brawl_fn, "scaling.py(brawl_attrs)", "exec"), g)
brawl_attrs = g["brawl_attrs"]

SUBJECT = "metaknight"
tsrc = open(ROOT + "/melee/src/melee/ft/types.h", encoding="utf-8").read()
blk = tsrc[tsrc.index("typedef struct ftCo_DatAttrs {"):tsrc.index("} ftCo_DatAttrs;")]
moff = {nm: (int(off, 16), ty) for off, ty, nm in re.findall(r"/\* \+([0-9A-F]{3}) fp\+[0-9A-F]+ \*/ (\w+) (\w+);", blk)}
gcm = mex_hsd.Gcm(ISO)
melee = {}
for c in MELEE:
    ar = mex_hsd.Archive(gcm.read(f"Pl{c}.dat"))
    root = [o for n, o in ar.publics if n.startswith("ftData") and not n.endswith(("Nr", "AJ"))][0]
    ca = ar.u32(root)
    melee[c] = {key: struct.unpack(">i" if moff[mn][1] == "int" else ">f", ar.data[ca+moff[mn][0]:ca+moff[mn][0]+4])[0]
                for key, mn, boff, kind in ATTRS}
brawl = {n: brawl_attrs(n) for n in BRAWL}
B = json.load(open(MK + "/analysis/brawl_metaknight.json"))
bmk = {a["offset"]: a["value"] for a in B["attributes"]}
for key, mn, boff, kind in ATTRS:
    assert abs(bmk[f"0x{boff:03X}"] - brawl[SUBJECT][key]) < 1e-3, key

def stats(v): return {"mean": statistics.mean(v), "median": statistics.median(v), "std": statistics.pstdev(v), "min": min(v), "max": max(v)}
def r(x, n=4): return None if x is None else float(f"{x:.{n}g}")
out = []
for key, mn, boff, kind in ATTRS:
    mv = [melee[c][key] for c in MELEE]; bv = [brawl[n][key] for n in BRAWL]
    ms, bs = stats(mv), stats(bv)
    bkv = brawl[SUBJECT][key]; mkv = melee["Kb"][key]          # host = Melee Kirby
    ratio = ms["mean"] * (bkv / bs["mean"]) if bs["mean"] else None
    z = ms["mean"] + ms["std"] * (bkv - bs["mean"]) / bs["std"] if bs["std"] else None
    ratio_med = ms["median"] * (bkv / bs["median"]) if bs["median"] else None
    clamp = lambda x: None if x is None else min(max(x, ms["min"]), ms["max"])
    # keys kept identical to scaling.json so tuning.py's attribute bases (brawl_kirby -> brawl_raw, ratio, zscore, ...) work
    e = {"key": key, "melee_attr": mn, "melee_offset": f"0x{moff[mn][0]:03X}", "brawl_offset": f"0x{boff:03X}", "kind": kind,
         "brawl_kirby": r(bkv), "brawl_metaknight": r(bkv), "melee_kirby": r(mkv),
         "melee_cast": {k: r(v) for k, v in ms.items()}, "brawl_cast": {k: r(v) for k, v in bs.items()},
         "brawl_rank": sorted(bv, reverse=True).index(bkv) + 1, "brawl_cast_n": len(bv),
         "ratio": r(ratio), "ratio_clamped": r(clamp(ratio)), "ratio_median": r(clamp(ratio_med)), "zscore": r(z), "zscore_clamped": r(clamp(z)),
         "brawl_cv": r(bs["std"] / bs["mean"]) if bs["mean"] else None, "melee_cv": r(ms["std"] / ms["mean"]) if ms["mean"] else None}
    flags = []
    if kind == "phys":
        rec = "ratio"
        if bs["mean"] and ms["mean"] and e["brawl_cv"] and e["melee_cv"] and (e["brawl_cv"] / e["melee_cv"] > 1.6 or e["melee_cv"] / e["brawl_cv"] > 1.6):
            rec = "zscore"; flags.append("cast spread differs a lot between games (CV %.2f Brawl vs %.2f Melee) -> z-score" % (e["brawl_cv"], e["melee_cv"]))
        if key in ("gravity", "terminal_velocity", "fast_fall"): rec = "zscore"; flags.append("Brawl vertical physics is globally floatier; z-score keeps MK's relative place in Melee's fall-speed distribution")
        if bkv == 0 or bs["mean"] == 0: rec = "literal"; flags.append("value 0 (multi-jump uses special attrs) -> keep 0")
        val = {"ratio": e["ratio_clamped"], "zscore": e["zscore_clamped"], "literal": r(bkv)}[rec]
        if rec != "literal" and (val in (r(ms["min"]), r(ms["max"]))): flags.append("clamped to Melee cast bound")
    elif kind == "frames":
        rec = "brawl_literal"; val = int(round(bkv))
        flags.append("timing, not physics scale: Brawl MK's literal frames")
        if key.startswith("landing_lag") and key != "landing_lag_normal":
            flags.append("Melee L-cancel halves this (Melee mechanic kept); Brawl values are uncancelled lag")
    else:
        rec = "literal"; val = int(bkv); flags.append("6 jumps (1 ground + 5 air); Kirby host has the 5-state multi-jump table")
    if kind == "phys" and mkv and val is not None and (val / mkv > 2 or val / mkv < 0.5):
        flags.append("ABSURD? scaled %s is >2x / <0.5x Melee Kirby (%s) (ratio %s, z %s). Brawl 0x078 'Air Stopping Mobility' may not mean Melee's base drift accel -> keep the host's value until a feel test" % (val, r(mkv), e["ratio_clamped"], e["zscore_clamped"]))
        rec = "melee_kirby (fallback)"; val = r(mkv)
    e.update(recommended_variant=rec, recommended_value=val, notes=flags)
    out.append(e)
doc = {"subject": "Brawl Meta Knight -> Melee (host: Kirby)", "method": "tools/scaling.py of the Brawl Kirby port, subject = metaknight: "
       "ratio = melee_mean * brawl_mk / brawl_mean; zscore = melee_mean + melee_std * (brawl_mk - brawl_mean) / brawl_std; both clamped to the Melee cast [min,max]",
       "melee_cast": MELEE, "brawl_cast": BRAWL, "attributes": out, "patch_list": {e["melee_attr"]: e["recommended_value"] for e in out}}
json.dump(doc, open(MK + "/analysis/scaling_mk.json", "w"), indent=1)

# ------------------------------------------------ the 185-row map
pair = {p[0]: p for p in PAIRS}
written = {f"0x{boff:03X}": mn for key, mn, boff, kind in ATTRS}
written["0x0B4"] = "model_scaling"       # build_mk.py writes MK's Brawl Size (MK's own model is in Brawl units)
M = json.load(open(os.path.join(os.path.dirname(os.path.dirname(MK)), "experiment", "brawl-kirby", "analysis", "melee_kirby.json")))
mval = {a["name"]: a["value"] for a in M["common_attributes"]}
rows = []
for a in B["attributes"]:
    p = pair.get(a["offset"])
    mn = p[1] if p else None
    if a["offset"] in written: status = "written (cast-scaled, tuning.json)"
    elif p and p[2].startswith("not_ported"): status = "not ported (Brawl global mechanic)"
    elif p and p[2].startswith("optional"): status = "Brawl-only character ability (Geno v2: glide) / chain flag"
    elif mn and mn.startswith("ftData"): status = "maps outside ftCo_DatAttrs (camera box) - not written"
    elif mn: status = "maps to Melee field, host (Kirby) value kept in Phase 1"
    else: status = "unmapped (no Melee counterpart / unknown Brawl word)"
    rows.append({"index": a["index"], "brawl_offset": a["offset"], "brawl_name": a["name"], "brawl_value": a["value"],
                 "melee_field": mn, "melee_host_value": mval.get(mn) if mn else None, "confidence": p[2] if p else None,
                 "caveat": p[3] if p else None, "status": status})
cnt = {}
for x in rows: cnt[x["status"]] = cnt.get(x["status"], 0) + 1
json.dump({"count": len(rows), "summary": cnt, "rows": rows}, open(MK + "/analysis/attributes_185.json", "w"), indent=1)
for e in out:
    print(f"{e['key']:<20} MK {e['brawl_metaknight']:<8} MeleeKb {e['melee_kirby']:<8} ratio {e['ratio_clamped']} z {e['zscore_clamped']} -> {e['recommended_variant']} {e['recommended_value']}")
print(cnt)
