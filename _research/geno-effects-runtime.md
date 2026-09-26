# Geno effects runtime - design (2026-09-26, lane beta; revised the same day)

**This revision wins over the first one** (GD's scope change, 2026-09-26): no 1:1 port of Ultimate's shaders.
Higher-fidelity effects in Aurora, close enough to Ultimate, from a **small library of general, parameterised
effect shaders**; emission, motion, colour / alpha curves, textures and blend modes stay faithful.

## 0. The pipeline: the effect IR

```
source game --importer--> Geno effect IR (.gfx.json) --> Geno effect runtime (native) --> Aurora
```

The same shape as the character IR (`ports/ir/`): the `.gfx.json` format is **game-neutral**, one stage of the
port pipeline. Schema: `ports/ir/schema/effects.schema.json`; reference: `melee/docs/geno.md` section 20.
- Every **material is "shader type + parameters"** from the runtime's shader library (section 4). There is no
  IR of source shader programs: an importer reads them only to pick the type and its parameters.
- Importers: `ports/ir/tools/ultimate_vfx_geno.py` (Ultimate eft2 / VFXB). Halberd's Brawl effects (REFF /
  REFT) could get an importer later that writes the same format.
- Built so far (lane beta): the importer's type mapping + bloom parameters; the native loader, simulation and
  numeric census (`melee/pc/platform/gw_fx.c`, test `fx_sim`). Not built: the game-half attach / per-frame
  driver and the geno.json `"fx"` binding (next), the renderer (after Codex's report).

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
| package loader (`.gfx.json`; later PNG / mesh -> GPU) + simulation + census (**built**) | `pc/platform/gw_fx.c` (`gw_Fx_Find/Attach/Detach/Frame/Stat/Census`) | native |
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
- fragment: one of the effect shader library's types, chosen by `material.shader` (section 4.1).
- soft particles: fade by (scene depth - particle depth) / `soft_particle.distance` - needs the depth buffer as a
  texture (Aurora already has it as an attachment; the hook samples a copy).
- fresnel / near / far alpha: in the fragment from the view vector and depth.
- **framebuffer copy** for distortion and heat haze (Firaga's `fire_rif1` samples the framebuffer): once per
  frame, copy the colour target before the effect pass into a sampled texture (a `copyTextureToTexture` into
  a same-size texture), bind it as the "framebuffer" input.

### 4.1 The effect shader library (replaces per-emitter program translation)

A handful of WGSL shaders, each parameterised by the material; the importer maps every source emitter to the
nearest one (Ultimate: by what its compiled programs read, `shader_type()` in the importer).

| type | what it draws | parameters |
|---|---|---|
| `sprite` | texture(s) x the colour ramps | `color`: `modulate` (color0 x tex) or `lerp` (lerp(color1, color0, tex)); `alpha`: `texture` or `texture_product` |
| `warp` | texture `offset` displaces texture `base`'s UVs (animated fire, energy) | + `strength[2]`, `base`, `offset` |
| `distortion` | displaces the **frame copy** (heat haze, refraction) | + `strength[2]` |

Common to all: UV scroll / scale / rotate and pattern (atlas) animation per sampler, the colour / alpha curves,
the blend mode (alpha, add, sub, mul, screen), `alpha_test`, `fresnel` (alpha by view angle), soft particles
(depth copy), near / far alpha, and **bloom** (section 4.2).

Firaga's mapping (the importer, GD's ef_trail.eff): 7 warp (fire1/2/3, fireline1, sphere1, spherering1, circle2),
2 sprite (flare1, spark2: lerp), 1 distortion (fire_rif1). Ice: 10 sprite, 1 warp; both Thunder sets: sprite.
This matches what reading the programs by hand found (`ultimate-particles.md` 5.4).

The disassembly and the vertex-output map stay as **reference** for choosing the mapping (`shader/*.txt`
beside the package; `--keep-programs` puts the op list and the map in `program`); the runtime never reads them.
The vertex-output map (varying -> source field, a backward slice of each vertex program's output stores):
`a[0x80..0x88]` color0 x ColorScale, `a[0x8c]` alpha0, `a[0x90..]` color1 or uv0 (per program), uvK from
TexScrollAnimK (u / v by address parity), `a[0xb4]` ParamAnim (the warp strength's animation), `a[0x70..0x7c]`
position.

### 4.2 Effect-only bloom (GD approved, 2026-09-26)

Geno effects write their over-1.0 (HDR) contribution into a separate bloom buffer during the effect pass; it is
thresholded, blurred (a downsample / upsample chain, 4-5 levels) and added over the frame after the effect draw
hook. Melee's world and fighters never enter it: the vanilla look does not change. Per material:
`bloom {threshold, intensity}`; the Ultimate importer derives intensity from ColorScale x the peak colour0 (the
part over 1.0; spark2 2.0, fireline1 1.0, the fire bodies 0.1-0.5).

## 5. Rollback, netplay, LAB

- Effects are visual only. On a rollback the runtime **restores and re-simulates**: the game half passes its
  own frame counter (game memory, so a rollback restores it); a frame not after the last one seen restores the
  state kept for the frame before it (a ring of 16 per-frame copies, `FX_RING`; older = reset) and the resim
  steps it again. The seeded PRNG makes the result identical (`fx_sim` checks it). Attaches made during the
  resim are made again by the game code. Nothing enters `gw_snap`.
- Netplay: packages are mod content, hashed into the fighter's identity like any mod file (a mismatch greys
  the fighter out, as today).
- LAB: the rewind treats it like a rollback. A LAB overlay shows emitter / particle counts (the census, as in
  geno events 38-41 today).

## 6. Budget and cost estimate (re-estimated for the shader library + bloom)

- Budget: 2 000 live particles, 64 emitters, 16 pipelines per match (Firaga: 32 particles, 10 emitters).
  One instanced draw per emitter.
- Done: loader + simulation + census (native, headless-tested). Remaining:
  - game-half driver (attach on article spawn, detach on destroy, the per-frame call, the geno.json `"fx"`
    binding) + a Sora check in game: ~2-3 days
  - the rest of the simulation (wave, curves' loops, pattern animation, shapes beyond sphere / circle /
    point): ~2 days
  - after Codex's report: the Aurora hook + depth / colour copies + billboard and mesh particles: ~1 week
  - the shader library (sprite, warp, distortion; fresnel, soft particles, alpha test): ~3-4 days
  - effect-only bloom (buffer + threshold + blur chain + composite): ~2-3 days
  - Firaga side by side, then Ice / Thunder, tuning the mapping: ~3 days
  **~3 weeks** (down from 3-3.5: no WGSL generator, no per-program fidelity work; bloom added).

## 7. Decisions for GD / the coordinator

1. The Aurora hook (one draw callback + a depth copy + a colour copy per frame, + the effect-only bloom
   composite) is the only renderer change; it lands after Codex's performance work.
2. Effects re-simulate on rollback instead of snapshotting (cheaper, exact with the seeded PRNG).
3. Particle budget above (2 000 / match).
