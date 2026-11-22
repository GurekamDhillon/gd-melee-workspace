#!/usr/bin/env python3
"""Envoy UI, step 7: endless loops, sessions, the bank, the fighter picker, wave fights.

One design per screen, in the final kit (build_final.py). Writes:

  step7.html, step7-screens.html      the sources, beside this file
  preview/step7-sessions.png          the sheet
  screens/<name>.png, <name>@2x.png   each new screen alone at 640x480 and 1280x960 (new names only)

Original vector art only; retail menu parts are grey placeholders; fighters, foes, enemies and stages
are placeholders with invented names. Fonts: Bricolage Grotesque and Source Sans 3 (SIL OFL).
"""
import math
from pathlib import Path
from playwright.sync_api import sync_playwright

import build_final as bf
import build_step2 as s2
import build_step3 as s3
import build_step4 as s4
import build_step5 as s5
import build_step6 as s6
from build_step2 import svg, burst, SUN, INK, WHITE, CORAL, LAGOON, LILAC, STAR, BURST
from build_step3 import at, sil, bt, say, ptr, cur, frame, fcard, lock
from build_step4 import pog, d2, fst, ttl, DR, BG, BG2
from build_step5 import coin, FLOOR
from build_step6 import kicon, KINDS
from build_final import H, kpill, kem, kmini, sdots

HERE = Path(__file__).resolve().parent
PALE = "#C9BFF5"

CSS7 = r"""
/* ---------- step 7 ---------- */
.sdots.sm{gap:3px}
.sdots.sm i{width:12px;height:12px;border-width:2px}
.chip .pl,.hc .pl{position:absolute;z-index:3;background:#2A1A6E;color:#fff;border:1.5px solid #fff;border-radius:7px;font-family:"Brico";font-weight:800;font-size:11px;line-height:11px;padding:0 2.5px 1px;white-space:nowrap}
.chip .pl{right:-3px;top:-3px}
.chip .pl.lo{top:9px}
.hc .pl{right:-3px;top:-4px}
.fc.lk.on{background:#DAD7E8 !important}
.tk{display:inline-flex;gap:3px;align-items:center}
.tk svg{display:block;flex:none}
.q7{position:absolute;display:flex;align-items:center;gap:7px;height:28px;background:#fff;border:3px solid #2A1A6E;border-radius:10px;box-shadow:3px 4px 0 #2A1A6E;padding:0 10px 0 7px;white-space:nowrap;z-index:5}
.q7 b{font-family:"Brico";font-weight:800;font-size:13px;line-height:15px;letter-spacing:-.2px}
.q7 span.t{font-size:12px;line-height:14px;font-weight:700;color:#5A4C99}
.ts{position:absolute;display:flex;align-items:center;gap:5px;height:24px;background:#fff;border:2.5px solid #2A1A6E;border-radius:9px;box-shadow:2px 3px 0 #2A1A6E;padding:0 8px 0 4px;font-family:"Brico";font-weight:800;font-size:12.5px;line-height:14px;white-space:nowrap;color:#2A1A6E;z-index:6}
.ts svg{display:block;flex:none}
.ts .nb{position:absolute;bottom:-9px;width:12px;height:9px}
.bq{display:flex;justify-content:center;gap:38px;position:absolute;left:0;width:640px}
.bq>div{display:flex;flex-direction:column;align-items:center;gap:7px}
.bq .lb7{font-size:11px;line-height:12px;font-weight:700;color:#C9BFF5;white-space:nowrap}
.bq .ct{height:22px;display:flex;align-items:center;gap:6px;color:#fff;font-size:12.5px;line-height:14px;font-weight:700;white-space:nowrap}
.sl{position:relative;height:47px;border-top:2px dashed rgba(42,26,110,.28)}
.sl:first-child{border-top:0}
.seat{position:absolute;top:7px;width:100px;height:70px;border-radius:9px;padding:4px 5px}
.seat.ch{background:#FFD84A;box-shadow:0 0 0 2.5px #2A1A6E}
.seat .hd{display:flex;align-items:center;gap:5px;margin-top:5px;height:34px;overflow:hidden}
.seat .hd svg{flex:none}
.seat .nm7{font-family:"Brico";font-weight:800;font-size:12.5px;line-height:13px;letter-spacing:-.2px}
.stamp{position:absolute;border:3px solid #FF4D6D;color:#FF4D6D;background:#fff;border-radius:8px;font-family:"Brico";font-weight:800;white-space:nowrap}
.fc .tab{font-size:11px;line-height:14px;padding:0 4px}
.fc.rn .q{font-family:"Brico";font-weight:800;font-size:34px;line-height:48px;color:#5A4C99}
.wv{display:flex;gap:3px;margin-left:5px}
.wv i{width:8px;height:8px;border-radius:50%;border:1.5px solid #fff;box-sizing:border-box}
.wv i.d{background:#C9BFF5;border-color:#C9BFF5}
.wv i.c{background:#FFD84A;border-color:#FFD84A;box-shadow:0 0 0 1.5px #2A1A6E,0 0 0 3px #fff}

/* ---------- the sheet ---------- */
.two{display:grid;grid-template-columns:640px 640px;gap:22px 56px;align-items:start}
.two h3,.three h3{font-weight:900;font-size:20px;line-height:26px;margin-bottom:6px;white-space:nowrap}
.two h3 span,.three h3 span{font-weight:600;font-size:15px;color:#45425E;margin-left:9px}
.three{display:grid;grid-template-columns:repeat(3,499px);gap:14px 11px;margin-top:22px;align-items:start}
.three h3{font-size:17px;line-height:22px}
.three h3 span{font-size:13.5px}
.cap{max-width:640px}
"""
bf.CSS = bf.CSS + CSS7

# ------------------------------------------------------------------ the run at loop 3
LOOP, BEST = 3, 4
P7 = [(1, "Fighter A", 0, [("Ember", 5), ("Bolt", 3), ("Echo", 2), ("Wildfire", 1)]), (1, "Fighter B", 1, [("Frost", 2), ("Metronome", 4), ("Shatter", 1)]),
      (2, "Fighter C", 3, [("Frost", 3), ("Clean Landing", 3), ("Mirror", 2), ("Perfect Form", 1), ("Tailwind", 2)]), (2, "Fighter D", 5, [("Tailwind", 2), ("Feather Storm", 2), ("Ember", 1)])]
N7 = 5
KEYS = ["Plague Bearer", "Glass Core"]
SESSION = [["duel", "pack", "duel"], ["elite", "boss"]]      # every loop: fights 1 to 3, then the elite and the boss
bf.MID = P7
bf.pick_side.__defaults__ = (N7,)
bf.OFFERS = {1: ["Shatter", "Tailwind", "Mirror"], 2: ["Echo", "Shatter", "Bolt"]}
bf.HUDKEYS[:] = KEYS

# ------------------------------------------------------------------ patched parts: "+N" past level 3, small dots past 6
_chip, _hchip = s4.chip, s5.hchip


def plus(lvl, lo=False):
    return f'<span class="pl{" lo" if lo else ""}">+{lvl - 3}</span>' if lvl > 3 else ""


def chip7(d, lvl, mode=""):
    return _chip(d, lvl, mode)[:-6] + plus(lvl, mode == "up") + "</div>"


def hchip7(d, lvl, chg, **kw):
    return _hchip(d, lvl, chg, **kw)[:-6] + plus(lvl) + "</div>"


s4.chip = chip7
s5.hchip = hchip7


def hdots(left, total):
    """Stock dots in a fight: 14 px up to six, 12 px for seven and eight."""
    return s5.stockdots(left, total).replace('class="sdots"', 'class="sdots sm"') if total > 6 else s5.stockdots(left, total)


def hdw(total):
    return total * 15 - 3 if total > 6 else total * 18 - 4


def stocks(x, y, left, total, label="Team stocks", rot=-1.5, plus_=False):
    w = max(128, total * 15 + 21)
    return s3.stocks(x, y, left, total, label, rot=rot, w=w, plus=plus_).replace(burst("+1", CORAL, 40, 15), burst("+1", CORAL, 44, 15)), w


# ------------------------------------------------------------------ bank tokens
def ptok(size=18, st=""):
    """A banked reward not opened yet: a white badge with a question mark. st: done, cur or empty."""
    face, ink = (INK, "#fff") if st == "done" else ("#fff", INK)
    ring = f'<circle r="11.4" fill="{SUN}" stroke="{INK}" stroke-width="1.6"/>' if st == "cur" else ""
    mk = ('<path d="M-3.4,.2L-1,2.8L3.6,-2.6" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>' if st == "done"
          else f'<path d="M-2.9,-2.2 A3,3 0 1 1 1.3,.4 C.3,1 0,1.5 0,2.6" fill="none" stroke="{ink}" stroke-width="2.3" stroke-linecap="round"/><circle cy="5.6" r="1.35" fill="{ink}"/>')
    return svg(size, size, "-12.5 -12.5 25 25", f'{ring}<circle r="8.2" fill="{face}" stroke="{INK}" stroke-width="2.2"/>{mk}')


def ktok(size=18, st=""):
    """A keystone that is due: the ink wedge, small."""
    ring = f'<circle r="11.4" fill="{SUN}" stroke="{INK}" stroke-width="1.6"/>' if st == "cur" else ""
    return svg(size, size, "-12.5 -12.5 25 25", f'{ring}<path d="M-8,-6.5 H8 L5.6,7 H-5.6Z" fill="{INK}" stroke="#fff" stroke-width="4.4" stroke-linejoin="round"/>'
               f'<path d="M-8,-6.5 H8 L5.6,7 H-5.6Z" fill="{INK}" stroke="{INK}" stroke-width="1.6" stroke-linejoin="round"/><path transform="scale(.42) translate(0 1)" d="{STAR}" fill="{SUN}"/>')


def dtok(d, size=18, st=""):
    ring = f'<circle r="11.4" fill="{SUN}" stroke="{INK}" stroke-width="1.6"/>' if st == "cur" else ""
    return svg(size, size, "-12.5 -12.5 25 25", f'{ring}<g transform="translate(-9 -9)">{pog(DR[d][0], 18, 0, sq=False)}</g>')


def tokens(items, cur_=None, size=18):
    """The bank as a row. items: "pick", "key" or a drive name. Before cur_ they are done."""
    out = ""
    for i, it in enumerate(items):
        st = "" if cur_ is None else ("done" if i < cur_ else ("cur" if i == cur_ else ""))
        out += ptok(size, st) if it == "pick" else (ktok(size, st) if it == "key" else (ptok(size, st) if st == "done" else dtok(it, size, st)))
    return f'<span class="tk">{out}</span>'


def queue(items, cur_, label, then, right=16, top=441):
    """Where the stop is: the bank as tokens, which reward this is, and what follows."""
    return f'<div class="q7" style="right:{right}px;top:{top}px;transform:rotate(.6deg)">{tokens(items, cur_)}<b>{label}</b><span class="t">{then}</span></div>'


# ------------------------------------------------------------------ the loop strip
def mark(kind, st, x, y, r):
    if kind != "elite":
        return s6.tmark(kind, st, x, y, r)
    fill = {"done": INK, "cur": CORAL}.get(st, WHITE)
    q = r * 1.22
    o = f'<circle cx="{x}" cy="{y}" r="{r + 4.4}" fill="none" stroke="{INK}" stroke-width="2"/>' if st in ("cur", "lost") else ""
    o += f'<path d="M{x},{y - q:.1f} L{x + q:.1f},{y} L{x},{y + q:.1f} L{x - q:.1f},{y}Z" fill="{fill}" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>'
    if st == "lost":
        k = r * .5
        o += f'<path d="M{x - k},{y - k}L{x + k},{y + k}M{x + k},{y - k}L{x - k},{y + k}" stroke="{CORAL}" stroke-width="3" stroke-linecap="round"/>'
    return o


def geo(small):
    return (dict(xs=[74, 98, 122, 174, 199], tents=[148, 225], r=5.5, cy=30, lab=(64, 162), lf=15, lx=8, ly=13) if small
            else dict(xs=[134, 184, 234, 346, 396], tents=[290, 452], r=7, cy=31, lab=(120, 330), lf=22, lx=13, ly=9))


def lstrip(x, y, loop, pos, lost=False, w=608, rot=-.4, tab=None, stamp=None, small=False, face=SUN, then=True, label=None):
    """One loop on one strip: three fights, a stop, the elite and the boss, a stop. pos is the fight that is next (0 to 4)."""
    g = geo(small)
    kinds = ["duel", "duel", "duel", "elite", "boss"]
    m = ""
    for i, k in enumerate(kinds):
        st = "done" if i < pos else (("lost" if lost else "cur") if i == pos else "todo")
        m += mark(k, st, g["xs"][i], g["cy"], g["r"])
    for j, tx in enumerate(g["tents"]):
        m += s6.tmark("rest", "done" if (j == 0 and pos >= 3) else "todo", tx, g["cy"], g["r"] * .86)
    o = (f'<div class="bn" style="position:absolute;left:{g["lx"]}px;top:{g["ly"]}px;font-size:{g["lf"]}px;line-height:{g["lf"] + 3}px;letter-spacing:-.4px;white-space:nowrap">{label or f"Loop {loop}"}</div>'
         f'<div class="s10" style="position:absolute;left:{g["lab"][0]}px;top:3px">Fights 1 to 3</div><div class="s10" style="position:absolute;left:{g["lab"][1]}px;top:3px">Elite, boss</div>'
         + at(0, 0, svg(w - 6, 44, f"0 0 {w - 6} 44", m)))
    if then and not small:
        o += f'<div class="s10" style="position:absolute;left:486px;top:23px;color:{INK}">then loop {loop + 1}</div>'
    if stamp:
        o += f'<div class="stamp" style="right:10px;top:7px;transform:rotate(-5deg);font-size:14.5px;line-height:20px;padding:0 7px">{stamp}</div>'
    if tab:
        o += f'<span class="tab" style="background:{INK};left:auto;right:-8px;top:auto;bottom:-17px;transform:rotate(-4deg)">{tab}</span>'
    return f'<div class="st" style="left:{x}px;top:{y}px;width:{w}px;height:46px;background:{face};transform:rotate({rot}deg)">{o}</div>'


def best(x, y, n, rot=1.5, new=False):
    """The best loop reached. A new best is the same sticker in sunny, and says so."""
    return (f'<div class="st" style="left:{x}px;top:{y}px;height:30px;white-space:nowrap;transform:rotate({rot}deg);display:flex;align-items:center;gap:6px;padding:0 8px;{"background:" + SUN + ";" if new else ""}">'
            f'<span style="flex:none;display:flex">{s2.star_svg(17, fill="#fff" if new else SUN, sw=2.4)}</span><span class="bn" style="font-size:14px;line-height:16px;white-space:nowrap">{"New best" if new else "Best"}: loop {n}</span></div>')


def inject(fr, extra):
    """Add stickers to a finished frame()."""
    assert fr.endswith("</div></div>")
    return fr[:-12] + extra + "</div></div>"


def bgsvg(body):
    return svg(854, 480, "-107 0 854 480", body, 'class="sc"')


# ------------------------------------------------------------------ A. the banner between two fights of a session
def banner(fight=2, kind="pack", where="on Stage 4", pool=(5, 7), coins=47, bank=("pick",), bank_txt="1 reward"):
    s, i = (0, fight - 1) if fight <= 3 else (1, fight - 4)
    bg = bgsvg(f'<rect x="-107" width="854" height="480" fill="#2C1E70"/>'
               f'<text x="320" y="412" text-anchor="middle" font-family="Brico" font-weight="800" font-size="470" letter-spacing="-10" fill="#33257C">{fight}</text>'
               f'<path d="M-107,438 Q110,408 320,430 T747,420 V480 H-107Z" fill="#251861"/>')
    n = len(SESSION[s])
    marks = "".join(mark(k, "done" if j < i else ("cur" if j == i else "todo"), 14 + j * 30, 14, 8) for j, k in enumerate(SESSION[s]))
    st = (f'<div class="st" style="left:118px;top:146px;width:404px;height:100px;background:{SUN};transform:rotate(-1.5deg)">'
          f'<span class="tab" style="background:{INK};font-size:14px;line-height:19px;padding:0 7px">Loop {LOOP}</span>'
          f'<div style="position:absolute;left:14px;top:20px">{kicon(kind, 58)}</div>'
          f'<div class="hl" style="position:absolute;left:84px;top:13px;font-size:36px;line-height:38px;letter-spacing:-1px">Fight {fight} of 5</div>'
          f'<div style="position:absolute;left:86px;top:56px;font-size:13.5px;line-height:18px;white-space:nowrap"><span class="bn" style="font-size:17px;letter-spacing:-.3px">{KINDS[kind]}</span> {where}</div>'
          f'<div class="s10" style="position:absolute;right:14px;top:50px;color:{INK}">This session</div>'
          f'<div style="position:absolute;right:{12}px;top:64px">{svg(n * 30 - 2, 28, f"0 0 {n * 30 - 2} 28", marks)}</div></div>')
    row = (f'<div class="bq" style="top:286px"><div><span class="lb7">{"Team stocks" if pool[0] > 1 else "Last stock"}</span><span class="ct">{hdots(*pool)}</span></div>'
           f'<div><span class="lb7">Coins</span><span class="ct">{s5.coins(coins)}</span></div>'
           f'<div><span class="lb7">Banked for the stop</span><span class="ct">{tokens(bank)}{bank_txt}</span></div></div>')
    return frame(bg + st + row)


# ------------------------------------------------------------------ B and E. the fight HUD with the loop, the bank and a drop
def hud_party7(x, y, pool, n, plus=False, anchor="middle"):
    left, total = pool
    w = hdw(total)
    b = ""
    if left == 1:
        b = at(-10, -8, svg(30, 30, "-27 -27 54 54", f'<path d="{BURST}" fill="{SUN}" stroke="{INK}" stroke-width="3.4" stroke-linejoin="round"/>'), "z-index:-1")
    return f'<div class="hp" style="left:{x - 6}px;top:446px;width:0;height:20px">{at(-w / 2, 0 if total <= 6 else 1, b + hdots(left, total))}</div>'


s5.party = hud_party7


def bankpill(n, pop=False):
    b = at(-12, -11, svg(22, 22, "-27 -27 54 54", f'<path d="{BURST}" fill="{SUN}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'), "z-index:-1") if pop else ""
    return f'<div class="cn" style="padding-left:1px">{b}{ptok(17)}{n}</div>'


def topleft(coins, bank, label, pop=False):
    keys = "".join(f'<div style="position:relative;width:32px;height:27px;margin-right:2px">{kmini(k)}</div>' for k in KEYS)
    return (f'<div class="hp" style="left:14px;top:14px;display:flex;align-items:center;gap:0">{keys}<div style="margin-left:4px">{s5.coins(coins)}</div>'
            f'<div style="margin-left:6px">{bankpill(bank, pop)}</div></div>'
            f'<div class="hp" style="left:14px;top:47px"><span class="nt s" style="position:static">{label}</span></div>')


def plr7(p, **kw):
    base = {1: dict(p=1, name="Fighter A", kind=0, dmg=87, heat=78, row=[("Ember", 5, .8), ("Bolt", 3, .45), ("Echo", 2, .2), ("Wildfire", 1, .6)], active=("bolt", 1, 3), bench=("Fighter B", 1, 34, [])),
            2: dict(p=2, name="Fighter C", kind=3, dmg=41, heat=38, row=[("Frost", 3, .55), ("Clean Landing", 3, .3), ("Mirror", 2, .7), ("Perfect Form", 1, .15), ("Tailwind", 2, .4)], active=("wind", 1, 2),
                    bench=("Fighter D", 5, 112, []))}[p]
    base = dict(base)
    base.update(kw)
    return base


def hud(label, P1=None, P2=None, fs=(), pool=(5, 7), coins=47, bank=1, pop=False, extra="", world=None):
    fz = bf.fight(P1=P1 or plr7(1), P2=P2 or plr7(2), fs=list(fs), pool=pool, n=coins, world=world)
    assert fz.endswith("</div>")
    return fz[:-6] + topleft(coins, bank, label, pop) + extra + "</div>"


def drop_world(x, d, name=True):
    """A dropped drive on the floor: the badge as a die-cut sticker, a sunny ring under it, its name over it."""
    f, rar = DR[d][0], DR[d][1]
    ring = (f'<ellipse cx="{x}" cy="{FLOOR + 1}" rx="21" ry="6.5" fill="none" stroke="{INK}" stroke-width="6.5"/><ellipse cx="{x}" cy="{FLOOR + 1}" rx="21" ry="6.5" fill="none" stroke="{SUN}" stroke-width="3"/>'
            f'<ellipse cx="{x}" cy="{FLOOR + 1}" rx="33" ry="10" fill="none" stroke="{SUN}" stroke-width="2" opacity=".45"/>')
    o = at(0, 0, svg(1, 1, "0 0 1 1", ring))
    o += at(x - 17, FLOOR - 44, svg(34, 34, "-17 -17 34 34", f'<circle r="15" fill="#fff" stroke="{INK}" stroke-width="2.4"/><g transform="translate(-12 -12)">{pog(f, 24, 0, sq=False)}</g>'))
    if name:
        o += f'<div class="hp" style="left:{x - 60}px;top:{FLOOR - 64}px;width:120px;text-align:center"><span class="nt s" style="position:static">{d}</span></div>'
    return o


def toast(x, y, d, text, nx):
    """The pickup line over the player's row. nx: where the notch points, from the toast's left edge."""
    nb = svg(12, 9, "0 0 12 9", f'<path d="M0,0 H12 L6,8Z" fill="#fff" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/><rect x="1.5" y="-2" width="9" height="3.6" fill="#fff"/>', f'class="nb" style="left:{nx - 6}px"')
    return f'<div class="ts" style="left:{x}px;top:{y}px;transform:rotate(-1.5deg)">{pog(DR[d][0], 17, 0, sq=False)}{text}{nb}</div>'


def chipring(cx, cy):
    return at(cx - 19, cy - 19, svg(38, 38, "-19 -19 38 38", f'<circle r="16" fill="none" stroke="{INK}" stroke-width="5"/><circle r="16" fill="none" stroke="{SUN}" stroke-width="2.6"/>'), "z-index:1")


PACK = [s5.MIN(18), s5.MIN(47), s5.MIN(0)]
ROWX, ROWY = 14 + 100, 382 + 12     # P1's drive row in the frame


def drop(state="floor"):
    lab = f"Loop {LOOP}, fight 2 of 5"
    if state == "floor":
        return hud(lab, fs=PACK[:2], extra=drop_world(432, "Frost"))
    if state == "worn":
        P1 = plr7(1, row=[("Ember", 5, .8), ("Bolt", 3, .45), ("Echo", 2, .2), ("Wildfire", 1, .6), ("Frost", 1, 0)])
        k = 4
        return hud(lab, P1=P1, fs=PACK[:2], extra=chipring(ROWX + 15 + 30 * k, ROWY + 15) + toast(ROWX + 30 * k - 54, 360, "Frost", "Frost on, slot 5", 69))
    if state == "up":
        P1 = plr7(1, row=[("Ember", 5, .8), ("Bolt", 4, .45), ("Echo", 2, .2), ("Wildfire", 1, .6)])
        k = 1
        return hud(lab, P1=P1, fs=PACK[:2], extra=chipring(ROWX + 15 + 30 * k, ROWY + 15) + toast(ROWX + 30 * k - 22, 360, "Bolt", "Bolt, level 4", 37)
                   + at(ROWX + 30 * k + 82, 336, burst("Level|up!", CORAL, 50, 14), "z-index:7"))
    P1 = plr7(1, row=[("Ember", 5, .8), ("Bolt", 3, .45), ("Echo", 2, .2), ("Wildfire", 1, .6), ("Shatter", 1, .3)])
    return hud(lab, P1=P1, fs=PACK[:2], bank=2, pop=True, extra=toast(ROWX + 6, 360, "Frost", "Row full. Frost is banked.", 60))


def hud_loop():
    return hud(f"Loop {LOOP}, fight 4 of 5", fs=[bf.ELITE], pool=(5, 7), bank=3)


# ------------------------------------------------------------------ F. a wave fight
def waveplate(wave, of, left):
    pips = "".join(f'<i class="{"d" if i < wave - 1 else ("c" if i == wave - 1 else "")}"></i>' for i in range(of))
    return (f'<div class="fp hp" style="right:16px;top:14px;height:38px">{sil(2, 17, "#8E88B8")}'
            f'<div><div class="n" style="display:flex;align-items:center">Wave {wave} of {of}<span class="wv">{pips}</span></div>'
            f'<div class="d" style="font-size:21px;line-height:22px">{left} left</div></div></div>')


def waves():
    cx = 320
    P1, P2 = plr7(1, dmg=52, heat=66), plr7(2, dmg=23, heat=31)
    w = (s5.actor(cx - 74, FLOOR, 0, "p1", orb=[DR[d][0] for d, _, _ in P1["row"]], ready=[0], heat="hot") + s5.actor(cx + 128, 232, 3, "p2", orb=[DR[d][0] for d, _, _ in P2["row"]], heat="warm"))
    for x, fy in ((cx - 196, FLOOR), (cx - 150, 232), (cx + 14, FLOOR), (cx + 58, FLOOR), (cx + 196, FLOOR)):
        w += s5.actor(x, fy, 2, "foe", w=24)
    return hud(f"Loop {LOOP}, fight 2 of 5", P1=P1, P2=P2, fs=[], world=w, extra=waveplate(2, 3, 5))


# ------------------------------------------------------------------ C. the stop: rewards, keystone, (shop), road
def stop_pick(solo=False):
    items = ["pick", "pick", "pick", "key"]
    if solo:
        return inject(bf.pick(dict(i=0)), queue(items, 0, "Reward 1 of 3", "then a keystone, then the shop"))
    return inject(bf.pick(dict(i=0), dict(i=0)), queue(items, 0, "Reward 1 of 3", "then a keystone, then the shop"))


def stop_keystone():
    fr = bf.keystone(2, ("Echo Oath", "Winter Oath", "Grand Finale"), KEYS[:1])
    return inject(fr, queue(["pick", "pick", "pick", "key"], 3, "The keystone", "then the shop"))


def sposter(x, y, head, sub, lines, win, then, stamp=None):
    rows = ""
    for num, kind, name, where, car in lines:
        cr = "".join(f'<span style="margin-left:1px">{pog(DR[c][0], 20, 1, sq=False)}</span>' for c in car)
        rows += (f'<div class="sl"><div style="position:absolute;left:0;top:6px">{kicon(kind, 34)}</div>'
                 f'<div class="s10" style="position:absolute;left:42px;top:6px">Fight {num}</div><div class="bn" style="position:absolute;left:42px;top:18px;font-size:17px;line-height:20px;letter-spacing:-.3px">{KINDS[kind]}</div>'
                 f'<div style="position:absolute;left:108px;top:7px"><div class="t14" style="font-size:13.5px;line-height:16px">{name}</div><div class="b13" style="color:#5A4C99;white-space:nowrap">{where}</div></div>'
                 f'<div style="position:absolute;right:0;top:12px;display:flex">{cr}</div></div>')
    h = len(lines) * 47
    return (f'<div class="st" style="left:{x}px;top:{y}px;width:300px;height:290px;transform:rotate(-1deg);overflow:hidden">'
            f'<div style="position:absolute;left:0;top:0;width:294px;height:56px;background:{SUN};border-bottom:3px solid {INK}">'
            f'<div class="hl" style="position:absolute;left:10px;top:5px;font-size:24px;line-height:27px">{head}</div><div class="s10" style="position:absolute;left:11px;top:35px;color:{INK}">{sub}</div></div>'
            f'<div style="position:absolute;left:10px;top:59px;width:274px">{rows}</div>'
            f'<div style="position:absolute;left:10px;top:{59 + h + 3}px;width:274px;border-top:2px dashed rgba(42,26,110,.3);padding-top:6px">'
            f'<div class="s10">If you win</div><div class="b13" style="font-size:13px;line-height:16px">{win}</div><div class="b13" style="color:#5A4C99;margin-top:4px">{then}</div></div></div>')


def road(state="session"):
    clear = state == "clear"
    p = [s6.bg_road()]
    if clear:
        loop, pos, pool, coins = LOOP, 0, (6, 7), 12
        p.append(s4.big_rays(170, 214, 430, 18, SUN, .12))
        post = sposter(20, 70, "Loop 3 begins", "Fights 1 to 3, back to back",
                       [(1, "duel", "Fighter H", "on Stage 2", []), (2, "pack", "Five small foes", "on Stage 4", []), (3, "duel", "Fighter M", "on Stage 7", ["Bolt"])],
                       "Each win banks a reward for the stop.", "After this: a stop, then the elite and the boss.")
        line, a = "Loop 2 is cleared. Foes hit harder in loop 3, and the pool gains a stock.", "Start loop 3"
    else:
        loop, pos, pool, coins = LOOP, 3, (5, 7), 31
        post = sposter(20, 70, "Next: elite, then boss", f"Loop {LOOP}, fights 4 and 5, back to back",
                       [(4, "elite", "Fighter K", "on Stage 6", ["Wildfire", "Frost"]), (5, "boss", "Boss 2", "in the Cage arena", [])],
                       "The elite banks one of its drives and a reward. The boss banks a keystone.", "After this: a stop, then loop 4. The pool gains a stock.")
        line, a = "An elite, then the boss, with no stop between them.", "Start fight 4"
    p.append(lstrip(16, 8, loop, pos, stamp=f"Loop {loop - 1} cleared" if clear else None, then=not clear))
    p.append(at(16 + 3 + geo(False)["xs"][pos] - 13, 50, svg(26, 14, "0 0 26 14", f'<path d="M13,2 L22,12 H4Z" fill="{CORAL}" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>'), "z-index:4"))
    p += [post, s6.party(340, 72, cols=2, dx=146, dy=90, data=P7, n=N7)]
    sk, w = stocks(342, 254, pool[0], pool[1], plus_=clear)
    p += [sk, s6.purse(342 + w + (34 if clear else 12), 256, coins, w=104, note="Coins"), kpill(344, 316, KEYS[0], -1.5), kpill(486, 316, KEYS[1], 1.2)]
    if clear:
        p.append(best(470, 348, 3, rot=-1.5, new=True))
    p += [say(line), H(("A", a), ("Y", "Read your drives"), ("Start", "Pause"))]
    return frame("".join(p))


# ------------------------------------------------------------------ D. the camp with loops, and the fighter picker
def camp7(state="new"):
    saved = state == "saved"
    if saved:
        items = [("go", "Continue run", f"Loop {LOOP}, fight 4 of 5. 5 of 7 stocks left."), ("new", "New run", ""), ("fighters", "Fighters", f"{lock(11, LILAC)} set for this run"),
                 ("ta", "Team attack", s3.switch(False)), ("ng", "NG+ level", "0"), ("col", "Collection", "14 of 40"), ("back", "Back", "")]
        hov = "go"
    else:
        items = [("go", "Start run", "A new run, from loop 1."), ("fighters", "Fighters", "2 each"), ("ta", "Team attack", s3.switch(False)), ("ng", "NG+ level", "0"),
                 ("col", "Collection", "14 of 40"), ("back", "Back", "")]
        hov = "fighters"
    rots = [-1.2, .9, -.7, 1, -.9, .7, -1.1, 1.2]
    p, y = [s3.scene(1), s3.title()], 58
    for i, (k, lab, val) in enumerate(items):
        on = k == hov
        cls = "row" + (" big" if k == "go" else "") + (" back" if k == "back" else "") + (" on" if on else "")
        v = f'<span class="v">{val}</span>' if val else ""
        fd = "opacity:.5;" if (k == "fighters" and saved) else ""
        p.append(f'<div class="{cls}" style="top:{y}px;{fd}transform:rotate({0 if on else rots[i]}deg)"><span class="l">{lab}</span>{v}</div>')
        if on:
            p.append(ptr(10, y + (14 if k == "go" else 2)))
        y += 62 if k == "go" else 36
    p += [fcard(292, 54, "Fighter A", 0, 72, -3, "P1"), fcard(368, 60, "Fighter B", 1, 72, 2), s3.swap(354, 92),
          fcard(468, 58, "Fighter C", 3, 72, -2, "P2"), fcard(544, 54, "Fighter D", 5, 72, 3), s3.swap(530, 92)]
    if saved:
        sk, w = stocks(294, 244, 5, 7, rot=2)
        p += [lstrip(290, 182, LOOP, 3, w=312, rot=-1, small=True, tab="Saved run"), sk, kpill(294 + w + 14, 242, KEYS[0], -2), kpill(294 + w + 20, 271, KEYS[1], 1.5),
              s3.locktag(296, 304, -2), best(294 + w + 14, 310, BEST)]
        line = f"Pick up at loop {LOOP}, fight 4 with the saved party."
        h = [("Up / Down", "Choose"), ("A", "Continue run"), ("B", "Main menu"), ("P2: hold B", "Leave")]
    else:
        sk, w = stocks(294, 244, 5, 5, rot=2)
        p += [lstrip(290, 182, 1, -1, w=312, rot=-1, small=True, tab="Every loop", face="#fff", label="A loop"), sk, best(294 + w + 16, 252, BEST)]
        line = "Choose who you bring. Each player picks a main and a partner."
        h = [("Up / Down", "Choose"), ("A", "Choose fighters"), ("B", "Main menu"), ("Start", "Start run"), ("P2: hold B", "Leave")]
    return frame("".join(p + [say(line), H(*h)]))


NAMES = [f"Fighter {c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
KIND = {0: 0, 1: 1, 2: 3, 3: 5}
LOCKED = {14, 20, 22, 24, 25}
GX, GY, CW, CH, PX, PY = 26, 40, 60, 75, 66, 81


def cellxy(i):
    return GX + (i % 9) * PX, GY + (i // 9) * PY


def ctab(text, col, right=False):
    pos = "left:auto;right:-7px;transform:rotate(6deg)" if right else ""
    return f'<span class="tab" style="background:{col};{pos}">{text}</span>'


def seat(x, label, i, ch=False, empty=False):
    if empty:
        body = f'<div class="hd"><span class="nm7" style="color:{LILAC}">Not picked</span></div>'
    else:
        body = f'<div class="hd">{sil(KIND.get(i, i % 6), 21)}<span class="nm7">{NAMES[i].replace(" ", "<br>")}</span></div>'
    return f'<div class="seat{" ch" if ch else ""}" style="left:{x}px"><div class="s10" style="color:{INK if ch else LILAC}">{label}</div>{body}</div>'


def tray(x, p, main, partner, step, hov=None):
    """A player's two seats and their Done. step: main, partner, done (the cursor is on Done), ready."""
    col = CORAL if p == 1 else LAGOON
    o = f'<span class="tab" style="background:{col}">P{p}</span>'
    o += seat(8, "Main, choosing" if step == "main" else "Main", hov if (step == "main" and hov is not None) else main, ch=step == "main")
    o += seat(112, "Partner, choosing" if step == "partner" else "Partner", hov if (step == "partner" and hov is not None) else partner, ch=step == "partner", empty=(partner is None and step != "partner"))
    if step == "ready":
        o += f'<div class="stamp" style="left:216px;top:26px;transform:rotate(-7deg);font-size:17px;line-height:24px;padding:0 9px">Ready</div>'
    else:
        on = step == "done"
        o += f'<div class="db{" on" if on else ""}" style="left:{220 if on else 217}px;top:24px;width:64px;{"" if on else "opacity:.36;"}">Done</div>'
        if on:
            o += cur(266, 42, p)
    return f'<div class="st" style="left:{x}px;top:290px;width:294px;height:92px;transform:rotate({-.5 if p == 1 else .5}deg)">{o}</div>'


def picker(state="two"):
    solo = state == "solo"
    marks = {0: [("Main", CORAL, False)], 1: [("Partner", CORAL, False)]}
    if not solo:
        marks.setdefault(2, []).append(("Main", LAGOON, True))
        marks.setdefault(3, []).append(("Partner", LAGOON, True))
    hov = 14 if solo else 4
    p = [bgsvg(f'<rect x="-107" width="854" height="480" fill="{BG}"/><path d="M-107,300 Q120,282 330,296 T747,288 V480 H-107Z" fill="{BG2}"/><rect x="-107" y="396" width="854" height="84" fill="#33257C"/>'),
         ttl("Choose fighters", 16, 2, 24), at(232, 15, '<div class="wt">Each player brings two: a main and a partner.</div>')]
    for i in range(27):
        x, y = cellxy(i)
        rot = 0 if i == hov else (-.7, .6, -.5, .7)[(i + i // 9) % 4]
        tabs = "".join(ctab(t, c, r) for t, c, r in marks.get(i, []))
        if i == 26:
            c = (f'<div class="st fc s rn" style="left:{x}px;top:{y}px;width:{CW}px;height:{CH}px;transform:rotate({rot}deg)"><div class="q">?</div><div class="nm">Random</div></div>')
        elif i in LOCKED:
            c = fcard(x, y, "", i % 6, CW, rot, state="lock", note="Locked", cls="on" if i == hov else "").replace(f"height:{round(CW * 1.3) + 2}px", f"height:{CH}px")
        else:
            c = fcard(x, y, NAMES[i], KIND.get(i, i % 6), CW, rot, cls="on" if i == hov else "").replace(f"height:{round(CW * 1.3) + 2}px", f"height:{CH}px")
            if tabs:
                c = c.replace('">', '">' + tabs, 1)
        p.append(c)
    hx, hy = cellxy(hov)
    p.append(cur(hx + CW - 9, hy + CH - 12, 1))
    if solo:
        p += [tray(20, 1, 0, 1, "partner", None),
              say("Locked. Clear loop 2 with any party to open this fighter."), H(("Stick", "Choose"), ("B", "Back"))]
    else:
        p += [tray(20, 1, 0, 1, "partner", hov), tray(326, 2, 2, 3, "ready"),
              f'<div class="strip" style="left:24px">Fighter E as your partner.</div><div class="strip" style="left:330px">Ready. Waiting for P1.</div>',
              H(("Stick", "Choose"), ("A", "Pick"), ("B", "Back"))]
    return frame("".join(p))


# ------------------------------------------------------------------ E. the main-menu sticker and the results
def loopcard(loop, pos, bst):
    m = "".join(mark(k, "done" if i < pos else ("cur" if i == pos else "todo"), (15 + i * 26) if i < 3 else (28 + (i - 3) * 26), 13 if i < 3 else 41, 6.5) for i, k in enumerate(["duel", "duel", "duel", "elite", "boss"]))
    return (f'<div class="st" style="left:245px;top:0;width:97px;height:136px;background:{SUN};transform:rotate(3deg)">'
            f'<div class="bn" style="position:absolute;left:9px;top:5px;font-size:20px;line-height:23px;letter-spacing:-.4px;white-space:nowrap">Loop {loop}</div>'
            f'<div style="position:absolute;left:5px;top:34px">{svg(82, 56, "0 0 82 56", m)}</div>'
            f'<div class="s10" style="position:absolute;left:9px;top:98px;color:{INK}">Fight {pos + 1} of 5</div><div class="s10" style="position:absolute;left:9px;top:112px;color:{INK}">Best: loop {bst}</div></div>')


def mstick7(state):
    rows = "".join(bf.mrow(p, nm, k, ch, i % 2 == 0, N7) for i, (p, nm, k, ch) in enumerate(P7))
    sk, w = stocks(8, 218, 5, 7, rot=-3)
    return (f'<div class="p2"><div class="st" style="left:2px;top:8px;width:246px;height:198px;transform:rotate(-2deg)">'
            f'<div class="band"><div class="hl" style="font-size:23px;line-height:25px">Continue run</div><div class="sub">Loop {LOOP}, fight 4 of 5. Saved at the stop.</div></div>{rows}</div>'
            f'{loopcard(LOOP, 3, BEST)}'
            f'<div class="st" style="left:254px;top:146px;width:80px;height:30px;transform:rotate(4deg);background:{LAGOON};text-align:center"><span class="bn" style="font-size:15px;line-height:24px;color:#fff">NG+ 0</span></div>'
            f'{sk}{kpill(w + 22, 222, KEYS[0], 1.5)}{kpill(w + 30, 251, KEYS[1], -1.5)}'
            f'<div class="st" style="left:262px;top:186px;width:72px;height:28px;transform:rotate(-3deg);display:flex;align-items:center;gap:4px;padding-left:6px">{coin(17)}<span class="bn" style="font-size:15px">31</span></div></div>')


def menu7():
    s2.DESC["saved"] = f"Continue your run from loop {LOOP}, fight 4."
    old = bf.mstick
    bf.mstick = mstick7
    try:
        return bf.menu("saved")
    finally:
        bf.mstick = old


def results7():
    name = lambda t: f'<span class="bn" style="font-size:14px;line-height:16px">{t}</span>'
    both = lambda a, b: (f'<span class="cy2"><span class="pt" style="background:{CORAL}">P1</span>{a}</span> <span class="cy2" style="margin-left:3px"><span class="pt" style="background:{LAGOON}">P2</span>{b}</span>')
    data = [(1, "Fighter A", 0, [("Ember", 6), ("Bolt", 4), ("Echo", 2), ("Wildfire", 2), ("Shatter", 1)]), (1, "Fighter B", 1, [("Frost", 3), ("Metronome", 5), ("Shatter", 1), ("Bolt", 1)]),
            (2, "Fighter C", 3, [("Frost", 3), ("Clean Landing", 4), ("Mirror", 2), ("Perfect Form", 2), ("Tailwind", 3)]), (2, "Fighter D", 5, [("Tailwind", 2), ("Feather Storm", 3), ("Ember", 2)])]
    kn = ["Plague Bearer", "Glass Core", "Long Fuse"]
    nums = [("Loops cleared", "3"), ("Drives fired", "1,204"), ("Coins earned", both(612, 548)), ("Stocks lost", "19")]
    un = (bf.unl(16, 322, 132, "New drive", f'{pog("fire", 26, 2, sq=False)}{name("Wildfire")}', -1)
          + bf.unl(160, 324, 256, "Still locked", f'{lock(15, LILAC)}<span class="b13" style="color:#5A4C99">Fighter O opens when you clear loop 4.</span>', 1, True))
    p = [s6.bg_res(False), ttl("The run ended", 16, 0, 30), at(22, 38, '<div class="wt" style="font-size:13px;line-height:16px">Reached loop 4, fight 3: the duel on Stage 9 took the last stock.</div>'),
         f'<div class="st" style="left:534px;top:6px;width:88px;height:46px;transform:rotate(3deg);padding:4px 9px"><div class="s10">Time</div><div class="bn" style="font-size:20px;line-height:22px">58:12</div></div>',
         lstrip(16, 62, 4, 2, lost=True, rot=-.3, then=False), best(364, 6, 4, rot=-2, new=True),
         s6.party(18, 122, data=data, n=N7, cols=4, dx=152)]
    p += [kpill(18, 212 + i * 27, k, (-1.5, 1.2, -1)[i]) for i, k in enumerate(kn)]
    xs, ws = (166, 276, 386, 536), (100, 100, 140, 86)
    for i, (l, v) in enumerate(nums):
        p.append(f'<div class="num" style="left:{xs[i]}px;top:216px;width:{ws[i]}px;height:48px;transform:rotate({(-.8, .7, -.6, .8)[i]}deg)"><div class="s10">{l}</div><div class="bn"{" style=font-size:15px" if i == 2 else ""}>{v}</div></div>')
    p.append(ttl("Unlocked", 14, 293, 17))
    return frame("".join(p + [un, say("Loop 4 is your new best. It was loop 3."), H(("A", "Back to camp"))]))


# ------------------------------------------------------------------ every new screen, by file name
def screens():
    S = {}
    S["banner"] = banner(2, "pack", "on Stage 4", (5, 7), 47, ("pick",), "1 reward")
    S["banner-boss"] = banner(5, "boss", "in the Cage arena", (1, 7), 63, ("pick", "Frost", "pick"), "3 rewards")
    S["drop"] = drop("floor")
    S["drop-worn"] = drop("worn")
    S["drop-level-up"] = drop("up")
    S["drop-banked"] = drop("bank")
    S["stop-pick"] = stop_pick()
    S["stop-pick-solo"] = stop_pick(True)
    S["stop-keystone"] = stop_keystone()
    S["road-session"] = road("session")
    S["road-loop-clear"] = road("clear")
    S["camp-loops"] = camp7("new")
    S["camp-loops-saved"] = camp7("saved")
    S["fighters"] = picker("two")
    S["fighters-solo"] = picker("solo")
    S["hud-loop"] = hud_loop()
    S["menu-loop"] = menu7()
    S["results-loop"] = results7()
    S["waves"] = waves()
    return S


# ------------------------------------------------------------------ the sheet
def cell(S, k, title, state, cap, zoom=1.0):
    return f'<div><h3>{title}<span>{state}</span></h3>{bf.shot(S[k], zoom)}<p class="cap" style="max-width:{640 * zoom:.0f}px">{cap}</p></div>'


def parts_e():
    lb = bf.lb
    o = ""
    for i, (l, t) in enumerate(((5, 5), (5, 6), (5, 7), (1, 8))):
        o += at(14 + i * 148, 16, hdots(l, t)) + lb(14 + i * 148, 40, f"{t} dots: {'14' if t <= 6 else '12'} px", True)
    for i, (l, t) in enumerate(((5, 5), (5, 7), (6, 8))):
        o += stocks(16 + i * 190, 64, l, t)[0]
    o += lb(16, 126, "On a sticker the capsule grows; the sticker is 128 wide up to six dots, 136 for seven, 151 for eight.", True)
    o += lb(16, 152, "Level past 3: three full pips and an ink flag with the extra levels.")
    o += at(10, 166, '<div style="width:236px;height:42px;background:#fff;border-radius:9px"></div>')
    for i, (d, l) in enumerate((("Ember", 3), ("Ember", 4), ("Echo", 5), ("Bolt", 12))):
        o += at(18 + i * 60, 172, s4.chip(d, l)) + lb(14 + i * 60, 212, f"level {l}", True)
    for i, (d, l) in enumerate((("Ember", 3), ("Ember", 5), ("Echo", 4))):
        o += at(280 + i * 62, 170, s5.hchip(d, l, .6)) + lb(276 + i * 62, 212, f"HUD, level {l}", True)
    o += at(476, 176, f'<div class="rib" style="position:static;display:inline-flex;align-items:center">{s4.stars(3, 11)}<span class="bn" style="font-size:11px;line-height:12px;margin:0 2px 0 3px">+2</span></div>') + lb(470, 212, "On a tag: after the stars", True)
    return bf.pn("Stock dots at 5 to 8, and levels past 3", "The pool gains a stock for each loop cleared, up to eight. A drive's level has no top; the three pips stay and a flag counts the rest.", 610, 232, o, zoom=.78)


def parts_b():
    lb = bf.lb
    big = lambda d: svg(34, 34, "-17 -17 34 34", f'<circle r="15" fill="#fff" stroke="{INK}" stroke-width="2.4"/><g transform="translate(-12 -12)">{pog(DR[d][0], 24, 0, sq=False)}</g>')
    o = ""
    for i, d in enumerate(("Frost", "Bolt", "Perfect Form")):
        x = 50 + i * 96
        o += at(x - 17, 34, big(d)) + f'<div class="hp" style="left:{x - 60}px;top:14px;width:120px;text-align:center"><span class="nt s" style="position:static">{d}</span></div>'
        o += at(0, 0, svg(1, 1, "0 0 1 1", f'<ellipse cx="{x}" cy="76" rx="21" ry="6.5" fill="none" stroke="{INK}" stroke-width="6.5"/><ellipse cx="{x}" cy="76" rx="21" ry="6.5" fill="none" stroke="{SUN}" stroke-width="3"/>', 'style="display:block"'))
    o += lb(14, 100, "The drop: a 24 px badge on a white die-cut disc, 10 px over the floor, a sunny ring under it, its name over it.", True)
    o += toast(16, 124, "Frost", "Frost on, slot 5", 30) + toast(176, 124, "Bolt", "Bolt, level 4", 30) + toast(318, 124, "Frost", "Row full. Frost is banked.", 30)
    o += lb(14, 164, "The pickup line: 24 high, over the chip it is about, for 90 frames. Three wordings.", True)
    o += at(16, 190, bankpill(1)) + at(70, 190, bankpill(2, True)) + lb(120, 193, "The bank counter, beside the coins. It pops when something is banked.", True)
    o += at(16, 226, tokens(["pick", "pick", "Frost", "key"])) + lb(100, 229, "Bank tokens: a reward to open, a banked drive, a keystone that is due.", True)
    o += at(16, 256, tokens(["pick", "pick", "Frost", "key"], 1)) + lb(100, 259, "At the stop: done, the one being opened, to come.", True)
    return bf.pn("The drop, the pickup line and the bank", "A KO can leave a drive on the floor. The fighter in play takes it by touching it; no button.", 610, 286, o, zoom=1.0, dark=True)


def html(S):
    two = lambda *c: f'<div class="two">{"".join(c)}</div>'
    three = lambda *c: f'<div class="three">{"".join(c)}</div>'
    small = lambda k, t, s, c: cell(S, k, t, s, c, .78)
    A = two(cell(S, "banner", "The banner", "fight 2 is loading, session of three", "Shown over the load between two fights of a session, for about two seconds. No buttons, no strip, no hints: it is not a menu. One sunny sticker says the fight; the session's marks sit in its corner; stocks, coins and the bank sit under it, quiet."),
            cell(S, "banner-boss", "The banner", "the boss is loading, one stock left", "The second session has two marks: the elite's diamond, done, and the boss's star. The last stock is coral on its burst and its label changes to \"Last stock\". The bank shows a banked drive between two rewards."))
    B = two(cell(S, "drop", "A drop on the floor", "a pack fight; a foe's KO left Frost", "The drive's own badge on a white disc with a sunny ring on the floor and its name over it. It is a sticker, so it is ours to take. The fight label under the keystones now carries the loop, and the bank counter sits beside the coins."),
            f'<div>{parts_b()}</div>') + three(
        small("drop-worn", "Picked up: worn", "a free slot", "The badge lands in the next free slot with a ring; the line reads \"Frost on, slot 5\"."),
        small("drop-level-up", "Picked up: level up", "a duplicate", "A drive the fighter already wears goes up a level: the Level up burst, the line \"Bolt, level 4\", and the flag on the chip reads +1."),
        small("drop-banked", "Picked up: banked", "the row is full", "Nothing changes in the row. The line says why, and the bank counter at the top left pops and counts one more."))
    C = two(cell(S, "stop-pick", "The stop: rewards", "reward 1 of 3, both players choosing", "The pick of three as it is. One sticker at the bottom right is the whole stop: the bank as tokens with this one lit, \"Reward 1 of 3\", and what follows."),
            cell(S, "stop-keystone", "The stop: the keystone", "only when one is due", "The keystone pick as it is, with the same sticker: three rewards done, the wedge lit, then the shop. The shop itself is the rest stop screen, unchanged; its last row, \"Back on the road\", leads to the road screen."),
            cell(S, "road-session", "The road", "the next session: fights 4 and 5", "The poster lists the session, one line a fight, because nothing stops between them. The strip on top is one loop: three fights, a stop, the elite, the boss, a stop, then the next loop."),
            cell(S, "road-loop-clear", "The road: a loop is cleared", "after the boss and its stop", "The same screen. A stamp on the new strip, rays behind the poster, +1 on the stock pool, and the best loop if it is a new one. A starts the next loop."))
    D = two(cell(S, "camp-loops", "Camp", "no saved run, the Fighters row hovered", "The Fighters row is back and opens the picker; the cards on the right are the last party used. \"Run length\" is gone: a run is endless. \"Best: loop 4\" sits by the stocks."),
            cell(S, "fighters", "Choose fighters", "two players; P1 on the partner, P2 ready", "One plain grid, a cursor each. Three presses of A a player: main, partner, Done. The cursor starts on what you had, so A, A, A keeps the last party. Your picks carry your tab; the tray under the grid holds your two seats.")) + three(
        small("camp-loops-saved", "Camp: a saved run", "loop 3, saved at the stop", "The party is set for the run, so the Fighters row is faded with a lock. The strip shows the loop; the pool is 5 of 7."),
        small("fighters-solo", "Choose fighters: solo, a locked fighter", "", "One tray. A locked fighter is a faded card with a lock; the strip says what opens it and the hint line has no A."),
        small("stop-pick-solo", "The stop: rewards, solo", "", "The same sticker in the same corner on the centred solo layout."))
    E = two(cell(S, "hud-loop", "Fight HUD in loop 3", "the elite; levels past 3; 5 of 7 stocks", "\"Loop 3, fight 4 of 5\" on a white tag under the keystones. Ember is level 5: three pips and +2. Seven stock dots are 12 px so they still fit between the two corners."),
            cell(S, "results-loop", "Results", "the run ended in loop 4; a new best", "A run only ends when the last stock goes. The headline line says where; the strip shows the loop it ended in; \"Loops cleared\" leads the numbers; the best loop has its own sticker.")) + three(
        small("menu-loop", "Main menu: the saved run", "", "The punch card becomes a loop card: the loop, its five marks, the fight, the best loop. A run is saved at a stop, so the line says so."),
        small("waves", "F. A wave fight (provisional)", "wave 2 of 3", "One ink plate in the foes' corner replaces the foe plates: the wave, its pips, and how many are left. Everything else is the same HUD."),
        f'<div>{parts_e()}</div>')
    sec = lambda t, lede, body: f'<div class="sec"><h2>{t}</h2><p class="lede">{lede}</p>{body}</div>'
    return bf.head("Envoy UI, step 7") + f"""<div id="c">
<div class="top"><h1>Step 7: loops and sessions</h1>
<p>The screens the new rules need, one design each, in the final kit. Each is 640 by 480 game pixels, shown at actual size; the small ones at 0.78.</p></div>
{sec("A. Between two fights of a session", "No menu between the fights of a session, only this, over the load.", A)}
{sec("B. A drive dropped in a fight", "How it reads in the world, and the moment it is picked up.", B)}
{sec("C. The stop after a session", "One stop: the banked rewards one after another, a keystone if one is due, the shop, then the road to the next session.", C)}
{sec("D. The camp and the fighter picker", "The party is chosen at the camp, once, before a run. There is no character or stage select inside a run.", D)}
{sec("E. Loops and levels, and F. the wave fight", "Where the loop, a level past 3 and a bigger stock pool show. The wave counter is provisional, for packs of small enemies.", E)}
<p class="foot">Original vector art. Fonts: Bricolage Grotesque, Source Sans 3 (SIL OFL). Retail menu rows are grey placeholders. Fighters, foes, enemies, bosses and stages are placeholders with invented names; loadouts, prices, counts and times are made up for the mock.</p>
</div></body></html>"""


def main():
    S = screens()
    (HERE / "step7.html").write_text(html(S), encoding="utf-8")
    (HERE / "step7-screens.html").write_text(bf.screens_html(S), encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
        page.goto((HERE / "step7.html").as_uri())
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(400)
        page.locator("#c").screenshot(path=str(HERE / "preview" / "step7-sessions.png"), type="png")
        print("sheet height", page.evaluate("document.getElementById('c').offsetHeight"))
        for scale in (1, 2):
            pg = browser.new_page(viewport={"width": 700, "height": 600}, device_scale_factor=scale)
            pg.goto((HERE / "step7-screens.html").as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(400)
            if scale == 1:
                for b in pg.evaluate(bf.CHECK):
                    print(b)
            for k in S:
                out = HERE / "screens" / f"{k}{'@2x' if scale == 2 else ''}.png"
                pg.locator(f"#s-{k}").screenshot(path=str(out), type="png")
            pg.close()
        browser.close()


if __name__ == "__main__":
    main()
