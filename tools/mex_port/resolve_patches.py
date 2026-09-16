#!/usr/bin/env python3
import argparse
import bisect
import collections
import glob
import os
import re
import sys

SYMBOL_RE = re.compile(
    r"^(\S+)\s*=\s*\.(\w+):0x([0-9A-Fa-f]+);\s*//\s*type:(\w+)\s*size:0x([0-9A-Fa-f]+)"
)
INSERT_AT_RE = re.compile(r"^\s*#\s*To be inserted\s+(?:at\s*|@\s*)(?:0x)?([0-9A-Fa-f]{5,8})", re.I)


def load_symbols(path):
    syms = []
    for line in open(path, errors="ignore"):
        m = SYMBOL_RE.match(line)
        if not m:
            continue
        name, section = m.group(1), m.group(2)
        addr, typ, size = int(m.group(3), 16), m.group(4), int(m.group(5), 16)
        if size > 0:
            syms.append((addr, addr + size, name, section, typ))
    syms.sort(key=lambda s: s[0])
    return syms


class Resolver:
    def __init__(self, syms, kinds):
        self.syms = [s for s in syms if s[4] in kinds]
        self.starts = [s[0] for s in self.syms]

    def resolve(self, addr):
        i = bisect.bisect_right(self.starts, addr) - 1
        if i < 0:
            return None
        start, end, name, section, typ = self.syms[i]
        return (name, section, typ) if start <= addr < end else None


def collect_patch_addresses(root):
    out = []
    for path in sorted(glob.glob(os.path.join(root, "asm", "**", "*.asm"), recursive=True)):
        addrs = []
        for line in open(path, errors="ignore"):
            m = INSERT_AT_RE.match(line)
            if m:
                addrs.append(int(m.group(1), 16))
        if addrs:
            out.append((os.path.relpath(path, root), addrs))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mex", required=True, help="path to the m-ex checkout")
    ap.add_argument("--symbols", required=True, help="path to config/GALE01/symbols.txt")
    ap.add_argument("--out", help="write the markdown report here")
    args = ap.parse_args()

    syms = load_symbols(args.symbols)
    funcs = Resolver(syms, {"function"})
    anything = Resolver(syms, {"function", "object", "label"})
    patches = collect_patch_addresses(args.mex)

    total = sum(len(a) for _, a in patches)
    res_f = res_a = 0
    per_cat = collections.Counter()
    per_cat_f = collections.Counter()
    hits = collections.Counter()
    unresolved = []

    lines = []

    def emit(s=""):
        lines.append(s)
        print(s)

    emit("# m-ex patch triage — insertion addresses resolved to decomp symbols")
    emit()
    emit(f"- m-ex checkout: `{args.mex}`")
    emit(f"- symbol table: `{args.symbols}` ({len(syms)} sized symbols)")
    emit(f"- `.asm` files scanned: {len(glob.glob(os.path.join(args.mex, 'asm', '**', '*.asm'), recursive=True))}")
    emit(f"- files with an `#To be inserted at <addr>` directive: {len(patches)}")
    emit(f"- insertion addresses: {total}")
    emit()

    for rel, addrs in patches:
        cat = "/".join(rel.split("/")[:2])
        for a in addrs:
            per_cat[cat] += 1
            f = funcs.resolve(a)
            if f:
                res_f += 1
                per_cat_f[cat] += 1
                hits[f[0]] += 1
            if not anything.resolve(a):
                unresolved.append((rel, a))

    emit(f"**Resolved to a decomp function: {res_f}/{total} "
         f"({100.0 * res_f / max(1, total):.1f}%)**")
    emit()
    emit("## By category")
    emit()
    emit("| inserted | resolved to a function | category |")
    emit("|---:|---:|---|")
    for cat, c in per_cat.most_common():
        emit(f"| {c} | {per_cat_f[cat]} | `{cat}` |")
    emit()
    emit("## Most-patched decomp functions")
    emit()
    emit("| patches | function |")
    emit("|---:|---|")
    for fn, c in hits.most_common(40):
        emit(f"| {c} | `{fn}` |")
    emit()
    emit("## Unresolved addresses")
    emit()
    if not unresolved:
        emit("None — every address lands inside a sized symbol.")
    else:
        emit("| address | patch |")
        emit("|---|---|")
        for rel, a in unresolved:
            emit(f"| `0x{a:08X}` | `{rel}` |")

    if args.out:
        with open(args.out, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\nwrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
