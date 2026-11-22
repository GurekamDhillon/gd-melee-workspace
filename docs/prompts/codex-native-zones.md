# Codex packet W: native zones (non-physical trigger volumes) (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `melee/pc/geno/CLAUDE.md`, `docs/scripting.md`). Both trees are deliberately dirty: do NOT
commit, reset, stash, revert or reformat. Do NOT run `tools/port/build.sh`, do NOT launch the game. Keep every file
compilable at every save. Other Codex jobs are editing `melee/src/melee/gr/`, `pc/gameworld/script_stage_slots*`,
`ft/ftcommon.c`, `gw_script_items.inc` and Lua mods: put your code in NEW files; touch shared files (registration tables,
the frame hooks) last, small, after re-reading them.

## The owner's idea (verbatim)
"We could also use geno collision detection with our custom objects and place a "no physics" bounding box across each
room, and each transition period to have a proper track of where the character is. (Taking care of the situation where we
are not in a bounded area)".
It came from playing a room-based level whose camera fought itself at doorways because room membership was derived from
rectangles and movement direction in script. A Lua job is redesigning that camera on explicit room and transition zones
(`docs/prompts/codex-mission-runtime-fix9.md`, section "ADDED") with a Lua overlap test for now. This packet gives the
engine the general capability, so membership is computed once, natively, deterministically, and every system can use it.

## Build
1. **Zones.** A zone is a named, non-physical volume attached to the level: an axis-aligned rectangle in the gameplay plane
   (and, if contained, a convex polygon), with a kind string (`room`, `transition`, `trigger`, free-form), a label, optional
   tags, and an owner script. Zones never collide, never appear in the game's collision tables, cost nothing when none
   exist, and may follow a scripted model instance (a zone bound to a moving platform or a streamed chunk moves and is
   removed with it). `gd.zone_add{...}` -> handle; `gd.zone_set(handle, {...})`; `gd.zone_remove(handle)`;
   `gd.zones()`; capacity stated and refused cleanly beyond it.
2. **Membership, computed once per logic frame, natively**, for every fighter entity (all six slots, sub-fighters such as
   Nana reported with their owner), and optionally for items (standalone Geno items first), using ONE documented reference
   point per entity (state it: the fighter's position/TopN versus ECB centre: choose from how the game treats "where the
   fighter is" for blast zones, and say why), with the previous frame's membership kept.
   `gd.zones_at(port)` -> the zones containing that fighter now (ordered by kind then area), with time-in-zone;
   `gd.zone_members(handle)`; `gd.point_zones(x, y)`.
3. **Events**: `on_zone_enter{zone=, label=, kind=, port=, entity=, x=, y=, from=}` and `on_zone_exit{...}` (and
   `on_zone_none{port=}` / `on_zone_some{port=}` when a fighter leaves every zone or re-enters one: the owner's "not in a
   bounded area" case), queued like the existing events, armed only when a script defines the hook (the LAB events test
   guards that invariant: do not weaken it), exactly one event per real transition (no chatter from a fighter standing on a
   boundary: define the boundary rule: half-open intervals or a small configurable skin), and correct across teleport,
   respawn, bench/call, stage switch and scene change (a membership that ends because the fighter or the zone went away
   emits its exit).
4. **Deterministic and snapshot-safe**: zone definitions and membership live where LAB savestates/rewind and rollback
   capture them, or are re-derived each frame from state that is; say which and prove it with a rewind fixture (0 differing
   bytes with zones present). Zone definition writes are gameplay writes (the usual offline gate) only if they can affect
   game state; reading membership is always allowed. State what it would take for zones to be used online.
5. **Integration with what exists**: contact traces and `gd.contacts(port)` gain the current zones; `gd.wait_until{...}`
   accepts `zone=` (wait until inside a named zone) and its failure sentence names the zone the fighter was in instead;
   the debug overlay line shows zone membership; the profiler gets a zone for the membership pass.
6. **Geno**: say how zones relate to the Geno layer (a level described by Geno stage data would declare its zones as data):
   reserve the encoding now if that is cheap; do not build the stage layer.
7. A demo for the catalogue (`melee/pc/scripts/examples/demos/`): "zones": two rooms and a transition zone drawn as
   outlines, text showing which zone each fighter is in, and the enter/exit events logged (project rule: every capability
   ships with a single-feature demo; check your `gd.` calls against the registration tables).
Tests in the suite's pattern: overlap on edges and corners, one event per transition, standing on a boundary, teleport and
respawn, zone bound to a moving instance, capacity, cleanup on unload and scene change, rewind exactness, the
none/some events. `docs/scripting.md` section "Zones".
Report `_build/tmp/codex-native-zones-report.md`: signatures, file:line, the reference point and boundary rule, cost, the
snapshot story, and a native test plan (the room-and-doorway cases: stop in a doorway, turn back, dash across ten times,
get knocked out of every zone and come back).
