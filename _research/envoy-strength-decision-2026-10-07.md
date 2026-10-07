# Envoy: what "Build strength" is for, and what the player reads from it (decision, 2026-10-07)

Supersedes: nothing. Builds on `_research/envoy-synergy-analysis-2026-10-05.md` (v2 strength, calibration, the 126-trial CPU-vs-CPU runs in
`_build/audit-20261003/envoy-foes/`) and `_research/envoy-readability-pass1-2026-10-05.md`. Game branch `agent/envoy-feel`, workspace branch `ws/envoy-feel`.

**Status: a DECISION MADE UNDER DELEGATION.** The owner (2026-10-07) handed this one over: "make a decision that makes sense in game feel". It is
written down so Opus or the owner can veto it. Every part is one small change that is easy to revert (the last section says how).

Tags: **[measured today]** is an offline run of the mod's real Lua (the `sim_build.lua` harness of the earlier lanes, copied to the scratchpad with
`mod_graph` and `mod_tuning` added so it computes strength v2, the number the game computes); **[earlier lane]** is quoted from the notes above;
**[read]** is read from source.

## 0. The decision in six lines

1. **Keep the formula** (strength v2) and keep it as the thing opponents are scaled from. Do not retune it blind.
2. **Change what the player sees.** Build strength was shown as `+358%` over an empty build. It is now an index: `x4.58`, three significant figures
   (`x1.19`, `x4.58`, `x87.1`, `x164`), the same `x` the other rows already used. It reads as "how many times stronger the whole build is", not as a damage bonus,
   and it stays readable at New Game+ (it was `+8600%`).
3. **Say when the number cannot see a piece.** A drive with a technique or crit rule (L-cancel, wavedash, perfect shield, tech, a crit chance) now carries
   one line in its detail panel: "Technique: worth more the more you use it. The strength number counts it lightly."
4. **Defence past the engine's floors does not count, and now says so.** It already did not count in the number (the budget clamps at the engine's floors);
   a Damage-you-take row that sits at its floor now reads `x0.15 (limit)`.
5. **Keep the +25% cap** on how far an opponent's build may be ahead of yours (1% per effective depth, capped; bosses x1.15, the last boss x1.3).
6. **The number is a progress meter, not a difficulty meter**, by construction (opponents are rolled from it). It should not be sold as "how hard the next fight is".

## 1. What strength is and where it goes [read]

`mod_budget.lua` `B.build` returns `strength = echo x offence x toughness^.25 x launch^.25 x utility x speed`, floored at 1 (an empty build is exactly 1.0), with v2
(the default, `mod_tuning` `strength=v2`) valuing a record by what the build around it feeds it (`mod_graph`) and a triggered status by its trigger's measured rate x
duration. It has three consumers:

| consumer | what it does with the number | player sees it? |
|---|---|---|
| opponent roll (`foe_roll`, `run_host:roll_wanted`) | target = your strength x `P.factor` = (1 + min(.25, .01 x effective depth)) x role (boss 1.15, last boss 1.3); the roll accepts builds within [.8, 1.2] of the target | no (only with `envoy devui on`) |
| reward and bag detail panels (`run_screen:compare`) | `Build strength a -> b` for the pick, beside the rows that changed | yes |
| the strip (`run_hud`) | `+N%` | only with the developer overlay |

It does **not** steer rewards in the game (there is no "recommended" pick). Only a player reading the panel does.

## 2. Does the number predict difficulty? No, and it should not [measured today, earlier lane]

Opponents are rolled to your strength x about 1.0 to 1.3, so a bigger number never means an easier game and a smaller one never a harder game.
Realised opponent/player strength ratio over 8 seeded Classic runs x 4 loops (`edge.lua`, strength-greedy picker, every stage won):

| loop | opponent / player strength: mean | min | max | rolls above the nominal edge |
|---|---|---|---|---|
| 0 | 1.06 | 0.93 | 1.31 | 0% |
| 1 | 1.19 | 1.08 | 1.61 | 6% |
| 2 | 1.25 | 0.87 | 1.47 | 48% |
| 3 | 1.27 | 1.03 | 1.42 | 55% |

The player's own number, same runs (median, p10 to p90): loop 0 x1.8 (1.1 to 3.4), loop 1 x6.8 (3.2 to 15), loop 2 x36 (15 to 76), loop 3 x169 (83 to 255).
It compounds because the tier curve does (x1.45 per tier past tier 3). So the number is a **progress meter**: it says how far this run has grown. As a
percentage that was `+80%` ... `+16,800%`; as an index it is `x1.8` ... `x169`. Neither tells you how hard the next fight is, and the screens must not imply it.

## 3. The three open questions of the handoff

### 3.1 "CPU-vs-CPU runs never picked technique or crit modifiers by it": true, smaller than it sounded, and not a formula problem

[measured today] 80 runs x 11 stages, the real offers and merge rule: technique/crit affixes are **6.1% of affixes held under a random picker and 4.4% under a
strength-greedy picker**; runs holding at least one: 38% vs 25%. At 22 stages: 6.6% vs 5.0%, 43% vs 28%. So the greedy number steers *away* from them by about a third,
it does not exclude them, and they are rare in the offers to begin with (they are 6% of what rolls).

Why the number undervalues them: a CPU performs a hit-confirmed L-cancel once per 450 s [earlier lane], so a technique trigger counts at the placeholder human rates in
`B.human` (L-cancel .15/s, wavedash .08/s, perfect shield .05/s, tech .05/s, air dodge .05/s, times skill .6). Those rates are guesses; the earlier lane asked for the owner's real counters.
Raising them without data would bake a guess into the opponent scaler. A person who pulls these off often gets more than the number shows; a person who rarely does gets about what it shows.

**Decision: do not change the rates. Tell the player** (item 3 of section 0). If the owner's counters arrive, edit `B.human` and nothing else moves.

### 3.2 "Should defence past the engine's floors count?": it already does not; the screen now says so

[read] `hr_percent_cap` in `pc/gameworld/script_hit_rules_core.h` floors incoming damage at x0.15 and launch at x0.05 (and `hr_cap` floors the per-field `knockback_taken` at x0.1).
`mod_budget.lua` caps the `damage_taken` family at -85% and `launch_taken` at -95%, the same numbers, and the strength formula reads the clamped `potential`. So extra defence
past the floor is worth exactly nothing in the number and nothing in the fight. [earlier lane] by New Game+ 3 a strength-greedy build has `damage_taken` raw -4.04 against a
clamped value of .15: three more floors' worth of defence wasted. What was missing was an explanation: a defence pick at the floor showed "Build strength (no change)".
The row now reads `x0.15 (limit)`, and the modifier text already says "-85% (the most a build can reach)". **Decision: it does not count; it is signalled.**

### 3.3 "Is +25% the right cap on the opponents' edge?": keep it

[earlier lane] 126 CPU-vs-CPU trials, player driven at skill .6: without the cap the opponents out-dealt the player 1.0x / 1.3x / 2.5x / 4.6x at loops 0 / 1 / 2 / 3 and the
player won 40 / 41 / 44 / 26%; with it 0.94x / 1.17x / 2.1x / 3.2x and 38 / 48 / 56 / 44% (n=27 per loop, about +-10%). [measured today] the *realised* edge is the cap on average
(mean 1.25 to 1.27 at loops 2 to 3, table above) with a tail to 1.47 because the roll accepts [.8, 1.2] of the target; a boss adds x1.15. A win rate near half for a skill-.6 proxy through
New Game+ 3 is what "hard but fair" looks like on paper; a person plays better than the proxy, so it will feel easier than 50%, which suits a roguelite's late loops.
The knob is one line (`mod_progression.lua`, `P.opponent_edge_cap`). **Decision: keep .25. Re-judge after the owner has played a loop 2 run** (this is a feel call the proxy cannot make).

## 4. What I looked at and did NOT change (so nobody re-derives it)

* **Echoes** is still over-counted: v2 gives x1.60 for the drive at tier 3 against a measured x1.05 in damage per minute. The earlier lane flagged it as possibly a bug in how the copies land
  on the proxy's target ("Echoes needs a look by the owner"). I did not cap it harder, because if the copies are broken the fix is to the copies, not the number. Open.
* **Smasher's Creed x1.90 (measured x1.31), Skybreaker x1.75 (x1.38)**: still above what the CPU proxy measured. The proxy smashes rarely; a person may not. Since the opponents' builds are valued by the
  same formula, a consistent bias cancels in the matchup and only misleads a player choosing between two picks. Left.
* **Gambler** x1.22 against x1.25 measured, **Sprinter** x1.10 against x1.01: v2 fixed these.
* **The roll band [.8, 1.2]** makes half the late rolls exceed the nominal edge. Tightening it would make fights more uniform and cost roll time (the roller already hits "CAP" fallbacks early); not done.
* Nothing in the combat maths changed. This lane changes text, one number format and some notes.

## 5. Signalling of the lane-made rules (the owner's condition for accepting them)

The rules were accepted "as long as each thing has sufficient signalling". Where each is told, before and after this lane (the UI is English only; the legacy UI is the default, the Atlas
screens are off until `uxatlas on`, so both are covered where they exist):

| rule | told before | told now |
|---|---|---|
| keystones are not removable | a held keystone's detail: "You keep it for the whole run."; the offer said only "Pick one. If you skip, it stays owed." | the run-start panel ends "Keystones are permanent for this run."; an offered keystone: "Permanent: it stays for the whole run. Pick one; ..."; taking one shows a card "Keystone: X / Permanent for this run."; the Atlas explainer says "<family> keystone, permanent this run" |
| a replaced drive is lost when the bag is full | the swap screen says "It is gone for good." (kept); a full-bag pickup card "Bag full: X / Held for the stage end" | additionally, the pickup that FILLS the build says "Bag full: the next drive replaces one." before anything is replaced; the full-bag card now says "Give up a drive at the stage end (n waiting)." |
| rewards every third stage | nothing at a clear that pays none | a card at the next stage start: "No reward this stage / Next one: in 2 stages." (or "The next stage pays one."); a clear skipped because you stood still says why |
| a 30 s ceiling on the drive-collection hold | **this rule no longer exists in the default flow**: the stage-end payout (`payout=true`, `envoy_payout.lua`) has no ceiling ("no ceiling while you play"; the way out is Z + D-pad Down, shown in the banner). The 30 s ceiling and its countdown live only in the older hold (`payout=false`). | the Atlas collect banner now carries the seconds when the older hold counts them ("Collect the drives  22 s"); the legacy draw already did. Nothing to signal in the default flow: there is no clock. **The handoff's list is stale on this point.** |
| changed keystone drawbacks | every keystone shows its "Drawback:" line in the offer, the bag and the run-start panel | unchanged |

## 6. How to veto or revert

* The format only: `drive_text.lua` `fmt` / `T.strength_text` (and the dev strip in `run_hud.lua`). Revert to `('%+d%%'):format(round((v-1)*100))` and the three tests in `envoy_drive_text.lua`, `envoy_run_ux.lua`.
* The technique note: `T.technique_note` and the two `has_technique` lines in `run_screen.lua`.
* The cards: the `show_card` / `next_card` lines in `run_host.lua` (`build_full`, `next_reward_line`, `take_keystone`, run begin).
* The cap: `P.opponent_edge_cap` (unchanged here).
* On-screen look of all of it is OWED to a person with a monitor (`tools/port/envoy_look_tour.sh` opens it).
