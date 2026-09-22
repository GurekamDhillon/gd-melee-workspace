"""Build the hub main-menu prototype.

    python pipeline/hub.py

Proves "geometry, not texture": the screen is flat-colour quads plus a few
white alpha masks (labels, icons) tinted by material colour. Writes:

    out_hub/hub_layout.json   the source of truth - every quad, vertex, colour,
                              UV and state rule the engine needs
    out_hub/tex/2x, tex/1x    the only textures: white-on-alpha PNG-32 masks
    out_hub/preview/          drawn FROM hub_layout.json, with the textures
                              pre-quantised to I4 - i.e. what the engine draws

Separate from build.py on purpose: that one wipes out/ on every run.
"""
import base64
import io
import json
import math
import os
import shutil
import sys

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hub_layout as L                                    # noqa: E402
from build import downscale_half, save_png               # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_hub")

# ------------------------------------------------------------ textures
# Labels are set upright. The quad's shear is what makes them italic.
FONTS = {
    # single quotes only: these land inside a double-quoted style attribute
    "hero":  "88px 'Arial Black', 'Segoe UI Black', sans-serif",
    "tile":  "36px 'Arial Black', 'Segoe UI Black', sans-serif",
    "title": "30px 'Arial Black', 'Segoe UI Black', sans-serif",
    "desc":  "bold 24px Arial, 'Segoe UI', sans-serif",
}
TRACK = {"hero": 4, "tile": 2, "title": 3, "desc": 0}
PAD = 4


def _circle(cx, cy, r):
    return ("M%g %g a%g %g 0 1 0 %g 0 a%g %g 0 1 0 %g 0 Z"
            % (cx - r, cy, r, r, 2 * r, r, r, -2 * r))


def _gear(cx=32, cy=32, teeth=8, r_out=29, r_root=22, hole=9):
    pts = []
    step = 2 * math.pi / teeth
    for i in range(teeth):
        a = i * step - math.pi / 2
        for da, r in ((-0.30, r_root), (-0.16, r_out), (0.16, r_out), (0.30, r_root)):
            ang = a + da * step * 1.6
            pts.append("%.2f %.2f" % (cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return "M" + " L".join(pts) + " Z " + _circle(cx, cy, hole)


# Original pictograms on a 64 grid. White silhouettes only - colour is
# applied by the material, so the same texture serves every state.
ICONS = {
    # two chevrons clashing, spark above. Both wound the same way, or nonzero
    # fill cancels out where they overlap and leaves a hole in the middle.
    "versus": ("M4 12 L14 12 L36 32 L14 52 L4 52 L26 32 Z "
               "M60 12 L38 32 L60 52 L50 52 L28 32 L50 12 Z "
               "M32 1 L35 8 L42 11 L35 14 L32 21 L29 14 L22 11 L29 8 Z"),
    # bullseye, alternating rings via even-odd
    "solo": " ".join(_circle(32, 32, r) for r in (29, 22, 15, 9, 4)),
    # gem on a stepped pedestal
    "collection": ("M32 3 L47 21 L32 39 L17 21 Z "
                   "M14 43 L50 43 L50 50 L14 50 Z "
                   "M6 53 L58 53 L58 61 L6 61 Z"),
    "options": _gear(),
}
ICON_SIZE = {"versus": 256, "solo": 128, "collection": 128, "options": 128}
# even-odd only where holes are the design (rings, gear bore); elsewhere it
# would punch a hole wherever two shapes overlap
FILL_RULE = {"versus": "nonzero", "solo": "evenodd",
             "collection": "nonzero", "options": "evenodd"}


def pot(n, lo=8):
    p = lo
    while p < n:
        p *= 2
    return p


def _shot(page, html, w, h):
    page.set_viewport_size({"width": max(w, 64), "height": max(h, 64)})
    page.set_content('<!doctype html><html><head><style>'
                     'html,body{margin:0;background:transparent}'
                     '.cv{position:relative;overflow:hidden;width:%dpx;height:%dpx}'
                     '</style></head><body><div class="cv">%s</div></body></html>'
                     % (w, h, html))
    png = page.locator(".cv").screenshot(omit_background=True, type="png")
    return Image.open(io.BytesIO(png)).convert("RGBA")


def text_texture(page, text, style):
    """Render big, crop to the actual ink, then pick the smallest POT canvas.
    Sizing from the DOM line box instead wastes up to 3/4 of the texture on
    ascender/descender space the glyphs never touch."""
    span = ('<span style="position:absolute;left:%dpx;top:%dpx;'
            'white-space:nowrap;line-height:1;color:#fff;font:%s;'
            'letter-spacing:%dpx">%s</span>'
            % (PAD * 4, PAD * 4, FONTS[style], TRACK[style], text))
    big = _shot(page, span, 2048, 256)
    x0, y0, x1, y1 = big.getchannel("A").getbbox()
    ink = big.crop((x0 - 1, y0 - 1, x1 + 1, y1 + 1))
    out = Image.new("RGBA", (pot(ink.width + 2, 4), pot(ink.height + 2, 4)), (0, 0, 0, 0))
    out.paste(ink, (1, 1))
    return out


def icon_texture(page, name):
    n = ICON_SIZE[name]
    svg = ('<svg width="%d" height="%d" viewBox="0 0 64 64">'
           '<path d="%s" fill="#fff" fill-rule="%s"/></svg>'
           % (n, n, ICONS[name], FILL_RULE[name]))
    return _shot(page, svg, n, n)


def whiten(img):
    """Mask textures are pure white + alpha, so the converter's output is
    determined by alpha alone. Kills any AA colour Chromium left in RGB."""
    a = img.getchannel("A")
    out = Image.new("RGBA", img.size, (255, 255, 255, 0))
    out.putalpha(a)
    return out


def meta(name, img, tight):
    w, h = img.size
    if tight:
        x0, y0, x1, y1 = img.getchannel("A").getbbox()
        # 1 texel of slack so bilinear filtering never clips the glyph edge
        x0, y0 = max(0, x0 - 1), max(0, y0 - 1)
        x1, y1 = min(w, x1 + 1), min(h, y1 + 1)
    else:
        x0, y0, x1, y1 = 0, 0, w, h
    return dict(name=name, size_2x=[w, h],
                uv=[round(x0 / w, 6), round(y0 / h, 6), round(x1 / w, 6), round(y1 / h, 6)],
                uv_texels_2x=[x0, y0, x1, y1],
                quad_1x=[(x1 - x0) / 2, (y1 - y0) / 2])


def i4(img):
    """GX I4: 16 intensity levels. For a white mask that is 16 alpha levels."""
    a = np.asarray(img.getchannel("A")).astype("float64")
    q = (np.round(a / 255 * 15) * 17).astype("uint8")
    out = Image.new("RGBA", img.size, (255, 255, 255, 0))
    out.putalpha(Image.fromarray(q, "L"))
    return out


# ------------------------------------------------------------- preview
def _pts(verts, off=(0, 0)):
    return " ".join("%.3f,%.3f" % (x + off[0], y + off[1]) for x, y in verts)


def _matrix(q, tex_size):
    """Affine map texel(0..W,0..H) -> screen, landing the UV rect on the quad."""
    W, H = tex_size
    u0, v0, u1, v1 = q["uv"]
    (tlx, tly), (trx, try_), _br, (blx, bly) = q["verts"]
    du, dv = (u1 - u0) * W, (v1 - v0) * H
    a, b = (trx - tlx) / du, (try_ - tly) / du
    c, d = (blx - tlx) / dv, (bly - tly) / dv
    e = tlx - a * u0 * W - c * v0 * H
    f = tly - b * u0 * W - d * v0 * H
    return a, b, c, d, e, f


def svg_scene(layout, textures_b64, tex_sizes, sel_id, wire=False):
    defs, body, n = [], [], [0]

    def flat(q, colour, off=(0, 0)):
        body.append('<polygon points="%s" fill="%s"/>' % (_pts(q["verts"], off), colour))

    def textured(q, colour, off=(0, 0)):
        n[0] += 1
        a, b, c, d, e, f = _matrix(q, tex_sizes[q["texture"]])
        W, H = tex_sizes[q["texture"]]
        defs.append('<mask id="m%d" maskUnits="userSpaceOnUse" x="-50" y="-50" '
                    'width="740" height="580"><image href="data:image/png;base64,%s" '
                    'width="%d" height="%d" preserveAspectRatio="none" '
                    'transform="translate(%g %g) matrix(%g %g %g %g %g %g)"/></mask>'
                    % (n[0], textures_b64[q["texture"]], W, H,
                       off[0], off[1], a, b, c, d, e, f))
        body.append('<polygon points="%s" fill="%s" mask="url(#m%d)"/>'
                    % (_pts(q["verts"], off), colour, n[0]))

    for q in layout["quads"]:
        (textured if q["kind"] == "textured" else flat)(q, q["colour"])

    order = sorted(layout["tiles"], key=lambda t: t["id"] == sel_id)   # sel last
    for t in order:
        st = layout["states"]["sel" if t["id"] == sel_id else "ng"]
        off = st["offset"]
        for q in t["quads"]:
            role = q["role"]
            if role == "plate":
                if st["plate"]:
                    flat(q, st["plate"])
            elif role == "face":
                flat(q, st["face"], off)
            elif role == "icon":
                textured(q, st["icon"], off)
            elif role == "label":
                textured(q, st["label"], off)
        if t["id"] == sel_id:
            textured(t["desc"], t["desc"]["colour"])

    if wire:
        allq = list(layout["quads"]) + [q for t in layout["tiles"] for q in t["quads"]] \
            + [t["desc"] for t in layout["tiles"]]
        for q in allq:
            col = "#39ff88" if q["kind"] == "textured" else "#ff3fd0"
            body.append('<polygon points="%s" fill="none" stroke="%s" '
                        'stroke-width="0.75"%s/>'
                        % (_pts(q["verts"]), col,
                           ' stroke-dasharray="3 2"' if q["kind"] == "textured" else ""))
        x0, y0, x1, y1 = layout["safe_area"]
        body.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" '
                    'stroke="#ffd766" stroke-width="0.75" stroke-dasharray="6 4"/>'
                    % (x0, y0, x1 - x0, y1 - y0))

    return ('<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="960" '
            'viewBox="0 0 640 480"><defs>%s</defs>'
            '<rect x="-10" y="-10" width="660" height="500" fill="%s"/>%s</svg>'
            % ("".join(defs), layout["clear_colour"], "".join(body)))


def render_svg(page, svg):
    page.set_viewport_size({"width": 1280, "height": 960})
    page.set_content("<body style='margin:0'>%s</body>" % svg)
    png = page.locator("svg").screenshot(type="png")
    return Image.open(io.BytesIO(png)).convert("RGBA")


# -------------------------------------------------------------- checks
def check(layout, textures):
    errs = []
    sx0, sy0, sx1, sy1 = layout["safe_area"]
    sel_off = layout["states"]["sel"]["offset"]

    def every_quad():
        for q in layout["quads"]:
            yield q, (0, 0)
        for t in layout["tiles"]:
            for q in t["quads"]:
                moves = q["role"] in ("face", "icon", "label")
                yield q, (sel_off if moves else (0, 0))
            yield t["desc"], (0, 0)

    for q, off in every_quad():
        if q["kind"] == "textured":
            (a, b), (c, d), (e, f), (g, h) = q["verts"]
            if abs(a + e - c - g) > 1e-6 or abs(b + f - d - h) > 1e-6:
                errs.append("%s is not a parallelogram - texture would kink" % q["id"])
        if q["role"] == "decor":
            continue
        for dx, dy in {(0, 0), tuple(off)}:
            for x, y in q["verts"]:
                if not (sx0 <= x + dx <= sx1 and sy0 <= y + dy <= sy1):
                    errs.append("%s leaves title-safe at (%.1f,%.1f)" % (q["id"], x + dx, y + dy))
                    break

    for t in layout["tiles"]:
        lx0, ly0, lx1, ly1 = t["_label_rect"]
        ix0, iy0, ix1, iy1 = t["_icon_rect"]
        tx0, ty0, tx1, ty1 = t["rect_unsheared"]
        if lx0 < ix1 and ix0 < lx1 and ly0 < iy1 and iy0 < ly1:
            errs.append("%s: label overlaps icon" % t["id"])
        for nm, (x0, y0, x1, y1) in (("label", t["_label_rect"]), ("icon", t["_icon_rect"])):
            if x0 < tx0 or y0 < ty0 or x1 > tx1 or y1 > ty1:
                errs.append("%s: %s spills outside its tile" % (t["id"], nm))

    for name, img in textures.items():
        w, h = img.size
        if not (w & (w - 1) == 0 and h & (h - 1) == 0 and w <= 1024 and h <= 1024):
            errs.append("%s is %dx%d - not POT / over 1024" % (name, w, h))
    return errs


# ---------------------------------------------------------------- main
def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for sub in ("tex/2x", "tex/1x", "preview"):
        os.makedirs(os.path.join(OUT, sub))

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(device_scale_factor=1)

        textures, metas = {}, {}
        jobs = [("lbl_title", "MAIN MENU", "title")]
        for b in L.BUCKETS:
            jobs.append(("lbl_" + b["id"], b["label"], "hero" if b["rank"] == 0 else "tile"))
            jobs.append(("desc_" + b["id"], b["desc"], "desc"))
        for name, text, style in jobs:
            img = whiten(text_texture(page, text, style))
            textures[name], metas[name] = img, meta(name, img, tight=True)
        for b in L.BUCKETS:
            name = "ico_" + b["id"]
            img = whiten(icon_texture(page, b["id"]))
            textures[name], metas[name] = img, meta(name, img, tight=False)

        layout = L.build(metas)
        errs = check(layout, textures)

        b64, sizes = {}, {}
        for name, img in textures.items():
            save_png(img, os.path.join(OUT, "tex/2x", name + ".png"))
            save_png(downscale_half(img), os.path.join(OUT, "tex/1x", name + ".png"))
            buf = io.BytesIO()
            i4(img).save(buf, "PNG")                 # preview what I4 will look like
            b64[name] = base64.b64encode(buf.getvalue()).decode()
            sizes[name] = img.size

        frames = []
        for b in L.BUCKETS:
            shot = render_svg(page, svg_scene(layout, b64, sizes, b["id"]))
            save_png(shot, os.path.join(OUT, "preview", "hub_sel_%s_2x.png" % b["id"]))
            small = downscale_half(shot)
            save_png(small, os.path.join(OUT, "preview", "hub_sel_%s_1x.png" % b["id"]))
            frames.append(small.convert("RGB"))
        wire = render_svg(page, svg_scene(layout, b64, sizes, "versus", wire=True))
        save_png(wire, os.path.join(OUT, "preview", "hub_wireframe_2x.png"))
        frames[0].save(os.path.join(OUT, "preview", "hub_cycle_1x.gif"), save_all=True,
                       append_images=frames[1:], duration=900, loop=0)
        browser.close()

    # ---- emit layout (drop build-only keys)
    for t in layout["tiles"]:
        t.pop("_label_rect"), t.pop("_icon_rect")
    tex_rows, tex_bytes = [], 0
    for name, m in metas.items():
        w, h = m["size_2x"]
        tex_bytes += w * h // 2
        tex_rows.append(dict(
            name=name, file_2x="out_hub/tex/2x/%s.png" % name,
            file_1x="out_hub/tex/1x/%s.png" % name,
            size_2x=[w, h], size_1x=[w // 2, h // 2],
            uv=m["uv"], uv_texels_2x=m["uv_texels_2x"],
            format="I4", fallback="IA4",
            bytes_2x_I4=w * h // 2))
    layout["textures"] = tex_rows
    layout["texture_notes"] = [
        "Every texture is a white mask. Convert to I4 (4bpp): GX expands "
        "I4 to I in all four channels, so TEV must take RGB from the material "
        "colour and only ALPHA from the texture. Taking RGB from the texture "
        "as well would darken every anti-aliased edge a second time.",
        "IA4 (8bpp) is the fallback if that TEV setup is awkward: intensity "
        "fixed at 15, alpha carries coverage.",
        "UVs are normalised, so the same layout works for the 1x and 2x "
        "textures unchanged.",
    ]
    layout["provenance"] = ("Original. Layout, pictograms and text generated "
                            "from pipeline/hub_layout.py and pipeline/hub.py. "
                            "Design principles only (hierarchy, single shear "
                            "angle, flat colour); no layout or asset taken "
                            "from any shipped game.")
    with open(os.path.join(OUT, "hub_layout.json"), "w", encoding="utf-8") as fh:
        json.dump(layout, fh, indent=2)

    # ---- cost report
    n_flat = sum(1 for q in layout["quads"] if q["kind"] == "flat") + \
        sum(1 for t in layout["tiles"] for q in t["quads"] if q["kind"] == "flat")
    n_tex = sum(1 for q in layout["quads"] if q["kind"] == "textured") + \
        sum(1 for t in layout["tiles"] for q in t["quads"] if q["kind"] == "textured") + \
        len(layout["tiles"])
    baked_screens = 1280 * 960 * 2 * len(L.BUCKETS)
    baked_tiles = 0
    for t in layout["tiles"]:
        xs = [v[0] for v in t["quads"][1]["verts"]]
        ys = [v[1] for v in t["quads"][1]["verts"]]
        w, h = pot(int((max(xs) - min(xs) + 5) * 2)), pot(int((max(ys) - min(ys) + 5) * 2))
        baked_tiles += w * h * 2 * 2        # RGB5A3, ng + sel

    print("hub: %d flat quads, %d textured quads, %d textures"
          % (n_flat, n_tex, len(textures)))
    print("  texture memory @2x, I4 ............ %7.1f KB" % (tex_bytes / 1024))
    print("  baked alternative: 4 full screens . %7.1f KB (RGB5A3, and over the 1024 limit)"
          % (baked_screens / 1024))
    print("  baked alternative: per-tile ng+sel  %7.1f KB (RGB5A3, excl. header/footer)"
          % (baked_tiles / 1024))
    for name in sorted(metas):
        m = metas[name]
        print("   %-17s %4dx%-4d I4 %6.1f KB   quad %6.1f x %5.1f @1x"
              % (name, m["size_2x"][0], m["size_2x"][1],
                 m["size_2x"][0] * m["size_2x"][1] / 2048, *m["quad_1x"]))
    if errs:
        print("\nCHECKS FAILED:")
        for e in errs:
            print("  - " + e)
        return 1
    print("\nchecks ok: textured quads are parallelograms, everything but decor "
          "stays title-safe (incl. sel offset), no label/icon overlap, all textures POT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
