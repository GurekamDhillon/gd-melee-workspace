"""Numeric in-game checks of Meta Knight's model visuals (no screenshots): the draw list, the eyes, the shine layers, the
model-part states. Needs the Geno exe with the Lab (gd.dobjs, gd.set_motion), MK on port 1 in training (MELEE_LAB=1).

    python tools/ingame_visuals.py <console-port> [--report analysis/ingame_visuals.json]

1. draw list (gd.dobjs): 14 DObjs; the eye DObj (model/work/PlBmNr_build.json eye_dobj) is drawn (not hidden) with three
   TObjs - skin on TEX0, the two eye layers on TEX1 / TEX2, CI8 256x128 - and the costume texture-anim list holds exactly
   those two eye layers; the shoulder-pad and gem DObjs carry a REFLECTION + COLORMAP_ADD layer.
2. eyes per frame: every clip in PLAN is entered with gd.set_motion and stepped; each frame both costume eye TObjs'
   anim frame must be the state anim/out/eye_states.json gives that clip frame (last event <= frame, state 0 before the
   first), and their texture SRT must equal that state's values (the matanim track the engine applied).
3. model parts: in the up taunt (AppealHi) the cape model goes to state 3 (no cape) with the mantle ball at Brawl's frames,
   and every DObj's hidden flag matches the part table for the model states the engine reports."""
import sys, os, json, socket, argparse, collections
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument("port", type=int)
ap.add_argument("--report", default=os.path.join(MK, "analysis", "ingame_visuals.json"))
a = ap.parse_args()

sock = socket.create_connection(("127.0.0.1", a.port), timeout=60)
f = sock.makefile("r", encoding="utf-8", errors="replace"); f.readline()
def cmd(line):
    sock.sendall((line + "\n").encode()); out = []
    while True:
        r = f.readline()
        if not r: raise SystemExit("console closed (game gone?)")
        r = r.rstrip("\n")
        if r in (">>> ok", ">>> error"): return out, r == ">>> ok"
        if not r.startswith("> "): out.append(r)
def lua(expr):
    out, ok = cmd("= " + expr)
    return "\n".join(out).replace("[console] ", "")

BUILD = json.load(open(os.path.join(MK, "model", "work", "PlBmNr_build.json")))
EYES = json.load(open(os.path.join(MK, "anim", "out", "eye_states.json")))
MR = json.load(open(os.path.join(MK, "anim", "out", "motion_rows.json")))
INST = json.load(open(os.path.join(MK, "mods-slot", "metaknight-slot", "MK_INSTALL.json")))
MODELS = INST["PlBm.dat"]["x8"]["models"]
EYE_DOBJ = BUILD["eye_dobj"]

cmd("vis_snap = function(p) local pl = gd.player(p) if not pl then return 'none' end local d = gd.dobjs(p) "
    "local c = {} for _, x in ipairs(d.costume) do c[#c+1] = string.format('%.2f,%.5f,%.5f,%.5f,%.5f', x.frame, x.su, x.sv, x.tu, x.tv) end "
    "local h = {} for _, o in ipairs(d) do h[#h+1] = o.hidden and '1' or '0' end "
    "return string.format('%s|%d|%d|%.2f|%s|%s|%s', pl.motion_name or '?', pl.action or -1, pl.anim_id or -1, pl.anim_frame_f or -1, "
    "table.concat(d.models, ','), table.concat(c, ';'), table.concat(h, '')) end")
cmd("vis_full = function(p) local d = gd.dobjs(p) local t = {} for _, o in ipairs(d) do local ts = {} for _, x in ipairs(o.tobjs) do "
    "ts[#ts+1] = string.format('%d:%d:%d:%d:%d:%d', x.id, x.src, x.flags, x.fmt, x.w, x.h) end t[#t+1] = (o.hidden and '1' or '0') .. '=' .. table.concat(ts, '/') end "
    "return table.concat(t, ';') end")

def parse(s):
    p = s.split("|")
    cost = [tuple(float(v) for v in x.split(",")) for x in p[5].split(";")] if p[5] else []
    return {"motion": p[0], "action": int(p[1]), "anim": int(p[2]), "frame": float(p[3]),
            "models": [int(x) for x in p[4].split(",")] if p[4] else [], "costume": cost, "hidden": [c == "1" for c in p[6]]}

report = collections.OrderedDict(); fails = 0
def need(ch, cond, what): ch.append((bool(cond), what))

cmd("pause"); cmd("gd.release(1)"); cmd("gd.release(2)")
for i in range(200):
    cmd("gd.input(1, {buttons='', x=0, y=0}, 600) gd.step(1)")
    if lua("gd.player(1).motion_name") == "Wait" and i > 30: break
cmd("gd.release(1)")
cmd("savestate 1"); cmd("step 1")

# ---- 1. draw list ------------------------------------------------------------------------------------
ch = []
full = lua("vis_full(1)").split(";")
dl = []
for x in full:
    hid, ts = x.split("=")
    dl.append({"hidden": hid == "1", "tobjs": [tuple(int(v) for v in t.split(":")) for t in ts.split("/")] if ts else []})
need(ch, len(dl) == 14, f"14 DObjs in the draw list ({len(dl)})")
e = dl[EYE_DOBJ]
need(ch, not e["hidden"], f"eye DObj {EYE_DOBJ} is drawn (hidden flag clear)")
need(ch, len(e["tobjs"]) == 3, f"eye DObj has 3 TObjs ({len(e['tobjs'])})")
if len(e["tobjs"]) == 3:
    need(ch, [t[1] for t in e["tobjs"]] == [4, 5, 6], f"eye layers read TEX0 / TEX1 / TEX2 ({[t[1] for t in e['tobjs']]})")
    need(ch, all(t[3] == 9 and t[4] == 256 and t[5] == 128 for t in e["tobjs"][1:]), "both eye layers are the CI8 256x128 eye texture")
    need(ch, all((t[2] >> 16) & 0xF == 1 for t in e["tobjs"][1:]), "both eye layers blend by the eye texture's alpha (COLORMAP_ALPHA_MASK)")
shine = {d["dobj"]: d for d in BUILD["dobjs"] if any("REFLECTION" in l["coord"] for l in d["layers"])}
for di, d in shine.items():
    refl = [t for t in dl[di]["tobjs"] if t[2] & 0xF == 1]
    need(ch, len(refl) == 1 and (refl[0][2] >> 16) & 0xF == 7, f"DObj {di} ({d['material']}) has a REFLECTION + COLORMAP_ADD layer in the engine")
snap = parse(lua("vis_snap(1)"))
need(ch, len(snap["costume"]) == 2, f"two costume texture-anim TObjs (the eyes): {len(snap['costume'])}")
report["draw_list"] = {"dobjs": [{"hidden": x["hidden"], "tobjs": x["tobjs"]} for x in dl], "checks": [{"ok": c, "what": w} for c, w in ch]}
ok = all(c for c, _ in ch); fails += not ok
print(f"{'OK  ' if ok else 'FAIL'} draw list"); [print(f"       {'ok ' if c else 'NO '} {w}") for c, w in ch]

# ---- 2. eyes per frame ---------------------------------------------------------------------------------
# row -> clip from the slot's PlBm.dat motion table itself (AJ offset / size -> motion_rows), as the script passes match
sys.path.insert(0, os.path.join(MK, "model", "tools")); import install_mk as IM
_w = IM.Writer(open(os.path.join(MK, "mods-slot", "metaknight-slot", "files", "PlBm.dat"), "rb").read())
_mt = _w.u32(_w.ar.public([x for x, _ in _w.ar.publics if x.startswith("ftData")][0]) + 0xC)
_by_off = {(c["offset"], c["size"]): c for c in MR["clips"] + MR["extras"]}
by_row = {}
for r in range(480):
    c = _by_off.get((_w.u32(_mt + r * 0x18 + 4), _w.u32(_mt + r * 0x18 + 8)))
    if c is not None: by_row[r] = c
def expected_state(clip, fr):
    st = 0; off = 0
    for n in clip.split("+"):
        c = EYES["clips"].get(n)
        if c is None: return None
        for ef, es in c["events"]:
            if ef + off <= fr: st = es
        off += c["frames"]
    return st
STATES = EYES["states"]
UPTAUNT = [("", 1, 0, 0), ("DUP", 1, 0, 80)]                      # stick up + taunt -> the Geno AppealHi state
PLAN = [("Wait", 150, None), ("DamageN1", 14, None), ("AttackS4Hi", 60, None), ("AttackLw4", 50, None), ("AppealSR", 70, None),
        ("AppealHi", 125, UPTAUNT)]   # (motion name, frames, input plan or None = gd.set_motion)
names = {}
for mid in range(0, 400):
    n = lua(f"gd.motion_name({mid}, 1)")
    if n and n not in names: names[n] = mid
def enter(mname, plan):
    cmd("loadstate 1"); cmd("step 1")
    if plan is None:
        cmd(f"= gd.set_motion(1, {names[mname]})"); cmd("step 1")
    else:
        for b, n_, x, y in plan:
            for _ in range(n_): cmd(f"gd.input(1, {{buttons='{b}', x={x}, y={y}}}, 600) gd.step(1)")
        cmd("gd.release(1)")
        for _ in range(3):
            if parse(lua("vis_snap(1)"))["motion"] == mname: break
            cmd("step 1")
for mname, nfr, plan in PLAN:
    ch = []; rows = []
    if plan is None and names.get(mname) is None:
        report["eyes " + mname] = {"skipped": "no motion named " + mname}; print("SKIP eyes", mname); continue
    enter(mname, plan)
    exact = near = n = 0; srt_err = 0.0; seen = set(); first_anim = None
    for k in range(nfr):
        s = parse(lua("vis_snap(1)"))
        if s["motion"] != mname: break
        c = by_row.get(s["anim"])
        if c is None: break
        exp = expected_state(c["brawl_clip"], int(round(s["frame"])))
        if exp is None: break
        got = [int(round(x[0])) for x in s["costume"]]
        n += 1; seen.add(exp)
        if all(g == exp for g in got): exact += 1
        prv = expected_state(c["brawl_clip"], int(round(s["frame"])) - 1)
        nxt = expected_state(c["brawl_clip"], int(round(s["frame"])) + 1)
        if all(g in (exp, prv, nxt) for g in got): near += 1
        for ci, (fr_, su, sv, tu, tv) in enumerate(s["costume"]):
            g = int(round(fr_))
            if 0 <= g < len(STATES):
                col = 0 if ci == 0 else 4
                srt_err = max(srt_err, abs(su - STATES[g][col]), abs(sv - STATES[g][col + 1]), abs(tu - STATES[g][col + 2]), abs(tv - STATES[g][col + 3]))
        rows.append({"frame": s["frame"], "anim": s["anim"], "expected": exp, "got": got})
        cmd("step 1")
    need(ch, n > 5, f"{mname} played ({n} frames, row {rows[0]['anim'] if rows else '-'} clip {by_row.get(rows[0]['anim'], {}).get('brawl_clip') if rows else '-'})")
    need(ch, n and near == n, f"both eyes show the Brawl eye state of the clip frame (+-1 frame) on every frame: {near}/{n} (exact {exact})")
    need(ch, srt_err < 1e-3, f"the engine applied each state's texture SRT (worst {srt_err:.2e})")
    need(ch, len(seen) > 1 or mname == "Wait", f"the clip changes the eye state ({sorted(seen)[:8]})")
    report["eyes " + mname] = {"frames": rows, "checks": [{"ok": c, "what": w} for c, w in ch]}
    ok = all(c for c, _ in ch); fails += not ok
    print(f"{'OK  ' if ok else 'FAIL'} eyes {mname}"); [print(f"       {'ok ' if c else 'NO '} {w}") for c, w in ch]

# ---- 3. model parts: hidden flags follow the part table ------------------------------------------------
ch = []; bad = 0; nchk = 0; states0 = set()
seq3 = []
for mname, nfr, plan in (("Wait", 5, None), ("AppealHi", 125, UPTAUNT), ("Guard", 20, None), ("JumpAerialF", 20, None)):
    if plan is None and names.get(mname) is None: continue
    enter(mname, plan)
    for k in range(nfr):
        s = parse(lua("vis_snap(1)"))
        want = {}
        for m, st in enumerate(s["models"]):
            if m < len(MODELS):
                for j, lst in enumerate(MODELS[m]):
                    for d in lst: want[d] = want.get(d, True) and (j != st)
        for d, hid in want.items():
            nchk += 1
            if s["hidden"][d] != hid: bad += 1
        if s["models"]: states0.add(s["models"][0])
        if mname == "AppealHi": seq3.append((s["motion"], s["frame"], tuple(s["models"])))
        cmd("step 1")
need(ch, nchk > 100 and bad == 0, f"every part-table DObj's hidden flag = the model state the engine holds ({nchk} checks, {bad} wrong)")
ah = [x for x in seq3 if x[0] == "AppealHi"]
none_fr = [x[1] for x in ah if x[2] and x[2][0] == 3]
need(ch, none_fr and 20 <= min(none_fr) <= 23, f"up taunt: no cape (cape model state 3) from Brawl's frame 21 ({min(none_fr) if none_fr else '-'}..{max(none_fr) if none_fr else '-'})")
need(ch, any(x[2][1] == 1 for x in ah if len(x[2]) > 1), "up taunt: the mantle ball (body model state 1) shows while the cape is gone")
report["model_parts"] = {"cape_states_seen": sorted(states0), "checks": [{"ok": c, "what": w} for c, w in ch if w]}
ok = all(c for c, w in ch if w); fails += not ok
print(f"{'OK  ' if ok else 'FAIL'} model parts (cape states seen {sorted(states0)})"); [print(f"       {'ok ' if c else 'NO '} {w}") for c, w in ch if w]

cmd("loadstate 1"); cmd("step 1"); cmd("resume")
os.makedirs(os.path.dirname(a.report), exist_ok=True)
json.dump(report, open(a.report, "w"), indent=1)
print("FAILS", fails)
