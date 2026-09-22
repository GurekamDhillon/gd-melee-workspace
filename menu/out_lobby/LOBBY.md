# Online rooms delivery: waiting room, code entry, pick/ban lobby

This covers the three screens of the room flow: **Online Play → Host → waiting room**, **Guest → code entry → waiting room (joining)**, and the **lobby** both players share for every game of a set. Everything builds on the section 1 kit and the online pieces, so these still apply:
- template coordinates are unsheared (`x' = x + (240 - y) * 0.25`, applied last);
- colours are kit tokens;
- all text is set from `font_manifest.json` using the fit rule. No words are baked into textures.

## Build order

```
python pipeline/kit.py && python pipeline/font_atlas.py && python pipeline/glyphs.py \
  && python pipeline/icons.py && python pipeline/kit_ui.py && python pipeline/online.py \
  && python pipeline/lobby.py
```

`lobby.py` is new. It draws its own masks (it imports `icons.py`'s helpers but writes only to `out_lobby/`), writes the layouts and motion, composes the previews from those layouts, runs the checks, and exits non-zero if any check fails. All checks pass.

To convert for the engine, run from `melee/` (the main checkout's `png2gx.py` has `--layout` and I4):

```
python pc/tools/png2gx.py --layout ../menu/out_lobby/waiting_room_layout.json \
    --layout ../menu/out_lobby/code_entry_layout.json \
    --layout ../menu/out_lobby/lobby_layout.json --outdir ../_build/ui
```

This has been run. `--layout` converts each layout's `textures` and copies the layout together with its sibling `*_motion.json`, all under their own names. **Never pass `out_lobby/manifest.json`**: its basename would overwrite the kit's `manifest.json` in `_build/ui`. The kit's copy was checked before and after the run and is unchanged.

## Files

| File | What it is | How the engine uses it |
|---|---|---|
| `waiting_room_layout.json` | Host view and guest "joining" view: `chrome`, `room_plate` (panel, hero code plate, copy row, share lines), `status_strip` (online's, by reference) | Read at runtime. `textures` is what png2gx converts |
| `waiting_room_motion.json` | 5 events: `room_plate_in`, `room_code_copied`, `join_sweep` (loop), `opponent_found`, `room_leave`, plus `sequences` | Played by the motion player |
| `code_entry_layout.json` | `chrome`, `panel`, `field` (plate, 4 cells, `slot_template`, `arrows`), `hints_row`, `status_strip` | Read at runtime |
| `code_entry_motion.json` | 7 events: `code_slot_move`, `code_letter_step`, `code_type`, `code_paste`, `code_invalid`, `code_caret_blink` (loop), `code_join` | Played by the motion player |
| `lobby_layout.json` | `chrome`, `score_plaque`, `phase_banner`, `action_plate`, `cards` (P1, P2), `turn_arrow`, `stage_grid` (6 tiles + `tile_states`), `coin_badge`, `countdown`, `lobby_status`, `phases` (the rules), `slots_engine_fills` | Read at runtime |
| `lobby_motion.json` | 20 events (listed below), plus `sequences` | Played by the motion player |
| `icons_manifest.json` | The 9 new masks, with use, minimum draw size and legibility counts | Reference only |
| `manifest.json` | Textures per screen, the online and kit textures reused, memory per screen, every check result | Reference only. **Do not convert it** |
| `2x/`, `1x/` | `ico_strike_x`, `ico_strike_o`, `ico_lock`, `ico_coin` (128 at 2x); `ico_pick`, `ico_crown`, `ico_wait`, `ico_turn`, `ico_keyboard` (64 at 2x). All are I4 | Loaded by name |
| `preview/` | Composed from the layout JSON, at 2x and 1x | Reference only |

The screens also use textures that already exist:
- from online: `ico_copy`, `ico_link`, `ico_warning` and `sig_bar_1`–`4`;
- from out_nav: `ico_online` (the status strip's idle icon) and `ico_versus` (the breadcrumb);
- from the kit: `glyph_a`, `glyph_b`, `glyph_x`, `glyph_y`, `glyph_start`, `glyph_dpad`, `glyph_check`, and the font pages `caption`, `body`, `row`, `label`, `title`, `heading` and `display`.

All of these are already in `_build/ui`.

## One addition to the layout format

These layouts carry state tables, so the previews can be drawn from the JSON alone. An element is `{origin, quads, slots, states: {axis: {state: {key: token}}}, lift_joint(s)}`, and two lookups are added:
- A colour, texture, uv or opacity written `"<axis.key>"` is looked up as `states[axis][current state of axis][key]`. If the result is `null`, the quad is not drawn. `port:<p>` inside a value takes the acting player's port.
- `"when": {axis: [states]}` on a quad or slot means it draws only in those states.
- A state with `offset` lifts every joint in `lift_joints` by that amount (the kit's (−3, −3)). A `plate` quad at rest peeks out behind it.

`lookup()`, `visible()` and `draw_el()` in `pipeline/lobby.py` are the reference implementation, about 60 lines. A few quads are positioned by a rule, and those carry a string instead of a number, with the rule next to it:
- the card badge width;
- the action icon group;
- the paste glyph.

## Screens, and the slots the engine fills

### Waiting room (`waiting_room_layout.json`)

- **Hero code plate.** This is the online code plate's look (ink plate, 4 px accent, bone text) at hero size.
  - It has 4 cells of 72×92. Slots `char_0`–`char_3` each hold one character in the `display` role (56), centred in its cell. The alphabet is `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`, and its widest glyph (W, 46.1 px) fits the cell's 64 px.
  - The code entry field uses the same cell rects, so a code sits in the same place on both players' screens.
- **Plate states:** `ng`, `copied` (ok accent, 40 frames), `joining` (gold accent, gold_lt characters) and `failed`.
- **Copy row** (host only): `copy_icon` and `copy_text`.
  - `copied`: `glyph_check` in ok, with "Copied to clipboard".
  - `idle`: `ico_copy` in muted, with "Press X to copy it again".
  - The text comes from each state's `text_string`.
- **`share_line`:**
  - host: "Send it to your opponent. They pick Join and type it in.";
  - guest: "Joining room KQ7X...".
- **`sub_line`** is optional.
- **Status strip:** online's `status_strip`, unchanged, at (90, 358, 596, 388).
  - waiting and connecting use `working`;
  - opponent found uses `connected`, which shows ping;
  - a failed join uses `failed`.
- **Footer:**
  - host: B Leave, X Copy Code;
  - guest: B Cancel.

### Code entry (`code_entry_layout.json`)

- **Field.** An ink plate with a 4 px accent. The accent state is `ng`, `editing`, `invalid` or `joining`.
- **Slots.** Four slots, each drawn from `slot_template`. Each slot has one of five states:

| State | Face | Content |
|---|---|---|
| `empty` | @bg | muted dash |
| `filled` | @bg | bone character |
| `active_empty` | gold, lifted, with a gold_dk plate | ink caret |
| `active_filled` | gold, lifted, with a gold_dk plate | ink character and caret |
| `invalid` | @bg | bone character, plus a danger bar under it |

- The slot's character slot is `char`, in the display role.
- **Arrows.** `arrow_up` and `arrow_down` use the atlas glyphs ↑ ↓ in the heading role, in gold. They centre on the active cell and ride with it (`code_slot_move`).
- **Hints row:**
  - `ico_keyboard` with "Or type it on a keyboard";
  - `glyph_y` with "Paste";
  - the alphabet note.
- **Rules** (in the file):
  - Left and right move between slots. At the ends they bump.
  - Up and down cycle through the alphabet, wrapping.
  - Typing fills the active slot and moves right.
  - Backspace clears and moves left.
  - Y or Ctrl+V pastes the clipboard's first 4 alphabet characters. Case is folded, and spaces and dashes are dropped.
  - A joins when all 4 slots are filled. With gaps, A jumps to the first empty slot.
  - Invalid or not found: every filled slot turns `invalid`, the accent turns danger, `code_invalid` shakes the field, and the strip goes to `failed`. The first edit clears all of it.

### Lobby (`lobby_layout.json`)

| Region | Rect (unsheared) | Slots / states |
|---|---|---|
| Header title = **GAME counter** | chrome | title slot: "GAME n" (`game_advance`) |
| **Score plaque** | 446,24–550,52 | `set_label` "SET", `set_score` "a - b" (P1 left, like the cards) |
| **Phase banner** | 88,80–392,126 | `phase_title` (title), `instruction` (body); accent by `phase`: character / stage / ready |
| **Action plate** | 400,80–556,126 | `action_text`, `action_icon`; states: `your_turn`, `their_turn`, `ready_off`, `ready_on`, `ready_wait`, `ready_both` |
| **Cards** P1 / P2 | 88,134 / 336,134, 220×72 | see below |
| **Turn arrow** | the 28 px gap | `ico_turn`; `turn`: p1 (U flipped) / p2 / none |
| **Stage grid** | 88,214–556,394, 3×2, tiles 148×86 | per tile: `name`, `art` (optional 64×56), `tab_text`; `tile_states` |
| **Coin badge** | 186,262–454,346 (+ dim) | `coin_label`, `coin_caption`, `coin_text`; `coin`: p1 / p2 / spinning |
| **Countdown** | slab 272,246–368,334 (+ dim) | `numeral` (display: 3, 2, 1), `stage_line` |
| **Lobby status** | the description strip's rect | `status_text`, `ping_ms`, ping bars as online |
| Footer | chrome | `hints_by_phase` |

**The action plate has two jobs in one rect.** During strike, ban and pick phases it is the turn indicator: YOUR TURN on gold, lifted; OPPONENT'S TURN on @face. In the ready phase it is the READY button:
- `ready_off`: START glyph and READY;
- `ready_on`: ok, a check and READY, lifted, for 30 frames;
- `ready_wait`: ok, pips and WAITING;
- `ready_both`: gold, a check and GO!.

It always says what this player needs to do now. Turn is never shown by colour alone: the words, the gold outline and lift on the active card, and the arrow all carry it.

**Cards** (`card_p1`, `card_p2`). P2 is P1 mirrored: the portrait and port stripe sit at the outer edge, and the text is right-aligned toward the centre. Both are written out in full, so the engine does no mirroring. Each card has five state axes:

| Axis | States |
|---|---|
| `turn` | `active` (gold outline, gold_dk plate, lifted) or `idle` |
| `portrait` | `empty` (frame over @bg), `hidden` (ink with a "?" in `@face_hi`, heading role), `shown` (`portrait_art` is the engine's captured 64×56 icon) |
| `badge` | `waiting` (hourglass), `picking` (3 pips), `locked` (padlock on bone), `ready` (check on ok), `none` |
| `crown` | yes / no (`ico_crown`, the previous game's winner) |
| `you` | yes / no ("YOU" caption, this machine's card only) |

The card's slots:
- `port_label` "P1"/"P2", in ink on the port tab;
- `you_tag`;
- `hidden_mark`;
- `name`, up to 20 characters: body, then caption by the fit rule;
- `badge_text`.

**Stage tiles** (`tile_0`–`tile_5`, row-major: Battlefield, Dream Land, Final Destination, Fountain of Dreams, Pokemon Stadium, Yoshi's Story):

| State | Look |
|---|---|
| available | @face, bone name |
| hovered | gold, lifted, gold_dk plate (this machine's cursor) |
| hover_remote | port-coloured outline and port tab (the opponent's cursor on their turn) |
| struck_p1 | ink face, dimmed art, **cross** mask in P1 red, tab "P1" |
| struck_p2 | ink face, dimmed art, **barred ring** mask in P2 blue, tab "P2" |
| banned | ink face, dimmed art, **padlock** in the banning player's colour, tab names them |
| picked | gold, lifted, gold_dk plate and outline, ink tab with a gold_lt check |
| unavailable | ink face, art at 0.2, disabled name (READY phase, the rest) |

**Why 3×2 and not 6×1:**
- In a 148 px tile, every name fits on one line at body. A 6×1 row gives 68 px tiles, and every name would need two lines at caption.
- Each tile keeps a full 64×56 image slot above its name.
- The d-pad moves in 2D, at most 3 steps.
- The 1-2-2 strike order reads across two short rows.
- The grid fits between the cards and the status strip, with the lift.

**Phases** (the `phases` block has the full rules):

*Game 1*
1. **Character** (blind). Each player picks on Melee's own character select screen. The lobby card shows PICKING, then LOCKED IN. The opponent's portrait stays `hidden` until both have locked in; then `card_reveal` runs on both. The grid shows the legal list with no cursor.
2. **Stage.** `coin_badge_in` and `coin_flip`, then the badge leaves and the turn goes to the coin winner (`turn_handoff`). Strikes go 1-2-2 (`strike_stamp`). The last tile becomes `picked` (`pick_confirm`).
3. **Ready.**

*Game 2 onward*
1. **Stage.** The previous winner bans 2 (`ban_lock`, padlock in their colour); the loser picks one of the remaining 4.
2. **Character.** Not blind: the winner is PICKING and the loser WAITING, then they swap.
3. **Ready.**

**After a match:** the room returns to the lobby. `game_advance` runs, the crown moves, and `score_update` runs.

### Lobby motion (`lobby_motion.json`)

| Event | What it does |
|---|---|
| `card_reveal` | Portrait SCA_X 1→0 in 7 frames; the state switches to shown while edge-on; 0→1.12→1. The card bobs and the face flashes gold_lt. P2 starts 4 frames after P1 |
| `badge_set` | The badge pops 0.6→1.15→1 |
| `badge_pips` | Loop. The PICKING and ready_wait pips |
| `turn_handoff` | The arrow's SCA_X runs through 0 onto the new UV. The new card lifts, the old one drops, the outlines swap colour, and the action text slides |
| `tile_hover` / `tile_unhover` | The kit lift, like `row_select` |
| `tile_hover_remote` | The outline fades to the port colour and the tab rises |
| `strike_stamp` | The mark stamps 1.7→0.92→1. The tile thumps 2 px, the face goes to ink at frame 3, and the tab pops |
| `ban_lock` | The padlock drops 14 px and squashes shut. The face goes to ink and the tab pops |
| `pick_confirm` | The tile swells 1.07, flashes gold_lt→gold, lifts, and the check tab pops. The rest go `unavailable` |
| `ready_toggle` | The plate pops 1.07, the face flashes, and the plate lifts |
| `coin_flip` | 59 frames: SCA_X swings 1→0→−1…, slowing, with 6 zero crossings. **Start the coin on the winner's face and it lands there.** It hops 28 px, bounces, and then `coin_text` fades in |
| `coin_badge_in` / `coin_badge_out` | The badge enters and leaves |
| `countdown_in` / `countdown_tick` ×3 / `countdown_out` | Each numeral pops 1.5→0.94→1 and fades out by frame 59; 60 frames per tick |
| `phase_change` | The banner text slides and the accent grows |
| `score_update` | The score pops |
| `game_advance` | The header title swaps and the crown pops |

## Checks (all pass)

- **Every text slot fits its maximum** at its role, using the kit's walker. The display and heading roles contain no lower case. Footer hints fit.
- **Fit-rule strings:**
  - All six 20-character kit test names fit the card name slot (122 px) without truncating. "Captain Falcon Alt 2" sets at body; "Wario Man, Microgame" (119.8 px) and the other four step to caption.
  - All 6 stage names fit at body with no step; the widest is Fountain of Dreams, 120.2 of 136 px.
  - The 28-character worst case, "Princess Peach's Castle", fits at caption.
  - Every action string, badge and phase title fits with no step.
  - Every room-alphabet character fits a code cell.
- **Title-safe including peak motion,** for all 16 composed screens. The check uses every joint's extreme translation plus its peak scale about the joint group's centre, taken from this section's motion plus the kit's and online's. The lifted items (cards, tiles, action plate, code slots) add their overshoot.
- **Regions don't collide:**
  - the lifted card outline clears the banner;
  - the grid clears the cards;
  - the grid ends above the status strip;
  - the code field stays inside the panel.
- **Contrast in every state, generated from the state tables** (94 pairs). All text is ≥ 4.5:1, including the port-coloured strike and ban marks on tiles, which I held to 4.5, not 3. The lowest text pairs:
  - P2 blue on ink, 4.83 (P2 mark, P2 tab text, coin label);
  - P1 red on ink, 4.89.
- **Graphics are ≥ 3:1,** with two exceptions, both reported rather than required:
  - The copied-state check icon on @face is 4.08 and the invalid bar 3.62.
  - `hover_remote`'s port outline against the tile's own face is 2.6 (it is 4.8 against the ink gutter). The port tab, which is text at 4.83:1, carries that state.
- **P1 vs P2 are never colour only.** P1 strikes are a cross and P2 strikes a barred ring, and every mark has a P1/P2 tab. The two masks overlap at IoU 0.37, so they really are different shapes. The ban is a third shape, the padlock. Colour distance P1/P2 (ΔE2000):

| Vision | ΔE |
|---|---:|
| Normal | 45.9 |
| Deuteranopia | 58.1 |
| Protanopia | 50.3 |
| Tritanopia | 71.6 |

- **Masks:** power-of-two and ≤ 1024. The shape and hole counts survive at 2× of each mask's smallest draw.
- **Memory:** under 1 MB on every screen (below).

## Previews (all looked at)

All previews use worst-case names, "Wario Man, Microgame" on both cards.

| File | Shows |
|---|---|
| `waiting_host` | Host, code copied, waiting |
| `waiting_host_found` | Opponent found, ping 42 ms, copy row idle |
| `waiting_guest` | Joining KQ7X: gold plate and sweep |
| `code_empty` | Empty field, caret on slot 1 |
| `code_partial` | "KQ" filled, caret on slot 3 |
| `code_invalid` | "KQ7W" not found: danger accent and bars, failed strip |
| `lobby_g1_blind` | Game 1: P1 (you) PICKING with an empty frame; P2 LOCKED IN, hidden "?" |
| `lobby_g1_reveal` | Both locked, both portraits shown |
| `lobby_g1_coin` | Coin badge: "P2 STRIKES FIRST" |
| `lobby_g1_strike` | Mid-strike: P2 struck 2, P1 struck 1, P1's cursor on Final Destination, YOUR TURN, arrow at P1 |
| `lobby_g1_strike_remote` | The opponent's turn: P2's remote hover outline and tab |
| `lobby_g1_final` | Fountain of Dreams picked; the rest struck (P1 cross ×2, P2 ring ×3) |
| `lobby_g2_ban` | Game 2: P2 (crown) banned 2, P1 hovering to counterpick, score 0 - 1 |
| `lobby_g2_char` | Game 2 characters: P2 PICKING (active), P1 WAITING |
| `lobby_ready` | Game 3, 1 - 1: P1 READY (the plate reads WAITING), P2 WAITING |
| `lobby_countdown` | Both ready, "2" over the dimmed lobby |
| `parts_tiles`, `parts_cards`, `parts_action`, `parts_code`, `icons_sheet_2x` | Every state of each piece |

## Memory at 2x per composed screen (excluding disc art)

| Screen | KB |
|---|---:|
| Waiting room: host / found / guest | 417.5 / 429.0 / 416.5 |
| Code entry: empty / partial / invalid | 324.0 / 580.0 / 550.0 |
| Lobby, Game 1: blind / reveal / coin | 305.0 / 177.0 / 241.5 |
| Lobby, Game 1: strike / remote / final | 219.5 / 211.5 / 187.5 |
| Lobby, Game 2: ban / characters | 213.5 / 217.0 |
| Lobby: ready / countdown | 215.5 / 469.5 |

Most of this is font pages:
- `display` is 256 KB, used by the room code and the countdown;
- `heading` is 128 KB, used by the code arrows and the hidden "?";
- the small sans pages come to 160 KB.

This section's own masks total 42 KB. Loading every lobby state at once would be about 600 KB, still under budget.

## Open issues

1. **The `<axis.key>` / `when` lookup is new to the layout format.** The player needs about 60 lines for it; `draw_el()` in `lobby.py` is the reference. Without it, the state tables still read as plain data.
2. **The room code uses `display` (Source Sans Black caps), not a monospaced face.** The cells fix the positions, and the alphabet already drops I, O, 0 and 1, so no new atlas is needed. If a Hasklug look is wanted to match the code plate, a `room` role in `font_atlas.py` would cost about 32 KB. The `code` atlas can't be used: it has no G–Z.
3. **`loop` motion,** as in online: `badge_pips`, `join_sweep` and `code_caret_blink`.
4. **New sound cues are markers only:** `sfx_strike`, `sfx_lock`, `sfx_coin`, `sfx_land`, `sfx_turn`, `sfx_reveal`, `sfx_tick`, `sfx_menu_confirm`.
5. **`hover_remote` needs the opponent's cursor over the network.** If netplay doesn't send it, drop the state; the turn plate and arrow still say whose move it is.
6. **The coin result must be decided before the flip,** by the host or server, and shown on both machines from the same seed. The animation only lands on the face it started on.
7. **The stage name "Pokémon Stadium" needs é,** which the atlas lacks (it covers ASCII plus a few extras). The strings use "Pokemon" for now. A Latin-1 supplement to the atlas would fix it; that belongs to the second-script pass.
8. **The action plate is hidden in phases where both players act** (the blind pick, and the moment after the final pick). The banner-right area is empty then. An alternative is to show `their_turn`-style text such as "BOTH PICK" there. The string is not in the layout yet.
9. **Two players only.** The layouts have no P3 or P4 cards.
10. **The lobby's status line takes the chrome description strip.** The kit toast (for example "Code copied") still covers it as designed.
11. **Countdown numerals are the display size (56 px) at rest,** as the brief asked. The 1.5× pop briefly upsamples the display page. If a bigger resting numeral is wanted, it needs a larger atlas role (only 1, 2 and 3 are needed, so it would be a tiny page).
