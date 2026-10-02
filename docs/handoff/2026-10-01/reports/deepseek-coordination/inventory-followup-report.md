Let me re-read the current modules before making the review fixes.

Now let me apply the review fixes to `inventory.lua`.

Now rewrite `equipment.lua` with symmetric occupancy, owned inventory, domain validation, and transactional apply.

Now rewrite the test wrapper for the new API and all follow-up cases.

All 15 pass. Now update the contract doc to match the reviewed API.

Review defects fixed in the isolated lane. No commits, no bundler/main/native edits, other modules untouched.

## What changed (only the original 5 owned files)
1. **Symmetric two-handed occupancy** — `equipment.lua:117` now checks both directions; `Equipment.validate` rejects saved records with either conflict. Repro now fails (`long_reach_band` then `buckler` → `occupancy conflict`), explicit replacement still frees the occupied slot.
2. **Ownership domain** — `equipment.lua:258` `_domain` requires `record.owner == run.id`, active run, known host, checked before resolve/apply/revert; foreign/malformed records return `nil,reason`, while a valid zero-contribution record still returns `0` (`equipment.lua:295,309`). `inventory.lua:66` `domain` is enforced in `plan_use`/`validate_plan`, so no foreign heals/charges/supplies/modifiers.
3. **Owned equipment inventory** — record gains bounded `owned` (`max_owned` 32, `max_owned_per_item` 4), with staged `Equipment.acquire`/`release`; `equip` requires an owned instance and `validate` rejects an equipped-but-unowned item. No free catalogue buff; native held items still refused.
4. **Transactional apply** — `equipment.lua:309` snapshots the host's modifier table, removes stale `eq:<host>:` mods, installs the desired set, and restores exactly on return-false, throw, or Core modifier-capacity failure (all-or-nothing). Non-equipment/other-host contributions untouched; loadout swaps reconcile without drift.
5. **Plan binding** — `inventory.lua:267` attaches a `binding` (owner/scope/item/count/ready_at/frame/context/source-record); `inventory.lua:366` deep-compares the current canonical record, so replayed/tampered/foreign/frame/context-stale plans are refused before spending. Charge uses the actual float `state.charge` (2.5/3 advertises and grants 0.5, no floored free charge).
6. **Legacy supplies** — added bounded `legacy_restore` (heal 30); `from_legacy_supplies` (`inventory.lua:416`) preserves exact count and meaning, never clamps, and does not double-source the supplies economy. Test uses it and confirms heal-30 with no `supply_crate`.
7. **Tests** — 15 named cases (up from 10) covering symmetric 2-hand, owned acquire/release, foreign/invalid refusal, 0-vs-refusal, partial-apply rollback (return-false/throw/actual capacity), stale-mod reconciliation, stale/replayed/tampered/foreign/unequipped plans, fractional charge, legacy-9 no loss/inflation.

## Frozen outputs (sha256)
```
1f4ae5ff… inventory.lua
a18d7548… equipment.lua
9ac418ff… run_history.lua   (unchanged)
a2be05c0… tools/roguelite/test_inventory_economy.py
9d5415f7… docs/INVENTORY-ECONOMY-CONTRACT.md
```

## Results
- `test_inventory_economy.py`: **15/15 pass** (0.4s).
- Full discover: **129 ran, 4 errors, 6 skipped** — same 4 pre-existing environment errors as before (missing generated `menu/out_effects_study`, `menu/out_roguelite/room-kit`, `roguelite_certification`); no inventory/equipment failures.
- Modules re-checked bundle-wrapped (`(function() … end)()`) and syntax-clean.

## API/schema changes (unshipped; integration worker)
- Equipment record adds `owned`; new `Equipment.owns/acquire/release`; `modifiers` returns `nil,reason` for invalid/foreign. `create` initializes `owned={}`.
- `plan_use` requires `ctx.run` (and `ctx.progress` for supply/key); `validate_plan(plan,{inventory,run,frame,context})` is the new signature.
- New consumable `legacy_restore`.

## Unavailable evidence
No native build/install/game run or human playtest (headless Linux, no discs). Native effect application, visuals and menus remain integration work; balance numbers are defaults. Not landed, not shipping until root wires `prepare.py`/`main.lua`.
