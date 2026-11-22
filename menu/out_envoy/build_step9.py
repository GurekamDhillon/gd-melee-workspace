#!/usr/bin/env python3
"""Envoy UI, step 9: a look of its own for every drive (46), the Uniques (16), keystones (8) and actives (5).

One definition per drive (`parts`) makes both things the player sees: the 3D model (meshed with the primitives of
`envoy_drives/tools/make_drives.py`: bevelled prisms, plus the ring and ball this step adds) and the 2D glyph on the
sticker badge (the same parts, front on, white with an ink edge). So the orbiter, the HUD chip and the pick row
cannot drift apart.

Writes preview/step9-drives-a.png and -b.png, glyphs/<id>.svg and .png (64 px), and DRIVE-MODELS.md.
Everything here is original geometry computed by this script. Nothing is traced or adapted from any game.
usage: python build_step9.py
"""
import math
import random
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw

import build_step2 as s2
import build_step3 as s3
import build_step4 as s4
import build_final as bf
from build_step2 import svg, SUN, INK, STAR, BURST
from build_step4 import SPARK

HERE = Path(__file__).resolve().parent
PAPER, PAPER2, NIGHT = "#4C3D9E", "#43348F", "#140C33"
BRIGHT, DARK = "#BFE3F5", "#1C1740"
ACTIVE = "#3E6BFF"

# ---------------------------------------------------------------------------------------------- vectors, mesh
# The mesh primitives, atlas rows, part lists (DRIVES, UNIQUES) and tier/ascended treatments live in the game repo's
# envoy_drives/tools/drive_parts.py, which make_drives.py also meshes: the model and the glyph cannot drift.
import os, sys
for _p in (os.environ.get("GW_DRIVE_PARTS", ""), "E:/Projects/Melee Workspace/melee/pc/scripts/examples/envoy_drives/tools",
           "C:/melee-wt/drvmodels/pc/scripts/examples/envoy_drives/tools"):
    if _p and os.path.exists(os.path.join(_p, "drive_parts.py")):
        sys.path.insert(0, _p)
        break
import drive_parts as _dp  # noqa: E402
globals().update({k: v for k, v in vars(_dp).items() if not k.startswith("__")})


# ---------------------------------------------------------------------------------------------- flat-shaded drawing of a mesh
YAW, PITCH = -24, 11
def view(p, yaw=YAW, pit=PITCH):
    x, y, z = p
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw)); x, z = x*c + z*s, -x*s + z*c
    c, s = math.cos(math.radians(pit)), math.sin(math.radians(pit)); y, z = y*c - z*s, y*s + z*c
    return (x, y, z)

LIGHT = norm((-.45, .7, .6))
def faces(mesh, yaw=YAW, pit=PITCH, foil=False):
    out = []
    for a, b, c, t, rw in mesh.tris:
        A, Bq, C = view(a, yaw, pit), view(b, yaw, pit), view(c, yaw, pit)
        n = norm(cross(sub(Bq, A), sub(C, A)))
        if n[2] <= 0.02:
            continue
        k = .74 + .26*max(0.0, dot(n, LIGHT))
        if foil:
            hcol = [hexrgb(x) for x in s4.HOLO.split(",")]
            f = (math.atan2(n[1], n[0])/math.pi + 1)*2.999 + n[2]*2
            col = mix(hcol[int(f) % 6], hcol[(int(f)+1) % 6], f % 1)
            col = mix(col, (255, 255, 255), .15)
        else:
            col = ramp(rw, t)
        col = tuple(min(255, int(v*k + (18 if k > .93 else 0))) for v in col)
        out.append(((A[2]+Bq[2]+C[2])/3, [(A[0], -A[1]), (Bq[0], -Bq[1]), (C[0], -C[1])], col))
    out.sort(key=lambda f: f[0])
    return out


VB = 1.5
def draw(mesh, size, ow=2.2, mode="color", yaw=YAW, pit=PITCH, edge=INK, edge2=None, over="", under="", foil=False, vb=VB, cid=None):
    """An svg of the mesh. ow: outline in output px (the ink hull). mode 'black' is the silhouette test."""
    fs = faces(mesh, yaw, pit, foil)
    px = 2*vb/size
    pts = lambda f: " ".join(f"{x:.3f},{y:.3f}" for x, y in f[1])
    b = under
    if mode == "black":
        b += "".join(f'<polygon points="{pts(f)}" fill="#000" stroke="#000" stroke-width="{px*.6:.4f}"/>' for f in fs)
    else:
        if edge2:
            b += f'<g stroke="{edge2}" fill="{edge2}" stroke-width="{(ow*2+2.6)*px:.4f}" stroke-linejoin="round">' + "".join(f'<polygon points="{pts(f)}"/>' for f in fs) + "</g>"
        if ow:
            b += f'<g stroke="{edge}" fill="{edge}" stroke-width="{ow*2*px:.4f}" stroke-linejoin="round">' + "".join(f'<polygon points="{pts(f)}"/>' for f in fs) + "</g>"
        b += "".join(f'<polygon points="{pts(f)}" fill="rgb{f[2]}" stroke="rgb{f[2]}" stroke-width="{px*.5:.4f}" stroke-linejoin="round"/>' for f in fs)
        if cid:
            b += f'<clipPath id="{cid}">' + "".join(f'<polygon points="{pts(f)}"/>' for f in fs) + "</clipPath>"
    return svg(size, size, f"{-vb} {-vb} {2*vb} {2*vb}", b + over, 'style="overflow:visible"')


def raster(mesh, n=24, yaw=YAW, pit=PITCH):
    """The silhouette at orbit size as a set of pixels (for the too-alike check)."""
    S = n*6
    im = Image.new("L", (S, S), 0); d = ImageDraw.Draw(im)
    for _, f, _ in faces(mesh, yaw, pit):
        d.polygon([((x/1.08 + 1)*S/2, (y/1.08 + 1)*S/2) for x, y in f], fill=255)
    im = im.resize((n, n), Image.LANCZOS)
    return [v > 110 for v in im.tobytes()]


# ---------------------------------------------------------------------------------------------- the 46 drives


# ---------------------------------------------------------------------------------------------- badges (the kit's own helpers)
GLY = {}
_glyph0 = s4.glyph
def _glyph(f):
    return GLY[f] if f in GLY else _glyph0(f)
s4.glyph = _glyph          # pog() looks its glyph up through this name, so the kit's badge draws ours unchanged
for d in DRIVES:
    s4.FAM["d:" + d["key"]] = (FAMD[d["fam"]][1], FAMD[d["fam"]][3])
    GLY["d:" + d["key"]] = glyph_inner(d["parts"])

AGLY = {
    "volley": "".join(s4._solid(f"M{x},-7L{x+6.6},0L{x},7Z") for x in (-10.4, -3.4, 3.6)),
    "overdrive": s4._line("M-8,5A8,8 0 0 1 8,5", 2.5) + s4._solid("M-1.6,5L6.4,-5.4L1.6,6Z"),
    "detonate": f'<path transform="scale(.37)" d="{BURST}" fill="#fff" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/><circle r="2.6" fill="{INK}"/>',
    "recall": s4._line("M6.5,-8V0A4.5,4.5 0 0 1 2,4.5H-2", 2.5) + s4._solid("M-2,-.6L-9.4,4.5L-2,9.6Z"),
    "double_down": s4._line("M-7,-7.6L0,-1.8L7,-7.6M-7,.8L0,6.6L7,.8", 2.5),
}
ACTS = [("volley", "Volley", 3, "Every drive fires now, in order.", "Three darts in a line: the whole row, one after another."),
        ("overdrive", "Overdrive", 3, "5 s: Heat fills x2 and hits cost none.", "A gauge with its needle past the top."),
        ("detonate", "Detonate", 2, "Every word on every foe bursts and ends.", "A burst with a core: the words go off."),
        ("recall", "Recall", 2, "Warp to centre stage, safe for 1 s.", "An arrow that turns back."),
        ("double_down", "Double Down", 4, "Heat to the top. A hit in 5 s loses it all.", "Two chevrons down: the stake, doubled.")]
for k, *_ in ACTS:
    s4.FAM["a:" + k] = ("Active", ACTIVE); GLY["a:" + k] = AGLY[k]


def badge(key, size, rar=None, halo=False):
    d = DK[key]
    return s4.pog("d:" + key, size, d["tier"] if rar is None else rar, halo, sq=False)

def abadge(key, size): return s4.pog("a:" + key, size, 0, False, sq=True)

def star(size, fill=SUN):
    return svg(size, size, "-12 -12 24 24", f'<path d="{STAR}" fill="{fill}" stroke="{INK}" stroke-width="2.6" stroke-linejoin="round"/>')

def asc_badge(key, size, rar=None):
    """Ascended: the same badge with the gold star riding its lower right edge."""
    s = max(9, size*.44)
    return (f'<span style="position:relative;display:inline-block;line-height:0">{badge(key, size, rar)}'
            f'<span style="position:absolute;right:{-s*.28:.1f}px;bottom:{-s*.24:.1f}px">{star(round(s))}</span></span>')

def ubadge(key, size):
    """The seventh treatment: a diamond cut (not round, not square, not a wedge), a black face, a rim in the Unique's
    own metal, and the glyph in that metal's light colour."""
    u = UK[key]
    dia = lambda r, a: f'<rect x="{-r}" y="{-r}" width="{2*r}" height="{2*r}" rx="{r*.2:.1f}" transform="rotate(45)" {a}/>'
    b = (dia(12.6, f'fill="#fff" stroke="{INK}" stroke-width="1.8"') + dia(10.9, f'fill="{u["c1"]}" stroke="{INK}" stroke-width="1.4"') + dia(8.9, f'fill="{NIGHT}"')
         + f'<g transform="scale(.74)">{glyph_inner(u["parts"], face=u["c2"] if hexrgb(u["c2"])[0] > 150 else "#F3F0F8", edge=NIGHT, ew=1.2)}</g>')
    return svg(size, size, "-19 -19 38 38", b)

def upip(size=8):
    return svg(size, size, "-6 -6 12 12", f'<rect x="-3.4" y="-3.4" width="6.8" height="6.8" transform="rotate(45)" fill="#fff" stroke="{INK}" stroke-width="2"/>')


# keystones: the five drawn emblems stay; three are new
KEYS = [("plague_bearer", "Plague Bearer", "Every 8% dealt adds Burning, to 3 stacks.", "To 6 stacks; your damage resets the timer.", "Three flames, one large."),
        ("glass_core", "Glass Core", "Heat fills twice as fast; you take 60% more.", "Heat fills x3; your gain cap is x6.", "A cut gem with a crack."),
        ("grand_finale", "Grand Finale", "Smash attacks launch harder with Heat.", "Full strength at Blazing; a smash KO keeps half.", "A sixteen-point burst."),
        ("echo_oath", "Echo Oath", "Every drive fire repeats once at half.", "The repeat is at full strength.", "Two discs, one behind the other."),
        ("overclock", "Overclock", "Drives charge twice as fast.", "Drives charge x3.", "A dial with its hand past the last mark."),
        ("twin_soul", "Twin Soul", "The benched fighter's drives orbit and fire too.", "Both rows are one line; sets count across both.", "Two drops turning round each other."),
        ("winter_oath", "Winter Oath", "Your hits leave the foe Chilled for 2 seconds.", "Chill lasts 4 s; a smash freezes it solid.", "An ice crystal with a core."),
        ("all_in", "All In", "A KO keeps all Heat; a lost stock takes all.", "Blazing fires deal x2.5, not x2.", "One notched token: the whole stake.")]

def kem(k, size):
    name = {a: b for a, b, *_ in KEYS}.get(k, k)
    if k == "overclock":
        e = (f'<circle r="11.5" fill="#E9E4FF" stroke="{INK}" stroke-width="2.6"/>'
             + "".join(f'<path d="M0,-11.5V-8" transform="rotate({a})" stroke="{INK}" stroke-width="2.2" stroke-linecap="round"/>' for a in (-90, -45, 0, 45, 90))
             + f'<path d="M0,2L9.4,-4.4" stroke="{INK}" stroke-width="3" stroke-linecap="round"/><circle cy="2" r="2.6" fill="{INK}"/>'
             + f'<path transform="translate(12 -11.5)" d="{SPARK}" fill="{SUN}" stroke="{INK}" stroke-width="1.5" stroke-linejoin="round"/>')
    elif k == "twin_soul":
        drop = "M0,-11C6,-5 7,-1 7,2.4A7,7 0 0 1 -7,2.4C-7,-1 -6,-5 0,-11Z"
        e = (f'<path d="{drop}" transform="translate(-4.6 2.4) rotate(-20) scale(.82)" fill="{INK}" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round"/>'
             f'<path d="{drop}" transform="translate(4.6 -2.4) rotate(160) scale(.82)" fill="#C9BFF5" stroke="{INK}" stroke-width="2.8" stroke-linejoin="round"/>')
    elif k == "all_in":
        e = (f'<circle r="11.5" fill="{INK}"/>' + "".join(f'<path d="M-2.2,-12.4H2.2V-8.2H-2.2Z" transform="rotate({a})" fill="#fff"/>' for a in range(0, 360, 60))
             + f'<circle r="5.6" fill="#fff"/><circle r="2.6" fill="{INK}"/>')
    else:
        return bf.kem(name, size)
    return svg(size, size, "-21 -21 42 42", f'<circle r="18.5" fill="#fff" stroke="{INK}" stroke-width="3"/>{e}')

def kem_awake(k, size):
    """Awakened: the same emblem on a disc with a second ring and a spark, so it reads without the sunny wedge."""
    inner = kem(k, size)
    s = size/42
    return (f'<span style="position:relative;display:inline-block;line-height:0;width:{size}px;height:{size}px">'
            f'<span style="position:absolute;left:{-4*s:.1f}px;top:{-4*s:.1f}px">{svg(round(size + 8*s), round(size + 8*s), "-25 -25 50 50", f"""<circle r="23" fill="{SUN}" stroke="{INK}" stroke-width="2.4"/>""")}</span>'
            f'<span style="position:absolute;left:0;top:0">{inner}</span>'
            f'<span style="position:absolute;right:{-7*s:.1f}px;top:{-7*s:.1f}px">{svg(round(15*s), round(15*s), "-7 -7 14 14", f"""<path d="{SPARK}" fill="#fff" stroke="{INK}" stroke-width="1.6" stroke-linejoin="round"/>""")}</span></span>')

def kmini(k, awake=False):
    pts = "M3,3 H29 L25.5,23 H6.5Z"
    face = SUN if awake else INK
    return (f'<span style="position:relative;display:inline-block;width:32px;height:27px;line-height:0">'
            + svg(32, 27, "0 0 32 27", f'<path d="{pts}" fill="#fff" stroke="#fff" stroke-width="5" stroke-linejoin="round"/><path d="{pts}" fill="{face}" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>')
            + f'<span style="position:absolute;left:6.5px;top:3px">{kem(k, 19)}</span>'
            + (f'<span style="position:absolute;right:-5px;top:-5px">{svg(11, 11, "-7 -7 14 14", f"""<path d="{SPARK}" fill="#fff" stroke="{INK}" stroke-width="1.8" stroke-linejoin="round"/>""")}</span>' if awake else "") + "</span>")

def kwedge(k, name, rule, awake):
    a, _, b = name.partition(" ")
    w, h = 150, 196
    face, col = (SUN, INK) if awake else (INK, "#fff")
    return (f'<div class="kw9"><div class="kwb">{s4.wedge_svg(w, h, 18, face)}</div><div class="kwe">{(kem_awake if awake else kem)(k, 52)}</div>'
            f'<div class="kwt" style="color:{col}"><b>{a}<br>{b}</b><span>{rule}</span></div>'
            + ('<div class="kwf">Awakened</div>' if awake else "") + "</div>")


def orb(mesh, px, ow=1.2, x=False, **kw):
    """A model whose own box is px across. Returns (svg, drawn size): x=True uses the taller box for rings and stars."""
    tot = round(px*(AVB if x else VB))
    return draw(mesh, tot, ow, vb=AVB if x else VB, **kw), tot

def uorb(u, px, ow=1.0):
    tot = round(px*VB)
    return udraw(u, tot, ow, fx=False), tot

AVB = 1.86   # an ascended or tiered model needs a taller box; draw it at size*AVB/VB so the body keeps its scale
def drawx(mesh, size, ow, **kw):
    return draw(mesh, round(size*AVB/VB), ow, vb=AVB, **kw)


def glow_under(col, r=1.25, op=.55, uid="g"):
    return (f'<radialGradient id="{uid}"><stop offset=".25" stop-color="{col}" stop-opacity="{op}"/><stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient>'
            f'<circle r="{r}" fill="url(#{uid})"/>')


_uid = [0]
def udraw(u, size, ow=1.8, fx=True, mode="color"):
    """A Unique: dark body, double edge (ink then white), and a still of its material effect."""
    m = umesh(u)
    if mode == "black":
        return draw(m, size, 0, "black")
    _uid[0] += 1
    cid = f"uc{_uid[0]}"
    rnd = random.Random(u["key"])
    c2 = u["c2"] if hexrgb(u["c2"])[0] > 120 else u["c1"]
    over = under = ""
    k = u["fx"] if fx else None
    cl = lambda body: f'<g clip-path="url(#{cid})">{body}</g>'
    spark = lambda x, y, s, col="#fff", op=1: f'<path transform="translate({x:.2f} {y:.2f}) scale({s/5.5:.3f})" d="{SPARK}" fill="{col}" opacity="{op}"/>'
    if k == "pulse":
        over = cl(f'<linearGradient id="{cid}g" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".3" stop-color="#fff" stop-opacity=".95"/><stop offset=".55" stop-color="{c2}" stop-opacity=".4"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                  f'<rect x="-1.5" y="-1.1" width="2.2" height="1.5" fill="url(#{cid}g)"/>') + "".join(spark(-1.25 - i*.14, .1 - i*.2, .12 - i*.03, "#fff", .9 - i*.25) for i in range(3))
    elif k == "glow":
        under = glow_under(u["c2"], 1.45, .6, cid + "u")
        over = cl(f'<linearGradient id="{cid}g" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#FFD9A0" stop-opacity=".95"/><stop offset=".5" stop-color="{u["c2"]}" stop-opacity=".8"/><stop offset=".62" stop-color="{u["c2"]}" stop-opacity="0"/></linearGradient>'
                  f'<rect x="-1.5" y="-1.5" width="3" height="3" fill="url(#{cid}g)"/>') + "".join(f'<circle cx="{rnd.uniform(-.7, .7):.2f}" cy="{rnd.uniform(-1.45, -.7):.2f}" r="{rnd.uniform(.03, .06):.2f}" fill="#B9B6C4" opacity=".8"/>' for _ in range(9))
    elif k == "sheen":
        over = cl('<path d="M-.5,-1.6L.1,-1.6L-.9,1.6L-1.5,1.6Z" fill="#fff" opacity=".8"/><path d="M.34,-1.6L.52,-1.6L-.48,1.6L-.66,1.6Z" fill="#fff" opacity=".55"/>')
    elif k == "motes":
        over = cl("".join(f'<path d="M{x:.2f},{y:.2f}v.22" stroke="{c2}" stroke-width=".07" stroke-linecap="round" opacity=".9"/><circle cx="{x:.2f}" cy="{y:.2f}" r=".06" fill="#fff"/>'
                          for x, y in [(rnd.uniform(-.35, .35), rnd.uniform(-.7, .6)) for _ in range(12)]))
    elif k == "dissolve":
        sq = lambda x, y, s, col, op=1: f'<rect x="{x:.2f}" y="{y:.2f}" width="{s:.2f}" height="{s:.2f}" fill="{col}" opacity="{op}"/>'
        over = cl(f'<linearGradient id="{cid}g" x1="0" y1="0" x2="1" y2="1"><stop offset=".45" stop-color="#62CCF5" stop-opacity="0"/><stop offset=".6" stop-color="#fff"/><stop offset=".66" stop-color="#62CCF5"/><stop offset="1" stop-color="#62CCF5"/></linearGradient>'
                  f'<rect x="-1.5" y="-1.5" width="3" height="3" fill="url(#{cid}g)"/>' + "".join(sq(rnd.uniform(-.5, .5), rnd.uniform(-.5, .5), rnd.uniform(.08, .16), "#fff") for _ in range(16)))
        over += "".join(sq(rnd.uniform(-.2, 1.2), rnd.uniform(-1.4, -.5), rnd.uniform(.05, .1), "#D9D9E2", .8) for _ in range(9))
    elif k == "rings":
        over = cl("".join(f'<ellipse cx="-.1" cy="-.28" rx="{r:.2f}" ry="{r*1.35:.2f}" transform="rotate(28 -.1 -.28)" fill="none" stroke="{"#E9F5B8" if i < 3 else u["c2"]}" stroke-width=".07" opacity="{1 if i < 3 else .35}"/>' for i, r in enumerate((.1, .2, .3, .4))))
    elif k == "haze":
        wav = lambda y, a, op: f'<path d="M-1.35,{y} q.22,{-a} .45,0 t.45,0 t.45,0 t.45,0 t.45,0 t.45,0" fill="none" stroke="#fff" stroke-width=".06" opacity="{op}"/>'
        under = glow_under(u["c2"], 1.5, .35, cid + "u")
        over = wav(-1.2, .16, .6) + wav(-1.38, .12, .35) + wav(1.2, .12, .3) + cl(f'<circle cx="-.1" cy=".4" r=".34" fill="{u["c2"]}"/><circle cx="-.1" cy=".4" r=".6" fill="{u["c2"]}" opacity=".35"/>')
    elif k == "pattern":
        gear = lambda x, y, r: f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="{c2}" stroke-width=".07" stroke-dasharray=".1 .08"/><circle cx="{x}" cy="{y}" r="{r*.3:.2f}" fill="{c2}"/>'
        over = cl(gear(.5, -.1, .26) + gear(.02, .22, .2) + gear(.75, .38, .16) + gear(.3, .5, .12))
    elif k == "sparks":
        over = "".join(spark(x, y, s, "#fff") for x, y, s in ((1.2, -.5, .26), (.86, -.92, .16), (1.32, -.1, .12), (.5, -1.12, .1), (-.72, -1.05, .14), (-1.0, .62, .1)))
    elif k == "flow":
        over = cl('<path d="M-.5,.9C.3,.5 -.4,.1 .1,-.1S.4,-.6 -.2,-.9" fill="none" stroke="#fff" stroke-width=".16" opacity=".85" stroke-linecap="round"/>'
                  '<path d="M.5,.7C.1,.3 .5,0 .1,-.3" fill="none" stroke="#fff" stroke-width=".08" opacity=".6" stroke-linecap="round"/>')
    elif k == "trail":
        note = lambda x, y, s, op: f'<g transform="translate({x} {y}) scale({s})" opacity="{op}" fill="{u["c2"]}"><ellipse cx="0" cy=".3" rx=".2" ry=".15"/><rect x=".13" y="-.4" width=".07" height=".7"/></g>'
        under = note(-1.3, .9, 1.0, .9) + note(-1.05, 1.3, .7, .6) + note(-1.45, 1.4, .5, .35)
    elif k == "glitter":
        over = cl("".join(spark(rnd.uniform(-.8, .8), rnd.uniform(-.7, .8), rnd.uniform(.1, .26), rnd.choice(["#fff", "#FFF6B8"])) for _ in range(11)))
    elif k == "streak":
        under = "".join(f'<path d="M{x},{y} q-.6,.12 -1.1,{.5 + i*.05}" fill="none" stroke="#fff" stroke-width="{.09 - i*.015:.3f}" stroke-linecap="round" opacity="{.8 - i*.17:.2f}"/>'
                        for i, (x, y) in enumerate(((-.2, .7), (.3, .5), (.8, .25), (-.7, 1.0))))
    elif k == "scales":
        over = cl("".join(f'<path d="M-.11,0a.11,.11 0 0 0 .22,0" transform="translate({.68*math.cos(math.radians(a)):.2f} {.06 - .68*math.sin(math.radians(a)):.2f}) rotate({-a + 90})" fill="none" stroke="{"#E8FFF6" if 140 < a < 250 else "#1D2A28"}" stroke-width=".07"/>'
                          for a in range(84, 330, 14)))
    elif k == "foil":
        return draw(m, size, ow, edge=NIGHT, edge2="#fff", foil=True, cid=cid, over=cl('<path d="M-.3,-1.6L.0,-1.6L-.7,1.6L-1.0,1.6Z" fill="#fff" opacity=".55"/>'))
    return draw(m, size, ow, edge=NIGHT, edge2="#fff", over=over, under=under, cid=cid)


# ---------------------------------------------------------------------------------------------- the sheet
BASE9 = r"""
@font-face{font-family:"SS3";src:url("../SourceSans3/SourceSans3-Semibold.otf");font-weight:600}
@font-face{font-family:"SS3";src:url("../SourceSans3/SourceSans3-Bold.otf");font-weight:700}
@font-face{font-family:"SS3";src:url("../SourceSans3/SourceSans3-Black.otf");font-weight:900}
@font-face{font-family:"Brico";src:url("fonts/BricolageGrotesque.ttf");font-weight:200 800}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#E6E5EC}
body{width:1600px;font-family:"SS3";font-weight:600;color:#1A1830;-webkit-font-smoothing:antialiased}
#c{width:1600px}
.lede{color:#45425E;line-height:1.35}
"""

CSS9 = r"""
#c{padding:40px 40px 34px}
.top9{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:26px}
.top9 h1{font-family:"Brico";font-weight:800;font-size:50px;line-height:1;letter-spacing:-1.2px;color:#2A1A6E}
.top9 p{font-size:17.5px;line-height:1.35;max-width:760px;color:#45425E}
.s9{background:#F6F5FA;border-radius:16px;padding:22px 24px 24px;margin-bottom:26px}
.s9 h2{font-family:"Brico";font-weight:800;font-size:27px;letter-spacing:-.5px;color:#2A1A6E;margin-bottom:4px}
.s9 .lede{font-size:16px;margin-bottom:16px;max-width:1240px}
.note9{font-size:14px;line-height:1.35;color:#45425E}
.note9 b{color:#1A1830}
.lang{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}
.lg{background:#fff;border:3px solid #2A1A6E;border-radius:13px;box-shadow:3px 4px 0 #2A1A6E;padding:10px 12px 12px}
.lg .pair{display:flex;align-items:center;justify-content:space-between;height:96px;background:#E9E7F2;border-radius:9px;padding:0 10px;margin-bottom:9px}
.lg h3{font-family:"Brico";font-weight:800;font-size:18px;color:#2A1A6E;display:flex;align-items:center;gap:7px}
.lg h3 i{width:15px;height:15px;border-radius:50%;border:2.4px solid #2A1A6E;display:inline-block}
.lg .say{font-weight:700;font-size:14.5px;line-height:1.25;margin:5px 0 4px;color:#1A1830}
.lg .why{font-size:13px;line-height:1.3;color:#45425E}
.fam{display:flex;align-items:center;gap:12px;margin:0 0 12px}
.fam .sw{width:30px;height:30px;border-radius:50%;border:3px solid #2A1A6E}
.fam h2{margin:0}
.fam span{font-size:15.5px;color:#45425E}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.cd{position:relative;display:flex;gap:11px;background:#fff;border:3px solid #2A1A6E;border-radius:13px;box-shadow:3px 4px 0 #2A1A6E;padding:9px 10px 9px 9px;min-height:148px}
.cd .mo{flex:none;width:126px;height:126px;padding-right:14px;padding-bottom:10px;border-radius:9px;background:#4C3D9E;display:flex;align-items:center;justify-content:center;position:relative}
.cd .mo .ac{position:absolute;right:-1px;bottom:-3px;line-height:0}
.cd .tx{min-width:0;flex:1}
.cd .bd{display:flex;align-items:center;gap:8px;height:50px}
.cd .bd .ch{display:flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:8px;background:#4C3D9E}
.cd .nm{font-family:"Brico";font-weight:800;font-size:16.5px;line-height:18px;color:#2A1A6E;letter-spacing:-.3px;margin-top:3px;white-space:nowrap}
.cd .id{font-size:12px;line-height:14px;color:#5A4C99;font-weight:700}
.cd .ia{font-size:13px;line-height:15.5px;color:#1A1830;margin-top:4px}
.cd.u{background:#140C33;border-color:#140C33;box-shadow:0 0 0 2.5px #fff,3px 5px 0 2.5px #2A1A6E}
.cd.u .mo{background:#241A52}
.cd.u .nm{color:#fff}.cd.u .id{color:#C9BFF5}.cd.u .ia{color:#E9E4FF}
.cd.u .fxn{font-size:12.5px;line-height:15px;color:#C9BFF5;margin-top:4px}
.cd.u .fxn b{color:#fff;font-weight:700}
.rowp{display:flex;gap:14px;align-items:stretch;flex-wrap:wrap}
.pn{background:#4C3D9E;border-radius:13px;padding:14px 16px 14px;color:#fff}
.pn h4{font-family:"Brico";font-weight:800;font-size:16px;margin-bottom:8px;color:#fff}
.pn .pr{display:flex;gap:6px;align-items:flex-start}
.pn .it{display:inline-flex;flex-direction:column;align-items:center;gap:6px;margin-right:16px;vertical-align:top;font-size:12.5px;font-weight:700;color:#C9BFF5;text-align:center;line-height:14px}
.pn .it b{color:#fff}
.pn .it .bx{height:128px;display:flex;align-items:center;justify-content:center}
.sh{display:inline-block;background:#FFD84A;color:#2A1A6E;border:2px solid #2A1A6E;border-radius:8px;font-family:"Brico";font-weight:800;font-size:11.5px;line-height:13px;padding:1px 6px 2px;margin-bottom:5px}
.fb{font-size:12.5px;line-height:15px;color:#E9E4FF;max-width:268px;text-align:left;font-weight:600}
.fb b{color:#fff}
.kw9{position:relative;width:158px;height:206px;flex:none}
.kw9 .kwb{position:absolute;left:0;top:0;line-height:0}
.kw9 .kwe{position:absolute;left:49px;top:-16px}
.kw9 .kwt{position:absolute;left:20px;top:44px;width:110px;text-align:center}
.kw9 .kwt b{display:block;font-family:"Brico";font-weight:800;font-size:17px;line-height:18px;letter-spacing:-.3px}
.kw9 .kwt span{display:block;font-size:11.5px;line-height:13.5px;font-weight:700;margin-top:7px}
.kw9 .kwf{position:absolute;left:39px;bottom:22px;background:#fff;border:2px solid #2A1A6E;border-radius:8px;font-family:"Brico";font-weight:800;font-size:11px;color:#2A1A6E;padding:0 6px 1px}
.kgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px 14px}
.kc{display:flex;gap:10px;align-items:center;background:#fff;border:3px solid #2A1A6E;border-radius:12px;padding:8px 10px}
.kc b{font-family:"Brico";font-weight:800;font-size:15px;color:#2A1A6E;display:block;line-height:16px}
.kc span{font-size:12.5px;line-height:14.5px;color:#45425E;display:block}
.kc .hud{display:flex;gap:8px;align-items:center;background:#4C3D9E;border-radius:8px;padding:6px 8px}
.strip{display:flex;flex-wrap:wrap;gap:0;border-radius:10px;overflow:hidden}
.strip .fr{display:flex;align-items:center;gap:5px;padding:9px 10px}
.strip .fr + .fr{border-left:2px dashed rgba(128,128,160,.5)}
.lbl{font-size:13px;font-weight:700;color:#45425E;margin:10px 0 5px}
.mock{position:relative;width:640px;height:480px;border-radius:6px;overflow:hidden;flex:none;line-height:0}
.rec{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.rec div{background:#fff;border:3px solid #2A1A6E;border-radius:12px;padding:12px 14px;font-size:14.5px;line-height:1.35}
.rec b{font-family:"Brico";font-weight:800;font-size:16.5px;color:#2A1A6E;display:block;margin-bottom:3px}
.foot{font-size:13px;color:#5A5870;margin-top:6px}
.tg9{position:relative;background:#fff;border:3px solid #2A1A6E;border-radius:11px;box-shadow:3px 4px 0 #2A1A6E;padding:5px 10px 6px 12px;display:flex;gap:10px;align-items:center}
.tg9 b{font-family:"Brico";font-weight:800;font-size:16px;color:#2A1A6E;display:block;line-height:18px}
.tg9 span{font-size:12.5px;line-height:15px;color:#1A1830;font-weight:700;display:block}
.tg9.un{background:#140C33;border-color:#140C33;box-shadow:0 0 0 3px #fff,4px 6px 0 3px #2A1A6E}
.tg9.un b{color:#fff;font-size:21px;line-height:23px}.tg9.un span{color:#E9E4FF;font-size:14px;line-height:17px}
"""


def card(d):
    m = dmesh(d)
    return (f'<div class="cd"><div class="mo">{draw(m, 104, 2.4)}<span class="ac">{orb(m, 24, 1.3)[0]}</span></div><div class="tx">'
            f'<div class="bd">{badge(d["key"], 46)}<span class="ch">{badge(d["key"], 22, 0)}</span></div>'
            f'<div class="nm">{d["name"]}</div><div class="id">{TIERS[d["tier"]]}, {d["key"]}</div><div class="ia">{d["idea"]}</div></div></div>')


def ucard(u):
    return (f'<div class="cd u"><div class="mo">{udraw(u, 100, 2.0)}<span class="ac">{uorb(u, 24)[0]}</span></div><div class="tx">'
            f'<div class="bd">{ubadge(u["key"], 50)}<span class="ch" style="background:#4C3D9E">{ubadge(u["key"], 24)}</span></div>'
            f'<div class="nm">{u["name"]}</div><div class="ia">{u["rule"]}</div>'
            f'<div class="fxn"><b>Material:</b> {u["mat"]} <b>It says:</b> {u["says"]}</div></div></div>')


def lang_strip():
    out = ""
    for k, word, pool, col, *_ in FAMS:
        parts = GUARD_BASE if k == "guard" else DK[BASE[k]]["parts"]
        m = build(parts, k)
        say, why = LANG[k]
        out += (f'<div class="lg"><div class="pair">{draw(m, 76, 0, "black")}{orb(m, 24, 0, mode="black")[0]}{draw(m, 76, 2.2)}</div>'
                f'<h3><i style="background:{col}"></i>{word}</h3><div class="say">{say}</div><div class="why">{why}</div></div>')
    return f'<div class="lang">{out}</div>'


def nest(x, y, s):
    """Place an <svg ...> string inside another svg."""
    return f'<g transform="translate({x:.1f} {y:.1f})">{s}</g>'

def stext(x, y, t, size=11, fill=INK, anchor="middle", wt=700, fam="SS3"):
    return f'<text x="{x}" y="{y}" font-family="{fam}" font-weight="{wt}" font-size="{size}" fill="{fill}" text-anchor="{anchor}">{t}</text>'

def nametag(x, y, t):
    w = len(t)*5.6 + 10
    return (f'<rect x="{x - w/2:.1f}" y="{y - 7}" width="{w:.1f}" height="14" rx="5" fill="#fff" stroke="{INK}" stroke-width="2"/>' + stext(x, y + 3.6, t, 11))

def fighter(x, y, h=64, kind=0, fill="#BFC2CE"):
    w = h/1.4
    return nest(x - w/2, y - h, s3.sil(kind, round(w), fill))

def floor_drop(x, fy, model, name, unique=False):
    """Step 7's drop with the model in the badge's place: the white disc behind it, the sunny rings on the floor.
    model: (svg, size) from orb()."""
    msvg, tot = model
    ring = (f'<ellipse cx="{x}" cy="{fy + 1}" rx="21" ry="6.5" fill="none" stroke="{INK}" stroke-width="6.5"/><ellipse cx="{x}" cy="{fy + 1}" rx="21" ry="6.5" fill="none" stroke="{"#fff" if unique else SUN}" stroke-width="3"/>'
            f'<ellipse cx="{x}" cy="{fy + 1}" rx="33" ry="10" fill="none" stroke="{"#fff" if unique else SUN}" stroke-width="2" opacity=".45"/>')
    if unique:
        beam = (f'<linearGradient id="bm{x}" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#fff" stop-opacity=".85"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                f'<rect x="{x - 5}" y="{fy - 150}" width="10" height="150" fill="url(#bm{x})"/><rect x="{x - 1.5}" y="{fy - 150}" width="3" height="150" fill="url(#bm{x})"/>')
        disc = f'<rect x="-13" y="-13" width="26" height="26" rx="3" transform="translate({x} {fy - 27}) rotate(45)" fill="{NIGHT}" stroke="#fff" stroke-width="2.4"/>'
    else:
        beam = ""
        disc = f'<circle cx="{x}" cy="{fy - 27}" r="15" fill="#fff" stroke="{INK}" stroke-width="2.4"/>'
    return beam + ring + disc + nest(x - tot/2, fy - 27 - tot/2, msvg) + nametag(x, fy - 54 - (6 if unique else 0), name)


def orbit(cx, cy, items, rx=50, ry=13, phase=20):
    """Five drives round a fighter. Returns (behind, front) svg: the far half is drawn before the fighter.
    items: functions of the model size in px returning (svg, drawn size)."""
    back = front = ""
    n = len(items)
    path = f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="#fff" stroke-width="1" stroke-dasharray="2 4" opacity=".35"/>'
    for i, fn in enumerate(items):
        a = math.radians(phase + 360*i/n)
        x, y = cx + rx*math.cos(a), cy + ry*math.sin(a)
        near = math.sin(a) > 0
        msvg, tot = fn(26 if near else 21)
        s = nest(x - tot/2, y - tot/2, msvg)
        if near: front += s
        else: back += s
    return path + back, front


def stage(bright):
    if bright:
        return ('<rect width="640" height="480" fill="#BFE3F5"/><rect y="300" width="640" height="180" fill="#A5D3EC"/>'
                '<path d="M70,372H570L540,404H100Z" fill="#E9E2CF" stroke="#8C8470" stroke-width="2"/><rect x="100" y="404" width="440" height="14" fill="#B9B098"/>')
    return ('<rect width="640" height="480" fill="#1C1740"/><rect y="250" width="640" height="230" fill="#161233"/>'
            '<path d="M70,372H570L540,404H100Z" fill="#3A3468" stroke="#0E0A26" stroke-width="2"/><rect x="100" y="404" width="440" height="14" fill="#2A2552"/>')


def hudrow(x, y, chips):
    out = f'<rect x="{x - 6}" y="{y - 5}" width="{len(chips)*27 + 9}" height="32" rx="9" fill="#fff" stroke="{INK}" stroke-width="2.5"/>'
    for i, c in enumerate(chips):
        out += nest(x + i*27, y, c)
    return out


def mock(bright, row_, unique=None, drop=None):
    """A 640 x 480 screen at real size. row_: (key, level) for five drives; level 5 draws the ascended form."""
    items, chips = [], []
    for k, lv in row_:
        d = DK[k]
        mesh = asc_mesh(d, d["tier"]) if lv >= 5 else tier_mesh(dmesh(d), d["tier"])
        sc = {1: 1.0, 2: 1.15}.get(lv, 1.3)
        items.append(lambda px, mesh=mesh, sc=sc: orb(mesh, px*sc, 1.2, x=True))
        chips.append(badge(k, 22) + (nest(13, 13, star(10)) if lv >= 5 else ""))
    cx, fy = 236, 372
    back, front = orbit(cx, fy - 46, items, 74, 17)
    body = stage(bright) + back + fighter(cx, fy, 88, 0) + front
    if unique:
        u = UK[unique]
        body += f'<ellipse cx="{cx}" cy="{fy - 52}" rx="70" ry="22" transform="rotate(-35 {cx} {fy - 52})" fill="none" stroke="#fff" stroke-width="1" stroke-dasharray="2 4" opacity=".4"/>'
        ux, uy = cx + 54, fy - 100
        for i, (dx, dy) in enumerate(((-36, -2), (-24, -4), (-12, -3))):
            g, tot = uorb(u, 28)
            body += f'<g opacity="{.16 + .13*i:.2f}">' + nest(ux + dx - tot/2, uy + dy - tot/2, g) + "</g>"
        g, tot = uorb(u, 31, 1.1)
        body += nest(ux - tot/2, uy - tot/2, g)
        chips = chips[:4] + [ubadge(unique, 24)]
    body += fighter(442, fy, 88, 3, "#8E90A0")
    if drop and drop in UK:
        body += floor_drop(540, fy, uorb(UK[drop], 22), UK[drop]["name"], True)
    elif drop:
        d2 = DK[drop]
        body += floor_drop(540, fy, orb(dmesh(d2), 22), d2["name"])
        for i, t in enumerate((.2, .4, .6, .8)):
            x = 540 + (cx + 74 - 540)*t; y = (fy - 27) - 19*t - 70*math.sin(math.pi*t)
            g, tot = orb(dmesh(d2), 24 - 4*t, 1.0)
            body += f'<g opacity="{.22 + .14*i:.2f}">' + nest(x - tot/2, y - tot/2, g) + "</g>"
    body += hudrow(22, 436, chips) + nametag(52, 420, "P1 row")
    return f'<div class="mock">{svg(640, 480, "0 0 640 480", body)}</div>'


def chiprow(bg, keys_fn):
    out = ""
    for k, word, *_ in FAMS:
        out += f'<div class="fr" style="background:{bg}">' + "".join(badge(d["key"], 22) for d in DRIVES if d["fam"] == k) + "</div>"
    out += f'<div class="fr" style="background:{bg}">' + "".join(ubadge(u["key"], 24) for u in UNIQUES) + "</div>"
    out += f'<div class="fr" style="background:{bg}">' + "".join(abadge(a[0], 22) for a in ACTS) + "</div>"
    return f'<div class="strip">{out}</div>'


def silrow(size, bg="#fff"):
    out = ""
    for k, *_ in FAMS:
        out += f'<div class="fr" style="background:{bg};gap:0">' + "".join(orb(dmesh(d), size, 0, mode="black")[0] for d in DRIVES if d["fam"] == k) + "</div>"
    out += f'<div class="fr" style="background:{bg};gap:0">' + "".join(udraw(u, round(size*VB), mode="black") for u in UNIQUES) + "</div>"
    return f'<div class="strip">{out}</div>'


def alike(n=8):
    """The measured too-alike list: overlap of the orbit-size silhouettes, every pair."""
    items = [(d["name"], d["fam"], raster(dmesh(d))) for d in DRIVES] + [(u["name"], "unique", raster(umesh(u))) for u in UNIQUES]
    res = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            a, b = items[i][2], items[j][2]
            inter = sum(1 for x, y in zip(a, b) if x and y); uni = sum(1 for x, y in zip(a, b) if x or y)
            res.append((inter/uni, items[i][0], items[j][0], items[i][1] == items[j][1]))
    res.sort(reverse=True)
    return res[:n], [r for r in res if not r[3]][:n]


def head(title):
    holo = "".join(f'<stop offset="{i / 5:.2f}" stop-color="{c}"/>' for i, c in enumerate(s4.HOLO.split(",")))
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title><style>{BASE9}{CSS9}</style></head>'
            f'<body><svg width="0" height="0" style="position:absolute"><defs><linearGradient id="holo" x1="0" y1="0" x2="1" y2="1">{holo}</linearGradient></defs></svg>')


def sheet_a():
    out = head("Envoy UI, step 9: drives (a)") + '<div id="c">'
    out += ('<div class="top9"><h1>A look for every drive</h1><p>46 drives, each with one idea shown three ways: the model that orbits the fighter, '
            'the badge in menus, the 22 px chip on the HUD. Every drawing on this sheet is made from the same part list that would build the model.</p></div>')
    out += ('<div class="s9"><h2>Six shape languages</h2><div class="lede">Family is readable from the outline alone. Each tile: the base form in black at 76 px and at orbit size (24 px), '
            f'then as the model. Colour is the second cue, never the only one.</div>{lang_strip()}</div>')
    for k, word, pool, col, *_ in FAMS:
        ds = [d for d in DRIVES if d["fam"] == k]
        out += (f'<div class="s9"><div class="fam"><span class="sw" style="background:{col}"></span><h2>{word}</h2><span>{LANG[k][0]} {len(ds)} drives. In the pool data: {pool}.</span></div>'
                f'<div class="cards">{"".join(card(d) for d in ds)}</div></div>')
    out += ('<div class="foot">Each card: the model as drawn in orbit (104 px, and at its real 24 px in the corner), the badge with its tier edge, the 22 px HUD chip, the name, tier and pool id, and why the shape. '
            'Original geometry. Fighters and stages elsewhere on these sheets are placeholders.</div></div></body></html>')
    return out


def tiers_panel():
    e = DK["ember"]; m = dmesh(e)
    it = lambda inner, cap: f'<div class="it"><div class="bx">{inner}</div>{cap}</div>'
    p1 = ("<h4>Tier: a ring is added under the form, the body never changes</h4><div class='pr'>"
          + it(drawx(m, 84, 2.2), f'{badge("ember", 30, 0)}<b>Common</b>plain body')
          + it(drawx(tier_mesh(m, 1), 84, 2.2), f'{badge("ember", 30, 1)}<b>Rare</b>a white ring')
          + it(drawx(tier_mesh(m, 2), 84, 2.2), f'{badge("ember", 30, 2)}<b>Epic</b>a foil ring, a spark')
          + it(drawx(tier_mesh(dmesh(DK["quicksilver"]), 2), 84, 2.2), f'{badge("quicksilver", 30)}<b>Quicksilver</b>Epic')
          + '<div><span class="sh">Better as a shader</span><div class="fb"><b>The Epic foil.</b> A view-angle rainbow on the ring that moves as the drive rocks. '
            '<b>Without shaders:</b> the ring\'s 14 segments take the six foil rows in turn and the ring spins, so the colours travel.</div></div></div>')
    p2 = ("<h4>Level 1 to 3: size and glow, one step each</h4><div class='pr'>"
          + it(draw(m, 74, 2.0), "<b>Level 1</b>size x1.0")
          + it(draw(m, 86, 2.1, under=glow_under("#FFD9A0", 1.4, .35, "lv2")), "<b>Level 2</b>x1.15, seams lit")
          + it(draw(m, 98, 2.2, under=glow_under("#FFE9B8", 1.5, .7, "lv3")), "<b>Level 3</b>x1.3, core pulses")
          + '<div><span class="sh">Better as a shader</span><div class="fb"><b>The glow steps.</b> A rim light whose strength is the level, pulsing at 3. '
            '<b>Without shaders:</b> size alone carries it (x1.0, x1.15, x1.3) and the hot row is baked one step brighter per level. Levels 4 to 9 keep the level 3 size.</div></div></div>')
    asc = "".join(it(drawx(asc_mesh(DK[k], DK[k]["tier"]), 80, 2.0), f'{asc_badge(k, 30)}<b>{DK[k]["name"]}</b>') for k in ("ember", "frost", "feather_storm", "perfect_form", "thorns", "relay", "steam"))
    p3 = ("<h4>Level 5, ascended: one rule for every drive. Gold seams, and a gold star in a ring over its head</h4><div class='pr'>" + asc
          + '<div><span class="sh">Better as a shader</span><div class="fb"><b>The halo.</b> A soft additive glow round the star with slow turning rays, the star as a sprite. '
            '<b>Without shaders:</b> a 12-segment gold ring and a twenty-triangle star 0.4 over the form, as drawn. The hot row swaps to the gold row either way. '
            'Tier sits under the form and ascension over it, so an ascended Epic (Steam, last) shows both and the family outline stays clear between them.</div></div></div>')
    return f'<div class="pn" style="flex:1 1 700px">{p1}</div><div class="pn" style="flex:1 1 700px">{p2}</div><div class="pn" style="flex:1 1 100%">{p3}</div>'


def drop_panel():
    fy = 150
    body = f'<rect width="760" height="190" rx="8" fill="#BFE3F5"/><rect y="{fy}" width="760" height="40" fill="#E9E2CF"/><path d="M0,{fy}H760" stroke="#8C8470" stroke-width="2"/>'
    body += floor_drop(70, fy, orb(dmesh(DK["shatter"]), 22), "Shatter")
    body += floor_drop(190, fy, orb(tier_mesh(dmesh(DK["tailwind"]), 1), 22, x=True), "Tailwind")
    body += floor_drop(310, fy, orb(tier_mesh(dmesh(DK["colossus"]), 2), 22, x=True), "Colossus")
    m = dmesh(DK["updraft"])
    body += (f'<ellipse cx="440" cy="{fy + 1}" rx="21" ry="6.5" fill="none" stroke="{INK}" stroke-width="6.5" opacity=".5"/><ellipse cx="440" cy="{fy + 1}" rx="21" ry="6.5" fill="none" stroke="{SUN}" stroke-width="3" opacity=".5"/>')
    pts = []
    for i, t in enumerate((0, .2, .42, .64, .84, 1)):
        x = 440 + 232*t; y = (fy - 27) - 26*t - 62*math.sin(math.pi*t)
        pts.append((x, y))
        g, tot = orb(m, 24 - 4*t, 1.1)
        body += f'<g opacity="{.3 + .14*i:.2f}">' + nest(x - tot/2, y - tot/2, g) + "</g>"
    body += f'<path d="M{" L".join(f"{x:.0f},{y:.0f}" for x, y in pts)}" fill="none" stroke="{SUN}" stroke-width="2" stroke-dasharray="2 5" stroke-linecap="round" transform="translate(0 19)" opacity=".9"/>'
    body += fighter(716, fy, 88, 0) + f'<circle cx="672" cy="{fy - 53}" r="15" fill="none" stroke="{INK}" stroke-width="4.5"/><circle cx="672" cy="{fy - 53}" r="15" fill="none" stroke="{SUN}" stroke-width="2.4"/>'
    body += stext(70, 182, "Common", 11, "#45425E") + stext(190, 182, "Rare", 11, "#45425E") + stext(310, 182, "Epic", 11, "#45425E") + stext(556, 182, "the fly-in: 30 frames, six shown", 11, "#45425E")
    return ('<div class="rowp" style="align-items:center">' + svg(912, 228, "0 0 760 190", body) + '<div class="note9" style="flex:1;min-width:300px">'
            '<b>On the floor.</b> White disc r 15 behind the model, centre 27 px over the floor. Model 22 px. Sunny rings 21 x 6.5 and 33 x 10. Name tag 20 px above. The tier ring shows under the form.<br><br>'
            '<b>Fly-in.</b> Frames 0 to 6 the disc shrinks away. Frames 0 to 30 the model arcs to its slot, 62 px high at the middle, with a dotted sunny trail. Frame 30: the sunny ring on its HUD chip, 90 frames.<br><br>'
            '<b>The glass shell</b> of the built pickups is dropped: the disc does its job and does not hide the shape.</div></div>')


def pick_event():
    u = UK["puppeteer"]
    tag = lambda k: f'<div class="tg9" style="opacity:.3;transform:scale(.86)">{badge(k, 40)}<div><b>{DK[k]["name"]}</b><span>{DK[k]["rule"][:38]}</span></div></div>'
    rays = "".join(f'<path d="M0,0L{240*math.cos(a - .07):.0f},{240*math.sin(a - .07):.0f}L{240*math.cos(a + .07):.0f},{240*math.sin(a + .07):.0f}Z" fill="#fff" opacity=".1"/>' for a in [i*math.pi/9 for i in range(18)])
    return (f'<div style="position:relative;width:640px;height:300px;background:#2A1A6E;border-radius:10px;overflow:hidden;flex:none">'
            f'<div style="position:absolute;left:320px;top:150px">{svg(1, 1, "0 0 1 1", rays, "style=overflow:visible")}</div>'
            f'<div style="position:absolute;left:14px;top:12px;display:flex;gap:6px">{tag("bolt")}{tag("hex")}{tag("rush")}</div>'
            f'<div style="position:absolute;left:96px;top:104px;width:448px"><div class="tg9 un" style="transform:rotate(-1.2deg);padding:12px 16px 14px 14px">'
            f'<div style="flex:none">{udraw(u, 96, 2.0)}</div><div><b>{u["name"]}</b><span>{u["rule"]}</span>'
            f'<span style="margin-top:8px;display:flex;align-items:center;gap:6px;color:#C9BFF5">{ubadge(u["key"], 26)}{upip(9)} One of a kind. It has no family and no levels.</span></div></div></div>'
            f'<div style="position:absolute;left:52px;top:62px;transform:rotate(-8deg);z-index:3">{s2.burst("A|Unique", "#8E7CF0", 84, 13)}</div>'
            f'<div style="position:absolute;left:150px;bottom:14px;font-family:Brico;font-weight:800;font-size:13px;color:#fff">A  Take (replaces your Unique)   B  Leave it</div></div>')


def sheet_b(top_same, top_cross):
    out = head("Envoy UI, step 9: drives (b)") + '<div id="c">'
    out += ('<div class="top9"><h1>Tiers, drops, Uniques, checks</h1><p>How tier, level and ascension show on a model without a new mesh, how a drive lies on the floor, '
            'the sixteen Uniques, the keystone and active marks, and the legibility tests at real size.</p></div>')
    out += f'<div class="s9"><h2>Tier, level and ascension on the model</h2><div class="lede">Three things, three different places: tier is a ring under the form, level is size and glow, ascension is a gold star in a ring over it. The family outline between them is never covered. Yellow tags mark what would be better done in a shader; each has a geometry-only version, which is what is drawn.</div><div class="rowp">{tiers_panel()}</div></div>'
    out += (f'<div class="s9"><h2>The floor drop and the fly-in</h2><div class="lede">Step 7\'s drop, with the model in the badge\'s place: the white disc stays behind it so it reads on any stage, the sunny rings stay on the floor, the name tag stays above. '
            f'The model bobs 2 px and rocks; it does not spin edge-on. Taken, the disc pops away in 6 frames, the model arcs to its orbit slot in 30, and the chip it lands on gets the sunny ring.</div>{drop_panel()}</div>')
    out += (f'<div class="s9" style="background:#E3E0EE"><h2>Uniques: the seventh treatment, for no family</h2><div class="lede">A Unique is dark where every family drive is bright. Body: near black with one metal or earth colour of its own (none of the six family colours, nor coral, lagoon or sunny). '
            f'Edge: ink and then white, where a family drive has ink only. Badge: cut as a diamond, black face, rim in its own colour, one diamond pip in place of three level pips. Each has one living material, drawn here as a still; all sixteen need the custom shader, and without it they fall back to the dark body, the double edge and a slow sheen baked into the atlas.</div>'
            f'<div class="cards">{"".join(ucard(u) for u in UNIQUES)}</div>'
            f'<div class="rowp" style="margin-top:16px">{mock(False, [("wildfire", 2), ("thorns", 1), ("frost", 3), ("feather_storm", 1)], "ashbank", "kiln")}<div style="flex:1;min-width:300px">{pick_event()}'
            f'<div class="note9" style="margin-top:12px"><b>In orbit.</b> It does not ride the row\'s ring. It takes its own path tilted 35 degrees, turning the other way, a fifth larger, leaving a short light trail, so one glance finds it. '
            f'Its slot in the HUD row is still its place in the chain.<br><b>On the floor.</b> A black diamond plate where a drive has a white disc, white rings where a drive has sunny ones, and a thin column of light 150 px tall so it can be found from across the stage.<br>'
            f'<b>In the pick list.</b> Its own beat: the three ordinary tags clear, one dark tag slides in larger with its material running and the burst "A Unique", and input is held half a second.</div></div></div></div>')
    kc = "".join(f'<div class="kc"><div class="hud">{kmini(k)}{kmini(k, True)}</div>{kem(k, 44)}<div><b>{n}</b><span>{em}</span></div></div>' for k, n, r, aw, em in KEYS)
    ex = KEYS[4]
    ac = "".join(f'<div class="kc" style="flex:1">{abadge(k, 46)}<span class="hud" style="padding:6px">{abadge(k, 22)}</span><div><b>{n}</b><span>{pips} pips. {why}</span></div></div>' for k, n, pips, rule, why in ACTS)
    out += (f'<div class="s9"><h2>Keystones and actives</h2><div class="lede">Keystones stay grape-ink wedges; each of the eight has its own emblem on a white disc (five were drawn in earlier steps, Overclock, Twin Soul and All In are new). '
            f'Awakened: the wedge turns sunny, as "Set!" does, and the emblem disc gains a sunny second ring and a white spark, so it still reads on the 32 px HUD wedge. Actives are the drive badge cut square in cobalt, a colour no family uses, each with its own glyph.</div>'
            f'<div class="rowp" style="align-items:center"><div class="pn" style="display:flex;gap:18px;padding:26px 20px 12px">{kwedge(ex[0], ex[1], ex[2], False)}{kwedge(ex[0], ex[1], ex[3], True)}</div>'
            f'<div style="flex:1"><div class="kgrid" style="grid-template-columns:repeat(2,1fr)">{kc}</div></div></div>'
            f'<div class="lbl">The five actives: the badge at 46 px and the 22 px HUD chip</div><div style="display:flex;gap:10px">{ac}</div></div>')
    same = "; ".join(f"{a} and {b} ({v:.0%})" for v, a, b, _ in top_same[:6])
    cross = "; ".join(f"{a} and {b} ({v:.0%})" for v, a, b, _ in top_cross[:5])
    out += (f'<div class="s9"><h2>Legibility at real size</h2><div class="lede">Nothing below is enlarged. Chips are 22 px (Uniques 24), silhouettes are 24 px across the model itself, the screens 640 by 480.</div>'
            f'<div class="lbl">Every chip on a bright stage tone: Fire, Frost, Sky, Tempo, Guard, Utility, the Uniques, the actives</div>{chiprow(BRIGHT, None)}'
            f'<div class="lbl">The same on a dark stage tone</div>{chiprow(DARK, None)}'
            f'<div class="lbl">Every model as a pure black shape at orbit size (24 px), by family, then the Uniques</div>{silrow(24)}'
            f'<div class="lbl">The same at 20 px, the size of a drive on the far side of the orbit</div>{silrow(20)}'
            f'<div class="note9" style="margin:10px 0 14px"><b>Measured overlap of the 24 px silhouettes</b> (shared pixels over all pixels, every pair). Closest across families: {cross}. Closest overall: {same}.</div>'
            f'<div class="rowp">{mock(True, [("ember", 1), ("bolt", 2), ("frost", 1), ("perfect_form", 3), ("echo", 1)], None, "comet")}{mock(False, [("kindle", 1), ("steam", 5), ("updraft", 2), ("last_stand", 1), ("relay", 3)], None, "tailwind")}</div>'
            f'<div class="note9" style="margin-top:10px"><b>Left, bright stage.</b> Ember (level 1), Bolt (2), Frost (1), Perfect Form (Rare, 3), Echo (Rare, 1). <b>Right, dark stage.</b> Kindle, an ascended Steam (Epic), Updraft (2), Last Stand (Rare), Relay (Rare, 3). '
            f'Near drives are 26 px at level 1, far ones 21 px and behind the fighter. The white tag at the bottom is the same five as HUD chips: each glyph is the model above it, front on. A drop lies at the right with its fly-in as four fading steps.</div></div>')
    out += ('<div class="s9"><h2>What to decide</h2><div class="rec">'
            '<div><b>1. The six languages</b>Tall and pointed, six-sided, wide and open, ringed, flat-topped and heavy, counted pieces. If one of these is wrong the drives under it change, so this comes first.</div>'
            '<div><b>2. The ink edge on models</b>Every model on these sheets has an ink outline, which is what makes a 24 px drive read on any stage. It costs a second copy of each mesh (or one outline shader). Without it the bright stages lose the pale families.</div>'
            '<div><b>3. Facing the camera</b>The models are flat reliefs, as the six built ones are. They rock 12 degrees and never spin edge-on. A full spin would hide the shape half the time.</div>'
            '<div><b>4. The weakest shapes</b>Jet Trail, Nova, Slick, Static, Contagion and Clockwork Heel are the ones least sure to read at 22 px. Look at those chips first in the rows above.</div>'
            '<div><b>5. Uniques</b>The diamond badge and the dark body are the class. Shared Flame was briefed as two linked rings, which is Utility\'s own mark, so it is drawn as a figure of eight. Albatross and Ouroboros lean on Sky and Tempo shapes and rely on the dark body to stand apart.</div>'
            '<div><b>6. Shaders</b>Three ordinary treatments are tagged as better in a shader, each with a version that needs none. The sixteen Unique materials have no good geometry-only version: they wait on the shader study.</div>'
            '</div><div class="foot">Original vector and geometry work, generated by build_step9.py. Fonts: Bricolage Grotesque, Source Sans 3 (SIL OFL). Fighter silhouettes and stages are neutral placeholders.</div></div>')
    return out + "</div></body></html>"


# ---------------------------------------------------------------------------------------------- outputs
def glyph_files():
    """glyphs/<id>.svg: the glyph alone (white, ink edge) in a 24-unit box, for the badge baker. PNGs are shot from these."""
    out = HERE / "glyphs"
    out.mkdir(exist_ok=True)
    items = {}
    for d in DRIVES:
        items[d["key"]] = ("-12 -12 24 24", GLY["d:" + d["key"]])
    for u in UNIQUES:
        items["unique_" + u["key"]] = ("-12 -12 24 24", glyph_inner(u["parts"], face="#F3F0F8", edge=NIGHT))
    for k, *_ in ACTS:
        items["active_" + k] = ("-12 -12 24 24", AGLY[k])
    files = {}
    for k, (vb, inner) in items.items():
        s = f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="{vb}">{inner}</svg>'
        (out / f"{k}.svg").write_text(s, encoding="utf-8")
        files[k] = s
    for k, *_ in KEYS:
        s = kem(k, 64).replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
        (out / f"keystone_{k}.svg").write_text(s, encoding="utf-8")
        files["keystone_" + k] = s
    return files


def models_md(top_same, top_cross):
    L = []
    A = L.append
    A("# Envoy drive models: build specs (step 9)\n")
    A("Design only. Nothing here is built. Written by `build_step9.py`, from the same part lists that draw `preview/step9-drives-a.png` and `-b.png`, "
      "so the triangle counts below are counted from real meshes, not estimated. Everything is original geometry; nothing is traced or adapted from any game.\n")
    A("## 1. What the existing generator does (the baseline)\n")
    A("`pc/scripts/examples/envoy_drives/tools/make_drives.py` (standard library only) writes six family bodies, a glass shell, three rarity overlays and one shared atlas.\n")
    A("- **Primitives.** `Mesh.tri` (flat-shaded, wound away from a centre), `poly` (convex fan), `pyramid`, and `prism`: a convex 2D polygon extruded from z0 to z1 with the front cap shrunk about its centroid, so the side walls are the bevel. Bodies use bevels 0.55 to 0.62. Spheres are an inlined icosahedron or octahedron. `ring_overlay` is a three-sided ring about the vertical axis.")
    A("- **Size.** `normalise` centres each body and scales it into a cube of half-size 2.2 world units; Envoy lifts a drive 2.6 and draws it at scale 1.15.")
    A("- **Budget.** Bodies are 24 to 80 triangles; overlays 74 to 146; the shell 20. Every triangle has its own three vertices (flat shading), 32 bytes each.")
    A("- **Colour.** One 128 x 128 atlas; each 5-texel row is a ramp along u from a dark body colour to a bright one, and a second glow atlas holds the emissive part of the same ramp. A vertex picks a row (v) and a place on the ramp (u), so a seam or a core is bright and a wall is dark. No per-model texture.")
    A("- **Glass and glow.** The glass shell is an icosahedron drawn with alpha 0.28. The shader study (`scratch/envoy-notes/shader-effects-study.md`) found that today the glow atlas is sampled on the CPU and baked into vertex colours, and the glass is plain alpha blend: there is no bloom and no emissive pass.")
    A("- **Rarity.** An added overlay model at the same transform, never a new body. This document keeps that rule.\n")
    A("## 2. What must be added to the generator\n")
    A("| addition | what | why |\n|---|---|---|")
    A("| `ring_xy(c, r, w, a0, a1, segs, zh, tilt)` | a ring or an arc facing the camera: a flat front face and two slanted back faces, 6 triangles a segment, end caps on arcs, an optional lean about X | Tempo's rings, Sky's arcs, Nova, Gatekeeper; 14 segments for a full ring |")
    A("| `ball(c, r)` | the icosahedron as a helper (20 triangles) | Comet, Snowball, pivots and knots |")
    A("| part lists | a drive is a list of parts (`P` prism, `R` ring, `B` ball) with a role: body, hot, or raised mark. `build(parts, family)` meshes it; `glyph_inner(parts)` draws the badge glyph from the same list | the model and the glyph cannot drift apart; the badge baker reads `glyphs/<id>.svg` |")
    A("| family rows in the Party pack colours | `fire` #FF7A1F, `frost` #62CCF5, `sky` #86D63C, `tempo` #C866F2, `guard` #C99455, `util` #AEA8CC, each with a `_hot` row (the colour mixed 35% toward a pale tint, to that tint) | the orbiter must be the colour of its sticker; the old rows (red, green, blue, yellow, purple, white) can stay for the old six bodies |")
    A("| rows `white`, `sun`, `ink`, `foil0` to `foil5` | the Rare ring, the ascended gold, the hull, the Epic ring | 22 rows are in use today and 25 fit (128 / 5); the new set needs 12 family rows + 9, so drop the six `prism` rows and the three old rarity rows, or make the atlas 128 x 256 |")
    A("| 32 Unique rows | a body row and a hot row per Unique | this is what forces the taller atlas; or give Uniques their own 128 x 128 atlas, which the shader work wants anyway |")
    A("| `hull(mesh, 0.09)` | a copy of the mesh pushed out along its face normals, wound inside out, in the `ink` row: the outline | the single biggest gain in legibility at 24 px. Doubles the triangle count. Better as an outline pass in a shader |")
    A("| `tier_ring(tier)` | the Rare and Epic rings as overlay models (`drive_ring_rare2`, `drive_ring_epic`), 84 triangles each, plus an 16-triangle spark | replaces magic / rare / unique overlays, which are a different tier set |")
    A("| `halo()` and `star()` | the ascended overlay: a 12-segment flat ring (72 triangles) and a two-sided ten-point star (20) | one overlay model serves all 46 |")
    A("| one mesh per drive | `drive_<id>.gxmesh`, `.material.json`, `.coll.json` for 46 drives and 16 Uniques | `drive_models.lua` picks by id, falling back to the family body |")
    A("| orbit facing | not the generator: the drawer must face models to the camera and rock them, not spin them | these are reliefs 0.4 deep; edge-on they vanish |\n")
    A("## 3. Shared treatments\n")
    A("**Proportions.** Parts are given in a box of -1 to 1 (x right, y up, z toward the camera); `normalise` then scales to half-size 2.2 as today. Body parts are prisms from z -0.2 to 0.2 with bevel 0.72 unless a spec says otherwise; hot parts z -0.24 to 0.26; raised marks z 0.14 to 0.33 in the hot row. Ramp positions: back 0.3, bevel rim 0.95, cap 0.7 (hot: 0.4, 0.95, 0.75). The bright bevel rim is the glowing seam of the existing family look.\n")
    _n = [len(dmesh(d).tris) for d in DRIVES]
    A(("**Triangle budget.** {lo} to {hi} for a body (mean {mean}), counted below; rings are the cost (84 a full ring), so Relay with two is the largest. With the ink hull, twice that. The existing bodies are 24 to 80, with a mean of 51, so the average rises by about half; five drives in orbit with hulls stay under 2,000 triangles.\n").format(lo=min(_n), hi=max(_n), mean=round(sum(_n)/len(_n))))
    A("**Orbit.** Each model faces the camera and rocks 12 degrees about its vertical axis (period 2.4 s, each slot a fifth of a period out of step). The per-drive animation below is added to that. The near half of the orbit draws at 26 px on a 640 x 480 screen, the far half at 21 px and behind the fighter.\n")
    A("| what | on the model | on the badge | better as a shader? | geometry-only version (drawn on the sheet) |\n|---|---|---|---|---|")
    A("| Common | the body alone | plain edge | no | - |")
    A("| Rare | a white ring lying flat under the form (radius 0.84 at y -1.14), so the outline above it is untouched | thick white die-cut | no | the `white` row ring, 84 triangles |")
    A("| Epic | the same ring in foil, and a four-point sunny spark riding it | foil rim and spark | **yes**: a view-angle iridescence on the ring | the 14 segments take `foil0` to `foil5` in turn and the ring spins once in 3 s |")
    A("| Level 1, 2, 3 | size x1.0, x1.15, x1.3; seams lit at 2; the core pulses at 3 | one, two, three pips | **yes**: a rim light whose strength is the level | size alone, and the hot row baked one ramp step brighter per level (three copies of the u offset, no new mesh) |")
    A("| Levels 4 to 9 | the level 3 size | gold pips (4 to 6), white pips (7 to 9), as step 7 | no | - |")
    A("| Ascended (level 5) | the hot row swaps to `sun` (gold seams); a gold star (0.76 across) inside a small flat gold ring (radius 0.52) floats 0.4 over the form | the gold star on the badge's lower right edge | **yes**: a soft additive glow with slow rays round the star, the star as a sprite | the ring and star overlay model, 92 triangles |")
    A("| Unbound (level 9) | the ascended model at x1.3, riding 20 px above the fighter's head instead of in the ring | as the content pass: it leaves the row | no | - |")
    A("| The ink edge | an ink outline about 1.2 px at orbit size | (the badge has its own) | **yes**: an outline pass | `hull()`, the inside-out copy |\n")
    A("Tier sits under the form, ascension over it, level is size: three cues in three different places, so an ascended Epic at level 6 still reads and the family outline between them is never covered. A first version put the Rare ring round the waist and a large halo behind the form; both were dropped because the ring cut the outline and the halo made every ascended drive round, which is the language of Tempo.\n")
    A("**The floor drop.** Step 7's drop with the model in the badge's place. The white disc (r 15, 2.4 ink edge) stays behind the model as a backing plate, centre 27 px above the floor; the sunny ellipse rings (21 x 6.5 and 33 x 10) stay on the floor; the name tag stays 20 px above the disc. The model is drawn 22 px across, bobs 2 px (period 1.2 s) and rocks; the glass shell is dropped (the disc does its job). Tier rings show. An ascended drive cannot drop.\n")
    A("**The fly-in (30 frames).** Frames 0 to 6: the disc scales to nothing and the floor rings fade. Frames 0 to 30: the model follows an arc from the disc to its orbit slot, 62 px high at the middle, leaving a dotted sunny trail of five points that fade over 12 frames. Frame 30: it joins the orbit and the HUD chip gets step 7's sunny ring for 90 frames.\n")
    A("## 4. The six shape languages\n")
    A("| family (pool) | colour | language | why it separates at 24 px |\n|---|---|---|---|")
    for k, word, pool, col, *_ in FAMS:
        A(f"| {word} ({pool}) | {col} | {LANG[k][0]} | {LANG[k][1]} |")
    A("")
    A("## 5. The 46 drives\n")
    A("Rows: body `<family>`, hot `<family>_hot`. \"Emissive\" lists the parts in the hot row beyond the bevel rims, which glow on every drive. Triangles are the body alone, without hull or overlays.\n")
    for k, word, pool, col, *_ in FAMS:
        A(f"### {word} ({pool}), rows `{k}` and `{k}_hot`\n")
        A("| id | name | tier | triangles | form | emissive parts | orbit animation | glyph |\n|---|---|---|---|---|---|---|---|")
        for d in DRIVES:
            if d["fam"] != k:
                continue
            n = len(dmesh(d).tris)
            hot = sum(1 for p in d["parts"] if p["role"] in "hi" and p["m"])
            A(f"| `{d['key']}` | {d['name']} | {TIERS[d['tier']]} | {n} | {d['form']} | {hot} of {sum(1 for p in d['parts'] if p['m'])} parts | {d['anim']} | `glyphs/{d['key']}.svg`: {d['idea']} |")
        A("")
    A("The exact coordinates of every part are in `DRIVES` in `build_step9.py`; copy the part list, not the prose.\n")
    A("## 6. The 16 Uniques\n")
    A("Rules and briefs: `scratch/envoy-notes/envoy-content-pass.md` section 9. Class treatment:\n")
    A("- **No family.** The body row runs from near black to a dark version of the Unique's own colour; the hot row is its second colour. None is a family colour, coral, lagoon or sunny.")
    A("- **Double edge.** Ink hull, then a white hull outside it (0.09 and 0.16). A family drive has the ink hull only. This is the cue that does not rely on colour.")
    A("- **Badge.** A diamond cut (a rounded square turned 45 degrees): the Unique's colour as the rim, a black face, the glyph in its light colour; one diamond pip where a drive has three level pips. Round is a drive, square is an active, a wedge is a keystone, a diamond is a Unique.")
    A("- **No tier ring, no levels, no halo, no star** (content pass 9.1).")
    A("- **Orbit.** Its own path, tilted 35 degrees to the row's ring and turning the other way, drawn at x1.2, with a short light trail (a shader sprite trail; without shaders, three fading copies).")
    A("- **Floor.** A black diamond plate with a white edge in place of the white disc, white floor rings in place of sunny, and a column of light 150 px tall.")
    A("- **Pick list.** Its own beat, as the content pass 9.5: the three tags clear, one dark tag slides in at x1.4 with the material running and the burst \"A Unique\"; input held 30 frames.")
    A("- **Shader.** Every signature material needs the mod draw layer the shader study recommends (per-object material with four parameters and a clock). Without it: the dark body, the double edge and one baked sheen band in the atlas row.\n")
    A("| id | name | triangles | form | colours (body, light) | signature material (shader) | what it must say | still on the sheet |\n|---|---|---|---|---|---|---|---|")
    for u in UNIQUES:
        A(f"| `{u['key']}` | {u['name']} | {len(umesh(u).tris)} | {u['form']} | {u['c1']}, {u['c2']} | {u['mat']} | {u['says']} | `{u['fx']}` |")
    A("")
    A("Three briefs were bent to keep the class outside the family languages: **Shared Flame** was \"two linked rings\", which is Utility's family mark and Relay's form, so it is a figure of eight with a drop at the join. **Albatross** is one long bent wing, where Sky's forms are symmetric. **Ouroboros** is a ring, as Tempo's are, but it thins to a tail and has a head; it relies on the dark body and double edge.\n")
    A("## 7. Keystones and actives (2D only)\n")
    A("| id | name | emblem | file |\n|---|---|---|---|")
    for k, n, r, aw, em in KEYS:
        A(f"| `{k}` | {n} | {em} | `glyphs/keystone_{k}.svg` |")
    A("")
    A("Awakened: the wedge face turns sunny; the emblem disc gains a sunny outer ring and a white spark at its upper right; the 32 px HUD wedge does the same. Plague Bearer and Grand Finale use coral and Echo Oath uses lagoon in emblems drawn in earlier steps; those are the player colours, and worth a second look.\n")
    A("| id | name | pips | glyph | file |\n|---|---|---|---|---|")
    for k, n, pips, rule, why in ACTS:
        A(f"| `{k}` | {n} | {pips} | {why} | `glyphs/active_{k}.svg` |")
    A("")
    A("Actives are the drive badge cut square (`pog(..., sq=True)`) in cobalt #3E6BFF, which no family uses.\n")
    A("## 8. Too alike, and what was done\n")
    A("Measured: overlap of the 24 px black silhouettes (shared pixels over all pixels), every pair of the 62 models.\n")
    A("| closest pairs across families | overlap |\n|---|---|")
    for v, a, b, _ in top_cross:
        A(f"| {a} and {b} | {v:.0%} |")
    A("")
    A("| closest pairs inside one family | overlap |\n|---|---|")
    for v, a, b, s in [r for r in top_same if r[3]][:8]:
        A(f"| {a} and {b} | {v:.0%} |")
    A("")
    A("The overlap number is crude (two filled shapes of the same size always score high), so it was used to find pairs to look at, not to pass them. What it found and what was changed:\n")
    A("| pair | what was wrong | what was done |\n|---|---|---|")
    for a, b, c in [
        ("Hex, Clean Landing, Leech, Surge (82 to 89% with each other)", "all four were a filled plate with a mark raised on it; in black they were the same blob", "Hex is now cut through by its cross into four wedges; Clean Landing is a thin ring with the tick inside; Leech is the plus itself; Surge is two slabs sliding past each other"),
        ("Wildfire and Feather Storm (78%)", "both were three prongs fanned from one root", "Wildfire is one tall flame with a small flame standing apart at each side of its foot"),
        ("Leech and Mirror (83%)", "a fat plus fills a diamond", "the plus arms went from 0.66 to 0.56 wide; Mirror's halves moved 0.4 apart and its hollow half got a thinner frame. Now under 70%"),
        ("Cinder Heart and Ashbank (79%)", "a heart-shaped coal and an urn are both wide-shouldered with a knob on top", "the urn got two ear handles; it is also dark with the double edge. Now 70%"),
        ("Ember and Magpie (76%)", "a pouch drawn narrow is a teardrop", "the pouch is squatter (1.7 wide) with a wide flared neck"),
        ("Comet and Meteor", "both began as a ball with a tail", "Comet is a ball thrown up off a wide arc; Meteor is a dart diving point down"),
        ("Rush, Tailwind, Clean Landing", "three discs with an ink mark each", "Rush is a ring with three speed lines; Tailwind is an arrow through a hoop; Clean Landing is the ring with a tick"),
        ("Tailwind and the Sky family mark", "a curl of wind is Sky's own family glyph, and Tailwind is a Tempo drive", "no curl: the hoop and arrow"),
        ("Colossus and Affliction", "both were three stacked bars", "Affliction is four cells of honeycomb; Colossus keeps the stack, widening upward"),
        ("Echo and Mirror", "both were diamonds", "Echo is three blocks stepping down to the right"),
        ("Slick, Bulwark, Gatekeeper", "three arches", "Slick is a ring lying flat; Bulwark is a solid dome on a slab; Gatekeeper keeps the open arch"),
        ("Hex and Tempo's rings", "a hexagon ring with a centre dot is a bullseye", "Hex has no hole"),
        ("Shared Flame and Relay", "the Unique was briefed as two linked rings, which is Utility's family mark and Relay's form", "Shared Flame is a figure of eight, upright, with a drop at the join"),
        ("The Rare ring and every outline", "a ring round the waist cut the family outline at 24 px", "the tier ring lies under the form"),
        ("The ascended halo and Tempo", "a large halo behind the form made every ascended drive round", "the halo is a small ring with the star, over the form"),
    ]:
        A(f"| {a} | {b} | {c} |")
    A("")
    A("Still close and left: **Ember and Cinder Heart** (79%, same family: the heart is wider and has a cleft), **Clean Landing and Perfect Form** (74%, same family: a tick against a centre disc), **Cinder Heart** against several filled shapes (it is the roundest Fire form).\n")
    A("## 9. Least sure to read\n")
    A("1. **Jet Trail**: a small ring and two thin wakes; at 22 px the wakes are one pixel of white. May need to lose the outer wake.\n2. **Nova**: the flame between two arcs; the arcs can read as a Tempo ring at orbit size.\n3. **Slick**: a flat oval; it is the only tilted ring and can read as a Guard slab in black.\n4. **Static**: the zigzag belt is an ink mark and is gone at 22 px; the two barbs carry it alone.\n5. **Contagion**: the three buds are 4 px each at chip size.\n6. **Clockwork Heel** (Unique): three small pieces; the key is too small for the chip.\n7. **Puppeteer** (Unique): the threads are one pixel at chip size.\n8. **Thunderhead and Bolt**: both carry a zigzag; the cloud is what separates them, and it does.\n9. **Riposte and Thorns**: the same plate with different things sticking out.\n")
    (HERE / "DRIVE-MODELS.md").write_text("\n".join(L), encoding="utf-8")


def main():
    top_same, top_cross = alike(10)
    for v, a, b, s in top_cross[:6] + [r for r in top_same if r[3]][:6]:
        print(f"alike {v:.2f} {a} / {b}{' (same family)' if s else ''}")
    files = glyph_files()
    models_md(top_same, top_cross)
    (HERE / "step9-a.html").write_text(sheet_a(), encoding="utf-8")
    (HERE / "step9-b.html").write_text(sheet_b(top_same, top_cross), encoding="utf-8")
    gl = ("<!doctype html><html><body style='margin:0;background:transparent'>"
          + "".join(f'<div id="g-{k}" style="width:64px;height:64px;line-height:0">{s}</div>' for k, s in files.items()) + "</body></html>")
    (HERE / "glyphs" / "_all.html").write_text(gl, encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        for tag in "ab":
            page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
            page.goto((HERE / f"step9-{tag}.html").as_uri())
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(400)
            page.locator("#c").screenshot(path=str(HERE / "preview" / f"step9-drives-{tag}.png"), type="png")
            print("sheet", tag, "height", page.evaluate("document.getElementById('c').offsetHeight"))
            for b in page.evaluate("""() => { const o = []; for (const e of document.querySelectorAll('.cd .tx,.lg,.kw9 .kwt,.kc,.rec div,.tg9')) {
                if (e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1) o.push('overflow: ' + e.textContent.slice(0, 50)); } return o; }"""):
                print(b)
            page.close()
        pg = browser.new_page(viewport={"width": 200, "height": 200}, device_scale_factor=1)
        pg.goto((HERE / "glyphs" / "_all.html").as_uri())
        for k in files:
            pg.locator(f"#g-{k}").screenshot(path=str(HERE / "glyphs" / f"{k}.png"), type="png", omit_background=True)
        browser.close()
    (HERE / "glyphs" / "_all.html").unlink()
    print(len(DRIVES), "drives,", len(UNIQUES), "uniques,", len(files), "glyph files")


if __name__ == "__main__":
    main()
