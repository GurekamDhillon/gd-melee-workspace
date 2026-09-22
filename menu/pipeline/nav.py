"""Section 2: navigation screens - hubs from a rule, lists from the kit template, grids,
tables, the event list and the sound test.

    python pipeline/kit.py && python pipeline/font_atlas.py && python pipeline/glyphs.py \
        && python pipeline/icons.py && python pipeline/kit_ui.py && python pipeline/nav.py

Writes out_nav/:
    hubs_layout.json          THE HUB RULE for 1-9 tiles: cluster, column split, height
                              steps, tile size classes, label setting chain, states
    hub_<screen>_layout.json  every hub generated from the rule (hub_layout.json format,
                              unsheared kit convention, labels are atlas text slots)
    nav_motion.json           hub motion in the kit convention (unsheared, colour tokens)
    list_<screen>_layout.json the list screens: rows, widgets, maxima
    grid_layout.json          checkbox-cell grid rule (Item Switch, Random Stage Switch)
    table_layout.json         records table template
    event_layout.json         event list + detail panel
    soundtest_layout.json     track rows with a playing indicator
    manifest.json             every section-2 texture, GX format and why; memory per screen
    preview/                  composed from the JSON alone

Hub labels and descriptions come from the font atlas. Nothing is baked: the old out_hub
Arial Black label textures (lbl_*, desc_*) are retired.
"""
import json
import math
import os
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit                                                  # noqa: E402
import kit_ui as U                                          # noqa: E402
from build import downscale_half                           # noqa: E402

K = kit.K
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_nav")
S, Y0 = kit.SHEAR, 240
SAFE = U.SAFE
Q, T, k, tr = U.Q, U.T, U.k, U.tr
text_w, base_for, cap = U.text_w, U.base_for, U.cap
SANS = ["caption", "body", "row", "label", "title", "heading", "hero", "display"]
ROLES = U.ROLES


def fit1(role, s, width):
    """Kit fit rule: role, one smaller, then truncate. -> (role, string)."""
    chain = [role] + ([SANS[SANS.index(role) - 1]] if SANS.index(role) > 0 else [])
    for r in chain:
        if text_w(r, s) <= width + 0.01:
            return r, s
    r = chain[-1]
    while s and text_w(r, s + "…") > width:
        s = s[:-1]
    return r, s.rstrip() + "…"


# ================================================================ THE HUB RULE
CLUSTER = (90, 82, 556, 390)          # unsheared; between the breadcrumb and description
HERO_X1 = 352                         # hero column 90..352 (262), secondaries 360..556 (196)
SEC_X0 = 360
G = 8                                 # gutter: the ink backplate shows through
BACKPLATE = 6                         # backplate overhang around the cluster
LIFT = [-6.25, -5.0]                  # unsheared = (-5, -5) on screen, the prototype's lift
LIFT_PEAK = 1.3                       # select overshoot
SCALE_PEAK = 1.03
RECOIL = 2.0


def ratio(s):
    """Height step between consecutive secondaries. 0.76 is the prototype's
    144 -> 110 -> 82; it flattens as the column fills so the last tile never drops
    below a row's height."""
    return min(1.0, 0.76 + 0.06 * max(0, s - 3))


def hub_rects(n):
    """Tile rects (unsheared) in rank order: rank 0 is the hero."""
    x0, y0, x1, y1 = CLUSTER
    if n == 1:
        return [(x0, y0, x1, y1)]
    rects = [(x0, y0, HERO_X1, y1)]
    s = n - 1
    avail = (y1 - y0) - G * (s - 1)
    r = ratio(s)
    w = [r ** i for i in range(s)]
    tot = sum(w)
    cum = 0.0
    edge = 0                                   # cumulative rounding: no drift at the end
    for i in range(s):
        cum += w[i]
        nxt = round(avail * cum / tot)
        top = y0 + edge + G * i
        rects.append((SEC_X0, top, x1, y0 + nxt + G * i))
        edge = nxt
    return rects


# size classes by tile height (the hero is its own class)
CLASSES = {
    "hero":  dict(pad=16, icon=96, place="icon top-right, label bottom-left",
                  chain=[("hero", 1), ("hero", 2), ("heading", 1), ("heading", 2), ("title", 1)]),
    "tall":  dict(min_h=96, pad=10, icon=40, place="icon top-right, label bottom-left",
                  chain=[("label", 1), ("label", 2), ("row", 1), ("row", 2)]),
    "mid":   dict(min_h=44, pad=10, icon=28, place="icon right, centred; label left, centred",
                  chain=[("label", 1), ("row", 1), ("row", 2), ("body", 1)]),
    "short": dict(min_h=0, pad=8, icon=24, place="icon right, centred; label left, centred",
                  chain=[("row", 1), ("body", 1)]),
}


def size_class(h, hero):
    if hero:
        return "hero"
    return "tall" if h >= 96 else "mid" if h >= 44 else "short"


def line_pitch(role):
    return round(ROLES[role]["size"] * 1.08, 2)          # caps only: cap height + a gap


def split_lines(s, n, role, width):
    """Break s at spaces into n lines, minimising the widest line; None if a word
    alone is too wide."""
    words = s.split(" ")
    if n == 1:
        return [s] if text_w(role, s) <= width + 0.01 else None
    if len(words) < n:
        return None
    best = None
    for cut in range(1, len(words)):
        a, b = " ".join(words[:cut]), " ".join(words[cut:])
        wmax = max(text_w(role, a), text_w(role, b))
        if wmax <= width + 0.01 and (best is None or wmax < best[0]):
            best = (wmax, [a, b])
    return best[1] if best else None


def set_label(s, cls, width, height):
    """-> (role, [lines]) by the class chain; truncates at the last step."""
    for role, n in CLASSES[cls]["chain"]:
        lines = split_lines(s, n, role, width)
        if lines and (cap(role) + (n - 1) * line_pitch(role)) <= height:
            return role, lines, False
    role = CLASSES[cls]["chain"][-1][0]
    r, t = fit1(role, s, width)
    return r, [t], True


SEC_ROLES = ["label", "row", "body"]


def label_box(rect, cls):
    """(width, height) the label may use in a tile of this class."""
    x0, y0, x1, y1 = rect
    c = CLASSES[cls]
    pad, ic = c["pad"], c["icon"]
    if cls in ("hero", "tall"):
        return x1 - x0 - 2 * pad - (4 if cls == "hero" else 0), (y1 - pad) - (y0 + pad + ic + 6)
    return (x1 - pad - ic) - 8 - (x0 + pad), y1 - y0 - 2 * pad


def fits_at(label, rect, cls, role):
    w, h = label_box(rect, cls)
    for n in ((1, 2) if cls != "short" else (1,)):
        lines = split_lines(label, n, role, w)
        if lines and cap(role) + (n - 1) * line_pitch(role) <= h:
            return lines
    return None


def secondary_role(tiles):
    """One role for every secondary tile of a hub: the largest in SEC_ROLES at which
    every secondary label fits (one line, or two where the class allows)."""
    for role in SEC_ROLES:
        if all(fits_at(lab, rect, cls, role) for lab, rect, cls in tiles):
            return role
    return None


def tile_layout(rect, cls, label, role=None):
    """Icon rect and label lines/baselines for one tile, all unsheared. role: the hub's
    shared secondary role (None for the hero, which uses its own chain)."""
    x0, y0, x1, y1 = rect
    c = CLASSES[cls]
    pad, ic = c["pad"], c["icon"]
    if cls in ("hero", "tall"):
        icon = (x1 - pad - ic, y0 + pad, x1 - pad, y0 + pad + ic)
        lw, lh = label_box(rect, cls)
        role, lines, trunc = pick(label, rect, cls, role, lw, lh)
        p = line_pitch(role)
        last = y1 - pad
        bases = [last - (len(lines) - 1 - i) * p for i in range(len(lines))]
        lx = x0 + pad + 2
    else:
        cy = (y0 + y1) / 2
        icon = (x1 - pad - ic, cy - ic / 2, x1 - pad, cy + ic / 2)
        lw, lh = label_box(rect, cls)
        role, lines, trunc = pick(label, rect, cls, role, lw, lh)
        p = line_pitch(role)
        block = cap(role) + (len(lines) - 1) * p
        top = cy - block / 2
        bases = [top + cap(role) + i * p for i in range(len(lines))]
        lx = x0 + pad
    return dict(icon=icon, role=role, lines=lines, bases=bases, x=lx, width=lw, height=lh,
                truncated=trunc)


def pick(label, rect, cls, role, lw, lh):
    if role is None:
        return set_label(label, cls, lw, lh)
    lines = fits_at(label, rect, cls, role)
    if lines:
        return role, lines, False
    r, t = fit1(role, label, lw)
    return r, [t], True


# ---- the hubs (items in rank order: hero first, then the menu's own order)
HUBS = {
    "main": dict(title="MAIN MENU", section=None, crumbs=[], items=[
        ("versus", "VERSUS", "ico_versus", "Up to four players. Your rules, your stage.", "versus"),
        ("solo", "SOLO", "ico_solo", "Classic, Adventure, events, training and more.", "solo"),
        ("collection", "COLLECTION", "ico_collection",
         "Trophies: gallery, lottery and your collection.", "collection"),
        ("options", "OPTIONS", "ico_options", "Rumble, sound, display, language and save data.",
         "options"),
        ("data", "DATA", "ico_data", "Snapshots, movies, sound test, records, messages.", "data")]),
    "solo": dict(title="SOLO", section="solo", crumbs=["SOLO"], items=[
        ("regular", "REGULAR MATCH", "ico_regular", "Classic, Adventure and All-Star."),
        ("event", "EVENT MATCH", "ico_event", "Special battles with their own rules."),
        ("stadium", "STADIUM", "ico_stadium", "Target Test, Home-Run Contest and Multi-Man."),
        ("training", "TRAINING", "ico_training", "Practice against a dummy, any stage, any speed.")]),
    "regular": dict(title="REGULAR MATCH", section="solo", crumbs=["SOLO", "REGULAR MATCH"], items=[
        ("classic", "CLASSIC", "ico_classic", "A series of battles, then the final boss."),
        ("adventure", "ADVENTURE", "ico_adventure", "Side-scrolling stages between the battles."),
        ("allstar", "ALL-STAR", "ico_allstar", "Every fighter, one after another.")]),
    "stadium": dict(title="STADIUM", section="solo", crumbs=["SOLO", "STADIUM"], items=[
        ("target", "TARGET TEST", "ico_target", "Break every target as fast as you can."),
        ("homerun", "HOME-RUN CONTEST", "ico_homerun", "Launch the Sandbag as far as it will go."),
        ("multiman", "MULTI-MAN MELEE", "ico_multiman", "Take on a whole team of fighters.")]),
    "versus": dict(title="VERSUS", section="versus", crumbs=["VERSUS"], items=[
        ("melee", "MELEE", "ico_melee", "Up to four players. Your rules, your stage."),
        ("online", "ONLINE", "ico_online", "Play a friend over the internet."),
        ("tournament", "TOURNAMENT", "ico_tournament", "A bracket for up to 64 players."),
        ("special", "SPECIAL MELEE", "ico_special", "Melee with a twist."),
        ("rules", "RULES", "ico_rules", "Stock, time, items and stages."),
        ("names", "NAME ENTRY", "ico_names", "Make a name tag.")]),
    "collection": dict(title="COLLECTION", section="collection", crumbs=["COLLECTION"], items=[
        ("trophies", "COLLECTION", "ico_trophies", "Arrange trophies on a stand."),
        ("gallery", "GALLERY", "ico_gallery", "Look at the trophies you have."),
        ("lottery", "LOTTERY", "ico_lottery", "Spend coins on new trophies.")]),
    "data": dict(title="DATA", section="data", crumbs=["DATA"], items=[
        ("records", "RECORDS", "ico_records", "VS, bonus and other records."),
        ("snapshots", "SNAPSHOTS", "ico_snapshots", "Pictures saved to the memory card."),
        ("movies", "MOVIES", "ico_movies", "Watch the movies you have seen."),
        ("soundtest", "SOUND TEST", "ico_soundtest", "Listen to music, effects and voices."),
        ("messages", "SPECIAL MESSAGES", "ico_messages", "Messages you have unlocked.")]),
}

STATES = dict(
    ng=dict(face="@face", icon="@face_hi", label="bone", plate=None, offset=[0, 0]),
    sel=dict(face="gold", icon="gold_dk", label="ink", plate="gold_dk", offset=LIFT),
)


def build_hub(hid, spec=None, labels=None):
    spec = spec or HUBS[hid]
    items = spec["items"]
    rects = hub_rects(len(items))
    classes = [size_class(r[3] - r[1], rank == 0) for rank, r in enumerate(rects)]
    sec_role = secondary_role([(it[1], r, c) for it, r, c in
                               zip(items[1:], rects[1:], classes[1:])]) or SEC_ROLES[-1]
    tiles = []
    for rank, (it, rect) in enumerate(zip(items, rects)):
        iid, label, icon, desc = it[:4]
        sec = it[4] if len(it) > 4 else spec["section"]
        cls = classes[rank]
        L = tile_layout(rect, cls, labels[rank] if labels else label,
                        None if cls == "hero" else sec_role)
        x0, y0, x1, y1 = rect
        tiles.append(dict(
            id=iid, rank=rank, hero=cls == "hero", size_class=cls, section=sec,
            rect_unsheared=list(rect),
            pivot=[round((x0 + x1) / 2, 2), round((y0 + y1) / 2, 2)],
            quads=[Q("%s_plate" % iid, rect, None, role="plate", joint="plate_%s" % iid),
                   Q("%s_face" % iid, rect, "@face", role="face", joint="lift_%s" % iid),
                   Q("%s_icon" % iid, L["icon"], "@face_hi", role="icon", joint="lift_%s" % iid,
                     texture=icon)],
            slots=[dict(T("%s_label_%d" % (iid, n), L["role"], (L["x"], b), line, "bone",
                          joint="lift_%s" % iid, max_width=L["width"]), line_of=len(L["lines"]))
                   for n, (line, b) in enumerate(zip(L["lines"], L["bases"]))],
            label=labels[rank] if labels else label, desc=desc,
            _L=L))
    return dict(
        name="hub_%s" % hid, space="unsheared", shear=dict(S=S, Y0=Y0),
        rule="hubs_layout.json", section=spec["section"] or "per tile (main menu)",
        chrome=dict(template="chrome_layout.json", title=spec["title"], crumbs=spec["crumbs"],
                    crumb_icon=None if hid == "main" else "ico_" + spec["section"],
                    description="the selected tile's desc, in the description strip"),
        cluster=dict(rect=list(CLUSTER),
                     backplate=Q("backplate", (CLUSTER[0] - BACKPLATE, CLUSTER[1] - BACKPLATE,
                                               CLUSTER[2] + BACKPLATE, CLUSTER[3] + BACKPLATE),
                                 "ink", joint="cluster")),
        tiles=tiles, states=STATES,
        textures=[])


def hubs_rule():
    ex = {n: [[round(v, 2) for v in r] for r in hub_rects(n)] for n in range(1, 10)}
    return dict(
        name="hubs", space="unsheared", shear=dict(S=S, Y0=Y0),
        what="The layout rule every hub (2-9 tiles) is generated from. hub_<screen>_layout.json "
             "are its output for the vanilla hubs; any other hub follows the same steps.",
        cluster=dict(rect=list(CLUSTER), hero_x1=HERO_X1, secondary_x0=SEC_X0, gutter=G,
                     backplate_overhang=BACKPLATE),
        steps=[
            "Order the items by rank: the menu's hero item first, then the others in menu order.",
            "n = 1: the tile fills the cluster (hero class).",
            "n >= 2: rank 0 is the hero, x %d..%d, full cluster height. The other s = n - 1 "
            "tiles stack in one column, x %d..%d." % (CLUSTER[0], HERO_X1, SEC_X0, CLUSTER[2]),
            "Column heights: avail = cluster height - gutter * (s - 1); r = min(1, 0.76 + "
            "0.06 * max(0, s - 3)). Tile i spans edge(i-1)..edge(i) with edge(i) = "
            "round(avail * sum(r^0..r^i) / sum(r^0..r^(s-1))), offset by gutter * i "
            "(cumulative rounding: the column ends exactly at the cluster bottom and no tile "
            "is more than 1 px off its share).",
            "Each tile's size class comes from its height: hero; tall h >= 96; mid 44 <= h < 96; "
            "short h < 44. The class sets padding, icon size and placement, and the label chain.",
            "Labels are set from the atlas, caps. The hero tries its chain in order - (role, "
            "lines) - and takes the first where every line fits the label width and the block "
            "fits the label height. The secondaries share ONE role per hub, so the column reads "
            "evenly: the largest of label / row / body at which every secondary label fits, in "
            "one line or (except short tiles) two. Two-line labels break at a space, balancing "
            "the lines. If nothing fits, truncate with '…' (the checks prove no vanilla hub and "
            "no 1-9 tile hub of 'SPECIAL MESSAGES' needs it).",
            "Draw order: backplate, tiles by rank, the previous selection, the selection last. "
            "A tile draws plate, face, icon, label.",
        ],
        ratio_by_s={s: ratio(s) for s in range(1, 9)},
        classes=CLASSES, secondary_roles=SEC_ROLES, line_pitch={r: line_pitch(r) for r in ("hero", "heading", "title",
                                                                 "label", "row", "body")},
        states=STATES,
        state_rules=[
            "Exactly one tile is 'sel'. Selection is colour + translate, no texture change.",
            "sel: face, icon and label take the sel colours; the lift joint translates by "
            "offset %s (unsheared; = (-5, -5) on screen); the plate appears at rest in gold_dk."
            % LIFT,
            "Colour tokens resolve per tile: on the main menu every tile takes the colours of "
            "the section it leads to; elsewhere the screen's section.",
            "The description strip (chrome) shows the selected tile's desc.",
        ],
        joints="per tile i: tile_<i> (slide, recoil) > plate_<i> (alpha) and lift_<i> (lift, "
               "scale about the tile centre) > face/icon/label; desc_<i> for the description",
        examples=ex,
        icon_textures="ico_<name>, 256x256 I4 (128 px at 1x); drawn at 24-96 px",
    )


# ================================================================ motion
def nav_motion():
    lx, ly = LIFT
    ev = {}
    ev["tile_select"] = dict(
        applies_to="the newly selected tile", sfx=[dict(frame=0, cue="sfx_cursor_move")],
        pivot="tile centre",
        tracks=[tr("lift_<id>", "TRA_X", k(0, 0, fc=True), k(4, lx * LIFT_PEAK), k(9, lx)),
                tr("lift_<id>", "TRA_Y", k(0, 0, fc=True), k(4, ly * LIFT_PEAK), k(9, ly)),
                tr("lift_<id>", "SCA_X", k(0, 1, fc=True), k(3, SCALE_PEAK), k(10, 1)),
                tr("lift_<id>", "SCA_Y", k(0, 1, fc=True), k(3, SCALE_PEAK), k(10, 1)),
                tr("face_<id>", "COLOUR", k(0, "@face", "LIN", fc=True), k(1, "gold_lt", "LIN"),
                   k(8, "gold", "LIN"), kind="material"),
                tr("icon_<id>", "COLOUR", k(0, "@face_hi", "CON", fc=True), k(1, "gold_dk", "CON"),
                   kind="material"),
                tr("label_<id>", "COLOUR", k(0, "bone", "CON", fc=True), k(1, "ink", "CON"),
                   kind="material"),
                tr("plate_<id>", "ALPHA", k(0, 1, "CON"), kind="material")])
    ev["tile_deselect"] = dict(
        applies_to="the previously selected tile", sfx=[],
        tracks=[tr("lift_<id>", "TRA_X", k(0, lx, fc=True), k(5, 0)),
                tr("lift_<id>", "TRA_Y", k(0, ly, fc=True), k(5, 0)),
                tr("lift_<id>", "SCA_X", k(0, 1, fc=True), k(5, 1)),
                tr("lift_<id>", "SCA_Y", k(0, 1, fc=True), k(5, 1)),
                tr("face_<id>", "COLOUR", k(0, "gold", "LIN", fc=True), k(2, "@face", "LIN"),
                   kind="material"),
                tr("icon_<id>", "COLOUR", k(0, "gold_dk", "CON", fc=True), k(2, "@face_hi", "CON"),
                   kind="material"),
                tr("label_<id>", "COLOUR", k(0, "ink", "CON", fc=True), k(2, "bone", "CON"),
                   kind="material"),
                tr("plate_<id>", "ALPHA", k(0, 1, "CON"), k(5, 0, "CON"), kind="material")])
    ev["tile_recoil"] = dict(
        applies_to="every other tile",
        note="value r scales the unit vector from the selected tile's pivot to this tile's "
             "pivot, times %g px (unsheared)" % RECOIL,
        tracks=[tr("tile_<id>", "RECOIL", k(0, 0), k(3, 1), k(10, 0))])
    ev["desc_in"] = dict(
        applies_to="the description strip text, for the new selection",
        tracks=[tr("desc_<id>", "ALPHA", k(0, 0, "LIN", fc=True), k(6, 1, "LIN"), kind="material"),
                tr("desc_<id>", "TRA_X", k(0, -12), k(6, 0))])
    ev["desc_out"] = dict(
        applies_to="the description strip text, for the previous selection",
        tracks=[tr("desc_<id>", "ALPHA", k(0, 1, "LIN", fc=True), k(3, 0, "LIN"),
                   kind="material")])
    ev["tile_confirm"] = dict(
        applies_to="the selected tile, on A", sfx=[dict(frame=3, cue="sfx_confirm")],
        tracks=[tr("lift_<id>", "TRA_X", k(0, lx, fc=True), k(3, 0), k(6, lx * 0.35), k(10, 0)),
                tr("lift_<id>", "TRA_Y", k(0, ly, fc=True), k(3, 0), k(6, ly * 0.35), k(10, 0)),
                tr("lift_<id>", "SCA_X", k(0, 1, fc=True), k(3, 0.97), k(10, 1)),
                tr("lift_<id>", "SCA_Y", k(0, 1, fc=True), k(3, 0.97), k(10, 1)),
                tr("face_<id>", "COLOUR", k(0, "gold", "LIN", fc=True), k(3, "bone", "LIN"),
                   k(12, "gold", "LIN"), kind="material")])
    ev["tile_slide_out"] = dict(
        applies_to="each tile; stagger 2 frames by rank, the chosen tile last; backplate with "
                   "the first", sfx=[dict(frame=0, cue="sfx_screen_whoosh")], offscreen=True,
        tracks=[tr("tile_<id>", "TRA_X", k(0, 0), k(12, -720, "SPL", -120))])
    ev["tile_slide_in"] = dict(
        applies_to="each tile by rank, starting at slide_in_offsets[rank]; backplate with the hero",
        sfx=[dict(frame=0, cue="sfx_screen_whoosh")], offscreen=True,
        tracks=[tr("tile_<id>", "TRA_X", k(0, 720, "SPL", -120), k(12, -6), k(17, 0))])
    ev["chrome_out"] = dict(
        applies_to="header up, footer and description down", offscreen=True,
        tracks=[tr("header", "TRA_Y", k(0, 0), k(10, -60)), tr("footer", "TRA_Y", k(0, 0),
                                                               k(10, 60))])
    ev["chrome_in"] = dict(
        applies_to="header and footer back", offscreen=True,
        tracks=[tr("header", "TRA_Y", k(0, -60), k(10, 0)), tr("footer", "TRA_Y", k(0, 60),
                                                                k(10, 0))])
    for e in ev.values():
        e["length_frames"] = 1 + max(kk["frame"] for t in e["tracks"] for kk in t["keys"])
    return dict(
        fps=60, format="hub_motion.json: tracks, from_current, interpolation and transform "
                       "rules unchanged; see out_hub/hub_motion.json",
        space="unsheared (the kit convention): joint transforms apply before the shear",
        converted_from="out_hub/hub_motion.json (screen space). The lift (-5, -5) on screen is "
                       "(-6.25, -5) unsheared; everything else is identical in value and timing.",
        value_expressions="colour values are kit tokens resolved per tile (see hubs_layout "
                          "state_rules)",
        events=ev,
        slide_in_offsets=[0, 3, 5, 7, 9, 11, 12, 13, 14],
        sequences=dict(
            cursor_move=[dict(event="tile_deselect", on="previous"),
                         dict(event="desc_out", on="previous"),
                         dict(event="tile_select", on="new"), dict(event="desc_in", on="new"),
                         dict(event="tile_recoil", on="others")],
            confirm=[dict(event="tile_confirm", on="selected"),
                     dict(sequence="screen_out", at=14)],
            screen_out=[dict(event="chrome_out"),
                        dict(event="tile_slide_out", order="by rank, selected last",
                             stagger_frames=2)],
            screen_in=[dict(event="chrome_in"),
                       dict(event="tile_slide_in", order="by rank", offsets="slide_in_offsets",
                            before_start="hold TRA_X at 720"),
                       dict(initial_state="the selected tile starts at its sel rest values")]))


# ================================================================ lists
LIST_SCREENS = {
    "multiman": dict(title="MULTI-MAN MELEE", section="solo",
                     crumbs=["SOLO", "STADIUM", "MULTI-MAN MELEE"], rows=[
                         ("10-Man Melee", "action", None, "KO ten fighters."),
                         ("100-Man Melee", "action", None, "KO one hundred fighters."),
                         ("3-Minute Melee", "action", None, "As many KOs as you can in three minutes."),
                         ("15-Minute Melee", "action", None, "Survive fifteen minutes."),
                         ("Endless Melee", "action", None, "Fight until you fall."),
                         ("Cruel Melee", "action", None, "Tough opponents. Good luck.")],
                     record=True),
    "special": dict(title="SPECIAL MELEE", section="versus", crumbs=["VERSUS", "SPECIAL MELEE"],
                    rows=[("Camera Mode", "action", None, "Take pictures during the match."),
                          ("Stamina Mode", "action", None, "Knock out an opponent's health."),
                          ("Super Sudden Death", "action", None, "Everyone starts at 300%."),
                          ("Giant Melee", "action", None, "Everyone is huge."),
                          ("Tiny Melee", "action", None, "Everyone is tiny."),
                          ("Invisible Melee", "action", None, "Now you see them..."),
                          ("Fixed-Camera Mode", "action", None, "The camera does not follow."),
                          ("Single-Button Mode", "action", None, "One attack button."),
                          ("Lightning Melee", "action", None, "Everything moves faster."),
                          ("Slo-Mo Melee", "action", None, "Everything moves slower.")]),
    "options": dict(title="OPTIONS", section="options", crumbs=["OPTIONS"], rows=[
        ("Rumble", "action", None, "Turn controller rumble on or off."),
        ("Sound", "choice", "Stereo", "Stereo or mono, music and effects balance."),
        ("Screen Display", "choice", "Deflicker Off", "Flicker filter."),
        ("Language", "choice", "English", "English or Japanese."),
        ("Erase Data", "danger", None, "Delete save data.")]),
    "rules": dict(title="RULES", section="versus", crumbs=["VERSUS", "RULES"], rows=[
        ("Mode", "choice", "Stock", "How a match is won."),
        ("Stocks", "stepper", "99", "Lives each player starts with."),
        ("Handicap", "choice", "Auto", "Auto evens out winners and losers."),
        ("Damage Ratio", "slider", "2.0x", "How far hits send fighters."),
        ("Stage Selection", "choice", "Random", "How the stage is chosen."),
        ("Items", "action", None, "Which items appear, and how often."),
        ("More Rules", "action", None, "Pause, score display, self-destructs and more.")]),
    "more_rules": dict(title="MORE RULES", section="versus", crumbs=["VERSUS", "RULES", "MORE RULES"],
                       rows=[("Stock Time Limit", "stepper", "99:00", "A clock for stock matches."),
                             ("Friendly Fire", "toggle", None, "Team attacks hit teammates."),
                             ("Pause", "toggle", None, "Allow pausing during the match."),
                             ("Score Display", "toggle", None, "Show scores during the match."),
                             ("Self-Destructs", "choice", "-2", "What falling off costs."),
                             ("Random Stage Select", "action", None, "Which stages Random picks."),
                             ("Launch Speed", "slider", "100%", "How fast launched fighters fly."),
                             ("Tournament Rules", "toggle", None, "Common tournament defaults.")]),
    "records": dict(title="RECORDS", section="data", crumbs=["DATA", "RECORDS"], rows=[
        ("VS. Records", "action", None, "Records from VS. matches."),
        ("Bonus Records", "action", None, "Bonuses you have earned."),
        ("Misc. Records", "action", None, "Everything else the game counts.")]),
}


def list_layout(lid):
    spec = LIST_SCREENS[lid]
    rows = []
    for label, w, val, help_ in spec["rows"]:
        lw = U.VALUE_X - U.ROW_X0 - 16 - 12 if w not in ("action", "danger") else \
            U.ROW_X1 - U.ROW_X0 - 32 - 24
        rows.append(dict(label=label, widget=w, value_max=val, help=help_,
                         label_slot=T("label", "row", (16, base_for("row", 0, U.ROW_H)), label,
                                      "bone", joint="row", max_width=lw)))
    return dict(name="list_%s" % lid, space="unsheared", template="list_layout.json",
                section=spec["section"],
                chrome=dict(title=spec["title"], crumbs=spec["crumbs"],
                            crumb_icon="ico_" + spec["section"]),
                rows=rows,
                row_variants=dict(
                    action=dict(note="does something on A; a gold chevron '→' in the value area "
                                     "right edge (atlas), aux colour"),
                    danger=dict(note="destructive (Erase Data): a 6 px danger stripe at the row's "
                                     "left edge, like the dialog's danger button; the label stays "
                                     "bone/ink - red text fails 4.5:1 on the faces",
                                quads=[Q("danger_stripe", (0, 0, 6, U.ROW_H), "danger",
                                         joint="row")]),
                    record=dict(note="Multi-Man: the best result, right-aligned in the value area "
                                     "(body, muted / ink when selected), e.g. '100 KOs' or "
                                     "'14:59.99'", slot=T("record", "body", (U.VALUE_W,
                                                                               cap("body") / 2),
                                                          "14:59.99", "aux", align="right")),
                    completed=dict(note="mark_completed (12 px) after the label when the mode "
                                        "is cleared; mark_new (burst + 'NEW' from strings) for "
                                        "newly unlocked items")),
                marks=dict(completed="mark_completed", locked="mark_locked", new="mark_new"))


# ================================================================ grid, table, event, sound test
GRID = dict(x0=104, y0=122, cell=[72, 64], pitch=[76, 68], cols=6, visible_rows=4,
            header_row=dict(rect=[U.ROW_X0, U.ROW_Y0, U.ROW_X1, U.ROW_Y0 + U.ROW_H],
                            note="Item Switch: the frequency choice row; Stage Switch: a "
                                 "page/count row ('24 of 80 on')"),
            track=[572, 122, 578, 390])


def grid_layout():
    x1 = GRID["x0"] + (GRID["cols"] - 1) * GRID["pitch"][0] + GRID["cell"][0]
    y1 = GRID["y0"] + (GRID["visible_rows"] - 1) * GRID["pitch"][1] + GRID["cell"][1]
    return dict(
        name="grid", space="unsheared", cell_template="widgets_layout.json check_cell",
        grid=dict(GRID, rect=[GRID["x0"], GRID["y0"], x1, y1]),
        rules=[
            "Cells run left to right, top to bottom: col = i %% %d, row = i // %d; cell top-left "
            "= (%d + col * %d, %d + (row - first_row) * %d)." % (GRID["cols"], GRID["cols"],
                                                                GRID["x0"], GRID["pitch"][0],
                                                                GRID["y0"], GRID["pitch"][1]),
            "%d rows show at a time (%d cells). More rows scroll by one row (kit scroll event, "
            "pitch %d), keeping the cursor one row from either edge; the kit scroll track sits "
            "at x %d." % (GRID["visible_rows"], GRID["visible_rows"] * GRID["cols"],
                          GRID["pitch"][1], GRID["track"][0]),
            "Any count fits: vanilla Item Switch is 31 cells (6 rows), m-ex Random Stage Switch "
            "up to 80+ (14 rows). The disc art is the cell's 64x56 slot.",
            "Footer: A toggle, X all on, Y all off, B back. The header row is a normal list row "
            "(its widget: choice for frequency).",
        ],
        max_counts=dict(item_switch=40, stage_switch=96))


TABLE = dict(x0=96, x1=540, header_y=84, header_h=22, row_h=26, pitch=28, visible=10,
             icon=24, name_w=150, num_w=64)


def table_layout():
    x0 = TABLE["x0"]
    return dict(
        name="table", space="unsheared",
        geometry=TABLE,
        quads=[Q("header", (x0, TABLE["header_y"], TABLE["x1"],
                            TABLE["header_y"] + TABLE["header_h"]), "ink"),
               Q("row_even", (x0, 0, TABLE["x1"], TABLE["row_h"]), "@face", joint="row"),
               Q("row_odd", (x0, 0, TABLE["x1"], TABLE["row_h"]), "@bg", joint="row"),
               Q("totals_rule", (x0, -3, TABLE["x1"], -1), "gold"),
               Q("sel_frame", (x0 - 2, -2, TABLE["x1"] + 2, TABLE["row_h"] + 2), "gold",
                 joint="row_sel")],
        columns=[
            dict(id="icon", kind="disc_art", size_1x=[24, 24], x=x0 + 8,
                 note="stock icon from the disc (per costume)"),
            dict(id="name", kind="text", role="body", x=x0 + 8 + 24 + 8, width=TABLE["name_w"],
                 max="Mr. Game & Watch Jr.", fit="body -> caption -> truncate"),
            dict(id="num_<i>", kind="text", role="body", align="right", width=TABLE["num_w"],
                 max="99999", header_role="caption", header_max="LOSSES",
                 x_rule="right edge of column i = x1 - 8 - (ncols - 1 - i) * %d" % TABLE["num_w"]),
        ],
        rules=[
            "Header row: ink, caption labels in gold (strings), numbers' headers right-aligned.",
            "Rows alternate @face / @bg; up to %d visible, then the kit scroll." % TABLE["visible"],
            "Numbers are body, tabular (the atlas's digits share one advance): a column never "
            "jitters.",
            "The selected row draws a 2 px gold frame (no lift - a table row is not a button).",
            "Totals row: the last row, with a gold rule above it and labels in bone Black ('row' "
            "role).",
            "Columns: up to 4 numeric columns of %d px fit beside a %d px name at 640x480." %
            (TABLE["num_w"], TABLE["name_w"]),
        ])


EVENT = dict(list_x0=96, list_x1=318, detail=[330, 84, 556, 390], number_w=30)


def event_layout():
    lx0, lx1 = EVENT["list_x0"], EVENT["list_x1"]
    dx0, dy0, dx1, dy1 = EVENT["detail"]
    return dict(
        name="event", space="unsheared", list_template="list_layout.json rows, narrowed",
        list=dict(x0=lx0, x1=lx1, rows_top=U.ROW_Y0, pitch=U.PITCH, row_h=U.ROW_H, visible=9),
        row=dict(
            slots=[T("number", "row", (12, base_for("row", 0, U.ROW_H)), "51", "muted",
                     note="tabular; ink on sel"),
                   T("name", "body", (12 + EVENT["number_w"], base_for("body", 0, U.ROW_H)),
                     "Trouble King 2: Return", "bone",
                     max_width=lx1 - lx0 - 12 - EVENT["number_w"] - 24),
                   dict(id="completed", kind="mark", texture="mark_completed", size=[12, 12],
                        x=lx1 - lx0 - 18)]),
        detail=dict(
            rect=[dx0, dy0, dx1, dy1],
            quads=[Q("panel", (dx0, dy0, dx1, dy1), "ink"),
                   Q("title_slab", (dx0, dy0, dx1, dy0 + 28), "gold")],
            slots=[T("title", "label", (dx0 + 10, base_for("label", dy0, dy0 + 28)),
                     "TROUBLE KING 2: RETURN", "ink", max_width=dx1 - dx0 - 20,
                     note="fit rule; caps from strings"),
                   dict(id="art", kind="disc_art", rect=[dx0 + 10, dy0 + 38, dx1 - 10, dy0 + 138],
                        note="the event's disc image if the disc has one; a 9-slice frame the "
                             "engine sizes; hidden (and the text moves up) if none"),
                   dict(id="paragraph", kind="text_block", role="body", x=dx0 + 10,
                        top=dy0 + 158, width=dx1 - dx0 - 20, max_lines=7,
                        line_pitch=ROLES["body"]["metrics"]["line_height"],
                        wrap="break at spaces; beyond max_lines, truncate the last line with '…'"),
                   T("best_label", "caption", (dx0 + 10, dy1 - 10), "BEST", "muted"),
                   T("best", "row", (dx1 - 10, dy1 - 10), "99:59.99", "bone", align="right")]),
        rules=["The list is the kit row template, 222 px wide; the detail panel follows the "
               "selection (no motion beyond a 4-frame text fade).",
               "Locked events show mark_locked in place of the number and '???' from strings."])


def soundtest_layout():
    return dict(
        name="soundtest", space="unsheared", template="list_layout.json rows",
        row=dict(
            slots=[T("track_no", "row", (16, base_for("row", 0, U.ROW_H)), "99", "muted"),
                   T("title", "row", (52, base_for("row", 0, U.ROW_H)),
                     "Princess Peach's Castle", "bone",
                     max_width=U.ROW_X1 - U.ROW_X0 - 52 - 60, note="fit rule")],
            playing=dict(quads=[Q("eq_%d" % i, (U.ROW_X1 - U.ROW_X0 - 44 + i * 9, 8,
                                                U.ROW_X1 - U.ROW_X0 - 38 + i * 9, U.ROW_H - 8),
                                  "gold", joint="eq_%d" % i) for i in range(3)],
                         note="three bars at the row's right; only on the playing track; "
                              "soundtest_playing loop scales them on Y about their bottom edge")),
        motion=dict(soundtest_playing=dict(
            loop=dict(from_frame=0, to_frame=48),
            tracks=[tr("eq_%d" % i, "SCA_Y", k(0, 0.3 + 0.2 * i), k(8 + 4 * i, 1.0),
                       k(20 + 3 * i, 0.4), k(34, 0.85 - 0.15 * i), k(48, 0.3 + 0.2 * i))
                    for i in range(3)])),
        rules=["The playing track's number turns gold and the bars show, in any row state; on "
               "a selected (gold) row the bars are ink."])


# ================================================================ drawing
class Scene(U.Scene):
    pass


def tok(sc, t, section):
    if t is None:
        return None
    if t.startswith("@"):
        return kit.SECTIONS[section][t[1:]]
    return sc.col(t)


def draw_hub(sc, lay, sel_rank=0, crumb=True):
    chrome = U.chrome()
    tiles = lay["tiles"]
    sel = tiles[sel_rank]
    sc.crumb_icon = lay["chrome"]["crumb_icon"]
    if lay["chrome"]["crumb_icon"] is None:
        sc.crumb_icon = "__none__"
    sc.footer_end = U.draw_chrome(sc, chrome, lay["chrome"]["title"], lay["chrome"]["crumbs"],
                                  [("a", "Select"), ("b", "Back")], sel["desc"])
    bp = lay["cluster"]["backplate"]["verts"]
    sc.quad(bp[0] + bp[2], "ink", joint="cluster")
    order = [t for t in tiles if t is not sel] + [sel]
    for t in order:
        st = STATES["sel" if t is sel else "ng"]
        sec = t["section"]
        dx, dy = st["offset"]
        x0, y0, x1, y1 = t["rect_unsheared"]
        j = "lift_%s" % t["id"]
        if st["plate"]:
            sc.quad((x0, y0, x1, y1), tok(sc, st["plate"], sec), joint="plate")
        sc.quad((x0 + dx, y0 + dy, x1 + dx, y1 + dy), tok(sc, st["face"], sec), joint=j)
        ix0, iy0, ix1, iy1 = t["_L"]["icon"]
        sc.quad((ix0 + dx, iy0 + dy, ix1 + dx, iy1 + dy), tok(sc, st["icon"], sec),
                tex=t["quads"][2]["texture"], joint=j)
        L = t["_L"]
        for line, b in zip(L["lines"], L["bases"]):
            sc.text(L["role"], line, L["x"] + dx, b + dy, tok(sc, st["label"], sec), joint=j)


def draw_list(sc, lid, sel=0, first=0):
    spec = LIST_SCREENS[lid]
    rows = spec["rows"]
    selrow = rows[sel]
    sc.footer_end = U.draw_chrome(sc, U.chrome(), spec["title"], spec["crumbs"],
                                  [("a", "Select"), ("b", "Back")], selrow[3])
    shown = list(enumerate(rows))[first:first + U.VISIBLE]
    later = []
    for slot, (i, r) in enumerate(shown):
        if i == sel:
            later.append((slot, r))
            continue
        draw_list_row(sc, slot, r, "ng", spec)
    for slot, r in later:
        draw_list_row(sc, slot, r, "sel", spec)
    if len(rows) > U.VISIBLE:
        U.draw_scroll(sc, first, U.VISIBLE, len(rows))


VALUES = {"choice": lambda v: (v, True, True), "stepper": lambda v: v,
          "slider": lambda v: (0.5, v), "toggle": lambda v: True}


def draw_list_row(sc, slot, r, state, spec):
    label, w, val, _ = r
    y = U.ROW_Y0 + slot * U.PITCH
    st = U.ROW_T["states"][state]
    dx, dy = st["offset"]
    if st["plate"]:
        sc.quad((U.ROW_X0, y, U.ROW_X1, y + U.ROW_H), st["plate"], joint="row_plate")
    sc.quad((U.ROW_X0 + dx, y + dy, U.ROW_X1 + dx, y + U.ROW_H + dy), st["face"], joint="row")
    if w == "danger":
        sc.quad((U.ROW_X0 + dx, y + dy, U.ROW_X0 + 6 + dx, y + U.ROW_H + dy), "danger", joint="row")
    sc.text("row", label, U.ROW_X0 + 16 + dx, y + base_for("row", 0, U.ROW_H) + dy, st["label"],
            joint="row")
    wc = U.WID["colours"][state]
    cy = y + U.ROW_H / 2 + dy
    if w in ("action", "danger"):
        if spec.get("record"):
            sc.text("body", "14:59.99", U.VALUE_X + U.VALUE_W - 22 + dx, cy + cap("body") / 2,
                    wc["aux"], align="right", joint="row")
        sc.text("row", "→", U.VALUE_X + U.VALUE_W + dx, cy + cap("row") / 2, wc["aux"],
                align="right", joint="row")
    else:
        U.draw_widget(sc, w, U.VALUE_X + dx, cy, state, VALUES[w](val))


def draw_grid(sc, count, first_row, sel, title, crumbs, header):
    sc.footer_end = U.draw_chrome(sc, U.chrome(), title, crumbs,
                                  [("a", "Toggle"), ("x", "All On"), ("y", "All Off"),
                                   ("b", "Back")], "Choose which %s can appear." % header[2])
    # header row (list row, ng)
    draw_list_row(sc, 0, (header[0], header[1], header[3][0], ""), "ng", {})
    cw, chh = GRID["cell"]
    px, py = GRID["pitch"]
    total_rows = math.ceil(count / GRID["cols"])
    later = None
    for i in range(first_row * GRID["cols"], min(count, (first_row + GRID["visible_rows"]) *
                                                 GRID["cols"])):
        col, row = i % GRID["cols"], i // GRID["cols"] - first_row
        x, y = GRID["x0"] + col * px, GRID["y0"] + row * py
        if i == sel:
            later = (i, x, y)
            continue
        draw_cell(sc, x, y, i % 4 != 1, False)
    if later:
        draw_cell(sc, later[1], later[2], later[0] % 4 != 1, True)
    x0, y0, x1, y1 = GRID["track"]
    h = y1 - y0
    th = max(16, h * GRID["visible_rows"] / total_rows)
    ty = y0 + (h - th) * first_row / max(1, total_rows - GRID["visible_rows"])
    sc.quad(GRID["track"], "ink")
    sc.quad((x0, ty, x1, ty + th), "@face_hi", joint="thumb")


def draw_cell(sc, x, y, on, sel):
    dx, dy = U.LIFT if sel else (0, 0)
    if sel:
        sc.quad((x, y, x + 72, y + 64), "gold_dk", joint="cell_plate")
    sc.quad((x + dx, y + dy, x + 72 + dx, y + 64 + dy), "ink", joint="cell")
    sc.quad((x + 3 + dx, y + 3 + dy, x + 69 + dx, y + 61 + dy), "gold" if sel else "@face",
            joint="cell")
    sc.quad((x + 4 + dx, y + 4 + dy, x + 68 + dx, y + 60 + dy), "@face_hi" if on else "#8a8a8a",
            opacity=0.9 if on else 0.45, joint="cell")
    sc.text("caption", "64×56", x + 36 + dx, y + 36 + dy, "ink", align="centre", joint="cell")
    sc.quad((x + 50 + dx, y + dy, x + 72 + dx, y + 16 + dy), "gold" if on else "ink",
            joint="cell_tab")
    if on:
        sc.quad((x + 54 + dx, y + 1 + dy, x + 68 + dx, y + 15 + dy), "ink", tex="glyph_check",
                joint="cell_tab")


def draw_table(sc):
    sc.footer_end = U.draw_chrome(sc, U.chrome(), "VS. RECORDS", ["DATA", "RECORDS", "VS. RECORDS"],
                                  [("a", "Details"), ("l", "Sort"), ("b", "Back")],
                                  "Wins, KOs and falls for every fighter.")
    x0, x1 = TABLE["x0"], TABLE["x1"]
    hy = TABLE["header_y"]
    heads = ["WINS", "LOSSES", "KOS", "FALLS"]
    sc.quad((x0, hy, x1, hy + TABLE["header_h"]), "ink")
    sc.text("caption", "FIGHTER", x0 + 40, base_for("caption", hy, hy + TABLE["header_h"]), "gold")
    for c, hname in enumerate(heads):
        rx = x1 - 8 - (len(heads) - 1 - c) * TABLE["num_w"]
        sc.text("caption", hname, rx, base_for("caption", hy, hy + TABLE["header_h"]), "gold",
                align="right")
    names = ["Mr. Game & Watch Jr.", "Captain Falcon", "Ice Climbers", "Princess Daisy (SSB)",
             "Young Link", "Jigglypuff", "Ganondorf", "Dr. Mario", "Wario Man, Microgame"]
    y = hy + TABLE["header_h"] + 4
    for i, n in enumerate(names):
        face = "@face" if i % 2 == 0 else "@bg"
        sc.quad((x0, y, x1, y + TABLE["row_h"]), face, joint="row")
        if i == 2:
            for (a, b, c, d) in ((x0 - 2, y - 2, x1 + 2, y), (x0 - 2, y + TABLE["row_h"], x1 + 2,
                                                               y + TABLE["row_h"] + 2),
                                 (x0 - 2, y, x0, y + TABLE["row_h"]),
                                 (x1, y, x1 + 2, y + TABLE["row_h"])):
                sc.quad((a, b, c, d), "gold", joint="row_sel")
        sc.quad((x0 + 8, y + 1, x0 + 32, y + 25), "@face_hi", opacity=0.5, joint="row")
        r, s = fit1("body", n, TABLE["name_w"])
        sc.text(r, s, x0 + 40, base_for(r, y, y + TABLE["row_h"]), "bone")
        for c in range(len(heads)):
            rx = x1 - 8 - (len(heads) - 1 - c) * TABLE["num_w"]
            sc.text("body", "%d" % [99999, 4821, 1375, 88][c], rx,
                    base_for("body", y, y + TABLE["row_h"]), "bone", align="right")
        y += TABLE["pitch"]
    sc.quad((x0, y - 3, x1, y - 1), "gold")
    sc.quad((x0, y, x1, y + TABLE["row_h"]), "ink")
    sc.text("row", "Total", x0 + 40, base_for("row", y, y + TABLE["row_h"]), "bone")
    for c in range(len(heads)):
        rx = x1 - 8 - (len(heads) - 1 - c) * TABLE["num_w"]
        sc.text("row", "%d" % [99999, 99999, 12375, 792][c], rx,
                base_for("row", y, y + TABLE["row_h"]), "bone", align="right")
    sc.table_bottom = y + TABLE["row_h"]


def wrap(role, text, width):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_w(role, t) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def draw_event(sc):
    sc.footer_end = U.draw_chrome(sc, U.chrome(), "EVENT MATCH", ["SOLO", "EVENT MATCH"],
                                  [("a", "Start"), ("b", "Back")],
                                  "Special battles with their own rules.")
    lx0, lx1 = EVENT["list_x0"], EVENT["list_x1"]
    names = [("1", "Trouble King"), ("2", "Lord of the Jungle"), ("3", "Bomb-fest"),
             ("4", "Trouble King 2: Return"), ("5", "Cold Armor"), ("6", "Hide 'n' Sheik"),
             ("7", "All-Star Match Deluxe"), ("8", "???"), ("51", "The Showdown at the End")]
    sel = 3
    for i, (num, name) in enumerate(names):
        if i == sel:
            continue
        ev_row(sc, i, num, name, "ng", done=i < 5, locked=name == "???")
    ev_row(sc, sel, *names[sel], "sel", done=True)
    dx0, dy0, dx1, dy1 = EVENT["detail"]
    sc.quad((dx0, dy0, dx1, dy1), "ink")
    sc.quad((dx0, dy0, dx1, dy0 + 28), "gold")
    r, s = fit1("label", "TROUBLE KING 2: RETURN", dx1 - dx0 - 20)
    sc.text(r, s, dx0 + 10, base_for(r, dy0, dy0 + 28), "ink")
    sc.quad((dx0 + 10, dy0 + 38, dx1 - 10, dy0 + 138), "@face", opacity=0.6)
    sc.text("caption", "DISC IMAGE (if any)", (dx0 + dx1) / 2, dy0 + 92, "muted", align="centre")
    para = ("Three giants stand between you and the exit, and each one is tougher than the last. "
            "Items are off, the clock is short, and your stock is a single life, so play safe "
            "and punish every mistake you see them make on the way down.")
    lines = wrap("body", para, dx1 - dx0 - 20)
    lp = ROLES["body"]["metrics"]["line_height"]
    maxl = 7
    if len(lines) > maxl:
        lines = lines[:maxl]
        lines[-1] = fit1("body", lines[-1] + " …", dx1 - dx0 - 20)[1]
    for i, ln in enumerate(lines):
        sc.text("body", ln, dx0 + 10, dy0 + 158 + i * lp, "bone")
    sc.text("caption", "BEST", dx0 + 10, dy1 - 10, "muted")
    sc.text("row", "99:59.99", dx1 - 10, dy1 - 10, "bone", align="right")
    sc.event_para_bottom = dy0 + 158 + (len(lines) - 1) * lp


def ev_row(sc, i, num, name, state, done=False, locked=False):
    lx0, lx1 = EVENT["list_x0"], EVENT["list_x1"]
    y = U.ROW_Y0 + i * U.PITCH
    st = U.ROW_T["states"][state]
    dx, dy = st["offset"]
    if st["plate"]:
        sc.quad((lx0, y, lx1, y + U.ROW_H), st["plate"], joint="row_plate")
    sc.quad((lx0 + dx, y + dy, lx1 + dx, y + U.ROW_H + dy), st["face"], joint="row")
    wc = U.WID["colours"][state]
    if locked:
        sc.quad((lx0 + 12 + dx, y + 9 + dy, lx0 + 24 + dx, y + 21 + dy), wc["aux"],
                tex="mark_locked", joint="row")
    else:
        sc.text("row", num, lx0 + 12 + dx, y + base_for("row", 0, U.ROW_H) + dy, wc["aux"],
                joint="row")
    width = lx1 - lx0 - 12 - EVENT["number_w"] - 24
    r, s = fit1("body", name, width)
    sc.text(r, s, lx0 + 12 + EVENT["number_w"] + dx, y + base_for(r, 0, U.ROW_H) + dy, st["label"],
            joint="row")
    if done:
        sc.quad((lx1 - 18 + dx, y + 9 + dy, lx1 - 6 + dx, y + 21 + dy),
                "ok" if state != "sel" else "ink", tex="mark_completed", joint="row")


def draw_soundtest(sc):
    sc.footer_end = U.draw_chrome(sc, U.chrome(), "SOUND TEST", ["DATA", "SOUND TEST"],
                                  [("a", "Play"), ("x", "Stop"), ("b", "Back")],
                                  "Listen to music, effects and voices.")
    tracks = ["Opening", "Menu 1", "Menu 2", "Princess Peach's Castle", "Rainbow Cruise",
              "Kongo Jungle", "Jungle Japes", "Great Bay", "Temple"]
    playing, sel = 3, 5
    for i, t in enumerate(tracks):
        if i != sel:
            st_row(sc, i, i + 1, t, "ng", i == playing)
    st_row(sc, sel, sel + 1, tracks[sel], "sel", sel == playing)
    U.draw_scroll(sc, 0, U.VISIBLE, 60)


def st_row(sc, i, num, title, state, playing):
    y = U.ROW_Y0 + i * U.PITCH
    st = U.ROW_T["states"][state]
    dx, dy = st["offset"]
    if st["plate"]:
        sc.quad((U.ROW_X0, y, U.ROW_X1, y + U.ROW_H), st["plate"], joint="row_plate")
    sc.quad((U.ROW_X0 + dx, y + dy, U.ROW_X1 + dx, y + U.ROW_H + dy), st["face"], joint="row")
    wc = U.WID["colours"][state]
    sc.text("row", "%d" % num, U.ROW_X0 + 16 + dx, y + base_for("row", 0, U.ROW_H) + dy,
            "gold" if playing and state != "sel" else wc["aux"], joint="row")
    r, s = fit1("row", title, U.ROW_X1 - U.ROW_X0 - 52 - 60)
    sc.text(r, s, U.ROW_X0 + 52 + dx, y + base_for(r, 0, U.ROW_H) + dy, st["label"], joint="row")
    if playing:
        for n, hfrac in enumerate((0.55, 1.0, 0.7)):
            bx = U.ROW_X1 - 44 + n * 9 + dx
            hh = (U.ROW_H - 16) * hfrac
            sc.quad((bx, y + U.ROW_H - 8 - hh + dy, bx + 6, y + U.ROW_H - 8 + dy),
                    "ink" if state == "sel" else "gold", joint="eq_%d" % n)


# ================================================================ checks
def shear_pt(x, y):
    return (x + (Y0 - y) * S, y)


def check_hub(hid, lay):
    errs = []
    sx0, sy0, sx1, sy1 = SAFE
    bp = lay["cluster"]["backplate"]["verts"]
    for vx, vy in bp:
        px, py = shear_pt(vx, vy)
        if not (sx0 <= px <= sx1 and sy0 <= py <= sy1):
            errs.append("%s: backplate leaves title-safe at (%.1f, %.1f)" % (hid, px, py))
            break
    for t in lay["tiles"]:
        x0, y0, x1, y1 = t["rect_unsheared"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        bad = False
        for vx, vy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            for (dx, dy, s) in ((LIFT[0] * LIFT_PEAK, LIFT[1] * LIFT_PEAK, SCALE_PEAK),
                                (RECOIL, RECOIL, 1.0), (-RECOIL, -RECOIL, 1.0),
                                (RECOIL, -RECOIL, 1.0), (-RECOIL, RECOIL, 1.0)):
                px, py = shear_pt(cx + (vx - cx) * s + dx, cy + (vy - cy) * s + dy)
                if not (sx0 - 1e-6 <= px <= sx1 + 1e-6 and sy0 - 1e-6 <= py <= sy1 + 1e-6):
                    errs.append("%s/%s leaves title-safe at peak motion (%.1f, %.1f)"
                                % (hid, t["id"], px, py))
                    bad = True
                    break
            if bad:
                break
        L = t["_L"]
        if L["truncated"]:
            errs.append("%s/%s: label '%s' truncates" % (hid, t["id"], t["label"]))
        # label block inside the tile, clear of the icon
        lx0 = L["x"]
        lx1 = lx0 + max(text_w(L["role"], ln) for ln in L["lines"])
        ly0 = L["bases"][0] - cap(L["role"])
        ly1 = L["bases"][-1]
        ix0, iy0, ix1, iy1 = L["icon"]
        if lx0 < ix1 and ix0 < lx1 and ly0 < iy1 and iy0 < ly1:
            errs.append("%s/%s: label overlaps icon" % (hid, t["id"]))
        if lx0 < x0 or lx1 > x1 or ly0 < y0 or ly1 > y1:
            errs.append("%s/%s: label spills out of its tile" % (hid, t["id"]))
        if ix0 < x0 or ix1 > x1 or iy0 < y0 or iy1 > y1:
            errs.append("%s/%s: icon spills out of its tile" % (hid, t["id"]))
        if not os.path.exists(os.path.join(OUT, "2x", t["quads"][2]["texture"] + ".png")):
            errs.append("%s/%s: icon %s missing" % (hid, t["id"], t["quads"][2]["texture"]))
    # contrast per tile section: label and icon on face, both states
    for t in lay["tiles"]:
        sec = t["section"]
        sc = Scene(sec)
        for st, lab_need, ic_need in (("ng", kit.MIN_TEXT, kit.MIN_GRAPHIC),
                                      ("sel", kit.MIN_TEXT, 2.0)):
            s_ = STATES[st]
            f = K.hexrgb(tok(sc, s_["face"], sec))
            c1 = K.contrast(K.hexrgb(tok(sc, s_["label"], sec)), f)
            c2 = K.contrast(K.hexrgb(tok(sc, s_["icon"], sec)), f)
            if c1 < lab_need:
                errs.append("%s/%s %s: label contrast %.2f" % (hid, t["id"], st, c1))
            if c2 < ic_need:
                errs.append("%s/%s %s: icon contrast %.2f" % (hid, t["id"], st, c2))
    return errs


def check_lists():
    errs = []
    for lid, spec in LIST_SCREENS.items():
        lay = list_layout(lid)
        for r in lay["rows"]:
            s = r["label_slot"]
            if text_w("row", s["max"]) > s["max_width_1x"]:
                errs.append("list %s: '%s' needs %.1f > %.1f" % (lid, s["max"],
                                                                  text_w("row", s["max"]),
                                                                  s["max_width_1x"]))
            if r["widget"] == "choice":
                width = U.VALUE_W - 2 * (text_w("row", "←") + 8)
                if text_w("row", r["value_max"]) > width:
                    errs.append("list %s: value '%s' too wide" % (lid, r["value_max"]))
        if len(spec["rows"]) > U.VISIBLE and lid not in ("special",):
            errs.append("list %s: %d rows > %d visible and no scroll preview"
                        % (lid, len(spec["rows"]), U.VISIBLE))
    return errs


def check_grid():
    errs = []
    g = grid_layout()["grid"]
    x0, y0, x1, y1 = g["rect"]
    sx0, sy0, sx1, sy1 = SAFE
    for vx, vy in ((x0 + U.LIFT[0] * 1.3, y0 + U.LIFT[1] * 1.3), (x1, y0), (x1, y1), (x0, y1)):
        px, py = shear_pt(vx, vy)
        if not (sx0 <= px <= sx1 and sy0 <= py <= sy1):
            errs.append("grid leaves title-safe at (%.1f, %.1f)" % (px, py))
    tx0, ty0, tx1, ty1 = g["track"]
    for vx, vy in ((tx1, ty0), (tx0, ty1)):
        px, py = shear_pt(vx, vy)
        if not (sx0 <= px <= sx1):
            errs.append("grid track leaves title-safe at (%.1f, %.1f)" % (px, py))
    if y1 > U.DESC[1] - 4:
        errs.append("grid runs into the description strip (%d > %d)" % (y1, U.DESC[1] - 4))
    if x1 >= tx0 - 4:
        errs.append("grid touches its scroll track")
    return errs


def check_table(sc):
    errs = []
    if sc.table_bottom > U.DESC[1] - 4:
        errs.append("table runs into the description strip (%.1f)" % sc.table_bottom)
    name_x1 = TABLE["x0"] + 40 + TABLE["name_w"]
    first_num_x0 = TABLE["x1"] - 8 - 3 * TABLE["num_w"] - TABLE["num_w"] + 4
    if name_x1 > first_num_x0 + 8:
        errs.append("table name column overlaps the numbers (%.1f > %.1f)" % (name_x1,
                                                                             first_num_x0))
    for h in ("LOSSES", "99999"):
        if text_w("caption" if h[0].isalpha() else "body", h) > TABLE["num_w"] - 8:
            errs.append("table: '%s' wider than its column" % h)
    for n in kit.NAME_FIT["test_names"]:
        r, s = fit1("body", n, TABLE["name_w"])
        if s != n:
            errs.append("table: name '%s' truncates" % n)
    return errs


def check_event(sc):
    errs = []
    dy1 = EVENT["detail"][3]
    if sc.event_para_bottom > dy1 - 30:
        errs.append("event paragraph runs into BEST (%.1f > %.1f)" % (sc.event_para_bottom,
                                                                      dy1 - 30))
    return errs


# ================================================================ main
def memory(sc):
    names = {it["tex"] for it in sc.items if it["tex"]}
    total = 0
    for n in names:
        w, h = Image.open(U.tex_path(n)).size
        total += w * h // 2
    return total, sorted(names)


def strip_private(lay):
    out = json.loads(json.dumps(lay, default=str))
    for t in out.get("tiles", []):
        t.pop("_L", None)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
    U.WID, U.DLG, U.CUR = U.widgets(), U.dialog(), U.cursor_layout()
    U.ROW_T = U.list_layout()["templates"][0]
    icons = json.load(open(os.path.join(OUT, "icons_manifest.json"), encoding="utf-8"))
    icon_rows = {t["name"]: t for t in icons["textures"]}
    errs = []

    # ---- hubs
    hubs = {hid: build_hub(hid) for hid in HUBS}
    for hid, lay in hubs.items():
        errs += check_hub(hid, lay)
        used = sorted({t["quads"][2]["texture"] for t in lay["tiles"]} |
                      ({lay["chrome"]["crumb_icon"]} if lay["chrome"]["crumb_icon"] else set()))
        lay["textures"] = [dict(name=n, file_2x=icon_rows[n]["file_2x"],
                                file_1x=icon_rows[n]["file_1x"], size_2x=icon_rows[n]["size_2x"],
                                format="I4", fallback="IA4") for n in used]
    # the rule, exercised for every n with the worst labels in every slot
    worst = "SPECIAL MESSAGES"
    rule_hubs = {}
    for n in range(1, 10):
        items = [("t%d" % i, worst, "ico_messages", "x") for i in range(n)]
        lay = build_hub("rule%d" % n, dict(title="HUB %d" % n, section="versus",
                                           crumbs=["VERSUS"], items=items))
        rule_hubs[n] = lay
        errs += check_hub("rule n=%d" % n, lay)
    rule = hubs_rule()
    rule["label_results"] = {
        hid: {t["id"]: dict(cls=t["size_class"], role=t["_L"]["role"], lines=t["_L"]["lines"])
              for t in lay["tiles"]} for hid, lay in hubs.items()}
    rule["worst_label_by_n"] = {n: [dict(cls=t["size_class"], role=t["_L"]["role"],
                                         lines=t["_L"]["lines"]) for t in lay["tiles"]]
                                for n, lay in rule_hubs.items()}

    mot = nav_motion()
    errs += check_lists()
    errs += check_grid()

    # ---- write layouts
    with open(os.path.join(OUT, "hubs_layout.json"), "w", encoding="utf-8") as fh:
        json.dump(rule, fh, indent=1, ensure_ascii=False)
    for hid, lay in hubs.items():
        with open(os.path.join(OUT, "hub_%s_layout.json" % hid), "w", encoding="utf-8") as fh:
            json.dump(strip_private(lay), fh, indent=1, ensure_ascii=False)
    with open(os.path.join(OUT, "nav_motion.json"), "w", encoding="utf-8") as fh:
        json.dump(mot, fh, indent=1, ensure_ascii=False)
    for lid in LIST_SCREENS:
        with open(os.path.join(OUT, "list_%s_layout.json" % lid), "w", encoding="utf-8") as fh:
            json.dump(list_layout(lid), fh, indent=1, ensure_ascii=False)
    for name, fn in (("grid", grid_layout), ("table", table_layout), ("event", event_layout),
                     ("soundtest", soundtest_layout)):
        lay = fn()
        if name in ("event",):
            lay["textures"] = [dict(name=n, file_2x=icon_rows[n]["file_2x"],
                                    file_1x=icon_rows[n]["file_1x"],
                                    size_2x=icon_rows[n]["size_2x"], format="I4", fallback="IA4")
                               for n in ("mark_completed", "mark_locked")]
        with open(os.path.join(OUT, "%s_layout.json" % name), "w", encoding="utf-8") as fh:
            json.dump(lay, fh, indent=1, ensure_ascii=False)

    # ---- previews
    scenes = {}
    for hid, lay in hubs.items():
        sc = Scene(lay["section"] if lay["section"] in kit.SECTIONS else "versus")
        draw_hub(sc, lay, 0)
        scenes["hub_%s" % hid] = sc
    # the versus hub with Online selected, and the data hub on its smallest tile
    sc = Scene("versus")
    draw_hub(sc, hubs["versus"], 1)
    scenes["hub_versus_online"] = sc
    sc = Scene("data")
    draw_hub(sc, hubs["data"], 4)
    scenes["hub_data_last"] = sc
    sc = Scene("versus")
    draw_hub(sc, rule_hubs[9], 8)
    scenes["hub_rule_n9"] = sc
    for lid, sel, first in (("rules", 3, 0), ("options", 4, 0), ("special", 9, 1),
                            ("multiman", 1, 0), ("more_rules", 6, 0)):
        spec = LIST_SCREENS[lid]
        sc = Scene(spec["section"])
        draw_list(sc, lid, sel, first)
        scenes["list_%s" % lid] = sc
    sc = Scene("versus")
    draw_grid(sc, 31, 1, 16, "ITEM SWITCH", ["VERSUS", "RULES", "ITEM SWITCH"],
              ("Item Frequency", "choice", "items", ("Very High", True, False)))
    scenes["grid_items"] = sc
    sc = Scene("versus")
    draw_grid(sc, 96, 12, 80, "RANDOM STAGE SWITCH", ["VERSUS", "MORE RULES", "STAGES"],
              ("Stages On", "choice", "stages", ("80 of 96", True, True)))
    scenes["grid_stages"] = sc
    sc = Scene("data")
    draw_table(sc)
    scenes["table_records"] = sc
    errs += check_table(sc)
    sc = Scene("solo")
    draw_event(sc)
    scenes["event_match"] = sc
    errs += check_event(sc)
    sc = Scene("data")
    draw_soundtest(sc)
    scenes["sound_test"] = sc

    # kit-level per-scene checks: footers, title-safe with kit row/cell motion
    kitmot = U.motion()
    errs_k, _ = U.check({n: s for n, s in scenes.items() if not n.startswith("hub")},
                        kitmot, dict(widgets=U.WID))
    errs += errs_k

    mem = {}
    for n, sc in scenes.items():
        b, names = memory(sc)
        mem[n] = dict(bytes_2x=b, textures=names)
        if b > U.BUDGET:
            errs.append("%s uses %.0f KB > 1 MB" % (n, b / 1024))

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(
            provenance="Original. Icons drawn in pipeline/icons.py; layouts and motion from "
                       "pipeline/nav.py; nothing traced, sampled or recoloured from Melee.",
            convert="python pc/tools/png2gx.py --layout <menu>/out_nav/manifest.json --outdir "
                    "_build/ui   (all section-2 icons and marks)",
            retired=["lbl_title", "lbl_versus", "lbl_solo", "lbl_collection", "lbl_options",
                     "desc_versus", "desc_solo", "desc_collection", "desc_options"],
            textures=[dict(t, why=t["why"]) for t in icons["textures"]],
            memory_2x_per_screen={n: round(m["bytes_2x"] / 1024, 1) for n, m in mem.items()}),
            fh, indent=1, ensure_ascii=False)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(device_scale_factor=1)
        tx = U.Textures()
        for name, sc in scenes.items():
            img = U.render(page, sc, tx)
            img.save(os.path.join(OUT, "preview", "%s_2x.png" % name))
            downscale_half(img.convert("RGBA")).convert("RGB").save(
                os.path.join(OUT, "preview", "%s_1x.png" % name))
        # the rule sheet: n = 2..9 at quarter size
        sheet = Image.new("RGB", (4 * 320, 2 * 240), (0, 0, 0))
        for i, n in enumerate(range(2, 10)):
            sc = Scene("versus")
            names = ["MELEE", "ONLINE", "TOURNAMENT", "SPECIAL MELEE", "RULES", "NAME ENTRY",
                     "HOME-RUN CONTEST", "SPECIAL MESSAGES", "MULTI-MAN MELEE"]
            items = [("t%d" % j, names[j], "ico_" + ["melee", "online", "tournament", "special",
                                                     "rules", "names", "homerun", "messages",
                                                     "multiman"][j], "Tile %d" % (j + 1))
                     for j in range(n)]
            lay = build_hub("n%d" % n, dict(title="%d TILES" % n, section="versus",
                                            crumbs=["RULE"], items=items))
            errs += check_hub("sheet n=%d" % n, lay)
            draw_hub(sc, lay, 0)
            img = U.render(page, sc, tx).resize((320, 240), Image.LANCZOS)
            sheet.paste(img, ((i % 4) * 320, (i // 4) * 240))
        sheet.save(os.path.join(OUT, "preview", "hub_rule_sheet.png"))
        browser.close()

    print("hubs: %s" % ", ".join("%s(%d)" % (h, len(l["tiles"])) for h, l in hubs.items()))
    for hid, lay in hubs.items():
        print("   %-10s %s" % (hid, "  ".join("%s:%s/%s%s" % (t["id"], t["size_class"],
                                                             t["_L"]["role"],
                                                             "x2" if len(t["_L"]["lines"]) > 1
                                                             else "")
                                           for t in lay["tiles"])))
    print("rule heights by n:", {n: [round(r[3] - r[1]) for r in hub_rects(n)]
                                 for n in range(2, 10)})
    print("lists: %s" % ", ".join(LIST_SCREENS))
    print("memory @2x per composed screen (excl. disc art):")
    for n, m in mem.items():
        print("   %-18s %6.1f KB" % (n, m["bytes_2x"] / 1024))
    if errs:
        print("\nCHECKS FAILED (%d):" % len(errs))
        for e in errs[:50]:
            print("  - " + e)
        return 1
    print("\nnav checks ok: hubs 1-9 tiles title-safe at peak motion incl. recoil, no label "
          "truncates or overlaps its icon, icons present, contrast per section; list labels "
          "and values fit; grid/table/event fit their areas; memory under budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
