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
