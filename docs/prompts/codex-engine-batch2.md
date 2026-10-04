# Codex packet F: engine batch 2 for missions and Envoy (2026-10-03)

Workspace `<workspace>`; the game is the separate checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `melee/pc/geno/CLAUDE.md`, `docs/scripting.md`). Both trees are deliberately dirty: do NOT
commit, reset, stash, revert or reformat anything. Do NOT run `tools/port/build.sh` and do NOT launch the game (the integrator
builds and tests). Keep every file compilable at every save. Do not edit `melee/src/melee/gm/gmfrontend*`,
`melee/src/sysdolphin/`, the missions mod or the envoy mod. The current tree builds clean and passes 227/227 native tests.
Credit: record in your report whose work each idea comes from (see `CREDITS.md`); consult, never copy, third-party code.

Do the three parts in this order; each is independently useful, each gets headless tests in the suite's existing pattern
(`melee/pc/platform/gw_script_*_tests.inc`, fake-fighter fixtures) written before the code, a log line for anything observable,
and its section in `docs/scripting.md`. Root causes only. Everything must be refused online exactly as other gameplay writes
are, and cleaned up on script unload, match end and scene change.

## Part 1: camera parameters for custom levels (small)
Evidence: `_research/camera-for-large-levels-2026-10-03.md`; design: section 8 (E9, E10) of
`docs/superpowers/specs/2026-10-03-mission-folders-and-large-levels-design.md`.
- `gd.camera_params{min_dist=, max_depth=, fov=, fixed_zoom=, track_smooth=, track_ratio=, tilt=, pan=, yaw_gain=, pitch_gain=}`
  writing the stage's camera info (fields in `melee/src/melee/gr/ground.c` ~2689-2740 and their users in `cm/camera.c`), any
  subset, validated ranges, returns the previous values; `gd.camera_params(nil)` restores the stage's own. Zero yaw/pitch gains
  must remove the origin-distance skew the note describes. Restored automatically on unload.
- Remove the per-call `gw_log` line and the LAB-timeline fork on `gd.stage_set_origin` / `gd.stage_set_camera_bounds`, which
  scripts now call every frame (log only on change of state, or once).
- Hard rule: never touch the C-stick path; custom modes keep C-stick attacks (the 1P-mode gate is `gm_IsCurrently1PMode`).

## Part 2: passive fighter modifiers (medium)
Requested by the Envoy slice (`_build/tmp/codex-envoy-slice1-report.md`, "Boss and engine requests" item 1; spec
`docs/superpowers/specs/2026-10-03-supertime-envoy-design.md` section 4).
- `gd.fighter_mod(port, {damage_dealt=, damage_taken=, run_speed=, air_speed=, shield_max=})`: script-owned, reversible
  multipliers (1.0 = unchanged; validated, clamped ranges that you state), returning a handle or replacing the port's set;
  `gd.fighter_mod(port, nil)` clears. They must survive respawn and character state changes, apply to ported/Geno fighters
  as well as vanilla, never stack accidentally on reload, and leave the fighter exactly as it was when cleared (prove with a
  test that applies, clears and compares the attribute bytes).
- Find the right hook for each: prefer the game's own existing ratios where they exist (attack/defense ratios in the
  player/start data are real vanilla mechanisms) over patching attribute tables; say which mechanism you used for each and why.
- Deterministic and snapshot-safe: state lives where the LAB savestate/rewind captures it, or is re-derived each frame from
  script-owned data; say which.

## Part 3: reserve fighters, benched and called (medium to large)
Evidence and credit: `_research/tagfighter-insights-2026-10-03.md` (the bench/unbench recipe and its traps are Joyastick's
findings in MeleeVS; ideas only, their mod code is unlicensed, do not copy it). Our starting points: `ScriptGame_CpuMode`,
`fly_refused` in `melee/pc/geno/geno_lab_mode.c`, `gd.teleport`, the LAB's scene launch (`_research/scene-launch.md`).
- `gd.fighter_bench(port)` / `gd.fighter_call(port, x, y, {facing=, intangible_frames=})` / `gd.fighter_benched(port)`:
  bench = frozen, invisible, intangible, no AI/input, excluded from the camera, cannot lose a stock, re-asserted every frame;
  call = clean wait state, placed with proper floor/air handling at the target, camera box re-seeded, stale velocity/input
  cleared. Refuse (return `false, reason`) in the states where it is unsafe (grabbed/grabbing, thrown, dead/respawning,
  sub-fighter and transformation halves handled together: Nana, Zelda/Sheik) and list them.
- Six player slots: the game has `Gm_Player_NumMax` = 6 and Multi-Man Melee runs one human against five recycled enemies
  (`melee/src/melee/gm/gmmultiman.c:597-607`). Establish from the code what stops OUR scene launch and LAB from starting a
  match with slots 5 and 6 filled (HUD, camera, start data `players[4]` versus `[6]`, CSS data), and either enable it behind
  the scene option (e.g. `p5=`, `p6=`) if the change is contained, or report exactly what it takes. Do not enlarge any table
  beyond six.
- Rollback: keep all bench state where the snapshot captures it.

## Report
`_build/tmp/codex-engine-batch2-report.md`: signatures, file:line of every new function, mechanism chosen per modifier, the
refused-state list, the six-slot findings, tests added, unverified assumptions, credits, and an exact native test plan for the
integrator (console/Lua snippets and the log lines or measurements that prove each part).
