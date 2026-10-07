"""Lint the ONLINE PLAY rows' strings against what the Atlas explainer and row can show.

    python tools/port/check_atlas_online_text.py [path to gmfrontend.c]

A label must fit a list row beside a value widget (at most 18 characters). A help string is the explainer's WHAT: it must wrap
to at most 3 lines at 33 characters a line (the wide preset's 232 px at 7 px a character, the fake width the tests use; the real
font is a little narrower, so this is conservative). The explainer would clamp a longer one with an ellipsis, which is the
failure this catches before the owner sees it.
"""
import re
import sys

MAX_LABEL = 18
MAX_LINES = 3
LINE = 33


def table_text(src):
    a = src.index("static const FrontendItem fe_items_online[] = {")
    return src[a:src.index("};", a)]


def pairs(text):
    q = re.findall(r'"((?:[^"\\]|\\.)*)"', text)
    return [(q[i], q[i + 1]) for i in range(0, len(q) - 1, 2)]


def wrap_lines(s):
    lines, cur = 0, ""
    for word in s.split():
        while len(word) > LINE:
            if cur:
                lines, cur = lines + 1, ""
            lines, word = lines + 1, word[LINE:]
        if cur and len(cur) + 1 + len(word) > LINE:
            lines, cur = lines + 1, word
        else:
            cur = (cur + " " + word).strip()
    return lines + (1 if cur else 0)


def lint(ps):
    out = []
    for label, help_ in ps:
        if len(label) > MAX_LABEL:
            out.append('label "%s" is %d characters (at most %d)' % (label, len(label), MAX_LABEL))
        if wrap_lines(help_) > MAX_LINES:
            out.append('help of "%s" wraps to %d lines at %d characters (at most %d)' % (label, wrap_lines(help_), LINE, MAX_LINES))
    return out


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "melee/src/melee/gm/gmfrontend.c"
    findings = lint(pairs(table_text(open(path, encoding="utf-8").read())))
    for f in findings:
        print("FAIL:", f)
    print("check_atlas_online_text: %d finding(s)" % len(findings))
    sys.exit(1 if findings else 0)
