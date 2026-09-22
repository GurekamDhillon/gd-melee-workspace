"""Build the placeholder menu art.

    python pipeline/build.py

HTML + CSS -> headless Chromium -> straight-alpha PNG-32 (sRGB).
Writes:
    out/2x/*.png      authoring resolution (1280x960 presentation)
    out/1x/*.png      640x480 native framebuffer, premultiplied downscale
    out/ora/*.ora     layered source, one file per element
    out/preview/      composed mockups - reference only, NOT deliverables
    out/manifest.json per-file dimensions, format recommendation, notes
"""
import json
import os
import shutil

from PIL import Image, ImageCms, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

import elements
from ora import write_ora

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")

with open(os.path.join(HERE, "style.css"), encoding="utf-8") as fh:
    CSS = fh.read()

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
%(css)s
%(isolate)s
</style></head><body>
<div class="el %(cls)s" style="width:%(w)dpx;height:%(h)dpx">%(body)s</div>
</body></html>"""

# Hide every layer except one, without disturbing layout.  opacity, not
# visibility: a descendant can set visibility:visible and override a hidden
# parent (the hover/press chevron does exactly that), which silently leaks
# one layer's art into all the others.  opacity cannot be overridden.
ISOLATE = '.lyr:not([data-layer="%s"]){opacity:0 !important}'

SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def save_png(img, path):
    """PNG-32, straight (non-premultiplied) alpha, sRGB-tagged."""
    img.convert("RGBA").save(path, "PNG", icc_profile=SRGB, optimize=True)


def downscale_half(img):
    """Premultiply -> resize -> un-premultiply.

    Filtering straight alpha directly pulls the RGB of fully transparent
    pixels (which Chromium leaves at 0,0,0) into every edge texel and the
    art ends up with a dark halo. This is the fix.
    """
    import numpy as np
    arr = np.asarray(img.convert("RGBA")).astype("float64")
    alpha = arr[..., 3:4] / 255.0
    arr[..., :3] *= alpha
    small = Image.fromarray(arr.round().astype("uint8"), "RGBA").resize(
        (max(1, img.width // 2), max(1, img.height // 2)), Image.LANCZOS)
    out = np.asarray(small).astype("float64")
    a2 = out[..., 3:4] / 255.0
    with np.errstate(divide="ignore", invalid="ignore"):
        rgb = np.where(a2 > 0, out[..., :3] / a2, 0.0)
    out[..., :3] = rgb.clip(0, 255)
    return Image.fromarray(out.round().astype("uint8"), "RGBA")


def render(page, item, isolate=None):
    body = "".join(html for _name, html in item["layers"])
    page.set_viewport_size({"width": item["w"], "height": item["h"]})
    page.set_content(PAGE % dict(
        css=CSS,
        isolate=(ISOLATE % isolate) if isolate else "",
        cls=item["cls"], w=item["w"], h=item["h"], body=body))
    shot = page.locator(".el").screenshot(omit_background=True, type="png")
    import io
    return Image.open(io.BytesIO(shot)).convert("RGBA")


def is_pot(n):
    return n > 0 and (n & (n - 1)) == 0


def _frame_onto(canvas, flat, m=16):
    W, H = canvas.size
    ch = flat["frame_corner_tl"].height
    eh = flat["frame_edge_h"]
    ev = flat["frame_edge_v"]
    span_x = W - 2 * m - 2 * ch
    span_y = H - 2 * m - 2 * ch
    top = eh.resize((span_x, eh.height), Image.NEAREST)
    canvas.alpha_composite(top, (m + ch, m))
    canvas.alpha_composite(top.transpose(Image.FLIP_TOP_BOTTOM),
                           (m + ch, H - m - eh.height))
    left = ev.resize((ev.width, span_y), Image.NEAREST)
    canvas.alpha_composite(left, (m, m + ch))
    canvas.alpha_composite(left.transpose(Image.FLIP_LEFT_RIGHT),
                           (W - m - ev.width, m + ch))
    canvas.alpha_composite(flat["frame_corner_tl"], (m, m))
    canvas.alpha_composite(flat["frame_corner_tr"], (W - m - ch, m))
    canvas.alpha_composite(flat["frame_corner_bl"], (m, H - m - ch))
    canvas.alpha_composite(flat["frame_corner_br"], (W - m - ch, H - m - ch))


def _font(size):
    for name in ("arialbd.ttf", "seguisb.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def preview_screen(flat, path_2x, path_1x):
    """The first real target: frame + panel + cursor, i.e. the loading
    screen / trophy-get popup shape. Reference mockup, not a deliverable."""
    W, H = 1280, 960
    canvas = Image.new("RGBA", (W, H), (10, 14, 24, 255))
    _frame_onto(canvas, flat)

    panel = flat["panel_bg"]
    px, py = (W - panel.width) // 2, (H - panel.height) // 2
    canvas.alpha_composite(panel, (px, py))
    canvas.alpha_composite(flat["btn_play_hover"], (px + 256, py + 300))
    canvas.alpha_composite(flat["cursor_hand"], (px + 500, py + 350))

    d = ImageDraw.Draw(canvas)
    sw, sh = int(W * 0.9), int(H * 0.9)          # title-safe, 90%
    d.rectangle([(W - sw) // 2, (H - sh) // 2,
                 (W + sw) // 2 - 1, (H + sh) // 2 - 1],
                outline=(240, 180, 41, 120), width=2)
    d.text(((W - sw) // 2 + 8, (H - sh) // 2 + 8),
           "title-safe 90%  -  576x432 @1x",
           font=_font(18), fill=(240, 180, 41, 170))
    save_png(canvas, path_2x)
    save_png(downscale_half(canvas), path_1x)


def preview_states(flat, path_2x, path_1x):
    """Button state sheet, laid out 1:1 with labels. Reference only."""
    names = ["btn_play_ng", "btn_play_hover", "btn_play_press", "btn_play_disabled"]
    bw, bh, pitch, pad = 512, 128, 176, 40
    W = bw + pad * 2
    H = pad + len(names) * pitch
    canvas = Image.new("RGBA", (W, H), (18, 22, 34, 255))
    d = ImageDraw.Draw(canvas)
    f = _font(20)
    for i, name in enumerate(names):
        y = pad + i * pitch
        d.text((pad, y - 26), name + ".png   %dx%d @2x" % (bw, bh),
               font=f, fill=(150, 165, 190, 255))
        canvas.alpha_composite(flat[name], (pad, y))
    save_png(canvas, path_2x)
    save_png(downscale_half(canvas), path_1x)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for sub in ("2x", "1x", "ora", "preview"):
        os.makedirs(os.path.join(OUT, sub))

    items = elements.catalog()
    flat_2x, manifest = {}, []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb",
                                          "--disable-lcd-text"])
        page = browser.new_page(device_scale_factor=1)

        for item in items:
            flat = render(page, item)
            flat_2x[item["name"]] = flat
            save_png(flat, os.path.join(OUT, "2x", item["name"] + ".png"))

            small = downscale_half(flat)
            save_png(small, os.path.join(OUT, "1x", item["name"] + ".png"))

            layers = [(name, render(page, item, isolate=name))
                      for name, _html in item["layers"]]
            write_ora(os.path.join(OUT, "ora", item["name"] + ".ora"),
                      (item["w"], item["h"]), layers, flat)

            entry = dict(
                name=item["name"],
                file_2x="out/2x/%s.png" % item["name"],
                file_1x="out/1x/%s.png" % item["name"],
                layered="out/ora/%s.ora" % item["name"],
                size_2x=[item["w"], item["h"]],
                size_1x=[item["w"] // 2, item["h"] // 2],
                power_of_two=is_pot(item["w"]) and is_pot(item["h"]),
                multiple_of_four=item["w"] % 4 == 0 and item["h"] % 4 == 0,
                within_1024=item["w"] <= 1024 and item["h"] <= 1024,
                recommended_format=item["fmt"],
                format_rationale=item["why"],
                layers=[n for n, _ in item["layers"]],
                notes=item["note"])
            if "hotspot_1x" in item:
                entry["hotspot_1x"] = item["hotspot_1x"]
            manifest.append(entry)

        preview_screen(flat_2x,
                       os.path.join(OUT, "preview", "screen_1280x960.png"),
                       os.path.join(OUT, "preview", "screen_640x480.png"))
        preview_states(flat_2x,
                       os.path.join(OUT, "preview", "btn_states_2x.png"),
                       os.path.join(OUT, "preview", "btn_states_1x.png"))
        browser.close()

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(
            project="placeholder menu art - pipeline bring-up",
            status="PLACEHOLDER. Proves the PNG -> GX texture -> HSD quad path. "
                   "Not shipping art; the written spec still goes to a human artist.",
            provenance="100% generated from the HTML/CSS in pipeline/. No traced, "
                       "recoloured or referenced Nintendo assets of any kind.",
            design_canvas_1x=[640, 480],
            presentation_2x=[1280, 960],
            title_safe_1x=[576, 432],
            colour_space="sRGB, straight (non-premultiplied) alpha, PNG-32",
            elements=manifest), fh, indent=2)

    for e in manifest:
        print("%-22s %4dx%-4d @2x  %-7s  pot=%s" % (
            e["name"], e["size_2x"][0], e["size_2x"][1],
            e["recommended_format"], e["power_of_two"]))
    print("\n%d elements -> out/" % len(manifest))


if __name__ == "__main__":
    main()
