"""Play any built fighter in a real-time window, using tools/port/run.sh.

python tools/geno/play.py --project ports/example --lab --clip jab1
python tools/geno/play.py --project path/to/fighter.json --vs cpu

--check resolves without writes or processes. Stale gameplay requires --rebuild.
The gameplay-only builder refuses changed art; it never silently exports it.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid


class PlayError(ValueError):
    pass


@dataclass(frozen=True)
class PlayPlan:
    project: Path
    workspace: Path
    key: str
    package: Path
    mods_dir: Path
    iso: Path | None
    scene: str
    run_dir: Path
    log_path: Path
    argv: tuple[str, ...]
    env: dict[str, str]
    stale: tuple[str, ...]
    rebuild_argv: tuple[str, ...]

    def summary(self):
        return dict(ok=True, project=str(self.project), key=self.key,
                    package=str(self.package), mods_dir=str(self.mods_dir), scene=self.scene,
                    run_dir=str(self.run_dir), log_path=str(self.log_path),
                    launch_log=str(self.run_dir / "launch.log"), stale=list(self.stale),
                    can_rebuild=bool(self.rebuild_argv), rebuild_argv=list(self.rebuild_argv))


def _json(path):
    try:
        text = path.read_text(encoding="utf-8-sig")
        value = json.loads("\n".join(line for line in text.splitlines()
                                     if not line.lstrip().startswith("//")))
    except (OSError, ValueError) as exc:
        raise PlayError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PlayError(f"{path}: expected a JSON object")
    return value


def _path(value, base):
    if not isinstance(value, (str, os.PathLike)) or not str(value) or "\0" in str(value):
        raise PlayError("Expected a nonempty path")
    p = Path(value).expanduser()
    return (p if p.is_absolute() else base / p).resolve()


def _workspace(project):
    for directory in (project.parent, *project.parent.parents):
        if (directory / ".git").exists():
            return directory
    return Path(__file__).resolve().parents[2]


_ENV_KEYS = {"GW_ROOT", "GW_BUILD_ROOT", "GW_MELEE", "GW_ISO_VANILLA",
             "GW_BASH", "GW_PYTHON", "GW_ENGINE_EXE", "GW_BLENDER", "BLENDER", "GW_FIGHTERBUILD"}


def _settings(workspace, supplied):
    """Read literal path assignments only. Never execute .env in Python."""
    candidates = []
    if supplied.get("GW_ROOT"):
        candidates.append(_path(supplied["GW_ROOT"], workspace) / ".env")
    candidates.append(workspace / ".env")
    candidates.extend(p / ".env" for p in workspace.parents
                      if (p / "tools/port/portlib.sh").is_file())
    values = {}
    for candidate in candidates:
        if not candidate.is_file():
            continue
        values["GW_ROOT"] = str(candidate.parent.resolve())
        for line in candidate.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"^\s*(?:export\s+)?([A-Z_0-9]+)\s*=\s*(.*?)\s*$", line)
            if not m or m[1] not in _ENV_KEYS:
                continue
            raw = m[2]
            if raw[:1] in ("'", '"'):
                end = raw.find(raw[0], 1)
                rest = raw[end + 1:].strip()
                if end < 0 or (rest and not rest.startswith("#")):
                    raise PlayError(f"{candidate}: unsupported assignment for {m[1]}")
                raw = raw[1:end]
            else:
                raw = re.split(r"\s+#", raw, maxsplit=1)[0].strip()
            if "$(" in raw or chr(96) in raw:
                raise PlayError(f"{candidate}: {m[1]} must be a literal path")
            lookup = {**values, **supplied}
            raw = re.sub(r"\$\{([A-Z_0-9]+)\}|\$([A-Z_0-9]+)",
                         lambda match: lookup.get(match[1] or match[2], match[0]), raw)
            values[m[1]] = raw
        values.setdefault("GW_ROOT", str(candidate.parent.resolve()))
        break
    values.update(supplied)
    return values


def python_executable(env):
    return env.get("GW_PYTHON", "").strip() or sys.executable


def _bash(env):
    if env.get("GW_BASH", "").strip():
        return env["GW_BASH"]
    if os.name == "nt":
        # System32/bash.exe is the WSL launcher. Native paths require Git Bash.
        git = shutil.which("git", path=env.get("PATH", os.defpath))
        if git:
            for parent in Path(git).parents:
                for name in ("bin/bash.exe", "usr/bin/bash.exe"):
                    if (parent / name).is_file():
                        return str(parent / name)
    found = shutil.which("bash", path=env.get("PATH", os.defpath))
    if found:
        if os.name == "nt" and Path(found).parent.name.lower() in ("system32", "sysnative", "syswow64"):
            raise PlayError("Git Bash not found; set GW_BASH to Git's bash.exe (the WSL shim cannot use native paths)")
        return found
    return "bash"  # launch preflight reports missing Bash


def _gameplay_rebuild(argv):
    if not isinstance(argv, list) or not all(isinstance(a, str) and a and "\0" not in a for a in argv):
        raise PlayError("workbench.json: rebuild must be an array of nonempty arguments")
    if not argv:
        return ()
    result = [a for a in argv if a != "--auto"]
    if "--gameplay-only" not in result:
        result.append("--gameplay-only")
    return tuple(result)


def _source_files(config, cfg, workspace, artist):
    files = [config]
    if artist:
        # Load this checkout's pure cache helper, including when Blender imported
        # the resolver by file from a copied add-on or another active worktree.
        cache_path = Path(__file__).resolve().parent / "artist/gameplay_cache.py"
        spec = importlib.util.spec_from_file_location(__name__ + "_art_cache", cache_path)
        gameplay_cache = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gameplay_cache)
        try:
            files.extend(Path(p) for p in gameplay_cache.signature(config)["art"])
        except OSError as exc:
            raise PlayError(f"Artist source is missing: {exc}; restore it before rebuilding") from exc
        return files
    for key in ("gameplay", "fidelity"):
        if cfg.get(key):
            files.append(_path(cfg[key], config.parent))
    for key in ("art_blend", "art_glb"):
        if cfg.get(key):
            files.append(_path(cfg[key], workspace))
    if cfg.get("moves_dir"):
        moves = _path(cfg["moves_dir"], config.parent)
        if moves.is_dir():
            files.extend(p for p in moves.rglob("*") if p.is_file()
                         and p.suffix in (".genoasm", ".lua", ".json"))
    for directory in ("lua", "scripts"):
        base = config.parent / directory
        if base.is_dir():
            files.extend(p for p in base.rglob("*.lua") if p.is_file())
    gameplay = config.parent / cfg.get("gameplay", "gameplay.json")
    if gameplay.is_file():
        data = _json(gameplay)
        files.extend(_path(data[key], config.parent)
                     for key in ("source_ir", "host_ir") if data.get(key))
    for index, arg in enumerate(cfg.get("rebuild", [])):
        if arg == "--fighter" and index + 1 < len(cfg["rebuild"]):
            fighter = _path(cfg["rebuild"][index + 1], workspace)
            files.append(fighter)
            if fighter.is_file():
                f = _json(fighter)
                files.extend(_path(f["art"][key], fighter.parent)
                             for key in ("blend", "glb") if f.get("art", {}).get(key))
        elif index == 1 and arg.endswith(".py"):
            files.append(_path(arg, workspace))
    return list(dict.fromkeys(files))


def _staleness(package, files):
    required = (package / "mod.json", package / "geno.json")
    missing = [f"Missing built package file: {p}" for p in required if not p.is_file()]
    if missing:
        return tuple(missing)
    built = min(p.stat().st_mtime_ns for p in required)
    return tuple(f"Source is newer than the package: {p}"
                 for p in files if p.is_file() and p.stat().st_mtime_ns > built)


def _clip_row(want, config, cfg, package):
    if not want or any(c.isspace() for c in want) or "\0" in want:
        raise PlayError("--clip needs one row number, move id or clip name")
    if want.isdecimal():
        return want
    gameplay = config.parent / cfg.get("gameplay", "gameplay.json")
    move = None
    if cfg.get("schema") == "workbench/1" and gameplay.is_file():
        move = next((m for m in _json(gameplay).get("moves", []) if m.get("name") == want), None)
    plan_path = package / "files/plan.json"
    plan = _json(plan_path) if plan_path.is_file() else {}
    if move:
        pick = move.get("pick", {}).get("clip")
        if pick:
            return pick
        for motion in move.get("motions", []):
            for row in plan.get("motion_rows", []):
                if row.get("motion") != motion:
                    continue
                if isinstance(row.get("row"), int):
                    return str(row["row"])
                if row.get("clip"):
                    return str(row["clip"])
                if isinstance(row.get("row"), str):
                    return row["row"]
            clips = plan.get("row_clips", [])
            if isinstance(motion, int) and 0 <= motion < len(clips) and clips[motion]:
                return clips[motion]
        if not plan:
            return want  # rebuild will resolve it before launch
        raise PlayError(f"Move {want!r} has no installed animation row; rebuild its package")
    # Stock row names can be bound to authored clips with different names.
    # The LAB exposes the installed clip name/symbol for those animation rows.
    for row in plan.get("motion_rows", []):
        if row.get("row") == want and row.get("clip"):
            return str(row["clip"])
    bank = plan.get("bank", {}).get("clips", {})
    if isinstance(bank, dict):
        known = want in bank or any(c.get("symbol") == want for c in bank.values())
    else:
        known = any(c.get("name") == want or c.get("symbol") == want for c in bank)
    if not plan or known:
        return want
    raise PlayError(f"Unknown clip or move row: {want}")


def resolve_project(project, *, root=None, env=None, mode="lab", clip=None,
                    run_name=None, mods_dir=None, engine_exe=None, iso=None):
    """Resolve paths, argv, scene and staleness without writes or processes."""
    if mode not in ("lab", "vs"):
        raise PlayError("Play mode must be lab or vs")
    supplied = dict(os.environ if env is None else env)
    base = Path(root).resolve() if root else Path.cwd()
    source = _path(project, base)
    if source.is_dir():
        source /= "workbench.json" if (source / "workbench.json").is_file() else "fighter.json"
    cfg = _json(source)
    artist = cfg.get("schema") == "geno-artist/1"
    workspace = (Path(root).resolve() if root else
                 Path(__file__).resolve().parents[2] if artist else _workspace(source))
    settings = _settings(workspace, supplied)
    runtime = _path(settings.get("GW_ROOT", str(workspace)), workspace)
    build = _path(settings.get("GW_BUILD_ROOT", str(runtime / "_build")), runtime)
    engine_exe = engine_exe or settings.get("GW_ENGINE_EXE", "")
    if engine_exe:
        engine = _path(engine_exe, workspace)
        if engine.name.lower() != "melee-pc.exe":
            raise PlayError("Engine override must name melee-pc.exe (run.sh owns launch)")
        build = engine.parent
    artist = cfg.get("schema") == "geno-artist/1"
    if not artist and cfg.get("schema") != "workbench/1":
        raise PlayError(f"{source}: unsupported project schema")
    package_id = cfg.get("key") if artist else cfg.get("mod_id") or cfg.get("id")
    if not isinstance(package_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", package_id):
        raise PlayError("Project needs a safe fighter key or mod_id")
    if artist:
        if cfg.get("output"):
            out = _path(cfg["output"], source.parent)
        else:
            out = next((p for p in (source.parent / "package", source.parent)
                        if (p / "mods" / package_id / "mod.json").is_file()),
                       workspace / "_build/artist" / package_id)
        mods = _path(mods_dir, workspace) if mods_dir else (out / "mods").resolve()
        rebuild = (python_executable(settings), "-m", "tools.geno.artist", "build",
                   str(source), "--out", str(mods.parent), "--gameplay-only")
    else:
        if mods_dir or cfg.get("mods_dir"):
            mods = _path(mods_dir or cfg["mods_dir"], workspace)
        elif cfg.get("plan_abs") or cfg.get("plan"):
            plan = _path(cfg.get("plan_abs") or cfg["plan"],
                         workspace if cfg.get("plan_abs") else source.parent)
            if plan.parent.name != "files":
                raise PlayError("Set mods_dir in workbench.json; plan is outside a built package")
            mods = plan.parent.parent.parent
        else:
            raise PlayError("Set mods_dir or a built-package plan_abs in workbench.json")
        rebuild = _gameplay_rebuild(cfg.get("rebuild", []))
    package = mods / package_id
    key = package_id
    if (package / "geno.json").is_file():
        fighters = _json(package / "geno.json").get("fighters", [])
        keys = [f.get("define", {}).get("key") for f in fighters if isinstance(f, dict)]
        keys = [k for k in keys if k]
        if len(keys) != 1:
            raise PlayError(f"{package}: play needs exactly one built define fighter")
        key = keys[0]
        if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", key):
            raise PlayError("Built package has an invalid define key")
    enabled = mods / "enabled.txt"
    if enabled.is_file():
        ids = {s.strip() for s in enabled.read_text(encoding="utf-8-sig").splitlines()
               if s.strip() and not s.lstrip().startswith("#")}
        if package_id not in ids:
            raise PlayError(f"{package_id} is disabled in {enabled}")
        if mode == "lab" and "geno-lab" not in ids:
            raise PlayError(f"Enable geno-lab in {enabled} before playing in LAB")
    if mode == "lab" and (package / "geno.json").is_file() and not (mods / "geno-lab/mod.json").is_file():
        raise PlayError(f"geno-lab is missing from {mods}; build/install the project first")
    name = run_name or f"{key}-{mode}-{uuid.uuid4().hex[:12]}"
    if not isinstance(name, str) or name in (".", "..") or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise PlayError("Run name must be one safe sandbox directory name")
    run = build / "runs" / name
    disc_value = iso or settings.get("GW_ISO_VANILLA", "")
    disc = _path(disc_value, runtime) if disc_value else None
    scene = f"mode={mode};p1=geno:{key}/hu;p2=mario/cpu{'0' if mode == 'lab' else '9'};stage=fd;items=off;time=0"
    launch_env = dict(settings)
    if not launch_env.get("GW_MELEE"):
        launch_env["GW_MELEE"] = str(runtime / "melee")
    for variable in ("MELEE_LAB_MODE", "MELEE_LAB_CLIP", "MELEE_CPU_IDLE", "MELEE_PAD_SCRIPT",
                     "MELEE_WORKBENCH", "MELEE_WORKBENCH_DIR", "MELEE_WB_DIR",
                     "MELEE_CONSOLE_PORT", "MELEE_WB_HEADLESS", "MELEE_WB_PORT",
                     "MELEE_WINDOW_X", "MELEE_WINDOW_Y", "MELEE_PAD_IGNORE_ADAPTER",
                     "MELEE_TEST", "MELEE_REPLAY", "MELEE_REPLAY_FILE",
                     "MELEE_FULLSCREEN_TOGGLE_AT", "MELEE_LAB_BATCH", "MELEE_LAB_BATCH_QUIT"):
        launch_env.pop(variable, None)
    launch_env.update({
        "GW_ROOT": str(runtime), "GW_BUILD_ROOT": str(build), "GW_ENV_RESOLVED": "1",
        "MELEE_MODS_DIR": str(mods), "MELEE_SCENE": scene,
        "MELEE_TURBO": "0", "MELEE_TURBO_RENDER": "1", "MELEE_UNATTENDED": "0",
        "MELEE_MAX_SECONDS": "0", "MELEE_WINDOW_HIDE": "0", "MELEE_FULLSCREEN": "0",
        "MELEE_FPS": "60", "MELEE_NETPLAY_BIND": "127.0.0.1",
        "MELEE_RUN_LABEL": f"{key} / {'LAB CLIPS' if clip and mode == 'lab' else mode.upper()}",
    })
    if mode == "lab" and clip:
        launch_env.update(MELEE_LAB_MODE="clips", MELEE_LAB_CLIP=_clip_row(str(clip), source, cfg, package),
                          MELEE_CPU_IDLE="1")
    argv = (_bash(settings), str(workspace / "tools/port/run.sh"), "--realtime", name)
    if disc:
        argv += ("--iso", str(disc))
    stale = _staleness(package, _source_files(source, cfg, workspace, artist))
    return PlayPlan(source, workspace, key, package, mods, disc, scene, run,
                    run / "melee-pc.log", argv, launch_env, stale, rebuild)


def launch(plan):
    """Start the wrapper detached, log its output, and return its PID."""
    if plan.stale:
        raise PlayError("Package is stale; rebuild before play")
    if not plan.iso or not plan.iso.is_file():
        raise PlayError("Disc image not found: set GW_ISO_VANILLA in .env or use --iso")
    if not (plan.run_dir.parent.parent / "melee-pc.exe").is_file():
        raise PlayError("Engine not found: build with tools/port/build.sh or set GW_BUILD_ROOT")
    if not Path(plan.argv[0]).is_file() and not shutil.which(plan.argv[0], path=plan.env.get("PATH", os.defpath)):
        raise PlayError("Git Bash not found: set GW_BASH to bash.exe")
    if not Path(plan.argv[1]).is_file():
        raise PlayError("tools/port/run.sh is missing from the project's checkout")
    plan.run_dir.mkdir(parents=True, exist_ok=False)
    flags = ({"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
             if os.name == "nt" else {"start_new_session": True})
    with (plan.run_dir / "launch.log").open("w", encoding="utf-8") as output:
        proc = subprocess.Popen(plan.argv, cwd=plan.workspace, env=plan.env,
                                stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, **flags)
    return proc.pid


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Workbench directory/JSON or artist fighter.json")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--lab", action="store_true", help="Open LAB (default)")
    modes.add_argument("--vs", choices=("cpu",), help="Play against level 9 Mario")
    parser.add_argument("--clip", help="Current move, animation row or clip name (LAB only)")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild stale gameplay before play")
    parser.add_argument("--check", action="store_true", help="Resolve only; no writes or processes")
    parser.add_argument("--json", action="store_true", help="Machine-readable result for UI callers")
    parser.add_argument("--mods-dir", help="Override installed mods directory")
    parser.add_argument("--engine-exe", help="Override melee-pc.exe; run.sh still owns launch")
    parser.add_argument("--iso", help="Override local disc path")
    args = parser.parse_args(argv)
    options = dict(mode="vs" if args.vs else "lab", clip=args.clip,
                   mods_dir=args.mods_dir, engine_exe=args.engine_exe, iso=args.iso)
    try:
        plan = resolve_project(args.project, **options)
        if not args.check and plan.stale:
            if not args.rebuild:
                raise PlayError("Package is stale:\n" + "\n".join(plan.stale) +
                                "\nRebuild gameplay first: repeat this command with --rebuild.")
            if not plan.rebuild_argv:
                raise PlayError("Package is stale and workbench.json has no rebuild command")
            build_log = plan.run_dir.parent.parent / "play-rebuild" / (plan.run_dir.name + ".log")
            build_log.parent.mkdir(parents=True, exist_ok=True)
            with build_log.open("w", encoding="utf-8") as output:
                result = subprocess.run(plan.rebuild_argv, cwd=plan.workspace, env=plan.env,
                                        stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                                        **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}))
            if result.returncode:
                tail = "\n".join(build_log.read_text(encoding="utf-8", errors="replace").splitlines()[-8:])
                raise PlayError(f"Gameplay rebuild failed. Log: {build_log}\n{tail}")
            plan = resolve_project(args.project, run_name=plan.run_dir.name, **options)
            if plan.stale:
                raise PlayError("Package is still stale after rebuild:\n" + "\n".join(plan.stale))
        value = plan.summary()
        if not args.check:
            value["pid"] = launch(plan)
        if args.json or args.check:
            print(json.dumps(value))
        else:
            print(f"{plan.key}: play started")
            print(f"Log: {plan.log_path}\nLaunch log: {plan.run_dir / 'launch.log'}")
        return 0
    except (PlayError, OSError) as exc:
        if args.json or args.check:
            print(json.dumps({"ok": False, "error": str(exc)}))
        else:
            print(f"Play: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
