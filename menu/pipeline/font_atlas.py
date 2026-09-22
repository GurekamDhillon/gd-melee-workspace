"""Font atlas for the kit's type scale.

    python pipeline/font_atlas.py

One atlas per type-scale role (kit.TYPE_SCALE), rendered at 2x from the
role's face (Source Sans 3, or Hasklug for the fixed-width 'tag' role; both
SIL OFL), white on alpha, quantised to I4. Glyphs are upright: italics are
drawn by shearing the glyph quads (kit.SHEAR), so one atlas serves both.

Every glyph carries the metrics the engine needs to set text from strings:
pen-relative offset, size and advance, all in 1x px, plus the font's GPOS
kerning pairs within the charset. Advances and kerning come from the font
tables, not the rasteriser. The build checks digits are tabular in every
role and that the 'tag' role is truly monospaced.

Atlases are paged by script. English fills the 'latin' pages; a second
script adds its own pages to the same role without moving any latin glyph.

Writes out_kit/font/{2x,1x}/font_<role>_<script>_<page>.png and
out_kit/font/font_manifest.json, plus a specimen set from the manifest.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit                                                 # noqa: E402
from build import downscale_half, save_png               # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_kit", "font")
PAD = 2          # 2x texels of empty border around every glyph (1 texel at 1x)
MAX_PAGE = 1024
STAR = "★"  # in neither font: drawn here as an original five-point star


def pot(n):
    p = 8
    while p < n:
        p *= 2
    return p


def even(n):
    return n + (n & 1)


def star_glyph(em, cap_em, mono):
    """Five-point star centred on the cap height. In the monospaced face it
    keeps the 0.6 em cell; in the proportional face it gets its own width."""
    ss = 4
    adv = (0.6 if mono else 0.76) * em
    cap = cap_em * em
    R = (0.28 if mono else 0.34) * em
    r = R * 0.42
    cx, cy = adv / 2, -cap / 2                        # baseline-relative
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rad = R if i % 2 == 0 else r
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    x0 = math.floor(min(p[0] for p in pts)) - 1
    y0 = math.floor(min(p[1] for p in pts)) - 1
    x1 = math.ceil(max(p[0] for p in pts)) + 1
    y1 = math.ceil(max(p[1] for p in pts)) + 1
    big = Image.new("L", ((x1 - x0) * ss, (y1 - y0) * ss), 0)
    ImageDraw.Draw(big).polygon([((x - x0) * ss, (y - y0) * ss) for x, y in pts], fill=255)
    a = big.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    return a, (x0, y0), adv


def font_tables(path, chars):
    """Advances, cap/x height and kerning, in em, from the font tables. PIL's
    getlength rounds to whole pixels, which drifts a 20-character name by
    ~4px at 1x, and PIL's per-glyph rendering applies no kerning at all."""
    from fontTools.ttLib import TTFont
    f = TTFont(path)
    upm, cmap, hmtx = f["head"].unitsPerEm, f.getBestCmap(), f["hmtx"]
    adv = {chr(cp): hmtx[g][0] / upm for cp, g in cmap.items()}
    os2 = f["OS/2"]
    g2c = {}
    for ch in chars:
        if ord(ch) in cmap:
            g2c.setdefault(cmap[ord(ch)], []).append(ch)

    kern = {}
    if "GPOS" in f:
        gpos = f["GPOS"].table
        idx = []
        for fr in gpos.FeatureList.FeatureRecord:
            if fr.FeatureTag == "kern":
                idx += [i for i in fr.Feature.LookupListIndex if i not in idx]
        for li in sorted(idx):
            # within a lookup the first subtable that applies wins; separate
            # lookups add up
            done = set()
            lk = gpos.LookupList.Lookup[li]
            for st in lk.SubTable:
                if lk.LookupType == 9:
                    st = st.ExtSubTable
                if getattr(st, "LookupType", 2) != 2:
                    continue
                cov = st.Coverage.glyphs
                if st.Format == 1:
                    for i, g1 in enumerate(cov):
                        if g1 not in g2c:
                            continue
                        for pvr in st.PairSet[i].PairValueRecord:
                            g2 = pvr.SecondGlyph
                            if g2 not in g2c or (g1, g2) in done:
                                continue
                            done.add((g1, g2))
                            v = getattr(pvr.Value1, "XAdvance", 0) or 0 if pvr.Value1 else 0
                            if v:
                                for a in g2c[g1]:
                                    for b in g2c[g2]:
                                        kern[a + b] = kern.get(a + b, 0) + v / upm
                elif st.Format == 2:
                    cd1, cd2 = st.ClassDef1.classDefs, st.ClassDef2.classDefs
                    for g1 in cov:
                        if g1 not in g2c:
                            continue
                        rec1 = st.Class1Record[cd1.get(g1, 0)]
                        for g2 in g2c:
                            if (g1, g2) in done:
                                continue
                            done.add((g1, g2))
                            val = rec1.Class2Record[cd2.get(g2, 0)].Value1
                            v = getattr(val, "XAdvance", 0) or 0 if val else 0
                            if v:
                                for a in g2c[g1]:
                                    for b in g2c[g2]:
                                        kern[a + b] = kern.get(a + b, 0) + v / upm
    return dict(adv=adv, kern=kern, cap=os2.sCapHeight / upm, xh=os2.sxHeight / upm)


def render_glyph(font, ch, em, tables, mono):
    """-> (alpha image, (left, top) of the image relative to the pen at the
    baseline, advance), all in 2x px."""
    advances = tables["adv"]
    if ch == STAR:
        return star_glyph(em, tables["cap"], mono)
    adv = advances[ch] * em
    l, t, r, b = font.getbbox(ch, anchor="ls")
    if r <= l or b <= t:
        return None, (0, 0), adv                          # space
    img = Image.new("L", (r - l, b - t), 0)
    ImageDraw.Draw(img).text((-l, -t), ch, font=font, fill=255, anchor="ls")
    return img, (l, t), adv


def pack(items, w, h):
    """Shelf packing; items (key, img). Positions stay even so the 1x page
    (a 2:1 downscale) keeps every glyph on whole texels."""
    x, y, shelf, placed = 0, 0, 0, {}
    for key, img in items:
        gw, gh = even(img.width + 2 * PAD), even(img.height + 2 * PAD)
        if x + gw > w:
            x, y, shelf = 0, y + shelf, 0
        if y + gh > h:
            return None
        placed[key] = (x, y, gw, gh)
        x += gw
        shelf = max(shelf, gh)
    return placed


def paginate(items):
    """Smallest POT page that holds everything; spill to more pages at 1024."""
    items = sorted(items, key=lambda kv: (-kv[1].height, kv[0]))
    area = sum(even(i.width + 2 * PAD) * even(i.height + 2 * PAD) for _, i in items)
    side = pot(int(math.sqrt(area)))
    for w, h in [(side, side // 2), (side, side), (side * 2, side)]:
        if w <= MAX_PAGE and h <= MAX_PAGE:
            placed = pack(items, w, h)
            if placed:
                return [(w, h, placed)]
    pages, rest = [], items
    while rest:
        placed = pack(rest, MAX_PAGE, MAX_PAGE)
        if placed is None:
            placed, n = {}, 0
            for k in range(len(rest), 0, -1):
                p = pack(rest[:k], MAX_PAGE, MAX_PAGE)
                if p:
                    placed, n = p, k
                    break
            rest_next = rest[n:]
        else:
            rest_next = []
        pages.append((MAX_PAGE, MAX_PAGE, placed))
        rest = rest_next
    return pages


def i4(alpha):
    a = np.asarray(alpha).astype("float64")
    return Image.fromarray((np.round(a / 255 * 15) * 17).astype("uint8"), "L")


def mask_rgba(alpha):
    out = Image.new("RGBA", alpha.size, (255, 255, 255, 0))
    out.putalpha(alpha)
    return out


def build_role(spec):
    em = spec["size"] * 2
    path = kit.font_path(spec["face"], spec["weight"])
    font = ImageFont.truetype(path, em)
    chars = kit.charset(spec["charset"])
    tables = font_tables(path, chars)
    mono = spec["face"] == "mono"
    glyphs, items = {}, []
    for ch in chars:
        img, (l, t), adv = render_glyph(font, ch, em, tables, mono)
        glyphs[ch] = dict(img=img, off=(l, t), adv=adv)
        if img is not None:
            items.append((ch, img))

    pages = paginate(items)
    out_pages, meta = [], {}
    for pi, (w, h, placed) in enumerate(pages):
        page = Image.new("L", (w, h), 0)
        for ch, (x, y, gw, gh) in placed.items():
            page.paste(glyphs[ch]["img"], (x + PAD, y + PAD))
            meta[ch] = (pi, x, y, gw, gh)
        out_pages.append(i4(page))

    rows = {}
    for ch, g in glyphs.items():
        row = dict(advance=round(g["adv"] / 2, 3))
        if ch in meta:
            pi, x, y, gw, gh = meta[ch]
            w, h = pages[pi][0], pages[pi][1]
            l, t = g["off"]
            row.update(page=pi, uv=[x / w, y / h, (x + gw) / w, (y + gh) / h],
                       size=[gw / 2, gh / 2],
                       offset=[(l - PAD) / 2, (t - PAD) / 2])
        rows[ch] = row

    asc, desc = font.getmetrics()
    lh = round(spec["size"] * 1.25)
    size = spec["size"]
    return out_pages, dict(
        role=spec["role"], size=size, face=spec["face"], font=kit.FONTS[spec["face"]]["name"],
        weight=spec["weight"], charset=spec["charset"], use=spec["use"], monospaced=mono,
        metrics=dict(ascent=round(asc / 2, 2), descent=round(desc / 2, 2),
                     cap_height=round(tables["cap"] * size, 2),
                     x_height=round(tables["xh"] * size, 2), line_height=lh,
                     advance_digit=round(tables["adv"]["0"] * size, 3)),
        glyphs=rows,
        kerning={pair: round(v * size, 3) for pair, v in sorted(tables["kern"].items())
                 if pair[0] in chars and pair[1] in chars and round(v * size, 3) != 0})


# --------------------------------------------------------------- setting
def layout_text(role, text, shear=0.0):
    """Pen walk: -> [(ch, x, y, w, h, uv, page)] with (x, y) the glyph's top-
    left relative to the pen origin at the baseline. Same maths the engine
    uses; the specimen is drawn with it."""
    out, pen, prev = [], 0.0, None
    for ch in text:
        if ch not in role["glyphs"]:
            ch = "?"
        if prev:
            pen += role["kerning"].get(prev + ch, 0.0)
        g = role["glyphs"][ch]
        if "uv" in g:
            ox, oy = g["offset"]
            out.append((ch, pen + ox, oy, g["size"][0], g["size"][1], g["uv"], g["page"]))
        pen += g["advance"]
        prev = ch
    return out, pen


def text_width(role, text):
    return layout_text(role, text)[1]


def draw_text(canvas, pages_2x, role, text, x, y, colour, scale=2, shear=0.0):
    """Blit glyphs from the 2x pages onto an RGB canvas at `scale` px per 1x
    unit. With shear, each glyph is sheared about the baseline, as the
    engine's parallelogram quads do."""
    quads, width = layout_text(role, text)
    for ch, gx, gy, gw, gh, uv, page in quads:
        pg = pages_2x[page]
        W, H = pg.size
        crop = pg.crop((round(uv[0] * W), round(uv[1] * H), round(uv[2] * W), round(uv[3] * H)))
        if scale != 2:
            crop = crop.resize((round(gw * scale), round(gh * scale)), Image.LANCZOS)
        if shear:
            # x' = x + (baseline - y) * S, in the crop's own pixel space
            base = -gy * scale
            extra = int(math.ceil(crop.height * shear)) + 1
            crop = crop.transform((crop.width + extra, crop.height), Image.AFFINE,
                                  (1, shear, -shear * base - max(0, shear * (base - crop.height))
                                   + 0, 0, 1, 0),
                                  resample=Image.BICUBIC)
            dx = shear * (base - crop.height) if base > crop.height else 0
        else:
            dx = 0
        px = round(x * scale + gx * scale + dx)
        py = round(y * scale + gy * scale)
        tint = Image.new("RGB", crop.size, colour)
        canvas.paste(tint, (px, py), crop)
    return width


def specimen(manifest, pages, path):
    W, Hh = 640 * 2, 30
    for r in manifest["roles"].values():
        Hh += r["metrics"]["line_height"] * 2 * 2 + 16
    img = Image.new("RGB", (W, Hh), kit.K.hexrgb(kit.SECTIONS["versus"]["bg"]))
    dr = ImageDraw.Draw(img)
    bone, gold = kit.K.hexrgb(kit.PALETTE["bone"]), kit.K.hexrgb(kit.PALETTE["gold"])
    muted = kit.K.hexrgb(kit.PALETTE["muted"])
    y = 12
    sample = {"full": "Princess Peach's Castle 1234567890 ×% … ←→ ★",
              "caps": "VERSUS 1ST 2ND ★ ×4 100%",
              "code": "203.0.113.7:51500 255.255.255.255:65535 [fe80::1]:51500"}
    for name, r in manifest["roles"].items():
        lh = r["metrics"]["line_height"]
        base = y / 2 + r["metrics"]["ascent"] * 0.8
        dr.line((0, round(base * 2), W, round(base * 2)), fill=(40, 60, 120))
        w = draw_text(img, pages[name], r, sample[r["charset"]], 16, base, bone)
        label = "%s %d" % (name, r["size"])
        if r["charset"] == "code":
            label = "%d" % r["size"]
        draw_text(img, pages[name], r, label.upper() if r["charset"] == "caps" else label,
                  16 + w + 12, base, muted)
        base2 = base + lh
        draw_text(img, pages[name], r, sample[r["charset"]], 16, base2, gold, shear=kit.SHEAR)
        y += lh * 2 * 2 + 16
    img.save(path)


# ------------------------------------------------------------------ main
def main():
    for sub in ("2x", "1x"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
        for f in os.listdir(os.path.join(OUT, sub)):
            os.remove(os.path.join(OUT, sub, f))

    manifest = dict(
        fonts={k: "%s, %s (see %s/LICENSE.md)" % (v["name"], v["licence"], v["dir"])
               for k, v in kit.FONTS.items()},
        star="original five-point star drawn by this script (neither font has U+2605)",
        units="1x px. offset = glyph quad top-left relative to the pen at the "
              "baseline (y down, so negative is above). advance moves the pen.",
        setting=[
            "For each character: if a previous character exists, pen.x += "
            "kerning[prev + ch] (absent = 0). Quad at pen + offset, size 'size', "
            "UVs 'uv' on page 'page'; then pen.x += advance.",
            "Missing characters fall back to '?'.",
            "Italic: shear each quad about the baseline, x' = x + (baseline_y - y) "
            "* %g. The quads stay parallelograms, so the texture maps exactly." % kit.SHEAR,
            "Digits share one advance in every role (tabular), so changing numbers "
            "never jitter. The 'tag' role is fully monospaced and has no kerning.",
            "Fit: slots are sized in px. Too wide -> next smaller role of the same "
            "face -> truncate with '…'. Never squash.",
            "Ordinals (%s): numeral in '%s', suffix in '%s', suffix cap top aligned "
            "to numeral cap top." % ("/".join(kit.ORDINAL["suffixes"]),
                                      kit.ORDINAL["numeral"], kit.ORDINAL["suffix"]),
        ],
        scripts=dict(latin="pages listed per role; a second script adds pages "
                           "under its own key without moving latin glyphs"),
        format=dict(gx="I4", fallback="IA4",
                    why="white glyph coverage only; colour comes from vertex/material "
                        "colour, so 4-bit intensity is enough (16 edge levels)"),
        roles={}, textures=[])

    pages_2x, errs, total = {}, [], 0
    for spec in kit.TYPE_SCALE:
        pages, role = build_role(spec)
        name = spec["role"]
        role["pages"] = {"latin": []}
        pages_2x[name] = pages
        for pi, page in enumerate(pages):
            fn = "font_%s_latin_%d" % (name, pi)
            save_png(mask_rgba(page), os.path.join(OUT, "2x", fn + ".png"))
            save_png(downscale_half(mask_rgba(page)), os.path.join(OUT, "1x", fn + ".png"))
            w, h = page.size
            total += w * h // 2
            role["pages"]["latin"].append(fn)
            manifest["textures"].append(dict(
                name=fn, file_2x="out_kit/font/2x/%s.png" % fn,
                file_1x="out_kit/font/1x/%s.png" % fn, size_2x=[w, h],
                format="I4", bytes_2x=w * h // 2))
            if w > MAX_PAGE or h > MAX_PAGE or w & (w - 1) or h & (h - 1):
                errs.append("%s is %dx%d - not POT / over %d" % (fn, w, h, MAX_PAGE))
        manifest["roles"][name] = role

        # checks
        missing = [c for c in kit.charset(spec["charset"]) if c not in role["glyphs"]]
        empty = [c for c, g in role["glyphs"].items() if c != " " and "uv" not in g]
        if missing or empty:
            errs.append("%s: missing %r, empty %r" % (name, missing, empty))
        digits = {role["glyphs"][d]["advance"] for d in "0123456789"}
        if len(digits) != 1:
            errs.append("%s: digits are not tabular: %s" % (name, digits))
        advs = {g["advance"] for g in role["glyphs"].values()}
        if role["monospaced"] and (len(advs) != 1 or role["kerning"]):
            errs.append("%s: not monospaced (%d advances, %d kern pairs)"
                        % (name, len(advs), len(role["kerning"])))

    # names from the brief must fit a portrait-width plate at body size
    names = {"Mr. Game & Watch": 136, "Captain Falcon": 136, "Princess Peach's Castle": 240}
    for s, limit in names.items():
        w = text_width(manifest["roles"]["body"], s)
        if w > limit - 12:
            errs.append("'%s' is %.1f px at body, plate is %d" % (s, w, limit))

    # section 3: 20-character character names on the 136 px portrait plate, by the fit rule
    nf = kit.NAME_FIT
    avail = nf["plate_1x"] - 2 * nf["pad_1x"]
    name_report = {}
    for s in nf["test_names"]:
        if len(s) != nf["max_chars"]:
            errs.append("name test '%s' is %d characters, not %d" % (s, len(s), nf["max_chars"]))
        widths = {r: round(text_width(manifest["roles"][r], s), 1) for r in nf["roles"]}
        fits = next((r for r in nf["roles"] if widths[r] <= avail), None)
        name_report[s] = dict(widths, set_in=fits or "truncated")
        if fits is None:
            errs.append("20-char name '%s' does not fit %d px even at %s (%s)"
                        % (s, avail, nf["roles"][-1], widths))
    manifest["name_fit"] = dict(avail_1x=avail, results=name_report)

    manifest["bytes_2x_total"] = total
    with open(os.path.join(OUT, "font_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)

    os.makedirs(os.path.join(ROOT, "out_kit", "preview"), exist_ok=True)
    specimen(manifest, {k: [p for p in v] for k, v in pages_2x.items()},
             os.path.join(ROOT, "out_kit", "preview", "font_specimen_2x.png"))

    for name, r in manifest["roles"].items():
        sizes = [t["size_2x"] for t in manifest["textures"] if t["name"].startswith("font_%s_" % name)]
        kb = sum(w * h // 2 for w, h in sizes) / 1024
        print("  %-8s %2dpx %-4s %-5s %3d glyphs %4d kern  %s  %6.1f KB"
              % (name, r["size"], r["face"], r["weight"], len(r["glyphs"]), len(r["kerning"]),
                 " ".join("%dx%d" % tuple(s) for s in sizes), kb))
    print("  total @2x I4: %.1f KB" % (total / 1024))
    for s in ("Mr. Game & Watch", "Princess Peach's Castle"):
        print("  '%s' at body: %.1f px" % (s, text_width(manifest["roles"]["body"], s)))
    print("  20-char names on a %d px plate (body -> caption):" % avail)
    for s, r in name_report.items():
        print("    %-22s body %5.1f  caption %5.1f  -> %s" % (s, r["body"], r["caption"], r["set_in"]))
    print("  21-char code at 'code': %.1f px"
          % text_width(manifest["roles"]["code"], "255.255.255.255:65535"))
    if errs:
        print("\nCHECKS FAILED:")
        for e in errs:
            print("  - " + e)
        return 1
    print("\nfont checks ok: full coverage, tabular digits, 'tag' monospaced, longest "
          "names fit, pages POT <= %d" % MAX_PAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
