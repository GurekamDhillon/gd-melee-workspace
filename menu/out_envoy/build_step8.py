#!/usr/bin/env python3
"""Envoy UI, step 8: the macro loop. Three ways to give a run a road, a reward economy and a reason to come back.

A choice sheet, not final screens: for each of M1 (forked road), M2 (regions) and M3 (dares) one line, the
shape of one loop, and a mock of its deciding screen in the final kit; then the camp's goals and collection,
and a recommendation. Writes:

  step8.html                    the source, beside this file
  preview/step8-macro.png       the sheet

Original vector art only. Fighters, foes, regions, bosses and stages are placeholders with invented names.
Fonts: Bricolage Grotesque and Source Sans 3 (SIL OFL). Design note: scratch/envoy-notes/envoy-macro-loop.md.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

import build_final as bf
import build_step2 as s2
import build_step3 as s3
import build_step4 as s4
import build_step6 as s6
import build_step7 as s7
from build_step2 import svg, SUN, INK, WHITE, CORAL, LAGOON, LILAC, STAR
from build_step3 import at, say, ptr, cur, frame, fcard, lock
from build_step4 import pog, ttl, FAM, BG, BG2
from build_step5 import coin
from build_step6 import kicon, KINDS
from build_final import H, kpill
from build_step7 import lstrip, stocks, best, ptok, ktok, geo, mark, KEYS, PALE

HERE = Path(__file__).resolve().parent

CSS8 = r"""
/* ---------- step 8: game pixels ---------- */
.fk8{overflow:hidden}
.fk8 .hd8{position:absolute;left:0;top:0;right:0;height:46px;border-bottom:2px dashed rgba(42,26,110,.3)}
.fk8 .fr8{position:relative;height:40px}
.rw{display:flex;align-items:center;gap:3px;white-space:nowrap}
.rw svg{display:block;flex:none}
.rw .bn{font-size:13px;line-height:15px;margin:0 4px 0 1px}
.dg8{display:inline-flex;gap:3px;vertical-align:middle}
.dg8 i{width:9px;height:9px;border-radius:50%;border:2px solid #2A1A6E;background:#fff;display:block}
.dg8 i.y{background:#FF4D6D}
.dr8{position:absolute;left:30px;width:580px;height:54px;background:#fff;border:3px solid #2A1A6E;border-radius:12px;box-shadow:3px 4px 0 #2A1A6E}
.dr8.on{left:42px}
.rg{position:absolute;width:62px;height:62px;border-radius:50%;background:#fff;border:3px solid #2A1A6E;box-shadow:3px 4px 0 #2A1A6E;display:flex;align-items:center;justify-content:center}
.rg.dn{background:#DAD7E8}
.rg svg{display:block}
.rgl{position:absolute;width:120px;text-align:center;color:#fff;font-family:"Brico";font-weight:800;font-size:13px;line-height:15px;white-space:nowrap}
.rgl span{display:block;font-family:"SS3";font-weight:700;font-size:11px;line-height:12px;color:#C9BFF5}
.gl{position:absolute;left:290px;width:330px;height:60px;background:#fff;border:3px solid #2A1A6E;border-radius:12px;box-shadow:3px 4px 0 #2A1A6E}
.kv{display:grid;grid-template-columns:62px 1fr;gap:5px 6px;align-items:start}
.kv .b13{line-height:14px}

/* ---------- step 8: the sheet ---------- */
.m8{display:grid;grid-template-columns:1fr 640px;gap:20px 44px;align-items:start}
.m8 h3,.meta8 h3{font-weight:900;font-size:20px;line-height:26px;margin-bottom:6px}
.m8 h3 span,.meta8 h3 span{font-weight:600;font-size:15px;color:#45425E;margin-left:9px}
.dia{background:#F6F5FA;border-radius:18px;padding:12px 14px 8px}
.dia svg{display:block}
.fx8{display:grid;grid-template-columns:1fr 1fr;gap:12px 30px;margin-top:16px}
.fx8 b{display:block;font-weight:900;font-size:15.5px;color:#1A1830;margin-bottom:1px}
.fx8 p{font-size:15px;line-height:1.36;color:#45425E}
.econ{display:grid;grid-template-columns:repeat(4,1fr);gap:12px 26px;background:#F6F5FA;border-radius:14px;padding:14px 18px;margin-bottom:38px}
.econ div{display:grid;grid-template-columns:30px 1fr;gap:9px;align-items:start;font-size:14.5px;line-height:1.32;color:#45425E}
.econ b{color:#1A1830;font-weight:900;display:block}
.econ svg{display:block;margin-top:1px}
.meta8{display:grid;grid-template-columns:640px 1fr;gap:20px 44px;align-items:start}
.rec8{background:#2A1A6E;color:#F4F1FF;border-radius:18px;padding:26px 30px 24px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:34px}
.rec8 h2{font-size:25px;line-height:1.15;margin-bottom:8px;color:#FFD84A}
.rec8 p{font-size:16.5px;line-height:1.42;max-width:none}
.rec8 p+p{margin-top:8px}
.rec8 b{font-weight:900;color:#FFD84A}
.rec8 ol{margin:0 0 0 20px;font-size:16.5px;line-height:1.42}
.rec8 li{margin-bottom:4px}
"""
bf.CSS = bf.CSS + CSS8

GREY = "#45425E"
DASH29 = 'stroke-dasharray="2 9"'
DASH17 = 'stroke-dasharray="1 7"'


# ------------------------------------------------------------------ reward tokens (the bank's vocabulary, extended)
def utok(size=18):
    """A level-up: coral, a white arrow."""
    return svg(size, size, "-12.5 -12.5 25 25", f'<circle r="8.6" fill="{CORAL}" stroke="{INK}" stroke-width="2.2"/><path d="M0,-5 L5,1 H2 V5 H-2 V1 H-5Z" fill="#fff"/>')


def stok(size=18):
    """A stock: the stock dot on ink."""
    return svg(size, size, "-12.5 -12.5 25 25", f'<circle r="9.4" fill="{INK}"/><circle r="4.8" fill="#fff"/>')


def ftok(fam, size=18):
    """A pick from one family: the family's badge."""
    return svg(size, size, "-12.5 -12.5 25 25", f'<g transform="translate(-9.5 -9.5)">{pog(fam, 19, 0, sq=False)}</g>')


def rtok(size=18):
    """A pick that is Rare or better: the reward badge with the thick white die-cut and a star."""
    return svg(size, size, "-12.5 -12.5 25 25", f'<circle r="10.6" fill="#fff" stroke="{INK}" stroke-width="1.6"/><circle r="6.6" fill="{SUN}" stroke="{INK}" stroke-width="1.8"/>'
               f'<path transform="scale(.36)" d="{STAR}" fill="{INK}"/>')


def ltok(size=18):
    """One more drive slot: a dashed seat with a plus."""
    return svg(size, size, "-12.5 -12.5 25 25", f'<circle r="8.6" fill="#FBF6DD" stroke="{INK}" stroke-width="2.2" stroke-dasharray="3.2 2.4"/><path d="M0,-4.2V4.2M-4.2,0H4.2" stroke="{INK}" stroke-width="2.4" stroke-linecap="round"/>')


def rw(*items):
    """A row of rewards: tokens, and words where a number is needed."""
    return '<div class="rw">' + "".join(i if i.startswith("<svg") else f'<span class="bn">{i}</span>' for i in items) + "</div>"


def danger(n):
    return '<span class="dg8">' + "".join(f'<i class="{"y" if i < n else ""}"></i>' for i in range(3)) + "</span>"


def bg(body=""):
    return svg(854, 480, "-107 0 854 480", f'<rect x="-107" width="854" height="480" fill="{BG}"/>{body}', 'class="sc"')


def pointer(pos):
    return at(16 + 3 + geo(False)["xs"][pos] - 13, 50, svg(26, 14, "0 0 26 14", f'<path d="M13,2 L22,12 H4Z" fill="{CORAL}" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>'), "z-index:4")


# ------------------------------------------------------------------ M1. the forked road
def fposter(x, y, name, word, dg, sub, fights, bank, words, on=False, rot=0):
    rows = ""
    for i, (kind, label, who, where) in enumerate(fights):
        rows += (f'<div class="fr8"><div style="position:absolute;left:0;top:5px">{kicon(kind, 28)}</div>'
                 f'<div class="s10" style="position:absolute;left:34px;top:5px">Fight {i + 1}</div><div class="bn" style="position:absolute;left:34px;top:17px;font-size:15px;line-height:17px;letter-spacing:-.2px">{label}</div>'
                 f'<div style="position:absolute;left:90px;top:5px"><div class="b13" style="white-space:nowrap">{who}</div><div class="s10">{where}</div></div></div>')
    return (f'<div class="st fk8{" on" if on else ""}" style="left:{x}px;top:{y}px;width:194px;height:262px;transform:rotate({rot}deg)">'
            f'<div class="hd8"><div class="bn" style="position:absolute;left:8px;top:3px;font-size:19px;line-height:22px;letter-spacing:-.4px;white-space:nowrap">{name}</div>'
            f'<div class="s10" style="position:absolute;left:9px;top:28px;color:{INK}">{word} {danger(dg)}</div></div>'
            f'<div style="position:absolute;left:8px;top:48px;width:174px">{rows}</div>'
            f'<div style="position:absolute;left:8px;top:171px;width:174px;border-top:2px dashed rgba(42,26,110,.3);padding-top:5px">'
            f'<div class="s10" style="margin-bottom:3px">You bank</div>{bank}<div class="b13" style="margin-top:4px;line-height:14px">{words}</div>'
            f'<div class="s10" style="margin-top:4px;white-space:normal;line-height:13px">{sub}</div></div></div>')


def fork():
    p = [s6.bg_road(), lstrip(16, 8, 3, 0), pointer(0)]
    p.append(fposter(14, 72, "Open road", "Calm", 1, "Plain fights.",
                     [("duel", "Duel", "Fighter H", "Stage 2"), ("pack", "Pack", "Two fighters", "Stage 4"), ("duel", "Duel", "Fighter M", "Stage 7")],
                     rw(ptok(), ptok(), ptok()), "3 drive picks", rot=-1))
    p.append(fposter(223, 68, "Swarm road", "Rough", 2, "Small foes drop drives more often.",
                     [("pack", "Waves", "Small foes", "Stage 5, 3 waves"), ("pack", "Pack", "Three fighters", "Stage 4"), ("pack", "Waves", "Small foes", "Stage 1, 4 waves")],
                     rw(ptok(), ptok(), coin(18), "90"), "2 drive picks, 90 coins", on=True))
    p.append(fposter(432, 72, "Steep road", "Steep", 3, "Every foe carries one more drive.",
                     [("duel", "Duel", "Fighter R", "Stage 3"), ("shift", "Shift", "Two fighters", "Stage 6 to 8"), ("elite", "Elite", "Fighter T", "Stage 9")],
                     rw(ptok(), rtok(), utok()), "A pick, a Rare pick, a level-up", rot=1))
    p.append(cur(390, 316, 1))
    sk, w = stocks(16, 346, 5, 7, rot=-1.2)
    p += [sk, s6.purse(16 + w + 12, 347, 31, w=96, note="Coins", rot=1), kpill(16 + w + 124, 349, KEYS[0], -1.5), kpill(16 + w + 124, 378, KEYS[1], 1.2),
          at(448, 352, f'<div class="s10" style="color:{PALE}">Next stop sells</div><div style="margin-top:4px">{rw(utok(), stok())}</div>')]
    p += [say("Three roads to the next stop. You see every fight and what it banks."), H(("Left / Right", "Choose"), ("A", "Take the Swarm road"), ("Y", "Read your drives"), ("Start", "Pause"))]
    return frame("".join(p))


# ------------------------------------------------------------------ M2. regions
REG = {"meadow": ("Sunny Meadow", "util"), "gale": ("Gale Pass", "wind"), "cinder": ("Cinder Flats", "fire"), "frost": ("Frostmere", "frost"),
       "clock": ("Clockwork Yard", "bolt"), "hollow": ("The Hollow", "tech")}


def rnode(k, x, y, st="", note="", top=False):
    name, fam = REG[k]
    ring = "box-shadow:0 0 0 3px #fff,4px 6px 0 3px #2A1A6E;background:#FFD84A;" if st == "on" else ""
    face = pog(fam, 36, 0, sq=False)
    extra = ""
    if st == "done":
        extra = at(38, -8, svg(26, 26, "-13 -13 26 26", f'<circle r="10.5" fill="{INK}" stroke="#fff" stroke-width="2.4"/><path d="M-4.4,.4L-1.2,3.6L4.8,-3.4" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>'))
    if st == "lock":
        face = lock(22, LILAC)
    return (f'<div class="rg{" dn" if st in ("done", "lock") else ""}" style="left:{x - 31}px;top:{y - 31}px;{ring}">{face}{extra}</div>'
            f'<div class="rgl" style="left:{x - 60}px;top:{y - 66 if top else y + 39}px">{name}<span>{note}</span></div>')


def region():
    P = {"meadow": (62, 318), "gale": (166, 250), "cinder": (62, 150), "frost": (182, 150), "clock": (290, 262), "hollow": (292, 76)}
    ln = lambda a, b, dash=True, col="#fff", op=.9: (f'<path d="M{P[a][0]},{P[a][1]} L{P[b][0]},{P[b][1]}" stroke="{col}" stroke-width="4" stroke-linecap="round" '
                                                     f'{DASH29 if dash else ""} opacity="{op}" fill="none"/>')
    roads = (ln("meadow", "gale", False, INK, 1) + ln("gale", "cinder") + ln("gale", "frost", False, SUN, 1) + ln("gale", "clock") + ln("frost", "hollow", op=.4) + ln("cinder", "frost", op=.4))
    p = [bg(s6.stars_bg(((-60, 40, 2), (566, 24, 1.8), (706, 70, 2.2))) + f'<ellipse cx="150" cy="420" rx="360" ry="120" fill="{BG2}"/><rect x="-107" y="392" width="854" height="88" fill="#33257C"/>{roads}')]
    p.append(ttl("Loop 3: choose a region", 14, 4, 22))
    p += [rnode("meadow", *P["meadow"], "done", "Loop 1"), rnode("gale", *P["gale"], "done", "Loop 2"), rnode("cinder", *P["cinder"], "", "Fire, Technique"),
          rnode("frost", *P["frost"], "on", "Frost, Wind", top=True), rnode("clock", *P["clock"], "", "Lightning, Utility"), rnode("hollow", *P["hollow"], "lock", "Opens at loop 5")]
    p.append(cur(200, 160, 1))
    kv = lambda k, v: f'<div class="s10" style="padding-top:1px">{k}</div><div class="b13">{v}</div>'
    drops = f'<span style="display:inline-flex;gap:3px;vertical-align:-4px">{ftok("frost", 17)}{ftok("wind", 17)}</span> twice as often'
    p.append(f'<div class="st" style="left:354px;top:46px;width:272px;height:326px;transform:rotate(.8deg);overflow:hidden">'
             f'<div style="position:absolute;left:0;top:0;width:266px;height:54px;background:{SUN};border-bottom:3px solid {INK}">'
             f'<div class="hl" style="position:absolute;left:10px;top:4px;font-size:24px;line-height:27px">Frostmere</div><div class="s10" style="position:absolute;left:11px;top:34px;color:{INK}">Loop 3, five fights</div>'
             f'<div style="position:absolute;right:8px;top:9px">{pog("frost", 34, 0, sq=False)}</div></div>'
             f'<div class="kv" style="position:absolute;left:10px;top:63px;width:246px">'
             + kv("Stages", "Stage 3, Stage 6, Stage 9") + kv("Foes", "Heavy fighters, ice crawlers") + kv("Rule here", "Chill lasts twice as long, on foes and on you.")
             + kv("Drops", drops) + kv("Elite", "Fighter K: Frost, Shatter") + kv("Boss", "Boss 3, in the Ice arena") + "</div>"
             f'<div style="position:absolute;left:10px;top:254px;width:246px;border-top:2px dashed rgba(42,26,110,.3);padding-top:6px">'
             f'<div class="s10" style="margin-bottom:3px">Clearing it banks</div>{rw(ktok(), ltok(), stok())}<div class="b13" style="margin-top:4px;line-height:14px">A keystone, a drive slot, a stock</div></div></div>')
    p += [say("One region a loop. It sets the stages, the foes, the drops and the boss."), H(("Stick", "Choose"), ("A", "Go to Frostmere"), ("Y", "Read your drives"), ("Start", "Pause"))]
    return frame("".join(p))


# ------------------------------------------------------------------ M3. dares
def drow(y, name, rule, bank, words, dg, on=False, rot=0, plain=False):
    left = (f'<div class="bn" style="position:absolute;left:12px;top:5px;font-size:18px;line-height:21px;letter-spacing:-.3px;white-space:nowrap">{name}'
            + (f'<span style="margin-left:8px">{danger(dg)}</span>' if dg else "") + "</div>"
            f'<div class="b13" style="position:absolute;left:12px;top:28px;white-space:nowrap;color:{INK if on else LILAC}">{rule}</div>')
    right = "" if plain else (f'<div style="position:absolute;left:386px;top:6px;width:180px;border-left:2px dashed rgba(42,26,110,.3);padding-left:10px;height:36px">'
                              f'<div class="s10" style="margin-bottom:2px{";color:" + INK if on else ""}">Prize at the stop</div><div style="display:flex;align-items:center;gap:5px">{bank}<span class="b13" style="white-space:nowrap">{words}</span></div></div>')
    return f'<div class="dr8{" on" if on else ""}" style="top:{y}px;transform:rotate({0 if on else rot}deg)">{left}{right}</div>'


def dare():
    p = [s6.bg_road(), lstrip(16, 8, 3, 0), pointer(0)]
    p.append(ttl("A dare for fights 1 to 3?", 28, 62, 19))
    p.append(drow(98, "Big foes", "Foes are larger and hit 25% harder.", rw(rtok()), "A Rare pick", 2, rot=-.5))
    p.append(drow(160, "No bench", "No tagging. Your main fights all three alone.", rw(coin(18)), "120 coins", 2, on=True))
    p.append(ptr(10, 174))
    p.append(drow(222, "Bruised", "You start every fight at 40%.", rw(utok(), utok()), "Two level-ups", 3, rot=.5))
    p.append(drow(284, "No dare", "The fights as they are. Each win still banks a drive pick.", "", "", 0, rot=-.4, plain=True))
    sk, w = stocks(30, 350, 5, 7, rot=-1.2)
    p += [sk, s6.purse(30 + w + 12, 351, 31, w=96, note="Coins", rot=1),
          at(292, 356, f'<div class="s10" style="color:{PALE}">Opens with goals</div><div class="b13" style="color:#fff;margin-top:3px">{lock(11, PALE)} Double dare: sign two at once</div>')]
    p += [say("A dare lasts the three fights. Its prize is banked when you reach the stop."), H(("Up / Down", "Choose"), ("A", "Sign No bench"), ("Y", "Read your drives"), ("Start", "Pause"))]
    return frame("".join(p))


# ------------------------------------------------------------------ the camp: goals, kit, bests
def goal(y, text, opens, prog, icon, rot):
    return (f'<div class="gl" style="top:{y}px;transform:rotate({rot}deg)"><div style="position:absolute;left:8px;top:11px">{icon}</div>'
            f'<div class="bn" style="position:absolute;left:46px;top:4px;font-size:14.5px;line-height:17px;letter-spacing:-.2px;white-space:nowrap">{text}</div>'
            f'<div class="b13" style="position:absolute;left:46px;top:22px;white-space:nowrap">Opens {opens}</div>'
            f'<div class="s10" style="position:absolute;left:46px;top:38px">{prog}</div></div>')


def camp8():
    items = [("go", "Start run", "A new run, from loop 1."), ("fighters", "Fighters", "2 each"), ("kit", "Kit", "Fire kit"), ("goals", "Goals", "3 open"),
             ("col", "Collection", "38 of 71"), ("ta", "Team attack", s3.switch(False)), ("back", "Back", "")]
    rots = [-1.2, .9, -.7, 1, -.9, .7, -1.1]
    p, y = [s3.scene(1), s3.title()], 58
    for i, (k, lab, val) in enumerate(items):
        on = k == "goals"
        cls = "row" + (" big" if k == "go" else "") + (" back" if k == "back" else "") + (" on" if on else "")
        v = f'<span class="v">{val}</span>' if val else ""
        p.append(f'<div class="{cls}" style="top:{y}px;transform:rotate({0 if on else rots[i]}deg)"><span class="l">{lab}</span>{v}</div>')
        if on:
            p.append(ptr(10, y + 2))
        y += 62 if k == "go" else 36
    head = lambda kind: svg(32, 36, "0 0 40 56", f'<g fill="#BFC2CE" stroke="{INK}" stroke-width="3" stroke-linejoin="round"><path d="{s3.SILS[kind][0]}"/>{s3.SILS[kind][1]}</g>')
    p.append(goal(58, "Reach loop 5", "Fighter N", "Best so far: loop 4", head(4), -.6))
    p.append(goal(128, "Beat a boss with three Frost drives", "the drive Glacier", "Not done yet", svg(32, 32, "0 0 32 32", f'<g transform="translate(1 1)">{pog("frost", 30, 1, sq=False)}</g>'), .5))
    p.append(goal(198, "Win an elite fight without tagging", "the Relay kit", "Not done yet", svg(32, 32, "-16 -16 32 32", f'<rect x="-12" y="-9" width="24" height="19" rx="4" fill="{SUN}" stroke="{INK}" stroke-width="2.6"/><path d="M-6,-9 V-13 H6 V-9" fill="none" stroke="{INK}" stroke-width="2.6"/>'), -.4))
    p.append(best(294, 274, 4, rot=-1.5))
    p.append(f'<div class="st" style="left:438px;top:272px;height:30px;transform:rotate(1.2deg);display:flex;align-items:center;padding:0 9px;white-space:nowrap"><span class="bn" style="font-size:13px;line-height:15px">A and B together: loop 3</span></div>')
    p += [say("Three goals at a time. Each opens a fighter, a drive, a keystone or a kit."), H(("Up / Down", "Choose"), ("A", "See every goal"), ("B", "Main menu"), ("Start", "Start run"))]
    return frame("".join(p))


def kitcard(x, y, name, parts, note, locked=False, on=False, rot=0):
    body = "".join(f'<span style="display:flex;align-items:center;gap:4px">{i}<span class="b13" style="white-space:nowrap">{t}</span></span>' for i, t in parts)
    lk = f'<div style="position:absolute;right:8px;top:7px">{lock(13, LILAC)}</div>' if locked else ""
    return (f'<div class="st{" on" if on else ""}" style="left:{x}px;top:{y}px;width:188px;height:104px;transform:rotate({rot}deg);{"background:#DAD7E8;" if locked else ""}">{lk}'
            f'<div class="bn" style="position:absolute;left:9px;top:5px;font-size:16px;line-height:19px;letter-spacing:-.3px">{name}</div>'
            f'<div style="position:absolute;left:9px;top:29px;display:flex;flex-direction:column;gap:4px">{body}</div>'
            f'<div class="s10" style="position:absolute;left:9px;top:82px">{note}</div></div>')


def meta_parts():
    lb = bf.lb
    kem = lambda k: bf.kem(k, 19)
    o = lb(16, 12, "Kit: what a run starts with. Every kit is one Common drive and one keystone; none is stronger, they are different.")
    o += kitcard(16, 34, "Plain kit", [(ptok(19), "Pick of three drives"), (ktok(19), "Pick of three keystones")], "Open from the start", rot=-.6)
    o += kitcard(222, 34, "Fire kit", [(ftok("fire", 19), "Ember"), (kem("Plague Bearer"), "Plague Bearer")], "Opened: reach loop 2", on=True)
    o += kitcard(428, 34, "Relay kit", [(ftok("wind", 19), "Slipstream"), (kem("Twin Soul"), "Twin Soul")], "Win an elite without tagging", locked=True, rot=.6)
    o += lb(16, 160, "Collection: everything seen is kept with its text. Locked things show what opens them.")
    for i, (n, c) in enumerate((("Drives", "22 of 40"), ("Keystones", "5 of 9"), ("Fighters", "21 of 26"), ("Kits", "2 of 6"), ("Roads and dares", "6 of 12"))):
        w = (104, 118, 112, 88, 150)[i]
        x = (16, 128, 254, 374, 470)[i]
        o += (f'<div class="st" style="left:{x}px;top:182px;width:{w}px;height:44px;transform:rotate({(-.8, .6, -.5, .7, -.6)[i]}deg);padding:4px 8px"><div class="s10">{n}</div>'
              f'<div class="bn" style="font-size:16px;line-height:19px;white-space:nowrap">{c}</div></div>')
    o += lb(16, 248, "Bests: the highest loop, kept overall, for each pair of fighters, and for the daily road (one seed a day, one try).")
    o += best(16, 270, 4, rot=-1)
    for i, t in enumerate(("A and B: loop 3", "C and D: loop 2", "Daily road: loop 2")):
        o += (f'<div class="st" style="left:{(160, 300, 440)[i]}px;top:270px;height:30px;transform:rotate({(.8, -.6, .7)[i]}deg);display:flex;align-items:center;padding:0 9px;white-space:nowrap">'
              f'<span class="bn" style="font-size:12.5px;line-height:15px">{t}</span></div>')
    return bf.pn("Kits, the collection and the bests", "What the camp's other rows open. Nothing here raises a number: a run with every goal done starts exactly as strong as the first one.", 640, 318, o, zoom=1.0)


# ------------------------------------------------------------------ the loop diagrams
T = lambda x, y, t, a="start", w=600, c=GREY, s=13.5: f'<text x="{x}" y="{y}" text-anchor="{a}" font-family="SS3" font-weight="{w}" font-size="{s}" fill="{c}">{t}</text>'
L = lambda d, c=INK, dash=False: f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round" {DASH17 if dash else ""}/>'


def choose(x, y, label):
    """Where the player decides: a coral A."""
    return (f'<circle cx="{x}" cy="{y}" r="12" fill="{CORAL}" stroke="{INK}" stroke-width="2.4"/><text x="{x}" y="{y + 5}" text-anchor="middle" font-family="Brico" font-weight="800" font-size="14" fill="#fff">A</text>'
            + T(x, y - 20, label, "middle", 900, "#1A1830"))


def tentm(x, y):
    return s6.tmark("rest", "done", x, y, 8)


def dia1():
    b = ""
    for ry in (52, 104, 156):
        b += L(f"M70,104 C100,104 110,{ry} 150,{ry} H300 C340,{ry} 350,104 380,104")
    for i, (ry, lab) in enumerate(((52, "Open: 3 picks"), (104, "Swarm: 2 picks, coins"), (156, "Steep: Rare pick, level-up"))):
        kinds = (("duel", "duel", "duel"), ("duel", "duel", "duel"), ("duel", "duel", "elite"))[i]
        for j, k in enumerate(kinds):
            b += mark(k, "todo", 170 + j * 55, ry, 8)
        b += T(152, ry - 15, lab, s=12.5)
    b += L("M380,104 H450") + tentm(380, 104)
    for ry in (70, 138):
        b += L(f"M450,104 C480,104 490,{ry} 530,{ry} C580,{ry} 590,104 640,104") + mark("elite", "todo", 540, ry, 8)
    b += T(556, 58, "Elite K: Wildfire, a stock", s=12.5) + T(556, 162, "Elite P: Echo, a level-up", s=12.5)
    b += L("M640,104 H770") + s6.tmark("boss", "todo", 660, 104, 9) + tentm(745, 104)
    b += choose(52, 104, "Road") + choose(450, 104, "Elite") + T(380, 132, "stop", "middle") + T(660, 132, "boss", "middle") + T(745, 132, "stop", "middle")
    b += T(790, 108, "loop + 1", s=12.5)
    return svg(830, 190, "0 0 860 190", b)


def dia2():
    disc = lambda x, y, fam, r=15: f'<circle cx="{x}" cy="{y}" r="{r}" fill="{FAM[fam][1]}" stroke="{INK}" stroke-width="2.6"/>'
    b = ""
    for ry in (48, 104, 160):
        b += L(f"M52,{ry} C100,{ry} 110,104 150,104", dash=ry != 104)
    b += f'<rect x="150" y="62" width="520" height="84" rx="22" fill="#DDF3FC" stroke="{INK}" stroke-width="2.6"/>'
    b += L("M196,104 H630")
    for j in range(3):
        b += mark("duel", "todo", 196 + j * 60, 104, 8)
    b += tentm(390, 104) + mark("elite", "todo", 460, 104, 8) + s6.tmark("boss", "todo", 540, 104, 9) + tentm(620, 104)
    b += T(168, 82, "Frostmere: its own stages, foes, drops, rule and boss", w=900, c="#1A1830") + T(390, 132, "stop", "middle") + T(620, 132, "stop", "middle") + T(540, 132, "boss", "middle")
    for i, fam in enumerate(("fire", "frost", "bolt")):
        b += disc(52, 48 + i * 56, fam)
    for ry in (48, 104, 160):
        b += L(f"M670,104 C720,104 730,{ry} 778,{ry}", dash=True)
    for i, fam in enumerate(("fire", "bolt", "tech")):
        b += disc(790, 48 + i * 56, fam)
    b += choose(108, 104, "") + choose(718, 104, "") + T(30, 20, "Choose 1 of 3 regions", w=900, c="#1A1830") + T(830, 20, "and again, next loop", "end", w=900, c="#1A1830")
    return svg(830, 190, "0 0 860 190", b)


def dia3():
    slips = lambda x, y: "".join(f'<rect x="{x - 13}" y="{y - 17}" width="26" height="34" rx="4" fill="#fff" stroke="{INK}" stroke-width="2.4" transform="rotate({r} {x} {y}) translate({dx} 0)"/>' for r, dx in ((-14, -16), (10, 16), (0, 0)))
    b = L("M60,104 H800")
    b += slips(60, 104)
    for j in range(3):
        b += mark("duel", "todo", 190 + j * 60, 104, 8)
    b += f'<path d="M172,128 V136 H328 V128" fill="none" stroke="{CORAL}" stroke-width="2.6" stroke-linejoin="round"/>' + T(250, 156, "the dare's rule is on", "middle", c="#1A1830")
    b += tentm(400, 104) + T(400, 132, "stop", "middle") + T(400, 74, "prize banked", "middle", 900, "#1A1830")
    b += slips(490, 104)
    b += mark("elite", "todo", 600, 104, 8) + s6.tmark("boss", "todo", 660, 104, 9)
    b += f'<path d="M582,128 V136 H678 V128" fill="none" stroke="{CORAL}" stroke-width="2.6" stroke-linejoin="round"/>' + T(630, 156, "rule on", "middle", c="#1A1830")
    b += tentm(750, 104) + T(750, 132, "stop", "middle") + T(750, 74, "prize banked", "middle", 900, "#1A1830")
    b += T(60, 58, "Sign 1 of 3, or none", "middle", 900, "#1A1830") + T(490, 58, "Sign 1 of 3, or none", "middle", 900, "#1A1830")
    b += f'<circle cx="60" cy="150" r="12" fill="{CORAL}" stroke="{INK}" stroke-width="2.4"/><text x="60" y="155" text-anchor="middle" font-family="Brico" font-weight="800" font-size="14" fill="#fff">A</text>'
    b += f'<circle cx="490" cy="150" r="12" fill="{CORAL}" stroke="{INK}" stroke-width="2.4"/><text x="490" y="155" text-anchor="middle" font-family="Brico" font-weight="800" font-size="14" fill="#fff">A</text>'
    b += T(812, 108, "loop + 1", s=12.5)
    return svg(830, 190, "0 0 860 190", b)


# ------------------------------------------------------------------ the sheet
def screens():
    return {"road-fork": fork(), "region-map": region(), "dare-pick": dare(), "camp-goals": camp8()}


def facts(*rows):
    return '<div class="fx8">' + "".join(f"<div><b>{k}</b><p>{v}</p></div>" for k, v in rows) + "</div>"


def html(S):
    sec = lambda t, lede, body: f'<div class="sec"><h2>{t}</h2><p class="lede">{lede}</p>{body}</div>'
    shot = lambda k, t, s, c: f'<div><h3>{t}<span>{s}</span></h3>{bf.shot(S[k], 1.0)}<p class="cap" style="max-width:640px">{c}</p></div>'
    left = lambda d, f: f'<div><h3>One loop<span>a coral A is a decision</span></h3><div class="dia">{d}</div>{f}</div>'
    econ = [(ptok(26), "Drive pick", "One of three. Every fight won banks one. The floor of every road."), (ftok("frost", 26), "Family pick", "One of three from one family. How a road or a region feeds a build."),
            (rtok(26), "Rare pick", "One of three, Rare or better. Only from danger: steep roads, dares, elites."), (utok(26), "Level-up", "Raise a drive you wear. The scarce one: late growth is levels."),
            (coin(26), "Coins", "Common. The shop turns them into anything, at a poor rate."), (stok(26), "Stock", "The run's life. Scarce: one elite a loop, the shop, a loop cleared."),
            (ltok(26), "Drive slot", "Bosses 1 and 2 only. Three slots become five."), (ktok(26), "Keystone", "Bosses only. Later bosses raise a keystone you hold.")]
    E = '<div class="econ">' + "".join(f"<div>{i}<span><b>{n}</b>{t}</span></div>" for i, n, t in econ) + "</div>"
    M1 = '<div class="m8">' + left(dia1(), facts(("You decide", "Which of three roads to the next stop, and which of two elites. Twice a loop, a few seconds each, at the stop you were already at."), ("New screens", "None. The road screen shows three narrow posters in place of one."), ("It needs", "Fight kinds that differ (duel, pack, shift room, waves, elite) and four reward kinds in the bank. Mostly planned already."), ("Two players", "Player 1 holds the cursor. Player 2 plants a flag on the road they want."), ("Endless loops", "From loop 2 a third road, from loop 4 roads with two twists and two prizes."), ("Size and risk", "Small. The risk is roads that differ only in numbers, so one is always right."))) + shot("road-fork", "M1. The forked road", "the stop before fights 1 to 3", "Three posters where the road screen had one. Each lists its fights and what it banks, so the trade is read in one look: the open road is three plain picks, the swarm road pays coins and drops, the steep road pays a Rare pick and a level-up.") + '</div>'
    M2 = '<div class="m8">' + left(dia2(), facts(("You decide", "The region for the whole loop, from three on offer. Once a loop, after the boss."), ("New screens", "The region map. A region name on the banner and the loop strip. A page in the collection."), ("It needs", "Five or six regions, each with stages, a wave mix, a rule, a drop tilt, an elite and a boss. Today there is one real boss."), ("Two players", "Player 1 holds the cursor. Player 2 plants a flag."), ("Endless loops", "A region met again is its deeper form: its rule doubled, its elite with one more drive."), ("Size and risk", "Large, and most of it is content. The risk is five regions that are one boss in five coats."))) + shot("region-map", "M2. Regions", "after the boss of loop 2", "A small map. The cursor is on Frostmere, so its sticker says what the loop will be: stages, foes, the region's rule, which drives drop, the elite, the boss and what clearing it banks.") + '</div>'
    M3 = '<div class="m8">' + left(dia3(), facts(("You decide", "Whether to sign a dare for the next session, and which. Twice a loop."), ("New screens", "The dare list, as the last step of the stop. A small ink tag in the fight HUD while a dare is on."), ("It needs", "Ten to twelve dares. Most are switches the rules already have: foe size and damage, one more foe, no tag, a starting percent."), ("Two players", "Both must hold A to sign. One player can never dare for the other."), ("Endless loops", "Dares come in three weights. Goals open the heavy ones and the double dare."), ("Size and risk", "Small to medium. The risk is that it reads as a punishment menu, and that always or never signing is right."))) + shot("dare-pick", "M3. Dares", "the stop before fights 1 to 3", "The road stays one line. A plain list, like the shop: three dares and No dare. A dare is a rule for the session and a prize banked at the next stop.") + '</div>'
    META = '<div class="meta8">' + shot("camp-goals", "The camp", "the Goals row hovered", "Two new rows, Kit and Goals, in the same list. Three goals show at a time; each names what it opens. The best loop sits under them, with the best of the pair you have picked.") + '<div style="padding-top:32px">' + meta_parts() + '</div></div>'
    REC = (f'<div class="rec8"><div><h2>Build M1, with dares as its twists</h2><p>The forked road is the plain one: no new screen, a choice read in one look, taken at a stop you were already at. '
           f'A steep road is a dare: its twist and its prize are printed on the poster, so M3 needs no list of its own.</p><p>Regions come last, as the coat a loop wears, once wave fights and a second boss exist.</p></div>'
           f'<div><h2>The smallest slice to play</h2><p>At the stop before fights 1 to 3, two posters. The open road: duel, pack, duel, three picks. '
           f'The steep road: the same three fights, every foe carries one more drive; it banks two picks and a level-up.</p><p>It uses only fights and rewards that exist. The new parts are a second poster, left and right, and a level-up token in the bank.</p></div>'
           f'<div><h2>Then, in this order</h2><ol><li>The elite fork: two elites, each showing the drive and the prize it banks.</li><li>Goals and bests at the camp.</li><li>Wave fights as the swarm road.</li><li>Kits.</li><li>Regions.</li></ol></div></div>')
    return bf.head("Envoy UI, step 8") + f"""<div id="c">
<div class="top"><h1>Step 8: where the run goes</h1>
<p>The fights are good. This sheet is the layer above them: three ways to give a run a road, different rewards, and a reason to start the next one. Screens are 640 by 480 game pixels at actual size.</p></div>
{sec("What a choice is for", "Today every reward is a drive pick. These eight are what a road can pay. Two are scarce on purpose, level-ups and stocks, so a road is about power, safety or money.", E)}
{sec("M1. The forked road", "At each stop the road splits into two or three posters. Pick one: you see its fights and what it banks.", M1)}
{sec("M2. Regions", "Each loop is one themed region picked from a small map. The region changes the stages, the foes, the drops and the boss.", M2)}
{sec("M3. Dares", "The road stays one line. Before each session you may sign a dare: a harder rule for those fights, and a prize at the stop.", M3)}
{sec("Between runs: goals, kits, bests", "The same for all three. Play opens things to play with. Nothing makes a fighter stronger before the run starts.", META)}
{REC}
<p class="foot">Original vector art. Fonts: Bricolage Grotesque, Source Sans 3 (SIL OFL). Fighters, foes, regions, bosses and stages are placeholders with invented names; prizes, prices and counts are made up for the mock.</p>
</div></body></html>"""


def main():
    S = screens()
    (HERE / "step8.html").write_text(html(S), encoding="utf-8")
    tmp = HERE / "step8-screens.tmp.html"
    tmp.write_text(bf.screens_html(S), encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
        page.goto((HERE / "step8.html").as_uri())
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(400)
        page.locator("#c").screenshot(path=str(HERE / "preview" / "step8-macro.png"), type="png")
        print("sheet height", page.evaluate("document.getElementById('c').offsetHeight"))
        pg = browser.new_page(viewport={"width": 700, "height": 600}, device_scale_factor=1)
        pg.goto(tmp.as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(400)
        for b in pg.evaluate(bf.CHECK):
            print(b)
        browser.close()
    tmp.unlink()


if __name__ == "__main__":
    main()
