#!/usr/bin/env python3
"""cpu_soak.py - two real netplay clients over loopback, CPU opponents in the match, then a verdict.

Envoy online stage 6 (docs/superpowers/plans/2026-10-08-envoy-online-stage6.md): is the retail CPU AI
identical on both peers through rollbacks? No server (direct connect on 127.0.0.1), both windows parked
offscreen, each human slot driven by MELEE_PAD_BOT, the host's scene extended with CPU slots through
MELEE_NETPLAY_CPUS (pc/platform/gw_netplay.c). The game's own confirmed-frame checksum log
(MELEE_RB_HASHLOG) is written by both peers and compared frame by frame; the first differing frame is
printed together with the "DESYNC" lines and the rollback counters of each log.

    cpu_soak.py NAME --secs 300 --cpus 20:1:9 --net-sim lag=50,jitter=20,loss=3
    cpu_soak.py NAME --secs 120 --cpus 20:1:9,9:2:9 --teams

Environment: GW_MELEE / GW_BUILD_ROOT select the build (default: the main checkout's _build); the disc comes
from GW_ISO_VANILLA (.env). Both children are stopped by numeric PID before this script exits.
Only two games run at a time. There is no server at all (direct connect on loopback).
"""
import argparse
import os
import re
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_WS = os.environ.get("GW_ROOT_MAIN", "E:/Projects/Melee Workspace")
GIT_BASH = os.environ.get("GIT_BASH", "C:/Program Files/Git/bin/bash.exe")


def free_port(start, kind):
    """First port >= start that binds on 127.0.0.1 (UDP for the netplay port, TCP for the console)."""
    for p in range(start, start + 400):
        s = socket.socket(socket.AF_INET, kind)
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            pass
        finally:
            s.close()
    sys.exit("no free port near %d" % start)


def read_env_file(path):
    out = {}
    try:
        for line in open(path, encoding="utf-8"):
            m = re.match(r"\s*(?:export\s+)?([A-Z0-9_]+)=(.*)", line)
            if m and not line.lstrip().startswith("#"):
                out[m.group(1)] = m.group(2).strip().strip('"')
    except OSError:
        pass
    return out


def ps(cmd):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
    return r.stdout.strip()


def pids_under(fragment):
    out = ps("Get-CimInstance Win32_Process -Filter \"Name='melee-pc.exe'\" | Where-Object { $_.ExecutablePath -like '*%s*' } "
             "| ForEach-Object { $_.ProcessId }" % fragment)
    return [int(x) for x in out.split() if x.isdigit()]


def kill(pid):
    subprocess.run(["taskkill", "/PID", str(int(pid)), "/F", "/T"], capture_output=True)


def console(port):
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=5)
        f = s.makefile("r", encoding="utf-8", errors="replace")
        f.readline()
        return (s, f)
    except OSError:
        return None


def con_cmd(sf, line):
    s, f = sf
    s.sendall((line + "\n").encode())
    out = []
    while True:
        l = f.readline()
        if not l:
            return out
        l = l.rstrip("\n")
        if l in (">>> ok", ">>> error"):
            return out
        out.append(l)


def hashes(path):
    out = {}
    try:
        for line in open(path):
            p = line.strip().split(",")
            if len(p) == 2 and p[0].lstrip("-").isdigit():
                out[int(p[0])] = p[1]
    except OSError:
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--secs", type=int, default=120)
    ap.add_argument("--cpus", default="", help="MELEE_NETPLAY_CPUS: ckind:color:level[,ckind:color:level]")
    ap.add_argument("--teams", action="store_true", help="humans on team 0, CPUs on team 1")
    ap.add_argument("--net-sim", default="", help="MELEE_NET_SIM, e.g. lag=50,jitter=20,loss=3 (empty: clean)")
    ap.add_argument("--delay", type=int, default=2)
    ap.add_argument("--stage", type=int, default=32, help="external stage id (32 = Final Destination)")
    ap.add_argument("--edge", type=int, default=70)
    ap.add_argument("--chars", default="2,2", help="host,guest CKind (default Fox,Fox)")
    ap.add_argument("--seed", type=int, default=100, help="pad bot seed base")
    ap.add_argument("--no-bots", action="store_true", help="human slots stand still")
    ap.add_argument("--host-env", action="append", default=[], help="K=V for the host only")
    ap.add_argument("--guest-env", action="append", default=[], help="K=V for the guest only")
    ap.add_argument("--both-env", action="append", default=[], help="K=V for both")
    ap.add_argument("--out", default=None, help="directory for logs (default <build root>/cpu_soak/<name>)")
    ap.add_argument("--turbo", default="off")
    ap.add_argument("--stocks", type=int, default=99)
    ap.add_argument("--minutes", type=int, default=60)
    a = ap.parse_args()

    melee = os.environ.get("GW_MELEE", MAIN_WS + "/melee")
    broot = os.environ.get("GW_BUILD_ROOT", MAIN_WS + "/_build")
    envf = read_env_file(MAIN_WS + "/.env")
    iso = os.environ.get("GW_ISO_VANILLA") or envf.get("GW_ISO_VANILLA")
    if not iso:
        sys.exit("no GW_ISO_VANILLA")
    out = a.out or (broot + "/cpu_soak/" + a.name)
    os.makedirs(out, exist_ok=True)
    runs = broot + "/runs"
    port = free_port(57000 + (os.getpid() % 900), socket.SOCK_DGRAM)  # a unique 57xxx UDP port: other lanes hold the pid-derived ones
    hc = free_port(57100 + (os.getpid() % 400), socket.SOCK_STREAM)
    gc = free_port(hc + 1, socket.SOCK_STREAM)

    base = dict(os.environ)
    base.update({
        "GW_MELEE": melee, "GW_BUILD_ROOT": broot, "GW_ISO_VANILLA": iso,
        "MELEE_SCENE": "mode=vs;at=match;p1=fox/c0/hu;p2=fox/c0/hu;stage=fd;time=0",
        "MELEE_NETPLAY_STOCKS": str(a.stocks), "MELEE_NETPLAY_MINUTES": str(a.minutes),
        "MELEE_NETPLAY_BIND": "127.0.0.1", "MELEE_NETPLAY_DELAY": str(a.delay),
        "MELEE_NETPLAY_STAGE": str(a.stage), "MELEE_VOLUME": "0", "MELEE_PAD_IGNORE_ADAPTER": "1",
        "MELEE_SKIP_INTRO": "1", "MELEE_PAD_BOT_EDGE": str(a.edge), "MELEE_RB_LOG": "0",
        "MELEE_WINDOW_X": "30000", "MELEE_WINDOW_Y": "30000", "MELEE_WINDOW_W": "640", "MELEE_WINDOW_H": "360",
        "MELEE_NETPLAY_TURBO": a.turbo,
    })
    nomods = broot + "/nomods"
    os.makedirs(nomods, exist_ok=True)
    base["MELEE_MODS_DIR"] = nomods
    if a.net_sim:
        base["MELEE_NET_SIM"] = a.net_sim
    for kv in a.both_env:
        k, v = kv.split("=", 1)
        base[k] = v
    chars = a.chars.split(",")
    tag_h, tag_g = a.name + "_h", a.name + "_g"
    envs = {}
    for who, cport, ck, mode in (("h", hc, chars[0], "host:%d" % port), ("g", gc, chars[1], "join:127.0.0.1:%d" % port)):
        tag = tag_h if who == "h" else tag_g
        e = dict(base)
        e["MELEE_NETPLAY"] = mode
        e["MELEE_NETPLAY_CHAR"] = ck
        e["MELEE_CONSOLE_PORT"] = str(cport)
        e["MELEE_RB_HASHLOG"] = out + "/%s.hash" % tag
        if who == "h" and a.cpus:
            e["MELEE_NETPLAY_CPUS"] = a.cpus
            if a.teams:
                e["MELEE_NETPLAY_TEAMS"] = "1"
        if not a.no_bots:
            e["MELEE_PAD_BOT"] = "%d,0,%d" % (0 if who == "h" else 1, a.seed + (0 if who == "h" else 1))
        for kv in (a.host_env if who == "h" else a.guest_env):
            k, v = kv.split("=", 1)
            e[k] = v
        envs[who] = e

    def launch(who, tag):
        cmd = [GIT_BASH, "-c", 'cd "%s" && exec bash tools/port/run.sh --realtime %s --iso "$GW_ISO_VANILLA"' % (MAIN_WS, tag)]
        lf = open(out + "/%s.out" % tag, "w")
        return subprocess.Popen(cmd, env=envs[who], stdout=lf, stderr=subprocess.STDOUT)

    started = []
    sh = sg = None
    try:
        ph = launch("h", tag_h)
        started.append(ph)
        time.sleep(6)
        pg = launch("g", tag_g)
        started.append(pg)
        t0 = time.time()
        deadline = time.time() + 240
        while time.time() < deadline and not (sh and sg):
            if ph.poll() is not None or pg.poll() is not None:
                break
            sh = sh or console(hc)
            sg = sg or console(gc)
            time.sleep(1)
        t_start = time.time()
        print("clients up after %.0f s; soaking %d s" % (t_start - t0, a.secs))
        while time.time() - t_start < a.secs and ph.poll() is None and pg.poll() is None:
            time.sleep(2)
        probe = ('= (function() local t={} for _,p in ipairs(gd.players()) do t[#t+1]=string.format('
                 '"P%d cpu=%s team=%d stocks=%d falls=%d pct=%.0f x=%.1f act=%d",p.port,tostring(p.cpu),p.team,p.stocks,p.falls,'
                 'p.percent,p.x,p.action) end return table.concat(t," | ").." | items="..#gd.items() end)()')
        for who_, s_ in (("host", sh), ("guest", sg)):
            try:
                if s_:
                    print(who_, "players:", " ".join(con_cmd(s_, probe)))
            except Exception as ex:
                print(who_, "probe failed", ex)
        for s_ in (sh, sg):
            try:
                if s_:
                    con_cmd(s_, "= gd.quit()")
            except Exception:
                pass
        time.sleep(5)
    finally:
        for frag in (tag_h, tag_g):
            for pid in pids_under(frag):
                kill(pid)
        for p in started:
            if p.poll() is None:
                kill(p.pid)
        time.sleep(1)

    summary = {}
    for who, tag in (("h", tag_h), ("g", tag_g)):
        log = runs + "/" + tag + "/melee-pc.log"
        txt = ""
        try:
            txt = open(log, encoding="utf-8", errors="replace").read()
            open(out + "/%s.log" % tag, "w", encoding="utf-8").write(txt)
        except OSError:
            pass
        desyncs = re.findall(r"netplay: DESYNC at frame (-?\d+)", txt)
        roll = re.findall(r"rb: [^\n]*rollback[^\n]*", txt)
        summary[who] = {"log_bytes": len(txt), "desync": desyncs[:3], "ndesync": len(desyncs),
                        "rb_last": roll[-1][:200] if roll else "",
                        "crash": bool(re.search(r"crash|exception|EXCEPTION|assert", txt[-4000:]))}
    h, g = hashes(out + "/%s.hash" % tag_h), hashes(out + "/%s.hash" % tag_g)
    common = sorted(set(h) & set(g))
    first = next((f for f in common if h[f] != g[f]), None)
    print("\n== RESULT %s ==" % a.name)
    print("hash frames: host %d guest %d common %d (last %s)" % (len(h), len(g), len(common), common[-1] if common else None))
    print("first differing confirmed frame: %s" % first)
    for who in "hg":
        print(who, summary[who])
    ok = first is None and not summary["h"]["ndesync"] and not summary["g"]["ndesync"] and len(common) > 0
    print("VERDICT:", "CLEAN" if ok else "DIVERGED/ABNORMAL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
