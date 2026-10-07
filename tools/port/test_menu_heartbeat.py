"""Static guards for the Controls heartbeat and the menu-major list: python tools/port/test_menu_heartbeat.py"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")


def read(*p):
    return open(os.path.join(GAME, *p), encoding="utf-8", errors="replace").read()


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

    def test_remap_layer_runs_only_after_the_heartbeat(self):
        """fss_remap_frame is called from exactly one place, the settings branch, after the heartbeat."""
        body = frontend_on_frame()
        hb = body.index("Controls_Menu(")
        calls = [m.start() for m in re.finditer(r"fss_remap_frame\(", body)]
        self.assertLessEqual(len(calls), 1)
        for c in calls:
            self.assertGreater(c, hb)
        others = []
        gm = os.path.join(GAME, "src", "melee", "gm")
        for name in sorted(os.listdir(gm)):
            if not name.endswith((".c", ".inc", ".h")) or name == "gmfrontend_atlas_remap.h":
                continue
            text = read("src", "melee", "gm", name)
            if name == "gmfrontend.c":
                text = text.replace(body, "")
            for m in re.finditer(r"fss_remap_frame\(", text):
                line = text[text.rfind("\n", 0, m.start()) + 1:text.find("\n", m.start())]
                if not line.lstrip().startswith(("static", "/*", "*", "//")):
                    others.append((name, line.strip()))
        self.assertEqual(others, [], "fss_remap_frame is called only from the settings branch of the frontend frame")


if __name__ == "__main__":
    unittest.main()
