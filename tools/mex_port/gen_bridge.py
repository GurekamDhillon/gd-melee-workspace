#!/usr/bin/env python3
"""Generate the guest->native bridge table for the PPC blob interpreter.

Pairs `melee/config/GALE01/symbols.txt` (guest address -> decomp symbol name) with
`_build/melee-pc.map` (gw_<name> -> native VA) so the interpreter can resolve an absolute
guest address (a `bl`/`bctrl` target or a static global) to its native `gw_` counterpart.

Output: `pc/platform/gw_mex_bridge.c` + `.h` (checked in). Each entry is {guest, native, kind}
sorted by guest address; the runtime binary-searches it. Re-run after the game relinks (the map
changes): `python3 tools/mex_port/gen_bridge.py`.

`melee/config/GALE01/splits.txt` is the third input: it says which source file owns a guest
address, which is the only way to tell apart the many decomp statics that SHARE A NAME across
TUs (`stageGObj0_OnInit` is `static` in 44 stage files). Address -> owning source file ->
`src_..._<file>.c.obj` -> the one map entry from that object.

Usage: gen_bridge.py [--symbols PATH] [--splits PATH] [--map PATH]
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
    # The trailing columns are an optional type letter or two ("f", "f i") and then the object
    # file the symbol came from. That last column is what tells two same-named statics apart,
    # so it is captured rather than ignored.
    r"(?:(?:\s+[a-z])*\s+(?P<obj>\S+))?\s*$"
)
# A splits.txt stanza: `melee/gr/grtseak.c:` followed by indented `<section> start:0x.. end:0x..`
SPLIT_FILE_RE = re.compile(r"^(?P<path>\S[^\s:]*\.(?:c|cpp))\s*:\s*$")
# A function-local static in symbols.txt: MWCC names `static HSD_TevDesc tev` inside a function
# `tev$297`. clang names the same object `<function>.tev`, which is how it appears in the map.
LOCAL_STATIC_RE = re.compile(r"^(?P<var>[A-Za-z_][A-Za-z0-9_]*)\$\d+$")
SPLIT_RANGE_RE = re.compile(
    r"^\s+\S+\s+start:(?P<start>0x[0-9A-Fa-f]+)\s+end:(?P<end>0x[0-9A-Fa-f]+)"
)


def parse_symbols(path):
    """-> {name: [(addr, kind, scope, size), ...]}, one entry per DISTINCT guest address.

    A name is not unique in symbols.txt. `stageGObj0_OnInit` is `static` in 44 different stage
    TUs and so appears at 44 guest addresses, all of them real, all of them different functions.
    This used to keep only the first, which silently threw away 377 guest addresses before the
    map was ever consulted - so no amount of map-side cleverness could have bridged them.
    (The first-only rule was aimed at a symbol LISTED TWICE FOR ONE ADDRESS, per section; that
    case is still collapsed, by address.)
    """
    out = {}  # name -> [(addr, kind, scope, size), ...]
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
        occs = out.setdefault(name, [])
        if not any(o[0] == addr for o in occs):
            occs.append((addr, typ, scope, size))
    return out


def parse_map(path):
    """-> (public {gw_name: addr}, statics {name: [(addr, obj), ...]}).

    MSVC's map has a "Static symbols" section after the public one. Internal-linkage functions
    appear there under their PLAIN C name (gwtool only prefixes externally visible symbols), so
    it is the only place a `scope:local` decomp symbol can be found. A name that occurs more
    than once there is ambiguous BY NAME (two TUs, two different functions), so every
    occurrence is kept along with the object file it came from and resolve_static() below picks
    between them using the guest address's owning source file.
    """
    public, statics, public_objs = {}, {}, {}
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
            statics.setdefault(name, []).append((addr, m.group("obj") or ""))
        else:
            # Kept with its object as well: gwtool exports SOME same-named statics publicly (one
            # of the seven `doEnter`s is `gw_doEnter`), so the public section holds candidates
            # the object-file match has to be able to choose from too.
            public_objs.setdefault(name, []).append((addr, m.group("obj") or ""))
            if name not in public:
                public[name] = addr
    return public, statics, public_objs


def parse_splits(path):
    """-> a sorted list of (start, end, obj_stem), one per section of each source file.

    melee/config/GALE01/splits.txt records, for every decomp TU, the guest address range it owns
    in each section. That is the disambiguator the map alone cannot supply: a guest address falls
    in exactly one file's .text (or .data, .bss, ...), and the link turns that file into exactly
    one object - `melee/gr/grtseak.c` -> `src_melee_gr_grtseak.c.obj`.

    That transform is checked against the real map rather than assumed: 973 of the 1126 stanzas
    name an object melee-pc.map actually contains. The other 153 are MSL/Runtime/SDK files the
    port shims natively instead of building, so they have no object and simply never match.
    """
    ranges = []
    stem = None
    for line in open(path, "r", encoding="utf-8", errors="replace"):
        m = SPLIT_FILE_RE.match(line)
        if m:
            stem = "src_" + m.group("path").replace("/", "_") + ".obj"
            continue
        if stem is None:
            continue
        m = SPLIT_RANGE_RE.match(line)
        if m:
            ranges.append((int(m.group("start"), 16), int(m.group("end"), 16), stem))
        elif not line.strip():
            stem = None
    ranges.sort()
    return ranges


def owning_obj(ranges, guest):
    """The .obj stem of the source file whose splits.txt range contains `guest`, or None."""
    lo, hi = 0, len(ranges)
    while lo < hi:
        mid = (lo + hi) // 2
        if ranges[mid][0] > guest:
            hi = mid
        else:
            lo = mid + 1
    if lo == 0:
        return None
    start, end, stem = ranges[lo - 1]
    return stem if start <= guest < end else None


def resolve_static(statics, ranges, name, guest, strict=False, extra=()):
    """-> (native addr, was_disambiguated) for a `static` in the port, or (None, False).

    A single occurrence of the name in the map's static section is unambiguous and is taken as
    is; that is the long-standing path and it is unchanged. SEVERAL occurrences used to be
    dropped outright, because a name shared by five TUs names five different functions and
    nothing in the map alone says which one a guest address means. splits.txt does say: the
    address belongs to one source file, that file becomes one object, and the map names each
    candidate's object. When exactly one candidate came from the owning object, that is the
    function - no guessing. When none or more than one does, it stays dropped, which remains
    the honest answer for a static that really is unresolvable.

    `strict` demands the object match even when there is only one candidate. It is used when the
    GUEST side is ambiguous too - when symbols.txt gives the same name to several addresses -
    because then "the only static with this name" is not evidence that it is THIS address's.
    """
    cands = statics.get(name) or []
    if len(cands) == 1 and not strict:
        return cands[0][0], False
    cands = cands + list(extra)
    if not cands:
        return None, False
    stem = owning_obj(ranges, guest)
    if stem is None:
        return None, False
    hits = [a for a, obj in cands if obj == stem]
    if len(hits) != 1:
        return None, False
    return hits[0], True


def main():
    ap = argparse.ArgumentParser()
    # Derive the repo root from this script's location (tools/mex_port/gen_bridge.py) so the
    # generator works from WSL, Git Bash and cmd alike; a hardcoded /mnt/c path did not.
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--symbols", default=os.path.join(repo, "melee/config/GALE01/symbols.txt"))
    ap.add_argument("--splits", default=os.path.join(repo, "melee/config/GALE01/splits.txt"))
    ap.add_argument("--map", default=os.path.join(repo, "_build/melee-pc.map"))
    ap.add_argument("--out-c", default=os.path.join(repo, "melee/pc/platform/gw_mex_bridge.c"))
    ap.add_argument("--out-h", default=os.path.join(repo, "melee/pc/platform/gw_mex_bridge.h"))
    args = ap.parse_args()

    syms = parse_symbols(args.symbols)
    mp, statics, mp_objs = parse_map(args.map)
    ranges = parse_splits(args.splits)

    # Function-local statics by (object, variable name). The two compilers disagree on the
    # function part of the name (MWCC keeps none, only a counter), so the pairing is: the object
    # splits.txt says owns the guest address, and the one `*.<var>` in it. GrSp.dat (ext:307)
    # passes `tev$297` - HSD_ShadowStartRender's TEV descriptor - to HSD_SetupTevStageAll, and
    # with no entry the native side read MEM1 at the guest address instead of the static.
    local_by_obj = {}
    for nm, occs2 in list(statics.items()) + list(mp_objs.items()):
        if "." not in nm:
            continue
        var = nm.rsplit(".", 1)[1]
        for a, obj in occs2:
            local_by_obj.setdefault((obj, var), set()).add(a)

    entries = []  # (guest, native, kind)
    n_demangled = n_static = n_split = n_local = 0
    for name, occs in syms.items():
        # Several guest addresses sharing one name are several different statics. A name-based
        # lookup - public OR single-candidate static - cannot be right for more than one of
        # them, so those are resolved ONLY through the object file splits.txt names.
        multi = len(occs) > 1
        for guest, typ, scope, size in occs:
            native = None if multi else mp.get("gw_" + name)
            if native is None and not multi:
                # MWERKS-mangled decomp name -> the port's plain C name (sqrtf__Ff -> gw_sqrtf).
                mm = MANGLE_RE.match(name)
                if mm is not None:
                    native = mp.get("gw_" + mm.group("base"))
                    if native is not None:
                        n_demangled += 1
            if native is None:
                # Static in the port: no gw_ public symbol, but the map's static section has it
                # under its plain name. `scope:` in symbols.txt is not a reliable predictor - the
                # port makes its own linkage decisions (grLast_8021B2D8 is scope:global there and
                # static here), so the static section is consulted whenever the public lookup
                # fails. Unambiguous by name, or else pinned to one object by splits.txt.
                native, by_split = resolve_static(
                    statics, ranges, name, guest, strict=multi,
                    extra=(mp_objs.get("gw_" + name, []) if multi else ()))
                if native is not None:
                    n_static += 1
                    if by_split:
                        n_split += 1
            if native is None:
                lm = LOCAL_STATIC_RE.match(name)
                if lm is not None:
                    hits = local_by_obj.get((owning_obj(ranges, guest), lm.group("var")), set())
                    if len(hits) == 1:
                        native = next(iter(hits))
                        n_local += 1
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

/* The forward question by RANGE: for a GUEST address that may be interior to one of the game's
 * globals, the native address of that same byte, or 0. The exact-base lookup above misses
 * `global[i]` for every i != 0, which made the interpreter read MEM1 instead of this exe's
 * .data - silently, and wrongly, on every interior access. */
uint32_t gw_mex_bridge_guest_data(uint32_t guest_addr);

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
    # --- the GUEST extents of the same objects ------------------------------------------------
    # The forward direction has the identical interior-pointer problem the native side documents,
    # and until now had only an exact-base lookup. An interpreted `lwz rD, 0x34(rA)` where rA is a
    # bridged global computes guest base+0x34, which missed the exact match and fell through to
    # MEM1 - where the object is NOT, because the game's statics live in this exe's .data. That is
    # a silent wrong read on every interior access to a global, and it surfaced as branches to
    # addresses inside data objects (gmResultCharacterData +0x20 and +0x34 both turned up as
    # "resolver returned NULL for guest address ...").
    gruns = []
    for guest, native, kind, size in entries:
        if kind == "obj" and size > 0:
            gruns.append((guest, guest + size, native))
    gruns.sort()
    gcovered = sum(h - l for l, h, _ in gruns)
    g_lo = gruns[0][0]
    g_hi = max(h for _, h, _ in gruns)

    c_src.append("/* GUEST extents of the game's globals, sorted: [lo, hi) in the GUEST address\n")
    c_src.append(" * space, each with the native base of the same object. %d objects, %d bytes.\n"
                 % (len(gruns), gcovered))
    c_src.append(" *\n")
    c_src.append(" * This is what makes an INTERIOR guest pointer resolvable. gw_mex_bridge_lookup\n")
    c_src.append(" * matches an object's BASE only, so `global[i]` for i != 0 missed it and the\n")
    c_src.append(" * interpreter fell through to MEM1 - where the object is not, because the game's\n")
    c_src.append(" * statics live in this exe's .data. A silent wrong value on every interior\n")
    c_src.append(" * access to a global. The native side has had a range test for exactly this\n")
    c_src.append(" * reason; the forward direction simply never got one. */\n")
    c_src.append("typedef struct gw_mex_bridge_grun {\n")
    c_src.append("    uint32_t lo;\n")
    c_src.append("    uint32_t hi;\n")
    c_src.append("    uint32_t native;\n")
    c_src.append("} gw_mex_bridge_grun;\n\n")
    c_src.append("static const gw_mex_bridge_grun gw_mex_bridge_guest_tbl[] = {\n")
    for glo, ghi, gnat in gruns:
        c_src.append("    { 0x%08Xu, 0x%08Xu, 0x%08Xu },\n" % (glo, ghi, gnat))
    c_src.append("};\n\n")
    c_src.append("uint32_t gw_mex_bridge_guest_data(uint32_t guest_addr)\n")
    c_src.append("{\n")
    c_src.append("    uint32_t lo = 0;\n")
    c_src.append("    uint32_t hi = (uint32_t)(sizeof gw_mex_bridge_guest_tbl /\n")
    c_src.append("                            sizeof gw_mex_bridge_guest_tbl[0]);\n")
    c_src.append("    if (guest_addr < 0x%08Xu || guest_addr >= 0x%08Xu) {\n" % (g_lo, g_hi))
    c_src.append("        return 0;\n")
    c_src.append("    }\n")
    c_src.append("    while (lo < hi) {\n")
    c_src.append("        uint32_t mid = lo + (hi - lo) / 2;\n")
    c_src.append("        const gw_mex_bridge_grun *r = &gw_mex_bridge_guest_tbl[mid];\n")
    c_src.append("        if (guest_addr < r->lo) { hi = mid; continue; }\n")
    c_src.append("        if (guest_addr >= r->hi) { lo = mid + 1; continue; }\n")
    c_src.append("        return r->native + (guest_addr - r->lo);\n")
    c_src.append("    }\n")
    c_src.append("    return 0;\n")
    c_src.append("}\n\n")

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

    print("bridge: +%d demangled, +%d static-section (%d of them name-ambiguous, resolved by "
          "splits.txt), +%d function-local statics" % (n_demangled, n_static, n_split, n_local))
    print("bridge: %d entries (%d functions, %d objects) -> %s" %
          (len(entries), fn_count, obj_count, args.out_c))
    print("bridge: guest game-global extents: %d objects, %d bytes" % (len(gruns), gcovered))
    print("bridge: native game-global extents: %d runs, %d bytes, %d object(s) with no size" %
          (len(merged), covered, len(no_size)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
