I'll work through each review defect. Let me first re-read the current helper code and tests to plan precise edits.

Now I'll rewrite the campaign module with deferred pause-safe transactions, retained ownership, coherent pending saves, encounter continuity, correct destination placement, and effect verification.

Now update main.lua: pause ownership, gating, stock protocol, and pending-progress mirroring.

Now update the test harness to return copy snapshots and cover each defect. Let me rewrite `test_v2_runtime.py`.

The stale-pending fix requires every successful save to clear the pending record. Let me centralize that.

Found it: Lua's `find('one-way')` treats `-` as a pattern quantifier. Fixing that and the tick-pacing in three tests.

All 17 pass. Now verify legacy suites still pass after the main.lua changes.

All green. Let me capture the final diff stat for the report.

Fixed all review P1s with regression coverage. Stopping edits so root can merge.

## Owned files changed
- game `pc/scripts/examples/roguelite/runtime_campaign.lua` (rewritten, v2)
- game `pc/scripts/examples/roguelite/main.lua` (+344/−38)
- wrapper `tools/roguelite/test_v2_runtime.py` (17 tests; `gd.player` now returns copy snapshots)
- wrapper `tools/roguelite/prepare.py` (unchanged this pass; bundle order already correct)

`test_runtime.py`, `test_persistence.py`, recipes, and the four runtime helpers were not touched.

## Fixes by review item
1. **Transitions paused.** `request_travel`/`enter_current` now only stage (`phase='requested'`); main calls `v2_set_paused(true)` before `campaign:tick()` runs `RuntimeRooms:begin/build/place/persist/commit/settle`. Pause persists through flushing/recovery/error/effect-rollback. `on_frame` is gated on `campaign:running()` (Core/fighters/stocks/move earning frozen). `v2_set_paused(false)` → `unpause()` restores the normal command tree.
2. **Ownership retained.** Any post-begin failure sets `phase='recovering'`; `self.tx` is kept until `RuntimeRooms:rollback` actually succeeds (fighters restored, destination destroyed) before the source resumes. Bounded by `max_rollback_attempts`; terminal failure keeps `tx` and surfaces `phase='error'`. `_place` uses the **destination** node (`self.dest_node`), so r2→r4 places p2 at the enemy spawn, not x58. `reset(true)` only on `on_match_end`/`on_unload`.
3. **No stale pending saves.** All durable writes funnel through `_save`, which clears `pending_save` on success; `_flush_pending_save` retries the newest record, and `_persist_progress` installs the newest in-memory progress via `opts.set_progress` (which mirrors the run). A later successful heal/travel/reward can never be overwritten by an older generation; max retries surface `error`, keeping ownership.
4. **Encounter lifecycle.** `request_travel` no longer drops `encounter_active` or clears actors. `_settle` (after durable commit) always clears the orchestrator before starting the next encounter; a refused clear stays owned and blocks. Combat exits require `objectives[room]=='done'` in both `request_travel` and `door_exit`. `begin` failure clears and enters `error` fail-closed. `_stage_events` guards non-table events/nil reasons.
5. **Stock protocol.** `_configure_encounter_engine` writes the **native 99 baseline**, never logical `remaining`. main passes `campaign:stock(2,1,0)` only on an observed decrease, so one KO decrements exactly one and a champion is not cleared early; new waves reset to baseline. Regression asserts engine p2 stays 99 on entry, 1 KO → remaining 2→1 and not cleared, 2 KOs → cleared.
6. **Effect failures.** `_apply_effects` uses `pcall`, treats `false`/throw as refusal, and readback-verifies `percent`. Partial multi-effect failure rolls back applied effects; a refused rollback is retained in `effect_pending` (`phase='effects'`) until `retry_effects` succeeds (bounded). A failed save rolls effects back and does **not** re-snapshot the live run (avoids orphaning hosts); no free heal/claim/spend.
7. **Success mirrors.** Reward commit uses `_save(progress, result.run)`; main commits the mirrored `run_override` pair, then `set_run(result.run)` is the same object. No snapshot restore remains.

## API changes
- `RuntimeCampaign` v2 adds `blocked()`, `running()`, `failed()`, `take_notice()`, `attempt_recovery()`, `retry_effects()`, `_save()`. Phases now include `requested`, `settling`, `recovering`, `effects`, `error`. `enter_current`/`request_travel` stage only; `tick` executes. `status()` v2 adds `blocked`, `failed`, `notice`, `pending_save`, `effect_pending`.
- New opts: `set_progress`, `stock_baseline`, `max_rollback_attempts`, `max_save_attempts`, `max_effect_attempts`.
- main: `v2_set_paused`/`v2_isolate`, gated `on_frame`, one-KO stock calls, `ensure_campaign` passes `set_progress`+`stock_baseline`.

## Commands / results
- `python3 test_v2_runtime.py` → **17/17 OK** (15 campaign + 2 bundled-main).
- `test_persistence.py` green; `test_physical/encounter/reward_runtime`, `test_route/progress/adapter/checkpoint/legacy/codec/progression/topology/dungeon/commands/core/menus/roster/route_map/ai/economy/integration_edges` green.
- v1 `test_runtime` Lua body green with the seeded separator semicolon patched in a temp copy (root reports that fix is landing; file untouched).

## Remaining limits
- Still no native build/install/on-screen play; all evidence is deterministic stubs. Physical v2 play and native certification remain root's parallel driver.
- `gd.set_percent` is the only documented native effect; **charge is honestly unavailable** (no engine API), and no undocumented Core poking is done. Fighter/champion host-gene charging compatibility remains pending. No claim of complete genes/AI.
- Asset-dependent suites (`test_rooms`, `test_certify_rooms`, the install step) still fail only on missing `menu/out_*` art in this isolated lane.
