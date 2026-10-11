# Xenoverse 2 Kamehameha, inventory and port notes (2026-10-10)

Lane: workspace `ws/goku-kame-xv2`, game `agent/goku-kame-xv2` (no game-repo change was needed). Owner brief: the reworked Kamehameha looked wrong, so port Goku's
Kamehameha from XV2 as directly as the engine allows (animation, effects, voice and SFX). Gameplay (charge steps, store rule, multi-hit, damage table) is unchanged
(`ports/goku-xv2/KAMEHAMEHA.md`); only the presentation is replaced.

**Asset policy, followed exactly as for the Goku model.** XV2 bytes (models, textures, effects, audio, the CPK contents, every dump and PNG/WAV/.gnsnd derived from them)
exist only under git-ignored `_build/` (`_build/xv2-kame/`, `_build/goku-xv2/fx|audio/`) and `.omo/`. What is committed: our extractors (`tools/xv2x/`), our converters
(`ports/goku-xv2/tools/xv2_fx.py`, `xv2_audio.py`, `emp_view.py`), the glue (`build.py`, `kame_try.py`) and gameplay numbers. The game install is
`E:\Games\DB Xenoverse 2` (version 1.25.02.0); the effect files are the shallow export `...\modding\exports\goku-base-shallow-v0.1\raw\skill\` (README of the port).

## R1. Inventory (skill folders, BAC entries, BSA, effects, audio)

| item | where | what it is |
|---|---|---|
| Kamehameha | `skill/SPA/000_GOK_KMH/` | BAC (54 entries, 36 non-empty), BAS, BSA (9 entries), EAN (body clip 0, 127 frames; `_F`, `_MAM` copies), EEPK + `pbind/tbind/ptcl/trc` EMB + EMM, `Kmh_Bas/Fire/Hand.emo` (+ `.emb .emm .mat.ema .obj.ema .light.ema`) |
| Super Kamehameha | `skill/ULT/000_GOK_CKM/` | same shape: `Ckm_Bas/Fire/Hand/HandPrx.emo`, 10 EMPs (`Crg, Fireptcl, LineAll, Wav, FireLine, Tail, Last, 4ptcl, CrgLOD, HitFin`), `Ckm_Beam.etr` (4 ribbons), BAC 6 entries, cam EAN |
| Gogeta's Kamehameha (not ported) | `skill/SPA/040_GKG_KMB/` | `Kmb_*` |
| audio | CPK `data.cpk sound/SE/Battle/Skill/CAR_BTL_S000_KMH_SE.acb` (+ `U000_CKM_SE`), `data0.cpk sound/VOX/Battle/Skill/CAR_BTL_S000_KMH_GOK_VOX.acb` and `.../en/` (+ `U000_CKM_GOK_VOX`) | see R4 |

**BAC (`000_GOK_KMH.bac`), the regular Kamehameha.** Entries 0, 1, 2 are the three charge tiers on the ground; 5-7, 10-12, 15-17, 20, 30-32, 35-37, 40-42, 45-47, 50 are the
air / variant / assist copies. Frame numbers are 60 fps game frames. All three play the skill clip 0 (`GOK_SPA_KMH`, 127 frames) with BAC `Time Scale` events:

| entry | Time Scale (start, length, scale) | Charge Control | projectile (BSA entry, frame) | effects (EEPK ids, SuperSkill) | sounds |
|---|---|---|---|---|---|
| 0 (lowest) | (0,42,x1.75) (42,18,x1.5) (84,4,x0.3) (88,17,x0.7) | frame 20, length 20, ChargeTime 72 | BSA 0 at 56 | 0 at 10 (charge), 1 at 54 (muzzle), 0 off at 59, 1 off at 80 | SE cue 0 and VOX cue 0 at 0, VOX cue 1 at 58 |
| 1 (mid) | (0,42,x1.6) (42,18,x1.25) (84,4,x0.25) (88,15,x0.45) (103,17,x0.9) | none | BSA 20 at 60 | 0 at 10, 1 at 56, 0 off 60, 1 off 85 | VOX 0 at 0, VOX 1 at 58 |
| 2 (full) | (0,45,x1.5) (45,15,x1.25) (84,4,x0.2) (88,16,x0.3) (104,16,x0.8) | none | BSA 30 at 60 | 0 at 10, 1 at 56, 0 off 59, 1 off 92 | VOX 0 at 0, VOX 1 at 58 |

Also per entry: `Camera` (EAN `g_x_LND`, frames 54-64 / 58-73 / 58-79), `Function` 33 at 52 (length 53), 4 at 56-60 (param 100) and 38 at 93 (not translated), face animations,
`Tracking`, `Bone Modification`. Stage background effects (`StageBG` ids 220 / 240) and a common effect 45 at 61 are not ported. The Super (`000_GOK_CKM.bac`, entry 0):
SE cue 0 at 0, VOX cue 0 at 34, VOX cue 1 at 96, projectile BSA 0 at 92, camera 0-240, effects at 0/1/10/20/88/90/94/110/160/170/192/200.

**BSA (`000_GOK_KMH.bsa`).** Entries 0, 20, 30 are the beam projectiles the BAC spawns (their `Type0` lists point at entries 5 / 25 / 35, whose `Type1` rows carry F_04 = 10, probably the motion/speed field; unverified), with `Expires` 1 / 21 / 31 and hit effects
`StageBG 600` and `Common 101`. We keep the gameplay's hit-sphere beam; the BSA speed/lifetime are not used.

**EEPK (`000_GOK_KMH.eepk`).** Containers: PBIND (8 EMPs: `Kmh_Crg, CrgON, LineAll, Wav, Fireptcl, 4ptcl, Ring, tsubu`, textures `ptcl.emb` 13 DDS, materials `ptcl.emm`
18 rows), EMO (`Kmh_Fire, Kmh_Bas, Kmh_Hand`), TBIND (`Kmh_Beam, Beam2, Beam3.etr`; textures `trc.emb` beam00 / ring_beamCor / T2_UV01; materials `trc.emm`), LIGHT (`Kmh_Crg/Fire/Bas.light.ema`).
Effects: 0 = charge at `g_L_Hand` (Crg x0.4, CrgON x0.8 at 42 and x1.2 at 78, Crg again x0.6 at 42 and x1.0 at 78, tsubu) ; 1 = muzzle (Fire.emo + Ring.emp, x0.8) ; 3 / 4 / 5 = beam for the
three BSA entries (Bas.emo x1.6, Hand.emo x0.45 at z -0.3, Fireptcl/4ptcl x1.6, Wav x1.8, LineAll, and the ETR ribbon) ; 10, 15, 16 = charge/beam variants for other BAC entries.

**The beam in XV2 is a projectile head with trail ribbons**: `Kmh_Bas.emo` (core spike `Cor` r 0.28 m x 3.3 m, shells `BasB`, `BasB1`, `BasB_kushi` r 0.5 m x 1 m, materials
`T1_VFX_MTN_DIS_ALPHA`, `TexScrl` 3.7 / 4.9 per second, additive core + alpha shells), `Kmh_Hand.emo` (head ball), the particle files at the head, and `Kmh_Beam.etr`: three ribbons
(scale 0.69 / 0.65 / 0.45 m, textures beam00 / ring_beamCor / T2_UV01, scroll V -0.05 / 0.10 / 0.04 per frame) that form the long body. `obj.ema` poses the parts (TRS `Rotation X -90`, TRS scale
0.8 / 0.6 / 0.8, Cor Y 0.3 -> 0.8 in 3 frames, BasB Y pulsing 1.27 <-> 1.97 every 4 frames), `mat.ema` animates colour and `TexScrl` over an 80-frame loop.

### Formats, readers, licences
- LazyBone152's XV2-Tools (`Xv2CoreLib`, MIT, `modding/src/XV2-Tools/LICENSE`) is the community reference for BAC/BSA/EEPK/EMP/EMO/EMB/EMM/EMA/ETR/ACB/AFS2/CPK, VGAudio (LB_Common, MIT) for HCA. We call the built DLL from
  our own console tools (`tools/xv2x/audio`, `tools/xv2x/fx`, new code, no third-party code copied; the library is loaded from the install of the tool bundle, not vendored).
- Our readers/converters: `xv2_fx.py` (EMP node trees and EMO + EMA bone poses -> Geno effect packages), `xv2_audio.py` (ACB WAVs -> `.gnsnd`), `emp_view.py` (a compact EMP dump for reading).
- Sources of the format knowledge: the Xv2CoreLib source (field names, enums), XenoKit/EEPK Organiser conventions (ScaleBase x ScaleXY = half-quad, SpriteSheet keys = sub-rects), the shallow export's own decoded JSON.

## R2. Animation
The body animation is XV2's own clip: `000_GOK_KMH.ean` clip 0 (`xGOK_SPA_KMH` in the bank; LAB: `ports/goku-xv2/tools/clips.ps1 xGOK_SPA_KMH`). The Melee states already used it (rows `KameCharge` = clip frames 0-40 held at 40, `KameTap/Mid/Full` fire from clip frame 48; BAC entry 12 as the pick).
XV2 plays the cup phase at x1.75 (42 game frames = 73 clip frames) and then holds for the charge (Charge Control); ours plays the same cup frames at x1.0 (40 frames), the held pose is the clip's frame 40. The
thrust that XV2 reaches at clip frame ~95 (BAC projectile at 56 with the x1.75/x1.5 scales) is our release-row crop from clip frame 48 (the same thrust pose, reached 8 frames after the state starts, the beam held by `ANIM_RATE`).
Not changed this lane: the clip rows themselves (an owner-visible check that the poses match is in the report; there is no XV2 capture to compare, see Owed).

## R3. Effects: what is converted and what is not
Packages (all `_build/goku-xv2/fx/P_TrailGokuXKame*`, bound in `build.py` `FX_STATES`): `XKameCharge`, `XKameMuzzle`, `XKameTap/Mid/Full`, `XKameSuperCharge`, `XKameSuperMuzzle`, `XKameSuper`.
- Beam: 3 trail ribbons from the hand to the head (two crossing quads, XV2's ETR textures, widths from the ETR, blend from the trail material, scroll from the ETR), the head (`Bas` parts and `Hand` parts with their `obj.ema` pose baked into the vertices, additive core + alpha shells, `TexScrl` and `MatCol` from the material table), and the particle files at the head. One uniform scale per tier (model units per XV2 metre: Tap 2.6, Mid 3.5, Full 4.6, Super 3.2) makes the head as wide as the hit sphere.
- Charge: the `Kmh_Crg` sprite stack stepping up (x0.4 / 0.6 / 1.0 at charge frames 0 / 20 / 40), the `CrgON` flash at each 15-frame step, `tsubu` motes.
- Muzzle: `Kmh_Fire.emo` (flare dome) at release.

Approximations (each is a place to look if the owner's eye disagrees):
1. XV2's projectile frame is -Z forward (the TRS bone turns the mesh -90 degrees about X). The dome is the head and the tube trails behind it; the particle files keep +Z forward (their -4 m offsets sit behind the head, their emitters spray back from it). Sign choices are unverified without an XV2 capture.
2. `ShapeDraw` emissions (the shock-ring polygon bands) are **dropped**: a flat plate looked wrong. This removes `Kmh_Ring` (the muzzle ring) entirely and the rings of Crg/4ptcl/Fireptcl/LineAll.
3. `ConeExtrude` (ribbon stripes) is a velocity-stretched streak; the ETR ribbons are two crossing quads (XV2's are camera-oriented extrusions), uniform width instead of the ETR's taper over segment age.
4. Animated emitter positions (`Position` key curves) use their first key; `Vortex`, `Translation`, `Acceleration` modifiers are not mapped (`Drag` is). Child emitters are flattened (the runtime has no child-emitter links).
5. `obj.ema` / `mat.ema` poses use their sustained mean (frames 10-59); the BasB length pulse (every 4 frames) and the colour animations are not played. The beam's growth (grow in 3-6 frames, hold, shrink) is ours.
6. Light EMAs (`Kmh_*.light.ema`, dynamic lights), the refraction ribbon (`T1_VFX_TRC_RI`), the screen-space camera shake (BAC `Camera` events) and the stage-background effects are not converted.
7. Units: ScaleBase x ScaleXY x 2 = quad width in XV2 metres; velocity per second -> per frame /60; texture scroll per second -> /60. The charge ball sits at `hand.R` + (0,0,4), as before: XV2 attaches it to `g_L_Hand`.
8. Material blend comes from `AlphaBlendType` (1 = additive) or the `add*` name; everything else is alpha blend. Colour = Color1 over life; Color2 and `Glare` colours are not used (a bloom pass stands in).

## R4. Audio
`tools/xv2x/audio` (`Xv2Audio list|get|acb`) pulls the ACBs out of the CPKs and decodes the HCA waveforms; `xv2_audio.py` converts to mono 32 kHz `.gnsnd` (peak -1 dBFS).
| XV2 cue | file | length | Melee use (retail id played by the script, bound as an `audio.voice` row) |
|---|---|---|---|
| KMH VOX 0 "ka-me-ha-me" (BDB_GOK_071) | jp 0.90 s, en 0.92 s | `GnKameVoxCharge` | id 200121, at the start of `KameCharge` (BAC: frame 0) |
| KMH SE 0 `kamehame_Charge` = waveform `4_charge` | 2.10 s | `GnKameSeCharge` | id 200124, with the voice |
| KMH VOX 1 (BDB_GOK_072) the release shout | jp 0.59 s, en 0.71 s | `GnKameVoxFire` | id 200115, at the beam start of Tap/Mid/Full (BAC: frame 58, 2 frames after the projectile) |
| KMH SE 1 `kamehame_shot` = waveform `4_shot` | 3.41 s | `GnKameSeShot` | id 200118, with the shout |
| CKM SE 0 `Superkamehame_charge` | 2.80 s | `GnKameSuperSeCharge` | id 200127, at the start of `KameSuper` |
| CKM VOX 0 (same line as KMH) | | `GnKameVoxCharge` | id 200121 at state frame 19 (BAC: 34 of 96 to the shot) |
| CKM VOX 1 `L1_GOK_M1_088` the Super shout | jp 0.94 s, en 0.97 s | `GnKameSuperVoxFire` | id 200130 at the beam start |
| CKM SE 1 `Superkamehame_shot` | 3.72 s | `GnKameSuperSeShot` | id 200112 |
The two KMH SE *sequence* cues (0, 1) have no waveform of their own in the ACB (the library's sequence resolver returns none); they are named for the two waveforms (cue 2 `4_charge`, cue 3 `4_shot`), which is how they are used here.
Japanese is the default; `python ports/goku-xv2/tools/xv2_audio.py --lang en` then `build.py` gives the English lines. The retail ids are Mewtwo Shadow Ball ids (Goku never plays them). The old synthesised chimes at the 15-frame steps are gone (XV2 has none).
The charge script restarts when the held charge clip wraps (`ctx.loop()`); the row is now 135 frames long so the voice repeats only after 2.2 s of holding.

## R5. Gameplay kept
Charge steps (15 a step, 60 full), shield-store, B resume, full stored charge fires at once, **a hit wipes a partial stored charge and keeps a full one** (owner decision, as built), beam hits and damage table, startup 5 / 6 / 8 / 54 are unchanged. XV2 timing did not force a change.

## Owed
- A side-by-side with an XV2 reference capture: XV2 was not run (no patcher installed; no way to launch a skill in a captured scene without it). The converted look is judged against XV2's data, not against its screen.
- On-screen review by the owner of: beam proportions, the ribbon taper, the charge ball placement and size, the muzzle (rings dropped), the Super head size.
- English lines were converted but not listened to in game.

## Audio quality pass (2026-10-10, owner: "sounds like shit")
Measured per stage (source WAV -> `.gnsnd` decode -> engine mix):
- **Resampling was the cause.** `tools/geno/audio.py` converts to 32 kHz by linear interpolation with no low-pass. Against a band-limited resample the error was only **16.1 dB** below the signal for the charge SE (44.1 kHz), 30.9 dB for the shot, 26.3 dB for the 24 kHz voice: audible aliasing/imaging distortion. `xv2_audio.py` now resamples with a Kaiser polyphase filter (scipy `resample_poly`, beta 8.6) and hands the converter a 32 kHz file, so it stores it untouched.
- **Level / clipping.** The old clips were peak-normalised to 0.89 and a voice and an SE start in the same frame (`GnKameVoxCharge` + `GnKameSeCharge`): their sum clipped the 16-bit mix (29094 + 28639 peak). Now voices peak at 0.55 and SEs at 0.40 of full scale, DC removed, 5 ms fade-out so clips never end on a click.
- Stereo fold: the source cues are mono, nothing folded. Bit depth: the source is the HCA decode to 16-bit; `.gnsnd` is 16-bit PCM (no ADPCM). Truncation/loop: clips are whole (0.59 to 3.72 s, below the 10 s cap), played once. Pitch: the row plays at the clip rate.
- **Engine cap (not changed):** the AX mixer and `gw_Audio_PlayClip` run at a fixed 32 kHz ("the audio rate is the clip rate: no resampling", `shim_ax.c`), and `.gnsnd` v1 is fixed 32 kHz, so everything above 16 kHz is lost (the 44.1/48 kHz SEs keep little there: 0.003 % of energy above 15 kHz, so this is audible mainly as a slightly dull top, not as distortion). The 24 kHz voices are band-limited at 12 kHz in the source anyway. Proposed engine change if the owner wants more: `.gnsnd` v2 with a stored rate (44.1 / 48 kHz) and a resampling mixer for clips (about half a day: header field, polyphase or cubic interpolation per clip in `gw_ax_mix_clips`, tests).
- A/B files: `_build/xv2-kame/audio/ab/<clip>_1_source.wav` (the XV2 decode), `_2_old_linear.wav` (what the game played before), `_3_game_new.wav` (the 32 kHz data the mixer now outputs at row volume 127; the mixer applies `gain/127` and adds to the main bus, so this is what leaves it). A capture of the live output device was not made.

## Charge traces (retail Samus | retail Mewtwo | Goku; frame t from the first B; motion names)
See `ports/goku-xv2/KAMEHAMEHA.md` section 0 for the model. Findings from the traces (`tools/kame_traces.py`): Start lasts 13 frames (Samus) and 17 (Mewtwo) before the loop; a shield press at t=33 gives Cancel at t=33 and Wait at t=41 in both natives (an 8-frame Cancel); a flick gives EscapeF at t=33 in both; X (jump) is ignored by both (they stay charging); with no input Samus auto-stores at t=133 (Cancel, Wait 141) while Mewtwo enters LoopFull at t=137 and waits; B after a stored partial charge re-enters Start then Hold (13 frames), and Samus's resumed charge reaches full at 228.

## Rendering features that would close the gap to XV2 (not built; estimates)
Existing: the effect runtime already has an effect-only bloom (half-resolution, threshold + intensity), a frame-copy distortion shader, additive/alpha blend and UV scroll/sprite sheets. Missing, by visual weight:
1. **XV2's glare / bloom colour** (`Glare` + `GlareCol*` per material: the bright core blooms in a tinted colour, wider than ours). Per-material bloom tint and a wider blur: ~1 day (render + importer fields).
2. **Camera-oriented ribbon extrusion** for ETR trails (taper by segment age, 73-segment strips). Ours are two crossed quads. A real strip mesh emitter with per-frame path history: ~2 to 3 days (the format notes "stripes' history" as not in v1).
3. **Dissolve/parallax material** (`T1_VFX_MTN_DIS_ALPHA`, `PRLX`: a second scrolling texture masks the first). A two-sampler `dissolve` shader type: ~1 day.
4. **Soft particles** (depth-fade where a sprite meets geometry; the IR already carries `soft_particle`, the renderer does not read it). Depth snapshot already exists for the bloom: ~0.5 day.
5. **ShapeDraw ring bands** (the shock rings): a ring/band mesh emitter with the sprite-sheet texture: ~1 day.
6. **Dynamic lights** (`*.light.ema`: colour/intensity over time on the fighter/stage): lighting hook on the Melee side: ~2 days, invasive.
7. **Screen shake / zoom on release** (BAC `Camera`, EAN `g_x_LND`): a fighter-script camera command: ~1 day.
8. **Refraction ribbon** (`T1_VFX_TRC_RI`): reuses the distortion pass on a ribbon: ~0.5 day after 2.

## Parameters for the FX lane (data in `_build/xv2-kame/fx/lane_params.json`, written by `ports/goku-xv2/tools/xv2_lane_params.py`)
**The finding that matters most: XV2's beam body is a tapering *trail*, not a constant-width tube.** Each ETR ribbon's `Scale` (width, metres) is a curve over the age of a segment:
a segment is born at the projectile head at full width and narrows with age, so the body is a comet tail behind a fast head (BSA speed field 10 per frame). Our two crossed constant-width quads cannot look like it.
Kamehameha (`Kmh_Beam.etr`, Beam = tier of BAC entry 0, Beam2 = entry 1/20, Beam3 = entry 2/30; frames are 60 fps; width curve keys `age:width_m`; alpha keys `age:alpha`):

| ribbon | texture | blend | width (m) by age | alpha by age | scroll (uv/frame) | extrude / hold / seg |
|---|---|---|---|---|---|---|
| Beam: core | beam00 | alpha | 0:0.69, 11:0.2, 18:0.05 | 0:1, 14:1, 18:0 | v -0.05 | 60 / 18 / 73 |
| Beam: streaks | ring_beamCor | alpha | 0:0.65, 12:0.175, 20:0.1 | 0:0, 1:1, 16:1, 18:0.25, 20:0 | v +0.10 | 58 / 20 / 69 |
| Beam: cloud | T2_UV01 | alpha | 0:0.45, 12:-0.025, 20:-0.1 | 0:0, 1:1, 18:1, 20:0 | u 0.01 v 0.04 | 58 / 20 / 73 |
| Beam2 (core / streaks / cloud) | same | alpha | 0.79 to 0.04 (11) to 0.005 (18); 0.75 to 0.05 (13) to 0.005 (22); 0.55 to 0.06 (13) to 0.005 (22) | same shape, hold 18 / 22 / 22 | v -0.08 / 0.10 / 0.07 | 80 |
| Beam3 | same | alpha | 0.94 to 0.05 (12) to 0.005 (20); 0.8 to 0.1 (14) to 0.005 (24); 0.8 to 0.1 (13) | hold 20 / 24 / 22 | v -0.05 / 0.10 / 0.07 | 100 / 100 / 80 |
Flags `AutoOrientation, NoDegrade, DoublePointOfMiddleSection, DisplayMiddleSection` (camera-facing strip, a doubled middle point, 73 segments); colour 1,1,1 all three (the blue is in the textures); `UV repeat Wrap/Wrap`.
Super (`Ckm_Beam.etr`, 4 ribbons, widths 2.15 (refraction, skipped) / 1.68 / 1.35 / 1.25 m, hold 32 / 20 / 20 / 30; ring_beamCor tinted 0,0.3,1; `beam00` is additive, `T2_UV01` and ring alpha).
Per-tier suggestion for the lane (our hit-sphere radius in model units / the XV2 metre scale `S` used by `xv2_fx.py`): width multiplier 2.0 / 2.6 / 3.5 / 4.6 / 5.8 for tiers 0..4 and 3.2 for Super at the curves above (a ribbon of 0.69 m x 4.6 is 3.2 model units half width, matching the Full sphere radius 4.2/1.43), segment life 12 / 24 / 34 / 46 / 62 frames (= `life` in `xv2_fx.TIERS`).
**Bloom-worthy emissive layers** (materials with `Glare`): `Kmh_Bas` core `Cor` (GlareCol 0,1,1, additive, TexScrl u 3.7/s, MatCol1 G 1.84 = hot), `Kmh_Hand` `cor` (1,1.1,1.2) and `hand` (0,1,1), particle materials `add_G`, `nml_G*` (0.5-1.3 colour; the `.ptcl.emm` GlareCol floats are 1.1,1.2,1.3 for `add_G`), Super: `Ckm_Hand` glare 1,1.1,5 / 1,1.7,5 (a strong blue), `Ckm_Fire` 1.66,1.66,2.0. Per-material glare tint plus a wider blur is what the lane needs; the colour is above 1.0 so it is an HDR multiplier.
**Camera / shake.** The BAC `Camera` events (EAN index 0 on bone `g_x_LND`): KMH entry 0 frames 54-64, entry 1 frames 58-73, entry 2 frames 58-79 (10 / 15 / 21 frames long, starting 2 frames before the projectile). The KMH skill ships **no** `.cam.ean` in the export (EanType 1 / 2 refer to the character / common camera banks: `GOK.cam.ean` clip 0 is the 210-frame intro, `CMN.cam.ean` has 34 clips, none a Kamehameha shake), so the shake amplitude is not recoverable from the data we have; use 10 / 15 / 21 frames as the duration and a small amplitude as a design choice. The Super has its own: `000_GOK_CKM.cam.ean` clip `GOK_CAM_CKM_C` (225 frames, BAC camera event frames 0-240): Node Position range (x 1.56, y 0.39, z 4.99) and Rotation range (0.77, 0.47, 1.9) degrees over the clip, 221 / 223 keys.
Time scales (BAC, game frames): entry 0 x1.75 (0-42), x1.5 (42-60), x0.3 (84-88) and x0.7 (88-105): the slow-motion beat at the end of the beam is part of XV2's presentation.
