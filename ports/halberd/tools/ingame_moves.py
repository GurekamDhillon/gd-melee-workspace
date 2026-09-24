"""Drive Meta Knight (port 1) through every normal, grab/throw and special on a running game (console socket) and
compare the hitboxes the ENGINE reports (Geno Lab gd.hitboxes) with what the build wrote (CHANGES.json).

    python tools/ingame_moves.py <console-port> [--changes build/stage/CHANGES.json] [--only fair,bair]

Needs the Geno exe (gd.lab_api), a training match with MK on port 1 and a level-0 CPU on port 2, and the game
left paused between steps (the script pauses it). Every move starts from savestate 1 (taken at start: MK standing).
Per frame it records the motion name and the active hitboxes; a move passes when every hitbox the build wrote for
the rows the move visits shows up in the engine with the same damage / angle / kbg / bkb / set knockback, and the
game is still answering afterwards. Report: analysis/ingame_moves.json."""
import sys, os, json, socket, argparse, time, collections
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument("port", type=int)
ap.add_argument("--changes", default=os.path.join(MK, "build", "stage", "CHANGES.json"))
ap.add_argument("--only", default=None)
ap.add_argument("--report", default=os.path.join(MK, "analysis", "ingame_moves.json"))
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

cmd("hb_snap = function(p) local t = {} for _, h in ipairs(gd.hitboxes(p) or {}) do "
    "t[#t+1] = string.format('%d:%d:%d:%d:%d:%d:%.2f', h.id, math.floor(h.damage + 0.5), h.angle, h.kbg, h.bkb, h.wbk, h.radius) end "
    "local pl = gd.player(p) return (pl and (pl.motion_name or '?') or 'none') .. '|' .. (pl and pl.action_frame or -1) .. '|' .. table.concat(t, ' ') .. '|' .. (pl and pl.facing or 0) end")
C = json.load(open(a.changes))
by_row = collections.defaultdict(list)
for m in C["moves"]:
    for h in m.get("written_hitboxes", []): by_row[m["melee_name"]].append((m["move"], h))
# motion name (engine) -> submotion row name (CHANGES) where they differ
ROW_OF = {"SpecialAirHi4": "SpecialAirHiEnd", "SpecialAirNEnd": "SpecialNEnd", "Attack100Loop": "Attack100Loop", "SpecialAirHi1": "SpecialAirHi1"}

# input plans: list of (buttons, frames, x, y); "step N" = neutral for N frames. Stick -127..127.
def seq(*items): return list(items)
AIR = [("Y", 1, 0, 0), ("none", 7, 0, 0)]
RUN = [("approach", 11, 0, 0)]
NEAR = [("approach", 14, 0, 0)]
PLANS = collections.OrderedDict([
    ("jab (tap)", seq(("A", 2, 0, 0), ("none", 70, 0, 0))),
    ("jab (mash)", seq(*[x for _ in range(12) for x in (("A", 2, 0, 0), ("none", 2, 0, 0))], ("none", 40, 0, 0))),
    ("dash_attack", seq(("none", 12, 127, 0), ("A", 1, 127, 0), ("none", 60, 0, 0))),
    ("ftilt", seq(("A", 1, 50, 0), ("none", 45, 0, 0))),
    ("utilt", seq(("A", 1, 0, 45), ("none", 45, 0, 0))),
    ("dtilt", seq(("none", 3, 0, -50), ("A", 1, 0, -50), ("none", 45, 0, 0))),
    ("fsmash", seq(("A", 1, 127, 0), ("none", 60, 0, 0))),
    ("usmash", seq(("A", 1, 0, 127), ("none", 60, 0, 0))),
    ("dsmash", seq(("A", 1, 0, -127), ("none", 60, 0, 0))),
    ("nair", seq(*AIR, ("A", 1, 0, 0), ("none", 60, 0, 0))),
    ("fair", seq(*AIR, ("A", 1, 127, 0), ("none", 60, 0, 0))),
    ("bair", seq(*AIR, ("A", 1, -127, 0), ("none", 60, 0, 0))),
    ("uair", seq(*AIR, ("A", 1, 0, 127), ("none", 60, 0, 0))),
    ("dair", seq(*AIR, ("A", 1, 0, -127), ("none", 60, 0, 0))),
    ("grab+pummel+fthrow", seq(*RUN, ("none", 4, 0, 0), ("Z", 1, 0, 0), ("none", 14, 0, 0), ("A", 1, 0, 0), ("none", 30, 0, 0), ("none", 2, 127, 0), ("none", 80, 0, 0))),
    ("grab+bthrow", seq(*RUN, ("none", 4, 0, 0), ("Z", 1, 0, 0), ("none", 14, 0, 0), ("none", 2, -127, 0), ("none", 80, 0, 0))),
    ("grab+uthrow", seq(*RUN, ("none", 4, 0, 0), ("Z", 1, 0, 0), ("none", 14, 0, 0), ("none", 2, 0, 127), ("none", 100, 0, 0))),
    ("grab+dthrow", seq(*RUN, ("none", 4, 0, 0), ("Z", 1, 0, 0), ("none", 14, 0, 0), ("none", 2, 0, -127), ("none", 100, 0, 0))),
    ("dash_grab", seq(("none", 12, 127, 0), ("Z", 1, 127, 0), ("none", 45, 0, 0))),
    ("neutral_b (hold)", seq(("B", 50, 0, 0), ("none", 45, 0, 0))),
    ("neutral_b air", seq(*AIR, ("B", 45, 0, 0), ("none", 60, 0, 0))),
    ("side_b", seq(("B", 1, 127, 0), ("none", 80, 0, 0))),
    ("side_b air", seq(*AIR, ("Y", 1, 0, 0), ("none", 8, 0, 0), ("B", 1, 127, 0), ("none", 100, 0, 0))),
    ("up_b", seq(("B", 1, 0, 127), ("none", 150, 0, 0))),
    ("up_b air", seq(*AIR, ("B", 1, 0, 127), ("none", 150, 0, 0))),
    ("down_b", seq(("B", 1, 0, -127), ("none", 110, 0, 0))),
    ("down_b air", seq(*AIR, ("B", 1, 0, -127), ("none", 120, 0, 0))),
    ("near: jab", seq(*NEAR, ("A", 2, 0, 0), ("none", 60, 0, 0))),
    ("near: ftilt", seq(*NEAR, ("A", 1, 50, 0), ("none", 40, 0, 0))),
    ("near: dtilt", seq(*NEAR, ("none", 3, 0, -50), ("A", 1, 0, -50), ("none", 40, 0, 0))),
    ("near: fsmash", seq(*NEAR, ("A", 1, 127, 0), ("none", 60, 0, 0))),
    ("near: usmash", seq(*NEAR, ("A", 1, 0, 127), ("none", 60, 0, 0))),
    ("near: dsmash", seq(*NEAR, ("A", 1, 0, -127), ("none", 60, 0, 0))),
    ("near: neutral_b", seq(*NEAR, ("B", 40, 0, 0), ("none", 45, 0, 0))),
    ("near: side_b", seq(*NEAR, ("B", 1, 127, 0), ("none", 70, 0, 0))),
    ("near: up_b", seq(*NEAR, ("B", 1, 0, 127), ("none", 120, 0, 0))),
    ("near: down_b", seq(*NEAR, ("B", 1, 0, -127), ("none", 90, 0, 0))),
    ("ftilt chain (A A A)", seq(("A", 1, 50, 0), ("none", 7, 0, 0), ("A", 1, 0, 0), ("none", 8, 0, 0), ("A", 1, 0, 0), ("none", 45, 0, 0))),
    ("near: ftilt chain", seq(*NEAR, ("A", 1, 50, 0), ("none", 7, 0, 0), ("A", 1, 0, 0), ("none", 8, 0, 0), ("A", 1, 0, 0), ("none", 45, 0, 0))),
    ("6 jumps", seq(*[x for _ in range(6) for x in (("Y", 2, 0, 0), ("none", 22, 0, 0))], ("none", 150, 0, 0))),
])
if a.only: PLANS = collections.OrderedDict((k, v) for k, v in PLANS.items() if any(o in k for o in a.only.split(",")))
cmd("pause"); cmd("gd.release(1)"); cmd("gd.release(2)")
for _ in range(90):                       # settle: MK standing still, nothing buffered
    cmd("gd.input(1, {buttons='', x=0, y=0}, 600) gd.step(1)")
    if lua("gd.player(1).motion_name") == "Wait" and _ > 30: break
cmd("gd.release(1)")
print("start:", lua("hb_snap(1)"), lua("gd.player(1).x"), lua("gd.player(2).x"))
cmd("savestate 1"); cmd("step 1")
report = collections.OrderedDict(); fails = 0
for name, plan in PLANS.items():
    cmd("loadstate 1"); cmd("step 1")
    frames = []
    for buttons, n, x, y in plan:
        if buttons == "approach":           # run at the CPU until close enough to grab
            for i in range(120):
                d = float(lua("gd.player(2).x - gd.player(1).x"))
                if abs(d) < (n or 11): break
                cmd(f"gd.input(1, {{buttons='', x={55 if d > 0 else -55}, y=0}}, 600) gd.step(1)")   # walk
                frames.append(lua("hb_snap(1)"))
            continue
        for i in range(n):
            # one console line: the override and the step land on the same logic frame (a paused game keeps
            # polling the pad between console lines, which would eat a separate "input" command's sample)
            b = "" if buttons == "none" else buttons
            # the override holds until replaced: the game's frame may read a pad sample other than the one polled
            # on the stepped frame (a 1-sample override moved buttons but not the stick), so every sample = this input
            cmd(f"gd.input(1, {{buttons='{b}', x={x}, y={y}}}, 600) gd.step(1)")
            frames.append(lua("hb_snap(1)"))
    cmd("gd.release(1)")
    # motions visited and hitboxes seen
    seen = collections.defaultdict(set); motions = []; facing = []
    for s in frames:
        mot, fr, hbs = (s.split("|") + ["", ""])[:3]
        facing.append((s.split("|") + ["", "", "", "0"])[3])
        if not motions or motions[-1] != mot: motions.append(mot)
        for h in hbs.split():
            i, dmg, ang, kbg, bkb, wbk, rad = h.split(":")
            seen[ROW_OF.get(mot, mot)].add((int(dmg), int(ang), int(kbg), int(bkb), int(wbk)))
    checks = []; missing = []
    for mot in dict.fromkeys(ROW_OF.get(m, m) for m in motions):
        exp = {(h["damage"], h["angle"], h["kbg"], h["bkb"], h["wdsk"]) for _, h in by_row.get(mot, [])}
        if not exp: continue
        got = seen.get(mot, set())
        # Melee stales a move once it connects: hitboxes created after the first hit show the reduced damage
        # (x0.91 per queue entry, rounded) - accept a lower damage with every other field equal
        def match(g, e): return g[1:] == e[1:] and (g[0] == e[0] or 0.5 * e[0] <= g[0] < e[0])
        miss = sorted(e for e in exp if not any(match(g, e) for g in got))
        unexp = sorted(g for g in got if not any(match(g, e) for e in exp))
        checks.append({"row": mot, "expected": len(exp), "seen": len(exp) - len(miss), "missing": miss, "unexpected": unexp})
        if miss: missing.append((mot, miss))
    alive = lua("gd.frame()") != ""
    extra_info = {"p2_percent": lua("gd.player(2).percent"), "jumps_left_min": None}
    ok = alive and not any(c["unexpected"] for c in checks)
    turned = len(set(facing)) > 1
    report[name] = {"motions": motions, "checks": checks, "alive": alive, "ok": ok, "p2_percent": extra_info["p2_percent"], "turned": turned, "frames": frames}
    fails += not ok
    print(f"{'OK  ' if ok else 'FAIL'} {name:22s} P2 {extra_info['p2_percent']:>5}%{' turned' if turned else ''}  {' > '.join(motions)[:170]}")
    for c in checks:
        print(f"       {c['row']:18s} hitbox value sets seen {c['seen']}/{c['expected']}" + (f"  not reached: {c['missing'][:4]}" if c['missing'] else "")
              + (f"  UNEXPECTED {c['unexpected'][:4]}" if c['unexpected'] else ""))
cmd("loadstate 1"); cmd("step 1"); cmd("resume")
json.dump(report, open(a.report, "w"), indent=1)
print("FAILS", fails)
