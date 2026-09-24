"""Drive Meta Knight through his moves on a running exe (console socket) and screenshot the effects.

    python effects/tools/fx_drive.py <console-port> --out <dir> [--only fsmash,drill] [--frames-per-shot ...]

Needs MK on port 1 (training, a level-0 CPU on port 2). Every plan starts from savestate 1 (MK standing). Per plan it
records motion / frame each step and takes screenshots at the plan's frames. Report: <dir>/drive.json."""
import sys, os, json, socket, argparse, collections, time
ap = argparse.ArgumentParser()
ap.add_argument("port", type=int)
ap.add_argument("--out", required=True)
ap.add_argument("--only", default=None)
ap.add_argument("--noshots", action="store_true")
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

cmd("fx_snap = function(p) local pl = gd.player(p) if not pl then return 'none' end "
    "return string.format('%s|%d|%.1f|%.1f|%.1f', pl.motion_name or '?', pl.action or -1, pl.anim_frame_f or -1, pl.x, pl.y) end")

def seq(*items): return list(items)
# (buttons, frames, x, y, cx, cy)
JUMP = [("Y", 1, 0, 0, 0, 0), ("none", 7, 0, 0, 0, 0)]
PLANS = collections.OrderedDict([
    ("jab_rapid", (seq(*[x for _ in range(10) for x in (("A", 2, 0, 0, 0, 0), ("none", 2, 0, 0, 0, 0))]), [6, 12, 20, 30])),
    ("ftilt", (seq(("none", 1, 25, 0, 0, 0), ("none", 1, 45, 0, 0, 0), ("A", 1, 60, 0, 0, 0), ("none", 30, 0, 0, 0, 0)), [5, 7, 10])),
    ("utilt", (seq(("none", 1, 0, 25, 0, 0), ("none", 1, 0, 45, 0, 0), ("A", 1, 0, 60, 0, 0), ("none", 30, 0, 0, 0, 0)), [10, 12, 15])),
    ("dtilt", (seq(("none", 1, 0, -25, 0, 0), ("none", 1, 0, -45, 0, 0), ("A", 1, 0, -60, 0, 0), ("none", 25, 0, 0, 0, 0)), [4, 6, 8])),
    ("fsmash", (seq(("A", 1, 127, 0, 0, 0), ("none", 45, 0, 0, 0, 0)), [22, 24, 26, 29])),
    ("usmash", (seq(("A", 1, 0, 127, 0, 0), ("none", 50, 0, 0, 0, 0)), [6, 8, 11, 15])),
    ("dsmash", (seq(("A", 1, 0, -127, 0, 0), ("none", 35, 0, 0, 0, 0)), [2, 4, 8])),
    ("nair", (seq(*JUMP, ("A", 1, 0, 0, 0, 0), ("none", 40, 0, 0, 0, 0)), [8 + 3, 8 + 8, 8 + 14])),
    ("fair", (seq(*JUMP, ("A", 1, 80, 0, 0, 0), ("none", 40, 0, 0, 0, 0)), [8 + 5, 8 + 8, 8 + 11])),
    ("bair", (seq(*JUMP, ("A", 1, -80, 0, 0, 0), ("none", 40, 0, 0, 0, 0)), [8 + 6, 8 + 9, 8 + 13])),
    ("uair", (seq(*JUMP, ("none", 1, 0, 30, 0, 0), ("A", 1, 0, 60, 0, 0), ("none", 30, 0, 0, 0, 0)), [9 + 2, 9 + 4, 9 + 6])),
    ("dair", (seq(*JUMP, ("none", 1, 0, -30, 0, 0), ("A", 1, 0, -60, 0, 0), ("none", 30, 0, 0, 0, 0)), [9 + 3, 9 + 5, 9 + 8])),
    ("tornado", (seq(("B", 1, 0, 0, 0, 0), *[x for _ in range(8) for x in (("none", 6, 0, 0, 0, 0), ("B", 2, 0, 0, 0, 0))], ("none", 60, 0, 0, 0, 0)), [10, 20, 40, 60])),
    ("drill", (seq(("B", 1, 127, 0, 0, 0), ("none", 90, 0, 0, 0, 0)), [20, 26, 32, 40, 50])),
    ("shuttle", (seq(("B", 1, 0, 127, 0, 0), ("none", 90, 0, 0, 0, 0)), [8, 10, 14, 20, 30, 40])),
    ("cape", (seq(("B", 1, 0, -127, 0, 0), ("none", 80, 0, 0, 0, 0)), [5, 8, 12, 24, 30, 36, 44])),
    ("dash_attack", (seq(("none", 10, 127, 0, 0, 0), ("A", 1, 127, 0, 0, 0), ("none", 30, 0, 0, 0, 0)), [14, 16, 19])),
    ("glide_attack", (seq(*JUMP, ("Y", 24, 0, 0, 0, 0), ("none", 6, 0, 0, 0, 0), ("A", 1, 0, 0, 0, 0), ("none", 30, 0, 0, 0, 0)), [8 + 24 + 6 + 3, 8 + 24 + 6 + 6])),
    ("bthrow", (seq(("Z", 1, 0, 0, 0, 0), ("none", 10, 0, 0, 0, 0), ("none", 1, -127, 0, 0, 0), ("none", 40, 0, 0, 0, 0)), [12 + 1, 12 + 15, 12 + 18])),
    ("run", (seq(("none", 40, 127, 0, 0, 0)), [10, 20, 30])),
])
if a.only: PLANS = collections.OrderedDict((k, v) for k, v in PLANS.items() if any(o == k for o in a.only.split(",")))

cmd("pause"); cmd("gd.release(1)"); cmd("gd.release(2)")
for i in range(240):
    cmd("gd.input(1, {buttons='', x=0, y=0}, 600) gd.step(1)")
    if lua("gd.player(1).motion_name") == "Wait" and i > 30: break
cmd("gd.release(1)")
st = lua("fx_snap(1)"); print("start:", st)
cmd("savestate 1"); cmd("step 1")
rep = {}
for name, (plan, shots) in PLANS.items():
    cmd("gd.release(1)"); cmd("loadstate 1"); cmd("gd.input(1, {buttons='', x=0, y=0}, 600) gd.step(1)")
    fc = float(lua("gd.player(1).facing") or 1) or 1.0
    fs = 1 if fc > 0 else -1
    frames = []; t = 0; shots_taken = []
    for (btn, n, x, y, cx, cy) in plan:
        for _ in range(n):
            cmd("gd.input(1, {buttons='%s', x=%d, y=%d, cx=%d, cy=%d}, 600) gd.step(1)" % ("" if btn == "none" else btn, x * fs, y, cx * fs, cy))
            t += 1
            s = lua("fx_snap(1)"); frames.append((t, s))
            if t in shots and not a.noshots:
                p = os.path.join(a.out, "%s_%02d.png" % (name, t)).replace("\\", "/")
                cmd("shot " + p); shots_taken.append(p)
                for _ in range(40):
                    time.sleep(0.1)
                    if os.path.exists(p): break
                time.sleep(0.2)
    rep[name] = {"frames": frames, "shots": shots_taken}
    print(name, " -> ".join(sorted(set(s.split("|")[0] for _, s in frames), key=lambda m: [x[1].split("|")[0] for x in frames].index(m))))
cmd("gd.release(1)")
json.dump(rep, open(os.path.join(a.out, "drive.json"), "w"), indent=1)
