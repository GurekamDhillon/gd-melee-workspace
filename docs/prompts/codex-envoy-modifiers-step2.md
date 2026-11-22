# Codex packet EM3: drives as rolled loot, and the full first pool (2026-10-04)

Workspace root is two levels above this file; game checkout `melee/`. Same rules as EM1 and EM2: both trees are
deliberately dirty, no commits, no `tools/port/build.sh`, no game launch, keep every file compilable; do not stop for
design approval; record your choices in the report. Design: `docs/superpowers/specs/2026-10-04-envoy-loot-and-modifiers-design.md`
(this packet is build-order steps 2 and 3 of section 11, and nothing beyond them: no opponent rolls, no Classic yet).

## Where the owner is
The owner played EM1 + EM2 in the LAB with eight modifiers on Mario (Pyromancer, Kindling, Pyre, Feasting, Updraft,
Crosswind, Glass Core, Reprisal) and said: "Okay feels pretty awesome!". The log showed a four-modifier chain off real
hits ("hit converted to fire by Pyromancer, burn applied by Kindling, launch boosted by Pyre, heal 10 from Feasting").
So the core is approved: build on it without changing how it feels.

One bug found in play, already fixed by the integrator in `mod_engine.lua` (keep it): a lost stock cleared the fighter's
EQUIPPED modifiers. The earlier packet's wording caused it. The rule is: a lost stock clears what was happening to the
fighter (statuses, stacks, recent events, timed values); the build (equipped modifiers, their steady effects, looks and
hit rules) persists and is re-derived. Add the missing test, and check `mod_lab.lua` and the display for the same
assumption (the log showed `fighter mod: cleared port=N` on each KO: steady values such as Glass Core's must be back
on the respawned fighter without the player doing anything).

## Build
1. **Drives as loot (spec section 5).** A generator: base type by colour with its implicit (red damage dealt, green run
   and air speed, blue knockback taken, yellow jump height, purple status duration, white no implicit and one extra
   modifier), rarity (Common, Magic, Rare, Unique) setting how many prefixes and suffixes roll, weighted pools with
   tiers that rise with a depth value, no duplicate modifier groups on one drive, seeded and deterministic. Names
   generated from the modifiers ("Burning Red Drive of the Updraft"); the tooltip is generated from the same records as
   the rules. Uniques are fixed drives.
2. **Bag and slots (spec section 6).** Four equipped slots (tuning value), a twelve-drive bag, equip / swap / discard on
   a controller-only screen built from existing kit components (no new art), showing each drive's name, rarity colour,
   lines of rule text, and what changes if you equip it. One keystone at most. Equipping re-derives values, looks and
   native hit rules at once. Whether the bag persists between runs is behind one switch (default: fresh per run).
3. **Physical drops.** Use the existing drive pickup item (hover, spin, effects, sounds): a dropped drive's core glows
   in its element and rarity sets the beam and sparkle (spec section 8b); walking over it puts it in the bag with a
   short name card. In the LAB: `drive drop [rarity] [seed]` spawns one near the opponent, `drive give ...`, `bag`.
4. **The full first pool (spec section 8): about thirty modifiers, five uniques, three keystones**, each a data record
   with its rule, text and shader look, using only what the engine can really do after EM1 and EM2 (hit rules now
   allow conversion and versus-status damage and knockback). Keep the vocabulary small so sharing is common; every new
   modifier must share a tag, status or event with at least two others. Include the spec's examples where they are
   possible (Second Wind, Conductor, Hoarder, Mirror Shard, Aerialist, Juggernaut: report honestly which are not yet
   possible and why). Uniques and keystones get a signature look.
5. **The synergy test (spec section 8):** a generated table of every pair of modifiers that interact (shared tag,
   status produced by one and consumed by the other, event raised by one and triggered on by the other), and a list of
   at least five two-modifier and two three-modifier chains nobody wrote as a set, each with a play script.
6. Tests: generation determinism and distributions over 10,000 rolls, no invalid drive, name and tooltip from the same
   record, bag and slot rules, equip/unequip leaving nothing behind, the stock-loss rule above, every modifier alone,
   the listed chains, rewind exactness with a full bag. Update `PLAYTEST.md`. Regenerate the bundle last.
Report `_build/tmp/codex-envoy-modifiers-step2-report.md`: the pool as a table (id, kind, rule text, look, tags), what
could not be built and why, the synergy table summary, what the integrator must build, and a short play script for the
owner (commands to drop drives, what to equip, what to try).
