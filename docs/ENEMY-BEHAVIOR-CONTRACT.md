# Enemy and boss behaviour contract (Gate 6)

Authored 2026-09-30 by the bounded Gate 6 enemy/boss controller worker, revised
after review. Scope, current state and integration limits, not a claim that the
game mode is complete. Native combat, visuals and normal-speed feel remain
pending root validation.

## 1. What this contract is

Two new pure Lua modules own the decision half of Gate 6:

| module | contents |
|---|---|
| `runtime/encounter_behaviors.lua` | six mechanically distinct enemy **archetypes**, twelve authored **compositions**, the observation -> decision -> legal-request engine, the simultaneous-tell arbiter and measured counters. |
| `runtime/boss_behaviors.lua` | three distinct **boss controller** phase machines and the partial-boss **progress addon** schema. |

`runtime/` means `melee/worktrees/linux/pc/scripts/examples/roguelite/`. The
modules contain no engine calls and no `require`. They do not edit
`core.lua`, the catalogues, `runtime_encounters.lua`, `technical_ai.lua`,
`progress.lua`, `main.lua` or `prepare.py`.

The controller layer is deliberately only half of a fight: it decides and
returns legal requests. The host must execute them through the real engine and
report measured outcomes back. A green test here proves the decision contract,
never a native hit, a rendered tell or a playable encounter.

## 2. Observation boundary

`Behaviors.tick(frame, observations)` accepts one observation per actor keyed by
its stable id. An observation carries only observable state:

```
{
  frame   = <monotonic integer>,
  self    = { id, x, y, vx, vy, facing, grounded, airborne, on_stage, hitlag,
              action, percent, kos, hits_taken, guard_hit, alive, vulnerable },
  targets = { { id, port, kind, x, y, vx, vy, facing, grounded, airborne,
                offstage, hitlag, action, attacking, vulnerable, percent }, ... },
  bounds  = { min_x, max_x, min_y, max_y, center_x, floor_y },
  terrain = { ledges = { { x, side }, ... } },
}
```

`Behaviors.sanitize_obs` copies only those fields. Anything else (raw
`input`, `buttons`, `teleport`, handles as keys, unknown secret fields) is
**dropped and counted**, never consulted. Hidden player input and engine
internals cannot influence a decision by construction, and a test verifies that
adding hidden fields does not change the decision stream.

### 2.1 Explicit host adapter contract

`Behaviors.adapter_contract` names the real meaning of every adapter value. The
host must synthesize them from engine reads:

* `self.kos` - logical encounter losses/KOs attributed to the actor, tracked by
  the host. **`gd.player` has no `kos` field**; the adapter derives it.
* `self.hits_taken` - measured hits the actor actually received. For a custom
  actor this comes from `gd.enemy_state(handle).received`.
* `self.guard_hit` - an observed successful guard/block event.
* `targets[].attacking` - the target's action/hitbox is a real attack, never
  inferred from player input.
* For custom actors, **`gd.enemy_state(handle).received` is damage received and
  `gd.enemy_state(handle).hits` is contacts delivered** - `hits` is not a
  received-hit counter.
* `bounds` y increases **upward**; `Behaviors.placement(bounds, lane, height)`
  therefore places height N **above** the floor.

### 2.2 Observable history, reaction delay and vision

Each actor keeps a bounded per-target pose history (`Behaviors.history = 32`,
`Behaviors.memory = 120` frames), but **only poses the actor can actually see
that frame are stored**. A line-of-sight failure **immediately clears that
target's history**, even if history already existed, and a target that leaves
the observation is forgotten. A candidate must also be **currently observable**
this frame; a delayed pose alone is never enough. Consequences:

* an occluded target cannot be attacked from stale memory - visible through
  frame 10 and occluded since 11, it is never attacked at frame 197;
* if line of sight is lost mid-tell, the advertised tell is cancelled;
* reaction delay starts at first reveal, not at the last frame the target was
  secretly trackable.

Decisions aim only at the delayed visible pose `reaction` frames ago
(`Behaviors.delayed_pose`). Reactive triggers (`target_attack`,
`target_airborne`, `guard_hit`) additionally require the condition to persist
for `reaction` frames. Reaction is bounded to `0..30`. Boss phase inputs
(`player_offstage`, `player_airborne`) use the same delayed, currently-observable
poses, so an occluded offstage target cannot drive a transition.

A target must be inside the archetype `vision_x` / `vision_y` box and, where
`front_gate` is set, in front of the actor. A configured injected
`visible(agent, target, selfpose, frame)` predicate must return **exactly `true`**
to grant visibility; `false`, `nil`, a thrown error or any other value fails
closed and is never an implicit yes (a thrown predicate is surfaced as an event
and a counter). With no predicate configured, visibility follows the explicit
observed-target semantics above.

**Malformed observations.** `Behaviors.sanitize_obs` never raises on malformed
input and never admits an invalid actor. A missing/non-table/non-finite `self`
is refused with a reason; non-table, id-less or non-finite targets are dropped
(and counted); an omitted `targets` is an empty set. A refused observation
produces an `observation_refused` event, clears the currently-observable set and
clears the target history, so a malformed frame can never retain invisible
history or drive a decision.

### 2.3 Monotonic decision time

`tick` refuses a frame below the previous frame (`non-monotonic decision time`).
Frames only move forward.

## 3. Decision and legal-request boundary

Each tick returns `true, { requests = {...}, events = {...} }`. Request kinds:

| kind | meaning | host binding |
|---|---|---|
| `move` | `dir` (-1/0/1), `run`, `intent`, `capability`; a legal horizontal locomotion intent | map to a controller D-pad/analog intent; clamp to the actor's real movement |
| `recover` | `dir`, `jump`, `capability`; off-stage recovery intent toward the room centre | map to a jump/double-jump input; never a teleport |
| `ability` | `host`, `slot`, `target`, `reach`, `damage`, `action`, `move_id`, `generation` | execute with `Core.activate` + the actor's native strike/input path |

`capability` is `grounded` or `aerial`, derived from the actor/phase. Movement is
horizontal only; requests never claim vertical flight the actor does not have.
An `ability` request is produced only when **all** hold: the actor is **eligible**
(`alive ~= false` and `hitlag == 0`), the real `Core.ability(run, host, slot)` is
`ready`, the delayed visible target pose is inside the ability's `reach` (and the
archetype vertical bound), the reaction gate elapsed and any tell has completed.
The request copies `reach`, `damage`, `action` and `trigger` from Core, so the
decision layer never invents an engine API and never grants charge.

Reading the ability is read-only: `tick` calls `Core.snapshot`-invariant code
only. A test asserts the run serializes identically before and after 80 ticks.
Charging stays the host's responsibility through the real event path. Dead or
hit-stunned actors never request; a pending tell is cancelled.

`move_id` is `"<actor id>#<generation>:<slot>:<serial>"`, a stable per-actor
provenance key. **Generation** distinguishes actor incarnations: removing an
actor purges its confirmable requests, so re-adding the same stable id cannot
inherit an old success, and a stale confirmation is refused.

## 4. Archetypes, compositions and distinctness

`Behaviors.archetypes` has exactly six rows; each differs in at least one of
movement policy, vision, reaction, tell/recovery timing, ability-slot choice,
ledge policy and reaction trigger:

| archetype | host | mechanic |
|---|---|---|
| `pressure` | custom | relentless direct advance with a bounded gap leap |
| `guard` | custom | holds a post and counters a committed target or a guarded hit |
| `zone` | custom or fighter | distance-band spacing; punishes approach, retreats when crowded |
| `aerial` | fighter | waits for an airborne/offstage target, then dives |
| `elite` | custom | alternates advance/hold stances across two ability slots |
| `boss` | fighter | phase machine delegated to `boss_behaviors` |

The set spans custom Adventure actors and fighter CPUs. `Behaviors.validate`
refuses renamed duplicates and checks the six/twelve targets, supported Core
`family`/`slot` placements and agreement with the encounter catalogue.

`Behaviors.compositions` has exactly twelve authored actor groups. Each row
carries `kind`, `role`, `archetype`, `family`, `slot`, `level`, `count`, a
`lane` (-3..3) and `height` (0..2). `Behaviors.placement(bounds, lane, height)`
turns that into a deterministic spawn suggestion **above** the floor; the host
owns the real spawn. Compositions are refinements of existing encounter ids
(`scout_pair`, `pincer_pair`, `guard_post`, `shield_wall`, `zoner_wall`,
`skyline_denial`, `aerial_duel`, `recovery_hunt`, `elite_mix`, `elite_twin`,
`swarm_rush`, `bastion_hold`), and validation checks their actor counts match
the catalogue rows.

## 5. Fairness, tells and the arbiter

When an actor is ready on a legal target it first enters a readable **tell** of
`tell_frames` (12-20 for archetypes, 14-28 for bosses), reported as a `tell`
event and visible in `states()`. Only after the tell does the `ability` request
fire; then the actor enters `recovery_frames`, during which it cannot attack.

**Tell retention.** The tell advertises an exact target, slot, move instance,
**owned run table**, **gene table**, **host-slot state table** and **original
action**, and releases only against those same object identities. Core reuses
textual ids (`run1`, `r4`) per run, so id/key comparison is insufficient; the
manager compares Lua table identity. At release the actor uses the advertised
target/slot/gene/action; if any identity changed - the target gone or out of
reach, the slot unequipped, the gene table replaced (even under the same id),
the run table swapped or reconstructed from a snapshot, the host slot state
reinitialised, the action/family changed, or the actor died - the tell is
**cancelled** and may retell on a later decision, without spending anything and
without emitting a stale advertised ability request. The actor's bound world
references (run, gene, state) are captured at startup and only compared at the
identity check.

`Behaviors` owns one arbiter per room. With `max_simultaneous_tells = 1` and
`tell_gap`, at most one tell is active and a minimum gap separates tells, so no
two overlapping tells can leave the player without a response window. A test
verifies no frame has two tells and that consecutive tells are spaced.

## 6. Counters: measured, never claimed

Counters are separated and only incremented from observed events:

* `opportunities` - rising-edge frames where a legal ability condition held;
* `requests` - ability requests actually emitted;
* `successes` - **only** incremented by `manager:confirm(move_id, true)` when the
  host reports a real result. A request that is never confirmed leaves
  `successes` at zero.
* `tells`, `deferred`, `refused`, `denied`, `failed`, `ineligible`, `surfaced`
  are tracked separately.

Movement and recovery keep their own `opportunities/requests` sets. No native
tech count (for example a completed L-cancel) is claimed here; the host must
report it. This is intentionally narrower than the plan's AI comparison, which
still requires a Windows/native run.

## 7. Ownership, eligibility, escape and cleanup

The manager tracks a bounded number of actors (`max_actors`, default 24) by
stable id and generation. `remove(id, reason)` distinguishes `defeated` from
`escaped`: an escaped required actor is **not** a defeat and never unlocks a
room. `release()` tears every owned decision agent down and reports no defeat.
Native handles are opaque and are never primary keys; stable ids are.

Room awareness: `move` intents are clamped to `bounds`, grounded actors stop
before an authored ledge unless their policy is `climb`/`recover`, and an
off-stage actor emits a bounded `recover` intent toward the centre instead of a
teleport. Boss phase `positioning` anchors drive real combat movement (a boss at
`x=50` under a left-wall demand requests a leftward move), not only idle patrol.

## 8. Boss controllers

`BossBehaviors.controllers` has exactly three phase machines, each three phases
and a distinct signature:

| controller | family | phases | positioning demand |
|---|---|---|---|
| `warden` | cinder | measure -> advance -> overdrive | midlane, then a diagonal escape lane, then off the left wall |
| `glacier` | rime | bulwark -> shatter -> undertow | bait the counter, outrun the mark chain, hold the right platform |
| `tempest` | rime | circle -> dive -> grounded | do not idle airborne, stay off the centre line, pounce on the long landing |

Each phase declares `motion`, `band`, `tell`, `recovery`, `attack_slots`,
`attack_choice`, `positioning` and `vulnerability`, and an `advance` condition
expressed only in observable state (`kos`, `hits_taken`, `time`,
`player_offstage`, `player_airborne`). A phase is entered only when its observed
condition holds; phases never move backward. Each phase changes mechanics
(movement, spacing, slot choice, timings, vulnerability), not health.

**Vulnerability/recovery.** A committed attack opens a bounded vulnerability
window (`after_attack`) during recovery. `on_recovery` opens a window after a
**real committed attack** (an `ability` request, with the explicit attack phases
startup -> active -> recovery) or an aborted tell; movement and patrol are never
recovery and never open a window, and an uncharged boss that only moves stays
invulnerable. The window is bounded and expires. A whiff can open one via
`manager:confirm(move_id, false)`. These windows are decisions the host may
honour as punishable state - they do **not** grant invulnerability, skip lag,
teleports or charge.

**Lifecycle.** A completed/retired boss is **inert**: it emits a single
`retired` event and never requests, moves or attacks. `BossBehaviors.attach`
adds a boss to an existing encounter-behaviors manager; `BossBehaviors.state` is
a read-only view. `BossBehaviors.defeat(manager, state, room, id, frame, ctx)`
is the real defeat-to-completion lifecycle: it records `completed`, syncs the
addon and then releases the agent. No caller sets `completed` manually.

**Resume.** `BossBehaviors.resume(manager, actor, controller_id, entry)` refuses
a record whose controller does not match (`glacier` can never be adopted as
`warden`) and restores the saved `phase`, elapsed `phase_frames` and
`completed`/`rewarded` flags. `BossBehaviors.compositions` maps
`champ_cinder`/`champ_rime`/`champ_gale` to the three controllers with the same
families the encounter catalogue uses.

## 9. Boss progress addon

`progress.lua` is frozen and rejects unknown fields, so partial-boss state is a
**separate, versioned sibling record** - not a new field on the progress table:

```
{ version = 1, owner = <stable owner key>, run_id = <textual run id>,
  generation = <checkpoint generation>,
  bosses = { [room_id] = {
    controller, family, phase, phase_frames, kos, hits, completed, rewarded } } }
```

`BossBehaviors.owner_key(profile_id, run_id)` builds the stable owner key
`profile_id .. '/' .. run_id` from Core's stable profile-owner lineage and run
instance. This is authoritative: two profiles that both contain a run whose
textual id is `run1` have distinct owner keys, so one profile can never accept
the other's rewarded flags.

`progress_new(owner, run_id, generation)`, `progress_record`,
`progress_validate`, `progress_validate_entry`, `progress_bind`, `progress_sync`,
`progress_phase`, `progress_reward_eligible`, `progress_claim_reward`,
`progress_encode(Codec)` and `progress_decode(text, Codec)` are provided.
Validation bounds the boss count, controller id, phase range, family, counters
and flags.

**Binding.** The record is bound to the stable owner key and checkpoint
generation. `progress_sync`/`progress_claim_reward`/`progress_reward_eligible`
accept a `ctx = {owner, run_id, generation}` and refuse a mismatch (`owner`
mismatch is refused first), so a loose sidecar can never grant a reward to the
wrong profile lineage/run/checkpoint. `progress_claim_reward` refuses a second
claim and refuses before the boss is `completed`. `completed` is only set from an
observed defeat, never a timeout or phase change. `progress_sync` stores the
**latest measured** `kos`/`hits`, not the counters captured at the last phase
transition. A test round-trips the record through the real `codec.lua`.

## 10. Optional gene_actions callback and failure surfacing

The concurrent Gate 5 `gene_actions` worker may pass an optional transaction API
as `deps.actions`:

```
deps.actions = {
  available = function(request) return true|false end,  -- veto before submit
  submit    = function(request) return ok, token end,    -- enqueue the transaction
}
```

An optional `deps.permission(agent, request)` may also veto an action.
Callbacks are explicit and optional. The protocol is exact-true: a configured
callback must return exactly `true` to permit/accept; `false`, `nil` or a thrown
error is a denial/failure. Without them, legal `ability` requests are returned as
before. With them:

* a denial/veto surfaces on the request (`refused`) and is counted; no pending
  entry is stored;
* a failed submit (including a `nil` return) surfaces on the request (`failed`)
  and is counted; no pending entry is stored;
* a thrown callback fails closed and is surfaced;
* success is still only counted from `manager:confirm` - a callback is never
  treated as proof a native hit happened.

A refused or failed request therefore leaves nothing actionable behind.

## 11. Integration requirements (root/integration worker)

1. Bundle `encounter_behaviors.lua` then `boss_behaviors.lua` in `prepare.py`
   after `enemy_genes`/`technical_ai` and before `main.lua` (the bundler is
   root-owned; this worker cannot edit it).
2. Provide the observation function from real engine reads (`gd.player`,
   `gd.enemy_state`, room bounds, authored ledges) following
   `Behaviors.adapter_contract`; execute `move`/`recover` intents, and execute
   `ability` requests via `Core.activate` plus the actor's native strike
   (`gd.enemy_strike`/`gd.enemy_hurt`) or fighter input path.
3. Report measured results with `manager:confirm(move_id, success)`.
4. Persist the boss progress addon next to the checkpoint, bound to the stable
   owner key (`BossBehaviors.owner_key(profile.id, run.id)`) and the checkpoint
   generation; gate boss rewards through `progress_claim_reward`; drive
   `BossBehaviors.defeat` on an observed defeat.
5. Drive `tick` from the paused-safe gameplay update with real monotonic frames.

## 12. Frozen files and unavailable evidence

Owned, new, frozen for this task:

* `runtime/encounter_behaviors.lua`
* `runtime/boss_behaviors.lua`
* `tools/roguelite/test_enemy_behaviors.py`
* `docs/ENEMY-BEHAVIOR-CONTRACT.md`

Not edited: `main.lua`, `prepare.py`, `core.lua`, `runtime_encounters.lua`,
`technical_ai.lua`, `progress.lua`, `checkpoint.lua`, all catalogues and all
other tests. No commits, staging, builds, installs or game runs.

Evidence is the headless Lua suite (`test_enemy_behaviors.py`, engine stubs)
against the real Core/catalogues/Codec. **Unavailable here:** native enemy
combat, rendered tells, the Windows/Linux game, controller play, AI
tech-execution counts, human readability and boss feel. No 20XX/UnclePunch or
other external system is reused or claimed; only the existing native technical
assist interface was read. Native validation remains pending, and the runtime
native wiring to `main.lua`/`prepare.py` is still pending.
