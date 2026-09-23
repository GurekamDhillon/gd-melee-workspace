"""check_strings.py - the launcher's string table (Lang.cs) against its sources.

    python tools/release/launcher/check_strings.py

Every L.T("..."), L.F("...") and L.N("...") key in the .cs files must have a Spanish entry in
Lang.cs with the same {n} placeholders; no key may be listed twice (a duplicate throws when the
table loads). Keys are compared as written in the C# source (escapes and all). Exit code 1 on a
problem; unused Spanish entries are only listed.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIT = r'"((?:[^"\\]|\\.)*)"'
USE = re.compile(r'\bL\.(?:T|F|N)\(\s*' + LIT)
USE_INSIDE = re.compile(r'(?<![\w.])(?:T|N)\(\s*' + LIT)  # T("...") / N("...") inside Lang.cs itself
ENTRY = re.compile(r'\{\s*' + LIT + r'\s*,\s*' + LIT + r'\s*\}', re.S)
PH = re.compile(r'\{(\d+)(?:[:,][^}]*)?\}')


def main():
    used = {}
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".cs"):
            continue
        text = open(os.path.join(HERE, name), encoding="utf-8").read()
        if name == "Lang.cs":
            head = text[:text.index("static readonly Dictionary")]
            for m in USE_INSIDE.finditer(head):
                used.setdefault(m.group(1), name)
            table = text[text.index("static readonly Dictionary"):]
        for m in USE.finditer(text):
            used.setdefault(m.group(1), name)
    entries = ENTRY.findall(table)
    bad = 0
    seen = set()
    for k, v in entries:
        if k in seen:
            print("DUPLICATE key: %s" % k)
            bad += 1
        seen.add(k)
        if sorted(set(PH.findall(k))) != sorted(set(PH.findall(v))):
            print("PLACEHOLDERS differ: %s  ->  %s" % (k, v))
            bad += 1
    for k, where in sorted(used.items()):
        if k not in seen:
            print("MISSING Spanish for (%s): %s" % (where, k))
            bad += 1
    unused = [k for k in seen if k not in used]
    for k in sorted(unused):
        print("unused entry: %s" % k)
    print("%d keys used, %d entries, %d problem(s)" % (len(used), len(entries), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
