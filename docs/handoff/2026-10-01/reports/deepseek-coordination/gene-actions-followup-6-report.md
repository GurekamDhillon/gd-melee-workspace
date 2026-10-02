# Gene-actions followup 6 report: reentrant-reset ABA and retired-source restore

Lane: isolated `gene-actions` worktree, branch `agent/deepseek-gene-actions-20260930`.
Bounded correction only. No main/native/save-schema change, no commit/build/install/art.

## Files
- `melee/worktrees/linux/pc/scripts/examples/roguelite/core.lua` (modified)
- `melee/worktrees/linux/pc/scripts/examples/roguelite/gene_actions.lua` (new)
- `melee/worktrees/linux/pc/scripts/examples/roguelite/gene_behaviors.lua` (new)
- `tools/roguelite/test_gene_actions.py` (new)
- `docs/GENE-ACTION-CONTRACT.md` (new)
- this report (coordination artifact, outside the lane)

## Bug 1: reentrant room-clear ABA
Reproduced sequence: player fire consumes a mark (expected revision `R`); inside
the world callback `ga:on_room_leave()` removed the record and `forget_run`
reset the registry to 0; the same callback marked then consumed again, reaching
the same numeric revision `R`; the release's reentrant refund matched the stale
expected `R` and resurrected the player's old mark.

Fix: Core revisions are now a **per-run monotonic clock** (`seq`), never reused
and never rewound. `bump` assigns `seq+1` (not a per-target counter), and
`Core.reset_mark_revisions(r)` drops the target map but keeps the clock, so a
revision captured before a reset can never equal one issued after it.
`forget_run` remains the hard run-end removal and `finish` removes the registry.
The engine's `clear` calls `reset_mark_revisions` (falling back to `forget_run`).
Cap 256, preflight-before-charge and all identity/refund/expiry guarantees are
unchanged.

Memory is still bounded: `reset_mark_revisions` clears the target map at room
leave after pending transactions are cancelled; MAX residency stays under
`MARK_TARGET_CAP = 256`, and the monotonic `seq` is a single number.

## Bug 2: retired-source restore
`Core.restore_mark(r,'enemy',{source='missing_host',expires=180},0)` succeeded,
then `Core.snapshot` rejected the orphan mark. Fix: `restore_mark` now requires
`r.hosts[before.source]`; a source retired inside the callback causes a refusal
with no mutation, so no orphan mark can be created.

## Tests (real Core + real action engine)
`python3 -m unittest tools.roguelite.test_gene_actions -v` -> 2 tests OK,
`31 finding groups passed`. New/updated:
- Group 30: the exact supported reentrant room-leave sequence. `on_room_leave`
  inside the callback, then ally mark + consume; the player's cancelled action
  must not resurrect its mark, and fresh actions remain usable.
- Group 31: direct `restore_mark` with a missing source host returns `nil`, does
  not mutate marks, and the run snapshot stays valid; a second case retires the
  mark's source host inside a real apply callback and asserts no orphan mark and
  a snapshot-valid run.
- Group 27/29 updated to assert **invalidation, not zero**: after
  `reset_mark_revisions` a stale expected revision is refused and a fresh mark
  gets a strictly newer revision (clock never rewound).
- Group 13's foreign-mark fixture now uses a real live source host (an ally),
  since an orphan source is correctly unrestorable.

Reasoning: with the previous counter reset and no source check, group 30
resurrected the old mark and group 31's `Core.snapshot` assertion failed.

## Focused suites
- `test_core.py`: pass (snapshot round-trip unchanged; revisions not serialized).
- `test_gene_catalogue.py`: pass.
- `test_checkpoint.py`, `test_legacy.py`: pass.
- Full discovery: 116 tests, same 4 pre-existing environment errors (missing art/
  room-kit sidecars, absent `roguelite_certification/main.lua`, `import prepare`
  in `test_persistence`/`test_runtime`), unrelated.
- `luac5.4 -p` clean; no global leakage; content-deterministic reruns; no
  trailing whitespace.

## Limitations
- Native collision/startup/occlusion/conversion remain unbound; the fake world
  proves the transaction/ownership contract, not native hits.
- The monotonic clock grows a single number per mutation for the run's lifetime;
  it is not persisted, and active transactions do not survive a resume.
- The engine reset depends on integration calling `on_room_leave`; without it the
  256 cap still bounds memory and refuses cleanly.
- Root owns the full Core persistence/migration regression on the final artifact;
  Windows/hardware/human acceptance is untouched.
