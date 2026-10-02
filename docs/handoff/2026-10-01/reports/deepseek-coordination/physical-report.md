I'll start by reading the required checkpoint docs and understanding the existing modules.

The game checkout is embedded at `melee/worktrees/linux`. Let me read the key modules.

Now I have enough context. Let me set up a todo list and inspect a couple more details (progress/route integration, `Rooms.view`).

Now writing the runtime module.

Found a bug: `commit` sets `tx.done` before calling `self:arrival(tx)`. Let me fix.

Let me verify model budgets and that ascent rooms load under `Rooms.max_assets`, then write the test wrapper.

Now I'll write the wrapper test file.

The tests pass outcomes where room tokens are expected. Let me fix all four bodies.

All 7 pass. Now let me run the full roguelite suite and check for regressions.

Let me strengthen the drop test to also verify the segmented floor is built without filling the opening.

Let me review the final module once more.

Two small refinements: match the checkpoint's construction order (floors, slopes, platforms) and drop the unused `placed` field from the room view.

Let me add explicit merge-entry and one-way-direction coverage.

Let me also cover visual-instance allocation refusal rolling back already-built collision.

Done. Two new files only; no tracked file edited, nothing staged or committed.

## Owned files
- `melee/worktrees/linux/pc/scripts/examples/roguelite/runtime_rooms.lua` (new, 304 lines, game repo)
- `tools/roguelite/test_physical_runtime.py` (new, 388 lines, workspace repo)

Dirty baseline (`adapter/progress/room_recipes/rooms/route.lua`, docs, existing tests) untouched. `git diff --check` clean in both repos.

## API / return shapes
`RuntimeRooms.new(engine, rooms, opts)` — injected; `engine` is `gd`'s stage/model surface (`stage_isolate`, `stage_add_platform`, `stage_add_line`, `stage_remove`, optional `teleport`), `rooms` is the `Rooms` module. `opts={max_lines=16,max_total_lines=32,drop_margin=4,door_reach=13,vertical_reach=10}`.

- `:isolated() -> bool` (checked precondition; never toggled here)
- `:resolve_exit(source_node,dest_node,exit) -> info | nil,reason`; `info={trigger,arrival,side,socket,arrival_socket,to,edge_id,kind,label,drop[,opening]}`. Source socket → trigger (`Rooms.anchor`, explicit anchor first); destination socket → arrival (`Rooms.arrival(socket)` then `exit.arrival`). Canonical adapter exits, no room-ID/two-door whitelist.
- `:triggered(info,player[,floor]) -> bool`; drop needs `y < floor.y-drop_margin` inside the authored opening, never proximity while standing.
- `:begin(dest_node,{from=room_token,exit=adapter_exit}) -> tx | nil,reason` — validates isolation, plan/collision, per-room + total line budgets, exit resolution; allocates nothing.
- `:step(tx) -> 'loading' | 'ready' | nil,reason` — one asset load per `'loading'`; `'ready'` after collision (floor segments → `stage_add_line` slopes → platforms) + visuals; failure rolls destination back and leaves source intact.
- `:place(tx,{{port=,x=,y=},...}) -> true | nil,reason` (no callbacks)
- `:arrival(tx) -> {x,y,facing}`
- `:commit(tx) -> outcome,reason`; `outcome={room_id,room={room_id,theme,instances,assets,line_count,lines,error},arrival,spawn,released,room_ref}`; source teardown refusal → `released=false` + `:pending()`, retried by `:flush()`.
- `:rollback(tx) -> true | false,reason` — destroys only destination, retains refused handles for retry.
- `:flush()`, `:active_room()`, `:view_active()`, `:pending()`, `:total()`, `:view(room)`.

Transaction state is explicit tables; after commit `tx.done`, `busy` cleared. No hidden callbacks or stale pointers.

## Commands / results
- `python3 tools/roguelite/test_physical_runtime.py -v` → 7 passed.
- `python3 -m unittest discover -s tools/roguelite -p 'test_*.py'` → Ran 44, OK (skipped=1).
- `luac5.4 -p .../runtime_rooms.lua` OK; `python3 -m py_compile tools/roguelite/test_physical_runtime.py` OK.

Tests run real `Rng/RoomCatalogue/RoomRecipes/EncounterCatalogue/Progression/Topology/Adapter/Rooms` with a test-only `Adapter` admission wrapper (`is_certified=true`) and a fake engine. Coverage: translated floor segments/slope endpoints, incremental preload, source/destination sockets (upper, merge, return), one-way drop, allocation/visual-placement refusal, partial-cleanup retry, isolation interruption, dual-residency/total-line bounds, open drop gap, and the strict uncertified adapter gate.

## Root integration notes
- Add `('runtime_rooms','RuntimeRooms')` to `prepare.py`'s bundle list before `main.lua`.
- `main`: construct with `gd` (Rooms reads global `gd`; injected engine must be that same table), keep `gd.stage_isolate(true)` before `begin` and `false` on unload.
- Replace inline floor/platform assembly and per-side exit lookup with `:resolve_exit`/`:triggered`; replace the v1-only `Rooms.preload_step(room_visuals)` loop with the transaction's `:step`. First room is `begin(dest)`; transitions are `begin(dest,{from=active_room(),exit=adapter_exit})`.
- Sequence: `step` → `'ready'` → `:place` from `:arrival` → `commit`; only then assign `Route:travel/collect/save`. On failure call `:rollback` (do not commit logical state). If `commit` returns `released=false`, call `:flush()` until clean.
- `draw=false` is passed on added lines (model instances render); this needs the current `gs_stage_opts` `draw` support in root's native source (embedded snapshot lacks it; tests stub it).

## Limitations (reported, not hidden)
- The engine has no per-room grouping: during a build both rooms' colliders/instances are live in the same isolated stage (bounded ≤ `max_total_lines`; two rooms fit native cap 200 lines / 32 assets / 128 instances). Source is never destroyed before commit, so destination rollback leaves the source exactly as it was.
- A resident source cannot be hidden/paused (`stage_remove`/`model_despawn` are destructive). A refused source teardown is a reported leak window (`released=false`, `:pending()`), retried by `:flush()`.
- This module does not certify recipes; the adapter/Route gate stays upstream. These are fake-engine, pure tests — no native build, run, live gameplay or certification.
