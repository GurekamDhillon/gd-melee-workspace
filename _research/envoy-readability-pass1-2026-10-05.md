# Envoy readability, pass 1 (game design): inventory and proposal

Date: 2026-10-05. Status: proposal for the owner's approval; nothing in `melee/` or any mod file was changed, no game was run, nothing was built.
Supersedes: nothing. Builds on `_research/envoy-synergy-analysis-2026-10-05.md` (graph, archetypes, strength) and `_research/envoy-netplay-scoping-2026-10-05.md` (native evaluator).
Pass 2 (the looks) is another lane's; section 4g and section 4h hand it a bounded list.

Labels used throughout: **[OWNER]** his words, **[MEASURED]** computed from the mod's own source, its real roller or the recorded logs, **[JUDGEMENT]** mine.
Scripts and every output file: `_build/audit-20261003/envoy-pass1/` (`inventory.lua`, `sim_items.lua`, `sim_runs.lua`, `sim_power.lua`, `proposal.lua`, `log_counts.py`, `build_doc.py`; JSON and CSV beside them). All run with plain `lua` / `python` from the workspace root.

---

## 0. One-page summary

**[OWNER]** "too much visual stuff happening all at once, and its hard to correlate whats what ... SEPARATE out drives and keystones into further smaller pieces, with easier bite sized rules to be able to understand mostly at a glance." Earlier: "not everything needs a suffix, prefix, modifer, this, and that, all at once. The things we gain early on should be more tame"; "stop inventory spam/bloat".

**The problem in numbers [MEASURED]**

| what | today |
|---|---|
| pieces in the pool | 86 (38 ordinary drive rules, 42 keystones, 6 uniques) |
| pieces that fit a bite-size rule (one trigger, one condition, one effect, at most one status read and one given, at most 14 words, no drawback on ordinary drives) | ordinary 23/38, keystones 20/42, uniques 5/6 (total 48/86) |
| a rare reward drive | 4.2 rules, 19 "things to hold in mind", 50 words, 6 lines (up to 5 rules for a white one) |
| the owner's recorded crit build (depth 30, loop 2; assembled with the dev `grant` command, so a ceiling build) | 6 drives, 22 rule lines, 6 keystones, 55 lines and 509 words to read, 7 statuses, 6 trigger kinds |
| of those 22 drive rules, how many do anything | **11**: the same rule on several drives does not stack (`drive_bag.lua` `derive` keeps the highest tier), so the other 11 are text only. "Critical Flow" is on 5 of the 6 drives. (In typical greedy play duplicates are rare: 0.5 per build; the waste is real but it is the ceiling case.) |
| keystone allowance | 1 + effective depth / 5, no ceiling: 3 at depth 10, 6 at depth 26, 12 at depth 56 |
| keystones that pay their price with a status on yourself (Chill, Curse, Burn: the same looks that mean "the enemy has this") | 13 of 42 |
| a typical player-assembled build at effective depth 30 to 40 (greedy picker, real reward economy) | 6 drives, 8 rule instances, 7.4 keystones, 14.9 distinct rules, 6.3 statuses, 3.9 rules that fire per hit, 258 words |
| announcements | 3 toasts queued in one frame at depth 5 and again at depth 10 (slot, keystone allowance, tier: 18 s on screen); 4 "<archetype> assembled" toasts within 9 to 13 s in both granted-build logs (24 s of queue); a "Modifier!" flash on every rule fire (not counted in any log) |
| pieces that do nothing without a partner | 23 of 86 (17 of 38 ordinary) |

**The recommendation [JUDGEMENT]**: keep the drive models and the whole structure (colour base, prefix and suffix, keystones, uniques, merging) but make every piece one bite: a drive carries at most two rules (one below effective depth 5), a keystone is one rule line and one drawback line taken from a fixed price list (no keystone pays with a status on yourself), the pool goes from 86 to 72 pieces (the 12 least distinct keystones and the two ordinary pieces that carry drawbacks are cut), statuses shrink to five everyone learns (Burn, Chill, Haste, Guarded, Marked) plus a Momentum counter and a private Shock, and assembly stops being an event (no "assembled" toast; the build is understood from a one-line theme count). Result [MEASURED, offline]: ordinary 36/36, keystones 29/30, uniques 6/6 (total 71/72) pass the bite rule; a rare drive drops from 50 words to 17; the typical build at depth 30 to 40 from 258 words to 150, from 6.3 to 4.5 statuses, from 7.4 to 5.0 keystones; the drive changes alone move median build strength by at most 8% (the keystone allowance schedule is what moves late power, section 5).

**Decisions only the owner can make** (details and my suggested answers in section 6.2): (1) at most two rules per drive? (2) cut the keystone pool to 30 as listed? (3) slow the keystone allowance after the fourth (one per New Game+ lap)? (4) the seven-item price list and no status as a price? (5) no "assembled" toasts, no in-match link flash? (6) a duplicate of an equipped rule merges into it (colour no longer required) instead of being dead? (7) Kindling and Icebound apply on any hit? (8) payoffs open at depth 5? (9) Curse is renamed Marked? (10) Momentum becomes a counter (orbs), not a status look? (11) what happens to saved runs that hold a cut piece?

---

## 1. The inventory (generated)

Source: the real mod modules loaded read-only by `load.lua` (the way `melee/pc/tests/envoy_testlib.lua` loads them); `inventory.lua` writes `pieces.json`, `pieces.csv` (one row per piece, every field below), `statuses.json`, `archetypes.json`, `inventory_summary.txt`. **The full per-piece tables (id, name, slot, from depth, when, if, then, numbers per tier, drawback, statuses, score, words, and the rule text exactly as the player reads it) are Appendix A1 to A3 at the end of this document**; this section holds the counts and the other inventories.

### 1.1 Counts by slot and family [MEASURED]

| slot kind | count |
|---|---|
| prefix (standing rule, trigger `equip`) | 16 |
| suffix (a trigger: something happens) | 22 |
| unique (a whole drive with a fixed rule and cost) | 6 |
| keystone | 42 |
| **total** | 86 |

Keystones by drive colour (`keystones.lua`): red Damage 7, green Speed 8, blue Defence 7, yellow Air 6, purple Status 6, white Wild 8. Triggers across all 86 pieces: `equip` 38, `hit_dealt` 12, `interval` 5, `perfect_shield` 4, `landing` 3, `ko_dealt` 2, `status_applied` 2, `ledge_grab` 2, `clank` 2, `hit_taken` 2, `wavedash` 2, `lcancel_hit` 2, `crit` 2, `combo` 2, `jump` 1, `air_jump` 1, `air_dodge` 1, `tech` 1, `combo_end` 1, `armor` 1.
`from depth` is `min_depth`: only the 12 technique and crit drive pieces have one today (4 to 8); every other piece can roll at stage 1.

| budget family (a piece can declare several) | ordinary | unique | keystone |
|---|---|---|---|
| air_jumps | 0 | 0 | 1 |
| armor | 1 | 0 | 3 |
| clank | 0 | 1 | 0 |
| cleanse | 3 | 0 | 3 |
| conversion | 3 | 3 | 3 |
| crit | 6 | 0 | 3 |
| damage_dealt | 2 | 3 | 8 |
| damage_taken | 5 | 3 | 13 |
| echo | 2 | 1 | 2 |
| fall | 0 | 0 | 1 |
| intangible | 0 | 0 | 1 |
| jump | 1 | 0 | 3 |
| launch_dealt | 2 | 0 | 2 |
| launch_taken | 8 | 0 | 22 |
| momentum | 5 | 0 | 6 |
| restrict | 0 | 0 | 2 |
| speed | 8 | 1 | 20 |
| status_duration | 1 | 0 | 2 |
| sustain | 5 | 0 | 12 |
| weight | 0 | 0 | 1 |

### 1.2 Statuses [MEASURED from the records; effect column from `mod_status.lua`]

| status | what it does | applied by (n; * = keystone; @ who gets it) | of those, a PRICE on yourself | read by (n) | removed by | pieces touching it |
|---|---|---|---|---|---|---|
| burn | damage over time on the target (tier damage per second; stacks to 3 for Plague Bearer) | 3 (kindling@target, plague_bearer@self*, plague_bearer@target*) | plague_bearer | 4 (pyre, cinder, malice, everburn) | cleansing | 7 |
| shock | the target's next hit taken has extra hitstun (native) | 3 (critical_mass@target*, conductor@chain*, conductor@target*) | - | 2 (combo_surge, combo_finish) | - | 4 |
| chill | -20% run and air speed | 8 (icebound@target, retribution@self*, parry_master@self*, deep_freeze@self*, deep_freeze@target*, finishers_mark@self*, powershield_oath@self*, combo_conduit@self*) | retribution, parry_master, deep_freeze, finishers_mark, powershield_oath, combo_conduit | 2 (brittle, shatter) | cleansing | 10 |
| curse | target's later hits-taken launch farther by the stored bonus | 12 (brittle@target, malice@target, bloodlust@self*, hit_and_run@self*, banked_momentum@self*, retribution@target*, hang_time@self*, opportunist@target*, deep_freeze@target*, finishers_mark@target*, desperado@self*, critical_mass@self*) | bloodlust, hit_and_run, banked_momentum, hang_time, desperado, critical_mass | 2 (combo_conduit, combo_finish) | cleansing | 15 |
| haste | +20% run and air speed | 14 (crosswind@self, ledge@self, bloodlust@self*, last_stand@self*, hit_and_run@self*, perpetual_motion@self*, skyfarer@self*, clash_king@self*, desperado@self*, fury@self*, clean_lander@self*, clean_landing@self, combo_surge@self, critical_flow@self) | - | 4 (still_heart, rush, echo_weaver, trailing) | still_heart | 18 |
| guarded | -25% damage taken and -15% launch taken | 12 (reprisal@self, still_heart@self*, bastion@self, shelter@self, last_stand@self*, iron_resolve@self*, parry_master@self*, hang_time@self*, desperado@self*, wavedasher@self*, powershield_oath@self*, tech_guard@self) | - | 2 (renewal, retaliation) | fury | 15 |
| momentum | stacks to 5; a stored resource only landing/rush rules read | 8 (updraft@self, reprisal@self, rush@self, hit_and_run@self*, banked_momentum@self*, hang_time@self*, fury@self*, critical_mass@self*) | - | 2 (crosswind, bastion) | crosswind, bastion, iron_resolve | 11 |

Reading it: **Haste** is touched by 18 pieces, **Guarded** by 15, **Curse** by 15, **Chill** by 10, **Momentum** by 11. Curse and Chill are each the price paid by 6 keystones. Momentum has 8 appliers and 2 readers and no effect of its own. Burn is applied by 2 pieces (Plague Bearer also burns its owner), Shock by 2. The surface/afterimage look of a status therefore stands for several unrelated causes, and for both "the enemy has it" and "you paid for it".

### 1.3 Synergies and archetypes [MEASURED; the archetype table is typed data in `mod_graph.lua`]

| id | name (announced as "<name> assembled") | roles and the alternatives that fill them (a+b = both held) | pieces | of them keystones | toast blurb |
|---|---|---|---|---|---|
| burn | Burn stacking | a Burn applier: plague_bearer / kindling+burning / kindling+pyromancer / kindling+ember_crown / a payoff: pyre / cinder / everburn | 8 | 3 | Your hits set Burn and your payoff drives turn it into damage. |
| chill | Chill stacking | a Chill applier: deep_freeze / icebound+frosted / icebound+frozen_oath / icebound+winter_heart / a payoff: brittle / shatter | 7 | 2 | Your hits Chill and your payoff drives turn it into damage. |
| shock | Shock chain | an electric source: charged / storm_shell / Conductor: conductor | 3 | 1 | Electric hits Shock one opponent and chain it to the next. |
| momentum | Momentum speed | a Momentum source: updraft / hit_and_run / banked_momentum / hang_time / reprisal / critical_mass / fury / a landing payoff: crosswind / bastion | 9 | 5 | Hits build Momentum and a landing spends it. |
| haste | Haste web | a Haste source: ledge / clean_landing / combo_surge / skyfarer / perpetual_motion / bloodlust / hit_and_run / critical_flow / crosswind / a payoff: rush / echo_weaver / trailing | 12 | 5 | Haste feeds your Haste payoffs, and they feed Haste again. |
| guard | Guard and heal | a Guarded source: reprisal / bastion / shelter / tech_guard / parry_master / hang_time / iron_resolve / last_stand / desperado / Renewal: renewal | 10 | 5 | Guarded turns into healing. |
| technique | Technique crit | a technique trigger: wave_edge / combo_conduit / a crit payoff: critical_flow / critical_mass | 4 | 2 | A technique forces a crit and the crit pays out. |
| crit | Passive crit | a crit chance: keen / ruthless / finishing / gambler / executioner / a crit payoff: brutal / critical_flow / critical_mass | 8 | 3 | Crit chance meets a stronger crit. |
| armour | Armour retaliation | an armour source: shield_stance / wavedasher / powershield_oath / juggernaut / Retaliation: retaliation | 5 | 3 | Armour that absorbs a hit makes your next hit a crit. |

An archetype is announced the first time its two roles are filled. The pair table `mod_synergy.generate` derives 180 (after the proposal: 88) pairs. In the synergy analysis only 4.2% of pairs actually interact, and even when a player chases them three of the nine archetypes (Shock chain, Technique crit, Armour retaliation) complete in under 10% of 12-stage runs.

### 1.4 Every place the game announces something [MEASURED from source; file and line cited]

| where | what | when | source |
|---|---|---|---|
| toast (strip panel, 360 logic frames, queued) | Starter panel at run start: starter drive name + base line + keystone name + effect + drawback | once per run | run_host.lua:394-413 |
| toast | Milestones: "Fifth/Sixth slot unlocked", "Keystone allowance: n", "Drive tier n", "New Game+ n" | stage start, when the number changes | run_host.lua:369-379,437 |
| toast | "<Archetype> assembled" + one-line blurb (gold title, archetype emblem) | first time each of 9 archetypes is complete in the run; polled every 20 frames | synergy_fx.lua:178-186 |
| toast | "Technique rule fired: <rule>. Techniques show as a coloured afterimage while their reward lasts." then a plain "Technique" | first technique/crit rule fire per run | mod_lab.lua:687-695; run_host.lua:46 |
| toast | "Critical hit xN.N" | per crit moment (presentation per peer) | mod_lab.lua:280-300 / earned_fx |
| toast | "A drive moved to the bag: fewer slots", "Bag full..." , "Build update refused/delayed" | slot reduction, host errors | mod_lab.lua:460-479,819-820 |
| flash (strip text, 90 frames) | "<Modifier name>!" or "Modifier!" on EVERY engine trace change (any modifier fired) | every rule fire that writes a trace line | run_hud.lua:40-46 |
| flash | "Slot n changed", "Slot n emptied", "Keystone: <name>", "Keystone removed", "Merged", "+ drive", "Drive waiting", "Build ready", "Passed it on", "Out of bounds: a stock is lost", "Collect the drives (n s)" | player/host actions | run_host.lua:152-704 |
| card (150 frames) | "Merged!" card; "A drive dropped!"; "Picked up: <drive>" / "Bag full" | drive events | run_host.lua:230,527-542 |
| banner | "Collect the drives n s" banner + marker on nearest floor drive | stage end hold | run_host.lua:573-634 |
| strip (always on) | 6 drive pips (colour = base, rarity border), "+N%" strength, "Depth n", keystone letters | always | run_hud.lua:55-80 |
| link flash (world) | archetype-coloured link between fighter and target when a chain fires; at most 1 per 18 frames, softened inside 45 | a chain link fires | synergy_fx.lua:132-175 |
| emblem pill + counter (strip) | archetype emblem with a counter that climbs while the chain fires | while a chain is firing | synergy_fx.lua:160-200 |
| surface (player-model shader) | persistent motif treatment while an archetype is complete, stronger while the chain fires | continuous | synergy_fx.lua header |
| surface / afterimage | status looks: burn shock chill curse haste guarded momentum (the surface channel), earned afterimage per technique (blue L-cancel, teal shield, gold wave, red combo, white move, violet miss) | while the status/window lasts | mod_status.lua; drive_text.lua:99; earned_fx.lua |
| tracer + impact frame | crit tracer and impact frame | per crit | mod_lab.lua:280-300 |
| opponent plate | every modifier the opponent carries, one line each (deferred while a toast is up) | at opponent intro | drive_text.lua:156-166; run_host.lua:47 |
| reward / bag screens | full detail lines of the focused drive, totals before/after, archetype banner n/m, link marks, "advances/completes" marks on offers | reward moment, Z+START | run_screen.lua; synergy_fx.lua grid |

What the recorded sessions show (logs read only; `log_counts.py`; the logs hold log lines, not what was drawn, so toasts and "Modifier!" flashes are counted only where the mod logged them. **The harness under-reports**; status applications are native timed-channel restarts only (channels 1 and 2 are the only ones seen), a lower bound):

| log | wall minutes | stages started | "<archetype> assembled" toasts | milestone toasts (slot / allowance / tier / NG+) | crits logged | forced crits armed | afterimages on | tracers on | status applications (native timed channels) | per wall minute |
|---|---|---|---|---|---|---|---|---|---|---|
| envoy-play (Classic, ~51 min) | 51.1 | 21 | 4 | 11 | 42 | 20 | 66 | 54 | 416 | 8.1 |
| envoy-crit (granted crit build, depth 30 loop 2, ~8 min) | 8.4 | 1 | 4 | 0 | 4 | 4 | 3 | 6 | 54 | 6.4 |
| envoy-falco3 (granted build, ~3 min) | 3.2 | 1 | 4 | 0 | 1 | 4 | 4 | 2 | 56 | 17.5 |

Per stage in the 51-minute run (mean over its 21 stages): 19.8 native status applications, 2.0 crits logged, 1.0 forced crit armed, 3.1 afterimages, 2.6 tracers, 0.2 "assembled" toasts, 0.5 milestone toasts. Per wall minute: 8.1 status applications, 0.8 crits, 1.3 afterimages, 1.1 tracers. These are lower bounds (see above); the milestone toasts and the assembled toasts arrive in bursts, not evenly.

Facts from the same logs: in the 51-minute Classic run the three milestone toasts (Fifth slot unlocked, Keystone allowance 2, Drive tier 2) were raised in the same frame at stage 5, and again at stage 10 (Sixth slot, allowance 3, tier 3): the toast queue plays one at a time for 360 frames each, so the player waits 18 s. In both granted-build logs the first four "assembled" toasts arrive within 9 to 13 s, two or three of them in a single frame. Those two builds were made with the dev `grant` command (the logs show 10 to 12 grant lines), so they are ceiling builds, not typical play; the recorded 51-minute run is typical play.
The owner's own build is the `envoy-crit` log's slot dump: `Brutal Keen Red Drive of the Icebound and of Critical Flow` is slot 3 of 6, the other five are `Ruthless Brutal Trailing White Drive of the of Critical Flow and of the Wave`, `Ruthless Keen Green Drive of the Shelter and of Critical Flow`, `Keen Brutal Purple Drive of the Bastion and of Critical Flow`, `Ruthless Keen Yellow Drive of the of Critical Flow and Updraft`, `Green Drive: Cinder`; keystones `hit_and_run, gambler, critical_mass, combo_conduit, wavedasher, aerialist`; allowance 12, owed 6.

---

## 2. Complexity score

### 2.1 Definition (computed in `inventory.lua`)

Score of one piece = the number of separate things a player must hold in mind:

| term | counted as |
|---|---|
| triggers | 1 if the piece fires on an event (a standing rule counts 0), plus 1 for every alternative trigger (`also`) |
| conditions | every condition on the trigger and on every alternative |
| effects | distinct benefit effects (value effects on the same budget family count once: run and air speed are one idea; the three bad-status removals are one "cleanse"; a drawback effect is not a benefit) |
| drawbacks | 1 if the piece has a price (a `cost` text, or a drawback effect such as slower, bleed, a status on yourself) |
| statuses | distinct statuses named anywhere in it (conditions, effects, price); "any status" counts once |
| numbers | numbers in the text the player reads (`drive_text.mod_lines`, tier 1) |

Also computed per piece: words in the rule text, and **needs a partner** from the derived graph (`mod_graph.lua`): it reads a status, element, crit or armour event that none of its own effects produces. An item's score = base line (2) + its pieces; a build's score = the sum over its distinct rules.

### 2.2 Distribution over the 86 pieces [MEASURED]

| group | measure | n | min | p25 | median | p75 | p90 | max | mean |
|---|---|---|---|---|---|---|---|---|---|
| all 86 | score | 86 | 1 | 3 | 5 | 8 | 9 | 13 | 5.5 |
| all 86 | words of rule text | 86 | 4 | 10 | 14 | 21 | 26 | 33 | 15.5 |
| ordinary drive pieces (38) | score | 38 | 1 | 3 | 4 | 6 | 8 | 13 | 4.6 |
| ordinary drive pieces (38) | words of rule text | 38 | 4 | 9 | 10 | 15 | 22 | 29 | 12.2 |
| keystones (42) | score | 42 | 2 | 4 | 7 | 9 | 10 | 12 | 6.7 |
| keystones (42) | words of rule text | 42 | 9 | 14 | 18 | 23 | 26 | 33 | 19.1 |
| uniques (6) | score | 6 | 2 | 3 | 3 | 3 | 5 | 5 | 3.2 |
| uniques (6) | words of rule text | 6 | 7 | 8 | 9 | 13 | 18 | 18 | 10.7 |

Histogram, score:count over all 86: 1:4 2:7 3:14 4:13 5:9 6:9 7:5 8:11 9:6 10:4 11:2 12:1 13:1. Median piece: 5 things to hold in mind and 14 words; the worst keystone reads 33 words.

### 2.3 The 20 heaviest pieces

| rank | id | slot | score | words | numbers | triggers | conditions | effects | drawbacks | statuses | needs a partner |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | combo_finish | suffix | 13 | 9 | 2 | 3 | 5 | 1 | 0 | 2 | yes |
| 2 | combo_conduit | keystone | 12 | 32 | 3 | 2 | 3 | 1 | 1 | 2 | yes |
| 3 | critical_mass | keystone | 11 | 33 | 4 | 1 | 0 | 2 | 1 | 3 | yes |
| 4 | finishers_mark | keystone | 11 | 28 | 5 | 1 | 1 | 1 | 1 | 2 |  |
| 5 | combo_surge | suffix | 10 | 27 | 2 | 2 | 3 | 1 | 0 | 2 | yes |
| 6 | desperado | keystone | 10 | 20 | 2 | 1 | 1 | 2 | 1 | 3 |  |
| 7 | hang_time | keystone | 10 | 23 | 3 | 1 | 0 | 2 | 1 | 3 |  |
| 8 | parry_master | keystone | 10 | 18 | 4 | 1 | 0 | 2 | 1 | 2 |  |
| 9 | bloodlust | keystone | 9 | 22 | 3 | 1 | 0 | 2 | 1 | 2 |  |
| 10 | deep_freeze | keystone | 9 | 21 | 3 | 1 | 0 | 2 | 1 | 2 |  |
| 11 | hit_and_run | keystone | 9 | 24 | 2 | 1 | 0 | 2 | 1 | 3 |  |
| 12 | opportunist | keystone | 9 | 26 | 3 | 1 | 1 | 1 | 1 | 2 |  |
| 13 | powershield_oath | keystone | 9 | 25 | 3 | 1 | 0 | 2 | 1 | 2 |  |
| 14 | retribution | keystone | 9 | 26 | 4 | 1 | 0 | 1 | 1 | 2 |  |
| 15 | bastion | suffix | 8 | 14 | 2 | 1 | 1 | 2 | 0 | 2 | yes |
| 16 | bulwark | keystone | 8 | 18 | 4 | 0 | 0 | 2 | 2 | 0 |  |
| 17 | clash_king | keystone | 8 | 20 | 3 | 1 | 0 | 2 | 1 | 1 |  |
| 18 | conductor | keystone | 8 | 25 | 2 | 1 | 1 | 2 | 1 | 1 | yes |
| 19 | crosswind | suffix | 8 | 15 | 2 | 1 | 1 | 2 | 0 | 2 | yes |
| 20 | everburn | keystone | 8 | 21 | 4 | 0 | 0 | 2 | 1 | 1 | yes |

Eight of the top ten are keystones (a second benefit and a status on yourself as the price); the two heaviest drive pieces (`combo_finish` 13, `combo_surge` 10) are heavy because the synergy bridges added alternative triggers (Shock, Cursed) to a plain combo trigger. Full ranking: `inventory_summary.txt`.

### 2.4 ITEMS as rolled: the real roller, offline [MEASURED]

Method: `drive_loot:roll` with `mod_progression` contexts, 1000 seeds per cell, natural rarity (weights by depth band), as `melee/pc/tests/envoy_drive_loot.lua` builds it. "eff." = depth + 13 x loop. A build here = all slots (4 to 6) filled with natural rolls plus the whole keystone allowance filled from the real offer (random pick); that is neither a typical nor a maximal player build, it is the roller's own mean. "After" = the proposal of section 4 (pool, curve and allowance).

**One drive (natural roll)**

| depth | loop | eff. | rarity c/m/r/u % | rules/drive today (mean) | p90 | max | after (mean) | after max | score today mean | p90 | max | score after mean | p90 | max | words today mean | p90 | words after mean | p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 1 | 100/0/0/0 | 1.00 | 1 | 1 | 1.00 | 1 | 6.1 | 9 | 10 | 4.8 | 7 | 8 | 15 | 20 | 12 | 16 |
| 5 | 0 | 5 | 86/14/0/0 | 1.32 | 2 | 3 | 1.15 | 2 | 7.4 | 12 | 20 | 5.9 | 9 | 12 | 19 | 29 | 11 | 17 |
| 10 | 0 | 10 | 80/15/4/1 | 1.45 | 2 | 5 | 1.19 | 2 | 8.1 | 14 | 32 | 6.0 | 9 | 13 | 21 | 36 | 12 | 17 |
| 20 | 0 | 20 | 80/15/4/1 | 1.43 | 2 | 5 | 1.19 | 2 | 8.0 | 13 | 31 | 6.0 | 9 | 12 | 21 | 35 | 12 | 17 |
| 30 | 0 | 30 | 80/15/4/1 | 1.44 | 2 | 5 | 1.19 | 2 | 8.0 | 13 | 28 | 6.0 | 9 | 12 | 21 | 35 | 12 | 17 |
| 30 | 1 | 43 | 80/15/4/1 | 1.43 | 2 | 5 | 1.19 | 2 | 8.0 | 13 | 26 | 6.0 | 9 | 13 | 21 | 34 | 12 | 17 |
| 30 | 2 | 56 | 80/15/4/1 | 1.43 | 2 | 5 | 1.19 | 2 | 8.0 | 13 | 29 | 6.0 | 9 | 12 | 21 | 35 | 12 | 17 |

A forced **rare** drive (what the third reward offer is), 2000 seeds each:

| depth | rules today (max) | score today | words today | lines read today | rules after (max) | score after | words after | lines after |
|---|---|---|---|---|---|---|---|---|
| 3 | 2.16 (3) | 11.0 | 26 | 3.4 | 1.00 (1) | 4.8 | 12 | 2.0 |
| 6 | 3.17 (4) | 15.2 | 38 | 4.8 | 2.00 (2) | 8.8 | 16 | 3.0 |
| 10 and deeper | 4.17 (5) | 19.3 | 50 | 6.0 | 2.00 (2) | 8.8 | 17 | 3.0 |

**One whole build from natural rolls** (`rule instances` = drive rules + keystones; `per-hit rules` = pieces triggered by a hit, a hit taken, a combo or a crit)

| depth | loop | eff. | slots | allow. | rule instances today | after | distinct rules today | after | statuses touched today | after | trigger kinds today | after | per-hit rules today | after | need a partner today | after | build score today | after | words read today | after |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 1 | 4 | 1 | 5.0 | 5.0 | 4.8 | 4.7 | 3.6 | 2.5 | 2.0 | 1.8 | 1.2 | 1.1 | 2.0 | 0.1 | 31 | 24 | 77 | 63 |
| 5 | 0 | 5 | 5 | 2 | 8.6 | 7.8 | 8.1 | 7.3 | 4.9 | 4.3 | 3.2 | 2.8 | 2.2 | 2.0 | 3.2 | 2.6 | 51 | 39 | 129 | 86 |
| 10 | 0 | 10 | 6 | 3 | 11.6 | 10.1 | 10.8 | 9.6 | 5.7 | 4.7 | 4.4 | 3.7 | 3.1 | 2.7 | 4.2 | 3.1 | 68 | 51 | 182 | 118 |
| 20 | 0 | 20 | 6 | 5 | 13.6 | 11.1 | 12.9 | 10.6 | 6.1 | 4.9 | 5.1 | 4.0 | 3.7 | 3.0 | 4.5 | 3.2 | 82 | 56 | 221 | 132 |
| 30 | 0 | 30 | 6 | 7 | 15.6 | 12.1 | 14.9 | 11.6 | 6.4 | 5.1 | 5.9 | 4.3 | 4.4 | 3.4 | 4.8 | 3.3 | 96 | 61 | 258 | 147 |
| 30 | 1 | 43 | 6 | 9 | 17.6 | 13.1 | 16.9 | 12.6 | 6.6 | 5.2 | 6.6 | 4.6 | 5.0 | 3.8 | 5.1 | 3.4 | 110 | 66 | 298 | 162 |
| 30 | 2 | 56 | 6 | 12 | 20.6 | 14.1 | 19.8 | 13.6 | 6.9 | 5.4 | 7.7 | 4.9 | 6.1 | 4.2 | 5.6 | 3.5 | 131 | 71 | 356 | 177 |

**Builds as a player assembles them** (`sim_runs.lua`: the real reward economy, floor drops, rewards, merging, bag of four, a strength-greedy picker, every stage won, 300 runs, Classic, loops 0 to 2 so effective depth to about 40; the Adventure mode run is in `sim_runs_adventure.txt` and agrees). Cells "today / after".

| eff. depth band | samples | slots | keystone allowance today / after | affix instances | rare drives held (today) | keystones held | DISTINCT rules | dead duplicates | statuses touched | trigger kinds | per-hit rules | need a partner | fail the rule | score | words read | lines read |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1-3 | 900 | 4.0 | 1.0 / 1.0 | 3.4 / 3.4 | 0.0 | 1.0 / 1.0 | 4.3 / 4.2 | 0.1 / 0.2 | 3.4 / 2.2 | 1.9 / 1.7 | 1.1 / 1.0 | 1.7 / 0.1 | 1.8 / 0.0 | 21 / 14 | 68 / 56 | 9 / 9 |
| 4-7 | 1200 | 4.8 | 1.8 / 1.8 | 5.3 / 5.1 | 0.0 | 1.8 / 1.8 | 6.9 / 6.4 | 0.2 / 0.4 | 4.6 / 3.2 | 2.9 / 2.5 | 1.7 / 1.6 | 2.6 / 0.6 | 3.0 / 0.0 | 33 / 23 | 109 / 84 | 14 / 13 |
| 8-12 | 900 | 5.3 | 2.3 / 2.3 | 6.5 / 5.9 | 0.1 | 2.3 / 2.3 | 8.5 / 7.8 | 0.3 / 0.4 | 5.0 / 3.7 | 3.5 / 2.9 | 2.2 / 1.9 | 3.1 / 1.0 | 3.9 / 0.1 | 42 / 29 | 137 / 101 | 17 / 16 |
| 13-19 | 2100 | 6.0 | 3.7 / 3.7 | 8.0 / 6.9 | 0.4 | 3.7 / 3.7 | 11.2 / 10.1 | 0.5 / 0.5 | 5.6 / 4.2 | 4.4 / 3.6 | 2.8 / 2.5 | 3.7 / 1.4 | 5.4 / 0.1 | 57 / 39 | 184 / 131 | 23 / 20 |
| 20-29 | 2400 | 6.0 | 5.5 / 4.2 | 8.0 / 6.9 | 0.4 | 5.5 / 4.2 | 13.0 / 10.6 | 0.5 / 0.5 | 6.0 / 4.3 | 5.2 / 3.8 | 3.3 / 2.7 | 3.9 / 1.5 | 6.7 / 0.1 | 70 / 42 | 220 / 139 | 26 / 22 |
| 30-40 | 2400 | 6.0 | 7.4 / 5.0 | 8.0 / 6.9 | 0.4 | 7.4 / 5.0 | 14.9 / 11.3 | 0.5 / 0.5 | 6.3 / 4.5 | 6.0 / 4.1 | 3.9 / 3.0 | 4.2 / 1.5 | 8.0 / 0.2 | 84 / 45 | 258 / 150 | 30 / 23 |

Two things the table says. **First**, a typical build holds only 1.15 rules per drive (6.9 to 8 instances in 6 drives): the stacking problem is the rare end, not the average, and it hits exactly the moment the owner described (a rare reward on the third offer, or a granted build). **Second**, even at stages 1 to 3 the typical build already touches 3.4 of the 7 statuses, and 1.7 of its 4.3 distinct rules (40%) need a partner the player does not have yet.

The owner's recorded build, scored with the same inventory (`owner_build.lua`):

| measure | value |
|---|---|
| drive rule instances / distinct rules / dead duplicates | 22 / 11 / 11 |
| keystones | 6 |
| rule lines / words the screens show | 55 / 509 |
| statuses touched / trigger kinds / rules that need a partner / rules failing the bite rule | 7 / 6 / 7 / 8 |
| build score (distinct rules) | 90 |
| strength today, all records at the depth-30 loop-2 tier (ratios only: the log's own HUD said +627%, so the build was granted at lower tiers) | x33.4 |

---

## 3. Diagnosis: where "too much at once" comes from

| # | cause | numbers [MEASURED] | what it does to reading |
|---|---|---|---|
| 1 | **Affix stacking per drive** | rare drive 4.2 rules (5 for white), score 19.3, 50 words, 6 lines, 0.3 drawback clauses; common drive already 2.1 lines at stage 1 | the drive name becomes a sentence ("Brutal Keen Red Drive of the Icebound and of Critical Flow") and the panel a paragraph |
| 2 | **Duplicates are dead** | owner's granted build: 11 of 22 drive rules do nothing (a normal rule on a second drive is ignored; only its highest tier counts); typical greedy play: 0.5 dead copies per build | the player reads and equips things that are inert, and cannot tell which |
| 3 | **Keystone count and weight** | allowance 1 + eff/5, uncapped (12 at eff. 56); a keystone averages score 6.8 and 19 words in 2 lines; 21 of 42 have two or more benefit effects or a status on yourself as the price | each keystone is a small paragraph; seven is a page |
| 4 | **Shared statuses** | Haste touched by 18 pieces, Guarded 15, Curse 15, Chill 10, Momentum 11; 13 keystones pay with Chill, Curse or Burn on yourself | a status look cannot mean one thing: "Chill" is both "you slowed them" and "you paid for your keystone" |
| 5 | **Triggers that fire per hit** | 19 pieces fire on a hit, a hit taken, a combo or a crit; greedy builds at depth 30 to 40 hold 3.9 of them live; every rule fire also raises the generic "Modifier!" flash | the per-hit rules are the visual noise: one hit can start 3 or 4 effects at once |
| 6 | **Synergies announced on assembly** | 9 archetypes; 4 "assembled" toasts in 51 min of normal play, 4 inside 13 s in granted builds; each toast queues for 360 frames | the game tells the player something is assembled instead of letting them see which two pieces did it |
| 7 | **Milestone toasts stack** | slot, allowance and tier toasts are raised in the same frame at depth 5 and 10 | 18 s of banner for three numbers |
| 8 | **Pieces whose rule is not one short sentence** | 38 of 86 fail the bite rule; 21 have a rule sentence over 14 words; 18 have two or more benefit effects; 8 technique and crit pieces carry a second "tutorial" line; 4 crit pieces say "the engine has none until a modifier grants a chance" | the player reads instructions where they expect a rule |
| 9 | **Same thing, several words** | Haste is "Haste", "Hasted", "moving fast" (Rush, Trailing) and "speed boost" (Still Heart); Guarded is restated as "take 25% less damage" in 7 texts; Chill as "20% slower" in 11 | the player cannot match a text to a look |
| 10 | **Pieces that only matter in combination** | 23 of 86 (17 of 38 ordinary); 17 of 38 ordinary pieces (45%) are payoffs or enablers; a greedy build holds 1.7 of them already at stages 1 to 3 (of 4.3 distinct rules) | a dead drive early: one rule that needs another piece the player does not have |
| 11 | **Hubs** | the synergy analysis: Rush, Trailing, Echo Weaver and Still Heart are fed by 14 Haste sources each | easy to switch on and says nothing about the build |

Bugs seen while reading (not fixed, for whoever owns those files):

1. `drive_loot.lua` `L:name`: suffix labels that already begin with "of" are joined with `' of the '`, giving "Drive of the of Critical Flow and of the Wave" (seen in the owner's slot dump).
2. `drive_text.lua` `technique_lines`: for a passive rule only the first effect is spoken, so **Brutal reads "Your hits crit 3% of the time" and never mentions its multiplier gain** (its reason to exist); and Brutal, Keen, Ruthless and Finishing all show the line "Crits are rare: the engine has none until a modifier grants a chance", wrong on Brutal (it grants a chance) and a developer word for the player.
3. A normal rule held on two equipped drives is accepted, shown, and ignored (`drive_bag.lua` `derive`); `drive_merge.lua` only merges within one colour, so the cross-colour duplicate cannot merge either.
4. Rush's text says "moving fast" for the Haste condition (vocabulary, section 3 row 9).

---

## 4. The proposal for the split

Everything below is checked mechanically: `proposal.lua` copies the real pool, makes the edits as data records, and every edited record passes `mod_schema.validate`; `inventory.lua` (run with `PROPOSED=1`) then scores the result with the same rule. Nothing proposed needs an op, condition kind or trigger that is not already in `mod_schema.lua` / `mod_registry.lua` (4h).

### 4a. The rule for a rule

A **bite-size piece** is one sentence a player can say in one breath. Exact limits (the limits in `inventory.lua` `LIM`, tested on every piece):

| # | limit | applies to |
|---|---|---|
| R1 | at most one trigger; a standing rule has none; **no alternative triggers** (`also`) | every piece |
| R2 | at most one condition | every piece |
| R3 | exactly one benefit effect (value effects on one family count once; "spend 1 Momentum" is the price of the effect, not a second effect; cleanse counts once) | every piece |
| R4 | names at most two statuses: at most one it needs (reads) and at most one it gives; the Momentum counter and "any status" do not count | every piece |
| R5 | at most 2 numbers in the text it shows (3 on a keystone or unique, which also states a price) | every piece |
| R6 | rule sentence at most 14 words as tested today (target 12 once statuses stop restating their own numbers); no tutorial second line | every piece |
| R7 | **no drawback on an ordinary drive** | prefix and suffix drives |
| R8 | a keystone is **one rule line and one drawback line** (price line at most 12 words, one drawback effect) | keystones |
| R9 | the price comes from a fixed list: **Slow** (run speed -X%), **Low** (jump -X%), **Fragile** (launched X% farther), **Weak** (damage you deal -X%), **Vulnerable** (damage you take +X%), **Lock** (cannot run / shield), and for a triggered keystone **Bleed** (lose N damage each time it fires). **Never a status on yourself.** | keystones and uniques |
| R10 | a payoff (reads a status it does not give) opens at effective depth 5 | drive pieces |
| R11 | each status has one name in all text (Haste, Guarded, Burning, Chilled, Marked); its numbers live in the glossary, not in every sentence | all text |

Result of the test today [MEASURED]: ordinary 23/38, keystones 20/42, uniques 5/6 (total 48/86). After the proposal: ordinary 36/36, keystones 29/30, uniques 6/6 (total 71/72); the single exception is Conductor, kept on purpose (it Shocks the target and chains the Shock: two effects, one idea).

### 4b. What changes, piece by piece

**Every piece that fails today, with its new one-line rule** (a keystone shows rule line and drawback line; numbers are the new tier numbers where they change):

| id | slot | fails today | NEW rule text (and price) | what changes | new numbers: tier 1 / 2 / 3 |
|---|---|---|---|---|---|
| brutal | prefix | words>14 | Your hits crit 3% of the time; crits gain +0.25x. | BUG: today the text hides the multiplier gain (the only reason to take it); the line now states both | mult=1.25 / mult=1.312 / mult=1.375 |
| echoes | prefix | words>14 | Aerial attacks repeat once, weaker. | shorter | copies=1 / copies=2 / copies=3 |
| featherweight | prefix | drawback on an ordinary drive | **CUT** | ordinary drive with a drawback clause; same reason |  |
| finishing | prefix | numbers>2; words>14 | Hits on a target above 100% crit 25% of the time. | multiplier moves to the glossary (x1.5); chance 25% | chance=0.25 / chance=0.3125 / chance=0.375 |
| heavy | prefix | drawback on an ordinary drive | **CUT** | ordinary drive with a drawback clause; the colour bases already give speed and jump |  |
| keen | prefix | words>14 | Your hits crit 5% of the time. | engine line out; crit multiplier is the glossary x1.5 | chance=0.05 / chance=0.0625 / chance=0.075 |
| ruthless | prefix | words>14 | Your aerial hits crit 15% of the time. | multiplier moves to the glossary (x1.5); one number | chance=0.15 / chance=0.1875 / chance=0.225 |
| clean_landing | suffix | words>14 | L-cancel after a hit: Haste for 1.5 s. | tutorial line out | duration=90 / duration=120 / duration=150 |
| combo_finish | suffix | triggers>1; conditions>1; reads >1 status | Finish a combo of 3+ hits: heal 3%. | drop the Shock and Curse alternative triggers | heal=3 / heal=4 / heal=5 |
| combo_surge | suffix | triggers>1; conditions>1; words>14 | 3rd hit of a combo: Haste for 0.8 s. | drop the Shock alternative trigger | duration=45 / duration=60 / duration=75 |
| critical_flow | suffix | words>14 | Land a crit: Haste for 0.8 s. | tutorial line out | duration=45 / duration=60 / duration=75 |
| crosswind | suffix | words>14 | Land with Momentum: spend 1, gain Haste for 3 s. | payoff: opens at depth 5 so a one-rule drive is never dead | duration=180 / duration=225 / duration=270 |
| reprisal | suffix | effects>1; numbers>2 | Perfect shield: Guarded for 3 s. | one effect: the free Momentum goes | duration=180 / duration=225 / duration=270 |
| retaliation | suffix | triggers>1; conditions>1 | When armour absorbs a hit: your next hit crits (x1.4). | drop the Guarded alternative trigger (the bridge becomes its own optional piece, Riposte) | mult=1.4 / mult=1.6 / mult=1.8 |
| tech_guard | suffix | words>14 | Tech: Guarded for 1 s. | tutorial line out | duration=60 / duration=90 / duration=120 |
| storm_shell | unique | effects>1 | All your attacks become electric. / Drawback: damage you deal -20%. | one rule (electric), one price; the defence half goes, like Ember Crown and Winter Heart |  |
| bloodlust | keystone | effects>1 | Knock out a fighter: heal 20%. / Drawback: you lose 3 damage points each time. | one rule (heal); price Bleed | heal=20 |
| bulwark | keystone | effects>1; numbers>2; more than one drawback | Launch you take -35%. / Drawback: you run 20% slower. | one stat (launch taken); one price |  |
| clash_king | keystone | effects>1 | **CUT** | clank is a rare event (0.02 per second measured for a CPU) and needs a fighter clank |  |
| clean_lander | keystone | words>14 | L-cancel after a hit: Haste for 2 s. / Drawback: you lose 1 damage point each time. | text trim | duration=120 |
| combo_conduit | keystone | triggers>1; conditions>1; words>14 | 3rd hit of a combo: your next hit crits (x1.6). / Drawback: you lose 1 damage point each time. | drop the Cursed alternative trigger; price Bleed |  |
| conductor | keystone | effects>1; words>14 | Electric hits Shock the target and chain it onward. / Drawback: you lose 1 damage point per electric hit. | text trim; the one deliberate two-effect keystone (Shock and its chain are one idea) | duration=150 |
| critical_mass | keystone | effects>1; numbers>2; words>14 | **CUT** | 3 effects, 4 numbers; hub of the 8 crit sources |  |
| deep_freeze | keystone | effects>1; gives >1 status | Every hit Chills the target for 4 s. / Drawback: you lose 1 damage point per hit. | one rule (Chill); price Bleed | bonus=0.04 duration=240 |
| desperado | keystone | effects>1; gives >1 status | **CUT** | near-duplicate of Last Stand (a state gives Haste and Guarded) |  |
| everburn | keystone | effects>1; numbers>2; words>14 | Burning targets take 50% more damage. / Drawback: you take 15% more damage. | one rule; price Vulnerable |  |
| featherfall | keystone | effects>1 | **CUT** | weight and fall speed are not read by anything else |  |
| finishers_mark | keystone | numbers>2; words>14 | **CUT** | near-duplicate of Opportunist (hit a target, Mark it, pay 1) |  |
| fury | keystone | effects>1 | When you are hit, gain Haste for 3 s. / Drawback: you lose 1 damage point each time. | one rule (Haste); price Bleed | duration=180 |
| hang_time | keystone | effects>1; drawback line>12 words | **CUT** | air-jump trigger with Guarded, Momentum and a self-status price |  |
| hit_and_run | keystone | effects>1; drawback line>12 words | Every hit you land gives Haste for 2 s. / Drawback: you lose 1 damage point per hit. | one rule (Haste); price Bleed | duration=120 |
| last_stand | keystone | effects>1; gives >1 status | On your last stock you are always Guarded. / Drawback: you lose 2 damage points every second. | one rule (Guarded); price Bleed |  |
| opportunist | keystone | words>14 | Hit a target with a status: Mark it for 2.5 s. / Drawback: you lose 1 damage point per hit. | shorter text | bonus=0.06 duration=150 |
| parry_master | keystone | effects>1; numbers>2 | Perfect shield: Guarded for 5 s. / Drawback: you lose 1 damage point each time. | one rule (Guarded); price Bleed | duration=300 |
| plague_bearer | keystone | numbers>2; words>14 | Every hit sets the target Burning (stacks to 3). / Drawback: you lose 1 damage point per hit. | one rule; price Bleed instead of Burn on yourself | damage=2 duration=120 |
| powershield_oath | keystone | effects>1; words>14 | **CUT** | technique keystone for a rare event; Parry Master covers perfect shield |  |
| retribution | keystone | numbers>2; words>14 | When you are hit, the attacker is Marked for 3 s. / Drawback: you lose 1 damage point each time. | Marked on the attacker; price Bleed | bonus=0.08 duration=180 |
| wavedasher | keystone | effects>1; words>14 | Wavedash: super armour for 6 frames. / Drawback: you lose 2 damage points each time. | one rule (armour); price Bleed |  |

**Kept as they are**: 28 pieces already pass and are not touched at all; 20 more pass but get an edit (a payoff opening at depth 5, a trimmed line, a price swap). The 30 keystones below include every keystone that passes and is not cut.

**Cut outright** (whether or not they pass), with the reason:

| id | slot | score today | passed the rule? | why cut |
|---|---|---|---|---|
| banked_momentum | keystone | 7 | yes | free counter with no effect of its own; Momentum has 2 readers |
| clash_king | keystone | 8 | no | clank is a rare event (0.02 per second measured for a CPU) and needs a fighter clank |
| critical_mass | keystone | 11 | no | 3 effects, 4 numbers; hub of the 8 crit sources |
| desperado | keystone | 10 | no | near-duplicate of Last Stand (a state gives Haste and Guarded) |
| echo_oath | keystone | 3 | yes | third echo keystone; Echoes measured +5% damage, strength x2.2 |
| featherfall | keystone | 6 | no | weight and fall speed are not read by anything else |
| finishers_mark | keystone | 11 | no | near-duplicate of Opportunist (hit a target, Mark it, pay 1) |
| hang_time | keystone | 10 | no | air-jump trigger with Guarded, Momentum and a self-status price |
| phase_dash | keystone | 5 | yes | air-dodge event is flagged unverified in play |
| powershield_oath | keystone | 9 | no | technique keystone for a rare event; Parry Master covers perfect shield |
| skyfarer | keystone | 6 | yes | same template as Perpetual Motion (an event gives Haste and costs 1 damage) |
| still_heart | keystone | 6 | yes | deletes Haste, the most-fed status: an anti-synergy piece with no identity of its own |
| featherweight | prefix | 4 | no | ordinary drive with a drawback clause; same reason |
| heavy | prefix | 4 | no | ordinary drive with a drawback clause; the colour bases already give speed and jump |

**The ordinary pieces whose text or record changes** (text trims, dropped alternative triggers, the crit multiplier moved to the glossary, payoff depth):

| id | rule text today | rule text after | score today | score after | words today | words after | what changed |
|---|---|---|---|---|---|---|---|
| kindling | Fire hits set the target Burning for 3 seconds (3 damage every second) | Your hits set the target Burning for 3 s. | 6 | 4 | 13 | 9 | applier on any hit: no fire-hit prerequisite (balance: number to be tuned) |
| pyre | Your hits launch Burning targets 8% farther | . | 3 | 2 | 7 | 1 | payoff: opens at depth 5 so a one-rule drive is never dead |
| feasting | Knock out a target that has a status effect: heal 10% | Ko_dealt: heal 10%. | 5 | 5 | 11 | 3 | payoff: opens at depth 5 so a one-rule drive is never dead |
| crosswind | Land with Momentum: spend one stack for +20% run and air speed for 3 seconds | Land with Momentum: spend 1, gain Haste for 3 s. | 8 | 8 | 15 | 10 | payoff: opens at depth 5 so a one-rule drive is never dead |
| icebound | Ice hits Chill the target (20% slower) for 3 seconds | Your hits Chill the target for 3 s. | 6 | 4 | 10 | 8 | applier on any hit: no ice-hit prerequisite |
| brittle | Hit a Chilled target: your later hits launch them 3% farther for 2 seconds | Hit_dealt: Curse for 2 seconds. | 7 | 6 | 14 | 5 | payoff: opens at depth 5 so a one-rule drive is never dead |
| reprisal | Perfect shield: take 25% less damage for 3 seconds (Guarded), and gain 1 Momentum | Perfect shield: Guarded for 3 s. | 8 | 4 | 14 | 6 | one effect: the free Momentum goes |
| cinder | Your hits deal 10% more damage to Burning targets | . | 3 | 2 | 9 | 1 | payoff: opens at depth 5 so a one-rule drive is never dead |
| shatter | Your hits deal 10% more damage to Chilled targets | . | 3 | 2 | 9 | 1 | payoff: opens at depth 5 so a one-rule drive is never dead |
| bastion | Land with Momentum: spend one stack to take 25% less damage for 2 seconds | Landing: Guarded for 2 seconds. | 8 | 7 | 14 | 5 | payoff: opens at depth 5 so a one-rule drive is never dead |
| renewal | Whenever you become Guarded (less damage taken): heal 2% | Status_applied: heal 2%. | 5 | 5 | 9 | 3 | payoff: opens at depth 5 so a one-rule drive is never dead |
| rush | Hit while moving fast: gain Momentum for 4 seconds | Hit_dealt: Momentum for 4 seconds. | 6 | 6 | 9 | 5 | payoff: opens at depth 5 so a one-rule drive is never dead |
| malice | Hit a Burning target: your later hits launch them 3% farther for 2 seconds | Hit_dealt: Curse for 2 seconds. | 7 | 6 | 14 | 5 | payoff: opens at depth 5 so a one-rule drive is never dead |
| clean_landing | L-cancel a landing after the aerial hit: Haste for 1.5 seconds. / You earn it by technique: a blue afterimage shows while it lasts. | L-cancel after a hit: Haste for 1.5 s. | 4 | 4 | 23 | 8 | tutorial line out |
| tech_guard | Tech: Guarded for 1 second. / You earn it by technique: a teal afterimage shows while it lasts. | Tech: Guarded for 1 s. | 4 | 4 | 17 | 5 | tutorial line out |
| combo_surge | Land a hit that makes a combo of at least 3: Haste for 0.8 seconds. / You earn it by technique: a red afterimage shows while it lasts. | 3rd hit of a combo: Haste for 0.8 s. | 10 | 6 | 27 | 9 | drop the Shock alternative trigger |
| combo_finish | Finish a combo of at least 3: heal 3%. | Finish a combo of 3+ hits: heal 3%. | 13 | 5 | 9 | 8 | drop the Shock and Curse alternative triggers |
| retaliation | When your armour absorbs a hit: your next hit crits for x1.4. | When armour absorbs a hit: your next hit crits (x1.4). | 7 | 4 | 12 | 10 | drop the Guarded alternative trigger (the bridge becomes its own optional piece, Riposte) |
| keen | Your hits crit 5% of the time. / Crits are rare: the engine has none until a modifier grants a chance. | Your hits crit 5% of the time. | 2 | 2 | 20 | 7 | engine line out; crit multiplier is the glossary x1.5 |
| brutal | Your hits crit 3% of the time. / Crits are rare: the engine has none until a modifier grants a chance. | Your hits crit 3% of the time; crits gain +0.25x. | 2 | 3 | 20 | 10 | BUG: today the text hides the multiplier gain (the only reason to take it); the line now states both |
| ruthless | Your aerial hits crit 12% of the time (x1.6). / Crits are rare: the engine has none until a modifier grants a chance. | Your aerial hits crit 15% of the time. | 3 | 2 | 22 | 8 | multiplier moves to the glossary (x1.5); one number |
| finishing | Your hits crit 20% of the time (x1.75), but only on a target above 100% damage. / Crits are rare: the engine has none until a modifier grants a chance. | Hits on a target above 100% crit 25% of the time. | 4 | 3 | 29 | 11 | multiplier moves to the glossary (x1.5); chance 25% |
| critical_flow | Land a crit: Haste for 0.8 seconds. / A crit flashes an impact frame and a tracer on the hit. | Land a crit: Haste for 0.8 s. | 4 | 4 | 19 | 7 | tutorial line out |
| trailing | While moving fast, you leave afterimages | . | 2 | 2 | 6 | 1 | payoff: opens at depth 5 so a one-rule drive is never dead |
| echoes | Your aerial attacks repeat a moment later at reduced damage (more copies at higher tiers) | Aerial attacks repeat once, weaker. | 1 | 1 | 15 | 5 | shorter |

**The 30 keystones after the proposal** (the owner's "pool of about 30"):

| id | name | when | the rule (one line) | the drawback (one line) | score | passes |
|---|---|---|---|---|---|---|
| pyromancer | Pyromancer | always | All your attacks become fire | Drawback: ice hits against you deal 60% more damage | 3 | yes |
| frozen_oath | Frozen Oath | always | All your attacks become ice | Drawback: fire hits against you deal 60% more damage | 3 | yes |
| smash_doctrine | Smasher's Creed | always | Smash attacks deal 60% more damage | Drawback: you run 15% slower | 4 | yes |
| aerial_doctrine | Skybreaker | always | Aerial attacks deal 50% more damage | Drawback: you jump 20% lower | 4 | yes |
| bloodlust | Bloodlust | ko_dealt | Knock out a fighter: heal 20%. | Drawback: you lose 3 damage points each time. | 5 | yes |
| last_stand | Last Stand | interval | On your last stock you are always Guarded. | Drawback: you lose 2 damage points every second. | 6 | yes |
| sprinter | Sprinter's Pact | always | Run and air speed +30%. | Drawback: you are launched 20% farther. | 4 | yes |
| hit_and_run | Hit and Run | hit_dealt | Every hit you land gives Haste for 2 s. | Drawback: you lose 1 damage point per hit. | 6 | yes |
| perpetual_motion | Perpetual Motion | landing | Every landing gives Haste for 4 seconds | Drawback: every landing costs you 1 damage point | 6 | yes |
| bulwark | Bulwark | always | Launch you take -35%. | Drawback: you run 20% slower. | 4 | yes |
| iron_resolve | Iron Resolve | interval | You are always Guarded: 25% less damage and 15% less launch taken | Drawback: you cannot hold Momentum | 7 | yes |
| retribution | Retribution | hit_taken | When you are hit, the attacker is Marked for 3 s. | Drawback: you lose 1 damage point each time. | 6 | yes |
| parry_master | Parry Master | perfect_shield | Perfect shield: Guarded for 5 s. | Drawback: you lose 1 damage point each time. | 6 | yes |
| skyborne | Skyborne | always | Jump and air jump height +50%. | Drawback: you are launched 25% farther. | 4 | yes |
| dive_bomber | Dive Bomber | always | Aerial attacks launch 30% farther | Drawback: you run 20% slower | 4 | yes |
| pandemic | Pandemic | always | Statuses you cause last 60% longer | Drawback: damage you deal -15% | 4 | yes |
| opportunist | Opportunist | hit_dealt | Hit a target with a status: Mark it for 2.5 s. | Drawback: you lose 1 damage point per hit. | 8 | yes |
| plague_bearer | Plague Bearer | hit_dealt | Every hit sets the target Burning (stacks to 3). | Drawback: you lose 1 damage point per hit. | 6 | yes |
| deep_freeze | Deep Freeze | hit_dealt | Every hit Chills the target for 4 s. | Drawback: you lose 1 damage point per hit. | 6 | yes |
| everburn | Everburn | always | Burning targets take 50% more damage. | Drawback: you take 15% more damage. | 5 | yes |
| echo_weaver | Echo Weaver | always | While Hasted, your attacks repeat twice at half damage | Drawback: damage you deal -10% | 4 | yes |
| fury | Fury | hit_taken | When you are hit, gain Haste for 3 s. | Drawback: you lose 1 damage point each time. | 6 | yes |
| wavedasher | Wavedasher | wavedash | Wavedash: super armour for 6 frames. | Drawback: you lose 2 damage points each time. | 5 | yes |
| clean_lander | Clean Lander | lcancel_hit | L-cancel after a hit: Haste for 2 s. | Drawback: you lose 1 damage point each time. | 6 | yes |
| juggernaut | Juggernaut | always | You do not flinch from hits that deal under 6 damage | Drawback: you cannot run | 3 | yes |
| executioner | Executioner | always | Hits on a target above 100% damage always crit for double | Drawback: damage you deal -10%, and no hit below 100% can crit | 5 | yes |
| combo_conduit | Combo Conduit | combo | 3rd hit of a combo: your next hit crits (x1.6). | Drawback: you lose 1 damage point each time. | 7 | yes |
| aerialist | Aerialist | always | You have five air jumps | Drawback: you cannot shield | 2 | yes |
| conductor | Conductor | hit_dealt | Electric hits Shock the target and chain it onward. | Drawback: you lose 1 damage point per electric hit. | 7 | no (the one deliberate two-effect keystone) |
| gambler | Gambler | always | Every hit has a 35% chance to deal double or triple damage | Drawback: all your hits deal 20% less damage first | 4 | yes |

New pieces: none are required. One optional piece, "Riposte" (when hit while Guarded: your next hit crits), would keep the Guard-to-crit bridge that Retaliation loses by dropping its alternative trigger; I would not add it (join before adding).

### 4c. How many rules, how many keystones

**Rules per drive.** [JUDGEMENT] Never more than two. One below effective depth 5; two from depth 5 on; no white extra. Two rules read as "always" plus "when": the roller already alternates a standing rule (prefix) and a trigger rule (suffix) from a seeded start, so a two-rule drive is one of each. Rarity stops meaning "more rules": magic and rare both carry two (rare is the better tier, which the merge already models; my simulation treats rare like magic, so it slightly understates the power of a rare).

| effective depth | rules per drive (max) | drive slots | keystones held (allowance) |
|---|---|---|---|
| 0 to 4 | 1 | 4 | 1 (random at run start) |
| 5 to 9 | 2 | 5 | 2 |
| 10 to 14 | 2 | 6 | 3 |
| 15 to 27 | 2 | 6 | 4 |
| 28 to 40 | 2 | 6 | 5 |
| 41 to 53 | 2 | 6 | 6 |
| 54 and on | 2 | 6 | 7 (+1 per 13) |

Today for comparison: 1 rule to depth 2, 2 to 5, 3 to 9, 4 after; +1 for a white drive from depth 3; allowance 1 + depth/5 without a ceiling.

**Keystones.** One at the start, three offered at a time, one picked, as now. The allowance follows the table: +1 at depth 5, 10 and 15, then one per New Game+ lap. [OWNER] "we can just gain as many as we want, as long as we get far enough into the game": the number still grows without a ceiling, only slower after the fourth; it is a decision (6.2 #3) because it is also the biggest lever on late power (section 5).
**Does a keystone need splitting into "a rule" and "its drawback"?** Not into separate pieces: keeping them on one card is the point of a keystone (the trade is the build). It is split into **two lines each with a limit** (R8) and the drawback is drawn from a seven-item list (R9), so a player learns seven prices once and every keystone card is "one rule, one price". Splitting a keystone into several small stacking pieces is what drives already are; a keystone that stacked would be a drive. (An alternative, choosing the price separately, is shape C2 in section 6.1.)

### 4d. Statuses: vocabulary and what is private

| status | role after the proposal | why |
|---|---|---|
| **Burn** | core | applied by 2 pieces (Kindling, Plague Bearer), read by 4 payoffs; a clear damage-over-time identity |
| **Chill** | core | applied by 2 (Icebound, Deep Freeze), read by 2 payoffs |
| **Haste** | core | the most-fed status (9 appliers after the cuts); one meaning: you are fast |
| **Guarded** | core | 7 appliers; one meaning: you take less |
| **Marked** (today "Curse") | core, rename | applied only to a target (4 appliers); never a price on yourself; read by nothing: its effect is the number it carries (later hits launch farther) |
| **Momentum** | **a counter, not a status look** | stacks to 5, spent on landing (Crosswind, Bastion); today 8 appliers and 2 readers and no effect of its own; shown as 1 to 5 orbs (pass 2) |
| **Shock** | private to the electric theme | applied by Conductor (and its chain); native extra hitstun; read by nothing |

Five statuses with a look, one counter, one private status: **7 words of vocabulary, ever**. Status table after the proposal:

| status | what it does | applied by (n; * = keystone; @ who gets it) | of those, a PRICE on yourself | read by (n) | removed by | pieces touching it |
|---|---|---|---|---|---|---|
| burn | damage over time on the target (tier damage per second; stacks to 3 for Plague Bearer) | 2 (kindling@target, plague_bearer@target*) | - | 4 (pyre, cinder, malice, everburn) | cleansing | 7 |
| shock | the target's next hit taken has extra hitstun (native) | 2 (conductor@chain*, conductor@target*) | - | 0 | - | 1 |
| chill | -20% run and air speed | 2 (icebound@target, deep_freeze@target*) | - | 2 (brittle, shatter) | cleansing | 5 |
| curse | target's later hits-taken launch farther by the stored bonus | 4 (brittle@target, malice@target, retribution@target*, opportunist@target*) | - | 0 | cleansing | 5 |
| haste | +20% run and air speed | 9 (crosswind@self, ledge@self, hit_and_run@self*, perpetual_motion@self*, fury@self*, clean_lander@self*, clean_landing@self, combo_surge@self, critical_flow@self) | - | 3 (rush, echo_weaver, trailing) | - | 12 |
| guarded | -25% damage taken and -15% launch taken | 7 (reprisal@self, bastion@self, shelter@self, last_stand@self*, iron_resolve@self*, parry_master@self*, tech_guard@self) | - | 1 (renewal) | - | 8 |
| momentum | stacks to 5; a stored resource only landing/rush rules read | 2 (updraft@self, rush@self) | - | 2 (crosswind, bastion) | crosswind, bastion, iron_resolve | 5 |

### 4e. Synergies and archetypes: do not announce assembly

[JUDGEMENT] An assembled build is not an event. Today the game raises a toast for something the player did not do at that moment (nine archetypes, a roles table the player never saw), and the underlying fact (a status a piece gives is a status another piece reads) is already visible in the text if one status has one word.

1. **Remove the "<archetype> assembled" toast and the in-match link flash/emblem pill** from the match. Keep the grid marks on the reward and bag screens (a link between two pieces, "advances / completes" on an offer): that is where a player has time to read them.
2. **A combination is understood from its parts**: a payoff names the status its partner gives in the same word ("Hit a Burning target: ..." beside "Your hits set the target Burning ..."); the strip shows one line of **theme counts** instead of a banner ("Burn 3  Haste 2  Crit 2": held rules by the status or element they touch). That line is cheap, always true and replaces nine archetype announcements.
3. The archetype table stays as data for connecting offers and the grid; after the cuts all nine remain completable (`vocab_check.txt`): momentum 9 to 6 pieces, guard 10 to 8, technique 4 to 3, haste 12 to 11, crit 8 to 7, armour 5 to 4.
4. Payoffs open at depth 5 (R10), so a one-rule drive is never a payoff with nothing to pay off. Kindling and Icebound no longer need a fire or ice hit (they apply on any hit), which removes the three-piece chain "Burning, Kindling, Cinder" for one effect. The three element drives (Burning, Frosted, Charged) stay as the colour of your hits.

### 4f. What the player is told, and when (naming)

* **Names.** A drive is named by its colour and its rules, never by grammar: one rule `Green Drive: Kindling`, two rules `Green Drive: Kindling + Updraft`; a unique is its own name. No prefix/suffix English (that removes bug 1 of section 3). The card shows two lines, labelled by kind: `Always: ...` for a standing rule, `When: ...` for a trigger.
* **Rule text** is one line per rule, with the sentence limits of 4a; the status's own numbers are in a glossary reachable from the detail panel.
* **Starter panel** (one drive, one keystone): keep, it is one panel.
* **Milestones**: one toast at depth 5 and 10, not three: "Depth 5: fifth slot, second keystone at the next clear, drives tier 2".
* **Drops and merges**: keep the pickup and merge cards.
* **The generic "Modifier!" flash**: replace by the piece's own mark (pass 2).
* **Technique hint**: keep the once-per-run line, shorten it to one sentence.
* **Detail on demand**: the reward and bag screens keep the full lines for the focused drive only (already how they work).

### 4g. A budget the visual pass can rely on

The bounds in column 2 are my proposal [JUDGEMENT]; the other two columns are [MEASURED].

| budget | proposed bound | measured after the proposal (typical build, eff. 30 to 40) | today |
|---|---|---|---|
| distinct rules held (drive rules + keystones) | 12 until effective depth 15 (6 x 2 and at most 4 keystones would be 16: the drive slots are 4 to 6), 19 at most (6 drives x 2 + 7 keystones) | 11.3 mean | 14.9 mean; the owner's build 17 distinct plus 11 dead copies |
| rule lines on screen in the bag | 32 at most (6 base lines + 12 drive rules + 7 keystones x 2) | 23 | 30; owner build 55 |
| statuses with a look | 5, plus 1 counter and 1 private | 4.5 touched | 6.3 touched (7 vocabulary) |
| statuses live on one fighter at once | **3** (the visual pass orders them; a fourth is suppressed, never stacked) | not measured | not bounded |
| pieces that fire per hit (live) | 3 as a design target | 3.0 mean | 3.9 |
| trigger kinds in one build | 5 | 4.1 | 6.0 |
| announcements at once | 1 toast, never queued | - | 3 queued; 4 archetype toasts |
| words in a rule line | 14 (12 target) | 150 words per whole build | 258 |

The pieces the second pass has to give looks to (after the proposal), by what the player would see change:

| what the player would see change | pieces after the proposal |
|---|---|
| gives a status (the status look) | 27 |
| element of your hits (fire / ice / electric) | 11 |
| a stat number (no visible event) | 8 |
| crit chance or size (no event until a crit lands) | 6 |
| a number on hits against a status | 4 |
| heal | 4 |
| echo copies | 4 |
| arms the next hit as a crit | 3 |
| other | 2 |
| armour for a moment | 2 |
| armour (always on) | 1 |

[JUDGEMENT] So the list is short: **5 status looks, 1 counter (Momentum orbs), 1 private status (Shock), 3 element looks (fire, ice, electric), 4 moment marks** (a crit lands, the next hit is armed to crit, armour absorbs, a price is paid: the Bleed tick, new and distinct from any status), **1 heal, 1 echo (repeat) look, and one emblem per keystone** (30, drawn only while that keystone fires, per-hit ones last). Passive stat rules (about 30 pieces) get **no live look**; they live in the bag and the strip only. Per-hit pieces (live list after the proposal: brittle, combo_conduit, combo_finish, combo_surge, conductor, critical_flow, deep_freeze, fury, hit_and_run, icebound, kindling, malice, opportunist, plague_bearer, retribution, rush, updraft) are the ones that need the smallest, quietest mark, because they fire many times a fight.

### 4h. Can it all be data? The vocabulary check [MEASURED, `vocab_check.txt`]

| | today | proposed |
|---|---|---|
| pieces | 86 | 72 pieces: 14 prefix, 22 suffix, 6 unique, 30 keystone |
| triggered effect ops used (the native evaluator's 12 are: status, stacks, remove_status, heal, damage, emit, clank_damage, armor, intangible, interrupt, crit_next, chain_status: my reading of the scoping study's list) | 9 | 8 (`status`, `damage`, `heal`, `remove_status`, `armor`, `crit_next`, `chain_status`, `clank_damage`) |
| condition kinds used (of the 21 in `mod_schema.lua`) | 9 | 7 |
| passive ops | value, convert, versus-status, crit, armor, echo, air_jumps, restrict | the same |
| records that need an op, condition or trigger outside that vocabulary | - | **none** |
| passive pieces / online-safe now (`engine:online_safe`) | 38 / 33 | 34 / 30 |
| triggered pieces a native evaluator must run | 48 | **38** |

Flags: none of the proposed pieces needs a Lua callback. Bleed is the existing `damage` op on self; "Marked" is a rename of an existing status; the crit multiplier x1.5 becomes a glossary constant (the `crit` op already has a default multiplier). Dropping `also` removes the only multi-trigger records. The native evaluator's job shrinks by 10 records and needs 8 of its 12 ops (`stacks`, `emit`, `interrupt`, `intangible` are not used by any proposed piece).

---

## 5. What it does to balance and to the rest

**Power per depth [MEASURED, offline, `sim_power.lua`].** Assumptions, stated: every surviving piece keeps **today's numbers** (except the few listed in 4b); strength is `mod_budget.build` as the mod computes it (strength v2, the default tuning, an x factor over an empty build, the HUD shows +%); the picker is the strength-greedy stand-in of the earlier synergy lane; every stage is won; rare drives are treated like magic drives (2 rules, same tiers). "After" is the full proposal (72-piece pool, two rules, no white extra, new allowance). Median over 300 runs (Classic) and 150 (Adventure).

Classic:

| eff. depth band | strength today: median (p25-p75) | keystones today | strength after: median (p25-p75) | keystones after | after / today | drive curve only / today | full pool + today's keystone allowance / today |
|---|---|---|---|---|---|---|---|
| 1-3 | x1.62 (1.39-1.94) | 1.0 | x1.63 (1.39-1.90) | 1.0 | 1.00 | 1.00 | 1.00 |
| 4-7 | x2.47 (1.95-3.25) | 2.0 | x2.37 (1.84-3.07) | 2.0 | 0.96 | 0.98 | 0.96 |
| 8-12 | x3.33 (2.47-4.71) | 2.0 | x3.09 (2.35-4.25) | 2.0 | 0.93 | 0.98 | 0.93 |
| 13-19 | x7.40 (5.02-11.49) | 4.0 | x6.21 (4.41-8.99) | 4.0 | 0.84 | 0.94 | 0.84 |
| 20-29 | x21.68 (12.78-39.03) | 5.0 | x11.58 (6.68-18.12) | 4.0 | 0.53 | 0.92 | 0.77 |
| 30-40 | x77.81 (43.66-139.90) | 7.0 | x27.28 (14.66-47.28) | 5.0 | 0.35 | 0.94 | 0.65 |

Adventure:

| eff. depth band | strength today: median (p25-p75) | keystones today | strength after: median (p25-p75) | keystones after | after / today | drive curve only / today | full pool + today's keystone allowance / today |
|---|---|---|---|---|---|---|---|
| 1-3 | x1.58 (1.41-1.90) | 1.0 | x1.60 (1.34-1.89) | 1.0 | 1.01 | 1.00 | 1.01 |
| 4-7 | x2.30 (1.85-3.08) | 2.0 | x2.25 (1.84-2.93) | 2.0 | 0.98 | 0.99 | 0.98 |
| 8-12 | x3.37 (2.56-4.45) | 3.0 | x3.05 (2.32-4.29) | 3.0 | 0.91 | 0.98 | 0.91 |
| 13-19 | x5.70 (4.19-8.13) | 4.0 | x5.17 (3.62-6.88) | 4.0 | 0.91 | 0.96 | 0.91 |
| 20-29 | x19.32 (12.27-29.90) | 6.0 | x9.48 (6.32-15.50) | 4.0 | 0.49 | 0.98 | 0.71 |
| 30-40 | x66.35 (40.76-118.46) | 8.0 | x24.53 (11.27-44.30) | 5.0 | 0.37 | 1.00 | 0.70 |
| 41-70 | x859.53 (343.15-1886.37) | 12.0 | x216.75 (84.12-418.16) | 7.0 | 0.25 | 0.97 | 0.59 |

Reading it [MEASURED]: the **drive changes alone cost at most 8% of median build strength** (second last column), and nothing before effective depth 5. The other pool changes (cuts, payoffs at depth 5, the price swaps) bring it, with today's keystone allowance, to 0.96 at depth 4 to 7, 0.93 at 8 to 12 and 0.84 at 13 to 19 (last column). The big drop later (strength 0.53 at depth 20 to 29, 0.35 at 30 to 40) is **the keystone allowance schedule**, not the readability changes: with today's allowance the full proposal is 0.77 and 0.65 of today. The late numbers are dominated by the tier curve (tier grows every 5 depth, 1.45x per tier past tier 3): the earlier analysis found 3.5x of the median 25-stage strength is the tier curve itself, so "absurdly strong late" is already present, and I do not claim the new late numbers are better balanced, only smaller. The owner's granted build: cutting each drive to its first two rules is 0.56 of today, and holding 4 keystones instead of 6 is 0.47 (`owner_build.txt`).

* **Opponents** use the same pool, roll and curve (`foe_roll`: a build rolled against the player's actual strength times an edge of +1% per depth, capped at +25%, plus a held-drives cap). They inherit the two-rule cap, the cuts and the new allowance; the +25% cap is unchanged. Because the edge is relative to the player's own strength, a smaller number on both sides keeps the exchange the same; I did not run fights, so "the same" is by construction, not measured. Opponent plates (one line per modifier) get shorter with the pool. The earlier analysis' finding that opponents roll technique pieces a CPU does not perform is unchanged.
* **Co-op** (`COOP.md`): one host per seat with its own bag, slots and keystones; the same module serves both, so the curve, cuts and price list apply per seat. Cross-seat synergy (a payoff of P2 reads a status P1 applied) is unaffected, since statuses stay per victim. Not run.
* **Online** (`ONLINE.md`, the scoping study): see 4h. Every proposed piece is a data record over the existing vocabulary; the set of online-safe passive pieces goes 33 to 30 and the triggered pieces the native evaluator must reproduce goes 48 to 38. The record digest and pool digest change (the pool changes), so a build record or a set started before the change is not valid after it; a pool cut is a protocol-level change like any pool change.
* **Tests that encode today's design and would change** (the Lua tests under `melee/pc/tests/`; I did not run them against the proposal): `envoy_loot_pacing` (the affix-count table 1/2/3/4, white +1, "keystone allowance has no ceiling", "filled slots within 12% of the pre-curve game", the `' of the '` name assertion); `envoy_drive_loot` ("forced rarity" expects 1/2/4 affixes plus white; the unique/white count checks; the 4-affix names; duplicate-id tier tests); `envoy_drive_merge` (a merge never adds a modifier: unchanged, plus a new cross-colour merge test); `envoy_keystones` (thirty keystones and the exact pool, drawbacks via status on self, the wording of every drawback line); `envoy_drive_text` (every modifier has plain lines; the new lines); `envoy_synergy` (the bridges test expects the Shock and Cursed readers and Brutal's own chance as built; the archetype pieces list); `envoy_modifiers_pool`, `envoy_budget`, `envoy_power_curve` (golden tiers, opponent contexts, the "three-keystone witness"); `envoy_online_build` ("38 passive records, 33 online-safe" becomes 34 and 30); `envoy_online` and `envoy_codec` digests (pool digest changes). Native tests are not touched except where they pin a pool digest.
* **Saved runs.** A saved bag holding a cut id (14 ids: `heavy`, `featherweight` and 12 keystones) would fail validation (`unknown affix`); the ids that stay but change numbers (Ruthless, Finishing, Kindling and others) keep validating, and a saved 3- or 4-affix drive keeps validating through the legacy count path in `drive_loot:validate` (the old shape is accepted). So the migration is: map each cut id to nothing (drop it, with a notice) or to its nearest survivor; a decision (6.2 #11). Run state saved by the host stores records by id, so a record's text changing needs nothing.
* **Menus.** Fewer lines per drive (rare: 6 to 3), one-line names, a bag of four, one theme-count line instead of banners: it moves the same direction as "the menus already fairly overwhelming".

---

## 6. Alternative shapes and the owner's decisions

### 6.1 Three shapes for the whole thing

| | **A: one rule per drive** | **B: at most two rules per drive (recommended)** | **C1: one rule plus an upgrade level** | **C2: rules on separate chips** |
|---|---|---|---|---|
| shape | every drive is one rule; depth gives more slots (4 to 10) | one rule early, two from depth 5, a standing rule and a trigger rule | one rule per drive; "rare" is a higher tier, merging raises the tier (already in the mod) | a drive is a socket; rules are small items slotted into it; the drive gives the colour base |
| rules in a full build (6 drives) | 6 to 10 | up to 12 | 6 | 12 or more |
| reading | simplest | one "always" and one "when" per drive; names stay short | simplest and most legible per drive, but one idea per slot caps variety | smallest atoms, most items |
| inventory | needs more slots to keep power: the opposite of "stop inventory bloat" | unchanged (4 slots to 6, bag of 4) | unchanged | **a second item kind**: more to hold, drop, merge, show |
| measured / reasoned | typical builds already average 1.15 rules per drive, so A matches today's typical build; power is kept only by adding slots | drive-only power cost at most 8% (section 5) | roughly A with fewer slots; power falls to about 0.5 for builds that today stack rares (owner build: 0.56) | not simulated |
| risk | menus grow | very little: it caps the rare tail and leaves the average | fewer builds possible; "rare" feels less special | the largest rebuild: roller, bag, merge, screens, save, native build record |
| recommendation | no | **yes** | the fallback if two rules still read as too much in play | no (it adds the bloat the owner named) |

Keystone variants: **K1 (recommended)** one card, rule and price fixed together, price from the list; **K2** the price is picked separately when taking the keystone (rule from the 30, price from 2 or 3 offered): halves the authoring (about 30 rules plus 7 prices instead of 42 baked cards) and makes the same rule feel different, but adds a second choice on the keystone screen and needs a small engine change (a keystone becomes two records). **K3** keystones become small stacking pieces: no, that is a drive.

### 6.2 Decisions only the owner can make (each with my suggested answer)

| # | question | suggested answer |
|---|---|---|
| 1 | At most two rules on any drive, one below depth 5 (no white extra)? | Yes. It caps the rare tail (4.2 rules, 50 words) and costs at most 8% of median power. |
| 2 | Cut the keystone pool from 42 to 30 with the list in 4b (and drop Heavy and Featherweight)? | Yes; veto any single cut and I would keep it. |
| 3 | After the fourth keystone, one more per New Game+ lap (13 effective depth) instead of one per 5? | Yes if "far enough into the game" means laps; it keeps growth without a ceiling and roughly halves late strength. If he wants 12 keystones at depth 56, keep today's schedule and accept that the typical build then holds 11 keystone cards. |
| 4 | The seven prices and no status as a price? | Yes: it frees Chill and Curse from meaning "I paid". Bleed for triggered keystones is crude (a rare trigger such as a KO makes a small cost); the budget lane tunes it. |
| 5 | No "assembled" toast and no in-match link flash; grid marks and a theme-count line instead? | Yes. |
| 6 | A gained drive whose rule you already hold (any colour) merges into it instead of being dead? | Yes: otherwise a rule on a second drive stays inert (11 of 22 in the recorded build). |
| 7 | Kindling and Icebound apply on any hit (no fire or ice hit needed; the numbers will be lowered)? | Yes; it deletes a three-piece chain. Needs a balance pass: Burn per hit is the strongest thing in the pool. |
| 8 | Payoffs (11 ordinary pieces) open at depth 5? | Yes. |
| 9 | Rename Curse to Marked? | Yes (internal id stays `curse`; saves are unaffected). |
| 10 | Momentum becomes a counter shown as orbs, not a status look? | Yes: it matches the orbit-stack idea he liked and removes a status nothing reads. |
| 11 | Saved runs holding a cut piece: drop it with a notice, or keep the old pool alive until that run ends? | Drop with a notice; a pool digest already forks saves and online sets, and the run still has its other pieces. |
| 12 | The crit multiplier is a fixed x1.5 except Brutal, Gambler and Executioner? | Yes (one number per crit piece). |
| 13 | Keep the six uniques as they are (they already read as rule plus price)? | Yes. |
| 14 | Opponent plates: show only the opponent's keystones (name + one line) and a count of drive rules? | Yes, but it is a pass 2 call. |

Not decided by this pass: the numbers of every kept piece (they are today's), Kindling, Icebound, Plague Bearer and Brutal's real tuning, and the looks.

---

## 7. What I did not do, and the limits [JUDGEMENT]

* No game ran. Nothing here was seen on screen or timed in play; "reads at a glance" is measured as words, counts and score, not by a player.
* The picker is a stand-in (strength-greedy), the same one the earlier synergy lane used; the owner's real choices differ, which is why the owner's own build is scored separately.
* The recorded logs hold log lines, not the player's screen: toasts, flashes and per-hit rule fires are mostly unlogged, so the announcement counts are lower bounds.
* The CPU performs techniques far less than a person; nothing here changes that finding.
* The strength numbers late in a run are driven by the tier curve; they are good for ratios, not for judging how strong a late build feels.
* The bite-rule limits (14 words, 2 numbers) are tuned to today's text, which restates status numbers; the proposed 12 words and 1 number per piece is a target that the glossary change makes possible, not something this pass tested.
* The proposal text for each rewritten piece is mine; the owner and the visual lane may want to word them.

---

## Appendix A: every piece, as the mod defines it today [MEASURED]

Columns: `when` is the trigger (`always` = a standing rule; `OR` lists alternative triggers); `if` the conditions; `then` the effects (`$name` is a tier number); `numbers` the three tier tables; `drawback` the cost text; `score`, `words`, the bite verdict and the rule text exactly as the player reads it at tier 1 (`/` separates its lines). Machine-readable: `pieces.csv`, `pieces.json`.

### A1. Ordinary drive pieces (38)

| id | name | slot | from depth | when | if | then (effects) | numbers: tier 1 / 2 / 3 | drawback (cost text, or the effect that is the drawback) | statuses | tags | budget family | score | words | passes the bite rule? | rule text exactly as the player reads it (tier 1) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kindling | Kindling | suffix | 0 | hit_dealt | tag=fire | status status=burn subject=target duration=duration amount=damage | damage=3 duration=180 / damage=3.75 duration=225 / damage=4.5 duration=270 | - | burn | fire burning | sustain | 6 | 13 | yes | Fire hits set the target Burning for 3 seconds (3 damage every second) |
| pyre | Pyre | prefix | 0 | always | - | versus-status status=burn change{launch=ratio} match{} | bonus=0.08 ratio=1.08 / bonus=0.1 ratio=1.1 / bonus=0.12 ratio=1.12 | - | burn | burning damage | launch_dealt | 3 | 7 | yes | Your hits launch Burning targets 8% farther |
| burning | Burning | prefix | 0 | always | - | convert change{element=fire} match{move=smash} |  /  /  | - | - | smash fire | conversion | 1 | 4 | yes | Smash attacks become fire |
| charged | Charged | prefix | 0 | always | - | convert change{element=electric} match{move=aerial} |  /  /  | - | - | aerial electric | conversion | 1 | 4 | yes | Aerial attacks become electric |
| feasting | Feasting | suffix | 0 | ko_dealt | target_status=any | heal subject=self amount=heal | heal=10 / heal=12.5 / heal=15 | - | any | healing | sustain | 5 | 11 | yes | Knock out a target that has a status effect: heal 10% |
| updraft | Updraft | suffix | 0 | hit_dealt | tag=aerial | status status=momentum subject=self duration=duration amount=1 | duration=300 / duration=375 / duration=450 | - | momentum | aerial momentum | momentum | 6 | 10 | yes | Aerial hits build Momentum (up to 5) for 5 seconds |
| crosswind | Crosswind | suffix | 0 | landing | self_status=momentum | remove_status status=momentum subject=self count=1; status status=haste subject=self duration=duration amount=1 | duration=180 / duration=225 / duration=270 | - | haste momentum | momentum hasted | momentum speed cleanse | 8 | 15 | no: words>14 | Land with Momentum: spend one stack for +20% run and air speed for 3 seconds |
| icebound | Icebound | suffix | 0 | hit_dealt | tag=ice | status status=chill subject=target duration=duration amount=1 | duration=180 / duration=225 / duration=270 | - | chill | ice chilled | speed | 6 | 10 | yes | Ice hits Chill the target (20% slower) for 3 seconds |
| brittle | Brittle | suffix | 0 | hit_dealt | target_status=chill | status status=curse subject=target duration=duration amount=bonus | bonus=0.025 duration=120 / bonus=0.03125 duration=150 / bonus=0.0375 duration=180 | - | chill curse | chilled cursed | launch_taken | 7 | 14 | yes | Hit a Chilled target: your later hits launch them 3% farther for 2 seconds |
| reprisal | Reprisal | suffix | 0 | perfect_shield | - | status status=guarded subject=self duration=duration amount=1; status status=momentum subject=self duration=duration amount=1 | duration=180 / duration=225 / duration=270 | - | guarded momentum | guarded momentum | damage_taken launch_taken momentum | 8 | 14 | no: effects>1; numbers>2 | Perfect shield: take 25% less damage for 3 seconds (Guarded), and gain 1 Momentum |
| frosted | Frosted | prefix | 0 | always | - | convert change{element=ice} match{move=smash} |  /  /  | - | - | ice chilled | conversion | 1 | 4 | yes | Smash attacks become ice |
| heavy | Heavy | prefix | 0 | always | - | versus-status change{launch=ratio} match{move=any}; value key=run_speed value=0.85 | ratio=1.05 / ratio=1.062 / ratio=1.075 | value:speed: | - | damage momentum | launch_dealt speed | 4 | 9 | no: drawback on an ordinary drive | Your hits launch targets 5% farther / Run speed -15% |
| featherweight | Featherweight | prefix | 0 | always | - | value key=jump_height value=ratio; value key=knockback_taken value=1.1 | ratio=1.15 / ratio=1.188 / ratio=1.225 | value:launch_taken: | - | aerial momentum | jump launch_taken | 4 | 7 | no: drawback on an ordinary drive | Jump height +15% / Launch you take +10% |
| lingering | Lingering | prefix | 0 | always | - | value key=status_duration value=ratio | ratio=1.2 / ratio=1.25 / ratio=1.3 | - | - | burning chilled hasted | status_duration | 2 | 7 | yes | Status effects you cause last 20% longer |
| cinder | Cinder | prefix | 0 | always | - | versus-status status=burn change{percent_damage=ratio} match{} | ratio=1.1 / ratio=1.125 / ratio=1.15 | - | burn | burning damage | damage_dealt | 3 | 9 | yes | Your hits deal 10% more damage to Burning targets |
| shatter | Shatter | prefix | 0 | always | - | versus-status status=chill change{percent_damage=ratio} match{} | ratio=1.1 / ratio=1.125 / ratio=1.15 | - | chill | chilled damage | damage_dealt | 3 | 9 | yes | Your hits deal 10% more damage to Chilled targets |
| ledge | Ledge | suffix | 0 | ledge_grab | - | status status=haste subject=self duration=duration amount=1 | duration=180 / duration=225 / duration=270 | - | haste | hasted momentum | speed | 5 | 11 | yes | Grab a ledge: +20% run and air speed for 3 seconds |
| bastion | Bastion | suffix | 0 | landing | self_status=momentum | remove_status status=momentum subject=self count=1; status status=guarded subject=self duration=duration amount=1 | duration=120 / duration=150 / duration=180 | - | guarded momentum | guarded momentum | damage_taken launch_taken momentum cleanse | 8 | 14 | yes | Land with Momentum: spend one stack to take 25% less damage for 2 seconds |
| renewal | Renewal | suffix | 0 | status_applied | status=guarded | heal subject=self amount=heal | heal=2 / heal=2.5 / heal=3 | - | guarded | healing guarded | sustain | 5 | 9 | yes | Whenever you become Guarded (less damage taken): heal 2% |
| rush | Rush | suffix | 0 | hit_dealt | self_status=haste | status status=momentum subject=self duration=duration amount=1 | duration=240 / duration=300 / duration=360 | - | haste momentum | hasted momentum | momentum | 6 | 9 | yes | Hit while moving fast: gain Momentum for 4 seconds |
| shelter | Shelter | suffix | 0 | ledge_grab | - | status status=guarded subject=self duration=duration amount=1 | duration=120 / duration=150 / duration=180 | - | guarded | guarded healing | damage_taken launch_taken | 5 | 10 | yes | Grab a ledge: take 25% less damage for 2 seconds |
| malice | Malice | suffix | 0 | hit_dealt | target_status=burn | status status=curse subject=target duration=duration amount=bonus | bonus=0.025 duration=120 / bonus=0.03125 duration=150 / bonus=0.0375 duration=180 | - | burn curse | cursed burning | launch_taken | 7 | 14 | yes | Hit a Burning target: your later hits launch them 3% farther for 2 seconds |
| armoured | Damage resistant | prefix | 0 | always | - | value key=damage_taken value=ratio | ratio=0.92 / ratio=0.9 / ratio=0.88 | - | - | guarded | damage_taken | 2 | 4 | yes | Damage you take -8% |
| cleansing | Cleansing | suffix | 0 | interval | - | remove_status status=burn subject=self; remove_status status=chill subject=self; remove_status status=curse subject=self |  /  /  | - | burn chill curse | guarded | sustain speed launch_taken cleanse | 5 | 10 | yes | Every second, Burn, Chill and Curse on you wear off |
| clean_landing | of the Clean Landing | suffix | 5 | lcancel_hit | - | status status=haste subject=self duration=duration amount=1 | duration=90 / duration=120 / duration=150 | - | haste | hasted aerial technique | speed | 4 | 23 | no: words>14 | L-cancel a landing after the aerial hit: Haste for 1.5 seconds. / You earn it by technique: a blue afterimage shows while it lasts. |
| wave_edge | of the Wave | suffix | 6 | wavedash | - | crit_next multiplier=mult count=1 | mult=1.4 / mult=1.6 / mult=1.8 | - | - | critical technique | crit | 3 | 7 | yes | Wavedash: your next hit crits for x1.4. |
| shield_stance | of the Stance | suffix | 7 | perfect_shield | - | armor type=hit_count value=1 frames=frames | frames=90 / frames=120 / frames=150 | - | - | guarded technique | armor | 3 | 11 | yes | Perfect shield: armour that absorbs the next hit for 1.5 seconds. |
| tech_guard | of the Tech | suffix | 5 | tech | - | status status=guarded subject=self duration=duration amount=1 | duration=60 / duration=90 / duration=120 | - | guarded | guarded technique | damage_taken launch_taken | 4 | 17 | no: words>14 | Tech: Guarded for 1 second. / You earn it by technique: a teal afterimage shows while it lasts. |
| combo_surge | of the Combo | suffix | 6 | combo OR combo[combo_at_least=2;target_status=shock] | combo_at_least=3 | status status=haste subject=self duration=duration amount=1 | duration=45 / duration=60 / duration=75 | - | haste shock | hasted technique | speed | 10 | 27 | no: triggers>1; conditions>1; words>14 | Land a hit that makes a combo of at least 3: Haste for 0.8 seconds. / You earn it by technique: a red afterimage shows while it lasts. |
| combo_finish | of the Finish | suffix | 6 | combo_end OR combo_end[combo_at_least=2;target_status=shock] OR combo_end[combo_at_least=2;target_status=curse] | combo_at_least=3 | heal subject=self amount=heal | heal=3 / heal=4 / heal=5 | - | curse shock | healing technique | sustain | 13 | 9 | no: triggers>1; conditions>1; reads >1 status | Finish a combo of at least 3: heal 3%. |
| retaliation | of Retaliation | suffix | 8 | armor OR hit_taken[self_status=guarded] | armor_result=absorbed | crit_next multiplier=mult count=1 | mult=1.4 / mult=1.6 / mult=1.8 | - | guarded | critical guarded | crit | 7 | 12 | no: triggers>1; conditions>1 | When your armour absorbs a hit: your next hit crits for x1.4. |
| keen | Keen | prefix | 4 | always | - | crit chance=chance | chance=0.05 / chance=0.0625 / chance=0.075 | - | - | critical damage | crit | 2 | 20 | no: words>14 | Your hits crit 5% of the time. / Crits are rare: the engine has none until a modifier grants a chance. |
| brutal | Brutal | prefix | 6 | always | - | crit chance=0.03; crit multiplier=mult | mult=1.25 / mult=1.312 / mult=1.375 | - | - | critical damage | crit | 2 | 20 | no: words>14 | Your hits crit 3% of the time. / Crits are rare: the engine has none until a modifier grants a chance. |
| ruthless | Ruthless | prefix | 6 | always | - | crit chance=chance multiplier=mult | chance=0.12 mult=1.6 / chance=0.15 mult=1.7 / chance=0.18 mult=1.8 | - | - | critical aerial | crit | 3 | 22 | no: words>14 | Your aerial hits crit 12% of the time (x1.6). / Crits are rare: the engine has none until a modifier grants a chance. |
| finishing | Finishing | prefix | 7 | always | - | crit chance=chance multiplier=mult | chance=0.2 mult=1.75 / chance=0.25 mult=1.9 / chance=0.3 mult=2 | - | - | critical damage | crit | 4 | 29 | no: numbers>2; words>14 | Your hits crit 20% of the time (x1.75), but only on a target above 100% damage. / Crits are rare: the engine has none until a modifier grants a chance. |
| critical_flow | of Critical Flow | suffix | 6 | crit | - | status status=haste subject=self duration=duration amount=1 | duration=45 / duration=60 / duration=75 | - | haste | hasted critical | speed | 4 | 19 | no: words>14 | Land a crit: Haste for 0.8 seconds. / A crit flashes an impact frame and a tracer on the hit. |
| trailing | Trailing | prefix | 0 | always | - | echo status=haste match{move=aerial} | copies=1 / copies=2 / copies=3 | - | haste | hasted momentum | echo | 2 | 6 | yes | While moving fast, you leave afterimages |
| echoes | of Echoes | prefix | 0 | always | - | echo match{move=aerial} | copies=1 / copies=2 / copies=3 | - | - | aerial damage momentum | echo | 1 | 15 | no: words>14 | Your aerial attacks repeat a moment later at reduced damage (more copies at higher tiers) |

### A2. Keystones (42)

| id | name | slot | from depth | when | if | then (effects) | numbers: tier 1 / 2 / 3 | drawback (cost text, or the effect that is the drawback) | statuses | tags | budget family | score | words | passes the bite rule? | rule text exactly as the player reads it (tier 1) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pyromancer | Pyromancer | keystone | 0 | always | - | convert change{element=fire} match{move=any}; versus-status change{percent_damage=1.6} match{element=ice,incoming=true} |  | Hits with an original Ice element deal +60% damage to you. | - | keystone fire ice | conversion damage_taken | 3 | 14 | yes | All your attacks become fire / Drawback: ice hits against you deal 60% more damage |
| still_heart | Still Heart | keystone | 0 | status_applied | status=haste | remove_status status=haste subject=self; status status=guarded subject=self duration=duration amount=1 | duration=180 | You lose Haste movement bonuses. | guarded haste | keystone hasted guarded | speed damage_taken launch_taken cleanse | 6 | 15 | yes | Moving fast turns into taking less damage instead / Drawback: you cannot get a speed boost |
| frozen_oath | Frozen Oath | keystone | 0 | always | - | convert change{element=ice} match{move=any}; versus-status change{percent_damage=1.6} match{element=fire,incoming=true} |  | Original Fire hits against you deal +60% damage. | - | keystone ice chilled damage | conversion damage_taken | 3 | 14 | yes | All your attacks become ice / Drawback: fire hits against you deal 60% more damage |
| smash_doctrine | Smasher's Creed | keystone | 0 | always | - | convert change{percent_damage=1.6} match{move=smash}; value key=run_speed value=0.85 |  | Run speed -15%. | - | keystone smash damage | damage_dealt speed | 4 | 11 | yes | Smash attacks deal 60% more damage / Drawback: you run 15% slower |
| aerial_doctrine | Skybreaker | keystone | 0 | always | - | convert change{percent_damage=1.5} match{move=aerial}; value key=jump_height value=0.8 |  | Jump height -20%. | - | keystone aerial damage | damage_dealt jump | 4 | 11 | yes | Aerial attacks deal 50% more damage / Drawback: you jump 20% lower |
| bloodlust | Bloodlust | keystone | 0 | ko_dealt | - | heal subject=self amount=heal; status status=haste subject=self duration=duration amount=1; status status=curse subject=self duration=180 amount=0.1 | duration=180 heal=20 | Be launched 10% farther for 3 seconds. | curse haste | keystone hasted healing | launch_taken speed sustain | 9 | 22 | no: effects>1 | Knock out a fighter: heal 20% and gain Haste for 3 seconds / Drawback: you are launched 10% farther for the same time |
| last_stand | Last Stand | keystone | 0 | interval | last_stock=true | status status=guarded subject=self duration=90 amount=1; status status=haste subject=self duration=90 amount=1; damage subject=self amount=2 |  | On your last stock you lose 2 damage points every second. | guarded haste | keystone guarded hasted | damage_taken launch_taken speed sustain | 8 | 21 | no: effects>1; gives >1 status | On your last stock you are always Guarded and Hasted / Drawback: on your last stock you bleed 2 damage every second |
| sprinter | Sprinter's Pact | keystone | 0 | always | - | value key=run_speed value=1.35; value key=air_speed value=1.2; value key=knockback_taken value=1.2 |  | Launched 20% farther. | - | keystone hasted | launch_taken speed | 5 | 13 | yes | Run speed +35% and air speed +20% / Drawback: you are launched 20% farther |
| hit_and_run | Hit and Run | keystone | 0 | hit_dealt | - | status status=haste subject=self duration=duration amount=1; status status=momentum subject=self duration=duration amount=1; status status=curse subject=self duration=120 amount=0.05 | duration=120 | Launched 5% farther for 2 seconds after each hit. | curse haste momentum | keystone hasted momentum | launch_taken momentum speed | 9 | 24 | no: effects>1; drawback line>12 words | Every hit you land gives Haste and Momentum for 2 seconds / Drawback: each hit also makes you launched 5% farther for the same time |
| perpetual_motion | Perpetual Motion | keystone | 0 | landing | - | status status=haste subject=self duration=duration amount=1; damage subject=self amount=1 | duration=240 | Every landing costs 1 damage point. | haste | keystone hasted | speed sustain | 6 | 15 | yes | Every landing gives Haste for 4 seconds / Drawback: every landing costs you 1 damage point |
| banked_momentum | Banked Momentum | keystone | 0 | interval | - | status status=momentum subject=self duration=600 amount=1; status status=curse subject=self duration=90 amount=0.05 |  | You are always launched 5% farther. | curse momentum | keystone momentum | launch_taken momentum | 7 | 17 | yes | Every second you gain a Momentum stack (up to 5) / Drawback: you are always launched 5% farther |
| bulwark | Bulwark | keystone | 0 | always | - | value key=knockback_taken value=0.6; value key=damage_taken value=0.8; value key=run_speed value=0.75; value key=jump_height value=0.85 |  | Run speed -25% and jump height -15%. | - | keystone guarded | damage_taken jump launch_taken speed | 8 | 18 | no: effects>1; numbers>2; more than one drawback | Launch you take -40% and damage you take -20% / Drawback: you run 25% slower and jump 15% lower |
| iron_resolve | Iron Resolve | keystone | 0 | interval | - | status status=guarded subject=self duration=60 amount=1; remove_status status=momentum subject=self |  | You cannot hold Momentum. | guarded momentum | keystone guarded momentum | cleanse damage_taken launch_taken momentum | 7 | 17 | yes | You are always Guarded: 25% less damage and 15% less launch taken / Drawback: you cannot hold Momentum |
| retribution | Retribution | keystone | 0 | hit_taken | - | status status=curse subject=target duration=duration amount=bonus; status status=chill subject=self duration=120 amount=1 | bonus=0.08 duration=180 | You are Chilled for 2 seconds. | chill curse | keystone cursed chilled | launch_taken speed | 9 | 26 | no: numbers>2; words>14 | When you are hit, the attacker is Cursed (later hits launch them 8% farther) for 3 seconds / Drawback: you are Chilled (20% slower) for 2 seconds |
| parry_master | Parry Master | keystone | 0 | perfect_shield | - | status status=guarded subject=self duration=duration amount=1; heal subject=self amount=heal; status status=chill subject=self duration=90 amount=1 | duration=300 heal=10 | You are Chilled for 1.5 seconds. | chill guarded | keystone guarded healing | damage_taken launch_taken speed sustain | 10 | 18 | no: effects>1; numbers>2 | Perfect shield: Guarded for 5 seconds and heal 10% / Drawback: you are Chilled (20% slower) for 1.5 seconds |
| skyborne | Skyborne | keystone | 0 | always | - | value key=jump_height value=1.5; value key=air_jump_height value=1.5; value key=knockback_taken value=1.25 |  | Launched 25% farther. | - | keystone aerial | jump launch_taken | 4 | 13 | yes | Jump height and air jump height +50% / Drawback: you are launched 25% farther |
| dive_bomber | Dive Bomber | keystone | 0 | always | - | convert change{launch=1.3} match{move=aerial}; value key=run_speed value=0.8 |  | Run speed -20%. | - | keystone aerial | launch_dealt speed | 4 | 10 | yes | Aerial attacks launch 30% farther / Drawback: you run 20% slower |
| skyfarer | Skyfarer | keystone | 0 | jump | - | status status=haste subject=self duration=duration amount=1; damage subject=self amount=1 | duration=90 | Every jump costs 1 damage point. | haste | keystone hasted aerial | speed sustain | 6 | 15 | yes | Every jump gives Haste for 1.5 seconds / Drawback: every jump costs you 1 damage point |
| hang_time | Hang Time | keystone | 0 | air_jump | - | status status=guarded subject=self duration=duration amount=1; status status=momentum subject=self duration=180 amount=1; status status=curse subject=self duration=120 amount=0.05 | duration=120 | Launched 5% farther for 2 seconds. | curse guarded momentum | keystone guarded momentum aerial | damage_taken launch_taken momentum | 10 | 23 | no: effects>1; drawback line>12 words | Every air jump gives Guarded for 2 seconds and Momentum / Drawback: each air jump also makes you launched 5% farther for 2 seconds |
| pandemic | Pandemic | keystone | 0 | always | - | value key=status_duration value=1.6; value key=damage_dealt value=0.85 |  | Damage you deal -15%. | - | keystone cursed | damage_dealt status_duration | 4 | 11 | yes | Statuses you cause last 60% longer / Drawback: damage you deal -15% |
| opportunist | Opportunist | keystone | 0 | hit_dealt | target_status=any | status status=curse subject=target duration=duration amount=bonus; damage subject=self amount=1 | bonus=0.06 duration=150 | Each such hit costs you 1 damage point. | any curse | keystone cursed | launch_taken sustain | 9 | 26 | no: words>14 | Hit a target with any status: Curse it (later hits launch it 6% farther) for 2.5 seconds / Drawback: each such hit costs you 1 damage point |
| plague_bearer | Plague Bearer | keystone | 0 | hit_dealt | - | status status=burn subject=target duration=duration amount=damage; status status=burn subject=self duration=60 amount=1 | damage=2 duration=120 | Each hit also sets you Burning for 1 second. | burn | keystone burning fire | sustain | 8 | 26 | no: numbers>2; words>14 | Every hit sets the target Burning for 2 seconds (2 damage a second, stacking to 3) / Drawback: each hit also sets you Burning for 1 second |
| deep_freeze | Deep Freeze | keystone | 0 | hit_dealt | - | status status=chill subject=target duration=duration amount=1; status status=curse subject=target duration=duration amount=bonus; status status=chill subject=self duration=60 amount=1 | bonus=0.04 duration=240 | Each hit also Chills you for 1 second. | chill curse | keystone chilled ice | launch_taken speed | 9 | 21 | no: effects>1; gives >1 status | Every hit Chills and Curses the target for 4 seconds / Drawback: each hit also Chills you (20% slower) for 1 second |
| everburn | Everburn | keystone | 0 | always | - | versus-status status=burn change{launch=1.15,percent_damage=1.5} match{}; value key=status_duration value=1.3; value key=damage_taken value=1.15 |  | Damage you take +15%. | burn | keystone burning damage | damage_dealt damage_taken launch_dealt status_duration | 8 | 21 | no: effects>1; numbers>2; words>14 | Burning targets take 50% more damage and launch 15% farther; your statuses last 30% longer / Drawback: you take 15% more damage |
| clash_king | Clash King | keystone | 0 | clank | - | heal subject=self amount=heal; status status=haste subject=self duration=duration amount=1; damage subject=self amount=2 | duration=150 heal=10 | Each clank costs you 2 damage points. | haste | keystone hasted healing | speed sustain | 8 | 20 | no: effects>1 | Clank with a fighter: heal 10% and gain Haste for 2.5 seconds / Drawback: each clank costs you 2 damage points |
| echo_weaver | Echo Weaver | keystone | 0 | always | - | echo status=haste match{move=any}; value key=damage_dealt value=0.9 |  | Damage you deal -10%. | haste | keystone hasted damage | damage_dealt echo | 4 | 14 | yes | While Hasted, your attacks repeat twice at half damage / Drawback: damage you deal -10% |
| finishers_mark | Finisher's Mark | keystone | 0 | hit_dealt | target_damage_above=100 | status status=curse subject=target duration=duration amount=bonus; status status=chill subject=self duration=60 amount=1 | bonus=0.08 duration=150 | Each such hit Chills you for 1 second. | chill curse | keystone cursed | launch_taken speed | 11 | 28 | no: numbers>2; words>14 | Hit a target above 100% damage: Curse it (later hits launch it 8% farther) for 2.5 seconds / Drawback: each such hit Chills you (20% slower) for 1 second |
| desperado | Desperado | keystone | 0 | interval | self_damage_above=80 | status status=haste subject=self duration=60 amount=1; status status=guarded subject=self duration=60 amount=1; status status=curse subject=self duration=60 amount=0.1 |  | While you are above 80% damage you are launched 10% farther. | curse guarded haste | keystone hasted guarded | damage_taken launch_taken speed | 10 | 20 | no: effects>1; gives >1 status | While you are above 80% damage you are Hasted and Guarded / Drawback: in that state you are launched 10% farther |
| fury | Fury | keystone | 0 | hit_taken | - | status status=momentum subject=self duration=300 amount=1; status status=haste subject=self duration=duration amount=1; remove_status status=guarded subject=self | duration=180 | Being hit ends your Guarded status. | guarded haste momentum | keystone hasted momentum | cleanse damage_taken launch_taken momentum speed | 8 | 18 | no: effects>1 | When you are hit, gain Momentum and Haste for 3 seconds / Drawback: being hit ends your Guarded status |
| wavedasher | Wavedasher | keystone | 0 | wavedash | - | armor type=super frames=6; status status=guarded subject=self duration=12 amount=1; damage subject=self amount=2 |  | Each wavedash costs 2 damage points. | guarded | keystone guarded technique | armor damage_taken launch_taken sustain | 8 | 23 | no: effects>1; words>14 | Wavedash: super armour for 6 frames, then Guarded for 12 (gold afterimages while it lasts) / Drawback: each wavedash costs you 2 damage points |
| clean_lander | Clean Lander | keystone | 0 | lcancel_hit | - | status status=haste subject=self duration=duration amount=1; damage subject=self amount=1 | duration=120 | Each such landing costs 1 damage point. | haste | keystone hasted aerial technique | speed sustain | 6 | 26 | no: words>14 | L-cancel a landing after the aerial hit: Haste for 2 seconds (blue afterimages for exactly that long) / Drawback: each such landing costs you 1 damage point |
| powershield_oath | Powershield Oath | keystone | 0 | perfect_shield | - | armor type=hit_count value=1 frames=90; status status=guarded subject=self duration=90 amount=1; status status=chill subject=self duration=60 amount=1 |  | You are Chilled for 1 second. | chill guarded | keystone guarded technique | armor damage_taken launch_taken speed | 9 | 25 | no: effects>1; words>14 | Perfect shield: absorb the next hit with armour and be Guarded for 1.5 seconds (teal afterimages) / Drawback: you are Chilled (20% slower) for 1 second |
| juggernaut | Juggernaut | keystone | 0 | always | - | armor type=damage_threshold value=6; restrict |  | You cannot run. | - | keystone guarded technique | armor restrict | 3 | 15 | yes | You do not flinch from hits that deal under 6 damage / Drawback: you cannot run |
| executioner | Executioner | keystone | 0 | always | - | crit chance=1 multiplier=2; value key=damage_dealt value=0.9 |  | Damage you deal -10%, and hits on a target under 100% never crit. | - | keystone damage critical | crit damage_dealt | 5 | 23 | yes | Hits on a target above 100% damage always crit for double / Drawback: damage you deal -10%, and no hit below 100% can crit |
| critical_mass | Critical Mass | keystone | 0 | crit | - | status status=momentum subject=self duration=duration amount=1; status status=shock subject=target duration=shock amount=1; status status=curse subject=self duration=90 amount=0.05 | duration=300 shock=180 | A crit also makes you launched 5% farther for 1.5 seconds. | curse momentum shock | keystone momentum critical shocked | launch_taken momentum | 11 | 33 | no: effects>1; numbers>2; words>14 | Land a crit: gain Momentum (up to 5) for 5 seconds and Shock the target (its next hit taken stuns longer) / Drawback: each crit also makes you launched 5% farther for 1.5 seconds |
| combo_conduit | Combo Conduit | keystone | 0 | combo OR combo[combo_at_least=2;target_status=curse] | combo_at_least=3 | crit_next multiplier=1.6 count=1; status status=chill subject=self duration=60 amount=1 |  | Each such hit Chills you for 1 second. | chill curse | keystone critical technique | crit speed | 12 | 32 | no: triggers>1; conditions>1; words>14 | Land the third or later hit of a combo (the second on a Cursed target): your next hit crits for x1.6 / Drawback: each such hit Chills you (20% slower) for 1 second |
| aerialist | Aerialist | keystone | 0 | always | - | air_jumps count=5; restrict |  | You cannot shield. | - | keystone aerial technique | air_jumps restrict | 2 | 9 | yes | You have five air jumps / Drawback: you cannot shield |
| phase_dash | Phase Dash | keystone | 0 | air_dodge | - | intangible frames=4; damage subject=self amount=1 |  | Each air dodge costs 1 damage point. | - | keystone technique | intangible sustain | 5 | 18 | yes | Air dodge: you are intangible for 4 extra frames / Drawback: each air dodge costs you 1 damage point |
| conductor | Conductor | keystone | 0 | hit_dealt | tag=electric | status status=shock subject=target duration=duration amount=1; chain_status status=shock duration=duration amount=1; damage subject=self amount=1 | duration=150 | Each electric hit costs you 1 damage point. | shock | keystone electric shocked | conversion launch_taken sustain | 8 | 25 | no: effects>1; words>14 | Electric hits Shock the target and chain Shock to the nearest other opponent for 2.5 seconds / Drawback: each electric hit costs you 1 damage point |
| gambler | Gambler | keystone | 0 | always | - | crit chance=0.35 multiplier=2; value key=damage_dealt value=0.8 |  | All your hits deal 20% less damage before any crit. | - | keystone damage critical | crit damage_dealt | 4 | 21 | yes | Every hit has a 35% chance to deal double or triple damage / Drawback: all your hits deal 20% less damage first |
| featherfall | Featherfall | keystone | 0 | always | - | value key=fall_speed value=0.65; value key=weight value=0.75; value key=knockback_taken value=1.3 |  | Launched 30% farther. | - | keystone aerial | fall launch_taken weight | 6 | 14 | no: effects>1 | You fall 35% slower and weigh 25% less / Drawback: you are launched 30% farther |
| echo_oath | Echo Oath | keystone | 0 | always | - | echo match{move=any}; value key=damage_dealt value=0.5 | copies=1 / copies=2 / copies=3 | All attack damage, including echoes, is 50% lower. | - | aerial damage momentum | echo damage_dealt | 3 | 17 | yes | Every attack repeats a moment later at reduced damage / Drawback: all your attack damage is 50% lower |

### A3. Uniques (6)

| id | name | slot | from depth | when | if | then (effects) | numbers: tier 1 / 2 / 3 | drawback (cost text, or the effect that is the drawback) | statuses | tags | budget family | score | words | passes the bite rule? | rule text exactly as the player reads it (tier 1) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| glass_core | Glass Core | unique | 0 | always | - | value key=damage_dealt value=1.6; value key=damage_taken value=1.6 |  | Take 60% more attack percent damage. | - | unique damage | damage_dealt damage_taken | 3 | 7 | yes | Damage you deal and take both +60% |
| ember_crown | Ember Crown | unique | 0 | always | - | convert change{element=fire} match{move=any}; value key=damage_taken value=1.3 |  | Take 30% more attack damage. | - | unique fire burning | conversion damage_taken | 3 | 9 | yes | All your attacks become fire / Damage you take +30% |
| winter_heart | Winter Heart | unique | 0 | always | - | convert change{element=ice} match{move=any}; value key=run_speed value=0.8 |  | Run 20% slower. | - | unique ice chilled | conversion speed | 3 | 8 | yes | All your attacks become ice / Run speed -20% |
| storm_shell | Storm Shell | unique | 0 | always | - | convert change{element=electric} match{move=any}; value key=damage_taken value=0.8; value key=damage_dealt value=0.8 |  | Deal 20% less attack damage. | - | unique electric guarded | conversion damage_taken damage_dealt | 5 | 13 | no: effects>1 | All your attacks become electric / Damage you take -20% / Damage you deal -20% |
| mirror_shard | Mirror Shard | unique | 0 | clank | - | clank_damage subject=target |  | Requires a fighter-to-fighter clank; no benefit against item clanks. | - | unique damage guarded | clank | 3 | 18 | yes | When your attack clashes with a fighter: they take both attacks' damage / Only works against fighters, not items |
| echo_heart | Echo Heart | unique | 0 | always | - | echo match{move=any}; value key=damage_dealt value=0.75 | copies=1 / copies=2 / copies=3 | All attack damage, including echoes, is 25% lower. | - | aerial damage momentum | echo damage_dealt | 2 | 9 | yes | Every attack repeats a moment later at reduced damage |
