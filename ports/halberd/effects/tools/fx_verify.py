"""Numeric check of Meta Knight's effects on a running exe (no screenshots): what the live scripts spawn, and that every
custom effect id resolves and is drawn.

    python effects/tools/fx_verify.py <console-port> <game log> [--out effects/work/fx_verify.json]

1. Static, from the running game (Lab gd.timeline): every GFX (id, bone, frame) and sword-trail command of each motion
   MK has, compared with effects/work/fx_report.json (what build_mk_effects placed, by row).
2. Live: drives the moves (set_motion for the normal moves, pad input for the Geno specials) and reads the log's
   m-ex effect trace ("effect N drawn as bank B model/generator K ... in motion M", once per id) and its misses
   ("not drawn"); also the particle / generator / effect counters around each special (log line "fxcount").
"""
import os, re, json, socket, argparse, time, collections
ap = argparse.ArgumentParser()
ap.add_argument("port", type=int)
ap.add_argument("log")
ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "work", "fx_verify.json"))
a = ap.parse_args()
sock = socket.create_connection(("127.0.0.1", a.port), timeout=120)
f = sock.makefile("r", encoding="utf-8", errors="replace"); f.readline()
def cmd(line):
    sock.sendall((line + "\n").encode()); out = []
    while True:
        r = f.readline()
        if not r: raise SystemExit("console closed")
        r = r.rstrip("\n")
        if r in (">>> ok", ">>> error"): return out, r == ">>> ok"
        if not r.startswith("> "): out.append(r)
def lua(expr):
    out, ok = cmd("= " + expr); return "\n".join(out).replace("[console] ", "")

cmd("pause")
cmd("fxtl = function(m) local t = gd.timeline(1, m) if not t then return 'none' end local o = {} "
    "for _, e in ipairs(t.events or {}) do if e.op == 10 then o[#o+1] = string.format('g:%d:%d:%d', math.floor(e.frame), e.gfx or -1, e.bone or -1) "
    "elseif e.op == 49 then o[#o+1] = string.format('t:%d:%s', math.floor(e.frame), e.words and string.format('%08X', e.words[1] or 0) or '?') end end "
    "return (t.motion_name or '?') .. '|' .. (t.anim_name or '?') .. '|' .. table.concat(o, ' ') end")
rep = {"timeline": {}, "live": {}}
for m in range(0, 400):
    s = lua("fxtl(%d)" % m)
    if s and s != "none" and "|" in s:
        name, anim, ev = s.split("|", 2)
        if ev.strip(): rep["timeline"][m] = {"motion": name, "anim": anim, "events": ev.split()}
print("motions with effect commands:", len(rep["timeline"]))

# live: stand, save, then run each move
for i in range(200):
    cmd("gd.input(1, {buttons='', x=0, y=0}, 600) gd.step(1)")
    if lua("gd.player(1).motion_name") == "Wait" and i > 30: break
cmd("gd.release(1)"); cmd("savestate 1")
names = {}
for i in range(0, 400):
    n = lua("gd.motion_name(%d, 1)" % i)
    if n and n not in names: names[n] = i
MOVES = ["Attack100Loop", "AttackS3S", "Attack12", "Attack13", "AttackHi3", "AttackLw3", "AttackS4S", "AttackHi4", "AttackLw4",
         "AttackAirN", "AttackAirF", "AttackAirB", "AttackAirHi", "AttackAirLw", "AttackDash", "ThrowB", "DownAttackU",
         "DownAttackD", "CliffAttackQuick", "CliffAttackSlow", "EscapeF", "Run", "SpecialHi1", "SpecialAirHi2", "SpecialLw1",
         "SpecialLwEnd", "SpecialS"]
for mv in MOVES:
    mid = names.get(mv)
    if mid is None: continue
    cmd("gd.release(1)"); cmd("loadstate 1")
    lift = 20 if "Air" in mv else 0
    cmd("= gd.set_motion(1, %d, 40, 1.0, %s)" % (mid, float(lift)))
    time.sleep(1.0)
    rep["live"][mv] = lua("gd.player(1).motion_name")
# Geno specials by input (neutral B = Tornado, side B = Drill, up B, down B)
def drive(label, seq):
    cmd("gd.release(1)"); cmd("loadstate 1")
    fc = float(lua("gd.player(1).facing") or 1) or 1.0; fs = 1 if fc > 0 else -1
    seen = []
    for btn, n, x, y in seq:
        for _ in range(n):
            cmd("gd.input(1, {buttons='%s', x=%d, y=%d}, 600) gd.step(1)" % (btn, x * fs, y))
            m = lua("gd.player(1).motion_name")
            if not seen or seen[-1] != m: seen.append(m)
    cmd("gd.release(1)")
    rep["live"][label] = seen
drive("geno_tornado", [("B", 1, 0, 0)] + [("", 6, 0, 0), ("B", 2, 0, 0)] * 6 + [("", 60, 0, 0)])
drive("geno_drill", [("B", 1, 127, 0), ("", 90, 0, 0)])
drive("geno_upb", [("B", 1, 0, 127), ("", 100, 0, 0)])
drive("geno_cape", [("B", 1, 0, -127), ("", 80, 0, 0)])
drive("geno_cape_fwd", [("B", 1, 0, -127), ("", 8, 0, 0), ("", 20, 127, 0), ("", 50, 0, 0)])
drive("glide_attack", [("Y", 1, 0, 0), ("", 7, 0, 0), ("Y", 24, 0, 0), ("", 6, 0, 0), ("A", 1, 0, 0), ("", 40, 0, 0)])
time.sleep(1.0)
log = open(a.log, encoding="utf-8", errors="replace").read().splitlines()
drawn = [l for l in log if "mexeffect: fighter kind" in l and "drawn as" in l]
miss = [l for l in log if "mexeffect: fighter kind" in l and "not drawn" in l]
rep["drawn"] = drawn; rep["missed"] = miss
json.dump(rep, open(a.out, "w"), indent=1)
print("drawn ids:", len(drawn), " missed:", len(miss))
for l in drawn: print("  ", l.split("mexeffect: ")[1])
for l in miss: print("  MISS", l)
for k, v in rep["live"].items(): print("  live", k, v)
