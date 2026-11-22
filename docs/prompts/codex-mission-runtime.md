# Codex packet B: the mission runtime as its own module (2026-10-03)

Workspace `<workspace>`; the game is the separate checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`).
Both trees are deliberately dirty: do NOT commit, reset, stash, revert or reformat anything, and do not touch files outside the
list below. Lua and Python only: do NOT edit C, do NOT run `tools/port/build.sh`, do NOT launch the game. Two other packets run
at the same time (engine C; a Blender exporter); stay inside your files.

Read first: `docs/superpowers/specs/2026-10-03-mission-folders-and-large-levels-design.md` (sections 3, 5, 6, 7),
`_research/blender-to-game-level-loop-2026-10-03.md`, `_research/large-levels-and-maze-stitching-2026-10-03.md` (the chunk manager
and the streaming calls `gd.area_load` / `gd.area_unload` it measured), `docs/scripting.md`, and the existing code you are
extracting from: `melee/pc/scripts/examples/map_editor/` (`scripts/mission.lua` the pure state machine, `scripts/main.lua` the
glue around `mission_*`, README "Missions", `samples/`), with its tests `melee/pc/tests/map_mission_test.lua`,
`melee/pc/tests/map_editor_test.lua` and `tools/port/test_map_mission.py`, `tools/port/map_mission_sync.py`.

## Files you own
New mod `melee/pc/scripts/examples/missions/` (`mod.json`, `scripts/*.lua`, `README.md`, `missions/first/` sample folder), new
tests `melee/pc/tests/missions_*.lua`, a Python wrapper `tools/port/test_missions.py`, and a bundler `tools/port/missions_bundle.py`
if the mod needs its modules concatenated into one entry script (the engine loads ONE entry file per mod and has no `require`;
`tools/port/map_mission_sync.py` and `tools/roguelite/prepare.py` show the two existing ways). You may read but must NOT edit the
map editor mod, its tests, or anything under `ports/`, `melee/pc/geno/`, `melee/pc/platform/`, `melee/pc/gameworld/`.

## The engine API you code against (another packet implements it; treat it as given, stub it in tests)
- `gd.mod_read(path)` -> text | nil, err; `gd.mod_list(dir)` -> {{name=, dir=}} | nil, err; `gd.mod_stamp(path)` -> integer | nil.
  Paths are relative to this mod's folder and begin with `missions/`.
- Model/asset loading accepts paths beginning with `missions/`.
- `gd.stage_hide(bool)` hides the host stage's models and collision.
- `gd.player(port)` additionally has `on_floor`, `floor_y`, `floor_passthrough`, `wall`, `ceiling`, `ledge`, `jumps_left`.
- Everything else is the existing API in `docs/scripting.md` (enemies, `stage_set_spawn`, bounds, `fly`, `fly_target`,
  `fly_attack`, `area_load`/`area_unload` - check exact names in `melee/pc/platform/gw_script.c` registration tables).

## What to build
1. **A standalone missions mod** that loads a mission FOLDER `missions/<name>/` (`level.lua`, `mission.lua`, `models/`, optional
   `chunks/<id>/`): validates both files in an empty environment before changing anything (reuse the editor's validation rules;
   a `mission` table inside `level.lua` still loads), builds the part catalogue from the folder's `models/` (no hard-coded
   palette), places the parts with collision, applies camera bounds, blast zones and spawns from the level, hides the host stage,
   and runs the mission with the existing pure state machine (copy `mission.lua` unchanged as a module; do not fork its logic).
   Small files with one job each (loader, validator, world builder, chunk manager, mission glue, test commands, HUD); no file over
   ~400 lines; keep top-level locals well under Lua's 200 limit.
2. **Chunk streaming** for large levels: chunks declare a rectangle; keep the 3x3 neighbourhood of the player's chunk loaded with
   `area_load` / `area_unload`; each chunk has its own spawn point so a KO respawns in the chunk the player was in.
3. **Reload:** poll `gd.mod_stamp` of `level.lua` and `mission.lua` every 15 frames and reload atomically (a refused folder
   leaves the running level untouched); console command `mission reload`.
4. **Play from a marker:** `mission play <name>`, `mission play <name> from <marker>` (state as if the mission had reached that
   marker: earlier waves cleared, checkpoint set), `mission stop`, `mission restart`, `mission list`.
5. **Fly-based test commands** (first-class, the owner's requirement): `mission fly next|prev`, `mission fly <marker>`,
   `mission clear` (defeat the current wave with `gd.fly_attack`), `mission drop` (`gd.fly(port,"place")` then normal control),
   `mission tour` (visit every marker and chunk in order, log one line each: what loaded, how long, any refusal).
6. A sample `missions/first/` built from the kit part names in `melee/pc/scripts/examples/map_editor/samples/` (models are NOT in
   the repo: the sample's `models/` stays empty with a README line saying the Blender exporter fills it; tests stub model loading).

## Acceptance (offline)
- `lua melee/pc/tests/missions_*.lua` and `python -m unittest discover -s tools/port -p "test_missions.py"` pass, with a stub `gd`
  (extend the pattern in `map_editor_test.lua`): folder loading and every validation refusal, catalogue from folder, chunk
  window as the player crosses chunk borders (loads/unloads counted), respawn point per chunk, reload on stamp change and
  atomic refusal, play-from-marker state, each fly command, cleanup on match end / unload. Write each test before the code.
- The existing suites still pass untouched: `lua pc/tests/map_mission_test.lua`, `lua pc/tests/map_editor_test.lua` (run from
  `melee/`), `python -m unittest discover -s tools/port -p "test_*.py"`.
- `luac -p` on every Lua file (Lua 5.4 is on PATH).

## Report
Write `_build/tmp/codex-mission-runtime-report.md`: the module list with one line each, the folder schema as implemented, every
console command, the engine calls you rely on (name + the registration line you checked, and which are stubbed because the other
packet adds them), test names and counts, anything you could not do, and a native test plan for the integrator (exact console
commands and the log lines that prove each feature). Do not claim anything works in the game; you did not run it.
