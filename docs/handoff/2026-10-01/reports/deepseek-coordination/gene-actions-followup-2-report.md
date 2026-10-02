Residual P1s confirmed. I'll rework the engine for exact instance identity, targeted refunds by owned state, mark tokens, reservation-based capacity, the release-kind map, and reentrant cleanup.

Now the identity validation by exact reference:

Now the regression tests. First extend the fake world with reentrancy hooks and a mutable run holder:

All 18 groups pass. Let me run the full verification suite:

Now update the contract doc for the v3 fixes:

Residual P1s fixed in the same four frozen files only. Report:

## Root causes and fixes (`gene_actions.lua` v3)

1. **Callback-time slot swap refunded the replacement** — refund now credits `rec.state` (the *original* gene's state table captured at begin) and restores its `ready_at`; it no longer looks up `host.state[slot]` at refund time, so a swapped-in gene gains nothing and the original is made whole.
2. **Refund erased a concurrent other-host mark** — captures `mark_before`/`mark_after` around `Core.activate` and rolls back **only if the current mark still equals the value this action produced** (`same_mark` token compare); a foreign mark written during the callback is left intact.
3. **Two profiles with `run1` spent the wrong gene** — identity is now exact object identity (run table, gene instance table, slot state table, instance id, Core action), validated every phase; a run-instance swap cancels instead of spending/running against the other run.
4. **Capacity read `Core.ability.capacity` (nonexistent)** — capacity now comes from `Core.resolve(...).capacity`.
5. **Contribution cap let simultaneous handles through** — `contribution_load()` counts settled handles **plus pending contribution-kind reservations**; checked before spend.
6. **`convert` preflight looked for `release_convert`** — added `release_kind = {guard='guard', convert='conversion', siphon='conversion'}`; missing/false/throw releases are refused, retained and retried (bounded, reported stuck), never leaked.
7. **Reentrant room cleanup orphaned a guard modifier** — after the native callback returns, if the record was removed reentrantly the engine cancels the intent, refunds the owned cost, and releases the handle the callback created.
8. **`replace_run` / whole-run snapshots** remained unused; `advance` reacquires the authoritative run per record.

Cinder/rime remain the only admitted genes; `from_core()` still guards their exact Core actions.

## New regressions (real Core + adversarial fake world)
The suite now has 18 finding groups, adding: slot swap inside the callback (original refunded, replacement at 0); concurrent foreign-mark preserved and consumed foreign mark restored; two-profile `run1` cross-instance cancellation; pending-reservation contribution capacity; cleanup reentered inside `apply` leaving no modifier/handle; and `release_conversion` used with a missing-seam refusal. Each new case fails against the prior engine.

## Evidence
- `luac5.4 -p` clean; no global leakage; content-deterministic reruns.
- `python3 -m unittest tools.roguelite.test_gene_actions -v` → 2 tests OK, `18 finding groups passed`; `test_core`/`test_gene_catalogue` still pass.
- Full discovery: 116 tests, the same 4 pre-existing environment errors (missing generated art/room-kit sidecars, absent `roguelite_certification/main.lua`, `import prepare`), unrelated to these modules.

## Frozen outputs (untracked; no commits/staging/native/art)
`gene_behaviors.lua` (383), `gene_actions.lua` (600), `test_gene_actions.py` (636), `GENE-ACTION-CONTRACT.md` (345). Doc §4–§5 now specify exact instance identity, mark-token rollback, `Core.resolve` capacity, reservation counting, the release-kind map and reentrant cleanup. No newly unproven mechanic is offered; native/human evidence remains pending.