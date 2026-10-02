# B3 — Inventory / equipment / collection / economy audit (read-only)

Lane: B3. Author: read-only audit agent. Date: 2026-09-30.
Scope: `melee/worktrees/linux/pc/scripts/examples/roguelite/` — `inventory.lua`, `equipment.lua`,
`run_history.lua`, `core.lua`, `menus.lua`, `runtime_rewards.lua`, `runtime_campaign.lua`,
`main.lua`, `checkpoint.lua`, `codec.lua`, `progress.lua`, `route.lua`, `encounter_catalogue.lua`,
`room_recipes.lua`, `adapter.lua`; the bundler `tools/roguelite/prepare.py`; the installed bundle
`_build/agents/linux/mods/roguelite/scripts/main.lua`; the tests
`tools/roguelite/test_inventory_economy.py`, `tools/roguelite/test_economy.py`.
Specification: `docs/INVENTORY-ECONOMY-CONTRACT.md` (read in full), Gate 7 of
`docs/ROGUELITE-COMPLETION-PLAN.md` (§12, lines 274–296), and
`docs/HANDOFF-PERSISTENCE-BATCH2-2026-09-30.md`.

**No build, no game run, no console (51701) connection.** Nothing was modified, staged or
committed except this report. Frozen lanes under `_build/deepseek-worktrees/`,
`_build/sol-worktrees/`, `_build/model-tests/` were not touched.

What *was* executed (headless, no engine):

```
cd tools/roguelite && python3 -B -m unittest test_inventory_economy -v
→ Ran 16 tests in 0.313s — OK
```

plus two small read-only Lua probes against the real `route.lua`/`adapter.lua`/`room_recipes.lua`
(see §6.1). These are decision/model tests. They prove no consumable was ever handed to a player,
no equipment exists in a build, and no economy number was ever seen on screen.

---

## Summary

**The single largest finding: `inventory.lua`, `equipment.lua` and `run_history.lua` are dead
code.** They are not in the bundle list, not installed, and referenced by nothing. I verified all
three of those independently (file grep, `prepare.py` read, installed-bundle read).

```
tools/roguelite/prepare.py:34-39   bundle list — no ('inventory',…), ('equipment',…),
                                   ('run_history',…)
grep -rn 'Inventory|Equipment|RunHistory' rogue*.lua   → only a prose comment in gene_actions.lua:18
grep -c 'Inventory' _build/agents/linux/mods/roguelite/scripts/main.lua   → 0
```

Every reference to these three modules lives in `test_inventory_economy.py`, which `loadfile`s
them by path (PRELUDE lines 23–25) — so the 16 passing tests exercise code the game never loads.
The contract itself says this plainly (§3–§10: "pure-service implementation… Not yet wired into
`main.lua` and not yet in a shipping bundle"), and §10.1 assigns bundling to an integration worker
that has not done it. **This confirms the previous lane's note and raises it to a verified fact.**

What a player actually gets today:

* **Consumables: exactly one — Restore.** It is not an inventory item at all. It is the integer
  `run.progress.supplies` (0–9, `core.lua:47`, `core.lua:401`), spent at
  `runtime_campaign.lua:774-792` (`use_supply`) or, on the v1 path, inline at `main.lua:1021`.
  There is no ownership record, no stacking, no capacity, no cooldown, no context restriction,
  no pre-use refusal beyond "supplies > 0". None of the 13 catalogue consumables in
  `inventory.lua:83-129` exist in the game.
* **Equipment: zero.** No equipped-item record, no slots, no ownership. What the player manipulates
  is *genes* placed into three anatomical slots (`assault`/`guard`/`traversal`,
  `core.lua:185-196`), which are simultaneously the stat container, the placement system and the
  thing the mannequins draw (`menus.lua:355-367`). A gene is a body part; there is no separate
  "item equipped on the body" concept to distinguish from Marth's sword.
* **Collection/economy:** breeding and fusion are genuinely implemented and reversible; inventory
  and equipment are not. The permanent currency ledger (`Inventory.Economy`) exists only inside
  the dead module. `Core` has no currency field at all — `profile` fields are fixed at
  `core.lua:396` (`type,id,version,seed,world_seed,next_run,genes,finished`), so there is nowhere
  to store one without a schema change.
* **Persistence:** the reward-offer guarantee **partially holds** — the offer *spec* is persisted
  in the manifest before the player ever sees it (§5.1), but the *offer list* and the pending
  `reward_room` flag are in-memory only (`runtime_campaign.lua:87`, `:425-427`), and the v1
  reward path (`menus.lua:61-66`, `menus.lua:333-345`) has no persistence of offers at all and
  keys `claimed` by bare room id while the v2 path keys it `'reward:'..id` — a real collision risk
  documented as unresolved in the handoff (`HANDOFF-PERSISTENCE-BATCH2-2026-09-30.md:122-124`).

A second-order finding that dominates everything else: **the v2 route cannot currently be created
at all**, so most of the code I audited is itself not live. `RoomRecipes` ships every recipe with
`certified = false` (`room_recipes.lua:82`), `Adapter:check` refuses any manifest containing an
uncertified recipe (`adapter.lua:47-50`), and `Route:create` calls it (`route.lua:47`). I ran
this: `route:create` returns `nil` with the shipped recipes and returns a table only after I
forced `certified = true` in memory. The live runtime is therefore the **v1 `Dungeon` slice**, which
routes around `RuntimeCampaign`, `RuntimeRewards`, `RuntimeRooms` and the transactional save path
entirely. Every "implemented" persistence verdict below is therefore about code that does not run.

---

## Capability table

| # | Feature (contract §) | Status | Evidence |
|---|---|---|---|
| **Reachability** ||||
| 1 | `inventory.lua` bundled (`prepare.py`) | **MISSING** | `prepare.py:34-39` — absent from list; installed bundle has 0 occurrences |
| 2 | `equipment.lua` bundled | **MISSING** | same |
| 3 | `run_history.lua` bundled | **MISSING** | same |
| 4 | Services constructed in `main.lua` | **MISSING** | no `Inventory.new` / `Equipment.new` / `RunHistory.new` in any bundled `.lua` |
| 5 | Called from `menus.lua` | **MISSING** | `menus.lua` never mentions them; only live genes (`C.equip/C.reward/C.breed/C.fuse`) |
| 6 | Dead-code verdict | **CONFIRMED** | `inventory.lua`, `equipment.lua`, `run_history.lua` are unreachable at runtime |
| **Consumables (§3)** ||||
| 7 | Owned inventory record | **MISSING (live)** | live model is `run.progress.supplies` integer, `core.lua:47`, `core.lua:401` |
| 8 | Stacking (`stack_max` per def) | **MISSING (live)** | `inventory.lua:85-117` defines them; nothing consumes them |
| 9 | Capacity on distinct stacks | **MISSING (live)** | `inventory.lua:213` validates; no live record exists |
| 10 | Cooldowns | **MISSING (live)** | `inventory.lua:278-279` / `:352`; live path has none |
| 11 | Context restrictions | **MISSING (live)** | `inventory.lua:280`; live Restore usable from any pause state |
| 12 | Truthful pre-use refusal | **PARTIAL** | live: `main.lua:728` blocks Restore at 0 supplies with a reason; **but** `main.lua:1021` (v1 path) has no `gd.player(1)` nil-guard and no save-failure rollback |
| 13 | ≥6 consumable types (plan line 89) | **1 of 6+** | only Restore (`commands.lua:20`, `commands.lua:200-203`) |
| 14 | `from_legacy_supplies` migration | **NOT CALLED** | `inventory.lua:407-420`; zero live callers |
| **Equipment (§4)** ||||
| 15 | Slot ownership record | **MISSING** | `equipment.lua:144-151`; no live analogue |
| 16 | Reversible stat contribution | **MISSING** | `equipment.lua:309-359` (`apply`/`revert`); live genes resolve through `Core.resolve` only (`core.lua:198`) |
| 17 | 8 slots / ≥8 definitions (plan line 89) | **MISSING (live)** | `equipment.lua:69-87` defines 12 supported; 0 reachable |
| 18 | Owned-before-equip / unowned refusal | **MISSING (live)** | `equipment.lua:175`, `:238` |
| 19 | Two-handed symmetric occupancy | **MISSING (live)** | `equipment.lua:117-133`, `:181-188` |
| 20 | **Gameplay item vs. built-in sword/accessory distinguished** | **NOT ATTEMPTED** | the only slot system is genes-as-body-parts (`core.lua:185-196`, `menus.lua:355-367`); no separate item layer exists to distinguish, so contract §4 "never binds/deletes the fighter's built-in sword" is untested in reality |
| 21 | Native held-item refusal | **N/A live** | `equipment.lua:97-99`, `equipment.lua:34` — honest refusal, but no live code path reaches it |
| **Collection (§5, plan line 91)** ||||
| 22 | Gene inspection | **IMPLEMENTED** | `menus.lua:32-41` (`detail`), `menus.lua:376-388` (stat panel) |
| 23 | Comparison (parent↔child) | **IMPLEMENTED** | `menus.lua:411-424` (trait/parents/child table), `menus.lua:186-188` (before/after) |
| 24 | Ancestry display | **PARTIAL** | `menus.lua:386` shows `Parents a + b` or `Origin` — one line, no tree, no grandparent depth |
| 25 | Sorting / filtering | **PARTIAL** | `menus.lua:10` sorts by numeric id suffix only; **no filter control exists** |
| 26 | Breeding | **IMPLEMENTED** | `menus.lua:209-210` (preview on clone), `menus.lua:318-320` (commit), `core.lua:301-306`; parents retained |
| 27 | Breeding cost surfaced | **MISSING** | `menus.lua:209` calls `C.breed` directly; no economy ledger, no cost shown to the player |
| 28 | Inheritance locks | **IMPLEMENTED (1 stat)** | `menus.lua:223` (single `LOCK INHERITED POWER` button, `stat='potency'`), `menus.lua:315-317`, `core.lua:297-300`; lock *effect* previewed at `menus.lua:421` (`LOCK` suffix) |
| 29 | Fusion | **IMPLEMENTED** | `menus.lua:50-60` (unequips parents first — no dangling ref), `menus.lua:321-323`, `core.lua:307-314` |
| 30 | Discard / replacement | **BROKEN in live flow** | the `DISCARD SELECTED` control exists at `menus.lua:236-239` but only when `ctx.capacity.full` — and `main.lua:779-783` (`menu_context`) **never sets `capacity`**; and `Menus.apply` has no `'discard'` branch, so it falls to `menus.lua:347` `'Lifecycle action must be handled by main'` → **the button always refuses** |
| 31 | Full-capacity handling (no silent loss) | **PARTIAL** | `menus.lua:190-192` shows a note; `main.lua:387-388` silently drops the export when the profile is at 128 genes — **no replacement/discard decision is offered**, exactly what the contract forbids |
| 32 | Destructive confirmations | **IMPLEMENTED** | `menus.lua:286-298` — two-press bound to action identity + menu + section + generation |
| 33 | Run history | **MISSING (live)** | `run_history.lua` unbundled; `profile.finished` exists (`core.lua:396`) but no screen reads it (`main.lua:1248` only counts it in a log line) |
| 34 | Victory export **choice** | **MISSING** | `main.lua:387` picks `h.slots.assault or traversal or guard` **automatically**; contract/plan (line 98) requires offering the player the choice |
| **Economy (§6)** ||||
| 35 | Bounded currency ledger | **MODULE-ONLY** | `inventory.lua:428-470`; not bundled, not called; `Core` has no currency field (`core.lua:396`) |
| 36 | Deterministic reward value | **MODULE-ONLY** | `inventory.lua:472-476` |
| 37 | Deterministic non-zero breed cost | **MODULE-ONLY** | `inventory.lua:481-488` |
| 38 | Simulation / tuning harness | **PARTIAL** | `tools/roguelite/test_economy.py` (40-run fresh + capacity profile) and `test_inventory_economy.py:588-630` (30-run ledger sim). Pure model, **not connected to any live reward source** |
| **Persistence (§5 of task, contract §2/§10.3)** ||||
| 39 | Reward **spec** persisted before choice | **HOLDS (v2 code)** | `route.lua:45` copies `reward_spec` into the manifest at route creation; manifest is written by `main.lua:244`/`Checkpoint.encode` before any play; `route.lua:101` refuses a save whose spec drifted from the catalogue |
| 40 | Reload cannot reroll offers | **PARTIAL** | spec: yes (`route.lua:45`, `main.lua:244-247`). Offer **list/claim**: v2 `reward_room` is in-memory only (`runtime_campaign.lua:87`, `:425-427`, `:561-562`) and is lost on reload — but it is *re-derived* from the persisted `claimed` flag, so no reroll; the real risk is a **lost pending offer** if the player quits at the reward, plus the v1/v2 `claimed` key mismatch (`menus.lua:339` bare id vs `runtime_rewards.lua:304` `'reward:'..id`) which `route.lua:148-149` treats as disagreement |
| 41 | Full capacity, no silent loss | **FAILS** | `main.lua:387-388` drops the export silently at 128 genes; no UI branch exists |
| 42 | Refused saves, no silent loss | **MOSTLY HOLDS (v2), FAILS (v1)** | v2: `save()` validates the staged generation *before* writing (`main.lua:270-276`), requires atomic write + readback (`main.lua:280-288`), and commits live refs only after (`main.lua:289-294`); `reward_commit` rolls the native effect back on save refusal (`runtime_campaign.lua:743-754`). v1: `main.lua:1021` calls `save()` and ignores the return value — a refused save silently loses the spend-and-heal |
| 43 | No repeated export | **HOLDS** | `core.lua:316` returns the existing `finished[r.id]` — `Core.finish` is idempotent (`test_economy.py:48-50`) |
| 44 | No dangling equipped parents | **HOLDS (fusion)** | `core.lua:308` refuses fusion while a parent is equipped; `menus.lua:52-54` unequips first. `inventory.lua:549-557` relies on the same rule |
| 45 | Records persisted with the profile | **N/A** | contract §10.3 asks for inventory/equipment/history sections in the checkpoint; none exist, because the records do not exist |
| 46 | Future-slot protection | **IMPLEMENTED (adjacent)** | `main.lua:256-262` (redirects around a protected slot), `main.lua:315-322` (`classify` sets `protected`), `checkpoint.lua:69`, `:108`, `:121` (`preserved` reasons) |
| **Honesty / support** ||||
| 47 | Unimplemented effects refused, not faked | **HOLDS in both layers** | `inventory.lua:151-153`; `runtime_rewards.lua:186-188` (mutations), `:207-210` (equipment); `menus.lua:284` surfaces blocked reasons |
| 48 | Balance numbers reviewed | **PENDING** | contract §10.4 — "defaults pending human review". No human playtest has occurred |

---

## Ranked gap list (player-visible impact)

**G1 — The inventory/equipment/run-history services are dead code.** A player will never hold,
stack, cool down, equip, unequip or inspect a single item, and no run is ever written to a
history. This is the whole of contract §3, §4, §6, §7 and roughly 60% of §5. Every other gap on
this list is a subset of it. *Fix: bundle the three modules (`prepare.py:34-39`) **and** wire them
in `main.lua` — bundling alone changes nothing a player can observe.*

**G2 — One consumable, and it is a raw integer, not an item.** Plan line 89 asks for ≥6 types with
ownership, capacity, stacking and cooldowns; the game has `Restore` = `progress.supplies`
(`core.lua:47`). A player sees `Restore x2` in a menu (`commands.lua:203`) and cannot learn why it
is 2, cannot carry a bandage next to it, cannot be told "on cooldown", and cannot be refused for
context.

**G3 — No equipment layer, so "equipment vs. the fighter's own sword" is unanswerable.**
Contract §4 and plan line 278 require a gameplay equipment record distinct from native held items.
Because the only slot system is genes-as-body-parts, there is no second layer to compare against.
A player choosing a "warding charm" sees a rectangle change colour on a mannequin
(`menus.lua:355-367`) and nothing else.

**G4 — Victory export is chosen automatically, and silently vanishes at full capacity.**
`main.lua:387` exports whatever is in `assault` without asking; `main.lua:388` then drops the
export entirely if the profile holds 128 genes, with no message and no discard/replace prompt.
Plan line 98 and the task's persistence clause both explicitly forbid this. The player loses a
run's inheritance with no feedback. **Highest-severity single bug in this audit** — it is silent
permanent loss of earned progress.

**G5 — The DISCARD SELECTED button can never work.** `menus.lua:236-239` gates it on
`ctx.capacity.full`; `main.lua:779-783` never supplies `capacity`, so the control never renders.
Even if it rendered, `Menus.apply` has no `'discard'` branch and would return
`'Lifecycle action must be handled by main'` (`menus.lua:347`). The player can never free a slot,
which is what makes G4 unrecoverable.

**G6 — No permanent economy at all.** No currency, no costs, no progression. Breeding is free
(`menus.lua:318-320` calls `Core.breed` with no ledger), so "no unlimited free reroll"
(plan line 98, contract §6) is satisfied only by accident — nothing is scarce. `Core`'s profile
schema has no currency field (`core.lua:396`), so this needs a schema change, not just wiring.

**G7 — v1/v2 `claimed` key mismatch.** v1 writes `claimed[node.id]` (`menus.lua:339`), v2 and
`route.lua:94` use `'reward:'..node.id`. `route.lua:148-149` rejects any save where the two
disagree, and `main.lua:107` strips the prefix in one direction only. A save that crosses paths
can be refused as `'claim records disagree'`. Documented as known in
`HANDOFF-PERSISTENCE-BATCH2-2026-09-30.md:122-124`.

**G8 — v1 restore path has no save-failure rollback.** `main.lua:1021` decrements supplies,
applies `gd.set_percent`, calls `save()` and ignores the result, then reports success. If the
save is refused, the in-memory spend is committed anyway and the player is told it worked. The v2
equivalent (`runtime_campaign.lua:774-792`) does roll back correctly.

**G9 — No run history screen.** Plan line 91 and completion-plan line 359 (complete results with
outcome, notable changes, collection consequences, chosen export) are unmet. The player cannot
see past runs, win rate, or what a run actually yielded.

**G10 — Collection sorting/filtering is one sort key and no filter** (`menus.lua:10`). Ancestry is
a single line (`menus.lua:386`). At 128 genes the library is an unfilterable paginated wall.

**G11 — Breeding cost and lock consequences are invisible.** `Inventory.Economy.breed_cost`
(`inventory.lua:481-488`) exists but `menus.lua:209` never calls it. Locks are limited to a single
`potency` button (`menus.lua:223`) even though `core.lua:297` supports all five stats.

**G12 — The v2 route is uncreatable, so the good persistence work is unreachable.** All recipes
ship `certified = false` (`room_recipes.lua:82`); `adapter.lua:47-50` refuses; `route.lua:47`
propagates. Verified by probe (§6.1). The live runtime is the v1 `Dungeon` slice, which bypasses
`RuntimeCampaign`, `RuntimeRewards`, `RuntimeRooms` and the whole transactional save path.

---

## 6. Notes on two specific questions

### 6.1 Is there a simulation / tuning harness? What does it prove?

Yes, two, both pure-Lua model simulations:

* `tools/roguelite/test_economy.py` — 40 mixed runs on a fresh profile plus a 128-gene capacity
  profile. Asserts bounded gene/ledger growth, that a failed export at capacity leaves the profile
  byte-identical, that `finish` without export still succeeds and is idempotent, and that a
  failure run adds no collection genes.
* `tools/roguelite/test_inventory_economy.py:588-630` — 30 runs driving a `Inventory.Economy`
  ledger with `reward_value`, `spend` and `commit_breed`, plus a 128-gene full-collection refusal.

**What they prove:** the Core invariants are internally consistent — caps hold, `finish` is
idempotent, a refused export does not mutate the profile, a failed breed leaves the ledger
untouched, currency clamps at `cap`.

**What they do not prove, and cannot:**

* Nothing is connected to a live reward source. The live rewards are `EncounterCatalogue.rewards`
  (stat deltas) and the fixed four-card v1 slice (`menus.lua:61-66`). Neither ever calls
  `Economy.reward_value`, so the simulated numbers are not the numbers the game uses.
* The 30-run simulation breeds `'g1' + 'g3'` on a fixed cadence (`test_inventory_economy.py:604`).
  That is a scheduler, not a player. It measures nothing about decision quality, build diversity,
  or whether progression is *interesting*.
* Every `assert` is a bound check. No test asserts a *rate*: nothing establishes how long a run
  takes, how much currency a competent player earns, or whether `breed_cost`
  (`inventory.lua:486`, `20 + floor((potency_a + potency_b) * 2)`, clamped 20–500) is affordable
  relative to `reward_value` (`inventory.lua:472`, 50–90 on success). **The economy has never been
  balanced against itself.**
* Pure Lua, no engine. Nothing here proves a reward reaches a menu, a save round-trips, or a
  screen renders.

Probe run for G12 (read-only, no files modified):

```lua
-- with shipped room_recipes.lua
route:create(run) → nil          (adapter:check refuses: recipe not certified)
-- after `for _,r in pairs(Recipes.recipes) do r.certified=true end` in memory only
route:create(run) → table
```

### 6.2 Do the persistence guarantees hold?

Trace: `main.lua:779-783` → `Menus.apply` → `main.lua:799-807` (`Core.snapshot` before, `save()`,
`Core.restore` the snapshot on refusal) → `save()` at `main.lua:216-295` → `Checkpoint.encode`
(`checkpoint.lua:24-44`) → `gd.data_write_atomic` + `gd.data_read` readback (`main.lua:280-288`) →
`Checkpoint.decode` (`checkpoint.lua:59-127`) with `pcall` guards at `main.lua:317`.

* *"Persist reward offers before choice; reload cannot reroll them"* — **holds for the v2 code
  path.** The reward spec is written into the manifest at route creation (`route.lua:45`) and the
  manifest is durably saved before any play (`main.lua:244-247`, `:266`), and `route.lua:101`
  refuses any resumed save whose spec no longer matches the catalogue. `test_inventory_economy.py:632-676`
  (`test_route_reward_specs_persisted_no_reroll`) asserts exactly this across a 200-seed sweep.
  **Caveat:** the *offer list* and the pending `reward_room` flag are not persisted
  (`runtime_campaign.lua:87`). They are recomputed from `claimed` on reload, so no reroll, but a
  player who quits at a reward screen returns to a room whose offer must be re-earned — untested,
  and I mark the resulting UX **PENDING human play**.
* *"Full capacity … without silent loss"* — **FAILS.** `main.lua:388`.
* *"Refused saves without silent loss"* — **holds in v2, fails in v1.** `main.lua:1021`.
* *"No repeated export"* — **holds** (`core.lua:316`).
* *"No dangling equipped parents"* — **holds** (`core.lua:308` + `menus.lua:52-54`).

---

## 7. Proposed implementation order

Sequenced so each step is independently observable and does not strand the next.

1. **Fix the two silent-loss bugs first, ahead of any feature work.** They are small, local and
   player-visible today: `main.lua:387-388` must present an explicit export choice and, at 128
   genes, open a discard/replace decision instead of dropping the export; `main.lua:1021` must
   check the `save()` result and restore percent + supplies on refusal. *No dependency on
   inventory/equipment.*
2. **Wire the discard path.** Supply `capacity` in `menu_context()` (`main.lua:779-783`) and add a
   `'discard'` branch to `Menus.apply` (`menus.lua:306`) calling `Inventory.Collection.commit_discard`
   (which already has confirmation and the dangling-ancestry guard, `inventory.lua:567-574`).
   Without this, step 1's full-capacity branch has nowhere to send the player.
3. **Reconcile the `claimed` key.** Settle the bare-id vs `'reward:'..id` question once, in
   `menus.lua:339` / `main.lua:107` / `route.lua:148-149`, and add a test that saves through both
   paths. Unblocks any later v2 work and closes G7.
4. **Bundle the three modules** (`prepare.py:34-39`, before `main.lua`) and add a bundle-content
   assertion to the Python suite so the modules cannot silently fall out of the bundle again.
   *This step alone is invisible to the player; pair it with step 5 or it will look like a no-op.*
5. **Make Restore an inventory item.** Construct `Inventory.new` in `main.lua`, seed it from
   `Inventory.from_legacy_supplies` (`inventory.lua:407`) so the count and meaning are preserved,
   add `legacy_restore` (and at minimum `repair_kit`, `field_bandage`, `supply_crate`,
   `charge_cell`) to the live catalogue, and route both `use_supply` call sites through
   `plan_use` → `validate_plan` → apply → save → commit. This is the step that finally makes
   cooldowns, capacity and truthful refusal real. Closes G2.
6. **Add the equipment record**, on top of step 5's persistence: `Equipment.new` in `main.lua`,
   persist it as its own checkpoint section (`Checkpoint.encode` needs a new length-delimited
   field, `checkpoint.lua:41-43`), and re-`apply` on every loadout change. Decide explicitly
   whether an equipment item is a *separate* entity from the gene body-part — that decision is the
   substance of contract §4 and plan line 278, and it should be written down before code.
7. **Add the economy.** `Core`'s profile schema needs a currency field (`core.lua:396`); add it,
   version it, migrate old saves. Then surface `breed_cost` in the breeding UI (`menus.lua:209`)
   and make `Economy.reward_value` the actual source of run payouts — currently the live rewards
   bypass it entirely. Then extend `test_economy.py` to assert *rates*, not just bounds.
8. **Run history screen**, from `RunHistory.from_core_finished` (`run_history.lua:189`) plus a
   per-run append at `Core.finish` (`main.lua:386`). Closes G9 and plan line 359.
9. **Collection UX**: filtering, real sorting, an ancestry view deeper than one line
   (`menus.lua:10`, `:386`). Lowest player impact of the list; do it last.
10. **Certification** (G12) is a separate lane's dependency, not this one, but it gates live
    verification of steps 5–8. Everything above is currently verifiable only as a model.

### What remains PENDING

Everything requiring a build or human play. Specifically: whether a supply crate is *worth* using,
whether any cooldown is felt, whether an equipment delta is visible on a real fighter, whether the
economy paces, and whether losing an export at full capacity (G4) is noticed at all without the
message. No claim is made that any of this works on screen.