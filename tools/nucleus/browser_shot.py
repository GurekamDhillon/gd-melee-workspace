#!/usr/bin/env python3
"""browser_shot.py - drive the game's menus over its console socket and take screenshots (the Nucleus browser's acceptance driver).

    python tools/nucleus/browser_shot.py --name nb1 --mods <empty mods dir> --iso <iso> --api http://127.0.0.1:8765/api/public/v1 \
        --steps "wait:20 press:DOWN press:A wait:2 shot:out/mods.png key:Z wait:4 shot:out/browser.png" [--scene "mode=menu"] [--nucleus-dir D]

Starts tools/port/run.sh in its own sandbox with the window parked off screen (MELEE_WINDOW_X/Y=30000), connects to the console socket, runs the
steps, then quits. Steps (space separated):  wait:S   press:BUTTON[+BUTTON][:FRAMES] (gd.input on port 1; A B X Y Z L R START UP DOWN LEFT RIGHT)
shot:PATH   lua:CODE (one console line, no spaces: use ~ for a space)   log:REGEX (fail unless the run's log matches so far; tails melee-pc.log)
The exit status is 0 when every shot and every log check succeeded. Everything the game does is on its own socket: no window ever needs a person.
"""
import argparse
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skins"))
from skin_shot import Console, bash_path, git_bash, ROOT  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--name", required=True)
    ap.add_argument("--mods", required=True)
    ap.add_argument("--iso", required=True)
    ap.add_argument("--steps", required=True)
    ap.add_argument("--scene", default="mode=menu")
    ap.add_argument("--api", default="")
    ap.add_argument("--nucleus-dir", default="")
    ap.add_argument("--build-root", default=os.environ.get("GW_BUILD_ROOT", ""))
    ap.add_argument("--melee", default=os.environ.get("GW_MELEE", ""))
    ap.add_argument("--port", type=int, default=58000 + os.getpid() % 900)
    ap.add_argument("--max-seconds", type=int, default=240)
    ap.add_argument("--env", action="append", default=[])
    a = ap.parse_args()

    env = dict(os.environ)
    env.update({"MELEE_MODS_DIR": a.mods, "MELEE_SCENE": a.scene, "MELEE_CONSOLE_PORT": str(a.port), "MELEE_WINDOW_X": "30000",
                "MELEE_WINDOW_Y": "30000", "MELEE_VOLUME": "0", "MELEE_NO_ONBOARD": "1", "MELEE_ATLAS": "1"})
    if a.api:
        env["MELEE_NUCLEUS_API"] = a.api
    if a.nucleus_dir:
        env["MELEE_NUCLEUS_DIR"] = a.nucleus_dir
    if a.build_root:
        env["GW_BUILD_ROOT"] = a.build_root
    if a.melee:
        env["GW_MELEE"] = a.melee
    for kv in a.env:
        k, v = kv.split("=", 1)
        env[k] = v
    cmd = [git_bash(), bash_path(ROOT) + "/tools/port/run.sh", "--realtime", "--idle-cpus", "--max-seconds", str(a.max_seconds), a.name, "--iso", a.iso]
    p = subprocess.Popen(cmd, env=env)
    con = Console(a.port)
    ok = True
    log_path = os.path.join(a.build_root or os.path.join(ROOT, "_build"), "runs", a.name, "melee-pc.log")
    try:
        if not con.connect(time.time() + 120):
            print("FAIL: no console socket")
            return 1
        for step in a.steps.split():
            kind, _, arg = step.partition(":")
            if kind == "wait":
                time.sleep(float(arg))
            elif kind == "press":
                btn, _, frames = arg.partition(":")
                out, good = con.run('= gd.input(1,"%s",%d)' % (btn, int(frames or 4)))
                time.sleep(0.35 + int(frames or 4) / 60.0)
                ok &= good
            elif kind == "key":
                out, good = con.run('= gd.input(1,"%s",4)' % arg)
                time.sleep(0.5)
                ok &= good
            elif kind == "lua":
                out, good = con.run(arg.replace("~", " "))
                print("lua ->", "ok" if good else "ERROR", " ".join(out)[:300])
                ok &= good
            elif kind == "shot":
                os.makedirs(os.path.dirname(os.path.abspath(arg)), exist_ok=True)
                out, good = con.run("shot " + os.path.abspath(arg))
                print("shot", arg, "ok" if good else "ERROR", " ".join(out)[:200])
                ok &= good
                time.sleep(2.0)                 # the file is written a few frames later
            elif kind == "log":
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as fp:
                        text = fp.read()
                except OSError:
                    text = ""
                hit = re.search(arg.replace("~", " "), text)
                print("log", arg, "FOUND" if hit else "MISSING", hit.group(0)[:160] if hit else "")
                ok &= bool(hit)
            else:
                print("unknown step", step)
                ok = False
        try:
            con.run("quit")
        except (OSError, ConnectionError):
            pass
    finally:
        try:
            p.wait(timeout=40)
        except subprocess.TimeoutExpired:
            p.terminate()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
