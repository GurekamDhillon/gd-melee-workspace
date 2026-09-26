# Code task for Codex: the rest of the Geno effect simulation

Written 2026-09-26 by the coordinating Claude session. **Code only.** Do NOT run build.sh/run.sh,
run the game, launch other Codex processes, or touch Aurora/renderer files. You MAY compile the one
file you change to check syntax (see Acceptance). A Claude lane builds, runs the suite and checks in
game afterwards.

## Background

The Melee PC port has a native effect runtime ("Geno effects") that simulates Smash-Ultimate-style
emitters from a JSON effect IR. Read first: `melee/docs/geno.md` §20 (format, shader library,
runtime), `_research/geno-effects-runtime.md`, `ports/ir/schema/effects.schema.json`, then
`melee/pc/platform/gw_fx.c` (the simulation; loader, emission, particles, rollback re-simulation,
census, budget) and `gw_fx_internal.h`. The headless test is `fx_sim` (find it in
`melee/pc/platform/gw_tests_*.c`). Real packages to read for which fields occur:
`_build/agents/beta/gfx/*.gfx.json` (game-derived: read, never copy into the repo).

## What to add (in `gw_fx.c` / `gw_fx_internal.h`, plus `fx_sim` cases)

1. **Wave fluctuation** (the format's wave fields): the periodic offset/scale/alpha modulation.
2. **Curve loops**: the colour/alpha/scale curve loop settings the format already carries
   (loop, loop count, random start phase), which the sim currently ignores.
3. **Pattern (flipbook) animation modes**: fit_life / clamp / loop / random, with the atlas divide.
4. **Remaining emitter shapes** in the format (cylinder, box, line, disc variants, hollow/filled,
   sweep and caliber) not yet handled; list which the census packages actually use and do those first.
5. **Fade on stop**: when an emitter is detached, stop emission and let live particles fade with
   the format's fade-out rules instead of vanishing.
6. **UV randoms**: random initial UV scroll/rotation per particle.
7. **Budget:** the per-match cap (2000 particles / 64 emitter instances) is hit by 8 Blizzaga shots of
   11 emitters. Make the instance pool 256, and when the pool is full, refuse the newest instance's
   lowest-priority emitters (not a whole effect), counting refusals in the census. Keep particles at
   2000.

Everything must stay deterministic and rollback-safe exactly as the existing code is: all randomness
from the per-instance seeded PRNG, no wall-clock, no allocation in the per-frame path.

## Acceptance (you check these yourself)

- `gw_fx.c` compiles on its own: find the clang invocation build.sh uses for pc/platform C files
  (tools/port/portlib.sh) and run just that for `gw_fx.c` with `-fsyntax-only`; 0 errors, 0 new
  warnings.
- `fx_sim` gains one case per feature above, each asserting numbers (e.g. a wave's offset at a
  given frame, a looped curve's value after its period, the flipbook frame at 25/50/75% of life, a
  shape's spawn positions within its bounds, fade-out alpha after detach, the refusal count at the
  cap). You can't run them; write them so a reviewer can check them by reading.
- The existing `fx_sim` cases are unchanged.

## Rules

- Touch only `gw_fx.c`, `gw_fx_internal.h` and the file holding `fx_sim`. Work in the game repo
  checkout `melee/` on branch `pc-port`, uncommitted. No commits.
- If a format field's meaning is unclear, read `ports/ir/tools/ultimate_vfx_geno.py` (how it's
  produced) and say in the report what you assumed.

## Report (final message, also `_build/tmp/codex-fxsim-report.md`)

Files changed; each feature and its test; assumptions; the syntax-check command and result.
