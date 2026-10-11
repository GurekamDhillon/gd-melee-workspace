"""In-game check: a projectile edited in Blender flies as authored.

    python tools/blender/geno_workbench/engine_check/run_engine_check.py --engine-root _build/agents/projectiles-game \
        --article KameOrb --velocity 1.5 0.5 --lifetime 10 [--gravity 0.05] [--work _build/projectiles-check]

Steps (all against copies; the project's committed gameplay.json is restored at the end):
  1. copy the built Goku package twice (A = baseline, B = edited) and rebuild each gameplay-only from the port;
  2. start the Workbench server (no engine) on the port, edit the article in a background Blender with the add-on's own
     Apply path (edit_projectile.py), so B's gameplay.json carries the Blender edit;
  3. run the LAB twice (A, B) with projectile_probe: Goku charges neutral B, every live Goku article is logged each frame;
  4. compare each log with the add-on's predicted path (compare_probe.py) and print the PASS/FAIL lines.
Needs the disc (GW_ISO_VANILLA in .env), Blender (GW_BLENDER or the Steam path), the launcher build (GW_LAUNCHER) and an
engine build root (tools/port/agent_new.sh + build.sh).  Windows only; the game windows are placed off screen.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import launch  # noqa: E402

HERE = Path(__file__).resolve().parent
WT = HERE.parents[3]                                  # this worktree
MAIN = Path(os.environ.get("GW_MAIN_ROOT", WT.parents[1]))   # the workspace root (shared _build, .env, tools/port)
PORT = WT / "ports/goku-xv2"
BASH = os.environ.get("GW_GIT_BASH", "C:/Program Files/Git/bin/bash.exe")
BLENDER = os.environ.get("GW_BLENDER") or "D:/SteamLibrary/steamapps/common/Blender/blender.exe"


def env_iso():
    for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*(.+)", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise SystemExit("GW_ISO_VANILLA missing from .env")


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], **kw)


def build_package(author, out, log):
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(author / "package", out)
    with open(log, "w", encoding="utf-8") as fh:
        r = run([sys.executable, PORT / "tools/build.py", "--fighter", author / "fighter.json", "--gameplay-only", "--out", out],
                cwd=WT, stdout=fh, stderr=subprocess.STDOUT)
    tail = Path(log).read_text(encoding="utf-8", errors="replace").splitlines()[-6:]
    print("\n".join("  build| " + l for l in tail))
    if r.returncode != 0:
        raise SystemExit("gameplay-only build failed (see %s)" % log)


def play(engine_root, mods, name, results):
    probe = mods / "projectile-probe"
    if probe.exists():
        shutil.rmtree(probe)
    shutil.copytree(HERE / "projectile_probe", probe)
    (mods / "enabled.txt").write_text("goku-xv2\ngeno-lab\nprojectile-probe\n", encoding="utf-8")
    env = dict(os.environ)
    env.update({"GW_BUILD_ROOT": str(engine_root), "GW_MELEE": str(engine_root.parents[2] / "worktrees" / engine_root.name),
                "MELEE_MODS_DIR": str(mods), "MELEE_SCENE": "mode=lab;p1=geno:goku-xv2/hu;p2=mario/hu;stage=fd;items=off;time=0",
                "MELEE_UNATTENDED": "1", "MELEE_MAX_SECONDS": "240", "MELEE_LAB_UI": "0", "MELEE_NETPLAY_BIND": "127.0.0.1",
                "MELEE_WINDOW_X": "30000", "MELEE_WINDOW_Y": "30000", "MELEE_WINDOW_W": "960", "MELEE_WINDOW_H": "540",
                "MELEE_RUN_LABEL": "projectile check " + name, "MELEE_TURBO": "1",
                "MELEE_PAD_SCRIPT": (PORT / "combo/tests/turbo_pad.lua").as_posix()})
    results.mkdir(parents=True, exist_ok=True)
    with open(results / (name + ".run.txt"), "w", encoding="utf-8") as fh:
        run([BASH, (MAIN / "tools/port/run.sh").as_posix(), "--max-seconds", "240", name, "--iso", env_iso()],
            cwd=MAIN, env=env, stdout=fh, stderr=subprocess.STDOUT)
    log = engine_root / "runs" / name / "melee-pc.log"
    if not log.exists():
        raise SystemExit("no log at %s" % log)
    dest = results / (name + ".melee-pc.log")
    shutil.copy(log, dest)
    return dest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine-root", type=Path, required=True)
    ap.add_argument("--author", type=Path, default=MAIN / "_build/goku-xv2/author-source")
    ap.add_argument("--work", type=Path, default=MAIN / "_build/projectiles-check")
    ap.add_argument("--article", default="KameOrb")
    ap.add_argument("--velocity", type=float, nargs=2)
    ap.add_argument("--lifetime", type=int)
    ap.add_argument("--gravity", type=float)
    ap.add_argument("--launcher", default=os.environ.get("GW_LAUNCHER") or str(MAIN / "_build/projectiles-qt/GD Melee.exe"))
    ap.add_argument("--skip-baseline", action="store_true")
    args = ap.parse_args(argv)
    work = args.work
    work.mkdir(parents=True, exist_ok=True)
    gameplay = PORT / "gameplay.json"
    original = gameplay.read_bytes()
    try:
        if not args.skip_baseline:
            build_package(args.author, work / "pkgA", work / "buildA.log")
        # --- edit through the real server and the add-on
        server = subprocess.Popen([args.launcher, "--project", str(PORT), "--serve"], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        port = None
        t0 = time.time()
        while time.time() - t0 < 60 and port is None:
            line = server.stdout.readline()
            if not line:
                break
            port = launch.parse_serve_line(line.strip())
        if port is None:
            raise SystemExit("workbench server did not report a port")
        cmd = [BLENDER, "-b", "--factory-startup", "--python", HERE / "edit_projectile.py", "--", "--port", port,
               "--article", args.article]
        for flag, val in (("--velocity", args.velocity), ("--lifetime", args.lifetime), ("--gravity", args.gravity)):
            if val is not None:
                cmd += [flag] + ([str(v) for v in val] if isinstance(val, list) else [str(val)])
        r = run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("\n".join(l for l in r.stdout.splitlines() if l.startswith("EDIT")))
        try:
            server.stdin.close()
            server.wait(timeout=20)
        except Exception:
            server.kill()
        if r.returncode != 0:
            raise SystemExit("Blender edit failed")
        edited_json = work / "gameplay.edited.json"
        shutil.copy(gameplay, edited_json)
        build_package(args.author, work / "pkgB", work / "buildB.log")
        logs = {}
        if not args.skip_baseline:
            logs["A"] = play(args.engine_root, work / "pkgA/mods", "projcheck-base", work / "results")
        logs["B"] = play(args.engine_root, work / "pkgB/mods", "projcheck-edit", work / "results")
    finally:
        gameplay.write_bytes(original)   # the committed source is never left edited
    rc = 0
    import json
    base_json = work / "gameplay.base.json"
    base_json.write_bytes(original)
    kind = next(i for i, a in enumerate(json.loads(original)["articles"]) if a["name"] == args.article)
    for tag, src in (("A", base_json), ("B", edited_json)):
        if tag not in logs:
            continue
        print("== %s (%s)" % (tag, "baseline" if tag == "A" else "edited in Blender"))
        r = run([sys.executable, HERE / "compare_probe.py", logs[tag], src, args.article, "--kind", kind])
        rc = rc or r.returncode
    return rc


if __name__ == "__main__":
    sys.exit(main())
