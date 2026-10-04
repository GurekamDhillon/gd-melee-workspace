# Codex packet EM4: power budget, and opponents that roll modifiers (2026-10-04)

Workspace root is two levels above this file; game checkout `melee/`. Same rules as EM1-EM3: both trees deliberately
dirty, no commits, no `tools/port/build.sh`, no game launch, keep every file compilable; do not stop for design
approval; record your choices in the report. Design: `docs/superpowers/specs/2026-10-04-envoy-loot-and-modifiers-design.md`
(this packet is a balance pass on what exists plus build-order step 4, opponents; not Classic yet).

## Where the owner is
The owner played EM3 (loot, bag, pool) in the LAB and said: "looks cool, but it seems like I can kill most "vanilla"
two or so hits, which seems OP". The log (`_build/runs/envoy-loot-play1/melee-pc.log`) shows the player's fighter values
at `dealt=2.16` (Glass Core x2 times a red drive's implicit) against an opponent with no modifiers. The feel of chains
is approved ("Okay feels pretty awesome!"): keep chains loud and visible; fix how much raw killing power stacks.

## Why it happens (verify, then fix the cause, not just the numbers)
1. **Damage multipliers buy knockback twice.** Melee's knockback grows with the hit's damage and with the victim's
   percent after the hit, so doubling a hitbox's damage is far more than double the killing power. Every damage
   multiplier in the pool (Glass Core, the red implicit, Cinder, Shatter, versus-status damage) currently scales the
   hitbox damage that feeds the launch formula.
2. **Launch multipliers stack multiplicatively on top** (Pyre x1.25, Curse from Brittle/Malice, Heavy's knockback
   growth, Featherweight on the victim).
3. **The opponent has nothing.** Budgets are only meaningful against opponents that also roll modifiers.

## Build
A. **Separate "damage" from "launch" in the engine and the vocabulary.** A damage modifier adds percent to the victim
   without feeding the launch formula more than the original hit would (find the cleanest correct way in the hit-rule
   code: for example compute knockback from the unmodified hitbox damage and apply the extra percent alongside; state
   exactly what you did to staling, shield damage, clank priority and the on-screen percent). Launch power is changed
   only by modifiers that say "launch" in their text. If that needs a native change in the hit rules (a damage scale
   that does not feed knockback), make it, with tests and the snapshot story intact.
B. **A stacking rule and a budget.** Within one family (damage dealt, launch dealt, damage taken, launch taken, speed)
   bonuses ADD rather than multiply, then one cap per family applies (state the caps: a suggestion is damage dealt
   +60%, launch dealt +30%, taken reductions no better than -40%); uniques and keystones may exceed a cap only with a
   cost that is at least as large. Every modifier and implicit declares its family so the validator can sum a build's
   worst case and refuse a pool whose reachable four-slot build breaks a cap. Print each family's current total and cap
   in the bag screen so the player sees their budget.
C. **Retune the pool to that budget.** Glass Core must stay dramatic without being a two-hit kill: propose its new
   rule in the report (for example +60% damage dealt and taken, with launch unchanged, or a different trade entirely).
   For every modifier say the old and new numbers. Target, stated as a test on the knockback formula with real fighter
   weights: a four-slot Rare build with a unique kills a middleweight from the centre of Final Destination with a
   smash attack roughly 20-30 percent earlier than vanilla, not at a third of the percent.
D. **Opponents roll modifiers (spec section 7, step 4).** Each CPU opponent rolls from the same pool with a budget
   centred on the player's build strength (the family totals from B give a single strength number), seeded per run and
   stage, uniques and keystones allowed (owner's decision). Shown on a nameplate at stage start ("Hasted, Burning
   Fox") and worn as the same shader treatments. Opponents use the same engine: their statuses, chains and hit rules
   apply to the player. In the LAB: `foe roll [strength] [seed] [port]`, `foe clear`, and the standing opponent can be
   switched to a fighting CPU with its modifiers on.
E. Tests: the launch test in C; family sums and caps; the validator refusing an over-budget pool; opponent rolls
   deterministic and centred (mean strength within a stated tolerance over 1,000 rolls); a modded opponent's rules
   affecting the player; cleanup. Update `PLAYTEST.md`; regenerate the bundle last.
Report `_build/tmp/codex-envoy-balance-and-opponents-report.md`: the cause confirmed with numbers (the launch a
doubled-damage smash produced versus vanilla), what changed natively, the family table with caps, the retuned pool
(old and new), whether the integrator must rebuild, and a play script (a balanced build to equip, an opponent to roll,
what the owner should feel).
