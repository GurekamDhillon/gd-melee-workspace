# Workbench (direction a): menus as physical objects on a work surface

Open `index.html` (no server needed) for the gallery; `kit.html` is the live kit showcase. `python build.py` re-renders everything (headless Chromium, no network).

**The idea.** The game is a work surface: a dark slate-green cutting mat with a printed 16 px grid. Everything on it is a solid object with weight, and each material means one thing. **Chipboard** is a choice you can pick up (buttons, rows, bins). A plastic **puck** is something you own or play (drives, pegs). A **kraft tag** is information about the lifted piece, one rule per tag. A taped **paper slip** is an event (notification, warning). **Cast steel** is heavy and committed (keystones hanging from a rail, clamps, quit). **Label tape** says where you are (title, breadcrumbs, the hint rail). A **recess** is where things go (trays, sockets, value windows, switches). A **manila folder** holds boards (settings, LAB, launcher).

**The rules of the style.**
1. Depth is a visible front edge plus a hard offset shadow. No gradients, no glow. One piece per screen is lifted (edge 3 to 7, shadow grows, two orange grip clamps sit outside its corners); only the lifted piece has a tag, tied to it by a string.
2. Verbs are physical: pick up (A), put back (B), turn over (X), sort (Y), lay side by side (Z), flip page (L R). Selected things are seated flush and carry a pin; disabled things are die-cut outlines with nothing to pick up.
3. Four players: every player-owned thing carries a tape flag or peg with a colour, a shape (circle, square, triangle, diamond; CPU hexagon) and a number. Signals are never colour alone.
4. Scale: a two-word menu is a few big boards and one tag; the dense screens (character select, remap editor, bag) stay calm because everything but the lifted piece is flat and one tone. Wide screens (16:9) keep interaction in the 4:3 core and use the extra width for status drawers (ports, notices) or more columns.
5. Drives are the real models drawn on pucks in sockets; keystones hang as heavier steel pieces with a letter and a colour band.

**Drives (what was done).** `drives.py` reads the committed `melee/pc/scripts/examples/envoy_drives/models/*.gxmesh` and the two atlases and draws each drive headlessly as an orthographic flat-shaded SVG (painter sort, one fixed light, base times light plus glow, as the in-game screen model does). They are real geometry and the real palette, not redrawn by hand. Rarity rings are the real overlay meshes. The family-to-piece assignment on the screens (for example Frosted as purple) is illustrative: the pool appendix gives colours for keystones only. Piece names and rule lines are the real text from `APPENDIX-pieces.md`.

**What it needs from the engine beyond flat quads, atlas text and model cells: nothing required.** Every piece is 1 to 3 flat quads (face, edge strip, shadow quad at a fixed offset); the mat grid is one tiled texture; chamfered tags and keystone shapes are baked 9-slice textures; the string is a thin quad. Optional, with fallbacks: (a) quad rotation for the 2 degree tilt of slips: without it slips sit straight (the screens work as is); (b) the hatched disc-art placeholder is a texture: without it a flat dark quad with the label; (c) the dialog cover is a translucent black quad (exists today); (d) the drives are `gd.kit.model` cells: without them the same pucks show a flat family shape (the HUD already uses these shapes). No shaders are used anywhere.

**Fonts.** The engine's two: Source Sans 3 (Adobe, SIL OFL 1.1; `menu/SourceSans3/`) for everything, Hasklug Mono Medium (Hasklig/Source Code Pro with Nerd Font glyphs, SIL OFL 1.1; `menu/Hasklug/`) for printed captions. Loaded from `menu/` by `@font-face`; no new families, so nothing to add to `CREDITS.md`.

**Credits.** Playwright and Chromium render the pages. No outside images or ideas were used beyond everyday objects (cutting mats, label tape, index cards, gaming tokens). The drive models are this project's own (`envoy_drives`).

**Placeholders and sample state.** Fighter and stage names are plain strings; every picture of a fighter, stage or portrait is a hatched frame labelled "disc art". Unknown values are bracketed (`[ROOM CODE]`, `[PING]`, `[VERSION]`, `[BEST TIME]`, `[KOS]`). The live match numbers on the HUD (47%, 82%) and the sample setting values are illustrative, not game data. Mod kinds on the mods screen are illustrative.

**Files.** `tokens.css`, `kit.css`, `parts.py`/`screens.py`/`kitpage.py` (generators), `screens/*.html`, `out/*.png`, `assets/` (drive SVGs), `build.py`.
