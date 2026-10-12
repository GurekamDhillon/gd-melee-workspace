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


@pytest.mark.parametrize("variant", ["tall", "stub", "bare"])
def test_rig_and_hand_bake_in_blender(variant):
    exe = blender()
    if not exe:
        pytest.skip("no Blender")
    run = subprocess.run([exe, "-b", "--factory-startup", "--python", str(HERE / "blender_anim_rig_check.py"), "--", "--synthetic", variant],
                         capture_output=True, text=True, timeout=300)
    out = run.stdout + run.stderr
    assert f"ANIMRIG OK {variant}" in out, out[-3000:]


@pytest.mark.parametrize("variant", ["tall", "stub", "bare"])
def test_panel_operators_in_blender(variant):
    """Generate rig / Switch space / to IK / to FK as operators, from object, pose and edit mode (Falcon's mode-switch failure)."""
    exe = blender()
    if not exe:
        pytest.skip("no Blender")
    run = subprocess.run([exe, "-b", "--factory-startup", "--python", str(HERE / "blender_anim_ui_check.py"), "--", "--synthetic", variant],
                         capture_output=True, text=True, timeout=300)
    out = run.stdout + run.stderr
    assert "ANIMUI OK synthetic" in out, out[-3000:]


def _art(rel):
    """The local art lives under _build of the main checkout (a lane worktree has none of its own)."""
    here = HERE.parents[3]
    for root in (os.environ.get("GW_ROOT"), here, here.parent.parent):
        if root and (Path(root) / rel).is_file():
            return Path(root) / rel
    return here / rel


REAL = {"falcon": _art("_build/geno-falcon-art/falcon.blend"), "goku": _art("_build/goku-xv2/author-source/goku.blend")}


@pytest.mark.parametrize("fighter", sorted(REAL))
def test_real_fighter_copy(fighter, tmp_path):
    """The same checks on a COPY of the real fighter's .blend (skipped when the local art is not built)."""
    exe = blender()
    src = REAL[fighter]
    if not exe or not src.is_file():
        pytest.skip("no Blender or no local art")
    blend = tmp_path / f"{fighter}.blend"
    shutil.copy(src, blend)
    for script, ok in (("blender_anim_rig_check.py", f"ANIMRIG OK {fighter}"), ("blender_anim_ui_check.py", f"ANIMUI OK {fighter}")):
        extra = ["--hand", str(tmp_path / "hand.json")] if script == "blender_anim_rig_check.py" else []
        run = subprocess.run([exe, "-b", "--factory-startup", "--python", str(HERE / script), "--", "--blend", str(blend)] + extra,
                             capture_output=True, text=True, timeout=900)
        out = run.stdout + run.stderr
        assert ok in out, out[-3000:]
