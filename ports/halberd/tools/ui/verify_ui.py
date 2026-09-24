"""Numeric checks of build_mk_ui.py's output (no screenshots):

    python tools/ui/verify_ui.py --after <mod files> [--before <files before build_mk_ui>] [--png build/ui/out]

 - MK's frames: CSP ext 51 + c*stride (6), stock reserved + c*stride + 52 (6), GmRst frame 51 (5 strips), CSS icon joint
   58 decode to the expected format / size and match the converted PNGs (mean texel error of the GX quantisation: CSP CI8 with one index map shared by the 6 costumes <= 11, icon CI8 <= 6, stock CI4 16-colour <= 16, I4 max <= 17);
 - every OTHER frame of those atlases (all fighters' CSPs / stocks / names / icons) decodes identical before vs after;
 - Brawl Kirby's art (CSP ext 33, stock internal 34, icon joint 57) is identical to brawl-kirby-slot's own files;
 - m-ex tables: MK's CSS icon row -> joint 58; insignia[51] = 5;
 - HSDRaw round trip (model/tools/mkbuild roundtrip) of MnSlChr.usd, IfAll.usd, GmRst.usd, MxDt.dat.
Exit 0 = all OK."""
import argparse, os, struct, subprocess, sys
from PIL import Image, ImageChops
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, r"C:/Users/Gurek/Desktop/GD's Melee/tools/mex_port"); sys.path.insert(0, HERE)
import mex_hsd, fobj, gxcodec as G
BKSLOT = os.path.join(os.path.dirname(os.path.dirname(MK)), "experiment", "brawl-kirby", "mods-slot", "brawl-kirby-slot", "files")
MB = os.path.join(MK, "model", "tools", "mkbuild", "bin", "Release", "net8.0", "mkbuild.exe")
ap = argparse.ArgumentParser()
ap.add_argument("--after", required=True); ap.add_argument("--before"); ap.add_argument("--png", default=os.path.join(MK, "build", "ui", "out"))
a = ap.parse_args()
fails = []; oks = 0
def check(c, msg):
    global oks
    if c: oks += 1
    else: fails.append(msg); print("FAIL", msg)

class A:
    def __init__(s, p):
        s.ar = mex_hsd.Archive(open(p, "rb").read()); s.d = s.ar.data
    def u32(s, o): return struct.unpack(">I", s.d[o:o+4])[0]
    def u16(s, o): return struct.unpack(">H", s.d[o:o+2])[0]
    def desc_img(s, desc, tl=None):
        w, h = struct.unpack(">HH", s.d[desc+4:desc+8]); fmt = s.u32(desc + 8); p = s.u32(desc)
        lut = None
        if tl: lut = bytes(s.d[s.u32(tl):s.u32(tl) + 2 * s.u16(tl + 0xC)])
        hp = (h + 7) // 8 * 8 if fmt in (0, 8) else h
        return G.decode(bytes(s.d[p:p + G.size_of(fmt, w, hp)]), fmt, w, hp, lut).crop((0, 0, w, h)), (w, h, fmt)
    def ta_frame(s, ta, fr):
        f = s.u32(s.u32(ta + 8) + 8); ii = ti = None
        while f:
            if s.d[f+12] == 1: ii = int(fobj.value_at(s.d, f, fr))
            if s.d[f+12] == 10: ti = int(fobj.value_at(s.d, f, fr))
            f = s.u32(f)
        desc = s.u32(s.u32(ta + 0xC) + 4 * ii); tl = s.u32(s.u32(ta + 0x10) + 4 * ti) if ti is not None else None
        return s.desc_img(desc, tl)
    def ta_last(s, ta):
        f = s.u32(s.u32(ta + 8) + 8); return int(max(k[0] for k in fobj.decode(s.d, f)))
    def key_at(s, ta, fr):
        return fobj.has_key_at(s.d, s.u32(s.u32(ta + 8) + 8), fr)

same = lambda x, y: x.size == y.size and ImageChops.difference(x, y).getbbox() is None
def maxerr(x, y):
    """(mean, max) per-channel texel error over texels either image covers - the GX quantisation cost"""
    x = x.convert("RGBA"); y = y.convert("RGBA")
    e = [max(abs(p - q) for p, q in zip(cx, cy)) for cx, cy in zip(x.getdata(), y.getdata()) if cx[3] > 16 or cy[3] > 16]
    return round(sum(e) / max(1, len(e)), 2), max(e or [0])

def csp(p):
    m = A(p); msc = m.ar.public("mexSelectChr"); return m, m.u32(m.u32(msc + 0x0C) + 8), m.u32(msc + 0x10)
def stock(p):
    f = A(p); stc = f.ar.public("Stc_icns"); r, st = struct.unpack(">HH", f.d[stc:stc+4]); return f, f.u32(f.u32(f.u32(stc + 4) + 8) + 8), r, st
def icon(m, j):
    msc = m.ar.public("mexSelectChr"); kids = []; o = m.u32(m.u32(msc) + 8)
    while o: kids.append(o); o = m.u32(o + 0xC)
    to = m.u32(m.u32(m.u32(m.u32(kids[j - 1] + 0x10) + 4) + 8) + 8)
    return m.desc_img(m.u32(to + 0x4C), m.u32(to + 0x50)), len(kids)
def names(p):
    g = A(p); tas = []
    for o in g.ar.reloc_offsets:
        t = o - 0xC; it = g.u32(o)
        if t < 0 or t + 0x18 > len(g.d) or it + 4 > len(g.d) or o % 4: continue
        first = g.u32(it)
        if first + 12 > len(g.d) or g.u32(first + 8) != 0: continue
        if struct.unpack(">HH", g.d[first+4:first+8]) in ((120, 24), (256, 28)) and 40 < g.u16(t + 0x14) < 100 and g.u32(t + 8): tas.append(t)
    return g, sorted(tas)

AF = lambda n: os.path.join(a.after, n)
# ---- MK's new art
m, ta, stride = csp(AF("MnSlChr.usd"))
for c in range(6):
    im, (w, h, fmt) = m.ta_frame(ta, 51 + c * stride)
    check((w, h, fmt) == (136, 188, 9), "CSP c%d format %s" % (c, (w, h, fmt)))
    e = maxerr(im, Image.open(os.path.join(a.png, "csp_%d.png" % c))); check(e[0] <= 11, "CSP c%d texel err %s" % (c, e))
    print("CSP costume %d: frame %d  %dx%d CI8  texel err vs source mean %.2f max %d" % ((c, 51 + c * stride, w, h) + e))
f, sta, res, sst = stock(AF("IfAll.usd"))
for c in range(6):
    im, (w, h, fmt) = f.ta_frame(sta, res + c * sst + 52)
    check((w, h, fmt) == (24, 24, 8), "stock c%d format" % c)
    e = maxerr(im, Image.open(os.path.join(a.png, "stock_%d.png" % c))); print("stock costume %d: frame %d  24x24 CI4  texel err mean %.2f max %d" % ((c, res + c * sst + 52) + e))
    check(e[0] <= 16, "stock c%d err %s" % (c, e))
(im, (w, h, fmt)), nj = icon(m, 58)
check((w, h, fmt) == (64, 56, 9) and nj == 58, "icon format %s joints %d" % ((w, h, fmt), nj))
e = maxerr(im, Image.open(os.path.join(a.png, "css_icon.png"))); check(e[0] <= 6, "icon err %s" % (e,)); print("CSS icon joint 58: 64x56 CI8 texel err mean %.2f max %d" % e)
g, tas = names(AF("GmRst.usd")); check(len(tas) == 5, "GmRst strips %d" % len(tas))
for t in tas:
    im, (w, h, fmt) = g.ta_frame(t, 51)
    check(fmt == 0 and g.key_at(t, 51), "name 0x%X fmt %d key %s" % (t, fmt, g.key_at(t, 51)))
    e = maxerr(im, Image.open(os.path.join(a.png, "name_%dx%d.png" % (w, h)))); check(e[1] <= 17, "name err %s" % (e,))
    print("GmRst strip 0x%X: frame 51 -> %dx%d I4, key on frame 51, texel err mean %.2f max %d" % ((t, w, h) + e))
    check(not g.key_at(t, 33), "GmRst frame 33 (Brawl Kirby) gained a key")
mx = A(AF("MxDt.dat")); md = mx.d; base = mx.ar.public("mexData"); meta = mx.u32(base); css = mx.u32(mx.u32(base + 4) + 4)
rows = {md[css+0xDC+i*0x1C+1]: md[css+0xDC+i*0x1C+4] for i in range(struct.unpack(">i", md[meta+12:meta+16])[0])}
check(rows[51] == 58 and rows[33] == 57, "icon rows ext51->%s ext33->%s" % (rows.get(51), rows.get(33)))
check(md[mx.u32(mx.u32(base + 8) + 8) + 51] == 5, "insignia[51]")
print("m-ex: CSS icon row ext 51 -> joint %d, ext 33 -> joint %d; insignia[51] = %d" % (rows[51], rows[33], md[mx.u32(mx.u32(base + 8) + 8) + 51]))

# ---- nothing else changed
if a.before:
    BF = lambda n: os.path.join(a.before, n)
    mb, tab, _ = csp(BF("MnSlChr.usd")); n = 0
    mine = {51 + c * stride for c in range(6)}
    for fr in range(0, m.ta_last(ta) + 1):
        if fr in mine: continue
        check(same(mb.ta_frame(tab, fr)[0], m.ta_frame(ta, fr)[0]), "CSP frame %d changed" % fr); n += 1
    print("CSP: %d other frames identical before/after" % n)
    fb, stb, _, _ = stock(BF("IfAll.usd")); n = 0
    mine = {res + c * sst + 52 for c in range(6)}
    for fr in range(0, f.ta_last(sta) + 1):
        if fr in mine: continue
        check(same(fb.ta_frame(stb, fr)[0], f.ta_frame(sta, fr)[0]), "stock frame %d changed" % fr); n += 1
    print("stock: %d other frames identical before/after" % n)
    for j in range(1, 58):
        check(same(icon(mb, j)[0][0], icon(m, j)[0][0]), "icon joint %d changed" % j)
    print("CSS icons: joints 1-57 identical before/after")
    gb = os.path.join(a.before, "GmRst.usd")
    if not os.path.exists(gb):
        open(os.path.join(os.environ.get("TEMP", "."), "_gmrst_disc.usd"), "wb").write(mex_hsd.Gcm("C:/iso/SSBM ACE Build v2.0.0.iso").read("GmRst.usd"))
        gb = os.path.join(os.environ.get("TEMP", "."), "_gmrst_disc.usd")
    g0, tas0 = names(gb); n = 0
    for t0, t in zip(tas0, tas):
        for fr in range(0, g.ta_last(t) + 1):
            if fr == 51: continue
            check(same(g0.ta_frame(t0, fr)[0], g.ta_frame(t, fr)[0]), "GmRst 0x%X frame %d changed" % (t, fr)); n += 1
    print("GmRst: %d other strip frames identical to the base" % n)
# ---- Brawl Kirby's art vs brawl-kirby-slot's own files
kb, kta, kst = csp(os.path.join(BKSLOT, "MnSlChr.usd")); kf, ksta, kres, ksst = stock(os.path.join(BKSLOT, "IfAll.usd"))
for c in range(8):
    fr = 33 + c * kst
    if fr <= m.ta_last(ta): check(same(kb.ta_frame(kta, fr)[0], m.ta_frame(ta, fr)[0]), "BK CSP c%d differs" % c)
    check(same(kf.ta_frame(ksta, kres + c * ksst + 34)[0], f.ta_frame(sta, res + c * sst + 34)[0]), "BK stock c%d differs" % c)
check(same(icon(kb, 57)[0][0], icon(m, 57)[0][0]), "BK icon differs")
print("Brawl Kirby: CSP frames, stock icons (internal 34), icon joint 57 identical to brawl-kirby-slot's files")
# ---- HSDRaw round trip
for n in ("MnSlChr.usd", "IfAll.usd", "GmRst.usd", "MxDt.dat"):
    r = subprocess.run([MB, "roundtrip", AF(n)], capture_output=True, text=True)
    print("  " + r.stdout.strip().splitlines()[0] if r.stdout.strip() else "  " + r.stderr[-300:])
    check(r.returncode == 0, "roundtrip " + n)
print("verify_ui: %d ok, %d fail" % (oks, len(fails)))
sys.exit(1 if fails else 0)
