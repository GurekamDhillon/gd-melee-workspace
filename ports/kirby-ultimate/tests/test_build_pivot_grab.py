"""A distinct CatchTurn row must retain Kirby's existing grab and animation data."""

from pathlib import Path
import json
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ports/kirby-ultimate/tools"))
import build_pivot_grab as pivot  # noqa: E402
import build_side_b as side  # noqa: E402

BASE = ROOT / "_build/tmp/ultimate-kirby-additive-lab/mods/ultimate-kirby-additive-slot/files"
IR = ROOT / "experiment/character-ir/instances/kirby.ultimate.ir.json"
PROFILE = ROOT / "_build/tmp/ultimate-kirby-wave-native-lab-v2/source/geno.json"


@unittest.skipUnless((BASE / "PlUk.dat").is_file(), "local native Kirby archive required")
class PivotGrabTest(unittest.TestCase):
    def test_source_timing_and_capsules(self):
        boxes = pivot.source_grab(IR)
        self.assertEqual([(b["situation"], b["radius"], b["start"][2], b["end"][2])
                          for b in boxes],
                         [("ground", 3.1, -4.0, -15.7),
                          ("air", 1.55, -2.45, -17.25)])

    def test_append_preserves_old_rows_and_adds_source_window(self):
        fighter = (BASE / "PlUk.dat").read_bytes()
        aj = (BASE / "PlUkAJ.dat").read_bytes()
        ar = side.mex_hsd.Archive(fighter)
        row243 = side.motion_table(ar) + 243 * 0x18
        clip = aj[ar.u32(row243 + 4):ar.u32(row243 + 4) + ar.u32(row243 + 8)]
        clip = clip.replace(b"CatchDash", b"CatchTurn")
        self.assertIn(b"CatchTurn", clip)
        output, animation = pivot.append_pivot(fighter, aj, clip, pivot.source_grab(IR))
        after = side.mex_hsd.Archive(output)
        self.assertEqual(animation[:len(aj)], aj)
        self.assertEqual(after.public("ftDataKirby"), ar.public("ftDataKirby"))
        old_table, new_table = side.motion_table(ar), side.motion_table(after)
        self.assertEqual(after.data[new_table:new_table + 479 * 0x18],
                         ar.data[old_table:old_table + 479 * 0x18])
        row = new_table + 479 * 0x18
        self.assertEqual(after.u32(row + 8), len(clip))
        self.assertEqual(animation[after.u32(row + 4):after.u32(row + 4) + len(clip)], clip)
        self.assertEqual(side.flatten(after, 479)[-1][1], 0)
        self.assertEqual({f for f, op, _, _ in side.flatten(after, 479) if op == 11}, {10})
        self.assertEqual({f for f, op, _, _ in side.flatten(after, 479) if op == 16}, {12})
        spheres = [words for _, op, words, _ in side.flatten(after, 479) if op == 11]
        self.assertEqual([words[4] & 3 for words in spheres], [2, 2, 1, 1])
        self.assertEqual([(words[0] >> 23) & 7 for words in spheres], [0, 1, 2, 3])
        self.assertTrue(all((words[1] & 0xFFFF) > 0 for words in spheres))
        self.assertEqual([after.u32(new_table + i * 0x18 + 0xC)
                          for i in (242, 243, 322, 323)],
                         [ar.u32(old_table + i * 0x18 + 0xC)
                          for i in (242, 243, 322, 323)])
        x10_old = ar.u32(ar.public("ftDataKirby") + 0x10)
        x10_new = after.u32(after.public("ftDataKirby") + 0x10)
        self.assertEqual(after.data[x10_new:x10_new + 479 * 2],
                         ar.data[x10_old:x10_old + 479 * 2])
        self.assertEqual(after.data[x10_new + 479 * 2:x10_new + 480 * 2], b"\0\0")

    @unittest.skipUnless(PROFILE.is_file(), "local native Kirby profile required")
    def test_profile_routes_reverse_grab_to_distinct_state(self):
        original = json.loads(PROFILE.read_text(encoding="utf-8"))
        new = pivot.add_pivot_profile(original)
        fighter = new["fighters"][0]
        state = fighter["states"][-1]
        self.assertEqual((state["name"], state["subaction"], state["like"]),
                         ("PivotGrab", 479, "motion:214"))
        self.assertEqual(fighter["hooks"]["on_frame"][-1],
                         f"geno.kirby.pivot_grab:{len(fighter['states']) - 1}")


if __name__ == "__main__":
    unittest.main()
