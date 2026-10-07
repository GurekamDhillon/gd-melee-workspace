"""Draw the source UI offline with captured native kit/fill calls."""
from pathlib import Path
import shutil
import subprocess
import unittest
from tools.test_support import require_game

ROOT = Path(__file__).resolve().parents[2]


class RewardUITests(unittest.TestCase):
    def test_reward_drawing_and_controller_menu(self):
        require_game('pc/scripts/examples/envoy/scripts/menu_draw.lua')
        lua = shutil.which('lua') or shutil.which('lua5.4') or shutil.which('lua5.3')
        if not lua:
            self.skipTest('Lua interpreter unavailable')
        result = subprocess.run([lua, 'tools/port/test_envoy_reward_ui.lua'], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('captured HUD/menu bars', result.stdout)


if __name__ == '__main__':
    unittest.main()
