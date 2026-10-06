"""ATLAS: renders every page and preview.

    python build.py            everything: screens/*.html, kit.html, out/*.png, index.html
    python build.py 04 09      only screens whose file name starts with these prefixes (quick iteration)

Deterministic and offline: Playwright's headless Chromium, local fonts, no network. The six drive models are drawn from the
committed generator's own geometry (drives.py). Nothing opens a window.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parts                      # noqa: E402
import drives                     # noqa: E402

SCREENS_DIR = os.path.join(HERE, "screens")
OUT = os.path.join(HERE, "out")


def screens_list():
    import screens_a as A
    import screens_b as B
    return [
        ("01-title", A.s01, "Title / press start"), ("02-main-menu", A.s02, "Main menu"), ("03-solo", A.s03, "Solo hub"),
        ("04-characters", A.s04, "Character select, Versus"), ("05-stages", A.s05, "Stage select"), ("06-versus-rules", A.s06, "Versus rules with Turbo"),
        ("07-online-room", A.s07, "Online room"), ("08-envoy-setup", A.s08, "Envoy run setup"),
        ("09-envoy-bag", B.s09, "Envoy bag"), ("10-envoy-reward", B.s10, "Envoy reward"), ("11-envoy-hud", B.s11, "In-match HUD, Envoy stage"),
        ("12-pause", B.s12, "Pause"), ("12b-payout", B.s12b, "End-of-stage payout"), ("13-results", B.s13, "Results"),
        ("14-settings-video", B.s14, "Settings: video"), ("14b-settings-audio", B.s14b, "Settings: audio"), ("14c-remap", B.s14c, "Settings: controls, remap editor"),
        ("15-mods", B.s15, "Mods"), ("16-lab-pause", B.s16, "LAB pause menu"), ("17-launcher", B.s17, "Launcher: Play tab"),
    ]


WIDE = ["02-main-menu", "04-characters", "09-envoy-bag"]
SMALL = ["02-main-menu", "09-envoy-bag"]


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    only = sys.argv[1:]
    svg, info = drives.build_defs()
    parts.DRIVES["svg"] = svg
    os.makedirs(SCREENS_DIR, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    jobs = []   # (html path, png path, kind)
    for name, fn, title in screens_list():
        if only and not any(name.startswith(o) for o in only):
            continue
        write(os.path.join(SCREENS_DIR, name + ".html"), fn(False))
        jobs.append((name + ".html", name + ".png", "std"))
        if name in WIDE:
            write(os.path.join(SCREENS_DIR, "wide-" + name + ".html"), fn(True))
            jobs.append(("wide-" + name + ".html", "wide-" + name + ".png", "wide"))
        if name in SMALL:
            jobs.append((name + ".html", "small-" + name + ".png", "small"))
    kit_jobs = []
    if not only:
        import kitpage
        kitpage.write_kit(HERE, svg)
        kit_jobs = kitpage.JOBS
    from playwright.sync_api import sync_playwright
    from PIL import Image
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        for html, png, kind in jobs:
            scale = {"std": 2, "wide": 2.25, "small": 1}[kind]
            w = 853 if kind == "wide" else 640
            hh = 484
            if html.startswith("17-"):
                w, hh = 900, 600
            ctx = browser.new_context(viewport={"width": w + 2, "height": hh + 4}, device_scale_factor=scale)
            page = ctx.new_page()
            page.goto("file:///" + os.path.join(SCREENS_DIR, html).replace("\\", "/"))
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(120)
            el = page.query_selector(".s")
            dest = os.path.join(OUT, png)
            el.screenshot(path=dest)
            if kind == "wide":
                im = Image.open(dest)
                im.resize((1920, 1080), Image.LANCZOS).save(dest)
            ctx.close()
            print("rendered", png)
        for html, sel, png, scale, width in kit_jobs:
            ctx = browser.new_context(viewport={"width": width, "height": 900}, device_scale_factor=scale)
            page = ctx.new_page()
            page.goto("file:///" + os.path.join(HERE, html).replace("\\", "/"))
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(150)
            page.query_selector(sel).screenshot(path=os.path.join(OUT, png))
            ctx.close()
            print("rendered", png)
        browser.close()
    if not only:
        import indexpage
        write(os.path.join(HERE, "index.html"), indexpage.make(screens_list(), WIDE, SMALL, kit_jobs))
        print("index.html written")


if __name__ == "__main__":
    main()
