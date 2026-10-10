"""Prune old run sandboxes under <build root>/runs.

Deletes sandboxes past --keep (default 40, MELEE_RUNS_KEEP) and strips the exe/dll/cache copies from
those past --strip-after (default 10, MELEE_RUNS_STRIP_AFTER), newest first by mtime. Never touches a
sandbox with a running game or a launch marker, and preserves everything when the process list
cannot be read. It only ever acts on direct children of --root.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

# Files that make a sandbox big (an exe copy, runtime DLLs, shader/pipeline caches). A stripped run
# keeps everything else: melee-pc.log, crashlogs/, results/, scripts-data, perf.json, the map.
STRIP_SUFFIXES = ('.exe', '.dll')
STRIP_NAMES = ('dawn_cache.db', 'initial_pipeline_cache.db', 'initial_pipeline_cache.core')
# An unstamped sandbox (made by another launcher) only becomes prunable once this old.
UNSTAMPED_MIN_AGE_S = 3 * 24 * 3600


def normalized(path):
    return str(Path(path).resolve()).replace('\\', '/').casefold()


def live_games():
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
            "$ErrorActionPreference='Stop'; $p=@(Get-CimInstance Win32_Process -Filter \"Name='melee-pc.exe'\"); "
            "if (@($p | Where-Object { -not $_.ExecutablePath }).Count) { exit 2 }; "
            "ConvertTo-Json -Compress -InputObject @($p | ForEach-Object { $_.ExecutablePath })"],
            capture_output=True, text=True, check=True)
        paths = json.loads(result.stdout)
        return paths if isinstance(paths, list) and all(isinstance(p, str) and p for p in paths) else None
    except (OSError, ValueError, subprocess.CalledProcessError):
        return None


def strippable(name):
    low = name.lower()
    return low.endswith(STRIP_SUFFIXES) or low in STRIP_NAMES


def plan(entries, keep, strip_after, current, active, now, unstamped_min_age=UNSTAMPED_MIN_AGE_S):
    """Pure selection. entries: [(name, mtime, stamped)]; active: names with a live game.

    Returns (delete, strip): names to remove whole, names to strip the exe/dll/cache copies from.
    Newest first by mtime. Never selects `current` or an active name. An unstamped entry younger
    than `unstamped_min_age` is protected, though it still occupies a retention slot."""
    ordered = sorted(entries, key=lambda e: e[1], reverse=True)
    delete, strip = [], []
    for rank, (name, mtime, stamped) in enumerate(ordered):
        if name == current or name in active:
            continue
        if rank >= max(0, keep):
            if stamped or now - mtime >= unstamped_min_age:
                delete.append(name)
        elif rank >= max(0, strip_after):
            strip.append(name)
    return delete, strip


def dir_size(path):
    total = 0
    for dirpath, _, files in os.walk(path):
        for f in files:
            try:
                total += os.lstat(os.path.join(dirpath, f)).st_size
            except OSError:
                pass
    return total


def prune(root, keep, current, live, strip_after=10, log=print, now=None):
    root = Path(root).resolve()
    if live is None:
        print('run pruning skipped: active process paths could not be verified', file=sys.stderr)
        return
    now = time.time() if now is None else now
    active = {normalized(p) for p in live}
    if normalized(root / current / 'melee-pc.exe') in active:
        raise RuntimeError(f'sandbox {current!r} already running; choose another name')
    entries, paths = [], {}
    for path in root.iterdir():
        # Resolve and validate every recursive deletion target, including junctions.
        if not path.is_dir() or path.is_symlink() or path.resolve().parent != root:
            continue
        stamp = path / '.last_run'
        stamped = stamp.is_file()
        entries.append((path.name, (stamp if stamped else path).stat().st_mtime, stamped))
        paths[path.name] = path
    running = {n for n, p in paths.items() if normalized(p / 'melee-pc.exe') in active}
    delete, strip = plan(entries, keep, strip_after, current, running, now)
    freed = 0
    for name in delete + strip:
        path = paths[name]
        lock = path / '.active-run'
        try:
            # The runner claims the same directory before copying or launching.
            # This atomic claim closes the start-versus-prune race.
            lock.mkdir()
        except (FileExistsError, FileNotFoundError):
            continue
        try:
            if path.resolve().parent != root:
                continue
            if name in delete:
                size = dir_size(path)
                shutil.rmtree(path)
                freed += size
                log(f'pruned run {name} ({size / 2**20:.0f} MB)')
            else:
                size = 0
                for f in path.iterdir():
                    if f.is_file() and not f.is_symlink() and strippable(f.name):
                        size += f.stat().st_size
                        f.unlink()
                if size:
                    freed += size
                    log(f'stripped run {name}: exe/dll/cache copies, {size / 2**20:.0f} MB (logs kept)')
        finally:
            if lock.exists():
                lock.rmdir()
    if freed:
        log(f'run pruning freed {freed / 2**20:.0f} MB under {root}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--keep', type=int,
                        default=int(os.environ.get('MELEE_RUNS_KEEP', os.environ.get('GW_RUNS_KEEP', 40))))
    parser.add_argument('--strip-after', type=int,
                        default=int(os.environ.get('MELEE_RUNS_STRIP_AFTER', 10)))
    parser.add_argument('--current', required=True,
                        help='sandbox name being launched (never pruned); use "none" for a manual prune')
    args = parser.parse_args()
    try:
        prune(args.root, args.keep, args.current, live_games(), args.strip_after)
    except (OSError, RuntimeError) as error:
        print(f'run refused: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
