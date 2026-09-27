"""Ultimate Final Cutter hitboxes on Kirby's existing up-B phases."""

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "ports/kirby-ultimate/tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_final_cutter", TOOLS / "build_final_cutter.py")
cutter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cutter)


class FinalCutterTests(unittest.TestCase):
    def test_source_up_b_payload_and_aerial_alias(self):
        from build_side_b import linear_words, mex_hsd, script_pointer
        import build_normals as normal

        source = cutter.source_scripts(cutter.DEFAULT_IR)
        self.assertEqual(len([e for e in source["ground"]["events"]
                              if e["op"] == "hitbox.create"]), 10)
        original = cutter.DEFAULT_BASE.read_bytes()
        patched, changed = cutter.patch_archive(original, original, source)
        self.assertEqual(changed, [325, 329])
        again, changed_again = cutter.patch_archive(patched, original, source)
        self.assertEqual(changed_again, [])
        self.assertEqual(again, patched)
        archive = mex_hsd.Archive(patched)
        self.assertEqual(normal.compiled_hitbox_frames(linear_words(archive, 325)),
                         [1, 3, 19, 28])
        self.assertEqual(normal.compiled_hitbox_damages(linear_words(archive, 325)),
                         [5] * 8 + [2, 2])
        self.assertEqual(cutter.aerial_call_target(archive), script_pointer(archive, 325))


if __name__ == "__main__":
    unittest.main()
