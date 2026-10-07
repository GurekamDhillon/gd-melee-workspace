"""Static guards for the Controls heartbeat and the menu-major list: python tools/port/test_menu_heartbeat.py"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")


def read(*p):
    with open(os.path.join(GAME, *p), encoding="utf-8", errors="replace") as f:
        return f.read().replace("\r\n", "\n")


def frontend_on_frame():
    src = read("src", "melee", "gm", "gmfrontend.c")
    body = src[src.index("void gm_Scene_Frontend_OnFrame(void)"):]
    return body[:body.index("\nvoid gm_Scene_Frontend_OnExit")]


class Heartbeat(unittest.TestCase):
    def test_menu_majors_unchanged(self):
        rt = read("pc", "platform", "gw_controls_runtime.inc")
        m = re.search(r"int menu = (.*?);", rt, re.S).group(1)
        majors = sorted(int(x, 0) for x in re.findall(r"major == (0x[0-9A-Fa-f]+|\d+)", m))
        self.assertEqual(majors, [0, 1, 8, 9, 0x0B, 0x0C, 0x0D, 0x2E])

    def test_window_is_100ms(self):
        rt = read("pc", "platform", "gw_controls_runtime.inc")
        self.assertIn("ctl_menu_until = GetTickCount() + 100;", rt)

    def test_heartbeat_runs_once_before_any_branch(self):
        body = frontend_on_frame()
        beats = [m.start() for m in re.finditer(r"Controls_Menu\(", body)]
        self.assertEqual(len(beats), 1, "exactly one heartbeat call per frame")
        for needle in ("fa_frame(", "fas_frame(", "fas.active", "fss_frame(", "fk_frame(", "fss_frame(", "fss_active("):
            i = body.find(needle)
            if i >= 0:
                self.assertLess(beats[0], i, "the heartbeat must come before %s" % needle)

    def test_remap_screen_stays_the_table(self):
        src = read("src", "melee", "gm", "gmfrontend.c")
        self.assertIn("fe.screen == &fe_screen_remap ? fcr_port : -1", src)

    def test_the_atlas_branch_comes_after_the_heartbeat(self):
        """The settings branch (fss_frame) is called once, from gm_Scene_Frontend_OnFrame, after Controls_Menu."""
        body = frontend_on_frame()
        hb = body.index("Controls_Menu(")
        calls = [m.start() for m in re.finditer(r"fss_frame" + chr(92) + "(", body)]
        self.assertEqual(len(calls), 1, "one Atlas settings branch")
        self.assertGreater(calls[0], hb, "the Atlas branch must come after the Controls_Menu heartbeat")

    def test_remap_layer_runs_only_inside_the_settings_branch(self):
        """fss_remap_frame (fcr_frame, moved) is called from exactly one place: inside fss_frame, which runs after the heartbeat."""
        gm = os.path.join(GAME, "src", "melee", "gm")
        found = []
        for name in sorted(os.listdir(gm)):
            if not name.endswith((".c", ".inc", ".h")):
                continue
            text = read("src", "melee", "gm", name)
            for m in re.finditer(r"fss_remap_frame" + chr(92) + "(", text):
                line = text[text.rfind(chr(10), 0, m.start()) + 1:text.find(chr(10), m.start())]
                if line.lstrip().startswith(("static", "/*", "*", "//")):
                    continue                                    # its definition and comments
                found.append((name, m.start()))
        self.assertEqual([n for n, _ in found], ["gmfrontend_atlas_set.inc"], "only the Atlas settings file calls it")
        text = read("src", "melee", "gm", "gmfrontend_atlas_set.inc")
        start = text.index("static bool fss_frame(void)")
        self.assertTrue(start < found[0][1] < text.index(chr(10) + "}" + chr(10), start), "and only inside fss_frame")
        body = frontend_on_frame()
        self.assertNotIn("fss_remap_frame", body, "gm_Scene_Frontend_OnFrame never calls the remap layer itself")
        self.assertNotIn("fcr_frame", body.split("fss_frame")[0].split("Controls_Menu(")[1], "no legacy capture frame runs between the heartbeat and the Atlas branch")

    def test_the_legacy_remap_frame_is_unchanged(self):
        """The legacy path (MELEE_ATLAS=0) still calls fcr_frame for the remap screen, after the Atlas branch."""
        body = frontend_on_frame()
        self.assertIn("fe.screen == &fe_screen_remap && fcr_frame()", body)
        self.assertLess(body.index("fss_frame("), body.index("fcr_frame()"))


if __name__ == "__main__":
    unittest.main()
