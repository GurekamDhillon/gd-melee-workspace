#!/usr/bin/env python3
"""Run the map editor's mission-layer Lua tests (stub gd; no game, no engine) under plain lua.

    python -m unittest discover -s tools/port -p "test_map_mission.py"

Skips cleanly when `lua` (5.4, as embedded in the game) is not on PATH.
"""
import shutil
import subprocess
import sys
import unittest
from tools.test_support import GAME, require_game
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MELEE = GAME
LUA = shutil.which('lua')


@unittest.skipUnless(LUA, 'lua is not on PATH')
class MapMissionTests(unittest.TestCase):
    def run_lua(self, script):
        require_game(script)
        # The tests load files relative to melee/, like the other pc/tests Lua scripts.
        return subprocess.run([LUA, script], cwd=MELEE, capture_output=True, text=True, timeout=120)

    def test_mission_module_and_editor_layer(self):
        r = self.run_lua('pc/tests/map_mission_test.lua')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('0 failed', r.stdout)

    def test_existing_editor_contract_still_passes(self):
        r = self.run_lua('pc/tests/map_editor_test.lua')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_main_embeds_the_current_mission_module(self):
        require_game('pc/scripts/examples/map_editor/scripts/mission.lua')
        r = subprocess.run([sys.executable, str(ROOT / 'tools/port/map_mission_sync.py'), '--check'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
