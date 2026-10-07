"""python tools/port/check_no_disc_text.py [--melee PATH]: decoded retail text must never reach a log or a file.

The Atlas data screens decode the disc's own words (event names and descriptions, message bodies, sound names, bonus lines) at run time into a bounded
buffer (fad_sis_text in src/melee/gm/gmfrontend_atlas_data.inc, at_sis_decode in pc/platform/gw_ui_retailtext.c) and draw them. Nothing decoded may be
written to a log, a fixture or a file: the logs carry counts only. This reads every call to a log or file function (OSReport, gw_log, printf, fprintf, fwrite,
fputs, puts) as a whole STATEMENT, however many lines it spans and however its format string is wrapped, and fails when its arguments could carry a string: a
%s anywhere in the format, or a buffer-like name among the arguments. A statement that prints an authored screen id or a count says so with /* OK-NOTEXT */
anywhere in it. The files covered are every Atlas adapter and door that touches the text: gmfrontend_atlas*.inc, gw_script_ui_set.inc, gw_script_ui_data.inc and
the pure data units.
"""
import glob
import os
import re
import sys

FILES = [
    "src/melee/gm/gmfrontend_atlas.inc",
    "src/melee/gm/gmfrontend_atlas_data.inc",
    "src/melee/gm/gmfrontend_atlas_online.inc",
    "src/melee/gm/gmfrontend_atlas_select.inc",
    "src/melee/gm/gmfrontend_atlas_set.inc",
    "pc/platform/gw_script_ui_set.inc",
    "pc/platform/gw_script_ui_data.inc",
    "pc/platform/gw_ui_data.c",
    "pc/platform/gw_ui_data_models.c",
    "pc/platform/gw_ui_retailtext.c",
    "pc/platform/gw_ui_results.c",
]
SINKS = re.compile(r"\b(OSReport|gw_log|printf|fprintf|fwrite|fputs|puts)\s*\(")
# an argument that looks like a decoded buffer
TEXTY = re.compile(r"\b(name|desc|msg|text|label|buf|txt|sub|body|help|out)\w*\b")


def statements(text):
    """(line number, statement text) for each sink call, the span of its balanced parentheses plus the rest of the comment on its last line."""
    for m in SINKS.finditer(text):
        i = m.end()
        depth, j, instr = 1, i, False
        while j < len(text) and depth > 0:
            c = text[j]
            if instr:
                if c == "\\":
                    j += 1
                elif c == '"':
                    instr = False
            elif c == '"':
                instr = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            j += 1
        end = text.find("\n", j)
        yield text.count("\n", 0, m.start()) + 1, text[m.start():(end if end >= 0 else len(text))]


def strip_literals(call):
    """the call with each string literal folded away (adjacent literals are one format), keeping the %s count and the arguments."""
    fmt = "".join(re.findall(r'"((?:\\.|[^"\\])*)"', call))
    args = re.sub(r'"(?:\\.|[^"\\])*"', '""', call)
    return fmt, args


def problems(root, files=None):
    out = []
    for rel in files if files is not None else FILES:
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            text = f.read()
        for n, stmt in statements(text):
            if "OK-NOTEXT" in stmt:
                continue
            fmt, args = strip_literals(stmt)
            head = args.split("(", 1)[1] if "(" in args else args
            if "%s" in fmt or TEXTY.search(head):
                out.append("%s:%d: a log call could print a string: %s" % (rel, n, " ".join(stmt.split())[:140]))
    return out


def main(argv):
    root = os.environ.get("GW_MELEE", "")
    if "--melee" in argv:
        root = argv[argv.index("--melee") + 1]
    bad = problems(root)
    for b in bad:
        print(b)
    print("check_no_disc_text: %d problem(s)" % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
