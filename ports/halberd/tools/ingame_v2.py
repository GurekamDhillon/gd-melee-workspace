"""Drive Meta Knight's Geno v2 / v3 moves on a running Geno exe (console socket) and check what the engine does.

    python tools/ingame_v2.py <console-port> [--only glide,drill] [--changes mods-slot/metaknight-slot/CHANGES.json]

Needs the Geno exe with geno.json v2 (MELEE_MODS_DIR -> metaknight-slot + geno-lab), a VS/training match with MK on
port 1 and a level-0 CPU on port 2. Every plan starts from savestate 1 (MK standing, taken at start). Per frame it
records motion / anim / frame / position / velocity / hitboxes; each plan has checks (states reached, the glide
pose follows the angle, the tornado rises on B taps, the drill climbs when steered up, hitboxes = CHANGES.json by
the row the state plays). v3 plans ("v3 ..."): Shuttle Loop (both facings, ground / air, the loop path, glide / landing /
helpless ending, ledge grab), Drill Rush (drills through a hit for its whole clip, ground / air ends) and Dimensional
Cape (hidden / intangible vanish, stick steering, N / F / B slash and the plain reappear); every plan also checks that no
Kirby special motion (Final Cutter, hammer, stone, inhale: motions 341-398) is ever entered. Report: analysis/ingame_v2.json."""
import sys, os, json, socket, argparse, collections
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument("port", type=int)
ap.add_argument("--changes", default=os.path.join(MK, "mods-slot", "metaknight-slot", "CHANGES.json"))
ap.add_argument("--only", default=None)
ap.add_argument("--report", default=os.path.join(MK, "analysis", "ingame_v2.json"))
ap.add_argument("--keep-paused", action="store_true")
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

cmd("v2_snap = function(p) local pl = gd.player(p) if not pl then return 'none' end local t = {} "
    "for _, h in ipairs(gd.hitboxes(p) or {}) do t[#t+1] = string.format('%d:%d:%d:%d:%d:%d', h.id, math.floor(h.damage + 0.5), h.angle, h.kbg, h.bkb, h.wbk) end "
    "return string.format('%s|%d|%d|%.2f|%.2f|%.2f|%.3f|%.3f|%d|%s|%.1f|%s|%d|%s', pl.motion_name or '?', pl.action or -1, pl.anim_id or -1, "
    "pl.anim_frame_f or -1, pl.x, pl.y, pl.vx, pl.vy, pl.airborne and 1 or 0, pl.anim_name or '?', pl.facing or 0, table.concat(t, ' '), "
    "pl.hidden and 1 or 0, pl.body_state or '?') end")
C = json.load(open(a.changes))
by_row = collections.defaultdict(set)
for m in C["moves"]:
    for h in m.get("written_hitboxes", []): by_row[m["melee_row"]].add((h["damage"], h["angle"], h["kbg"], h["bkb"], h["wdsk"]))
STATES = {s["name"]: s for s in C["geno"]["states"]}
# KEEP_FRAME air -> ground switches keep the air row's live hitboxes (Melee's mid-move transition): accept them there
for air, gnd in (("DrillEnd", "DrillEndGround"), ("TornadoEnd", "TornadoEndGround")):
    by_row[STATES[gnd]["subaction"]] |= by_row[STATES[air]["subaction"]]

def seq(*items): return list(items)
JUMP = [("Y", 1, 0, 0), ("none", 8, 0, 0)]                  # ground jump, rising
GLIDE = JUMP + [("Y", 40, 0, 0)]                             # air jump held 40 frames: GlideStart at 16, Glide after its clip
PLANS = collections.OrderedDict([
    ("glide: entry + neutral", seq(*GLIDE, ("none", 60, 0, 0))),
    ("glide: pitch up -> stall", seq(*GLIDE, ("none", 110, 0, 110))),
    ("glide: pitch down (dive)", seq(*GLIDE, ("none", 40, 0, -110), ("none", 20, 0, 0))),
    ("glide: exit on B", seq(*GLIDE, ("none", 10, 0, 0), ("B", 1, 0, 0), ("none", 40, 0, 0))),
    ("glide: exit on shield", seq(*GLIDE, ("none", 10, 0, 0), ("R", 1, 0, 0), ("none", 40, 0, 0))),
    ("glide: attack", seq(*GLIDE, ("none", 6, 0, 0), ("A", 1, 0, 0), ("none", 60, 0, 0))),
    ("glide: landing", seq(*GLIDE, ("none", 5, 0, -110), ("none", 150, 0, -40))),
    ("up_b air -> glide", seq(*JUMP, ("none", 6, 0, 0), ("B", 1, 0, 127), ("none", 140, 0, 0))),
    ("up_b ground", seq(("B", 1, 0, 127), ("none", 150, 0, 0))),
    ("tornado: ground, no taps", seq(("B", 1, 0, 0), ("none", 140, 0, 0))),
    ("tornado: B taps rise", seq(("B", 1, 0, 0), *[x for _ in range(10) for x in (("none", 6, 0, 0), ("B", 2, 0, 0))], ("none", 80, 0, 0))),
    ("tornado: air, drift", seq(*JUMP, ("B", 1, 0, 0), ("none", 30, 90, 0), ("none", 80, 0, 0))),
    ("drill: ground straight", seq(("B", 1, 127, 0), ("none", 110, 0, 0))),
    ("drill: air steer up", seq(*JUMP, ("B", 1, 127, 0), ("none", 22, 0, 0), ("none", 30, 0, 110), ("none", 60, 0, 0))),
    ("drill: air steer down", seq(*JUMP, ("Y", 1, 0, 0), ("none", 10, 0, 0), ("B", 1, 127, 0), ("none", 22, 0, 0), ("none", 25, 0, -110), ("none", 60, 0, 0))),
    ("taunt: down (Melee)", seq(("DUP", 1, 0, 0), ("none", 125, 0, 0))),
    ("taunt: up (stick up)", seq(("none", 1, 0, 0), ("DUP", 1, 0, 80), ("none", 125, 0, 0))),
    ("taunt: side (stick fwd)", seq(("DUP", 1, 90, 0), ("none", 125, 0, 0))),
])
TURN = [("none", 1, -127, 0), ("none", 20, 0, 0)]                          # face left (standing turn), settle in Wait
DOWNB = ("B", 1, 0, -127)
PLANS.update([
    ("v3 up_b ground (right)", seq(("B", 1, 0, 127), ("none", 150, 0, 0))),
    ("v3 up_b ground (left)", seq(*TURN, ("B", 1, 0, 127), ("none", 150, 0, 0))),
    ("v3 up_b air (right)", seq(*JUMP, ("none", 6, 0, 0), ("B", 1, 0, 127), ("none", 60, 0, 0))),
    ("v3 up_b air (left)", seq(*TURN, *JUMP, ("none", 6, 0, 0), ("B", 1, 0, 127), ("none", 60, 0, 0))),
    ("v3 up_b glide ends helpless", seq(("B", 1, 0, 127), ("none", 36, 0, 0), ("R", 1, 0, 0), ("none", 60, 0, 0))),
    ("v3 drill air end helpless", seq(*JUMP, ("Y", 1, 0, 0), ("none", 4, 0, 0), ("B", 1, 127, 0), ("none", 22, 0, 0), ("none", 45, 0, 40), ("none", 60, 0, 0))),
    ("v3 cape ground, B held (N)", seq(DOWNB, ("B", 30, 0, 0), ("none", 80, 0, 0))),
    ("v3 cape ground, nothing held (end)", seq(DOWNB, ("none", 100, 0, 0))),
    ("v3 cape air, B + stick forward (B)", seq(*JUMP, ("Y", 1, 0, 0), ("none", 4, 0, 0), DOWNB, ("B", 30, 127, 0), ("none", 70, 0, 0))),
    ("v3 cape air, A + stick back (F)", seq(*JUMP, ("Y", 1, 0, 0), ("none", 4, 0, 0), DOWNB, ("A", 30, -127, 0), ("none", 70, 0, 0))),
    ("v3 cape air, steer up (end)", seq(*JUMP, ("none", 4, 0, 0), DOWNB, ("none", 30, 0, 127), ("none", 70, 0, 0))),
])
if a.only: PLANS = collections.OrderedDict((k, v) for k, v in PLANS.items() if any(o in k for o in a.only.split(",")))

cmd("pause"); cmd("gd.release(1)"); cmd("gd.release(2)")
for i in range(120):
    cmd("gd.input(1, {buttons='', x=0, y=0}, 600) gd.step(1)")
    if lua("gd.player(1).motion_name") == "Wait" and i > 30: break
cmd("gd.release(1)")
st = lua("v2_snap(1)"); print("start:", st)
if not st.startswith("Wait|"): raise SystemExit("MK is not standing (Wait) - is someone else driving port 1? start: " + st)
cmd("savestate 1"); cmd("step 1")
# ledge plans: run off FD's nearer edge (x +-85.6) facing away from the stage, fall a while, Shuttle Loop (air)
x_start = float(st.split("|")[4]); edge_dir = 1 if x_start >= 0 else -1
run_n = int((85.6 - abs(x_start)) / 1.8) + 14
# drill through a hit: walk toward the level-0 CPU, then Drill Rush into it
fox_x = float(lua("gd.player(2).x")); gap = fox_x - x_start; tdir = 1 if gap > 0 else -1
k = "v3 drill through a hit"
if a.only is None or any(o in k for o in a.only.split(",")):
    PLANS[k] = seq(("none", max(int((abs(gap) - 30) / 1.8), 0), 127 * tdir, 0), ("none", 30, 0, 0), ("B", 1, 127 * tdir, 0), ("none", 110, 0, 0))
for fall in (6, 14, 22, 30):
    k = f"v3 up_b ledge (fall {fall})"
    if a.only is None or any(o in k for o in a.only.split(",")):
        PLANS[k] = seq(("none", run_n, 127 * edge_dir, 0), ("none", fall, 0, 0), ("B", 1, 0, 127), ("none", 100, 0, 0))

SNAME = {0x400 + i: s["name"] for i, s in enumerate(C["geno"]["states"])}
def parse(s):
    p = s.split("|")
    return {"motion": SNAME.get(int(p[1]), p[0]), "action": int(p[1]), "anim": int(p[2]), "frame": float(p[3]), "x": float(p[4]), "y": float(p[5]),
            "vx": float(p[6]), "vy": float(p[7]), "air": p[8] == "1", "anim_name": p[9], "facing": float(p[10]),
            "hb": [tuple(int(v) for v in h.split(":")) for h in p[11].split()] if len(p) > 11 and p[11] else [],
            "hidden": len(p) > 12 and p[12] == "1", "body": p[13] if len(p) > 13 else "?"}

report = collections.OrderedDict(); fails = 0
for name, plan in PLANS.items():
    cmd("loadstate 1"); cmd("step 1")
    frames = []
    for buttons, n, x, y in plan:
        for i in range(n):
            b = "" if buttons == "none" else buttons
            cmd(f"gd.input(1, {{buttons='{b}', x={x}, y={y}}}, 600) gd.step(1)")
            frames.append(parse(lua("v2_snap(1)")))
    cmd("gd.release(1)")
    motions = []
    for fr in frames:
        if not motions or motions[-1] != fr["motion"]: motions.append(fr["motion"])
    # hitboxes by the row (anim id) that created them, against CHANGES.json
    seen = collections.defaultdict(set)
    for fr in frames:
        for h in fr["hb"]: seen[fr["anim"]].add(h[1:])
    hb_checks = []
    for row, got in seen.items():
        exp = by_row.get(row)
        if not exp: continue
        def match(g, e): return g[1:] == e[1:] and (g[0] == e[0] or 0.5 * e[0] <= g[0] < e[0])
        unexp = sorted(g for g in got if not any(match(g, e) for e in exp))
        hb_checks.append({"row": row, "expected": len(exp), "seen": sum(1 for e in exp if any(match(g, e) for g in got)), "unexpected": unexp})
    ch = []
    def need(cond, what): ch.append((bool(cond), what))
    ms = set(motions)
    if name.startswith("glide"):
        need({"GlideStart", "Glide"} <= ms, "GlideStart -> Glide")
        g = [fr for fr in frames if fr["motion"] == "Glide"]
        # v3: the Glide starts its clip at pose_center - angle, so the ENTRY frame is posed too (was clip frame 0, nose up)
        if "neutral" in name and g: need(max(abs(fr["frame"] - 90) for fr in g[0:20]) < 3, f"neutral glide poses level from its entry frame (entry frame {g[0]['frame']:.0f})")
        if "pitch up" in name:
            need(g and min(fr["frame"] for fr in g) < 60, "stick up: pose nose-up (frame < 60)")
            need("GlideEnd" in ms, "climbing stalls -> GlideEnd")
        if "dive" in name:
            need(g and max(fr["frame"] for fr in g) > 120, "stick down: pose nose-down (frame > 120)")
            sp = [(fr["vx"] ** 2 + fr["vy"] ** 2) ** 0.5 for fr in g]
            need(sp and max(sp) > sp[0] + 0.1, f"diving gains speed ({sp[0]:.2f} -> {max(sp):.2f})" if sp else "diving gains speed")
        if "exit" in name: need("GlideEnd" in ms, "button -> GlideEnd")
        if "attack" in name:
            need("GlideAttack" in ms, "A -> GlideAttack")
            need(any(r["row"] == STATES["GlideAttack"]["subaction"] and r["seen"] for r in hb_checks), "glide attack hitboxes (12%)")
        if "landing" in name: need("GlideLanding" in ms, "landing -> GlideLanding")
    if name.startswith("up_b air"): need("Glide" in ms, "Shuttle Loop ends in Glide (air)")
    if name.startswith("up_b ground"): need(ms & {"Glide", "FallSpecial", "LandingFallSpecial"}, "ground Shuttle Loop ends in Glide / FallSpecial")
    if name.startswith("tornado"):
        need("Tornado" in ms, "B -> Tornado")
        need(ms & {"TornadoEnd", "TornadoEndGround"}, "tornado ends -> TornadoEnd(Ground)")
        t = [fr for fr in frames if fr["motion"] == "Tornado"]
        if "B taps" in name: need(t and max(fr["y"] for fr in t) > t[0]["y"] + 8, f"B taps lift MK (rise {max(fr['y'] for fr in t) - t[0]['y']:.1f})" if t else "B taps lift")
        if "drift" in name: need(t and t[-1]["x"] - t[0]["x"] > 5, f"stick drifts the tornado ({t[-1]['x'] - t[0]['x']:.1f})" if t else "drift")
        need(any(r["row"] == STATES["Tornado"]["subaction"] and r["seen"] for r in hb_checks), "tornado hitboxes")
    if name.startswith("drill"):
        need({"DrillStart", "Drill"} <= ms or {"DrillStartAir", "Drill"} <= ms, "side-B -> DrillStart -> Drill")
        need(ms & {"DrillEnd", "DrillEndGround"}, "-> DrillEnd(Ground)")
        d = [fr for fr in frames if fr["motion"] == "Drill"]
        if d:
            sp = sorted(abs(fr["vx"]) + abs(fr["vy"]) for fr in d)
            need(sp[len(sp) // 2] > 0.8, f"rush speed from the clip's TransN (median |v| {sp[len(sp) // 2]:.2f})")
        if "up" in name: need(d and max(fr["vy"] for fr in d) > 0.8, "stick up: the drill climbs")
        if "down" in name: need(d and min(fr["vy"] for fr in d) < -0.8, "stick down: the drill dives")
        need(any(r["row"] == STATES["Drill"]["subaction"] and r["seen"] for r in hb_checks), "drill hitboxes")
    # ---- v3
    kb = sorted({fr["motion"] for fr in frames if "Special" in fr["motion"] and fr["motion"] not in ("FallSpecial", "LandingFallSpecial")})
    need(not kb, "no Kirby special motion entered" + (f" (got {kb})" if kb else ""))
    if name.startswith("v3 up_b"):
        left = "(left)" in name
        u = [fr for fr in frames if fr["motion"] in ("UpB", "UpBLoop")]
        need(u, "Up-B enters the root-motion states (UpB / UpBLoop)")
        if u and "ledge" not in name:
            x0, y0 = u[0]["x"], u[0]["y"]
            top = max(u, key=lambda fr: fr["y"])
            back = [(fr["x"] - x0) * (1 if left else -1) for fr in u]          # + = behind MK's facing
            need(top["y"] - y0 > 25, f"the loop rises (+{top['y'] - y0:.1f})")
            need(max(back) > 5, f"the loop travels back over the top ({max(back):.1f} behind the start)")
            need(all((fr["facing"] < 0) == left for fr in u), "facing kept through the loop")
        if "ground" in name or "air" in name: need("Glide" in ms, "ends in Glide (in the air)")
        if "helpless" in name: need({"GlideEnd", "FallSpecial"} <= ms, "the up-B glide ends helpless (GlideEnd -> FallSpecial)")
        if "ledge" in name: report.setdefault("_ledge", {})[name] = sorted(ms & {"CliffCatch", "CliffWait", "UpBLand", "Glide", "FallSpecial"})
    if name.startswith("v3 drill"):
        d = [fr for fr in frames if fr["motion"] == "Drill"]
        if "hit" in name:
            p2 = float(lua("gd.player(2).percent"))
            need(p2 >= 3, f"the rush connected with the CPU several times (CPU at {p2:.0f}%)")
            need(len(d) >= 45, f"a hit does not end the rush ({len(d)} frames in Drill, clip 45 + hitlag)")
            need(ms & {"DrillEndGround", "DrillEnd"}, "-> the end")
        if "air end" in name: need({"DrillEnd", "FallSpecial"} <= ms, "air end -> FallSpecial (helpless)")
    if name.startswith("v3 cape"):
        st0 = [fr for fr in frames if fr["motion"] in ("CapeStart", "CapeStartAir")]
        need(st0, "down-B -> CapeStart(Air)")
        hid = [i for i, fr in enumerate(frames) if fr["hidden"]]
        need(len(hid) >= 12, f"MK hidden while vanished ({len(hid)} frames)")
        need(any(fr["body"] == "intangible" for fr in frames if fr["hidden"]), "intangible while vanished")
        need(not frames[-1]["hidden"], "visible again after the move")
        want = ("CapeN" if "(N)" in name else "CapeBAir" if "(B)" in name else "CapeFAir" if "(F)" in name else
                "CapeEndAir" if "air" in name else "CapeEnd")
        need(want in ms, f"reappears in {want}")
        if want.startswith("Cape") and "End" not in want:
            need(any(r["row"] == STATES[want]["subaction"] and r["seen"] for r in hb_checks), f"{want} slash hitboxes (14%)")
        if "air" in name: need("FallSpecial" in ms, "air cape ends helpless (FallSpecial)")
        else: need(ms & {"Wait"} and frames[-1]["motion"] in ("Wait", "Wait3"), "ground cape ends in Wait")
        if st0 and hid:
            v0 = frames[hid[0]]; v1 = frames[hid[-1]]
            if "steer up" in name: need(v1["y"] - v0["y"] > 15, f"stick up steers the vanish up ({v1['y'] - v0['y']:.1f})")
            if "forward" in name: need(v1["x"] - v0["x"] > 15, f"stick forward steers the vanish forward ({v1['x'] - v0['x']:.1f})")
            if "back" in name: need(v0["x"] - v1["x"] > 15, f"stick back steers the vanish back ({v0['x'] - v1['x']:.1f})")
    if name.startswith("taunt: up"): need("AppealHi" in ms, "stick up + taunt -> AppealHi")
    if name.startswith("taunt: side"): need("AppealS" in ms, "stick sideways + taunt -> AppealS")
    if name.startswith("taunt: down"): need(not ms & {"AppealHi", "AppealS"}, "plain taunt stays Melee's (AppealLw clip)")
    alive = lua("gd.frame()") != ""
    ok = alive and all(c for c, _ in ch) and not any(r["unexpected"] for r in hb_checks)
    fails += not ok
    report[name] = {"ok": ok, "motions": motions, "checks": [{"ok": c, "what": w} for c, w in ch], "hitboxes": hb_checks, "frames": frames}
    print(f"{'OK  ' if ok else 'FAIL'} {name:28s} {' > '.join(motions)[:150]}")
    for c, w in ch:
        if not c or os.environ.get("V2_VERBOSE"): print(f"       {'ok ' if c else 'NO '} {w}")
    for r in hb_checks:
        if r["unexpected"]: print(f"       row {r['row']}: UNEXPECTED hitboxes {r['unexpected'][:4]}")
cmd("loadstate 1"); cmd("step 1")
if not a.keep_paused: cmd("resume")
if "_ledge" in report:
    got = [k for k, v in report["_ledge"].items() if "CliffCatch" in v]
    print("ledge runs:", report["_ledge"], "->", "grabbed in " + ", ".join(got) if got else "NO LEDGE GRAB")
    if not got: fails += 1
json.dump(report, open(a.report, "w"), indent=1)
print("FAILS", fails)
