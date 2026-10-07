"""check_qt_strings.py - the Qt launcher's t("English", "Spanish") pairs.

    python tools/release/launcher/check_qt_strings.py

The Qt window does not use Lang.cs (that is the C# reference launcher, checked by check_strings.py): it carries
each string inline as t("English", "Spanish"), and main.cpp picks the half. This is a lexical scan of qt/*.cpp
and qt/*.h, like check_strings.py. Strings are compared as written (escapes and all).

Problems (exit 1):
  - an empty English half;
  - the same English text with two different second halves (the lookup is by the English text);
  - %1, %2 ... placeholders that differ between the two halves.
Information only (never a failure, because new strings are written t("English", "English") by rule):
  - pairs whose halves are identical, listed as untranslated.
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIT = r'"((?:[^"\\]|\\.)*)"'
PAIR = re.compile(r'(?<![\w.>])t\(\s*' + LIT + r'\s*,\s*' + LIT + r'\s*\)')
PH = re.compile(r'%(\d+)')


def scan(directory):
    pairs, untranslated, problems, seen = 0, [], [], {}
    files = sorted(glob.glob(os.path.join(directory, "*.cpp")) + glob.glob(os.path.join(directory, "*.h")))
    for path in files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for m in PAIR.finditer(text):
            en, es = m.group(1), m.group(2)
            line = text.count("\n", 0, m.start()) + 1
            where = "%s:%d" % (os.path.basename(path), line)
            pairs += 1
            if not en.strip():
                problems.append('%s: empty English half' % where)
                continue
            if en == es:
                if en not in untranslated:
                    untranslated.append(en)
            if sorted(PH.findall(en)) != sorted(PH.findall(es)):
                problems.append('%s: placeholders differ: "%s"' % (where, en))
            if en in seen and seen[en][0] != es:
                problems.append('%s: "%s" has two second halves ("%s" at %s, "%s" here)' % (where, en, seen[en][0], seen[en][1], es))
            seen.setdefault(en, (es, where))
    return {"pairs": pairs, "untranslated": untranslated, "problems": problems, "files": len(files)}


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    directory = argv[1] if len(argv) > 1 else os.path.join(HERE, "qt")
    r = scan(directory)
    for p in r["problems"]:
        print("PROBLEM:", p)
    print("%d pairs, %d untranslated (identical halves), %d problem(s)" % (r["pairs"], len(r["untranslated"]), len(r["problems"])))
    return 1 if r["problems"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
