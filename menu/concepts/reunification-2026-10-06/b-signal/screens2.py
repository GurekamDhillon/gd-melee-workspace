"""Screens 09-17: Envoy bag, reward, HUD, pause, payout, results, settings, mods, LAB pause, launcher."""
from ui import *

# Real piece names and real one-line rules (APPENDIX-pieces.md). Family colours here follow the drive models' meaning
# (red damage, green speed, blue defence, yellow air, purple status, white wild); the family of each piece is illustrative.
P = {
    "kindling": ("Kindling", "Your hits set the target Burning for 3 s.", "purple", "magic", "When"),
    "icebound": ("Icebound", "Your hits Chill the target for 2 s.", "purple", "magic", "When"),
    "lingering": ("Lingering", "Status effects you cause last 20% longer", "purple", "rare", "Always on"),
    "cinder": ("Cinder", "Your hits deal 10% more damage to Burning targets", "red", "magic", "Always on"),
    "ledge": ("Ledge", "Grab a ledge: Haste for 3 s.", "green", None, "When"),
    "shelter": ("Shelter", "Grab a ledge: Guarded for 2 s.", "blue", None, "When"),
    "armoured": ("Damage resistant", "Damage you take -8%", "blue", None, "Always on"),
}
FAM_WORD = {"red": "Damage", "green": "Speed", "blue": "Defence", "yellow": "Air", "purple": "Status", "white": "Wild"}


def drv(k, size="md", state=""):
    n, r, fam, rar, w = P[k]
    return drive(fam, size, rar, state)


# ---------------------------------------------------------------- 09 the bag
def s09(wide=False):
    W = 853.3333 if wide else 640
    b = crumb("Envoy", "Bag")
    b += count("03", "11")
    # the map strip: everything the player owns is visible all the time, tiny, and doubles as the tab strip
    eq = ["kindling", "icebound", "lingering", "cinder", "ledge", None]
    bag = ["lingering", "shelter", "armoured", None]
    x0 = 32
    b += '<div class="abs" style="left:%dpx;top:46px">%s</div>' % (x0, tabs(["Equipped"], "Equipped", f=True, counts={"Equipped": "5/6"}))
    for i, k in enumerate(eq):
        x = x0 + i * 44
        if k is None:
            b += '<div class="abs" style="left:%dpx;top:78px">%s</div>' % (x, drive_slot("md", "empty"))
        else:
            b += '<div class="abs brk %s" style="left:%dpx;top:78px">%s</div>' % ("f" if i == 2 else "", x, drv(k, "md"))
    gx = 32 + 6 * 44 + 24
    b += '<div class="abs" style="left:%dpx;top:46px">%s</div>' % (gx, tabs(["Bag"], "Bag", f=False, counts={"Bag": "3/4"}))
    for i, k in enumerate(bag):
        x = gx + i * 44
        if k is None:
            b += '<div class="abs" style="left:%dpx;top:78px">%s</div>' % (x, drive_slot("md", "empty"))
        else:
            b += '<div class="abs" style="left:%dpx;top:78px">%s</div>' % (x, drv(k, "md"))
    kx = gx + 4 * 44 + 24
    b += '<div class="abs" style="left:%dpx;top:46px">%s</div>' % (kx, tabs(["Keystone"], "Keystone", f=False, counts={"Keystone": "1/2"}))
    b += '<div class="abs" style="left:%dpx;top:84px">%s</div>' % (kx, ks("E", "purple", "on"))
    b += '<div class="abs" style="left:%dpx;top:84px">%s</div>' % (kx + 34, ks("+", "purple", "empty"))
    # merge connector: the bag's second Lingering flows into the equipped one
    mx1 = x0 + 2 * 44 + 20
    mx2 = gx + 20
    b += ('<svg class="abs" style="left:0;top:0" width="%d" height="140" viewBox="0 0 %d 140"><path d="M%d 122 V130 H%d V122" fill="none" stroke="#d4ff2a" stroke-width="2"/>'
          '<polygon points="%d,121 %d,121 %d,115" fill="#d4ff2a" transform="translate(0,0)"/></svg>' % (int(W), int(W), mx2, mx1, mx1 - 4, mx1 + 4, mx1))
    b += '<div class="abs c volt" style="left:%dpx;top:124px;background:var(--ground);padding:0 6px">Merge</div>' % ((mx1 + mx2) // 2 - 20)
    # the detail lens: the active group, FULL rule text for every row, the focused row enlarged
    y = 142
    for i, k in enumerate(eq):
        if i == 2:
            n, r, fam, rar, when = P[k]
            h = 112
            b += '<div class="abs" style="left:32px;top:%dpx;width:%dpx;height:%dpx">' % (y, int(W) - 64, h)
            b += '<div style="position:absolute;left:0;top:4px;bottom:4px;width:6px;background:var(--volt)"></div>'
            b += '<div class="abs" style="left:22px;top:2px">%s</div>' % drive(fam, "lg", rar, "")
            b += '<div class="abs" style="left:122px;top:0;right:0">'
            b += '<div class="fx ab" style="gap:8px"><span class="d s-focus bone">%s</span><span class="badge" style="margin-left:6px">RARE</span><span class="badge" style="margin-left:0">%s</span><span class="badge" style="margin-left:0">%s</span></div>' % (esc(n), esc(when.upper()), esc(FAM_WORD[fam].upper()))
            b += '<div class="d bone" style="font-weight:600;font-size:20px;text-transform:none;letter-spacing:.01em;line-height:1;margin-top:6px">%s</div>' % esc(r)
            b += '<div class="fx ac" style="gap:8px;margin-top:10px">%s<span class="c bone">Merge the Lingering in your bag. It gets stronger.</span></div>' % glyph("a")
            b += '</div></div>'
            y += h + 4
        else:
            if k is None:
                b += ('<div class="abs fx ac" style="left:52px;top:%dpx;height:30px;gap:12px"><span class="d s-row off">Empty slot</span>'
                      '<span class="c" style="color:var(--off)">Drops go here first</span></div>' % y)
            else:
                n, r, fam, rar, when = P[k]
                b += ('<div class="abs fx ac" style="left:32px;top:%dpx;width:%dpx;height:30px">'
                      '<span style="width:20px"></span>%s<span class="d s-row mid" style="width:134px;margin-left:10px">%s</span>'
                      '<span class="b dim nw" style="color:var(--dim)">%s</span></div>' % (y, int(W) - 64, drive(fam, "sm", rar), esc(n), esc(r)))
            y += 32
    b += foot(hint("stick", "Move"), hint("a", "Merge"), hint("x", "To bag"), hint("b", "Back"), hint("l", "Group"))
    return page("09 envoy bag", b, wide)


# ---------------------------------------------------------------- 10 reward
def s10(wide=False):
    b = crumb("Envoy", "Stage 3", "Reward")
    b += '<div class="count c">Take one</div>'
    b += ('<div class="abs fx ac" style="left:32px;top:50px;gap:12px"><span class="sel"></span>'
          '<span class="d s-head volt">Unlocked: fifth slot</span></div>')
    # the build, small, top right: a choice is made against what you own
    b += '<div class="abs c" style="left:330px;top:58px">Your build</div>'
    cells = ["kindling", "icebound", "lingering", None, "open", "lock"]
    for i, k in enumerate(cells):
        x = 420 + i * 32
        if k == "open":
            b += '<div class="abs" style="left:%dpx;top:50px"><div class="gc sm" style="border:2px solid var(--volt);width:28px;height:28px"></div></div>' % x
        elif k == "lock":
            b += '<div class="abs" style="left:%dpx;top:50px">%s</div>' % (x, drive_slot("sm", "lock"))
        elif k is None:
            b += '<div class="abs" style="left:%dpx;top:50px">%s</div>' % (x, drive_slot("sm", "empty"))
        else:
            b += '<div class="abs" style="left:%dpx;top:50px">%s</div>' % (x, drv(k, "sm"))
    # three offers: the focused one is wide, the others stay readable
    cols = [(32, 252, "cinder", True, "Goes into slot 5.", "Completes Burning with Kindling."),
            (304, 150, "lingering", False, "Merges: Lingering got stronger.", ""),
            (470, 138, "shelter", False, "Goes into slot 5.", "")]
    for x, w, k, f, line1, line2 in cols:
        n, r, fam, rar, when = P[k]
        if f:
            b += '<div class="abs brk f" style="left:%dpx;top:92px">%s</div>' % (x + 8, drive(fam, "hg", rar))
            b += '<div class="abs" style="left:%dpx;top:220px;width:%dpx">' % (x, w)
            b += '<div class="d s-focus bone">%s</div>' % esc(n)
            b += '<div class="d bone" style="font-weight:600;font-size:20px;text-transform:none;letter-spacing:.01em;line-height:22px;margin-top:8px">%s</div>' % esc(r)
            b += '<div class="c" style="margin-top:8px">%s / %s</div>' % (when, FAM_WORD[fam])
            b += '<div class="c bone" style="margin-top:5px">%s</div>' % esc(line1)
            b += '<div class="fx" style="gap:8px;margin-top:4px"><span class="sel" style="margin-top:4px;flex:none"></span><span class="c bone" style="white-space:normal">%s</span></div>' % esc(line2)
            b += '</div>'
        else:
            b += '<div class="abs" style="left:%dpx;top:120px">%s</div>' % (x, drive(fam, "lg", rar, ""))
            b += '<div class="abs" style="left:%dpx;top:220px;width:%dpx">' % (x, w)
            b += '<div class="d s-head mid">%s</div>' % esc(n)
            b += '<div class="b" style="margin-top:8px;color:var(--dim)">%s</div>' % esc(r)
            b += '<div class="c" style="margin-top:8px">%s / %s</div>' % (when, FAM_WORD[fam])
            b += '<div class="c mid" style="margin-top:5px">%s</div>' % esc(line1)
            b += '</div>'
    right = ('<span class="fx ac" style="gap:10px;white-space:nowrap"><span class="c">Time left</span><span class="pg plain" style="display:inline-block;width:110px;vertical-align:middle"><i style="width:78%"></i></span>'
             '<span class="c bone">38 s</span></span>')
    b += foot(hint("stick", "Look"), hint("a", "Take"), hint("x", "Bag"), hint("b", "Skip"), right=right)
    return page("10 envoy reward", b, wide)


# ---------------------------------------------------------------- stage stand-in (flat silhouette, no screenshots)
def stand(dim=0.0):
    s = '<div class="stand" style="left:120px;top:332px;width:400px;height:20px"></div>'
    s += '<div class="stand" style="left:140px;top:352px;width:360px;height:40px;opacity:.55"></div>'
    s += '<div class="stand" style="left:180px;top:268px;width:90px;height:8px"></div>'
    s += '<div class="stand" style="left:370px;top:268px;width:90px;height:8px"></div>'
    s += '<div class="stand" style="left:270px;top:208px;width:100px;height:8px"></div>'
    s += '<div class="stand" style="left:224px;top:290px;width:16px;height:42px;background:#232831"></div>'
    s += '<div class="stand" style="left:402px;top:290px;width:16px;height:42px;background:#232831"></div>'
    return s


# ---------------------------------------------------------------- 11 HUD
def s11(wide=False):
    b = stand()
    # floor drives
    b += '<div class="abs" style="left:196px;top:220px">%s</div>' % drive("red", "md", None)
    b += '<div class="abs" style="left:398px;top:220px">%s</div>' % drive("green", "md", None)
    b += '<div class="abs" style="left:213px;top:262px;width:6px;height:6px;background:var(--mid);opacity:.0"></div>'
    # top-left: the build bar, squares and keystone letters
    b += ('<div class="abs" style="left:32px;top:28px"><div class="fx ac" style="gap:10px">%s%s</div>'
          '<div class="c" style="margin-top:8px">Build 5 / 6</div></div>' % (
              segs(["purple", "purple", "purple", "red", "green", None]), ks("E", "purple", "on sm")))
    # top-centre: the one instruction
    b += ('<div class="abs r" style="left:160px;width:320px;top:28px;text-align:center"><div class="d s-head bone">Collect the drives</div>'
          '<div class="c" style="margin-top:6px">2 on the stage</div></div>')
    # top-right: a small opponent card
    b += ('<div class="abs" style="right:32px;top:28px;text-align:right"><div class="fx ac jb" style="gap:8px;justify-content:flex-end">%s<span class="d s-row mid">Marth</span></div>'
          '<div class="d s-head dim" style="margin-top:6px">63<span style="font-size:20px">%%</span></div></div>' % tally(2, "p2", cpu=True))
    # bottom-left: you
    b += ('<div class="abs" style="left:32px;bottom:30px"><div class="fx ac" style="gap:8px;margin-bottom:6px">%s<span class="d s-row bone">Fox</span></div>'
          '<div class="d s-focus bone" style="line-height:.8">47<span style="font-size:20px">%%</span></div>'
          '<div class="fx" style="gap:5px;margin-top:8px">%s</div></div>' % (
              tally(1, "p1"), "".join('<span style="width:14px;height:6px;background:var(--p1)"></span>' for _ in range(3))))
    # a corner note
    b += note("Merged!", "Lingering got stronger.", right=32, bottom=34, mine=True)
    return page("11 envoy hud", b, wide)


# ---------------------------------------------------------------- 12 pause
def s12(wide=False):
    b = stand()
    b += '<div class="scrim"></div>'
    b += '<div class="abs" style="z-index:22;left:0;top:0;width:100%;height:100%">'
    b += crumb("Paused")
    b += '<div class="count c"><span style="color:var(--p1)">P1</span> <b>has the menu</b></div>'
    b += lens("hub", 32, 66, 360, li("Resume", f=True), li("Bag"), li("Controls"), li("Quit"))
    # the build, always readable at a glance
    b += '<div class="abs" style="left:400px;top:106px;width:208px"><div class="c" style="margin-bottom:10px">Stage 4 / Classic</div>'
    b += '<div class="fx" style="gap:6px;margin-bottom:14px">%s</div>' % "".join(
        (drv(k, "sm") if k else drive_slot("sm", "empty")) for k in ("kindling", "icebound", "lingering", "cinder", None, None))
    b += '<div class="fx ac" style="gap:8px">%s<span class="c">Keystone: Everburn</span></div></div>' % ks("E", "purple", "on sm")
    b += foot(hint("stick", "Move"), hint("a", "Select"), hint("start", "Resume"), hint("z", "Bag"))
    b += "</div>"
    return page("12 pause", b, wide)


def s12b(wide=False):
    b = crumb("Envoy", "Stage 4")
    b += '<div class="abs c" style="left:32px;top:64px">Cleared</div>'
    b += '<div class="d s-hero bone abs" style="left:30px;top:82px">Stage 4</div>'
    # the payout: a short ledger, each line one fact
    lines = [("Time", "[TIME]"), ("Drives", "2 collected"), ("Coins", "+[COINS]"), ("Next", "Stage 5 / [THEME]")]
    y = 222
    b += '<div class="abs" style="left:32px;top:214px;width:400px;height:1px;background:var(--line)"></div>'
    for i, (a, v) in enumerate(lines):
        b += ('<div class="abs fx ab nw" style="left:32px;top:%dpx;width:420px"><span class="d s-head dim" style="width:120px">%s</span>'
              '<span class="d s-head bone">%s</span></div>' % (y, esc(a), esc(v)))
        y += 40
    b += '<div class="abs" style="left:476px;top:206px">%s</div>' % drive("red", "hg", None, "")
    b += '<div class="abs c" style="left:476px;top:336px;width:140px">Picked up: Cinder</div>'
    b += '<div class="abs" style="left:32px;top:390px">%s</div>' % btn("Continue", "f", sm=True)
    b += foot(hint("a", "Continue"), hint("x", "Bag"))
    return page("12b payout", b, wide)


# ---------------------------------------------------------------- 13 results
def s13(wide=False):
    b = crumb("Versus", "Results")
    b += '<div class="count c">Battlefield / 4 stocks</div>'
    b += '<div class="abs fx ac" style="left:32px;top:56px;gap:10px">%s<span class="c volt">P1 wins</span></div>' % tally(1, "p1", big=True)
    b += '<div class="d s-mega bone abs" style="left:24px;top:84px">Fox</div>'
    head = '<div class="abs c fx" style="left:32px;top:256px;width:576px"><span style="width:60px">Place</span><span style="width:210px">Fighter</span><span style="width:90px;text-align:right">KOs</span><span style="width:90px;text-align:right">Falls</span><span style="width:126px;text-align:right">Damage dealt</span></div>'
    b += head
    rows = [("1st", "p1", 1, "Fox", False, "3", "1", "212", True), ("2nd", "p2", 2, "Marth", False, "1", "3", "158", False),
            ("3rd", "p3", 3, "Pikachu", True, "0", "2", "97", False), ("4th", "p4", 4, "Roy", False, "0", "3", "64", False)]
    y = 280
    for pl, p, n, name, cpu, ko, fa, dm, win in rows:
        cls = "bone" if win else "mid"
        b += ('<div class="abs fx ac" style="left:32px;top:%dpx;width:576px;height:34px">'
              '<span class="d s-head %s" style="width:60px">%s</span><span class="fx ac" style="width:210px;gap:10px">%s<span class="d s-head %s">%s</span></span>'
              '<span class="d s-head %s" style="width:90px;text-align:right">%s</span><span class="d s-head %s" style="width:90px;text-align:right">%s</span>'
              '<span class="d s-head %s" style="width:126px;text-align:right">%s</span></div>' % (y, "volt" if win else "dim", pl, tally(n, p, cpu=cpu), cls, esc(name), cls, ko, cls, fa, cls, dm))
        y += 36
    b += foot(hint("a", "Rematch"), hint("x", "Characters"), hint("y", "Stages"), hint("b", "Leave"))
    return page("13 results", b, wide)


# ---------------------------------------------------------------- 14 settings
SET_TABS = ["Video", "Audio", "Controls", "Online", "Mods", "Gameplay"]


def s14(wide=False):
    b = crumb("Settings", "Controls")
    b += count("03", "06")
    b += '<div class="abs" style="left:32px;top:46px">%s</div>' % tabs(SET_TABS, "Controls", f=False, left="l", right="r")
    def g2(*n):
        return "".join(glyph(x) for x in n)
    def vv(*n):
        return '<span class="fx ac" style="gap:6px;justify-content:flex-end">%s</span>' % "".join(glyph(x) for x in n)
    rows = [li("Attack", v=vv("a")), li("Special", v=vv("b")),
            li("Jump", f=True, v=vv("x", "y")),
            li("Shield", v=vv("l", "r")), li("Grab", v=vv("z")), li("Taunt", v=vv("dpad")), li("Smash", v=vv("cstick")), li("Pause", v=vv("start"))]
    b += lens("dense", 32, 88, 330, *rows)
    # editing state: the strong thing on this screen
    b += ('<div class="abs" style="left:32px;top:322px;width:330px"><div class="d s-head bone">Press a button</div>'
          '<div class="c" style="margin-top:6px">to set Jump. Hold B to cancel.</div>'
          '<div class="fx ac" style="gap:12px;margin-top:12px"><span class="c">When taken</span>%s</div></div>' % opts(["Swap", "Also"], "Swap", f=True))
    # right column: profile, preset, the stick tester
    rx = 400
    b += '<div class="abs" style="left:%dpx;top:92px;width:208px">' % rx
    b += '<div class="c">Profile</div><div class="step f" style="margin:4px 0 14px">%s GD %s</div>' % (ARR_L, ARR_R)
    b += '<div class="c">Preset</div><div class="step" style="margin:4px 0 14px">%s Default %s</div>' % (ARR_L, ARR_R)
    b += '<div class="c" style="margin-bottom:8px">Test</div>'
    b += ('<svg width="116" height="116" viewBox="0 0 116 116"><rect x="1" y="1" width="114" height="114" fill="none" stroke="#2b3039" stroke-width="1"/>'
          '<line x1="58" y1="1" x2="58" y2="115" stroke="#2b3039"/><line x1="1" y1="58" x2="115" y2="58" stroke="#2b3039"/>'
          '<circle cx="58" cy="58" r="40" fill="none" stroke="#4a505a"/><rect x="82" y="30" width="8" height="8" fill="#d4ff2a"/></svg>')
    b += '<div class="c" style="margin-top:6px;color:var(--off)">Move the stick to see it</div></div>'
    b += foot(hint("stick", "Move"), hint("a", "Bind"), hint("x", "Clear"), hint("y", "Reset row"), hint("z", "Presets"), hint("b", "Back"))
    return page("14 settings controls", b, wide)


def s14b(wide=False):
    b = crumb("Settings", "Video")
    b += count("01", "06")
    b += '<div class="abs" style="left:32px;top:46px">%s</div>' % tabs(SET_TABS, "Video", f=False, left="l", right="r")
    rows = [li("Render scale", v=step("2x")),
            li("Frame rate", f=True, v=opts(["60", "120", "Uncapped"], "120", f=True)),
            '<div class="help" style="padding-left:20px;margin:-8px 0 10px">How often the game draws a frame.</div>',
            li("VSync", v=opts(["Off", "On"], "On")),
            li("FPS readout", v=opts(["Off", "On"], "Off"))]
    b += lens("list", 32, 100, 576, *rows)
    b += foot(hint("stick", "Move"), hint("dpad_lr", "Change"), hint("b", "Back"), hint("l", "Tab"), hint("z", "Defaults"))
    return page("14b settings video", b, wide)


def s14c(wide=False):
    b = crumb("Settings", "Audio")
    b += count("02", "06")
    b += '<div class="abs" style="left:32px;top:46px">%s</div>' % tabs(SET_TABS, "Audio", f=False, left="l", right="r")
    rows = [li("Master volume", v=slider(70, "70", w=220)),
            li("Music mix", f=True, v=slider(55, "55", f=True, w=220)),
            '<div class="help" style="padding-left:20px;margin:-8px 0 10px">Music against effects and voices.</div>',
            li("Effects mix", v=slider(80, "80", w=220)),
            li("Output", v=opts(["Stereo", "Mono"], "Stereo"))]
    b += lens("list", 32, 100, 576, *rows)
    b += foot(hint("stick", "Move"), hint("dpad_lr", "Change"), hint("b", "Back"), hint("l", "Tab"), hint("z", "Defaults"))
    return page("14c settings audio", b, wide)


# ---------------------------------------------------------------- 15 mods
def s15(wide=False):
    rows = [li("geno-lab", badge="MENU", v=opts(["Off", "On"], "On")),
            li("envoy", badge="MENU", v=opts(["Off", "On"], "On")),
            li("envoy_drives", v=opts(["Off", "On"], "On")),
            li("halberd", v=opts(["Off", "On"], "On")),
            li("turbo-combo", off=False, v=opts(["Off", "On"], "Off")),
            li("stage_tour", f=True, badge="CONFLICT", v=opts(["Off", "On"], "On", f=True)),
            '<div class="help" style="padding-left:20px;margin:-8px 0 0"><span class="alarm" style="font-family:var(--f-display);font-weight:800;font-size:20px;letter-spacing:.03em;margin-right:10px;text-transform:uppercase">Conflict</span>Also changes the stage list, like [OTHER MOD]. Turn one of them off.</div>']
    b = crumb("Settings", "Mods")
    b += count("06", "06")
    b += lens("list", 32, 64, 576, *rows)
    b += '<div class="abs fx ac" style="left:32px;top:392px;gap:10px"><span class="badge" style="margin:0">MENU</span><span class="c">adds its own entry to the menus</span></div>'
    b += '<div class="abs c r" style="right:32px;top:392px">Changes apply at the next start</div>'
    b += foot(hint("stick", "Move"), hint("a", "Turn on or off"), hint("b", "Back"), hint("y", "Details"))
    return page("15 mods", b, wide)


# ---------------------------------------------------------------- 16 LAB pause
def s16(wide=False):
    b = stand()
    b += '<div class="scrim" style="background:rgba(8,9,11,.84)"></div>'
    b += '<div class="abs" style="z-index:22;left:0;top:0;width:100%;height:100%">'
    b += crumb("The Lab", "Paused")
    b += '<div class="count c">Frame <b>0412</b></div>'
    b += '<div class="abs" style="left:32px;top:46px">%s</div>' % tabs(["Play", "Display", "Dummy", "States", "Tools", "Exit"], "Display", f=False, left="l", right="r")
    rows = [li("Clean", v=opts(["Off", "On"], "Off")), li("Hitboxes", f=True, v=opts(["Off", "On"], "On", f=True)),
            li("Frames", v=opts(["Off", "On"], "Off")), li("Stage", v=opts(["Off", "On"], "Off")), li("Inspect", v=opts(["Off", "On"], "On")),
            li("Moves", v=opts(["Off", "On"], "Off")), li("Launch", v=opts(["Off", "On"], "Off")),
            li("Combo", v=opts(["Off", "On"], "Off"))]
    b += lens("dense", 32, 94, 340, *rows)
    b += '<div class="abs" style="left:412px;top:100px;width:196px"><div class="c" style="margin-bottom:8px">Hitboxes</div><div class="b">Draws every hitbox and hurtbox as it is live.</div>'
    b += '<div class="c" style="margin-top:14px;color:var(--off)">Key: H</div></div>'
    b += foot(hint("stick", "Move"), hint("dpad_lr", "Toggle"), hint("start", "Resume"), hint("y", "Frame step"), hint("l", "Tab"))
    b += "</div>"
    return page("16 lab pause", b, wide)


# ---------------------------------------------------------------- 17 launcher (a desktop window)
def s17(wide=False):
    W, H = 1000, 640
    b = ""
    b += ('<div class="abs fx ac jb" style="left:0;right:0;top:0;height:44px;padding:0 20px;border-bottom:1px solid var(--line)">'
          '<span class="d s-row bone" style="font-size:20px">GD\'s Melee <span class="c" style="margin-left:10px">launcher / [VERSION]</span></span>'
          '<span class="fx" style="gap:22px"><svg width="14" height="14"><rect x="1" y="12" width="12" height="2" fill="#7a828e"/></svg>'
          '<svg width="14" height="14"><rect x="1" y="1" width="12" height="12" fill="none" stroke="#7a828e" stroke-width="2"/></svg>'
          '<svg width="14" height="14"><path d="M1 1L13 13M13 1L1 13" stroke="#7a828e" stroke-width="2"/></svg></span></div>')
    b += '<div class="abs" style="left:32px;top:70px">%s</div>' % tabs(["Play", "Mods", "Diagnostics", "About"], "Play", f=True)
    # left: the disc library
    b += '<div class="abs c" style="left:32px;top:132px">Disc library</div>'
    b += lens("list", 32, 156, 440, li("ACE", f=True, sel=True, badge="READY"), li("Vanilla", badge="READY"), li("Akaneia", badge="CHECK"))
    b += '<div class="abs fx" style="left:52px;top:352px;gap:16px">%s%s</div>' % (btn("Add disc", "", sm=True), btn("Manage", "", sm=True))
    # right: the few switches
    b += '<div class="abs" style="left:560px;top:132px;width:408px">'
    b += '<div class="c" style="margin-bottom:14px">Options</div>'
    for lab, on in (("Unlock everything", "Off"), ("Skip intro", "On"), ("Close launcher on play", "Off")):
        b += '<div class="fx ab jb" style="margin-bottom:18px"><span class="d s-row mid">%s</span>%s</div>' % (lab, opts(["Off", "On"], on))
    b += '<div class="fx ab jb" style="margin-bottom:6px"><span class="d s-row mid">Volume</span>%s</div>' % slider(3, "3", w=170)
    b += '</div>'
    # the one big action
    b += '<div class="abs" style="right:32px;bottom:62px;text-align:right">%s</div>' % btn("Play", "f", extra="")
    b += '<div class="abs c r" style="right:32px;bottom:34px">Plays with the ACE disc</div>'
    b += '<div class="abs" style="left:32px;top:420px"><div class="c" style="margin-bottom:10px">Now</div><div class="d s-row mid">6 mods on</div><div class="d s-row alarm" style="margin-top:4px">1 conflict</div></div>'
    b += cursor(960, 575, hot=True)
    b += ('<div class="abs fx ac" style="left:32px;bottom:22px;gap:22px">%s %s %s %s %s %s</div>' % (
        hint("Tab", "Move"), hint("Space", "Change"), hint("Enter", "Play"), hint("lmb", "Click"), hint("rmb", "Back"), hint("wheel", "Scroll")))
    return page("17 launcher play", b, width=W, height=H)


SCREENS2 = [("09-envoy-bag", s09, True), ("10-envoy-reward", s10, False), ("11-envoy-hud", s11, False), ("12-pause", s12, False),
            ("12b-payout", s12b, False), ("13-results", s13, False), ("14-settings-controls", s14, False),
            ("14b-settings-video", s14b, False), ("14c-settings-audio", s14c, False), ("15-mods", s15, False),
            ("16-lab-pause", s16, False), ("17-launcher-play", s17, False)]
