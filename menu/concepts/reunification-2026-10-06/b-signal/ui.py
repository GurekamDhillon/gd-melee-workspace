"""SIGNAL: small HTML builders. Every screen and the kit sheet are generated from these, so the style lives in one place."""
import html


def esc(s):
    return html.escape(str(s), quote=False)


# ------------------------------------------------------------------ pad, keyboard and mouse glyphs (original, drawn here)
_T = 'font-family="Sig Mono, monospace" font-weight="700" font-size="12" text-anchor="middle"'
BONE, INK, MID = "#eeebe3", "#0c0e11", "#b0b7c1"
GL = {
    "a": '<svg class="g" viewBox="0 0 20 20" width="20" height="20"><circle cx="10" cy="10" r="9.5" fill="%s"/><text x="10" y="14.2" %s fill="%s">A</text></svg>' % (BONE, _T, INK),
    "b": '<svg class="g" viewBox="0 0 20 20" width="20" height="20"><circle cx="10" cy="10" r="8.2" fill="none" stroke="%s" stroke-width="2"/><text x="10" y="14.2" %s fill="%s">B</text></svg>' % (BONE, _T, BONE),
    "x": '<svg class="g" viewBox="0 0 28 20" width="28" height="20"><ellipse cx="14" cy="10" rx="13" ry="8.6" fill="none" stroke="%s" stroke-width="2"/><text x="14" y="14.2" %s fill="%s">X</text></svg>' % (BONE, _T, BONE),
    "y": '<svg class="g" viewBox="0 0 22 20" width="22" height="20"><ellipse cx="11" cy="10" rx="9.6" ry="9" fill="none" stroke="%s" stroke-width="2"/><text x="11" y="14.2" %s fill="%s">Y</text></svg>' % (BONE, _T, BONE),
    "z": '<svg class="g" viewBox="0 0 30 20" width="30" height="20"><polygon points="7,2 30,2 23,18 0,18" fill="%s"/><text x="15" y="14.2" %s fill="%s">Z</text></svg>' % (BONE, _T, INK),
    "l": '<svg class="g" viewBox="0 0 30 20" width="30" height="20"><polygon points="1,18 1,8 8,2 29,2 29,18" fill="none" stroke="%s" stroke-width="2"/><text x="15" y="14.2" %s fill="%s">L</text></svg>' % (BONE, _T, BONE),
    "r": '<svg class="g" viewBox="0 0 30 20" width="30" height="20"><polygon points="29,18 29,8 22,2 1,2 1,18" fill="none" stroke="%s" stroke-width="2"/><text x="15" y="14.2" %s fill="%s">R</text></svg>' % (BONE, _T, BONE),
    "start": '<svg class="g" viewBox="0 0 50 20" width="50" height="20"><rect x="1" y="2" width="48" height="16" fill="none" stroke="%s" stroke-width="2"/><text x="25" y="14.2" %s fill="%s">START</text></svg>' % (BONE, _T, BONE),
    "stick": '<svg class="g" viewBox="0 0 20 20" width="20" height="20"><circle cx="10" cy="10" r="8.6" fill="none" stroke="%s" stroke-width="2"/><circle cx="10" cy="10" r="3.4" fill="%s"/></svg>' % (BONE, BONE),
    "cstick": '<svg class="g" viewBox="0 0 20 20" width="20" height="20"><circle cx="10" cy="10" r="8.6" fill="none" stroke="%s" stroke-width="2"/><text x="10" y="14.2" %s fill="%s">C</text></svg>' % (BONE, _T, BONE),
    "dpad": '<svg class="g" viewBox="0 0 20 20" width="20" height="20"><polygon points="7,1 13,1 13,7 19,7 19,13 13,13 13,19 7,19 7,13 1,13 1,7 7,7" fill="none" stroke="%s" stroke-width="2" stroke-linejoin="miter"/></svg>' % BONE,
    "dpad_lr": '<svg class="g" viewBox="0 0 20 20" width="20" height="20"><polygon points="7,1 13,1 13,7 19,7 19,13 13,13 13,19 7,19 7,13 1,13 1,7 7,7" fill="none" stroke="%s" stroke-width="1.6"/><rect x="1" y="7" width="5" height="6" fill="%s"/><rect x="14" y="7" width="5" height="6" fill="%s"/></svg>' % (BONE, BONE, BONE),
    "dpad_ud": '<svg class="g" viewBox="0 0 20 20" width="20" height="20"><polygon points="7,1 13,1 13,7 19,7 19,13 13,13 13,19 7,19 7,13 1,13 1,7 7,7" fill="none" stroke="%s" stroke-width="1.6"/><rect x="7" y="1" width="6" height="5" fill="%s"/><rect x="7" y="14" width="6" height="5" fill="%s"/></svg>' % (BONE, BONE, BONE),
    "lmb": '<svg class="g" viewBox="0 0 16 22" width="16" height="22"><rect x="1" y="1" width="14" height="20" fill="none" stroke="%s" stroke-width="1.6"/><rect x="1" y="1" width="7" height="9" fill="%s"/><line x1="8" y1="1" x2="8" y2="10" stroke="%s" stroke-width="1.6"/></svg>' % (BONE, BONE, INK),
    "rmb": '<svg class="g" viewBox="0 0 16 22" width="16" height="22"><rect x="1" y="1" width="14" height="20" fill="none" stroke="%s" stroke-width="1.6"/><rect x="8" y="1" width="7" height="9" fill="%s"/><line x1="8" y1="1" x2="8" y2="10" stroke="%s" stroke-width="1.6"/></svg>' % (BONE, BONE, INK),
    "wheel": '<svg class="g" viewBox="0 0 16 22" width="16" height="22"><rect x="1" y="1" width="14" height="20" fill="none" stroke="%s" stroke-width="1.6"/><rect x="6" y="4" width="4" height="7" fill="%s"/></svg>' % (BONE, BONE),
}


def glyph(name):
    return GL[name]


def key(label):
    return ('<span style="display:inline-block;border:1px solid #b0b7c1;border-bottom-width:3px;padding:0 6px;min-width:20px;text-align:center;'
            'font-family:var(--f-mono);font-weight:700;font-size:12px;line-height:14px;color:#eeebe3;text-transform:uppercase">%s</span>' % esc(label))


def hint(g, text, off=False):
    gl = GL[g] if g in GL else key(g)
    return '<span class="hint%s">%s%s</span>' % (" is-off" if off else "", gl, esc(text))


def foot(*hints, right=""):
    return '<div class="foot">%s<span class="gap"></span>%s</div>' % ("".join(hints), right)


def crumb(*parts):
    out = []
    for i, p in enumerate(parts):
        out.append('<span class="%s">%s</span>' % ("here" if i == len(parts) - 1 else "", esc(p)))
    return '<div class="crumb c">%s</div>' % '<em>/</em>'.join(out)


def count(a, b, label=""):
    return '<div class="count c">%s<b>%s</b> <i>/</i> %s</div>' % (esc(label + " ") if label else "", esc(a), esc(b))


# ------------------------------------------------------------------ lists
def li(text, f=False, v="", cls="", sel=False, sub="", badge="", off=False, pressed=False):
    c = "li" + (" f" if f else "") + (" is-off" if off else "") + (" pressed" if pressed else "") + (" " + cls if cls else "")
    s = '<div class="%s">' % c
    if sel:
        s += '<span class="sel"></span>'
    s += esc(text)
    if badge:
        s += '<span class="badge">%s</span>' % esc(badge)
    if sub:
        s += '<span class="sub">%s</span>' % sub
    if v:
        s += '<span class="v">%s</span>' % v
    return s + "</div>"


def lens(mode, left, top, width, *rows):
    return '<div class="lens %s" style="left:%spx;top:%spx;width:%spx">%s</div>' % (mode, left, top, width, "".join(rows))


def opts(options, on, f=False, dis=False, press=False):
    cls = "opts" + (" f" if f else "") + (" dis" if dis else "") + (" press" if press else "")
    return '<span class="%s">%s</span>' % (cls, "".join('<i class="%s">%s</i>' % ("on" if o == on else "", esc(o)) for o in options))


ARR_L = '<svg viewBox="0 0 9 14"><polygon points="9,0 9,14 0,7"/></svg>'
ARR_R = '<svg viewBox="0 0 9 14"><polygon points="0,0 0,14 9,7"/></svg>'


def step(value, f=False):
    return '<span class="step%s">%s%s%s</span>' % (" f" if f else "", ARR_L, esc(value), ARR_R)


def slider(pct, num, f=False, dis=False, press=False, w=150):
    cls = "sl" + (" f" if f else "") + (" dis" if dis else "") + (" press" if press else "")
    return '<span class="%s"><span class="tr" style="width:%dpx;--w:%d%%"><span class="fl"></span><span class="tk"></span></span><span class="n">%s</span></span>' % (cls, w, pct, esc(num))


def tabs(items, active, f=True, counts=None, left=None, right=None, extra_style=""):
    counts = counts or {}
    out = ""
    if left:
        out += GL[left]
    for t in items:
        small = '<small>%s</small>' % esc(counts[t]) if t in counts else ""
        out += '<a class="%s">%s%s</a>' % ("on" if t == active else "", esc(t), small)
    if right:
        out += GL[right]
    return '<div class="tabs%s" style="%s">%s</div>' % (" f" if f else "", extra_style, out)


def btn(text, state="", sm=False, extra=""):
    return '<span class="bt %s%s %s">%s</span>' % (state, " sm" if sm else "", extra, esc(text))


# ------------------------------------------------------------------ models, discs, ports
PREFIX = ['../']


def drive(fam, size="md", rarity=None, state="", frame=None):
    src = "%sassets/drives/drive_%s%s.png" % (PREFIX[0], fam, "_" + rarity if rarity else "")
    return '<div class="gc %s %s"><img src="%s" alt=""></div>' % (size, state, src)


def drive_slot(size="md", kind="empty"):
    return '<div class="gc %s %s"><span class="slot"></span></div>' % (size, kind)


def disc(w, h, label="disc art", cls="", style="", mono=None):
    corners = '<i class="tl"></i><i class="tr2"></i><i class="bl"></i><i class="br"></i>' if not mono else ""
    return '<div class="disc %s%s" data-l="%s"%s style="width:%spx;height:%spx;%s">%s</div>' % (
        cls, " mono" if mono else "", esc(label), (' data-c="%s"' % esc(mono)) if mono else "", w, h, style, corners)


def tally(n, port="p1", cpu=False, big=False, mini=False):
    return '<span class="tally %s%s%s%s">%s</span>' % (port, " cpu" if cpu else "", " big" if big else "", " mini" if mini else "", "<b></b>" * n)


def ks(letter, colour, state="", size=""):
    return '<span class="ks k-%s %s %s">%s</span>' % (colour, state, size, esc(letter))


def rc(name, rule, colour, when="", state="", style=""):
    w = '<span class="c">%s</span>' % esc(when) if when else ""
    return '<div class="rc k-%s %s" style="%s"><i class="tick"></i><div><div class="rn">%s%s</div><div class="rl">%s</div></div></div>' % (
        colour, state, style, esc(name), w, esc(rule))


def note(head, body, left=None, top=None, right=None, bottom=None, mine=False, extra=""):
    pos = ";".join("%s:%spx" % (k, v) for k, v in (("left", left), ("top", top), ("right", right), ("bottom", bottom)) if v is not None)
    return '<div class="note%s" style="%s;%s"><div class="nh">%s</div><div class="nb">%s</div></div>' % (" mine" if mine else "", pos, extra, esc(head), esc(body))


def cursor(left, top, hot=False):
    return '<svg class="cur%s" style="left:%spx;top:%spx" viewBox="0 0 14 20"><polygon points="1,1 1,17 5,13 8,19 11,17.5 8,12 13,12"/></svg>' % (" hot" if hot else "", left, top)


def segs(items):
    """items: list of colour name or None (empty)"""
    return '<span class="segs">%s</span>' % "".join(
        ('<b style="--kc:var(--f-%s)"></b>' % c) if c else '<b class="e"></b>' for c in items)


# ------------------------------------------------------------------ page
def page(title, body, wide=False, width=None, height=480, extra_css=""):
    w = width or (853.3333 if wide else 640)
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>%(t)s</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="../kit.css">
<style>%(css)s .scr{width:%(w)spx;height:%(h)spx}</style></head>
<body><div class="scr%(wc)s" id="scr">%(b)s</div>
<script>
/* opened from disk: fit the %(w0)s x %(h)s canvas to the window; the renderer passes ?z=2 etc. */
(function(){var q=new URLSearchParams(location.search).get('z');var z=q?parseFloat(q):Math.min(innerWidth/%(w)s,innerHeight/%(h)s);document.body.style.zoom=z;})();
</script></body></html>""" % {"t": esc(title), "b": body, "w": w, "w0": int(w), "h": height, "wc": " wide" if wide else "", "css": extra_css}
