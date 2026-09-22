"""Element definitions.

Every element is a flat list of sibling layers, absolutely positioned and all
the same size as the canvas. That is what lets the renderer screenshot one
layer at a time (for the .ora) and all of them at once (for the PNG) from
exactly the same markup - the flat and the layered outputs cannot drift apart.

Sizes are 2x (authoring res). 1x is produced by downscaling.
All sizes are powers of two, and therefore also multiples of four.
"""

PANEL_W, PANEL_H = 1024, 512
BTN_W, BTN_H = 512, 128
CUR = 64
CORNER = 128
EDGE_LONG, EDGE_SHORT = 128, 32


def _layer(name, html):
    return (name, '<div class="lyr" data-layer="%s">%s</div>' % (name, html))


# ---------------------------------------------------------------- panel
def panel():
    rivets = "".join(
        '<div class="rivet" style="left:%dpx;top:%dpx"></div>' % (x, y)
        for x, y in ((44, 44), (PANEL_W - 76, 92),
                     (44, PANEL_H - 76), (PANEL_W - 76, PANEL_H - 76))
    )
    return [
        _layer("shadow",  '<div class="clip shadow fill"></div>'),
        _layer("base",    '<div class="clip base fill"></div>'),
        _layer("plate",   '<div class="clip"><div class="plate fill"></div></div>'),
        _layer("hatch",   '<div class="clip"><div class="plate fill">'
                          '<div class="stripes"></div></div></div>'),
        _layer("bevel",   '<div class="clip"><div class="bevel-lt fill"></div>'
                          '<div class="bevel-dk fill"></div></div>'),
        _layer("outline", '<div class="clip outline fill"></div>'),
        _layer("trim",    '<div class="clip"><div class="trim fill"></div></div>'),
        _layer("tab",     '<div class="tab-ink"></div><div class="tab"></div>'),
        _layer("rivets",  rivets),
    ]


# --------------------------------------------------------------- button
def button(state, label="PLAY"):
    cls = "btn" if state == "ng" else "btn " + state
    return cls, [
        _layer("shadow", '<div class="clip shadow fill"></div>'),
        _layer("base",   '<div class="body"><div class="clip outline fill"></div>'
                         '<div class="clip"><div class="inner fill"></div></div></div>'),
        _layer("hatch",  '<div class="body"><div class="clip"><div class="inner fill">'
                         '<div class="stripes"></div></div></div></div>'),
        _layer("bevel",  '<div class="body"><div class="clip">'
                         '<div class="bevel fill"></div></div></div>'),
        _layer("trim",   '<div class="body"><div class="clip">'
                         '<div class="trim fill"></div></div></div>'),
        _layer("chev",   '<div class="body"><div class="chev"></div></div>'),
        _layer("label",  '<div class="body"><div class="label">%s</div></div>' % label),
    ]


# ------------------------------------------------------------------ row
# A text-free list row: the game draws the label and value on top with its
# own font, so the art carries none. `sel` is the cursor's row - lighter
# plate, gold trim, the hover chevron - matching btn_play_hover.
ROW_W, ROW_H = 1024, 64
GLYPH = 64


def row(state):
    cls = "row" if state == "ng" else "row " + state
    return cls, [
        _layer("shadow", '<div class="clip shadow fill"></div>'),
        _layer("base",   '<div class="clip outline fill"></div>'
                         '<div class="clip"><div class="inner fill"></div></div>'),
        _layer("hatch",  '<div class="clip"><div class="inner fill">'
                         '<div class="stripes"></div></div></div>'),
        _layer("trim",   '<div class="clip"><div class="trim fill"></div></div>'),
        _layer("chev",   '<div class="chev"></div>'),
    ]


# ---------------------------------------------------------------- glyph
# Controller button glyphs for the footer hints: flat disc, ink outline,
# hard-offset shadow, bone letter. No gloss - hard stops only.
def glyph(letter, face):
    return "glyph", [
        _layer("shadow", '<div class="disc shadow"></div>'),
        _layer("ink",    '<div class="disc ink"></div>'),
        _layer("face",   '<div class="disc face" style="background:%s"></div>' % face),
        _layer("bevel",  '<div class="disc bevel"></div>'),
        _layer("letter", '<div class="letter">%s</div>' % letter),
    ]


# --------------------------------------------------------------- cursor
# Blocky pointing hand on a 32x32 grid, scaled 2x. Flat fills plus one ink
# stroke weight; nothing here needs more than a handful of colours.
_HAND = "M12 4 h4 v10 h2 v-3 h4 v3 h2 v-2 h4 v2 h2 v9 q0 4 -4 4 h-14 v-23 z"
_SVG = '<svg width="64" height="64" viewBox="0 0 32 32">'


def cursor():
    return [
        _layer("shadow",  _SVG + '<path d="%s" transform="translate(1.5,1.5)" '
                                 'fill="#0a0e18" stroke="#0a0e18" stroke-width="3" '
                                 'stroke-linejoin="round"/></svg>' % _HAND),
        _layer("outline", _SVG + '<path d="%s" fill="#0a0e18" stroke="#0a0e18" '
                                 'stroke-width="3" stroke-linejoin="round"/></svg>' % _HAND),
        _layer("fill",    _SVG + '<path d="%s" fill="#f2efe4"/></svg>' % _HAND),
        _layer("detail",  _SVG + '<g stroke="#0a0e18" stroke-width="1.5" '
                                 'stroke-linecap="round" fill="none">'
                                 '<path d="M18 15 v4"/><path d="M22 15 v4"/>'
                                 '<path d="M26 16 v3"/></g></svg>'),
        _layer("cuff",    _SVG + '<path d="M12 4 h4 v4 h-4 z" fill="#f0b429"/></svg>'),
    ]


# ---------------------------------------------------------------- frame
def _rot(rot, inner):
    return ('<div style="position:absolute;inset:0;transform:rotate(%ddeg);'
            'transform-origin:50%% 50%%">%s</div>' % (rot, inner))


def corner(rot):
    return [
        _layer("ink",  _rot(rot, '<div class="ink fill"></div>')),
        _layer("cob",  _rot(rot, '<div class="cob fill"></div>')),
        _layer("gold", _rot(rot, '<div class="gld fill"></div><div class="cap"></div>')),
    ]


def edge():
    return [
        _layer("ink",  '<div class="ink"></div>'),
        _layer("cob",  '<div class="cob"></div>'),
        _layer("gold", '<div class="gld"></div>'),
    ]


# --------------------------------------------------------------- catalog
def catalog():
    items = []

    items.append(dict(
        name="panel_bg", w=PANEL_W, h=PANEL_H, cls="panel", layers=panel(),
        fmt="CI8 (RGB5A3 TLUT)",
        why="Measured: the whole panel is 74 distinct colours after an RGB5A3 "
            "quantise, so a CI8 index + RGB5A3 palette reproduces it exactly - "
            "byte-identical to straight RGB5A3 at half the memory (512 KB vs "
            "1 MB @2x). Costs one TLUT slot. Fall back to RGB5A3 if TLUT slots "
            "are the scarcer resource; the art is unaffected either way.",
        note="Caption plate for the loading screen and the trophy-get popup. "
             "Diagonal hatch verified against RGB5A3: max delta 8/255, the "
             "stripe separation survives at 8.0 luma, no banding."))

    for state in ("ng", "hover", "press", "disabled"):
        cls, layers = button(state)
        items.append(dict(
            name="btn_play_" + state, w=BTN_W, h=BTN_H, cls=cls, layers=layers,
            fmt="RGBA8",
            why="Carries text. CMPR chews glyph edges and RGB5A3's 5-bit channels "
                "shift the bone-white label off-white. CI8 is out too - hover "
                "measures 258 colours, just over the 256 limit.",
            note="TexAnim frame %d of 4 (ng, hover, press, disabled) on one "
                 "HSD_A_T_TIMG track. Same canvas, same quad, same UV rect: "
                 "'press' is offset +8,+8 @2x inside its own image rather than "
                 "being a smaller texture, so a state change is one "
                 "animateJoint(joint, TOBJ_MASK, %d) call and nothing moves."
                 % (("ng", "hover", "press", "disabled").index(state),
                    ("ng", "hover", "press", "disabled").index(state))))

    for state in ("ng", "hover", "press"):
        cls, layers = button(state, label="CONTINUE")
        items.append(dict(
            name="btn_continue_" + state, w=BTN_W, h=BTN_H, cls=cls, layers=layers,
            fmt="RGBA8",
            why="Carries text, same reasons as btn_play.",
            note="The frontend's 'continue' action (Match Setup -> character "
                 "select). Same canvas and state conventions as btn_play."))

    for state in ("ng", "sel"):
        cls, layers = row(state)
        items.append(dict(
            name="row_" + state, w=ROW_W, h=ROW_H, cls=cls, layers=layers,
            fmt="RGB5A3",
            why="No text, hard edges, a handful of colours; the slanted ends "
                "need only 1-bit alpha, which RGB5A3's opaque mode gives exactly.",
            note="Frontend list row, drawn at ~528x34 @1x under the game's own "
                 "label/value text. 'sel' is the cursor row."))

    for letter, face in (("A", "#2fb36a"), ("B", "#d9433c")):
        cls, layers = glyph(letter, face)
        items.append(dict(
            name="glyph_" + letter.lower(), w=GLYPH, h=GLYPH, cls=cls, layers=layers,
            fmt="RGBA8",
            why="Tiny; carries a letter, so keep it lossless.",
            note="Footer hint glyph, drawn at 24x24 @1x."))

    items.append(dict(
        name="cursor_hand", w=CUR, h=CUR, cls="cursor", layers=cursor(),
        fmt="RGBA8",
        why="Tiny (16 KB at 2x) and needs clean alpha on a stepped silhouette; "
            "CMPR's 1-bit alpha would jag the outline.",
        note="Hotspot (14,4) @1x / (28,8) @2x - tip of the index finger.",
        hotspot_1x=[14, 4]))

    for rot, tag in ((0, "tl"), (90, "tr"), (180, "br"), (270, "bl")):
        items.append(dict(
            name="frame_corner_" + tag, w=CORNER, h=CORNER, cls="fr corner",
            layers=corner(rot), fmt="RGB5A3",
            why="Large transparent region, hard-edged art, no text. Only 5 "
                "colours, so CI8 would halve it - but that saves 16 KB for a "
                "whole TLUT slot, which is the worse trade. Stay RGB5A3.",
            note="9-slice piece. Emitted per orientation rather than relying on "
                 "runtime UV flips - collapse to one texture with mirrored UVs if "
                 "that turns out cheaper."))

    items.append(dict(
        name="frame_edge_h", w=EDGE_LONG, h=EDGE_SHORT, cls="fr edge-h",
        layers=edge(), fmt="RGB5A3",
        why="Constant along U, so it stays crisp stretched between corners.",
        note="9-slice piece. Tileable / stretchable on X."))
    items.append(dict(
        name="frame_edge_v", w=EDGE_SHORT, h=EDGE_LONG, cls="fr edge-v",
        layers=edge(), fmt="RGB5A3",
        why="Constant along V, so it stays crisp stretched between corners.",
        note="9-slice piece. Tileable / stretchable on Y."))

    return items
