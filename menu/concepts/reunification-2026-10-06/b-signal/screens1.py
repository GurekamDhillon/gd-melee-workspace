"""Screens 01-08: title, main, solo, character select, stage select, rules, online room, Envoy run setup."""
from ui import *

PAD_NAV = [hint("stick", "Move"), hint("a", "Select"), hint("b", "Back")]

RETAIL = [("Dr. Mario", "DRM"), ("Mario", "MAR"), ("Luigi", "LUI"), ("Bowser", "BOW"), ("Peach", "PEA"), ("Yoshi", "YOS"),
          ("Donkey Kong", "DK"), ("Captain Falcon", "CF"), ("Ganondorf", "GAN"), ("Falco", "FAL"), ("Fox", "FOX"), ("Ness", "NES"),
          ("Ice Climbers", "IC"), ("Kirby", "KIR"), ("Samus", "SAM"), ("Zelda", "ZEL"), ("Link", "LNK"), ("Young Link", "YL"),
          ("Pichu", "PCH"), ("Pikachu", "PIK"), ("Jigglypuff", "JIG"), ("Mewtwo", "M2"), ("Mr. Game & Watch", "GW"),
          ("Marth", "MRT"), ("Roy", "ROY")]
ADDED = [("Meta Knight", "MK", "halberd"), ("Ultimate Kirby", "UK", "kirby-ultimate"), ("Sora", "SOR", "ultimate-trail")]


# ---------------------------------------------------------------- 01 title
def s01(wide=False):
    ports = ""
    for i, (p, st, on) in enumerate((("p1", "PAD", True), ("p2", "PAD", True), ("p3", "NO PAD", False), ("p4", "NO PAD", False))):
        ports += ('<div class="fx ac" style="gap:10px;margin-bottom:8px;opacity:%s">%s<span class="c %s">%s</span></div>'
                  % (1 if on else .45, tally(i + 1, p), "mid" if on else "", st))
    b = ""
    b += '<div class="c abs" style="left:32px;top:24px">PC PORT <span style="color:var(--off)">/</span> <span class="mid">[VERSION]</span></div>'
    b += '<div class="d s-hero abs dim" style="left:30px;top:70px">GD\'S</div>'
    b += '<div class="d s-mega abs bone" style="left:24px;top:150px;letter-spacing:-.01em">MELEE</div>'
    b += '<div class="abs" style="left:32px;right:32px;top:312px;height:1px;background:var(--line)"></div>'
    b += '<div class="abs" style="left:32px;top:311px;width:132px;height:3px;background:var(--volt)"></div>'
    b += '<div class="abs" style="left:32px;top:346px">%s</div>' % btn("PRESS START", "f")
    b += '<div class="abs" style="left:236px;top:356px">%s</div>' % glyph("start")
    b += '<div class="abs" style="right:32px;top:332px">%s</div>' % ports
    b += foot(hint("start", "Start"), hint("y", "Rematch last"), hint("z", "Mods"))
    return page("01 title", b, wide)


# ---------------------------------------------------------------- 02 main menu
def s02(wide=False):
    rows = [li("Solo"), li("Versus", f=True), li("Online"), li("Envoy", badge="MOD"), li("Mods"), li("Settings"),
            li("Collection", cls="") ]
    # collection and data are folded into one quiet tail row
    rows[-1] = '<div class="li" style="font-size:20px;margin-top:6px;font-weight:700;letter-spacing:.03em">Collection <span style="color:var(--off);padding:0 10px">/</span> Data</div>'
    b = crumb("Main")
    b += count("02", "07")
    b += lens("hub", 32, 62, 360, *rows)
    px = 400 if not wide else 470
    peek = '<div class="c" style="margin-bottom:8px">Versus</div>'
    peek += '<div class="b" style="width:190px;margin-bottom:16px">Up to four players. Your rules, your stage.</div>'
    for i, t in enumerate(("Melee", "Tournament", "Special Melee", "Rules", "Name Entry")):
        peek += '<div class="d s-row %s" style="margin-bottom:7px">%s%s</div>' % ("bone" if i == 0 else "dim", t, '<span class="c" style="margin-left:10px;color:var(--volt)">A</span>' if i == 0 else "")
    b += '<div class="abs" style="left:%dpx;top:106px">%s</div>' % (px, peek)
    # the one-press way into a match
    b += ('<div class="abs" style="left:%dpx;top:352px"><div class="fx ac" style="gap:8px">%s<span class="d s-row bone">Rematch</span></div>'
          '<div class="c" style="margin-top:6px">Fox vs CPU 3 / Battlefield</div><div class="c" style="margin-top:2px;color:var(--off)">4 stocks / 8:00</div></div>' % (px, glyph("y")))
    if wide:
        last = '<div class="c" style="margin-bottom:10px">Last session</div>'
        for t, s in (("Versus", "Fox vs CPU 3"), ("Envoy", "Run [N], stage [N]"), ("Lab", "Fox, Final Destination")):
            last += '<div class="d s-row mid" style="margin-bottom:2px">%s</div><div class="c" style="margin-bottom:12px">%s</div>' % (t, s)
        b += '<div class="abs" style="left:690px;top:106px;width:140px">%s</div>' % last
    b += foot(hint("stick", "Move"), hint("a", "Select"), hint("b", "Title"), hint("y", "Rematch"), hint("l", "Mods", off=False))
    return page("02 main menu", b, wide)


# ---------------------------------------------------------------- 03 solo
def s03(wide=False):
    rows = [li("Classic"), li("Adventure"), li("All-Star"), li("Event Match"), li("Stadium"), li("Training"),
            li("The Lab", f=True, badge="MOD"), li("Envoy", badge="MOD")]
    b = crumb("Main", "Solo")
    b += count("07", "08")
    b += lens("list", 32, 64, 380, *rows)
    side = '<div class="c" style="margin-bottom:8px">The Lab <span style="color:var(--off)">/</span> geno-lab</div>'
    side += '<div class="b" style="width:200px;margin-bottom:16px">Any fighters, no timer, frame-step, hitboxes, timelines.</div>'
    for t in ("Clean", "Hitboxes", "Frames", "Stage", "Inspect", "Moves", "Launch", "Training", "Combo"):
        side += '<span class="d s-row dim" style="display:inline-block;margin:0 12px 6px 0">%s</span>' % t
    b += '<div class="abs" style="left:412px;top:116px;width:200px">%s</div>' % side
    b += '<div class="abs c" style="left:412px;top:310px;width:196px;color:var(--off)">Offline only. Two entries come from mods; they are marked.</div>'
    b += foot(*PAD_NAV, hint("l", "Switch menu"))
    return page("03 solo", b, wide)


# ---------------------------------------------------------------- 04 character select
def s04(wide=False):
    cols = 12 if wide else 8
    W = 853.3333 if wide else 640
    cells = [(n, c, None) for n, c in RETAIL] + [("Random", "?", None)] + [(n, c, m) for n, c, m in ADDED]
    cw, ch, px, py = 44, 36, 50, 42
    gx, gy = 32, 160
    tokens = {"Marth": (2, False), "Pikachu": (3, True)}
    out = ""
    for i, (n, c, m) in enumerate(cells):
        x, y = gx + (i % cols) * px, gy + (i // cols) * py
        tok = tokens.get(n)
        focus = n == "Meta Knight"
        style = "position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;" % (x, y, cw, ch)
        inner = disc(cw, ch, mono=c, cls="on" if (focus or tok) else "")
        if m:  # geno/added: a notch in the corner marks it, plus the GENO word in focus
            inner += '<div style="position:absolute;right:0;top:0;width:0;height:0;border-style:solid;border-width:0 11px 11px 0;border-color:transparent var(--bone) transparent transparent"></div>'
        if tok:
            inner += '<div style="position:absolute;left:3px;top:3px">%s</div>' % tally(tok[0], "p%d" % tok[0], cpu=tok[1], mini=True)
            inner += '<div style="position:absolute;left:0;right:0;bottom:0;height:3px;background:var(--p%d)"></div>' % tok[0]
        if focus:
            inner += '<div style="position:absolute;left:3px;top:3px">%s</div>' % tally(1, "p1", mini=True)
            out += '<div class="brk f" style="%s transform:scale(1.22);z-index:5">%s</div>' % (style, inner)
        else:
            out += '<div style="%s">%s</div>' % (style, inner)
    b = crumb("Versus", "Melee", "Characters")
    b += count("27", "29")
    b += '<div class="abs" style="left:32px;top:50px">%s</div>' % tabs(["All", "Retail", "Added", "Geno"], "All", f=False, left="l", right="r")
    b += '<div class="d s-focus abs bone" style="left:32px;top:74px">Meta Knight</div>'
    b += '<div class="abs fx ac" style="left:32px;top:128px;gap:10px"><span class="badge" style="margin:0;color:var(--bone);border-color:var(--bone)">GENO</span><span class="c">Added fighter / from mod halberd</span></div>'
    b += out
    rows = 4 if wide is False else 3
    # portrait + costume
    rx = int(W) - 32 - 136
    b += '<div class="abs" style="left:%dpx;top:84px">%s</div>' % (rx, disc(136, 188, "disc art"))
    b += '<div class="abs" style="left:%dpx;top:284px"><div class="c" style="margin-bottom:6px">Costume 3 / 5</div><div class="fx" style="gap:6px">%s</div></div>' % (
        rx, "".join('<span style="width:20px;height:10px;background:%s"></span>' % ("var(--volt)" if i == 2 else "var(--line)") for i in range(5)))
    # four ports along the bottom: the active one is bright, the others recede
    slots = [("p1", 1, "Picking", "Meta Knight", "Human, costume 3", True, False),
             ("p2", 2, "Ready", "Marth", "Human, costume 2", False, False),
             ("p3", 3, "Ready", "Pikachu", "CPU 5, costume 1", False, True),
             ("p4", 4, "Open", "-", "Press A to join", False, False)]
    sw = (int(W) - 64) / 4
    for i, (p, n, st, nm, cap, act, cpu) in enumerate(slots):
        x = 32 + i * sw
        opacity = 1 if (act or st == "Ready") else 1
        b += ('<div class="abs %s" style="left:%dpx;top:338px;width:%dpx">'
              '<div style="height:3px;width:%dpx;background:%s;margin-bottom:8px"></div>'
              '<div class="fx ac" style="gap:8px">%s<span class="pn">P%d</span><span class="c" style="margin-left:auto;color:%s">%s</span></div>'
              '<div class="d s-row %s" style="margin-top:6px">%s</div><div class="c nw" style="margin-top:3px">%s</div></div>'
              % (p, x, sw - 16, sw - 16, "var(--volt)" if act else "var(--line)", tally(n, p, cpu=cpu), n,
                 "var(--volt)" if act else "var(--dim)", st, "bone" if (act or st == "Ready") else "off", esc(nm), esc(cap)))
    b += foot(hint("a", "Pick"), hint("b", "Back"), hint("x", "Costume"), hint("y", "CPU"), hint("l", "Page"), hint("start", "Fight", off=True))
    return page("04 character select", b, wide)


# ---------------------------------------------------------------- 05 stage select
def s05(wide=False):
    names = [("Yoshi's Story", True), ("Fountain of Dreams", True), ("Dream Land", True), ("Final Destination", True),
             ("Battlefield", True), ("Pokemon Stadium", True), ("Fourside", False), ("Corneria", False), ("Kongo Jungle", False)]
    rows = []
    for n, rot in names:
        rows.append(li(n, f=(n == "Final Destination"), sel=rot))
    b = crumb("Versus", "Melee", "Stages")
    b += count("04", "29")
    b += '<div class="abs" style="left:32px;top:50px">%s</div>' % tabs(["Legal", "All", "Added"], "Legal", f=False, counts={"Legal": "6"}, left="l", right="r")
    b += lens("list", 32, 96, 360, *rows)
    b += '<div class="scrl" style="right:12px;top:96px;height:300px"><i style="top:30px;height:56px"></i></div>'
    b += '<div class="abs" style="left:404px;top:262px">%s</div>' % disc(204, 126, "disc art")
    b += ('<div class="abs" style="left:404px;top:96px;width:204px"><div class="c" style="margin-bottom:8px">Stage list: 6 in rotation</div>'
          '<div class="fx ac jb"><span class="d s-row mid">In rotation</span>%s</div>'
          '<div class="c" style="margin-top:10px;color:var(--off)">Random picks only these.</div></div>' % opts(["No", "Yes"], "Yes", f=True))
    b += foot(hint("a", "Pick"), hint("b", "Back"), hint("x", "In rotation"), hint("y", "Random"), hint("l", "Page"))
    return page("05 stage select", b, wide)


# ---------------------------------------------------------------- 06 rules
def s06(wide=False):
    rows = [
        li("Mode", v=opts(["Stock", "Time", "Coins"], "Stock")),
        li("Stocks", v=step("4")),
        li("Time limit", v=step("8:00")),
        li("Teams", v=opts(["Off", "On"], "Off")),
        li("Items", v=opts(["Off", "Low", "Medium", "High"], "Off")),
        li("Damage ratio", v=slider(50, "1.0x")),
        li("Stage choice", v=opts(["Pick", "Random", "List"], "Pick")),
        li("Turbo", f=True, v=opts(["Off", "On"], "On", f=True)),
        '<div class="help" style="padding-left:20px;margin:-8px 0 0">Match rule. In a room, the host sets it for everyone.</div>',
    ]
    b = crumb("Versus", "Melee", "Rules")
    b += count("08", "08")
    b += lens("list", 32, 62, 576, *rows)
    b += foot(hint("stick", "Move"), hint("dpad_lr", "Change"), hint("a", "Characters"), hint("b", "Back"), hint("z", "Defaults"))
    return page("06 versus rules", b, wide)


# ---------------------------------------------------------------- 07 online room
def s07(wide=False):
    bars = "".join('<span style="display:inline-block;width:4px;margin-right:2px;vertical-align:bottom;height:%dpx;background:%s"></span>' % (6 + i * 3, "var(--bone)" if i < 4 else "var(--off)") for i in range(5))
    b = crumb("Online", "Room")
    b += '<div class="count c" style="display:flex;gap:10px;align-items:flex-end;justify-content:flex-end"><span>%s</span><span class="bone">42 ms</span><span>Stable</span></div>' % bars
    b += '<div class="c abs" style="left:32px;top:58px">Room code</div>'
    b += '<div class="d s-hero abs bone" style="left:30px;top:76px;letter-spacing:.02em">K7Q3</div>'
    b += '<div class="abs fx ac" style="left:262px;top:112px;gap:10px">%s<span class="c">Copy code</span></div>' % glyph("x")
    # players
    def prow(top, p, n, name, role, ready, mine):
        r = '<div class="abs fx ac" style="left:32px;top:%dpx;width:576px;gap:14px">' % top
        r += tally(n, p, big=True)
        r += '<span class="d s-head %s">%s</span>' % ("bone" if ready else "mid", esc(name))
        r += '<span class="badge">%s</span>' % role
        if mine:
            r += '<span class="c volt">You</span>'
        r += '<span class="fx ac" style="margin-left:auto;gap:8px">%s<span class="d s-row %s">%s</span></span></div>' % (
            '<span class="sel"></span>' if ready else '<span class="sel hollow"></span>', "bone" if ready else "dim", "Ready" if ready else "Not ready")
        return r
    b += prow(176, "p1", 1, "GD", "HOST", True, True)
    b += prow(214, "p2", 2, "kestrel", "GUEST", False, False)
    b += '<div class="abs" style="left:32px;top:252px;right:32px;height:1px;background:var(--line)"></div>'
    rows = [li("Turbo", f=True, v=opts(["Off", "On"], "On", f=True)),
            li("Envoy set", v=opts(["Off", "On"], "Off")),
            li("Stocks", v=step("4")),
            li("Time limit", v=step("8:00"))]
    b += lens("dense", 32, 268, 380, *rows)
    b += '<div class="abs c nw" style="left:52px;top:396px">Host sets rule changes. The guest sees them at once.</div>'
    b += '<div class="abs" style="right:32px;top:312px">%s</div>' % btn("Ready")
    b += '<div class="abs c r" style="right:32px;top:366px;width:150px;color:var(--off)">Both ready: 3 second countdown</div>'
    b += foot(hint("stick", "Move"), hint("a", "Change"), hint("start", "Ready"), hint("b", "Leave room"))
    return page("07 online room", b, wide)


# ---------------------------------------------------------------- 08 Envoy run setup
def s08(wide=False):
    rows = [li("Mode", v=opts(["Classic", "Adventure"], "Classic")),
            li("Fighter", v=step("Fox")),
            li("Players", v=opts(["Solo", "Co-op"], "Solo")),
            li("Start run", f=True)]
    b = crumb("Envoy", "New run")
    b += count("04", "04")
    b += lens("list", 32, 72, 400, *rows)
    b += '<div class="abs" style="left:472px;top:72px">%s</div>' % disc(136, 188, "disc art")
    b += '<div class="abs fx ac" style="left:472px;top:268px;gap:8px">%s<span class="d s-row mid">Fox</span></div>' % tally(1, "p1")
    # the build starts empty: four open slots, two locked, a bag of four
    cells = '<div class="abs" style="left:32px;top:314px"><div class="c" style="margin-bottom:12px">Your build <span style="color:var(--off)">/ 4 of 6 slots open</span></div><div class="fx" style="gap:10px">'
    cells += "".join(drive_slot("md", "empty") for _ in range(4)) + "".join(drive_slot("md", "lock") for _ in range(2))
    cells += '<div style="width:22px"></div>' + "".join(drive_slot("md", "empty") for _ in range(4)) + "</div>"
    cells += '<div class="c" style="margin-top:12px;color:var(--off)">Equipped, then bag. Drives drop in stages.</div></div>'
    b += cells
    b += foot(hint("stick", "Move"), hint("dpad_lr", "Change"), hint("a", "Start"), hint("b", "Back"))
    return page("08 envoy run setup", b, wide)


SCREENS1 = [("01-title", s01, False), ("02-main-menu", s02, True), ("03-solo", s03, False), ("04-character-select", s04, True),
            ("05-stage-select", s05, False), ("06-versus-rules", s06, False), ("07-online-room", s07, False), ("08-envoy-run-setup", s08, False)]
