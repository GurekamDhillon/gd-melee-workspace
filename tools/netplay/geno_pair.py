#!/usr/bin/env python3
"""geno_pair.py - two local clients, one online match, Geno defines (slice 7), and a verdict from the logs.

    python tools/netplay/geno_pair.py NAME --host-ck 123 --guest-ck 123 [--mods-host DIR] [--mods-guest DIR]
           [--net-sim "lag=60,jitter=15,loss=5"] [--seconds 120] [--seed 100] [--stocks 4] [--minutes 8]
           [--stage 31] [--delay 2] [--expect play|refuse] [--exe PATH] [--disc vanilla]

Starts the HOST (P1) and the GUEST (P2) through _build/netplay_local.ps1 on loopback only (MELEE_NETPLAY_BIND=127.0.0.1, a
random port, windows parked off screen at 30000,30000), each driven by MELEE_PAD_BOT and writing the confirmed-frame checksum
log (MELEE_RB_HASHLOG). Both are closed by numeric PID after --seconds. Then it reads what the games logged and prints one
line of facts and a verdict:

  play    a match started on both sides, no "DESYNC", the confirmed-frame checksums of the two sides agree over every frame
          both have, and the match ran at least --min-frames confirmed frames
  refuse  no match started, and a log line explains why (the reason is printed)

Nothing here touches the public matchmaking server: the scripted path dials the other copy directly. Results (logs, hash
logs, a summary.json) are kept in <build root>/net/NAME/. Exit status 0 = the verdict is what --expect said.
"""
import argparse, json, os, re, shutil, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAIN_ROOT = os.environ.get("GW_ROOT_ENV", "E:/Projects/Melee Workspace")


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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("name")
    ap.add_argument("--host-ck", type=int, required=True)
    ap.add_argument("--guest-ck", type=int, required=True)
    ap.add_argument("--mods-host", default="")
    ap.add_argument("--mods-guest", default="")
    ap.add_argument("--net-sim", default="off")
    ap.add_argument("--seconds", type=int, default=120)
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--stocks", default="4")
    ap.add_argument("--minutes", default="8")
    ap.add_argument("--stage", default="31")
    ap.add_argument("--delay", type=int, default=2)
    ap.add_argument("--edge", default="62", help="MELEE_PAD_BOT_EDGE (Battlefield 62, Final Destination 70)")
    ap.add_argument("--expect", default="play", choices=("play", "refuse"))
    ap.add_argument("--min-frames", type=int, default=600)
    ap.add_argument("--exe", default="")
    ap.add_argument("--disc", default="vanilla")
    ap.add_argument("--no-bot", action="store_true")
    ap.add_argument("--no-cov", action="store_true", help="do not load the coverage observer (tools/netplay/geno_cov.lua)")
    ap.add_argument("--extra-env", default="", help="KEY=VAL,KEY=VAL for both sides")
    a = ap.parse_args()

    build_root = os.environ.get("GW_BUILD_ROOT")
    if not build_root:
        sys.exit("set GW_BUILD_ROOT (the lane's build root) first")
    exe = a.exe or os.path.join(build_root, "melee-pc.exe")
    exe_dir = os.path.dirname(os.path.abspath(exe))
    out = os.path.join(build_root, "net", a.name)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    port = 51800 + (os.getpid() % 150)

    common = {"MELEE_NETPLAY_BIND": "127.0.0.1", "MELEE_WINDOW_X": "30000", "MELEE_WINDOW_Y": "30000", "MELEE_VOLUME": "0",
              "MELEE_PAD_IGNORE_ADAPTER": "1", "MELEE_PAD_BOT_EDGE": a.edge, "MELEE_NETPLAY_STAGE": a.stage,
              "MELEE_NETPLAY_STOCKS": a.stocks, "MELEE_NETPLAY_MINUTES": a.minutes, "MELEE_RB_LOG": "0"}
    for kv in filter(None, a.extra_env.split(",")):
        k, v = kv.split("=", 1)
        common[k] = v
    sand = {"np_host": os.path.join(exe_dir, "runs", "np_host"), "np_guest": os.path.join(exe_dir, "runs", "np_guest")}
    host = dict(common, MELEE_RB_HASHLOG=os.path.join(sand["np_host"], "hashes.csv").replace("\\", "/"))
    guest = dict(common, MELEE_RB_HASHLOG=os.path.join(sand["np_guest"], "hashes.csv").replace("\\", "/"))
    if a.mods_host:
        host["MELEE_MODS_DIR"] = os.path.abspath(a.mods_host)
    if a.mods_guest:
        guest["MELEE_MODS_DIR"] = os.path.abspath(a.mods_guest)
    cov = os.path.join(ROOT, "tools", "netplay", "geno_cov.lua")
    if not a.no_cov:
        host["MELEE_SCRIPT"] = cov
        guest["MELEE_SCRIPT"] = cov
    if not a.no_bot:
        host["MELEE_PAD_BOT"] = "0,0,%d" % a.seed
        guest["MELEE_PAD_BOT"] = "1,0,%d" % (a.seed + 1)
    for d in sand.values():
        os.makedirs(d, exist_ok=True)
        for f in ("hashes.csv", "melee-pc.log"):
            try:
                os.remove(os.path.join(d, f))
            except OSError:
                pass
    # NEVER the public server: the rooms of this run live on a matchmaking server of our own, bound to loopback
    sport = 51600 + (os.getpid() % 150)
    srv = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "netplay", "server", "gdmelee_server.py"),
                            "--bind", "127.0.0.1", "--port", str(sport)], stdout=open(os.path.join(out, "server.log"), "w"),
                           stderr=subprocess.STDOUT)
    time.sleep(1.5)
    cmd = ("& '%s' -Disc %s -Port %d -Delay %d -Seconds %d -NetSim '%s' -HostChar %d -GuestChar %d -HostDevice gc -GuestDevice keyboard "
           "-Label '%s' -Exe '%s' -Server '127.0.0.1:%d' -EnvHost %s -EnvGuest %s" %
           (os.path.join(MAIN_ROOT, "_build", "netplay_local.ps1").replace("'", "''"), a.disc, port, a.delay, a.seconds,
            a.net_sim.replace("'", "''"), a.host_ck, a.guest_ck, a.name, os.path.abspath(exe).replace("'", "''"), sport, ps_hash(host), ps_hash(guest)))
    t0 = time.time()
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], capture_output=True, text=True)
    srv.terminate()
    try:
        srv.wait(timeout=10)
    except subprocess.TimeoutExpired:
        srv.kill()
    sys.stdout.write(r.stdout[-1500:])
    if r.returncode != 0:
        sys.stdout.write(r.stderr[-1500:])
    time.sleep(2)
    res = {}
    for side, tag in (("host", "np_host"), ("guest", "np_guest")):
        d = os.path.join(out, side)
        os.makedirs(d, exist_ok=True)
        for fn in ("melee-pc.log", "hashes.csv"):
            try:
                shutil.copy2(os.path.join(sand[tag], fn), d)
            except OSError:
                pass
        res[side] = read(os.path.join(d, "melee-pc.log"))
    summary = {"name": a.name, "host_ck": a.host_ck, "guest_ck": a.guest_ck, "net_sim": a.net_sim, "seconds": a.seconds}
    started = {s: bool(re.search(r"netplay: started", res[s])) for s in res}
    summary["started"] = started
    summary["desyncs"] = {s: len(re.findall(r"netplay: DESYNC", res[s])) for s in res}
    hh, hg = hashes(os.path.join(out, "host", "hashes.csv")), hashes(os.path.join(out, "guest", "hashes.csv"))
    shared = sorted(hh.keys() & hg.keys())
    bad = [f for f in shared if hh[f] != hg[f]]
    summary["confirmed_frames"] = {"host": len(hh), "guest": len(hg), "shared": len(shared), "mismatching": len(bad),
                                   "last_shared": shared[-1] if shared else None}
    summary["refusals"] = {s: re.findall(r"netplay: (?:refused|lobby - pick|.*cannot play)[^\n]*|scene: Geno definition refused[^\n]*|The host cannot play[^\n]*", res[s])[:3] for s in res}
    summary["define_lines"] = {s: re.findall(r"native define kind[^\n]*|mexid: define[^\n]*|mexid: online in common[^\n]*", res[s])[:6] for s in res}
    summary["coverage"] = {s: re.findall(r"GENOCOV f=\d+ p\d moves=\d+ geno=\d+ luafaults=\S+ stocks=\S+ pct=\S+", res[s])[-2:] for s in res}
    summary["crash"] = {s: bool(re.search(r"ASSERT|FATAL|crash", res[s])) for s in res}
    summary["wall_s"] = round(time.time() - t0)
    played = all(started.values()) and len(shared) >= a.min_frames and not bad and not any(summary["desyncs"].values())
    summary["verdict"] = "play" if played else ("refuse" if not all(started.values()) and not any(summary["desyncs"].values()) else "FAIL")
    with open(os.path.join(out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))
    return 0 if summary["verdict"] == a.expect else 1


if __name__ == "__main__":
    sys.exit(main())
