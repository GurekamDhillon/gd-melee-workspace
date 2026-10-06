#!/usr/bin/env python3
"""One command: renders the whole Workbench direction (headless Chromium, no network, deterministic).

    python build.py            -> assets/ (drive tokens from the real models), screens/*.html, kit.html,
                                  out/*.png, index.html
Checks run on every page (text >= 12 px at 640x480 scale, no clipped text, nothing off the canvas) and are
printed; the exit code is non-zero if a hard check fails.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import drives                      # noqa: E402
import screens as S                # noqa: E402
import kitpage                     # noqa: E402
from playwright.sync_api import sync_playwright   # noqa: E402

OUT = os.path.join(HERE, "out")
SCR = os.path.join(HERE, "screens")

WIDE = 1920 / 1080 * 480           # logical width of a 16:9 canvas at 480 high

# (file, title, builder, logical width, logical height, zoom)
SCREENS = [
    ("01-title", "Title", lambda: S.s01(), 640, 480, 2),
    ("02-main-menu", "Main menu", lambda: S.s02(), 640, 480, 2),
    ("03-solo", "Solo hub", lambda: S.s03(), 640, 480, 2),
    ("04-characters", "Character select (Versus)", lambda: S.s04(), 640, 480, 2),
    ("05-stages", "Stage select", lambda: S.s05(), 640, 480, 2),
    ("06-versus-rules", "Versus rules, with Turbo", lambda: S.s06(), 640, 480, 2),
    ("07-online-room", "Online room", lambda: S.s07(), 640, 480, 2),
    ("08-envoy-setup", "Envoy run setup", lambda: S.s08(), 640, 480, 2),
    ("09-envoy-bag", "Envoy bag", lambda: S.s09(), 640, 480, 2),
    ("10-envoy-reward", "Envoy reward", lambda: S.s10(), 640, 480, 2),
    ("11-envoy-hud", "Envoy in-match HUD", lambda: S.s11(), 640, 480, 2),
    ("12-pause", "Pause", lambda: S.s12(), 640, 480, 2),
    ("12b-payout", "End-of-stage payout", lambda: S.s12b(), 640, 480, 2),
    ("13-results", "Results", lambda: S.s13(), 640, 480, 2),
    ("14-settings-video", "Settings: video", lambda: S.s14(), 640, 480, 2),
    ("14b-settings-audio", "Settings: audio", lambda: S.s14b(), 640, 480, 2),
    ("14c-settings-controls", "Settings: controls and remap editor", lambda: S.s14c(), 640, 480, 2),
    ("15-mods", "Mods", lambda: S.s15(), 640, 480, 2),
    ("16-lab-pause", "The LAB pause menu", lambda: S.s16(), 640, 480, 2),
    ("17-launcher", "Launcher: Play tab (desktop window)", lambda: S.s17(), 960, 600, 4 / 3),
    ("wide-02-main-menu", "Main menu, 16:9", lambda: S.s02(WIDE), WIDE, 480, 2.25),
    ("wide-04-characters", "Character select, 16:9", lambda: S.s04(WIDE), WIDE, 480, 2.25),
    ("wide-09-envoy-bag", "Envoy bag, 16:9", lambda: S.s09(WIDE), WIDE, 480, 2.25),
    ("small-02-main-menu", "Main menu at true 640x480", lambda: S.s02(), 640, 480, 1),
    ("small-09-envoy-bag", "Envoy bag at true 640x480", lambda: S.s09(), 640, 480, 1),
]

CHECK_JS = """
(z) => {
  const bad = [];
  const scr = document.querySelector('.screen');
  const sb = scr.getBoundingClientRect();
  document.querySelectorAll('.screen *').forEach(el => {
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own) return;
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize) / (el.closest('svg') ? 1 : 1);
    if (fs < 11.99 && !el.closest('svg')) bad.push('small ' + fs.toFixed(1) + 'px: ' + el.textContent.trim().slice(0, 30));
    if (el.scrollWidth > el.clientWidth + 1 && cs.display !== 'inline') bad.push('clipped: ' + el.textContent.trim().slice(0, 30));
    const r = el.getBoundingClientRect();
    if (r.width && (r.right > sb.right + 2 || r.left < sb.left - 2 || r.bottom > sb.bottom + 2)) bad.push('offcanvas: ' + el.textContent.trim().slice(0, 30));
  });
  return bad;
}
"""


def wrap(title, inner, w, h, zoom, depth="../", a="../assets/"):
    inner = inner.replace("{A}", a)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>%s</title>'
            '<link rel="stylesheet" href="%stokens.css"><link rel="stylesheet" href="%skit.css">'
            '<style>html{zoom:%s}body{margin:0}</style></head><body><div class="screen" style="--w:%spx;height:%spx">%s</div></body></html>'
            % (title, depth, depth, round(zoom, 5), round(w, 3), h, inner))


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SCR, exist_ok=True)
    os.makedirs(os.path.join(HERE, "assets"), exist_ok=True)
    drives.build(os.path.join(HERE, "assets"))
    fail = 0
    pages = []
    for name, title, fn, w, h, z in SCREENS:
        path = os.path.join(SCR, name + ".html")
        open(path, "w", encoding="utf-8").write(wrap("Workbench: " + title, fn(), w, h, z))
        pages.append((name, title, path, w, h, z))
    kit_pages = kitpage.build(HERE)           # writes kit.html, returns [(png name, selector)]
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, title, path, w, h, z in pages:
            vw, vh = round(w * z), round(h * z)
            pg = b.new_page(viewport={"width": vw, "height": vh}, device_scale_factor=1)
            pg.goto("file:///" + path.replace("\\", "/"))
            pg.wait_for_timeout(120)
            pg.evaluate("document.fonts.ready")
            pg.screenshot(path=os.path.join(OUT, name + ".png"), clip={"x": 0, "y": 0, "width": vw, "height": vh})
            bad = pg.evaluate(CHECK_JS, z)
            print("%-26s %dx%d %s" % (name, vw, vh, "ok" if not bad else "; ".join(sorted(set(bad))[:8])))
            if any(x.startswith("small") for x in bad):
                fail += 1
            pg.close()
        pg = b.new_page(viewport={"width": 1700, "height": 1200}, device_scale_factor=1)
        pg.goto("file:///" + os.path.join(HERE, "kit.html").replace("\\", "/"))
        pg.wait_for_timeout(250)
        for png, sel in kit_pages:
            pg.locator(sel).screenshot(path=os.path.join(OUT, png))
            print("%-26s kit sheet" % png)
        b.close()
    kitpage.index(HERE, [(n, t, w, h, z) for n, t, _, w, h, z in pages], [k[0] for k in kit_pages])
    print("done", "FAIL" if fail else "ok")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
