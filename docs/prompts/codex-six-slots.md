# Codex packet M: six-fighter matches for missions and the LAB (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `_research/scene-launch.md`). Both trees are deliberately dirty: do NOT commit, reset, stash,
revert or reformat. Do NOT run `tools/port/build.sh`, do NOT launch the game. Keep every file compilable at every save.
Other jobs are editing Lua mods only; the engine C is otherwise quiet. The current build is clean and passes 236/236.

## Why
The owner: "Why do at most three fighters fit in a match? Can we fix that? There are multiman fight modes built into melee."
The game has six player slots (`Gm_Player_NumMax` = 6); Multi-Man Melee runs one human against five enemies recycled through
slots 1-5 (`melee/src/melee/gm/gmmultiman.c:597-607`). Missions and Envoy need up to five fighter enemies at once and waves
that reuse slots. Your own audit already found what is four-wide on OUR side: `_build/tmp/codex-engine-batch2-report.md`,
section "Six-slot audit" (the scene config `GW_SL_SLOTS=4` and parser in `melee/pc/platform/gw_runtime.c` ~1520/2003,
`SceneLaunch_SeedVs` and the preload seeding loops in `melee/src/melee/gm/gmscenelaunch.h` ~107/280, CSS/training scratch that
stays four-wide, the LAB sharing that seeding) and what is ALREADY six-wide (`StartMeleeData.players[6]`, HUD anchors,
camera subjects; `lbDvd_80017700(4)` is a heap selector, not a player count: do not touch it).

## Build
1. `MELEE_SCENE` / `gd.scene_launch` accept `p5=` and `p6=` for direct VS and LAB launches (not through the character
   select, which stays four-wide: refuse six-slot routes that would pass through CSS/training scratch, with a clear message).
2. Seeding, preload and rules for all six slots; teams so that slots 2-6 can be one enemy team against the player.
3. Every script API that takes a port accepts 1..6 where the engine supports it (`gd.player`, `gd.players`, `gd.input`,
   `gd.cpu_mode`, `gd.fighter_mod`, `gd.fighter_bench/call/benched`, `gd.fighter_shader`, `gd.teleport`, contacts...): audit
   each for a hard-coded 4 and fix or document. Controllers remain four physical ports: slots 5-6 are CPU or script-driven.
4. Slot recycling for waves, the Multi-Man way: a helper (`gd.fighter_recycle(port, {character=?, x=, y=, ...})` or the
   documented equivalent built from bench/call and stocks) that brings a defeated enemy slot back as a fresh enemy, same
   character (changing character mid-match needs its files loaded at match start: if a different character is requested and
   was not preloaded, refuse clearly; allow preloading a list of characters at launch if the game cache allows it and say
   what the limit is from the code).
5. Memory: establish from the code what loading six DIFFERENT characters costs against the heaps the port uses (the five in
   Multi-Man are identical wireframes); add a launch-time check with a clear refusal rather than a crash, and a log line with
   the headroom.
6. LAB: reset/restart, savestate/rewind and the LAB panels with six fighters: fix what assumes four, or refuse six-slot
   savestates clearly if the snapshot format cannot take it and say what it would need.
7. HUD and camera: nothing to enlarge; note what needs eyes (percent spacing with six, framing).

Tests in the suite's pattern (parser, seeding, port-range audit, recycle, the CSS refusal). Report
`_build/tmp/codex-six-slots-report.md` with file:line, the memory findings, unverified items and a native test plan (launch
lines for 1v5 same character, 1v5 mixed, a wave of 12 through 3 slots; what to measure).
