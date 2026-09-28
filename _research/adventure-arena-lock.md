# Adventure Mushroom Kingdom: arena lock

2026-09-27. Source-only research; no builds, gameplay verification or DAT inspection.
Workspace HEAD `7d36c5bd`; game HEAD `2a156901`. Supersedes no earlier note.
Below, `src/` and `pc/` paths are relative to the read-only game checkout
`../../melee`; `docs/` paths are relative to this workspace. Line numbers describe
the files read, including current PC additions.

**Finding:** Mushroom Kingdom has one scripted Yoshi encounter lock, not a sequence
of enemy-count locks for every scrolling section. It moves a camera/bounds origin
with P1, fixes that origin for the encounter, removes selected terrain, and restores
traversal when the fighter-wave manager signals completion. Its separate traversal
zone index is a respawn checkpoint selector.

## Camera and bounds

- `grKinokoRoute_80207634` initializes map object 0 from map markers: camera origin
  `0x94`, camera corners `0x95/0x96`, blast corners `0x97/0x98`; then multiplies the
  four camera extents by **1.5**. Map object 2's `grKinokoRoute_80207A98` loads the
  same marker bounds without that multiplier. Thus creation order matters:
  initialization creates **2,0,1,3**; encounter entry recreates **0,2** (unexpanded
  bounds win); exit recreates **2,0** (expanded camera wins).
  (`src/melee/gr/grkinokoroute.c:107`, `:178`, `:283`, `:417`, `:465`.)
- The underlying loaders are `Ground_801C39C0` and `Ground_801C3BB4`
  (`src/melee/gr/ground.c:2760`, `:2867`). They derive ordered extents relative to
  the camera origin. `Ground_801C38BC` writes that origin (`ground.c:2682`). Both
  `Stage_GetCamBounds*Offset` **and** `Stage_GetBlastZone*Offset` add it back
  (`src/melee/gr/stage.c:43`, `:107`). Scrolling therefore moves world-space KO
  boundaries as well as camera limits; it does not move the whole map.
- Every tick, `grKinokoRoute_80207C88` follows P1 outside phase 2, clamping its
  **camera target copy**, not fighter position: Y to `[20,250] * stage scale`; X
  initially between marker 0 and `0xBD`, and after the encounter no farther left
  than the encounter marker. During phase 2, target = encounter marker + `(0,30)`.
  (`grkinokoroute.c:348`, `:379`, `:442`.)
- With `cam_timer > 0`, the origin advances `(target-current)/remaining`, decrementing
  the timer: a 60-tick transition when entering/exiting the fight. Otherwise it moves
  to **10 units short of the target** if the gap exceeds 10, leaving smaller gaps
  alone; this is not a 10-units-per-frame speed limit (`grkinokoroute.c:480`).
  The `ftLib_80086EC0` flag holds the current origin and resets the timer to 60;
  dead motion states hold it with timer zero (`grkinokoroute.c:371`;
  `src/melee/ft/ftlib.c:698`, `:887`).
- These remain normal match-camera limits, not a detached fixed camera: subjects
  are fitted/clamped by `Camera_8002958C` (`src/melee/cm/camera.c:561`, especially
  `:620`); `Camera_8002A768` applies boundary corrections (`camera.c:1225`, `:1386`).
  `Camera_80030AE0(true/false)` toggles the P1 Z-range special case, **not** the lock
  itself (`camera.c:4717`, `fighter_z_out_of_range`, `:1639`).

## Trigger, encounter, unlock

| State/event | Exact behavior |
|---|---|
| Init | `phase=0`, `zone_idx=0`, `cam_timer=0`, `spawn_idx=-1`; save respawn marker 4 (`grKinokoRoute_80207B5C`, `grkinokoroute.c:321`). No phase-1 assignment appears in this stage. |
| Traversal checkpoints | Passing marker `zone_idx+5` in X increments the index while that marker is below 7: checkpoints 5 and 6. Publish to `stage_info.x6DC` (`grKinokoRoute_80207C88`, `grkinokoroute.c:433`). `Ground_801C5774` returns it; `fn_8016719C` selects respawn via `Stage_80224E38(index+4)` (`ground.c:3973`; `src/melee/gm/gm_1601.c:3395`; `stage.c:231`). These do not load per-section camera rectangles. |
| Encounter entry | While `phase<2`, `Ground_801C3DB4(NULL,60,10000)` returns a matched event marker; set phase 2, reset completion latch, begin 60-tick transition, recreate bounds objects, pause/clear ambient generator (`grkinokoroute.c:403`). |
| Actual position test | `Ground_801C0C2C` scans existing markers `0xBD..0xC6`: strict `abs(dx)<30`, `abs(dy)<5000`, with P1 eligibility check. The stage call arms the scan and reads its stored result; this is marker proximity, not merely `x > constant` (`ground.c:989`, `:1042`, `Ground_801C3DB4`, `:2965`). The separate `Ground_801C3D44(NULL,30,10000)` tests markers `0x99..0xB2` with half-width 15 (`ground.c:1011`, `:2950`). |
| Fight | `gm_801674C4(0x11,10,3,0xB3,grKinokoRoute_80208480)` starts **10 Yoshis, up to 3 active**. `0x11` is `CKind_Yoshi`, not an item enemy (`grkinokoroute.c:413`; `src/melee/ft/forward.h:183`; `gm_1601.c:3522`). |
| Terrain transition | Once phase-2 `cam_timer` reaches zero, call `grKinokoRoute_8020836C(gobj,0)`. Respawn marker 4 is temporarily placed at marker `0xBD` + `(0,50)` and the published checkpoint index is 0 (`grkinokoroute.c:442`). |
| Completion | `fn_8016A4C8` replenishes eligible vacant fighter slots, consuming the pending count. When pending count is zero **and no flagged active slot has stocks**, invoke callback with 1 (`src/melee/gm/gm_16A2.c:785`, `:898`). `grKinokoRoute_80208480` writes the ground completion latch (`grkinokoroute.c:558`; `Ground_801C5740/5750/5764`, `ground.c:3958`). |
| Unlock | Latch 1 makes phase 3, restores terrain and saved respawn marker, enables ambient generator, recreates traversal bounds, and starts another 60-tick transition (`grkinokoroute.c:457`). Phase 3 cannot retrigger the phase `<2` encounter. Timer controls transition/terrain removal, not wave victory. |

The GM spawn manager reserves up to three vacant slots in `fn_8016A09C`
(`gm_16A2.c:539`). Spawn X comes from marker `slot + 0xB3 - 1`; Y is the current
camera top, and each fighter has one stock (`getSpawnPointIndex`, `:738`;
`fn_8016A4C8`, `:820`). The Adventure scene table also identifies this route's
Yoshi opponents (`gm_803DE650`, `src/melee/gm/gmadventure.c:700`). The completion
callback is not exclusively a victory hook: P1's route respawn cleanup also calls
`fn_80169444(2)`, whose argument is `bool`, thus reaching this callback as true
(`gm_80167320`, `gm_1601.c:3484`; `gm_16A2.c:77`).

## What physically blocks progress?

`grKinokoRoute_8020836C` hides JObj subtree `0x53` and **disables** collision joints
`0x3C,0x33,0x0C,0x0D,0x0E,0x0F` during the fight; unlock shows it and re-enables
those joints. It also switches `It_PKind_Random` material-item interaction via
`grMaterial_801C8E28/801C8E08` (`grkinokoroute.c:511`). `mpLib_80057BC0` removes a
joint from the active collision list and clears its line-enable flags;
`mpJointListAdd` reverses that (`src/melee/mp/mplib.c:5552`, `:5459`). These are
collision **group IDs**, not individual line IDs.

**Read:** fixed regional blast zones plus disappearing/reappearing geometry.
**Not established:** new invisible walls. This routine removes existing collision;
it does not create walls or clamp fighter X. **Inference:** removing connecting
terrain isolates the fight platform, with regional KO boundaries penalizing escape.
Without DAT geometry, the exact bridges/walls/floors represented by these groups,
their coordinates, and whether an existing invisible boundary is among them remain
unverified. Camera confinement alone is not a physical barrier.

## Ambient enemies and data ownership

- `grKinokoRoute_802074D8` passes `yakumono_param->x4` to the ambient generator
  (`grkinokoroute.c:129`). `grZakoGenerator_801CA67C` assigns 80 marker slots
  `0x20..0x6F` (`src/melee/gr/grzakogenerator.c:123`).
  `grZakoGenerator_801CA8B4` spawns by marker position inside current blast bounds;
  normal ticks exclude the inner rectangle halfway between camera and blast
  bounds. Initial `grZakoGenerator_801CADE0` bypasses that inner exclusion
  (`grzakogenerator.c:147`, `:308`). Thus scrolling bounds activate ambient enemies;
  they are not keyed to `zone_idx` or counted for Yoshi victory.
- `grZakoGenerator_801CACB8` marks a defeated entry exhausted or gives it a
  `0x708`-tick respawn delay according to its descriptor. Encounter entry's
  `grZakoGenerator_801CAF08` disables generation and removes eligible enemy/item
  kinds; exit's `grZakoGenerator_801CAEF0(true)` resumes it
  (`grzakogenerator.c:273`, `:349`, `:344`).
- **DAT data:** `/GrNKr.dat` supplies map hierarchy/markers, `coll_data`,
  `grGroundParam`, `itemdata`, and `yakumono_param`; the latter supplies ambient
  spawn descriptors. See `grNKr_StageData` (`grkinokoroute.c:89`) and archive symbol
  loading (`src/melee/gr/grdatfiles.c:58`, `:66`, `:78`). Marker lookup transforms
  the referenced JObj into world coordinates (`Ground_801C2D24`, `ground.c:2210`).
  Exact numerical marker coordinates and descriptor contents were not read.
- **Code:** phase transitions, marker/group IDs, thresholds, 1.5 camera expansion,
  60-tick interpolation, ten-Yoshi/three-slot configuration, and the 51-entry
  breakable-material joint table (`grNKr_803B82F4`, `grkinokoroute.c:50`;
  `grKinokoRoute_80208564`, `:594`). There is no general table of arena sections
  in this stage's C source.

Cross-check: Shrine implements repeated marker encounters, a completion bitmask,
collision toggles and one-Link fights in `grShrineRoute_80208F70`
(`src/melee/gr/grshrineroute.c:405`, `:587`, `:598`). Big Blue's
`grBigBlueRoute_8020DED4` clamps a scrolling origin (`grbigblueroute.c:1165`);
Zebes' `grZebesRoute_8020B42C` scrolls vertically and counts down to a quake
(`grzebesroute.c:180`). These share primitives, not one universal section-lock system.

## Reuse in our Lua engine (proposal, not implemented here)

| Piece | Available now / missing |
|---|---|
| Section controller | Lua can compare P1 position with authored section rectangles, own a `travel -> fighting -> cleared` state and timers, and track only successfully spawned wave handles. Unlock when its own pending queue and live set are empty. This needs no retail route state machine. |
| Camera | `gd.camera_move/set/follow` can frame and tween a locked arena; `gd.camera_attach` returns control. `gd.camera_bounds(true)` **lifts** clamps; it does not set a rectangle or move blast zones (`pc/platform/gw_script.c:852`, registrations `:5047`; `docs/scripting.md:375`). Use manual framing now; adaptive normal-camera confinement needs the pending bounds hook. |
| Physical gates | `gd.stage_add_line` creates actual wall/floor/ceiling collision; retain handles and `gd.stage_remove` on clear, or `gd.stage_move` for moving gates (`l_stage_add_line/remove/move`, `pc/platform/gw_script.c:4830`, `:4875`, `:4885`). Respect wall orientation, cover jump routes, and handle collision-pool exhaustion. Default walls draw bars; `gd.stage_view` hides script geometry globally (`:4900`), not collision. |
| Gate models | Current source registers **`gd.model_load/spawn/move/set/despawn/get`** (`gw_script.c:5088`), newer than the scripting overview. `l_model_spawn` imports asset collision unless `collision=false`; despawn removes the instance; model-owned lines must be moved/removed via model APIs (`pc/platform/gw_script_model_api.inc:82`, `:103`, `:141`, `:159`; `gw_script.c:4878`). A collidable gate model can therefore own its barrier; `visible=false` alone is not a collision-disable request. The older `gd.stage_add_model`/attached-floor surface is also documented (`docs/scripting.md:335`). |
| Waves | `gd.spawn_enemy` supports goomba, koopa, redead, like_like, octorok, polar_bear; `on_enemy_defeated{kind,handle}` identifies stock defeats (`gw_script.c:4922`, `:4926`, `:6694`; `pc/gameworld/script_game.c:1148`). `gd.enemy_remove` is cleanup, not a defeat. Koopa-to-shell is not a defeat event. These APIs do not spawn Yoshi fighter waves (`docs/scripting.md:394`). |
| `gd.stage_bounds` (upcoming) | No registration/implementation found in this checkout. Needed contract: read/set/restore camera rectangle and blast rectangle separately, with explicit world-vs-origin-relative semantics; apply reliably against native stage updates and restore on unload/scene change. Do not invent its Lua signature. Native primitives already exist in `Ground_801C3880..38BC` and `Ground_801C3980..39B0` (`ground.c:2662`, `:2740`). Bounds create camera/KO limits, not solid gates. |

Additional native hooks **only if required for the stronger version**: address and
toggle existing stage collision groups/visual subtrees (the Lua line API controls
its own handles); enumerate script enemies and distinguish defeat/despawn so a
wave cannot remain locked after non-defeat removal or savestate restoration; and
a fighter-wave spawn/lifecycle API for retail-style Yoshis. Lua bookkeeping is not
snapshotted (`docs/scripting.md:403`). An ordinary offline item-enemy wave with
scripted gates and a manually framed camera can use today's APIs; claiming it
works on *any* stage still requires handling native hazards/moving terrain,
capacity limits, and camera/bounds ownership.
