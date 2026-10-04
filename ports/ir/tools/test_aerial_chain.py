#!/usr/bin/env python3
import json
import unittest
from pathlib import Path

import aerial_chain as AC

ACMD = Path(__file__).resolve().parents[3] / "_build/tmp/codex-nodrop-run/trail.acmd.json"


@unittest.skipUnless(ACMD.exists(), "local Sora ACMD export unavailable")
class StageTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r["script"]: r for r in json.loads(ACMD.read_text(encoding="utf-8"))
                    if r.get("agent") == "trail" and r.get("kind") == "game"}

    def test_nair_stages(self):
        t = AC.stage_table(self.rows, "nair")
        self.assertEqual([s["clip"] for s in t], ["c05attackairn", "c05attackairn2", "c05attackairn3"])
        self.assertEqual([s["cancel"] for s in t], [42, 37, 42])
        self.assertEqual((t[0]["window_open"], t[0]["transition"]), (16, 23))
        self.assertEqual(t[1]["rates"], [(0.0, 0.8), (14.0, 1)])
        self.assertEqual((t[1]["first_hit"], t[2]["first_hit"]), (6.0, 9.0))

    def test_fair_stages_reuse_the_nair_2_and_3_clips(self):
        t = AC.stage_table(self.rows, "fair")
        self.assertEqual([s["clip"] for s in t], ["c05attackairf", "c05attackairn2", "c05attackairn3"])
        self.assertEqual((t[0]["window_open"], t[0]["transition"]), (14, 21))
        self.assertEqual(t[0]["rates"], [(3.0, 2), (5.0, 1)])


if __name__ == "__main__":
    unittest.main()
