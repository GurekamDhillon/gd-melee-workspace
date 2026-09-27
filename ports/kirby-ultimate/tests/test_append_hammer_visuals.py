"""The Hammer motion extension preserves all existing playable Kirby rows."""

from pathlib import Path
import copy
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ports/kirby-ultimate/tools"))
import append_hammer_visuals as hammer  # noqa: E402

SOURCE = ROOT / "_build/tmp/ultimate-kirby-additive-stone-sixth-277-core/source"
MANIFEST = ROOT / "_build/tmp/ultimate-kirby-hammer-clips/install-manifest.json"


@unittest.skipUnless(SOURCE.is_dir() and MANIFEST.is_file(),
                     "local generated Ultimate clips and fighter required")
class HammerVisualsTest(unittest.TestCase):
    def test_preserves_old_rows_and_appends_verified_clips(self):
        raw = (SOURCE / "files/PlKb.dat").read_bytes()
        aj = (SOURCE / "files/PlKbAJ.dat").read_bytes()
        entries = hammer.clips(MANIFEST)
        fighter, animation = hammer.append(raw, aj, entries)
        before, after = hammer.side.mex_hsd.Archive(raw), hammer.side.mex_hsd.Archive(fighter)
        old_table, new_table = hammer.side.motion_table(before), hammer.side.motion_table(after)
        self.assertEqual(before.data[old_table:old_table + 479 * 0x18],
                         after.data[new_table:new_table + 479 * 0x18])
        self.assertTrue(animation.startswith(aj))
        for row, symbol, clip, _ in entries:
            field = new_table + row * 0x18
            self.assertIn(field, after.reloc_set)
            self.assertIn(field + 0xC, after.reloc_set)
            at, size = after.u32(field + 4), after.u32(field + 8)
            self.assertEqual(animation[at:at + size], clip)
            sym = after.u32(field)
            self.assertEqual(bytes(after.data[sym:]).split(b"\0", 1)[0], symbol.encode())
            template = new_table + hammer.SCRIPT_TEMPLATE[row] * 0x18
            self.assertEqual(after.u32(field + 0xC), after.u32(template + 0xC))

    def test_rejects_tampered_manifest(self):
        import json
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
            doc["animations"][0]["row"] = 478
            path.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "479..488"):
                hammer.clips(path)

    def test_profile_uses_dedicated_charge_walk_and_max_rows(self):
        import json
        profile = json.loads((SOURCE / "geno.json").read_text(encoding="utf-8"))
        result = hammer.update_profile(copy.deepcopy(profile))
        states = result["fighters"][0]["states"]
        self.assertEqual([states[i]["subaction"] for i in (0, 2, 3, 5, 6)],
                         [479, 481, 482, 483, 480])
        self.assertEqual(states[6]["name"], "HammerWalk")


if __name__ == "__main__":
    unittest.main()
