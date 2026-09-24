"""Brand / marketing kit for GD's Melee, in the menu kit's visual language.

    python pipeline/build_brand.py      -> out_brand/ (wiped and rebuilt every run)

Everything is SVG built here (text is converted to outlines with fontTools from the
kit's OFL fonts, so every SVG is self-contained), then rasterised by headless
Chromium. Original art only: no Nintendo/HAL logos, lettering, characters, stages or
screenshots, and nothing traced, recoloured or sampled from them.

Visual language, same as the kit and the README art: one shear (skewX -14.036deg,
the kit's S = 0.25), flat colour, hard ink shadows at a fixed offset, cobalt faces,
gold for emphasis, bone text. The key art adds abstract motifs only: speed lines,
an impact burst, a stack of frames rewinding (rollback) and a P1-P2 link (netplay).

Words live in pipeline/brand_text.json.
"""
import io
import json
import math
import os
import random
import shutil
import sys

from PIL import Image
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit                                                  # noqa: E402
import icons as I                                           # noqa: E402
import readme as R                                          # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_brand")
TEXT = json.load(open(os.path.join(HERE, "brand_text.json"), encoding="utf-8"))
PAL = kit.PALETTE
VS = kit.SECTIONS["versus"]
T = 0.25                                  # tan(14.036deg): the kit's shear
SKEW = -14.036

C = dict(
    ink=PAL["ink"], bone=PAL["bone"], muted=PAL["muted"], gold=PAL["gold"],
    gold_lt=PAL["gold_lt"], gold_dk=PAL["gold_dk"], danger=PAL["danger"], ok=PAL["ok"],
    night=VS["bg"], band=VS["band"], cobalt=VS["face"], cobalt_lt="#2f55b8",
    cobalt_hi="#4a7ae0", lilac=VS["face_hi"], cobalt_dk="#14265c",
    p1=kit.PORTS["p1"], p2=kit.PORTS["p2"], paper="#f2efe4", white="#ffffff",
)


# ============================================================ text -> outlines
class Face:
    def __init__(self, path):
        self.f = TTFont(path, lazy=True)
        self.gs = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.upem = self.f["head"].unitsPerEm
        self.hmtx = self.f["hmtx"]
        self.cap = self.f["OS/2"].sCapHeight / self.upem

    def _g(self, ch):
        return self.cmap.get(ord(ch), ".notdef")

    def width(self, text, size, track=0.0):
        s = size / self.upem
        return sum(self.hmtx[self._g(c)][0] for c in text) * s + track * max(0, len(text) - 1)

    def d(self, text, size, x=0.0, y=0.0, track=0.0):
        s = size / self.upem
        out, cx = [], x
        for ch in text:
            g = self._g(ch)
            pen = SVGPathPen(self.gs, ntos=lambda v: ("%.2f" % v).rstrip("0").rstrip("."))
            self.gs[g].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
            out.append(pen.getCommands())
            cx += self.hmtx[g][0] * s + track
        return " ".join(out)


FACES = {}


def face(k):
    if k not in FACES:
        FACES[k] = Face(os.path.join(ROOT, {
            "black": "SourceSans3/SourceSans3-Black.otf",
            "bold": "SourceSans3/SourceSans3-Bold.otf",
            "mono": "Hasklug/HasklugNerdFont-Bold.otf"}[k]))
    return FACES[k]


def text(s, size, x, y, fill, f="black", track=0.0, anchor="start", extra=""):
    """Outlined text; y is the baseline."""
    fc = face(f)
    w = fc.width(s, size, track)
    x0 = x - {"start": 0, "middle": w / 2, "end": w}[anchor]
    return '<path d="%s" fill="%s"%s/>' % (fc.d(s, size, x0, y, track), fill, extra), w


def tw(s, size, f="black", track=0.0):
    return face(f).width(s, size, track)


# ============================================================ svg helpers
_uid = [0]


def uid(p):
    _uid[0] += 1
    return "%s%d" % (p, _uid[0])


def svg(w, h, body, bg=None, vb=None):
    vb = vb or (0, 0, w, h)
    back = '<rect x="%g" y="%g" width="%g" height="%g" fill="%s"/>' % (vb[0], vb[1], vb[2], vb[3], bg) \
        if bg else ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%g %g %g %g">'
            '%s%s</svg>' % (w, h, vb[0], vb[1], vb[2], vb[3], back, body))


def sk(x, y, inner, s=1.0):
    """Shear about the local baseline y=0, then place at (x, y)."""
    return '<g transform="translate(%.2f %.2f) scale(%g) skewX(%g)">%s</g>' % (x, y, s, SKEW, inner)


def para(x, y, w, h):
    """Sheared parallelogram, (x,y) is the unsheared top-left, sheared about the bottom."""
    o = h * T
    return "M%.2f %.2f H%.2f L%.2f %.2f H%.2f Z" % (x + o, y, x + w + o, x + w, y + h, x)


def poly(pts):
    return "M" + " L".join("%.2f %.2f" % p for p in pts) + " Z"


def G(inner, t="", op=None):
    return '<g%s%s>%s</g>' % (' transform="%s"' % t if t else "",
                              ' opacity="%g"' % op if op is not None else "", inner)


# ============================================================ logo system
LOGO_VARIANTS = {
    #          MELEE      shadow     tag fill   tag text  tile      tile text
    "dark":  (C["bone"], C["ink"], C["gold"], C["ink"], C["gold"], C["ink"]),
    "light": (C["cobalt"], C["ink"], C["gold"], C["ink"], C["gold"], C["ink"]),
    "white": (C["white"], None, C["white"], None, C["white"], None),
    "black": (C["ink"], None, C["ink"], None, C["ink"], None),
}


def knock(shape_d, text_d, fill):
    """shape with the text cut out (for the one-colour versions)."""
    m = uid("ko")
    return ('<mask id="%s" maskUnits="userSpaceOnUse" x="-5000" y="-5000" width="10000" '
            'height="10000"><rect x="-5000" y="-5000" width="10000" height="10000" fill="#fff"/>'
            '<path d="%s" fill="#000"/></mask><path d="%s" fill="%s" mask="url(#%s)"/>'
            % (m, text_d, shape_d, fill, m))


def tag_box(label, size, x, base, v):
    """A gold plate carrying `label` (Black, caps), bottom-left at (x, base). Unsheared
    coords; the caller shears. Returns (svg, w, h)."""
    word, sh, tagf, tagt = v[0], v[1], v[2], v[3]
    cap = face("black").cap * size
    px, py = size * 0.30, size * 0.17
    w = tw(label, size, track=size * 0.02) + 2 * px
    h = cap + 2 * py
    box = poly([(x, base - h), (x + w, base - h), (x + w, base), (x, base)])
    td = face("black").d(label, size, x + px, base - py, size * 0.02)
    out = ""
    if sh:
        o = size * 0.10
        out += '<path d="%s" fill="%s" transform="translate(%g %g)"/>' % (box, sh, o, o)
        out += '<path d="%s" fill="%s"/><path d="%s" fill="%s"/>' % (box, tagf, td, tagt)
    else:
        out += knock(box, td, tagf)
    return out, w, h


def wordmark(v, N=200):
    """Primary wordmark: GD'S on a plate above MELEE. Local coords: MELEE baseline at
    y=0, left at x=0, sheared. Returns (svg, bbox) with bbox in the sheared space."""
    word, sh = v[0], v[1]
    fc = face("black")
    track = N * 0.012
    wm = fc.width("MELEE", N, track)
    capN = fc.cap * N
    d = fc.d("MELEE", N, 0, 0, track)
    s = ""
    o = N * 0.05
    if sh:
        s += '<path d="%s" fill="%s" transform="translate(%g %g)"/>' % (d, sh, o, o)
    s += '<path d="%s" fill="%s"/>' % (d, word)
    tag, tw_, th = tag_box("GD'S", N * 0.34, N * 0.03, -capN - N * 0.09, v)
    s = tag + s
    top = -capN - N * 0.09 - th
    bot = o if sh else 0
    bbox = (-T * bot, top, wm + T * (-top) + (o if sh else 0), bot)
    return '<g transform="skewX(%g)">%s</g>' % (SKEW, s), bbox


def wordmark_inline(v, N=200):
    """One line: [GD'S] MELEE, the plate at MELEE's cap height."""
    word, sh = v[0], v[1]
    fc = face("black")
    capN = fc.cap * N
    tsize = capN / (face("black").cap + 0.34)          # plate height == MELEE cap height
    tag, twid, th = tag_box("GD'S", tsize, 0, 0, v)
    gap = N * 0.14
    track = N * 0.012
    d = fc.d("MELEE", N, twid + gap, 0, track)
    wm = twid + gap + fc.width("MELEE", N, track)
    o = N * 0.05
    s = tag
    if sh:
        s += '<path d="%s" fill="%s" transform="translate(%g %g)"/>' % (d, sh, o, o)
    s += '<path d="%s" fill="%s"/>' % (d, word)
    bot = o if sh else 0
    bbox = (-T * bot, -capN, wm + T * capN + (o if sh else 0), bot)
    return '<g transform="skewX(%g)">%s</g>' % (SKEW, s), bbox


def monogram(v, H=100, small=False, chamfer=True):
    """The mark: GD on a gold sheared tile with a chamfered corner and ink shadow.
    `small` drops the shear/chamfer/shadow and maximises the letters (16-32 px)."""
    tilef, tilet, sh = v[4], v[5], v[1]
    fc = face("black")
    if small:
        W = H
        box = poly([(0, 0), (W, 0), (W, H), (0, H)])
        size = H * 0.80
        tr = -H * 0.02
        w = fc.width("GD", size, tr)
        td = fc.d("GD", size, (W - w) / 2, H / 2 + fc.cap * size / 2, tr)
        if tilet:
            return ('<path d="%s" fill="%s"/><path d="%s" fill="%s"/>' % (box, tilef, td, tilet),
                    (0, 0, W, H))
        return knock(box, td, tilef), (0, 0, W, H)
    W = H * 1.18
    o = H * T
    c = H * 0.22 if chamfer else 0
    # sheared tile, chamfer at the top-right
    pts = [(o, 0), (o + W - c, 0), (o + W - c * T, c), (W, H), (0, H)]
    box = poly(pts)
    size = H * 0.86
    tr = -H * 0.015
    w = fc.width("GD", size, tr)
    cx = W / 2 + o / 2
    base = H / 2 + fc.cap * size / 2
    # letters are sheared too, about their baseline; skewX pushes the cap middle
    # right by T*cap/2, so pull it back to sit on the tile's centre line
    td_raw = fc.d("GD", size, cx - w / 2, 0, tr)
    tx = -T * (base - H / 2)
    so = H * 0.08
    s = ""
    if sh:
        s += '<path d="%s" fill="%s" transform="translate(%g %g)"/>' % (box, sh, so, so)
    if tilet:
        s += '<path d="%s" fill="%s"/>' % (box, tilef)
        s += '<g transform="translate(%g %g) skewX(%g)"><path d="%s" fill="%s"/></g>' % (
            tx, base, SKEW, td_raw, tilet)
    else:
        m = uid("km")
        s += ('<mask id="%s" maskUnits="userSpaceOnUse" x="-500" y="-500" width="3000" height="3000">'
              '<rect x="-500" y="-500" width="3000" height="3000" fill="#fff"/>'
              '<g transform="translate(%g %g) skewX(%g)"><path d="%s" fill="#000"/></g></mask>'
              '<path d="%s" fill="%s" mask="url(#%s)"/>'
              % (m, tx, base, SKEW, td_raw, box, tilef, m))
    return s, (0, 0, W + o + (so if sh else 0), H + (so if sh else 0))


def place(comp, x, y, w=None, h=None):
    """Scale comp (svg, bbox) to width w or height h, with its bbox top-left at (x, y)."""
    s_, (x0, y0, x1, y1) = comp
    sc = (w / (x1 - x0)) if w else (h / (y1 - y0)) if h else 1.0
    return ('<g transform="translate(%.2f %.2f) scale(%.4f) translate(%.2f %.2f)">%s</g>'
            % (x, y, sc, -x0, -y0, s_), (x1 - x0) * sc, (y1 - y0) * sc)


def logo_lockup(kind, v):
    """-> (svg body, width, height), tight + clear-space padding."""
    if kind == "wordmark":
        comp = wordmark(v)
        body, w, h = place(comp, 0, 0, h=300)
    elif kind == "monogram":
        body, w, h = place(monogram(v), 0, 0, h=300)
    elif kind == "horizontal":
        m, mw, mh = place(monogram(v), 0, 0, h=200)
        wi, ww, wh = place(wordmark_inline(v), mw + 60, 200 - 170 - 12, h=170 + 12 * 0)
        body, w, h = m + wi, mw + 60 + ww, 200
    elif kind == "stacked":
        wm, ww, wh = place(wordmark(v), 0, 0, w=900)
        m, mw, mh = place(monogram(v), 0, 0, h=260)
        body = G(m, "translate(%g 0)" % ((900 - mw) / 2)) + G(wm, "translate(0 %g)" % (mh + 50))
        w, h = 900, mh + 50 + wh
    else:
        raise KeyError(kind)
    pad = 40
    return G(body, "translate(%d %d)" % (pad, pad)), w + 2 * pad, h + 2 * pad


# ============================================================ glyphs for emoji / badges
def _glyph_body(name):
    c, r, rr, P, S = I.circle, I.rect, I.rrect, I.P, I.S
    if name in ("rollback", "replay", "mex", "hd", "sync"):
        return R._body(name)
    if name == "netplay":
        return I.ICONS["ico_online"]["body"]
    if name == "win":
        return (P("M16 4 H48 V20 A16 16 0 0 1 16 20 Z") +
                S("M17 9 H7 V15 A10 10 0 0 0 19 27 M47 9 H57 V15 A10 10 0 0 1 45 27", 5) +
                P(r(28, 34, 8, 12)) + P(r(16, 46, 32, 12)))
    if name == "lobby":
        return (P(c(20, 18, 10)) + P(c(44, 18, 10)) +
                P("M2 60 C2 42 10 33 20 33 C30 33 34 40 36 46 C38 40 42 33 44 33 C54 33 62 42 "
                  "62 60 Z"))
    if name == "strikes":
        return (P(r(4, 46, 56, 9)) + P("M14 55 L20 62 H44 L50 55 Z") +
                S("M16 4 L48 36 M48 4 L16 36", 9))
    if name == "bugs":
        return (P(rr(18, 20, 28, 40, 14)) + P(c(32, 13, 9)) +
                S("M18 30 H5 M18 42 H5 M46 30 H59 M46 42 H59 M20 54 L10 62 M44 54 L54 62 "
                  "M26 6 L20 1 M38 6 L44 1", 5))
    if name == "announce":
        return (P("M6 22 H20 L48 6 V58 L20 42 H6 Z") + P("M14 42 H26 L30 60 H20 Z") +
                S("M54 20 L62 14 M55 32 H63 M54 44 L62 50", 5))
    if name == "pc":
        return P(rr(4, 6, 56, 38, 3)) + P(r(26, 44, 12, 8)) + P(r(14, 52, 36, 7))
    if name == "tag":
        return dict(shape=P("M4 8 H34 L60 34 L34 60 L4 30 Z"), knock=P(c(18, 22, 6)))
    if name == "chat":
        return dict(shape=P("M4 8 H60 V44 H30 L14 58 V44 H4 Z"),
                    knock=P(c(20, 26, 5)) + P(c(32, 26, 5)) + P(c(44, 26, 5)))
    if name == "download":
        return P("M24 4 H40 V26 H54 L32 50 L10 26 H24 Z") + P(r(6, 54, 52, 8))
    raise KeyError(name)


def glyph(name, colour, x, y, px):
    b = _glyph_body(name)
    s = px / 64.0
    if isinstance(b, dict):
        m = uid("gk")
        inner = ('<mask id="%s" maskUnits="userSpaceOnUse" x="-2" y="-2" width="68" height="68">'
                 '<rect x="-2" y="-2" width="68" height="68" fill="#fff"/><g fill="#000" '
                 'stroke="#000">%s</g></mask><g fill="%s" mask="url(#%s)">%s</g>'
                 % (m, b["knock"].replace('fill="#fff"', 'fill="#fff"'), colour, m, b["shape"]))
    else:
        inner = '<g fill="%s">%s</g>' % (colour, b.replace('stroke="#fff"', 'stroke="%s"' % colour))
    return '<g transform="translate(%.2f %.2f) scale(%.4f)">%s</g>' % (x, y, s, inner)


# ============================================================ key-art motifs
def speed_lines(rng, cx, cy, W, H, n=90, r0=260, cols=None):
    cols = cols or [(C["lilac"], 0.16), (C["cobalt_hi"], 0.22), (C["gold"], 0.30), (C["bone"], 0.12)]
    out = []
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi)
        ra = r0 * rng.uniform(1.05, 1.9)
        L = rng.uniform(0.25, 0.9) * max(W, H)
        th = rng.uniform(2, 11)
        col, op = cols[0] if i % 5 in (0, 1) else cols[1] if i % 5 == 2 else cols[2] if i % 5 == 3 else cols[3]
        ca, sa = math.cos(a), math.sin(a)
        nx, ny = -sa, ca
        p0 = (cx + ca * ra, cy + sa * ra)
        p1 = (cx + ca * (ra + L), cy + sa * (ra + L))
        pts = [p0, (p1[0] + nx * th, p1[1] + ny * th), (p1[0] - nx * th, p1[1] - ny * th)]
        out.append('<path d="%s" fill="%s" opacity="%g"/>' % (poly(pts), col, op))
    return "".join(out)


def burst(rng, cx, cy, R, n=14, squash=0.86):
    pts = []
    for i in range(2 * n):
        a = i * math.pi / n + rng.uniform(-0.08, 0.08)
        r = R * (rng.uniform(0.86, 1.12) if i % 2 == 0 else rng.uniform(0.50, 0.60))
        pts.append((math.cos(a) * r, math.sin(a) * r * squash))

    def layer(k, col, dx=0, dy=0):
        return '<path d="%s" fill="%s"/>' % (poly([(cx + x * k + dx, cy + y * k + dy) for x, y in pts]), col)
    sh = R * 0.05
    return (layer(1.0, C["ink"], sh, sh) + layer(1.0, C["gold"]) + layer(0.70, C["gold_lt"]) +
            layer(0.40, C["bone"]))


def frames(cx, cy, fw, fh, n=5, dx=110, dy=-78, labels=True, stroke=6):
    """A stack of sheared frames receding up-right from (cx, cy): the rollback motif.
    Drawn oldest first so the newest sits on top."""
    out = []
    ops = [1.0, 0.72, 0.5, 0.34, 0.22, 0.14]
    for i in reversed(range(n)):
        x = cx + dx * i - fw / 2
        y = cy + dy * i - fh / 2
        op = ops[min(i, len(ops) - 1)]
        d = para(x, y, fw, fh)
        out.append('<path d="%s" fill="%s" opacity="%g"/>' % (d, C["cobalt"], 0.55 * op + 0.1))
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%g" opacity="%g" '
                   'stroke-linejoin="miter"/>' % (d, C["lilac"] if i else C["bone"], stroke, op))
        if labels:
            t, _ = text("F-%d" % i if i else "F 0", fh * 0.13, x + fh * T + fw - fh * 0.08, y + fh * 0.19,
                        C["gold"] if i else C["gold_lt"], "mono", anchor="end")
            out.append(G(t, op=op))
    return "".join(out)


def rewind_arc(cx, cy, r, a0, a1, w, col):
    """A thick arc arrow bending back (the rollback arrow), counter-clockwise a0 -> a1 (deg)."""
    p = lambda a, rr: (cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a)))
    x0, y0 = p(a0, r)
    x1, y1 = p(a1, r)
    large = 1 if abs(a1 - a0) > 180 else 0
    arc = '<path d="M%.1f %.1f A%g %g 0 %d 0 %.1f %.1f" fill="none" stroke="%s" stroke-width="%g"/>' % (
        x0, y0, r, r, large, x1, y1, col, w)
    # arrow head at the end, pointing along the counter-clockwise tangent
    ta = math.radians(a1)
    tx, ty = math.sin(ta), -math.cos(ta)
    nx, ny = math.cos(ta), math.sin(ta)
    hl, hw = w * 2.2, w * 1.7
    tip = (x1 + tx * hl, y1 + ty * hl)
    head = poly([tip, (x1 + nx * hw, y1 + ny * hw), (x1 - nx * hw, y1 - ny * hw)])
    return arc + '<path d="%s" fill="%s"/>' % (head, col)


def port_chip(x, y, label, col, h=64):
    w = h * 1.55
    d = para(x, y, w, h)
    t, _ = text(label, h * 0.62, x + w / 2 + h * T / 2, y + h * 0.5 + face("black").cap * h * 0.31,
                C["bone"], anchor="middle")
    return ('<path d="%s" fill="%s" transform="translate(%g %g)"/>' % (d, C["ink"], h * 0.1, h * 0.1) +
            '<path d="%s" fill="%s"/>' % (d, col) + t)


def link(p1, p2, col, w=6, packets=4):
    """Netplay link: a stepped dashed path with square packets riding it."""
    (x0, y0), (x1, y1) = p1, p2
    mx = (x0 + x1) / 2
    pts = [(x0, y0), (mx, y0), (mx, y1), (x1, y1)]
    d = "M" + " L".join("%.1f %.1f" % p for p in pts)
    out = ['<path d="%s" fill="none" stroke="%s" stroke-width="%g" stroke-dasharray="%g %g"/>'
           % (d, col, w, w * 3, w * 2)]
    segs = [(pts[i], pts[i + 1]) for i in range(3)]
    lens = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs]
    tot = sum(lens)
    for k in range(packets):
        t = tot * (k + 0.5) / packets
        for (a, b), L in zip(segs, lens):
            if t <= L:
                px, py = a[0] + (b[0] - a[0]) * t / L, a[1] + (b[1] - a[1]) * t / L
                s = w * 2.6
                out.append('<rect x="%.1f" y="%.1f" width="%g" height="%g" fill="%s"/>'
                           % (px - s / 2, py - s / 2, s, s, C["gold_lt"] if k % 2 else col))
                break
            t -= L
    return "".join(out)


def timeline(x0, x1, y, h, rb=4):
    """Frame ruler with the playhead and a rollback window."""
    out = []
    step = h * 0.9
    n = int((x1 - x0) / step)
    for i in range(n + 1):
        x = x0 + i * step
        th = h if i % 5 == 0 else h * 0.55
        out.append('<rect x="%.1f" y="%.1f" width="%g" height="%g" fill="%s" opacity="0.6"/>'
                   % (x, y - th, max(2, h * 0.12), th, C["lilac"]))
    ph = x0 + (n - 3) * step
    win0 = ph - rb * step
    out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%g" fill="%s" opacity="0.85"/>'
               % (win0, y + h * 0.25, rb * step, h * 0.35, C["gold"]))
    out.append('<path d="%s" fill="%s"/>' % (poly([(ph - h * 0.45, y - h * 1.5), (ph + h * 0.45, y - h * 1.5),
                                                   (ph, y - h * 0.9)]), C["bone"]))
    out.append('<rect x="%.1f" y="%.1f" width="%g" height="%g" fill="%s"/>'
               % (ph - h * 0.06, y - h * 1.0, h * 0.12, h * 1.6, C["bone"]))
    t, _ = text("ROLLBACK %dF" % rb, h * 0.8, win0, y + h * 1.75, C["gold"], "mono", track=h * 0.05)
    out.append(t)
    return "".join(out)


def corners(W, H, m, L, w, col):
    out = []
    for (x, y, sx, sy) in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        out.append('<path d="M%.1f %.1f V%.1f H%.1f V%.1f H%.1f V%.1f Z" fill="%s"/>'
                   % (x, y, y + sy * L, x + sx * w, y + sy * w, x + sx * L, y, col))
    return "".join(out)


def bands(W, H, xs, col=None, op=1.0):
    return "".join('<path d="%s" fill="%s" opacity="%g"/>' % (para(x, -10, bw, H + 20), col or C["band"], op)
                   for x, bw in xs)


def scene(W, H, s, burst_at, seed=7, n_lines=90, frame_at=None, link_at=None, tl=None,
          band_xs=None, corner=True, arc=True):
    """The key-art plate. s = scale relative to a 1080-tall design."""
    rng = random.Random(seed)
    bx, by, br = burst_at
    out = [bands(W, H, band_xs if band_xs is not None else
                 [(W * 0.06, W * 0.035), (W * 0.58, W * 0.24), (W * 0.86, W * 0.05)])]
    out.append(speed_lines(rng, bx, by, W, H, n=n_lines, r0=br))
    if link_at:
        (a, b) = link_at
        out.append(link((a[0] + 50 * s, a[1] + 32 * s), (b[0] + 50 * s, b[1] + 32 * s), C["p2"], 7 * s))
    if frame_at:
        fx, fy, fw = frame_at
        out.append(frames(fx, fy, fw, fw * 0.62, dx=fw * 0.24, dy=-fw * 0.17, stroke=6 * s))
    if arc:
        out.append(rewind_arc(bx, by, br * 1.30, -20, -150, 20 * s, C["gold"]))
    out.append(burst(rng, bx, by, br))
    if link_at:
        (a, b) = link_at
        out.append(port_chip(a[0], a[1], "P1", C["p1"], 64 * s) + port_chip(b[0], b[1], "P2", C["p2"], 64 * s))
    if tl:
        out.append(timeline(tl[0], tl[1], tl[2], 22 * s))
    if corner:
        out.append(corners(W, H, 36 * s, 70 * s, 10 * s, C["gold"]))
    return "".join(out)


def tagline_strip(x, y, w, h, s_text):
    """Ink strip with a gold tick and bone text (the README strip)."""
    d = para(x, y, w, h)
    tick = para(x + h * 0.30, y + h * 0.22, h * 0.20, h * 0.56)
    t, tw_ = text(s_text, h * 0.50, x + h * 0.85, y + h * 0.5 + face("bold").cap * h * 0.25,
                  C["bone"], "bold")
    t = '<g transform="translate(%g %g) skewX(%g) translate(%g %g)">%s</g>' % (
        0, y + h, SKEW, 0, -(y + h), t)
    return '<path d="%s" fill="%s"/><path d="%s" fill="%s"/>%s' % (d, C["ink"], tick, C["gold"], t), tw_


def fit_strip(x, y, h, s_text, pad=None):
    w = tw(s_text, h * 0.50, "bold") + h * 1.4
    return tagline_strip(x, y, w, h, s_text)[0], w


def chip(x, y, h, label, fill, tcol):
    w = tw(label, h * 0.52, "black", h * 0.03) + h * 0.9
    d = para(x, y, w, h)
    t, _ = text(label, h * 0.52, x + h * 0.45, y + h * 0.5 + face("black").cap * h * 0.26, tcol,
                track=h * 0.03)
    t = '<g transform="translate(0 %g) skewX(%g) translate(0 %g)">%s</g>' % (y + h, SKEW, -(y + h), t)
    return ('<path d="%s" fill="%s" transform="translate(%g %g)"/><path d="%s" fill="%s"/>%s'
            % (d, C["ink"], h * 0.1, h * 0.1, d, fill, t)), w


def chips_row(x, y, h, labels, gap=None):
    gap = gap or h * 0.35
    out = []
    for i, lb in enumerate(labels):
        s_, w = chip(x, y, h, lb, C["gold"] if i == 0 else C["cobalt"], C["ink"] if i == 0 else C["bone"])
        out.append(s_)
        x += w + gap
    return "".join(out), x


def small_mono(x, y, size, s_text, col=None, op=0.9):
    t, _ = text(s_text, size, x, y, col or C["lilac"], "mono", track=size * 0.08)
    return G(t, op=op)


# ============================================================ assets
def keyart(W=1920, H=1080, with_text=True):
    s = H / 1080
    body = scene(W, H, s, (W * 0.735, H * 0.47, 300 * s), seed=11, n_lines=110,
                 frame_at=(W * 0.80, H * 0.38, 300 * s),
                 link_at=((W * 0.555, H * 0.14), (W * 0.84, H * 0.80)),
                 tl=(W * 0.52, W * 0.93, H * 0.925))
    body += small_mono(70 * s, 100 * s, 22 * s, "NATIVE PC PORT // ROLLBACK NETPLAY")
    body += small_mono(70 * s, H - 70 * s, 22 * s, "FRAME 000000   INPUT OK   SYNC OK", op=0.7)
    if with_text:
        wm, ww, wh = place(wordmark(LOGO_VARIANTS["dark"]), 110 * s, 260 * s, w=900 * s)
        body += wm
        strip, sw = fit_strip(96 * s, 260 * s + wh + 50 * s, 64 * s, TEXT["tagline"])
        body += strip
        row, _ = chips_row(100 * s, 260 * s + wh + 150 * s, 50 * s, TEXT["features"][:3])
        body += row
    return svg(W, H, body, bg=C["night"])


def discord_icon():
    W = 512
    rng = random.Random(3)
    body = bands(W, W, [(40, 40), (330, 120)])
    body += speed_lines(rng, 256, 256, W, W, n=34, r0=190,
                        cols=[(C["lilac"], 0.18), (C["cobalt_hi"], 0.25), (C["gold"], 0.35), (C["bone"], 0.12)])
    m, mw, mh = place(monogram(LOGO_VARIANTS["dark"]), 0, 0, w=372)
    body += G(m, "translate(%g %g)" % ((W - mw) / 2 + 4, (W - mh) / 2 + 2))
    return svg(W, W, body, bg=C["night"])


def discord_banner():
    W, H = 960, 540
    s = H / 1080
    body = scene(W, H, s * 1.2, (W * 0.80, H * 0.52, 250 * s), seed=5, n_lines=60,
                 frame_at=(W * 0.86, H * 0.40, 250 * s), link_at=None, tl=None, corner=False)
    wm, ww, wh = place(wordmark(LOGO_VARIANTS["dark"]), 56, 0, w=560)
    body += G(wm, "translate(0 %g)" % ((H - wh) / 2 - 10))
    return svg(W, H, body, bg=C["night"])


def discord_splash():
    W, H = 1920, 1080
    s = 1.0
    # centre is covered by Discord's invite card: keep the motifs at the edges
    body = scene(W, H, s, (W * 0.90, H * 0.78, 330), seed=21, n_lines=90,
                 frame_at=(W * 0.14, H * 0.80, 300),
                 link_at=((W * 0.72, H * 0.10), (W * 0.90, H * 0.36)),
                 tl=None, band_xs=[(40, 70), (1500, 300), (1840, 40)])
    wm, ww, wh = place(wordmark(LOGO_VARIANTS["dark"]), 90, 80, w=520)
    body += wm
    return svg(W, H, body, bg=C["night"])


def emoji(kind):
    W = 128
    tiles = {
        "rollback": (C["gold"], C["ink"], "rollback"),
        "replays": (C["cobalt_lt"], C["bone"], "replay"),
        "mods": ("#8a4bb0", C["bone"], "mex"),
        "lobby": (C["ok"], C["ink"], "lobby"),
        "strikes": (C["bone"], C["ink"], "strikes"),
        "bugs": (C["danger"], C["bone"], "bugs"),
        "announcements": ("#f08a29", C["ink"], "announce"),
        "netplay": (C["p2"], C["bone"], "netplay"),
        "win": (C["gold_lt"], C["ink"], "win"),
        "gg": (C["ink"], C["gold"], None),
    }
    fill, gcol, g = tiles[kind]
    h = 112
    x, y = 2, 5
    wdt = 128 - x - h * T - 7
    d = para(x, y, wdt, h)
    body = '<path d="%s" fill="%s" transform="translate(7 7)"/>' % (d, C["ink"] if kind != "gg" else C["gold_dk"])
    body += '<path d="%s" fill="%s"/>' % (d, fill)
    if kind == "gg":
        body += '<path d="%s" fill="none" stroke="%s" stroke-width="5"/>' % (d, C["gold"])
        t, _ = text("GG", 78, 0, 0, gcol, track=-2)
        w = tw("GG", 78, track=-2)
        body += '<g transform="translate(%g %g) skewX(%g)">%s</g>' % (x + h * T / 2 + wdt / 2 - w / 2,
                                                                    y + h / 2 + face("black").cap * 78 / 2,
                                                                    SKEW, t)
    else:
        gp = 84
        body += glyph(g, gcol, x + h * T / 2 + (wdt - gp) / 2, y + (h - gp) / 2, gp)
    return svg(W, W, body)


def github_social(port=False):
    W, H = 1280, 640
    s = H / 1080 * 1.1
    body = scene(W, H, s, (W * 0.80, H * 0.46, 250 * s), seed=9 if port else 13, n_lines=70,
                 frame_at=(W * 0.86, H * 0.36, 250 * s),
                 link_at=None if port else ((W * 0.62, H * 0.13), (W * 0.84, H * 0.76)),
                 tl=(W * 0.60, W * 0.93, H * 0.90) if port else None, corner=True)
    if not port:
        wm, ww, wh = place(wordmark(LOGO_VARIANTS["dark"]), 90, 120, w=640)
        body += wm
        strip, sw = fit_strip(80, 120 + wh + 40, 52, TEXT["tagline"])
        body += strip
        row, _ = chips_row(84, 120 + wh + 128, 40, TEXT["features"][3:6])
        body += row
    else:
        wm, ww, wh = place(wordmark_inline(LOGO_VARIANTS["dark"]), 90, 110, w=430)
        body += wm
        t, w1 = text(TEXT["port_title"], 60, 0, 0, C["bone"], track=1)
        sh, _ = text(TEXT["port_title"], 60, 4, 4, C["ink"], track=1)
        body += '<g transform="translate(96 %g) skewX(%g)">%s%s</g>' % (110 + wh + 120, SKEW, sh, t)
        strip, sw = fit_strip(80, 110 + wh + 170, 48, TEXT["port_sub"])
        body += strip
        row, _ = chips_row(84, 110 + wh + 262, 40, ["DECOMP", "WINDOWS X64", "OPEN SOURCE"])
        body += row
    return svg(W, H, body, bg=C["night"])


def twitter_header():
    W, H = 1500, 500
    s = 0.62
    body = scene(W, H, s, (W * 0.84, H * 0.50, 190), seed=17, n_lines=80,
                 frame_at=(W * 0.90, H * 0.40, 200), link_at=None, tl=None,
                 band_xs=[(60, 50), (820, 260), (1420, 30)])
    # the avatar covers the bottom-left on the profile page: the words sit centre-right
    wm, ww, wh = place(wordmark(LOGO_VARIANTS["dark"]), 520, 0, w=560)
    body += G(wm, "translate(0 %g)" % ((H - wh) / 2 - 40))
    strip, sw = fit_strip(505, (H + wh) / 2 + 0, 44, TEXT["tagline"])
    body += strip
    return svg(W, H, body, bg=C["night"])


def headline_block(x, y, lines, size, col=C["bone"]):
    out = []
    for i, ln in enumerate(lines):
        base = y + size * 0.72 + i * size * 0.92
        t, _ = text(ln, size, 0, 0, col, track=size * 0.005)
        sh, _ = text(ln, size, size * 0.05, size * 0.05, C["ink"], track=size * 0.005)
        out.append('<g transform="translate(%g %g) skewX(%g)">%s%s</g>' % (x, base, SKEW, sh, t))
    return "".join(out)


def post(W, H, placeholder=True):
    s = W / 1080
    body = scene(W, H, s, (W * 0.78, H * 0.30, 260), seed=29, n_lines=80,
                 frame_at=(W * 0.86, H * 0.20, 240), link_at=None,
                 tl=(W * 0.08, W * 0.60, H - 64) if H > W else None,
                 band_xs=[(40, 40), (600, 260), (1000, 40)])
    wm, ww, wh = place(wordmark_inline(LOGO_VARIANTS["dark"]), 80, 80, w=420)
    body += wm
    # headline slot
    sy = H * 0.50 if H == W else H * 0.46
    slot_h = 300 if H == W else 420
    d = para(70, sy - 20, W - 190, slot_h)
    body += '<path d="%s" fill="%s" opacity="0.55"/>' % (d, C["ink"])
    body += '<path d="%s" fill="none" stroke="%s" stroke-width="4" stroke-dasharray="18 12" opacity="0.8"/>' % (
        d, C["gold"])
    if placeholder:
        lines = TEXT["headline"]
        size = min(108 if H == W else 128, (W - 330) / max(tw(l, 1) for l in lines))
        body += headline_block(110, sy + 20, lines, size)
        sub, _ = fit_strip(96, sy + 20 + size * 0.92 * len(lines) + 30, 46, TEXT["subhead"])
        body += sub
    return svg(W, H, body, bg=C["night"])


def youtube(placeholder=True):
    W, H = 1280, 720
    s = H / 1080
    body = scene(W, H, s * 1.2, (W * 0.84, H * 0.44, 250 * s * 1.2), seed=31, n_lines=80,
                 frame_at=(W * 0.83, H * 0.30, 250 * s), link_at=None, tl=None, corner=False,
                 band_xs=[(30, 40), (780, 240)])
    m, mw, mh = place(monogram(LOGO_VARIANTS["dark"]), 60, 50, h=90)
    body += m
    if placeholder:
        body += headline_block(70, 200, TEXT["yt_headline"],
                               min(180, 620 / max(tw(l, 1) for l in TEXT["yt_headline"])), C["bone"])
    # bottom-right carries YouTube's timestamp: nothing important there
    return svg(W, H, body, bg=C["night"])


def badge(b):
    h = 28
    lab, val = b["label"], b["value"]
    fs = 12.5
    tr = 1.3
    ic = 16
    lw = 10 + ic + 7 + tw(lab, fs, "bold", tr) + 12
    vw = 12 + tw(val, fs, "black", tr) + 14
    W = lw + vw + h * T
    o = h * T
    vf, vt = (C["gold"], C["ink"]) if b["style"] == "gold" else (C["cobalt_lt"], C["bone"])
    left = poly([(0, 0), (lw + o, 0), (lw, h), (0, h)])
    right = poly([(lw + o, 0), (W, 0), (W - o, h), (lw, h)])
    body = '<path d="%s" fill="%s"/><path d="%s" fill="%s"/>' % (left, C["ink"], right, vf)
    body += '<rect x="0" y="0" width="4" height="%d" fill="%s"/>' % (h, C["gold"])
    body += glyph(b["icon"], C["gold"], 10, (h - ic) / 2, ic)
    t1, _ = text(lab, fs, 10 + ic + 7, h / 2 + face("bold").cap * fs / 2, C["bone"], "bold", tr)
    t2, _ = text(val, fs, lw + 12 + o / 2, h / 2 + face("black").cap * fs / 2, vt, "black", tr)
    body += t1 + t2
    return svg(math.ceil(W), h, body), math.ceil(W), h


def download_button():
    W, H = 640, 150
    h = 124
    o = h * T
    w = W - o - 14
    d = para(0, 0, w, h)
    body = '<path d="%s" fill="%s" transform="translate(12 12)"/>' % (d, C["ink"])
    body += '<path d="%s" fill="%s"/>' % (d, C["gold"])
    pane = poly([(o, 0), (o + 124, 0), (124, h), (0, h)])
    body += '<path d="%s" fill="%s"/>' % (pane, C["ink"])
    body += glyph("download", C["gold"], o / 2 + 124 / 2 - 34, h / 2 - 34, 68)
    fs1 = min(44, 420 / tw("DOWNLOAD FOR WINDOWS", 1, track=0.5 / 44))
    t1, _ = text("DOWNLOAD FOR WINDOWS", fs1, 0, 0, C["ink"], track=0.5)
    t2, _ = text("%s  ·  x64  ·  free" % TEXT["version"], 26, 0, 0, C["ink"], "bold", track=0.6)
    body += '<g transform="translate(%g %g) skewX(%g)">%s</g>' % (160 + (h - 72) * T * 0 + 16, 72, SKEW, t1)
    body += '<g transform="translate(%g %g) skewX(%g)">%s</g>' % (160 + 4, 108, SKEW, t2)
    return svg(W, H, body)


def app_icon(px, small=None):
    """App icon on transparent. <= 32 px uses the simplified mark."""
    small = px <= 32 if small is None else small
    if small:
        m, mw, mh = place(monogram(LOGO_VARIANTS["dark"], small=True), 0, 0, w=100)
        body = m
        return svg(px, px, body, vb=(0, 0, 100, 100))
    m, mw, mh = place(monogram(LOGO_VARIANTS["dark"]), 0, 0, w=960)
    body = G(m, "translate(%g %g)" % ((1024 - mw) / 2, (1024 - mh) / 2))
    return svg(px, px, body, vb=(0, 0, 1024, 1024))


def app_icon_plate(px):
    """Opaque version for platforms that don't take alpha (apple-touch, maskable)."""
    rng = random.Random(3)
    body = bands(1024, 1024, [(80, 80), (660, 240)])
    body += speed_lines(rng, 512, 512, 1024, 1024, n=30, r0=380)
    m, mw, mh = place(monogram(LOGO_VARIANTS["dark"]), 0, 0, w=700)
    body += G(m, "translate(%g %g)" % ((1024 - mw) / 2, (1024 - mh) / 2))
    return svg(px, px, body, bg=C["night"], vb=(0, 0, 1024, 1024))


# ============================================================ render
class Renderer:
    def __init__(self, p):
        self.b = p.chromium.launch(args=["--force-color-profile=srgb"])
        self.pages = {}

    def png(self, svg_s, w, h, scale=1, transparent=True):
        if scale not in self.pages:
            self.pages[scale] = self.b.new_page(device_scale_factor=scale)
        pg = self.pages[scale]
        pg.set_viewport_size({"width": int(w), "height": int(h)})
        pg.set_content('<!doctype html><html><head><style>html,body{margin:0;padding:0;'
                       'background:transparent}svg{display:block}</style></head><body>%s</body></html>'
                       % svg_s)
        png = pg.locator("svg").first.screenshot(type="png", omit_background=transparent)
        return Image.open(io.BytesIO(png)).convert("RGBA")

    def html(self, html_s, w, h, scale=1):
        if scale not in self.pages:
            self.pages[scale] = self.b.new_page(device_scale_factor=scale)
        pg = self.pages[scale]
        pg.set_viewport_size({"width": int(w), "height": int(h)})
        pg.set_content(html_s)
        pg.evaluate("document.fonts.ready")
        png = pg.locator("#sheet").screenshot(type="png")
        return Image.open(io.BytesIO(png)).convert("RGBA")


FILES = []            # (path, size, use)


def write(rel, data, use):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if isinstance(data, str):
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(data)
        FILES.append((rel, "vector", use))
    else:
        data.save(p, optimize=True)
        FILES.append((rel, "%dx%d" % data.size, use))


def shrink(img, px):
    """Premultiplied downscale (no dark fringes), per the pipeline README."""
    import numpy as np
    a = np.asarray(img).astype(np.float32) / 255.0
    a[..., :3] *= a[..., 3:4]
    pm = Image.fromarray((a * 255).round().astype("uint8"), "RGBA")
    sz = px if isinstance(px, tuple) else (px, px)
    pm = pm.resize(sz, Image.LANCZOS)
    b = np.asarray(pm).astype(np.float32) / 255.0
    al = b[..., 3:4]
    b[..., :3] = np.where(al > 0, b[..., :3] / np.maximum(al, 1e-6), 0)
    return Image.fromarray((b.clip(0, 1) * 255).round().astype("uint8"), "RGBA")


def circle_crop(img):
    m = Image.new("L", img.size, 0)
    from PIL import ImageDraw
    ImageDraw.Draw(m).ellipse((0, 0, img.size[0] - 1, img.size[1] - 1), fill=255)
    out = img.copy()
    out.putalpha(Image.composite(img.getchannel("A"), m, m).point(lambda v: v) if False else m)
    return out


def contrast(a, b):
    def lum(h):
        r, g, bb = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(bb)
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


EMOJI = ["rollback", "replays", "mods", "lobby", "strikes", "bugs", "announcements", "netplay",
         "win", "gg"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    with sync_playwright() as p:
        r = Renderer(p)

        # ---- logos
        for kind in ("wordmark", "monogram", "horizontal", "stacked"):
            for vn in ("dark", "light", "white", "black"):
                body, w, h = logo_lockup(kind, LOGO_VARIANTS[vn])
                s_ = svg(math.ceil(w), math.ceil(h), body)
                use = {"dark": "on dark backgrounds", "light": "on light backgrounds",
                       "white": "one colour, white, on photos/dark", "black": "one colour, black, print/light"}[vn]
                write("logo/%s_%s.svg" % (kind, vn), s_, "%s logo, %s" % (kind, use))
                write("logo/%s_%s.png" % (kind, vn), r.png(s_, w, h, 2), "%s logo @2x, %s" % (kind, use))

        # ---- key art
        for with_text, nm in ((True, "keyart"), (False, "keyart_clean")):
            s_ = keyart(with_text=with_text)
            write("keyart/%s.svg" % nm, s_, "title card source (vector)" if with_text else "clean plate source")
            write("keyart/%s_1080p.png" % nm, r.png(s_, 1920, 1080, 1, False),
                  "title card / key art 1920x1080" if with_text else "clean plate, no text, 1920x1080")
            write("keyart/%s_4k.png" % nm, r.png(s_, 1920, 1080, 2, False),
                  "title card / key art 3840x2160" if with_text else "clean plate, no text, 3840x2160")

        # ---- discord
        s_ = discord_icon()
        write("discord/server_icon.svg", s_, "Discord server icon source")
        ic = r.png(s_, 512, 512, 1, False)
        write("discord/server_icon_512.png", ic, "Discord server icon (upload; Discord crops to a circle)")
        s_ = discord_banner()
        write("discord/server_banner.svg", s_, "Discord server banner source")
        bn = r.png(s_, 960, 540, 1, False)
        write("discord/server_banner_960x540.png", bn, "Discord server banner (Boost level 2)")
        s_ = discord_splash()
        sp = r.png(s_, 1920, 1080, 1, False)
        write("discord/invite_splash_1920x1080.png", sp, "Discord invite splash (Boost level 1)")
        emo = {}
        for e in EMOJI:
            s_ = emoji(e)
            write("discord/emoji/%s.svg" % e, s_, "emoji source :%s:" % e)
            emo[e] = r.png(s_, 128, 128, 1)
            write("discord/emoji/%s.png" % e, emo[e], "Discord emoji / role icon :gdm_%s:" % e)

        # ---- social
        for port, nm in ((False, "github_social_game"), (True, "github_social_port")):
            s_ = github_social(port)
            write("social/%s.png" % nm, r.png(s_, 1280, 640, 1, False),
                  "GitHub social preview, %s repo" % ("decomp/port fork" if port else "game"))
        s_ = twitter_header()
        write("social/x_header_1500x500.png", r.png(s_, 1500, 500, 1, False), "Twitter/X header")
        for W, H, nm in ((1080, 1080, "post_square"), (1080, 1350, "post_portrait")):
            write("social/%s_1080x%d.png" % (nm, H), r.png(post(W, H), W, H, 1, False),
                  "post template with placeholder headline")
            write("social/%s_1080x%d_blank.png" % (nm, H), r.png(post(W, H, False), W, H, 1, False),
                  "post template, empty headline slot (type over it)")
        write("social/youtube_thumb_1280x720.png", r.png(youtube(), 1280, 720, 1, False),
              "YouTube thumbnail template with placeholder headline")
        write("social/youtube_thumb_1280x720_blank.png", r.png(youtube(False), 1280, 720, 1, False),
              "YouTube thumbnail template, no headline")

        # ---- badges
        for b in TEXT["badges"]:
            s_, w, h = badge(b)
            write("badges/%s.svg" % b["id"], s_, "README badge: %s %s" % (b["label"], b["value"]))
            write("badges/%s@2x.png" % b["id"], r.png(s_, w, h, 2), "README badge PNG fallback")
        s_ = download_button()
        write("badges/download_windows.svg", s_, "Download for Windows button (release page / README)")
        write("badges/download_windows.png", r.png(s_, 640, 150, 1), "Download button 640x150")
        write("badges/download_windows@2x.png", r.png(s_, 640, 150, 2), "Download button 1280x300")

        # ---- app icons
        big = r.png(app_icon(1024), 1024, 1024, 1)
        write("icons/app_icon_1024.png", big, "app icon master (transparent)")
        write("icons/app_icon.svg", app_icon(1024), "app icon source (full mark)")
        write("icons/app_icon_small.svg", app_icon(32, True), "app icon source for 16-32 px")
        sizes = [16, 24, 32, 48, 64, 128, 256]
        ims = {}
        for sz in sizes:
            if sz <= 32:
                ims[sz] = r.png(app_icon(sz), sz, sz, 1)
            else:
                ims[sz] = shrink(big, sz)
        ico = os.path.join(OUT, "icons", "gds_melee.ico")
        ims[256].save(ico, format="ICO", sizes=[(s, s) for s in sizes],
                      append_images=[ims[s] for s in sizes if s != 256])
        FILES.append(("icons/gds_melee.ico", "16-256", "Windows icon for melee-pc.exe and the launcher"))
        fav = os.path.join(OUT, "icons", "favicon", "favicon.ico")
        os.makedirs(os.path.dirname(fav), exist_ok=True)
        ims[48].save(fav, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)],
                     append_images=[ims[16], ims[32]])
        FILES.append(("icons/favicon/favicon.ico", "16/32/48", "site favicon"))
        write("icons/favicon/favicon.svg", app_icon(32, True), "site favicon (SVG, modern browsers)")
        write("icons/favicon/favicon-16.png", ims[16], "favicon PNG")
        write("icons/favicon/favicon-32.png", ims[32], "favicon PNG")
        plate = r.png(app_icon_plate(1024), 1024, 1024, 1, False)
        write("icons/favicon/apple-touch-icon.png", shrink(plate, 180), "iOS home-screen icon (opaque)")
        write("icons/favicon/icon-192.png", shrink(plate, 192), "Android / PWA icon (opaque)")
        write("icons/favicon/icon-512.png", shrink(plate, 512), "Android / PWA icon, maskable-safe")
        write("icons/favicon/site.webmanifest", json.dumps({
            "name": "GD's Melee", "short_name": "GD's Melee",
            "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "icon-512.png", "sizes": "512x512", "type": "image/png",
                       "purpose": "any maskable"}],
            "theme_color": C["night"], "background_color": C["night"], "display": "standalone"},
            indent=2), "web manifest for the favicon set")

        # ---- previews at real display size (checks)
        prev = []
        bg_dark, bg_light = (49, 51, 56, 255), (255, 255, 255, 255)
        canvas = Image.new("RGBA", (1200, 560), bg_dark)
        x = 20
        for sz in (128, 80, 48, 32, 24):
            c = circle_crop(shrink(ic, sz))
            canvas.alpha_composite(c, (x, 20))
            x += sz + 24
        b240 = shrink(bn, (240, 135))
        canvas.alpha_composite(b240, (20, 170))
        canvas.alpha_composite(shrink(sp, (480, 270)), (290, 170))
        y = 470
        x = 20
        for e in EMOJI:
            canvas.alpha_composite(shrink(emo[e], 22), (x, y))
            canvas.alpha_composite(shrink(emo[e], 48), (x, y + 30))
            x += 60
        light = Image.new("RGBA", (620, 60), bg_light)
        x = 10
        for e in EMOJI:
            light.alpha_composite(shrink(emo[e], 22), (x, 8))
            light.alpha_composite(shrink(emo[e], 32), (x + 26, 8)) if False else None
            x += 30
        canvas.alpha_composite(light, (790, 170))
        write("preview/discord_display_size.png", canvas,
              "check sheet: Discord assets at their real display sizes (not for upload)")

        write("preview/brand_sheet.png", r.png(brand_sheet(), 2400, 2000, 1, False),
              "brand sheet overview")
    write_md()
    return FILES


# ============================================================ brand sheet + BRAND.md
SWATCHES = [("Night", "night", "page background"), ("Band", "band", "backdrop bands"),
            ("Cobalt", "cobalt", "faces, panels"), ("Cobalt lt", "cobalt_lt", "badges, accents"),
            ("Lilac", "lilac", "frames, rules"), ("Gold", "gold", "emphasis, tag, mark"),
            ("Gold lt", "gold_lt", "highlight"), ("Gold dk", "gold_dk", "icon on gold"),
            ("Ink", "ink", "shadows, text on gold"), ("Bone", "bone", "text on dark"),
            ("P1 red", "p1", "port / danger"), ("P2 blue", "p2", "port / link")]


def _img(path, x, y, w, h):
    import base64
    b = base64.b64encode(open(os.path.join(OUT, path), "rb").read()).decode()
    return '<image href="data:image/png;base64,%s" x="%g" y="%g" width="%g" height="%g"/>' % (b, x, y, w, h)


def brand_sheet():
    W, H = 2400, 2000
    L = lambda s_, sz, x, y, col=C["bone"], f="bold": text(s_, sz, x, y, col, f)[0]
    b = L("GD'S MELEE  BRAND KIT", 64, 80, 120, C["gold"], "black")
    b += L("Everything generated from pipeline/build_brand.py. Original art only.", 28, 80, 170, C["muted"])
    # palette
    b += L("PALETTE", 34, 80, 260, C["gold"], "black")
    for i, (n, k, u) in enumerate(SWATCHES):
        x, y = 80 + (i % 6) * 370, 290 + (i // 6) * 230
        b += '<rect x="%d" y="%d" width="340" height="120" fill="%s" stroke="%s" stroke-width="3"/>' % (
            x, y, C[k], C["ink"])
        b += L(n, 28, x, y + 160) + L(C[k].upper(), 26, x, y + 192, C["muted"], "mono") + L(u, 22, x, y + 222, C["muted"])
    # fonts
    b += L("TYPE", 34, 80, 820, C["gold"], "black")
    b += L("Source Sans 3 Black  DISPLAY / WORDMARK", 56, 80, 900, C["bone"], "black")
    b += L("Source Sans 3 Bold  taglines, body, badge labels", 40, 80, 960)
    b += L("Hasklug Bold  FRAME 000 / ROLLBACK 4F / hex codes", 36, 80, 1015, C["lilac"], "mono")
    b += L("All display type is sheared 14 deg (skewX -14.036, the kit's S = 0.25). Shadows are hard ink offsets.", 26, 80, 1060, C["muted"])
    # clear space
    b += L("CLEAR SPACE + MIN SIZE", 34, 80, 1150, C["gold"], "black")
    b += '<rect x="80" y="1180" width="760" height="420" fill="none" stroke="%s" stroke-width="3" stroke-dasharray="14 10"/>' % C["gold"]
    b += _img("logo/wordmark_dark.png", 150, 1250, 620, 620 * 0.42)
    b += L("x = height of the GD'S plate; keep x clear on every side", 24, 80, 1640, C["muted"])
    b += L("Min size: wordmark 120 px wide / 25 mm; monogram 24 px (below 32 px use app_icon_small)", 24, 80, 1675, C["muted"])
    b += _img("logo/monogram_dark.png", 900, 1200, 220, 220 * 0.8)
    b += _img("icons/favicon/favicon-32.png", 1160, 1250, 32, 32)
    b += _img("icons/favicon/favicon-16.png", 1210, 1258, 16, 16)
    # do / don't
    b += L("DO / DON'T", 34, 1300, 1150, C["gold"], "black")
    cells = [("DO: dark on dark", "logo/wordmark_dark.png", "", True),
             ("DON'T: recolour", "logo/wordmark_dark.png", "hue", False),
             ("DON'T: stretch", "logo/wordmark_dark.png", "stretch", False),
             ("DON'T: unshear / rotate", "logo/wordmark_dark.png", "rot", False)]
    for i, (lb, pth, fx, ok) in enumerate(cells):
        x, y = 1300 + (i % 2) * 520, 1190 + (i // 2) * 330
        b += '<rect x="%d" y="%d" width="480" height="260" fill="%s"/>' % (x, y, C["band"])
        tr = {"": "", "hue": "", "stretch": "translate(%d %d) scale(1.2 0.7) translate(%d %d)" % (x + 60, y + 60, -(x + 60), -(y + 60)),
              "rot": "rotate(12 %d %d)" % (x + 240, y + 130)}[fx]
        filt = ' filter="url(#hue)"' if fx == "hue" else ""
        b += '<g transform="%s"%s>%s</g>' % (tr, filt, _img(pth, x + 60, y + 50, 360, 360 * 0.42))
        b += L(lb, 24, x, y + 295, C["ok"] if ok else C["danger"], "black")
    b = '<defs><filter id="hue"><feColorMatrix type="hueRotate" values="140"/></filter></defs>' + b
    b += L("No Nintendo marks, characters or traced art. Never add them to the logo or key art.", 24, 80, 1920, C["muted"])
    return svg(W, H, b, bg=C["night"])


def write_md():
    rows = chr(10).join("| `%s` | %s | %s |" % (p, sz, u) for p, sz, u in FILES)
    pal = chr(10).join("| %s | `%s` | %s |" % (n, C[k], u) for n, k, u in SWATCHES)
    md = BRAND_MD.replace("{PAL}", pal).replace("{ROWS}", rows)
    with open(os.path.join(OUT, "BRAND.md"), "w", encoding="utf-8") as fh:
        fh.write(md)


BRAND_MD = """# GD's Melee brand kit

Built by `python pipeline/build_brand.py` (words in `pipeline/brand_text.json`). Every image
is generated from SVG/HTML in that script and rendered by headless Chromium; text is converted
to outlines, so the SVGs are self-contained. Nothing is traced, recoloured or sampled from any
Nintendo asset: no Nintendo logos, no character art, no trademarked marks.

Overview: `preview/brand_sheet.png`. Discord display-size check: `preview/discord_display_size.png`.

## Picks

- Discord server icon: `discord/server_icon_512.png`
- Discord server banner: `discord/server_banner_960x540.png`
- GitHub social preview: `social/github_social_game.png` (game), `social/github_social_port.png` (decomp/port fork)

## Palette

Same values as the in-game menu kit (`pipeline/kit.py`).

| Name | Hex | Use |
|---|---|---|
{PAL}

## Type

- **Source Sans 3 Black**: wordmark, headlines, chips. Uppercase, sheared 14 degrees.
- **Source Sans 3 Bold**: taglines, body, badge labels.
- **Hasklug Bold** (mono): frame counters, technical labels, hex codes.

The one shear everywhere is skewX(-14.036deg) (the kit's S = 0.25). Shadows are hard ink
offsets (about 5% of the type size), never blurred.

## Logo

- **Wordmark** (primary): the GD'S plate over MELEE.
- **Monogram**: GD on the chamfered gold tile. Below 32 px use `icons/app_icon_small.svg`
  (unsheared, maximised letters).
- **Horizontal lockup**: monogram + one-line wordmark. **Stacked lockup**: monogram over the wordmark.
- Variants: `dark` (for dark backgrounds), `light` (for light backgrounds), `white` and `black`
  (one colour, plate letters knocked out, no shadow).

**Clear space**: x on every side, where x is the height of the GD'S plate.
**Minimum size**: wordmark 120 px wide (25 mm in print); monogram 24 px; 16 px only with the small mark.

**Do**: use the supplied files; keep the gold plate and ink shadow; use the white/black versions on photos.
**Don't**: recolour, stretch, rotate or unshear the mark, add outlines/glows/gradients, set the
wordmark in another font, or combine it with any Nintendo mark or character art.

## Files

| File | Size | Use |
|---|---|---|
{ROWS}
"""


if __name__ == "__main__":
    main()
