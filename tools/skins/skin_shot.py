#!/usr/bin/env python3
"""skin_shot.py - start one game window off screen on a scene, take screenshots over its console socket, quit.

    python tools/skins/skin_shot.py --name skshot1 --mods <mods dir> --iso <iso> \
        --scene "mode=vs;at=css;p1=fox/c34/hu;p2=falco/cpu0" --wait 25 --shot out/css.png \
        [--then 'keys...' ] [--exe <melee-pc.exe>] [--build-root <root>] [--melee <game checkout>]

It runs tools/port/run.sh in its own sandbox (a copy of the exe), so a build can go on beside it. The window is parked at
MELEE_WINDOW_X/Y=30000 (a screenshot comes from the game's own framebuffer, not the desktop). `--lua` lines (repeatable) are
sent to the console after the wait and before each shot, e.g. to press buttons: --lua '= gd.pad_hold and 1'.
Exit status 0 when every shot was written. Needs the exe built with the scripting engine (console socket).
"""
import argparse
import os
import socket
import subprocess
import sys
import time

ROOT = os.environ.get("GW_ROOT_MAIN") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class Console:
    def __init__(self, port):
        self.port, self.sock, self.f = port, None, None

    def connect(self, deadline):
        while time.time() < deadline:
            try:
                self.sock = socket.create_connection(("127.0.0.1", self.port), timeout=10)
                self.f = self.sock.makefile("r", encoding="utf-8", errors="replace")
                self.f.readline()
                return True
            except OSError:
                time.sleep(1)
        return False

    def run(self, line):
        self.sock.sendall((line + "\n").encode("utf-8"))
        out = []
        while True:
            r = self.f.readline()
            if not r:
                raise ConnectionError("console closed")
            r = r.rstrip("\n")
            if r in (">>> ok", ">>> error"):
                return [o for o in out if not o.startswith("> ")], r == ">>> ok"
            out.append(r)


def bash_path(p):
    """A Windows path -> the /e/x form Git Bash takes as a script path."""
    p = p.replace("\\", "/").rstrip("/")
    if len(p) > 1 and p[1] == ":":
        p = "/" + p[0].lower() + p[2:]
    return p


def git_bash():
    """Git Bash, not the WSL bash.exe that comes first on a Windows PATH."""
    for c in (os.environ.get("GW_BASH", ""), "C:/Program Files/Git/bin/bash.exe", "C:/Program Files (x86)/Git/bin/bash.exe"):
        if c and os.path.exists(c):
            return c
    return "bash"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--name", required=True, help="sandbox name (unique per run)")
    ap.add_argument("--mods", required=True)
    ap.add_argument("--iso", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--wait", type=int, default=25, help="seconds after the console answers before the first shot")
    ap.add_argument("--shot", action="append", default=[], help="PNG path (repeatable; one per --wait-between)")
    ap.add_argument("--between", type=int, default=3, help="seconds between shots")
    ap.add_argument("--lua", action="append", default=[], help="console line sent before the NEXT shot (repeatable, in order)")
    ap.add_argument("--build-root", default=os.environ.get("GW_BUILD_ROOT", ""))
    ap.add_argument("--melee", default=os.environ.get("GW_MELEE", ""))
    ap.add_argument("--port", type=int, default=58000 + os.getpid() % 900)
    ap.add_argument("--env", action="append", default=[], help="K=V for the game")
    a = ap.parse_args()

    env = dict(os.environ)
    env.update({"MELEE_MODS_DIR": a.mods, "MELEE_SCENE": a.scene, "MELEE_CONSOLE_PORT": str(a.port), "MELEE_WINDOW_X": "30000",
                "MELEE_WINDOW_Y": "30000", "MELEE_VOLUME": "0", "MELEE_NO_ONBOARD": "1", "MELEE_ATLAS": "1",
                "MELEE_SCRIPT": os.environ.get("MELEE_SCRIPT", "")})
    if not env["MELEE_SCRIPT"]:
        del env["MELEE_SCRIPT"]
    if a.build_root:
        env["GW_BUILD_ROOT"] = a.build_root
    if a.melee:
        env["GW_MELEE"] = a.melee
    for kv in a.env:
        k, v = kv.split("=", 1)
        env[k] = v
    cmd = [git_bash(), bash_path(ROOT) + "/tools/port/run.sh", "--realtime", "--idle-cpus", "--max-seconds", str(a.wait + 20 + 6 * len(a.shot)),
           a.name, "--iso", a.iso]
    p = subprocess.Popen(cmd, env=env)
    con = Console(a.port)
    ok = True
    try:
        if not con.connect(time.time() + 90):
            print("FAIL: no console socket")
            return 1
        time.sleep(a.wait)
        lua = list(a.lua)
        for i, path in enumerate(a.shot):
            if lua:
                out, good = con.run(lua.pop(0))
                print("lua ->", "ok" if good else "ERROR", " ".join(out)[:200])
                time.sleep(1.5)
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            out, good = con.run("shot " + os.path.abspath(path))
            print("shot", path, "ok" if good else "ERROR", " ".join(out)[:200])
            ok &= good
            time.sleep(a.between)
        try:
            con.run("quit")
        except (OSError, ConnectionError):
            pass
    finally:
        try:
            p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            p.terminate()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
