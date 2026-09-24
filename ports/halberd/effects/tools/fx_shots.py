"""Screenshot Meta Knight's moves at chosen frames with the scripting API's gd.set_motion (the Lab's lock-step entry):
every shot starts from savestate 1 (MK standing), enters the motion at frame 1 and steps to the frame, so the effects
the script spawns on the way are drawn exactly as in play.

    python effects/tools/fx_shots.py <console-port> --out <dir> [--only fsmash,drill] [--list]
Report: <dir>/shots.json (motion reached, frame, per shot)."""
import os, json, socket, argparse, collections, time
ap = argparse.ArgumentParser()
ap.add_argument("port", type=int)
ap.add_argument("--out", required=True)
ap.add_argument("--only", default=None)
ap.add_argument("--list", action="store_true")
a = ap.parse_args()
a.out = os.path.abspath(a.out); os.makedirs(a.out, exist_ok=True)
sock = socket.create_connection(("127.0.0.1", a.port), timeout=120)
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

cmd("pause")
names = {}
for i in range(0, 0x440):
    n = lua("gd.motion_name(%d, 1)" % i)
    if n and n not in names: names[n] = i
if a.list:
    print(json.dumps(names, indent=0)); raise SystemExit
# (motion name, frames, lift into the air)
PLANS = collections.OrderedDict([
    ("jab", ("Attack100Loop", [4, 10, 16], 0)),
    ("ftilt", ("AttackS3S", [3, 5, 7], 0)),
    ("ftilt2", ("Attack12", [3, 5], 0)),
    ("utilt", ("AttackHi3", [8, 10, 12], 0)),
    ("dtilt", ("AttackLw3", [2, 4, 6], 0)),
    ("fsmash", ("AttackS4S", [23, 25, 28], 0)),
    ("usmash", ("AttackHi4", [6, 9, 13, 18], 0)),
    ("dsmash", ("AttackLw4", [3, 5, 9], 0)),
    ("nair", ("AttackAirN", [4, 8, 14], 20)),
    ("fair", ("AttackAirF", [5, 7, 10], 20)),
    ("bair", ("AttackAirB", [6, 8, 11], 20)),
    ("uair", ("AttackAirHi", [2, 4, 6], 20)),
    ("dair", ("AttackAirLw", [3, 5, 8], 20)),
    ("dash_attack", ("AttackDash", [4, 6, 9], 0)),
    ("tornado", ("SpecialNLoop", [5, 15, 30, 45], 10)),
    ("drill", ("SpecialS", [3, 8, 16, 30], 15)),
    ("shuttle", ("SpecialHi1", [8, 10, 14, 20], 0)),
    ("shuttle_loop", ("SpecialAirHi2", [2, 6, 12, 20], 25)),
    ("cape_start", ("SpecialLw1", [6, 10, 16], 0)),
    ("cape_vanish", ("SpecialLw", [2, 10], 0)),
    ("cape_attack", ("SpecialLwEnd", [2, 5, 8, 14], 0)),
    
    ("tornado_geno", ("#1029", [4, 10, 20, 35, 60], 12)),
    ("drill_geno", ("#1034", [2, 5, 9, 14, 20, 30], 15)),
    ("glide_attack", ("#1026", [3, 6, 9], 25)),
    ("bthrow", ("ThrowB", [15, 18, 21], 0)),
    ("getup_u", ("DownAttackU", [15, 17, 26], 0)),
    ("ledge_quick", ("CliffAttackQuick", [23, 25, 28], 0)),
])
if a.only: PLANS = collections.OrderedDict((k, v) for k, v in PLANS.items() if k in a.only.split(","))
rep = {}
cmd("gd.release(1)")
for label, (mname, frames, lift) in PLANS.items():
    mid = names.get(mname) if not str(mname).startswith("#") else int(mname[1:])
    if mid is None:
        print(label, "no motion", mname); rep[label] = {"error": "no motion " + mname}; continue
    rep[label] = {"motion": mname, "id": mid, "shots": []}
    for fr in frames:
        cmd("loadstate 1")
        time.sleep(0.15)
        out, ok = cmd("= gd.set_motion(1, %d, %d, 1.0, %s)" % (mid, fr, float(lift)))
        time.sleep(0.25 + fr / 50.0)
        st = lua("(function() local p = gd.player(1) return string.format('%s|%.0f', p.motion_name or '?', p.anim_frame_f or -1) end)()")
        p = os.path.join(a.out, "%s_%02d.png" % (label, fr)).replace("\\", "/")
        if os.path.exists(p): os.remove(p)
        cmd("shot " + p)
        for _ in range(50):
            time.sleep(0.1)
            if os.path.exists(p): break
        time.sleep(0.15)
        rep[label]["shots"].append({"frame": fr, "state": st, "file": p, "set_motion": out})
    print(label, mname, [s["state"] for s in rep[label]["shots"]])
json.dump(rep, open(os.path.join(a.out, "shots.json"), "w"), indent=1)
