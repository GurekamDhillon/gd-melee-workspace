"""Static guards on the retail guards of the framed trophy scenes (Atlas step 10).

    python -m unittest tools/port/test_toy_guards.py        (GW_MELEE = the game checkout, default <root>/melee)

A guard hides what is DRAWN, never what runs: a render callback that returns early, a text object's `hidden` flag. These tests pin where such a line may
be (Review Focus 1, 8 and 10): only under TARGET_PC, never inside a GObj proc, only at the creation or draw sites of the pieces named in
gw_ui_retail_ids.h, never on the retail 3D (the viewer, the backdrop, the machine, the coins, the popup); and the scenes with nothing to hide have no
guard at all.
"""
import os
import re
import unittest

ROOT = os.environ.get("GW_MELEE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "melee")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as f:
        return f.read().replace("\r\n", "\n")


def function_bodies(text):
    """name -> body, for functions whose header starts in column 0 and ends with `{` at the end of a line, closing brace in column 0."""
    out = {}
    for m in re.finditer(r"^(?:[A-Za-z_][\w \*]*?[ \*])(\w+)\([^;{}]*\)\s*\{\n", text, re.M):
        end = text.find("\n}\n", m.end())
        if end > 0:
            out[m.group(1)] = text[m.start():end]
    return out


def proc_names(text):
    """the functions set up as GObj procs: HSD_GObj_SetupProc(gobj, [cast] name, prio)"""
    return set(m.group(1) for m in re.finditer(r"HSD_GObj_SetupProc\(\s*[^,]+,\s*(?:\([^)]*\)\s*)?_?(\w+)\s*,", text))


def lines_with(text, needle):
    return [(i + 1, l) for i, l in enumerate(text.split("\n")) if needle in l]


def inside_target_pc(text, lineno):
    """True when the line is inside an open `#if defined(TARGET_PC)` (no #else/#endif closed it)."""
    depth_pc = 0
    stack = []
    for i, l in enumerate(text.split("\n")[:lineno]):
        s = l.strip()
        if s.startswith("#if"):
            stack.append("TARGET_PC" in s)
        elif s.startswith("#else") and stack:
            stack[-1] = False
        elif s.startswith("#endif") and stack:
            stack.pop()
    return any(stack)


class Guards(unittest.TestCase):
    def test_guards_only_under_target_pc(self):
        for f in ("src/melee/ty/toy.c", "src/melee/ty/tydisplay.c", "src/melee/ty/tyfigupon.c"):
            t = read(f)
            for n, l in lines_with(t, "Ui_RetailHidden"):
                self.assertTrue(inside_target_pc(t, n), "%s:%d: a guard outside TARGET_PC" % (f, n))

    def test_no_guard_inside_a_proc(self):
        for f in ("src/melee/ty/toy.c", "src/melee/ty/tydisplay.c", "src/melee/ty/tyfigupon.c"):
            t = read(f)
            procs = proc_names(t)
            self.assertTrue(procs, f + ": found no procs (the parser is stale)")
            bodies = function_bodies(t)
            for p in procs:
                key = p if p in bodies else "_" + p
                if key in bodies:
                    self.assertNotIn("Ui_RetailHidden", bodies[key], "%s: the proc %s must never read the mask" % (f, p))
                    self.assertNotRegex(bodies[key], r"->hidden\s*=\s*1", "%s: the proc %s must not hide anything" % (f, p))

    def test_nothing_to_hide_in_the_collection_and_the_lottery(self):
        # the room, the shelves, the machine, the coin digits and the popup are all retail 3D (or the popup's own text): no guard at all
        for f in ("src/melee/ty/tydisplay.c", "src/melee/ty/tyfigupon.c"):
            t = read(f)
            self.assertNotIn("Ui_RetailHidden", t, f)
            self.assertNotIn("TOY_PANEL_RENDER", t, f)
            self.assertNotRegex(t, r"->hidden\s*=\s*1;\n[^\n]*//?\s*atlas", f)
        # the Lottery's popup keeps its own text flag exactly as retail wrote it
        lot = read("src/melee/ty/tyfigupon.c")
        self.assertEqual(len(re.findall(r"->hidden = [01];", lot)), 3, "tyfigupon.c's own three writes of the popup's hidden flag (lines 360, 850, 1489 at the merge base) are unchanged")

    def test_gallery_guards_are_the_three_named_sites(self):
        t = read("src/melee/ty/toy.c")
        # the panel (link 0x3C, ToyFigurePanel) and the info frame (link 0x38, TyMnInfo): the render callback argument only
        self.assertEqual(len(re.findall(r"GObj_SetupGXLink\([^;]*TOY_PANEL_RENDER, 0x3C, 0\);", t)), 1)
        self.assertEqual(len(re.findall(r"GObj_SetupGXLink\([^;]*TOY_INFO_RENDER, 0x38, 0\);", t)), 1)
        self.assertEqual(len(re.findall(r"TOY_(?:PANEL|INFO)_RENDER", t)), 2 + 4, "two uses, plus the two #define pairs")
        # never the backdrop (0x33), the viewer (0x39), the background (0x32), the lights (0x34 to 0x37)
        for link in ("0x33", "0x39", "0x32", "0x35", "0x36", "0x37"):
            for m in re.finditer(r"GObj_SetupGXLink\(([^;]*), " + link + r", [^)]*\);", t):
                self.assertNotIn("_RENDER", m.group(1), "the retail 3D at link %s must not be guarded" % link)
        # the render wrappers call retail's own callback and nothing else
        bodies = function_bodies(t)
        self.assertRegex(bodies["Toy_RenderPanelGuarded"], r"Ui_RetailHidden\(AT_RE_TOY_PANEL\)\) return;\n\s*HSD_GObj_JObjCallback\(gobj, pass\);")
        self.assertRegex(bodies["Toy_RenderInfoGuarded"], r"Ui_RetailHidden\(AT_RE_TOY_INFO\)\) return;\n\s*HSD_SObjLib_803A49E0\(gobj, pass\);")

    def test_gallery_text_hiding_is_only_ever_set_to_one_under_the_mask(self):
        t = read("src/melee/ty/toy.c")
        writes = re.findall(r"(\w+(?:->\w+)*)->hidden\s*=\s*([^;]*);", t)
        self.assertEqual(len(writes), 4, "four text objects: x144, x148, x14C, x150")
        self.assertTrue(all(v.strip() == "1" for _, v in writes), "never written to 0 (retail's own flag is not overwritten)")
        n = lines_with(t, "->hidden = 1;")[0][0]
        window = "\n".join(t.split("\n")[max(0, n - 4):n])
        self.assertIn("Ui_RetailHidden(AT_RE_TOY_TEXT)", window)

    def test_readbacks_only_read(self):
        for f, fn in (("src/melee/ty/toy.c", "Toy_PcReadback"), ("src/melee/ty/tyfigupon.c", "tyFigupon_PcReadback")):
            t = read(f)
            b = function_bodies(t)[fn]
            stores = [l for l in b.split("\n") if re.search(r"(?:->|\.)\w+\s*(?:[-+|&]?=)[^=]", l) or re.search(r"\]\s*=[^=]", l) or re.search(r"\+\+|--", l)]
            self.assertEqual(stores, [], f + ": " + fn + " must only read (a local declaration is the only `=` allowed)")


if __name__ == "__main__":
    unittest.main()
