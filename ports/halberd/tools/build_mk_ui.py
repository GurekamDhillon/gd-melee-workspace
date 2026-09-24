"""Meta Knight's own menu / UI art from Brawl's menu textures, written into the metaknight-slot mod's shared files.

    python tools/build_mk_ui.py --files mods-slot/metaknight-slot/files        (build_mk_slot.py step 3b)

Runs AFTER tools/mk_slot_files.py, which builds MnSlChr.usd / IfAll.usd on top of brawl-kirby-slot's copies and gives
MK's row (internal 52 / external 51) a CSS icon joint and CSP / stock frames that are copies of Kirby's. This replaces
those placeholders. Brawl Kirby's icon joint 57, CSP frames at ext 33 and stock frames at internal 34 are not touched,
and the files do NOT grow (IfAll.usd is loaded into the Stay heap at every match and ACE's copy nearly fills it):

  MnSlChr.usd  CSS icon  MK's icon joint (mk_slot_files' new joint) gets its own DObj/MObj/TObj chain and a 64x56 CI8
                         image: the art window (60x39) is MK cut out of Brawl's CSP at the framing of Brawl's CSS icon
                         (MenSelchrChrFace.022, matched numerically); border and the name band are ACE's own Meta Knight
                         icon's (ext 41), so the label reads the way ACE labels Meta Knight.
               CSP       Brawl's MenSelchrFaceB.211-216 (128x160 CI8) -> 136x188 CI8, written IN PLACE into the replaced
                         row's (ACE "Wolf SSBU") CSP pixel buffer + its 6 TLUTs, ACE's layout: one index map shared by
                         the 6 costumes, one RGB5A3 palette each. Keyed at frames ext + costume * csp_stride. Used by the
                         CSS doors and by the online lobby (mnCharSel_PcArtPortrait -> mnCharSel_MexCspFrame).
  IfAll.usd    stocks    Brawl's InfStc.211-216 (32x32 CI4) -> 24x24 CI4 + 16-entry TLUTs, in place in the replaced row's
                         stock images (costumes whose buffer another fighter shares get paired with one of MK's own:
                         shared index map, own TLUT). Keyed at Stc_icns frames reserved + costume * stride + internal.
  both         keys      the CSP / stock TIMG + TCLT tracks are re-encoded as ONE shared compact stream (the disc's own
                         layout) and every key stream the append-only chain disc -> brawl-kirby-slot -> mk_slot_files left
                         behind is physically removed (Ar.compact: whole 32-byte blocks, pointers / relocs / symbols
                         remapped, nothing may point into a removed block).
  GmRst.usd    names     (new in this mod; base = brawl-kirby-slot's if it ships one, else the disc's) the per-player
                         120x24 and winner-banner 256x28 I4 name strips show Brawl's MK name art (MenSelchrChrNm.211,
                         144x32 I4) at frame = external id 51 (the frame is already keyed to the replaced row's image,
                         which gets its own pixel buffer). With GmRst coming from a mod the port's results screen treats
                         a keyed frame as the fighter's own name (gw_Mex_ResultArtIsOwn + gmRst_ImageKeyAt) and stops
                         drawing MK's name with GDI. Brawl Kirby's ext 33 still has no key, so its drawn name is unchanged.
  MxDt.dat     emblem    checked only: insignia[51] must be 5 (Kirby series; MK's Brawl series).

Costume map (Melee order Nr Ye Bu Re Gr Wh = Brawl costumes 00 05 03 01 02 04, model_anim_ready.md). Brawl's CSS art is
in CSS colour order, not costume-file order: texture .21k (k = 1..6) is costume 00 04 01 02 03 05 (measured: mean colours
of the CSPs / stock icons against the mantle / mask textures of FitMetaknight0X.pac - k=2 cream = 04 white, k=3 red =
01, k=4 green = 02, k=5 dark blue = 03, k=6 pink/orange = 05).
Brawl textures are dumped once with tools/ui/brawl_tex_dump.exe (BrawlLib, 32-bit) into build/ui/brawl/."""
import argparse, json, os, struct, subprocess, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE)
ROOT = r"C:/Users/Gurek/Desktop/GD's Melee"
sys.path.insert(0, ROOT + "/tools/mex_port"); sys.path.insert(0, os.path.join(HERE, "ui"))
import mex_hsd, fobj, gxcodec as G

ISO = "C:/iso/SSBM ACE Build v2.0.0.iso"
BRAWL = "C:/iso/brawl-extract/files"
BKSLOT = os.path.join(os.path.dirname(os.path.dirname(MK)), "experiment", "brawl-kirby", "mods-slot", "brawl-kirby-slot", "files")
SRCDIR = os.path.join(MK, "build", "ui", "brawl")
DUMP = os.path.join(HERE, "ui", "brawl_tex_dump.exe")
MELEE_TO_BRAWL = [0, 5, 3, 1, 2, 4]            # Nr Ye Bu Re Gr Wh -> Brawl costume file
BRAWL_TO_CSS = {0: 1, 4: 2, 1: 3, 2: 4, 3: 5, 5: 6}   # Brawl costume -> .21k texture (CSS colour order)
EXT, INTERNAL, ACE_MK_EXT, INSIGNIA_KIRBY = 51, 52, 41, 5
CSP_SCALE, CSP_TOP = 1.35, 12                  # Brawl bust (rows 4..125 of 128x160) -> Melee 136x188 frame
ICON_FROM_CSP = (0.70, -6, -19)                 # Brawl icon 80x56 = CSP * 0.70 at (-6,-19) (best match, mean err 15/255)

ap = argparse.ArgumentParser()
ap.add_argument("--files", required=True, help="mod files/ folder (MnSlChr.usd, IfAll.usd, MxDt.dat from mk_slot_files.py)")
ap.add_argument("--base", default=BKSLOT, help="folder whose GmRst.usd is the base (default brawl-kirby-slot's; else the disc's)")
ap.add_argument("--png", default=os.path.join(MK, "build", "ui", "out"), help="where the converted art is also written as PNG")
a = ap.parse_args()
os.makedirs(a.png, exist_ok=True)
log = {"sources": {}, "csp": [], "stock": [], "icon": {}, "names": {}}


# ------------------------------------------------------------------ Brawl sources
def brawl_png(sub, name, files, rx):
    p = os.path.join(SRCDIR, sub, name + ".png")
    if not os.path.exists(p):
        subprocess.run([DUMP, os.path.join(SRCDIR, sub), rx] + [os.path.join(BRAWL, f) for f in files], check=True, stdout=subprocess.DEVNULL)
    idx = {e["name"]: e for e in json.load(open(os.path.join(SRCDIR, sub, "index.json")))}
    e = idx[name]; log["sources"][name] = "%s  %s %dx%d %s" % (e["path"], "", e["width"], e["height"], e["format"])
    return Image.open(p).convert("RGBA")

CSPF = ["menu/common/char_bust_tex/MenSelchrFaceB210.brres"]
csp_src = {k: brawl_png("csp", "MenSelchrFaceB.21%d" % k, CSPF, "") for k in range(1, 7)}
stock_src = {k: brawl_png("stock", "InfStc.21%d" % k, ["menu/common/StockFaceTex_en.brres"], "") for k in range(1, 7)}
icon_src = brawl_png("scsel", "MenSelchrChrFace.022", ["menu2/sc_selcharacter_en.pac"], "")
name_src = brawl_png("scsel", "MenSelchrChrNm.211", ["menu2/sc_selcharacter_en.pac"], "")
assert icon_src.size == (80, 56) and name_src.size == (144, 32) and all(i.size == (128, 160) for i in csp_src.values())


def scaled(im, s):
    w, h = round(im.width * s), round(im.height * s)
    return im.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA")


def csp_art(k):
    """Brawl CSP (bust, transparent background, rows 4..125 used) -> 136x188 Melee CSP frame."""
    src = csp_src[k]; s = scaled(src, CSP_SCALE)
    out = Image.new("RGBA", (136, 188), (0, 0, 0, 0))
    ox = -((s.width - 136) // 2); oy = CSP_TOP - round(4 * CSP_SCALE)
    out.paste(s, (ox, oy), s)
    return out


def stock_art(k):
    """Brawl InfStc 32x32 (content 3..29) -> 24x24: the 28x28 centre, scaled 6/7."""
    return stock_src[k].crop((2, 2, 30, 30)).convert("RGBa").resize((24, 24), Image.LANCZOS).convert("RGBA")


def name_art(w, h, top, cap):
    """Brawl's name texture (white on black I4) -> a w x h white-on-black strip, text `cap` rows tall from row `top`."""
    L = name_src.convert("L"); bb = L.point(lambda v: 255 if v > 40 else 0).getbbox()
    t = L.crop(bb); s = cap / t.height
    t = t.resize((max(1, round(t.width * s)), cap), Image.LANCZOS)
    if t.width > w - 4: t = t.resize((w - 4, cap), Image.LANCZOS)
    out = Image.new("L", (w, h), 0); out.paste(t, ((w - t.width) // 2, top))
    return out.convert("RGBA")


# ------------------------------------------------------------------ archive writer
class Ar:
    def __init__(self, path_or_bytes):
        raw = path_or_bytes if isinstance(path_or_bytes, bytes) else open(path_or_bytes, "rb").read()
        self.raw = raw; self.ar = mex_hsd.Archive(raw)
        self.d = bytearray(self.ar.data); self.rel = set(self.ar.reloc_offsets)
    def u32(self, o): return struct.unpack(">I", self.d[o:o+4])[0]
    def u16(self, o): return struct.unpack(">H", self.d[o:o+2])[0]
    def put(self, o, v): self.d[o:o+4] = struct.pack(">I", v)
    def ptr(self, o, v): self.put(o, v); (self.rel.add if v else self.rel.discard)(o)
    def append(self, b, align=0x20):
        while len(self.d) % align: self.d.append(0)
        at = len(self.d); self.d += b; return at
    def clone(self, node, size):
        at = self.append(bytes(self.d[node:node+size]), 4)
        for i in range(0, size, 4):
            if node + i in self.rel: self.rel.add(at + i)
        return at
    remap = staticmethod(lambda o: o)

    def compact(self, ranges):
        """Physically remove dead byte ranges (orphaned key streams / buffers left behind by append-only edits).
        Each range shrinks to whole 32-byte blocks (so every later texture keeps its GX alignment); nothing may point
        into a removed block and no pointer field may live in one (asserted). Pointers, relocations and the public /
        extern symbol offsets are remapped. Returns the bytes removed."""
        blocks = []
        for s, e in ranges:
            s2, e2 = (s + 31) & ~31, e & ~31
            if e2 > s2: blocks.append((s2, e2))
        blocks.sort(); merged = []
        for s, e in blocks:
            if merged and s <= merged[-1][1]: merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
            else: merged.append((s, e))
        inside = lambda o: any(s <= o < e for s, e in merged)
        for o in self.rel:
            assert not inside(o), "a pointer field at 0x%X lies in a removed block" % o
            assert not inside(self.u32(o)), "0x%X points into a removed block (0x%X)" % (o, self.u32(o))
        starts = [s for s, _ in merged]; cum = []; t = 0
        for s, e in merged: t += e - s; cum.append(t)
        import bisect
        def mp(o):
            i = bisect.bisect_right(starts, o) - 1
            return o - (cum[i] if i >= 0 else 0)
        nd = bytearray(); p = 0
        for s, e in merged: nd += self.d[p:s]; p = e
        nd += self.d[p:]
        nrel = set()
        for o in self.rel:
            struct.pack_into(">I", nd, mp(o), mp(self.u32(o))); nrel.add(mp(o))
        prev = self.remap
        self.remap = lambda o, prev=prev, mp=mp: mp(prev(o))
        self.d, self.rel = nd, nrel
        return t

    def save(self, path):
        while len(self.d) % 4: self.d.append(0)
        rel = sorted(self.rel); tail = bytearray(self.raw[self.ar.o_public:])
        for i in range(self.ar.nb_public + self.ar.nb_extern):          # symbol data offsets follow any compaction
            o = struct.unpack(">I", tail[8*i:8*i+4])[0]
            struct.pack_into(">I", tail, 8*i, self.remap(o))
        body = bytes(self.d) + b"".join(struct.pack(">I", x) for x in rel) + bytes(tail)
        open(path, "wb").write(struct.pack(">5I", 0x20 + len(body), len(self.d), len(rel), self.ar.nb_public, self.ar.nb_extern)
                               + self.raw[0x14:0x20] + body)

    def image(self, fmt, w, h, pix, like_desc):
        """new HSD_ImageDesc (a copy of `like_desc` for the LOD fields) over newly appended pixels"""
        assert len(pix) == G.size_of(fmt, w, h), (len(pix), fmt, w, h)
        p = self.append(pix, 0x20); desc = self.clone(like_desc, 0x18)
        self.ptr(desc, p); self.d[desc+4:desc+8] = struct.pack(">HH", w, h); self.put(desc + 8, fmt)
        return desc

    def tlut(self, lut, n, like_tlut):
        p = self.append(lut, 0x20); t = self.clone(like_tlut, 0x10)
        self.ptr(t, p); self.d[t+0xC:t+0xE] = struct.pack(">H", n)
        return t

    def grow_table(self, table, n, extra):
        """copy a pointer table of n entries to the end with `extra` appended -> (new table, first new index)"""
        nt = self.append(bytes(4 * (n + len(extra))), 4)
        for i in range(n): self.ptr(nt + 4 * i, self.u32(table + 4 * i))
        for i, v in enumerate(extra): self.ptr(nt + 4 * (n + i), v)
        return nt, n

    def texanim_add(self, ta, images, tluts):
        """append images (+ tluts) to a TexAnim's tables; returns the first new image / tlut index"""
        ni, nt = self.u16(ta + 0x14), self.u16(ta + 0x16)
        it, i0 = self.grow_table(self.u32(ta + 0xC), ni, images); self.ptr(ta + 0xC, it)
        self.d[ta+0x14:ta+0x16] = struct.pack(">H", ni + len(images))
        t0 = None
        if tluts:
            tt, t0 = self.grow_table(self.u32(ta + 0x10), nt, tluts); self.ptr(ta + 0x10, tt)
            self.d[ta+0x16:ta+0x18] = struct.pack(">H", nt + len(tluts))
        return i0, t0

    def texanim_key(self, ta, frames):
        """frames: {frame: (image index, tlut index or None)} -> constant keys on the TIMG (1) / TCLT (10) tracks"""
        f = self.u32(self.u32(ta + 8) + 8); done = set()
        while f:
            typ = self.d[f + 12]
            if typ == 1: fobj.set_constant(self.d, f, {fr: v[0] for fr, v in frames.items()}); done.add(1)
            if typ == 10 and any(v[1] is not None for v in frames.values()):
                fobj.set_constant(self.d, f, {fr: v[1] for fr, v in frames.items()}); done.add(10)
            f = self.u32(f)
        return done


def save_png(im, name): im.save(os.path.join(a.png, name))


# ------------------------------------------------------------------ MxDt: icon row, stride, emblem
mx = Ar(os.path.join(a.files, "MxDt.dat")); md = mx.d
base = mx.ar.public("mexData"); meta = mx.u32(base); menu = mx.u32(base + 4); css = mx.u32(menu + 4); ft = mx.u32(base + 8)
n_icons = struct.unpack(">i", md[meta+12:meta+16])[0]
rows = {md[css+0xDC+i*0x1C+1]: css + 0xDC + i * 0x1C for i in range(n_icons)}
mk_joint, ace_mk_joint = md[rows[EXT] + 4], md[rows[ACE_MK_EXT] + 4]
insignia = md[mx.u32(ft + 8) + EXT]
assert insignia == INSIGNIA_KIRBY, "insignia[%d] = %d, want %d (Kirby series)" % (EXT, insignia, INSIGNIA_KIRBY)
log["emblem"] = {"insignia[51]": insignia, "note": "Kirby series emblem (MK's Brawl series); ACE's own Meta Knight (ext 41) uses the same"}

# ------------------------------------------------------------------ MnSlChr.usd
m = Ar(os.path.join(a.files, "MnSlChr.usd"))
msc = m.ar.public("mexSelectChr")
kids = []; o = m.u32(m.u32(msc) + 8)
while o: kids.append(o); o = m.u32(o + 0xC)
assert mk_joint == len(kids), ("MK's icon joint should be the last one (mk_slot_files appends it)", mk_joint, len(kids))

def icon_image(joint):
    dob1 = m.u32(m.u32(kids[joint - 1] + 0x10) + 4); to = m.u32(m.u32(dob1 + 8) + 8)
    desc, tl = m.u32(to + 0x4C), m.u32(to + 0x50)
    w, h = struct.unpack(">HH", m.d[desc+4:desc+8]); fmt = m.u32(desc + 8); p = m.u32(desc)
    lut = bytes(m.d[m.u32(tl):m.u32(tl) + 2 * struct.unpack(">H", m.d[tl+0xC:tl+0xE])[0]])
    return G.decode(bytes(m.d[p:p + G.size_of(fmt, w, h)]), fmt, w, h, lut), (dob1, to, desc, tl)

# the art window: texels that differ between the disc's icons (the rest - border, top-right mark - are the template)
from collections import Counter
icons = {}
for j in range(1, len(kids) + 1):
    im, ids = icon_image(j)
    icons.setdefault(ids[2], im)
allicons = list(icons.values())
tmpl_ace, (_, _, like_desc, like_tlut) = icon_image(ace_mk_joint)
window = set()
for y in range(2, 41):                                       # rows 41..51: the name band (kept from ACE's MK icon)
    for x in range(64):
        if Counter(im.getpixel((x, y)) for im in allicons).most_common(1)[0][1] < 0.8 * len(allicons): window.add((x, y))
# MK cut out of Brawl's CSP at the Brawl icon's framing, fitted to the window width (80 -> 60)
s0, ix, iy = ICON_FROM_CSP; fit = 60 / 80.0
cut = scaled(csp_src[BRAWL_TO_CSS[MELEE_TO_BRAWL[0]]], s0 * fit)
art = Image.new("RGBA", (64, 56), (0, 0, 0, 0))
art.paste(cut, (2 + round(ix * fit), 2 + round(iy * fit - (56 * fit - 39) / 2)), cut)   # 42 rows -> 39: centre crop
icon = tmpl_ace.copy()
for (x, y) in window: icon.putpixel((x, y), art.getpixel((x, y)))
save_png(icon, "css_icon.png")
pix, lut, n = G.encode_ci(icon, G.GX_TF_C8)
# own DObj chain for MK's icon joint: dobj0 (frame, shared MObj) -> dobj1 (new MObj -> new TObj -> new image + TLUT)
jo = kids[mk_joint - 1]; dob0 = m.u32(jo + 0x10); dob1 = m.u32(dob0 + 4)
n_dob0, n_dob1 = m.clone(dob0, 0x10), m.clone(dob1, 0x10)
mo = m.u32(dob1 + 8); n_mo = m.clone(mo, 0x18); to = m.u32(mo + 8); n_to = m.clone(to, 0x5C)
n_desc = m.image(G.GX_TF_C8, 64, 56, pix, like_desc); n_tl = m.tlut(lut, n, like_tlut)
m.ptr(n_to + 0x4C, n_desc); m.ptr(n_to + 0x50, n_tl); m.ptr(n_mo + 8, n_to)
m.ptr(n_dob1 + 8, n_mo); m.ptr(n_dob0 + 4, n_dob1); m.ptr(jo + 0x10, n_dob0)
log["icon"] = {"joint": mk_joint, "band_from_icon_joint": ace_mk_joint, "window_texels": len(window), "format": "CI8 64x56",
               "tlut": "RGB5A3 x%d" % n, "desc": "0x%X" % n_desc, "dobj0": "0x%X" % n_dob0}

# ------------------------------------------------------------------ reuse of the replaced row's own art (no growth)
# IfAll.usd is loaded into the Stay heap at a match and ACE's copy already nearly fills the largest free block with two
# big fighters loaded (MK + Brawl Kirby: 1,041,520 B free for a 1,038,580 B IfAll) - 12 KB more and the load fails
# (ALLOC_FAIL heap 3, then a crash). So MK's art goes where the row it replaced (ACE's "Wolf SSBU", internal 52 /
# external 51) kept its own: after mk_slot_files re-keyed those frames to Kirby's, Wolf SSBU's CSP / stock images are
# referenced by nothing. Their pixel / TLUT buffers are rewritten in place (only when no other pointer in the file
# reaches them) and the keys on MK's frames are set back to them in place - the files do not grow. ACE's layout is
# kept: a fighter's costumes share one CSP pixel buffer and differ by TLUT (joint quantisation of the 6 costumes).
def track_values(ar, ta, typ):
    f = ar.u32(ar.u32(ta + 8) + 8)
    while f:
        if ar.d[f + 12] == typ:
            fv = ar.d[f + 13]
            ks = [(int(k[0]), int(fobj._val(k[2], fv))) for k in fobj.decode(ar.d, f) if k[2] is not None]
            return f, ks
        f = ar.u32(f)
    return None, []


def value_at(ks, fr): return [v for t, v in ks if t <= fr][-1]


def refs(ar, target):
    """how many relocated words of the file point at `target`"""
    return sum(1 for o in ar.rel if ar.u32(o) == target)


def reuse_plan(cur, base, ta_cur, ta_base, frames):
    """-> (ok, image indices, tlut indices): what the base file keys on `frames`, ok when `cur` no longer shows them"""
    _, bi = track_values(base, ta_base, 1); _, bt = track_values(base, ta_base, 10)
    _, ci = track_values(cur, ta_cur, 1); _, ct = track_values(cur, ta_cur, 10)
    last = max(t for t, _ in ci)
    imgs = [value_at(bi, fr) for fr in frames]; tls = [value_at(bt, fr) for fr in frames]
    used_i = {value_at(ci, fr) for fr in range(last + 1)}; used_t = {value_at(ct, fr) for fr in range(last + 1)}
    ok = not (set(imgs) & used_i) and not (set(tls) & used_t) and len(set(imgs)) == len(frames) and len(set(tls)) == len(frames)
    return ok, imgs, tls


def base_bytes(name):
    p = os.path.join(BKSLOT, name)
    return open(p, "rb").read() if os.path.exists(p) else mex_hsd.Gcm(ISO).read(name)


def desc_of(ar, ta, i): return ar.u32(ar.u32(ta + 0xC) + 4 * i)
def tlut_of(ar, ta, i): return ar.u32(ar.u32(ta + 0x10) + 4 * i)


def set_keys(ar, ta, frames_img, frames_tl):
    for typ, fv in ((1, frames_img), (10, frames_tl)):
        f, _ = track_values(ar, ta, typ)
        if not fobj.set_inplace(ar.d, f, fv):
            fobj.set_constant(ar.d, f, fv); log.setdefault("grew", []).append("key stream type %d re-encoded (appended)" % typ)


def write_tlut(ar, t, lut, n):
    """TLUT data in place when only this TLUT desc points at it and it holds n entries, else a new buffer"""
    tp = ar.u32(t)
    if refs(ar, tp) == 1 and struct.unpack(">H", ar.d[t+0xC:t+0xE])[0] == n:
        ar.d[tp:tp + len(lut)] = lut; return "in place"
    ar.ptr(t, ar.append(lut, 0x20)); ar.d[t+0xC:t+0xE] = struct.pack(">H", n); return "new buffer"


def stream_ranges(raw_or_ar, locate):
    """(start, end) of every FObj key stream of the TexAnim `locate(ar)` in a file (a version this file was built from:
    the edits are append-only, so its offsets are this file's offsets)."""
    ar = raw_or_ar if isinstance(raw_or_ar, Ar) else Ar(raw_or_ar)
    ta = locate(ar); f = ar.u32(ar.u32(ta + 8) + 8); out = set()
    while f: out.add((ar.u32(f + 16), ar.u32(f + 16) + ar.u32(f + 4))); f = ar.u32(f)
    return out


def consolidate(ar, locate, history):
    """Re-encode the TexAnim's constant TIMG / TCLT tracks compactly - ONE shared stream when both select the same
    index on every frame, as the disc's own file does - and physically remove every key stream the chain of append-only
    edits (disc -> brawl-kirby-slot -> mk_slot_files -> here) left behind. Returns (stream bytes, bytes removed)."""
    ta = locate(ar); tracks = {}; f = ar.u32(ar.u32(ta + 8) + 8)
    while f: tracks[ar.d[f + 12]] = f; f = ar.u32(f)
    dead = set(history) | stream_ranges(ar, locate)
    keys = {t: fobj.constant_keys(ar.d, fo) for t, fo in tracks.items()}
    shared = len(tracks) == 2 and keys[1] == keys[10] and ar.d[tracks[1] + 13] == ar.d[tracks[10] + 13]
    written = {}
    for t, fo in sorted(tracks.items()):
        k = 1 if shared else t
        if k not in written:
            s = fobj.encode_constant(keys[k], ar.d[fo + 13]); written[k] = (ar.append(s, 4), len(s))
        pos, ln = written[k]
        ar.put(fo + 16, pos); ar.put(fo + 4, ln)
    removed = ar.compact(dead)
    return sum(l for _, l in written.values()), removed, shared


# CSPs
ta = m.u32(m.u32(msc + 0x0C) + 8); stride = m.u32(msc + 0x10)
mb = Ar(base_bytes("MnSlChr.usd")); tab = mb.u32(mb.u32(mb.ar.public("mexSelectChr") + 0x0C) + 8)
frames = [EXT + c * stride for c in range(6)]
ok, imgs, tls = reuse_plan(m, mb, ta, tab, frames)
arts = [csp_art(BRAWL_TO_CSS[b]) for b in MELEE_TO_BRAWL]
for c, im in enumerate(arts): save_png(im, "csp_%d.png" % c)
descs = [desc_of(m, ta, i) for i in imgs]
bufs = {m.u32(d) for d in descs}
if ok and len(bufs) == 1 and refs(m, next(iter(bufs))) == len(descs) and \
        all(struct.unpack(">HHI", m.d[d+4:d+12]) == (136, 188, 9) for d in descs):
    pix, luts, n = G.encode_ci_joint(arts, G.GX_TF_C8)
    buf = next(iter(bufs)); m.d[buf:buf + len(pix)] = pix
    how = [write_tlut(m, tlut_of(m, ta, t), luts[c], n) for c, t in enumerate(tls)]
    mode = "in place: the replaced row's shared CSP buffer 0x%X + its 6 TLUTs (%s); one index map, 6 palettes" % (buf, ", ".join(sorted(set(how))))
else:                                              # fallback: new images + TLUTs appended to the tables
    new_d, new_t = [], []
    for im in arts:
        pix, lut, n = G.encode_ci(im, G.GX_TF_C8)
        new_d.append(m.image(G.GX_TF_C8, 136, 188, pix, desc_of(m, ta, 0))); new_t.append(m.tlut(lut, n, tlut_of(m, ta, 0)))
    i0, t0 = m.texanim_add(ta, new_d, new_t); imgs = [i0 + c for c in range(6)]; tls = [t0 + c for c in range(6)]
    mode = "appended (the replaced row's CSPs are shared or still used)"; log.setdefault("grew", []).append("MnSlChr CSPs appended")
set_keys(m, ta, {fr: imgs[c] for c, fr in enumerate(frames)}, {fr: tls[c] for c, fr in enumerate(frames)})
log["csp"] = {"mode": mode, "frames": [{"costume": c, "brawl": "MenSelchrFaceB.21%d (costume %02d)" % (BRAWL_TO_CSS[b], b),
              "frame": frames[c], "image": imgs[c], "tlut": tls[c], "format": "CI8 136x188"} for c, b in enumerate(MELEE_TO_BRAWL)]}
loc_csp = lambda x: x.u32(x.u32(x.ar.public("mexSelectChr") + 0x0C) + 8)
hist = stream_ranges(mex_hsd.Gcm(ISO).read("MnSlChr.usd"), loc_csp) | stream_ranges(mb, loc_csp)
size0 = len(m.raw); sl, removed, shared = consolidate(m, loc_csp, hist)
m.save(os.path.join(a.files, "MnSlChr.usd"))
log["csp"]["keys"] = "one %s key stream (%d B); %d B of orphaned key streams removed" % ("shared TIMG/TCLT" if shared else "per-track", sl, removed)

# ------------------------------------------------------------------ IfAll.usd stock icons
f = Ar(os.path.join(a.files, "IfAll.usd")); size0 = len(f.raw)
stc = f.ar.public("Stc_icns"); reserved, sstride = struct.unpack(">HH", f.d[stc:stc+4])
ta = f.u32(f.u32(f.u32(stc + 4) + 8) + 8)
fb = Ar(base_bytes("IfAll.usd")); stb = fb.ar.public("Stc_icns"); tab = fb.u32(fb.u32(fb.u32(stb + 4) + 8) + 8)
frames = [reserved + c * sstride + INTERNAL for c in range(6)]
ok, imgs, tls = reuse_plan(f, fb, ta, tab, frames)
arts = [stock_art(BRAWL_TO_CSS[b]) for b in MELEE_TO_BRAWL]
for c, im in enumerate(arts): save_png(im, "stock_%d.png" % c)
descs = [desc_of(f, ta, i) for i in imgs]
assert ok and all(struct.unpack(">HHI", f.d[d+4:d+12]) == (24, 24, 8) for d in descs), "stock reuse impossible: %s" % imgs
excl = [c for c, d in enumerate(descs) if refs(f, f.u32(d)) == 1]          # pixel buffers only this desc reaches
share = [c for c in range(6) if c not in excl]
assert len(share) <= len(excl), (excl, share)
groups = [[c] for c in excl[:len(excl) - len(share)]] + [[e, s] for e, s in zip(excl[len(excl) - len(share):], share)]
how = []
for grp in groups:
    if len(grp) > 1:
        pix, luts, n = G.encode_ci_joint([arts[c] for c in grp], G.GX_TF_C4)
    else:
        pix, lut, n = G.encode_ci(arts[grp[0]], G.GX_TF_C4); luts = [lut]
    buf = f.u32(descs[grp[0]]); f.d[buf:buf + len(pix)] = pix
    for i, c in enumerate(grp):
        if c != grp[0]: f.put(descs[c], buf)                                # same relocated field, new target
        how.append(write_tlut(f, tlut_of(f, ta, tls[c]), luts[i], n))
set_keys(f, ta, {fr: imgs[c] for c, fr in enumerate(frames)}, {fr: tls[c] for c, fr in enumerate(frames)})
loc_stc = lambda x: x.u32(x.u32(x.u32(x.ar.public("Stc_icns") + 4) + 8) + 8)
hist = stream_ranges(mex_hsd.Gcm(ISO).read("IfAll.usd"), loc_stc) | stream_ranges(fb, loc_stc)
sl, removed, shared = consolidate(f, loc_stc, hist)
f.save(os.path.join(a.files, "IfAll.usd"))
keys_note = "one %s key stream (%d B); %d B of orphaned key streams removed" % ("shared TIMG/TCLT" if shared else "per-track", sl, removed)
log["stock"] = {"mode": "in place: the replaced row's stock images; pixel buffers per costume group %s (a group shares one index map, "
                        "own TLUTs); TLUTs %s" % (groups, ", ".join(sorted(set(how)))),
                "size": "%d -> %d B" % (size0, os.path.getsize(os.path.join(a.files, "IfAll.usd"))), "keys": keys_note,
                "frames": [{"costume": c, "brawl": "InfStc.21%d (costume %02d)" % (BRAWL_TO_CSS[b], b), "frame": frames[c],
                            "image": imgs[c], "tlut": tls[c], "format": "CI4 24x24"} for c, b in enumerate(MELEE_TO_BRAWL)]}

# ------------------------------------------------------------------ GmRst.usd name strips
bp = os.path.join(a.base, "GmRst.usd") if a.base else None
g = Ar(open(bp, "rb").read() if bp and os.path.exists(bp) else mex_hsd.Gcm(ISO).read("GmRst.usd"))
log["names"]["base"] = bp if bp and os.path.exists(bp) else "disc"
tas = {}
for o in g.ar.reloc_offsets:                     # TexAnims whose image table holds I4 name strips
    t = o - 0xC; it = g.u32(o)
    if t < 0 or t + 0x18 > len(g.d) or it + 4 > len(g.d) or o % 4: continue
    first = g.u32(it)
    if first + 12 > len(g.d) or g.u32(first + 8) != 0: continue
    wh = struct.unpack(">HH", g.d[first+4:first+8])
    n = g.u16(t + 0x14)
    if wh in ((120, 24), (256, 28)) and 40 < n < 100 and g.u32(t + 8): tas[t] = wh
assert sorted(tas.values()).count((120, 24)) == 4 and list(tas.values()).count((256, 28)) == 1, tas
# frame 51 is keyed to the replaced row's name image, whose pixels it shares with ACE's own Wolf: that image desc gets
# its own new pixel buffer when frame 51 is the only frame showing it (else a new image in the table)
enc = {}
for wh, (top, cap) in (((120, 24), (4, 16)), ((256, 28), (1, 26))):
    w, h = wh; hp = (h + 7) // 8 * 8
    im = name_art(w, hp, top, cap)
    for y in range(h, hp):
        for x in range(w): im.putpixel((x, y), (0, 0, 0, 255))
    save_png(im.crop((0, 0, w, h)), "name_%dx%d.png" % wh)
    enc[wh] = [G.encode_i4(im), hp, None]
for t, wh in sorted(tas.items()):
    _, ks = track_values(g, t, 1)
    img = value_at(ks, EXT); desc = desc_of(g, t, img)
    only = [fr for fr in range(max(k for k, _ in ks) + 1) if value_at(ks, fr) == img] == [EXT] and any(k == EXT for k, _ in ks)
    same_size = struct.unpack(">HHI", g.d[desc+4:desc+12]) == (wh[0], wh[1], 0)
    pix, hp, buf = enc[wh]
    if only and same_size:
        if buf is None: buf = enc[wh][2] = g.append(pix, 0x20)
        g.ptr(desc, buf); mode = "image %d (desc 0x%X) -> own new buffer 0x%X" % (img, desc, buf)
    else:
        nd = g.image(G.GX_TF_I4, wh[0], hp, pix, desc); g.d[nd+6:nd+8] = struct.pack(">H", wh[1])
        it = g.u32(t + 0xC); n = g.u16(t + 0x14); nt, img = g.grow_table(it, n, [nd])
        g.ptr(t + 0xC, nt); g.d[t+0x14:t+0x16] = struct.pack(">H", n + 1)
        f_, _ = track_values(g, t, 1); fobj.set_constant(g.d, f_, {EXT: img}); mode = "new image %d" % img
    log["names"]["texanim 0x%X" % t] = {"size": "%dx%d I4" % wh, "frame": EXT, "image": img, "mode": mode}
g.save(os.path.join(a.files, "GmRst.usd"))

print(json.dumps(log, indent=1))
