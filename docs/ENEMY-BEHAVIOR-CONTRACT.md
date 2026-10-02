# Enemy and boss behaviour contract (Gate 6)

Authored 2026-09-30 by the bounded Gate 6 enemy/boss controller worker. Scope,
current state and integration limits, not a claim that the game mode is
complete. Native combat, visuals and normal-speed feel remain pending root
validation.

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

**Reaction delay.** Each actor keeps a bounded per-target pose history
(`Behaviors.history = 32`). Decisions aim only at the target pose the actor
could have seen `reaction` frames ago (`Behaviors.delayed_pose`), so a
newly-appeared or newly-airborne target cannot be tracked instantaneously.
Reactive triggers (`target_attack`, `target_airborne`, `guard_hit`) additionally
require the condition to persist for `reaction` frames before firing. Reaction
is bounded to `0..30` frames.

**Vision and occlusion.** A target must be inside the archetype `vision_x` /
`vision_y` box and, where `front_gate` is set, in front of the actor. An optional
injected `visible(agent, target, pose)` predicate enforces occlusion. A hidden
target never produces a tell or ability request.

**Monotonic decision time.** `tick` refuses a frame below the previous frame
(`non-monotonic decision time`). Frames only move forward.

## 3. Decision and legal-request boundary

Each tick returns `true, { requests = {...}, events = {...} }`. Request kinds:

| kind | meaning | host binding |
|---|---|---|
| `move` | `dir` (-1/0/1), `run`, `intent`; a legal locomotion intent | map to a controller D-pad/analog intent; clamp to the actor's real movement |
| `recover` | `dir`, `jump`; off-stage recovery intent toward the room centre | map to a jump/double-jump input; never a teleport |
| `ability` | `host`, `slot`, `target`, `reach`, `damage`, `action`, `move_id` | execute with `Core.activate` + the actor's native strike/input path |

An `ability` request is produced only when **all** hold: the real
`Core.ability(run, host, slot)` is `ready`, the delayed target pose is inside
the ability's `reach` (and the archetype vertical bound), the target is
visible, the reaction gate elapsed and any tell has completed. The request
copies `reach`, `damage`, `action` and `trigger` from Core, so the decision
layer never invents an engine API and never grants charge.

Reading the ability is read-only: `tick` calls `Core.snapshot`-invariant code
only. A test asserts the run serializes identically before and after 80 ticks.
Charging stays the host's responsibility through the real event path.

`move_id` is `"<actor id>:<slot>:<serial>"`, a stable per-actor provenance key.
Repeated contacts do not reuse a key; duplicate confirmations are refused.

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
refuses renamed duplicates and checks the six/ twelve targets, supported Core
`family`/`slot` placements and agreement with the encounter catalogue.

`Behaviors.compositions` has exactly twelve authored actor groups. Each row
carries `kind`, `role`, `archetype`, `family`, `slot`, `level`, `count`, a
`lane` (-3..3) and `height` (0..2). `Behaviors.placement(bounds, lane, height)`
turns that into a deterministic spawn suggestion; the host owns the real
spawn. Compositions are refinements of existing encounter ids
(`scout_pair`, `pincer_pair`, `guard_post`, `shield_wall`, `zoner_wall`,
`skyline_denial`, `aerial_duel`, `recovery_hunt`, `elite_mix`, `elite_twin`,
`swarm_rush`, `bastion_hold`), and validation checks their actor counts match
the catalogue rows.

## 5. Fairness, tells and the arbiter

When an actor is ready on a legal target it first enters a readable **tell** of
`tell_frames` (12-20 for archetypes, 14-28 for bosses), reported as a `tell`
event and visible in `states()`. Only after the tell does the `ability` request
fire; then the actor enters `recovery_frames`, during which it cannot attack.
This gives the player a real startup and recovery window.

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
  `successes` at zero. `tells`, `deferred` and `refused` are tracked separately.

Movement and recovery keep their own `opportunities/requests` sets. No native
tech count (for example a completed L-cancel) is claimed here; the host must
report it. This is intentionally narrower than the plan's AI comparison, which
still requires a Windows/native run.

## 7. Ownership, escape and cleanup

The manager tracks a bounded number of actors (`max_actors`, default 24) by
stable id. `remove(id, reason)` distinguishes `defeated` from `escaped`:
an escaped required actor is **not** a defeat and never unlocks a room.
`release()` tears every owned decision agent down and reports no defeat. Native
handles are opaque and are never primary keys; stable ids are.

Room awareness: `move` intents are clamped to `bounds`, grounded actors stop
before an authored ledge unless their policy is `climb`/`recover`, and an
off-stage actor emits a bounded `recover` intent toward the centre instead of a
teleport.

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
`player_offstage`, `player_airborne`). Phases advance forward only on an observed
condition; a phase that only changed HP would not qualify. Each phase changes
mechanics (movement, spacing, slot choice, timings, vulnerability), not health.

**Vulnerability/recovery.** A committed attack opens a bounded vulnerability
window (`after_attack`) during recovery; a whiff can open one via
`manager:confirm(move_id, false)`. These windows are decisions the host may
honour as punishable state - they do **not** grant invulnerability, skip lag,
teleports or charge.

`BossBehaviors.attach(manager, actor, controller_id)` adds a boss to an
existing encounter-behaviors manager; `BossBehaviors.state` is a read-only view.
`BossBehaviors.resume` restores a saved phase. `BossBehaviors.compositions` maps
`champ_cinder`/`champ_rime`/`champ_gale` to the three controllers with the same
families the encounter catalogue uses.

## 9. Boss progress addon

`progress.lua` is frozen and rejects unknown fields, so partial-boss state is a
**separate, versioned sibling record** - not a new field on the progress table:

```
{ version = 1, bosses = { [room_id] = {
    controller, family, phase, phase_frames, kos, hits, completed, rewarded } } }
```

`progress_new`, `progress_record`, `progress_validate`, `progress_sync`,
`progress_phase`, `progress_reward_eligible`, `progress_claim_reward`,
`progress_encode(Codec)` and `progress_decode(text, Codec)` are provided.
Validation bounds the boss count, controller id, phase range, family, counters
and flags. `progress_claim_reward` refuses a second claim and refuses before the
boss is `completed`, so a reload cannot duplicate a boss reward. `completed` is
only set from an observed defeat, never a timeout or phase change. A test
round-trips the record through the real `codec.lua`.

## 10. Optional gene_actions callback

The concurrent Gate 5 `gene_actions` worker may pass an optional transaction
API as `deps.actions`:

```
deps.actions = {
  available = function(request) return true|false end,  -- veto before submit
  submit    = function(request) return ok, token end,    -- enqueue the transaction
}
```

The callback is explicit and optional. Without it, legal `ability` requests are
returned as before. With it, a veto is surfaced on the request (`refused`) and
counted; a submit is forwarded. Success is still only counted from
`manager:confirm` - the callback is never treated as proof a native hit
happened.

## 11. Integration requirements (root/integration worker)

1. Bundle `encounter_behaviors.lua` then `boss_behaviors.lua` in `prepare.py`
   after `enemy_genes`/`technical_ai` and before `main.lua` (the bundler is
   root-owned; this worker cannot edit it).
2. Provide the observation function from real engine reads (`gd.player`,
   `gd.enemy_state`, room bounds, authored ledges), execute `move`/`recover`
   intents, and execute `ability` requests via `Core.activate` plus the actor's
   native strike (`gd.enemy_strike`/`gd.enemy_hurt`) or fighter input path.
3. Report measured results with `manager:confirm(move_id, success)`.
4. Persist the boss progress addon (checkpoint sidecar or the next checkpoint
   schema) and use `progress_claim_reward` to gate boss rewards.
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
assist interface was read. Native validation remains pending.
