#!/usr/bin/env python3
"""envoy_set_win.py - TWO REAL WINDOWS clients on this machine play an online Envoy set through the real menus and lobby, over loopback only
(a local copy of the matchmaking server bound to 127.0.0.1; never netplay.gsd.sh), driven over each client's console. It is envoy_set.py without the
WSL Linux guest, built for the stage 4 soak (triggered builds firing under MELEE_NET_SIM lag / jitter / loss, long sets, 0 desyncs).

Both clients are launched offscreen (MELEE_WINDOW_X/Y = 30000) and bind their UDP socket to 127.0.0.1 (MELEE_NETPLAY_BIND), because every run.sh sandbox is
a new exe path and Windows Firewall asks about each one (a prompt stalls the game until somebody clicks it); a loopback bind never triggers it.

  python tools/xplat/envoy_set_win.py <tag> [--games 3] [--netsim lag=50,jitter=20,loss=3] [--seed N] [--timeout 1800] [--stocks N]

Environment: GW_MELEE and GW_BUILD_ROOT select the game checkout and its build root (tools/port/agent_new.sh); GW_ROOT_ENV the workspace root.
Writes _build/xplat/envoy_win/<tag>/: trace.txt, host.log, guest.log, *.hashes.csv, result.json, mods.csv (the evaluator's counters over time).
Every process this starts is stopped by numeric PID before it returns.
"""
import argparse, os, re, socket, subprocess, sys, time, random, shutil, json

HERE = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
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


def free_gb():
    out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB"], capture_output=True, text=True).stdout
    return float(out.strip().replace(",", "."))


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


STATE = ('(function() local np=gd.netplay() local e=np.envoy local m=gd.match() local me=np.players[np.me+1] '
         'return table.concat({np.phase,np.lobby,np.game,np.turn,np.me,tostring(m.active),m.frame,gd.scene().name,tostring(e.on),tostring(e.open),e.picks[1],e.picks[2],e.round,e.refused,e.word,e.peer_word,tostring(me.locked),tostring(me.ready),np.status},"|") end)()')
# the evaluator's counters: ticks|events|variants|fx|frame0|drop0|queue0|mask0|mask1|statuses0|statuses1
MODS = ('(function() local m=gd.netmods() local p=m.ports local function st(q) local t={} for n,v in pairs(q.statuses) do t[#t+1]=n..":"..v.stacks.."x"..string.format("%.2f",v.amount) end table.sort(t) return table.concat(t,",") end '
        'return table.concat({tostring(m.active),m.ticks,m.events,m.variants_applied,m.fx_applied,p[1].frame,p[1].dropped,p[1].queue,p[1].mask,p[2].mask,st(p[1]),st(p[2])},"|") end)()')
BUILDS = ('(function() local b=gd.netbuild() local out={b.word,tostring(b.applied)} for i=1,2 do local s=b.slots[i] '
          'out[#out+1]=table.concat({i,tostring(s.active),tostring(s.digest),tostring(s.applied_ops),tostring(s.applied_nops),tostring(s.live)},",") end return table.concat(out,"|") end)()')
FIRST_FREE = ('(function() local np=gd.netplay() for i,st in ipairs(np.stages) do if st==0 then return gd.netplay_act("stage",i) end end return false end)()')


def parse_state(s):
    if not s:
        return None
    p = s.strip('"').split("|")
    if len(p) < 19:
        return None
    k = ["phase", "lobby", "game", "turn", "me", "match", "frame", "scene", "env_on", "env_open", "pick1", "pick2", "round", "refused", "word", "peer", "locked", "ready"]
    d = dict(zip(k, p[:18]))
    d["status"] = "|".join(p[18:])
    return d


def kill(pid):
    subprocess.run(["taskkill", "/PID", str(int(pid)), "/T", "/F"], capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--games", type=int, default=3)
    ap.add_argument("--netsim", default="off")
    ap.add_argument("--delay", type=int, default=2)
    ap.add_argument("--picks", default="1,2")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--seed", type=int, default=0, help="the set's run seed (MELEE_NETPLAY_SEED on the host); 0 = the host's own draw")
    ap.add_argument("--poison", action="store_true", help="MELEE_ENVOY_POISON on the guest: the hash must trip")
    ap.add_argument("--mods-poison", action="store_true", help="MELEE_MODS_POISON=1 on the guest: the evaluator word differs on that peer, the hash must trip")
    ap.add_argument("--no-bots", action="store_true")
    ap.add_argument("--port-base", type=int, default=53000, help="base of this run's UDP/console ports (server +100, host +200, guest +400, consoles +600)")
    ap.add_argument("--turbo", default="", help="MELEE_NETPLAY_TURBO for the host (on|off|HEX): the online Turbo match rule")
    a = ap.parse_args()
    out_dir = "%s/%s" % (OUT, a.tag)
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir, exist_ok=True)
    trace = open(out_dir + "/trace.txt", "w", encoding="utf-8")
    modscsv = open(out_dir + "/mods.csv", "w", encoding="utf-8")
    t0 = time.time()

    def log(*x):
        line = "[%6.1f] %s" % (time.time() - t0, " ".join(str(i) for i in x))
        print(line, flush=True)
        trace.write(line + "\n")
        trace.flush()

    if free_gb() < 2.5:
        print("not enough free memory")
        return 2
    env0 = load_env()
    iso = env0["GW_ISO_VANILLA"]
    rnd = random.Random()
    pb = a.port_base  # each lane has its own range (53xxx envoy-s4, 56xxx linux-turbo); 51500 is the shared default
    sport = pb + 100 + rnd.randrange(80)
    hport = pb + 200 + rnd.randrange(100)
    gport = pb + 400 + rnd.randrange(100)
    hc = pb + 600 + rnd.randrange(20)
    gc = hc + 20
    pids = {}
    mods = BUILD + "/mods"
    shutil.rmtree(mods, ignore_errors=True)
    shutil.copytree(WT + "/pc/scripts/examples/envoy", mods + "/envoy", ignore=shutil.ignore_patterns("*.md"))
    srv = subprocess.Popen([sys.executable, ROOT + "/tools/netplay/server/gdmelee_server.py", "--bind", "127.0.0.1", "--port", str(sport)],
                           stdout=open(out_dir + "/server.log", "w"), stderr=subprocess.STDOUT)
    pids["server"] = srv.pid
    open(out_dir + "/pids.txt", "w").write(json.dumps(pids))
    log("server pid", srv.pid, "udp", sport, "consoles", hc, gc)
    common = dict(env0, MELEE_SCENE="mode=menu", MELEE_SKIP_INTRO="1", MELEE_VOLUME="0", MELEE_PAD_IGNORE_ADAPTER="1",
                  MELEE_NETPLAY_SERVER="127.0.0.1:%d" % sport, MELEE_NETPLAY_BIND="127.0.0.1", MELEE_NETPLAY_DELAY=str(a.delay), MELEE_PAD_BOT_EDGE="70",
                  MELEE_RB_LOG="0", MELEE_MODS_DIR=mods, MELEE_WINDOW_X="30000", MELEE_WINDOW_Y="30000", MELEE_WINDOW_W="640", MELEE_WINDOW_H="360",
                  MELEE_RUN_OWNER="envoy-s4", MELEE_SCRIPT_MS="5000")
    if a.netsim != "off":
        common["MELEE_NET_SIM"] = a.netsim
    if a.turbo:
        common["MELEE_NETPLAY_TURBO"] = a.turbo
    procs = {}

    def launch(side, script, console, extra):
        name = "ens4-%s-%s" % (a.tag, side)
        env = dict(common, MELEE_SCRIPT=script, MELEE_CONSOLE_PORT=str(console), MELEE_RB_HASHLOG="%s/runs/%s/hashes.csv" % (BUILD, name), **extra)
        os.makedirs("%s/runs/%s" % (BUILD, name), exist_ok=True)
        p = subprocess.Popen([BASH, ROOT + "/tools/port/run.sh", "--realtime", name, "--iso", iso], cwd=WT, env=env,
                             stdout=open("%s/%s.out" % (out_dir, side), "w"), stderr=subprocess.STDOUT)
        procs[side] = p
        pids[side] = p.pid
        open(out_dir + "/pids.txt", "w").write(json.dumps(pids))
        log("launched", side, "launcher pid", p.pid, "run", name)
        return p, name

    def stop_all():
        for side, p in procs.items():
            if p.poll() is None:
                log("launcher pid", p.pid, "still running; stopping that process tree by PID")
                kill(p.pid)
        srv.terminate()
        try:
            srv.wait(10)
        except Exception:
            kill(srv.pid)

    hx = dict(MELEE_WINDOW_X="30000", MELEE_NETPLAY_PORT=str(hport))
    if not a.no_bots:
        hx["MELEE_PAD_BOT"] = "0,0,%d" % (100 + rnd.randrange(50))
    if a.seed:
        hx["MELEE_NETPLAY_SEED"] = str(a.seed)
    hp, hname = launch("h", HERE + "/envoy/en_host.lua", hc, hx)
    host = Con(hc, "host")
    code = None
    t = time.time()
    while time.time() - t < 240:
        c = host.ev("gd.netplay().code")
        if c and len(c.strip('"')) == 4 and "?" not in c:
            code = c.strip('"')
            break
        time.sleep(2)
    if not code:
        log("no room code")
        stop_all()
        return 1
    log("room", code)
    gx = dict(MELEE_LAB_ROOM=code, MELEE_NETPLAY_PORT=str(gport))
    if not a.no_bots:
        gx["MELEE_PAD_BOT"] = "1,0,%d" % (200 + rnd.randrange(50))
    if a.poison:
        gx["MELEE_ENVOY_POISON"] = "1"
    if a.mods_poison:
        gx["MELEE_MODS_POISON"] = "1"
    gp, gname = launch("g", HERE + "/envoy/en_guest.lua", gc, gx)
    guest = Con(gc, "guest")
    log("consoles connected")
    result = {"tag": a.tag, "netsim": a.netsim, "games": [], "ok": False, "desync": False}

    def finish(code_):
        for c in (host, guest):
            try:
                c.cmd("quit")
            except Exception:
                pass
        time.sleep(4)
        for side in ("h", "g"):
            base = "%s/runs/ens4-%s-%s" % (BUILD, a.tag, side)
            for fn, dst in (("melee-pc.log", "%s.log" % ("host" if side == "h" else "guest")), ("hashes.csv", "%s.hashes.csv" % side)):
                try:
                    shutil.copy(os.path.join(base, fn), "%s/%s" % (out_dir, dst))
                except OSError as e:
                    log("missing", side, fn, e)
        stop_all()
        # the verdict from the logs: desyncs, rollbacks, the evaluator's own lines
        for who in ("host", "guest"):
            try:
                txt = open("%s/%s.log" % (out_dir, who), encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            result[who] = {"desync_lines": len(re.findall(r"DESYNC", txt)), "rollbacks": len(re.findall(r"rollback", txt)), "mods_sealed": len(re.findall(r"triggered program sealed|envoy mods: port=\d program sealed", txt)),
                           "refused": len(re.findall(r"REFUSED", txt))}
            if result[who]["desync_lines"]:
                result["desync"] = True
        json.dump(result, open(out_dir + "/result.json", "w"), indent=1)
        log("RESULT", "PASS" if result["ok"] and not result["desync"] else "INCOMPLETE/FAIL", json.dumps({k: v for k, v in result.items() if k != "games"}))
        return code_

    picks = [int(x) for x in a.picks.split(",")]
    host.cmd("envoynet auto %d" % picks[0])
    guest.cmd("envoynet auto %d" % picks[1])
    done_games = 0
    evidence_for = {}
    last_log = 0
    last_mods = 0
    t_end = time.time() + a.timeout
    log("in the lobby loop")
    prev = None
    while time.time() < t_end:
        hs, gs_ = parse_state(host.ev(STATE)), parse_state(guest.ev(STATE))
        if hs is None or gs_ is None:
            log("console lost")
            break
        keys = ("phase", "lobby", "game", "match", "frame", "scene", "env_open", "pick1", "pick2", "round", "refused", "word", "peer", "ready")
        line = "H %s | G %s" % ("|".join(str(hs[k]) for k in keys), "|".join(str(gs_[k]) for k in keys))
        if line != prev and time.time() - last_log > 1.5:
            log(line)
            prev = line
            last_log = time.time()
        for who, st, con in (("H", hs, host), ("G", gs_, guest)):
            if st["phase"] == "lobby":
                lp = st["lobby"]
                me = int(st["me"])
                if (lp == "char_blind" and st["locked"] != "true") or (lp in ("char_winner", "char_loser") and int(st["turn"]) == me):
                    con.ev('gd.netplay_act("char")')
                elif lp in ("strike", "ban", "pick") and int(st["turn"]) == me:
                    con.ev(FIRST_FREE)
                elif lp == "ready" and st["ready"] != "true" and st["env_open"] != "true":
                    con.ev('gd.netplay_act("ready",true)')
            if st["scene"] == "GS_RESULTS" and int(st["frame"]) > 200:
                con.cmd("input 1 %s 4" % ("START" if int(time.time()) % 2 else "A"))
        if hs["match"] == "true" and gs_["match"] == "true" and time.time() - last_mods > 5:
            last_mods = time.time()
            mh, mg = host.ev(MODS), guest.ev(MODS)
            modscsv.write("%.1f,%s,H,%s\n%.1f,%s,G,%s\n" % (time.time() - t0, hs["game"], mh, time.time() - t0, hs["game"], mg))
            modscsv.flush()
        if hs["match"] == "true" and gs_["match"] == "true" and int(hs["frame"]) > 180 and int(gs_["frame"]) > 180 and hs["game"] not in evidence_for:
            g_no = hs["game"]
            evidence_for[g_no] = True
            ev = {"game": g_no, "host_view": host.ev(BUILDS), "guest_view": guest.ev(BUILDS), "host_mods": host.ev(MODS), "guest_mods": guest.ev(MODS), "host_frame": hs["frame"], "guest_frame": gs_["frame"]}
            result["games"].append(ev)
            log("EVIDENCE game", g_no, json.dumps(ev))
        if hs["scene"] != "GS_VS" and gs_["scene"] != "GS_VS" and len(result["games"]) > done_games:
            done_games = len(result["games"])
            log("game", done_games, "over")
            if done_games >= a.games:
                result["ok"] = True
                time.sleep(3)
                return finish(0)
        if (a.poison or a.mods_poison) and hs["match"] == "true" and int(hs["frame"]) > 900:
            log("poison run: 900 frames in")
            time.sleep(10)
            result["ok"] = True
            return finish(0)
        if re.search(r"DESYNC", (hs["status"] or "") + (gs_["status"] or "")):
            result["desync"] = True
            log("DESYNC reported in the lobby status")
        time.sleep(1.2)
    log("timeout")
    return finish(1)


if __name__ == "__main__":
    sys.exit(main())
