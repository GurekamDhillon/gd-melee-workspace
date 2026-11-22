# Parallel packet P7: design: Geno expresses a FULL fighter (design only, no code) (2026-10-04)

Rules: `docs/prompts/codex-parallel-rules.md` (read it first). You own ONE new file:
`docs/superpowers/specs/2026-10-04-geno-full-fighter-design.md`, plus your report. Write no code and edit nothing else.
This is a design for the owner to review before anything is built: be concrete, cite file:line for every claim about
what exists, and separate what you verified by reading from what you infer.

## The owner's direction (verbatim)
"basically I think we need Geno to be able to express a full character instead of just what M-EX doesnt"

Today the Geno engine (our fighter-extension engine: `melee/docs/geno.md`, `melee/pc/geno/`, `tools/geno/`,
`docs/learn/geno-fighters/`, especially `00-what-m-ex-and-geno-are.md` and `10-known-gaps.md`) sits ON TOP of an m-ex
fighter: m-ex supplies the slot, the fighter data file, the model, animations, attributes, the ftFunction tables and
PowerPC callbacks our interpreter runs (`docs/MEX_PORT_STATUS.md`, `melee/pc/platform/gw_mex_*`), and Geno adds what
m-ex cannot express. The owner wants Geno to be able to describe an ENTIRE fighter by itself, as data plus Lua, so a
character can be authored, or ported from another game or another mod, with no MexTK, no PowerPC code and no m-ex
package. A private character port now running is the first real customer; Ultimate fighter ports (`ports/`) are the
second; a from-scratch original fighter is the third.

## Deliver in the spec
1. **Inventory: everything a complete Melee fighter is.** From the decompilation and our port, list every part with
   where retail defines it: slot and ids (fighter kind, character kind, the per-character tables), the fighter data
   file and what is in it (attributes, model, bones, hurtboxes, ECB, the action/subaction tables and their script
   commands, animation banks, the costume/material data), common states and the fighter-specific states with their
   animation, physics, collision, interrupt and input callbacks, special moves, articles/items and their state tables,
   effects, sound and voice banks, the camera and results-screen data, CSS icon/portrait/name/announcer, stock icons,
   Kirby copy ability and hat, CPU AI tables, throws and being-thrown data, ledge/shield/swim/item-use behaviour,
   trophies and records, team colours and costumes.
2. **For each part: who supplies it today for a modded fighter** (m-ex data, m-ex PowerPC code via our interpreter,
   Geno data, Geno Lua, or nothing), and **whether Geno can express it now**, with the exact schema fields or the gap.
3. **The target format**: a Geno fighter package that is complete by itself. Propose the folder layout and schema
   (extending `geno.json` and `.genoasm` rather than replacing them), covering: identity and select-screen entry;
   attributes; model, skeleton, hurtboxes and costumes (which model/animation formats we accept: the retail HSD data,
   our own mesh format used for stage pieces, and an import path from standard tools such as Blender/glTF: recommend
   one primary path and say why); animations and how states reference them; the state machine for EVERY state
   (inheriting any common state by default and overriding per state, so a fighter is short to write); move scripts
   (hitboxes, throws, effects, sounds, timers) as data; logic that data cannot express, in sandboxed deterministic Lua
   with a stated API and budget; articles/projectiles; effects and sounds referenced by name from packages; AI hints so
   a CPU can use the fighter; Kirby copy; results/victory; costumes and team colours.
   State what stays "use the retail common behaviour unless overridden" so nobody has to redefine walking.
4. **Coexistence and migration**: a Geno-only fighter, an m-ex fighter, and an m-ex fighter with Geno extensions must all
   load side by side; how an existing m-ex + Geno fighter (Sora, Ultimate Kirby, Meta Knight under `ports/`) would be
   converted to Geno-only, and what would be lost or gained; how the slot is registered without `MxDt.dat` (the roster
   registry work: `_build/tmp/codex-roster-registry-report.md`), and the caps that must go (32 Geno profiles).
5. **Determinism, rollback and netplay**: what a Geno-only fighter must guarantee to be usable online; what Lua may and
   may not do; how fighter content is identified so both peers agree (hash of the package).
6. **Vanilla disc, one folder** (standing rule): everything a fighter needs is in its folder; nothing derived from the
   disc is shipped; say how a fighter may REFERENCE retail assets (a donor fighter's animation, a retail effect) without
   containing them.
7. **Tooling and the human author**: the checker, assembler, exporter and a Blender path extended to the full format;
   live reload in the LAB; a "new fighter" template that boots as a playable clone of a retail fighter in one command,
   then is edited piece by piece; what the learning guide's packets become.
8. **Build order as slices, each ending with something playable**, smallest first (for example: slice 1 a Geno-only
   fighter that reuses a retail fighter's model and animations by reference but owns all its states, attributes and
   moves; slice 2 its own articles, effects and sounds; slice 3 its own model, skeleton and animations through the
   import path; slice 4 select screen, costumes, results, Kirby, AI; slice 5 migration of the existing ports), with a
   rough size for each and the engine work it needs.
9. **Risks and open decisions for the owner**, each as a question with your recommendation.
Report `_build/tmp/codex-geno-full-fighter-design-report.md`: a one-page summary and the three decisions that most need
the owner.
