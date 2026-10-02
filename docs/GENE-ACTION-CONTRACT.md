# Gene action contract (Gate 5)

Status: **prototype contract, independent worker output, not integrated and not
offered in shipping gameplay.** Authored 2026-09-30, revised after coordinator
review. It implements Gate 5's action/event contract as two pure Lua modules plus
a real-module test. It does not claim native collision, engine integration,
balance or human play. The live game still runs its own immediate
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
  explicit `opts.admitted` override.

Honest implementation counts (`GeneBehaviors.status()`): 6 families, 12 authored
genes, **2 offered**, **10 prototype pending a Core/native binding**, 6 authored
reactions, **1 modelled** (Thermal Shock). The prototype count is not shipped
content.

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
`height`, `arc`, `occlusion` (`line`/`ignore`), `spend`, `refund`, `reversible`
and `earning` (`per_move`/`per_target`). All are bounded and validated. The only
implemented spend point is `release`; a non-release `spend` is rejected by
`validate()` so an unsupported policy can never be offered. `native` marks the
two genes whose effect Core already drives today.

### Authored synergies (non-recursive)

Six cross-family reactions keyed by the same ids as `gene_catalogue.lua`:
`thermal_shock` (fire+frost, implemented), `plasma_surge` (fire+flux),
`charged_crystals` (frost+sigil), `chain_lightning` (kinetic+sigil),
`aegis_crush` (aegis+kinetic), `flux_bloom` (flux+frost). Thermal Shock is the
first and only one modelled against Core. `validate()` rejects a reaction whose
`input` consumes another reaction's `output`, so the table can never chain
recursively. Reaction lineage is also refused as a charge source.

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
  `world.can_start`, the native and release seams, and the target policy. It
  mutates nothing.
- `c:begin(host, slot, opts)` starts a transaction from a successful preflight
  and returns a read-only record (or `nil, reason`). Charge is **not** spent yet.
- `c:advance()` runs one observation per unpaused logic frame, after
  `Core.tick`. It reacquires the authoritative run for every record. Startup
  elapses, then the spend point fires, then active, then recovery, then settled.
- `c:on_event(event)` forwards a real contact to `Core.on_event` per slot.
  Reaction, reflection and projectile lineage return 0. `per_target` genes key
  the move by target; `per_move` genes keep the original key.
- `c:interrupt(host, slot, reason)`, `c:clear([evidence])` and
  `c:on_room_leave()` release owned reversible state and drop records.

### Clock

The only clock is `run.frame`. `age = run.frame - start_frame` is bounded by
`caps.lifetime` (600). No wall-clock, no hidden timer. A non-integer or negative
age (clock regression) interrupts the transaction.

### Spend point and targeted refund

Default `spend = 'release'`. Charge is committed exactly once, at the
startup->active transition, through the real `Core.activate` call. Consequences:

- Interrupted in startup: nothing was spent; the charge survives.
- Free-state can change after `begin` (hitstun, landing, a menu). The spend point
  re-checks `world.can_start`; if it is false the action is cancelled before
  spending, and a missing seam fails closed.
- Target dodges or is occluded at release: target is re-validated **before**
  spending; the action whiffs and the charge survives.
- Native application refuses (false, nil or a thrown error): the engine applies
  the authored refund policy. With `refund = 'on_refuse'` it refunds **only the
  original gene's own state table** — `charge` is credited back up to the
  capacity read from `Core.resolve` (not a nonexistent `Core.ability` field),
  `ready_at` is restored — plus the mark this action touched. The spend refund is
  conditional on the exact runtime state object's ephemeral spend revision still
  matching the one this action produced: a later activation of that same state (even
  moved to another slot, and even in the same frame with an equal `ready_at`)
  owns the cooldown and its spend is preserved. A refused conditional restore is
  counted as `stats.refund_refused`, never as a successful `stats.refunded`. With
  `refund = 'never'` the charge stays spent and the mark is not rolled back; in
  both cases an owned contribution handle from the failed apply is still
  released. A slot swapped during the callback cannot receive the refund. It
  never snapshots or replaces the whole run.

### Stable identity (equipment/room/loadout changes)

Every phase re-validates the **exact object identity** the action was planned
against: the run table, the gene instance table, the slot state table, the
equipped instance id and the Core action for the placement. A textual run id is
not sufficient (two profiles both expose `run1`). If any changed — a different
gene equipped, the slot cleared, the run instance swapped — the pending action
is **cancelled**, not resolved against the replacement. A total run-instance swap
during an active action also cancels and never spends a gene from the other run.

### Mark mutation ownership seam (Core)

Value comparison alone is insufficient: `nil -> mark -> nil` proves nothing, so a
refund could resurrect a mark another action consumed or an expiry removed. Core
now exposes a bounded, **ephemeral** per-run, per-target mark revision registry
(never serialized; pending actions never resume across a load):

- every mark write in `core.lua` — set (`activate` mark), consume (`activate`
  fire), and expiry (`tick`) — bumps a **per-run monotonic clock** and stores
  that value as the target's revision; the clock is never reused and never
  rewound;
- `Core.mark_revision(run, target)` reads it;
- `Core.restore_mark(run, target, before, expected)` restores only when the
  revision still equals `expected`, the source host still exists (else the save
  validator would reject an orphan mark), the value is not already expired, and
  a revision slot is available; the restore itself bumps the revision so an
  out-of-order second refund is refused. It refuses an untracked mutation when
  the registry is saturated, so a restore can never create an untracked mark.
- `Core.reset_mark_revisions(r)` drops the mark and spend maps but **keeps the
  clock**, so a stale revision captured before a room clear can never become
  valid again; `Core.forget_run(r)` removes the registry at run end, and `finish`
  does too. Weak keys bound lifetime, and `MARK_TARGET_CAP` bounds residency.
- A second ephemeral clock owns **runtime-state spend**: `Core.activate` bumps
  the revision of the exact state object it spends from; `Core.spend_revision(state)`
  reads it; and `Core.restore_spend(state, expected, ready_at, cost, capacity)`
  refunds that exact state only while its revision still matches. Keying on the
  state object (weak keys, bounded to live states) rather than the slot name
  means the same gene instance moved between slots is still owned, while a newer
  spend on that state from any slot/host — including a same-frame equal-value
  ABA — invalidates the old refund. `Core.reset_mark_revisions` deliberately does
  **not** clear spend ownership, so a room clear alone still leaves an ordinary
  in-flight spend refundable; only mark tombstones reset.

**Capacity (`MARK_TARGET_CAP = 256`).** Derived from inspected generation limits:
`topology.lua` rejects a route outside 12..18 rooms, and the encounter actor
budget defaults to 12 live actors, so a whole route can retire up to
`18 * 12 = 216` distinct actor hosts, plus two fighter ports. 256 covers that
with headroom; the engine also resets the registry on room leave once pending
actions are cancelled, keeping the resident set near one room's needs. At
saturation Core never evicts a tombstone: `activate` preflights any mark set or
fire-consume **before** charging, and refuses the whole action (`mark revision
capacity`) with no mutation and no spend. Already-tracked targets remain usable.
The engine mirrors this check in `preflight` for an early refusal.

The engine reads the revision before and after its own `activate`. If the
revision did not move, it owns no mark transaction and never touches marks. If it
did move, a refund calls `restore_mark` with the post-activate revision; any
mark another host wrote during the callback, or an expiry, has advanced the
revision and the restore is refused.

### Target policy (range, facing, occlusion)

For opponent routes the engine selects a target via `world.query`, then applies
its own pure policy: horizontal reach from `Core.ability.reach` (falling back to
the spec range), a vertical band, a facing arc for `arc = 'facing'`, and a
line-of-sight check via `world.occluded` when `occlusion = 'line'`. Self targets,
shielded targets and reflecting targets are refused in preflight. Free-state
(`can_start`) and occlusion are promised behaviour and fail closed when their
seam is absent.

### Earning and provenance

`on_event` charges each equipped slot individually with a slot-scoped dedup key:
`per_move` uses the original `move_id`, `per_target` uses
`move_id .. '@' .. target`. This preserves Core's dedup for other installed genes
and stops a per_target gene from inflating a per_move gene on the same host.
Reaction (`reaction`/non-direct lineage), projectile and reflected provenance
return 0 and cannot self-charge.

`settled` records per attack and per target: serial, source host, slot, gene,
Core action, mechanic, effect kind, route, `move_id`, target, reaction, lineage,
spend/apply flags and frame. The log is bounded by `caps.provenance` (128) and is
cleared on room leave. Each move instance applies once even when the active
window is polled across many frames.

### Enemy parity

`begin` accepts any valid non-`player` host with an equipped gene. The same
costs, readiness, target policy, refund, identity validation and provenance
apply. Simultaneous player and enemy actions share one run; one refusal never
disturbs another action's state.

## 5. Concurrency and ownership contract

This section is the direct answer to the 2026-09-30 review findings.

1. **No whole-run replacement.** The engine never calls `Core.snapshot`/`restore`
   and never swaps the run. `advance` reacquires `world.get_run()` for every
   record and validates by object identity, so a run changed between records —
   or a different profile's `run1` — is caught. `world.replace_run` is not used;
   integration must swap run tables outside the engine if it needs to.
2. **Targeted refunds only, by authored policy.** A refused application refunds
   the original gene's state table and the touched mark (compared as an owned
   token) when `refund = 'on_refuse'`; with `refund = 'never'` nothing is
   restored. Unrelated contact charge, modifiers and intervening ticks survive in
   both cases. Simultaneous actors are independent, and a callback-time slot swap
   cannot gift the replacement. Free-state is re-checked at the spend point, so a
   `can_start` that turns false after `begin` cancels before any hit.
3. **Identity at every phase.** A pending action is cancelled if the run table,
   gene instance, slot state or Core action changed — including a total run
   instance swap. It never spends a replacement gene or another run's gene.
4. **Protected callbacks.** `Core.activate` and every `world.apply_*`/`release_*`
   call is wrapped. Success requires exactly `true`; `false`, `nil` and thrown
   errors are refusals. A refusal refunds and cleans up; it never silently
   succeeds or leaks the charge.
5. **Slot-scoped earning.** Charging keys are computed per slot from the authored
   earning policy, so per_target and per_move genes on the same host do not
   contaminate each other.
6. **Bounded owned contributions.** The release callback name is mapped exactly:
   `guard` -> `release_guard`, `convert`/`siphon` -> `release_conversion`. Before
   spending, the engine requires that seam and checks capacity against
   **settled handles plus pending reservations**, so simultaneous activations
   cannot each reserve the same free slot. Each handle has a real expiry
   (`effect.duration`, capped at `caps.lifetime`). Expired handles are released;
   a refused release is retained and retried up to `caps.contrib_retries` (3),
   then reported as a stuck contribution and kept. Room leave releases every
   owned handle and returns `released, refused`; it never forgets one.
7. **Reentrant cleanup.** If a room cleanup runs inside a native callback, the
   record is already gone when the callback returns; the engine then cancels the
   intent, refunds the owned cost, and releases any handle the callback created.
   No retired handle leaks.

## 6. Integration callback contract (`world`)

The engine calls only these; anything absent is refused, never faked.

| Callback | Purpose |
| --- | --- |
| `get_run()` | the active Core run table (the engine mutates this reference in place) |
| `can_start(run, host, slot)` | free-state gate (required; fail closed) |
| `observe(host)` | `{host,x,y,facing,alive,reflecting,shielding}` for range/occlusion |
| `query(host, spec, ability)` | candidate target view for opponent routes |
| `occluded(from_host, target_view)` | native line-of-sight (required for `line` specs) |
| `apply_effect(run, request)` | offense/chain/root/counter strike (native hit) |
| `apply_movement(run, request)` | dash/hover (native impulse/flight) |
| `apply_status(run, request)` | mark/root status |
| `apply_guard(run, request)` / `release_guard` | defense contribution + its removal |
| `apply_conversion(run, request)` / `release_conversion` | resource conversion + removal |

Each `apply_*` must return exactly `true` (optionally `true, {contrib={...}}`) or
a refusal; a thrown error is treated as a refusal.

Core must provide `mark_revision` and `restore_mark` (added in this pass); the
transaction requires them and fails closed without them. No save/checkpoint
schema changed — the revision registry is ephemeral and deliberately not
persisted, and active transactions do not survive a resume.

`request` contains `{host, slot, gene, id, action, spec, move_id, route, native,
target, target_view, host_view}`. `action` is the resolved `Core.activate`
result, so a native adapter maps it to `gd.hit`, `gd.enemy_hurt`,
`gd.impulse`, or an owned-enemy strike exactly like today's `apply_gene`.
Cinder's guard counter selects an opponent and releases through `apply_effect`;
self-centered guard stances (`bulwark`, `glacier`, `brand`) use `apply_guard`.

For the enemy/encounter worker: call `c:preflight`/`c:begin` for a legal request
and consume the `advance()` events + `provenance()` for observation.

## 7. Native missing seam (honest limitations)

This contract runs on **Core only**. The following are not implemented and are
not claimed:

- There is no native dodgeable startup for cinder/rime today; `main.lua` applies
  them immediately. The startup/active/recovery phases are contract-level. Only
  `gale`/`glacier`/prototype specs carry nonzero startup.
- There is no native attack-range/occlusion collision behind these gates.
  `apply_effect`/`apply_movement` must bind to the existing bounded native calls;
  a missing callback makes the transaction fail closed.
- New-family resources/status are action-controller records. Real conversion of
  charge between slots/resources, chain spread, roots and guard absorption need
  either Core support or a native adapter; none is invented here.
- Per-target earning keys Core's `move_id`; whether distinct native hits for one
  animation instance are actually distinguishable requires native evidence.
- `gd.hit` still emits no `on_hit` callback in the current build, so charging is
  driven by the existing event hooks, not by the injected hit returning an event.

## 8. Test evidence

`tools/roguelite/test_gene_actions.py` runs the real `gene_behaviors.lua`,
`core.lua` and `gene_actions.lua` under `lua5.4` with a deterministic fake world.
It registers the unoffered prototype definitions in memory so the real Core
charge/spend APIs drive every family; production admission stays cinder/rime.
The program covers thirty-six adjacent finding groups with adversarial cases,
including: contract/status counts and rejection of an unsupported `spend` policy;
cost and targeted refund (unrelated modifier/charge preserved, throwing callback,
`replace_run` never called); simultaneous player+enemy actions; equipment swap
cancelling a pending startup; startup/dodge and fail-closed
free-state/occlusion/status seams; mark restoration after a refused Thermal
Shock; slot-scoped earning (per_target vs per_move, reaction/projectile/
reflection); contribution ownership (release seam, expiry, refused-release retry,
stuck reporting, capacity, room-leave with no drift); movement route, enemy
parity, record/provenance/lifetime caps; and the residual-P1 regressions:

- a slot swap inside the native callback refunds the original gene, never the
  replacement;
- target-mark rollback preserves a concurrent foreign mark and restores a
  consumed foreign mark;
- two profiles that both expose `run1`: identity is the run instance, and the
  pending action is cancelled instead of spending the other run's gene;
- contribution capacity counts pending reservations, so simultaneous activations
  cannot both reserve the one free handle;
- room cleanup reentered inside the native callback does not orphan the effect
  handle and leaves no modifier;
- `convert`/`siphon` release through `release_conversion`; a missing or false
  release seam is refused before spending;
- free-state is re-checked at the spend point, so `can_start` turning false after
  `begin` produces no hit and no state change;
- authored `refund = 'never'` keeps the charge spent while `on_refuse` refunds;
- unrelated state (a modifier and a contact charge) written *during* the refused
  callback survives;
- a per-host refusal and a success in one `advance` stay independent;
- siphon conversion executes against the opponent and releases through
  `release_conversion`;
- the exact P1 `nil -> mark -> nil` interleaving: a refused fire must not
  resurrect a mark another host consumed during the callback;
- a callback `Core.tick` past the captured mark's expiry must not restore it;
- a legitimately refused fire restores its consumed, still-live mark exactly
  once, and a stale-revision second restore is refused;
- run identity: a restored run starts revision-free, a stale revision from
  another run instance is refused, and `forget_run` clears the registry;
- capacity: real Core tracks 256 distinct targets; the 257th mark is refused with
  no spend, no cooldown change and no residual mark; a tracked target still works
  and an untracked restore is refused; the engine crosses 64 and the full bound
  through the real action engine, refuses the over-bound mark cleanly, and a
  tracked target keeps working;
- reentrant reset: a room clear inside the callback drops the target map but the
  monotonic clock keeps the pending refund's stale revision invalid, so the old
  mark is never resurrected and fresh actions still work; `reset_mark_revisions`
  invalidation is asserted, not just zeroed;
- source retirement: restoring a mark whose source host was removed returns `nil`
  and leaves a snapshot-valid run, both directly and from a real callback that
  retires the source mid-apply;
- cooldown ownership: the exact default-Cinder repro (a later same-slot
  activation's `ready_at`/charge survive a stale refund), a same-frame equal
  `ready_at` ABA rejected by the spend revision, and a no-spend earn-only
  callback still restoring the original cooldown while preserving earned charge;
- state ownership across slots: a room clear alone still leaves an ordinary
  in-flight spend refundable, and a runtime state moved to another slot and
  re-spent owns its newer cooldown (the stale refund is refused and counted as
  `stats.refund_refused`);
- adversarial behavior data and Core drift.

Command:

```sh
python3 -m unittest tools.roguelite.test_gene_actions -v
```

Result: 2 tests, passing. Full discovery `python3 -m unittest discover -s
tools/roguelite -p 'test_*.py'` runs 116 tests; the 4 errors are pre-existing
environment failures (missing generated `menu/out_effects_study` and room-kit
sidecars, the absent `roguelite_certification/main.lua`, and the `import prepare`
path quirk in `test_runtime`), unrelated to these pure modules.

The fake world proves the transaction contract. It does **not** prove native
collision, hitstop, projectile/reflection resolution, controller feel or balance.

## 9. Integration requirements for the live worker

1. Bundle the two modules lexically in `prepare.py` before `main.lua`
   (`gene_behaviors`, then `gene_actions`, after `core`/`gene_catalogue`).
2. Construct one controller with the real `Core`, `GeneBehaviors`, and a `world`
   adapter that binds the callbacks in section 6 to the current `apply_gene`
   native calls. Only add `admitted` ids that are actually offered. Provide
   `can_start`, `observe`, `query`, `occluded` and the required `release_*` seams.
3. Call `c:advance()` once per unpaused frame after `Core.tick(run, 1)`, and
   `c:on_room_leave()` on room cleanup (handle a non-zero `refused` return).
4. Route charge events through `c:on_event` (it preserves Core's reaction
   refusal) and the command preflight through `c:preflight`.
5. Keep `main.lua` as the owner of scene/input/lifecycle; this engine owns only
   the action state machine.
