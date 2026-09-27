"""Ultimate grab windows on the reachable Melee Kirby host actions."""

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "ports/kirby-ultimate/tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_grabs", TOOLS / "build_grabs.py")
grabs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grabs)


class GrabTimingTests(unittest.TestCase):
    def test_stand_and_dash_grab_windows_match_source(self):
        from build_side_b import flatten, mex_hsd

        source = grabs.source_grabs(grabs.DEFAULT_IR)
        self.assertEqual(source, {242: {"active": 6, "clear": 8},
                                  243: {"active": 9, "clear": 11}})
        original = grabs.DEFAULT_BASE.read_bytes()
        patched, changed = grabs.patch_archive(original, source)
        self.assertEqual(changed, [243])
        again, changed_again = grabs.patch_archive(patched, source)
        self.assertEqual(changed_again, [])
        self.assertEqual(again, patched)
        archive = mex_hsd.Archive(patched)
        for row, times in source.items():
            with self.subTest(row=row):
                events = flatten(archive, row)
                self.assertEqual({frame for frame, op, _, _ in events if op == 11},
                                 {times["active"]})
                self.assertEqual({frame for frame, op, _, _ in events if op == 16},
                                 {times["clear"]})


if __name__ == "__main__":
    unittest.main()
