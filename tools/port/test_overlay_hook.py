"""Static guards on the framed trophy scenes' OVERLAY hook (Atlas step 10).

    python -m unittest tools/port/test_overlay_hook.py        (GW_MELEE = the game checkout, default <root>/melee)

What they pin, from the plan's Review Focus: retail's own on_frame runs first and always (the wrapper never swallows it); Atlas reads no pad and records no
hit; the wrapper exists only on the PC build and only for an OVERLAY scene (or the probe); no framed screen draws while a session is on; the policy mask is
set before the scene's on_enter (Script_SceneBegin runs AFTER on_enter: the plan assumed the opposite); the probe logs numbers, never text.
"""
import os
import re
import unittest

ROOT = os.environ.get("GW_MELEE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "melee")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as f:
        return f.read().replace("\r\n", "\n")


def body(text, signature_re):
    """The text of the first function whose header matches, up to its closing brace in column 0."""
    m = re.search(signature_re, text)
    assert m, "function not found: " + signature_re
    end = text.index("\n}\n", m.start())
    return text[m.start():end]


class Hook(unittest.TestCase):
    def test_inner_on_frame_runs_first_and_always(self):
        t = read("src/melee/gm/gmfrontend_atlas_toy.inc")
        b = body(t, r"static void fat_overlay_frame\(void\)")
        self.assertLess(b.index("fat_inner"), b.index("fat_submit"), "the retail on_frame must run before the chrome is submitted")
        first_return = b.find("return")
        self.assertGreater(first_return, b.index("fat_inner();"), "a return before the inner on_frame would skip the retail frame")
        self.assertRegex(b, r"if \(fat_inner != NULL\) \{\n\s*fat_inner\(\);\n\s*\}", "the inner call is unconditional but for NULL")

    def test_no_pad_and_no_hits(self):
        t = read("src/melee/gm/gmfrontend_atlas_toy.inc")
        for banned in ("Ui_Intent", "Ui_PollEvent", "Ui_Tile", "Ui_More"):
            self.assertNotIn(banned, t)
        host = read("pc/platform/gw_script_ui_toy.inc")
        self.assertIn("input_feed = 1", host, "a framed screen reads no pad")
        main = read("pc/platform/gw_script_ui.inc")
        self.assertRegex(main, r"AT_PRIMARY_FRAME\) return;", "the host's engine event handler ignores a framed screen")
        screen = read("pc/platform/gw_ui_screen.c")
        self.assertRegex(screen, r"at_screen_wants_pad[^\n]*AT_PRIMARY_FRAME")

    def test_wrapper_only_under_target_pc_and_overlay(self):
        g = read("src/melee/gm/gm_1A3F.c")
        i = g.index("Fad_OverlayWrap")
        before = g[:i]
        self.assertGreater(before.rfind("#if defined(TARGET_PC)"), before.rfind("#endif"), "the wrapper call is inside a TARGET_PC block")
        window = g[max(0, i - 400):i + 300]
        self.assertRegex(window, r"AT_POLICY_OVERLAY")
        self.assertIn("Ui_ToyProbe", window)
        # the retail call is untouched off the PC build
        self.assertRegex(g, r"#else\n\s*gm_801A4D34\(scene->on_frame, info\);\n#endif")

    def test_the_wrapper_is_only_for_the_three_scenes(self):
        t = read("src/melee/gm/gmfrontend_atlas_toy.inc")
        b = body(t, r"void \(\*Fad_OverlayWrap")
        self.assertRegex(b, r"kind != GS_TOY_GALLERY && kind != GS_TOY_LOTTERY && kind != GS_TOY_COLLECTION\) \{\n\s*return inner;")
        self.assertIn("_Static_assert(GS_TOY_GALLERY == 11 && GS_TOY_LOTTERY == 12 && GS_TOY_COLLECTION == 13", t)

    def test_online_guard(self):
        t = read("src/melee/gm/gmfrontend_atlas_toy.inc")
        b = body(t, r"static void fat_overlay_frame\(void\)")
        self.assertIn("Ui_NetplayActive()", b)
        self.assertLess(b.index("Ui_NetplayActive()"), b.index("fat_submit(fat_kind)"), "the online check comes before the submit")
        self.assertNotRegex(t, r"\bNetplay_\w+|\bgw_Netplay", "game-side adapter files name no netplay function (check_atlas_online.sh)")
        host = read("pc/platform/gw_script_ui_toy.inc")
        self.assertNotRegex(host, r"gw_Netplay_|Netplay_Enabled", "the host half reads online state only through gs_ui_online")

    def test_policy_mask_is_set_before_on_enter(self):
        g = read("src/melee/gm/gm_1A3F.c")
        self.assertLess(g.index("Ui_ScenePolicyMask("), g.index("scene->on_enter(info->enter_data)"))
        # why: Script_SceneBegin (the host's scene hook) is in gm_801A4D34, after on_enter
        s = read("src/melee/gm/gmscene.c")
        self.assertGreater(s.index("Script_SceneBegin(info"), s.index("void gm_801A4D34"))
        self.assertNotIn("Script_SceneBegin", body(s, r"void gm_801A4B88\("))

    def test_probe_logs_numbers_only(self):
        t = read("src/melee/gm/gmfrontend_atlas_toy.inc")
        b = body(t, r"static void fat_probe\(u8 kind\)")
        for m in re.finditer(r'OSReport\("([^"]*)"', b):
            self.assertNotIn("%s", m.group(1), "the probe never prints a string (no disc text in a log)")

    def test_no_window_means_no_chrome_and_no_mask(self):
        t = read("src/melee/gm/gmfrontend_atlas_toy.inc")
        for name in ("FAT_GALLERY_WIN", "FAT_LOTTERY_WIN", "FAT_COLLECTION_WIN"):
            self.assertRegex(t, r"static const int " + name + r"\[4\] = \{ [0-9, ]+ \};")
        self.assertIn("Fad_ToyWindowKnown", read("src/melee/gm/gm_1A3F.c"))
        host = read("pc/platform/gw_script_ui_toy.inc")
        self.assertRegex(host, r"if \(!\(w > 0 && h > 0\) && !gs_ui_frame_win_set\)", "an unmeasured window is refused, not drawn as a whole-canvas plate")


if __name__ == "__main__":
    unittest.main()
