"""The ATLAS kit showcase: kit.html and its sheets (rendered to out/kit-*.png by build.py)."""
import os
import re

import parts
from parts import *
from parts import _cw
from screens_b import mini, P

# (html, selector, png, device scale, viewport width)
JOBS = [
    ("kit.html", "#k1", "kit-1-palette-type.png", 2, 1010),
    ("kit.html", "#k1b", "kit-1b-true-scale-640x480.png", 1, 700),
    ("kit.html", "#k2", "kit-2-controls.png", 2, 1010),
    ("kit.html", "#k3", "kit-3-cells-rules-models.png", 2, 1010),
    ("kit.html", "#k4", "kit-4-feedback-input-ports.png", 2, 1010),
    ("kit.html", "#k5", "kit-5-structure-motion.png", 2, 1010),
]


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(rgb):
    def f(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = _lum(_hex(a)), _lum(_hex(b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


PAL = [
    ("ground", "#0d1015", "E0: the backdrop", "ivory"), ("ground2", "#131820", "E0: quiet panes, wells", "ivory"), ("plate", "#1a1f29", "E1: a pane", "ivory"),
    ("plate2", "#222836", "E2: rows and cells", "ivory"), ("lift", "#2e3648", "E3: the thing in focus", "ivory"), ("edge", "#06080b", "front edge of a plate", "ivory"),
    ("ivory", "#f1ebdc", "text, primary", "ink"), ("text2", "#c8c4b8", "text, secondary", "ink"), ("muted", "#9aa2b4", "labels, hints", "ink"), ("dim", "#6e768a", "disabled only", "ink"),
    ("ember", "#ff7a3d", "focus and the one action", "ink"), ("jade", "#4fd6aa", "information, origin, on", "ink"), ("sun", "#f2c14e", "caution", "ink"), ("rose", "#ef4f7d", "danger", "ink"),
    ("p1", "#f0504a", "port 1: circle", "ink"), ("p2", "#4a90ff", "port 2: square", "ink"), ("p3", "#f3cf3e", "port 3: hexagon", "ink"), ("p4", "#42d68b", "port 4: diamond", "ink"), ("cpu", "#8f98aa", "CPU: hatched", "ink"),
]


def sw(name, hx, role, on):
    onhex = "#0b0d12" if on == "ink" else "#f1ebdc"
    r_plate = ratio(hx, "#1a1f29")
    r_on = ratio(hx, onhex)
    t = ('<div style="background:%s;color:%s;padding:8px 10px;height:112px;display:flex;flex-direction:column;justify-content:space-between;border-bottom:3px solid var(--edge);'
         'clip-path:polygon(5px 0,100%% 0,100%% calc(100%% - 5px),calc(100%% - 5px) 100%%,0 100%%,0 5px)">'
         '<div class="cap" style="font-size:16px;font-weight:700;letter-spacing:.08em">%s</div>'
         '<div style="font-size:12px;line-height:1.2"><span class="num">%s</span><br>%s<br><span class="num">%.1f:1 on plate &middot; %.1f:1 with %s</span></div></div>') % (
        hx, onhex, name, hx, role, r_plate, r_on, "ink" if on == "ink" else "ivory")
    return t


def section(id_, title, sub, inner, w=960):
    return ('<section class="sheet" id="%s" style="width:%dpx"><div class="grat"></div><div style="position:relative">'
            '<div style="display:flex;align-items:baseline;gap:14px;margin-bottom:14px"><span class="cap" style="font-size:30px;font-weight:700;letter-spacing:.08em">%s</span>'
            '<span class="muted" style="font-size:14px">%s</span><span class="cap dim" style="margin-left:auto;font-size:14px">ATLAS kit &middot; %s</span></div>%s</div></section>') % (
        id_, w, esc(title), esc(sub), id_, inner)


def lab(t):
    return '<div class="cap muted" style="font-size:13px;letter-spacing:.14em;margin:14px 0 6px">%s</div>' % esc(t)


def k1():
    swatches = '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px">%s</div>' % "".join(sw(*p) for p in PAL)
    scale = [("display", 64, "Barlow Condensed Bold", "GD'S MELEE", "cap"), ("hero", 44, "Barlow Condensed Bold", "STAGE CLEAR", "cap"),
             ("title", 28, "Barlow Condensed Bold", "KINDLING", "cap"), ("label", 20, "Barlow Condensed SemiBold, tracked", "ROOM CODE", "cap"),
             ("row", 16, "Source Sans 3 Semibold", "Time limit, Turbo, Render scale", ""), ("body", 14, "Source Sans 3 Semibold", "Your hits set the target Burning for 3 s.", ""),
             ("caption", 12, "Source Sans 3 Semibold / Barlow caps", "Hatched = disc art. Press A to join.", "")]
    rows = "".join('<div style="display:flex;align-items:baseline;gap:14px;padding:6px 0;border-bottom:1px solid var(--line)"><span class="num muted" style="width:92px;font-size:12px">%s %dpx</span>'
                   '<span class="%s" style="font-size:%dpx;font-weight:%d;line-height:1.1;letter-spacing:%s;flex:1">%s</span><span class="dim" style="font-size:12px;width:180px;text-align:right">%s</span></div>' % (
                       n, sz, "cap" if c else "", sz, 700 if sz >= 28 else 600, ".06em" if c else "0", esc(txt), f) for n, sz, f, txt, c in scale)
    elev = ''.join('<div style="flex:1"><div style="height:64px;background:%s;border-bottom:%dpx solid var(--edge);display:grid;place-items:center;clip-path:polygon(8px 0,100%% 0,100%% calc(100%% - 8px),calc(100%% - 8px) 100%%,0 100%%,0 8px);%s" class="cap">%s</div>'
                   '<div class="muted" style="font-size:12px;margin-top:6px">%s</div></div>' % (bg, th, ex, nm, ds) for nm, bg, th, ex, ds in (
        ("E0 ground", "var(--ground2)", 0, "", "backdrop; no edge"), ("E1 plate", "var(--plate)", 3, "", "pane; 3 px front edge"), ("E2 row", "var(--plate2)", 3, "", "row or cell; 3 px edge"),
        ("E3 lift", "var(--lift)", 3, "transform:translateY(-2px);border-bottom-color:var(--ember)", "focus: up 2 px, ember edge"), ("Modal", "var(--plate)", 6, "", "6 px edge over a 72% scrim")))
    inner = (lab("Palette: names, hex, contrast ratios (WCAG, against the plate and against the text colour that sits on it)") + swatches +
             lab("Type scale (the engine atlas: Source Sans 3 and Hasklug as shipped; Barlow Condensed is the one added family)") + '<div>%s</div>' % rows +
             lab("Depth with flat quads: five levels, one rule (a higher plate is lighter and shows a thicker front edge)") + '<div style="display:flex;gap:10px">%s</div>' % elev +
             lab("Shape: chamfers on two opposite corners only (two triangles per plate), no curves except the port circle") +
             '<div style="display:flex;gap:14px;align-items:center">%s%s%s%s%s</div>' % (
                 '<div class="pane" style="width:150px;height:56px"></div>', '<div class="row" style="width:150px"></div>', '<div class="cw" style="--cw:56px;--ch2:56px"><div class="cell"></div></div>',
                 tag("Tag"), '<div style="display:flex;gap:6px">%s%s%s%s</div>' % (pt(1, "lg"), pt(2, "lg"), pt(3, "lg"), pt(4, "lg"))))
    return section("k1", "Palette, type, depth", "Disabled text is the only text under 4.5:1.", inner)


def k1b():
    # a 1:1 640x480 crop: dsf 1, so 12 px is 12 px
    inner = ('<div class="grat"></div><div style="position:absolute;left:24px;top:20px;right:24px">'
             '<div class="cap muted" style="font-size:13px">True scale: this sheet is rendered 1:1, 640x480 logical = 640x480 pixels</div><div style="height:12px"></div>'
             '<div class="pane" style="padding:10px"><div class="ph">Smallest sizes in use</div>'
             '<div style="font-size:12px;line-height:1.3" class="muted">Caption, 12 px: Hatched = disc art. Press A to join. Hold X to open. [ROOM CODE] [PING] ms.</div>'
             '<div style="font-size:13px;margin-top:6px;color:var(--text2)">Tag and hint, 13 px: Turn on or off, Merge into slot 1, Back to fighters.</div>'
             '<div style="font-size:14px;margin-top:6px">Body, 14 px: Your hits set the target Burning for 3 s.</div>'
             '<div style="font-size:16px;margin-top:6px;font-weight:600">Row, 16 px: Time limit, Turbo, Render scale</div></div>'
             '<div style="height:10px"></div><div class="list" style="gap:5px">%s%s%s</div><div style="height:10px"></div>'
             '<div style="display:flex;gap:10px;align-items:center">%s%s%s%s %s</div></div>') % (
        row("Turbo", tog(True), "bolt", "focus"), row("Time limit", choice("8:00"), "clock"), row("Stocks", slider(3, 12, "4"), "flag"),
        hint("A", "Select"), hint("B", "Back"), hint("Y", "Details"), hint("S", "Start"), tag("Geno", "jade"))
    return '<section class="sheet" id="k1b" style="width:640px;height:480px;position:relative;overflow:hidden">%s</section>' % inner


def states_table():
    cols = ["Rest", "Focus", "Pressed", "Disabled", "Selected"]
    head = '<div></div>' + "".join('<div class="cap muted" style="font-size:13px;letter-spacing:.14em">%s</div>' % c for c in cols)

    def r(name, *cells):
        return '<div class="cap muted" style="font-size:13px;letter-spacing:.1em;align-self:center">%s</div>' % name + "".join('<div style="min-width:0">%s</div>' % c for c in cells)
    g = lambda a: a
    rows = [
        r("Button", btn("Play"), btn("Play", "focus"), btn("Play", "press"), btn("Play", "dis"), btn("Play", "sel")),
        r("List row", row("Window", "", "video"), row("Window", "", "video", "focus"), row("Window", "", "video", "press"), row("Window", "", "video", "dis"), row("Window", "", "video", "sel")),
        r("Toggle", row("Sync", tog(False)), row("Sync", tog(True), state="focus"), row("Sync", tog(True), state="press"), row("Sync", tog(False), state="dis"), row("Sync", tog(True), state="sel")),
        r("Choice", row("Mode", choice("Off")), row("Mode", choice("Off"), state="focus"), row("Mode", choice("Off"), state="press"), row("Mode", choice("Off"), state="dis"), row("Mode", choice("Off"), state="sel")),
        r("Slider", row("Vol", slider(7, 12)), row("Vol", slider(7, 12), state="focus"), row("Vol", slider(7, 12), state="press"), row("Vol", slider(7, 12), state="dis"), row("Vol", slider(7, 12), state="sel")),
        r("Fighter cell", fighter_cell("Falco"), fighter_cell("Falco", "focus", bk="var(--p1)"), fighter_cell("Falco", "focus", bk="var(--p1)").replace("translateY(-2px)", ""), fighter_cell("Falco", "dis"), fighter_cell("Falco", "sel")),
        r("Drive cell", drive_cell("red", None, "", 48, 48), drive_cell("red", None, "focus", 48, 48), drive_cell("red", None, "focus", 48, 48), lock_cell(48, 48), drive_cell("red", None, "sel", 48, 48)),
        r("Tab", '<div class="tabs" style="margin-bottom:0"><span class="tab">Video</span></div>', '<div class="tabs" style="margin-bottom:0"><span class="tab on">Video</span></div>', '<span class="dim" style="font-size:12px">held: as Focus</span>',
          '<div class="tabs" style="margin-bottom:0"><span class="tab dis">Video</span></div>', '<span class="dim" style="font-size:12px">the active tab is the selection</span>'),
    ]
    return '<div style="display:grid;grid-template-columns:70px repeat(5,1fr);gap:12px 8px;align-items:start;padding:8px 2px 14px">%s%s</div>' % (head, "".join(rows))


def k2():
    note_ = ('<div class="muted" style="font-size:13px;line-height:1.4">Focus is always three cues at once: the plate lifts 2 px, its front edge turns ember, and a tick (rows) or four registration brackets (cells) appear. '
             'Pressed drops 1 px and darkens the edge. Selected adds a jade bar and never moves. Disabled is hatched, not just dim. Toggles say ON or OFF and move their lit half.</div>')
    inner = states_table() + note_
    return section("k2", "Controls in every state", "Pad focus first. Mouse hover = Focus. Right click = B.", inner)


def k3():
    fams = [("red", "damage"), ("green", "speed"), ("blue", "defence"), ("yellow", "air"), ("purple", "status"), ("white", "wild")]
    cells = '<div style="display:flex;gap:12px">%s</div>' % "".join(
        '<div style="text-align:center">%s<div class="cap muted" style="font-size:12px;margin-top:4px">%s</div></div>' % (drive_cell(f, None, "", 64, 64), n) for f, n in fams)
    rings = '<div style="display:flex;gap:12px">%s</div>' % "".join(
        '<div style="text-align:center">%s<div class="cap muted" style="font-size:12px;margin-top:4px">%s</div></div>' % (drive_cell("purple", r, "", 64, 64), n) for r, n in ((None, "common"), ("magic", "magic"), ("rare", "rare"), ("unique", "unique")))
    big = '<div class="pane" style="width:230px"><div class="det"><div class="media" style="--mh:110px"><div style="width:96px;height:96px;position:relative">%s</div></div><div><div class="kick">Bag cell 1</div><h2>Kindling</h2></div><div class="what">%s</div></div></div>' % (drv("purple"), P["Kindling"][1])
    stones = '<div style="display:flex;gap:10px;align-items:center">%s</div>' % "".join(stone(c[0].upper(), c) for c in ("red", "green", "blue", "yellow", "purple", "white")) + \
             '<div style="display:flex;gap:10px;align-items:center;margin-top:8px">%s%s<span class="muted" style="font-size:13px">empty, locked</span></div>' % (stone("", "", "empty"), stone("", "", "lock"))
    slots = '<div style="display:flex;gap:8px">%s%s%s%s%s</div>' % (drive_cell("blue", None, "", 52, 52, ix=1), empty_cell(52, 52, label="2"), lock_cell(52, 52, label="3"),
                                                                     drive_cell("purple", None, "", 52, 52, plus=True, ix=4), drive_cell("yellow", None, "focus", 52, 52, bk="var(--ember)", ix=5))
    cards = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">%s%s</div>' % (rulecard("purple", "Cinder", P["Cinder"][1]), rulecard("blue", "Reprisal", P["Reprisal"][1], state="focus"))
    chips = '<div style="display:flex;gap:6px;flex-wrap:wrap">%s%s%s%s%s%s</div>' % (tag("Geno", "jade"), tag("Mod", "jade"), tag("Added", "sun"), tag("Conflict", "rose"), tag("Depth 5", "line"), tag("Press a button", "ember"))
    disc = ('<div style="display:flex;gap:14px;align-items:flex-end"><div><div class="cw" style="--cw:64px;--ch2:56px"><div class="cell"><div class="disc"><span class="ini">FA</span></div></div></div><div class="cap muted" style="font-size:12px;margin-top:4px">icon 64x56</div></div>'
            '<div><div class="cw" style="--cw:136px;--ch2:188px"><div class="cell"><div class="disc"><span class="ini" style="font-size:30px">FA</span><span class="lab">disc art</span></div></div></div><div class="cap muted" style="font-size:12px;margin-top:4px">portrait 136x188</div></div>'
            '<div class="muted" style="font-size:13px;max-width:220px;line-height:1.35">Disc art is never committed. The frame is the hatch, the two-letter abbreviation and, on large frames, the words disc art. Fighter names are plain strings.</div></div>')
    inner = ('<div style="display:grid;grid-template-columns:1fr 250px;gap:20px"><div>' + lab("Drive models: six families by shape and colour (drawn from the committed generator geometry)") + cells +
             lab("Rarity is an added ring, never a new body") + rings + lab("Equipment slots: filled, empty, locked, merge target, focus") + slots +
             lab("One rule per piece: name, one line, nothing else. Rarity and family are in the model") + cards + lab("Tags: origin, caution, conflict, depth, action") + chips + lab("Keystones: an arch stone, family colour, a letter") + stones +
             '</div><div>' + lab("The detail pane for one drive (cell: model only; pane: model, name, rule)") + big + '</div></div>' + lab("Disc-art frames") + disc)
    return section("k3", "Cells, rules, models", "A cell shows only the model. The name and the one rule appear for the piece in focus.", inner)


def k4():
    notes = '<div style="display:grid;grid-template-columns:1fr;gap:8px">%s%s%s%s</div>' % (
        note("<b>Merged!</b> Kindling got stronger.", "", "plus", 70), note("Another drive is on the floor.", "warn", "warn", 40),
        note("Could not reach the server.", "err", "x", 20), note("The guest is choosing a fighter.", "info", "clock", 55))
    dlg = ('<div style="position:relative;height:196px;background:var(--ground2);overflow:hidden"><div class="scrim"></div>'
           '<div class="dlg" style="width:300px"><h3>Quit this run?</h3><p>Your drives and keystone are lost.</p><div class="acts">%s%s</div></div></div>') % (btn("Keep playing", "focus", kgl="B"), btn("Quit", "", kgl="A"))
    tip = '<div style="display:flex;gap:12px;align-items:center"><span class="tip">Turbo: everyone plays faster.</span>%s</div>' % fighter_cell("Fox", "focus", bk="var(--p2)")
    gc = '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">%s</div>' % "".join(kg(g) for g in ("A", "B", "X", "Y", "Z", "L", "R", "START", "stick", "dpad"))
    kb = '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><span class="kk">Enter</span><span class="kk">Esc</span><span class="kk">&uarr;</span><span class="kk">&darr;</span><span class="kk">Tab</span><span class="kk">Ctrl</span><span class="kk">M</span><span style="width:14px"></span><span class="ms l"></span><span class="muted" style="font-size:13px">click = A</span><span class="ms r"></span><span class="muted" style="font-size:13px">right click = B</span></div>'
    ports = '<div style="display:flex;gap:10px;align-items:center">%s%s%s%s%s</div>' % (pt(1, "lg"), pt(2, "lg"), pt(3, "lg"), pt(4, "lg"), pt("cpu", "lg"))
    brk = '<div style="display:flex;gap:18px">%s</div>' % "".join(fighter_cell("Fox", "focus", w=44, h=44, bk=c) for c in ("var(--p1)", "var(--p2)", "var(--p3)", "var(--p4)", "var(--cpu)"))
    pcs = ('<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px"><div class="pcard p1">%s<div><div class="t1">Fox</div><div class="t2">Costume 1</div></div></div>'
           '<div class="pcard p2">%s<div><div class="t1">Falco</div><div class="t2">Costume 2</div></div></div>'
           '<div class="pcard cpu">%s<div><div class="t1">Marth</div><div class="t2">Level 3</div></div></div>'
           '<div class="pcard p3 empty">%s<div><div class="t1" style="color:var(--muted)">Open</div><div class="t2">Press A</div></div></div>'
           '<div class="pcard p4 closed">%s<div><div class="t1" style="color:var(--dim)">Closed</div></div></div></div>') % (pt(1), pt(2), pt("cpu"), pt(3), pt(4))
    prog = ('<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:center"><div><div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px"><span>Warming up the match</span><span class="num muted">[N] %%</span></div>%s</div>'
            '<div style="display:flex;gap:10px;align-items:center"><span class="cap muted" style="font-size:12px">Waiting</span>%s</div></div>') % (
        bar(14, 28), "".join('<span style="width:14px;height:14px;background:%s;transform:rotate(%d deg);display:inline-block"></span>' % ("var(--ember)" if i == 0 else "var(--line2)", 45) for i in range(4)))
    scroll = ('<div style="display:flex;gap:16px;align-items:stretch;height:100px"><div class="pane quiet" style="width:200px;padding:8px;display:flex;gap:8px"><div class="list" style="flex:1;gap:4px">%s%s</div>'
              '<div class="sb"><i style="top:0;height:30%%"></i></div></div><div class="muted" style="font-size:13px;align-self:center">A 4 px bar at the right edge; the count sits in the footer: <span class="num">3 / 24</span>. Lists wrap at the ends.</div></div>') % (row("Meta Knight", ""), row("Ultimate Kirby", ""))
    empty = ('<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px"><div class="empty-s" style="height:96px">%s<div>No replays yet.</div><div class="dim" style="font-size:13px">Finish a match to save one.</div></div>'
             '<div class="empty-s" style="height:96px">%s<div>No other mods are installed.</div><div class="dim" style="font-size:13px">%s Browse folders</div></div></div>') % (ic("ghost", "lg"), ic("folder", "lg"), kg("Y"))
    inner = ('<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px"><div>' + lab("Corner notes: one line, one icon, a timer rule") + notes + lab("Dialog: one question, two actions, B is always the safe one") + dlg +
             lab("Tooltip (hover or Y)") + tip + lab("Progress, waiting") + prog + '</div><div>' + lab("Key hints: GameCube pad") + gc + lab("Keyboard and mouse (as additions)") + kb +
             lab("Player ports: numeral + shape + colour (circle, square, hexagon, diamond, hatched CPU)") + ports + lab("Cursor and focus brackets in port colours") + brk + lab("Port cards: active, human, CPU, open, closed") + pcs.replace("grid-template-columns:repeat(5,1fr)", "grid-template-columns:repeat(2,1fr)") +
             lab("Scroll") + scroll + lab("Empty states") + empty + '</div></div>')
    return section("k4", "Feedback, input, ports", "Every signal has a shape or a word as well as a colour.", inner)


def wire(kind):
    """A tiny wireframe of the one structure, with the regions named."""
    box = lambda x, y, w, h, bg, txt="", ex="": '<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;background:%s;%s" class="cap">%s</div>' % (x, y, w, h, bg, ex, txt)
    t = lambda s_: '<span style="font-size:11px;letter-spacing:.1em;color:#8a92a6">%s</span>' % s_
    base = box(0, 0, 192, 144, "#0d1015") + box(10, 6, 110, 8, "#2b3242", "") + box(150, 6, 32, 8, "#2b3242") + box(0, 17, 192, 1, "#323a4b") + box(10, 128, 110, 8, "#2b3242") + box(150, 128, 30, 8, "#2b3242")
    if kind == "menu":
        body = "".join(box(10, 24 + i * 19, 90, 15, "#ff7a3d" if i == 1 else "#222836") for i in range(5)) + box(108, 24, 74, 96, "#1a1f29") + box(114, 30, 62, 26, "#131820") + box(114, 62, 50, 6, "#c8c4b8") + box(114, 74, 62, 4, "#6e768a") + box(114, 82, 40, 4, "#6e768a")
        name = "Two-word main menu"
    elif kind == "bag":
        body = box(10, 24, 108, 96, "#1a1f29") + "".join(box(16 + i * 17, 32, 14, 14, "#222836") for i in range(6)) + "".join(box(16 + i * 17, 56, 14, 14, "#ff7a3d" if i == 0 else "#222836") for i in range(4)) + "".join(box(16 + i * 12, 82, 10, 12, "#ef4f4f") for i in range(1)) + box(16, 102, 96, 12, "#131820") + box(124, 24, 58, 96, "#1a1f29") + box(132, 30, 40, 26, "#131820") + box(130, 62, 44, 6, "#c8c4b8") + box(130, 74, 36, 4, "#6e768a")
        name = "Envoy bag"
    else:
        body = box(10, 24, 108, 96, "#1a1f29") + "".join(box(16, 32 + i * 13, 96, 10, "#ff7a3d" if i == 0 else "#222836") for i in range(7)) + box(124, 24, 58, 96, "#1a1f29") + box(132, 30, 40, 30, "#131820") + box(130, 66, 44, 6, "#c8c4b8") + box(130, 78, 36, 4, "#6e768a")
        name = "Remap editor"
    return ('<div style="width:192px"><div style="position:relative;width:192px;height:144px;background:#0d1015">%s%s</div><div class="cap" style="font-size:14px;margin-top:6px;letter-spacing:.1em">%s</div></div>') % (base, body, name)


def k5():
    regions = ('<div style="position:relative;width:480px;height:360px;background:var(--ground);flex:none">'
               '<div style="position:absolute;left:24px;top:14px;right:24px;height:20px;background:#1d2433"></div><div style="position:absolute;left:32px;top:16px" class="cap"><span style="font-size:13px;color:var(--ivory)">1  WHERE: trail + chapter dots (header, always)</span></div>'
               '<div style="position:absolute;left:24px;top:46px;width:260px;height:262px;background:var(--plate);box-shadow:inset 3px 0 0 var(--ember)"></div><div style="position:absolute;left:34px;top:56px;width:244px" class="cap"><span style="font-size:13px">2  PRIMARY: the thing you act on<br>(list, grid, cards). One per screen.</span></div>'
               '<div style="position:absolute;left:296px;top:46px;width:160px;height:262px;background:var(--plate)"></div><div style="position:absolute;left:304px;top:56px;width:146px;line-height:1.35" class="cap"><span style="font-size:13px">3  EXPLAINER: for the focus only<br><br>WHAT: one rule line<br>WITH: what it works with<br>FROM: where it came from<br>Y = more</span></div>'
               '<div style="position:absolute;left:24px;top:322px;right:24px;height:22px;background:#1d2433"></div><div style="position:absolute;left:32px;top:325px" class="cap"><span style="font-size:13px">4  KEYS: the pad hints for this screen (footer, always)</span></div></div>')
    rules = ('<div style="flex:1;font-size:14px;line-height:1.45;color:var(--text2)"><div class="cap" style="font-size:16px;color:var(--ivory)">Rules of the structure</div>'
             '<ul style="margin:8px 0 0 18px"><li>One primary, one supporting pane. Everything else is quiet (ground tone, muted text).</li><li>Detail on demand: a cell shows the model only; a row shows a name and one value. Rules appear for the piece in focus.</li>'
             '<li>Same places on all 17 screens: trail top left, chapter dots top right, explainer on the right, keys at the bottom.</li><li>Never more than one short rule per piece on screen at once.</li>'
             '<li>Wide screens add a chapter rail on the left and widen the explainer: nothing new is shown.</li></ul></div>')
    wires = '<div style="display:flex;gap:16px">%s%s%s</div>' % (wire("menu"), wire("bag"), wire("remap"))
    motion = [("Focus lift", 80, "ease-out", "plate up 2 px, edge turns ember, brackets draw in"), ("Tab change", 120, "ease-out", "tab rises, plate colour joins the pane"), ("Explainer swap", 100, "linear", "cross-fade; skipped if reduced motion"),
              ("Dialog", 140, "ease-out", "scrim to 72%, plate rises 6 px"), ("Corner note", 160, "ease-out", "slides in; holds 3 s; timer rule drains"), ("Reward cards", 40, "stagger", "40 ms between the three offers"),
              ("Model turntable", 12000, "linear", "12 s a turn at rest, 6 s in focus"), ("Merge", 240, "ease-in-out", "two cells slide together, ring fades in")]
    mrows = "".join('<div style="display:flex;align-items:center;gap:10px;padding:5px 0;border-bottom:1px solid var(--line);font-size:13px"><span style="width:116px" class="cap">%s</span><span class="num" style="width:62px;color:var(--ember)">%s</span>'
                    '<span style="width:70px" class="muted">%s</span><span style="flex:1;height:8px;background:var(--ground);position:relative"><i style="position:absolute;left:0;top:0;bottom:0;width:%d%%;background:var(--ember)"></i></span><span class="muted" style="width:290px">%s</span></div>' % (
                        n, ("%d ms" % ms) if ms < 1000 else ("%d s" % (ms // 1000)), ez, max(3, min(100, ms // 30 if ms < 1000 else 100)), ds) for n, ms, ez, ds in motion)
    inner = (lab("The one structure: four places, same on every screen") + '<div style="display:flex;gap:24px;align-items:flex-start">%s%s</div>' % (regions, rules) +
             lab("The same structure serving a two-word menu, the bag and the remap editor") + wires + lab("Motion notes (what moves, how fast; the bar is relative length)") + mrows)
    return section("k5", "Structure and motion", "The system fits on one page: where things are, and how they move.", inner)


def write_kit(here, svg):
    parts.DRIVES["svg"] = svg
    body = "".join([k1(), k1b(), k2(), k3(), k4(), k5()])
    html = ('<!doctype html><html><head><meta charset="utf-8"><title>ATLAS kit showcase</title><link rel="stylesheet" href="tokens.css"><link rel="stylesheet" href="kit.css">'
            '<style>body{background:#05070a;padding:16px;display:flex;flex-direction:column;gap:24px;align-items:flex-start}.sheet{position:relative;background:var(--ground);padding:22px 24px 26px;overflow:hidden}'
            '.sheet .grat{position:absolute;inset:0}.sheet>div{position:relative}.sheet#k1b{padding:0}</style></head><body>%s%s</body></html>') % (defs(svg), body)
    with open(os.path.join(here, "kit.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
