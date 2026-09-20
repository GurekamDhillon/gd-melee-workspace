#!/usr/bin/env python3
"""Generate the guest->native bridge table for the PPC blob interpreter.

Pairs `melee/config/GALE01/symbols.txt` (guest address -> decomp symbol name) with
`_build/melee-pc.map` (gw_<name> -> native VA) so the interpreter can resolve an absolute
guest address (a `bl`/`bctrl` target or a static global) to its native `gw_` counterpart.

Output: `pc/platform/gw_mex_bridge.c` + `.h` (checked in). Each entry is {guest, native, kind}
sorted by guest address; the runtime binary-searches it. Re-run after the game relinks (the map
changes): `python3 tools/mex_port/gen_bridge.py`.

Usage: gen_bridge.py [--symbols PATH] [--map PATH]
"""
import argparse
import os
import re
import sys

# `scope:` is OPTIONAL: 1454 symbols.txt lines carry only `type:`/`size:`, and requiring scope
# silently dropped every one of them (guest 0x8003E998 among them, which Diddy calls).
SYMBOL_RE = re.compile(
    r"^\s*(?P<name>\S+)\s*=\s*\.\S+:(?P<addr>0x[0-9A-Fa-f]+)\s*;"
    r".*?type:(?P<typ>\w+)"
)
SCOPE_RE = re.compile(r"scope:(?P<scope>\w+)")
# `size:` gives an object's extent. It is what makes an INTERIOR pointer resolvable: an engine
# accessor returns `&global[i]`, not `&global`, so an exact-base reverse lookup misses for every
# i != 0 and - worse - succeeds for i == 0, which is the kind of half-working that hides a bug.
SIZE_RE = re.compile(r"size:(?P<size>0x[0-9A-Fa-f]+)")
# MWERKS mangling: `sqrtf__Ff`, `func__FPi` ... The port's C symbol is the bare name.
MANGLE_RE = re.compile(r"^(?P<base>[A-Za-z_][A-Za-z0-9_]*)__F[A-Za-z0-9_]*$")
# melee-pc.map public-symbol line: " 0001:00309e40       _gw_OSReport_PrintSpaces   1030ae40 f  obj"
# (data-section lines have no `f`/`d` type letter, so it is optional)
MAP_RE = re.compile(
    r"^\s*[0-9A-Fa-f]{4}:[0-9A-Fa-f]{8}\s+"
    r"(?P<name>_[A-Za-z0-9_$@?.]+)\s+"
    r"(?P<addr>[0-9A-Fa-f]{8})\b"
)


def parse_symbols(path):
    out = {}  # name -> (addr, kind, scope, size)
    for line in open(path, "r", encoding="utf-8", errors="replace"):
        m = SYMBOL_RE.match(line)
        if not m:
            continue
        name = m.group("name")
        addr = int(m.group("addr"), 16)
        typ = m.group("typ")
        sm = SCOPE_RE.search(line)
        scope = sm.group("scope") if sm else "global"
        zm = SIZE_RE.search(line)
        size = int(zm.group("size"), 16) if zm else 0
        # A decomp symbol may be listed more than once (per section); keep the first.
        if name not in out:
            out[name] = (addr, typ, scope, size)
    return out


def parse_map(path):
    """-> (public {gw_name: addr}, statics {name: addr or None}).

    MSVC's map has a "Static symbols" section after the public one. Internal-linkage functions
    appear there under their PLAIN C name (gwtool only prefixes externally visible symbols), so
    it is the only place a `scope:local` decomp symbol can be found. A name that occurs more
    than once there is ambiguous (two TUs, two different functions) and is recorded as None so
    it is never paired.
    """
    public, statics = {}, {}
    in_static = False
    for line in open(path, "r", encoding="utf-8", errors="replace"):
        if line.strip() == "Static symbols":
            in_static = True
            continue
        m = MAP_RE.match(line)
        if not m:
            continue
        name = m.group("name")
        addr = int(m.group("addr"), 16)
        # MSVC prefixes a leading underscore; strip it to get the C symbol name.
        if name.startswith("_"):
            name = name[1:]
        if in_static:
            statics[name] = None if name in statics else addr
        elif name not in public:
            public[name] = addr
    return public, statics


def main():
    ap = argparse.ArgumentParser()
    # Derive the repo root from this script's location (tools/mex_port/gen_bridge.py) so the
    # generator works from WSL, Git Bash and cmd alike; a hardcoded /mnt/c path did not.
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--symbols", default=os.path.join(repo, "melee/config/GALE01/symbols.txt"))
    ap.add_argument("--map", default=os.path.join(repo, "_build/melee-pc.map"))
    ap.add_argument("--out-c", default=os.path.join(repo, "melee/pc/platform/gw_mex_bridge.c"))
    ap.add_argument("--out-h", default=os.path.join(repo, "melee/pc/platform/gw_mex_bridge.h"))
    args = ap.parse_args()

    syms = parse_symbols(args.symbols)
    mp, statics = parse_map(args.map)

    entries = []  # (guest, native, kind)
    n_demangled = n_static = 0
    for name, (guest, typ, scope, size) in syms.items():
        native = mp.get("gw_" + name)
        if native is None:
            # MWERKS-mangled decomp name -> the port's plain C name (sqrtf__Ff -> gw_sqrtf).
            mm = MANGLE_RE.match(name)
            if mm is not None:
                native = mp.get("gw_" + mm.group("base"))
                if native is not None:
                    n_demangled += 1
        if native is None:
            # Static in the port: no gw_ public symbol, but the map's static section has it under
            # its plain name. `scope:` in symbols.txt is not a reliable predictor - the port makes
            # its own linkage decisions (grLast_8021B2D8 is scope:global there and static here),
            # so the static section is consulted whenever the public lookup fails. Only when that
            # name is unambiguous. This can only ADD entries for
            # addresses that previously resolved to nothing, so it cannot change a call that
            # already worked.
            native = statics.get(name)
            if native is not None:
                n_static += 1
        if native is None:
            continue
        kind = "fn" if typ == "function" else "obj"
        entries.append((guest, native, kind, size))

    entries.sort(key=lambda e: e[0])
    fn_count = sum(1 for e in entries if e[2] == "fn")
    obj_count = sum(1 for e in entries if e[2] == "obj")

    # --- the native extents of the game's globals --------------------------------------------
    # The reverse of the table above, and the answer to a different question: "is this NATIVE
    # address one of the game's globals?" An engine function bridged out of interpreted code can
    # RETURN a pointer to one (grDatFiles_801C6330 ends `return &grDatFiles_8049EE10[i]`), and
    # that pointer is a host address - the globals live in this exe's .data, not in MEM1. The
    # interpreter has to recognise it wherever it later turns up, which is by range, not by base.
    #
    # Ranges come from symbols.txt's own `size:`, merged into disjoint runs. Nothing is guessed:
    # an object with no recorded size is LEFT OUT (a dereference of it still faults cleanly, which
    # is the honest failure) and counted in the summary.
    runs, no_size = [], []
    for guest, native, kind, size in entries:
        if kind != "obj":
            continue
        if size <= 0:
            no_size.append((guest, native))
            continue
        runs.append((native, native + size))
    runs.sort()
    merged = []
    for lo, hi in runs:
        if merged and lo <= merged[-1][1]:
            if hi > merged[-1][1]:
                merged[-1][1] = hi
        else:
            merged.append([lo, hi])
    covered = sum(h - l for l, h in merged)

    # Emit a header + a C file with the packed sorted table.
    hdr = """/* gw_mex_bridge.h - guest->native bridge table for the PPC blob interpreter.
 *
 * GENERATED by tools/mex_port/gen_bridge.py - do not edit by hand. Pairs symbols.txt guest
 * addresses with melee-pc.map gw_ native VAs, so the interpreter resolves absolute guest
 * addresses (bl/bctrl targets and static globals) to the port's native `gw_` code/data.
 */
#ifndef GW_MEX_BRIDGE_H
#define GW_MEX_BRIDGE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Look up a guest address. Returns the native VA, or 0 when there is no bridge entry. `kind`
 * is set to 1 for a function, 0 for a data object (may be NULL). */
uint32_t gw_mex_bridge_lookup(uint32_t guest_addr, int *kind);

/* Number of entries (for tests/diagnostics). */
uint32_t gw_mex_bridge_count(void);

/* The reverse question, by RANGE: does [native_addr, native_addr + size) lie wholly inside one of
 * the game's globals as this exe lays them out? A bridged engine function can RETURN a pointer to
 * a global (grDatFiles_801C6330 ends `return &grDatFiles_8049EE10[i]`), and that pointer is a host
 * address, because the game's globals live in the exe's .data rather than in MEM1. Interpreted
 * code then dereferences it - possibly long after, out of a field it was stored in - so the
 * interpreter must recognise such an address on the ordinary load/store path.
 *
 * By range and not by base: `&global[i]` is interior for every i != 0, so an exact-base lookup
 * would miss those and succeed only for i == 0. */
int gw_mex_bridge_is_native_data(uint32_t native_addr, uint32_t size);

#ifdef __cplusplus
}
#endif
#endif /* GW_MEX_BRIDGE_H */
"""
    with open(args.out_h, "w") as f:
        f.write(hdr)

    c_src = []
    c_src.append("/* gw_mex_bridge.c - GENERATED by tools/mex_port/gen_bridge.py - do not edit. */\n")
    c_src.append('#include "gw_mex_bridge.h"\n')
    c_src.append("#include <stddef.h>\n\n")
    c_src.append("typedef struct gw_mex_bridge_entry {\n")
    c_src.append("    uint32_t guest;\n")
    c_src.append("    uint32_t native;\n")
    c_src.append("    uint8_t  kind; /* 1 = function, 0 = data object */\n")
    c_src.append("} gw_mex_bridge_entry;\n\n")
    c_src.append("static const gw_mex_bridge_entry gw_mex_bridge_table[] = {\n")
    for guest, native, kind, _size in entries:
        k = 1 if kind == "fn" else 0
        c_src.append("    { 0x%08Xu, 0x%08Xu, %d },\n" % (guest, native, k))
    c_src.append("};\n\n")
    c_src.append("uint32_t gw_mex_bridge_count(void)\n")
    c_src.append("{\n")
    c_src.append("    return (uint32_t)(sizeof gw_mex_bridge_table / sizeof gw_mex_bridge_table[0]);\n")
    c_src.append("}\n\n")
    c_src.append("uint32_t gw_mex_bridge_lookup(uint32_t guest_addr, int *kind)\n")
    c_src.append("{\n")
    c_src.append("    uint32_t lo = 0;\n")
    c_src.append("    uint32_t hi = gw_mex_bridge_count();\n")
    c_src.append("    if (kind != NULL) { *kind = 0; }\n")
    c_src.append("    while (lo < hi) {\n")
    c_src.append("        uint32_t mid = lo + (hi - lo) / 2;\n")
    c_src.append("        uint32_t g = gw_mex_bridge_table[mid].guest;\n")
    c_src.append("        if (g == guest_addr) {\n")
    c_src.append("            if (kind != NULL) { *kind = gw_mex_bridge_table[mid].kind; }\n")
    c_src.append("            return gw_mex_bridge_table[mid].native;\n")
    c_src.append("        }\n")
    c_src.append("        if (g < guest_addr) { lo = mid + 1; } else { hi = mid; }\n")
    c_src.append("    }\n")
    c_src.append("    return 0;\n")
    c_src.append("}\n\n")

    c_src.append("/* Native extents of the game's globals, disjoint and sorted: [lo, hi) of each\n")
    c_src.append(" * data object's storage in THIS exe's .data. %d runs, %d bytes, from\n"
                 % (len(merged), covered))
    c_src.append(" * symbols.txt's own size: fields. %d object(s) had no recorded size and are\n"
                 % len(no_size))
    c_src.append(" * deliberately absent - dereferencing one still faults, which is honest. */\n")
    c_src.append("typedef struct gw_mex_bridge_run {\n")
    c_src.append("    uint32_t lo;\n")
    c_src.append("    uint32_t hi;\n")
    c_src.append("} gw_mex_bridge_run;\n\n")
    c_src.append("static const gw_mex_bridge_run gw_mex_bridge_native_data[] = {\n")
    for lo, hi in merged:
        c_src.append("    { 0x%08Xu, 0x%08Xu },\n" % (lo, hi))
    c_src.append("};\n\n")
    c_src.append("int gw_mex_bridge_is_native_data(uint32_t native_addr, uint32_t size)\n")
    c_src.append("{\n")
    c_src.append("    uint32_t lo = 0;\n")
    c_src.append("    uint32_t hi = (uint32_t)(sizeof gw_mex_bridge_native_data /\n")
    c_src.append("                            sizeof gw_mex_bridge_native_data[0]);\n")
    c_src.append("    /* Cheap reject first: almost every address asked about is a guest one. */\n")
    c_src.append("    if (native_addr < 0x%08Xu || native_addr >= 0x%08Xu) {\n"
                 % (merged[0][0], merged[-1][1]))
    c_src.append("        return 0;\n")
    c_src.append("    }\n")
    c_src.append("    while (lo < hi) {\n")
    c_src.append("        uint32_t mid = lo + (hi - lo) / 2;\n")
    c_src.append("        if (native_addr >= gw_mex_bridge_native_data[mid].hi) {\n")
    c_src.append("            lo = mid + 1;\n")
    c_src.append("        } else if (native_addr < gw_mex_bridge_native_data[mid].lo) {\n")
    c_src.append("            hi = mid;\n")
    c_src.append("        } else {\n")
    c_src.append("            /* The whole access must stay inside the run, so a multi-byte load\n")
    c_src.append("             * cannot walk off the end of a global into whatever follows it. */\n")
    c_src.append("            return (uint64_t)native_addr + size <=\n")
    c_src.append("                   (uint64_t)gw_mex_bridge_native_data[mid].hi;\n")
    c_src.append("        }\n")
    c_src.append("    }\n")
    c_src.append("    return 0;\n")
    c_src.append("}\n")

    with open(args.out_c, "w") as f:
        f.write("".join(c_src))

    print("bridge: +%d demangled, +%d static-section" % (n_demangled, n_static))
    print("bridge: %d entries (%d functions, %d objects) -> %s" %
          (len(entries), fn_count, obj_count, args.out_c))
    print("bridge: native game-global extents: %d runs, %d bytes, %d object(s) with no size" %
          (len(merged), covered, len(no_size)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
