"""HTML builders for the Workbench kit. Pure functions returning strings; build.py assembles pages.
`{A}` in a string is replaced by the asset path prefix when a page is written."""
import html as _h

esc = _h.escape


def pos(x=None, y=None, w=None, h=None, extra=""):
    s = ""
    for k, v in (("left", x), ("top", y), ("width", w), ("height", h)):
        if v is not None:
            s += "%s:%spx;" % (k, round(v, 2))
    return 'style="position:absolute;%s%s"' % (s, extra)


def at(x, y, inner, w=None, h=None, cls="", extra=""):
    return '<div class="%s" %s>%s</div>' % (cls, pos(x, y, w, h, extra), inner)


# ------------------------------------------------------------------ player shapes
SHAPES = {
    "circle": '<circle cx="6" cy="6" r="5"/>',
    "square": '<rect x="1" y="1" width="10" height="10"/>',
    "triangle": '<polygon points="6,0.5 11.5,11 0.5,11"/>',
    "diamond": '<polygon points="6,0 12,6 6,12 0,6"/>',
    "hexagon": '<polygon points="3,1 9,1 12,6 9,11 3,11 0,6"/>',
}
PORT_SHAPE = {"p1": "circle", "p2": "square", "p3": "triangle", "p4": "diamond", "cpu": "hexagon"}
PORT_NAME = {"p1": "P1", "p2": "P2", "p3": "P3", "p4": "P4", "cpu": "CPU"}


def shape(port):
    return '<svg viewBox="0 0 12 12" aria-hidden="true">%s</svg>' % SHAPES[PORT_SHAPE[port]]


def flag(port, text=None):
    return '<span class="flag %s">%s%s</span>' % (port, shape(port), esc(text or PORT_NAME[port]))


def peg(port):
    return '<span class="peg %s">%s</span>' % (port, shape(port))


def cursor(port, x, y):
    return '<div class="cursor %s" style="left:%spx;top:%spx"><div class="pad">%s</div></div>' % (port, x, y, shape(port))


# ------------------------------------------------------------------ family shapes (silhouette per drive family)
FAM_SHAPE = {
    "red": '<polygon points="7,0 8.6,5.4 14,7 8.6,8.6 7,14 5.4,8.6 0,7 5.4,5.4"/>',
    "green": '<polygon points="0,1 5,1 8,7 5,13 0,13 3,7"/><polygon points="6,1 11,1 14,7 11,13 6,13 9,7"/>',
    "blue": '<polygon points="1,1 13,1 13,7 7,14 1,7"/>',
    "yellow": '<polygon points="7,13 0,3 4,6 4,0 7,5 10,0 10,6 14,3"/>',
    "purple": '<circle cx="7" cy="7" r="4.5"/><circle cx="2" cy="2.5" r="1.6"/><circle cx="12" cy="3" r="1.6"/><circle cx="12" cy="12" r="1.6"/>',
    "white": '<polygon points="2,4 8,0 14,6 10,14 3,11"/>',
}
FAM_COL = {"red": "#e0443a", "green": "#38b36a", "blue": "#3b82e8", "yellow": "#f0c030", "purple": "#b04ae6", "white": "#e8ecf4"}


def famshape(fam, size=14, col=None):
    return '<svg viewBox="0 0 14 14" width="%d" height="%d" fill="%s">%s</svg>' % (size, size, col or "currentColor", FAM_SHAPE[fam])


# ------------------------------------------------------------------ pad glyphs, keycaps, mouse
def _t(txt, x, y, fill, size=13):
    return '<text x="%s" y="%s" text-anchor="middle" font-family="SS3" font-weight="900" font-size="%s" fill="%s">%s</text>' % (x, y, size, fill, txt)


PAD = {
    "A": ('0 0 24 24', '<circle cx="12" cy="12" r="11" fill="#3fae6a"/>' + _t("A", 12, 17, "#06210f", 14)),
    "B": ('0 0 24 24', '<circle cx="12" cy="12" r="9" fill="#e0443a"/>' + _t("B", 12, 16.5, "#fff", 13)),
    "X": ('0 0 24 24', '<ellipse cx="12" cy="12" rx="9" ry="11" fill="#c9c5b4"/>' + _t("X", 12, 16.5, "#191714", 13)),
    "Y": ('0 0 24 24', '<ellipse cx="12" cy="12" rx="11" ry="9" fill="#c9c5b4"/>' + _t("Y", 12, 16.5, "#191714", 13)),
    "Z": ('0 0 28 24', '<rect x="1" y="4" width="26" height="16" rx="6" fill="#9a6ae0"/>' + _t("Z", 14, 17, "#1d0b3d", 13)),
    "L": ('0 0 30 24', '<path d="M2 20 L2 8 Q2 3 8 3 L28 3 L28 20 Z" fill="#c9c5b4"/>' + _t("L", 15, 17, "#191714", 13)),
    "R": ('0 0 30 24', '<path d="M28 20 L28 8 Q28 3 22 3 L2 3 L2 20 Z" fill="#c9c5b4"/>' + _t("R", 15, 17, "#191714", 13)),
    "START": ('0 0 52 24', '<rect x="1" y="4" width="50" height="16" rx="8" fill="#c9c5b4"/>' + _t("START", 26, 16.4, "#191714", 11.5)),
    "STICK": ('0 0 24 24', '<circle cx="12" cy="12" r="10" fill="none" stroke="#c9c5b4" stroke-width="3"/><circle cx="12" cy="12" r="4.5" fill="#c9c5b4"/>'),
    "DPAD": ('0 0 24 24', '<path d="M9 1h6v8h8v6h-8v8H9v-8H1V9h8z" fill="#c9c5b4"/>'),
    "CSTICK": ('0 0 24 24', '<circle cx="12" cy="12" r="10" fill="#f0c030"/><circle cx="12" cy="12" r="4.5" fill="#6a4f06"/>'),
}


def pad(name):
    vb, body = PAD[name]
    w = float(vb.split()[2]) / 24 * 22
    return '<svg class="g" viewBox="%s" width="%.1f" height="22" aria-label="%s">%s</svg>' % (vb, w, name, body)


def kc(label):
    return '<span class="kc">%s</span>' % (label if label.startswith("&#") else esc(label))


def mouse(btn="L"):
    left = '#ff7a2f' if btn == "L" else '#c9c5b4'
    right = '#ff7a2f' if btn == "R" else '#c9c5b4'
    wheel = '#ff7a2f' if btn == "W" else '#8a8573'
    return ('<svg class="g" viewBox="0 0 20 26" width="17" height="22"><path d="M10 1 H4 Q1 1 1 5 V10 H10Z" fill="%s"/><path d="M10 1 H16 Q19 1 19 5 V10 H10Z" fill="%s"/>'
            '<path d="M1 12 H19 V19 Q19 25 10 25 Q1 25 1 19Z" fill="#c9c5b4"/><rect x="8.4" y="3" width="3.2" height="6" rx="1.5" fill="%s"/></svg>') % (left, right, wheel)


def hints(items, w=640, pad_left=14, right=None):
    """items: list of (glyph_html, verb). `right` is optional print text at the far right."""
    hs = "".join('<span class="h">%s<span>%s</span></span>' % (g, esc(v)) for g, v in items)
    r = '<span class="sp"></span><span class="print" style="color:var(--mat-print)">%s</span>' % esc(right) if right else ""
    return '<div class="hints" style="position:absolute;left:0;right:0;bottom:0;padding-left:%spx">%s%s</div>' % (pad_left, hs, r)


PADHINT = {
    "pick": (lambda: pad("A"), "Pick up"), "put": (lambda: pad("B"), "Put back"), "turn": (lambda: pad("X"), "Turn over"),
    "sort": (lambda: pad("Y"), "Sort"), "cmp": (lambda: pad("Z"), "Lay side by side"),
    "lr": (lambda: pad("L") + pad("R"), "Flip page"), "start": (lambda: pad("START"), "Clear the bench"),
    "move": (lambda: pad("STICK") + pad("DPAD"), "Slide along"),
}


def ph(*keys, extra=()):
    out = []
    for k in keys:
        g, v = PADHINT[k]
        out.append((g(), v))
    out.extend(extra)
    return out


# ------------------------------------------------------------------ objects
def puck(fam, cls="", rar=None, name=None, style=""):
    src = "drive_%s%s.svg" % (fam, "_" + rar if rar else "")
    return '<div class="puck fam-%s %s" style="%s"><img src="{A}%s" alt="%s"></div>' % (fam, cls, style, src, esc(name or fam + " drive"))


def sock(inner="", cls="", no=None, style=""):
    n = '<span class="no">%s</span>' % no if no else ""
    return '<div class="sock %s" style="%s">%s%s</div>' % (cls, style, inner, n)


def pin():
    return '<span class="pin"><svg viewBox="0 0 12 12"><path d="M1.5 6.5 L4.8 9.8 L10.5 2.5" fill="none" stroke="#e8dfca" stroke-width="2.4"/></svg></span>'


def row(label, val=None, cls="", icon="", small=None, w=None, style="", widget=""):
    v = '<span class="win">%s</span>' % esc(val) if val is not None else ""
    sm = "<small>%s</small>" % esc(small) if small else ""
    sp = ""
    return ('<div class="board row %s" style="%s%s">%s%s<span>%s</span>%s<span class="sp"></span>%s%s</div>'
            % (cls, ("width:%spx;" % w) if w else "", style, pin(), icon, esc(label), sm, widget, v))


def tog(on=False, cls=""):
    return '<span class="tog %s %s"><b>%s</b></span>' % ("on" if on else "", cls, "ON" if on else "OFF")


def choice(val, n=0, i=0, cls="", wide=None):
    d = "".join('<i class="%s"></i>' % ("on" if k == i else "") for k in range(n))
    dots = '<span class="dots">%s</span>' % d if n else ""
    st = ' style="min-width:%spx"' % wide if wide else ""
    return ('<span class="choice %s"><span class="arr l %s"></span><span class="win"%s>%s</span><span class="arr r %s"></span>%s</span>'
            % (cls, "dim" if i == 0 and n else "", st, esc(val), "dim" if i == n - 1 and n else "", dots))


def slider(frac, w=150):
    x = frac * (w - 16)
    return ('<span class="sld" style="width:%spx"><span class="groove"></span><span class="fillbar" style="width:%spx"></span><span class="ticks"></span><span class="car" style="left:%spx"></span></span>'
            % (w, x + 8, x))


def disc(kind="icon", label="disc art", extra="", style="", w=None, h=None, cls=""):
    art = ""
    if w:
        style += ";width:%spx;height:%spx" % (w, h)
        art = ' style="width:%spx;height:%spx"' % (w - 8, h - 8)
    return '<div class="disc %s %s" style="%s"><div class="art"%s><span>%s</span></div>%s</div>' % (kind, cls, style, art, esc(label), extra)


def stamp(txt, style=""):
    return '<span class="stamp" style="%s">%s</span>' % (style, esc(txt))


def chip(txt, cls=""):
    return '<span class="chip %s">%s</span>' % (cls, esc(txt))


def tag(name, rule, meta=None, price=None, w=200, cls="", style="", hole_string=None):
    m = '<div class="meta">%s</div>' % meta if meta else ""
    p = '<div class="price">%s</div>' % esc(price) if price else ""
    return ('<div class="tag %s" style="width:%spx;%s"><span class="hole"></span><div class="face">%s<h4>%s</h4><div class="rule">%s</div>%s</div></div>'
            % (cls, w, style, m, esc(name), esc(rule) if rule else "", p))


def string(x1, y1, x2, y2, sag=14):
    """A string between two points (the tag's hole and the thing it is tied to): hard shadow copy under it."""
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2 + sag
    d = "M%s %s Q%s %s %s %s" % (x1, y1, mx, my, x2, y2)
    return ('<svg class="string" style="left:0;top:0;width:1px;height:1px"><path d="%s" fill="none" stroke="#080b09" stroke-width="2.4" transform="translate(2 3)"/>'
            '<path d="%s" fill="none" stroke="#f1e8d2" stroke-width="2.4"/></svg>') % (d, d)


def keystone(letter, colour, focus=False, w=None):
    return ('<div class="hooked"><div class="chain"></div><div class="key kc-%s %s"><div class="face"><b>%s</b></div><div class="band"></div></div></div>'
            % (colour, "focus" if focus else "", esc(letter)))


def hook_empty():
    return '<div class="hook-empty"><i></i></div>'


def slip(text, small=None, cls="", w=None, style=""):
    s = "<small>%s</small>" % esc(small) if small else ""
    return '<div class="slip %s" style="%s%s">%s%s</div>' % (cls, ("width:%spx;" % w) if w else "", style, s, esc(text))


def tape(text, cls=""):
    return '<span class="tape %s">%s</span>' % (cls, esc(text))


def crumbs(items):
    out = []
    for i, c in enumerate(items):
        if i:
            out.append("<i></i>")
        out.append(tape(c, "sm" + (" dim" if i < len(items) - 1 else "")))
    return '<div class="crumbs">%s</div>' % "".join(out)


def tabs(names, sel, focus=None, counts=None):
    out = []
    for i, n in enumerate(names):
        c = "tab"
        if i == sel:
            c += " sel"
        elif i == focus:
            c += " focus"
        cn = '<span class="chip n">%s</span>' % counts[i] if counts and counts.get(i) else ""
        out.append('<div class="%s">%s%s</div>' % (c, esc(n), cn))
    return '<div class="tabs">%s</div>' % "".join(out)


def prog(n, on, cur=None):
    return '<span class="prog">%s</span>' % "".join('<i class="%s"></i>' % ("cur" if i == cur else ("on" if i < on else "")) for i in range(n))


def scroll(h, top, size):
    return '<div class="scr" style="height:%spx"><b style="top:%spx;height:%spx"></b></div>' % (h, top, size)


# ------------------------------------------------------------------ icons (flat pictograms in ink, 28 grid)
def _i(body, col="currentColor"):
    return '<svg class="icn" viewBox="0 0 28 28" fill="%s">%s</svg>' % (col, body)


ICON = {
    "solo": '<circle cx="14" cy="10" r="6"/><rect x="5" y="19" width="18" height="5" rx="2"/>',
    "versus": '<circle cx="8" cy="10" r="5"/><rect x="2" y="18" width="12" height="6" rx="2"/><rect x="14" y="5" width="11" height="11" rx="2"/><rect x="14" y="18" width="12" height="6" rx="2"/>',
    "online": '<circle cx="6" cy="14" r="4.5"/><circle cx="22" cy="14" r="4.5"/><rect x="9" y="12.5" width="10" height="3"/>',
    "collection": '<rect x="2" y="16" width="7" height="9"/><rect x="10.5" y="10" width="7" height="15"/><rect x="19" y="4" width="7" height="21"/>',
    "settings": '<rect x="2" y="7" width="24" height="4" rx="1.5"/><rect x="15" y="3" width="6" height="12" rx="2"/><rect x="2" y="18" width="24" height="4" rx="1.5"/><rect x="5" y="14" width="6" height="12" rx="2"/>',
    "data": '<rect x="6" y="3" width="18" height="6" rx="1.5"/><rect x="4" y="11" width="20" height="6" rx="1.5"/><rect x="2" y="19" width="22" height="6" rx="1.5"/>',
    "mods": '<path d="M3 8h8V5a3 3 0 0 1 6 0v3h8v8h-3a3 3 0 0 0 0 6h3v4H3z"/>',
    "classic": '<path d="M5 3h3v22H5z"/><polygon points="8,4 24,9 8,15"/>',
    "adventure": '<polygon points="2,24 10,8 16,16 20,10 26,24"/>',
    "allstar": '<polygon points="14,2 17.5,10.5 26,11 19.5,17 21.5,26 14,21 6.5,26 8.5,17 2,11 10.5,10.5"/>',
    "event": '<rect x="3" y="5" width="22" height="20" rx="2"/><rect x="7" y="2" width="3" height="6" fill="#e8dfca"/><rect x="18" y="2" width="3" height="6" fill="#e8dfca"/><rect x="7" y="12" width="14" height="3" fill="#e8dfca"/>',
    "stadium": '<path d="M2 22 Q14 -2 26 22 Z"/>',
    "training": '<circle cx="14" cy="14" r="12"/><circle cx="14" cy="14" r="7" fill="#e8dfca"/><circle cx="14" cy="14" r="3"/>',
    "lab": '<path d="M10 2h8v2h-2v7l8 13a2 2 0 0 1-2 3H6a2 2 0 0 1-2-3l8-13V4h-2z"/>',
    "tool": '<rect x="3" y="3" width="22" height="7" rx="2"/><rect x="11" y="10" width="6" height="16"/>',
    "page": '<rect x="5" y="2" width="18" height="24" rx="2"/>',
    "disc": '<circle cx="14" cy="14" r="12"/><circle cx="14" cy="14" r="4" fill="#e8dfca"/>',
    "step": '<polygon points="4,4 14,14 4,24"/><rect x="18" y="4" width="5" height="20"/>',
    "eye": '<path d="M1 14 Q14 1 27 14 Q14 27 1 14Z"/><circle cx="14" cy="14" r="5" fill="#e8dfca"/>',
    "dummy": '<circle cx="14" cy="7" r="5"/><rect x="9" y="14" width="10" height="11" rx="2"/>',
    "video": '<rect x="2" y="4" width="24" height="16" rx="2"/><rect x="9" y="22" width="10" height="3"/>',
    "audio": '<polygon points="2,10 8,10 15,4 15,24 8,18 2,18"/><path d="M19 9 Q23 14 19 19" fill="none" stroke="currentColor" stroke-width="3"/>',
    "pad": '<rect x="2" y="7" width="24" height="15" rx="7"/><rect x="7" y="13" width="7" height="2.4" fill="#e8dfca"/><rect x="9.3" y="10.7" width="2.4" height="7" fill="#e8dfca"/><circle cx="19" cy="13" r="2" fill="#e8dfca"/><circle cx="22" cy="17" r="2" fill="#e8dfca"/>',
    "warn": '<polygon points="14,2 27,25 1,25"/><rect x="12.6" y="10" width="2.8" height="8" fill="#e8dfca"/><rect x="12.6" y="20" width="2.8" height="2.8" fill="#e8dfca"/>',
}


def icon(name, col=None):
    return _i(ICON[name], col or "currentColor")


def mini_drive(fam, size=34):
    return '<span style="display:inline-block;width:%dpx;height:%dpx;flex:none"><img src="{A}drive_%s.svg" width="%d" height="%d"></span>' % (size, size, fam, size, size)
