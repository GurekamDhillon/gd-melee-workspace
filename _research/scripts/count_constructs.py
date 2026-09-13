#!/usr/bin/env python3
"""Count MWCC-specific constructs / intrinsics per source area of doldecomp/melee.
Read-only. Usage: python count_constructs.py [melee_root]"""
import os, re, sys, collections

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"C:\gdm\melee"
AREAS = {
    "melee": "src/melee",
    "sysdolphin": "src/sysdolphin",
    "dolphin/include": "extern/dolphin/include",
    "dolphin/src": "extern/dolphin/src",
    "MSL": "src/MSL",
    "Runtime": "src/Runtime",
    "MetroTRK": "src/MetroTRK",
    "src-root": "src",  # placeholder.h / m2c_macros.h (non-recursive handled below)
}
PATTERNS = collections.OrderedDict([
    ("asm-keyword", r"\basm\b"),
    ("__asm", r"__asm"),
    ("ASM-macro", r"\bASM\b"),
    ("__cntlzw", r"__cntlzw"),
    ("__fabs", r"__fabs\b"),
    ("__fabsf", r"__fabsf"),
    ("__frsqrte", r"__frsqrte"),
    ("__fres", r"__fres\b"),
    ("__fnmsub*", r"__fnmsub"),
    ("__fmadd*", r"__fmadd"),
    ("__fsel", r"__fsel"),
    ("__rlwimi", r"__rlwimi"),
    ("__rlwinm", r"__rlwinm"),
    ("__lwbrx/__stwbrx/__lhbrx/__sthbrx", r"__(lw|st|lh|sth)brx"),
    ("__dcbz", r"__dcbz"),
    ("__dcb[fsi]/__icbi", r"__(dcb[fsi]|icbi)\b"),
    ("__sync/__isync/__eieio", r"__(sync|isync|eieio)\s*\("),
    ("__mftb", r"__mftb"),
    ("__abs/__labs", r"__l?abs\b"),
    ("psq_ / paired-single", r"\bpsq_|\bps_"),
    ("__builtin_*", r"__builtin_\w+"),
    ("__va_arg/_var_arg_typeof", r"__va_arg|_var_arg_typeof"),
    ("__MWERKS__", r"__MWERKS__"),
    ("MWERKS_GEKKO", r"MWERKS_GEKKO"),
    ("__PPCGEKKO__", r"__PPCGEKKO__"),
    ("LINT", r"\bLINT\b"),
    ("M2CTX", r"\bM2CTX\b"),
    ("M2C_FIELD", r"M2C_FIELD"),
    ("M2C_*other", r"M2C_(?!FIELD)\w+"),
    ("MUST_MATCH", r"\bMUST_MATCH\b"),
    ("#pragma", r"^\s*#\s*pragma\b"),
    ("__declspec", r"__declspec"),
    ("__attribute__", r"__attribute__"),
    ("AT_ADDRESS / : 0x addr", r"AT_ADDRESS"),
    ("register kw", r"\bregister\b"),
    ("volatile kw", r"\bvolatile\b"),
    ("inline kw", r"\binline\b"),
    ("static inline", r"\bstatic\s+inline\b"),
    ("__inline", r"\b__inline\b"),
    ("__attribute__((weak))/WEAK", r"\bWEAK\b"),
    ("SECTION_*/SDATA/DATA", r"\b(SECTION_\w+|SDATA)\b"),
    ("PAD_STACK", r"\bPAD_STACK\b|FORCE_PAD_STACK"),
    ("__FILE__/__LINE__", r"__(FILE|LINE)__"),
    ("va_start", r"\bva_start\b"),
    ("va_list", r"\bva_list\b"),
    ("...) varargs decl", r"\.\.\.\s*\)"),
    ("OSFastCast", r"OSf32to|OSu\d+tof32|OSs\d+tof32|FastCast"),
    ("GQR", r"\bGQR|\bgqr\d"),
])

def iter_files(area_rel):
    base = os.path.join(ROOT, area_rel)
    if area_rel == "src":
        for f in os.listdir(base):
            p = os.path.join(base, f)
            if os.path.isfile(p) and f.endswith((".c", ".h")):
                yield p
        return
    for dp, dn, fn in os.walk(base):
        for f in fn:
            if f.endswith((".c", ".h")):
                yield os.path.join(dp, f)

results = collections.OrderedDict()
filehits = collections.defaultdict(lambda: collections.defaultdict(set))
compiled = {k: re.compile(v, re.M) for k, v in PATTERNS.items()}
for area, rel in AREAS.items():
    cnt_c = collections.Counter(); cnt_h = collections.Counter()
    for p in iter_files(rel):
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for k, rx in compiled.items():
            n = len(rx.findall(txt))
            if n:
                (cnt_c if p.endswith(".c") else cnt_h)[k] += n
                filehits[area][k].add(os.path.relpath(p, ROOT))
    results[area] = (cnt_c, cnt_h)

hdr = f"{'pattern':34s}" + "".join(f"{a[:14]:>16s}" for a in AREAS)
print(hdr)
for k in PATTERNS:
    row = f"{k:34s}"
    for a in AREAS:
        c, h = results[a]
        row += f"{str(c[k])+'/'+str(h[k]):>16s}"
    print(row)
print("\n(values are occurrences in .c/.h)\n")
if len(sys.argv) > 2:
    want = sys.argv[2]
    for a in AREAS:
        fs = sorted(filehits[a].get(want, []))
        if fs:
            print(f"[{a}] {want}: {len(fs)} files")
            for f in fs[:200]:
                print("   ", f)
