Read the review. The defect: menu ops replace the global `run` table, but the campaign (and its orchestrator) keep the old table, so saves persist a stale run. Let me add explicit current-campaign rebinding.

Fixed the current-campaign run rebinding P1, tested with the real menu paths, and stopped.

## Root cause
Menu/Core transactions (`Menus.apply` place/unequip/fuse/reward, and refusal `Core.restore`) install a **new run table** into the global `run`, while the live campaign (and its encounter orchestrator) still held the old table. Subsequent campaign saves (`lose_life`, transitions, reward) persisted the stale run, so a durably saved loadout could disappear.

## Changes (only my four files)

**`runtime_campaign.lua`**
- `_save(progress, run_override)` again accepts an override and commits it into the instance only on a durable write; reward commit now persists `result.run` and the instance follows it (removed the duplicate in-memory-only assignment).
- New explicit `replace_run(new_run)`: rebinds the **current** campaign/orchestrator to an exact run table and mirrors the route progress. Retired owners are never touched.

**`main.lua`**
- Central `rebind_current_run(r)` sets the global `run` and calls `campaign:replace_run(r)` only on the live campaign.
- Applied at every table-replacing site while a campaign exists: `choose_menu` menu-action `result.run`, the failed-save restore path, `finish` save-failure restore, and the two `apply_gene` refusal restores (`gd.impulse` failure, activation refused). Audited the remaining `run=` sites (load, new-run staging, v1 fallback) — none can occur with a live campaign.
- No change to collection context (remains rest-only) and no gameplay bypass.

## Tests
- `python3 test_v2_runtime.py` → **27/27 OK**. New `test_main_rest_menu_run_rebind_persists_and_restores` (real bundled main + real Menus/Core): travels legitimately to the rest room, opens the real rest menu via the command tree, places `r3` into traversal, asserts the campaign is rebound to the menu-produced run, continues, forces `lose_life`, and decodes the durable checkpoint to prove the loadout persisted; then a `fail_atomic` placement is rolled back exactly and the campaign rebound, with the committed loadout intact.
- Existing campaign reward test now asserts `campaign.run` identity with the committed run.
- Legacy green: `test_persistence.py`, all pure helper suites, and v1 `test_runtime` (seeded semicolon patched only in a temp copy; repo file untouched). `git diff --check` clean.

## Remaining limits / native gap
- No native build/play; evidence is deterministic stubs with native-correct copy `gd.player`.
- The native owner-cleanup seam is still missing (`gs_unload` only drops the script env); `on_unload` attempts teardown, retains refused effect/save ownership, and never fabricates `reset(true)` — the honest external prerequisite remains Root/Sol's.
- Charge effects remain honestly unavailable; host-gene charging and the full 12-gate goal stay open.