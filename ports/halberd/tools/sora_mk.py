"""sora_mk.py - find Meta Knight / glide classes that live in sora_melee.rel (module 27): vtables via CW RTTI,
slot -> function (doldecomp/brawl sora_melee symbols). Writes ../dump/sora_mk.json."""
import json, os, re, struct, bisect
HERE = os.path.dirname(os.path.abspath(__file__))
REL = r"C:\iso\brawl-extract\files\module\sora_melee.rel"
SYM = os.path.join(HERE, "..", "..", "..", "experiment", "tooling", "brawl", "config", "RSBE01_02", "rels", "sora_melee", "symbols.txt")
WANT = ("Metaknight", "Glide", "JumpAerialFly", "MultiJump")
d = open(REL, "rb").read()
U = lambda o: struct.unpack(">I", d[o:o + 4])[0]
secs = []
for i in range(U(0xC)):
    o = U(0x10) + 8 * i
    secs.append((U(o) & ~1, U(o + 4)))
SELF = U(0)
dw = {}
for k in range(U(0x2C) // 8):
    mid, roff = U(U(0x28) + 8 * k), U(U(0x28) + 8 * k + 4)
    if mid != SELF:
        continue
    o, cur, pos = roff, None, 0
    while True:
        off, typ, sec, add = struct.unpack(">HBBI", d[o:o + 8]); o += 8
        if typ == 0xCB: break
        pos += off
        if typ == 0xCA: cur, pos = sec, 0; continue
        if typ == 0xC9: continue
        if typ == 1: dw[(cur, pos)] = (sec, add)
syms = []
R = re.compile(r"^(\S+) = \.text:0x([0-9A-Fa-f]+); // type:function size:0x([0-9A-Fa-f]+)")
for line in open(SYM, encoding="utf-8"):
    m = R.match(line)
    if m: syms.append((int(m.group(2), 16), int(m.group(3), 16), m.group(1)))
syms.sort(); st = [s[0] for s in syms]
def fn(a):
    i = bisect.bisect_right(st, a) - 1
    return dict(name=syms[i][2], offset="0x%X" % syms[i][0], size=syms[i][1]) if i >= 0 and a < syms[i][0] + syms[i][1] else dict(name=None, offset="0x%X" % a)
def cstr(sec, off):
    b = d[secs[sec][0]:secs[sec][0] + secs[sec][1]]
    e = b.find(b"\0", off); s = b[off:e]
    return s.decode() if 2 <= len(s) < 400 and all(32 <= c < 127 for c in s) else None
ti = {}
for (sec, o), (tsec, add) in dw.items():
    if sec in (4, 5) and tsec in (4, 5):
        s = cstr(tsec, add)
        if s and any(w in s for w in WANT): ti[(sec, o)] = s
out = []
for (sec, o), (tsec, add) in sorted(dw.items()):
    if (tsec, add) in ti and sec == 5:
        slots, p = [], o + 8
        while (5, p) in dw and dw[(5, p)][0] == 1:
            slots.append(fn(dw[(5, p)][1])); p += 4
        if slots:
            out.append(dict(vtable=".data+0x%X" % o, class_name=ti[(tsec, add)], slots=slots))
json.dump(out, open(os.path.join(HERE, "..", "dump", "sora_mk.json"), "w"), indent=1)
for v in out:
    print(v["vtable"], v["class_name"][:90], len(v["slots"]), [(k, s["name"], s.get("size")) for k, s in enumerate(v["slots"]) if s.get("size", 0) > 8][:12])
