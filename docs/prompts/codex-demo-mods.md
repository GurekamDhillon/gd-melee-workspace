# Codex packet S: demo mods, one per feature, and showcase mods that combine them (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`docs/scripting.md`, `docs/shaders.md`, `docs/profiling.md` if present, `docs/mods-packaging.md`,
`docs/HANDOFF-2026-10-03-ENGINE-DAY.md` for what exists and how far each thing was verified). Both trees are deliberately
dirty: do NOT commit, reset, stash, revert or reformat. Lua, JSON, WGSL, Markdown and Python only: do NOT edit C, do NOT run
`tools/port/build.sh`, do NOT launch the game. Other jobs are editing engine C (`melee/pc/geno/`, the LAB mod) and
`tools/geno/`: stay out. No game-derived data and no third-party assets: demos use the built-in kit pieces by name,
primitives and text only (models are filled by the user's own exports; a demo must still do something visible without
them). Credit techniques in each README and in `CREDITS.md` where a source was consulted.

## The owner's direction (verbatim)
"We should be good tooling providers and make demo mods showcasing each feature individually, then like real mods demoing
many features together showing real "work" you know what I mean."

## Build
A. **A demo catalogue**: `melee/pc/scripts/examples/demos/` with `README.md` (the index: one line per demo, what it shows,
   the API section it teaches, how to run it, whether it has been run in the game). One self-contained mod folder per
   feature (`mod.json`, `scripts/main.lua`, a README of at most a page, and data files where the feature needs them), each
   the SMALLEST program that shows the feature clearly on the vanilla disc in the LAB, readable top to bottom by someone
   learning the API, heavily commented, with on-screen text saying what you are looking at and which keys or console
   commands change it, and a clean unload. One feature per demo; no demo over ~150 lines of Lua. Cover every public
   capability, verified against the registration tables and docs (never call an API you have not found registered):
   input and pad reads; text and kit drawing with the safe area; fighters: reading state, teleport, percent, CPU modes;
   passive modifiers (`gd.fighter_mod`); bench and call; the debug fly cursor; contacts, traces and `gd.wait_until`; camera
   control and `gd.camera_params`; stage collision lines and platforms; models (`gd.model_*`) and labels; custom materials,
   glass and lights; mission folders (a tiny level), chunks and reload; the mission camera modes; the maze generator (a
   seed and its ASCII map); enemies and waves; items: standalone Geno items with `on_item_collect`, and the unified item
   list; events (`on_clank`, enemy defeat, stage switch); timed hitstop; post-process passes (one demo per built-in idea:
   grade, vignette, outline, bloom) and a custom WGSL pass with live reload; fighter and stage surface shaders; per-part
   tints (`gd.dobj_tint`, `gd.parts`); effects (`gd.fx_*`); stage slots, switching and the queue; six-fighter launches and
   slot recycling; saving data (`gd.data_*`); the profiler (`gd.perf`, zones, the console commands); the console socket
   from an external script (a tiny Python client demo); a Geno fighter overlay (point at the tutorial mod in
   `docs/learn/geno-fighters/` rather than duplicating it). Where an existing sample already is that demo
   (`stage_switch_demo`, the post samples, `missions/first`, the bench mod), move nothing: list it in the index and add
   only what is missing.
B. **Showcase mods** that do real work by combining features, each a complete small thing someone would actually play or
   use, with its own README explaining the design and which demos to read for each part:
   1. "Gauntlet": a three-room mission (hand-authored level folder + a generated maze section) with waves, a benched boss
      called for the finale, item drops that buff the player through passive modifiers, the follow and chunk cameras, a
      stage switch as the transition into the boss room, a post-process flourish on victory, a results screen in kit UI,
      and a saved best time.
   2. "Training card": a LAB-side tool: pick a move, see its contact trace, hitbox data and frame timeline as text, with a
      `wait_until`-driven drill ("land on the platform within N frames") and pass/fail feedback: showing the tooling side.
   3. "Stage tour": a queue of stage slots with a different transition and shader look per stage and a HUD caption: the
      presentation side.
   Supertime Envoy (`melee/pc/scripts/examples/envoy/`) is the fourth showcase and already exists: do not edit it; link it.
C. **Checks**: every demo and showcase passes `luac -p`; a Python test (`tools/port/test_demo_mods.py`) loads each
   `mod.json`, checks the entry exists, that every `gd.` function a demo calls appears in the engine's registration tables
   (parse `melee/pc/platform/gw_script*.c|inc` for registered names), and that each demo is in the index; a stub-`gd` smoke
   run of each demo's load and one frame where the existing test stubs make that practical.
D. A runner for the integrator: `tools/port/demo_tour.py` that launches the game on a chosen disc and walks the catalogue
   (load a demo, hold it N seconds, take a screenshot with `gd.screenshot`, unload, next) on the second monitor
   (`MELEE_WINDOW_X=-1080 MELEE_WINDOW_Y=-360`, width <= 1080; never hidden), writing a contact sheet and a pass/fail line
   per demo from the log (script errors = fail). You do not run it; the integrator does.
Report `_build/tmp/codex-demo-mods-report.md`: the catalogue table, APIs you found registered but undocumented or documented
but not registered (useful by itself), anything a demo could not show without an engine change, and how to run the tour.
