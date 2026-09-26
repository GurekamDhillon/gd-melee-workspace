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


## 8. Fighter effect bindings and sword trails (2026-09-26)

`fx_bindings.json` sits beside the fighter's `.gfx.json` packages. Version 1 has `fighter`,
`host`, `unit_scale`, and `states[]`. Each state names its Melee `subaction`, Ultimate
`script`, and ordered `calls[]`. A call records its ACMD `frame`, `macro`, effect name,
package, source `bone` and mapped Melee `joint`, bone-local `offset` and `rotation`,
uniform `scale`, `follow`, ACMD branch conditions in `when`, and `end_frame`/`end_event`.
The engine should spawn the package at the indicated frame of the state's clock, transform its
offset by the live joint when `follow` is true, and detach at the explicit off/detach
frame or state exit. `emitter_life` lets a world-fixed burst finish naturally. The
`owner_destroy` end event retains an `EFFECT_FOLLOW_NO_STOP` instance until its
owner is destroyed or another action explicitly turns that effect off. The
offset scale is 1.0 for Sora's Ultimate rig, matching `acmd_to_ftcmd.py`; `+Z` is
source forward and `+Y` is up, as declared by each package's `space`. Schema:
`ports/ir/schema/fx_bindings.schema.json`. `when` preserves branches from the
decompiled script; the runtime must evaluate those conditions or explicitly choose
the same branch as the move implementation. Common `sys_*` effects are omitted from
bindings and remain Melee common-effect work.

### Sword trails from AFTER_IMAGE4_ON_arg29

Sora's effect scripts contain 27 ON and 27 OFF calls. Every pair is below; the
complete 29 arguments of each ON and argument of each OFF are also in
`_build/tmp/codex-fx/effect_census.json`. Texture hashes could not be resolved to
filenames in the fighter EffectLibrary dump. No explicit RGB colour appears in these
calls: colour is texture/material driven; the final two numeric macro parameters
are preserved raw in the census rather than mislabeled as RGB.

| Script | ON frame | Textures (Hash40) | Bones, local endpoints | Length | Colour | OFF frame, argument |
|---|---:|---|---|---:|---|---|
| trail/effect_attack11 | 8 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 16, [4] |
| trail/effect_attackhi3 | 33 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 37, [4] |
| trail/effect_attacklw3 | 8 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 15, [4] |
| trail/effect_attacks4hi | 14 | 0x1332cbbbcd / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 20 | texture driven | 25, [4] |
| trail/effect_attacks4 | 14 | 0x1332cbbbcd / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 20 | texture driven | 25, [4] |
| trail/effect_attacks4lw | 14 | 0x1332cbbbcd / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 20 | texture driven | 25, [4] |
| trail/effect_attackairn | 6 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 22, [3] |
| trail/effect_attackairn2 | 6 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 13, [6] |
| trail/effect_attackairn3 | 7 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 14, [3] |
| trail/effect_attackairf2 | 6 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 13, [6] |
| trail/effect_attackairf3 | 7 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 14, [3] |
| trail/effect_attackairhi | 9 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 19, [3] |
| trail/effect_attackairlw | 10 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 45, [3] |
| trail/effect_downattacku | 17 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 22, [3] |
| trail/effect_downattacku | 23 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 26, [4] |
| trail/effect_downattackd | 17 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 22, [3] |
| trail/effect_downattackd | 23 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 7 | texture driven | 26, [4] |
| trail/effect_slipattack | 16 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 8 | texture driven | 22, [4] |
| trail/effect_slipattack | 23 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 8 | texture driven | 28, [4] |
| trail/effect_specialhi | 6 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 14 | texture driven | 31, [3] |
| trail/effect_specialhi | 35 | 0xd5b4336ac / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 14 | texture driven | 41, [2] |
| trail/effect_specialairhi | 6 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 14 | texture driven | 31, [3] |
| trail/effect_specialairhi | 35 | 0xd5b4336ac / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 14 | texture driven | 41, [2] |
| trail/effect_speciallw | 4 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 14 | texture driven | 8, [3] |
| trail/effect_speciallw | 8 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0.5] → haver [0, 19, 1] | 14 | texture driven | 14, [0] |
| trail/effect_specialairlw | 4 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0] → haver [0, 13.8, 0] | 14 | texture driven | 8, [3] |
| trail/effect_specialairlw | 8 | 0x13dcc5dae1 / 0x1345cc8b5b | haver [0, 2, 0.5] → haver [0, 19, 1] | 14 | texture driven | 14, [0] |

An eventual trail renderer needs to sample both listed bone-local endpoints each
animation frame, retain the specified number of samples, construct a ribbon between
successive samples, UV-map the two textures, apply their colour and alpha with the
macro's blend/cull settings, and stop the matching trail on `AFTER_IMAGE_OFF` or
state exit. Rollback must reconstruct the same sample history. This importer does
not implement sword-trail rendering.

### Binding clock clarification

Each state also declares `clock`: `animation` means its call frames follow the
fighter clip, and `game` means frames since state entry. The six Firaga, Blizzaga,
and Thundaga Geno cast states use `game`, because their stand-in clips do not carry
Sora's animation frames. Their ACMD effect frames are converted through the same
`game_time()` motion-rate segments and Firaga start/cast/end offsets used by
`trail_magic_geno.py`.

`situation` optionally limits a call to `ground` or `air` when one Geno state
serves both. Sonic Blade's start uses it because the airborne `SonicStart`
effect is one unit higher than the grounded version; the later dash effects
have identical parameters in both scripts.
