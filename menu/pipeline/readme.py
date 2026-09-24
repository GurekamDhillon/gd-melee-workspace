"""Artwork for the project's GitHub README, in the kit's rectangular style.

    python pipeline/readme.py        -> out_readme/*.png, out_readme/README_ART.md

Words come from pipeline/readme_text.json; edit that and rebuild. Everything is
drawn here from HTML/CSS/SVG with the kit's palette (kit.py) and the kit's OFL
fonts (Source Sans 3), rendered by headless Chromium. Original art only: no
Nintendo, HAL or Melee logos, lettering, characters, stages or screenshots, and
nothing traced from them. The wordmark is typeset, not drawn after any logo.

Style: one shear for everything (skewX -14deg = the kit's S = 0.25), flat colour,
hard ink shadows at a fixed offset, cobalt faces, gold for emphasis.

Checks, on every build (non-zero exit on failure):
  * every text box fits its text (no overflow, measured in the page);
  * boxes that must not touch don't overlap;
  * the social card keeps all text inside its safe area;
  * tagline and feature text contrast >= 4.5:1 on both variants.
"""
import base64
import io
import json
import os
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit                                                  # noqa: E402
import icons as I                                           # noqa: E402

K = kit.K
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_readme")
TEXT = json.load(open(os.path.join(HERE, "readme_text.json"), encoding="utf-8"))
PAL = kit.PALETTE
VS = kit.SECTIONS["versus"]
SKEW = -14.036                     # atan(0.25): the kit's shear, in CSS degrees

VARIANTS = {
    "dark":  dict(bg=VS["bg"], band=VS["band"], shadow=PAL["ink"], word=PAL["bone"],
                  page="#0d1117"),
    "light": dict(bg="#f2efe4", band="#e2e0f0", shadow=PAL["ink"], word=VS["face"],
                  page="#ffffff"),
}


# ------------------------------------------------------------ icons (64 grid)
def _body(name):
    c, r, rr, st, P, S = I.circle, I.rect, I.rrect, I.star, I.P, I.S
    if name == "rollback":
        return (S("M50 18 A24 24 0 1 0 56 36", 6.5) + P("M44 6 L60 12 L50 26 Z") +
                P("M34 22 L20 32 L34 42 Z") + P("M46 22 L32 32 L46 42 Z"))
    if name == "hd":
        return (S(rr(4, 6, 56, 38, 3), 5.5) + P(r(26, 46, 12, 8)) + P(r(16, 54, 32, 6)) +
                S("M14 22 V16 H22 M42 16 H50 V22 M50 28 V34 H42 M22 34 H14 V28", 4.5))
    if name == "replay":
        holes = "".join(P(r(x, 10, 6, 5)) + P(r(x, 49, 6, 5)) for x in (10, 22, 34, 46))
        return dict(shape=P(rr(2, 6, 60, 52, 4)),
                    knock=holes + P(r(8, 18, 48, 28)) + '<path d="M26 22 L42 32 L26 42 Z" '
                                                          'fill="#fff"/>')
    if name == "mex":
        return P("M6 22 H22 A7 7 0 1 1 36 22 H52 V36 A7 7 0 1 1 52 50 V60 H6 Z")
    if name == "ucf":
        return (S("M22 4 H42 L60 22 V42 L42 60 H22 L4 42 V22 Z", 5) + P(c(32, 32, 11)) +
                P(r(30, 10, 4, 6)) + P(r(30, 48, 4, 6)) + P(r(10, 30, 6, 4)) + P(r(48, 30, 6, 4)))
    if name == "sync":
        wave = "M2 %g H14 V%g H30 V%g H46 V%g H62"
        return (S(wave % (24, 10, 24, 10), 5.5) + S(wave % (56, 42, 56, 42), 5.5) +
                P(r(22, 30, 20, 4.5)) + P(r(22, 37, 20, 4.5)))
    if name == "online":
        return I.ICONS["ico_online"]["body"]
    if name == "strike":   # the lobby's stage strikes: four stages, one picked, one struck
        return (S(r(6, 8, 22, 20), 5) + P(r(36, 8, 22, 20)) + S(r(6, 36, 22, 20), 5) +
                S(r(36, 36, 22, 20), 5) + S("M8 38 L26 54 M26 38 L8 54", 5))
    if name == "roster":   # a grid of fighter slots, the last one open
        cells = "".join(P(r(1 + col * 16, 8 + row * 16, 13, 13))
                        for row in range(3) for col in range(4) if (row, col) != (2, 3))
        return cells + S(r(50, 42, 10, 10), 3.5)
    if name == "code":     # </>
        return S("M18 18 L4 32 L18 46 M46 18 L60 32 L46 46 M38 12 L26 52", 7)
    if name == "launcher":  # a window with a play button
        return (S(rr(4, 10, 56, 44, 4), 5) + P(r(4, 10, 56, 9)) + P("M26 26 L42 36 L26 46 Z"))
    raise KeyError(name)


def icon_svg(name, colour, px):
    if name.startswith("ico_"):  # a kit menu icon (training, options...), as the hub draws it
        return hub_icon(name, colour, px)
    b = _body(name)
    if isinstance(b, dict):
        inner = ('<defs><mask id="k_%s" maskUnits="userSpaceOnUse" x="-2" y="-2" width="68" '
                 'height="68"><rect x="-2" y="-2" width="68" height="68" fill="#fff"/>'
                 '<g fill="#000">%s</g></mask></defs><g fill="%s" mask="url(#k_%s)">%s</g>'
                 % (name, b["knock"], colour, name, b["shape"]))
    else:
        inner = '<g fill="%s">%s</g>' % (colour, b.replace('stroke="#fff"',
                                                           'stroke="%s"' % colour))
    return ('<svg width="%d" height="%d" viewBox="0 0 64 64" style="display:block">%s</svg>'
            % (px, px, inner))


def hub_icon(name, colour, px):
    ic = I.ICONS[name]
    b = ic["body"] if ic["body"] is not None else None
    if b is None:
        inner = ('<defs><mask id="h_%s" maskUnits="userSpaceOnUse" x="-2" y="-2" width="68" '
                 'height="68"><rect x="-2" y="-2" width="68" height="68" fill="#fff"/>'
                 '<g fill="#000">%s</g></mask></defs><g fill="%s" mask="url(#h_%s)">%s</g>'
                 % (name, ic["knock"], colour, name, ic["shape"]))
    else:
        inner = '<g fill="%s">%s</g>' % (colour, b.replace('stroke="#fff"',
                                                           'stroke="%s"' % colour))
    return ('<svg width="%d" height="%d" viewBox="0 0 64 64" style="display:block">%s</svg>'
            % (px, px, inner))


# ------------------------------------------------------------ page scaffolding
def fonts_css():
    out = []
    for w, f in (("900", "SourceSans3-Black.otf"), ("700", "SourceSans3-Bold.otf")):
        b64 = base64.b64encode(open(os.path.join(ROOT, "SourceSans3", f), "rb").read()).decode()
        out.append("@font-face{font-family:kit;font-weight:%s;src:url(data:font/otf;base64,%s)}"
                   % (w, b64))
    return "".join(out)


FONTS_CSS = None


def page_html(w, h, bg, body, extra_css=""):
    return ('<!doctype html><html><head><style>%s'
            'html,body{margin:0;padding:0;background:transparent}'
            '#c{position:relative;width:%dpx;height:%dpx;overflow:hidden;background:%s;'
            'font-family:kit}'
            '.a{position:absolute}'
            '#sk{position:absolute;left:0;top:0;width:100%%;height:100%%;'
            'transform:skewX(%gdeg);transform-origin:0 50%%}'
            '.t{white-space:nowrap;line-height:1}'
            '%s</style></head><body><div id="c"><div id="sk">%s</div></div></body></html>'
            % (FONTS_CSS, w, h, bg, SKEW, extra_css, body))


def bands(v, w, h, xs):
    return "".join('<div class="a sk" style="left:%dpx;top:0;width:%dpx;height:%dpx;'
                   'background:%s"></div>' % (x, bw, h, v["band"])
                   for x, bw in xs)


def wordmark(v, x, y, name_px, tag_px):
    """GD'S on a gold tag, MELEE below in the variant's word colour with a hard ink
    shadow, an ink rule running out from the tag like the kit header."""
    tag, name = TEXT["wordmark"]["tag"].upper(), TEXT["wordmark"]["name"].upper()
    sh = max(4, round(name_px * 0.05))
    return (
        '<div class="a sk" data-box="wordmark" style="left:%dpx;top:%dpx">'
        '<div class="t" style="display:inline-block;background:%s;color:%s;'
        'font-weight:900;font-size:%dpx;padding:%dpx %dpx %dpx %dpx;letter-spacing:1px;'
        'box-shadow:%dpx %dpx 0 %s">%s</div>'
        '<div class="t" style="color:%s;font-weight:900;font-size:%dpx;'
        'letter-spacing:%dpx;margin-top:%dpx;text-shadow:%dpx %dpx 0 %s">%s</div></div>'
        % (x, y, PAL["gold"], PAL["ink"], tag_px, tag_px * 0.14, tag_px * 0.34, tag_px * 0.06,
           tag_px * 0.30, sh * 0.6, sh * 0.6, v["shadow"], tag,
           v["word"], name_px, max(1, name_px // 60), -name_px * 0.10, sh, sh, v["shadow"], name))


def strip(x, y, w, h, text, px, fit_id="tagline"):
    return ('<div class="a sk" data-box="tagline" style="left:%dpx;top:%dpx;width:%dpx;'
            'height:%dpx;background:%s">'
            '<div class="a" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;background:%s">'
            '</div><div class="a t" data-fit="%s" style="left:%dpx;top:0;right:%dpx;'
            'height:%dpx;line-height:%dpx;color:%s;font-weight:700;font-size:%dpx;'
            'overflow:hidden">%s</div></div>'
            % (x, y, w, h, PAL["ink"], h * 0.28, h * 0.28, h * 0.22, h * 0.44, PAL["gold"],
               fit_id, h * 0.8, h * 0.4, h, h, PAL["bone"], px, text))


def cluster(v, x, y, w, h, icons, g=10):
    """A little hub: a gold hero tile and two cobalt tiles stepping down."""
    hw = round(w * 0.52)
    sw = w - hw - g
    h1 = round((h - g) * 0.57)
    h2 = h - g - h1
    shadow = 8
    tiles = [(x, y, hw, h, PAL["gold"], PAL["gold_dk"], icons[0], h * 0.42),
             (x + hw + g, y, sw, h1, VS["face"], VS["face_hi"], icons[1], h1 * 0.5),
             (x + hw + g, y + h1 + g, sw, h2, VS["face"], VS["face_hi"], icons[2], h2 * 0.55)]
    out = ['<div class="a sk" data-box="cluster" style="left:%dpx;top:%dpx;width:%dpx;'
           'height:%dpx;background:%s;box-shadow:%dpx %dpx 0 %s"></div>'
           % (x - 6, y - 6, w + 12, h + 12, PAL["ink"], shadow, shadow, v["shadow"])]
    for tx, ty, tw, th, face, ic_col, ic, ipx in tiles:
        out.append('<div class="a sk" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;'
                   'background:%s"><div class="a" style="right:%dpx;top:%dpx">%s</div></div>'
                   % (tx, ty, tw, th, face, th * 0.12 + 4, th * 0.12, hub_icon(ic, ic_col, ipx)))
    return "".join(out)


# ------------------------------------------------------------ the assets
def banner(v):
    W, H = 1600, 400
    b = bands(v, W, H, [(40, 60), (1380, 110), (1520, 24)])
    b += wordmark(v, 150, 48, 170, 54)
    b += strip(118, 300, 1000, 50, TEXT["tagline"], 26)
    b += cluster(v, 1180, 70, 300, 250, ["ico_online", "ico_movies", "ico_options"])
    return W, H, v["bg"], b


def social(v):
    W, H = 1280, 640
    b = bands(v, W, H, [(30, 70), (1110, 120), (1250, 26)])
    b += wordmark(v, 150, 138, 200, 64)
    b += strip(128, 472, 1030, 58, TEXT["social_tagline"], 27)
    b += cluster(v, 830, 130, 300, 250, ["ico_online", "ico_movies", "ico_options"])
    return W, H, v["bg"], b


SOCIAL_SAFE = (64, 48, 1216, 592)


def tile(v, f):
    W, H = 400, 200
    b = bands(v, W, H, [(352, 26)])
    # card: cobalt face, ink shadow, gold icon block with ink icon
    b += ('<div class="a sk" style="left:20px;top:22px;width:352px;height:150px;background:%s;'
          'box-shadow:7px 7px 0 %s"></div>' % (VS["face"], v["shadow"]))
    b += ('<div class="a sk" style="left:20px;top:22px;width:82px;height:150px;background:%s">'
          '<div class="a" style="left:9px;top:43px">%s</div></div>'
          % (PAL["gold"], icon_svg(f["icon"], PAL["ink"], 64)))
    b += ('<div class="a sk" data-box="title" style="left:120px;top:50px;width:240px;'
          'height:32px"><div class="t" data-fit="title_%s" style="width:240px;height:32px;'
          'overflow:hidden;color:%s;font-weight:900;font-size:22px;line-height:32px">%s</div>'
          '</div>' % (f["id"], PAL["gold_lt"], f["title"]))
    b += ('<div class="a sk" data-box="text" style="left:120px;top:88px;width:236px;'
          'height:74px"><div data-fit="text_%s" style="width:236px;height:74px;overflow:hidden;'
          'color:%s;font-weight:700;font-size:16px;line-height:24px;text-wrap:balance">%s</div></div>'
          % (f["id"], PAL["bone"], f["text"]))
    return W, H, v["bg"], b


def divider():
    W, H = 1600, 32
    b = ('<div class="a sk" style="left:40px;top:12px;width:1480px;height:8px;background:%s">'
         '</div><div class="a sk" style="left:40px;top:6px;width:220px;height:20px;'
         'background:%s;box-shadow:4px 4px 0 %s"></div>'
         % (VS["face"], PAL["gold"], PAL["ink"]))
    return W, H, "transparent", b


# ------------------------------------------------------------ render + check
CHECK_JS = """() => {
  const out = {fit: [], boxes: []};
  for (const e of document.querySelectorAll('[data-fit]')) {
    out.fit.push({id: e.dataset.fit, sw: e.scrollWidth, cw: e.clientWidth,
                  sh: e.scrollHeight, ch: e.clientHeight});
  }
  for (const e of document.querySelectorAll('[data-box]')) {
    const r = e.getBoundingClientRect();
    out.boxes.push({id: e.dataset.box, x0: r.left, y0: r.top, x1: r.right, y1: r.bottom});
  }
  for (const e of document.querySelectorAll('[data-fit]')) {
    const r = e.getBoundingClientRect();
    out.boxes.push({id: 'text:' + e.dataset.fit, x0: r.left, y0: r.top, x1: r.right,
                    y1: r.bottom});
  }
  return out;
}"""


def shoot(page, w, h, bg, body):
    page.set_viewport_size({"width": w, "height": h})
    page.set_content(page_html(w, h, bg, body))
    page.evaluate("document.fonts.ready")
    info = page.evaluate(CHECK_JS)
    png = page.locator("#c").screenshot(type="png", omit_background=(bg == "transparent"))
    return Image.open(io.BytesIO(png)), info


def overlaps(a, b):
    return a["x0"] < b["x1"] and b["x0"] < a["x1"] and a["y0"] < b["y1"] and b["y0"] < a["y1"]


MD_HEAD = """# README artwork

Built by `python pipeline/readme.py` from `pipeline/readme_text.json`. To change a word, edit
that JSON and rebuild. Every image is original: HTML/CSS/SVG with the kit's palette and the
kit's OFL fonts (Source Sans 3), rendered by headless Chromium. There are no Nintendo, HAL or
Melee logos, lettering, characters, stages or screenshots, and nothing is traced from them.
The wordmark is typeset in Source Sans 3 Black and sheared at the kit's 14 degrees; it is
the placeholder project wordmark for section 6.

The snippets assume the images are copied to `docs/readme/` in the repo. Adjust the paths if
they go elsewhere. Nothing here has been placed in any README.

## Files

| File | Size | Pairing | Use |
|---|---|---|---|
"""

MD_USE = {"banner": "hero banner, top of the README", "feature": "feature tile",
          "social": "repo Settings > Social preview (upload; not referenced in the README)",
          "divider": "section divider (transparent; reads on both themes)"}

MD_TILE = """    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_{id}_dark.png">
      <img alt="{title}: {text}" src="docs/readme/feature_{id}_light.png" width="400">
    </picture></td>
"""

MD_TAIL = """</table>
```

## Divider

```html
<p align="center"><img alt="" src="docs/readme/divider.png" width="800"></p>
```

## Social preview

Upload `social_preview.png` (1280x640) under the repo's **Settings > General > Social
preview**. All of its text sits at least 64 px from the sides and 48 px from the top and
bottom, so crops don't cut it.

## Checks (all pass on every build)

- Every text box fits its text, measured in the page (titles one line, descriptions at most
  three balanced lines, the tagline one line).
- The wordmark, tagline and art cluster never overlap.
- The social card's text stays inside its safe area.
- Contrast is at least 4.5:1 for every text: {contrast}.
"""

MD_MID = """
`@2x` banners are the same art at 3200x800 for sharp display on HiDPI screens. The feature
tiles are 800x400, drawn at 2x for a 400x200 display size.

## Hero banner (light/dark)

GitHub picks the source through `prefers-color-scheme`:

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/readme/banner_dark@2x.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/readme/banner_light@2x.png">
    <img alt="{alt}" src="docs/readme/banner_light@2x.png" width="800">
  </picture>
</p>
```

## Features

A two-column grid. Each tile is a `<picture>` so it follows the theme, and the tile's words
repeat in `alt` for screen readers:

```html
<table>
"""


def write_md(files, contrast):
    L = [MD_HEAD]
    for f in files:
        kind = f["file"].split("_")[0].split(".")[0]
        pair = {"dark": "dark (pair: `%s`)" % f["file"].replace("dark", "light"),
                "light": "light (pair: `%s`)" % f["file"].replace("light", "dark"),
                "both": "one file for both themes"}[f["variant"]]
        if f["file"] == "social_preview.png":
            pair = "one file (GitHub shows it on neither theme)"
        L.append("| `%s` | %dx%d | %s | %s |\n" % (f["file"], f["size"][0], f["size"][1], pair,
                                                  MD_USE.get(kind, kind)))
    alt = "%s %s - %s" % (TEXT["wordmark"]["tag"], TEXT["wordmark"]["name"], TEXT["tagline"])
    L.append(MD_MID.replace("{alt}", alt.replace('"', "&quot;")))
    feats = TEXT["features"]
    for i in range(0, len(feats), 2):
        L.append("  <tr>\n")
        for f in feats[i:i + 2]:
            L.append(MD_TILE.format(id=f["id"], title=f["title"], text=f["text"]))
        L.append("  </tr>\n")
    L.append(MD_TAIL.replace("{contrast}", "; ".join("%s %.2f:1" % kv for kv in contrast.items()
                                                      if "GitHub" not in kv[0])))
    with open(os.path.join(OUT, "README_ART.md"), "w", encoding="utf-8") as fh:
        fh.write("".join(L))


def main():
    global FONTS_CSS
    sys.stdout.reconfigure(encoding="utf-8")
    FONTS_CSS = fonts_css()
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".png"):
            os.remove(os.path.join(OUT, f))
    errs, files = [], []

    jobs = []
    for vn, v in VARIANTS.items():
        jobs.append(("banner_%s" % vn, banner(v), (1, 2), vn))
        for f in TEXT["features"]:
            jobs.append(("feature_%s_%s" % (f["id"], vn), tile(v, f), (2,), vn))
    jobs.append(("social_preview", social(VARIANTS["dark"]), (1,), "dark"))
    jobs.append(("divider", divider(), (1,), "both"))

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        pages = {d: browser.new_page(device_scale_factor=d) for d in (1, 2)}
        for name, (w, h, bg, body), scales, vn in jobs:
            for d in scales:
                img, info = shoot(pages[d], w, h, bg, body)
                suffix = "" if (d == 1 or scales == (2,)) else "@2x"
                fn = "%s%s.png" % (name, suffix)
                img.save(os.path.join(OUT, fn))
                files.append(dict(file=fn, size=list(img.size), variant=vn))
                if d != scales[0]:
                    continue
                for fi in info["fit"]:
                    if fi["sw"] > fi["cw"] + 0.5 or fi["sh"] > fi["ch"] + 0.5:
                        errs.append("%s: text '%s' overflows its box (%dx%d in %dx%d)"
                                    % (name, fi["id"], fi["sw"], fi["sh"], fi["cw"], fi["ch"]))
                boxes = [b for b in info["boxes"] if not b["id"].startswith("text:")]
                for i in range(len(boxes)):
                    for j in range(i + 1, len(boxes)):
                        a, b2 = boxes[i], boxes[j]
                        if a["id"] != b2["id"] and overlaps(a, b2) and \
                                {a["id"], b2["id"]} != {"title", "text"}:
                            errs.append("%s: %s overlaps %s" % (name, a["id"], b2["id"]))
                if name == "social_preview":
                    x0, y0, x1, y1 = SOCIAL_SAFE
                    for b2 in info["boxes"]:
                        if b2["x0"] < x0 or b2["y0"] < y0 or b2["x1"] > x1 or b2["y1"] > y1:
                            errs.append("social: %s leaves the safe area %s: %s"
                                        % (b2["id"], SOCIAL_SAFE, [round(b2[k], 1) for k in
                                                                    ("x0", "y0", "x1", "y1")]))
                for b2 in info["boxes"]:
                    if b2["x0"] < 0 or b2["y0"] < 0 or b2["x1"] > w or b2["y1"] > h:
                        errs.append("%s: %s leaves the canvas" % (name, b2["id"]))
        browser.close()

    # contrast: tagline and feature text on both variants (the strip and card are the
    # same in both, so the page colour never touches text - checked anyway)
    rep = {}
    pairs = [("tagline (bone on ink strip)", PAL["bone"], PAL["ink"]),
             ("feature title (gold_lt on cobalt)", PAL["gold_lt"], VS["face"]),
             ("feature text (bone on cobalt)", PAL["bone"], VS["face"]),
             ("wordmark tag (ink on gold)", PAL["ink"], PAL["gold"])]
    for vn, v in VARIANTS.items():
        pairs.append(("wordmark name on %s bg" % vn, v["word"], v["bg"]))
    for n, fg, bg in pairs:
        c = K.contrast(K.hexrgb(fg), K.hexrgb(bg))
        rep[n] = round(c, 2)
        if c < 4.5:
            errs.append("contrast %s %.2f:1 < 4.5" % (n, c))
    # the banner edge against GitHub's page, so the banner reads as a panel
    for vn, v in VARIANTS.items():
        rep["banner %s vs GitHub page" % vn] = round(K.contrast(K.hexrgb(v["bg"]),
                                                                K.hexrgb(v["page"])), 2)

    json.dump(dict(files=files, contrast=rep), open(os.path.join(OUT, "readme_art.json"), "w",
                                                     encoding="utf-8"), indent=1)
    write_md(files, rep)
    for f in files:
        print("  %-34s %4dx%-4d %s" % (f["file"], f["size"][0], f["size"][1], f["variant"]))
    print("contrast:", rep)
    if errs:
        print("\nCHECKS FAILED (%d):" % len(errs))
        for e in errs[:40]:
            print("  - " + e)
        return 1
    print("\nreadme checks ok: text fits every box, no overlaps, social text inside its safe "
          "area, tagline/feature contrast >= 4.5:1 on both variants")
    return 0


if __name__ == "__main__":
    sys.exit(main())
