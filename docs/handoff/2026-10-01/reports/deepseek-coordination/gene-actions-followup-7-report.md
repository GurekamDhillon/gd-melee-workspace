# Gene-actions followup 7 report: cooldown refund owns its spend

Lane: isolated `gene-actions` worktree, branch `agent/deepseek-gene-actions-20260930`.
Bounded correction only. No main/native/save-schema change, no commit/build/install/art.

## Files
- `melee/worktrees/linux/pc/scripts/examples/roguelite/core.lua` (modified)
- `melee/worktrees/linux/pc/scripts/examples/roguelite/gene_actions.lua` (new)
- `melee/worktrees/linux/pc/scripts/examples/roguelite/gene_behaviors.lua` (new)
- `tools/roguelite/test_gene_actions.py` (new)
- `docs/GENE-ACTION-CONTRACT.md` (new)
- this report (coordination artifact, outside the lane)

## Defect
`refund` unconditionally set `state.ready_at = pre.ready_at` (and credited the
charge). If the same slot was spent again during the refused apply callback, the
refund clobbered the newer activation's cooldown/charge. Equal-value ABA (two
spends in one frame producing the same `ready_at`) could not be distinguished by
comparing timestamps.

## Fix
Ephemeral per-run, per-slot **spend revision** in Core:
- `Core.activate` bumps the slot's spend revision whenever it spends.
- `Core.spend_revision(run, host, slot)` reads it; `Core.restore_spend(run, host,
  slot, state, expected, ready_at, cost, capacity)` refunds the exact original
  state table (`rec.state`, so a slot swap cannot receive it) only while the
  revision still matches `expected`, then bumps so a stale second refund fails.
- Revisions share the per-run monotonic clock with mark revisions, so a reset can
  never make a stale expected valid. `reset_mark_revisions` now clears the mark
  **and** spend maps but keeps the clock. Charge is credited up to the capacity
  captured from `Core.resolve`; `refund='never'` performs no spend restore.
- Targeted refunds are unchanged: no whole-run snapshot.

## Real-Core regressions (default Cinder)
`test_gene_actions`: 2 tests OK, `34 finding groups passed`.
- Group 32 (exact repro): first Cinder is refused after `on_room_leave` +
  `Core.tick(90)` + a second successful `Core.activate`; asserts the newer
  `ready_at == 180` and `charge == 0` survive the refund.
- Group 33: same-frame equal `ready_at` (re-armed fixture) is rejected by the
  spend revision; the newer 90-frame cooldown survives.
- Group 34: a no-spend callback that only earns charge still restores the
  original cooldown and keeps charge at capacity.

Reasoning: with the previous unconditional restore, groups 32 and 33 fail
(`ready_at` becomes 0).

## Focused suites
- `test_core.py`, `test_gene_catalogue.py`, `test_checkpoint.py`,
  `test_legacy.py`: pass.
- All prior 31 groups, including reentrant/run/gene/state/mark/refund-never/expiry,
  remain green.
- Full discovery: 116 tests, same 4 pre-existing environment errors (missing art/
  room-kit sidecars, absent `roguelite_certification/main.lua`, `import prepare`
  in `test_persistence`/`test_runtime`), unrelated.
- `luac5.4 -p` clean; no global leakage; content-deterministic reruns; no
  trailing whitespace.

## Limitations
- Native collision/startup/occlusion/conversion remain unbound; the fake world
  proves the transaction/ownership contract, not native hits.
- Spend and mark revisions are ephemeral, single per-run numbers, not persisted;
  active transactions do not survive a resume.
- The same-frame double-spend case cannot occur naturally under the current
  cooldown, so group 33 uses an explicit re-arm fixture; the revision is what
  makes it safe if it ever does.
- Root owns the final Core persistence/migration regression; Windows/hardware/
  human acceptance is untouched.
