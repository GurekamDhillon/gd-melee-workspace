# Stage seam collision research (read-only)

Lane: `_build/deepseek-worktrees/stage-seams`. Sources read from this lane's read-only game
checkout (`melee/worktrees/linux`, clean at HEAD) plus the parallel `sol-worktrees/native-owner-cleanup`
lane (read only; not edited). Human report: snag/pop at all three ascent joins
stairs->balcony, balcony->ramp, ramp->upper-landing. This file is the only write.

## 1. What actually happens at a seam

The scripted floor lines are one independent `MapLine`/joint each and carry no adjacency:

- `ScriptGame_StageReady` zeroes `prev_id0/next_id0/prev_id1/next_id1` for every reserved slot
  (`pc/gameworld/script_game.c:586`) and `ScriptGame_StageAddLine` never sets them
  (`pc/gameworld/script_game.c:620-680`); it writes one vertex pair, one `MapLine`, one `MapJoint`,
  then `mpJointListAdd(j)` (`:675`). `StageAddLine` is the shared body of `gd.stage_add_platform`
  and `gd.stage_add_line` (`pc/platform/gw_script.c:4929,4956`).
- Grounded fighters follow the **link graph**, not raw geometry. Per grounded frame
  `mpColl_80044838_Floor` (`src/melee/mp/mpcoll.c:1504`) calls `mpLib_8004DD90_Floor(floor.index,...)`
  (`:1519`); when that returns -1 it clamps `cur_pos` to `mpFloorGetLeft`/`mpFloorGetRight`
  and re-queries (`:1525-1537`). That clamp is the visible snag.
- `mpLib_8004DD90_Floor` (`src/melee/mp/mplib.c:1102`) walks left/right with `mpLineGetPrev`/`mpLineGetNext`,
  allowing a 0.1 overshoot before giving up (`:1125,:1143`).
- `mpLineGetNext` (`mplib.c:1028`) tries `next_id1` **only if** the target is enabled, not hidden and
  `dist(this.v1, target.v0)^2 < 4.0` (2 world units), else falls back to `next_id0` with **no** check.
  `mpLineGetPrev` (`:1049`) is symmetric on `prev_id1`/`prev_id0`.
- `mpCheckFloor` extends each line's endpoints by 1.0 unit along its direction when
  `mpLineGetPrev/Next != -1` (`mpLib_8004ED5C`, `mplib.c:1591-1608`). No link => no 1-unit overlap
  => the movement segment can cross a join and miss the next line for a frame.
- `mpLinesConnected` (`mplib.c:4607`), `mpIsland_8005A728` floor islands (`src/melee/mp/mpisland.c:103`),
  dynamic islands `mpIsland_8005B004` (`mpisland.c:496,515,547`), `mpLib_80053DA4_Floor`
  (`mplib.c:4129`) and `mpFloorGetRight` (`mplib.c:4188`) all read the same fields.

So unlinked adjacent floors are separate islands: the follow query dead-ends at the shared vertex
and clamps, then the next frame `mpColl_8004A908_Floor` (`mpcoll.c:3777-3834`) may adopt the
neighbour via `mpCheckFloor`. One-frame clamp + re-acquire = the snag/pop, and it fits all three
joins being endpoint-to-endpoint between *different joints*.

## 2. The ascent geometry (facts)

`runtime_rooms.lua:170-181` adds `collision.floor_segments` as platforms first, then `collision.lines`
(slopes), then platforms. `room_recipes.lua:88-91` gives the slopes and `:63-66` the solid landings;
`ASCENT_MODULES` is `:28-34`:

- stairs `(-52,0)->(-26,13)`; balcony platform `-26..0 @13`; ramp `(0,13)->(26,26)`;
  upper landing platform `26..52 @26`.
- joins are exact: stairs.v1 = balcony.v0 = `(-26,13)`; balcony.v1 = ramp.v0 = `(0,13)`;
  ramp.v1 = landing.v0 = `(26,26)`. All kind=floor, all different joints.
- The main floor in these recipes is one platform `-65..65 @0`, so stairs.v0 `(-52,0)` is a
  **T** on it, not an endpoint; `combat_flank` (`room_recipes.lua:143-150`) is the same pattern.

## 3. Link encoding: facts and one hypothesis

`MapLine` (`src/melee/mp/types.h:47-56`). From the traversal code above, for a floor A (v0 left,
v1 right) whose v1 meets B's v0, a forward link is `A.next_id1 = B` (validated) and the fallback
`A.next_id0 = B`; the reverse is `B.prev_id1 = B.prev_id0 = A`. `mpPruneEmptyLines` remaps
`*_id1` onto `*_id0` when a line is collapsed (`mplib.c:861-872`), i.e. the two encode the same
directional chain. The project's own reader walks `prev_id0`/`next_id0`
(`pc/gameworld/script_bounds.inc:40`) and its fixture sets only those
(`pc/tests/stage_bounds_test.c:44,57`).

**Hypothesis (unverified):** vanilla disc map data fills both `_id0` and `_id1` for a same-kind
neighbour. The decomp has no link *builder* (adjacency is baked into `coll_data`), and no
disc-derived `MapLine` dump exists in this checkout, so I could not confirm it. Set both, then test.

**Safety fact:** `*_id0` has no enabled/hidden/proximity guard, and its consumers check only the
kind bit (e.g. `mpLib_80053DA4_Floor`, `mplib.c:4129-4131`). A stale `_id0` pointing at a removed
line is still walked. Links must therefore be cleared, never left stale.

## 4. Recommendation (bounded)

Weld automatically in native code (the Lua layer has no map indices), with an explicit override only
for ambiguity. Per dynamic floor-line endpoint, link to another dynamic floor endpoint when **all**:

1. exact match within `EPS` (~0.05 world units; well inside the 2.0 `_id1` guard and the 13-unit grid);
2. same `kind` (floor) and same owner/group — use the `owner` already added by the sol lane
   (`script_stage_owner.inc`; assigned at `script_game.c:687`) or an equivalent group id;
3. the candidate matches at **its opposite endpoint** (A.v1<->B.v0), not mid-segment (rejects the
   main-floor T and other intersections);
4. uniqueness: exactly one candidate within `EPS`; a branch/overlap (>1) or none stays -1; never
   link an end that is already linked (degree <= 1);
5. write both `next_id0` and `next_id1` (resp. `prev_id0`/`prev_id1`) to `B`/`A`; otherwise all -1.

Recompute by clearing every dynamic line's four link fields and re-welding, **before**
`mpJointListAdd` so `mpIsland_8005B004` sees them, on add, remove, move/set. Best-effort `mpLib_8005667C(j)`
after a move re-runs the island refresh (`mplib.c:5076`). Removal: fully clear then re-weld the
survivors. Reset already zeroes the map (`script_game.c:586`).

Dual rooms: `runtime_rooms.lua` builds the destination while the source is still resident and
gameplay is paused (`:20-26`). Because the two rooms have different owners, rule 2 prevents any
cross-room weld; no special "paused" handling is needed if the weld is owner-scoped. Commit removes
the source, so its links must be cleared and the destination re-welded.

Snapshots: `gw_snap.c:196` includes `pc_gameworld_script_game.c.obj`, and the map (`map->lines`) is
game MEM1, so the link bytes restore with the pointer. **Do not** re-weld after restore; a
post-restore native recompute would be unsnapshotted state. Verify with `gd.rewind_test` (hypothesis).

Auto vs explicit: auto-weld is right here because authors already emit exact endpoints
(`room_recipes.lua`). Add only `seam="off"` (suppress) or an explicit `gd.stage_link(a,b)`/`seam=<handle>`
for genuinely ambiguous authors; do not require handles for the common case.

## 5. Tests (actual source; Windows run is the only acceptance)

1. Link builder against a synthetic `MapCollData`: exact endpoints weld; 3-unit gap does not;
   three lines at one point stay unmatched; T-junction not welded; opposite owner not welded;
   passthrough slope <-> solid landing **do** weld (walking needs it).
2. Removal: build A-B, remove B, assert A's four fields are -1, `mpLineGetNext(A) == -1`,
   `mpLinesConnected(A,B) == false`; re-add B and assert reweld.
3. Move: move B > 2 units, assert the validated `_id1` fails **and** no stale `_id0` resurrects it;
   move back and assert reweld.
4. Rebuild ordering: add stairs/balcony/ramp/landing, assert `mpLib_8004DD90_Floor` walks
   stairs.v1 -> balcony -> ramp without -1 and `mpIsland_8005AB54` groups them.
5. Owner boundary: dual-room (owner A + owner B sharing a point) has no cross link; after commit
   removes A the destination links are intact.
6. Native controller: extend `docs/ROGUELITE-WATCHED-RETESTS.md` with a short ordinary walk across
   each join at 60 Hz, asserting grounded continuity (no positive->negative y snap, no `Collide_Edge`),
   before/after. Only this verifies the on-screen pop; off Windows only PowerPC syntax-check and the
   link/traversal arithmetic can be checked.

## 6. Confidence

Facts: unlinked dynamic lines; the follow/clamp path; the `_id1`-validated / `_id0`-unvalidated
split; the three exact joins; `_id0` consumers ignore enabled/hidden.
Hypotheses needing a test: vanilla sets both id fields; island rebuild ordering after late welding;
snapshot restore without recompute. Unverified from disc data: the exact vanilla encoding.
