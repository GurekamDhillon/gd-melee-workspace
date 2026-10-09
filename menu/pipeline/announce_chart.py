"""Comparison chart for the 0.2.2 Discord announcement: GD's Melee vs vanilla Melee.

    python menu/pipeline/announce_chart.py   -> menu/out_announce/chart_1.png, chart_2.png

Original art only (provenance rule, menu/CLAUDE.md): colours come from the Atlas
tokens (menu/atlas/tokens.json), fonts are Barlow Condensed and Source Sans 3
(both OFL, in menu/). No Nintendo logos, characters, screenshots or game fonts.

Every claim in ROWS is traced to a published release note or the shipped zip's
README; the source is in the third element of each row's comment. Nothing
unreleased, hidden or unverified is listed. Checks (non-zero exit on failure):
  * no text box overflows its box (measured in the page);
  * text contrast >= 4.5:1 for every text colour on its background.
"""
import base64
import json
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
MENU = os.path.dirname(HERE)
OUT = os.path.join(MENU, "out_announce")
TOK = json.load(open(os.path.join(MENU, "atlas", "tokens.json")))["colours"]


def C(name):
    return "#%06x" % (TOK[name] >> 8)


BG, PLATE, PLATE2, INK = C("ground"), C("plate"), C("plate2"), C("ink")
IVORY, MUTED, TEXT2, SUN, JADE, ROSE, LINE = (C("ivory"), C("muted"), C("text2"),
                                              C("sun"), C("jade"), C("rose"), C("line2"))

VERSION = "0.2.2"
LINK = "github.com/GurekamDhillon/gd-melee-workspace/releases/tag/v0.2.2"

# (label, vanilla, ours). Cell = ("y"|"n"|"t", text). y = check, n = cross, t = plain text.
# Vanilla "y" only where the original game really has it.
SECTIONS = [
    ("PLATFORM", [
        ("Runs as", ("t", "GameCube or Wii hardware, or the Dolphin emulator"),
                    ("y", "A native app on Windows and Linux. No emulator.")),             # README, 0.2.0 notes
        ("Display", ("t", "Console video output"),
                    ("y", "Fullscreen (F11 / Alt+Enter), HD render scale, widescreen option")),  # 0.1.0, 0.2.0, 0.2.2
        ("Frame rate", ("t", "60 fps"),
                       ("y", "60 fps, or uncapped / 120 to 144 Hz with smooth interpolation")),  # 0.1.7
        ("Controls", ("t", "GameCube controller"),
                     ("y", "GameCube adapter or any gamepad, plus mouse in the menus")),   # README-user
    ]),
    ("ONLINE", [
        ("Online play", ("n", "None on the console"),
                        ("y", "Built-in rollback netcode")),                               # 0.1.0
        ("Finding a match", ("n", "No"),
                            ("y", "Private rooms by code, or Random Opponent")),           # 0.1.0
        ("Competitive lobby", ("n", "No"),
                              ("y", "Blind picks, starters and counterpicks, 1-2-1 stage strikes, bans, rematches")),  # 0.1.0, 0.1.4
        ("Windows and Linux", ("n", "No"),
                              ("y", "Both play each other online")),                       # 0.2.0
        ("Mods online", ("n", "No"),
                        ("y", "Pick any fighter or stage both players have")),             # 0.1.0
        ("Keeps you in sync", ("n", "No"),
                              ("y", "Mismatched builds or discs are refused, not desynced")),  # 0.2.0, 0.2.2
        ("Turbo rule", ("n", "No"),
                       ("y", "Cancel into most moves after a connected hit (private rooms)")),  # 0.2.0
        ("After a disconnect", ("n", "No"),
                               ("y", "Tied games replay; Envoy sets resume or can be abandoned")),  # 0.2.2
    ]),
    ("CONTENT AND MODS", [
        ("Mod discs", ("n", "No"),
                      ("y", "m-ex mod discs and loose mods, managed in the launcher")),    # 0.1.0, README
        ("Roster size", ("t", "Fixed roster"),
                        ("y", "Up to 94 fighter slots with m-ex mods")),                   # 0.1.5
        ("Costumes", ("t", "The original palette slots"),
                     ("y", "255 costumes per fighter")),                                   # 0.2.2
        ("Mod browser", ("n", "No"),
                        ("y", "In-game SSBM Nucleus browser: search, thumbnails, install queue")),  # 0.2.2
        ("Scripting", ("n", "No"),
                      ("y", "Lua scripts and mods, in-game console, custom menus")),       # 0.1.0, 0.2.0
        ("Stage and camera tools", ("n", "No"),
                                   ("y", "Script cameras, add platforms, place custom 3D models, map editor example")),  # 0.1.7
    ]),
    ("MODES", [
        ("Envoy roguelite", ("n", "No"),
                            ("y", "A roguelike run on Classic and Adventure: drives, keystones, New Game+, 2-player offline co-op")),  # 0.2.0
        ("Envoy online", ("n", "No"),
                         ("y", "Two-player sets in a private room (passive drives only)")),  # 0.2.0
        ("Training", ("t", "Training Mode"),
                     ("y", "LAB: frame data, hitbox view, configurable dummy, combos and drills, saved states")),  # 0.1.5, 0.1.6, README-user
    ]),
    ("QUALITY OF LIFE", [
        ("Unlocks", ("t", "Earned by playing"),
                    ("y", "Everything unlocked from the start (Settings > Gameplay turns it off)")),  # 0.2.2
        ("Crash reports", ("n", "No"),
                          ("y", "Saved for you, with opt-in upload from the launcher")),   # 0.1.2, 0.2.0
        ("Launcher", ("n", "No"),
                     ("y", "Disc library, mod toggles, diagnostics; English and Spanish")),  # 0.1.4, 0.2.0
    ]),
]

PARTS = [("chart_1.png", ["PLATFORM", "ONLINE"]),
         ("chart_2.png", ["CONTENT AND MODS", "MODES", "QUALITY OF LIFE"])]

W = 1600


def font_css():
    def b64(p):
        return base64.b64encode(open(p, "rb").read()).decode()
    return (
        "@font-face{font-family:BC;font-weight:700;src:url(data:font/ttf;base64,%s)}"
        "@font-face{font-family:BC;font-weight:600;src:url(data:font/ttf;base64,%s)}"
        "@font-face{font-family:SS;font-weight:400;src:url(data:font/otf;base64,%s)}"
        "@font-face{font-family:SS;font-weight:600;src:url(data:font/otf;base64,%s)}"
        "@font-face{font-family:SS;font-weight:700;src:url(data:font/otf;base64,%s)}") % (
        b64(os.path.join(MENU, "Barlow", "BarlowCondensed-Bold.ttf")),
        b64(os.path.join(MENU, "Barlow", "BarlowCondensed-SemiBold.ttf")),
        b64(os.path.join(MENU, "SourceSans3", "SourceSans3-Semibold.otf")),
        b64(os.path.join(MENU, "SourceSans3", "SourceSans3-Semibold.otf")),
        b64(os.path.join(MENU, "SourceSans3", "SourceSans3-Bold.otf")))


CHECK = ('<svg viewBox="0 0 24 24" width="30" height="30"><path d="M3 13 L9 19 L21 5" fill="none" '
         'stroke="%s" stroke-width="4.5" stroke-linecap="square"/></svg>' % JADE)
CROSS = ('<svg viewBox="0 0 24 24" width="30" height="30"><path d="M5 5 L19 19 M19 5 L5 19" fill="none" '
         'stroke="%s" stroke-width="4.5" stroke-linecap="square"/></svg>' % ROSE)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def cell(c, cls):
    kind, text = c
    icon = {"y": CHECK, "n": CROSS, "t": ""}[kind]
    return '<div class="cell %s">%s<span class="tx">%s</span></div>' % (cls, icon, esc(text))


def page(keys, first, last):
    h = ["<html><head><meta charset=utf-8><style>", font_css(), """
*{box-sizing:border-box;margin:0}
body{width:%dpx;background:%s;font-family:SS,sans-serif;color:%s;padding:48px 56px 40px}
.title{font:700 74px/1.25 BC;color:%s;letter-spacing:1px;text-transform:uppercase}
.title b{color:%s;font-weight:700}
.sub{font:600 30px/1.3 BC;color:%s;margin:10px 0 30px;letter-spacing:1px;text-transform:uppercase}
.cols,.row{display:grid;grid-template-columns:300px 1fr 1.55fr;gap:0}
.cols{margin-bottom:6px}
.ch{font:700 34px/1 BC;text-transform:uppercase;letter-spacing:1px;padding:16px 22px}
.ch.v{color:%s}.ch.g{color:%s;background:%s;border-top:6px solid %s}
.sec{margin:26px 0 8px;display:inline-block;background:%s;color:%s;font:700 38px/1 BC;
  letter-spacing:2px;padding:10px 26px;transform:skewX(-14deg);box-shadow:6px 6px 0 %s}
.sec span{display:inline-block;transform:skewX(14deg)}
.row{border-bottom:2px solid %s;min-height:70px}
.lab{font:700 31px/1.15 BC;text-transform:uppercase;letter-spacing:.5px;color:%s;padding:14px 22px 14px 22px;
  display:flex;align-items:center}
.cell{display:flex;align-items:center;gap:14px;padding:12px 22px;font:600 25px/1.25 SS;min-height:70px}
.cell svg{flex:none}.cell.v .tx{color:%s}.cell.g{background:%s}.cell.g .tx{color:%s}
.foot{margin-top:34px;border-top:4px solid %s;padding-top:20px;display:flex;flex-direction:column;gap:8px}
.foot .big{font:700 34px/1.15 BC;color:%s;letter-spacing:1px}
.foot .sm{font:600 24px/1.35 SS;color:%s}
</style></head><body>""" % (W, BG, IVORY, IVORY, SUN, TEXT2, MUTED, IVORY, PLATE2, SUN,
                           SUN, INK, INK, LINE, SUN, MUTED, PLATE, IVORY, SUN, SUN, MUTED)]
    if first:
        h.append('<div class="title">GD\'s Melee <b>%s</b> vs vanilla Melee</div>' % VERSION)
        h.append('<div class="sub">Everything in our build compared with Melee NTSC 1.02 on GameCube or Dolphin</div>')
    h.append('<div class="cols"><div></div><div class="ch v">Vanilla Melee</div>'
             '<div class="ch g">GD\'s Melee %s</div></div>' % VERSION)
    for title, rows in SECTIONS:
        if title not in keys:
            continue
        h.append('<div class="sec"><span>%s</span></div>' % title)
        for lab, v, g in rows:
            h.append('<div class="row"><div class="lab">%s</div>%s%s</div>' % (esc(lab), cell(v, "v"), cell(g, "g")))
    if last:
        h.append('<div class="foot"><div class="big">Download v%s for Windows and Linux: %s</div>'
                 '<div class="sm">Bring your own Melee NTSC-U 1.02 disc image; no game data is included. '
                 'Windows and Linux 0.2.2 play each other, not 0.2.1 or earlier.</div>'
                 '<div class="sm">Mods from SSBM Nucleus - https://ssbmnucleus.net. Not affiliated with or '
                 'endorsed by Nintendo or HAL Laboratory.</div></div>' % (VERSION, LINK))
    h.append("</body></html>")
    return "".join(h)


def lum(hexc):
    r, g, b = [int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


CHECKS = {  # text colour, background
    "title ivory on ground": (IVORY, BG), "title gold on ground": (SUN, BG),
    "subtitle on ground": (TEXT2, BG), "label gold on plate": (SUN, PLATE),
    "vanilla text on ground": (MUTED, BG), "ours text on plate": (IVORY, PLATE),
    "ours header gold on plate2": (SUN, PLATE2), "vanilla header on ground": (MUTED, BG),
    "section ink on gold": (INK, SUN), "foot gold on ground": (SUN, BG),
    "foot small on ground": (MUTED, BG), "check jade on plate": (JADE, PLATE),
    "cross rose on ground": (ROSE, BG)}


def main():
    os.makedirs(OUT, exist_ok=True)
    errs = []
    rep = {}
    for n, (a, b) in CHECKS.items():
        c = contrast(a, b)
        rep[n] = round(c, 2)
        if c < 4.5:
            errs.append("contrast %s %.2f:1 < 4.5" % (n, c))
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        for i, (name, keys) in enumerate(PARTS):
            pg = browser.new_page(viewport={"width": W, "height": 800})
            pg.set_content(page(keys, i == 0, i == len(PARTS) - 1))
            pg.evaluate("document.fonts.ready")
            bad = pg.evaluate("""() => [...document.querySelectorAll('.tx,.lab,.title,.sub,.big,.sm,.ch')]
                .filter(e => e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1)
                .map(e => e.textContent.slice(0, 40))""")
            # a cell must stay at most three lines
            tall = pg.evaluate("""() => [...document.querySelectorAll('.tx')]
                .filter(e => e.getBoundingClientRect().height > 3 * parseFloat(getComputedStyle(e).lineHeight) + 1)
                .map(e => e.textContent.slice(0, 40))""")
            wide = pg.evaluate("document.documentElement.scrollWidth > %d" % W)
            errs += ["overflow: " + t for t in bad + tall] + (["page wider than %d" % W] if wide else [])
            pg.screenshot(path=os.path.join(OUT, name), full_page=True)
            dims = pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.scrollHeight]")
            rep[name] = dims
            pg.close()
        browser.close()
    print("checks:", json.dumps(rep))
    if errs:
        print("FAIL:\n  " + "\n  ".join(errs))
        sys.exit(1)
    print("ok: no overflow, contrast >= 4.5:1")


if __name__ == "__main__":
    main()
