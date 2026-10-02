Let me fix the forgeable `validate_plan` and non-transactional `revert`.

Let me reproduce the exact root probe to confirm the forgery is now refused.

Second review blockers fixed and frozen. Stopped editing; no commits/build/install/native/game/art, only the five owned files touched.

## Blocker 1 — forgeable `validate_plan` (confirmed root repro)
**Cause:** validation trusted the plan's mutable copies (`effects`, `inventory`, `cost`, `binding`), so `plan.effects[1].amount=999` and `plan.inventory=clone(source)` validated.
**Fix (`inventory.lua:366`):** `validate_plan` no longer trusts the plan. It requires the authoritative `ctx` (`inventory`, `item`, `frame`, `context`, `run`, `progress`, `target`, `effects`), re-derives the canonical plan through the same side-effect-free resolver, and demands the caller's plan match it **exactly** (item, cost, effects, staged inventory, binding, message). Direct repro:
```
legit            -> true
forged amount999 -> nil  plan does not match the canonical action
no-spend inventory-> nil  plan does not match the canonical action
```
Charge uses the real float state: `2.5/3` grants `0.5`; same-frame `3/3` → `already full`; `2.9/3` → canonical mismatch; a capacity modifier or unequipped target also invalidates. Heal-contract bound changes revalidate.

## Blocker 2 — non-transactional `revert`
**Cause:** `revert` ignored `remove_modifier` return values/throws and could partial-clear; `apply` only caught `nil`, not `false`.
**Fix (`equipment.lua`):** `apply` and `revert` both use all-or-nothing reconciliation. A callback returning `false`/`nil` or throwing is an explicit refusal even after a side effect; the host's modifier table is snapshotted and restored exactly. `revert` returns `nil,reason` on failure and the removed count (`0` is a real success) otherwise. Only the record host's `eq:<host>:` modifiers are touched and only that host's modifier table is replaced — unrelated contributions and other hosts survive.

## Tests (16/16 pass)
Added `test_equipment_apply_revert_return_false_rollback` and rewrote the plan test: forged amount, unstaged inventory, swapped item/cost, altered binding, ctx item mismatch, frame/context, changed heal bound, replay, foreign record, unequipped target, fractional/`3.0`/`2.9`/capacity change; plus apply/revert `false`-after-mutation and throw-after-partial with unrelated-host preservation.

## Results / freeze
- `test_inventory_economy.py`: **16/16** (0.34s).
- Full discover: **130 ran, 4 errors, 6 skipped** — same 4 pre-existing environment errors (missing `menu/out_effects_study`, `menu/out_roguelite/room-kit`, `roguelite_certification`); no inventory/equipment failures. Modules re-checked bundle-wrapped.
- Checksums: `inventory.lua 586ec034…`, `equipment.lua c9a9257e…`, `run_history.lua 9ac418ff…` (unchanged), `test_inventory_economy.py b8562730…`, `INVENTORY-ECONOMY-CONTRACT.md 41407188…`.
- Seeded dirty baseline and other workers' files untouched.

## Integration notes
`validate_plan` now requires `ctx.item` (and the original `target`/`effects` contract); `equipment` `apply`/`revert` treat any non-truthy Core return as refusal. Native effect application, visuals, menus and the `prepare.py`/`main.lua` wiring remain pending on root.