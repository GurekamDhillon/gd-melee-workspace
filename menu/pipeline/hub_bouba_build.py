"""Build the bouba hub prototype.

    python pipeline/hub_bouba_build.py

Renders pipeline/hub_bouba.py into out_hub_bouba/ - never touches out_hub/.
Previews are drawn from the emitted fans and quads with textures
pre-quantised to I4, i.e. what the engine will draw.
"""
import base64
import io
import itertools
import json
import os
import shutil
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hub as H                                           # noqa: E402
import hub_bouba as L                                     # noqa: E402
from build import downscale_half, save_png               # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_hub_bouba")

# A round-join stroke softens the pictograms' corners. Solo is already round
# and its ring gaps would close up under a stroke.
STROKE = {"versus": 4, "solo": 0, "collection": 4, "options": 3}


def icon_texture(page, name):
    n = H.ICON_SIZE[name]
    sw = STROKE[name]
    stroke = (' stroke="#fff" stroke-width="%g" stroke-linejoin="round"' % sw) if sw else ""
    svg = ('<svg width="%d" height="%d" viewBox="-3 -3 70 70">'
           '<path d="%s" fill="#fff" fill-rule="%s"%s/></svg>'
           % (n, n, H.ICONS[name], H.FILL_RULE[name], stroke))
    return H._shot(page, svg, n, n)


# ------------------------------------------------------------- preview
def svg_scene(layout, b64, sizes, sel_id, wire=False):
    defs, body, n = [], [], [0]

    def poly(q, colour, off=(0, 0)):
        body.append('<polygon points="%s" fill="%s"/>' % (H._pts(q["verts"], off), colour))

    def textured(q, colour, off=(0, 0)):
        n[0] += 1
        a, b, c, d, e, f = H._matrix(q, sizes[q["texture"]])
        W, Ht = sizes[q["texture"]]
        defs.append('<mask id="m%d" maskUnits="userSpaceOnUse" x="-50" y="-50" '
                    'width="740" height="580"><image href="data:image/png;base64,%s" '
                    'width="%d" height="%d" preserveAspectRatio="none" '
                    'transform="translate(%g %g) matrix(%g %g %g %g %g %g)"/></mask>'
                    % (n[0], b64[q["texture"]], W, Ht, off[0], off[1], a, b, c, d, e, f))
        body.append('<polygon points="%s" fill="%s" mask="url(#m%d)"/>'
                    % (H._pts(q["verts"], off), colour, n[0]))

    for q in layout["quads"]:
        (textured if q["kind"] == "textured" else poly)(q, q["colour"])

    # outlines first, all of them: a lifted face may cross a neighbour's gap
    for t in layout["tiles"]:
        poly(t["quads"][0], t["quads"][0]["colour"])
    for t in sorted(layout["tiles"], key=lambda t: t["id"] == sel_id):
        st = layout["states"]["sel" if t["id"] == sel_id else "ng"]
        off = st["offset"]
        for q in t["quads"][1:]:
            role = q["role"]
            if role == "plate":
                if st["plate"]:
                    poly(q, st["plate"])
            elif role == "face":
                poly(q, st["face"], off)
            else:
                textured(q, st[role], off)
        if t["id"] == sel_id:
            textured(t["desc"], t["desc"]["colour"])

    if wire:
        allq = list(layout["quads"]) + [q for t in layout["tiles"] for q in t["quads"]] \
            + [t["desc"] for t in layout["tiles"]]
        for q in allq:
            if q["kind"] == "fan":
                cx, cy = q["centre"]
                spokes = "".join("M%.2f %.2fL%.2f %.2f" % (cx, cy, x, y) for x, y in q["verts"])
                body.append('<path d="%s" stroke="#ff3fd0" stroke-width="0.25" '
                            'opacity="0.5"/>' % spokes)
                body.append('<polygon points="%s" fill="none" stroke="#ff3fd0" '
                            'stroke-width="0.5"/>' % H._pts(q["verts"]))
            else:
                body.append('<polygon points="%s" fill="none" stroke="#39ff88" '
                            'stroke-width="0.75" stroke-dasharray="3 2"/>' % H._pts(q["verts"]))
        x0, y0, x1, y1 = layout["safe_area"]
        body.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" '
                    'stroke="#ffd766" stroke-width="0.75" stroke-dasharray="6 4"/>'
                    % (x0, y0, x1 - x0, y1 - y0))

    return ('<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="960" '
            'viewBox="0 0 640 480"><defs>%s</defs>'
            '<rect x="-10" y="-10" width="660" height="500" fill="%s"/>%s</svg>'
            % ("".join(defs), layout["clear_colour"], "".join(body)))


# -------------------------------------------------------------- checks
def corners(r):
    x0, y0, x1, y1 = r
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def check(layout, textures):
    errs = []
    sx0, sy0, sx1, sy1 = layout["safe_area"]
    off = layout["states"]["sel"]["offset"]
    tiles = layout["tiles"]

    # title-safe, including the selected lift
    def every():
        for q in layout["quads"]:
            yield q, [(0, 0)]
        for t in tiles:
            for q in t["quads"]:
                yield q, [(0, 0), off] if q["role"] in ("face", "icon", "label") else [(0, 0)]
            yield t["desc"], [(0, 0)]

    for q, offs in every():
        if q["kind"] == "textured":
            (a, b), (c, d), (e, f), (g, h) = q["verts"]
            if abs(a + e - c - g) > 1e-6 or abs(b + f - d - h) > 1e-6:
                errs.append("%s is not a parallelogram - texture would kink" % q["id"])
        if q["role"] == "decor":
            continue
        bad = [(x + dx, y + dy) for dx, dy in offs for x, y in q["verts"]
               if not (sx0 <= x + dx <= sx1 and sy0 <= y + dy <= sy1)]
        if bad:
            errs.append("%s leaves title-safe at (%.1f,%.1f)" % (q["id"], *bad[0]))

    # label and icon: inside their shape with INSET to spare, and apart
    for t in tiles:
        s = t["shape"]
        for nm in ("_label_rect", "_icon_rect"):
            worst = max(L.sdf(s, x, y) for x, y in corners(t[nm]))
            if worst > -L.INSET:
                errs.append("%s: %s only %.1f px inside its shape (need %d)"
                            % (t["id"], nm[1:-5], -worst, L.INSET))
        lx0, ly0, lx1, ly1 = t["_label_rect"]
        ix0, iy0, ix1, iy1 = t["_icon_rect"]
        if lx0 < ix1 and ix0 < lx1 and ly0 < iy1 and iy0 < ly1:
            errs.append("%s: label overlaps icon" % t["id"])

    # tiles: outlines keep a visible gap, lifted faces don't cross a neighbour
    GAP = 4
    for a, b in itertools.permutations(tiles, 2):
        ring_a = L.ring(a["shape"], L.OUTLINE)
        near = min(L.sdf(b["shape"], x, y) for x, y in ring_a) - L.OUTLINE
        if near < GAP:
            errs.append("%s/%s outlines only %.1f px apart (need %d)"
                        % (a["id"], b["id"], near, GAP))
        lifted = [(x + off[0], y + off[1]) for x, y in L.ring(a["shape"])]
        if min(L.sdf(b["shape"], x, y) for x, y in lifted) < L.OUTLINE:
            errs.append("%s lifted face crosses %s's outline" % (a["id"], b["id"]))

    # hierarchy: hero at least twice the biggest secondary
    hero = next(t for t in tiles if t["hero"])
    big = max(L.area(t["shape"]) for t in tiles if not t["hero"])
    if L.area(hero["shape"]) < 2 * big:
        errs.append("hero is only %.2fx the largest secondary" % (L.area(hero["shape"]) / big))

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
            img = H.whiten(H.text_texture(page, text, style))
            textures[name], metas[name] = img, H.meta(name, img, tight=True)
        for b in L.BUCKETS:
            name = "ico_" + b["id"]
            img = H.whiten(icon_texture(page, b["id"]))
            textures[name], metas[name] = img, H.meta(name, img, tight=False)

        layout = L.build(metas)
        errs = check(layout, textures)

        b64, sizes = {}, {}
        for name, img in textures.items():
            save_png(img, os.path.join(OUT, "tex/2x", name + ".png"))
            save_png(downscale_half(img), os.path.join(OUT, "tex/1x", name + ".png"))
            buf = io.BytesIO()
            H.i4(img).save(buf, "PNG")
            b64[name] = base64.b64encode(buf.getvalue()).decode()
            sizes[name] = img.size

        frames = []
        for b in L.BUCKETS:
            shot = H.render_svg(page, svg_scene(layout, b64, sizes, b["id"]))
            save_png(shot, os.path.join(OUT, "preview", "hub_sel_%s_2x.png" % b["id"]))
            small = downscale_half(shot)
            save_png(small, os.path.join(OUT, "preview", "hub_sel_%s_1x.png" % b["id"]))
            frames.append(small.convert("RGB"))
        wire = H.render_svg(page, svg_scene(layout, b64, sizes, "versus", wire=True))
        save_png(wire, os.path.join(OUT, "preview", "hub_wireframe_2x.png"))
        frames[0].save(os.path.join(OUT, "preview", "hub_cycle_1x.gif"), save_all=True,
                       append_images=frames[1:], duration=900, loop=0)
        browser.close()

    for t in layout["tiles"]:
        t.pop("_label_rect"), t.pop("_icon_rect")
    tex_rows, tex_bytes = [], 0
    for name, m in metas.items():
        w, h = m["size_2x"]
        tex_bytes += w * h // 2
        tex_rows.append(dict(
            name=name, file_2x="out_hub_bouba/tex/2x/%s.png" % name,
            file_1x="out_hub_bouba/tex/1x/%s.png" % name,
            size_2x=[w, h], size_1x=[w // 2, h // 2],
            uv=m["uv"], uv_texels_2x=m["uv_texels_2x"],
            format="I4", fallback="IA4", bytes_2x_I4=w * h // 2))
    layout["textures"] = tex_rows
    layout["provenance"] = ("Original. Generated from pipeline/hub_bouba.py and "
                            "pipeline/hub_bouba_build.py; no layout or asset taken "
                            "from any shipped game.")
    with open(os.path.join(OUT, "hub_layout.json"), "w", encoding="utf-8") as fh:
        json.dump(layout, fh, indent=2)

    allq = list(layout["quads"]) + [q for t in layout["tiles"] for q in t["quads"]] \
        + [t["desc"] for t in layout["tiles"]]
    fans = [q for q in allq if q["kind"] == "fan"]
    n_tex = sum(1 for q in allq if q["kind"] == "textured")
    print("bouba: %d fans (%d triangles), %d textured quads, %d textures"
          % (len(fans), sum(len(q["verts"]) for q in fans), n_tex, len(textures)))
    print("  texture memory @2x, I4 ... %6.1f KB" % (tex_bytes / 1024))
    for t in layout["tiles"]:
        print("   %-11s %-8s %3d ring verts  area %6.0f px2"
              % (t["id"], t["shape"]["type"], len(L.ring(t["shape"])), L.area(t["shape"])))
    if errs:
        print("\nCHECKS FAILED:")
        for e in errs:
            print("  - " + e)
        return 1
    print("\nchecks ok: title-safe incl. lift, labels/icons inside their shapes, "
          "no label/icon overlap, tile gaps held, hero dominates, textures POT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
