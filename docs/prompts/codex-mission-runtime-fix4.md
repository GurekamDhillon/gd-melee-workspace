# Packet B follow-up 4: two camera items left after round 4 in the game (2026-10-03)

Round 4 (fresh repo mod, no local patches) measured your fix3 and it holds: blast zone fixed in world space across a
2,500-unit sweep with zero deaths; origin snaps within 10 frames of a KO; the player sits 5 to 14 units from centre while
running (was 79); chunk zoom shows exactly the room height; door crossings keep the player on screen in every sample; shaft
mode keeps the player on screen; rest skew 0.00; C-stick still attacks; `mission stop` restores exactly; unused CPUs are
benched and out of frame. Evidence: `_build/audit-20261003/mission-verify/r4/` (`logs/mv4-*-mv.log`, `shots/`, montages).
Same rules (Lua/Python, your files, no build, no game, no commits). The maze generator job is editing its own files in the
missions mod and the bundle: re-read before editing shared files and regenerate the bundle last.

1. **Chunk mode shows void past the level's outer edge.** At the level's left end the visible left edge was -64 while the
   level rectangle ends at -32.5 and the chunk union at 0. Measured cause: the runtime clamps the origin with the 16:9
   visible width W=199.1, but the native camera clamp lets the view extend about 31.5 units past the camera bounds, as if it
   assumed a 4:3-wide view (136 = 4/3 of the 112 height). Find in the camera code (`melee/src/melee/cm/camera.c`, the bounds
   clamp and how widescreen widening interacts with it: a separate job is changing the aspect handling in
   `sysdolphin/baselib/cobj.c`, so derive the visible width from the engine's real view aspect at runtime rather than a
   constant: use the documented Lua read for the view aspect / `gd.project`, and say which) what width the native clamp
   uses, and clamp the origin so the visible rectangle never passes the level's outer rectangle on any side, at any aspect.
   Test with the formula for 4:3, 16:9 and 21:9. If the level is narrower than the view, centre it.
2. **The respawn at the far end of a long level is a fast pan.** The origin and blast zone snap correctly, but the camera's
   eye and interest still travel about 2,500 units over ~50 frames through native smoothing (skew peaks at -798 while the
   player is dead). Cut instead of panning: on a far respawn set the camera's position and interest to the respawn framing
   on the same frame (use the existing camera calls in `docs/scripting.md`: a camera cut / fixed move with zero frames, or
   temporarily raising `track_smooth` to its instant value for one frame; state which works by reading the engine side). If
   no call can do it, say exactly what engine call is missing rather than approximating.
3. The cosmetic log line at play start (`CPU 2 bench refused; stand fallback: unsafe action or held item`, then the bench
   succeeds a moment later): retry the bench quietly until the fighter is in a safe state, and log once when it takes.
Report: `_build/tmp/codex-mission-runtime-fix4-report.md` with the clamp formula and the expected visible edges at each
level end for the tester's two levels.
