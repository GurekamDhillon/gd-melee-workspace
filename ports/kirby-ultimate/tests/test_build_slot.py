"""Structural checks for the explicit, unmounted Ultimate Kirby m-ex package."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ports/kirby-ultimate/tools"))
sys.path.insert(0, str(ROOT / "tools/mex_port"))
import build_slot  # noqa: E402
from mex_hsd import Archive  # noqa: E402

BASE = ROOT / "ports/halberd/mods-slot/metaknight-slot/files/MxDt.dat"


class BuildSlotTest(unittest.TestCase):
    def test_requires_eight_explicit_costumes(self):
        with self.assertRaisesRegex(ValueError, "all eight"):
            build_slot.parse_costumes(["0:PlKbNr.dat"])
        with self.assertRaisesRegex(ValueError, "duplicate costume"):
            build_slot.parse_costumes(["0:a", "0:b"])

    @unittest.skipUnless(BASE.is_file(), "local ACE m-ex base is required")
    def test_own_animation_and_eight_costume_table(self):
        raw = BASE.read_bytes()
        self.assertEqual(build_slot.row_info(raw, 53, 52), ("Lucina", "PlLu.dat"))
        patched = build_slot.own_anim_and_costumes(raw, 53, 52)
        ar = Archive(patched)
        ft = ar.u32(ar.public("mexData") + 8)
        info = ar.u32(ft + 0x10)
        self.assertEqual(ar.data[info + 4 * 52], 8)
        table = ar.u32(ar.u32(ft + 0x14) + 4 * 53)
        for index, color in enumerate(build_slot.COLORS):
            self.assertEqual(build_slot.cstring(ar.data, ar.u32(table + 16 * index)),
                             f"PlUk{color}.dat")
            self.assertEqual(ar.u32(table + 16 * index + 12), index if index < 6 else index - 6)
        anim = ar.u32(ft + 0x1C)
        self.assertEqual(build_slot.cstring(ar.data, ar.u32(anim + 4 * 53)), "PlUkAJ.dat")

    @unittest.skipUnless(BASE.is_file(), "local ACE m-ex base is required")
    def test_replacement_name_must_match_before_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "unmounted-slot"
            with self.assertRaisesRegex(ValueError, "not 'Wolf SSBU'"):
                build_slot.build(Path(folder) / "missing-source", BASE.parent, output,
                                 53, 52, "Wolf SSBU", "Ultimate Kirby", [])
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
