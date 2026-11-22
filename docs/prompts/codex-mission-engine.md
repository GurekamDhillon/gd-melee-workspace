# Codex packet A: engine support for mission folders (2026-10-03)

Workspace `<workspace>`; the game is the separate checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`). Both trees are deliberately dirty: do NOT commit, reset, stash, revert or reformat anything, and
do not touch files outside the list below. Code only: do NOT run `tools/port/build.sh`, do NOT launch the game. Two other
packets run at the same time on other files; stay inside yours.

Read first: `docs/superpowers/specs/2026-10-03-mission-folders-and-large-levels-design.md` (sections 2-4),
`_research/blender-to-game-level-loop-2026-10-03.md`, `_research/large-levels-and-maze-stitching-2026-10-03.md`,
`docs/scripting.md` ("Stage content", "Console and files", "Gameplay"), and the shim boundary rules in `melee/CLAUDE.md`
(game-side code is compiled for PowerPC and retargeted; scalars only across the boundary; floats as bit patterns).

## Files you own
`melee/pc/platform/gw_script.c` and its `gw_script_*.inc`, `melee/pc/platform/gw_mods.c` / `.h`,
`melee/pc/gameworld/script_model*.inc|h`, `melee/pc/gameworld/script_game.c`, `melee/pc/gameworld/script_arena.inc`,
`melee/pc/gameworld/script_lab.h`, `melee/pc/geno/geno_lab_mode.c` (only the fly range), new tests under
`melee/pc/tests/` and `melee/pc/platform/gw_script_*tests*.inc`, and `docs/scripting.md` (the sections for the functions you add).
Do NOT edit `melee/pc/geno/geno_game*.c|inc`, `melee/src/**`, any Lua under `melee/pc/scripts/`, or anything in `ports/`, `tools/`.

## What to build (this is the API contract the Lua packet codes against; keep these names and shapes exactly)
1. **Mod-relative file access** for scripts (spec E1):
   - `gd.mod_read(path)` -> `text` or `nil, err`. `path` is relative to the calling script's own mod folder, must begin with
     `missions/`, forward slashes only; refuse `..`, absolute paths, drive letters, backslashes and anything over 1 MiB.
   - `gd.mod_list(dir)` -> array of `{name=string, dir=bool}` sorted by name, same path rules; `nil, err` if it is not a directory.
   - `gd.mod_stamp(path)` -> an integer that changes when the file's content changes (size + modification time is enough), or `nil`.
   - Every model/asset loading function a script already has (find them: the map editor mod uses them) must accept a path that
     begins with `missions/` and resolve it under the calling script's mod folder, in addition to today's `models/` behaviour.
   Read-only, offline-safe, no new write access.
2. **Model assets keyed by content and freed** (spec E2): today assets are cached by path for the whole scene, never freed, cap 32
   ("model cache full (32 scene-pinned assets)"), so a re-exported file under the same name is ignored. Make the cache key the
   file's content (hash) plus path, free an asset when its last instance is removed, and raise the cap to at least 128 or size it
   from the pool. A changed file under the same name must load as a new asset. Keep existing callers working.
3. **Hide the host stage** (spec E3): `gd.stage_hide(bool)` -> bool. `true` stops drawing the host stage's own models and
   disables its collision for the rest of the match; `false` restores both. Owner-guarded like the other stage calls, restored at
   match end and on script unload, refused online. If only one of the two halves is safely possible, implement it and say so.
4. **Limits** (spec E7): `gd.fly_target` range from +/-10,000 to +/-49,000; the per-mesh collision-line limit from 32 to 64 if the
   pools allow (say what bounds it); correct `docs/scripting.md` where it says 128 instances / 200 lines (the code has 256 / 768).
5. **Reads for a traversal bot** (spec E8): extend the table `gd.player(port)` returns with `on_floor` (bool), `floor_y` (number or
   nil), `floor_passthrough` (bool: standing on a drop-through floor), `wall` (-1 left, 1 right, 0 none), `ceiling` (bool),
   `ledge` (bool: hanging), `jumps_left` (integer). Take them from the fighter's collision data (`coll_data.env_flags`, floor line
   flags) and jump counters; follow the existing LAB read pattern (an enum in `script_lab.h`, a case in `script_game.c`, a setter
   in `gw_script.c`).

## Acceptance (offline)
- Each addition has a native headless test in the existing style (`gw_tests_core.c` / the `*_tests.inc` files show how tests are
  registered; name them `script_mission_*`) covering the path rules (every refusal case), content-keyed reload of a changed
  asset, freeing on last instance removal, and the new player fields against a fake fighter where the existing tests do so.
- Game-side C must pass a PowerPC syntax check; you cannot run the compiler in your sandbox, so instead keep to the constructs
  already used in the files you edit and list in your report every new function, its file and line, for the integrator to check.
- No behaviour change for a script that does not call the new functions.

## Report
Write `_build/tmp/codex-mission-engine-report.md`: what you changed (file:line), the exact Lua signatures as implemented, anything
in the contract you could not meet and why, every assumption about engine behaviour you could not verify without running the game,
and a short native test plan for the integrator (what to run in the LAB and which log line shows each feature working). If
something is impossible as specified, stop and say so in the report instead of improvising a different API.
