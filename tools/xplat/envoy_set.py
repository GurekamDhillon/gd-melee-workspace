#!/usr/bin/env python3
"""run_set.py - two REAL clients over loopback play an online Envoy set through the real menus and lobby (the local matchmaking server on 127.0.0.1
only: never the public one), driven over each client's console. Loopback only. Everything is recorded in envoy-net/runs/<tag>/.

  python run_set.py <tag> [--games 3] [--envoy on|off] [--netsim lag=40,jitter=10,loss=2] [--poison] [--tamper] [--delay 2]
                    [--old-guest-exe PATH] [--picks 1,2]

--poison   the guest's slot-1 record word is flipped after the apply (MELEE_ENVOY_POISON=1): the rollback hash must report a desync
--tamper   after the lobby, the guest restages a different build (console: envoynet tamper): the host must refuse the match with a clear message
"""
import argparse, os, re, socket, subprocess, sys, time, random, shutil, json

HERE = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
ROOT = os.environ.get("GW_ROOT_ENV", "E:/Projects/Melee Workspace")
BUILD = os.environ["GW_BUILD_ROOT"].replace("\\", "/")
WT = os.environ["GW_MELEE"].replace("\\", "/")
BASH = "C:/Program Files/Git/bin/bash.exe"
OUT = ROOT + "/_build/xplat/envoy_sets"
LINUX_DIR = "outD"
WSL_DISC = "/mnt/c/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
def _wsl_ip():
    e = dict(os.environ); e["MSYS_NO_PATHCONV"] = "1"
    out = subprocess.run(["wsl", "-d", "Debian", "--", "bash", "-lc", "ip -4 addr show eth0"], env=e, capture_output=True, text=True).stdout
    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", out)
    return m.group(1) if m else "127.0.0.1"
WSL_IP = _wsl_ip()

def load_env():
    env = dict(os.environ)
    for line in open(ROOT + "/.env", encoding="utf-8", errors="replace"):
        m = re.match(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"?([^"\n]*)"?\s*$', line)
        if m: env[m.group(1)] = m.group(2)
    env["GW_MELEE"] = WT
    env["GW_BUILD_ROOT"] = BUILD
    return env

def free_gb():
    out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB"], capture_output=True, text=True).stdout
    return float(out.strip().replace(",", "."))

class Con:
    def __init__(self, port, name, tries=240, host_addr="127.0.0.1"):
        self.name = name
        for _ in range(tries):
            try:
                self.s = socket.create_connection((host_addr, port), timeout=60); break
            except OSError: time.sleep(1)
        else: raise SystemExit("no console on %d" % port)
        self.f = self.s.makefile("r", encoding="utf-8", errors="replace"); self.f.readline()
    def cmd(self, c):
        self.s.sendall((c + "\n").encode()); out = []
        while True:
            l = self.f.readline()
            if not l: raise EOFError(self.name)
            l = l.rstrip("\n")
            if l in (">>> ok", ">>> error"): return [o for o in out if not o.startswith("> ")], l == ">>> ok"
            out.append(l)
    def ev(self, e):
        try:
            out, ok = self.cmd("= " + e)
        except (EOFError, OSError): return None
        return out[-1].strip() if ok and out else None

STATE = ('(function() local np=gd.netplay() local e=np.envoy local m=gd.match() local me=np.players[np.me+1] '
         'return table.concat({np.phase,np.lobby,np.game,np.turn,np.me,tostring(m.active),m.frame,gd.scene().name,tostring(e.on),tostring(e.open),e.picks[1],e.picks[2],e.round,e.refused,e.word,e.peer_word,tostring(me.locked),tostring(me.ready),np.status},"|") end)()')
BUILDS = ('(function() local b=gd.netbuild() local out={b.word,tostring(b.applied)} for i=1,2 do local s=b.slots[i] '
          'out[#out+1]=table.concat({i,tostring(s.active),tostring(s.digest),tostring(s.applied_ops),tostring(s.applied_nops),tostring(s.live),tostring(s.rules),tostring(s.rules_word)},",") '
          'if s.values then local ks={} for k,v in pairs(s.values) do ks[#ks+1]=k.."="..string.format("%.4f",v) end table.sort(ks) out[#out+1]=table.concat(ks,";") end end return table.concat(out,"|") end)()')
FIRST_FREE = ('(function() local np=gd.netplay() for i,st in ipairs(np.stages) do if st==0 then return gd.netplay_act("stage",i) end end return false end)()')

def parse_state(s):
    if not s: return None
    p = s.strip('"').split("|")
    if len(p) < 19: return None
    k = ["phase", "lobby", "game", "turn", "me", "match", "frame", "scene", "env_on", "env_open", "pick1", "pick2", "round", "refused", "word", "peer", "locked", "ready"]
    d = dict(zip(k, p[:18])); d["status"] = "|".join(p[18:]); return d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag"); ap.add_argument("--games", type=int, default=3); ap.add_argument("--envoy", default="on")
    ap.add_argument("--netsim", default="off"); ap.add_argument("--poison", action="store_true"); ap.add_argument("--tamper", action="store_true")
    ap.add_argument("--delay", type=int, default=2); ap.add_argument("--picks", default="1,2"); ap.add_argument("--timeout", type=int, default=1500)
    ap.add_argument("--old-guest-exe", default="")
    a = ap.parse_args()
    out_dir = "%s/%s" % (OUT, a.tag); shutil.rmtree(out_dir, ignore_errors=True); os.makedirs(out_dir, exist_ok=True)
    trace = open(out_dir + "/trace.txt", "w", encoding="utf-8")
    def log(*x):
        line = "[%6.1f] %s" % (time.time() - t0, " ".join(str(i) for i in x)); print(line, flush=True); trace.write(line + "\n"); trace.flush()
    t0 = time.time()
    if free_gb() < 2.5: print("not enough free memory"); return 2
    env0 = load_env(); iso = env0["GW_ISO_VANILLA"]
    rnd = random.Random(); sport = 51900 + rnd.randrange(80); hc = 53600 + rnd.randrange(20); gc = hc + 20
    pids = {}
    gw_ip = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-NetIPAddress -InterfaceAlias 'vEthernet (WSL*' -AddressFamily IPv4 | Select-Object -First 1).IPAddress"], capture_output=True, text=True).stdout.strip()
    srv = subprocess.Popen([sys.executable, ROOT + "/tools/netplay/server/gdmelee_server.py", "--bind", "0.0.0.0", "--port", str(sport)], stdout=open(out_dir + "/server.log", "w"), stderr=subprocess.STDOUT)
    pids["server"] = srv.pid
    open(out_dir + "/pids.txt", "w").write(json.dumps(pids))
    log("server pid", srv.pid, "udp", sport, "consoles", hc, gc)
    common = dict(env0, MELEE_SCENE="mode=menu", MELEE_SKIP_INTRO="1", MELEE_VOLUME="0", MELEE_PAD_IGNORE_ADAPTER="1",
                  MELEE_NETPLAY_SERVER="%s:%d" % (gw_ip, sport), MELEE_NETPLAY_DELAY=str(a.delay), MELEE_PAD_BOT_EDGE="70", MELEE_RB_LOG="0")
    win_mods = ROOT + ("/_build/xplat/mods" if a.envoy == "on" else "/_build/nomods")
    lin_mods = "/mnt/h/xpmods" if a.envoy == "on" else "/mnt/h/xpnomods"
    if a.netsim != "off": common["MELEE_NET_SIM"] = a.netsim
    def launch(side, script, console, extra):
        name = "en-%s-%s" % (a.tag, side)
        if side == "h":   # Windows
            env = dict(common, MELEE_SCRIPT=script, MELEE_CONSOLE_PORT=str(console), MELEE_MODS_DIR=win_mods, MELEE_RB_HASHLOG="%s/runs/%s/hashes.csv" % (BUILD, name), **extra)
            os.makedirs("%s/runs/%s" % (BUILD, name), exist_ok=True)
            p = subprocess.Popen([BASH, ROOT + "/tools/port/run.sh", "--realtime", name, "--iso", iso], cwd=WT, env=env, stdout=open("%s/%s.out" % (out_dir, side), "w"), stderr=subprocess.STDOUT)
        else:             # Linux, in the WSL rootfs
            kv = dict(common, MELEE_SCRIPT=script, MELEE_CONSOLE_PORT=str(console), MELEE_MODS_DIR=lin_mods, **extra)
            kv = {k: v for k, v in kv.items() if k.startswith("MELEE_") and k not in ("MELEE_RB_HASHLOG",)}
            kvs = " ".join("'%s=%s'" % (k, v.replace("'", "")) for k, v in kv.items())
            inner = ("cd ~/lb2; export MELEE_VANILLA_ISO='%s'; ./enterD.sh env bash /mnt/h/wsD/tools/xplat/run_linux_net.sh /mnt/h/%s/linux %s %d %s"
                     % (WSL_DISC, LINUX_DIR, name, a.timeout + 300, kvs))
            e2 = dict(os.environ); e2["MSYS_NO_PATHCONV"] = "1"
            p = subprocess.Popen(["wsl", "-d", "Debian", "--", "bash", "-lc", inner], env=e2, stdout=open("%s/%s.out" % (out_dir, side), "w"), stderr=subprocess.STDOUT)
        pids[side] = p.pid; open(out_dir + "/pids.txt", "w").write(json.dumps(pids)); log("launched", side, "launcher pid", p.pid, "run", name)
        return p, name
    hp, hname = launch("h", HERE + "/envoy/en_host.lua", hc, dict(MELEE_PAD_BOT="0,0,%d" % (100 + rnd.randrange(50)), MELEE_WINDOW_X="20", MELEE_WINDOW_Y="20", MELEE_WINDOW_W="960", MELEE_WINDOW_H="540"))
    time.sleep(6)
    gx = dict(MELEE_PAD_BOT="1,0,%d" % (200 + rnd.randrange(50)), MELEE_WINDOW_X="20", MELEE_WINDOW_Y="20", MELEE_WINDOW_W="960", MELEE_WINDOW_H="540")
    if a.poison: gx["MELEE_ENVOY_POISON"] = "1"
    gp, gname = launch("g", "/mnt/h/wsD/tools/xplat/envoy/en_guest.lua", gc, gx)
    host, guest = Con(hc, "host"), Con(gc, "guest", host_addr=WSL_IP)
    log("consoles connected")
    result = {"tag": a.tag, "games": [], "ok": False}
    def finish(code):
        for c in (host, guest):
            try: c.cmd("quit")
            except Exception: pass
        time.sleep(4)
        for side in ("h", "g"):
            if side == "h": base = "%s/runs/en-%s-h" % (BUILD, a.tag)
            else: base = "//wsl.localhost/Debian/home/gd/lb2/%s/xpn-en-%s-g" % (LINUX_DIR, a.tag)
            for fn, dst in (("melee-pc.log", "%s.log" % side), ("hashes.csv", "%s.hashes.csv" % side)):
                try: shutil.copy(os.path.join(base, fn), "%s/%s" % (out_dir, dst))
                except OSError as e: log("missing", side, fn, e)
        for nm in ("h", "g"):
            p = hp if nm == "h" else gp
            if p.poll() is None:
                log("bash pid", p.pid, "still running; stopping that process tree by PID")
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
        srv.terminate()
        try: srv.wait(10)
        except Exception: subprocess.run(["taskkill", "/PID", str(srv.pid), "/F"], capture_output=True)
        json.dump(result, open(out_dir + "/result.json", "w"), indent=1)
        log("RESULT", "PASS" if result["ok"] else "INCOMPLETE/FAIL", json.dumps({k: v for k, v in result.items() if k != "games"}))
        return code
    # ---- connect
    code = None; t = time.time()
    while time.time() - t < 240:
        c = host.ev("gd.netplay().code")
        if c and len(c.strip('"')) == 4 and "?" not in c: code = c.strip('"'); break
        time.sleep(2)
    if not code: log("no room code"); return finish(1)
    log("room", code)
    while time.time() - t < 400 and guest.ev("gd.menu().screen") != "JOIN ROOM": time.sleep(2)
    guest.ev('gd.netplay_act("code","%s")' % code)
    picks = [int(x) for x in a.picks.split(",")]
    host.cmd("envoynet auto %d" % picks[0]); guest.cmd("envoynet auto %d" % picks[1])
    done_games = 0; evidence_for = {}; tampered = False; last_log = 0; t_end = time.time() + a.timeout
    log("in the lobby loop")
    prev = None
    while time.time() < t_end:
        hs, gs_ = parse_state(host.ev(STATE)), parse_state(guest.ev(STATE))
        if hs is None or gs_ is None: log("console lost"); break
        line = "H %s | G %s" % ("|".join(str(hs[k]) for k in ("phase", "lobby", "game", "match", "frame", "scene", "env_open", "pick1", "pick2", "round", "refused", "word", "peer", "ready")),
                                 "|".join(str(gs_[k]) for k in ("phase", "lobby", "game", "match", "frame", "scene", "env_open", "pick1", "pick2", "round", "refused", "word", "peer", "ready")))
        if line != prev and time.time() - last_log > 1.5: log(line); prev = line; last_log = time.time()
        for who, st, con in (("H", hs, host), ("G", gs_, guest)):
            if st["phase"] == "lobby":
                lp = st["lobby"]; me = int(st["me"])
                if (lp == "char_blind" and st["locked"] != "true") or (lp in ("char_winner", "char_loser") and int(st["turn"]) == me): con.ev('gd.netplay_act("char")')
                elif lp in ("strike", "ban", "pick") and int(st["turn"]) == me: con.ev(FIRST_FREE)
                elif lp == "ready" and st["ready"] != "true" and st["env_open"] != "true": con.ev('gd.netplay_act("ready",true)')
            elif st["phase"] not in ("working", "connected", "running") and st["match"] != "true" and st["scene"] not in ("GS_FRONTEND",):
                pass
            if st["scene"] == "GS_RESULTS" and int(st["frame"]) > 200:
                con.cmd("input 1 %s 4" % ("START" if int(time.time()) % 2 else "A"))       # the results screens want START / A
        if a.tamper and not tampered and hs["phase"] == "lobby" and gs_["phase"] == "lobby" and hs["env_on"] == "true" and hs["word"] != "00000000" and gs_["word"] != "00000000":
            time.sleep(3); log("TAMPER: the guest restages a different build"); guest.cmd("envoynet tamper"); tampered = True
        if a.envoy != "on" and int(hs["refused"]) > 0:
            result["no_mod"] = {"host_refused": hs["refused"], "host_status": hs["status"], "guest_status": gs_["status"], "match_started": hs["match"]}
            log("NO-MOD result", json.dumps(result["no_mod"])); time.sleep(4); result["ok"] = True; return finish(0)
        if a.tamper and tampered and (int(hs["refused"]) > 0 or int(gs_["refused"]) > 0):
            result["tamper"] = {"host_refused": hs["refused"], "guest_refused": gs_["refused"], "host_status": hs["status"], "guest_status": gs_["status"], "match_started": hs["match"], "words": [hs["word"], gs_["word"]]}
            log("TAMPER result", json.dumps(result["tamper"])); time.sleep(5); result["ok"] = True; return finish(0)
        if hs["match"] == "true" and gs_["match"] == "true" and int(hs["frame"]) > 180 and int(gs_["frame"]) > 180 and hs["game"] not in evidence_for:
            g_no = hs["game"]; evidence_for[g_no] = True
            ev = {"game": g_no, "host_view": host.ev(BUILDS), "guest_view": guest.ev(BUILDS), "host_frame": hs["frame"], "guest_frame": gs_["frame"]}
            result["games"].append(ev); log("EVIDENCE game", g_no, json.dumps(ev))
        if hs["scene"] != "GS_VS" and gs_["scene"] != "GS_VS" and len(result["games"]) > done_games:
            done_games = len(result["games"]); log("game", done_games, "over")
            if done_games >= a.games: result["ok"] = True; time.sleep(3); return finish(0)
        if a.poison and hs["match"] == "true" and int(hs["frame"]) > 600:
            log("poison run: 600 frames in"); time.sleep(10); result["ok"] = True; return finish(0)
        time.sleep(1.2)
    log("timeout")
    return finish(1)

if __name__ == "__main__":
    sys.exit(main())
