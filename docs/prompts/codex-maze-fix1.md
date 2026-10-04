# Maze generator follow-up 1: first run in the real game (2026-10-03)

Same rules as your packet (your files in the missions mod and `tools/maze/`, Lua/Python only, no C, no build, no game
launch, no commits). The mission runtime thread has since changed the room camera to authored room/transition zones
(`_build/tmp/codex-mission-runtime-fix9-report.md`) and fixed a staging crash: re-read the current sources before editing,
and regenerate the missions bundle last (`tools/port/missions_bundle.py`). An Envoy job is waiting on your final message.

A lane ran four seeds in the game with real scripted walking and jumping. Evidence and proposed diffs (written against a
19:46 copy, so re-derive, do not blindly apply): `_build/audit-20261003/maze-gen/patches/*.diff`, logs and drivers beside.
Seed 7 size 12 was walked start to goal and completed; climbs, drops, sealed exits, respawn and streaming all held.

1. BLOCKER: `mission maze N` refused: `maze_commands.lua:21` passes `'models/'` to `loader.catalogue`; must be
   `'missions/'`. Verified in game.
2. `tools/maze/generate.py:92` (`--prepare-mod`) and the README write the kit to the mod-root `models/`; the runtime reads
   `missions/models/`. Fix and test the prepared layout against the engine path rule (`missions/` prefix, no traversal,
   backslash or drive).
3. Every enemy was in wave 1 at mission start, so enemies in unloaded chunks fell to the blast zone. Lane's verified fix:
   one wave per enemy chunk triggered on entering that chunk, capped at 8 waves with adjacent chunks sharing. Now that
   zones exist, trigger from the room zone.
4. P1 sinks through the floor on first placement (also on the hand-made `grid` level): placed while still grounded on the
   hidden host stage line, sinks to y about -12.5, contact trace `leave lost_contact` then `ceiling_hit`; a plain teleport
   rescue repeats the sink. The lane worked around it in `runtime.lua` (fly-and-place recovery in the first 240 frames).
   The staging crash fix changed entry readiness: check whether that already cures it; if not, fix the cause in the
   placement order rather than keep a recovery flicker, and report anything that needs the engine.
5. Reachability: a chunk with an open down exit has a 24-wide floor hole at x 53..77 in the middle of the left/right
   walk, so "walk left/right" is false there (start chunk of seed 99, goal chunk of seed 123). Move the down opening off
   the main walk line or bridge it with a pass-through platform so walking is true and dropping is a choice; update the
   checker so its edge costs match the geometry.
6. Seeds 1 and 99: P1 takes about 1% per second from the first frame with no attacker; both have a reward_end chunk next
   to the start; seeds 7 and 123 are clean. Find the cause (a reward/hazard adapter, a trigger, an overlapping zone).
7. Two chunk loads in one frame exceeded the 50 ms script budget once (`runtime.lua:150 ran too long`) after a long
   fly jump: at most one chunk install step per frame, queued.
8. Minor: `chunk spawn` flips between two chunks while hopping across a vertical border (use the committed room from the
   zone rule); the `mission: complete` log line is sometimes missing though the state is complete; the goal has no visible
   marker in the game picture (give it a kit model, not only a Lua overlay); the main path is east-biased and rooms repeat,
   so mazes read as staircases: vary direction and room templates, and add wall/doorway/goal pieces from the kit.
9. Emit a room zone per chunk and a transition zone per stitched door, climb and drop, in the format the runtime now reads.
Tests for each; report `_build/tmp/codex-maze-fix1-report.md` with file:line and what a tester should re-walk.
