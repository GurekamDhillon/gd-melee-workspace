"""The seventeen screens. Each function returns the inner HTML of a `.screen`; `build.py` wraps and renders.
Coordinates are in the engine's 640x480 logical canvas; `w` > 640 adds mat on both sides (the 4:3 core stays centred)."""
from parts import *

REG = '<i class="reg tl"></i><i class="reg tr"></i><i class="reg bl"></i><i class="reg br"></i>'

# retail roster names: plain strings only
ROSTER = ["Dr. Mario", "Mario", "Luigi", "Bowser", "Peach", "Yoshi", "Donkey Kong", "Captain Falcon", "Ganondorf",
          "Falco", "Fox", "Ness", "Ice Climbers", "Kirby", "Samus", "Zelda", "Link", "Young Link", "Pichu", "Pikachu",
          "Jigglypuff", "Mewtwo", "Mr. Game & Watch", "Marth", "Roy", "Sheik", "Random"]
STAGES = ["Peach's Castle", "Rainbow Cruise", "Kongo Jungle", "Jungle Japes", "Great Bay", "Temple", "Brinstar",
          "Brinstar Depths", "Yoshi's Story", "Yoshi's Island", "Fountain of Dreams", "Green Greens", "Corneria",
          "Venom", "Pokemon Stadium", "Poke Floats"]


def core(w, inner, h=480):
    off = (w - 640) / 2
    return '<div style="position:absolute;left:%spx;top:0;width:640px;height:%spx">%s</div>' % (off, h, inner)


def head(title, trail=(), x=32, y=16):
    t = tape(title)
    c = crumbs(list(trail) + [title]) if trail else ""
    # breadcrumb sits above-left as small tapes; title tape under it
    return at(x, y, tape(title) + (('<span style="margin-left:14px">%s</span>' % crumbs(trail)) if trail else ""),
              cls="", extra="display:flex;align-items:center;")


def screen(w, inner, rail, h=480, bg=True, side=""):
    return REG + side + core(w, inner, h) + rail


def rail_for(w, items, right=None):
    return hints(items, pad_left=(w - 640) / 2 + 32, right=right)


# ================================================================== 01 title
def s01(w=640):
    tiles = ""
    for i, (ch, dy) in enumerate(zip("GD'S", (0, 4, -3, 2))):
        tiles += '<div class="board tile" %s>%s</div>' % (pos(216 + i * 54, 46 + dy, 46, 54, "font-size:34px"), esc(ch))
    for i, (ch, dy) in enumerate(zip("MELEE", (0, -5, 3, -2, 4))):
        tiles += '<div class="board tile" %s>%s</div>' % (pos(134 + i * 76, 112 + dy, 68, 80, "font-size:56px"), ch)
    fams = ["red", "green", "blue", "yellow", "purple", "white"]
    socks = "".join(sock(puck(f, "seat"), style="width:64px;height:64px") for f in fams)
    tray = at(98, 236, '<div style="display:flex;gap:8px;padding:10px">%s</div>' % socks, cls="tray")
    start = at(170, 352, '<div class="board btn hero focus">%s<span>Press START</span></div>' % pad("START"), extra="width:300px")
    note = at(32, 420, '<span class="print">An original menu concept: no game art</span>')
    return screen(w, tiles + tray + start + note, rail_for(w, [(pad("START"), "Begin")], right="[VERSION]"))


# ================================================================== 02 main menu
MAIN = [("SUPERTIME ENVOY", "drive"), ("SOLO", "solo"), ("VERSUS", "versus"), ("COLLECTION", "collection"), ("SETTINGS", "settings"), ("DATA", "data")]


def s02(w=640, small=False):
    rows = ""
    for i, (lab, ic) in enumerate(MAIN):
        icn = mini_drive("red", 36) if ic == "drive" else icon(ic)
        c = "focus" if i == 2 else ""
        rows += '<div %s>%s</div>' % (pos(32, 70 + i * 60, 280, 52), row(lab, cls="big " + c, icon=icn, style="height:52px;width:280px"))
    pegs = "".join(sock(peg(p).replace('class="peg', 'class="peg xl'), style="width:84px;height:84px;display:flex;align-items:center;justify-content:center") for p in ("p1", "p2", "p3", "p4"))
    tray = at(340, 70, '<div style="display:grid;grid-template-columns:84px 84px;gap:14px;justify-content:center;padding:16px">%s</div>' % pegs, w=268, h=214, cls="tray")
    lbl = at(348, 292, '<span class="print">Four ports, one bench</span>', extra="")
    tg = at(340, 316, tag("VERSUS", "Up to four players. Your rules, your stage.", w=268))
    st = string(358, 331, 310, 216, sag=26)
    inner = head("Main menu") + rows + tray + tg + st
    side = ""
    if w > 640:
        off = (w - 640) / 2
        d = "".join(at(off / 2 - 22, 90 + i * 64, sock(peg(p).replace('class="peg', 'class="peg xl'), style="width:60px;height:60px;display:flex;align-items:center;justify-content:center;opacity:%s" % (1 if i == 0 else .45)), w=60, h=60) for i, p in enumerate(("p1", "p2", "p3", "p4")))
        d += at(off / 2 - 40, 66, '<span class="print">Ports</span>')
        right = at(w - off + 8, 92, slip("connected", "Online", w=92), w=92)
        right += at(w - off + 8, 164, slip("4 on", "Mods", w=92), w=92)
        right += at(w - off + 8, 236, slip("1 pad", "Ports", w=92), w=92)
        side = d + right
    rail = rail_for(w, ph("pick", "put", extra=[(pad("L") + pad("R"), "Flip page")]), right=None)
    return screen(w, inner, rail, side=side)


# ================================================================== 03 solo hub
SOLO = [("CLASSIC", "classic", 0), ("ADVENTURE", "adventure", 0), ("ALL-STAR", "allstar", 0), ("EVENT", "event", 0),
        ("STADIUM", "stadium", 0), ("TRAINING", "training", 0), ("LAB", "lab", 1), ("ENVOY", "drive", 1)]


def s03(w=640):
    bins = ""
    for i, (lab, ic, mod) in enumerate(SOLO):
        r, c = divmod(i, 4)
        x, y = 32 + c * 146, 72 + r * 130
        icn = mini_drive("red", 48) if ic == "drive" else icon(ic)
        ch = chip("MOD") if mod else ""
        bins += '<div class="board bin %s" %s>%s<span>%s</span>%s</div>' % ("focus" if lab == "LAB" else "", pos(x, y), icn, lab, ch)
    tg = at(250, 334, tag("LAB", "The Geno Lab: any fighters, no timer, frame-step, hitboxes, timelines.", meta=chip("added by geno-lab"), w=358))
    st = string(270, 351, 360, 320, sag=8)
    sl = at(32, 352, slip("MOD = a piece a mod you switched on put here.", w=190), w=190)
    return screen(w, head("Solo", ["Main menu"]) + bins + st + tg + sl, rail_for(w, ph("pick", "put", "move")))


# ================================================================== 04 character select
def rcell(name, focus=False, sel=False, geno=False, cursor_port=None):
    ex = stamp("GENO") if geno else ""
    if cursor_port:
        ex += '<span style="position:absolute;left:-8px;top:-12px;z-index:6">%s</span>' % peg(cursor_port).replace('class="peg', 'class="peg sm')
    return '<div class="disc sm %s %s">%s<div class="art"></div></div>' % ("focus" if focus else "", "seat" if sel else "", ex)


def s04_wide(w):
    bw, gap = 188, 12
    specs = [("p1", "P1 · HUMAN", "Fox", 1), ("p2", "P2 · HUMAN", "Marth", 3), ("cpu", "CPU · LEVEL 3", "Kirby", 0), (None, None, None, None)]
    bays = ""
    for i, (p, lab, nm, co) in enumerate(specs):
        x = 32 + i * (bw + gap)
        if p:
            costume = "".join('<i style="display:inline-block;width:10px;height:10px;border-radius:9px;margin-right:4px;background:%s"></i>' % ("#e8dfca" if k == co else "#3c4d45") for k in range(5))
            inner = ('<div style="position:absolute;left:8px;top:8px">%s</div><div style="position:absolute;left:8px;top:40px">%s</div>'
                     '<div style="position:absolute;left:78px;top:46px"><div style="font-size:20px;font-weight:900;letter-spacing:.04em;text-transform:uppercase">%s</div>'
                     '<div class="print" style="margin:4px 0 4px">Costume</div><div>%s</div></div>') % (flag(p, lab), disc("icon", "disc art", cls="sm"), esc(nm), costume)
            bays += at(x, 54, inner, w=bw, h=102, cls="bay %s" % p, extra="color:var(--bone)")
        else:
            inner = '<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px"><div class="board off row" style="width:%spx;height:40px;justify-content:center">Join</div><span class="print">Pick up a pad</span></div>' % (bw - 24)
            bays += at(x, 54, inner, w=bw, h=102, cls="bay", extra="border-top-color:#3c4d45")
    cols = 13
    cells = "".join(rcell(nm, focus=(nm == "Ness"), sel=(nm == "Fox"), cursor_port=("p1" if nm == "Ness" else None)) for nm in ROSTER[:26])
    trw = cols * 62 + 20
    gx = (w - trw) / 2
    rowthree = ('<div style="grid-column:1 / span 13;display:flex;align-items:center;gap:14px;margin-top:2px;padding-top:6px;border-top:2px solid #26332d">%s<span class="print" style="width:120px;line-height:1.25">Added fighters<br>page 2 of 2</span>%s%s%s'
                '<span style="margin-left:auto;display:flex;align-items:center;gap:6px">%s<span style="font-size:14px;color:var(--bone)">= defined in Geno</span></span></div>') % (
        rcell("Random"), rcell("Meta Knight", geno=True), rcell("Kirby (Ultimate)"), rcell("Sora", geno=True), stamp("GENO", "color:var(--bone)"))
    grid = at(gx, 170, '<div style="display:grid;grid-template-columns:repeat(%d,56px);gap:8px 6px;padding:14px 10px 12px">%s%s</div>' % (cols, cells, rowthree), w=trw, cls="tray")
    ci = ROSTER.index("Ness")
    cx, cy = gx + 10 + (ci % cols) * 62, 170 + 14 + (ci // cols) * 56
    nt = at(cx - 22, cy - 40, '<div class="tag" style="width:106px"><span class="hole" style="left:6px;top:6px;width:10px;height:10px"></span><div class="face" style="padding:6px 6px 6px 22px;clip-path:polygon(0 10px,10px 0,100% 0,100% 100%,0 100%)"><h4 style="margin:0;font-size:14px;letter-spacing:.02em">NESS</h4></div></div>')
    key = at(gx, 170 + 14 + 3 * 56 + 22, '<span class="print">Hatched frame = disc art (placeholder)</span>')
    return REG + head("Characters", ["Versus"]) + bays + grid + nt + key + hints(ph("pick", "put", "turn", extra=[(pad("L") + pad("R"), "Next page")]), pad_left=32)


def s04(w=640):
    wide = w > 640
    if wide:
        return s04_wide(w)
    bw = 180 if wide else 138
    gap = 12 if wide else 8
    total = 4 * bw + 3 * gap
    x0 = (640 - total) / 2 if not wide else (640 - total) / 2
    bays = ""
    specs = [("p1", "P1 · HUMAN", "Fox", 1), ("p2", "P2 · HUMAN", "Marth", 3), ("cpu", "CPU · LEVEL 3", "Kirby", 0), (None, None, None, None)]
    for i, (p, lab, nm, co) in enumerate(specs):
        x = x0 + i * (bw + gap)
        if p:
            costume = "".join('<i style="display:inline-block;width:8px;height:8px;border-radius:9px;margin-right:2px;background:%s"></i>' % ("#e8dfca" if k == co else "#3c4d45") for k in range(5))
            inner = ('<div style="position:absolute;left:8px;top:8px">%s</div><div style="position:absolute;left:8px;top:40px">%s</div>'
                     '<div style="position:absolute;left:%spx;top:44px;width:%spx"><div style="font-size:16px;font-weight:900;letter-spacing:.04em;text-transform:uppercase">%s</div>'
                     '<div style="margin-top:8px">%s</div></div>') % (flag(p, lab), disc("icon", "disc art", cls="sm"), 72 if not wide else 78, bw - 80, esc(nm), costume)
            bays += at(x, 54, inner, w=bw, h=102, cls="bay %s" % p, extra="color:var(--bone)")
        else:
            inner = '<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px"><div class="board off row" style="width:%spx;height:40px;justify-content:center">Join</div><span class="print">Pick up a pad</span></div>' % (bw - 24)
            bays += at(x, 54, inner, w=bw, h=102, cls="bay", extra="border-top-color:#3c4d45")
    # roster
    cols = 14 if wide else 9
    cw = 56 + (6 if not wide else 8)
    rows_ = -(-len(ROSTER) // cols)
    cells = ""
    for i, nm in enumerate(ROSTER):
        cells += rcell(nm, focus=(nm == "Ness"), sel=(nm == "Fox"), cursor_port=("p1" if nm == "Ness" else None))
    trayw = cols * cw + 4
    trw = trayw + 20
    gx = (640 - trw) / 2
    grid = at(gx, 168, '<div style="display:grid;grid-template-columns:repeat(%d,56px);gap:8px 6px;padding:14px 10px 10px;justify-content:center">%s</div>' % (cols, cells), w=trw, cls="tray", extra="")
    # name tag tied to the lifted cell
    ci = ROSTER.index("Ness")
    cx, cy = gx + 10 + (ci % cols) * (56 + 6), 168 + 14 + (ci // cols) * 56
    nt = at(cx - 22, cy - 40, '<div class="tag" style="width:106px"><span class="hole" style="left:6px;top:6px;width:10px;height:10px"></span><div class="face" style="padding:6px 6px 6px 22px;clip-path:polygon(0 10px,10px 0,100% 0,100% 100%,0 100%)"><h4 style="margin:0;font-size:14px;letter-spacing:.02em">NESS</h4></div></div>')
    # added fighters
    ay = 168 + 14 + rows_ * 56 + 22
    ad = ""
    for nm, g in (("Meta Knight", 1), ("Kirby (Ultimate)", 0), ("Sora", 1)):
        ad += rcell(nm, geno=bool(g))
    added = at(gx, ay, '<div style="display:flex;align-items:center;gap:14px;padding:8px 14px"><span class="print" style="width:120px;line-height:1.25">Added fighters<br>page 2 of 2</span><div style="display:flex;gap:12px">%s</div>'
               '<span style="margin-left:auto;display:flex;align-items:center;gap:6px">%s<span style="font-size:14px">= defined in Geno</span></span></div>' % (ad, stamp("GENO", "color:var(--bone)")), w=trw, cls="tray")
    key = at(gx, ay + 76, '<span class="print">Hatched frame = disc art (placeholder)</span>') if wide else ""
    return screen(w, head("Characters", ["Versus"]) + bays + grid + nt + added + key,
                  rail_for(w, ph("pick", "put", "turn", extra=[(pad("L") + pad("R"), "Next page")])))


# ================================================================== 05 stage select
def s05(w=640):
    cells = ""
    for i, nm in enumerate(STAGES):
        cells += disc("icon", "disc art", w=88, h=66, cls="focus" if i == 7 else "").replace("<span>disc art</span>", "")
    tr = at(32, 66, '<div style="display:grid;grid-template-columns:repeat(4,88px);gap:10px 8px;padding:16px 16px">%s</div>' % cells, w=404, cls="tray")
    big = at(454, 66, disc("icon", "disc art", w=154, h=104), w=154)
    tg = at(450, 196, tag("BRINSTAR DEPTHS", "P1 picks the stage.", meta=flag("p1", "P1"), w=158))
    st = string(472, 212, 428, 194, sag=14)
    page = at(454, 340, '<div class="print" style="margin-bottom:6px">Page 1 of 2</div>' + prog(2, 1, cur=0), w=154)
    lst = at(450, 384, row("List", "Standard", style="height:34px;width:158px;padding:0 8px"), w=158)
    return screen(w, head("Stages", ["Versus", "Characters"]) + tr + big + st + tg + page + lst,
                  rail_for(w, ph("pick", "put", "lr", "turn")))


# ================================================================== 06 versus rules
def s06(w=640):
    R = [("Mode", choice("Stock", 3, 0, wide=96), 0), ("Stocks", choice("4", 5, 3, wide=44), 0), ("Time limit", slider(0.48, 110) + '<span class="win" style="min-width:56px;margin-left:8px">8:00</span>', 1),
         ("Handicap", choice("Off", 2, 0, wide=60), 0), ("Damage ratio", slider(0.4, 110) + '<span class="win" style="min-width:56px;margin-left:8px">1.0x</span>', 1),
         ("Team attack", tog(False), 0), ("Items", choice("Off", 3, 0, wide=80), 0), ("Stage choice", choice("Pick", 3, 0, wide=80), 0), ("Turbo", tog(True), 0)]
    out = ""
    for i, (lab, wd, _) in enumerate(R):
        f = lab == "Turbo"
        out += '<div %s>%s</div>' % (pos(32, 62 + i * 38, 392, 32), row(lab, cls="focus" if f else "", widget=wd, style="height:32px;width:392px"))
    tg = at(444, 196, tag("TURBO", "Everything runs faster.", meta=chip("a match rule"), price="Same switch in online rooms.", w=164))
    st = string(464, 212, 428, 372, sag=-14)
    go = at(444, 392, '<div class="board btn" style="height:44px;font-size:16px;padding:0 10px;width:164px;white-space:nowrap">Pick fighters</div>')
    intro = at(444, 66, '<span class="print" style="line-height:1.4;display:block">Nine rules.<br>The piece in your hand<br>is the one with a tag.</span>')
    return screen(w, head("Match setup", ["Versus"]) + out + intro + tg + st + go, rail_for(w, ph("pick", "put", "turn", "move")))


# ================================================================== 07 online room
def s07(w=640):
    code = at(32, 56, '<span class="print" style="margin-right:8px">Room code</span>' + tape("[ROOM CODE]"), extra="display:flex;align-items:center")

    def bay(p, y, nm, ready, ping):
        rd = ('<div class="board btn" style="height:34px;padding:0 12px;font-size:14px;gap:6px">%s READY</div>' % pin()) if ready else '<div class="board off row" style="height:34px;padding:0 12px;font-size:14px">Waiting</div>'
        rd = rd.replace('class="pin"', 'class="pin" style="display:inline-flex"')
        bars = '<span style="display:inline-flex;gap:3px;align-items:flex-end">%s</span>' % "".join('<i style="width:6px;height:%dpx;background:%s;display:block"></i>' % (6 + k * 4, "var(--bone)" if k < ping else "#3c4d45") for k in range(4))
        inner = ('<div style="position:absolute;left:10px;top:10px">%s</div><div style="position:absolute;left:10px;top:42px;font-size:24px;font-weight:900;letter-spacing:.05em;text-transform:uppercase">%s</div>'
                 '<div style="position:absolute;left:10px;bottom:10px;display:flex;align-items:center;gap:8px">%s<span style="font-size:14px">%s</span></div>'
                 '<div style="position:absolute;right:10px;bottom:10px">%s</div>') % (flag(p, "P1 · HOST" if p == "p1" else "P2 · GUEST"), esc(nm), bars, "Good · [PING] ms" if ping > 2 else "Slow · [PING] ms", rd)
        return at(32, y, inner, w=272, h=112, cls="bay %s" % p)
    bays = bay("p1", 96, "GD", True, 4) + bay("p2", 220, "[GUEST NAME]", False, 2)
    R = [("Turbo", tog(True), "focus"), ("Envoy rules", choice("Off", 2, 0, wide=64), ""), ("Stocks", choice("4", 5, 3, wide=44), ""), ("Time limit", choice("8:00", 3, 1, wide=64), ""),
         ("Stage list", choice("Standard", 3, 0, wide=88), ""), ("Input delay", choice("Auto", 3, 0, wide=56), "")]
    rows = "".join('<div %s>%s</div>' % (pos(324, 96 + i * 40, 284, 34), row(l, cls=c, widget=wd, style="height:34px;width:284px")) for i, (l, wd, c) in enumerate(R))
    rl = at(324, 66, '<span class="print">Room rules (host sets)</span>')
    tg = at(324, 350, tag("TURBO", "Everything runs faster.", w=284))
    st = string(344, 366, 590, 130, sag=24)
    sl = at(40, 354, slip("Both players see the rules before they ready up.", "Notice", w=240), w=240)
    return screen(w, head("Online room", ["Versus", "Online"]) + code + bays + rl + rows + tg + sl,
                  rail_for(w, [(pad("A"), "Pick up"), (pad("B"), "Leave the room"), (pad("X"), "Copy code"), (pad("Y"), "Rules")]))


# ================================================================== 08 envoy setup
def s08(w=640):
    seg = lambda a, b, ia: ('<div class="seg"><div class="board %s">%s%s</div><div class="board %s">%s%s</div></div>'
                            % ("sel" if ia == 0 else "", pin(), a, "sel" if ia == 1 else "", pin(), b))
    st = lambda lab, wd, y, f=False: at(32, y, row(lab, cls="focus" if f else "", widget=wd, style="height:56px;width:380px"), w=380, h=56)
    r1 = st("Type", seg("Classic", "Adventure", 0), 74)
    r2 = st("Fighter", '<span class="win" style="min-width:90px">Fox</span>', 142, True)
    r3 = st("Players", seg("Solo", "Co-op", 0), 210)
    r4 = st("Difficulty", choice("Standard", 3, 0, wide=100), 278)
    start = at(32, 360, '<div class="board btn hero" style="width:380px">Start run</div>')
    tray = at(436, 66, '<div style="display:flex;flex-direction:column;align-items:center;padding:12px 8px 14px;gap:10px"><span class="print" style="text-align:center">Your bench<br>starts empty</span>'
              + '<div style="display:grid;grid-template-columns:repeat(3,48px);gap:8px">%s</div></div>' % "".join(sock("", cls="empty", style="width:48px;height:48px") for _ in range(6)), w=172, cls="tray")
    por = at(436, 250, disc("icon", "disc art", cls="") + '<div style="margin-left:14px;font-size:24px;font-weight:900;letter-spacing:.06em">FOX</div>', extra="display:flex;align-items:center")
    sl = at(440, 340, slip("Drives you win land on the bench.", "How it works", w=168), w=168)
    return screen(w, head("Run setup", ["Supertime Envoy"]) + r1 + r2 + r3 + r4 + start + tray + por + sl,
                  rail_for(w, ph("pick", "put", "move")))


# ================================================================== 09 bag
def s09(w=640):
    wide = w > 640
    big = 56 if wide else 46
    pg = 6
    lw = 6 * (big + pg) + 20
    tagx = 32 + lw + (36 if wide else 16)
    tagw = int(w - 32 - tagx) if wide else 228
    ps = lambda fam, cl="seat": puck(fam, "sm " + cl, style="margin:%spx" % ((big - 40) / 2))
    sk = lambda inner, cls="": sock(inner, cls, style="width:%dpx;height:%dpx" % (big, big))

    # keystones on the rail
    nk = 4 if wide else 3
    keys = ""
    for i, (l, c) in enumerate((("P", "red"), ("F", "blue"))):
        keys += at(40 + i * 76, 74, keystone(l, c), w=56)
    for i in range(2, nk):
        keys += at(40 + i * 76, 74, hook_empty(), w=56)
    rail = at(32, 64, '<div class="rail" style="width:%spx"></div>' % lw)
    kl = at(32, 48, '<span class="print">Keystones: 2 hanging</span>')

    # equipped tray: slots 1, 2, [3+4 merged pair], 5, 6 (slot numbers printed)
    def slot(inner, name):
        return '<div style="width:%dpx">%s<div class="nm" style="width:%dpx;margin-top:6px">%s</div></div>' % (big, inner, big + 8, name)
    pair_h = big * 2 + 4
    pair = ('<div style="position:relative;width:%dpx;height:%dpx"><div class="sock" style="width:%dpx;height:%dpx;position:absolute;left:0;top:0"></div>'
            '<div style="position:absolute;left:0;top:0">%s</div><div style="position:absolute;left:0;top:%dpx">%s</div>'
            '<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:8px;background:var(--steel);box-shadow:0 2px 0 var(--steel-edge);z-index:5"></div></div>'
            % (big, pair_h, big, pair_h, ps("purple", "focus"), big - 2, ps("purple", "focus"), 6, big - 5, big - 8))
    pair_html = '<div style="width:%dpx">%s<div class="nm" style="width:%dpx;margin-top:6px;margin-left:-4px;color:var(--bone)">Frosted + Icebound</div></div>' % (big, pair, big + 8)
    els = (slot(sk(ps("red")), "Burning") + slot(sk(ps("red")), "Kindling") + slot(sk(ps("white")), "Echoes") + slot(sk(ps("blue")), "Reprisal") + pair_html)
    ey = 176
    lbl = at(32, ey - 18, '<span class="print">Equipped 6 of 6</span>')
    eq_tray = at(32, ey, '<div style="display:flex;gap:%dpx;padding:10px;align-items:flex-start">%s</div>' % (pg, els), w=lw, cls="tray")
    th = 20 + pair_h + 22
    by = ey + th + 26
    bag = at(32, by, '<div style="display:flex;gap:%dpx;padding:10px">%s</div>' % (pg, "".join(sk(ps(f)) for f in ("blue", "yellow", "purple", "red"))), w=4 * (big + pg) + 14, cls="tray")
    bl = at(32, by - 18, '<span class="print">Bag 4 of 4</span>')

    # the tags (one rule each) for the lifted pair, tied to it by strings
    t1 = at(tagx, 56, tag("FROSTED", "Smash attacks become ice", meta=chip("standing rule"), w=tagw))
    t2 = at(tagx, 168, tag("ICEBOUND", "Your hits Chill the target for 2 s.", meta=chip("trigger rule"), w=tagw))
    staple = ""
    px = 32 + 10 + 4 * (big + pg) + big
    s1 = string(tagx + 20, 72, px - 4, ey + 24, sag=26)
    s2 = string(tagx + 20, 184, px - 4, ey + 24 + big, sag=20)
    sl = at(tagx, 332, slip("Merged: Frosted + Icebound", "Set down", w=min(tagw, 230)), w=tagw)
    mid = at(tagx, 396, '<span class="print" style="line-height:1.4;display:block">One rule per piece.<br>Hold a piece to read it.</span>')
    inner = head("Your drives", ["Supertime Envoy"], x=32) + kl + rail + keys + lbl + eq_tray + bl + bag + t1 + staple + t2 + s1 + s2 + sl + mid
    hs = ph("pick", "put", "turn", "cmp", extra=[(pad("L") + pad("R"), "Bench / bag")])
    return REG + inner + hints(hs, pad_left=32)


# ================================================================== 10 reward
def s10(w=640):
    offers = [("ICEBOUND", "Your hits Chill the target for 2 s.", "purple", True),
              ("UPDRAFT", "Aerial hits add 1 Momentum (up to 5) for 5 s.", "yellow", False),
              ("REPRISAL", "Perfect shield: Guarded for 3 s.", "blue", False)]
    out = ""
    for i, (nm, rule, fam, comp) in enumerate(offers):
        x = 32 + i * 200
        stp = ('<div style="height:20px">%s</div>' % stamp("completes ice")) if comp else '<div style="height:20px"></div>'
        body = ('<div style="padding:12px 14px 10px">%s<div style="display:flex;justify-content:center;height:100px;margin-top:6px">%s</div>'
                '<div style="font-size:20px;font-weight:900;letter-spacing:.06em;margin-top:8px">%s</div><div style="font-size:14px;font-weight:700;line-height:1.25;margin-top:4px;min-height:54px">%s</div>'
                '<div style="margin-top:6px">%s</div></div>') % (stp, puck(fam, "xl", style="margin:6px 0 0"), nm, esc(rule), chip("trigger rule"))
        out += at(x, 62 + (0 if i == 0 else 4), body, w=176, h=254, cls="board %s" % ("focus" if i == 0 else ""))
    bench = "".join(sock(puck(f, "sm seat", style="margin:6px"), style="width:52px;height:52px") for f in ("red", "red", "purple", "white"))
    bench += sock("", cls="empty", style="width:52px;height:52px;box-shadow:inset 0 3px 0 #000, 0 0 0 3px var(--focus)")
    padlock = '<svg viewBox="0 0 28 28" width="26" height="26" fill="currentColor"><rect x="5" y="12" width="18" height="13" rx="2"/><path d="M9 12V9a5 5 0 0 1 10 0v3" fill="none" stroke="currentColor" stroke-width="3"/></svg>'
    bench += sock('<div class="lock">%s</div>' % padlock, style="width:52px;height:52px")
    tray = at(32, 350, '<div style="display:flex;gap:6px;padding:8px 10px">%s</div>' % bench, cls="tray")
    bl = at(32, 332, '<span class="print">Your bench · slot 5 is new</span>')
    timer = at(424, 350, '<div class="print" style="margin-bottom:6px;line-height:1.3">Take one before<br>the timer ends</div>' + prog(9, 6), w=184)
    new = at(404, 8, slip("Unlocked: fifth slot", "Milestone", w=190), w=190)
    st = string(100, 312, 180, 378, sag=36)
    return screen(w, head("Stage cleared", ["Supertime Envoy"]) + out + st + bl + tray + timer + new, rail_for(w, ph("pick", "put", "turn", "move")))


# ================================================================== 11 HUD
def stage_bg():
    return ('<div class="stagebg"><i style="left:110px;top:326px;width:420px;height:46px"></i><i style="left:150px;top:394px;width:340px;height:90px;opacity:.7"></i>'
            '<i style="left:150px;top:262px;width:90px;height:10px"></i><i style="left:400px;top:262px;width:90px;height:10px"></i><i style="left:275px;top:204px;width:90px;height:10px"></i>'
            '<i style="left:296px;top:296px;width:48px;height:30px;border-radius:12px 12px 0 0;background:#34454e"></i></div>')


def s11(w=640):
    sq = [("red", 1), ("red", 1), ("purple", 1), ("purple", 1), ("white", 1), ("blue", 1)]
    bar = '<div class="bar6">%s</div>' % "".join('<i class="fam-%s">%s</i>' % (f, famshape(f, 14)) for f, _ in sq[:6])
    keys = '<div style="display:flex;gap:6px;margin-top:10px">%s</div>' % (
        '<div class="ks-s kc-red"><div class="face">P</div><div class="band"></div></div><div class="ks-s kc-blue"><div class="face">F</div><div class="band"></div></div>')
    top = at(32, 22, '<div class="print" style="margin-bottom:6px;color:var(--bone)">Build</div>' + bar + keys)
    instr = at(220, 20, slip("Collect the drives", "Stage 4", w=200, cls="flat"), w=200)
    opp = at(450, 22, ('<div class="hudplate" style="width:158px;height:46px;padding:5px 8px;display:flex;align-items:center;gap:8px">%s<span style="font-size:14px;font-weight:900">MARTH</span><span style="margin-left:auto;font-size:20px;font-weight:900">82%%</span></div>') % peg("cpu").replace('class="peg', 'class="peg sm'))
    plate = at(40, 384, ('<div class="hudplate" style="width:176px;height:66px;padding:6px 10px"><div style="display:flex;align-items:center;gap:8px">%s<span style="font-size:14px;font-weight:900">FOX</span></div>'
                          '<div style="display:flex;align-items:flex-end;gap:10px;margin-top:2px"><span style="font-size:36px;font-weight:900;line-height:1">47<span style="font-size:20px">%%</span></span><span style="display:flex;gap:4px;margin-bottom:5px">%s</span></div></div>')
               % (flag("p1", "P1"), "".join(peg("p1").replace('class="peg', 'class="peg sm plain') for _ in range(3))))
    note = at(430, 400, slip("Picked up: Icebound", "Drive", w=180), w=180)
    inner = stage_bg() + top + instr + opp + plate + note
    return screen(w, inner, "", bg=False)


# ================================================================== 12 pause + payout
def s12(w=640):
    items = [("RESUME", "play", True), ("BAG", "page", False), ("CONTROLS", "pad", False), ("QUIT", "warn", False)]
    rows = "".join('<div %s>%s</div>' % (pos(70, 150 + i * 62, 240, 52), row(l, cls="big" + (" focus" if f else ""), icon=(icon(ic) if ic != "play" else '<svg class="icn" viewBox="0 0 28 28"><polygon points="6,3 25,14 6,25"/></svg>'), style="height:52px;width:240px;" + ("background:#e9c9c2;" if l == "QUIT" else ""))) for i, (l, ic, f) in enumerate(items))
    cover = '<div class="cover"></div>'
    t = at(70, 90, tape("Paused") + '<span style="margin-left:14px">%s</span>' % flag("p1", "P1 HOLDS THE PAD"), extra="display:flex;align-items:center;z-index:25")
    tg = at(350, 150, tag("RESUME", "Put the match back on the bench.", w=230))
    bench = at(350, 250, '<div class="print" style="margin-bottom:6px">Your build</div><div class="bar6">%s</div>' % "".join('<i class="fam-%s">%s</i>' % (f, famshape(f, 14)) for f in ("red", "red", "purple", "purple", "white", "blue")), w=230)
    z = lambda s: s.replace('class="board row', 'style_z class="board row')
    body = stage_bg() + cover + '<div style="position:absolute;inset:0;z-index:22">' + t + rows + tg + bench + '</div>'
    return screen(w, body, rail_for(w, ph("pick", "put", "move")).replace('class="hints" style="', 'class="hints" style="z-index:30;'), bg=False)


def s12b(w=640):
    rec = at(60, 40, ('<div class="receipt"><div style="font-size:24px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px">Stage 4 cleared</div>'
                      '<div class="ln"><span>Drives collected</span><b>3</b></div><div class="ln"><span>Clear time</span><b>[TIME]</b></div><div class="ln"><span>Best time</span><b>[BEST TIME]</b></div>'
                      '<div class="ln"><span>Keystone choice</span><b>earned</b></div><div style="margin-top:12px">%s</div></div>') % stamp("Unlocked: fifth slot"))
    bench = "".join(sock(puck(f, "sm seat", style="margin:6px"), style="width:52px;height:52px") for f in ("red", "red", "purple"))
    bench += sock("", cls="empty", style="width:52px;height:52px")
    bench += sock("", cls="empty", style="width:52px;height:52px")
    tray = at(330, 220, '<div style="display:flex;gap:6px;padding:10px">%s</div>' % bench, cls="tray")
    drop = at(330 + 3 * 58 + 10, 150, puck("yellow", "sm", style="margin:6px"), w=52)
    shadow = at(330 + 3 * 58 + 20, 232, '<div style="width:34px;height:8px;background:var(--shadow);opacity:.55;border-radius:9px"></div>')
    lab = at(330, 96, '<span class="print" style="line-height:1.4;display:block">Payout drops in,<br>left to right</span>')
    sl = at(380, 320, slip("Your bag is empty: 4 free", "Notice", w=200), w=200)
    return screen(w, head("Payout", ["Supertime Envoy"], x=330, y=16).replace("left:330px", "left:330px") + rec + lab + tray + drop + shadow + sl,
                  rail_for(w, [(pad("A"), "Pick up the rewards")]))


# ================================================================== 13 results
def s13(w=640):
    res = [("p1", "FOX", 1, 176), ("p2", "MARTH", 2, 142), ("cpu", "KIRBY", 3, 116), ("p4", "[NAME]", 4, 96)]
    pods = ""
    base = 384
    for i, (p, nm, pl, h) in enumerate(res):
        x = 56 + i * 134
        top = base - h
        cl = "focus" if pl == 1 else ""
        inner = ('<div style="padding:10px;font-size:14px"><div style="font-size:32px;font-weight:900;line-height:1">%s</div><div style="font-size:14px;font-weight:900;margin-top:4px;letter-spacing:.05em">%s</div><div style="font-size:14px;font-weight:600;margin-top:4px">KOs [KOS]</div></div>' % (["1st", "2nd", "3rd", "4th"][pl - 1], nm))
        pods += at(x, top, inner, w=118, h=h, cls="board %s" % cl, extra="border-radius:3px 3px 0 0")
        pods += at(x + 12, top - 82 - (5 if pl == 1 else 0), disc("icon", "disc art"), w=72)
        pods += at(x + 90, top - 28 - (5 if pl == 1 else 0), peg(p), w=28)
    floor = at(32, base + 3, '<div style="height:10px;background:var(--steel);border-radius:2px;box-shadow:0 3px 0 var(--steel-edge)"></div>', w=576)
    return screen(w, head("Results", ["Versus"]) + pods + floor, rail_for(w, [(pad("A"), "Rematch"), (pad("B"), "Back to fighters"), (pad("X"), "Turn over the stats")]))


# ================================================================== 14 settings
PAGES = ["VIDEO", "AUDIO", "CONTROLS", "ONLINE", "MODS", "GAMEPLAY"]


def settings_shell(sel, rows, extra="", title="Settings"):
    t = at(32, 62, tabs(PAGES, sel, focus=None))
    sheet = at(32, 96, rows, w=576, h=330, cls="sheet", extra="padding:16px 18px")
    return head(title, ["Main menu"]) + t + sheet + extra


def s14(w=640):
    R = [("Render scale", slider(0.5, 150) + '<span class="win" style="min-width:48px;margin-left:8px">2x</span>', 0),
         ("Frame rate", choice("120", 3, 1, wide=96), 1), ("Vsync", tog(True), 0), ("FPS readout", tog(False), 0)]
    rows = "".join('<div style="margin-bottom:12px">%s</div>' % row(l, cls="focus" if i == 1 else "", widget=wd, style="height:40px") for i, (l, wd, _) in enumerate(R))
    rows = '<div style="width:340px">%s</div>' % rows
    side = at(400, 112, tag("FRAME RATE", "How often the picture updates.", w=186, price="Uncapped is for testing."), w=186)
    return screen(w, settings_shell(0, rows, side), rail_for(w, ph("pick", "put", "lr", "move")))


def s14b(w=640):
    R = [("Master volume", slider(0.6, 140) + '<span class="win" style="min-width:48px;margin-left:8px">60</span>'), ("Music", slider(0.8, 140) + '<span class="win" style="min-width:48px;margin-left:8px">80</span>'),
         ("Effects mix", slider(0.7, 140) + '<span class="win" style="min-width:48px;margin-left:8px">70</span>'), ("Sound", choice("Stereo", 2, 0, wide=88))]
    rows = "".join('<div style="margin-bottom:12px">%s</div>' % row(l, cls="focus" if i == 0 else "", widget=wd, style="height:40px") for i, (l, wd) in enumerate(R))
    rows = '<div style="width:380px">%s</div>' % rows
    side = at(420, 112, tag("MASTER VOLUME", "Everything, at once.", w=170), w=170) + at(420, 220, '<div class="tip">Left / right to turn it</div>')
    return screen(w, settings_shell(1, rows, side), rail_for(w, ph("pick", "put", "lr", "move")))


def s14c(w=640):
    padsvg = ('<svg viewBox="0 0 200 130" width="190" height="124" style="filter:drop-shadow(4px 6px 0 var(--shadow))"><path d="M30 20 Q60 6 100 12 Q140 6 170 20 Q196 40 192 86 Q186 124 160 120 Q140 116 128 92 L72 92 Q60 116 40 120 Q14 124 8 86 Q4 40 30 20Z" fill="#e8dfca"/>'
              '<rect x="38" y="46" width="28" height="9" fill="#191714"/><rect x="47.5" y="36.5" width="9" height="28" fill="#191714"/><circle cx="68" cy="82" r="11" fill="#8a8470"/><circle cx="134" cy="82" r="9" fill="#d6c47a"/>'
              '<circle cx="152" cy="42" r="10" fill="#3fae6a" stroke="#ff7a2f" stroke-width="4"/><text x="152" y="46.5" text-anchor="middle" font-family="SS3" font-weight="900" font-size="13" fill="#06210f">A</text>'
              '<circle cx="132" cy="54" r="6" fill="#e0443a"/><ellipse cx="164" cy="64" rx="5" ry="7" fill="#9a968a"/><ellipse cx="148" cy="26" rx="7" ry="5" fill="#9a968a"/>'
              '<rect x="86" y="46" width="28" height="9" rx="4" fill="#9a968a"/><rect x="146" y="2" width="30" height="8" rx="3" fill="#9a6ae0"/></svg>')
    left = at(14, 4, '<div class="print" style="margin-bottom:6px">Profile</div>' + '<div class="seg"><div class="board sel">%s Keyboard</div><div class="board">Pad</div></div>' % pin()
              + '<div style="margin-top:10px">%s</div><div class="print" style="margin:8px 0 4px">Presets</div><div style="display:flex;gap:5px;flex-wrap:wrap;width:236px">%s%s%s</div>' % (padsvg, chip("Default"), chip("Left hand", "line"), chip("Fighting pad", "line")))
    keys = [("A", "J", "Mouse L"), ("B", "K", ""), ("X", "L", ""), ("Y", "I", ""), ("Z", "O", ""), ("START", "Enter", "")]
    rr = ""
    for i, (b, k1, k2) in enumerate(keys):
        win = '<span class="win" style="min-width:46px">%s</span>' % esc(k1)
        also = ('<span class="win" style="min-width:60px">%s</span>' % esc(k2)) if k2 else '<span class="win" style="min-width:60px;color:#7f8a83">+ also</span>'
        rr += '<div style="margin-bottom:6px">%s</div>' % row("", cls="focus" if i == 0 else "", icon=pad(b), widget=win + also, style="height:34px;width:262px;gap:6px;padding:0 8px")
    right = ('<div style="position:absolute;left:262px;top:2px;width:262px"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><span class="print">Bindings</span>'
             '<div class="seg"><div class="board sel" style="height:26px;padding:0 8px;font-size:12px">%s Swap</div><div class="board" style="height:26px;padding:0 8px;font-size:12px">Also</div></div></div>%s<div class="more"></div></div>') % (pin(), rr)
    body = '<div style="position:relative;width:530px;height:300px">%s%s</div>' % (left, right)
    slipx = at(404, 4, slip("Press the key you want", "Binding A", w=190), w=190)
    return screen(w, settings_shell(2, body, "", title="Settings") + slipx, rail_for(w, [(pad("A"), "Pick up a binding"), (pad("B"), "Put back"), (pad("X"), "Clear it"), (pad("Y"), "Test pad"), (pad("L") + pad("R"), "Page")]))


# ================================================================== 15 mods
def s15(w=640):
    mods = [("Supertime Envoy", "script", True, "+ ENVOY", False), ("Envoy Drives", "assets", True, None, False), ("Envoy Drives SA2", "assets", True, None, False),
            ("Geno Lab", "script", True, "+ LAB", True), ("The Courier", "fighter", False, None, False), ("Sora", "fighter", True, None, False), ("Meta Knight", "fighter", False, None, False)]
    rows = ""
    for i, (nm, kind, on, entry, f) in enumerate(mods):
        wd = (stamp(entry) if entry else "") + chip(kind) + tog(on)
        rows += '<div %s>%s</div>' % (pos(32, 64 + i * 46, 400, 38), row(nm, cls="focus" if f else "", widget=wd, style="height:38px;width:400px;gap:8px"))
    clamp = at(436, 64 + 1 * 46 + 12, '<div style="width:14px;height:58px;border:5px solid var(--steel);border-left:0;border-radius:0 8px 8px 0;box-shadow:3px 3px 0 var(--shadow)"></div>', w=24)
    cl = at(470, 64 + 1 * 46 + 4, slip("Conflict: both give the same drive models. Pick one.", "Warning", cls="warn", w=138), w=138)
    tg = at(444, 274, tag("GENO LAB", "Adds LAB to Solo.", meta=chip("script"), price="Applies at next start.", w=164))
    st = string(464, 290, 412, 220, sag=30)
    legend = at(32, 398, '<span class="print">+ NAME on a mod = it adds a menu entry</span>')
    return screen(w, head("Mods", ["Settings"]) + rows + clamp + cl + tg + st + legend,
                  rail_for(w, [(pad("A"), "Switch on / off"), (pad("B"), "Put back"), (pad("X"), "Turn over"), (pad("Y"), "Sort by kind")]))


# ================================================================== 16 LAB pause
MODES = ["CLEAN", "HITBOXES", "FRAMES", "STAGE", "INSPECT", "MOVES", "LAUNCH", "TRAINING", "COMBO"]


def s16(w=640):
    tabs_ = at(32, 62, tabs(["PLAY", "DISPLAY", "DUMMY", "STATES", "TOOLS", "EXIT"], 0))
    chips = "".join('<div class="board %s" style="height:28px;padding:0 5px;display:flex;align-items:center;font-size:12px;letter-spacing:0;font-weight:900">%s%s</div>'
                    % ("sel" if m == "HITBOXES" else "", pin().replace('class="pin"', 'class="pin" style="width:12px;height:12px;margin-right:3px"') if m == "HITBOXES" else "", m) for m in MODES)
    mode = '<div class="print" style="margin-bottom:6px">Mode</div><div style="display:flex;gap:4px;width:548px">%s</div>' % chips
    R = [("Hitboxes", tog(True)), ("Frame step", '<span class="win">Press A</span>'), ("Rewind", '<span class="win">Hold L</span>'), ("Speed", slider(0.5, 100) + '<span class="win" style="min-width:48px;margin-left:8px">1x</span>'), ("Timer", tog(False))]
    rows = "".join('<div style="margin-top:%dpx;width:310px">%s</div>' % (16 if i == 0 else 6, row(l, cls="focus" if i == 0 else "", icon=icon(["eye", "step", "step", "tool", "page"][i]).replace('class="icn"', 'class="icn" style="width:22px;height:22px"'), widget=wd, style="height:34px")) for i, (l, wd) in enumerate(R))
    body = '<div style="position:relative">%s%s</div>' % (mode, rows)
    sheet = at(32, 96, '<div style="padding:12px 14px;position:relative">%s</div>' % body, w=576, h=316, cls="sheet")
    tg = at(374, 206, tag("HITBOXES", "Draw every hitbox and hurtbox.", w=212, price="Turns off with CLEAN."), w=212)
    st = string(393, 222, 330, 190, sag=30)
    cover = '<div class="cover" style="z-index:1"></div>'
    return stage_bg() + cover + '<div style="position:absolute;inset:0;z-index:5">' + REG + head("The LAB", ["Solo"]) + tabs_ + sheet + st + tg + '</div>' + rail_for(w, ph("pick", "put", "lr", "move")).replace('class="hints" style="', 'class="hints" style="z-index:30;')


# ================================================================== 17 launcher (desktop window, 960x600)
def s17():
    discs = [("Vanilla", "Ready"), ("Akaneia", "Ready"), ("ACE", "Ready")]
    rows = "".join('<div style="margin-bottom:10px">%s</div>' % row(n, cls=("sel " if i == 0 else "") + ("focus" if i == 1 else ""), widget=chip(st, "line"), style="height:44px") for i, (n, st) in enumerate(discs))
    lab = lambda t: '<span style="font-size:16px;font-weight:900;letter-spacing:.06em;text-transform:uppercase;color:var(--ink)">%s</span>' % t
    opts = "".join('<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">%s%s</div>' % (lab(l), tog(o)) for l, o in (("Unlock everything", False), ("Skip intro", True), ("Close launcher on play", False)))
    vol = '<div style="display:flex;align-items:center;justify-content:space-between">%s<span style="display:flex;align-items:center;gap:8px">%s<span class="win" style="min-width:44px">40</span></span></div>' % (lab("Volume"), slider(0.4, 150))
    left = ('<div class="print" style="margin-bottom:8px">Disc library</div>%s<div style="display:flex;gap:12px;margin-top:6px">'
            '<div class="board btn" style="height:36px;font-size:14px;padding:0 14px">Add disc</div><div class="board btn" style="height:36px;font-size:14px;padding:0 14px">Manage</div></div>') % rows
    sheet = at(24, 94, '<div style="display:flex;gap:28px;padding:20px 22px"><div style="width:330px">%s</div><div style="width:320px"><div class="print" style="margin-bottom:10px">Options</div>%s%s</div></div>' % (left, opts, vol), w=700, h=300, cls="sheet")
    pk = at(24, 420, '<div class="board btn hero focus" style="width:300px;height:64px;font-size:28px">Play</div>')
    art = at(748, 94, '<div style="display:grid;grid-template-columns:repeat(2,64px);gap:10px;padding:14px">%s</div>' % "".join(sock(puck(f, "seat"), style="width:64px;height:64px") for f in ("red", "green", "blue", "yellow", "purple", "white")), w=172, cls="tray")
    ver = at(748, 340, '<div class="print" style="line-height:1.6">Version [VERSION]<br>Mods on: 4<br>Netplay: [STATUS]</div>')
    title = '<div style="position:absolute;left:0;top:0;right:0;height:40px;background:var(--tape);display:flex;align-items:center;padding:0 16px;gap:12px;box-shadow:0 3px 0 var(--tape-lip)"><span style="font-weight:900;font-size:16px;letter-spacing:.14em;text-transform:uppercase">GD\'s Melee Launcher</span><span style="margin-left:auto;display:flex;gap:14px;font-weight:900;font-size:16px;color:var(--mat-print)">&#9472;&nbsp;&nbsp;&#9633;&nbsp;&nbsp;&#10005;</span></div>'
    tb = at(24, 60, tabs(["PLAY", "MODS", "DIAGNOSTICS", "ABOUT"], 0, focus=None), cls="")
    foot = ('<div class="hints" style="position:absolute;left:0;right:0;bottom:0">%s%s%s<span class="sp"></span><span class="print">Mouse and keyboard</span></div>'
            % ('<span class="h">' + mouse("L") + '<span>Click to pick up</span></span>', '<span class="h">' + kc("Tab") + '<span>Move along</span></span>', '<span class="h">' + kc("Esc") + '<span>Put back</span></span>'))
    return REG + title + tb + sheet + pk + art + ver + foot
