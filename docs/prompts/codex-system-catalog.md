# Parallel packet P8: a surfacing catalogue of everything that must become ONE system (docs only) (2026-10-04)

Rules: `docs/prompts/codex-parallel-rules.md` (read it first). You own ONE new file,
`docs/superpowers/specs/2026-10-04-one-system-catalogue.md`, plus your report. Write no code and edit nothing else.
Three engine jobs are editing source right now (echo hitboxes, armour types, Geno `define` slice 1): read their packets
and any reports that exist, and mark what is in flight as in flight.

## The owner (verbatim)
"Can you do a surfacing catalog to see REALLY what all needs to be intertwined into one system?"

Context: over two days this project grew many capabilities, mostly built separately by different jobs. The owner's game
direction (`docs/superpowers/specs/2026-10-04-envoy-loot-and-modifiers-design.md`) depends on emergence: a small shared
vocabulary (tags, triggers, conditions, statuses, effects, visuals) where separately written rules combine. The owner
now senses that the pieces exist but are not yet one system. The catalogue's job is to surface, from the CODE and not
from memory, every piece, what it can already talk to, and what it cannot.

## Method (be exhaustive and cite file:line; separate "verified by reading" from "inferred")
Build the inventory from the sources of truth, not from the docs' claims:
- every script hook/event the engine raises (the `on_*` dispatch tables in `melee/pc/platform/gw_script*.c/.inc` and the
  `Script_GameEvent` producers in `melee/src/melee/` and `melee/pc/gameworld/`), with payload fields;
- every `gd.*` call in the registration tables, grouped by what it reads or changes;
- the modifier engine's actual vocabulary (`melee/pc/scripts/examples/envoy/scripts/mod_schema.lua`, `mod_engine.lua`,
  `mod_pool.lua`, `mod_display.lua`): triggers, conditions, statuses, effect kinds, visual kinds, families, tags;
- the native rule systems: hit rules, fighter modifiers, fighter capabilities, armour, zones, items/drives, echoes,
  afterimages and tracers, surface/post shaders, lights, world effects, sound;
- the Geno engine's own vocabulary (`melee/pc/geno/`, `melee/docs/geno.md`, `tools/geno/geno.schema.json`): states,
  move scripts, hitbox flags, articles, overlays, `attach` and the in-flight `define`;
- the 1P/run layer (Classic and Adventure hooks, the hold, New Game+), stage slots and switching, the mission/level
  runtime (parked), six slots, roster registry, the LAB (savestates, rewind, drills).

## Deliver in the catalogue
1. **The parts list.** One table per layer, one row per capability: name, what it is in one line, where it lives
   (file:line), status (in a played build / built and unseen / in flight / parked / missing), deterministic and
   snapshot-covered or not, offline-only or not.
2. **The vocabulary as it really is.** Every noun and verb any system uses, deduplicated: move tags, elements,
   statuses, families, events/triggers, conditions, effect kinds, visual channels, entity kinds (fighter, sub-fighter,
   CPU opponent, item, article, projectile, echo, stage object, zone). For each: which systems PRODUCE it, which CONSUME
   it. Flag every near-duplicate (two names for one idea, two events for one moment, a status in Lua mirrored by a bit
   in native code), every term only one system knows, and every producer with no consumer or consumer with no producer.
3. **The connection matrix.** Systems against systems: for each pair, connected (how: event, shared field, direct call),
   could be connected cheaply, or should stay separate (say why). Specifically answer: can a modifier trigger on it;
   can a modifier cause it; can a Geno fighter's own data trigger on or cause it (a character ability, not loot); can a
   CPU opponent have it; can an item, article or echo carry it; does it have a visual in the three-channel language
   (surface = equipped/status on you, afterimage = earned status while it lasts, tracer = this hit carries something);
   does it survive stage switches, respawn, rewind and New Game+.
4. **Where "one system" is actually broken today**: a ranked list of seams, each with evidence: parallel mechanisms that
   should be one (for example a native status bitmask and a Lua status table; fighter modifiers versus fighter
   capabilities versus Geno attributes; three ways to spawn a thing; several event queues), rules that exist for the
   player but not opponents or items, gameplay that has no visual or visuals with no gameplay meaning, things loot can do
   that a fighter's own definition cannot and the reverse, anything that only works in the LAB or only in Classic.
5. **The spine proposal**: the smallest core that everything should plug into (most likely: one event bus with typed,
   tagged payloads; one status/stack store; one effect vocabulary with native and Lua executors; one "source" concept
   so a rule can come from a drive, a fighter's own definition, an item, a stage or an opponent's roll; one visual
   binding from state to the three channels), what each existing system would need to change to plug in, and what can
   stay as it is. Give it as a dependency-ordered list of unification steps, each small, each leaving the game playable,
   with the ones that unlock the most combinations first. Do not propose new features: only joining what exists.
6. **A one-page map** at the top: the layers and the spine as an ASCII diagram, and the ten most valuable connections
   that do not exist yet, in order.
Report `_build/tmp/codex-system-catalog-report.md`: the one-page map, counts (hooks, calls, vocabulary terms, seams), and
the three unification steps you would do first.
