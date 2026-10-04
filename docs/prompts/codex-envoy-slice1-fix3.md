# Packet E1 follow-up 3: Envoy after its second run in the game (2026-10-03)

Same rules (Lua/Python only, your mod and tests, no C, no build, no game, no commits). Round 2 on a fresh copy, vanilla disc:
fresh install starts and a normal match is untouched; no soft-lock; confirm screens open on the safe default; the menu
launches the LAB; staged load in nine one-frame steps; all seven kinds defeated across runs with real item drives that
rest on the floor and credit once; stats match the tuning table; boss and P1 at 0%; win written once; fail and abandon
paths; unload releases everything. Evidence `_build/audit-20261003/envoy-verify2/` (`patches/10-*`, `11-*`, logs env2-a..j).
Fix, each with a test:
1. **The pause menu does not pause during a run** (`owns_pause=false`, `gd.paused()=false`, frames advancing).
   `app.lua` ~179 gates pausing on `not self.mission.retiring`; Envoy never drains the mission runtime's retire queue
   (`runtime.lua` ~79, `install.lua` ~241 and ~314-320 expect `pre_frame`), so `retiring` stays set for the whole run, and
   the retired areas and model assets are never unloaded (a leak across rooms and runs). The tester verified a fix in an
   isolated copy: drain the retire queue from `app:frame` (do NOT register `on_frame_pre` to call `mission:pre_frame()`:
   that broke the run with `envoy: refused boss already reserved`). See `patches/10-app-pause-gate-retiring.diff` for the
   intent (it is not in git-apply format). Prove with a test that retired assets are released and pause freezes the game.
2. Use the new script deadlines (`gd.deadline(name, frames)` / `gd.deadline_done(name)`,
   `_build/tmp/codex-hung-game-detection-report.md`) around every wait Envoy does (staging, boss call, settle), guarded for
   absence, so a stall names itself in the log.
3. Three back-to-back runs were not completed by the tester (a test fixture stalled): add an offline test that runs three
   runs in sequence against the stub and asserts nothing accumulates (items, tints, modifiers, benched ports, retire queue).
4. Records shows only "Last result": show run count, wins, best time. `envoy status` shows a stale room after a run.
Report `_build/tmp/codex-envoy-slice1-fix3-report.md`.
