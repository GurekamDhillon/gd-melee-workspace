#!/usr/bin/env python3
"""np_drive.py - a two-window netplay test that waits on game STATE, not frame counts.

Starts a host and a guest window through _build/netplay_local.ps1 (-Menu -RealNetwork: both boot
to the main menu and meet through ONLINE PLAY and the server), each running a built-in input
script (np_host / np_guest, pc/scripts/examples) that walks the real menus and plays the lobby.
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
import os
import socket
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOST_PORT, GUEST_PORT = 51721, 51722


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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--exe", default="", help="melee-pc.exe to run (default: _build's)")
    ap.add_argument("--disc", default="ace")
    ap.add_argument("--label", default="np_drive")
    ap.add_argument("--timeout", type=int, default=300, help="seconds for each stage")
    ap.add_argument("--shots", default="", help="folder for one screenshot per side at the match")
    ap.add_argument("--keep", action="store_true", help="leave the windows open at the end")
    a = ap.parse_args()

    env_host = "@{MELEE_CONSOLE_PORT='%d';MELEE_SCRIPT='builtin:np_host';MELEE_VOLUME='3'}" % HOST_PORT
    env_guest = "@{MELEE_CONSOLE_PORT='%d';MELEE_SCRIPT='builtin:np_guest';MELEE_VOLUME='3'}" % GUEST_PORT
    cmd = ("& '%s' -Menu -RealNetwork -HostDevice gc -GuestDevice keyboard -Disc %s -Label '%s' -EnvHost %s -EnvGuest %s%s" %
           (os.path.join(ROOT, "_build", "netplay_local.ps1").replace("'", "''"), a.disc, a.label.replace("'", "''"),
            env_host, env_guest,
            (" -Exe '%s'" % os.path.abspath(a.exe).replace("'", "''")) if a.exe else ""))
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
        for side in (host, guest):
            print("  %s: %s" % (side.name, side.value("gd.netplay().status")))
    finally:
        if not a.keep:
            for side in (host, guest):
                try:
                    side.run("quit")
                except (OSError, ConnectionError):
                    pass
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
