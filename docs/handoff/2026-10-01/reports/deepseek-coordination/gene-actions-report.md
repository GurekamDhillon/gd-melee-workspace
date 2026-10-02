I'll start by orienting myself: reading the coordination prompt, AGENTS.md, status, and the completion plan.

Now I have enough context. Let me set up my task list and start implementing.

Now the action transaction engine:

The engine works with a smoke test. Now the comprehensive Python wrapper:

All 15 scenarios pass. Now the contract document:

I want to align cinder.guard with the current runtime, which releases a targeted counter. Let me refine the defense targeting policy:

Gate 5 gene-action contract implemented and tested. Report:

## Frozen files (new, untracked; nothing staged/committed)

Game checkout `melee/worktrees/linux`:
- `pc/scripts/examples/roguelite/gene_behaviors.lua` (362 lines) — pure behavior specs + validation
- `pc/scripts/examples/roguelite/gene_actions.lua` (419 lines) — pure action transaction engine

Tooling worktree:
- `tools/roguelite/test_gene_actions.py` (441 lines)
- `docs/GENE-ACTION-CONTRACT.md` (256 lines)

No edits to `core.lua`, `gene_catalogue.lua`, `enemy_genes.lua`, `main.lua`, `prepare.py`, catalogues or other modules. Seeded dirty baselines preserved.

## API
- `GeneBehaviors`: 12 genes / 6 families, each ≥2 placements with `action/trigger/category` exact from Core for cinder/rime (`from_core` re-checks and fails on drift), plus startup/active/recovery, range/height/arc/occlusion, spend/refund/reversible, `earning`, `native`. Six authored cross-family reactions; `validate()` rejects any reaction that consumes another reaction's output, duplicate/route-mismatched behaviors and missing family primaries.
- `GeneActions.new(Core, Behaviors, world, opts)`: `preflight → startup → active → recovery → settled`; `begin`, `advance`, `interrupt`, `on_event`, `clear`, `on_room_leave`, `view`, `provenance`. Spend is once at release through real `Core.activate`; refusal restores the pre-spend `Core.snapshot` in place. Enemy parity, missing-seam refusal, bounded record/provenance/lifetime caps, reversible contributions released on interrupt/room-leave. Default admitted set is cinder/rime only.

## Results
- `python3 -m unittest tools.roguelite.test_gene_actions -v` → 2 tests OK, 15 scenarios: costs/refusals, spend point + reversible refund, repeat multihit once, move-id dedup, reaction lineage no-charge, startup/dodge/occlusion, shield+reflect, control status seam, guard-counter strike seam, reversible defense/conversion no drift, movement refund, enemy parity, Thermal Shock consumes mark, per-target earning, caps, missing seam refusal, adversarial data + Core drift.
- `luac5.4 -p` clean; no global leakage; deterministic (content-identical reruns).
- `test_core`, `test_gene_catalogue` still pass. Full discovery: 116 tests, 4 pre-existing environment errors (`menu/out_effects_study` + room-kit sidecars absent, `roguelite_certification/main.lua` absent, `test_runtime` `import prepare`), unrelated to these modules.

## Integration requirements (live worker owns main.lua/prepare.py)
Bundle `gene_behaviors` then `gene_actions` after `core`; build one controller with a `world` adapter binding `get_run/can_start/observe/query/occluded/apply_effect/apply_movement/apply_status/apply_guard/apply_conversion` (+ `release_*`) to the existing `gd.hit`/`gd.enemy_hurt`/`gd.impulse` calls; call `advance()` after `Core.tick(run,1)` and `on_room_leave()` on cleanup. Callback contract and required ordering are in the doc §5/§8.

## Unavailable native/human evidence
The engine runs on Core only. No native dodgeable startup/range/occlusion collision, no real cross-resource conversion, no reflection/projectile resolution, no controller feel or balance — the fake world proves the contract, not native hits. `gd.hit` still emits no `on_hit`. Windows/hardware/human play remain pending; the acceptance ledger `G5-*` row was left untouched for the coordinator.
