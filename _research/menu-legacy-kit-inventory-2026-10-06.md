# The legacy menu kit: an inventory of every menu and screen (2026-10-06)

Purpose: the factual map for the menu re-unification design conversation. "Legacy menu kit" = everything the port draws or wraps today. This is not a design. Reading only: no game, launcher or build was run; no tracked file changed.

Labels: **[code]** read in source (file:line where useful), **[image]** seen in a picture, **[doc]** stated in a doc or note, **[judgement]** mine. Paths are relative to the workspace; game files are under `melee/`. `GM` = `melee/src/melee/gm/`, `PL` = `melee/pc/platform/`, `E` = `melee/pc/scripts/examples/envoy/scripts/`, `LAB` = `melee/pc/geno/mods/geno-lab/scripts/lab.lua`.

What was NOT verified: nothing was seen running in this session. All in-game pictures are older captures from `_build/audit-20261003/`. I saw no in-game capture of the port's own hub main menu, settings pages, remap screen, online lobby or CSS on a 4:3 window (only generator previews, and one ultrawide CSS capture). I saw no capture of the retail title, results or 1P screens. Those rows rest on code.

---

## 0. One-page summary

1. **There are five separate menu systems, not one kit.** (a) The retail game's own screens (title, 1P modes' select, results, trophies, data, rules, name entry, in-match HUD, pause) are still live. (b) The port's native frontend (`gmfrontend*.c/.inc`, 12.4k lines) replaces the retail list/hub menus, settings, VS character/stage select, online rooms and loading. (c) `gd.kit`, a script-facing re-implementation of the same kit over the ImGui overlay (`PL/gw_kit.c`, 1.6k lines), used by Envoy, the LAB and demos. (d) The Envoy and LAB mods, each with their own screens, built on (c). (e) The Qt launcher, a separate program with its own copy of the style. [code]
2. **The look is one coherent family**: one 0.25 shear, flat colour, hard offset shadows, cobalt faces, gold emphasis, Source Sans 3 (+ Hasklug mono), five section tints (Versus blue, Solo brown, Collection purple, Options grey, Data green). [image: `menu/out_nav/preview/*`, `menu/out_kit/preview/sections_strip.png`]. The consistency breaks at the edges: the Envoy grid screens and HUD, the LAB, and the older Envoy panel use unsheared, dark, thin-framed panels with a different type feel [image: `envoy-join/shots/reward_keys_43.png`, `lab_sheet.png`].
3. **Native-kit screens are data tables**: a row list (`FrontendItem`: action, choice, slider, toggle) is the screen; a new settings page costs one table. Hubs and lists are tables of `FeMenuItem`. Hub art, room screens, CSS/SSS and loading are layout JSON played by a small player (`gmfrontend_player.inc`). [code]
4. **Mods can use only `gd.kit` calls** (text, paragraph, image, icon, panel, button, list, model). They cannot add a native screen, a settings page, a main-menu entry (except the single hard-wired "SUPERTIME ENVOY" tile) or a pause tab. There are no widget calls for toggle, choice, slider or grid in the kit (a grid component exists as a copied Lua file). [code: `docs/scripting.md` "Kit drawing", `_research/menu-kit-pieces.md`]
5. **Most of the game's recent capability has no menu.** Offline Turbo, the CPU controller, stage switching and custom stages, fighters defined in Geno, the Courier, the performance record, crash reporting, the replay/rollback tools and all developer overlays are reached by console command or a script's own screen. Envoy's rule system, keystones and the bag exist only inside the Envoy mod's own screens. [section 4]
6. **Retail screens still show through.** Classic, Adventure, All-Star, Event, Stadium modes, Tournament, Camera, Trophies, Data (snapshots, movies, sound test, messages, records), Rules, Name Entry, Rumble, Display, Language, Erase, the title, results and the whole in-match HUD and pause are retail art in retail style (or a recoloured retail layout). [code, GM/gmfrontend_menus.inc `FA_NATIVE`]
7. **Layout is 640x480 virtual, centred, letterboxed in the native frontend; scripts see a wider canvas via `gd.safe_area()`.** On a 2.25:1 window the native CSS draws its 4:3 content in the centre with empty blue to the sides [image: `batch2-verify/shots/css225.png`]. The kit is authored 2x, so hard text floor is 12 px (caption) at 640x480. [code/doc]
8. **Biggest risks for a rebuild**: netplay (which screens run under rollback), the 50 ms script budget, the 16384-quad list and 512-triangle model limit, "no disc-derived art", "mods on vanilla, one folder each", two translation systems (game is English-only literals; launcher has a string table), and the launcher being a separate Qt program.

Counts at a glance (details in section 6): about 28 native-kit screens, 14 + 3 Envoy menu screens and about 7 Envoy HUD pieces, LAB: 6 pause tabs + 9 modes + about 6 overlays, launcher: 4 tabs, retail screens still reachable: about 25.

---

## 1. The map of every screen and menu a player can reach

### 1.0 Flow tree (launch to gameplay and back)

```
Launcher (Qt)  Play | Mods | Diagnostics | About            [launcher draws]
  -> game exe, boot
       boot / memory-card prompt / opening movie            [retail; port skips card prompt, option to skip intro]
       first-boot onboarding (settings.cfg has no onboarded=1)  [native kit, menus.inc:1169]
       TITLE  ("Press Start")                              [retail gmtitle.c]
         -> MAIN MENU (hub)                                [native kit]
            SUPERTIME ENVOY  (only if the mod is loaded)   [native tile -> Lua mod screens]
            SOLO (hub)
               REGULAR MATCH (hub) -> Classic | Adventure | All-Star   [native hub -> retail modes]
               EVENT MATCH         [retail list screen, run natively in GM_MENU]
               STADIUM (hub) -> Target Test | Home-Run | Multi-Man (list: 6 modes)  [native -> retail]
               TRAINING            [retail mode, kit CSS/SSS, retail training panel]
               LAB (only if geno-lab loaded)  [native tile -> LAB mode: kit CSS/SSS, Lua pause menu]
            VERSUS (hub)
               MELEE  -> MATCH SETUP (native rows) -> kit CSS -> kit SSS -> LOADING -> match -> retail results -> back to CSS
               ONLINE -> online rows -> code entry | waiting room | lobby (strikes/bans) -> kit CSS -> LOADING -> match
               TOURNAMENT          [retail]
               SPECIAL MELEE (list: 10 modes, use VS machinery -> kit CSS/SSS)
               RULES               [retail list screen]
               NAME ENTRY          [retail]
            COLLECTION (hub) -> Gallery | Lottery | Collection (trophies)  [retail]
            SETTINGS (list)
               VIDEO, AUDIO, CONTROLS (+ remap editor), ONLINE, MODS, GAMEPLAY  [native pages]
               RUMBLE, SCREEN DISPLAY, LANGUAGE, ERASE DATA                    [retail]
            DATA (hub) -> Snapshots | Movies | Sound Test | Special Messages [retail]; Records (list) -> VS | Bonus | Misc [retail]
match: retail HUD + retail pause (+ mod HUD through gd.kit, LAB overlays, Envoy strip)
results: retail (gmresult.c)  -> CSS (VS) or back to a menu
```

### 1.1 Port native frontend screens (drawn by the port's kit; `GM` = game side)

All: pad, keyboard (hotkeys only), mouse (point, click, right click = B, wheel) [code: `gmfrontend_mouse.inc`]. All footer hints are mouse buttons. Offline unless stated. Each screen is a `GS_FRONTEND` scene in its own mode, routed by `gmFrontend_Route` [code: `gmfrontend.c` top comment].

| Screen (on-screen name) | Where | In / out | Online? | State |
|---|---|---|---|---|
| MAIN MENU hub: SUPERTIME ENVOY, SOLO, VERSUS, COLLECTION, SETTINGS, DATA | `gmfrontend_menus.inc:69` | from title; B = title | n/a | finished. Envoy tile hidden unless `Script_TbdAvailable`; its action `FA_TBD` calls `Script_TbdRequest` (menus.inc:1222). Its icon is `ico_adventure`, reused from Adventure |
| SOLO hub: Regular Match, Event Match, Stadium, Training, LAB | menus.inc:83 | B = main | n/a | finished; LAB tile only if geno-lab loaded |
| REGULAR MATCH hub | menus.inc:96 | | n/a | finished |
| STADIUM hub | menus.inc:105 | | n/a | finished |
| MULTI-MAN MELEE list (6) | menus.inc:114 | | n/a | finished, no icons |
| VERSUS hub: Melee, Online, Tournament, Special Melee, Rules, Name Entry | menus.inc:129 | | n/a | finished. ONLINE is not a vanilla slot (`SEL_VS_ONLINE 0x40`) |
| SPECIAL MELEE list (10) | menus.inc:142 | | n/a | finished |
| COLLECTION hub (3) | menus.inc:163 | | n/a | finished |
| SETTINGS list (10: 6 port pages + 4 retail) | menus.inc:172 | | n/a | finished; mixes port and retail destinations |
| DATA hub (5) / RECORDS list (3) | menus.inc:186 / 198 | | n/a | menus finished; destinations retail |
| MATCH SETUP (VS. MELEE rules rows, about 9) | `gmfrontend.c:223` | VS > Melee; A continues to CSS | offline only (online uses room rules) | finished, rows only |
| ONLINE PLAY rows: Host, Join, Random Opponent (soon), Stage List, Turbo, Envoy, Stocks, Time Limit, Input Delay | `gmfrontend.c:605` | VS > Online | is online | finished except "Random Opponent": **placeholder** (`fe_ol_random`, "coming soon" per the comment at gmfrontend.c:~565) |
| JOIN ROOM (code entry) | `gmfrontend_online.inc` (FL_CODE) | Join; type, paste or d-pad | is online | finished [image: `out_lobby/preview/code_*`] |
| WAITING ROOM (host / guest) | same (FL_WAIT) | | is online | finished [image: `waiting_host_1x.png`] |
| LOBBY (strikes, bans, picks, ready, countdown, coin flip) | same (FL_LOBBY) | | is online | finished [image: `lobby_g1_strike_1x.png`, `lobby_countdown_1x.png`] |
| CHARACTERS (kit CSS) | `gmfrontend_select.inc` (FL_CSS) | VS, Training, LAB, lobby | offline and in lobby | finished; `MELEE_NATIVE_CSS=1` keeps retail one [image: `css225.png`] |
| STAGES (kit SSS) | same (FL_SSS) | | same | finished |
| LOADING ("GET READY": who fights where, warm-up bar) | `gmfrontend.c:624`, `loading.py` | before every VS match; after the online countdown | both | finished [image: `loading_four_1x.png`] |
| SETTINGS > VIDEO (5 rows) | `settings.inc:189` | | n/a | finished |
| SETTINGS > AUDIO (3) | `settings.inc:222` | | n/a | finished |
| SETTINGS > CONTROLS (12) + remap editor + how-to | `settings.inc:348`, `controls.inc` | | n/a | finished; remap has Swap/Also, profiles, presets, tester |
| SETTINGS > ONLINE (6: name, server, delay, stage list, Turbo, Envoy) | `settings.inc:420` | | n/a | finished |
| SETTINGS > MODS (turn mods on/off, one row each) | `settings.inc:437` | | n/a | functional; applies at next start; no install, no detail beyond the help line (up to 512 chars) |
| SETTINGS > GAMEPLAY (10: unlock everything, default rules) | `settings.inc:548` | | n/a | finished |
| First-boot onboarding | menus.inc:1169 | once per profile | n/a | finished (not seen) |
| Dialog and toast | `dialog_layout.json`, kit_motion | any | n/a | finished [image: `list_dialog_1x.png`] |

Not found as a screen: the mod browser. Install, remote sources and updates are not built in Qt either; `docs/mods-browser.md` describes the legacy C# flow only [doc].

### 1.2 Retail screens still reachable (drawn by the game's own code and art)

Not seen as pictures. All pad only (no mouse through the kit; the mouse hook is the frontend's) [code: mouse.inc says "every frontend screen"; retail screens are not frontend screens].

| Screen | Entered from | File | Replaced or wrapped by the port? | State |
|---|---|---|---|---|
| Boot, opening movie, memory-card prompt | start | `gmboot.c`, `gmopening*.c`, `gmscmemcard.c` | port auto-creates card and can skip | retail untouched, port skips |
| Title | boot | `gmtitle.c` (TARGET_PC edits at :281) | not replaced; art brief section 6 asked for a wordmark and prompt, **not built** | retail untouched |
| Event Match list and detail | Solo > Event | `gmevent.c` | frontend leaves for `GM_MENU` natively (`FA_NATIVE`); the kit preview `out_nav/preview/event_match_1x.png` exists as art only | retail; kit art exists but is not wired [judgement] |
| Rules list, More Rules, Item Switch, Random Stage Switch | Versus > Rules | `mn*.c`, `gm_*` | `FA_NATIVE`; kit art exists (`list_rules`, `list_more_rules`, `grid_items`, `grid_stages` previews) | retail; art unwired |
| Name Entry | Versus > Name Entry | | native | retail |
| Rumble, Screen Display, Language, Erase Data | Settings | | native | retail |
| Snapshots, Movies, Sound Test, Special Messages | Data | | native | retail; kit `sound_test` art exists, unwired |
| VS / Bonus / Misc Records | Data > Records | | native | retail; `table_records` art exists, unwired |
| Trophy Gallery, Lottery, Collection | Collection | | native `GM_TOY_*` | retail |
| Classic, Adventure, All-Star: CSS, intermission screens, bonus screens | Solo | `gmclassic.c`, `gmadventure.c`, `gmallstar.c` | CSS is the retail CSS (only VS, Training, LAB call `gmFrontend_SelectScene`/`TrainingSelect`/`ModeSelect` [code: grep]) | retail |
| Target Test, Home-Run, Multi-Man | Stadium | | native | retail |
| Tournament bracket, Camera Mode | Versus | | native | retail |
| Training panel (in-match controls) | Training | `gmtrainingmode.c` | CSS/SSS replaced, panel retail | retail |
| In-match HUD (damage, stocks, timer, "GO!", "GAME!"), pause screen | any match | | not replaced; scripts draw over it | retail |
| Results ("Special Bonus", placement) | match end | `gmresult*.c` | not replaced; brief section 5 asked for it, not built | retail |
| Game Over, Staff Roll | | | | retail |
| Debug menu | | | not found as reachable; unverified | unknown [judgement] |

### 1.3 Script-drawn screens: Envoy (mod `melee/pc/scripts/examples/envoy`, about 11.0k Lua lines in 63 files)

Pad only ("Controller only" [doc: `MENUS.md`]). A keyboard shows a "Connect a controller" panel [image: `envoy-join/shots/reward_keys_169_a.png`]. Offline (Envoy online has a separate reward box, see 3.4). `menu.lua` states: title, profile, hub, setup, fighter, companion, records, interlude, results, reward, pause, confirm, quit, playing (14) [code: grep of `menu.lua`].

| Screen | Contents | How in | State |
|---|---|---|---|
| Title / Profile | "Enter Envoy", "Close Envoy"; "Continue profile" | main-menu tile, or `envoy` console command | parked mission flow, **superseded** by retail flow [doc: MENUS.md "Parked mission contract"] |
| Hub (garden) | walkable level, stations at x=-180 Run exit, -90 Fighter, 0 Companion, 90 Records, 180 Nest (closed) | | functional; the walkable garden only appears when its model resolves |
| Setup, Fighter, Companion, Records | lists and stat bars | stations | functional rough; companion and records are the older pet-growth design |
| Playing / pause / confirm / quit | START opens pause; Resume, Companion, Abandon | | functional |
| Interlude, Results | gains, next theme; before/after grades | | functional; older design |
| **Reward screen** (grid: TAKE ONE, KEYSTONE: ONE, EQUIPPED n/6, BAG n/4, KEYSTONES n/allowed + one detail panel + A/X/Y/B bar + 45 s countdown) | `E/run_screen.lua` (485 lines) on the grid component | after a cleared stage | current design [image: `reward_keys_43.png`, `_169_a.png`] |
| **Bag screen** (YOUR DRIVES) | same grid, Z+START in a fight pauses | | current [image: `bag_43.png`, `bag_full_43.png`] |
| **Swap** ("BAG FULL", GIVE UP WHICH?) | same grid | when a drive has nowhere to go | current [image: `swap_169_a.png`] |
| Build strip (HUD) | one pip per slot + keystone cells | rule-host run | current [image: `strip_169_a.png`, top-left] |
| Announcement panel, opponent card, pickup note, "Collect the drives" banner, drive arrow, synergy pill, co-op strips | `E/run_hud.lua` (168), `run_host.lua` (1115) | | current; partly slated for removal [doc: gameplay UI audit] |
| Older "SuperTime Envoy" companion panel, tag panel, labels | `E/hud.lua`, `retail_app.lua:309-329` | rules-off route | **duplicate** of the strip [doc: audit #24, #25] |
| Modifier LAB text box, Drive LAB card | `mod_display.lua`, `drive_lab.lua` | dev route | developer UI, visible in a capture [image: `strip_169_a.png`, the dark text box under the strip] |
| Online reward box | `mod_lab.lua:754` | netplay between stages | **placeholder**, plain debug-font box [doc: audit #23] |

### 1.4 Script-drawn screens: the LAB (mod `melee/pc/geno/mods/geno-lab`, `lab.lua` 5,290 lines, 84 ui files)

Pad, keyboard hotkeys (letters, TAB, F3, digits). Offline only (it forks the rewind timeline) [code: `CLAUDE.md` of the mod].

| Piece | Contents | State |
|---|---|---|
| Mode strip (bottom-left chip, key strip) | 9 modes found: CLEAN, HITBOXES, FRAMES, STAGE, INSPECT, MOVES, LAUNCH, TRAINING, COMBO; each owns toggles with a key, icon and description | finished. CLEAN shows just a tiny corner chip [image: `frozen-k/shots/cast_blast.png`, bottom-left bracket icon] |
| Pause menu | tabs PLAY, DISPLAY, DUMMY, STATES, TOOLS, EXIT; rows with icon, value, adjust, detail panel, controls strip | finished [image: `lab_sheet.png` item 9] |
| Info panel, hitbox data, move timeline, states library, frame data export | | finished |
| Own art | 83 icons `ico_lab_*`, `lab_frame_*`, chips, stripes, in its own cyan/ink palette | separate palette from the kit (`lab_palette.py`) [image: `lab_sheet.png`] |

### 1.5 Other script-drawn UI (examples, demos)

`demos/grid-inventory` (the grid component, 4/5/6 layouts), `demos/screen-models` (12 original models in a 4x3 cell grid), `kit_hud` (a kit panel over a match), `callouts` (`gd.comm`, Corneria-style window), `training-card`, `map_editor` (help via `paragraph`), `pickup-juice`, `profiler`. About 88 demo folders exist; only the above draw screens [code: directory listing and READMEs].

### 1.6 Engine-drawn overlays

| Overlay | File | How in |
|---|---|---|
| In-game console (backtick) | `PL/gw_console.cpp` (825) | key `` ` `` |
| Debug fly readout (FLY P1 x y speed) | `gw_console.cpp:538`, `gw_script.c` | F11 or `fly` |
| FPS/timing readouts, loading overlay ("##gw_loading") | `PL/gw_overlay.cpp` (557), `gw_profiler*.c` | Settings > Video "FPS readout" / script |
| Hitbox draws, frame step | LAB, engine | LAB |

### 1.7 The launcher (Qt, `tools/release/launcher/qt/`, about 2.7k lines C++; C# reference 2.6k lines)

Own program, own copy of the kit (`kit.cpp`: palette tokens, `Surface`, `Button`, icons from `kit.qrc`). Tabs: **Play** (Disc library, Add Disc, Manage, "Unlock everything", "Skip intro", "Close launcher on play", volume, PLAY), **Mods** (local list, enable/disable, `.removed` recovery; no install), **Diagnostics** (log toggles, render and controller diagnostics, categories and traces), **About**. [code: `window.cpp:78,189,352,372,425`; image: `_build/launcher-smoke-shots/launcher-0.png`, `-2.png`]. Mouse and keyboard; no pad. Strings go through `Lang`/string table [code: `Lang.cs`, `check_strings.py`; the Qt copy was not read]. Windows build; the Qt launcher is described as portable [doc].

---

## 2. The legacy kit as a system

### 2.1 Components

| Component | What | Defined | Used by | Known problems |
|---|---|---|---|---|
| Canvas | 640x480 virtual units, y down; native frontend centres and letterboxes it; script canvas widens (`gd.safe_area()` `{w follows aspect, h=480}`) | `gw_kit.h`, scripting.md:711 | all | native screens do not use the wide canvas [image: `css225.png`] |
| Text roles | caption 12, body 14, row 16, label 20, title 24, heading 32, hero 44, display 56 (Source Sans 3 bold/black), tag 20, code 16 (Hasklug mono). Fit rule: step down one role, then truncate with ellipsis. Hero/display are caps only. Charset: ASCII plus a few symbols; English only | `menu/out_kit/font/font_manifest.json` | all | no second script (the retail screens still have Japanese); sizes are 1x pixels, so 12 px caption at 480p |
| Palette | ink, bone, muted, disabled, gold, gold_lt, gold_dk, danger, ok; 5 sections with face/bg/band/face_hi; p1..p4, cpu | `kit.json` | all | the LAB and the Envoy grid add their own palettes (`gd` mod palette, `colours` table in `drive_menu.lua`) |
| Section backdrop | tinted background with diagonal bands | `kit.json` bands, `chrome_layout.json` | native | mods get colours, not the backdrop |
| Chrome | header slab, breadcrumb with section icon, description strip, footer hints | `chrome_layout.json` | native | script screens re-draw their own title row |
| Hub | hero tile plus stepped secondaries; one shear; hard-shadow lift on select | `hub*.py`, `nav.py`, `hub_layout.json` | native | bouba (rounded) hub exists as a rejected alternative [image: `out_hub_bouba`] |
| List row, scroll bar, value widgets (toggle, choice, slider, stepper) | `list_layout.json`, `widgets_layout.json` | native | **no script equivalents** except `gd.kit.list`/`button` (label and value only) |
| Grid, table, event list+detail | `grid_layout.json`, `table_layout.json`, `event_layout.json` | art for retail screens; **not wired** (retail screens still draw) | |
| Panels | 9-slice `frame_*` (6 pieces), plus `lab_frame_*` | `build.py` | native, `gd.kit.panel` | the kit's own README says new frame pieces were wanted (2026-09-27) |
| Key chips / glyphs | `glyph_a b x y z l r start stick cstick dpad`, LAB's `lab_key_*` | `glyphs.py` | native, scripts | scripts have no chip call; LAB composes its own (`key_chip`) |
| Icons | `ico_*`: about 29 nav icons, 12 kit icons in scripting docs, 83 LAB icons | `icons.py`, `lab_art.py` | | main-menu Envoy tile reuses `ico_adventure` |
| Cursor | hand sprite; per-port variants planned | `cursor_layout.json` | CSS | |
| Model cells | `gd.kit.model` (script model into a rect; ortho camera, fixed light, painter sort, 512 tris) | `gw_kit.c` | Envoy grid (optional), demos | no native-side use; see limits |
| Dialog / toast | `dialog_layout.json` | native only | | not callable from scripts (proposed `gd.kit.toast`) |
| Motion | `kit_motion.json`, `hub_motion.json` etc: joint list, keyframes, `from_current` keys | `gmfrontend_player.inc` | native | scripts animate by hand |
| Sound | game's own menu sfx (`sfxForward/Back/Move`) | `gmfrontend.c` | native | no sound call in `gd.kit` |

### 2.2 Layout model

Everything is authored in 640x480; title-safe `[32, 24, 608, 456]` [doc: ART-BRIEF]. The native frontend renders HD at any window size but centred 4:3 (the player adds the kit canvas's left edge for the mouse) [code: mouse.inc]. Scripts use `gd.safe_area()`. The grid component composes at most 760 wide and computes a cell size of 56..24 px, with `fit = false` below 24 [doc: grid-inventory README]. Textures: 2x authoring, drawn at 1x size, power of two, at most 1024, GX formats (I4 mask, CI8, RGB5A3, RGBA8) [doc: menu README].

### 2.3 Art pipeline (`menu/pipeline/`, 13.1k Python lines)

HTML/CSS/SVG rendered by headless Chromium, PNG to GX via `melee/pc/tools/png2gx.py`, layout and motion JSON beside each set, previews composed from the JSON alone. Generated, none hand-painted or traced; provenance rule: nothing from Melee. [doc: menu CLAUDE.md]

| Set | PNGs | What |
|---|---|---|
| `out` | 53 | original placeholder bring-up (button, frame) |
| `out_kit` | 66 | the kit: fonts, palette, widgets, glyphs, chrome (read by the game as `ui/`; `_build/ui` has 151 files) |
| `out_hub`, `out_hub_bouba` | 36, 35 | hub prototypes (rectangular chosen, rounded rejected) |
| `out_nav` | 106 | hubs, lists, tables, grids, event, sound test; 29 icons |
| `out_lobby`, `out_online`, `out_loading` | 59, 43, 8 | online room screens and loading |
| `out_roguelite`, `out_roguelite_expansion` | 25, 93 | **art studies by another agent** (Astra; marked "illustrative", "native integration pending", [image: `out_roguelite/preview/build.png`, `out_roguelite_expansion/preview/01-combat.png`]). Under the owner's "don't trust Sol/Astra" note these are unverified |
| `out_brand` | 58 | logos, key art, badges, social |
| `out_readme`, `docs/readme` | 18, ~30 | README art |
| `out_effects_study`, `out_discord_*` | 17, 27, 17 | effects and Discord |
| `concepts/` | 0 PNGs | `menu-genres.html` only |

### 2.4 Input model

| Input | Native frontend | Script `gd.kit` screens | Launcher |
|---|---|---|---|
| Pad | any of 4 ports; vanilla's own order, wraps; hub left/right [doc: frontend-menus.md] | script reads pad (`menu_input.lua` reads the physical pre-mask pad; `gd.input_mask`, `gd.input_chord` hide D-pad/START from the game; refused online) | none |
| Mouse | point = move cursor, click = A, right = B, wheel scrolls, footer hints clickable; local UI only, never reaches pads or netplay [code: mouse.inc] | script reads mouse itself if at all (Envoy: "Controller only") | full |
| Keyboard | hotkeys only (keyboard is not a pad) | LAB uses letter keys; Envoy shows "keyboard is for hotkeys only" | full |
| Focus | one cursor per screen; CSS has one token per port | per-script; the grid component: nearest cell in direction | Qt focus |
| Remap | Settings > Controls editor, profiles, presets | none | none |
| Multiple players | CSS and lobby; menus follow "the port that pressed A" (`gm_801677E8`) | co-op Envoy uses `extra` latches per port | n/a |

### 2.5 Limits

| Limit | Value | Source |
|---|---|---|
| Quads per frame in the script kit list | 16,384 (`KQ_MAX`); the "40/512 quads" log text belongs to the older game-side player and was not found in the code I searched | `gw_kit.c:1155` |
| Triangles per `gd.kit.model` | 512; 64 distinct atlases; scissored to the rect | scripting.md |
| Script budget | 50 ms or the instruction cap (`MELEE_SCRIPT_BUDGET`, `MELEE_SCRIPT_MS`) per tick | scripting.md:217 |
| Main-chunk locals | 200 in `lab.lua`; new work goes in nested scopes | LAB CLAUDE.md |
| Text | no per-frame measuring loops; measure and wrap are cached (`wrap`), `gd.kit.paragraph` exists since 2026-09-28 | LAB CLAUDE.md |
| Grid cost | about 0.3-0.4 ms of script time per draw (1024x576) | grid README |
| Texture sets | one atlas texture per font role; each texture lookup searches mod `ui/` first | gw_kit.h |
| Mod art | `.gxtex` made by `png2gx.py` in `mods/<id>/ui/`; manifest `*_ui.json` | scripting.md |

### 2.6 Native versus script

| | Native frontend (`gmfrontend*`) | `gd.kit` |
|---|---|---|
| Runs | only in frontend scenes, through the game's text canvas and GX link callbacks (draws via aurora) | any scene, through the ImGui overlay pass, after the game |
| Reads game state | yes (rules, roster, netplay) | no ("drawing only"), so offline and online |
| Atlas text | same font manifest and fit rule | same |
| Adds screens | by editing C | cannot add a native screen or main-menu item |
| Hit tests | player's evaluated quads | the script's own rectangles |
| Order with game UI | below the retail HUD in the pass order | always above the world and the retail HUD |

What a mod author gets today: text/paragraph/measure/metrics, image, icon, panel, button, list, model, colour tokens, own textures and palette, `gd.safe_area()`, `gd.comm`, plus plain `gd.fill/box/line/text`. No: toggle/choice/slider/tabs/grid/dialog/toast/scroll calls (the grid exists as Lua copied into each mod by `embed.py`), no sound call besides `gd.play_sound`, no focus manager, no animation helpers. [code/doc]

---

## 3. Inconsistencies and pain (with evidence)

### 3.1 Same problem, different answers

| Problem | Answer A | Answer B (and C) | Evidence |
|---|---|---|---|
| Envoy build display in a match | the build strip (slots + keystones), `run_hud.lua` | the older companion stat panel (Power/Speed/Guard/Jump bars) top-right, `hud.lua`; plus the Modifier LAB text box | audit #1, #24 [doc]; the dark text box is visible under the strip [image: `strip_169_a.png`] |
| Character select | native kit CSS (VS, Training, LAB, lobby) | retail CSS (Classic, Adventure, All-Star, Tournament, Camera, Multi-Man, Stadium) | `gmFrontend_SelectScene` callers [code: grep] |
| Settings | native kit pages (Video, Audio, Controls, Online, Mods, Gameplay) | retail Options screens (Rumble, Display, Language, Erase) inside the same SETTINGS list | menus.inc:172 |
| Rules | native MATCH SETUP rows (one screen) | retail Rules / More Rules / Item Switch (still retail); the kit art for them was made and not wired | menus.inc:129, [image: `out_nav/preview/list_rules_1x.png`] |
| Showing a list | native rows with widgets (`FrontendItem`) | `gd.kit.list` (label+value), LAB rows (icon, value, adjust), Envoy grid cells and wrapped detail text, launcher Qt lists | sections 1.1, 1.3, 1.4, 1.7 |
| Loot/inventory | Envoy grid | Envoy rows list in the older bag (`drive_menu.lua` own text wrap) | `drive_menu.lua:1-30` [code] |
| Palette / fonts | kit palette, Source Sans 3 | LAB palette (cyan accent `#38c9d9`, ink glass) [image: `lab_sheet.png` item 6]; Envoy rarity colours hard-coded (`colours={common=0xD7D4CFFF,...}`); launcher copy | `drive_menu.lua:6` |
| Reward moment | kit-ish grid with countdown (offline) | plain debug box (online) | audit #23 |
| Panel frame | kit 9-slice (`frame_*`) | LAB `lab_frame_*`; Envoy grid draws its own thin border frames with corner notches | [image: `reward_keys_43.png`] |
| Header | slab + breadcrumb (native) | italic title with underline rule only (Envoy) | [image: `hub_main_1x.png` vs `reward_keys_43.png`] |
| Hubs | rectangular hub shipped | bouba hub prototype kept in repo | `out_hub_bouba` |
| Button glyphs | kit glyph set (A green, B red) | grey circle glyphs in Envoy's bar; retail glyphs on retail screens | [image: `reward_keys_43.png` bottom bar] |

### 3.2 Retail showing through [judgement + code]

Every `FA_NATIVE` row (Event, Rules, Name Entry, Rumble, Display, Language, Erase, Snapshots, Movies, Sound Test, Messages, 3 Records) leaves the port's style the moment A is pressed. Title, results, trophies and the in-match HUD never entered it. The owner's brief asked for a new title and results (art brief sections 5, 6); neither was built. In the Envoy captures the retail "CP" tag, stock icons and damage numbers sit under kit panels [image: `bag_43.png`].

### 3.3 Overwhelm and roughness (cited)

| Source | Finding |
|---|---|
| Owner, quoted in `envoy-readability-pass1` | "too much visual stuff happening all at once, and its hard to correlate whats what"; wants "bite sized rules ... understand mostly at a glance" |
| `envoy-gameplay-ui-audit-2026-10-05.md` | the loudest items are the gold text under the bar, 6 s top-centre announcement panels that queue, the wide opponent panel, a duplicate older HUD, error toasts titled "Technique", the build bar drawn over the retail results screen, a plain debug-font reward box online |
| `envoy-readability-pass1` | 86 pieces; a ceiling build is 22 rule lines, 509 words; 3 toasts queued in one frame; 18 s of announcements |
| `envoy-visual-identity-2026-10-05.md` | owner wants distinct visual identities (halos, orbiters) for pieces; the drive models are "10/10 S+, charming and adorable"; menus were "looked at in captures" only |
| My reading of the reward screen [image] | the bag screen shows at once: three title rows, a block of up to 6+4+6 small cells, a dense detail paragraph (four to five sentence fragments), and an action bar. Rarity is a corner pip plus border colour; family is the fill colour. Drive models are tiny (about 12 px figures on a 40 px cell) |
| Hand-written Lua | Envoy menu files are compressed single-line style (`menu.lua`, `drive_menu.lua`), costly to read and change [code] |

### 3.4 Dead, duplicate, parked code [code unless noted]

- Envoy's mission/garden/companion flow (`hub.lua`, `companion.lua`, `menu*.lua` screens title/profile/hub/setup/fighter/companion/records) is "parked" by the 2026-10-04 retail contract but still wired [doc: MENUS.md].
- Two bag UIs (`drive_menu.lua`, older, versus `run_screen.lua` on the grid).
- `out_hub_bouba`, `out_roguelite*` (studies), `out/` placeholder set.
- Nav art for Event, Rules, More Rules, Item/Stage Switch, Records, Sound Test, Multi-Man icons: generated and checked, not consumed by the game (the screens are retail) [judgement from `FA_NATIVE`].
- `FA_TBD` item named "TBD" in code, shown as "SUPERTIME ENVOY"; art studies carry the old "TBD" name [image: `out_roguelite/preview/build.png`].
- "Random Opponent (soon)" row.
- `gmFrontend_ModeSelect` is used only by the LAB.
- The older C# launcher (kept as reference).

### 3.5 Strings

Game side: English literals in tables ("Strings the player sees are plain English in the tables; the launcher, not the game, is translated" [doc: GM CLAUDE.md]). Retail screens still use the disc's language. The launcher has a string table keyed by exact English text (`Lang.cs`, `check_strings.py`, root CLAUDE.md). The art brief asked for zero baked-text textures and English plus later a second script; the atlas is Latin only [doc].

### 3.6 Accessibility and legibility

- Text floor 12 px (caption) and 14 px body at 640x480; at 480p windowed that is the whole screen's height [code]. Retail-style small labels remain on retail screens.
- Colour-only signals: Envoy cell family (fill) and rarity (border/notches) [image]; port colours checked for deuteranopia/protanopia in the kit (`kit_cvd_swatches.png`) and the LAB palette [image: `lab_sheet.png` item 6]; Envoy statuses use colour afterimages [doc: visual identity note].
- Pad-only Envoy; no mouse; keyboard says "hotkeys only".
- Reduced motion: only the Astra study has a toggle [image: `01-combat.png` control "Reduced motion & flashes"]; the native frontend has none that I found.
- Focus visibility is a gold lift in native lists; in the Envoy grid a gold frame on a dark cell (seen as visible but small in the bag capture).

### 3.7 Non-4:3

Native screens are 4:3 centred; the 2.25:1 CSS capture shows roster and panels clustered in the centre with plain side area [image: `css225.png`] (a hand-set 3240x1440 capture). The kit docs say the wide-canvas/safe-area change for the native side was "tracked separately" (`_research/menu-kit-pieces.md`). Envoy screens are safe-area aware (640, 853, 1140 [doc: MENUS.md], seen at 4:3 and 16:9 [image: `reward_keys_43.png`, `_169_a.png`]); in the 16:9 capture the panel is not centred and the dim backdrop does not cover the whole canvas edge.

---

## 4. What exists in the game now and has no proper menu

| Feature | Where a player reaches it now [code/doc] | What a menu would need to show |
|---|---|---|
| Envoy run, setup (fighter, difficulty, stocks, type Classic/Adventure) | main-menu tile -> script screens (title/profile/hub/setup); older flow; console `envoy ...` for the rule-host (`envoy rules on`, `envoy classic`) | a run start with the retail setup, profile/records, mode choice; the rule-host path is console-only [audit finding 3] |
| Rule system, split pieces, keystones | only inside reward/bag screens as grid cells | per-piece one-line rule, family/rarity, price list, what merges; budget of the pool (86 now, 72 proposed) |
| Press-A pickup, payout | in-world prompts; no menu | rules the player can read; floor items; "collect the drives" hold |
| Co-op and online Envoy | `envoy coop ...` console; online Envoy toggle in Settings>Online and room rows; reward box debug-styled | two-player reward flow, ready state, sets |
| Turbo | Online rows and Settings>Online toggle for rooms; **offline Turbo has no menu** (`turbo-combo` demo, `MELEE_TURBO`, test flags) | a rules toggle in Match Setup, lobby indicator, netplay-safe note |
| CPU controller / levels | CSS slot HMN/CPU/level; scripted `gd.cpu_mode` has no UI | LAB dummy tab covers some (DUMMY tab) |
| Geno fighters, native defines, roster extras | appear on the CSS as fighters; no list of what is Geno/m-ex; no per-fighter info | origin badge, move list, costume count, credits |
| The Courier / vanilla-* mods | mods; appear in roster if enabled | same |
| Stage switching, custom stages, large maps | script API (`stage_switch_demo`, `stage_tour`), not a menu; Settings has "stage list" for online only | stage browser, page tabs, previews, credit; stage options per mode |
| Mods on/off | Launcher Mods tab (list), Settings>Mods (rows) | two lists with two behaviours; install, update, conflicts, requirements, per-mod settings, kind badges (`docs/mods-browser.md` is design only) |
| Performance record, profiler | `profiler` demo, console, Settings>Video FPS | a perf page, 120 fps budget readout |
| Netplay protocol / room options | rows for Stage List, Turbo, Envoy, Stocks, Time, Delay | ping history, rematch, spectate (not found), replay browser |
| Replays, rollback tools | `gw_replay.c`, console, LAB rollback visualiser | replay list, share |
| Crash reporting | uploads to the netplay server (per memory note: TCP crash uploads) | consent, last-crash notice (not found as UI) |
| Developer overlays | console, F11 fly, LAB modes, Envoy `devui`, `uxdump` | a single "developer" switch with a visible indicator |
| Records / tag / player profile | retail records only; native name/tag in Settings>Online (name) and retail Name Entry | one profile screen (name, tags, controller profile, records, Envoy profile) |
| Language | retail Language row | multi-language kit |

---

## 5. Constraints a new system must respect

| Area | Constraint | Source |
|---|---|---|
| What can be drawn | 2D quads (flat, textured, 9-slice, parallelograms), atlas text, tint masks, vertex colour (script models), `gd.kit.model` (512 tris, orthographic, fixed light, no custom materials, painter sort); no per-quad shaders; post passes (32, each full-screen) and custom materials exist for world/fighters, not for menu quads; no video seen in the kit | gw_kit.h, scripting.md, `docs/shaders.md` [doc, not re-read here] |
| Motion | the native player plays JSON joint animations; scripts have none | frontend-menus.md |
| Budgets | 16,384 quads; 50 ms scripts; texture memory 1 MB per screen at 2x (brief); hubs built from 13 masks at 138 KB | code/doc |
| Determinism | `gd.kit` draws are presentation only (not hashed, nothing to restore) and allowed online; `gd.input_mask/chord`, `fx_*`, `model_*` instances, `comm` refuse under netplay/rollback; mouse input never enters the input stream; LAB offline only; online lobby and rooms are native, synchronised through the netplay layer | scripting.md, mouse.inc, visual-identity note |
| Netplay screens | lobby, strikes, bans, ready, countdown, coin must stay synchronised by the existing protocol (protocol number 3 in NEXT-SESSION) | online.inc header |
| Mods | one folder each, run on the vanilla disc; mod art in `ui/`; a script has no way to register a menu entry | memory notes, mods-packaging |
| Disc art | none may be committed; frame the disc's icons (64x56 CSS and SSS icons, 136x188 portraits) with generated frames; names are strings | ART-BRIEF, root CLAUDE.md |
| Credits | every outside tool/asset named with link in the same change (fonts: Source Sans 3 and Hasklug, SIL OFL) | memory note, menu CLAUDE.md |
| Launcher | separate Qt program with its own kit copy and string table; Windows build, portable; no pad | tools/release |
| Linux | game has `gc_adapter_linux.inc` and a Linux package guard; menus untested off Windows by agents | root CLAUDE.md |
| Coexistence | possible by design: the frontend routes screen by screen (`gmFrontend_Route`, `FA_NATIVE` hand-off to retail and back) and `gd.kit` overlays any scene; screens can be swapped one `MenuKind` at a time; the toggle `MELEE_FRONTEND_MENUS` and `MELEE_NATIVE_CSS` are fallback switches | gmfrontend.c |
| Tests | `fe_menu_sweep.py` walks every item; `gw_kit_tests`; `lab_stage_d_check.lua`; `grid_inventory.lua`; launcher `check_strings.py` | docs |

---

## 6. Sizing

| Area | Files | Lines |
|---|---|---|
| Native frontend (`GM/gmfrontend*`) | 12 | 12,411 (online 2,531; menus 1,491; player 1,919; select 1,522; kit 844; kitlist 633; settings 600) |
| Script kit native (`PL/gw_kit.*`, `gw_uigen.*`) | 4 | 2,595 |
| Console and overlay | 2 | 1,382 |
| Envoy mod Lua | 63 | about 11,036 (menu-related: `run_screen` 485, `run_hud` 168, `hud` ~100, `menu*` ~300, `drive_menu` 96, `retail_app` 379, `app` 336, `hub` ~150) |
| LAB | 1 + 84 ui | 5,290 + art generators |
| Art pipeline `menu/pipeline` | 40 py | 13,116 |
| Art outputs `menu/out_*` | about 800 PNG | 15 kit 2x files; `_build/ui` holds 151 files |
| Launcher Qt / C# | 14 / 3 | 2,699 / 2,644 |
| Docs | | `scripting.md` 2,576, `ART-BRIEF` 198, `frontend-menus.md`, `menu-kit-pieces.md` |

Distinct screens (counting each separately visible state, not variants):

| Who draws | Count |
|---|---|
| Port native kit | about 28: 7 hubs, 4 lists, match setup, online rows, 6 settings pages, remap and how-to, 3 room screens, loading (2 instances), CSS, SSS, onboarding |
| Retail (still reachable) | about 25 (section 1.2) plus the in-match HUD |
| Envoy mod via `gd.kit` | 14 menu states + 3 grid layouts + about 7 HUD pieces |
| LAB | 6 pause tabs + 9 modes + about 6 panels |
| Launcher | 4 tabs (+ dialogs) |
| Console/overlay | about 4 |

Rough ordering of what a migration could do first with least risk [judgement, information only]:

1. Things already behind a fallback switch: hubs/lists (native, tables), because `FM_HUB/FM_LIST` are data.
2. The Envoy grid screens and HUD (script-side, offline, presentation only: cannot desync).
3. Wiring the existing but unconsumed nav art (event, rules, records, sound test).
4. Settings pages (table driven).
5. CSS/SSS and loading (more state).
6. Online lobby (netplay-synchronised; highest risk).
7. Retail-only screens (title, results, trophies): require engine work, no existing replacement.
8. The launcher last or in parallel (separate program).

---

## 7. Questions for the owner (not answered here)

1. Scope: is the **launcher** (Qt) part of the re-unification, or its own look?
2. Are **retail's own menus** (title, results, trophies, data, rules, name entry, 1P modes) to be replaced, or left as they are?
3. Is the **in-match HUD** (retail damage/stocks/timer, Envoy strip) and the **pause** part of "menus"?
4. Should **mods** be able to add menus (main-menu entries, settings pages, pause tabs) or only draw screens?
5. One layout for every aspect ratio, or keep a centred 4:3 core with a wider canvas?
6. Is **mouse and keyboard** a first-class input, or pad first with mouse as an addition (as today)?
7. Does the **Envoy** menu set stay inside the Envoy mod, or become the game's own?
8. Do the **drive models** (3D) become a general "model cell" language across menus?
9. **Languages**: is a second script (Japanese, retail's language setting) in scope?
10. Is the **section tint** idea (Solo brown, Versus blue, ...) part of the identity, or one of the things to replace?
11. Keep **hard-shadow/shear** as the identity, or is the new style a clean break (the art studies by Astra in `out_roguelite*` are unverified)?
12. Does the migration need to ship **screen by screen** while the old kit still runs?
13. Is **accessibility** (reduced motion, larger text, colour-blind-safe signals) a requirement?
14. Which features in section 4 must get a menu first?

---

Pictures seen (32): `menu/out_nav/preview/` hub_main, hub_solo, list_options, list_special, grid_items, event_match, table_records; `menu/out_hub/preview/hub_sel_versus_1x`; `menu/out_hub_bouba/preview/hub_sel_versus_1x`; `menu/out_kit/preview/` list_versus, widgets_solo, sections_strip, list_dialog; `menu/out_lobby/preview/` lobby_g1_strike, waiting_host, lobby_countdown; `menu/out_loading/preview/loading_four`; `menu/out_roguelite/preview/build`; `menu/out_roguelite_expansion/preview/01-combat`; `menu/out_brand/keyart/keyart_clean_1080p`; `docs/readme/banner_dark`; `_build/audit-20261003/` envoy-join (reward_keys_43, reward_keys_169_a, bag_43, swap_169_a, strip_169_a), envoy-look/after/bag_full_43, batch2-verify/css225, geno-slice4 lab_sheet, frozen-k/cast_blast; `_build/launcher-smoke-shots/launcher-0`, `-2`. Not looked at: `out_online` (no previews), `out_readme` set, the rest of the Envoy/FX captures (not menus).
