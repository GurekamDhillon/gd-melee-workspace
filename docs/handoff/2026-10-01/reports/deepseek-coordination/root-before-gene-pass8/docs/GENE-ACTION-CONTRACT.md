# Gene action contract (Gate 5)

Status: **prototype contract, independent worker output, not integrated and not
offered in shipping gameplay.** Authored 2026-09-30 by the bounded DeepSeek
gene-actions worker. It implements Gate 5's action/event contract as two pure Lua
modules plus a real-module test. It does not claim native collision, engine
integration, balance or human play. The live game still runs its own immediate
`Core.activate` + `gd.hit`/`gd.impulse` path in `main.lua`; wiring this engine in
is a separate integration task owned by the live integration worker.

## 1. Files and ownership

| Path | Kind | State |
| --- | --- | --- |
| `melee/worktrees/linux/pc/scripts/examples/roguelite/gene_behaviors.lua` | new pure module | frozen for review |
| `melee/worktrees/linux/pc/scripts/examples/roguelite/gene_actions.lua` | new pure module | frozen for review |
| `tools/roguelite/test_gene_actions.py` | new test wrapper | frozen for review |
| `docs/GENE-ACTION-CONTRACT.md` | this document | frozen for review |

Not touched: `core.lua`, `gene_catalogue.lua`, `enemy_genes.lua`, `main.lua`,
`prepare.py`, any catalogue or shared runtime file. Existing Core APIs and old
saves are unchanged. `gene_behaviors.from_core()` fails if the offered cinder/rime
actions ever drift from `core.lua`.

## 2. What is authoritative

- `core.lua` is the authority for charge, spend, cooldown, caps, marks, the
  Thermal Shock reaction and serialization. This contract never re-implements
  them and never calls an engine global.
- `gene_catalogue.lua` remains the shipping exposure list. `gene_behaviors.lua`
  is the mechanic contract behind those definitions; it does not expose them.
- Only `cinder` and `rime` are admitted by default. Every other family is
  `offered = false` and is refused by the transaction unless a caller passes an
  explicit `opts.admitted` override. No new shipping exposure is created here.

## 3. Behavior contract (`gene_behaviors.lua`)

`GeneBehaviors` is data plus validation. A `(gene, placement)` record names a
route the transaction can execute and an effect kind on that route.

### Families and mechanics

| Family | Role | Primary mechanic | Genes |
| --- | --- | --- | --- |
| fire / Ember | pressure/damage | `damage` | `cinder` (offered), `emberline` |
| frost / Rime | control/mark | `control` | `rime` (offered), `glacier` |
| kinetic / Gale | movement | `movement` | `gale`, `dashstep` |
| aegis / Aegis | defensive/impact | `defense` | `bulwark`, `retaliate` |
| flux / Flux | resource conversion | `conversion` | `siphon`, `convert` |
| sigil / Sigil | mark/chain control | `chain` | `brand`, `chain` |

Mechanics map to transaction routes: `damage`/`chain` -> offense,
`control` -> control, `movement` -> movement, `defense` -> defense,
`conversion` -> conversion. `validate()` asserts the effect route matches the
mechanic route, so "movement", "defense", "resource conversion" and
"mark/control" are distinct code paths, not renamed damage.

### The twelve behavior sets

| Gene | Placements (action / mechanic / effect) |
| --- | --- |
| cinder | assault `eruption` damage burst; traversal `step` movement dash; guard `counter` defense counter (opponent-targeted) |
| emberline | assault `tracer` damage line; traversal `trailblaze` movement hover |
| rime | assault `mark` control mark; traversal `glide` movement hover; guard `mark` control mark |
| glacier | assault `freeze` control root (startup 6, recovery 10); guard `walls` defense guard |
| gale | traversal `gust` movement dash; assault `windblade` damage push |
| dashstep | traversal `cadence` movement dash (repeat 2); assault `momentum` damage burst |
| bulwark | guard `bulwark` defense guard; assault `bash` damage push |
| retaliate | guard `retaliate` defense counter; assault `riposte` damage burst |
| siphon | assault `siphon` conversion; guard `draw` conversion |
| convert | guard `lens` conversion; traversal `vent` movement dash |
| brand | assault `brand` chain; guard `sigilward` defense guard |
| chain | assault `chain` chain; traversal `linkstep` movement dash |

`cinder` and `rime` actions/triggers/categories are copied verbatim from
`core.lua` and re-checked by `from_core()`. Per-gene placement signatures
(action, mechanic, effect kind, trigger) must be distinct, gene signatures must
be globally unique, and every family must express its primary mechanic.

### Bounded placement policy

Each placement declares `startup`, `active`, `recovery` frames, `range`,
`height`, `arc`, `occlusion` (`line`/`ignore`), `spend` (`release`/`start`),
`refund` (`on_refuse`/`never`), `reversible` and `earning`
(`per_move`/`per_target`). All are bounded and validated. `native` marks the two
genes whose effect Core already drives today.

### Authored synergies (non-recursive)

Six cross-family reactions keyed by the same ids as `gene_catalogue.lua`:
`thermal_shock` (fire+frost, implemented), `plasma_surge` (fire+flux),
`charged_crystals` (frost+sigil), `chain_lightning` (kinetic+sigil),
`aegis_crush` (aegis+kinetic), `flux_bloom` (flux+frost). Thermal Shock is the
first and only one modelled against Core. `validate()` rejects a reaction whose
`input` consumes another reaction's `output`, so the table can never chain
recursively. Reaction lineage is also refused as a charge source by the
transaction and by Core.

## 4. Action transaction (`gene_actions.lua`)

`GeneActions.new(Core, Behaviors, world, opts)` returns a controller. Explicit
dependencies: the real `Core` module, the `Behaviors` module and a `world`
adapter. `GeneActions.new` asserts `Behaviors.validate` and
`Behaviors.from_core(Core)`.

```
preflight -> startup -> active -> recovery -> settled
```

- `c:preflight(host, slot, opts)` is pure: it resolves the equipped gene, checks
  admission, charge/readiness via `Core.ability`, free-state via
  `world.can_start`, the native seam, and the target policy. It mutates nothing.
- `c:begin(host, slot, opts)` starts a transaction from a successful preflight
  and returns a read-only record (or `nil, reason`). Charge is **not** spent yet.
- `c:advance()` runs one observation per unpaused logic frame, after
  `Core.tick`. Startup elapses, then the spend point fires, then active, then
  recovery, then settled. Order is deterministic (sorted keys).
- `c:on_event(event)` forwards a real contact to `Core.on_event`. Reaction
  lineage returns 0. `per_target` genes key the move by target using Core's
  existing `move_id`, so earning can be per move or per target without a new API.
- `c:interrupt(host, slot, reason)`, `c:clear([evidence])` and
  `c:on_room_leave()` release owned reversible state and drop records.

### Clock

The only clock is `run.frame`. `age = run.frame - start_frame` is bounded by
`caps.lifetime` (600). No wall-clock, no hidden timer. A non-integer or negative
age (clock regression) interrupts the transaction.

### Spend point, interruption and refund

Default `spend = 'release'`. Charge is committed exactly once, at the
startup->active transition, through the real `Core.activate` call. Consequences:

- Interrupted in startup: nothing was spent; the charge survives.
- Target dodges or is occluded at release: target is re-validated **before**
  spending; the action whiffs and the charge survives.
- Native application refuses after spending (`refund = 'on_refuse'`): the
  engine restores the pre-spend `Core.snapshot` in place, so every holder of the
  run reference sees the refund. `refund = 'never'` leaves the charge spent.

### Target policy (range, facing, occlusion)

For opponent routes the engine selects a target via `world.query`, then applies
its own pure policy: horizontal reach from `Core.ability.reach` (falling back to
the spec range), a vertical band, a facing arc for `arc = 'facing'`, and an
optional line-of-sight check via `world.occluded` when `occlusion = 'line'`.
Self targets, shielded targets and reflecting targets are refused in preflight.

### Refusal and provenance

`settled` records per attack and per target: serial, source host, slot, gene,
Core action, mechanic, effect kind, route, `move_id`, target, reaction, lineage,
spend/apply flags and frame. The log is bounded by `caps.provenance` (128) and is
cleared on room leave. The transaction applies each move instance once even when
the active window is polled across many frames.

### Enemy parity

`begin` accepts any valid non-`player` host with an equipped gene. The same
costs, readiness, target policy, refund and provenance apply.

## 5. Integration callback contract (`world`)

The engine calls only these; anything absent is refused, never faked.

| Callback | Purpose |
| --- | --- |
| `get_run()` | the active Core run table (engine mutates this reference) |
| `can_start(run, host, slot)` | free-state gate (e.g. `free_to_cast`) |
| `observe(host)` | `{host,x,y,facing,alive,reflecting,shielding}` for range/occlusion |
| `query(host, spec, ability)` | candidate target view for opponent routes |
| `occluded(from_host, target_view)` | native line-of-sight (optional) |
| `apply_effect(run, request)` | offense/chain/root/counter strike (native hit) |
| `apply_movement(run, request)` | dash/hover (native impulse/flight) |
| `apply_status(run, request)` | mark/root status |
| `apply_guard(run, request)` / `release_guard` | defense contribution + its removal |
| `apply_conversion(run, request)` / `release_conversion` | resource conversion + removal |
| `replace_run(run)` | optional; otherwise the engine rewrites the run table in place |

`request` contains `{host, slot, gene, id, action, spec, move_id, route, native,
target, target_view, host_view}`. `action` is the resolved `Core.activate`
result, so a native adapter maps it to `gd.hit`, `gd.enemy_hurt`,
`gd.impulse`, or an owned-enemy strike exactly like today's `apply_gene`.
Cinder's guard counter selects an opponent, so it releases through
`apply_effect`; self-centered guard stances (`bulwark`, `glacier`, `brand`)
use `apply_guard`.

For the enemy/encounter worker: call `c:preflight`/`c:begin` for a legal request
and consume the `advance()` events + `provenance()` for observation. This is the
optional callback API referenced by the concurrent enemy-behaviors task.

## 6. Native missing seam (honest limitations)

This contract runs on **Core only**. The following are not implemented and are
not claimed:

- There is no native dodgeable startup for cinder/rime today; `main.lua` applies
  them immediately. The startup/active/recovery phases are contract-level. Only
  `gale`/`glacier`/prototype specs carry nonzero startup.
- There is no native attack-range/occlusion collision behind these gates.
  `apply_effect`/`apply_movement` must bind to the existing bounded native calls;
  a missing callback makes the transaction refuse.
- New-family resources/status are action-controller records. Real conversion of
  charge between slots/resources, chain spread, roots and guard absorption need
  either Core support or a native adapter; none is invented here.
- Per-target earning keys Core's `move_id`; whether distinct native hits for one
  animation instance are actually distinguishable requires native evidence.
- `ga.hit` still emits no `on_hit` callback in the current build, so charging is
  driven by the existing event hooks, not by the injected hit returning an event.

## 7. Test evidence

`tools/roguelite/test_gene_actions.py` runs the real `gene_behaviors.lua`,
`core.lua` and `gene_actions.lua` under `lua5.4` with a deterministic fake world.
It registers the unoffered prototype definitions in memory so the real Core
charge/spend APIs drive every family; production admission stays cinder/rime.
Fifteen scenarios assert:

cost/readiness refusal without mutation; spend point and reversible refund;
single application per move instance (repeat multihit); move-id dedup; reaction
lineage never charges; startup window and dodge whiff; occlusion refusal; shield
and reflection refusal; control-route status seam; guard-counter strike seam;
reversible defense and conversion apply/release with no drift; movement route and refund; enemy parity;
Thermal Shock consumes the Rime mark; per-target earning; record/provenance caps;
missing native seam refusal; adversarial behavior data rejection; Core drift
detection.

Command:

```sh
python3 -m unittest tools.roguelite.test_gene_actions -v
```

Result: 2 tests, passing. Full discovery `python3 -m unittest discover -s
tools/roguelite -p 'test_*.py'` ran 116 tests; the 4 errors are pre-existing
environment failures (missing generated `menu/out_effects_study` and room-kit
sidecars, and the `import prepare` path quirk in `test_runtime`), unrelated to
these pure modules.

The fake world proves the transaction contract. It does **not** prove native
collision, hitstop, projectile/reflection resolution, controller feel or balance.

## 8. Integration requirements for the live worker

1. Bundle the two modules lexically in `prepare.py` before `main.lua`
   (`gene_behaviors`, then `gene_actions`, after `core`/`gene_catalogue`).
2. Construct one controller with the real `Core`, `GeneBehaviors`, and a `world`
   adapter that binds the callbacks in section 5 to the current `apply_gene`
   native calls. Only add `admitted` ids that are actually offered.
3. Call `c:advance()` once per unpaused frame after `Core.tick(run, 1)`, and
   `c:on_room_leave()` on room cleanup.
4. Route charge events through `c:on_event` (it preserves Core's reaction
   refusal) and the command preflight through `c:preflight`.
5. Keep `main.lua` as the owner of scene/input/lifecycle; this engine owns only
   the action state machine.
