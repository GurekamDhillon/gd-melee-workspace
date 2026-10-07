"""The one line each mode's CSS and SSS state carries (gmFrontend_AtlasSelect) is where the audit says it must be, and the legacy writer the Atlas select ends
through does not touch what a mode's exit handler keeps.

    python tools/port/test_css_hooks.py        (GW_MELEE selects the game checkout)

 1. every GS_CSS / GS_SSS state in css_states.py (the audit of the game sources) either carries the hook in its on_enter (or in a static helper that
    on_enter calls, one level deep) with the right `sss` argument, or is on the list of states that go another way, with the reason;
 2. the hook appears in no function that is not the on_enter of such a state;
 3. fs_css_finish (gmfrontend_select.inc), which the Atlas select ends the scene through, never assigns stocks or nametag: a mode's exit handler reads them
    through gm_801B0730 and they must arrive exactly as the mode's on_enter set them;
 4. the held groups (Classic, Adventure, All-Star, Stadium) are gated in gmFrontend_AtlasSelect and the gate names what the retail screens show that the Atlas
    one does not yet.
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import css_states  # noqa: E402

GAME = css_states.GAME
GM = css_states.GM

# states that reach their select another way, or are not a player-facing select
OTHER_WAY = {
    "gmvsmode.c": "VS mode: gmFrontend_SelectScene (always on the kit's select)",
    "gmtrainingmode.c": "Training: gmFrontend_TrainingSelect",
    "gmhanyucss.c": "the debug scene GM_HANYU_CSS (cycles match_type on exit)",
    "gmhanyusss.c": "the debug scene GM_HANYU_SSS",
    "gmtoumode.c": "the tournament SSS data scene: it forces its stage (force_stage_id) and has no select of its own",
}

STRIP = re.compile(r"/\*.*?\*/|//[^\n]*|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'", re.S)
HEAD = re.compile(r"^(?:static\s+)?[A-Za-z][\w\s\*]*?\b(\w+)\([^;{}]*\)\s*\{", re.M)


def read(name):
    with open(os.path.join(GM, name), encoding="utf-8", errors="replace") as f:
        return f.read().replace("\r\n", "\n")


def blank(text):
    """The text with comments, strings and character constants blanked (same length): a brace inside one is not a brace."""
    return STRIP.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def span(flat, m):
    """A function ends at the first closing brace in column 0 (the decomp's style; brace counting is thrown by #if branches)."""
    j = flat.find("\n}", m.end())
    return m.start(), len(flat) if j < 0 else j + 2


def functions(text):
    """[(name, body)] of the top-level functions of a C file: a header at the start of a line, then its braces matched."""
    flat = blank(text)
    out = []
    pos = 0
    while True:
        m = HEAD.search(flat, pos)
        if not m:
            return out
        a, b = span(flat, m)
        out.append((m.group(1), text[a:b]))
        pos = b


def body(text, fn):
    for name, b in functions(text):
        if name == fn:
            return b
    return None


def hook_args(b):
    return [int(x) for x in re.findall(r"gmFrontend_AtlasSelect\(\s*\w+\s*,\s*(\d)\s*,", b)]


class Hooks(unittest.TestCase):
    def test_every_audited_state_has_its_hook_or_a_reason(self):
        seen = set()
        for r in css_states.scan():
            if r["file"] in OTHER_WAY:
                continue
            text = read(r["file"])
            b = body(text, r["on_enter"])
            self.assertIsNotNone(b, "%s: on_enter %s not found" % (r["file"], r["on_enter"]))
            args = hook_args(b)
            if not args:                                   # a static helper on_enter calls (Multi-Man's six states share one)
                for callee in re.findall(r"\b(\w+)\s*\(", b):
                    cb = body(text, callee)
                    if cb is not None and callee != r["on_enter"]:
                        args += hook_args(cb)
            want = 0 if r["scene"] == "GS_CSS" else 1
            self.assertEqual(args, [want], "%s %s: expected one hook with sss=%d, found %r" % (r["file"], r["on_enter"], want, args))
            seen.add((r["file"], r["on_enter"]))
        self.assertGreater(len(seen), 20)

    def test_the_hook_is_nowhere_else(self):
        allowed = {}
        for r in css_states.scan():
            allowed.setdefault(r["file"], set()).add(r["on_enter"])
        found = 0
        for name in sorted(os.listdir(GM)):
            if not name.endswith(".c") or name.startswith("gmfrontend"):
                continue
            for fn, fb in functions(read(name)):
                if "gmFrontend_AtlasSelect(" not in fb:
                    continue
                found += 1
                ok = fn in allowed.get(name, set())
                if not ok and name == "gmmultiman.c":
                    ok = fn == "gm_801B6AD8_inline"       # the one static helper only the six on_enter functions call
                self.assertTrue(ok, "%s: the hook is in %s, which is not the on_enter of a CSS or SSS state" % (name, fn))
        self.assertGreater(found, 20)

    def test_multiman_helper_is_only_called_by_on_enter(self):
        text = read("gmmultiman.c")
        enters = {r["on_enter"] for r in css_states.scan() if r["file"] == "gmmultiman.c"}
        callers = [fn for fn, fb in functions(text) if re.search(r"\bgm_801B6AD8_inline\(", fb) and fn != "gm_801B6AD8_inline"]
        self.assertEqual(len(callers), 6)
        for fn in callers:
            self.assertIn(fn, enters, "the helper is called from %s, which is not an on_enter" % fn)

    def test_the_finish_writer_never_touches_stocks_or_nametag(self):
        sel = read("gmfrontend_select.inc")
        b = body(sel, "fs_css_finish")
        self.assertIsNotNone(b)
        self.assertNotRegex(b, r"\bstocks\b")
        self.assertNotRegex(b, r"\bnametag\b")
        # and the preload writes only the entering port's entry in a one-player mode
        pb = body(sel, "fs_preload_players")
        self.assertIsNotNone(pb)
        self.assertIn("fs_preload_only", pb)

    def test_a_routed_mode_leaves_nothing_behind_for_training_or_the_next_scene(self):
        """gmFrontend_AtlasSelect registers a state's data and a mode name; gm_Scene_Frontend_OnEnter uses them up. A stale registration would make a later scene (Training's
        CSS after a routed mode, VS, the LAB) match the wrong branch and take the wrong rules."""
        text = read("gmfrontend.c")
        enter = body(text, "gm_Scene_Frontend_OnEnter")
        self.assertIsNotNone(enter)
        # the training branch still exists and sets the training rules: fe_sel_training = true and Training's own data
        tr = enter[enter.index("fe_train_css || enter_data == fe_train_sss"):]
        self.assertIn("fe_sel_training = true", tr)
        self.assertIn("fe_sel_css = (CSSData*) fe_train_css", tr)
        # every other branch sets fe_sel_training = false (VS, the routed modes)
        self.assertEqual(enter.count("fe_sel_training = false"), 2)
        # both registrations are cleared after the whole chain (so a routed VS-data mode, which the first branch catches, is cleared too), before the menus return
        tail = enter[enter.index("fe_sel_training = true"):]
        self.assertRegex(tail, r"fe_ats_css = NULL;\s*fe_ats_sss = NULL;")
        self.assertLess(tail.index("fe_ats_css = NULL;"), tail.index("if (fe.next_menus)"))
        # the registration is a pointer compare against fe_ats_*: a cleared (NULL) one never matches real enter data
        self.assertIn("enter_data != NULL && (enter_data == fe_ats_css || enter_data == fe_ats_sss)", enter)
        # the named mode a ModeSelect queued is not wiped by a mode that has no name
        at = body(text, "gmFrontend_AtlasSelect")
        self.assertRegex(at, r"if \(name != NULL\) \{\s*fe_sel_mode_pending = name;")

    def test_the_route_is_decided_before_the_state_is_routed(self):
        at = body(read("gmfrontend.c"), "gmFrontend_AtlasSelect")
        self.assertIn("Ui_SelCanOpen() == 0", at)                       # the Atlas screen could not open: the state stays on the retail screen
        self.assertIn("Frontend_NativeSelect() != 0", at)               # MELEE_NATIVE_CSS=1 keeps the retail screens
        self.assertLess(at.index("Ui_SelCanOpen() == 0"), at.index("fe_ats_css = css"))
        self.assertLess(at.index("Frontend_NativeSelect() != 0"), at.index("scene_kind = GS_FRONTEND"))

    def test_the_preload_filter_is_set_only_once_the_screen_is_up(self):
        a = read("gmfrontend_atlas_select.inc")
        f = body(a, "fas_open_css")
        self.assertIsNotNone(f)
        self.assertNotIn("fs_preload_only = fas.enter", f[:f.index("Ui_SelOpen(")])      # not before the open
        self.assertIn("fs_preload_only = fas.enter", f[f.index("Ui_SelOpen("):])
        self.assertRegex(a, r"\} fas = \{ 0, 0, -1, 0, -1, -1 \};")                       # no zeroed handle: a zero is a valid-looking handle
        self.assertEqual(len(re.findall(r"fas_art_identity\(", a)), 3)                    # defined once, called for fighters and stages

    def test_the_select_opened_in_a_scene_init_belongs_to_the_scene_that_begins(self):
        """D1: the frontend opens the select in the scene's init, before Script_SceneBegin runs Ui_SceneExit for the ending scene. The open is bracketed with
        Ui_SelNextScene so the host stamps the screen for the scene that is about to begin; without it the screen opened and closed in the same frame."""
        enter = body(read("gmfrontend.c"), "gm_Scene_Frontend_OnEnter")
        self.assertIsNotNone(enter)
        i = enter.index("fl_open(fe.screen->art)")
        self.assertRegex(enter[:i], r"Ui_SelNextScene\(1\);\s*$")
        self.assertRegex(enter[i:], r"^fl_open\(fe\.screen->art\);\s*Ui_SelNextScene\(0\);")

    def test_the_legacy_panels_draw_nothing_under_an_atlas_select_or_a_room_screen(self):
        """D2: with the Atlas select up fl.on is never set (the legacy build is skipped), so fe_draw_panels fell through to the rows loop over a stale n_list and
        a NULL items table (Giant Melee crashed there) and drew the blue plate and arrows that stayed after leaving."""
        d = body(read("gmfrontend.c"), "fe_draw_panels")
        self.assertIsNotNone(d)
        self.assertRegex(d, r"fe\.screen == NULL \|\| fe\.screen->art != 0 \|\| fas_active\(\)")
        self.assertLess(d.index("fas_active()"), d.index("hsd_80391A04"))

    def test_the_settings_door_closes_with_its_scene_before_the_select_opens(self):
        """D3: Match Setup > Continue starts the CSS scene; the settings screen is native too (one at a time) and was closed only by Ui_SceneExit, which runs after the
        new scene's init, so the select was refused and the legacy kit CSS drew. fss_exit closes the host screen itself, as fss_close does before a room."""
        e = body(read("gmfrontend_atlas_set.inc"), "fss_exit")
        self.assertIsNotNone(e)
        self.assertRegex(e, r"if \(fss\.h >= 0\) \{\s*Ui_SetClose\(fss\.h\);")
        self.assertLess(e.index("Ui_SetClose(fss.h)"), e.index("fss.h = -1"))

    def test_held_groups_are_gated_and_say_why(self):
        text = read("gmfrontend.c")
        b = body(text, "gmFrontend_AtlasSelect")
        self.assertIsNotNone(b)
        self.assertIn("atlas_select_solo", b)
        self.assertRegex(b, r"mt >= 0xB && mt <= 0xD")
        self.assertRegex(b, r"mt >= 0xF && mt <= 0x16")
        doc = text[text.index("THE ONE ENTRY POINT"):text.index("void gmFrontend_AtlasSelect")]
        for word in ("difficulty", "stock", "record"):
            self.assertIn(word, doc)


if __name__ == "__main__":
    unittest.main()
