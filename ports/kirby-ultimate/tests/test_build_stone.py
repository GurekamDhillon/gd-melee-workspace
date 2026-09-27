"""Stone air hitbox transfer and exact-NRO ground timing evidence."""

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ports/kirby-ultimate/tools"))
sys.path.insert(0, str(ROOT / "tools/mex_port"))
import build_side_b as side  # noqa: E402
import build_stone  # noqa: E402
from mex_hsd import Archive  # noqa: E402

BASE = ROOT / "experiment/brawl-kirby/disc/PlKb.dat"


@unittest.skipUnless(BASE.is_file(), "local Melee Kirby baseline is required")
class BuildStoneTest(unittest.TestCase):
    def test_air_combat_transfer_preserves_status_script_and_ground(self):
        original = BASE.read_bytes()
        ir = json.loads(build_stone.IR.read_text(encoding="utf-8"))
        patched, changed = build_stone.patch_fighter(original, original, ir)
        self.assertEqual(changed, [336])
        before, after = Archive(original), Archive(patched)
        self.assertEqual(side.linear_words(before, 332), side.linear_words(after, 332))
        self.assertEqual(side.linear_words(before, 336)[-1], 0)
        hit = next(words for _, op, words, _ in side.flatten(after, 336) if op == 11)
        self.assertEqual(hit[0] & 1023, 18)
        self.assertEqual((hit[3] >> 23) & 511, 70)
        self.assertEqual((hit[3] >> 14) & 511, 76)
        self.assertEqual((hit[4] >> 23) & 511, 69)
        self.assertEqual(build_stone.patch_fighter(patched, original, ir), (patched, []))

    def test_nonmonotonic_ground_clear_is_rejected(self):
        ir = json.loads(build_stone.IR.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "ground Stone clear"):
            build_stone.ground_timeline(ir)

    @unittest.skipUnless(build_stone.NRO.is_file(), "local Ultimate 13.0.2 Kirby NRO required")
    def test_exact_nro_resolves_zero_duration_ground_hitboxes(self):
        ir = json.loads(build_stone.IR.read_text(encoding="utf-8"))
        ground = build_stone.ground_resolution(ir, build_stone.NRO, BASE.read_bytes())
        self.assertEqual(ground["source_absolute_frames"], [14, 14, 2])
        self.assertEqual(ground["effective_clear_frame"], 14)
        self.assertEqual(ground["persistent_hitbox_frames"], 0)
        self.assertEqual(ground["nro_sha256"], build_stone.NRO_SHA256)


if __name__ == "__main__":
    unittest.main()
