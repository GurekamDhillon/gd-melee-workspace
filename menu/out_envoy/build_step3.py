#!/usr/bin/env python3
"""Envoy UI, step 3: the camp (hub and run setup). One review sheet.

Writes step3.html beside this file and renders preview/step3-camp.png (1600 px wide) with headless
Chromium, like build_step2.py. Everything inside a `.g` box is authored in game pixels (640x480
native) and scaled with CSS zoom. Original vector art only; fighters are neutral silhouettes with
placeholder names. Fonts: Bricolage Grotesque and Source Sans 3 (SIL OFL).
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

import build_step2 as s2
from build_step2 import svg, star_svg, stock_dots, act_group, burst, SUN, INK, WHITE, CORAL, LAGOON, LILAC, FLAME, STAR

HERE = Path(__file__).resolve().parent
FLAME_IN = "M0,-6 C8,4 14,12 14,24 C14,36 7,42 0,42 C-7,42 -14,36 -14,24 C-14,14 -6,8 0,-6Z"
REC = "c2"  # the layout shown at actual size and in the flow strip

CSS = s2.CSS + r"""
.note{font-size:15.5px;line-height:1.4;color:#45425E}
.note b{color:#1A1830;font-weight:700}
.lay{background:#F6F5FA;border-radius:18px;padding:22px 20px 20px;margin-bottom:44px}
.lay .hd{display:flex;align-items:baseline;gap:14px;margin-bottom:14px}
.lay .hd b{font-weight:900;font-size:50px;line-height:.9}
.lay .hd span{font-weight:900;font-size:26px}
.mainrow{display:grid;grid-template-columns:896px 1fr;gap:24px;align-items:start;margin-bottom:22px}
.mainrow .g{zoom:1.4}
.side h3{font-weight:900;font-size:17px;margin:16px 0 6px}
.side h3:first-child{margin-top:0}
.side p,.side li{font-size:15.5px;line-height:1.4;color:#45425E}
.side ol{padding-left:20px}
.side li b,.side p b{color:#1A1830;font-weight:700}
.side table{border-collapse:collapse;font-size:15px;line-height:1.3;color:#45425E;width:100%}
.side td{padding:4px 8px 4px 0;vertical-align:top;border-top:1px solid #DDDBE8}
.side td:first-child{font-weight:700;color:#1A1830;white-space:nowrap;width:118px}
.side .trade{font-size:15.5px;line-height:1.35;font-weight:700;border-left:4px solid #1A1830;padding-left:10px;margin-top:16px;color:#1A1830}
.states{display:grid;grid-template-columns:repeat(3,486px);gap:16px 11px}
.states .g{zoom:.759}
.states .tag{margin-bottom:5px}
.flow{display:flex;align-items:flex-start;background:#F6F5FA;border-radius:18px;padding:20px 0 18px 20px}
.fstep{width:320px}
.fstep .g{zoom:.5}
.fstep .cap{width:310px}
.farr{width:66px;height:240px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;font-size:13px;line-height:1.15;font-weight:700;color:#1A1830;text-align:center}
.farr i{font-style:normal;color:#8A2A45}
.fnote{margin-top:14px;font-size:15.5px;line-height:1.4;color:#45425E;max-width:1300px}
.fnote b{color:#1A1830}
.act2{display:grid;grid-template-columns:640px 853px;gap:22px;align-items:start}

/* ---------- game-pixel world: the camp ---------- */
.cs{position:relative;width:640px;height:480px;overflow:hidden;background:#4C3D9E}
.cs.wide{width:853px}
.cs .in{position:absolute;left:0;top:0;width:640px;height:480px}
.cs.wide .in{left:106px}
.cs .sc{position:absolute;left:-107px;top:0;display:block}
.cs .dim{position:absolute;left:-107px;top:0;width:854px;height:480px;background:rgba(26,16,74,.66)}
.on{background:#FFD84A !important;box-shadow:0 0 0 3px #fff,4px 6px 0 3px #2A1A6E !important;z-index:3}
.on2{background:#D8F5F1 !important;box-shadow:0 0 0 3px #00A99D,4px 6px 0 3px #2A1A6E !important;z-index:3}
.pt{display:inline-block;border:2.5px solid #2A1A6E;border-radius:8px;color:#fff;font-family:"Brico";font-weight:800;font-size:12px;line-height:15px;padding:0 5px}
.cur{position:absolute;z-index:6;display:flex;align-items:flex-end}
.cur svg{display:block}
.cur .pt{margin-left:-5px;margin-bottom:-6px}
.ptr{position:absolute;z-index:6}
.say{position:absolute;left:24px;top:402px;height:32px;background:#fff;border:3px solid #2A1A6E;border-radius:10px;box-shadow:3px 4px 0 #2A1A6E;padding:0 12px;line-height:25px;font-size:13.5px;font-weight:700;color:#2A1A6E;white-space:nowrap;transform:rotate(-.6deg)}
.hints{position:absolute;left:26px;top:449px;display:flex;gap:16px;color:#fff;font-size:12.5px;line-height:18px;font-weight:700;white-space:nowrap}
.bt{display:inline-block;min-width:18px;height:18px;border-radius:9px;background:#fff;border:2px solid #2A1A6E;color:#2A1A6E;font-family:"Brico";font-weight:800;font-size:11px;line-height:14px;text-align:center;padding:0 4px;margin-right:5px}
.row{position:absolute;left:30px;width:234px;height:30px;background:#fff;border:3px solid #2A1A6E;border-radius:10px;box-shadow:3px 4px 0 #2A1A6E;display:flex;align-items:center;justify-content:space-between;padding:0 10px}
.row .l{font-family:"Brico";font-weight:800;font-size:15px;line-height:18px;letter-spacing:-.2px;white-space:nowrap}
.row .v{font-size:12.5px;line-height:16px;font-weight:700;color:#5A4C99;white-space:nowrap;display:flex;align-items:center;gap:5px}
.row.on{left:42px}
.row.on .v{color:#2A1A6E}
.row.big{height:54px;flex-direction:column;align-items:flex-start;justify-content:center}
.row.big .l{font-size:23px;line-height:25px;letter-spacing:-.5px}
.row.big .v{font-size:12.5px}
.row.back{width:112px;height:28px}
.row.back .l{font-size:13.5px}
.swt{display:inline-block;position:relative;width:32px;height:18px;border-radius:9px;border:2.5px solid #2A1A6E;background:#D9D6E8}
.swt::after{content:"";position:absolute;left:1px;top:1px;width:11px;height:11px;border-radius:50%;background:#fff;border:2px solid #2A1A6E;box-sizing:border-box}
.swt.y{background:#FF4D6D}
.swt.y::after{left:15px}
.fc{text-align:center;padding-top:5px}
.fc svg{display:block;margin:0 auto}
.fc .nm{font-family:"Brico";font-weight:800;font-size:12px;line-height:14px;white-space:nowrap;margin-top:2px}
.fc.s .nm{font-size:11px;line-height:13px;margin-top:1px;letter-spacing:-.2px}
.fc.lk{background:#DAD7E8}
.fc.lk .nm{color:#5A4C99}
.fc .lock{position:absolute;left:50%;top:32%;margin-left:-9px}
.fe{font-size:12px;line-height:14px;font-weight:700;color:#5A4C99;padding:0 5px}
.tb{position:absolute;height:25px;background:#fff;border:3px solid #2A1A6E;border-radius:9px;font-family:"Brico";font-weight:800;font-size:12.5px;line-height:17px;padding:0 8px;white-space:nowrap;color:#5A4C99}
.tb.sel{background:#FFD84A;color:#2A1A6E;z-index:2}
.ld{display:flex;gap:4px}
.ld i{width:21px;height:21px;border-radius:50%;border:2.5px solid #2A1A6E;font-style:normal;font-family:"Brico";font-weight:800;font-size:12px;line-height:16px;text-align:center;background:#fff;color:#2A1A6E}
.ld i.x{background:#D9D6E8;border-color:#8E8AA8;color:#8E8AA8}
.ld i.p{border-style:dashed;background:#FBF6DD;color:#5A4C99}
.ld i.n{background:#FF4D6D;color:#fff;box-shadow:0 0 0 2px #FFD84A,0 0 0 4.5px #2A1A6E}
.t14{font-family:"Brico";font-weight:800;font-size:14.5px;line-height:17px;letter-spacing:-.2px;white-space:nowrap}
.t12{font-size:12px;line-height:14px;font-weight:700;color:#5A4C99;white-space:nowrap}
.dbtn{position:absolute;top:122px;width:150px;height:34px;border:3px solid #2A1A6E;border-radius:10px;box-shadow:3px 4px 0 #2A1A6E;background:#fff;text-align:center;font-family:"Brico";font-weight:800;font-size:14.5px;line-height:27px;white-space:nowrap}
.ph{position:absolute;left:40px;top:40px;width:560px;height:400px;border:5px dashed #C9BFF5;border-radius:26px;color:#fff;text-align:center}
.ph b{display:block;font-family:"Brico";font-weight:800;font-size:44px;line-height:48px;letter-spacing:-1px;margin-top:34px}
.ph span{display:block;font-size:25px;line-height:30px;font-weight:700;color:#D9D3F7;margin-top:8px}
.ph .cards{display:flex;gap:26px;justify-content:center;margin-top:30px}
.ph .cards i{width:124px;height:170px;border:5px dashed #FFD84A;border-radius:20px}
"""


# ------------------------------------------------------------------ small parts
def at(x, y, inner, extra=""):
    return f'<div style="position:absolute;left:{x}px;top:{y}px;{extra}">{inner}</div>'


SILS = [
    ('M7,54 C7,34 11,25 20,25 C29,25 33,34 33,54Z', '<circle cx="20" cy="12" r="8.5"/>'),
    ('M3,54 C3,36 8,24 20,24 C32,24 37,36 37,54Z', '<circle cx="20" cy="13" r="10"/>'),
    ('M9,54 C9,43 12,37 20,37 C28,37 31,43 31,54Z', '<circle cx="20" cy="23" r="13"/>'),
    ('M11,54 C11,30 13,21 20,21 C27,21 29,30 29,54Z', '<circle cx="20" cy="10" r="7"/>'),
    ('M4,54 L14,25 H26 L36,54Z', '<circle cx="20" cy="13" r="8.5"/>'),
    ('M7,54 C7,36 11,27 20,27 C29,27 33,36 33,54Z', '<circle cx="20" cy="15" r="8.5"/><path d="M9,9 H31 V6 H26 V2 H14 V6 H9Z"/>'),
]


def sil(kind, w, fill="#BFC2CE", op=1):
    body, head = SILS[kind % 6]
    return svg(w, round(w * 1.4), "0 0 40 56",
               f'<g fill="{fill}" stroke="{INK}" stroke-width="2.6" stroke-linejoin="round" opacity="{op}"><path d="{body}"/>{head}</g>')


def lock(size=14, col=INK):
    return svg(size, round(size * 1.15), "0 0 14 16",
               f'<path d="M4,7V5a3,3 0 0 1 6,0V7" fill="none" stroke="{col}" stroke-width="2.4"/><rect x="1.5" y="7" width="11" height="8" rx="2.2" fill="{col}"/>',
               'style="display:inline-block;vertical-align:-2px"')


def bt(t):
    return f'<span class="bt">{t}</span>'


def hints(*items):
    return '<div class="hints">' + "".join(f'<span>{bt(b)}{t}</span>' for b, t in items) + "</div>"


def say(t):
    return f'<div class="say">{t}</div>'


def ptr(x, y, col=CORAL):
    return (f'<div class="ptr" style="left:{x}px;top:{y}px">' + svg(28, 26, "0 0 28 26",
            f'<path d="M3,9 H14 V3 L25,13 L14,23 V17 H3Z" fill="{col}" stroke="#fff" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M3,9 H14 V3 L25,13 L14,23 V17 H3Z" fill="{col}" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>') + "</div>")


def cur(x, y, p):
    """A player's cursor: an arrow with the player tag, pinned over the lower right of a sticker."""
    col = CORAL if p == 1 else LAGOON
    d = "M3,3 L3,20 L8,15.5 L12,23 L16,21 L12,14 L19,14Z"
    return (f'<div class="cur" style="left:{x}px;top:{y}px">' + svg(24, 27, "0 0 24 27",
            f'<path d="{d}" fill="{col}" stroke="#fff" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="{col}" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round"/>')
            + f'<span class="pt" style="background:{col}">P{p}</span></div>')


def fcard(x, y, name, kind, w=72, rot=0, tag=None, cls="", state="ok", note=""):
    h = round(w * 1.3) + (2 if w < 64 else 0)
    small = " s" if w < 64 else ""
    sw = round(w * .6)
    tagh = ""
    if tag:
        col = CORAL if tag == "P1" else LAGOON
        tagh = f'<span class="tab" style="background:{col}">{tag}</span>'
    if state == "empty":
        return (f'<div class="st dash fc{small} {cls}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;transform:rotate({rot}deg)">{tagh}'
                f'{sil(0, sw, "#E4DFC6", .55)}<div class="nm" style="color:{LILAC}">{note}</div></div>')
    if state == "lock":
        return (f'<div class="st fc lk{small} {cls}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;transform:rotate({rot}deg)">'
                f'{sil(kind, sw, "#A9A5C2", .7)}<div class="lock">{lock(18)}</div><div class="nm">{note}</div></div>')
    return (f'<div class="st fc{small} {cls}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;transform:rotate({rot}deg)">{tagh}'
            f'{sil(kind, sw)}<div class="nm">{name}</div></div>')


def swap(x, y):
    return at(x, y, svg(22, 22, "-11 -11 22 22",
              f'<circle r="9.5" fill="#fff" stroke="{INK}" stroke-width="2.2"/>'
              f'<path d="M-5,-2.5H4M1.5,-5.5L4.5,-2.5L1.5,.5M5,3H-4M-1.5,0L-4.5,3L-1.5,6" fill="none" stroke="{INK}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'), "z-index:4")


def acts(done, cur_, top, x0=8, step=100):
    return "".join(f'<div style="position:absolute;left:{x0 + a * step}px;top:{top}px"><div class="s10">Act {a + 1}</div>{act_group(a, done, cur_, 20)}</div>' for a in range(3))


def short_acts(top, x0=8):
    body = "".join(s2.enc(i if i < 4 else 3, 0, None, 11 + i * 20 + (3 if i == 4 else 0), 12) for i in range(5))
    return f'<div style="position:absolute;left:{x0}px;top:{top}px"><div class="s10">Short run: 4 fights, then a boss</div>{svg(120, 24, "0 0 120 24", body)}</div>'


def stocks(x, y, left, total, label, rot=2, w=128, plus=False):
    b = at(w - 8, 4, burst("+1", CORAL, 40, 15), "z-index:4") if plus else ""
    return (f'<div class="st" style="left:{x}px;top:{y}px;width:{w}px;height:50px;transform:rotate({rot}deg);padding:6px 9px">{b}'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px"><span class="s10">{label}</span>'
            f'<span class="bn" style="font-size:13px;line-height:14px;white-space:nowrap">{left} of {total}</span></div>{stock_dots(left, total)}</div>')


def keystone(x, y, rot=-2):
    return (f'<div class="keyp" style="left:{x}px;top:{y}px;height:40px;transform:rotate({rot}deg)">{star_svg(18, sw=0)}'
            f'<div><div class="s10">Keystone</div><div class="bn">Plague Bearer</div></div></div>')


def locktag(x, y, rot=-3, w=124):
    return (f'<div class="st" style="left:{x}px;top:{y}px;width:{w}px;height:52px;transform:rotate({rot}deg);padding:4px 8px">'
            f'<div class="s10">{lock(10, LILAC)} Set for this run</div><div class="t12" style="color:{INK}">NG+ level 0</div><div class="t12" style="color:{INK}">Team attack off</div></div>')


def switch(on):
    return f'<span class="swt{" y" if on else ""}"></span><span class="bn" style="font-size:13px;color:{INK}">{"On" if on else "Off"}</span>'


def ladder(sel, top_ok, one_only, lo=0, hi=11):
    out = ""
    for i in range(lo, hi):
        cls = "n" if i == sel else ("" if i <= top_ok else ("p" if i <= one_only else "x"))
        out += f'<i class="{cls}">{i}</i>'
    return f'<div class="ld">{out}</div>'


def title(x=22, y=12):
    body = (f'<circle cx="19" cy="19" r="14.5" fill="{INK}"/><circle cx="19" cy="19" r="11.5" fill="#fff"/>'
            f'<circle cx="15.4" cy="19" r="5" fill="{CORAL}" stroke="{INK}" stroke-width="2"/><circle cx="22.6" cy="19" r="5" fill="{LAGOON}" stroke="{INK}" stroke-width="2"/>'
            f'<text x="41" y="27" font-family="Brico" font-weight="800" font-size="23" letter-spacing="-.5" fill="#fff" stroke="{INK}" stroke-width="4.5" paint-order="stroke" stroke-linejoin="round">Envoy camp</text>')
    return at(x, y, svg(190, 38, "0 0 190 38", body))


def fire(x, y, s):
    return (f'<g transform="translate({x} {y})"><circle cy="{-40 * s:.0f}" r="{150 * s:.0f}" fill="{SUN}" opacity=".08"/><circle cy="{-40 * s:.0f}" r="{90 * s:.0f}" fill="{SUN}" opacity=".1"/>'
            f'<g transform="scale({s})"><rect x="-44" y="-10" width="88" height="14" rx="7" fill="#231558" transform="rotate(14)"/><rect x="-44" y="-10" width="88" height="14" rx="7" fill="#231558" transform="rotate(-14)"/>'
            f'<g transform="translate(0 -56)"><path d="{FLAME}" fill="{CORAL}"/><path d="{FLAME_IN}" fill="{SUN}"/></g></g></g>')


def tent(px, py, base, half, face="#6253B6"):
    return (f'<path d="M{px},{py} L{px - half},{base} H{px + half}Z" fill="{face}"/>'
            f'<path d="M{px},{py + (base - py) * .45:.0f} L{px - half * .2:.0f},{base} H{px + half * .2:.0f}Z" fill="#2C1E70"/>'
            f'<path d="M{px},{py} L{px + half},{base} H{px + half * .45:.0f}Z" fill="#000" opacity=".13"/>')


def scene(kind):
    """The backdrop. Flat, no outlines: anything outlined in grape ink is a sticker you can move to."""
    stars = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{SUN}" opacity=".75"/>' for x, y, r in
                    ((-70, 60, 2), (52, 46, 1.6), (212, 22, 2.2), (300, 150, 1.6), (372, 28, 1.8), (470, 16, 1.5), (628, 150, 2), (700, 40, 2.2), (268, 96, 1.5), (-30, 170, 1.6)))
    if kind == 1:
        g = 388
        body = (f'<circle cx="596" cy="150" r="64" fill="#5849AE"/>{stars}'
                f'<ellipse cx="80" cy="{g + 6}" rx="330" ry="74" fill="#42338F"/><ellipse cx="640" cy="{g + 6}" rx="300" ry="96" fill="#42338F"/>'
                f'{tent(338, 318, g, 50)}{tent(566, 312, g, 56)}<rect x="-107" y="{g}" width="854" height="{480 - g}" fill="#33257C"/>{fire(452, g + 2, .42)}')
    else:
        g = 304
        body = (f'<circle cx="320" cy="74" r="58" fill="#5849AE"/>{stars}'
                f'<ellipse cx="-20" cy="{g + 6}" rx="300" ry="70" fill="#42338F"/><ellipse cx="660" cy="{g + 6}" rx="300" ry="80" fill="#42338F"/>'
                f'{tent(138, 126, g, 132)}{tent(502, 122, g, 134)}<rect x="-107" y="{g}" width="854" height="{480 - g}" fill="#33257C"/>{fire(320, g - 4, .62)}')
    return svg(854, 480, "-107 0 854 480", f'<rect x="-107" width="854" height="480" fill="#4C3D9E"/>{body}', 'class="sc"')


def dialog(x, y):
    mini = "".join(f'<span style="display:inline-block;margin-right:4px">{act_group(a, 6, 6, 17, 5)}</span>' for a in range(3))
    return (f'<div class="dim" style="z-index:7"></div><div class="st" style="left:{x}px;top:{y}px;width:344px;height:176px;transform:rotate(-1.2deg);padding:10px 14px;z-index:8">'
            f'<div class="hl" style="font-size:22px;line-height:25px">Abandon the saved run?</div>'
            f'<div class="sub" style="font-size:13px;line-height:16px;margin-top:3px">Act 2, fight 3 and its 3 stocks will be gone for good.</div>'
            f'<div style="margin-top:6px;height:24px;white-space:nowrap">{mini}</div>'
            f'<div class="dbtn on" style="left:14px">Keep the run</div><div class="dbtn" style="left:178px;background:{CORAL};color:#fff">Abandon it</div>'
            f'{ptr(-16, 126)}</div>')


def frame(inner, wide=False):
    return f'<div class="cs{" wide" if wide else ""}"><div class="in">{inner}</div></div>'


SAY = {
    "main": "Pick up at act 2, fight 3 with the saved party.",
    "first": "Three acts. Each is 3 fights, then a boss. One pool of 4 stocks.",
    "join": "Player 2 is in: 5 stocks together. Pick two fighters, then start.",
    "pick": "Bring two fighters each. You swap between your two mid-fight.",
    "ng": "Together you play the lower level. P2 has opened 1, so 1 is the top.",
    "ta": "On: your attacks hit your partner too. Fixed once the run starts.",
}


# ------------------------------------------------------------------ C1: the sticker list
def c1_rows(state):
    saved = state not in ("first", "join")
    hover = {"main": "go", "first": "go", "join": "go", "pick": "fighters", "ng": "ng", "ta": "ta", "abandon": "new"}[state]
    first = state == "first"
    ngv = (f'{lock(11, LILAC)} 0 only' if first else ("1" if state == "ng" else "0"))
    items = [("go", "Continue run" if saved else "Start run", "Act 2, fight 3. 3 of 5 stocks left." if saved else "A new full run, from act 1.")]
    if saved:
        items.append(("new", "New run", ""))
    items += [("fighters", "Fighters", "2 each"), ("len", "Run length", "Full, 3 acts"), ("ta", "Team attack", switch(state == "ta")),
              ("ng", "NG+ level", ngv), ("col", "Collection", "9 of 40" if first else "14 of 40"), ("back", "Back", "")]
    rots = [-1.2, .9, -.7, 1, -.9, .7, -1.1, 1.2]
    out, y = "", 58
    for i, (k, lab, val) in enumerate(items):
        on = k == hover
        cls = "row" + (" big" if k == "go" else "") + (" back" if k == "back" else "") + (" on" if on else "")
        rot = 0 if on else rots[i]
        v = f'<span class="v">{val}</span>' if val else ""
        out += f'<div class="{cls}" style="top:{y}px;transform:rotate({rot}deg)"><span class="l">{lab}</span>{v}</div>'
        if on:
            out += ptr(10, y + (14 if k == "go" else 2))
        y += 62 if k == "go" else 36
    return out


def c1_sheet():
    names = "ABCDEFGHIJKLMNO"
    locked = {9: "Beat act 2", 13: "Win a run", 14: "Win NG+ 2"}
    cards = ""
    for i in range(15):
        x, y = 12 + (i % 5) * 65, 50 + (i // 5) * 87
        if i in locked:
            cards += fcard(x, y, "", i, 58, state="lock", note=locked[i])
            continue
        tag = {0: "P1", 1: "P1", 2: "P2"}.get(i)
        cls = "on" if i == 1 else ("on2" if i == 6 else "")
        cards += fcard(x, y, f"Fighter {names[i]}", i, 58, tag=tag, cls=cls)
    cards += cur(12 + 65 + 47, 50 + 64, 1) + cur(12 + 65 + 47, 50 + 87 + 64, 2)
    return (f'<div class="st" style="left:270px;top:44px;width:348px;height:348px;transform:rotate(.7deg);z-index:5">'
            f'<div style="position:absolute;left:12px;top:7px"><span class="hl" style="font-size:21px;line-height:24px">Fighters</span>'
            f'<span class="t12" style="margin-left:10px">Tagged ones are in the party. A swaps one in.</span></div>'
            f'{cards}<div class="t12" style="position:absolute;left:12px;top:318px">{lock(11, LILAC)} 3 still locked. Each says what opens it.</div></div>')


def c1(state, wide=False):
    saved = state not in ("first", "join")
    p = [scene(1), title(), c1_rows(state)]
    if state == "pick":
        p.append(c1_sheet())
    else:
        p += [fcard(292, 54, "Fighter A", 0, 72, -3, "P1"), fcard(368, 60, "Fighter B", 1, 72, 2), swap(354, 92)]
        if state == "first":
            p.append(f'<div class="st dash" style="left:462px;top:58px;width:152px;height:92px;transform:rotate(2deg);padding:8px 10px">'
                     f'<span class="tab" style="background:{LAGOON}">P2</span><div class="t14" style="margin-top:4px">Player 2</div>'
                     f'<div class="fe" style="padding:0;margin-top:5px;line-height:20px;white-space:nowrap">{bt("Start")}Join locally<br>{bt("Y")}Play online</div></div>')
        elif state == "join":
            p += [fcard(468, 58, "", 0, 72, -2, "P2", "on2", "empty", "Pick"), fcard(544, 54, "", 0, 72, 3, None, "", "empty", "Pick"),
                  cur(468 + 60, 58 + 82, 2), at(566, 18, burst("P2|joined", LAGOON, 62, 13), "z-index:5")]
        else:
            p += [fcard(468, 58, "Fighter C", 2, 72, -2, "P2"), fcard(544, 54, "Fighter D", 3, 72, 3), swap(530, 92)]
        if saved:
            p.append(f'<div class="st" style="left:290px;top:182px;width:312px;height:48px;background:{SUN};transform:rotate(-1deg)">'
                     f'<span class="tab" style="background:{INK};left:auto;right:-8px;transform:rotate(5deg)">Saved run</span>{acts(6, 6, 5)}</div>')
            if state == "ng":
                p.append(f'<div class="st on" style="left:284px;top:244px;width:318px;height:92px;padding:7px 10px;transform:rotate(.6deg)">'
                         f'<div style="display:flex;justify-content:space-between;margin-bottom:8px"><span class="t14">NG+ level 1</span><span class="t12" style="color:{INK}">for the next new run</span></div>'
                         f'{ladder(1, 1, 3)}<div class="t12" style="margin-top:9px;color:{INK}">P1 has opened 3. P2 has opened 1. {lock(10, "#8E8AA8")} not beaten yet.</div></div>')
            else:
                p += [stocks(296, 242, 3, 5, "Team stocks"), keystone(438, 240), locktag(452, 290, 2)]
        else:
            two = state == "join"
            p.append(f'<div class="st" style="left:290px;top:182px;width:312px;height:48px;transform:rotate(-1deg)">'
                     f'<span class="tab" style="background:{INK};left:auto;right:-8px;transform:rotate(5deg)">A full run</span>{acts(0, None, 5)}</div>')
            p.append(stocks(296, 242, 5 if two else 4, 5 if two else 4, "Team stocks" if two else "Solo stocks", plus=two))
    if state == "abandon":
        p.append(dialog(148, 132))
        p.append(hints(("A", "Choose"), ("B", "Keep the run")).replace('class="hints"', 'class="hints" style="z-index:9"'))
    else:
        p.append(say(SAY[state]))
        go = "Continue run" if saved else "Start run"
        h = {"main": [("A", "Choose"), ("B", "Main menu"), ("Start", go)],
             "first": [("A", "Choose"), ("B", "Main menu"), ("Start", go)],
             "join": [("A", "Choose"), ("B", "Main menu"), ("Start", go), ("P2: hold B", "Leave")],
             "pick": [("A", "Swap in"), ("B", "Done"), ("P2: hold B", "Leave")],
             "ng": [("Left / Right", "Change level"), ("B", "Main menu"), ("Start", go)],
             "ta": [("A", "Switch"), ("B", "Main menu"), ("Start", go)]}[state]
        p.append(hints(*h))
    return frame("".join(p), wide)


# ------------------------------------------------------------------ C2: the party is the menu
def c2_tray(x, p, cards, hov):
    out = ""
    for i, (nm, kind, st) in enumerate(cards):
        cx = 18 + i * 66
        if st == "lock":
            out += fcard(cx, 6, "", kind, 58, state="lock", note=nm)
        else:
            out += fcard(cx, 6, nm, kind, 58, cls=("on" if p == 1 else "on2") if i == hov else "", tag=f"P{p}" if st == "in" else None)
    arrows = "".join(f'<svg width="10" height="16" viewBox="0 0 10 16" style="position:absolute;left:{ax}px;top:38px"><path d="{d}" fill="{INK}"/></svg>'
                     for ax, d in ((4, "M9,1V15L1,8Z"), (284, "M1,1V15L9,8Z")))
    return (f'<div class="st" style="left:{x}px;top:296px;width:302px;height:96px;z-index:5;transform:rotate({-.6 if p == 1 else .6}deg)">{out}{arrows}'
            f'{cur(18 + hov * 66 + 47, 6 + 64, p)}</div>')


def c2(state, wide=False):
    saved = state not in ("first", "join")
    hov = {"main": "run", "first": "run", "join": "run", "pick": "b", "ng": "ng", "ta": "ta", "abandon": "run"}[state]
    p = [scene(2), title()]
    # the run ticket and its tabs
    if saved:
        sel = 1 if state == "abandon" else 0
        tabs = [("Continue", 226), ("New run", 309), ("Short run", 386)]
    else:
        sel, tabs = 0, [("Full run", 226), ("Short run", 302)]
    for i, (t, x) in enumerate(tabs):
        p.append(f'<div class="tb{" sel" if i == sel else ""}" style="left:{x}px;top:{35 if i == sel else 37}px;transform:rotate({(-2, 2, -1.5)[i]}deg)">{t}</div>')
    if saved and sel == 0:
        head, sub, a = "Continue run", "Act 2, fight 3. Saved after fight 2.", acts(6, 6, 47, 10)
    else:
        head, sub, a = ("New run" if saved else "Start run"), "Three acts. Each is 3 fights, then a boss.", acts(0, None, 47, 10)
    p.append(f'<div class="st{" on" if hov == "run" else ""}" style="left:140px;top:60px;width:320px;height:92px;transform:rotate(-1deg)">'
             f'<div style="padding:5px 10px 0"><div class="hl" style="font-size:22px;line-height:24px">{head}</div><div class="sub">{sub}</div></div>{a}</div>')
    if hov == "run" and state != "abandon":
        p.append(cur(140 + 306, 60 + 80, 1))
    if saved:
        p += [stocks(474, 50, 3, 5, "Team stocks", 3), keystone(480, 108), locktag(12, 92)]
    elif state == "join":
        p.append(stocks(474, 60, 5, 5, "Team stocks", 3, plus=True))
    else:
        p.append(stocks(474, 60, 4, 4, "Solo stocks", 3))
    # the party
    p += [fcard(48, 170, "Fighter A", 0, 84, -3, "P1"), fcard(140, 176, "Fighter B", 1, 84, 2, None, "on" if hov == "b" else ""), swap(125, 216)]
    if state == "first":
        p.append(f'<div class="st dash" style="left:414px;top:176px;width:178px;height:100px;transform:rotate(2deg);padding:10px 12px">'
                 f'<span class="tab" style="background:{LAGOON}">P2</span><div class="t14" style="margin-top:4px">Player 2</div>'
                 f'<div class="fe" style="padding:0;margin-top:5px;line-height:20px;white-space:nowrap">{bt("Start")}Join locally<br>{bt("Y")}Play online</div></div>')
    elif state == "join":
        p += [fcard(414, 174, "", 0, 84, -2, "P2", "on2", "empty", "Pick"), fcard(506, 168, "", 0, 84, 3, None, "", "empty", "Pick"),
              cur(414 + 72, 174 + 96, 2), at(548, 126, burst("P2|joined", LAGOON, 62, 13), "z-index:5")]
    else:
        p += [fcard(414, 174, "Fighter C", 2, 84, -2, "P2", "on2" if state in ("main", "ng", "ta") else ""),
              fcard(506, 168, "Fighter D", 3, 84, 3, None, "on2" if state == "pick" else ""), swap(491, 212)]
        if state in ("main", "ng", "ta"):
            p.append(cur(414 + 72, 174 + 96, 2))
    # the bottom row: rules and the collection
    if state == "pick":
        p.append(c2_tray(14, 1, [("Fighter B", 1, "in"), ("Fighter E", 4, ""), ("Fighter F", 5, ""), ("Beat act 2", 9, "lock")], 2))
        p.append(c2_tray(324, 2, [("Fighter D", 3, "in"), ("Fighter G", 0, ""), ("Fighter H", 2, ""), ("Fighter I", 4, "")], 1))
    else:
        first = state == "first"
        p.append(f'<div class="st" style="left:24px;top:330px;width:76px;height:36px;transform:rotate(-2deg);text-align:center"><span class="t14" style="line-height:29px">Back</span></div>')
        p.append(f'<div class="st{" on" if hov == "ta" else ""}" style="left:116px;top:320px;width:152px;height:56px;transform:rotate({0 if hov == "ta" else 1.2}deg);padding:6px 10px">'
                 f'<div class="t14">Team attack</div><div style="display:flex;align-items:center;gap:6px;margin-top:5px">{switch(state == "ta")}</div></div>')
        ngsub = f'{lock(10, LILAC)} Beat a run to open 1' if first else ("Left or right to change" if hov == "ng" else "0 to 1 open together")
        p.append(f'<div class="st{" on" if hov == "ng" else ""}" style="left:284px;top:320px;width:172px;height:56px;transform:rotate({0 if hov == "ng" else -1}deg);padding:6px 10px">'
                 f'<div class="t14">NG+ level {1 if state == "ng" else 0}</div><div class="t12" style="margin-top:6px{";color:" + INK if hov == "ng" else ""}">{ngsub}</div></div>')
        p.append(f'<div class="st" style="left:472px;top:320px;width:144px;height:56px;transform:rotate(1.5deg);padding:6px 10px">'
                 f'<div class="t14">Collection</div><div class="t12" style="margin-top:6px">{"9" if first else "14"} of 40 found</div></div>')
        if hov == "ta":
            p.append(cur(116 + 138, 320 + 42, 1))
        if hov == "ng":
            p.append(cur(284 + 158, 320 + 42, 1))
            p.append(f'<div class="st" style="left:226px;top:184px;width:182px;height:124px;padding:7px 10px;transform:rotate(-.8deg);z-index:4">'
                     f'<div class="t14" style="margin-bottom:7px">NG+ level</div>{ladder(1, 1, 3, 0, 6)}<div style="height:6px"></div>{ladder(1, 1, 3, 6, 11)}'
                     f'<div class="t12" style="margin-top:7px;color:{INK};white-space:normal;line-height:13px">P1 has opened 3,<br>P2 has opened 1.</div></div>')
    if state == "abandon":
        p.append(dialog(148, 150))
        p.append(hints(("A", "Choose"), ("B", "Keep the run")).replace('class="hints"', 'class="hints" style="z-index:9"'))
    else:
        p.append(say(SAY[state]))
        go = "Continue run" if saved else "Start run"
        h = {"main": [("Stick", "Move"), ("A", "Choose"), ("L R", "Other tickets"), ("B", "Main menu"), ("Start", go)],
             "first": [("Stick", "Move"), ("A", "Choose"), ("L R", "Other tickets"), ("B", "Main menu"), ("Start", go)],
             "join": [("Stick", "Move"), ("A", "Choose"), ("B", "Main menu"), ("Start", go), ("P2: hold B", "Leave")],
             "pick": [("Left / Right", "Browse"), ("A", "Swap in"), ("B", "Close"), ("P2: hold B", "Leave")],
             "ng": [("Left / Right", "Change level"), ("Stick", "Move"), ("B", "Main menu"), ("Start", go)],
             "ta": [("A", "Switch"), ("Stick", "Move"), ("B", "Main menu"), ("Start", go)]}[state]
        p.append(hints(*h))
    return frame("".join(p), wide)


# ------------------------------------------------------------------ sheet
STATES = [
    ("first", "First time, solo", "No save, one player. NG+ is held at 0 and says why. The P2 slot says how to join, locally or online."),
    ("join", "P2 joining", "P2 pressed Start. Their slots appear, the stock pool goes from 4 to 5, and they are asked to pick. Hold B on controller 2 leaves."),
    ("pick", "Fighters pick", None),
    ("ng", "NG+ level", "Levels both players have opened are solid, levels only one has opened are dashed, the rest are locked."),
    ("ta", "Team attack", "A flips the switch. Online, only the host's cursor can; the guest sees the same sticker with the host's choice."),
    ("abandon", "Abandon the saved run?", None),
]
PICK_CAP = {
    "c1": "A sticker sheet covers the party side. Both cursors are on it at once; tagged fighters are in the party; locked ones name what opens them.",
    "c2": "A tray opens under each player's own pair, so both can browse at once. The fighter being swapped out stays lit.",
}
ABAN_CAP = {
    "c1": "Shown after A on New run. The cursor starts on Keep the run, and B also keeps it.",
    "c2": "Shown after A on the New run or Short run ticket. The cursor starts on Keep the run, and B also keeps it.",
}


def states(fn, key):
    out = ""
    for st, name, cap in STATES:
        cap = cap or (PICK_CAP[key] if st == "pick" else ABAN_CAP[key])
        out += f'<div><div class="tag">{name}</div><div class="g">{fn(st)}</div><p class="cap">{cap}</p></div>'
    return f'<div class="states">{out}</div>'


def layout(tag, name, fn, key, side):
    return (f'<div class="lay"><div class="hd"><b>{tag}</b><span>{name}</span></div>'
            f'<div class="mainrow"><div><div class="g">{fn("main")}</div><p class="cap"><b>Main state:</b> two players, a saved run at act 2, fight 3.</p></div>'
            f'<div class="side">{side}</div></div>{states(fn, key)}</div>')


SIDE1 = """<h3>The idea</h3>
<p>A list of stickers down the left is the whole menu. The party and the run stand on the right as a status board you look at but never move onto.</p>
<h3>Reading order</h3>
<ol><li><b>The big sticker</b>, top left: what Start does right now.</li><li><b>The list</b> under it: one row per thing you can change, each with its current value on the row.</li>
<li><b>The party</b>, top right: who is in, two fighters each.</li><li><b>The run</b>, under the party: where the save is, stocks left, keystone, and the rules it was started with.</li>
<li><b>The white strip</b>: one line about the hovered row.</li></ol>
<h3>Buttons</h3>
<table><tr><td>Up / Down</td><td>Move the one cursor. Player 1 owns it.</td></tr><tr><td>A</td><td>Choose the row, or flip Team attack.</td></tr>
<tr><td>Left / Right</td><td>Change Run length and NG+ level on their rows.</td></tr><tr><td>Start</td><td>Continue run (or Start run) from any row.</td></tr>
<tr><td>B</td><td>Main menu.</td></tr><tr><td>P2 Start</td><td>Join. Hold B on controller 2 to leave.</td></tr></table>
<p class="trade">One column, one cursor, nothing to learn. Player 2 has nothing to do here except inside Fighters, and the party is decoration rather than something you touch.</p>"""

SIDE2 = """<h3>The idea</h3>
<p>There is no list. The run ticket, the four fighters and the rules are the stickers, laid out as the camp itself, and each player walks their own cursor across them.</p>
<h3>Reading order</h3>
<ol><li><b>The ticket</b>, top: the run. Its tabs are the other tickets you could take instead (a new run, a short run).</li>
<li><b>The party</b>, middle: P1's pair by the left tent, P2's by the right. A on a fighter opens that slot.</li>
<li><b>The rules</b>, bottom: Team attack, NG+ level, and the Collection, with Back in the corner.</li><li><b>The white strip</b>: one line about what P1 is on.</li></ol>
<h3>Buttons</h3>
<table><tr><td>Stick</td><td>Move your cursor between stickers: three rows, at most four across.</td></tr><tr><td>A</td><td>Choose: use the ticket, open a fighter slot, flip Team attack.</td></tr>
<tr><td>L / R</td><td>Flip to the other tickets from anywhere.</td></tr><tr><td>Start</td><td>Use the ticket on top from anywhere.</td></tr>
<tr><td>B</td><td>Main menu (P1). P2: hold B to leave.</td></tr><tr><td>P2</td><td>Has a cursor too: own fighters and the Collection. Tickets and rules are P1's.</td></tr></table>
<p class="trade">Both players have something to do, and the party is the thing you touch. It asks for a two-way cursor, and the three rows have to stay this tidy for it to read.</p>"""


def placeholder(big, small, cards=False):
    c = '<div class="cards"><i></i><i></i><i></i></div>' if cards else ""
    return f'<div class="cs" style="background:#33257C"><div class="ph"><b>{big}</b><span>{small}</span>{c}</div></div>'


def arrow(fwd, back):
    a = svg(54, 16, "0 0 54 16", '<path d="M2,8H48M40,2L49,8L40,14" fill="none" stroke="#1A1830" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>')
    b = svg(54, 16, "0 0 54 16", '<path d="M52,8H6M14,2L5,8L14,14" fill="none" stroke="#8A2A45" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="5 4"/>') if back else ""
    return f'<div class="farr"><span>{fwd}</span>{a}{b}<i>{back}</i></div>'


def flow(fn):
    f = lambda scr, cap: f'<div class="fstep"><div class="g">{scr}</div><p class="cap">{cap}</p></div>'
    return ('<div class="flow">'
            + f(s2.screen(3, s2.p2, "saved"), "<b>Main menu.</b> Envoy row hovered; the panel shows the save.")
            + arrow("A", "B")
            + f(fn("main"), "<b>Camp.</b> Set the party and the rules. <b>Start</b>, or <b>A</b> on the run, begins. With a save present, a new run asks first.")
            + arrow("A or Start", "B")
            + f(placeholder("Keystone pick", "Choose 1 of 3. Designed in a later step.", True), "<b>Keystone pick</b> (placeholder). New runs only. <b>A</b> takes a keystone. <b>B</b> returns to the camp; nothing has been saved yet.")
            + arrow("A", "")
            + f(placeholder("First fight", "Act 1, fight 1. HUD designed in a later step."), "<b>First fight.</b> No way back from here; the run has begun. Rules and party are fixed.")
            + "</div>")


def html():
    rec_fn, rec_name = (c2, "C2") if REC == "c2" else (c1, "C1")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Envoy UI step 3</title><style>{CSS}</style></head>
<body><div id="c">
<div class="top"><h1>The Envoy camp</h1>
<p>Step 3 of the UI design. One choice: the camp layout, C1 or C2. Drive cards, the keystone pick, the HUD, rewards, the map and results are not designed yet.</p></div>
<div class="key"><span><i style="background:#fff;box-shadow:inset 0 0 0 2.5px {INK}"></i>Outlined in grape ink: a sticker. Stickers are the only things a cursor can land on or that carry facts.</span>
<span><i style="background:#4C3D9E"></i>Flat violet, no outlines: the proposed backdrop, a paper-cut camp at night (two tents, a fire, a moon).</span>
<span><i style="background:{SUN};box-shadow:inset 0 0 0 2.5px {INK}"></i>Sunny with a white edge: the cursor. Coral arrow is P1, lagoon is P2.</span></div>

{layout("C1", "The sticker list", c1, "c1", SIDE1)}
{layout("C2", "The party is the menu", c2, "c2", SIDE2)}

<div class="sec"><h2>From the main menu to the first fight</h2>
<p class="lede">The same four steps for either layout, drawn with {rec_name}. Solid arrows go forward, dashed arrows are the Back paths.</p>
{flow(rec_fn)}
<p class="fnote"><b>Continue run skips the keystone pick.</b> From the camp it goes straight to the saved run's next fight, with the keystone, party, NG+ level and Team attack it was started with. A run is saved only between fights, so the camp never shows a save in the middle of one.</p></div>

<div class="sec"><h2>{rec_name} at actual size, and in widescreen</h2>
<p class="lede">Left: 640 by 480, the size the game renders before upscaling. Smallest text is 11 px (act names, sticker captions); names are 12 px and up. Right: 16:9 at the same scale.</p>
<div class="act2"><div><div class="g">{rec_fn("main")}</div><p class="cap"><b>4:3, 640 by 480.</b></p></div>
<div><div class="g">{rec_fn("main", True)}</div><p class="cap"><b>16:9, 853 by 480.</b> Stickers keep their 4:3 positions and size, centred as one block and never stretched. Only the backdrop grows: more hill and sky at each side. Nothing is placed in the extra width, so a 4:3 player misses nothing.</p></div></div></div>

<div class="rec" style="grid-template-columns:150px 1fr"><h2>Recommended</h2>
<p><b>C2, the party is the menu.</b> The camp is where two people get ready together, and C2 is the only layout where both of them hold a cursor and the fighters are the things you touch; its three rows (run, party, rules) keep the loose stickers in a fixed reading order. C1 is the fallback if a two-way cursor feels like too much: it is the plainest, but it leaves Player 2 watching.</p></div>
<p class="foot">Original vector art. Fonts: Bricolage Grotesque, Source Sans 3 (SIL OFL). Fighters are neutral silhouettes with placeholder names; drive and keystone names are the step 1 samples; unlock conditions and collection counts are invented for the mock. The grey main-menu frame is the step 2 placeholder for retail parts.</p>
</div></body></html>"""


def main():
    src = HERE / "step3.html"
    src.write_text(html(), encoding="utf-8")
    (HERE / "preview").mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
        page.goto(src.as_uri())
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(300)
        bad = page.evaluate("""() => [...document.querySelectorAll('.g *')].filter(e => e.children.length === 0 && !(e instanceof SVGElement) && (e.scrollWidth > e.clientWidth + 1) && getComputedStyle(e).display !== 'inline').map(e => e.className + ': ' + e.textContent.slice(0, 40))""")
        for b in sorted(set(bad)):
            print("overflow:", b)
        wide = page.evaluate("""() => [...document.querySelectorAll('.say, .hints')].filter(e => e.offsetLeft + e.offsetWidth > 620).map(e => e.className + ' too wide: ' + e.textContent.slice(0, 50))""")
        for b in sorted(set(wide)):
            print(b)
        page.locator("#c").screenshot(path=str(HERE / "preview" / "step3-camp.png"), type="png")
        print(page.evaluate("document.getElementById('c').offsetHeight"))
        browser.close()


if __name__ == "__main__":
    main()
