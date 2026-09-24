"""Offline verification of a Meta Knight build (tools/build_mk.py output folder).

    python tools/verify_mk.py [--mod build/stage] [--tag phase1]

1. experiment/brawl-kirby/tools/verify_mod.py, unchanged, on stage A (<mod>/files/PlKb.dat): every written hitbox field,
   start frame and window, IASA, throw values, attributes, special attributes, the tuning re-derivation, and every row
   the build does not write byte-identical to vanilla Kirby.
2. Meta Knight extras on stage A: grab boxes are catch boxes (element 8) with MK's size/start; every added command
   (RapidJab, BodyCollState, FighterVis, loop checkpoints, throw release, multi-jump gate, ModelVis) is in the script
   at its counter; loops end in Goto-self with a wait; no Geno escape (opcode 59) in the Pl file.
3. Stage B (<mod>/final/PlBm.dat, the shipped file), every script reachable from the motion table:
   hitbox / GFX / wind bones are MK joints (< 105), hurtbox-state bones are one of MK's 9 hurtbox joints (the engine
   asserts "illegal parts" otherwise), ModelVis only names model 0 (cape, states 0-2) or 1 (body, 0-1); rows this build
   wrote are byte-identical to stage A.
4. geno.json overlays: every escape is a known v1 sub with the right length, and the overlay minus its escapes is
   exactly the Pl file's script for that row."""
import os, sys, json, subprocess, argparse, struct
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE); EXP = os.path.join(os.path.dirname(os.path.dirname(MK)), "experiment")
BKT = os.path.join(EXP, "brawl-kirby", "tools")
sys.path.insert(0, r"C:/Users/Gurek/Desktop/GD's Melee/tools/mex_port"); sys.path.insert(0, os.path.join(MK, "model", "tools"))
import mex_hsd
ap = argparse.ArgumentParser(); ap.add_argument("--mod", default=os.path.join(MK, "build", "stage")); ap.add_argument("--tag", default="phase1")
a = ap.parse_args()
dec = os.path.join(MK, "analysis", f"{a.tag}_decoded.json"); rep = os.path.join(MK, "analysis", f"{a.tag}_verify.json")
r = subprocess.run([sys.executable, os.path.join(BKT, "verify_mod.py"), "--mod", a.mod, "--decode", "--decoded", dec, "--report", rep],
                   capture_output=True, text=True)
lines = r.stdout.strip().splitlines()
bk_fails = int([l for l in lines if l.startswith("FAILS")][-1].split()[1])
for l in lines:
    if l.startswith(("FAIL", "unchanged", "attributes", "tuning", "FAILS")): print("verify_mod:", l[:260])
O = json.load(open(dec)); C = json.load(open(os.path.join(a.mod, "CHANGES.json")))
osc = {s["offset"]: s for s in O["scripts"]}
extra = []
def fail(m): extra.append(m)
WANT = [("RapidJab", "RapidJab"), ("BodyCollState", "BodyCollState"), ("FighterVis", "FighterVis"), ("ModelVis", "ModelVis"),
        ("loop checkpoint", "ThrowFlagB3/B4"), ("throw release", "ThrowFlagB3/B4"), ("multi-jump gate", "SetCmdVar")]
for m in C["moves"]:
    row = O["motion_table"][m["melee_row"]]; sc = osc[row["script"]]; evs = sc["events"]
    if m.get("written_catch_boxes"):
        got = [(e.get("frame"), e["hitbox"]) for e in evs if e["name"] == "Hitbox"]
        exp = m["written_catch_boxes"]
        if len(got) != len(exp): fail(f"{m['move']}: {len(got)} catch boxes decoded, {len(exp)} written")
        for (f, h), x in zip(got, exp):
            if h["element_raw"] != 8: fail(f"{m['move']} slot{x['slot']}: element {h['element_raw']} is not catch (8)")
            if abs(h["size"] - x["size"]) > 1 / 256 + 1e-6: fail(f"{m['move']} slot{x['slot']}: size {h['size']} != {x['size']}")
            if f is not None and f + 1 != x["active"][0]: fail(f"{m['move']} slot{x['slot']}: start {f + 1} != {x['active'][0]}")
    for c, label in m.get("extra_events", []):
        want = next((n for p, n in WANT if label.startswith(p) or p in label), None)
        if want and not any(e["name"] == want and (e.get("frame") is None or e["frame"] == c) for e in evs):
            fail(f"{m['move']} row {m['melee_row']}: {want} @{c} missing ({label})")
    names = [e["name"] for e in evs]
    if "Goto" in names:
        g = [e for e in evs if e["name"] == "Goto"][-1]
        if int(g["args"]["target"], 16) != int(row["script"], 16): fail(f"{m['move']}: Goto does not loop to itself")
        if not any(n in ("SyncWait", "AsyncWait", "SetTimerAnim") for n in names[:-1]): fail(f"{m['move']}: loop without a wait")
    if any(e["op"] == "engine.unknown" for e in evs): fail(f"{m['move']}: unknown opcode (a Geno escape?) in the Pl file")

# ---- stage B
J = IM_J = json.load(open(os.path.join(MK, "model", "work", "skeleton.json")))["joints"]
HURT = {h["bone"] for h in json.load(open(os.path.join(MK, "analysis", "brawl_metaknight.json")))["hurtboxes"]}
FL = [1, 1, 1, 1, 1, 2, 1, 2, 1, 1]
OL = [5, 5, 1, 1, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1, 1, 7, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 2, 1, 4]
def scripts_of(path):
    ar = mex_hsd.Archive(open(path, "rb").read()); d = ar.data; rel = set(ar.reloc_offsets)
    u = lambda o: struct.unpack(">I", d[o:o + 4])[0]
    fd = ar.public([s for s, _ in ar.publics if s.startswith("ftData")][0]); mt = u(fd + 0xC)
    rows = {}
    for r_ in range(len(O["motion_table"])):
        po = mt + r_ * 0x18 + 0xC
        if po in rel: rows[r_] = u(po)
    cmds = {}; seen = set()
    def walk(o, owner):
        while o not in seen and o + 4 <= len(d):
            seen.add(o); w = u(o); op = w >> 26
            if op < 10:
                if op in (0, 6): return
                if op in (5, 7):
                    t = u(o + 4) if (o + 4) in rel else 0
                    if t: walk(t, owner)
                    if op == 7: return
                o += 4 * FL[op]; continue
            if op - 10 >= len(OL): cmds[o] = (owner, op, [w]); return
            ln = OL[op - 10]; cmds[o] = (owner, op, [u(o + 4 * k) for k in range(ln)]); o += 4 * ln
    for r_, s in rows.items(): walk(s, r_)
    def words_at(o):
        out = []
        while True:
            w = u(o); op = w >> 26
            ln = FL[op] if op < 10 else (OL[op - 10] if op - 10 < len(OL) else 1)
            out += [u(o + 4 * k) for k in range(ln)]
            if op in (0, 6, 7) or len(out) > 4000: return out
            o += 4 * ln
    return rows, cmds, words_at
final = os.path.join(a.mod, "final", "PlBm.dat")
rowsB, cmdsB, wordsB = scripts_of(final)
_, _, wordsA = scripts_of(os.path.join(a.mod, "files", "PlKb.dat"))
rowsA = scripts_of(os.path.join(a.mod, "files", "PlKb.dat"))[0]
bad = {"bone": 0, "hurt": 0, "vis": 0}
for o, (owner, op, ws) in cmdsB.items():
    w0 = ws[0]
    if op == 11 and not (w0 >> 10) & 1 and ((w0 >> 11) & 0xFF) >= len(J): bad["bone"] += 1; fail(f"stage B row {owner}: hitbox bone {(w0 >> 11) & 0xFF} >= {len(J)}")
    if op == 10 and not (w0 >> 17) & 1 and not (w0 >> 15) & 1 and ((w0 >> 18) & 0xFF) >= len(J): bad["bone"] += 1; fail(f"stage B row {owner}: GFX bone {(w0 >> 18) & 0xFF}")
    if op == 58 and (w0 & 0xFF) >= len(J): bad["bone"] += 1; fail(f"stage B row {owner}: wind bone {w0 & 0xFF}")
    if op == 28 and ((w0 >> 18) & 0xFF) not in HURT: bad["hurt"] += 1; fail(f"stage B row {owner}: hurtbox-state bone {(w0 >> 18) & 0xFF} is not an MK hurtbox joint {sorted(HURT)}")
    if op == 31:
        i, v = (w0 >> 19) & 0x7F, w0 & 0x7FFFF
        if i > 1 or (i == 0 and v > 3) or (i == 1 and v > 1): bad["vis"] += 1; fail(f"stage B row {owner}: ModelVis({i},{v}) outside MK's models")
mine = {m["melee_row"] for m in C["moves"]}
for r_ in mine:
    if wordsB(rowsB[r_]) != wordsA(rowsA[r_]): fail(f"stage B changed row {r_} that the build wrote")
# ---- geno.json overlays
G = json.load(open(os.path.join(a.mod, "geno.json")))
LEN_OK = {0x09: {3}, 0x30: {2, 3, 4}, 0x31: {1, 2, 3}, 0x39: {2}, 0x13: {1}, 0x0A: {2}}
nov = 0
def timed(ws, check=None):
    """(frame, command words) for every non-wait command; escapes skipped (checked by `check`)."""
    out = []; o = 0; f = 0
    while o < len(ws):
        w = ws[o]; op = w >> 26
        if op == 59:
            if check: check(w)
            o += max((w >> 16) & 0xF, 1); continue
        ln = FL[op] if op < 10 else OL[op - 10]
        if op == 1: f += w & 0x3FFFFFF
        elif op == 2: f = max(f, w & 0x3FFFFFF)
        else: out.append((f, tuple(ws[o:o + ln])))
        o += ln
        if op in (0, 6, 7): break
    return out
for ov in G["fighters"][0].get("subactions", []):
    ws = [int(x, 16) for x in ov["words"]]
    def chk(w, ov=ov):
        global nov
        sub, ln = (w >> 20) & 0x3F, (w >> 16) & 0xF; nov += 1
        if sub not in LEN_OK or ln not in LEN_OK[sub]: fail(f"overlay row {ov['index']}: escape sub 0x{sub:02X} len {ln} not a known v1 form")
    ORIGW = (59 << 26) | (0x13 << 20) | (1 << 16)
    if ws and ws[-1] == ORIGW:        # escapes + ORIG: the row's own shipped (stage B) script runs after them
        pre = timed(ws[:-1], chk); nov += 1
        if pre: fail(f"overlay row {ov['index']}: ORIG overlay has plain commands before ORIG")
        if ov["index"] not in rowsB: fail(f"overlay row {ov['index']}: ORIG on a row without a script")
    elif timed(ws, chk) != timed(wordsB(rowsB[ov["index"]])): fail(f"overlay row {ov['index']}: overlay minus escapes differs from the Pl script")
# ---- Geno v2 profile (geno_v2_encodings.md): states, targets, specials, parameter blocks, rows
F = G["fighters"][0]
if G.get("geno", 1) >= 2:
    states = F.get("states", []); names = [s_["name"] for s_ in states]
    if len(states) > 48: fail(f"v2: {len(states)} states > GENO_MAX_STATES 48 (v3)")
    if len(set(names)) != len(names): fail("v2: duplicate state names")
    BHV = {"geno.air", "geno.ground", "geno.glide.start", "geno.glide", "geno.glide.attack", "geno.glide.landing", "geno.glide.end",
           "geno.tornado", "geno.drill.start", "geno.drill", "geno.drill.end", "geno.anim_motion",
           "geno.cape", "geno.cape.attack", "geno.cape.end"}
    def tgt_ok(t):
        if isinstance(t, int) or t in ("auto", "helpless"): return True
        k, _, v = str(t).partition(":")
        return (k == "geno" and (v in names or (v.isdigit() and int(v) < len(states)))) or (k in ("motion", "special") and v.isdigit())
    arB = mex_hsd.Archive(open(final, "rb").read()); dB = arB.data
    uB = lambda o: struct.unpack(">I", dB[o:o + 4])[0]
    mtB = uB(arB.public([s_ for s_, _ in arB.publics if s_.startswith("ftData")][0]) + 0xC)
    for i, s_ in enumerate(states):
        if s_["behavior"] not in BHV: fail(f"v2 state {s_['name']}: unknown behaviour {s_['behavior']}")
        for k in ("next", "land"):
            if k in s_ and not tgt_ok(s_[k]): fail(f"v2 state {s_['name']}: bad {k} target {s_[k]}")
        sa = s_.get("subaction")
        if not isinstance(sa, int) or sa not in rowsB: fail(f"v2 state {s_['name']}: subaction {sa} has no script"); continue
        if s_["behavior"] == "geno.drill" and not uB(mtB + sa * 0x18 + 0x10) & 0x80000000:
            fail(f"v2 state {s_['name']}: row {sa} is not animation-driven (0x80000000): the drill speed would be drill.speed")
        if sa not in {m["melee_row"] for m in C["moves"]}: fail(f"v2 state {s_['name']}: row {sa} is not a row this build wrote (no clip check after install)")
    for k, t in (F.get("specials") or {}).items():
        if not tgt_ok(t): fail(f"v2 specials.{k}: bad target {t}")
    for blk, n in (("glide", 22), ("tornado", 20), ("drill", 6), ("cape", 6)):
        miss = [f"w{i:02d}" for i in range(n) if f"w{i:02d}" not in (F.get(blk) or {})]
        if miss: fail(f"v2 {blk} block: missing Brawl words {miss}")
    if "speed" in (F.get("drill") or {}): fail("v2 drill.speed set: the rush speed should come from the clip's TransN")
    # every CHG / CHGAND GENO target in the overlays names a declared state
    for ov in F.get("subactions", []):
        ws = [int(x, 16) for x in ov["words"]]; o = 0
        while o < len(ws):
            w = ws[o]; op = w >> 26
            if op == 59:
                sub, ln = (w >> 20) & 0x3F, max((w >> 16) & 0xF, 1)
                if sub == 0x30 and (ws[o + 1] >> 28) == 2 and (ws[o + 1] & 0xFFFF) >= len(states):
                    fail(f"overlay row {ov['index']}: GENO({ws[o + 1] & 0xFFFF}) is not a declared state")
                o += ln; continue
            ln = FL[op] if op < 10 else OL[op - 10]; o += ln
            if op in (0, 6, 7): break
    # ---- Geno v3: Shuttle Loop / Drill Rush / Dimensional Cape as Geno states (no Kirby special code on the Geno exe)
    if G.get("geno", 1) >= 3:
        byname = {s_["name"]: (i, s_) for i, s_ in enumerate(states)}
        SP = F.get("specials") or {}
        KIRBY_SPECIAL_ROWS = set(range(305, 338))          # Kirby's inhale / hammer / Final Cutter / stone rows (the main exe's fallback)
        want_sp = {"hi": ("UpB", "geno.anim_motion"), "air_hi": ("UpBAir", "geno.anim_motion"), "lw": ("CapeStart", "geno.cape"),
                   "air_lw": ("CapeStartAir", "geno.cape"), "s": ("DrillStart", "geno.drill.start"), "air_s": ("DrillStartAir", "geno.drill.start")}
        for k, (nm, bh) in want_sp.items():
            if SP.get(k) != f"geno:{nm}": fail(f"v3 specials.{k} = {SP.get(k)}, want geno:{nm}")
            elif byname.get(nm, (0, {}))[1].get("behavior") != bh: fail(f"v3 state {nm}: behaviour {byname[nm][1].get('behavior')} != {bh}")
        for nm, (i, s_) in byname.items():
            if nm.startswith(("UpB", "Cape", "Drill")) and s_.get("subaction") in KIRBY_SPECIAL_ROWS:
                fail(f"v3 state {nm}: plays Kirby special row {s_['subaction']} (must be its own row)")
        def row_flags(r): return uB(mtB + r * 0x18 + 0x10)
        for nm in ("UpB", "UpBAir", "UpBLoop", "CapeN", "CapeNAir", "CapeF", "CapeFAir", "CapeB", "CapeBAir"):
            if nm in byname and not row_flags(byname[nm][1]["subaction"]) & 0x80000000:
                fail(f"v3 state {nm}: row {byname[nm][1]['subaction']} is not animation-driven (its TransN would not move MK)")
        order = [n for n in names if byname[n][1]["behavior"] == "geno.cape.attack"]
        if order != ["CapeN", "CapeNAir", "CapeF", "CapeFAir", "CapeB", "CapeBAir"]: fail(f"v3 cape attack order {order}")
        if [n for n in names if byname[n][1]["behavior"] == "geno.cape.end"] != ["CapeEnd", "CapeEndAir"]: fail("v3 cape end order")
        if [n for n in names if byname[n][1]["behavior"] == "geno.drill.end"] != ["DrillEndGround", "DrillEnd"]: fail("v3 drill end order (ground, air)")
        if (F.get("drill") or {}).get("bounce", 7) != 0: fail("v3 drill.bounce must be 0 (Brawl never ends the rush on hit / shield / wall)")
        if byname["DrillEnd"][1].get("land") != "motion:43": fail("v3 DrillEnd (air) must land in LandingFallSpecial")
        # the escapes each move needs, by row and counter
        OVW = {o["index"]: [int(x, 16) for x in o["words"]] for o in F.get("subactions", [])}
        def escapes(row):
            ws = OVW.get(row, []); out = []; o = 0; fr = 0
            while o < len(ws):
                w = ws[o]; op = w >> 26
                if op == 59:
                    ln = max((w >> 16) & 0xF, 1); out.append((fr, (w >> 20) & 0x3F, ws[o + 1:o + ln])); o += ln; continue
                ln = FL[op] if op < 10 else OL[op - 10]
                if op == 1: fr += w & 0x3FFFFFF
                elif op == 2: fr = max(fr, w & 0x3FFFFFF)
                o += ln
                if op in (0, 6, 7): break
            return out
        def has(row, fr, sub, first=None, label=""):
            if not any(f_ == fr and s2 == sub and (first is None or (a and a[0] == first)) for f_, s2, a in escapes(row)):
                fail(f"v3 row {row}: missing {label} @{fr}")
        GL = byname["Glide"][0]
        for nm in ("UpB", "UpBLoop"):
            r = byname[nm][1]["subaction"]
            has(r, 0, 0x30, (2 << 28) | GL, "CHG ANIM_END & AIR -> GENO(Glide)")
            has(r, 7, 0x09, 0x30, "PUT LEDGE 2 (Brawl Allow Ledgegrab @7)")
        if not byname["UpB"][1].get("liftoff"): fail("v3 UpB must lift off with the clip's rise (Brawl Set Air/Ground @5)")
        has(byname["Drill"][1]["subaction"], 20, 0x09, 0x30, "PUT LEDGE 1 (Brawl @20)")
        for nm in ("CapeStart", "CapeStartAir"): has(byname[nm][1]["subaction"], 12, 0x09, 0x31, "PUT HIDDEN 1 (vanish)")
        for nm in ("CapeN", "CapeNAir", "CapeF", "CapeFAir", "CapeB", "CapeBAir"): has(byname[nm][1]["subaction"], 1, 0x09, 0x31, "PUT HIDDEN 0 (reappear)")
        for nm in ("CapeN", "CapeNAir", "CapeB", "CapeBAir"): has(byname[nm][1]["subaction"], 1, 0x09, 0x01, "PUT FACING 0 (Reverse Direction)")
        for nm in ("CapeF", "CapeFAir"):
            if any(f_ == 1 and s2 == 0x09 and a and a[0] == 0x01 for f_, s2, a in escapes(byname[nm][1]["subaction"])): fail(f"v3 {nm} must not turn around")
        print("geno v3: Up-B / Drill Rush / Dimensional Cape states, rows and escapes checked")
    print(f"geno v2: {len(states)} states, specials {F.get('specials')}, glide/tornado/drill blocks checked")
print(f"stage B: {len(cmdsB)} commands in {len(rowsB)} row scripts; bad bones {bad['bone']}, bad hurtbox joints {bad['hurt']}, bad ModelVis {bad['vis']}")
print(f"geno.json: {len(G['fighters'][0].get('subactions', []))} overlays, {nov} escapes checked")
json.dump({"verify_mod_fails": bk_fails, "extra_fails": extra}, open(os.path.join(MK, "analysis", f"{a.tag}_verify_mk.json"), "w"), indent=1)
for x in extra[:40]: print("FAIL", x)
print(f"verify_mod fails {bk_fails} | MK checks: {len(extra)} fails")
print("FAILS", bk_fails + len(extra))
sys.exit(1 if bk_fails + len(extra) else 0)
