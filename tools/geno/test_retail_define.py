"""retail_define.py and the checker's relative-branch rule, on synthetic archives (no disc, no game data)."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ports" / "ir" / "tools"))
sys.path.insert(0, str(ROOT))
from tools.geno import check, define, script  # noqa: E402
import retail_define  # noqa: E402


class FakeArchive:
    """a flat word memory at addresses 0x100.. with u32(addr)"""
    def __init__(self, words):
        self.mem = {0x100 + 4 * i: w for i, w in enumerate(words)}

    def u32(self, addr):
        return self.mem[addr]


def W(op, rest=0):
    return (op << 26) | rest


class ReadOverlayTests(unittest.TestCase):
    def test_straight_script_is_copied_verbatim(self):
        words = [W(1, 5), W(2, 7), W(0)]
        ar = FakeArchive(words)
        self.assertEqual(retail_define.read_overlay(ar, 0x100), words)

    def test_goto_back_becomes_a_word_index(self):
        # wait 4; goto start
        ar = FakeArchive([W(1, 4), W(7), 0x100])
        self.assertEqual(retail_define.read_overlay(ar, 0x100), [W(1, 4), W(7), 0])

    def test_subroutine_body_is_appended_and_returns(self):
        # main: subroutine -> 0x200 ; end.  body at 0x200: wait 3 ; return
        ar = FakeArchive([W(5), 0x200, W(0)] + [0] * 61 + [W(1, 3), W(6)])
        self.assertEqual(ar.u32(0x200), W(1, 3))
        out = retail_define.read_overlay(ar, 0x100)
        self.assertEqual(out, [W(5), 3, W(0), W(1, 3), W(6)])

    def test_shared_callee_is_laid_out_once(self):
        ar = FakeArchive([W(5), 0x200, W(5), 0x200, W(0)] + [0] * 59 + [W(1, 3), W(6)])
        out = retail_define.read_overlay(ar, 0x100)
        self.assertEqual(out.count(W(6)), 1)
        self.assertEqual(out[1], out[3])


class CheckerTests(unittest.TestCase):
    def test_relative_branch_accepted_for_a_define_only(self):
        words = [W(1, 4), W(7), 0]
        errors = []
        check.validate_script(words, "$", errors, relative_branches=True)
        self.assertEqual(errors, [])
        errors = []
        check.validate_script(words, "$", errors)
        self.assertTrue(any("absolute" in e["message"] for e in errors))

    def test_relative_branch_must_land_on_a_command(self):
        errors = []
        check.validate_script([W(1, 4), W(7), 9], "$", errors, relative_branches=True)
        self.assertTrue(errors)

    def test_template_needs_none_and_geno_10(self):
        fighter = {"define": {"key": "k", "name": "n", "base": "mario", "common": "melee.common.v1", "resources": "retail:mario", "template": "captain"}}
        errors = define.validate_definition({"geno": 10, "fighters": [fighter]}, fighter, "$")
        self.assertTrue(any("template" in e[0] for e in errors))

    def test_captain_rows_widen_the_subaction_limit(self):
        f = {"define": {"key": "k", "name": "n", "base": "none", "common": "melee.common.v1", "resources": "mod:files", "template": "captain"},
             "fighter": {"plan": "p", "animation": "a", "costumes": []}, "subactions": [{"index": 317, "file": "x"}]}
        self.assertEqual([e for e in define.validate_definition({"geno": 10, "fighters": [f]}, f, "$") if "subaction" in e[1]], [])
        g = copy.deepcopy(f)
        g["subactions"][0]["index"] = 318
        self.assertTrue([e for e in define.validate_definition({"geno": 10, "fighters": [g]}, g, "$") if "subaction" in e[1]])


if __name__ == "__main__":
    unittest.main()
