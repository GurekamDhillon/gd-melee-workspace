"""Checks for the Ultimate ACMD to Kirby ftcmd normal-attack pass."""

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "ports/kirby-ultimate/tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_normals", TOOLS / "build_normals.py")
normal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(normal)


class NormalAttackTests(unittest.TestCase):
    def test_source_rows_match_ultimate_ir_and_melee_motion_names(self):
        sources = normal.source_rows(normal.DEFAULT_IR, normal.DEFAULT_MELEE)
        self.assertEqual(sources[52]["subaction"], "attack_dash")
        self.assertEqual(sources[52]["script"]["id"],
                         "script:kirby/attackdash/game_attackdash")
        self.assertEqual(sources[68]["subaction"], "attack_air_n")
        self.assertEqual(sources[68]["melee_name"], "AttackAirN")

    def test_dash_script_uses_ultimate_windows_and_preserves_host_nonhit_events(self):
        from build_side_b import flatten, mex_hsd

        base = mex_hsd.Archive(normal.DEFAULT_BASE.read_bytes())
        sources = normal.source_rows(normal.DEFAULT_IR, normal.DEFAULT_MELEE)
        script, reloc = normal.make_script(flatten(base, 52), sources[52]["script"],
                                           normal.templates(base, 52))
        self.assertTrue(script and script[-1] == 0)
        self.assertEqual(reloc, sorted(set(reloc)))
        self.assertIn(12, normal.compiled_hitbox_damages(script))
        self.assertEqual(normal.compiled_hitbox_frames(script), [9, 18, 27])
        host = flatten(base, 52)
        host_nonhit = [w[0] for _, op, words, _ in host if op not in normal.HITBOX_OPS for w in [words]]
        self.assertTrue(any(w in script for w in host_nonhit if w != 0))

    def test_patch_is_byte_stable_and_keeps_side_b_pointer(self):
        from build_side_b import mex_hsd, motion_table

        base_bytes = normal.DEFAULT_BASE.read_bytes()
        sources = normal.source_rows(normal.DEFAULT_IR, normal.DEFAULT_MELEE)
        selected = {52: sources[52]}
        once, changed = normal.patch_archive(base_bytes, base_bytes, selected)
        twice, changed_again = normal.patch_archive(once, base_bytes, selected)
        self.assertEqual(changed, [52])
        self.assertEqual(changed_again, [])
        self.assertEqual(once, twice)
        before, after = mex_hsd.Archive(base_bytes), mex_hsd.Archive(once)
        table = motion_table(before)
        self.assertEqual(before.u32(table + 322 * 0x18 + 0xC),
                         after.u32(table + 322 * 0x18 + 0xC))

    def test_variant_normals_use_ultimate_hitbox_frames(self):
        from build_side_b import linear_words, mex_hsd

        base_bytes = normal.DEFAULT_BASE.read_bytes()
        sources = normal.source_rows(normal.DEFAULT_IR, normal.DEFAULT_MELEE)
        selected = {row: sources[row] for row in (51, 53, 57, 60, 64)}
        once, changed = normal.patch_archive(base_bytes, base_bytes, selected)
        twice, changed_again = normal.patch_archive(once, base_bytes, selected)
        self.assertEqual(changed, sorted(selected))
        self.assertEqual(changed_again, [])
        self.assertEqual(once, twice)
        archive = mex_hsd.Archive(once)
        for row, source in selected.items():
            with self.subTest(row=row):
                compiled = normal.compiled_hitbox_frames(linear_words(archive, row))
                expected = sorted({int(e["frame"]) for e in source["script"]["events"]
                                   if e["op"] == "hitbox.create"})
                self.assertEqual(compiled, expected)

    def test_down_air_unrolls_five_ultimate_multihits_and_finisher(self):
        from build_side_b import linear_words, mex_hsd

        base_bytes = normal.DEFAULT_BASE.read_bytes()
        source = normal.source_rows(normal.DEFAULT_IR, normal.DEFAULT_MELEE)[72]
        patched, changed = normal.patch_archive(base_bytes, base_bytes, {72: source})
        self.assertEqual(changed, [72])
        words = linear_words(mex_hsd.Archive(patched), 72)
        self.assertEqual(normal.compiled_hitbox_frames(words), [18, 21, 24, 27, 30, 34])
        self.assertEqual(normal.compiled_hitbox_damages(words), [1, 1, 1, 1, 1, 2])
        rebuilt, changed_again = normal.patch_archive(patched, base_bytes, {72: source})
        self.assertEqual(changed_again, [])
        self.assertEqual(rebuilt, patched)

    def test_getup_ledge_and_pummel_use_source_hitbox_windows(self):
        from build_side_b import linear_words, mex_hsd

        base_bytes = normal.DEFAULT_BASE.read_bytes()
        sources = normal.source_rows(normal.DEFAULT_IR, normal.DEFAULT_MELEE)
        expected = {187: ("down_attack_u", [16, 20]),
                    195: ("down_attack_d", [16, 20]),
                    221: ("cliff_attack_quick", [20]),
                    222: ("cliff_attack_quick", [20]),
                    245: ("catch_attack", [1])}
        selected = {row: sources[row] for row in expected}
        patched, changed = normal.patch_archive(base_bytes, base_bytes, selected)
        self.assertEqual(changed, sorted(expected))
        archive = mex_hsd.Archive(patched)
        for row, (name, frames) in expected.items():
            with self.subTest(row=row):
                self.assertEqual(sources[row]["subaction"], name)
                self.assertEqual(normal.compiled_hitbox_frames(linear_words(archive, row)),
                                 frames)


if __name__ == "__main__":
    unittest.main()
