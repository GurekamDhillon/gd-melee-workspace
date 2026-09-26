# Geno effects runtime - design (2026-09-26, lane beta)

**Design only; nothing built.** The renderer side waits for Codex's performance report (worktree codex-perf
owns the Aurora / shim_gx files now). The data side is built: the format is `melee/docs/geno.md` section 20,
the converter `ports/ir/tools/ultimate_vfx_geno.py`. Supersedes the route-(c) plan in
`ultimate-particles.md` section 3 for effects from other games (GD, 2026-09-26: "a real effect capability").

## 1. Goal and boundaries

Draw an effect from another game (Ultimate first; Firaga's `P_TrailFireBullet` is the first test) with its own
emitter behaviour and its own shading, inside a Melee match, rollback-safe and netplay-neutral. General: the
runtime knows the `.gfx.json` format, never a fighter.

Boundaries:
- Gameplay never reads effects. Effects are **visual state**: they are re-simulated, not snapshotted
  (section 5).
- Melee's own effects (HSD particles, effect models) are untouched; the runtime draws next to them.
- It draws through **Aurora directly** (our own WebGPU pipelines and WGSL shaders), not through the GX shim
  (GX's fixed TEV cannot express soft particles, distortion, or HDR colour).

## 2. Where it lives

| part | file (new) | half |
|---|---|---|
| package loader (`.gfx.json`, PNG, mesh JSON -> GPU textures / buffers) | `pc/platform/gw_fx_load.c` | native |
| simulation (emitters, particles; fixed step = the game frame) | `pc/platform/gw_fx_sim.c` | native |
| renderer (pipelines, draw lists, framebuffer copy) | `pc/platform/gw_fx_render.cpp` + `extern/aurora` hook | native (Aurora) |
| spawn / attach API for the game | `Geno_FxSpawn(name, gobj, jobj, flags)` etc. in `pc/geno/geno_game_fx.inc` | game half -> native (scalars + a guest JObj address) |
| geno.json binding | articles' / states' `"fx": [{"package", "effect", "joint", "frame"}]` | registry |

Why native, not game-half: the simulation needs floats, curves and random numbers at a rate (hundreds of
particles) that the game half has no reason to touch, and it must never enter a snapshot.

## 3. Simulation (the eft2 semantics, from the format's fields)

Per emitter instance: owner (a guest JObj address + the game frame it was attached), local transform, age,
emission accumulator, a particle pool (structure of arrays; cap per emitter from `max_particles` or 256).

Per game frame (called after the game's own effect update, so attached joints are final):
1. **Emitter matrix**: the owner joint's world matrix (read from guest memory, read-only) x `transform`.
   `follow` = srt / translate / none decides whether live particles move with it.
2. **Emission**: after `start` frames, for `duration` (or while attached): `rate` per `interval` frames (+
   randoms), or `by_distance` (particles per `unit` of emitter travel, capped); `one_time` = a single burst.
3. **Spawn**: position from `shape` (sphere_fill with `caliber`, sweep, divisions...), velocity =
   `all_direction` x radial + `direction` x `direction_scale` (in the emitter frame) + `inherit` x emitter
   velocity, randomised by `random_pct`; life (+ random), scale (+ random), rotation init (+ random), per-
   particle random seed.
4. **Integrate**: velocity x `air_resistance`, + gravity (world or emitter frame), position += velocity;
   rotation += add; age += 1.
5. **Curves**: colour0 / alpha0 / colour1 / alpha1 / scale / param evaluated at age / life (8-key linear, loop
   rates as specified); `wave` fluctuation; texture pattern frame and UV scroll / scale / rotate per sampler.
6. **Kill** at life; an emitter ends when its owner goes away (fade per `emission.fade`).

Deterministic: one PRNG per emitter seeded from (package, emitter, owner, spawn frame), no host time. That is
what makes re-simulation exact (section 5).

## 4. Rendering

**Draw point**: after Melee's opaque and translucent world passes, before the HUD - one Aurora hook
(`aurora_fx_draw(view, proj, depth, color)`), the only change to Aurora. Particles are depth-tested against
Melee's depth buffer.

**Pipelines** (created at package load, one per distinct material):
- blend: alpha, add, sub, mul, screen; depth test / write per `material`; cull per `display_side`.
- vertex: billboard modes (billboard, y_billboard, plate_xy/xz, directional_y / polygon) built in the vertex
  shader from per-instance data (position, scale, rotation, colour0/1, UVs); **mesh particles** (`kind: mesh`)
  instance the emitter's mesh with the same per-instance data; stripes later.
- fragment: generated per emitter from `program` (section 4.1), or the standard eft2 combine for `normal`
  shaders (colour = lerp(colour1, colour0, texture) etc., the modes EffectLibrary names).
- soft particles: fade by (scene depth - particle depth) / `soft_particle.distance` - needs the depth buffer as a
  texture (Aurora already has it as an attachment; the hook samples a copy).
- fresnel / near / far alpha: in the fragment from the view vector and depth.
- **framebuffer copy** for distortion and heat haze (Firaga's `fire_rif1` samples the framebuffer): once per
  frame, copy the colour target before the effect pass into a sampled texture (a `copyTextureToTexture` into
  a same-size texture), bind it as the "framebuffer" input.

### 4.1 From the source program to WGSL

The eft2 fragment programs of these effects are straight-line (the converter checks): texture samples, ALU,
an alpha-test kill, outputs in `$r0..$r3`. The runtime's generator turns the op list into WGSL at load:
registers -> `let` temporaries, `texs` -> `textureSample(t<slot>, s<slot>, uv)` with the swizzle, `ffma` /
`fmul` / `fadd` / `fmnmx` / `fset` / `f2f floor` / `mufu rcp|rsq` -> their WGSL, `kil` -> `discard`. Inputs:
- **varyings** `a[0xNN]`: produced by our vertex stage with the same meaning the eft2 vertex program gives them.
  Known from reading the programs (converter output, fire / sphere / ring emitters): `a[0x80..0x8c]` particle
  colour0 rgb + alpha0, `a[0x90..0x94]` uv of sampler 0, `a[0x98..0x9c]` uv of sampler 1 (after pattern and
  scroll), `a[0xa0..0xa4]` uv of sampler 2, `a[0xb0]` / `a[0xb4]` alpha1 / the indirect (warp) strength,
  `a[0xc0..0xcc]` colour1 rgba, `a[0xc4]` the particle's age ratio, `a[0xd4]` fade, `a[0xe0..0xf8]` view /
  normal vectors (fresnel). **To confirm**: translate the matching vertex programs (the same disassembler, the
  first NVN block of each Shader.bnsh) and read each output store; the converter already has the code blocks.
- **uniform words** `c9[...]` = the emitter's static block (the emitter record itself: e.g. `c9[0x100/0x104]`
  the indirect scales, `c9[0x5e8]` the alpha-test threshold, `c9[0x5c8/0x5cc]` fresnel params), `c16[...]` =
  the per-emitter dynamic block (`c16[0x0]` / `c16[0x20]` colour scales, `c16[0x44..0x4c]` the fade). Mapped by
  offset from EffectLibrary's struct layout; each one used by the four Firaga-family programs is listed in
  `ultimate-particles.md` 5.4.
- **texture handles** 0x8 / 0xa / 0xc = sampler slots 0 / 1 / 2 (inferred from the programs; to confirm).

Why translate instead of re-authoring a shader per effect: every emitter of every effect has its own program
(Firaga alone has 10); hand-writing them does not scale, and the translation is exact where the code is.

## 5. Rollback, netplay, LAB

- Effects are visual only. On a rollback the runtime **discards and re-simulates** from the attach events:
  every attach is recorded with its game frame (a ring of the last 128 frames' events, like the pad log); a
  resim replays them, and the deterministic PRNG (section 3) makes the result identical. Nothing enters
  `gw_snap`.
- Netplay: packages are mod content, hashed into the fighter's identity like any mod file (a mismatch greys
  the fighter out, as today).
- LAB: the rewind treats it like a rollback. A LAB overlay shows emitter / particle counts (the census, as in
  geno events 38-41 today).

## 6. Budget and cost estimate

- Budget: 2 000 live particles, 64 emitters, 16 pipelines per match (Firaga v2: 32 particles, 10 emitters).
  One instanced draw per emitter.
- Estimate: loader + simulation (no renderer): ~1 week; Aurora hook + pipelines + WGSL generator + billboard
  and mesh particles: ~1-1.5 weeks; soft particles + framebuffer copy + distortion: ~0.5 week; vertex-program
  confirmation of the varying map + Firaga side-by-side tuning: ~0.5 week. **~3-3.5 weeks.**
- Order: (1) loader + sim + a debug census (no drawing; verifiable numerically) - can start now, it touches no
  renderer file; (2) after Codex's report: the Aurora hook and pipelines; (3) Firaga end to end; (4) the other
  spells (P_TrailIce*, P_TrailThunder*), then any effect.

## 7. Decisions for GD / the coordinator

1. The Aurora hook (one draw callback + a depth copy + a colour copy per frame) is the only renderer change;
   it lands after Codex's performance work.
2. Effects re-simulate on rollback instead of snapshotting (cheaper, exact with the seeded PRNG).
3. Particle budget above (2 000 / match).
