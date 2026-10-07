"""The game-side adapter (src/melee/gm/gmfrontend_atlas_select.inc) cannot include a host header, so it repeats the host's numbers: input bits, result
bits, cell and card flags, event kinds, the Ui_CssGet / Ui_SssGet selectors. This test reads both sides and fails when one moved.

    python tools/port/test_select_enums.py        (GW_MELEE selects the game checkout)
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")
PLAT = os.path.join(GAME, "pc", "platform")
ADAPTER = os.path.join(GAME, "src", "melee", "gm", "gmfrontend_atlas_select.inc")


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def enums(path):
    """{name: value} of every enumerator in every enum of a C file (sequential numbering, hex, previous names)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = strip_comments(f.read())
    out = {}
    for body in re.findall(r"enum\s*\w*\s*\{(.*?)\}", text, re.S):
        nxt = 0
        for item in body.split(","):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                name, expr = [x.strip() for x in item.split("=", 1)]
                nxt = int(eval(expr, {"__builtins__": {}}, dict(out)))
            else:
                name = item
            out[name] = nxt
            nxt += 1
    return out


class SelectEnums(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = enums(ADAPTER)
        cls.host = {}
        for f in ("gw_ui_css.h", "gw_ui_sss.h", "gw_ui_parts.h", "gw_ui_screen.h", "gw_script_ui_sel.inc"):
            cls.host.update(enums(os.path.join(PLAT, f)))

    def check(self, game_prefix, host_prefix, strip=""):
        pairs = [(g, h) for g in self.game for h in [host_prefix + g[len(game_prefix):]] if g.startswith(game_prefix)]
        self.assertTrue(pairs, "no %s* names in the adapter" % game_prefix)
        for g, h in pairs:
            self.assertIn(h, self.host, "%s has no host twin %s" % (g, h))
            self.assertEqual(self.game[g], self.host[h], "%s (%d) != %s (%d)" % (g, self.game[g], h, self.host[h]))

    def test_input_bits(self):
        self.check("FA_CI_", "AT_CI_")

    def test_result_bits(self):
        self.check("FA_CE_", "AT_CE_")

    def test_cell_and_card_flags(self):
        self.check("FA_CELL_", "AT_CELL_")
        self.check("FA_CARD_", "AT_CARD_")

    def test_note_kind(self):
        self.assertEqual(self.game["FA_NOTE_INFO"], self.host["AT_NOTE_INFO"])

    def test_select_kinds_and_events(self):
        self.check("FA_SEL_", "GS_SEL_")
        self.check("FA_SELEV_", "GS_SELEV_")

    def test_css_selectors(self):
        self.check("FA_CG_", "GS_CSSG_")

    def test_sss_selectors(self):
        self.check("FA_SG_", "GS_SSSG_")

    def test_every_shim_the_adapter_declares_exists_on_the_host(self):
        with open(ADAPTER, encoding="utf-8", errors="replace") as f:
            text = strip_comments(f.read())
        with open(os.path.join(PLAT, "gw_script_ui_sel.inc"), encoding="utf-8", errors="replace") as f:
            host = strip_comments(f.read())
        for m in re.finditer(r"extern\s+[\w\s\*]+?\b(Ui_(?:Sel|Css|Sss|Art)\w*)\s*\(", text):
            name = m.group(1)
            self.assertRegex(host, r"\bgw_%s\s*\(" % name, "the adapter declares %s but the host defines no gw_%s" % (name, name))


if __name__ == "__main__":
    unittest.main()
