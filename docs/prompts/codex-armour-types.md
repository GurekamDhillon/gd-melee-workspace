# Parallel packet P2b: armour types as a Geno engine extension (2026-10-04)

Rules: `docs/prompts/codex-parallel-rules.md` (read it again). Two other jobs are running: the Geno `define` slice 1
(editing `melee/pc/geno/`, `tools/geno/` and the roster) and the Envoy echo work (the Envoy mod and hit rules). You own
your fighter-capabilities files (`script_fighter_caps*`, `gw_script_fighter_caps*`) and the minimal `TARGET_PC` hooks in
`melee/src/melee/ft/`. No commits, no build, no game launch. Do not stop for design approval; record choices.

## The owner (verbatim)
Asked whether heavy/super armour like Smash Ultimate's exists natively in Melee, then: "adding additional armour types
seem like a great geno extension and easily testable".

## What retail has (verified by the integrator; re-verify)
`src/melee/ft/kinds/ftCommon/ftCo_Damage.c` ~136-145: the larger of `fp->dmg.armor0` and `fp->dmg.armor1`, plus
`p_ftCommonData->metal_armor` when metal, is SUBTRACTED from `kb_applied`, floored at `kb_min`. Set by Yoshi's aerial
jump (`ftCo_JumpAerial.c` ~230, `armor1`), Bowser and Giga Bowser (`ftkoopa.c` ~322, `ftgkoopa.c` ~314, `armor0`), Nana
(`ftnana.c` ~368). So Melee has knockback-subtractive armour only: no damage-threshold armour and no absolute super
armour. Your P2 job already exposed flinch resistance by reusing this.

## Build: a complete, explicit set of armour types
Each is a per-fighter value a script or Geno data can set, optionally for a WINDOW (frames) or tied to an action state
or a range of its animation frames, composable with retail armour, cleared with the other capabilities, snapshot and
rewind exact, and each with its own honest name so tooltips read correctly:
1. **Knockback armour** (retail style): subtract N from knockback. Already there: make it one of the named types.
2. **Damage-threshold armour** (Ultimate's heavy armour): a hit whose damage is below a threshold does not flinch;
   percent is still taken. Threshold compares the single hit the game selected for the reaction (your earlier fix).
3. **Knockback-threshold armour**: a hit whose computed knockback is below a threshold does not flinch (different from
   subtracting: above the threshold the full knockback applies).
4. **Super armour** (absolute, for a window): no hit causes flinch or launch while active; percent is taken; grabs
   still work unless a separate grab-immunity flag is set; say exactly what happens to hitlag for both sides, to
   hitstun-based mechanics, to throws, and to hits that would KO at that percent (state the retail-consistent choice).
5. **Hit-count armour**: absorbs the next N hits (or N hits per window) without flinching, then breaks, with an event
   when it breaks.
6. **Damage-pool armour** (a "super armour health bar"): absorbs flinching until a total of D damage has been taken
   during the window, then breaks.
7. **Directional armour** (optional, if cheap): armour only against hits from the front or the back.
Common rules: several types can be active; define the order they are evaluated and prove it with tests; every armoured
hit raises an event (`on_armor{port, type, absorbed=true|false, broke=true|false, damage, knockback}`) so modifiers and
visuals can react (the Guarded status look flashes on an absorbed hit); elements with special retail reactions
(ice freeze, grabs, sleep, the burying and paralysing ones) have a stated rule each; CPUs and sub-fighters work; nothing
changes for a fighter with no armour set (retail values untouched).
Script API in the existing capability style (`gd.fighter_armor(port, {type=..., value=..., frames=..., state=...,
from=..., to=...})`, read-back, clear), documented.
**As a Geno engine extension**: the natural home is per-state and per-move armour windows in a fighter's Geno data
(`geno.json` / `.genoasm`: "armour type X from frame A to frame B of this move"). The `define` slice 1 job is editing
the Geno schema and engine right now, so do NOT edit `melee/pc/geno/` or `tools/geno/`: implement the native capability
and the script API completely, and write the exact schema fields, encoding and loader hook you propose into your report
as an integration request for the integrator to apply after slice 1.
**Easily testable** is part of the brief: suite tests for every type against the real knockback formula (below and
above each threshold, at low and high percent, the break events, the evaluation order, window expiry, snapshot
exactness), and a catalogue demo ("armour types": a standing fighter cycles through each type while a second fighter
hits it with a weak, a medium and a strong attack; text shows what was absorbed and why).
Report `_build/tmp/codex-armour-types-report.md`: each type's exact rule, file:line, the Geno schema proposal, what the
Envoy job should add as modifiers (as data it can copy: do not edit the Envoy mod), and a tester's script.
