I read the addendum and the native `gs_unload`. Let me inspect the exact main sections to fix.

Confirmed: `gs_unload` only drops script env/commands/tasks — no stage teardown. Let me make `tick` yield one phase per call, then fix main's unload/new-run staging.

Now rewrite the new-run branch to preserve references and restore on refusal.

All 19 pass. Verify legacy suites unaffected.

Addressed the corrective review. Stopping edits for merge.

## Owned files changed
- game `pc/scripts/examples/roguelite/runtime_campaign.lua` (799 lines)
- game `pc/scripts/examples/roguelite/main.lua` (+393/−39)
- wrapper `tools/roguelite/test_v2_runtime.py` (19 tests)
- `tools/roguelite/prepare.py` unchanged this pass

## Fixes

1. **No fabricated scene teardown on unload.** Confirmed in native `gs_unload` (`pc/platform/gw_script.c:5483`): it runs `on_unload`, restores camera/pads/tasks/commands and unrefs the env — it does **not** remove stage colliders/models. `on_unload` now releases what the engine accepts via `campaign:teardown()` and only `reset(false)` when clean; a refused release is logged as *requiring a native owner-cleanup seam* rather than calling `reset(true)`. `reset(true)` is now used only in `on_match_end` (confirmed scene begin/teardown). Docs corrected accordingly.

2. **New-run restores exact previous references on refusal.** New-run now snapshots `profile/run/route/campaign/run_fighter` first, stages the certified route on a `Core.restore` copy, and promotes only after `v2_isolate() and save()` succeed. On any refusal it restores every reference (so `profile.next_run`, `world_seed`, run id and fighter are byte-equivalent) and never retires the previous owner. The prior owner is released only after a durable save (or aborted if its cleanup refuses, via an orphan list retried at cleanup/`on_match_end`).

3. **Active pending-save retry under main.** `blocked()` covers `pending_save`/`effect_pending`; main pauses and calls `campaign:tick()` every frame while blocked, so a failed progress save retries once storage recovers. Regression drives `lose_life` failure through the bundled main, restores the writer, and asserts pending clears and a durable write occurs.

4. **One bounded phase per tick.** `RuntimeCampaign:tick()` now performs exactly one phase (requested/loading/placing/persisting/committing/settling) and returns; loading still yields one asset per call. No single hook serializes floor build + save + destructive commit + enemy spawn. Pause is established before any geometry mutation; no unpause occurs while cleanup/effects are refused.

5. **§7 mirrors left as-is** per the addendum (not substantiated); no speculative clone architecture added.

## Tests (all with native-correct copy `gd.player` snapshots)
- `python3 test_v2_runtime.py` → **19/19 OK**. New this pass: `test_main_failed_new_run_restores_profile_and_retries`, `test_main_retries_active_pending_save`; existing 17 still green (now with one-phase ticks).
- `test_persistence.py` green; `test_physical/encounter/reward_runtime`, `test_route/progress/adapter/checkpoint/legacy/codec/progression/topology/dungeon/commands/core/menus/roster/route_map/ai/economy/integration_edges` green.
- v1 `test_runtime` Lua body green with the seeded semicolon patched in a temp copy (file untouched); only the missing-art install step fails in this lane.

## Required native change (root to implement)
A script-owner cleanup seam so script-created stage entities are released when a mod/script is unloaded: either a native call that removes all stage lines/platforms/models spawned by a script, or a confirmed scene-teardown signal distinct from `on_unload`. Until then a refused v2 teardown at unload leaves colliders because the Lua env is gone.

## Remaining limits
No native build/play; evidence is deterministic stubs. Charge effects remain honestly unavailable (no engine API). Native actor host-gene charging and full 12-gate gameplay stay open; no certification flips. Asset-dependent suites still fail only on missing `menu/out_*` art in this isolated lane.