"""World-space retarget pilot must emit usable Melee FigaTrees."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
ANIM = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "experiment/brawl-kirby/tools/anim"))
sys.path.insert(0, str(ANIM))
import figatree
import convert_world


class WorldRetargetTest(unittest.TestCase):
    def test_scripted_throw_root_keeps_stock_frame_timing(self):
        _, archives = convert_world.local.melee_anim.melee_aj()
        for row, name, source_frames in ((247, "ThrowF", 72),
                                         (248, "ThrowB", 62),
                                         (249, "ThrowHi", 83)):
            with self.subTest(row=row):
                stock = archives[f"PlyKirby5K_Share_ACTION_{name}_figatree"][2]
                frame = 33
                actual = convert_world._stock_root_translation(stock, frame, source_frames, row)
                tracks = {track["type"]: track for track in stock["joints"][1]}
                for axis, kind in enumerate(convert_world.local.TRACK_TYPE["translation"]):
                    expected = figatree.evaluate(tracks[kind]["keys"], frame) if kind in tracks else 0
                    self.assertAlmostEqual(actual[axis], expected, places=5)

    def test_wait_jump_run_pilot_has_world_pose_checks(self):
        for policy in ("rebased", "source-world", "source-world-scaled"):
            with self.subTest(policy=policy), tempfile.TemporaryDirectory() as temp:
                result = subprocess.run([
                    sys.executable, str(ANIM / "convert_world.py"),
                    "--root", str(ROOT), "--out", temp, "--bind-policy", policy,
                    "--clips", "a00wait1", "a03jumpf", "a02run",
                ], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                doc = json.loads((Path(temp) / "install-manifest.json").read_text())
                self.assertEqual(doc["mesh_bind_policy"], policy)
                self.assertEqual({entry["row"] for entry in doc["animations"]}, {2, 16, 13})
                for entry in doc["animations"]:
                    symbol, tree = figatree.parse_archive((Path(temp) / entry["file"]).read_bytes())
                    self.assertEqual(symbol, entry["symbol"])
                    self.assertEqual(len(tree["joints"]), 46)
                    self.assertLess(entry["bytes"], 0x10000)
                    self.assertLess(entry["max_mapped_world_translation_error"], 0.1)
                    if policy.startswith("source-world"):
                        self.assertLess(entry["max_mapped_world_axis_marker_error"], 0.25)


if __name__ == "__main__":
    unittest.main()
