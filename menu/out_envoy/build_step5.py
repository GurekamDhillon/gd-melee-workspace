#!/usr/bin/env python3
"""Envoy UI, step 5: the in-fight HUD.

Writes step5.html beside this file and renders preview/step5-hud.png (1600 px wide) with headless
Chromium, like build_step4.py. Every mock screen is authored in game pixels (640x480 native, or
853x480 for 16:9) and scaled with CSS zoom. Original vector art only; the fight is a flat placeholder
stage with neutral silhouettes. Fonts: Bricolage Grotesque and Source Sans 3 (SIL OFL).
"""
import math
from pathlib import Path
from playwright.sync_api import sync_playwright

import build_step4 as s4
from build_step2 import svg, SUN, INK, CORAL, LAGOON, LILAC, FLAME, BURST
from build_step3 import at, sil, FLAME_IN
from build_step4 import pog, DR, SPARK

HERE = Path(__file__).resolve().parent
HEATC = {"cold": "#B9B2DE", "warm": "#FFBE2E", "hot": "#FF8A1F", "blaze": "#FF4A1C"}
HEATN = {"cold": "Cold", "warm": "Warm", "hot": "Hot", "blaze": "Blazing"}
MARKS = (25, 60, 110)
TRACK = "#170E45"
_n = [0]

CSS = s4.CSS + r"""
.two{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:start}
.two .lay{margin-bottom:0;padding:18px 5px 16px}
.two .lay .hd,.two .lay .note,.two .lay .trade{margin-left:15px;margin-right:15px}
.lay .note{font-size:15.5px;line-height:1.4;color:#45425E;margin-top:10px}
.lay .trade{font-size:15.5px;line-height:1.35;font-weight:700;border-left:4px solid #1A1830;padding-left:10px;margin-top:12px;color:#1A1830}
.where{display:grid;grid-template-columns:1fr 1fr 1fr;gap:26px;background:#F6F5FA;border-radius:18px;padding:18px 20px;margin-top:20px}
.where h3{font-weight:900;font-size:17px;margin-bottom:5px}
.where p{font-size:15.5px;line-height:1.4;color:#45425E}
.where b{color:#1A1830;font-weight:700}
.mt3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px 10px;margin:0 15px}
.mt .tag{margin-bottom:4px}
.mt .cap{margin-top:5px;font-size:13.5px}
.mtb{position:relative;width:226px;height:98px;border-radius:8px;overflow:hidden;background:#1E2A4A}
.mtb .g{position:relative;zoom:1.15;width:196px;height:85px}
.act5{display:grid;grid-template-columns:640px 853px;gap:22px;align-items:start}

/* ---------- game-pixel world: the fight ---------- */
.fz{position:relative;width:640px;height:480px;overflow:hidden;background:#1E2A4A}
.fz.wide{width:853px}
.fz svg,.mtb svg{overflow:visible;display:block}
.fz .sc{position:absolute;left:0;top:0}
.hp{position:absolute}
.hp .pt{position:absolute;left:0;top:0}
.hrow{display:flex;position:relative}
.hc{position:relative;width:30px;height:38px;flex:none}
.hc .pips{position:absolute;left:50%;top:31px;transform:translateX(-50%);display:flex;gap:2px}
.hc .pips i{width:7px;height:6px;border-radius:2px;border:1.5px solid #8E88B8;background:#2A1A6E}
.hc .pips i.y{background:#fff;border-color:#2A1A6E;box-shadow:0 0 0 1px #fff}
.hc .pips.a i{width:7px;height:7px;border-radius:50%}
.hc .pips.a i.y{background:#FFD84A;border-color:#2A1A6E;box-shadow:0 0 0 1px #fff}
.hc .dp{position:absolute;left:19px;top:-6px}
.bn2{display:inline-flex;align-items:center;gap:5px;height:22px;border:2.5px solid #2A1A6E;border-radius:9px;box-shadow:2px 3px 0 #2A1A6E;padding:0 6px 0 5px;white-space:nowrap;background:#fff}
.bn2 .n{font-size:11px;line-height:12px;font-weight:700;color:#5A4C99}
.bn2 .d{font-family:"Brico";font-weight:800;font-size:14px;line-height:14px;letter-spacing:-.3px;min-width:27px}
.bn2 .mi{display:flex;gap:1px}
.fp{position:absolute;display:flex;align-items:center;gap:5px;background:#2A1A6E;border:2.5px solid #fff;border-radius:11px;box-shadow:0 0 0 2px #2A1A6E,2px 4px 0 2px #2A1A6E;padding:0 8px 0 5px;color:#fff;white-space:nowrap}
.fp .n{font-size:11px;line-height:11px;font-weight:700;color:#C9BFF5}
.fp .d{font-family:"Brico";font-weight:800;letter-spacing:-.4px}
.fp .dv{display:flex;gap:1px;margin-left:2px}
.fp .wd{position:absolute;right:8px;bottom:-11px;display:flex;align-items:center;gap:2px;background:#fff;border:2px solid #2A1A6E;border-radius:7px;padding:0 4px 0 2px;height:14px}
.fp .wd i{width:4px;height:4px;border-radius:50%;background:#FF7A1F;border:1px solid #2A1A6E;box-sizing:content-box}
.fp .wd i.o{background:#fff}
.sdots{display:flex;gap:4px}
.sdots i{width:14px;height:14px;border-radius:50%;background:#fff;border:2.5px solid #2A1A6E;box-shadow:0 0 0 1.5px #fff,1.5px 3px 0 1.5px #2A1A6E}
.sdots i.off{background:#2A1A6E;border-color:#fff;box-shadow:none;transform:scale(.6)}
.nt{display:inline-block;background:#fff;border:2px solid #2A1A6E;border-radius:7px;font-family:"Brico";font-weight:800;font-size:12px;line-height:13px;padding:0 5px 1px;white-space:nowrap;color:#2A1A6E}
.nt.s{font-family:"SS3";font-weight:700;font-size:11px;line-height:12px;padding:0 4px 1px}
.cn{display:inline-flex;align-items:center;gap:3px;position:relative;background:#fff;border:2px solid #2A1A6E;border-radius:9px;height:19px;padding:0 6px 0 2px;font-family:"Brico";font-weight:800;font-size:13px;line-height:13px;color:#2A1A6E}
.sdots i.last{background:#FF4D6D}
"""


# ------------------------------------------------------------------ small parts
def uid():
    _n[0] += 1
    return f"u{_n[0]}"


def hstate(h):
    return "blaze" if h >= 110 else "hot" if h >= 60 else "warm" if h >= 25 else "cold"


def otx(t, size, fill="#fff", sw=None, anchor="start", w=None, sh=True, font="Brico", wt=800):
    """Outlined text that reads over any stage: white face, ink edge, hard ink shadow."""
    sw = sw or max(3, size * .2)
    w = w or int(len(t) * size * .6) + 6
    h = int(size * 1.3)
    x = {"start": 2, "middle": w / 2, "end": w - 2}[anchor]
    a = (f'x="{x}" y="{size * 1.02:.1f}" text-anchor="{anchor}" font-family="{font}" font-weight="{wt}" font-size="{size}" '
         f'letter-spacing="{-.3 if font == "Brico" else 0}" stroke-linejoin="round"')
    shadow = f'<text {a} transform="translate(1.5 2.5)" fill="{INK}" stroke="{INK}" stroke-width="{sw}">{t}</text>' if sh else ""
    return svg(w, h, f"0 0 {w} {h}", shadow + f'<text {a} fill="{fill}" stroke="{INK}" stroke-width="{sw}" paint-order="stroke">{t}</text>')


def dmg(v, size=40, anchor="start"):
    w = int(len(str(v)) * size * .6 + size * .52) + 6
    return otx(f'{v}<tspan font-size="{size * .5:.0f}" dx="1">%</tspan>', size, w=w, sw=size * .2, anchor=anchor)


def flame_mark(st, cx, base, pop=False):
    """The Heat state as a flame of four sizes. Its foot stays put; only its size and colour change."""
    s = {"cold": .12, "warm": .165, "hot": .21, "blaze": .26}[st]
    col = HEATC[st] if st != "cold" else "#8E88B8"
    o = ""
    if pop:
        o += f'<path transform="translate({cx} {base - 46 * s:.1f}) scale({s * 2.4:.2f})" d="{BURST}" fill="{SUN}" stroke="{INK}" stroke-width="1.6" stroke-linejoin="round"/>'
    o += (f'<g transform="translate({cx} {base - 50 * s:.1f}) scale({s})"><path d="{FLAME}" fill="#fff" stroke="#fff" stroke-width="{5.4 / s:.0f}" stroke-linejoin="round"/>'
          f'<path d="{FLAME}" fill="{col}" stroke="{INK}" stroke-width="{2.4 / s:.0f}" stroke-linejoin="round"/>')
    if st in ("hot", "blaze"):
        o += f'<path d="{FLAME_IN}" fill="{"#fff" if st == "blaze" else "#FFD84A"}" transform="translate(0 6) scale(.9)"/>'
    return o + "</g>"


def coin(size=14):
    return svg(size, size, "-8 -8 16 16", f'<circle r="6.6" fill="{SUN}" stroke="{INK}" stroke-width="2"/><circle r="3.4" fill="none" stroke="{INK}" stroke-width="1.5"/>')


def coin_g(x, y, s=1.0):
    return (f'<g transform="translate({x:.1f} {y:.1f}) scale({s})"><circle r="6.2" fill="#fff"/><circle r="5" fill="{SUN}" stroke="{INK}" stroke-width="1.8"/>'
            f'<circle r="2.4" fill="none" stroke="{INK}" stroke-width="1.2"/></g>')


def spark_g(x, y, s=1.0, col=SUN):
    return f'<path transform="translate({x:.1f} {y:.1f}) scale({s})" d="{SPARK}" fill="{col}" stroke="{INK}" stroke-width="{1.5 / s:.1f}" stroke-linejoin="round"/>'


def dpad(d, size=14, lit=False):
    """A D-pad with one arm inked: the button that does this."""
    arm = {"right": "M2.5,-2.5H7V2.5H2.5Z", "down": "M-2.5,2.5H2.5V7H-2.5Z"}[d]
    cross = "M-2.5,-7H2.5V-2.5H7V2.5H2.5V7H-2.5V2.5H-7V-2.5H-2.5Z"
    return svg(size, size, "-9 -9 18 18", f'<path d="{cross}" fill="#fff" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>'
               f'<path d="{arm}" fill="{CORAL if lit else INK}"/>')


# ------------------------------------------------------------------ the Heat meter, two ways
def m1(heat, w=150, cap=150, gain=0, loss=0, cross=None, full=False, cash=False):
    """M1, the bar. Three marks, fill coloured by state, a flame at its foot that grows with the state."""
    st = hstate(heat)
    col = HEATC[st]
    bx, by, bh = 22, 6, 11
    bw = w * cap / 150
    X = lambda v: bx + w * min(v, cap) / 150
    c = uid()
    o = (f'<rect x="{bx - 4.5}" y="{by - 4.5}" width="{bw + 9}" height="{bh + 9}" rx="10" fill="{SUN if full else "#fff"}"/>'
         f'<rect x="{bx - 2.5}" y="{by - 2.5}" width="{bw + 5}" height="{bh + 5}" rx="8" fill="{INK}"/>'
         f'<clipPath id="{c}"><rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="5.5"/></clipPath>'
         f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="5.5" fill="{TRACK}"/><g clip-path="url(#{c})">')
    keep = heat / 2 if cash else heat
    o += f'<rect x="{bx}" y="{by}" width="{X(keep) - bx:.1f}" height="{bh}" fill="{col}"/>'
    if st == "blaze":
        o += f'<rect x="{bx}" y="{by + 2.5}" width="{X(keep) - bx:.1f}" height="2.6" fill="#fff" opacity=".9"/>'
    if gain:
        o += f'<rect x="{X(heat - gain):.1f}" y="{by}" width="{X(heat) - X(heat - gain):.1f}" height="{bh}" fill="#fff"/>'
    if cash:
        o += f'<rect x="{X(keep):.1f}" y="{by}" width="{X(heat) - X(keep):.1f}" height="{bh}" fill="{col}" opacity=".38"/>'
    if loss:
        o += (f'<rect x="{X(heat) + 1:.1f}" y="{by + 1.5}" width="{X(heat + loss) - X(heat) - 2:.1f}" height="{bh - 3}" rx="2" fill="{HEATC[hstate(heat + loss)]}" fill-opacity=".3" stroke="#fff" '
              f'stroke-width="1.5" stroke-dasharray="3 2.4"/>')
    o += "</g>"
    for t in MARKS:
        x = X(t)
        o += (f'<path d="M{x:.1f},{by - 6.5}V{by - 1}" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>'
              f'<path d="M{x:.1f},{by}V{by + bh}" stroke="{INK if keep >= t or (cash and heat >= t) else "#fff"}" stroke-width="2" opacity="{1 if keep >= t else .75}"/>')
    if loss:
        lc = HEATC[hstate(heat + loss)]
        for i, (dx, dy, r) in enumerate(((.2, 8, 20), (.55, 11, -25), (.9, 7, 40))):
            x = X(heat) + (X(heat + loss) - X(heat)) * dx
            o += f'<rect x="{x - 3.5:.1f}" y="{by + bh + dy - 5}" width="8" height="7" rx="1.5" fill="{lc}" stroke="#fff" stroke-width="1.3" transform="rotate({r} {x:.1f} {by + bh + dy})"/>'
    if cross:
        o += f'<path transform="translate({X(cross):.1f} {by + bh / 2}) scale(.42)" d="{BURST}" fill="{SUN}" stroke="{INK}" stroke-width="3.6" stroke-linejoin="round"/>'
    if full:
        e = bx + bw
        o += spark_g(e + 12, by - 4, 1.3) + spark_g(e + 22, by + 9, 1.7) + spark_g(e + 11, by + 19, 1.0)
    if cash:
        e, my = bx + bw + 4, by + bh / 2
        o += (coin_g(e + 7, my - 3, .8) + coin_g(e + 16, my - 9, .95) + coin_g(e + 26, my - 14, 1.1)
              + f'<circle cx="{e + 37}" cy="{my - 19}" r="4.6" fill="{SUN}" stroke="{INK}" stroke-width="2"/><circle cx="{e + 37}" cy="{my - 19}" r="6.4" fill="none" stroke="#fff" stroke-width="1.4"/>')
    o += flame_mark(st, 9.5, by + bh + 4, pop=bool(cross) or cash)
    return svg(f"{bx + bw + 6:.0f}", 24, f"0 0 {bx + bw + 6:.0f} 24", o)


def m2(d, heat, cap=150, gain=0, loss=0, cross=None, full=False, cash=False):
    """M2, the ring. The damage percent sits on a round sticker whose rim is the meter."""
    st = hstate(heat)
    col = HEATC[st]
    R, cx, cy = 28, 42, 38
    C = 2 * math.pi * R
    L = C * .75
    seg = lambda a, b, colr, extra="": (f'<circle r="{R}" fill="none" stroke="{colr}" stroke-width="8" '
                                        f'stroke-dasharray="0 {L * a / cap:.2f} {max(L * (b - a) / cap, 0):.2f} {C:.1f}" {extra}/>')
    pt = lambda v, r: (r * math.cos(math.radians(135 + 270 * v / cap)), r * math.sin(math.radians(135 + 270 * v / cap)))
    keep = heat / 2 if cash else heat
    o = (f'<circle cx="{cx + 2}" cy="{cy + 3}" r="35" fill="{INK}"/><circle cx="{cx}" cy="{cy}" r="35" fill="{SUN if full else "#fff"}" stroke="{INK}" stroke-width="2.6"/>'
         f'<g transform="translate({cx} {cy})"><g transform="rotate(135)">' + seg(0, cap, INK, 'stroke-width="12" stroke-linecap="round"') + seg(0, cap, TRACK)
         + seg(0, keep, col))
    if st == "blaze":
        o += f'<circle r="{R + 1.8}" fill="none" stroke="#fff" stroke-width="2" opacity=".9" stroke-dasharray="0 0 {L * keep / cap * (R + 1.8) / R:.2f} {C * 2:.1f}"/>'
    if gain:
        o += seg(heat - gain, heat, "#fff")
    if cash:
        o += seg(keep, heat, col, 'opacity=".38"')
    if loss:
        o += seg(heat, heat + loss, HEATC[hstate(heat + loss)], 'opacity=".4"')
    o += "</g>"
    for t in MARKS:
        (x0, y0), (x1, y1) = pt(t, R - 4), pt(t, R + 7)
        on = keep >= t
        o += (f'<path d="M{x0:.1f},{y0:.1f}L{x1:.1f},{y1:.1f}" stroke="{INK if on else "#fff"}" stroke-width="2" stroke-linecap="butt"/>')
    if loss:
        lc = HEATC[hstate(heat + loss)]
        for i, (v, r, rot) in enumerate(((.15, 42, 20), (.5, 46, -30), (.9, 42, 50))):
            x, y = pt(heat + loss * v, r)
            o += f'<rect x="{x - 3.5:.1f}" y="{y - 3:.1f}" width="7" height="6" rx="1.5" fill="{lc}" stroke="{INK}" stroke-width="1.5" transform="rotate({rot} {x:.1f} {y:.1f})"/>'
    if cross:
        x, y = pt(cross, R)
        o += f'<path transform="translate({x:.1f} {y:.1f}) scale(.42)" d="{BURST}" fill="{SUN}" stroke="{INK}" stroke-width="3.6" stroke-linejoin="round"/>'
    if full:
        o += spark_g(44, -14, 1.3) + spark_g(52, 2, 1.7) + spark_g(44, 18, 1.0)
    if cash:
        x, y = pt((keep + heat) / 2, R + 6)
        o += (f'<path d="M{x:.1f},{y:.1f} C{x + 20:.1f},{y - 4:.1f} {x + 44:.1f},{y + 6:.1f} {x + 62:.1f},{y + 30:.1f}" fill="none" stroke="#fff" stroke-width="2" stroke-dasharray="2 4" stroke-linecap="round"/>'
              + coin_g(x + 16, y + 0, .9) + coin_g(x + 36, y + 7, 1.05) + coin_g(x + 52, y + 19, 1.2)
              + f'<circle cx="{x + 64:.1f}" cy="{y + 34:.1f}" r="5" fill="{SUN}" stroke="{INK}" stroke-width="2"/>')
    fs = 21 if d < 100 else 17
    o += (f'<text y="{fs * .36:.1f}" text-anchor="middle" font-family="Brico" font-weight="800" font-size="{fs}" letter-spacing="-.6" fill="{INK}">{d}'
          f'<tspan font-size="10" dx=".5">%</tspan></text></g>')
    o += flame_mark(st, cx, cy + 41, pop=bool(cross) or cash)
    return svg(84, 84, "0 0 84 84", o)


# ------------------------------------------------------------------ drive row, active drive, bench
def hchip(d, lvl, chg, fired=False, spark=False, pips=True):
    """A drive in the HUD row: the D2 badge, a charge ring around it, level pips under it."""
    f, rar = DR[d][0], DR[d][1]
    c = 2 * math.pi * 11.6
    b = ""
    if fired:
        b += f'<path d="{BURST}" transform="scale(.78)" fill="{SUN}" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round"/>'
    b += (f'<circle r="14.6" fill="#fff"/><circle r="13.4" fill="{INK}"/><circle r="11.6" fill="none" stroke="#5A4C99" stroke-width="2.6"/>'
          f'<circle r="11.6" fill="none" stroke="{SUN}" stroke-width="2.9" stroke-dasharray="{c * (1 if fired else chg):.1f} {c:.1f}" transform="rotate(-90)"/>'
          f'<g transform="translate(-9.5 -9.5)">{pog(f, 19, 0, sq=False)}</g>')
    if spark:
        b += spark_g(11, -11, 1.5) + spark_g(-13, -9, .8)
    p = ""
    if pips:
        p = '<div class="pips">' + "".join(f'<i class="{"y" if i < lvl else ""}"></i>' for i in range(3)) + "</div>"
    return f'<div class="hc">{svg(30, 30, "-15 -15 30 30", b)}{p}</div>'


def hrow(P, pips=True):
    chips = "".join(hchip(d, l, c, fired=i in P.get("fired", ()), spark=P.get("spark") == i, pips=pips) for i, (d, l, c) in enumerate(P["row"]))
    line = ""
    fr = sorted(P.get("fired", ()))
    if len(fr) > 1:
        x0, x1 = fr[0] * 30 + 15, fr[-1] * 30 + 15
        line = at(0, 0, svg(150, 30, "0 0 150 30", f'<path d="M{x0},15H{x1}" stroke="{INK}" stroke-width="9" stroke-linecap="round"/><path d="M{x0},15H{x1}" stroke="{SUN}" stroke-width="5" stroke-linecap="round"/>'))
    return f'<div class="hrow">{line}{chips}</div>'


def active(P):
    f, have, need = P["active"]
    ready = have >= need
    b = ""
    if ready:
        b += f'<path d="{BURST}" transform="scale(.8)" fill="{SUN}" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round"/>'
    b += f'<rect x="-13.5" y="-13.5" width="27" height="27" rx="8" fill="#fff"/><g transform="translate(-11.5 -11.5)">{pog(f, 23, 0, sq=True)}</g>'
    pp = '<div class="pips a">' + "".join(f'<i class="{"y" if i < have else ""}"></i>' for i in range(need)) + "</div>"
    return f'<div class="hc">{svg(30, 30, "-15 -15 30 30", b)}<div class="dp">{dpad("right", 15, ready)}</div>{pp}</div>'


def bench(B, cd=None):
    """The benched fighter: head, name, percent, their row, and the tag button. On cooldown it refills left to right."""
    name, kind, d, row = B
    mi = "".join(pog(DR[n][0], 15, 0, sq=False) for n in row)
    bg = "" if cd is None else f'background:linear-gradient(90deg,#fff 0 {cd * 100:.0f}%,#B9B4CE {cd * 100:.0f}% 100%)'
    return (f'<div class="bn2" style="{bg}">{sil(kind, 10)}<span class="n">{name}</span><span class="d">{d}%</span><span class="mi">{mi}</span>'
            f'<span style="opacity:{.35 if cd is not None else 1}">{dpad("down", 14)}</span></div>')


# ------------------------------------------------------------------ party things and foes
def stockdots(left, total):
    last = left == 1
    return '<div class="sdots">' + "".join(f'<i class="{"off" if i >= left else ("last" if last else "")}"></i>' for i in range(total)) + "</div>"


def keymini(name="Plague Bearer"):
    w = int(len(name) * 6.3) + 24
    pts = f"M4,3 H{w - 4} L{w - 9},20 H9Z"
    return svg(w, 23, f"0 0 {w} 23", f'<path d="{pts}" fill="#fff" stroke="#fff" stroke-width="5" stroke-linejoin="round"/><path d="{pts}" fill="{INK}" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>'
               f'<text x="{w / 2}" y="15.5" text-anchor="middle" font-family="Brico" font-weight="800" font-size="11.5" fill="{SUN}">{name}</text>')


def coins(n, plus=False):
    b = at(-13, -12, svg(20, 20, "-27 -27 54 54", f'<path d="{BURST}" fill="{SUN}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'), "z-index:-1") if plus else ""
    return f'<div class="cn">{b}{coin(15)}{n}</div>'


def party(x, y, pool, n, plus=False, anchor="middle"):
    left, total = pool
    w = total * 18 - 4
    kw = int(len("Plague Bearer") * 6.3) + 24
    burst_ = ""
    if left == 1:
        burst_ = at(-10, -8, svg(30, 30, "-27 -27 54 54", f'<path d="{BURST}" fill="{SUN}" stroke="{INK}" stroke-width="3.4" stroke-linejoin="round"/>'), "z-index:-1")
    if anchor == "middle":
        a = at(-(w + 46) / 2, 0, burst_ + stockdots(left, total)) + at(-(w + 46) / 2 + w + 9, -2, coins(n, plus)) + at(-kw / 2, 24, keymini())
        return f'<div class="hp" style="left:{x}px;top:{y}px;width:0;height:48px">{a}</div>'
    a = at(0, 0, burst_ + stockdots(left, total)) + at(w + 10, -2, coins(n, plus)) + at(-2, 23, keymini())
    return f'<div class="hp" style="left:{x}px;top:{y}px;width:{w + 50}px;height:48px">{a}</div>'


def foe_w(F):
    k = F["k"]
    if k == "elite":
        return 62 + len(str(F["dmg"])) * 13 + len(F.get("dr", ())) * 19
    return 38 + len(str(F["dmg"])) * 10


def foe(F, x, y):
    """A foe's plate: dark, so it is never one of ours. Elites carry their drives and a name."""
    k = F["k"]
    if k == "elite":
        dv = '<span class="dv">' + "".join(pog(DR[n][0], 18, 1, sq=False) for n in F.get("dr", ())) + "</span>"
        wd = ""
        if F.get("burn"):
            wd = ('<span class="wd">' + svg(9, 11, "-36 -48 72 102", f'<path d="{FLAME}" fill="#FF7A1F" stroke="{INK}" stroke-width="9" stroke-linejoin="round"/>')
                  + "".join(f'<i class="{"" if i < F["burn"] else "o"}"></i>' for i in range(3)) + "</span>")
        return (f'<div class="fp hp" style="left:{x}px;top:{y}px;height:38px;width:{foe_w(F)}px">{sil(F.get("kind", 4), 15, "#8E88B8")}'
                f'<div><div class="n">Elite</div><div class="d" style="font-size:21px;line-height:21px">{F["dmg"]}%</div></div>{dv}{wd}</div>')
    return (f'<div class="fp hp" style="left:{x}px;top:{y + 5}px;height:28px;width:{foe_w(F)}px">{sil(F.get("kind", 2), 11, "#8E88B8")}'
            f'<div class="d" style="font-size:16px;line-height:17px">{F["dmg"]}%</div></div>')


def foes_row(fs, right, y, gap=8):
    out, x = "", right
    for F in reversed(fs):
        x -= foe_w(F)
        out = foe(F, x, y) + out
        x -= gap
    return out


def bossbar(W, hp, done=1, brk=False):
    """Boss HP: one long bar across the top, cut in quarters. Each quarter mark is a break."""
    w, x0, y0, h = 340, (W - 340) / 2 + 14, 15, 15
    c = uid()
    o = (f'<rect x="{x0 - 4.5}" y="{y0 - 4.5}" width="{w + 9}" height="{h + 9}" rx="11" fill="#fff"/><rect x="{x0 - 2.5}" y="{y0 - 2.5}" width="{w + 5}" height="{h + 5}" rx="9" fill="{INK}"/>'
         f'<clipPath id="{c}"><rect x="{x0}" y="{y0}" width="{w}" height="{h}" rx="6.5"/></clipPath><rect x="{x0}" y="{y0}" width="{w}" height="{h}" rx="6.5" fill="{TRACK}"/>'
         f'<g clip-path="url(#{c})"><rect x="{x0}" y="{y0}" width="{w * hp:.1f}" height="{h}" fill="#fff"/>')
    if brk:
        o += f'<rect x="{x0 + w * hp:.1f}" y="{y0}" width="{w * .045:.1f}" height="{h}" fill="{SUN}"/>'
    o += "</g>"
    for i in (1, 2, 3):
        x = x0 + w * i / 4
        o += f'<path d="M{x},{y0}V{y0 + h}" stroke="{INK if i / 4 < hp else "#fff"}" stroke-width="2.6"/><path d="M{x},{y0 - 7}V{y0 - 1}" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/>'
        if i > 3 - done and not (brk and abs(i / 4 - hp) < .01):
            o += spark_g(x, y0 + h + 10, 1.5)
    if brk:
        x = x0 + w * (3 - done) / 4 + w * .0
        x = x0 + w * hp
        o += (f'<path transform="translate({x:.1f} {y0 + h / 2}) scale(.62)" d="{BURST}" fill="{SUN}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
              + "".join(f'<rect x="{x + dx}" y="{y0 + dy}" width="8" height="6" rx="1.5" fill="#fff" stroke="{INK}" stroke-width="1.6" transform="rotate({r} {x + dx} {y0 + dy})"/>' for dx, dy, r in ((14, 24, 25), (26, 30, -20), (6, 34, 50))))
    head = at(x0 - 40, 4, f'<div style="width:34px;height:34px;border-radius:50%;background:{INK};border:2.5px solid #fff;box-shadow:0 0 0 2px {INK};display:flex;align-items:center;justify-content:center">{sil(5, 17, "#8E88B8")}</div>')
    name = at(x0 + 2, 34, '<span class="nt">Boss</span>')
    return f'<div class="hpx" style="position:absolute;left:0;top:0;width:0;height:0">{at(0, 0, svg(W, 60, f"0 0 {W} 60", o))}{head}{name}</div>'


# ------------------------------------------------------------------ the placeholder fight
THEME = {
    "dark": dict(sky="#1E2A4A", far="#26355F", body="#3B476F", top="#7483B5"),
    "bright": dict(sky="#CDEBF7", far="#E7F6FC", body="#DCCFA9", top="#FFFDF2"),
}
FLOOR = 306


def scene(W, theme):
    t = THEME[theme]
    cx = W / 2
    return f'<div class="sc">' + svg(W, 480, f"0 0 {W} 480",
        f'<rect width="{W}" height="480" fill="{t["sky"]}"/><path d="M0,400 C{cx - 220},250 {cx - 60},330 {cx},300 C{cx + 120},240 {cx + 260},330 {W},260 V480 H0Z" fill="{t["far"]}"/>'
        f'<path d="M{cx - 232},{FLOOR + 5} H{cx + 232} L{cx + 196},{FLOOR + 40} H{cx - 196}Z" fill="{t["body"]}"/><rect x="{cx - 236}" y="{FLOOR}" width="472" height="9" rx="3" fill="{t["top"]}"/>'
        f'<rect x="{cx - 176}" y="232" width="96" height="7" rx="3" fill="{t["top"]}"/><rect x="{cx + 80}" y="232" width="96" height="7" rx="3" fill="{t["top"]}"/>') + "</div>"


def orbit_pts(x, fy, w, n):
    cy = fy - w * .75
    return [(x + w * .95 * math.cos(math.radians(a)), cy + w * .42 * math.sin(math.radians(a))) for a in (205, 335, 90, 150, 30)[:n]]


def actor(x, fy, kind, team, w=40, orb=(), ready=(), heat=None, foe_orb=False):
    """A fighter on the stage: a silhouette, a player pointer, the heat it holds, and its orbiting drives."""
    o = ""
    if heat and heat != "cold":
        s = {"warm": .34, "hot": .5, "blaze": .68}[heat]
        o += at(x - 36 * s, fy - 96 * s, svg(72 * s, 100 * s, "-36 -46 72 100", f'<path d="{FLAME}" fill="{HEATC[heat]}" opacity=".9"/>'))
    fill = {"p1": "#C9CCD8", "p2": "#C9CCD8"}.get(team, "#6B6F8C")
    pts = orbit_pts(x, fy, w, len(orb))
    back = "".join(at(px - 7.5, py - 7.5, pog(f, 15, 0, sq=False)) for (px, py), f in list(zip(pts, orb))[:2] if True)
    o += back + at(x - w / 2, fy - w * 1.4, sil(kind, w, fill))
    for i, ((px, py), f) in enumerate(zip(pts, orb)):
        if i < 2 and i not in ready:
            continue
        if i in ready:
            o += at(px - 13, py - 13, svg(26, 26, "-13 -13 26 26", f'<circle r="11.4" fill="{SUN}" stroke="{INK}" stroke-width="1.8"/><g transform="translate(-8.5 -8.5)">{pog(f, 17, 0, sq=False)}</g>'))
        else:
            o += at(px - 7.5, py - 7.5, pog(f, 15, 0, sq=False))
    if foe_orb:
        for px, py in pts:
            o += at(px - 10, py - 10, svg(20, 20, "-10 -10 20 20", f'<circle r="8.8" fill="none" stroke="{INK}" stroke-width="1.6" stroke-dasharray="2 2"/>'))
    if team in ("p1", "p2"):
        col = CORAL if team == "p1" else LAGOON
        o += at(x - 12, fy - w * 1.4 - 27, f'<span class="pt" style="background:{col};position:static">P{team[1]}</span>' + svg(10, 6, "0 0 10 6", f'<path d="M1,0H9L5,5.5Z" fill="{col}" stroke="{INK}" stroke-width="1.6" stroke-linejoin="round"/>', 'style="margin:-2px 0 0 8px;display:block"'))
    return o


# ------------------------------------------------------------------ player clusters
def h2w(P):
    return 136 + 30 * len(P["row"])


def pc_h2(P, x, y, low=0):
    """A player's corner: percent, the row and the active beside it, Heat under it, the bench under that."""
    col = CORAL if P["p"] == 1 else LAGOON
    o = (at(-2, 10, dmg(P["dmg"], 40)) + f'<span class="pt" style="background:{col};top:-3px">P{P["p"]}</span>' + at(27, -3, f'<span class="nt">{P["name"]}</span>')
         + at(100, 12, hrow(P)) + at(106 + 30 * len(P["row"]), 12, active(P))
         + at(low, 59, m1(P["heat"], w=122, cap=P.get("cap", 150), **P.get("m", {}))) + at(low, 85, bench(P["bench"], P.get("cd"))))
    return f'<div class="hp" style="left:{x}px;top:{y}px;width:{h2w(P)}px;height:108px">{o}</div>'


def pc_h1(P, x, y):
    """Band slots: the fighter in play, then the benched one, as two Smash-style slots."""
    col = CORAL if P["p"] == 1 else LAGOON
    a = (at(-2, 9, dmg(P["dmg"], 36)) + f'<span class="pt" style="background:{col};top:-3px">P{P["p"]}</span>' + at(27, -3, f'<span class="nt">{P["name"]}</span>') + at(98, 10, active(P)) + at(0, 50, m1(P["heat"], w=100, **P.get("m", {}))) + at(2, 74, hrow(P, pips=False)))
    name, kind, d, row = P["bench"]
    mi = "".join(pog(DR[n][0], 16, 0, sq=False) for n in row)
    b = (at(-1, 14, dmg(d, 23)) + at(0, -2, f'<span class="nt s">{name}</span>') + at(48, 21, dpad("down", 14))
         + at(0, 46, f'<div style="display:flex;gap:1px">{mi}</div>'))
    return (f'<div class="hp" style="left:{x}px;top:{y}px;width:130px;height:102px">{a}</div>'
            f'<div class="hp" style="left:{x + 138}px;top:{y + 22}px;width:62px;height:64px">{b}</div>')


# ------------------------------------------------------------------ data
def player(p, **kw):
    base = {
        1: dict(p=1, name="Fighter A", kind=0, dmg=87, heat=78, row=[("Ember", 2, .8), ("Bolt", 1, .45), ("Echo", 1, .2)], active=("bolt", 1, 3),
                bench=("Fighter B", 1, 34, ["Frost", "Shatter", "Metronome"])),
        2: dict(p=2, name="Fighter C", kind=3, dmg=41, heat=38, row=[("Frost", 1, .55), ("Clean Landing", 2, .3), ("Mirror", 1, .7)], active=("wind", 1, 2),
                bench=("Fighter D", 5, 112, ["Tailwind", "Feather Storm", "Ember"])),
    }[p]
    base = dict(base)
    base.update(kw)
    return base


ELITE = dict(k="elite", dmg=62, dr=("Wildfire", "Frost"), burn=2)
MIN = lambda d, kind=2: dict(k="min", dmg=d, kind=kind)


def world_default(cx, P1, P2, fs):
    o = ""
    if P1:
        o += actor(cx - 74, FLOOR, P1["kind"], "p1", orb=[DR[d][0] for d, _, _ in P1["row"]], ready=[i for i, (_, _, c) in enumerate(P1["row"]) if c >= .8], heat=hstate(P1["heat"]))
    if P2:
        o += actor(cx + 128, 232, P2["kind"], "p2", orb=[DR[d][0] for d, _, _ in P2["row"]], heat=hstate(P2["heat"]))
    spots = [(cx + 26, FLOOR), (cx - 168, FLOOR), (cx - 128, 232), (cx + 186, FLOOR)]
    for i, F in enumerate(fs):
        x, fy = spots[i % 4]
        if F["k"] == "elite":
            o += actor(x, fy, 4, "foe", w=46, orb=[DR[d][0] for d in F["dr"]], foe_orb=True)
        else:
            o += actor(x, fy, F.get("kind", 2), "foe", w=30)
    return o


def screen(lay="h2", theme="dark", wide=False, P1=None, P2=None, fs=(), boss=None, pool=(4, 5), n=23, world=None, fx="", plus=False):
    W = 853 if wide else 640
    cx = W / 2
    o = scene(W, theme) + (world if world is not None else world_default(cx, P1, P2, fs)) + fx
    if lay == "h2":
        if P1:
            o += pc_h2(P1, 14, 360)
        if P2:
            o += pc_h2(P2, W - 14 - h2w(P2), 360, low=h2w(P2) - 226)
        o += party(cx, 420, pool, n, plus)
        o += foes_row(list(fs), W - 16, 14)
    else:
        x = 12
        for P in (P1, P2):
            if P:
                o += pc_h1(P, x, 364)
                x += 212
        o += foes_row(list(fs), W - 14, 412, gap=7)
        o += party(16, 16, pool, n, plus, anchor="start")
    if boss:
        o += bossbar(W, *boss)
    return f'<div class="fz{" wide" if wide else ""}" data-w="{W}">{o}</div>'


# ------------------------------------------------------------------ moments drawn in the world
def chain_fx(cx):
    """Ember fires, its damage fills Bolt, Bolt fills Echo: the line runs orbiter to orbiter, then out to the foe."""
    pts = orbit_pts(cx - 74, FLOOR, 40, 3)
    tx, ty = cx + 26, FLOOR - 36
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in (pts[0], pts[2], pts[1])) + f" L{tx - 20},{ty}"
    o = (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
         f'<path d="{d}" fill="none" stroke="{SUN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    for (dx, dy, s, f) in ((0, 0, .62, "fire"), (16, -16, .46, "bolt"), (14, 12, .36, "util")):
        o += f'<path transform="translate({tx + dx} {ty + dy}) scale({s})" d="{BURST}" fill="{s4.FAM[f][1]}" stroke="{INK}" stroke-width="{2.4 / s:.1f}" stroke-linejoin="round"/>'
    return at(0, 0, svg(1, 1, "0 0 1 1", o))


def spark_fx(x, fy):
    o = spark_g(x - 22, fy - 3, 2.0) + spark_g(x + 20, fy - 6, 1.3) + spark_g(x + 30, fy + 2, .8)
    return at(0, 0, svg(1, 1, "0 0 1 1", o))


def cash_fx(cx, x, fy, W):
    """A cash-out seen in the world: a flare where the foe was, coins on their way to the counter."""
    o = f'<path transform="translate({x} {fy - 26}) scale(1.0)" d="{BURST}" fill="{SUN}" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round"/>'
    for i, t in enumerate((.35, .6, .82)):
        px = x + 44 * math.sin(t * 3.1) + (cx + 46 - x) * t
        py = fy - 26 + (424 - fy + 26) * t
        o += coin_g(px, py, 1.3)
    return at(0, 0, svg(1, 1, "0 0 1 1", o))


# ------------------------------------------------------------------ sheet parts
def shot(inner, zoom, label=None, cap=None, wide=False):
    W = 853 if wide else 640
    lab = f'<div class="tag">{label}</div>' if label else ""
    c = f'<p class="cap" style="max-width:{W * zoom:.0f}px">{cap}</p>' if cap else ""
    return f'<div>{lab}<div style="width:{W * zoom:.0f}px;height:{480 * zoom:.0f}px;border-radius:8px;overflow:hidden"><div class="g" style="zoom:{zoom}">{inner}</div></div>{c}</div>'


def mtile(label, inner, cap):
    return f'<div class="mt"><div class="tag">{label}</div><div class="mtb"><div class="g">{inner}</div></div><p class="cap">{cap}</p></div>'


MSTATES = [
    ("Cold", dict(heat=12), 23, "Under 25. No flame."),
    ("Warm", dict(heat=38), 41, "25 and up. Fires hit x1.25."),
    ("Hot", dict(heat=78), 87, "60 and up. Fires hit x1.5."),
    ("Blazing", dict(heat=126), 96, "110 and up. Fires hit x2."),
    ("Gaining", dict(heat=52, gain=14), 41, "The new piece lands white, sized by the hit."),
    ("Losing", dict(heat=64, loss=20), 107, "The lost piece is seen breaking off."),
    ("Crossing into Hot", dict(heat=63, gain=9, cross=60), 58, "The mark pops and the flame steps up."),
    ("At the cap", dict(heat=150, full=True), 72, "Sunny rim. Extra damage sparks off the end."),
    ("KO cash-out", dict(heat=96, cash=True), 64, "Half leaves as coins and an active pip."),
]


def meter_tiles(which):
    out = []
    for name, kw, d, cap in MSTATES:
        if which == 1:
            inner = at(8, 2, dmg(d, 36)) + at(4, 52, m1(w=122, **kw))
        else:
            inner = at(52, 1, m2(d, **kw))
        out.append(mtile(name, inner, cap))
    return '<div class="mt3">' + "".join(out) + "</div>"


def main_screen(lay, **kw):
    return screen(lay, P1=player(1), P2=player(2), fs=[MIN(18), ELITE], **kw)


def state_screens():
    cx = 320
    S = []
    S.append(("Solo duel", screen(P1=player(1, heat=30, dmg=22), fs=[dict(k="min", dmg=54, kind=1)], pool=(4, 4), n=6),
              "One player, one foe, four stocks. The right corner stays empty."))
    S.append(("A pack of four", screen(P1=player(1), P2=player(2), fs=[MIN(71), MIN(9, 0), MIN(33, 3), MIN(48, 1)]),
              "Four small plates along the top. They never crowd the players."))
    P1 = player(1, heat=112, m=dict(cash=True))
    S.append(("Boss, at a break", screen(P1=P1, P2=player(2), boss=(.5, 2, True), n=31, plus=True,
              world=actor(cx - 74, FLOOR, 0, "p1", orb=["fire", "bolt", "util"], heat="blaze") + actor(cx + 128, 232, 3, "p2", orb=["frost", "tech", "util"], heat="warm")
              + actor(cx + 46, FLOOR, 5, "foe", w=84), fx=cash_fx(cx, cx + 46, FLOOR - 84, 640)),
              "HP is one bar cut in quarters. Each quarter is a break, and a break is a cash-out: coins fly, the meter keeps half."))
    P1 = player(1, row=[("Ember", 2, 1), ("Bolt", 1, 1), ("Echo", 1, 1)], fired=(0, 1, 2), m=dict(gain=10))
    S.append(("A drive fires, with a chain", screen(P1=P1, P2=player(2), fs=[MIN(18), dict(ELITE, dmg=79)], fx=chain_fx(cx)),
              "The line runs drive to drive around the fighter, then out to the foe. In the row the same three light up, joined."))
    P2 = player(2, spark=1, row=[("Frost", 1, .55), ("Clean Landing", 2, .62), ("Mirror", 1, .7)])
    S.append(("Technique spark", screen(P1=player(1), P2=P2, fs=[MIN(18), ELITE], fx=spark_fx(cx + 128, 232)),
              "P2 lands an L-cancel: a spark at the feet, and one on the drive it fed."))
    S.append(("Active drive ready", screen(P1=player(1, active=("bolt", 3, 3)), P2=player(2), fs=[MIN(18), ELITE]),
              "P1's active is full: sunny burst, D-pad right turns coral. P2's has one pip of two."))
    P1 = player(1, name="Fighter B", kind=1, dmg=34, row=[("Frost", 1, .1), ("Shatter", 1, .35), ("Metronome", 2, .6)],
                bench=("Fighter A", 0, 87, ["Ember", "Bolt", "Echo"]), cd=.4)
    S.append(("Just tagged", screen(P1=P1, P2=player(2), fs=[MIN(18), ELITE]),
              "P1 swapped to Fighter B. Fighter A's sticker is grey and refills over five seconds. Heat did not move."))
    S.append(("Last stock", screen(P1=player(1, dmg=131), P2=player(2, dmg=96), fs=[MIN(18), ELITE], pool=(1, 5)),
              "One dot left, coral, on a burst. Nothing else changes."))
    S.append(("Over a bright stage", main_screen("h2", theme="bright"),
              "Same HUD on a pale stage: the ink edges carry it."))
    P1 = player(1, m=dict(cash=True), heat=96, active=("bolt", 2, 3))
    kx = cx - 190
    fx = at(0, 0, svg(1, 1, "0 0 1 1",
            f'<path transform="translate({kx} {FLOOR - 40}) scale(1.25)" d="{BURST}" fill="{SUN}" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>'
            + "".join(coin_g(kx + (cx + 46 - kx) * t, FLOOR - 40 + 150 * t * t + 14 * t, 1.25) for t in (.3, .55, .8))
            + f'<path transform="translate({cx + 26} {FLOOR - 40}) scale(.6)" d="{BURST}" fill="{HEATC["hot"]}" stroke="{INK}" stroke-width="3.6" stroke-linejoin="round"/>'))
    S.insert(3, ("A KO cashes out", screen(P1=P1, P2=player(2), fs=[dict(ELITE, dmg=71)], n=32, plus=True, fx=fx),
              "P1 KOs the minion while Hot: a flare where it fell, coins to the counter, a pip to the active, a flare on the elite. The bar keeps half."))
    five = lambda p, more: player(p, row=player(p)["row"] + more)
    S.append(("Five drives each", screen(P1=five(1, [("Tailwind", 1, .5), ("Shatter", 3, .9)]), P2=five(2, [("Ember", 1, .15), ("Metronome", 2, .4)]), fs=[MIN(18), ELITE]),
              "The rows grow toward the middle and still clear each other at 4:3. P2's bar and bench stay where they were, so the shared stickers keep their place."))
    S.append(("A raised cap", screen(P1=player(1, heat=170, cap=250), P2=player(2, heat=38, cap=200), fs=[MIN(18), ELITE]),
              "P1's cap is 250 and P2's is 200: the bar is longer, the three marks stay where they were. 250 is the longest it gets."))
    return "".join(shot(s, .759, n, c) for n, s, c in S)


def html():
    holo = "".join(f'<stop offset="{i / 5:.2f}" stop-color="{c}"/>' for i, c in enumerate(s4.HOLO.split(",")))
    rec = main_screen("h2")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Envoy UI step 5</title><style>{CSS}</style></head>
<body><svg width="0" height="0" style="position:absolute"><defs><linearGradient id="holo" x1="0" y1="0" x2="1" y2="1">{holo}</linearGradient></defs></svg><div id="c">
<div class="top"><h1>The fight HUD</h1>
<p>Step 5 of the UI design. Two choices: where things sit (H1 or H2) and how Heat is drawn (M1 or M2). The map, the shop, results and pause are not designed yet.</p></div>
<div class="key"><span><i style="background:#fff;box-shadow:inset 0 0 0 2.5px {INK}"></i>White with an ink edge: ours. Coral is P1, lagoon is P2.</span>
<span><i style="background:{INK};box-shadow:inset 0 0 0 2.5px #fff"></i>Ink with a white edge: a foe, or the keystone wedge.</span>
<span><i style="background:{SUN};box-shadow:inset 0 0 0 2.5px {INK}"></i>Sunny: something is ready or just fired.</span>
<span><i style="background:linear-gradient(90deg,{HEATC["cold"]} 0 25%,{HEATC["warm"]} 25% 50%,{HEATC["hot"]} 50% 75%,{HEATC["blaze"]} 75%);box-shadow:inset 0 0 0 2.5px {INK}"></i>Heat: Cold, Warm, Hot, Blazing.</span></div>

<div class="sec"><h2>Where things sit</h2>
<p class="lede">The same fight in both: two players, an elite carrying two drives, one minion. P1 is Hot, P2 is Warm. Both are drawn with the bar meter so only the layout differs.</p>
<div class="two">
<div class="lay"><div class="hd"><b>H1</b><span>One band</span></div>{shot(main_screen("h1"), 1.15)}
<p class="note">Everyone is a slot along the bottom, like a Smash HUD: P1's fighter, their benched fighter, P2's pair, then the foes. Stocks, keystone and coins sit top left.</p>
<p class="trade">Familiar, and the top stays empty. But the band is full at two foes: four foes or a boss bar have to go somewhere else, and the row has to drop its level pips to fit.</p></div>
<div class="lay"><div class="hd"><b>H2</b><span>Our corners, their top</span></div>{shot(main_screen("h2"), 1.15)}
<p class="note">Each player owns a bottom corner. What the party shares (stocks, keystone, coins) sits between them. Foes line up along the top, where a boss bar also goes.</p>
<p class="trade">One rule to learn: bottom is us, top is them. It holds from a solo duel to four foes to a boss without anything moving.</p></div>
</div>
<div class="where"><div><h3>On the fighter</h3><p>The <b>moments</b>: a drive glowing when it is ready, the fire, the chain line running drive to drive, the technique spark, and a flame that grows with the Heat state. Eyes are already there.</p></div>
<div><h3>In the HUD row</h3><p>The <b>facts</b> the orbit cannot hold still: slot order left to right, level pips, and exact charge as a ring. A badge only flashes sunny on the frame it fires.</p></div>
<div><h3>No numbers but percent</h3><p>Heat has no digits, as the design note rules: four flame sizes and three marks say it. The only other number is coins, and it changes only at a cash-out.</p></div></div></div>

<div class="sec"><h2>The Heat meter</h2>
<p class="lede">One per player, next to their percent. Heat rises 1 for each 1% dealt and falls 1 for each 1% taken; it never drains on its own. Both candidates use the same colours, the same three marks and the same flame.</p>
<div class="two">
<div class="lay"><div class="hd"><b>M1</b><span>The bar</span></div>{meter_tiles(1)}
<p class="trade">Percent stays big and alone. Gains and losses read as length, and a raised cap is simply a longer bar with the marks where they were.</p></div>
<div class="lay"><div class="hd"><b>M2</b><span>The ring</span></div>{meter_tiles(2)}
<p class="trade">One place to look, and compact. But the percent shrinks to fit inside, a lost piece is harder to see on a curve, and a raised cap has to squeeze the marks round.</p></div>
</div></div>

<div class="sec"><h2>H2 with M1, in twelve situations</h2>
<p class="lede">The chosen pair. Nothing changes position between these; only what is lit.</p>
<div class="states">{state_screens()}</div></div>

<div class="sec"><h2>Chosen: H2 and M1 at actual size</h2>
<p class="lede">640 by 480, the size the game renders before upscaling, and the same screen at 16:9. Smallest text is 11 px (the benched fighter's name, the word Elite); percent is 40 px.</p>
<div class="act5"><div><div class="g">{rec}</div><p class="cap"><b>4:3.</b></p></div>
<div><div class="g">{main_screen("h2", wide=True)}</div><p class="cap"><b>16:9.</b> The corners follow the screen edges, the shared stickers stay centred, and the foes stay top right. Nothing is stretched or resized, so the middle only gets clearer.</p></div></div></div>

<div class="rec" style="grid-template-columns:150px 1fr 1fr"><h2>Chosen</h2>
<p><b>H2, our corners and their top.</b> It is the one layout that does not change shape between a duel, a pack and a boss, and it keeps each player's percent, Heat and drives in one corner they can find without reading.</p>
<p><b>M1, the bar.</b> It leaves the percent as the biggest thing on screen and shows gain, loss and a raised cap the plainest way there is: longer or shorter.</p></div>
<p class="foot">Original vector art. Fonts: Bricolage Grotesque, Source Sans 3 (SIL OFL). The stage and fighters are placeholders with invented names; drive loadouts, percents and coin counts are made up for the mock. Heat thresholds (25, 60, 110, cap 150) and the one-for-one loss follow the design note and the owner's ruling.</p>
</div></body></html>"""


CHECK = """() => {
  const out = [];
  document.querySelectorAll('.fz').forEach((f, i) => {
    const W = +f.dataset.w, fr = f.getBoundingClientRect(), z = fr.width / W;
    const box = e => { let l = 1e9, t = 1e9, r = -1e9, b = -1e9;
      [e, ...e.querySelectorAll('*')].forEach(k => { const q = k.getBoundingClientRect(); if (!q.width || !q.height) return; if (k.tagName === 'svg' && q.width * q.height < 4) return;
        l = Math.min(l, q.left); t = Math.min(t, q.top); r = Math.max(r, q.right); b = Math.max(b, q.bottom); });
      return { l: (l - fr.left) / z, t: (t - fr.top) / z, r: (r - fr.left) / z, b: (b - fr.top) / z }; };
    const hs = [...f.querySelectorAll(':scope > .hp')].map(e => [e, box(e)]);
    hs.forEach(([e, b], a) => {
      if (b.l < 4 || b.t < 2 || b.r > W - 4 || b.b > 476) out.push(`screen ${i}: piece ${a} leaves the frame ${JSON.stringify(b, (k, v) => typeof v === 'number' ? Math.round(v) : v)}`);
      hs.slice(a + 1).forEach(([e2, b2], c) => { if (b.l < b2.r && b2.l < b.r && b.t < b2.b && b2.t < b.b) out.push(`screen ${i}: pieces ${a} and ${a + 1 + c} overlap`); });
    });
  });
  return out; }"""


def main():
    src = HERE / "step5.html"
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
        page.locator("#c").screenshot(path=str(HERE / "preview" / "step5-hud.png"), type="png")
        print(page.evaluate("document.getElementById('c').offsetHeight"))
        browser.close()


if __name__ == "__main__":
    main()
