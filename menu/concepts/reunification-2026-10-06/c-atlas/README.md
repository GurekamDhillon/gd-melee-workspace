# ATLAS: rich and layered, kept calm (menu direction c, 2026-10-06)

Open `index.html` (no server). Rebuild everything with `python build.py` (headless Chromium, offline, deterministic). Kit sheets: `kit.html` and `out/kit-*.png`. The 17 screens are `screens/*.html` and `out/NN-*.png`.

**The idea.** A modern action-RPG menu has depth; the owner found Envoy's "too much at once". Atlas keeps the depth and rations it with one structure on every screen: **where** (trail and chapter dots, top), **primary** (the thing you act on, left), **explainer** (the one thing in focus, right, always WHAT / WITH / FROM, `Y` for more), **keys** (pad hints, bottom). Cells show only a model or a name; the rule, the pairings and the origin appear for the focus alone, so a piece never shows more than one short rule at once.

**Style rules.**
- Depth with flat quads: E0 ground, E1 plate, E2 row/cell, E3 lift, modal. A higher level is lighter and shows a thicker front edge (3 px plates, 6 px modal). No shadows, gradients or curves; chamfers on two opposite corners only.
- Focus is three cues at once: lift 2 px, ember front edge, and a tick (rows) or four registration brackets (cells, tinted with the port colour). Selected = jade bar; disabled = hatched.
- Ember is the one action and focus; jade is information, origin and "on"; sun is caution; rose is danger. Colour is never the only signal.
- Four players: numeral plus shape (circle, square, hexagon, diamond) plus colour; CPU is hatched grey.
- Drive models live in cells (model only, floor shadow) and in the explainer (large, with the rule); rarity is the real ring overlay; keystones are arch stones with a letter.
- Wide screens add a chapter rail and widen grids and the explainer; nothing new appears. Atlas ground carries a faint graticule of `+` marks (one 48 px tile).
- Same structure serves a two-word menu (02), the bag (09) and the remap editor (14c): see `out/kit-5-structure-motion.png`.

**Engine needs.** Everything is flat quads, 2-triangle chamfers, a tiled texture for the graticule, atlas text, and `gd.kit.model` cells (already there). New engine work: (1) a third font atlas for **Barlow Condensed** (caps labels and titles; fallback: Source Sans 3 Bold caps, same sizes, titles will be about 12% wider so fit rules step down one role); (2) letter-spacing (tracking) in atlas text (fallback: none; labels read slightly tighter); (3) clip-less chamfers are plain triangles (no work); (4) hatch fills are a small tiled mask texture (fallback: flat dim fill plus a word such as "Closed"); (5) turntable motion for model cells is per-frame yaw, already scriptable. No custom shaders are needed.

**Drives.** `drives.py` imports the committed generator `melee/pc/scripts/examples/envoy_drives/tools/make_drives.py` read-only, takes its own triangles and colour-ramp table, rotates them to a three-quarter view, lights them and writes flat-shaded SVG. These are the real models drawn in 2D, not captures. Family colours of individual drives are assigned from the mod README's meanings (the appendix has no family field for drives); keystone colours come from the appendix. Rule text is the real appendix text.

**Placeholders and mock data.** Bracketed values (`[ROOM CODE]`, `[PING]`, `[N]`, `[VERSION]`, `[CLEAR TIME]`) are unknown real values. The results screen's KOs and falls are sample match data, not game stats. LAB rows (Behaviour, Shield, Percent...) are plausible, not read from `lab.lua`. Disc art is always a hatched, labelled placeholder; fighter and stage names are plain strings.

**Fonts.** Source Sans 3 (Adobe, SIL OFL 1.1) and Hasklug Nerd Font (SIL OFL 1.1; Hack/Source Code Pro lineage with Nerd Fonts patches), both loaded from `menu/SourceSans3` and `menu/Hasklug`. Added: **Barlow Condensed** by Jeremy Tribby, SIL OFL 1.1, https://github.com/jpt/barlow (files from https://github.com/google/fonts/tree/main/ofl/barlowcondensed), in `fonts/` with `OFL.txt`. Coordinator: add Barlow Condensed to `CREDITS.md`.

**Credits.** Playwright and headless Chromium render the pages (as `menu/pipeline/readme.py` does). Everything else is original to this project; nothing is traced from Nintendo or HAL work.

Files: `tokens.css`, `kit.css`, `parts.py` (components), `screens_a.py`, `screens_b.py`, `kitpage.py`, `drives.py`, `indexpage.py`, `build.py`.
