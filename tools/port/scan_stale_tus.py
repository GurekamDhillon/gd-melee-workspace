#!/usr/bin/env python3
"""Batch the existing conservative game-TU timestamp scan into one process.

--compare runs the preserved shell scan against the same tree and reports a
unified diff if either membership or manifest order differs. It does not build.
"""

import argparse
import difflib
import glob
import os
from pathlib import Path
import shutil
import subprocess
import sys


PORT = Path(__file__).resolve().parent
ROOT = PORT.parent.parent


def newest_header(files: Path, melee: Path):
    """Match find -name '*.h' -newer files.txt across the three old roots."""
    manifest_time = files.stat().st_mtime_ns
    newest = None
    for root in (melee / "src", melee / "include", melee / "pc" / "geno"):
        for base, dirs, names in os.walk(root, followlinks=False):
            for name in dirs + names:
                if not name.endswith(".h"):
                    continue
                try:
                    modified = (Path(base) / name).stat().st_mtime_ns
                except OSError:
                    continue
                if modified > manifest_time and (newest is None or modified > newest):
                    newest = modified
    return newest


def scan(files: Path, melee: Path, out: Path):
    """Return exactly the old scan's ordered list of stale, existing TUs."""
    if not files.is_file():
        return []
    header_time = newest_header(files, melee)
    # The old `tr -d '\r'` removes every CR byte, not just CRLF line endings.
    manifest = files.read_bytes().replace(b"\r", b"").decode("utf-8")
    stale = []
    for file_name in manifest.split("\n"):
        if not file_name:
            continue
        source = melee / file_name
        if not source.exists():
            continue
        obj = out / (file_name.replace("/", "_") + ".obj")
        if not obj.is_file():
            stale.append(file_name)
            continue
        obj_time = obj.stat().st_mtime_ns
        if source.stat().st_mtime_ns > obj_time:
            stale.append(file_name)
            continue
        # Bash expands "${src%.c}"_*.inc even for unusual manifest entries.
        stem = str(source)[:-2] if str(source).endswith(".c") else str(source)
        if any(Path(part).exists() and Path(part).stat().st_mtime_ns > obj_time
               for part in glob.glob(stem + "_*.inc")):
            stale.append(file_name)
            continue
        if header_time is not None and header_time > obj_time:
            stale.append(file_name)
    return stale


def compare(files: Path, melee: Path, out: Path, current, bash: str):
    legacy = PORT / "scan_stale_tus_legacy.sh"
    result = subprocess.run(
        [bash, str(legacy), str(files), str(melee), str(out)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
        raise RuntimeError(f"legacy stale scan failed with exit {result.returncode}")
    old = result.stdout.decode("utf-8").splitlines()
    if old != current:
        sys.stderr.writelines(difflib.unified_diff(
            [name + "\n" for name in old], [name + "\n" for name in current],
            fromfile="legacy", tofile="python",
        ))
        return False
    print(f"stale scan match: {len(current)} TU(s)")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files", type=Path, default=ROOT / "_build/masstest/files.txt")
    parser.add_argument("--melee", type=Path, default=Path(os.environ.get("GW_MELEE", ROOT / "melee")))
    build_root = Path(os.environ.get("GW_BUILD_ROOT", ROOT / "_build"))
    parser.add_argument("--out", type=Path, default=Path(os.environ.get("GW_OUT", build_root / "masstest/out")))
    parser.add_argument("--output", type=Path, help="write the ordered stale list for xargs")
    parser.add_argument("--compare", action="store_true", help="diff against the previous shell scan")
    parser.add_argument("--bash", default=shutil.which("bash") or "bash",
                        help="Git Bash executable for --compare")
    args = parser.parse_args()

    current = scan(args.files, args.melee, args.out)
    if args.compare and not compare(args.files, args.melee, args.out, current, args.bash):
        return 1
    data = "".join(name + "\n" for name in current).encode("utf-8")
    if args.output:
        args.output.write_bytes(data)
    elif not args.compare:
        sys.stdout.buffer.write(data)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, UnicodeError) as exc:
        sys.exit(f"stale scan failed: {exc}")
