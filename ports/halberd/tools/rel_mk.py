"""rel_mk.py - structural analysis of vanilla Brawl module/ft_metaknight.rel (module id 111).

Sections, relocations per imported module, function boundaries (doldecomp/brawl splits:
experiment/tooling/brawl/config/RSBE01_02/rels/ft_metaknight/symbols.txt), vtables reconstructed from
CodeWarrior RTTI (vtable = [typeinfo*, this-offset, fn*...]; typeinfo = [name*, bases*]), import names
from the decomp symbol lists of main.dol and sora_melee.rel, intra-module call graph, jump tables.
Writes ../dump/rel_mk.json.
"""
import collections
import json
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.normpath(os.path.join(HERE, "..", "..", "..", "experiment"))
REL = r"C:\iso\brawl-extract\files\module\ft_metaknight.rel"
CFG = os.path.join(EXP, "tooling", "brawl", "config", "RSBE01_02")
OUT = os.path.join(HERE, "..", "dump", "rel_mk.json")

d = open(REL, "rb").read()
U = lambda o: struct.unpack(">I", d[o:o + 4])[0]
SECNAME = [None, ".text", ".ctors", ".dtors", ".rodata", ".data", ".bss"]
secs = []
for i in range(U(0xC)):
    o = U(0x10) + 8 * i
    off, size = U(o), U(o + 4)
    secs.append(dict(index=i, name=SECNAME[i] if i < len(SECNAME) else None, offset=off & ~1, exec=bool(off & 1), size=size))
TEXT = secs[1]
DATA = secs[5]
RODATA = secs[4]


def sec_bytes(i):
    s = secs[i]
    return d[s["offset"]:s["offset"] + s["size"]] if s["offset"] else b""


# ---- symbol lists
SYM_RE = re.compile(r"^(\S+) = (\.\w+):0x([0-9A-Fa-f]+); // type:(\w+)(?: size:0x([0-9A-Fa-f]+))?")


def load_syms(path):
    out = []
    for line in open(path, encoding="utf-8"):
        m = SYM_RE.match(line)
        if m:
            out.append(dict(name=m.group(1), sec=m.group(2), addr=int(m.group(3), 16), type=m.group(4), size=int(m.group(5), 16) if m.group(5) else 0))
    return out


own = load_syms(os.path.join(CFG, "rels", "ft_metaknight", "symbols.txt"))
sora = load_syms(os.path.join(CFG, "rels", "sora_melee", "symbols.txt"))
main = load_syms(os.path.join(CFG, "symbols.txt"))
sora_by = {(s["sec"], s["addr"]): s["name"] for s in sora}
main_by = {s["addr"]: s["name"] for s in main}
funcs = sorted([s for s in own if s["sec"] == ".text" and s["type"] == "function"], key=lambda s: s["addr"])

# ---- relocations
names_mod = {0: "main.dol", 27: "sora_melee", 111: "ft_metaknight"}
relocs = []  # (module, src_sec, src_off, type, dst_sec, addend)
imps = []
for k in range(U(0x2C) // 8):
    mid, roff = U(U(0x28) + 8 * k), U(U(0x28) + 8 * k + 4)
    o, cur_sec, pos, tc = roff, None, 0, collections.Counter()
    while True:
        off, typ, sec, add = struct.unpack(">HBBI", d[o:o + 8])
        o += 8
        if typ == 0xCB:
            break
        pos += off
        if typ == 0xCA:
            cur_sec, pos = sec, 0
            continue
        if typ == 0xC9:
            continue
        tc[typ] += 1
        relocs.append((mid, cur_sec, pos, typ, sec, add))
    imps.append(dict(module_id=mid, module=names_mod.get(mid, str(mid)), relocations=sum(tc.values()), by_type={str(a): b for a, b in sorted(tc.items())}))
RTYPE = {1: "abs32", 4: "lo16", 5: "hi16", 6: "hi16_adjusted", 10: "branch24"}


def target_name(mid, dsec, add):
    if mid == 0:
        return main_by.get(add, "main.dol:0x%08X" % add)
    if mid == 27:
        return sora_by.get((SECNAME[dsec], add), "sora_melee:%s+0x%X" % (SECNAME[dsec], add))
    if mid == 111:
        return "self:%s+0x%X" % (SECNAME[dsec], add)
    return "%d:%d+0x%X" % (mid, dsec, add)


# ---- function lookup
starts = [f["addr"] for f in funcs]


def func_at(off):
    import bisect
    i = bisect.bisect_right(starts, off) - 1
    if i >= 0 and off < funcs[i]["addr"] + max(funcs[i]["size"], 4):
        return funcs[i]["name"]
    return None


# ---- per-function calls (reloc'd branches = imports; plain bl within .text = local)
text = sec_bytes(1)
calls = collections.defaultdict(collections.Counter)
imports_ct = collections.Counter()
reloc_sites = set()
for mid, ssec, soff, typ, dsec, add in relocs:
    if ssec == 1:
        reloc_sites.add(soff)
        fn = func_at(soff)
        tn = target_name(mid, dsec, add)
        if typ == 10:
            if mid == 111 and dsec == 1:
                tn = func_at(add) or tn
            calls[fn][tn] += 1
        if mid in (0, 27):
            imports_ct[(mid, tn, RTYPE.get(typ, str(typ)))] += 1
for off in range(0, len(text), 4):
    w = struct.unpack(">I", text[off:off + 4])[0]
    if (w >> 26) == 18 and (w & 3) == 1 and off not in reloc_sites:  # bl, relative
        li = w & 0x03FFFFFC
        if li & 0x02000000:
            li -= 0x04000000
        tgt = off + li
        if 0 <= tgt < len(text):
            calls[func_at(off)][func_at(tgt) or "self:.text+0x%X" % tgt] += 1

# ---- .data word relocations -> vtables via RTTI
data = sec_bytes(5)
rodata = sec_bytes(4)
dw = {}
for mid, ssec, soff, typ, dsec, add in relocs:
    if ssec == 5 and typ == 1:
        dw[soff] = (mid, dsec, add)


def cstr(sec, off):
    b = data if sec == 5 else rodata if sec == 4 else b""
    if off >= len(b):
        return None
    e = b.find(b"\0", off)
    s = b[off:e]
    if len(s) >= 2 and all(32 <= c < 127 for c in s):
        return s.decode()
    return None


typeinfo = {}
for o, (mid, dsec, add) in dw.items():
    if mid == 111 and dsec in (4, 5):
        s = cstr(dsec, add)
        if s and o % 4 == 0:
            typeinfo[o] = s  # o = typeinfo struct (first word = name ptr)
vtables = []
for o in sorted(dw):
    mid, dsec, add = dw[o]
    if mid == 111 and dsec == 5 and add in typeinfo:
        # vtable candidate: next word = this-offset (unrelocated), then function pointers
        slots = []
        p = o + 8
        while p in dw and dw[p][1] == 1:
            m2, s2, a2 = dw[p]
            slots.append(func_at(a2) if m2 == 111 else target_name(m2, s2, a2))
            p += 4
        if slots:
            this_off = struct.unpack(">i", data[o + 4:o + 8])[0]
            vtables.append(dict(offset="0x%X" % o, class_name=typeinfo[add], this_offset=this_off, slots=slots,
                                own_slots=sum(1 for s in slots if s and s.startswith("fn_111_"))))
fn_classes = collections.defaultdict(set)
for v in vtables:
    for k, s in enumerate(v["slots"]):
        if s and s.startswith("fn_111_"):
            fn_classes[s].add("%s[%d]" % (v["class_name"], k))

# ---- jump tables (switches); count distinct targets
jts = []
for s in own:
    if s["name"].startswith("jumptable_"):
        ents = [dw.get(s["addr"] + 4 * k) for k in range(s["size"] // 4)]
        tg = [func_at(e[2]) for e in ents if e and e[1] == 1]
        jts.append(dict(name=s["name"], offset="0x%X" % s["addr"], entries=s["size"] // 4, function=collections.Counter(tg).most_common(1)[0][0] if tg else None))

# ---- rodata floats
flt = []
for k in range(0, len(rodata) - 3, 4):
    f = struct.unpack(">f", rodata[k:k + 4])[0]
    flt.append(round(f, 6))

strings = sorted(set(m.group().decode() for m in re.finditer(rb"[ -~]{6,}", data + rodata)))
fl = []
for f in funcs:
    cl = calls.get(f["name"], {})
    fl.append(dict(name=f["name"], offset="0x%X" % f["addr"], size=f["size"], classes=sorted(fn_classes.get(f["name"], [])),
                   calls={k: v for k, v in sorted(cl.items(), key=lambda x: -x[1])}))
out = dict(
    file="module/ft_metaknight.rel", bytes=len(d),
    header=dict(module_id=U(0), num_sections=U(0xC), version=U(0x1C), bss_size=U(0x20), prolog="0x%X" % U(0x34), epilog="0x%X" % U(0x38), unresolved="0x%X" % U(0x3C)),
    sections=[dict(s, offset="0x%X" % s["offset"]) for s in secs if s["size"]],
    imports=imps, relocations_total=len(relocs),
    import_targets=[dict(module=names_mod[m], target=t, kind=k, count=c) for (m, t, k), c in imports_ct.most_common()],
    functions=fl, vtables=vtables, jump_tables=jts, rodata_floats=flt, strings=strings,
    symbol_source="doldecomp/brawl config RSBE01_02 (experiment/tooling/brawl @ 345952a3)",
)
json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1)
print("functions", len(fl), "vtables", len(vtables), "own-slot fns", len(fn_classes), "jumptables", len(jts), "imports", len(imports_ct), "relocs", len(relocs))
for v in vtables:
    print(v["offset"], v["class_name"], len(v["slots"]), v["own_slots"])
