"""SIGNAL kit showcase: kit.html and its PNG sheets (out/kit-*.png). Generated from ui.py so it cannot drift from the screens."""
from ui import *

KIT_PNGS = ["kit-1-foundations.png", "kit-2-states.png", "kit-3-pieces.png", "kit-4-input-and-motion.png"]
KIT_TITLES = ["Foundations: palette, type, ports, true size", "Components in every state", "Pieces: cells, rules, keystones, notes, dialogs, frames",
              "Input glyphs, focus signals, motion"]

PALETTE = [
    ("Ground", "ground", "#0c0e11", "the one ground"),
    ("Surface", "ground-2", "#14171c", "disc-art frames, tooltips"),
    ("Raised", "ground-3", "#1d2128", "pressed surface, stage stand-in"),
    ("Line", "line", "#2b3039", "the hairline, the only rule"),
    ("Off", "off", "#4a505a", "disabled; never carries meaning alone"),
    ("Dim", "dim", "#7a828e", "receded text"),
    ("Mid", "mid", "#b0b7c1", "secondary text, rule lines"),
    ("Bone", "bone", "#eeebe3", "text in focus"),
    ("Volt", "volt", "#d4ff2a", "ONLY focus and what is yours"),
    ("Alarm", "alarm", "#ff3b30", "destructive confirms, always with a word"),
]
PORTS = [("P1", "p1", "#ff8fa3", 1, False), ("P2", "p2", "#55aaff", 2, False), ("P3", "p3", "#b98cff", 3, False),
         ("P4", "p4", "#ffb547", 4, False), ("CPU", "pc", "#8a909a", 3, True)]
FAMS = [("Damage", "red", "#f43e36"), ("Speed", "green", "#22d26c"), ("Defence", "blue", "#3c7cff"), ("Air", "yellow", "#ffcc1e"),
        ("Status", "purple", "#b64aec"), ("Wild", "white", "#e8ecf6")]


def lum(h):
    h = h.lstrip("#")
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = lum(a), lum(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


CSS = """
body{background:#0c0e11}
.sheet{width:1280px;padding:44px 52px 52px;background:var(--ground);position:relative;overflow:hidden}
.sheet h1{font:800 56px/.9 var(--f-display);text-transform:uppercase;margin:0 0 4px;letter-spacing:-.004em}
.sheet h1 span{color:var(--volt)}
.sheet .sub{font:600 14px/18px var(--f-body);color:var(--mid);max-width:720px;margin-bottom:28px}
.sec{margin-top:34px}
.sec>.c.h{display:block;padding-bottom:8px;border-bottom:1px solid var(--line);margin-bottom:16px;color:var(--mid)}
.sw{display:flex;gap:12px;flex-wrap:wrap}
.sw>div{width:112px}
.sw i{display:block;height:64px;border:1px solid var(--line)}
.sw b{display:block;font:800 20px/1 var(--f-display);text-transform:uppercase;letter-spacing:.03em;margin:8px 0 2px}
.sw span{display:block;font:500 12px/16px var(--f-mono);color:var(--dim);letter-spacing:.02em}
.grid5{display:grid;grid-template-columns:170px repeat(5,1fr);gap:22px 18px;align-items:center}
.grid5 .hd{font:500 12px/16px var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--dim);border-bottom:1px solid var(--line);padding-bottom:8px}
.grid5>.rl{font:800 20px/1 var(--f-display);text-transform:uppercase;letter-spacing:.03em;color:var(--mid)}
.grid5>.rl small{display:block;font:500 12px/16px var(--f-mono);color:var(--dim);letter-spacing:.04em;margin-top:4px;text-transform:none}
.cellb{min-height:44px;position:relative}
.cellb .lens{position:static}
.cellb .lens .li{margin:0}
.na{font:500 12px var(--f-mono);color:var(--off);letter-spacing:.06em}
.ts{display:flex;align-items:baseline;gap:20px;margin-bottom:14px}
.ts .m{width:200px;flex:none}
.ts .m b{display:block;font:500 12px/16px var(--f-mono);color:var(--bone);letter-spacing:.06em}
.ts .m i{display:block;font:500 12px/16px var(--f-mono);color:var(--dim);font-style:normal;letter-spacing:.04em}
.two{display:flex;gap:40px;align-items:flex-start}
.true{width:640px;height:480px;position:relative;border:1px solid var(--line);flex:none}
.tp{width:100%;height:100%;position:relative;overflow:hidden;background:var(--ground)}
.tl{font:500 12px/16px var(--f-mono);color:var(--dim);letter-spacing:.04em}
.row{display:flex;gap:26px;align-items:center;flex-wrap:wrap}
.card{background:var(--ground);border:1px solid var(--line);padding:16px;position:relative}
.mo{display:flex;gap:16px;flex-wrap:wrap}
.mo>div{width:292px;border-top:3px solid var(--mid);padding-top:10px}
.mo b{display:block;font:800 20px/1 var(--f-display);text-transform:uppercase;letter-spacing:.03em}
.mo span{display:block;font:600 14px/18px var(--f-body);color:var(--mid);margin-top:4px}
.mo i{display:block;margin-top:8px;height:6px;background:var(--line);position:relative}
.mo i u{position:absolute;left:0;top:0;bottom:0;background:var(--volt);text-decoration:none}
.rc.f::before{content:"";position:absolute;left:-16px;top:0;bottom:0;width:6px;background:var(--volt)}
.rc.press{transform:translateX(3px)}
.tabs.press a.on{background:var(--bone);color:var(--ground);border-bottom-color:var(--bone);padding:0 4px 4px}
.mini-scr{width:640px;height:480px;position:relative;overflow:hidden;background:var(--ground);zoom:.62;border:1px solid var(--line)}
.legend{display:flex;gap:30px;flex-wrap:wrap}
.legend>div{width:240px}
.legend .d{display:block;margin-bottom:6px}
"""


def swatches():
    out = '<div class="sw">'
    for name, tok, hx, use in PALETTE:
        on_ground = ratio(hx, "#0c0e11")
        on_bone = ratio(hx, "#eeebe3")
        out += '<div><i style="background:%s"></i><b>%s</b><span>%s</span><span>vs ground %.1f:1</span><span>vs bone %.1f:1</span><span style="color:var(--mid);margin-top:4px">%s</span></div>' % (
            hx, name, hx, on_ground, on_bone, esc(use))
    return out + "</div>"


def ports():
    out = '<div class="row" style="gap:36px">'
    for n, cls, hx, t, cpu in PORTS:
        out += ('<div class="%s" style="width:150px"><div class="fx ac" style="gap:10px">%s<span class="pn">%s</span></div>'
                '<div class="tl" style="margin-top:8px">%s / %.1f:1 on ground</div><div class="tl">%s</div></div>' % (
                    cls, tally(t, cls, cpu=cpu, big=True), n, hx, ratio(hx, "#0c0e11"), "hollow bars: a CPU" if cpu else "%d bar%s" % (t, "" if t == 1 else "s")))
    out += "</div>"
    out += '<div class="tl" style="margin-top:12px;max-width:760px">Ports are told apart by the number of bars first, by the numeral second and by colour third, so no player loses a signal to colour vision. The colours are quiet by design and never fill a surface: they live in a 3 px bar, a numeral and a 3 px underline, so four players never make a rainbow.</div>'
    return out


def families():
    out = '<div class="row" style="gap:20px">'
    for n, k, hx in FAMS:
        out += '<div style="width:130px;text-align:left">%s<div class="c mid" style="margin-top:8px">%s</div><div class="tl">%s</div></div>' % (drive(k, "lg", None), n, hx)
    return out + "</div>"


def sheet1():
    h = '<div class="sheet" id="s1"><h1>Signal <span>/</span> kit 1</h1><div class="sub">One ground, one accent. Type does the work: six sizes and a mega, nothing else. Volt means exactly two things, focus and what is yours.</div>'
    h += '<div class="sec"><span class="c h">Palette: name, value, contrast</span>%s</div>' % swatches()
    h += '<div class="sec"><span class="c h">Player ports: tally bars, numeral, quiet colour</span>%s</div>' % ports()
    h += '<div class="sec"><span class="c h">Drive families: the real models, drawn from their geometry (3 px tick + shape carry the meaning)</span>%s</div>' % families()
    # type scale
    h += '<div class="sec"><span class="c h">Type scale (px at the 640x480 canvas). Barlow Condensed for words in focus, Source Sans 3 for sentences, Hasklug Mono for captions</span>'
    for nm, px, cls, sample, use in [
        ("mega", 160, "d s-mega", "Melee", "title and results only"),
        ("hero", 96, "d s-hero", "Versus", "the focus in a hub, big numerals"),
        ("focus", 56, "d s-focus", "Final Destination", "the focus in a list, a piece's name"),
        ("head", 32, "d s-head", "Collect the drives", "hub rows at rest, buttons, section words"),
        ("row", 20, "d s-row", "Unlock everything", "receded rows, tabs, options"),
        ("body", 14, "b", "Your hits Chill the target for 2 s.", "every sentence, one rule per line"),
        ("caption", 12, "c", "Move / Select / Back", "hints, labels, counters: the floor, never smaller"),
    ]:
        h += '<div class="ts"><div class="m"><b>%s %dpx</b><i>%s</i></div><div class="%s bone">%s</div></div>' % (nm, px, esc(use), cls, esc(sample))
    h += "</div>"
    # true size
    h += '<div class="sec"><span class="c h">The floor at true 640x480 scale (1 css px = 1 canvas px; open this PNG at 100%)</span><div class="two">'
    tp = '<div class="true"><div class="tp">'
    tp += crumb("Versus", "Melee", "Rules") + count("08", "08")
    tp += lens("list", 32, 62, 576, li("Items", v=opts(["Off", "Low", "Medium", "High"], "Off")), li("Stage choice", v=opts(["Pick", "Random", "List"], "Pick")),
               li("Turbo", f=True, v=opts(["Off", "On"], "On", f=True)),
               '<div class="help" style="padding-left:20px;margin:-8px 0 0">Match rule. In a room, the host sets it for everyone.</div>')
    tp += '<div class="abs" style="left:32px;top:300px;width:420px"><div class="c">12 px caption: the smallest text anywhere</div><div class="b" style="margin-top:6px">14 px body: sentences. 20 px row: receded words.</div></div>'
    tp += foot(hint("stick", "Move"), hint("a", "Next"), hint("b", "Back"))
    tp += "</div></div>"
    h += tp
    h += '<div style="width:420px"><div class="b">The canvas is 640x480 and every size above is in canvas px. Disc art is always a labelled frame, never the art.</div>'
    h += '<div style="margin-top:20px" class="row">%s%s%s</div>' % (disc(64, 56, "icon", mono="FOX"), disc(136, 188, "disc art"), disc(120, 68, "disc art"))
    h += '<div class="tl" style="margin-top:10px">Icon 64x56, portrait 136x188, stage preview: framed placeholders that never contain disc art. The monogram stands in for an icon on the roster.</div></div>'
    h += "</div></div></div>"
    return h


def states(label, sub, cells, na=False):
    out = '<div class="rl">%s<small>%s</small></div>' % (esc(label), esc(sub))
    for c in cells:
        out += '<div class="cellb">%s</div>' % c
    return out


def lensrow(**kw):
    return '<div class="lens list">%s</div>' % li("Items", **kw)


def sheet2():
    h = '<div class="sheet" id="s2"><h1>Signal <span>/</span> kit 2</h1><div class="sub">Every control in every state. There are no boxes: a state is a change of size, brightness, a bar, a bracket or one solid block, and volt only ever shows focus or what is yours.</div>'
    h += '<div class="grid5"><div class="hd"></div>' + "".join('<div class="hd">%s</div>' % x for x in ("Rest", "Focus", "Pressed", "Disabled", "Selected")) + "</div>"
    g = '<div class="grid5" style="margin-top:18px">'
    g += states("Button", "a word; focus is the one solid block", [btn("Play"), btn("Play", "f"), btn("Play", "press"), btn("Play", "dis"), btn("Play", "chosen")])
    g += states("List row", "bar + size; no box", [lensrow(), lensrow(f=True), lensrow(pressed=True), lensrow(off=True), lensrow(sel=True)])
    tabs_ = ["One", "Two", "Three"]
    g += states("Tab strip", "underline under the current word", [tabs(tabs_, "One", f=False), tabs(tabs_, "One", f=True),
                '<div class="tabs press"><a class="on">One</a><a>Two</a><a>Three</a></div>',
                '<div class="tabs"><a class="on is-off">One</a><a class="is-off">Two</a><a class="is-off">Three</a></div>', tabs(tabs_, "Two", f=False)])
    g += states("Toggle", "two words, one underlined", [opts(["Off", "On"], "Off"), opts(["Off", "On"], "On", f=True), opts(["Off", "On"], "On", press=True),
                opts(["Off", "On"], "Off", dis=True), opts(["Off", "On"], "On")])
    g += states("Choice", "a strip up to four, else stepped", [opts(["Low", "Medium", "High"], "Medium"), opts(["Low", "Medium", "High"], "Medium", f=True),
                opts(["Low", "Medium", "High"], "Medium", press=True), opts(["Low", "Medium", "High"], "Medium", dis=True), step("Medium")])
    g += states("Stepper", "arrows exist only in focus", ['<span class="step">%s 4 %s</span>' % (ARR_L.replace('<svg ', '<svg style="visibility:hidden" '), ARR_R.replace('<svg ', '<svg style="visibility:hidden" ')),
                step("4", f=True), step("4", f=True), '<span class="step" style="color:var(--off)">4</span>', step("4")])
    g += states("Slider", "a hairline, a tick, a numeral", [slider(40, "40", w=130), slider(40, "40", f=True, w=130), slider(64, "64", f=True, press=True, w=130), slider(40, "40", dis=True, w=130), '<span class="na">not selectable</span>'])
    g += states("Grid cell", "the model floats; brackets in focus", [drive("blue", "md", "magic"), '<div class="brk f" style="width:40px;height:40px">%s</div>' % drive("blue", "md", "magic"),
                drive("blue", "md", "magic", "press"), drive("blue", "md", "magic", "dis"), drive("blue", "md", "magic", "s")])
    g += states("Keystone", "the letter is the signal", [ks("E", "purple"), '<span class="brk f">%s</span>' % ks("E", "purple"), ks("E", "purple", "press"), ks("E", "purple", "dis"), ks("E", "purple", "on")])
    g += states("Rule card", "who, what, when, one line", [rc("Icebound", "Your hits Chill the target for 2 s.", "purple", "When"),
                '<div style="padding-left:16px;position:relative">%s</div>' % rc("Icebound", "Your hits Chill the target for 2 s.", "purple", "When", state="f"),
                '<div style="padding-left:6px">%s</div>' % rc("Icebound", "Your hits Chill the target for 2 s.", "purple", "When", state="press"),
                rc("Icebound", "Your hits Chill the target for 2 s.", "purple", "When", state="dis"),
                '<div class="fx" style="gap:8px"><span class="sel" style="margin-top:6px;flex:none"></span>%s</div>' % rc("Icebound", "Your hits Chill the target for 2 s.", "purple", "When")])
    g += "</div>"
    h += g
    h += '<div class="tl" style="margin-top:26px;max-width:880px">Pressed is a 3 px shift or an inverse fill, never a colour change. Disabled is dim with a strike or a dashed edge, so it is readable in greyscale. Selected is a hard volt square (what is yours) or a bone underline (a value that is set). A toggle never needs a box.</div>'
    h += "</div>"
    return h


def sheet3():
    h = '<div class="sheet" id="s3"><h1>Signal <span>/</span> kit 3</h1><div class="sub">The pieces that carry content: model cells, rules, keystones, notes, dialogs, frames, progress, scroll, empty states.</div>'
    h += '<div class="sec"><span class="c h">Model cell: the drive floats on the ground over a floor tick. Four sizes; rarity is a ring on the same model</span><div class="row" style="gap:30px;align-items:flex-end">'
    h += drive("red", "sm", None) + drive("green", "md", None) + drive("blue", "lg", "magic") + drive("yellow", "hg", "rare") + drive("purple", "hg", "unique") + drive("white", "hg", None)
    h += '</div><div class="tl" style="margin-top:10px">Rendered headlessly from the committed generator (envoy_drives/tools/make_drives.py): the same triangles and atlas ramps, flat shaded with a fixed light and a painter sort, which is what gd.kit.model does. Plain, magic, rare and unique rings shown.</div></div>'
    h += '<div class="sec"><span class="c h">One rule per piece, and a keystone with its price</span><div class="two" style="gap:60px"><div style="width:380px">'
    h += rc("Kindling", "Your hits set the target Burning for 3 s.", "purple", "When") + '<div style="height:18px"></div>'
    h += rc("Cinder", "Your hits deal 10% more damage to Burning targets", "red", "Always on") + '<div style="height:18px"></div>'
    h += rc("Echo Heart", "Every attack repeats a moment later at reduced damage.", "white", "Unique")
    h += '</div><div style="width:440px"><div class="fx" style="gap:16px">%s<div><div class="d s-row bone">Everburn</div><div class="b" style="margin-top:4px">Burning targets take 50%% more damage.</div><div class="b" style="color:var(--dim);margin-top:2px">Drawback: you take 15%% more damage.</div></div></div>' % ks("E", "purple", "on lg")
    h += '<div class="fx ac" style="gap:12px;margin-top:20px">%s%s%s%s<span class="c" style="margin-left:6px">held / free / locked</span></div></div></div></div>' % (
        ks("E", "purple", "on"), ks("+", "purple", "empty"), ks("S", "red", "dis"), segs(["purple", "purple", "red", "green", None, None]))
    h += '<div class="sec"><span class="c h">Corner notes (appear from the edge, hold, leave) and a tooltip</span><div class="row" style="gap:50px;align-items:flex-start">'
    h += '<div style="position:relative;width:290px;height:70px">%s</div>' % note("Merged!", "Lingering got stronger.", left=0, top=0, mine=True)
    h += '<div style="position:relative;width:290px;height:70px">%s</div>' % note("Saved", "Your settings are saved.", left=0, top=0)
    h += '<div style="width:290px">%s<div class="tl" style="margin-top:8px">A tooltip is the one small box: surface, hairline, 3 px left bar.</div></div>' % ('<span class="tip">Turbo changes the speed of the whole match for everyone in the room.</span>')
    h += '</div></div>'
    # dialog minis
    dlg1 = '<div class="mini-scr"><div class="scrim"></div><div class="dlg" style="top:150px"><div class="rule"></div><div class="d s-focus bone">Leave the room?</div><div class="b" style="margin-top:10px">Your opponent will see that you left.</div><div class="fx" style="gap:14px;margin-top:22px">%s%s</div></div></div>' % (btn("Stay", "f", sm=True), btn("Leave", "", sm=True))
    dlg2 = '<div class="mini-scr"><div class="scrim"></div><div class="dlg danger" style="top:150px"><div class="rule"></div><div class="d s-focus alarm">Erase all data?</div><div class="b" style="margin-top:10px">This cannot be undone. Your settings and records go.</div><div class="fx" style="gap:14px;margin-top:22px">%s%s</div></div></div>' % (btn("Keep", "f", sm=True), btn("Erase", "", sm=True, extra="danger"))
    h += '<div class="sec"><span class="c h">Dialog: no window, the screen dims and the question takes the screen; danger adds a word and a red rule, never colour alone</span><div class="row" style="gap:30px">%s%s</div></div>' % (dlg1, dlg2)
    # progress, scroll, empty
    h += '<div class="sec"><span class="c h">Progress, scroll and empty states</span><div class="two" style="gap:50px">'
    h += '<div style="width:300px"><div class="c" style="margin-bottom:10px">Loading / warm-up</div><div class="pg" style="margin-bottom:6px"><i style="width:62%"></i></div><div class="fx jb"><span class="c bone">Get ready</span><span class="c">62%</span></div>'
    h += '<div class="c" style="margin:22px 0 10px">Time left</div><div class="pg plain"><i style="width:78%%"></i></div><div class="c" style="margin:22px 0 10px">Build 4 / 6</div>%s</div>' % segs(["purple", "purple", "red", "green", None, None])
    h += '<div style="width:260px;height:150px;position:relative"><div class="c" style="margin-bottom:6px">+3 above</div>%s<div class="scrl" style="right:0;top:24px;height:110px"><i style="top:30px;height:30px"></i></div><div class="c" style="position:absolute;bottom:0">+9 below</div></div>' % (
        '<div class="lens dense" style="position:static;width:230px">%s%s%s</div>' % (li("Halberd"), li("Stage tour", f=True), li("Turbo combo")))
    h += '<div style="width:290px"><div class="empty-w">No mods</div><div class="b" style="margin-top:10px">Put a mod folder in mods/ and it shows up here.</div><div class="fx ac" style="gap:8px;margin-top:10px">%s<span class="c mid">Open the mods folder</span></div></div>' % glyph("y")
    h += '</div></div></div>'
    return h


def sheet4():
    h = '<div class="sheet" id="s4"><h1>Signal <span>/</span> kit 4</h1><div class="sub">Pad first. Every screen shows its focus and its hints; keyboard and mouse are additions. Motion is quick and always moves in the direction you went.</div>'
    h += '<div class="sec"><span class="c h">GameCube pad hints (original line drawings)</span><div class="row" style="gap:34px">'
    for n, lab in (("a", "A"), ("b", "B"), ("x", "X"), ("y", "Y"), ("z", "Z"), ("l", "L"), ("r", "R"), ("start", "Start"), ("stick", "Stick"), ("cstick", "C-stick"), ("dpad", "D-pad"), ("dpad_lr", "Left/right"), ("dpad_ud", "Up/down")):
        h += '<span class="hint">%s%s</span>' % (glyph(n), lab)
    h += '</div></div>'
    h += '<div class="sec"><span class="c h">Keyboard and mouse hints</span><div class="row" style="gap:34px">'
    for n, lab in (("Enter", "Select"), ("Esc", "Back"), ("Tab", "Next"), ("Space", "Change"), ("Up", "Up"), ("Down", "Down"), ("F3", "Overlay")):
        h += '<span class="hint">%s%s</span>' % (key(n), lab)
    for n, lab in (("lmb", "Click"), ("rmb", "Back"), ("wheel", "Scroll")):
        h += '<span class="hint">%s%s</span>' % (glyph(n), lab)
    h += '</div></div>'
    # focus signals
    h += '<div class="sec"><span class="c h">One focus language: what focus looks like on each kind of thing</span><div class="legend">'
    h += '<div><div class="d s-row bone">List row</div><div class="lens list" style="position:static">%s</div><div class="tl">volt bar, size steps up</div></div>' % li("Items", f=True)
    h += '<div><div class="d s-row bone">Cell</div><div class="brk f" style="width:40px;height:40px;margin:6px">%s</div><div class="tl" style="margin-top:10px">volt corner brackets</div></div>' % drive("red", "md", None)
    h += '<div><div class="d s-row bone">Button</div>%s<div class="tl" style="margin-top:10px">the one solid volt block</div></div>' % btn("Start", "f")
    h += '<div><div class="d s-row bone">Tab and option</div>%s<div class="tl" style="margin-top:10px">volt underline</div></div>' % tabs(["One", "Two"], "One", f=True)
    h += '<div><div class="d s-row bone">Mouse cursor</div><div style="position:relative;height:36px;width:120px">%s%s</div><div class="tl">bone arrow; volt over a target</div></div>' % (cursor(4, 4), cursor(60, 4, hot=True))
    h += '</div></div>'
    # motion strip
    h += '<div class="sec"><span class="c h">Motion notes: what moves, how fast. Reduced motion turns every move into a 0 ms cut and keeps the focus bar</span><div class="mo">'
    for nm, ms, txt, w in (("Focus moves", "70 ms", "The bar jumps and the type steps between sizes (20 to 56) with an ease-out. Nothing waits for it.", 20),
                           ("Screen change", "110 ms", "The new content slides 24 px in from the side you moved toward; the old one is a cut. Left and right are always the same direction.", 36),
                           ("Dialog", "160 ms", "The scrim fades to 90% and the question slides 16 px up. Back dismisses in 80 ms.", 52),
                           ("Corner note", "180 ms in", "Slides in from the edge, holds 2.4 s, leaves in 120 ms. At most one note at a time; a second replaces the first.", 60),
                           ("Press", "40 ms", "A 2 to 3 px shift and an inverse fill. No colour change, no bounce.", 12),
                           ("Hub peek", "110 ms", "Moving the focus in a hub swaps the peek column with the same slide.", 36)):
        h += '<div><b>%s <span style="display:inline;color:var(--volt);font-family:var(--f-mono);font-weight:500;font-size:12px;letter-spacing:.06em">%s</span></b><span>%s</span><i><u style="width:%d%%"></u></i></div>' % (nm, ms, txt, w)
    h += '</div></div></div>'
    return h


def kit_html():
    import ui
    ui.PREFIX[0] = ''
    body = sheet1() + sheet2() + sheet3() + sheet4()
    r = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>SIGNAL kit showcase</title>'
            '<link rel="stylesheet" href="kit.css"><style>%s</style></head><body>%s'
            '<script>document.body.style.margin="0"</script></body></html>' % (CSS, body))
    ui.PREFIX[0] = '../'
    return r


def render_kit(browser, here, out):
    pg = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
    pg.goto((here / "kit.html").as_uri())
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(200)
    for sid, png in zip(("s1", "s2", "s3", "s4"), KIT_PNGS):
        pg.locator("#" + sid).screenshot(path=str(out / png))
        print("  ", png)
    pg.close()
