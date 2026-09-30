# Inventory / equipment / run-history economy contract (Gate 7)

Status: pure-service implementation, tested at the module level. Not yet wired
into `main.lua` and not yet in a shipping bundle. This document is the interface
contract for the live-integration worker and the reviewer.

## 1. Scope and ownership

This work owns exactly five new files:

| File | Kind |
| --- | --- |
| `melee/worktrees/linux/pc/scripts/examples/roguelite/inventory.lua` | pure game module |
| `melee/worktrees/linux/pc/scripts/examples/roguelite/equipment.lua` | pure game module (Core modifier wrap) |
| `melee/worktrees/linux/pc/scripts/examples/roguelite/run_history.lua` | pure game module |
| `tools/roguelite/test_inventory_economy.py` | wrapper test |
| `docs/INVENTORY-ECONOMY-CONTRACT.md` | this document |

No existing file was modified. In particular `core.lua`, `main.lua`,
`progress.lua`, `checkpoint.lua`, the catalogues and `prepare.py` are untouched
by this work. Bundling and live wiring belong to the integration worker.

The three modules are independent, versioned records with explicit injected
dependencies. They never rely on bundle order or globals and never call
`load`/`loadstring`/`dofile` on save text.

## 2. Transaction contract (all three services)

```
preview -> independent stage -> validate -> reversible native effects
        -> atomic persist (caller) -> commit (caller swaps in the staged record)
```

* Mutating operations return a staged copy; the source is never mutated.
* The caller applies the returned effect intents, persists atomically, and only
  then commits the staged record. Failure means "do not commit"; rollback is
  simply discarding the staged value.
* An effect whose mechanic does not exist is refused **before** any count,
  cooldown or currency is spent.
* Ownership domain is enforced: a run-scoped record may only act on the run it
  belongs to (matching `owner`/`run.id`, active); a profile-scoped record only on
  its profile. Foreign records are refused, not silently applied.
* `Inventory:validate_plan(plan, ctx)` never trusts the plan's own mutable
  fields. It reconstructs the canonical action by re-running the resolver from
  the authoritative `ctx` (`inventory`, `item`, `frame`, `context`, `run`,
  `progress`, `target`, `effects`) and requires the caller's plan to match it
  exactly (item, cost, effects, staged inventory, binding, message). A forged
  effect amount, an unstaged inventory, a swapped item/cost, an altered binding,
  a changed charge state/capacity/target or a changed effect contract therefore
  re-derive a different canonical plan and are refused before any spend. Plans
  are previews, not free-use tokens.
* `Equipment:apply` and `Equipment:revert` are transactional reconciliations of
  the owned equipment modifiers; a Core callback that returns false/nil or throws
  is an explicit refusal even after a side effect, and the host's modifier table
  is restored exactly (all-or-nothing). Only this host's modifier table is
  replaced on rollback; other hosts and non-equipment contributions are never
  touched.

## 3. `inventory.lua` — consumables

`Inventory.new({Codec=Codec, Core=Core, Progress=Progress})` builds the service.
Codec is required for serialization; Core/Progress are required only for the
effects that resolve against them.

A record is `{version=1, owner=<id>, scope='run'|'profile', capacity=N,
items={id=count}, ready_at={id=frame}}`. `capacity` bounds distinct stacks; each
stack is bounded by its definition's `stack_max`.

### Consumable definitions

| id | effect | target | cooldown | stack | contexts | implemented |
| --- | --- | --- | --- | --- | --- | --- |
| `repair_kit` | heal 30 | player | 600 | 3 | combat, rest | yes |
| `field_bandage` | heal 15 | player | 240 | 5 | combat, rest, field | yes |
| `charge_flask` | charge 3 | equipped gene | 300 | 3 | combat, rest | yes |
| `charge_cell` | charge 1 | equipped gene | 180 | 4 | combat, rest | yes |
| `supply_crate` | supply 1 | progress | 0 | 9 | reward, rest | yes |
| `supply_pack` | supply 2 | progress | 0 | 4 | reward | yes |
| `ember_phial` | modifier potency +2 / 900f | equipped gene | 900 | 2 | combat, rest | yes |
| `rime_salve` | modifier capacity +1 / 600f | equipped gene | 900 | 2 | combat, rest | yes |
| `warp_shard` | persistent key `vault_charge` | progress | 0 | 1 | field | yes |
| `legacy_restore` | heal 30 (legacy Restore) | player | 0 | 9 | combat, rest, field | yes |
| `frost_tonic` | cleanse | — | 0 | 2 | rest | **no** |
| `smoke_bomb` | flee | — | 600 | 2 | combat | **no** |
| `bomb_core` | blast 20 | — | 600 | 2 | combat | **no** |

The three unimplemented entries are honest refusals: no status/cleanse system,
no disengage system and no bounded blast system exist in Core/Progress, so
`classify`/`available`/`plan_use` refuse them ("effect <kind> is not
implemented"). They are never surfaced as working items.

### Effect intents

`Inventory:plan_use(inv, id, ctx)` returns
`{inventory=<staged>, effects=<intents>, cost, message, cooldown_until}` where
each intent is `{kind, ..., contract_version=1}`:

* `heal` → `{kind='heal', target='player', amount}`; requires
  `ctx.effects={version=1, heal=true, max_heal=?}`.
* `charge` → `{kind='charge', host, slot, gene, amount, before, target, capacity}`;
  requires `ctx.effects={version=1, charge=true}`; target must be a
  player-equipped Core gene; charged only up to `capacity - current`.
* `supply` → `{kind='supply', amount}` applied to `Progress.supplies`.
* `modifier` → `{kind='modifier', host, slot, gene, stat, add, duration}` applied
  through `Core.apply_modifier` with `expires`.
* `key` → `{kind='key', key}` applied through `Progress.unlock`.

### Plan validation and fractional charge

`plan_use` returns a `binding` (owner, scope, item, count, ready_at, frame,
context and a copy of the source record) for callers, but `validate_plan` treats
it as untrusted metadata. It re-derives the canonical plan from the authoritative
context and compares the entire result, so the confirmed forge
(`plan.effects[1].amount=999`, `plan.inventory=clone(source)`) is refused
(`plan does not match the canonical action`). Charge uses the **actual resolved
float** `state.charge`, so a fractional state (2.5 of 3) advertises and grants
0.5, never a floored free charge; a same-frame change to 3 or 2.9 re-derives a
different or refused canonical plan.

### Legacy supplies migration

`Inventory.from_legacy_supplies(value, {owner, scope, capacity})` maps the legacy
integer `progress.supplies` (0–9) to the bounded `legacy_restore` definition
(heal 30) — the old "Restore" resource — **not** to a `supply_crate` food grant,
so the count and meaning are preserved and the supplies economy is not
double-sourced. The count is never clamped; an out-of-range value is refused. It
reads only and never writes back to a saved route/progress. `test_inventory_economy.py`
asserts the encoded progress is byte-identical before and after migration and
that using one Restore heals 30 without granting supplies.

## 4. `equipment.lua` — reversible equipment

`Equipment.new(Core, {Codec=Codec})` wraps the real Core modifier API
(`apply_modifier`/`remove_modifier`/`resolve`/`definitions`). Slots:
`weapon, offhand, core, plating, charm, boots, focus, sigil`. A record is
`{version=1, owner, host='player', capacity, slots={slot=item}, owned={item=count}}`.

Items are not free: `acquire`/`release` manage a bounded owned stash
(`max_owned` distinct, `max_owned_per_item` per item) and `equip` requires the
item to be owned. Validation rejects a saved record that equips an unowned item.
Two-handed items declare `occupies`; occupancy conflicts are enforced **both
ways** — a two-hander blocks a later offhand item, an equipped offhand item
blocks equipping a two-hander, and a saved record with either conflict is invalid
— while an explicit replacement (equipping into the occupied key's own slot) is
preserved and frees the previously occupied slot.

>=8 supported definitions contribute one bounded delta per item to the occupied
gene slots listed in `placements`, and only when the item's `family` is `any` or
matches the gene family read from `Core.definitions`. Contributions resolve
**once** into deterministic modifier ids `eq:<host>:<item>:<gene_slot>`.

`apply` is a transactional reconciliation: it removes stale `eq:<host>:`
modifiers not in the desired set and installs the desired set, snapshotting the
host's modifier table and restoring it exactly if any Core call returns
false/nil, throws (even after a side effect), or hits Core's modifier capacity.
`revert` uses the same all-or-nothing contract to clear every `eq:<host>:`
modifier: a failed or throwing remove restores the host's table and returns
`nil,reason`; a successful clear returns the removed count (`0` is a real
success, never reported as a refusal). Only this host's modifier table is
replaced on rollback, so other hosts and non-equipment contributions survive.
Because `Core.resolve` rebuilds each stat from base + upgrades + currently active
modifiers, apply/revert and loadout swaps are exact and produce **no numerical
drift** (tested five cycles plus snapshot equality and swap reconciliation).

Both `apply`/`revert`/`modifiers` validate the record and check the ownership
domain (owner must equal `run.id`; host must exist) before resolving. A malformed
or foreign record is refused (`nil,reason`); a valid record that contributes
nothing returns `0` — a refusal is never reported as an empty success.

Native policy: this layer is stat resolution only. It never binds, deletes or
replaces a fighter's built-in sword, shield or scabbard. Definitions requesting a
native held item (`native_item`/`native`/`held_item`/`mesh`) are refused
("native held items are not supported"); `Equipment.native_held_items_supported`
is `false`. No native held-item API exists or is called — the test runs the
service against a spy Core whose metatable errors on any access outside the four
permitted functions.

Two-handed items declare `occupies` slots and are refused while an occupied slot
holds another item until it is unequipped.

## 5. `inventory.lua` — collection adapters

Preview adapters run the actual Core operation on a `snapshot`/`restore` clone,
so they report exact Core behaviour without mutating the live profile/run:

* `Collection.breed_preview` — deterministic child id/seed and a bounded positive
  `breed_cost`; reports `requires_discard` when the collection is full.
* `Collection.commit_breed(Core, profile, ledger, a, b, {confirm=true})` — charges
  the exact quoted cost (no free reroll; every breed costs and requires
  confirmation) then calls the real `Core.breed`. A failed breed leaves the
  caller's ledger untouched because the spend was staged.
* `Collection.export_preview` — refuses enemy-owned genes via the real
  `Core.finish` rule; requires confirmation.
* `Collection.fusion_preview` — real `Core.fuse` on a clone; equipped parents are
  refused; reports the child. A stale staged plan whose target was fused away
  fails `Inventory:validate_plan`.
* `Collection.discard_preview` / `commit_discard` — full-collection
  replacement/discard requires confirmation and refuses a gene still referenced
  by another gene's ancestry (dangling-reference guard).

## 6. `inventory.lua` — bounded economy

`Economy.new({cap})` → `{version=1, currency, cap, earned, spent}`. Sources are
enumerated (`run_success`, `run_failure`, `reward`, `sell`, `discard`, `refund`);
`earn` clamps at `cap` and `spend` refuses below zero, so no loop can inflate
currency past the cap. `reward_value(outcome, difficulty)` and
`breed_cost(Core, profile, a, b)` are deterministic, and the breeding cost is
always positive, so there is no free/limitless reroll.

## 7. `run_history.lua` — bounded history

`RunHistory.new(owner, {max_entries, overflow='refuse'|'evict'})`. Entries carry
outcome, run id, optional seed/stocks/frames/gene/currency and id arrays
(`rewards`, `mutations`, `rooms`) capped at `max_array = 16` with an honest
`truncated` flag. `append` returns a staged copy and refuses or evicts the oldest
entry. Serialization uses the injected sandbox-safe `Codec` — never Core's frozen
save codec and never `load`.

`RunHistory.from_core_finished(owner, profile, opts)` is the explicit migration
boundary: it reads Core's `profile.finished` (`{outcome, export}`) in run-serial
order, invents no fields, and never mutates the profile (tested by snapshot
equality).

## 8. API summary

```
Inventory.new(deps) -> service
Inventory.create{owner,scope,capacity} -> record | nil,reason
Inventory.def(id) / classify(def)
Inventory.validate(record) -> ok | false,reason
Inventory.count/cooldown/available
Inventory.acquire(record,id,amount) -> staged | nil,reason
service:plan_use(record,id,ctx) -> plan | nil,reason   -- ctx: frame, context, run/profile, progress, target, effects
service:validate_plan(plan,{inventory=...,item=...,run=...,frame=...,context=...,target=...,effects=...}) -> ok | nil,reason
service:encode(record) / decode(text)
Inventory.from_legacy_supplies(value,opts)
Inventory.Economy.{new,validate,earn,spend,reward_value,breed_cost}
Inventory.Collection.{breed_preview,commit_breed,export_preview,
  fusion_preview,discard_preview,commit_discard,parent_references}

Equipment.new(Core,deps) -> service
Equipment.{slots,definitions,create,validate,owns,acquire,release,equip,unequip}
service:modifiers(record,run) -> list | nil,reason
service:apply(run,record) -> count | nil,reason
service:revert(run,record) -> count | nil,reason
service:encode/decode

RunHistory.new(owner,opts) / make_entry(run,summary) / append
RunHistory.validate / summary / encode(history,codec) / decode(text,codec)
RunHistory.from_core_finished(owner,profile,opts)
```

All defined records have `version = 1` and reject unknown fields, so a future
incompatible record is preserved rather than silently adopted.

## 9. Tests and evidence

`tools/roguelite/test_inventory_economy.py` (16 named cases, pure Lua, no engine):
capacity zero/caps/stacking; reject-before-spend, ownership domain and rollback;
cooldowns and context restrictions; legacy supplies preserving count/meaning
without route mutation or resource inflation; equipment owned acquisition/release
and unowned-equip refusal; equipment reversibility/no-drift; symmetric two-handed
occupancy and saved-record rejection; foreign/invalid record refusal and the
0-vs-refusal distinction; transactional apply and revert rollback on
return-false and throw (including after a side effect) and actual Core modifier
capacity, with unrelated hosts/contributions preserved and stale-mod swap
reconciliation; native-item
refusal and Core API surface; canonical plan reconstruction refusing forged
effects, unstaged inventory, swapped item/cost, altered binding,
replayed/foreign/stale plans, changed capacity/target/heal-contract and
fractional charge; run-history bounds/Codec/Core migration;
breeding/export/fusion/discard with confirmation, enemy refusal and dangling
references; a fresh/established economy simulation with bounded currency and
honest support status; and route reward-spec persistence with no reroll.

Run: `python3 -m unittest test_inventory_economy -v` from `tools/roguelite`, or
the full discover command in `docs/ROGUELITE-ACCEPTANCE.md`.

## 10. Integration requirements (owned by the integration worker)

1. Bundle the three modules in `tools/roguelite/prepare.py` (add
   `('inventory','Inventory')`, `('equipment','Equipment')`,
   `('run_history','RunHistory')` before `main.lua`), then rebuild the installed
   bundle.
2. In `main.lua`, construct the services with the bundled `Codec`, `Core` and
   `Progress`, and drive the documented transaction order: stage → validate
   (including `Inventory:validate_plan` with the current record and
   `Equipment:apply`, passing the `run` whose `id` matches `owner`) → persist in
   the TBD3 checkpoint → commit. On any failure keep the previous committed
   record. `plan_use` needs `run` (and `progress` for supply/key) so the
   ownership domain can be checked; equipment records must be created and
   acquired before an item is equipped.
3. Persist the inventory/equipment/history records alongside the existing
   profile/run/manifest/progress sections, or add explicit checkpoint fields; do
   not regenerate them from the catalogue.
4. UI/menus, native heal/charge application and visual mapping remain integration
   work; this pass ships only the pure mechanics.

## 11. Honest support status / unavailable evidence

* Native effect application, in-engine item use, equipment visuals and menu
  affordances are **not implemented** here; the modules expose intents only.
* No native build, install, game run or human playtest was performed (headless
  Linux agent, no disc images). Nothing is claimed live.
* `frost_tonic`, `smoke_bomb`, `bomb_core`, `ghost_lens` and `ruin_blade` are
  deliberate refusals, not missing tests.
* Balance numbers (cooldowns, costs, deltas) are defaults pending human review.
