"""Checks the selected Ultimate source clips against the local asset inventory."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
BUILDER = Path(__file__).with_name("build_manifest.py")


class ManifestTest(unittest.TestCase):
    def test_selected_clips_are_located_and_hashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "manifest.json"
            result = subprocess.run(
                [sys.executable, str(BUILDER), "--root", str(ROOT), "--out", str(target)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(target.read_text(encoding="utf-8"))
        clips = manifest["clips"]
        rows = {row for clip in clips for row in clip["melee_motion_rows"]}
        self.assertTrue({2, 7, 8, 9, 12, 13, 16, 30, 31, 295, 299, 322, 323} <= rows)
        self.assertTrue({46, 47, 52, 55, 58, 59, 62, 66, 67, 68, 69, 70, 71} <= rows)
        self.assertTrue(set(range(324, 332)) <= rows)
        self.assertTrue({51, 53, 57, 60, 64, 72, 187, 195, 221, 222,
                         242, 243, 245, 247, 248, 249, 250} <= rows)
        air_end = next(clip for clip in clips if 331 in clip["melee_motion_rows"])
        self.assertIn("SpecialAirHi4", air_end["melee_motion_names"])
        self.assertNotIn(18, rows)  # Melee has no archive symbol for this placeholder row.
        self.assertTrue(all(len(clip["sha256"]) == 64 for clip in clips))
        self.assertTrue(all(clip["ir_clip_id"].startswith("clip:motion.body.c00.") for clip in clips))
        self.assertTrue(all(clip["final_frame_index"] > 0 for clip in clips))
        self.assertTrue(any(clip["ultimate_file"].endswith("d01specials.nuanmb") for clip in clips))
        self.assertTrue(all(clip.get("ultimate_motion_entries") for clip in clips))
        hammer = next(clip for clip in clips if clip["ultimate_file"].endswith("d01specials.nuanmb"))
        self.assertTrue({"special_s", "special_s_s"} <= {
            entry["status"] for entry in hammer["ultimate_motion_entries"]})
        air_hammer = next((clip for clip in clips if clip["ultimate_file"].endswith("d01specialairs.nuanmb")), None)
        self.assertIsNotNone(air_hammer)
        self.assertEqual(air_hammer["melee_motion_rows"], [323])
        self.assertEqual(hammer["melee_motion_rows"], [322])


if __name__ == "__main__":
    unittest.main()
