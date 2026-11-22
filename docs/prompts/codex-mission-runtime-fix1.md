# Packet B follow-up: mission runtime after the first in-game runs (2026-10-03)

18 game runs on the vanilla disc in the LAB. Evidence: `_build/audit-20261003/mission-verify/` (`logs/`, `patches/`, `work/`,
`mods/` = the isolated copy that ran). Same rules as before (Lua/Python only, your files only, no build, no game, no commits).
The integrator has ALREADY applied `patches/02a` and `02b` to your `runtime.lua` and `commands.lua` (asserts on `gd.teleport`,
which returns nothing, and on `gd.fly(port,'place')`, which returns false after landing). After that, `lua
pc/tests/missions_runtime.lua` (from `melee/`) FAILS: fix the tests and stubs so they model the real returns (check every `gd`
call you assert on against what the engine really returns: read the C in `melee/pc/platform/gw_script*.c|inc`), and regenerate
`scripts/main.lua` with `tools/port/missions_bundle.py`.

Defects found in the game, fix each at the root with a test:
1. Completion is unreliable: in runs 8 and 9 the player reached the goal with both waves defeated and `mission: complete` was
   never logged; in runs 5 and 6 the first `mission clear` did not advance wave 1. Runs 11 and 12 completed. Logs:
   `logs/mv-run5..12*`. Find the cause (ordering between wave completion and goal checks, enemies that fall off rather than
   being defeated, checkpoint ordering, the one-step lag below) and make it deterministic.
2. Chunk bookkeeping: log lines lag one step behind the game; the c2->c3 crossing at x=390 produced no line in its step; the
   switch to c1 was logged with the fighter at x<=120 although the border is at 130; flying across several chunks thrashes
   (target chunk loads, then the real position reloads the old window) before converging. Make the window follow the
   fighter's real position with hysteresis, and fly commands pre-load the destination.
3. Reload cost: every chunk folder carries its own copy of the 1024px colour and glow atlases (11.2 MB per copy), each reload
   pins a new generation, and the engine's 64 MiB scene budget is exhausted by the third export of a two-chunk level (a
   five-chunk level pins ~56 MB at once). The exporter side is being changed to write ONE shared atlas per mission and to
   leave unchanged files untouched; on your side: load a shared `models/` atlas for all chunks if present, and report a
   refused reload with the engine's real reason.
4. Pass the level's part names through to the engine as instance labels when `gd.model_label` exists (another packet adds it;
   guard for its absence), so contact traces can name pieces.
Report: `_build/tmp/codex-mission-runtime-fix1-report.md` (causes in a few lines each, file:line, tests, native test plan).
