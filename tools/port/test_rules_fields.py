"""The Atlas Rules and More Rules rows read and write the fields the retail screens do: python tools/port/test_rules_fields.py

Retail: mnmainrule.c copies six values into GameRules (mode, time_limit, handicap, damage_ratio, stage_sel, stock_count); mnruleplus.c's mnRulePlus_SaveRules copies five
(stock_time_limit, friendly_fire, pause, score_display, unk_xc). The Atlas tables (gmfrontend_settings.inc: fe_items_rules, fe_items_morerules; their getters and setters
partly in gmfrontend.c, shared with MATCH SETUP) must write exactly those, and read them back from the same field. Read as text; nothing is run.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")
GM = os.path.join(GAME, "src", "melee", "gm")


def read(*p):
    with open(os.path.join(GAME, *p), encoding="utf-8", errors="replace") as f:
        return f.read().replace("\r\n", "\n")


def retail_rules_fields():
    src = read("src", "melee", "mn", "mnmainrule.c")
    block = src[src.index("rules = gmMainLib_GetGameRules();"):]
    block = block[:block.index("break;")] if "break;" in block[:600] else block[:600]
    return sorted(set(re.findall(r"rules->(\w+) = data->fields", block)))


def retail_more_fields():
    src = read("src", "melee", "mn", "mnruleplus.c")
    body = src[src.index("static inline void mnRulePlus_SaveRules(void)"):]
    body = body[:body.index("\n}\n")]
    return sorted(set(re.findall(r"gmMainLib_GetGameRules\(\)->(\w+) = ", body)))


def table_rows(name):
    text = read("src", "melee", "gm", "gmfrontend_settings.inc")
    body = text[text.index("static const FrontendItem %s[] = {" % name):]
    body = body[:body.index("\n};")]
    return [r for r in re.findall(r"\{ FE_\w+, [^\n]*", body)]


def func_text(name):
    for f in ("gmfrontend.c", "gmfrontend_settings.inc"):
        t = read("src", "melee", "gm", f)
        m = re.search(r"static (?:int|void) %s\([^)]*\)\s*\{" % re.escape(name), t)
        if m:
            depth, i = 1, m.end()                     # the matching brace: one-line and multi-line functions alike
            while depth and i < len(t):
                depth += (t[i] == "{") - (t[i] == "}")
                i += 1
            return t[m.start():i]
    raise AssertionError("no function " + name)


def fields_of(row_text, which):
    """The GameRules field a row's getter ('get') or setter ('set') touches."""
    parts = re.split(r",\s*", row_text.replace("\n", " "))
    names = [p.strip() for p in parts]
    # positional: kind, action, label (maybe with commas inside the string: take the function names after the label and help)
    idents = [n for n in names if re.fullmatch(r"(?:fe|frl)_\w+", n)]
    out = set()
    for n in idents:
        if (which == "get" and "_get_" in n) or (which == "set" and "_set_" in n):
            out |= set(re.findall(r"(?:GetGameRules\(\)|\br)->(\w+)", func_text(n)))
    return out


class RulesFields(unittest.TestCase):
    def test_retail_lists_are_what_the_plan_read(self):
        self.assertEqual(retail_rules_fields(), ["damage_ratio", "handicap", "mode", "stage_sel", "stock_count", "time_limit"])
        self.assertEqual(retail_more_fields(), ["friendly_fire", "pause", "score_display", "stock_time_limit", "unk_xc"])

    def test_rules_rows_write_the_retail_fields(self):
        written = set()
        for row in table_rows("fe_items_rules"):
            written |= fields_of(row, "set")
        self.assertEqual(sorted(written), retail_rules_fields())

    def test_rules_rows_read_the_retail_fields(self):
        read_ = set()
        for row in table_rows("fe_items_rules"):
            read_ |= fields_of(row, "get")
        self.assertEqual(sorted(read_), retail_rules_fields())

    def test_more_rules_rows_write_and_read_the_retail_fields(self):
        w, r = set(), set()
        for row in table_rows("fe_items_morerules"):
            w |= fields_of(row, "set")
            r |= fields_of(row, "get")
        self.assertEqual(sorted(w), retail_more_fields())
        self.assertEqual(sorted(r), retail_more_fields())

    def test_time_and_stocks_share_a_place(self):
        """Retail's second Rules row is the time limit in every mode but Stock and the stock count in Stock mode."""
        rows = table_rows("fe_items_rules")
        time_row = [r for r in rows if '"Time Limit"' in r][0]
        stock_row = [r for r in rows if '"Stocks"' in r][0]
        self.assertIn("frl_not_stock", time_row)
        self.assertIn("fe_is_stock", stock_row)
        self.assertIn("mode != 1", func_text("frl_not_stock"))
        self.assertIn("mode == 1", func_text("fe_is_stock"))

    def test_the_bounds_are_the_retail_table(self):
        src = read("src", "melee", "mn", "mnruleplus.c")
        stat = re.search(r"u8 stat\[6\]\[2\];.*?\{\s*\{ 0, 99 \}, \{ 0, 1 \}, \{ 0, 1 \}, \{ 0, 1 \}, \{ 0, 2 \}, \{ 0, 0 \} \}", src, re.S)
        self.assertIsNotNone(stat, "mnruleplus.c's bounds table changed: re-read the More Rules ranges")
        more = "\n".join(table_rows("fe_items_morerules"))
        self.assertRegex(more, r'"Stock Time Limit".*?, 0, 99, 1,')
        self.assertRegex(more, r'"Friendly Fire".*?, 0, 1, 1,')
        self.assertRegex(more, r'"Pause".*?, 0, 1, 1,')
        self.assertRegex(more, r'"Score Display".*?, 0, 1, 1,')
        self.assertRegex(more, r'"Sudden Death Penalty".*?, 0, 2, 1,')

    def test_item_and_stage_switch_storage_is_named_and_left_to_the_game(self):
        """The audit names the storage (item_mask, stage_mask); the lists stay the game's screen because their row names are the disc's text."""
        sw = read("src", "melee", "mn", "mnitemsw.c")
        self.assertIn("mn_8022E978(*order, data->items[i]);", sw)
        self.assertIn("item_mask", read("src", "melee", "mn", "mnmain.c"))
        self.assertIn("stage_mask", read("src", "melee", "gm", "gm_1601.c"))
        s = read("src", "melee", "gm", "gmfrontend_settings.inc")
        self.assertIn("frl_retail", s)
        self.assertIn("fm.native_sel = SEL_VS_RULES;", s)


class RulesPositions(unittest.TestCase):
    def test_atlas_rules_row_and_legacy_row(self):
        m = read("src", "melee", "gm", "gmfrontend_menus.inc")
        atlas = re.search(r"static const FeMenuItem fm_vs_atlas\[\] = \{(.*?)\n\};", m, re.S).group(1)
        legacy = re.search(r"static const FeMenuItem fm_vs\[\] = \{(.*?)\n\};", m, re.S).group(1)
        self.assertRegex(atlas, r'\{ "RULES",[^\n]*SEL_VS_RULES, FA_RULES \}')
        self.assertRegex(legacy, r'\{ "RULES",[^\n]*SEL_VS_RULES, FA_NATIVE \}')     # MELEE_ATLAS=0 keeps the game's own screen
        self.assertIn("case FA_RULES:", m)
        self.assertIn("fe_rules_from_menus();", m)

    def test_back_lands_on_versus_rules_and_the_native_return_reopens_the_screen(self):
        s = read("src", "melee", "gm", "gmfrontend_settings.inc")
        self.assertIn("fm_back_kind = MENU_KIND_VS;", s)
        self.assertIn("fm_back_sel = SEL_VS_RULES;", s)
        g = read("src", "melee", "gm", "gmfrontend.c")
        ret = g[g.index("bool gmFrontend_NativeReturn(int kind, int sel)"):]
        ret = ret[:ret.index("\n}\n")]
        self.assertIn("kind == MENU_KIND_VS && sel == SEL_VS_RULES", ret)
        self.assertIn("fe_rules_resume();", ret)
        self.assertLess(ret.index("fe_rules_resume();"), ret.index("fm_route_to_menus"))

    def test_match_setup_is_drawn_by_the_adapter(self):
        a = read("src", "melee", "gm", "gmfrontend_atlas_set.inc")
        self.assertIn("s == &fe_screen_vs_setup", a)
        self.assertIn("return FSS_K_MATCH;", a)


if __name__ == "__main__":
    unittest.main()
