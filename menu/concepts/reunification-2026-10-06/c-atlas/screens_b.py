"""Screens 09-17: the Envoy build screens, the in-match layer, results, settings, mods, the LAB, the launcher."""
from parts import *
from parts import _cw
from screens_a import RETAIL

# real pieces and their real one-line rules (APPENDIX-pieces.md). The family colour is assigned by the drive README's meanings
# (red damage, green speed, blue defence, yellow air, purple status, white wild): the appendix has no family field for drives.
P = {
    "Kindling": ("purple", "Your hits set the target Burning for 3 s.", "Depth 0"),
    "Keen": ("red", "Your hits crit 5% of the time.", "Depth 4"),
    "Reprisal": ("blue", "Perfect shield: Guarded for 3 s.", "Depth 0"),
    "Ledge": ("green", "Grab a ledge: Haste for 3 s.", "Depth 0"),
    "Updraft": ("yellow", "Aerial hits add 1 Momentum (up to 5) for 5 s.", "Depth 0"),
    "Cinder": ("purple", "Your hits deal 10% more damage to Burning targets.", "Depth 5"),
    "Pyre": ("purple", "Your hits launch Burning targets 8% farther.", "Depth 5"),
    "Echoes": ("yellow", "Aerial attacks repeat once, weaker.", "Depth 0"),
    "Tech": ("blue", "Tech: Guarded for 1 s.", "Depth 5"),
    "Echo Heart": ("white", "Every attack repeats a moment later at reduced damage.", "Unique"),
}


def mini(name, w=26, ring=None, state=""):
    fam = P[name][0]
    return '<div class="cw %s" style="--cw:%dpx;--ch2:%dpx"><div class="cell drv">%s</div></div>' % (state, w, w, drv(fam, ring))


def pips_stock(n, tot=3):
    return '<span style="display:inline-flex;gap:3px">%s</span>' % "".join(
        '<i style="width:9px;height:9px;background:%s;clip-path:polygon(50%% 0,100%% 50%%,50%% 100%%,0 50%%)"></i>' % ("var(--ivory)" if i < n else "#333b4d") for i in range(tot))


# ------------------------------------------------------------------ 09 bag
def s09(wide=False):
    cw = 56
    eq = [drive_cell("purple", None, "", cw, cw, plus=True, ix=1), drive_cell("red", None, "", cw, cw, ix=2), drive_cell("blue", None, "", cw, cw, ix=3),
          drive_cell("green", None, "", cw, cw, ix=4), drive_cell("yellow", None, "", cw, cw, ix=5), lock_cell(cw, cw, label="6")]
    bag = [drive_cell("purple", None, "focus", cw, cw, bk="var(--ember)"), drive_cell("purple", None, "", cw, cw), drive_cell("white", "unique", "", cw, cw),
           empty_cell(cw, cw)]
    row_ = lambda cells: '<div style="display:flex;gap:6px">%s</div>' % "".join(cells)
    ks = '<div style="display:flex;gap:8px;align-items:center">%s%s%s<span class="muted" style="margin-left:6px;font-size:13px">One held</span></div>' % (
        stone("P", "red"), stone("", "", "empty"), stone("", "", "lock"))
    lab = lambda t, r="": '<div class="ph"%s>%s%s</div>' % ("", esc(t), '<span class="r">%s</span>' % r if r else "")
    left_inner = ('%s%s<div style="height:14px"></div>%s%s<div style="height:14px"></div>%s%s') % (
        lab("Equipped", "5 / 6"), row_(eq), lab("Bag", "3 / 4"), row_(bag), lab("Keystone"), ks)
    # detail: Kindling in the bag, merge target slot 1
    media = '<div style="width:88px;height:88px;position:relative">%s</div>' % drv("purple")
    merge = ('<div style="margin-top:auto;background:var(--ground2);padding:8px 10px;display:flex;align-items:center;gap:8px"><span class="cap muted" style="font-size:13px;letter-spacing:.14em;width:50px">If you merge</span>%s<span class="cap muted" style="font-size:14px">+</span>%s'
             '<span class="cap" style="font-size:14px;color:var(--jade)">&rarr;</span>%s<span style="font-size:13px;margin-left:6px;color:var(--text2)">Slot 1 Kindling<br>gets stronger.</span></div>') % (
        mini("Kindling", 34), mini("Kindling", 34, state="merge"), '<div class="cw" style="--cw:34px;--ch2:34px"><div class="cell drv">%s</div></div>' % drv("purple", "magic"))
    left_inner = left_inner + merge
    left = '<div class="col" style="width:%dpx"><div class="pane fill" style="display:flex;flex-direction:column">%s</div></div>' % (404 if not wide else 440, left_inner)
    det = detail("Kindling", P["Kindling"][1],
                 rows=[("With", '<span style="display:flex;gap:4px;align-items:center">%s</span>' % (mini("Cinder", 24) + mini("Pyre", 24))),
                       ("From", "Depth 0, Fire")],
                 media=media, kick="Bag cell 1", mh=104)
    right = '<div class="col fill">%s</div>' % pane(det, "fill")
    return page(["Solo", "Envoy", "Your drives"], left + right,
                [("dpad", "Move"), ("A", "Merge into slot 1"), ("X", "Discard"), ("Y", "More"), ("B", "Close")], chap=0, wide=wide, pos="Bag 1 / 4", title="09 envoy bag")


# ------------------------------------------------------------------ 10 reward
def s10(wide=False):
    def offer(name, state="", ribbon=""):
        fam = P[name][0]
        r = '<div style="position:absolute;left:0;right:0;top:0;height:20px;background:var(--jade);color:var(--ink);display:flex;align-items:center;justify-content:center;gap:5px;font-family:var(--f-cap);font-weight:700;font-size:14px;letter-spacing:.12em;z-index:4">%s%s</div>' % (ic("check", "sm"), ribbon) if ribbon else ""
        return ('<div class="cw %s" style="--cw:176px;--ch2:150px;--bk:var(--ember)"><div class="cell drv nosh" style="background:%s">%s'
                '<div style="position:absolute;left:0;right:0;top:%dpx;display:grid;place-items:center"><div style="width:84px;height:84px;position:relative">%s</div></div>'
                '<div class="cap" style="position:absolute;left:0;right:0;bottom:8px;text-align:center;font-size:22px;font-weight:700;letter-spacing:.06em">%s</div></div><b class="brk"></b></div>') % (
            state, "var(--lift)" if state == "focus" else "var(--ground2)", r, 34 if ribbon else 20, drv(fam), name)
    offers = '<div style="display:flex;gap:12px;justify-content:center">%s%s%s</div>' % (offer("Cinder", "focus", "COMPLETES FIRE"), offer("Echoes"), offer("Tech"))
    strip = ('<div class="pane" style="padding:8px 12px;display:flex;align-items:center;gap:12px"><div style="flex:1;min-width:0"><span class="cap" style="font-size:20px;font-weight:700;letter-spacing:.06em">Cinder</span>'
             '<div style="font-size:15px;margin-top:2px">%s</div></div><div style="display:flex;gap:6px;align-items:center">%s%s</div></div>') % (
        P["Cinder"][1], tag("Fire 3 / 3", "jade"), tag("Depth 5", "line"))
    bsl = [mini("Kindling", 32), mini("Keen", 32), mini("Reprisal", 32), mini("Ledge", 32),
           '<div class="cw merge" style="--cw:32px;--ch2:32px"><div class="cell empty" style="box-shadow:inset 0 0 0 2px var(--jade);color:var(--jade)">%s</div></div>' % ic("plus", "sm"), lock_cell(32, 32)]
    bbag = [empty_cell(32, 32) for _ in range(4)]
    cap = lambda t: '<span class="cap muted" style="font-size:13px;letter-spacing:.14em">%s</span>' % t
    build = ('<div class="pane quiet" style="padding:8px 12px;display:flex;align-items:center;gap:8px">%s<div style="display:flex;gap:4px">%s</div>'
             '<span style="width:1px;height:26px;background:var(--line);margin:0 6px"></span>%s<div style="display:flex;gap:4px">%s</div><span style="margin-left:auto" class="jade">Goes into slot 5</span></div>') % (
        cap("Equipped"), "".join(bsl), cap("Bag"), "".join(bbag))
    top = ('<div style="display:flex;align-items:center;gap:12px"><div style="flex:1">%s</div><div style="display:flex;align-items:center;gap:8px;width:196px">%s<div style="flex:1">%s</div><span class="num" style="font-size:13px">[45 s]</span></div></div>') % (
        note("<b>Unlocked: fifth slot</b>", "", "star", 100), cap("Take one"), bar(15, 22))
    return page(["Solo", "Envoy", "Reward"], '<div class="col fill" style="gap:10px">%s%s%s%s</div>' % (top, offers, strip, build),
                [("dpad", "Move"), ("A", "Take"), ("X", "To bag"), ("Y", "More"), ("B", "Skip")], chap=0, wide=wide, pos="Stage 3 clear", title="10 envoy reward")


# ------------------------------------------------------------------ the match layer (11, 12, 16)
def scene():
    plat = lambda l, t, w_, h, c: '<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;background:%s"></div>' % (l, t, w_, h, c)
    fighter = lambda x, y, c, tok: ('<div style="position:absolute;left:%dpx;top:%dpx;width:26px;height:56px"><div style="position:absolute;left:5px;top:0;width:16px;height:16px;background:%s;clip-path:circle(50%%)"></div>'
                                     '<div style="position:absolute;left:0;top:18px;width:26px;height:38px;background:%s;clip-path:polygon(15%% 0,85%% 0,100%% 100%%,0 100%%)"></div>'
                                     '<div style="position:absolute;left:-2px;top:-26px">%s</div></div>') % (x, y, c, c, tok)
    s = ('<div style="position:absolute;inset:0;background:#0e141f"></div>' + plat(0, 250, 640, 230, "#111826") + plat(0, 360, 640, 120, "#141c2b") +
         plat(120, 330, 400, 22, "#2a3347") + plat(120, 330, 400, 4, "#3a455e") + plat(120, 352, 400, 40, "#1c2434") +
         plat(160, 262, 110, 6, "#2a3347") + plat(370, 262, 110, 6, "#2a3347") + plat(265, 196, 110, 6, "#2a3347") +
         fighter(246, 274, "#46526b", pt(1)) + fighter(396, 274, "#46526b", pt("cpu")))
    # two floor drives under their glass shells, and the arrow that points at the nearer one
    s += ('<div style="position:absolute;left:316px;top:288px;width:38px;height:38px">%s</div><div style="position:absolute;left:176px;top:288px;width:38px;height:38px">%s</div>'
          '<div style="position:absolute;left:326px;top:262px;width:0;height:0;border-left:9px solid transparent;border-right:9px solid transparent;border-top:12px solid var(--ember)"></div>') % (
        '<svg viewBox="-2.45 -2.45 4.9 4.9" style="width:100%;height:100%"><use href="#drv-blue"/></svg>', '<svg viewBox="-2.45 -2.45 4.9 4.9" style="width:100%;height:100%"><use href="#drv-green"/></svg>')
    return s


HUD_PLATE = "background:rgba(20,25,35,.84);border-bottom:3px solid rgba(6,8,11,.9);"


def hud_layer():
    build = ('<div style="position:absolute;left:32px;top:24px;display:flex;gap:4px;align-items:center;padding:5px;%s">%s<span style="width:2px;height:22px;background:var(--line);margin:0 3px"></span>%s</div>') % (
        HUD_PLATE, "".join([mini("Kindling", 28), mini("Keen", 28), mini("Reprisal", 28), mini("Ledge", 28), mini("Updraft", 28), lock_cell(28, 28)]), stone("P", "red", "").replace('class="stone ', 'class="stone sm '))
    banner = ('<div style="position:absolute;left:0;right:0;top:92px;display:flex;justify-content:center"><div class="cap" style="display:flex;gap:8px;align-items:center;padding:4px 14px;font-size:17px;font-weight:600;letter-spacing:.14em;%s">%s Collect the drives</div></div>') % (
        HUD_PLATE, '<span style="color:var(--ember)">%s</span>' % ic("down", "sm"))
    opp = ('<div style="position:absolute;right:32px;top:24px;width:184px;padding:6px 8px;%s;display:flex;flex-direction:column;gap:5px">'
           '<div style="display:flex;align-items:center;gap:8px">%s<span class="cap" style="font-size:17px;font-weight:700;letter-spacing:.06em;flex:1">Fox</span><span class="num" style="font-size:18px">23%%</span></div>'
           '<div style="display:flex;align-items:center;gap:6px">%s<span style="margin-left:auto;display:flex;align-items:center;gap:5px;font-size:12px;color:var(--muted);white-space:nowrap">%s Damage resistant</span></div></div>') % (
        HUD_PLATE, pt("cpu"), pips_stock(3), mini("Pyre", 18))
    me = ('<div style="position:absolute;left:32px;bottom:26px;display:flex;align-items:center;gap:10px;padding:8px 14px 8px 10px;border-top:3px solid var(--p1);%s">%s<div><div class="cap" style="font-size:16px;font-weight:700;letter-spacing:.08em;line-height:1">Sora</div><div style="margin-top:5px">%s</div></div>'
          '<div class="num" style="font-size:44px;line-height:1;font-weight:700;margin-left:6px">87<span style="font-size:20px">%%</span></div></div>') % (HUD_PLATE, pt(1, "lg"), pips_stock(3))
    nt = '<div style="position:absolute;right:32px;bottom:26px">%s</div>' % note("<b>Merged!</b> Kindling got stronger.", "", "plus", 70)
    return build + banner + opp + me + nt


def _matchpage(inner, title, hints=()):
    p = page([], "", [], head_extra="<style>.hdr,.hdr-rule,.body,.foot{display:none}</style>", ground=False, title=title)
    return p.replace('<div class="hdr">', inner + '<div class="hdr">', 1)


def s11(wide=False):
    return _matchpage(scene() + hud_layer(), "11 envoy hud")


def s12(wide=False):
    rows = [row("Resume", "", "right", "focus"), row("Bag", '<span class="num">5 / 6</span>', "mods"), row("Controls", "", "pad"), row("Quit run", "", "x")]
    dlg = ('<div style="position:absolute;left:50%%;top:50%%;transform:translate(-50%%,-50%%);width:300px">'
           '<div class="pane" style="padding:12px 14px 14px"><div class="ph" style="margin-bottom:10px"><span style="font-size:18px;color:var(--ivory)">Paused</span></div>'
           '<div class="list" style="gap:5px">%s</div><div style="margin-top:12px;display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)">%s<span>Adventure, stage 3 of [N]</span></div></div>'
           '<div style="display:flex;gap:18px;justify-content:center;margin-top:12px">%s%s%s</div></div>') % ("".join(rows), ic("envoy", "sm"), hint("A", "Select"), hint("B", "Resume"), hint("Z", "Bag"))
    return _matchpage(scene() + hud_layer() + '<div class="scrim"></div>' + dlg, "12 pause")


def s12b(wide=False):
    dlg = ('<div style="position:absolute;left:50%%;top:50%%;transform:translate(-50%%,-50%%);width:420px">'
           '<div class="pane" style="padding:14px 16px 16px;border-top:4px solid var(--jade)">'
           '<div class="kick cap jade" style="font-size:14px">Stage 3</div><div class="cap" style="font-size:44px;font-weight:700;line-height:1;letter-spacing:.06em">Stage clear</div>'
           '<div style="display:flex;gap:18px;margin:12px 0 10px;font-size:14px;color:var(--text2)"><span><span class="cap dim" style="font-size:12px">Time</span><br><span class="num">[CLEAR TIME]</span></span><span><span class="cap dim" style="font-size:12px">KOs</span><br><span class="num">[N]</span></span><span><span class="cap dim" style="font-size:12px">Drives picked up</span><br><span class="num">[N]</span></span></div>'
           '<div class="sep-line" style="margin:10px 0"></div>'
           '<div style="display:flex;align-items:center;gap:10px">%s<div style="white-space:nowrap"><div style="font-size:15px"><b>Choose one of three drives.</b></div><div class="jade" style="font-size:14px;margin-top:2px">Unlocked: fifth slot</div></div></div>'
           '<div style="margin-top:14px;display:flex;justify-content:flex-end">%s</div></div></div>') % (
        '<div style="display:flex;gap:2px">%s</div>' % "".join(mini(n, 34) for n in ("Cinder", "Echoes", "Tech")), btn("Reward", "focus", kgl="A"))
    return _matchpage(scene() + '<div class="scrim" style="background:rgba(5,7,10,.55)"></div>' + dlg, "12b payout")


# ------------------------------------------------------------------ 13 results
def s13(wide=False):
    def res(place, n, fighter, name, kos, falls, dealt, win=False):
        c = "p%d" % n if n != "cpu" else "cpu"
        stats = "".join('<div style="text-align:right;width:62px"><div class="cap dim" style="font-size:12px;line-height:1">%s</div><div class="num" style="font-size:20px">%s</div></div>' % (l, v) for l, v in (("KOs", kos), ("Falls", falls), ("Dealt", dealt)))
        return ('<div class="pcard %s" style="height:84px;gap:14px;padding:8px 14px"><span class="cap" style="font-size:34px;font-weight:700;width:34px;color:%s">%d</span>%s'
                '<div class="cw" style="--cw:46px;--ch2:46px"><div class="cell"><div class="disc"><span class="ini">%s</span></div></div></div>'
                '<div style="flex:1;min-width:0"><div class="t1" style="font-size:22px">%s</div><div class="t2">%s</div></div>%s</div>') % (
            c, "var(--ember)" if win else "var(--muted)", place, pt(n, "lg"), initials(fighter), fighter, name, stats)
    banner = ('<div class="pane" style="padding:18px 20px;display:flex;align-items:center;gap:14px;border-top:4px solid var(--ember)"><div><div class="cap muted" style="font-size:14px">Winner</div>'
              '<div class="cap" style="font-size:52px;font-weight:700;line-height:1;letter-spacing:.05em">Sora</div></div><div style="margin-left:auto;text-align:right"><div class="cap muted" style="font-size:14px">Battlefield</div><div style="font-size:18px">Stock match, 4 stocks</div></div></div>')
    rows = '<div class="col" style="gap:8px">%s%s</div>' % (res(1, 1, "Sora", "Player 1", 4, 1, "[N]%", True), res(2, "cpu", "Fox", "CPU, Level 3", 1, 4, "[N]%"))
    acts = '<div style="display:flex;gap:8px;margin-top:auto">%s%s%s</div>' % (btn("Rematch", "focus", "big", kgl="A"), btn("Fighters", "", "big", kgl="X"), btn("Main menu", "", "big", kgl="B"))
    return page(["Versus", "Melee", "Results"], '<div class="col fill" style="gap:10px">%s%s%s</div>' % (banner, rows, acts),
                [("dpad", "Move"), ("A", "Rematch"), ("X", "Back to fighters"), ("B", "Main menu")], chap=1, wide=wide, pos="Match 1", title="13 results")


# ------------------------------------------------------------------ 14 settings
SET_TABS = [("Video", "", ""), ("Audio", "", ""), ("Controls", "", ""), ("Online", "", ""), ("Game", "", "")]


def _settab(active):
    return tabs([(l, n, "on" if l == active else "") for l, n, _ in SET_TABS], dense=True)


def _page_settings(active, rows, det, hints, pos, title, trail=("Settings",)):
    left = '<div class="col" style="flex:1.45">%s%s</div>' % (_settab(active), pane('<div class="list" style="gap:5px">%s</div>' % "".join(rows), "fill", style="padding-top:14px"))
    right = '<div class="col" style="flex:.7">%s</div>' % pane(det, "fill")
    return page(list(trail) + [active], left + right, hints, chap=4, pos=pos, title=title)


def s14(wide=False):
    rows = [row("Window", choice("Borderless"), "video"), row("Render scale", slider(4, 12, "200%"), "video", "focus"), row("Frame rate", choice("120"), "clock"),
            row("VSync", tog(False), "refresh"), row("FPS readout", tog(True), "data")]
    media = '<div style="display:flex;align-items:flex-end;gap:10px;color:var(--muted)"><div style="width:22px;height:16px;box-shadow:inset 0 0 0 2px var(--line2)"></div><div style="width:44px;height:33px;background:var(--ember)"></div><div style="width:66px;height:50px;box-shadow:inset 0 0 0 2px var(--line2)"></div></div>'
    det = detail("Render scale", "How sharply the game is drawn, relative to the window. Higher costs more.",
                 rows=[("Now", '<span class="num">200%</span>'), ("With", tag("Frame rate", "line"))], media=media, kick="Video", more="Performance record", mh=88)
    return _page_settings("Video", rows, det, [("dpad", "Move"), ("dpad", "Change"), ("L", "Page"), ("B", "Back"), ("Y", "Reset page")], "2 / 5", "14 settings video")


def s14b(wide=False):
    rows = [row("Master volume", slider(8, 20, "40"), "audio", "focus"), row("Music", slider(14, 20, "70"), "audio"), row("Effects", slider(16, 20, "80"), "audio"),
            row("Output", choice("Stereo"), "audio")]
    media = '<div style="display:flex;gap:3px;align-items:flex-end;height:60px">%s</div>' % "".join('<i style="width:9px;height:%dpx;background:%s"></i>' % (10 + (i * 7) % 40, "var(--ember)" if i < 9 else "var(--ground)") for i in range(16))
    det = detail("Master volume", "Loudness of everything. Music and effects are mixed under it.", rows=[("Test", btn("Play sound", "", kgl="X"))], media=media, kick="Audio", mh=88)
    return _page_settings("Audio", rows, det, [("dpad", "Move"), ("dpad", "Change"), ("X", "Test sound"), ("L", "Page"), ("B", "Back")], "1 / 4", "14b settings audio")


def s14c(wide=False):
    bind = [("A", "Attack", ""), ("B", "Special", ""), ("X", "Jump", ""), ("Y", "Jump", "Also"), ("Z", "Grab", ""), ("L", "Shield", ""), ("R", "Shield", "Swap")]
    rows = ['<div class="row" style="height:30px"><span class="lbl">Profile</span><span class="val">%s</span></div>' % choice("Default")]
    for g, act, mod in bind:
        st = "focus" if g == "A" else ""
        right = ('<span class="tag ember">Press a button</span>' if st else ('<span class="tag line">%s</span>' % mod if mod else ""))
        rows.append('<div class="row %s" style="height:30px;gap:10px">%s<span class="lbl" style="flex:1;font-size:16px;color:var(--ivory)">%s</span>%s</div>' % (st, kg(g), act, right))
    # the pad: a flat top-down controller built from boxes
    pad = ('<div style="position:relative;width:200px;height:104px;margin-top:8px">'
           '<div style="position:absolute;left:8px;top:10px;width:184px;height:84px;background:var(--plate2);clip-path:polygon(8% 0,92% 0,100% 40%,92% 100%,70% 100%,62% 78%,38% 78%,30% 100%,8% 100%,0 40%)"></div>'
           '<div style="position:absolute;left:24px;top:34px;width:34px;height:34px;border-radius:50%%;background:var(--ground);box-shadow:inset 0 0 0 2px var(--line2)"></div>'
           '<div style="position:absolute;left:36px;top:46px;width:10px;height:10px;border-radius:50%%;background:var(--muted)"></div>'
           '<div style="position:absolute;left:84px;top:62px;width:22px;height:22px;"><div style="position:absolute;left:8px;top:0;width:6px;height:22px;background:var(--line2)"></div><div style="position:absolute;left:0;top:8px;width:22px;height:6px;background:var(--line2)"></div></div>'
           '<div style="position:absolute;left:146px;top:62px;width:22px;height:22px;border-radius:50%%;background:var(--ground);box-shadow:inset 0 0 0 2px var(--p3)"></div>'
           '<div style="position:absolute;left:138px;top:28px;width:36px;height:36px;border-radius:50%%;background:var(--pad-a);display:grid;place-items:center;color:var(--ink);font-family:var(--f-cap);font-weight:700;font-size:20px;box-shadow:0 0 0 3px var(--ember)">A</div>'
           '<div style="position:absolute;left:120px;top:50px;width:18px;height:18px;border-radius:50%%;background:var(--pad-b);display:grid;place-items:center;font-family:var(--f-cap);font-weight:700;font-size:13px;color:#fff">B</div>'
           '<div style="position:absolute;left:176px;top:44px;width:18px;height:18px;border-radius:50%%;background:var(--pad-x);display:grid;place-items:center;font-family:var(--f-cap);font-weight:700;font-size:13px;color:var(--ink)">X</div>'
           '<div style="position:absolute;left:146px;top:14px;width:18px;height:18px;border-radius:50%%;background:var(--pad-x);display:grid;place-items:center;font-family:var(--f-cap);font-weight:700;font-size:13px;color:var(--ink)">Y</div>'
           '<div style="position:absolute;left:96px;top:30px;width:20px;height:10px;background:var(--pad-z)"></div>'
           '<div style="position:absolute;left:14px;top:2px;width:44px;height:10px;background:#c4cad8;clip-path:polygon(0 100%,10% 0,90% 0,100% 100%)"></div>'
           '<div style="position:absolute;left:142px;top:2px;width:44px;height:10px;background:#c4cad8;clip-path:polygon(0 100%,10% 0,90% 0,100% 100%)"></div></div>')
    pad = pad.replace("%%", "%")
    det = detail("A button", "Attack. Press the new button for it, or swap two.", rows=[("Mode", tag("Replace", "ember") + tag("Also", "line") + tag("Swap", "line")), ("Tester", '<span class="muted">Press any button</span>')],
                 media=pad, kick="Pad, port 1", more="Presets", mh=124)
    left = '<div class="col" style="flex:1">%s%s</div>' % (_settab("Controls"), pane('<div class="list" style="gap:4px">%s</div>' % "".join(rows), "fill", style="padding-top:14px"))
    right = '<div class="col" style="flex:.85">%s</div>' % pane(det, "fill")
    return page(["Settings", "Controls", "Remap"], left + right, [("dpad", "Move"), ("A", "Rebind"), ("X", "Swap"), ("Y", "Presets"), ("B", "Back")], chap=4, pos="1 / 7", title="14c remap")


# ------------------------------------------------------------------ 15 mods
def s15(wide=False):
    def mod(name, kind, on, sub, state="", warn=False):
        right = '<span class="tag sun" style="margin-right:4px">%s Conflict</span>' % ic("warn", "sm") if warn else ""
        return '<div class="row tall %s" style="gap:8px;height:43px"><span class="lbl" style="font-size:17px;color:var(--ivory)">%s<small>%s</small></span>%s%s</div>' % (state, name, sub, right, tog(on))
    rows = [mod("Supertime Envoy", "Mode", True, "Mode &middot; adds Solo &gt; Envoy"), mod("Geno LAB", "Tool", True, "Tool &middot; adds Solo &gt; LAB"),
            mod("Envoy Drives", "Assets", True, "Assets &middot; drive models", "focus", True), mod("Envoy Drives SA2", "Assets", True, "Assets &middot; drive models", "", True),
            mod("Sora", "Fighter", True, "Fighter &middot; Geno"), mod("Meta Knight", "Fighter", False, "Fighter")]
    note_ = '<div style="margin-top:8px;display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)">%s<span>Changes apply when the game restarts.</span></div>' % ic("refresh", "sm")
    left = '<div class="col" style="flex:1.5">%s%s</div>' % (tabs([("Installed", "6", "on"), ("Conflicts", "1", "")], lr=False), pane('<div class="list" style="gap:4px">%s</div>' % "".join(rows), "fill", style="padding-top:12px"))
    media = '<div style="display:flex;gap:18px;align-items:center"><div style="width:52px;height:52px;position:relative">%s</div><span class="cap sun" style="font-size:26px;font-weight:700">=</span><div style="width:52px;height:52px;position:relative">%s</div></div>' % (drv("red"), drv("red"))
    det = detail("Envoy Drives", "Provides the same drive models as Envoy Drives SA2. Keep one on.",
                 rows=[("Adds", '<span class="muted">Models only</span>'), ("From", "envoy_drives")], media=media, kick="Conflict", more="Resolve", mh=76)
    right = '<div class="col" style="flex:.8">%s</div>' % pane(det, "fill")
    return page(["Mods"], left + right, [("dpad", "Move"), ("A", "Turn on or off"), ("B", "Back"), ("Y", "Details")], chap=3, pos="3 / 6  Applies at restart", title="15 mods")


# ------------------------------------------------------------------ 16 LAB pause
def s16(wide=False):
    labtabs = tabs([("Play", "", ""), ("Display", "", ""), ("Dummy", "", "on"), ("States", "", ""), ("Tools", "", ""), ("Exit", "", "")], lr=False, dense=True)
    rows = [row("Behaviour", choice("Stand"), "training", "focus"), row("Shield", choice("Never"), "lock"), row("Percent", stepper("0%"), "up"),
            row("Reset position", '<span class="muted" style="font-family:var(--f-ui)">Now</span>', "refresh", chev=True), row("Respawn on KO", tog(True), "flag")]
    det = detail("Behaviour", "What the dummy does while you test.", rows=[("With", tag("Hitboxes", "line") + tag("Frames", "line")), ("From", tag("Mod", "jade") + "<span>Geno LAB</span>")], kick="Dummy", more="All behaviours", mh=0)
    left = '<div class="col" style="flex:1.45;justify-content:flex-start">%s%s</div>' % (labtabs, pane('<div class="list" style="gap:5px">%s</div>' % "".join(rows), "", style="padding-top:14px"))
    right = '<div class="col" style="flex:.75;justify-content:flex-start">%s</div>' % pane(det, "")
    p = page(["LAB", "Pause", "Dummy"], left + right, [("dpad", "Move"), ("dpad", "Change"), ("L", "Page"), ("R", "Page"), ("B", "Resume"), ("Y", "Frame step")], chap=0, pos="1 / 5", title="16 lab pause", ground=False)
    return p.replace('<div class="hdr">', scene() + '<div class="scrim" style="background:rgba(8,10,14,.66)"></div><div class="hdr">', 1)


# ------------------------------------------------------------------ 17 launcher
def s17(wide=False):
    rail = "".join('<div class="row tall %s" style="gap:10px;height:44px">%s<span class="lbl cap" style="font-size:18px;letter-spacing:.08em">%s</span></div>' % (st, ic(i, ""), l)
                   for l, i, st in (("Play", "right", "focus"), ("Mods", "mods", ""), ("Diagnostics", "data", ""), ("About", "star", "")))
    discs = [row("Vanilla", tag("Ready", "jade"), "disc", "sel"), row("Akaneia", tag("Ready", "jade"), "disc"), row("ACE", tag("Ready", "jade"), "disc", "focus sel")]
    disc_pane = pane('<div class="list" style="gap:5px">%s</div><div style="display:flex;gap:8px;margin-top:10px">%s%s</div>' % ("".join(discs), btn("Add disc", "", ico="plus"), btn("Manage", "")), "", head="Disc library", headr="3 discs")
    opts = pane('<div class="list" style="gap:5px">%s</div>' % "".join([row("Unlock everything", tog(False)), row("Skip intro", tog(True)), row("Close launcher on play", tog(False)),
                                                                          row("Volume", slider(2, 20, "10"))]), "", head="Options")
    det = detail("ACE", "The game starts from the selected disc.", rows=[("Mods", '<span class="num">[N] on</span>'), ("Build", '<span class="num">[VERSION]</span>')], kick="Play with", more="Mods for this disc")
    go = ('<div style="display:flex;flex-direction:column;gap:8px"><span style="display:flex;align-items:center;gap:8px;white-space:nowrap" class="muted">%s<span style="font-size:14px">Game files are ready.</span></span>%s'
          '<span style="display:flex;gap:6px;align-items:center;white-space:nowrap;font-size:13px" class="muted"><span class="kk">Enter</span> to play <span class="kk">Ctrl</span><span class="kk">M</span> mods</span></div>') % (ic("check", "sm"), btn("Play", "focus", "big w", ico="right"))
    main = ('<div style="display:flex;gap:12px;flex:1;min-height:0"><div class="col" style="width:420px;gap:10px">%s%s</div><div class="col fill" style="gap:10px">%s%s</div></div>') % (disc_pane, opts, pane(det, "fill"), go)
    html_ = ('<!doctype html><html><head><meta charset="utf-8"><title>17 launcher</title><link rel="stylesheet" href="../tokens.css"><link rel="stylesheet" href="../kit.css">'
             '<style>.s{height:600px}</style></head><body>%s<div class="s" style="--w:900px;background:#080a0e">'
             '<div style="position:absolute;left:0;right:0;top:0;height:34px;display:flex;align-items:center;gap:10px;padding:0 12px;background:var(--ground);border-bottom:1px solid var(--line)">%s<span class="cap" style="font-size:15px;letter-spacing:.14em;color:var(--muted)">GD&rsquo;S MELEE &middot; Launcher</span><span style="margin-left:auto;display:flex;gap:6px"><i style="width:22px;height:4px;background:var(--line2);margin-top:12px"></i><i style="width:18px;height:18px;box-shadow:inset 0 0 0 2px var(--line2);margin-top:3px"></i><i style="width:18px;height:18px;margin-top:3px;position:relative;color:var(--line2)">%s</i></span></div>'
             '<div style="position:absolute;left:0;top:34px;bottom:0;width:204px;background:var(--ground2);padding:16px 12px"><div class="list" style="gap:6px">%s</div>'
             '<div style="position:absolute;left:14px;bottom:14px;font-size:13px;color:var(--dim)" class="num">v0.1.7</div></div>'
             '<div style="position:absolute;left:204px;right:0;top:34px;bottom:0;padding:18px 24px 18px;display:flex;flex-direction:column;gap:12px">'
             '<div style="display:flex;align-items:baseline;gap:12px"><span class="cap" style="font-size:34px;font-weight:700;letter-spacing:.06em">Play</span><span class="muted" style="font-size:14px">Pick a disc, then play.</span></div>'
             '%s</div></div></body></html>') % (
        defs(parts_svg()), mark(18), ic("x", "sm"), rail, main)
    return html_


def parts_svg():
    import parts as _p
    return _p.DRIVES["svg"]
