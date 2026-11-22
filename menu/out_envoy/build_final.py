#!/usr/bin/env python3
"""Envoy UI, final: every chosen screen in one consistent design.

Consolidates steps 2 to 6 (L3 row, P2 stickers, camp C1, drive D2, pick of three R2, keystone K1,
HUD H2 + M1 with the small bench sticker, map N2, shop S1, results, pause) and applies the rulings
that the step sheets disagreed on. Writes:

  final.html, final-screens.html     the sources, beside this file
  preview/final-spread.png           the flow in play order, other states, and the parts kit
  preview/final-flow.png, final-parts.png   the same in two halves, only if the spread is very tall
  screens/<name>.png, <name>@2x.png  each screen alone at 640x480 and 1280x960

Every screen is authored in game pixels (640x480) and scaled with CSS zoom. Original vector art
only; retail menu parts are grey placeholders; fighters, foes, bosses and stages are placeholders
with invented names. Fonts: Bricolage Grotesque and Source Sans 3 (SIL OFL).
"""
import math
from pathlib import Path
from playwright.sync_api import sync_playwright

import build_step2 as s2
import build_step3 as s3
import build_step4 as s4
import build_step5 as s5
import build_step6 as s6
from build_step2 import svg, star_svg, burst, SUN, INK, WHITE, CORAL, LAGOON, LILAC, FLAME, STAR, BURST
from build_step3 import at, sil, bt, hints, say, ptr, cur, frame, fcard, lock
from build_step4 import pog, d2, fst, curd, ttl, DR, FAM, RAR, KS, BG, BG2, SPARK
from build_step5 import coin, dpad, HEATC

HERE = Path(__file__).resolve().parent

# ------------------------------------------------------------------ rulings applied to the step data
RUN = s6.RUN            # fight, fight, fight, rest stop, boss; three acts
KINDS = s6.KINDS
DR["Feather Storm"] = ("wind", 1, 30, ["feathers rain on the nearest foe for 10%."], ["the feathers deal 16%", "they follow the foe"])
KS.update({
    "Echo Oath": ("Every drive fires twice, the second at half strength.", None, "Good with big drives"),
    "Winter Oath": ("All your damage Chills for 2 seconds.", "frost", "Good with frost"),
    "Grand Finale": ("Smash attacks launch harder the more Heat you hold.", None, "Good with high Heat"),
})
FAM["stone"] = ("Spare (clay)", "#C99455")
FAM["rose"] = ("Spare (rose)", "#FF9CC4")
ACTIVES = {"Volley": ("bolt", 3, "every drive fires now, in order, as one chain.")}

# The party at three moments. Slots: 3, then 4 after boss 1, then 5 after boss 2.
START = [(1, "Fighter A", 0, []), (1, "Fighter B", 1, []), (2, "Fighter C", 3, []), (2, "Fighter D", 5, [])]
MID = [(1, "Fighter A", 0, [("Ember", 2), ("Bolt", 1), ("Echo", 1)]), (1, "Fighter B", 1, [("Frost", 1), ("Metronome", 2)]),
       (2, "Fighter C", 3, [("Frost", 1), ("Clean Landing", 2), ("Mirror", 1), ("Tailwind", 1)]), (2, "Fighter D", 5, [("Tailwind", 1), ("Feather Storm", 1)])]
END = [(1, "Fighter A", 0, [("Ember", 3), ("Bolt", 2), ("Echo", 1), ("Wildfire", 1), ("Shatter", 1)]), (1, "Fighter B", 1, [("Frost", 2), ("Metronome", 2), ("Shatter", 1), ("Bolt", 1)]),
       (2, "Fighter C", 3, [("Frost", 1), ("Clean Landing", 3), ("Mirror", 2), ("Perfect Form", 1), ("Tailwind", 2)]), (2, "Fighter D", 5, [("Tailwind", 2), ("Feather Storm", 2), ("Ember", 1)])]
KEYS1, KEYS2, KEYS3 = ["Plague Bearer"], ["Plague Bearer", "Glass Core"], ["Plague Bearer", "Glass Core", "Long Fuse"]

CSS = s6.CSS + r"""
/* ---------- final: one strip, one stock dot, the menu rows ---------- */
.say,.strip{top:403px;height:30px;line-height:23px;font-size:13px;padding:0 11px;border-radius:10px;transform:rotate(-.6deg);z-index:5}
.sk{display:inline-flex;gap:3px;background:#2A1A6E;border-radius:10px;padding:3px 5px;vertical-align:top}
.sk i{width:12px;height:12px;border-radius:50%;background:#fff;display:block}
.sk i.off{background:none;box-shadow:inset 0 0 0 2px #6E61B5;transform:scale(.72)}
.sk i.last{background:#FF4D6D}
.fr2{display:flex;align-items:center;gap:4px;height:34px;padding-left:7px;border-top:2px dashed rgba(42,26,110,.25)}
.fr2 .ptag,.fr2 .pgap{flex:none;width:27px;text-align:center}
.fr2 .ptag{border:2.5px solid #2A1A6E;border-radius:8px;color:#fff;font-family:"Brico";font-weight:800;font-size:12px;line-height:15px}
.fr2 .hd{height:21px;overflow:hidden;flex:none}
.fr2 .fn{font-size:11px;line-height:12px;font-weight:700;width:50px;flex:none;white-space:nowrap}
.fr2 .cr{display:flex}
.kq{position:absolute;display:flex;align-items:center;gap:5px;height:25px;background:#2A1A6E;border-radius:9px;padding:0 9px 0 3px;color:#FFD84A;font-family:"Brico";font-weight:800;font-size:12.5px;line-height:14px;white-space:nowrap}
.kq svg{display:block;flex:none}
.cy2{display:inline-flex;align-items:center;gap:3px}
.ng i{font-size:11px}
.gs .plate.on{background:#B4B9CA !important;box-shadow:0 0 0 2.5px #F1F2F7 !important}
.pp{z-index:4}
.cy2 .pt{font-size:11px;line-height:13px;padding:0 3px;border-width:2px}

/* ---------- the sheet ---------- */
.fl2{display:grid;grid-template-columns:704px 112px 704px;align-items:start}
.fw h3{font-weight:900;font-size:23px;line-height:30px;margin-bottom:8px;display:flex;align-items:center;gap:10px;white-space:nowrap}
.fw h3 i{font-style:normal;flex:none;width:30px;height:30px;border-radius:50%;background:#1A1830;color:#fff;font-size:17px;line-height:30px;text-align:center}
.fw h3 span{font-weight:600;font-size:15.5px;color:#45425E}
.fw .cap{font-size:15px;min-height:40px}
.conn{height:528px;margin-top:38px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px}
.cl{font-size:13.5px;line-height:1.2;font-weight:700;color:#1A1830;text-align:center;width:108px}
.cl em{font-style:normal;font-weight:600;color:#45425E;display:block;margin-top:3px}
.kb{display:inline-block;min-width:22px;height:22px;border-radius:11px;background:#fff;border:2px solid #1A1830;font-weight:900;font-size:13px;line-height:18px;text-align:center;padding:0 6px;margin:0 4px 3px 0;vertical-align:middle}
.turn{height:78px;position:relative}
.turn svg{position:absolute;left:0;top:0}
.turn .cl{position:absolute;left:560px;top:20px;width:400px;background:#E6E5EC;padding:4px 0}
.row4 .cap{font-size:13.5px}
.pgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.pn{background:#F6F5FA;border-radius:18px;padding:16px 16px 14px}
.pn.w{grid-column:1 / 3}
.pn h3{font-weight:900;font-size:20px;margin-bottom:3px}
.pn p{font-size:14.5px;line-height:1.35;color:#45425E;margin-bottom:10px;max-width:1300px}
.pn p b{color:#1A1830;font-weight:700}
.pb{position:relative;border-radius:10px;overflow:hidden;background:#4C3D9E}
.pb.dk{background:#1E2A4A}
.pb .g{position:relative}
.pb svg{overflow:visible}
.lb{z-index:6;position:absolute;color:#fff;font-size:11px;line-height:13px;font-weight:700;white-space:nowrap}
.lb.q{color:#C9BFF5}
.sw{display:grid;grid-template-columns:repeat(4,1fr);gap:10px 18px}
.sw div{display:flex;gap:10px;align-items:center;font-size:14px;line-height:1.25;color:#45425E}
.sw i{flex:none;width:44px;height:44px;border-radius:10px;border:2.5px solid #1A1830}
.sw b{display:block;color:#1A1830;font-weight:700}
.ty{position:absolute;left:14px;display:flex;align-items:center;gap:14px;white-space:nowrap}
.ty .lb{position:static}
"""


# ------------------------------------------------------------------ shared parts, patched into the step modules
def sdots(left, total=5):
    """Stock dots: white, the last one coral. On a white sticker they sit in an ink capsule so they read."""
    last = left == 1
    return '<div class="sk">' + "".join(f'<i class="{"off" if i >= left else ("last" if last else "")}"></i>' for i in range(total)) + "</div>"


def kem(k, size):
    """Keystone emblem on a white disc; the three step 4 ones plus three more for the later picks."""
    if k == "Echo Oath":
        e = (f'<circle cx="-4" r="8" fill="none" stroke="{INK}" stroke-width="2.6"/><circle cx="4.5" r="8" fill="{LAGOON}" stroke="{INK}" stroke-width="2.4"/>')
    elif k == "Winter Oath":
        e = (f'<path d="M0,-12V12M-10.4,-6L10.4,6M-10.4,6L10.4,-6" fill="none" stroke="{INK}" stroke-width="2.8" stroke-linecap="round"/><circle r="4" fill="#62CCF5" stroke="{INK}" stroke-width="2"/>')
    elif k == "Grand Finale":
        e = f'<path transform="scale(.5)" d="{BURST}" fill="{CORAL}" stroke="{INK}" stroke-width="4.6" stroke-linejoin="round"/>'
    else:
        return _kem(k, size)
    return svg(size, size, "-21 -21 42 42", f'<circle r="18.5" fill="#fff" stroke="{INK}" stroke-width="3"/>{e}')


def kpill(x, y, name, rot=0):
    """A held keystone as a pill: emblem and name. Camp, map, results, main menu."""
    return f'<div class="kq" style="left:{x}px;top:{y}px;transform:rotate({rot}deg)">{kem(name, 21)}{name}</div>'


def kmini(k):
    """A held keystone in the fight HUD: a small ink wedge with the emblem, no words."""
    pts = "M3,3 H29 L25.5,23 H6.5Z"
    return svg(32, 27, "0 0 32 27", f'<path d="{pts}" fill="#fff" stroke="#fff" stroke-width="5" stroke-linejoin="round"/><path d="{pts}" fill="{INK}" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>') \
        + f'<div style="position:absolute;left:6.5px;top:3px">{kem(k, 19)}</div>'


HUDKEYS = list(KEYS2)


def hud_party(x, y, pool, n, plus=False, anchor="middle"):
    """What the party shares in a fight: stock dots, coins, and one to three keystone wedges under them."""
    left, total = pool
    w = total * 18 - 4
    b = ""
    if left == 1:
        b = at(-10, -8, svg(30, 30, "-27 -27 54 54", f'<path d="{BURST}" fill="{SUN}" stroke="{INK}" stroke-width="3.4" stroke-linejoin="round"/>'), "z-index:-1")
    a = at(-w / 2, 0, b + s5.stockdots(left, total))
    keys = "".join(at(i * 34, 0, kmini(k), "width:32px;height:27px") for i, k in enumerate(HUDKEYS))
    kw = len(HUDKEYS) * 34
    return (f'<div class="hp" style="left:{x - 6}px;top:446px;width:0;height:20px">{a}</div>'
            f'<div class="hp" style="left:14px;top:14px;width:{kw + 56}px;height:27px">{keys}{at(kw + 6, 4, s5.coins(n, plus))}</div>')


def trail(x, y, pos, lost=False, w=608, gap=31, r=7, step=200, rot=-.4, stamp=False, pad=12, tab=None):
    """The run on one sunny strip: dots are fights, a tent is the rest stop, a star is the boss."""
    acts = ""
    for a in range(3):
        m = "".join(s6.tmark(kind, "done" if a * 5 + i < pos else (("lost" if lost else "cur") if a * 5 + i == pos else "todo"), 13 + i * gap, 13, r) for i, kind in enumerate(RUN[a]))
        sw = 26 + 4 * gap
        acts += f'<div style="position:absolute;left:{pad + a * step}px;top:3px"><div class="s10">Act {a + 1}</div>{svg(sw, 26, f"0 0 {sw} 26", m)}</div>'
    st = ""
    if stamp:
        st = (f'<div class="bn" style="position:absolute;right:14px;top:6px;transform:rotate(-7deg);border:3px solid {CORAL};color:{CORAL};background:#fff;'
              f'border-radius:8px;font-size:17px;line-height:23px;padding:0 8px">Cleared</div>')
    if tab:
        st += f'<span class="tab" style="background:{INK};left:auto;right:-8px;top:auto;bottom:-17px;transform:rotate(-4deg)">{tab}</span>'
    return f'<div class="st" style="left:{x}px;top:{y}px;width:{w}px;height:46px;background:{SUN};transform:rotate({rot}deg)">{acts}{st}</div>'


def punch(pos, cur_=None, dim=False, stamp=False, lost=False):
    """The main-menu punch card: the same marks as the trail, an act to a line."""
    pos = {12: 15}.get(pos, pos)
    rows = ""
    for a in range(3):
        m = "".join(s6.tmark(kind, "done" if a * 5 + i < pos else ("cur" if (a * 5 + i == pos and cur_ is not None) else "todo"), 11 + i * 15.5, 12, 5) for i, kind in enumerate(RUN[a]))
        rows += f'<div style="position:absolute;left:4px;top:{6 + a * 41}px"><div class="s10">Act {a + 1}</div>{svg(88, 24, "0 0 88 24", m)}</div>'
    st = (f'<div class="bn" style="position:absolute;left:8px;top:48px;transform:rotate(-14deg);border:3px solid {CORAL};color:{CORAL};background:rgba(255,255,255,.9);border-radius:8px;font-size:18px;line-height:24px;padding:0 8px">Cleared</div>' if stamp else "")
    return f'<div class="st" style="left:245px;top:0;width:97px;height:136px;background:{SUN};transform:rotate(3deg);{"opacity:.5;" if dim else ""}">{rows}{st}</div>'


s4.lvburst = lambda style, size=50: f'<div class="lvb" style="{style}">{burst("Level|up!", CORAL, size, 14)}</div>'
_kem = s4.kem
s4.kem = s6.kem = kem
s3.stock_dots = s2.stock_dots = sdots
s2.punch_card = punch
s2.pog = lambda kind, size=28: pog("fire" if kind == "ember" else "frost", size, 1, sq=False)
s6.keypill = kpill
s6.trail = trail
s5.party = hud_party
_bossbar = s5.bossbar
s5.bossbar = lambda W, *a: _bossbar(W + 120, *a)   # the boss bar sits right of the party's keystones and coins
s5.pc_h2 = s6.pc_h2_new


def H(*items):
    """The one hint line. Order is always: move, A, B, Y, Start, then player 2's own."""
    return hints(*items)


def zi(h):
    return h.replace('class="hints"', 'class="hints" style="z-index:9"')


def party(x, y, data, n, **kw):
    return s6.party(x, y, data=data, n=n, **kw)


# ------------------------------------------------------------------ 1. the main-menu row and its stickers
s2.DESC.update(new="A co-op run for 1 or 2 players, three acts long.", saved="Continue your run from act 2, fight 2.",
               done="Run cleared. NG+ 1 is open at the camp.", miss="Envoy needs your Brawl disc. Add it in the launcher.")


def mrow(p, name, kind, chips, first, n):
    col = CORAL if p == 1 else LAGOON
    tag = f'<span class="ptag" style="background:{col}">P{p}</span>' if first else '<span class="pgap"></span>'
    cs = "".join(s4.chip(d, l) for d, l in chips) + "".join(s4.empty_slot() for _ in range(n - len(chips)))
    return f'<div class="fr2">{tag}<div class="hd">{sil(kind, 15)}</div><span class="fn">{name}</span><span class="cr">{cs}</span></div>'


def mstick(state):
    """P2, loose stickers, in the 340x296 space right of the rows."""
    if state == "saved":
        rows = "".join(mrow(p, nm, k, ch, i % 2 == 0, 4) for i, (p, nm, k, ch) in enumerate(MID))
        return (f'<div class="p2"><div class="st" style="left:2px;top:8px;width:246px;height:198px;transform:rotate(-2deg)">'
                f'<div class="band"><div class="hl" style="font-size:23px;line-height:25px">Continue run</div><div class="sub">Act 2, fight 2. Saved after fight 1.</div></div>{rows}</div>'
                f'{punch(6, 6)}'
                f'<div class="st" style="left:254px;top:146px;width:80px;height:30px;transform:rotate(4deg);background:{LAGOON};text-align:center"><span class="bn" style="font-size:15px;line-height:24px;color:#fff">NG+ 0</span></div>'
                f'{s3.stocks(8, 218, 4, 5, "Team stocks", rot=-3, w=126)}{kpill(150, 220, KEYS2[0], 1.5)}{kpill(158, 249, KEYS2[1], -1.5)}'
                f'<div class="st" style="left:262px;top:186px;width:72px;height:28px;transform:rotate(-3deg);display:flex;align-items:center;gap:4px;padding-left:6px">{coin(17)}<span class="bn" style="font-size:15px">23</span></div></div>')
    if state == "new":
        e = lambda p, t: (f'<div class="fr2" style="height:50px"><span class="ptag" style="background:{CORAL if p == 1 else LAGOON}">P{p}</span>'
                          f'<div style="height:36px;overflow:hidden;opacity:.45">{sil(0, 26)}</div><div class="slot" style="width:150px">{t}</div></div>')
        return (f'<div class="p2"><div class="st" style="left:2px;top:8px;width:246px;height:164px;transform:rotate(-2deg)">'
                f'<div class="band"><div class="hl" style="font-size:23px;line-height:25px">Start a run</div><div class="sub">Three acts: fights, a rest stop, a boss.</div></div>'
                f'{e(1, "Pick two fighters at the camp.")}{e(2, "A second player joins at the camp.")}</div>{punch(0)}'
                f'<div class="st" style="left:176px;top:160px;width:150px;height:70px;transform:rotate(-3deg);padding:6px 9px"><div class="s10" style="margin-bottom:4px">One stock pool</div>'
                f'{sdots(5)}<div class="s10" style="margin-top:4px;color:{INK}">5 together, 4 solo</div></div></div>')
    return s2.p2(state)


def menu(state="saved"):
    return (f'<div class="gs"><div class="in"><div class="rhd">retail header (placeholder)</div><div class="rnote">grey = retail placeholder</div>'
            f'<div class="rows">{s2.rows(3, 2, state == "miss")}</div><div class="ppos">{mstick(state)}</div>{s2.bar(state)}</div></div>')


# ------------------------------------------------------------------ 2. the camp (C1)
def camp(state="main"):
    saved, two = state == "main", state != "first"
    go = ("go", "Continue run", "Act 2, fight 2. 4 of 5 stocks left.") if saved else ("go", "Start run", "A new full run, from act 1.")
    ngv = "0" if two else f"{lock(11, LILAC)} 0 only"
    items = [go] + ([("new", "New run", "")] if saved else []) + [
        ("fighters", "Fighters", "2 each"), ("len", "Run length", "Full, 3 acts"), ("ta", "Team attack", s3.switch(False)),
        ("ng", "NG+ level", ngv), ("col", "Collection", "14 of 40" if two else "9 of 40"), ("back", "Back", "")]
    rots = [-1.2, .9, -.7, 1, -.9, .7, -1.1, 1.2]
    p, y = [s3.scene(1), s3.title()], 58
    for i, (k, lab, val) in enumerate(items):
        on = k == "go"
        cls = "row" + (" big" if k == "go" else "") + (" back" if k == "back" else "") + (" on" if on else "")
        v = f'<span class="v">{val}</span>' if val else ""
        p.append(f'<div class="{cls}" style="top:{y}px;transform:rotate({0 if on else rots[i]}deg)"><span class="l">{lab}</span>{v}</div>')
        if on:
            p.append(ptr(10, y + 14))
        y += 62 if k == "go" else 36
    p += [fcard(292, 54, "Fighter A", 0, 72, -3, "P1"), fcard(368, 60, "Fighter B", 1, 72, 2), s3.swap(354, 92)]
    if two:
        p += [fcard(468, 58, "Fighter C", 3, 72, -2, "P2"), fcard(544, 54, "Fighter D", 5, 72, 3), s3.swap(530, 92)]
    else:
        p.append(f'<div class="st dash" style="left:462px;top:58px;width:152px;height:92px;transform:rotate(2deg);padding:8px 10px">'
                 f'<span class="tab" style="background:{LAGOON}">P2</span><div class="t14" style="margin-top:4px">Player 2</div>'
                 f'<div class="fe" style="padding:0;margin-top:5px;line-height:15px">{bt("Start")}Join<br><span style="display:inline-block;margin-top:5px">on controller 2</span></div></div>')
    if saved:
        p += [trail(290, 182, 6, w=312, gap=18, r=5.5, step=100, rot=-1, pad=8, tab="Saved run"),
              s3.stocks(294, 244, 4, 5, "Team stocks"), kpill(440, 242, KEYS2[0], -2), kpill(446, 271, KEYS2[1], 1.5), s3.locktag(296, 304, -2)]
        line = "Pick up at act 2, fight 2 with the saved party."
        h = [("Up / Down", "Choose"), ("A", "Continue run"), ("B", "Main menu"), ("P2: hold B", "Leave")]
    else:
        p += [trail(290, 182, 0, w=312, gap=18, r=5.5, step=100, rot=-1, pad=8, tab="A full run").replace(f"background:{SUN};", "background:#fff;"),
              s3.stocks(294, 244, 4, 4, "Solo stocks")]
        line = "Three acts. Each is 3 fights, a rest stop, then a boss."
        h = [("Up / Down", "Choose"), ("A", "Start run"), ("B", "Main menu")]
    return frame("".join(p + [say(line), H(*h)]))


# ------------------------------------------------------------------ 3. the keystone pick (K1)
def keystone(pick=1, names=("Plague Bearer", "Glass Core", "Long Fuse"), held=(), hov=0):
    p = [s4.bg_key(), ttl("Choose a keystone", 16, 2), s4.sockets(444, 12, pick - 1, pick)]
    sub = "One rule for the whole run. The party shares it." if pick == 1 else "One more rule, on top of what the party holds."
    p.append(at(22, 36, f'<div class="wt">{sub}</div>'))
    p += [kpill(446 + i * 0, 38 + i * 27, k) for i, k in enumerate(held)]
    for i, k in enumerate(names):
        on = i == hov
        p.append(s4.wedge(28 + i * 199, 106 + (0 if i == 1 else 12) - (8 if on else 0), k, rot=0 if on else (-4, 0, 4)[i], hov=on))
    p.append(curd(28 + hov * 199 + 16, 62, 1))
    if pick == 1:
        p += [say("Burning foes set fire to others close by. Nobody has a fire drive yet."), H(("Left / Right", "Choose"), ("A", "Take it"), ("B", "Back to camp"))]
    else:
        p += [say("Each drive fires a second time at half strength. It stacks with Plague Bearer."), H(("Left / Right", "Choose"), ("A", "Take it"))]
    return frame("".join(p))


# ------------------------------------------------------------------ 4. the map (N2)
s6.PARTY[:] = MID
s6.NEXT["mid"].update(win="One of its two drives, then your pick of three.", then="After this: a shift room, then the rest stop.", coins=23, keys=KEYS2, pool=(4, 5))
s6.nhints = lambda I: H(("A", I["a"]), ("Y", "Read your drives"), ("Start", "Pause"))


def _status(x, y, I, wide=True):
    left, total = I["pool"]
    return (s3.stocks(x, y, left, total, "Solo stocks" if I.get("solo") else "Team stocks", rot=-1.5) + s6.purse(x + 142, y + 2, I["coins"], note="Coins" if I.get("solo") else "Coins, one purse")
            + "".join(kpill(x + 2 + (i % 2) * 142, y + 62 + (i // 2) * 28, k, (-1.5, 1.2, -1)[i]) for i, k in enumerate(I["keys"])))


s6.status = _status


def map_(state="mid"):
    return s6.n2(state)


# ------------------------------------------------------------------ 5 and 8. the fight HUD (H2 + M1)
def plr(p, **kw):
    base = {
        1: dict(p=1, name="Fighter A", kind=0, dmg=87, heat=78, row=[("Ember", 2, .8), ("Bolt", 1, .45), ("Echo", 1, .2)], active=("bolt", 1, 3),
                bench=("Fighter B", 1, 34, [])),
        2: dict(p=2, name="Fighter C", kind=3, dmg=41, heat=38, row=[("Frost", 1, .55), ("Clean Landing", 2, .3), ("Mirror", 1, .7), ("Tailwind", 1, .15)], active=("wind", 1, 2),
                bench=("Fighter D", 5, 112, [])),
    }[p]
    base = dict(base)
    base.update(kw)
    return base


ELITE = dict(k="elite", dmg=62, dr=("Wildfire", "Frost"), burn=2)


def fight(**kw):
    args = dict(P1=plr(1), P2=plr(2), fs=[ELITE])
    args.update(kw)
    return s5.screen("h2", **args)


def boss():
    cx = 320
    world = (s5.actor(cx - 74, s5.FLOOR, 0, "p1", orb=["fire", "bolt", "util"], ready=[0], heat="blaze") + s5.actor(cx + 128, 232, 3, "p2", orb=["frost", "tech", "util", "wind"], heat="hot")
             + s5.actor(cx + 46, s5.FLOOR, 5, "foe", w=84))
    return fight(P1=plr(1, dmg=64, heat=126, row=[("Ember", 2, 1), ("Bolt", 1, .7), ("Echo", 1, .35)], active=("bolt", 3, 3)), P2=plr(2, dmg=98, heat=71), fs=[], boss=(.62, 1, False), n=31, pool=(3, 5),
                 world=world).replace('<span class="nt">Boss</span>', '<span class="nt">Boss 2</span>')


def over(fz, inner):
    return fz[:-6] + f'<div style="position:absolute;left:0;top:0;width:640px;height:480px;background:rgba(26,16,74,.86)"></div>{inner}</div>'


# ------------------------------------------------------------------ 6. the pick of three (R2)
OFFERS = {1: ["Bolt", "Shatter", "Tailwind"], 2: ["Echo", "Shatter", "Perfect Form"]}
NSLOT = 4


def fighters_of(p):
    return [(nm, k, ch) for pp, nm, k, ch in MID if pp == p]


def pick_side(p, st, x0, n=NSLOT):
    mode, i, h = st.get("m", "hover"), st.get("i", 0), st.get("h", 0)
    F = fighters_of(p)
    d = OFFERS[p][i]
    own = next(((j, l) for j, (_, _, ch) in enumerate(F) for dd, l in ch if dd == d), None)
    j = st.get("j")
    if j is None:
        j = own[0] if own else next((q for q, f in enumerate(F) if len(f[2]) < n), 0)
    name, chips = F[j][0], F[j][2]
    is_up = bool(own) and own[0] == j
    full = not is_up and len(chips) >= n
    slot = None if is_up else (h + 1 if (full and mode == "rep") else (None if full else len(chips) + 1))
    other = 2 if p == 1 else 1
    col = CORAL if p == 1 else LAGOON
    if mode == "skip":
        line = "Take nothing this time."
    elif mode == "rep":
        line = f"Replace {chips[h][0]} with {d} for good?"
    elif mode == "who":
        line = f"Who wears {d}? {name}'s row is full." if full else (f"Who wears {d}? Level up on {name}." if is_up else f"Who wears {d}? {name}, slot {slot}.")
    elif mode == "done":
        line = f"{d} is on {name}. Waiting for P{other}."
    elif mode == "auto":
        line = f"3 seconds left: {OFFERS[p][0]} will be taken."
    elif is_up:
        line = f"{name}'s {d} goes up to level {own[1] + 1}."
    elif full:
        line = f"{name}'s row is full. A picks a slot."
    else:
        line = f"{d} goes to {name}, slot {slot}."
    out, x = "", x0 + 30
    for k in range(3):
        dk = OFFERS[p][k]
        ok = next(((jj, l) for jj, (_, _, ch) in enumerate(F) for dd, l in ch if dd == dk), None)
        kw = dict(lvl=ok[1] + 1, up=F[ok[0]][0]) if ok else {}
        sel = k == i and mode != "skip"
        if mode == "auto" and k == 0:
            kw["flag"] = "Taken at 0"
        elif sel and full and not ok and mode in ("hover", "who"):
            kw["flag"] = "Row full"
        if sel and slot and mode != "done":
            kw["slot"] = slot
        out += d2(x, 44 + k * 78, dk, rot=0 if sel else (-.5, .4, -.3)[k], cls="hov" if sel else ("faded" if mode in ("who", "rep", "done") else ""), **kw)
    if mode in ("hover", "auto"):
        out += ptr(x0 + 2, 44 + i * 78 + 22, col)
    if mode != "done":
        out += f'<div class="skp{" on" if mode == "skip" else ""}" style="left:{x + 2}px;top:278px;width:84px;height:26px;line-height:19px;transform:rotate(-1.5deg)">Skip</div>'
        if mode == "skip":
            out += ptr(x0 + 2, 278, col)
    for q, (nm, kind, ch) in enumerate(F):
        cs = list(ch)
        pv, extra = None, ""
        if q == j and mode in ("hover", "who", "auto") and not full:
            pv = ("up", d) if is_up else ("new", d)
        if q == j and mode == "done":
            cs = [(dd, l + 1) if (is_up and dd == d) else (dd, l) for dd, l in cs] + ([] if is_up else [(d, 1)])
        if q == j and mode == "rep":
            extra = s6.chip_ring(h)
        out += fst(x + q * 144, 312, p, nm, kind, cs, n=n, v=True, cls="on" if (mode in ("who", "rep") and q == j) else "", prev=pv, rot=(-.6, .5)[q], tab=q == 0, extra=extra)
    if mode == "who":
        out += curd(x + j * 144 + 86, 288, p)
    if mode == "rep":
        out += cur(x + j * 144 + 4 + 26 * h + 15, 312 + 54, p)
    out += f'<div class="strip" style="left:{x - 6}px">{line}</div>'
    return out


def pick(a, b=None, t=14):
    solo = b is None
    p = [s4.bg_reward("none" if solo else "halves")]
    if solo:
        p.append(pick_side(1, a, 163))
    else:
        p += [f'<div class="pp" style="left:30px;top:10px;background:{CORAL};transform:rotate(-4deg)">P1</div>',
              f'<div class="pp" style="left:572px;top:10px;background:{LAGOON};transform:rotate(4deg)">P2</div>', pick_side(1, a, 0), pick_side(2, b, 320)]
    p += [at(0, 0, ttl("Pick a drive", 222, 0), "z-index:5"), s4.timer(372, 2, t, t <= 5), H(("Stick", "Choose"), ("A", "Take"), ("B", "Back"))]
    return frame("".join(p))


# ------------------------------------------------------------------ 7. the rest stop (S1)
SHOP = [("d", "Ember", 40), ("d", "Shatter", 80), ("d", "Perfect Form", 150), ("act", "Volley, an active", 80), ("lv", "Level up a drive", 60), ("stock", "Restore a stock", 50),
        ("roll", "Swap the drives on sale", 10), ("order", "Reorder drives", None), ("pact", "Pact: Echo for a stock", None), ("leave", "Back on the road", None)]
GAPS = (2, 3, 5, 7, 8)   # a small gap after these rows groups the list


def shop_row(x, y, w, it, coins, on, fade, rot):
    k, lab, pr = it
    cls = ("on " if on else "") + ("fd " if fade and not on else "") + ("ink " if k == "pact" else "") + ("no " if pr and pr > coins else "")
    icon = pog(DR[lab][0], 21, DR[lab][1], sq=False) if k == "d" else (pog("bolt", 21, 0, sq=True) if k == "act" else "")
    val = s6.price(pr) if pr else ("1 stock" if k == "pact" else ("free" if k == "order" else ""))
    return s6.srow(x, y, w, lab, val, cls, 0 if on else rot, icon, vs=(k == "order"))


def rowbig(x, y, name, chips, held, n):
    pitch, cw = (76, 70) if n <= 4 else (64, 62)
    w = 18 + n * pitch
    cells = ""
    for i in range(n):
        cx = 10 + i * pitch
        if i < len(chips):
            d, l = chips[i]
            hh = i == held
            arrows = ""
            if hh:
                tri = lambda fl: svg(11, 14, "0 0 11 14", f'<path d="{"M9,2 L2,7 L9,12Z" if fl else "M2,2 L9,7 L2,12Z"}" fill="{CORAL}" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>')
                arrows = at(-9, 12, tri(True)) + at(cw - 2, 12, tri(False))
            short = d if len(d) < 11 or n <= 4 else d.split(" ")[0]
            cells += (f'<div class="slotc{" h" if hh else ""}" style="left:{cx}px;top:{22 if hh else 27}px;width:{cw}px">{pog(DR[d][0], 32, DR[d][1], sq=False)}'
                      f'<div class="s10" style="margin-top:1px">{short}</div>{arrows}</div>')
        else:
            cells += (f'<div class="slotc" style="left:{cx}px;top:27px;width:{cw}px">' + svg(32, 32, "-16 -16 32 32", f'<circle r="12" fill="none" stroke="{LILAC}" stroke-width="2.2" stroke-dasharray="4 3.4"/>')
                      + '<div class="s10" style="margin-top:1px;color:#5A4C99">Empty</div></div>')
        cells += f'<span class="s10" style="position:absolute;left:{cx + 3}px;top:84px;color:#5A4C99">Slot {i + 1}</span>'
    return (f'<div class="st" style="left:{x}px;top:{y}px;width:{w}px;height:102px;z-index:4"><div style="position:absolute;left:10px;top:4px;display:flex;gap:10px;align-items:baseline">'
            f'<span class="t14">{name}\'s row</span><span class="t12">fires left to right</span></div>{cells}</div>')


def rest(state="shop", coins=96, data=MID, n=NSLOT):
    hov = {"shop": 1, "buy": 1, "poor": 2, "order": 7, "pact": 8}[state]
    p = [s6.bg_rest(), ttl("Rest stop", 16, 2, 24), s6.pursepill(160, 4, coins, state == "poor")]
    y = 44
    for i, it in enumerate(SHOP):
        on = i == hov
        p.append(shop_row(40 if on else 30, y, 238, it, coins, on, state in ("buy", "order"), (-.8, .7, -.6, .8, -.7, .6, -.8, .7, -.6, .7)[i]))
        if on and state not in ("buy", "order"):
            p.append(ptr(8, y + 1))
        y += 31 + (5 if i in GAPS else 0)
    px, py = 300, 146
    kw = {}
    if state == "buy":
        kw = dict(on=1, pj=1, prev=("new", "Shatter"))
        p += [curd(px + 146 + 88, py - 24, 1), d2(296, 50, "Shatter", slot=3, cls="hov")]
    elif state == "order":
        kw = dict(on=0, extra={0: s6.chip_ring(1)})
        p.append(rowbig(296, 34, "Fighter A", data[0][3], 1, n))
    elif state == "poor":
        p.append(d2(296, 50, "Perfect Form", flag="54 short"))
    else:
        p.append(d2(296, 50, "Shatter"))
    p.append(party(px, py, data, n, **kw))
    p.append(s3.stocks(302, 330, 4, 5, "Team stocks", rot=-1.5))
    if state == "pact":
        return frame("".join(p + [s6.pact_dlg(132, 132), zi(H(("Left / Right", "Choose"), ("A", "Keep the stock"), ("B", "Keep the stock")))]))
    line, h = {
        "shop": ("Buy Shatter for 80 coins. You choose who wears it next.", [("Up / Down", "Choose"), ("A", "Buy"), ("Y", "Read your drives"), ("Start", "Pause")]),
        "buy": ("Who wears Shatter? Fighter B, slot 3.", [("Stick", "Choose a fighter"), ("A", "Pay 80 coins"), ("B", "Back")]),
        "poor": ("Perfect Form costs 150 coins. The purse has 96.", [("Up / Down", "Choose"), ("Y", "Read your drives"), ("Start", "Pause")]),
        "order": ("Holding Bolt. Move it left or right, then put it down.", [("Left / Right", "Move Bolt"), ("A", "Put it down"), ("B", "Back")]),
    }[state]
    return frame("".join(p + [say(line), H(*h)]))


# ------------------------------------------------------------------ 9. results
def unl(x, y, w, kind, inner, rot=0, dash=False):
    return s6.unl(x, y, w, kind, inner, rot, dash)


def results(clear=True):
    name = lambda t: f'<span class="bn" style="font-size:14px;line-height:16px">{t}</span>'
    both = lambda a, b: (f'<span class="cy2"><span class="pt" style="background:{CORAL}">P1</span>{a}</span> <span class="cy2" style="margin-left:3px"><span class="pt" style="background:{LAGOON}">P2</span>{b}</span>')
    if clear:
        data, n, pos, kn = END, 5, 15, KEYS3
        head, sub, t = "Run cleared!", "All three acts, with 2 of 5 stocks to spare.", "41:36"
        nums = [("Drives fired", "388"), ("Longest chain", "4 drives"), ("Coins earned", both(212, 187)), ("Stocks lost", "7")]
        ng = "".join(f'<i class="{c}">{i}</i>' for i, c in ((0, ""), (1, "n"), (2, "x"), (3, "x")))
        un = (unl(16, 322, 124, "New fighter", f'<div style="height:28px;overflow:hidden">{sil(4, 20)}</div>{name("Fighter N")}', -1)
              + unl(152, 324, 132, "New drive", f'{pog("fire", 26, 2, sq=False)}{name("Wildfire")}', 1)
              + unl(296, 322, 150, "New keystone", f'{kem("Echo Oath", 28)}{name("Echo Oath")}', -.8)
              + unl(458, 324, 164, "NG+ level 1 is open", f'<div class="ld">{ng}</div>', 1))
        line = "Four new things are waiting at camp, and a harder run."
    else:
        data, n, pos, kn = MID, 4, 6, KEYS2
        head, sub, t = "The run ended", "Act 2, fight 2: the elite on Stage 6 took the last stock.", "24:10"
        nums = [("Drives fired", "212"), ("Longest chain", "3 drives"), ("Coins earned", both(96, 71)), ("Stocks lost", "6")]
        un = (unl(16, 322, 132, "New drive", f'{pog("fire", 26, 2, sq=False)}{name("Wildfire")}', -1)
              + unl(160, 324, 256, "Still locked", f'{lock(15, LILAC)}<span class="b13" style="color:#5A4C99">Fighter J opens when you beat act 2.</span>', 1, True))
        line = "Wildfire can now turn up in any run."
    p = [s6.bg_res(clear), ttl(head, 16, 0, 30), at(22, 38, f'<div class="wt" style="font-size:13px;line-height:16px">{sub}</div>'),
         f'<div class="st" style="left:534px;top:6px;width:88px;height:46px;transform:rotate(3deg);padding:4px 9px"><div class="s10">Time</div><div class="bn" style="font-size:20px;line-height:22px">{t}</div></div>',
         trail(16, 62, pos, lost=not clear, stamp=clear, rot=-.3), party(18, 122, data, n, cols=4, dx=152)]
    p += [kpill(18, 212 + i * 27, k, (-1.5, 1.2, -1)[i]) for i, k in enumerate(kn)]
    xs, ws = (166, 270, 378, 532), (96, 100, 146, 88)
    for i, (l, v) in enumerate(nums):
        p.append(f'<div class="num" style="left:{xs[i]}px;top:216px;width:{ws[i]}px;height:48px;transform:rotate({(-.8, .7, -.6, .8)[i]}deg)"><div class="s10">{l}</div><div class="bn"{" style=font-size:15px" if i == 2 else ""}>{v}</div></div>')
    p.append(ttl("Unlocked", 14, 293, 17))
    return frame("".join(p + [un, say(line), H(("A", "Back to camp"))]))


# ------------------------------------------------------------------ 10. pause, and the Second Wind offer
def pause(state="menu", data=MID, n=NSLOT, kn=KEYS2):
    read = state == "read"
    p = [ttl("Paused", 16, 2, 24), at(118, 12, f'<span class="pt" style="background:{LAGOON};font-size:12.5px;line-height:16px;transform:rotate(-3deg)">P2 paused</span>')]
    rows = [("Resume", "", "big"), ("Read drives", "", ""), ("Quit to camp", "the run is kept", "")]
    y = 46
    for i, (lab, v, c) in enumerate(rows):
        on = (i == 1) if read else (i == 0)
        fd = read and not on
        p.append(s6.srow(40 if (on and not read) else 30, y, 230, lab, v, c + (" on" if on else "") + (" fd" if fd else ""), 0 if on else (-.8, .7, -.6)[i], vs=True))
        if on and not read:
            p.append(ptr(8, y + 10, LAGOON))
        y += 58 if c == "big" else 34
    line = lambda d, t: f'<div style="display:flex;align-items:center;gap:7px;height:22px">{dpad(d, 17)}<span class="b13" style="white-space:nowrap">{t}</span></div>'
    p.append(f'<div class="st" style="left:28px;top:186px;width:236px;height:82px;transform:rotate(-1deg);padding:6px 10px"><div class="t14" style="margin-bottom:3px">The D-pad in a fight</div>'
             f'{line("down", "Down: tag in your other fighter")}{line("right", "Right: fire your active drive")}</div>')
    kw = dict(on=2, extra={2: s6.chip_ring(1)}) if read else {}
    p.append(party(300, 44, data, n, dy=86, **kw))
    p += [s6.kslab(298, 220 + i * 50, k, (-.5, .5, -.4)[i]) for i, k in enumerate(kn)]
    if read:
        p += [cur(300 + 4 + 26 + 15, 44 + 86 + 54, 2), d2(6, 284, "Clean Landing", 2, cls="hov"),
              say("Clean Landing, level 2, in Fighter C's slot 2."), H(("Stick", "Choose a drive"), ("B", "Back"), ("Start", "Resume"))]
    else:
        p += [say("Back to the fight. Either player can pause."), H(("Up / Down", "Choose"), ("A", "Resume"), ("Start", "Resume"))]
    return over(fight(), "".join(p))


def second_wind():
    d = (f'<div class="st" style="left:128px;top:124px;width:384px;height:192px;transform:rotate(-1deg);padding:10px 16px;z-index:8">'
         f'<div class="hl" style="font-size:25px;line-height:28px">Use your Second Wind?</div>'
         f'<div class="sub" style="font-size:13px;line-height:16.5px;margin-top:4px">The stock pool is empty. Once a run the party can get back up with one stock and carry on with this fight.</div>'
         f'<div class="t12" style="margin-top:6px">Say no and the run ends here.</div>'
         f'<div class="db on" style="left:16px;top:140px;width:168px">Use Second Wind</div><div class="db" style="left:200px;top:140px;width:168px">End the run</div>{ptr(-14, 144)}'
         f'{at(326, -26, burst("Once|a run", CORAL, 64, 13), "z-index:9")}</div>')
    return over(fight(P1=plr(1, dmg=143, heat=18), P2=plr(2, dmg=121, heat=9), fs=[dict(ELITE, dmg=88)], pool=(0, 5)),
                d + zi(H(("Left / Right", "Choose"), ("A", "Use Second Wind"))))


# ------------------------------------------------------------------ every screen, by file name
def screens():
    global HUDKEYS
    S = {}
    S["menu"] = menu("saved")
    S["menu-no-run"] = menu("new")
    S["menu-cleared"] = menu("done")
    S["menu-no-disc"] = menu("miss")
    S["camp"] = camp("main")
    S["camp-first-time"] = camp("first")
    S["keystone"] = keystone(1)
    S["keystone-after-boss"] = keystone(2, ("Echo Oath", "Winter Oath", "Grand Finale"), KEYS1)
    S["map"] = map_("mid")
    S["fight"] = fight()
    S["pick"] = pick(dict(i=0), dict(i=0))
    S["pick-row-full"] = pick(dict(m="done", i=0), dict(m="rep", i=1, j=0, h=3), 9)
    S["pick-solo"] = pick(dict(i=1))
    S["rest"] = rest("shop")
    S["rest-buying"] = rest("buy")
    S["rest-reorder"] = rest("order")
    S["boss"] = boss()
    S["results"] = results(True)
    S["results-lost"] = results(False)
    S["pause"] = pause("menu")
    S["pause-read-drives"] = pause("read")
    S["second-wind"] = second_wind()
    return S


FLOW = [
    ("menu", "Main menu", "the Envoy row, a saved run", "A sixth retail row between Vs. Mode and Trophies. While it is hovered the port draws loose stickers in the space on the right: the saved run, who is in it, what they wear."),
    ("camp", "Camp", "two players, a saved run", "One sticker list, Player 1's cursor. The right side is a status board: the party, the saved run, its stocks, keystones and locked rules. Player 2 joins here or not at all."),
    ("keystone", "Keystone pick", "run start, keystone 1 of 3", "Three grape-ink wedges. Shown at run start and again after bosses 1 and 2; the three seats top right count them."),
    ("map", "Map", "act 2, fight 2 is next, four slots", "The next-up poster says what the next stop is. The run strip on top is a straight path: fight, fight, fight, rest stop, boss."),
    ("fight", "Fight", "act 2, an elite; P1 Hot, P2 Warm", "Each player owns a bottom corner: percent, drive row, active drive, Heat bar, bench sticker. Stocks, coins and keystones sit between; foes along the top. No Heat digits."),
    ("pick", "Pick of three", "after the fight, both choosing", "Split down a paper seam: a list of three and a Skip for each player, their two fighters under it, and a strip that says what A does."),
    ("rest", "Rest stop", "act 2, before the boss", "One counter list, one cursor. The hovered drive shows its full tag over all four fighters. This is the only place drives are reordered."),
    ("boss", "Boss fight", "boss 2, one break done; P1 Blazing", "The same HUD. The boss bar takes the top and is cut in quarters; each quarter is a break, and a break is a cash-out."),
    ("results", "Results", "the run cleared, five slots, three keystones", "How far, the time, the final rows and keystones, four numbers, what unlocked, and one button."),
    ("pause", "Pause", "Start, in any fight", "Resume, Read drives, Quit to camp. The rows, the keystones with their rules and the two D-pad buttons are always showing."),
]
CONN = [("A", "Open the camp", ""), ("A", "New run", "Continue run goes straight to the map"), ("A", "Take it", ""), ("A", "Start the fight", ""),
        ("", "The last foe is KO'd", "no button"), ("A", "Take", "then the map; after three fights, A: Go in"), ("A", "Back on the road", "then the map, A: Fight the boss"),
        ("", "Boss 3 falls, or the last stock goes", "after bosses 1 and 2: pick of three, keystone, map"), ("Start", "Pause", "not a step: any time in a fight. From Results, A goes back to the camp")]
STATES = [
    ("menu-no-run", "Main menu: no run yet", "A opens the camp. The stickers say what a run is."),
    ("menu-cleared", "Main menu: run cleared", "A Cleared stamp on the punch card and the next NG+ level."),
    ("menu-no-disc", "Main menu: Brawl disc missing", "The row carries the no-disc mark; A shows the same three steps and the camp never loads."),
    ("camp-first-time", "Camp: first time, solo", "No save, one player, four stocks. The P2 slot says how to join: Start on controller 2."),
    ("keystone-after-boss", "Keystone pick: after boss 1", "One seat filled. The held keystone is named under the seats; there is no B."),
    ("pick-row-full", "Pick of three: the row is full", "P2 took Shatter for Fighter C, whose four slots are full, so the cursor walks the row to choose what it replaces. B goes back, and Skip is still there."),
    ("pick-solo", "Pick of three: solo", "The same stickers, centred. Shown: a level-up, marked from the moment it is offered."),
    ("rest-buying", "Rest stop: who wears it", "After A the list fades and the same cursor goes to the four fighters. A pays."),
    ("rest-reorder", "Rest stop: reordering", "Reorder drives, then a fighter. The row opens big and the held drive moves left and right."),
    ("second-wind", "Fight: the Second Wind offer", "The pool is empty: the fight freezes and asks once a run. Yes gives one stock and the same fight carries on."),
    ("results-lost", "Results: the run ended", "Same parts, same places. The strip marks where it stopped; a locked unlock says what opens it."),
    ("pause-read-drives", "Pause: Read drives", "The cursor walks any fighter's chips and the drive's full tag opens on the left. Y on the map and at the rest stop opens this."),
]


# ------------------------------------------------------------------ the sheet
def shot(inner, zoom, label=None, cap=None):
    lab = f'<div class="tag">{label}</div>' if label else ""
    c = f'<p class="cap" style="max-width:{640 * zoom:.0f}px">{cap}</p>' if cap else ""
    return f'<div>{lab}<div style="width:{640 * zoom:.0f}px;height:{480 * zoom:.0f}px;border-radius:8px;overflow:hidden"><div class="g" style="zoom:{zoom}">{inner}</div></div>{c}</div>'


def kb(b):
    return f'<span class="kb">{b}</span>' if b else ""


def flow_html(S):
    out = ""
    for r in range(5):
        a, b = FLOW[2 * r], FLOW[2 * r + 1]
        cell = lambda i, f: (f'<div class="fw"><h3><i>{i}</i>{f[1]}<span>{f[2]}</span></h3>{shot(S[f[0]], 1.1)}<p class="cap">{f[3]}</p></div>')
        bt_, t, e = CONN[2 * r]
        dash = ' stroke-dasharray="5 6"' if r == 4 else ""
        arrow = svg(112, 22, "0 0 112 22", f'<path d="M8,11 H96" stroke="#1A1830" stroke-width="2.5" stroke-linecap="round"{dash}/><path d="M92,4 L104,11 L92,18Z" fill="#1A1830"/>')
        conn = f'<div class="conn">{arrow}<div class="cl">{kb(bt_)}{t}{"<em>" + e + "</em>" if e else ""}</div></div>'
        out += f'<div class="fl2">{cell(2 * r + 1, a)}{conn}{cell(2 * r + 2, b)}</div>'
        if r < 4:
            bt_, t, e = CONN[2 * r + 1]
            path = svg(1520, 78, "0 0 1520 78", '<path d="M1168,0 V34 H352 V64" fill="none" stroke="#1A1830" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/><path d="M345,60 L352,74 L359,60Z" fill="#1A1830"/>')
            out += f'<div class="turn">{path}<div class="cl">{kb(bt_)}{t}{"<em>" + e + "</em>" if e else ""}</div></div>'
    return out


def lb(x, y, t, q=False):
    return f'<div class="lb{" q" if q else ""}" style="left:{x}px;top:{y}px">{t}</div>'


def pn(title, note, w, h, inner, zoom=1.2, wide=False, dark=False):
    return (f'<div class="pn{" w" if wide else ""}"><h3>{title}</h3><p>{note}</p><div class="pb{" dk" if dark else ""}" style="width:{w * zoom:.0f}px;height:{h * zoom:.0f}px">'
            f'<div class="g" style="zoom:{zoom};width:{w}px;height:{h}px">{inner}</div></div></div>')


def parts_html():
    P = []
    # colours
    sw = [("#FFD84A", "Sunny", "the cursor, a hovered sticker, ready, keystone names"), ("#2A1A6E", "Grape ink", "every outline and hard shadow, text, foe and keystone faces"),
          ("#FFFFFF", "White", "sticker faces: anything that is ours"), ("#FF4D6D", "Coral", "Player 1, the last stock, stamps and flags"),
          ("#00A99D", "Lagoon", "Player 2"), ("#5A4C99", "Lilac", "quiet text on white"), ("#C9BFF5", "Pale lilac", "quiet text on ink and violet, dashed seats"),
          ("#C2183F", "Deep coral", "a price the purse cannot pay"), ("#4C3D9E", "Paper violet", "scenery base. Also #43348F, #33257C, #3A2B86, #2C1E70, #5849AE, #6253B6. Never outlined"),
          ("#DAD7E8", "Faded sticker", "done, locked or disabled faces"), ("#FBF6DD", "Cream, dashed", "an empty seat a player can fill"), ("#170E45", "Heat track", "the empty part of a bar"),
          ("#B9B2DE", "Cold", "Heat under 25"), ("#FFBE2E", "Warm", "Heat 25 and up"), ("#FF8A1F", "Hot", "Heat 60 and up"), ("#FF4A1C", "Blazing", "Heat 110 and up")]
    P.append('<div class="pn w"><h3>Colours</h3><p>Flat fills only. The one gradient in the kit is the Epic foil rim: #FF8FB8, #FFE066, #8CF0C8, #7FD4FF, #C9A0FF, #FFB27A at 135 degrees.</p><div class="sw">'
             + "".join(f'<div><i style="background:{c}"></i><span><b>{n} {c}</b>{r}</span></div>' for c, n, r in sw) + "</div></div>")
    # type
    ty = [(ttl("Run cleared!", 0, 0, 30).replace("position:absolute;", ""), "Screen title, results: Bricolage 800, 30, white with a 4.5 ink edge", 44),
          (ttl("Rest stop", 0, 0, 24).replace("position:absolute;", ""), "Screen title: Bricolage 800, 24 (21 on the pick of three)", 38),
          ('<span class="hl">Continue run</span>', "Sticker headline: Bricolage 800, 22 to 28, tracking -0.6", 34),
          ('<span class="nm">Clean Landing</span>', "Drive name: Bricolage 800, 16", 24),
          ('<span class="t14">Fighter A</span>', "Fighter name, row label: Bricolage 800, 14 to 15", 24),
          ('<span class="fx" style="font-size:13px;color:#fff">Buy Shatter for 80 coins.</span>', "Strip and body: Source Sans 3 700, 13", 22),
          ('<span class="fx" style="color:#fff"><b>Every 35% you deal:</b> your next hit breaks.</span>', "Tag text: Source Sans 3 700, 11.5; the charge in Bricolage 800", 22),
          ('<span class="s10" style="color:#C9BFF5">Team stocks</span>', "Smallest label: Source Sans 3 700, 11. Nothing is smaller", 20)]
    y, inner = 10, ""
    for h_, t, hh in ty:
        inner += f'<div class="ty" style="top:{y}px"><div style="width:216px;color:#fff">{h_}</div>{lb(0, 0, t, True)}</div>'
        y += hh
    inner += at(14, y + 4, s5.dmg(87, 40)) + lb(244, y + 22, "Percent: Bricolage 800, 40, the sign at 20; white, 8 ink edge", True)
    P.append(pn("Type", "Two families. Bricolage Grotesque 800 for names, numbers and headlines; Source Sans 3 700 for sentences and labels. Sentence case everywhere.", 590, y + 66, inner))
    # families
    fam = ["fire", "bolt", "frost", "wind", "tech", "util", "stone", "rose"]
    inner = ""
    for i, f in enumerate(fam):
        x, yy = 14 + (i % 4) * 144, 12 + (i // 4) * 74
        inner += at(x, yy, pog(f, 46, 0, sq=False)) + lb(x + 52, yy + 8, FAM[f][0]) + lb(x + 52, yy + 23, FAM[f][1], True)
    P.append(pn("The eight families", "Colour and glyph together, never colour alone. Six are in use; the two spares are drawn so the system is complete. Glyphs are white with an ink edge.", 590, 160, inner))
    # badge
    inner = ""
    for i, (sz, t) in enumerate(((58, "58: the tag"), (32, "32: reorder"), (22, "22: a chip"), (19, "19: HUD row"), (15, "15: in orbit"))):
        x = 14 + (0, 76, 152, 222, 292)[i]
        inner += at(x, 14 + (58 - sz) / 2, pog("fire", sz, 1, sq=False)) + lb(x, 80, t, True)
    for i, r in enumerate(RAR):
        inner += at(376 + i * 70, 14, pog("frost", 58, i, sq=False)) + lb(380 + i * 70, 80, r)
    inner += lb(14, 104, "Level on a tag: three stars. On a chip: three pips.")
    for i in range(3):
        inner += at(14 + i * 66, 122, f'<div class="rib" style="position:static">{s4.stars(i + 1, 11)}</div>')
    inner += at(214, 122, f'<div class="rib" style="position:static">{s4.stars(2, 11, True)}</div>') + lb(214, 146, "a new star", True)
    cx0 = 300
    for i, (c, t) in enumerate(((s4.chip("Ember", 1), "level 1"), (s4.chip("Bolt", 2), "level 2"), (s4.chip("Echo", 3), "level 3"), (s4.chip("Frost", 1, "new"), "new"), (s4.chip("Frost", 2, "up"), "level up"), (s4.empty_slot(), "empty"))):
        inner += at(cx0 + i * 48, 116, c) + lb(cx0 + i * 48 - 6, 154, t, True)
    inner += lb(14, 176, "In the HUD row: a charge ring, sunny, clockwise from the top. Fired: a burst behind it for 6 frames.")
    for i, (kw, t) in enumerate(((dict(chg=.2), "20%"), (dict(chg=.6), "60%"), (dict(chg=1), "ready"), (dict(chg=1, fired=True), "fired"), (dict(chg=.5, spark=True), "technique"))):
        inner += at(14 + i * 56, 196, s5.hchip("Ember", 2, kw["chg"], fired=kw.get("fired", False), spark=kw.get("spark", False))) + lb(14 + i * 56, 238, t, True)
    inner += at(318, 196, s5.active(dict(active=("bolt", 1, 3)))) + lb(308, 238, "active, 1 of 3", True) + at(408, 196, s5.active(dict(active=("bolt", 3, 3)))) + lb(398, 238, "active, ready", True)
    P.append(pn("The drive badge", "One round badge at five sizes. Rarity is the edge: Common plain, Rare a thick white die-cut, Epic a foil rim with a spark. The active drive is the same badge cut square.", 590, 258, inner))
    # tag and fighter sticker
    inner = (d2(14, 14, "Shatter") + lb(60, 92, "Idle") + d2(318, 14, "Shatter", slot=3, cls="hov") + lb(364, 92, "Hovered, on its way to slot 3")
             + d2(622, 14, "Ember", 3, up="Fighter A") + lb(668, 92, "A duplicate: Level up") + d2(926, 14, "Perfect Form", flag="Row full", cls="hov") + lb(972, 92, "Flag: Row full, Taken at 0, 54 short"))
    for i, (n_, t) in enumerate(((3, "Fighter sticker: three slots, act 1"), (4, "Four slots, after boss 1"), (5, "Five slots, after boss 2"))):
        inner += fst(14 + i * 200, 124, 2, "Fighter C", 3, END[2][3][:n_ - 1] if i < 2 else END[2][3], n=n_, v=True, tab=i == 0) + lb(14 + i * 200, 212, t)
    inner += fst(614, 124, 1, "Fighter A", 0, MID[0][3], n=4, v=True, cls="on", prev=("new", "Shatter")) + lb(614, 212, "Hovered: where the drive lands")
    inner += fst(814, 124, 2, "Fighter C", 3, MID[2][3], n=4, v=True, cls="on", extra=s6.chip_ring(3)) + lb(814, 212, "Row full: the ring is on what goes")
    P.append(pn("The paper tag and the fighter sticker", "The tag: badge, name, rarity and family in words, the charge in bold as \"Every N% you deal\", what it does, what the next level adds. The fighter sticker is 140 by 80 and holds three, four or five slots at one size.",
                1216, 232, inner, wide=True))
    # keystone
    inner = (s4.wedge(16, 36, "Plague Bearer", rot=-3) + s4.wedge(212, 28, "Glass Core", hov=True) + lb(60, 318, "Idle: tilted 4 degrees") + lb(250, 318, "Hovered: sunny, upright, up 8")
             + s4.sockets(414, 16, 1, 2) + lb(414, 44, "The three seats", True) + kpill(416, 74, "Plague Bearer") + lb(416, 104, "Pill: camp, map, results, menu", True)
             + s6.kslab(416, 134, "Glass Core").replace("width:316px", "width:160px").replace("Everyone deals 30% more and takes 30% more.", "Pause: with its rule") + lb(416, 186, "Slab: 316 wide in the pause", True)
             + at(416, 214, "".join(at(i * 34, 0, kmini(k), "width:32px;height:27px") for i, k in enumerate(KEYS3)), "width:110px;height:30px") + lb(416, 248, "In a fight: emblem only, one to three", True))
    P.append(pn("The keystone", "Grape ink with a white die-cut, cut as a wedge, so it never reads as a drive. A run holds one to three; every screen that shows them stacks or lines up to three.", 590, 338, inner))
    # list rows
    r = lambda y, lab, val="", cls="", icon="", vs=False, x=44: s6.srow(x, y, 238, lab, val, cls, 0, icon, vs)
    inner = (r(12, "Continue run", "", "big on", x=54) + ptr(22, 22) + lb(304, 28, "Hovered, big: sunny, white ring, in 12")
             + r(72, "Run length", "Full, 3 acts", vs=True) + lb(304, 80, "Idle, with its value")
             + r(106, "Shatter", s6.price(80), icon=pog("frost", 21, 1, sq=False)) + lb(304, 114, "With a badge and a price")
             + r(140, "Perfect Form", s6.price(150), "no", icon=pog("tech", 21, 2, sq=False)) + lb(304, 148, "The purse cannot pay: deep coral")
             + r(174, "Reorder drives", "free", "fd", vs=True) + lb(304, 182, "Disabled or not in focus: 36% opacity")
             + r(208, "Pact: Echo for a stock", "1 stock", "ink") + lb(304, 216, "A deal: ink face, white edge")
             + f'<div class="row" style="left:44px;top:242px;width:238px">{"<span class=l>Team attack</span><span class=v>" + s3.switch(True) + "</span>"}</div>' + lb(304, 250, "A switch row (camp)"))
    P.append(pn("The list row", "The one way to choose. 28 px high (46 for the big row), 3 px ink edge, radius 10, hard shadow 3 / 4. Idle rows tilt by under one degree, alternating; the hovered row is straight.", 590, 284, inner))
    # cursors
    inner = (ptr(16, 14) + ptr(60, 14, LAGOON) + lb(100, 20, "List pointer, 28 by 26. Coral is P1, lagoon is P2.")
             + cur(18, 56, 1) + cur(62, 56, 2) + lb(110, 62, "Sticker cursor with the player tag: grids and chips")
             + curd(18, 96, 1) + curd(62, 96, 2) + lb(110, 104, "Pointer from above: wedges and fighter stickers")
             + at(22, 136, svg(30, 30, "-15 -15 30 30", f'<circle r="13" fill="none" stroke="{INK}" stroke-width="5"/><circle r="13" fill="none" stroke="{SUN}" stroke-width="2.6"/>' + f'<g transform="translate(-11 -11)">{pog("wind", 22, 0, sq=False)}</g>'))
             + lb(110, 144, "Chip ring: the drive being read, held or replaced")
             + at(20, 180, f'<div class="st on" style="position:relative;width:64px;height:30px"></div>') + lb(110, 188, "Hovered sticker: sunny face, 3 px white ring, shadow 4 / 6"))
    P.append(pn("Cursors", "One cursor per player and it always wears their colour. P1 holds it on shared screens; P2 has their own on the pick of three.", 590, 226, inner))
    # strip and hints
    inner = (say("Buy Shatter for 80 coins. You choose who wears it next.").replace('class="say"', 'class="say" style="top:14px;left:16px"') + lb(16, 52, "The strip: 30 high, at x 24, y 403, tilted -0.6 degrees. One sentence about the hovered thing.", True)
             + hints(("Up / Down", "Choose"), ("A", "Buy"), ("B", "Back"), ("Y", "Read your drives"), ("Start", "Pause")).replace('class="hints"', 'class="hints" style="top:78px;left:16px"')
             + lb(16, 104, "The hint line: at x 26, y 449. Always in this order: move, A, B, Y, Start.", True)
             + hints(("Left / Right", "Choose"), ("Stick", "Choose"), ("P2: hold B", "Leave")).replace('class="hints"', 'class="hints" style="top:128px;left:16px"')
             + at(18, 160, dpad("down", 22)) + lb(48, 164, "D-pad down: tag") + at(150, 160, dpad("right", 22)) + lb(180, 164, "D-pad right: the active") + at(322, 160, dpad("right", 22, True)) + lb(352, 164, "lit coral when ready"))
    P.append(pn("The description strip and the button hints", "Same strip and same hint line on every screen outside a fight. A is always followed by the words for what it does here; B is always back or the safe answer.", 590, 196, inner))
    # heat
    inner = ""
    HS = [("Cold", dict(heat=12)), ("Warm, from 25", dict(heat=38)), ("Hot, from 60", dict(heat=78)), ("Blazing, from 110", dict(heat=126)),
          ("Gaining: the new piece is white", dict(heat=52, gain=14)), ("Losing: the piece breaks off", dict(heat=64, loss=20)), ("Crossing a mark", dict(heat=63, gain=9, cross=60)),
          ("At the cap, 150", dict(heat=150, full=True)), ("KO: half pays out, half stays", dict(heat=96, cash=True)), ("Cap raised to 250", dict(heat=170, cap=250))]
    for i, (t, kw) in enumerate(HS):
        x, yy = 14 + (i % 3) * 192, 12 + (i // 3) * 54
        inner += at(x, yy, s5.m1(w=122, **kw)) + lb(x, yy + 32, t, True)
    P.append(pn("The Heat bar", "No digits. 122 px is 150 Heat; three marks at 25, 60 and 110; the fill takes the state's colour and the flame at its foot grows a size per state. A raised cap is a longer bar with the marks where they were.",
                590, 232, inner, dark=True))
    # stocks, coins, timer
    inner = (at(16, 18, s5.stockdots(4, 5)) + lb(16, 42, "In a fight: 4 of 5", True) + at(150, 18, s5.stockdots(1, 5)) + lb(150, 42, "The last one is coral", True)
             + at(290, 16, s5.coins(23)) + lb(290, 42, "Coins", True) + at(372, 16, s5.coins(31, True)) + lb(372, 42, "A cash-out lands", True)
             + s3.stocks(16, 70, 4, 5, "Team stocks", rot=-1.5) + lb(16, 130, "On a sticker: in ink", True) + s6.purse(170, 72, 23, note="Coins, one purse") + lb(170, 130, "The purse", True)
             + s6.pursepill(316, 76, 11, True).replace("z-index:4", "") + lb(316, 130, "Short of a price", True)
             + s4.timer(470, 14, 14) + lb(462, 58, "Timer", True) + s4.timer(528, 14, 3, True) + lb(524, 58, "Under 5 s", True))
    P.append(pn("Stock dots, coins, timer", "Stock dots are white, 14 px, with an ink edge; a spent dot shrinks to an ink point; when one is left it turns coral on a sunny burst. Coins are earned per player and land in one purse.", 590, 150, inner, dark=False))
    # stamps
    inner = (at(14, 10, burst("Set!", CORAL, 58, 16)) + at(84, 8, burst("Level|up!", CORAL, 58, 13)) + at(154, 6, burst("Once|a run", CORAL, 64, 13)) + at(230, 6, burst("P2|joined", LAGOON, 64, 13)) + at(306, 12, burst("+1", CORAL, 46, 15))
             + lb(14, 76, "Bursts: 16 points, coral or lagoon, tilted 8 degrees, 3.5 ink edge", True)
             + f'<div class="bn" style="position:absolute;left:400px;top:22px;transform:rotate(-7deg);border:3px solid {CORAL};color:{CORAL};background:#fff;border-radius:8px;font-size:17px;line-height:23px;padding:0 8px">Cleared</div>' + lb(400, 76, "Stamp", True)
             + f'<span class="flagp" style="left:16px;top:104px">Row full</span><span class="flagp" style="left:84px;top:104px">Taken at 0</span><span class="fl" style="left:166px;top:103px">Next</span>'
             + f'<span class="slotp" style="left:216px;top:104px;border:2px solid #fff">Slot 3</span>' + lb(14, 126, "Flags: coral for a warning, ink for a slot", True)
             + f'<span class="pt" style="position:absolute;left:300px;top:102px;background:{CORAL}">P1</span><span class="pt" style="position:absolute;left:334px;top:102px;background:{LAGOON}">P2</span>'
             + f'<div class="pp" style="left:376px;top:98px;background:{CORAL};transform:rotate(-4deg)">P1</div><div class="pp" style="left:426px;top:98px;background:{LAGOON};transform:rotate(4deg)">P2</div>' + lb(300, 126, "Player tags, small and large", True))
    P.append(pn("Bursts, stamps, flags and player tags", "The loud parts, used one at a time: a burst marks a moment that just happened, a flag marks a condition on the sticker it sits on.", 590, 146, inner))
    # trail, foes, boss bar, bench
    names = ("done", "next", "to do", "rest stop", "boss", "lost here")
    marks = "".join(s6.tmark(k, st, 22 + i * 62, 16, 7) for i, (k, st) in enumerate((("duel", "done"), ("duel", "cur"), ("duel", "todo"), ("rest", "todo"), ("boss", "todo"), ("duel", "lost"))))
    inner = (trail(14, 12, 6, w=608) + lb(14, 68, "The run strip: 608 by 46, sunny. An act is fight, fight, fight, rest stop, boss.")
             + f'<div class="st" style="left:14px;top:92px;width:380px;height:38px;background:{SUN}">{svg(374, 32, "0 0 374 32", marks)}</div>'
             + "".join(lb(20 + i * 62, 138, t, True) for i, t in enumerate(names))
             + at(650, 0, s5.foes_row([s5.MIN(18), ELITE], 250, 12)) + lb(650, 68, "Foes: ink plates, white edge. A minion; an elite with its drives and its Burning.")
             + at(580, 78, _bossbar(640, .62, 1).replace('<span class="nt">Boss</span>', '<span class="nt">Boss 2</span>')) + lb(730, 136, "Boss: one bar cut in quarters. Each quarter is a break.", True)
             + at(940, 20, s6.bench_small(("Fighter B", 1, 34, []))) + lb(920, 50, "Bench: head, percent, tag", True) + at(1090, 20, s6.bench_small(("Fighter B", 1, 34, []), .4)) + lb(1080, 50, "Refilling after a tag", True))
    P.append(pn("The run strip, foes, the boss bar and the bench", "White with an ink edge is ours; ink with a white edge is theirs.", 1216, 164, inner, wide=True, dark=True))
    return '<div class="pgrid">' + "".join(P) + "</div>"


def head(title):
    holo = "".join(f'<stop offset="{i / 5:.2f}" stop-color="{c}"/>' for i, c in enumerate(s4.HOLO.split(",")))
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title><style>{CSS}</style></head>'
            f'<body><svg width="0" height="0" style="position:absolute"><defs><linearGradient id="holo" x1="0" y1="0" x2="1" y2="1">{holo}</linearGradient></defs></svg>')


def html(S):
    states = "".join(shot(S[k], .575, n, c) for k, n, c in STATES)
    return head("Envoy UI, final") + f"""<div id="c">
<div id="flowpart">
<div class="top"><h1>Envoy, the whole UI</h1>
<p>The final design: every choice from steps 2 to 6 in one flow, with the steps' disagreements settled. Each screen is 640 by 480 game pixels, shown here at 1.1 times.</p></div>
<div class="key"><span><i style="background:#fff;box-shadow:inset 0 0 0 2.5px {INK}"></i>White with an ink edge: ours.</span>
<span><i style="background:{INK};box-shadow:inset 0 0 0 2.5px #fff"></i>Ink with a white edge: a foe, or a keystone.</span>
<span><i style="background:{SUN};box-shadow:inset 0 0 0 2.5px {INK}"></i>Sunny: the cursor, or something ready.</span>
<span><i style="background:{CORAL};box-shadow:inset 0 0 0 2.5px {INK}"></i>Coral: Player 1.</span>
<span><i style="background:{LAGOON};box-shadow:inset 0 0 0 2.5px {INK}"></i>Lagoon: Player 2.</span>
<span><i style="background:#6F7589"></i>Grey: retail, a placeholder.</span></div>

<div class="sec"><h2>The flow, in play order</h2>
<p class="lede">Ten screens. The line between two says which button takes you on. Between fights there is no character select: fight, pick of three, the keystone pick after a boss, map, fight.</p>
{flow_html(S)}</div>

<div class="sec"><h2>Other states</h2>
<p class="lede">The same screens in the states an implementer will meet next. Every one is also exported alone at 640 by 480 and at twice that.</p>
<div class="row4" style="margin-top:0">{states}</div></div>
</div>

<div id="partspart"><div class="sec" style="margin-bottom:0"><h2>The parts</h2>
<p class="lede">The whole sticker kit. Everything on every screen is one of these. Sizes are game pixels; drawn here at 1.2 times.</p>
{parts_html()}</div>
<p class="foot">Original vector art. Fonts: Bricolage Grotesque, Source Sans 3 (SIL OFL). Retail menu rows are grey placeholders. Fighters, foes, bosses and stages are placeholders with invented names; drive loadouts, prices, coin counts, times and result numbers are made up for the mock.</p></div>
</div></body></html>"""


def screens_html(S):
    return head("Envoy UI, screens") + "".join(f'<div class="g" id="s-{k}" style="width:640px;height:480px;overflow:hidden;margin-bottom:8px">{v}</div>' for k, v in S.items()) + "</body></html>"


CHECK = """() => {
  const out = [];
  document.querySelectorAll('.cs, .fz, .gs').forEach((f) => {
    const id = (f.closest('[id^=s-]') || {}).id || '?';
    const fr = f.getBoundingClientRect(), z = fr.width / 640;
    f.querySelectorAll('.st, .sr, .say, .hints, .strip, .kc, .kq, .dr, .num, .row').forEach(e => {
      const q = e.getBoundingClientRect();
      const l = (q.left - fr.left) / z, r = (q.right - fr.left) / z, t = (q.top - fr.top) / z, b = (q.bottom - fr.top) / z;
      if (l < 2 || r > 638 || t < 0 || b > 478) out.push(`${id}: ${e.className} leaves the frame (${Math.round(l)},${Math.round(t)})-(${Math.round(r)},${Math.round(b)}) ${e.textContent.slice(0, 30)}`);
    });
    f.querySelectorAll('*').forEach(e => { if (e.children.length === 0 && !(e instanceof SVGElement) && e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).display !== 'inline')
      out.push(`${id}: text overflow ${e.className}: ${e.textContent.slice(0, 40)}`); });
    f.querySelectorAll('*').forEach(e => { if (e.children.length === 0 && !(e instanceof SVGElement) && e.textContent.trim()) { const s = parseFloat(getComputedStyle(e).fontSize);
      if (s < 11) out.push(`${id}: text under 11 px (${s}) ${e.className}: ${e.textContent.slice(0, 30)}`); } });
    f.querySelectorAll('text').forEach(e => { const s = parseFloat(e.getAttribute('font-size') || '99'), m = e.getCTM(); const eff = s * (m ? m.a : 1);
      if (eff < 10.9) out.push(`${id}: svg text under 11 px (${eff.toFixed(1)}): ${e.textContent.slice(0, 30)}`); });
  });
  return [...new Set(out)]; }"""


def main():
    S = screens()
    (HERE / "final.html").write_text(html(S), encoding="utf-8")
    (HERE / "final-screens.html").write_text(screens_html(S), encoding="utf-8")
    (HERE / "preview").mkdir(exist_ok=True)
    (HERE / "screens").mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
        page.goto((HERE / "final.html").as_uri())
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(400)
        page.locator("#c").screenshot(path=str(HERE / "preview" / "final-spread.png"), type="png")
        h = page.evaluate("document.getElementById('c').offsetHeight")
        print("spread height", h)
        if h > 7000:
            page.locator("#flowpart").screenshot(path=str(HERE / "preview" / "final-flow.png"), type="png")
            page.locator("#partspart").screenshot(path=str(HERE / "preview" / "final-parts.png"), type="png")
        for scale in (1, 2):
            pg = browser.new_page(viewport={"width": 700, "height": 600}, device_scale_factor=scale)
            pg.goto((HERE / "final-screens.html").as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(400)
            if scale == 1:
                for b in pg.evaluate(CHECK):
                    print(b)
            for k in S:
                pg.locator(f"#s-{k}").screenshot(path=str(HERE / "screens" / f"{k}{'@2x' if scale == 2 else ''}.png"), type="png")
            pg.close()
        browser.close()


if __name__ == "__main__":
    main()
