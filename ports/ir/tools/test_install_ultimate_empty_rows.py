#!/usr/bin/env python3
"""Offline row-selection checks using the extracted Sora and Marth inputs."""
import json
import unittest
from pathlib import Path

import install_ultimate as IU


ROOT = Path(__file__).resolve().parents[3]
MOVESET = ROOT / "_build/tmp/ir/trail.moveset.json"
HOST_IR = ROOT / "_build/tmp/ir/marth.melee.ir.json"
MOTION = ROOT / "experiment/tooling/ultimate/workspace/extracted/fighter/trail/motion/body/c00"


class EmptyHostRowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.moveset = {int(k): v for k, v in json.loads(MOVESET.read_text(encoding="utf-8"))["rows"].items()}
        cls.subactions = json.loads(HOST_IR.read_text(encoding="utf-8"))["behavior"]["subactions"]
        cls.host_names = {s["index"]["value"]: s["name"] for s in cls.subactions}
        cls.initial_rows = {s["index"]["value"]: s["name"] for s in cls.subactions if not s["empty"]}
        cls.clips = {p.stem for p in MOTION.glob("*.nuanmb")}

    def test_sora_jab_adds_only_attack13(self):
        rows = dict(self.initial_rows)
        jab_moveset = {r: self.moveset[r] for r in (46, 47, 48)}
        admitted = IU.admit_empty_motion_rows(rows, set(), self.host_names, jab_moveset, self.clips)
        self.assertEqual(set(rows) - set(self.initial_rows), {48})
        self.assertEqual(rows[48], "Attack13")
        self.assertEqual(admitted, {48: "c00attack13"})

    def test_full_moveset_only_adds_explicitly_scripted_empty_rows(self):
        rows = dict(self.initial_rows)
        admitted = IU.admit_empty_motion_rows(rows, set(), self.host_names, self.moveset, self.clips)
        expected = {48, 53, 54, 56, 57, 60, 61, 63, 64}
        self.assertEqual(set(rows) - set(self.initial_rows), expected)
        self.assertEqual(set(admitted), expected)

    def test_clip_only_and_foreign_rows_are_not_admitted(self):
        rows = dict(self.initial_rows)
        clip_only = {48: {"clip": "c00attack13", "script": None, "words": None}}
        self.assertEqual(IU.admit_empty_motion_rows(rows, set(), self.host_names, clip_only, self.clips), {})
        self.assertNotIn(48, rows)
        self.assertEqual(IU.admit_empty_motion_rows(rows, {48}, self.host_names,
                                                      {48: self.moveset[48]}, self.clips), {})

    def test_missing_explicit_clip_fails_clearly(self):
        rows = dict(self.initial_rows)
        with self.assertRaisesRegex(ValueError, "moveset row 48: no clip c00attack13"):
            IU.admit_empty_motion_rows(rows, set(), self.host_names, {48: self.moveset[48]},
                                       self.clips - {"c00attack13"})


if __name__ == "__main__":
    unittest.main()
