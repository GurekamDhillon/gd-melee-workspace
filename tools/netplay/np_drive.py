#!/usr/bin/env python3
"""np_drive.py - a two-window netplay test that waits on game STATE, not frame counts.

Starts a host and a guest window through _build/netplay_local.ps1 (-Menu -RealNetwork: both boot
to the main menu and meet through ONLINE and the server), each running a built-in input
script (np_host / np_guest, pc/scripts/examples) that walks the Atlas main menu (ONLINE is a
main-menu row) and plays the lobby. The guest joins the host's room BY CODE: the host logs
"ROOMCODE <code>", this driver sends it with gd.netplay_act("code", ...) (a guest launched later
can take it from MELEE_LAB_ROOM instead). --local-server starts tools/netplay/server on
127.0.0.1 for the run (never point a test at the public server); --offscreen parks both windows.
This script watches both over their console sockets (MELEE_CONSOLE_PORT) and checks each stage:
the host gets a room code, the guest is given that code and joins, both reach the lobby, both
reach the match - then a screenshot of each side, and both windows are closed.

    python tools/netplay/np_drive.py                      # _build's exe, ACE
    python tools/netplay/np_drive.py --exe _build/agents/beta/melee-pc.exe --label "beta / B4"
    python tools/netplay/np_drive.py --shots _build/agents/beta/shots --timeout 240

Exit status 0 = the match started on both sides. Needs the server address (netplay_server.txt)
and the disc path in .env, like netplay_local.ps1. Test windows run at MELEE_VOLUME=3.
"""
import argparse
import atexit
import os
import socket
import subprocess
import sys
import time

ROOT = os.environ.get("GW_ROOT_MAIN") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # GW_ROOT_MAIN: run a lane's copy of this script against the main checkout's _build
HOST_PORT = int(os.environ.get("NP_DRIVE_HOST_CONSOLE", "51721"))  # another lane's pair may hold these: set both to run beside it
GUEST_PORT = int(os.environ.get("NP_DRIVE_GUEST_CONSOLE", "51722"))


class Console:
    """One window's console socket: send a line, collect the reply up to >>> ok / >>> error."""

    def __init__(self, port, name):
        self.port, self.name, self.sock, self.f = port, name, None, None

    def connect(self, deadline):
        while time.time() < deadline:
            try:
                self.sock = socket.create_connection(("127.0.0.1", self.port), timeout=10)
                self.f = self.sock.makefile("r", encoding="utf-8", errors="replace")
                self.f.readline()  # banner
                return True
            except OSError:
                time.sleep(1)
        return False

    def run(self, line):
        self.sock.sendall((line + "\n").encode("utf-8"))
        out = []
        while True:
            reply = self.f.readline()
            if not reply:
                raise ConnectionError(self.name + ": console closed")
            reply = reply.rstrip("\n")
            if reply in (">>> ok", ">>> error"):
                return [o for o in out if not o.startswith("> ")], reply == ">>> ok"
            out.append(reply)

    def value(self, expr):
        out, ok = self.run("= " + expr)
        return out[-1] if ok and out else None


def wait_for(what, check, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = check()
        if v:
            print("  ok   %-40s (%.0f s)" % (what, time.time() - t0))
            return v
        time.sleep(1)
    print("  FAIL %-40s (after %.0f s)" % (what, timeout))
    return None


def client_environment(inherited=None, bind=None):
    """Loopback by default; --bind or the caller's environment can opt into WSL networking."""
    env = dict(os.environ if inherited is None else inherited)
    if bind is not None:
        env["MELEE_NETPLAY_BIND"] = bind
    env.setdefault("MELEE_NETPLAY_BIND", "127.0.0.1")
    return env


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--exe", default="", help="melee-pc.exe to run (default: _build's)")
    ap.add_argument("--guest-exe", default="", help="a different melee-pc.exe for the guest (version-mismatch tests)")
    ap.add_argument("--server", default="", help="host:port of the matchmaking server (default: netplay_server.txt)")
    ap.add_argument("--disc", default="ace")
    ap.add_argument("--label", default="np_drive")
    ap.add_argument("--timeout", type=int, default=300, help="seconds for each stage")
    ap.add_argument("--shots", default="", help="folder for one screenshot per side at the match")
    ap.add_argument("--local-server", action="store_true", help="run a matchmaking server on 127.0.0.1 for this test (sets --server)")
    ap.add_argument("--offscreen", action="store_true", help="MELEE_WINDOW_X/Y=30000 on both windows")
    ap.add_argument("--keep", action="store_true", help="leave the windows open at the end")
    ap.add_argument("--bind", default=None, help="client/local-server bind (default: MELEE_NETPLAY_BIND or 127.0.0.1); WSL-to-Windows runs require a non-loopback override, e.g. 0.0.0.0")
    ap.add_argument("--host-env", action="append", default=[], help="K=V for the host window only (repeatable), e.g. MELEE_NETPLAY_CPUS=20:1:9")
    ap.add_argument("--guest-env", action="append", default=[], help="K=V for the guest window only (repeatable)")
    ap.add_argument("--host-cmd", action="append", default=[], help="a console line run on the host once it has a room code, before the guest joins (repeatable), e.g. '= gd.netplay_act(\"cpus\", \"20:1:9\", true)'")
    ap.add_argument("--probe", action="store_true", help="at the match, print every player (cpu, team, stocks) and the item count on both sides")
    ap.add_argument("--stay", type=int, default=0, help="seconds to keep playing once the match is running (rollback soak with the built-in pad scripts)")
    a = ap.parse_args()
    bind_env = client_environment(bind=a.bind)

    srv = None
    if a.local_server:
        sport = 51600 + (os.getpid() % 300)
        srv = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "netplay", "server", "gdmelee_server.py"),
                                "--bind", bind_env["MELEE_NETPLAY_BIND"], "--port", str(sport)])
        a.server = "%s:%d" % ("127.0.0.1" if bind_env["MELEE_NETPLAY_BIND"] == "0.0.0.0" else bind_env["MELEE_NETPLAY_BIND"], sport)
        atexit.register(srv.terminate)  # also on the early "no console socket" returns
    off = ";MELEE_WINDOW_X='30000';MELEE_WINDOW_Y='30000'" if a.offscreen else ""
    off += ";MELEE_NETPLAY_BIND='%s'" % bind_env["MELEE_NETPLAY_BIND"].replace("'", "''")
    # every test client binds loopback by default (--bind/MELEE_NETPLAY_BIND override): a fresh exe path on 0.0.0.0
    # raises a Windows Firewall prompt that stalls the run
    def extra_env(pairs):
        return "".join(";%s='%s'" % (k, v.replace("'", "''")) for k, v in (kv.split("=", 1) for kv in pairs))
    if not any(kv.startswith("MELEE_NETPLAY_PORT=") for kv in a.host_env):
        a.host_env.append("MELEE_NETPLAY_PORT=%d" % (52000 + os.getpid() % 900))  # another lane's host may hold 51500
    env_host = "@{MELEE_CONSOLE_PORT='%d';MELEE_SCRIPT='builtin:np_host';MELEE_VOLUME='3'%s%s}" % (HOST_PORT, off, extra_env(a.host_env))
    env_guest = "@{MELEE_CONSOLE_PORT='%d';MELEE_SCRIPT='builtin:np_guest';MELEE_VOLUME='3'%s%s}" % (GUEST_PORT, off, extra_env(a.guest_env))
    cmd = ("& '%s' -Menu -RealNetwork -HostDevice gc -GuestDevice keyboard -Disc %s -Label '%s' -EnvHost %s -EnvGuest %s%s" %
           (os.path.join(ROOT, "_build", "netplay_local.ps1").replace("'", "''"), a.disc, a.label.replace("'", "''"),
            env_host, env_guest,
            ((" -Exe '%s'" % os.path.abspath(a.exe).replace("'", "''")) if a.exe else "")
            + ((" -GuestExe '%s'" % os.path.abspath(a.guest_exe).replace("'", "''")) if a.guest_exe else "")
            + ((" -Server '%s'" % a.server) if a.server else "")))
    print("starting both windows")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], check=False)

    host, guest = Console(HOST_PORT, "host"), Console(GUEST_PORT, "guest")
    deadline = time.time() + 120
    if not (host.connect(deadline) and guest.connect(deadline)):
        print("FAIL: no console socket (is the exe built with the scripting engine?)")
        return 1
    ok = True
    try:
        host.run("label %s - HOST (np_host)" % a.label)
        guest.run("label %s - GUEST (np_guest)" % a.label)
        code = wait_for("host: room code from the server",
                        lambda: (lambda c: c if c and len(c.strip('"')) == 4 and "?" not in c else None)(
                            host.value("gd.netplay().code")), a.timeout)
        if not code:
            return 1
        code = code.strip('"')
        print("  room %s" % code)
        for line in a.host_cmd:
            out, good = host.run(line)
            print("  host cmd %-50s -> %s %s" % (line, "ok" if good else "ERROR", " ".join(out)))
        if not wait_for("guest: on the JOIN ROOM screen",
                        lambda: guest.value("gd.menu().screen") == "JOIN ROOM", a.timeout):
            return 1
        guest.value('gd.netplay_act("code", "%s")' % code)
        both_lobby = wait_for("both: in the lobby",
                              lambda: host.value("gd.netplay().phase") == "lobby" and
                              guest.value("gd.netplay().phase") == "lobby", a.timeout)
        ok &= bool(both_lobby)
        if both_lobby:
            ok &= bool(wait_for("both: the match is running",
                                lambda: host.value("gd.match().active") == "true" and
                                guest.value("gd.match().active") == "true", a.timeout))
        if ok and a.shots:
            time.sleep(5)
            os.makedirs(a.shots, exist_ok=True)
            host.run("shot %s" % os.path.abspath(os.path.join(a.shots, "np_drive_host.png")))
            guest.run("shot %s" % os.path.abspath(os.path.join(a.shots, "np_drive_guest.png")))
            time.sleep(2)
        if ok and a.probe:
            time.sleep(8)
            probe = ('(function() local t={} for _,p in ipairs(gd.players()) do t[#t+1]=string.format('
                     '"P%d cpu=%s team=%d stocks=%d",p.port,tostring(p.cpu),p.team,p.stocks) end '
                     'return table.concat(t," | ").." | items="..#gd.items() end)()')
            for side in (host, guest):
                print("  %s players: %s" % (side.name, side.value(probe)))
        if ok and a.stay:
            time.sleep(a.stay)
            for side in (host, guest):
                print("  %s after %d s: %s | rb: %s" % (side.name, a.stay, side.value("gd.netplay().status"),
                                                      side.value("gd.rollback and gd.rollback() or 'n/a'")))
        for side in (host, guest):
            print("  %s: %s" % (side.name, side.value("gd.netplay().status")))
    finally:
        if not a.keep:
            for side in (host, guest):
                try:
                    side.run("quit")
                except (OSError, ConnectionError):
                    pass
        if srv is not None:
            srv.terminate()
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
