# Codex packet C: Blender mission exporter and kit collision (2026-10-03)

Workspace `<workspace>`; the game is the separate checkout `melee/` (read `CLAUDE.md`, `tools/CLAUDE.md`).
Both trees are deliberately dirty: do NOT commit, reset, stash, revert or reformat anything, and do not touch files outside the
list below. Python only: do NOT edit C or Lua, do NOT run `tools/port/build.sh`, do NOT launch the game. Two other packets run at
the same time (engine C; the Lua mission runtime); stay inside your files. This is exporter CODE: do not model, texture or
restyle any art.

Read first: `docs/superpowers/specs/2026-10-03-mission-folders-and-large-levels-design.md` (sections 3, 9),
`_research/blender-to-game-level-loop-2026-10-03.md` (what the throwaway exporter did, the limits it hit, its recommendation) and
its throwaway code `_build/spikes/blender-loop/tools/` (reference only: reimplement cleanly, do not import from `_build`),
`_research/large-levels-and-maze-stitching-2026-10-03.md` (the chunk format and the finding that the kit has floor collision only),
the kit exporter `melee/pc/assets_src/bf_interior/export_kit.py` and `bf_interior_playset.py`, `tools/blender/README.md`, and the
layout/mission schema in `melee/pc/scripts/examples/map_editor/README.md` ("Layout files", "Missions").
Blender is at `experiment/tooling/ultimate/apps/Blender/blender-5.1.2-windows-x64/blender.exe` (run headless:
`blender.exe --factory-startup --background --python <script> -- <args>`).

## Files you own
New add-on package `tools/blender/gd_mission/` (`__init__.py`, small modules with one job each), its tests
`tools/blender/test_gd_mission.py` (pure-Python parts run under plain `python -m unittest`; Blender-dependent parts run headless
through a helper and skip cleanly if `blender.exe` is missing), `tools/blender/README.md` (a new "Mission exporter" section), and
`melee/pc/assets_src/bf_interior/export_kit.py` for item 4 only. Nothing else.

## What to build
1. **Scene conventions** (document them in the README): kit parts are objects whose name or custom property gives the part name
   (instances of the kit's meshes); mission markers are empties with a `gd_marker` custom property (`start`, `enemy` with
   `kind` and `wave`, `checkpoint`, `goal`, `trigger` with its action, `wave` rules) whose scale gives a zone's width/height;
   camera bounds and blast zones are rectangles (empties or mesh planes) tagged `gd_bounds=camera|blast`; chunks are rectangles
   tagged `gd_chunk=<id>`. Blender is Z-up in metres; the game plane is X right, Y up, with `units=6.5` game units per kit metre
   (the spike note records the mapping it used and verified: follow it and state it).
2. **Export mission** -> a mission folder `missions/<name>/` with `level.lua`, `mission.lua`, `models/` (only the models used),
   and `chunks/<id>/` when chunk rectangles exist (parts assigned to the chunk containing their origin). Write models first and
   the two Lua files last, each to a temporary name then renamed, so a reader never sees a half-written folder. Non-kit meshes
   are named by content hash. Lua is emitted as data (`return {...}`), deterministic ordering, numbers rounded to 4 places.
3. **Validate** before writing (and as its own command): part and collision-line budgets (128 parts without sections; per mesh
   at most 32 collision lines and 65,535 indices - take the limits from one constants module so the engine packet's raised limits
   can be dropped in), markers outside the level bounds, a mission that is not playable by the runtime's rule (start + objective;
   `reach_goal` needs a goal; `defeat_all` needs an enemy; `defeat_then_goal` needs both), overlapping chunk rectangles,
   unknown enemy kinds (the seven: goomba, koopa, redead, like_like, octorok, polar_bear, topi), mirrored parts that own
   collision (the engine refuses them). Errors name the object.
4. **Kit wall, ceiling and door-frame collision:** `export_kit.py` writes floor lines only. Add wall (`left_wall`/`right_wall`)
   and ceiling lines for the solid wall, corner, doorway and window parts and the underside of floors where the note says a
   ceiling is needed, following the line conventions and winding the large-levels note records (floors one-sided, left edge
   `right_wall` top to bottom, right edge `left_wall` bottom to top, ceiling right to left, door openings left out), keeping
   every part within 32 lines. Existing floor output must be byte-identical for parts you do not change.
5. **Send to game:** an operator that, after export, sends `mission reload` to the running game over the console socket
   (`melee/pc/scripts/console.py` shows the protocol; port from `MELEE_CONSOLE_PORT`). Fail quietly with a message if no game is
   listening.
6. A panel with: mission name, output mod folder, Validate, Export, Export and send. Plain; no custom drawing.

## Acceptance (offline)
- `python -m unittest tools/blender/test_gd_mission.py` passes: Lua emission (round-trip through `lua` on PATH: the emitted files
  load and equal the input), coordinate mapping, chunk assignment, each validator rule, atomic write order, content-hash naming.
  Write each test before the code.
- A headless Blender test builds a small scene in memory (a strip of floors, a ramp, a wall, markers, two chunk rectangles),
  exports it to a temp directory and checks the folder's contents; and one re-exports the kit to a temp directory and asserts the
  floor lines of unchanged parts are identical to before while wall/ceiling lines now exist for the wall parts.
- Do not write into `melee/pc/scripts/examples/`, `_build/agents/` or any mod folder; tests use temp directories.

## Report
Write `_build/tmp/codex-mission-blender-report.md`: the add-on's modules with one line each, the scene conventions, the
coordinate mapping with the numbers, the folder layout as written, validator rules, the collision lines added per kit part
(a table: part, floor/wall/ceiling line counts), test names and counts, anything you could not do or could not verify without
running the game (collision winding is the obvious one: say exactly what the integrator should test), and how to install the
add-on in Blender.
