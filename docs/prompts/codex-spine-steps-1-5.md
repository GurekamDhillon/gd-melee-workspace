# Codex packet S1: the one-system spine, steps 1 to 5 (2026-10-04)

Workspace root is two levels above this file; game checkout `melee/`. Both trees deliberately dirty: no commits, no
`tools/port/build.sh`, no game launch, keep every file compilable. Do not stop for design approval: the owner approved
this ("lgtm") on the integrator's summary of the catalogue. Record choices in the report. The integrator has just built
and committed the state you start from; if other jobs are named as running in your launch message, follow
`docs/prompts/codex-parallel-rules.md`.

## Why
`docs/superpowers/specs/2026-10-04-one-system-catalogue.md` (read all of it: the map, the ranked seams, section 5)
found that two days of separately built capabilities are not one system. Its top seams: the modifier engine is a LAB
island while Classic and Adventure still run the old companion-stat director (`mod_lab.lua:16`, `classic.lua:92`); three
status authorities (Lua named statuses, mirrored hit-rule bits, numeric capability channels); move tags incomplete at
collision (Geno and m-ex moves `unknown`, item hits untagged: `script_hit_context.inc:19`); four ways of naming an
entity; and new setters (capabilities, armour, echoes) outside the rewind journal (`gw_script_sim_state.inc:146`).
The owner's game depends on emergence from a small shared vocabulary, and wants technique abilities, crits, earned
afterimages and armour effects next (held in `docs/prompts/codex-earned-states-crits-held.md`: read it so the spine fits
what is coming, but build NONE of it). The owner's instruction for this round is to JOIN, not add.

## Build: the catalogue's section 5, steps 1 to 5, in order, each leaving the game playable
Follow the catalogue's own table for each step's change, compatibility boundary and required evidence. In short:
1. **Entity and source references.** One scalar, versioned reference for any entity (fighter, sub-fighter, CPU, item,
   article, projectile, echo, stage object) and for any SOURCE of a rule (a drive, an opponent's roll, a fighter's own
   definition, an item, a stage); frame, sequence, phase and cause in one event envelope. Old APIs keep working through
   adapters; stale references are refused.
2. **One descriptor registry and one replay executor for existing effects.** Schema, budget and compiler share the same
   field list, bounds and family; the simulation commit and rewind journal admit every implemented effect (fighter
   modifiers, damage, hit rules, and now capabilities, armour, timers, echoes), with stable handles; snapshot plus
   replay is zero-difference for each. "Do not postpone replay until the end."
3. **One status and stack authority.** Named statuses with stacks, origin and expiry live in one store; hit-rule masks,
   native expiry predicates and looks are DERIVED from it; existing results for Burn, Chill, Curse, Haste, Guarded and
   Momentum are unchanged. Fix the naming seam the catalogue found: statuses that are percent resistance are not called
   armour; real armour types keep their own honest names.
4. **Complete, tagged observations.** Every existing event (hit, clank, action, item, zone, contact, 1P, armour) goes
   through one typed envelope with consistent ordering; a hit carries the declared move tag and the original and
   effective element for retail, Geno and m-ex fighters, items, articles and echoes (declared by the source, not guessed
   from the owner's action); old hook signatures still fire.
5. **The rule host outside the LAB.** Extract the host from `mod_lab.lua`; the LAB becomes a debug adapter of it;
   Classic and Adventure install the SAME pool, bag, slots, opponent rolls and looks at their existing lifecycle
   boundaries (stage start, stage clear, game over, New Game+), behind a switch while the old stat route stays playable
   until the owner has played the new one. The same build gives the same result in the LAB and in a retail stage.
Also: the generated Envoy bundle is behind its sources (catalogue seam 8): regenerate it last, once, when your work is
consistent, and say so.
Tests for each step as the catalogue specifies (identity fixtures, zero-difference replay per effect, status parity,
tag exactness, LAB versus retail-stage parity). Update `docs/scripting.md` and the catalogue's status column for what
you changed. If all five are too much for one pass, finish them in order and stop cleanly between steps.
Report `_build/tmp/codex-spine-steps-1-5-report.md`: per step what changed (file:line), what stayed compatible, the
evidence, what the integrator must rebuild, and a play script: the loot build running inside a Classic run.
