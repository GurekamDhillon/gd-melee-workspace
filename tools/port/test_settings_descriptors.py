"""The settings tables and what is derived from them stay in step: python tools/port/test_settings_descriptors.py

A page is a FrontendItem table in the game. Two things are derived from the tables and committed beside them: the inventory (tools/port/settings_inventory_expected.json)
and the descriptor copy the native page test runs the real walker over (pc/tests/atlas_settings_tables.inc). Change a table and both must be regenerated, so a page
cannot gain or lose a row without the page tests being re-read.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import settings_descriptors  # noqa: E402
import settings_inventory  # noqa: E402


class Derived(unittest.TestCase):
    def test_inventory_matches(self):
        self.assertEqual(settings_inventory.main(["--check"]), 0)

    def test_descriptors_match(self):
        self.assertEqual(settings_descriptors.main(["--check"]), 0)

    def test_the_parser_reads_every_row(self):
        inv = settings_inventory.scan()
        text = settings_descriptors.build()
        for name, info in inv.items():
            self.assertIn('{ "%s", tbl_%s, %d, nopts_%s }' % (name, name, info["rows"], name), text, name)

    def test_split_top_keeps_strings_whole(self):
        f = settings_descriptors.split_top('FE_ACTION, FE_DO_CALL, "a, b", "c" "d", NULL, f(1, 2)')
        self.assertEqual(f, ["FE_ACTION", "FE_DO_CALL", '"a, b"', '"c" "d"', "NULL", "f(1, 2)"])
        self.assertEqual(settings_descriptors.literal('"c" "d"'), '"c" "d"')
        self.assertEqual(settings_descriptors.literal("NULL"), None)


if __name__ == "__main__":
    unittest.main()
