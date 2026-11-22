# Packet B follow-up 6: `mission play` exceeds the script time budget after fix5 (2026-10-03)

Same rules (Lua/Python, your files, no build, no game, no commits). Integrator smoke test of your fix5 on the stamped build,
LAB, vanilla disc, `mission play maze` (the tester's 8-chunk maze; play copy `_build/audit-20261003/maze-play/mods/`):
```
script [missions/main] mission: CPU 2 benched
script mission: stage_hide false accepted
script [missions/main] mission: refused missions/runtime.lua:89: ran too long (limit: 2000000 instructions or 50 ms per call)
```
Log `_build/runs/maze-smoke3/melee-pc.log`. The same level loaded with fix4 (`_build/runs/maze-smoke1/`), so the fix5
reordering pushed one call over the engine's per-call budget (2,000,000 instructions or 50 ms wall clock: read where the
budget is enforced in `melee/pc/platform/gw_script.c` and what resets it). The whole install runs inside one protected call
at `runtime.lua` ~86-100: `fighters.prepare`, `world.load` of the root, `chunks.update` (up to nine chunk loads with model
reads from disk), bounds, teleport, `stage_hide`, spawn, `glue.step`. A wall-clock limit makes this pass or fail by disc
cache state, so it must not depend on luck.
Fix at the root: make level installation a staged, resumable transaction spread across frames (one bounded step per frame:
prepare fighters; load root; load chunks one per frame, nearest first; bounds; place; hide; start), each step well inside
the budget, with the same atomicity as today from the player's point of view: the old level stays live until the new one is
fully staged, a refusal at any step rolls back to the old level, the player is held safely (benched or frozen and
intangible) while staging so nothing can damage or KO them, and the camera does not move until the commit. `mission reload`
uses the same path. Keep P1's percent clean (the run above also shows P1 at 16% on the host stage after the refusal: the
opponent acted before the bench: the CPU must be benched or stood before anything else, on the first frame the mod runs in
a match, not at play time). Measure in tests with a stub that counts instructions/time per step and asserts each step is
under a fraction of the budget for a 9-chunk load; add a test that a refusal mid-staging restores everything.
Also re-confirm in code that the camera-cut loop fix is still in (the smoke run could not reach it: zero cuts were logged
because the level never installed). Regenerate the bundle. Report `_build/tmp/codex-mission-runtime-fix6-report.md`.
