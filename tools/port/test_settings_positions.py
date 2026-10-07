"""Settings entry and return positions: python tools/port/test_settings_positions.py

Reads the source (no game, no disc). The tabbed Atlas settings are entered from five places and must go back to the right one:

  1. main menu SETTINGS   -> the tabs at VIDEO; B returns to the main menu's SETTINGS item
  2. main menu MODS       -> the tabs at MODS; B returns to the main menu's MODS item
  3. first boot           -> the tabs at CONTROLS once; B returns to SETTINGS
  4. the Language row     -> the game's own screen (the same native request the legacy list makes); its back-out reopens the tabs on GAME at Language
  5. B from a tab         -> the main menu on the item the entry came from

MELEE_ATLAS=0 keeps the legacy tree whole: the Settings list still has its own RUMBLE, SCREEN DISPLAY, LANGUAGE and ERASE DATA rows (the plan deleted them with the list;
that would leave the legacy menus without those options, so they stay and only the Atlas main menu stops going through the list).
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")


def read(n):
    with open(os.path.join(GAME, "src", "melee", "gm", n), encoding="utf-8", errors="replace") as f:
        return f.read().replace("\r\n", "\n")


def table(text, name):
    m = re.search(r"static const FeMenuItem %s\[\] = \{(.*?)\n\};" % re.escape(name), text, re.S)
    return m.group(1) if m else ""


def func(text, header):
    start = text.index(header + chr(10) + "{")  # the definition, not a forward declaration
    return text[start:text.index(chr(10) + "}" + chr(10), start)]


class Positions(unittest.TestCase):
    def test_the_atlas_main_menu_opens_the_tabs_the_legacy_one_keeps_its_list(self):
        m = read("gmfrontend_menus.inc")
        atlas = table(m, "fm_main_atlas")
        self.assertRegex(atlas, r'\{ "SETTINGS",[^\n]*SEL_MAIN_SETTINGS, FA_PAGE, 0 \}')          # page 0 is VIDEO: the first tab
        self.assertRegex(atlas, r'\{ "MODS",[^\n]*SEL_MAIN_MODS, FA_PAGE, 4 \}')                  # FSP_MODS
        legacy = table(m, "fm_main")
        self.assertRegex(legacy, re.compile(r'\{ "SETTINGS",.*?SEL_MAIN_SETTINGS, FA_SUB, MENU_KIND_SETTINGS \}', re.S))

    def test_the_legacy_list_keeps_the_retail_rows(self):
        m = table(read("gmfrontend_menus.inc"), "fm_settings")
        for name in ("RUMBLE", "SCREEN DISPLAY", "LANGUAGE", "ERASE DATA"):
            self.assertIn('{ "%s",' % name, m, "MELEE_ATLAS=0 must keep %s" % name)

    def test_language_return_row_survives(self):
        self.assertIn("{ GM_MENU, MENU_KIND_SETTINGS, SEL_SETTINGS_LANG }", read("gmfrontend_menus.inc"))

    def test_first_boot_opens_controls(self):
        m = read("gmfrontend_menus.inc")
        self.assertRegex(m, r"first boot -> SETTINGS > CONTROLS")
        self.assertRegex(m, r"fm\.pend_a = 2;")                                                    # FSP_CONTROLS
        s = read("gmfrontend_settings.inc")
        self.assertRegex(s, r"enum \{ FSP_VIDEO, FSP_AUDIO, FSP_CONTROLS,")                        # page 2 is CONTROLS

    def test_every_page_enters_through_one_function(self):
        g = read("gmfrontend.c")
        self.assertEqual(len(re.findall(r"static void fe_settings_from_menus\(int page\)\s*\{", g)), 1)
        self.assertIn("fe_settings_from_menus(fm.pend_a);", read("gmfrontend_menus.inc"))

    def test_back_goes_to_the_main_menu_item_the_entry_came_from(self):
        body = func(read("gmfrontend.c"), "static void fe_settings_from_menus(int page)")
        self.assertIn("if (Ui_Ready()) {", body)
        self.assertIn("fm_back_kind = MENU_KIND_MAIN;", body)
        self.assertIn("fm_back_sel = SEL_MAIN_SETTINGS;", body)
        self.assertIn("fm_back_sel = SEL_MAIN_MODS;", body)  # the MODS row's own item
        self.assertLess(body.index("fm_back_kind = MENU_KIND_SETTINGS;"), body.index("if (Ui_Ready())"))   # MELEE_ATLAS=0 keeps the legacy list item

    def test_language_is_a_row_that_hands_off(self):
        s = read("gmfrontend_settings.inc")
        row = func(s, "static void fsg_language(void)")
        self.assertIn("fm.native_req = true;", row)
        self.assertIn("fm.native_kind = MENU_KIND_SETTINGS;", row)
        self.assertIn("fm.native_sel = SEL_SETTINGS_LANG;", row)
        self.assertIn("fe.leaving = 1;", row)
        self.assertRegex(s, r'"Language", "[^"]*",\s*NULL, NULL, 0, 0, 0, NULL, fsg_fmt_language, fsg_atlas_only, fsg_language')

    def test_language_return_reopens_the_game_tab_on_language(self):
        g = read("gmfrontend.c")
        ret = func(g, "bool gmFrontend_NativeReturn(int kind, int sel)")
        self.assertIn("kind == MENU_KIND_SETTINGS && sel == SEL_SETTINGS_LANG", ret)
        self.assertIn("fe_settings_resume_game();", ret)
        self.assertLess(ret.index("fe_settings_resume_game();"), ret.index("fm_route_to_menus"))          # Atlas first; the legacy list for MELEE_ATLAS=0
        res = func(g, "static void fe_settings_resume_game(void)")
        self.assertIn("fe.screen = &fe_screen_settings[FSP_GAMEPLAY];", res)
        self.assertIn('fss.want_label = "Language";', res)
        self.assertIn("fm_back_sel = SEL_MAIN_SETTINGS;", res)

    def test_the_tab_table_matches_the_page_enum(self):
        s = read("gmfrontend_atlas_set.inc")
        names = re.search(r'fss_tab_names\[\] = "([^"]+)"', s).group(1).split(",")
        pages = re.search(r"fss_tab_page\[FSS_TABS\] = \{([^}]+)\}", s).group(1).replace(" ", "").split(",")
        self.assertEqual(names, ["VIDEO", "AUDIO", "CONTROLS", "ONLINE", "GAME", "MODS"])
        self.assertEqual(pages, ["FSP_VIDEO", "FSP_AUDIO", "FSP_CONTROLS", "FSP_ONLINE", "FSP_GAMEPLAY", "FSP_MODS"])     # GAME is FSP_GAMEPLAY and MODS comes last
        self.assertIn("#define FSS_TABS 6", s)
        enum = re.search(r"enum \{ (FSP_VIDEO[^}]*) \};", read("gmfrontend_settings.inc")).group(1)
        self.assertEqual(sorted(p.strip() for p in enum.split(",") if p.strip() != "FSP_COUNT"), sorted(pages))   # every page has a tab

    def test_mods_tab_refills_the_list_when_it_opens(self):
        s = read("gmfrontend_atlas_set.inc")
        self.assertIn("fsm_fill();", func(s, "static void fss_switch(const FrontendScreen* s)"))
        self.assertIn("fsm_fill();", func(read("gmfrontend.c"), "static void fe_settings_from_menus(int page)"))


if __name__ == "__main__":
    unittest.main()
