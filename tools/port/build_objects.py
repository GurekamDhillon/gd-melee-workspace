#!/usr/bin/env python3
"""Select and compile game TUs/native shims with dependency-aware object keys."""

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import scan_stale_tus
from scan_stale_tus import preserve_object


PORT = Path(__file__).resolve().parent
ROOT = PORT.parent.parent


def job_count(value=None):
    if value is not None and value != "":
        try:
            count = int(value)
        except ValueError as exc:
            raise ValueError("GW_JOBS must be a positive integer") from exc
        if count < 1:
            raise ValueError("GW_JOBS must be a positive integer")
        return count
    physical = None
    if os.name == "nt":
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Processor | Measure-Object NumberOfCores -Sum).Sum"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            try:
                physical = int(result.stdout.strip())
            except ValueError:
                pass
    else:
        try:
            physical = len({(int(package.read_text()), int(core.read_text()))
                            for package in Path("/sys/devices/system/cpu").glob("cpu*/topology/physical_package_id")
                            for core in [package.with_name("core_id")]})
        except (OSError, ValueError):
            pass
    return min(physical or os.cpu_count() or 1, 12)


def file_digest(path, cache=None):
    path = Path(path)
    return (cache.digest(path) if cache is not None else scan_stale_tus.hash_file(path)).hex()


def config(kind, root, source=None, cache=None):
    """Bind an object to its command, relevant environment and tool contents."""
    clang = Path(os.environ.get("GW_CLANG", str(root / "_toolchains/llvm/bin/clang.exe")))
    if kind == "game":
        script = root / "_build/masstest/pipe_win.sh"
        tools = [clang, Path(os.environ.get("GW_GWTOOL", str(root / "_build/gwtool/gwtool.exe")))]
        variables = ("GW_GWTOOL_FLAGS",)
    else:
        script = root / "tools/port/portlib.sh"
        tools = [clang]
        variables = ("GW_SDL_INCLUDE", "GW_IMGUI_INCLUDE", "GW_DAWN_INCLUDE",
                     "GW_DAWN_GEN_INCLUDE")
    digest = hashlib.sha256()
    digest.update(b"gw-compile-v2\0" + kind.encode() + b"\0")
    if source is not None:
        digest.update(source.suffix.encode() + b"\0")
        if source.name.startswith("gw_fx_") and source.suffix == ".cpp":
            digest.update(b"c++20\0")
    digest.update(file_digest(script, cache).encode())
    for name in variables:
        digest.update(b"\0" + name.encode() + b"=" + os.environ.get(name, "").encode())
    for tool in tools:
        digest.update(b"\0" + str(tool.resolve()).encode() + b"=" + file_digest(tool, cache).encode())
    return digest.digest()


def object_paths(obj):
    return Path(str(obj) + ".d"), Path(str(obj) + ".sha256")


def record(obj, source, melee, config_bytes, file_hashes=None):
    depfile, keyfile = object_paths(obj)
    if not obj.is_file() or not depfile.is_file():
        raise RuntimeError(f"compile did not produce object and depfile: {source}")
    value = scan_stale_tus.object_key(depfile, melee, config_bytes, source, file_hashes)
    temp = Path(str(keyfile) + f".{os.getpid()}.tmp")
    temp.write_text(value + "\n", encoding="ascii")
    temp.replace(keyfile)


def run_jobs(jobs, workers, on_success=None, cwd=None, env=None):
    """Stop launching queued jobs on the first failure; collect all running exits."""
    if workers < 1:
        raise ValueError("job count must be positive")
    pending = iter(jobs)
    running = []
    failure = None
    while True:
        while failure is None and len(running) < workers:
            try:
                label, argv = next(pending)
            except StopIteration:
                break
            try:
                running.append((label, subprocess.Popen(argv, cwd=cwd, env=env)))
            except OSError as exc:
                failure = f"{label} could not start: {exc}"
        if not running:
            break
        finished = []
        for label, process in running:
            status = process.poll()
            if status is None:
                continue
            finished.append((label, process))
            if status != 0 and failure is None:
                failure = f"{label} failed with exit {status}"
            elif status == 0 and on_success is not None:
                try:
                    on_success(label)
                except (OSError, RuntimeError, ValueError) as exc:
                    if failure is None:
                        failure = f"{label}: {exc}"
        for item in finished:
            running.remove(item)
        if running and not finished:
            time.sleep(0.05)
    if failure:
        raise RuntimeError(failure)


def shim_sources(melee):
    platform = melee / "pc/platform"
    return sorted([*platform.glob("*.c"), *platform.glob("*.cpp")])


def scan_shims(melee, out, root, file_hashes=None):
    stale = []
    fallback_header = None
    melee = melee.resolve()
    file_hashes = file_hashes if file_hashes is not None else scan_stale_tus.FileCache(out / ".content-cache.json")
    configs = {}
    for source in shim_sources(melee):
        obj = out / (source.stem + ".obj")
        depfile, keyfile = object_paths(obj)
        if not obj.is_file():
            stale.append(source.name)
        elif depfile.is_file() != keyfile.is_file():
            stale.append(source.name)
        elif not depfile.is_file():
            if fallback_header is None:
                fallback_header = max((p.stat().st_mtime_ns for p in (melee / "pc/platform").glob("*.h")), default=-1)
            if source.stat().st_mtime_ns > obj.stat().st_mtime_ns or fallback_header > obj.stat().st_mtime_ns:
                stale.append(source.name)
        else:
            mode = (source.suffix, source.name.startswith("gw_fx_") and source.suffix == ".cpp")
            if mode not in configs:
                configs[mode] = config("shim", root, source, file_hashes)
            try:
                actual = scan_stale_tus.object_key(depfile, melee, configs[mode], source, file_hashes)
                if actual != file_hashes.key(keyfile) and not scan_stale_tus.restore_object(obj, melee, configs[mode], source, file_hashes):
                    stale.append(source.name)
            except (OSError, UnicodeError, ValueError):
                stale.append(source.name)
    file_hashes.save()
    return stale


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("game", "shim", "record-shims", "jobs"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--melee", type=Path, default=Path(os.environ.get("GW_MELEE", ROOT / "melee")))
    parser.add_argument("--out", type=Path, default=Path(os.environ.get("GW_OUT", ROOT / "_build/masstest/out")))
    parser.add_argument("--shimobj", type=Path, default=Path(os.environ.get("GW_SHIMOBJ", ROOT / "_build/masstest/shimobj")))
    parser.add_argument("--files", type=Path, default=ROOT / "_build/masstest/files.txt")
    parser.add_argument("--jobs", type=int)
    parser.add_argument("--tu", action="append", default=[])
    parser.add_argument("--shim", action="append", default=[])
    args = parser.parse_args()
    if args.action == "jobs":
        print(job_count(os.environ.get("GW_JOBS")))
        return 0
    root, melee = args.root.resolve(), args.melee.resolve()
    cache_path = (args.out if args.action == "game" else args.shimobj) / ".content-cache.json"
    cache = scan_stale_tus.FileCache(cache_path)
    if args.action == "game":
        config_bytes = config("game", root, cache=cache)
        names = list(dict.fromkeys(args.tu or scan_stale_tus.scan_content(args.files, melee, args.out, config_bytes, cache)))
        sources = [(name, melee / name, args.out / (name.replace("/", "_") + ".obj")) for name in names]
        script = root / "_build/masstest/pipe_win.sh"
        jobs = [(name, [shutil.which("bash") or "bash", script.as_posix(), name]) for name in names]
        print(f"TUs stale: {len(names)}", flush=True)
        def on_success(name):
            source = melee / name
            obj = args.out / (name.replace("/", "_") + ".obj")
            record(obj, source, melee, config_bytes, record_cache)
    else:
        names = list(dict.fromkeys(args.shim or ([p.name for p in shim_sources(melee)] if args.action == "record-shims" else scan_shims(melee, args.shimobj, root, cache))))
        shim_configs = {}
        def shim_config(source):
            mode = (source.suffix, source.name.startswith("gw_fx_") and source.suffix == ".cpp")
            if mode not in shim_configs:
                shim_configs[mode] = config("shim", root, source, cache)
            return shim_configs[mode]
        if args.action == "record-shims":
            for name in names:
                source = melee / "pc/platform" / name
                record(args.shimobj / (source.stem + ".obj"), source, melee, shim_config(source), cache)
            cache.save()
            return 0
        print(f"shims stale: {len(names)}", flush=True)
        jobs = [(name, [shutil.which("bash") or "bash", "-c",
                        '. "$GW_ROOT/tools/port/portlib.sh"; gw_build_shim "$1"', "shim", name])
                for name in names]
        def on_success(name):
            source = melee / "pc/platform" / name
            record(args.shimobj / (source.stem + ".obj"), source, melee,
                   shim_config(source), record_cache)
    for name, source, obj in (sources if args.action == "game" else
                              [(n, melee / "pc/platform" / n, args.shimobj / (Path(n).stem + ".obj")) for n in names]):
        if not source.is_file():
            raise RuntimeError(f"missing source: {source}")
        preserve_object(obj)
        # An interrupted compile must never leave a valid key or old object behind.
        object_paths(obj)[1].unlink(missing_ok=True)
        obj.unlink(missing_ok=True)
    if jobs:
        cache.save()
        # Compilers may replace generated inputs/depfiles after scanning. Restat
        # in the recording pass while still sharing hashes among completed TUs.
        record_cache = scan_stale_tus.FileCache(cache_path)
        env = os.environ.copy()
        env.update(GW_ROOT=root.as_posix(), GW_MELEE=melee.as_posix(),
                   GW_OUT=args.out.resolve().as_posix(),
                   GW_SHIMOBJ=args.shimobj.resolve().as_posix())
        workers = job_count(str(args.jobs)) if args.jobs is not None else job_count(os.environ.get("GW_JOBS"))
        run_jobs(jobs, workers, on_success, melee, env)
        record_cache.save()
    else:
        cache.save()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        sys.exit(f"build objects failed: {exc}")
