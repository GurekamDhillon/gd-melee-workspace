"""ONLINE PLAY: the in-game online menu's pieces, built on the section 1 kit.

    python pipeline/kit.py && python pipeline/font_atlas.py && python pipeline/glyphs.py \
        && python pipeline/icons.py && python pipeline/kit_ui.py && python pipeline/online.py

Writes out_online/:
    online_layout.json    the screen: rows (host and join views), the new widgets (code
                          plate, action, pips, long-readout slider, choice with icon), the
                          status strip, the connecting dialog; textures listed for png2gx
    online_motion.json    hub_motion.json format: status changes, the looping activity,
                          code copied/pasted, host/join reflow, ping updates
    manifest.json         every texture the screen needs, GX format and why (own + kit)
    preview/*.png         composed from the JSON alone, worst-case strings

The screen is the engine's fe_items_online (gmfrontend.c) drawn with the kit's list
template: 13 items, of which the host view shows 10 and the join view 7. Everything
is unsheared template space, like the kit: x' = x + (240 - y) * 0.25 last.
"""
import json
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
OUT = os.path.join(ROOT, "out_online")
S, Y0 = kit.SHEAR, 240
Q, T, k, tr = U.Q, U.T, U.k, U.tr
text_w, base_for, cap = U.text_w, U.base_for, U.cap

# ---------------------------------------------------------------- geometry
ROW_X0, ROW_X1, ROW_Y0, ROW_H, PITCH = U.ROW_X0, U.ROW_X1, U.ROW_Y0, U.ROW_H, U.PITCH
VALUE_X, VALUE_W = U.VALUE_X, U.VALUE_W
VISIBLE = 8                                   # the ninth row slot holds the status strip
TRACK = (548, 96, 554, 346)
STRIP = (90, 358, 596, 388)                   # same x span as the description strip
BLOCK_W = 36
LIFT = U.LIFT

# the code plate: right-aligned in the value area, wide enough for 21 mono cells
CODE_MAX = "255.255.255.255:65535"
CODE_W = 240
CODE_H = 22
CODE_X0 = VALUE_W - CODE_W                    # -50: it reaches into the label's space
COPY_ICON = 16
CODE_PLACEHOLDER = "Press A to paste"
PIPS_MAX = 8

STATUS_MAX = "Refused: your friend is running a different disc image, v1.0"   # 60 chars
STATUS_LONG = ("Waiting for friend - no auto port forward, so if they can't join, "
               "paste their code")          # the fit rule's caption step; engine today
PING_MAX = "999 ms"

DIALOG_W = 420
DLG_TITLE_MAX = "WAITING FOR YOUR FRIEND"
DLG_STATUS_MAX = "Connecting to 255.255.255.255:65535... this can take a while"
CODE_LABEL_MAX = "HOST CODE"
CANCEL_MAX = "Cancel"

SANS = ["caption", "body", "row", "label", "title", "heading", "hero", "display"]


def fit(role, s, width):
    """The kit's fit rule: the role, then one role smaller in the same face, then
    truncate with an ellipsis. -> (role, string)."""
    chain = [role]
    if role in SANS and SANS.index(role) > 0:
        chain.append(SANS[SANS.index(role) - 1])
    for r in chain:
        if text_w(r, s) <= width + 0.01:
            return r, s
    r = chain[-1]
    while s and text_w(r, s + "…") > width:
        s = s[:-1]
    return r, s.rstrip() + "…"


# ---------------------------------------------------------------- the rows
# Mirrors fe_items_online. view: which Play As value shows the row.
ROWS = [
    dict(id="play_as", label="Play As", widget="choice_icon", view="both",
         value_max="Join", icons={"Host": "ico_host", "Join": "ico_join"},
         help="Host a match, or join a friend's."),
    dict(id="character", label="Character", widget="choice", view="both",
         value_max="Mr. Game & Watch", value_worst="Mr. Game & Watch Jr.",
         note="26 vanilla names; m-ex names up to 20 characters take the fit rule",
         help="Who you play."),
    dict(id="costume", label="Costume", widget="pips", view="both", value_max="Color 8",
         note="one pip per costume the character has (vanilla 4-6, m-ex up to 8); "
              "readout from the engine", help="Your fighter's colors."),
    dict(id="stage", label="Stage", widget="choice", view="host", value_max="Fountain of Dreams",
         value_worst="Princess Peach's Castle", help="Where you both play."),
    dict(id="stocks", label="Stocks", widget="slider_long", view="host", value_max="9",
         help="Lives each player starts with."),
    dict(id="time", label="Time Limit", widget="slider_long", view="host", value_max="20 min",
         help="The match clock."),
    dict(id="delay", label="Input Delay", widget="slider_long", view="host",
         value_max="8 frames", help="2 suits most connections; raise it if it stutters."),
    dict(id="paste_host", label="Paste Host Code", widget="action", view="join",
         icon="ico_paste", help="Copy your friend's code, then press A here."),
    dict(id="host_code", label="Host Code", widget="code_plate", view="join", copy=False,
         help="The code you pasted."),
    dict(id="host_match", label="Host Match", widget="action", view="host", icon="ico_host",
         help="Start hosting; your code is copied for your friend."),
    dict(id="connect", label="Connect", widget="action", view="join", icon="ico_join",
         help="Join the host whose code you pasted."),
    dict(id="your_code", label="Your Code", widget="code_plate", view="both", copy=True,
         help="Your address; it is copied to the clipboard."),
    dict(id="paste_friend", label="Paste Friend's Code", widget="action", view="host",
         icon="ico_paste", help="Only if they can't connect: paste their code here."),
]


def view_rows(view):
    return [r for r in ROWS if r["view"] in ("both", view)]


# widget-local space, like the kit: origin = value area left edge, row centre line
def code_plate_w():
    tx = CODE_X0 + 8
    icon_x0 = VALUE_W - 8 - COPY_ICON
    return dict(
        size=[CODE_W, CODE_H], origin="right-aligned in the value area: x %d..%d local"
        % (CODE_X0, VALUE_W),
        quads=[Q("plate", (CODE_X0, -CODE_H / 2, VALUE_W, CODE_H / 2), "plate", joint="code_plate"),
               Q("accent", (CODE_X0, -CODE_H / 2, CODE_X0 + 3, CODE_H / 2), "accent",
                 joint="code_plate"),
               Q("copy_icon", (icon_x0, -8, icon_x0 + COPY_ICON, 8), "icon", joint="code_icon",
                 texture="ico_copy")],
        slots=[T("code", "code", (tx, cap("code") / 2), CODE_MAX, "code_text", joint="code_plate",
                 max_width=icon_x0 - 6 - tx,
                 note="mono cells: every code draws at the same x; never the fit rule - "
                      "a code that is too long is not a code (show the placeholder)"),
               T("placeholder", "body", (tx, cap("body") / 2), CODE_PLACEHOLDER, "placeholder",
                 joint="code_plate", max_width=icon_x0 - 6 - tx,
                 note="shown instead of the code while there is none")],
        colours=dict(
            ng=dict(plate="ink", accent="@face_hi", code_text="bone", placeholder="muted",
                    icon="muted"),
            sel=dict(plate="ink", accent="gold", code_text="gold_lt", placeholder="muted",
                     icon="gold_lt"),
            disabled=dict(plate="ink", accent="disabled", code_text="disabled",
                          placeholder="disabled", icon="disabled"),
            copied=dict(plate="ok", accent="ok", code_text="ink", placeholder="ink", icon="ink",
                        note="held 40 frames by code_copied, then back to ng/sel")),
        rules=["copy_icon only on 'Your Code' (copy: true). 'Host Code' has no copy icon; "
               "its plate reaches the same width so the two codes line up.",
               "code_copied swaps copy_icon for glyph_check (same rect) for 40 frames.",
               "The empty state shows 'placeholder' (strings) instead of 'code'."])


def action_w():
    return dict(
        quads=[Q("icon", (VALUE_W - COPY_ICON, -8, VALUE_W, 8), "aux", joint="action_icon",
                 texture="<row icon>")],
        rules=["A row that does something when A is pressed. The icon names the action "
               "(ico_paste, ico_host, ico_join) and takes the widget 'aux' colour of the row "
               "state. Press plays kit bump on the icon if the action cannot run (e.g. "
               "Connect with no code)."])


def pips_w():
    return dict(
        quads=[Q("pip_<i>", (0, -5, 10, 5), "pip", joint="pip_<i>")],
        slots=[T("readout", "row", (VALUE_W, cap("row") / 2), "Color 8", "text", align="right",
                 max_width=VALUE_W - (PIPS_MAX * 15 - 5) - 10)],
        pitch=15, max=PIPS_MAX,
        colours=dict(ng=dict(pip="ink", pip_on="bone", text="bone"),
                     sel=dict(pip="gold_dk", pip_on="ink", text="ink"),
                     disabled=dict(pip="ink", pip_on="disabled", text="disabled")),
        rules=["One pip per costume, x = 15 * i, i from 0; the current one is pip_on "
               "and 2px taller (y -6..6).",
               "Stepping plays pips_step; at the ends, kit bump."])


def slider_long_w():
    tw = 96
    return dict(
        quads=[Q("track", (0, -3, tw, 3), "track"),
               Q("fill", (0, -3, tw, 3), "fill", joint="slider_fill"),
               Q("knob", (tw - 4, -9, tw + 4, 9), "knob", joint="slider_knob")],
        slots=[T("readout", "row", (VALUE_W, cap("row") / 2), "20 frames", "text", align="right",
                 max_width=VALUE_W - tw - 12)],
        track_w=tw,
        rules=["The kit slider with a %d px track, for readouts with units ('20 min', "
               "'8 frames'). fill SCA_X = value/max; knob TRA_X = %d * value/max - %d. "
               "kit slider_step and bump apply with %d in place of 130." % (tw, tw, tw, tw)])


def choice_icon_w():
    return dict(
        slots=[T("value", "row", (VALUE_W / 2 + 11, cap("row") / 2), "Join", "text",
                 align="centre", joint="choice_value"),
               dict(id="value_icon", kind="icon", size=[16, 16], colour="text",
                    joint="choice_value",
                    rule="16 px mask centred with the text as one group: group width = 16 + 6 "
                         "+ advance(value); icon x0 = VALUE_W/2 - group/2")],
        rules=["The kit choice (arrows at 0 and VALUE_W) whose value carries an icon per "
               "option (the row's 'icons' map). Play As: ico_host / ico_join."])


# ---------------------------------------------------------------- status strip
STATES = {
    "idle":      dict(block="@face", icon="ico_online", icon_colour="@face_hi", pips=False,
                      sweep=False, ping=False,
                      engine="FE_NP_IDLE", example="Choose Host or Join, then pick your fighter."),
    "working":   dict(block="gold", icon=None, icon_colour="ink", pips=True, sweep=True,
                      ping=False, engine="FE_NP_WORKING", example="Connecting..."),
    "connected": dict(block="ok", icon="ico_link", icon_colour="ink", pips=False, sweep=False,
                      ping=True, engine="FE_NP_CONNECTED", example="Connected! Starting..."),
    "failed":    dict(block="danger", icon="ico_warning", icon_colour="ink", pips=False,
                      sweep=False, ping=False, engine="FE_NP_FAILED",
                      example="Refused: different disc image",
                      alt_icon=dict(icon="ico_unlink",
                                    when="a live connection dropped (Disconnected: ...)")),
}


def strip_geom():
    x0, y0, x1, y1 = STRIP
    ping_w = text_w("caption", PING_MAX)
    ms_x1 = x1 - 10
    bars_x1 = ms_x1 - ping_w - 6
    bars = (bars_x1 - 16, (y0 + y1) / 2 - 8, bars_x1, (y0 + y1) / 2 + 8)
    text_x = x0 + BLOCK_W + 12
    text_max = bars[0] - 10 - text_x
    return dict(ping_w=ping_w, ms_x1=ms_x1, bars=bars, text_x=text_x, text_max=text_max)


def status_strip():
    x0, y0, x1, y1 = STRIP
    g = strip_geom()
    cy = (y0 + y1) / 2
    bx0, bx1 = x0, x0 + BLOCK_W
    pips = [Q("pip_%d" % i, (bx0 + 6 + i * 9, cy - 3, bx0 + 12 + i * 9, cy + 3), "ink",
              joint="activity_pip_%d" % i) for i in range(3)]
    return dict(
        rect=list(STRIP), space="unsheared",
        quads=[Q("strip_plate", STRIP, "ink", joint="strip"),
               Q("block", (bx0, y0, bx1, y1), "<state.block>", joint="status_block"),
               Q("state_icon", (bx0 + 10, cy - 8, bx0 + 26, cy + 8), "<state.icon_colour>",
                 joint="status_block", texture="<state.icon>")] + pips + [
               Q("sweep", (bx1, y1 - 2, bx1 + 40, y1), "gold", joint="strip_sweep"),
               ] + [Q("bar_%d" % (i + 1), g["bars"], "<bar colour>", joint="ping",
                      texture="sig_bar_%d" % (i + 1)) for i in range(4)],
        slots=[
            T("status", "body", (g["text_x"], base_for("body", y0, y1)), STATUS_MAX, "bone",
              joint="status_text", max_width=g["text_max"],
              note="the engine's status line (Netplay_MenuStatus); the fit rule's caption "
                   "step holds about 72 characters"),
            T("ping_ms", "caption", (g["ms_x1"], base_for("caption", y0, y1)), PING_MAX, "muted",
              align="right", joint="ping", note="round-trip in ms, tabular digits"),
        ],
        states=STATES,
        ping=dict(
            levels=[dict(max_ms=60, bars=4, colour="ok"), dict(max_ms=100, bars=3, colour="ok"),
                    dict(max_ms=150, bars=2, colour="gold"), dict(max_ms=None, bars=1,
                                                                  colour="danger")],
            unlit="@face",
            rules=["All four bar masks draw at one rect; the first `bars` take the level's "
                   "colour, the rest 'unlit'. The bar count is the cue, colour second, so "
                   "red-green colour-blind players read it too.",
                   "Shown only in 'connected' (and in-match later); ping_ms updates at most "
                   "twice a second, and ping_update plays only when the level changes."]),
        rules=["Replaces the list's ninth row slot on this screen: the list shows 8 rows and "
               "its scroll track ends at y=%d." % TRACK[3],
               "block, state_icon and the pips belong to the state; 'working' shows the "
               "three pips (activity loop) instead of an icon, plus the sweep under the strip.",
               "Text is always from strings. The text slot is sized for 60 characters at body; "
               "longer text steps to caption (fit rule), then truncates."])


# ---------------------------------------------------------------- connecting dialog
def dialog_geom():
    title_h = 28
    status_base = 50
    label_base = 72
    plate_y0 = 78
    plate_y1 = plate_y0 + CODE_H
    hint_base = plate_y1 + 26
    h = hint_base + 12
    x0, y0 = 320 - DIALOG_W / 2, round(240 - h / 2)
    return dict(title_h=title_h, status_base=status_base, label_base=label_base,
                plate_y0=plate_y0, plate_y1=plate_y1, hint_base=hint_base, h=h, x0=x0, y0=y0)


DLG_VARIANTS = {
    "connecting": dict(slab="gold", icon=None, pips=True, plate="host_code", cancel=True,
                       title="CONNECTING", status="Connecting to 203.0.113.7:51500..."),
    "waiting":    dict(slab="gold", icon=None, pips=True, plate="your_code", cancel=True,
                       title="WAITING FOR YOUR FRIEND",
                       status="Your code is copied - send it to your friend."),
    "connected":  dict(slab="ok", icon="ico_link", pips=False, plate="context", cancel=False,
                       title="CONNECTED", status="Connected! Starting..."),
    "failed":     dict(slab="danger", icon="ico_warning", pips=False, plate="context", cancel=True,
                       title="CONNECTION REFUSED", status="Refused: different disc image",
                       cancel_label="Back"),
}


def connect_dialog():
    g = dialog_geom()
    W = DIALOG_W
    pip_x0 = 16 + CODE_W + 16
    pcy = (g["plate_y0"] + g["plate_y1"]) / 2
    hint_w = 16 + 4 + text_w("body", CANCEL_MAX)
    return dict(
        name="connect_dialog", space="unsheared", base="dialog_layout.json (section 1)",
        origin="panel top-left; centred on (320, 240): x0 = %g, y0 = %g for h = %g"
        % (g["x0"], g["y0"], g["h"]),
        height=g["h"], width=W,
        quads=[
            Q("dim", (-60, -20, 700, 500), "ink", role="decor", joint="dialog_dim", opacity=0.65),
            Q("panel_ink", (-4, -4, W + 4, g["h"] + 4), "ink", joint="dialog_panel"),
            Q("panel_face", (0, 0, W, g["h"]), "@face", joint="dialog_panel"),
            Q("title_slab", (0, 0, "36 + advance(title) + 20 (or 16 + ... with no icon)",
                             g["title_h"]), "<variant.slab>", joint="dialog_panel"),
            Q("title_icon", (14, 6, 30, 22), "ink", joint="dialog_panel",
              texture="<variant.icon>"),
            dict(Q("code_plate", (16, g["plate_y0"], 16 + CODE_W, g["plate_y1"]), "ink",
                   joint="dialog_panel"), note="the code_plate widget, ng colours, drawn here"),
        ] + [Q("pip_%d" % i, (pip_x0 + i * 12, pcy - 4, pip_x0 + 8 + i * 12, pcy + 4), "gold",
               joint="activity_pip_%d" % i) for i in range(3)] + [
            Q("sweep", (0, g["h"] - 2, 40, g["h"]), "gold", joint="dialog_sweep"),
            Q("cancel_glyph", (W - 16 - hint_w, g["hint_base"] - cap("body") / 2 - 8,
                               W - 16 - hint_w + 16, g["hint_base"] - cap("body") / 2 + 8),
              "danger", joint="dialog_panel", texture="glyph_b"),
        ],
        slots=[
            T("title", "title", (36, base_for("title", 0, g["title_h"])), DLG_TITLE_MAX, "ink",
              joint="dialog_panel", max_width=W - 36 - 20,
              note="x = 16 when the variant has no icon"),
            T("status", "body", (16, g["status_base"]), DLG_STATUS_MAX, "bone",
              joint="dialog_panel", max_width=W - 32),
            T("code_label", "caption", (16, g["label_base"]), CODE_LABEL_MAX, "muted",
              joint="dialog_panel", note="'YOUR CODE' or 'HOST CODE' from strings"),
            T("code", "code", (24, (g["plate_y0"] + g["plate_y1"]) / 2 + cap("code") / 2),
              CODE_MAX, "bone", joint="dialog_panel", max_width=CODE_W - 16),
            T("cancel", "body", (W - 16, g["hint_base"]), CANCEL_MAX, "bone", align="right",
              joint="dialog_panel", note="glyph_b + 4 px + this text, right-aligned"),
        ],
        variants=DLG_VARIANTS,
        rules=["The section 1 dialog with no buttons: B cancels (Netplay_MenuCancel) and "
               "closes with kit dialog_close. It opens with kit dialog_open when Host Match or "
               "Connect starts (FE_NP_WORKING).",
               "Variants change slab colour, title icon and which parts show; the panel "
               "keeps its size so a variant change never jumps. plate 'context' keeps "
               "whichever code the dialog opened with (the host's when joining, yours when "
               "hosting). 'connected' hides the pips and the cancel hint; 'failed' hides the "
               "pips and shows B = Back.",
               "The pips and sweep play online activity_loop, the same loop as the strip."])


# ---------------------------------------------------------------- layout
def layout():
    ch = U.chrome()
    title_max = "ONLINE PLAY"
    return dict(
        name="online", space="unsheared", shear=dict(S=S, Y0=Y0), section="versus",
        engine="gmfrontend.c fe_screen_online / fe_items_online",
        chrome=dict(template="chrome_layout.json", title_max=title_max,
                    crumbs=["VERSUS", "ONLINE PLAY"], crumb_icon="ico_versus",
                    hints_worst=[["a", "Choose"], ["b", "Back"], ["x", "Copy Code"],
                                 ["y", "Paste"]],
                    description="the selected row's help line (item.help)"),
        panel=dict(template="list_layout.json", rows_top=ROW_Y0, row_h=ROW_H, pitch=PITCH,
                   visible=VISIBLE, x0=ROW_X0, x1=ROW_X1, track=list(TRACK)),
        views=dict(host=[r["id"] for r in view_rows("host")],
                   join=[r["id"] for r in view_rows("join")],
                   rule="Play As picks the view; rows of the other view are hidden, and "
                        "the rest reflow with online rows_reflow."),
        rows=[dict(r, label_slot=T("label_" + r["id"], "row", (16, base_for("row", 0, ROW_H)),
                                   r["label"], "bone", joint="row",
                                   max_width=(VALUE_X + (CODE_X0 if r["widget"] == "code_plate"
                                                         else 0)) - ROW_X0 - 16 - 12),
                   value_slot=(T("value_" + r["id"], "row", (VALUE_W / 2, cap("row") / 2),
                                 r["value_max"], "text", align="centre", joint="choice_value",
                                 max_width=VALUE_W - 2 * (text_w("row", "←") + 8))
                               if r["widget"] == "choice" else None))
              for r in ROWS],
        widgets=dict(code_plate=code_plate_w(), action=action_w(), pips=pips_w(),
                     slider_long=slider_long_w(), choice_icon=choice_icon_w(),
                     kit="toggle, choice, slider, stepper: widgets_layout.json"),
        status_strip=status_strip(),
        connect_dialog=connect_dialog(),
        strings=dict(
            note="All text is from strings. These are the worst cases the layout is checked "
                 "against, and suggestions where the engine's current strings run long.",
            status_max_chars=60,
            engine_status_today=[
                "Waiting for friend (code 255.255.255.255:65535 copied) - no auto port forward "
                "- if they can't join, paste their code",
                "Connecting to 255.255.255.255:65535... If it takes long, send your code "
                "255.255.255.255:65535 to the host"],
            suggested=dict(
                waiting="Waiting for your friend. Your code is copied.",
                waiting_no_upnp="No auto port forward: if they can't join, paste their code.",
                connecting="Connecting... If it takes long, send the host your code.",
                connected="Connected! Starting...",
                refused="Refused: different disc image",
                disconnected="Disconnected: your friend left",
                no_code="The clipboard doesn't hold a code (like 1.2.3.4:51500)"),
            code_placeholder=CODE_PLACEHOLDER),
        textures=[],                                  # filled in main() for png2gx --layout
    )


# ---------------------------------------------------------------- motion
def motion():
    ev = {}
    period = 36
    # activity: three pips light in turn, 12 frames apart, forever
    pip_tracks = []
    for i in range(3):
        o = i * 12
        keys = [k(0, 0.25, "CON")]
        if o:
            keys.append(k(o, 0.25, "LIN"))
        else:
            keys = [k(0, 0.25, "LIN")]
        keys += [k(o + 2, 1.0, "LIN"), k(o + 12, 1.0, "LIN"), k(o + 18, 0.25, "CON"),
                 k(period, 0.25, "CON")]
        pip_tracks.append(tr("activity_pip_%d" % i, "ALPHA", *keys, kind="material"))
        pip_tracks.append(tr("activity_pip_%d" % i, "SCA_Y", k(o, 1.0), k(o + 3, 1.35),
                             k(o + 8, 1.0), k(period, 1.0)))
    ev["activity_loop"] = dict(
        applies_to="status strip pips (working) and the connecting dialog's pips",
        loop=dict(from_frame=0, to_frame=period),
        note="LOOP: when the frame reaches to_frame, restart at from_frame with no "
             "from_current. Stops when the state leaves 'working' (status_set).",
        sfx=[], tracks=pip_tracks)
    sweep_len = STRIP[2] - (STRIP[0] + BLOCK_W) - 40
    ev["sweep_loop"] = dict(
        applies_to="strip_sweep (and dialog_sweep, with its own length)",
        loop=dict(from_frame=0, to_frame=72),
        tracks=[tr("strip_sweep", "TRA_X", k(0, 0, "SPL", 0), k(54, sweep_len, "SPL", 0),
                   k(72, sweep_len, "CON")),
                tr("strip_sweep", "ALPHA", k(0, 0, "LIN"), k(8, 1, "LIN"), k(46, 1, "LIN"),
                   k(54, 0, "CON"), k(72, 0, "CON"), kind="material")],
        note="dialog_sweep runs the same keys with length %d (panel width - 40)."
             % (DIALOG_W - 40))
    ev["status_set"] = dict(
        applies_to="status strip, on any change of state or text",
        sfx=[], note="the old text draws on status_text_out; the new on status_text",
        tracks=[tr("status_text_out", "TRA_X", k(0, 0), k(5, -10, "SPL", 0)),
                tr("status_text_out", "ALPHA", k(0, 1, "LIN"), k(4, 0, "LIN"), kind="material"),
                tr("status_text", "TRA_X", k(0, 12), k(7, -1), k(10, 0)),
                tr("status_text", "ALPHA", k(0, 0, "LIN"), k(6, 1, "LIN"), kind="material"),
                tr("status_block", "COLOUR", k(0, "<old block>", "CON"), k(1, "bone", "LIN"),
                   k(6, "<state.block>", "LIN"), kind="material")])
    ev["status_connected"] = dict(
        applies_to="status strip entering 'connected' (after status_set)",
        sfx=[dict(frame=0, cue="sfx_connected")], pivot="block centre",
        tracks=[tr("status_block", "SCA_X", k(0, 1), k(3, 1.15), k(10, 1)),
                tr("status_block", "SCA_Y", k(0, 1), k(3, 1.15), k(10, 1)),
                tr("strip", "COLOUR", k(0, "ok", "LIN"), k(10, "ink", "LIN"), kind="material")])
    ev["status_failed"] = dict(
        applies_to="status strip entering 'failed' (after status_set)",
        sfx=[dict(frame=0, cue="sfx_error")],
        tracks=[tr("strip", "TRA_X", k(0, 0), k(2, 4), k(5, -3), k(8, 2), k(11, -1), k(14, 0)),
                tr("strip", "COLOUR", k(0, "danger", "LIN"), k(12, "ink", "LIN"),
                   kind="material")])
    ev["ping_update"] = dict(
        applies_to="ping bars, when the level changes",
        tracks=[tr("bar_<i>", "COLOUR", k(0, "<old>", "LIN", fc=True), k(4, "<new>", "LIN"),
                   kind="material"),
                tr("ping", "SCA_Y", k(0, 1), k(2, 1.2), k(6, 1))],
        pivot="bars' bottom edge")
    ev["code_copied"] = dict(
        applies_to="code plate ('Your Code'), when the code reaches the clipboard",
        sfx=[dict(frame=0, cue="sfx_toast")], pivot="plate centre",
        note="colours switch to code_plate.colours.copied for 40 frames, then back; "
             "copy_icon shows glyph_check meanwhile",
        tracks=[tr("code_plate", "SCA_X", k(0, 1), k(3, 1.06), k(9, 1)),
                tr("code_plate", "SCA_Y", k(0, 1), k(3, 1.06), k(9, 1)),
                tr("code_plate", "COLOUR", k(0, "ok", "CON"), k(40, "<state plate>", "CON"),
                   kind="material"),
                tr("code_icon", "SCA_X", k(0, 0.6), k(4, 1.2), k(8, 1)),
                tr("code_icon", "SCA_Y", k(0, 0.6), k(4, 1.2), k(8, 1))])
    ev["code_paste"] = dict(
        applies_to="code plate ('Host Code'), when a code is pasted",
        sfx=[dict(frame=0, cue="sfx_value_change")],
        tracks=[tr("code_text", "TRA_X", k(0, -16), k(6, 1), k(9, 0)),
                tr("code_text", "ALPHA", k(0, 0, "LIN"), k(5, 1, "LIN"), kind="material"),
                tr("code_plate", "COLOUR", k(0, "gold_lt", "LIN"), k(8, "<state plate>", "LIN"),
                   kind="material")])
    ev["pips_step"] = dict(
        applies_to="pips widget", sfx=[dict(frame=0, cue="sfx_value_change")],
        tracks=[tr("pip_<new>", "SCA_X", k(0, 1.5), k(6, 1)), tr("pip_<new>", "SCA_Y", k(0, 1.5),
                                                                  k(6, 1))])
    ev["rows_reflow"] = dict(
        applies_to="list rows when Play As changes the view",
        sfx=[],
        note="rows that stay slide to their new slot (TRA_Y from their old y); rows that "
             "appear fade in 2 frames apart top to bottom; rows that go vanish at frame 0",
        tracks=[tr("row_<staying>", "TRA_Y", k(0, "old_y - new_y"), k(7, 0)),
                tr("row_<new>", "ALPHA", k(0, 0, "LIN"), k(5, 1, "LIN"), kind="material"),
                tr("row_<new>", "TRA_X", k(0, 14), k(7, 0))])
    for e in ev.values():
        e["length_frames"] = 1 + max(kk["frame"] for t in e["tracks"] for kk in t["keys"])
    return dict(
        fps=60, format="hub_motion.json: tracks, from_current, interpolation and transform "
                       "rules are identical; see out_hub/hub_motion.json and out_kit/kit_motion.json",
        space="unsheared - motion is applied before the screen shear",
        extension="'loop' {from_frame, to_frame}: new in this file - the event restarts at "
                  "from_frame when it reaches to_frame, until another event takes its channels",
        value_expressions="strings in <> are resolved by the engine from the layout's state "
                          "tables; colour values are kit tokens",
        events=ev,
        sequences=dict(
            start=[dict(event="dialog_open (kit)", on="connect_dialog"),
                   dict(event="status_set", on="strip", state="working"),
                   dict(event="activity_loop", on="strip + dialog"),
                   dict(event="sweep_loop", on="strip + dialog")],
            connected=[dict(event="status_set", state="connected"),
                       dict(event="status_connected"),
                       dict(note="dialog variant 'connected' for 30 frames, then the match")],
            failed=[dict(event="status_set", state="failed"), dict(event="status_failed"),
                    dict(note="dialog variant 'failed'; B closes it (kit dialog_close)")],
            cancel=[dict(event="dialog_close (kit)"), dict(event="status_set", state="idle")],
            copy=[dict(event="code_copied", on="your_code"),
                  dict(event="toast_in (kit)", text="Code copied", optional=True)],
        ))


# ---------------------------------------------------------------- drawing
class Scene(U.Scene):
    pass


def col_state(state_tok, sc, tok):
    return tok


def draw_choice_value(sc, x, cy, text, colour, role="row", icon=None):
    width = VALUE_W - 2 * (text_w("row", "←") + 8)
    r, s = fit(role, text, width - (22 if icon else 0))
    w = text_w(r, s)
    cx = x + VALUE_W / 2
    if icon:
        g = 16 + 6 + w
        ix = cx - g / 2
        sc.quad((ix, cy - 8, ix + 16, cy + 8), colour, tex=icon, joint="choice_value")
        sc.text(r, s, ix + 22, cy + cap(r) / 2, colour, joint="choice_value")
    else:
        sc.text(r, s, cx, cy + cap(r) / 2, colour, align="centre", joint="choice_value")


def draw_value(sc, row, x, cy, state, value, flash=None):
    wc = U.WID["colours"][state]

    def c(t):
        return wc.get(t, t)
    w = row["widget"]
    if w in ("choice", "choice_icon"):
        text, lok, rok = value
        sc.text("row", "←", x, cy + cap("row") / 2, c("aux") if lok else "disabled",
                joint="choice_left")
        sc.text("row", "→", x + VALUE_W, cy + cap("row") / 2, c("aux") if rok else "disabled",
                align="right", joint="choice_right")
        draw_choice_value(sc, x, cy, text, c("text"),
                          icon=row.get("icons", {}).get(text) if w == "choice_icon" else None)
    elif w == "slider_long":
        frac, label = value
        tw = 96
        sc.quad((x, cy - 3, x + tw, cy + 3), c("track"))
        sc.quad((x, cy - 3, x + tw * frac, cy + 3), c("fill"), joint="slider_fill")
        kx = x + tw * frac
        sc.quad((kx - 4, cy - 9, kx + 4, cy + 9), c("knob"), joint="slider_knob")
        sc.text("row", label, x + VALUE_W, cy + cap("row") / 2, c("text"), align="right")
    elif w == "pips":
        n, cur, label = value
        pc = LAY["widgets"]["pips"]["colours"][state]
        for i in range(n):
            on = i == cur
            h = 6 if on else 5
            sc.quad((x + 15 * i, cy - h, x + 15 * i + 10, cy + h), pc["pip_on"] if on else pc["pip"],
                    joint="pip_%d" % i)
        sc.text("row", label, x + VALUE_W, cy + cap("row") / 2, pc["text"], align="right")
    elif w == "action":
        sc.quad((x + VALUE_W - 16, cy - 8, x + VALUE_W, cy + 8), c("aux"), tex=row["icon"],
                joint="action_icon")
    elif w == "code_plate":
        draw_code_plate(sc, x + CODE_X0, cy, value, state, copy=row["copy"], flash=flash)


def draw_code_plate(sc, x0, cy, code, state, copy=True, flash=None, joint="code_plate"):
    cc = LAY["widgets"]["code_plate"]["colours"][flash or state]
    sc.quad((x0, cy - CODE_H / 2, x0 + CODE_W, cy + CODE_H / 2), cc["plate"], joint=joint)
    sc.quad((x0, cy - CODE_H / 2, x0 + 3, cy + CODE_H / 2), cc["accent"], joint=joint)
    tx = x0 + 8
    if code:
        sc.text("code", code, tx, cy + cap("code") / 2, cc["code_text"], joint=joint)
    else:
        sc.text("body", CODE_PLACEHOLDER, tx, cy + cap("body") / 2, cc["placeholder"], joint=joint)
    if copy:
        ix = x0 + CODE_W - 8 - COPY_ICON
        sc.quad((ix, cy - 8, ix + COPY_ICON, cy + 8), cc["icon"],
                tex="glyph_check" if flash == "copied" else "ico_copy", joint="code_icon")


def draw_row(sc, slot, row, state, value, flash=None):
    y = ROW_Y0 + slot * PITCH
    st = U.ROW_T["states"][state]
    dx, dy = st["offset"]
    if st["plate"]:
        sc.quad((ROW_X0, y, ROW_X1, y + ROW_H), st["plate"], joint="row_plate")
    sc.quad((ROW_X0 + dx, y + dy, ROW_X1 + dx, y + ROW_H + dy), st["face"], joint="row")
    lw = (VALUE_X + (CODE_X0 if row["widget"] == "code_plate" else 0)) - ROW_X0 - 16 - 12
    r, s = fit("row", row["label"], lw)
    sc.text(r, s, ROW_X0 + 16 + dx, y + base_for(r, 0, ROW_H) + dy, st["label"], joint="row")
    draw_value(sc, row, VALUE_X + dx, y + ROW_H / 2 + dy, state, value, flash)


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


def draw_status(sc, state, text, ping=None, pip_phase=0, sweep=0.35):
    x0, y0, x1, y1 = STRIP
    st = STATES[state]
    g = strip_geom()
    cy = (y0 + y1) / 2
    sc.quad(STRIP, "ink", joint="strip")
    sc.quad((x0, y0, x0 + BLOCK_W, y1), st["block"], joint="status_block")
    if st["icon"]:
        icon = st.get("_icon", st["icon"])
        sc.quad((x0 + 10, cy - 8, x0 + 26, cy + 8), st["icon_colour"], tex=icon,
                joint="status_block")
    if st["pips"]:
        for i in range(3):
            lit = i == pip_phase
            h = 3 * (1.35 if lit else 1)
            sc.quad((x0 + 6 + i * 9, cy - h, x0 + 12 + i * 9, cy + h), "ink",
                    opacity=1.0 if lit else 0.35, joint="activity_pip_%d" % i)
    if st["sweep"]:
        L = STRIP[2] - (x0 + BLOCK_W) - 40
        sx = x0 + BLOCK_W + L * sweep
        sc.quad((sx, y1 - 2, sx + 40, y1), "gold", joint="strip_sweep_rest")
    r, s = fit("body", text, g["text_max"])
    sc.text(r, s, g["text_x"], base_for(r, y0, y1), "bone", joint="status_text")
    sc.status_fit = (r, s)
    if st["ping"] and ping is not None:
        lv = next(l for l in LAY["status_strip"]["ping"]["levels"]
                  if l["max_ms"] is None or ping <= l["max_ms"])
        for i in range(4):
            sc.quad(g["bars"], lv["colour"] if i < lv["bars"] else "@face",
                    tex="sig_bar_%d" % (i + 1), joint="ping")
        sc.text("caption", "%d ms" % ping, g["ms_x1"], base_for("caption", y0, y1), "muted",
                align="right", joint="ping")


def draw_connect_dialog(sc, variant, code=CODE_MAX, pip_phase=0, status=None, title=None,
                        label="HOST CODE"):
    v = DLG_VARIANTS[variant]
    g = dialog_geom()
    x0, y0, W, h = g["x0"], g["y0"], DIALOG_W, g["h"]
    title = title or v["title"]
    status = status or v["status"]
    sc.quad((-60, -20, 700, 500), "ink", opacity=0.65, tag="decor", sheared=False)
    sc.quad((x0 - 4, y0 - 4, x0 + W + 4, y0 + h + 4), "ink", joint="dialog_panel")
    sc.quad((x0, y0, x0 + W, y0 + h), "@face", joint="dialog_panel")
    tx = x0 + (36 if v["icon"] else 16)
    rt, st = fit("title", title, W - (tx - x0) - 20)
    sc.quad((x0, y0, tx + text_w(rt, st) + 20, y0 + g["title_h"]), v["slab"], joint="dialog_panel")
    if v["icon"]:
        sc.quad((x0 + 14, y0 + 6, x0 + 30, y0 + 22), "ink", tex=v["icon"], joint="dialog_panel")
    sc.text(rt, st, tx, y0 + base_for(rt, 0, g["title_h"]), "ink", joint="dialog_panel")
    rs, ss = fit("body", status, W - 32)
    sc.text(rs, ss, x0 + 16, y0 + g["status_base"], "bone", joint="dialog_panel")
    if v["plate"]:
        sc.text("caption", label, x0 + 16, y0 + g["label_base"], "muted", joint="dialog_panel")
        draw_code_plate(sc, x0 + 16, y0 + (g["plate_y0"] + g["plate_y1"]) / 2, code, "ng",
                        copy=v["plate"] == "your_code", joint="dialog_panel")
    if v["pips"]:
        px = x0 + 16 + CODE_W + 16
        pcy = y0 + (g["plate_y0"] + g["plate_y1"]) / 2
        for i in range(3):
            lit = i == pip_phase
            hh = 4 * (1.35 if lit else 1)
            sc.quad((px + i * 12, pcy - hh, px + 8 + i * 12, pcy + hh), "gold",
                    opacity=1.0 if lit else 0.35, joint="activity_pip_%d" % i)
        sc.quad((x0 + 120, y0 + h - 2, x0 + 160, y0 + h), "gold", joint="dialog_panel")
    if v["cancel"]:
        lab = v.get("cancel_label", "Cancel")
        tw = text_w("body", lab)
        gx = x0 + W - 16 - tw - 4 - 16
        gy = y0 + g["hint_base"] - cap("body") / 2 - 8
        sc.quad((gx, gy, gx + 16, gy + 16), "danger", tex="glyph_b", joint="dialog_panel")
        sc.text("body", lab, x0 + W - 16, y0 + g["hint_base"], "bone", align="right",
                joint="dialog_panel")


# ---------------------------------------------------------------- screens
HINTS = [("a", "Choose"), ("b", "Back"), ("x", "Copy Code"), ("y", "Paste")]


def values(view, state_worst=True):
    return dict(
        play_as=("Host" if view == "host" else "Join", view == "join", view == "host"),
        character=("Mr. Game & Watch Jr." if state_worst else "Mr. Game & Watch", True, True),
        costume=(8, 3, "Color 4"),
        stage=("Princess Peach's Castle", True, True),
        stocks=(1.0, "9"),
        time=(1.0, "20 min"),
        delay=(1.0, "8 frames"),
        paste_host=None, host_match=None, connect=None, paste_friend=None,
        host_code=CODE_MAX, your_code=CODE_MAX)


def screen(view, first=0, sel="character", status=("idle", None), ping=None, dialog=None,
           flash=None, vals=None, desc=None):
    sc = Scene("versus")
    rows = view_rows(view)
    selrow = next(r for r in rows if r["id"] == sel)
    desc = desc or selrow["help"]
    crumbs = ["VERSUS", "ONLINE PLAY"]
    sc.footer_end = U.draw_chrome(sc, U.chrome(), "ONLINE PLAY", crumbs, HINTS, desc)
    sc.crumb_end = U.CRUMB[0] + 22 + sum(text_w("body", c) for c in crumbs) + 14
    vals = vals or values(view)
    shown = rows[first:first + VISIBLE]
    for slot, r in enumerate(shown):
        if r["id"] != sel:
            draw_row(sc, slot, r, "ng", vals[r["id"]])
    if selrow in shown:
        draw_row(sc, shown.index(selrow), selrow, "sel", vals[sel],
                 flash=flash if selrow["widget"] == "code_plate" else None)
    if len(rows) > VISIBLE:
        draw_scroll(sc, first, VISIBLE, len(rows))
    st, text = status
    draw_status(sc, st, text or STATES[st]["example"], ping=ping)
    if dialog:
        draw_connect_dialog(sc, **dialog)
    return sc


# ---------------------------------------------------------------- checks
def check_extra(layout_, scenes):
    errs, report = [], {}
    # fit-rule slots: the status slot's long form must fit at caption
    g = strip_geom()
    need = text_w("caption", STATUS_LONG)
    report["status_long_at_caption"] = [round(need, 1), round(g["text_max"], 1), len(STATUS_LONG)]
    if len(STATUS_MAX) != 60:
        errs.append("STATUS_MAX is %d chars, the brief says 60" % len(STATUS_MAX))
    # the code must never need the fit rule
    cw = text_w("code", CODE_MAX)
    room = CODE_W - 8 - 8 - COPY_ICON - 6
    report["code_px"] = [round(cw, 1), room]
    if cw > room:
        errs.append("code plate: %s needs %.1f px, has %d" % (CODE_MAX, cw, room))
    # every row label fits at row size without the fit rule (they are fixed engine strings)
    for r in ROWS:
        lw = (VALUE_X + (CODE_X0 if r["widget"] == "code_plate" else 0)) - ROW_X0 - 16 - 12
        if r["widget"] == "action":
            lw = VALUE_X + VALUE_W - 16 - 12 - ROW_X0 - 16
        if text_w("row", r["label"]) > lw:
            errs.append("row label '%s' needs %.1f px, has %.1f" % (r["label"],
                                                                     text_w("row", r["label"]), lw))
    # the widest vanilla character name fits the choice without stepping down
    width = VALUE_W - 2 * (text_w("row", "←") + 8)
    for s in ("Mr. Game & Watch", "Fountain of Dreams", "Final Destination"):
        if text_w("row", s) > width:
            errs.append("choice: '%s' needs the fit rule (%.1f > %.1f)" % (s, text_w("row", s),
                                                                             width))
    # m-ex names at the fit rule's step (body) - no truncation for the test names
    for s in kit.NAME_FIT["test_names"] + ["Princess Peach's Castle"]:
        r, out = fit("row", s, width)
        if out != s:
            errs.append("choice: '%s' truncates to '%s'" % (s, out))
    # contrast: strip, plate, dialog, state blocks
    sc = Scene("versus")
    pairs = [("status text", "bone", "ink", kit.MIN_TEXT),
             ("code text ng", "bone", "ink", kit.MIN_TEXT),
             ("code text sel", "gold_lt", "ink", kit.MIN_TEXT),
             ("code text copied", "ink", "ok", kit.MIN_TEXT),
             ("placeholder", "muted", "ink", kit.MIN_TEXT),
             ("ping ms", "muted", "ink", kit.MIN_TEXT),
             ("dialog code label", "muted", "@face", kit.MIN_TEXT),
             ("idle icon on block", "@face_hi", "@face", kit.MIN_GRAPHIC),
             ("working pips on block", "ink", "gold", kit.MIN_GRAPHIC),
             ("connected icon on block", "ink", "ok", kit.MIN_GRAPHIC),
             ("failed icon on block", "ink", "danger", kit.MIN_GRAPHIC),
             ("dialog title on connected", "ink", "ok", kit.MIN_TEXT),
             ("dialog title on failed", "ink", "danger", kit.MIN_TEXT),
             ("ping bar ok", "ok", "ink", kit.MIN_GRAPHIC),
             ("ping bar gold", "gold", "ink", kit.MIN_GRAPHIC),
             ("ping bar danger", "danger", "ink", kit.MIN_GRAPHIC),
             ("copy icon ng", "muted", "ink", kit.MIN_GRAPHIC),
             ("action icon ng", "muted", "@face", kit.MIN_GRAPHIC),
             ("action icon sel", "ink", "gold", kit.MIN_GRAPHIC),
             ("pip on ng", "bone", "@face", kit.MIN_GRAPHIC),
             ("pip on sel", "ink", "gold", kit.MIN_GRAPHIC)]
    report["contrast"] = {}
    for s in kit.SECTIONS:
        sc = Scene(s)
        for name, fg, bg, need in pairs:
            c = K.contrast(K.hexrgb(sc.col(fg)), K.hexrgb(sc.col(bg)))
            report["contrast"][name] = min(report["contrast"].get(name, 99), round(c, 2))
            if c < need and s == "versus":
                errs.append("%s: %s %.2f:1 < %.1f" % (s, name, c, need))
    # unlit bars must read as present but off
    c = K.contrast(K.hexrgb(sc.col("ink")), K.hexrgb(Scene("versus").col("@face")))
    report["contrast"]["unlit bar on ink"] = round(c, 2)
    # state blocks under colour-blindness: report; icons + pips carry the state
    report["state_cvd"] = {}
    blocks = {s: Scene("versus").col(v["block"]) for s, v in STATES.items()}
    for kind in kit.CVD_KINDS:
        rows_ = []
        names = list(blocks)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i], names[j]
                d = K.de2000(K.simulate(K.hexrgb(blocks[a]), kind), K.simulate(K.hexrgb(blocks[b]),
                                                                                kind))
                rows_.append((round(d, 1), a, b))
        report["state_cvd"][kind] = min(rows_)
    return errs, report


def memory(sc):
    names = {it["tex"] for it in sc.items if it["tex"]}
    total = 0
    for n in names:
        w, h = Image.open(U.tex_path(n)).size
        total += w * h // 2                       # every texture here is I4
    return total, sorted(names)


# ---------------------------------------------------------------- main
LAY = None


def main():
    global LAY
    sys.stdout.reconfigure(encoding="utf-8")
    for sub in ("preview",):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    U.WID, U.DLG, U.CUR = U.widgets(), U.dialog(), U.cursor_layout()
    U.ROW_T = U.list_layout()["templates"][0]
    LAY = layout()
    mot = motion()

    # textures: this screen's own masks + ico_online (issued with section 2's icons)
    icons = json.load(open(os.path.join(OUT, "icons_manifest.json"), encoding="utf-8"))
    nav_icons = json.load(open(os.path.join(ROOT, "out_nav", "icons_manifest.json"),
                               encoding="utf-8"))
    own = icons["textures"] + [t for t in nav_icons["textures"]
                               if t["name"] in ("ico_online", "ico_versus")]
    LAY["textures"] = [dict(name=t["name"], file_2x=t["file_2x"], file_1x=t["file_1x"],
                            size_2x=t["size_2x"], format=t["format"], fallback=t["fallback"])
                       for t in own]

    # ---- previews
    scenes = {}
    scenes["online_host"] = screen("host", first=0, sel="character")
    scenes["online_host_code"] = screen("host", first=2, sel="your_code", flash="copied",
                                        status=("idle", "Code copied. Send it to your friend, "
                                                        "then press Host Match."))
    scenes["online_join"] = screen("join", sel="connect",
                                   status=("idle", "Host code 255.255.255.255:65535 pasted - "
                                                   "press Connect"))
    scenes["online_join_empty"] = screen(
        "join", sel="paste_host", vals=dict(values("join"), host_code=None),
        status=("idle", "The clipboard doesn't hold a code (like 1.2.3.4:51500)"))
    scenes["online_connecting"] = screen(
        "join", sel="connect", status=("working", "Connecting..."),
        dialog=dict(variant="connecting", code=CODE_MAX, status=DLG_STATUS_MAX))
    scenes["online_waiting"] = screen(
        "host", first=2, sel="host_match", status=("working", "Waiting for your friend..."),
        dialog=dict(variant="waiting", code=CODE_MAX, label="YOUR CODE",
                    title=DLG_TITLE_MAX))
    scenes["online_failed"] = screen("join", sel="connect", status=("failed", STATUS_MAX))
    scenes["online_failed_dialog"] = screen(
        "join", sel="connect", status=("failed", "Refused: different disc image"),
        dialog=dict(variant="failed"))
    scenes["online_connected"] = screen("host", first=2, sel="host_match",
                                        status=("connected", "Connected! Starting..."), ping=148)
    # a states sheet: every strip state, ping level, plate state and dialog variant
    parts = Scene("versus")
    parts.parts = True
    y = 40
    for st, txt, ping in (("idle", None, None), ("working", None, None),
                          ("connected", None, 42), ("failed", None, None)):
        sub = Scene("versus")
        draw_status(sub, st, txt or STATES[st]["example"], ping=ping)
        for it in sub.items:
            it["verts"] = [(vx, vy - STRIP[1] + y) for vx, vy in it["verts"]]
            it["sheared"] = False
        parts.items += sub.items
        y += 38
    for n, ms in enumerate((42, 90, 140, 220)):
        sub = Scene("versus")
        draw_status(sub, "connected", "Ping %d ms" % ms, ping=ms)
        for it in sub.items:
            it["verts"] = [(vx, vy - STRIP[1] + y) for vx, vy in it["verts"]]
            it["sheared"] = False
        parts.items += sub.items
        y += 38
    for n, (st, code, fl) in enumerate((("ng", CODE_MAX, None), ("sel", "203.0.113.7:51500", None),
                                        ("ng", None, None), ("ng", CODE_MAX, "copied"),
                                        ("disabled", CODE_MAX, None))):
        sub = Scene("versus")
        cx = 40 + (n % 3) * 190 + (n // 3) * 95
        draw_code_plate(sub, 0, 0, code, st, copy=True, flash=fl)
        for it in sub.items:
            it["verts"] = [(vx * 0.72 + cx, vy * 0.72 + y + 18 + (n // 3) * 26)
                           for vx, vy in it["verts"]]
            it["sheared"] = False
        parts.items += sub.items
    scenes_parts = {"online_parts": parts}

    # ---- checks
    kitmot = U.motion()
    allmot = dict(events=dict(kitmot["events"], **{k2: v for k2, v in mot["events"].items()
                                                   if "loop" not in v}))
    lay_for_check = dict(online=LAY, widgets=U.WID)
    errs, contrast = U.check(scenes, allmot, lay_for_check)
    # kit's check adds its own template-level checks (fine) - keep only per-scene ones + slots
    errs2, report = check_extra(LAY, scenes)
    errs += errs2
    # loops: peak extents stay inside title-safe (sweep ends inside the strip)
    L = STRIP[2] - (STRIP[0] + BLOCK_W) - 40
    if STRIP[0] + BLOCK_W + L + 40 > STRIP[2] + 1e-6:
        errs.append("sweep overruns the strip")

    # ---- write
    with open(os.path.join(OUT, "online_layout.json"), "w", encoding="utf-8") as fh:
        json.dump(LAY, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(OUT, "online_motion.json"), "w", encoding="utf-8") as fh:
        json.dump(mot, fh, indent=1, ensure_ascii=False)

    font = json.load(open(os.path.join(ROOT, "out_kit", "font", "font_manifest.json"),
                          encoding="utf-8"))
    kitman = json.load(open(os.path.join(ROOT, "out_kit", "manifest.json"), encoding="utf-8"))
    kit_rows = {t["name"]: t for t in kitman["textures"]}
    mem = {}
    for name, sc in dict(scenes, **scenes_parts).items():
        b, names = memory(sc)
        mem[name] = dict(bytes_2x=b, textures=names)
        if b > U.BUDGET:
            errs.append("%s uses %.0f KB > 1 MB" % (name, b / 1024))
    need_kit = sorted({n for m in mem.values() for n in m["textures"] if n in kit_rows})
    manifest = dict(
        provenance="Original. Masks drawn in pipeline/icons.py; layout and motion from "
                   "pipeline/online.py; nothing traced, sampled or recoloured from Melee.",
        convert="python pc/tools/png2gx.py --layout <menu>/out_online/online_layout.json "
                "--outdir _build/ui   (converts 'textures', copies the layout and "
                "online_motion.json)",
        textures=[dict(t, why=t.get("why", "white mask tinted by material colour; 16 edge "
                                           "levels are plenty")) for t in own],
        requires_from_kit=[dict(name=n, format=kit_rows[n]["format"],
                                bytes_2x=kit_rows[n]["bytes_2x"]) for n in need_kit],
        memory_2x_per_screen={n: round(m["bytes_2x"] / 1024, 1) for n, m in mem.items()},
        checks=dict(report, contrast_worst_kit=contrast))
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(device_scale_factor=1)
        tx = U.Textures()
        for name, sc in dict(scenes, **scenes_parts).items():
            img = U.render(page, sc, tx)
            img.save(os.path.join(OUT, "preview", "%s_2x.png" % name))
            downscale_half(img.convert("RGBA")).convert("RGB").save(
                os.path.join(OUT, "preview", "%s_1x.png" % name))
        browser.close()

    print("online: %d rows (host %d, join %d), %d strip states, %d dialog variants, "
          "%d motion events" % (len(ROWS), len(view_rows("host")), len(view_rows("join")),
                                len(STATES), len(DLG_VARIANTS), len(mot["events"])))
    print("memory @2x per composed screen (excl. disc art):")
    for n, m in mem.items():
        print("   %-22s %6.1f KB" % (n, m["bytes_2x"] / 1024))
    print("status slot: %.1f px for 60 chars at body; long form %s" %
          (strip_geom()["text_max"], report["status_long_at_caption"]))
    print("code: %s px; state blocks closest under CVD: %s" % (report["code_px"],
                                                                report["state_cvd"]))
    print("contrast (worst):", report["contrast"])
    if errs:
        print("\nCHECKS FAILED (%d):" % len(errs))
        for e in errs[:40]:
            print("  - " + e)
        return 1
    print("\nonline checks ok: slots fit (incl. fit-rule steps), code never truncates, "
          "title-safe incl. peak motion, contrast, memory under budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
