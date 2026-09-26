# Ultimate particles in Melee (Sora's magic) - research spike

**Written 2026-09-26 (lane beta). Research only: no engine or tool change came out of it.** Supersedes
nothing; the placeholder models it replaces are `ports/ir/tools/trail_magic_models.py` (melee
`docs/geno.md` 19.10).

GD: the placeholder spell models "ABSOLUTELY need to be replaced with the Ultimate particles". This
note is what the particles are, what Melee can draw, and three ways to get from one to the other.

## 1. Ultimate's side: `effect/fighter/trail/ef_trail.eff`

### 1.1 Container

`experiment/tooling/ultimate/workspace/extracted/effect/fighter/trail/`: one `ef_trail.eff`
(12,227,544 bytes) and `trail/` (5 `.nutexb` sword-trail textures, keyblade swing strips).

| layer | what (read with a 40-line Python walker, `scratchpad` not kept) |
|---|---|
| `EFFN` (Smash's wrapper) | u32 count 113 at +8, a 16-byte row per effect, then the effect NAMES (`TRAIL_FIRE_BULLET` ...), then the VFX binary at 0x1000 |
| `VFXB` v22 (0x16) | NintendoWare "eft2" / VFX binary, Switch generation (the format of Smash Ultimate, SMO, ...). Little-endian. Blocks are `magic, size, child offset, next offset, attr offset, binary offset, pad, child count` (0x20 bytes) |
| `ESTA` | the emitter-set array: 113 `ESET`s (= the 113 EFFN names, as `P_Trail...`) |
| `ESET` | an effect: a name and its `EMTR` children (4-14 each; 724 emitters in the file) |
| `EMTR` | one emitter: name at binary+0x10, then the ~0xA80-byte emitter record (below); child `EMTR`s = sub-emitters spawned by its particles |
| `GRTF` (3.68 MB) | a `BNTX` of **117 textures** (`BRTI`): Sora's own (`ef_trail_cloud00..02`, `ef_trail_beam..`, `ef_trail_aura00`, `ef_trail_color00`) and shared ones (`ef_cmn_fire00/05`, `ef_cmn_ice00`, `ef_cmn_flare01-03`, `ef_cmn_smoke*`, `ef_pikachu_lightning06`, ...) |
| `G3PR` (896 KB) | **primitives**: small meshes emitters draw instead of quads (rings, lightning strips, shards) |
| `GRSN` (5.3 MB) | **compiled shaders** (Switch GPU binaries): the per-emitter combiners - this is where Ultimate's look lives |

### 1.2 The magic's effects (emitter names, in order)

The article scripts (our acmd dump, `trail.acmd.json`, effect rows) call `EFFECT_FOLLOW` of hashed
names; the ESET names match 1:1 by meaning:

| effect | emitters |
|---|---|
| `P_TrailFireHold` (charge) | flare3_add flare2_add fire1 fire2 flash2 flash3 flash1 flare1_add |
| `P_TrailFireShot` (cast) | flare2_add fire1 impact3_2 impact1_2 line1 impact3_1 impact1_1 impact2 flash3 |
| **`P_TrailFireBullet`** (Firaga in flight) | fire_rif1 spherering1 fire3 sphere1 fire1 fire2 fireline1 circle2 flare1 spark2 |
| `P_TrailFireImpact` / `_End` | ring1 / flare2_add flash2 |
| `P_TrailIceHold` / `_Shot` | 9 / 10 emitters (smoke, flares, fragments, wind) |
| **`P_TrailIceBullet`** (a Blizzaga shard) | pointLight flareBase smoke2 fragment_front_Copy1 fragment_front powderFlash BulletFlare BulletSmoke Bullet1 parts flash |
| `P_TrailIceBulletEnd` | flash fragment_front fragment2 |
| **`P_TrailThunderCloud`** | flare1 cloud1 impact1 light1 flare2 |
| **`P_TrailThunderBullet`** (the bolt) | lightning3_sub lightning2 lightning1 lightning3 |
| `P_TrailThunderBulletTop` / `_End` / `_Hit` | 6 / 4 / 14 emitters (impact flashes, stone debris, rings) |

So a single Firaga in flight is 10 emitters, a Blizzaga shard 11 (x8 shards), a Thundaga strike 5 +
4 (+ the top flash and ground hit): Ultimate's "look" is 10-30 overlapping emitters per spell.

### 1.3 Inside an emitter (partial decode)

`fire1` of `P_TrailFireBullet` (EMTR at 0x97dc0, record 0xAC0 bytes), read as floats: plain values
sit where eft2's emitter record keeps them - e.g. at +0x0B0..0x0E0 `1, 0.005, 0.98, -2, 1, 1, 20, 20`
(a speed/decay/scale group), at +0x110 `10` (a 10-frame value), and two **8-key colour curves** in the
eft2 layout `(R, G, B, time)`:

```
+0x3C0 colour0: (1.00, 0.79, 0.39) t=0.16 -> (1.00, 0.58, 0.13) t=0.39 -> (1.00, 0.27, 0.10) t=0.67
               -> (1.00, 0.04, 0.04) t=1.00          # white-yellow core to red, over the life
+0x440 alpha:  1 1 1 @0.38, 0.4 0.4 0.4 @1.00        # holds, then fades to 0.4
+0x5D0 keys at 10 / 30 / 80 / 100 %                  # a 4-key (scale?) curve
```

That is decodable but NOT labelled: no tool here names v22's emitter fields.

### 1.4 Tools

| tool | what it does with VFXB | here? |
|---|---|---|
| Switch Toolbox (`apps/Switch-Toolbox`, `FirstPlugin.Plg.dll`: PTCL / VFXB) | opens the tree (sets, emitters), exports the BNTX textures; emitter PARAMETERS are shown only for older versions, v22 largely as raw data (not verified here) | yes |
| KillzXGaming's `EffectLibrary` (open source, C#, VFXB read/write) | the most complete public emitter-record layouts; which versions it covers fully is to be checked against v22 | no (would be a new upstream fetch) |
| Ultimate-Tex CLI (`apps/Ultimate-Tex-CLI`) | `.nutexb` only (the sword trails), not BNTX-in-VFXB | yes |
| our walker (this spike) | blocks, names, texture list, raw floats | scratch |

**What is needed to go further**: the v22 emitter record's field map (emission rate / count,
lifetime + random, initial velocity / spread / shape (point, sphere, circle, line, primitive),
gravity / air resistance, rotation + speed, scale curve, colour0/1 + alpha curves, texture + UV
animation (frames, scroll), blend (normal / add), billboard mode, primitive id, child emitter
settings). EffectLibrary's structs are the starting point; each field is then confirmed on a known
emitter (fire1's curves above make a good check).

## 2. Melee's side: the HSD particle system

Code (all decompiled, in the port): `src/sysdolphin/baselib/particle.c` (3,104 lines: generators,
particles, the command interpreter), `psdisp.c` (drawing), `psdisptev.c` (TEV setup), `psappsrt.c`
(particles following a joint), `psstructs.h`; loaded per bank by `psInitDataBank` /
`psInitDataBankLoad` / `psInitDataBankLocate` from an effect `.dat` (a fighter's `Ef<Xx>Data.dat`:
`effXxDataTable` = ptcl command bank + texture groups + effect models), spawned through `efSync_Spawn`
/ `efAsync_Spawn` -> `psGenerateParticle0` / generators.

| Melee has | notes |
|---|---|
| generators | point, disc, line, tornado, rect, cone, sphere (`auxDisc` ... `auxSphere`), count / interval / life, random ranges |
| per-particle bytecode (62 ops > 0x80 in `particle.c`) | set/add position and velocity, gravity, friction, velocity scale / normalise / aim at a joint, force fields, size interpolation (+ random), rotation interpolation, **PrimCol and EnvCol interpolation with per-channel random** (two colours per particle, over time), alpha compare, texture frame (PoseNum) + mirror / flip, spawn child particles / generators (with inherited position / velocity), conditional kill, callbacks |
| drawing | textured quads (billboard or along the velocity = "tail" / trail polygons), point sprites, appSRT (attached to a joint), two TEV colours, blend modes (normal / additive), fog |
| effect models | joint trees with animation (the precedent: Halberd converted 25 Brawl effect MODELS 1:1 with `efbuild`) |

Melee has no: programmable shaders (only fixed TEV: two colours x texture), soft / depth-faded
particles, distortion / refraction, emissive bloom, per-pixel lighting, noise / curl fields, GPU
counts (the particle pool is fixed-size, `psInitParticle(num)`), mesh "primitive" particles (a quad
or a point only - a mesh must be an effect MODEL instead).

**The in-repo precedent**: `ports/halberd/effects/tools/efbuild` (C#, HSDRaw) writes a fighter's own
effect bank: Brawl effect **models** about 1:1 (joints, textures, VIS/CHR/SRT/CLR animation baked)
and **particles** from a hand-written spec of op lists (HSDRaw `ParticleEncoding`) - Meta Knight's
4 generators "are approximations" (`ports/halberd/README.md`). m-ex's `effBehaviorTable` registers
the bank; Geno's article `"effect"` key (efAsync_Spawn on the article's joint) already attaches one.

## 3. Options

### (a) Convert Ultimate emitters into Melee particle banks

Per emitter: shape -> generator kind; rate / life / spread / velocity / gravity / drag -> generator
fields + ops; colour0 / colour1 / alpha curves -> PrimCol / EnvCol interpolation ops (Melee
interpolates linearly between keys the bytecode sets at given frames, so an 8-key curve becomes a
chain of timed interp ops); scale curve -> size interpolation; texture + frame animation -> a
texture group + PoseNum; additive / normal blend -> the particle's blend flag; child emitters ->
spawn-child ops. BNTX textures -> RGBA -> Melee texture groups (downscaled: the 117 textures are
3.6 MB compressed; Melee's effect heap wants ~100-300 KB per fighter).
Primitive emitters (`G3PR` meshes: lightning strips, rings, shards) -> Melee effect MODELS with
their texture and a baked SRT / alpha animation (the efbuild path).

Cannot map: the compiled shaders (`GRSN`) - the combiners that do Ultimate's glow, distortion,
alpha-erosion (the "burn away" of fire and smoke via an alpha-threshold texture), colour ramps
through a gradient texture, soft edges. Approximations: erosion -> alpha compare interpolation (Melee
HAS an alpha-compare op), gradient ramps -> PrimCol/EnvCol keys, glow -> additive layers.
Particle counts must be capped (Melee's pool is shared by the whole match).

Estimate: the v22 field map (with EffectLibrary as a start) 3-5 days; a converter (VFXB emitter ->
efbuild spec, textures, primitives -> models) 1-2 weeks; tuning the magic's ~40 emitters against
Ultimate side by side 1 week. **~3-4 weeks; looks like Ultimate at ~70-80 %, runs everywhere Melee
does, rollback-free (particles are visual) and netplay-neutral.**

### (b) A Geno particle engine that runs Ultimate-style emitters natively

Parse VFXB at load, simulate emitters in native code (the emitter record's full semantics), draw
through Aurora with our own shaders (a small set re-implementing the combiners Sora uses, since the
Switch shader binaries cannot run). Closest to "identical" (curves, counts, blending, soft
particles, primitives as meshes). Costs: the full emitter semantics (every field, not only the used
ones), a renderer path outside Melee's GX stream (Aurora extension, owned by beta), re-writing each
shader combiner by hand from observation (the binaries are not portable), and a new rollback rule
(visual-only state must be re-derived or snapshotted for SyncTest-clean resim; particles do not
affect gameplay, so re-simulating them is enough). **~2-3 months; ~90-95 %; only on the PC port
(fine: it is the only target), and it is a new engine surface to maintain.**

### (c) Hybrid (recommended)

(a)'s converter for everything Melee's particle system can express - which, per the op list above,
is most of what the magic's emitters do: billboard quads with colour / alpha / scale curves,
velocity, gravity, children - plus effect MODELS for the primitive emitters (lightning, rings,
shards), plus a **small, targeted** Geno/Aurora extension only where the look depends on it and
Melee cannot approximate: most likely (1) alpha-erosion by a threshold texture (fire and smoke
dissolving) and (2) additive glow layers with a gradient-ramp lookup. Both are small fixed shader
variants selectable per particle bank, not a general emitter engine. Everything stays inside
Melee's own effect pipeline (efSync/efAsync, banks, the effect heap), so rollback, LAB and netplay
need nothing new.

Estimate: (a) 3-4 weeks + the two shader variants ~1 week. **~4-5 weeks, ~85-90 %.**

**Recommendation: (c).** It matches the repo's rules (Melee's machinery first, as Halberd did for
Brawl effects; Geno only where Melee has no surface), keeps effects in the fighter's own bank (so
they ship in the mod like any m-ex fighter's), and leaves the expensive part (a native emitter
engine) out unless the side-by-side comparison proves the fixed-TEV path cannot reach "feels
identical". The first step is the same for (a) and (c) and decides between them cheaply: map v22's
emitter record on `P_TrailFireBullet` (10 emitters) and convert that one effect by hand through
efbuild; compare with Ultimate frame by frame.

## 4. Open / next steps

1. Fetch EffectLibrary (upstream, MIT per its repo - check) or read Switch Toolbox's VFXB code; map
   the v22 emitter record; confirm on `fire1` (the colour curves in 1.3).
2. Export the magic's textures from the BNTX (Switch Toolbox can) - never committed.
3. One effect end to end: `P_TrailFireBullet` -> an efbuild spec -> Sora's effect bank ->
   attached to the Fire article with its `"effect"` id (Geno 19.8 already has the hook).
4. Decide on the two shader variants after seeing (3) in game next to Ultimate footage.
5. Effect ids: Sora's bank needs an m-ex effect slot (m-ex effect ids 5000+, delta's D2 work).
