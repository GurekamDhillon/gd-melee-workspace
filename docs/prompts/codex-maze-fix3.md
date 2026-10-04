# Maze/mission follow-up 3: no hitches, fast start (Lua side) (2026-10-03)

Same rules as your earlier follow-ups (missions mod and `tools/maze/`, Lua/Python only, no C, no build, no game launch,
no commits); regenerate the missions bundle last. The owner: "I did experience some hitching when enemies were loaded in a
new section", "CANNOT have that", "also long start up time ...". Measured evidence and verified patches (re-derive against
current source, do not blindly apply): `_build/audit-20261003/maze-hitch/` (`patches/chunks-one-install-per-frame.diff`,
`patches/chunks.lua.fixed`, `patches/warm-enemy-pipelines.lua`). An engine job (`docs/prompts/codex-no-hitch-engine.md`)
is adding `gd.warm{...}`, `gd.area_prepare/activate`, and launch-into-mission; use them behind guards when present.
1. `chunks.lua` `C.update` installed every missing chunk of the 3x3 window on one frame (2-3 installs, 20-44 ms): at most
   ONE install or ONE unload per frame, nearest-to-player first, never on the frame a wave spawns; unloads deferred and
   lowest priority. Verified by the lane: 38.8 -> 11.2 ms at the window edge.
2. Warm everything the level will draw during the staged install, before the player is released: every enemy kind the
   level or maze can spawn (the first draw of a Goomba cost 1.2 s, a Koopa 0.75 s, in pipeline builds), every chunk model,
   the goal and drive items. Use `gd.warm` when it exists; until then the lane's fallback (spawn one of each kind for a
   few frames during staging, then remove) but only while the screen is covered, never visible to the player, and never
   leaving an enemy alive. Staging completes only when warm-up is done; log the time it took.
3. Prefetch ahead of travel: with one install per frame, start loading in the direction of travel early enough that the
   room the player is about to enter is always already installed (state the rule); the committed room from the zone rule
   drives it.
4. Bug: `mission maze` sent early fails permanently with `refused staging step prepare: missions/fighters.lua:95:
   respawning or unsafe CPU 2: waiting for bench before mission load`: retry that step each frame until safe (bounded,
   with a clear timeout message) instead of refusing.
5. One `ran too long (limit: 2000000 instruction...)` abort at `runtime.lua:147` on a frame with unload + spawn + wave:
   find the loop that can run long and bound it per frame.
6. Autostart: let a mod or level declare a mission to start at match load, so the engine's launch-into-mission hook can
   call it; with it the player never sees the host stage.
Tests for each; report `_build/tmp/codex-maze-fix3-report.md`.
