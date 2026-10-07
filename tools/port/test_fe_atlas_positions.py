"""Every (MenuKind, selection) the legacy router can produce lands on a visible item of an Atlas menu.

The frontend's menu tree (src/melee/gm/gmfrontend_menus.inc) is a position protocol: a menu is a MenuKind, an item is one of its
selection indices, and fm_position_for maps the game mode the player came from to the pair to land on. Atlas draws the same tree,
so every pair that table can produce has to name an item the Atlas menu shows. This test reads the source (no game, no disc).

Run from the workspace root:  GW_MELEE=<path to melee> python tools/port/test_fe_atlas_positions.py
"""
import os
import re
import unittest

GAME = os.environ.get("GW_MELEE") or os.path.join(os.path.dirname(__file__), "..", "..", "melee")
SRC = os.path.join(GAME, "src", "melee", "gm", "gmfrontend_menus.inc")


def read():
    with open(SRC, encoding="utf-8") as f:
        return f.read()


def table(text, name):
    """The rows of one `static const FeMenu <name>[]` table: kind -> (items array, atlas id or NULL)."""
    m = re.search(r"static const FeMenu %s\[\] = \{(.*?)\n\};" % re.escape(name), text, re.S)
    if not m:
        return {}
    rows = re.findall(r"\{\s*(MENU_KIND_\w+),\s*FM_\w+,.*?\"[A-Z .\-]+\",\s*(\w+),\s*FM_N\(\w+\)\s*(?:,\s*(\"[a-z.]+\"|NULL))?\s*\}", m.group(1), re.S)
    return {k: (arr, (aid or "NULL").strip('"')) for k, arr, aid in rows}


def menus(text):
    """What the player sees: the Atlas rows (fm_menus_atlas, when it exists) replace the legacy rows of the same kind."""
    out = table(text, "fm_menus")
    out.update(table(text, "fm_menus_atlas"))
    return out


def items(text, arr):
    m = re.search(r"static const FeMenuItem %s\[\] = \{(.*?)\n\};" % re.escape(arr), text, re.S)
    return re.findall(r"\{\s*\"[^\"]*\",\s*\"[^\"]*\",\s*(?:\"\w+\"|NULL),\s*(\w+)", m.group(1)) if m else []


def positions(text):
    body = text[text.index("static void fm_position_for"):]
    body = body[: body.index("int i;")]
    return re.findall(r"\{\s*GM_\w+,\s*(MENU_KIND_\w+),\s*(\w+)\s*\}", body)


class Positions(unittest.TestCase):
    def test_every_position_is_an_atlas_item(self):
        t = read()
        ms = menus(t)
        missing = []
        for kind, sel in positions(t):
            if kind == "MENU_KIND_EVENT":
                continue  # the Event list stays a retail screen (spec 13.2)
            self.assertIn(kind, ms, "%s has no menu" % kind)
            arr, aid = ms[kind]
            self.assertNotEqual(aid, "NULL", "%s is not an Atlas menu" % kind)
            sels = items(t, arr)
            if sel != "0" and sel not in sels:
                missing.append((kind, sel))
        self.assertEqual(missing, [])

    def test_atlas_ids_unique(self):
        ids = [aid for _arr, aid in menus(read()).values() if aid != "NULL"]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_atlas_menu_has_an_id(self):
        for kind, (_arr, aid) in menus(read()).items():
            self.assertNotEqual(aid, "NULL", "%s has no Atlas id" % kind)

    def test_back_targets_are_atlas_items(self):
        """B goes to (back_kind, back_sel) of each row: that pair is an item of an Atlas menu (or the main More strip)."""
        t = read()
        ms = menus(t)
        m = re.search(r"static const FeMenu fm_menus\[\] = \{(.*?)\n\};", t, re.S)
        for kind, bk, bs in re.findall(r"\{\s*(MENU_KIND_\w+),\s*FM_\w+,\s*\w+,\s*(\w+),\s*(\w+),", m.group(1)):
            if bk == "0xFF":
                continue
            arr, _aid = ms[bk]
            ok = bs in items(t, arr) or (bk == "MENU_KIND_MAIN" and bs in ("SEL_MAIN_TOY", "SEL_MAIN_DATA"))  # More: Collection, Data
            self.assertTrue(ok, "%s: B goes to %s %s, which is not an item" % (kind, bk, bs))

    def test_main_atlas_shape(self):
        """The Atlas main menu is exactly Solo, Versus, Online, Mods, Settings (More is drawn by the adapter); Versus lost Online."""
        t = read()
        self.assertEqual(items(t, "fm_main_atlas"), ["SEL_MAIN_1P", "SEL_MAIN_VS", "SEL_MAIN_ONLINE", "SEL_MAIN_MODS", "SEL_MAIN_SETTINGS"])
        vs = items(t, "fm_vs_atlas")
        self.assertNotIn("SEL_VS_ONLINE", vs)
        self.assertEqual(vs, ["SEL_VS_MELEE", "SEL_VS_TOURNAMENT", "SEL_VS_SPECIAL", "SEL_VS_RULES", "SEL_VS_NAME"])
        ms = menus(t)
        self.assertEqual(ms["MENU_KIND_MAIN"], ("fm_main_atlas", "main"))
        self.assertEqual(ms["MENU_KIND_VS"], ("fm_vs_atlas", "versus"))
        legacy = table(t, "fm_menus")
        self.assertEqual(legacy["MENU_KIND_MAIN"][1], "NULL")   # the legacy rows are not Atlas menus
        self.assertEqual(legacy["MENU_KIND_VS"][1], "NULL")

    def test_online_back_lands_on_main(self):
        t = read()
        body = t[t.index("static void fm_position_for"):]
        body = body[: body.index("for (i = 0; i < FM_N(map)")]
        self.assertIn("SEL_MAIN_ONLINE", body)

    def test_mods_page_back_lands_on_main(self):
        with open(os.path.join(GAME, "src", "melee", "gm", "gmfrontend.c"), encoding="utf-8") as f:
            g = f.read()
        self.assertIn("fm_back_sel = SEL_MAIN_MODS", g)

    def test_more_strip_targets_exist(self):
        """The More strip's Collection and Data return positions (SEL_MAIN_TOY, SEL_MAIN_DATA) are what the legacy rows hold."""
        t = read()
        self.assertIn("SEL_MAIN_TOY", items(t, "fm_main"))
        self.assertIn("SEL_MAIN_DATA", items(t, "fm_main"))
        with open(os.path.join(GAME, "src", "melee", "gm", "gmfrontend_atlas.inc"), encoding="utf-8") as f:
            a = f.read()
        self.assertIn("sel == SEL_MAIN_TOY", a)
        self.assertIn("sel == SEL_MAIN_DATA", a)

    @unittest.expectedFailure  # the FA_TBD tile is removed in the script API 2 change (Task 10); that change drops this mark
    def test_no_tbd_left(self):
        t = read()
        for word in ("FA_TBD", "SEL_MAIN_TBD", "Script_Tbd"):
            self.assertFalse(word in t, "%s is still in gmfrontend_menus.inc" % word)


if __name__ == "__main__":
    unittest.main()
