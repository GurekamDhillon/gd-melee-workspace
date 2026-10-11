"""Background Blender proof on authored fixtures, with all writes in .omo."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def test_figatree_actions_in_background_blender(tmp_path):
    candidates = (os.environ.get("GW_BLENDER"), shutil.which("blender"),
                  r"D:\SteamLibrary\steamapps\common\Blender\blender.exe")
    exe = next((p for p in candidates if p and Path(p).is_file()), None)
    if not exe:
        pytest.skip("Blender unavailable; see README background command")
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE="1", TEMP=str(tmp_path), TMP=str(tmp_path),
               BLENDER_USER_RESOURCES=str(tmp_path / "blender-user"),
               BLENDER_USER_CONFIG=str(tmp_path / "blender-user/config"),
               BLENDER_USER_SCRIPTS=str(tmp_path / "blender-user/scripts"),
               BLENDER_USER_DATAFILES=str(tmp_path / "blender-user/datafiles"))
    run = subprocess.run([exe, "--background", "--factory-startup", "--disable-autoexec", "-noaudio",
                          "--threads", "1", "--python-exit-code", "1", "--python",
                          str(HERE / "blender_figatree_check.py"), "--", str(tmp_path)],
                         cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    output = run.stdout + run.stderr
    (tmp_path / "blender-figatree.log").write_text(output, encoding="utf-8")
    assert run.returncode == 0, output[-6000:]
    assert "FIGATREE ACTIONS OK" in output, output[-6000:]
