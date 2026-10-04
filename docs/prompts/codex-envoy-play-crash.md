# Packet: the owner's first Envoy play session crashed on starting a second run (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`). Both trees are deliberately dirty: do NOT commit, reset, stash, revert or reformat. Do NOT
run `tools/port/build.sh`, do NOT launch the game. Keep every file compilable. Another Codex job is editing
`melee/src/melee/gr/` and `pc/gameworld/script_stage_slots*`; others are in Lua mods: re-read shared files before editing.

## What happened
The owner played Supertime Envoy (`melee/pc/scripts/examples/envoy/`, bundling the mission runtime
`melee/pc/scripts/examples/missions/`) on the vanilla disc. Run 1 as Fox completed normally and was WON
(`envoy: settled run=1 result=win one-write`). The owner then started a second run with a different fighter (Falco) from
the menu, which relaunches the scene (`gw: scene: set at runtime "mode=lab;p2=falco/cpu0;p1=falco;stage=fd"`). Shortly
after, the game died on a game-side assertion:
```
fighter ground no under Id! 0 17
assertion "0" failed in src/melee/ft/ftcommon.c on line 617.
gw: PANIC src/melee/ft/ftcommon.c:617
gw: launcher final reason=CRASH
```
Log: `_build/runs/envoy-play1/melee-pc.log` (lines ~4285-4350), crash reports in `_build/runs/envoy-play1/crashlogs/`.
That assert is in the game's own "put the fighter on the ground" routine (`ftcommon.c` ~596-618): it sets the fighter
grounded and then requires a floor line under it (`ft_80084A18`); player 0 was in motion 17 with no floor under it. So a
fighter was made grounded (or was already grounded and went through a landing) at a moment when the collision under it
did not exist: the host stage's collision hidden, or the level's pieces not yet live at that position, during the staged
install of the second run. Run 1 in the same session did not hit it, so the ordering differs on a re-entry (a new scene
with a fighter still arriving, a different character's entry timing, or state left from run 1).

## Fix both layers
1. **The cause, in the staged install (Lua).** From the log and `missions/scripts/install.lua`, `runtime.lua`,
   `fighters.lua` and Envoy's `run.lua`/`app.lua`: establish the exact order of events on the second run (scene launch,
   fighter entry, bench/stand of CPUs, staging steps, placement, `stage_hide`) and why P1 could be grounded with no floor.
   The invariant to enforce: from the first staging step until commit, the player is NEVER a grounded fighter over
   collision that is being removed or not yet installed: hold the player in a defined safe state (benched, or airborne and
   frozen above a guaranteed floor) before any host collision is hidden, and release only after the level's collision is
   live under the placement point (verify with `gd.floor_below` at the placement point before releasing). Wait for the
   fighter to be ready after a scene launch (entry animation finished) before staging starts. Add an offline test that
   replays the second-run order with a stub that models a fighter still in its entry/landing state.
2. **The engine must not die when a script removes the floor under a grounded fighter (C).** Any script that hides or
   removes collision can trigger this vanilla assertion and kill the game; that is not acceptable for a modding platform.
   In `ftcommon.c` ~613-618 (and any sibling "no floor under a grounded fighter" asserts: search for the same message and
   for `ft_80084A18` callers), under the PC guard only and leaving the original path intact for other targets: when no
   floor is found, log one rate-limited line naming the player, motion and position, and put the fighter into the game's
   own airborne fall instead of asserting (the way walking off an edge does). Add a headless fixture that removes the line
   under a grounded fake fighter and asserts the game continues with the fighter airborne. State whether the same hazard
   exists for items and for fighters hanging on a ledge or riding a moving platform.
Regenerate the missions and Envoy bundles (`tools/port/missions_bundle.py`, `tools/port/envoy_bundle.py`).
Report `_build/tmp/codex-envoy-play-crash-report.md`: the sequence that caused it, file:line of both fixes, tests.
