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

## 5. Firaga pilot: difference audit (2026-09-26, after GD's verdict "not accurate to Ultimate at all")

Source of the Ultimate column: GD's ef_trail.eff read by EffectLibrary (every value below is a decoded
field, named as the library names it). Melee column: what `trail_vfx_melee.py` v1 wrote into EfUsData.dat
(the efbuild spec) and what the in-game census measured (geno events 38/39). **INF** = inferred by us.

### 5.1 Faults found (ordered by how much they change the picture)

| # | fault | Ultimate (decoded) | pilot v1 | effect |
|---|---|---|---|---|
| 1 | **wrong direction** | every flame emitter is rotated by `EmitterInfo.RotateX` = pi/2, so its `DesignatedDir` (0, -1, 0) becomes local (0, 0, -1) = **backwards along the travel** (the weapon's forward is +Z); spark2's (0, 0, -1) is backwards too | velocity written as world (0, -v, 0) = **straight down**, spark2 as world -Z = **into the screen** | the fire trails downward instead of streaming behind the ball |
| 2 | **colour clipped to white** | colours are HDR: `Color0 x ColorScale` (1.1 / 1.2 / 2.0 / 3.0) goes through the custom shader (ShaderType = UserMacro2, shader 211) with Sampler2 = `ef_cmn_grade05` | `Color0 x ColorScale` clamped to 255 per channel, then lifted toward white for PrimCol | fire2 / fireline1 / spark2 render near-white; no red-orange-yellow gradient |
| 3 | **the combine is unknown** | `Combiner` fields are all 0, `ShaderType` 2: the colour/alpha combine is Nintendo's compiled user shader (Shader.bnsh, Maxwell), not table data | guessed PrimEnv lerp(env, prim, tex I), alpha = prim.a x tex A | the look depends on the guess (see 6.1) |
| 4 | **no random rotation** | `RotateInitRandZ` = 2 pi (every flame quad at a random roll) | every particle at roll 0 | identical-looking sprites, visible tiling |
| 5 | **wrong emission shape** | `ShapeInfo.VolumeType` 7 = filled sphere (hollow ratio `CaliberRatio` 0.2 / 0.7 / 1.0), 4 = sphere surface (fire_rif1) | disc (Melee type 0) of the same radius | flat, screen-plane spread instead of a ball |
| 6 | **no random ranges** | `ScaleRandom` 35-50 %, `LifeRandom` 20-60 %, `VelRandom` 20-50 % | fixed size, life, speed | uniform particles |
| 7 | **pattern animation mode** | `TextureAnim1.PatternAnimType` 1 = FitLifespan (fire_rif1, fire3, fire2, fireline1: the table's N frames stretched over the life), 2 = Clamp (fire1) | one frame per game frame for all | frames run too fast / wrong for long-lived particles |
| 8 | **emission delay** | `Emission.Start` 2 / 3 / 5 frames | none | particles appear at frame 0 |
| 9 | **velocity inheritance** | `EmVelInherit` -0.2 / -0.1 / +0.1 (a share of the ball's own speed, backwards) | none | missing drag-behind |
| 10 | **flare** | a *primitive* (mesh) emitter, scale 0.5, colour (1, 0.33, 0) alpha 0.4, additive (BlendType 1), `ef_cmn_grade00` | a particle of size 6 (**INF**) that interpolates to 0.25 in 2 frames (a bug: the primitive's scale curve applied to a particle) | the glow flickers out |
| 11 | **core meshes** | sphere1 / spherering1 / circle2 are G3PR primitives (meshes) with their own textures, rotation speeds (`RotateAddZ` 0.52 / 0.70 / -0.012 rad a frame), colours x 1.5 | one stand-in icosphere (**INF** radius 3.0), static, no ring, no circle | the core does not spin or layer |
| 12 | spawn offsets | `EmitterInfo.TransZ` 2.3 (fire1, flare1), 6.0 (fireline1) - in the emitter frame | ignored | particles start at the centre |
| 13 | depth / sort | fire_rif1 `DrawPath` 11, flare1 21 (later passes); soft-particle params present | Melee: generator order, no depth sort | draw order differs |

### 5.2 Per emitter, decoded vs pilot v1 vs measured

| emitter | life (rand %) | per frame | start | shape r | speed (dir) | scale (rand %) | colour0 keys x ColorScale | alpha | blend | tex (pattern) | pilot v1 life / rate / size | census @f30 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fire_rif1 | 15 (20) | 1 per 2 f = 0.5 | 5 | sphere surface 5.0 | 1.1 back, spread 0.01 | 9 (35) | white const | 4 keys 0 -> 1 @.19 -> .67 @.55 -> 0 | normal | fire00 atlas 11 frames FitLifespan | 15 / 0.5 / 2.97 | 6 (steady 7.5) |
| fire3 | 13 (25) | dist 1 per 2.2 u = 0.75 | 3 | filled sphere 3.5 | 0.35 back | 10 (40) | 4 keys (1,.58,.13) .. (.87,0,0) x1.1 | 1 | normal | 13 frames FitLifespan | 13 / 0.75 / 5.0 | 9 (9.75) |
| fire1 | 11 (0) | dist 0.8 per 2.5 u = 0.53 | 3 | filled sphere 2.0, hollow .2 | 0.15 back, grav 0.005 up, air .98 | 7 (35) | 4 keys (1,.79,.39) .. (1,.04,.04) x1.1 | 1 | normal | 11 frames Clamp | 11 / 0.53 / 2.27 | 6 (5.8) |
| fire2 | 8 (25) | dist 1 per 2 u = 0.825 | 2 | filled sphere 3.0, hollow .7 | 0.005 back | 4.5 (40) | 3 keys (1,.92,.77) .. (1,.48,.1) x1.2 | 2 keys 1 @.4 -> 0 | normal | 10 frames FitLifespan | 8 / 0.83 / 1.8 | 6 (6.6) |
| fireline1 | 13 (60) | 0.5 | 5 | filled sphere 6.3 | 3.0 back, spread 1.0 | 3.2 (35) | 4 keys white .. (1,0,0) x2.0 | 1 -> 0 @.86..1 | normal | 10 frames FitLifespan | 13 / 0.5 / 1.6 | 6 (6.5) |
| spark2 | 30 (50) | 0.5 | 5 | filled sphere 5.0 | 0.8 back (z), spread 0.1 | 2.8 x 3.92 (50) | 2 keys x3.0 | 1 -> 0 @.75..1 | normal | trail_parts00 | 30 / 0.5 / 1.4 | 14 (15) |
| flare1 | 2 | 1 (one-time primitive) | 0 | point | - | 0.5 | (1,.33,0) const | 0.4 | **add** | grade00 | 2 / 1 / 6 **INF** | 2 (2) |
| sphere1 / spherering1 / circle2 | 12 / 2 / 31 | one-time primitives | 0 | point | spin .52 / .70 / -.012 rad/f | 0.35 / 0.3 / 0.4 | (1,.59,.15)+(1,.13,.04) x1.5 / 3-key red x1.5 / (1,.95,.72) x1.5 | 2 / 1 / 1 | normal | mask02, fire03+fire00, line12 | not particles: one stand-in sphere | - |

The counts match the decoded steady states (rate x life) within one particle per emitter; everything
else in 5.1 is where the pilot is wrong.

### 5.3 Fix order (the coordinator's, with what each needs)

1. Direction and offsets (5.1 #1, #12): emit in the emitter frame (RotateX applied) with Melee's
   joint-oriented generator flag (0x100 | 0x400), so the article's facing rotation carries it. Tool only.
2. Shape, rotation, randoms, pattern mode, delays, inheritance (#4-#9): Melee has a sphere generator
   (type 8), per-particle random size (0xA4/0xA5 family), random rotation/pose ops, command waits.
   Tool only.
3. The flare and the core meshes (#10, #11): decode G3PR primitives into effect models (efbuild path).
4. The colour (#2, #3): needs the user shader's combine. Only its compiled Maxwell code exists; the plan
   is to decompile shader 211's fragment program with an open-source Maxwell decompiler (Ryujinx's shader
   translator, MIT) and then implement the SAME combine as a Melee renderer variant (a GX TEV stage
   sequence with the grade ramp as a second texture, if TEV can express it; an Aurora shader variant
   if not - that is the renderer change the coordinator must approve first).

### 5.4 The fragment shaders, disassembled (envytools `envydis -m gm107`, built from source in _build/agents/beta)

Each emitter carries its own compiled fragment program (Shader.bnsh; the fragment code is the last
NVN block, +0x80). Read with envydis, P_TrailFireBullet's combines are:

| emitter (shader) | colour | alpha | TEV-expressible? |
|---|---|---|---|
| fire1 / fire2 / fire3 / fireline1 (211 / 212 / 209 / 213, UserMacro2) | **Color0 x ColorScale, flat - no texture in the colour** | sat(fire00.G(uv1 + 2 x (indirect00.RG(uv0) - 0.5) x strength) x grade05.R(uv2) x Alpha0) x Alpha1; alpha-test kill | yes (grade05 is a border mask, not a heat ramp; the ramp idea was wrong); the UV warp needs GX indirect texturing |
| fire_rif1 (207, UserMacro1) | **2 x the FRAME BUFFER** (sampled at screen coordinates) x Color0 | fire00.G x grade05 x Alpha0 x vertex | no: a screen-space heat haze; needs a frame-buffer copy |
| spark2 / flare1 (216 / 215, Normal) | lerp(Color1, Color0, tex.rgb) (x vertex colour for flare1) | tex.a x Alpha0 (x Alpha1) | yes (Melee's PrimEnv) |
| sphere1 (210) | lerp(Color1, Color0, mask02.R(warped uv)) x vertex | smoothstep(0.1, 0.5, abs(n . v)) x Alpha0 (a view fresnel: soft edge) | per-vertex bake (billboarded, so n.v = n.z) |
| spherering1 (208) | vertex x Color0 | brave_fire00.G(warped) x Alpha0 | yes |
| circle2 (214) | lerp(Color1, Color0, line12.rgb) x vertex | line12.a x vertex a x Alpha0 | yes |

BNTX component selectors (2, 2, 2, 3) make a BC5 texture's rgb = R, a = G; BC4's (2, 2, 2, 2) = R.

**So no renderer change is needed for Firaga's colour**: the colour is the per-particle key colour, and the
textures only shape alpha. Two things remain that Melee's particle path cannot do: the UV warp (GX has
indirect texturing in hardware; Melee's particle TEV does not use it) and fire_rif1's heat haze (a frame
buffer copy).

### 5.5 Pilot v2 (what changed per audit item, with the census)

| # | item | v2 | measured (ACE, Sora slot, census events 38-41) |
|---|---|---|---|
| 1 | direction | velocity in the emitter frame (RotateX applied) + EmVelInherit x 1.65; the generator follows the article's joint whose rotation is the facing | mean particle position **behind** the ball: -3.1 / -7.4 / -8.1 units at frames 10 / 20 / 30 facing right, -3.0 / -7.8 / -8.3 facing left; forward speed ~0 |
| 2-3 | colour | the disassembled combine: flat Color0 x ColorScale per particle; alpha = atlas G x grade05 mask (baked into the frames) x Alpha0 keys | - |
| 4 | random roll | 4 generators per emitter at rolls 0.4 + k x 90 deg (Melee has no random-roll op) | 20 generators on the ball |
| 5 | shape | disc emission along the travel + a random offset of 0.8 x VolumeRadius on each axis (0xA8) | - |
| 6 | randoms | life random (0xA6), speed random (0xBD), scale random quantised into the 4 generators (scale x (1 - r x (k + .5) / 4)) | sizes e.g. fire3 4.75 / 4.25 / 3.75 / 3.25 |
| 7 | pattern | FitLifespan / Clamp / Loop per TextureAnim1.PatternAnimType | - |
| 8 | delays | Geno "effects" frame = Emission.Start: 2 (fire2), 3 (fire3, fire1), 5 (fireline1, spark2) | attached at article frames 2 / 3 / 5 (event 37) |
| 9 | inheritance | folded into the velocity | - |
| 10-11 | flare + core meshes | the four primitive emitters' own meshes (bfres, dumped with BfresLibrary): sphere1 hemisphere (327 verts, r 3.5), spherering1 (324, r ~6), circle2 (648, r 3.9), flare1 (64, r 12.3, additive), each on a billboarded joint with its ParticleScale, colours / alpha per 5.4 baked, spins 0.524 / 0.698 / -0.0122 rad a frame (Geno "spins") | the article item carries 8 joints, 4 display objects |
| 12 | offsets | TransZ 2.3 / 6.0 as emit joints of the model | effects on joints 2 / 3 |
| - | heat haze (fire_rif1) | left out (frame buffer) | - |

Live particles at frames 10 / 20 / 30: 8 / 25 / 32 (per emitter at 30: fire3 4, fire1 4, fire2 8, fireline1
12, spark2 4-5). Tests 190/190.

Still not carried: the UV warp (GX indirect), the heat haze, colour-key animation of the ring, soft
particles, per-particle random roll beyond 4 steps, the draw passes.
