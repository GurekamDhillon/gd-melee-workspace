"""python tools/port/check_no_disc_text.py [--melee PATH]: decoded retail text must never reach a log or a file.

The Atlas data screens decode the disc's own words (event names, message bodies, sound names) at run time into a bounded buffer
(fad_sis_text in src/melee/gm/gmfrontend_atlas_data.inc, at_sis_decode in pc/platform/gw_ui_retailtext.c) and draw them. Nothing decoded
may be written to a log, a fixture or a file: the logs carry counts only. This fails when a line in the data adapter or the data units
passes a string to a log or file call (OSReport, gw_log, printf, fprintf, fwrite, fputs, puts) through %s unless the line says
/* OK-NOTEXT */ (it prints an authored screen id, never decoded text).
"""
import os
import re
import sys

FILES = [
    "src/melee/gm/gmfrontend_atlas_data.inc",
    "pc/platform/gw_ui_data.c",
    "pc/platform/gw_ui_data_models.c",
    "pc/platform/gw_ui_retailtext.c",
    "pc/platform/gw_ui_results.c",
    "pc/platform/gw_script_ui_data.inc",
]
SINKS = re.compile(r"\b(OSReport|gw_log|printf|fprintf|fwrite|fputs|puts)\s*\(")
# the argument text that looks like a decoded buffer: name, desc, msg, text, label, buf, txt, sub, body (and any %s at all in a log line)
TEXTY = re.compile(r"\b(name|desc|msg|text|label|buf|txt|sub|body|help)\w*\b")


def problems(root, files=FILES):
    out = []
    for rel in files:
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            continue
        for n, line in enumerate(open(p, encoding="utf-8", errors="replace").read().splitlines(), 1):
            if not SINKS.search(line) or "%s" not in line or "OK-NOTEXT" in line:
                continue
            args = line.split("(", 1)[1]
            fmt_end = args.find('"', args.find('"') + 1)
            tail = args[fmt_end + 1:] if fmt_end >= 0 else args
            if TEXTY.search(tail) or "%s" in args:
                out.append("%s:%d: a log call formats a string: %s" % (rel, n, line.strip()))
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
