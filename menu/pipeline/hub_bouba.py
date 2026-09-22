"""Hub main menu, bouba variant - layout as geometry.

Same contract as hub_layout.py: colour lives in geometry, the only textures
are white masks (labels, icons), and selection is material colour + a joint
translate. What changes is the silhouette: the hero is a circle, the
secondaries are stadiums (pills), and the chrome is pill-shaped.

GX has no clip paths and no curves, so every round shape is a convex polygon
emitted as a triangle fan (centre + ring). The preview draws exactly those
vertices. Segment counts keep the chord error under MAX_SAG px at 1x, so the
facets are sub-pixel on screen.

Textured quads stay axis-aligned rectangles placed wholly inside their shape,
so nothing needs clipping. hub_bouba_build.py checks that.
Coordinates are 1x framebuffer pixels (640x480), origin top-left, y down.
"""
import math

MAX_SAG = 0.25                # max chord error, px @1x
SAFE = (32, 24, 608, 456)     # title-safe 90%
OUTLINE = 4                   # ink ring around every tile
INSET = 6                     # min distance from a label/icon to its tile edge

C = dict(
    ink="#0a0e18", bg="#14265c", band="#1a307a",
    cobalt="#1e3a8c", cobalt_lt="#2f55b8", cobalt_hi="#4a7ae0",
    gold="#f0b429", gold_lt="#ffd766", gold_dk="#a9761a", bone="#f2efe4",
)

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

# The hero reads first: largest shape, left, vertically centred on the
# cluster. Secondaries step down 132 -> 104 -> 88, 14px apart.
SHAPES = {
    "versus":     dict(type="circle", cx=190, cy=244, r=150),
    "solo":       dict(type="stadium", rect=[354, 68, 600, 200]),
    "collection": dict(type="stadium", rect=[354, 214, 600, 318]),
    "options":    dict(type="stadium", rect=[354, 332, 600, 420]),
}

HEADER = (40, 24, 600, 52)
FOOTER = (40, 430, 600, 456)

STATES = {
    "ng":  dict(face=C["cobalt"], icon=C["cobalt_hi"], label=C["bone"],
                offset=[0, 0], plate=None, z=0),
    # selected: the face lifts up-left off a darker plate left at rest - a
    # flat, hard-edged extrusion, same language as the rectangular hub
    "sel": dict(face=C["gold"], icon=C["gold_dk"], label=C["ink"],
                offset=[-5, -5], plate=C["gold_dk"], z=1),
}


# ---------------------------------------------------------------- shapes
def segs(r):
    """Ring segments for radius r so the chord error stays under MAX_SAG."""
    n = math.ceil(math.pi / math.acos(1 - MAX_SAG / r))
    return max(8, -(-n // 4) * 4)


def stadium(x0, y0, x1, y1):
    return dict(type="stadium", rect=[x0, y0, x1, y1])


def circle(cx, cy, r):
    return dict(type="circle", cx=cx, cy=cy, r=r)


def centre(s):
    if s["type"] == "circle":
        return [s["cx"], s["cy"]]
    x0, y0, x1, y1 = s["rect"]
    return [(x0 + x1) / 2, (y0 + y1) / 2]


def ring(s, grow=0.0):
    """Convex outline, clockwise on screen. Engine draws it as a fan."""
    if s["type"] == "circle":
        cx, cy, r = s["cx"], s["cy"], s["r"] + grow
        n = segs(r)
        return [[round(cx + r * math.cos(2 * math.pi * i / n - math.pi / 2), 3),
                 round(cy + r * math.sin(2 * math.pi * i / n - math.pi / 2), 3)]
                for i in range(n)]
    x0, y0, x1, y1 = s["rect"]
    x0, y0, x1, y1 = x0 - grow, y0 - grow, x1 + grow, y1 + grow
    r = (y1 - y0) / 2
    cy = (y0 + y1) / 2
    assert x1 - x0 >= 2 * r, "stadium narrower than its height"
    n = segs(r) // 2
    pts = []
    for cx, a0 in ((x1 - r, -math.pi / 2), (x0 + r, math.pi / 2)):
        for i in range(n + 1):
            a = a0 + math.pi * i / n
            pts.append([round(cx + r * math.cos(a), 3), round(cy + r * math.sin(a), 3)])
    return pts


def sdf(s, x, y):
    """Signed distance to the true shape edge; negative inside."""
    if s["type"] == "circle":
        return math.hypot(x - s["cx"], y - s["cy"]) - s["r"]
    x0, y0, x1, y1 = s["rect"]
    r = (y1 - y0) / 2
    px = min(max(x, x0 + r), x1 - r)
    return math.hypot(x - px, y - (y0 + y1) / 2) - r


def area(s):
    if s["type"] == "circle":
        return math.pi * s["r"] ** 2
    x0, y0, x1, y1 = s["rect"]
    r = (y1 - y0) / 2
    return (x1 - x0 - 2 * r) * (y1 - y0) + math.pi * r * r


# ----------------------------------------------------------------- quads
def _fan(id_, s, colour, role, grow=0.0):
    return dict(id=id_, kind="fan", role=role, centre=centre(s),
                verts=ring(s, grow), colour=colour)


def _tex(id_, tex, rect, colour, role):
    x0, y0, x1, y1 = rect
    return dict(id=id_, kind="textured", role=role, texture=tex["name"],
                verts=[[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                uv=tex["uv"], colour=colour)


def _centred(cx, cy, w, h):
    return (round(cx - w / 2, 3), round(cy - h / 2, 3),
            round(cx + w / 2, 3), round(cy + h / 2, 3))


def build(tex):
    """tex: name -> dict(name, size_2x, uv (normalised), quad_1x (w,h))"""
    quads = []

    # --- backdrop: two big soft blobs, allowed to bleed off-screen
    quads.append(_fan("blob_bl", circle(-20, 480, 200), C["band"], "decor"))
    quads.append(_fan("blob_tr", circle(660, 10, 150), C["band"], "decor"))

    # --- header: gold pill behind the title, thin ink pill for the rest
    t = tex["lbl_title"]
    tw, th = t["quad_1x"]
    hx0, hy0, hx1, hy1 = HEADER
    hh = hy1 - hy0
    slab_x1 = hx0 + hh / 2 + tw + hh / 2
    quads.append(_fan("header_rule", stadium(slab_x1 - 10, hy1 - 6, hx1, hy1),
                      C["ink"], "chrome"))
    quads.append(_fan("header_slab", stadium(hx0, hy0, slab_x1, hy1),
                      C["gold"], "chrome"))
    quads.append(_tex("header_title", t,
                      _centred((hx0 + slab_x1) / 2, (hy0 + hy1) / 2, tw, th),
                      C["ink"], "chrome"))

    # --- footer: ink pill, gold dot, description swaps per selection
    fx0, fy0, fx1, fy1 = FOOTER
    fcy = (fy0 + fy1) / 2
    quads.append(_fan("footer_strip", stadium(fx0, fy0, fx1, fy1), C["ink"], "chrome"))
    quads.append(_fan("footer_dot", circle(fx0 + 16, fcy, 5), C["gold"], "chrome"))

    tiles = []
    for b in BUCKETS:
        s = SHAPES[b["id"]]
        hero = b["rank"] == 0
        ico, lbl = tex["ico_" + b["id"]], tex["lbl_" + b["id"]]
        lw, lh = lbl["quad_1x"]

        if hero:
            # icon above, label below, both centred on the circle
            size = 112
            icon_rect = _centred(s["cx"], s["cy"] - 44, size, size)
            label_rect = _centred(s["cx"], s["cy"] + 46, lw, lh)
        else:
            # icon + label as one group, centred in the pill
            x0, y0, x1, y1 = s["rect"]
            h = y1 - y0
            cy = (y0 + y1) / 2
            size = round(h * 0.52)
            gx0 = round((x0 + x1) / 2 - (size + 12 + lw) / 2, 3)
            icon_rect = (gx0, round(cy - size / 2, 3), gx0 + size, round(cy + size / 2, 3))
            lx0 = gx0 + size + 12
            label_rect = (lx0, round(cy - lh / 2, 3), lx0 + lw, round(cy + lh / 2, 3))

        d = tex["desc_" + b["id"]]
        dw, dh = d["quad_1x"]
        desc_rect = (fx0 + 30, round(fcy - dh / 2, 3), fx0 + 30 + dw, round(fcy + dh / 2, 3))

        tiles.append(dict(
            id=b["id"], rank=b["rank"], hero=hero, shape=s,
            quads=[
                _fan("%s_outline" % b["id"], s, C["ink"], "outline", grow=OUTLINE),
                _fan("%s_plate" % b["id"], s, None, "plate"),
                _fan("%s_face" % b["id"], s, STATES["ng"]["face"], "face"),
                _tex("%s_icon" % b["id"], ico, icon_rect, STATES["ng"]["icon"], "icon"),
                _tex("%s_label" % b["id"], lbl, label_rect, STATES["ng"]["label"], "label"),
            ],
            desc=_tex("%s_desc" % b["id"], d, desc_rect, C["bone"], "desc"),
            _label_rect=label_rect, _icon_rect=icon_rect,
        ))

    return dict(
        framebuffer=[640, 480],
        units="1x framebuffer pixels, origin top-left, y down",
        design="bouba: circle hero, stadium secondaries, pill chrome",
        clear_colour=C["bg"],
        safe_area=list(SAFE),
        geometry_notes=[
            "kind 'fan': one GX_TRIANGLEFAN - emit 'centre', then every point "
            "of 'verts', then verts[0] again to close. Flat material colour, "
            "no texture. Rings are convex, clockwise on screen.",
            "kind 'textured': axis-aligned quad, two triangles, white-mask "
            "texture tinted by material colour. Always fully inside its tile "
            "shape, so no clipping is needed.",
            "Ring density: chord error <= %.2f px @1x." % MAX_SAG,
        ],
        states=STATES,
        state_rules=[
            "Exactly one tile is 'sel'; the rest are 'ng'.",
            "On 'sel': face/icon/label take the sel colours and translate by "
            "'offset'; the plate fan becomes visible in 'plate' colour at rest "
            "position; the tile draws above its neighbours (z).",
            "The outline fan never moves or changes colour.",
            "Only the selected tile's 'desc' quad is visible.",
            "No state adds or swaps a texture or a mesh.",
        ],
        quads=quads,
        tiles=tiles,
    )
