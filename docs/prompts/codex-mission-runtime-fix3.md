# Packet B follow-up 3: the camera after its first measured run in the game (2026-10-03)

Round 3 on the stamped build. Runtime fixes all pass (clear during respawn, completion 10/10, no border flip, labels, CPU
parked and idle). The camera did not: evidence `_build/audit-20261003/mission-verify/r3/` (`logs/*-mv.log` sampled every 10
frames, `shots/`, `patches/`, `work/camsum.py`). Same rules (Lua/Python, your files, no build, no game, no commits).
The integrator has ALREADY applied the tester's three diffs (check they applied and are right, then build on them):
`r3-01` the validator dropped `mode/window/min_dist/fov` whenever the `camera` table also carried the rectangle, so chunk and
shaft modes never applied; `r3-02` the blast rectangle was set once in world coordinates while the camera moves the stage
origin and the engine adds the origin to the blast zone, so the KO rectangle slid with the camera and P1 spawned inside it
(41 deaths in a minute); the diff rewrites the origin-relative blast rectangle when the origin has moved 30+ units;
`r3-03` the chunk distance used `tan(fov)` and `min()`: visible height is `2*d*tan(fov/2)` (measured with `gd.project`: fov 25,
d=83.2 shows 37 units), so chunks were framed 3.3x too close; now half-angle and the larger of the width/height distances.

Fix at the root, with tests, and re-derive every camera number from the measured relation above:
1. Blast zones: make them correct by construction rather than patched every 30 units: either keep the blast rectangle fixed
   in world space by compensating on EVERY origin change in the same call that moves the origin, or (better, if the engine
   API allows) set blast zones in a way that does not follow the origin; no frame may exist where the player's spawn or the
   level is inside the KO rectangle. Test: origin sweeps across a long level, blast edges stay at the level's authored edges.
2. The camera freezes while P1 is respawning (the tick returns early when P1 is not ready): after a KO at the far end, P1
   respawns at the start while the camera stays 2468 units away for ~300 frames, then sweeps back. Snap the origin
   (no tween) to the respawn location when the player is respawning or is further than a window from it.
3. The camera trails a running player: with `track_smooth=1` Mario running right sits up to 79 units right of centre (68% of
   the way to the edge) and sees little ahead. Adventure's stages lead by keeping the origin close (10-unit leash) and the
   stage default `track_smooth` 1.8. Make the player sit at or slightly behind centre with look-ahead in the facing/moving
   direction (the research note describes the fighter camera box extended in the facing direction); choose values, state the
   expected leash, and expose them in the level's `camera` table.
4. Parked CPUs are camera subjects: during chunk crossings the parked Fox filled the frame while Mario was off-screen. Non
   participating CPU ports must not be camera subjects, be hittable or wander: `gd.fighter_bench(port)` them (the engine
   bench is invisible, intangible, AI-frozen and camera-excluded; verified in the game) instead of parking them on the level,
   and only `gd.fighter_call` a port when the mission uses it (boss, fighter enemy). Keep stand mode as the fallback when
   bench is refused.
5. Chunk mode shows ~30 units beyond the chunk on each side (view 199 wide for a 138-wide room at the height-fitting
   distance): that is the aspect ratio; decide the rule (fit height and accept neighbours showing; clamp the origin so the
   view never passes the level's outer edge, so void is never shown at the level boundary) and implement the clamp using the
   real visible width from the formula and the window aspect.
6. Door crossing in chunk mode: the player is up to 101 units from centre against a 95 half-width during the 50-frame tween
   (off-screen for 3 of 282 samples). Start the tween before the border (when the player is within a margin of the door and
   moving toward it) or bias the origin toward the player during the tween so the player never leaves the view.
7. Shaft mode: the player was off-screen in 61 of 251 samples while falling or climbing fast (vertical leash 118 against a
   39 half-height). Follow faster vertically, with look-ahead by vertical speed, and a taller default window; state numbers.
8. Chunk sizes: the exporter's grid check needs whole metres, so 120x100 game units is not authorable (the tester used
   130x104 = 20x16 m). Make the default chunk 130x104 everywhere (docs, generator contract note for the maze job in
   `docs/prompts/codex-maze-generator.md`: append a line there rather than editing the generator's files).
Regenerate the bundle. Report `_build/tmp/codex-mission-runtime-fix3-report.md` with every chosen number and the expected
measurements, so the tester can compare.
