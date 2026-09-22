# Online Play delivery

This covers the pieces for the in-game **ONLINE PLAY** screen: `fe_screen_online` / `fe_items_online` in `gmfrontend.c`. They are built on the section 1 kit, so everything in `out_kit/SECTION1.md` still applies:
- template coordinates are unsheared;
- colours are kit tokens;
- text is set from `font_manifest.json`, using the fit rule.

## Build order

```
python pipeline/kit.py && python pipeline/font_atlas.py && python pipeline/glyphs.py \
  && python pipeline/icons.py && python pipeline/kit_ui.py && python pipeline/online.py
```

Each script checks its own output and exits non-zero on failure. All of them pass.
- `icons.py` is new. It draws the icon masks for this screen and for section 2.
- `font_atlas.py` gains the `code` role.

To convert for the engine, run from `melee/`:

```
python ../worktrees/menus/pc/tools/png2gx.py --layout ../menu/out_online/online_layout.json \
    --layout ../menu/out_kit/manifest.json --outdir ../_build/ui \
    --copy ../menu/out_kit/kit.json ../menu/out_kit/font/font_manifest.json
```

This has been run, so `_build/ui` now holds these textures and files:
- `ico_online`, `ico_host`, `ico_join`, `ico_paste`, `ico_copy`, `ico_link`, `ico_unlink`, `ico_warning` and `sig_bar_1`–`4`;
- the new `font_code_latin_0`;
- `online_layout.json` and `online_motion.json`.

**Use the `menus` worktree's `png2gx.py`.** The copy in the main `melee/` checkout has neither `--layout` nor I4/IA4, so it cannot convert these masks. Also, don't pass `out_online/manifest.json` to `--copy`: it has the same basename as the kit's manifest and overwrites it.

## Files

| File | What it is | How the engine uses it |
|---|---|---|
| `online_layout.json` | The screen: `chrome`, `panel`, `views`, `rows`, `widgets`, `status_strip`, `connect_dialog`, `strings`, `textures` | Read at runtime like `list_layout.json`. `textures` is the list `png2gx --layout` converts |
| `online_motion.json` | 10 events in the `hub_motion.json` format, plus `sequences` | Played by the existing player. `loop` is the one addition (see open issues) |
| `manifest.json` | Every texture the screen needs: its own, plus `requires_from_kit` (font pages and glyphs), GX formats and reasons, memory per screen, check results | Reference only; the engine never reads it |
| `icons_manifest.json` | The online masks, with use, minimum draw size and legibility counts | Reference only |
| `2x/`, `1x/` | `ico_host`, `ico_join`, `ico_paste`, `ico_copy`, `ico_link`, `ico_unlink`, `ico_warning`, `sig_bar_1`–`4`, all 64×64 I4 at 2x | Loaded by name |
| `../out_nav/2x/ico_online.png` | The globe. 256×256, because it is also the Versus hub tile's icon | Listed in `online_layout.json` `textures`, loaded by name |
| `preview/` | Composed from the JSON alone, at 2x and 1x | Reference only |

### Previews (all checked by eye)

| File | Shows |
|---|---|
| `online_host` | Host view, top of the list. Worst strings: "Mr. Game & Watch Jr." (steps to body), "Princess Peach's Castle", "8 frames" |
| `online_host_code` | Host view scrolled to Your Code, in the **copied** flash (ok plate, check mark) |
| `online_join` | Join view: pasted host code `255.255.255.255:65535`, Connect selected |
| `online_join_empty` | Join view with no host code: the plate's placeholder, and the "clipboard doesn't hold a code" status |
| `online_connecting` | Join, working: the strip shows pips and sweep; the dialog shows **CONNECTING** with the host code and pips |
| `online_waiting` | Host, working: the dialog shows **WAITING FOR YOUR FRIEND** (the longest title) with your code and copy icon |
| `online_connected` | Connected strip with ping (148 ms, so 2 gold bars) |
| `online_failed` | Failed strip with the 60-character worst status |
| `online_failed_dialog` | The dialog's **CONNECTION REFUSED** variant: danger slab, warning icon, the code, B = Back |
| `online_parts` | Every strip state, the four ping levels, and the code plate's states: ng, sel, empty, copied, disabled |

## The pieces

**(a) Icon masks.** All are white masks tinted by material colour, and all are I4.
- `ico_online`: a globe.
- `ico_host`: a beacon on a mast.
- `ico_join`: an arrow into a door.
- `ico_paste`: a clipboard with a down arrow.
- `ico_copy`: two sheets.
- `ico_link`: two chain links.
- `ico_unlink`: a broken link.
- `ico_warning`: a triangle with a knocked-out mark.
- The signal indicator is four separate bar masks, `sig_bar_1`–`4`. Draw all four at one rect. The first *n* take the level's colour and the rest take `@face`:

| Level | Bars | Colour |
|---|---:|---|
| ≤ 60 ms | 4 | ok |
| ≤ 100 ms | 3 | ok |
| ≤ 150 ms | 2 | gold |
| > 150 ms | 1 | danger |

The bar count is the primary cue and colour is secondary.

**(b) Code plate** (`widgets.code_plate`):
- An ink plate, 240×22, right-aligned in the value area. It reaches 50 px into the label side; the "Your Code" and "Host Code" labels still fit.
- It has a 3 px accent in `@face_hi` (gold when the row is selected).
- The code is set in the new **`code`** role: Hasklug Bold 16, fixed cells. `255.255.255.255:65535` measures 201.6 px against 202 px of room.
- The copy icon sits at the right. It appears on Your Code only. Host Code keeps the same plate width, so the two codes line up.
- States: ng, sel, disabled, and **copied**. Copied is an ok plate with ink text, the icon becomes `glyph_check`, and it lasts 40 frames (`code_copied`).
- The empty state shows a placeholder from strings ("Press A to paste").
- The code never takes the fit rule. A string that doesn't fit is not a code.

**(c) Status strip** (`status_strip`):
- It takes the list's ninth row slot, so this screen shows 8 rows and its scroll track ends at y = 346.
- Its x span, 90–596, matches the description strip. It reads as the top of the bottom chrome stack.
- A 36 px state block on the left carries the state; the table below lists them. `failed` swaps the icon for `ico_unlink` when a live connection dropped.
- The text slot is **379 px**: 60 characters at body (14 px). Longer text steps down to caption, then truncates.

| State | Block | In the block | Extras |
|---|---|---|---|
| idle | `@face` | `ico_online` | none |
| working | gold | 3 activity pips | a gold sweep under the strip |
| connected | ok | `ico_link` | ping bars and ms readout |
| failed | danger | `ico_warning` | none |

**(d) Connecting overlay** (`connect_dialog`):
- It is the section 1 dialog (420 px wide, dim, `dialog_open`/`dialog_close`) with no buttons.
- Contents: the title slab, one status line, a caption label ("HOST CODE" or "YOUR CODE"), the code plate, 3 pips, the sweep along the bottom edge, and **B = Cancel** at the bottom right.
- Variants:

| Variant | Slab | Title icon | Pips | B hint |
|---|---|---|---|---|
| connecting | gold | none | yes | Cancel |
| waiting | gold | none | yes | Cancel |
| connected | ok | `ico_link` | no | none |
| failed | danger | `ico_warning` | no | Back |

The panel keeps its size (h = 138) in every variant, so switching variants never jumps.

**(e) Screen.** `views` lists the rows for each Play As value. The host view has 10 rows and scrolls by 2; the join view has 7. `rows_reflow` animates a view change.

The rows map onto the kit's widgets:
- choice: Character, Stage;
- `choice_icon`: Play As, which shows `ico_host` or `ico_join` beside the value;
- `pips`: Costume, one pip per costume up to 8, plus the engine's readout;
- `slider_long`: Stocks, Time Limit, Input Delay. It is the kit slider with a 96 px track, so "8 frames" fits;
- `action`: the Paste, Host Match and Connect rows, each with its icon at the right;
- `code_plate`: Host Code, Your Code.

## Checks (all pass)

- Every text slot fits its maximum string at its role. This includes the fit-rule steps: m-ex names up to 20 characters and 28-character stage names reach body without truncating.
- The code never truncates.
- The row labels fit at row size.
- Title-safe holds including peak motion, using the kit's per-joint extents, for all 9 screens.
- Contrast holds for every text and graphic on this screen. Worst text is 4.52:1 (the dialog code label, muted on `@face`); worst graphic is 4.22:1 (the idle icon).
- State blocks under colour-blindness simulation: the closest pair is working/failed at ΔE 17.4 under deuteranopia. The icon or pips differ in every state regardless.
- Icon legibility: the shape and hole counts survive at 2x of the smallest draw (32 px).
- Memory is under budget; see below.

## Memory at 2x per composed screen (excluding disc art)

| Screen | KB |
|---|---:|
| Host view (top) | 228.0 |
| Host view, code copied | 246.5 |
| Join view | 216.0 |
| Join, connecting (dialog) | 216.0 |
| Host, waiting (dialog) | 216.0 |
| Connected | 226.0 |
| Failed | 186.0 |

Most of this is the four sans font pages (160 KB) and the title page (64 KB). This screen's own masks come to 22 KB, plus 32 KB for the globe. The `code` atlas is 16 KB; it covers `0-9 . : [ ] a-f A-F x - ? …`, and anything else falls back to `?`.

## Open issues

1. **`loop` is new to the motion format.** `activity_loop` (36 frames) and `sweep_loop` (72 frames) restart at `from_frame` when they reach `to_frame`, until `status_set` takes their channels. The player needs this one addition.
2. **The engine's status strings run long.** Today's longest are about 110 characters, with the code embedded, for example "Waiting for friend (code … copied) - no auto port forward - …". The caption step holds about 72, so these truncate. The code already has its own plate, so `online_layout.json` → `strings.suggested` gives short forms, all 60 characters or fewer. The same goes for the peer placeholder "(none - press A to paste)": it should become the plate's placeholder string instead of the code value.
3. **Costume is a slider in `fe_items_online`.** The layout specifies a `pips` widget, which suits a count that varies per character. The slider still works (`slider_long`) if the engine keeps it.
4. **"Your Code" and "Host Code" are sliders with `fe_np_zero`.** They should draw as `code_plate` widgets, with A (or X, per the footer hint) copying and pasting. `code_copied` wants a signal from `Netplay_MenuCode` / the clipboard write.
5. **`ico_online` lives in `out_nav/`** because it is also a section 2 hub icon. It is listed in `online_layout.json` `textures`, so the import finds it either way.
6. **No sounds exist.** `sfx_connected` and `sfx_error` are cue markers only, like the kit's.
