# Packet B follow-up 9: the owner played the room camera; door transitions fight (2026-10-03)

Same rules (Lua/Python, your files, no build, no game, no commits). You have just finished the staging crash fix; build on
that state and regenerate the bundle last.

The owner played the eight-room test level (chunk camera mode, 130x104 rooms) on the main monitor. Verbatim:
"The game is too eager to transition between rooms, if a player stops in the area between rooms or turns back in that area
the screen fights back and fore".

That is the behaviour added in follow-up 3 item 6 (start the camera tween BEFORE the border when the player is within a
margin of a door and moving toward it) meeting the chunk-ownership hysteresis: near a doorway the "current room" flips as
soon as the player enters the margin, and flips back as soon as they slow, stop or turn, so the camera eases one way and
then the other. The measured numbers from the lanes: the tween began 24 units before the border and ran about 45 frames.

Redesign the room transition so it is calm and decisive. Requirements:
1. **Commit, do not anticipate.** The camera belongs to one room at a time and changes room only when the player has
   actually crossed: the player's position is past the border by a commit distance (state it; something like a body width,
   not 24 units of anticipation), not merely approaching it. No transition is started by velocity or facing alone.
2. **Real hysteresis in both directions.** Once the camera has committed to room B it does not return to room A until the
   player is past the border by the commit distance on A's side. Standing still anywhere in the doorway, turning around in
   it, dashing back and forth across the line, or being knocked across and back must produce at most one transition per
   genuine crossing and never an oscillation. A transition in progress is never reversed mid-ease by a small movement:
   either let it complete and then (if the player really went back) do one clean return, or define a single reversal rule
   and state it.
3. **The player stays on screen without anticipation.** Instead of starting early, while the player is inside the doorway
   zone frame BOTH rooms' edges enough to keep the player visible (a doorway framing: the origin may sit between the two
   room centres, clamped, moving only as far as needed to keep the player inside a safe margin of the view), and ease to
   the committed room's framing after the commit. The earlier measurement to preserve: the player was never off screen
   during a crossing.
4. **No fighting between systems.** The chunk-streaming window, the respawn chunk, the blast-zone compensation and the
   camera each use the same committed room; none of them may use the anticipated one. Confirm no setter is called on frames
   where the committed room did not change.
5. Make the feel tunable per level and per door in the level's `camera` table: commit distance, ease duration and curve,
   doorway framing margin; choose defaults deliberately and state them, with what the owner should feel.
6. Vertical doors (climb and drop exits in a maze) follow the same rule with a vertical commit distance; a jump that peaks
   across the line and falls back must not transition.
Tests: a player stopping in the doorway for 300 frames (zero transitions after at most one), turning back before the
commit line (zero), dashing across and back ten times (at most one transition per real crossing, never two within the ease
duration), a knockback across and back, a jump that peaks across a vertical border and falls back (zero), and the on-screen
guarantee through each. Report `_build/tmp/codex-mission-runtime-fix9-report.md`: the rule in a few plain sentences, the
default numbers, file:line, and what the tester and the owner should try.

## ADDED (owner, 2026-10-03): track the player with authored zones, not with derived rectangles
The owner proposed the mechanism (verbatim): "We could also use geno collision detection with our custom objects and place
a "no physics" bounding box across each room, and each transition period to have a proper track of where the character is.
(Taking care of the situation where we are not in a bounded area)".
Build the camera redesign above ON this model:
- **Room zones and transition zones are explicit, authored, non-physical volumes.** Each room has a zone covering its
  interior; each connection between rooms (doorway, climb, drop) has its own transition zone spanning the opening and a
  little of both sides. They are data in the level and chunk files, exported from Blender markers (the exporter is not
  yours to edit: report the marker convention it should add, e.g. `gd_zone=room|transition` with the room ids a transition
  joins), and generated automatically by the maze generator for stitched chunks (also not yours to edit: report the
  change). For levels that do not author them, derive default zones from the chunk rectangles and door slots so existing
  levels keep working.
- **The rule becomes a state machine on zone membership**, with no distance thresholds scattered through the code:
  inside exactly one room zone = that room is the committed room; inside a transition zone = doorway framing (both rooms'
  edges, origin between the two centres, moved only as far as needed to keep the player on screen) and the committed room
  DOES NOT CHANGE; leaving a transition zone into a room zone commits that room (which may be the one the player came
  from: turning back costs nothing and causes no transition). Hysteresis is therefore the transition zone's own extent.
- **Outside every zone** (the case the owner called out: a fighter knocked out of bounds, falling through a pit, flying
  with the debug cursor, a level with gaps between rooms, a KO in flight): never guess a room from stale data and never
  snap. Keep the last committed room for streaming and respawn, switch the camera to a defined fallback (follow the player
  with the level-wide bounds) while they are outside, and return through the normal rule when they re-enter a zone. Log
  once on leaving all zones and once on re-entering, naming the zones.
- Membership uses the fighter's position with a stated reference point (the same point for every system), evaluated once
  per logic frame, and every consumer (camera, chunk streaming window, respawn chunk, blast-zone compensation, mission
  triggers, contact traces) reads that one result.
- Implement the overlap test in Lua now so this can be played immediately. A separate engine job is adding native zones
  (`gd.zone_add`, `on_zone_enter` / `on_zone_exit`, `gd.zones_at(port)`): put the membership source behind one small
  interface so it can switch to the engine's events when they exist, guarded for their absence.
- Offer a debug view: the existing debug overlay line gains the current room, transition zone and committed room; a console
  command `mission zones` lists zones and the player's membership.
Tests as listed above, plus: leaving all zones and re-entering a different room; a transition zone shared by three rooms
(a T-junction); overlapping room zones (refuse at validation with the object names).
