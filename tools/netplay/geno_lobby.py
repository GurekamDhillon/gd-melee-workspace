#!/usr/bin/env python3
"""geno_lobby.py - Geno slice 7 through the REAL lobby: the Atlas menu, a room code, a pick of a define, a set of games.

    python tools/netplay/geno_lobby.py NAME --host-ck 122 --guest-ck 122 [--mods-host DIR] [--mods-guest DIR] [--games 2]
           [--net-sim "lag=60,jitter=15,loss=5"] [--timeout 1500] [--expect play|refuse] [--exe PATH]

geno_pair.py plays the scripted (boot-time) path; this one walks tools/netplay/geno_np.lua through ONLINE > Host a Room /
Join a Room on loopback (a matchmaking server of our own on 127.0.0.1, MELEE_NETPLAY_BIND=127.0.0.1, windows parked at
30000,30000), picks the given fighters in the lobby with gd.netplay_act("char", ck), plays --games games with the fuzz pad bot
and the coverage observer, and reads the verdict from the logs:

  play    both sides logged "game N started" for every game, no "DESYNC", the confirmed-frame checksums agree
  refuse  a side logged "GENOLOBBY pick refused: <reason>" (the reason is printed), or no match ever started

Both games are stopped by numeric PID at the end; the server is stopped. Results: <build root>/net/NAME/.
"""
import argparse, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from np_drive import Console  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MAIN_ROOT = os.environ.get("GW_ROOT_ENV", "E:/Projects/Melee Workspace")
HOST_PORT, GUEST_PORT = 54831, 54832  # TCP console ports; the lane's UDP range is 54700-54999


def ps_hash(d):
    return "@{" + ";".join("%s='%s'" % (k, str(v).replace("'", "''")) for k, v in d.items()) + "}"


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def hashes(path):
    out = {}
    for line in read(path).splitlines():
        p = line.strip().split(",")
        if len(p) == 2 and p[0].lstrip("-").isdigit():
            out[int(p[0])] = p[1]
    return out


def kill(pid):
    subprocess.run(["powershell", "-NoProfile", "-Command", "Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % pid],
                   capture_output=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("name")
    ap.add_argument("--host-ck", type=int, required=True)
    ap.add_argument("--guest-ck", type=int, required=True)
    ap.add_argument("--mods-host", default="")
    ap.add_argument("--mods-guest", default="")
    ap.add_argument("--games", type=int, default=1)
    ap.add_argument("--net-sim", default="off")
    ap.add_argument("--timeout", type=int, default=1500, help="seconds for the whole run")
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--stocks", default="2")
    ap.add_argument("--minutes", default="2")
    ap.add_argument("--expect", default="play", choices=("play", "refuse"))
    ap.add_argument("--exe", default="")
    ap.add_argument("--disc", default="vanilla")
    a = ap.parse_args()

    build_root = os.environ.get("GW_BUILD_ROOT")
    if not build_root:
        sys.exit("set GW_BUILD_ROOT first")
    exe = os.path.abspath(a.exe or os.path.join(build_root, "melee-pc.exe"))
    exe_dir = os.path.dirname(exe)
    out = os.path.join(build_root, "net", a.name)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    sand = {"host": os.path.join(exe_dir, "runs", "np_host"), "guest": os.path.join(exe_dir, "runs", "np_guest")}
    for d in sand.values():
        os.makedirs(d, exist_ok=True)
        for f in ("hashes.csv", "melee-pc.log"):
            try:
                os.remove(os.path.join(d, f))
            except OSError:
                pass
    script = os.path.join(HERE, "geno_np.lua")

    base = {"MELEE_NETPLAY_BIND": "127.0.0.1", "MELEE_WINDOW_X": "30000", "MELEE_WINDOW_Y": "30000", "MELEE_VOLUME": "0",
            "MELEE_PAD_IGNORE_ADAPTER": "1", "MELEE_RB_LOG": "0", "MELEE_PAD_BOT_MODE": "fuzz", "MELEE_PAD_BOT_EDGE": "62",
            "MELEE_LAB_GAMES": str(a.games), "MELEE_SCRIPT": script,
            "MELEE_NETPLAY_STOCKS": a.stocks, "MELEE_NETPLAY_MINUTES": a.minutes}
    host = dict(base, MELEE_CONSOLE_PORT=str(HOST_PORT), MELEE_LAB_ROLE="host", MELEE_LAB_CK=str(a.host_ck),
                MELEE_PAD_BOT="0,0,%d" % a.seed, MELEE_RB_HASHLOG=os.path.join(sand["host"], "hashes.csv").replace("\\", "/"))
    guest = dict(base, MELEE_CONSOLE_PORT=str(GUEST_PORT), MELEE_LAB_ROLE="guest", MELEE_LAB_CK=str(a.guest_ck),
                 MELEE_PAD_BOT="1,0,%d" % (a.seed + 1), MELEE_RB_HASHLOG=os.path.join(sand["guest"], "hashes.csv").replace("\\", "/"))
    if a.mods_host:
        host["MELEE_MODS_DIR"] = os.path.abspath(a.mods_host)
    if a.mods_guest:
        guest["MELEE_MODS_DIR"] = os.path.abspath(a.mods_guest)

    import socket

    def free_udp(start):
        for p in range(start, start + 300):
            t = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                t.bind(("0.0.0.0", p))
                t.close()
                return p
            except OSError:
                t.close()
        return start

    sport = free_udp(54900 + (os.getpid() % 100))
    hport = free_udp(54700 + (os.getpid() % 40) * 2)
    host["MELEE_NETPLAY_PORT"] = str(hport)
    guest["MELEE_NETPLAY_PORT"] = str(hport + 1)
    srv = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "netplay", "server", "gdmelee_server.py"),
                            "--bind", "127.0.0.1", "--port", str(sport)], stdout=open(os.path.join(out, "server.log"), "w"),
                           stderr=subprocess.STDOUT)
    time.sleep(1.5)
    pids = []
    try:
        cmd = ("& '%s' -Menu -HostDevice gc -GuestDevice keyboard -Disc %s -NetSim '%s' -Label '%s' -Exe '%s' "
               "-Server '127.0.0.1:%d' -EnvHost %s -EnvGuest %s" %
               (os.path.join(MAIN_ROOT, "_build", "netplay_local.ps1").replace("'", "''"), a.disc, a.net_sim.replace("'", "''"),
                a.name, exe.replace("'", "''"), sport, ps_hash(host), ps_hash(guest)))
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], capture_output=True, text=True)
        pids = [int(x) for x in re.findall(r"pid (\d+)", r.stdout)]
        print("started pids", pids)
        t0 = time.time()
        hc, gc = Console(HOST_PORT, "host"), Console(GUEST_PORT, "guest")
        if not (hc.connect(time.time() + 120) and gc.connect(time.time() + 120)):
            print("FAIL: no console socket")
            return 1
        code = None
        while time.time() - t0 < 300 and code is None:
            m = re.search(r"ROOMCODE (\w{4})", read(os.path.join(sand["host"], "melee-pc.log")))
            if m:
                code = m.group(1)
            time.sleep(1)
        if code is None:
            print("FAIL: the host never logged a room code")
            return 1
        print("room", code)
        while time.time() - t0 < 300:
            if gc.value("gd.menu().screen") == "JOIN ROOM":
                break
            time.sleep(1)
        gc.value('gd.netplay_act("code", "%s")' % code)
        done = False
        while time.time() - t0 < a.timeout and not done:
            time.sleep(5)
            lh, lg = read(os.path.join(sand["host"], "melee-pc.log")), read(os.path.join(sand["guest"], "melee-pc.log"))
            both_done = "SET DONE" in lh and "SET DONE" in lg
            refused = "GENOLOBBY pick refused" in lh or "GENOLOBBY pick refused" in lg
            failed = "connection failed" in lh or "connection failed" in lg
            done = both_done or refused or failed
        time.sleep(3)
    finally:
        for pid in pids:
            kill(pid)
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except subprocess.TimeoutExpired:
            srv.kill()
        time.sleep(2)
    res = {}
    for side in ("host", "guest"):
        d = os.path.join(out, side)
        os.makedirs(d, exist_ok=True)
        for fn in ("melee-pc.log", "hashes.csv"):
            try:
                shutil.copy2(os.path.join(sand[side], fn), d)
            except OSError:
                pass
        res[side] = read(os.path.join(d, "melee-pc.log"))
    hh, hg = hashes(os.path.join(out, "host", "hashes.csv")), hashes(os.path.join(out, "guest", "hashes.csv"))
    shared = sorted(hh.keys() & hg.keys())
    bad = [f for f in shared if hh[f] != hg[f]]
    s = {"name": a.name, "host_ck": a.host_ck, "guest_ck": a.guest_ck, "net_sim": a.net_sim, "games_wanted": a.games}
    s["games_started"] = {k: len(re.findall(r"GENOLOBBY \w+: game \d+ started", v)) for k, v in res.items()}
    s["games_ended"] = {k: len(re.findall(r"GENOLOBBY \w+: game \d+ ended", v)) for k, v in res.items()}
    s["desyncs"] = {k: len(re.findall(r"netplay: DESYNC", v)) for k, v in res.items()}
    s["confirmed_frames"] = {"host": len(hh), "guest": len(hg), "shared": len(shared), "mismatching": len(bad)}
    s["refusals"] = {k: re.findall(r"GENOLOBBY pick refused: [^\n]*", v)[:2] for k, v in res.items()}
    s["lobby_notes"] = {k: re.findall(r"GENOLOBBY \w+: common fighters[^\n]*", v)[:2] for k, v in res.items()}
    s["define_lines"] = {k: re.findall(r"native define kind \d+ loaded[^\n]*|mexid: [^\n]*not in common[^\n]*", v)[:4] for k, v in res.items()}
    s["coverage"] = {k: re.findall(r"GENOCOV f=\d+ p\d moves=\d+ geno=\d+ luafaults=\S+ stocks=\S+ pct=\S+", v)[-2:] for k, v in res.items()}
    s["crash"] = {k: bool(re.search(r"ASSERT|FATAL|crash", v)) for k, v in res.items()}
    ok = (min(s["games_started"].values()) >= a.games and not any(s["desyncs"].values()) and not bad and len(shared) > 600)
    refused = any(s["refusals"].values())
    s["verdict"] = "play" if ok else ("refuse" if refused or max(s["games_started"].values()) == 0 else "FAIL")
    with open(os.path.join(out, "summary.json"), "w") as f:
        json.dump(s, f, indent=1)
    print(json.dumps(s, indent=1))
    return 0 if s["verdict"] == a.expect else 1


if __name__ == "__main__":
    sys.exit(main())
