# Gene-actions followup 8 report: runtime-state spend ownership

Lane: isolated `gene-actions` worktree, branch `agent/deepseek-gene-actions-20260930`.
Bounded correction only. No main/native/prepare/game/install/commit/other-lane changes.

## Files
- `melee/worktrees/linux/pc/scripts/examples/roguelite/core.lua` (modified)
- `melee/worktrees/linux/pc/scripts/examples/roguelite/gene_actions.lua` (new)
- `melee/worktrees/linux/pc/scripts/examples/roguelite/gene_behaviors.lua` (new)
- `tools/roguelite/test_gene_actions.py` (new)
- `docs/GENE-ACTION-CONTRACT.md` (new)
- this report (coordination artifact, outside the lane)

## Defects
1. `reset_mark_revisions` cleared the slot spend map, so a refused callback that
   only called `ga:on_room_leave()` lost its ordinary refundable spend
   (charge 0 / ready_at 90 instead of charge 3 / ready_at 0).
2. Spend tokens were keyed by `host@slot`. If the same gene instance was
   unequipped and re-equipped to another slot and re-spent, the new activation
   bumped the *new* slot's token, so the old slot's refund matched and clobbered
   the moved state's `ready_at`/charge.

## Fix
Spend ownership is now keyed by the **exact runtime state object**:
- `spend_revisions` is a weak-keyed table (`__mode='k'`) mapping state table ->
  a shared, never-reused monotonic clock value; `Core.activate` bumps the state
  it actually spends from.
- `Core.spend_revision(state)` reads it; `Core.restore_spend(state, expected,
  ready_at, cost, capacity)` refunds that exact state only while its revision
  still matches, then bumps. A newer spend on the same state — from any slot or
  host, including a same-frame equal-value ABA — invalidates the old refund.
- Weak keys bound residency to live runtime states (a run's states plus any
  state still held by an in-flight action); `finish`/`forget_run` clear the run's
  state tokens, and GC cleans the rest. No save schema fields.
- `Core.reset_mark_revisions` now clears only mark tombstones and keeps spend
  ownership, so an ordinary in-flight spend survives a room clear; only mark
  revisions invalidate (sixth-pass guarantee).
- The engine records `spend_rev_before/after` on the state object; a refused
  conditional restore increments `stats.refund_refused`, never `stats.refunded`.

## Regressions (real default Core)
`test_gene_actions`: 2 tests OK, `36 finding groups passed`.
- Group 35: refused apply whose callback only calls `on_room_leave`; asserts
  charge 3, ready_at 0, `stats.refunded == 1`.
- Group 36: inside the refused Cinder callback, unequip assault, equip the
  original gene to traversal, tick 90, re-charge and `Core.activate` traversal;
  asserts the moved state keeps ready_at 180 / charge 0 and
  `stats.refund_refused == 1`.
- Groups 32/33 now also assert `stats.refund_refused == 1` for the newer-spend
  refusals.
Both new groups fail against the prior slot-keyed implementation.

## Regression safety
All 34 prior groups remain green, including mark ABA/expiry/saturation/
source-host/dead-gene/never-refund and new-slot charge safety. `test_core`,
`test_gene_catalogue`, `test_checkpoint`, `test_legacy` pass. Full discovery:
116 tests, same 4 pre-existing environment errors (missing art/room-kit sidecars,
absent `roguelite_certification/main.lua`, `import prepare` in `test_persistence`/
`test_runtime`), unrelated. `luac5.4 -p` clean; no global leakage;
content-deterministic reruns; no trailing whitespace.

## Limitations
- Native collision/startup/occlusion/conversion remain unbound; the fake world
  proves the transaction/ownership contract, not native hits.
- Spend tokens are ephemeral and unpersisted; active transactions do not survive
  a resume. A conservative no-refund after a newer state spend is intentional and
  documented.
- Root still owns the final Core persistence/migration regression; Windows/
  hardware/human acceptance is untouched.
