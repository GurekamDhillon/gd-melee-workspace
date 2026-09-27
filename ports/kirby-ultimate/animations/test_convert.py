"""Static roundtrip checks for experimental Ultimate-to-HSD animation retargeting."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ANIM = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "experiment/brawl-kirby/tools/anim"))
import figatree


class ConverterTest(unittest.TestCase):
    def test_constant_track_covers_the_whole_clip(self):
        sys.path.insert(0, str(ANIM))
        import convert
        body, fv, fs, error = convert._track(np.full(19, 20.0), 0.003)
        keys = figatree.decode_keys(body, 0, len(body), fv, fs)
        self.assertEqual(len(keys), 2)
        self.assertEqual(keys[0][3], 18)
        self.assertEqual(figatree.evaluate(keys, 16), 20.0)
        self.assertLess(error, 0.003)

    def test_wait_clip_is_a_parseable_animated_46_joint_figatree(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(ANIM / "convert.py"), "--root", str(ROOT),
                 "--out", tmp, "--clips", "a00wait1"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((Path(tmp) / "install-manifest.json").read_text())
            self.assertEqual([entry["row"] for entry in manifest["animations"]], [2])
            raw = (Path(tmp) / manifest["animations"][0]["file"]).read_bytes()
            symbol, tree = figatree.parse_archive(raw)
        self.assertEqual(symbol, "PlyKirby5K_Share_ACTION_Wait1_figatree")
        self.assertEqual(len(tree["joints"]), 46)
        self.assertGreater(tree["frames"], 50)
        self.assertGreater(sum(len(joint) for joint in tree["joints"]), 10)

    def test_locomotion_root_tracks_match_melee_motion_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(ANIM / "convert.py"), "--root", str(ROOT),
                 "--out", tmp, "--clips", "a01walkslow", "a02run", "a02dash"],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((Path(tmp) / "install-manifest.json").read_text())
            by_row = {entry["row"]: entry for entry in manifest["animations"]}
            def root_track(row):
                raw = (Path(tmp) / by_row[row]["file"]).read_bytes()
                return {track["type"]: track for track in figatree.parse_archive(raw)[1]["joints"][1]}
            for row in (7, 13):
                self.assertTrue(all(axis not in root_track(row) for axis in (5, 6, 7)))
            self.assertGreater(figatree.evaluate(root_track(12)[7]["keys"], 24), 15)

    def test_animation_joints_follow_the_mesh_retarget_map(self):
        sys.path.insert(0, str(ANIM))
        import convert
        self.assertEqual(convert.BONE_MAP.get(24), "ShoulderL")
        self.assertEqual(convert.BONE_MAP.get(29), "ShoulderR")
        self.assertEqual(convert.BONE_MAP.get(26), "HandL")
        self.assertEqual(convert.BONE_MAP.get(31), "HandR")

    def test_jump_hand_euler_tracks_do_not_accumulate_extra_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(ANIM / "convert.py"), "--root", str(ROOT),
                 "--out", tmp, "--clips", "a03jumpf"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            raw = (Path(tmp) / "clips/JumpF.dat").read_bytes()
            tree = figatree.parse_archive(raw)[1]
        for track in tree["joints"][26]:
            if track["type"] in (1, 2, 3):
                values = [figatree.evaluate(track["keys"], frame) for frame in range(53)]
                self.assertLess(max(values) - min(values), 7.5)

    def test_run_pose_is_continuous_at_its_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(ANIM / "convert.py"), "--root", str(ROOT),
                 "--out", tmp, "--clips", "a02run"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            tree = figatree.parse_archive((Path(tmp) / "clips/Run.dat").read_bytes())[1]
        for joint in (7, 24, 26):
            for track in tree["joints"][joint]:
                first = figatree.evaluate(track["keys"], 0)
                last = figatree.evaluate(track["keys"], 40)
                distance = abs((last - first + 3.141592653589793) % (2 * 3.141592653589793)
                               - 3.141592653589793) if track["type"] in (1, 2, 3) else abs(last - first)
                self.assertLess(distance, 0.02, (joint, track["type"], distance))


if __name__ == "__main__":
    unittest.main()
