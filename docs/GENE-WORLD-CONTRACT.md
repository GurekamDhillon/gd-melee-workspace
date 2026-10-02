# Native gene-world adapter contract (Gate 5 world seam), review-3

Status: **prototype contract, independent worker output, not integrated and not
offered in shipping gameplay.** Authored 2026-09-30 by the bounded DeepSeek
gene-world worker; corrected in review-2 and review-3 against the refreshed
accepted dependencies. It binds the final `gene_actions` transaction to the
documented `gd.*` native calls. It does not claim native collision-loop proof,
balance, engine integration or human play; root owns wiring it into `main.lua`
and `prepare.py`.

Accepted dependency hashes are recorded in `GENE-WORLD-REVIEW-SEED.json`. This
lane adds only the bounded optional intent hooks below to the accepted
`gene_actions.lua`; Core and gene_behaviors are unmodified.

## 1. Files and ownership

| Path | Kind | State |
| --- | --- | --- |
| `melee/worktrees/linux/pc/scripts/examples/roguelite/runtime_gene_world.lua` | new native adapter | frozen for review |
| `tools/roguelite/test_gene_world.py` | new contract test | frozen for review |
| `docs/GENE-WORLD-CONTRACT.md` | this document | frozen for review |
| `melee/worktrees/linux/pc/scripts/examples/roguelite/gene_actions.lua` | accepted engine + 3 bounded optional hooks | frozen for review |

Not touched: `core.lua`, `gene_behaviors.lua`, `gene_catalogue.lua`,
`enemy_genes.lua`, `main.lua`, `prepare.py`, native code or other workers.

## 2. Constructor and injected binding

```lua
local world = GeneWorld.new(Core, engine, opts)
```

`engine`: `gd` (required), `get_run` (required), and optional `current_room`,
`visibility`, `invulnerable`, `reflecting`, `status`, `guard`, `conversion`,
`native_hit_contract`. `opts` may repeat any optional provider and set
`max_targets`/`max_bindings`/`max_contributions`.

## 3. Bounded engine hooks (`gene_actions.lua`)

Additive and optional only:

- `begin` calls `world.capture_intent(run, host, slot, target, spec)` after
  target selection and before any spend; a present hook returning `nil` or
  throwing refuses the action.
- `release` calls `world.validate_intent(run, rec.intent)` before the spend
  point; a present hook must return exactly `true`, else the action is cancelled
  with no spend.
- `request` carries `intent = rec.intent` to the mutation.

A world without either hook is unchanged; the accepted 34-group
`test_gene_actions.py` passes against this file and a hookless world still
completes an action.

## 4. Intent identity

`capture_intent` freezes `{run, source gen/ref/kind/port/handle/team/room/token,
target_host, target identity, room, spec}`. `validate_intent` re-checks the run
reference, source/target binding identity, current room, confirmed native
capability and target eligibility. Any change cancels before `Core.activate`,
including a Core-owned Rime mark whose target was rebound. `can_start` is
side-effect-free.

## 5. Native API mapping and the hit-acceptance opt-in

| seam | native call | contract |
| --- | --- | --- |
| fighter -> fighter | `gd.hit(port, {damage, angle, kbg, bkb, from})` | needs `native_hit_contract` |
| fighter -> owned custom | `gd.enemy_hurt(handle, {from, damage, angle, kbg, bkb, reach})` | audited separate contract |
| owned custom -> fighter | `gd.enemy_strike(handle, port, {damage, angle, kbg, bkb, reach})` | needs `native_hit_contract` |
| custom -> custom | none | refused |
| movement (fighter only) | `gd.impulse(port, {x, y})` | audited separate contract |
| Rime mark | none here | `Core.activate` owns the logical mark |

`gd.hit`/`gd.enemy_strike` route through `ftColl_80076640`, where native `false`
can already have chipped armor. Until root wires corrected native APIs, those
paths require `native_hit_contract = 'accepted_damage'`; without it they refuse
**before** the native call. Even with the opt-in, `true` means "accepted native
damage action (including armor absorption)", never proof of percent loss,
knockback, defeat or a collision callback. `gd.impulse` is a fighter-only
locomotion velocity: a custom-actor movement direction is impossible and refuses
at `begin` with no spend, refund or native call.

## 6. Eligibility and capability

- Player eligibility requires a **complete, explicitly known** native state:
  `body_state` and `timed_state` in `{normal, invincible, intangible}`, numeric
  `invincible`/`intangible` timers and a boolean `shield_on`. Any missing or `?`
  value is unknown and fails closed (no damage).
- `invulnerable` provider contract is strict boolean: `true` = invulnerable
  (refuse), `false` = explicitly not invulnerable (safe), `nil`/throw/other =
  unknown (refuse). Enemy `vulnerable` must be exactly `true`; a missing value
  fails closed.
- `capabilities()`, `supports(gene, slot, direction)` and `eligibility()` report
  the actual `gd`/provider availability and direction with a reason. A callable
  adapter stub is not capability proof: a missing native function or provider
  refuses at `begin` before any spend.

## 7. Contribution ownership

- Acceptance requires the provider's exact `true`; a `{ok=true,contrib=...}`
  table is not acceptance.
- **Any identifiable token is owned for cleanup regardless of acceptance.** On a
  refusal (false/nil/table success) or capacity limit the adapter attempts
  cleanup immediately; if the release refuses, the record is retained and
  retried by `reset`/`release`.
- Cleanup always calls `provider.release` with the run the token was minted in
  (`record.run`), never a later run after a `get_run` switch.
- `reset(run)` releases every owned token, refuses while a release is refused,
  and never forgets a native token on refund, reentrant release or reset.

## 8. Missing native capabilities (handoff)

No native occlusion/LOS, no fighter reflection read, no native guard/root/
freeze/convert/siphon seam, no custom-vs-custom strike, no dodgeable startup.
Armor `x221C_b4`, armorHP `x1834` and the opaque collision immunity flag
`x221D_b6` are not exposed by the readers. All are refused, never emulated.

## 9. Test evidence

```sh
python3 -m unittest tools.roguelite.test_gene_world -v
```

16 finding groups against the accepted dependencies with a stateful `gd` double:
capability/eligibility table; the hit-contract opt-in (refusal before any call
without it, correct shape with it); fighter/custom/custom-strike shapes;
team/room/dead/invincible/unknown/range/facing/shield refusals with a
known-normal success; unknown body/timed/shield and nil/error invulnerability
providers failing closed; missing native capability refused at `begin`;
false/nil/throw refunded once; movement free-state and impulse refusals; custom
traversal impossible direction refused at `begin` while fighter traversal
succeeds; unsupported root refused with no side effects; deterministic ties;
forged/NaN/infinite bounds; intent drift (movement port/token, Rime mark target,
run, room, handle) cancelling before spend; two simultaneous actions independent;
provider exact-true, rejection of table success, token cleanup on refusal,
retained refused cleanup and reset, owning-run cleanup; direct seam metadata and
Core mark ownership; hookless-world compatibility.

Full discovery is not green by design: 188 tests with 3 pre-existing
environmental errors (missing generated `menu/out_effects_study` manifest,
missing room-kit sidecars, `test_runtime` import quirk) and 4 skips. The accepted
34-group `test_gene_actions.py` passes against this lane's `gene_actions.lua`.

**Contract test, not native hit proof.** The double returns booleans; it runs no
Melee collision, hitlag, armor absorption, shields, projectiles or collision
callback.

## 10. Root integration requirements

1. Merge the three bounded `gene_actions.lua` hooks or land the lane file.
2. Bundle `runtime_gene_world.lua` before `main.lua`; construct one world with
   the real `gd`, `get_run`, `current_room` and a trustworthy `visibility`
   provider; bind/unbind actors with a per-encounter `token`.
3. Set `native_hit_contract` only after confirming the accepted native
   damage-result semantics.
4. Live collision/shield/immunity/controller acceptance remains a separate
   native validation pass.
