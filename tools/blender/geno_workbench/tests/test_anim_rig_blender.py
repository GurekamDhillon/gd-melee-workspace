"""Runs blender_anim_rig_check.py in background Blender on a synthetic humanoid (tall and stub variants). Skipped without Blender."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))


def blender():
    for candidate in (os.environ.get("GW_BLENDER"), shutil.which("blender"), r"D:\SteamLibrary\steamapps\common\Blender\blender.exe",
                      r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"):
        if candidate and Path(candidate).is_file():
            return candidate
    try:
        import launch
        found = launch.find_blender()
        if found and Path(found).is_file():
            return found
    except Exception:  # noqa: BLE001
        pass
    return None


@pytest.mark.parametrize("variant", ["tall", "stub"])
def test_rig_and_hand_bake_in_blender(variant):
    exe = blender()
    if not exe:
        pytest.skip("no Blender")
    run = subprocess.run([exe, "-b", "--factory-startup", "--python", str(HERE / "blender_anim_rig_check.py"), "--", "--synthetic", variant],
                         capture_output=True, text=True, timeout=300)
    out = run.stdout + run.stderr
    assert f"ANIMRIG OK {variant}" in out, out[-3000:]
