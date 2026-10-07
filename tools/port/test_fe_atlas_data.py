"""Static guards on the Atlas data adapter (src/melee/gm/gmfrontend_atlas_data.inc). No game, no disc.

    GW_MELEE=<game checkout> python -m unittest tools/port/test_fe_atlas_data.py     (from the workspace root)

Pins the plan's Review Focus items that source can pin: the adapter owns the cursor (1), back lands on the item that opened the screen (2), a screen
changes the save only through an allow-list of calls (6), the entry hook leaves every FA_NATIVE row in the table (retail untouched), and decoded text
never reaches a log (3, with check_no_disc_text.py).
"""
import os
import re
import unittest

ROOT = os.environ.get("GW_MELEE") or os.path.join(os.path.dirname(__file__), "..", "..", "melee")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as f:
        return f.read()


def function_body(text, signature):
    i = text.index(signature)
    j = text.index("\n}\n", i)
    return text[i:j]


class Adapter(unittest.TestCase):
    def setUp(self):
        self.t = read("src/melee/gm/gmfrontend_atlas_data.inc")

    def test_the_adapter_owns_the_cursor(self):
        # the host does not move a data screen's focus (it queues MOVE events), so the adapter must not hand the host's own mover the work back: no
        # FSS_IN_MOVE intent comes from anywhere but the pad feed, and the cursor moves over the WHOLE list (total), not over a window
        body = function_body(self.t, "static void fad_event(")
        self.assertIn("fad.total - 1", body, "up and down wrap over the whole list")
        self.assertNotRegex(body, r"Ui_SetIntent", "events are handled here, never fed back to the host")
        sync = function_body(self.t, "static bool fad_sync(")
        self.assertIn("Ui_DataFirst(fad.total", sync, "the window slides over the total")
        self.assertIn("Ui_SetFocus(fad.h", sync, "the host is told the focus by id")

    def test_a_hover_is_a_window_relative_slot(self):
        body = function_body(self.t, "static void fad_event(")
        self.assertRegex(body, r"fad\.first \+ slot", "a hover or a click adds the window's first row")

    def test_a_locked_row_cannot_be_accepted(self):
        self.assertRegex(self.t, r"i > fad_ev_last\)\s*\{\s*return false", "the event start refuses a locked row too (the host also drops it)")

    def test_back_returns_to_the_parent_item(self):
        # every screen names the (MenuKind, SEL) its native entry used, and it is one mn_PcOpenNative opens
        mn = read("src/melee/mn/mnmain.c")
        native = mn[mn.index("static void mn_PcOpenNative"):mn.index("not a native screen")]
        rows = re.findall(r"\{\s*FD_\w+\s*,\s*\"[\w.]+\"\s*,\s*\"[^\"]*\"\s*,\s*(MENU_KIND_\w+)\s*,\s*(SEL_\w+)", self.t)
        self.assertEqual(len(rows), 7, "events, name, sound, messages, bonus, misc, vsrec")
        for kind, sel in rows:
            self.assertIn(sel, native, "%s %s is not a native entry point" % (kind, sel))
        # and the parent menu is never changed: closing a data screen resubmits the menu, nothing sets fm.pend_kind for B
        back = function_body(self.t, "static void fad_back(")
        self.assertNotIn("fm.pend_kind", back)

    def test_screens_write_only_what_is_listed(self):
        writers = set(re.findall(r"\b(gmMainLib_\w*(?:Set|Write|Save)\w*|lbCardGame_SaveChanges|DeleteName|CreateNameAtIndex|WriteCharactersForNameAtIndex|gm_801BEB74|gmMainLib_8015ED68)\s*\(", self.t))
        self.assertEqual(writers, {"gm_801BEB74", "gmMainLib_8015ED68"},
                         "the save writes are the selection an event start stores (as mnEvent_8024D864 does) and the heard-track flag Sound Test stores for a track that sets one (mnSoundTest_PlaySampleAnim)")
        # the heard-track write is only ever made for a track lbAudioAx_80023090 flags, exactly as retail does
        body = function_body(self.t, "static bool fad_snd_accept(")
        self.assertRegex(body, r"if \(lbAudioAx_80023090\(.*\) != 0\) \{\s*gmMainLib_8015ED68")
        # Sound Test applies the saved volumes to the live mixer and sets none
        self.assertNotRegex(self.t, r"gmMainLib_8015ED6[0-79-F]|SetVolume|Settings_SetInt")
        # the Name Entry list opens retail for edits: it never writes a name itself
        self.assertNotRegex(function_body(self.t, "static bool fad_name_accept("), r"CreateName|WriteCharacters|DeleteName")

    def test_the_wheel_stops_at_the_ends_and_keys_wrap(self):
        body = function_body(self.t, "static void fad_event(")
        self.assertRegex(body, r"if \(slot == 1\)", "the host marks the wheel with slot 1")
        self.assertRegex(body, r"to >= 0 && to < fad\.total", "the wheel does not wrap")
        host = read("pc/platform/gw_script_ui_set.inc")
        self.assertIn("gs_set_push(GS_SETEV_MOVE, 1,", host)

    def test_every_text_read_is_bounded(self):
        self.assertIn("idx >= fad_sis_n", self.t, "the index is bounded by the table's real count, not a constant")
        self.assertNotIn("0x600", self.t)
        body = function_body(self.t, "static int fad_sis_text(")
        self.assertIn("Ui_SisDecode(p, len,", body, "the decoder is told how many bytes it may read")
        self.assertIn("p >= base + size", function_body(self.t, "static const u8* fad_sis_stream("), "a pointer outside the archive's data is refused")

    def test_a_missing_table_closes_the_archive_and_is_remembered(self):
        body = function_body(self.t, "static bool fad_sis_open(")
        self.assertIn("fad_sis_failed", body)
        self.assertRegex(body, r"HSD_SisLib_803A947C\(fad_sis_arc\);[^}]*fad_sis_failed = true")
        self.assertRegex(body, r"if \(fad_sis_failed \|\| fad_has\(Ui_EnvData\(\), \"notext\"\)\)")

    def test_notext_alone_means_every_screen(self):
        body = function_body(self.t, "static void fad_read_env(")
        self.assertIn("!any ||", body)

    def test_native_rows_stay_in_the_table(self):
        m = read("src/melee/gm/gmfrontend_menus.inc")
        self.assertIn("fad_open_for(m->kind, it->sel)", m, "the hook sits in fm_confirm")
        self.assertEqual(len(re.findall(r"FA_ATLAS", m)), 0, "no table row changed: FA_NATIVE stays, the retail screen is the fallback")
        hook = m.index("fad_open_for(m->kind, it->sel)")
        stop = m.index("it->sel == SEL_DATA_SOUND", hook - 400)
        self.assertLess(hook, stop + 200, "the hook comes before the Sound Test stop calls")
        self.assertIn("fad_frame(pad_in)", m)
        self.assertIn("fad_scene_exit();", m)

    def test_no_move_is_fed_to_a_data_screen_from_the_menu_path(self):
        a = read("src/melee/gm/gmfrontend_atlas.inc")
        self.assertIn("fad_sync()", a)
        self.assertLess(a.index("fad_sync()"), a.index("fa_submit(fm.menu)"), "the menu is not submitted while a data screen is up")

    def test_text_is_decoded_per_string_and_a_bad_glyph_keeps_the_authored_label(self):
        body = function_body(self.t, "static int fad_sis_text(")
        self.assertRegex(body, r"st\[1\] == 0 && st\[3\] == 0 && st\[4\] == 0", "unknown glyphs, jumps and bad opcodes all refuse a string")
        ev = function_body(self.t, "static void fad_ev_open(")
        self.assertIn("fad_ev_name[i][0] = '\\0'; /* a name with a glyph we cannot show", ev)

    def test_text_probe_logs_counts_only(self):
        for line in self.t.splitlines():
            if "OSReport(" in line and "%s" in line:
                self.assertIn("OK-NOTEXT", line, line.strip())

    def test_netplay_and_atlas_off_leave_retail(self):
        body = function_body(self.t, "static bool fad_wants(")
        self.assertIn("!Ui_Ready() || Ui_NetplayActive()", body)
        self.assertIn("fad_results_standin", self.t)
        stand = function_body(self.t, "static GameScene* fad_results_standin(")
        self.assertIn("Ui_NetplayActive()", stand)

    def test_every_screen_in_the_table_has_the_calls_a_screen_needs(self):
        table = self.t[self.t.index("static const FadScreen fad_screens[]"):]
        table = table[:table.index("};")]
        for row in re.findall(r"\{ (FD_\w+),(.*?)\},\n", table, re.S):
            fields = [x.strip() for x in row[1].split(",")]
            self.assertTrue(any(f.endswith("_total") for f in fields), row[0])
            self.assertTrue(any(f.endswith("_row") for f in fields), row[0])
            self.assertTrue(any(f.endswith("_explain") for f in fields), row[0])
            self.assertTrue(any(f.endswith("_keys") for f in fields), row[0])


if __name__ == "__main__":
    unittest.main()
