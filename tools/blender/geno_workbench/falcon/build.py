"""Initialize or rebuild the local Geno Falcon Workbench project (no Blender needed).

    python tools/blender/geno_workbench/falcon/build.py --prepare
    python tools/blender/geno_workbench/falcon/build.py --project _build/geno-falcon-art/project

GW_ROOT selects generated assets; GW_MELEE selects the engine source contract.
Only a missing package triggers staging or disc extraction. Authored sources survive.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
sys.path.insert(0, str(HERE.parent))
from falcon import metadata, project_build
from falcon.make_falcon_art import root_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--game", type=Path)
    parser.add_argument("--prepare", action="store_true", help="create missing sources before rebuilding")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    try:
        root = (args.root or root_dir()).resolve()
        project = (args.project or root / "_build/geno-falcon-art/project").resolve()
        marker = project / project_build.MANIFEST
        manifest = project_build.load(marker) if marker.is_file() else {}
        game = args.game or manifest.get("game") or os.environ.get("GW_MELEE") or root / "melee"
        os.environ["GW_MELEE"] = str(Path(game).resolve())
        initial_mode = "gameplay-only"
        if args.prepare:
            package = Path(manifest.get("package") or root / "_build/geno-falcon-art/mods/geno-falcon")
            seed = manifest.get("seed_package") or os.environ.get("GW_FALCON_PACKAGE") or root / "_build/falcon-look/geno-falcon"
            initial_mode = project_build.ensure_package(package, seed, root)
            states = [] if manifest else metadata.load_states(game)
            project_build.prepare(project, package, states, HERE / "project", root=root, game=game, seed=seed)
            project_build.write(package.parent / "enabled.txt", "geno-falcon\n")
        mode = project_build.rebuild(project)
        if initial_mode != "gameplay-only":
            mode = initial_mode
        print(f"BUILD_MODE: {mode} {time.perf_counter() - started:.3f}s")
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Falcon build: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
