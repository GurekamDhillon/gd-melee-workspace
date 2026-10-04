# Codex packet H: no hitches entering a room, and a fast start (engine) (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `docs/profiling.md`). Both trees are deliberately dirty: do NOT commit, reset, stash, revert
or reformat. Do NOT run `tools/port/build.sh`, do NOT launch the game. Keep every file compilable at every save. Lua jobs
are editing the missions and Envoy mods: do not touch them. Aurora changes go in `melee/extern/aurora` AND must be carried
as a patch under `_build/patches/` like `aurora-gd-surface-v1.patch` (say which file you added or extended).

The owner played a generated maze and said: "I did experience some hitching when enemies were loaded in a new section",
"CANNOT have that", and "also long start up time from versus match being started, and actually being put into the maze".
Target is 120 fps: 8.3 ms per frame. A lane measured it with the profiler; traces and drivers are under
`_build/audit-20261003/maze-hitch/` (`logs/`, `patches/`). Verify from code before designing.

## Measured causes
1. **600-760 ms stalls: render pipelines built synchronously on first draw.** First Goomba = 6 pipelines (~1.2 s over two
   frames), first Koopa = 4 (~0.75 s). Log line: `aurora::gfx::pipeline_cache: pipeline wait: draw blocked N ms on pipeline
   <hash> (built inline) - not covered by any warm-up` (`melee/extern/aurora/lib/gfx/pipeline_cache.cpp` ~1395-1408). Not in
   `_build/initial_pipeline_cache.db`, not queued by `gw_Gfx_PrewarmMustDraw` (`gw_runtime.c` ~3205-3215, logs `prewarm 0
   must-draw`), not covered by the loading hold (`src/melee/gm/gmscene.c` ~300-377, ~520-551). A second launch in the same
   sandbox has no stall (a per-sandbox cache). Spawning itself is 1-3 ms; the disc read is under 1 ms.
2. **20-44 ms frames: chunk installs.** `gd.area_load` (`pc/platform/gw_script_largemap.inc` ~61) plus `l_stage_add_line`
   (`gw_script.c` ~5692, ~0.2 ms per line, ~18 lines and 6 model instances per chunk) is 7-10 ms per chunk and atomic from
   Lua; unload is 8-15 ms. Lua is being changed to do one per frame, which still leaves 11-14.5 ms of work per crossing.
3. **Start-up: the loading hold always runs to its 10 s ceiling.** Release needs `Gfx_SeedPipelinesBuilt() >=
   Gfx_SeedCoreCount()` (`gmscene.c` ~538-545) but only 3 of 143 (cold) or 82 of 153 (warm) are built in time, so every
   launch waits the full ceiling (`gmscene.c` ~377, ~551). Boot to playable is ~15 s; the maze itself is 0.6 s.
4. No way to start a mission from launch: `MELEE_SCENE` has no mission keyword and there is no mod autostart, so the
   player sees the host stage first.

## Build
A. **Never build a pipeline inline during play when it could have been known.** A general mechanism, not a Goomba special
   case: (1) a call to declare "these will be drawn" ahead of time: `gd.warm{enemies={...}, items={...}, models={...},
   fighters={...}}` -> a handle with progress, which builds the needed pipelines on the background compile path WITHOUT
   drawing anything on screen and without blocking the game thread (find how a pipeline key is derived from a model's
   materials and make that derivable without a visible draw; if a hidden off-screen draw is the only way, do that);
   `gd.warm_done(handle)`; (2) learned coverage: every pipeline built inline is recorded with what triggered it into a
   persistent cache keyed by content so the next launch pre-builds it; state why the existing per-sandbox cache does not
   carry across sandboxes and fix that for user installs; (3) extend the seed tooling
   (`tools/port/build_pipeline_seed.py`) so a sweep that spawns every enemy kind, every item kind and every stage adds
   them, and report what to run; (4) when an inline build is unavoidable, do not block the game thread for hundreds of
   ms: skip that draw for the frames it takes (the object appears a few frames late) under a setting, default on for
   non-fighter objects; keep the log line and count them in the profiler.
B. **Chunk install under budget.** Make `gd.area_load`/`area_unload` and collision-line edits cheap enough that one chunk
   costs well under 4 ms on the game thread: batch the line adds (one rebuild of the collision tables per install, not
   per line), prepare model instances ahead in a `prepare` step Lua can call early and an `activate` step that is O(1),
   and the same for unload (deferred free). Give Lua `gd.area_prepare(name)` / `gd.area_activate(handle)` / status,
   keeping `gd.area_load` working. Snapshot/rewind exactness must hold (the existing rewind fixtures); say how.
C. **Start-up.** Find why core seed pipelines are not built within the hold and fix the cause (start the seed build at
   boot rather than at scene load, more compile workers, a smaller true core, ordering by what the first scene draws),
   so the hold releases on readiness in a few seconds instead of always at the ceiling. Do not just lower the ceiling.
D. **Launch straight into a mission.** A scene keyword (`mission=<folder>` / `maze=<seed>,<size>`) and a mod autostart
   declaration, so the level is requested during loading, the host stage is never shown, and the loading hold covers
   staging and `gd.warm`. The Lua side will retry on an unsafe CPU (their bug); you provide the hook and the ordering.
E. Profiler gaps the lane hit: hitch traces should name the game event that caused them (last script call, spawn, area
   load); the event ring overflowed (`event_overwrites` 578,638, `detail_overflow` 56,831); `gd.perf(1)` costs ~4.5 ms per
   call: make it cheap or document a cheap alternative; add frame number and milliseconds to game log lines.
Tests in the suite pattern for each; `docs/scripting.md` and `docs/profiling.md` updated; a catalogue demo for `gd.warm`
(project rule: each capability ships a single-feature demo). Report `_build/tmp/codex-no-hitch-engine-report.md`:
signatures, file:line, whether Aurora must be rebuilt, the patch file, and a native test plan with the exact numbers a
tester should see (no `pipeline wait` lines in a cold-sandbox walk of maze seed 7; worst frame per room entry; hold time).
Do not stop to ask for design approval: the integrator has approved this packet; record your choices in the report.
