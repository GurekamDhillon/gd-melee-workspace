"""Numeric check of Meta Knight's results-screen poses (no screenshots): win a 1-stock VS match against a level-0 Fox, then
log what MK's results fighter plays.

    python tools/ingame_results.py <console-port> [--hold B|Y|X] [--report analysis/ingame_results.json]

Needs a VS match: MELEE_SCENE="mode=vs;p1=mexext:51/stocks1;p2=fox/cpu0/stocks1;stage=fd" (the Lab for gd.dobjs).
Fox is put at 999 %, MK walks to him and forward-smashes him off. On the results screen the winner's pose is picked from
the pad (gm_1798.c: button 0x200 -> variant 0 = Win1, 0x800 -> 1 = Win2, 0x400 -> 2 = Win3, else random), so --hold
keeps that button down through the match end. Per results frame: MK's motion / animation (demo row) / frame, the
model-part states and the two eye TObjs' frames (gd.dobjs). Checks: the results fighter is MK (105 joints), it plays
MK's demo rows (anim/out/demo_rows.json: Win1 -> Win1Wait etc.), and the part states / eye states follow
vis_events.json 'demo' and eye_states.json at the logged frames."""
import sys, os, json, socket, argparse, time
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument("port", type=int)
ap.add_argument("--hold", default="B")
ap.add_argument("--report", default=os.path.join(MK, "analysis", "ingame_results.json"))
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

DEMO = json.load(open(os.path.join(MK, "anim", "out", "demo_rows.json")))["rows"]
VIS = {x["index"]: x for x in json.load(open(os.path.join(MK, "anim", "vis_events.json")))["demo"]}
EYES = json.load(open(os.path.join(MK, "anim", "out", "eye_states.json")))["clips"]
cmd("res_snap = function(p) local pl = gd.player(p) if not pl then return 'none' end local d = gd.dobjs(p) or {models={}, costume={}} "
    "local c = {} for _, x in ipairs(d.costume) do c[#c+1] = string.format('%.1f', x.frame) end "
    "return string.format('%s|%d|%d|%.2f|%s|%s|%d|%s|%.2f|%.2f', pl.motion_name or '?', pl.action or -1, pl.anim_id or -1, pl.anim_frame_f or -1, "
    "table.concat(d.models, ','), table.concat(c, ','), #(gd.joints(p) or {}), gd.scene().name or '?', pl.x or 0, pl.percent or -1) end")
def snap(p):
    s = lua(f"res_snap({p})")
    if s == "none" or "|" not in s: return None
    q = s.split("|")
    return {"motion": q[0], "action": int(q[1]), "anim": int(q[2]), "frame": float(q[3]),
            "models": [int(x) for x in q[4].split(",")] if q[4] else [], "eyes": [float(x) for x in q[5].split(",")] if q[5] else [],
            "joints": int(q[6]), "scene": q[7], "x": float(q[8])}

log = {"match": [], "results": []}
cmd("pause")
for i in range(600):                                   # to the match (the GO countdown ends)
    s1 = snap(1)
    if s1 and s1["motion"] == "Wait" and i > 60: break
    cmd("step 1")
cmd("gd.set_percent(2, 999)")
hold = a.hold
for i in range(900):                                   # walk right to Fox, forward-smash
    s1, s2 = snap(1), snap(2)
    if s2 is None or s1 is None or s1["scene"] != "GS_VS" and i > 5: break
    dx = s2["x"] - s1["x"]
    if abs(dx) > 14: cmd(f"gd.input(1, {{buttons='{hold}', x={127 if dx > 0 else -127}, y=0}}, 600) gd.step(1)")
    elif s1["motion"] in ("Wait", "Walk", "WalkSlow", "WalkMiddle", "WalkFast", "Dash", "Run", "RunBrake", "Turn"):
        cmd(f"gd.input(1, {{buttons='A {hold}', x={127 if dx > 0 else -127}, y=0}}, 600) gd.step(1)")
    else:
        cmd(f"gd.input(1, {{buttons='{hold}', x=0, y=0}}, 600) gd.step(1)")
    if i % 10 == 0: log["match"].append({"i": i, "mk": s1, "fox": s2})
    if lua("gd.scene().name") != "GS_VS": break
# the match ends -> (GAME! / results): run in real time with the button held, poll MK's results fighter
cmd("resume")
t0 = time.time(); seen_results = False; last_hold = 0
while time.time() - t0 < 120:
    if time.time() - last_hold > 5: cmd(f"gd.input(1, {{buttons='{hold}', x=0, y=0}}, 600)"); last_hold = time.time()
    sc = lua("gd.scene().name")
    if sc == "GS_RESULTS":
        seen_results = True
        sp = {p: snap(p) for p in range(1, 5)}
        log["results"].append({"t": round(time.time() - t0, 3), "scene": sc, "players": sp})
        if len(log["results"]) > 600: break
    else:
        time.sleep(0.05)
        if seen_results: break
cmd("gd.release(1)"); cmd("resume")

# ---- checks --------------------------------------------------------------------------------------------
checks = []
def need(c, w): checks.append((bool(c), w))
need(seen_results, "reached the results screen")
mk = [(r["t"], p, s) for r in log["results"] for p, s in r["players"].items() if s and s["joints"] == 105]
need(mk, f"MK's results fighter present (105 joints): {len(mk)} frames")
anims = []
for _, p, s in mk:
    if not anims or anims[-1] != (s["motion"], s["anim"]): anims.append((s["motion"], s["anim"]))
log["mk_motion_sequence"] = anims
demo_by_idx = {d["index"]: d for d in DEMO}
print("MK results motions (motion name, animation row):", anims)
# the part states / eyes of each logged frame against the demo row's plan (row = anim id if it is a demo index)
bad_vis = bad_eye = n = 0
for _, p, s in mk:
    d = demo_by_idx.get(s["anim"])
    if d is None: continue
    n += 1; fr = int(round(s["frame"]))
    want = {}
    for e in VIS.get(d["index"], {}).get("melee_modelvis", []):
        if e["frame"] <= fr: want[e["index"]] = e["value"]
    if s["models"] and any(s["models"][i] != v for i, v in want.items() if i < len(s["models"])): bad_vis += 1
    st = 0
    for ef, es in EYES.get(d["brawl_clip"], {}).get("events", []):
        if ef <= fr: st = es
    if s["eyes"] and any(abs(x - st) > 0.5 for x in s["eyes"]):
        prv = 0
        for ef, es in EYES.get(d["brawl_clip"], {}).get("events", []):
            if ef <= fr - 1: prv = es
        if any(abs(x - prv) > 0.5 for x in s["eyes"]): bad_eye += 1
need(n > 30, f"MK plays demo rows of MK's results table ({n} frames, rows {sorted({s['anim'] for _, _, s in mk})})")
need(n and bad_vis == 0, f"model-part states follow the Brawl result subaction ({bad_vis} of {n} frames off)")
need(n and bad_eye == 0, f"eye states follow the Brawl result eye clip ({bad_eye} of {n} frames off)")
for c, w in checks: print(("ok " if c else "NO ") + w)
log["checks"] = [{"ok": c, "what": w} for c, w in checks]
os.makedirs(os.path.dirname(a.report), exist_ok=True)
json.dump(log, open(a.report, "w"), indent=1)
print("FAILS", sum(1 for c, _ in checks if not c))
