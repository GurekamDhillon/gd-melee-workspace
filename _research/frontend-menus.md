# Frontend menus: the player, the JSON contract, the routing

Written 2026-09-21. Code in `melee/src/melee/gm/`: `gmfrontend.c` (scene, routing, the MATCH SETUP toolkit), plus three files it includes, `gmfrontend_player.inc`, `gmfrontend_kit.inc` and `gmfrontend_menus.inc`. Hooks live in `gmmenumode.c` and `mnmain.c`. The host side is `gw_UiFile_Read` and the two switches in `pc/platform/gw_runtime.c`. Art import is `pc/tools/png2gx.py --layout`. The sweep is `tools/port/fe_menu_sweep.py`.

The `.inc` files belong to the `gmfrontend.c` translation unit. Build them with `tools/port/build.sh --tu src/melee/gm/gmfrontend.c`. Adding a real TU would mean editing the shared link list that every agent uses.

## Switches

| Variable | Default | Effect |
|---|---|---|
| `MELEE_FRONTEND` | on | the port's frontend screens at all (MATCH SETUP, loading screen, menus) |
| `MELEE_FRONTEND_MENUS` | on | GM_MENU's list screens become frontend screens. Set it to `0` to get Melee's own menu, for side-by-side comparison |
| `MELEE_FE_HUBDEMO=<frame>` | off | shows `out_hub`'s own 4-tile hub and plays `pipeline/hub_motion.py`'s preview script, frozen at `<frame>`. Any non-number loops it |

## Importing art

```
python pc/tools/png2gx.py --layout <menu>/out_kit/manifest.json --layout <menu>/out_hub/hub_layout.json \
    --outdir _build/ui --copy <menu>/out_kit/{kit.json,font/font_manifest.json,chrome_layout.json,list_layout.json,kit_motion.json}
```

`--layout` accepts any JSON with a `textures` list (a `*_layout.json` or a section's `manifest.json`). It converts each texture at its own GX format, including the new `I4` and `IA4`, and copies the file along with a sibling `*_motion.json`. The game reads these files from `ui/` beside the exe, then `../../ui`, then `../../../../ui`, so agent sandboxes find `_build/ui`.

## The player

**Runtime JSON, not a converter.**
- The files are small, and the art side keeps changing them. The font manifest changed format twice in one afternoon.
- A 150-line parser in the game translation unit reads each file once. Its DOM is freed as soon as the model is built.
- It runs in the game TU because everything it produces is floats that game code reads. The host passes only file bytes, which read the same on both sides of gwtool's byte swap.

**What it implements, exactly as `hub_motion.json` states it:**
- **Keys:** `(frame, value, interp, slope)` with CON, LIN and SPL. SPL is a cubic Hermite with slopes in value/frame. Before the first key the channel holds that key's value; after the last key, the last value.
- **`from_current`:** replaced by the channel's value at the event's start.
- **Which event plays:** a channel plays the most recently started event whose start frame has been reached, in insertion order. That is how the reference sequencer's scheduled "hold at 720, then slide in" works.
- **Transforms:** a joint maps `p -> pivot + S(p - pivot) + T`, and the world transform is the parent's applied after the child's. RECOIL adds `r * 2 * unit(pivot(tile) - pivot(selected))`, with the 2 read from the `transform` text.
- **Draw order:** top-level quads, then tiles by rank, then the previous selection, then the selection. Each tile draws plate, face, icon, label. Every tile's description comes last. Opacity is material ALPHA times the joint ALPHA chain.
- **I4 masks:** one TEV stage that takes RGB from the vertex (material) colour and alpha from texture × material. RGBA textures modulate normally.
- **Material tracks on joints:** a material track whose target names a joint (`plate_<id>`, `desc_<id>`) drives that joint's ALPHA, which is how the file lists those channels.
- **Generated screens:** these instantiate the per-tile joints from the file's pattern, the joints ending in the first `tile_<id>`'s id. The hub demo takes the file's joints literally.

**Fidelity against the art previews.** Captures were taken at 1280×960 (2x), with the window frozen at each frame, and compared with `motion_select_sheet_2x.png` (frames 40–51 of the script, Versus → Solo).

| Frame (sheet) | Mean abs diff | Pixels off by >40 |
|---|---:|---:|
| f00 | 0.8 | 1.36% |
| f01 | 1.1 | 1.72% |
| f02 | 1.3 | 2.15% |
| f03 | 1.6 | 2.60% |
| f04 | 1.9 | 2.57% |
| f06 | 1.5 | 2.07% |
| f08 | 1.0 | 1.71% |
| f11 | 0.8 | 1.36% |
| settled Versus (vs `hub_sel_versus_2x.png`) | 0.08 | 0.12% |

- The flash on f01, the hero's deselect, the lift overshoot, the 3% pop, the plate and the label/icon switch frames all land on the same frames.
- The remaining difference is edge rasterisation: SVG antialiasing in Chromium against GPU triangles, plus bilinear sampling of I4 masks.
- `_build/tmp/fe_demo_compare.png` shows them side by side.

## The kit (section 1) as used

- **Text:**
  - Every frontend menu string is set from `font_manifest.json` alone: `kerning[prev+ch]`, a quad at pen + offset, then pen += advance. A missing character falls back to `?`.
  - `hero` and `display` text is uppercased.
  - The fit rule: step down to the next smaller role of the same face, then truncate with `…`. Nothing is squashed.
  - Glyphs are laid out unsheared and then pushed through the screen shear, so they come out italic.
  - HSD_SisLib is the fallback when the manifest is missing.
- **Colour:**
  - `kit.json` sections colour each screen: bg, bands and band rhythm, face and face_hi.
  - Each tile on the main menu takes the colours of the section it leads to.
  - Tokens (`@face`, `gold`, `port:p1`) are resolved in templates and in `kit_motion.json`.
- **Chrome:** `chrome_layout.json` supplies the header slab sized by its title, the breadcrumb (the section icon, then the path, with gold separator bars), the description strip, and the footer hints (A tinted `ok`, B tinted `danger`).
- **Lists:** `list_layout.json` supplies the rows (x 96–540, pitch 34, 9 visible). Lists scroll past nine rows, keeping the cursor one row from either edge, over 7 frames as the kit's scroll event does. List cursor moves play `kit_motion`'s `row_select` and `row_deselect`.
- **Hubs:** hubs use `hub_motion.json`. The hub's own number colours are mapped to each tile's section colours.
- **Space convention:** kit templates are unsheared, while `hub_layout.json` is still in screen space and its motion is applied in screen space. Generated screens build unsheared, shear, then apply the screen-space hub motion. When section 2 moves the hub to the kit's convention, the joint transforms should move before the shear. That is one place: `fp_evaluate` and `fp_draw_text`.

## Routing

A frontend position is always vanilla's pair (MenuKind, selection). That keeps all of vanilla's own positioning working:

| Event | What happens |
|---|---|
| any mode → GM_MENU | `gmFrontend_Route` computes where `gmmenumode.c` would open (force_main_menu, then previous mode → table), and enters GM_FRONTEND there instead. Exception: the Event list after an event stays native |
| frontend item → game mode | the frontend leaves for that mode and reports GM_MENU as the previous mode, as the native menu does |
| frontend item → not-yet-replaced screen | the frontend leaves for GM_MENU with a request. `gmmenumode.c` positions the menu at (parent, item), and `mnmain.c` opens the screen with the same call the parent's think makes (`mn_PcOpenNative`) |
| native screen backs out | `mn_80229894(kind, sel)` asks `gmFrontend_NativeReturn`. For a replaced menu, GM_MENU ends into GM_FRONTEND at (kind, sel) |
| VS > Melee | MATCH SETUP (its own GS_FRONTEND scene) → GM_VS. B goes back to the VS hub on Melee |
| Rules → START | native, as before: GM_MENU → GM_VS, through MATCH SETUP |
| L+R+START (not on Main) | force_main_menu, then GM_MENU, which routes to Main |
| Language change | GM_MENU → GM_MENU, which lands on Options > Language |

**On arrival, the menus do what `mnMain_Scene_OnEnter` does:**
- start the menu music (`lbAudioAx_80023F28(gmMainLib_8015ECB0())`);
- mark the save dirty (`lbCardGame_SaveChanges`);
- in the state's on_enter, `lbCardNew_AllocWorkArea`, `lbCardGame_LoadArchive(0)` and the three `lbDvd` preload calls.

## What is replaced and what is native

| Replaced (frontend) | Still native (in GM_MENU) |
|---|---|
| Main, Solo, Regular Match, Stadium, Multi-Man Melee, Versus, Special Melee, Collection, Options, Data, Records (the 3-item list) | Rules and More Rules, Item Switch, Stage Switch, Name Entry, Event Match list, Rumble, Sound, Screen Display, Language, Erase Data, Snapshots, Movies, Sound Test, Special Messages, VS/Bonus/Misc Records tables; CSS, SSS, trophies, results (other modes) |

Beyond the brief's table, three vanilla items are included because the native menu has them: Data > Movies (`SEL_DATA_ARCHIVES`), Special Melee > Slo-Mo Melee (`SEL_SPECIAL_VS_SLOMO`, visible in vanilla), and the Records sub-list.

## Tests

`python tools/port/fe_menu_sweep.py --disc <vanilla|ace|akaneia>` boots to the menu, walks to each item, presses A, holds or taps B back out, and checks the log. It verifies the destination mode or native screen and the return to the same item. There are 52 items.

**Pre-existing native crashes.** These also happen with `MELEE_FRONTEND_MENUS=0`, on the untouched native menu:
- **Options > Rumble:** `assertion "jobj" failed`.
- **Options > Erase Data:** access violation in `mn_8022F298` from `mnDataDel_8024FE4C`.
- **Data > Records > VS. Records:** the same access violation.

They are native screen bugs, not routing bugs.

## Art still expected (logged once per run as `frontend: art missing: <name> - expected from ...`)

| Texture | Brief section | Used by |
|---|---|---|
| `ico_data` | 2 | main-menu Data tile, the Data breadcrumb |
| `ico_regular`, `ico_event`, `ico_stadium`, `ico_training` | 2 | Solo hub |
| `ico_classic`, `ico_adventure`, `ico_allstar` | 2 | Regular Match hub |
| `ico_target`, `ico_homerun`, `ico_multiman` | 2 | Stadium hub |
| `ico_melee`, `ico_tournament`, `ico_special`, `ico_rules`, `ico_names` | 2 | Versus hub |
| `ico_gallery`, `ico_lottery`, `ico_trophies` | 2 | Collection hub |
| `ico_snapshots`, `ico_movies`, `ico_soundtest`, `ico_records`, `ico_messages` | 2 | Data hub |
| the hub layout rule for 2–9 tiles | 2 | every hub. Until it arrives, `fm_build`'s stand-in is used: a hero, plus a column stepping down ×0.76 |
| locked / new / completed marks | 2 | not used. Vanilla hides locked items |

Section 1's widgets, dialog, toast and cursor layouts are imported but not used yet. The replaced screens are all navigation. They come into use with Rules, Options and the dialogs.
