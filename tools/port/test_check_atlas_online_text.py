"""python tools/port/test_check_atlas_online_text.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_atlas_online_text as C  # noqa: E402

TABLE = '''static const FrontendItem fe_items_online[] = {
    { FE_ACTION, FE_DO_CALL, "Host a Room", "Open a room and get a code.", NULL, NULL },
    { FE_CHOICE, 0, "A Label That Is Far Too Long", "Short.", fe_get, fe_set },
    { FE_CHOICE, 0, "Envoy", "Rooms you host: a best-of set where each player fights with an Envoy build and picks a reward between games.", fe_get, fe_set },
};
'''


class Lint(unittest.TestCase):
    def test_pairs(self):
        self.assertEqual([p[0] for p in C.pairs(TABLE)], ["Host a Room", "A Label That Is Far Too Long", "Envoy"])

    def test_findings(self):
        f = C.lint(C.pairs(TABLE))
        self.assertEqual(len(f), 2)
        self.assertIn("A Label That Is Far Too Long", f[0])     # the label is over 18 characters
        self.assertIn("Envoy", f[1])                              # the help wraps to more than 3 lines at 33 characters

    def test_wrap(self):
        self.assertEqual(C.wrap_lines("one two three"), 1)
        self.assertEqual(C.wrap_lines("x" * 40), 2)               # a word longer than a line is broken, never squashed

    def test_the_real_table_is_clean(self):
        path = os.environ.get("GW_MELEE_GM", "")
        if path and os.path.exists(path):
            self.assertEqual(C.lint(C.pairs(C.table_text(open(path, encoding="utf-8").read()))), [])


if __name__ == "__main__":
    unittest.main()
