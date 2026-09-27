#!/usr/bin/env python3
"""Read Gr*.dat directly from GW_ISO_ACE and inspect/export its model parts.

All disc-derived output is confined to _build/tmp/stage-parts/. The ISO is
opened only for reading, and no extracted DAT is written to disk.
"""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STAGES = ("GrNBa", "GrNLa", "GrSt", "GrNKr")


def output_root(root=ROOT):
    return root / "_build" / "tmp" / "stage-parts"


def iso_from_env(root=ROOT):
    for line in (root / ".env").read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*(?:export\s+)?GW_ISO_ACE\s*=\s*(.*?)\s*$", line)
        if match:
            value = match.group(1).strip().strip('"\'')
            path = Path(os.path.expandvars(value)).expanduser()
            return path if path.is_absolute() else root / path
    raise ValueError("GW_ISO_ACE is missing from .env")


def stage_filename(name):
    stem = name[:-4] if name.lower().endswith(".dat") else name
    if not re.fullmatch(r"Gr[A-Za-z0-9]+", stem):
        raise ValueError(f"invalid stage name: {name!r}")
    return stem + ".dat"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stages", nargs="*", default=DEFAULT_STAGES,
                        help="Gr*.dat names (default: Battlefield, FD, Yoshi's Story, Adventure Mushroom Kingdom)")
    args = parser.parse_args(argv)
    stages = [stage_filename(s) for s in args.stages]
    iso = iso_from_env()
    if not iso.is_file():
        parser.error("GW_ISO_ACE does not point to a file")

    # Import the shared read-only disc FST reader without copying stage bytes.
    sys.path.insert(0, str(ROOT / "tools" / "mex_port"))
    from mex_hsd import Gcm

    out = output_root()
    out.mkdir(parents=True, exist_ok=True)
    project = Path(__file__).with_name("StageParts.csproj")
    subprocess.run(["dotnet", "build", str(project), "-c", "Release", "--nologo",
                    "-p:NuGetAudit=false"], check=True)
    helper = out / "build" / "Release" / "net8.0" / "StageParts.dll"
    disc = Gcm(iso)
    for name in stages:
        raw = disc.read(name)
        stage_out = out / name[:-4]
        stage_out.mkdir(exist_ok=True)
        result = subprocess.run(["dotnet", str(helper), name[:-4], str(stage_out)],
                                input=raw, check=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        print(result.stdout.decode("utf-8", "replace").strip())
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
