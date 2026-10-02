Understood — the core P1 is that campaign/orchestrator callbacks close over the module-level `run`/`route`, so an old campaign retires against the new run. Let me bind identity per campaign.

Now add a bundled-main regression for the promotion gate (old cleanup refused).

Fixed the remaining ownership/retirement blockers and stopped editing.

## Root cause fixed
Campaigns and their encounter orchestrators closed over module-level `run`/`route`, so once a new run was promoted, an old owner's teardown operated on the new run (e.g. deleting the deterministic `enemy_r4_1` host inherited by the new run).

## Changes (only my four files)

**`runtime_campaign.lua` (identity binding)**
- Constructor now takes `opts.route`/`opts.run` and stores `self.route`/`self.run`; every read, mutation, and the orchestrator's `get_run` closure bind to `self.run` for the instance lifetime. No module-global callbacks remain.
- `_save(progress)` persists `self.route`/`self.run`; `save_route(route,progress,run)` never replaces the route table, so identity survives writes.
- `_mirror` updates the instance's own run; `teardown({drop_pending=...})` discards a superseded owner's unpersisted advance instead of writing it into a later checkpoint.

**`main.lua`**
- `ensure_campaign(route,run)` always builds a fresh instance bound to the exact route/run; no caching.
- Explicit promotion gate: after a durable new-run save, if a previous owner exists, `retiring` holds it and the engine stays paused; `teardown({drop_pending=true})` is retried (bounded 16) each tick. New geometry/`enter_current`/unpause happen only after the old resources are actually released. On exhaustion the old owner is retained in `orphans` (never forgotten), the un-entered new campaign is dropped, and an error is shown — no overlapping-room run.
- `save_route` refuses to mutate the previous pair on failure; new-run restore of `profile/run/route/campaign/fighter` unchanged; ordinary transition rollback unchanged.
- `on_unload` still never fabricates `reset(true)`; orphans retired with `drop_pending`.
- v2 `collection` command may save+leave from any room (v1 keeps rest-only); `roguelite_state` exposes `retiring`/`orphans`.

## Tests (all with copy-snapshot `gd.player`)
- `python3 test_v2_runtime.py` → **22/22 OK**. New: `test_old_owner_teardown_is_bound_to_its_own_run` (real Core: old `enemy_r4_1` removed from run A, new run B host/gene byte-identical, no flush of old pending), `test_main_promotion_waits_for_refused_old_cleanup` (refused cleanup → paused, no active/unpause/new colliders, then recovery), `test_main_promotion_exhaustion_retains_old_owner` (bounded failure retains owner, builds nothing).
- `test_persistence.py`, all pure helpers, and v1 `test_runtime` (seeded semicolon patched only in a temp copy) remain green.

## Remaining limits / native gap
- The native owner-cleanup seam is still absent: `gs_unload` only drops the script env/commands/tasks, so a refused teardown at unload cannot be retried and colliders can survive. `on_unload` releases what it can and logs the need for a native seam (root/Sol implementing). `on_match_end` remains the only confirmed scene-teardown path.
- No native build/play; evidence is deterministic stubs. Charge effects still honestly unavailable; fighter/champion host-gene charging and the full 12-gate goal remain open.