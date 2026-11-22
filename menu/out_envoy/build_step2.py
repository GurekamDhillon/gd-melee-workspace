#!/usr/bin/env python3
"""Envoy UI, step 2: the main-menu row and its panel. One review sheet.

Writes step2.html beside this file and renders preview/step2-main-menu.png (1600 px wide) with
headless Chromium, like build_spread.py. Everything inside a `.g` box is authored in game pixels
(640x480 native) and scaled with CSS zoom, so the actual-size view is a fair legibility check.
Original vector art only. Retail menu parts are neutral grey placeholders. Fonts: Bricolage
Grotesque and Source Sans 3 (SIL OFL).
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent

SUN, INK, WHITE, CORAL, LAGOON, LILAC = "#FFD84A", "#2A1A6E", "#FFFFFF", "#FF4D6D", "#00A99D", "#5A4C99"
FLAME = "M0,-44 C16,-26 32,-10 32,14 C32,36 16,50 0,50 C-16,50 -32,36 -32,14 C-32,0 -22,-10 -17,-24 C-12,-14 -6,-14 0,-44Z"
STAR = "M0,-10 L3,-3.2 L10.2,-3 L4.6,1.6 L6.4,8.8 L0,4.8 L-6.4,8.8 L-4.6,1.6 L-10.2,-3 L-3,-3.2Z"
BURST = "M0,-27 L7,-17 L19,-19 L17,-7 L27,0 L17,7 L19,19 L7,17 L0,27 L-7,17 L-19,19 L-17,7 L-27,0 L-17,-7 L-19,-19 L-7,-17Z"

CSS = r"""
@font-face{font-family:"SS3";src:url("../SourceSans3/SourceSans3-Semibold.otf");font-weight:600}
@font-face{font-family:"SS3";src:url("../SourceSans3/SourceSans3-Bold.otf");font-weight:700}
@font-face{font-family:"SS3";src:url("../SourceSans3/SourceSans3-Black.otf");font-weight:900}
@font-face{font-family:"Brico";src:url("fonts/BricolageGrotesque.ttf");font-weight:200 800}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#E6E5EC}
body{width:1600px;font-family:"SS3";font-weight:600;color:#1A1830;-webkit-font-smoothing:antialiased}
#c{width:1600px;padding:44px 40px 40px}
.top{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:22px}
.top h1{font-weight:900;font-size:54px;line-height:1;letter-spacing:-1px}
.top p{font-size:19px;line-height:1.35;max-width:660px;color:#45425E;text-align:right}
.key{display:flex;gap:26px;align-items:center;font-size:15.5px;color:#45425E;margin-bottom:34px;background:#F6F5FA;border-radius:12px;padding:12px 18px}
.key i{display:inline-block;width:34px;height:18px;border-radius:4px;vertical-align:-3px;margin-right:8px}
h2{font-weight:900;font-size:30px;line-height:1.1;margin-bottom:6px}
.lede{font-size:17px;color:#45425E;margin-bottom:18px;max-width:1180px;line-height:1.35}
.sec{margin-bottom:44px}
.cap{font-size:14.5px;line-height:1.3;color:#45425E;margin-top:8px}
.cap b{color:#1A1830;font-weight:700}
.tag{font-weight:700;font-size:14px;color:#45425E;margin-bottom:6px}

/* ---------- label candidates ---------- */
.labs{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.lab{background:#F6F5FA;border-radius:18px;padding:20px 14px 18px}
.lab .hd{display:flex;align-items:baseline;gap:12px;margin-bottom:6px}
.lab .hd b{font-weight:900;font-size:46px;line-height:.9}
.lab .hd span{font-weight:900;font-size:23px}
.lab .idea{font-size:15.5px;line-height:1.35;color:#45425E;min-height:63px;margin-bottom:14px}
.big3{display:grid;grid-template-columns:96px 1fr;row-gap:8px;align-items:center;margin-bottom:18px}
.big3 span{font-size:14px;font-weight:700;color:#45425E;line-height:1.15}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.mini{background:#343949;border-radius:8px;padding:10px 0 0 4px;height:288px;overflow:hidden}
.mini .g{position:relative;width:222px;height:270px}
.lab .trade{font-size:15px;line-height:1.35;font-weight:700;border-left:4px solid #1A1830;padding-left:10px;margin-top:14px}

/* ---------- game-pixel world ---------- */
.g{font-family:"SS3";font-weight:700;color:#2A1A6E}
.gs{position:relative;width:640px;height:480px;overflow:hidden;background:repeating-linear-gradient(135deg,#343949 0 14px,#30354A 14px 28px)}
.gs.wide{width:853px}
.gs .in{position:absolute;left:0;top:0;width:640px;height:480px}
.gs.wide .in{left:106px}
.rhd{position:absolute;left:28px;top:26px;width:222px;height:30px;line-height:30px;padding-left:12px;background:#4A5064;border-radius:3px;color:#B4B9CA;font-size:12px;font-weight:600}
.rnote{position:absolute;right:28px;top:26px;line-height:30px;color:#8B91A6;font-size:12px;font-weight:600}
.plate{position:absolute;left:0;width:222px;height:38px;border-radius:4px;background:#6F7589}
.plate.on{background:#B4B9CA;box-shadow:0 0 0 2.5px #F1F2F7}
.plate .rl{line-height:38px;padding-left:16px;font-size:15px;font-weight:700;color:#2B2F3D;white-space:nowrap}
.plate.on .rl{color:#1B1E29}
.plate svg{position:absolute;left:0;top:0;display:block}
.rows{position:absolute;left:28px;top:84px;width:222px;height:270px}
.rpan{position:absolute;left:272px;top:76px;width:340px;height:296px;border-radius:6px;background:repeating-linear-gradient(135deg,#454B5F 0 10px,#3F4558 10px 20px);display:flex;align-items:center;justify-content:center;text-align:center;color:#AAB0C3;font-size:13px;font-weight:600;line-height:1.3}
.ppos{position:absolute;left:272px;top:76px}
.bar{width:584px;height:34px;line-height:34px;padding-left:14px;background:#4A5064;border-radius:3px;color:#fff;font-size:15px;font-weight:700;white-space:nowrap;overflow:hidden}
.gs .bar{position:absolute;left:28px;top:398px}
.bar.warn{color:#FFD84A}
.bar svg{vertical-align:-4px;margin-right:7px}
.bar.sm{width:340px;font-size:12.5px;padding-left:8px}
.bar.sm svg{margin-right:5px}

.st{position:absolute;background:#fff;border:3px solid #2A1A6E;border-radius:12px;box-shadow:3px 4px 0 #2A1A6E}
.st.dash{background:#FBF6DD;border-style:dashed;box-shadow:none}
.hl{font-family:"Brico";font-weight:800;font-size:26px;line-height:28px;letter-spacing:-.6px;white-space:nowrap}
.sub{font-size:12px;line-height:15px;font-weight:700;color:#2A1A6E}
.bn{font-family:"Brico";font-weight:800}
.s10{font-size:11px;line-height:12px;font-weight:700;color:#5A4C99;white-space:nowrap}
.tab{position:absolute;left:-7px;top:-9px;border:2.5px solid #2A1A6E;border-radius:8px;color:#fff;font-family:"Brico";font-weight:800;font-size:13px;line-height:17px;padding:0 6px;transform:rotate(-7deg)}
.drv{display:flex;align-items:center;gap:5px}
.drv .n{font-family:"Brico";font-weight:800;font-size:13px;line-height:13px}
.drv .sr{display:flex;gap:1px;margin-top:2px}
.drv svg{display:block}
.slot{font-size:11.5px;line-height:14px;font-weight:700;color:#5A4C99}
.dots{display:flex;gap:3px}
.dots i{width:11px;height:11px;border-radius:50%;background:#FF4D6D;border:2.2px solid #2A1A6E}
.dots i.off{background:none}
.keyp{position:absolute;background:#2A1A6E;border-radius:12px;color:#FFD84A;display:flex;align-items:center;gap:7px;padding:0 10px}
.keyp .s10{color:#C9BFF5}
.keyp .bn{font-size:14px;line-height:15px;white-space:nowrap}
.ng{display:flex;gap:2px}
.ng i{width:17px;height:17px;border-radius:50%;border:2px solid #2A1A6E;font-style:normal;font-family:"Brico";font-weight:800;font-size:10.5px;line-height:13px;text-align:center;color:#5A4C99;background:#fff}
.ng i.d{background:#2A1A6E;color:#fff}
.ng i.n{background:#FF4D6D;color:#fff;box-shadow:0 0 0 2px #FFD84A,0 0 0 4px #2A1A6E}
.steps{font-size:12.5px;line-height:17px;font-weight:700}
.steps b{display:inline-block;width:16px;height:16px;border-radius:50%;background:#2A1A6E;color:#fff;font-family:"Brico";font-weight:800;font-size:11px;line-height:16px;text-align:center;margin-right:6px}
.act{position:absolute;top:5px}
.act svg{display:block;margin-top:2px}

/* P1: box lid */
.p1{position:relative;width:340px;height:296px;background:#FFD84A;border:4px solid #2A1A6E;border-radius:16px;box-shadow:5px 6px 0 #2A1A6E}
.p1.miss{background:#F1ECD6;border-style:dashed;box-shadow:none}
.p1 .head{position:absolute;left:12px;top:9px}
.p1 .burst{position:absolute;right:-9px;top:-12px}
/* P2: loose stickers */
.p2{position:relative;width:340px;height:296px}
.p2 .band{background:#FFD84A;border-bottom:3px solid #2A1A6E;border-radius:9px 9px 0 0;padding:6px 10px 5px}
.p2 .dash .band{background:#F1ECD6;border-bottom-style:dashed}
.p2 .frow{position:relative;display:flex;align-items:center;gap:6px;height:50px;padding-left:9px;border-top:2px dashed rgba(42,26,110,.25)}
.p2 .frow:first-of-type{border-top:0}
.p2 .ptag{border:2.5px solid #2A1A6E;border-radius:8px;color:#fff;font-family:"Brico";font-weight:800;font-size:12px;line-height:16px;padding:0 5px}

/* ---------- panels grid ---------- */
.prow{display:grid;grid-template-columns:150px repeat(4,1fr);gap:16px;background:#F6F5FA;border-radius:18px;padding:22px 20px 18px;margin-bottom:16px;align-items:start}
.prow .who b{font-weight:900;font-size:46px;line-height:.9;display:block}
.prow .who span{font-weight:900;font-size:21px;line-height:1.1;display:block;margin:6px 0 8px}
.prow .who p{font-size:14.5px;line-height:1.35;color:#45425E}
.cell .hold{background:#343949;border-radius:8px;padding:16px 0 12px 11px;height:344px;overflow:hidden}
.cell .hold .g{zoom:.86}
.cell .bar{margin-top:14px}

/* ---------- composite ---------- */
.comp{display:grid;grid-template-columns:864px 640px;gap:16px;align-items:start}
.comp .big .g{zoom:1.35}
.wsec{display:grid;grid-template-columns:427px 1fr;gap:20px;margin-top:20px;align-items:center;background:#F6F5FA;border-radius:18px;padding:18px 20px}
.wsec .g{zoom:.5}
.wsec p{font-size:16px;line-height:1.4;color:#45425E;max-width:900px}
.wsec p b{color:#1A1830}

.rec{background:#1A1830;color:#F6F5FA;border-radius:18px;padding:26px 30px;display:grid;grid-template-columns:150px 1fr 1fr;gap:30px;align-items:start}
.rec h2{font-size:24px;margin:0}
.rec p{font-size:18px;line-height:1.38}
.rec b{font-weight:900;color:#FFD84A}
.foot{margin-top:14px;font-size:13.5px;color:#5A5775;line-height:1.35}
"""


# ------------------------------------------------------------------ small parts
def svg(w, h, vb, body, extra=""):
    return f'<svg width="{w}" height="{h}" viewBox="{vb}" {extra}>{body}</svg>'


def star_svg(size, fill=SUN, on=True, sw=2.4):
    dash = "" if on else ' stroke-opacity=".4" stroke-dasharray="2.5 2.5"'
    return svg(size, size, "-12 -12 24 24",
               f'<path d="{STAR}" fill="{fill if on else WHITE}" stroke="{INK}" stroke-width="{sw}" stroke-linejoin="round"{dash}/>')


def pog(kind, size=28):
    if kind == "ember":
        face, icon = CORAL, f'<g transform="scale(.15) translate(0 -3)"><path d="{FLAME}" fill="{SUN}" stroke="{INK}" stroke-width="11" stroke-linejoin="round"/></g>'
    else:
        face, icon = LAGOON, '<g stroke="#fff" stroke-width="2.4" stroke-linecap="round"><path d="M0,-6.5V6.5M-5.6,-3.25L5.6,3.25M-5.6,3.25L5.6,-3.25"/></g>'
    return svg(size, size, "-14 -14 28 28", f'<circle r="11.5" fill="{face}" stroke="{INK}" stroke-width="2.5"/>{icon}')


def drive(kind, lvl):
    name = "Ember" if kind == "ember" else "Frost"
    stars = "".join(star_svg(11, on=i < lvl, sw=3) for i in range(3))
    return f'<div class="drv">{pog(kind)}<div><div class="n">{name}</div><div class="sr">{stars}</div></div></div>'


def sil(w=40, h=56, wide=False):
    body = "M3,54 C3,36 8,24 20,24 C32,24 37,36 37,54Z" if wide else "M7,54 C7,34 11,25 20,25 C29,25 33,34 33,54Z"
    head = '<circle cx="20" cy="13" r="10"/>' if wide else '<circle cx="20" cy="12" r="8.5"/>'
    return svg(w, h, "0 0 40 56", f'<g fill="#BFC2CE" stroke="{INK}" stroke-width="2.6" stroke-linejoin="round"><path d="{body}"/>{head}</g>')


def stock_dots(left, total=5):
    return '<div class="dots">' + "".join(f'<i class="{"" if i < left else "off"}"></i>' for i in range(total)) + "</div>"


def disc_badge(size=18):
    return svg(size, size, "-10 -10 20 20",
               f'<circle r="8.6" fill="{CORAL}" stroke="{INK}" stroke-width="2"/><circle r="4.3" fill="none" stroke="#fff" stroke-width="1.8"/>'
               f'<circle r="1" fill="#fff"/><path d="M-6,6L6,-6" stroke="{INK}" stroke-width="4.4" stroke-linecap="round"/><path d="M-6,6L6,-6" stroke="#fff" stroke-width="2" stroke-linecap="round"/>')


def enc(i, done, cur, x, y, r=5.5):
    """One encounter mark. i: 0..11, every 4th is the boss (a star)."""
    boss = i % 4 == 3
    if i < done:
        fill, st = INK, INK
    elif i == cur:
        fill, st = CORAL, INK
    else:
        fill, st = WHITE, INK
    ring = f'<circle cx="{x}" cy="{y}" r="{r + 4.2}" fill="none" stroke="{INK}" stroke-width="2"/>' if i == cur else ""
    if boss:
        s = r / 6.4
        return f'{ring}<path transform="translate({x} {y}) scale({s:.2f})" d="{STAR}" fill="{fill}" stroke="{st}" stroke-width="{2.4 / s:.1f}" stroke-linejoin="round"/>'
    return f'{ring}<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{st}" stroke-width="2.2"/>'


def act_group(a, done, cur, gap=21, r=5.5):
    w = gap * 3 + 30
    body = "".join(enc(a * 4 + k, done, cur, 11 + k * gap + (3 if k == 3 else 0), 12, r) for k in range(4))
    return svg(w, 24, f"0 0 {w} 24", body)


def ng_ladder(cleared):
    out = ""
    for i in range(11):
        cls = "d" if i < cleared else ("n" if i == cleared else "")
        out += f'<i class="{cls}">{i}</i>'
    return f'<div class="ng">{out}</div>'


STEPS = '<div class="steps"><div><b>1</b>Open the launcher.</div><div><b>2</b>Add your Brawl disc.</div><div><b>3</b>Restart the game.</div></div>'

DESC = {
    "new": "A co-op run for 1 or 2 players, three acts long.",
    "saved": "Continue your run from act 2, fight 3.",
    "done": "Run cleared. NG+ 1 is open at the camp.",
    "miss": "Envoy needs your Brawl disc. Add it in the launcher.",
}
STATE_NAME = {
    "new": ("No run yet", "First time. A opens the camp."),
    "saved": ("A saved run", "Act 2, fight 3; two fighters; 3 of 5 stocks. A opens the camp with the run loaded."),
    "done": ("Run just cleared", "NG+ 1 unlocked. A opens the camp."),
    "miss": ("Brawl disc missing", "A opens a message with the same three steps; the camp never loads."),
}


def bar(state, cls=""):
    if state == "miss":
        return f'<div class="bar warn {cls}">{disc_badge(18)}{DESC[state]}</div>'
    return f'<div class="bar {cls}">{DESC[state]}</div>'


# ------------------------------------------------------------------ row labels
def wordmark(x, fill, size=26, sw=4.5, opacity=1):
    return (f'<text x="{x}" y="28" font-family="Brico" font-weight="800" font-size="{size}" letter-spacing="-.6" fill="{fill}" '
            f'stroke="{INK}" stroke-width="{sw}" paint-order="stroke" stroke-linejoin="round" opacity="{opacity}">Envoy</text>')


def label(v, state):
    """state: idle, on, miss. 222x38, the whole plate face; art stays inside the label area."""
    if v == 1:
        body = wordmark(15, SUN if state != "miss" else "#D5D1EA")
        if state == "miss":
            body += f'<g transform="translate(112 19)">{disc_badge(20)[disc_badge(20).index(">") + 1:-6]}</g>'
    elif v == 2:
        rot, face = (-3, WHITE) if state != "on" else (1.5, SUN)
        if state == "miss":
            face = "#E2DFEE"
        corner = (f'<g transform="translate(121 9) scale(.42)"><path d="{BURST}" fill="{CORAL}" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/></g>'
                  if state != "miss" else f'<g transform="translate(121 9) scale(1.05)">{disc_badge(20)[disc_badge(20).index(">") + 1:-6]}</g>')
        body = (f'<g transform="rotate({rot} 70 19)"><rect x="15" y="7" width="108" height="28" rx="10" fill="{INK}"/>'
                f'<rect x="12" y="4" width="108" height="28" rx="10" fill="{face}" stroke="{INK}" stroke-width="3"/>'
                f'<text x="24" y="26" font-family="Brico" font-weight="800" font-size="22" letter-spacing="-.5" fill="{INK}">Envoy</text>{corner}</g>')
    else:
        if state == "miss":
            em = f'<g transform="translate(25 19) scale(1.55)">{disc_badge(20)[disc_badge(20).index(">") + 1:-6]}</g>'
        else:
            ring = (f'<circle cx="25" cy="19" r="15" fill="{INK}"/><circle cx="25" cy="19" r="13" fill="none" stroke="{SUN}" stroke-width="3.2"/>'
                    if state == "on" else f'<circle cx="25" cy="19" r="14.5" fill="{INK}"/>')
            em = (f'{ring}<circle cx="25" cy="19" r="{10 if state == "on" else 11.5}" fill="#fff"/>'
                  f'<circle cx="21.4" cy="19" r="5" fill="{CORAL}" stroke="{INK}" stroke-width="2"/>'
                  f'<circle cx="28.6" cy="19" r="5" fill="{LAGOON}" stroke="{INK}" stroke-width="2"/>')
        fill = {"idle": WHITE, "on": SUN, "miss": "#D5D1EA"}[state]
        body = em + wordmark(47, fill)
    return svg(222, 38, "0 0 222 38", body)


SIBS = ["1-P Mode", "Vs. Mode", None, "Trophies", "Options", "Data"]


def rows(v, hover, miss=False):
    out = ""
    for i, name in enumerate(SIBS):
        on = " on" if i == hover else ""
        if name:
            inner = f'<div class="rl">{name}</div>'
        else:
            inner = label(v, "miss" if miss else ("on" if on else "idle"))
        out += f'<div class="plate{on}" style="top:{i * 46}px">{inner}</div>'
    return out


def one_plate(v, state):
    on = " on" if state == "on" else ""
    return f'<div class="g" style="zoom:1.55;position:relative;width:222px;height:38px"><div class="plate{on}" style="top:0">{label(v, state)}</div></div>'


def lab(v, name, idea, trade):
    big = "".join(f'<span>{cap}</span>{one_plate(v, st)}' for cap, st in
                  (("Idle", "idle"), ("Hovered", "on"), ("Disc missing", "miss")))
    minis = "".join(f'<div><div class="tag">{cap}</div><div class="mini"><div class="g" style="transform-origin:0 0">{rows(v, hv)}</div></div></div>'
                    for cap, hv in (("Idle, in the column at 640x480", 1), ("Hovered, at 640x480", 2)))
    return f"""<div class="lab"><div class="hd"><b>L{v}</b><span>{name}</span></div><p class="idea">{idea}</p>
<div class="big3">{big}</div><div class="pair">{minis}</div><p class="trade">{trade}</p></div>"""


# ------------------------------------------------------------------ P1: box lid
def burst(text, fill, size=58, fs=15):
    lines = text.split("|")
    y0 = 5 if len(lines) == 1 else -2
    t = "".join(f'<text x="0" y="{y0 + i * 14}" text-anchor="middle" font-family="Brico" font-weight="800" font-size="{fs}" fill="#fff" stroke="{INK}" stroke-width="3" paint-order="stroke" stroke-linejoin="round">{ln}</text>' for i, ln in enumerate(lines))
    return svg(size, size, "-29 -29 58 58", f'<path d="{BURST}" fill="{fill}" stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"/>{t}', 'class="burst" style="transform:rotate(8deg)"')


def track_strip(done, cur, dim=False):
    acts = "".join(f'<div class="act" style="left:{10 + a * 103}px"><div class="s10">Act {a + 1}</div>{act_group(a, done, cur)}</div>' for a in range(3))
    op = "opacity:.5;" if dim else ""
    return f'<div class="st" style="left:10px;top:64px;width:312px;height:46px;{op}">{acts}</div>'


def fighter_card(x, rot, tag, col, drives, wide=False):
    d = "".join(f'<div style="position:absolute;left:54px;top:{14 + i * 43}px">{drive(k, l)}</div>' for i, (k, l) in enumerate(drives))
    return (f'<div class="st" style="left:{x}px;top:120px;width:150px;height:108px;transform:rotate({rot}deg)">'
            f'<span class="tab" style="background:{col}">{tag}</span><div style="position:absolute;left:8px;top:40px">{sil(40, 56, wide)}</div>{d}</div>')


def slot_card(x, rot, tag, col, text):
    return (f'<div class="st dash" style="left:{x}px;top:120px;width:150px;height:108px;transform:rotate({rot}deg)">'
            f'<span class="tab" style="background:{col}">{tag}</span>'
            f'<div style="position:absolute;left:8px;top:40px;opacity:.45">{sil()}</div>'
            f'<div class="slot" style="position:absolute;left:56px;top:38px;width:84px">{text}</div></div>')


def p1(state):
    if state == "saved":
        return f"""<div class="p1">
<div class="head"><div class="hl">Continue run</div><div class="sub">Act 2, fight 3. Saved after fight 2.</div></div>
{burst("NG+ 0", LAGOON)}
{track_strip(6, 6)}
{fighter_card(10, -1.5, "P1", CORAL, [("ember", 2), ("frost", 1)])}
{fighter_card(172, 1.2, "P2", LAGOON, [("frost", 3), ("ember", 1)], True)}
<div class="st" style="left:10px;top:240px;width:156px;height:38px;display:flex;align-items:center;gap:8px;padding-left:9px">
  <div><div class="s10">Team stocks</div><div class="bn" style="font-size:13px;line-height:14px;white-space:nowrap">3 of 5</div></div>{stock_dots(3)}</div>
<div class="keyp" style="left:178px;top:240px;width:144px;height:38px;transform:rotate(1deg);padding:0 8px">{star_svg(18, sw=0)}<div><div class="s10">Keystone</div><div class="bn">Plague Bearer</div></div></div>
</div>"""
    if state == "new":
        return f"""<div class="p1">
<div class="head"><div class="hl">Start a run</div><div class="sub">Three acts. Each is 3 fights, then a boss.</div></div>
{burst("New", CORAL)}
{track_strip(0, None)}
{slot_card(10, -1.5, "P1", CORAL, "Pick a fighter at the camp.")}
{slot_card(172, 1.2, "P2", LAGOON, "A second player can join at the camp.")}
<div class="st" style="left:10px;top:240px;width:312px;height:38px;display:flex;align-items:center;gap:10px;padding-left:10px">
  {stock_dots(5)}<div class="sub">One stock pool: 5 together, 4 solo.</div></div>
</div>"""
    if state == "done":
        return f"""<div class="p1">
<div class="head"><div class="hl">Run cleared!</div><div class="sub">All three acts beaten on NG+ 0.</div></div>
{burst("NG+ 1|open", CORAL, 64, 13)}
{track_strip(12, None)}
<div class="st" style="left:10px;top:120px;width:312px;height:56px;transform:rotate(-.8deg);padding:7px 10px">
  <div class="s10" style="margin-bottom:6px">NG+ level: 0 cleared, 1 open, up to 10</div>{ng_ladder(1)}</div>
<div class="st" style="left:10px;top:188px;width:312px;height:52px;transform:rotate(.7deg);display:flex;align-items:center;gap:8px;padding-left:10px">
  <div style="width:82px"><div class="s10">New in the box</div><div class="bn" style="font-size:13px;line-height:15px">1 fighter,<br>2 drives</div></div>
  <div style="height:44px;overflow:hidden;margin-right:6px">{sil(32, 45)}</div>{pog("ember", 30)}{pog("frost", 30)}</div>
<div class="sub" style="position:absolute;left:12px;top:254px">Start the next run at the camp.</div>
</div>"""
    return f"""<div class="p1 miss">
<div class="head"><div class="hl" style="font-size:23px">Needs your Brawl disc</div><div class="sub">Envoy stays here and opens once the disc is added.</div></div>
<div class="st" style="left:10px;top:70px;width:312px;height:76px;padding:10px 12px;display:flex;gap:14px;align-items:center">{disc_badge(46)}{STEPS}</div>
{track_strip(0, None, True).replace("top:64px", "top:160px")}
<div class="sub" style="position:absolute;left:12px;top:222px;width:300px;color:{LILAC}">Three acts, 1 or 2 players, one shared stock pool. Waiting for the disc.</div>
</div>"""


# ------------------------------------------------------------------ P2: loose stickers
def punch_card(done, cur, dim=False, stamp=False):
    rows_ = "".join(f'<div style="position:absolute;left:4px;top:{6 + a * 41}px"><div class="s10">Act {a + 1}</div>{act_group(a, done, cur, 20, 6)}</div>' for a in range(3))
    st = (f'<div class="bn" style="position:absolute;left:8px;top:48px;transform:rotate(-14deg);border:3px solid {CORAL};color:{CORAL};background:rgba(255,255,255,.88);border-radius:8px;font-size:18px;line-height:24px;padding:0 8px">Cleared</div>' if stamp else "")
    op = "opacity:.5;" if dim else ""
    return f'<div class="st" style="left:245px;top:0;width:97px;height:136px;background:{SUN};transform:rotate(3deg);{op}">{rows_}{st}</div>'


def frow(tag, col, drives, wide=False):
    d = "".join(drive(k, l) for k, l in drives)
    return f'<div class="frow"><span class="ptag" style="background:{col}">{tag}</span><div style="height:42px;overflow:hidden">{sil(30, 42, wide)}</div>{d}</div>'


def frow_empty(tag, col, text):
    return f'<div class="frow"><span class="ptag" style="background:{col}">{tag}</span><div style="height:42px;overflow:hidden;opacity:.45">{sil(30, 42)}</div><div class="slot">{text}</div></div>'


def p2(state):
    card = 'class="st" style="left:2px;top:10px;width:246px;height:{h}px;transform:rotate(-2deg)"'
    if state == "saved":
        return f"""<div class="p2">
<div {card.format(h=176)}><div class="band"><div class="hl" style="font-size:23px;line-height:25px">Continue run</div><div class="sub">Act 2, fight 3. Saved after fight 2.</div></div>
{frow("P1", CORAL, [("ember", 2), ("frost", 1)])}{frow("P2", LAGOON, [("frost", 3), ("ember", 1)], True)}</div>
{punch_card(6, 6)}
<div class="st" style="left:214px;top:158px;width:122px;height:50px;transform:rotate(-3deg);padding:6px 9px"><div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px"><span class="s10">Team stocks</span><span class="bn" style="font-size:13px;line-height:14px">3 of 5</span></div>{stock_dots(3)}</div>
<div class="keyp" style="left:26px;top:214px;height:40px;transform:rotate(1.5deg)">{star_svg(18, sw=0)}<div><div class="s10">Keystone</div><div class="bn">Plague Bearer</div></div></div>
<div class="st" style="left:216px;top:222px;width:92px;height:34px;transform:rotate(4deg);background:{LAGOON};color:#fff;text-align:center"><span class="bn" style="font-size:16px;line-height:28px;-webkit-text-stroke:0">NG+ 0</span></div>
</div>"""
    if state == "new":
        return f"""<div class="p2">
<div {card.format(h=176)}><div class="band"><div class="hl" style="font-size:23px;line-height:25px">Start a run</div><div class="sub">Three acts. Each is 3 fights, then a boss.</div></div>
{frow_empty("P1", CORAL, "Pick a fighter at the camp.")}{frow_empty("P2", LAGOON, "A second player can join.")}</div>
{punch_card(0, None)}
<div class="st" style="left:196px;top:156px;width:138px;height:56px;transform:rotate(-3deg);padding:6px 9px"><div class="s10" style="margin-bottom:3px">One stock pool</div>
  {stock_dots(5)}<div class="s10" style="margin-top:3px;color:{INK}">5 together, 4 solo</div></div>
</div>"""
    if state == "done":
        return f"""<div class="p2">
<div {card.format(h=176)}><div class="band"><div class="hl" style="font-size:23px;line-height:25px">Run cleared!</div><div class="sub">NG+ 1 is open. Start it at the camp.</div></div>
<div style="padding:9px 10px 0"><div class="s10" style="margin-bottom:6px">NG+ level, up to 10</div>{ng_ladder(1)}</div>
<div style="display:flex;align-items:center;gap:7px;padding:10px 10px 0"><div style="width:76px"><div class="s10">New in the box</div><div class="bn" style="font-size:13px;line-height:15px">1 fighter,<br>2 drives</div></div>
  <div style="height:42px;overflow:hidden;margin-right:4px">{sil(30, 42)}</div>{pog("ember", 30)}{pog("frost", 30)}</div></div>
{punch_card(12, None, stamp=True)}
<div class="st" style="left:216px;top:170px;width:104px;height:38px;transform:rotate(4deg);background:{CORAL};text-align:center"><span class="bn" style="font-size:16px;line-height:32px;color:#fff">NG+ 1 open</span></div>
</div>"""
    return f"""<div class="p2">
<div class="st dash" style="left:2px;top:10px;width:246px;height:176px;transform:rotate(-2deg)"><div class="band"><div class="hl" style="font-size:19px;line-height:25px">Needs your Brawl disc</div><div class="sub">Envoy opens once the disc is added.</div></div>
<div style="padding:12px 12px 0;display:flex;gap:12px;align-items:center">{disc_badge(40)}{STEPS}</div></div>
{punch_card(0, None, dim=True)}
</div>"""


# ------------------------------------------------------------------ screens
def screen(v, panel, state, wide=False, hover=2):
    miss = state == "miss"
    return f"""<div class="gs{' wide' if wide else ''}"><div class="in">
<div class="rhd">retail header (placeholder)</div><div class="rnote">grey = retail, from the player's disc</div>
<div class="rows">{rows(v, hover, miss)}</div>
<div class="ppos">{panel(state)}</div>
{bar(state)}</div></div>"""


def panel_row(tag, name, idea, fn):
    cells = ""
    for st in ("new", "saved", "done", "miss"):
        t, c = STATE_NAME[st]
        cells += f'<div class="cell"><div class="tag">{t}</div><div class="hold"><div class="g">{fn(st)}{bar(st, "sm")}</div></div><p class="cap">{c}</p></div>'
    return f'<div class="prow"><div class="who"><b>{tag}</b><span>{name}</span><p>{idea}</p></div>{cells}</div>'


def html():
    labs = (lab(1, "Plain wordmark", "Only the word, in Bricolage with the grape die-cut outline. Nothing else on the plate; the retail highlight does all the hover work.",
                "Sits closest to the retail rows and survives any plate tint; shows the least Party pack.")
            + lab(2, "Sticker slapped on", "A white die-cut sticker, a little crooked, stuck on the plate. Hovered, it straightens and turns sunny.",
                  "The loudest. It reads as a second plate on top of the retail one and fights the retail highlight.")
            + lab(3, "Wordmark and emblem", "The word plus one small round sticker: two pogs, one per player. Hovered, the charge ring closes around it and the word turns sunny.",
                  "One sticker's worth of Party pack, and the emblem is where the disc mark goes. Needs a second label image for hover."))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Envoy UI step 2</title><style>{CSS}</style></head>
<body><div id="c">
<div class="top"><h1>Envoy on the main menu</h1>
<p>Step 2 of the UI design. Two choices: the row label (L1, L2 or L3) and the panel layout (P1 or P2). The camp, cards and HUD are not designed yet.</p></div>
<div class="key"><span><i style="background:#6F7589"></i>Grey is retail and comes from the player's disc: plates, highlight, motion, bars. Not ours to restyle.</span>
<span><i style="background:{SUN};box-shadow:inset 0 0 0 2.5px {INK}"></i>Colour is drawn by the port: the label image, the panel, the description text.</span></div>

<div class="sec"><h2>The row label</h2>
<p class="lede">Envoy is the third of six rows. Each candidate is shown large in its three states, then at game size in the column: once with the cursor on Vs. Mode, once on Envoy.</p>
<div class="labs">{labs}</div></div>

<div class="sec"><h2>The panel</h2>
<p class="lede">While Envoy is hovered the retail panel is hidden and the port draws in the same 340 by 296 space. Each layout is shown in its four states with the description-bar line under it. Drive and keystone names are the step 1 samples.</p>
{panel_row("P1", "Box lid", "One solid sunny panel fills the retail panel's space. Reads top to bottom: what A does, where the run is, who is in it, what is left.", p1)}
{panel_row("P2", "Loose stickers", "No backing. A save sticker, a punch card and a few small stickers sit straight on the retail background, overlapping.", p2)}
</div>

<div class="sec"><h2>The whole screen</h2>
<p class="lede">L3 and P1, Envoy hovered, with a saved run. Left: 4:3, enlarged. Right: the same screen at 640 by 480, the size the game renders before upscaling.</p>
<div class="comp"><div class="big"><div class="g">{screen(3, p1, "saved")}</div></div>
<div><div class="g">{screen(3, p1, "saved")}</div><p class="cap"><b>Actual size, 640 by 480.</b> Smallest text is 11 px (Team stocks, Keystone, act names); names are 13 px and up.</p></div></div>
<div class="wsec"><div class="g">{screen(3, p1, "saved", wide=True)}</div>
<p><b>Widescreen.</b> Nothing changes size. The panel keeps its 4:3 position and scale next to the plate column and is never stretched; the extra width is retail background. If the retail menu is found to stretch at 16:9 instead, the port's label, panel and text should still be drawn unstretched, anchored to the plate column's right edge.</p></div></div>

<div class="rec"><h2>Recommended</h2>
<p><b>Label L3, wordmark and emblem.</b> It lets the retail plate stay a retail plate while one small sticker says this row is different, and that sticker doubles as the charge ring on hover and the disc mark when the disc is missing.</p>
<p><b>Panel P1, box lid.</b> The retail panel leaves a hole when it is hidden, and one solid shape fills it; its fixed top-to-bottom order holds all four states and stays readable at 640 by 480.</p></div>
<p class="foot">Original vector art. Fonts: Bricolage Grotesque, Source Sans 3 (SIL OFL). Grey plates, bars and backgrounds are neutral placeholders for retail parts; fighters are neutral silhouettes; sibling row names are set in the sheet's own type.</p>
</div></body></html>"""


def main():
    src = HERE / "step2.html"
    src.write_text(html(), encoding="utf-8")
    (HERE / "preview").mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
        page.goto(src.as_uri())
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(300)
        bad = page.evaluate("""() => [...document.querySelectorAll('.g *, .lab *, .prow *')].filter(e => e.children.length === 0 && !(e instanceof SVGElement) && (e.scrollWidth > e.clientWidth + 1) && getComputedStyle(e).display !== 'inline').map(e => e.className + ': ' + e.textContent.slice(0, 40))""")
        for b in sorted(set(bad)):
            print("overflow:", b)
        page.locator("#c").screenshot(path=str(HERE / "preview" / "step2-main-menu.png"), type="png")
        print(page.evaluate("document.getElementById('c').offsetHeight"))
        browser.close()


if __name__ == "__main__":
    main()
