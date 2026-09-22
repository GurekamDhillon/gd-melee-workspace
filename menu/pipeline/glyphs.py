"""Kit masks: controller button glyphs and the cursor hand.

    python pipeline/glyphs.py      -> out_kit/{2x,1x}/glyph_*.png, cursor_*.png
                                      out_kit/glyphs_manifest.json

All white-on-alpha masks, tinted by material colour. Button glyphs are
original simple shapes with the button's letter knocked out (a letter on a
button is a symbol, identical in every language - no words are baked; START
carries a play mark, the word comes from strings). Sized to sit inline with
footer text: 16px tall at 1x, centred on the text's cap-height middle.

The cursor is the existing hand split into three masks so it can be tinted
per port: ink (outline, also drawn offset as its shadow), fill (port
colour) and detail (finger creases, ink). The port number sits on a sheared
badge quad set from the font atlas - no texture per port.
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
import kit                                                 # noqa: E402
from build import downscale_half, save_png               # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_kit")
FONT = kit.font_path("sans", "black")


def knock(text, x, y, size):
    return ('<text x="%g" y="%g" font-family="kit" font-size="%g" text-anchor="middle" '
            'dominant-baseline="central" fill="#000">%s</text>' % (x, y, size, text))


# name -> (w, h @2x, shape svg (white), knockout svg (black) or "")
GLYPHS = {
    "a":      (32, 32, '<circle cx="16" cy="16" r="15.5"/>', knock("A", 16, 17, 21)),
    "b":      (32, 32, '<circle cx="16" cy="16" r="12.5"/>', knock("B", 16, 17, 16)),
    "x":      (32, 32, '<rect x="6" y="1" width="20" height="30" rx="10"/>', knock("X", 16, 17, 17)),
    "y":      (32, 32, '<rect x="1" y="6" width="30" height="20" rx="10"/>', knock("Y", 16, 17, 17)),
    "z":      (64, 32, '<rect x="4" y="5" width="56" height="22" rx="5"/>', knock("Z", 32, 17, 18)),
    "l":      (64, 32, '<path d="M4 27 V14 Q4 5 16 5 H60 V27 Z"/>', knock("L", 34, 17, 18)),
    "r":      (64, 32, '<path d="M60 27 V14 Q60 5 48 5 H4 V27 Z"/>', knock("R", 30, 17, 18)),
    "start":  (64, 32, '<rect x="6" y="6" width="52" height="20" rx="10"/>',
               '<path d="M28 10.5 L38 16 L28 21.5 Z" fill="#000"/>'),
    "stick":  (32, 32, '<path fill-rule="evenodd" d="M16 0.5 a15.5 15.5 0 1 0 0.01 0 Z '
                       'M16 4.5 a11.5 11.5 0 1 0 0.01 0 Z"/><circle cx="16" cy="16" r="7"/>', ""),
    "cstick": (32, 32, '<circle cx="16" cy="16" r="12.5"/>', knock("C", 16, 17, 16)),
    "dpad":   (32, 32, '<path d="M11 1 H21 V11 H31 V21 H21 V31 H11 V21 H1 V11 H11 Z"/>',
               '<circle cx="16" cy="16" r="3" fill="#000"/>'),
    # kit mark for checkbox cells (not a button): a heavy check, hard corners
    "check":  (32, 32, '<path d="M3 17 L9 11 L14 16 L25 4 L31 10 L14 27 Z"/>', ""),
}

# The existing hand (elements.py), 32 grid, drawn at 64x64 @2x.
HAND = "M12 4 h4 v10 h2 v-3 h4 v3 h2 v-2 h4 v2 h2 v9 q0 4 -4 4 h-14 v-23 z"
CURSOR = {
    "cursor_ink":    '<path d="%s" fill="#fff" stroke="#fff" stroke-width="3" '
                     'stroke-linejoin="round"/>' % HAND,
    "cursor_fill":   '<path d="%s" fill="#fff"/>' % HAND,
    "cursor_detail": '<g stroke="#fff" stroke-width="1.5" stroke-linecap="round" fill="none">'
                     '<path d="M18 15 v4"/><path d="M22 15 v4"/><path d="M26 16 v3"/></g>',
}
HOTSPOT_1X = [14, 4]
SHADOW_OFFSET_1X = [1.5, 1.5]

TINT = {
    "default": "bone",
    "suggested": {"a": "ok", "b": "danger"},
    "why": "A/B tints are optional kit colours for confirm/back, never hardware "
           "colours; everything else is bone, or disabled when the action is unavailable",
}


def page_html(font_b64, w, h, body):
    return ('<!doctype html><html><head><style>'
            '@font-face{font-family:kit;src:url(data:font/otf;base64,%s)}'
            'html,body{margin:0;background:transparent}</style></head><body>'
            '<svg id="s" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>'
            '</body></html>' % (font_b64, w, h, w, h, body))


def shot(page, font_b64, w, h, body):
    page.set_viewport_size({"width": max(w, 64), "height": max(h, 64)})
    page.set_content(page_html(font_b64, w, h, body))
    page.evaluate("document.fonts.ready")
    png = page.locator("#s").screenshot(omit_background=True, type="png")
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    out = Image.new("RGBA", img.size, (255, 255, 255, 0))
    out.putalpha(img.getchannel("A"))           # masks are white + alpha only
    return out


def masked(shape, knockout, w, h, name):
    if not knockout:
        return '<g fill="#fff">%s</g>' % shape
    return ('<defs><mask id="k%s" maskUnits="userSpaceOnUse" x="0" y="0" width="%d" '
            'height="%d"><rect width="%d" height="%d" fill="#fff"/>%s</mask></defs>'
            '<g fill="#fff" mask="url(#k%s)">%s</g>' % (name, w, h, w, h, knockout, name, shape))


def main():
    for sub in ("2x", "1x", "preview"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    font_b64 = base64.b64encode(open(FONT, "rb").read()).decode()
    rows, imgs, errs = [], {}, []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(device_scale_factor=1)
        for name, (w, h, shape, ko) in GLYPHS.items():
            img = shot(page, font_b64, w, h, masked(shape, ko, w, h, name))
            imgs["glyph_" + name] = img
            rows.append(dict(name="glyph_" + name, size_2x=[w, h], size_1x=[w // 2, h // 2],
                             format="I4", why="white mask, tinted; 16 edge levels are "
                                              "plenty at 16px", kind="button_glyph"))
        for name, body in CURSOR.items():
            img = shot(page, font_b64, 64, 64, '<g transform="scale(2)">%s</g>' % body)
            imgs[name] = img
            rows.append(dict(name=name, size_2x=[64, 64], size_1x=[32, 32], format="I4",
                             why="white mask; the old cursor_hand was RGBA8 with colour "
                                 "baked in, which cannot be tinted per port",
                             kind="cursor"))
        browser.close()

    for name, img in imgs.items():
        save_png(img, os.path.join(OUT, "2x", name + ".png"))
        save_png(downscale_half(img), os.path.join(OUT, "1x", name + ".png"))
        w, h = img.size
        if w & (w - 1) or h & (h - 1) or w > 1024 or h > 1024:
            errs.append("%s not POT" % name)
        if img.getchannel("A").getbbox() is None:
            errs.append("%s is empty" % name)
    for r in rows:
        r["file_2x"] = "out_kit/2x/%s.png" % r["name"]
        r["file_1x"] = "out_kit/1x/%s.png" % r["name"]
        r["bytes_2x"] = r["size_2x"][0] * r["size_2x"][1] // 2

    # knockouts must survive at 1x: some pixel inside the shape is clear
    for name, (w, h, shape, ko) in GLYPHS.items():
        if not ko:
            continue
        small = downscale_half(imgs["glyph_" + name]).getchannel("A")
        cx, cy = w // 4, h // 4
        core = small.crop((cx - 3, cy - 3, cx + 3, cy + 3))
        if core.getextrema()[0] > 128:
            errs.append("glyph_%s: knockout closes up at 1x" % name)

    spec = dict(
        button_glyphs=dict(
            names=["glyph_" + n for n in GLYPHS if n != "check"],
            marks=["glyph_check"],
            height_1x=16, placement="vertically centred on the text's cap-height "
            "middle; 4px gap before the hint text", tint=TINT,
            replaces=["glyph_a", "glyph_b"],
            note="Directional hints: pair glyph_dpad or glyph_stick with an arrow "
                 "from the font atlas; no per-direction textures."),
        cursor=dict(
            hotspot_1x=HOTSPOT_1X,
            layers=[dict(texture="cursor_ink", colour="ink", offset_1x=SHADOW_OFFSET_1X,
                         role="shadow"),
                    dict(texture="cursor_ink", colour="ink", role="outline"),
                    dict(texture="cursor_fill", colour="bone | port colour", role="fill"),
                    dict(texture="cursor_detail", colour="ink", role="detail")],
            variants=dict(default=dict(fill="bone", badge=None),
                          **{p: dict(fill=p, badge=dict(text="1234"[i], colour=p))
                             for i, p in enumerate(["p1", "p2", "p3", "p4"])},
                          cpu=dict(fill="cpu", badge=dict(text="CPU", colour="cpu"))),
            badge=dict(kind="flat sheared quad", colour="ink", anchor_1x=[22, 22],
                       height_1x=14, pad_x_1x=4, text_role="caption",
                       text_colour="the variant's port colour",
                       note="width = text advance + 2*pad; sheared by kit SHEAR like "
                            "every other plate; port strings come from the engine"),
        ),
        textures=rows)
    with open(os.path.join(OUT, "glyphs_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)

    # preview: every glyph at 1x and 2x on the footer ink, then the cursor variants
    ink = kit.K.hexrgb(kit.PALETTE["ink"])
    sheet = Image.new("RGB", (900, 260), ink)
    x = 16
    for name in GLYPHS:
        g = imgs["glyph_" + name]
        col = kit.K.hexrgb(kit.PALETTE[TINT["suggested"].get(name, "bone")])
        sheet.paste(Image.new("RGB", g.size, col), (x, 16), g)
        g1 = downscale_half(g)
        sheet.paste(Image.new("RGB", g1.size, col), (x, 60), g1)
        x += g.width + 12
    x = 16
    for vname, v in spec["cursor"]["variants"].items():
        fill = kit.K.hexrgb(kit.PALETTE["bone"] if v["fill"] == "bone" else kit.PORTS[v["fill"]])
        base = (x, 120)
        sh = imgs["cursor_ink"]
        sheet.paste(Image.new("RGB", sh.size, ink), (base[0] + 3, base[1] + 3), sh)
        sheet.paste(Image.new("RGB", sh.size, (60, 70, 90)), base, sh)
        sheet.paste(Image.new("RGB", sh.size, fill), base, imgs["cursor_fill"])
        sheet.paste(Image.new("RGB", sh.size, ink), base, imgs["cursor_detail"])
        x += 100
    sheet.save(os.path.join(OUT, "preview", "glyphs_2x.png"))

    total = sum(r["bytes_2x"] for r in rows)
    print("glyphs: %d button glyphs, %d cursor masks, %.1f KB @2x I4"
          % (len(GLYPHS), len(CURSOR), total / 1024))
    if errs:
        print("CHECKS FAILED:")
        for e in errs:
            print("  - " + e)
        return 1
    print("glyph checks ok: POT, non-empty, knockouts open at 1x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
