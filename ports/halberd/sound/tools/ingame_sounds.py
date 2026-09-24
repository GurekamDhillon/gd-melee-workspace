"""Drive Meta Knight through his moves on a running exe (console socket) and record which motion rows he plays, per frame,
for the sound check (sound/tools/wav_detect.py matches the game's WAV capture against the bank afterwards).

    python sound/tools/ingame_sounds.py <console-port> [--out sound/work/ingame_<tag>.json] [--only a,b]

Needs a match with MK on port 1 (training, MELEE_LAB=1, a level-0 CPU on port 2) and MELEE_AUDIO_DUMP on. Every plan
starts from savestate 1 (MK standing). Per plan: the rows (anim ids) and motions MK went through, and from
sound/work/sound_report.json the Brawl sound events the pass placed in those rows (what should be heard)."""
import sys, os, json, socket, argparse, collections, time
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(os.path.dirname(HERE))
ap = argparse.ArgumentParser()
ap.add_argument("port", type=int)
ap.add_argument("--out", default=os.path.join(MK, "sound", "work", "ingame.json"))
ap.add_argument("--only", default=None)
ap.add_argument("--gap", type=int, default=45, help="idle frames after each plan (lets sounds finish)")
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
cmd("snd_snap = function(p) local pl = gd.player(p) if not pl then return 'none' end "
    "return string.format('%s|%d|%d|%.1f|%.2f|%.2f|%d', pl.motion_name or '?', pl.action or -1, pl.anim_id or -1, "
    "pl.anim_frame_f or -1, pl.x, pl.y, pl.airborne and 1 or 0) end")

J = [("Y", 1, 0, 0), ("none", 30, 0, 0)]
def s(*x): return list(x)
N = ("none", 1, 0, 0)
PLANS = collections.OrderedDict([
    ("walk", s(("none", 70, 60, 0))),
    ("dash + run + brake", s(("none", 50, 127, 0), ("none", 30, 0, 0))),
    ("turn", s(("none", 1, -127, 0), ("none", 20, 0, 0))),
    ("jump + land", s(*J, ("none", 40, 0, 0))),
    ("double jumps", s(("Y", 1, 0, 0), ("none", 10, 0, 0), ("Y", 1, 0, 0), ("none", 12, 0, 0), ("Y", 1, 0, 0), ("none", 80, 0, 0))),
    ("crouch", s(("none", 20, 0, -127), ("none", 20, 0, 0))),
    ("jab / rapid", s(N, ("A", 1, 0, 0), ("none", 2, 0, 0), ("A", 1, 0, 0), ("none", 2, 0, 0), ("A", 1, 0, 0), ("none", 2, 0, 0), ("A", 1, 0, 0), ("none", 50, 0, 0))),
    ("ftilt chain", s(N, ("A", 1, 60, 0), ("none", 8, 0, 0), ("A", 1, 0, 0), ("none", 8, 0, 0), ("A", 1, 0, 0), ("none", 50, 0, 0))),
    ("utilt", s(N, ("A", 1, 0, 60), ("none", 45, 0, 0))),
    ("dtilt", s(("none", 3, 0, -60), ("A", 1, 0, -60), ("none", 35, 0, 0))),
    ("fsmash", s(N, ("A", 1, 127, 0), ("none", 60, 0, 0))),
    ("usmash", s(N, ("A", 1, 0, 127), ("none", 60, 0, 0))),
    ("dsmash", s(N, ("A", 1, 0, -127), ("none", 50, 0, 0))),
    ("dash attack", s(("none", 8, 127, 0), ("A", 1, 127, 0), ("none", 45, 0, 0))),
    ("nair", s(("Y", 1, 0, 0), ("none", 4, 0, 0), ("A", 1, 0, 0), ("none", 60, 0, 0))),
    ("fair", s(("Y", 1, 0, 0), ("none", 4, 0, 0), ("A", 1, 90, 0), ("none", 60, 0, 0))),
    ("bair", s(("Y", 1, 0, 0), ("none", 4, 0, 0), ("A", 1, -90, 0), ("none", 60, 0, 0))),
    ("uair", s(("Y", 1, 0, 0), ("none", 4, 0, 0), ("A", 1, 0, 90), ("none", 60, 0, 0))),
    ("dair", s(("Y", 1, 0, 0), ("none", 4, 0, 0), ("A", 1, 0, -90), ("none", 60, 0, 0))),
    ("shield + spotdodge", s(("R", 20, 0, 0), ("R", 1, 0, -127), ("none", 40, 0, 0))),
    ("roll", s(("R", 6, 0, 0), ("R", 1, 127, 0), ("none", 40, 0, 0))),
    ("airdodge", s(("Y", 1, 0, 0), ("none", 6, 0, 0), ("R", 1, 0, 0), ("none", 60, 0, 0))),
    ("neutral B (tornado)", s(("B", 1, 0, 0), *[x for _ in range(6) for x in (("none", 6, 0, 0), ("B", 2, 0, 0))], ("none", 90, 0, 0))),
    ("side B (drill)", s(("B", 1, 127, 0), ("none", 110, 0, 0))),
    ("up B (shuttle loop)", s(("B", 1, 0, 127), ("none", 150, 0, 0))),
    ("down B (cape)", s(("B", 1, 0, -127), ("B", 30, 0, 0), ("none", 80, 0, 0))),
    ("taunt down", s(("DUP", 1, 0, 0), ("none", 125, 0, 0))),
    ("taunt up", s(N, ("DUP", 1, 0, 80), ("none", 125, 0, 0))),
    ("taunt side", s(("DUP", 1, 90, 0), ("none", 125, 0, 0))),
    ("grab (whiff)", s(("Z", 1, 0, 0), ("none", 40, 0, 0))),
])
if a.only: PLANS = collections.OrderedDict((k, v) for k, v in PLANS.items() if any(o in k for o in a.only.split(",")))

REP = json.load(open(os.path.join(MK, "sound", "work", "sound_report.json")))
row_ev = {int(r): v["placed"] for r, v in REP["rows"].items()}

cmd("pause"); cmd("gd.release(1)"); cmd("gd.release(2)")
for i in range(150):
    cmd("gd.input(1, {buttons='', x=0, y=0}, 600) gd.step(1)")
    if lua("gd.player(1).action") == "14" and i > 30: break
cmd("gd.release(1)")
st = lua("snd_snap(1)"); print("start:", st)
if not (st.startswith("Wait|") or st.split("|")[1] == "14"): raise SystemExit("MK is not standing (Wait): " + st)
cmd("savestate 1"); cmd("step 1")
out = collections.OrderedDict()
for name, plan in PLANS.items():
    cmd("loadstate 1"); cmd("step 1")
    t0 = time.time(); fr0 = lua("gd.frame()")
    frames = []
    for buttons, n, x, y in plan:
        for i in range(n):
            b = "" if buttons == "none" else buttons
            cmd(f"gd.input(1, {{buttons='{b}', x={x}, y={y}}}, 600) gd.step(1)")
            p = lua("snd_snap(1)").split("|")
            frames.append((p[0], int(p[2]), float(p[3])))
    cmd("gd.release(1)")
    for i in range(a.gap): cmd("gd.step(1)")
    rows = []; motions = []
    for m, row, fr in frames:
        if not rows or rows[-1][0] != row: rows.append([row, m, fr, fr])
        else: rows[-1][3] = fr
        if not motions or motions[-1] != m: motions.append(m)
    exp = []
    for row, m, f0, f1 in rows:
        for ev in row_ev.get(row, []):
            if f0 - 1 <= ev[0] <= f1 + 1: exp.append((row, m, ev[0], ev[1]))
    out[name] = {"motions": motions, "rows": rows, "expected": exp, "wall": [t0, time.time()], "frame0": fr0}
    print("%-24s %s | %d sound events: %s" % (name, " > ".join(motions)[:90], len(exp), "; ".join("%s@%d" % (e[3].split(" (")[0], e[2]) for e in exp)[:200]))
json.dump(out, open(a.out, "w"), indent=1)
cmd("resume")
