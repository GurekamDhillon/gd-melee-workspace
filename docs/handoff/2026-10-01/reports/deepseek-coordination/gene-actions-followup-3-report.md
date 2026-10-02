Supplemental findings confirmed. Fixing release-time eligibility and exact refund policy, then strengthening the regressions.

All 23 groups pass. Update the doc for the two new policy points:

Supplemental findings fixed in the same four frozen files. Evidence:

## Engine changes (`gene_actions.lua` v3)

1. **Release-time free-state re-check** — the spend point now calls `world.can_start(run, host, slot)` again (after identity, before target refresh). If it is false the action is cancelled before any hit; if the seam is missing it fails closed. A `can_start` that flips false after `begin` no longer hits.
2. **Exact refund policy** — on native refusal, `refund = 'on_refuse'` restores the original gene's state/mark; `refund = 'never'` leaves the charge spent and does not roll back the mark. Both paths still release any contribution handle the failed apply created (new `cleanup_contrib`). Refund capacity remains the real `Core.resolve(...).capacity`.
3. Reentrant-cleanup path also honours the authored refund policy.

## Strengthened regressions (now 23 finding groups, all green)

- `can_start` turning false after `begin` → no `apply_effect`, run snapshot unchanged, charge intact.
- `refund='never'` keeps charge at 0 with no refund counted; default `on_refuse` still refunds.
- Unrelated **callback-time** state (a guard modifier **and** a contact charge applied inside the refused callback) survives.
- Per-host refusal + success advanced in one frame: player refunded/interrupted, enemy spent/settled, no cross-contamination (no shared flag reset).
- Equipment replacement is uncharged and exposes no false readiness: after swap-cancel, `Core.ability` is not ready and `begin` refuses `not ready`.
- Contribution cap now exercises pending reservation, settled handle, and release-then-freed capacity.
- Siphon conversion execution against an opponent and release via `release_conversion` (conversion coverage restored).

## Results
- `luac5.4 -p` clean; no global leakage; content-deterministic reruns.
- `python3 -m unittest tools.roguelite.test_gene_actions -v` → 2 tests OK, `23 finding groups passed`; `test_core`/`test_gene_catalogue` pass.
- Full discovery: 116 tests, the same 4 pre-existing environment errors (missing generated art/room-kit sidecars, absent `roguelite_certification/main.lua`, `import prepare`), unrelated.

## Frozen outputs (untracked; no commits/native/art)
`gene_behaviors.lua` (383), `gene_actions.lua` (617), `test_gene_actions.py` (752), `GENE-ACTION-CONTRACT.md` (362). Doc §4–§5 now state the release-time free-state re-check and the `on_refuse`/`never` refund semantics. Cinder/rime remain the only admitted genes; no unproven mechanic is offered.