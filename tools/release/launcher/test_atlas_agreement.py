"""One source, every consumer: tokens.css -> tokens.json -> gw_ui_tokens.h, and the launcher loads the same JSON.

    python -m unittest tools/release/launcher/test_atlas_agreement.py

The launcher side of the agreement is also pinned in C++ (atlas_tests.cpp: tokens_load pins the constants,
tokens_match_the_file compares every loaded token against the repo's tokens.json). Change one source and a
test names it.
"""
import json, os, re, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "menu", "pipeline"))
import atlas_tokens as T


def game_header():
    """gw_ui_tokens.h of the game checkout: GW_MELEE, <root>/melee, or (in a worktree) the main checkout's melee."""
    candidates = []
    if os.environ.get("GW_MELEE"):
        candidates.append(os.environ["GW_MELEE"])
    candidates.append(os.path.join(ROOT, "melee"))
    if os.path.basename(os.path.dirname(ROOT)) == "worktrees":
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(ROOT)), "melee"))
    for c in candidates:
        h = os.path.join(c, "pc", "platform", "gw_ui_tokens.h")
        if os.path.exists(h):
            return h
    return None


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Agreement(unittest.TestCase):
    def test_json_is_the_css(self):
        css = T.parse(read(T.SRC)); on_disk = json.loads(read(T.OUT_JSON))
        for k in ("colours", "px", "ms"):
            self.assertEqual(css[k], on_disk[k], "menu/atlas/tokens.json is stale: run menu/pipeline/atlas_tokens.py")

    def test_header_is_the_json(self):
        hdr = game_header()
        if not hdr:
            self.skipTest("no game checkout: set GW_MELEE")
        text = read(hdr); tok = json.loads(read(T.OUT_JSON))
        for name, v in tok["colours"].items():
            self.assertIn("#define %s 0x%08Xu" % (T.cname("C", name), v), text, name)
        for name, v in tok["px"].items():
            self.assertRegex(text, r"#define %s %d\b" % (T.cname("PX", name), v), name)
        for name, v in tok["ms"].items():
            self.assertRegex(text, r"#define %s %d\b" % (T.cname("MS", name[2:] if name.startswith("m-") else name), v), name)

    def test_launcher_reads_the_same_file(self):
        qrc = read(os.path.join(HERE, "qt", "kit.qrc"))
        self.assertIn("menu/atlas/tokens.json", qrc)                       # the resource is the repo file, not a copy
        for name in ("kit.cpp", "window.cpp"):
            src = read(os.path.join(HERE, "qt", name))
            self.assertEqual(re.findall(r'QColor\(\s*"?#[0-9a-fA-F]{6}', src), [], name + ": a hex colour in the painting code: use atlas::colour")
            self.assertEqual(re.findall(r'"#[0-9a-fA-F]{6}"', src), [], name + ": a hex string in the painting code")
            self.assertEqual(re.findall(r'QColor\(\s*\d+\s*,\s*\d+\s*,\s*\d+', src), [], name + ": a numeric colour in the painting code")
            self.assertEqual(re.findall(r'\bQt::(?:red|green|blue|yellow|cyan|magenta|gray|darkGray|lightGray)\b', src), [], name + ": a Qt named colour")

    def test_launcher_values_match(self):
        tok = json.loads(read(T.OUT_JSON))
        self.assertEqual(tok["colours"]["ember"], 0xFF7A3DFF); self.assertEqual(tok["px"]["t-row"], 16)   # the values atlas_tests.cpp's tokens_load pins

    def test_the_launcher_ships_its_fonts_and_tokens_as_resources_only_from_menu(self):
        qrc = read(os.path.join(HERE, "qt", "kit.qrc"))
        self.assertIn("menu/Barlow/BarlowCondensed-SemiBold.ttf", qrc); self.assertIn("menu/Barlow/BarlowCondensed-Bold.ttf", qrc)
        self.assertIn("menu/SourceSans3/SourceSans3-Semibold.otf", qrc)


if __name__ == "__main__":
    unittest.main()
