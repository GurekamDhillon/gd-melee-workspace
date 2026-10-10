"""Open Geno Falcon's complete editable Workbench project in Blender.

    python tools/blender/geno_workbench/launch_falcon.py
    python tools/blender/geno_workbench/launch_falcon.py --check

Sources, generated project, staged package and art stay under _build/geno-falcon-art.
GW_FALCON_PACKAGE selects the seed package. Existing source edits survive relaunches;
only missing assets trigger copying/extraction. Other arguments reach launch_goku.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE))
from falcon import build as falcon_build
from falcon import make_falcon_art


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = make_falcon_art.root_dir().resolve()
    try:
        paths = make_falcon_art.tools_config.load_config(root)
    except make_falcon_art.tools_config.ToolsConfigError as exc:
        print("ERROR: %s" % exc)
        return 2
    out = root / "_build/geno-falcon-art"
    rc = falcon_build.main(["--prepare", "--root", str(root)])
    if rc:
        return rc
    # Art reads the just-staged/generated package, including first launches without a seed.
    saved_argv, saved_package = sys.argv, os.environ.get("GW_FALCON_PACKAGE")
    sys.argv = ["make_falcon_art.py"]
    os.environ["GW_FALCON_PACKAGE"] = str(out / "mods/geno-falcon")
    try:
        rc = make_falcon_art.main()
    finally:
        sys.argv = saved_argv
        if saved_package is None:
            os.environ.pop("GW_FALCON_PACKAGE", None)
        else:
            os.environ["GW_FALCON_PACKAGE"] = saved_package
    if rc:
        return rc
    project = out / "project"
    cfg = json.loads((project / "workbench.json").read_text(encoding="utf-8"))
    cmd = [sys.executable, str(HERE / "launch_goku.py"), "--project", str(project), "--art", cfg["art_blend"],
           "--mods", str(out / "mods"), "--work", str(root / "_build/wb-falcon")] + argv
    env = dict(os.environ)
    env.update({k: v for k, v in paths.items() if v})
    env["GW_ROOT"] = str(root)
    if not env.get("GW_ENGINE_EXE") and not (root / "_build/wb-falcon/engine/melee-pc.exe").is_file():
        for candidate in (root / "_build/wb-goku/engine/melee-pc.exe",
                          root / "_build/agents/geno-workbench/melee-pc.exe"):
            if candidate.is_file():
                env["GW_ENGINE_EXE"] = str(candidate)
                break
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    sys.exit(main())
