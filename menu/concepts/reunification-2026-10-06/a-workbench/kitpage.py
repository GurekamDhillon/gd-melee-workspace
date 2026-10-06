"""The kit showcase (kit.html -> out/kit-*.png) and the gallery (index.html)."""
import os
import re
from parts import *

TOK = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens.css"), encoding="utf-8").read()


def tokens():
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", TOK))


T = tokens()


def lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    la, lb = lum(a), lum(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def demo(label, html, w=None, cls="", style=""):
    return '<div class="demo %s" style="%s%s"><div class="stage">%s</div><div class="cap">%s</div></div>' % (cls, ("width:%spx;" % w) if w else "", style, html, esc(label))


def sheet(id_, title, sub, body):
    return ('<section class="ks" id="%s"><div class="khead">%s<span class="print" style="margin-left:16px">%s</span></div>%s</section>' % (id_, tape(title), esc(sub), body))


CSS = """
body{background:#0b0f0d;margin:0;padding:0}
.ks{position:relative;width:1600px;padding:28px 32px 36px;margin:0 0 24px;box-sizing:border-box;background-color:var(--mat);
 background-image:linear-gradient(var(--mat-grid) 1px,transparent 1px),linear-gradient(90deg,var(--mat-grid) 1px,transparent 1px);background-size:16px 16px}
.khead{display:flex;align-items:center;margin-bottom:22px;zoom:1.2}
.grid{display:flex;flex-wrap:wrap;gap:22px 26px;align-items:flex-start}
.demo{display:flex;flex-direction:column;gap:10px}
.demo .stage{position:relative;zoom:1.5;margin-bottom:14px}
.demo.f{width:285px}
.demo .cap{font-family:var(--mono);font-weight:500;font-size:12px;color:var(--mat-print);text-transform:uppercase;letter-spacing:.04em;max-width:420px}
.h2{font-weight:900;font-size:20px;letter-spacing:.12em;text-transform:uppercase;color:var(--bone);margin:26px 0 12px}
.h2 small{font-family:var(--mono);font-weight:500;font-size:12px;color:var(--mat-print);letter-spacing:.04em;margin-left:12px}
.mat-card{width:236px;display:flex;flex-direction:column;gap:10px}
.mat-card .sw{height:96px;position:relative;display:flex;align-items:center;justify-content:center}
.mat-card .sw>*{zoom:1.3}
.mat-card h5{margin:0;font-size:16px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;color:var(--bone)}
.mat-card p{margin:0;font-size:14px;font-weight:600;color:var(--bone);line-height:1.25;opacity:.9}
table.mx{border-collapse:separate;border-spacing:0 16px;color:var(--bone)}
table.mx th{font-family:var(--mono);font-weight:500;font-size:12px;color:var(--mat-print);text-transform:uppercase;letter-spacing:.06em;text-align:left;padding:0 22px 0 0}
table.mx td{padding:6px 28px 14px 0;vertical-align:middle}
table.mx td.k{font-weight:900;font-size:16px;letter-spacing:.1em;text-transform:uppercase;width:130px}
table.mx .z{zoom:1.3;display:inline-block}
.swatch{width:196px;display:flex;flex-direction:column}
.swatch .c{height:64px;border-radius:3px;box-shadow:0 3px 0 rgba(0,0,0,.4)}
.swatch .t{font-weight:900;font-size:14px;letter-spacing:.06em;color:var(--bone);margin-top:8px;text-transform:uppercase}
.swatch .m{font-family:var(--mono);font-weight:500;font-size:12px;color:var(--mat-print)}
.cr{width:296px;display:flex;align-items:center;gap:10px;font-weight:700;font-size:14px;color:var(--bone)}
.cr .s{width:112px;height:34px;display:flex;align-items:center;justify-content:center;border-radius:3px;font-weight:900;font-size:16px;flex:none}
.cr b{font-family:var(--mono);font-weight:500;font-size:12px;color:var(--mat-print)}
.ok{color:var(--ok)}
.spec{display:flex;align-items:baseline;gap:16px;color:var(--bone);margin-bottom:8px}
.spec span.n{font-family:var(--mono);font-weight:500;font-size:12px;color:var(--mat-print);width:150px;flex:none}
.frame640{position:relative;width:640px;height:200px;background-color:var(--mat);outline:2px dashed var(--mat-print);outline-offset:6px;overflow:hidden}
"""


def sw(name, key, textcol=None, desc=""):
    hexv = T[key]
    return '<div class="swatch"><div class="c" style="background:%s"></div><div class="t">%s</div><div class="m">%s · --%s</div><div class="m">%s</div></div>' % (hexv, name, hexv, key, desc)


def cr(label, fg, bg, kind="text"):
    r = ratio(T[fg], T[bg])
    need = 4.5 if kind == "text" else 3.0
    return ('<div class="cr"><span class="s" style="background:%s;color:%s">Aa</span><span><div>%s</div><b>%.1f : 1 · %s %s</b></span></div>'
            % (T[bg], T[fg], esc(label), r, "AA text" if kind == "text" else "non-text 3:1", "pass" if r >= need else "FAIL"))


def k1():
    mats = [
        ("Chipboard", "A choice you can pick up: buttons, list rows, bins, cards.", '<div class="board row" style="width:120px;height:44px">PICK</div>'),
        ("Puck", "Something you own or play: drives, pegs, fighters.", puck("red", "fam-red", style="margin:0")),
        ("Kraft tag", "Information about the lifted piece. One rule per tag.", '<div style="width:130px">%s</div>' % tag("NAME", "One rule.", w=130)),
        ("Paper slip", "An event, set down at the corner: notices and warnings.", slip("Set down", w=120, cls="flat")),
        ("Cast steel", "Heavy and committed: keystones, rails, clamps, quit.", '<div class="key kc-red" style="margin:0"><div class="face"><b>K</b></div><div class="band"></div></div>'),
        ("Label tape", "Where you are: titles, breadcrumbs, the hint rail.", tape("Where")),
        ("Recess", "Where things go: trays, sockets, windows, switches.", '<div class="sock empty" style="width:80px;height:64px"></div>'),
        ("Manila folder", "A page that holds boards: settings, LAB, launcher tab.", '<div class="sheet" style="width:130px;height:60px;border-radius:3px"></div>'),
    ]
    mc = "".join('<div class="mat-card"><div class="sw">%s</div><h5>%s</h5><p>%s</p></div>' % (h, n, d) for n, d, h in mats)
    pal = [("Mat", "mat", "Work surface"), ("Mat grid", "mat-grid", "16 px print"), ("Recess", "recess", "Sockets, trays"), ("Board", "board", "Choices"), ("Kraft", "kraft", "Tags"), ("Folder", "folder", "Pages"),
           ("Paper", "paper", "Dialogs"), ("Slip", "slip", "Notices"), ("Steel", "steel", "Heavy"), ("Tape", "tape", "Where"), ("Focus orange", "focus", "Grip clamps only"),
           ("Ink", "ink", "Text on pieces"), ("Bone", "bone", "Text on mat"), ("Mat print", "mat-print", "Captions"), ("Ok", "ok", "On / ready"), ("Danger", "danger", "Warn / quit"),
           ("P1 circle", "p1", "Red"), ("P2 square", "p2", "Blue"), ("P3 triangle", "p3", "Yellow"), ("P4 diamond", "p4", "Green"), ("CPU hexagon", "cpu", "Grey")]
    pals = "".join(sw(n, k, desc=d) for n, k, d in pal)
    crs = "".join([cr("Ink on chipboard (rows, buttons)", "ink", "board"), cr("Ink on kraft (tags)", "ink", "kraft"), cr("Ink on paper (dialogs)", "ink", "paper"), cr("Ink on slip (notices)", "ink", "slip"),
                   cr("Ink on folder (pages)", "ink", "folder"), cr("Bone on mat (printed text)", "bone", "mat"), cr("Bone on tape (titles, hints)", "bone", "tape"),
                   cr("Mat print on mat (captions)", "mat-print", "mat"), cr("Bone on recess (value windows)", "bone", "recess"), cr("Focus orange on mat (clamps)", "focus", "mat", "non"), cr("Focus orange on recess (clamps)", "focus", "recess", "non"), cr("P1 red on mat", "p1", "mat", "non"), cr("P2 blue on mat", "p2", "mat", "non"), cr("P3 yellow on mat", "p3", "mat", "non"),
                   cr("P4 green on mat", "p4", "mat", "non"), cr("CPU grey on mat", "cpu", "mat", "non"), cr("Ink on ok green (ON)", "ink", "ok")])
    thick = ('<div class="grid" style="gap:44px">%s%s%s</div>' % (
        demo("REST: edge 3, shadow +4/+7", '<div class="board row" style="width:150px">Rest</div>', style="padding:6px"),
        demo("LIFTED: edge 7, shadow +10/+17, clamps, one per screen", '<div class="board row focus" style="width:150px">Lifted</div>', style="padding:14px 18px 30px 14px"),
        demo("PRESSED: edge 1, shadow +2/+3", '<div class="board row pressed" style="width:150px">Pressed</div>', style="padding:6px")))
    roles = [("caption 12", "12px", "Source Sans 3 Bold · Hasklug for printed captions"), ("body 14", "14px", "Tags, notices, hint text"), ("row 16", "16px", "Rows, descriptions"),
             ("label 20", "20px", "Buttons, tape titles"), ("title 24", "24px", "Dialog titles"), ("heading 32", "32px", "Placings"), ("hero 44", "44px", "Caps only"), ("display 56", "56px", "Caps only, title tiles")]
    sp = "".join('<div class="spec"><span class="n">%s</span><span style="font-size:%s;font-weight:900;letter-spacing:.04em;line-height:1.1">%s</span></div>' % (n, f, "WORKBENCH Aa 0123" if int(f[:-2]) >= 32 else "Pick up the piece, put it back 0123") for n, f, _ in roles)
    # (zoomed to 1.5 so the page is readable; the TRUE size frame below is not zoomed)
    spz = '<div style="zoom:1.0">%s</div>' % sp
    true = ('<div class="frame640"><div style="position:absolute;left:20px;top:16px;color:var(--bone);font-size:12px;font-weight:700">caption 12: Pick up the piece, put it back. Never smaller.</div>'
            '<div style="position:absolute;left:20px;top:40px;color:var(--bone);font-size:14px;font-weight:700">body 14: Smash attacks become ice</div>'
            '<div style="position:absolute;left:20px;top:66px;color:var(--bone);font-size:16px;font-weight:900;letter-spacing:.06em">ROW 16: STOCKS</div>'
            '<div style="position:absolute;left:20px;top:100px">%s</div><div style="position:absolute;left:260px;top:104px;width:260px">%s</div><span class="print" style="position:absolute;left:20px;bottom:10px">true 640x480 scale, 1 px = 1 canvas unit</span></div>'
            % ('<div class="board row" style="width:200px;height:36px">Time limit</div>', tag("ICEBOUND", "Your hits Chill the target for 2 s.", w=200)))
    return sheet("k1", "Workbench: foundations", "tokens.css · materials, palette with contrast, thickness, type",
                 '<div class="h2">One surface, eight materials <small>each material means one thing</small></div><div class="grid" style="gap:26px 30px">%s</div>' % mc
                 + '<div class="h2">Thickness <small>depth is a visible edge plus a hard offset shadow: three flat quads, no gradient, no glow</small></div>' + thick
                 + '<div class="h2">Palette <small>names, hex, token</small></div><div class="grid" style="gap:18px 22px">%s</div>' % pals
                 + '<div class="h2">Contrast <small>text 4.5:1, signals and clamps 3:1</small></div><div class="grid" style="gap:12px 26px">%s</div>' % crs
                 + '<div class="h2">Type scale <small>engine roles; text never below 12 px at 640x480</small></div><div class="grid" style="align-items:flex-start;gap:40px"><div style="zoom:1.0">%s</div><div>%s</div></div>' % (spz, true)
                 + '<div class="h2">Space and shape <small>4 px grid · radii 3 (board) 7 (token) round (peg) · title-safe inset 32 x 24</small></div><div class="grid" style="gap:28px;align-items:flex-end">%s</div>' % "".join('<div style="display:flex;flex-direction:column;gap:6px;align-items:flex-start"><div style="width:%dpx;height:%dpx;background:var(--board)"></div><span class="print">%d px</span></div>' % (n * 2, n * 2, n) for n in (4, 8, 12, 16, 24, 32)))


def k2():
    B = lambda inner, cls="": '<div class="board btn %s" style="min-width:128px">%s</div>' % (cls, inner)
    R = lambda cls="", **k: row("Stocks", cls=cls, style="width:170px", **k)
    cells = {
        "Button": [B("Start"), B("Start", "focus"), B("Start", "pressed"), B("Start", "off"), B("Start", "sel").replace('class="board btn sel"', 'class="board btn sel"').replace("Start", pin() + "Start")],
        "List row": [R(), R("focus"), R("pressed"), R("off"), R("sel")],
        "Toggle": ['<span style="display:inline-block;padding:4px">%s</span>' % tog(False), '<span class="board row focus" style="width:170px;padding:0 8px;height:34px;display:inline-flex">Turbo<span class="sp"></span>%s</span>' % tog(True),
                   '<span class="tog on" style="transform:translate(1px,2px)"><b>ON</b></span>', tog(True, "dis"), '<span style="display:inline-block;padding:4px">%s</span>' % tog(True)],
        "Choice": [choice("Stock", 3, 0, wide=70), '<span class="board row focus" style="width:170px;padding:0 8px;height:34px;display:inline-flex"><span class="sp"></span>%s</span>' % choice("Stock", 3, 1, wide=70),
                   '<span class="choice"><span class="arr l" style="transform:translate(1px,2px)"></span><span class="win" style="min-width:70px">Stock</span><span class="arr r"></span></span>', '<span style="opacity:.4">%s</span>' % choice("Stock", 3, 0, wide=70), choice("Time", 3, 2, wide=70)],
        "Slider": [slider(0.4, 130), '<span style="position:relative;display:inline-block">%s</span>' % slider(0.6, 130).replace('class="car"', 'class="car" style="box-shadow:0 7px 0 var(--board-edge),8px 13px 0 var(--shadow);transform:translate(-2px,-5px);left:%spx"' % (0.6 * 114)),
                   slider(0.5, 130).replace('class="car"', 'class="car" style="transform:translate(1px,2px);box-shadow:0 1px 0 var(--board-edge)"'), '<span style="opacity:.4">%s</span>' % slider(0.4, 130), slider(0.8, 130)],
        "Grid cell + model": [sock(puck("red", "seat sm", style="margin:6px"), style="width:52px;height:52px"), sock(puck("red", "sm focus", style="margin:6px"), style="width:52px;height:52px;overflow:visible"),
                              sock(puck("red", "sm", style="margin:6px;transform:translate(1px,3px);--pe:1px"), style="width:52px;height:52px"), sock(puck("red", "sm ghost", style="margin:6px"), style="width:52px;height:52px"),
                              sock(puck("red", "sm seat", style="margin:6px") + '<span style="position:absolute;right:-4px;top:-4px">%s</span>' % pin().replace('class="pin"', 'class="pin" style="display:inline-flex;background:var(--ok)"'), style="width:52px;height:52px;overflow:visible")],
    }
    hdr = "".join("<th>%s</th>" % h for h in ("", "Rest", "Focus (lifted)", "Pressed", "Disabled", "Selected (seated)"))
    body = "".join('<tr><td class="k">%s</td>%s</tr>' % (k, "".join('<td><span class="z">%s</span></td>' % c for c in v)) for k, v in cells.items())
    tabsrow = ('<div class="grid" style="gap:30px">%s%s%s</div>' % (
        demo("tab strip: live tab is tall and joined to the folder; others sit behind, lower", tabs(["VIDEO", "AUDIO", "CONTROLS", "ONLINE"], 0) + '<div class="sheet" style="height:36px;width:380px;border-radius:0 3px 3px 3px"></div>'),
        demo("focus on a tab: it rises 2 px and gets the orange top edge", tabs(["VIDEO", "AUDIO", "CONTROLS", "ONLINE"], 0, focus=2) + '<div class="sheet" style="height:36px;width:380px;border-radius:0 3px 3px 3px"></div>'),
        demo("disabled tab: die-cut outline, nothing to pick up", '<div class="tabs"><div class="tab sel">MODS</div><div class="tab" style="background:transparent;outline:2px dashed #3c4d45;outline-offset:-2px;color:var(--mat-print);box-shadow:none">ONLINE</div></div><div class="sheet" style="height:36px;width:380px;border-radius:0 3px 3px 3px"></div>')))
    return sheet("k2", "Workbench: controls and states", "button · list row · toggle · choice · slider · grid cell · tab strip, in every state",
                 '<table class="mx"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (hdr, body) + '<div class="h2">Tab strip <small>index cards</small></div>' + tabsrow)


def k3():
    pucks = "".join(demo(f, puck(f, "", style="margin:6px 14px 10px")) for f in ("red", "green", "blue", "yellow", "purple", "white"))
    rar = "".join(demo(t, puck(f, "", rar=t, style="margin:6px 14px 10px")) for f, t in (("red", "magic"), ("blue", "rare"), ("yellow", "unique")))
    tagd = ('<div class="grid" style="gap:40px">%s%s%s</div>' % (
        demo("tag: one rule, a perforation, the price line", tag("PYROMANCER", "All your attacks become fire.", meta=chip("keystone") + chip("red", "line"), price="Drawback: ice hits against you deal 60% more damage.", w=230)),
        demo("tag for a drive: name, one rule", tag("FROSTED", "Smash attacks become ice", meta=chip("standing rule"), w=210)),
        demo("tag on paper (forms, long help)", tag("HOW IT WORKS", "Drives you win land on the bench.", w=210, cls="paper"))))
    keys = ('<div class="grid" style="gap:44px;align-items:flex-start">%s%s%s%s</div>' % (
        demo("keystone: hangs from the rail", '<div class="rail" style="width:80px;margin-bottom:0"></div><div style="margin-left:12px">%s</div>' % keystone("P", "red")),
        demo("keystone lifted (focus)", '<div style="margin:12px 0 0 12px">%s</div>' % keystone("F", "blue", focus=True)),
        demo("empty hook: a keystone can hang here", hook_empty()),
        demo("six keystone colours (letter + colour band)", '<div style="display:flex;gap:10px">%s</div>' % "".join('<div class="ks-s kc-%s" style="width:36px;height:42px"><div class="face" style="font-size:18px;padding-top:4px">%s</div><div class="band" style="height:7px"></div></div>' % (c, l) for c, l in (("red", "P"), ("blue", "F"), ("green", "H"), ("yellow", "S"), ("purple", "C"), ("white", "E"))))))
    notif = ('<div class="grid" style="gap:40px">%s%s%s%s</div>' % (
        demo("notification: a slip set down at the corner, taped", slip("Picked up: Icebound", "Drive", w=200)),
        demo("warning slip", slip("Conflict: both give the same drive models.", "Warning", cls="warn", w=200)),
        demo("dialog: paper with a steel clip, the mat is covered", '<div style="position:relative;width:340px;height:160px;overflow:hidden"><div class="cover" style="position:absolute"></div><div class="dlg" style="position:absolute;left:18px;top:26px;width:304px;padding:12px 14px"><span class="clip"></span><h3 style="font-size:20px">Quit the run?</h3><p style="font-size:14px;margin-bottom:10px">Drives you carry are lost.</p><div class="btns"><div class="board btn" style="height:32px;font-size:14px;padding:0 12px">Keep playing</div><div class="board btn danger" style="height:32px;font-size:14px;padding:0 12px">Quit</div></div></div></div>'),
        demo("tooltip: a small label with a pointer", '<span class="tip">Left / right to turn it</span>', style="padding-top:8px")))
    disc_ = ('<div class="grid" style="gap:44px;align-items:flex-start">%s%s%s%s</div>' % (
        demo("disc art: character icon 64x56 (placeholder)", disc("icon", "disc art")),
        demo("disc art: portrait 136x188 (placeholder)", disc("portrait", "disc art")),
        demo("fighter cell with the GENO stamp", '<div style="padding:10px 10px 4px">%s</div>' % rcell_geno()),
        demo("stamp and chips", '<div style="display:flex;flex-direction:column;gap:8px;align-items:flex-start;background:var(--board);padding:10px;color:var(--ink)">%s%s%s</div>' % (stamp("completes ice"), chip("trigger rule"), chip("script", "line")))))
    return sheet("k3", "Workbench: pieces", "drive pucks (from the real models) · tag · keystone · slip · dialog · tooltip · disc-art frames",
                 '<div class="h2">Drive pucks <small>the six real drive models, drawn from their mesh and atlas, seated on a plastic puck</small></div><div class="grid">%s</div>' % pucks
                 + '<div class="h2">Rarity <small>the real overlay rings: magic cyan, rare violet, unique gold</small></div><div class="grid">%s</div>' % rar
                 + '<div class="h2">Tags</div>' + tagd + '<div class="h2">Keystones</div>' + keys + '<div class="h2">Slips, dialog, tooltip</div>' + notif + '<div class="h2">Frames and marks</div>' + disc_)


def rcell_geno():
    return '<div class="disc sm"><span class="stamp">GENO</span><div class="art"></div></div>'


def k4():
    pads = [("A", "Pick up"), ("B", "Put back"), ("X", "Turn over"), ("Y", "Sort"), ("Z", "Lay side by side"), ("L", "Previous page"), ("R", "Next page"), ("START", "Pause"), ("STICK", "Slide along"), ("DPAD", "Step along"), ("CSTICK", "Not the camera: attacks")]
    pr = "".join('<div class="demo"><div class="stage" style="background:var(--tape);padding:8px 14px;display:flex;gap:8px;align-items:center;min-width:176px">%s<span style="font-size:14px;font-weight:700">%s</span></div></div>' % (pad(k), esc(v)) for k, v in pads)
    kb = [(kc("Enter"), "Pick up"), (kc("Esc"), "Put back"), (kc("Tab"), "Turn over"), (kc("Q") + kc("E"), "Flip page"), (kc("&#8592;") + kc("&#8593;") + kc("&#8594;") + kc("&#8595;"), "Slide along"), (mouse("L"), "Click: pick up"), (mouse("R"), "Right click: put back"), (mouse("W"), "Wheel: scroll")]
    kr = "".join('<div class="demo"><div class="stage" style="background:var(--tape);padding:8px 14px;display:flex;gap:8px;align-items:center;min-width:176px">%s<span style="font-size:14px;font-weight:700">%s</span></div></div>' % (a, esc(v)) for a, v in kb)
    ports = "".join('<div class="demo"><div class="stage" style="display:flex;flex-direction:column;gap:10px;align-items:flex-start">%s%s<div class="bay %s" style="width:150px;height:44px;border-top-width:4px"><div style="padding:10px 10px;font-size:14px;color:var(--bone)">Fox</div></div>%s</div><div class="cap">%s: colour + shape + number</div></div>'
                    % (peg(p), flag(p, PORT_NAME[p]), p, '<div style="position:relative;height:30px;width:60px">%s</div>' % cursor(p, 0, 0), PORT_NAME[p]) for p in ("p1", "p2", "p3", "p4", "cpu"))
    prog_ = ('<div class="grid" style="gap:40px">%s%s%s%s</div>' % (
        demo("progress: slots fill with blocks, the next one rises", prog(12, 7, cur=7)),
        demo("loading (GET READY): the same, plus the line", '<div style="display:flex;flex-direction:column;gap:6px;color:var(--bone)"><span class="print">Warming up the stage</span>%s</div>' % prog(12, 3, cur=3)),
        demo("scroll: carriage in a groove, paper edges peek", '<div style="display:flex;gap:8px;align-items:stretch;height:120px"><div style="width:140px;display:flex;flex-direction:column;gap:3px;justify-content:center"><div class="more"></div><div class="board row" style="height:30px;width:140px;font-size:14px">Row</div><div class="board row" style="height:30px;width:140px;font-size:14px">Row</div><div class="more"></div></div>%s</div>' % scroll(120, 24, 50)),
        demo("empty state: die-cut outlines and a plain slip", '<div class="empty-note tray"><div class="sock empty" style="width:48px;height:48px"></div><div class="sock empty" style="width:48px;height:48px"></div>%s</div>' % slip("Nothing here yet.", "Empty", w=130, cls="flat"))))
    rail = ('<div style="position:relative;width:640px;height:34px;margin-top:6px;zoom:1.4">%s</div>' % hints(ph("pick", "put", "turn", "move"), pad_left=14))
    return sheet("k4", "Workbench: input, players, progress", "pad glyphs with physical verbs · keyboard and mouse · four ports + CPU · progress, scroll, empty",
                 '<div class="h2">GameCube pad <small>verbs are physical: pick up, put back, turn over</small></div><div class="grid" style="gap:14px 18px">%s</div>' % pr
                 + '<div class="h2">Keyboard and mouse <small>additions, never the only way</small></div><div class="grid" style="gap:14px 18px">%s</div>' % kr
                 + '<div class="h2">Hint rail <small>label tape along the bottom edge: every screen shows its focus and its hints</small></div>' + rail
                 + '<div class="h2">Players <small>peg, tape flag, bay and cursor: a colour, a shape and a number, never colour alone</small></div><div class="grid" style="gap:30px">%s</div>' % ports
                 + '<div class="h2">Progress, scroll, empty</div>' + prog_)


def k5():
    def frame(label, html, ms):
        return '<div class="demo f"><div class="stage" style="width:190px;height:120px;position:relative;background:var(--mat);outline:2px solid var(--mat-grid);overflow:visible"><div style="position:absolute;left:24px;top:36px">%s</div></div><div class="cap">%s<br><b style="color:var(--bone)">%s</b></div></div>' % (html, label, ms)
    strip = ('<div class="grid" style="gap:12px;align-items:flex-start">%s%s%s%s%s</div>' % (
        frame("1 rest", '<div class="board row" style="width:120px;height:30px;font-size:12px">Versus</div>', "0 ms"),
        frame("2 lift: up 5, left 2, shadow grows, clamps appear", '<div class="board row focus" style="width:120px;height:30px;font-size:12px">Versus</div>', "90 ms ease-out"),
        frame("3 press: sink, shadow shrinks", '<div class="board row pressed" style="width:120px;height:30px;font-size:12px">Versus</div>', "50 ms"),
        frame("4 set down on release: settles 1 px past, then rests", '<div class="board row" style="width:120px;height:30px;font-size:12px;transform:translate(0,1px)">Versus</div>', "70 ms"),
        frame("5 put back: the lift reverses", '<div class="board row" style="width:120px;height:30px;font-size:12px">Versus</div>', "90 ms")))
    other = ('<div class="grid" style="gap:12px">%s%s%s%s</div>' % (
        frame("notification slides in from the edge, then rests (tilted 2 degrees)", slip("Picked up: Icebound", w=140, style="font-size:12px"), "160 ms ease-out, holds 3 s"),
        frame("tab swap: the live card rises, the old one drops", '<div class="tabs"><div class="tab sel" style="height:28px;font-size:12px;padding:0 8px">VIDEO</div><div class="tab" style="height:20px;font-size:12px;padding:0 8px">AUDIO</div></div>', "100 ms"),
        frame("dialog: paper drops 12 px, the cover fades in", '<div class="dlg" style="width:130px;padding:6px 8px;font-size:12px"><h3 style="font-size:14px;margin:0">Quit?</h3></div>', "120 ms; shadow shrinks as it lands"),
        frame("toggle: the block slides, 3 px of tilt, no bounce", tog(True), "160 ms")))
    need = ('<div class="grid" style="gap:30px"><div style="max-width:760px;color:var(--bone);font-size:16px;line-height:1.4;font-weight:600">'
            '<b>Needs nothing beyond flat quads, atlas text and model cells.</b> Every piece is 1 to 3 flat quads: a face, an edge strip, and a shadow quad offset by a fixed amount. '
            'The grid on the mat is one tiled texture. Tags and keystones use clipped corners that are baked into a 9-slice. '
            'Optional (the fallback is listed on the README): quad rotation for the 2 degree slip tilt, and a 1 px alpha edge for the hatched disc-art placeholder.</div></div>')
    return sheet("k5", "Workbench: motion and engine notes", "what moves, how fast · everything is a flat quad",
                 '<div class="h2">A piece, lifted and set down <small>the whole motion language is one gesture</small></div>' + strip + '<div class="h2">Other things that move</div>' + other + '<div class="h2">Engine</div>' + need)


SHEETS = [("kit-1-foundations.png", "k1", k1), ("kit-2-controls.png", "k2", k2), ("kit-3-pieces.png", "k3", k3), ("kit-4-input-players.png", "k4", k4), ("kit-5-motion.png", "k5", k5)]


def build(here):
    body = "".join(f() for _, _, f in SHEETS)
    body = body.replace("{A}", "assets/")
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Workbench kit</title><link rel="stylesheet" href="tokens.css"><link rel="stylesheet" href="kit.css"><style>%s</style></head><body>%s</body></html>'
            % (CSS, body))
    open(os.path.join(here, "kit.html"), "w", encoding="utf-8").write(page)
    return [(png, "#" + id_) for png, id_, _ in SHEETS]


def index(here, pages, kits):
    items = []
    for png in kits:
        items.append((png, "Kit showcase: " + png.replace("kit-", "").replace(".png", "").replace("-", " "), "kit"))
    for name, title, w, h, z in pages:
        items.append((name + ".png", title + (" (%dx%d)" % (round(w * z), round(h * z))), "screen"))
    figs = "".join('<figure data-i="%d"><a href="out/%s"><img src="out/%s" loading="lazy" alt="%s"></a><figcaption>%s</figcaption></figure>' % (i, p, p, esc(t), esc(t)) for i, (p, t, _) in enumerate(items))
    data = "[" + ",".join('["out/%s","%s"]' % (p, t.replace('"', "'")) for p, t, _ in items) + "]"
    html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Workbench menus</title>
<style>
:root{--mat:#1d2622;--bone:#ece7d6;--print:#8fa196;--board:#e8dfca;--ink:#191714}
body{margin:0;background:var(--mat);color:var(--bone);font:700 16px/1.3 "Source Sans 3",system-ui,sans-serif}
header{padding:28px 32px 8px}h1{margin:0 0 6px;font-size:32px;letter-spacing:.1em;text-transform:uppercase}
p{margin:4px 0;color:var(--print);max-width:880px;font-weight:600}
nav a{display:inline-block;margin:10px 12px 0 0;padding:8px 14px;background:var(--board);color:var(--ink);text-decoration:none;font-weight:900;letter-spacing:.06em;text-transform:uppercase;border-radius:3px;box-shadow:0 3px 0 #b0a281}
main{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:26px;padding:24px 32px 60px}
figure{margin:0}figure img{width:100%;display:block;background:#0b0f0d;box-shadow:6px 8px 0 #080b09;cursor:zoom-in}figcaption{margin-top:12px;color:var(--bone)}
#lb{position:fixed;inset:0;background:rgba(5,8,7,.94);display:none;flex-direction:column;align-items:center;justify-content:center;z-index:9}
#lb.on{display:flex}#lb img{max-width:96vw;max-height:88vh;box-shadow:8px 10px 0 #000}#lb div{margin-top:12px}#lb small{color:var(--print);margin-left:12px}
</style></head><body><header><h1>Workbench</h1>
<p>Menus as physical objects on a work surface. A choice is a board you pick up; the lifted piece carries a tag; drives sit on pucks in sockets; keystones hang as steel weights. Click an image to zoom; left and right arrow keys move between screens; Esc closes.</p>
<nav><a href="kit.html">Kit showcase (live HTML)</a><a href="README.md">README</a></nav></header>
<main>""" + figs + """</main>
<div id="lb"><img id="lbi" alt=""><div id="lbt"></div></div>
<script>
var D=""" + data + """,cur=0,lb=document.getElementById('lb'),im=document.getElementById('lbi'),tt=document.getElementById('lbt');
function show(i){cur=(i+D.length)%D.length;im.src=D[cur][0];tt.innerHTML=D[cur][1]+'<small>'+(cur+1)+' / '+D.length+'</small>';lb.className='on'}
document.querySelectorAll('figure').forEach(function(f){f.querySelector('a').addEventListener('click',function(e){e.preventDefault();show(+f.dataset.i)})});
lb.addEventListener('click',function(){lb.className=''});
document.addEventListener('keydown',function(e){if(!lb.className)return;if(e.key==='ArrowRight')show(cur+1);else if(e.key==='ArrowLeft')show(cur-1);else if(e.key==='Escape')lb.className=''});
</script></body></html>"""
    open(os.path.join(here, "index.html"), "w", encoding="utf-8").write(html)
