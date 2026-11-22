#!/usr/bin/env python3
"""autogroups: derive the object-slot config (groups.json) for skin.py from data instead of by hand.

Target side (structure only, any of the 26 fighters):
  - ftData<Name>.x8 parts visibility (decomp ft/ftparts.c ftParts_8007487C / 80074B6C, types.h FtPartsDesc):
    model_num models; per costume 4 lookup tables; per model a list of groups of DObj indices, ONE group shown at a
    time (swaps). Table 0 = high-detail set, table 1 = low-detail set (both index the costume's DObj list), table 2
    indexes the separate x203C list. A DObj listed in no table is always visible.
  - ftData.x8.x8: the DObjs that carry the eye texture animation (count, u16 indices per costume).
  - per DObj (costumebuild inspect): dominant joint by skin weight, triangle count; TObj count (skin.target).
  -> role per slot: hi:<region> / low:<region> / swap:<model>.<group>:<region> / eye / always:<region>, + confidence.
Source side: each object's dominant bone (mapped to a target joint -> region), its material/texture names (eye*),
size. Assignment:
  - eye-named source objects -> the eye texanim slots (left/right by x position); TObj 0 replaced, the rest kept
    (retail's blink frames keep animating the remaining layers) - fallback: fixed source eye, reported.
  - every other source object -> the biggest high-detail slot of its region (body if the region has none)
  - swap groups (hand variants etc.): when the source has an object of that region, the first slot of every
    variant gets a copy (a fixed shape for all variants: "fixed hand"); otherwise the variants are blanked and the
    region stays in the body mesh ("hands in body"). The decision is reported per fighter.
  - low-detail slots: the biggest one gets every non-eye source object with "reduce" (skin.py reduces it to the
    retail low-detail triangle count); the other low-detail slots are blanked.
  - other high-detail slots blanked; slots of unknown role kept (retail mesh) and flagged.

    autogroups.py roles  <PlXxNr.dat> <PlXx.dat> --fighter NAME [--plco PlCo.dat] [-o roles.json]
    autogroups.py groups <source.json> <PlXxNr.dat> <PlXx.dat> --fighter NAME [--plco] [--map m.json] -o groups.json
    autogroups.py tables                 (all 26 fighters from GW_ISO_VANILLA -> maps/<fighter>.roles.json)
"""
import argparse, json, os, re, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import skin
sys.path.insert(0, os.path.join(skin.ROOT, "tools", "mex_port"))
import mex_hsd


def _ptr(ar, off):
    return ar.u32(off) if off in ar.reloc_set else None


def read_vis(fighter_dat):
    """Parts visibility of costume 0 (the row the game falls back to) + eye texanim DObjs; indices only."""
    ar = mex_hsd.Archive(open(fighter_dat, "rb").read())
    ft = ar.public([s for s, _ in ar.publics if s.startswith("ftData")][0])
    x8 = _ptr(ar, ft + 8)
    out = {"models": 0, "tables": {}, "eye_dobjs": []}
    if x8 is None: return out
    mn = ar.u32(x8); vt = _ptr(ar, x8 + 4); out["models"] = mn
    if vt is not None:
        for k in range(4):
            p = _ptr(ar, vt + k * 4)
            if p is None: continue
            models = []
            for m in range(mn):
                cnt, ts = ar.u32(p + m * 8), _ptr(ar, p + m * 8 + 4)
                groups = []
                for j in range(cnt if ts is not None else 0):
                    n, lst = ar.u32(ts + j * 8), _ptr(ar, ts + j * 8 + 4)
                    groups.append(list(ar.data[lst:lst + n]) if lst is not None else [])
                models.append(groups)
            out["tables"][k] = models
    ne, xc = ar.u32(x8 + 8), _ptr(ar, x8 + 12)
    if xc is not None and ne:
        row = _ptr(ar, xc)
        if row is not None: out["eye_dobjs"] = [ar.u16(row + 2 * i) for i in range(ne)]
    return out


REGIONS = [("hand_l", r"^L(Hand|1st|2nd|3rd|4th|Thumb|Have)"), ("hand_r", r"^R(Hand|1st|2nd|3rd|4th|Thumb|Have)"),
           ("head", r"^(Head|Neck)"), ("foot_l", r"^L(Foot|Toe)"), ("foot_r", r"^R(Foot|Toe)")]


def region_of(joint_index, joints):
    """Region of a joint: the first named ancestor-or-self that matches a region; ExtraN under HeadN -> head."""
    j = joint_index
    while j is not None:
        n = joints[j]["name"]
        for r, pat in REGIONS:
            if re.match(pat, n): return r
        j = joints[j]["parent"]
    return "body"


def target_roles(costume, fighter_dat, fighter=None, plco=None, work=None):
    tgt = skin.read_target(costume, fighter, plco)
    work = work or os.path.join(skin.ROOT, "_build", "tmp", "autogroups"); os.makedirs(work, exist_ok=True)
    ij = os.path.join(work, os.path.basename(costume) + ".inspect.json")
    subprocess.run([skin.CB, "inspect", costume, ij], check=True, capture_output=True)
    ins = json.load(open(ij)); vis = read_vis(fighter_dat)
    J = tgt["joints"]; slots = []
    member = {}
    for k, models in vis["tables"].items():
        for m, groups in enumerate(models):
            for g, lst in enumerate(groups):
                for d in lst: member.setdefault(d, []).append((k, m, g, len(groups)))
    for i, (d, di) in enumerate(zip(tgt["dobjs"], ins["dobjs"])):
        acc = {}
        for v in di["verts"]:
            for j, w in v["w"]: acc[j] = acc.get(j, 0) + w
        dom = max(acc, key=acc.get) if acc else d["joint"]
        reg = region_of(dom, J)
        mem = [x for x in member.get(i, []) if x[0] in (0, 1)]
        if i in vis["eye_dobjs"]:
            role, conf, why = "eye", 0.9, "listed in ftData x8.x8 (eye texture animation)"
        elif any(x[3] > 1 and x[2] > 0 for x in mem):
            k, m, g, n = [x for x in mem if x[3] > 1 and x[2] > 0][0]
            role, conf, why = "swap:%d.%d:%s" % (m, g, reg), 0.75, "model %d alternate group %d of %d in table %d (shown instead of group 0)" % (m, g, n, k)
        elif any(x[0] == 1 for x in mem):
            role, conf, why = "low:" + reg, 0.85, "in the low-detail table"
        elif any(x[0] == 0 for x in mem):
            role, conf, why = "hi:" + reg, 0.85, "in the high-detail table"
        elif not vis["tables"]:
            role, conf, why = "always:" + reg, 0.6, "fighter has no parts-visibility table"
        else:
            role, conf, why = "always:" + reg, 0.7, "in no visibility table: always drawn"
        if di["tris"] == 0 and role != "eye": role, conf, why = "empty", 0.9, "no geometry in retail"
        slots.append({"dobj": i, "joint": J[dom]["name"], "joint_index": dom, "region": reg, "tris": di["tris"],
                      "tobjs": d["tobjs"], "role": role, "confidence": conf, "why": why})
    roles = {"fighter": fighter, "costume": os.path.basename(costume), "models": vis["models"],
             "tables": {str(k): [[len(g) for g in m] for m in v] for k, v in vis["tables"].items()},
             "eye_dobjs": vis["eye_dobjs"], "slots": slots}
    roles["confidence"] = round(float(np.mean([s["confidence"] for s in slots])) if slots else 0, 2)
    has_hi = any(s["role"].startswith("hi:") for s in slots)
    roles["needs_review"] = (not has_hi and not any(s["role"].startswith("always:") for s in slots)) or roles["confidence"] < 0.7
    return roles, tgt


# ---------------------------------------------------------------- source classification & assignment --------------------
def classify_source(src, tgt, mp):
    T = {j["name"]: j["index"] for j in tgt["joints"]}; mats = {m["name"]: m for m in src.get("materials", [])}
    out = []
    for o in src["objects"]:
        acc = {}
        for fp in o["tris"]:
            for bn, w in fp[14]: acc[bn] = acc.get(bn, 0) + w
        dom = max(acc, key=acc.get) if acc else None
        tj = T.get(mp["source_to_target"][dom]["target"]) if dom else 0
        texs = [r["texture"] for r in mats.get(o["material"], {}).get("refs", []) if r.get("map", "TexCoord") == "TexCoord"]
        names = " ".join([o["name"], o.get("material") or ""] + texs).lower()
        xs = [fp[0] for fp in o["tris"]] or [0]
        out.append({"object": o["name"], "tris": len(o["tris"]) // 3, "dominant_bone": dom, "region": region_of(tj, tgt["joints"]),
                    "eye": bool(re.search(r"eye|medama|hitomi", names)) and not re.search(r"brow|dmg|lash", names),
                    "x": float(np.mean(xs)), "texture": texs[0] if texs else None,
                    "alpha": bool(mats.get(o["material"], {}).get("alpha_test"))})
    return out


def assign(roles, srcobjs):
    S = roles["slots"]; groups = {}; why = {}; notes = []
    def put(i, g, w): groups[str(i)] = g; why[str(i)] = w
    eyes = [o for o in srcobjs if o["eye"]]; rest = [o for o in srcobjs if not o["eye"]]
    eye_slots = [s for s in S if s["role"] == "eye"]
    hi = [s for s in S if s["role"].startswith(("hi:", "always:"))]
    low = [s for s in S if s["role"].startswith("low:")]
    swaps = [s for s in S if s["role"].startswith("swap:")]
    # swaps: per region, does the source have its own object there?
    sw_regions = sorted({s["region"] for s in swaps})
    moved = set()
    for reg in sw_regions:
        own = [o for o in rest if o["region"] == reg]
        vs = [s for s in swaps if s["region"] == reg]
        if own:
            firsts = {}
            for s in vs: firsts.setdefault(s["role"].split(":")[1], s)
            for s in vs:
                if s is firsts[s["role"].split(":")[1]]:
                    put(s["dobj"], {"objects": [o["object"] for o in own], "textures": [own[0]["texture"]]}, "fixed %s shape: source objects %s in every variant" % (reg, [o["object"] for o in own]))
                else: put(s["dobj"], "blank", "extra piece of a %s variant: covered by the fixed shape" % reg)
            moved |= {o["object"] for o in own}; notes.append("%s: fixed shape from the source in all %d variants" % (reg, len(firsts)))
        else:
            for s in vs: put(s["dobj"], "blank", "%s variants blanked: the source keeps that region in its body mesh" % reg)
            notes.append("%s: in the body mesh; the retail swap variants are blanked (no open/closed change)" % reg)
    # high-detail: per region the biggest slot gets that region's objects; body takes the unplaced rest
    body = [o for o in rest if o["object"] not in moved]
    regs = {}
    for s in hi: regs.setdefault(s["region"], []).append(s)
    placed = set()
    for reg, ss in sorted(regs.items(), key=lambda x: x[0] == "body"):
        if reg.startswith("hand"):
            # hand shapes are switched by ANIMATION (the shape's joints are scaled to zero), not by visibility: the
            # fist slot is weighted to a non-finger joint (ExtraN under the hand), the open hand to the fingers.
            fists = [s for s in ss if s["joint"].startswith("ExtraN")]; opens = [s for s in ss if s not in fists]
            own = [o for o in body if o["region"] == reg and o["object"] not in placed]
            if own:
                for s in opens: put(s["dobj"], {"objects": [o["object"] for o in own], "textures": [own[0]["texture"]]}, "open hand on the finger joints: source %s" % [o["object"] for o in own])
                placed |= {o["object"] for o in own}
            else:
                for s in opens: put(s["dobj"], "blank", "open hand: the source hand stays in the body mesh and rides the finger joints")
            for s in fists:
                put(s["dobj"], {"cut_region": reg, "rebind_joint": s["joint_index"], "objects": [], "textures": [None]},
                    "fist (scale-switched joint %s, inferred from weights): a copy of the source %s geometry bound rigidly to it" % (s["joint"], reg))
            notes.append("%s: open hand rides the fingers; %d fist slot(s) get a rigid copy on the fist joint (animation scan not done: inferred from skin weights)" % (reg, len(fists)))
            continue
        big = max(ss, key=lambda s: s["tris"])
        objs = [o for o in body if (o["region"] == reg or reg == "body") and o["object"] not in placed]
        if objs:
            put(big["dobj"], {"objects": [o["object"] for o in objs], "textures": [objs[0]["texture"]], "alpha_test": any(o["alpha"] for o in objs)},
                "biggest high-detail %s slot: %s" % (reg, [o["object"] for o in objs])); placed |= {o["object"] for o in objs}
            for s in ss:
                if s is not big: put(s["dobj"], "blank", "other high-detail %s slot: geometry is in DObj %d" % (reg, big["dobj"]))
        else:
            for s in ss: put(s["dobj"], "blank", "no source geometry in region %s (it is drawn by the body slot)" % reg)
    unplaced = [o["object"] for o in body if o["object"] not in placed]
    if unplaced:
        bigb = max(hi, key=lambda s: s["tris"]) if hi else None
        if bigb:
            g = groups[str(bigb["dobj"])]
            if isinstance(g, dict): g["objects"] += unplaced
            else: put(bigb["dobj"], {"objects": unplaced, "textures": [body[0]["texture"]]}, "")
            why[str(bigb["dobj"])] += "; plus %s (no slot of their region)" % unplaced
    # eyes. Policy "static": the animated eye slots (ftData x8.x8) swap RETAIL images during blinks, which would land
    # on the source's eye UVs, so they are blanked and the source eyes go into the biggest non-animated head slot.
    # (Re-mapping blink frames from the source's lid textures is not implemented; reported.)
    if eyes:
        heads = [s for s in hi if s["region"] == "head" and str(s["dobj"]) in groups and isinstance(groups[str(s["dobj"])], dict)] or                 [s for s in hi if str(s["dobj"]) in groups and isinstance(groups[str(s["dobj"])], dict)]
        if heads:
            h = max(heads, key=lambda s: s["tris"]); groups[str(h["dobj"])]["objects"] += [o["object"] for o in eyes]
            why[str(h["dobj"])] += "; plus the source eyes %s as static meshes" % [o["object"] for o in eyes]
        for s in eye_slots: put(s["dobj"], "blank", "animated eye slot blanked: its blink frames are retail images (static source eyes instead)")
        notes.append("eyes: static source eyes (%d objects); %d animated eye slots blanked, no blinking" % (len(eyes), len(eye_slots)))
    elif eye_slots:
        for s in eye_slots: put(s["dobj"], "keep", "eye slot kept as retail: the source has no separate eye object")
        notes.append("eyes: kept retail (no source eye objects found) - review")
    # low-detail
    if low:
        big = max(low, key=lambda s: s["tris"])
        put(big["dobj"], {"objects": [o["object"] for o in srcobjs], "textures": [rest[0]["texture"] if rest else None], "reduce_to": sum(s["tris"] for s in low)},
            "low-detail copy, reduced to the retail low-detail triangle count %d" % sum(s["tris"] for s in low))
        for s in low:
            if s is not big: put(s["dobj"], "blank", "other low-detail slot: covered by DObj %d" % big["dobj"])
    for s in S:
        if str(s["dobj"]) not in groups:
            put(s["dobj"], "keep" if s["role"] != "empty" else "blank", "role %s: retail mesh kept" % s["role"] if s["role"] != "empty" else "empty in retail")
    conf = roles["confidence"] * (0.6 if (eye_slots and not eyes) else 1.0) * (0.85 if any("blanked" in n for n in notes) else 1.0)
    return {"max_texture": 256, "dobjs": groups, "_auto": {"why": why, "notes": notes, "confidence": round(conf, 2),
            "needs_review": roles["needs_review"] or conf < 0.6}}


def post_reduce(sk, groups, tgt, log):
    """Reduce 'reduce_to' slots (the low-detail copy) and build the fist copies ('cut_region' + 'rebind_joint').
    Called by skin.build when the groups came from autogroups."""
    J = tgt["joints"]; W = [np.array(j["world"]) for j in J]
    def world(v):
        if len(v["w"]) == 1 and J[v["w"][0][0]]["ibm"]: return (W[v["w"][0][0]] @ np.array(list(v["p"]) + [1.0]))[:3]
        return np.array(v["p"])
    byd = {d["dobj"]: d for d in sk["dobjs"]}
    for k, g in groups["dobjs"].items():
        if not (isinstance(g, dict) and g.get("cut_region")): continue
        reg, fj = g["cut_region"], g["rebind_joint"]; I = np.linalg.inv(W[fj]); cut = []
        for d in sk["dobjs"]:
            if str(d["dobj"]) == k or not d.get("tris") or isinstance(groups["dobjs"].get(str(d["dobj"])), dict) and groups["dobjs"][str(d["dobj"])].get("reduce_to"): continue
            for t in d["tris"]:
                if all(region_of(max(v["w"], key=lambda x: x[1])[0], J) == reg for v in t):
                    cut.append([{"p": (I @ np.append(world(v), 1.0))[:3].tolist(), "n": v["n"], "uvs": v["uvs"], "w": [[fj, 1.0]]} for v in t])
        tgt_d = byd.get(int(k))
        if tgt_d is not None:
            tgt_d["tris"] = cut; tgt_d["mode"] = "replace" if cut else "blank"
            if not tgt_d.get("textures") or tgt_d["textures"] == [None]:
                src_tex = next((d["textures"] for d in sk["dobjs"] if d.get("tris") and d is not tgt_d and d.get("textures")), [None]); tgt_d["textures"] = src_tex[:1]
        log.append("DObj %s: fist copy, %d triangles of %s bound to joint %d" % (k, len(cut), reg, fj))
    for d in sk["dobjs"]:
        g = groups["dobjs"].get(str(d["dobj"]))
        if isinstance(g, dict) and g.get("reduce_to") and d.get("tris"):
            tmp = {"dobjs": [d]}; skin.fit_budget(tmp, tgt, max(4, g["reduce_to"]), log)


def make_groups(source, costume, fighter_dat, fighter, plco=None, mapfile=None):
    src = skin.load_source(source) if isinstance(source, str) else source
    roles, tgt = target_roles(costume, fighter_dat, fighter, plco)
    start = None
    if mapfile:
        start = json.load(open(mapfile))["source_to_target"]
        start = {k: (v["target"] if isinstance(v, dict) else v) for k, v in start.items()}
        tn = {j["name"] for j in tgt["joints"]}; start = {k: v for k, v in start.items() if v in tn and k in {b["name"] for b in src["bones"]}}
    mp = skin.automap(src, tgt, start)
    g = assign(roles, classify_source(src, tgt, mp)); g["_auto"]["roles"] = roles["slots"]
    return g


def tables():
    import build_melee_fighter as B
    iso = os.environ.get("GW_ISO_VANILLA") or sys.exit("GW_ISO_VANILLA is not set (source .env)")
    g = mex_hsd.Gcm(iso); tmp = os.path.join(skin.ROOT, "_build", "tmp", "autogroups"); os.makedirs(tmp, exist_ok=True)
    plco = os.path.join(tmp, "PlCo.dat"); open(plco, "wb").write(g.read("PlCo.dat")); rows = []
    for name, (kind, code, _, _) in B.FIGHTERS.items():
        if name == "captain": continue
        nr, pl = os.path.join(tmp, "Pl%sNr.dat" % code), os.path.join(tmp, "Pl%s.dat" % code)
        open(nr, "wb").write(g.read("Pl%sNr.dat" % code)); open(pl, "wb").write(g.read("Pl%s.dat" % code))
        try:
            r, _ = target_roles(nr, pl, name, plco, tmp)
            json.dump({k: r[k] for k in ("fighter", "models", "tables", "eye_dobjs", "confidence", "needs_review")} |
                      {"slots": [{k: s[k] for k in ("dobj", "joint", "region", "tris", "tobjs", "role", "confidence", "why")} for s in r["slots"]]},
                      open(os.path.join(HERE, "maps", name + ".roles.json"), "w"), indent=1)
            c = {}
            for s in r["slots"]: c[s["role"].split(":")[0]] = c.get(s["role"].split(":")[0], 0) + 1
            rows.append((name, len(r["slots"]), r["models"], c, r["confidence"], r["needs_review"]))
        except Exception as e:
            rows.append((name, 0, 0, {"error": str(e)[:60]}, 0, True))
        finally:
            for f in (nr, pl, nr + ".inspect.json"):
                if os.path.exists(f): os.remove(f)
    for r in rows:
        print("%-12s slots %3d models %2d  %-60s conf %.2f %s" % (r[0], r[1], r[2], r[3], r[4], "NEEDS REVIEW" if r[5] else ""))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("roles"); p.add_argument("costume"); p.add_argument("fighter_dat"); p.add_argument("--fighter"); p.add_argument("--plco"); p.add_argument("-o")
    p = sp.add_parser("groups"); p.add_argument("source"); p.add_argument("costume"); p.add_argument("fighter_dat")
    p.add_argument("--fighter"); p.add_argument("--plco"); p.add_argument("--map"); p.add_argument("-o", required=True)
    sp.add_parser("tables")
    a = ap.parse_args()
    if a.cmd == "roles":
        r, _ = target_roles(a.costume, a.fighter_dat, a.fighter, a.plco)
        s = json.dumps(r, indent=1); open(a.o, "w").write(s) if a.o else print(s)
    elif a.cmd == "groups":
        g = make_groups(a.source, a.costume, a.fighter_dat, a.fighter, a.plco, a.map); json.dump(g, open(a.o, "w"), indent=1)
        for n in g["_auto"]["notes"]: print(n)
        print("confidence %.2f%s" % (g["_auto"]["confidence"], "  NEEDS REVIEW" if g["_auto"]["needs_review"] else ""))
    else:
        tables()


if __name__ == "__main__":
    main()
