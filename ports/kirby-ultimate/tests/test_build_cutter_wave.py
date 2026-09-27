"""Ultimate Final Cutter article0 motion and combat transfer."""

import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ports/kirby-ultimate/tools"))
sys.path.insert(0, str(ROOT / "tools/mex_port"))
import build_cutter_wave as wave  # noqa: E402
from mex_hsd import Archive  # noqa: E402

BASE = ROOT / "experiment/brawl-kirby/disc/PlKb.dat"


@unittest.skipUnless(BASE.is_file(), "local Melee Kirby baseline required")
class BuildCutterWaveTest(unittest.TestCase):
    def test_article0_transfer_preserves_other_articles_and_fighter_table(self):
        original = BASE.read_bytes()
        ir = json.loads(wave.IR.read_text(encoding="utf-8"))
        patched, changed = wave.patch_fighter(original, original, ir)
        self.assertTrue(changed)
        before, after = Archive(original), Archive(patched)
        root = before.public("ftDataKirby")
        self.assertEqual(after.public("ftDataKirby"), root)
        self.assertEqual(before.u32(root + 0xC), after.u32(root + 0xC))
        items = before.u32(root + 0x48)
        self.assertEqual(before.u32(items + 4), after.u32(items + 4))
        self.assertEqual(before.u32(items + 8), after.u32(items + 8))
        self.assertEqual(before.u32(items + 12), after.u32(items + 12))

        article = after.u32(items)
        attrs = after.u32(article + 4)
        self.assertAlmostEqual(struct.unpack_from(">f", after.data, attrs)[0], 4.8, places=6)
        self.assertAlmostEqual(struct.unpack_from(">f", after.data, attrs + 8)[0], 19)
        self.assertAlmostEqual(struct.unpack_from(">f", after.data, attrs + 12)[0], 0.28, places=6)
        self.assertEqual(before.u32(article + 0x10), after.u32(article + 0x10))

        words = wave.article_script(after)
        self.assertEqual([w >> 26 for w in words[::6]][:1], [11])
        self.assertEqual([words[i] & 0x1FFF for i in (0, 7, 13)], [5, 6, 6])
        self.assertEqual(words[6], (2 << 26) | 2)
        self.assertEqual(words[-1], 0)
        self.assertEqual([(words[i + 3] >> 23) & 511 for i in (0, 7, 13)], [70, 361, 361])
        self.assertEqual((words[13] >> 23) & 7, 1)  # second sphere, same hit group
        self.assertEqual(wave.patch_fighter(patched, original, ir), (patched, False))

    def test_source_shape_change_is_rejected(self):
        ir = json.loads(wave.IR.read_text(encoding="utf-8"))
        script = wave.source_script(ir)
        script["events"][1]["hitbox"]["damage"] = 7
        with self.assertRaisesRegex(ValueError, "Final Cutter wave source"):
            wave.patch_fighter(BASE.read_bytes(), BASE.read_bytes(), ir)

    def test_wave_hitboxes_do_not_inherit_stock_sixteen_frame_rehit(self):
        raw = BASE.read_bytes()
        ir = json.loads(wave.IR.read_text(encoding="utf-8"))
        patched, _ = wave.patch_fighter(raw, raw, ir)
        words = wave.article_script(Archive(patched))
        # Itemcmd word 5's top byte is the victim-list rehit timer. The
        # stock value 16 caused one wave to damage Fox twice, 16f apart.
        self.assertEqual([words[i + 5] >> 24 for i in (0, 7, 13)], [0, 0, 0])


if __name__ == "__main__":
    unittest.main()
