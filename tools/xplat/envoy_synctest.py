#!/usr/bin/env python3
"""envoy_synctest.py - the CURATED SyncTest with an Envoy build and a triggered program applied.

One offline window (offscreen, MELEE_WINDOW_X/Y = 30000) boots to the menu with the Envoy mod loaded; over its console it stages a set's two builds exactly as
the online lobby does (`envoynet stage <seed> <game>`: gd.netbuild_stage with the compiled triggered programs), then launches a VS match between two bot-driven
humans. MELEE_SYNCTEST_BENCH=1 + MELEE_SYNCTEST=12 + MELEE_SYNCTEST_CURATED=1 make the rollback machinery re-simulate every frame 12 frames deep against the first
pass and compare the curated hash (which includes the evaluator word). The run passes when the log shows `curated hash: N compared, 0 mismatching` with N large and
the evaluator did work (`gd.netmods()` events / fx counters from the console).

  python tools/xplat/envoy_synctest.py <tag> [--seed 424242] [--game 1] [--secs 240] [--picks 1,2]
"""
import argparse, os, re, socket, subprocess, sys, time, json, shutil, random

ROOT = os.environ.get("GW_ROOT_ENV", "E:/Projects/Melee Workspace")
BUILD = os.environ["GW_BUILD_ROOT"].replace("\\", "/")
WT = os.environ["GW_MELEE"].replace("\\", "/")
BASH = "C:/Program Files/Git/bin/bash.exe"
OUT = ROOT + "/_build/xplat/envoy_win"


def load_env():
    env = dict(os.environ)
    for line in open(ROOT + "/.env", encoding="utf-8", errors="replace"):
        m = re.match(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"?([^"\n]*)"?\s*$', line)
        if m:
            env[m.group(1)] = m.group(2)
    env["GW_MELEE"] = WT
    env["GW_BUILD_ROOT"] = BUILD
    return env


class Con:
    def __init__(self, port):
        for _ in range(240):
            try:
                self.s = socket.create_connection(("127.0.0.1", port), timeout=60)
                break
            except OSError:
                time.sleep(1)
        else:
            raise SystemExit("no console on %d" % port)
        self.f = self.s.makefile("r", encoding="utf-8", errors="replace")
        self.f.readline()

    def cmd(self, c):
        self.s.sendall((c + "\n").encode())
        out = []
        while True:
            l = self.f.readline()
            if not l:
                raise EOFError()
            l = l.rstrip("\n")
            if l in (">>> ok", ">>> error"):
                return [o for o in out if not o.startswith("> ")], l == ">>> ok"
            out.append(l)

    def ev(self, e):
        try:
            out, ok = self.cmd("= " + e)
        except (EOFError, OSError):
            return None
        return out[-1].strip() if ok and out else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--game", type=int, default=1)
    ap.add_argument("--secs", type=int, default=240)
    ap.add_argument("--k", default="12")
    a = ap.parse_args()
    out_dir = "%s/%s" % (OUT, a.tag)
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    trace = open(out_dir + "/trace.txt", "w")

    def log(*x):
        line = "[%6.1f] %s" % (time.time() - t0, " ".join(str(i) for i in x))
        print(line, flush=True)
        trace.write(line + "\n")
        trace.flush()

    env0 = load_env()
    rnd = random.Random()
    port = 53700 + rnd.randrange(60)
    mods = BUILD + "/mods"
    shutil.rmtree(mods, ignore_errors=True)
    shutil.copytree(WT + "/pc/scripts/examples/envoy", mods + "/envoy", ignore=shutil.ignore_patterns("*.md"))
    name = "ens4-%s" % a.tag
    env = dict(env0, MELEE_SCENE="mode=menu", MELEE_SKIP_INTRO="1", MELEE_VOLUME="0", MELEE_PAD_IGNORE_ADAPTER="1", MELEE_MODS_DIR=mods, MELEE_CONSOLE_PORT=str(port),
               MELEE_WINDOW_X="30000", MELEE_WINDOW_Y="30000", MELEE_WINDOW_W="640", MELEE_WINDOW_H="360", MELEE_RUN_OWNER="envoy-s4", MELEE_SCRIPT_MS="5000",
               MELEE_SYNCTEST_BENCH="1", MELEE_SYNCTEST=a.k, MELEE_SYNCTEST_CURATED="1", MELEE_PAD_BOT_EDGE="70",
               MELEE_PAD_BOT="0,0,%d;1,1,%d" % (100 + rnd.randrange(50), 200 + rnd.randrange(50)))
    os.makedirs("%s/runs/%s" % (BUILD, name), exist_ok=True)
    p = subprocess.Popen([BASH, ROOT + "/tools/port/run.sh", "--realtime", name, "--iso", env0["GW_ISO_VANILLA"]], cwd=WT, env=env,
                         stdout=open(out_dir + "/run.out", "w"), stderr=subprocess.STDOUT)
    log("launched pid", p.pid, "console", port)
    con = Con(port)
    ok = False
    try:
        for _ in range(120):
            if con.ev('gd.scene().name') == '"GS_FRONTEND"':
                break
            time.sleep(1)
        time.sleep(3)
        log("stage:", con.cmd("envoynet stage %d %d" % (a.seed, a.game)))
        # the two builds are staged; the bench's rollback session applies them at its open
        log("netbuild:", con.ev("gd.netbuild().word"))
        log("launch:", con.ev('gd.scene_launch("mode=vs;at=match;p1=fox/c0/hu;p2=marth/c0/hu;stage=battlefield;time=480;stocks=9;items=off")'))
        t = time.time()
        while time.time() - t < a.secs:
            time.sleep(10)
            m = con.ev("gd.match().frame")
            mods_ = con.ev('(function() local m=gd.netmods() return table.concat({tostring(m.active),m.ticks,m.events,m.variants_applied,m.fx_applied},"|") end)()')
            log("frame", m, "mods", mods_)
        ok = True
    except Exception as e:
        log("error", repr(e))
    try:
        con.cmd("quit")
    except Exception:
        pass
    time.sleep(4)
    if p.poll() is None:
        log("launcher pid", p.pid, "still running; stopping its tree by PID")
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
    src = "%s/runs/%s/melee-pc.log" % (BUILD, name)
    shutil.copy(src, out_dir + "/melee-pc.log")
    txt = open(out_dir + "/melee-pc.log", encoding="utf-8", errors="replace").read()
    cur = re.findall(r"curated hash: (\d+) compared, (\d+) mismatching", txt)
    snap = re.findall(r"snap: frame (\d+), (\d+) rollbacks, (\d+) checks, (\d+) mismatching", txt)
    res = {"tag": a.tag, "ran": ok, "curated": cur[-1] if cur else None, "snap": snap[-1] if snap else None, "applied": len(re.findall(r"triggered program sealed", txt)),
           "mods_lines": len(re.findall(r"envoy mods:", txt))}
    json.dump(res, open(out_dir + "/result.json", "w"), indent=1)
    log("RESULT", json.dumps(res))
    return 0 if ok and cur and int(cur[-1][1]) == 0 and int(cur[-1][0]) > 1000 else 1


if __name__ == "__main__":
    sys.exit(main())
