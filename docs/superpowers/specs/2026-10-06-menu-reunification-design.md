# Menu re-unification (design)

Date: 2026-10-06. Status: for the owner's review; nothing here is built. This is a design, written from the
code and the mockups; no game, launcher, build or browser was run.
Supersedes: nothing. It builds on `_research/menu-legacy-kit-inventory-2026-10-06.md` (the map of what exists; read
it first) and picks the Atlas direction of `menu/concepts/reunification-2026-10-06/`.
Labels: **[code]** read in source (`file:line`), **[doc]** stated in a doc, **[image]** seen in a mockup PNG,
**[estimate]** my arithmetic, **[proposal]** a choice this spec makes, **[unverified]** not checked (collected in section 18).
Paths are relative to the workspace; game files are under `melee/`. `GM` = `melee/src/melee/gm/`,
`PL` = `melee/pc/platform/`, `ATLAS` = `menu/concepts/reunification-2026-10-06/c-atlas/`.

## 1. Summary

1. **What.** Every menu the player sees (the game's, the mods', the launcher's) is redrawn and rebuilt on one system
   in the Atlas style. The old system is the **legacy menu kit** and is deleted piece by piece as screens move.
2. **How it is built.** One set of parts (plate, list row, tab strip, toggle, choice, slider, grid cell, model cell,
   explainer, dialog, corner note, key hints, trail) lives in the host (native C, `PL/gw_ui_*`), above the quad
   list that `gd.kit` already uses. Native screens and Lua scripts both call it.
3. **A screen is a description.** It fills four fixed places (trail, primary, explainer, keys). The engine does the
   layout (4:3 and wide), focus, pad, mouse and keyboard input, key hints and motion. A mod supplies content, models, text.
4. **Mods add menus.** A mod's `mod.json` declares an entry under a parent (`solo`, `versus`, `settings`...) and
   its Lua registers the screens behind it. Envoy is first. Mod screens only read input and draw.
5. **Coexistence.** The old router (`gmFrontend_Route`) stays. A screen is moved by changing which handler owns its
   `(MenuKind, selection)` or `(from, to)` slot; the other screens do not notice. Each step ships alone.
6. **Ten steps**: the owner's nine, in his order, plus a tenth that re-hosts the bespoke retail screens (trophies,
   snapshots, movies, tournament...) inside Atlas chrome (section 13.10). Each has its own retirement list
   (section 13). Step 1 is the parts plus the Envoy bag.
   **Retail takeover capability** (section 6.8): the hooks, the per-element mask that hides one retail drawing
   at a time, and the descriptions of a HUD zone and a pause screen are built (steps 2 and 3). Nothing retail is
   hidden by default; replacing the retail numerals and pause is the owner's later call.
7. **Things the code makes harder than the outline sounds** (section 13.11): the two kits are two codebases;
   the main-menu "Envoy tile" is wired to the older `roguelite/main` script, not to Envoy; "one character select
   for every mode" touches about 19 other mode files (23 `GS_CSS` states); title and results have no frontend hook today (pause and the HUD have usable
   hook sites); the mockup's type sizes and weights are not the engine atlas' sizes and weights; the bespoke retail
   screens are 3D scenes the retail renderer draws, so Atlas can frame them but not re-draw their models.
8. **Cost** (section 11): about 130 to 600 quads per screen before models and decoration [estimate from the
   mockup HTML], against a 16,384-quad list; about 6 to 7 MB of added font pages [estimate].

## 2. The owner's decisions (verbatim)

- "let's actually do a re-unification of all of our menus. the current menu stuff we'll call the legacy menu kit. redo
  the entire menu-ing for everything now that we have improvements across the game. brand new style and design
  paradigm too." and "refactor as needed".
- Scope: the launcher is in. Retail's own menus are replaced too "unless it has a lot of custom shit like the trophy
  dispenser". The in-match HUD and pause "can be" part of it. Mods should be able to add menus. The layout "should
  work in either case" (4:3 and wide). Envoy's menus: "Maybe the builders get generic'd and put in engine, but the
  assets are provided by the mod".
- Style: "Atlas is my preferred style". Workbench (`a-workbench`) and Signal (`b-signal`) were not chosen and
  nothing from them is mixed in.
- Main menu: Solo, Versus, Online, Mods, Settings, and a small "More" row (Collection, Data, Credits). "Envoy sound
  be main menu > solo > envoy" (read: should be).
- Approved ("Kk") outline, which this spec makes precise:
  1. One component set in the engine, drawn in the Atlas style (plate, list row, tab strip, toggle, choice, slider,
     grid cell, model cell, explainer pane, dialog, corner note, key hints, trail); native screens and scripts call
     the same parts.
  2. A screen is a description, not drawing code: it declares what goes in the four fixed places (trail, primary,
     explainer, keys); the engine does layout, focus movement, pad and mouse input, and the wide and 4:3
     arrangements. A mod supplies content, models and text.
  3. Mods can register a menu entry under a parent (e.g. under Solo) and supply the screens behind it; Envoy is the
     first, replacing its hard-wired tile. Mod screens only read input and draw, so they stay safe online.
  4. The changeover is screen by screen (old and new coexist through the router), in this order: (1) the component
     set + the Envoy bag as the proving screen; (2) title, main menu, Solo and the hubs; (3) Envoy's remaining
     screens and the in-match HUD; (4) character select, stage select, Versus rules, with ONE character select for
     every mode; (5) settings and the remap editor; (6) online room; (7) mods list and the LAB; (8) the retail
     screens being replaced (results, records, name entry and the rest; bespoke ones like the trophy lottery stay);
     (9) the launcher, its own piece of work in the same style. Each step ships on its own.
  5. Legacy kit art and screens are removed as each is replaced.
  6. Layout and focus rules are tested without the game; each converted screen then needs a look in the game (only
     when the owner is away, or by him).
- Assumptions he did not object to: the third font (Barlow Condensed, OFL) is added to the game's atlas; step 1's
  proving screen is the Envoy bag.
- **Answers to the first draft's open questions (2026-10-06).**
  1. The name: Atlas for the whole system: "yes".
  2. The retail percent/stock/timer HUD and the retail pause: "get prepped for it/build capability to". So the hooks
     and the capability to replace them are built; the replacement itself is a later decision he makes with it in
     front of him (6.8, steps 2, 3, 8).
  3. Envoy's parked screens (title, profile, garden hub, fighter, companion, records): "idk do what's optimal".
     **A delegated decision, not his words:** the coordinator's call is not to port them, to remove their screen
     wiring in step 3, and to keep their logic.
  4. The title in step 2 if the hook is cheap, else step 8: "lgtm".
  5. The retail Language row stays a native hand-off until the retail text screens are gone, then is removed: "ok".
  6. The bespoke retail screens are not simply left retail: "maybe we disassemble and reassemble these menus against
     our new menus so they stay in theme. Combining the original melee assets into it where we can to preserve the
     original look". This is a direction with room to drop a screen that proves too costly ("maybe", "where we
     can"); it supersedes "bespoke ones like the trophy lottery stay" in item 4 above and becomes step 10 (13.10).
- Standing rules that bind this design: no disc-derived art in either repo; mods run on the vanilla disc, one folder
  each; always give credit (name and link) in the same change; menus that exist online stay deterministic-safe;
  Envoy readability (one short rule per piece, each thing a distinct identity, the synergy notice a small
  top-corner note); the drive models are loved; performance target 120 fps; docs in English only.

## 3. Terms

Added to `docs/TERMINOLOGY.md` by step 1 (the file's rule: check it before inventing a word).

| Term | Meaning |
|---|---|
| **legacy menu kit** | Everything the port draws or wraps for menus today (the inventory's five systems): `GM/gmfrontend*` (native), the legacy parts of `gd.kit` (`panel`, `button`, `list`, the section palettes), the `menu/out_*` art sets, the Envoy and LAB screen code, the launcher's own kit copy, and the retail screens until each is replaced. |
| **Atlas** | (Name confirmed by the owner, section 2.) The name of the new system and its style: the parts, the screen description, the registry, the router glue. The owner already calls the style Atlas. Collision: the engine has "font atlas" and "texture atlas"; those always keep their qualifier, and bare "Atlas" means this system. Code names: `gw_ui_*` (host), `gd.ui` (Lua), `at_` (C identifiers). |
| **retail element** | One thing the retail game draws that Atlas may hide on its own (a HUD damage plate, the pause panel, a trophy menu's 2D frame). Each has a stable id (`hud.damage`...) and a guard. |
| **retail element mask** | The set of retail elements currently hidden. Empty by default. |
| **frame (re-host pattern)** | Running a retail scene unchanged and drawing Atlas chrome (trail, explainer, keys) around it, with chosen retail 2D pieces hidden (13.10). |
| **part** | One drawable control of the component set (a plate, a row, a cell...). |
| **screen** | One description registered with an id (`envoy.bag`). Not a game scene. |
| **place** | One of the four fixed regions of a screen: **trail** (where: top), **primary** (what you act on: left), **explainer** (the one thing in focus: right), **keys** (hints: bottom). |
| **chapter** | One of the five top-level entries (I Solo, II Versus, III Online, IV Mods, V Settings). A screen belongs to the chapter of its root entry. |
| **entry** | A menu item that opens a screen or runs an action, registered under a **parent** (an entry id or a built-in node such as `solo`). |
| **intent** | A device-independent input event (move, accept, back, alt-X/Y/Z, page L/R, start) produced by pad, mouse or keyboard. |
| **host** | The native, non-retargeted side of the exe (`PL/`). **Game side** is the retargeted decomp C (`GM/`). |

## 4. The style (normative)

The look is Atlas as drawn in `ATLAS/`. Where this section and a mockup differ, this section wins; the differences are
named. Files to read: `ATLAS/README.md`, `tokens.css`, `kit.css`, `parts.py`; sheets `out/kit-1-palette-type.png`,
`kit-2-controls.png`, `kit-3-cells-rules-models.png`, `kit-4-feedback-input-ports.png`, `kit-5-structure-motion.png`;
screens `out/02-main-menu.png`, `04-characters.png`, `09-envoy-bag.png`, `10-envoy-reward.png`, `11-envoy-hud.png`,
`14c-remap.png`, wide variants `out/wide-*.png`. Units are logical px of the 640x480 canvas.

### 4.1 Depth and shape

Flat quads only: no shadows, gradients or curves [doc: ATLAS/README.md]. Five levels, one rule: a higher level is
lighter and shows a thicker front edge. E0 ground (no edge), E1 plate (3 px edge), E2 row or cell (3 px edge), E3
lift (focus: up 2 px, ember edge), modal (6 px edge over a 72 % scrim). Chamfers are on two opposite corners only
(top-left and bottom-right): 8 px on panes and modals, 5 px on rows, buttons, notes and tags, 3 px on cells.
Pressed drops 1 px and darkens the edge to `ember-d`. Disabled is hatched, not just dimmed.

### 4.2 Palette (values from `ATLAS/tokens.css`; ratios from `kit-1`)

| Token | Hex | Use |
|---|---|---|
| ground / ground2 | #0d1015 / #131820 | E0 backdrop; quiet panes and wells |
| plate / plate2 / lift | #1a1f29 / #222836 / #2e3648 | E1 pane; E2 rows and cells; E3 focus |
| edge / edge2 / line / line2 | #06080b / #0b0e13 / #323a4b / #4a5570 | front edges; rules |
| ivory / text2 / muted / dim | #f1ebdc / #c8c4b8 / #9aa2b4 / #6e768a | primary text; secondary; labels and hints; disabled only |
| **ember** / ember-d | #ff7a3d / #a8431c | focus and the one action |
| **jade** / jade-d | #4fd6aa / #1f6e57 | information, origin, "on", selected |
| sun / rose | #f2c14e / #ef4f7d | caution / danger |
| p1 p2 p3 p4 cpu | #f0504a #4a90ff #f3cf3e #42d68b #8f98aa | ports |
| pad-a / b / x / z | #3dbb78 / #e5534b / #9aa3b5 / #8e6bdc | key-hint glyphs |

Rules: colour is never the only signal; disabled text (dim) is the only text under 4.5:1 [image: kit-1]; ember
means focus or the one action and nothing else; jade means information; the five section tints of the legacy kit
(Versus blue, Solo brown, ...) do not exist in Atlas, chapters are told apart by numeral and name.
These tokens are the source of truth for every consumer (game, Lua, launcher): section 6.9.

### 4.3 Type

Floor is 12 px at 640x480. The mockup's `kit.css` uses in-between sizes (13, 15, 17, 18, 22, 27) that the engine
atlas cannot have, and its Source Sans weight is Semibold where the shipped atlas is Bold and Black
(`menu/out_kit/font/font_manifest.json` roles `caption`..`display`: 12, 14, 16, 20, 24, 32, 44, 56; the mockup
tokens: 12, 14, 16, 20, 28, 44, 64) [code, image]. So Atlas defines **its own role set** (a second manifest
page set, additive; the legacy roles stay until step 9) and every mockup size snaps to it [proposal]:

| Role | Face and weight | Size | Charset | Use |
|---|---|---|---|---|
| `cap12` `cap14` `cap16` `cap20` | Barlow Condensed SemiBold, tracked +0.10 em | 12 14 16 20 | full | tags, toggle words, plate headings, tabs, trail, buttons, rail |
| `title` | Barlow Condensed Bold | 28 | full | explainer title, screen titles, dialog title |
| `hero` / `display` | Barlow Condensed Bold | 44 / 64 | caps only | title screen, results, big numerals |
| `body12` `body14` `row16` | Source Sans 3 Semibold | 12 14 16 | full | captions; rule text, hints; list rows, choices |
| `num12` `num14` `num16` | Hasklug Medium (tabular) | 12 14 16 | full | counters ("5 / 6"), values, codes |

Snap rule: nearest defined size, ties down, never below 12 (13 becomes 12 for caps and 14 for sentence text; 15 becomes
16; 17 and 18 become 16 or 20 by the part's table in `at_parts`; 22 becomes 20; 27 becomes 28). The fit rule of
`gw_Kit_Fit` stays: too wide steps down one role of the same face, then truncates with an ellipsis; never
squash [doc: scripting.md:343-350].

### 4.4 Space and plate heights (from `kit.css`)

Spacing steps 4, 8, 12, 16, 24. Screen margins 32 left and right (the title-safe box is 32, 24 to 608, 456 [doc:
`docs/ART-BRIEF-menus.md`]). Header: top 22, 30 high, rule at 56. Body: top 66, bottom edge 428 (52 from the
bottom), 12 between primary and explainer. Footer: top 434, 26 high. Part heights: list row 34 (tall 46, xl 54) with
a 5 px gap; button 34 (big 44); tab 26 (active 30); tag 20; corner note 30; toggle 22; port card 56; dialog 332 wide;
cell edge 24 to 56 as the grid allows; model cell margin 0.08 [doc: scripting.md:361]. Explainer width is one of
three presets, measured from the PNGs [image, approximate]: **narrow 160** (bag), **normal 196** (character select),
**wide 256** (main menu, remap). The screen names the preset; the primary place takes the rest.

### 4.5 The four places and the structure rules

Trail and chapter dots top, primary left, explainer right, keys at the bottom, on every screen
[image: kit-5]. One primary and one supporting pane; everything else is quiet (ground tone, muted text).
A cell shows only a model or a name. The explainer is always **WHAT** (one rule line), **WITH** (what it works with),
**FROM** (where it came from, as a tag), and `Y` for more. A piece never shows more than one short rule at a time
(the Envoy readability ruling). Wide screens add a chapter rail and widen primary and explainer; nothing new appears.

### 4.6 The focus rule

Three cues at once, always: the plate lifts 2 px, its front edge turns ember, and a tick (rows: 4 px at the left)
or four registration brackets (cells; tinted with the focusing port's colour on a shared screen) appear. Selected
adds a jade bar (rows) or jade ring (cells) and never moves. Toggles say ON or OFF and move their lit half.
Pad focus is the truth; mouse hover is focus [image: kit-2].

### 4.7 Port identity

Four players: numeral plus shape plus colour (1 circle red, 2 square blue, 3 hexagon yellow, 4 diamond green); CPU is
hatched grey with the word CPU. A port card has a 3 px top edge in the port colour [image: kit-4, 04].

### 4.8 What a cell may show

Cell: a model (drive, fighter art) **or** a name plate, plus at most: a slot index (top-left, `num12`), an origin
mark (top-right: jade `G`eno / sun `+` added), pips (top-right, 1 to 4), a bottom tag (`+ MERGE`), a port tag. No rule
text, no stats. Drive cells carry a floor shadow; rarity is the real ring model drawn over the body, never a new body
[image: kit-3]. Keystones are arch stones with a letter. Disc art (CSS icons 64x56, portraits 136x188) is drawn at
run time from game memory inside a generated hatched frame with the two-letter abbreviation; it is never stored
(section 12, item 8).

### 4.9 Motion

Times are on the UI clock (wall time, rate independent at 60 or 120 Hz, like `gd.kit.model` `spin` [doc:
scripting.md:361]), not logic frames. [image: kit-5]

| What | ms | Curve | Note |
|---|---|---|---|
| focus lift | 80 | ease-out | plate up, edge turns ember, brackets draw in |
| tab change | 120 | ease-out | |
| explainer swap | 100 | linear | cross-fade; skipped under reduced motion |
| dialog | 140 | ease-out | scrim to 72 %, plate rises 6 px |
| corner note | 160 in, hold 3 s | ease-out | timer rule drains |
| reward cards | 40 stagger | | |
| model turntable | 12 s per turn at rest, 6 s in focus | linear | |
| merge | 240 | ease-in-out | |

A **Reduced motion** setting (new; there is none today [doc: inventory 3.6]) turns every tween into a cut and stops
turntables. It lands in step 1 so no part is built without it.

### 4.10 4:3 and wide

The canvas is 640x480 logical. Width follows the window: `w = 480 x aspect`, never under 640 (the grid component's
documented minimum [doc: `melee/pc/scripts/examples/demos/grid-inventory/README.md`]). Two arrangements [proposal]:

| | Compact (`w < 760`) | Wide (`w >= 760`) |
|---|---|---|
| chapter | five dots top right | a 104 px rail at the left, 12 px gap |
| primary / explainer | as 4.4 | primary and explainer grow by the free width; a grid gets more columns, never bigger cells |
| content cap | | content is at most 1140 wide and centred; ground and graticule fill the rest |
| what appears | the same set of things in both |

The native frontend today centres a 4:3 band on wide windows (`GM/gmfrontend.c:920-932`, [image: inventory `css225.png`]);
Atlas replaces that per screen as it moves. Hit tests, key hints and focus use the arranged rectangles, never the
authoring ones.

## 5. How it works today (the facts the design must fit)

| Fact | Where |
|---|---|
| The native frontend is a game mode, `GM_FRONTEND`, with one state and one scene `GS_FRONTEND`. `gmFrontend_Route(from, to)` runs on every mode change and may return `GM_FRONTEND` instead of `to`. | [code] `GM/gmfrontend.c:44-96, 861-907, ~2170-2186` |
| Entering `GM_MENU`: if `MELEE_FRONTEND_MENUS` is on (`fe_menus_on`), the frontend either hands out a native screen request (`fm_route_native`) or turns the position into `(MenuKind, selection)` and opens its own menu (`fm_route_position`, `fm_route_to_menus`). Other pairs go through the `fe_rules[]` table (today one rule, `GM_MENU -> GM_VS` shows MATCH SETUP). | [code] `gmfrontend.c:655-657, 871-907, 1196-1212` |
| A menu is `FeMenu` (`kind`, hub or list, items); an item is `FeMenuItem` with `act` in `FA_SUB, FA_MODE, FA_NATIVE, FA_MATCH_SETUP, FA_ONLINE, FA_PAGE, FA_TBD`; `fm_menus[]` is the tree and `fm_find`/`fm_replaced` ask whether a kind is ours. `FA_NATIVE` leaves for the retail screen and comes back through `gmFrontend_NativeReturn`. | [code] `GM/gmfrontend_menus.inc:39-65, 204-238` |
| A settings or rules screen is a table of `FrontendItem` (action, choice, slider, toggle with `get`/`set`/`visible`/`enabled`); the screen is `FrontendScreen`; a per-frame function walks it (`fk_frame`). Room screens are drawn from layout JSON (`art != 0`). | [code] `gmfrontend.c:100-134, 1980-2030`; `GM/CLAUDE.md` |
| The CSS/SSS is `GS_FRONTEND` only for VS, Training and the LAB (`gmFrontend_SelectScene`, `TrainingSelect`, `ModeSelect`). About 19 other mode files declare 23 `GS_CSS` states between them (Classic, Adventure, All-Star, Event, Camera, Home-Run, Multi-Man with seven, about nine special melees, a data scene...). | [code] `gmfrontend.c:774-830`; `grep GS_CSS src/melee`: 21 files outside `gmfrontend` (VS and Training are the two that already call the kit; `gm_1A3F.c` is a switch case) |
| Native screens draw through the game's text canvas and GX link callbacks, with their own copy of the font loader (`FfRole`). `gd.kit` draws through the host: `GwKitQuad` quads in a two-bank list (`KQ_MAX` 16,384) shown by the ImGui overlay pass, with its own loader (`KfRole`). | [code] `GM/gmfrontend_kit.inc:38-56`; `PL/gw_kit.h:46-58`; `PL/gw_kit.c:1155-1158` |
| Mouse input is local UI only: it becomes what a pad press would have done and never reaches pads or netplay. | [code] `GM/gmfrontend_mouse.inc:1-17`; [doc] scripting.md:485 |
| `gd.kit` is drawing only, allowed online. `gd.input_mask`/`input_chord` and every gameplay write are refused in a netplay or rollback session by `gs_require_offline`. Hooks do not run on resimulated frames. | [code] `PL/gw_script.c:838-844, 1893-1900`; [doc] scripting.md:202-244, 337-345 |
| Envoy's bag and reward screens are Lua on a copied grid component (`D.grid`, embedded by `tools/port/envoy_bundle.py`), rebuilt on events, drawn from a cache, pad only; the focus rule is "nearest cell strictly in that direction (distance plus twice the sideways offset)". | [code] `melee/pc/scripts/examples/envoy/scripts/run_screen.lua:1-12`; [doc] `envoy/MENUS.md`, `demos/grid-inventory/README.md` |
| **The main-menu tile.** `fm_main` has `SUPERTIME ENVOY` as `FA_TBD`, visible when `Script_TbdAvailable()`; its confirm calls `Script_TbdRequest()`. The host answers true only if a script with id **`roguelite/main`** is enabled and gameplay. The consumer is `gd.tbd_request(true)` in the older **`roguelite`** example. The Envoy mod (id `envoy`) never calls it. | [code] `GM/gmfrontend_menus.inc:69-70, 246-251, 1222-1226`; `PL/gw_script.c:4093-4097, 7692-7701`; `melee/pc/scripts/examples/roguelite/main.lua:1250`; `envoy/mod.json` |
| The LAB entry is the same pattern (`SEL_1P_LAB`, `gd.lab_request`). | [code] `gmfrontend_menus.inc:42, 92`; `gw_script.c:4084-4089` |
| The launcher is a Qt program with its own kit (`kit.cpp`) and strings looked up by exact English text (`Lang.cs`; the Qt window uses `t("English", "Spanish")` pairs). | [code] `tools/release/launcher/qt/window.cpp:433`; `Lang.cs:1-12`; root `CLAUDE.md` |
| Standalone C tests exist and need no game: `tools/port/native_test.sh` builds e.g. `pc/tests/controls_remap_test.c`. | [code] `tools/port/native_test.sh:31` |

## 6. Architecture

### 6.1 The decision: the parts live in the host

Two places could own the parts: the game-side frontend (retargeted C, drawing through the game's GX) or the host
(`PL/`, drawing quads through the overlay). Atlas lives in the **host** [proposal], because:

- Lua can only call the host. The one-component-set rule needs Lua and native screens on the same code; the host is
  the only place both can reach. Game-side C cannot hold a Lua state or a native pointer (`melee/CLAUDE.md`, "shim
  boundary").
- The host already owns what parts need: atlas text with kerning and fit (`gw_Kit_*`), tinted masks, model cells
  (`gd.kit.model`), mouse and keyboard, and the UI clock.
- Host code is plain C with no game memory, so layout and focus are testable without the game
  (`native_test.sh` precedent).
- It removes the duplicate font loader (`FfRole` against `KfRole`).

Costs, stated: (a) game-side screens become adapters that submit a view each frame and apply the events they get back
(6.7); (b) the host draws in the overlay pass, above the game's own UI, so Atlas needs its own fade quad where the
native screens used the game's fade (`gmfrontend.c:916-948`); (c) retail art that lives in game memory (disc icons)
must be decoded host-side (section 12, item 8). If the overlay turns out to lag or reorder against a frontend scene,
the fallback is a thin game-side GX backend that reads the finished quad list through scalar accessors; the units
below do not change [unverified: the overlay's ordering against frontend scenes].

### 6.2 Units

| Unit | Does | Depends on | Lives in | Native or Lua |
|---|---|---|---|---|
| **U1 draw layer** | text (roles, fit, tracking), images, masks, polys, triangles, model cells into the quad list | texture loader, font manifest | `PL/gw_kit.c` (extended) | native C (exists) |
| **U2 parts** | emit each part from geometry plus state: plate, row, tab strip, toggle, choice, slider, cell, model cell, explainer, dialog, note, key hints, trail, rail; record hit rectangles | U1, tokens | `PL/gw_ui_parts.c` | native C |
| **U3 screen and layout** | the screen record (the one in-memory description), validation, arrangement for compact and wide, text-fit lint, explainer cache | U2, tokens | `PL/gw_ui_screen.c` | native C |
| **U4 focus and input** | intents from pad, mouse, keyboard; focus graph; repeat; scrolling; value change; events out | U3 | `PL/gw_ui_focus.c` | native C |
| **U5 stack and router glue** | screen stack, push/pop/replace, transitions and fade, modal, owner port, "which scenes show Atlas", hand-off with `gmFrontend_Route` | U3, U4 | `PL/gw_ui_stack.c` + `GM/gmfrontend_atlas.inc` | native C, one game-side file |
| **U6 registry** | entries by parent, ordering, visibility, mod manifests, caps | mods list, U5 | `PL/gw_ui_registry.c` | native C |
| **U7 script binding** | `gd.ui.*`: screen, invalidate, entry, note, dialog, key hints; callbacks | U3-U6, the script engine | `PL/gw_script_ui.inc` | native C binding, Lua content |
| **U8 game-side adapter** | submits a `FrontendScreen` or `FeMenu` view each frame through shims, applies returned events | shims `gw_Ui_*` | `GM/gmfrontend_atlas.inc` | retargeted C |
| **U9 content interface** | the files a mod provides: `mod.json` `menus`, `ui/` art, models, text | U6, U7 | docs and the loader | data |
| **Tokens** | one file of colours, sizes, timings | | `menu/atlas/tokens.json` (generated from `ATLAS/tokens.css` by `menu/pipeline`) | data |

Why parts, layout, focus and stack are native: they run every frame and must be identical for all callers,
testable, and outside the 50 ms script budget [doc: scripting.md:217]. Why content is Lua: screens are data and
event handlers; changing a rule line is a text edit, and a mod cannot add native code. A Lua screen costs script time
only when it rebuilds (on `invalidate`) or handles an event, never for layout or focus.

### 6.3 Dependencies

```
U9 content --> U6 registry --> U5 stack --> U4 focus --> U3 layout --> U2 parts --> U1 draw
U7 Lua binding ----------------^                          ^
U8 game-side adapter -------------------------------------'   (both U7 and U8 build the same U3 record)
tokens --> U2, U3 (and the launcher, section 13 step 9)
```

U1 to U6 have no game or Lua dependency. The Lua binding and the adapter are the only two doors in.

### 6.4 The router: how old and new coexist

No new routing mechanism. A screen is owned by exactly one handler, chosen per screen:

1. **Tree screens** (hubs, lists, settings pages, today `fm_menus[]`): each `FeMenu` gets a style `FM_ATLAS`
   (alongside `FM_HUB`, `FM_LIST`) [proposal]. `fm_find`/`fm_replaced` already decide whether a kind is "ours", so
   the existing position protocol `(MenuKind, selection)` and the retail back-out (`gmFrontend_NativeReturn`) keep
   working unchanged. An `FM_ATLAS` menu is drawn by the host: the per-frame function (`gmfrontend.c:1980-2030`)
   gets one new early branch, like the existing `fe.screen->art != 0` branch, that calls `fa_frame()` and returns.
   Confirm and back still end in `fm_do_pending`, which runs the same `FA_*` action as today.
2. **Rule screens** (`fe_rules[]`, VS flow): a rule's `FrontendScreen` gets an `atlas` id instead of rows. Same
   hand-off to `continue_to` / `back_to`.
3. **Retail screens** are reached by `FA_NATIVE` as now. A retail screen replaced in step 8 changes its `FeMenuItem`
   from `FA_NATIVE` to `FA_ATLAS` (new, opens an Atlas screen id). Entry `sel` indices stay the vanilla ones, so
   vanilla positioning code is untouched.
4. **Scenes that are not frontend screens** (title, results, the match, the bespoke retail scenes): the **scene
   policy** of 6.8 (steps 2, 3, 8, 10). A hook on the scene table, not a new router.
5. **Mod screens** are stack entries pushed by an entry or by `gd.ui.open(id)`; they run inside whichever scene is
   active (`GS_FRONTEND` for menus, a match for the in-match bag). No game mode is added.

Fallbacks: `MELEE_FRONTEND_MENUS` and `MELEE_NATIVE_CSS` stay until the legacy path they guard is deleted; a new
`MELEE_ATLAS=0` makes `FM_ATLAS` fall back to the legacy style for that kind while both exist [proposal]. Each step
retires its legacy path only after the owner's look.

### 6.5 Native or Lua: the rule

| | Native C (host) | Native C (game side) | Lua |
|---|---|---|---|
| Parts, layout, focus, input, stack, registry, fade, motion | yes | | |
| Screens whose truth is native state: settings tables, MATCH SETUP, CSS/SSS, the online room and lobby, loading | | yes (adapter) | |
| Screens that are only a list: Credits, the mods list (reads `Mods_*` [doc: mods-packaging.md section 4]) | yes (host C descriptions) | | |
| Mod content: Envoy, the LAB, demos, any mod | | | yes |

### 6.6 What each part draws

A part is a function `at_<part>(geometry, state, content)` that appends quads through U1 and a hit rectangle to the
screen's hit list. A chamfered plate is a hexagon drawn as two convex quads plus a front-edge strip (3 quad entries
[estimate]); GwKitQuad's corners are arbitrary, so this needs only a small `gw_Kit_DrawPoly4` helper
[code: `PL/gw_kit.h:46-58`; the current `kq_add` is axis-aligned, `gw_kit.c:1170-1190`]. Parts have no state of
their own except tween progress, owned by the stack.

### 6.7 The two doors: one record, two ways to fill it

- **Lua** builds a screen with `gd.ui.screen{...}` (section 7). The binding copies strings and numbers into the
  record at registration and on `invalidate`; callbacks stay in the Lua registry.
- **Game side** cannot give the host a function pointer. The adapter instead mirrors the existing table each frame:
  `fa_submit(const FrontendScreen*)` walks the items, calls each `get()` and `visible()`, and pushes label, kind and
  current value through scalar shims (`gw_Ui_ItemBegin(kind, id)`, `gw_Ui_Label(str)`, `gw_Ui_Value(int)`,
  `gw_Ui_Options(...)`), strings crossing as the existing shims do (`Settings_SetInt("envoy_online", v)`,
  `gmfrontend.c:554`). It then reads events (`gw_Ui_PollEvent(&item, &arg)`) and calls `set()` or the action. So
  **every existing `FrontendItem` table keeps working as the screen**; a settings page still costs one table.

Per-frame submission cost is a few hundred bytes of strings per screen; the host diffs and rebuilds the layout only
when something changed [estimate; unmeasured].

### 6.8 The retail takeover capability (built, off by default)

The owner's direction for the retail percent/stock/timer HUD and the retail pause is "get prepped for it/build
capability to" (section 2). So the capability is built and tested; **using** it on the retail numerals and pause is a
later decision he makes with the result in front of him. Nothing is hidden or replaced by default.

**What retail draws, and where it can be reached** [code]:

| Retail thing | How it is drawn | The one place to guard it |
|---|---|---|
| Damage (percent) plate | a GObj per player with GX link render callbacks `ifStatus_802F5DE0` / `ifStatus_802F5E50`, plus per-frame procs `ifStatus_802F5B48` / `ifStatus_802F4EDC` that animate it | the two render callbacks (`src/melee/if/ifstatus.c:633, 655`, created at `:692, 798`). The procs are never skipped: they keep their state running |
| Stocks | GObjs with callbacks `fn_802F9680`, `fn_802F94E0`, `fn_802F95E8`, `fn_802F9548`, `fn_802F9598` | `if/ifstock.c:590-1083` (the creation sites name them) |
| Timer | GObjs with `HSD_GObj_JObjCallback` | `if/iftime.c:214, 258` |
| Name tags, zoom, coin and prize readouts, hazard | `ifnametag.c`, `ifmagnify.c`, `ifcoget.c`, `ifprize.c`, `ifhazard.c` | each file's render callback |
| Pause panel (background plus L/R/A/Start, Z and analog-stick drawing) | the `GmPause` archive; `gm_801A0FEC(slot, flag)` shows it, `gm_801A10FC` hides it; with `flag == 0` it hides the background itself (`gm/gmpause.c:42-69`) | the callers: `gm/gmvs.c:1200, 1279, 1354`; `gm/gmcamera.c:270, 307`. The pause camera is `gm_EnablePlayerPauseCamera` |
| Title, results | whole scenes in the scene table (`gm/gmscdata.c`; results in `gmresult.c`, `gmresultplayer.c`) | the scene's `on_enter` / `on_frame` pair |
| Bespoke 2D menus (trophies, tournament...) | JObj trees hidden or shown with `HSD_JObjSetFlagsAll(jobj, JOBJ_HIDDEN)`, as retail itself does (`ty/toy.c:2667, 2873`; `gmpause.c:50-66`) | the same call, applied by the port |

**The capability, in four parts:**

1. **Scene policy** (`GM/gmfrontend_atlas.inc`, one table keyed by scene kind). Each entry is `RETAIL` (the default for
   every scene), `OVERLAY` or `REPLACE`.
   - `OVERLAY`: the retail `on_enter` and `on_frame` run unchanged, so its archives load and its logic runs; after
     them the adapter submits an Atlas screen and the host draws it. The scene's element mask applies.
   - `REPLACE`: the retail scene is not entered; a `GS_FRONTEND` stand-in takes its place with the same
     continue/back targets, the way `gmFrontend_Route` already does for the menus. Only valid where the scene's
     outputs are simple to reproduce (the title, results).
   The hook point is the scene table's function pair (`gmscdata.c`, entries such as `Toy_Scene_OnEnter` /
   `Toy_Scene_OnFrame` at `:141-143`), wrapped under `TARGET_PC` with the unprefixed-shim convention.
2. **Retail element registry and mask.** A `u32` mask in the host, `gw_Ui_RetailHidden(id)` readable from the game
   side. Each guard is one line at the single draw site: `if (gw_Ui_RetailHidden(ELEM_HUD_DAMAGE)) return;` at the
   top of a render callback, `flag = 0` for the pause panel, `JOBJ_HIDDEN` for bespoke JObj pieces. Presentation
   only: a guard never skips a proc, so no simulation or state changes, and with the mask empty the code path is as
   today. The mask is set by the scene policy, by `gd.ui.retail_hide{ids}` (offline only; a mod may never hide the
   match clock or result data), and for testing by `MELEE_ATLAS_RETAIL=<ids>` or a console command.
3. **A HUD zone description.** `gd.ui.hud{ id, zones = {...} }`, native or Lua. Zones are named rectangles inside the
   title-safe box: `top_left`, `top_center`, `top_right`, `bottom_left`, `bottom_center`, `bottom_right`. Each holds
   parts: the built-in `port_card{port}` (numeral and shape, name, percent, stocks, from the readbacks scripts already
   use, `gd.player` and `gd.match` [unverified: that percent and stocks are exposed for all four ports]), `timer{}`,
   `note{}`, `strip{}` (the build strip), `banner{}`. Retail elements that are still visible declare **keep-out
   rectangles** (damage plates, timer, stock icons) so Atlas parts never collide with them at 4:3 or wide. A HUD zone
   never takes focus, never masks the pad, draws online, and costs only its quads.
4. **A pause screen description.** `kind = "pause"` is an ordinary screen (list primary, keys, counter) pushed on
   the pause-on call sites above and popped on the pause-off ones; entries come from the match context and from
   mods that register under parent `pause`; intents come from the pausing port. Resume must return control to
   retail through a shim `gw_Ui_RequestUnpause()`; how retail detects an unpause (a START trigger it polls) is
   [unverified], and if the shim cannot be written the Atlas pause stays an overlay that draws entries while retail
   still owns START. Offline only: a netplay match does not get a focus-taking pause (8.4).

**What stays untouched by default:** every scene policy is `RETAIL` and the mask is empty, so retail damage, stocks,
timer, name tags, the pause panel, the title and results are exactly as today. A flip is one table line per scene or
one mask bit per element, tried first with the environment switch.

**Built in:** the scene policy and `REPLACE` in step 2 (first user: the title, if its hook is cheap, 13.2); the
element registry, mask, guards, `gd.ui.hud` with keep-outs and the pause description in step 3 (first users:
Envoy's HUD and pause, which hide nothing retail); `REPLACE` for results in step 8; `OVERLAY` plus the mask for the
bespoke scenes in step 10. Without the game: a table test of the mask and policy, a PowerPC syntax check of every
guard, a layout test of keep-out zones. Must be seen: a match with an empty mask looks as before; with each bit set
exactly that element disappears and nothing else; the Atlas port card beside the retail ones at 4:3 and 16:9.

## 7. The screen description

### 7.1 Shape

A screen has these fields. `?` means optional.

| Field | Meaning |
|---|---|
| `id` | `"<mod or area>.<name>"`; the registry rejects duplicates and ids that do not start with the mod's own id (mods) |
| `trail` | `{ title = "YOUR DRIVES" }`; the parents ("SOLO > ENVOY") come from the entry that opened it; `chapter` is inherited |
| `primary` | exactly one of `list`, `grid`, `tiles` (hub), `cards` (a row of offers), each optionally under `tabs` |
| `explainer?` | `"none"`, a preset (`narrow`, `normal`, `wide`) plus a **provider**: a table, or `function(focus) -> table`, called when focus changes (result cached) |
| `keys` | list of `{ button, label }`; `label` may be a function of the focus; `when` hides a hint; Move, A and B are generated when handlers exist |
| `counter?` | the right-hand footer text ("Bag 1 / 4", "3 / 6"), string or function |
| `on` | handlers: `accept(focus)`, `back()`, `alt = { X=, Y=, Z= }`, `page(dir)`, `change(item, value)`, `open()`, `close()` |
| `modal?` | a dialog over this screen |

Primary variants:

- **list**: `items` (array or function). Item: `{ id, label, sub?, icon?, tag?, value?, disabled? (bool or reason string), selected?, group? }`.
  `value` is one of `{ kind="toggle", get, set }`, `{ kind="choice", options={...}, get, set }`,
  `{ kind="slider", min, max, step, get, set, format? }`, `{ kind="text", get }`, `{ kind="counter", get }`.
  `get` is read every frame and must be O(1); `set` runs on change.
- **grid**: `blocks`, each `{ id, title, count?, cells (array or function), cols?, kind? ("cells" | "stones") }` plus
  an optional `footer` card. Cell: `{ id, model?, ring?, name?, index?, flags = { locked, empty, merge, new, selected }, pips?, origin?, port? }`.
  A cell has **no text beyond `name` and `index`**; the engine draws the name only when there is no model.
- **tiles**: `items` with `icon`, `label`, `blurb`, `tag?`; the engine picks the 2-column hub or the single column by item count.
- **cards**: 2 to 3 offers, each `{ id, model?, name, banner? }`, with the stagger of 4.9.

Explainer table: `{ media = {model=, ring=, spin=}|{icon=}|{frame="disc", text="SO"}, kicker, title, what, with = { cells... }, from = { tag, text }, more = fn }`.
`what` is one short rule: lint limit 110 characters or two lines at the preset width, whichever is shorter; an
over-long string is clamped with an ellipsis and logged once per id (the Envoy ruling: one short rule per piece)
[proposal].

Actions return `nil` or one of `{ push = id }`, `{ pop = true }`, `{ replace = id }`, `{ dialog = {...} }`,
`{ invalidate = true }`, `{ launch = ... }` (only where the mod's existing gameplay permissions allow; section 8).

### 7.2 Worked example: the Envoy bag (Lua, a mod)

This is `run_screen.lua`'s bag mode [code: `envoy/scripts/run_screen.lua:1-12`; layout in `envoy/MENUS.md`], as a
description. Drive models are Lua handles (`gd.model_load`), which is why this screen is a mod's, not the engine's.

```lua
local ui = gd.ui
ui.screen{
  id    = "envoy.bag",
  trail = { title = "YOUR DRIVES" },            -- SOLO > ENVOY > comes from the entry
  primary = { kind = "grid", blocks = {
    { id = "equipped", title = "EQUIPPED",
      count = function() return build:filled() .. " / " .. build:slots() end,
      cells = function() return equipped_cells() end },          -- 6 cells, locks included
    { id = "bag", title = "BAG",
      count = function() return #bag .. " / " .. bag_cap end,
      cells = function() return bag_cells() end },               -- 4 cells
    { id = "keys", title = "KEYSTONE", kind = "stones",
      cells = function() return keystone_cells() end, note = "One held" },
  }, footer = function(focus) return merge_preview(focus) end }, -- "IF YOU MERGE: a + b -> c"
  explainer = { width = "narrow", provide = function(cell)       -- called when focus changes
    if not cell or cell.empty then return nil end
    return {
      media  = { model = cell.model, ring = cell.ring, spin = true },
      kicker = cell.kicker,                        -- "BAG CELL 1"
      title  = cell.name,                          -- "KINDLING"
      what   = cell.rule,                          -- "Your hits set the target Burning for 3 s."
      with   = cell.pairs,                         -- cells that work with it
      from   = { text = cell.origin },             -- "Depth 0, Fire"
    }
  end },
  keys = {
    { "A", function(c) return c and c.merge_into and ("Merge into slot " .. c.merge_into) or "Equip" end },
    { "X", "Discard", when = function(c) return c and c.kind == "drive" end },
    { "Y", "More" },
    { "B", "Close" },
  },
  counter = function(c) return c and ("Bag " .. c.index .. " / " .. bag_cap) end,
  on = {
    accept = function(c) return do_obvious_thing(c) end,         -- merge, else equip, else bag
    alt    = { X = function(c) return ask_discard(c) end },
    back   = function() return { pop = true } end,
  },
}
```

The mod keeps the rules that make the screen correct (what A does, the merge preview, the "ask twice" discard); it
no longer places a pixel, moves a focus, reads the pad, or builds a hint bar. The older bag (`drive_menu.lua`) and
the grid copy (`D.grid`) have no remaining job and are retired by this step.

### 7.3 The same from native code

Host-native description (a screen that is only a list; designated initialisers, callbacks are host functions):

```c
static const AtItem credits_items[] = {
  { .id = "source-sans", .label = "Source Sans 3", .sub = "Adobe, SIL OFL 1.1", .tag = AT_TAG_JADE("FONT") },
  { .id = "barlow",      .label = "Barlow Condensed", .sub = "Jeremy Tribby, SIL OFL 1.1", .tag = AT_TAG_JADE("FONT") },
};
static const AtScreen credits = {
  .id = "more.credits", .title = "CREDITS", .parent = "more", .chapter = 0,
  .primary = { .kind = AT_LIST, .items = credits_items, .n = AT_N(credits_items) },
  .explainer = { .width = AT_NORMAL, .provide = credits_explain },
  .keys = { { AT_B, "Back" } },
};
```

Game-side adapter, for a screen that is a `FrontendScreen` table (nothing changes in the table; only the screen
record that points at it gains an `atlas` flag):

```c
/* gmfrontend_atlas.inc */
static void fa_frame(void)                 /* called from the frontend's per-frame function */
{
    fa_submit(fe.screen);                  /* items -> gw_Ui_* shims, current values included */
    while (gw_Ui_PollEvent(&ev_item, &ev_arg)) {
        fa_apply(fe.screen, ev_item, ev_arg);   /* the item's set(), call(), or FE_DO_CONTINUE/BACK */
    }
}
```

A Lua mod and a C screen end in the same `AtScreen` record; only the way its callbacks are held differs.

## 8. The mod interface

### 8.1 Registering an entry

`mod.json` gains a `menus` array [proposal; the manifest is a flat object today, `scripting.md` "The manifest"; this
is an array of flat objects, parsed like the strings-only reader allows]:

```json
"menus": [
  { "id": "envoy", "parent": "solo", "label": "ENVOY", "blurb": "Explore, fight and evolve your build.",
    "icon": "ico_envoy", "after": "training", "opens": "envoy.setup", "online": false }
]
```

Static, so the Mods screen can say "adds Solo > Envoy" before any script runs [image: `15-mods.png`], and a disabled
mod adds nothing. The registry puts a **MOD** tag on every mod entry (the inventory's "origin" signal). Parents are
the stable ids of the built-in tree: `main`, `solo`, `versus`, `online`, `mods`, `settings`, `more`,
`settings.<page>`, and later `pause` (step 3) and `lab.pause` (step 7). An unknown parent is ignored with one log
line. Visibility can also be driven at run time: `gd.ui.entry("envoy", { visible = false })` (locked until a
condition), `{ badge = "NEW" }`.

`opens` names a screen the script registered with `gd.ui.screen`; or the entry has `action = "script"` and the
mod's `on_entry(id)` hook runs (used when selecting must start a game, as Envoy's Classic run does).

### 8.2 What a mod supplies

- **Screens** via `gd.ui.screen` (7.1) and **notes and dialogs** via `gd.ui.note{...}`, `gd.ui.dialog{...}`.
- **Art** in its own `ui/` (the texture search already looks there first, `PL/gw_kit.h` "TEXTURE SEARCH"), through
  `*_ui.json` manifests. Icons must be Atlas-style masks (the pipeline's generator and a template are step 1
  deliverables). **Models** as `gd.model_load` handles, at most 512 triangles each [doc: scripting.md:361].
  **Text** as plain English strings (section 10).
- **Palette**: none. Atlas has one palette; a mod picks from tokens (`ember`, `jade`, `sun`, `rose`, ports, family
  colours of its own models). Mod palettes in `*_ui.json` keep working for `gd.kit` primitives but not for parts.

### 8.3 What a mod may not do

- Replace or hide a built-in screen or entry. It can only add.
- Register under a parent it does not own an entry for beyond the built-in list, or exceed the caps: 6 entries per
  mod per parent, 12 visible per parent in total (the rest scroll), labels at most 18 characters at `cap20`.
- Run native code, read other mods' screens, or draw parts outside a screen (it may still use the `gd.kit` primitives
  for world-space or HUD drawing, as today).
- Take focus while a netplay session is active (8.4).
- Read the pad directly in a screen and also let the game see it: a screen is modal for the intents it receives; the
  engine, not the mod, decides what the game sees.

### 8.4 Online

Atlas has no behaviour of its own that touches simulation, so the classes are:

| Class | Examples | Online |
|---|---|---|
| Presentation only | parts, hover, focus, mouse, keyboard, notes, dialogs, models, the explainer | allowed everywhere, in a lobby and in a match [doc: scripting.md:337-345] |
| Local input | intents from pad, mouse, keyboard while a screen is open | allowed; mouse and keyboard never reach pads or the netplay stream [code: `gmfrontend_mouse.inc:1-17`] |
| Masking the pad from the game (`gd.input_mask`, `input_chord`, the pause side-effects of a modal screen) | the in-match bag | **refused online** [code: `gw_script.c:838-844, 1893-1900`]; so an online in-match screen is non-modal: it draws and does not pause or mask, as Envoy's menus already behave online [code: `envoy/scripts/menu_input.lua:4-7`] |
| Gameplay writes from a handler | equipping a drive, launching a scene | the existing gates apply: refused online unless the mod is a rollback-safe design that the engine already admits [doc: scripting.md:224-244]. Atlas adds nothing that loosens this |
| Native online state (rooms, lobby, strikes, ready, countdown, coin flip) | the online screens | stay native state machines in `GM/gmfrontend_online.inc`; Atlas only draws them and returns intents. No mod screen is ever pushed over a room screen. Entries under `online` and `versus` are hidden while a session exists unless `"online": true` and the mod passes the existing netplay must-match handshake [doc: scripting.md:238-244] |

Menus that exist online (settings, online rows, room, lobby, loading, character and stage select in a lobby) keep
their logic where it is; step 6 is a drawing change only. Determinism rule for everything above: a screen's state is
never an input to the simulation.

## 9. Input

**Pad first.** The core takes intents; each caller feeds them: Lua reads `gd.pad(port, true)` (the physical, pre-mask
pad, as Envoy does [code: `menu_input.lua:1-7`]); native screens pass the same bits from the game's pad state through
one shim. D-pad or stick moves focus; A accepts; B backs; X, Y, Z are alts; L and R page tabs; START opens the pause
where one exists. Repeat: 300 ms delay then 80 ms on the UI clock [proposal]. The menu follows the port that last
pressed A (`gm_801677E8` today); CSS and lobby keep one token per port.

**Focus.** Lists: up and down wrap. Grids: the nearest focusable cell strictly in the pressed direction (distance
plus twice the sideways offset), holes skipped, blocks crossed in the same row or column, wrap keeps row or column
[doc: grid-inventory README "Focus rule"]; up and down jump between blocks. The last focus on a screen is
remembered when it is returned to.

**Mouse** (an addition): moving the pointer sets focus (only on movement, so a pad is never pulled back), left click
is accept, right click is back, the wheel scrolls lists or steps a value, key hints and tabs are clickable
[code: mouse.inc]. Hit tests use the arranged rectangles recorded by the parts.

**Keyboard** (an addition, menus only): arrows, Enter (accept), Escape (back), Tab and Shift+Tab (page), letters
stay free for hotkeys. The keyboard still never drives the game [doc: scripting.md:487]. [proposal]

**Key hints are generated, not written.** The keys place builds from the screen's handlers and `keys` list, drawn as
glyph plus label. Glyphs are the logical buttons (A green, B red, X and Y grey, Z purple, L R, START, stick, D-pad).
When the Controls remap profile moves a logical button to another physical one, the hint keeps the logical glyph and
the Controls screen's own row shows the physical binding (`Controls_Binding`, `gmfrontend_controls.inc`). If a mouse
or keyboard was the last device used, hints switch to the keyboard keys or the two mouse buttons [image: kit-4].
Whether menus read the pad before or after the remap is [unverified] and decides whether this holds; step 5 checks it.

## 10. Layout, text and language

- Canvas 640x480 logical, wide per 4.10. Every rectangle is computed by U3 from the declaration plus the measured
  text; nothing is placed by a mod.
- **Text fit** (normative): minimum 12 px at 640x480; measure with the same function that draws (including tracking);
  the fit rule steps down one role of the same face, then truncates with an ellipsis; a label never wraps except in
  the explainer (`what`, up to 3 lines) and dialogs (up to 4); a lint pass at registration logs any string that
  needed the ellipsis in the 640 arrangement, so mod authors see it.
- **Language.** English only today [doc: `GM/CLAUDE.md`; atlas is Latin only]. Atlas keeps these possible: every
  string reaches U3 through one lookup keyed by the exact English text (the launcher's scheme, `Lang.cs:1-12`), so a
  table can be added later; no width is assumed (all text is measured; no baked text in any texture); the font
  atlas is paged by script and "a second script adds its own pages ... without moving any latin glyph"
  [doc: `menu/pipeline/font_atlas.py:15-17`]; right-to-left is not designed. Fighter and stage names that the game
  stores in the disc's language are read at run time; a name with a non-Latin character falls back to the English
  name table through the lookup. The retail Language row (English or Japanese, `fm_settings` item) stays a native
  hand-off until the retail text screens are gone (the owner's "ok", section 2), then is removed. The launcher's own Spanish table (`window.cpp:433`) is out of this
  design's reach; docs stay English.
- **Accessibility**: Reduced motion (4.9), 12 px floor, colour never the only signal (numeral and shape for ports,
  hatching for disabled, letter on keystones, words ON/OFF), key hints always present.

## 11. Budgets

| Budget | Limit | What Atlas costs |
|---|---|---|
| Quads per frame (shared with every script draw and model triangle) | 16,384 (`KQ_MAX`) [code: `gw_kit.c:1155`] | A screen's own parts: **130 to 600 quads** [estimate: glyph count plus 3 per plate, counted on the 23 mockup HTML files; e.g. main menu 340, bag 345, character select 558, stages 588; not the real engine]. The graticule is one texture tile (or about 150 to 300 quads if drawn as marks). Brackets: 8 thin quads, focus only. Screen cap: **4,096** entries, warn at 3,000 [proposal] |
| Model cells | 512 triangles per model, 64 atlases [doc: scripting.md:361] | Drive bodies are 24 to 80 triangles, rings 74 to 146 [doc: `envoy_drives/README.md`]. Bag worst case: 16 cells at body plus the heaviest ring (about 226) = **3.6k triangles**, typical about 1.5k; one large explainer model about 226 [estimate]. Script cost per model call about 4 microseconds at 12-44 triangles [doc] |
| Script time | 50 ms or 2,000,000 instructions per call [doc: scripting.md:217] | Layout, focus and hints are native, so an idle Lua screen costs **0 per frame**; a rebuild is bounded by the screen cap. The grid component measured 0.3 to 0.4 ms per draw [doc: grid README]; Atlas should land below that, **target 0.5 ms total per frame for any screen** [proposal] |
| Frame | 8.3 ms at 120 fps | Menus are not the frame's cost centre; the budget above is the rule. Measured only when built [unverified] |
| Texture memory | host decodes to RGBA8 [code: `gw_Kit_TexPixels`, `gw_kit.h`] | The legacy font pages are **7.7 MB** decoded if all are loaded [measured: the 2x PNG sizes of `menu/out_kit/font/2x`]. Atlas adds 13 pages: Barlow 7 pages (about 4 MB), Source Sans 3 pages (about 0.8 MB), mono (about 0.4 MB), icons and masks (about 1 MB) = **about 6 to 7 MB** [estimate by analogy with the legacy page sizes]. Net after step 9 removes the legacy pages: about zero. Pages decode on first use (if so, unused roles are free) [unverified] |

The Atlas look itself is cheap: flat quads, no shader, no new pass.

## 12. Engine work beyond what exists

| # | Work | Why | Fallback if it slips |
|---|---|---|---|
| 1 | **Atlas font pages**: Barlow Condensed (SemiBold 12-20 tracked, Bold 28/44/64) and Source Sans 3 Semibold 12-16, Hasklug Medium 12-16, as a second page set in `font_atlas.py` and the manifest | 4.3 | Source Sans 3 Bold caps at the same sizes; the mockup says titles run about 12 % wider [doc: ATLAS/README.md], so the fit rule steps down one role more often |
| 2 | **Letter-spacing** (`tracking`, em/100) in `gw_Kit_DrawText`, `gw_Kit_TextWidth`, `gw_Kit_Fit` | caps labels | none (labels read slightly tighter) |
| 3 | **Hatch mask**: one small I4 tile drawn with repeated UVs for disabled, locked and disc-art frames | 4.1 | flat dim fill plus a word ("Closed", "Locked", "Disc art"). Needs the overlay sampler to wrap [unverified]; if it does not, UVs repeat by emitting one quad per tile |
| 4 | **Chamfer helper** `gw_Kit_DrawPoly4` (arbitrary four corners, flat or masked) | plates | build every plate from axis-aligned quads (square corners): the look loses its chamfers only |
| 5 | **Graticule tile** (48 px `+` mark, wrap) on the ground | the ground | plain ground |
| 6 | **Key-hint glyph and icon sets** in Atlas style: 36 line icons (the mockup set), pad glyphs recoloured to the Atlas pad tokens | parts | reuse legacy `glyph_*` masks tinted; keep legacy icons for entries without a new one |
| 7 | **Reduced motion** setting and the tween service on the UI clock | 4.9 | none; step 1 does not ship without it |
| 8 | **Disc-art cells**: decode retail icon and portrait textures from game memory host-side (`gw_Kit_TexAddGX` already decodes GX buffers from script models, `gw_kit.h`; `kit_decode_formats` test) and cache per fighter | CSS, SSS, results | the hatched frame with the two-letter abbreviation, which is the mockup's own placeholder |
| 9 | **Model turntable**: nothing to add; `gd.kit.model` already takes `spin` and `t` [doc: scripting.md:361] | | |
| 10 | **Model cells for native screens**: a host call taking a model handle created by Lua. Needed only when a native screen wants a model | | native screens use the frame, not a model |
| 11 | **`gd.ui`** binding, **registry**, **manifest `menus`** parsing | section 8 | |
| 12 | **The retail takeover capability** (6.8): the scene policy table, the retail element registry and mask with its guards, `gd.ui.hud` keep-out zones, the pause description and `gw_Ui_RequestUnpause` | steps 2, 3, 8, 10 | an unreachable element stays retail; the capability is still built for the others |
| 13 | **The `view` part and readback shims** for framed retail scenes: an opaque plate with a transparent window over the retail 3D render, and scalar shims that read retail state (current trophy, cursor, counts) | step 10 | draw the Atlas chrome without a window and let the retail 3D fill the screen behind the plates |

## 13. The migration plan

Common to every step: **verification without the game** is (a) a standalone C test of layout and focus for the
parts and screens the step adds (built by `tools/port/native_test.sh` like `controls_remap_test.c`): arranged
rectangles at 640x480, 853x480 and 1140x480 (a 2.25:1 window is 1080x480), no text under 12 px, no overlap, inside
the title-safe box, hint fit, contrast of the token pairs against the table in 4.2, quad count under the screen cap;
(b) a Lua stub test of every `gd.ui` description (like `melee/pc/geno/tools/lab_stage_d_check.lua`): fields valid,
ids unique, providers callable with sample content; (c) optionally a dump of the quad list to SVG for reading a
layout offline. **What must be seen in the game** is always: the screen at 4:3 and at 16:9, focus by pad and by mouse,
the key hints, and Reduced motion; it is looked at by the owner, or by an agent only while he is away (his rules on
windows and screenshots apply). Sizes: S small (days), M medium (about a week), L large; steps 8 and 10 are made of independent screens, each of which can be dropped.

### 13.1 Step 1: the parts and the Envoy bag (size L)

| | |
|---|---|
| Screens covered | Envoy **Bag screen (YOUR DRIVES)** (the inventory's 1.3), opened as today by Z+START in a fight and `bag` |
| Delivers | U1 additions (items 1-5, 7 of section 12; icons for the bag only), U2 all parts, U3 screen and layout, U4 focus and input (pad, mouse, keyboard), U5 stack (fade, modal, in-match non-modal online), `gd.ui.screen`/`invalidate`/`note`/`dialog`, `menu/atlas/tokens.json` and its generator, the Reduced motion setting, `docs/TERMINOLOGY.md` entries, a `docs/scripting.md` `gd.ui` section, `CREDITS.md` (Barlow now ships) and the OFL text in the package |
| Not yet | the registry and manifest `menus` (the bag still opens from its chord), native adapter (U8), any native screen |
| Retired | Envoy's older bag, `drive_menu.lua` and its Lua text wrap (inventory 3.4 "two bag UIs"); the bag's use of the embedded grid (`D.grid`; the component stays for reward and swap until step 3) |
| Depends on | nothing else; this is the root |
| Verified without the game | the common checks above for the bag at three widths; the Lua stub test of `envoy.bag` with the real cell shapes; `grid_inventory.lua` equivalence of focus movement (same neighbour for the same cell sets, since the rule is the same); quad and triangle budget with 16 drive models |
| Must be seen in game | the bag in a Classic run with drive models in cells and the explainer, the merge preview, discard dialog, hints, Z+START in and out, online non-modal behaviour in a room, 4:3 and 16:9, focus cost with the profiler |
| Done when | the Envoy bag is the Atlas bag, `drive_menu.lua` is deleted, the legacy grid still serves reward and swap, and the owner has looked at it |

Order inside step 1: (1) tokens and manifest generator; (2) font pages and tracking (fallback ready); (3) parts and
layout with the standalone tests; (4) `gd.ui` binding; (5) the bag description; (6) the in-game look.

### 13.2 Step 2: title, main menu, Solo and the hubs (size L)

| | |
|---|---|
| Screens | **Title** (retail `gmtitle.c`, "Press Start"); **MAIN MENU**, **SOLO**, **REGULAR MATCH**, **STADIUM**, **MULTI-MAN MELEE**, **VERSUS**, **SPECIAL MELEE**, **COLLECTION**, **SETTINGS** (the list), **DATA**, **RECORDS** (the lists; their destinations stay retail until step 8); first-boot onboarding; a new **Credits** screen |
| New structure | main menu is Solo, Versus, Online, Mods, Settings plus the More row; Online and Mods become top-level (their destinations are still the old Online rows and `Settings > Mods` page until steps 6 and 7); VERSUS keeps Melee, Tournament, Special Melee, Rules, Name Entry [image: `02-main-menu.png`] |
| Delivers | the registry (U6) and manifest `menus`; U8 game-side adapter for `FM_ATLAS` menus; the **scene policy** table with `OVERLAY` and `REPLACE` (6.8), first used for the title; **Envoy's entry** (`solo > ENVOY`, `opens` its setup) replacing the tile; the LAB entry as a built-in entry owned by its mod |
| Retired | `FM_HUB`/`FM_LIST` drawing and the hub/list art sets (`out_hub`, `out_hub_bouba`, the hub and list parts of `out_nav`, `hub_layout.json`, `list_layout.json`); `FA_TBD`, `SEL_MAIN_TBD`, `Script_TbdAvailable`, `Script_TbdRequest`, `gd.tbd_request` and `gd.lab_request`'s menu path (moved to the entry's `on_entry`); the old `roguelite` example's use of the tile (migrate or remove it; it is the only consumer, `roguelite/main.lua:1250`, and removal is a version change under scripting.md "Versioning") |
| Depends on | step 1 |
| The title | Decided ("lgtm", section 2): in step 2 if the hook is cheap, else step 8. The hook is the scene policy of 6.8 (`REPLACE`, a stand-in between the opening and the menu, or `OVERLAY`); `gmtitle.c:281` has the port's only edit today. The retail attract loop's timing is kept. Step 2 builds the policy table and tries the title first; if its retail scene proves entangled the title moves to step 8 and step 2 ships without it |
| Verified without the game | all hub and list screens as descriptions at three widths; the position protocol: a table test that every `(MenuKind, selection)` that `fm_position_for` can produce maps to the same screen and item as before (the legacy table is the oracle); registry tests (caps, ordering, unknown parent, disabled mod adds nothing); `fe_menu_sweep.py` if it runs without the disc [unverified] |
| Must be seen | each hub in 4:3 and 16:9; the walk Title > Main > Solo > Envoy and back with B; coming back from a retail screen lands on the right item; first-boot flow; the mods list says "adds Solo > Envoy" |

### 13.3 Step 3: Envoy's remaining screens and the in-match HUD (size M)

| | |
|---|---|
| Screens | Envoy **Reward screen**, **Swap** ("BAG FULL"), **Setup**, **Pause / confirm / quit**, **Interlude / Results** (the live ones), **online reward box** (the plain debug box [doc: audit #23]); in the HUD: the **build strip**, **opponent card**, **announcement and pickup notes** reduced to the corner note, **"Collect the drives" banner**, **synergy notice** (a small top-corner note), co-op strips; the pause screen of a match (see below) |
| Delivers | `cards` primary and the countdown note; the HUD parts as corner notes, banners and strips (parts only, drawn by `gd.ui.note` and `gd.ui.hud`); the generic builder pieces move into the engine as parts and their **assets stay in the mod** ("the builders get generic'd... assets provided by the mod") |
| Retired | `run_screen.lua`'s grid use and the embedded `D.grid` plus `embed.py` flow; `menu.lua`, `menu_draw.lua`, `menu_input.lua` screens that are replaced; the duplicate `hud.lua` companion panel and tag panel [doc: audit #24, #25]; the Modifier LAB text box and Drive LAB card stay developer-only (`envoy devui`); the grid demo is kept as a demo only if it moves to `gd.ui` |
| Parked Envoy screens | title, profile, hub (garden), fighter, companion, records are "parked" by the 2026-10-04 retail contract [doc: `envoy/MENUS.md`]. **Delegated decision** (owner: "idk do what's optimal"): they are **not ported**; their UI wiring is removed with the legacy screens in this step and their logic stays |
| HUD and pause capability | Built in this step (6.8): the retail element registry, mask and guards for damage, stocks, timer, name tags and the pause panel; `gd.ui.hud` with keep-out zones; the pause screen description with the pause on/off hooks (the `gmvs.c` and `gmcamera.c` sites). Envoy's HUD and pause (Resume, Bag, Controls, Quit run [image: `12-pause.png`]) are the first users and **hide nothing retail**. Replacing the retail numerals or the retail pause is the owner's later call, made with both versions in front of him |
| Depends on | steps 1 and 2 (the entry and setup under Solo) |
| Verified without the game | Lua stub tests for each screen; cap tests (at most one announcement visible, no queue longer than the ruling allows); corner-note layout at three widths with the retail HUD rectangles as keep-out zones |
| Must be seen | a full Classic Envoy run from the entry to the results; reward with the countdown; swap; online Envoy reward box; the HUD against the retail HUD at 4:3 and 16:9 (the build strip must not collide) |

### 13.4 Step 4: character select, stage select, Versus rules (size L)

| | |
|---|---|
| Screens | **CHARACTERS** (kit CSS), **STAGES** (kit SSS), **MATCH SETUP**, **LOADING ("GET READY")**, and the retail **Rules**, **More Rules**, **Item Switch**, **Random Stage Switch**; ONE character select for every mode |
| One CSS | today the kit CSS serves VS, Training and the LAB; about 19 other mode files own a `GS_CSS` state and its enter data (`gmFrontend_SelectScene` is called from three). The design: one Atlas CSS driven by a **mode profile** the mode declares (players allowed, CPU allowed, teams, costume rules, fixed fighters); a mode that fixes its fighter (Event) skips it as now. Each mode's CSS state calls the same entry and fills its own data. Modes migrate in groups: VS family (special melees share VS machinery [doc: inventory 1.1]) first, then Classic, Adventure, All-Star, then Event, Camera, Stadium, Multi-Man |
| Delivers | disc-art cells (item 8), port cards, strike/ban-capable stage grid (drawing only; the strike protocol is step 6), the profile mechanism, the hand-off of `CSSData`/`SSSData` unchanged |
| Retired | the retail CSS/SSS screens once the last mode is moved; `MELEE_NATIVE_CSS` and `Frontend_NativeSelect`; `gmfrontend_select.inc` drawing; the unwired `out_nav` art for rules and grids; `Frontend_TrainingSelect` |
| Depends on | steps 1, 2 |
| Verified without the game | layout tests with sample rosters of 26, 29 and 60 fighters at three widths; focus tests (4 ports, token per port, CPU toggles); a table test of each mode's declared profile against the mode file it replaces |
| Must be seen | each mode group in a real match start (that `CSSData` still gives the right fighters, costumes and team); Training and LAB unchanged in behaviour; CSS with disc art on the vanilla disc and with ACE [memory: test with ACE]; the stage grid with custom stages |

### 13.5 Step 5: settings and the remap editor (size M)

| | |
|---|---|
| Screens | SETTINGS pages **VIDEO, AUDIO, CONTROLS** (+ **remap editor**, **how-to**), **ONLINE** (the settings page), **GAMEPLAY**, and the retail rows **Rumble, Screen Display, Erase Data** (settings rows, so they go here, not to step 8); the Reduced motion row. The retail **Language** row stays a native hand-off (the owner's "ok") until the last retail text screen is gone (steps 8 and 10), then is removed |
| Delivers | tab strip over pages (the settings tabs of [image: `14c-remap.png`]), toggle, choice, slider as tables through the adapter; the remap editor's capture state stays in `gmfrontend_controls.inc` and `Controls_*`; hints per 9 |
| Retired | `gmfrontend_kitlist.inc` row drawing, `widgets_layout.json`, `list_layout.json`, the legacy widget art (`out_kit` widgets and glyph pieces that Atlas replaces) |
| Depends on | steps 1, 2 |
| Verified without the game | every page as a table through a stub adapter (item counts, formats, `visible`/`enabled`); `controls_remap_test.c` still passes; hint tests with a synthetic profile |
| Must be seen | each page; change a value and see it applied; the remap capture flow (timed press and release) with a real pad; hints after a remap (answers the pre/post-remap question in section 9); Erase Data's confirm dialog |

### 13.6 Step 6: the online room (size M)

| | |
|---|---|
| Screens | **ONLINE PLAY** rows (Host, Join, Random Opponent placeholder, Stage List, Turbo, Envoy, Stocks, Time Limit, Input Delay), **JOIN ROOM** (code entry), **WAITING ROOM**, **LOBBY** (strikes, bans, picks, ready, countdown, coin flip) |
| Delivers | code entry part (the `code` role), port cards with ping and the link meter, the dialogs; the **netplay layer is not touched**: drawing and intents only |
| Retired | the room layout JSON and `gmfrontend_online.inc` drawing (`out_lobby`, `out_online`, `fl_*` draw paths); the "Random Opponent (soon)" placeholder row is hidden or removed (owner call, not a question: it is a placeholder) |
| Depends on | steps 1, 2, 4 (the lobby uses the CSS and SSS) |
| Verified without the game | layout tests of every lobby state with sample data; a test that the intent stream into the lobby state machine is identical for pad and mouse; no host file in `PL/gw_ui_*` includes the netplay headers |
| Must be seen | two real clients: host and join by code, strikes, ready, countdown, a full match; a rollback session with a mod screen open (nothing masks, nothing desyncs); a dropped connection mid-lobby. This step is the highest risk for desync: it ships last among the player-facing flows |

### 13.7 Step 7: the mods list and the LAB (size L)

| | |
|---|---|
| Screens | **MODS** (replacing `Settings > Mods`: installed, conflicts, applies at next start, one row per mod with kind and "adds ..." lines [image: `15-mods.png`]); the **LAB**: pause menu tabs **PLAY, DISPLAY, DUMMY, STATES, TOOLS, DRILLS, EXIT**, the info panel, the move timeline and states library (as descriptions), the mode strip as corner notes. Dev overlays (hitbox draws, frame step, console, fly readout) stay dev tools and keep the primitive `gd.kit` |
| Delivers | the mods screen over `Mods_*` (list, toggle, `Mods_Save`, restart note, requirements and conflicts); `lab.pause` parent for LAB's own tabs; LAB's 6 modes' toggles as list items with value widgets |
| Retired | the LAB's own palette (`lab_palette.py`), `lab_frame_*`, the `ico_lab_*` art that Atlas icons replace, the chip and strip drawing in `lab.lua`; `Settings > Mods` page |
| Depends on | steps 1, 2, 5 |
| Verified without the game | `lab_stage_d_check.lua` still passes against the stub; the Lua stub test of the LAB's descriptions; main-chunk local count stays under 200 [doc: LAB `CLAUDE.md`]; the mods screen against a fixture `mods/` folder including a conflict |
| Must be seen | the LAB in a fight with the pause open, states saved and loaded, the info panel while paused; the mods list with a real folder and restart note; the LAB's offline-only behaviour is unchanged |

### 13.8 Step 8: the retail screens that can be rebuilt from data (size L)

Replaced (Atlas screens fed from game state by the adapter), per the owner's rule "unless it has a lot of custom
shit". The bespoke ones are not left retail: they are re-hosted in step 10 (13.10).

| Screen | From | Note |
|---|---|---|
| Event Match list and detail | `gmevent.c` | art exists in `out_nav`; native event data |
| Name Entry | Versus > Name Entry | 4-cell tag editor (`tag` role) |
| Sound Test, Special Messages | Data | list plus a text viewer |
| VS, Bonus, Misc Records | Data > Records | tables |
| Results | `gmresult.c`, `gmresultplayer.c` | scene policy `REPLACE` or `OVERLAY` (6.8); sample KOs and falls in the mockup are not game data |
| Game Over, 1P intermission and bonus summaries | | where the data is a list or a card |
| Title, if step 2 did not take it | `gmtitle.c` | |

Stays as it is: the opening movie and the memory-card prompt (pure video and a boot blocker; there is no menu to
rebuild). Retired: the retail text and layouts for each replaced screen drop out of use; nothing of the disc is
deleted from the game, nothing disc-derived is copied. The retail **Language** row (Settings) goes when the last
retail text screen of steps 8 and 10 is gone (the owner's "ok", section 2).
Depends on 1, 2, 4. Verified without the game: a table test per screen against a recorded sample of the game data it
reads (counts, formats); layouts at three widths. Must be seen: each screen reached by its real path, results after a
real match (and after a netplay match), name entry round trip.

### 13.9 Step 9: the launcher (size M)

The Qt launcher (`tools/release/launcher/qt/`, Windows) cannot link the engine's parts. It is its own piece of work
in the same style: it reads the same `menu/atlas/tokens.json`, re-implements the parts with QPainter polygons in
`kit.cpp` (plates, rows, tabs, toggles, tags, key chips; no model cells), loads Barlow Condensed from `kit.qrc` with
the OFL text in `licenses/`, and keeps four tabs (Play, Mods, Diagnostics, About) arranged on the four places where
they make sense [image: `17-launcher.png`]. Strings keep going through `Lang`/`check_strings.py` (change both copies
and run it, root `CLAUDE.md`). The launcher is mouse and keyboard, not pad. Retired: its copy of the legacy palette
and `Surface`/`Button`, the C# reference launcher's art, and finally the legacy menu art (`menu/out_*` sets that
nothing reads: `out`, `out_hub*`, `out_nav`, `out_lobby`, `out_online`, `out_loading`, the legacy `out_kit` pieces)
together with the legacy font roles and `gd.kit.panel/button/list` (deprecated at API 1 per scripting.md
"Versioning": the old names stay for one version, listed in `gd.deprecated`). Depends on step 1 for the tokens only;
it can run in parallel with 3 to 8. Verified without the game: `graphics_tests.cpp`/`tests.cpp` plus a token
agreement test (C header, Lua palette and Qt constants all generated from the one JSON). Must be seen: the launcher
on a real Windows desktop at 100 % and 150 % scaling.

### 13.10 Step 10: the bespoke retail screens, re-hosted in Atlas chrome (size L, each screen droppable)

**The owner's direction (6):** "maybe we disassemble and reassemble these menus against our new menus so they stay in
theme. Combining the original melee assets into it where we can to preserve the original look". "Maybe" and "where
we can" are kept: every screen below has its own go or no-go, and a screen that proves too costly is dropped
without holding the others up.

**Why a tenth step and not part of step 8.** Step 8 is rebuilding screens from data and stays shippable on its own.
These screens depend on the retail takeover capability (step 3), on `OVERLAY` scenes (6.8), on the `view` part
(section 12, item 13), carry the highest unknowns (each is thousands of lines of retail scene code) and can each be
dropped. Mixing them into step 8 would let one hard screen hold back results, records and name entry.
Depends on steps 1, 2, 3 and 8.

**What "disassemble and reassemble" can mean here [code, my reading of the scenes].** These screens are 3D or JObj
scenes built from archives the retail code loads at run time (`TyMn*.dat`, `Ty*.dat`, `TmBox.dat`, `GmStRoll.dat`,
`SdToy.dat` and so on). The retail renderer draws them in the game's own pass. Atlas quads cannot draw an HSD
model, so the models and animations cannot be lifted into Atlas parts; they stay drawn by retail, from the player's
disc, and nothing is copied or stored. What Atlas can do is the **frame** pattern:

1. The retail scene runs unchanged in `OVERLAY` mode (6.8): its archives load, its logic and its own pad polling run
   (`ty/toy.c:1429-1491`, `gmstaffroll.c:694-819` and `mngallery.c:203-205` all read `HSD_PadCopyStatus` directly), so
   no input is injected and no retail logic is rewritten.
2. The retail **2D menu pieces** (frames, headers, hint icons, labels) are hidden one by one with the element mask
   (`JOBJ_HIDDEN`, the call retail itself uses). The retail 3D (trophy, stand, lights, backdrop) is not hidden.
3. Atlas draws the **chrome** around it: trail, an explainer (name, one rule line, WITH and FROM), a counter, key
   hints, in the Atlas look. The 3D shows through a transparent **window** in an opaque Atlas plate (the `view`
   part). Where the retail camera cannot be re-framed, the window is placed where retail already frames the model.
4. **Readback shims** (scalars, like the existing `Mouse_*` and `Settings_*` shims) tell the adapter what retail is
   showing (trophy index, series counter, cursor cell, coin count). Retail strings (names, descriptions) live in its
   text archives (`SdToy.dat` and the like) in the game's own text encoding; Atlas can use them only if they can be
   decoded to its charset. If not, those retail text objects stay visible (a partial mask) and Atlas draws only the
   frame.
5. Mouse is not supported on a framed screen in version 1 (retail logic reads the pad; nothing is injected). The key
   hints show the pad only.

This corrects one assumption in the brief: the host-side **disc-art decode** (section 12, item 8) is needed only
where Atlas itself places a retail 2D texture (a fighter icon in the Tournament setup, for instance). A framed scene
does not use it, because the retail renderer draws its own assets.

| Screen | Retail scene and code [code] | Assets it loads at run time | Retail logic kept | Rebuilt | Size | What is unknown | Recommendation |
|---|---|---|---|---|---|---|---|
| **Trophy Gallery** | `GS_TOY_GALLERY`, `Toy_Scene_OnEnter` / `OnFrame` (`ty/toy.c:6421, 6568`; `gmscdata.c:141`), 6,842 lines | `TyMnView`, `TyMnBg`, `TyMnInfo`, `TyDatai`, `TyLight`, `TyStand`, one `Ty*.dat` per trophy, text `SdToy.dat` / `SdToyExp.dat` | everything: viewing, stick rotation and zoom, series counter, unlock state from the save | the 2D frame, header, info panel and hints | M | whether the name and description strings can be decoded to the Atlas charset; whether the retail camera can be re-framed into a window; m-ex trophies (ACE) | **Do it first.** It is the smallest scene with clear state and proves the pattern |
| **Collection (the trophy room)** | `GS_TOY_COLLECTION`, `tyDisplay_Scene_OnEnter` / `OnFrame` (`ty/tydisplay.c:1801, 1993`), 2,525 lines | `TyMnDisp`, the per-series `Ty*` archives (`Mycc`, `Map`, `Seri`, `Etc`, `Poke`, `Item` sets) | the room, shelf layout, cursor, camera | trail, counters, explainer for the selected trophy, hints | M | where the cursor's trophy id is readable; the room fills the screen, so a window means a re-framed camera | **Do it** after the Gallery; same shims |
| **Lottery (the dispenser)** | `GS_TOY_LOTTERY`, `tyFigupon_Scene_OnEnter` / `OnFrame` (`ty/tyfigupon.c`), 1,676 lines; `gm/gmtoylottery.c` sets up the card work area | `TyMnFigp`, `SdToy`; the machine and the trophy models | the machine, the pull, the coin balance and save writes, the "GOT IT! A NEW TROPHY!" popup (kept as retail: it shows the real trophy model) | coin count, chance and hints as Atlas chrome | S | the retail text objects for coins and chance (hide only if readable); a past entry fault is fixed, `pc/docs/TROPHIES.md` sections 1-3 | **Do it**, framing the machine and keeping the popup |
| **Movies** | Data > Movies: `mnGallery_80259868` (`mn/mngallery.c:470`), 516 lines, plays `.mth` video through `lbMthp_*` (`:138-221`) | the `Mv*.mth` movies; the video draws in a retail GX pass (448x336 and 640x480 targets) | playback, the unlock flag check, any-pad skip | the **list of unlocked movies** as an Atlas list, with the video window framed | M | how this port plays `.mth` (not traced); the movie titles and unlock flags are not in the code; the video fills the screen | **Do it** as a rebuilt list that calls retail playback; the video stays retail |
| **Staff Roll** | `gmstaffroll.c`, 1,338 lines | `GmStRoll.dat`, `SdStRoll.dat`, effects, audio sync | all of it: a scripted 3D cinematic with its own camera and text | nothing | S (optional) | none needed | **Leave retail.** Give it an entry under More > Credits ("Staff Roll"), and at most a small Atlas corner key hint; the project's own credits are the Atlas Credits screen (step 2) |
| **Tournament** | `GS_TOU_SETUP`, `GS_TOU_BRACKET`, `GS_TOU_ALT` (`gmscdata.c:316-330`), `gmtou_0/1/2.c`, `gmtoulib.c`, about 9,200 lines | `TmBox.dat`, `SdTou` text | the bracket logic and the match flow | the **setup** (selections and settings) as an Atlas list; the bracket and winner-out / loser-out scenes framed | L | the setup's data structures, name tags, how results feed back; I read only the scene table and the archive names | **Last, and only if Tournament is played.** Setup first (M); bracket framed after; otherwise drop |
| **Snapshots** | Data > Snapshots: `mnSnap_80257F24` (`mn/mnsnap.c`), 2,738 lines | the player's own saved photos from the memory card (not disc art), via `lbCardNew_*` tasks | the card I/O state machine and its error states | 4-thumbnail page grid and the delete/copy dialogs as Atlas parts | L | whether the PC port's card emulation holds photos at all; the thumbnails are retail JObj textures, so a frame can only leave them in a window | **Drop unless the owner cares.** Keep retail with an Atlas entry; the cost is high and the feature is rarely used here |
| **Training panel** (in match) | **not found by name** in `src/melee`; `gm_1879.c:437` branches on `GM_TRAINING`; `gmtrainingmode.c` (304 lines) is the CSS and exit only | unknown | unknown | unknown | unknown (L if re-hosted) | where the panel is built; a first task is to locate it by tracing the on-screen panel in a run | **Defer.** Decide after step 7: the LAB's DUMMY and PLAY tabs are the nearest prior art, and an Atlas `pause` screen (6.8) may be the right home |
| **Opening movie** | boot movie (`gmopening*.c`) | `.mth` video | | | | | **Stays as it is.** No menu, pure video; nothing to gain |

**Owner, 2026-10-06, after seeing this table: "Movies, staff roll, snapshots can be skipped".** Those three rows are
OUT of step 10: they stay retail and are reached by a native hand-off from their Atlas entry. The rows are kept above
as a record of what was read. Step 10 is therefore the Trophy Gallery, the Collection room and the Lottery, then the
Tournament and the Training panel if he asks for them.

Order inside step 10 (before that decision; read it without the three skipped screens): Gallery (proves the frame pattern), Collection, Lottery, Movies list, then the optional
Staff Roll hint, then Tournament setup and bracket, with Snapshots and the Training panel only on an explicit
yes. Each is one commit set and one look.
Retired per screen: the retail 2D pieces stay in the disc but are hidden by the mask; once a screen has shipped, its
retail text and hint objects are never drawn. Nothing of the disc is copied; nothing disc-derived is committed.
Verified without the game: the mask and policy tests of 6.8; layout tests of each chrome at three widths with a
sample trophy, movie and tournament dataset; PowerPC syntax checks of every guard. Must be seen (the owner, or an
agent while he is away): each screen entered by its real path on the vanilla disc and on ACE (m-ex trophies), with
the retail 3D unchanged inside the window, the hidden retail pieces gone and nothing else missing, the hints correct,
and the exit back to the Collection or Data hub.

### 13.11 What is harder than it sounds

- **"One component set"** is two codebases today (game-side retargeted C with `FfRole`, host C with `KfRole`); the
  design moves drawing to the host and turns game-side screens into adapters (6.1, 6.7).
- **"Replacing its hard-wired tile"**: the tile is wired to the old `roguelite/main` script, not to Envoy (section 5);
  the Envoy mod has no tile today. Step 2 therefore both adds Envoy's entry and removes roguelite's tile mechanism.
- **"ONE character select"**: about 19 mode files with their own CSS states and data (13.4); the mode profile is new
  design, and each group is its own risk.
- **Title and results** have no frontend hook; the scene policy (6.8) is real work and the title may slip to step 8. The HUD and pause are easier: their draw and call sites are known (6.8).
- **The bespoke retail screens** are 3D scenes drawn by the retail renderer; Atlas can frame and chrome them but not re-draw their models, so "disassemble and reassemble" means framing, with the 2D retail pieces hidden (13.10).
- **The mockup is not the engine's type**: sizes and weights differ (4.3); snapping changes some widths.
- **Disc art** that Atlas itself places (CSS icons, portraits) must be drawn from game memory without being stored (item 8). The framed retail scenes need no decode: the retail renderer draws its own assets at run time.
- **The online lobby** is a netplay-synchronised state machine; keeping it native while changing its look is the safe
  but slow path (13.6).
- **Mod models** are Lua handles, so a native screen cannot show a model cell without a bridge (item 10).

## 14. Out of scope

- New gameplay features or new menus for features that have none (offline Turbo, the CPU controller, stage browser,
  replays, crash-report consent, a profile screen; inventory section 4). Atlas makes adding them cheap; each is its
  own request.
- Per-mod auto-generated settings pages (a mod's own settings are a screen it registers).
- Spectate, replay browser, a mod browser with install and update (`docs/mods-browser.md` is design only).
- A second script or right-to-left layout (kept possible, not designed).
- The in-game console, the F11 fly readout and the LAB's hitbox overlays (developer tools stay as they are).
- Changing netplay protocol or rollback behaviour.
- Actually replacing the retail damage, stock and timer numerals and the retail pause. The capability is in scope and built (6.8); the replacement is the owner's later decision.
- Re-drawing retail 3D models (trophies, staff roll, bracket pieces) as Atlas quads: they stay retail-rendered inside Atlas chrome.
- Porting Envoy's parked screens (delegated decision, step 3).
- Redesigning Envoy's gameplay UI decisions (what is shown is the audit's and the owner's rulings; this spec only
  gives them a system).
- Any new art tool: Atlas art comes from `menu/pipeline` (HTML/CSS/SVG to PNG to GX) as today.

## 15. Open questions for the owner

The first draft's six questions are answered (section 2). What remains:

| # | Question | Recommendation |
|---|---|---|
| 1 | Step 10 has two screens that are expensive and rarely used: **Snapshots** and the **Tournament** bracket. Do you want them re-hosted at all? | No for Snapshots (keep retail with an Atlas entry). For Tournament, only if you play it; do the Gallery, Collection, Lottery and Movies first and decide the rest after you have seen those. |
| 2 | The **Training panel** has not been located in the decompiled source. Is it worth re-hosting, or is the LAB the intended home for that kind of tool? | Defer; decide after step 7. The LAB covers most of what the panel does. |

## 16. Risks

| Risk | Effect | Handling |
|---|---|---|
| Overlay ordering or latency against frontend scenes is worse than the game's own pass | menus lag the pad by a frame or draw under the fade | measure in step 1's look; fallback GX backend over the same quad list (6.1) |
| Host drawing makes native screens adapters | more moving parts per settings page | the adapter mirrors existing tables, so no table is rewritten; tests via a stub adapter |
| Font pages cost more than estimated, or tracking breaks kerning | memory, or caps labels read wrong | measure after step 1's page build; fallback Source Sans caps (12) |
| One-CSS migration breaks a mode's data contract | a mode starts with the wrong fighter or team | mode profiles, group-by-group migration, `CSSData` handed over unchanged, table test per mode |
| Online desync from a screen that masks input | rollback mismatch | online screens are non-modal; no `input_mask` online (existing refusal); step 6 tested with two clients |
| Mod menu entries as an attack or clutter surface | a mod floods Solo or steals focus | caps, parent whitelist, no override, hidden during sessions (8.3, 8.4) |
| Two systems alive for long | double maintenance | each step names what it retires; `MELEE_ATLAS=0` only while both exist |
| Mockup text and counts are samples | real content overflows | lint at registration; snap rule; fit rule |
| Scope creep into features with no menu | the ten steps never end | section 14 |
| A retail element guard hides more than intended, or a hidden element's state stops updating | a missing HUD number or a stuck animation | guards only on render callbacks and JObj flags, never on procs; empty mask by default; a per-bit look before any default changes |
| A framed retail scene cannot be re-framed into a window, or its text cannot be decoded | an ugly or half-themed screen | the plate-without-window and partial-mask fallbacks (13.10); each screen is droppable |
| Step 10 pulls in thousands of lines of retail scene code | the step never ends | per-screen go or no-go, order of 13.10, Snapshots and Tournament only on an explicit yes |
| Tool limits: headless tests prove layout, not looks | an ugly screen ships | every step ends with the owner's look |
| Launcher and game drift apart | two palettes again | one generated tokens file and an agreement test (13.9) |

## 17. Credits owed

Named in the same change that first ships each (the owner's rule), and in the in-game Credits screen from step 2.

| What | Who | Link | Licence | Where |
|---|---|---|---|---|
| Barlow Condensed (fonts in the game and launcher) | Jeremy Tribby | https://github.com/jpt/barlow (files from https://github.com/google/fonts/tree/main/ofl/barlowcondensed) | SIL OFL 1.1 | `CREDITS.md` already lists it for the mockups (line 156); step 1 changes the line to "ships in the game", adds the OFL text beside the font in the package and the launcher's `licenses/` |
| Source Sans 3 | Adobe | https://github.com/adobe-fonts/source-sans | SIL OFL 1.1 | already credited |
| Hasklug (Hasklig with Nerd Fonts patches) | Hasklig (author named from memory: Ian Tuomi, check before publishing), patched by Nerd Fonts (Ryan L. McIntyre and contributors) | https://github.com/ryanoasis/nerd-fonts | SIL OFL 1.1 | already credited; Hasklig's own upstream link to be added: not verified here |
| Playwright and headless Chromium | Microsoft; the Chromium project | https://playwright.dev | Apache 2.0 (Playwright) | already credited (art pipeline) |
| Qt (launcher) | The Qt Company and contributors | https://www.qt.io | as the launcher's `licenses/` states | existing; no change |
| Atlas parts, icons, the drive models | this project | | | nothing traced from Nintendo or HAL work [doc: `ATLAS/README.md`, `menu/CLAUDE.md`] |

No outside design idea beyond the above is used by this spec. If step 1's icon work adopts any existing icon set,
that set is named in that change.

## 18. What I could not verify

- That the host overlay draws correctly in front of a frontend scene's fade and at the same latency as the game's own
  pass (6.1). The inventory says `gd.kit` overlays any scene [doc]; I did not run it.
- That script `on_draw` and the pad hooks run during frontend scenes on the title and menus as well as in a match
  (Envoy's lobby menus imply it; I did not trace the hook sites).
- Whether the overlay sampler wraps UVs (hatch and graticule tiles) and whether font pages decode lazily.
- Whether menus read the pad before or after the Controls remap (key hints, section 9).
- Whether the scene table's function pair can be wrapped for `OVERLAY` and `REPLACE` without touching more than the
  table (6.8), and so whether the title hook is cheap; and how retail detects an unpause (`gw_Ui_RequestUnpause`).
- Whether the retail camera of each trophy scene can be re-framed into a window, whether the retail text archives
  decode to the Atlas charset, and where each scene exposes its selection (item 13). I read the scene tables, archive
  names and pad-polling sites, not the scenes' state.
- Where the Training panel is built (not found by name), how this port plays `.mth` movies, and whether card photos
  exist on PC.
- That percent and stocks are exposed for all four ports to the `gd.player` and `gd.match` readbacks the HUD zone
  would use.
- Whether `fe_menu_sweep.py` and the standalone tests build without the disc images.
- The GX formats of the retail CSS/SSS icons and portraits and the decode cost per frame (item 8).
- All numbers marked [estimate]: quads per screen (counted on the mockup HTML, not on engine output), font memory,
  per-frame submission cost, script cost.
- The widths of the three explainer presets (read off the PNGs at 2x).
- Whether `gd.lab_request`'s menu path and `gd.tbd_request` have consumers other than `geno-lab` and the `roguelite`
  example (I searched the workspace for `tbd_request` and found only `roguelite/main.lua:1250`, plus tests under
  `tools/roguelite/`).
- Nothing in this spec was seen running; every in-game claim in 13.x is a thing to be looked at, not a finding.
