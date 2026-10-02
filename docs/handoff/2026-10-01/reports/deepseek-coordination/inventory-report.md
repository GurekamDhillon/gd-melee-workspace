I'll start by orienting myself in the worktree and reading the required context.

This is a substantial pure-services implementation. Let me set up a task list and check the remaining context I need.

Now the test wrapper with all required cases:

Now the contract document:

Gate 7 independent work complete. No commits/staging/native build; seeded dirty baselines preserved.

## Frozen files (new, checksummed)
```
89e504af...  melee/worktrees/linux/pc/scripts/examples/roguelite/inventory.lua   (518 L)
1f1a125f...  melee/worktrees/linux/pc/scripts/examples/roguelite/equipment.lua   (255 L)
9ac418ff...  melee/worktrees/linux/pc/scripts/examples/roguelite/run_history.lua (206 L)
38b84bf3...  tools/roguelite/test_inventory_economy.py                           (413 L)
66448775...  docs/INVENTORY-ECONOMY-CONTRACT.md                                  (239 L)
```
Untouched: `core/main/progress/checkpoint/*catalogue`, `prepare.py`. No existing file modified (repo dirty baseline and `melee/worktrees/linux` HEAD `e833e01d9` unchanged). Root owns native/merging/art; this ships no bundle entry.

## API
- `Inventory.new/def/classify/create/validate/count/cooldown/available/acquire`, `svc:plan_use/validate_plan/encode/decode`, `from_legacy_supplies`; `Inventory.Economy.{new,validate,earn,spend,reward_value,breed_cost}`; `Inventory.Collection.{breed_preview,commit_breed,export_preview,fusion_preview,discard_preview,commit_discard,parent_references}`.
- `Equipment.new(Core){slots,definitions,create,validate,equip,unequip}`, `svc:modifiers/apply/revert/encode/decode`.
- `RunHistory.new/make_entry/append/validate/summary/encode/decode/from_core_finished`.
- Records are all `version=1`, reject unknown fields, inject `Codec`/`Core`/`Progress` explicitly.

## Coverage vs assignment
12 consumables (9 supported: heal/charge/supply/modifier/key; 3 honest refusals), 13 equipment (11 supported) across 8 stable slots. Transaction order preview→stage→validate→reversible effects→persist→commit; unavailable effects refused before spend. Equipment resolves once into deterministic `eq:` Core modifiers and reverts with zero numerical drift; native held items refused with a spy-Core API-surface proof. Collection adapters clone real Core for breed/export/fusion, enforce enemy-host filter, full-collection discard + confirmation, no free reroll. Run history is configurable/bounded, arrays capped at 16 with truncation flags, Codec-encoded, with a read-only Core-`finished` migration boundary. Legacy supplies migrate without mutating a saved route. Route restores persisted reward specs with no reroll.

## Results
`test_inventory_economy.py`: **10/10 pass** (0.38s). Full suite (`python3 -m unittest discover -s tools/roguelite`): **124 ran, 114 pass, 4 errors, 6 skipped**; the 4 errors are pre-existing environment gaps (missing generated `menu/out_effects_study`, `menu/out_roguelite/room-kit`, `roguelite_certification` dirs), not touched by these files.

## Integration requirements (integration worker owns)
1. Add `('inventory','Inventory'),('equipment','Equipment'),('run_history','RunHistory')` to `prepare.py` before `main.lua`.
2. In `main.lua`, build services with bundled `Codec/Core/Progress`; apply intents (native heal/charge; Core modifier; Progress key/supply) then persist in TBD3 and commit; discard staged record on any failure. Bundle-wrapping compiles (verified).
3. Persist the three records alongside existing sections; never regenerate from catalogue.

## Unavailable evidence
No native build/install/run or human playtest (headless Linux, no disc images). Native effect application, visuals and menus are unbuilt; balance numbers are defaults. Nothing claimed live.
