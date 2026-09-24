"""Meta Knight's Brawl effects on the metaknight-slot: an effect bank + the script commands that spawn it.

    python tools/build_mk_effects.py [--mod mods-slot/metaknight-slot] [--dry]

Run by build_mk_slot.py as its last step (after install_mk and geno.json), on the finished mod folder. Owns:
  files/EfBmData.dat  MK's effect bank (effBmDataTable + m-ex effBehaviorTable), built by effects/tools/efbuild from
                      ef_metaknight.pac (effects/tools/efexport.exe dump, cached in effects/work/ef_metaknight.json):
                      the 25 Brawl effect models converted (geometry, textures, VIS0/CHR0/SRT0/CLR0 animation) and the
                      three REFF particle effects re-authored as Melee generators (effects/tools/mk_ptcl.py)
  files/MxDt.dat      + one effect-table row (EfBmData.dat / effBmDataTable, appended) and MK's effect_index -> it
  files/PlBm.dat      the effect commands (GFX, sword trail) merged into every motion row whose clip is a Brawl
                      subaction with graphic events; rows are repointed at rewritten copies (append-only); the old
                      Kirby GFX of a rewritten row is replaced. Plus an ftFunction blob whose GetTrailData override
                      gives the sword afterimage MK's colours (Melee draws no trail for an m-ex fighter without one).
  geno.json           the same commands merged into the v1 overlays of those rows (overlays replace the Pl script on
                      the Geno exe)
Scripts are matched by clip, not by move key, so rows the other build steps add or rebuild pick their effects up on the
next run. Report: effects/work/fx_report.json."""
import argparse, json, os, struct, subprocess, sys, hashlib, collections
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE)
FX = os.path.join(MK, "effects"); FXT = os.path.join(FX, "tools"); FXW = os.path.join(FX, "work")
sys.path.insert(0, FXT); sys.path.insert(0, os.path.join(MK, "model", "tools"))
sys.path.insert(0, r"C:/Users/Gurek/Desktop/GD's Melee/tools/mex_port")
import ftscript as FS
import brawl_fx as BF
import install_mk as IM
import mex_hsd

EF_PAC = r"C:\iso\brawl-extract\files\effect\fighter\ef_metaknight.pac"
EF_COMMON = r"C:\iso\brawl-extract\files\effect\ef_common.pac"
EXPORT_EXE = os.path.join(FXT, "efexport.exe")
EFBUILD = os.path.join(FXT, "efbuild", "bin", "Release", "net8.0", "efbuild.exe")
EF_JSON = os.path.join(FXW, "ef_metaknight.json")
BANK_FILE, BANK_SYM = "EfBmData.dat", "effBmDataTable"
MK_INTERNAL = 52

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=os.path.join(MK, "mods-slot", "metaknight-slot"))
ap.add_argument("--dry", action="store_true", help="build and report, write nothing into the mod")
ap.add_argument("--no-trail", action="store_true")
A = ap.parse_args()
FILES = os.path.join(A.mod, "files")
REP = {"bank": {}, "rows": {}, "overlays": {}, "notes": []}


# ------------------------------------------------------------------ 1. Brawl dump
def export():
    if not os.path.exists(EF_JSON) or os.path.getmtime(EF_JSON) < os.path.getmtime(EFBUILD if False else EXPORT_EXE):
        os.makedirs(FXW, exist_ok=True)
        subprocess.run([EXPORT_EXE, EF_PAC, EF_JSON, EF_COMMON], check=True, cwd=FXT)
    return json.load(open(EF_JSON))


# ------------------------------------------------------------------ 2. MxDt: the bank row
def mxdt_bank(path, write):
    w = IM.Writer(open(path, "rb").read())
    root = w.ar.public("mexData")
    md = w.u32(root); eff = w.u32(root + 0x18); tbl = w.u32(eff); n = w.u32(md + 0x24)
    ft = w.u32(root + 0x08); effidx = w.u32(ft + 0x24)
    rows = []
    for i in range(n):
        f = w.u32(tbl + 12 * i); s = w.u32(tbl + 12 * i + 4)
        rows.append((w.str_at(f) if f else None, w.str_at(s) if s else None))
    bank = next((i for i, r in enumerate(rows) if r[0] == BANK_FILE), None)
    if bank is None:
        bank = n
        if n + 1 > 65: raise SystemExit("MxDt has %d effect banks; the port's particle arrays hold 65" % n)
        new = w.alloc(bytes(12 * (n + 1)), 4)
        for i in range(n):
            for k in range(3):
                o = tbl + 12 * i + 4 * k
                if o in w.relocs: w.ptr(new + 12 * i + 4 * k, w.u32(o))
                else: w.put(new + 12 * i + 4 * k, w.u32(o))
        w.ptr(new + 12 * n, w.cstr(BANK_FILE)); w.ptr(new + 12 * n + 4, w.cstr(BANK_SYM))
        w.ptr(eff, new); w.put(md + 0x24, n + 1)
    old = w.data[effidx + MK_INTERNAL]
    w.data[effidx + MK_INTERNAL] = bank
    REP["bank"].update({"mxdt_rows_before": n, "bank": bank, "effect_index_before": old, "row": [BANK_FILE, BANK_SYM]})
    if write: w.save(path)
    return bank


# ------------------------------------------------------------------ 3. the bank file
def build_bank(ef, bank, out):
    import mk_ptcl
    models = []
    for m in ef["models"]:
        s = {"src": m["brres"], "behavior": 6, "name": m["name"]}
        if "ShuttleLoop" in m["name"]: s["behavior"] = 4          # placed at TopN, facing, not following (11001000)
        if "Attack100" in m["name"]: s.update(lifetime=0, loop=True)   # rapid jab: lives until the action ends
        if "SwordFlare" in m["name"]: s["lifetime"] = BF.FLARE_LIFE
        models.append(s)
    spec = {"symbol": BANK_SYM, "models": models, "ptcl": mk_ptcl.spec(ef, bank * 1000)}
    sp = os.path.join(FXW, "spec.json"); json.dump(spec, open(sp, "w"), indent=1)
    subprocess.run([EFBUILD, "build", EF_JSON, sp, out], check=True, stdout=subprocess.DEVNULL)
    rp = os.path.join(FXW, "efbuild_report.json")
    os.replace(out + ".report.json", rp)                   # keep the build report out of the mod's files/
    r = json.load(open(rp))
    REP["bank"]["file"] = {"bytes": os.path.getsize(out), "sha1": hashlib.sha1(open(out, "rb").read()).hexdigest()[:12],
                           "models": len(models), "generators": len(spec["ptcl"]["generators"])}
    REP["bank"]["models"] = {k: {kk: v[kk] for kk in ("frames", "loop", "lifetime")} for k, v in r.items() if not k.startswith("_")}
    REP["bank"]["behaviours"] = {"models": [m["behavior"] for m in models], "ptcl": [g["behavior"] for g in spec["ptcl"]["generators"]]}


# ------------------------------------------------------------------ 4. events -> Melee commands
def encode(ev, efls_to_brres):
    fr, kind, d = ev
    if kind == "model":
        return FS.gfx_words(BF.MDL_BASE + d["brres"], d["bone"], d["off"], destroy=d["destroy"])
    if kind == "ptcl":
        return FS.gfx_words(BF.PTCL_BASE + d["gen"], d["bone"], d["off"], destroy=d["destroy"])
    if kind == "common":
        return FS.gfx_words(d["id"], d["bone"], d["off"], d.get("rng", (0, 0, 0)))
    if kind == "flare":
        return FS.gfx_words(BF.MDL_BASE + BF.FLARE_BRRES, d["bone"], destroy=True)
    if kind == "trail":
        return None if A.no_trail else [FS.trail_word(d["on"])]
    raise ValueError(kind)


def clip_parts(clip, subs):
    """'AttackS4Start+AttackS4S' -> [(AttackS4Start, 0), (AttackS4S, 21)] (Brawl frames of each joined clip)."""
    out = []; off = 0
    for n in clip.split("+"):
        out.append((n, off))
        x = subs.get(n); off += int(x["engine"]["brawl.psa"].get("anim_frames") or 0) if x else 0
    return out


def events_for_clip(clip, frames, subs, scripts, e2b):
    evs = []; notes = []
    for n, off in clip_parts(clip, subs):
        pe, nt = BF.plan_subaction(n, subs, scripts, e2b, None)
        if not pe and "SpecialAir" in n:                  # Brawl gives some air specials no graphic events of their
            n2 = n.replace("SpecialAir", "Special")        # own (SpecialAirLwF/B, AirLwStart): use the ground version's
            pe, nt2 = BF.plan_subaction(n2, subs, scripts, e2b, None)
            if pe: nt = nt2 + ["%s has no graphic events: %s's used" % (n, n2)]
        evs += [(fr + off, k, d) for fr, k, d in pe if fr + off < frames]
        notes += ["%s: %s" % (n, x) for x in nt]
    return evs, notes


# ------------------------------------------------------------------ 5. Pl file + overlays
def rewrite_pl(pl_path, geno_path, subs, scripts, e2b, write):
    w = IM.Writer(open(pl_path, "rb").read())
    ftsym = [s for s, _ in w.ar.publics if s.startswith("ftData")][0]
    fd = w.ar.public(ftsym); mt = w.u32(fd + 0xC)
    nrows = (w.u32(fd + 0x10) if False else None)
    MR = json.load(open(os.path.join(MK, "anim", "out", "motion_rows.json")))
    by_off = {(c["offset"], c["size"]): c for c in MR["clips"] + MR["extras"]}
    G = json.load(open(geno_path)) if os.path.exists(geno_path) else None
    ovl = {s["index"]: s for s in (G["fighters"][0].get("subactions", []) if G else [])}
    done = {}                                               # (old script, clip) -> new script offset
    r = 0
    while True:
        o = mt + r * 0x18
        if o + 0x18 > len(w.data) or r > 600: break
        sc = w.u32(o + 0xC) if (o + 0xC) in w.relocs else 0
        c = by_off.get((w.u32(o + 4), w.u32(o + 8)))
        if w.u32(o) == 0 and sc == 0 and c is None and r > 480: break
        if sc and c is not None:
            clip = c["brawl_clip"]; frames = int(c["frames"])
            evs, notes = events_for_clip(clip, frames, subs, scripts, e2b)
            if evs:
                enc = [(fr, encode((fr, k, d), e2b), d["label"], k) for fr, k, d in evs]
                enc = [(fr, ws, lab, k) for fr, ws, lab, k in enc if ws]
                key = (sc, clip)
                cmds = FS.parse_at(w.u32, sc)
                loops_to_start = cmds[-1][0] == FS.GOTO and w.u32(cmds[-1][2] + 4) == sc
                once = [(fr, ws, lab) for fr, ws, lab, k in enc if loops_to_start and fr == 0 and k in ("model", "ptcl")]
                rest = [(fr, ws, lab) for fr, ws, lab, k in enc if not (loops_to_start and fr == 0 and k in ("model", "ptcl"))]
                if key not in done:
                    new, rep = FS.insert(cmds, rest, strip={FS.GFX}, clip=frames, u32=w.u32)
                    new = [(FS.GFX, ws, None) for _, ws, _ in once] + new
                    # write: word list, Goto / Subroutine targets relocated
                    pos = []; p = 0
                    for cc in new: pos.append(p); p += 4 * len(cc[1])
                    at = w.alloc(bytes(p), 4)
                    old_off = {i: cmds[i][2] for i in range(len(cmds))}
                    new_of_old = {cc[2]: at + pos[j] for j, cc in enumerate(new) if cc[2] is not None}
                    first_orig = next(at + pos[j] for j, cc in enumerate(new) if cc[2] == 0) if any(cc[2] == 0 for cc in new) else at
                    for j, cc in enumerate(new):
                        for k2, word in enumerate(cc[1]): w.put(at + pos[j] + 4 * k2, word)
                        if cc[0] in (FS.GOTO, FS.SUB) and cc[2] is not None:
                            t = w.u32(old_off[cc[2]] + 4)
                            oi = next((i for i in old_off if old_off[i] == t), None)
                            if cc[0] == FS.GOTO and t == sc: nt = first_orig
                            elif oi is not None: nt = new_of_old.get(oi, t)
                            elif cc[0] == FS.GOTO:
                                # install_mk's row copies are [ModelVis] + the original, looping back into the
                                # ORIGINAL body: loop into this copy's own body instead, so the effects repeat
                                body = [x[1] for x in FS.parse_at(w.u32, t)]
                                own = [x[1] for x in cmds]
                                si = next((i for i in range(len(own)) if own[i:-1] == body[:-1]), None)
                                nt = t
                                if si is not None:
                                    cand = [new_of_old[i] for i in range(si, len(cmds)) if i in new_of_old]
                                    if cand: nt = min(cand); REP["notes"].append("row %d: loop retargeted into its own body (old +%d)" % (r, si))
                            else: nt = t
                            w.ptr(at + pos[j] + 4, nt)
                    done[key] = (at, rep, len(once))
                at, rep, n_once = done[key]
                w.ptr(o + 0xC, at)
                REP["rows"][r] = {"clip": clip, "frames": frames, "script": [hex(sc), hex(at)], "stripped_gfx": rep["stripped"],
                                  "once_before_loop": n_once, "placed": [(f, l) for f, l in rep["placed"]] ,
                                  "dropped": rep["dropped"], "skipped": notes}
                if r in ovl and "words" in ovl[r]:
                    old = [int(x, 16) if isinstance(x, str) else int(x) for x in ovl[r]["words"]]
                    oc = FS.parse_words(old)
                    if any(c2[0] == FS.GOTO for c2 in oc): REP["notes"].append("overlay row %d has a Goto: left alone" % r)
                    else:
                        nw, rp = FS.insert(oc, [(fr, ws, lab) for fr, ws, lab, k in enc], strip={FS.GFX}, clip=frames, u32=w.u32)
                        nw, fixed = FS.fix_overlay_skips(oc, nw)
                        ovl[r]["words"] = ["0x%08X" % x for x in FS.to_words(nw)]
                        REP["overlays"][r] = {"placed": rp["placed"], "dropped": rp["dropped"], "skips_fixed": fixed}
        r += 1
    bad = []
    for r2, o2 in ovl.items():
        if "words" not in o2: continue
        ws = [int(x, 16) if isinstance(x, str) else int(x) for x in o2["words"]]
        if any(((x >> 26) == FS.GENO and ((x >> 20) & 0x3F) == 0x13) for x in ws): continue      # ORIG overlays
        plain = [c for c in FS.parse_words(ws) if c[0] != FS.GENO]
        sc2 = w.u32(mt + r2 * 0x18 + 0xC)
        pl = [(c[0], c[1]) for c in FS.parse_at(w.u32, sc2)]
        def timed(cs):       # (counter, words) of every non-wait command: an escape may add a wait of its own
            tl, _ = FS.timeline(cs)
            return [(f, c[1]) for f, c in zip(tl, cs) if c[0] not in (FS.SYNC, FS.ASYNC)]
        if timed(plain) != timed(pl): bad.append(r2)
    REP["overlay_check"] = {"overlays_equal_to_pl_minus_escapes": len([k for k in ovl if "words" in ovl[k]]) - len(bad), "mismatch": bad}
    if bad: REP["notes"].append("overlay != Pl script (minus escapes) for rows %s" % bad)
    if write:
        w.save(pl_path)
        if G is not None: json.dump(G, open(geno_path, "w"), indent=1)
    return w


# ------------------------------------------------------------------ 6. sword trail: ftFunction GetTrailData
# Arch_FighterFunc slot 45 (GetTrailData, Header.s +0xB4). The blob returns a pointer to its own trailing SwordAttrs
# (ftMars/types.h, as Marth's dat_attrs +0x78): position-independent (bl/mflr), so no instruction relocations.
TRAIL = {"inner": 0.2, "outer": 1.0, "alpha": (255, 0), "rgb_a": (72, 88, 255), "rgb_b": (255, 236, 150),
         "part": 41, "base": 1.8, "tip": 14.0}     # part 41 = SwordM: the blade runs along its +X from 0 to 14.26


def trail_blob():
    code = [0x7C0802A6, 0x48000005, 0x7C6802A6, 0x7C0803A6, 0x38630010, 0x4E800020]   # mflr r0; bl +4; mflr r3; mtlr r0; addi r3,r3,0x10; blr
    t = TRAIL
    data = struct.pack(">2f", t["inner"], t["outer"]) + bytes([t["alpha"][0], t["alpha"][1], *t["rgb_a"], 0, *t["rgb_b"]]) \
        + bytes(3) + struct.pack(">i2f", t["part"], t["base"], t["tip"])
    assert len(data) == 0x20
    return b"".join(struct.pack(">I", x) for x in code) + data


def add_ftfunction(pl_path, write):
    raw = open(pl_path, "rb").read()
    ar = mex_hsd.Archive(raw)
    if any(s == "ftFunction" for s, _ in ar.publics):
        REP["notes"].append("PlBm.dat already has an ftFunction: trail blob not added")
        return
    w = IM.Writer(raw)
    blob = trail_blob()
    code = w.alloc(blob, 0x20)
    frt = w.alloc(struct.pack(">2I", 45, 0), 4)          # {ReplaceThis = slot 45, ReplaceWith = code offset 0}
    st = w.alloc(bytes(0x20), 4)
    w.ptr(st + 0x00, code); w.put(st + 0x04, 0); w.put(st + 0x08, 0)
    w.ptr(st + 0x0C, frt); w.put(st + 0x10, 1); w.put(st + 0x14, len(blob)); w.put(st + 0x18, 0); w.put(st + 0x1C, 0)
    # the pointer fields at +0 / +0xC must be relocations (HSD relocates them to data-relative offsets)
    # public symbol table: append one entry {data offset, string offset} and its name
    tail = ar.raw[ar.o_public:]
    nb_pub, nb_ext = ar.nb_public, ar.nb_extern
    pubs = [struct.unpack(">2I", tail[8 * i:8 * i + 8]) for i in range(nb_pub)]
    exts = [struct.unpack(">2I", tail[8 * (nb_pub + i):8 * (nb_pub + i) + 8]) for i in range(nb_ext)]
    strtab = bytearray(tail[8 * (nb_pub + nb_ext):])
    name_off = len(strtab); strtab += b"ftFunction\0"
    pubs.append((st, name_off))
    while len(w.data) % 4: w.data.append(0)
    rel = sorted(w.relocs)
    ntail = b"".join(struct.pack(">2I", *p) for p in pubs) + b"".join(struct.pack(">2I", *e) for e in exts) + bytes(strtab)
    body = bytes(w.data) + b"".join(struct.pack(">I", x) for x in rel) + ntail
    hdr = struct.pack(">5I", 0x20 + len(body), len(w.data), len(rel), nb_pub + 1, nb_ext) + ar.raw[0x14:0x20]
    REP["trail"] = dict(TRAIL, code_offset=hex(code), struct=hex(st), blob_bytes=len(blob))
    if write: open(pl_path, "wb").write(hdr + body)


# ------------------------------------------------------------------ 7. Dimensional Cape: a dark warp tint (visuals pass addition)
# Brawl's MantleStart / MantleEnd bursts refract the frame buffer through a drop mask (a dark warp around MK); Melee has
# no frame-buffer effect, so besides the violet burst particles (gen 1 / 2) MK himself takes the warp's colour: Melee's
# common colour animation 95 (PlCo ftLoadCommonData colour-anim table: 1 frame white 120, then violet (80, 0, 180) at
# alpha 90 fading to 0 over 24 frames - the darkness-element hit tint) starts with each MantleStart / MantleEnd burst,
# so MK darkens violet while the cape closes (5..12, then he is hidden) and comes out of the warp violet, fading.
# Script command op 46 (ftAction_80072A5C -> ftCo_800BFFD0(fp, id, 0)). Rows and overlays: where rewrite_pl placed the bursts.
COLANIM_OP, CAPE_WARP_COLANIM = 46, 95


def cape_warp_colanim(pl_path, geno_path, write):
    word = (COLANIM_OP << 26) | (CAPE_WARP_COLANIM << 18)
    w = IM.Writer(open(pl_path, "rb").read())
    fd = w.ar.public([s for s, _ in w.ar.publics if s.startswith("ftData")][0]); mt = w.u32(fd + 0xC)
    G = json.load(open(geno_path)) if os.path.exists(geno_path) else None
    ovl = {s["index"]: s for s in (G["fighters"][0].get("subactions", []) if G else [])}
    done = {}; rep = {"rows": {}, "overlays": {}}
    def frames_of(placed): return sorted({int(f) for f, lab in placed if "PtcMetaknightMantle" in str(lab)})
    for r, v in REP["rows"].items():
        fr = frames_of(v["placed"])
        if not fr: continue
        o = mt + int(r) * 0x18 + 0xC; sc = w.u32(o)
        ev = [(f, [word], "cape warp colanim %d" % CAPE_WARP_COLANIM) for f in fr]
        if sc not in done:
            cmds = FS.parse_at(w.u32, sc)
            new, rp = FS.insert(cmds, ev, clip=int(v["frames"]), u32=w.u32)
            pos = []; p = 0
            for cc in new: pos.append(p); p += 4 * len(cc[1])
            at = w.alloc(bytes(p), 4)
            old_off = {i: cmds[i][2] for i in range(len(cmds))}
            new_of_old = {cc[2]: at + pos[j] for j, cc in enumerate(new) if cc[2] is not None}
            first = next((at + pos[j] for j, cc in enumerate(new) if cc[2] == 0), at)
            for j, cc in enumerate(new):
                for k2, wd in enumerate(cc[1]): w.put(at + pos[j] + 4 * k2, wd)
                if cc[0] in (FS.GOTO, FS.SUB) and cc[2] is not None:
                    t = w.u32(old_off[cc[2]] + 4); oi = next((i for i in old_off if old_off[i] == t), None)
                    w.ptr(at + pos[j] + 4, first if (cc[0] == FS.GOTO and t == sc) else new_of_old.get(oi, t) if oi is not None else t)
            done[sc] = (at, rp)
        w.ptr(o, done[sc][0]); rep["rows"][r] = {"frames": fr, "placed": done[sc][1]["placed"], "dropped": done[sc][1]["dropped"]}
        ri = int(r)
        if ri in ovl and "words" in ovl[ri]:
            oc = FS.parse_words([int(x, 16) if isinstance(x, str) else int(x) for x in ovl[ri]["words"]])
            if not any(c2[0] == FS.GOTO for c2 in oc):
                nw, rp = FS.insert(oc, ev, clip=int(v["frames"]), u32=w.u32)
                nw, fixed = FS.fix_overlay_skips(oc, nw)
                ovl[ri]["words"] = ["0x%08X" % x for x in FS.to_words(nw)]
                rep["overlays"][r] = {"placed": rp["placed"], "dropped": rp["dropped"], "skips_fixed": fixed}
    REP["cape_warp_colanim"] = rep
    if write:
        w.save(pl_path)
        if G is not None: json.dump(G, open(geno_path, "w"), indent=1)


def main():
    ef = export()
    e2b = {e["i"]: e["brres"] for e in ef["efls"] if e["brres"] is not None}
    subs, scripts = BF.load_ir()
    write = not A.dry
    bank = mxdt_bank(os.path.join(FILES, "MxDt.dat"), write)
    out = os.path.join(FILES if write else FXW, BANK_FILE)
    build_bank(ef, bank, out)
    rewrite_pl(os.path.join(FILES, "PlBm.dat"), os.path.join(A.mod, "geno.json"), subs, scripts, e2b, write)
    if not A.no_trail: add_ftfunction(os.path.join(FILES, "PlBm.dat"), write)
    cape_warp_colanim(os.path.join(FILES, "PlBm.dat"), os.path.join(A.mod, "geno.json"), write)
    REP["summary"] = {"rows_rewritten": len(REP["rows"]), "overlays_rewritten": len(REP["overlays"]),
                      "events_placed": sum(len(v["placed"]) for v in REP["rows"].values()),
                      "events_dropped": sum(len(v["dropped"]) for v in REP["rows"].values())}
    json.dump(REP, open(os.path.join(FXW, "fx_report.json"), "w"), indent=1, default=str)
    print("   effects: bank %d (%s), %d rows rewritten, %d overlays, %d events placed, %d dropped%s" % (
        bank, BANK_FILE, REP["summary"]["rows_rewritten"], REP["summary"]["overlays_rewritten"], REP["summary"]["events_placed"],
        REP["summary"]["events_dropped"], "" if write else " (dry run)"))


if __name__ == "__main__":
    main()
