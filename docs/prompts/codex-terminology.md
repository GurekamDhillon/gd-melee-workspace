# P8 follow-up: the project's terminology, in one file (docs only) (2026-10-04)

Rules: `docs/prompts/codex-parallel-rules.md`. You own ONE new file, `docs/TERMINOLOGY.md`, plus one line added to
`docs/CLAUDE.md`'s table and one to the root `CLAUDE.md` orientation table pointing at it (shared files: smallest edit,
re-read first). No code. Build on the catalogue you just wrote
(`docs/superpowers/specs/2026-10-04-one-system-catalogue.md`), whose vocabulary section is the raw material.

The owner: "and we need to make a proper terminology md across our entire project probably." ... "you decide as you see
fit". The integrator decided yes: the project now has enough invented words, and enough words with two meanings, that
jobs and people talk past each other.

Write `docs/TERMINOLOGY.md` as the single reference for what words mean in this project:
1. **One entry per term**: the term, a one or two sentence definition a newcomer can use, what it is NOT (when it is
   commonly confused), where it lives (file or doc), and its status if it is not yet built. Alphabetical within
   sections: the port and its build (shim, retarget, bridge, provenance, run folder, the LAB), modding (m-ex, mod folder,
   slot, the roster registry), the Geno engine (attach, define, profile, state, article, overlay, `.genoasm`), scripting
   (`gd`, hook, event, gameplay write, offline gate, warm), the game layer (drive, modifier, prefix, suffix, unique,
   keystone, implicit, rarity, tier, slot, bag, family, budget, depth, loop), combat vocabulary (move tag, element,
   status, stack, trigger, condition, effect, conversion, hit rule, echo, armour types, skill event), visuals (surface
   treatment, afterimage, tracer, post pass, the three channels and their one meaning each), stages (stage slot,
   switch, lifecycle, zone, chunk, mission), people and process (the owner, integrator, Codex packet, lane, stamped
   build, verified in game versus written).
2. **Collisions, resolved explicitly** at the top, each with the rule to follow from now on. At least: "Geno" (the
   Geno engine is this project's fighter-extension engine; a character of the same name exists in an unrelated public
   mod: always write "the Geno engine" on first use); "slot" (fighter slot, roster slot, stage slot, drive slot, save
   slot); "state" (fighter action state, a status, saved state/savestate, game state); "item" (a retail item, a Geno
   standalone item, a drive as loot); "armour" (retail knockback armour versus the named types); "port" (controller
   port, a port of a fighter from another game, the PC port); "mod" (a script mod folder, a modifier, an m-ex mod);
   "echo", "afterimage" and "copy"; "tag" (move tag versus name tag); "stage" (a level, a build stage, a LAB roadmap
   stage). For each, choose the preferred word for each meaning and list the words to stop using.
3. **Rules for adding a term**: check this file first; one meaning per word; add the entry in the same change; a
   near-duplicate is a bug.
4. A short list of terms the catalogue found with two names in code for one idea, as renames to make later (do not
   rename anything now): old name, new name, where.
Keep it tight: definitions, not essays. Public-safe: no machine paths, no private branches, nothing about private ports.
Report `_build/tmp/codex-terminology-report.md` with the collision list and the proposed renames.
