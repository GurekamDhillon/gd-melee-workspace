# Codex packet EM1: the modifier engine, step 1 (2026-10-04)

Workspace root is two levels above this file; game checkout `melee/`. Read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `docs/scripting.md`, `docs/shaders.md`, and the approved design in full:
`docs/superpowers/specs/2026-10-04-envoy-loot-and-modifiers-design.md`. Both trees are deliberately dirty: do NOT commit,
reset, stash, revert or reformat. Do NOT run `tools/port/build.sh`, do NOT launch the game. Keep every file compilable at
every save. Do not stop to ask for design approval: the owner approved the spec ("lgtm") and answered its decisions
(section 14); record your own choices in the report. You have just finished follow-up 1 on the Classic flow: build on it.

## Why
The owner played Classic with drive rewards and said "Nothing was particularly great", then: "whats path of exile doing?
They have items with actives/passives, suffix/prefix modifiers/uniques/etc. We need to make emergent gameplay with
synergies" and "make it have visual components via shaders". The reward stops being a number and becomes an item with
rules on it; synergies come from separately written rules sharing tags and events; every rule is visible on the fighter.

## This packet = build-order step 1 of the spec (section 11), and nothing beyond it
Deliver something the owner can play in the LAB: pick modifiers from a debug list, hit a standing opponent, and SEE and
FEEL chains happen. No loot generation, no drops, no bag, no Classic integration yet (steps 2-5 come later).

1. **Engine reach first (spec section 10).** For every trigger, condition, effect and visual the spec lists, establish
   from the registration tables and the code whether it exists, with file:line. Then add what is missing and cheap, as
   general script capabilities (documented in `docs/scripting.md`, tested in the suite pattern, offline-only where they
   write gameplay, each with a single-feature catalogue demo: project rule):
   - at hit time: the attacker's move tag (jab, tilt, smash, aerial, special, grab, throw, projectile, dash attack:
     derive from the action state and hitbox owner; say how each fighter family maps and where it is ambiguous), the
     hit's element, damage, and whether each side was grounded or airborne;
   - changing a hit's element and adding damage/knockback/hitstop to it from a script, before it is applied;
   - fighter values: jump height (ground and air), number of air jumps, fall speed, weight, flinch resistance, shield
     size and regeneration; healing; brief intangibility; timed changes that clean themselves up;
   - events: shield hit, perfect shield, jump, air jump, landing, ledge grab, grab, throw, taunt, stock lost;
   - visuals: SEVERAL surface shader layers on one fighter composited in a set order with per-layer parameters driven
     every frame without recompiling; the same on a CPU opponent and on sub-fighters; layers that survive costume,
     metal and size changes; everything declared to `gd.warm` so nothing compiles in play.
   Anything that cannot be done without changing retail behaviour, or is expensive, is reported, and the modifiers that
   need it are left out: never faked.
2. **The modifier engine (Lua, in the Envoy mod, as its own module with no dependence on the run flow):** modifiers as
   data records `{id, tags, tiers, trigger, conditions, effects, stacking, text, visual}`; an event bus over the engine
   events with tagged payloads; trigger matching, conditions, effects that may raise further events, a chain depth
   limit and a per-frame budget; statuses and stacks (duration, max stacks, refresh rule); seeded and deterministic,
   fixed evaluation order, no wall-clock, state where the offline rewind captures it; the tooltip generated from the
   same record. The four rules of spec section 3 are enforced by the schema validator (a modifier may not name another
   modifier or a specific move).
3. **The first ten modifiers**, chosen so that at least three two-modifier chains and one three-modifier chain exist
   among them (the spec's Kindling / Pyre / Feasting chain must be one), plus one unique and one keystone, each with its
   shader treatment. The seven status looks of spec section 8b (Burn, Shock, Chill, Curse, Haste, Guarded, Momentum)
   are written as a small library of shader bodies with parameters; the layered "your build is on your fighter"
   treatment works for at least two equipped modifiers at once; the chain "moment" post pass fires scaled by chain
   length. Obey the readability rules (three layers at full strength, statuses outrank equipment, silhouette and hurt
   animation never hidden, an intensity setting, safe flash limits).
4. **A way to play it now**: a LAB panel or console commands (`mod list`, `mod add <id> [port]`, `mod clear`,
   `mod trace`) to put modifiers on the player and on the opponent; an overlay listing each fighter's active modifiers,
   statuses and stacks; and a trace of the last chain in plain words ("Burn applied by Kindling, +knockback from Pyre,
   heal from Feasting").
5. **Tests**: schema validation; each modifier alone; each intended chain; determinism (same seed, same result);
   the depth limit and budget; no status, layer or modified value left on anyone after `mod clear`, a KO, a respawn or
   a scene change; rewind exactness with modifiers active.
Report `_build/tmp/codex-envoy-modifiers-step1-report.md`: the engine reach table (exists / added / not possible, with
file:line), the vocabulary as actually supported, the ten modifiers with their text and look, what the integrator must
build (say if Aurora must be rebuilt), and a play script for the owner: which modifiers to add and what to do to see
each chain. If it is too much for one pass, finish items 1 and 2 completely, then as many modifiers as hold up, and say
where you stopped.
