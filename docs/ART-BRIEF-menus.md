# Art brief: replacing every vanilla menu

You own the art pipeline in `C:\Users\Gurek\Desktop\menu` (`pipeline/`, `out/`, `out_hub/`). The engine side is replacing Melee's menus with our own screens, drawn by `gmfrontend.c` in the PC port. This brief lists every asset those screens need, in the order the engine side will build them. Each section is the contract for one step. Deliver a section at a time; the engine side starts on section 1 as soon as it lands.

Everything you already set up still applies unchanged:
- The provenance rule: nothing is traced, recoloured, referenced or sampled from Melee. The `meleedump/index` metadata is fine to read. Never the pixels.
- Authoring at 2x, with power-of-two sizes of at most 1024.
- The quantisation checks and the white-mask-plus-material-tint approach.
- Straight alpha and no colour management.

## How the engine draws, so you know what's cheap

- **Coordinates and resolution:**
  - Every screen is laid out in 640×480 units (origin top-left, y down), the same space as `hub_layout.json`.
  - Textures are authored at 2x and drawn at their 1x size.
  - The window renders at any resolution, so edges stay sharp.
  - Keep everything inside the title-safe rectangle `[32, 24, 608, 456]`, including peak motion.
- **What the engine draws:**
  - flat quads and textured quads with explicit vertices (parallelograms for textured quads, as you already check);
  - one texture stage modulated by vertex colour;
  - 9-slices;
  - text from your font atlas.
- **Drawing is cheap, texture memory isn't.** Colour, translation, scale and visibility cost nothing per frame. New textures cost memory. Prefer masks tinted by colour over baked states.
- **Motion runs in our own player.** It plays your `hub_motion.json` format: the joint list, `from_current` keys, the transform rules, the keyframe maths and the sequences. Use that format for every animated thing below. Colour and alpha are 0–1, and alpha means opacity.
- **Text is always drawn from strings.** Never bake words into a texture. The engine supplies every label, name and number at runtime, and the English and Japanese versions differ. Melee's menus had 664 language-specific textures; we want zero.

## What always comes from the user's disc (don't draw these; frame them)

Vanilla and m-ex discs both supply these, and m-ex discs add characters and stages, so every count below is open-ended.

| Art | Size at 1x | Used on |
|---|---|---|
| Character select icon | 64×56 | CSS grid |
| Character portrait (per costume) | 136×188 | CSS player panels, results |
| Stock icon (per costume) | 24×24 | CSS, results, records |
| Stage select icon | 64×56 | SSS grid |
| Stage preview | varies by disc; the engine will report exact sizes | SSS |
| Results-screen character models (3D) | n/a | results |
| Item icons | small | item switch (rules) |

Your job for these is the frame, cell, plate, highlight and layout around them. Frames must be 9-slices, or sized by rule, so they fit whatever size the disc delivers.

Names (characters, stages, items, bonuses) are strings drawn with the font atlas. Plan for these lengths:
- Character names: up to 20 characters. The longest vanilla name is "Mr. Game & Watch" at 16.
- Stage names: up to 28. The longest vanilla name is "Princess Peach's Castle" at 23.
- Name tags: up to 4 characters.
- Bonus names: up to 24.

## Visual system

Extend the **rectangular hub** as the base system for every screen, because it's the one with a finished motion spec. Keep one system across all screens rather than mixing hub styles. If you think the bouba hub should be the base instead, say so before section 2. That's the point where changing costs nothing.

Define these once, in a shared `kit.json`:
- **Palette:** section tints, text colours, disabled.
- **Four player-port colours:** distinct under colour-blindness simulation (check deuteranopia and protanopia). Plus a CPU colour, a "closed slot" treatment and three team colours (red, blue, green, as the game's teams). Record the contrast of label text on each.
- **Type scale:** every text size the screens use. Reconcile it with your baked-text height clusters from `SORT.md`.

## Section 1: kit primitives and the font atlas (needed first; every screen uses these)

1. **Font atlas coverage:**
   - Printable ASCII 0x20–0x7E in every size of the type scale.
   - Plus `× % ° … – — ← → ↑ ↓ ★` and a tabular digit set that doesn't jitter when numbers change.
   - Plus ordinal suffixes `st nd rd th` sized for the results placement.
   - Include kerning or advance widths in the manifest.
   - English only for now; leave room in the atlas layout for a second script later.
2. **Button glyphs:** A, B, X, Y, Z, L, R, START, control stick, C-stick and D-pad, as masks. Draw them as original shapes, sized to sit inline with the footer text. They replace the current `glyph_a` and `glyph_b`.
3. **Screen chrome:**
   - A header bar with a title and a breadcrumb (e.g. VS > Rules > Items).
   - A footer with button-hint slots, each a glyph plus text.
   - A description strip.
   - One backdrop system that tints per section (Solo / Versus / Collection / Options / Data), so players know where they are.
4. **List-screen template** (rules, options, records lists, event list): a row in its normal, selected and disabled states; a section divider; a scroll indicator; and a value area on the right that holds any of the widgets below.
5. **Widgets:**
   - toggle (on/off);
   - choice (left/right arrows around a value);
   - slider (track, fill, knob, value readout);
   - stepper for numbers;
   - checkbox grid cell (item switch, stage switch).
   - Each needs normal, selected and disabled states, plus a motion spec for change, including a "can't go further" bump at the ends.
6. **Dialog:**
   - A modal panel for yes/no confirmations and memory-card messages: a title, 1–4 lines of body text and 1–3 buttons.
   - Plus a brief toast for messages like "Saved".
7. **Cursor:** the existing hand, plus a variant for each of the four ports and the CPU, with the port number drawn from the atlas, not baked.

## Section 2: navigation screens (title excluded)

Every navigation screen is either a **hub** (like the main menu) or a **list** (the section 1 template). Deliver a `*_layout.json` per screen in the `hub_layout.json` format, the icon masks it uses, and its motion. Where a hub has 2–9 tiles, give the layout rule (how tile sizes step down), not just one fixed arrangement, so hubs with any number of tiles can be generated from it.

| Screen | Kind | Items (each needs a label from strings; hub items also need an icon) |
|---|---|---|
| Main menu | hub | Solo, Versus, Collection, Options, Data |
| Solo | hub | Regular Match, Event Match, Training, Stadium |
| Regular Match | hub | Classic, Adventure, All-Star |
| Stadium | hub | Target Test, Home-Run Contest, Multi-Man Melee |
| Multi-Man Melee | hub or list | 10-Man, 100-Man, 3-Minute, 15-Minute, Endless, Cruel |
| Versus | hub | Melee, Tournament, Special Melee, Rules, Name Entry |
| Special Melee | hub or list | Camera Mode, Stamina, Super Sudden Death, Giant, Tiny, Invisible, Fixed Camera, Single-Button, Lightning |
| Collection | hub | Gallery, Lottery, Collection (the trophy screens) |
| Options | list | Rumble, Sound, Screen Display, Language, Erase Data |
| Data | hub | Snapshots, Sound Test, Records, Special Messages |
| Rules | list | Mode, Stock / Time, Handicap, Damage Ratio, Stage Selection, Items, More Rules |
| More Rules | list | about 8 settings (stock time limit, pause, score display, self-destructs, etc.) |
| Item Switch | grid of checkbox cells | item icons from the disc, a frequency choice, all on / all off |
| Random Stage Switch | grid of checkbox cells | stage icons from the disc, all on / all off |
| Records | list plus tables | a table style with a header row, a character column (stock icon plus name), numeric columns and a totals row |
| Event Match | list plus detail | an event row (number, name, completed mark, best time), a detail panel with a description paragraph, and a slot for the event's disc image if one exists |
| Sound Test | list | track rows with a playing indicator |

The icon masks this implies are the hub items above: about 30 icons, plus a small **completed** mark, a **locked** mark and a **new** badge for items that aren't unlocked yet.

## Section 3: character select screen (CSS)

The engine keeps all of Melee's CSS behaviour; only the look is new.

- **Roster grid:** cells frame the 64×56 disc icons.
  - States: normal, hovered by one or more ports (show every port hovering it), selected, locked.
  - A **random** cell.
  - The grid is a layout rule, not a fixed arrangement: it must fit anything from 26 up to about 60 characters (m-ex) without art changes, with a documented column and row formula.
- **Tokens:** one per port, in each port's colour with its number drawn from strings.
  - States: held by the hand, dropped on a character, lifted back.
  - Motion for the pick-up and the drop.
- **Player panel** (four, one per port), with states for human, CPU and closed. It carries:
  - the 136×188 disc portrait;
  - the character name;
  - the slot-type switch (HMN / CPU / closed);
  - a costume indicator (arrows or pips; costume counts vary per character);
  - a CPU level slider (1–9) and a handicap slider (1–9), each shown only when enabled;
  - a team-colour badge in team mode;
  - a name-tag plate.
- **Header strip:** the current rules summary (e.g. "Stock 4 · 8:00 · Items Off") and a way into Rules.
- **"Ready to fight" banner:** appears when at least two ports are ready, with its motion. The words come from strings.
- **Solo variant:** one panel plus difficulty and stock choices, for Classic, Adventure and All-Star.

## Section 4: stage select screen (SSS)

- **Stage grid:** cells frame the 64×56 disc icons. It's a layout rule that must hold up to about 80 stages. m-ex discs have pages: give a page tab or indicator and the page-change motion.
- **Preview frame:** a 9-slice sized by the engine to the disc's preview.
- **Name plate:** the stage name from strings.
- **Random cell.**
- **Tag marks:** optional small marks for **starter** and **counterpick**. Tournament players ask for these; the stage list comes from settings, not art.
- **Hover and confirm motion.**

## Section 5: results screen

- **One column per player,** in port colour (team colour in teams), holding:
  - a placement badge (1st–4th, with the numeral and ordinal from the atlas);
  - the 3D character model area (disc);
  - the name or name tag;
  - stat rows: KOs, falls, self-destructs, damage given, damage taken, peak damage, and the coin total in coin mode;
  - a bonus list that scrolls (name plus points).
- **Winner banner:** a frame whose text comes from strings ("P1 wins", team wins and "No contest" are all strings).
- **Reveal sequence:** columns in, placements counted, winner banner, then a "press Start" prompt. Deliver it as a motion sequence with its timings.

## Section 6: title screen

- A **project wordmark**: original, placeholder name "GD's Melee".
- A "Press Start" prompt style with its idle motion.
- A backdrop.
- An attract loop, or a still backdrop if motion is too costly.

No Nintendo, HAL or Melee logos, marks or lettering, in any form.

## Section 7: remaining screens

- **Name entry:**
  - An on-screen keyboard: key caps (normal, selected, pressed), wide keys for space, backspace, mode and OK, and a text field that shows 4 characters with a caret.
  - Layouts for letters, symbols and a second-script page.
  - The key labels come from the atlas.
- **Memory-card and boot messages:** these use the section 1 dialog. No new art beyond a small card icon mask.

## Not in scope

Leave these alone for now:
- the in-match HUD, pause and magnifier;
- the tournament bracket;
- game over, trophy fall, the staff roll and ending screens;
- 1P intermission screens;
- trophy models and the 3D areas of the trophy screens (the chrome around them is section 2);
- menu sound effects and music.

## Delivery format for every section

- **Textures:** in `out_*/2x` and `out_*/1x`, each listed in the section's `manifest.json` with its GX format and the reason for that format, as you already do. Names are lower snake case and stable across rebuilds, because the engine loads them by name.
- **Layouts:** `*_layout.json` in the `hub_layout.json` format. For each dynamic element (strings, disc art, counts), name the slot it fills and the maximum size it must fit, instead of placeholder art.
- **Motion:** `*_motion.json` in the `hub_motion.json` format.
- **Kit:** `kit.json`, as defined under Visual system.
- **Previews:** composed from the JSON alone, like the hub previews. Each screen's worst case is rendered with the longest names, 4 players, the largest roster and a CPU in every slot.
- **Checks:** the build checks everything the hub build already checks, plus:
  - text slots fit their stated maximum strings at their type size;
  - every dynamic grid holds its stated maximum count inside title-safe;
  - port colours are distinct under colour-blindness simulation.
- **Memory:** report the total texture memory per screen. Budget 1 MB at 2x per screen, excluding disc art. Say if a screen needs more, and why.

## Open questions to answer in your first delivery

1. Is the rectangular hub the base system, or should it be bouba? (See Visual system.)
2. How do sections read as different places (tint, backdrop pattern, header treatment) while staying one system?
3. What's the smallest type size you'll allow at 1x before it stops reading on a 640×480 CRT-style scale? The engine renders HD, but 1x should stay legible.
