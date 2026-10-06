"""Screens 01-08. Each function returns a full HTML page string; parts.page() draws the frame (trail, chapter, hints)."""
from parts import *
from parts import _cw

RETAIL = ["Mario", "Luigi", "Bowser", "Peach", "Yoshi", "Donkey Kong", "Captain Falcon", "Ganondorf", "Falco", "Fox", "Ness",
          "Ice Climbers", "Kirby", "Samus", "Zelda", "Sheik", "Link", "Young Link", "Pichu", "Pikachu", "Jigglypuff", "Mewtwo",
          "Mr. Game & Watch", "Marth", "Roy", "Dr. Mario"]
ADDED = [("Meta Knight", "add"), ("Ultimate Kirby", "add"), ("Sora", "geno")]
STAGES = ["Peach's Castle", "Rainbow Cruise", "Kongo Jungle", "Jungle Japes", "Great Bay", "Temple", "Brinstar", "Brinstar Depths",
          "Yoshi's Story", "Yoshi's Island", "Fountain of Dreams", "Green Greens", "Corneria", "Venom", "Pokemon Stadium",
          "Poke Floats", "Mute City", "Big Blue", "Onett", "Fourside", "Icicle Mountain", "Mushroom Kingdom", "Mushroom Kingdom II",
          "Flat Zone", "Dream Land", "Battlefield", "Final Destination"]


# ------------------------------------------------------------------ 01 title
def s01(wide=False):
    rose = ('<svg style="position:absolute;left:50%;top:44%;width:560px;height:560px;transform:translate(-50%,-50%)" viewBox="-100 -100 200 200" fill="none" stroke="#2a3346" stroke-width=".6">'
            '<path d="M0-96L96 0 0 96-96 0z"/><path d="M0-70L70 0 0 70-70 0z"/><path d="M0-44L44 0 0 44-44 0z"/>'
            '<path d="M0-100V100M-100 0H100" stroke="#232b3c"/><path d="M-68-68L68 68M68-68L-68 68" stroke="#1f2636"/>'
            '<path d="M0-100l5 14h-10zM100 0l-14 5v-10zM0 100l-5-14h10zM-100 0l14-5v10z" fill="#2a3346" stroke="none"/></svg>')
    body = (
        rose +
        '<div style="position:absolute;left:0;right:0;top:128px;display:flex;flex-direction:column;align-items:center">'
        '<svg style="width:54px;height:54px" viewBox="0 0 24 24"><use href="#i-mark"/></svg>'
        '<div class="cap" style="font-weight:700;font-size:78px;line-height:.95;letter-spacing:.07em;margin-top:10px;color:var(--ivory)">GD&rsquo;S MELEE</div>'
        '<div style="display:flex;align-items:center;gap:12px;margin-top:8px"><span style="width:70px;height:2px;background:var(--ember)"></span>'
        '<span class="cap" style="font-size:18px;letter-spacing:.34em;color:var(--muted)">PC PORT</span><span style="width:70px;height:2px;background:var(--ember)"></span></div>'
        '</div>'
        '<div style="position:absolute;left:0;right:0;top:330px;display:flex;justify-content:center">'
        '<span class="btn big focus" style="gap:12px">@START@ PRESS START</span></div>'
        '<div style="position:absolute;left:32px;bottom:24px;font-size:13px;color:var(--muted)" class="num">v0.1.7</div>'
        '<div style="position:absolute;right:32px;bottom:24px;font-size:13px;color:var(--dim)">Original menu art</div>'
    ).replace("@START@", kg("START"))
    p = page([], "", [], chap=None, wide=wide, head_extra="<style>.hdr,.hdr-rule,.body,.foot{display:none}</style>", title="01 title")
    return p.replace('<div class="hdr">', body + '<div class="hdr">', 1)


# ------------------------------------------------------------------ 02 main menu
def s02(wide=False):
    items = [("I", "Solo", "solo"), ("II", "Versus", "versus"), ("III", "Online", "online"), ("IV", "Mods", "mods"), ("V", "Settings", "settings")]
    rows = []
    for k, (n, lab, ico) in enumerate(items):
        st = "focus" if lab == "Versus" else ""
        rows.append('<div class="row xl %s" style="height:56px;gap:14px"><span class="tab" style="height:30px;padding:0;width:30px;justify-content:center;background:%s;color:%s;border:0;font-size:17px;font-weight:700;clip-path:polygon(0 0,calc(100%% - 6px) 0,100%% 6px,100%% 100%%,0 100%%)">%s</span>'
                    '<span class="cap lbl" style="font-size:30px;font-weight:700;letter-spacing:.06em">%s</span>%s</div>'
                    % (st, "var(--ember)" if st else "var(--ground)", "var(--ink)" if st else "var(--muted)", n, lab, ic("right", "sm") if st else ""))
    rows.append('<div class="row" style="height:34px;margin-top:6px;background:none;box-shadow:inset 0 0 0 1px var(--line);border-bottom:0;color:var(--muted)">%s<span class="lbl">More</span><span class="val" style="font-family:var(--f-ui)">Collection, Data, Credits</span></div>' % ic("more", "sm"))
    left = '<div class="col" style="width:%dpx"><div class="list" style="gap:6px">%s</div></div>' % (310 if not wide else 340, "".join(rows))
    inside = "".join(tag(x, "line") for x in ["Melee", "Tournament", "Special Melee", "Rules", "Name Entry"])
    det = detail("Versus", "Up to four players. Your rules, your stage.",
                 rows=[("Inside", '<span style="display:flex;gap:4px;flex-wrap:wrap">%s</span>' % inside), ("Players", "1 to 4")],
                 media='<div style="position:relative;width:100%%;height:100%%;display:grid;place-items:center;color:var(--ember)"><span class="cap" style="position:absolute;right:14px;bottom:-14px;font-size:110px;font-weight:700;color:#1d2330;line-height:1">II</span><span style="position:relative">%s</span></div>' % ic("versus", "xl"),
                 kick="Chapter II", more="Preview")
    right = '<div class="col fill">%s</div>' % pane(det, "fill")
    return page(["Main"], '<div class="col fill" style="flex-direction:row;gap:12px">%s%s</div>' % (left, right),
                [("dpad", "Move"), ("A", "Open"), ("B", "Title"), ("Y", "Preview")], chap=1, wide=wide, pos="2 / 5", title="02 main menu",
                status='<span class="tag line">GD</span>')


# ------------------------------------------------------------------ 03 solo hub
def s03(wide=False):
    modes = [("Classic", "classic", "Retail"), ("Adventure", "adventure", "Retail"), ("All-Star", "allstar", "Retail"), ("Event", "event", "Retail"),
             ("Stadium", "stadium", "Retail"), ("Training", "training", "Retail"), ("LAB", "lab", "Mod"), ("Envoy", "envoy", "Mod")]
    tiles = []
    for lab, ico, org in modes:
        st = "focus" if lab == "Envoy" else ""
        tiles.append('<div class="row xl %s" style="height:62px;gap:10px;padding:0 10px"><span style="color:%s">%s</span><span class="lbl"><span class="cap" style="font-size:21px;font-weight:700;letter-spacing:.05em">%s</span></span>%s</div>'
                     % (st, "var(--ember)" if st else "var(--muted)", ic(ico, "lg"), lab, tag("Mod", "jade") if org == "Mod" else ""))
    grid = '<div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:6px 8px;width:100%%">%s</div>' % "".join(tiles)
    media = '<div style="display:flex;gap:2px;align-items:center;height:96px;width:100%%;justify-content:center">%s</div>' % "".join(
        '<div style="width:62px;height:62px;position:relative">%s</div>' % drv(f) for f in ["red", "blue", "purple"])
    det = detail("Envoy", "Explore, fight and evolve your build.",
                 rows=[("Players", "1, or 2 in co-op"), ("With", tag("Drives", "line") + tag("Keystones", "line")), ("From", tag("Mod", "jade") + '<span>Supertime Envoy</span>')],
                 media=media, kick="Solo mode", more="Best runs")
    return page(["Main", "Solo"], '<div class="col fill" style="flex:1.25">%s</div><div class="col" style="flex:.8">%s</div>' % (grid, pane(det, "fill")),
                [("dpad", "Move"), ("A", "Open"), ("B", "Back"), ("Y", "Best runs")], chap=0, wide=wide, pos="8 / 8", title="03 solo hub")


# ------------------------------------------------------------------ 04 character select
def _grid_cells(focus_name, ports, cols=8):
    cells = []
    allf = [(n, None) for n in RETAIL] + ADDED
    for n, o in allf:
        st = "focus" if n == focus_name else ""
        cells.append(fighter_cell(n, st, org=o, port=ports.get(n), w=38, h=46, bk="var(--p1)" if n == focus_name else None))
    return '<div style="display:grid;grid-template-columns:repeat(%d,38px);gap:8px 5px;justify-content:start">%s</div>' % (cols, "".join(cells))


def s04(wide=False):
    grid = _grid_cells("Sora", {"Fox": "cpu", "Sora": 1}, 12 if wide else 8)
    # port tray
    def pc(cls, n, t1, t2, ini=None):
        face = '<div class="cw" style="--cw:34px;--ch2:34px"><div class="cell"><div class="disc"><span class="ini" style="font-size:13px">%s</span></div></div></div>' % ini if ini else ""
        return '<div class="pcard %s">%s%s<div style="min-width:0"><div class="t1">%s</div><div class="t2">%s</div></div></div>' % (cls, pt(n), face, t1, t2)
    tray = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">%s%s%s%s</div>' % (
        pc("p1", 1, "Sora", "Costume 1", "SO"),
        pc("cpu", "cpu", "Fox", "Level 3", "FO"),
        '<div class="pcard p3 empty">%s<div><div class="t1" style="color:var(--muted)">Open</div><div class="t2">Press %s to join</div></div></div>' % (pt(3), kg("A")),
        '<div class="pcard p4 closed">%s<div><div class="t1" style="color:var(--dim)">Closed</div><div class="t2" style="color:var(--dim)">Hold %s to open</div></div></div>' % (pt(4), kg("X")))
    # the retail grid keeps the page it was on; the legend answers "what are those hatched squares"
    legend = '<div style="display:flex;gap:14px;align-items:center;margin-top:10px;font-size:13px;color:var(--muted)"><span style="display:flex;align-items:center;gap:6px"><span class="org add" style="width:14px;height:14px;display:inline-grid;place-items:center;background:var(--sun);color:var(--ink);font-family:var(--f-cap);font-weight:700;font-size:12px">+</span>Added</span><span style="display:flex;align-items:center;gap:6px"><span style="width:14px;height:14px;display:inline-grid;place-items:center;background:var(--jade);color:var(--ink);font-family:var(--f-cap);font-weight:700;font-size:12px">G</span>Geno</span><span style="margin-left:auto" class="dim">Hatched = disc art</span></div>'
    left = '<div class="col" style="flex:1">%s%s</div>' % (
        tabs([("All", "29", "on"), ("Retail", "26", ""), ("Added", "3", "")]), pane(grid + legend, "fill", style="padding-top:14px"))
    portrait = ('<div style="width:62px;height:86px;position:relative"><div class="cell" style="position:absolute;inset:0;border-bottom-width:3px"><div class="disc"><span class="ini" style="font-size:22px">SO</span><span class="lab">disc art</span></div></div></div>')
    det = detail("Sora", "Geno fighter. Its moves are defined in the mod.",
                 rows=[("Costume", choice("1 / [N]")), ("From", tag("Geno", "jade"))],
                 media=portrait, kick="Fighter", mh=104)
    right = '<div class="col" style="width:196px">%s</div>' % pane(det, "fill")
    top = '<div style="display:flex;gap:12px;flex:1;min-height:0">%s%s</div>' % (left, right)
    return page(["Versus", "Melee", "Fighters"], '<div class="col fill">%s%s</div>' % (top, tray),
                [("dpad", "Move"), ("A", "Pick"), ("B", "Back"), ("X", "Costume"), ("Y", "Details"), ("S", "Fight")], chap=1, wide=wide,
                pos="29 / 29", title="04 character select")


# ------------------------------------------------------------------ 05 stage select
def s05(wide=False):
    cells = []
    shown = ["Peach's Castle", "Yoshi's Story", "Fountain of Dreams", "Pokemon Stadium", "Dream Land", "Battlefield", "Final Destination",
             "Kongo Jungle", "Great Bay", "Temple", "Brinstar", "Corneria", "Mute City", "Big Blue", "Onett", "Fourside", "Icicle Mountain", "Flat Zone"]
    legal = {"Battlefield", "Final Destination", "Yoshi's Story", "Fountain of Dreams", "Pokemon Stadium", "Dream Land"}
    for n in shown:
        st = "focus" if n == "Battlefield" else ""
        o = '<span class="org" style="background:var(--jade)">%s</span>' % "L" if n in legal else ""
        cells.append(_cw('<div class="cell"><div class="disc"><span class="ini">%s</span></div>%s<span class="nm">%s</span></div>' % (initials(n), o, esc(n)), st, 78, 58,
                         bk="var(--p1)" if st else None))
    cells.append(_cw('<div class="cell"><div class="disc" style="background:var(--plate2)"><span class="ini" style="color:var(--text2);font-size:22px">?</span></div><span class="nm">Random</span></div>', "", 74, 52))
    grid = '<div style="display:grid;grid-template-columns:repeat(4,78px);gap:8px 6px;justify-content:start">%s</div>' % "".join(cells[:16])
    left = '<div class="col" style="flex:1">%s%s</div>' % (
        tabs([("Tournament", "6", "on"), ("All", "29", ""), ("Added", "[N]", "")]),
        pane(grid, "fill", style="padding-top:14px"))
    prev = '<div style="width:176px;height:99px;position:relative"><div class="cell" style="position:absolute;inset:0"><div class="disc"><span class="ini" style="font-size:22px">BA</span><span class="lab">disc art</span></div></div></div>'
    det = detail("Battlefield", "Three floating platforms over a flat main stage.",
                 rows=[("List", tag("Tournament", "jade")), ("From", "Retail")], media=prev, kick="Stage", more="Hazards and blast zones", mclass="")
    right = '<div class="col" style="width:200px">%s</div>' % pane(det, "fill")
    who = ('<div class="pane quiet" style="padding:6px 10px;display:flex;align-items:center;gap:10px;height:40px"><span class="cap muted" style="font-size:13px">Fighting</span>%s<b style="font-weight:700">Sora</b><span class="dim">vs</span>%s<b style="font-weight:700">Fox</b>'
           '<span style="margin-left:auto;display:flex;align-items:center;gap:8px" class="muted">Picks: %s<b style="color:var(--ivory)">P1</b></span></div>') % (pt(1), pt("cpu"), pt(1))
    top = '<div style="display:flex;gap:12px;flex:1;min-height:0">%s%s</div>' % (left, right)
    return page(["Versus", "Melee", "Stage"], '<div class="col fill">%s%s</div>' % (top, who),
                [("dpad", "Move"), ("A", "Pick"), ("B", "Back"), ("L", "Page"), ("Y", "Details")], chap=1, wide=wide, pos="Battlefield 26 / 29", title="05 stage select")


# ------------------------------------------------------------------ 06 versus rules
def s06(wide=False):
    r = []
    r.append(group("Match"))
    r.append(row("Stocks", slider(3, 20, "4"), "flag"))
    r.append(row("Time limit", choice("8:00", 60), "clock"))
    r.append(row("Items", choice("Off", 60), "star"))
    r.append(row("Teams", tog(False), "people"))
    r.append(group("Pace"))
    r.append(row("Turbo", tog(True), "bolt", state="focus"))
    r.append(row("Damage ratio", stepper("1.0x"), "up"))
    left = '<div class="col fill"><div class="list" style="gap:5px">%s</div></div>' % "".join(r)
    normal = "".join('<i class="f"></i>' for _ in range(14))
    turbo = "".join('<i class="f"></i>' for _ in range(20))
    media = ('<div style="width:100%%;padding:0 6px"><div class="cap muted" style="font-size:13px;margin-bottom:3px">Normal</div><div class="bar" style="width:70%%">%s</div>'
             '<div class="cap ember" style="font-size:13px;margin:8px 0 3px">Turbo</div><div class="bar" style="width:100%%">%s</div></div>') % (normal, turbo)
    det = detail("Turbo", "Everyone plays faster. In a room the host decides for both players.",
                 rows=[("With", tag("Offline", "line") + tag("Rooms", "line") + tag("Envoy", "line")), ("Speed", '<span class="num">x[SPEED]</span>'), ("From", "Match rule")],
                 media=media, kick="Pace", more="Netplay notes")
    return page(["Versus", "Melee", "Rules"], '<div class="col" style="flex:1.12">%s</div><div class="col" style="flex:.88">%s</div>' % (left, pane(det, "fill")),
                [("dpad", "Move"), ("dpad", "Change"), ("A", "Fight"), ("B", "Back"), ("Y", "Notes")], chap=1, wide=wide, pos="6 / 8", title="06 versus rules")


# ------------------------------------------------------------------ 07 online room
def s07(wide=False):
    code = ('<div class="pane" style="padding:10px 14px"><div class="cap muted" style="font-size:13px">Room code</div>'
            '<div class="cap" style="font-size:36px;font-weight:700;letter-spacing:.12em;line-height:1.05;white-space:nowrap">[ROOM CODE]</div>'
            '<div style="display:flex;align-items:center;margin-top:8px"><span class="muted" style="font-size:13px">Share it to invite a friend.</span><span style="margin-left:auto">%s</span></div></div>' % btn("Copy", "", kgl="X").replace('class="btn', 'style="height:28px;padding:0 12px;font-size:15px" class="btn', 1))

    def player(n, name, fighter, ready, q, mid=False):
        rd_ = tag("Ready", "jade") if ready else tag("Choosing", "sun")
        return ('<div class="pcard p%d" style="height:58px;gap:10px">%s<div style="flex:1;min-width:0"><div class="t1" style="font-size:20px">%s</div><div class="t2">%s</div></div>'
                '<div style="display:flex;align-items:center;gap:8px">%s%s</div></div>') % (n, pt(n, "lg"), name, fighter, rd_, sig(q, mid))
    players = '<div class="col" style="gap:8px">%s%s</div>' % (player(1, "GD", "Sora, host", True, 4), player(2, "[Guest name]", "Fox", False, 3, True))
    link = ('<div class="pane quiet" style="padding:8px 12px;display:flex;align-items:center;gap:10px">%s<span style="font-size:14px"><b style="font-weight:700">Connection is good.</b> <span class="muted">[PING] ms, input delay [N] frames.</span></span></div>' % ic("online", ""))
    acts = '<div style="display:flex;gap:8px;margin-top:auto">%s%s</div>' % (btn("Ready", "focus", "big", kgl="A").replace('class="btn focus big"', 'class="btn focus big" style="flex:1"'), btn("Leave", "", "big", kgl="B"))
    left = '<div class="col" style="flex:1.1">%s%s%s%s</div>' % (code, players, link, acts)
    rules = [row("Stages", choice("Tournament"), "map"), row("Stocks", stepper("4"), "flag"), row("Time limit", choice("8:00"), "clock"),
             row("Turbo", tog(True), "bolt", state="focus"), row("Envoy", choice("Off"), "envoy")]
    right = '<div class="col" style="flex:1">%s<div style="margin-top:auto">%s</div></div>' % (
        pane('<div class="list" style="gap:5px">%s</div>' % "".join(rules), "", head="Room rules", headr="Host sets"),
        note("The guest is choosing a fighter.", "info", "clock", 40))
    return page(["Online", "Room"], left + right, [("dpad", "Move"), ("A", "Ready"), ("B", "Leave"), ("X", "Copy code")], chap=2, wide=wide,
                status='<span style="display:flex;align-items:center;gap:6px">%s<span>Server reachable</span></span>' % sig(4), title="07 online room")


# ------------------------------------------------------------------ 08 envoy run setup
def s08(wide=False):
    def step(n, title, inner, focus=False):
        return ('<div class="pane" style="padding:8px 12px 10px;%s"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px"><span class="pt" style="--c:%s;background:%s;color:var(--ink);clip-path:none;width:20px;height:20px;font-size:14px">%d</span>'
                '<span class="cap" style="font-size:16px;letter-spacing:.14em;color:%s">%s</span></div>%s</div>') % (
            "box-shadow:inset 3px 0 0 var(--ember);" if focus else "", "var(--ember)", "var(--ember)" if focus else "var(--line2)", n, "var(--ivory)" if focus else "var(--muted)", title, inner)
    two = lambda a, b, sa, sb: '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">%s%s</div>' % (
        '<div class="row tall %s">%s<span class="lbl">%s</span></div>' % (sa, ic("check", "sm") if "sel" in sa else "", a),
        '<div class="row tall %s">%s<span class="lbl">%s</span></div>' % (sb, ic("check", "sm") if "sel" in sb else "", b))
    s1 = step(1, "Mode", two("Classic", "Adventure", "", "sel focus"), True)
    fighter = ('<div style="display:flex;align-items:center;gap:10px"><div class="cw" style="--cw:44px;--ch2:40px"><div class="cell"><div class="disc"><span class="ini">SO</span></div><span class="org">G</span></div></div>'
               '<div class="row tall" style="flex:1"><span class="lbl">%s</span>%s</div></div>') % ("Sora", choice("Costume 1", 80))
    s2 = step(2, "Fighter", fighter)
    s3 = step(3, "Players", two("Solo", "Co-op", "sel", ""))
    go = '<div style="display:flex;gap:8px">%s%s</div>' % (btn("Start run", "", "big", kgl="S").replace('class="btn', 'style="flex:1" class="btn', 1), "")
    left = '<div class="col" style="flex:1.1;gap:8px">%s%s%s%s</div>' % (s1, s2, s3, go)
    # detail follows the focused step: Adventure
    slots = ('<div style="display:flex;gap:6px">%s</div>') % "".join(
        empty_cell(36, 36, label=str(i + 1)) if i < 4 else lock_cell(36, 36, label=str(i + 1)) for i in range(6))
    bag = '<div style="display:flex;gap:5px">%s</div>' % "".join(empty_cell(36, 36) for _ in range(4))
    cap = lambda t: '<div class="cap muted" style="font-size:12px;margin-bottom:4px">%s</div>' % t
    well = '<div style="padding:0 10px;width:100%%">%s%s<div style="height:8px"></div>%s%s</div>' % (cap("Slots: four open, two locked"), slots, cap("Bag: four cells"), bag)
    det = detail("Adventure", "Side-scrolling stages between the battles.",
                 rows=[("Opens", '<span class="muted">Fifth slot at depth [N]</span>')],
                 media=well, mh=124, kick="Run type", more="How a run works")
    right = '<div class="col" style="flex:.9">%s</div>' % pane(det, "fill")
    return page(["Solo", "Envoy", "Run setup"], left + right, [("dpad", "Move"), ("A", "Choose"), ("B", "Back"), ("S", "Start"), ("Y", "How it works")],
                chap=0, wide=wide, pos="Step 1 / 3", title="08 envoy run setup")
