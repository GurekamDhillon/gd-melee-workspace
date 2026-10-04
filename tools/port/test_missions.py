"""Offline mission runtime acceptance; no engine executable is invoked."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class MissionsTests(unittest.TestCase):
    def test_runtime_contracts(self):
        result = subprocess.run([shutil.which('lua') or 'lua',
                                 'pc/tests/missions_runtime.lua'], cwd=ROOT / 'melee',
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('0 failed', result.stdout)

    def test_validation_refusals(self):
        result = subprocess.run([shutil.which('lua') or 'lua',
                                 'pc/tests/missions_validation.lua'], cwd=ROOT / 'melee',
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('0 failed', result.stdout)

    def test_bundle_current_and_single_entry(self):
        spec = importlib.util.spec_from_file_location('missions_bundle', ROOT / 'tools/port/missions_bundle.py')
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        path = ROOT / 'melee/pc/scripts/examples/missions/scripts/main.lua'
        self.assertEqual(path.read_text(encoding='utf-8'), module.bundle())
        self.assertLess(len(path.read_text(encoding='utf-8').splitlines()), 400)


if __name__ == '__main__':
    unittest.main()
