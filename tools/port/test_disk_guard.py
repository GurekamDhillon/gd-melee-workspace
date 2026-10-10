import os
import tempfile
import unittest
from unittest.mock import patch
from collections import namedtuple

import disk_guard

Usage = namedtuple('Usage', 'total used free')
GIB = 1024 ** 3


class GuardTests(unittest.TestCase):
    def check(self, free_gb, **kw):
        with patch('shutil.disk_usage', return_value=Usage(100 * GIB, 0, int(free_gb * GIB))):
            return disk_guard.check('.', **kw)

    def test_enough_space_passes_silently(self):
        self.assertEqual(self.check(50, min_gb=20), (True, ''))

    def test_low_space_refuses_with_free_amount_and_cleanup_command(self):
        ok, msg = self.check(3.5, min_gb=20)
        self.assertFalse(ok)
        self.assertIn('3.5 GB free', msg)
        self.assertIn('disk_report.py', msg)
        self.assertIn('--allow-low-disk', msg)

    def test_override_warns_but_proceeds(self):
        ok, msg = self.check(3.5, min_gb=20, allow=True)
        self.assertTrue(ok)
        self.assertTrue(msg.startswith('warning:'))

    def test_env_threshold(self):
        with patch.dict(os.environ, {'MELEE_MIN_FREE_GB': '5'}):
            self.assertTrue(self.check(6)[0])
            self.assertFalse(self.check(4)[0])
        with patch.dict(os.environ, {'MELEE_MIN_FREE_GB': 'junk'}):
            self.assertEqual(disk_guard.min_free_gb(), 20.0)

    def test_nonexistent_path_uses_nearest_parent(self):
        with tempfile.TemporaryDirectory() as t, patch('shutil.disk_usage', return_value=Usage(1, 0, 7)) as m:
            self.assertEqual(disk_guard.free_bytes(os.path.join(t, 'a', 'b')), 7)
            self.assertEqual(os.path.abspath(str(m.call_args[0][0])), os.path.abspath(t))

    def test_cli_exit_codes(self):
        with patch('shutil.disk_usage', return_value=Usage(1, 0, 1 * GIB)):
            self.assertEqual(disk_guard.main(['--min-gb', '20']), 1)
            self.assertEqual(disk_guard.main(['--min-gb', '20', '--allow-low-disk']), 0)
            with patch.dict(os.environ, {'MELEE_ALLOW_LOW_DISK': '1'}):
                self.assertEqual(disk_guard.main(['--min-gb', '20']), 0)


if __name__ == '__main__':
    unittest.main()
