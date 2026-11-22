#!/usr/bin/env python3
"""Envoy UI, step 10: the mid-fight tag, rethought. Today's tag and four directions for it.

A choice sheet, not final screens: for today's tag and each direction, the input on a pad, three frames of
what happens, the HUD part, and the rule in one line; then a recommendation. Writes:

  step10.html                  the source, beside this file
  preview/step10-tag.png       the sheet

Original vector art only. The pad is a generic drawing, not any real controller; fighters and foes are
placeholders. Fonts: Bricolage Grotesque and Source Sans 3 (SIL OFL).
Design note: scratch/envoy-notes/envoy-tag-rethink.md.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

import build_final as bf
import build_step3 as s3
from build_step2 import svg, SUN, INK, WHITE, CORAL, LAGOON, LILAC, BURST
from build_step4 import pog

HERE = Path(__file__).resolve().parent
PALE = "#C9BFF5"
SKY = "#EEF0FB"
GREY = "#BFC2CE"

CSS10 = r"""
/* ---------- step 10: the sheet ---------- */
#c{background:#fff}
.dir{display:grid;grid-template-columns:318px 300px 1fr 214px;gap:0 26px;align-items:start;padding:20px 0 22px;border-top:3px solid #2A1A6E}
.dir.now{border-top:0;background:#F6F5FA;border-radius:18px;padding:18px 22px 20px;margin-bottom:26px}
.dir h2{font-size:27px;line-height:1.1;margin-bottom:8px;display:flex;align-items:center;gap:10px}
.dir h2 i{font-style:normal;flex:none;width:34px;height:34px;border-radius:50%;background:#2A1A6E;color:#fff;font-family:"Brico";font-weight:800;font-size:19px;line-height:33px;text-align:center}
.dir .rule{font-family:"Brico";font-weight:800;font-size:18px;line-height:23px;color:#2A1A6E;background:#FFD84A;border:3px solid #2A1A6E;border-radius:12px;box-shadow:3px 4px 0 #2A1A6E;padding:8px 12px 9px;transform:rotate(-1deg);margin:4px 4px 14px 0}
.dir.now .rule{background:#fff}
.dir dl{display:grid;grid-template-columns:74px 1fr;gap:5px 8px;font-size:14.5px;line-height:1.3;color:#45425E}
.dir dt{font-weight:900;color:#1A1830}
.dir h4{font-weight:900;font-size:14.5px;line-height:18px;color:#1A1830;margin-bottom:6px}
.dir h4 span{font-weight:600;color:#45425E;margin-left:7px}
.fr3{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.fr3 svg{display:block;width:100%;height:auto;border-radius:12px;border:3px solid #2A1A6E}
.fr3 p{font-size:14px;line-height:1.28;color:#45425E;margin-top:6px}
.fr3 p b{color:#1A1830;font-weight:900}
.pad svg,.hud svg{display:block}
.pad p,.hud p{font-size:14px;line-height:1.28;color:#45425E;margin-top:6px}
.pad p b,.hud p b{color:#1A1830;font-weight:900}
.rec10{background:#2A1A6E;color:#F4F1FF;border-radius:18px;padding:26px 30px 24px;display:grid;grid-template-columns:1.05fr 1.25fr 1fr;gap:36px;margin-top:8px}
.rec10 h2{font-size:25px;line-height:1.15;margin-bottom:8px;color:#FFD84A}
.rec10 p{font-size:16.5px;line-height:1.42}
.rec10 p+p{margin-top:8px}
.rec10 b{font-weight:900;color:#FFD84A}
.rec10 ol{margin:0 0 0 20px;font-size:16.5px;line-height:1.42}
.rec10 li+li{margin-top:5px}
.rec10 table{border-collapse:collapse;font-size:15.5px;line-height:1.3;margin-top:8px;width:100%}
.rec10 td{padding:4px 10px 4px 0;border-top:1.5px solid rgba(255,255,255,.22);vertical-align:top}
.rec10 td:last-child{font-weight:900;color:#FFD84A;white-space:nowrap;padding-right:0;text-align:right}
"""
bf.CSS = bf.CSS + CSS10

FONT = 'font-family="Brico" font-weight="800"'


def T(x, y, t, s=13, a="start", c=INK, extra=""):
    return f'<text x="{x}" y="{y}" {FONT} font-size="{s}" text-anchor="{a}" fill="{c}" {extra}>{t}</text>'


# ------------------------------------------------------------------ the pad (a generic drawing)
def btn(x, y, r, label, on=False, fs=None):
    fill = SUN if on else WHITE
    ring = f'<circle cx="{x}" cy="{y}" r="{r + 6}" fill="none" stroke="{CORAL}" stroke-width="3.5"/>' if on else ""
    return ring + f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{INK}" stroke-width="2.8"/>' + T(x, y + (fs or r) * .36, label, fs or r, "middle")


def pad(on=(), cross=(), note_l="", note_r=""):
    """on: parts lit sunny (stick, dpad_d, dpad_r, y, x, a, b, c, l, r, z). cross: parts struck out in coral."""
    lit = lambda k: k in on
    b = ""
    # shoulders
    b += f'<rect x="38" y="20" width="64" height="24" rx="10" fill="{SUN if lit("l") else WHITE}" stroke="{INK}" stroke-width="2.8"/>' + T(70, 33.5, "L", 11, "middle")
    b += f'<rect x="198" y="20" width="64" height="24" rx="10" fill="{SUN if lit("r") else WHITE}" stroke="{INK}" stroke-width="2.8"/>' + T(230, 33.5, "R", 11, "middle")
    b += f'<rect x="150" y="24" width="38" height="16" rx="7" fill="{SUN if lit("z") else WHITE}" stroke="{INK}" stroke-width="2.8"/>' + T(169, 35, "Z", 10, "middle")
    # body: one plain bar with two round grips
    b += f'<path d="M48,38 H252 C282,38 294,66 294,104 C294,150 278,178 256,178 C236,178 228,160 214,146 H86 C72,160 64,178 44,178 C22,178 6,150 6,104 C6,66 18,38 48,38Z" fill="{PALE}" stroke="{INK}" stroke-width="3.2" stroke-linejoin="round"/>'
    # control stick
    if lit("stick"):
        b += f'<circle cx="72" cy="84" r="31" fill="none" stroke="{CORAL}" stroke-width="3.5"/>'
    b += f'<circle cx="72" cy="84" r="24" fill="{WHITE}" stroke="{INK}" stroke-width="2.8"/><circle cx="72" cy="84" r="13" fill="{SUN if lit("stick") else GREY}" stroke="{INK}" stroke-width="2.8"/>'
    # d-pad
    cx, cy = 112, 132
    b += f'<path d="M{cx - 7},{cy - 20} h14 v13 h13 v14 h-13 v13 h-14 v-13 h-13 v-14 h13Z" fill="{WHITE}" stroke="{INK}" stroke-width="2.8" stroke-linejoin="round"/>'
    for k, (dx, dy) in (("dpad_d", (0, 13)), ("dpad_r", (13, 0)), ("dpad_l", (-13, 0)), ("dpad_u", (0, -13))):
        if lit(k):
            b += f'<rect x="{cx + dx - 6.5}" y="{cy + dy - 6.5}" width="13" height="13" rx="2" fill="{SUN}" stroke="{INK}" stroke-width="2.2"/><circle cx="{cx + dx}" cy="{cy + dy}" r="15" fill="none" stroke="{CORAL}" stroke-width="3.5"/>'
    # face buttons: a plain diamond
    b += btn(228, 104, 13, "A", lit("a")) + btn(202, 84, 11, "B", lit("b")) + btn(254, 84, 11, "X", lit("x")) + btn(228, 62, 11, "Y", lit("y"))
    # second stick
    b += f'<circle cx="188" cy="132" r="13" fill="{SUN if lit("c") else WHITE}" stroke="{INK}" stroke-width="2.8"/>' + T(188, 136.5, "C", 12, "middle")
    for k in cross:
        x, y = {"dpad_d": (112, 145), "stick": (72, 84)}[k]
        b += f'<path d="M{x - 13},{y - 13} L{x + 13},{y + 13} M{x - 13},{y + 13} L{x + 13},{y - 13}" stroke="{CORAL}" stroke-width="4.5" stroke-linecap="round"/>'
    if note_l:
        b += T(8, 200, note_l, 13.5)
    if note_r:
        b += T(292, 200, note_r, 13.5, "end")
    return svg(300, 186, "0 0 300 186", b)


def thumb(x1, y1, x2, y2):
    """The left thumb's trip, drawn over the pad."""
    return (f'<path d="M{x1},{y1} C{x1 - 34},{y1 + 14} {x2 - 40},{y2 - 8} {x2 - 18},{y2}" fill="none" stroke="{CORAL}" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="1 7"/>'
            f'<path d="M{x2 - 26},{y2 - 9} L{x2 - 16},{y2} L{x2 - 28},{y2 + 6}" fill="none" stroke="{CORAL}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>')


# ------------------------------------------------------------------ frames (placeholder fighters)
def fig(kind, x, y, s=1.0, fill=WHITE, letter="", op=1, dash=False, col=INK):
    """A placeholder fighter standing with its feet at (x, y)."""
    body, head = s3.SILS[kind % 6]
    d = ' stroke-dasharray="4 4"' if dash else ""
    lt = T(20, 46, letter, 15, "middle", col if fill != INK else WHITE) if letter else ""
    return (f'<g transform="translate({x - 20 * s} {y - 54 * s}) scale({s})" opacity="{op}">'
            f'<g fill="{fill}" stroke="{col}" stroke-width="2.8" stroke-linejoin="round"{d}><path d="{body}"/>{head}</g>{lt}</g>')


A = lambda x, y, **k: fig(0, x, y, fill=WHITE, letter="A", **k)
B = lambda x, y, **k: fig(4, x, y, fill=LILAC, letter="B", **k)
FOE = lambda x, y, **k: fig(1, x, y, fill=INK, col=INK, **k)


def hit(x, y, s=.5, fill=SUN):
    return f'<g transform="translate({x} {y}) scale({s})"><path d="{BURST}" fill="{fill}" stroke="{INK}" stroke-width="{2.6 / s:.1f}" stroke-linejoin="round"/></g>'


def popring(x, y, r=30):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="{CORAL}" stroke-width="4"/><circle cx="{x}" cy="{y}" r="{r + 8}" fill="none" stroke="{CORAL}" stroke-width="2.5" stroke-dasharray="3 7"/>'


def arrow(x1, y1, x2, y2, col=INK):
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    p = lambda d, w: f"{x2 - d * math.cos(a) + w * math.sin(a):.1f},{y2 - d * math.sin(a) - w * math.cos(a):.1f}"
    return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="3" stroke-linecap="round"/><path d="M{p(9, 5)} L{x2},{y2} L{p(9, -5)}" fill="none" stroke="{col}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'


def chip(x, y, t, fill=WHITE, col=INK, s=12.5):
    w = len(t) * s * .56 + 16
    return f'<rect x="{x}" y="{y}" width="{w:.0f}" height="22" rx="8" fill="{fill}" stroke="{INK}" stroke-width="2.4"/>' + T(x + w / 2, y + 15.5, t, s, "middle", col)


def keycap(x, y, t, r=11):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{SUN}" stroke="{INK}" stroke-width="2.6"/>' + T(x, y + 4.5, t, 13, "middle")


def scene(body, sky=SKY):
    floor = f'<rect x="0" y="118" width="240" height="32" fill="{PALE}"/><path d="M0,118 H240" stroke="{INK}" stroke-width="3"/>'
    return svg(240, 150, "0 0 240 150", f'<rect width="240" height="150" fill="{sky}"/>{floor}{body}')


def strip(*frames):
    return '<div class="fr3">' + "".join(f"<div>{scene(b)}<p>{c}</p></div>" for b, c in frames) + "</div>"


# ------------------------------------------------------------------ HUD parts
def sticker(x, y, w, h, fill=WHITE, rot=0):
    return f'<g transform="rotate({rot} {x + w / 2} {y + h / 2})"><rect x="{x + 3}" y="{y + 4}" width="{w}" height="{h}" rx="9" fill="{INK}"/><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{INK}" stroke-width="2.8"/>'


def head(x, y, fill, letter):
    return f'<circle cx="{x}" cy="{y}" r="10" fill="{fill}" stroke="{INK}" stroke-width="2.4"/>' + T(x, y + 4.2, letter, 11.5, "middle")


def ring(x, y, fam, frac, r=9):
    import math
    c = 2 * math.pi * (r + 4)
    return (f'<circle cx="{x}" cy="{y}" r="{r + 4}" fill="none" stroke="#DAD7E8" stroke-width="3"/>'
            f'<circle cx="{x}" cy="{y}" r="{r + 4}" fill="none" stroke="{INK}" stroke-width="3" stroke-dasharray="{c * frac:.1f} {c:.1f}" transform="rotate(-90 {x} {y})"/>'
            f'<g transform="translate({x - r} {y - r})">{pog(fam, 2 * r)}</g>')


def heatbar(x, y, w, frac, notch=None):
    b = f'<rect x="{x}" y="{y}" width="{w}" height="14" rx="7" fill="{WHITE}" stroke="{INK}" stroke-width="2.6"/><rect x="{x + 2}" y="{y + 2}" width="{(w - 4) * frac:.0f}" height="10" rx="5" fill="{CORAL}"/>'
    for m in (.18, .4, .73):
        b += f'<path d="M{x + w * m:.0f},{y - 3} v20" stroke="{INK}" stroke-width="2.2"/>'
    if notch is not None:
        nx = x + w * notch
        b += f'<path d="M{nx:.0f},{y + 17} l-6,9 h12Z" fill="{SUN}" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>'
    return b


def dglyph(x, y, lit="d"):
    b = f'<path d="M{x - 3.5},{y - 10} h7 v6.5 h6.5 v7 h-6.5 v6.5 h-7 v-6.5 h-6.5 v-7 h6.5Z" fill="{WHITE}" stroke="{INK}" stroke-width="2"/>'
    dx, dy = {"d": (0, 6.5), "r": (6.5, 0)}[lit]
    return b + f'<rect x="{x + dx - 3}" y="{y + dy - 3}" width="6" height="6" fill="{CORAL}"/>'


def hud(body, h=120):
    return svg(214, h, f"0 0 214 {h}", body)


HUD_NOW = hud(sticker(8, 30, 190, 44, "#DAD7E8", -2) + f'<rect x="12" y="34" width="84" height="36" rx="6" fill="{WHITE}"/>' + head(32, 52, LILAC, "B") + T(50, 57, "Fighter B", 14) + dglyph(172, 52) + "</g>"
              + T(8, 104, "fills over 5 seconds", 13, c="#45425E"))
HUD_1 = hud(sticker(8, 30, 190, 44, SUN, -2) + head(32, 52, LILAC, "B") + T(50, 57, "Fighter B", 14) + keycap(172, 52, "Y") + "</g>"
            + chip(96, 4, "now", CORAL, WHITE) + T(8, 98, "sunny for 20 frames", 13, c="#45425E") + T(8, 114, "after you deal damage", 13, c="#45425E"))
HUD_2 = hud(heatbar(10, 14, 190, .46, notch=.13) + keycap(35, 54, "Y") + T(52, 59, "30 Heat", 13.5)
            + sticker(8, 76, 190, 40, WHITE, 1.5) + head(30, 96, LILAC, "B") + ring(70, 96, "fire", .8) + ring(104, 96, "bolt", .35) + ring(138, 96, "frost", .1) + "</g>", 126)
HUD_3 = hud(sticker(8, 14, 190, 46, WHITE, -1.5) + head(30, 37, LILAC, "B") + ring(70, 37, "fire", .55) + ring(104, 37, "wind", .9) + ring(138, 37, "bolt", .2) + T(160, 42, "x½", 14) + "</g>"
            + T(8, 84, "no button in a fight;", 13, c="#45425E") + T(8, 101, "sunny on the platform", 13, c="#45425E"))
HUD_4 = hud(sticker(8, 12, 190, 46, WHITE, -1.5) + head(30, 35, WHITE, "A") + ring(70, 35, "fire", .55) + ring(104, 35, "bolt", .9) + ring(138, 35, "frost", .2) + "</g>"
            + dglyph(22, 88, "r") + T(40, 93, "active", 13) + dglyph(112, 88, "d") + T(130, 93, "2nd active", 13))


# ------------------------------------------------------------------ the rows
def row(n, name, rule, facts, pad_svg, pad_cap, frames, hud_svg, hud_cap, now=False):
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)
    num = f"<i>{n}</i>" if n else ""
    return (f'<div class="dir{" now" if now else ""}"><div><h2>{num}{name}</h2><div class="rule">{rule}</div><dl>{dl}</dl></div>'
            f'<div class="pad"><h4>The input</h4>{pad_svg}<p>{pad_cap}</p></div>'
            f'<div><h4>What happens<span>A and B are your pair, the dark one is the foe</span></h4>{frames}</div>'
            f'<div class="hud"><h4>On the HUD</h4>{hud_svg}<p>{hud_cap}</p></div></div>')


def rows():
    bars = f'<rect width="240" height="26" fill="#14102E"/><rect y="124" width="240" height="26" fill="#14102E"/>'
    card = f'<path d="M22,52 H228 L218,98 H12Z" fill="#14102E"/>' + T(120, 82, "TAG   A  &gt;&gt;  B", 19, "middle", WHITE)
    NOW = row("", "Today", "D-pad down, when standing or falling. The game stops for up to a second.",
              [("Gives", "Nothing, unless you wear Slipstream or Relay."), ("Limit", "5 seconds between tags."), ("Why it drags", "The steering thumb does it, it cannot cancel a move, and it is a cutscene.")],
              pad(on=("dpad_d",), cross=("stick",)).replace("</svg>", thumb(60, 96, 112, 147) + "</svg>"),
              "<b>The left thumb leaves the stick</b>, presses down, presses down again to skip, then travels back.",
              strip((A(86, 118) + FOE(150, 104) + hit(122, 78) + arrow(160, 70, 186, 44), "<b>A lands a hit</b> and has to finish the whole move first."),
                    (A(86, 118, op=.35) + FOE(168, 84, op=.35) + bars + card, "<b>Everything stops</b> behind bars and a name card, for you and for player 2."),
                    (B(86, 118) + FOE(186, 70) + T(86, 40, "?", 30, "middle", CORAL) + arrow(186, 36, 206, 22), "<b>B stands still.</b> Your thumb is on the D-pad, not the stick.")),
              HUD_NOW, "A small sticker beside the Heat bar. It says who is benched and nothing else.", now=True)
    D1 = row(1, "Quick Tag", "Tag when you are free to act, or right after you deal damage.",
             [("Gives", "Nothing new. This fixes the hands only."), ("Limit", "3 seconds between tags."), ("Build", "Small. One button masked, one check loosened, no freeze."), ("Risk", "Easy to do, still no reason to.")],
             pad(on=("y", "stick")), "<b>Y is Tag</b>; X and the stick still jump. The right thumb tags, the left never lets go. A press is kept for 8 frames.",
             strip((A(86, 118) + FOE(150, 104) + hit(122, 78) + keycap(36, 30, "Y") + T(54, 35, "within 20 frames", 12.5), "<b>A lands a hit.</b> Press Y during it or just after."),
                   (A(58, 118, op=.3, dash=True) + B(92, 118) + popring(92, 86) + FOE(170, 78), "<b>B is there on the next frame.</b> No pause, no card. Speed and facing carry over."),
                   (B(150, 84) + FOE(190, 52) + hit(172, 58) + arrow(100, 112, 134, 92, CORAL), "<b>B follows up at once</b>, still drifting the way you were holding.")),
             HUD_1, "The same sticker, with the Tag button on it. It turns sunny while a tag would cancel your move.")
    D2 = row(2, "Assist Strike", "Tag: your partner jumps in beside you and strikes once. Costs 30 Heat.",
             [("Gives", "A second body. Its damage fills your Heat and charges its own drive row."), ("Limit", "30 Heat a call. No cooldown."), ("Build", "Large. Two live fighters on one port, one of them scripted."), ("Risk", "The engine work, then a smash on demand.")],
             pad(on=("y", "stick")), "<b>Tap Y</b>: B strikes and leaves. <b>Hold Y</b>: B stays, A leaves. The stick picks the strike: side, up or down.",
             strip((A(92, 118) + FOE(156, 104) + hit(128, 78) + chip(8, 8, "Heat 52") , "<b>A lands a hit</b> with Heat to spend."),
                   (B(50, 118) + popring(50, 86, 28) + A(104, 118) + FOE(176, 80) + arrow(66, 80, 96, 66, CORAL) + chip(8, 8, "Heat 22", CORAL, WHITE), "<b>B appears behind A, already swinging.</b> You keep moving A the whole time."),
                   (B(60, 118, op=.3, dash=True) + A(150, 92) + FOE(198, 66) + hit(176, 62) + hit(120, 100, .34, CORAL), "<b>B's strike fires B's drives, then B is gone.</b> A is already on the foe.")),
             HUD_2, "A mark at 30 on the Heat bar. The bench sticker shows B's drives charging.")
    orbit = "".join(f'<g transform="translate({x - 10} {y - 10})" opacity=".85">{pog(f, 20)}</g>' for x, y, f in ((42, 64, "fire"), (130, 60, "wind"), (86, 28, "bolt")))
    plat = f'<path d="M112,84 H188 L178,96 H122Z" fill="{SUN}" stroke="{INK}" stroke-width="2.8" stroke-linejoin="round"/>'
    D3 = row(3, "Backline", "Your partner backs you up from the bench. Swap when you come back from a lost stock.",
             [("Gives", "Two drive rows firing. The bench's row charges at half speed."), ("Limit", "Half charge. No swap in the middle of a stock."), ("Build", "Small to medium. Mostly rules; the swap moves to the respawn."), ("Risk", "More power, fewer decisions. No two-fighter combos.")],
             pad(on=("dpad_d",)), "<b>Nothing to press in a fight.</b> D-pad down swaps only on the respawn platform, where nothing is chasing you.",
             strip((A(86, 118) + f'<ellipse cx="86" cy="62" rx="56" ry="38" fill="none" stroke="{INK}" stroke-width="2" stroke-dasharray="3 6" opacity=".5"/>' + orbit + FOE(186, 118), "<b>A fights.</b> B's drives ride a wide, dim ring around A."),
                   (A(86, 118) + FOE(180, 118) + f'<path d="M92,34 L128,62 L116,66 L160,92" fill="none" stroke="#3E6BFF" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>' + hit(170, 92, .46) + f'<g transform="translate(77 20)">{pog("bolt", 18)}</g>', "<b>A bench drive fills and fires</b> by itself at the foe A just hit."),
                   (plat + B(150, 86) + dglyph(24, 34) + T(40, 39, "send B", 12.5) + FOE(40, 118, s=.8), "<b>A stock is lost.</b> On the platform, press down to send B in at 0%.")),
             HUD_3, "The bench sticker becomes B's drive row.")
    cards = (sticker(26, 44, 82, 74, SUN, -4) + "</g>" + fig(0, 67, 110, s=.9, fill=WHITE, letter="A") + sticker(132, 44, 82, 74, WHITE, 3) + "</g>" + fig(4, 173, 110, s=.9, fill=LILAC, letter="B"))
    D4 = row(4, "Drop it", "One fighter per player in a fight. Choose who fights at each stop.",
             [("Gives", "A free D-pad direction, one row to read, and the three paired fighters become playable."), ("Loses", "Two-fighter combos, hiding a hurt fighter, two drives, a keystone and a Unique."), ("Build", "Deletion, plus rewriting the rules that mention a tag."), ("Risk", "Solo runs get thinner.")],
             pad(on=("dpad_d",)), "<b>The tag button is gone.</b> D-pad down can hold the second active drive.",
             strip((A(86, 118) + FOE(160, 104) + hit(130, 78), "<b>One fighter, one row.</b> A fight plays like a fight."),
                   (A(86, 118) + FOE(196, 30, op=.4) + hit(176, 44, .6, CORAL) + chip(8, 8, "fight won"), "<b>The fight ends.</b> B has not been on screen."),
                   (f'<rect width="240" height="150" fill="{INK}"/>' + T(120, 28, "Who takes the next fights?", 14, "middle", WHITE) + cards, "<b>At the stop, pick who fights next.</b> Both keep their own drives.")),
             HUD_4, "No bench sticker in a fight. It moves to the road screen.")
    return NOW + D1 + D2 + D3 + D4


def html():
    REC = ('<div class="rec10"><div><h2>Test Quick Tag first, then add Handoff</h2>'
           '<p>The hands are cheap to fix and the answer decides everything else. If the quick tag feels right, one sentence joins it to the build:</p>'
           '<p><b>Handoff: tag right after you deal damage and the newcomer&rsquo;s first drive fires.</b></p>'
           '<p>That is the one-body half of Assist Strike, on the cooldown that already exists. Relay becomes the big version of it.</p></div>'
           '<div><h2>The ten-minute test</h2><p>Solo, fight 1, a pair you know, two cheap drives each.</p>'
           '<table><tr><td>Tag button</td><td>Y</td></tr><tr><td>Freeze</td><td>2 frames, no card</td></tr><tr><td>A press is kept for</td><td>8 frames</td></tr>'
           '<tr><td>Tag out of a move after damage</td><td>20 frames</td></tr><tr><td>Between tags</td><td>3 seconds</td></tr></table>'
           '<p>Run and tag. Launcher, Y, aerial. Throw, Y, follow-up. Then the same with Handoff on.</p></div>'
           '<div><h2>What the answer leads to</h2><ol><li><b>Easy to do, and I tag for what it fires:</b> build Handoff. Assist Strike can wait.</li>'
           '<li><b>Easy to do, still beside the point:</b> Backline. Both fighters and both builds stay.</li>'
           '<li><b>Backline falls flat too:</b> drop it, as a roster of two with one per fight.</li></ol></div></div>')
    return bf.head("Envoy UI, step 10") + f"""<div id="c">
<div class="top"><h1>Step 10: the tag</h1>
<p>The swap works, and it feels apart from the fight. Today's tag, then four things it could become. Each row shows the input, three frames of play, the HUD part and the rule in one line.</p></div>
{rows()}
{REC}
<p class="foot">Original vector art. The pad is a generic drawing, not a real controller. Fonts: Bricolage Grotesque, Source Sans 3 (SIL OFL). Fighters and foes are placeholders; every number is a first value to try.</p>
</div></body></html>"""


def main():
    (HERE / "step10.html").write_text(html(), encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
        page.goto((HERE / "step10.html").as_uri())
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(400)
        page.locator("#c").screenshot(path=str(HERE / "preview" / "step10-tag.png"), type="png")
        print("sheet height", page.evaluate("document.getElementById('c').offsetHeight"))
        browser.close()


if __name__ == "__main__":
    main()
