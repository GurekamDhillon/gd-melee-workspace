# Envoy: do builds come together? Synergy analysis (2026-10-05)

Supersedes: nothing. Builds on `_build/audit-20261003/envoy-foes/PROGRESS.md` (126 CPU-vs-CPU trials, same harness family).
Read-only on the mod: everything below runs on a copy of `melee/pc/scripts/examples/envoy` at the `melee` HEAD commit (`6ff04337c`),
plus two instrumented copies of mine (a counter in `mod_engine.lua` and a `synstat` console command). No repo, engine or build change.

Every claim is tagged **[measured]** (a real game fight, frozen build, fast clock), **[simulated offline]** (the mod's real roll, merge,
bag, keystone and budget Lua run in plain `lua` with a policy making the choices) or **[inferred]** (read from the code or reasoned).
All scripts and result files: `_build/audit-20261003/envoy-synergy/` (`PROGRESS.md` there is the log; `res/` holds every table quoted).

## 0. Answer in five lines

1. **Partly.** Status "webs" connect easily (tempo: momentum, haste, guarded), burn and chill connect when pursued, but the **technique, crit,
   armour and shock archetypes almost never assemble in a 12-stage run** (4%, 4%, 9% when a player chases them; under 5% for a strength-greedy player).
2. **The synergy fires, but the payoffs are too small to feel.** In real fights the trigger chains fire (counts below), yet the damage
   uplift of "both halves" over "the sum of the halves" is inside fight noise for every pair except where a single keystone does all the work
   (Plague Bearer's burn: dealt/taken 1.8 to 4-5 with or without the payoff drives).
3. **"Strength" steers away from builds** and is wrong in measurable ways: Echoes counted x2.20, measured x1.05 in damage; Smasher's Creed x1.90 vs x1.31;
   Skybreaker x1.75 vs x1.38; Gambler x0.94 vs x1.25; Sprinter x0.94 vs x1.01. 32 of 86 records are worth 1.03 or less on their own (strength 1.0 = nothing).
4. **Power growth is the tier curve, not synergy**: the median 25-stage build is 3.5x stronger than the same records at tier 3. "Absurdly strong late" is already there;
   opponents keep pace (win rate 50 to 60%, damage ratio 1.1 to 1.4 at depth 5, 10 and loop 2, 43 fights).
5. **Cheapest levers**: a synergy-aware strength (patch in `res/mod_budget_v2.diff`), three one-line bridges, and a stronger payoff (details in section 6).

## 1. The pool, as the code defines it [inferred from code]

86 records: 38 drive affixes (26 plain + 12 technique/crit records with `min_depth` 4 to 8, weights 40 to 60), 6 uniques, 42 keystones
(26 may be the starting keystone; the other 16 first appear in the depth-5 offer). Keystones come 3 at a time at effective depth 5, 10, 15, ...;
drives hold 1 to 4 affixes by depth band (cap 1 to depth 2, 2 to 5, 3 to 9, 4 after); 4 slots at the start, 6 from depth 10; bag of 4 with auto-merge.

## 2. The interaction graph [inferred from code, enumerated offline]

Method (`static.lua`): each record's trigger, conditions and effects give what it **produces** (status on self or target, element conversion, crit chance or
forced crit, armour event) and what it **reads** (a status, an element tag, a crit or armour event, a crit chance). Edge kinds: feed, enable, amp
(status duration), offset (heal or cleanse pays another record's self-drawback), anti (removes or forbids what another uses), co-trigger.
All 3655 pairs were enumerated (`res/graph_edges.tsv`, 399 edges), plus 200000 sampled triples per pool.

| | pairs | interact (feed or enable) |
|---|---|---|
| all 86 | 3655 | 152 (4.2%): 131 direct + 21 through "any status" readers |
| 38 drive affixes | 703 | 41 (5.8%) |
| 42 keystones | 861 | 28 (3.3%) |

Sampled triples: 88.5% have no edge at all, 10.6% one edge, **0.9% are a connected chain, 0% a triangle**. Other edge kinds: 117 amp (three amplifiers,
Lingering, Pandemic, Everburn, onto about 39 status appliers), 66 offset, 46 anti, 16 co-trigger.

**Connected components.** On feed+enable edges there is one giant component of 65 records, held together by the Haste and "any status" hubs; so
components alone do not name archetypes. The archetypes below are the resource-centred sub-graphs (one resource: Burn, Chill, Shock, Momentum, Haste,
Guarded, Crit, Armour).

**Resources, who makes them, who reads them** (`res/static_report.txt`):

| resource | producers | readers |
|---|---|---|
| Burn on target | kindling, plague_bearer* | pyre, cinder, everburn*, malice (+ opportunist*, feasting) |
| fire element | burning, ember_crown (u), pyromancer* | kindling |
| Chill on target | icebound, deep_freeze* | brittle, shatter (+ opportunist*, feasting) |
| ice element | frosted, winter_heart (u), frozen_oath* | icebound |
| electric element | charged, storm_shell (u) | conductor* |
| Momentum (self) | updraft, rush, hit_and_run*, banked_momentum*, hang_time*, fury*, critical_mass*, reprisal | **crosswind, bastion only** (both on landing) |
| Haste (self) | 14 (ledge, clean_landing, combo_surge, skyfarer*, perpetual_motion*, bloodlust*, ...) | rush, echo_weaver*, trailing (+ still_heart*, which cancels it) |
| Guarded (self) | 12 | **renewal only** |
| crit event | wave_edge, combo_conduit*, keen, ruthless, finishing, gambler*, executioner*, retaliation | critical_flow, critical_mass* (+ brutal needs a chance) |
| armour event | shield_stance, wavedasher*, powershield_oath*, juggernaut* | **retaliation only** |
| **Curse on target** | 6 | **none** (a launch number only) |
| **Shock on target** | conductor*, critical_mass* | **none** beyond the native stun |

(* keystone, u unique.)

**Hubs (too central):** Rush, Still Heart*, Trailing, Echo Weaver* (each fed by 14 haste sources); Renewal (12 guarded sources); Feasting and
Opportunist* (read "any status": 11 and 10 sources); Brutal (8 crit-chance sources); Critical Flow and Critical Mass* (8 crit sources each; Critical Flow
also feeds out 4). A hub payoff is easy to switch on and says nothing about the build.
**Dead ends:** Curse, Shock, Guarded (one reader of twelve), Momentum (stacks are spent by a landing, see section 5).
**Isolated (no feed or enable edge):** 17 equip-only records (Smasher's Creed*, Skybreaker*, Sprinter's Pact*, Skyborne*, Dive Bomber*, Featherfall*,
Bulwark*, Aerialist*, Pandemic*, Echo Oath*, Echoes, Armoured, Heavy, Featherweight, Lingering, Glass Core, Echo Heart) and 4 triggered ones without a
partner (Cleansing, Combo Finish, Mirror Shard, Phase Dash*). Plain stat sticks are fine early ("things we gain early on should be more tame");
the flag is on the late ones that are the loudest keystones.

### Declared table vs derived [simulated offline, `comp_syn.lua`]

`mod_synergy.generate` declares 1700 of 3655 pairs (47%); only 189 carry a status or event reason, the other 1511 are shared-tag overlaps ("damage",
"keystone"). Of my 152 real pairs, 67 are declared mechanically, **64 are declared only by tag overlap** (every Brutal-with-crit-chance pair, Bloodlust to Echo Weaver),
none is missing. **101 declared mechanical pairs are not real**: the table ignores *whose* status (Cleansing cleanses *your* Burn, Kindling burns the *target*;
Feasting reads the *target's* status, not your Haste). It is vocabulary, not a design signal.

## 3. Archetype map (the centrepiece)

Defined by roles (every role must be filled by a held record; alternatives in brackets; * keystone). "Earliest" = first stage a completing set can exist
(`min_depth`, starter keystones, the depth-5 keystone offer). Odds are **[simulated offline]**, 500 runs per policy (400 for the targeted ones),
Classic cycle, real roll/merge/reward rules; "greedy" is the old strength-maximiser, "targeted" a player who weights pieces of that archetype x(1+0.5 per piece, max 4) on top of strength.
"Seen" = share of runs that have been offered a piece by stage 12.

| archetype | roles (applier / payoff) | keystones among pieces | earliest | complete by 12 stages: random / greedy / targeted | by 25 stages | strength cost of targeting (median) |
|---|---|---|---|---|---|---|
| **Burn stacking** | plague_bearer* or kindling+(burning/pyromancer*/ember_crown) / pyre, cinder, everburn* | plague_bearer, pyromancer, everburn (3) | 0 | 10 / 13 / **40%** | 15 / 24 / **60%** | 7.9 vs 9.0 (12), 89 vs 105 (25) |
| **Chill stacking** | deep_freeze* or icebound+(frosted/frozen_oath*/winter_heart) / brittle, shatter | deep_freeze, frozen_oath (2) | 0 | 7 / 8 / **30%** | 11 / 9 / **55%** | 8.0 / 91 |
| **Shock chain** | charged or storm_shell + conductor* | conductor (1) | 5 | 2 / 1 / **9%** | 4 / 2 / **22%** | 8.3 / 96 |
| **Momentum speed** | updraft, rush, reprisal, hit_and_run*, banked_momentum*, hang_time*, fury*, critical_mass* / crosswind or bastion | 5 | 0 | 21 / 43 / **60%** | 27 / 57 / **83%** | 8.0 / 90 |
| **Haste web** | ledge, clean_landing, combo_surge, skyfarer*, perpetual_motion*, bloodlust*, ... / rush, echo_weaver*, trailing | 6 | 0 | 30 / 29 / **72%** | 39 / 37 / **88%** | 7.7 / 85 |
| **Guard and heal** | reprisal, bastion, shelter, tech_guard, parry_master*, hang_time*, ... / renewal | 5 | 0 | 16 / 20 / **45%** | 19 / 23 / **46%** | 8.5 / 96 |
| **Technique crit** | wave_edge or combo_conduit* / critical_flow or critical_mass* | combo_conduit, critical_mass (2) | 5 | 0 / 0 / **4%** | 1 / 4 / **27%** | 8.4 / 90 |
| **Passive crit** | keen, ruthless, finishing, gambler*, executioner* / brutal, critical_flow, critical_mass* | gambler, executioner, critical_mass (3) | 5 | 2 / 6 / **25%** | 5 / 33 / **64%** | 8.0 / 93 |
| **Armour retaliation** | shield_stance, wavedasher*, powershield_oath*, juggernaut* / retaliation | wavedasher, powershield_oath, juggernaut (3) | 8 | 0 / 0 / **4%** | 0 / 5 / **19%** | 8.2 / 98 |

What the map says:

* **Two clusters carry the game**: the tempo web (Momentum, Haste, Guard) completes in 43 to 72% of runs by 12 stages once chased, and 30 to 40% with random picks;
  Burn and Chill are reachable (30 to 40%). These are the archetypes that "come together".
* **Shock, technique crit, armour retaliation are out of reach in 12 stages** and still rare in 25 (19 to 27% even when chased). Why: two-piece sets where one
  piece is a non-starter keystone (offered 3 of 42 per step) or a technique affix (weight 40 to 60, `min_depth` 5 to 8). Share of runs that have even *seen* a given
  non-starter keystone by stage 12: 13 to 16% (29 to 37% by 25); a given technique drive affix: 20 to 30% (45 to 62% by 25); Critical Flow 20%, Retaliation 16%.
  Burn and tempo pieces are seen by 65 to 81% of runs by stage 12. [simulated offline]
* **Which archetypes greedy builds land in** (stage 25): Momentum 57%, Haste web 37%, Passive crit 33% (through Gambler and Executioner, which strength likes), Burn 24%,
  Guard 23%, Chill 9%, Armour 5%, Technique crit 4%, Shock 2%. Adventure mode (22-stage loop) gives the same picture (`res/ad_*.jsonl`).
* **Diversity**: mean Jaccard distance between two final builds is 0.79 to 0.89 for every policy (builds differ by *which* records), but they fall into those 2 to 3 clusters;
  all 86 records are used somewhere. The "identity" is thin, the "variety" is not.
* The cost of chasing an archetype is 8 to 15% of the strength number (above), which is also the number the opponent is scaled from.

## 4. Pick policies [simulated offline, `policies.lua`, `res/agg_pol_cl.txt`]

Policies (all see the real offers, the real merge, a swap when the bag is full): **random**; **greedy** (maximise strength after the gain); **tech(s)** (greedy plus +25% x s per technique/crit record held, s = 0.3, 0.6, 0.9);
**commit(s)** (tech(s) plus x(1+0.3 per synergy edge held), edges in the leading resource counting double, so it commits once two pieces are held); **targeted** (one archetype, section 3).

| policy | stage | strength median | technique/crit records held | pair held | chain held (2+ edges) | archetype complete |
|---|---|---|---|---|---|---|
| random | 12 / 25 | 3.2 / 7.9 | 0.96 / 1.62 | 76% / 86% | 49% / 67% | 64% / 78% |
| greedy | 12 / 25 | 9.0 / 105 | 1.83 / 3.84 | 87% / 97% | 63% / 90% | 77% / 90% |
| tech(.6) | 12 / 25 | 8.7 / 103 | 2.60 / 4.66 | 87% / 97% | 61% / 89% | 77% / 92% |
| commit(.6) | 12 / 25 | 7.9 / 85 | 2.44 / 4.48 | 99% / 100% | 96% / 100% | 95% / 100% |

* **Technique valuing barely changes what is held** (1.83 to 2.60 technique records at 12; the three skill levels differ by 0.3): the supply is the limit, not the valuation.
* Strength is about 4x higher for greedy than for random after 12 stages (9.0 vs 3.2): choices matter hugely for the number; the number is not the build.
* **Reward screens are mostly not choices.** (Per screen; "obvious" = best beats second by 15%; "coin flip" = top two within 5%; "dead" = nothing offered beats what is held; "tension" = the strength-best and the synergy-best offer differ.)
  Drive screens (greedy, n=4500): obvious 29%, **dead 17%**, **coin flip 44%**, tension 17%, two or more offers that connect to the build 9%; 72% of them offer a technique/crit record.
  Keystone screens (n=2500): obvious 48%, dead 1%, coin flip 26%, **tension 48%**, two or more connecting offers 25%. The keystone screen is where a real decision sits.
* **Inventory** (greedy, per 25 stages): 14.1 floor drops + 9 reward picks = 23 drives gained; 6.6 merged automatically, 4.8 equipped, 4.2 bagged, 4.2 swapped for a held drive, 3.4 left behind. The 4-bag with auto-merge holds; the spam is already controlled.
* **Defence past the floor** (greedy at 25 stages): 18% of builds are below the -85% damage-taken floor (13% for random picks); at 12 stages none. Wasted defence is a late, minority problem here. (The earlier lane saw it at loop 3.)
* **Power**: 3.5x of the median 25-stage strength is the tier curve (same records capped at tier 3 give 32 instead of 88). Synergy adds nothing to the number (the budget is additive).

## 5. Fights [measured] (frozen build, fast clock, LAB, Fox vs Marth on Final Destination, 2 stocks, cap 5400 frames)

Setup (`fights.py`, `launch_syn.sh`): P1 is a retail CPU level 9 whose technique is set with `gd.cpu_assist` at the stated skill, P2 either a plain CPU (pair tests) or the run's
rolled opponent (`foe roll`, held cap on, edge cap +25%, skill = .03+.06 x depth capped .9 as the mod's own driver would). Builds are real bags (hand-built depth 10 for pairs, 6 slots, 3 keystone slots, every build validated
by the real bag; or the sim's own bags for archetype builds). My copy counts fired records, events and status frames per port (`synstat`). The fast clock skipped drawing; gameplay is not bit-identical with drawing (engine-lane finding): fine for counts and averages, not for an exact frame claim.
Noise: dealt-per-minute has sd about 25 on a mean of 160 for a no-feature fight (n=21), so **n=4 per cell detects only effects of about +-30%**.

### 5.1 Pairs: does the pair fire, and is the whole more than the sum? (8 pairs x 4 conditions x 4 fights, skill .6; `res/agg_pairs.txt`)

Conditions: both halves (AB), A only, B only, neither (same filler drives). Per fight, P1:

| pair (A feeds B) | trigger/effect counts with both | A alone / B alone | damage uplift, whole vs none | sum of halves | verdict |
|---|---|---|---|---|---|
| Plague Bearer* + Cinder, Pyre | burn applied 35.5, Burn up 76% of the fight | 49.5, 76% / payoffs 0 | **+306 dmg/min** | +298 | the keystone alone does everything; payoffs add 0 (synergy term +8, noise) |
| Burning + Kindling (Cinder held) | Kindling 2.2 fires, Burn up 14% | 0 / 1.8 | -3 | +27 | the enabler is not needed: retail moves already carry fire; the CPU rarely smashes |
| Updraft + Crosswind | Updraft 4.0, Crosswind 2.5, Haste up 13%, **Momentum up 44 frames** | Updraft alone 7.0 fires, Momentum up 932 frames | -6 | +13 | the landing spends every stack at once: Momentum never builds |
| Clean Landing + Rush + Crosswind | L-cancel hit 1.8, **Rush 22.5, Crosswind 8.8, Haste up 30%** | Haste up 5% / 0 | -10 | +42 | whole is 6x the Haste of the parts: a real self-feeding loop (haste -> hits -> momentum -> landing -> haste), but once started it just sits there and did not raise damage |
| Wave + Critical Flow (Keen held) | wavedash 4.2, crits 10.0 vs 5.5 baseline, Haste up 14% | 5.5 wavedash, 9.2 crits / 6.2 crits | +40 | +69 | fires; Haste is not a damage gain for the proxy |
| Shield Stance + Retaliation (Keen held) | perfect shield 1.5, armour absorbs 0.8 | 1.0 / 0 | +14 | -2 | the chain completes less than once a fight |
| Frosted + Icebound (Shatter held) | Icebound 2.0, Chill up 7% | 0 / 0 | +10 | -11 | smash-only conversion, CPU rarely smashes |
| Charged + Conductor* | Conductor 16.2, Shock up 13% | 0 / 9.8 | -3 | -4 | Charged raises Conductor fires 1.7x and Shock uptime 3.4x, still no damage |

**So: synergy fires (every chain produced its events), the mechanical uplift is real in status uptime (Haste 6x, Shock 3.4x) and in event counts, but the damage uplift of the whole over the sum is not distinguishable
from zero for any pair (largest swing -51 dmg/min against sd 25 per fight).** Only a keystone that applies a damage-over-time status moves the fight, and it moves it with or without its payoffs.
Payoffs on paper (+10% Cinder, +8% launch Pyre at tier 1; x1.5 at tier 3) are about +5% of total damage over the fight, below what n=4 can see and below what a player would feel.

Skill sweep (3 fights per cell, `res/pairs_s30_s90.jsonl`): the assist raises wavedashes per fight 1.3 / 4.2 / 6.0 at skill .3 / .6 / .9 (Wave fires follow), but **hit-confirmed L-cancels do not scale** (0, 1.8, 1.0 per fight): at .3 the whole L-cancel chain never starts; at .9 it starts but did not catch (haste up 123 frames). Event rates for the proxy at .6 over all pair fights (4042 engine seconds): hit 0.79/s, landing 0.46/s, perfect shield 0.018/s, wavedash 0.005/s, L-cancel after a hit 0.002/s.
**The CPU proxy performs technique far less often than a person would, so everything about technique triggers here is a lower bound**; the owner's own play counters are the number to use.

### 5.2 Calibration: what a record is worth in real damage vs the strength number (3 fights per cell, skill .6, `res/agg_cal.txt`)

| record alone | strength ratio (with / without) | measured dealt-per-minute ratio |
|---|---|---|
| Echoes (drive) | **x2.20** | **x1.05** |
| Smasher's Creed* | x1.90 | x1.31 |
| Skybreaker* | x1.75 | x1.38 |
| Everburn* (no Burn applier held) | x1.70 | x1.27 (inside noise; its payoff cannot fire) |
| Gambler* | **x0.94** | **x1.25** (19.7 crits per fight) |
| Keen + Brutal | x0.81 | x0.94 (5.3 crits per fight) |
| Sprinter's Pact* | x0.94 | x1.01 |

Each ratio has about +-15% error at n=3. The direction is the finding: Echoes is the single most-held record in greedy builds (79% at 25 stages) and its measured gain is a few percent. **Echoes needs a look by the owner** (its three half-damage copies should add far more than 5% on aerial hits; possibly the copies do not land or register on the proxy's targets).

### 5.3 Archetype builds against the opponents the run rolls (43 fights, 1 per build, skill .6; `res/agg_archfights.txt`)

Per archetype (burn, momentum, haste web, technique crit, guard and heal) and run point (depth 5, depth 10, loop 2 depth 5 = effective 31): the targeted-completed build, a half-built one, and the greedy pile at the same seed.

| type | n | win | damage ratio (P1/P2) | strength (v1) |
|---|---|---|---|---|
| completed | 14 | 0.61 | 1.49 | 4.7 / 11.4 / 113 at the three points |
| partial | 15 | 0.50 | 1.08 | 3.9 / 10.7 / 74 |
| pile | 14 | 0.54 | 1.18 | 4.8 / 12.9 / 131 |

Completed builds are 5 to 25% lower in strength and do **at least as well** as the pile (win .61 vs .54, +-.13), not clearly better. By depth, all builds together: effective 5: win .50, ratio 1.17; 10: win .60, ratio 1.43; 31: win .53, ratio 1.13.
**Opponent scaling holds** (the +25% cap and the held-drives cap keep fights close through loop 2). Caveats: one fight per build; the fire counts of the "completed" builds show the loudest filler (Cleansing, Opportunist, Iron Resolve) firing, **not** the archetype's own pieces: in 13 of 14 completed builds the archetype's pieces account for under half of all fires, and in 6 of them for none or one or two
(for example a "complete" Burn at loop 2 with 0 fires: Kindling needs a fire hit, which needs a smash). Opponents are scaled from the same strength number, so a pile inflated by Echoes also gets a stronger opponent than its real power deserves.

## 6. Proposals, ranked (the owner applies them; I applied none)

**Data supports (small, mechanical):**

1. **Make strength synergy-aware and honest about conditionals** (patch `res/mod_budget_v2.diff`, 92 lines, a copy of HEAD `mod_budget.lua`). Four changes:
   (a) a record that *reads* something (a status on the target, an element tag, a crit or armour event, a crit chance) counts `0.1 + 0.9 x (reads satisfied by the other held records)`: Everburn alone 1.75 -> 1.07, Feasting 1.38 -> 1.04, Reprisal 1.34 -> 1.04, Cinder, Shatter, Kindling, Rush, Crosswind, Conductor to about 1.01 to 1.02; with their partner they count in full;
   (b) a status granted by a trigger counts for `rate x duration` of its trigger (rates measured in 5.1: hit 0.8/s, landing 0.45/s, perfect shield 0.018/s, etc.; technique rates are a placeholder `human` table x skill 0.6 that **needs the owner's real numbers**), not for ever: Parry Master 1.54 -> 1.41, Hang Time 1.32 -> 1.03;
   (c) Echo capped at +0.6 (Echoes 2.2 -> 1.6; **proposal waits on the Echoes check**), speed counts 0.25 per point (Sprinter 1.0 -> 1.09), cleanse weight 0.1 -> 0.03 (Cleansing 1.30 -> 1.09).
   Effect offline (greedy under v2, 300 runs): Burn complete 24 -> 42% and "any archetype" 77 -> 89% at 12 stages (90 -> 99% at 25); it does **not** raise technique picks (1.83 -> 1.56 at 12): technique value needs the player's measured rates.
   This also fixes opponents: they are scaled from the same number.
2. **Raise the payoff so the whole is felt.** Cinder, Pyre, Shatter, Brittle, Malice give about +5% of total damage when the chain is on; a chain that cannot be told from noise is not a build. Measured contrast: the keystone DoT gives +160% damage per minute (490 vs 186). Suggested band for a payoff piece: +20 to 30% on the status's uptime, or a multiplier that only a *completed* chain earns (which the gating in 1 can supply). Taste: how loud.
3. **Plague Bearer and the DoT keystones are the outlier** (dealt per minute x2.6, 490 vs 186; win 100% vs 62%; dealt/taken 1.8 to 4 to 5). If the intention is that the *build* is the synergy rather than one keystone, check its numbers: a cut of its tier damage until the uplift is near Smasher's Creed's measured +31% would do.
4. **Three bridges, one-line each, no new records** (all edits to an existing record's condition or number):
   * **Momentum spends all stacks at a landing** (Crosswind removes Momentum; Updraft alone holds 932 frames, with Crosswind 44): make Crosswind and Bastion spend one stack, so "max 5" matters (edge: Momentum has 8 producers and 2 readers).
   * **Retaliation reads only an armour absorb** (4 producers, fires 0.8 per fight at best): also let it fire from `hit_taken` with `self_status guarded` (12 Guarded producers) so the Guard web connects to the crit web.
   * **Brutal is a dead roll without a crit chance** (8 enablers): give it its own 3% chance, or raise its weight when a chance is held; and **Curse and Shock have no reader** (Curse: 6 producers; Shock: 2): let one existing combo record (Combo Surge) also fire against a Shocked target, and one crit record add chance against a Cursed target, so the status archetypes touch the technique ones.
5. **Hubs**: Rush, Trailing, Echo Weaver, Still Heart (14 haste sources each) and Renewal (12 guarded): the Haste web completes in 72 to 88% of runs once chased and 30 to 39% by accident. Make the payoff scale with stacks or duration (so a long Haste is worth more than a blip) rather than on/off, or raise the cost.

**Needs the owner's taste or data:**

6. **Technique and crit access.** By 12 stages technique crit is 4% (27% by 25), armour retaliation 4% (19%), shock 9% (22%). If those should be reachable in a 12-stage run: lower `min_depth` of Wave, Critical Flow, Keen's partners from 5 to 8 down to about 3 to 4, and/or make one of the three keystone offers connect to a held record (below). **Do not tune further until the owner's own technique rates are known**: the CPU proxy does a hit-confirmed L-cancel once per 450 s.
7. **Offers that connect.** Replacing one of the three offers with a partner of a held piece, when none of the three connects, raises completion for a player who is not chasing (random picks: any archetype 64 -> 72% at 12, 78 -> 87% at 25; Burn 15 -> 21%) but little for the others (greedy +5 points at 12, 0 at 25; targeted +2). Cheap, safe, small; the UI cue ("this fits your Burn") may matter more than the roll.
8. **Reward economy.** 17% of drive screens offer nothing better than the build (dead) and 44% are coin flips; the keystone screens are real choices (tension 48%). Fewer, richer drive screens (the economy already moved that way) or a "skip for X" would match "stop the inventory spam"; the bag flow itself is already tame (3.4 of 23 drives left behind).
9. **Opponent scaling**: keep the +25% edge cap and the held-drive cap (fights stay at 50 to 60% over depth 5 to loop 2). Re-measure after item 1, because opponents are scaled from the number item 1 changes.
10. **Strength is also the reward steering and the foe scaler**: a build that completes an archetype is 5 to 25% lower on paper, which makes its next opponent easier; with item 1 that flips (a complete chain counts more), which will make completing archetypes harder on the opponent's side: intended or not is a taste call.

## 7. What the data can and cannot say

* **A CPU is not a person.** It performs technique at a fraction of a person's rate (L-cancel after a hit 0.002 per second at assist skill .6), uses smashes rarely, and does not play around statuses. So technique, smash and element-conversion pieces are measured as lower bounds; damage numbers are for a retail level 9 Fox, one stage, one opponent character.
* **Small n.** Pairs 4 per cell, calibration 3, archetype builds 1 per build; the detectable effect is about 30%. Absence of a measured uplift means "not larger than about 30% per fight", not "zero".
* **The policies are mine.** Commit, tech and targeted are stand-ins for a person; the diversity and completion numbers depend on how hard they chase. The sim assumes every stage is won (no retries, no deaths), the Classic cycle (11 stages, depth jump at the loop) for the 12 and 25 stage runs, and adventure for a check only.
* **The graph is derived from code, not from play**: it knows triggers, conditions and effects, not how often a condition holds; "interact" does not mean "interacts enough to matter" (section 5 measures that for 8 pairs only).
* **Fast clock, no draw** (`MELEE_TURBO_RENDER=0`); gameplay is not bit-identical with drawing. Fine for these statistics.
* **Strength v2 is a proposal I could only test offline** (and on single-record calibration); its constants (uptime rates, the 0.1 floor, the Echo cap) are chosen from the numbers above, not tuned by play.

## 8. Files

`_build/audit-20261003/envoy-synergy/`: `PROGRESS.md` (log); `static.lua`, `static_report.lua`, `comp_syn.lua`, `triples.lua`, `arch.lua` (static analysis and archetype definitions); `policies.lua`, `pol_run.lua`, `agg_pol.py`, `agg_arch.py`, `agg_v2.py` (policy sim);
`mkbag.lua`, `gen_arch_bags.lua`, `gen_jobs*.py`, `fights.py`, `launch_syn.sh`, `bundle_mine.py`, `mods/` (my instrumented copy of the mod at HEAD, `sy_probe`), `agg_pairs.py`, `agg_cal.py`, `agg_archfights.py` (fights); `mod_budget_v2.lua`; results in `res/`.

Prior tools reused: `_build/audit-20261003/envoy-foes/sim_build.lua` (copied with the module path changed), `efm` probe and `run_trials.py` structure.
