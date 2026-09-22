"""Icon masks for the online screen (out_online/) and section 2 (out_nav/).

    python pipeline/icons.py      -> out_online/{2x,1x}/ico_*.png, sig_bar_*.png
                                     out_nav/{2x,1x}/ico_*.png, mark_*.png
                                     out_online/icons_manifest.json, out_nav/icons_manifest.json
                                     out_nav/preview/icons_sheet_2x.png (+ out_online's)

Every icon is an original pictogram on a 64-unit grid, drawn here as SVG and
rendered by headless Chromium to a white-on-alpha mask; colour comes from the
material. Nothing is traced, referenced or sampled from Melee or any other
game. Where a subject has an obvious real-world object (a camera, an
envelope, a trophy cup), the drawing is of the object, not of any game's
drawing of it.

Rules the drawings keep, so they survive I4 and small draws:
  * strokes and gaps at least 5 grid units (at a 16 px draw that is 1.25 px);
  * no symbol depends on a detail below that: every hole is at least 6 units;
  * letters appear only where the letter IS the symbol (none so far) - words
    always come from strings (the "new" badge is a burst; NEW is set on it).

Checks: POT and <= 1024, not empty, and legibility - the number of separate
shapes and enclosed holes at full resolution must survive a downscale to
twice the icon's smallest draw size (what an HD window shows). The 1x count
is reported alongside.
"""
import base64
import io
import json
import math
import os
import sys

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hub as H                                          # noqa: E402
from build import downscale_half, save_png              # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = {"online": os.path.join(ROOT, "out_online"), "nav": os.path.join(ROOT, "out_nav")}


# ------------------------------------------------------------ helpers
def circle(cx, cy, r):
    return H._circle(cx, cy, r)


def ring(cx, cy, r_out, r_in):
    """Even-odd ring as one path (both circles, fill-rule evenodd)."""
    return circle(cx, cy, r_out) + " " + circle(cx, cy, r_in)


def rect(x, y, w, h):
    return "M%g %g h%g v%g h%g Z" % (x, y, w, h, -w)


def rrect(x, y, w, h, r):
    return ("M%g %g h%g a%g %g 0 0 1 %g %g v%g a%g %g 0 0 1 %g %g h%g a%g %g 0 0 1 %g %g "
            "v%g a%g %g 0 0 1 %g %g Z"
            % (x + r, y, w - 2 * r, r, r, r, r, h - 2 * r, r, r, -r, r, -(w - 2 * r),
               r, r, -r, -r, -(h - 2 * r), r, r, r, -r))


def star(cx, cy, R, r, n=5, rot=-90):
    pts = []
    for i in range(2 * n):
        a = math.radians(rot + i * 180 / n)
        rad = R if i % 2 == 0 else r
        pts.append("%.2f %.2f" % (cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return "M" + " L".join(pts) + " Z"


def P(d, rule="nonzero"):
    return '<path d="%s" fill-rule="%s"/>' % (d, rule)


def S(d, w=5, cap="butt", join="miter"):
    """Stroked path (stroke is white; fill none)."""
    return ('<path d="%s" fill="none" stroke="#fff" stroke-width="%g" stroke-linecap="%s" '
            'stroke-linejoin="%s"/>' % (d, w, cap, join))


def KO(shape, knock):
    """shape (white) with knock (drawn black) cut out of it."""
    return dict(shape=shape, knock=knock)


# ------------------------------------------------------------ the drawings
# name -> dict(set, size_2x, min_draw_1x, body | shape+knock, use)
ICONS = {}


def icon(name, set_, size, min_draw, use, body=None, shape=None, knock=None):
    ICONS[name] = dict(set=set_, size_2x=size, min_draw_1x=min_draw, use=use,
                       body=body, shape=shape, knock=knock)


# ---- online (row, status strip and dialog sizes: 16-32 px at 1x)
icon("ico_online", "nav", 256, 16,
     "Versus hub tile 'Online'; online screen breadcrumb root; status strip idle",
     body=(P(ring(32, 32, 29, 23.5), "evenodd") +
           S("M32 5 C 14 16, 14 48, 32 59 C 50 48, 50 16, 32 5 Z", 5.5) +
           S("M5 32 H59", 5.5)))
icon("ico_host", "online", 64, 16, "'Host Match' row; Play As = Host",
     body=(P(circle(32, 26, 7)) +
           S("M21 37 A 15.5 15.5 0 0 1 21 15", 5.5, "round") +
           S("M43 15 A 15.5 15.5 0 0 1 43 37", 5.5, "round") +
           S("M12.5 45.5 A 27 27 0 0 1 12.5 6.5", 5.5, "round") +
           S("M51.5 6.5 A 27 27 0 0 1 51.5 45.5", 5.5, "round") +
           P("M28 31 L36 31 L42 61 L22 61 Z")))
icon("ico_join", "online", 64, 16, "'Connect' row; Play As = Join",
     body=(S("M34 6 H56 V58 H34", 6, join="miter") +
           P("M4 27 H24 V15 L43 32 L24 49 V37 H4 Z")))
icon("ico_paste", "online", 64, 16, "'Paste Host Code', 'Paste Friend's Code' rows",
     shape=P(rrect(9, 8, 46, 54, 5)) + P(rrect(20, 2, 24, 13, 4)),
     knock=P(rect(15, 19, 34, 37)) + '<path d="M28 24 h8 v12 h8 L32 50 L20 36 h8 Z" fill="#fff"/>')
icon("ico_copy", "online", 64, 16, "code plate copy affordance; 'Your Code' row",
     shape=S(rrect(6, 6, 34, 40, 4), 5.5) + P(rrect(22, 20, 36, 42, 4)),
     knock=P(rrect(28, 26, 24, 30, 1)))
icon("ico_link", "online", 64, 16, "status strip connected; dialog when connected",
     body=(S(rrect(3, 20, 34, 24, 12), 6) + S(rrect(27, 20, 34, 24, 12), 6)))
icon("ico_unlink", "online", 64, 16, "status strip disconnected (peer lost)",
     body=(S("M24 20 H15 A12 12 0 0 0 15 44 H24", 6) +
           S("M40 20 H49 A12 12 0 0 1 49 44 H40", 6) +
           S("M32 3 V12 M32 52 V61", 5.5, "round")))
icon("ico_warning", "online", 64, 16, "status strip failed; failed dialog title",
     shape=P("M32 3 L62 58 H2 Z"),
     knock=P("M28.5 20 H35.5 L34.5 41 H29.5 Z") + P(circle(32, 49.5, 4)))
for i in range(4):
    h = 14 + i * 14
    icon("sig_bar_%d" % (i + 1), "online", 64, 16,
         "ping bar %d of 4; draw all four at one rect, lit ones in the quality colour" % (i + 1),
         body=P(rect(3 + i * 15.5, 60 - h, 11, h)))


# ---- section 2 hub icons (hero-capable: 256 texels = 128 px at 1x)
def hub(name, use, body=None, shape=None, knock=None):
    icon(name, "nav", 256, 16, use, body=body, shape=shape, knock=knock)


# the four prototype icons stay as drawn in hub.py (same paths), now 256 each
for n in ("versus", "solo", "collection", "options"):
    hub("ico_" + n, "main menu tile, %s breadcrumb root" % n,
        body=P(H.ICONS[n], H.FILL_RULE[n]))
hub("ico_data", "main menu tile 'Data', Data breadcrumb root",
    body=(P("M6 14 C6 3, 58 3, 58 14 V22 C58 33, 6 33, 6 22 Z") +
          P("M6 30 C12 39, 52 39, 58 30 V38 C58 49, 6 49, 6 38 Z") +
          P("M6 46 C12 55, 52 55, 58 46 V51 C58 62, 6 62, 6 51 Z")))
hub("ico_regular", "Solo > Regular Match: a climb of stages to a flag",
    body=(P("M2 62 V48 H18 V36 H34 V24 H50 V62 Z") +
          P("M50 24 V2 H55 V24 Z") + P("M55 3 L63 8 L55 13 Z")))
hub("ico_event", "Solo > Event Match: a date page with a star",
    shape=P(rrect(4, 8, 56, 52, 5)) + P(rect(14, 1, 7, 14)) + P(rect(43, 1, 7, 14)),
    knock=P(rect(10, 22, 44, 32)) + '<g fill="#fff">%s</g>' % P(star(32, 38.5, 13, 5.5)))
hub("ico_stadium", "Solo > Stadium: an arena on columns",
    body=(P("M2 22 L32 2 L62 22 Z") + P(rect(2, 27, 60, 6)) +
          P(rect(6, 38, 8, 14)) + P(rect(20, 38, 8, 14)) + P(rect(36, 38, 8, 14)) +
          P(rect(50, 38, 8, 14)) + P(rect(2, 57, 60, 6))))
hub("ico_training", "Solo > Training: a dumbbell",
    body=(P(rect(16, 29, 32, 6)) + P(rrect(8, 14, 10, 36, 2)) + P(rrect(46, 14, 10, 36, 2)) +
          P(rrect(1, 21, 8, 22, 2)) + P(rrect(55, 21, 8, 22, 2))))
hub("ico_classic", "Regular Match > Classic: a crown over a run of steps",
    body=(P("M6 34 L8 10 L20 22 L32 6 L44 22 L56 10 L58 34 Z") +
          P(rect(6, 38, 52, 7)) + P(rect(6, 50, 12, 12)) + P(rect(26, 50, 12, 12)) +
          P(rect(46, 50, 12, 12))))
hub("ico_adventure", "Regular Match > Adventure: mountains and a trail flag",
    body=(P("M1 58 L22 20 L32 36 L42 26 L63 58 Z") +
          P(rect(20, 2, 4, 20)) + P("M24 3 L36 8 L24 13 Z")))
hub("ico_allstar", "Regular Match > All-Star: a constellation of stars",
    body=(P(star(28, 36, 26, 11)) + P(star(52, 12, 10, 4.5)) + P(star(55, 44, 7, 3.2))))
hub("ico_target", "Stadium > Target Test: a reticle",
    body=(P(ring(32, 32, 24, 18.5), "evenodd") + P(circle(32, 32, 6)) +
          P(rect(29, 1, 6, 16)) + P(rect(29, 47, 6, 16)) + P(rect(1, 29, 16, 6)) +
          P(rect(47, 29, 16, 6))))
hub("ico_homerun", "Stadium > Home-Run Contest: a ball on a long arc",
    body=(P(circle(48, 18, 12)) +
          S("M3 60 Q 16 18, 34 20", 5, "round") +
          S("M10 60 Q 22 32, 34 30", 5, "round")))
hub("ico_multiman", "Stadium > Multi-Man Melee: a crowd of three",
    body=(P(circle(32, 16, 10)) + P("M16 60 C16 36, 48 36, 48 60 Z") +
          P(circle(11, 25, 7)) + P("M0 60 C0 42, 14 38, 16 44 C13 50, 13 56, 13 60 Z") +
          P(circle(53, 25, 7)) + P("M64 60 C64 42, 50 38, 48 44 C51 50, 51 56, 51 60 Z")))
hub("ico_melee", "Versus > Melee: four players round a spark",
    body=(P(circle(32, 8, 7)) + P(circle(32, 56, 7)) + P(circle(8, 32, 7)) +
          P(circle(56, 32, 7)) + P(star(32, 32, 14, 5.5, 4, -90))))
hub("ico_tournament", "Versus > Tournament: a bracket",
    body=S("M2 8 H18 V24 H2 M18 16 H32 V40 H48 M2 32 H18 V48 H2 M18 40 H32 "
           "M48 40 H62", 5.5) + P(circle(56, 40, 7)))
hub("ico_special", "Versus > Special Melee: a twist of sparkles",
    body=(P(star(26, 36, 24, 7, 4)) + P(star(50, 12, 11, 3.5, 4)) + P(star(52, 50, 8, 2.8, 4))))
hub("ico_rules", "Versus > Rules: ticked setting lines",
    body=(P(rect(4, 6, 12, 12)) + P(rect(22, 9, 38, 6)) +
          P(rect(4, 26, 12, 12)) + P(rect(22, 29, 38, 6)) +
          P(rect(4, 46, 12, 12)) + P(rect(22, 49, 38, 6))))
hub("ico_names", "Versus > Name Entry: a luggage tag",
    shape=P("M18 8 H58 V56 H18 L4 32 Z"),
    knock=P(circle(17, 32, 5)) + P(rect(28, 22, 22, 6)) + P(rect(28, 36, 16, 6)))
hub("ico_gallery", "Collection > Gallery: a framed picture",
    shape=P(rect(3, 7, 58, 50)),
    knock=P(rect(10, 14, 44, 36)) +
    '<g fill="#fff">%s%s</g>' % (P("M10 50 L25 30 L34 40 L41 33 L54 50 Z"),
                                 P(circle(44, 23, 5))))
hub("ico_lottery", "Collection > Lottery: a prize ticket",
    shape=P("M2 14 H62 V26 A6 6 0 0 0 62 38 V50 H2 V38 A6 6 0 0 0 2 26 Z"),
    knock="".join(P(rect(42, y, 5, 5)) for y in (17, 26, 35, 44)) +
    '<g fill="#fff"></g>' + P(star(22, 32, 12, 5)))
hub("ico_trophies", "Collection > Collection: a trophy cup on a base",
    body=(P("M16 4 H48 V18 C48 32, 40 38, 32 38 C24 38, 16 32, 16 18 Z") +
          S("M16 10 H8 V16 C8 24, 13 28, 18 28", 5) + S("M48 10 H56 V16 C56 24, 51 28, 46 28", 5) +
          P(rect(28, 38, 8, 10)) + P(rect(18, 48, 28, 6)) + P(rect(12, 56, 40, 7))))
hub("ico_snapshots", "Data > Snapshots: a camera",
    shape=P(rrect(2, 16, 60, 42, 5)) + P("M20 16 L25 6 H39 L44 16 Z"),
    knock=P(circle(32, 37, 14)) + '<g fill="#fff">%s</g>' % P(circle(32, 37, 8)) +
    P(rect(48, 22, 8, 5)))
hub("ico_movies", "Data > Movies: a film strip",
    shape=P(rect(8, 2, 48, 60)),
    knock=(P(rect(20, 8, 24, 20)) + P(rect(20, 36, 24, 20)) +
           "".join(P(rect(11, y, 5, 6)) + P(rect(48, y, 5, 6)) for y in (6, 18, 30, 42, 54))))
hub("ico_soundtest", "Data > Sound Test: a pair of notes",
    body=(P("M18 12 L56 4 V14 L24 21 V50 A9 7 0 1 1 18 44 Z") +
          P("M50 8 H56 V44 A9 7 0 1 1 50 38 Z")))
hub("ico_records", "Data > Records: a podium",
    body=(P(rect(22, 16, 20, 46)) + P(rect(2, 32, 18, 30)) + P(rect(44, 40, 18, 22)) +
          P(star(32, 6, 6, 2.6))))
hub("ico_messages", "Data > Special Messages: a sealed envelope",
    shape=P(rect(3, 12, 58, 40)),
    knock='<path d="M3 12 L32 36 L61 12" fill="none" stroke="#000" stroke-width="5" '
          'stroke-linejoin="miter"/>' + P(circle(32, 38, 5)))


# ---- marks (small: next to a row or at a tile corner, 12-16 px at 1x)
icon("mark_completed", "nav", 32, 12, "completed mark: event rows, cleared modes",
     shape=P(circle(32, 32, 30)), knock=P("M14 33 L23 24 L28 29 L43 14 L51 22 L28 45 Z"))
icon("mark_locked", "nav", 32, 12, "locked mark: items not yet unlocked (if ever shown)",
     shape=P(rrect(8, 28, 48, 34, 4)) + S("M18 30 V20 A14 14 0 0 1 46 20 V30", 7),
     knock=P(circle(32, 42, 5)) + P(rect(29.5, 42, 5, 11)))
icon("mark_new", "nav", 64, 16, "'new' badge: a burst; the word comes from strings, "
     "set on it in ink at caption size",
     body=P(star(32, 32, 31, 25, 14, -90)))


# ------------------------------------------------------------ rendering
def svg_body(ic):
    if ic["body"] is not None:
        return '<g fill="#fff">%s</g>' % ic["body"]
    # knock paths inherit black (cut); a path with an explicit #fff re-adds inside the cut
    knock = ic["knock"]
    return ('<defs><mask id="k" maskUnits="userSpaceOnUse" x="-2" y="-2" width="68" height="68">'
            '<rect x="-2" y="-2" width="68" height="68" fill="#fff"/><g fill="#000">%s</g>'
            '</mask></defs><g fill="#fff" stroke-width="0" mask="url(#k)">%s</g>'
            % (knock, ic["shape"]))


def render(page, ic):
    n = ic["size_2x"]
    html = ('<!doctype html><html><head><style>html,body{margin:0;background:transparent}'
            '</style></head><body><svg id="s" width="%d" height="%d" viewBox="0 0 64 64">%s'
            '</svg></body></html>' % (n, n, svg_body(ic)))
    page.set_viewport_size({"width": max(n, 64), "height": max(n, 64)})
    page.set_content(html)
    png = page.locator("#s").screenshot(omit_background=True, type="png")
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    out = Image.new("RGBA", img.size, (255, 255, 255, 0))
    out.putalpha(img.getchannel("A"))
    return out


def topology(alpha, thr=128):
    """(solid parts, enclosed holes) of a mask thresholded at 50%. Specks under two
    square grid units (rasteriser dust at a cusp) are not features and do not count."""
    a = np.asarray(alpha) >= thr
    min_area = 2 * (a.shape[0] / 64) ** 2
    lab, n = ndimage.label(a)
    solids = sum(1 for s in ndimage.sum(a, lab, range(1, n + 1)) if s >= min_area)
    lab, n = ndimage.label(~a)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    sizes = ndimage.sum(~a, lab, range(1, n + 1))
    holes = sum(1 for i, s in enumerate(sizes, 1) if i not in edge and s >= min_area)
    return solids, holes


def shrink(img, px):
    """Premultiplied area downscale to px x px (what a draw at that size samples)."""
    a = img.getchannel("A")
    return a.resize((px, px), Image.BOX)


def i4_alpha(img):
    a = np.asarray(img.getchannel("A")).astype("float64")
    return Image.fromarray((np.round(a / 255 * 15) * 17).astype("uint8"), "L")


def main():
    for d in OUT.values():
        for sub in ("2x", "1x", "preview"):
            os.makedirs(os.path.join(d, sub), exist_ok=True)
        for sub in ("2x", "1x"):
            for f in os.listdir(os.path.join(d, sub)):
                if f.startswith(("ico_", "sig_bar_", "mark_")):
                    os.remove(os.path.join(d, sub, f))
    errs, rows, imgs = [], {k: [] for k in OUT}, {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(device_scale_factor=1)
        for name, ic in ICONS.items():
            img = render(page, ic)
            imgs[name] = img
            d = OUT[ic["set"]]
            sub = os.path.basename(d)
            save_png(img, os.path.join(d, "2x", name + ".png"))
            save_png(downscale_half(img), os.path.join(d, "1x", name + ".png"))
            n = ic["size_2x"]
            if n & (n - 1) or n > 1024:
                errs.append("%s: %d not POT / over 1024" % (name, n))
            if img.getchannel("A").getbbox() is None:
                errs.append("%s is empty" % name)
            full = topology(img.getchannel("A"))
            hd = topology(shrink(img, 2 * ic["min_draw_1x"]))
            sd = topology(shrink(img, ic["min_draw_1x"]))
            if hd != full:
                errs.append("%s: at %d px (2x of its %d px draw) shapes/holes %s, full res %s"
                            % (name, 2 * ic["min_draw_1x"], ic["min_draw_1x"], hd, full))
            rows[ic["set"]].append(dict(
                name=name, file_2x="%s/2x/%s.png" % (sub, name),
                file_1x="%s/1x/%s.png" % (sub, name), size_2x=[n, n], size_1x=[n // 2, n // 2],
                format="I4", fallback="IA4", bytes_2x=n * n // 2,
                why="white mask tinted by material colour; 16 edge levels are plenty",
                use=ic["use"], min_draw_1x=ic["min_draw_1x"],
                legibility=dict(full=list(full), at_2x_draw=list(hd), at_1x_draw=list(sd))))
        browser.close()

    for key, d in OUT.items():
        with open(os.path.join(d, "icons_manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(provenance="Original pictograms drawn in pipeline/icons.py "
                                      "(SVG on a 64 grid); nothing traced, sampled or "
                                      "recoloured from Melee or any other game.",
                           textures=rows[key]), fh, indent=1)

    # contact sheets: each icon at 2x on a Versus face, then at its smallest draw (2x and 1x)
    for key, d in OUT.items():
        names = [r["name"] for r in rows[key]]
        cols = 8
        cw, chh = 150, 170
        sheet = Image.new("RGB", (cols * cw, ((len(names) + cols - 1) // cols) * chh),
                          (3, 37, 104))
        from PIL import ImageDraw
        dr = ImageDraw.Draw(sheet)
        for i, n in enumerate(names):
            x, y = (i % cols) * cw, (i // cols) * chh
            img = imgs[n]
            big = img.resize((96, 96), Image.LANCZOS) if img.width != 96 else img
            q = Image.new("RGBA", big.size, (255, 255, 255, 0))
            q.putalpha(i4_alpha(big))
            sheet.paste(Image.new("RGB", big.size, (157, 162, 248)), (x + 8, y + 8), q.getchannel("A"))
            m = ICONS[n]["min_draw_1x"]
            for k, px in enumerate((2 * m, m)):
                a = shrink(img, px)
                sheet.paste(Image.new("RGB", (px, px), (242, 239, 228)),
                            (x + 112, y + 8 + k * 40), a)
            dr.text((x + 8, y + 112), n, fill=(242, 239, 228))
            dr.text((x + 8, y + 128), "%d px min" % m, fill=(184, 194, 220))
        sheet.save(os.path.join(d, "preview", "icons_sheet_2x.png"))

    for key in OUT:
        kb = sum(r["bytes_2x"] for r in rows[key]) / 1024
        print("%-7s %2d masks, %.1f KB @2x I4" % (key, len(rows[key]), kb))
    if errs:
        print("\nCHECKS FAILED (%d):" % len(errs))
        for e in errs:
            print("  - " + e)
        return 1
    print("\nicon checks ok: POT <= 1024, non-empty, shapes and holes survive at 2x of "
          "every icon's smallest draw")
    return 0


if __name__ == "__main__":
    sys.exit(main())
