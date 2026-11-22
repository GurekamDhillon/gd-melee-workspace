# Packet F follow-up: engine batch 2 after in-game runs (2026-10-03)

Measured in the game (vanilla disc, LAB, CPU in stand mode). Evidence: `_build/audit-20261003/batch2-verify/` (probe
`mods/b2v/scripts/main.lua`, `patches/`, logs `_build/runs/b2v-*`). Same rules as before (no commits/reset, no build, no game,
keep files compilable). Other finished work is in the tree: contact events, shaders, clank event (`script_clank*.inc`,
`gw_script_clank*.inc`), controls remap: do not disturb it.

Confirmed working: camera params (min_dist, fov, fixed_zoom, track_ratio, zero gains remove the skew, nil restores to 1e-4,
unload restores, no log flood, C-stick still attacks); fighter_mod damage dealt/taken (exact ratios, combined applies once),
run_speed 0.5, air_speed 1.5, shield_max, KO/respawn persistence, exact restore, no stacking; bench (invisible, no hurtbox,
no AI, camera excluded, cannot die), air call, refusals for hitlag/hitstun/grab.

Fix at the root, each with a test:
1. **`gd.fighter_call` on the floor does not arrive in Wait.** It arrives in Fall (action 29), sinks below the floor (y 0 ->
   -3.45, Ice Climbers/Zelda about -2.1) for ~5 frames, then Landing (42) for ~30 frames, then Wait. The floor probe finds the
   floor (y snaps to 0), `ops->ground` and `ops->wait` run, yet the first physics frame is Fall with gravity and
   `airborne=false`. Hypothesis from the tester (unconfirmed): `mpColl_80043680` resets collision history without the ground
   flags/ECB state the Wait collision callback expects. Trace it in `pc/gameworld/script_fighter_bench.inc` (~169
   `script_bench_place`) against how the game itself places a grounded fighter (rebirth platform exit, `ftCo_Wait` entry,
   Entry states) and fix so a floor call is grounded Wait on the first frame with no sink. A consequence to fix with it: 20
   bench/call cycles had about half refused because the fighter was still in that 30-frame Landing.
2. **A called CPU gets its original CPU kind back**, so a CPU that was in stand mode starts acting about 200 frames after the
   call (Zelda walked away). Bench/call must preserve the script-selected `cpu_mode`.
3. **`pan`**: measured as vertical (eyeY-intY 18.4 -> -39.7, eye x unchanged), but `docs/scripting.md` says horizontal.
   Decide from the camera code which is right and make the name/doc/behaviour agree (if the field really is a pitch offset,
   document it as such; do not rename silently: keep `pan` accepted and say what it does).
4. **Docs**: default gains are 0.05; the floor-call arrival text must match item 1 after the fix.
5. **air_speed below 1**: at 0.5 the horizontal speed was still decaying toward the scaled limit after 33 frames of a hop
   (1.00 -> 0.50, limit 0.43). Decide whether the modifier should clamp immediately or let the game's own deceleration take
   it there, and document it; do not add a new mechanism unless the current one is wrong.
6. Mid-attack bench refusal, the Zelda/Sheik transform case and Nana/Sheik individual states could not be observed from Lua
   (`gd.player` exposes only the primary). Expose what a test needs (`gd.fighter_benched(port)` returning per-entity state) and
   add fixtures.
Already applied by the integrator (do not redo): the `%g` error format in `gw_script_camera_params.inc` (now `%f` with
`lua_Number` casts), and the dash->run clamp in `ft/fighter.c` ~1609 now uses `FT_SCRIPT_VALUE(fp, 2, dash_max_velocity)` so
run_speed above 1 is held: check that this is the right index and macro for the run-speed modifier and correct it if not.
Report: `_build/tmp/codex-engine-batch2-fix1-report.md` (cause of item 1 in a few lines, file:line, tests, re-test plan).
