"""One command: open Blender with Captain Falcon (Geno Falcon) driven by the real engine.

    python tools/blender/geno_workbench/launch_falcon.py            # interactive
    python tools/blender/geno_workbench/launch_falcon.py --check    # background report

Builds what is missing (falcon/make_falcon_art.py: the .blend from your disc), stages the Geno Falcon
package as a mods dir under _build/geno-falcon-art/mods, writes a project with absolute paths under
_build/geno-falcon-art/project (from falcon/project/), then runs launch_goku.py with those. Other
arguments pass through to launch_goku.py. Everything generated stays under _build/.
  GW_FALCON_PACKAGE  the built Geno Falcon mod dir (default <root>/_build/falcon-look/geno-falcon)
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "falcon"))
import make_falcon_art  # noqa: E402


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        paths = make_falcon_art.tools_config.load_config()
    except make_falcon_art.tools_config.ToolsConfigError as exc:
        print("ERROR: %s" % exc)
        return 2
    root = Path(paths["GW_ROOT"])
    out = root / "_build/geno-falcon-art"
    saved = sys.argv
    sys.argv = ["make_falcon_art.py"]
    try:
        rc = make_falcon_art.main()
    finally:
        sys.argv = saved
    if rc:
        return rc
    package = Path(paths.get("GW_FALCON_PACKAGE") or root / "_build/falcon-look/geno-falcon")
    if not (package / "files/plan.json").is_file():
        print("missing the Geno Falcon package: %s (set GW_FALCON_PACKAGE)" % package)
        return 2
    mods = out / "mods"
    dest = mods / "geno-falcon"
    if not (dest / "files/plan.json").is_file() or \
            (package / "files/plan.json").stat().st_mtime > (dest / "files/plan.json").stat().st_mtime:
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(package, dest)
    mods.mkdir(parents=True, exist_ok=True)
    (mods / "enabled.txt").write_text("geno-falcon\n")
    template = HERE / "falcon/project"
    proj = out / "project"
    proj.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((template / "workbench.json").read_text(encoding="utf-8"))
    for key in ("plan_abs", "art_blend", "mods_dir"):
        cfg[key] = str(root / cfg[key])
    (proj / "workbench.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    shutil.copy2(template / "gameplay.json", proj / "gameplay.json")
    cmd = [sys.executable, str(HERE / "launch_goku.py"), "--project", str(proj), "--art", cfg["art_blend"],
           "--mods", str(mods), "--work", str(root / "_build/wb-falcon")] + argv
    env = dict(paths)
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    sys.exit(main())
