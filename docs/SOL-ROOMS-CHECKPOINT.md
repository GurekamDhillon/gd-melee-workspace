# Sol 6.1 physical-room checkpoint — 2026-09-30

Pure implementation ready for runtime wiring. **Not installed or native certified.**
All recipes remain `certified=false`; normal adapter admission still refuses them.
The live `main.lua` remains v1 until the separate runtime integration lands.

## Owned changes

- `melee/worktrees/linux/pc/scripts/examples/roguelite/rooms.lua`: version 3,
  recipe-driven visual planner plus collision/socket helpers; legacy planner preserved.
- `room_recipes.lua` in the same directory: recipe versions 2, actual ascent
  slopes, solid upper landing, real ground opening, checked safe arrivals.
- `tools/roguelite/test_rooms.py`, `test_room_recipes.py`: physical regressions.
- `room_catalogue.lua` and `prepare.py` unchanged: existing 28-part/16-collision
  contract and full 21-model installer suffice. Root owns art-brief corrections.

## Runtime API

```lua
local state = Rooms.new()
local plan, why = Rooms.plan(node)        -- pure; nil + reason on refusal
local geometry, why = Rooms.collision(node)
local anchor = Rooms.anchor(node, exit)  -- copy of exit.anchor, else socket/side anchor
local arrival = Rooms.arrival(node, socket_id) -- copy; nil for unknown socket
local loaded, why = Rooms.preload_step(state, node) -- false=yield, true=ready, nil=failed
local ok, count_or_why = Rooms.enter(state, node)   -- visuals only, no collision
local cleared, why = Rooms.clear(state)
local released, why = Rooms.release(state)
Rooms.reset(state)                       -- only after native scene teardown
```

V2 `node` needs `id`, `template_id`, `recipe`, `room`, `exits`, and
`recipe_modules` for ascent rooms. Adapter supplies resolved snapshot fields,
including `recipe_version`; planner never regenerates geometry by room ID.
`room` contains `floor`, `kit`, `platforms`, `lines`, `exit_anchors`, `arrivals`.
Recipe arrivals are keyed by side. Adapter remaps them to actual socket IDs.
Exit shape is `{side,socket,anchor,to,...}`; explicit `anchor` takes precedence.

`Rooms.collision` returns:

```lua
{
 floor_segments = {{left=-65,right=-6.5,y=0},{left=6.5,right=65,y=0}},
 platforms = {{x=-13,y=13,width=26,passthrough=false,ledges=false}, ...},
 lines = {{x0=-52,y0=0,x1=-26,y1=13,kind='floor',passthrough=true,ledges=false}, ...}
}
```

The example floor segments are for a drop room. Rooms without openings return
one full segment. `Rooms.plan` v2 additionally returns `parts` (model transform
records with `collision=false`), `room_id`, `theme`, and copied `anchors` and
`arrivals`; its collision fields have the same shape. Legacy plan retains its
old shape, while `Rooms.collision` also handles legacy geometry.

`RoomRecipes.floor_segments(floor)` is the corresponding pure recipe validator.
`RoomRecipes.resolve(template)` returns geometry and recipe, independent of
certification. `is_certified` remains the admission gate.

## Geometry corrections

- Stairs `(-39,0)`: exact exporter slope `(-52,0) -> (-26,13)`.
- Balcony `(-13,13)`: solid 26-unit landing; no internal ledge flags.
- Ramp `(13,13)`: exact exporter slope `(0,13) -> (26,26)`.
- Upper floor `(39,26)`: **solid `bf_floor_4m`**, not the opening variant.
  The latter's gap was directly underneath the doorway and nominal arrival.
- Upper doorway `(39,26)`, mirrored `scale_x=-1`, matching top anchor.
- Bottom ground bay uses `bf_floor_opening_4m` at `(0,0)`: actual gap
  `[-6.5,6.5]`, width 13. No invisible continuous floor fills it.
- Bottom exit anchor `(0,-6,drop=true)` distinguishes the falling trigger from
  ground-level doors. Safe incoming bottom arrival is `(20,0,facing=-1)`,
  outside the hole. Other side arrivals: left `(-42,0,+1)`, right `(42,0,-1)`,
  top `(39,26,-1)`. Native body-clearance and trigger margins remain unproved.

## Lifecycle and main.lua wiring

1. Validate destination and call `preload_step(state, destination_node)` each
   frame before retiring the outgoing room. It loads at most one missing model
   per call and yields even after the last disk load. Calling with only `state`
   retains the six-model v1 preload. Failures latch until teardown/reset.
2. Construct every returned floor segment with `gd.stage_add_platform(center,
   y,width,{passthrough=false,ledges=true})`; never construct a full floor over
   `floor.openings`. Construct returned platforms using their own flags.
3. Construct each slope with `gd.stage_add_line(x0,y0,x1,y1,'floor',flags)`.
   The native API already exists. Track and retire all collision handles with
   the existing `platforms` ownership list. Model instances suppress sidecar
   collision, so these explicit lines are the only physical ascent.
4. Use explicit destination exit `arrival`/`arrival_socket` and
   `Rooms.arrival`; use `Rooms.anchor` for trigger and label projection.
   Gate drop activation on actual downward passage below the floor, rather
   than a broad distance test that activates from a standing ground position.
5. Check isolation, placement and checkpoint success before enabling combat
   and advancement. Keep old logical state until destination construction and
   persistence succeed; failed partial construction needs owned cleanup.

Budget: 28 visual instances, 10 cached model assets, at most 16 explicit
collision lines. Current ascent layouts use 26 instances. `enter` reuses cached
assets; refused despawns retain ownership and block subsequent enter/release.
`release` clears instances before releasing immutable asset references. `reset`
makes no native calls and must follow actual engine scene teardown.

## Verification

```sh
cd /home/gd/melee_linux_test/gdm
python3 -m unittest discover -s tools/roguelite -p test_rooms.py -q
python3 tools/roguelite/test_room_recipes.py
```

Passed: 13 named room tests, plus recipe script covering 20 templates. New
coverage checks all socket layouts without fixed IDs, incremental v2 preload,
cleanup/cache limits, segmented drops, invalid collision refusal, safe-arrival
validation, and slopes/opening widths against independent BF exporter
sidecars. Installer input sidecars must match the reviewed exporter records;
collider endpoints are checked against actual exported GXMS vertex bounds.
Owned `git diff --check` passes. These are pure/native-parser checks, not game
movement evidence. Sibling owns full route/integration suite results.

## Native work still required

Use an isolated profile and coordinate one shared build/game owner. For each
admitted recipe, capture normal-speed controller movement and fighting with
build ID, recipe version 2, assets and mobility contract `bf-walk-jump-v2`.
Debug teleportation/flight may inspect layout but cannot certify it.

- `branch_y`: floor -> stairs -> balcony -> ramp -> top door, top arrival ->
  ground return, both branch exits, fighting/knockback on both elevations.
- `rejoin_merge`: left and top incoming arrivals; safe merge progression and
  return through every bidirectional connection.
- `junction_cross`: all four sockets, actual fall through the 13-unit gap,
  trigger window at y=-6, destination landing, one-way refusal and alternate
  graph return. Check whether larger fighter feet can fall through naturally.
- `shortcut_door`: same drop/landing/directionality coverage without ascent.
- Other balcony/fork/tiered/rest recipes: certify each admitted variant, not
  just a shared helper. Other flat/platform layouts need their own native
  traversal/combat and arrival evidence as well.
- Short/heavy, floaty, fast-faller and multiple-jump fighters: ordinary-control
  ascent/return, seam pops, underside/body clearance, safe arrivals, fighting,
  camera/blast bounds and recovery. Record margins and failures.

Keep certification false until evidence is reviewed and recorded. Geometry
changes invalidate earlier certification. New content or artificial blanket
certification is outside this checkpoint.
