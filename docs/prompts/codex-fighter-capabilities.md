# Parallel packet P2: fighter capabilities the modifier pool is missing (engine) (2026-10-04)

Rules: `docs/prompts/codex-parallel-rules.md` (read it first). You own: NEW files under `melee/pc/gameworld/` and
`melee/pc/platform/` named `script_fighter_caps*` / `gw_script_fighter_caps*`, plus the minimal `TARGET_PC` hooks you
need in `melee/src/melee/ft/` (not `ftcoll.c`: that is another job's; if you need a hook there, request it).

Why: the Envoy modifier pool (`docs/superpowers/specs/2026-10-04-envoy-loot-and-modifiers-design.md`) had to leave out
five showpiece items because the engine cannot do them (`_build/tmp/codex-envoy-modifiers-step2-report.md`,
"Unsupported examples"): Second Wind, Aerialist, Juggernaut, Hoarder, Conductor. Add the general capabilities, as
script calls in the style of the existing `gd.fighter_mod` (per fighter entity incl. CPUs and sub-fighters, offline
gameplay gate, cleared on scene change and script unload, covered by the LAB snapshot and rewind with a 0-byte proof,
documented, tested in the suite pattern, each with a single-feature catalogue demo):
1. **Air-jump count**: set how many air jumps a fighter has (0-8), correct for multi-jump fighters (Kirby, Jigglypuff)
   and for the jump being restored on landing, ledge and hit as retail does.
2. **Action restrictions**: forbid shield, air dodge, running/dash, grab, or specials for a fighter (each a flag); the
   input is ignored cleanly (no stuck state, CPUs do not lock up), with a stated list of the action states gated.
3. **Flinch resistance (armour)**: hits below a damage threshold, or below a knockback threshold, do not interrupt the
   fighter (they still take the percent); find how retail does light and heavy armour (Yoshi's double jump, Bowser, the
   giant and metal states) and reuse it rather than inventing one.
4. **Give an item**: put a chosen or random item into a fighter's hands safely (respecting what a fighter can hold and
   the item spawn rules), and a hook for "at stage start".
5. **Targeting helpers**: nearest opponent to a fighter, opponents within a radius, line of sight not required; and a
   way to apply a short hitstun/hitlag bonus or a status-style timed value to a chosen target from a script event.
6. **Timed self effects**: brief intangibility and invincibility, metal for a duration, size change for a duration,
   each cleaning itself up.
Report `_build/tmp/codex-fighter-capabilities-report.md`: signatures, file:line, the retail mechanisms you reused, what
could not be done, the shared-file edits you made, and for each of the five items how the Envoy job should now express
it as data (do not edit the Envoy mod yourself).
