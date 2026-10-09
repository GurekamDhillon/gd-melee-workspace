#!/usr/bin/env python3
"""run_pair.py - stage-7 Classic proof: two REAL clients complete an agreed run of stages of an online STAGE RUN over loopback, each stage a fresh agreed
rollback session, the run carried between them by the run record (gw_netrun.h, RN2|...|digest). Envoy off (no mods). Loopback only: the local
matchmaking server on 127.0.0.1, both clients bound to 127.0.0.1 (MELEE_NETPLAY_BIND), windows parked offscreen. Never the public server.

  GW_MELEE=<game worktree> GW_BUILD_ROOT=<its build root> python run_pair.py <tag> [--games 2] [--poison] [--netsim lag=40,jitter=10,loss=2]

Per stage it records, for host and guest, the run record the game reports (gd.netplay().run), the scene, the frame; at the end it compares the two
clients' curated rollback hash logs (MELEE_RB_HASHLOG) stage by stage and the "netrun: ARRIVED" lines of the two game logs.
--poison  the guest computes its record from another seed (MELEE_NETRUN_POISON=1): the stage must be REFUSED and never start (negative control).
Everything lands in _build/netrun/<tag>/ (trace.txt, result.json, host/guest logs and hash logs).
"""
import argparse, json, os, random, re, shutil, socket, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
ROOT = os.environ.get("GW_ROOT_ENV", "E:/Projects/Melee Workspace")
BUILD = os.environ["GW_BUILD_ROOT"].replace("\\", "/")
WT = os.environ["GW_MELEE"].replace("\\", "/")
BASH = "C:/Program Files/Git/bin/bash.exe"
OUT = ROOT + "/_build/netrun"


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
    def __init__(self, port, name, tries=240):
        self.name = name
        for _ in range(tries):
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
                raise EOFError(self.name)
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


STATE = ('(function() local np=gd.netplay() local r=np.run local m=gd.match() local me=np.players[np.me+1] '
         'return table.concat({np.phase,np.lobby,np.game,np.turn,np.me,tostring(m.active),m.frame,gd.scene().name,tostring(r.on),r.stage,r.seed,r.record,r.refused,r.pool,r.over,r.ends,r.last,'
         'tostring(me.locked),tostring(me.ready),np.status},"~") end)()')
KEYS = ["phase", "lobby", "game", "turn", "me", "match", "frame", "scene", "run_on", "run_stage", "run_seed", "record", "refused", "pool", "over", "ends", "last", "locked", "ready"]


def parse_state(s):
    if not s:
        return None
    p = s.strip('"').split("~")
    if len(p) < len(KEYS) + 1:
        return None
    d = dict(zip(KEYS, p[:len(KEYS)]))
    d["status"] = "~".join(p[len(KEYS):])
    return d


FIRST_FREE = '(function() local np=gd.netplay() for i,st in ipairs(np.stages) do if st==0 then return gd.netplay_act("stage",i) end end return false end)()'


def sessions(path):
    """The hash log split into sessions (each match restarts at frame -123): [ {frame: hash} ]."""
    out = []
    try:
        for line in open(path, encoding="utf-8", errors="replace"):
            f, _, h = line.strip().partition(",")
            if not h:
                continue
            f = int(f)
            if f == -123:
                out.append({})
            if out:
                out[-1][f] = h
    except OSError:
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--games", type=int, default=2)
    ap.add_argument("--poison", action="store_true")
    ap.add_argument("--classic", action="store_true")
    ap.add_argument("--pool", type=int, default=12)
    ap.add_argument("--continues", type=int, choices=(0, 1), default=1)
    ap.add_argument("--expect-loss", action="store_true")
    ap.add_argument("--port", type=int, default=58270, help="host UDP port; server uses port+1, guest port+2")
    ap.add_argument("--netsim", default="off")
    ap.add_argument("--delay", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=1500)
    ap.add_argument("--stocks", default="1")
    ap.add_argument("--minutes", default="0", choices=("0",), help="runs have no timer; sudden death is excluded")
    ap.add_argument("--extra-frames", type=int, default=600, help="frames to play in the last stage before the proof is taken")
    a = ap.parse_args()
    out_dir = "%s/%s" % (OUT, a.tag)
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir, exist_ok=True)
    trace = open(out_dir + "/trace.txt", "w", encoding="utf-8")
    t0 = time.time()

    def log(*x):
        line = "[%6.1f] %s" % (time.time() - t0, " ".join(str(i) for i in x))
        print(line, flush=True)
        trace.write(line + "\n")
        trace.flush()

    env0 = load_env()
    for key in ("MELEE_NET_SIM", "MELEE_NETRUN_POISON", "MELEE_NETRUN_UNLOCK", "MELEE_NETPLAY_RUN_MINUTES"):
        env0.pop(key, None)
    iso = env0["GW_ISO_VANILLA"]
    rnd = random.Random()
    if not 58000 <= a.port <= 58997:
        ap.error("--port must be 58000..58997")
    sport = a.port + 1
    hc = 53600 + rnd.randrange(20)
    gc = hc + 20
    pids = {}
    srv = subprocess.Popen([sys.executable, HERE + "/../server/gdmelee_server.py", "--bind", "127.0.0.1", "--port", str(sport)],
                           stdout=open(out_dir + "/server.log", "w"), stderr=subprocess.STDOUT)
    pids["server"] = srv.pid
    open(out_dir + "/pids.txt", "w").write(json.dumps(pids))
    log("server pid", srv.pid, "udp 127.0.0.1:%d" % sport, "consoles", hc, gc)
    nomods = ROOT + "/_build/nomods"
    os.makedirs(nomods, exist_ok=True)
    common = dict(env0, MELEE_SCENE="mode=menu", MELEE_SKIP_INTRO="1", MELEE_VOLUME="0", MELEE_PAD_IGNORE_ADAPTER="1",
                  MELEE_NETPLAY_SERVER="127.0.0.1:%d" % sport, MELEE_NETPLAY_BIND="127.0.0.1", MELEE_NETPLAY_DELAY=str(a.delay),
                  MELEE_RB_LOG="0", MELEE_MODS_DIR=nomods, MELEE_WINDOW_X="30000", MELEE_WINDOW_Y="30000",
                  MELEE_WINDOW_W="640", MELEE_WINDOW_H="360")
    if a.netsim != "off":
        common["MELEE_NET_SIM"] = a.netsim

    def launch(side, script, console, extra):
        name = "rs-%s-%s" % (a.tag, side)
        run_dir = "%s/runs/%s" % (BUILD, name)
        os.makedirs(run_dir, exist_ok=True)
        env = dict(common, MELEE_SCRIPT=script, MELEE_CONSOLE_PORT=str(console), MELEE_RB_HASHLOG="%s/hashes.csv" % run_dir, **extra)
        p = subprocess.Popen([BASH, ROOT + "/tools/port/run.sh", "--realtime", name, "--iso", iso], cwd=WT, env=env,
                             stdout=open("%s/%s.out" % (out_dir, side), "w"), stderr=subprocess.STDOUT)
        pids[side] = p.pid
        open(out_dir + "/pids.txt", "w").write(json.dumps(pids))
        log("launched", side, "launcher pid", p.pid, "run", name)
        return p, run_dir

    hp, hdir = launch("h", HERE + "/run_host.lua", hc,
                      dict(MELEE_NETPLAY_RUN="classic" if a.classic else "1", MELEE_NETPLAY_PORT=str(a.port),
                           MELEE_NETPLAY_RUN_POOL=str(a.pool), MELEE_NETPLAY_RUN_CONT=str(a.continues),
                           MELEE_NETPLAY_RUN_LEN=str(a.games), MELEE_NETPLAY_RUN_STOCKS=a.stocks, MELEE_NETPLAY_RUN_MINUTES="0",
                           MELEE_PAD_BOT="0,0,%d" % (100 + rnd.randrange(50))))
    host = Con(hc, "host")
    code = None
    t = time.time()
    while time.time() - t < 240:
        c = host.ev("gd.netplay().code")
        if c and len(c.strip('"')) == 4 and "?" not in c:
            code = c.strip('"')
            break
        time.sleep(2)
    result = {"classic": a.classic, "expect_loss": a.expect_loss, "tag": a.tag, "stages": [], "ok": False, "poison": a.poison}
    gp = None

    def finish(rc):
        for c in (host, guest) if gp is not None else (host,):
            try:
                c.cmd("quit")
            except Exception:
                pass
        time.sleep(4)
        for side, base in (("h", hdir), ("g", gdir if gp is not None else None)):
            if base is None:
                continue
            for fn, dst in (("melee-pc.log", "%s.log" % side), ("hashes.csv", "%s.hashes.csv" % side)):
                try:
                    shutil.copy(os.path.join(base, fn), "%s/%s" % (out_dir, dst))
                except OSError as e:
                    log("missing", side, fn, e)
        for p in (hp, gp):
            if p is not None and p.poll() is None:
                log("launcher pid", p.pid, "still running; stopping that process tree by PID")
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
        srv.terminate()
        try:
            srv.wait(10)
        except Exception:
            subprocess.run(["taskkill", "/PID", str(srv.pid), "/F"], capture_output=True)
        # ---- the proof: logs and hashes
        arr = {}
        for side in ("h", "g"):
            try:
                txt = open("%s/%s.log" % (out_dir, side), encoding="utf-8", errors="replace").read()
            except OSError:
                txt = ""
            arr[side] = re.findall(r"netrun: ARRIVED in stage (\d+) of the run - (\S+) \(", txt)
            result["log_" + side] = {"arrived": arr[side], "refused": re.findall(r"netrun: .*REFUSED.*", txt)[:4],
                                     "desync": len(re.findall(r"CHECKSUM DESYNC|desyncs [1-9][0-9]*", txt, re.I)),
                                     "ends": re.findall(r"netrun: STAGE END (.*)", txt)}
        hs, gs_ = sessions(out_dir + "/h.hashes.csv"), sessions(out_dir + "/g.hashes.csv")
        cmp_ = []
        for i in range(min(len(hs), len(gs_))):
            common_f = sorted(set(hs[i]) & set(gs_[i]))
            bad = [f for f in common_f if hs[i][f] != gs_[i][f]]
            cmp_.append({"stage": i + 1, "frames_host": len(hs[i]), "frames_guest": len(gs_[i]), "frames_compared": len(common_f),
                         "mismatches": len(bad), "first_mismatch": bad[0] if bad else None})
        result["hash_compare"] = cmp_
        if not a.poison:
            result["ok"] = (result["ok"] and len(cmp_) >= (1 if a.expect_loss else a.games)
                            and all(c["frames_compared"] > 0 and c["mismatches"] == 0 for c in cmp_)
                            and arr["h"] == arr["g"] and len(arr["h"]) >= (1 if a.expect_loss else a.games)
                            and result["log_h"]["ends"] == result["log_g"]["ends"]
                            and len(result["log_h"]["ends"]) >= (1 if a.expect_loss else a.games)
                            and result["log_h"]["desync"] == result["log_g"]["desync"] == 0)
        else:
            result["ok"] = result["ok"] and not arr["h"] and not arr["g"]
        rc = 0 if result["ok"] else 1
        json.dump(result, open(out_dir + "/result.json", "w"), indent=1)
        log("RESULT", "PASS" if result["ok"] else "INCOMPLETE/FAIL", json.dumps({k: v for k, v in result.items() if k != "stages"}))
        return rc

    if not code:
        log("no room code")
        guest = None
        gdir = None
        return finish(1)
    log("room", code)
    gx = dict(MELEE_LAB_ROOM=code, MELEE_NETPLAY_PORT=str(a.port + 2), MELEE_PAD_BOT="1,0,%d" % (200 + rnd.randrange(50)))
    if a.poison:
        gx["MELEE_NETRUN_POISON"] = "1"
    gp, gdir = launch("g", HERE + "/run_guest.lua", gc, gx)
    guest = Con(gc, "guest")
    log("consoles connected")
    seen = {}
    t_end = time.time() + a.timeout
    prev = None
    last_log = 0
    while time.time() < t_end:
        hs_, gs_ = parse_state(host.ev(STATE)), parse_state(guest.ev(STATE))
        if hs_ is None or gs_ is None:
            log("console lost")
            break
        line = "H %s | G %s" % ("|".join(str(hs_[k]) for k in ("phase", "lobby", "game", "match", "frame", "scene", "run_stage", "refused", "ready")),
                                "|".join(str(gs_[k]) for k in ("phase", "lobby", "game", "match", "frame", "scene", "run_stage", "refused", "ready")))
        if line != prev and time.time() - last_log > 1.5:
            log(line)
            prev, last_log = line, time.time()
        for st, con in ((hs_, host), (gs_, guest)):
            if st["phase"] == "lobby":
                lp, me = st["lobby"], int(st["me"])
                if lp == "char_blind" and st["locked"] != "true":
                    con.ev('gd.netplay_act("char")')
                elif lp in ("char_winner", "char_loser") and int(st["turn"]) == me:
                    con.ev('gd.netplay_act("char")')
                elif lp in ("strike", "ban", "pick") and int(st["turn"]) == me:
                    con.ev(FIRST_FREE)   # (an ordinary set; a run never gets here)
                elif lp == "ready" and st["ready"] != "true" and st["over"] == "":
                    con.ev('gd.netplay_act("ready",true)')
            if st["scene"] == "GS_RESULTS" and int(st["frame"]) > 200:
                con.cmd("input 1 %s 4" % ("START" if int(time.time()) % 2 else "A"))
        if not a.poison and hs_["over"] in ("stocks", "cleared") and gs_["over"] == hs_["over"]:
            result["outcome"] = {"host": hs_, "guest": gs_}
            result["ok"] = (hs_["record"] == gs_["record"] and hs_["last"] == gs_["last"]
                            and (hs_["over"] == "stocks" if a.expect_loss else hs_["over"] == "cleared")
                            and all(stage["records_equal"] for stage in result["stages"]))
            return finish(0 if result["ok"] else 1)
        if a.poison and (int(hs_["refused"]) > 0 or int(gs_["refused"]) > 0):
            result["poison_result"] = {"host_refused": hs_["refused"], "guest_refused": gs_["refused"], "host_status": hs_["status"],
                                       "guest_status": gs_["status"], "match_started": [hs_["match"], gs_["match"]]}
            log("POISON result", json.dumps(result["poison_result"]))
            time.sleep(4)
            result["ok"] = (hs_["match"] != "true" and gs_["match"] != "true")
            return finish(0 if result["ok"] else 1)
        if hs_["match"] == "true" and gs_["match"] == "true" and hs_["run_on"] == "true" and gs_["run_on"] == "true":
            g_no = hs_["game"]
            need = 180 if int(g_no) < a.games else a.extra_frames
            if int(hs_["frame"]) > need and int(gs_["frame"]) > need and g_no not in seen:
                seen[g_no] = True
                ev = {"game": g_no, "host": {k: hs_[k] for k in ("record", "run_stage", "run_seed", "scene", "frame")},
                      "guest": {k: gs_[k] for k in ("record", "run_stage", "run_seed", "scene", "frame")}}
                ev["records_equal"] = hs_["record"] == gs_["record"] and hs_["record"] != ""
                result["stages"].append(ev)
                log("EVIDENCE stage", g_no, json.dumps(ev))
                if int(g_no) >= a.games:
                    log("last stage reached; waiting for the agreed outcome")
        time.sleep(1.2)
    log("timeout")
    return finish(1)


if __name__ == "__main__":
    sys.exit(main())
