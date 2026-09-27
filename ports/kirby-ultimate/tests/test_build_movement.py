"""Behavior tests for the Ultimate Kirby movement-only Geno pack."""

import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BUILDER = ROOT / "ports/kirby-ultimate/tools/build_movement.py"
BASELINE = ROOT / "experiment/brawl-kirby/analysis/melee_kirby.json"

PARAMS = {
    "walk_accel_mul": 0.168, "walk_accel_add": 0.105,
    "walk_speed_max": 0.977, "walk_slow_speed_mul": 0.2,
    "walk_middle_ratio": 0.5, "walk_fast_ratio": 0.75,
    "ground_brake": 0.116, "dash_speed": 1.9,
    "run_accel_mul": 0.10494, "run_accel_add": 0.044,
    "run_speed_max": 1.727, "jump_squat_frame": 3,
    "jump_speed_x": 0.85, "jump_speed_x_mul": 0.8,
    "jump_speed_x_max": 1.3, "jump_aerial_speed_x_mul": 0.0,
    "jump_initial_y": 13.9535, "jump_y": 25.37,
    "mini_jump_y": 12.24, "jump_aerial_y": 22.0,
    "air_accel_x_mul": 0.065, "air_accel_x_add": 0.03,
    "air_speed_x_stable": 0.84, "air_brake_x": 0.015,
    "air_accel_y": 0.064, "air_speed_y_stable": 1.23,
    "dive_speed_y": 1.968, "jump_count_max": 6,
    "squat_walk_type": False,
}


def fixture():
    return {
        "document_id": "kirby.ultimate",
        "subject": {"character": "Kirby", "engine": "ssbu.switch",
                    "distribution": {"version": "13.0.2"}},
        "behavior": {"attributes": {"common": [
            {"key": "ssbu." + name, "engine_name": name, "value": value,
             "provenance": {"confidence": "inferred", "evidence": ["ev:kirby_fighter_param"]}}
            for name, value in PARAMS.items()
        ]}},
    }


def build(doc, parent):
    ir_path = parent / "input.ir.json"
    ir_path.write_text(json.dumps(doc), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(BUILDER), "--ir", str(ir_path),
         "--baseline", str(BASELINE), "--out-parent", str(parent / "mods")],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result, parent / "mods/ultimate-kirby-movement"


class MovementBuilderTests(unittest.TestCase):
    def test_builds_mountable_pack_with_converted_jump_heights(self):
        with tempfile.TemporaryDirectory() as temp:
            result, pack = build(fixture(), Path(temp))
            self.assertEqual(result.returncode, 0, result.stderr)
            mod = json.loads((pack / "mod.json").read_text(encoding="utf-8"))
            geno = json.loads((pack / "geno.json").read_text(encoding="utf-8"))
            manifest = json.loads((pack / "source-manifest.json").read_text(encoding="utf-8"))
            self.assertTrue((pack / "files").is_dir())
            self.assertEqual(mod["id"], pack.name)
            self.assertEqual(geno["geno"], 3)
            fighter = geno["fighters"][0]
            self.assertEqual(fighter["attach"], "kirby")
            attrs = fighter["attributes"]
            self.assertEqual(attrs["walk_accel_base"], 0.105)
            self.assertEqual(attrs["walk_max_vel"], 0.977)
            self.assertAlmostEqual(attrs["slow_walk_max"], 0.977 * 0.2)
            self.assertEqual(attrs["dash_initial_velocity"], 1.9)
            self.assertEqual(attrs["dash_accel_mul"], 0.10494)
            self.assertEqual(attrs["jump_startup_time"], 3)
            self.assertEqual(attrs["gravity"], 0.064)
            self.assertEqual(attrs["terminal_velocity"], 1.23)
            self.assertEqual(attrs["jump_v_initial_velocity"], round(math.sqrt(2 * 0.064 * 25.37), 6))
            self.assertEqual(attrs["hop_v_initial_velocity"], round(math.sqrt(2 * 0.064 * 12.24), 6))
            self.assertLess(attrs["jump_v_initial_velocity"], 3)
            self.assertEqual(fighter["jumps"]["max"], 6)
            self.assertEqual(len(fighter["jumps"]["air_vy"]), 5)
            self.assertEqual(fighter["jumps"]["air_vy"][0], round(math.sqrt(2 * 0.064 * 22), 6))
            self.assertLess(fighter["jumps"]["air_vy"][4], fighter["jumps"]["air_vy"][0])
            self.assertEqual(manifest["source_document_id"], "kirby.ultimate")
            self.assertEqual(manifest["mappings"]["jump_v_initial_velocity"]["source_fields"],
                             ["jump_y", "air_accel_y"])
            self.assertIn("squat_walk_type", manifest["omitted_fields"])

    def test_changes_in_ir_change_generated_movement(self):
        original = fixture()
        changed = copy.deepcopy(original)
        for field in changed["behavior"]["attributes"]["common"]:
            if field["engine_name"] == "walk_speed_max":
                field["value"] = 1.111
            if field["engine_name"] == "jump_aerial_y":
                field["value"] = 30.0
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            r1, p1 = build(original, Path(first))
            r2, p2 = build(changed, Path(second))
            self.assertEqual((r1.returncode, r2.returncode), (0, 0), r1.stderr + r2.stderr)
            a = json.loads((p1 / "geno.json").read_text(encoding="utf-8"))["fighters"][0]
            b = json.loads((p2 / "geno.json").read_text(encoding="utf-8"))["fighters"][0]
            self.assertNotEqual(a["attributes"]["walk_max_vel"], b["attributes"]["walk_max_vel"])
            self.assertNotEqual(a["jumps"]["air_vy"], b["jumps"]["air_vy"])

    def test_missing_required_movement_field_fails_before_packaging(self):
        doc = fixture()
        doc["behavior"]["attributes"]["common"] = [
            field for field in doc["behavior"]["attributes"]["common"]
            if field["engine_name"] != "jump_aerial_y"
        ]
        with tempfile.TemporaryDirectory() as temp:
            result, pack = build(doc, Path(temp))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("jump_aerial_y", result.stderr)
            self.assertFalse(pack.exists())


if __name__ == "__main__":
    unittest.main()
