"""Rapid-jab loop timing and archive pointer checks."""

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "ports/kirby-ultimate/tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_rapid_jab", TOOLS / "build_rapid_jab.py")
rapid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rapid)


class RapidJabTests(unittest.TestCase):
    def test_source_has_eight_two_frame_pulses(self):
        source = rapid.source_hitbox(rapid.DEFAULT_IR)
        self.assertEqual(source["damage"], 0.2)
        self.assertEqual(source["offset"], [0.0, 5.5, 15.0])

    def test_loop_script_has_source_cadence_and_exit_checks(self):
        base = rapid.side.mex_hsd.Archive(rapid.DEFAULT_BASE.read_bytes())
        hitbox = rapid.source_hitbox(rapid.DEFAULT_IR)
        words, goto_index = rapid.make_loop(base, hitbox)
        events = rapid.decode_loop(words)
        self.assertEqual([frame for frame, op, _ in events if op == 11],
                         [frame for frame in range(0, 16, 2) for _ in (0, 1)])
        self.assertEqual([frame for frame, op, _ in events if op == 16],
                         list(range(1, 16, 2)))
        self.assertEqual([frame for frame, op, _ in events if op == 20],
                         list(range(1, 16, 2)))
        self.assertEqual([damage for _, op, damage in events if op == 11],
                         [damage for damage in (0, 0, 1, 0, 0, 0, 0, 1)
                          for _ in (0, 1)])
        self.assertEqual(words[goto_index - 2] >> 26, 8)
        self.assertEqual(words[goto_index - 1] >> 26, 7)

    def test_archive_patch_is_byte_stable_and_relocates_self_goto(self):
        base_bytes = rapid.DEFAULT_BASE.read_bytes()
        hitbox = rapid.source_hitbox(rapid.DEFAULT_IR)
        once, changed = rapid.patch_archive(base_bytes, base_bytes, hitbox)
        twice, changed_again = rapid.patch_archive(once, base_bytes, hitbox)
        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(once, twice)
        archive = rapid.side.mex_hsd.Archive(once)
        at = rapid.side.script_pointer(archive, 50)
        words = rapid.read_loop(archive, at)
        self.assertEqual(words[-1], at)
        self.assertIn(at + (len(words) - 1) * 4, archive.reloc_set)


if __name__ == "__main__":
    unittest.main()
