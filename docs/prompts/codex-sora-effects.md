# Code task for Codex: import the rest of Sora's effects, and bind them to his moves

Written 2026-09-26 by the coordinating Claude session. **Code only.** Do NOT build or run the game,
run build.sh/run.sh, launch other Codex processes, or touch the engine/renderer (`melee/`). Write the
code, run the offline checks below, and stop. A Claude lane installs, draws and checks in game.

## Background

Sora is ported from Smash Ultimate (fighter id **`trail`**, never `sora`) into a Melee PC port with
our own engine extensions ("Geno"). Effects go through a pipeline:

  Ultimate `ef_trail.eff` -> EffectLibrary dump -> `ports/ir/tools/ultimate_vfx_geno.py` (importer)
  -> a Geno effect package (`<set>.gfx.json` + tex/ + mesh/; the effect IR, described in
  `melee/docs/geno.md` §20 and `ports/ir/schema/effects.schema.json`) -> the native runtime.

Read the importer's docstring, geno.md §20 (20.1 format, 20.2 shader library, 20.3 runtime and the
`"fx"` binding) and `_research/geno-effects-runtime.md` first.

Today only the four magic emitter sets are imported (P_TrailFireBullet, P_TrailIceBullet,
P_TrailThunderBullet, P_TrailThunderCloud; outputs in `_build/agents/beta/gfx/`, with the dump the
importer read). The EffectLibrary dump of `ef_trail.eff` is at `_build/ultimate-vfx/ef_trail/` (one
folder per emitter set; the EffectLibrary build is in `_build/ultimate-vfx/EffectLibrary/`). It is
game-derived and git-excluded; never copy it into the repo.
They are bound to Geno articles (projectiles) through geno.json `"fx"`. Everything else Sora shows -
sword swing effects, hit sparks, the Keyblade glow, dash/landing dust specific to him, counter and
Sonic Blade effects - is missing.

**Baseline:** build on workspace commit `1a9b4ce` (the importer now has `texture_flow()` shader params
and the package `"space"` field: +Z forward, +Y up). For the byte-identity check below, first
regenerate the four magic packages with the UNCHANGED importer at 1a9b4ce into
`_build/tmp/codex-fx/baseline/` and compare against that, not against `_build/agents/beta/gfx/`
(which predates 1a9b4ce).

## What to do

1. **Census.** List every emitter set in the dump, and every effect call in Sora's effect scripts
   (Ghidra decompilation: `C:/Users/Gurek/ghidra-projects/sora_acmd/effect/*.c`, indexed by
   `index.tsv`; parse them the way `ports/ir/tools/acmd_parse.py` parses game scripts - reuse its
   helpers by importing it, do not edit it). For each call: script (motion), frame, macro
   (EFFECT, EFFECT_FOLLOW, EFFECT_FLW_POS, LANDING_EFFECT, AFTER_IMAGE4_ON..., EFFECT_OFF_KIND, etc.),
   effect name (Hash40 resolved where possible), bone, offset, rotation, scale, and the off/detach call
   that ends it.
2. **Import all of Sora's own sets** (names starting `P_Trail` / `trail_` or whatever the census shows
   as his) with the existing importer. Improve the importer where the census shows a gap (an emitter
   field or shape it doesn't map, a sub-section that decides the shader type). Keep it general, not
   Sora-specific. Every package must validate against `effects.schema.json`.
3. **Binding for fighter moves.** Today `"fx"` binds only to articles. Write the fighter-side binding
   as data, not engine code: a new file per fighter, `fx_bindings.json` next to the packages, listing
   for each Melee state/subaction the effect calls (frame, package, bone, offset/rotation/scale in
   Melee units, follow or world-fixed, end frame or end event). Use the same unit scale and bone mapping
   the rest of the port uses (see how `acmd_to_ftcmd.py` converts hitbox offsets and bones; import it,
   do not edit it). Add its schema: `ports/ir/schema/fx_bindings.schema.json`. Document the format as
   a new subsection in `_research/geno-effects-runtime.md` (not geno.md, which belongs to the engine
   lane); the engine lane will implement reading it.
4. **Sword trails** (AFTER_IMAGE macros) are a separate kind in Ultimate. Don't implement them; list
   every AFTER_IMAGE call with its parameters (texture, bones, colour, length), and write what a
   runtime needs to draw them, in the research doc.
5. **Common effects** Sora borrows from the shared pool (e.g. `sys_*` hit sparks, dust) are out of
   scope: list them in the report with their call counts; Melee's own common effects cover those.

## Files you may touch

`ports/ir/tools/ultimate_vfx_geno.py`, a new `ports/ir/tools/trail_fx_bindings.py` (or a general
name), new `ports/ir/tools/test_fx_bindings.py`, new `ports/ir/schema/fx_bindings.schema.json`,
`_research/geno-effects-runtime.md` (append only). Other files in `ports/ir/tools` have other agents'
uncommitted work; don't edit them.

## Acceptance (you check these yourself)

- The four magic packages come out byte-identical to the existing ones in `_build/agents/beta/gfx/`
  (the importer changes must not alter them), or every difference is listed and explained.
- Every imported package validates against `effects.schema.json`; `fx_bindings.json` validates
  against its new schema.
- `test_fx_bindings.py` (plain `python`): for at least five moves (e.g. jab 1, forward smash, a Sonic
  Blade dash, Counter, up special), asserts the frame, package, bone and offset of each effect call,
  read from the decompiled C by hand and cited in a comment (file + line), and converted with the
  port's scale. It passes.
- Outputs go under `_build/tmp/codex-fx/`. Never into a mods folder or the repo (all of it is derived
  from the game).

## Rules

- No commits, pushes or merges; list the files changed.
- If an emitter can't be expressed with the three shader types, map it to the nearest one, mark it
  in the package (`"approx": "<why>"`), and list it in the report. Don't invent new shader types.
- If the task is wrong or impossible as written, stop and say so rather than working around it.

## Report (final message, also written to `_build/tmp/codex-fx-report.md`)

1. Files changed and what.
2. The census: sets imported (count, emitters, textures, meshes), shader-type counts, the approx list.
3. The binding table summary: states covered and effect calls per state; the common-effect list with
   counts; the AFTER_IMAGE list.
4. The test output and the byte-identity result for the four magic packages.
5. The exact commands.
