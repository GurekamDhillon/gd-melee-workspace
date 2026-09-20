#!/usr/bin/env python3
"""Audit engine functions that RETURN a pointer into one of the game's globals.

WHY THIS EXISTS
---------------
In this port the game's static globals live in the exe's `.data`, not in guest MEM1. The bridge
translates guest -> native at the point of ACCESS (`gw_ppc_static_native` in pc/platform/gw_ppc.c),
which covers interpreted code that names a static by its guest address. It cannot cover a pointer
that an engine function HANDS BACK: `grDatFiles_801C6330` ends `return &grDatFiles_8049EE10[i]`, so
the blob receives a host address in r3 and dereferences it. That faulted (`ea=0x107819A0`, Akaneia's
Gamecube stage) until the interpreter learned to accept an address that is already native.

This tool answers "how big is that class?" - i.e. how many bridge-reachable functions can return
such a pointer. It is a census, not a checker: the fix is general, so nothing here needs changing
per function. Re-run it when the decomp grows, to see whether the shape is still what we think.

CONFIDENCE TIERS (printed per row, and the reason this is not one number)
------------------------------------------------------------------------
  A  `return &X`, `return X[i]`, `return X + i`, `return &X.f`
     The ADDRESS of a global. Always a native pointer in this port. Certain.
  B  bare `return X;`
     Native only when X is an ARRAY (array-to-pointer decay, e.g. grDatFiles_GetArchive). When X
     is a scalar or a pointer VARIABLE this returns its value and is harmless - HSD_CObjGetCurrent
     is `return current;`, a heap CObj pointer, and is a false positive. Reported separately
     rather than guessed at; resolving it needs the declaration, not the return statement.

Usage:
  python tools/mex_port/audit_native_returns.py [--melee PATH] [--list]
"""
import argparse
import os
import re
import sys

SYMBOL_RE = re.compile(r"^\s*(\S+)\s*=\s*\.\S+:(0x[0-9A-Fa-f]+)\s*;.*?type:(\w+)")
BRIDGE_RE = re.compile(r"\{ 0x([0-9A-Fa-f]+)u, 0x([0-9A-Fa-f]+)u, (\d) \}")
# `return [&] NAME [ [ . ; + ] ]` - the delimiter is what separates tier A from tier B.
RETURN_RE = re.compile(r"^\s*return\s+(&?)\s*([A-Za-z_]\w*)\s*([\[\.;+]|$)")
# A function definition line. Deliberately loose; only used to attribute a return statement to the
# nearest preceding definition, and the result is cross-checked against symbols.txt.
FUNC_RE = re.compile(r"^[A-Za-z_][\w \t\*]*\b(\w+)\s*\(")
NOT_A_DEF = ("return", "if", "for", "while", "switch", "else", "do")


def parse_symbols(path):
    """-> (objects {name: addr}, functions {name: addr}), first listing of each name."""
    objects, functions = {}, {}
    for line in open(path, "r", encoding="utf-8", errors="replace"):
        m = SYMBOL_RE.match(line)
        if not m:
            continue
        name, addr, typ = m.group(1), int(m.group(2), 16), m.group(3)
        target = functions if typ == "function" else objects
        if name not in target:
            target[name] = addr
    return objects, functions


def bridged_object_addrs(path):
    """Guest addresses of the bridge table's DATA entries (kind 0)."""
    out = set()
    for line in open(path, "r", encoding="utf-8", errors="replace"):
        m = BRIDGE_RE.search(line)
        if m and m.group(3) == "0":
            out.add(int(m.group(1), 16))
    return out


def scan(src_root, melee, global_names, function_names):
    hits = []
    for root, _dirs, files in os.walk(src_root):
        for fn in files:
            if not fn.endswith(".c"):
                continue
            path = os.path.join(root, fn)
            enclosing = None
            for lineno, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
                fm = FUNC_RE.match(line)
                if fm and not line.lstrip().startswith(NOT_A_DEF):
                    enclosing = fm.group(1)
                rm = RETURN_RE.match(line)
                if rm is None or rm.group(2) not in global_names:
                    continue
                tier = "B" if (rm.group(1) == "" and rm.group(3) == ";") else "A"
                hits.append({
                    "path": os.path.relpath(path, melee).replace("\\", "/"),
                    "line": lineno,
                    "func": enclosing,
                    "global": rm.group(2),
                    "tier": tier,
                    "bridged": enclosing in function_names,
                })
    return hits


def main():
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap = argparse.ArgumentParser()
    ap.add_argument("--melee", default=os.environ.get("GW_MELEE", os.path.join(repo, "melee")))
    ap.add_argument("--list", action="store_true", help="print every site, not just the summary")
    args = ap.parse_args()

    symbols = os.path.join(args.melee, "config/GALE01/symbols.txt")
    bridge = os.path.join(args.melee, "pc/platform/gw_mex_bridge.c")
    objects, functions = parse_symbols(symbols)
    in_bridge = bridged_object_addrs(bridge)
    # Only globals the bridge actually carries: one that never reaches the interpreter cannot be
    # returned to it either.
    global_names = set(n for n, a in objects.items() if a in in_bridge)

    hits = scan(os.path.join(args.melee, "src"), args.melee, global_names, functions)
    bridged = [h for h in hits if h["bridged"]]
    fns_a = set(h["func"] for h in bridged if h["tier"] == "A")
    fns_b = set(h["func"] for h in bridged if h["tier"] == "B") - fns_a

    print("game globals carried by the bridge          : %d" % len(global_names))
    print("`return <global>` sites                     : %d" % len(hits))
    print("  ... in a function symbols.txt names       : %d" % len(bridged))
    print()
    print("BRIDGE-REACHABLE FUNCTIONS RETURNING A NATIVE POINTER")
    print("  tier A (certain: the address of a global) : %d" % len(fns_a))
    print("  tier B (bare `return X;`, needs the decl) : %d" % len(fns_b))
    print()
    by_area = {}
    for h in bridged:
        if h["tier"] != "A":
            continue
        area = h["path"].split("/")[2] if h["path"].startswith("src/melee/") else \
            h["path"].split("/")[1]
        by_area.setdefault(area, set()).add(h["func"])
    print("  tier A by subsystem:")
    for area, fns in sorted(by_area.items(), key=lambda kv: -len(kv[1])):
        print("    %-14s %d" % (area, len(fns)))

    if args.list:
        print()
        for h in sorted(bridged, key=lambda h: (h["path"], h["line"])):
            print("%s %-44s %-32s %s:%d" %
                  (h["tier"], (h["func"] or "?") + "()", h["global"], h["path"], h["line"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
