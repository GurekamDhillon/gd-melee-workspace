#!/usr/bin/env python3
"""Check that every ported m-ex behaviour follows the fork's conventions.

m-ex behaviours are gated behind Mex_Enabled("<name>") under `#if defined(TARGET_PC)`, with an
attribution comment naming the upstream patch. With hundreds of ports landing from multiple
contributors, "did anyone skip the guard or the attribution?" is otherwise unanswerable by reading
128 diffs. This checks it mechanically.

A violation is one of:
  - a Mex_Enabled() call site with no `#if defined(TARGET_PC)` anywhere earlier in the file
  - a Mex_Enabled() call site with no attribution comment within LOOKBACK lines above it
  - a Mex_Enabled() call site with no m-ex URL in that comment

Exit code is the number of violations (0 = clean).
"""

import argparse
import os
import re
import sys

CALL_RE = re.compile(r'Mex_Enabled\s*\(\s*"([^"]+)"')
GUARD_RE = re.compile(r"#\s*if\s+defined\s*\(\s*TARGET_PC\s*\)")
LOOKBACK = 20


def scan(path):
    violations = []
    try:
        lines = open(path, errors="ignore").read().splitlines()
    except OSError:
        return violations
    guard_seen = False
    for i, line in enumerate(lines):
        if GUARD_RE.search(line):
            guard_seen = True
        m = CALL_RE.search(line)
        if not m:
            continue
        name = m.group(1)
        if not guard_seen:
            violations.append((path, i + 1, name, "no TARGET_PC guard earlier in file"))
        window = "\n".join(lines[max(0, i - LOOKBACK):i])
        if "m-ex" not in window:
            violations.append((path, i + 1, name, "no attribution comment within %d lines" % LOOKBACK))
        elif "github.com/akaneia/m-ex" not in window:
            violations.append((path, i + 1, name, "attribution does not cite the m-ex URL"))
    return violations


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default="src/melee", help="tree to scan (default src/melee)")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print("not a directory: %s" % args.root, file=sys.stderr)
        return 1

    all_v = []
    sites = 0
    names = {}
    for dirpath, _dirnames, filenames in os.walk(args.root):
        for fn in filenames:
            if not fn.endswith(".c"):
                continue
            path = os.path.join(dirpath, fn)
            found = scan(path)
            text = open(path, errors="ignore").read()
            sites += len(CALL_RE.findall(text))
            all_v.extend(found)
            for name in CALL_RE.findall(text):
                names.setdefault(name, []).append(path)

    for name, paths in sorted(names.items()):
        if len(set(paths)) > 1:
            all_v.append((", ".join(sorted(set(paths))), 0, name,
                          "feature name used in %d files - flags must be unique or unrelated "
                          "behaviours toggle together" % len(set(paths))))

    for path, line, name, why in all_v:
        print("VIOLATION %s:%d  Mex_Enabled(\"%s\") - %s" % (path, line, name, why))
    print("----------------------------------------")
    print("checked %d Mex_Enabled call site(s), %d violation(s)" % (sites, len(all_v)))
    return len(all_v)


if __name__ == "__main__":
    sys.exit(main())
