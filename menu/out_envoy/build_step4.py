#!/usr/bin/env python3
"""Envoy UI, step 4: the drive card, the pick-of-three reward screen and the keystone pick.

Writes step4.html beside this file and renders preview/step4-cards.png (1600 px wide) with headless
Chromium, like build_step3.py. Everything inside a `.g` box is authored in game pixels (640x480
native) and scaled with CSS zoom. Original vector art only, family glyphs included; fighters are
neutral silhouettes with placeholder names. Fonts: Bricolage Grotesque and Source Sans 3 (SIL OFL).
"""
import math
from pathlib import Path
from playwright.sync_api import sync_playwright

import build_step2 as s2
import build_step3 as s3
from build_step2 import svg, star_svg, burst, SUN, INK, WHITE, CORAL, LAGOON, LILAC, FLAME, STAR
from build_step3 import at, sil, bt, hints, say, ptr, cur, frame

HERE = Path(__file__).resolve().parent
BG, BG2 = "#4C3D9E", "#43348F"

# family: (word, colour). Six in use, two spare colours so the system reaches eight.
FAM = {
    "fire": ("Fire", "#FF7A1F"), "bolt": ("Lightning", "#3E6BFF"), "frost": ("Frost", "#62CCF5"),
    "wind": ("Wind", "#86D63C"), "tech": ("Technique", "#C866F2"), "util": ("Utility", "#AEA8CC"),
    "stone": ("Spare", "#C99455"), "rose": ("Spare", "#FF9CC4"),
}
RAR = ["Common", "Rare", "Epic"]
HOLO = "#FF8FB8,#FFE066,#8CF0C8,#7FD4FF,#C9A0FF,#FFB27A"

# name: family, rarity, % of damage dealt per charge, effect per level, what levels 2 and 3 add
DR = {
    "Ember": ("fire", 0, 20, ["a fire burst, 6% and Burning.", "a fire burst that reaches 2 foes, 6% and Burning.", "a fire burst on every foe near the target."],
              ["the burst reaches 2 foes", "it hits every foe nearby"]),
    "Wildfire": ("fire", 2, 45, ["the ground under the foe burns for 4 s."], ["the fire creeps along the floor", "it burns for 8 s"]),
    "Bolt": ("bolt", 1, 30, ["your next hit chains to a second foe for 8%."], ["it chains to 3 foes", "it chains to every foe"]),
    "Frost": ("frost", 0, 25, ["your next hit Chills, slowing the foe for 3 s."], ["Chill lasts 5 s", "Chilled foes also fall slower"]),
    "Shatter": ("frost", 1, 35, ["your next hit on a Chilled foe breaks for 12%."], ["the break also stuns", "it breaks for 18%"]),
    "Tailwind": ("wind", 0, 15, ["a gust: faster runs and higher jumps for 4 s."], ["the gust lasts 6 s", "your partner gets it too"]),
    "Feather Storm": ("wind", 1, 30, ["feathers rain on the nearest foe, 5 hits of 2%."], ["8 feathers", "they follow the foe"]),
    "Clean Landing": ("tech", 1, 40, ["your next landing has no lag and pops foes up."], ["two landings a charge", "three landings a charge"]),
    "Perfect Form": ("tech", 2, 60, ["your next smash comes out fully charged."], ["it cannot be interrupted", "two smashes a charge"]),
    "Echo": ("util", 2, 50, ["fires your last drive again."], ["fires it twice", "fires it three times"]),
    "Mirror": ("util", 1, 40, ["copies the last drive your partner fired."], ["the copy is one level higher", "it copies two"]),
    "Metronome": ("util", 0, 10, ["a small pulse, 2% to foes touching you."], ["the pulse deals 3%", "the pulse deals 4%"]),
}

CSS = s3.CSS + r"""
.cardrow{display:flex;gap:22px;align-items:flex-start;margin-bottom:20px}
.gb{background:#4C3D9E;border-radius:10px;position:relative;overflow:hidden}
.gb .g{position:relative}
.legend{font-size:15.5px;line-height:1.38;color:#45425E}
.legend li{margin:0 0 7px 22px}
.legend b{color:#1A1830;font-weight:700}
.legend.two{columns:2;column-gap:34px}
.legend.two li{break-inside:avoid}
.co{position:absolute;width:24px;height:24px;border-radius:50%;background:#1A1830;border:2.5px solid #fff;color:#fff;font-weight:900;font-size:14px;line-height:19px;text-align:center}
.famkey{display:flex;gap:18px;align-items:center;flex-wrap:wrap;font-size:15.5px;color:#45425E;background:#F6F5FA;border-radius:12px;padding:12px 18px;margin-bottom:26px}
.famkey span{display:inline-flex;align-items:center;gap:7px;font-weight:700;color:#1A1830}
.famkey em{font-style:normal;color:#45425E;font-weight:600}
.kside{display:grid;grid-template-columns:896px 1fr;gap:24px;align-items:start}
.kside .g{zoom:1.4}
.kside .tk .g{zoom:.84}
.act3{display:grid;grid-template-columns:640px 640px;gap:22px;align-items:start}

/* ---------- game-pixel world: drives ---------- */
.dcw{position:absolute;width:126px;height:186px;z-index:1}
.dc{position:absolute;left:0;top:0;width:126px;height:186px;background:#fff;border:3px solid #2A1A6E;border-radius:13px;box-shadow:3px 4px 0 #2A1A6E;overflow:hidden}
.dcw.r1 .dc{box-shadow:0 0 0 3px #fff,0 0 0 5px #2A1A6E,3px 5px 0 5px #2A1A6E}
.dcw.r2::before{content:"";position:absolute;left:-6px;top:-6px;width:138px;height:198px;border-radius:18px;background:linear-gradient(135deg,#FF8FB8,#FFE066,#8CF0C8,#7FD4FF,#C9A0FF,#FFB27A,#FF8FB8);border:2px solid #2A1A6E;box-shadow:3px 5px 0 #2A1A6E}
.dcw.r2 .dc{box-shadow:none}
.dcw.hov{z-index:3}
.dcw.hov .dc{background:#FFD84A}
.dcw.hov .nx{color:#2A1A6E}
.dcw.faded,.dr.faded{opacity:.34}
.dc .band{position:absolute;left:0;top:0;width:120px;height:42px;border-bottom:3px solid #2A1A6E}
.dc .band svg{position:absolute;left:42px;top:0}
.rib{position:absolute;display:flex;align-items:center;gap:1px;background:#fff;border:2.5px solid #2A1A6E;border-radius:10px;padding:1px 4px;height:19px}
.dc .rib{left:50%;top:32px;transform:translateX(-50%)}
.dc .bd{position:absolute;left:7px;top:53px;width:106px;height:127px}
.nm{font-family:"Brico";font-weight:800;font-size:16px;line-height:18px;letter-spacing:-.4px;white-space:nowrap}
.dc .nm{text-align:center}
.cp{font-size:11px;line-height:13px;font-weight:700;color:#5A4C99;white-space:nowrap}
.dc .cp{text-align:center;margin-bottom:3px}
.fx{font-size:11.5px;line-height:13px;font-weight:700;color:#2A1A6E}
.fx b{font-family:"Brico";font-weight:800;letter-spacing:-.1px}
.nx{font-size:11px;line-height:13px;font-weight:700;color:#5A4C99}
.dc .nx{position:absolute;left:0;bottom:4px;width:106px}
.slotp{position:absolute;background:#2A1A6E;color:#fff;border-radius:7px;font-family:"Brico";font-weight:800;font-size:11px;line-height:14px;padding:0 5px;white-space:nowrap}
.dc .slotp{right:4px;top:4px}
.flagp{position:absolute;background:#FF4D6D;color:#fff;border:2px solid #2A1A6E;border-radius:8px;font-family:"Brico";font-weight:800;font-size:11px;line-height:13px;padding:0 5px;white-space:nowrap;z-index:4}
.dcw>.flagp{left:8px;top:-9px;transform:rotate(-3deg)}
.lvb{position:absolute;z-index:5}
.spk{position:absolute;z-index:4}
.rays{position:absolute;z-index:0}

.dr{position:absolute;width:284px;height:72px;z-index:1}
.dr .tg{position:absolute;left:40px;top:2px;width:244px;height:68px;background:#fff;border:3px solid #2A1A6E;border-radius:11px;box-shadow:3px 4px 0 #2A1A6E;padding:4px 8px 0 22px}
.dr.hov{z-index:3}
.dr.hov .tg{background:#FFD84A;box-shadow:0 0 0 3px #fff,3px 5px 0 3px #2A1A6E}
.dr.hov .nx,.dr.hov .cp{color:#2A1A6E}
.dr .l1{display:flex;align-items:baseline;justify-content:space-between;height:18px}
.dr .hole{position:absolute;left:207px;top:5px;width:9px;height:9px;border-radius:50%;background:#4C3D9E;border:2px solid #2A1A6E;display:none}
.dr .bg{position:absolute;left:-3px;top:-4px}
.dr .bg svg{display:block}
.dr .rib{left:4px;top:51px;z-index:2}
.dr .slotp{right:-7px;top:-9px;transform:rotate(4deg);border:2px solid #fff}
.dr .flagp{right:6px;top:4px}

.chip{position:relative;width:26px;height:34px;flex:none}
.chip>svg{position:absolute;left:50%;top:13px;transform:translate(-50%,-50%)}
.chip .pips{position:absolute;left:50%;top:27px;transform:translateX(-50%);display:flex;gap:2px}
.chip .pips i{width:6px;height:5px;border-radius:2px;border:1.5px solid #2A1A6E;background:#fff}
.chip .pips i.y{background:#2A1A6E}
.chip .pips i.n{background:#FF4D6D}
.chip .upb{position:absolute;left:15px;top:-4px;z-index:2}
.fs .hd{position:absolute;left:6px;top:6px}
.fs .fn{position:absolute;left:36px;top:4px}
.fs .cr{position:absolute;left:35px;top:22px;display:flex}
.fs.v .hd{left:5px;top:3px}
.fs.v .fn{left:33px;top:9px}
.fs.v .cr{left:4px;top:38px}
.fs .full{position:absolute;right:6px;top:5px}
.strip{position:absolute;height:26px;background:#fff;border:3px solid #2A1A6E;border-radius:9px;box-shadow:3px 4px 0 #2A1A6E;padding:0 9px;line-height:19px;font-size:12px;font-weight:700;color:#2A1A6E;white-space:nowrap;transform:rotate(-.5deg)}
.skp{position:absolute;height:28px;background:#fff;border:3px solid #2A1A6E;border-radius:10px;box-shadow:3px 4px 0 #2A1A6E;font-family:"Brico";font-weight:800;font-size:13.5px;line-height:21px;text-align:center;white-space:nowrap}
.pp{position:absolute;border:3px solid #2A1A6E;border-radius:10px;color:#fff;font-family:"Brico";font-weight:800;font-size:16px;line-height:20px;padding:0 7px;box-shadow:2px 3px 0 #2A1A6E}
.wt{color:#fff;font-size:12px;line-height:14px;font-weight:700;white-space:nowrap}

/* ---------- keystones ---------- */
.kw{position:absolute}
.kw>svg{position:absolute;left:0;top:0;display:block}
.kw .kin{position:absolute;text-align:center;color:#fff}
.kw .em{position:absolute;left:50%;transform:translateX(-50%)}
.kn{font-family:"Brico";font-weight:800;letter-spacing:-.5px;color:#FFD84A}
.kr{font-weight:700;color:#fff}
.kg{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;line-height:14px;font-weight:700;color:#C9BFF5;white-space:nowrap}
.kw.hov .kn,.kw.hov .kr,.kw.hov .kg,.ks.hov .kn,.ks.hov .kr,.ks.hov .kg{color:#2A1A6E}
.ks{position:absolute;width:320px;height:96px;background:#2A1A6E;border:3px solid #fff;border-radius:16px;box-shadow:0 0 0 2.5px #2A1A6E,4px 6px 0 2.5px #2A1A6E}
.ks.hov{background:#FFD84A;z-index:3}
.ks .em{position:absolute;left:8px;top:14px}
.ks .tx{position:absolute;left:78px;top:7px;width:230px}
.sock{display:flex;align-items:center;gap:4px}
"""


# ------------------------------------------------------------------ glyphs, pogs, stars
def _line(d, w=2.5):
    a = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    return f'<path d="{d}" {a} stroke="{INK}" stroke-width="{w + 3.2}"/><path d="{d}" {a} stroke="#fff" stroke-width="{w}"/>'


def _solid(d):
    return f'<path d="{d}" fill="#fff" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>'


def glyph(f):
    """Family glyph, white with an ink edge, drawn in a box of about 22 units around the origin."""
    if f == "fire":
        return f'<g transform="translate(0 -.6) scale(.2)"><path d="{FLAME}" fill="#fff" stroke="{INK}" stroke-width="11" stroke-linejoin="round"/></g>'
    if f == "bolt":
        return _solid("M2.6,-10.5 L-7.2,1.6 H-1 L-3.2,10.5 L7.2,-2.2 H1.2Z")
    if f == "frost":
        return _line("M0,-9V9M-7.8,-4.5L7.8,4.5M-7.8,4.5L7.8,-4.5", 2.3)
    if f == "wind":
        return _line("M-9,-3.2H2.6a3.6,3.6 0 1 0 -3.6,-3.6M-9,3.2H5.4a3.3,3.3 0 1 1 -3.3,3.3", 2.3)
    if f == "tech":
        return (f'<circle r="7.6" fill="none" stroke="{INK}" stroke-width="5.6"/><circle r="7.6" fill="none" stroke="#fff" stroke-width="2.5"/>'
                f'<circle r="2.9" fill="#fff" stroke="{INK}" stroke-width="1.6"/>')
    if f == "util":
        c = lambda col, w: "".join(f'<circle cx="{x}" r="5.4" fill="none" stroke="{col}" stroke-width="{w}"/>' for x in (-3.8, 3.8))
        return c(INK, 5.4) + c("#fff", 2.3)
    if f == "stone":
        return _solid("M0,-9L8,-4.5V4.5L0,9L-8,4.5V-4.5Z")
    return _solid("M0,-10C5,-3 8,1 8,4.6A8,8 0 0 1 -8,4.6C-8,1 -5,-3 0,-10Z")


SPARK = "M0,-5.5 L1.5,-1.5 L5.5,0 L1.5,1.5 L0,5.5 L-1.5,1.5 L-5.5,0 L-1.5,-1.5Z"
SPK = svg(22, 22, "-7 -7 14 14", f'<path d="{SPARK}" fill="{SUN}" stroke="{INK}" stroke-width="1.5" stroke-linejoin="round"/>')
SQ = False  # chip shape: square tiles for the D1 card, round badges for D2


def pog(f, size, rar=0, halo=False, sq=None):
    """A drive's badge. Rarity is the edge: none, a thick white die-cut, or a foil rim."""
    sq = SQ if sq is None else sq
    col = FAM[f][1]
    vb = 19 if halo else 16
    px = size * vb / 16
    sh = (lambda r, a: f'<rect x="{-r}" y="{-r}" width="{2 * r}" height="{2 * r}" rx="{r * .42:.1f}" {a}/>') if sq else (lambda r, a: f'<circle r="{r}" {a}/>')
    b = ""
    if halo:
        b += sh(17.2, f'fill="{SUN}" stroke="{INK}" stroke-width="1.6"')
    if rar:
        b += sh(14.6, f'fill="{"#fff" if rar == 1 else "url(#holo)"}" stroke="{INK}" stroke-width="1.8"')
    b += sh(11.4, f'fill="{col}" stroke="{INK}" stroke-width="2.4"') + f'<g transform="scale({.82 if sq else .9})">{glyph(f)}</g>'
    if rar == 2:
        b += f'<path transform="translate(11 -11)" d="{SPARK}" fill="{SUN}" stroke="{INK}" stroke-width="1.4" stroke-linejoin="round"/>'
    return svg(f"{px:.1f}", f"{px:.1f}", f"{-vb} {-vb} {2 * vb} {2 * vb}", b)


def stars(lvl, size=12, new=False):
    out = ""
    for i in range(3):
        if new and i == lvl - 1:
            out += star_svg(round(size * 1.5), CORAL, True, 2.6)
        else:
            out += star_svg(size, on=i < lvl, sw=3)
    return out


def rays(x, y, size, n=14):
    p = ""
    for i in range(n):
        a0, a1 = (i - .22) * 2 * math.pi / n, (i + .22) * 2 * math.pi / n
        r = 50 if i % 2 else 43
        p += f'<path d="M0,0 L{r * math.cos(a0):.1f},{r * math.sin(a0):.1f} L{r * math.cos(a1):.1f},{r * math.sin(a1):.1f}Z" fill="{SUN}"/>'
    return f'<div class="rays" style="left:{x - size / 2}px;top:{y - size / 2}px">{svg(size, size, "-50 -50 100 100", p)}</div>'


def lvburst(style, size=50):
    return f'<div class="lvb" style="{style}">{burst("Level|up!", CORAL, size, 13)}</div>'


# ------------------------------------------------------------------ D1: the tall card
def d1(x, y, d, lvl=1, rot=0, cls="", slot=None, up=None, flag=None):
    f, rar, chg, fx, nxt = DR[d]
    col = FAM[f][1]
    if up:
        body = f'<div class="fx"><b>Level {lvl} adds:</b> {nxt[lvl - 2]}.</div><div class="nx">{up} has level {lvl - 1}.</div>'
    else:
        nx = f"Lv {lvl + 1}: {nxt[lvl - 1]}." if lvl < 3 else "Top level."
        body = f'<div class="fx"><b>Every {chg}% you deal:</b> {fx[min(lvl, len(fx)) - 1]}</div><div class="nx">{nx}</div>'
    ex = rays(x + 63, y + 93, 216) if (up and "faded" not in cls) else ""
    slotp = f'<span class="slotp">Slot {slot}</span>' if slot else ""
    flagp = f'<span class="flagp">{flag}</span>' if flag else ""
    spk = f'<div class="spk" style="left:-11px;top:-12px">{SPK}</div>' if rar == 2 else ""
    return (f'{ex}<div class="dcw r{rar} {cls}" style="left:{x}px;top:{y}px;transform:rotate({rot}deg)"><div class="dc">'
            f'<div class="band" style="background:{col}">{svg(36, 36, "-13 -13 26 26", glyph(f))}{slotp}</div>'
            f'<div class="rib">{stars(lvl, 12, bool(up))}</div>'
            f'<div class="bd"><div class="nm">{d}</div><div class="cp">{RAR[rar]} {FAM[f][0].lower()}</div>{body}</div></div>'
            f'{spk}{flagp}{lvburst("right:-13px;top:-15px") if up else ""}</div>')


# ------------------------------------------------------------------ D2: the badge and its tag
def d2(x, y, d, lvl=1, rot=0, cls="", slot=None, up=None, flag=None):
    f, rar, chg, fx, nxt = DR[d]
    if up:
        body = f'<div class="fx"><b>Level {lvl} adds:</b> {nxt[lvl - 2]}.</div><div class="nx">{up} has level {lvl - 1}.</div>'
    else:
        nx = f"Lv {lvl + 1}: {nxt[lvl - 1]}." if lvl < 3 else "Top level."
        body = f'<div class="fx"><b>Every {chg}% you deal:</b> {fx[min(lvl, len(fx)) - 1]}</div><div class="nx">{nx}</div>'
    ex = rays(x + 26, y + 26, 150) if (up and "faded" not in cls) else ""
    slotp = f'<span class="slotp">Slot {slot}</span>' if slot else ""
    flagp = f'<span class="flagp">{flag}</span>' if flag else ""
    cp = "" if (flag or up) else f'<span class="cp">{RAR[rar]} {FAM[f][0].lower()}</span>'
    return (f'{ex}<div class="dr {cls}" style="left:{x}px;top:{y}px;transform:rotate({rot}deg)">'
            f'<div class="tg"><div class="l1"><span class="nm">{d}</span>{cp}</div>{body}{slotp}{flagp}</div>'
            f'<div class="bg">{pog(f, 58, rar, sq=False)}</div><div class="rib">{stars(lvl, 11, bool(up))}</div>'
            f'{lvburst("right:-12px;top:-17px", 48) if up else ""}</div>')


# ------------------------------------------------------------------ chips and fighter stickers
def chip(d, lvl, mode=""):
    f, rar = DR[d][0], DR[d][1]
    pips = "".join(f'<i class="{"n" if (mode == "up" and i == lvl - 1) else ("y" if i < lvl else "")}"></i>' for i in range(3))
    upb = ""
    if mode == "up":
        upb = '<div class="upb">' + svg(13, 13, "-7 -7 14 14", f'<circle r="5.8" fill="{CORAL}" stroke="{INK}" stroke-width="1.6"/><path d="M0,-3.2L3.2,.6H1.2V3.2H-1.2V.6H-3.2Z" fill="#fff"/>') + "</div>"
    return f'<div class="chip">{pog(f, 22, rar, halo=bool(mode))}{upb}<div class="pips">{pips}</div></div>'


def empty_slot():
    return '<div class="chip">' + svg(24, 24, "-12 -12 24 24", f'<circle r="9.5" fill="none" stroke="{LILAC}" stroke-width="2" stroke-dasharray="3.5 3.2"/>') + "</div>"


def fst(x, y, p, name, kind, chips, n=3, v=False, w=None, cls="", prev=None, rot=0, tab=True, extra=""):
    """A fighter and their drive row. prev: ("new", drive) or ("up", drive) lights the slot the pick lands in."""
    cs, k = [], len(chips)
    for d, l in chips:
        cs.append(chip(d, l + 1, "up") if prev and prev == ("up", d) else chip(d, l))
    for i in range(k, n):
        cs.append(chip(prev[1], 1, "new") if (prev and prev[0] == "new" and i == k) else empty_slot())
    w = w or (140 if v else 212)
    h = 80 if v else 64
    col = CORAL if p == 1 else LAGOON
    tabh = f'<span class="tab" style="background:{col}">P{p}</span>' if tab else ""
    return (f'<div class="st fs{" v" if v else ""} {cls}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;transform:rotate({rot}deg)">{tabh}'
            f'<div class="hd">{sil(kind, 22)}</div><div class="fn t14">{name}</div><div class="cr">{"".join(cs)}</div>{extra}</div>')


def curd(x, y, p):
    """A player's pointer that comes down from above, for stickers with something under them."""
    col = CORAL if p == 1 else LAGOON
    d = "M9,3 H17 V13 H23 L13,25 L3,13 H9Z"
    return (f'<div class="cur" style="left:{x}px;top:{y}px;align-items:flex-start">' + svg(26, 28, "0 0 26 28",
            f'<path d="{d}" fill="{col}" stroke="#fff" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="{col}" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round"/>')
            + f'<span class="pt" style="background:{col};margin-left:-3px;margin-bottom:0">P{p}</span></div>')


def ttl(text, x, y, size=21, anchor="start"):
    w = int(len(text) * size * .62) + 12
    tx = 5 if anchor == "start" else w - 5
    return at(x if anchor == "start" else x - w, y, svg(w, size + 12, f"0 0 {w} {size + 12}",
              f'<text x="{tx}" y="{size + 2}" text-anchor="{anchor}" font-family="Brico" font-weight="800" font-size="{size}" letter-spacing="-.5" fill="#fff" stroke="{INK}" stroke-width="4.5" paint-order="stroke" stroke-linejoin="round">{text}</text>'))


def timer(x, y, s, hot=False):
    if hot:
        return at(x - 8, y - 7, burst(str(s), CORAL, 54, 22).replace('y="5"', 'y="8"'), "z-index:6")
    c = 2 * math.pi * 13
    return at(x, y, svg(38, 38, "-19 -19 38 38",
              f'<circle r="17" fill="#fff" stroke="{INK}" stroke-width="2.6"/><circle r="13" fill="none" stroke="#DAD7E8" stroke-width="4"/>'
              f'<circle r="13" fill="none" stroke="{CORAL}" stroke-width="4" stroke-dasharray="{c * s / 20:.1f} {c:.1f}" transform="rotate(-90)"/>'
              f'<text y="5.5" text-anchor="middle" font-family="Brico" font-weight="800" font-size="15" fill="{INK}">{s}</text>'), "z-index:6")


def confetti(seed=0):
    pts = [(-60, 30, SUN), (186, 16, CORAL), (452, 14, LAGOON), (690, 60, SUN), (-40, 236, LAGOON), (700, 250, CORAL), (716, 440, SUN), (-70, 430, CORAL)]
    return "".join(f'<rect x="{x}" y="{y}" width="9" height="9" rx="2" fill="{c}" opacity=".5" transform="rotate({(i * 37 + seed) % 90} {x} {y})"/>' for i, (x, y, c) in enumerate(pts))


def bg_reward(kind):
    """Flat backdrop. rows: a hill band under the second shelf. halves: a paper seam down the middle. none: solo."""
    b = f'<rect x="-107" width="854" height="480" fill="{BG}"/>'
    if kind == "rows":
        b += f'<path d="M-107,236 Q110,222 320,234 T747,230 V480 H-107Z" fill="{BG2}"/>'
    elif kind == "halves":
        z = "".join(f"L{326 if i % 2 else 314},{i * 24}" for i in range(1, 21))
        b += f'<path d="M320,0 {z} H747 V0Z" fill="{BG2}"/>'
    else:
        b += f'<circle cx="320" cy="560" r="330" fill="{BG2}"/>'
    return svg(854, 480, "-107 0 854 480", b + confetti(), 'class="sc"')


# ------------------------------------------------------------------ the two players' offers
PL = {
    1: dict(offers=["Bolt", "Ember", "Tailwind"], fighters=[("Fighter A", 0, [("Ember", 1), ("Metronome", 1)]), ("Fighter B", 1, [("Frost", 1)])]),
    2: dict(offers=["Shatter", "Echo", "Clean Landing"], fighters=[("Fighter C", 2, [("Frost", 2), ("Wildfire", 1)]), ("Fighter D", 3, [("Feather Storm", 1)])]),
}


def owner(p, d):
    for j, (_, _, ch) in enumerate(PL[p]["fighters"]):
        for dd, l in ch:
            if dd == d:
                return j, l
    return None


def resolve(p, st):
    """Work out, for one player's state, which fighter lights up and what the status line says."""
    mode, i, j = st.get("m", "hover"), st.get("i", 0), st.get("j")
    d = PL[p]["offers"][i]
    own = owner(p, d)
    if j is None:
        j = own[0] if own else 0
    name = PL[p]["fighters"][j][0]
    is_up = bool(own) and own[0] == j
    prev = ("up", d) if is_up else ("new", d)
    slot = None if is_up else len(PL[p]["fighters"][j][2]) + 1
    other = 2 if p == 1 else 1
    if mode == "skip":
        line, prev = "Take nothing this time.", None
    elif mode == "who":
        line = f"Who wears {d}? Level up on {name}." if is_up else f"Who wears {d}? {name}, slot {slot}."
    elif mode == "done":
        line = f"{d} is on {name}. Waiting for P{other}."
    elif mode == "auto":
        line = f"3 seconds left: {PL[p]['offers'][0]} will be taken."
    elif is_up:
        line = f"Level up! {name}'s {d} goes to level {own[1] + 1}."
    else:
        line = f"{d} goes to {name}, slot {slot}."
    return mode, i, j, d, prev, slot, line


def offer_card(fn, p, k, x, y, mode, i, slot, rots):
    d = PL[p]["offers"][k]
    own = owner(p, d)
    kw = dict(lvl=own[1] + 1, up=PL[p]["fighters"][own[0]][0]) if own else {}
    sel = k == i and mode != "skip"
    cls = "hov" if sel else ("faded" if mode in ("who", "done") else "")
    if mode == "auto" and k == 0:
        kw["flag"] = "Taken at 0"
    if sel and slot and mode != "done":
        kw["slot"] = slot
    return fn(x, y, d, rot=0 if sel else rots[k], cls=cls, **kw)


# ------------------------------------------------------------------ R1: two shelves, tall cards
def r1_side(p, st, y0, solo=False):
    global SQ
    SQ = True
    mode, i, j, d, prev, slot, line = resolve(p, st)
    out = ""
    for k in range(3):
        out += offer_card(d1, p, k, 14 + k * 132, y0 - (4 if (k == i and mode in ("hover", "auto")) else 0), mode, i, slot, (-1.4, 1, -.8))
    if mode in ("hover", "auto"):
        out += cur(14 + i * 132 + 108, y0 + 172, p)
    for q, (nm, kind, ch) in enumerate(PL[p]["fighters"]):
        chips = list(ch)
        pv = prev if (q == j and mode != "done") else None
        if mode == "done" and q == j:
            chips = [(dd, l + 1) if prev == ("up", dd) else (dd, l) for dd, l in chips] + ([(d, 1)] if prev[0] == "new" else [])
        out += fst(414, y0 + q * 70, p, nm, kind, chips, cls="on" if (mode == "who" and q == j) else "", prev=pv, rot=(.6, -.5)[q], tab=q == 0)
    if mode == "who":
        out += cur(414 + 150, y0 + j * 70 + 40, p)
    if mode == "done":
        out += f'<div class="strip" style="left:414px;top:{y0 + 148}px">Done. Waiting for P{2 if p == 1 else 1}.</div>'
    else:
        out += f'<div class="skp{" on" if mode == "skip" else ""}" style="left:414px;top:{y0 + 148}px;width:92px;transform:rotate(-1.5deg)">Skip</div>'
        if mode == "skip":
            out += cur(414 + 78, y0 + 148 + 16, p)
    SQ = False
    return out, line


def r1(a, b=None, t=14):
    solo = b is None
    p = [bg_reward("none" if solo else "rows"), ttl("Pick a drive", 16, 2), timer(590, 2, t, t <= 5)]
    if solo:
        o, line = r1_side(1, a, 104, True)
        p += [o, say(line), hints(("Left / Right", "Choose"), ("A", "Take"), ("B", "Back"))]
    else:
        p += [r1_side(1, a, 40)[0], r1_side(2, b, 244)[0], hints(("Left / Right", "Choose"), ("A", "Take"), ("B", "Back"))]
    return frame("".join(p))


# ------------------------------------------------------------------ R2: two halves, badge rows
def r2_side(p, st, x0):
    mode, i, j, d, prev, slot, line = resolve(p, st)
    out, x = "", x0 + 30
    for k in range(3):
        out += offer_card(d2, p, k, x, 52 + k * 80, mode, i, slot, (-.5, .4, -.3))
    if mode in ("hover", "auto"):
        out += ptr(x0 + 2, 52 + i * 80 + 22, CORAL if p == 1 else LAGOON)
    if mode != "done":
        out += f'<div class="skp{" on" if mode == "skip" else ""}" style="left:{x + 2}px;top:290px;width:84px;height:26px;line-height:19px;transform:rotate(-1.5deg)">Skip</div>'
        if mode == "skip":
            out += ptr(x0 + 2, 290, CORAL if p == 1 else LAGOON)
    for q, (nm, kind, ch) in enumerate(PL[p]["fighters"]):
        chips = list(ch)
        pv = prev if (q == j and mode != "done") else None
        if mode == "done" and q == j:
            chips = [(dd, l + 1) if prev == ("up", dd) else (dd, l) for dd, l in chips] + ([(d, 1)] if prev[0] == "new" else [])
        out += fst(x + q * 144, 324, p, nm, kind, chips, v=True, cls="on" if (mode == "who" and q == j) else "", prev=pv, rot=(-.6, .5)[q], tab=q == 0)
    if mode == "who":
        out += curd(x + j * 144 + 86, 300, p)
    out += f'<div class="strip" style="left:{x}px;top:411px">{line}</div>'
    return out


def r2(a, b=None, t=14):
    solo = b is None
    p = [bg_reward("none" if solo else "halves"), ttl("Pick a drive", 222, 0), timer(372, 2, t, t <= 5)]
    if solo:
        p += [r2_side(1, a, 163)]
    else:
        p += [f'<div class="pp" style="left:30px;top:10px;background:{CORAL};transform:rotate(-4deg)">P1</div>',
              f'<div class="pp" style="left:572px;top:10px;background:{LAGOON};transform:rotate(4deg)">P2</div>', r2_side(1, a, 0), r2_side(2, b, 320)]
    p.append(hints(("Up / Down", "Choose"), ("A", "Take"), ("B", "Back")))
    return frame("".join(p))


RSTATES = [
    ("Solo", "One player: the same stickers at the same size, centred. Nothing to relearn when a second player joins.", (dict(i=0), None, 14)),
    ("Hovering a level-up", "P1 is on Ember, which Fighter A already wears. The offer is marked from the moment it appears; hovering lights the chip it will raise.", (dict(i=1), dict(i=1), 12)),
    ("Choosing who wears it", "After A, the other two offers fade and the pointer moves to the player's two fighters. It starts on the fighter the game would pick. B goes back to the three.", (dict(m="who", i=0, j=1), dict(i=1), 9)),
    ("One player done", "P1 has taken Bolt for Fighter B. The chip is in the row and P1's side says it is waiting. P2 keeps choosing.", (dict(m="done", i=0, j=1), dict(i=2), 7)),
    ("Timer nearly out", "Under 5 seconds the timer turns into a coral burst and the first offer of anyone still choosing is flagged as the one that will be taken.", (dict(m="done", i=0, j=1), dict(m="auto", i=2), 3)),
    ("Skip", "Skip is a fourth sticker after the three offers, reached with the same cursor. Shown: P1 about to take nothing.", (dict(m="skip"), dict(i=0), 11)),
]


# ------------------------------------------------------------------ keystones
KS = {
    "Plague Bearer": ("Your Burning spreads to nearby foes.", "fire", "Good with fire"),
    "Glass Core": ("Everyone deals 30% more and takes 30% more.", None, "Good with anything"),
    "Long Fuse": ("Drives need twice the damage to charge, then fire twice.", None, "Good with slow drives"),
}


def kem(k, size):
    """Keystone emblem on a white disc."""
    if k == "Plague Bearer":
        fl = lambda x, y, s: f'<g transform="translate({x} {y}) scale({s})"><path d="{FLAME}" fill="{CORAL}" stroke="{INK}" stroke-width="{2.4 / s:.0f}" stroke-linejoin="round"/></g>'
        e = fl(-8.5, 5, .1) + fl(8.5, 5, .1) + fl(0, -1, .2)
    elif k == "Glass Core":
        e = (f'<path d="M0,-13 L10,-3 L0,13 L-10,-3Z" fill="#BDEBFF" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round"/>'
             f'<path d="M-10,-3H10M-3,-3L1,3L-2,7" fill="none" stroke="{INK}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>')
    else:
        e = (f'<circle cx="-2" cy="4" r="8.5" fill="{INK}"/><path d="M4,-3 C7,-8 10,-6 11,-11" fill="none" stroke="{INK}" stroke-width="2.4" stroke-linecap="round"/>'
             f'<path transform="translate(11.5 -12.5)" d="{SPARK}" fill="{SUN}" stroke="{INK}" stroke-width="1.5" stroke-linejoin="round"/>')
    return svg(size, size, "-21 -21 42 42", f'<circle r="18.5" fill="#fff" stroke="{INK}" stroke-width="3"/>{e}')


def wedge_svg(w, h, ins, face, dash=False):
    pts = f"M10,10 H{w - 10} L{w - 10 - ins},{h - 10} H{10 + ins}Z"
    a = 'stroke-linejoin="round"'
    if dash:
        return svg(w, h, f"0 0 {w} {h}", f'<path d="{pts}" fill="rgba(42,26,110,.35)" stroke="#C9BFF5" stroke-width="2.5" stroke-dasharray="6 5" {a}/>')
    return svg(w + 8, h + 10, f"0 0 {w + 8} {h + 10}",
               f'<path d="{pts}" transform="translate(4 6)" fill="{INK}" stroke="{INK}" stroke-width="19" {a}/>'
               f'<path d="{pts}" fill="#fff" stroke="#fff" stroke-width="19" {a}/><path d="{pts}" fill="{INK}" stroke="{INK}" stroke-width="13" {a}/>'
               f'<path d="{pts}" fill="{face}" stroke="{face}" stroke-width="8" {a}/>')


def kgood(k, size=18):
    _, fam, good = KS[k]
    return f'<span class="kg">{pog(fam, size, sq=False) if fam else ""}{good}</span>'


def wedge(x, y, k, w=186, h=276, rot=0, hov=False, big=1.0):
    rule = KS[k][0]
    a, b = k.split(" ")
    return (f'<div class="kw{" hov" if hov else ""}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;transform:rotate({rot}deg);z-index:{3 if hov else 1}">'
            f'{wedge_svg(w, h, 22, SUN if hov else INK)}<div class="em" style="top:-22px">{kem(k, round(62 * big))}</div>'
            f'<div class="kin" style="left:22px;top:{round(44 * big)}px;width:{w - 44}px">'
            f'<div class="kn" style="font-size:{round(25 * big)}px;line-height:{round(25 * big)}px">{a}<br>{b}</div>'
            f'<div class="kr" style="font-size:{14.5 * big:.1f}px;line-height:{round(18 * big)}px;margin:{round(12 * big)}px 6px 0">{rule}</div></div>'
            f'<div class="kin" style="left:0;bottom:30px;width:{w}px">{kgood(k)}</div></div>')


def sockets(x, y, filled=0, pick=1):
    w = ""
    for i in range(3):
        on = i < filled
        w += svg(22, 22, "0 0 22 22", f'<path d="M3,4H19L16,18H6Z" fill="{SUN if on else "none"}" stroke="{INK if on else "#C9BFF5"}" stroke-width="2.2" stroke-linejoin="round" stroke-dasharray="{"0" if on else "3 2.5"}"/>')
    return at(x, y, f'<div class="sock">{w}<span class="wt" style="margin-left:4px">Keystone {pick} of 3</span></div>')


def bg_key(arch=False):
    stars_ = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{SUN}" opacity=".7"/>' for x, y, r in ((-64, 70, 2), (70, 60, 1.6), (300, 66, 1.6), (566, 62, 1.8), (700, 96, 2.2), (-30, 300, 1.6), (704, 320, 1.8)))
    b = f'<rect x="-107" width="854" height="480" fill="#3A2B86"/>{stars_}'
    if arch:
        b += (f'<path d="M366,394 V238 A134,134 0 0 1 634,238 V394 H566 V238 A66,66 0 0 0 434,238 V394Z" fill="#5849AE"/>'
              f'<path d="M434,394 V238 A66,66 0 0 1 566,238 V394Z" fill="#2C1E70"/><rect x="-107" y="394" width="854" height="86" fill="#2C1E70"/>')
    else:
        b += (f'<path d="M-107,480 V330 A430,430 0 0 1 747,330 V480Z" fill="#43348F"/><path d="M-20,480 V360 A340,340 0 0 1 660,360 V480Z" fill="#3A2B86"/>'
              f'<rect x="-107" y="398" width="854" height="82" fill="#2C1E70"/>')
    return svg(854, 480, "-107 0 854 480", b, 'class="sc"')


def big_rays(cx, cy, r=420, n=18, col=SUN, op=.22):
    p = ""
    for i in range(n):
        a0, a1 = (i - .25) * 2 * math.pi / n, (i + .25) * 2 * math.pi / n
        p += f'<path d="M{cx},{cy} L{cx + r * math.cos(a0):.0f},{cy + r * math.sin(a0):.0f} L{cx + r * math.cos(a1):.0f},{cy + r * math.sin(a1):.0f}Z" fill="{col}" opacity="{op}"/>'
    return svg(854, 480, "-107 0 854 480", p, 'class="sc"')


KNAMES = list(KS)


def k1(state="pick", hov=0):
    p = [bg_key()]
    if state == "pick":
        p += [ttl("Choose a keystone", 16, 2), at(22, 36, '<div class="wt">One rule for the whole run. The party shares it.</div>'), sockets(444, 12)]
        for i, k in enumerate(KNAMES):
            on = i == hov
            p.append(wedge(28 + i * 199, 106 + (0 if i == 1 else 12) - (8 if on else 0), k, rot=0 if on else (-4, 0, 4)[i], hov=on))
        p += [curd(28 + hov * 199 + 16, 62, 1), say("Burning foes set fire to others close by. Nobody has a fire drive yet."),
              hints(("Left / Right", "Choose"), ("A", "Take it"), ("B", "Back to camp"))]
    else:
        k = KNAMES[hov]
        p += [big_rays(320, 230), sockets(444, 12, 1),
              wedge(-70, 170, KNAMES[1], rot=-24).replace('class="kw"', 'class="kw" data-o="1"').replace("z-index:1", "z-index:1;opacity:.3"),
              wedge(524, 170, KNAMES[2], rot=24).replace("z-index:1", "z-index:1;opacity:.3"),
              wedge(203, 92, k, w=234, h=300, hov=True, big=1.16),
              at(388, 70, burst("Set!", CORAL, 66, 17), "z-index:5"),
              ttl("Plague Bearer is the rule", 16, 2),
              say("Your Burning spreads to nearby foes, for the whole run."), hints(("A", "Start the first fight"))]
    return frame("".join(p))


def slab(x, y, k, hov=False, rot=0):
    rule = KS[k][0]
    em = svg(62, 68, "0 0 62 68", f'<path d="M6,6H56L48,62H14Z" fill="#fff" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>')
    return (f'<div class="ks{" hov" if hov else ""}" style="left:{x}px;top:{y}px;transform:rotate({rot}deg)"><div class="em">{em}'
            f'<div style="position:absolute;left:8px;top:8px">{kem(k, 46)}</div></div>'
            f'<div class="tx"><div class="kn" style="font-size:21px;line-height:23px">{k}</div>'
            f'<div class="kr" style="font-size:12.5px;line-height:15px;margin:2px 0 4px;height:30px">{rule}</div>{kgood(k, 16)}</div></div>')


def crown(k=None, solid=False):
    """The arch on the right of K2: three seats for the run's three keystones; the hovered one tries the first seat."""
    out = ""
    for ang, lab in ((-52, "1"), (52, "2")):
        cx, cy = 500 + 100 * math.sin(math.radians(ang)), 238 - 100 * math.cos(math.radians(ang))
        out += at(cx - 38, cy - 33, wedge_svg(76, 66, 9, None, True) + f'<div style="position:absolute;left:31px;top:23px">{s3.lock(13, "#C9BFF5")}</div>', f"transform:rotate({ang}deg)")
    if k:
        a, b = k.split(" ")
        face = SUN if solid else INK
        out += (f'<div class="kw{" hov" if solid else ""}" style="left:446px;top:88px;width:108px;height:96px;z-index:3">{wedge_svg(108, 96, 12, face)}'
                f'<div class="kin" style="left:10px;top:25px;width:88px"><div class="kn" style="font-size:15px;line-height:16px">{a}<br>{b}</div></div>'
                f'<div class="em" style="top:-20px">{kem(k, 40)}</div></div>')
    party = "".join(at(440 + i * 31, 322 + (0, 4, 2, 5)[i], sil(i, 26)) for i in range(4))
    out += party + at(366, 290, '<div class="wt" style="width:268px;text-align:center">One rule for all four</div>')
    out += at(366, 206, '<div class="wt" style="width:268px;text-align:center;color:#C9BFF5;line-height:13px">Two more seats open<br>after bosses 1 and 2</div>')
    return out


def k2(state="pick", hov=0):
    p = [bg_key(True)]
    if state == "pick":
        p += [ttl("Choose a keystone", 16, 2), at(22, 36, '<div class="wt">One rule for the whole run. The party shares it.</div>')]
        for i, k in enumerate(KNAMES):
            on = i == hov
            p.append(slab(42 if on else 28, 66 + i * 108, k, on, 0 if on else (-.8, .7, -.6)[i]))
        p += [ptr(10, 66 + hov * 108 + 34), crown(KNAMES[hov]), say("Burning foes set fire to others close by. Nobody has a fire drive yet."),
              hints(("Up / Down", "Choose"), ("A", "Take it"), ("B", "Back to camp"))]
    else:
        k = KNAMES[hov]
        p += [big_rays(500, 136, 300, 16), ttl("Plague Bearer is the rule", 16, 2), slab(28, 150, k, True, -1.5), crown(k, True),
              at(548, 60, burst("Set!", CORAL, 60, 16), "z-index:5"),
              say("Your Burning spreads to nearby foes, for the whole run."), hints(("A", "Start the first fight"))]
    return frame("".join(p))


# ------------------------------------------------------------------ sheet parts
def box(inner, w, h, zoom=1.0, label=None, cap=None, dots=()):
    lab = f'<div class="tag">{label}</div>' if label else ""
    c = f'<p class="cap" style="max-width:{w * zoom:.0f}px">{cap}</p>' if cap else ""
    d = "".join(f'<span class="co" style="left:{x * zoom - 12:.0f}px;top:{y * zoom - 12:.0f}px">{n}</span>' for n, x, y in dots)
    return (f'<div>{lab}<div class="gb" style="width:{w * zoom:.0f}px;height:{h * zoom:.0f}px"><div class="g" style="zoom:{zoom};width:{w}px;height:{h}px">{inner}</div>{d}</div>{c}</div>')


FAM6 = ["Ember", "Bolt", "Frost", "Tailwind", "Clean Landing", "Echo"]

LEG = ["<b>Family</b>: the colour and the glyph together, never colour alone.",
       "<b>Level</b>: three stars. A duplicate fills the next one.",
       "<b>Name</b>, then rarity and family in words.",
       "<b>What charges it</b>, in bold: always damage you deal, in percent.",
       "<b>What it does</b> when it fires, in one sentence.",
       "<b>What the next level adds</b>, in the quieter colour.",
       "<b>Slot</b>: only shown while the card is on its way to a fighter, so slot order can matter later without the card changing.",
       "<b>Rarity</b> is the edge: plain, a thick white die-cut, or a foil rim with a spark."]


def legend(two=False):
    return f'<ol class="legend{" two" if two else ""}">' + "".join(f"<li>{t}</li>" for t in LEG) + "</ol>"


def card_section_d1():
    global SQ
    SQ = True
    anat = box(d1(32, 14, "Ember", 2, slot=3), 190, 216, 2.2, dots=((1, 16, 34), (2, 16, 56), (3, 16, 78), (4, 16, 108), (8, 16, 160), (7, 174, 28), (5, 174, 128), (6, 174, 184)))
    six = "".join(d1(12 + i * 137, 16, "Ember", l, rot=r) for i, (l, r) in enumerate(((1, -1), (2, .8), (3, -.6))))
    six += "".join(d1(12 + (i + 3) * 137 + 6, 16, n, rot=r) for i, (n, r) in enumerate((("Ember", .9), ("Bolt", -.8), ("Echo", .6))))
    lv = box(six, 846, 220, 1, "Levels 1, 2 and 3 of Ember, then the three rarities: Common, Rare, Epic (names assumed)")
    fam = box("".join(d1(12 + i * 137 + (6 if i > 2 else 0), 16, n, rot=(-1, .8, -.6, .9, -.8, .6)[i]) for i, n in enumerate(FAM6)), 846, 220, 1, "One card from each of six families")
    row = box(fst(14, 16, 1, "Fighter A", 0, [("Ember", 2), ("Frost", 1)], rot=-.6) + fst(14, 92, 2, "Fighter C", 2, [("Bolt", 1), ("Echo", 3), ("Tailwind", 2), ("Clean Landing", 1)], n=5, rot=.5),
              240, 170, 1.25, "The chip in a fighter's row: 3 slots, later 4 and 5",
              "A square tile with the family glyph; level is the three pips under it; the edge still shows rarity. A dashed ring is an empty slot.")
    up = box(d1(62, 36, "Ember", 2, up="Fighter A") + fst(18, 246, 1, "Fighter A", 0, [("Ember", 1), ("Metronome", 1)], prev=("up", "Ember"), w=212), 250, 326, 1.0, "Level-up",
             "Rays behind the card, a coral burst, the new star drawn larger in coral, and the text switches to what the level adds and who has it.")
    SQ = False
    return (f'<div class="cardrow">{anat}<div style="width:216px">{legend()}</div><div>{lv}<div style="height:16px"></div>{fam}</div></div>'
            f'<div class="cardrow">{row}{up}<div class="side" style="width:560px"><h3>The idea</h3><p>A trading card you would stick in an album: a colour band with the family glyph, a ribbon of stars, then the words. Three of them side by side is the picture most players expect from a pick of three.</p>'
            f'<h3>What it costs</h3><p>At 126 game pixels wide the sentence wraps to three or four short lines, and the card is a different shape from the thing that ends up in the row and orbiting the fighter, so the chip has to be learned separately.</p>'
            f'<p class="trade">The most collectable. The hardest to read quickly on a 480-line screen.</p></div></div>')


def card_section_d2():
    anat = box(d2(22, 24, "Ember", 2, slot=3), 346, 116, 2.1, dots=((1, 48, 10), (8, 9, 50), (2, 48, 106), (3, 110, 13), (7, 328, 24), (4, 328, 58), (5, 328, 73), (6, 328, 88)))
    lv = box("".join(d2(12, 12 + i * 80, "Ember", i + 1, rot=(-.5, .4, -.3)[i]) for i in range(3)), 310, 254, 1, "Levels 1, 2 and 3")
    rr = box("".join(d2(12, 12 + i * 80, n, rot=(.4, -.5, .3)[i]) for i, n in enumerate(("Ember", "Bolt", "Echo"))), 310, 254, 1, "Common, Rare, Epic (names assumed)")
    fam = box("".join(d2(12 + (i % 2) * 300, 12 + (i // 2) * 80, n, rot=(-.5, .4, -.3, .5, -.4, .3)[i]) for i, n in enumerate(FAM6)), 608, 254, 1, "One from each of six families")
    row = box(fst(14, 16, 1, "Fighter A", 0, [("Ember", 2), ("Frost", 1)], rot=-.6) + fst(14, 92, 2, "Fighter C", 2, [("Bolt", 1), ("Echo", 3), ("Tailwind", 2), ("Clean Landing", 1)], n=5, rot=.5),
              240, 170, 1.25, "The chip in a fighter's row: 3 slots, later 4 and 5",
              "The chip is the same badge, smaller. Level is the three pips under it. Round, so a charge ring can wrap it in a fight (HUD not designed yet).")
    up = box(d2(14, 30, "Ember", 2, up="Fighter A") + fst(70, 132, 1, "Fighter A", 0, [("Ember", 1), ("Metronome", 1)], prev=("up", "Ember"), w=212), 316, 212, 1.0, "Level-up",
             "Rays behind the badge, a coral burst on the tag, the new star larger in coral, and the tag says what the level adds and who has it.")
    return (f'<div class="cardrow"><div>{anat}<div style="height:14px"></div><div style="width:726px">{legend(True)}</div></div>{lv}{rr}</div>'
            f'<div class="cardrow">{fam}{row}<div>{up}</div></div>'
            f'<div class="side" style="max-width:1100px"><h3>The idea</h3><p>The drive is a round badge, the same object that orbits the fighter, sits in the row and will carry the charge ring. The words ride on a paper tag tied to it, so the sentence gets a full line instead of a narrow column.</p>'
            f'<p class="trade">One shape from pick to row to fight, and the easiest to read. Less of a "card": three of them make a list, not a hand.</p></div>')


def reward_layout(tag, name, fn, side):
    main = fn(dict(i=0), dict(i=1), 14)
    st = "".join(f'<div><div class="tag">{n}</div><div class="g">{fn(*args)}</div><p class="cap">{cap}</p></div>' for n, cap, args in RSTATES)
    return (f'<div class="lay"><div class="hd"><b>{tag}</b><span>{name}</span></div>'
            f'<div class="mainrow"><div><div class="g">{main}</div><p class="cap"><b>Two players, 14 seconds left.</b> P1 is on Bolt, a new drive for Fighter A. P2 is on Echo. Ember is already marked as a level-up.</p></div>'
            f'<div class="side">{side}</div></div><div class="states">{st}</div></div>')


SIDE_R1 = """<h3>The idea</h3>
<p>Each player has a shelf: P1's across the top, P2's across the bottom. Three tall cards (D1) stand on it, with that player's two fighters and Skip to the right.</p>
<h3>Reading order</h3>
<ol><li><b>Your three cards</b>, left to right. Each carries its whole sentence.</li><li><b>Your two fighters</b> and their rows. A lit chip shows where the hovered card would land.</li>
<li><b>Skip</b>, under the fighters.</li><li><b>The timer</b>, top right, shared.</li></ol>
<h3>Buttons</h3>
<table><tr><td>Left / Right</td><td>Move across your three cards, then Skip.</td></tr><tr><td>A</td><td>Take the card. The pointer moves to your fighters.</td></tr>
<tr><td>Up / Down, A</td><td>Choose who wears it. It starts on the fighter the game would pick, so A, A is the fast path.</td></tr>
<tr><td>B</td><td>Back to the three.</td></tr><tr><td>Timer at 0</td><td>The first card goes to the fighter the game would pick.</td></tr></table>
<p class="trade">Looks like a hand of cards and reads left to right. Six cards of wrapped text make a busy screen, and there is no room left for a line that says what A will do.</p>"""

SIDE_R2 = """<h3>The idea</h3>
<p>The screen is split down a paper seam: P1's side on the left, P2's on the right, like the camp. Each side is a short list of three badges with their tags (D2), then Skip, then that player's two fighters.</p>
<h3>Reading order</h3>
<ol><li><b>Your three offers</b>, top to bottom. Each tag is a full sentence on two lines.</li><li><b>Skip</b>, the fourth row.</li>
<li><b>Your two fighters</b> and their rows. A lit chip shows where the hovered offer would land.</li><li><b>Your white strip</b>: what A does right now, in words.</li>
<li><b>The timer</b>, top centre, on the seam.</li></ol>
<h3>Buttons</h3>
<table><tr><td>Up / Down</td><td>Move down your three offers, then Skip.</td></tr><tr><td>A</td><td>Take the offer. The pointer moves to your fighters.</td></tr>
<tr><td>Left / Right, A</td><td>Choose who wears it. It starts on the fighter the game would pick, so A, A is the fast path.</td></tr>
<tr><td>B</td><td>Back to the three.</td></tr><tr><td>Timer at 0</td><td>The first offer goes to the fighter the game would pick.</td></tr></table>
<p class="trade">The same one-column list as the camp, once per player. Each side is self-contained and says what A will do. It is a list, so it has less of the "pick a card" theatre.</p>"""

SIDE_K1 = """<h3>The idea</h3>
<p>Three big stones fill the screen, cut like the wedge at the top of an arch and fanned as if they were part of one. Drives are small and white; keystones are large and grape ink with sunny names, so the two picks can never be mistaken for each other.</p>
<h3>Buttons</h3>
<table><tr><td>Left / Right</td><td>Move between the three stones.</td></tr><tr><td>A</td><td>Take it.</td></tr><tr><td>B</td><td>Back to camp (run start only; nothing is saved yet).</td></tr></table>
<p style="margin-top:10px">One pointer, Player 1's, as in the camp. No timer. The three small seats at the top right count the run's three keystone picks.</p>
<p class="trade">The biggest moment and the plainest controls. Each stone has room for one rule and one hint, no more.</p>"""

SIDE_K2 = """<h3>The idea</h3>
<p>A list of three slabs on the left, like the camp, and on the right a paper arch with the party standing under it. The hovered keystone tries the top seat of the arch; taking it sets it there. Two more seats wait for the bosses.</p>
<h3>Buttons</h3>
<table><tr><td>Up / Down</td><td>Move between the three slabs.</td></tr><tr><td>A</td><td>Take it.</td></tr><tr><td>B</td><td>Back to camp (run start only).</td></tr></table>
<p style="margin-top:10px">Same single pointer and no timer.</p>
<p class="trade">Tells the story of the run (three stones make the arch) and matches the camp list. The choices themselves are smaller, so the moment is quieter.</p>"""


def key_layout(tag, name, fn, side, cap):
    return (f'<div class="lay"><div class="hd"><b>{tag}</b><span>{name}</span></div><div class="kside"><div><div class="g">{fn("pick")}</div>'
            f'<p class="cap"><b>Run start.</b> Plague Bearer hovered. The white strip explains it and says how it fits the party.</p></div>'
            f'<div class="side">{side}<h3 style="margin-top:18px">The taken moment</h3><div class="tk"><div class="g">{fn("taken")}</div></div><p class="cap">{cap}</p></div></div></div>')


def famkey():
    items = "".join(f'<span>{pog(k, 30, sq=False)}{FAM[k][0]}</span>' for k in ("fire", "bolt", "frost", "wind", "tech", "util"))
    spare = "".join(f'<span>{pog(k, 30, sq=False)}</span>' for k in ("stone", "rose"))
    return (f'<div class="famkey"><b style="color:#1A1830">Families</b>{items}<span>{spare}<em>two spare colours and glyphs, so the set reaches eight</em></span>'
            f'<em>None of them is coral, lagoon or sunny: those stay Player 1, Player 2 and the cursor.</em></div>')


def html():
    holo = "".join(f'<stop offset="{i / 5:.2f}" stop-color="{c}"/>' for i, c in enumerate(HOLO.split(",")))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Envoy UI step 4</title><style>{CSS}</style></head>
<body><svg width="0" height="0" style="position:absolute"><defs><linearGradient id="holo" x1="0" y1="0" x2="1" y2="1">{holo}</linearGradient></defs></svg><div id="c">
<div class="top"><h1>Drives, rewards and keystones</h1>
<p>Step 4 of the UI design. Three choices: the drive card (D1 or D2), the pick-of-three screen (R1 or R2) and the keystone pick (K1 or K2). The fight HUD, the map, the shop and results are not designed yet.</p></div>
<div class="key"><span><i style="background:#fff;box-shadow:inset 0 0 0 2.5px {INK}"></i>Outlined in grape ink: a sticker, as before.</span>
<span><i style="background:{SUN};box-shadow:inset 0 0 0 2.5px {INK}"></i>Sunny: what a cursor is on. Coral arrow is P1, lagoon is P2.</span>
<span><i style="background:{CORAL};box-shadow:inset 0 0 0 2.5px {INK}"></i>A coral burst: something just happened or is about to (level up, timer, set).</span></div>

<div class="sec"><h2>The drive card</h2>
<p class="lede">The same facts on both: family, level, name, rarity, what charges it, what it does, what the next level adds, and a slot when it is going somewhere. Charge is always written as damage dealt. Shown on the violet the game draws behind them.</p>
{famkey()}
<div class="lay"><div class="hd"><b>D1</b><span>The tall card</span></div>{card_section_d1()}</div>
<div class="lay"><div class="hd"><b>D2</b><span>The badge and its tag</span></div>{card_section_d2()}</div></div>

<div class="sec"><h2>The pick of three</h2>
<p class="lede">After a fight each player is offered three drives and takes one or skips, both at once, with 20 seconds on the clock. R1 is drawn with the D1 card and R2 with the D2 badge, because each layout only works with that shape. Same steps in both: choose an offer, A, choose which of your two fighters wears it, A.</p>
{reward_layout("R1", "Two shelves", r1, SIDE_R1)}
{reward_layout("R2", "Two halves", r2, SIDE_R2)}</div>

<div class="sec"><h2>The keystone pick</h2>
<p class="lede">At run start and after bosses 1 and 2 the party takes one of three keystones: one rule for everyone, for the rest of the run. It is drawn in grape ink and cut as a wedge, the stone at the top of an arch, so it never looks like a drive.</p>
{key_layout("K1", "Three stones", k1, SIDE_K1, "The chosen stone grows to the centre and turns sunny, the other two fall away, and the first seat at the top right fills.")}
{key_layout("K2", "Build the arch", k2, SIDE_K2, "The slab stays, the others leave, and the stone sets into the top of the arch over the party.")}</div>

<div class="sec"><h2>Recommended: D2, R2 and K1 at actual size</h2>
<p class="lede">640 by 480, the size the game renders before upscaling. Smallest text is 11 px (rarity and next-level lines); sentences are 11.5 px and up.</p>
<div class="act3"><div><div class="g">{r2(dict(i=0), dict(i=1), 14)}</div><p class="cap"><b>Pick of three, R2 with D2 badges.</b></p></div>
<div><div class="g">{k1("pick")}</div><p class="cap"><b>Keystone pick, K1.</b></p></div></div></div>

<div class="rec" style="grid-template-columns:150px 1fr 1fr 1fr"><h2>Recommended</h2>
<p><b>D2, the badge and its tag.</b> It is one shape from the pick to the row to the thing orbiting the fighter, the sentence gets a full line, and a round badge is where a charge ring belongs.</p>
<p><b>R2, two halves.</b> It is the camp's plain list once per player: your side, your cursor, up and down, A. It is the only layout with room to say in words what A will do, which matters most for a level-up.</p>
<p><b>K1, three stones.</b> Full-screen, dark and wedge-cut against small white badges in a list: the keystone reads as a different and bigger kind of choice at a glance, with left, right and A.</p></div>
<p class="foot">Original vector art, family glyphs included. Fonts: Bricolage Grotesque, Source Sans 3 (SIL OFL). Fighters are neutral silhouettes with placeholder names. Drive effects, charge amounts, level bonuses, rarity names and the Long Fuse keystone are invented for the mock; only the drive and keystone names given so far are real.</p>
</div></body></html>"""


def main():
    src = HERE / "step4.html"
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
        tall = page.evaluate("""() => {
            const out = [];
            for (const c of document.querySelectorAll('.dc')) { const fx = c.querySelector('.fx'), nx = c.querySelector('.nx'); const a = fx.getBoundingClientRect(), b = nx.getBoundingClientRect(); if (a.bottom > b.top + .5) out.push('card text collides: ' + c.querySelector('.nm').textContent + ' / ' + fx.textContent.slice(0, 30)); }
            for (const t of document.querySelectorAll('.dr .tg')) { if (t.scrollHeight > t.clientHeight + 1) out.push('tag too tall: ' + t.textContent.slice(0, 40)); const l = t.querySelector('.l1'); if (l.scrollWidth > l.clientWidth + 1) out.push('tag name line too wide: ' + l.textContent); }
            for (const s of document.querySelectorAll('.strip')) { if (s.offsetWidth > 286) out.push('strip too wide (' + s.offsetWidth + '): ' + s.textContent); }
            for (const s of document.querySelectorAll('.say, .hints')) { if (s.offsetLeft + s.offsetWidth > 620) out.push(s.className + ' too wide: ' + s.textContent.slice(0, 50)); }
            for (const k of document.querySelectorAll('.ks .tx, .kw .in')) { if (k.scrollWidth > k.clientWidth + 1) out.push('keystone text too wide: ' + k.textContent.slice(0, 40)); }
            return out; }""")
        for b in sorted(set(tall)):
            print(b)
        page.locator("#c").screenshot(path=str(HERE / "preview" / "step4-cards.png"), type="png")
        print(page.evaluate("document.getElementById('c').offsetHeight"))
        browser.close()


if __name__ == "__main__":
    main()
