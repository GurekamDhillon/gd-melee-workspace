# Sol runtime checkpoint — 2026-09-30

This is a tested pure integration seam, **not live v2 gameplay**. `main.lua`
still creates the fixed v1 dungeon and writes TBD2. All physical recipes remain
uncertified. No native build, shared launch, install, staging or commit occurred.
Preserve dirty work and saves; resume this patch in place.

## Frozen ownership and evidence

Runtime directory: `melee/worktrees/linux/pc/scripts/examples/roguelite/`.
Owned edits: `adapter.lua`, `route.lua`, `progress.lua` and wrapper
`tools/roguelite/test_route.py`. Runtime worker is frozen; root owns integration
and native driving. `sol_rooms` owns `rooms.lua`, recipes/catalogue and room
installation/tests. Root owns expansion art. Baseline copies of runtime-owned
files are under `_build/sol-runtime-backup/`.

Executed:

```sh
python3 -m unittest discover -s tools/roguelite -p 'test_*.py' -v
python3 tools/roguelite/test_route.py
python3 tools/roguelite/test_progress.py
python3 tools/roguelite/test_adapter.py
python3 tools/roguelite/test_checkpoint.py
python3 tools/roguelite/test_legacy.py
```

Full discovery: 35 named unittest cases passed, plus the independently printed
Lua suites executed at import. Durable output:
`_build/sol-runtime-backup/tests.log`. Final route suite additionally passed
missing-resolved-geometry, unvisited objective and future-generator refusals.
These are engine stubs/pure tests, not certification or normal-speed gameplay.

## Pure APIs to consume

Construct lexical modules; no sandbox `require`:

```lua
local topology = Topology.new(RoomCatalogue, EncounterCatalogue, Progression, Rng)
local adapter = Adapter.new(RoomCatalogue, RoomRecipes)
local routes = Route.new({topology=topology, adapter=adapter,
  progress=Progress, progression=Progression, encounters=EncounterCatalogue})
```

`routes:create(run, opts)` returns `{manifest, view, progress}` or `nil, reason`.
Generation errors/refusal are contained. Each room now stores `geometry`,
`recipe_version`, `recipe_modules`, and optional resolved `encounter_spec` and
`reward_spec`. Specs are copied when `encounters` is injected. Recipe admission
remains strict: create refuses uncertified rooms. Do not certify everything to
get a run. New manifest progress starts at `manifest.start_room`; create does
**not** mutate `run.progress.room`. The caller must synchronize that bridge.

`routes:validate_save(run, manifest, progress)` returns `true` or `false, reason`.
It checks topology, exact versions, resolved geometry against the currently
certified recipe, authored sockets, edge direction/index, seed/run ownership,
room/edge identity sets, claims, pickup/key sources, opened locks and Core counter
mirrors. With `encounters` injected, saved specs must match supported definitions.
A saved geometry change refuses; it is not regenerated. Supporting historical
recipe versions after future edits still requires retained reviewed definitions.

`routes:resume(run, manifest, progress)` returns the same result shape as create
or `nil, reason`, consuming saved values without generation. Some malformed
nested data can still throw in downstream validation; the loader must wrap
semantic validation in `pcall` and treat exceptions as controlled refusal.

`routes:travel(route, exit)` returns **a new progress table** or `nil, reason`.
It does not mutate `route.progress`. Exit must belong to current room with the
right direction/destination/socket. It applies locks, arrival, visited/discovery
and reveal updates to the copy. Assign the result only as part of a room-entry
transaction; rollback it if construction, placement, reward/pickup or persistence
fails. Consumable lock policy matches `progression.lua`: lock identity opens
permanently unless `lock['repeat']=true`; an opened lock charges no return trip.
Repeat tolls charge every crossing.

`routes:collect(route)` returns `true` or `nil, reason`. It transactionally
**replaces** `route.progress` on success. Persistent room keys and stable
one-shot pickups are granted once; overflow leaves the prior record intact.
Accepted pickup data is `room.pickups={{id=...,key=...,amount=...}}` or the
validator's compatibility `grants_consumable`, `pickup_id`, `consumable_amount`.
Do not retain a cached progress reference across collect.

Progress schema is now **2**. `Progress.new` adds `opened`, `pickups` and
`encounter_kos` maps. Old schema is refused, not silently rewritten; it was not
used by the live v1/TBD2 runtime. `Progress.enter` leaves current room unchanged
on capacity refusal. Existing `Progress` methods remain available.

## Adapter and physical room interface

`adapter:manifest(manifest)` returns `{nodes,order,start,final,world_seed,
topology_signature}` or `nil, reason`. Nodes carry legacy-shaped `kind`, stable
instance ID, `room` resolved geometry, `recipe`, `recipe_version`,
`recipe_modules`, `encounter_spec`, `reward_spec` and per-socket exits:

```lua
{edge_id=..., to=..., side=..., socket=..., anchor={x=...,y=...},
 arrival_socket=..., arrival={x=...,y=...}, label=..., kind=...,
 gate=..., hidden=...}
```

Destination arrival is selected by destination socket, then authored side.
Distinct sockets remain distinct at split/merge/return. Use room-worker helpers:

```lua
Rooms.preload_step(state, node) -- one incremental load; state-only retains v1
Rooms.collision(node)          -- {floor_segments,platforms,lines} or nil,reason
Rooms.anchor(node, exit)       -- explicit anchor, then socket/side lookup
Rooms.arrival(node, socket)    -- safe authored arrival
```

`main.lua` must build floor segments instead of its unconditional continuous
floor and construct slopes via real `gd.stage_add_line`. Preserve separate
load/build/place callbacks. Actual ground drop gap is `[-6.5,6.5]`, trigger
`(0,-6)`, safe bottom arrival `(20,0)`. Upper doorway uses solid floor at `(39,26)`.
See the room-worker handoff for physical limitations and budgets.

## Remaining main.lua replacement work

1. Instantiate the service and certified runtime catalogues. Existing data lists
   mechanics that are not implemented. Filter admission or implement them;
   copying an encounter/reward spec is not gameplay. Multiple fighter rows
   cannot automatically map to the single p2 slot.
2. Replace `begin()`'s `Dungeon.generate` on new runs with route create, with an
   explicit logged refusal/fallback while no admitted physical set exists.
   Preserve existing saved v1 runs with the **frozen** `dungeon_v1.lua`.
   `prepare.py` currently bundles `dungeon`, not lexical `DungeonV1`; add the
   frozen module deliberately when wiring migration/resume.
3. Replace local `checkpoint()`, `save()` and `load_data()` TBD2 code with TBD3.
   Existing `Checkpoint.encode/decode` already has separate manifest/progress
   sections. Serialize manifest/progress with `Codec`, Core profile/run with
   `Core.snapshot`, and validate selected/run fighter metadata independently
   with `Roster.decode`. Require route semantics after envelope integrity.
4. Replace `enter(id)`/complete-entry transaction, fixed floor/platform assembly,
   v1-only preload call, per-side exit lookup and spawn selection. Use explicit
   arrival socket when resuming or traversing; preserve incremental yields,
   isolation failure handling and owned-geometry cleanup.
5. Replace literal `approach` enemy choice and legacy fighter encounters with
   stable entities from admitted resolved specs. Persist confirmed defeated IDs
   and encounter stocks. An actor disappearing/escaping is not confirmed defeat;
   current `on_frame()` incorrectly clears such traversal encounters.
6. Resolve reward menus from supported saved specs; current `Menus` offers fixed
   four options regardless of manifest. Save one-time claim `reward:<room_id>`
   only after effect and durable checkpoint succeed. Mirror Core cleared/claimed,
   room, supplies and stocks with Progress objectives/claims/current_room/supplies/
   lives. Rollback **both** on failed reward, finish, entry and save.
7. Use per-socket door proximity, gate refusal and map discovery; retain recursive
   D-pad command precedence and root-only taunt. Test both split branches, both
   merge entries, return traversal, interrupted transition and exact route resume.

## Persistence traps and remaining safeguards

- Legacy `Legacy.migrate(text,{core,codec,checkpoint,v1})` returns TBD3 text with
  frozen v1 manifest but **no Progress section**. Dispatch schema v1 separately;
  do not force it through the v2 service or current generator.
- Current Checkpoint accepts the earlier roster-only TBD3 envelope for parsing.
  That does not make it a valid v2 save without resolved progress.
- Unknown future envelope/generator/progress versions must remain preserved and
  explain refusal. Loading an older valid A/B generation must not overwrite an
  unrecognized future file. Detect this before allowing writes/new runs.
- Native `gd.data_write_atomic(name,text)` is **pending**. Implement and test safe
  temporary-write/flush/rename with existing sandbox filename rules. Feature
  detection/readback fallback must state durability limits. Existing raw writes
  can damage the chosen A/B target; prior generation must remain readable.
- Current semantic checks do not yet prove arbitrary consumable inventory/opened
  lock history or full traversal provenance. Add source/claim/resource consistency
  and adversarial tests before declaring TBD3 safe for all generated content.
- Atomic helper, main wiring, native room admission and exact live save/reload are
  outstanding. Pure green tests do not pass the generated-run/native gate.
