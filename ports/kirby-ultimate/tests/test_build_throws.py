"""Checks for Ultimate absolute throw data on Melee Kirby's host actions."""

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "ports/kirby-ultimate/tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_throws", TOOLS / "build_throws.py")
throws = importlib.util.module_from_spec(spec)
spec.loader.exec_module(throws)


class ThrowPayloadTests(unittest.TestCase):
    def test_release_frames_come_from_ultimate_game_scripts(self):
        source = throws.source_throws(throws.DEFAULT_IR)
        self.assertEqual({row: entry["release_frame"] for row, entry in source.items()},
                         {247: 45, 248: 41, 249: 51, 250: 58})

    def test_four_absolute_throws_and_source_release_frames(self):
        from build_side_b import mex_hsd, script_pointer, flatten

        original = throws.DEFAULT_BASE.read_bytes()
        source = throws.source_throws(throws.DEFAULT_IR)
        changed_bytes, rows = throws.patch_archive(original, source)
        self.assertEqual(rows, [247, 248, 249, 250])
        self.assertEqual(throws.patch_archive(changed_bytes, source)[1], [])
        self.assertEqual(throws.patch_archive(changed_bytes, source)[0], changed_bytes)

        archive = mex_hsd.Archive(changed_bytes)
        expected = {247: (5, 75, 125, 40), 248: (8, 130, 120, 30),
                    249: (10, 78, 74, 75), 250: (2, 63, 180, 60)}
        for row, (damage, angle, kbg, bkb) in expected.items():
            with self.subTest(row=row):
                found = throws.throw_words(archive, row)
                self.assertEqual(len(found), 2)
                first = found[0][1]
                self.assertEqual(first[0] & 0x7FFFFF, damage)
                self.assertEqual((first[1] >> 23) & 0x1FF, angle)
                self.assertEqual((first[1] >> 14) & 0x1FF, kbg)
                self.assertEqual((first[2] >> 23) & 0x1FF, bkb)
                self.assertEqual(found[1][1][0] & 0x7FFFFF, 3)
                releases = [frame for frame, op, _, _ in flatten(archive, row) if op == 20]
                self.assertEqual(releases, [source[row]["release_frame"]])
                if row in (247, 249):
                    self.assertEqual(script_pointer(archive, row),
                                     script_pointer(mex_hsd.Archive(original), row))
                else:
                    self.assertNotEqual(script_pointer(archive, row),
                                        script_pointer(mex_hsd.Archive(original), row))


if __name__ == "__main__":
    unittest.main()
