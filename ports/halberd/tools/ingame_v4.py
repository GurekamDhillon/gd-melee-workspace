"""Numeric in-game checks of Geno v4 (Meta Knight's model follows his specials) - no screenshots, joints and hitboxes only.

    python tools/ingame_v4.py <console-port> [--only drill,tornado] [--report analysis/ingame_v4.json]

Needs the Geno exe (MK on port 1 with geno.json v4 keys, the Lab: gd.joints / gd.hitboxes) and a level-0 CPU on port 2 far away.
Every plan starts from savestate 1 (MK standing).

Drill Rush (Brawl: SpecialSRush turns the posture rot.x by -stickY x 3 a frame, SpecialSEnd eases it):
  each steered run is compared with a straight run of the same facing / situation, frame by frame at the same clip frame:
  every joint's and every hitbox's offset from TopN must be the straight run's offset turned by the pitch in the world XY
  plane (turn = pitch x facing: nose up for either facing), the depth (z) unchanged, and the travel direction must be the
  nose's (atan2(vy, vx x facing) = pitch). The expected pitch is also rebuilt from the stick: +-3 a rush frame, x 0.8 a
  frame in the end.
Mach Tornado (Brawl: the spin rate is SpecialNSpin's frame speed, 1 clip frame = 1 degree of YRotN):
  the rate is rebuilt from Brawl's formula (80, -1.5 a frame, +16 per accepted B tap with a 10-frame cooldown, 0..80, -2 a
  frame after 70 frames, ends at <= 10) and checked against the clip frame (mod 360) and against the body itself: the
  shoulders' heading around YRotN turns by the rate every frame."""
import sys, os, json, socket, argparse, collections, math
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument("port", type=int)
ap.add_argument("--only", default=None)
ap.add_argument("--report", default=os.path.join(MK, "analysis", "ingame_v4.json"))
ap.add_argument("--keep-paused", action="store_true")
ap.add_argument("--offline", action="store_true", help="re-analyse <report>_raw.json, no game")
a = ap.parse_args()

if a.offline:
    runs = json.load(open(a.report.replace(".json", "_raw.json")))
else:
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
    def snap(p):
        """v4_snap(p) is longer than a console reply (~1800 chars): keep it in a global and read it in chunks"""
        n = int(lua(f"(function() v4_last = v4_snap({p}) return #v4_last end)()"))
        return "".join(lua(f"v4_last:sub({i}, {min(i + 1199, n)})") for i in range(1, n + 1, 1200))

    cmd("v4_snap = function(p) local pl = gd.player(p) if not pl then return 'none' end "
        "local js = {} for _, j in ipairs(gd.joints(p) or {}) do js[#js+1] = string.format('%.4f,%.4f,%.4f,%d', j.x, j.y, j.z, j.parent) end "
        "local hs = {} for _, h in ipairs(gd.hitboxes(p) or {}) do hs[#hs+1] = string.format('%d,%d,%.4f,%.4f,%.4f', h.id, h.bone, h.x, h.y, h.z) end "
        "return string.format('%s|%d|%.3f|%.3f|%.3f|%.4f|%.4f|%.1f|%d|%s|%s', pl.motion_name or '?', pl.action or -1, pl.anim_frame_f or -1, "
        "pl.x, pl.y, pl.vx, pl.vy, pl.facing or 0, pl.airborne and 1 or 0, table.concat(js, ';'), table.concat(hs, ';')) end")

    GJ = json.load(open(os.path.join(MK, "mods-slot", "metaknight-slot", "geno.json")))["fighters"][0]
    SNAME = {0x400 + i: st["name"] for i, st in enumerate(GJ["states"])}
    def parse(s):
        p = s.split("|")
        p[0] = SNAME.get(int(p[1]), p[0])
        js = [tuple(float(v) for v in j.split(",")) for j in p[9].split(";")] if p[9] else []
        hs = [tuple(float(v) for v in h.split(",")) for h in p[10].split(";")] if len(p) > 10 and p[10] else []
        return {"motion": p[0], "action": int(p[1]), "frame": float(p[2]), "x": float(p[3]), "y": float(p[4]), "vx": float(p[5]),
                "vy": float(p[6]), "facing": float(p[7]), "air": p[8] == "1", "joints": js, "hb": hs}

    TOPN, YROTN, LSH, RSH, SWORD = 0, 4, 9, 34, 41
    JUMP = [("Y", 1, 0, 0), ("none", 8, 0, 0), ("Y", 1, 0, 0), ("none", 6, 0, 0)]   # ground jump + air jump: room to drill
    TURN = [("none", 1, -127, 0), ("none", 20, 0, 0)]
    SIDEB_R, SIDEB_L = ("B", 1, 127, 0), ("B", 1, -127, 0)
    def drill(left, air, steer_y, steer_n):
        pre = (TURN if left else []) + (JUMP if air else [])
        sb = SIDEB_L if left else SIDEB_R
        # hold the steer from the side-B press: the start ignores it, the rush turns from its first frame
        return pre + [(sb[0], 1, sb[2], 0), ("none", 21, 0, steer_y if steer_n else 0),
                      ("none", steer_n, 0, steer_y), ("none", 45 + 30 + 8 - steer_n, 0, 0)]
    PLANS = collections.OrderedDict()
    for left in (False, True):
        for air in (True, False):
            tag = f"drill {'air' if air else 'ground'} {'left' if left else 'right'}"
            PLANS[tag + " straight"] = drill(left, air, 0, 0)
            PLANS[tag + " up"] = drill(left, air, 127, 30 if air else 12)
            if air: PLANS[tag + " down"] = drill(left, air, -127, 25)
    TAPS = [x for _ in range(6) for x in (("none", 5, 0, 0), ("B", 1, 0, 0))]
    PLANS["tornado ground"] = [("B", 1, 0, 0), ("none", 140, 0, 0)]
    PLANS["tornado taps"] = [("B", 1, 0, 0)] + TAPS + [("none", 120, 0, 0)]
    PLANS["tornado air left"] = TURN + JUMP + [("B", 1, 0, 0), ("none", 30, -90, 0), ("none", 120, 0, 0)]
    if a.only: PLANS = collections.OrderedDict((k, v) for k, v in PLANS.items() if any(o in k for o in a.only.split(",")))

    cmd("pause"); cmd("gd.release(1)"); cmd("gd.release(2)")
    for i in range(120):
        cmd("gd.input(1, {buttons='', x=0, y=0}, 600) gd.step(1)")
        if lua("gd.player(1).motion_name") == "Wait" and i > 30: break
    cmd("gd.release(1)")
    st0 = parse(snap(1))
    if st0["motion"] != "Wait": raise SystemExit("MK is not standing (Wait): " + st0["motion"])
    cmd("savestate 1"); cmd("step 1")
    # the skeleton: joint 4 must be YRotN (parent 3 XRotN, parent 2 TransN, parent 0 TopN), 41 SwordM
    par = [int(j[3]) for j in st0["joints"]]
    print("joints", len(par), "parents 1..5:", par[1:6], "sword parent", par[SWORD] if len(par) > SWORD else None)

    runs = {}
    for name, plan in PLANS.items():
        cmd("loadstate 1"); cmd("step 1")
        frames = []
        for buttons, n, x, y in plan:
            for _ in range(n):
                b = "" if buttons == "none" else buttons
                # the stick's y also carries the tap (taps are 1 frame of B)
                cmd(f"gd.input(1, {{buttons='{b}', x={x}, y={y}}}, 600) gd.step(1)")
                fr = parse(snap(1)); fr["in"] = (b, x, y); frames.append(fr)
        cmd("gd.release(1)")
        runs[name] = frames

    json.dump(runs, open(a.report.replace(".json", "_raw.json"), "w"))
TOPN, YROTN, LSH, RSH, SWORD = 0, 4, 9, 34, 41
def wrap(d): return (d + 180.0) % 360.0 - 180.0
def rel(fr, i): j, t = fr["joints"][i], fr["joints"][TOPN]; return (j[0] - t[0], j[1] - t[1], j[2] - t[2])
def fit_turn(pairs):
    """least-squares rotation (deg, CCW in world XY) taking the reference offsets onto the steered ones"""
    c = s = 0.0
    for (ax, ay), (bx, by) in pairs: c += ax * bx + ay * by; s += ax * by - ay * bx
    return math.degrees(math.atan2(s, c))

report = collections.OrderedDict(); fails = 0
def need(ch, cond, what): ch.append((bool(cond), what))
# joints whose matrix the game did not recompute this frame (hidden parts: the cape chain during the rush, the wings
# after SpecialSEnd's Model Changer at 10; frozen in the world while the body moved) carry no pose: marked per frame and left out of the rigid-turn fit
for rf in runs.values():
    for k, fr in enumerate(rf):
        fr["stale"] = set()
        if k == 0: continue
        p0 = rf[k - 1]["joints"]; p1 = fr["joints"]
        # frozen = not recomputed: the joint did not move at all while the body (BodyN, 6) did
        if len(p0) != len(p1) or math.dist(p0[6][:3], p1[6][:3]) < 1e-3: continue
        fr["stale"] = {i for i in range(1, len(p1)) if math.dist(p0[i][:3], p1[i][:3]) < 1e-4}
    # a part hidden in a state is hidden for all of it: the union over the state's frames of this run
    by_state = collections.defaultdict(set)
    for fr in rf: by_state[fr["motion"]] |= fr["stale"]
    for fr in rf: fr["stale"] = by_state[fr["motion"]]
for name, frames in runs.items():
    ch = []; rec = {}
    if name.startswith("drill") and not name.endswith("straight"):
        left = " left" in name
        # reference poses at pitch 0: every straight run of the same facing, by (state, clip frame)
        rmap = {}
        for rn, rf in runs.items():
            if rn.startswith("drill") and rn.endswith("straight") and (" left" in rn) == left:
                for fr in rf:
                    if fr["motion"] in ("Drill", "DrillEnd", "DrillEndGround"):
                        rmap.setdefault((fr["motion"], round(fr["frame"], 2)), fr)
        # expected pitch, rebuilt from the stick (the pad reaches the game one frame after it is set):
        # +-3 per rush frame (stick normalised by 80, dead zone 0.2875), x (1 - 2/10) per end frame
        pitch = 0.0; rows = []; worst = worst_hb = worst_z = worst_trav = worst_res = 0.0; n_hb = n_j = 0
        prev_in = None
        for fr in frames:
            m = fr["motion"]; stick = prev_in[2] if prev_in else 0; prev_in = fr["in"]
            if m == "Drill":
                sy = max(-1.0, min(1.0, stick / 80.0))
                if abs(sy) >= 0.2875: pitch += sy * 3.0
            elif m in ("DrillEnd", "DrillEndGround"):
                pitch -= 2.0 * pitch / 10.0
            else:
                continue
            fac = 1.0 if fr["facing"] >= 0 else -1.0
            want = pitch * fac
            r0 = rmap.get((m, round(fr["frame"], 2)))
            row = {"motion": m, "frame": fr["frame"], "air": fr["air"], "pitch_expected": round(pitch, 3), "want_turn": round(want, 3)}
            if r0 is not None:
                pairs = []; dz = 0.0
                for i in range(1, min(len(fr["joints"]), len(r0["joints"]))):
                    ja, jb = r0["joints"][i], fr["joints"][i]
                    # joints the game never places (the cape / wing attach nodes sit at the world origin) carry no pose
                    if abs(ja[0]) + abs(ja[1]) + abs(ja[2]) < 1e-3 or abs(jb[0]) + abs(jb[1]) + abs(jb[2]) < 1e-3: continue
                    if i in fr["stale"] or i in r0["stale"]: continue
                    a_ = rel(r0, i); b_ = rel(fr, i)
                    if math.hypot(a_[0], a_[1]) < 0.5: continue
                    pairs.append(((a_[0], a_[1]), (b_[0], b_[1]))); dz = max(dz, abs(a_[2] - b_[2]))
                turn = fit_turn(pairs)
                cr, sr = math.cos(math.radians(turn)), math.sin(math.radians(turn)); res = 0.0
                for (ax, ay), (bx, by) in pairs: res = max(res, math.hypot(ax * cr - ay * sr - bx, ax * sr + ay * cr - by))
                row.update({"model_turn": round(turn, 3), "joints": len(pairs), "joint_residual": round(res, 4), "dz": round(dz, 4)})
                worst = max(worst, abs(wrap(turn - want))); worst_z = max(worst_z, dz); worst_res = max(worst_res, res); n_j += 1
                hb0 = {int(h[0]): h for h in r0["hb"]}; t0 = r0["joints"][TOPN]; t1 = fr["joints"][TOPN]
                hbt = []
                for h in fr["hb"]:
                    h0 = hb0.get(int(h[0]))
                    if h0 is None: continue
                    ax, ay = h0[2] - t0[0], h0[3] - t0[1]; bx, by = h[2] - t1[0], h[3] - t1[1]
                    if math.hypot(ax, ay) < 1.0: continue
                    ht = math.degrees(math.atan2(ax * by - ay * bx, ax * bx + ay * by)); hbt.append(round(ht, 3))
                    worst_hb = max(worst_hb, abs(wrap(ht - want))); n_hb += 1
                if hbt: row["hitbox_turns"] = hbt
            if m == "Drill" and fr["air"] and math.hypot(fr["vx"], fr["vy"]) > 0.3:
                trav = math.degrees(math.atan2(fr["vy"], fr["vx"] * fac)); row["travel"] = round(trav, 3)
                worst_trav = max(worst_trav, abs(wrap(trav - pitch)))
            rows.append(row)
        rec = {"rows": rows}
        maxp = max((abs(r["pitch_expected"]) for r in rows), default=0)
        need(ch, rows and n_j > 30, f"Drill / DrillEnd frames compared with a pitch-0 reference ({n_j})")
        need(ch, maxp > 20, f"the stick pitched the rush (max {maxp:.0f} deg)")
        need(ch, worst < 0.05, f"model turn = pitch x facing at every compared frame (worst {worst:.4f} deg)")
        need(ch, worst_res < 0.05, f"a rigid turn about TopN (worst joint residual {worst_res:.4f})")
        need(ch, worst_z < 0.01, f"the turn stays in the XY plane (worst joint dz {worst_z:.4f})")
        need(ch, n_hb > 0 and worst_hb < 0.05, f"hitboxes turn with the model ({n_hb} hitbox-frames, worst {worst_hb:.4f} deg)")
        need(ch, worst_trav < 0.05, f"airborne travel follows the nose (worst {worst_trav:.4f} deg)")
        end = [r for r in rows if r["motion"] != "Drill" and "model_turn" in r]
        need(ch, len(end) > 5 and abs(end[-1]["model_turn"]) < 1.0 < abs(end[0]["model_turn"]),
             f"the end eases the model to level ({end[0]['model_turn'] if end else '-'} -> {end[-1]['model_turn'] if end else '-'})")
        rec["summary"] = {"max_pitch": maxp, "compared_frames": n_j, "worst_turn_err": worst, "worst_joint_residual": worst_res,
                          "worst_hitbox_err": worst_hb, "hitbox_frames": n_hb, "worst_dz": worst_z, "worst_travel_err": worst_trav}
    elif name.startswith("drill"):
        rec = {"motions": sorted({fr["motion"] for fr in frames})}
        need(ch, any(fr["motion"] == "Drill" for fr in frames), "reference run reached Drill")
    elif name.startswith("tornado"):
        t = [fr for fr in frames if fr["motion"] == "Tornado"]
        # the spin rate, rebuilt from the inputs exactly as the phys callback runs it (Brawl's execStatus + kinetic 0x65):
        # every frame from the entry frame on: since += 1; while the countdown (70) runs: r -= 1.5, a B press arms a lift,
        # an armed lift >= 10 frames after the last one adds 16 (and resets the count), r in [0, 80]; after it r -= 2.
        # The entry frame's own B press counts (the special's press). The joints advance by the rate the frame's phys set,
        # on the next frame; the state ends (anim callback, before phys) once r <= 10.
        r = 80.0; cd = 70; since = 0; armed = 0; rows = []; frame_exp = None; worst_f = worst_body = 0.0
        prev_head = None; started = False; lifts = 0; ended_ok = None; prev_in = ("", 0, 0)
        for k, fr in enumerate(frames):
            pin, prev_in = prev_in, fr["in"]
            if fr["motion"] != "Tornado":
                if started:
                    ended_ok = r <= 10.0
                    break
                continue
            if not started:
                started = True; frame_exp = fr["frame"]
            else:
                frame_exp = (frame_exp + r) % 360.0
            row = {"k": len(rows), "frame": round(fr["frame"], 3), "frame_expected": round(frame_exp, 3), "rate_in": round(r, 3)}
            worst_f = max(worst_f, abs(wrap(fr["frame"] - frame_exp)))
            ls, rs = fr["joints"][LSH], fr["joints"][RSH]
            head = math.degrees(math.atan2(ls[2] - rs[2], ls[0] - rs[0]))
            if prev_head is not None:
                d = abs(wrap(head - prev_head)); row["body_turn"] = round(d, 3)
                worst_body = max(worst_body, abs(d - min(r, 360.0 - r)))
            prev_head = head
            # this frame's phys
            since += 1
            if cd >= 0:
                cd -= 1; r -= 1.5
                if pin[0] == "B": armed = 1
                if since >= 10 and armed:
                    r += 16.0; armed = 0; since = 0; lifts += 1
                r = min(max(r, 0.0), 80.0)
            else:
                r = max(r - 2.0, 0.0)
            row["rate_set"] = round(r, 3)
            rows.append(row)
        rec = {"rows": rows}
        need(ch, len(t) > 20, f"Tornado entered ({len(t)} frames)")
        need(ch, worst_f < 0.01, f"clip frame = running sum of the spin rate, mod 360 (worst {worst_f:.4f} frames)")
        need(ch, worst_body < 0.25, f"the body (shoulders around YRotN) turns by the rate every frame (worst {worst_body:.3f} deg)")
        need(ch, ended_ok, f"the spin ends when the rate reaches 10 ({len(t)} frames, {lifts} lifts)")
        if "taps" in name: need(ch, lifts >= 2, f"B taps lift and speed the spin up ({lifts} lifts)")
        rec["summary"] = {"frames": len(t), "lifts": lifts, "worst_frame_err": worst_f, "worst_body_err": worst_body,
                          "first_rates": [x["rate_set"] for x in rows[:6]]}
    ok = all(c for c, _ in ch); fails += not ok
    rec["checks"] = [{"ok": c, "what": w} for c, w in ch]; rec["ok"] = ok
    report[name] = rec
    print(f"{'OK  ' if ok else 'FAIL'} {name}")
    for c, w in ch: print(f"       {'ok ' if c else 'NO '} {w}")
if not a.offline:
    cmd("loadstate 1"); cmd("step 1")
    if not a.keep_paused: cmd("resume")
os.makedirs(os.path.dirname(a.report), exist_ok=True)
json.dump(report, open(a.report, "w"), indent=1)
print("FAILS", fails)
