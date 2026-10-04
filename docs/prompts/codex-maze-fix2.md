# Maze generator follow-up 2: the owner played seed 7 size 12 to the goal (2026-10-03)

Same rules as follow-up 1 (your files, Lua/Python only, no C, no build, no game launch, no commits); build on your
follow-up 1 state and regenerate the missions bundle last.

The owner's verdict, verbatim:
- "Read lightly as a maze"
- "the climbs and drops were fine, but need tuning, some platforms are placed to close to ceilings and stuff like that."
- "Floor holes did not annoy me"
- "The camera was ok"

1. **Clearance tuning (the concrete complaint).** Platforms sit too close to ceilings and other geometry. Add clearance
   rules to the chunk templates AND a checker that enforces them on every generated maze, including across stitched
   seams (a platform in one chunk under the floor of the chunk above): minimum headroom above any standable surface
   (state the number; derive it from fighter heights measured in the game: Ganondorf is 17.97 tall, a full hop reaches
   about 29 units and a double jump about 52 for Mario: a standing fighter must be able to full-hop without hitting a
   ceiling unless the template marks a deliberate crawl space), minimum gap between a platform and a wall, vertical
   spacing between climb platforms comfortably inside a single jump for the slowest and lowest-jumping fighter, landing
   surfaces under drops wide enough to land on. Retune the starter templates to pass; fail generation with the chunk and
   object names when a template cannot.
2. **Floor holes are fine as they are**: this reverses follow-up 1 item 5. Do not bridge or move them; keep them as a
   deliberate hop. Keep only the checker correction (its edge cost for that walk must say "needs a hop").
3. **Make it read more as a maze** (it read "lightly" as one): less east bias, loops and real choices rather than a spine
   with stubs, dead ends that are far enough to feel like a wrong turn, more room templates so adjacent rooms differ, and
   vertical and horizontal runs mixed. Keep the solvability guarantee and the 1,000-seed check; add a measured
   "maze-ness" summary per seed (branch count, longest dead end, turns on the main route, direction histogram) and report
   the distribution before and after.
4. **A finish.** The log showed `mission: complete` and then play simply carried on. Reaching the goal needs a visible goal
   object from the kit and a clear end moment through the mission runtime's existing completion flow.
Tests for each; report `_build/tmp/codex-maze-fix2-report.md` with the clearance numbers and the before/after maze-ness.

## ADDED (owner, 2026-10-03): interconnected mazes
Verbatim: "It could feel more maze like if we had entrances and exits to other maze seeds and such interconnected that way
across multiple mazes."
5. **A maze world: several mazes joined by doors.** Design it and build the generator and data side; do it after items
   1-4. A world is generated from one world seed: N regions, each a maze from its own derived seed (so a region can be
   regenerated or swapped alone) with its own theme/template mix, joined by connector exits (a region may have several
   entrances and exits, on any side, including vertical), so that the region graph itself has loops and choices: more than
   one way between regions, optional regions, a region you pass through twice from different doors. Solvability is proved
   on the whole world (start region to goal region), and per region between each pair of its connectors that the world
   graph relies on; one-way connectors (drops) are allowed only where the checker proves no soft lock.
   Because chunks stream, prefer ONE continuous chunk graph (regions placed side by side or stacked in world space with
   connector chunks between them: no reload, no second install, the camera/zone rule simply carries across) over loading
   a different level per region; state the limits you find (chunk count, coordinate range, streaming window, blast-zone
   bounds, script budget) and where a real level change would be needed instead. Each region gets a region zone and each
   connector a transition zone; the HUD/map dump shows the current region and the world graph.
   Commands: `mission world <seed> [regions] [size]`, the ASCII world map, and per-region reroll offline. Report what the
   Envoy campaign would need to use a world as a run (rooms as regions, boss region last).
