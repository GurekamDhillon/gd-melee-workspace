This one needs a bounded Core seam. Let me read the relevant Core sections before editing.

Now update the concurrent-mark test to use a real Core mutation, and add the new regression groups:

Core diff is surgical. Let me update the contract doc for the Core revision seam:

P1 fixed with a bounded Core seam. Evidence:

## Fix
`rollback_mark`/`same_mark` value comparison was unsound for `nil -> mark -> nil`. Replaced with a bounded **ephemeral per-run, per-target mark revision** seam in `core.lua` (the one authorized shared edit):

- Every mark write in Core now bumps the target's revision: `activate` set, `activate` fire consume, and `tick` expiry.
- `Core.mark_revision(run, target)` reads it; `Core.restore_mark(run, target, before, expected)` restores only if the revision still equals `expected`, the captured mark is not already expired, and the registry is not saturated; the restore itself bumps the revision so an out-of-order second refund is refused.
- `Core.forget_run` + `finish` clear the registry; weak keys and a 64-target cap bound it. It is deliberately **not** serialized and pending transactions never resume, so no save/checkpoint schema changed.

`gene_actions.lua` now reads the revision before/after its own `activate`; if it did not move, it owns no mark transaction and touches no marks. A refund calls `restore_mark` with the post-activate revision, so a mark another host wrote, or an expiry tick, during the callback is never resurrected. `GA.new` fails closed without the seam.

Core diff: +55/−4, only the registry, two read/restore functions, `forget_run`, the three bumps and the `finish` cleanup — no validate/codec/definitions change.

## Regressions (real Core)
Added four groups (now 27 total, all green):
- **exact P1**: player fire consumes an old mark; an ally marks **and** consumes a new one inside the callback; refund leaves no mark.
- callback `Core.tick(181)` past a captured mark's expiry → not restored.
- legitimately refused fire restores the consumed **live** mark exactly once; a stale-revision second restore is refused.
- run identity: a restored run starts revision-free, a stale revision from another instance is refused, `forget_run` cleans.
- The prior concurrent-foreign-mark test now uses a real Core `activate` (manual assignment cannot exercise the seam).

## Results
- `luac5.4 -p` clean; no global leakage; content-deterministic reruns.
- `test_gene_actions` (27 groups), `test_core`, `test_gene_catalogue`, `test_checkpoint`, `test_legacy` all pass.
- Full discovery: 116 tests, the same 4 pre-existing environment errors (missing art/room-kit, absent `roguelite_certification/main.lua`, `import prepare` in `test_persistence`/`test_runtime`), unrelated.

## Frozen
`gene_behaviors.lua` (383), `gene_actions.lua` (617), `core.lua` (340), `test_gene_actions.py` (831), `GENE-ACTION-CONTRACT.md` (390). No commits/native/art. Cinder/rime remain the only admitted genes.

Root still needs the full Core persistence/migration regression after freeze (allowed, but the review says root owns it); the local checkpoint/legacy suites pass. No native/human evidence is claimed.