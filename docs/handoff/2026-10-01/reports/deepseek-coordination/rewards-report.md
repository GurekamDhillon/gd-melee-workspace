I'll start by exploring the codebase to understand the existing structures.

I have enough context. Let me set up a todo list and write the module.

All 9 new tests pass. Let me review the final module once more and verify no global leaks.

Let me expose small public wrappers for target/family inspection instead of tests reaching into private methods.

Done. Stopping editing.

## Owned files (only these changed)
- `melee/worktrees/linux/pc/scripts/examples/roguelite/runtime_rewards.lua` (new, 501 lines)
- `tools/roguelite/test_reward_runtime.py` (new, 250 lines)

Baseline dirty Sol modules (`adapter/progress/room_recipes/rooms/route.lua`) untouched; no commits/staging/build/install.

## Exact API
`local R = RuntimeRewards.new(Core, {Progress=P, EncounterCatalogue=EC, GeneCatalogue=GC})` — `GeneCatalogue` optional; deps injected, no `require`, no globals.

- `R:classify(spec)` → `{id,version,kind,family,supported,reason,mechanic,requires_target,requires_effect,stat,delta,adds,removes,supply,heal,charge}`. `supported` = mechanic exists in Core/Progress, independent of a run.
- `R:supported_definitions(catalogue?)` → sorted classify results; the generator-admission filter (`supported` + honest `reason`).
- `R:gene_family(kind)` / `R:family_kinds(family)` → implemented bridge read from `Core.definitions` (not guessed).
- `R:targets(run, spec)` → eligible `{id,kind,family,host,slot}`.
- `R:preview(ctx)` → view or `nil,reason`; enumerates `targets` when no `ctx.target`, else resolves it.
- `R:commit(ctx)` → `{ok=true, kind,family,spec,claim_id,room_id,run,progress,target,benefit,cost,changes,effects,message}` or `nil,reason`.
- `ctx = {run, progress, spec | node, room_id | node.id, target?, effects?}`. `claim_id = 'reward:'..room_id`; requires `progress.visited[room]` and `progress.objectives[room]=='done'`, refuses if already claimed.
- `run/progress` returned are staged copies (`Core.snapshot/restore` + validated `Progress`); originals never mutated. Preview and commit both call the same internal resolver, so stats cannot disagree.

## Supported / refused content
- Supported: 8 stat upgrades + 7 tradeoffs (fire/frost/any) via `Core.reward`; `supply_crate`/`supply_pack` as bounded `progress.supplies`; `repair_kit`/`charge_flask` as **deferred intents** gated on `ctx.effects={version=1,heal=true,charge=true,...}`.
- Refused explicitly: all mutations/reactions (`implemented=false`), all equipment (no Core slot/ownership), `overcharge`/`storm_pin`/`chain_spark`/`echo_mark` (cobalt has no implemented Core family), fully-clamped upgrades, and any tradeoff whose gain or cost is at cap (all-or-nothing).
- Effects: `{kind='heal',target='player',amount,contract_version=1}` and `{kind='charge',host='player',slot,gene,amount,before,target,capacity,contract_version=1}`; no effect intent is produced without the contract.

## Tests
`python3 -m unittest tools.roguelite.test_reward_runtime -v` → **9/9 OK** (supported filtering, upgrade preview==commit, cap boundaries, tradeoff atomicity both directions, family/target/enemy-owner filtering, duplicate/uncleared/unvisited claims, forged spec, supplies cap, heal/charge contracts + full-charge refusal, snapshot round-trip and rollback contract, classify refusals). Full discovery `python3 -m unittest discover -s tools/roguelite -p 'test_*.py'`: my 9 pass; only 2 pre-existing artifact errors (`test_rooms`, `test_runtime`) from missing `menu/out_*` art, unrelated and present without my files.

## Required root wiring (not done here)
1. `prepare.py` bundle: add `('runtime_rewards','Rewards')` before `main` (order flexible; deps are injected).
2. `main.lua`: `local rewards = Rewards.new(Core,{Progress=Progress,EncounterCatalogue=EncounterCatalogue,GeneCatalogue=GeneCatalogue})`; supply the v2 `Progress` record and the resolved `node.reward_spec` (from `Route`/adapter) to `rewards:preview/commit`; persist returned `run`+`progress`, then apply `effects` (heal via `gd.set_percent`; charge via `run.hosts.player.state[slot].charge = intent.target`), discarding the transaction if either fails.
3. `menus.lua`: replace the four fixed `rewards` cards + `apply` branch with `preview` enumeration and `commit`; render `targets[].changes/benefit/cost/message`.
4. Pass `effects={version=1,heal=true,charge=true,max_heal=100}` only if root can commit those native/Core effects; otherwise heal/charge stay refused by design.

Limitations: pure-module only — no native build/game ran, so this does not prove in-engine play or balance; v2 wiring and the effect contract application are root's.
