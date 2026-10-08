#!/usr/bin/env python3
"""np_envoy_resume.py - the stage-5 proofs of online Envoy (docs/superpowers/plans/2026-10-08-envoy-online-stage5.md): two REAL clients over loopback with the
simulated network play an Envoy set, lose each other, and resume / abandon / re-resume it, driven over each client's console.

  GW_MELEE=<game checkout> GW_BUILD_ROOT=<its build root> python tools/netplay/np_envoy_resume.py set  <tag>   # Versus set: blackout, kill, mid-match kill, abandon
  GW_MELEE=... GW_BUILD_ROOT=... python tools/netplay/np_envoy_resume.py coop <tag>                              # co-op flag: refused READY, record, resume, abandon, one-sided record

Loopback only: the local matchmaking server is started on 127.0.0.1 (never the public one), both clients bind 127.0.0.1 (MELEE_NETPLAY_BIND, so no firewall prompt), windows are parked
offscreen (MELEE_WINDOW_X/Y=30000), the guest joins the host's room BY CODE (np_s5_guest.lua), the network is MELEE_NET_SIM_FILE (lag/jitter/loss, 'loss=100' = a blackout).
Every process this starts is stopped by its numeric PID at the end. Evidence: <GW_BUILD_ROOT>/np_s5/<tag>/trace.txt and result.json; the clients' own logs are copied beside them.
"""
import json, os, re, shutil, socket, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
ROOT = os.environ.get("GW_ROOT_ENV") or "E:/Projects/Melee Workspace"  # the workspace with .env and _build/SDL3.dll (a lane worktree has none of them)
BUILD = os.environ["GW_BUILD_ROOT"].replace("\\", "/")
WT = os.environ["GW_MELEE"].replace("\\", "/")
BASH = "C:/Program Files/Git/bin/bash.exe"
NETSIM = os.environ.get("MELEE_NET_SIM", "lag=40,jitter=10,loss=2")
BLACKOUT = "lag=40,jitter=10,loss=100"


def load_env():
    env = dict(os.environ)
    for line in open(ROOT + "/.env", encoding="utf-8", errors="replace"):
        m = re.match(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"?([^"\n]*)"?\s*$', line)
        if m:
            env[m.group(1)] = m.group(2)
    env["GW_MELEE"] = WT
    env["GW_BUILD_ROOT"] = BUILD
    return env


def free_port(kind=socket.SOCK_DGRAM, lo=51700, hi=58000):
    """a port nobody else on this machine holds (other lanes run their own servers and hosts)"""
    import random
    for _ in range(200):
        p = random.randrange(lo, hi)
        t = socket.socket(socket.AF_INET, kind)
        try:
            t.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            t.close()
    raise SystemExit("no free port")


class Con:
    def __init__(self, port, name, tries=240):
        self.name = name
        for _ in range(tries):
            try:
                self.s = socket.create_connection(("127.0.0.1", port), timeout=60)
                self.f = self.s.makefile("r", encoding="utf-8", errors="replace")
                self.f.readline()  # the banner; a console still starting up can reset the connection here
                break
            except OSError:  # includes ConnectionResetError (WinError 10054) from a console that is not ready yet
                try:
                    self.s.close()
                except Exception:
                    pass
                time.sleep(1)
        else:
            raise SystemExit("no console on %d" % port)

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


STATE = ('(function() local np=gd.netplay() local m=gd.match() local me=np.players[np.me+1] '
         'return table.concat({np.phase,np.lobby,np.game,np.turn,np.me,tostring(m.active),m.frame,gd.scene().name,tostring(me.locked),tostring(me.ready),np.status},"|") end)()')
RUN = ('(function() local np=gd.netplay() local e=np.envoy local r=e.run local c=r.record local w={np.phase,e.mode,r.status,tostring(r.pending),'
       'c and c.digest or "-",c and c.state or "-",c and c.game or 0,c and c.round or 0,c and (c.score[1].."-"..c.score[2]) or "-",c and c.seed or 0,'
       'c and (c.picks[2] and (c.picks[2][1]..c.picks[2][2]) or "--") or "-",r.resumed,r.abandoned,r.interrupted,e.seed,e.round,tostring(e.open),e.word,r.note} '
       'return table.concat(w,"|") end)()')
RUN_KEYS = ["phase", "mode", "status", "pending", "digest", "state", "game", "round", "score", "seed", "pick2", "resumed", "abandoned", "interrupted", "env_seed", "env_round",
            "env_open", "word", "note"]
# run.record falls back to the saved (including abandoned) record before the
# next game starts. Probe the lobby separately when checking a fresh set.
LOBBY = ('(function() local np=gd.netplay() local e=np.envoy '
         'return table.concat({np.phase,np.game,np.score[1].."-"..np.score[2],e.seed,e.round,tostring(e.open),'
         'e.picks[1]..","..e.picks[2],tostring(next(e.history)==nil),tostring(e.run.live)},"|") end)()')
LOBBY_KEYS = ["phase", "game", "score", "env_seed", "env_round", "env_open", "picks", "history", "live"]


def fresh_lobby(h, g):
    return bool(h and g and h == g and h["phase"] == "lobby" and h["game"] == "1" and h["score"] == "0-0"
                and h["env_round"] == "0" and h["env_open"] == "false" and h["picks"] == "-1,-1"
                and h["history"] == "true" and h["live"] == "false" and int(h["env_seed"]) > 0)


FIRST_FREE = ('(function() local np=gd.netplay() for i,st in ipairs(np.stages) do if st==0 then return gd.netplay_act("stage",i) end end return false end)()')


def parse(s, keys):
    if not s:
        return None
    p = s.strip('"').split("|")
    d = dict(zip(keys, p[:len(keys) - 1]))
    d[keys[-1]] = "|".join(p[len(keys) - 1:])
    return d


def parse_state(s):
    if not s:
        return None
    p = s.strip('"').split("|")
    if len(p) < 11:
        return None
    k = ["phase", "lobby", "game", "turn", "me", "match", "frame", "scene", "locked", "ready"]
    d = dict(zip(k, p[:10]))
    d["status"] = "|".join(p[10:])
    return d


class Side:
    """One client: its sandbox name, console, process, simulated-network file."""

    def __init__(self, drv, role, name, console, extra):
        self.drv, self.role, self.name, self.console, self.extra = drv, role, name, console, extra
        self.proc = None
        self.con = None
        self.sim = "%s/np_s5/%s/%s.net.txt" % (BUILD, drv.tag, role)
        self.sandbox = "%s/runs/%s" % (BUILD, name)

    def launch(self, code=None):
        d = self.drv
        os.makedirs(os.path.dirname(self.sim), exist_ok=True)
        open(self.sim, "w").write(NETSIM)
        marker = self.sandbox + "/.active-run"
        if os.path.isdir(marker):
            os.rmdir(marker)  # left by a killed launcher
        env = dict(d.env0, MELEE_SCENE="mode=menu", MELEE_SKIP_INTRO="1", MELEE_VOLUME="0", MELEE_PAD_IGNORE_ADAPTER="1", MELEE_NETPLAY_SERVER=d.server,
                   MELEE_NETPLAY_BIND="127.0.0.1", MELEE_NETPLAY_PORT=str(d.udp), MELEE_NETPLAY_DELAY="2", MELEE_PAD_BOT_EDGE="70", MELEE_RB_LOG="0", MELEE_MODS_DIR=d.mods,
                   MELEE_WINDOW_X="30000", MELEE_WINDOW_Y="30000", MELEE_WINDOW_W="640", MELEE_WINDOW_H="360", MELEE_NET_SIM_FILE=self.sim,
                   MELEE_CONSOLE_PORT=str(self.console), MELEE_SCRIPT=HERE + ("/np_s5_host.lua" if self.role == "host" else "/np_s5_guest.lua"),
                   MELEE_PAD_BOT=("0,0,%d" % (100 + d.rnd % 50)) if self.role == "host" else ("1,0,%d" % (200 + d.rnd % 50)))
        env.update(self.extra)
        if code:
            env["MELEE_LAB_ROOM"] = code
        os.makedirs(self.sandbox, exist_ok=True)
        self.proc = subprocess.Popen([BASH, ROOT + "/tools/port/run.sh", "--realtime", self.name, "--iso", d.iso], cwd=WT, env=env,
                                     stdout=open("%s/np_s5/%s/%s.out" % (BUILD, d.tag, self.role), "a"), stderr=subprocess.STDOUT)
        d.pids[self.role + "@" + str(len(d.pids))] = self.proc.pid
        d.log("launched", self.role, "run", self.name, "pid", self.proc.pid, "code", code or "-")
        self.con = Con(self.console, self.role)

    def kill(self):
        if self.proc is not None and self.proc.poll() is None:
            self.drv.log("stopping", self.role, "pid", self.proc.pid)
            subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], capture_output=True)
            try:
                self.proc.wait(20)
            except Exception:
                pass
        self.con = None
        marker = self.sandbox + "/.active-run"
        if os.path.isdir(marker):
            try:
                os.rmdir(marker)
            except OSError:
                pass

    def state(self):
        return parse_state(self.con.ev(STATE)) if self.con else None

    def run(self):
        return parse(self.con.ev(RUN), RUN_KEYS) if self.con else None

    def lobby(self):
        return parse(self.con.ev(LOBBY), LOBBY_KEYS) if self.con else None

    def netsim(self, text):
        open(self.sim, "w").write(text)

    def settings(self):
        out = {}
        p = self.sandbox + "/settings.cfg"
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="replace"):
                if "=" in line:
                    k, v = line.rstrip("\r\n").split("=", 1)
                    out[k] = v
        return out

    def saved(self):
        s = self.settings()
        text = s.get("envoy_run", "")
        f = text.split("|")
        return {"text": text, "digest": f[-1] if len(f) == 19 else "", "state": int(s.get("envoy_run_state", "0") or 0), "me": s.get("envoy_run_me", ""),
                "game": int(f[2]) + 1 if len(f) == 19 and f[2].isdigit() else 0, "seed": f[1] if len(f) == 19 else "", "started": 0 if len(f) != 19 or f[12] == "-" else len(f[12]) // 6,
                "bw": f[13] if len(f) == 19 else "", "mode": f[8] if len(f) == 19 else "",
                "stocks": int(f[15]) if len(f) == 19 else -1, "continues": int(f[16]) if len(f) == 19 else -1, "lost": int(f[17]) if len(f) == 19 else -1}


STATE_NAMES = {0: "none", 1: "active", 2: "interrupted", 3: "abandoned", 4: "continued"}


class Driver:
    def __init__(self, tag):
        self.tag = tag
        self.out = "%s/np_s5/%s" % (BUILD, tag)
        # A proof tag owns its evidence; require a new tag rather than deleting prior runs.
        os.makedirs(self.out, exist_ok=False)
        self.trace = open(self.out + "/trace.txt", "w", encoding="utf-8")
        self.t0 = time.time()
        self.env0 = load_env()
        self.iso = self.env0["GW_ISO_VANILLA"]
        self.pids = {}
        self.checks = []
        self.evidence = {}
        self.rnd = int(time.time()) % 1000
        # the Envoy mod of THIS game checkout, copied (the run sandboxes only see MELEE_MODS_DIR)
        self.mods = self.out + "/mods"
        shutil.copytree(WT + "/pc/scripts/examples/envoy", self.mods + "/envoy")
        sport = int(os.environ.get("MELEE_S5_SERVER_PORT", "0")) or free_port()
        self.server = "127.0.0.1:%d" % sport
        self.srv = subprocess.Popen([sys.executable, HERE + "/server/gdmelee_server.py", "--bind", "127.0.0.1", "--port", str(sport)],
                                    stdout=open(self.out + "/server.log", "w"), stderr=subprocess.STDOUT)
        self.pids["server"] = self.srv.pid
        self.log("server pid", self.srv.pid, "on", self.server)
        self.udp = int(os.environ.get("MELEE_NETPLAY_PORT", "0")) or free_port()  # the host's game port (the default 51500 is taken when another lane is hosting)
        base = free_port(socket.SOCK_STREAM, 53000, 54000)
        self.host = Side(self, "host", "s5-%s-h" % tag, base, {})
        self.guest = Side(self, "guest", "s5-%s-g" % tag, free_port(socket.SOCK_STREAM, 54000, 55000), {})

    def log(self, *x):
        line = "[%6.1f] %s" % (time.time() - self.t0, " ".join(str(i) for i in x))
        print(line, flush=True)
        self.trace.write(line + "\n")
        self.trace.flush()

    def check(self, what, ok, detail=""):
        self.checks.append({"check": what, "ok": bool(ok), "detail": detail})
        self.log("CHECK %-4s %s %s" % ("PASS" if ok else "FAIL", what, detail))
        return bool(ok)

    def wait(self, what, fn, timeout=240, every=1.0):
        t = time.time()
        while time.time() - t < timeout:
            try:
                v = fn()
            except (EOFError, OSError):
                v = None
            if v:
                self.log("ok   %s (%.0fs)" % (what, time.time() - t))
                return v
            time.sleep(every)
        self.log("TIMEOUT %s after %ds" % (what, timeout))
        return None

    def room_code(self):
        def f():
            c = self.host.con.ev("gd.netplay().code")
            return c.strip('"') if c and len(c.strip('"')) == 4 and "?" not in c else None
        return self.wait("host: room code", f, 300, 2)

    def both(self, pred, what, timeout=240):
        def f():
            h, g = self.host.run(), self.guest.run()
            return (h, g) if h and g and pred(h, g) else None
        return self.wait(what, f, timeout)

    def rejoin_after_loss(self, code):
        self.guest.kill()
        # As in B/C, let the old transport expire before joining again. A fresh
        # guest accepted by the still-live session restarts lobby sequence 0,
        # while the host expects the old guest's next sequence. After abandon
        # there is no live record, so the interrupted-record counter won't rise.
        if not self.wait("E: host leaves the old lobby", lambda: (lambda s: s and s["phase"] != "lobby")(self.host.state()), 150, 1):
            return False
        self.guest.launch(code)
        return True

    def drive_lobby_once(self):
        """one step of what two players do in the lobby (characters, strike/ban/pick, ready) and at the results screens"""
        for side in (self.host, self.guest):
            st = side.state()
            if not st:
                continue
            if st["phase"] == "lobby":
                lp = st["lobby"]
                me = int(st["me"])
                if (lp == "char_blind" and st["locked"] != "true") or (lp in ("char_winner", "char_loser") and int(st["turn"]) == me):
                    side.con.ev('gd.netplay_act("char")')
                elif lp in ("strike", "ban", "pick") and int(st["turn"]) == me:
                    side.con.ev(FIRST_FREE)
                elif lp == "ready" and st["ready"] != "true":
                    side.con.ev('gd.netplay_act("ready",true)')
            if st["scene"] == "GS_RESULTS" and int(st["frame"]) > 200:
                side.con.cmd("input 1 %s 4" % ("START" if int(time.time()) % 2 else "A"))

    def finish(self, result_ok):
        for s in (self.host, self.guest):
            try:
                if s.con:
                    s.con.cmd("quit")
            except Exception:
                pass
        time.sleep(3)
        for s in (self.host, self.guest):
            s.kill()
        try:
            self.srv.terminate()
            self.srv.wait(10)
        except Exception:
            subprocess.run(["taskkill", "/PID", str(self.srv.pid), "/F"], capture_output=True)
        for s in (self.host, self.guest):
            for fn, dst in (("melee-pc.log", "%s.log" % s.role), ("settings.cfg", "%s.settings.cfg" % s.role)):
                try:
                    shutil.copy(os.path.join(s.sandbox, fn), "%s/%s" % (self.out, dst))
                except OSError as e:
                    self.log("missing", s.role, fn, e)
        ok = result_ok and all(c["ok"] for c in self.checks)
        json.dump({"tag": self.tag, "ok": ok, "checks": self.checks, "evidence": self.evidence, "pids": self.pids}, open(self.out + "/result.json", "w"), indent=1)
        self.log("RESULT", "PASS" if ok else "FAIL", "%d checks, %d failed" % (len(self.checks), sum(1 for c in self.checks if not c["ok"])))
        return 0 if ok else 1


def same(h, g, *keys):
    return all(h[k] == g[k] for k in keys)


# ---------------------------------------------------------------------------------------------------------------------------------------------
def scenario_set(d):
    d.host.launch()
    code = d.room_code()
    if not code:
        return d.finish(False)
    d.log("room", code)
    d.guest.launch(code)
    both = d.both(lambda h, g: h["phase"] == "lobby" and g["phase"] == "lobby" and h["status"] != "checking" and g["status"] != "checking", "both in the lobby, saved-run check done", 400)
    if not both:
        return d.finish(False)
    h, g = both
    d.check("a first meeting finds no saved run: a fresh set", h["status"] == "fresh" and g["status"] == "fresh" and h["digest"] == "-" and g["digest"] == "-", "host %s, guest %s" % (h["status"], g["status"]))
    d.host.con.cmd("envoynet auto 1")
    d.guest.con.cmd("envoynet auto 2")

    # --- game 1, to its end, then the game-2 reward ---
    def match_on():
        d.drive_lobby_once()
        a, b = d.host.state(), d.guest.state()
        return a and b and a["match"] == "true" and b["match"] == "true" and int(a["frame"]) > 300 and int(b["frame"]) > 300
    if not d.wait("game 1 running on both", match_on, 600, 1.2):
        return d.finish(False)
    time.sleep(2)
    h, g = d.host.run(), d.guest.run()
    sh, sg = d.host.saved(), d.guest.saved()
    d.check("game 1 started: both clients saved the same record (started 1, active)", sh["digest"] and sh["digest"] == sg["digest"] and sh["started"] == 1 and sh["state"] == 1 and sg["state"] == 1 and sh["bw"] == sg["bw"] and sh["bw"] != "00000000",
            "digest %s / %s, build word %s" % (sh["digest"], sg["digest"], sh["bw"]))
    d.evidence["game1_started"] = {"host": sh, "guest": sg}

    def reward_done():
        d.drive_lobby_once()
        a, b = d.host.run(), d.guest.run()
        return a and b and a["phase"] == "lobby" and b["phase"] == "lobby" and a["env_round"] == "2" and b["env_round"] == "2" and a["env_open"] == "false" and b["env_open"] == "false" and a["game"] == "2"
    if not d.wait("game 1 finished, game-2 reward resolved on both", reward_done, 1500, 1.5):
        return d.finish(False)
    time.sleep(2)
    h, g = d.host.run(), d.guest.run()
    sh, sg = d.host.saved(), d.guest.saved()
    d1 = h["digest"]
    d.check("after the reward: equal live records on both (game 2, round 2, same picks and score)", same(h, g, "digest", "game", "round", "score", "seed", "pick2") and h["game"] == "2" and h["round"] == "2",
            "digest %s, score %s, picks %s" % (h["digest"], h["score"], h["pick2"]))
    d.check("...and equal saved records", sh["digest"] == sg["digest"] == d1 and sh["state"] == 1 and sg["state"] == 1, "settings.cfg: host %s %s, guest %s %s" % (sh["digest"], STATE_NAMES[sh["state"]], sg["digest"], STATE_NAMES[sg["state"]]))
    d.evidence["boundary"] = {"host": h, "guest": g, "saved_host": sh, "saved_guest": sg}

    # --- A: a simulated blackout; the connection dies, the network comes back, the pair meets again ---
    d.log("A: blackout")
    ih, ig = int(h["interrupted"]), int(g["interrupted"])
    d.host.netsim(BLACKOUT)
    d.guest.netsim(BLACKOUT)
    gone = d.wait("both report the connection lost (interrupted)", lambda: (lambda a, b: a and b and int(a["interrupted"]) > ih and int(b["interrupted"]) > ig)(d.host.run(), d.guest.run()), 150, 1)
    d.check("A: the blackout interrupts the run on both sides", gone, "")
    sh, sg = d.host.saved(), d.guest.saved()
    d.check("A: both saved records are interrupted with the same digest", sh["state"] == 2 and sg["state"] == 2 and sh["digest"] == sg["digest"] == d1, "%s %s / %s %s" % (sh["digest"], STATE_NAMES[sh["state"]], sg["digest"], STATE_NAMES[sg["state"]]))
    d.host.netsim(NETSIM)
    d.guest.netsim(NETSIM)
    back = d.both(lambda h, g: h["phase"] == "lobby" and g["phase"] == "lobby" and h["status"] == "resumed" and g["status"] == "resumed", "A: both back in the lobby, run resumed", 300)
    if back:
        h, g = back
        d.check("A: resume yields identical run digests, game, score, picks and seed",
                same(h, g, "digest", "game", "round", "score", "seed", "pick2") and h["digest"] == d1 and h["game"] == "2" and h["round"] == "2", "host %s guest %s (before the drop: %s)" % (h["digest"], g["digest"], d1))
        d.check("A: the resumed record is active again on both", h["state"] == "active" and g["state"] == "active", "")
        d.evidence["A_resumed"] = {"host": h, "guest": g}
    else:
        d.check("A: resumed", False)
        return d.finish(False)

    # --- B: kill the guest between games, start it again with the same sandbox, join by code ---
    d.log("B: kill the guest")
    d.guest.kill()
    ih = int(d.host.run()["interrupted"])
    d.wait("host notices (interrupted)", lambda: (lambda a: a and int(a["interrupted"]) > ih)(d.host.run()), 150, 1)
    rh = int(d.host.run()["resumed"])
    d.guest.launch(code)
    back = d.both(lambda h, g: h["phase"] == "lobby" and g["phase"] == "lobby" and h["status"] == "resumed" and g["status"] == "resumed" and int(h["resumed"]) == rh + 1, "B: the new guest process resumed the run", 400)
    if back:
        h, g = back
        d.check("B: a fresh guest process resumes with identical run digests", same(h, g, "digest", "game", "round", "score", "seed", "pick2") and h["digest"] == d1, "host %s guest %s" % (h["digest"], g["digest"]))
        d.evidence["B_resumed"] = {"host": h, "guest": g}
    else:
        d.check("B: resumed", False)
        return d.finish(False)

    # --- C: play on from the resumed run (game 2), then drop mid-match and resume again: the game is replayed ---
    d.host.con.cmd("envoynet auto 1")
    d.guest.con.cmd("envoynet auto 2")
    if not d.wait("game 2 (the resumed run) running on both", match_on, 600, 1.2):
        return d.finish(False)
    time.sleep(2)
    sh, sg = d.host.saved(), d.guest.saved()
    d.check("C: the resumed run plays on: game 2 started, same record, same build word on both", sh["digest"] == sg["digest"] and sh["started"] == 2 and sh["bw"] == sg["bw"] and sh["bw"] != "00000000" and sh["digest"] != d1,
            "%s bw %s / %s bw %s" % (sh["digest"], sh["bw"], sg["digest"], sg["bw"]))
    d2 = sh["digest"]
    d.log("C: kill the guest in the middle of game 2")
    d.guest.kill()
    d.wait("host sees the match end (back to a menu or the room)", lambda: (lambda a: a and a["scene"] != "GS_VS")(d.host.state()), 180, 1)
    sh = d.host.saved()
    d.check("C: a mid-match loss keeps the record of the START of that game (game 2 started, same digest)", sh["digest"] == d2 and sh["started"] == 2 and sh["state"] in (1, 2), "%s %s" % (sh["digest"], STATE_NAMES[sh["state"]]))
    rh = int(d.host.run()["resumed"])
    d.guest.launch(code)
    back = d.both(lambda h, g: h["phase"] == "lobby" and g["phase"] == "lobby" and h["status"] == "resumed" and g["status"] == "resumed" and int(h["resumed"]) == rh + 1, "C: resumed after the mid-match loss", 600)
    if back:
        h, g = back
        d.check("C: identical run digests on both after the mid-match loss; game 2 will be replayed", same(h, g, "digest", "game", "round", "score", "seed", "pick2") and h["digest"] == d2 and h["game"] == "2",
                "host %s guest %s game %s" % (h["digest"], g["digest"], h["game"]))
        d.evidence["C_resumed"] = {"host": h, "guest": g}
    else:
        d.check("C: resumed", False)
        return d.finish(False)

    # --- D: abandon (asked by the guest): both clients end up consistent ---
    d.log("D: the guest abandons the run")
    d.guest.con.ev('gd.netplay_act("rabandon")')
    ab = d.both(lambda h, g: h["status"] == "abandoned" and g["status"] == "abandoned" and h["abandoned"] == "1" and g["abandoned"] == "1", "D: both report the run abandoned", 60)
    if ab:
        h, g = ab
        sh, sg = d.host.saved(), d.guest.saved()
        d.check("D: abandon leaves both records abandoned with the SAME digest (the run that was live)", sh["state"] == 3 and sg["state"] == 3 and sh["digest"] == sg["digest"] == d2, "%s %s / %s %s" % (sh["digest"], STATE_NAMES[sh["state"]], sg["digest"], STATE_NAMES[sg["state"]]))
        def new_lobby():
            lh, lg = d.host.lobby(), d.guest.lobby()
            return (lh, lg) if fresh_lobby(lh, lg) else None
        fresh = d.wait("D: fresh lobby state reaches both peers", new_lobby, 60)
        lh, lg = fresh or (d.host.lobby(), d.guest.lobby())
        d.check("D: and both start the same new run: game 1, 0-0, one new seed, no picks", bool(fresh),
                "live host %s / guest %s" % (lh, lg))
        d.check("D: the new seed is not the abandoned run's", bool(lh and lh["env_seed"] != d.evidence["boundary"]["host"]["seed"]), "%s vs %s" % (lh and lh["env_seed"], d.evidence["boundary"]["host"]["seed"]))
        d.evidence["D_abandoned"] = {"host": d.host.run(), "guest": d.guest.run(), "live_host": lh, "live_guest": lg, "saved_host": sh, "saved_guest": sg}
    else:
        d.check("D: abandoned", False)
        return d.finish(False)

    # --- E: an abandoned run is not offered again ---
    d.log("E: kill the guest, start it again")
    if not d.rejoin_after_loss(code):
        d.check("E: host closed the old connection", False)
        return d.finish(False)
    back = d.both(lambda h, g: h["phase"] == "lobby" and g["phase"] == "lobby" and h["status"] != "checking" and g["status"] != "checking" and g["status"] != "abandoned", "E: both in the lobby again", 400)
    if back:
        h, g = back
        d.check("E: the abandoned run is not offered again (a fresh run, no resume)", h["status"] == "fresh" and g["status"] == "fresh", "host %s guest %s" % (h["status"], g["status"]))
    else:
        d.check("E: lobby again", False)
    return d.finish(True)


def scenario_coop(d):
    d.host.extra = {"MELEE_LAB_ENVOY_MODE": "coop"}
    d.host.launch()
    code = d.room_code()
    if not code:
        return d.finish(False)
    d.guest.launch(code)
    both = d.both(lambda h, g: h["phase"] == "lobby" and g["phase"] == "lobby" and h["status"] != "checking" and g["status"] != "checking", "both in a co-op room's lobby", 400)
    if not both:
        return d.finish(False)
    h, g = both
    d.check("the room's mode is co-op on both sides (the mode word rode in the handshake)", h["mode"] == "coop" and g["mode"] == "coop", "host %s guest %s" % (h["mode"], g["mode"]))
    time.sleep(3)
    h, g = d.host.run(), d.guest.run()
    d.check("a co-op room begins its run record at once; equal digests", h["digest"] != "-" and h["digest"] == g["digest"] and h["state"] == "active" and g["state"] == "active", "%s / %s" % (h["digest"], g["digest"]))
    d1 = h["digest"]
    sh, sg = d.host.saved(), d.guest.saved()
    d.check("both saved it as a co-op record (mode word 45560002) in settings.cfg", sh["mode"] == "45560002" and sg["mode"] == "45560002" and sh["digest"] == sg["digest"] == d1, "%s %s" % (sh["mode"], sg["mode"]))
    d.check("shared stocks and one continue token are digest-carried on both", sh["stocks"] == sg["stocks"] and sh["stocks"] > 0 and sh["continues"] == sg["continues"] == 1 and sh["lost"] == sg["lost"] == 0)
    # READY is refused with the reason (nobody can start a match)
    for side in (d.host, d.guest):
        side.con.ev('gd.netplay_act("char")')
    time.sleep(2)
    for _ in range(40):
        d.drive_lobby_once()
        s = d.host.state()
        if s and s["lobby"] == "ready":
            break
        time.sleep(0.5)
    d.host.con.ev('gd.netplay_act("ready",true)')
    time.sleep(2)
    hs, gs_ = d.host.state(), d.guest.state()
    d.check("READY is refused in a co-op room, with the reason on screen", hs and "co-op" in hs["status"] and hs["ready"] != "true", "status: %s" % (hs or {}).get("status"))
    # kill the guest, resume the co-op record
    d.guest.kill()
    d.wait("host notices", lambda: (lambda a: a and int(a["interrupted"]) >= 1)(d.host.run()), 150, 1)
    d.guest.launch(code)
    back = d.both(lambda h, g: h["phase"] == "lobby" and g["phase"] == "lobby" and h["status"] == "resumed" and g["status"] == "resumed", "co-op record resumed", 400)
    if back:
        h, g = back
        d.check("the co-op run resumes with identical digests", h["digest"] == g["digest"] == d1 and h["mode"] == "coop", "%s / %s" % (h["digest"], g["digest"]))
    else:
        d.check("co-op resumed", False)
        return d.finish(False)
    # a script's digest (the co-op director's) joins the record on both, so the digests move together
    d.host.con.ev('gd.netplay_act("rnote","0123456789abcdef")')
    d.guest.con.ev('gd.netplay_act("rnote","0123456789abcdef")')
    time.sleep(2)
    h, g = d.host.run(), d.guest.run()
    d.check("the co-op director's digest joins the record; both digests move to the same new value", h["digest"] == g["digest"] and h["digest"] != d1, "%s / %s" % (h["digest"], g["digest"]))
    d2 = h["digest"]
    # one-sided record: a guest with no record (a new sandbox) meets a host that has one -> a new run, the old one kept
    d.guest.kill()
    d.wait("host notices again", lambda: (lambda a: a and int(a["interrupted"]) >= 2)(d.host.run()), 150, 1)
    d.guest = Side(d, "guest", "s5-%s-g2" % d.tag, d.guest.console, {})
    d.guest.launch(code)
    back = d.both(lambda h, g: h["phase"] == "lobby" and g["phase"] == "lobby" and h["status"] != "checking" and g["status"] != "checking", "a guest without the record joins", 400)
    if back:
        d.wait("the new run's record exists on both", lambda: (lambda a, b: a and b and a["digest"] != "-" and a["digest"] == b["digest"])(d.host.run(), d.guest.run()), 30, 1)
        h, g = d.host.run(), d.guest.run()
        d.check("a record on one side only is not resumed: a new run on both, equal digests", h["status"] == "fresh" and g["status"] == "fresh" and h["digest"] == g["digest"] and h["digest"] != d2, "%s %s %s / %s" % (h["status"], g["status"], h["digest"], g["digest"]))
    else:
        d.check("lobby with the new guest", False)
    # abandon from the host
    d.host.con.ev('gd.netplay_act("rabandon")')
    ab = d.both(lambda h, g: h["status"] == "abandoned" and g["status"] == "abandoned", "co-op run abandoned on both", 60)
    if ab:
        sh, sg = d.host.saved(), d.guest.saved()
        d.check("co-op abandon begins the same new active record on both", sh["state"] == 1 and sg["state"] == 1 and sh["digest"] == sg["digest"] and sh["continues"] == sg["continues"] == 1, "%s / %s" % (sh["digest"], sg["digest"]))
    else:
        d.check("co-op abandoned", False)
    return d.finish(True)


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("set", "coop"):
        print(__doc__)
        return 2
    d = Driver(sys.argv[2])
    try:
        return scenario_set(d) if sys.argv[1] == "set" else scenario_coop(d)
    except BaseException as e:
        d.log("EXCEPTION", repr(e))
        return d.finish(False) or 1


if __name__ == "__main__":
    sys.exit(main())
