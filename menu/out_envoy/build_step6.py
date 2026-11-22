#!/usr/bin/env python3
"""Envoy UI, step 6: the screens between and around fights.

The run map / next encounter (N1, N2), the rest stop and its shop (S1, S2), the run results, the
Second Wind offer and the pause screen, plus the step 5 bench revision. Writes step6.html beside this
file and renders preview/step6-between.png (1600 px wide) with headless Chromium, like build_step5.py.
Every mock screen is authored in game pixels (640x480 native) and scaled with CSS zoom. Original
vector art only; fighters, foes, bosses and stages are neutral placeholders with invented names.
Fonts: Bricolage Grotesque and Source Sans 3 (SIL OFL).
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

import build_step3 as s3
import build_step4 as s4
import build_step5 as s5
from build_step2 import svg, star_svg, burst, SUN, INK, WHITE, CORAL, LAGOON, LILAC, FLAME, STAR, BURST
from build_step3 import at, sil, bt, hints, say, ptr, cur, frame, fcard, lock
from build_step4 import pog, d2, fst, curd, ttl, DR, FAM, RAR, kem, KS, BG, BG2
from build_step5 import coin, dpad

HERE = Path(__file__).resolve().parent

CSS = s5.CSS + r"""
.row4{display:grid;grid-template-columns:repeat(4,368px);gap:14px 16px;margin-top:16px}
.row3{display:grid;grid-template-columns:repeat(3,499px);gap:11px}
.rowlab{font-weight:900;font-size:19px;margin:22px 0 0}
.rowlab span{font-weight:600;font-size:15.5px;color:#45425E;margin-left:10px}
.lay .g .fs .hd{margin:0;display:block}
.pz{display:grid;grid-template-columns:640px 448px 1fr;gap:24px;align-items:start}
.bench{display:grid;grid-template-columns:640px 640px;gap:22px;align-items:start}
.md{display:inline-flex;gap:3px;vertical-align:-1px;margin:0 3px}
.md i{width:10px;height:10px;border-radius:50%;background:#fff;border:2px solid #fff;box-sizing:border-box}
.md i.o{background:none;opacity:.55}

/* ---------- game-pixel world: between fights ---------- */
.sr{position:absolute;height:28px;background:#fff;border:3px solid #2A1A6E;border-radius:10px;box-shadow:3px 4px 0 #2A1A6E;display:flex;align-items:center;gap:6px;padding:0 9px 0 8px}
.sr svg{display:block;flex:none}
.sr .l{font-family:"Brico";font-weight:800;font-size:14px;line-height:17px;letter-spacing:-.2px;white-space:nowrap;flex:1}
.sr .v{font-family:"Brico";font-weight:800;font-size:13.5px;line-height:16px;display:flex;align-items:center;gap:3px;white-space:nowrap}
.sr .v.s{font-family:"SS3";font-weight:700;font-size:12px;color:#5A4C99}
.sr.big{height:46px}
.sr.big .l{font-size:22px;line-height:24px;letter-spacing:-.5px}
.sr.ink{background:#2A1A6E;border-color:#fff;box-shadow:0 0 0 2.5px #2A1A6E,3px 5px 0 2.5px #2A1A6E}
.sr.ink .l{color:#FFD84A}
.sr.ink .v{color:#fff}
.sr.ink.on .l,.sr.ink.on .v{color:#2A1A6E}
.sr.no .v{color:#C2183F}
.sr.fd{opacity:.36}
.sr.on .v.s{color:#2A1A6E}
.stop{text-align:center}
.stop svg{display:block;margin:0 auto}
.stop .w{font-family:"Brico";font-weight:800;font-size:13.5px;line-height:15px;letter-spacing:-.2px;white-space:nowrap}
.stop.dn{background:#DAD7E8}
.stop.dn .w{color:#5A4C99}
.fl{position:absolute;background:#FF4D6D;color:#fff;border:2px solid #2A1A6E;border-radius:8px;font-family:"Brico";font-weight:800;font-size:11.5px;line-height:14px;padding:0 6px;white-space:nowrap;z-index:4}
.b13{font-size:12.5px;line-height:15px;font-weight:700;color:#2A1A6E}
.cy{display:flex;align-items:center;gap:4px;white-space:nowrap}
.cy svg{display:block;flex:none}
.cy .bn{font-size:13px;line-height:15px}
.kc{position:absolute;display:flex;align-items:center;gap:8px;background:#2A1A6E;border:2.5px solid #fff;border-radius:12px;box-shadow:0 0 0 2px #2A1A6E,3px 5px 0 2px #2A1A6E;padding:3px 10px 3px 5px;color:#fff}
.kc svg{display:block;flex:none}
.kc .kn{font-size:14px;line-height:16px;white-space:nowrap}
.kc .kr{font-size:11.5px;line-height:13px;white-space:nowrap}
.db{position:absolute;height:34px;border:3px solid #2A1A6E;border-radius:10px;box-shadow:3px 4px 0 #2A1A6E;background:#fff;text-align:center;font-family:"Brico";font-weight:800;font-size:14.5px;line-height:27px;white-space:nowrap;color:#2A1A6E}
.dimx{position:absolute;left:-107px;top:0;width:960px;height:480px;background:rgba(26,16,74,.7);z-index:7}
.num{position:absolute;background:#fff;border:3px solid #2A1A6E;border-radius:11px;box-shadow:3px 4px 0 #2A1A6E;padding:4px 9px 0}
.num .bn{font-size:19px;line-height:21px;letter-spacing:-.4px;white-space:nowrap}
.slotc{position:absolute;width:70px;height:58px;border-radius:9px;text-align:center;padding-top:3px}
.slotc svg{display:block;margin:0 auto}
.slotc.h{background:#FFD84A;box-shadow:0 0 0 2.5px #2A1A6E,2px 4px 0 2.5px #2A1A6E}
.slotc .s10{color:#2A1A6E}
"""

KINDS = {"duel": "Duel", "pack": "Pack", "elite": "Elite", "shift": "Shift room", "rest": "Rest stop", "boss": "Boss"}
# One act is three fights, a rest stop, then the boss. The rest sitting just before the boss is this sheet's assumption.
RUN = [["duel", "pack", "elite", "rest", "boss"], ["pack", "elite", "shift", "rest", "boss"], ["duel", "shift", "elite", "rest", "boss"]]

PARTY = [(1, "Fighter A", 0, [("Ember", 2), ("Bolt", 1), ("Echo", 1)]), (1, "Fighter B", 1, [("Frost", 1), ("Metronome", 2)]),
         (2, "Fighter C", 3, [("Frost", 1), ("Clean Landing", 2), ("Mirror", 1)]), (2, "Fighter D", 5, [("Tailwind", 1), ("Feather Storm", 1)])]
FINAL = [(1, "Fighter A", 0, [("Ember", 3), ("Bolt", 2), ("Echo", 1), ("Wildfire", 1)]), (1, "Fighter B", 1, [("Frost", 2), ("Metronome", 2), ("Shatter", 1)]),
         (2, "Fighter C", 3, [("Frost", 1), ("Clean Landing", 3), ("Mirror", 2), ("Perfect Form", 1)]), (2, "Fighter D", 5, [("Tailwind", 2), ("Feather Storm", 2), ("Ember", 1)])]

NEXT = {
    "mid": dict(pos=6, sub="Act 2, fight 2 of 3", name="Fighter K", where="on Stage 6", fk=4, carries=["Wildfire", "Frost"],
                win="One of its two drives, then your pick of three.", win1="one of its drives and a pick of three.", then="After this: a shift room, then the rest stop.",
                say="An elite: a strong fighter with two drives of its own.", a="Start the fight", pool=(4, 5), coins=23, keys=["Plague Bearer", "Glass Core"]),
    "start": dict(pos=0, sub="Act 1, fight 1 of 3", name="Fighter H", where="on Stage 1", fk=1, note="One fighter, no drives.",
                  win="Your pick of three drives.", win1="your pick of three drives.", then="After this: a pack, then an elite.",
                  say="The first fight of the run. One fighter, nothing extra.", a="Start the fight", pool=(5, 5), coins=0, keys=["Plague Bearer"], empty=True),
    "boss": dict(pos=9, sub="Act 2, the boss", name="Boss 2", where="in the Cage arena", fk=5, note="A big one. Its bar breaks four times.",
                 win="A new keystone, then act 3.", win1="a new keystone, then act 3.", then="No rest stop until act 3.",
                 say="The act 2 boss. Beat it and the party takes a third keystone.", a="Fight the boss", pool=(3, 5), coins=9, keys=["Plague Bearer", "Glass Core"]),
    "rest": dict(pos=8, sub="Act 2, once an act", name="No fight here", where="A shop and a breather", fk=None, note="Buy or level a drive, restore a stock, reorder a row.", note1="Buy or level a drive, restore a stock.",
                 win="", then="After this: the act 2 boss.",
                 say="A rest stop: spend coins, reorder drives, then on to the boss.", a="Go in", pool=(3, 5), coins=38, keys=["Plague Bearer", "Glass Core"]),
}
NEXT["solo"] = dict(NEXT["mid"], pool=(3, 4), solo=True)


# ------------------------------------------------------------------ small parts
def fig(k, s, dx, dy, fill="#BFC2CE"):
    body, head = s3.SILS[k % 6]
    return (f'<g transform="translate({dx} {dy}) scale({s})" fill="{fill}" stroke="{INK}" stroke-width="{2.5 / s:.1f}" stroke-linejoin="round">'
            f'<path d="{body}"/>{head}</g>')


def kicon(kind, size=38):
    """An encounter kind as a small picture, in a 40-unit box."""
    if kind == "duel":
        b = fig(0, .66, -13.2, -19)
    elif kind == "pack":
        b = fig(2, .42, -20, -15) + fig(2, .42, 3, -15) + fig(2, .5, -10, -8)
    elif kind == "elite":
        b = fig(4, .66, -15.2, -18) + f'<path transform="translate(11 -10) scale(.8)" d="{STAR}" fill="{SUN}" stroke="{INK}" stroke-width="2.8" stroke-linejoin="round"/>'
    elif kind == "shift":
        b = (f'<rect x="-16" y="5" width="32" height="7" rx="3.5" fill="#fff" stroke="{INK}" stroke-width="2.5" transform="rotate(-16)"/>'
             f'<path d="M-11,-5 A11.5,11.5 0 0 1 10,-9" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>'
             f'<path d="M5,-16 L12,-8 L2,-5Z" fill="{INK}" stroke="{INK}" stroke-width="1.5" stroke-linejoin="round"/>')
    elif kind == "rest":
        b = (f'<path d="M-5,-14 L-18,13 H8Z" fill="#fff" stroke="{INK}" stroke-width="2.6" stroke-linejoin="round"/><path d="M-5,-1 L-10,13 H0Z" fill="{INK}"/>'
             f'<g transform="translate(13 6) scale(.15)"><path d="{FLAME}" fill="{CORAL}" stroke="{INK}" stroke-width="17" stroke-linejoin="round"/></g>')
    else:
        b = f'<path transform="scale(1.65)" d="{STAR}" fill="{SUN}" stroke="{INK}" stroke-width="1.6" stroke-linejoin="round"/>'
    return svg(size, size, "-20 -20 40 40", b)


def tmark(kind, st, x, y, r):
    fill = {"done": INK, "cur": CORAL}.get(st, WHITE)
    o = f'<circle cx="{x}" cy="{y}" r="{r + 4.4}" fill="none" stroke="{INK}" stroke-width="2"/>' if st == "cur" else ""
    a = f'fill="{fill}" stroke="{INK}" stroke-linejoin="round"'
    if kind == "boss":
        s = r / 6.2
        o += f'<path transform="translate({x} {y}) scale({s:.2f})" d="{STAR}" {a} stroke-width="{2.3 / s:.1f}"/>'
    elif kind == "rest":
        o += f'<path d="M{x},{y - r} L{x + r * 1.08:.1f},{y + r * .86:.1f} H{x - r * 1.08:.1f}Z" {a} stroke-width="2.2"/>'
    else:
        o += f'<circle cx="{x}" cy="{y}" r="{r}" {a} stroke-width="2.2"/>'
    if st == "lost":
        o += f'<circle cx="{x}" cy="{y}" r="{r + 4.4}" fill="none" stroke="{INK}" stroke-width="2"/>'
        d = f"M{x - r * .55:.1f},{y - r * .55:.1f}L{x + r * .55:.1f},{y + r * .55:.1f}M{x + r * .55:.1f},{y - r * .55:.1f}L{x - r * .55:.1f},{y + r * .55:.1f}"
        o += f'<path d="{d}" stroke="{CORAL}" stroke-width="3" stroke-linecap="round"/>'
    return o


def trail(x, y, pos, lost=False, w=608, gap=31, r=7, step=200, rot=-.4, stamp=False, pad=12):
    """The whole run on one sunny strip: dots are fights, a tent is the rest stop, a star is the boss."""
    acts = ""
    for a in range(3):
        m = ""
        for i, kind in enumerate(RUN[a]):
            n = a * 5 + i
            st = "done" if n < pos else (("lost" if lost else "cur") if n == pos else "todo")
            m += tmark(kind, st, 13 + i * gap, 13, r)
        sw = 26 + 4 * gap
        acts += f'<div style="position:absolute;left:{pad + a * step}px;top:3px"><div class="s10">Act {a + 1}</div>{svg(sw, 26, f"0 0 {sw} 26", m)}</div>'
    st = ""
    if stamp:
        st = (f'<div class="bn" style="position:absolute;right:14px;top:6px;transform:rotate(-7deg);border:3px solid {CORAL};color:{CORAL};background:#fff;'
              f'border-radius:8px;font-size:17px;line-height:23px;padding:0 8px">Cleared</div>')
    return f'<div class="st" style="left:{x}px;top:{y}px;width:{w}px;height:46px;background:{SUN};transform:rotate({rot}deg)">{acts}{st}</div>'


def keypill(x, y, name, rot=0):
    return (f'<div class="keyp" style="left:{x}px;top:{y}px;height:25px;border-radius:9px;padding:0 9px 0 6px;gap:5px;transform:rotate({rot}deg)">{star_svg(13, sw=0)}'
            f'<div class="bn" style="font-size:12.5px;line-height:14px">{name}</div></div>')


def keys(x, y, names, dx=0, dy=29):
    return "".join(keypill(x + i * dx, y + i * dy, n, (-1.5, 1.2, -1)[i % 3]) for i, n in enumerate(names))


def purse(x, y, n, rot=1.5, w=124, warn=False, note="Coins, one purse"):
    return (f'<div class="st" style="left:{x}px;top:{y}px;width:{w}px;height:50px;transform:rotate({rot}deg);padding:6px 9px">'
            f'<div class="s10">{note}</div><div style="display:flex;align-items:center;gap:5px;margin-top:2px">{coin(22)}'
            f'<span class="bn" style="font-size:21px;line-height:22px;color:{"#C2183F" if warn else INK}">{n}</span></div></div>')


def pursepill(x, y, n, low=False):
    return (f'<div class="st" style="left:{x}px;top:{y}px;width:128px;height:34px;transform:rotate(1deg);display:flex;align-items:center;gap:5px;padding:0 8px;z-index:4">{coin(21)}'
            f'<span class="bn" style="font-size:20px;line-height:22px;color:{"#C2183F" if low else INK}">{n}</span><span class="s10">one purse</span></div>')


def party(x, y, cols=2, dx=146, dy=90, solo=False, empty=False, on=None, prev=None, pj=None, data=None, n=4, extra=None):
    out = ""
    F = (data or PARTY)[:2 if solo else 4]
    for q, (p, nm, kind, ch) in enumerate(F):
        px, py = x + (q % cols) * dx, y + (q // cols) * dy
        out += fst(px, py, p, nm, kind, [] if empty else ch, n=n, v=True, cls="on" if on == q else "", prev=prev if pj == q else None,
                   rot=(-.6, .5, .4, -.5)[q], tab=q % 2 == 0, extra=(extra or {}).get(q, ""))
    return out


def chip_ring(k):
    """Marks chip k in a fighter sticker as the one being held or read."""
    return at(4 + 26 * k - 2, 36, svg(30, 30, "-15 -15 30 30", f'<circle r="13" fill="none" stroke="{INK}" stroke-width="5"/><circle r="13" fill="none" stroke="{SUN}" stroke-width="2.6"/>'), "z-index:3")


def srow(x, y, w, label, val="", cls="", rot=0, icon="", vs=False):
    v = f'<span class="v{" s" if vs else ""}">{val}</span>' if val else ""
    return f'<div class="sr {cls}" style="left:{x}px;top:{y}px;width:{w}px;transform:rotate({rot}deg)">{icon}<span class="l">{label}</span>{v}</div>'


def price(n):
    return f"{coin(15)}{n}"


def stars_bg(pts):
    return "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{SUN}" opacity=".7"/>' for x, y, r in pts)


def bg_road():
    b = (f'<rect x="-107" width="854" height="480" fill="{BG}"/>' + stars_bg(((-60, 40, 2), (250, 30, 1.6), (566, 24, 1.8), (706, 70, 2.2)))
         + f'<ellipse cx="60" cy="420" rx="330" ry="150" fill="{BG2}"/><ellipse cx="620" cy="440" rx="320" ry="190" fill="{BG2}"/>'
         f'<path d="M-107,330 C80,290 200,372 340,332 S620,300 747,344" fill="none" stroke="#5849AE" stroke-width="30" stroke-linecap="round"/>'
         f'<rect x="-107" y="392" width="854" height="88" fill="#33257C"/>')
    return svg(854, 480, "-107 0 854 480", b, 'class="sc"')


def bg_rest():
    g = 392
    b = (f'<rect x="-107" width="854" height="480" fill="{BG}"/><circle cx="560" cy="60" r="46" fill="#5849AE"/>' + stars_bg(((-60, 40, 2), (270, 22, 1.6), (430, 34, 1.8), (706, 110, 2.2)))
         + f'<ellipse cx="40" cy="{g + 6}" rx="330" ry="80" fill="{BG2}"/><ellipse cx="640" cy="{g + 6}" rx="300" ry="96" fill="{BG2}"/>'
         f'{s3.tent(520, 318, g, 54)}<rect x="-107" y="{g}" width="854" height="{480 - g}" fill="#33257C"/>{s3.fire(596, g + 22, .36)}')
    return svg(854, 480, "-107 0 854 480", b, 'class="sc"')


def bg_res(clear):
    b = (f'<rect x="-107" width="854" height="480" fill="#3A2B86"/>' + stars_bg(((-64, 70, 2), (470, 40, 1.6), (700, 96, 2.2)))
         + f'<path d="M-107,480 V330 A430,430 0 0 1 747,330 V480Z" fill="#43348F"/><rect x="-107" y="398" width="854" height="82" fill="#2C1E70"/>')
    if clear:
        b += s4.confetti(20)
    return svg(854, 480, "-107 0 854 480", b, 'class="sc"') + (s4.big_rays(320, 40, 520, 20, SUN, .13) if clear else "")


def carries(names, size=20):
    return "".join(f'<span class="cy">{pog(DR[n][0], size, 1, sq=False)}<span class="bn">{n}</span></span>' for n in names)


def status(x, y, I, wide=True):
    left, total = I["pool"]
    label = "Solo stocks" if I.get("solo") else "Team stocks"
    return (s3.stocks(x, y, left, total, label, rot=-1.5) + purse(x + 142, y + 2, I["coins"], note="Coins" if I.get("solo") else "Coins, one purse")
            + keys(x + 2, y + 62, I["keys"], dx=136 if wide else 0, dy=0 if wide else 29))


def nhints(I):
    return hints(("A", I["a"]), ("Y", "Read your drives"), ("Start", "Save and quit"))


def kind_of(I):
    return RUN[I["pos"] // 5][I["pos"] % 5]


# ------------------------------------------------------------------ N1: the trail is the screen
def n1(state="mid"):
    I = NEXT[state]
    a, i = divmod(I["pos"], 5)
    kind = RUN[a][i]
    p = [bg_road(), ttl(f"Act {a + 1} of 3", 16, 2, 24), trail(388, 6, I["pos"], w=236, gap=13, r=4.4, step=75, rot=.6, pad=8)]
    xs = [14 + k * 124 for k in range(5)]
    d = "M" + " L".join(f"{x + 52},112" for x in xs)
    p.append(at(0, 0, svg(640, 200, "0 0 640 200", f'<path d="{d}" fill="none" stroke="#C9BFF5" stroke-width="5" stroke-dasharray="2 11" stroke-linecap="round"/>')))
    for k, kd in enumerate(RUN[a]):
        x = xs[k]
        if k == i:
            p.append(f'<div class="st stop on" style="left:{x - 4}px;top:56px;width:112px;height:102px;padding-top:9px">{kicon(kd, 48)}<div class="w" style="font-size:16px;line-height:19px;margin-top:3px">{KINDS[kd]}</div>'
                     f'<span class="fl" style="left:-8px;top:-10px;transform:rotate(-5deg)">Next</span></div>')
        else:
            done = k < i
            chk = ""
            if done:
                chk = at(82, -9, svg(22, 22, "-11 -11 22 22", f'<circle r="9.3" fill="{INK}" stroke="#fff" stroke-width="2"/><path d="M-4.2,.2L-1.2,3.4L4.6,-3.2" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'))
            p.append(f'<div class="st stop{" dn" if done else ""}" style="left:{x}px;top:70px;width:104px;height:78px;padding-top:7px;transform:rotate({(-1.4, 1, -.8, 1.2, -1)[k]}deg)">'
                     f'{kicon(kd, 36)}<div class="w" style="margin-top:2px">{KINDS[kd]}</div>{chk}</div>')
    left = i <= 2
    tx, sx = (16, 356) if left else (302, 16)
    cx = xs[i] + 52
    p.append(at(0, 0, svg(640, 200, "0 0 640 200", f'<path d="M{cx},160 V184" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>')))
    if kind == "rest":
        pic = kicon("rest", 50)
        l2 = f'<div class="b13" style="white-space:nowrap">{I["note1"]}</div><div class="b13" style="white-space:nowrap;color:#5A4C99">{I["then"]}</div>'
    else:
        pic = sil(I["fk"], 38)
        mid = f'<div style="display:flex;gap:9px;align-items:center;height:24px"><span class="s10">Carries</span>{carries(I["carries"])}</div>' if I.get("carries") else f'<div class="b13" style="height:24px;line-height:23px;white-space:nowrap">{I["note"]}</div>'
        l2 = f'{mid}<div class="b13" style="white-space:nowrap"><span style="color:#5A4C99">Win:</span> {I["win1"]}</div>'
    p.append(f'<div class="st" style="left:{tx}px;top:182px;width:322px;height:88px;transform:rotate(-.6deg)"><div style="position:absolute;left:11px;top:14px">{pic}</div>'
             f'<div style="position:absolute;left:66px;top:7px"><div class="t14" style="font-size:16px;line-height:20px">{I["name"]} <span style="font-family:SS3;font-weight:700;font-size:13px;letter-spacing:0">{I["where"]}</span></div>{l2}</div></div>')
    p.append(status(sx, 184, I))
    p.append(party(22 if not I.get("solo") else 174, 296, cols=4, dx=150, solo=I.get("solo"), empty=I.get("empty")))
    p += [say(I["say"]), nhints(I)]
    return frame("".join(p))


# ------------------------------------------------------------------ N2: the next-up poster
def poster(x, y, I):
    kind = kind_of(I)
    if kind == "rest":
        pic = at(22, 22, kicon("rest", 80))
    elif kind == "boss":
        pic = at(22, 8, sil(I["fk"], 80, "#6B6F8C"))
    else:
        pic = at(36, 30, sil(I["fk"], 52, "#6B6F8C"))
    if I.get("carries"):
        body = f'<div class="s10" style="margin-top:9px">Carries</div><div style="display:flex;flex-direction:column;gap:3px;margin-top:3px">{carries(I["carries"], 22)}</div>'
    else:
        body = f'<div class="b13" style="margin-top:9px;width:136px">{I["note"]}</div>'
    win = (f'<div class="s10">If you win</div><div class="b13" style="font-size:13.5px;line-height:17px">{I["win"]}</div>' if I["win"] else "")
    return (f'<div class="st" style="left:{x}px;top:{y}px;width:300px;height:290px;transform:rotate(-1deg);overflow:hidden">'
            f'<div style="position:absolute;left:0;top:0;width:294px;height:56px;background:{SUN};border-bottom:3px solid {INK}"><div style="position:absolute;left:8px;top:7px">{kicon(kind, 40)}</div>'
            f'<div class="hl" style="position:absolute;left:56px;top:4px;font-size:28px">{KINDS[kind]}</div><div class="s10" style="position:absolute;left:57px;top:35px;color:{INK}">{I["sub"]}</div></div>'
            f'<div style="position:absolute;left:10px;top:68px;width:124px;height:118px;border:2.5px solid {INK};border-radius:10px;background:#DDD7F4;overflow:hidden">'
            f'<div style="position:absolute;left:0;top:92px;width:124px;height:26px;background:#B5ACE0"></div>{pic}</div>'
            f'<div style="position:absolute;left:146px;top:66px;width:142px"><div class="t14" style="font-size:18px;line-height:21px">{I["name"]}</div><div class="b13">{I["where"]}</div>{body}</div>'
            f'<div style="position:absolute;left:10px;top:197px;width:274px;border-top:2px dashed rgba(42,26,110,.3);padding-top:7px">{win}'
            f'<div class="b13" style="color:#5A4C99;margin-top:{6 if I["win"] else 0}px">{I["then"]}</div></div></div>')


def n2(state="mid"):
    I = NEXT[state]
    p = [bg_road(), trail(16, 8, I["pos"]), poster(20, 70, I)]
    p.append(at(I["pos"] // 5 * 200 + 28 + (I["pos"] % 5) * 31 - 4, 49, svg(26, 14, "0 0 26 14", f'<path d="M13,2 L22,12 H4Z" fill="{CORAL}" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>'), "z-index:4"))
    p.append(party(340, 72, cols=2, dx=146, dy=90, solo=I.get("solo"), empty=I.get("empty")))
    p.append(status(342, 162 if I.get("solo") else 254, I))
    p += [say(I["say"]), nhints(I)]
    return frame("".join(p))


NSTATES = [("start", "Start of act 1", "Nothing won yet, five stocks, empty rows, one keystone."),
           ("boss", "Next is a boss", "The star on the trail. The win line says keystone, not drives."),
           ("rest", "Next is a rest stop", "The tent. A says Go in, and the purse is the number to look at."),
           ("solo", "Solo", "Two fighters and four stocks. Nothing else moves.")]


# ------------------------------------------------------------------ the shop's goods
SHOP = [("d", "Ember", 12), ("d", "Shatter", 18), ("d", "Perfect Form", 26), ("lv", "Level up a drive", 15), ("stock", "Restore a stock", 20),
        ("roll", "Swap the drives on sale", 5), ("order", "Reorder drives", None), ("pact", "Pact: Echo for a stock", None), ("leave", "Back on the road", None)]
SHOP2 = {1: [("d", "Ember", 12), ("d", "Shatter", 18)], 2: [("d", "Bolt", 18), ("d", "Perfect Form", 26)]}
REST2 = [("lv", "Level up a drive", 15), ("stock", "Restore a stock", 20), ("roll", "Swap my two drives", 5), ("order", "Reorder drives", None),
         ("pact", "Pact: Echo for a stock", None), ("leave", "Done", None)]
SHORT = {"Ember": "a fire burst when it fires", "Shatter": "breaks a Chilled foe for 12%", "Bolt": "chains a hit to a second foe", "Perfect Form": "a full smash, no charging"}


def shop_row(x, y, w, it, coins, on, fade, rot):
    k, lab, pr = it
    cls = ("on " if on else "") + ("fd " if fade and not on else "") + ("ink " if k == "pact" else "") + ("no " if pr and pr > coins else "")
    icon = pog(DR[lab][0], 21, DR[lab][1], sq=False) if k == "d" else ""
    val = price(pr) if pr else ("1 stock" if k == "pact" else "")
    return srow(x, y, w, lab, val, cls, 0 if on else rot, icon)


def rowbig(x, y, name, chips, held):
    cells = ""
    for i in range(4):
        cx = 10 + i * 76
        if i < len(chips):
            d, l = chips[i]
            h = i == held
            arrows = ""
            if h:
                tri = lambda fl: svg(11, 14, "0 0 11 14", f'<path d="{"M9,2 L2,7 L9,12Z" if fl else "M2,2 L9,7 L2,12Z"}" fill="{CORAL}" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>')
                arrows = at(-9, 12, tri(True)) + at(68, 12, tri(False))
            cells += (f'<div class="slotc{" h" if h else ""}" style="left:{cx}px;top:{22 if h else 27}px">{pog(DR[d][0], 32, DR[d][1], sq=False)}'
                      f'<div class="s10" style="margin-top:1px">{d}</div>{arrows}</div>')
        else:
            cells += (f'<div class="slotc" style="left:{cx}px;top:27px">' + svg(32, 32, "-16 -16 32 32", f'<circle r="12" fill="none" stroke="{LILAC}" stroke-width="2.2" stroke-dasharray="4 3.4"/>')
                      + '<div class="s10" style="margin-top:1px;color:#5A4C99">Empty</div></div>')
        cells += f'<span class="s10" style="position:absolute;left:{cx + 3}px;top:{84}px;color:#5A4C99">Slot {i + 1}</span>'
    return (f'<div class="st" style="left:{x}px;top:{y}px;width:322px;height:102px;z-index:4"><div style="position:absolute;left:10px;top:4px;display:flex;gap:10px;align-items:baseline">'
            f'<span class="t14">{name}\'s row</span><span class="t12">fires left to right</span></div>{cells}</div>')


def pact_dlg(x, y, who=None):
    dots = lambda n: '<span class="md">' + "".join(f'<i class="{"" if i < n else "o"}"></i>' for i in range(5)) + "</span>"
    if who:
        btn = (f'<div class="db" style="left:14px;top:134px;width:164px;background:{CORAL};color:#fff">P1: take the pact</div>'
               f'<div class="db on" style="left:192px;top:134px;width:164px">P2: A agrees, B refuses</div>')
        head, pt = "P1 wants the pact", ""
    else:
        btn = (f'<div class="db on" style="left:14px;top:134px;width:164px">Keep the stock</div>'
               f'<div class="db" style="left:192px;top:134px;width:164px">Take the pact</div>')
        head, pt = "A pact is offered", ptr(-18, 138)
    return (f'<div class="dimx"></div><div class="st" style="left:{x}px;top:{y}px;width:376px;height:186px;background:{INK};border-color:#fff;box-shadow:0 0 0 2.5px {INK},4px 6px 0 2.5px {INK};'
            f'transform:rotate(-1deg);padding:9px 14px;z-index:8;color:#fff"><div class="hl" style="font-size:22px;line-height:25px;color:{SUN}">{head}</div>'
            f'<div style="font-size:13px;line-height:16px;font-weight:700;margin-top:3px">Echo, an epic drive, for one stock from the pool. Once this act.</div>'
            f'<div style="display:flex;align-items:center;gap:8px;margin-top:9px;height:44px">{pog("util", 40, 2, sq=False)}<span class="bn" style="font-size:16px;color:{SUN}">Echo</span>'
            f'<span style="font-size:12.5px;font-weight:700;margin-left:14px;white-space:nowrap">Stock pool {dots(4)} becomes {dots(3)}</span></div>{btn}{pt}</div>')


def zi(h):
    return h.replace('class="hints"', 'class="hints" style="z-index:9"')


# ------------------------------------------------------------------ S1: one counter, one cursor
def s1(state="shop"):
    hov = {"shop": 1, "buy": 1, "poor": 2, "order": 6, "pact": 7}[state]
    coins = 11 if state == "poor" else 41
    p = [bg_rest(), ttl("Rest stop", 16, 2, 24), pursepill(160, 4, coins, state == "poor")]
    y = 46
    for i, it in enumerate(SHOP):
        on = i == hov
        p.append(shop_row(40 if on else 30, y, 238, it, coins, on, state in ("buy", "order"), (-.8, .7, -.6, .8, -.7, .6, -.8, .7, -.6)[i]))
        if on and state not in ("buy", "order"):
            p.append(ptr(8, y + 1))
        y += 33 + (6 if i in (2, 5, 7) else 0)
    px, py = 300, 146
    kw = {}
    if state == "buy":
        kw = dict(on=1, pj=1, prev=("new", "Shatter"))
        p.append(curd(px + 146 + 88, py - 24, 1))
    if state == "order":
        kw = dict(on=0, extra={0: chip_ring(1)})
        p.append(rowbig(296, 34, "Fighter A", PARTY[0][3], 1))
    elif state == "poor":
        p.append(d2(296, 50, "Perfect Form", flag="15 short"))
    elif state == "buy":
        p.append(d2(296, 50, "Shatter", slot=3, cls="hov"))
    else:
        p.append(d2(296, 50, "Shatter"))
    p.append(party(px, py, **kw))
    p.append(s3.stocks(302, 330, 4, 5, "Team stocks", rot=-1.5))
    if state == "pact":
        p += [pact_dlg(132, 132), zi(hints(("Left / Right", "Choose"), ("A", "Confirm"), ("B", "Keep the stock")))]
        return frame("".join(p))
    line, h = {
        "shop": ("Buy Shatter for 18 coins. You choose who wears it next.", [("Up / Down", "Choose"), ("A", "Buy"), ("Start", "Back on the road")]),
        "buy": ("Who wears Shatter? Fighter B, slot 3.", [("Stick", "Choose a fighter"), ("A", "Pay 18 coins"), ("B", "Back")]),
        "poor": ("Perfect Form costs 26 coins. The purse has 11.", [("Up / Down", "Choose"), ("Start", "Back on the road")]),
        "order": ("Holding Bolt. Move it left or right, then put it down.", [("Left / Right", "Move Bolt"), ("A", "Put it down"), ("B", "Done")]),
    }[state]
    p += [say(line), hints(*h)]
    return frame("".join(p))


# ------------------------------------------------------------------ S2: two halves, a list each
def s2_side(p, st, x0, coins):
    mode, i = st.get("m", "hover"), st.get("i", 0)
    items = SHOP2[p] + REST2
    col = CORAL if p == 1 else LAGOON
    out, x = "", x0 + 36
    for k, it in enumerate(items):
        on = k == i and mode != "done"
        out += shop_row(x + (6 if on else 0), 46 + k * 31, 256, it, coins, on, mode in ("who", "order", "done"), (-.5, .4, -.3, .5, -.4, .3, -.5, .4)[k])
        if on and mode == "hover":
            out += ptr(x0 + 6, 46 + k * 31, col)
    F = [f for f in PARTY if f[0] == p]
    kind, lab, pr = items[i]
    for q, (_, nm, fk, ch) in enumerate(F):
        fx = x0 + 30 + q * 144
        sel = q == st.get("j", 0)
        prev = ("new", lab) if (mode == "who" and sel) else None
        extra = chip_ring(st.get("h", 1)) if (mode == "order" and sel) else ""
        out += fst(fx, 308, p, nm, fk, ch, n=4, v=True, cls="on" if (mode in ("who", "order") and sel) else "", prev=prev, rot=(-.6, .5)[q], tab=q == 0, extra=extra)
        if mode == "who" and sel:
            out += curd(fx + 96, 284, p)
    other = 2 if p == 1 else 1
    if mode == "done":
        line = f"Done. Waiting for P{other}."
    elif mode == "who":
        line = f"Who wears {lab}? {F[st.get('j', 0)][1]}, slot {len(F[st.get('j', 0)][3]) + 1}."
    elif mode == "order":
        line = f"Holding {F[st.get('j', 0)][3][st.get('h', 1)][0]}. Left / Right moves it."
    elif kind == "d":
        line = f"{lab}: {SHORT[lab]}." if pr <= coins else f"{lab} costs {pr}. The purse has {coins}."
    else:
        line = {"lv": "Pick one of your drives to raise a level.", "stock": "One stock back in the shared pool.", "roll": "Two new drives on your side.",
                "order": "Change the order your drives fire in.", "pact": "Echo for one shared stock. Both must agree.", "leave": "Leave when both players are done."}[kind]
    out += f'<div class="strip" style="left:{x0 + 30}px;top:402px">{line}</div>'
    return out


def s2(a, b, coins=41, pact=False):
    p = [s4.bg_reward("halves"), f'<div class="pp" style="left:30px;top:10px;background:{CORAL};transform:rotate(-4deg)">P1</div>',
         f'<div class="pp" style="left:572px;top:10px;background:{LAGOON};transform:rotate(4deg)">P2</div>', ttl("Rest stop", 76, 4, 21),
         pursepill(256, 4, coins, coins < 12),
         s2_side(1, a, 0, coins), s2_side(2, b, 320, coins)]
    if pact:
        p += [pact_dlg(132, 132, who=1), zi(hints(("P2: A", "Agree"), ("P2: B", "Refuse")))]
    else:
        p.append(hints(("Up / Down", "Choose"), ("A", "Buy"), ("B", "Back")))
    return frame("".join(p))


S1STATES = [("buy", "Buying", "After A the list fades and the same cursor goes to the four fighters, starting on the one the game would pick. A pays."),
            ("poor", "Can't afford", "Prices over the purse turn red. A does nothing on them, and the strip gives both numbers."),
            ("order", "Reordering a row", "Choose Reorder drives, then a fighter. Their row opens big; the held drive moves left and right."),
            ("pact", "The pact offer", "An ink row in the list. A opens a yes or no, with the cursor starting on Keep the stock.")]
S2STATES = [((dict(m="who", i=1, j=1), dict(i=2)), {}, "Buying", "P1 is choosing who wears Shatter while P2 keeps shopping. Each player only equips their own two fighters."),
            ((dict(m="done"), dict(i=1)), dict(coins=11), "Can't afford", "P1 spent first. P2's Perfect Form is now out of reach: one purse, two shoppers."),
            ((dict(m="order", i=5, j=0, h=1), dict(i=0)), {}, "Reordering a row", "The row is reordered inside the small fighter sticker; there is no room to open it."),
            ((dict(i=6), dict(i=3)), dict(pact=True), "The pact offer", "The stock is shared, so one player asks and the other has to agree.")]


# ------------------------------------------------------------------ the fight behind pause and Second Wind
def bench_small(B, cd=None):
    name, kind, d, row = B
    bg = "" if cd is None else f'background:linear-gradient(90deg,#fff 0 {cd * 100:.0f}%,#B9B4CE {cd * 100:.0f}% 100%)'
    return f'<div class="bn2" style="{bg}">{sil(kind, 10)}<span class="d">{d}%</span>{dpad("down", 14)}</div>'


def pc_h2_new(P, x, y, low=0):
    """Step 5 revision: the bench sticker is head, percent and tag button, and rides at the end of the Heat bar."""
    col = CORAL if P["p"] == 1 else LAGOON
    y += 22
    o = (at(-2, 10, s5.dmg(P["dmg"], 40)) + f'<span class="pt" style="background:{col};top:-3px">P{P["p"]}</span>' + at(27, -3, f'<span class="nt">{P["name"]}</span>')
         + at(100, 12, s5.hrow(P)) + at(106 + 30 * len(P["row"]), 12, s5.active(P))
         + at(low, 59, s5.m1(P["heat"], w=122, cap=P.get("cap", 150), **P.get("m", {}))) + at(low + 153, 60, bench_small(P["bench"], P.get("cd"))))
    return f'<div class="hp" style="left:{x}px;top:{y}px;width:{s5.h2w(P)}px;height:86px">{o}</div>'


def fight(**kw):
    args = dict(P1=s5.player(1), P2=s5.player(2), fs=[s5.MIN(18), s5.ELITE])
    args.update(kw)
    return s5.screen("h2", **args)


def over(fz, inner):
    return fz[:-6] + f'<div style="position:absolute;left:0;top:0;width:640px;height:480px;background:rgba(26,16,74,.86)"></div>{inner}</div>'


def kslab(x, y, k, rot=0):
    return (f'<div class="kc" style="left:{x}px;top:{y}px;width:316px;height:42px;transform:rotate({rot}deg)">{kem(k, 34)}'
            f'<div><div class="kn">{k}</div><div class="kr">{KS[k][0]}</div></div></div>')


def pause(state="menu"):
    read = state == "read"
    p = [ttl("Paused", 16, 2, 24), at(118, 12, f'<span class="pt" style="background:{LAGOON};font-size:12.5px;line-height:16px;transform:rotate(-3deg)">P2 paused</span>')]
    rows = [("Resume", "", "big"), ("Read drives", "", ""), ("Quit to camp", "the run is kept", "")]
    y = 46
    for i, (lab, v, c) in enumerate(rows):
        on = (i == 1) if read else (i == 0)
        fd = read and not on
        p.append(srow(40 if (on and not read) else 30, y, 230, lab, v, c + (" on" if on else "") + (" fd" if fd else ""), 0 if on else (-.8, .7, -.6)[i], vs=True))
        if on and not read:
            p.append(ptr(8, y + 10, LAGOON))
        y += 58 if c == "big" else 34
    line = lambda d, t: f'<div style="display:flex;align-items:center;gap:7px;height:22px">{dpad(d, 17)}<span class="b13" style="white-space:nowrap">{t}</span></div>'
    p.append(f'<div class="st" style="left:28px;top:186px;width:236px;height:82px;transform:rotate(-1deg);padding:6px 10px"><div class="t14" style="margin-bottom:3px">The D-pad in a fight</div>'
             f'{line("down", "Down: tag in your other fighter")}{line("right", "Right: fire your active drive")}</div>')
    kw = dict(on=2, extra={2: chip_ring(1)}) if read else {}
    p.append(party(300, 48, dy=88, n=3, data=[(pp, n, k, c if n != "Fighter B" else c + [("Shatter", 1)]) for pp, n, k, c in PARTY[:3]] + [(2, "Fighter D", 5, PARTY[3][3] + [("Ember", 1)])], **kw))
    p += [kslab(298, 232, "Plague Bearer", -.5), kslab(298, 284, "Glass Core", .5)]
    if read:
        p += [cur(300 + 4 + 26 + 15, 48 + 88 + 54, 2), d2(296, 340, "Clean Landing", 2, cls="hov"),
              hints(("Stick", "Choose a drive"), ("B", "Back"), ("Start", "Resume"))]
    else:
        p += [say("Back to the fight. Either player can pause."), hints(("Up / Down", "Choose"), ("A", "Resume"), ("Start", "Resume"))]
    return over(fight(), "".join(p))


def second_wind():
    P1 = s5.player(1, dmg=143, heat=18)
    P2 = s5.player(2, dmg=121, heat=9)
    d = (f'<div class="st" style="left:128px;top:124px;width:384px;height:192px;transform:rotate(-1deg);padding:10px 16px;z-index:8">'
         f'<div class="hl" style="font-size:25px;line-height:28px">Use your Second Wind?</div>'
         f'<div class="sub" style="font-size:13px;line-height:16.5px;margin-top:4px">The stock pool is empty. Once a run the party can get back up with one stock and finish this fight.</div>'
         f'<div class="t12" style="margin-top:6px">Say no and the run ends here.</div>'
         f'<div class="db on" style="left:16px;top:140px;width:168px">Use Second Wind</div><div class="db" style="left:200px;top:140px;width:168px">End the run</div>{ptr(-14, 144)}'
         f'{at(326, -26, burst("Once|a run", CORAL, 64, 13), "z-index:9")}</div>')
    return over(fight(P1=P1, P2=P2, fs=[dict(s5.ELITE, dmg=88)], pool=(0, 5)), d + hints(("Left / Right", "Choose"), ("A", "Confirm")))


# ------------------------------------------------------------------ results
def num(x, y, label, val, rot=0, w=112):
    return f'<div class="num" style="left:{x}px;top:{y}px;width:{w}px;height:48px;transform:rotate({rot}deg)"><div class="s10">{label}</div><div class="bn">{val}</div></div>'


def unl(x, y, w, kind, inner, rot=0, dash=False):
    return (f'<div class="st{" dash" if dash else ""}" style="left:{x}px;top:{y}px;width:{w}px;height:58px;transform:rotate({rot}deg);padding:5px 9px">'
            f'<div class="s10">{kind}</div><div style="display:flex;align-items:center;gap:6px;margin-top:3px;white-space:nowrap">{inner}</div></div>')


def results(clear=False):
    name = lambda t: f'<span class="bn" style="font-size:14px;line-height:16px">{t}</span>'
    if clear:
        data, pos, kn = FINAL, 15, ["Plague Bearer", "Glass Core", "Long Fuse"]
        head, sub, t = "Run cleared!", "All three acts, with 2 of 5 stocks to spare.", "41:36"
        nums = [("Drives fired", "388"), ("Longest chain", "6 drives"), ("Coins earned", "171"), ("Stocks lost", "7")]
        ng = "".join(f'<i class="{c}">{i}</i>' for i, c in ((0, ""), (1, "n"), (2, "x"), (3, "x")))
        un = (unl(16, 322, 124, "New fighter", f'<div style="height:28px;overflow:hidden">{sil(4, 20)}</div>{name("Fighter N")}', -1)
              + unl(152, 324, 132, "New drive", f'{pog("fire", 26, 2, sq=False)}{name("Wildfire")}', 1)
              + unl(296, 322, 150, "New keystone", f'{kem("Long Fuse", 28)}{name("Long Fuse")}', -.8)
              + unl(458, 324, 164, "NG+ level 1 is open", f'<div class="ld">{ng}</div>', 1))
        line = "Four new things are waiting at camp, and a harder run."
    else:
        data, pos, kn = PARTY, 6, ["Plague Bearer", "Glass Core"]
        head, sub, t = "The run ended", "Act 2, fight 2: the elite on Stage 6 took the last stock.", "24:10"
        nums = [("Drives fired", "212"), ("Longest chain", "5 drives"), ("Coins earned", "96"), ("Stocks lost", "5")]
        un = (unl(16, 322, 132, "New drive", f'{pog("fire", 26, 2, sq=False)}{name("Wildfire")}', -1)
              + unl(160, 324, 256, "Still locked", f'{lock(15, LILAC)}<span class="b13" style="color:#5A4C99">Fighter J opens when you beat act 2.</span>', 1, True))
        line = "Wildfire can now turn up in any run."
    p = [bg_res(clear), ttl(head, 16, 0, 30), at(22, 38, f'<div class="wt" style="font-size:13px;line-height:16px">{sub}</div>'),
         f'<div class="st" style="left:534px;top:6px;width:88px;height:46px;transform:rotate(3deg);padding:4px 9px"><div class="s10">Time</div><div class="bn" style="font-size:20px;line-height:22px">{t}</div></div>',
         trail(16, 62, pos, lost=not clear, stamp=clear, rot=-.3), party(18, 122, cols=4, dx=152, data=data)]
    p.append(keys(18, 210, kn, dx=0, dy=26))
    for i, (l, v) in enumerate(nums):
        p.append(num(166 + i * 116, 216, l, v, (-.8, .7, -.6, .8)[i], 106))
    p.append(ttl("Unlocked", 14, 291, 17))
    p += [un, say(line), hints(("A", "Back to camp"))]
    return frame("".join(p))


# ------------------------------------------------------------------ sheet parts
def shot(inner, zoom, label=None, cap=None):
    lab = f'<div class="tag">{label}</div>' if label else ""
    c = f'<p class="cap" style="max-width:{640 * zoom:.0f}px">{cap}</p>' if cap else ""
    return f'<div>{lab}<div style="width:{640 * zoom:.0f}px;height:{480 * zoom:.0f}px;border-radius:8px;overflow:hidden"><div class="g" style="zoom:{zoom}">{inner}</div></div>{c}</div>'


def crop(inner, y0, h):
    return f'<div style="width:640px;height:{h}px;border-radius:8px;overflow:hidden"><div class="g" style="margin-top:-{y0}px">{inner}</div></div>'


def lay(tag, name, main, note, trade):
    return (f'<div class="lay"><div class="hd"><b>{tag}</b><span>{name}</span></div>{shot(main, 1.15)}<p class="note">{note}</p><p class="trade">{trade}</p></div>')


def html():
    holo = "".join(f'<stop offset="{i / 5:.2f}" stop-color="{c}"/>' for i, c in enumerate(s4.HOLO.split(",")))
    before = crop(s5.main_screen("h2"), 344, 136)
    s5.pc_h2 = pc_h2_new
    after = crop(fight(), 344, 136)
    nrow = lambda fn: "".join(shot(fn(k), .575, n, c) for k, n, c in NSTATES)
    s1row = "".join(shot(s1(k), .575, n, c) for k, n, c in S1STATES)
    s2row = "".join(shot(s2(*ab, **kw), .575, n, c) for ab, kw, n, c in S2STATES)
    s2main = s2(dict(i=1), dict(i=2))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Envoy UI step 6</title><style>{CSS}</style></head>
<body><svg width="0" height="0" style="position:absolute"><defs><linearGradient id="holo" x1="0" y1="0" x2="1" y2="1">{holo}</linearGradient></defs></svg><div id="c">
<div class="top"><h1>Between the fights</h1>
<p>Step 6 of the UI design. Two choices: the map (N1 or N2) and the rest stop (S1 or S2). Results and pause are one design each. The path is a straight line: no forks.</p></div>

<div class="sec"><h2>First, the step 5 change: a smaller bench sticker</h2>
<div class="bench"><div><div class="tag">Before, actual size</div>{before}</div><div><div class="tag">After, actual size</div>{after}</div>
</div>
<p class="lede" style="margin:12px 0 0">The benched fighter is now head, percent and the tag button: no name, no little drive row. It sits at the end of the Heat bar instead of under it, so each corner goes from 108 px tall to 86 px. If a raised Heat cap makes the bar long enough to reach it, the sticker drops back under the bar.</p></div>

<div class="sec"><h2>The map: what is next</h2>
<p class="lede">Shown after the pick of three (and after the keystone pick, following a boss). Both candidates show the same moment: two players, act 2, one fight won, an elite next. One button matters and it says what it does. The game saves when this screen opens.</p>
<div class="two">
{lay("N1", "The trail", n1("mid"), "This act's five stops are five stickers across the screen, with the next one raised and sunny. A tag hangs from it with the foe, the stage and what a win gives. The whole run is a small strip top right; the party is a row along the bottom.",
     "You see the road ahead at a glance. But the thing you came to read, the next fight, gets the smallest sticker on screen, and the tag has to jump sides when the next stop is far right.")}
{lay("N2", "The next-up poster", n2("mid"), "One poster says what is next: kind, foe, stage, what it carries, what a win gives, and what comes after. The whole run is one strip along the top with a pointer on the next stop. The party and what it shares sit on the right, as at camp.",
     "The next fight is the biggest thing on screen and nothing moves between states. The road ahead is only dots, a tent and a star, plus one line of words.")}
</div>
<p class="rowlab">N1 in four other states</p><div class="row4">{nrow(n1)}</div>
<p class="rowlab">N2 in four other states</p><div class="row4">{nrow(n2)}</div></div>

<div class="sec"><h2>The rest stop and its shop</h2>
<p class="lede">Once an act, before the boss. Both candidates sell the same things: three drives, a level, a stock, a swap of the drives on sale, a free reorder, and a pact when one is offered. Coins are one shared purse in both.</p>
<div class="two">
{lay("S1", "One counter", s1("shop"), "The camp again: one list down the left, one cursor. Player 1 holds it; player 2 takes it by pressing A, and the pointer changes colour. The hovered drive shows its full tag on the right, above all four fighters, so anything can go to anyone.",
     "One list to read, full drive text, and a shared purse cannot be raced because only one hand is on it. Two players take turns, which is slower.")}
{lay("S2", "Two halves", s2main, "The pick-of-three screen again: a paper seam, a list and two fighters for each player, both shopping at once. Each side has its own two drives on sale; the purse sits on the seam.",
     "Fast for two. But one purse with two cursors is a race, drive text shrinks to one line, a row has no room to open for reordering, and the pact needs a second yes.")}
</div>
<p class="rowlab">S1 in four other states</p><div class="row4">{s1row}</div>
<p class="rowlab">S2 in the same four</p><div class="row4">{s2row}</div></div>

<div class="sec"><h2>Run results</h2>
<p class="lede">One design. The same parts in the same places whether the run was lost or cleared: how far, the time, the final rows and keystones, four numbers, what unlocked, and one button back to camp.</p>
<div class="row3">{shot(second_wind(), .78, "The Second Wind offer", "When the pool empties in an offline run, the fight freezes and asks once. The cursor starts on Use Second Wind, since the other answer cannot be undone. Either player answers.")}
{shot(results(False), .78, "Run lost", "The trail shows where it stopped with a cross. Unlocks still count, and a locked one says what opens it.")}
{shot(results(True), .78, "Run cleared", "Sunny rays, a Cleared stamp on the trail, a third keystone, and the next NG+ level marked open.")}</div></div>

<div class="sec"><h2>Pause</h2>
<div class="pz">{shot(pause("menu"), 1, "Either player presses Start, actual size")}
{shot(pause("read"), .7, "Read drives", "The cursor walks the chips, any fighter's. The hovered drive shows the same tag as the pick of three.")}
<div class="note"><b>Three rows:</b> Resume, Read drives, Quit to camp. Start always resumes, from anywhere.<br><br>
<b>Always showing:</b> the four rows as they stand, both keystones with their rule, and the two D-pad buttons. A player who only wants to check a rule never has to move.<br><br>
<b>Quit to camp</b> asks once (the same yes or no as Abandon at camp, with Keep playing first) and says the run will wait at the start of this fight.<br><br>
<b>Read your drives</b> on the map (the Y button) opens this same panel.</div></div></div>

<div class="sec"><h2>Recommended: N2 and S1 at actual size</h2>
<p class="lede">640 by 480, the size the game renders before upscaling. Smallest text is 11 px.</p>
<div class="act5" style="grid-template-columns:640px 640px"><div><div class="g">{n2("mid")}</div></div><div><div class="g">{s1("shop")}</div></div></div></div>

<div class="rec" style="grid-template-columns:150px 1fr 1fr"><h2>Recommended</h2>
<p><b>N2, the next-up poster.</b> With a straight path there is nothing to choose on the map, so its job is to say what the next fight is, in words, and get out of the way. The poster does that and stays put in every state.</p>
<p><b>S1, one counter.</b> It is the camp list again: one cursor, full drive text, any fighter. It also makes the shared purse safe, which S2 cannot do without splitting the coins per player.</p></div>
<p class="foot">Original vector art. Fonts: Bricolage Grotesque, Source Sans 3 (SIL OFL). Fighters, foes, bosses and stages are placeholders with invented names; prices, coin counts, times and result numbers are made up for the mock. Assumed here: the rest stop sits just before the boss, a drive row holds four, the party holds one keystone per act reached, and coins are one shared purse.</p>
</div></body></html>"""


CHECK = """() => {
  const out = [];
  document.querySelectorAll('.cs, .fz').forEach((f, i) => {
    const fr = f.getBoundingClientRect(), z = fr.width / 640;
    f.querySelectorAll('.st, .sr, .say, .hints, .strip, .kc, .keyp, .dr, .num').forEach(e => {
      const q = e.getBoundingClientRect();
      const l = (q.left - fr.left) / z, r = (q.right - fr.left) / z, t = (q.top - fr.top) / z, b = (q.bottom - fr.top) / z;
      if (l < 2 || r > 638 || t < 0 || b > 478) out.push(`screen ${i}: ${e.className} leaves the frame (${Math.round(l)},${Math.round(t)})-(${Math.round(r)},${Math.round(b)}) ${e.textContent.slice(0, 30)}`);
    });
    f.querySelectorAll('*').forEach(e => { if (e.children.length === 0 && !(e instanceof SVGElement) && e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).display !== 'inline')
      out.push(`screen ${i}: text overflow ${e.className}: ${e.textContent.slice(0, 40)}`); });
  });
  return [...new Set(out)]; }"""


def main():
    src = HERE / "step6.html"
    src.write_text(html(), encoding="utf-8")
    (HERE / "preview").mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
        page.goto(src.as_uri())
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(300)
        for b in page.evaluate(CHECK):
            print(b)
        page.locator("#c").screenshot(path=str(HERE / "preview" / "step6-between.png"), type="png")
        print(page.evaluate("document.getElementById('c').offsetHeight"))
        browser.close()


if __name__ == "__main__":
    main()
