"""ONLINE ROOMS: waiting room, room-code entry and the pick/ban lobby, on the section 1 kit.

    python pipeline/kit.py && python pipeline/font_atlas.py && python pipeline/glyphs.py \
        && python pipeline/icons.py && python pipeline/kit_ui.py && python pipeline/online.py \
        && python pipeline/lobby.py

Writes out_lobby/:
    waiting_room_layout.json  host view (hero room code, copy row, status strip) and the
                              guest's "joining" view
    waiting_room_motion.json  plate in, copied, join sweep, opponent found
    code_entry_layout.json    the 4-slot editable room-code field (caret, arrows, states)
    code_entry_motion.json    slot move, letter step, type, paste, invalid shake, caret blink
    lobby_layout.json         player cards, phase banner, action plate (turn / ready), stage
                              strike grid, coin badge, game counter + set score, countdown,
                              lobby status strip, footer hints
    lobby_motion.json         reveal, badge, strike stamp, ban lock, pick confirm, turn
                              handoff, ready toggle, coin flip, countdown, phase/game change
    icons_manifest.json       this section's masks (I4), with legibility counts
    manifest.json             every texture each screen needs, formats, memory, check results
    2x/ 1x/                   the masks
    preview/*.png             composed from the JSON alone (generic element walker below)

Layout format: the kit's (unsheared template space, x' = x + (240 - y) * 0.25 applied last;
colours are kit tokens). One addition, so a preview can be drawn from the file alone:
    element = {origin, quads, slots, states: {axis: {state: {key: token}}}, lift_joint}
    a colour/texture/uv/opacity written "<axis.key>" is looked up in the element's state
    table for the current state of that axis; a quad or slot with "when": {axis: [states]}
    draws only in those states. Nothing else is implied.
Everything here is original: drawn from HTML/SVG in this file, nothing traced, sampled or
recoloured from Melee or any other game.
"""
import copy
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
import icons as IC                                          # noqa: E402
import online as ON                                         # noqa: E402
from build import downscale_half, save_png                 # noqa: E402

K = kit.K
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_lobby")
S, Y0 = kit.SHEAR, 240
Q, T, k, tr = U.Q, U.T, U.k, U.tr
text_w, base_for, cap = U.text_w, U.base_for, U.cap
fit = ON.fit
SECTION = "versus"
LIFT = U.LIFT                                  # (-3, -3): the kit's selection lift
U.TEX_DIRS.append(os.path.join(OUT, "2x"))

ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LEN = 4

# ================================================================ icon masks
LOBBY_ICONS = {}


def icon(name, size, min_draw, use, body=None, shape=None, knock=None):
    LOBBY_ICONS[name] = dict(set="lobby", size_2x=size, min_draw_1x=min_draw, use=use,
                             body=body, shape=shape, knock=knock)


P, Sk, circle, rect, rrect, star = IC.P, IC.S, IC.circle, IC.rect, IC.rrect, IC.star

icon("ico_strike_x", 128, 24, "stage tile struck by P1: a cross (P1's strike shape)",
     body=P("M6 16 L16 6 L32 22 L48 6 L58 16 L42 32 L58 48 L48 58 L32 42 L16 58 L6 48 L22 32 Z"))
icon("ico_strike_o", 128, 24, "stage tile struck by P2: a barred ring (P2's strike shape - "
     "never the same shape as P1's)",
     body=P(IC.ring(32, 32, 28, 19), "evenodd") +
     P("M13.6 20.0 L20.0 13.6 L50.4 44.0 L44.0 50.4 Z"))
icon("ico_lock", 128, 12, "stage ban mark (tile) and the LOCKED IN badge: a padlock",
     shape=P(rrect(8, 28, 48, 34, 5)) + Sk("M19 30 V21 A13 13 0 0 1 45 21 V30", 8),
     knock=P(circle(32, 41, 5.5)) + P(rect(29, 41, 6, 12)))
icon("ico_pick", 64, 12, "picked / final stage tab, READY badge: a heavy check",
     body=P("M4 34 L15 23 L25 33 L49 9 L60 20 L25 55 Z"))
icon("ico_crown", 64, 16, "previous game's winner, on the player card",
     body=P("M4 50 L7 14 L21 30 L32 8 L43 30 L57 14 L60 50 Z") + P(rect(4, 54, 56, 7)))
icon("ico_coin", 128, 32, "coin flip badge: a coin with a milled rim; the port label is "
     "set on it from strings",
     body=P(IC.ring(32, 32, 31, 25.5), "evenodd") + P(circle(32, 32, 22)))
icon("ico_wait", 64, 12, "WAITING badge, opponent's turn: an hourglass",
     body=P(rect(10, 3, 44, 8)) + P(rect(10, 53, 44, 8)) +
     P("M15 10 H49 C49 24, 39 28, 37 32 C39 36, 49 40, 49 54 H15 C15 40, 25 36, 27 32 "
       "C25 28, 15 24, 15 10 Z"))
icon("ico_turn", 64, 16, "turn indicator between the cards; points right as drawn, the "
     "engine flips U for left",
     body=P("M4 22 H30 V6 L60 32 L30 58 V42 H4 Z"))
icon("ico_keyboard", 64, 16, "code entry: 'type on a keyboard' hint",
     shape=P(rrect(2, 14, 60, 38, 5)),
     knock="".join(P(rect(8 + 10 * i, 20, 6, 6)) for i in range(5)) +
     "".join(P(rect(13 + 10 * i, 30, 6, 6)) for i in range(4)) + P(rect(16, 40, 32, 6)))

ICON_SIZE = {n: v["size_2x"] for n, v in LOBBY_ICONS.items()}


def build_icons(page):
    errs, rows, imgs = [], [], {}
    for sub in ("2x", "1x", "preview"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    for name, ic in LOBBY_ICONS.items():
        img = IC.render(page, ic)
        imgs[name] = img
        save_png(img, os.path.join(OUT, "2x", name + ".png"))
        save_png(downscale_half(img), os.path.join(OUT, "1x", name + ".png"))
        n = ic["size_2x"]
        if n & (n - 1) or n > 1024:
            errs.append("%s: %d not POT / over 1024" % (name, n))
        if img.getchannel("A").getbbox() is None:
            errs.append("%s is empty" % name)
        full = IC.topology(img.getchannel("A"))
        hd = IC.topology(IC.shrink(img, 2 * ic["min_draw_1x"]))
        sd = IC.topology(IC.shrink(img, ic["min_draw_1x"]))
        if hd != full:
            errs.append("%s: at %d px shapes/holes %s, full res %s"
                        % (name, 2 * ic["min_draw_1x"], hd, full))
        rows.append(dict(name=name, file_2x="out_lobby/2x/%s.png" % name,
                         file_1x="out_lobby/1x/%s.png" % name, size_2x=[n, n],
                         size_1x=[n // 2, n // 2], format="I4", fallback="IA4",
                         bytes_2x=n * n // 2,
                         why="white mask tinted by material colour; 16 edge levels are plenty",
                         use=ic["use"], min_draw_1x=ic["min_draw_1x"],
                         legibility=dict(full=list(full), at_2x_draw=list(hd),
                                         at_1x_draw=list(sd))))
    # contact sheet
    from PIL import ImageDraw
    cols, cw, chh = 5, 170, 180
    sheet = Image.new("RGB", (cols * cw, ((len(rows) + cols - 1) // cols) * chh), (3, 37, 104))
    dr = ImageDraw.Draw(sheet)
    for i, r in enumerate(rows):
        x, y = (i % cols) * cw, (i // cols) * chh
        img = imgs[r["name"]]
        big = img.resize((96, 96), Image.LANCZOS)
        sheet.paste(Image.new("RGB", big.size, (157, 162, 248)), (x + 8, y + 8),
                    IC.i4_alpha(big))
        m = r["min_draw_1x"]
        for kk, px in enumerate((2 * m, m)):
            sheet.paste(Image.new("RGB", (px, px), (242, 239, 228)),
                        (x + 112, y + 8 + kk * (2 * m + 8)), IC.shrink(img, px))
        dr.text((x + 8, y + 120), r["name"], fill=(242, 239, 228))
        dr.text((x + 8, y + 136), "%d px min" % m, fill=(184, 194, 220))
    sheet.save(os.path.join(OUT, "preview", "icons_sheet_2x.png"))
    return errs, rows


# ================================================================ element helpers
def when(d, **axes):
    d["when"] = {a: list(v) for a, v in axes.items()}
    return d


def rel(el, rect_):
    return rect_


def QT(id_, rect_, colour, texture=None, joint=None, uv=None, opacity=None, **w):
    q = Q(id_, rect_, colour, joint=joint, texture=texture)
    if uv is not None:
        q["uv"] = uv
    if opacity is not None:
        q["opacity"] = opacity
    if w:
        when(q, **w)
    return q


def TT(id_, role, anchor, max_str, colour, align="left", joint=None, max_width=None,
       note=None, **w):
    t = T(id_, role, anchor, max_str, colour, align=align, joint=joint, max_width=max_width,
          note=note)
    if w:
        when(t, **w)
    return t


# ================================================================ waiting room
PANEL = (120, 92, 520, 346)                    # the room panel, both room screens
CELL_W, CELL_H, CELL_GAP = 72, 92, 10
PLATE_X0 = 149
PLATE_X1 = PLATE_X0 + 4 + 8 + CODE_LEN * CELL_W + (CODE_LEN - 1) * CELL_GAP + 12   # 491
CELL_X0 = PLATE_X0 + 12


def cell_x(i):
    return CELL_X0 + i * (CELL_W + CELL_GAP)


WR_PLATE_Y = (132, 240)
WR_CELL_Y = (140, 232)
COPY_ROW = (250, 270)
STATUS_EX = dict(
    waiting="Waiting for an opponent...",
    found="Opponent found: Wario Man, Microgame",
    connecting="Connecting to your opponent...",
    joining="Joining room KQ7X...",
    failed="No room KQ7X. Check the code with your host.",
)


def code_cells(y0, y1, joint, chars_colour, face_colour, lift=False):
    quads, slots = [], []
    for i in range(CODE_LEN):
        x = cell_x(i)
        quads.append(QT("cell_%d" % i, (x, y0, x + CELL_W, y1), face_colour, joint=joint))
        slots.append(TT("char_%d" % i, "display", (x + CELL_W / 2, base_for("display", y0, y1)),
                        "W", chars_colour, align="centre", joint=joint, max_width=CELL_W - 8,
                        note="one character of the room code (%s); display role, caps "
                             "only; centred in its cell so every code draws in the same "
                             "four places" % ROOM_ALPHABET))
    return quads, slots


def waiting_room_layout():
    x0, y0, x1, y1 = PANEL
    py0, py1 = WR_PLATE_Y
    cq, cs = code_cells(*WR_CELL_Y, joint="room_plate", chars_colour="<plate.char>",
                        face_colour="@bg")
    cb = base_for("body", *COPY_ROW)
    plate = dict(
        id="room_plate", origin=[0, 0], lift_joint=None,
        quads=[QT("panel_ink", (x0 - 4, y0 - 4, x1 + 4, y1 + 4), "ink", joint="room_panel"),
               QT("panel_face", PANEL, "@face", joint="room_panel"),
               QT("plate", (PLATE_X0, py0, PLATE_X1, py1), "<plate.plate>", joint="room_plate"),
               QT("accent", (PLATE_X0, py0, PLATE_X0 + 4, py1), "<plate.accent>",
                  joint="room_plate")] + cq + [
               QT("sweep", (PLATE_X0 + 4, py1 - 3, PLATE_X0 + 44, py1), "gold",
                  joint="plate_sweep", view=["guest"]),
               QT("copy_icon", (PLATE_X0, cb - cap("body") / 2 - 8, PLATE_X0 + 16,
                                cb - cap("body") / 2 + 8), "<copy.icon_colour>",
                  texture="<copy.icon>", joint="copy_row", view=["host"])],
        slots=[TT("code_label", "caption", (PLATE_X0, py0 - 8), "ROOM CODE", "gold",
                  joint="room_panel", max_width=PLATE_X1 - PLATE_X0,
                  note="strings: 'ROOM CODE'"),
               ] + cs + [
               TT("copy_text", "body", (PLATE_X0 + 22, cb), "Copied to clipboard",
                  "<copy.text>", joint="copy_row", max_width=PLATE_X1 - PLATE_X0 - 22,
                  view=["host"], note="copy.text_string from strings"),
               TT("share_line", "body", (PLATE_X0, 296),
                  "Send it to your opponent. They pick Join and type it in.", "muted",
                  joint="room_panel", max_width=PLATE_X1 - PLATE_X0,
                  note="host: the share hint; guest: 'Joining room KQ7X...'"),
               TT("sub_line", "caption", (PLATE_X0, 318),
                  "Codes use A-Z and 2-9, never I, O, 0 or 1.", "muted",
                  joint="room_panel", max_width=PLATE_X1 - PLATE_X0,
                  note="optional second line (strings)")],
        states=dict(
            view=dict(host=dict(note="your room: code, copy row, share hint"),
                      guest=dict(note="joining someone's room: the code you typed, the "
                                      "sweep runs under the plate, no copy row")),
            plate=dict(ng=dict(plate="ink", accent="@face_hi", char="bone"),
                       copied=dict(plate="ink", accent="ok", char="bone",
                                   note="40 frames after the code reaches the clipboard"),
                       joining=dict(plate="ink", accent="gold", char="gold_lt"),
                       failed=dict(plate="ink", accent="danger", char="bone")),
            copy=dict(copied=dict(icon="glyph_check", icon_colour="ok", text="bone",
                                  text_string="Copied to clipboard"),
                      idle=dict(icon="ico_copy", icon_colour="muted", text="muted",
                                text_string="Press X to copy it again"))),
        contrast_pairs=[["plate.char", "@bg"], ["copy.text", "@face"],
                        ["copy.icon_colour", "@face", "graphic"]])
    lay = dict(
        name="waiting_room", space="unsheared", shear=dict(S=S, Y0=Y0), section=SECTION,
        element_format="see pipeline/lobby.py docstring: <axis.key> lookups and 'when'",
        chrome=dict(template="chrome_layout.json",
                    title=dict(host="WAITING ROOM", guest="JOINING ROOM"),
                    crumbs=dict(host=["VERSUS", "ONLINE PLAY", "HOST"],
                                guest=["VERSUS", "ONLINE PLAY", "JOIN"]),
                    crumb_icon="ico_versus",
                    hints=dict(host=[["b", "Leave"], ["x", "Copy Code"]],
                               guest=[["b", "Cancel"]]),
                    description=dict(host="Your room stays open until you leave.",
                                     guest="The host sees you as soon as you're in.")),
        room_plate=plate,
        status_strip=dict(template="online_layout.json status_strip (unchanged: rect, "
                                   "block, pips, sweep, ping)",
                          rect=list(ON.STRIP),
                          states_used=dict(waiting="working", found="connected",
                                           connecting="working", joining="working",
                                           failed="failed"),
                          examples=STATUS_EX),
        slots_engine_fills=dict(
            char_0_3="the room code, one character per cell (4 from %s)" % ROOM_ALPHABET,
            copy_text="copy.text_string of the copy state",
            share_line="host: share hint; guest: 'Joining room %s...'",
            status="online status strip text (60 chars at body, fit rule beyond)",
            ping_ms="status strip readout once connected"),
        rules=[
            "The room plate reuses the online code plate's look (ink plate, 4px accent, "
            "bone code) at hero size: 4 cells of 72x92, the display role, one character "
            "centred per cell. The code entry field uses the same cell rects, so a code "
            "looks identical on both players' screens.",
            "Host: code_copied plays when the room code reaches the clipboard (on open and "
            "on X); the copy row shows the 'copied' state for 40 frames, then 'idle'.",
            "Guest: the same plate shows the code being joined, plate 'joining', and "
            "join_sweep loops under it until the server answers.",
            "B leaves the room (host) or cancels (guest): kit dialog_close-style exit, then "
            "back to ONLINE PLAY.",
            "When the opponent arrives: status 'connected' (online status_connected), "
            "opponent_found here, then the lobby opens after 45 frames."],
        textures=[])
    return lay


# ================================================================ code entry
CE_PLATE_Y = (142, 250)
CE_CELL_Y = (150, 242)


def code_entry_layout():
    x0, y0, x1, y1 = PANEL
    py0, py1 = CE_PLATE_Y
    cy0, cy1 = CE_CELL_Y
    hint_y = (284, 300)
    hb = base_for("body", *hint_y)
    quads = [QT("panel_ink", (x0 - 4, y0 - 4, x1 + 4, y1 + 4), "ink", joint="room_panel"),
             QT("panel_face", PANEL, "@face", joint="room_panel"),
             QT("field_plate", (PLATE_X0, py0, PLATE_X1, py1), "ink", joint="code_field"),
             QT("field_accent", (PLATE_X0, py0, PLATE_X0 + 4, py1), "<field.accent>",
                joint="code_field")]
    slot_t = dict(
        id="slot", origin="cell i top-left: x = %d + i * %d, y = %d" % (CELL_X0,
                                                                     CELL_W + CELL_GAP, cy0),
        size=[CELL_W, CELL_H], lift_joint="code_slot_<i>",
        quads=[QT("slot_plate", (0, 0, CELL_W, CELL_H), "<slot.plate>",
                  joint="code_slot_plate_<i>", slot=["active_empty", "active_filled"]),
               QT("slot_face", (0, 0, CELL_W, CELL_H), "<slot.face>", joint="code_slot_<i>"),
               QT("dash", (CELL_W / 2 - 12, CELL_H - 30, CELL_W / 2 + 12, CELL_H - 26),
                  "<slot.dash>", joint="code_slot_<i>", slot=["empty"]),
               QT("caret", (12, CELL_H - 12, CELL_W - 12, CELL_H - 7), "<slot.caret>",
                  joint="code_caret", slot=["active_empty", "active_filled"]),
               QT("invalid_bar", (6, CELL_H - 6, CELL_W - 6, CELL_H - 2), "danger",
                  joint="code_slot_<i>", slot=["invalid"])],
        slots=[TT("char", "display", (CELL_W / 2, base_for("display", 0, CELL_H)), "W",
                  "<slot.char>", align="centre", joint="code_char_<i>", max_width=CELL_W - 8,
                  slot=["filled", "active_filled", "invalid"],
                  note="one of %s; display role (caps only). Anything typed outside the "
                       "alphabet is refused with kit bump on the slot" % ROOM_ALPHABET)],
        states=dict(slot=dict(
            empty=dict(face="@bg", dash="muted", char="bone"),
            filled=dict(face="@bg", char="bone"),
            active_empty=dict(face="gold", plate="gold_dk", caret="ink", char="ink",
                              offset=LIFT),
            active_filled=dict(face="gold", plate="gold_dk", caret="ink", char="ink",
                               offset=LIFT),
            invalid=dict(face="@bg", char="bone",
                         note="every filled slot, while code_invalid plays and until the "
                              "next edit"))),
        contrast_pairs=[["slot.char", "slot.face"], ["slot.dash", "slot.face", "graphic"],
                        ["slot.caret", "slot.face", "graphic"]])
    arrows = dict(
        id="slot_arrows", joint="code_arrows",
        origin="centred on the active cell: x = cell centre",
        slots=[TT("arrow_up", "heading", (0, py0 - 4), "↑", "<arrows.colour>", align="centre",
                  joint="code_arrow_up", note="atlas glyph U+2191"),
               TT("arrow_down", "heading", (0, py1 + 4 + cap("heading")), "↓", "<arrows.colour>",
                  align="centre", joint="code_arrow_down", note="atlas glyph U+2193")],
        states=dict(arrows=dict(ng=dict(colour="gold"), blocked=dict(colour="disabled"),
                                hidden=dict(colour=None))),
        rules=["Up/down step the active slot through the alphabet (wraps; an empty slot "
               "starts at A going up, 9 going down). The arrows ride with the active slot "
               "(code_slot_move) and flash on a step (code_letter_step)."],
        contrast_pairs=[["arrows.colour", "@face", "graphic"]])
    lay = dict(
        name="code_entry", space="unsheared", shear=dict(S=S, Y0=Y0), section=SECTION,
        element_format="see pipeline/lobby.py docstring",
        chrome=dict(template="chrome_layout.json", title="JOIN ROOM",
                    crumbs=["VERSUS", "ONLINE PLAY", "JOIN"], crumb_icon="ico_versus",
                    hints=[["dpad", "Move"], ["a", "Join"], ["y", "Paste"], ["b", "Back"]],
                    description="Up/down change a letter, left/right move between slots."),
        panel=dict(rect=list(PANEL), quads=quads[:2]),
        field=dict(
            id="code_field", rect=[PLATE_X0, py0, PLATE_X1, py1], quads=quads[2:],
            slots=[TT("instruction", "body", (PLATE_X0, 108),
                      "Type the 4-character room code from your host.", "bone",
                      joint="room_panel", max_width=PLATE_X1 - PLATE_X0)],
            cells=[[cell_x(i), cy0, cell_x(i) + CELL_W, cy1] for i in range(CODE_LEN)],
            states=dict(field=dict(ng=dict(accent="@face_hi"), editing=dict(accent="gold"),
                                   invalid=dict(accent="danger"),
                                   joining=dict(accent="gold_lt"))),
            slot_template=slot_t, arrows=arrows),
        hints_row=dict(
            quads=[QT("keyboard_icon", (PLATE_X0, hint_y[0], PLATE_X0 + 16, hint_y[1]),
                      "muted", texture="ico_keyboard", joint="room_panel"),
                   QT("paste_glyph", ("x1 - 4 - advance(paste) - 16", hint_y[0],
                                      "x1 - 4 - advance(paste)", hint_y[1]), "bone",
                      texture="glyph_y", joint="room_panel")],
            slots=[TT("keyboard_text", "body", (PLATE_X0 + 22, hb), "Or type it on a keyboard",
                      "muted", joint="room_panel", max_width=180),
                   TT("paste_text", "body", (PLATE_X1, hb), "Paste", "bone", align="right",
                      joint="room_panel", max_width=PLATE_X1 - PLATE_X0 - 22 - 180 - 20 - 20),
                   TT("alphabet_note", "caption", (PLATE_X0, 322),
                      "Codes use A-Z and 2-9, never I, O, 0 or 1.", "muted",
                      joint="room_panel", max_width=PLATE_X1 - PLATE_X0)],
            rules=["Y (or Ctrl+V) pastes: the clipboard's first 4 alphabet characters "
                   "(case-folded, spaces and dashes dropped) fill the slots, code_paste "
                   "plays, the caret goes to the end. Anything else: kit bump on the field "
                   "and the strip's 'no code' text.",
                   "A keyboard types straight into the active slot and moves right; "
                   "Backspace clears the slot left of the caret and moves there."]),
        status_strip=dict(template="online_layout.json status_strip", rect=list(ON.STRIP),
                          examples=dict(idle="Enter the code, then press A to join.",
                                        joining=STATUS_EX["joining"],
                                        failed=STATUS_EX["failed"],
                                        no_code="The clipboard doesn't hold a room code.")),
        slots_engine_fills=dict(
            char="per slot, when filled: one character of %s" % ROOM_ALPHABET,
            slot_state="per slot: empty / filled / active_empty / active_filled / invalid",
            field_state="ng / editing / invalid / joining",
            arrows_state="ng (active slot) / blocked (never: the alphabet wraps) / hidden "
                         "(while joining)",
            status="online status strip text"),
        rules=["Left/right (d-pad or arrow keys) move the active slot; it stops at the ends "
               "with kit bump. A joins when all 4 slots are filled; with gaps, A moves the "
               "caret to the first empty slot (kit bump on it).",
               "Invalid (the server has no such room, or the code is malformed): every filled "
               "slot takes 'invalid', the field accent turns danger, code_invalid shakes the "
               "field, the strip shows 'failed'. The first edit clears it.",
               "The four cell rects equal the waiting room's, so the code a guest types sits "
               "exactly where the host's plate shows it."],
        textures=[])
    return lay


# ================================================================ lobby
BANNER = (88, 80, 392, 126)
ACTION = (400, 80, 556, 126)
CARD_W, CARD_H, CARD_Y = 220, 72, 134
CARD_X = dict(p1=88, p2=336)
GAP_X = (CARD_X["p1"] + CARD_W, CARD_X["p2"])            # 308..336
GRID = (88, 214, 556, 394)
TILE_W, TILE_H, TILE_GX, TILE_GY = 148, 86, 12, 8
STATUS = U.DESC                                            # the chrome's description strip
SCORE = (446, 24, 550, 52)
STAGES = ["Battlefield", "Dream Land", "Final Destination", "Fountain of Dreams",
          "Pokemon Stadium", "Yoshi's Story"]
STAGE_WORST = "Princess Peach's Castle"
NAME_MAX = max(kit.NAME_FIT["test_names"], key=lambda s: text_w("caption", s))
PHASE_MAX = "CHARACTER PICK"
INSTR_MAX = "Pick on the character screen - kept hidden."
BADGES = dict(waiting="WAITING", picking="PICKING", locked="LOCKED IN", ready="READY")


def tile_rect(i):
    c, r = i % 3, i // 3
    x = GRID[0] + c * (TILE_W + TILE_GX)
    y = GRID[1] + r * (TILE_H + TILE_GY)
    return (x, y, x + TILE_W, y + TILE_H)


def mirror(rect_, w):
    x0, y0, x1, y1 = rect_
    return (w - x1, y0, w - x0, y1)


def card_element(port):
    """A player card in card-local space; P2 is P1 mirrored (portrait and stripe at the
    outer edge, text right-aligned towards the centre)."""
    W, H = CARD_W, CARD_H
    m = port == "p2"

    def R(r):
        return mirror(r, W) if m else r

    def X(x):
        return W - x if m else x
    tx0, tx1 = 90, W - 8                                   # text column (P1)
    tab = (tx0, 8, tx0 + 24, 22)
    crown = (tx0 + 28, 7, tx0 + 44, 23)
    name_base = base_for("body", 26, 40)
    badge_y = (47, 65)
    bw_max = 5 + 12 + 4 + text_w("caption", BADGES["locked"]) + 6
    frame = (10, 6, 78, 66)
    art = (12, 8, 76, 64)
    al = "right" if m else "left"
    pips = [QT("badge_pip_%d" % i, R((tx0 + 5 + i * 5, 53, tx0 + 8.5 + i * 5, 59)),
               "<badge.icon_colour>", joint="card_badge_" + port, badge=["picking"])
            for i in range(3)]
    el = dict(
        id="card_" + port, port=port, origin=[CARD_X[port], CARD_Y], size=[W, H],
        lift_joint="card_" + port,
        lift_joints=["card_" + port, "card_portrait_" + port, "card_badge_" + port,
                     "card_crown_" + port],
        quads=[QT("card_plate", (-3, -3, W + 3, H + 3), "<turn.plate>", joint="card_plate_" + port,
                  turn=["active"]),
               QT("card_outline", (-3, -3, W + 3, H + 3), "<turn.outline>", joint="card_" + port),
               QT("card_face", (0, 0, W, H), "@face", joint="card_" + port),
               QT("port_stripe", R((0, 0, 6, H)), "port:" + port, joint="card_" + port),
               QT("portrait_frame", R(frame), "ink", joint="card_" + port),
               QT("portrait_empty", R(art), "@bg", joint="card_portrait_" + port,
                  portrait=["empty"]),
               dict(QT("portrait_art", R(art), "#ffffff", joint="card_portrait_" + port,
                       portrait=["shown"]), kind="disc_art", size_1x=[64, 56],
                    note="the engine's captured 64x56 CSS icon of the fighter"),
               QT("port_tab", R(tab), "port:" + port, joint="card_" + port),
               QT("crown", R(crown), "gold", texture="ico_crown", joint="card_crown_" + port,
                  crown=["yes"]),
               QT("badge", ("x per rule", badge_y[0], "x per rule", badge_y[1]),
                  "<badge.block>", joint="card_badge_" + port,
                  badge=["waiting", "picking", "locked", "ready"]),
               QT("badge_icon", R((tx0 + 5, 50, tx0 + 17, 62)), "<badge.icon_colour>",
                  texture="<badge.icon>", joint="card_badge_" + port,
                  badge=["waiting", "locked", "ready"])] + pips,
        slots=[TT("port_label", "caption", (X(tx0 + 12), base_for("caption", *tab[1::2])), "P2",
                  "ink", align="centre", joint="card_" + port, max_width=22,
                  note="strings 'P1' / 'P2'"),
               TT("you_tag", "caption", (X(tx0 + 48), base_for("caption", *tab[1::2])), "YOU",
                  "muted", align=al, joint="card_" + port, max_width=tx1 - tx0 - 48,
                  you=["yes"], note="strings 'YOU' on this machine's card only"),
               TT("hidden_mark", "heading", (X(44), base_for("heading", 8, 64)), "?",
                  "@face_hi", align="centre", joint="card_portrait_" + port,
                  portrait=["hidden"], note="the blind-pick placeholder, drawn on ink"),
               TT("name", "body", (X(tx0), name_base), "Captain Falcon Alt 2", "bone", align=al,
                  joint="card_" + port, max_width=tx1 - tx0,
                  note="player name, max 20 characters; fit rule body -> caption -> '…'"),
               TT("badge_text", "caption", (X(tx0 + 21), base_for("caption", *badge_y)),
                  BADGES["locked"], "<badge.text>", align=al, joint="card_badge_" + port,
                  max_width=text_w("caption", BADGES["locked"]),
                  badge=["waiting", "picking", "locked", "ready"],
                  note="strings: WAITING / PICKING / LOCKED IN / READY")],
        badge_rule="badge rect: x from the text column edge (%s = %g) over 5 + 12 (icon or "
                   "pips) + 4 + advance(badge_text) + 6; widest (LOCKED IN) = %.1f"
                   % ("right" if m else "left", X(tx0), bw_max),
        states=dict(
            turn=dict(active=dict(outline="gold", plate="gold_dk", offset=LIFT,
                                  note="whose turn it is: gold outline, lifted"),
                      idle=dict(outline="ink")),
            portrait=dict(empty=dict(note="no fighter yet: the frame over @bg"),
                          hidden=dict(note="blind pick, locked: ink + '?', until the reveal"),
                          shown=dict(note="the disc art")),
            badge=dict(waiting=dict(block="ink", text="muted", icon="ico_wait",
                                    icon_colour="muted"),
                       picking=dict(block="ink", text="gold_lt", icon=None,
                                    icon_colour="gold", note="3 pips run lobby badge_pips"),
                       locked=dict(block="bone", text="ink", icon="ico_lock",
                                   icon_colour="ink"),
                       ready=dict(block="ok", text="ink", icon="ico_pick", icon_colour="ink"),
                       none=dict(note="no badge (stage phases)")),
            crown=dict(yes={}, no={}),
            you=dict(yes={}, no={})),
        contrast_pairs=[["badge.text", "badge.block"], ["badge.icon_colour", "badge.block",
                                                         "graphic"]])
    return el


def tile_element(i):
    W, H = TILE_W, TILE_H
    x0, y0, _, _ = tile_rect(i)
    art = (W / 2 - 32, 6, W / 2 + 32, 62)
    mark = (W / 2 - 20, 14, W / 2 + 20, 54)
    tab = (W - 30, 0, W, 16)
    marked = ["struck_p1", "struck_p2", "banned"]
    el = dict(
        id="tile_%d" % i, index=i, origin=[x0, y0], size=[W, H], lift_joint="tile_%d" % i,
        lift_joints=["tile_%d" % i, "tile_mark_%d" % i, "tile_tab_%d" % i],
        quads=[QT("tile_plate", (-3, -3, W + 3, H + 3), "<tile.plate>", joint="tile_plate_%d" % i,
                  tile=["hovered", "picked"]),
               QT("tile_outline", (-3, -3, W + 3, H + 3), "<tile.outline>", joint="tile_%d" % i),
               QT("tile_face", (0, 0, W, H), "<tile.face>", joint="tile_%d" % i),
               dict(QT("art", art, "<tile.art>", joint="tile_%d" % i, opacity="<tile.art_opacity>"),
                    kind="disc_art", size_1x=[64, 56], optional=True,
                    note="the stage's 64x56 select icon from the disc; if absent, draw this "
                         "quad flat in @face_hi at art_opacity * 0.5"),
               QT("mark", mark, "<tile.mark_colour>", texture="<tile.mark>",
                  joint="tile_mark_%d" % i, tile=marked),
               QT("tab", tab, "<tile.tab>", joint="tile_tab_%d" % i,
                  tile=marked + ["picked", "hover_remote"]),
               QT("tab_icon", (W - 22, 1, W - 8, 15), "<tile.tab_icon>", texture="ico_pick",
                  joint="tile_tab_%d" % i, tile=["picked"])],
        slots=[TT("tab_text", "caption", (W - 15, base_for("caption", 0, 16)), "P2",
                  "<tile.tab_text>", align="centre", joint="tile_tab_%d" % i, max_width=26,
                  tile=marked + ["hover_remote"], note="port label of who struck / banned / "
                                                      "is hovering: strings 'P1' / 'P2'"),
               TT("name", "body", (W / 2, base_for("body", 64, 84)), "Fountain of Dreams",
                  "<tile.name>", align="centre", joint="tile_%d" % i, max_width=W - 12,
                  note="stage name from strings; fit rule body -> caption -> '…'")])
    return el


TILE_STATES = dict(
    available=dict(outline="ink", face="@face", art="#ffffff", art_opacity=1.0, name="bone"),
    hovered=dict(outline="ink", face="gold", plate="gold_dk", art="#ffffff", art_opacity=1.0,
                 name="ink", offset=LIFT, note="this machine's cursor (kit selection)"),
    hover_remote=dict(outline="port:<p>", face="@face", art="#ffffff", art_opacity=1.0,
                      name="bone", tab="port:<p>", tab_text="ink",
                      note="the opponent's cursor during their turn: port outline + port tab"),
    struck_p1=dict(outline="ink", face="ink", art="#8a8a8a", art_opacity=0.35, name="disabled",
                   mark="ico_strike_x", mark_colour="port:p1", tab="port:p1", tab_text="ink"),
    struck_p2=dict(outline="ink", face="ink", art="#8a8a8a", art_opacity=0.35, name="disabled",
                   mark="ico_strike_o", mark_colour="port:p2", tab="port:p2", tab_text="ink"),
    banned=dict(outline="ink", face="ink", art="#8a8a8a", art_opacity=0.35, name="disabled",
                mark="ico_lock", mark_colour="port:<p>", tab="port:<p>", tab_text="ink",
                note="<p> = the banning player (the previous game's winner)"),
    picked=dict(outline="gold_dk", face="gold", plate="gold_dk", art="#ffffff", art_opacity=1.0,
                name="ink", tab="ink", tab_icon="gold_lt", offset=LIFT,
                note="the stage to play (strike survivor or counterpick): gold, lifted, a "
                     "check tab"),
    unavailable=dict(outline="ink", face="ink", art="#8a8a8a", art_opacity=0.2, name="disabled",
                     note="not selectable now and not struck (e.g. READY phase, others)"),
)


ACTION_STATES = dict(
    your_turn=dict(face="gold", plate="gold_dk", text="ink", icon=None, offset=LIFT,
                   string="YOUR TURN"),
    their_turn=dict(face="@face", text="bone", icon=None, string="OPPONENT'S TURN"),
    ready_off=dict(face="@face", text="bone", icon="glyph_start", icon_colour="bone",
                   icon_w=32, string="READY", note="press START (or A) to ready up"),
    ready_on=dict(face="ok", plate="ink", text="ink", icon="ico_pick", icon_colour="ink",
                  icon_w=16, offset=LIFT, string="READY",
                  note="30 frames after the press, then ready_wait (or ready_both)"),
    ready_wait=dict(face="ok", text="ink", icon="pips", icon_colour="ink", icon_w=16,
                    string="WAITING", note="you are ready, the opponent is not"),
    ready_both=dict(face="gold", plate="gold_dk", text="ink", icon="ico_pick",
                    icon_colour="ink", icon_w=16, offset=LIFT, string="GO!",
                    note="both ready: holds while the countdown runs"),
)


def lobby_layout():
    bx0, by0, bx1, by1 = BANNER
    ax0, ay0, ax1, ay1 = ACTION
    cards = [card_element("p1"), card_element("p2")]
    tiles = [tile_element(i) for i in range(6)]
    gx0, gx1 = GAP_X
    gcy = CARD_Y + CARD_H / 2
    act_base = base_for("row", ay0, ay1)
    coin = dict(rect=[186, 262, 454, 346], coin=[198, 280, 246, 328])
    cx0, cy0, cx1, cy1 = coin["rect"]
    ccx0, ccy0, ccx1, ccy1 = coin["coin"]
    cd = (272, 246, 368, 334)                        # countdown slab
    sb = base_for("title", SCORE[1], SCORE[3])
    lay = dict(
        name="lobby", space="unsheared", shear=dict(S=S, Y0=Y0), section=SECTION,
        element_format="see pipeline/lobby.py docstring: <axis.key> lookups and 'when'",
        chrome=dict(template="chrome_layout.json",
                    title_slot="the GAME counter: strings 'GAME %d' (title role; the slab "
                               "follows its width)",
                    title_max="GAME 5",
                    crumbs=["VERSUS", "ONLINE PLAY", "ROOM KQ7X"], crumb_icon="ico_versus",
                    hints=[["a", "Strike"], ["b", "Back"], ["start", "Ready"],
                           ["dpad", "Move"]],
                    hints_by_phase=dict(
                        character=[["a", "Pick"], ["b", "Leave"]],
                        stage_strike=[["a", "Strike"], ["dpad", "Move"], ["b", "Leave"]],
                        stage_ban=[["a", "Ban"], ["dpad", "Move"], ["b", "Leave"]],
                        stage_pick=[["a", "Pick"], ["dpad", "Move"], ["b", "Leave"]],
                        ready=[["start", "Ready"], ["b", "Leave"]]),
                    description="replaced by lobby_status (same rect)"),
        score_plaque=dict(
            id="score_plaque", rect=list(SCORE),
            quads=[QT("plaque", SCORE, "ink", joint="score_plaque")],
            slots=[TT("set_label", "caption", (SCORE[0] + 10, base_for("caption", *SCORE[1::2])),
                      "SET", "muted", joint="score_plaque", note="strings 'SET'"),
                   TT("set_score", "title", (SCORE[2] - 10, sb), "2 - 1", "bone", align="right",
                      joint="set_score", max_width=SCORE[2] - SCORE[0] - 20 - 26,
                      note="'<P1 wins> - <P2 wins>', P1 always left like the cards; tabular "
                           "digits")]),
        phase_banner=dict(
            id="phase_banner", rect=list(BANNER),
            quads=[QT("banner_plate", BANNER, "ink", joint="phase_banner"),
                   QT("banner_accent", (bx0, by0, bx0 + 6, by1), "<phase.accent>",
                      joint="phase_banner")],
            slots=[TT("phase_title", "title", (bx0 + 18, by0 + 22), PHASE_MAX, "bone",
                      joint="phase_title", max_width=bx1 - bx0 - 30,
                      note="strings: CHARACTER PICK / STAGE STRIKING / COUNTERPICK / "
                           "READY CHECK"),
                   TT("instruction", "body", (bx0 + 18, by0 + 39), INSTR_MAX, "muted",
                      joint="phase_title", max_width=bx1 - bx0 - 30,
                      note="e.g. 'P1 strikes 1 stage', 'Counterpick: P2 bans 2', 'Both "
                           "ready?'")],
            states=dict(phase=dict(character=dict(accent="@face_hi"),
                                   stage=dict(accent="gold"),
                                   ready=dict(accent="ok"))),
            contrast_pairs=[["bone", "ink"], ["muted", "ink"]]),
        action_plate=dict(
            id="action_plate", rect=list(ACTION), lift_joint="action_plate",
            lift_joints=["action_plate", "action_text"],
            quads=[QT("action_plate_dk", (ax0 - 3, ay0 - 3, ax1 + 3, ay1 + 3), "<action.plate>", joint="action_plate_rest",
                      action=["your_turn", "ready_on", "ready_both"]),
                   QT("action_outline", (ax0 - 3, ay0 - 3, ax1 + 3, ay1 + 3), "ink",
                      joint="action_plate"),
                   QT("action_face", ACTION, "<action.face>", joint="action_plate"),
                   QT("action_icon", ("group rule", act_base - cap("row") / 2 - 8,
                                      "group rule", act_base - cap("row") / 2 + 8),
                      "<action.icon_colour>", texture="<action.icon>", joint="action_plate",
                      action=["ready_off", "ready_on", "ready_both"])],
            slots=[TT("action_text", "row", ((ax0 + ax1) / 2, act_base), "OPPONENT'S TURN",
                      "<action.text>", align="centre", joint="action_text",
                      max_width=ax1 - ax0 - 12,
                      note="action.string from strings; with an icon, icon + 6 + text are "
                           "centred as one group")],
            states=dict(action=ACTION_STATES),
            rules=["One rect, two jobs: the TURN indicator during pick/strike/ban phases "
                   "(your_turn / their_turn) and the READY button in the ready phase "
                   "(ready_off / ready_on / ready_wait / ready_both). It always says what "
                   "is needed from this player now.",
                   "ready_wait shows 3 ink pips (lobby badge_pips) in the icon's place."],
            contrast_pairs=[["action.text", "action.face"],
                            ["action.icon_colour", "action.face", "graphic"]]),
        cards=cards,
        turn_arrow=dict(
            id="turn_arrow", rect=[gx0 + 2, gcy - 12, gx1 - 2, gcy + 12],
            quads=[QT("turn_arrow", (gx0 + 2, gcy - 12, gx1 - 2, gcy + 12), "gold",
                      texture="ico_turn", uv="<turn.uv>", joint="turn_arrow",
                      turn=["p1", "p2"])],
            states=dict(turn=dict(p1=dict(uv=[1, 0, 0, 1], note="points left, at P1"),
                                  p2=dict(uv=[0, 0, 1, 1], note="points right, at P2"),
                                  none=dict(note="hidden (both act: blind pick, ready)"))),
            rules=["Sits in the %d px gap between the cards. With the active card's gold "
                   "outline and lift, and the action plate's words, turn is never colour "
                   "only." % (gx1 - gx0)]),
        stage_grid=dict(
            id="stage_grid", rect=list(GRID), columns=3, rows=2, tile=[TILE_W, TILE_H],
            gutter=[TILE_GX, TILE_GY],
            why_3x2=["Names fit on one line at body (14) in a 148 px tile - 6x1 tiles would "
                     "be 68 px wide and every name would need 2 lines at caption.",
                     "Each tile keeps a full 64x56 image slot above its name.",
                     "The d-pad moves in 2D, 3 steps at most, and the 1-2-2 strike order "
                     "reads across two short rows.",
                     "It fits between the cards and the status strip with the kit lift."],
            order="row-major: " + ", ".join(STAGES),
            tiles=tiles,
            tile_states=TILE_STATES,
            contrast_pairs=[["name", "face"], ["tab_text", "tab"], ["mark_colour", "face"]],
            rules=["Draw order: tiles 0-5, the hovered or picked tile last.",
                   "Strikes: P1's mark is the cross (ico_strike_x) in P1 colour, P2's the "
                   "barred ring (ico_strike_o) in P2 colour, and the tab names the player - "
                   "shape, label and colour all differ.",
                   "Ban: the padlock (ico_lock) in the banning player's colour, tab names "
                   "them. Picked: gold, lifted, check tab.",
                   "Stage images come from the disc later: the art quad is optional."]),
        coin_badge=dict(
            id="coin_badge", rect=coin["rect"],
            quads=[QT("coin_dim", (-60, -20, 700, 500), "ink", opacity=0.45, joint="coin_dim"),
                   QT("coin_ink", (cx0 - 4, cy0 - 4, cx1 + 4, cy1 + 4), "ink", joint="coin_badge"),
                   QT("coin_face", coin["rect"], "@face", joint="coin_badge"),
                   QT("coin", coin["coin"], "<coin.colour>", texture="ico_coin",
                      joint="coin")],
            slots=[TT("coin_label", "title", ((ccx0 + ccx1) / 2, base_for("title", ccy0, ccy1)),
                      "P2", "ink", align="centre", joint="coin",
                      note="the port label on the coin's face ('P1' / 'P2')"),
                   TT("coin_caption", "caption", (ccx1 + 14, cy0 + 22), "COIN FLIP", "muted",
                      joint="coin_badge", note="strings 'COIN FLIP'"),
                   TT("coin_text", "label", (ccx1 + 14, cy0 + 50), "P2 STRIKES FIRST", "bone",
                      joint="coin_text", max_width=cx1 - ccx1 - 14 - 12,
                      note="strings '%s STRIKES FIRST'")],
            states=dict(coin=dict(p1=dict(colour="port:p1"), p2=dict(colour="port:p2"),
                                  spinning=dict(colour="gold",
                                                note="label alternates P1/P2 each half turn"))),
            rules=["Game 1 only, when the stage phase starts. coin_flip plays (48 frames), "
                   "coin_text fades in, holds 60 frames, then coin_badge_out and the turn "
                   "goes to the winner (turn_handoff)."],
            contrast_pairs=[["ink", "coin.colour"], ["bone", "@face"], ["muted", "@face"]]),
        countdown=dict(
            id="countdown", rect=list(cd),
            quads=[QT("countdown_dim", (-60, -20, 700, 500), "ink", opacity=0.55,
                      joint="countdown_dim"),
                   QT("countdown_ink", (cd[0] - 4, cd[1] - 4, cd[2] + 4, cd[3] + 4), "ink",
                      joint="countdown_slab"),
                   QT("countdown_slab", cd, "gold", joint="countdown_slab"),
                   QT("countdown_strip", (cd[0] - 60, cd[3] + 10, cd[2] + 60, cd[3] + 30),
                      "ink", joint="countdown_strip")],
            slots=[TT("numeral", "display", ((cd[0] + cd[2]) / 2, base_for("display", cd[1], cd[3])),
                      "3", "ink", align="centre", joint="countdown_numeral",
                      note="'3', '2', '1' from the display atlas"),
                   TT("stage_line", "body", ((cd[0] + cd[2]) / 2, base_for("body", cd[3] + 10,
                                                                        cd[3] + 30)),
                      "Fountain of Dreams", "bone", align="centre", joint="countdown_strip",
                      max_width=cd[2] - cd[0] + 120 - 16, note="the stage being loaded")],
            rules=["Both ready: countdown_in, then countdown_tick three times (60 frames "
                   "each, numeral 3, 2, 1), then the match. Either player's B during the "
                   "count cancels it (countdown_out, both back to ready_off)."],
            contrast_pairs=[["ink", "gold"], ["bone", "ink"]]),
        lobby_status=dict(
            id="lobby_status", rect=list(STATUS),
            quads=[QT("status_plate", STATUS, "ink", joint="lobby_status")] +
                  [QT("bar_%d" % (i + 1), (STATUS[2] - 10 - text_w("caption", "999 ms") - 6 - 16,
                                           STATUS[1] + 4, STATUS[2] - 10 -
                                           text_w("caption", "999 ms") - 6, STATUS[3] - 4),
                      "<ping bar colour>", texture="sig_bar_%d" % (i + 1), joint="ping")
                   for i in range(4)],
            slots=[TT("status_text", "body", (STATUS[0] + 16, base_for("body", *STATUS[1::2])),
                      "Opponent: Wario Man, Microgame. Winner of game 2 bans first.", "bone",
                      joint="status_text",
                      max_width=STATUS[2] - STATUS[0] - 16 - 10 - text_w("caption", "999 ms")
                      - 6 - 16 - 10,
                      note="one line of context from strings; fit rule beyond"),
                   TT("ping_ms", "caption", (STATUS[2] - 10, base_for("caption", *STATUS[1::2])),
                      "999 ms", "muted", align="right", joint="ping")],
            rules=["Takes the chrome description strip's rect on this screen. Ping levels "
                   "and bar colours as online_layout.json status_strip.ping."]),
        phases=dict(
            game1=[dict(phase="character", blind=True,
                        cards="each: PICKING until locked, then LOCKED IN; the opponent's "
                              "portrait 'hidden', your own 'shown'. Both locked -> "
                              "card_reveal on both, then the stage phase",
                        banner=["CHARACTER PICK", INSTR_MAX], action="hidden (both act)",
                        grid="all tiles 'available', no cursor (a preview of the legal list)"),
                   dict(phase="stage", kind="strike", coin_flip=True,
                        order="1-2-2: the coin winner strikes 1, the other 2, the winner 2",
                        banner=["STAGE STRIKING", "P1 strikes 1 stage"],
                        action="your_turn / their_turn",
                        end="the last available tile becomes 'picked' (pick_confirm)"),
                   dict(phase="ready")],
            game2_plus=[dict(phase="stage", kind="ban_pick",
                             order="previous winner bans 2 (banned), loser picks 1 of the 4 "
                                   "left (picked)",
                             banner=["COUNTERPICK", "Counterpick: P2 bans 2"],
                             cards="crown on the previous winner"),
                        dict(phase="character", blind=False,
                             order="winner picks first (PICKING, loser WAITING), then the "
                                   "loser; portraits shown as they lock",
                             banner=["CHARACTER PICK", "P2 picks first, then P1"]),
                        dict(phase="ready")],
            ready=dict(banner=["READY CHECK", "Both ready?"],
                       action="ready_off -> ready_on -> ready_wait / ready_both",
                       cards="badge READY or WAITING", grid="picked tile + the rest "
                                                         "'unavailable' (struck/banned keep "
                                                         "their marks)"),
            after_match="the room returns here: set_score updates (score_update), the "
                        "header counter advances (game_advance), crown moves to the winner"),
        slots_engine_fills=dict(
            chrome_title="GAME counter 'GAME n'",
            set_score="'a - b'",
            phase_title="phase name", instruction="whose move, how many",
            card_p1_p2=dict(name="player name (20 chars max)", portrait_art="64x56 disc icon",
                            port_label="P1/P2", you_tag="YOU (this machine)",
                            badge_text="WAITING/PICKING/LOCKED IN/READY",
                            states="turn, portrait, badge, crown, you"),
            action_text="action.string", tile_i=dict(name="stage name", art="optional 64x56",
                                                     tab_text="P1/P2", state="tile_states"),
            coin=dict(coin_label="P1/P2", coin_text="'Pn STRIKES FIRST'"),
            countdown=dict(numeral="3/2/1", stage_line="stage name"),
            lobby_status=dict(status_text="context line", ping_ms="round trip")),
        textures=[])
    return lay


# ================================================================ motion
def finish(ev):
    for e in ev.values():
        e["length_frames"] = 1 + max(kk["frame"] for t in e["tracks"] for kk in t["keys"])
    return ev


FORMAT = ("hub_motion.json: tracks, from_current, interpolation and transform rules are "
          "identical; see out_kit/kit_motion.json. 'loop' as in out_online/online_motion.json")


def waiting_room_motion():
    ev = {}
    ev["room_plate_in"] = dict(
        applies_to="room plate when the screen opens", sfx=[], pivot="plate centre",
        note="char_<i> start 4 frames apart",
        tracks=[tr("room_plate", "SCA_X", k(0, 0.9), k(6, 1.03), k(10, 1)),
                tr("room_plate", "SCA_Y", k(0, 0.9), k(6, 1.03), k(10, 1)),
                tr("room_plate", "ALPHA", k(0, 0, "LIN"), k(4, 1, "LIN"), kind="material"),
                tr("char_<i>", "TRA_Y", k(0, 14), k(6, -2), k(9, 0)),
                tr("char_<i>", "ALPHA", k(0, 0, "LIN"), k(5, 1, "LIN"), kind="material")])
    ev["room_code_copied"] = dict(
        applies_to="room plate + copy row, when the code reaches the clipboard",
        sfx=[dict(frame=0, cue="sfx_toast")], pivot="plate centre",
        note="plate state 'copied' and copy state 'copied' for 40 frames, then ng / idle",
        tracks=[tr("room_plate", "SCA_X", k(0, 1), k(3, 1.04), k(9, 1)),
                tr("room_plate", "SCA_Y", k(0, 1), k(3, 1.04), k(9, 1)),
                tr("accent", "COLOUR", k(0, "ok", "CON"), k(40, "@face_hi", "CON"),
                   kind="material"),
                tr("copy_row", "TRA_X", k(0, -8), k(6, 1), k(9, 0)),
                tr("copy_row", "ALPHA", k(0, 0, "LIN"), k(4, 1, "LIN"), kind="material")])
    ev["join_sweep"] = dict(
        applies_to="guest: the sweep under the plate while joining",
        loop=dict(from_frame=0, to_frame=60),
        tracks=[tr("plate_sweep", "TRA_X", k(0, 0, "SPL", 0),
                   k(44, PLATE_X1 - PLATE_X0 - 48, "SPL", 0),
                   k(60, PLATE_X1 - PLATE_X0 - 48, "CON")),
                tr("plate_sweep", "ALPHA", k(0, 0, "LIN"), k(6, 1, "LIN"), k(38, 1, "LIN"),
                   k(44, 0, "CON"), k(60, 0, "CON"), kind="material")])
    ev["opponent_found"] = dict(
        applies_to="room panel when the opponent connects (with online status_connected)",
        sfx=[dict(frame=0, cue="sfx_connected")], pivot="panel centre",
        tracks=[tr("room_panel", "SCA_X", k(0, 1), k(4, 1.02), k(10, 1)),
                tr("room_panel", "SCA_Y", k(0, 1), k(4, 1.02), k(10, 1)),
                tr("accent", "COLOUR", k(0, "ok", "LIN"), k(20, "@face_hi", "LIN"),
                   kind="material")])
    ev["room_leave"] = dict(
        applies_to="room panel on B", sfx=[dict(frame=0, cue="sfx_dialog_close")],
        tracks=[tr("room_panel", "ALPHA", k(0, 1, "LIN"), k(6, 0, "LIN"), kind="material"),
                tr("room_panel", "SCA_X", k(0, 1), k(6, 0.96)),
                tr("room_panel", "SCA_Y", k(0, 1), k(6, 0.96))])
    return dict(fps=60, format=FORMAT, space="unsheared", events=finish(ev),
                sequences=dict(
                    host_open=[dict(event="room_plate_in"), dict(event="room_code_copied",
                                                                 at_frame=12)],
                    guest_open=[dict(event="room_plate_in"), dict(event="join_sweep"),
                                dict(event="status_set (online)", state="working")],
                    found=[dict(event="status_set (online)", state="connected"),
                           dict(event="status_connected (online)"),
                           dict(event="opponent_found"),
                           dict(note="45 frames, then the lobby")],
                    join_failed=[dict(event="status_set (online)", state="failed"),
                                 dict(event="status_failed (online)"),
                                 dict(note="back to code entry with field 'invalid' and "
                                           "code_invalid")]))


def code_entry_motion():
    ev = {}
    pitch = CELL_W + CELL_GAP
    ev["code_slot_move"] = dict(
        applies_to="left/right: caret, arrows and the active lift move to the new slot",
        sfx=[dict(frame=0, cue="sfx_cursor_move")],
        note="delta = new - old slot (+-1); code_slot_<new> lifts, code_slot_<old> drops",
        tracks=[tr("code_arrows", "TRA_X", k(0, 0, fc=True), k(4, "%d*delta + 3*delta" % pitch),
                   k(7, "%d*delta" % pitch)),
                tr("code_caret", "TRA_X", k(0, 0, fc=True), k(4, "%d*delta" % pitch))] +
               U.lift_tracks("code_slot_<new>", *LIFT) + U.drop_tracks("code_slot_<old>"))
    ev["code_letter_step"] = dict(
        applies_to="up/down on the active slot", sfx=[dict(frame=0, cue="sfx_value_change")],
        note="dir = +1 up (next letter), -1 down; the old character draws on "
             "code_char_out, the new on code_char_<i>",
        tracks=[tr("code_char_out", "TRA_Y", k(0, 0), k(5, "14*dir", "SPL", 0)),
                tr("code_char_out", "ALPHA", k(0, 1, "LIN"), k(4, 0, "LIN"), kind="material"),
                tr("code_char_<i>", "TRA_Y", k(0, "-14*dir"), k(6, "2*dir"), k(9, 0)),
                tr("code_char_<i>", "ALPHA", k(0, 0, "LIN"), k(5, 1, "LIN"), kind="material"),
                tr("code_arrow_<up|down>", "TRA_Y", k(0, 0), k(2, "-4*dir"), k(7, 0)),
                tr("code_arrow_<up|down>", "COLOUR", k(0, "gold_lt", "LIN"), k(7, "gold", "LIN"),
                   kind="material")])
    ev["code_type"] = dict(
        applies_to="a typed character lands in the active slot (then code_slot_move +1)",
        sfx=[dict(frame=0, cue="sfx_value_tick")], pivot="slot centre",
        tracks=[tr("code_char_<i>", "SCA_X", k(0, 1.35), k(6, 1)),
                tr("code_char_<i>", "SCA_Y", k(0, 1.35), k(6, 1)),
                tr("code_slot_<i>", "COLOUR", k(0, "gold_lt", "LIN"), k(6, "<slot face>", "LIN"),
                   kind="material")])
    ev["code_paste"] = dict(
        applies_to="Y / Ctrl+V with a code on the clipboard: all four slots fill",
        sfx=[dict(frame=0, cue="sfx_value_change")],
        note="slot i starts at frame 3*i; the field accent flashes gold_lt",
        tracks=[tr("code_char_<i>", "TRA_Y", k(0, -12), k(6, 1), k(9, 0)),
                tr("code_char_<i>", "ALPHA", k(0, 0, "LIN"), k(4, 1, "LIN"), kind="material"),
                tr("field_accent", "COLOUR", k(0, "gold_lt", "LIN"), k(16, "<field accent>",
                                                                         "LIN"),
                   kind="material")])
    ev["code_invalid"] = dict(
        applies_to="the server has no such room (or the code is malformed)",
        sfx=[dict(frame=0, cue="sfx_error")],
        tracks=[tr("code_field", "TRA_X", k(0, 0), k(2, 6), k(5, -5), k(8, 4), k(11, -3),
                   k(14, 2), k(17, 0)),
                tr("field_accent", "COLOUR", k(0, "danger", "CON"), kind="material"),
                tr("invalid_bar", "SCA_X", k(0, 0), k(6, 1))])
    ev["code_caret_blink"] = dict(
        applies_to="the caret on the active slot", loop=dict(from_frame=0, to_frame=48),
        note="restarts at frame 0 (fully on) on every move, step or type",
        tracks=[tr("code_caret", "ALPHA", k(0, 1, "CON"), k(28, 0.2, "CON"), k(48, 0.2, "CON"),
                   kind="material")])
    ev["code_join"] = dict(
        applies_to="A with all 4 filled: the field commits",
        sfx=[dict(frame=0, cue="sfx_menu_confirm")], pivot="field centre",
        tracks=[tr("code_field", "SCA_X", k(0, 1), k(3, 1.03), k(8, 1)),
                tr("code_field", "SCA_Y", k(0, 1), k(3, 1.03), k(8, 1)),
                tr("code_arrows", "ALPHA", k(0, 1, "LIN"), k(4, 0, "LIN"), kind="material")])
    return dict(fps=60, format=FORMAT, space="unsheared", events=finish(ev),
                value_expressions="delta, dir; <...> from the layout's state tables",
                sequences=dict(
                    move=[dict(event="code_slot_move"), dict(event="code_caret_blink",
                                                             restart=True)],
                    step=[dict(event="code_letter_step"), dict(event="code_caret_blink",
                                                               restart=True)],
                    type=[dict(event="code_type"), dict(event="code_slot_move", delta=1,
                                                        when="not the last slot")],
                    join=[dict(event="code_join"),
                          dict(event="status_set (online)", state="working"),
                          dict(note="then the waiting room, guest view")],
                    not_found=[dict(event="code_invalid"),
                               dict(event="status_set (online)", state="failed")],
                    hold_repeat=dict(delay_frames=24, interval_frames=4,
                                     note="up/down held repeats through the alphabet")))


def lobby_motion():
    ev = {}
    ev["phase_change"] = dict(
        applies_to="phase banner, on any phase or instruction change",
        sfx=[dict(frame=0, cue="sfx_value_change")],
        note="old text on phase_title_out, new on phase_title",
        tracks=[tr("phase_title_out", "TRA_X", k(0, 0), k(5, -12, "SPL", 0)),
                tr("phase_title_out", "ALPHA", k(0, 1, "LIN"), k(4, 0, "LIN"), kind="material"),
                tr("phase_title", "TRA_X", k(0, 14), k(7, -1), k(10, 0)),
                tr("phase_title", "ALPHA", k(0, 0, "LIN"), k(6, 1, "LIN"), kind="material"),
                tr("banner_accent", "SCA_Y", k(0, 0.2), k(6, 1)),
                tr("banner_accent", "COLOUR", k(0, "bone", "LIN"), k(8, "<phase accent>", "LIN"),
                   kind="material")])
    ev["badge_set"] = dict(
        applies_to="a card's status badge changes (PICKING -> LOCKED IN etc.)",
        sfx=[dict(frame=0, cue="sfx_toggle")], pivot="badge centre",
        tracks=[tr("card_badge_<p>", "SCA_X", k(0, 0.6), k(4, 1.15), k(9, 1)),
                tr("card_badge_<p>", "SCA_Y", k(0, 0.6), k(4, 1.15), k(9, 1))])
    ev["badge_pips"] = dict(
        applies_to="PICKING badge pips and the ready_wait pips (same keys as online "
                   "activity_loop, 6 px pitch)",
        loop=dict(from_frame=0, to_frame=36),
        tracks=[tr("badge_pip_%d" % i, "ALPHA", *([k(0, 0.3, "CON")] if i else []),
                   k(i * 12, 0.3 if i else 1.0, "LIN"), k(i * 12 + 2, 1.0, "LIN"),
                   k(i * 12 + 12, 1.0, "LIN"), k(i * 12 + 18, 0.3, "CON"), k(36, 0.3, "CON"),
                   kind="material") for i in range(3)])
    ev["card_reveal"] = dict(
        applies_to="both cards when both players have locked in (blind pick)",
        sfx=[dict(frame=0, cue="sfx_value_change"), dict(frame=7, cue="sfx_reveal")],
        pivot="portrait centre",
        note="portrait state switches hidden -> shown at frame 7 (edge-on); P2 starts 4 "
             "frames after P1",
        tracks=[tr("card_portrait_<p>", "SCA_X", k(0, 1, "SPL", 0), k(7, 0, "LIN"),
                   k(12, 1.12, "SPL"), k(16, 1)),
                tr("card_portrait_<p>", "SCA_Y", k(0, 1), k(7, 1.08), k(16, 1)),
                tr("card_<p>", "TRA_Y", k(0, 0), k(7, -3), k(14, 0)),
                tr("card_face_<p>", "COLOUR", k(7, "gold_lt", "LIN"), k(18, "@face", "LIN"),
                   kind="material")])
    ev["turn_handoff"] = dict(
        applies_to="turn passes: arrow flips, the new card lifts, the old drops, the action "
                   "plate swaps words",
        sfx=[dict(frame=0, cue="sfx_turn")],
        note="dir = +1 when P2 gets the turn, -1 for P1 (the arrow's SCA_X runs through 0 "
             "and lands on 1 with the new UV)",
        tracks=[tr("turn_arrow", "SCA_X", k(0, 1, fc=True), k(4, 0, "LIN"), k(8, 1.25),
                   k(12, 1)),
                tr("turn_arrow", "TRA_X", k(4, "-6*dir"), k(12, 0))] +
               U.lift_tracks("card_<new>", *LIFT) + U.drop_tracks("card_<old>") + [
                tr("card_outline_<new>", "COLOUR", k(0, "ink", "LIN"), k(6, "gold", "LIN"),
                   kind="material"),
                tr("card_outline_<old>", "COLOUR", k(0, "gold", "LIN"), k(4, "ink", "LIN"),
                   kind="material"),
                tr("action_text", "TRA_X", k(0, "14*dir"), k(7, "-1*dir"), k(10, 0)),
                tr("action_text", "ALPHA", k(0, 0, "LIN"), k(6, 1, "LIN"), kind="material"),
                tr("action_plate", "COLOUR", k(0, "<old face>", "LIN"), k(6, "<new face>", "LIN"),
                   kind="material")])
    ev["tile_hover"] = dict(applies_to="stage tile under this machine's cursor",
                            sfx=[dict(frame=0, cue="sfx_cursor_move")],
                            tracks=U.lift_tracks("tile_<i>", *LIFT) + [
                                tr("tile_plate_<i>", "ALPHA", k(0, 1, "CON"), kind="material"),
                                tr("tile_face_<i>", "COLOUR", k(0, "@face", "LIN", fc=True),
                                   k(1, "gold_lt", "LIN"), k(8, "gold", "LIN"),
                                   kind="material")])
    ev["tile_unhover"] = dict(applies_to="stage tile the cursor left", sfx=[],
                              tracks=U.drop_tracks("tile_<i>") + [
                                  tr("tile_plate_<i>", "ALPHA", k(0, 1, "CON"), k(5, 0, "CON"),
                                     kind="material"),
                                  tr("tile_face_<i>", "COLOUR", k(0, "gold", "LIN", fc=True),
                                     k(2, "@face", "LIN"), kind="material")])
    ev["tile_hover_remote"] = dict(
        applies_to="the opponent's cursor moves (their turn): outline + tab in their colour",
        sfx=[], tracks=[tr("tile_outline_<i>", "COLOUR", k(0, "ink", "LIN"), k(4, "port:<p>",
                                                                              "LIN"),
                           kind="material"),
                        tr("tile_tab_<i>", "TRA_Y", k(0, 6), k(5, 0))])
    ev["strike_stamp"] = dict(
        applies_to="a tile is struck: the mark stamps down, the tile thumps, the tab pops",
        sfx=[dict(frame=3, cue="sfx_strike")], pivot="mark centre (tile centre for tile_<i>)",
        note="the tile drops its hover lift at frame 0 (tile_unhover's position keys)",
        tracks=[tr("tile_mark_<i>", "SCA_X", k(0, 1.7), k(4, 0.92), k(8, 1)),
                tr("tile_mark_<i>", "SCA_Y", k(0, 1.7), k(4, 0.92), k(8, 1)),
                tr("tile_mark_<i>", "ALPHA", k(0, 0, "LIN"), k(3, 1, "LIN"), kind="material"),
                tr("tile_<i>", "TRA_Y", k(0, 0, fc=True), k(3, 0), k(5, 2), k(9, 0)),
                tr("tile_face_<i>", "COLOUR", k(0, "<from>", "LIN", fc=True), k(3, "ink", "LIN"),
                   kind="material"),
                tr("tile_tab_<i>", "SCA_X", k(0, 0), k(5, 0), k(8, 1.2), k(11, 1)),
                tr("tile_tab_<i>", "SCA_Y", k(0, 0), k(5, 0), k(8, 1.2), k(11, 1))])
    ev["ban_lock"] = dict(
        applies_to="a tile is banned: the padlock drops in and snaps shut",
        sfx=[dict(frame=6, cue="sfx_lock")], pivot="mark bottom",
        tracks=[tr("tile_mark_<i>", "TRA_Y", k(0, -14), k(6, 0, "SPL", 0)),
                tr("tile_mark_<i>", "ALPHA", k(0, 0, "LIN"), k(3, 1, "LIN"), kind="material"),
                tr("tile_mark_<i>", "SCA_Y", k(6, 1), k(8, 0.86), k(12, 1)),
                tr("tile_mark_<i>", "SCA_X", k(6, 1), k(8, 1.08), k(12, 1)),
                tr("tile_face_<i>", "COLOUR", k(0, "<from>", "LIN", fc=True), k(6, "ink", "LIN"),
                   kind="material"),
                tr("tile_tab_<i>", "SCA_X", k(0, 0), k(6, 0), k(9, 1.2), k(12, 1)),
                tr("tile_tab_<i>", "SCA_Y", k(0, 0), k(6, 0), k(9, 1.2), k(12, 1))])
    ev["pick_confirm"] = dict(
        applies_to="the stage is decided (last one standing, or the counterpick)",
        sfx=[dict(frame=0, cue="sfx_menu_confirm")], pivot="tile centre",
        note="the other tiles still 'available' switch to 'unavailable' at frame 4",
        tracks=[tr("tile_<i>", "SCA_X", k(0, 1), k(4, 1.07), k(10, 1)),
                tr("tile_<i>", "SCA_Y", k(0, 1), k(4, 1.07), k(10, 1)),
                tr("tile_face_<i>", "COLOUR", k(0, "gold_lt", "LIN"), k(10, "gold", "LIN"),
                   kind="material"),
                tr("tile_tab_<i>", "SCA_X", k(0, 0), k(4, 0), k(8, 1.2), k(11, 1)),
                tr("tile_tab_<i>", "SCA_Y", k(0, 0), k(4, 0), k(8, 1.2), k(11, 1))] +
               U.lift_tracks("tile_<i>", *LIFT))
    ev["ready_toggle"] = dict(
        applies_to="READY button pressed (dir +1) or cancelled with B (dir -1)",
        sfx=[dict(frame=0, cue="sfx_toggle")], pivot="plate centre",
        tracks=[tr("action_plate", "SCA_X", k(0, 1), k(3, 1.07), k(9, 1)),
                tr("action_plate", "SCA_Y", k(0, 1), k(3, 1.07), k(9, 1)),
                tr("action_face", "COLOUR", k(0, "gold_lt", "LIN"), k(8, "<new face>", "LIN"),
                   kind="material")] + U.lift_tracks("action_plate", *LIFT))
    flips = [k(0, 1, "LIN")]
    f, s, sign, step = 0, 1, -1, 3
    while f < 40:                                 # the coin spins, slowing: 3,3,3,4,4,5,5,6..
        f += step
        flips.append(k(f, 0, "LIN"))
        f += step
        flips.append(k(f, sign, "LIN"))
        sign = -sign
        step = min(6, step + (1 if f > 12 else 0))
    flips.append(k(f + 4, 1, "SPL"))
    ev["coin_flip"] = dict(
        applies_to="coin badge, game 1 stage phase start", sfx=[dict(frame=0, cue="sfx_coin"),
                                                                dict(frame=f, cue="sfx_land")],
        pivot="coin centre",
        note="SCA_X runs 1 -> 0 -> -1 -> 0 -> 1 ...; each time it passes 0 the coin swaps "
             "label (P1/P2) and colour (spinning = gold). It passes 0 an even number of "
             "times (%d), so START it on the winner's face and it lands there; coin_text "
             "fades in after." % sum(1 for kk in flips if kk["value"] == 0),
        tracks=[tr("coin", "SCA_X", *flips),
                tr("coin", "TRA_Y", k(0, 0), k(10, -28, "SPL", 0), k(24, 0, "LIN"),
                   k(f - 4, -5, "SPL", 0), k(f, 0, "LIN"), k(f + 4, 0)),
                tr("coin_text", "ALPHA", k(0, 0, "CON"), k(f + 2, 0, "LIN"), k(f + 8, 1, "LIN"),
                   kind="material"),
                tr("coin_text", "TRA_X", k(f + 2, 12), k(f + 10, 0))])
    ev["coin_badge_in"] = dict(
        applies_to="coin badge appears", sfx=[dict(frame=0, cue="sfx_dialog_open")],
        pivot="badge centre",
        tracks=[tr("coin_dim", "ALPHA", k(0, 0, "LIN"), k(6, 0.45, "LIN"), kind="material"),
                tr("coin_badge", "SCA_X", k(0, 0.9), k(5, 1.02), k(9, 1)),
                tr("coin_badge", "SCA_Y", k(0, 0.9), k(5, 1.02), k(9, 1)),
                tr("coin_badge", "ALPHA", k(0, 0, "LIN"), k(4, 1, "LIN"), kind="material")])
    ev["coin_badge_out"] = dict(
        applies_to="coin badge leaves (then turn_handoff to the winner)", sfx=[],
        tracks=[tr("coin_dim", "ALPHA", k(0, 0.45, "LIN"), k(6, 0, "LIN"), kind="material"),
                tr("coin_badge", "ALPHA", k(0, 1, "LIN"), k(5, 0, "LIN"), kind="material"),
                tr("coin_badge", "SCA_X", k(0, 1), k(5, 0.94)),
                tr("coin_badge", "SCA_Y", k(0, 1), k(5, 0.94))])
    ev["countdown_in"] = dict(
        applies_to="both ready", sfx=[],
        tracks=[tr("countdown_dim", "ALPHA", k(0, 0, "LIN"), k(8, 0.55, "LIN"), kind="material"),
                tr("countdown_slab", "SCA_X", k(0, 0.6), k(6, 1.06), k(10, 1)),
                tr("countdown_slab", "SCA_Y", k(0, 0.6), k(6, 1.06), k(10, 1)),
                tr("countdown_strip", "TRA_X", k(0, 40), k(8, -2), k(11, 0)),
                tr("countdown_strip", "ALPHA", k(0, 0, "LIN"), k(6, 1, "LIN"), kind="material")])
    ev["countdown_tick"] = dict(
        applies_to="each numeral 3, 2, 1 (60 frames each)", sfx=[dict(frame=0, cue="sfx_tick")],
        pivot="numeral centre",
        tracks=[tr("countdown_numeral", "SCA_X", k(0, 1.5), k(6, 0.94), k(10, 1)),
                tr("countdown_numeral", "SCA_Y", k(0, 1.5), k(6, 0.94), k(10, 1)),
                tr("countdown_numeral", "ALPHA", k(0, 0, "LIN"), k(4, 1, "LIN"), k(50, 1, "LIN"),
                   k(59, 0, "LIN"), kind="material"),
                tr("countdown_slab", "SCA_X", k(0, 1.08), k(8, 1)),
                tr("countdown_slab", "SCA_Y", k(0, 1.08), k(8, 1))])
    ev["countdown_out"] = dict(
        applies_to="cancelled (either B) or the match loads", sfx=[],
        tracks=[tr("countdown_dim", "ALPHA", k(0, 0.55, "LIN"), k(6, 0, "LIN"), kind="material"),
                tr("countdown_slab", "ALPHA", k(0, 1, "LIN"), k(5, 0, "LIN"), kind="material"),
                tr("countdown_strip", "ALPHA", k(0, 1, "LIN"), k(5, 0, "LIN"), kind="material")])
    ev["score_update"] = dict(
        applies_to="set score after a game", sfx=[dict(frame=0, cue="sfx_value_change")],
        pivot="score centre",
        tracks=[tr("set_score", "SCA_X", k(0, 1.4), k(6, 0.95), k(10, 1)),
                tr("set_score", "SCA_Y", k(0, 1.4), k(6, 0.95), k(10, 1)),
                tr("set_score", "COLOUR", k(0, "gold_lt", "LIN"), k(20, "bone", "LIN"),
                   kind="material")])
    ev["game_advance"] = dict(
        applies_to="header GAME counter after a match; crown moves to the winner",
        sfx=[], note="the chrome title draws the old string on title_out",
        tracks=[tr("title_out", "TRA_Y", k(0, 0), k(5, -8, "SPL", 0)),
                tr("title_out", "ALPHA", k(0, 1, "LIN"), k(4, 0, "LIN"), kind="material"),
                tr("title", "TRA_Y", k(0, 8), k(6, -1), k(9, 0)),
                tr("title", "ALPHA", k(0, 0, "LIN"), k(5, 1, "LIN"), kind="material"),
                tr("card_crown_<winner>", "SCA_X", k(0, 0), k(6, 1.3), k(10, 1)),
                tr("card_crown_<winner>", "SCA_Y", k(0, 0), k(6, 1.3), k(10, 1))])
    return dict(fps=60, format=FORMAT, space="unsheared - applied before the screen shear",
                value_expressions="dir; <p>, <i>, <new>, <old>, <winner> name instances; "
                                  "colours are kit tokens; <...> values come from the "
                                  "layout's state tables",
                extension="'loop' as in online_motion.json (badge_pips)",
                events=finish(ev),
                sequences=dict(
                    blind_lock=[dict(event="badge_set", on="the player who locked",
                                     badge="locked")],
                    reveal=[dict(event="card_reveal", on="p1"),
                            dict(event="card_reveal", on="p2", at_frame=4),
                            dict(event="phase_change", at_frame=30, phase="stage")],
                    stage_phase_game1=[dict(event="coin_badge_in"), dict(event="coin_flip",
                                                                          at_frame=10),
                                       dict(hold_frames=60), dict(event="coin_badge_out"),
                                       dict(event="turn_handoff", on="coin winner")],
                    strike=[dict(event="strike_stamp", on="tile"),
                            dict(event="turn_handoff", when="the striker's quota is done"),
                            dict(event="pick_confirm", when="one tile is left")],
                    ban=[dict(event="ban_lock"),
                         dict(event="turn_handoff", when="2 bans done")],
                    counterpick=[dict(event="pick_confirm"), dict(event="phase_change",
                                                                  phase="character")],
                    ready=[dict(event="ready_toggle", dir=1), dict(event="badge_set",
                                                                    badge="ready")],
                    both_ready=[dict(event="countdown_in"), dict(event="countdown_tick",
                                                                 numeral="3"),
                                dict(event="countdown_tick", numeral="2", at_frame=60),
                                dict(event="countdown_tick", numeral="1", at_frame=120),
                                dict(note="frame 180: the match")],
                    after_match=[dict(event="game_advance"), dict(event="score_update"),
                                 dict(event="phase_change", phase="stage (counterpick)")]))


# ================================================================ drawing from the JSON
def lookup(tok, el, axes):
    """Resolve '<axis.key>' against the element's state table; other tokens pass through."""
    if not isinstance(tok, str) or not (tok.startswith("<") and tok.endswith(">")):
        return tok
    inner = tok[1:-1]
    if "." not in inner:
        return None
    axis, key = inner.split(".", 1)
    st = el.get("states", {}).get(axis, {}).get(axes.get(axis))
    if st is None:
        return None
    v = st.get(key)
    if isinstance(v, str) and "<p>" in v:
        v = v.replace("<p>", axes.get("p", "p1"))
    return v


def visible(item, axes):
    for a, allowed in item.get("when", {}).items():
        if axes.get(a) not in allowed:
            return False
    return True


def lift_of(el, axes):
    for axis, table in el.get("states", {}).items():
        st = table.get(axes.get(axis))
        if st and "offset" in st:
            return st["offset"]
    return [0, 0]


def draw_el(sc, el, axes, vals, origin=None, placeholder_art=True, skip=()):
    ox, oy = origin if origin is not None else el.get("origin", [0, 0])
    dx, dy = lift_of(el, axes)
    lj = set(el.get("lift_joints") or ([el["lift_joint"]] if el.get("lift_joint") else []))
    for q in el.get("quads", []):
        if q["id"] in skip or not visible(q, axes):
            continue
        colour = lookup(q["colour"], el, axes)
        tex = lookup(q.get("texture"), el, axes)
        if colour is None or (q.get("texture") and not tex):
            continue
        (x0, y0), _, (x1, y1), _ = q["verts"]
        if any(isinstance(v, str) for v in (x0, y0, x1, y1)):
            continue                                # rule-placed; drawn by the caller
        lifted = q.get("joint") in lj
        ddx, ddy = (dx, dy) if lifted else (0, 0)
        r = (x0 + ox + ddx, y0 + oy + ddy, x1 + ox + ddx, y1 + oy + ddy)
        op = lookup(q.get("opacity", 1.0), el, axes)
        if q.get("kind") == "disc_art":
            if not placeholder_art:
                continue
            # preview only: the disc's 64x56 icon is not ours - a tinted placeholder + label
            sc.quad(r, "@face_hi", opacity=op * 0.9, joint=q.get("joint"))
            sc.text("caption", "64×56", (r[0] + r[2]) / 2, (r[1] + r[3]) / 2 + cap("caption") / 2,
                    "ink", align="centre", joint=q.get("joint"), opacity=max(op, 0.5))
            continue
        uv = lookup(q.get("uv"), el, axes) or (0, 0, 1, 1)
        sc.quad(r, colour, tex=tex, uv=tuple(uv), opacity=op, joint=q.get("joint"))
    fits = {}
    for s in el.get("slots", []):
        if s["id"] in skip or not visible(s, axes) or s.get("kind") != "text":
            continue
        v = vals.get(s["id"])
        if v is None:
            continue
        colour = lookup(s["colour"], el, axes)
        if colour is None:
            continue
        lifted = s.get("joint") in lj
        ddx, ddy = (dx, dy) if lifted else (0, 0)
        role = s["role"]
        if role in ("display", "hero"):
            r, txt = role, v.upper()
        else:
            r, txt = fit(role, v, s["max_width_1x"])
        fits[s["id"]] = (r, txt)
        ax, ay = s["anchor"]
        sc.text(r, txt, ax + ox + ddx, ay + oy + ddy, colour, align=s["align"],
                joint=s.get("joint"))
    return fits


# ---- chrome with a per-screen description (or none)
def chrome(sc, title, crumbs, hints, desc):
    sc.footer_end = U.draw_chrome(sc, U.chrome(), title, crumbs, hints, desc)
    sc.crumb_end = U.CRUMB[0] + 22 + sum(text_w("body", c) for c in crumbs) + \
        14 * (len(crumbs) - 1)


def set_joint(sc, n0, joint):
    for it in sc.items[n0:]:
        it["joint"] = it["joint"] or joint


# ---- waiting room
def draw_waiting(view="host", code="KQ7X", plate="copied", copy_state="copied",
                 status=("working", STATUS_EX["waiting"]), ping=None):
    L = WR
    ch = L["chrome"]
    sc = U.Scene(SECTION)
    chrome(sc, ch["title"][view], ch["crumbs"][view], ch["hints"][view],
           ch["description"][view])
    el = L["room_plate"]
    axes = dict(view=view, plate=plate, copy=copy_state)
    vals = {"char_%d" % i: c for i, c in enumerate(code)}
    vals["code_label"] = "ROOM CODE"
    vals["copy_text"] = el["states"]["copy"][copy_state]["text_string"]
    vals["share_line"] = ("Send it to your opponent. They pick Join and type it in."
                          if view == "host" else "Joining room %s..." % code)
    vals["sub_line"] = "Codes use A-Z and 2-9, never I, O, 0 or 1." if view == "host" else \
        "The host's screen shows the same code."
    sc.fits = draw_el(sc, el, axes, vals)
    ON.draw_status(sc, status[0], status[1], ping=ping)
    return sc


# ---- code entry
def draw_code_entry(chars, active, field="editing", status=("idle", None), invalid=False):
    L = CE
    ch = L["chrome"]
    sc = U.Scene(SECTION)
    chrome(sc, ch["title"], ch["crumbs"], ch["hints"], ch["description"])
    for q in L["panel"]["quads"]:
        (x0, y0), _, (x1, y1), _ = q["verts"]
        sc.quad((x0, y0, x1, y1), q["colour"], joint=q.get("joint"))
    F = L["field"]
    fel = dict(F, states=F["states"])
    draw_el(sc, dict(quads=F["quads"], slots=F["slots"], states=F["states"]),
            dict(field=field), dict(instruction="Type the 4-character room code from your host."),
            origin=(0, 0))
    st = F["slot_template"]
    order = [i for i in range(CODE_LEN) if i != active] + ([active] if active is not None else [])
    for i in order:
        c = chars[i] if i < len(chars) else None
        if invalid and c:
            state = "invalid"
        elif i == active:
            state = "active_filled" if c else "active_empty"
        else:
            state = "filled" if c else "empty"
        el = copy.deepcopy(st)
        for item in el["quads"] + el["slots"]:
            if "joint" in item:
                item["joint"] = item["joint"].replace("<i>", str(i))
        el["lift_joint"] = "code_slot_%d" % i
        # every joint in the slot lifts with it (caret, char)
        for item in el["quads"] + el["slots"]:
            if item.get("joint", "").startswith(("code_char_", "code_caret")):
                item["joint"] = el["lift_joint"]
        draw_el(sc, el, dict(slot=state), dict(char=c), origin=(cell_x(i), CE_CELL_Y[0]))
    if active is not None and field != "joining":
        A = F["arrows"]
        cx = cell_x(active) + CELL_W / 2 + LIFT[0]
        draw_el(sc, A, dict(arrows="ng"), dict(arrow_up="↑", arrow_down="↓"),
                origin=(cx, LIFT[1]))
    H = L["hints_row"]
    draw_el(sc, dict(quads=H["quads"], slots=H["slots"]), {},
            dict(keyboard_text="Or type it on a keyboard", paste_text="Paste",
                 alphabet_note="Codes use A-Z and 2-9, never I, O, 0 or 1."), origin=(0, 0))
    pq = H["quads"][1]
    pw = text_w("body", "Paste")
    y0, y1 = pq["verts"][0][1], pq["verts"][2][1]
    sc.quad((PLATE_X1 - 4 - pw - 16, y0, PLATE_X1 - 4 - pw, y1), "bone", tex="glyph_y",
            joint="room_panel")
    stt, txt = status
    ON.draw_status(sc, stt, txt or L["status_strip"]["examples"]["idle"])
    return sc


# ---- lobby
def draw_card(sc, el, axes, name, badge_text):
    vals = dict(port_label=el["port"].upper(), you_tag="YOU", hidden_mark="?", name=name,
                badge_text=badge_text)
    n_start = len(sc.items)
    fits = draw_el(sc, el, axes, vals)
    # the badge rect follows its text (rule in the layout)
    if axes.get("badge") in ("waiting", "picking", "locked", "ready"):
        ox, oy = el["origin"]
        dx, dy = lift_of(el, axes)
        st = el["states"]["badge"][axes["badge"]]
        w = 5 + 12 + 4 + text_w("caption", badge_text) + 6
        m = el["port"] == "p2"
        x_edge = (CARD_W - 90) if m else 90
        x0, x1 = (x_edge - w, x_edge) if m else (x_edge, x_edge + w)
        n0 = len(sc.items)
        sc.quad((x0 + ox + dx, 47 + oy + dy, x1 + ox + dx, 65 + oy + dy), st["block"],
                joint="card_badge_" + el["port"])
        # the block must sit under icon + text: move it before them
        item = sc.items.pop()
        first = next(i for i, it in enumerate(sc.items)
                     if i >= n_start and it["joint"] == "card_badge_" + el["port"])
        sc.items.insert(first, item)
    return fits


def draw_action(sc, L, state):
    el = L["action_plate"]
    st = el["states"]["action"][state]
    axes = dict(action=state)
    draw_el(sc, el, axes, {}, skip=("action_text", "action_icon"))
    ax0, ay0, ax1, ay1 = ACTION
    dx, dy = st.get("offset", [0, 0])
    base = base_for("row", ay0, ay1) + dy
    txt = st["string"]
    r, s = fit("row", txt, ax1 - ax0 - 12 - (st.get("icon_w", 0) + 6 if st.get("icon") else 0))
    w = text_w(r, s)
    iw = st.get("icon_w", 0) if st.get("icon") else 0
    g = w + (iw + 6 if iw else 0)
    x = (ax0 + ax1) / 2 - g / 2 + dx
    if st.get("icon") == "pips":
        cy = base - cap("row") / 2
        for i in range(3):
            sc.quad((x + i * 6, cy - 3 - (1 if i == 0 else 0), x + i * 6 + 4, cy + 3 + (1 if i == 0 else 0)),
                    st["icon_colour"], opacity=1.0 if i == 0 else 0.35,
                    joint="badge_pip_%d" % i)
    elif st.get("icon"):
        cy = base - cap("row") / 2
        sc.quad((x, cy - 8, x + iw, cy + 8), st["icon_colour"], tex=st["icon"],
                joint="action_plate")
    sc.text(r, s, x + (iw + 6 if iw else 0), base, st["text"], joint="action_plate")
    return r, s


def draw_lobby(game=1, phase="character", banner=("CHARACTER PICK", INSTR_MAX),
               cards=None, action=None, turn=None, tiles=None, remote=None, coin=None,
               countdown=None, score="0 - 0", status="Opponent: Wario Man, Microgame",
               ping=42, hints=None):
    L = LB
    ch = L["chrome"]
    sc = U.Scene(SECTION)
    chrome(sc, "GAME %d" % game, ch["crumbs"], hints or ch["hints_by_phase"].get(phase, ch["hints"]),
           "")
    # score plaque
    sp = L["score_plaque"]
    draw_el(sc, sp, {}, dict(set_label="SET", set_score=score), origin=(0, 0))
    # banner
    draw_el(sc, L["phase_banner"], dict(phase="stage" if phase.startswith("stage") else phase),
            dict(phase_title=banner[0], instruction=banner[1]), origin=(0, 0))
    if action:
        sc.action_fit = draw_action(sc, L, action)
    # cards (the active one last)
    cards = cards or {}
    order = sorted(("p1", "p2"), key=lambda p: cards[p].get("turn") == "active")
    sc.card_fits = {}
    for p in order:
        el = L["cards"][0 if p == "p1" else 1]
        c = cards[p]
        axes = dict(turn=c.get("turn", "idle"), portrait=c.get("portrait", "empty"),
                    badge=c.get("badge", "none"), crown=c.get("crown", "no"),
                    you=c.get("you", "no"))
        sc.card_fits[p] = draw_card(sc, el, axes, c["name"],
                                    BADGES.get(axes["badge"], ""))
    if turn:
        draw_el(sc, L["turn_arrow"], dict(turn=turn), {}, origin=(0, 0))
    # grid
    G = L["stage_grid"]
    tiles = tiles or ["available"] * 6
    order = sorted(range(6), key=lambda i: tiles[i] in ("hovered", "picked"))
    sc.tile_fits = {}
    for i in order:
        state = tiles[i]
        el = dict(G["tiles"][i], states=dict(tile=G["tile_states"]))
        p = None
        if state == "hover_remote":
            p = remote or "p2"
        elif state.startswith("banned"):
            p = state.split(":")[1] if ":" in state else "p1"
            state = "banned"
        elif state.startswith("struck_"):
            p = state[7:]
        vals = dict(name=STAGES[i], tab_text=(p or "").upper())
        sc.tile_fits[i] = draw_el(sc, el, dict(tile=state, p=p or "p1"), vals)
    # status (the description strip's rect)
    draw_el(sc, L["lobby_status"], {}, dict(status_text=status, ping_ms="%d ms" % ping),
            origin=(0, 0), skip=tuple("bar_%d" % (i + 1) for i in range(4)))
    lv = next(lv for lv in ON.LAY["status_strip"]["ping"]["levels"]
              if lv["max_ms"] is None or ping <= lv["max_ms"])
    bq = L["lobby_status"]["quads"][1]
    (bx0, by0), _, (bx1, by1), _ = bq["verts"]
    for i in range(4):
        sc.quad((bx0, by0, bx1, by1), lv["colour"] if i < lv["bars"] else "@face",
                tex="sig_bar_%d" % (i + 1), joint="ping")
    if coin:
        el = L["coin_badge"]
        n0 = len(sc.items)
        draw_el(sc, el, dict(coin=coin), dict(coin_label=coin.upper(), coin_caption="COIN FLIP",
                                              coin_text="%s STRIKES FIRST" % coin.upper()),
                origin=(0, 0))
        for it in sc.items[n0:]:
            if it["joint"] == "coin_dim":
                it["tag"], it["sheared"] = "decor", False
    if countdown:
        el = L["countdown"]
        n0 = len(sc.items)
        draw_el(sc, el, {}, dict(numeral=countdown[0], stage_line=countdown[1]), origin=(0, 0))
        for it in sc.items[n0:]:
            if it["joint"] == "countdown_dim":
                it["tag"], it["sheared"] = "decor", False
    return sc


# ================================================================ parts sheets
def parts_tiles():
    """Every tile state, in the grid's own rects (a 3x2 page per 6 states), plus 2 more."""
    sc = U.Scene(SECTION)
    states = ["available", "hovered", "hover_remote", "struck_p1", "struck_p2", "banned:p2",
              "picked", "unavailable"]
    G = LB["stage_grid"]
    for n, state in enumerate(states):
        c, r = n % 4, n // 4
        x, y = 40 + c * 146, 60 + r * 170
        el = dict(G["tiles"][n % 6], states=dict(tile=G["tile_states"]))
        p = None
        st = state
        if state == "hover_remote":
            p = "p2"
        elif state.startswith("banned"):
            p, st = "p2", "banned"
        elif state.startswith("struck_"):
            p = state[7:]
        n0 = len(sc.items)
        draw_el(sc, el, dict(tile=st, p=p or "p1"), dict(name=STAGES[n % 6],
                                                          tab_text=(p or "").upper()),
                origin=(x, y))
        sc.text("caption", state.replace(":p2", " (P2)"), x, y + 110, "bone")
        for it in sc.items[n0:]:
            it["sheared"] = False
            it["verts"] = [(vx * 0.9 + 10, vy) for vx, vy in it["verts"]]
    sc.parts = True
    return sc


def parts_cards():
    sc = U.Scene(SECTION)
    combos = [dict(turn="idle", portrait="empty", badge="waiting"),
              dict(turn="active", portrait="empty", badge="picking", you="yes"),
              dict(turn="idle", portrait="hidden", badge="locked"),
              dict(turn="idle", portrait="shown", badge="ready", crown="yes"),
              dict(turn="active", portrait="shown", badge="none", crown="yes", you="yes")]
    y = 40
    for n, cmb in enumerate(combos):
        for p, x in (("p1", 30), ("p2", 330)):
            el = copy.deepcopy(LB["cards"][0 if p == "p1" else 1])
            el["origin"] = [x, y]
            axes = dict(dict(turn="idle", portrait="empty", badge="none", crown="no", you="no"),
                        **cmb)
            n0 = len(sc.items)
            draw_card(sc, el, axes, NAME_MAX if n % 2 == 0 else "Captain Falcon Alt 2",
                      BADGES.get(axes["badge"], ""))
            for it in sc.items[n0:]:
                it["sheared"] = False
        y += 84
    # action plate states
    y = 470 - 50
    sc.parts = True
    return sc


def parts_action():
    sc = U.Scene(SECTION)
    y0 = 40
    for n, state in enumerate(ACTION_STATES):
        sub = U.Scene(SECTION)
        draw_action(sub, LB, state)
        dx = 40 + (n % 2) * 300 - ACTION[0]
        dy = y0 + (n // 2) * 70 - ACTION[1]
        for it in sub.items:
            it["verts"] = [(vx + dx, vy + dy) for vx, vy in it["verts"]]
            it["sheared"] = False
        sc.items += sub.items
        sc.text("caption", state, 40 + (n % 2) * 300, y0 + (n // 2) * 70 + 62, "bone")
    # the coin in three states
    for n, cs_ in enumerate(("p1", "p2", "spinning")):
        x = 60 + n * 120
        sc.quad((x, 280, x + 48, 328), sc.col("port:p1") and ("port:" + cs_ if cs_ != "spinning"
                                                             else "gold"), tex="ico_coin")
        sc.text("title", "P1" if cs_ != "p2" else "P2", x + 24, base_for("title", 280, 328), "ink",
                align="centre")
        sc.text("caption", "coin " + cs_, x, 346, "bone")
    for it in sc.items:
        it["sheared"] = False
    return sc


def parts_code():
    sc = U.Scene(SECTION)
    st = CE["field"]["slot_template"]
    for n, (state, c) in enumerate((("empty", None), ("filled", "Q"), ("active_empty", None),
                                    ("active_filled", "7"), ("invalid", "X"))):
        x = 50 + n * 110
        el = copy.deepcopy(st)
        for item in el["quads"] + el["slots"]:
            if "joint" in item:
                item["joint"] = "code_slot_0"
        el["lift_joint"] = "code_slot_0"
        el.pop("lift_joints", None)
        sc.quad((x - 8, 112, x + CELL_W + 8, 120 + CELL_H + 8), "ink")   # the field plate
        draw_el(sc, el, dict(slot=state), dict(char=c), origin=(x, 120))
        sc.text("caption", state, x, 240, "bone")
    for it in sc.items:
        it["sheared"] = False
    return sc


# ================================================================ checks
def joint_ext(motions):
    ext = {}
    for mot in motions:
        for e in mot["events"].values():
            if e.get("offscreen"):
                continue
            for t in e["tracks"]:
                if t["kind"] != "joint":
                    continue
                vals = [kk["value"] for kk in t["keys"] if isinstance(kk["value"], (int, float))]
                if not vals:
                    continue
                tgt = t["target"]
                j = ext.setdefault(tgt, dict(tx=[0, 0], ty=[0, 0], s=1.0))
                lo, hi = min(vals + [0]), max(vals + [0])
                if t["channel"] == "TRA_X":
                    j["tx"] = [min(j["tx"][0], lo), max(j["tx"][1], hi)]
                elif t["channel"] == "TRA_Y":
                    j["ty"] = [min(j["ty"][0], lo), max(j["ty"][1], hi)]
                elif t["channel"].startswith("SCA"):
                    j["s"] = max(j["s"], max(abs(v) for v in vals))
    return ext


def ext_for(ext, joint):
    """Motion targets name instances with <p>, <i>, <new>...: match by pattern."""
    import re
    if not joint:
        return dict(tx=[0, 0], ty=[0, 0], s=1.0)
    out = dict(tx=[0, 0], ty=[0, 0], s=1.0)
    for tgt, e in ext.items():
        pat = "^" + re.sub(r"<[^>]+>", r"[A-Za-z0-9_]+", re.escape(tgt).replace(r"\<", "<")
                           .replace(r"\>", ">")) + "$"
        if re.match(pat, joint):
            out = dict(tx=[min(out["tx"][0], e["tx"][0]), max(out["tx"][1], e["tx"][1])],
                       ty=[min(out["ty"][0], e["ty"][0]), max(out["ty"][1], e["ty"][1])],
                       s=max(out["s"], e["s"]))
    return out


LIFT_JOINT_PREFIX = ("card_p", "tile_", "action_plate", "code_slot_")


def check_safe(name, sc, ext):
    """Every non-decor item stays in title-safe at peak motion: each joint's extreme
    translation plus its peak scale about the joint group's centre."""
    errs = []
    sx0, sy0, sx1, sy1 = U.SAFE
    groups = {}
    for it in sc.items:
        groups.setdefault(it["joint"], []).append(it)
    for j, items in groups.items():
        xs = [v[0] for it in items for v in it["verts"]]
        ys = [v[1] for it in items for v in it["verts"]]
        gcx, gcy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        e = ext_for(ext, j)
        lifted = j and j.startswith(LIFT_JOINT_PREFIX)
        over = 0.3 if lifted else 1.0             # lift is drawn at rest; add the overshoot
        bad = None
        for it in items:
            if it["tag"] == "decor":
                continue
            for vx, vy in it["verts"]:
                for ddx in (e["tx"][0] * over, e["tx"][1] * over):
                    for ddy in (e["ty"][0] * over, e["ty"][1] * over):
                        px = gcx + (vx - gcx) * e["s"] + ddx
                        py = gcy + (vy - gcy) * e["s"] + ddy
                        if it["sheared"]:
                            px, py = U.shear_pt(px, py)
                        if not (sx0 - 1e-6 <= px <= sx1 + 1e-6 and sy0 - 1e-6 <= py <= sy1 + 1e-6):
                            bad = (px, py)
                            break
                    if bad:
                        break
                if bad:
                    break
            if bad:
                break
        if bad:
            errs.append("%s: joint %s leaves title-safe at (%.1f, %.1f) at peak motion"
                        % (name, j, bad[0], bad[1]))
    return errs


def contrast_pairs():
    """(name, fg, bg, need) for every text and mark in every state, generated from the
    state tables so a new state can't slip past."""
    out = []
    G = LB["stage_grid"]
    for st, v in G["tile_states"].items():
        for p in ("p1", "p2"):
            def c(key):
                x = v.get(key)
                return x.replace("<p>", p) if isinstance(x, str) else x
            out.append(("tile %s name" % st, c("name"), c("face"), kit.MIN_TEXT))
            if v.get("tab_text"):
                out.append(("tile %s tab text (%s)" % (st, p), c("tab_text"), c("tab"),
                            kit.MIN_TEXT))
            if v.get("mark_colour"):
                # the brief asks 4.5:1 for port-coloured marks too, not just 3:1
                out.append(("tile %s mark (%s)" % (st, p), c("mark_colour"), c("face"),
                            kit.MIN_TEXT))
            if st == "picked":
                out.append(("tile picked tab icon", "gold_lt", "ink", kit.MIN_GRAPHIC))
                out.append(("tile picked tab on face", c("tab"), c("face"), kit.MIN_GRAPHIC))
    for p in ("p1", "p2"):
        out.append(("card port label %s" % p, "ink", "port:" + p, kit.MIN_TEXT))
        out.append(("tile hover_remote outline vs gutter %s" % p, "port:" + p, "ink",
                    kit.MIN_GRAPHIC))
        # against the tile's own face it is only ~2.6:1 - the port tab (text, 4.8:1) is
        # what carries the state; reported, floor 1.5 so the ring still reads as a ring
        out.append(("tile hover_remote outline vs face %s" % p, "port:" + p, "@face", 1.5))
    for st, v in LB["cards"][0]["states"]["badge"].items():
        if "block" in v:
            out.append(("badge %s text" % st, v["text"], v["block"], kit.MIN_TEXT))
            out.append(("badge %s icon" % st, v["icon_colour"], v["block"], kit.MIN_GRAPHIC))
    out += [("card name", "bone", "@face", kit.MIN_TEXT),
            ("card you tag", "muted", "@face", kit.MIN_TEXT),
            ("card hidden '?'", "@face_hi", "ink", kit.MIN_TEXT),
            ("card crown", "gold", "@face", kit.MIN_GRAPHIC),
            ("card outline active", "gold", "@bg", kit.MIN_GRAPHIC),
            ("banner title", "bone", "ink", kit.MIN_TEXT),
            ("banner instruction", "muted", "ink", kit.MIN_TEXT),
            ("score label", "muted", "ink", kit.MIN_TEXT),
            ("score", "bone", "ink", kit.MIN_TEXT),
            ("turn arrow", "gold", "@bg", kit.MIN_GRAPHIC),
            ("coin caption", "muted", "@face", kit.MIN_TEXT),
            ("coin text", "bone", "@face", kit.MIN_TEXT),
            ("coin label p1", "ink", "port:p1", kit.MIN_TEXT),
            ("coin label p2", "ink", "port:p2", kit.MIN_TEXT),
            ("coin label spinning", "ink", "gold", kit.MIN_TEXT),
            ("countdown numeral", "ink", "gold", kit.MIN_TEXT),
            ("countdown stage line", "bone", "ink", kit.MIN_TEXT),
            ("lobby status", "bone", "ink", kit.MIN_TEXT),
            ("lobby ping ms", "muted", "ink", kit.MIN_TEXT)]
    for st, v in ACTION_STATES.items():
        out.append(("action %s text" % st, v["text"], v["face"], kit.MIN_TEXT))
        if v.get("icon"):
            out.append(("action %s icon" % st, v["icon_colour"], v["face"], kit.MIN_GRAPHIC))
    # waiting room
    wr = WR["room_plate"]["states"]
    for st, v in wr["plate"].items():
        out.append(("room code %s" % st, v["char"], "@bg", kit.MIN_TEXT))
        out.append(("room accent %s" % st, v["accent"], "ink", kit.MIN_GRAPHIC))
    for st, v in wr["copy"].items():
        out.append(("copy row %s text" % st, v["text"], "@face", kit.MIN_TEXT))
        out.append(("copy row %s icon" % st, v["icon_colour"], "@face", kit.MIN_GRAPHIC))
    out += [("room label", "gold", "@face", kit.MIN_TEXT),
            ("room share line", "muted", "@face", kit.MIN_TEXT)]
    # code entry
    for st, v in CE["field"]["slot_template"]["states"]["slot"].items():
        out.append(("code slot %s char" % st, v["char"], v["face"], kit.MIN_TEXT))
        if v.get("dash"):
            out.append(("code slot %s dash" % st, v["dash"], v["face"], kit.MIN_GRAPHIC))
        if v.get("caret"):
            out.append(("code slot %s caret" % st, v["caret"], v["face"], kit.MIN_GRAPHIC))
    out += [("code slot invalid bar", "danger", "@bg", kit.MIN_GRAPHIC),
            ("code arrows", "gold", "@face", kit.MIN_GRAPHIC),
            ("code instruction", "bone", "@face", kit.MIN_TEXT),
            ("code hints", "muted", "@face", kit.MIN_TEXT),
            ("code keyboard icon", "muted", "@face", kit.MIN_GRAPHIC)]
    return out


def check_all(scenes, layouts, motions):
    errs, report = [], {}
    # 1. slots fit their maxima; caps-only roles; footer/breadcrumb (the kit's walker)
    kerrs, _ = U.check({n: s for n, s in scenes.items() if not getattr(s, "parts", False)},
                       dict(events={}), dict(layouts, widgets=U.WID))
    errs += [e for e in kerrs if "leaves title-safe" not in e]   # own peak check below
    # 2. fit-rule strings: player names and stage names never truncate
    card = LB["cards"][0]
    name_slot = next(s for s in card["slots"] if s["id"] == "name")
    report["names"] = {}
    for n in kit.NAME_FIT["test_names"]:
        r, out = fit("body", n, name_slot["max_width_1x"])
        report["names"][n] = r
        if out != n:
            errs.append("card name '%s' truncates to '%s'" % (n, out))
    tile_slot = next(s for s in LB["stage_grid"]["tiles"][0]["slots"] if s["id"] == "name")
    report["stages"] = {}
    for n in STAGES:
        if text_w("body", n) > tile_slot["max_width_1x"]:
            errs.append("stage '%s' needs the fit rule (%.1f > %.1f)"
                        % (n, text_w("body", n), tile_slot["max_width_1x"]))
        report["stages"][n] = round(text_w("body", n), 1)
    r, out = fit("body", STAGE_WORST, tile_slot["max_width_1x"])
    report["stage_worst_28"] = [STAGE_WORST, r, out == STAGE_WORST]
    if out != STAGE_WORST:
        errs.append("stage worst '%s' truncates" % STAGE_WORST)
    # every action string, badge, phase title fits without stepping down
    for st, v in ACTION_STATES.items():
        room = ACTION[2] - ACTION[0] - 12 - (v.get("icon_w", 0) + 6 if v.get("icon") else 0)
        if text_w("row", v["string"]) > room:
            errs.append("action %s '%s' needs %.1f px, has %.1f" % (st, v["string"],
                                                                     text_w("row", v["string"]),
                                                                     room))
    for s in ("CHARACTER PICK", "STAGE STRIKING", "COUNTERPICK", "READY CHECK"):
        if text_w("title", s) > BANNER[2] - BANNER[0] - 30:
            errs.append("phase title '%s' too wide" % s)
    # room code: every alphabet character fits a cell at display
    wmax = max(text_w("display", c) for c in ROOM_ALPHABET)
    report["room_char_max_px"] = [round(wmax, 1), CELL_W - 8]
    if wmax > CELL_W - 8:
        errs.append("room code char %.1f px > cell %d" % (wmax, CELL_W - 8))
    missing = [c for c in ROOM_ALPHABET + "?123" if c not in U.ROLES["display"]["glyphs"]]
    if missing:
        errs.append("display atlas lacks %s" % missing)
    # 3. title-safe incl. peak motion (own motion + the kit's)
    ext = joint_ext(motions)
    for n, sc in scenes.items():
        if not getattr(sc, "parts", False):
            errs += check_safe(n, sc, ext)
    # 4. regions don't collide (with lift)
    if GRID[1] + LIFT[1] < CARD_Y + CARD_H + 3:
        errs.append("grid overlaps the cards")
    if tile_rect(5)[3] + 3 > U.DESC[1]:
        errs.append("grid runs into the status strip")
    if CARD_Y + LIFT[1] - 3 < BANNER[3]:
        errs.append("lifted card outline touches the banner")
    if CE_CELL_Y[1] > CE_PLATE_Y[1] or PLATE_X1 > PANEL[2]:
        errs.append("code field leaves the panel")
    # 5. contrast, every state
    sc = U.Scene(SECTION)
    report["contrast"] = {}
    for name, fg, bg, need in contrast_pairs():
        c = K.contrast(K.hexrgb(sc.col(fg)), K.hexrgb(sc.col(bg)))
        report["contrast"][name] = round(c, 2)
        if c < need - 1e-9:
            errs.append("contrast %s: %s on %s %.2f:1 < %.1f" % (name, fg, bg, c, need))
    # 6. P1 / P2 marks under colour blindness, and never colour only
    report["p1_p2_cvd_dE"] = {kind: round(K.de2000(K.simulate(K.hexrgb(kit.PORTS["p1"]), kind),
                                                   K.simulate(K.hexrgb(kit.PORTS["p2"]), kind)), 1)
                              for kind in kit.CVD_KINDS}
    for kind, d in report["p1_p2_cvd_dE"].items():
        if d < kit.MIN_PORT_DE.get(kind, 8):
            errs.append("P1/P2 only dE %.1f under %s" % (d, kind))
    ts = LB["stage_grid"]["tile_states"]
    if ts["struck_p1"]["mark"] == ts["struck_p2"]["mark"]:
        errs.append("P1 and P2 strikes share a shape")
    if len({ts["struck_p1"]["mark"], ts["struck_p2"]["mark"], ts["banned"]["mark"]}) != 3:
        errs.append("strike / ban marks are not all different shapes")
    # the strike shapes must also differ as pixels (not just names)
    import numpy as np
    a = np.asarray(Image.open(U.tex_path("ico_strike_x")).getchannel("A"), dtype=float) / 255
    b = np.asarray(Image.open(U.tex_path("ico_strike_o")).getchannel("A"), dtype=float) / 255
    iou = (np.minimum(a, b).sum() / np.maximum(a, b).sum())
    report["strike_shape_overlap_iou"] = round(float(iou), 3)
    if iou > 0.5:
        errs.append("strike shapes overlap too much (IoU %.2f)" % iou)
    return errs, report


def memory(sc):
    names = {it["tex"] for it in sc.items if it["tex"]}
    total = 0
    for n in names:
        w, h = Image.open(U.tex_path(n)).size
        total += w * h // 2                        # everything on these screens is I4
    return total, sorted(names)


# ================================================================ main
WR = CE = LB = None


def main():
    global WR, CE, LB
    sys.stdout.reconfigure(encoding="utf-8")
    for sub in ("2x", "1x", "preview"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    U.WID, U.DLG, U.CUR = U.widgets(), U.dialog(), U.cursor_layout()
    U.ROW_T = U.list_layout()["templates"][0]
    ON.LAY = ON.layout()
    errs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(device_scale_factor=1)
        ierrs, icon_rows = build_icons(page)
        errs += ierrs

        WR, CE, LB = waiting_room_layout(), code_entry_layout(), lobby_layout()
        mots = dict(waiting_room=waiting_room_motion(), code_entry=code_entry_motion(),
                    lobby=lobby_motion())

        # ---- previews (each composed from the layout dicts written below)
        LONG = NAME_MAX
        SHORT = "Captain Falcon Alt 2"
        sc = {}
        sc["waiting_host"] = draw_waiting("host", "KQ7X", "copied", "copied",
                                          ("working", STATUS_EX["waiting"]))
        sc["waiting_host_found"] = draw_waiting("host", "WM8Y", "ng", "idle",
                                                ("connected", STATUS_EX["found"]), ping=42)
        sc["waiting_guest"] = draw_waiting("guest", "KQ7X", "joining", "idle",
                                           ("working", STATUS_EX["joining"]))
        sc["code_empty"] = draw_code_entry("", 0, field="editing")
        sc["code_partial"] = draw_code_entry("KQ", 2, field="editing",
                                             status=("idle", "Enter the code, then press A "
                                                             "to join."))
        sc["code_invalid"] = draw_code_entry("KQ7W", 3, field="invalid", invalid=True,
                                             status=("failed", "No room KQ7W. Check the code "
                                                               "with your host."))
        sc["lobby_g1_blind"] = draw_lobby(
            1, "character", ("CHARACTER PICK", INSTR_MAX),
            cards=dict(p1=dict(portrait="empty", badge="picking", you="yes", name=LONG),
                       p2=dict(portrait="hidden", badge="locked", name=LONG)),
            score="0 - 0")
        sc["lobby_g1_reveal"] = draw_lobby(
            1, "character", ("CHARACTER PICK", "Both locked in!"),
            cards=dict(p1=dict(portrait="shown", badge="locked", you="yes", name=LONG),
                       p2=dict(portrait="shown", badge="locked", name=LONG)),
            score="0 - 0")
        sc["lobby_g1_coin"] = draw_lobby(
            1, "stage_strike", ("STAGE STRIKING", "Flipping for first strike..."),
            cards=dict(p1=dict(portrait="shown", you="yes", name=LONG),
                       p2=dict(portrait="shown", name=LONG)),
            coin="p2", score="0 - 0")
        sc["lobby_g1_strike"] = draw_lobby(
            1, "stage_strike", ("STAGE STRIKING", "P1 strikes 2 stages - 1 to go"),
            cards=dict(p1=dict(portrait="shown", turn="active", you="yes", name=LONG),
                       p2=dict(portrait="shown", name=LONG)),
            action="your_turn", turn="p1",
            tiles=["struck_p2", "available", "hovered", "struck_p1", "struck_p2", "available"],
            score="0 - 0")
        sc["lobby_g1_strike_remote"] = draw_lobby(
            1, "stage_strike", ("STAGE STRIKING", "P2 strikes 2 stages"),
            cards=dict(p1=dict(portrait="shown", you="yes", name=LONG),
                       p2=dict(portrait="shown", turn="active", name=LONG)),
            action="their_turn", turn="p2",
            tiles=["available", "available", "hover_remote", "available", "struck_p1",
                   "available"], remote="p2", score="0 - 0")
        sc["lobby_g1_final"] = draw_lobby(
            1, "stage_strike", ("STAGE STRIKING", "Stage: Fountain of Dreams"),
            cards=dict(p1=dict(portrait="shown", you="yes", name=LONG),
                       p2=dict(portrait="shown", name=LONG)),
            tiles=["struck_p2", "struck_p1", "struck_p1", "picked", "struck_p2", "struck_p2"],
            score="0 - 0")
        sc["lobby_g2_ban"] = draw_lobby(
            2, "stage_ban", ("COUNTERPICK", "Counterpick: P2 banned 2, P1 picks"),
            cards=dict(p1=dict(portrait="shown", turn="active", you="yes", name=LONG),
                       p2=dict(portrait="shown", crown="yes", name=LONG)),
            action="your_turn", turn="p1",
            tiles=["available", "banned:p2", "available", "hovered", "banned:p2",
                   "available"],
            score="0 - 1", hints=[["a", "Pick"], ["dpad", "Move"], ["b", "Leave"]])
        sc["lobby_g2_char"] = draw_lobby(
            2, "character", ("CHARACTER PICK", "P2 picks first, then P1"),
            cards=dict(p1=dict(portrait="shown", badge="waiting", you="yes", name=LONG),
                       p2=dict(portrait="shown", badge="picking", turn="active", crown="yes",
                               name=LONG)),
            action="their_turn", turn="p2",
            tiles=["unavailable", "banned:p2", "unavailable", "picked", "banned:p2",
                   "unavailable"], score="0 - 1")
        sc["lobby_ready"] = draw_lobby(
            3, "ready", ("READY CHECK", "Both ready?"),
            cards=dict(p1=dict(portrait="shown", badge="ready", you="yes", crown="yes",
                               name=LONG),
                       p2=dict(portrait="shown", badge="waiting", name=LONG)),
            action="ready_wait",
            tiles=["unavailable", "banned:p1", "picked", "unavailable", "banned:p1",
                   "unavailable"], score="1 - 1")
        sc["lobby_countdown"] = draw_lobby(
            3, "ready", ("READY CHECK", "Both ready!"),
            cards=dict(p1=dict(portrait="shown", badge="ready", you="yes", crown="yes",
                               name=LONG),
                       p2=dict(portrait="shown", badge="ready", name=LONG)),
            action="ready_both",
            tiles=["unavailable", "banned:p1", "picked", "unavailable", "banned:p1",
                   "unavailable"], score="1 - 1", countdown=("2", "Final Destination"))
        parts = dict(parts_tiles=parts_tiles(), parts_cards=parts_cards(),
                     parts_action=parts_action(), parts_code=parts_code())
        for v in parts.values():
            v.parts = True

        # ---- textures per layout (png2gx --layout converts these)
        own = {r["name"]: r for r in icon_rows}
        on_rows = {t["name"]: t for t in json.load(open(os.path.join(ROOT, "out_online",
                                                                     "icons_manifest.json"),
                                                        encoding="utf-8"))["textures"]}

        def tex_rows(scenes_):
            names = set()
            for s_ in scenes_:
                names |= {it["tex"] for it in s_.items if it["tex"]}
            rows = []
            for n in sorted(names):
                src = own.get(n) or on_rows.get(n)
                if src:
                    rows.append(dict(name=n, file_2x=src["file_2x"], file_1x=src["file_1x"],
                                     size_2x=src["size_2x"], format="I4", fallback="IA4"))
            return rows
        WR["textures"] = tex_rows([sc["waiting_host"], sc["waiting_host_found"],
                                   sc["waiting_guest"]])
        CE["textures"] = tex_rows([sc["code_empty"], sc["code_partial"], sc["code_invalid"]])
        LB["textures"] = tex_rows([v for n, v in sc.items() if n.startswith("lobby")] +
                                  list(parts.values()))
        # icons used by rules but not in a preview (spinning coin etc.) are all in parts
        missing = set(own) - {t["name"] for L in (WR, CE, LB) for t in L["textures"]}
        if missing:
            errs.append("masks drawn but used by no layout: %s" % sorted(missing))

        # ---- checks
        layouts = dict(waiting_room=WR, code_entry=CE, lobby=LB)
        kmot = U.motion()
        omot = json.load(open(os.path.join(ROOT, "out_online", "online_motion.json"),
                              encoding="utf-8"))
        omot = dict(events={n: e for n, e in omot["events"].items()})
        cerrs, report = check_all(sc, layouts, list(mots.values()) + [kmot, omot])
        errs += cerrs

        # ---- write
        for n, L in layouts.items():
            with open(os.path.join(OUT, "%s_layout.json" % n), "w", encoding="utf-8") as fh:
                json.dump(L, fh, indent=1, ensure_ascii=False)
            with open(os.path.join(OUT, "%s_motion.json" % n), "w", encoding="utf-8") as fh:
                json.dump(mots[n], fh, indent=1, ensure_ascii=False)
        with open(os.path.join(OUT, "icons_manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(provenance="Original pictograms drawn in pipeline/lobby.py (SVG on "
                                      "a 64 grid); nothing traced, sampled or recoloured from "
                                      "Melee or any other game.", textures=icon_rows), fh,
                      indent=1)

        mem = {}
        for n, s_ in dict(sc, **parts).items():
            b, names = memory(s_)
            mem[n] = dict(bytes_2x=b, textures=names)
            if b > U.BUDGET and not n.startswith("parts"):
                errs.append("%s uses %.0f KB > 1 MB" % (n, b / 1024))
        kitman = json.load(open(os.path.join(ROOT, "out_kit", "manifest.json"), encoding="utf-8"))
        kit_rows = {t["name"]: t for t in kitman["textures"]}
        need_kit = sorted({n for m in mem.values() for n in m["textures"] if n in kit_rows})
        manifest = dict(
            provenance="Original. Masks, layouts and motion from pipeline/lobby.py; nothing "
                       "traced, sampled or recoloured from Melee or any other game.",
            convert="from melee/: python pc/tools/png2gx.py --layout ../menu/out_lobby/"
                    "waiting_room_layout.json --layout ../menu/out_lobby/code_entry_layout.json "
                    "--layout ../menu/out_lobby/lobby_layout.json --outdir ../_build/ui  "
                    "(never pass this manifest.json: its basename clobbers the kit's)",
            layouts={n: "%s_layout.json + %s_motion.json" % (n, n) for n in layouts},
            textures=[dict(r, why=r["why"]) for r in icon_rows],
            reused_from_online=sorted({t["name"] for L in layouts.values() for t in L["textures"]
                                       if t["name"] in on_rows}),
            requires_from_kit=[dict(name=n, format=kit_rows[n]["format"],
                                    bytes_2x=kit_rows[n]["bytes_2x"]) for n in need_kit],
            memory_2x_per_screen={n: round(m["bytes_2x"] / 1024, 1) for n, m in mem.items()},
            checks=report)
        with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=1, ensure_ascii=False)

        # ---- render
        tx = U.Textures()
        for name, s_ in dict(sc, **parts).items():
            img = U.render(page, s_, tx)
            img.save(os.path.join(OUT, "preview", "%s_2x.png" % name))
            downscale_half(img.convert("RGBA")).convert("RGB").save(
                os.path.join(OUT, "preview", "%s_1x.png" % name))
        browser.close()

    print("lobby: %d masks, %d previews (+%d parts sheets)" % (len(icon_rows), len(sc), len(parts)))
    for n, m in mots.items():
        print("  %s_motion: %d events" % (n, len(m["events"])))
    print("memory @2x per composed screen (excl. disc art):")
    for n, m in mem.items():
        print("   %-24s %6.1f KB" % (n, m["bytes_2x"] / 1024))
    print("names at the fit rule:", report["names"])
    print("stage names at body (px):", report["stages"], "worst:", report["stage_worst_28"])
    print("P1/P2 dE under CVD:", report["p1_p2_cvd_dE"], "strike IoU",
          report["strike_shape_overlap_iou"])
    worst = sorted(report["contrast"].items(), key=lambda kv: kv[1])[:8]
    print("lowest contrasts:", worst)
    if errs:
        print("\nCHECKS FAILED (%d):" % len(errs))
        for e in errs[:60]:
            print("  - " + e)
        return 1
    print("\nlobby checks ok: slots fit (incl. fit-rule steps), title-safe incl. peak motion, "
          "contrast in every state, P1/P2 by shape + label + colour, POT masks, memory")
    return 0


if __name__ == "__main__":
    sys.exit(main())
