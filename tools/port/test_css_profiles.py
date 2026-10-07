"""The mode profile table must cover exactly the retail CSSMatchType enum: python tools/port/test_css_profiles.py"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")


class Profiles(unittest.TestCase):
    def enum_values(self):
        types = open(os.path.join(GAME, "src", "melee", "mn", "types.h"), encoding="utf-8", errors="replace").read()
        body = re.search(r"typedef enum CSSMatchType \{(.*?)\} CSSMatchType;", types, re.S).group(1)
        return sorted(int(v, 0) for v in re.findall(r"=\s*(0x[0-9A-Fa-f]+|\d+)", body))

    def table_rows(self):
        table = open(os.path.join(GAME, "pc", "platform", "gw_ui_css_profile.c"), encoding="utf-8").read()
        return sorted(int(v, 0) for v in re.findall(r"\{\s*(0x[0-9A-Fa-f]+|\d+)\s*,\s*\d+\s*,", table))

    def test_enum_equals_table(self):
        rows = [v for v in self.table_rows() if v != 0x40]          # 0x40 is the lobby, not a retail value
        self.assertEqual(self.enum_values(), rows)

    def test_lobby_is_the_only_extra(self):
        extra = [v for v in self.table_rows() if v not in self.enum_values()]
        self.assertEqual(extra, [0x40])

    def test_every_state_in_the_audit_has_a_profile(self):
        # the audit (css_states.py) records the match type each GS_CSS file stores; every one must have a profile
        sys.path.insert(0, HERE)
        import css_states
        known = set(self.table_rows())
        for row in css_states.scan():
            for mt in row["match_types"]:
                self.assertIn(mt, known, "%s stores match_type 0x%X which has no profile" % (row["file"], mt))


if __name__ == "__main__":
    unittest.main()
