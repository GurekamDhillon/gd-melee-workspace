# Codex packet G: open up custom shaders (2026-10-03)

Workspace `<workspace>`; the game is the separate checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `melee/pc/geno/CLAUDE.md`, `docs/scripting.md`, `_research/geno-effects-runtime.md`, and the
render review `_build/audit-20261003/render-effects/` hand-back summarised below). Both trees are deliberately dirty: do NOT
commit, reset, stash, revert or reformat anything. Do NOT run `tools/port/build.sh` and do NOT launch the game (the integrator
builds and tests). Keep every file compilable at every save.
TWO other Codex jobs are editing right now: engine batch 2 (`melee/pc/platform/gw_script*.c|inc` new files for camera/fighter
mods/bench, `melee/pc/gameworld/script_*`, `melee/src/melee/cm/camera.c`, `melee/pc/geno/geno_lab_mode.c`) and a menu job
(`melee/src/melee/gm/gmfrontend*`, `melee/src/sysdolphin/`, `melee/pc/platform/gw_settings.c`, `shim_vi.c`). Put your code in
NEW files wherever possible; where you must touch a shared file (`gw_script.c` registration tables, `script_game.c`), make that
edit last, small, and re-read the file immediately before editing it. Never overwrite someone else's hunk.
Credit: name in the report and in `CREDITS.md` any outside technique or reference you draw on; consult, never copy.

## The owner's goal
"I want to be able to do anything with our shaders." Today (`melee/pc/platform/gw_fx_render.cpp`, `gw_fx.c`): one built-in WGSL
module with a mode switch, drawn only as particles/effect meshes at one point in the frame through Aurora's public extension
API (`aurora/gfx.hpp`: `push_custom_draw`, `resolve_pass`, `create_pass`), an effect-only bloom, a frame copy and depth
snapshot; nothing shader-related is exposed to Lua; kit map models (`gd.model_*`, drawn in `melee/pc/platform/gw_script.c`
~5260-5330 and `gw_script_model_draw.inc` with emulated GX state: one fixed key light, no stage lights) and everything of
Melee's own use Aurora's generated shaders. Hard constraints: stay inside Aurora's public extension API (do not edit Aurora or
`shim_gx`); a frame that uses none of this costs nothing and renders exactly as before; performance target 120 fps (state the
cost model of each feature and add `gd.perf`-visible counters); offline/visual only, so it must not affect game state,
rollback or determinism; a bad shader must never crash or blank the game: compile errors are reported (log + Lua return) and
the draw is skipped.

Build these three, in this order, each usable on its own:

## 1. Shaders as data
A mod can supply its own WGSL for an effect. Define a small, documented contract: the mod provides a fragment function body
(and optionally a vertex displacement function) that is spliced into our module with a fixed, documented set of inputs
(particle/mesh varyings, the three package textures and samplers, the scene copy and depth, time, per-effect parameters as a
uniform block of named floats/vec4s declared in the effect's data, camera/projection). Compile at load, validate, cache by
content hash, report errors with the mod's file and line. Loadable from a mod folder (same containment rules as
`gw_script_mission.inc`'s path checks) and hot-reloadable when the file's stamp changes (developer workflow: edit, save, see).
Works for effect packages (the IR's `material.shader`) and from Lua (item 2's API). WGSL has sampling restrictions inside
non-uniform control flow: document them where the mod author will read them.

## 2. Full-screen passes
A post-process chain over the finished 3D picture (and optionally before the HUD: decide the insertion points Aurora's API
allows and say which exist: after world, after effects, after HUD), each pass a mod-supplied WGSL fragment with inputs: scene
colour, scene depth (linearised helper provided), previous pass, time, resolution, named parameters. Lua API, e.g.
`gd.post_add(name_or_path, {order=, params={...}, stage="world"|"final"})` -> handle, `gd.post_set(handle, {params})`,
`gd.post_remove(handle)`, `gd.post_clear()`; cleaned up on script unload/match end/scene change; refused online only if it can
affect state (it should not: say why it is safe). Ship four small example passes as a sample mod with a README: colour grade
(LUT-free: lift/gamma/gain + saturation), vignette, depth-based outline, whole-scene bloom. Half-resolution option per pass.

## 3. Custom materials for our own models
Kit/mission models loaded through `gd.model_load` can opt into our own pipeline instead of the emulated GX one: a material
described next to the mesh (a small JSON or fields in the existing sidecar) selecting a built-in material or a mod WGSL
fragment, with albedo/atlas, optional normal map, emissive, opacity, roughness-like scalar, and lighting from a small set of
script-set lights (`gd.light_set{dir=, color=, ambient=}`) defaulting to the current fixed key light so existing levels look
the same. Must depth-test and write depth consistently with the rest of the scene so fighters, items and vanilla effects sort
against it exactly as they do against today's kit pieces (read `melee/pc/gameworld/script_stage_render_pass.inc` and
`script_model_order.inc`: opaque pieces draw once in camera mode 2; translucent pieces are split far/near around the fighter
plane). Provide a proper glass material: the current glass atlas is nearly invisible when drawn once (its old look came from
being drawn 3-4 times), so give glass an authored opacity/tint and a fresnel-style edge, and make the existing glass kit part
use it by default if that is contained; otherwise say what the art side must change. Models without a material file render
exactly as today.

## Tests and docs
Headless tests in the suite's pattern for everything that does not need a GPU (contract splicing, parameter block layout,
validation and error reporting, path containment, handle lifetime and cleanup, material sidecar parsing, defaults preserved);
say what can only be checked on screen. `docs/scripting.md` gets the new API; add `docs/shaders.md` as the author's guide (the
contract, inputs, examples, the WGSL differences from GLSL/HLSL that bite, performance notes).

## Report
`_build/tmp/codex-shaders-report.md`: what each part does with file:line, the exact contracts, which Aurora extension points
each uses and what Aurora does not allow (so the next step is known), cost model, tests, unverified items, credits, and an
on-screen test plan for the integrator (Lua snippets, what should be seen, what to measure with `gd.perf`).
