"""Section 1 kit templates: screen chrome, list screen, widgets, dialog,
toast and cursor - layouts, motion, previews and checks.

    python pipeline/kit.py && python pipeline/font_atlas.py \
        && python pipeline/glyphs.py && python pipeline/kit_ui.py

Writes to out_kit/:
    chrome_layout.json list_layout.json widgets_layout.json
    dialog_layout.json cursor_layout.json    templates (format below)
    kit_motion.json                          hub_motion.json format
    manifest.json                            every kit texture, format, why
    preview/*.png                            composed from the JSON alone

Template format = hub_layout.json plus two things templates need:
  * space "unsheared": every vertex, glyph quads included, goes through the
    screen shear x' = x + (Y0 - y) * S as the LAST step, after layout and
    motion. That is what lets a row template be stamped at any y.
  * slots: dynamic content (strings, disc art, counts) with the type role,
    alignment, anchor (baseline point for text) and the maximum it must fit.
    Colours are kit tokens: '@face' etc. from the current section,
    'port:p1', or a palette name.
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

K = kit.K
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_kit")
S, Y0 = kit.SHEAR, 240
SAFE = (32, 24, 608, 456)
BUDGET = 1024 * 1024

FONT = json.load(open(os.path.join(OUT, "font", "font_manifest.json"), encoding="utf-8"))
GLY = json.load(open(os.path.join(OUT, "glyphs_manifest.json"), encoding="utf-8"))
ROLES = FONT["roles"]


def cap(role):
    return ROLES[role]["metrics"]["cap_height"]


def pen_walk(role, s):
    """-> [(char, pen_x)], total width: advances + kerning, as the engine sets it."""
    r = ROLES[role]
    out, pen, prev = [], 0.0, None
    for ch in s:
        if ch not in r["glyphs"]:
            ch = "?"
        if prev:
            pen += r["kerning"].get(prev + ch, 0.0)
        out.append((ch, pen))
        pen += r["glyphs"][ch]["advance"]
        prev = ch
    return out, pen


def text_w(role, s):
    return pen_walk(role, s)[1]


def base_for(role, y0, y1):
    """Baseline that centres the role's cap height in [y0, y1]."""
    return round((y0 + y1) / 2 + cap(role) / 2, 2)


# ============================================================ templates
def Q(id_, rect, colour, role="chrome", joint=None, texture=None, opacity=1.0):
    x0, y0, x1, y1 = rect
    q = dict(id=id_, kind="textured" if texture else "flat", role=role,
             verts=[[x0, y0], [x1, y0], [x1, y1], [x0, y1]], colour=colour)
    if texture:
        q["texture"], q["uv"] = texture, [0, 0, 1, 1]
    if joint:
        q["joint"] = joint
    if opacity != 1.0:
        q["opacity"] = opacity
    return q


def T(id_, role, anchor, max_str, colour, align="left", joint=None, max_width=None, note=None):
    s = dict(id=id_, kind="text", role=role, anchor=[round(anchor[0], 2), round(anchor[1], 2)],
             align=align, max=max_str, max_chars=len(max_str),
             max_width_1x=round(max_width if max_width else text_w(role, max_str), 2),
             colour=colour)
    if joint:
        s["joint"] = joint
    if note:
        s["note"] = note
    return s


# ---- chrome: header, breadcrumb, description strip, footer, backdrop
HEADER = (84, 24, 550, 52)
CRUMB = (96, 56, 550, 72)
DESC = (90, 398, 596, 422)
FOOTER = (90, 430, 596, 456)
TITLE_MAX = "RANDOM STAGE SWITCH!"          # 20 characters
CRUMB_MAX = "VERSUS / MORE RULES / RANDOM STAGE SWITCH / PAGE 12"[:52]
# Proportional text: slots are sized in px. These are realistic worst-case
# strings, checked against those widths; the engine applies the fit rule
# (next smaller role, then truncate with an ellipsis) to anything longer.
DESC_MAX = "Choose how many stocks each player starts with, from 1 to 99. L+R resets it."
HINT_MAX = "Defaults"                        # 8 characters
HINTS = 4
HINT_W = 72        # px per hint text: 4 wide glyphs + 4 texts + gaps fit the footer


def chrome():
    hx0, hy0, hx1, hy1 = HEADER
    title_x = hx0 + 16
    slab_x1 = title_x + text_w("title", TITLE_MAX) + 20
    fb = base_for("body", FOOTER[1], FOOTER[3])
    glyph_y0 = fb - cap("body") / 2 - 8
    return dict(
        name="chrome", space="unsheared", shear=dict(S=S, Y0=Y0),
        quads=[
            Q("header_rule", (slab_x1 - 4, hy1 - 6, hx1, hy1), "ink"),
            Q("header_slab", (hx0, hy0, slab_x1, hy1), "gold"),
            Q("crumb_icon", (CRUMB[0], CRUMB[1], CRUMB[0] + 16, CRUMB[1] + 16), "@face_hi",
              texture="ico_<section>"),
            Q("desc_strip", DESC, "ink"),
            Q("footer_strip", FOOTER, "ink"),
            Q("footer_mark", (FOOTER[0] + 10, FOOTER[1] + 7, FOOTER[0] + 16, FOOTER[3] - 7), "gold"),
        ],
        backdrop=dict(clear="@bg", bands="kit.sections[<section>].bands",
                      band_rect="(x, -40, x + w, 520)", colour="@band", role="decor"),
        slots=[
            T("title", "title", (title_x, base_for("title", hy0, hy1)), TITLE_MAX, "ink",
              max_width=hx1 - title_x - 40),
            T("breadcrumb", "body", (CRUMB[0] + 22, base_for("body", CRUMB[1], CRUMB[3])),
              CRUMB_MAX, "muted", max_width=CRUMB[2] - CRUMB[0] - 22,
              note="crumbs joined by a separator; the last crumb is bone"),
            T("description", "body", (DESC[0] + 16, base_for("body", DESC[1], DESC[3])),
              DESC_MAX, "bone", max_width=DESC[2] - DESC[0] - 32),
        ] + [
            dict(id="hint_%d" % i, kind="hint", glyph_slot="glyph_<button>",
                 glyph_h_1x=16, glyph_y0=round(glyph_y0, 2),
                 text=T("hint_%d_text" % i, "body", (0, fb), HINT_MAX, "bone",
                        max_width=HINT_W))
            for i in range(HINTS)
        ],
        rules=[
            "Header slab width follows the title: slab.x1 = title.x + advance(title) + 20; "
            "the ink rule starts 4px inside the slab's end.",
            "Breadcrumb: crumbs separated by 6px gap, a 2x10 gold bar quad, 6px gap. "
            "Earlier crumbs muted, the current one bone. If it exceeds max_width_1x, "
            "replace middle crumbs with '…' until it fits.",
            "Footer hints lay out left to right from x = footer.x0 + 24: glyph (16 or 32 "
            "wide), 4px, text, 12px. At most %d hints, each text at most %d px (fit rule "
            "beyond that)." % (HINTS, HINT_W),
            "The description strip is one line; longer copy belongs on a detail panel.",
        ])


# ---- list template
ROW_X0, ROW_X1, ROW_Y0, ROW_H, PITCH = 96, 540, 84, 30, 34
VISIBLE = 9
VALUE_X = 340
VALUE_W = 190
LABEL_MAX = "Stock Time Limit (min)"        # 22 characters
TRACK = (548, 96, 554, 380)
LIFT = [-3, -3]


def row_template():
    cy = ROW_H / 2
    return dict(
        name="row", space="unsheared", origin="row top-left at (%d, %d + i * %d)"
        % (ROW_X0, ROW_Y0, PITCH),
        quads=[
            Q("row_plate", (0, 0, ROW_X1 - ROW_X0, ROW_H), None, role="plate", joint="row_plate"),
            Q("row_face", (0, 0, ROW_X1 - ROW_X0, ROW_H), "@face", role="face", joint="row"),
        ],
        slots=[
            T("label", "row", (16, base_for("row", 0, ROW_H)), LABEL_MAX, "bone", joint="row",
              max_width=VALUE_X - ROW_X0 - 16 - 12),
            dict(id="value", kind="widget", origin=[VALUE_X - ROW_X0, cy], size=[VALUE_W, 22],
                 joint="row", accepts=["toggle", "choice", "slider", "stepper", "none"]),
        ],
        states=dict(
            ng=dict(face="@face", label="bone", plate=None, offset=[0, 0]),
            sel=dict(face="gold", label="ink", plate="gold_dk", offset=LIFT),
            disabled=dict(face="@face", label="disabled", plate=None, offset=[0, 0],
                          note="the cursor skips disabled rows"),
        ))


def divider_template():
    cy = ROW_H / 2
    label_x = 16
    return dict(
        name="divider", space="unsheared", origin="takes one row slot",
        quads=[
            Q("div_rule", (0, cy - 1, ROW_X1 - ROW_X0, cy + 1), "gold"),
            Q("div_plate", (8, cy - 8, label_x + 8 + text_w("caption", "ITEMS & HAZARDS"), cy + 8),
              "@bg"),
        ],
        slots=[T("label", "caption", (label_x, base_for("caption", 0, ROW_H)),
                 "ITEMS & HAZARDS", "gold")],
        rules=["div_plate width = label advance + 16; it knocks the rule out behind the label."])


def scroll_template():
    x0, y0, x1, y1 = TRACK
    return dict(
        name="scroll", space="unsheared",
        quads=[Q("track", TRACK, "ink"),
               Q("thumb", (x0, y0, x1, y0 + 80), "@face_hi", joint="thumb")],
        slots=[T("more_up", "caption", (x0 - 1.1, y0 - 4), "↑", "gold"),
               T("more_down", "caption", (x0 - 1.1, y1 + 12), "↓", "gold")],
        rules=["Shown only when rows exceed the %d visible." % VISIBLE,
               "thumb.h = max(16, track.h * visible / total); thumb.y slides with the "
               "first visible row (motion: scroll).",
               "more_up / more_down are visible only when rows are hidden that way."])


def list_layout():
    return dict(
        name="list", space="unsheared", shear=dict(S=S, Y0=Y0),
        panel=dict(rows_top=ROW_Y0, row_h=ROW_H, pitch=PITCH, visible=VISIBLE,
                   x0=ROW_X0, x1=ROW_X1),
        templates=[row_template(), divider_template(), scroll_template()],
        rules=[
            "Rows stack at pitch %d from y=%d; up to %d visible. Scrolling keeps the "
            "selected row at least one row from either edge." % (PITCH, ROW_Y0, VISIBLE),
            "Exactly one row is 'sel'. Draw order: rows top to bottom, the selected "
            "row last.",
            "A row's value slot hosts one widget from widgets_layout.json, in the "
            "row's state.",
        ])


# ---- widgets: local origin = value area left edge, row centre line
CHOICE_MAX = "Tournament Mode"[:14]        # 14 characters
NUM_MAX = "99:59"


def widgets():
    return dict(
        name="widgets", space="unsheared",
        origin="value area left edge, vertical centre of the row",
        states_from="the hosting row: ng / sel / disabled",
        colours=dict(
            ng=dict(row="@face", text="bone", aux="muted", track="ink", track_text="muted",
                    fill="@face_hi", knob="bone", toggle_knob="bone", knob_text="ink",
                    plate="ink", plate_glyph="bone"),
            sel=dict(row="gold", text="ink", aux="ink", track="ink", track_text="gold_dk",
                     fill="gold_dk", knob="ink", toggle_knob="gold_lt", knob_text="ink",
                     plate="ink", plate_glyph="gold_lt"),
            disabled=dict(row="@face", text="disabled", aux="disabled", track="ink",
                          track_text="disabled", fill="disabled", knob="disabled",
                          toggle_knob="disabled", knob_text="ink", plate="ink",
                          plate_glyph="disabled")),
        contrast_pairs=[["text", "row"], ["aux", "row"], ["track_text", "track"],
                        ["knob_text", "toggle_knob"], ["plate_glyph", "plate"]],
        widgets=dict(
            toggle=dict(
                quads=[Q("track", (0, -10, 120, 10), "track"),
                       Q("knob", (62, -8, 118, 8), "toggle_knob", joint="toggle_knob")],
                slots=[T("off", "row", (30, cap("row") / 2), "OFF", "track_text", align="centre"),
                       T("on", "row", (90, cap("row") / 2), "ON", "track_text", align="centre")],
                rules=["knob covers the active half: x 2..58 (off) or 62..118 (on).",
                       "The active half's text uses knob_text and draws above the knob."]),
            choice=dict(
                slots=[T("left", "row", (0, cap("row") / 2), "←", "aux", joint="choice_left"),
                       T("value", "row", (VALUE_W / 2, cap("row") / 2), CHOICE_MAX, "text",
                         align="centre", joint="choice_value"),
                       T("right", "row", (VALUE_W, cap("row") / 2), "→", "aux",
                         align="right", joint="choice_right")],
                rules=["wrap: true cycles; wrap: false stops at the ends, where the blocked "
                       "arrow takes 'disabled' and a press plays choice_bump."]),
            slider=dict(
                quads=[Q("track", (0, -3, 130, 3), "track"),
                       Q("fill", (0, -3, 130, 3), "fill", joint="slider_fill"),
                       Q("knob", (126, -9, 134, 9), "knob", joint="slider_knob")],
                slots=[T("readout", "row", (VALUE_W, cap("row") / 2), "100%", "text",
                         align="right", note="tabular digits; format from the engine")],
                rules=["fill SCA_X = value/max about x=0; knob TRA_X = 130 * value/max - 130."]),
            stepper=dict(
                quads=[Q("minus", (0, -10, 24, 10), "plate", joint="stepper_minus"),
                       Q("plus", (VALUE_W - 24, -10, VALUE_W, 10), "plate", joint="stepper_plus")],
                slots=[T("minus_g", "row", (12, cap("row") / 2), "-", "plate_glyph", align="centre",
                         joint="stepper_minus"),
                       T("plus_g", "row", (VALUE_W - 12, cap("row") / 2), "+", "plate_glyph",
                         align="centre", joint="stepper_plus"),
                       T("value", "row", (VALUE_W / 2, cap("row") / 2), NUM_MAX, "text",
                         align="centre", joint="stepper_value")],
                rules=["Held input repeats after 24 frames, then every 4 frames; after 60 "
                       "frames held, the step size multiplies by 10 if the engine allows."]),
            check_cell=dict(
                size=[72, 64], origin="cell top-left; grid pitch 76 x 68",
                quads=[Q("plate", (0, 0, 72, 64), None, role="plate", joint="cell_plate"),
                       Q("outline", (0, 0, 72, 64), "ink", joint="cell"),
                       Q("face", (3, 3, 69, 61), "@face", role="face", joint="cell"),
                       Q("tab", (50, 0, 72, 16), "ink", joint="cell_tab"),
                       Q("mark", (54, 1, 68, 15), "ink", joint="cell_tab", texture="glyph_check")],
                slots=[dict(id="art", kind="disc_art", rect=[4, 4, 68, 60], size_1x=[64, 56],
                            joint="cell", note="the disc's item or stage icon")],
                states=dict(
                    on=dict(tab="gold", mark="visible", art=dict(colour="#ffffff", opacity=1.0)),
                    off=dict(tab="ink", mark="hidden", art=dict(colour="#8a8a8a", opacity=0.45)),
                    sel=dict(face="gold", plate="gold_dk", offset=LIFT),
                    disabled=dict(face="@face", art=dict(colour="#8a8a8a", opacity=0.25),
                                  tab="ink", mark="hidden")),
                rules=["sel combines with on/off. Colour-blind safe: on/off differ by the "
                       "mark and the art's brightness, not only the tab colour."]),
        ))


# ---- dialog and toast
DIALOG_W = 420
D_TITLE_MAX = "OVERWRITE THE DATA IN SLOT B?"
D_LINE_MAX = "All records, unlocks, names and snapshots will be erased."
BTN_W, BTN_H, BTN_GAP = 110, 30, 10
BTN_MAX = "Continue"                                 # 8 characters
TOAST = DESC                      # covers the description strip completely
TOAST_MAX = "Saved to the Memory Card in Slot A. Your rules will be used from now on."


def dialog_geom(lines, buttons):
    title_h = 28
    body_top = title_h + 22
    last = body_top + (lines - 1) * 18
    btn_y = last + 18
    h = btn_y + BTN_H + 16
    x0, y0 = 320 - DIALOG_W / 2, round(240 - h / 2)
    return x0, y0, h, body_top, btn_y


def dialog():
    x0, y0, h, body_top, btn_y = dialog_geom(4, 3)
    return dict(
        name="dialog", space="unsheared",
        origin="panel top-left; the panel is centred on (320, 240) for its height",
        height_rule="h = 28 + 22 + (lines - 1) * 18 + 18 + %d + 16  (lines 1-4)" % BTN_H,
        quads=[
            Q("dim", (-60, -20, 700, 500), "ink", role="decor", joint="dialog_dim", opacity=0.65),
            Q("panel_ink", (-4, -4, DIALOG_W + 4, "h+4"), "ink", joint="dialog_panel"),
            Q("panel_face", (0, 0, DIALOG_W, "h"), "@face", joint="dialog_panel"),
            Q("title_slab", (0, 0, 16 + text_w("title", D_TITLE_MAX) + 20, 28), "gold",
              joint="dialog_panel"),
        ],
        slots=[T("title", "title", (16, base_for("title", 0, 28)), D_TITLE_MAX, "ink",
                 joint="dialog_panel", max_width=DIALOG_W - 36)] +
              [T("line_%d" % i, "body", (16, body_top + 18 * i), D_LINE_MAX, "bone",
                 max_width=DIALOG_W - 32,
                 joint="dialog_panel") for i in range(4)] +
              [dict(id="button_%d" % i, kind="button", size=[BTN_W, BTN_H],
                    origin="right-aligned: x1 = W - 16 - i * (%d + %d), y = body_top + (lines - 1) "
                           "* 18 + 18" % (BTN_W, BTN_GAP),
                    label=T("button_%d_label" % i, "label", (BTN_W / 2, base_for("label", 0, BTN_H)),
                            BTN_MAX, "bone", align="centre"),
                    joint="dialog_button") for i in range(3)],
        button_states=dict(
            ng=dict(face="@bg", label="bone", offset=[0, 0], plate=None),
            sel=dict(face="gold", label="ink", offset=LIFT, plate="gold_dk"),
            danger_ng=dict(face="@bg", label="bone", accent="danger", offset=[0, 0], plate=None),
            danger_sel=dict(face="danger", label="ink", accent="ink", offset=LIFT, plate="ink"),
            accent_rect="(0, 0, 6, h): a stripe at the button's left edge, danger buttons only; "
                        "red text on the dark face failed 4.5:1 in every section"),
        toast=dict(
            rect=list(TOAST), space="unsheared",
            quads=[Q("toast_plate", TOAST, "ink", joint="toast"),
                   Q("toast_accent", (TOAST[0], TOAST[1], TOAST[0] + 6, TOAST[3]), "ok",
                     joint="toast")],
            slots=[T("toast_text", "body", (TOAST[0] + 16, base_for("body", TOAST[1], TOAST[3])),
                     TOAST_MAX, "bone", joint="toast", max_width=TOAST[2] - TOAST[0] - 32)],
            rules=["Covers the description strip exactly, sliding in from the right; the "
                   "description underneath is hidden once the toast lands. accent is 'ok' "
                   "or 'danger'.",
                   "toast_in, hold 90 frames (or until the next toast), toast_out."]),
        rules=["Default selection is the non-destructive button.",
               "The dim quad and the panel are drawn above everything, cursor included."])


def cursor_layout():
    c = GLY["cursor"]
    return dict(name="cursor", space="screen (never sheared: the hand points where it points)",
                size_1x=[32, 32], hotspot_1x=c["hotspot_1x"], layers=c["layers"],
                variants=c["variants"], badge=c["badge"],
                slots=[T("badge_text", "caption",
                         (c["badge"]["anchor_1x"][0] + c["badge"]["pad_x_1x"],
                          c["badge"]["anchor_1x"][1] + base_for("caption", 0, c["badge"]["height_1x"])),
                         "CPU", "port:<port>")])


# ================================================================ motion
def k(f, v, ip="SPL", s=0.0, fc=False):
    d = dict(frame=f, value=v, interp=ip, slope=s)
    if fc:
        d["from_current"] = True
    return d


def tr(target, channel, *keys, kind="joint"):
    return dict(target=target, kind=kind, channel=channel, keys=list(keys))


def lift_tracks(j, dx, dy, over=1.3):
    return [tr(j, "TRA_X", k(0, 0, fc=True), k(4, dx * over), k(9, dx)),
            tr(j, "TRA_Y", k(0, 0, fc=True), k(4, dy * over), k(9, dy))]


def drop_tracks(j):
    return [tr(j, "TRA_X", k(0, 0, fc=True), k(5, 0)), tr(j, "TRA_Y", k(0, 0, fc=True), k(5, 0))]


def motion():
    ev = {}
    ev["row_select"] = dict(
        applies_to="row", sfx=[dict(frame=0, cue="sfx_cursor_move")],
        tracks=lift_tracks("row", *LIFT) + [
            tr("row_plate", "ALPHA", k(0, 1, "CON"), kind="material"),
            tr("row_face", "COLOUR", k(0, "@face", "LIN", fc=True), k(1, "gold_lt", "LIN"),
               k(8, "gold", "LIN"), kind="material"),
            tr("row_label", "COLOUR", k(0, "bone", "CON"), k(1, "ink", "CON"), kind="material")])
    ev["row_deselect"] = dict(
        applies_to="row", sfx=[],
        tracks=drop_tracks("row") + [
            tr("row_plate", "ALPHA", k(0, 1, "CON"), k(5, 0, "CON"), kind="material"),
            tr("row_face", "COLOUR", k(0, "gold", "LIN", fc=True), k(2, "@face", "LIN"),
               kind="material"),
            tr("row_label", "COLOUR", k(0, "ink", "CON"), k(2, "bone", "CON"), kind="material")])
    ev["scroll"] = dict(
        applies_to="list rows and thumb", sfx=[],
        note="rows TRA_Y by -pitch * delta; thumb TRA_Y to its new position",
        tracks=[tr("rows", "TRA_Y", k(0, 0, fc=True), k(6, "-34*delta")),
                tr("thumb", "TRA_Y", k(0, 0, fc=True), k(6, "target"))])
    ev["toggle_set"] = dict(
        applies_to="toggle", sfx=[dict(frame=0, cue="sfx_toggle")],
        note="dir = +1 to on, -1 to off; knob travels 60px",
        tracks=[tr("toggle_knob", "TRA_X", k(0, 0, fc=True), k(4, "60*dir + 3*dir"), k(8, "60*dir")),
                tr("toggle_knob", "SCA_X", k(0, 1), k(2, 1.12), k(8, 1))])
    ev["choice_step"] = dict(
        applies_to="choice", sfx=[dict(frame=0, cue="sfx_value_change")],
        note="the old string draws on value_out, the new on value; dir = +1 right, -1 left",
        tracks=[tr("choice_value_out", "TRA_X", k(0, 0), k(4, "16*dir", "SPL", 0)),
                tr("choice_value_out", "ALPHA", k(0, 1, "LIN"), k(4, 0, "LIN"), kind="material"),
                tr("choice_value", "TRA_X", k(0, "-16*dir"), k(6, "2*dir"), k(9, 0)),
                tr("choice_value", "ALPHA", k(0, 0, "LIN"), k(5, 1, "LIN"), kind="material"),
                tr("choice_arrow_<dir>", "COLOUR", k(0, "gold_lt", "LIN"), k(6, "aux", "LIN"),
                   kind="material"),
                tr("choice_arrow_<dir>", "TRA_X", k(0, 0), k(2, "3*dir"), k(6, 0))])
    bump = [tr("<value>", "TRA_X", k(0, 0, fc=True), k(2, "3*dir"), k(4, "-1*dir"), k(7, 0)),
            tr("<blocked_arrow>", "COLOUR", k(0, "danger", "CON"), k(8, "disabled", "CON"),
               kind="material")]
    ev["bump"] = dict(
        applies_to="choice, slider, stepper at an end ('can't go further')",
        sfx=[dict(frame=0, cue="sfx_bump")],
        note="<value> is choice_value, slider_knob or stepper_value; no value change",
        tracks=bump)
    ev["slider_step"] = dict(
        applies_to="slider", sfx=[dict(frame=0, cue="sfx_value_tick")],
        tracks=[tr("slider_fill", "SCA_X", k(0, 1, fc=True), k(5, "value/max")),
                tr("slider_knob", "TRA_X", k(0, 0, fc=True), k(5, "130*value/max-130")),
                tr("slider_knob", "SCA_Y", k(0, 1), k(2, 1.2), k(6, 1))])
    ev["stepper_step"] = dict(
        applies_to="stepper", sfx=[dict(frame=0, cue="sfx_value_tick")],
        note="dir = +1 plus, -1 minus",
        tracks=[tr("stepper_value", "TRA_Y", k(0, "3*dir"), k(4, 0)),
                tr("stepper_<plus|minus>", "SCA_X", k(0, 0.85), k(5, 1)),
                tr("stepper_<plus|minus>", "SCA_Y", k(0, 0.85), k(5, 1))])
    ev["check_toggle"] = dict(
        applies_to="check_cell", sfx=[dict(frame=0, cue="sfx_toggle")],
        tracks=[tr("cell_tab", "SCA_X", k(0, 0.6), k(3, 1.15), k(7, 1)),
                tr("cell_tab", "SCA_Y", k(0, 0.6), k(3, 1.15), k(7, 1)),
                tr("cell_art", "COLOUR", k(0, "#8a8a8a|#ffffff", "LIN", fc=True),
                   k(4, "target", "LIN"), kind="material")])
    ev["cell_select"] = dict(applies_to="check_cell", sfx=[dict(frame=0, cue="sfx_cursor_move")],
                             tracks=lift_tracks("cell", *LIFT) + [
                                 tr("cell_plate", "ALPHA", k(0, 1, "CON"), kind="material")])
    ev["cell_deselect"] = dict(applies_to="check_cell", sfx=[],
                               tracks=drop_tracks("cell") + [
                                   tr("cell_plate", "ALPHA", k(0, 1, "CON"), k(5, 0, "CON"),
                                      kind="material")])
    ev["dialog_open"] = dict(
        applies_to="dialog", sfx=[dict(frame=0, cue="sfx_dialog_open")],
        pivot="panel centre",
        tracks=[tr("dialog_dim", "ALPHA", k(0, 0, "LIN"), k(6, 0.65, "LIN"), kind="material"),
                tr("dialog_panel", "ALPHA", k(0, 0, "LIN"), k(4, 1, "LIN"), kind="material"),
                tr("dialog_panel", "SCA_X", k(0, 0.92), k(5, 1.02), k(9, 1)),
                tr("dialog_panel", "SCA_Y", k(0, 0.92), k(5, 1.02), k(9, 1))])
    ev["dialog_close"] = dict(
        applies_to="dialog", sfx=[dict(frame=0, cue="sfx_dialog_close")],
        tracks=[tr("dialog_panel", "ALPHA", k(0, 1, "LIN"), k(4, 0, "LIN"), kind="material"),
                tr("dialog_panel", "SCA_X", k(0, 1), k(4, 0.96)),
                tr("dialog_panel", "SCA_Y", k(0, 1), k(4, 0.96)),
                tr("dialog_dim", "ALPHA", k(0, 0.65, "LIN"), k(6, 0, "LIN"), kind="material")])
    ev["button_select"] = dict(applies_to="dialog button", sfx=[dict(frame=0, cue="sfx_cursor_move")],
                               note="same as row_select on the button's joints",
                               tracks=lift_tracks("dialog_button", *LIFT))
    ev["button_deselect"] = dict(applies_to="dialog button", sfx=[],
                                 tracks=drop_tracks("dialog_button"))
    ev["toast_in"] = dict(applies_to="toast", sfx=[dict(frame=0, cue="sfx_toast")], offscreen=True,
                          tracks=[tr("toast", "TRA_X", k(0, 600, "SPL", -110), k(9, -4), k(13, 0))])
    ev["toast_out"] = dict(applies_to="toast", sfx=[], offscreen=True,
                           tracks=[tr("toast", "TRA_X", k(0, 0, fc=True), k(9, 600, "SPL", 120))])
    ev["cursor_press"] = dict(applies_to="cursor", sfx=[], pivot="hotspot",
                              tracks=[tr("cursor", "SCA_X", k(0, 1), k(2, 0.88), k(7, 1)),
                                      tr("cursor", "SCA_Y", k(0, 1), k(2, 0.88), k(7, 1))])
    for e in ev.values():
        e["length_frames"] = 1 + max(kk["frame"] for t in e["tracks"] for kk in t["keys"])

    return dict(
        fps=60, format="hub_motion.json: tracks, from_current, interpolation and "
                       "transform rules are identical; see out_hub/hub_motion.json",
        space="unsheared - motion is applied before the screen shear",
        value_expressions="string values are evaluated by the player: dir, value, max, "
                          "delta, target; colour values are kit tokens",
        events=ev,
        sequences=dict(
            list_cursor_move=[dict(event="row_deselect", on="previous"),
                              dict(event="row_select", on="new"),
                              dict(event="scroll", when="the new row is within one row of an edge")],
            value_change=[dict(event="toggle_set | choice_step | slider_step | stepper_step",
                               on="selected row", when="the value can change"),
                          dict(event="bump", on="selected row", when="it cannot")],
            dialog=[dict(event="dialog_open"), dict(event="button_select", on="default button"),
                    dict(event="dialog_close", when="confirmed or cancelled")],
            toast=[dict(event="toast_in"), dict(hold_frames=90), dict(event="toast_out")],
            hold_repeat=dict(delay_frames=24, interval_frames=4),
        ))


# ================================================================ preview
class Scene:
    """Collects draw items in unsheared screen space, then shears once."""
    def __init__(self, section):
        self.section, self.items = section, []

    def col(self, tok):
        if tok is None:
            return None
        if tok.startswith("@"):
            return kit.SECTIONS[self.section][tok[1:]]
        if tok.startswith("port:"):
            return kit.PORTS[tok[5:]]
        if tok.startswith("#"):
            return tok
        return kit.PALETTE[tok]

    def quad(self, rect, colour, tex=None, uv=(0, 0, 1, 1), opacity=1.0, joint=None,
             sheared=True, tag=None):
        x0, y0, x1, y1 = rect
        self.items.append(dict(verts=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                               colour=self.col(colour) if colour else None, tex=tex, uv=uv,
                               opacity=opacity, joint=joint, sheared=sheared, tag=tag))

    def text(self, role, s, x, base, colour, align="left", joint=None, opacity=1.0):
        r = ROLES[role]
        w = text_w(role, s)
        if align == "centre":
            x -= w / 2
        elif align == "right":
            x -= w
        for ch, px in pen_walk(role, s)[0]:
            g = r["glyphs"][ch]
            if "uv" in g:
                ox, oy = g["offset"]
                gw, gh = g["size"]
                page = r["pages"]["latin"][g["page"]]
                pen = x + px
                self.quad((pen + ox, base + oy, pen + ox + gw, base + oy + gh), colour,
                          tex=page, uv=g["uv"], joint=joint, opacity=opacity, tag="glyph")
        return w


def shear_pt(x, y):
    return (x + (Y0 - y) * S, y)


# where a texture name is found, first match wins: kit, section 2 (out_nav), online,
# then the hub prototype (out_hub) for anything not yet re-issued
TEX_DIRS = [os.path.join(OUT, "font", "2x"), os.path.join(OUT, "2x"),
            os.path.join(ROOT, "out_nav", "2x"), os.path.join(ROOT, "out_online", "2x"),
            os.path.join(ROOT, "out_hub", "tex", "2x")]


def tex_path(name):
    for d in TEX_DIRS:
        p = os.path.join(d, name + ".png")
        if os.path.exists(p):
            return p
    return None


class Textures:
    def __init__(self):
        self.b64, self.size = {}, {}

    def get(self, name):
        if name not in self.b64:
            path = tex_path(name)
            img = Image.open(path)
            self.size[name] = img.size
            self.b64[name] = base64.b64encode(open(path, "rb").read()).decode()
        return name


def svg(scene, tx, clear):
    defs, body, used = [], [], set()
    for i, it in enumerate(scene.items):
        vs = [shear_pt(*v) if it["sheared"] else v for v in it["verts"]]
        pts = " ".join("%.3f,%.3f" % v for v in vs)
        op = ' opacity="%.3f"' % it["opacity"] if it["opacity"] < 1 else ""
        if not it["tex"]:
            body.append('<polygon points="%s" fill="%s"%s/>' % (pts, it["colour"], op))
            continue
        name = tx.get(it["tex"])
        used.add(name)
        W, H = tx.size[name]
        u0, v0, u1, v1 = it["uv"]
        (tlx, tly), (trx, try_), _, (blx, bly) = vs
        du, dv = (u1 - u0) * W, (v1 - v0) * H
        a, b = (trx - tlx) / du, (try_ - tly) / du
        c, d = (blx - tlx) / dv, (bly - tly) / dv
        e = tlx - a * u0 * W - c * v0 * H
        f = tly - b * u0 * W - d * v0 * H
        defs.append('<mask id="m%d" maskUnits="userSpaceOnUse" x="-100" y="-100" width="840" '
                    'height="680"><use href="#t_%s" transform="matrix(%g %g %g %g %g %g)"/></mask>'
                    % (i, name, a, b, c, d, e, f))
        body.append('<polygon points="%s" fill="%s" mask="url(#m%d)"%s/>' % (pts, it["colour"], i, op))
    imgs = "".join('<image id="t_%s" href="data:image/png;base64,%s" width="%d" height="%d"/>'
                   % (n, tx.b64[n], *tx.size[n]) for n in used)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="960" viewBox="0 0 640 480">'
            '<defs>%s%s</defs><rect x="-10" y="-10" width="660" height="500" fill="%s"/>%s</svg>'
            % (imgs, "".join(defs), clear, "".join(body)))


def render(page, scene, tx):
    page.set_viewport_size({"width": 1280, "height": 960})
    page.set_content("<body style='margin:0'>%s</body>" % svg(scene, tx, scene.col("@bg")))
    return Image.open(io.BytesIO(page.locator("svg").screenshot(type="png"))).convert("RGB")


# ---- composing screens from the templates
def draw_chrome(sc, ch, title, crumbs, hints, desc):
    for x, w in kit.SECTIONS[sc.section]["bands"]:
        sc.quad((x, -40, x + w, 520), "@band", tag="decor")
    q = {x["id"]: x for x in ch["quads"]}
    title_x = ch["slots"][0]["anchor"][0]
    slab_x1 = title_x + text_w("title", title) + 20
    hx0, hy0, hx1, hy1 = HEADER
    sc.quad((slab_x1 - 4, hy1 - 6, hx1, hy1), "ink")
    sc.quad((hx0, hy0, slab_x1, hy1), "gold")
    sc.text("title", title, title_x, ch["slots"][0]["anchor"][1], "ink")
    icon = getattr(sc, "crumb_icon", None) or "ico_" + sc.section
    if tex_path(icon):
        sc.quad(q["crumb_icon"]["verts"][0] + q["crumb_icon"]["verts"][2], "@face_hi", tex=icon)
    bx, by = ch["slots"][1]["anchor"]
    for i, c in enumerate(crumbs):
        last = i == len(crumbs) - 1
        bx += sc.text("body", c, bx, by, "bone" if last else "muted")
        if not last:
            sc.quad((bx + 6, by - 9, bx + 8, by + 1), "gold")
            bx += 14
    sc.quad(DESC, "ink")
    sc.text("body", desc, DESC[0] + 16, ch["slots"][2]["anchor"][1], "bone")
    sc.quad(FOOTER, "ink")
    sc.quad((FOOTER[0] + 10, FOOTER[1] + 7, FOOTER[0] + 16, FOOTER[3] - 7), "gold")
    fb = base_for("body", FOOTER[1], FOOTER[3])
    hx = FOOTER[0] + 24
    gy0 = fb - cap("body") / 2 - 8
    for g, t in hints:
        gw = GLY_W[g]
        tint = GLY["button_glyphs"]["tint"]["suggested"].get(g, "bone")
        sc.quad((hx, gy0, hx + gw, gy0 + 16), tint, tex="glyph_" + g)
        hx += gw + 4
        end = hx + sc.text("body", t, hx, fb, "bone")
        hx = end + 12
    return end


GLY_W = {r["name"][6:]: r["size_1x"][0] for r in GLY["textures"] if r["name"].startswith("glyph_")}


def draw_widget(sc, kind, ox, oy, state, value):
    W = WID["widgets"][kind]
    colours = WID["colours"][state]

    def c(tok):
        return colours.get(tok, tok)
    if kind == "toggle":
        on = value
        sc.quad((ox, oy - 10, ox + 120, oy + 10), c("track"))
        kx = 62 if on else 2
        sc.quad((ox + kx, oy - 8, ox + kx + 56, oy + 8), c("toggle_knob"), joint="toggle_knob")
        for label, cx, active in (("OFF", 30, not on), ("ON", 90, on)):
            sc.text("row", label, ox + cx, oy + cap("row") / 2,
                    c("knob_text") if active else c("track_text"), align="centre")
    elif kind == "choice":
        text, left_ok, right_ok = value
        sc.text("row", "←", ox, oy + cap("row") / 2, c("aux") if left_ok else "disabled",
                joint="choice_left")
        sc.text("row", text, ox + VALUE_W / 2, oy + cap("row") / 2, c("text"), align="centre",
                joint="choice_value")
        sc.text("row", "→", ox + VALUE_W, oy + cap("row") / 2,
                c("aux") if right_ok else "disabled", align="right", joint="choice_right")
    elif kind == "slider":
        frac, label = value
        sc.quad((ox, oy - 3, ox + 130, oy + 3), c("track"))
        sc.quad((ox, oy - 3, ox + 130 * frac, oy + 3), c("fill"), joint="slider_fill")
        kx = ox + 130 * frac
        sc.quad((kx - 4, oy - 9, kx + 4, oy + 9), c("knob"), joint="slider_knob")
        sc.text("row", label, ox + VALUE_W, oy + cap("row") / 2, c("text"), align="right")
    elif kind == "stepper":
        sc.quad((ox, oy - 10, ox + 24, oy + 10), c("plate"), joint="stepper_minus")
        sc.quad((ox + VALUE_W - 24, oy - 10, ox + VALUE_W, oy + 10), c("plate"), joint="stepper_plus")
        sc.text("row", "-", ox + 12, oy + cap("row") / 2, c("plate_glyph"), align="centre")
        sc.text("row", "+", ox + VALUE_W - 12, oy + cap("row") / 2, c("plate_glyph"), align="centre")
        sc.text("row", value, ox + VALUE_W / 2, oy + cap("row") / 2, c("text"), align="centre",
                joint="stepper_value")


def draw_row(sc, i, label, state, widget=None, value=None, lift=None):
    y = ROW_Y0 + i * PITCH
    st = ROW_T["states"][state]
    off = lift if lift is not None else st["offset"]
    if st["plate"]:
        sc.quad((ROW_X0, y, ROW_X1, y + ROW_H), st["plate"], joint="row_plate")
    dx, dy = off
    sc.quad((ROW_X0 + dx, y + dy, ROW_X1 + dx, y + ROW_H + dy), st["face"], joint="row")
    sc.text("row", label, ROW_X0 + 16 + dx, y + base_for("row", 0, ROW_H) + dy, st["label"])
    if widget:
        draw_widget(sc, widget, VALUE_X + dx, y + ROW_H / 2 + dy, state, value)


def draw_divider(sc, i, label):
    y = ROW_Y0 + i * PITCH
    cy = y + ROW_H / 2
    sc.quad((ROW_X0, cy - 1, ROW_X1, cy + 1), "gold")
    sc.quad((ROW_X0 + 8, cy - 8, ROW_X0 + 24 + text_w("caption", label), cy + 8), "@bg")
    sc.text("caption", label, ROW_X0 + 16, y + base_for("caption", 0, ROW_H), "gold")


def draw_scroll(sc, first, visible, total):
    x0, y0, x1, y1 = TRACK
    h = y1 - y0
    th = max(16, h * visible / total)
    ty = y0 + (h - th) * first / max(1, total - visible)
    sc.quad(TRACK, "ink")
    sc.quad((x0, ty, x1, ty + th), "@face_hi", joint="thumb")
    if first > 0:
        sc.text("caption", "↑", x0 + 3, y0 - 4, "gold", align="centre")
    if first + visible < total:
        sc.text("caption", "↓", x0 + 3, y1 + 12, "gold", align="centre")


def draw_dialog(sc, title, lines, buttons, sel):
    x0, y0, h, body_top, btn_y = dialog_geom(len(lines), len(buttons))
    sc.quad((-60, -20, 700, 500), "ink", opacity=0.65, tag="decor", sheared=False)
    sc.quad((x0 - 4, y0 - 4, x0 + DIALOG_W + 4, y0 + h + 4), "ink", joint="dialog_panel")
    sc.quad((x0, y0, x0 + DIALOG_W, y0 + h), "@face", joint="dialog_panel")
    sc.quad((x0, y0, x0 + 16 + text_w("title", title) + 20, y0 + 28), "gold", joint="dialog_panel")
    sc.text("title", title, x0 + 16, y0 + base_for("title", 0, 28), "ink", joint="dialog_panel")
    for i, ln in enumerate(lines):
        sc.text("body", ln, x0 + 16, y0 + body_top + 18 * i, "bone", joint="dialog_panel")
    bx1 = x0 + DIALOG_W - 16
    for i, (label, danger) in enumerate(reversed(buttons)):
        idx = len(buttons) - 1 - i
        st = DLG["button_states"][("danger_" if danger else "") + ("sel" if idx == sel else "ng")]
        bx0 = bx1 - BTN_W
        by = y0 + btn_y
        if st["plate"]:
            sc.quad((bx0, by, bx1, by + BTN_H), st["plate"], joint="dialog_button")
        dx, dy = st["offset"]
        sc.quad((bx0 + dx, by + dy, bx1 + dx, by + BTN_H + dy), st["face"], joint="dialog_button")
        if st.get("accent"):
            sc.quad((bx0 + dx, by + dy, bx0 + 6 + dx, by + BTN_H + dy), st["accent"],
                    joint="dialog_button")
        sc.text("label", label, (bx0 + bx1) / 2 + dx, by + base_for("label", 0, BTN_H) + dy,
                st["label"], align="centre", joint="dialog_button")
        bx1 = bx0 - BTN_GAP


def draw_toast(sc, text, accent="ok"):
    sc.quad(TOAST, "ink", joint="toast")
    sc.quad((TOAST[0], TOAST[1], TOAST[0] + 6, TOAST[3]), accent, joint="toast")
    sc.text("body", text, TOAST[0] + 16, base_for("body", TOAST[1], TOAST[3]), "bone", joint="toast")


def draw_cursor(sc, x, y, variant):
    v = CUR["variants"][variant]
    fill = "bone" if v["fill"] == "bone" else "port:" + v["fill"]
    hx, hy = CUR["hotspot_1x"]
    ox, oy = x - hx, y - hy
    sdx, sdy = CUR["layers"][0]["offset_1x"]
    sc.quad((ox + sdx, oy + sdy, ox + 32 + sdx, oy + 32 + sdy), "ink", tex="cursor_ink", sheared=False)
    sc.quad((ox, oy, ox + 32, oy + 32), "ink", tex="cursor_ink", sheared=False)
    sc.quad((ox, oy, ox + 32, oy + 32), fill, tex="cursor_fill", sheared=False)
    sc.quad((ox, oy, ox + 32, oy + 32), "ink", tex="cursor_detail", sheared=False)
    if v["badge"]:
        b = CUR["badge"]
        t = v["badge"]["text"]
        bx, by = ox + b["anchor_1x"][0], oy + b["anchor_1x"][1]
        w = text_w("caption", t) + 2 * b["pad_x_1x"]
        hgt = b["height_1x"]
        sk = hgt * S
        sc.items.append(dict(verts=[(bx + sk, by), (bx + w + sk, by), (bx + w, by + hgt), (bx, by + hgt)],
                             colour=sc.col("ink"), tex=None, uv=None, opacity=1.0, joint="cursor",
                             sheared=False, tag=None))
        sc.text("caption", t, bx + b["pad_x_1x"] + sk / 2, by + base_for("caption", 0, hgt),
                "port:" + v["fill"])
        # badge text is sheared like the plate: shear the glyphs just added about their baseline
        base = by + base_for("caption", 0, hgt)
        for it in sc.items[-len(t):]:
            it["sheared"] = False
            it["verts"] = [(vx + (base - vy) * S, vy) for vx, vy in it["verts"]]


# ================================================================ checks
def check(scenes, mot, layouts):
    errs = []
    # 1. slots fit their maxima at their type size
    def walk(o):
        if isinstance(o, dict):
            if o.get("kind") == "text":
                need = text_w(o["role"], o["max"])
                if need > o["max_width_1x"] + 0.01:
                    errs.append("slot %s: '%s' needs %.1f px, has %.1f"
                                % (o["id"], o["max"], need, o["max_width_1x"]))
                if o["role"] in ("hero", "display") and any(ch.islower() for ch in o["max"]):
                    errs.append("slot %s uses lower case in a caps-only role" % o["id"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for lay in layouts.values():
        walk(lay)

    # footer: worst-case hints fit before the strip end
    for name, sc in scenes.items():
        if getattr(sc, "footer_end", None) and sc.footer_end > FOOTER[2] - 8:
            errs.append("%s: footer hints run to x=%.1f (strip ends %d)" % (name, sc.footer_end, FOOTER[2]))
        if getattr(sc, "crumb_end", None) and sc.crumb_end > CRUMB[2]:
            errs.append("%s: breadcrumb runs to x=%.1f" % (name, sc.crumb_end))

    # 2. title-safe incl. peak motion, per joint
    ext = {}
    for e in mot["events"].values():
        if e.get("offscreen"):
            continue
        for t in e["tracks"]:
            if t["kind"] != "joint":
                continue
            vals = [kk["value"] for kk in t["keys"] if isinstance(kk["value"], (int, float))]
            if not vals:
                continue
            lo, hi = min(vals + [0]), max(vals + [0])
            j = ext.setdefault(t["target"], dict(tx=[0, 0], ty=[0, 0], s=1.0))
            if t["channel"] == "TRA_X":
                j["tx"] = [min(j["tx"][0], lo), max(j["tx"][1], hi)]
            elif t["channel"] == "TRA_Y":
                j["ty"] = [min(j["ty"][0], lo), max(j["ty"][1], hi)]
            elif t["channel"].startswith("SCA"):
                j["s"] = max(j["s"], max(vals))
    sx0, sy0, sx1, sy1 = SAFE
    for name, sc in scenes.items():
        for it in sc.items:
            if it["tag"] == "decor":
                continue
            j = ext.get(it["joint"] or "", dict(tx=[0, 0], ty=[0, 0], s=1.0))
            # lift is already drawn at rest for the selected item; add the overshoot beyond it
            over = 0.3 if it["joint"] in ("row", "cell", "dialog_button") else 1.0
            xs = [v[0] for v in it["verts"]]
            ys = [v[1] for v in it["verts"]]
            cx, cy = sum(xs) / 4, sum(ys) / 4
            for vx, vy in it["verts"]:
                for dx in (j["tx"][0] * over, j["tx"][1] * over):
                    for dy in (j["ty"][0] * over, j["ty"][1] * over):
                        px = cx + (vx - cx) * j["s"] + dx
                        py = cy + (vy - cy) * j["s"] + dy
                        if it["sheared"]:
                            px, py = shear_pt(px, py)
                        if not (sx0 - 1e-6 <= px <= sx1 + 1e-6 and sy0 - 1e-6 <= py <= sy1 + 1e-6):
                            errs.append("%s: %s item leaves title-safe at (%.1f, %.1f)"
                                        % (name, it["joint"] or it["tag"] or "quad", px, py))
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break

    # 3. every list row fits 9 visible between breadcrumb and description
    last = ROW_Y0 + (VISIBLE - 1) * PITCH + ROW_H
    if last + LIFT[1] < CRUMB[3] or last > DESC[1] - 4:
        errs.append("list rows end at y=%d, description starts %d" % (last, DESC[1]))

    # 4. text contrast in every state, every section
    wc = layouts["widgets"]["colours"]
    pairs = [("widget %s %s on %s" % (st, fg, bg), wc[st][fg], wc[st][bg])
             for st in wc for fg, bg in layouts["widgets"]["contrast_pairs"]]
    pairs += [("row ng label", "bone", "@face"), ("row sel label", "ink", "gold"),
             ("row disabled label", "disabled", "@face"), ("dialog button ng", "bone", "@bg"),
             ("dialog danger ng", "bone", "@bg"), ("dialog danger sel", "ink", "danger"),
             ("divider label", "gold", "@bg"), ("footer", "bone", "ink"),
             ("breadcrumb", "muted", "@bg")]
    report = {}
    for s in kit.SECTIONS:
        sc = Scene(s)
        for name, fg, bg in pairs:
            c = K.contrast(K.hexrgb(sc.col(fg)), K.hexrgb(sc.col(bg)))
            need = kit.MIN_DISABLED if "disabled" in name else kit.MIN_TEXT
            report.setdefault(name, []).append(round(c, 2))
            if c < need:
                errs.append("%s: %s %.2f:1 < %.1f" % (s, name, c, need))
    return errs, {k: min(v) for k, v in report.items()}


# ================================================================== main
def memory(tex_names):
    total = 0
    rows = {r["name"]: r for r in MANIFEST_ROWS}
    for n in sorted(set(tex_names)):
        total += rows[n]["bytes_2x"] if n in rows else 0
    return total


MANIFEST_ROWS = []


def main():
    global WID, DLG, CUR, ROW_T
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
    layouts = dict(chrome=chrome(), list=list_layout(), widgets=widgets(), dialog=dialog(),
                   cursor=cursor_layout())
    WID, DLG, CUR = layouts["widgets"], layouts["dialog"], layouts["cursor"]
    ROW_T = layouts["list"]["templates"][0]
    mot = motion()
    for n, lay in layouts.items():
        with open(os.path.join(OUT, "%s_layout.json" % n), "w", encoding="utf-8") as fh:
            json.dump(lay, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(OUT, "kit_motion.json"), "w", encoding="utf-8") as fh:
        json.dump(mot, fh, indent=1, ensure_ascii=False)

    # ---- manifest: every kit texture with format + reason
    for t in FONT["textures"]:
        MANIFEST_ROWS.append(dict(t, kind="font", why=FONT["format"]["why"]))
    for t in GLY["textures"]:
        MANIFEST_ROWS.append(t)
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(provenance="Original. Kit textures generated by pipeline/font_atlas.py "
                                  "and pipeline/glyphs.py; nothing traced, sampled or recoloured "
                                  "from Melee.", textures=MANIFEST_ROWS), fh, indent=1)

    # ---- worst-case compositions
    scenes = {}
    worst_hints = [("start", "Defaults"), ("l", "Previous"), ("r", "Next Tab"), ("z", "Settings")]

    def list_screen(section, sel=2, dialog=False, toast=False):
        sc = Scene(section)
        crumbs = ["VERSUS", "MORE RULES", "RANDOM STAGE SWITCH"]
        desc = DESC_MAX
        sc.footer_end = draw_chrome(sc, layouts["chrome"], TITLE_MAX, crumbs, worst_hints, desc)
        bx = CRUMB[0] + 22
        sc.crumb_end = bx + sum(text_w("body", c) for c in crumbs) + 14 * (len(crumbs) - 1)
        rows = [
            ("row", "Mode", "choice", ("Tournament Mod", False, True)),
            ("row", "Stock Time Limit (min)", "stepper", NUM_MAX),
            ("row", "Handicap", "toggle", True),
            ("row", "Damage Ratio", "slider", (0.5, "100%")),
            ("div", "ITEMS & HAZARDS"),
            ("row", "Items", "choice", ("High", True, True)),
            ("row", "Pause", "toggle", False),
            ("dis", "Score Display", "toggle", False),
            ("row", "Self-Destructs", "choice", ("-1", True, True)),
        ]
        for i, r in enumerate(rows):                     # the selected row draws last
            if r[0] == "div":
                draw_divider(sc, i, r[1])
            elif i != sel:
                draw_row(sc, i, r[1], "disabled" if r[0] == "dis" else "ng", r[2], r[3])
        draw_row(sc, sel, rows[sel][1], "sel", rows[sel][2], rows[sel][3])
        draw_scroll(sc, 2, VISIBLE, 14)
        if toast:
            draw_toast(sc, TOAST_MAX)
        if dialog:
            draw_dialog(sc, D_TITLE_MAX, [D_LINE_MAX, "This cannot be undone. Back up to the other slot",
                                     "first if you want to keep a copy.", "Continue?"],
                        [("Cancel", False), ("Back Up", False), ("Erase", True)], 2)
        return sc

    scenes["list_versus"] = list_screen("versus", sel=3)
    scenes["list_dialog"] = list_screen("collection", sel=3, dialog=True)
    scenes["list_toast"] = list_screen("options", sel=5, toast=True)

    # widget sheet: every widget in every state
    ws = Scene("solo")
    draw_chrome(ws, layouts["chrome"], "WIDGETS", ["SOLO", "KIT"], [("a", "Change"), ("b", "Back")],
                "Every widget in normal, selected and disabled states.")
    widgets_rows = [("Toggle", "toggle", True), ("Choice", "choice", ("Tournament Mod", False, True)),
                    ("Slider", "slider", (0.72, "72%")), ("Stepper", "stepper", "3:00")]
    i = 0
    for label, kind, val in widgets_rows:
        for state in ("ng", "sel", "disabled"):
            if i >= VISIBLE:
                break
            draw_row(ws, i, "%s %s" % (label, state), state, kind, val)
            i += 1
    scenes["widgets_solo"] = ws
    ws2 = Scene("data")
    draw_chrome(ws2, layouts["chrome"], "WIDGETS", ["DATA", "KIT"], [("a", "Change"), ("b", "Back")],
                "Stepper states, and a divider.")
    for i, state in enumerate(("ng", "sel", "disabled")):
        if state != "sel":
            draw_row(ws2, i, "Stepper %s" % state, state, "stepper", "99:59")
    draw_divider(ws2, 3, "SECTION DIVIDER")
    draw_row(ws2, 1, "Stepper sel", "sel", "stepper", "99:59")
    scenes["widgets_data"] = ws2

    # grid of checkbox cells + cursor variants
    gs = Scene("versus")
    draw_chrome(gs, layouts["chrome"], "ITEM SWITCH", ["VERSUS", "RULES", "ITEM SWITCH"],
                [("a", "Toggle"), ("x", "All On"), ("y", "All Off"), ("b", "Back")],
                "Choose which items can appear.")
    for n in range(12):
        cx, cy = 104 + (n % 6) * 76, 96 + (n // 6) * 68
        on = n % 3 != 1
        sel = n == 7
        dis = n == 11
        if sel:
            gs.quad((cx, cy, cx + 72, cy + 64), "gold_dk", joint="cell_plate")
        dx, dy = LIFT if sel else (0, 0)
        gs.quad((cx + dx, cy + dy, cx + 72 + dx, cy + 64 + dy), "ink", joint="cell")
        gs.quad((cx + 3 + dx, cy + 3 + dy, cx + 69 + dx, cy + 61 + dy), "gold" if sel else "@face",
                joint="cell")
        gs.quad((cx + 4 + dx, cy + 4 + dy, cx + 68 + dx, cy + 60 + dy),
                "#8a8a8a" if (not on or dis) else "@face_hi", opacity=0.25 if dis else (0.45 if not on else 0.9),
                joint="cell")
        gs.text("caption", "64×56", cx + 36 + dx, cy + 36 + dy, "ink", align="centre",
                joint="cell")                             # placeholder: disc art slot
        gs.quad((cx + 50 + dx, cy + dy, cx + 72 + dx, cy + 16 + dy), "gold" if on and not dis else "ink",
                joint="cell_tab")
        if on and not dis:
            gs.quad((cx + 54 + dx, cy + 1 + dy, cx + 68 + dx, cy + 15 + dy), "ink", tex="glyph_check",
                    joint="cell_tab")
    for n, v in enumerate(["default", "p1", "p2", "p3", "p4", "cpu"]):
        draw_cursor(gs, 130 + n * 70, 270, v)
    scenes["grid_cursor"] = gs

    sections = {}
    for s in kit.SECTIONS:
        sections[s] = list_screen(s, sel=3)

    errs, contrast = check(dict(scenes, **{"list_" + s: v for s, v in sections.items()}), mot, layouts)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(device_scale_factor=1)
        tx = Textures()
        for name, sc in scenes.items():
            img = render(page, sc, tx)
            img.save(os.path.join(OUT, "preview", "%s_2x.png" % name))
            downscale_half(img.convert("RGBA")).convert("RGB").save(
                os.path.join(OUT, "preview", "%s_1x.png" % name))
        strip = Image.new("RGB", (640 * 5 // 2 + 16, 240), (0, 0, 0))
        for n, (s, sc) in enumerate(sections.items()):
            img = render(page, sc, tx).resize((320, 240), Image.LANCZOS)
            strip.paste(img, (n * 324, 0))
        strip = strip.resize((5 * 324, 240))
        strip.save(os.path.join(OUT, "preview", "sections_strip.png"))
        browser.close()

    # ---- memory per screen
    def used(sc):
        return {it["tex"] for it in sc.items if it["tex"]}
    rows = {r["name"]: r for r in MANIFEST_ROWS}
    print("kit templates: %s" % ", ".join("%s_layout.json" % n for n in layouts))
    print("motion: %d events" % len(mot["events"]))
    print("memory @2x per composed screen (excl. disc art):")
    for name, sc in scenes.items():
        names = used(sc)
        b = sum(rows[n]["bytes_2x"] for n in names if n in rows)
        extra = [n for n in names if n not in rows]
        for n in extra:                          # section icons: I4 masks, w*h/2 bytes
            w, h = Image.open(tex_path(n)).size
            b += w * h // 2
        print("   %-14s %6.1f KB  %s" % (name, b / 1024, "OVER BUDGET" if b > BUDGET else ""))
        if b > BUDGET:
            errs.append("%s uses %.0f KB > 1 MB" % (name, b / 1024))
    print("worst text contrast across sections:", contrast)
    if errs:
        print("\nCHECKS FAILED (%d):" % len(errs))
        for e in errs[:30]:
            print("  - " + e)
        return 1
    print("\nkit checks ok: slots fit their maxima, title-safe incl. peak motion, "
          "rows fit, contrast in every state and section, memory under budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
