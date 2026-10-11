"""Run the Projectiles self-tests in a background Blender (skipped when Blender is not installed)."""
import os
import subprocess
from pathlib import Path

import pytest

ADDON = Path(__file__).resolve().parents[1]
CANDIDATES = [os.environ.get("GW_BLENDER", ""), r"D:\SteamLibrary\steamapps\common\Blender\blender.exe"]
BLENDER = next((c for c in CANDIDATES if c and Path(c).is_file()), None)


@pytest.mark.skipif(BLENDER is None, reason="no Blender")
@pytest.mark.parametrize("script,ok", [("selftest_projectiles.py", "PROJECTILES SELFTEST OK"),
                                       ("selftest_projectiles_session.py", "PROJECTILES SESSION OK")])
def test_blender_selftest(script, ok):
    out = subprocess.run([BLENDER, "-b", "--factory-startup", "--python", str(ADDON / script)],
                         capture_output=True, text=True, timeout=240, encoding="utf-8", errors="replace")
    assert ok in out.stdout, out.stdout[-2000:] + out.stderr[-1000:]
    assert "FAIL " not in out.stdout
