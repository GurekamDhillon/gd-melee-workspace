# Blender to game level loop: spike, 2026-10-03

Question: how fast and smooth can "edit the level in Blender, see and play it in the running game" be made with
what exists today, and what must be added? Method: a throwaway Blender level and exporter, a throwaway sandbox mod
(the tracked map editor `main.lua` copied unmodified, a probe appended to the copy), run on the VANILLA disc in the
LAB (Falco, FD), driven over the console socket. No tracked file was touched; no build.

**Throwaway code, all under `_build/spikes/blender-loop/`** (not to be kept as is): `tools/make_level_blend.py`
(imports the 23 kit `.gxmesh` into Blender, builds `level.blend`), `tools/export_mission.py` (scene walker, writes the
mission folder, optional `--merge=<name>`), `tools/edit.py` (scripted "author edits"), `tools/change.sh` (edit,
export, install, timed), `tools/probe.lua` + `tools/pre.lua` (probe appended to the editor copy), `tools/driver.py`
+ `s_*.py` (socket driver and scenarios), `tools/assemble.sh`, `tools/run_game.sh`. Logs: `run<N>-driver.log` (the
timings), `_build/runs/bl-run<N>/melee-pc.log`. Sandbox names (game runs): `bl-run1`, `bl-run2`, `bl-run3`
(aborted: exporter bug), `bl-run4`, `bl-run5`, `bl-run6` (never launched), `bl-run7`, `bl-run8`. Screenshots:
`run2/data/map_editor_main/loop_*.png`, `run5/.../merged.png`.

## Verdict

The loop is already fast: save in Blender to playable in the running game takes about **1.1 to 1.2 s**, of which the
game side is 0.05 s (pushed over the console socket) or about 0.2 s (file watcher). It needs no match restart. What
is missing is not speed but plumbing: a mission folder the game can load from one place, a reload command that
survives bad input, and a catalog/cache that does not assume a fixed kit.

## What was built and run

- Blender level: 9 kit parts as linked duplicates of imported kit meshes (custom property `kit_part`), marker empties
  (`START`, `ENEMY_<kind>_<wave>`, `CHECKPOINT`, `GOAL`; zone size = empty scale), objective on scene properties.
  Coordinates: 1 Blender unit = 1 kit metre; game X = Blender X, game Y = Blender Z, game Z (visual depth) = -Blender Y;
  x6.5 for game units; `rot` = atan2 of the object's local X axis in the XZ plane.
- Exporter output (the "mission folder"): `level.lua` (layout v2 + `mission` table, exactly the format `map play`
  loads), `models/` with only the used `.gxmesh`, `.coll.json` and the shared atlas. A 9-part level exports 6 files.
- Game: the level was played start, goomba, checkpoint, koopa, goal and finished `mission: complete`.

## Timings (seconds, wall clock, this machine)

| Stage | geometry change (lift a floor) | marker change (move enemy) | new part types (stairs, wall, extra floors) |
|---|---|---|---|
| Blender: open + edit + save (scripted stand-in for the author) | 0.54 | 0.61 | 0.52 |
| Blender: open + export mission folder | 0.51 | 0.50 | 0.58 |
| Install into the game's folders (copy changed files, atomic rename of the layout last) | 0.03 | 0.03 | 0.06 (first ever install with models: 0.45) |
| Export done to the reload command returning (socket push) | 0.045 | 0.034 | n/a |
| Export done to level live and mission running, socket push | **0.060** | **0.050** | n/a |
| Export done to level live and mission running, in-game file watcher (poll every 15 frames) | n/a | n/a | **0.188** (two new models loaded in that time) |
| Whole author loop, save to playable (export + install + reload) | **about 0.6** | **about 0.6** | **about 0.8** |

Notes on the numbers. The author-side "edit" step is my script, so a real author's cost is "save .blend" (instant) +
export; the 0.5 s is mostly Blender process start. Two measurements of "rotmirror" through the watcher (0.125 s) were a
FAILED load and are not in the table. Frame counts: the sample level completes in about 574 logic frames (9.6 s) with
real walking; with the fly cursor, 5.0 to 5.5 s wall.

## What survives a reload (`map play live.lua` while a mission is running)

Nothing of the run survives, by design of the existing command: parts are all despawned and respawned with new ids,
`mission: aborted (restart)` is logged, the mission restarts from wave 1, enemies respawn, P1 is teleported to the
start (`P1=(-52.6,30)` before, `(-120,40)` after), checkpoint and deaths and time reset. The match, the fighter, the
camera and the loaded model assets are kept. Reload while the fly-cursor bot was mid-run recovered by itself (it
re-targeted the respawned enemies and completed).

Failure behaviour: a refused layout is atomic. The previous level stays loaded and the mission keeps running
(seen with the mirrored-collision and unknown-part cases). One exception: if P1 is dead or respawning at reload,
the layout loads but `Mission not started: gd.teleport: that fighter's state cannot fly` and no mission runs
(run=false) until the next reload.

## What worked

- Geometry, marker and new-part changes with the same reload command, no restart. Partial effects none.
- Rotation (ramp at 15 degrees, floor_2m at 15 degrees scaled 1.5) loaded; the fly-cursor "place" onto the rotated
  ramp landed at y=58.4 (ramp origin y=56): collision rotates with the part. Mirror (negative scale) works for a part
  without collision.
- Screenshots (read): `loop_a_start.png` shows the kit floor strip in place with the textured dashed edge, Falco on
  it, a goomba on it, no gaps, scale matching the fighters (floor 26 units is about 4 fighter heights wide).
  `loop_c_newpart.png` shows the strip continuing and a railed ramp/stairs rising to the right. `merged.png` (one
  merged mesh) is visually identical to the 9-part version. In all of them the original FD stage is still drawn and
  solid below the level (the kit level floats at y=30 above FD's slab at y=0): the level does not replace the stage.
  `loop_d_rotmirror.png` was taken during a refused load and not judged.
- Merged section mesh: a Python merge over the exported kit `.gxmesh` files (transform vertices, concatenate indices,
  transform collision lines, sidecar names the shared `bf_kit` atlas) gives one `sec_0.gxmesh` (2340 triangles,
  collision=9). It loads, draws identically, the fly-cursor "place" lands on it (y=30 on the floor, 43 on the upper
  floor), and the mission completed on it (5.0 s). So per-section export is possible with the existing model format
  and without Blender's bake (reusing the kit atlas UVs). No new textures: a section can only use kit textures.

## What failed, and the walls (with log lines)

1. **Layout and models cannot live in one folder.** `gd.data_read` is confined to `scripts-data/<script id>/` (plain
   names; one level of subfolder is allowed by `gs_data_path`, but the editor's `file_name()` accepts only
   `^[%w_-]+%.lua$`). Models load only from the mod's own `models/` (`gs_stage_model_open`: entry dir and one parent), or
   from another mounted mod as `<modid>/<path>`. Measured: `map play ../x.lua`, `sub/level.lua`, `C:/x.lua` all give
   `use a plain filename such as layout.lua`. So today the "folder" is two places: the layout in `scripts-data/map_editor_main/`
   and the models in `mods/map_editor/models/`. My installer wrote both.
2. **The part catalog is hard-coded.** `validate()` rejects any part not in the PALETTE block generated into
   `main.lua`: `map_editor/main:768: unknown kit part` (tested with a copy of a real mesh named `bf_custom_pillar`). A
   level with its own meshes (merged sections, new art) is refused until the catalog is edited; I worked around it in
   the sandbox copy by adding to the `known` table from the probe.
3. **Model assets are cached by path for the whole scene, never freed.** Replacing `bf_floor_4m.gxmesh` on disk and
   reloading logs no new `loaded` line (count stayed 1) and the old mesh is used (`gs_model_open_at` returns the cached slot).
   So a re-exported merged section with the same name is ignored until a new match; a new name works but each one pins
   a slot: `GS_STAGE_MODELS = SCRIPT_MESH_ASSETS = 32` assets, 64 MiB (`model cache full (32 scene-pinned assets); start a
   new scene`). Measured (run8): re-exporting a section under a new name each time, the 29th new name failed with `map_editor/main:625: model cache full (32 scene-pinned assets); start a new scene` (4 slots were already used by kit parts and one earlier section). Iteration cost stayed about 0.9 s each until then; the failed load left the previous level running. Kit parts are
   immune (their files never change); per-level section meshes are not.
4. **Instance limit.** 149 parts: `map_editor/main:762: invalid part index` (the editor's `MAX_PARTS=128`; the message
   does not say "model limit"; the layout is refused whole, old level kept). The engine pool is 256 instances
   (`SCRIPT_MESH_INSTANCES`), shared with other scripts.
5. **Collision lines: the 200 in the docs is stale for models.** 119 parts (110 `bf_floor_opening_4m`, 2 lines each, +9 base,
   about 229 lines) loaded with no error, and landing on parts at the highest x confirmed collision (y=132 as expected).
   The code has `SCRIPT_STAGE_LINES 768` and `SCRIPT_STAGE_JOINTS 1024` (script_game.c); the 200 applies to
   `gd.stage_add_line`. Not driven to failure (128 parts of 2 lines is only 256).
6. **Per-instance limit 32 lines, sidecar 16 KiB.** A merged section with 39 collision lines:
   `map_editor/main:625: invalid model collision sidecar: ...sec_t1.coll.json` (limit `SCRIPT_MESH_LINES 32`). Sections
   must be 32 collision lines or fewer.
7. **Vertex limit.** GXMS indices are 16 bit: merging 109 floors fails in the exporter `54972 verts / 77820 indices (limit
   65535)`; about 85 floor-sized parts per section at most.
8. **Mirroring a part that owns collision is refused:** `map_editor/main:673: model transform reverses collision kind or
   exceeds world bounds` (mirrored ramp, collision on). Visual-only mirror is fine, so the exporter should mirror with
   `collision=false` plus a separately authored part, or the add-on should refuse.
9. **Units.** The layout must say `units=6.5` and equals the kit's `UNIT = 5 x KIT_SCALE (1.3)`; any other value is
   `kit scale differs`. An author must know: 1 m = 6.5 units; a floor part's origin is the centre of its top line;
   Blender Y is depth and points away from the camera (game +Z is toward it); positions are absolute game coordinates
   on top of the host stage (FD slab at y=0 is still solid, blast zone and camera are FD's unless the layout carries
   bounds; `stage_isolate` was not tried); spawn y of the start is feet height, zones test the feet.
10. Smaller: a failed reload still looks like success to anything that only checks the command result (the editor logs the
    error to the script log and a toast; the console reply carried it in my runs, `>>> ok` regardless), so a tool must read
    the lines. `map play` while P1 is dead leaves no mission. The console `probe`-style commands are the only way to hit
    a script's locals; the stock editor has `map play/load/mission play` and nothing for watching a file.

## What a good loop needs (where, size)

| # | Item | Where | Size |
|---|---|---|---|
| 1 | One-folder mission loader: `mission load <folder>` reads `level.lua` and models from a folder inside the mod or a data subfolder; models resolved relative to it (a `gd.model_load` that accepts a path under the script's data dir, or loading from `<modid>/models` with a mission mod) | engine C (path rules in `gs_model_open`, `gs_data_path`) + game Lua | M |
| 2 | Catalog from the folder instead of the PALETTE block: `validate()` accepts any part whose `.gxmesh` exists in the mission folder | game Lua (editor or a new mission runtime) | S |
| 3 | `mission reload` that is atomic, keeps the old level on any error and reports errors in the command reply; optional "keep the player position / start mid-level at a marker" (play from here) | game Lua | S |
| 4 | File watcher: poll the folder's manifest/stamp every ~15 frames and reload (measured 0.19 s end to end) | game Lua (done in the probe: about 10 lines) | S |
| 5 | Content-addressed model names (`sec_<hash>`) written by the exporter so re-exports never hit the path cache; plus asset release or a larger or evictable asset pool | Blender add-on (names) now; engine C (`gs_model_open_at` eviction, 32-slot cap) later | S now, M for eviction |
| 6 | Blender add-on: kit library, marker types as real objects with constraints, zone gizmos, validator (118/128 parts, 32 lines per section, 65535 indices, mirrored collision, goal unreachable by checks, markers inside bounds), "Export mission" button and "send to running game" (write folder, ping the console socket) | Blender add-on | L |
| 7 | Section merge in the exporter (the `--merge` function, grouping by section collection, split at 32 lines / 65535 indices, reuse of kit atlas) | Blender add-on (Python, no bake) | M |
| 8 | Custom-art path: baking a level-specific atlas for non-kit meshes (the existing bake is a Cycles pass over the kit, slow) | Blender add-on | L |
| 9 | Bounds and spawns from markers; replace or hide the FD slab (`gd.stage_isolate`) | exporter + game Lua | S |
| 10 | Runtime for more than one section: unload and load sections as the player moves (maze chunks, large maps), within 32 assets and 128 instances | engine C + game Lua | L |
| 11 | Doc fix: 200 lines vs 768 and the models' real limits | docs | S |

## Recommendation

- Mission folder: `missions/<name>/{mission.json or level.lua, models/*.gxmesh|.coll.json|atlas}` inside a mod, one
  `level.lua` in the format that exists today (so the editor can still open it), models named by content hash for any
  non-kit mesh. The runtime loads the folder as a unit; the editor stays a nudge tool.
- Reload: a game-side file watcher on `level.lua` (poll every 15 frames, `data_read`, compare, load atomically; 0.19 s
  measured) plus the same entry point on the console socket (`mission reload`, 0.05 s) for the add-on's "send to
  game" button. The add-on must write the models first and the layout last, atomically (rename), as `change.sh` does.
- Author in Blender as parts first (instances of kit parts; 128 and 32-line limits visible in the validator); merge
  into sections only when a level needs more than 128 parts, with content-hash names.
- Treat a reload as a restart of the mission, not as a patch of the live run (it is one today); add "play from marker"
  so iterating on a late room does not cost a walk from the start.
- Before the spec: get the owner to try the loop with a controller (fly-cursor and scripted input proved the
  geometry and collision; feel was not judged).

## What used the fly cursor and what used real movement

Fly cursor (a fixture): the completion runs after the reload checks (`flybot`: fly_target to the nearest enemy with
fly_attack, then checkpoint, then goal; 5.0 to 5.5 s), all "place onto the floor" collision checks (base floor, 119-part
level, rotated ramp, merged section), and the mid-run reload recovery. Real movement: the first completion (run2, a
scripted pad bot: walk right, tap A near enemies; 9.6 s) and the three reloads in that run. Note the first fly bot attempt
used damage 50 (out of 1..30) and errored; it was fixed before the reported runs.

## Remaining measurements, closed in run8 and what is still open

- Closed: the asset cap (above); a merged section under a fresh name end to end (export, load, mission completed with the fly cursor in 5.9 s wall).
- Rotation and mirror visuals were NOT judged: `rot.png` and `mirror_visual.png` were taken at the start camera and the rotated parts are off screen at the right. Rotated collision is verified (landing y=58.4); visual-only mirror loaded without error.
- Still open: collision lines past 768 / joints past 1024 (a level of about 24 merged 32-line sections), and 128 instances plus the host stage's own lines.
