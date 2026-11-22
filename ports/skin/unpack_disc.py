#!/usr/bin/env python3
"""Unpack the fighter files of a Brawl disc image into a folder, by driving an installed DolphinTool.

    python ports/skin/unpack_disc.py <disc image> <output folder> [--all]

Only the game partition's `fighter/` directory is extracted unless --all is given. The result is the same kind of
tree `brawl_root()` accepts (a folder that contains `fighter/<name>/Fit<Name>NN.pac`), so the skin wizard can start
from it. No keys or game data live in this repo: DolphinTool reads the image you give it. The image path is never
printed or logged.

DolphinTool is found from, in order: the SKIN_DOLPHINTOOL environment variable, a `DolphinTool` on PATH, and the
usual install folders. Install Dolphin (5.0-17xxx or later ships DolphinTool) if none is found.
"""
import argparse
import os
import shutil
import subprocess
import sys

CANDIDATES = [
    os.environ.get("SKIN_DOLPHINTOOL", ""),
    shutil.which("DolphinTool") or "",
    shutil.which("dolphin-tool") or "",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Brawl Online\resources\dolphin\DolphinTool.exe"),
    os.path.expandvars(r"%ProgramFiles%\Dolphin\DolphinTool.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Dolphin\DolphinTool.exe"),
    "/usr/bin/dolphin-tool",
    "/Applications/Dolphin.app/Contents/MacOS/dolphin-tool",
]


def find_tool():
    for c in CANDIDATES:
        if c and os.path.isfile(c):
            return c
    return None


def fighter_root(out_dir):
    """Return the folder that holds `fighter/`, wherever DolphinTool put it (it may add DATA/ and files/)."""
    for sub in ("", "files", os.path.join("DATA", "files"), "DATA"):
        root = os.path.join(out_dir, sub) if sub else out_dir
        if os.path.isdir(os.path.join(root, "fighter")):
            return root
    return None


def unpack(image, out_dir, everything=False):
    """Extract `fighter/` (or the whole game partition) from a disc image. Returns the folder holding `fighter/`."""
    if not os.path.isfile(image):
        raise SystemExit("unpack_disc: the disc image was not found")
    tool = find_tool()
    if not tool:
        raise SystemExit("unpack_disc: DolphinTool was not found. Install Dolphin, or set SKIN_DOLPHINTOOL to "
                         "DolphinTool's path, or unpack the disc yourself and point the wizard at that folder.")
    os.makedirs(out_dir, exist_ok=True)
    already = fighter_root(out_dir)
    if already:
        return already
    cmd = [tool, "extract", "-i", image, "-o", out_dir, "-g", "-q"]
    if not everything:
        cmd += ["-s", "fighter"]
    # The image path is passed to the tool but never echoed.
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "").strip().replace(image, "<disc image>")
        raise SystemExit("unpack_disc: extraction failed (%d): %s" % (r.returncode, msg[:400]))
    root = fighter_root(out_dir)
    if not root:
        raise SystemExit("unpack_disc: extraction finished but no fighter/ folder was produced. Is this a Brawl disc?")
    return root


def main():
    ap = argparse.ArgumentParser(description="Unpack a Brawl disc image's fighter files with DolphinTool.")
    ap.add_argument("image")
    ap.add_argument("out")
    ap.add_argument("--all", action="store_true", help="extract the whole game partition, not only fighter/")
    a = ap.parse_args()
    root = unpack(a.image, a.out, a.all)
    n = sum(1 for d in os.listdir(os.path.join(root, "fighter")) if os.path.isdir(os.path.join(root, "fighter", d)))
    print("unpacked: %s  (%d fighter folders)" % (root, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
