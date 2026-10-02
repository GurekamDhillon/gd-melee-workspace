I'll start by reading the referenced docs and inspecting the actual module contracts.

Let me read the other key docs and locate the game checkout.

This is a substantial integration task. Let me set up tracking and read the core module contracts.

Now let me read prepare.py, route.lua, progress.lua, and the test harness.

Now the big one, main.lua. Let me read it in full.

Let me read the catalogue/recipe modules and the helper-runtime tests to learn the expected interfaces.

I now have enough context. Let me update my todos and start implementing the campaign module.

Now the main.lua integration. First, refactor `save()` to support staged overrides.

Let me run the existing v1 test suite to check for regressions.

The seeded `test_runtime.py` has a pre-existing Lua statement-separator defect (the new `gd.data_write_atomic=...` line runs into the following `(function()`). Let me verify my changes don't break v1 by running a temp-patched copy, and run the rest of the suite.

v1 runtime behavior is preserved (all Lua prints passed); the only failure is the missing art asset, which is expected in this isolated lane. Let me run the focused pure/helper suites.

I see — the seeded `test_persistence.py` encodes the pre-integration v2-refusal contract and its stub lacks `stage_add_line`. I'll add a graceful engine-capability gate so an incapable engine refuses v2 traversal (preserving that behavior) while a capable engine gets live play.

Now the main deliverable: `test_v2_runtime.py`. Let me write it with a deterministic stub, real modules, and focused API coverage.

Main's v2 path must enable empty-stage isolation (v1's `enter()` did). Let me add that and then the main-integration tests.

All 10 new tests pass. Let me run the broader legacy suite to confirm no regressions.

Let me add diagnostic smoke coverage (draw, commands, callbacks, supply) to the main integration test to catch runtime errors in those paths.

Bounded live v2 integration implemented and tested. Stopping editing so root can land.

## Owned files changed

- **game `pc/scripts/examples/roguelite/runtime_campaign.lua`** (new, 649 lines) — engine-injected v2 run controller.
- **game `pc/scripts/examples/roguelite/main.lua`** — v1/v2 dispatch, save refactor, callbacks, door/drop wiring, reward overlay, teardown.
- **wrapper `tools/roguelite/prepare.py`** — bundles `runtime_rooms`, `runtime_encounters`, `runtime_rewards`, `runtime_campaign` after their deps and before `main`.
- **wrapper `tools/roguelite/test_v2_runtime.py`** (new) — 10 focused tests.

Not touched: `test_runtime.py`, `test_persistence.py`, `rooms.lua`, recipes, the four runtime helpers, or any other seeded-dirty file.

## Campaign API (`RuntimeCampaign.new(gd, deps, opts)`)

Injected: `Core, Progress, RouteMap, Rooms, RuntimeRooms, RuntimeEncounters, RuntimeRewards, EnemyGenes, EnemyCatalogue, TechAI, GeneCatalogue, routes, Encounters`; callbacks `get_run/set_run/get_route/save_route/finish/say`.

`enter_current`, `tick` (paused state machine: loading→placing→persisting→committing→flushing), `request_travel`, `door_exit`/`request_door`, `frame` (encounter update + downward-only drop), `enemy_defeated`, `stock`, `hit`, `lose_life`, `use_supply`, `reward_preview`/`reward_commit`, `route_map`, `teardown`, `reset(confirmed)`, `status`.

Ordering implemented: `Route.travel`+`Route.collect` staged on copies → destination built/placed → validated atomic `save_route` → **only then** physical `commit`; refusal rolls fighters + staged progress back and keeps the source room/key/visited. Source-cleanup refusal leaves `phase='flushing'` with retained `pending_source`. Rewards: stage → reversible native effect (heal via `gd.set_percent`; charge honestly unavailable) → durable save → rollback effects + run on failure. Defeat/stock stage+persist and retry on failure rather than respawn. One-way gates/opened-return via `Route.travel`; per-socket triggers/arrivals via `RuntimeRooms`.

## main.lua

- New-run dispatch probes `routes.create` on a **staged** profile/run through the production certification gate; refusal leaves profile/run untouched and keeps v1 live. Resume uses the saved resolved route. No fixed eight-room ids/bosses in v2.
- Non-destructive `save(route?,run?)`; `save_route` validates with `Route.validate_save` before writing. `v2_engine_ready`/`v2_isolate` refuse gracefully on an incapable engine.
- Callbacks route explicitly to the campaign; command tree and door precedence preserved (Down at root uses a door, else Special); `reward_ui` overlay; `rogue_map`, `roguelite_v2()` diagnostic.

## Commands run / results

- `python3 test_v2_runtime.py` → **10/10 OK** (entry, per-socket travel, save-refusal rollback, cleanup retry, persistent/consumable gates + opened return, downward-only drop, one-way refusal, reward atomicity + unsupported filtering, mixed fighter/custom waves + partial resume, teardown; plus bundled-main new-run/travel-refusal/resume).
- `test_persistence.py` → all scenarios pass (v2 refusal preserved by the capability gate).
- `test_physical_runtime.py`, `test_encounter_runtime.py`, `test_reward_runtime.py`, `test_route/progress/adapter/checkpoint/legacy/codec/progression/topology/dungeon` → pass; v1 `test_runtime` Lua body passes when its seeded separator defect is patched in a temp copy.

## Limits / notes for root

- **No native build, install, or on-screen play** — all evidence is deterministic engine stubs. Physical v2 play, certification and exact live save/reload remain unverified; recipes are still uncertified.
- Seeded `test_runtime.py` has a pre-existing Lua statement-separator defect (`gd.data_write_atomic=gd.data_write` followed by `(function()` calls the boolean). I did not modify it; a semicolon fixes it.
- `test_rooms.py` (1 error), `test_certify_rooms.py` (2 errors), and the install step of `test_runtime.py`/`test_persistence` fail only on missing art under `menu/out_*` in this isolated lane.
- v2 fighter/champion gene hosts are exposed for provenance but their ability charging is not driven from `Core.on_event`; boss multi-phase authored behavior, full map UI and equipment/mutation rewards remain unsupported and are refused honestly.
