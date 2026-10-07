"""python -m unittest tools/port/test_retail_screens.py: the inventory of retail screens still retail matches the committed one.

    GW_MELEE=<game checkout> python -m unittest tools/port/test_retail_screens.py     (from tools/port)

When a screen moves to Atlas (or comes back) the expected file changes in the same commit: python tools/port/retail_screens.py --json > tools/port/retail_screens_expected.json
"""
import json
import os
import unittest

import retail_screens as r

GAME = os.environ.get("GW_MELEE") or os.path.join(os.path.dirname(__file__), "..", "..", "melee")
HERE = os.path.dirname(os.path.abspath(__file__))


class Inventory(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(HERE, "retail_screens_expected.json"), encoding="utf-8") as f:
            self.expected = json.load(f)

    def test_matches_the_committed_inventory(self):
        self.assertEqual(r.inventory(GAME), self.expected["entries"])
        self.assertEqual(r.SCENES, self.expected["scenes"])

    def test_fifteen_native_entry_points(self):
        self.assertEqual(len(self.expected["entries"]), 15)

    def test_the_owner_skips_stay_retail_and_the_rest_of_step_8_is_atlas(self):
        by_sel = {e["sel"]: e for e in self.expected["entries"]}
        for sel in ("SEL_DATA_SNAP", "SEL_DATA_ARCHIVES"):
            self.assertTrue(by_sel[sel]["stays"] and not by_sel[sel]["atlas"], sel)
        for sel in ("SEL_1P_EVENT", "SEL_VS_NAME", "SEL_DATA_SOUND", "SEL_DATA_SPECIAL", "SEL_RECORDS_VS", "SEL_RECORDS_BONUS", "SEL_RECORDS_MISC"):
            self.assertTrue(by_sel[sel]["atlas"], sel)
        self.assertFalse(by_sel["SEL_SETTINGS_LANG"]["atlas"] or by_sel["SEL_SETTINGS_LANG"]["step5"], "Language stays a retail hand-off: the owner kept the row")
        stays = {s["scene"] for s in self.expected["scenes"] if s.get("stays")}
        self.assertIn("GS_STAFFROLL", stays)


if __name__ == "__main__":
    unittest.main()
