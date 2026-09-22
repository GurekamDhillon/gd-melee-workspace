"""Hub main menu - layout as geometry.

The whole screen is authored as axis-aligned rectangles in an "unsheared"
space, then pushed through ONE shear:

    x' = x + (Y0 - y) * S        y' = y

so every vertical edge on screen leans by the same angle and every gutter is
parallel. A sheared rectangle is a parallelogram, and a parallelogram maps a
texture *exactly* with two triangles (the map is affine). That is what makes
the italic labels free: the label texture is upright text, and the shear on
the quad italicises it. A trapezoid would not work - two affine triangles
kink the texture along the diagonal - so textured quads must stay
parallelograms. build asserts this.

Colour lives in geometry (flat vertex/material colour), never in textures.
The only textures are white alpha masks: labels and icon silhouettes.
Coordinates are 1x framebuffer pixels (640x480), origin top-left, y down.
"""

S = 0.25          # shear: ~14 degrees
Y0 = 240          # shear pivot row (screen centre) - keeps the layout centred

SAFE = (32, 24, 608, 456)     # title-safe 90%, 576x432 @1x

C = dict(
    ink="#0a0e18", bg="#14265c", band="#1a307a",
    cobalt="#1e3a8c", cobalt_lt="#2f55b8", cobalt_hi="#4a7ae0",
    gold="#f0b429", gold_lt="#ffd766", gold_dk="#a9761a", bone="#f2efe4",
)


def shear(x, y):
    return [round(x + (Y0 - y) * S, 3), round(y, 3)]


def para(x0, y0, x1, y1):
    """Unsheared rect -> screen parallelogram, vertices TL, TR, BR, BL."""
    return [shear(x0, y0), shear(x1, y0), shear(x1, y1), shear(x0, y1)]


# Buckets, broad to specific. Rank 0 is the hero: it gets the dominant tile.
BUCKETS = [
    dict(id="versus",     label="VERSUS",     rank=0,
         desc="Up to four players. Your rules, your stage."),
    dict(id="solo",       label="SOLO",       rank=1,
         desc="Challenges, training and solo play."),
    dict(id="collection", label="COLLECTION", rank=2,
         desc="Trophies, replays, sound test and records."),
    dict(id="options",    label="OPTIONS",    rank=3,
         desc="Controls, sound, display and save data."),
]

# Unsheared tile rects. Size hierarchy is the point: the hero takes the full
# height; the secondaries step down 144 -> 110 -> 82.
TILES = {
    "versus":     (90, 68, 352, 420),
    "solo":       (360, 68, 556, 212),
    "collection": (360, 220, 556, 330),
    "options":    (360, 338, 556, 420),
}
GUTTER = 6        # backplate overhang; tiles sit 8px apart, ink shows through

# The shear moves the top of the screen +54px and the bottom -54px, so the
# horizontal extents here are narrower than they look. hub.py checks it.
HEADER = (84, 24, 550, 52)
FOOTER = (90, 430, 596, 456)

STATES = {
    # colours are material colours; label/icon textures are white masks
    "ng":  dict(face=C["cobalt"], icon=C["cobalt_hi"], label=C["bone"],
                offset=[0, 0], plate=None, z=0),
    # selected: face lifts up-left, a darker plate stays behind at rest
    # position - a flat, hard-edged extrusion, no shadow blur anywhere
    "sel": dict(face=C["gold"], icon=C["gold_dk"], label=C["ink"],
                offset=[-5, -5], plate=C["gold_dk"], z=1),
}


def _flat(id_, verts, colour, role):
    return dict(id=id_, kind="flat", role=role, verts=verts, colour=colour)


def _tex(id_, tex, rect, colour, role):
    return dict(id=id_, kind="textured", role=role, texture=tex["name"],
                verts=para(*rect), uv=tex["uv"], colour=colour)


def build(tex):
    """tex: name -> dict(name, size_2x, uv (normalised u0,v0,u1,v1), quad_1x (w,h))"""
    quads = []

    # --- backdrop: decor bands may bleed off-screen, nothing else may
    quads.append(_flat("band_l", para(18, -40, 40, 520), C["band"], "decor"))
    quads.append(_flat("band_r", para(572, -40, 612, 520), C["band"], "decor"))

    # --- header: short gold slab behind the title, ink rule for the rest
    t = tex["lbl_title"]
    tw, th = t["quad_1x"]
    hx0, hy0, hx1, hy1 = HEADER
    slab_x1 = hx0 + 16 + tw + 20
    quads.append(_flat("header_rule", para(slab_x1 - 4, hy1 - 6, hx1, hy1),
                       C["ink"], "chrome"))
    quads.append(_flat("header_slab", para(hx0, hy0, slab_x1, hy1),
                       C["gold"], "chrome"))
    ty = hy0 + (hy1 - hy0 - th) / 2
    quads.append(_tex("header_title", t, (hx0 + 16, ty, hx0 + 16 + tw, ty + th),
                      C["ink"], "chrome"))

    # --- cluster backplate: one ink quad, gutters are just this showing through
    xs = [r[0] for r in TILES.values()] + [r[2] for r in TILES.values()]
    ys = [r[1] for r in TILES.values()] + [r[3] for r in TILES.values()]
    quads.append(_flat("backplate", para(min(xs) - GUTTER, min(ys) - GUTTER,
                                         max(xs) + GUTTER, max(ys) + GUTTER),
                       C["ink"], "chrome"))

    # --- footer: ink strip, gold marker, description swaps per selection
    fx0, fy0, fx1, fy1 = FOOTER
    quads.append(_flat("footer_strip", para(fx0, fy0, fx1, fy1), C["ink"], "chrome"))
    quads.append(_flat("footer_mark", para(fx0 + 10, fy0 + 7, fx0 + 22, fy1 - 7),
                       C["gold"], "chrome"))

    tiles = []
    for b in BUCKETS:
        x0, y0, x1, y1 = TILES[b["id"]]
        hero = b["rank"] == 0
        pad = 16 if hero else 10

        ico = tex["ico_%s" % b["id"]]
        iw, ih = ico["quad_1x"]
        icon_rect = (x1 - pad - iw, y0 + pad, x1 - pad, y0 + pad + ih)

        lbl = tex["lbl_%s" % b["id"]]
        lw, lh = lbl["quad_1x"]
        label_rect = (x0 + pad + 2, y1 - pad - lh, x0 + pad + 2 + lw, y1 - pad)

        d = tex["desc_%s" % b["id"]]
        dw, dh = d["quad_1x"]
        dy = fy0 + (fy1 - fy0 - dh) / 2
        desc_rect = (fx0 + 32, dy, fx0 + 32 + dw, dy + dh)

        tiles.append(dict(
            id=b["id"], rank=b["rank"], hero=hero,
            rect_unsheared=[x0, y0, x1, y1],
            quads=[
                _flat("%s_plate" % b["id"], para(x0, y0, x1, y1), None, "plate"),
                _flat("%s_face" % b["id"], para(x0, y0, x1, y1),
                      STATES["ng"]["face"], "face"),
                _tex("%s_icon" % b["id"], ico, icon_rect, STATES["ng"]["icon"], "icon"),
                _tex("%s_label" % b["id"], lbl, label_rect, STATES["ng"]["label"], "label"),
            ],
            desc=_tex("%s_desc" % b["id"], d, desc_rect, C["bone"], "desc"),
            _label_rect=label_rect, _icon_rect=icon_rect,
        ))

    return dict(
        framebuffer=[640, 480],
        units="1x framebuffer pixels, origin top-left, y down",
        shear=dict(S=S, Y0=Y0, formula="x' = x + (Y0 - y) * S"),
        clear_colour=C["bg"],
        safe_area=list(SAFE),
        states=STATES,
        state_rules=[
            "Exactly one tile is 'sel'; the rest are 'ng'.",
            "On 'sel': face/icon/label take the sel colours, the face, icon "
            "and label quads translate by 'offset', the plate quad becomes "
            "visible in 'plate' colour at rest position, and the tile draws "
            "above its neighbours (z).",
            "Only the selected tile's 'desc' quad is visible.",
            "No state adds or swaps a texture. Selection is colour + "
            "translate: material colour animation and a joint translate.",
        ],
        quads=quads,
        tiles=tiles,
    )
