# Codex packet N: a real profiler and a worst-case benchmark harness (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md`, `docs/scripting.md` on `gd.perf`,
`docs/HANDOFF-2026-10-03-ENGINE-DAY.md` for what exists as of today). Both trees are deliberately dirty: do NOT commit,
reset, stash, revert or reformat. Do NOT run `tools/port/build.sh`, do NOT rebuild Aurora, do NOT launch the game (the
integrator builds and runs). Keep every file compilable at every save. The six-slot job has just finished in
`melee/pc/platform/gw_runtime.c` and `melee/src/melee/gm/gmscenelaunch.h`: read `_build/tmp/codex-six-slots-report.md` and
build on it. Other jobs are editing Lua mods only. Credit every outside tool or technique in `CREDITS.md` and, for anything
vendored, in `tools/release/THIRD-PARTY-NOTICES.txt` with its licence text.

## Why
The owner's target is 120 fps (8.33 ms per frame) with ported fighters, six-fighter matches, large custom levels, shaders
and rollback netplay. Today `gd.perf` reports total logic time, draw-recording time, render-worker time and some counts. It
cannot say WHERE time goes, has no GPU time, no rollback cost, no hitch capture and no file output. The owner: "So we need to
bolster our profiler as well?" then "yes queue it on codex, use tracy or whatever you want". After this packet the owner
intends to study optimisation mods from other games and apply what fits, so the profiler must make a bottleneck obvious and
a harness must make a measurement repeatable.

## Part 1: the profiler
Design it as a small instrumentation API with pluggable outputs, zero cost when off and cheap when on (state the measured
or estimated overhead per zone), read-only with respect to game state (rollback, replays and LAB rewind stay exact: say why).

1. **Zones and counters.** Scoped timing zones (`GW_PROF_ZONE("name")` style, nestable, per thread: game thread, render
   worker, audio) and named counters. Game-side code compiled through the PPC retarget cannot call native code freely:
   provide the scalar shim the game side calls (see the shim boundary rules in `melee/CLAUDE.md`), and keep zone names as
   ids, not pointers.
2. **What to instrument** (the breakdown that is missing today):
   - the frame: input, game logic, draw recording, render worker, present/vsync wait, and GPU time (item 3);
   - inside logic: per fighter (by slot and character), fighter subphases (input/AI, action state, physics, collision,
     hitbox checks, animation and skinning if it runs on the game thread), items and projectiles, our item-based enemies,
     stage, particles and effects (vanilla and Geno), camera, HUD;
   - the m-ex PowerPC interpreter: time and instruction counts per call site / per fighter (it interprets mod-disc fighter
     code and is a prime suspect), and Geno hook time;
   - Lua: per script and per callback (`on_frame`, `on_frame_pre`, events), plus time inside each `gd.*` call family;
   - rollback and snapshots: frames re-simulated this frame, snapshot save and restore time and bytes, the LAB rewind store;
   - loading: file reads, decode, texture and mesh upload, shader/pipeline compilation (each compile as its own event with
     the shader's identity), chunk load/unload, model reload, bench/call;
   - memory: headroom of the heaps the six-slot report identified, sampled per frame.
3. **GPU time.** Through whatever Dawn/WebGPU and Aurora's public API allow (timestamp queries if the device has the
   feature; say what is available on the D3D11 default and the D3D12 backend, and what you chose). Per frame at minimum;
   per pass (EFB, our post passes, bloom, custom materials, surface shaders) if feasible. If timestamp queries are not
   reachable without changing Aurora, say exactly what small change would expose them and add it to the existing carried
   patch mechanism (`_build/patches/`, see `aurora-gd-surface-v1.md`) as a separate, documented patch; the integrator
   rebuilds Aurora (recipe: `GW_VSDIR`/`GW_VCVARSALL` pointing at VS Build Tools, `GW_AURORA_ROOT=C:/gdm`, from PowerShell).
4. **Hitch capture.** A ring buffer of the last N frames' zones; when a frame exceeds a threshold (default 2x budget), dump
   that frame and its neighbours with every event on them (compiles, loads, rollbacks) to a file, rate-limited.
5. **Outputs.**
   - Always available, no dependency: a per-run report file (JSON) with percentiles (p50, p95, p99, max) per zone and per
     counter, and an optional trace in Chrome Trace Event format (opens in Perfetto or chrome://tracing) for a chosen frame
     range.
   - Tracy (https://github.com/wolfpld/tracy, BSD-3-Clause) as an optional backend behind a build flag, off by default and
     never in release builds: if you can obtain the client source in your sandbox, vendor only the client under
     `melee/pc/third_party/` with its licence and wire the zones to it; if you cannot fetch it, leave the backend interface
     and exact integration steps for the integrator (which files, which defines, the link change) and do not fake it.
   - `gd.perf()` keeps its current fields (do not break existing users) and gains the new breakdown as nested tables;
     console commands `prof on|off`, `prof report`, `prof trace <frames>`, `prof hitch <ms>`.
   - Environment switches documented in `PORT_DEV_QUICKREF.md` in the existing table.

## Part 2: the benchmark harness and the three worst cases
A repeatable harness: `tools/bench/` (Python) plus a mod `melee/pc/scripts/examples/bench/` (Lua). One command runs a named
scenario on a chosen disc for a fixed number of frames with a fixed seed and scripted inputs for every slot, with the
profiler on, on the second monitor by default (`MELEE_WINDOW_X=-1080 MELEE_WINDOW_Y=-360`, width <= 1080; never hidden: the
game stalls hidden), CPUs explicitly in the mode the scenario needs (`cpu0` is NOT idle: use `gd.cpu_mode`), and writes
`_build/bench/<scenario>/<timestamp>/report.json` plus a one-screen text summary. Scripted input does not drive a CPU slot:
slots a script must pilot are human slots.
Scenarios, each a data file so more can be added:
1. `steady_worst`: six different fighters if memory admits them (else the heaviest admissible set: report which), including
   Ice Climbers and any ported/Geno fighter the mods directory provides, all attacking/shielding/firing on scripted loops,
   items very high, our item-based enemies at their cap, a custom level at the instance limit with custom materials and
   glass, camera zoomed to show everything, every Lua system on (missions, contact trace, debug overlay), the full
   post-process chain, a surface shader on every fighter, the clank pass firing repeatedly, internal resolution and MSAA at
   maximum, frame rate uncapped (`MELEE_FPS=u`).
2. `rollback_worst`: four ported or heavy fighters, projectiles, and a forced maximum-depth rollback every frame. Find the
   existing rollback test hooks (SyncTest / forced rollback in `melee/pc/platform/gw_rollback.c`, `gw_snap.c`, the net
   tests) and use them; if forcing a depth is not possible today, add the smallest test-only switch and say so.
3. `hitch_worst`: a scripted sequence that triggers each known spike once and separately, from a cold start: first use of
   every shader and effect, chunk border crossings in a generated maze, a level reload, bench/call of a fighter, the clank
   pass starting, a LAB savestate and a rewind; reported as worst single frame per event with the hitch dump.
Also `baseline`: a plain vanilla two-fighter match on Final Destination, for comparison and for checking the profiler's own
overhead (run it with the profiler off and on).
A comparison tool: `tools/bench/compare.py <reportA> <reportB>` prints per-zone deltas and exits non-zero when any budgeted
zone regresses beyond a tolerance; a budgets file with an initial allocation of the 8.33 ms across subsystems (your proposal,
marked as a proposal).

## Tests and docs
Headless tests in the suite's pattern for the zone accounting (nesting, per-thread, overflow), percentile maths, the hitch
ring, report schema, zero-cost-when-off (no allocations, no timing calls on the hot path: show how you checked), and that
the profiler does not change simulation results (a replay or sync test with it on and off). Python tests for the harness
and compare tool. `docs/profiling.md`: how to run a scenario, read the report, open a trace, add a zone, add a scenario.

## Report
`_build/tmp/codex-profiler-bench-report.md`: the API, every instrumented zone with file:line, what GPU timing you got and
what Aurora would need for more, overhead, the Tracy status, tests, unverified items, and the exact commands for the
integrator to run each scenario and what a sane first result should look like.
