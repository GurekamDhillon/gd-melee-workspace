"""ATLAS component helpers: each returns an HTML string that kit.css styles. Screens and the kit sheet use only these."""
import html

DRIVES = {'svg': ''}   # set by build.py (drives.build_defs) before any page is made

ICONS = {
    "solo": '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c0-4 3-6.5 7-6.5s7 2.5 7 6.5"/>',
    "versus": '<path d="M3 6l7 6-7 6M21 6l-7 6 7 6"/>',
    "online": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3.5 3 3.5 15 0 18M12 3c-3.5 3-3.5 15 0 18"/>',
    "mods": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12v9M4 7.5l8 4.5 8-4.5"/>',
    "settings": '<path d="M4 7h16M4 12h16M4 17h16"/><rect class="f" x="14" y="5" width="4" height="4"/><rect class="f" x="6" y="10" width="4" height="4"/><rect class="f" x="12" y="15" width="4" height="4"/>',
    "more": '<rect class="f" x="4" y="10" width="4" height="4"/><rect class="f" x="10" y="10" width="4" height="4"/><rect class="f" x="16" y="10" width="4" height="4"/>',
    "classic": '<path d="M6 21V4M6 5h12l-3 4 3 4H6"/>',
    "adventure": '<path d="M4 18c4 0 3-8 8-8s3-4 8-4"/><circle class="f" cx="4" cy="18" r="1.8"/><circle class="f" cx="20" cy="6" r="1.8"/>',
    "allstar": '<path d="M12 3l2.7 6 6.3.6-4.8 4.2 1.5 6.2L12 16.8 6.3 20l1.5-6.2L3 9.6 9.3 9z"/>',
    "event": '<rect x="4" y="5" width="16" height="15"/><path d="M4 10h16M8 3v4M16 3v4"/>',
    "stadium": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><rect class="f" x="11" y="11" width="2" height="2"/>',
    "training": '<circle cx="12" cy="6" r="3"/><path d="M12 9v8M7 12h10M9 21l3-4 3 4"/>',
    "lab": '<path d="M9 3h6M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2h12.4a1.5 1.5 0 0 0 1.3-2L14 9V3M7.5 15h9"/>',
    "envoy": '<path d="M12 2l9 10-9 10-9-10z"/><path d="M12 7v10M7 12h10"/>',
    "lock": '<rect x="5" y="11" width="14" height="10"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "check": '<path d="M4 12l5 5 11-11"/>',
    "x": '<path d="M5 5l14 14M19 5L5 19"/>',
    "warn": '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v1"/>',
    "plus": '<path d="M12 4v16M4 12h16"/>',
    "audio": '<path d="M4 9h4l5-4v14l-5-4H4zM16 9c1.5 1.5 1.5 4.5 0 6"/>',
    "video": '<rect x="3" y="5" width="18" height="12"/><path d="M8 21h8M12 17v4"/>',
    "pad": '<path d="M7 7h10a5 5 0 0 1 5 5v2a3 3 0 0 1-5.500 1.500L15 14H9l-1.500 1.500A3 3 0 0 1 2 14v-2a5 5 0 0 1 5-5z"/><path d="M7 10v4M5 12h4"/>',
    "disc": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/>',
    "collection": '<path d="M7 4h10v5a5 5 0 0 1-10 0zM7 6H4v2a3 3 0 0 0 3 3M17 6h3v2a3 3 0 0 1-3 3M12 14v4M8 21h8"/>',
    "data": '<path d="M5 6h14M5 12h14M5 18h14"/><rect class="f" x="3" y="5" width="2" height="2"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
    "up": '<path d="M5 15l7-7 7 7"/>', "down": '<path d="M5 9l7 7 7-7"/>',
    "left": '<path d="M15 5l-7 7 7 7"/>', "right": '<path d="M9 5l7 7-7 7"/>',
    "star": '<path d="M12 3l2.7 6 6.3.6-4.8 4.2 1.5 6.2L12 16.8 6.3 20l1.5-6.2L3 9.6 9.3 9z"/>',
    "flag": '<path d="M6 21V4M6 5h12l-3 4 3 4H6"/>',
    "bolt": '<path d="M13 2L5 14h6l-1 8 8-12h-6z"/>',
    "people": '<circle cx="8" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M2 20c0-4 2.5-6 6-6s6 2 6 6M15 14c3 0 6 1.500 6 5"/>',
    "folder": '<path d="M3 6h7l2 2h9v11H3z"/>',
    "refresh": '<path d="M19 8a8 8 0 1 0 1 5M19 3v5h-5"/>',
    "ghost": '<path d="M5 21V10a7 7 0 0 1 14 0v11l-3.5-3-3.500 3-3.500-3z"/>',
    "map": '<path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2zM9 4v14M15 6v14"/>',
}

# real drive families: shape + colour. The model SVG carries both; the key is the family.
FAM = {"red": "damage", "green": "speed", "blue": "defence", "yellow": "air", "purple": "status", "white": "wild"}

NAV = [("I", "Solo", "solo"), ("II", "Versus", "versus"), ("III", "Online", "online"), ("IV", "Mods", "mods"), ("V", "Settings", "settings")]


def esc(s):
    return html.escape(str(s), quote=False)


def ic(name, cls=""):
    return '<svg class="ic %s" viewBox="0 0 24 24"><use href="#i-%s"/></svg>' % (cls, name)


def defs(drives_svg):
    g = "".join('<g id="i-%s">%s</g>' % (k, v) for k, v in ICONS.items())
    mark = ('<g id="i-mark"><path d="M12 1l11 11-11 11L1 12z" fill="#ff7a3d"/><path d="M12 5l7 7-7 7-7-7z" fill="#0d1015"/>'
            '<path d="M12 8l4 4-4 4-4-4z" fill="#f1ebdc"/></g>')
    return '<svg class="defs" xmlns="http://www.w3.org/2000/svg" width="0" height="0"><defs>%s%s%s</defs></svg>' % (g, mark, drives_svg)


def mark(size=22):
    return '<svg class="mark" style="width:%dpx;height:%dpx" viewBox="0 0 24 24"><use href="#i-mark"/></svg>' % (size, size)


def drv(fam, ring=None, cls=""):
    r = '<use href="#ring-%s"/>' % ring if ring else ""
    return '<svg class="m %s" viewBox="-2.45 -2.45 4.9 4.9"><use href="#drv-%s"/>%s</svg>' % (cls, fam, r)


def kg(g, extra=""):
    if g in ("stick", "dpad"):
        return '<span class="kg %s"></span>' % g
    cls = {"START": "S"}.get(g, g)
    txt = "START" if g in ("S", "START") else g
    return '<span class="kg %s">%s</span>' % (cls, txt)


def hint(g, label):
    return '<span class="hint">%s<b>%s</b></span>' % (kg(g), esc(label))


def pt(n, cls=""):
    if n == "cpu":
        return '<span class="pt cpu %s">CPU</span>' % cls
    return '<span class="pt p%d %s">%d</span>' % (n, cls, n)


# ------------------------------------------------------------------ frame
def page(trail, body, hints=(), chap=None, wide=False, status="", pos="", title="atlas", foot_extra="", overlay="",
         head_extra="", w=None, ground=True):
    W = w or (853 if wide else 640)
    t = []
    for i, x in enumerate(trail):
        if i:
            t.append('<span class="sep"></span>')
        t.append('<span class="%s">%s</span>' % ("here" if i == len(trail) - 1 else "", esc(x)))
    chapdots = ""
    rail = ""
    if chap is not None:
        chapdots = '<div class="chap">%s</div>' % "".join('<i class="%s">%s</i>' % ("on" if k == chap else "", n[0]) for k, n in enumerate(NAV))
        rail = '<div class="rail">%s</div>' % "".join(
            '<div class="rr %s"><i>%s</i>%s</div>' % ("on" if k == chap else "", n[0], n[1]) for k, n in enumerate(NAV))
    hint_html = "".join(hint(g, l) for g, l in hints)
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>%s</title>'
        '<link rel="stylesheet" href="../tokens.css"><link rel="stylesheet" href="../kit.css">%s</head><body>%s'
        '<div class="s%s" style="--w:%dpx">%s'
        '<div class="hdr">%s<div class="trail">%s</div><div class="sp"></div>%s<div class="status">%s</div></div><div class="hdr-rule"></div>'
        '<div class="body">%s%s</div>'
        '<div class="foot">%s<div class="sp"></div>%s%s</div>%s</div></body></html>'
    ) % (esc(title), head_extra, defs(DRIVES['svg']), " wide" if wide else "", W,
         '<div class="grat"></div><div class="facet a"></div><div class="facet b"></div>' if ground else "",
         mark(), "".join(t), chapdots, status, rail, body, hint_html, '<span class="hint muted num">%s</span>' % esc(pos) if pos else "",
         foot_extra, overlay)


# ------------------------------------------------------------------ rows and widgets
def tog(on):
    return '<span class="tog"><i class="%s">OFF</i><i class="%s">ON</i></span>' % ("off" if not on else "", "on" if on else "")


def choice(v, w=None):
    st = ' style="min-width:%dpx"' % w if w else ""
    return '<span class="choice"><span class="ar">&#9664;</span><span class="v"%s>%s</span><span class="ar">&#9654;</span></span>' % (st, esc(v))


def stepper(v):
    return '<span class="stepper"><span class="ar">&#9664;</span><span class="num">%s</span><span class="ar">&#9654;</span></span>' % esc(v)


def slider(n, total=20, val=None):
    ticks = []
    for i in range(total):
        c = "k" if i == n else ("f" if i < n else "")
        ticks.append('<i class="%s"></i>' % c)
    v = '<span class="num" style="min-width:34px;text-align:right">%s</span>' % esc(val) if val is not None else ""
    return '<span class="sl">%s</span>%s' % ("".join(ticks), v)


def row(label, val="", ico=None, state="", sub=None, cls="", chev=False):
    i = ic(ico, "") if ico else ""
    s = '<span class="sub">%s</span>' % esc(sub) if sub else ""
    c = ic("right", "sm") if chev else ""
    v = '<span class="val">%s%s</span>' % (val, c) if (val or chev) else ""
    return '<div class="row %s %s">%s<span class="lbl">%s %s</span>%s</div>' % (state, cls, i, esc(label), s, v)


def group(label):
    return '<div class="row group">%s</div>' % esc(label)


def btn(label, state="", cls="", ico=None, kgl=None):
    i = ic(ico) if ico else ""
    k = kg(kgl) if kgl else ""
    return '<span class="btn %s %s">%s%s%s</span>' % (state, cls, k, i, esc(label))


def tag(t, cls=""):
    return '<span class="tag %s">%s</span>' % (cls, esc(t))


def tabs(items, lr=True, dense=False):
    out = []
    if lr:
        out.append('<span class="lr">%s</span>' % kg("L"))
    for it in items:
        label, n, st = (it + ("", ""))[:3] if len(it) < 3 else it
        cnt = '<span class="n">%s</span>' % esc(n) if n != "" else ""
        out.append('<span class="tab %s">%s%s</span>' % (st, esc(label), cnt))
    out.append('<span class="sp"></span>')
    if lr:
        out.append('<span class="lr">%s</span>' % kg("R"))
    return '<div class="tabs %s">%s</div>' % ("dense" if dense else "", "".join(out))


def pane(inner, cls="", style="", head=None, headr=""):
    h = '<div class="ph">%s%s</div>' % (esc(head), '<span class="r">%s</span>' % headr if headr else "") if head else ""
    return '<div class="pane %s" style="%s">%s%s</div>' % (cls, style, h, inner)


# ------------------------------------------------------------------ cells
def initials(name):
    w = [x for x in name.replace(".", " ").replace("-", " ").split() if x]
    if len(w) >= 2:
        return (w[0][0] + w[1][0]).upper()
    return name[:2].upper()


def _cw(inner, state="", w=44, h=40, bk=None):
    return '<div class="cw %s" style="--cw:%dpx;--ch2:%dpx;%s">%s<b class="brk"></b></div>' % (
        state, w, h, ("--bk:%s;" % bk) if bk else "", inner)


def fighter_cell(name, state="", org=None, port=None, w=44, h=40, bk=None, label=False):
    o = ""
    if org == "geno":
        o = '<span class="org">G</span>'
    elif org == "add":
        o = '<span class="org add">+</span>'
    p = '<span class="ptag">%s</span>' % pt(port) if port else ""
    nm = '<span class="nm">%s</span>' % esc(name) if label else ""
    return _cw('<div class="cell"><div class="disc"><span class="ini">%s</span></div>%s%s%s</div>' % (initials(name), o, nm, p),
               state, w, h, bk=bk)


def drive_cell(fam, ring=None, state="", w=48, h=48, extra="", bk=None, pips=0, plus=False, ix=None):
    pip = '<span class="pip">%s</span>' % ("<i></i>" * pips) if pips else ""
    pl = '<span class="plus">+ MERGE</span>' if plus else ""
    n = '<span class="nq">%s</span>' % ix if ix else ""
    return _cw('<div class="cell drv">%s%s%s%s%s</div>' % (pl, n, drv(fam, ring), pip, extra), state + (" merge" if plus else ""), w, h, bk=bk)


def empty_cell(w=48, h=48, state="", label="", bk=None):
    return _cw('<div class="cell empty">%s%s</div>' % (ic("plus", "sm"), '<span class="nq">%s</span>' % label if label else ""), state, w, h, bk=bk)


def lock_cell(w=48, h=48, state="", label="", bk=None):
    return _cw('<div class="cell lock">%s%s</div>' % (ic("lock", "sm"), '<span class="nq">%s</span>' % label if label else ""), "dis " + state, w, h, bk=bk)


def stone(letter, color, state=""):
    if state == "empty":
        return '<span class="stone empty"><b>%s</b></span>' % ic("plus", "sm")
    if state == "lock":
        return '<span class="stone lock"><b>%s</b></span>' % ic("lock", "sm")
    return '<span class="stone %s"><b>%s</b></span>' % (color, esc(letter))


def rulecard(fam, name, rule, ring=None, state="", extra=""):
    st = ' style="box-shadow:inset 0 0 0 2px var(--ember)"' if state == "focus" else ""
    return ('<div class="rulecard"%s><div class="cw" style="--cw:40px;--ch2:40px"><div class="cell drv" style="background:var(--ground2)">%s</div></div>'
            '<div><div class="nm">%s</div><div class="ru">%s</div></div>%s</div>') % (st, drv(fam, ring), esc(name), esc(rule), extra)


def detail(title, what, rows=(), media="", kick="", more=None, mclass="", mh=None):
    q = "".join("<dt>%s</dt><dd>%s</dd>" % (esc(k), v) for k, v in rows)
    m = '<div class="media %s" style="%s">%s</div>' % (mclass, ("--mh:%dpx" % mh) if mh else "", media) if media else ""
    k = '<div class="kick">%s</div>' % esc(kick) if kick else ""
    mo = '<div class="more">%s<b>%s</b></div>' % (kg("Y"), esc(more)) if more else ""
    return '<div class="det">%s<div>%s<h2>%s</h2></div><div class="what">%s</div><dl class="q">%s</dl>%s</div>' % (m, k, esc(title), what, q, mo)


def note(text, kind="", ico="check", tm=60):
    return '<div class="note %s" style="--tm:%d%%"><span class="ni">%s</span><span>%s</span></div>' % (kind, tm, ic(ico, "sm"), text)


def sig(n, mid=False):
    return '<span class="sig %s">%s</span>' % ("mid" if mid else "", "".join('<i class="%s"></i>' % ("f" if i < n else "") for i in range(4)))


def bar(n, total=24, cls=""):
    return '<div class="bar %s">%s</div>' % (cls, "".join('<i class="%s"></i>' % ("f" if i < n else "") for i in range(total)))
