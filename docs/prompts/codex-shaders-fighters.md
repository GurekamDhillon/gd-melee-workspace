# Codex packet H: custom shading on fighters and vanilla stage geometry (2026-10-03)

Workspace `<workspace>`; the game is the separate checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md`, `_research/geno-effects-runtime.md`). Aurora (by
encounter, https://github.com/encounter/aurora, MIT) is at `melee/extern/aurora/`; how it is built and whether we already carry
patches to it: `_build/build_aurora_melee.bat`, `_build/patches/`. Both trees are deliberately dirty: do NOT commit, reset,
stash, revert or reformat anything. Do NOT run `tools/port/build.sh`, do NOT rebuild Aurora, do NOT launch the game (the
integrator does). Keep every file compilable at every save.
THREE other Codex jobs are editing right now. Packet G (`docs/prompts/codex-shaders.md`: shaders as data, full-screen passes,
custom materials for OUR OWN loaded models) owns `melee/pc/platform/gw_fx_render.cpp`, `gw_fx.c` and its new files: read its
packet so your work composes with it, and do not edit its files. Engine batch 2 owns `gw_script*` additions, `pc/gameworld/`,
`cm/camera.c`; a menu job owns `gm/gmfrontend*`, `sysdolphin/`. Work in NEW files; touch shared files last and minimally,
re-reading them first.

## The owner's goal
"I want to be able to do anything with our shaders." This packet is the hard part: the things Melee itself draws (fighters,
items, vanilla stages) go through Aurora's GX emulation, which GENERATES a WGSL shader per TEV configuration. We do not own
those shaders. Wanted: cel shading, rim light, outlines, dissolve, hit-flash and tint overrides, per-fighter material effects,
normal-buffer access for post-processing.

## Phase 1: establish exactly what is possible (write it down before coding)
Read Aurora's GX pipeline (`melee/extern/aurora/lib/gfx/`: the shader generation, pipeline cache, draw recording, the public
extension API in `include/aurora/gfx.hpp`, the EFB pass layout incl. the normal attachment that `gw_fx_render.cpp`'s header
mentions) and our GX shim (`melee/pc/platform/shim_gx*`). Answer with file:line: where the generated WGSL is assembled; what
identifies a draw (can we know "this draw belongs to fighter N / the stage / an item" at record time: via our shim setting a
tag around the fighter's render callback?); which hooks exist without modifying Aurora; what a minimal Aurora change would be
(a callback to post-process generated shader source keyed by a draw tag, or extra attachments: object-id / normals), kept as a
carried patch in the same form as any existing ones.

## Phase 2: build the least invasive route that works, in this preference order
A. No Aurora change: tag draws in our shim (fighter/item/stage/kit, with player slot) and write an object-id + normal
   G-buffer through whatever Aurora already exposes, so packet G's full-screen passes can do outlines, rim light, cel
   quantisation and per-fighter effects in screen space (`gd.post_*` inputs gain `object_id`, `normal`). If Aurora cannot give
   us this without changes, say precisely why.
B. A small carried Aurora patch (opt-in, zero cost when unused, generated shaders byte-identical when no override is active):
   a hook that lets us append a mod-supplied WGSL function to the generated fragment shader for tagged draws
   (`fn gd_surface(color: vec4f, in: ...) -> vec4f` with documented inputs: lit colour, vertex colour, normal if available,
   world/eye position, uv0, time, per-object params), selected per object from Lua:
   `gd.fighter_shader(port, name_or_path, {params})`, `gd.stage_shader(...)`, cleared on unload/match end.
   Pipeline-cache keys must include the override so nothing leaks between objects.
Implement A, and B if A proves insufficient for per-material effects (dissolve and cel shading on the surface itself need B).
Constraints as in packet G: unused = no cost and identical picture; never crash on a bad shader (report and skip); visual
only, no game-state effect; 120 fps target, state the cost; Aurora changes minimal, isolated, documented as a patch file with
the upstream commit it applies to, and credited.

## Deliver
Tests where possible headlessly (tagging state machine, cache-key separation, shader splice text, parameter layout), three
example shaders (cel + outline, rim light, dissolve) in a sample mod, `docs/shaders.md` additions coordinated with packet G
(append a clearly marked section; do not rewrite theirs), `CREDITS.md` entries for anything you draw on.
Report `_build/tmp/codex-shaders-fighters-report.md`: Phase 1 findings with file:line, the route chosen and why, the Aurora
patch (if any) and how to rebuild Aurora with it, unverified items, and an on-screen test plan for the integrator.
