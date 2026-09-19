#!/usr/bin/env python3
"""Derive PowerPC bridge call signatures from the decomp's own C prototypes.

WHY THIS EXISTS
---------------
`gw_ppc_bridge_call` (pc/platform/gw_ppc.c) marshals a guest PPC call out to a native engine
function using a `gw_ppc_sig` {float_args, n_args, ret_float}. When the resolver supplies no
signature the bridge DEFAULTS to float_args=0, n_args=8, ret_float=0 - i.e. "every argument is
an integer in r3..r10, the return is a word in r3".

PowerPC EABI does not work that way: each float parameter is passed in the next FPR (f1..f8)
while each integer/pointer parameter takes the next GPR (r3..r10), interleaved in *declaration*
order, and a float return comes back in f1. So for any function taking or returning a float the
default reads the WRONG registers and throws the float return away. It does not crash; it
silently produces wrong numbers (this is what made `atan2f` return garbage and hang the guest's
`while (a < 0) a += 2*PI;` loop).

A hand-written table (`gw_mex_sigs` in pc/platform/gw_mex_ftfunction_runtime.c) covers libm plus
one engine function. This tool derives the rest mechanically from the decomp prototypes.

SIBLING TOOL, NOT AN EXTENSION OF gen_bridge.py
-----------------------------------------------
gen_bridge.py answers "where does guest address X live natively?" by pairing symbols.txt with the
LINKER MAP - it must be re-run after every relink. This tool answers a different question,
"what shape does guest address X have?", from symbols.txt plus the decomp HEADERS - it does not
depend on the map and does not need re-running when the game relinks. The inputs, the cadence and
the failure modes are disjoint, so they stay separate programs. They share only the symbols.txt
parser, which is duplicated here (a dozen lines) rather than coupling the two.

CONSERVATISM RULE
-----------------
A wrong signature is another silent-garbage bug and is strictly worse than no signature (no
signature = today's status quo for that target). Whenever a prototype cannot be parsed with
confidence this tool EMITS NOTHING for it and records it in the warnings list. It never guesses.

Usage:
  python3 tools/mex_port/gen_sigs.py [--blob PATH --blob-base ADDR] [--out-c PATH] [--report PATH]
"""
import argparse
import os
import re
import struct
import sys

# --------------------------------------------------------------------------------------
# symbols.txt:  name = .text:0xADDR; // type:function size:0x30 scope:global
# --------------------------------------------------------------------------------------
SYMBOL_RE = re.compile(
    r"^\s*(?P<name>\S+)\s*=\s*\.\S+:(?P<addr>0x[0-9A-Fa-f]+)\s*;.*?type:(?P<typ>\w+)"
)


def parse_symbols(path):
    """name -> (addr, type). Keeps the first listing of a name (it may repeat per section)."""
    out = {}
    for line in open(path, "r", encoding="utf-8", errors="replace"):
        m = SYMBOL_RE.match(line)
        if not m:
            continue
        name = m.group("name")
        if name not in out:
            out[name] = (int(m.group("addr"), 16), m.group("typ"))
    return out


def ambiguous_names(path):
    """Function names listed at more than one address -> set of those addresses."""
    seen = {}
    for line in open(path, "r", encoding="utf-8", errors="replace"):
        m = SYMBOL_RE.match(line)
        if m and m.group("typ") == "function":
            seen.setdefault(m.group("name"), set()).add(int(m.group("addr"), 16))
    return dict((k, v) for k, v in seen.items() if len(v) > 1)


# --------------------------------------------------------------------------------------
# Blob scan: find the guest addresses the relocated m-ex code actually bridges out to.
# A `bl` is opcode 18 (0x48000000) with LK=1; the 24-bit displacement is sign-extended and
# word-aligned. AA=1 means the displacement is an absolute address.
# --------------------------------------------------------------------------------------
def scan_blob_targets(path, base):
    data = open(path, "rb").read()
    n = len(data)
    targets = set()
    for off in range(0, n - 3, 4):
        w = struct.unpack_from(">I", data, off)[0]
        if (w >> 26) != 18 or not (w & 1):
            continue
        d = w & 0x03FFFFFC
        if d & 0x02000000:
            d -= 0x04000000
        t = d & 0xFFFFFFFF if (w >> 1) & 1 else (base + off + d) & 0xFFFFFFFF
        if base <= t < base + n:
            continue  # internal call: interpreted, not bridged
        targets.add(t)
    return targets, n


# --------------------------------------------------------------------------------------
# Header / source scanning
#
# Include roots are exactly the ones the PC port compiles with
# (melee/pc/build/masstest/pipe_win.sh):
#     -Isrc -isystem src/MSL -isystem extern/dolphin/include -isystem extern/dolphin/src
#     -isystem build/GALE01/include
# Scanning a root the build does NOT use (extern/aurora, dusklight/) would let a
# *different* project's prototype win, so those are excluded deliberately.
# --------------------------------------------------------------------------------------
INCLUDE_ROOTS = [
    "melee/src",
    "melee/extern/dolphin/include",
    "melee/extern/dolphin/src",
    "melee/build/GALE01/include",
]

BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
LINE_COMMENT = re.compile(r"//[^\n]*")
ADDR_COMMENT = re.compile(r"/\*\s*([0-9A-Fa-f]{6})\s*\*/")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def strip_comments_keep_addr(text):
    """Blank out comments (preserving offsets) but remember each `/* 0693AC */` address tag."""
    addr_at = {}  # offset of the char AFTER the comment -> address string
    out = list(text)

    def blank(m):
        a = ADDR_COMMENT.match(m.group(0))
        if a:
            addr_at[m.end()] = a.group(1)
        for i in range(m.start(), m.end()):
            if out[i] != "\n":
                out[i] = " "

    for m in BLOCK_COMMENT.finditer(text):
        blank(m)
    for m in LINE_COMMENT.finditer("".join(out)):
        for i in range(m.start(), m.end()):
            out[i] = " "
    return "".join(out), addr_at


def find_prototypes(text, wanted):
    """Yield (name, ret_text, params_text, addr_tag) for each declaration/definition of a
    wanted name. Handles multi-line prototypes; requires a `;` or `{` after the parameter
    list so call sites and macro uses are not mistaken for declarations."""
    src, addr_at = strip_comments_keep_addr(text)
    n = len(src)
    for m in IDENT.finditer(src):
        name = m.group(0)
        if name not in wanted:
            continue
        i = m.end()
        while i < n and src[i] in " \t\n":
            i += 1
        if i >= n or src[i] != "(":
            continue
        # match the parameter list
        depth = 0
        j = i
        while j < n:
            if src[j] == "(":
                depth += 1
            elif src[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= n:
            continue
        params = src[i + 1:j]
        k = j + 1
        while k < n and src[k] in " \t\n":
            k += 1
        if k >= n or src[k] not in ";{":
            continue  # a call, not a declaration
        # the return type is whatever sits between the previous statement boundary and the name
        s = m.start()
        b = max(src.rfind(";", 0, s), src.rfind("}", 0, s), src.rfind("{", 0, s),
                src.rfind(")", 0, s), src.rfind("#", 0, s), -1)
        ret = src[b + 1:s]
        if "\n" in ret.strip():  # a stray multi-statement span: too risky to read
            ret = ret.strip().splitlines()[-1]
        # `(*name)(...)` is a function-pointer declarator, not a function declaration
        if ret.rstrip().endswith("(*") or ret.rstrip().endswith("( *"):
            continue
        tag = None
        for off, a in addr_at.items():
            if 0 <= s - off <= 80 and src[off:s].strip().replace("*", "").replace(" ", "") \
                    == ret.strip().replace("*", "").replace(" ", ""):
                tag = a
                break
        yield name, ret.strip(), params.strip(), tag, ("def" if src[k] == "{" else "decl")


def collect_prototypes(repo, wanted):
    """name -> list of (ret, params, addr_tag, kind, path)."""
    found = {}
    for root in INCLUDE_ROOTS:
        base = os.path.join(repo, root)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for f in files:
                if not f.endswith((".h", ".c")):
                    continue
                p = os.path.join(dirpath, f)
                try:
                    text = open(p, "r", encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                # Cheap pre-filter: skip files that mention none of the names. Testing set
                # membership of the file's identifiers beats `any(w in text ...)` once
                # `wanted` is large (--all-symbols).
                if not (wanted & set(IDENT.findall(text))):
                    continue
                for name, ret, params, tag, kind in find_prototypes(text, wanted):
                    found.setdefault(name, []).append((ret, params, tag, kind, p))
    return found


# --------------------------------------------------------------------------------------
# Type classification
#
# The bridge marshals each native argument into ONE 32-bit slot. So a parameter is usable
# only when it is either:
#   INT   - an integer, enum or pointer: rides the next GPR (r3..r10), one slot.
#   FLOAT - a 4-byte float: rides the next FPR (f1..f8), one slot (bits copied verbatim).
# Everything else (double, by-value struct, varargs, unknown typedef) is UNSUPPORTED and
# makes the whole function unparseable. `double` in particular is NOT just "a wider float":
# PPC would pass it in an FPR but the native callee expects 8 bytes across two cdecl slots,
# and gw_ppc_bridge_call only ever writes 4.
# --------------------------------------------------------------------------------------
INT, FLOAT, DOUBLE, STRUCT, UNKNOWN, VOID = "INT", "FLOAT", "DOUBLE", "STRUCT", "UNKNOWN", "VOID"

# Builtin / fixed-width scalars the decomp uses everywhere.
BASE_TYPES = {
    "void": VOID,
    "char": INT, "signed char": INT, "unsigned char": INT,
    "short": INT, "short int": INT, "unsigned short": INT, "unsigned short int": INT,
    "int": INT, "signed": INT, "signed int": INT, "unsigned": INT, "unsigned int": INT,
    "long": INT, "long int": INT, "unsigned long": INT, "unsigned long int": INT,
    "long long": INT, "unsigned long long": INT,
    "_Bool": INT, "bool": INT,
    "s8": INT, "u8": INT, "s16": INT, "u16": INT, "s32": INT, "u32": INT,
    "s64": INT, "u64": INT, "size_t": INT, "ptrdiff_t": INT, "intptr_t": INT,
    "uintptr_t": INT, "uint32_t": INT, "int32_t": INT, "uint8_t": INT, "int8_t": INT,
    "uint16_t": INT, "int16_t": INT, "BOOL": INT, "vs32": INT, "vu32": INT,
    "vs16": INT, "vu16": INT, "vs8": INT, "vu8": INT,
    "float": FLOAT, "f32": FLOAT, "vf32": FLOAT,
    "double": DOUBLE, "long double": DOUBLE, "f64": DOUBLE, "vf64": DOUBLE,
    # placeholder.h: #define UNK_T void* / UNK_RET void
    "UNK_T": INT, "UNK_RET": VOID, "UNK_PARAMS": VOID,
}

TYPEDEF_RE = re.compile(
    r"\btypedef\s+(?P<body>[^;{}()]+?)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*;")
TYPEDEF_TAG_RE = re.compile(
    r"\btypedef\s+(?P<kw>struct|union|enum)\b[^;{}]*\{.*?\}\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*;",
    re.S)
TYPEDEF_FNPTR_RE = re.compile(
    r"\btypedef\s+[^;{}]*?\(\s*\*\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\)\s*\(")
ENUM_TAG_RE = re.compile(r"\benum\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\{")
STRUCT_TAG_RE = re.compile(r"\b(?:struct|union)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\{")


def collect_typedefs(repo):
    """typedef name -> category, resolved transitively. Anything not resolvable stays out of
    the map, which makes every function using it unparseable (the conservative outcome)."""
    raw = {}       # name -> the spelled-out base type, for later resolution
    direct = {}    # name -> category, known immediately
    for root in INCLUDE_ROOTS:
        base = os.path.join(repo, root)
        if not os.path.isdir(base):
            continue
        for dirpath, _d, files in os.walk(base):
            for f in files:
                if not f.endswith((".h", ".c")):
                    continue
                try:
                    text = open(os.path.join(dirpath, f), "r", encoding="utf-8",
                                errors="replace").read()
                except OSError:
                    continue
                text, _ = strip_comments_keep_addr(text)
                for m in TYPEDEF_FNPTR_RE.finditer(text):
                    direct.setdefault(m.group("name"), INT)  # function pointer == a pointer
                for m in TYPEDEF_TAG_RE.finditer(text):
                    direct.setdefault(m.group("name"),
                                      INT if m.group("kw") == "enum" else STRUCT)
                for m in ENUM_TAG_RE.finditer(text):
                    direct.setdefault("enum " + m.group("name"), INT)
                for m in STRUCT_TAG_RE.finditer(text):
                    direct.setdefault("struct " + m.group("name"), STRUCT)
                    direct.setdefault("union " + m.group("name"), STRUCT)
                for m in TYPEDEF_RE.finditer(text):
                    body = " ".join(m.group("body").split())
                    nm = m.group("name")
                    if "*" in body:
                        direct.setdefault(nm, INT)
                    elif body.startswith("enum "):
                        direct.setdefault(nm, INT)
                    elif body.startswith(("struct ", "union ")):
                        raw.setdefault(nm, body)
                    else:
                        raw.setdefault(nm, body)

    out = dict(direct)

    def resolve(name, seen):
        if name in out:
            return out[name]
        if name in BASE_TYPES:
            return BASE_TYPES[name]
        if name in seen:
            return None
        seen.add(name)
        body = raw.get(name)
        if body is None:
            return None
        if body.startswith(("struct ", "union ")):
            cat = out.get(body, STRUCT)   # a bare `typedef struct Foo Foo;` is an aggregate
        elif body in BASE_TYPES:
            cat = BASE_TYPES[body]
        else:
            cat = resolve(body, seen)
        if cat is not None:
            out[name] = cat
        return cat

    for nm in list(raw):
        resolve(nm, set())
    return out


# Storage-class / qualifier / attribute spellings that carry no ABI meaning. Each is verified
# to expand to nothing or to a pure __attribute__ (src/Runtime/platform.h), so dropping it
# cannot change how an argument is passed.
QUALIFIERS = {"const", "volatile", "restrict", "__restrict", "register", "static", "inline",
              "extern", "__attribute__", "ATTRIBUTE_ALIGN", "ATTRIBUTE_NORETURN",
              "__declspec", "noreturn", "aligned"}
# Longest-first so "unsigned long long" wins over "unsigned long" and "unsigned".
MULTIWORD = sorted((k for k in BASE_TYPES if " " in k), key=lambda s: -len(s.split()))


def split_params(text):
    """Split a parameter list on top-level commas (function-pointer params nest parens)."""
    out, depth, cur = [], 0, []
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur))
    return [p.strip() for p in out]


def classify_decl(decl, typedefs):
    """Classify one parameter (or a return type) -> (category, reason)."""
    d = " ".join(decl.split())
    if not d:
        return UNKNOWN, "empty declarator"
    if d == "...":
        return UNKNOWN, "varargs"
    if d in ("void",):
        return VOID, "void"
    # Pointers and arrays (including function pointers) are one GPR-sized integer slot.
    if "*" in d or "[" in d:
        return INT, "pointer/array"
    words = [w for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", d) if w not in QUALIFIERS]
    if not words:
        return UNKNOWN, "no type tokens in %r" % d
    if words[0] in ("struct", "union", "enum"):
        if len(words) < 2:
            return UNKNOWN, "anonymous aggregate parameter"
        tag = words[0] + " " + words[1]
        rest = words[2:]
        cat = typedefs.get(tag, INT if words[0] == "enum" else STRUCT)
    else:
        consumed, base = 1, words[0]
        for mw in MULTIWORD:
            parts = mw.split()
            if words[:len(parts)] == parts:
                consumed, base = len(parts), mw
                break
        rest = words[consumed:]
        cat = BASE_TYPES.get(base, typedefs.get(base))
        if cat is None:
            return UNKNOWN, "unresolved type %r" % base
    if len(rest) > 1:
        return UNKNOWN, "unexpected declarator tokens %r in %r" % (rest, d)
    return cat, d


def derive_sig(ret_text, params_text, typedefs):
    """-> (float_args, n_args, ret_float, detail) or (None, None, None, reason)."""
    params = split_params(params_text)
    if len(params) == 1 and params[0].strip() == "void":
        params = []
    if not params and params_text.strip() == "":
        # K&R `f()` says nothing about the arguments; the decomp uses it for genuinely
        # unknown prototypes, so refuse rather than assume zero.
        return None, None, None, "empty () parameter list: prototype is unspecified"

    slots, mask, detail = 0, 0, []
    for p in params:
        cat, why = classify_decl(p, typedefs)
        if cat == VOID:
            return None, None, None, "`void` among several parameters (%r)" % params_text
        if cat == FLOAT:
            mask |= 1 << slots
            detail.append("f:" + p.strip())
        elif cat == INT:
            detail.append("i:" + p.strip())
        elif cat == DOUBLE:
            return None, None, None, ("parameter %r is a double: the bridge marshals 4-byte "
                                      "slots only" % p.strip())
        elif cat == STRUCT:
            return None, None, None, "parameter %r is a by-value struct/union" % p.strip()
        else:
            return None, None, None, "parameter %r: %s" % (p.strip(), why)
        slots += 1
        if slots > 8:
            return None, None, None, "more than 8 argument slots (bridge caps at 8)"

    rcat, rwhy = classify_decl(ret_text, typedefs)
    if rcat == VOID or rcat == INT:
        ret_float = 0
    elif rcat == FLOAT:
        ret_float = 1
    elif rcat == DOUBLE:
        return None, None, None, "returns a double: the bridge captures a 4-byte float only"
    elif rcat == STRUCT:
        # PPC would pass a hidden sret pointer in r3 (shifting every argument by one slot) and
        # the native MSVC callee's own sret rule depends on the struct's size. Two ABIs that
        # only sometimes agree: refuse.
        return None, None, None, "returns a by-value struct/union (hidden sret pointer)"
    else:
        return None, None, None, "return type %r: %s" % (ret_text, rwhy)
    return mask, slots, ret_float, ", ".join(detail) if detail else "(void)"



# --------------------------------------------------------------------------------------
# Call-site cross-check (independent evidence, advisory)
#
# The derived signature says "this call passes N floats". The guest code at each call site
# says the same thing out loud: before a `bl` it loads the float arguments into f1..fN. So
# walking backwards from every call site and recording the highest FPR written gives a second,
# completely independent opinion on the float count - one that comes from the compiled m-ex
# code rather than from the decomp headers.
#
# This is a HEURISTIC and its result is advisory, never authoritative:
#   - the backward walk stops at the previous branch, so it can miss a load placed earlier;
#   - a float argument can be left in an FPR by the *previous* call's return value;
#   - it sees the highest FPR written, which bounds the float count but cannot tell WHICH
#     argument slots they are.
# A mismatch is therefore a prompt to go read the prototype, not proof that it is wrong.
# --------------------------------------------------------------------------------------
FPR_DEST_OPS = {48, 49, 50, 51}          # lfs, lfsu, lfd, lfdu  -> frD in bits 6..10
FPR_ARITH_OPS = {59, 63}                 # float arithmetic      -> frD in bits 6..10
BRANCH_OPS = {16, 18, 19}


def callsite_float_counts(blob_path, base):
    """guest target -> set of observed "highest FPR index written before the call" values."""
    data = open(blob_path, "rb").read()
    n = len(data)
    words = [struct.unpack_from(">I", data, o)[0] for o in range(0, n - (n % 4), 4)]
    out = {}
    for idx, w in enumerate(words):
        if (w >> 26) != 18 or not (w & 1):
            continue
        d = w & 0x03FFFFFC
        if d & 0x02000000:
            d -= 0x04000000
        t = d & 0xFFFFFFFF if (w >> 1) & 1 else (base + idx * 4 + d) & 0xFFFFFFFF
        if base <= t < base + n:
            continue
        hi = 0
        for k in range(idx - 1, max(-1, idx - 13), -1):
            ww = words[k]
            op = ww >> 26
            if op in BRANCH_OPS:
                break
            if op in FPR_DEST_OPS or op in FPR_ARITH_OPS:
                frd = (ww >> 21) & 31
                if 1 <= frd <= 8:
                    hi = max(hi, frd)
        out.setdefault(t, set()).add(hi)
    return out

# --------------------------------------------------------------------------------------
# Candidate selection
# --------------------------------------------------------------------------------------
def tier_of(cand, addr):
    """Rank a prototype candidate. Lower is better.

      0 = header declaration carrying a `/* XXXXXX */` tag that MATCHES symbols.txt
      1 = header declaration with no address tag
      2 = definition in a .c, or any other spelling
      9 = the address tag CONTRADICTS symbols.txt -> never usable.
    """
    _ret, _params, tag, kind, path = cand
    is_hdr = path.endswith(".h")
    if tag is not None:
        if int(tag, 16) == (addr & 0xFFFFFF):
            return 0 if is_hdr else 2
        return 9
    return 1 if (is_hdr and kind == "decl") else 2


def resolve_one(name, addr, cands, typedefs):
    """-> (sig, note) where sig is (mask, nargs, ret_float) or None."""
    if not cands:
        return None, "no prototype found in any include root"
    ranked = {}
    for c in cands:
        ranked.setdefault(tier_of(c, addr), []).append(c)
    if set(ranked) == {9}:
        return None, "every prototype address tag contradicts symbols.txt"
    tiers = sorted(t for t in ranked if t != 9)
    for tier in tiers:
        parsed, failures = {}, []
        for ret, params, _tag, _kind, path in ranked[tier]:
            mask, nargs, rf, why = derive_sig(ret, params, typedefs)
            if mask is None:
                failures.append("%s: %s" % (os.path.basename(path), why))
            else:
                parsed.setdefault((mask, nargs, rf), []).append((path, why))
        if not parsed:
            if tier == tiers[0]:
                return None, "; ".join(sorted(set(failures))[:3])
            continue
        if len(parsed) > 1:
            shapes = ["mask=0x%X n=%d rf=%d" % k for k in parsed]
            return None, "conflicting prototypes: " + " vs ".join(sorted(shapes))
        key = list(parsed.keys())[0]
        info = parsed[key]
        rel = info[0][0].replace("\\", "/")
        return key, "tier%d %s [%s]" % (tier, rel.split("/melee/")[-1], info[0][1])
    return None, "no candidate parsed"


# The hand-written table already in pc/platform/gw_mex_ftfunction_runtime.c. The generator MUST
# agree with every one of these; a disagreement is a bug in the generator, not license to
# special-case the entry.
HANDWRITTEN = {
    0x8000CE50: (0x1, 1, 1, "expf"),
    0x8000CEE0: (0x3, 2, 1, "powf"),
    0x80022C30: (0x3, 2, 1, "atan2f"),
    0x80022D1C: (0x1, 1, 1, "acosf"),
    0x80022DBC: (0x1, 1, 1, "asinf"),
    0x80022E68: (0x1, 1, 1, "atanf"),
    0x803261BC: (0x1, 1, 1, "tanf"),
    0x80326240: (0x1, 1, 1, "cosf"),
    0x803263D4: (0x1, 1, 1, "sinf"),
    0x803265A8: (0x1, 1, 1, "logf"),
    0x80364340: (0x3, 2, 1, "fmodf"),
    0x803228C0: (0x1, 1, 0, "__cvt_fp2unsigned"),
    0x800693AC: ((1 << 3) | (1 << 4) | (1 << 5), 7, 0, "Fighter_ChangeMotionState"),
}


def emit_c(entries, path, blob_info):
    L = []
    L.append("/* gw_mex_sigs_gen.c - GENERATED by tools/mex_port/gen_sigs.py - do not edit.\n")
    L.append(" *\n")
    L.append(" * PowerPC->native call signatures for the guest addresses the m-ex blob bridges\n")
    L.append(" * out to, derived from the decomp C prototypes. Each entry tells\n")
    L.append(" * gw_ppc_bridge_call which argument slots come from an FPR (f1..f8) rather than a\n")
    L.append(" * GPR (r3..r10), how many slots there are, and whether the result returns in f1.\n")
    L.append(" *\n")
    L.append(" * %s\n" % blob_info)
    L.append(" * Functions whose prototype could not be parsed with confidence are deliberately\n")
    L.append(" * ABSENT: they keep the interpreter's integer default, which is what they already\n")
    L.append(" * had. See _research/bridge-signatures.md for the list and the reasons.\n")
    L.append(" */\n")
    L.append("#include <stdint.h>\n\n")
    L.append("typedef struct gw_mex_gen_sig {\n")
    L.append("    uint32_t guest;      /* guest address, as in config/GALE01/symbols.txt */\n")
    L.append("    uint32_t float_args; /* bit i => arg slot i is a float from the next FPR */\n")
    L.append("    uint32_t n_args;     /* 0..8 */\n")
    L.append("    int      ret_float;  /* callee returns a float, captured into f1 */\n")
    L.append("} gw_mex_gen_sig;\n\n")
    L.append("/* Sorted by guest address; binary-searchable. */\n")
    L.append("static const gw_mex_gen_sig gw_mex_gen_sigs[] = {\n")
    for addr, name, mask, nargs, rf, note in entries:
        L.append("    { 0x%08Xu, 0x%02Xu, %u, %d }, /* %s */\n"
                 % (addr, mask, nargs, rf, name))
    L.append("};\n\n")
    L.append("#define GW_MEX_GEN_SIG_COUNT "
             "((uint32_t)(sizeof gw_mex_gen_sigs / sizeof gw_mex_gen_sigs[0]))\n")
    open(path, "w").write("".join(L))


def main():
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default=os.path.join(repo, "melee/config/GALE01/symbols.txt"))
    ap.add_argument("--blob", default=os.path.join(repo, "_build/sonic_ftfunction_reloc.bin"))
    ap.add_argument("--blob-base", default="0x807F4D60")
    ap.add_argument("--out-c", default=os.path.join(repo, "_build/gw_mex_sigs_gen.c"))
    ap.add_argument("--report", default=None,
                    help="where to write the audit (default: <out-c>.report.txt)")
    ap.add_argument("--all-symbols", action="store_true",
                    help="derive for every function in symbols.txt, not just the blob targets")
    args = ap.parse_args()
    if args.report is None:
        args.report = args.out_c + ".report.txt"

    syms = parse_symbols(args.symbols)
    ambiguous = ambiguous_names(args.symbols)
    by_addr = {}
    for nm, (a, t) in syms.items():
        if t == "function":
            by_addr.setdefault(a, nm)
    # parse_symbols keeps only a name's FIRST address, so re-add the other addresses of an
    # ambiguous name; they are then refused below instead of silently dropped.
    for nm, addrs in ambiguous.items():
        for a in addrs:
            by_addr.setdefault(a, nm)

    if args.all_symbols:
        targets = sorted(by_addr)
        blob_info = "Scope: every function symbol in symbols.txt (--all-symbols)."
    else:
        tset, blen = scan_blob_targets(args.blob, int(args.blob_base, 16))
        targets = sorted(tset)
        blob_info = ("Scope: the %d distinct out-of-blob bl targets in %s (base 0x%08X, %d "
                     "bytes)." % (len(targets), os.path.basename(args.blob),
                                  int(args.blob_base, 16), blen))

    # Always resolve the hand-written entries too, even when they are outside the blob scope:
    # the cross-check below is the tool's only ground truth and must cover all of them.
    blob_targets = set(targets)
    targets = sorted(set(targets) | set(HANDWRITTEN))

    wanted = set(by_addr[t] for t in targets if t in by_addr)
    sys.stderr.write("scanning prototypes for %d names...\n" % len(wanted))
    typedefs = collect_typedefs(repo)
    protos = collect_prototypes(repo, wanted)
    sys.stderr.write("typedefs resolved: %d; names with candidates: %d\n"
                     % (len(typedefs), len(protos)))

    entries, unparseable = [], []
    for addr in targets:
        name = by_addr.get(addr)
        if name is None:
            unparseable.append((addr, "<no symbol>",
                                "address is not a function in symbols.txt (data, or a false "
                                "bl decoded out of an in-blob data word)"))
            continue
        if name in ambiguous:
            unparseable.append((addr, name, "name denotes %d different addresses in "
                                "symbols.txt (static helper repeated across TUs): a prototype "
                                "cannot be attributed to one of them" % len(ambiguous[name])))
            continue
        sig, note = resolve_one(name, addr, protos.get(name, []), typedefs)
        if sig is None:
            unparseable.append((addr, name, note))
        else:
            mask, nargs, rf = sig
            entries.append((addr, name, mask, nargs, rf, note))

    # --- cross-check against the hand-written table -----------------------------------
    disagreements, confirmed, uncovered = [], [], []
    got = dict((e[0], e) for e in entries)
    for a in sorted(HANDWRITTEN):
        m, n, rf, nm = HANDWRITTEN[a]
        e = got.get(a)
        if e is None:
            miss = [u for u in unparseable if u[0] == a]
            reason = miss[0][2] if miss else "not in the derived scope"
            uncovered.append((a, nm, reason))
        elif (e[2], e[3], e[4]) != (m, n, rf):
            disagreements.append((a, nm, (m, n, rf), (e[2], e[3], e[4]), e[5]))
        else:
            confirmed.append((a, nm))

    emit_c(entries, args.out_c, blob_info)

    lines = []
    lines.append(blob_info)
    b_res = sum(1 for e in entries if e[0] in blob_targets)
    b_unres = sum(1 for u in unparseable if u[0] in blob_targets)
    lines.append("%s: %d   resolved: %d   unresolved: %d"
                 % ("functions" if args.all_symbols else "blob targets",
                    len(blob_targets), b_res, b_unres))
    lines.append("total scope (blob + hand-written cross-check set): %d   resolved: %d   "
                 "unresolved: %d" % (len(targets), len(entries), len(unparseable)))
    lines.append("with float args or a float return: %d"
                 % sum(1 for e in entries if e[2] or e[4]))
    lines.append("")
    lines.append("== hand-written cross-check (%d entries) ==" % len(HANDWRITTEN))
    lines.append("confirmed: %d   disagreements: %d   not covered: %d"
                 % (len(confirmed), len(disagreements), len(uncovered)))
    for a, nm, exp, got_, why in disagreements:
        lines.append("  DISAGREE 0x%08X %s: handwritten mask=0x%X n=%d rf=%d | derived "
                     "mask=0x%X n=%d rf=%d  (%s)" % (a, nm, exp[0], exp[1], exp[2],
                                                     got_[0], got_[1], got_[2], why))
    for a, nm, why in uncovered:
        lines.append("  NOT-COVERED 0x%08X %s: %s" % (a, nm, why))
    lines.append("")
    lines.append("== call-site cross-check (advisory; see the note above the scanner) ==")
    if args.all_symbols:
        lines.append("  skipped (--all-symbols has no blob to scan)")
    else:
        obs = callsite_float_counts(args.blob, int(args.blob_base, 16))
        agree = flagged = 0
        flags = []
        for addr, name, mask, nargs, rf, note in entries:
            if addr not in obs:
                continue
            want = bin(mask).count("1")
            seen = obs[addr]
            if want in seen or (want == 0 and seen == {0}):
                agree += 1
            else:
                flagged += 1
                flags.append("  CHECK 0x%08X %-40s derived %d float arg(s); call sites load up "
                             "to f%s" % (addr, name, want,
                                         "/f".join(str(x) for x in sorted(seen))))
        lines.append("  agree: %d   worth a look: %d" % (agree, flagged))
        lines.extend(flags)
    lines.append("")
    lines.append("== resolved ==")
    for addr, name, mask, nargs, rf, note in entries:
        lines.append("  0x%08X %-46s mask=0x%02X n=%d rf=%d  %s"
                     % (addr, name, mask, nargs, rf, note))
    lines.append("")
    lines.append("== NOT emitted (these keep the integer default) ==")
    for addr, name, why in unparseable:
        lines.append("  0x%08X %-46s %s" % (addr, name, why))
    report = chr(10).join(lines) + chr(10)
    open(args.report, "w").write(report)
    sys.stderr.write("wrote %s + %s\n" % (args.out_c, args.report))
    print(report)

    if disagreements:
        sys.stderr.write("FAIL: %d disagreement(s) with the hand-written table\n"
                         % len(disagreements))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
