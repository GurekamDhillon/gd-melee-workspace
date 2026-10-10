"""One command: open Blender with the real Goku loaded from the real engine.

    python tools/blender/geno_workbench/launch_goku.py            # interactive Blender
    python tools/blender/geno_workbench/launch_goku.py --check    # background Blender, prints GENO_WB_REPORT lines

It (1) starts the Qt launcher's persistent `--serve` session, which starts the headless
engine (MELEE_WB_HEADLESS=1) on the Goku mod, (2) opens Blender with bootstrap.py, which
connects, imports the artist rig and calibrates it, loads a move row and draws the overlays,
(3) stops the launcher (and with it the engine) when Blender exits.

Everything is overridable by environment (paths below are this machine's defaults):
  GW_ROOT          the main workspace checkout (has .env, _build/goku-xv2, ports/goku-xv2)
  GW_BLENDER       blender.exe
  GW_LAUNCHER      gd-melee-launcher.exe built with --serve (Windows Qt build; needs Qt on PATH).
                   Default: <GW_ROOT>/_build/wb-win/gd-melee-launcher.exe (copy the build there, with the
                   Qt DLLs it needs beside it or Qt on GW_QT_BIN), else the newest one under _build/.
                   Blender's console is also written to <GW_ROOT>/_build/wb-goku/blender.log.
  GW_QT_BIN        Qt bin directory prepended to PATH for the launcher
  GW_ENGINE_EXE    melee-pc.exe built from the geno-workbench game branch (schema 2, headless)
  GW_ISO_VANILLA   the disc image (from .env; never committed)
No disc-derived data is written anywhere under git.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import launch  # noqa: E402  (stdlib-only helper next to this file)


def _find_root() -> Path:
    env = os.environ.get("GW_ROOT")
    if env:
        return Path(env)
    for parent in HERE.parents:
        if (parent / ".env").is_file() and (parent / "_build").is_dir():
            return parent
    return Path("E:/Projects/Melee Workspace")


def _read_env_file(path: Path) -> dict:
    out = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def main() -> int:
    root = _find_root()
    envfile = _read_env_file(root / ".env")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="run Blender in the background, print a report, exit")
    ap.add_argument("--row", default="", help="move row to load (default: first engine row named like a jab, else none)")
    ap.add_argument("--frame", type=int, default=0)
    ap.add_argument("--exercise", default="", help="comma list of rows to play to the end, switch between and restart the engine on (with --check)")
    ap.add_argument("--serve-only", action="store_true", help="start the server and engine, print the port, wait for Enter")
    ap.add_argument("--windowed-engine", action="store_true", help="show the engine window instead of headless")
    args = ap.parse_args()

    blender = os.environ.get("GW_BLENDER", "D:/SteamLibrary/steamapps/common/Blender/blender.exe")
    launcher = os.environ.get("GW_LAUNCHER") or str(
        next((p for p in (root / "_build/wb-win/gd-melee-launcher.exe",           # the stable home (README.md)
                          HERE.parents[2] / "_build/wb-win/gd-melee-launcher.exe") if p.is_file()), ""))
    if not launcher:
        launcher = launch.find_launcher(root=root) or ""
    qt_bin = os.environ.get("GW_QT_BIN", "E:/Projects/Qt/6.8.3/msvc2022_64/bin")
    engine_src = Path(os.environ.get("GW_ENGINE_EXE") or next(
        (c for c in (root / "_build/agents/geno-workbench/melee-pc.exe", root / "_build/wb-goku/engine/melee-pc.exe")
         if c.is_file()), root / "_build/agents/geno-workbench/melee-pc.exe"))
    project = root / "ports/goku-xv2"
    mods = root / "_build/goku-xv2/author-source/package/mods"
    art = root / "_build/goku-xv2/author-source/goku.blend"
    iso = os.environ.get("GW_ISO_VANILLA") or envfile.get("GW_ISO_VANILLA", "")
    work = root / "_build/wb-goku"

    for label, path in (("Blender", blender), ("launcher", launcher), ("engine exe", engine_src),
                        ("project", project), ("mods dir", mods), ("art", art), ("disc image", iso)):
        if not path or not Path(path).exists():
            print("missing %s: %r (set the matching GW_* variable)" % (label, str(path)))
            return 2

    # The engine runs from its own sandbox with its own copy of the exe and DLLs.
    (work / "engine").mkdir(parents=True, exist_ok=True)
    (work / "payloads").mkdir(parents=True, exist_ok=True)
    engine = work / "engine" / "melee-pc.exe"
    if engine_src.resolve() != engine.resolve():
        shutil.copy2(engine_src, engine)
    for dll in ("SDL3.dll", "webgpu_dawn.dll"):
        candidates = [engine_src.parent / dll] + sorted(engine_src.parent.glob("runs/*/" + dll))
        found = next((c for c in candidates if c.is_file()), None)
        if found and not (engine.parent / dll).exists() and found.resolve() != (engine.parent / dll).resolve():
            shutil.copy2(found, engine.parent / dll)

    os.environ["GW_QT_BIN"] = qt_bin
    argv, env = launch.serve_launch(
        launcher, str(project), engine_exe=str(engine), mods_dir=str(mods), iso=iso,
        headless=not args.windowed_engine)
    # keep the payload directory where earlier runs put it
    if "--wb-dir" in argv:
        argv[argv.index("--wb-dir") + 1] = str(work / "payloads")
    print("starting launcher --serve ...")
    proc, port = launch.start_serve(argv, timeout=120, env=env)
    print("WB_SERVE port=%d" % port)
    try:
        if args.serve_only:
            input("server up; press Enter to stop ")
            return 0
        cmd = [blender]
        if os.environ.get("GW_WB_SHOT"):
            cmd += ["--enable-event-simulate"]   # lets bootstrap close the splash before it screenshots
        if args.check:
            cmd += ["--background", "--factory-startup"]
        cmd += ["--python", str(HERE / "bootstrap.py"), "--", "--project", str(project), "--port", str(port),
                "--art", str(art), "--launcher", str(launcher), "--engine", str(engine), "--mods", str(mods)]
        if iso:
            cmd += ["--iso", str(iso)]
        if args.row:
            cmd += ["--row", args.row]
        elif args.check:
            cmd += ["--row", "jab1"]   # the engine's rows are the project's moves (jab1, utilt, ...), not clip names
        if args.frame:
            cmd += ["--frame", str(args.frame)]
        if args.exercise:
            cmd += ["--exercise", args.exercise]
        if args.check:
            cmd += ["--report"]
        print("starting Blender ...")
        blender_log = work / "blender.log"
        if not args.check:
            # Tee Blender's console to a file: a traceback in the add-on is otherwise lost with the window.
            print("Blender log: %s" % blender_log)
            with open(blender_log, "w", encoding="utf-8", errors="replace") as log,                     subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                     errors="replace") as bl:
                for line in bl.stdout:
                    print(line, end="")
                    log.write(line)
                    log.flush()
            return bl.returncode
        # Blender exits 0 even when the script raised; a check fails on a traceback or a missing report
        seen = {"trace": False, "report": False}
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace") as bl,                 open(blender_log, "w", encoding="utf-8", errors="replace") as log:
            for line in bl.stdout:
                print(line, end="")
                log.write(line)
                seen["trace"] |= "Traceback (most recent call last)" in line
                seen["report"] |= "GENO_WB_REPORT" in line
        return 1 if bl.returncode or seen["trace"] or not seen["report"] else 0
    finally:
        launch._stop_process(proc)


if __name__ == "__main__":
    sys.exit(main())
