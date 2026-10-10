"""Open Blender on the Goku export rig with the Geno > Splice panel ready (no engine server needed).

    python tools/blender/geno_workbench/splice_goku.py [--check]

Outside Blender this starts Blender with itself as the --python script; inside Blender it registers the add-on,
points Project at ports/goku-xv2 and selects GokuExport. Paths (override by environment):
  GW_BLENDER  blender.exe        GW_ART   the Goku .blend (default <GW_ROOT>/_build/goku-xv2/author-source/goku.blend)
  GW_PROJECT  ports/goku-xv2 checkout WITH local ir/ (default: this checkout's, else GW_ROOT's)
  GW_SITE     dir holding scipy + Pillow for Blender's Python (pip install --target, never global)
Local XV2 data is read only; nothing is written under git.
"""
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("GW_ROOT", "E:/Projects/Melee Workspace"))


def _inside_blender():
    try:
        import bpy  # noqa: F401
        return bool(getattr(sys.modules["bpy"], "app", None)) and "--splice-goku" in sys.argv
    except ImportError:
        return False


def _setup():
    import bpy
    for extra in filter(None, os.environ.get("GW_SITE", "").split(os.pathsep)):
        sys.path.insert(0, extra)
    sys.path.insert(0, str(HERE.parent))
    import geno_workbench
    geno_workbench.register()
    bpy.context.scene.geno_wb.project = os.environ["GW_PROJECT"]
    arm = bpy.data.objects["GokuExport"]
    bpy.context.view_layer.objects.active = arm
    for obj in bpy.data.objects:
        obj.select_set(obj == arm)
    print("GENO_WB_CHECK splice_goku ready project=%s" % os.environ["GW_PROJECT"])


def main():
    env = dict(os.environ)
    blender = env.get("GW_BLENDER", "D:/SteamLibrary/steamapps/common/Blender/blender.exe")
    art = env.get("GW_ART", str(ROOT / "_build/goku-xv2/author-source/goku.blend"))
    project = env.get("GW_PROJECT")
    if not project:
        local = HERE.parents[2] / "ports/goku-xv2"
        project = str(local if (local / "ir/goku.xv2.ir.json").is_file() else ROOT / "ports/goku-xv2")
    env["GW_PROJECT"] = project
    site = HERE.parents[2] / "_build/wbnla-site"
    if "GW_SITE" not in env and site.is_dir():
        env["GW_SITE"] = str(site)
    cmd = [blender] + (["--background", "--factory-startup"] if "--check" in sys.argv else []) + [
        art, "--python", str(Path(__file__).resolve()), "--", "--splice-goku"]
    return subprocess.call(cmd, env=env)


if _inside_blender():
    _setup()
elif __name__ == "__main__":
    sys.exit(main())
