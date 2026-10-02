# B2 — Encounter / boss / AI systems audit (read-only)

Lane: B2. Author: read-only audit agent. Date: 2026-09-30.
Scope: `melee/worktrees/linux/pc/scripts/examples/roguelite/` encounter, enemy, gene, boss and
AI Lua; the native technical-assist policy; the script host API in
`pc/platform/gw_script.c` / `pc/gameworld/script_game.c`; the Lua bundler
`tools/roguelite/prepare.py`; gates in `docs/ROGUELITE-COMPLETION-PLAN.md` §11 (Gate 6),
`docs/ENEMY-BEHAVIOR-CONTRACT.md`, `docs/ROGUELITE-ACCEPTANCE.md`.

**No build, no game run, no console (51701) connection was performed.** Nothing was modified,
staged or committed. `enemy_behaviors.lua` does not exist in the tree (see §2.1).

What *was* executed: the headless Lua/Python unit suites, which load Lua source with stubs and
touch no engine code —

```
python3 -m unittest tools.roguelite.test_encounter_runtime tools.roguelite.test_enemy_behaviors \
  tools.roguelite.test_enemy_genes tools.roguelite.test_enemy_catalogue tools.roguelite.test_ai
→ Ran 42 tests in 0.653s — OK
```

Those 42 are decision/logic tests. They prove no native hit, no rendered tell, no AI tech
execution, no boss feel and no playable encounter.

---

## Summary

The project has **two disconnected halves** and the milestone's headline content sits entirely in
the half that never ships.

1. **Live half (in the game).** `runtime_encounters.lua` is a genuinely well-built orchestrator —
   stable entity IDs, transactional spawn with rollback, bounded wave scheduling, a provenance gate,
   observed-stock defeat confirmation, bounded respawn/escape recovery and honest refusal when a
   composition is not representable. `enemy_genes.lua` attaches a Core gene host to each custom
   Adventure actor and drives it with a real charge → fixed 24-frame telegraph → strike cycle.
   `technical_ai.lua`/`technical_ai.inc` give native CPU Fox/Falco a bounded, honest L-cancel and
   ground-tech *shoulder input* assist.

2. **Unshipped half (never reaches the game).** `encounter_behaviors.lua` (1066 lines) and
   `boss_behaviors.lua` (479 lines) are a complete, well-designed, fully-tested pure decision layer:
   six mechanically distinct archetypes, twelve compositions, an observation sanitizer, a
   reaction-delay/vision-box model, a simultaneous-tell arbiter, a table-identity tell binding,
   three three-phase boss machines with distinct positioning demands and vulnerability windows, and
   a versioned boss progress addon with owner-key binding. **They are not in the `prepare.py`
   bundle list** (`tools/roguelite/prepare.py:34` bundles `enemy_genes` and `technical_ai` but not
   these two) and **nothing in the tree references `EncounterBehaviors` or `BossBehaviors`**. The
   behaviour contract itself documents this as pending integration work
   (`docs/ENEMY-BEHAVIOR-CONTRACT.md` §11.1, §12). The acceptance table agrees:
   `docs/ROGUELITE-ACCEPTANCE.md:182` marks `G6-*` as **planned**, and only `G6-ENEMY` (data only)
   as automated-pass.

So the honest state of Gate 6 is: **the encounter/boss *mechanics* content that a player would
actually experience does not exist yet, and the content that does exist is not connected to the
engine.** Everything below is that gap, itemised.

### Headline findings

- **F1 — No reinforcement timing and no activation regions exist at all.** Not partial, absent. The
  only scheduling concept is "wave N is all custom actors that are consecutive; each fighter is its
  own singleton wave" (`runtime_encounters.lua:225-231`). Every wave spawns instantly at
  `begin()`/on wave advance (`runtime_encounters.lua:356-365`, `483`). No delay field exists in
  `encounter_spec` (`encounter_catalogue.lua:19-42`) or in `plan()`. Gate 6 explicitly requires
  reinforcement timing and activation regions (`ROGUELITE-COMPLETION-PLAN.md:260`).
- **F2 — Custom actors have no behaviour differentiation whatsoever in-game.** All custom actors run
  *vanilla Adventure AI* (unmodifiable — see F3) plus one identical gene-attack cycle with a fixed
  24-frame telegraph for every kind (`enemy_genes.lua:69-83`). The `motion`, `ledge`, `fall`,
  `tells`, `buffs` and `counterplay` columns in `enemy_catalogue.lua:16-21` are inert data; the file
  says so itself (`enemy_catalogue.lua:1-4`). A `goomba` and a `redead` in the same wave are
  behaviourally identical apart from which player gene they mirror.
- **F3 — The native host API cannot express any of the requested AI.** The entire custom-actor
  surface registered for scripts is six functions (`gw_script.c:5658-5659`): `spawn_enemy`,
  `enemy_remove`, `enemy_alive`, `enemy_state`, `enemy_strike`, `enemy_hurt`. There is **no**
  movement, target-selection, aggression, patrol, or AI-parameter setter. `enemy_state` is read-only
  (`gw_script.c:5450-5466`). Movement, approach/retreat, ledge policy, tells and vulnerability for
  the non-fighter roster therefore cannot be implemented in Lua at all today — this needs a native
  addition, not a Lua one.
- **F4 — Bosses are HP/stock changes only.** Live bosses are a `champion` fighter CPU with
  `stocks = 2` and a `potency` buff (`runtime_encounters.lua:198-199`, `339`). The code is
  explicit that its `phase` field is *not* a phase: "only the observed stock phase (1-based KOs),
  not the catalogue's authored multi-phase mechanic, which this port does not implement"
  (`runtime_encounters.lua:587-590`). `enemy_catalogue.lua:20` declares `phases = 3` as data only.
  Real phase logic exists — `boss_behaviors.lua:23-79`, three controllers × three phases, each
  changing motion/band/tell/recovery/slots/positioning/vulnerability, advanced forward-only on
  observed `kos`/`hits_taken`/`time`/`player_offstage`/`player_airborne`
  (`boss_behaviors.lua:119-131`) — and is unshipped.
- **F5 — The fighter AI is an honest input assist, not a fighting AI, and it is Fox/Falco-only.**
  `technical_ai.inc:26-32` gates on `Ft_Kind_Fox || Ft_Kind_Falco` **and** `CpuKind_4`. It writes
  exactly two things: `triggers[0] = 0.35f` and `held_buttons[0] |= HSD_PAD_R`
  (`technical_ai.inc:139-140`). It never touches motion, lag, velocity, position or charge. It has
  no spacing, no punishment, no approach/retreat, no shielding, no ledge logic — all of that is
  baseline native `CpuKind_4`. `_research/roguelite-ai-2026-09-30.md` states this plainly: "It does
  not model human perception or provide a complete fighting AI."
- **F6 — No illegal observation found.** This is a genuinely clean result and should be preserved.
  The policy header states "No imported training/20XX code"
  (`technical_ai_policy.h:1-2`); a tree-wide search for 20XX/UnclePunch/TM-CE/SmashBot/Slippi-AI
  finds **zero** matches in code (only the dated audit in `_research/roguelite-ai-2026-09-30.md:12-16`).
  No teleport, no skipped lag, no invented charge: the assist runs *inside* CPU input synthesis
  before LR normalisation (`technical_ai.inc:80-83`) and only adds a button edge;
  `ScriptGame_EnemyStrike` re-validates reach, facing, hitlag and hurt state against real
  collision (`script_game.c:2492-2504`) and cannot hit a shielding fighter
  (`script_game.c:2496`); the unshipped layer sanitises observations against an allowlist and
  counts dropped fields (`encounter_behaviors.lua:48-60`, `227-251`), clears history on LOS loss
  (`encounter_behaviors.lua:305-309`) and requires a reaction-delayed pose
  (`encounter_behaviors.lua:319-329`). The `phase`/`recovery` windows grant *punishability*, not
  invulnerability.

---

## Capability table

| system | status | evidence |
|---|---|---|
| Encounter composition (data) | **Implemented** — 17 encounters, 6 archetypes, 3 themes | `encounter_catalogue.lua:24-42`, `:8-17` |
| Encounter composition (12 authored groups) | **Implemented but unshipped** | `encounter_behaviors.lua:151-194`, absent from `prepare.py:34` |
| Stable actor / entity IDs | **Implemented** — `enemy_<room>_<serial>`, aligned with `route.lua` | `runtime_encounters.lua:26-27`, `:209` |
| Actor admission honesty (refuse, never silently drop) | **Implemented** — unsupported kind/family/slot/budget refused whole | `runtime_encounters.lua:171-181`, `:218-222` |
| Wave scheduling (custom-shared / fighter-singleton) | **Implemented** — limited by the single fighter CPU port | `runtime_encounters.lua:225-231`, `:333` |
| **Reinforcement timing** | **Missing** — no field, no delay, spawns are immediate | `runtime_encounters.lua:356-365`, `:467-489`; no match for `reinforc` in the module |
| **Activation regions** | **Missing** — actors spawn regardless of player position | `runtime_encounters.lua:308-309` (`spawn_point` is a fixed 4-slot cycle, `:235-241`) |
| Gene assignment | **Implemented (partial scope)** — cinder/rime only; families `kinetic`/`sigil`/`fire`/`aegis`/`flux` are catalogue intent | `runtime_encounters.lua:55`, `:179-191`; `enemy_catalogue.lua:8-13` |
| Gene host lifecycle (acquire/equip/buff/release) | **Implemented** — transactional, rollback on refusal | `runtime_encounters.lua:259-300`, `:336-341`, `:642-657` |
| Custom-actor gene charge/tell/recovery cycle | **Implemented** — charge → 24f telegraph → strike → recovery | `enemy_genes.lua:66-83` |
| Custom-actor **movement / attack variety / per-archetype behaviour** | **Missing in-game** — identical cycle for every kind; native vanilla Adventure AI does the movement | `enemy_genes.lua:69-83`; no movement API in `gw_script.c:5658-5659` |
| Custom-actor **vulnerability window control** | **Missing** — no API; `enemy_state.vulnerable` is read-only | `gw_script.c:5463` |
| Defeat provenance gate | **Implemented** — handle→entity map, stale/duplicate rejection, dedup by contact id | `runtime_encounters.lua:524-537` |
| Completion policy | **Implemented (simple)** — clear when every entity in every wave is `progress.defeated` | `runtime_encounters.lua:460-465`, `:467-474`, `:558-561` |
| Completion policy (multi-stage / objectives) | **Missing** — `objectives` exists in progress schema but no encounter uses it | `progress.lua:33`, `runtime_encounters.lua` (no `objective` reference) |
| Escape / vanish recovery | **Implemented** — bounded respawn on the same stable id, then a hard error | `runtime_encounters.lua:430-452`, `:498-508` |
| Checkpoint: encounter state | **Implemented** — `defeated` set + `encounter_kos` per room | `progress.lua:33`, `:88`, `:150-151`; `runtime_encounters.lua:390-398`, `:584-586` |
| Checkpoint: **boss phase / remaining stock** | **Partial** — stock resumes via `encounter_kos`; **phase is not persisted** (the addon that would persist it, `boss_behaviors.lua:275-440`, is unshipped and has zero callers) | `runtime_encounters.lua:390-398`; `boss_behaviors.lua:275-440`; grep for `BossBehaviors` outside its own file → no hits |
| Checkpoint envelope | **Implemented** — versioned, checksummed, length-delimited, preserves unknown future versions | `checkpoint.lua:11`, `:41-43`, `:59-127` |
| Bosses (live) | **Partial** — 3 named champions, 2 stocks, potency buff; **no phase logic** | `encounter_catalogue.lua:39-41`, `runtime_encounters.lua:198-199`, `:339`, `:587-590` |
| Bosses (phase machines) | **Implemented but unshipped** — 3 controllers × 3 phases, forward-only, observable triggers, positioning anchors, vulnerability windows | `boss_behaviors.lua:23-79`, `:100-118`, `:119-131`, `:135-200` |
| Boss reward-duplication guard | **Implemented but unshipped** — owner-key + generation binding, single claim | `boss_behaviors.lua:283-290`, `:330`, `:399-424` |
| Tell / simultaneous-tell arbiter | **Implemented but unshipped** — max concurrent tells + mandatory gap | `encounter_behaviors.lua:335-362`, `:945-971` |
| Observation sanitizer + reaction delay | **Implemented but unshipped** | `encounter_behaviors.lua:48-60`, `:227-251`, `:319-329`, `:571-591` |
| Ledge policy / offstage recovery | **Implemented but unshipped** — `move`/`recover` intents, never a teleport | `encounter_behaviors.lua:738-764`, `:916-929` |
| Measured counters (opp/request/success) | **Implemented** — success only via host `confirm` | `encounter_behaviors.lua:627-634`, `:691-711` |
| **Fighter AI: tech assist** | **Implemented (narrow, honest)** — bounded L-cancel + ground-tech input, 6/4/2f delay, 60/80/95% accept, 8/40f cooldown | `technical_ai_policy.h:16-70`, `technical_ai.inc:83-141`, `technical_ai.lua:4-12` |
| **Fighter AI: coverage** | **Missing** — Fox/Falco CPU only; `CpuKind_4` only | `technical_ai.inc:26-32` |
| **Fighter AI: spacing / punish / approach / retreat / ledge / gene use** | **Missing** — none implemented; baseline native CPU only | `technical_ai.inc:1-3` ("Baseline directions/attacks/recovery remain untouched"); `_research/roguelite-ai-2026-09-30.md:36-45` |
| **Fighter AI: measured completion rates** | **Missing** — counters report *attempts*, explicitly not successes | `technical_ai_policy.h:36`; `_research/roguelite-ai-2026-09-30.md:43-45` ("configured policy probabilities, **not measured success rates**") |
| Room-aware target/recovery guidance for CPU | **Missing** — no bounded navigation guidance implemented | `ROGUELITE-COMPLETION-PLAN.md:266` requires it; no implementation found |
| Illegal observation / 20XX reuse | **None found** — clean | §6 below |

---

## 2. Non-fighter (custom actor) roster

### 2.1 Roster size

**Four** logical enemy kinds exist, of which **two** are custom Adventure actors and **two** are
fighter CPUs (`enemy_catalogue.lua:16-21`):

| kind | host | native spawnable? | in-game use |
|---|---|---|---|
| `goomba` | adventure | yes | custom actor, cinder gene |
| `redead` | adventure | yes | custom actor, rime gene |
| `fighter` | fighter | n/a | singleton CPU wave |
| `champion` | fighter | n/a | 2-stock CPU "boss" |

The native spawn list has **six** names — `goomba, koopa, redead, like_like, octorok, polar_bear`
(`gw_script.c:5380-5382`) — and `runtime_encounters.lua:48-50` accepts all six as `CUSTOM_NATIVE`.
**However `enemy_catalogue.enemies` only defines four kinds**, and `plan()` refuses any kind absent
from the catalogue (`runtime_encounters.lua:171-172`). So **`koopa`, `like_like`, `octorok` and
`polar_bear` are unreachable today** — spawnable natively but not authorable by any encounter.
Four of six native actors are dead content.

Note also: **`enemy_behaviors.lua` does not exist.** The task brief lists it; there is no such file
in the tree (find returns only `boss_behaviors.lua`/`encounter_behaviors.lua`/`technical_ai.lua`).
`test_enemy_behaviors.py` exercises `encounter_behaviors.lua`, not a separate `enemy_behaviors.lua`.

### 2.2 What each custom actor actually does

Identical for every kind — `enemy_genes.lua:50-87` is a single kind-agnostic controller:

- **Spawn**: `gd.spawn_enemy(kind, x, y, {facing=-1})` at a fixed 4-position cycle
  (`runtime_encounters.lua:235-241`). No activation region.
- **Gene host**: acquire + equip a cinder/rime gene, then two authored modifiers —
  `capacity -2`, `potency +1` (`enemy_genes.lua:35-36`). These are the *only* per-actor buffs;
  they are identical for all kinds and all levels. **`level` is not used at all** except to derive
  the TechAI skill tier (`runtime_encounters.lua:243-245`), which applies only to fighter CPUs.
- **Movement**: none. The controller never requests movement; the actor runs the stock Adventure AI
  (`GmZool`/native per-kind AI). Not observable, not steerable, not archityped.
- **Attack**: exactly one — the player's own equipped gene, fired via `gd.enemy_strike`
  (`enemy_genes.lua:72-74`). This is the custom actor's *only* offensive action in the game.
- **Tell**: a **fixed 24-frame telegraph** for every actor, every kind, every phase
  (`enemy_genes.lua:81`: `s.windup_until = r.frame+24`). There is no per-archetype tell length in
  the live path; the per-archetype `tell_frames` (12/14/18/16/20/24 in
  `encounter_behaviors.lua:91-146`) are unshipped.
- **Recovery**: real and correct — `phase='recovery'` after a successful strike, `phase='ready'`
  with a 20-frame retry after a refusal, with charge/mark rollback on refusal so a refused attempt
  costs nothing (`enemy_genes.lua:69-77`).
- **Vulnerability**: none controlled. `enemy_state.vulnerable` is read-only
  (`gw_script.c:5463`); nothing can open a punish window on a custom actor.
- **Fall/escape rules**: **not implemented**; only *detected*. `plan()` copies `def.fall`/`def.ledge`
  onto the entity (`runtime_encounters.lua:212`) and `escaped()` re-spawns anything outside the room
  bounds (`runtime_encounters.lua:454-458`, `:430-452`). A `redead` with `ledge='climb'` and a
  `goomba` with `ledge='turn'` both walk off identically; the per-kind ledge rule is dead data.
  `fall='despawn'` vs `'recover'` changes nothing.

**Demonstration-only actor: yes.** `main.lua:549-558` (the legacy v1 path) spawns exactly one
goomba or redead at the fixed point `(12,2)` in a traversal room, attaches a gene and logs a
message. It has no encounter, no composition, no objective and no role beyond "an enemy exists".
This is a presence demonstration. Worse, `ROGUELITE-COMPLETION-PLAN.md:74` records the live defect:
"A native Adventure enemy disappearing currently unlocks traversal" — an escaped required enemy is
counted as a completed combat objective. `main.lua:1075` clears the room on the *last* enemy handle
disappearing, with no escape check.

---

## 3. Bosses

**Live: 0 real bosses.** **Authored-but-unshipped: 3, each with 3 real phases.**

Live path (`encounter_catalogue.lua:39-41` defines `champ_cinder`, `champ_rime`, `champ_gale`):

- A `champion` entity is a singleton fighter CPU with `stocks = 2` and `champion_potency = 4`
  applied as a gene-host `potency` modifier (`runtime_encounters.lua:198-199`, `:339`, `:350`).
- The only "phase" is the stock counter. The code says so in a comment
  (`runtime_encounters.lua:587-590`): the event's `phase = kos + 1` is "only the observed stock
  phase (1-based KOs), not the catalogue's authored multi-phase mechanic, which this port does not
  implement."
- No recovery window, no positioning demand, no attack selection, no phase transition. HP/potency
  and stock count are the entire difference between a champion and a `fighter`
  (`runtime_encounters.lua:175`, `:198`).
- `enemy_catalogue.lua:20` declares `phases = 3` and `:42` asserts it — this is a **data-only**
  assertion (`enemy_catalogue.lua:1-4` explicitly says the AI and native wrappers are Gate 6 work).
  This is the single clearest case in the codebase of a contract that advertises mechanics no code
  implements.

Unshipped path — this *is* real phase logic, and it is good:

- Three controllers, `warden` / `glacier` / `tempest` (`boss_behaviors.lua:23-79`), each with three
  phases, each phase declaring `motion`, `band`, `tell`, `recovery`, `attack_slots`,
  `attack_choice`, `positioning` and `vulnerability`.
- **Recovery windows are real**: `vulnerability.after_attack` opens a bounded punish window on a
  committed attack; `on_recovery` opens one only after a real committed attack or an aborted tell —
  movement/patrol never opens it (`boss_behaviors.lua:196-208`); `on_whiff` opens one on a confirmed
  miss (`boss_behaviors.lua:206`; `encounter_behaviors.lua:703-707`).
- **Positioning demands are real**: `apply_phase` writes `agent.anchor_x` from the phase's
  `positioning.anchor` (`boss_behaviors.lua:100-118`), and `locomotion` converts a violated anchor
  into an actual leftward/rightward movement request beyond idle patrol
  (`encounter_behaviors.lua:803-809`) — a boss under a left-wall demand requests leftward motion.
- **Phase transitions are forward-only and use observable state only**: `kos`, `hits_taken`, `time`,
  `player_offstage`, `player_airborne` (`boss_behaviors.lua:119-131`), evaluated against delayed poses
  of *currently visible* targets only (`boss_behaviors.lua:157-163`). A phase cannot be skipped or
  reversed; a transition cancels any in-flight tell and releases the arbiter slot
  (`boss_behaviors.lua:170-176`).
- A retired/completed boss is inert (`boss_behaviors.lua:141-147`).

**Gap**: none of this is reachable. `BossBehaviors.attach` is never called; the progress addon
(`boss_behaviors.lua:275-440`) has zero callers, so boss phase/reward state is not persisted and a
reload re-runs the fight from stock 2.

---

## 4. AI

### 4.1 Does the project depend on 20XX? — **No.**

Primary-source evidence:

- `technical_ai_policy.h:1-2`: "Original bounded technical input policy. **No imported
  training/20XX code.** Pure observations -> a shoulder pulse; no action/physics/timer mutation."
- A recursive search of `melee/`, `tools/`, `docs/`, `ports/`, `menu/` for
  `20xx|unclepunch|ssbm|ai_persist|customtech|TM-CE|SmashBot|Slippi-AI` returns **no code matches**.
  The only hits outside `_build/linux` (an unrelated third-party dependency tree) are inside the
  dated audit `_research/roguelite-ai-2026-09-30.md:4-16`, which records commits, release tags and
  license-endpoint findings for 20XX-HACK-PACK, UnclePunch Training Mode, SmashBot (GPL-3.0) and
  Slippi-AI / Phillip II (MIT code, weights terms unestablished) — and concludes "No code copied"
  for each.
- `technical_ai.inc:143-185` is a self-contained deterministic policy regression
  (`ScriptGame_CpuTechnicalTest`) with no external data.

That audit satisfies the plan's requirement to "recheck original source and applicable reuse/model
terms before adopting code or weights" (`ROGUELITE-COMPLETION-PLAN.md:262`) and then correctly
declines adoption. **Decision to keep: remain original-only.** The gate also demands a "short
runnable comparison" of vanilla vs. candidate on identical seeds — *that* is missing (PENDING, needs
a Windows/Linux run).

### 4.2 `technical_ai.lua` — full read (22 lines)

It is a thin lifecycle adapter, not an AI. `configure` (`:4-12`) validates and forwards
`port, skill, seed` to native `gd.cpu_technical`; `clear` (`:13-16`); `status` (`:17-21`). It fails
closed to "native CPU baseline" on any refusal (`:9`, `:18`, `:20`). No combat decisions are
translated into Lua — the header says so (`:2`). That is the correct architectural boundary.

### 4.3 What the native policy actually does

`technical_ai.inc:83-141`, gated by `technical_ai_supported` (`:26-32`): primary entity, Fox or
Falco, CPU-controlled, `CpuKind_4`, no sub-fighter.

- Runs inside CPU input synthesis before LR normalisation/edge timers (`:80-83`).
- **Two** possible outputs, nothing else (`:139-140`): `triggers[0] = 0.35f` (analogue L-cancel
  attempt) or `held_buttons[0] |= HSD_PAD_R` (digital ground-tech attempt).
- L-cancel gate: active aerial attack with the native landing-lag command flag, no actionable
  interrupt, downward velocity, and a real floor found by `mpCheckFloor` ray over at most 12 frames
  (`:111-113`, `:119-133`).
- Tech gate: live `DamageFly*` hitstun only, actionable tumble explicitly excluded, native tech
  lockout respected, tech unlock required (`:116-118`, `:63` in the policy header, `:137`).
- Bounded: 6/4/2-frame decision delay by skill, 60/80/95% acceptance, one attempt per opportunity,
  8/40-frame cooldowns, seeded private xorshift that does not touch game RNG
  (`technical_ai_policy.h:16-70`).
- Fails closed: no floor, out of window, not freshly pressable, hitlag, pause, netplay, rollback,
  replay, actor replaced (`technical_ai.inc:94-107`, `:42-48` in the header).

### 4.4 Adequacy judgement

**Adequate as an honest, bounded technical-input assist. Not adequate for the stated Gate 6 goal.**
It is *not* cheating, and it is *not* a fighting AI. The gap against
`ROGUELITE-COMPLETION-PLAN.md:264-266` is total, and the plan itself says a task is "not complete
because level 9 is selected or an L-cancel input was attempted."

Measurable gaps, with the metric each needs:

| # | gap | current state | measurable target |
|---|---|---|---|
| A1 | **L-cancel *completion* rate** | counters record *attempts*; `_research/roguelite-ai-2026-09-30.md:43-45` states these are "configured policy probabilities, **not measured success rates**" | completed L-cancels / opportunities, per skill, vanilla vs. assist, identical seeds. Native counter must distinguish pulse from real cancel. |
| A2 | **Tech completion rate** | same — `opportunities/techs/misses` are policy bookkeeping (`technical_ai.inc:71-73`) | completed techs / opportunities, missed-tech followups (currently baseline only, per the audit) |
| A3 | **Fighter coverage** | Fox/Falco + `CpuKind_4` only (`technical_ai.inc:26-32`) | assist active for every fighter an encounter can spawn; measure per-character |
| A4 | **Spacing / approach / retreat decisions** | **not implemented**; baseline native only | distance-band distribution and approach/retreat counts vs. vanilla, on the same layout |
| A5 | **Punishment (shield punish, whiff punish)** | **not implemented** | punish attempts and punishes-per-whiff; requires observing opponent recovery, which the current self-only observation has no hook for |
| A6 | **Room-aware navigation / recovery** | **not implemented**; plan explicitly warns "Native AI may assume stock navigation" (`ROGUELITE-COMPLETION-PLAN.md:266`) | ledge deaths and recovery attempts per encounter on custom room collision |
| A7 | **Gene use by AI** | **not implemented** — the fighter gene host's ability is never requested by any AI; the only gene activation in the game is the *player's* (`gene_actions.lua`) | gene activations per encounter and whether the buff changes outcomes |
| A8 | **Opportunity/input/success counters reported separately** | policy counters exist but no comparison harness | the vanilla-vs-candidate report the gate requires (`ROGUELITE-COMPLETION-PLAN.md:264`) |

Note the structural point: A4–A7 are *not* reachable through `technical_ai.inc`'s current shape. It
adds a shoulder pulse to a native CPU that already owns directions, attacks and recovery. To add
spacing or punishment you must either (a) extend the native policy with opponent observation, or
(b) hand directions to the scripted layer — and (b) needs a way to override native CPU input, which
does not exist. That is a design decision for root, and it is the one thing this milestone most
needs settled.

---

## 5. Ranked gaps (effort / impact)

Effort: S ≈ 1–2 days, M ≈ 3–5, L ≈ 1–2 weeks, all excluding native build+run time.
Impact: high / medium / low against Gate 6 exit (`ROGUELITE-COMPLETION-PLAN.md:272`).

### 1. Wire the decision layer into the shipped bundle and the runtime — **L / highest impact**

`encounter_behaviors.lua` + `boss_behaviors.lua` are complete, tested, and absent.
`prepare.py:34` must bundle them after `technical_ai` and before `main.lua`; `main.lua` /
`runtime_campaign.lua` must construct a manager, feed it real observations, execute `move` /
`recover` / `ability` requests and call `manager:confirm`. Without this, *every other item on this
list is unreachable* and Gate 6 delivers zero player-visible content. This is exactly the
integration the behaviour contract's §11 already specifies.

### 2. Add a native custom-actor control surface — **L / highest impact, blocks #1's payoff**

Even bundled, the archetype layer's `move` / `recover` intents have nothing to bind to: the entire
scripted enemy API is six functions (`gw_script.c:5658-5659`), none of which moves an actor.
`Behaviors:ledge_blocked` and the whole ledge/vulnerability story are unreachable for non-fighters.
Needs a native `enemy_control`-style setter (direction/target intent/vulnerability window), scoped
to script ownership like the rest of `gs_enemy_owned`. **This is the true critical path**: item #1
without #2 ships a decision layer that can only attack.

### 3. Boss phase persistence and reward gating — **M / high**

`boss_behaviors.lua:275-440` already implements owner-key + generation binding and single-claim
reward gating. It has zero callers. Persist the addon alongside the checkpoint and gate boss rewards
through `progress_claim_reward`. Directly required by
`ROGUELITE-COMPLETION-PLAN.md:270` and by `ROGUELITE-ACCEPTANCE.md` resume requirements. Cheap
because the hard part is written.

### 4. Fighter AI coverage beyond Fox/Falco — **M / high**

`technical_ai.inc:26-32` excludes every other character. Gate 6 requires "every fighter archetype
actually used by encounter data" (`ROGUELITE-COMPLETION-PLAN.md:266`). Whether this is a
`CpuKind` selection change, a broaden-condition change, or a per-character table is a root design
call; it is bounded.

### 5. Reinforcement timing and activation regions — **M / high**

Currently zero. Add a bounded delay/trigger field to `encounter_spec` and honour it in `plan()` /
`spawn_wave()`. Cheap in Lua once the schema is agreed; explicitly named in
`ROGUELITE-COMPLETION-PLAN.md:260`.

### 6. Measured AI comparison (vanilla vs. assist) — **M / high, but PENDING a human run**

`_research/roguelite-ai-2026-09-30.md:67` says a win-rate gain is "not established by policy tests."
Gate 6 exit requires demonstrated measured improvement (`ROGUELITE-COMPLETION-PLAN.md:272`). Needs
the native build and a seeded A/B harness — **PENDING: requires a build and human/agent play; I
did not run either.**

### 7. Real per-kind custom-actor differentiation — **M / medium, depends on #2**

Today all kinds share one cycle (`enemy_genes.lua:69-83`). At minimum vary tell length and
per-kind stats by `level` (currently unused for custom actors, `runtime_encounters.lua:243-245`), and
honour `def.ledge` / `def.fall` in the recovery path. Real differentiation needs #2.

### 8. Unreachable native actors — **S / medium**

`koopa`, `like_like`, `octorok`, `polar_bear` are spawnable (`gw_script.c:5380-5382`) but absent
from `enemy_catalogue.enemies`, so no encounter can reference them
(`runtime_encounters.lua:171-172`). Four of six native actors are dead content. Adding catalogue rows
would immediately widen the non-fighter roster from 2 to 6.

### 9. Fix the traversal escape-completes-objective defect — **S / high value, small**

`main.lua:1075` clears a room when the last enemy handle disappears, with no escape check — so
walking an enemy offstage completes the objective (`ROGUELITE-COMPLETION-PLAN.md:74`). The v2 path
already handles this correctly via `escaped()` + `recover_actor` (`runtime_encounters.lua:454-458`,
`:430-452`); the legacy path needs the same distinction. Cheap correctness win.

### 10. Per-kind encounter scaling — **S / medium**

`level` only affects fighter TechAI skill (`runtime_encounters.lua:243-245`); custom actors get the
same `potency +1` regardless (`enemy_genes.lua:36`). Difficulty currently comes from composition
count alone, not from stats. Directly serves "difficulty uses decisions and combinations as well as
bounded stats" (`ROGUELITE-COMPLETION-PLAN.md:260`).

---

## 6. Illegal observation audit — **clean**

Checked systematically; no violations found.

| concern | verdict | evidence |
|---|---|---|
| Omniscient input read | **None.** The native overlay runs before LR normalisation and only *adds* a button edge; it never reads the opponent's pad. | `technical_ai.inc:80-83`, `:139-140` |
| Hidden state read | **None.** Observation is allowlisted; unknown fields are dropped and counted. | `encounter_behaviors.lua:48-60`, `:227-251` |
| Stale-memory attack after LOS loss | **Guarded** — LOS failure clears history immediately, and a candidate must be currently visible *and* have a reaction-delayed pose. | `encounter_behaviors.lua:305-309`, `:551-557`, `:319-329` |
| Fail-open callbacks | **Closed** — a configured `visible`/`permission`/`actions` callback must return exactly `true`; `false`, `nil` and thrown errors all fail closed and are surfaced. | `encounter_behaviors.lua:277-282`, `:642-654` |
| Teleport recovery | **None.** Offstage recovery is a `recover` intent (a jump toward centre), never a position write. | `encounter_behaviors.lua:916-929`, `:759-764` |
| Skipped lag | **None.** The assist refuses to act during hitlag (`technical_ai.inc:103-107`); `enemy_strike` re-checks both actors' hitlag. | `script_game.c:2494`, `:2503` |
| Invented charge / invulnerability | **None.** Ability requests copy `reach/damage/action/trigger` from real `Core.ability`; charging stays the host's job via the real event path; vulnerability windows grant punishability, not invulnerability. | `encounter_behaviors.lua:823-832`; `ENEMY-BEHAVIOR-CONTRACT.md:198-205` |
| Strike through guard / off-range / behind | **None** — all re-validated natively against real collision. | `script_game.c:2496-2504` |
| Fabricated defeat | **None.** Defeat requires observed evidence: a handle→entity mapping for custom actors, a monotonically decreasing stock transition for fighters. | `runtime_encounters.lua:540-563`, `:568-604` |
| Reward duplication | **Guarded** (unshipped) — owner key + generation binding, single claim. | `boss_behaviors.lua:330`, `:349`, `:409-424` |
| 20XX / external AI reuse | **None.** | §4.1 |

Two soft observations, not violations:

- `enemy_genes.lua:68` reads the player's live `x/y` every frame to gate a strike. That is the
  same position any melee AI reads; it is gated by `reach`, facing, and a native hit-range recheck
  (`script_game.c:2500-2502`). Acceptable.
- `enemy_genes.lua:62-64` offers an opt-in `poll_player_hits` path that reads
  `enemy_state.last_attacker` to attribute who hit the enemy. It is off unless the host enables it
  and is read-only feedback, so it cannot improve the AI's decisions.

---

## 7. Proposed implementation order for this milestone

**Phase 0 — unblock everything (root decision required, no code)**
Settle *how* custom-actor movement is delivered: native control surface (item #2) or a
direction-override on the existing CPU path. Every phase below depends on this answer. Also settle
how much fighter AI is native (extend `technical_ai.inc`) versus scripted (needs a direction
override) — this is the same underlying question.

**Phase 1 — ship what is already written (items #1 partial, #3)**
1. `prepare.py:34` — bundle `encounter_behaviors` then `boss_behaviors`.
2. `main.lua` / `runtime_campaign.lua` — construct the manager per room; wire `Behaviors.validate`
   and `BossBehaviors.validate` into startup so an invalid catalogue refuses early.
3. Persist the boss progress addon beside the checkpoint (`Checkpoint.encode` already has a
   free-text section list — `checkpoint.lua:34-39`); gate boss rewards via `progress_claim_reward`.
   *Value: real boss phases + reward safety ship this phase even before movement works, because
   phase/positioning logic is pure decision-making.*

**Phase 2 — bind the layer to the engine (item #2)**
4. Native custom-actor control surface, script-owned, no teleport/lag/charge escape hatches.
5. `main.lua` observation adapter implementing `Behaviors.adapter_contract`
   (`encounter_behaviors.lua:35-44`); note `gd.player` has **no** `kos` field
   (`gw_script.c:1195-1216`) — derive it; `attacking` must be derived from `action`, never from
   player input; `guard_hit` has no source and needs one.
6. Execute `move` / `recover` / `ability`; call `manager:confirm(move_id, success)` for real results.
   *After this phase the six archetypes become mechanically distinct in-game.*

**Phase 3 — encounter depth (items #5, #7, #8, #10)**
7. Reinforcement timing + activation regions in `encounter_spec` / `plan()` / `spawn_wave()`.
8. Catalogue rows for `koopa` / `like_like` / `octorok` / `polar_bear` → 6 non-fighter kinds.
9. Per-kind, per-`level` scaling; honour `def.ledge` / `def.fall` in the recovery path.
10. Fix #9 (traversal escape-completes-objective) — small, do it early in this phase.

**Phase 4 — fighter AI (items #4, #6, A4–A8)**
11. Broaden the assist beyond Fox/Falco + `CpuKind_4`; add room-aware guidance.
12. Seeded A/B harness: vanilla vs. assist, identical seeds and layouts, reporting
    opportunity/input/success separately, L-cancel and tech *completion* (not attempts), spacing,
    approach/retreat, punish and gene use.
13. Then, only if Phase 0 chose the scripted route, spacing/punishment/approach on the scripted
    layer.
*Item 12 is where PENDING resolves — it needs a native build and a run. Nothing before it can
claim measured AI improvement.*

**Verification boundary.** Every phase above is verified by the headless Lua/Python suites
(42 currently green) plus native `script_cpu_technical`. Items requiring a build or human play —
the A/B AI comparison, rendered tells, boss feel and counterplay readability — are **PENDING**. I
did not build, launch or play anything.

---

## Appendix — cited primary sources

- `melee/worktrees/linux/pc/scripts/examples/roguelite/`: `runtime_encounters.lua` (730),
  `encounter_behaviors.lua` (1066), `boss_behaviors.lua` (479), `enemy_genes.lua` (90),
  `enemy_catalogue.lua` (54), `encounter_catalogue.lua` (160), `checkpoint.lua` (129),
  `progress.lua`, `main.lua`, `gene_actions.lua`, `technical_ai.lua` (22).
- `melee/worktrees/linux/src/melee/ft/technical_ai_policy.h` (71), `technical_ai.inc` (185),
  included at `src/melee/ft/fighter.c:2153`.
- `melee/worktrees/linux/pc/platform/gw_script.c`: player view `:1195-1216`, enemy names `:5380-5382`,
  enemy script API registration `:5658-5659`, `l_enemy_state` `:5450-5466`,
  `gs_enemy_combat` `:5469-5494`.
- `melee/worktrees/linux/pc/gameworld/script_game.c`: `ScriptGame_EnemyStrike` `:2482-2520`,
  `ScriptGame_EnemyHurt` `:2521-2559`.
- `tools/roguelite/prepare.py:32-54` (bundle list at `:34`);
  `tools/roguelite/test_{ai,encounter_runtime,enemy_behaviors,enemy_genes,enemy_catalogue}.py`.
- `docs/ROGUELITE-COMPLETION-PLAN.md:56,73-74,260-272`; `docs/ENEMY-BEHAVIOR-CONTRACT.md` (whole);
  `docs/ROGUELITE-ACCEPTANCE.md:161,182-183`;
  `_research/roguelite-ai-2026-09-30.md:4-16,36-45,67`.