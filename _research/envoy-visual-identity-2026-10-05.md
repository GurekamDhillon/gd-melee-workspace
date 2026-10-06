# Envoy visual identity: design and feasibility survey (readability pass 2)

Date: 2026-10-05. Status: design only. Nothing here was run: no game window, no build, no capture. The game-design lane
(pass 1) had written nothing yet when I started and again when I finished (`_build/audit-20261003/envoy-pass1/` was empty,
`_research/envoy-readability-pass1-2026-10-05.md` did not exist), so the grammar below is built from the **kinds** of piece and
from the record fields, not from pass 1's proposed names. Where pass 1 renames or splits pieces, nothing here needs to change
(section 3.2 and `drafts/look_rules.lua`).

Re-check at the end (22:31 the same evening): pass 1 had begun writing data (`_build/audit-20261003/envoy-pass1/`:
`inventory_summary.txt`, `archetypes.json`, `inventory.lua`) but no proposal and no research document yet. Its inventory counts
**86 pieces**: 42 keystones, 16 prefixes, 22 suffixes, 6 unique drives; keystones by colour 7 red, 8 green, 7 blue, 6 yellow,
6 purple, 8 white; budget families such as `speed`, `launch_taken`, `damage_taken`, `sustain`, `crit`, `conversion`,
`momentum`. That fits the grammar: every piece has a `kind`, a `trigger` and a drive colour, which is all `look_rules.lua`
reads. When pass 1 lands, re-run the 20-piece storyboard (section 3.3) against its renamed pieces; if it adds a "what it
changes" tag per piece, offer it as the WHO source (section 3.2).

Labels used throughout: **[Owner]** his words, **[Read]** read in a doc or in code (path given), **[Measured]** a number someone
else measured and recorded (not me; I measured nothing), **[Mine]** my judgement or proposal.

Drafts and this file's companions: `_build/audit-20261003/envoy-pass2/` (`PROGRESS.md`, `drafts/`).

---

## 0. One-page summary

**The complaint [Owner]:** too much visual stuff at once, hard to tell what is what; each thing needs its own identity so it
can be seen; he wants things circling or following the player, following the fist, hands or head like a halo, spires of
light, bursts of flame, swirls, rotations ("examples, not literal requests"); he only really notices the player-model shader
effects today; the drive models are "10/10 S+, charming and adorable".

**What the engine can do today [Read]:**
- A model-surface look per fighter (16 floats a frame), full-screen post passes (32 of them, each a full-screen cost), tracers
  and earned afterimages on hands, feet, head and hitboxes, world particle packages that follow a joint or sit at a world
  point (offline only), kit models placed in the world each frame (offline only, 256 instances).
- World-space with real occlusion exists today **offline**, through effect packages (`gd.fx_play`/`gd.fx_world`) and model
  instances. Nothing online (`fx_*`, `model_*` refuse under netplay/rollback in the source).
- **A finding [Mine, from the source, unverified on screen]:** a post pass can occlude itself against the fighter and stage,
  because the scene depth snapshot is available to it (`scene_depth`, `linear_depth`) and `gd.project` returns a depth. Tonight's
  shaders did not use it, so "nothing can occlude them" is a property of those shaders, not of post passes. The units need one
  calibration step (section 2.4).

**The gap, in one line [Mine]:** orbit and swirl motion, role names for bone attachment, per-instance shader parameters, a
rotation argument for world effects, and above all **a declarative, rollback-safe effect binding** so any of it can run in
online Envoy. Post passes cannot scale to six fighters (each is a full-screen pass), so they are for the player's own fighter
and the interim only.

**The grammar [Mine]:** every piece gets a look from six channels, each with one meaning: **WHO** (colour and silhouette from the
drive's own model), **WHAT KIND** (carrier: surface, orbiters, halo, floor ring, fist glow, tracer, stamp), **WHEN** (idle,
armed, charging, fired, stacking, expiring: motion states), **HOW MUCH** (count, size, fill), **WHERE** (fist = the next hit,
feet = movement, head = a held keystone, chest = defence, hitbox = a strike, floor = build and synergy), and **loudness
inversely proportional to duration** (the longer something lasts, the quieter it is).

**The budget [Mine]:** your fighter: at most 3 loud persistent looks plus one quiet dimmed halo; an opponent: 2; in a six-fighter
match at most 8 persistent looks on screen; bursts at most 4 a second per fighter and 10 on screen, merged inside 12 frames;
**at most one screen-wide effect at a time**, none persistent. Passive drive rules get no look of their own; the effect
shows when it acts.

**Cut or change today [Mine]:** the 2 equipment layers on the surface, the persistent archetype lane, the link-flash overlay, the
crit toast, the pickup post pulse, the 6-second archetype toast, floor drops running 5 emitters each for up to 30 drops.

**Owner decisions needed first:** section 7.3 (11 short questions with my suggested answers).

**Drafts (untested, not compiled):** `drafts/orbiters.wgsl`, `drafts/bone_glow.wgsl`, `drafts/strike_mark.wgsl`,
`drafts/look_rules.lua` (this one runs: `lua look_rules.lua`, self-test passes).

---

## 1. What the engine can draw today

Sources: `docs/scripting.md`, `docs/shaders.md` (all read), `melee/docs/scripting.md`, `melee/docs/geno.md` §20,
`melee/pc/platform/gw_script.c`, `gw_script_model_api.inc`, `gw_fx_motion.cpp`, `gw_surface.cpp`, `gw_shader_effects.inc`,
`melee/pc/gameworld/script_motion.inc`, `script_parts.inc`, `script_model.h`.

### 1.1 Every visual output kind

"Offline" means `gs_require_offline` in the source: refused during netplay/rollback [Read: `gw_script.c:838`].

| kind | where it lives | what drives it per frame | cost and limits | rollback / netplay | hot reload | Geno / custom fighters |
|---|---|---|---|---|---|---|
| **Fighter surface** `gd.fighter_shader(port, path, {params})`, `gd.fighter_shader_set` | on the fighter's own model pixels (cannot draw off the body) | 16 floats per port, replaced whole; no compile on update; Envoy packs statuses, equipment, lane 14 into them | one GX variant per material, warm with `gd.warm`; 256 distinct sources per process; a cold compile hitches (90-260 ms [Measured: `earned_fx.lua` comment]); no geometry | visual-only; selection and params are not in snapshots, rebuilt from Lua state after a restore; allowed online per docs | **not polled**: call again after editing [Read: surface-shaders README] | any port 1..6, CPU and sub-fighters included [Read: scripting.md surface section] |
| **Stage surface** `gd.stage_shader` | stage model pixels | params | as above | as above | as above | n/a |
| **Post pass** `gd.post_add/_set/_remove`, `shader_load` | whole screen, two insertion points (`world`, `final`) | params every frame, position via `gd.project`; `duration_frames` + `clock` timed passes | 32 passes, 128 shader handles; each full pass is W*H shading plus one offscreen resolve; `half=true` is about a quarter; one colour+depth snapshot per stage; 16 named params, each a `vec4f` read with `.x` | visual-only; allowed online; no Lua hooks in replay | yes, polled every 250 ms | independent of fighter type |
| **Effect package emitters** (Geno `.gfx.json`) via `gd.fx_play`, `gd.fx_world`, `gd.fx_move`, `gd.fx_control`, `gd.fx_end`, `gd.fx_instance` | **in the world**, depth tested, camera-facing or plate/stripe/mesh particles; follows a joint (`fx_play`/`fx_attach`) or a world point | `fx_move` (world anchor); `fx_control(h, emitter, {opacity, rate, speed, life, size, brightness, turbulence}, tween<=600)` (7 floats, tweened); `fx_end(h, fade)` | 64 packages, 2000 particles, 256 emitter instances; a full pool refuses the newest package's lowest-priority emitters; `fx_control` ranges 0..3 | **offline only**, and each call forks the rewind timeline (`gs_rw_branch`); particle state sits in the FX rollback ring (16 frames) | custom fragment and vertex bodies hot reload; whether package JSON reloads is not stated (assume restart) | joint is a raw index (`fx_play(pkg, port, joint, x, y, z, scale, seed)`); **no role names** |
| **Custom effect shader** `material.shader.type="custom"` and `gd.fx_shader(pkg, emitter, handle)` | per emitter | named params via `gd.shader_set`; **shared by every instance of that emitter** (not per fighter) | fragment gets `uv`, `world`, `normal`, `fresnel`, `param`, `ii`, `parts[ii]`, `scene_color`, `scene_depth`; vertex gets `position, normal, uv` only (no particle index); one colour/depth snapshot per effect frame; `time_seconds()` is host time | visual-only | fragment and vertex bodies yes | n/a |
| **Fighter-bound packages from Geno `fx_bindings`** | on a Geno fighter's joints, driven by its motion state | native state machine (`gw_Fx_Drive`) | 8 fighters of driver state | **rollback-safe by construction** (state restored with the instances) [Read: geno.md §20.3] | n/a | only Geno fighters, conditions are motion states, not Envoy statuses |
| **World model instances** `gd.model_load/_spawn/_set/_move` | in the world; drawn once in the main camera before fighters, projectiles, shields and particle effects | any of `x y z rot rot_x rot_y scale scale_x/y/z tint alpha visible layer background` each frame | 256 instances, 128 assets, 64 MiB, 64 owners; custom materials: built-in `lit/unlit/glass` or a fragment (+vertex) with **static** `params` in `material.json`; no per-instance parameter call documented | offline + gameplay mod (`gs_require_stage`); instance fields are snapshotted game memory | shader body yes; mesh/material restart the scene | any (placed by script from `gd.joints`/`gd.player`) |
| **Stage DAT models** `gd.stage_add_model` | stage world pass, lit and fogged | `gd.stage_move` | 8 DATs, 64 models | offline | n/a | n/a |
| **Screen-space kit models** `gd.kit.model` | a rectangle of the HUD canvas (inventory cells) | yaw/pitch/spin/tint | 512 triangles each, 16384-quad list | presentation; online ok | n/a | n/a |
| **Tracers** `gd.tracer_add/_set/_bind/_window`, `gd.tracer_hitboxes` | ribbon in the world (depth optional) behind a point | anchor `right_hand/left_hand/right_foot/left_foot/head`, joint index, hitbox 0..4, held item, sword tip, all active hitboxes; start and end by `bind` (status channel) or `window` (frames) | 64 handles; fixed shaders `solid/glow/fire/electric/frost/dark`; 4 params; Catmull-Rom smoothing; cold variants are skipped (`gd.warm{tracers=true}`) | no gameplay gate; online correctness "unverified" [Read]; history rebuilt on restore | built-in WGSL only | role anchors use the fighter's part table (`ftParts_GetBoneIndex`), explicit index for custom skeletons |
| **Afterimages** `gd.afterimage_add/_bind/_window`, `gd.echo_afterimage` | pose-history copies of the fighter | start/end by `bind` (status 1..4) or `window`; tint per cause | 12 emitters, 1..6 copies, lifetime 2..31 logic frames; one emitter per port; no always-on (`trigger="flag"` default, others need `debug=true`) | as tracers | n/a | any fighter whose draws can be replayed; held-item and fog-range materials are skipped whole |
| **Part tints** `gd.dobjs`, `gd.dobj_tint`, `gd.parts` | single draw objects of a fighter (a glove, a hat) | rgb per draw object | measured: `gd.parts(1,true)` 0.785 ms a call, `dobj_tint` 53 calls a frame was 1.5 ms [Measured: `_build/audit-20261003/envoy-perf/PROGRESS.md`], so event-driven only | `parts_clear` is offline-gated; presentation | n/a | per fighter model |
| **2D overlay** `gd.fill/box/line/text`, `gd.kit.*` at `gd.project(joint)` | screen, always on top, in call order with the HUD | any, every frame from `on_draw` | 16384 quads/frame; `gd.kit.panel` 0.18 ms [Measured: envoy-perf] | `on_draw` does not run in resimulation; online ok | n/a | any |
| **Light** `gd.light_set` | one key light and ambient | direction, colours | affects only opt-in custom model materials, not fighters | visual-only | n/a | n/a |
| **Camera / hitstop** | not a signal [Read: presentation language; memory] | `gd.hitstop` offline only | | | | |

Fixed numbers worth keeping: 16 named params (each a `vec4f`, scalar in `.x`), 32 post passes, 128 live shader handles, 256
surface sources, 64 tracer handles, 12 afterimage emitters, 64 effect packages / 2000 particles / 256 emitter instances,
256 model instances / 128 model assets.

### 1.2 Things the docs are thin about that matter for this pass

| point | what I found [Read] | what stays unknown |
|---|---|---|
| `fx_attach` returns only a boolean; `fx_play` returns a handle | `gw_script.c` `l_fx_attach` pushes `handle>0`; `l_fx_play` pushes the handle | whether an attached effect survives the fighter's respawn or KO |
| `fx_play/fx_attach/fx_control/fx_end/fx_instance` are **not in the public scripting.md** (only `fx_world`, `fx_move`, `fx_end` are) | seen in `gw_script.c:3480-3580` and the `effects_lab`, `character_parts_lab` examples | the public contract; needs a doc line when used |
| Role anchors exist for tracers, not for effects | `script_motion.inc`: `common[]={LHandN,RHandN,LFootJ,RFootJ,HeadN}` resolved by `ftParts_GetBoneIndex` | the same table is a 20-line reuse for `fx_play` |
| Geno defines currently build on a base fighter's resources | geno.md §22 (`"base":"mario"`, `"resources":"retail:mario"`) | a fully own skeleton is future; explicit joint indices (0..254) are the documented route |
| The fx rate/size/brightness controls are per instance, shader params are per emitter | `fx_control` writes per handle; `gd.fx_shader` binds one shader and one param block to a package emitter | per-instance shader params do not exist |
| Model instance in front of a fighter | docs: opaque parts "test and write depth against each other"; "use this for decorative room kits, not solid foreground obstacles that should hide fighters" | whether a small model nearer the camera than the fighter occludes it correctly; try it first |
| Post-pass occlusion | `scene_depth` is "a snapshot of the chosen insertion point, not a fighter mask: translucent surfaces generally do not write it" and `gd.project` returns `depth` as its 4th value | the unit relationship between the two (calibrate) |
| Netplay classification mismatch | `_research/envoy-netplay-scoping-2026-10-05.md` §1b lists `fx_world/fx_move/fx_control/fx_end` and `model_*` as "presentation only"; the source gates them offline | one of them should change (section 2, spec C) |

---

## 2. The gap

### 2.1 What the owner asked for, against the engine

| ask | TODAY, world space with occlusion | TODAY, screen space only | not at all |
|---|---|---|---|
| orbiting orbs/particles around the body | **offline:** model instances moved each frame (the drive meshes themselves, small; `gd.joints` for the centre); or an effect package with a custom vertex shader (hard, see below) | `drafts/orbiters.wgsl`, with depth occlusion if the calibration works | online in any world form |
| follow a fist, hands, head (halo) | **offline:** `fx_play` on a joint index (depth tested); tracers on hands, feet, head (a trail, degenerate when the point is still) | `drafts/bone_glow.wgsl` (orb, halo, arc) on `gd.project` of a joint; 2D overlay glyph | role names for `fx_play`; online |
| spires of light | **offline:** package with y-billboard/cylinder emitters (the `DriveLoot_beam_*` packages already exist); a tall glass mesh with a scrolling fragment | `fanfare.wgsl` (tonight) | |
| bursts of flame | **offline:** package emitter with a custom fragment (port `flame.wgsl`; it uses UV and time, so it ports almost directly) | `flame.wgsl` (tonight) | |
| swirls and other rotations | sprite spin (`rotation.add`) and a custom vertex displacement by time | `flame_orbit`, `fanfare` ribbons (tonight) | a native swirl force; a steady orbit as an emitter motion |
| a circle at the place a hitbox will appear, aimed along the attack | model disc oriented by `rot`/`rot_x`/`rot_y` with a custom material: but its params are static, so charge and blast cannot be driven (only tint/alpha/scale) | `spell_cast.wgsl` + `spell.lua` (tonight), `drafts/strike_mark.wgsl` | rotation on effects; per-instance params |
| a script read of "where will this move's hitbox be" | `gd.timeline(port, motion)` already returns each hitbox event's frame, bone, offsets, size, angle (static) [Read: geno.md line 463]; the **world** position needs the animation pose | learn by watching (tonight) | pose at a future frame |

### 2.2 The smallest additions, as specs

Sizes are my estimates [Mine]. None is written. All keep one rule: the effect must be a pure function of snapshotted state
plus a deterministic clock, so rollback and re-simulation draw the same picture.

| id | gap | API shape | where | rough size | rollback / netplay note |
|---|---|---|---|---|---|
| **A** | native orbit motion and count | in a package emitter: `particle.orbit = {radius, speed, tilt, axis: "joint"|"world_z", phase_by_index: true}`; position = origin + circle(age, index), no integration; and a new `fx_control` key `count` (0..16: live orbiters kept alive, respawned in place) | `gw_fx.c` (simulate + schema validator), `ports/ir/schema/effects.schema.json`, `gw_script.c` `l_fx_control` key table | 150-250 lines | deterministic from particle age and index, so identical on re-simulation; `count` comes from snapshotted state |
| **A2** | swirl force | `forces.swirl = {axis, rate, falloff}` (a tangential acceleration about the emitter axis) | same files | 40-80 lines | deterministic |
| **B** | role names for bone effects | `gd.fx_play(pkg, port, joint, ...)` accepts `"right_hand"|"left_hand"|"right_foot"|"left_foot"|"head"` or `-1..-5`, resolved like the motion anchors | `script_motion.inc` already has the table; add a resolver next to `ScriptGame_PartsJoint` in `script_parts.inc`, call it from `l_fx_play`/`l_fx_attach` | about 20 lines | none (presentation) |
| **C** | rollback-safe, online effect binding (the key one) | `gd.fx_bind{port, package, anchor=role|joint, when={timed_status=1|crit_force|shock|armor|always}, count_from="status_stacks"|nil, controls={...}}` returning a bind handle. Instances are created and ended **by the engine each logic frame** from snapshotted state, stored in the FX driver ring (`fx_drv`) like Geno's `fx_bindings`, restored on rewind. Lua only declares; it is not called in replay | `gw_fx.c` `gw_Fx_Drive` (extend the condition set from motion states to the fighter's native timed-status channels, shock, crit force, armour), `gw_script.c` registration | 300-500 lines plus a demo | the whole point: no `fx_*` calls from Lua per frame, so no offline gate is needed. Also change `fx_*` docs/gates to match the scoping note |
| **D** | per-instance shader parameters, and rotation | `gd.fx_control(h, em, {u0=,u1=,u2=,u3=})` four extra tweened floats exposed to the effect fragment (via the `parts[ii]` storage or a small per-instance block); `fx_play`/`fx_world` take `rot` (degrees about Z) and `tilt` (about X) | `gw_fx.c` (instance record), `gw_shader_effects.inc` (expose), `l_fx_play/l_fx_world` | 100-200 lines | presentation; set from snapshotted state through C |
| **E** | where a hitbox will be | first: **no engine change**: a LAB pre-bake script steps `gd.set_motion(port, motion, frame)` and reads `gd.hitboxes(port, true)` for each frame, writing a per-fighter JSON table (`dx, dy` relative to the fighter, facing-normalised, size, angle, element) shipped as mod data; second, if it proves worth it: `gd.hitbox_preview(port, motion)` returning the same rows from the animation pose without moving the fighter | pre-bake is Lua only (offline, forks the LAB timeline, done once). The engine version is `script_game.c` plus read-only animation sampling on a scratch pose | pre-bake: about 80 lines of Lua; engine version: 400+ lines, a large item | read-only; no hash effect |
| **F** | per-instance params for custom **model** materials | `gd.model_set(inst, {params={...}})` | `gw_script_model_api.inc`, the material uniform | 60-120 lines | instance fields are snapshotted today; params would be presentation, outside the snapshot |
| **G** | a bone-bound camera-facing quad with a custom fragment, depth tested | already covered by an effect package with one `plate`/billboard emitter + custom fragment + spec B/C; no new primitive needed | | | |
| **H** | turn the offline gates into a decision | model and fx writes called per frame from Lua stay offline; online uses C | | | |

### 2.3 What can be done in the next live session with no engine change [Mine]

1. Player's fighter, screen space: orbiters (stacks), halo (keystones), fist orb/arc (armed), strike mark, fanfare: the four
   drafts. Passes are per fighter-carrier; budget at most 4 live (section 4).
2. Floor drops and rarity beams: already world-space (`DriveLoot_*`, `PickupJuice_*`); reduce counts.
3. Offline world props: model-instance orbiters made from the real drive meshes at scale 0.1 to 0.2 (the loved models, reused as
   they are), a spire from `DriveLoot_beam_*` moved with `fx_move` to the fighter each frame (`fx_world` + `fx_move`).
4. Hitbox table pre-bake in the LAB (spec E, first form).
5. Depth calibration and the in-front-of-fighter model test (section 2.4).

### 2.4 Two cheap experiments to run first (decide a lot)

| experiment | how | what it decides |
|---|---|---|
| post-pass occlusion | draw `orbiters.wgsl` with `depth.z=0`, then return `linear_depth(scene_depth(uv))` as a grey over the fighter's centre and compare with the 4th return of `gd.project(x,y,0)` | whether screen-space orbiters can pass behind the fighter and stage; if yes, post passes become acceptable for far more of this pass |
| model in front of a fighter | place a small drive mesh at `z` nearer the camera than the fighter and at `z` behind; look from the side | whether world-model orbiters occlude and are occluded correctly |

---

## 3. The visual grammar

### 3.1 Channels, each with one meaning

| channel | answers | carried by | values | source of the values |
|---|---|---|---|---|
| **WHO** | which drive family or element | **colour** and **silhouette** | red, green, blue, yellow, purple, white (the six drive families); an element conversion shows the element's colour (fire red, ice blue, electric yellow, darkness purple, the rule `drive_drop.lua` already uses) | the drive models' atlas rows and shapes: red caltrop, green double chevron, blue heater shield, yellow feather fan, purple spore orb, white shard gem [Read: `envoy_drives/README.md`, `make_drives.py`]. Rarity is a separate overlay: magic one cyan ring, rare two violet rings, unique a gold ring with a crown of eight points |
| **WHAT KIND** | what sort of piece | **carrier** | drive rule in passing: none (see below); drive rule that acts: **stamp** at its anchor; element conversion: **tracer** on the hitbox; held keystone or unique: **halo** over the head; status: **surface** on the body that has it; stack count: **orbiters**; armed next hit: **fist glow**; technique: **floor ring** at the feet; synergy: **floor circle**; level-up: **spire** | the record fields (`kind`, `trigger`, effect ops), by rule (`look_rules.lua`) |
| **WHEN** | state | **motion** (shape of the movement), never colour | idle/held: slow constant spin, dim; **armed**: brighter, steady, one slow breath a second; **charging**: ring tightens, spin accelerates (as `spell_cast`); **fired**: one flash and one burst, at most 24 frames, motes collapse to or leave the anchor; **stacking**: the new orbiter pops in with a ping; at the maximum the orbiters join into a ring; **expiring**: the last 30 frames the motes drop away one at a time outward (never a strobe); rotation direction is polarity: clockwise on the screen = a buff on yourself, counter-clockwise = something applied to a target | the engine's own timers (status frames, armour, crit force) |
| **HOW MUCH** | amount | **count**, **size**, **fill** | count of orbiters = stacks (1..5); size = tier or strength (1..3, or crit `strength` 0..1); ring fill = charge or time left. Brightness is not an amount: it is reserved for WHEN (armed) | status `stacks/max`, record tier, `on_crit` strength |
| **WHERE** | on the body | **anchor** | fist (right hand): the next hit; feet: movement and technique; head: a held keystone; chest: defence and armour; hitbox: a strike and what it carries; target body: something applied; floor: build identity and synergy; sky: reward | the trigger and ops, by rule |
| **LOUDNESS** | importance | **intensity** | the longer a thing lasts the quieter it is: a temporary status, an armed fist and a stack count are louder than a permanent keystone halo, which is louder than nothing | duration of the piece |

One consequence [Mine]: **a passive number gets no look of its own.** "Heavy", "Armoured", "Pyre" and the other equip-only value
drives only colour the single "identity" layer on the surface (the strongest family or a completed archetype) and show in the
HUD strip. Their effect becomes visible when it acts: Pyre's payoff is a larger contact stamp on a Burning target. This is how
the screen gets quieter without losing information.

The drawback of a keystone is shown as a dark counter-notch on its halo that flashes when the cost is paid (Wavedasher's 2
damage, Gambler's -20%) [Mine; optional, drop it if it reads as noise].

### 3.2 The rule is by field, not by name

`drafts/look_rules.lua` assigns carrier, anchor and state from `kind`, `trigger` and the effect ops (`convert`, `status`,
`crit_next`, `armor`, `heal`, `value`, `versus-status`, `crit`, `echo`) and the colour from the drive's colour or the
conversion's element. A renamed or split piece keeps its look as long as its fields are the same. Its self-test passes ten
records copied from the real pool (kindling, pyre, burning, crosswind, wave_edge, shield_stance, cleansing, pyromancer,
gambler, glass_core) and the allocator keeps "haste, armed crit, momentum x3" plus a dimmed keystone halo when five things
compete.

Fields pass 1 should keep stable so the grammar survives: `kind`, `trigger`, `effects[].op`, `visual.look`, drive colour
(family). If pass 1 adds a one-line "what it changes" tag per piece (damage, speed, defence, sustain, status, crit), it can
replace colour-by-family as WHO without touching the rest.

### 3.3 Storyboard: 20 real pieces

Pieces and fields from `mod_pool.lua`, `mod_techniques.lua`, `keystones.lua` (the keystones' rules from their cost lines).
"idle / armed / fires / stacks / ends" is what the player sees. "none" means deliberately nothing.

| # | piece (kind, trigger) | idle | armed | fires | stacks | ends |
|---|---|---|---|---|---|---|
| 1 | Kindling (drive, `hit_dealt`: apply Burn) | none | none | a red star-shaped spark at the contact point; the target's Burn ember rim starts | Burn stacks = rim intensity on the target (surface), no orbiters | rim fades in the last 30 frames, one ember lifts |
| 2 | Pyre (drive, equip: launch vs Burning) | none (feeds identity tint) | none | on a Burning target the contact stamp is larger and the rim flares once (the payoff) | none | none |
| 3 | Burning (drive, equip: smash becomes Fire) | none | none | fire tracer on the smash's hitbox for its active frames only | none | tracer ends with the hitbox |
| 4 | Updraft (drive, `hit_dealt` aerial: Momentum) | none | none | amber chevron pip leaves the contact and joins the waist orbit | one amber chevron orbiter per stack, 1..5, clockwise at the waist | orbiters drop outward one by one in the last 30 frames, the last one pops |
| 5 | Crosswind (drive, `landing`: spend Momentum, gain Haste) | none | none | floor ring at the feet in Haste green; one orbiter dives into the feet; Haste streaks start | stacks drop by one | streaks fade |
| 6 | Feasting (drive, `ko_dealt`: heal) | none | none | rising teal motes from the chest, count about heal/5 | none | motes rise out |
| 7 | Cleansing (drive, `interval`: cleanse) | none | none | silent unless it removed a status: one ring wipes down the body as that status's surface ends | none | none |
| 8 | of the Clean Landing (technique, `lcancel_hit`: Haste) | none | none | floor ring at the feet; existing earned afterimage while Haste lasts | none | afterimage ends with the status |
| 9 | of the Wave (technique, `wavedash`: next hit crits) | none | **fist orb** in the crit colour at the right hand, until used | floor ring at the feet at the wavedash; on the next hit the fist orb pops, the crit tracer and impact run | none | orb ends when the hit lands (it persists until then: one slot) |
| 10 | of the Stance (technique, `perfect_shield`: armour) | none | thin blue facet glint on the chest for its frames | shield-shaped flash at the chest | none | on absorb: shard burst; on timeout: fade |
| 11 | Keen (drive, equip: crit chance) | none | none | nothing of its own; the crit moment (impact + tracer, scaled by strength) is the look | none | none |
| 12 | of Critical Flow (drive, `crit`: Haste) | none | none | the crit moment, then Haste streaks; adds no look | none | streaks fade |
| 13 | Glass Core (unique, equip: +60% dealt and taken) | gold-crown halo, white, a hairline crack mark | none | none | none | none |
| 14 | Ember Crown (unique, equip: all hits Fire, take x1.3) | gold-crown halo with three red flame points | none | fire tracer on every hit's hitbox (conversion) | none | none |
| 15 | Plague Bearer (keystone, purple, `hit_dealt`: Burn target, Burn self) | purple halo, one notch | none | purple spore spark at contact; target ember rim; a brief ember rim on yourself (the cost) | target Burn stacks to 3 = rim | rims fade |
| 16 | Echo Weaver (keystone, white, equip: echo while Hasted) | white halo, one notch | none | while Hasted, two faint white copies trail each attack (the echo pictures) | none | copies stop with Haste |
| 17 | Wavedasher (keystone, green, `wavedash`: armour then Guarded, 2 damage) | green halo, one notch | none | floor ring at the feet, chest facet flash, Guarded surface for 12 frames, a dark counter-notch flashes (the cost) | none | Guarded surface ends |
| 18 | Gambler (keystone, white, equip: 35% crit, hits -20%) | white halo | none | the crit moment on a crit; x3 draws a larger impact than x2 (strength) | none | none |
| 19 | Critical Mass (keystone, white, `crit`: Momentum, Shock target) | white halo | none | crit moment, +1 amber orbiter, Shock arcs on the target | Momentum orbiters | as 4 |
| 20 | Juggernaut (keystone, blue, equip: armour under 6 damage, cannot run) | blue halo | none | a small shield stamp at the chest when a hit is absorbed | none | none |

Check against the budget: the idle build of a fighter holding 3 keystones, 2 uniques and 6 drives is **one** halo (with five
notches) and one identity tint. Nothing orbits until Momentum exists; nothing glows at the fist until a next hit is armed.

---

## 4. Budget and priority order

### 4.1 Numbers [Mine; to be tuned live]

| limit | own fighter | opponent | six-fighter match |
|---|---|---|---|
| persistent loud looks (surface, orbit set, fist glow, afterimage) | 3 | 2 (surface + halo) | at most 8 on screen in total |
| persistent quiet looks (the halo) | 1, dimmed to a thin ring when 3 loud ones are live | 1 | counts toward the 8 |
| momentary bursts | 4 a second | 2 a second, only those that touch the player or are caused by the player | 10 a second on screen |
| one burst | at most 24 frames and 40 particles; same slot within 12 frames merges into one | | |
| screen-wide effects | **1 at a time, never persistent**, at most 30 frames (fanfare 150) | none | none |
| post passes live | 4 of 32 (orbit, halo/glow, strike mark, one screen-wide) | 0 (world carriers only) | 4 |
| world emitters reserved for fighters | 60 instances, 600 particles of the engine's 256/2000 | 30 / 300 | drops and pickups keep the rest |

Why these [Mine]: three loud looks is about what a player can name at once; each post pass is a full-screen cost, so six
fighters with their own passes would be 6 to 18 passes; the 120 fps target is 8.3 ms [Owner/Read: memory
`performance-target-120-fps`]. The measured Envoy baseline in the LAB is about 4.2 to 4.7 ms frame_work for four fighters
with six mods [Measured: envoy-perf FINAL], so the headroom is real but not large.

### 4.2 What yields to what

| contest | winner | rule |
|---|---|---|
| a temporary state against a held one | the temporary one | loudness is inverse to duration; the halo dims to a thin ring rather than disappear |
| status surface against identity tint | the status | identity shows only when no status is live |
| armed fist against orbit stacks | the fist | the next hit is the decision; orbiters thin to 60% intensity while armed |
| any burst against a lower one | the higher, in order: crit (strength at least 0.6) > technique > triggered drive > status applied > pickup | when the 4/s is full, the lowest queued is dropped |
| a synergy moment against a crit impact | the crit; the synergy ring still blossoms (it is in the world, not screen-wide) | |
| two screen-wide effects | fanfare > strong crit > synergy pulse; the lower is dropped, not queued (the fanfare is queued) | |

Must be momentary instead of persistent: synergy (the floor circle), technique stamps, crit, level-up, drive collection. Must
stay persistent: statuses (they are state), the halo (held), orbit stacks (they are a count).

### 4.3 Showing the opponents' builds

[Mine] **Less, and only what matters to you.** Opponents show their statuses (surface), a thin halo if they hold a keystone
(their rule is the thing that will hurt you), and the nameplate's archetype tag (kept). No orbiters, no fist glow, no floor
marks, bursts only when they touch you or you cause them. In **online adversarial** play the same grammar applies at about 70%
intensity, because the opponent's build is information, not decoration. In co-op the ally gets the full grammar in their
port colour at 70%.

### 4.4 Six fighters on screen

| rule | effect |
|---|---|
| rank by relevance: you, then whoever is fighting you or nearest, then the rest | rank 1 full, rank 2 two looks, rank 3 and beyond one look (the strongest status) |
| level of detail by size on screen | orbiters and halo off below about 12% of the target height |
| a global cap of 8 persistent looks and 10 bursts a second | the allocator in `look_rules.lua` (`allocate`, `burst`) |
| post passes only for the player | other fighters use world carriers, hence the engine specs A, B, C |

### 4.5 What to remove or change in today's presentation

Inventory from `synergy_fx.lua`, `mod_display.lua`, `earned_fx.lua`, `visual.lua`, `run_hud.lua`, `drive_drop.lua`,
`modifiers_surface.wgsl` (all read). Frame numbers are as coded.

| current output | what it is | verdict | reason |
|---|---|---|---|
| 7 status surface treatments (burn ember rim, shock arc, chill frost, curse inverted rim, haste streaks, guarded facets, momentum stack climb) | surface; strongest 3 slots, rest faint tint | **keep**, but 2 slots, not 3 | the thing the owner notices; a third and a faint tint blur |
| 2 equipment layers (look + hue + strength per modifier and drive rarity) | surface, from every equipped modifier's `visual` and every drive's rarity | **cut** as a per-piece layer; replace with one identity layer | this is the pile: up to nine looks mixed into two layers and a combined hue |
| lane 14: assembled archetype on the surface (persistent .625, stronger while firing) | surface | **cut** the persistent part; keep a brief rise while a chain fires, or use the floor circle | persistent equals "always on"; a synergy is a moment |
| chain pulse post pass (`modifiers_chain.wgsl`, 18 frames, at least 30 apart, up to 0.06 strength) | screen-wide | **change**: only this or the crit pass may run, whichever outranks; or replace by the floor circle | the one-screen-wide rule |
| chain link flash (curved line between fighter and target in the archetype colour, with an emblem) | 2D overlay on top of everything | **cut**, keep only the co-op seat-to-seat link | duplicates the floor circle; an overlay cannot sit in the world |
| HUD emblem pill with a climbing counter | HUD | **keep** | text and emblems belong in the HUD |
| opponent nameplate archetype tag | HUD | **keep** | it is how opponents' builds are read |
| archetype announcement toast (`announce_frames=360`, 6 seconds) | text | **change** to 90 frames, one line | text only where a build is read; 6 s covers the fight |
| crit impact post pass (`crit.wgsl`, scaled by strength, floor `min_s=.12`) | screen-wide | **change**: no post pass below strength 0.35; light crits use the tracer and a contact spark | most crits will be light; do not tear the screen for them |
| crit tracer on active hitboxes (24 frames) | tracer | **keep** | "this hit carries something" is exactly its meaning |
| crit toast on a strong crit | text | **cut** | the impact already says it |
| earned afterimage, one emitter per fighter, tinted by cause | afterimage | **keep** | earned state only, as approved |
| pickup pulse post pass (`drive-pulse.wgsl`, 12 to 18 frames) | screen-wide | **cut** | the in-world collect burst already says "collected"; it uses the one screen-wide slot |
| floor drops: 5 emitters each (glow, pool, sparkles, highlight, pop trail) plus rarity beam and sparkles, `max_effect_drops=30` | world emitters | **change**: full set for the 6 nearest drops, glow and beam only beyond, none beyond 12 | 30 drops times 6 is 180 emitter instances of the engine's 256 |
| HUD flash, pickup card | HUD | **keep** | where a build is chosen |
| grid link marks, banner, offer marks (inventory UI) | UI | **keep**, but belongs to pass 1's screens | not fight presentation |

---

## 5. A look for each kind, worked out

Costs: **S** surface param update (free, 16 floats); **P** a post pass (full-screen, use `half=true` for soft glows); **W** world
emitter instances; **T** tracer handle. Carriers marked "needs B/C" wait on the specs in section 2.2 for non-player fighters
and for online; for the player's fighter offline they can use the interim route.

### 5.1 Drive rules

| option | what the player sees | carrier |
|---|---|---|
| 1 | nothing persistent; when it acts, a **stamp** of the drive's silhouette at its anchor, in the family colour, size by tier | W, 1 burst |
| 2 | a one-time **roll call** at stage start: the equipped drives' tiny silhouettes circle the fighter once (1.5 s) and dock into the HUD strip | P or W, momentary, once |
| 3 | a sticker of each drive on the body | rejected: persistent clutter |

**Recommend 1 plus 2.** Drive: `stamp.slot`, `stamp.colour`, `stamp.size`, `stamp.anchor` (contact, feet, chest, hands, target).
Cost: about 1 burst, 12 to 24 frames, 20 to 40 particles; roll call: one pass for 90 frames, once a stage.

### 5.2 Keystones (and uniques)

| option | what the player sees | carrier |
|---|---|---|
| 1 | a **halo** over the head: a thin tilted ring in the family colour with one notch per keystone; uniques wear a gold crown of points; the drawback is a dark counter-notch | bone-bound world quad (needs B/C) or `bone_glow` mode 1 for the player |
| 2 | a small spire of light above the head per keystone | rejected as persistent: too loud |
| 3 | a floor sigil | **momentary only**: blossoms for 24 frames when the keystone's trigger fires |

**Recommend 1, with 3 as its "fires" state.** Drive: `halo.count` (notches), `halo.colour`, `halo.phase`, `halo.dim`,
`halo.pulse` (on fire). Cost: one quiet look; P (half-res) for the player now, one world quad per fighter later.

### 5.3 The core statuses

| status | today | recommend |
|---|---|---|
| burn, shock, chill, curse, haste, guarded | surface treatment, intensity by stacks/max | keep the surface; add a **stamp at the moment of application** (small, in the status colour, at the affected body); expiry: last 30 frames the surface thins, never flickers |
| momentum | surface "stack climb" | **orbiters**: one amber chevron per stack, up to 5, waist height; the surface climb becomes secondary (or off) |

Options considered: orbiters for every status (rejected: clutter), floor rings for every status (rejected: floor is for
technique and synergy). Drive: per status a lane value (intensity), `orbit.count` for momentum, `orbit.phase`. Cost: S for all,
P or W only for momentum.

### 5.4 Technique triggers

| option | what the player sees |
|---|---|
| 1 | a **floor ring** at the feet in the technique colour (the existing technique pink, `0xFF3FA4`), size by speed, 18 frames |
| 2 | a small upward spire at the feet |
| 3 | only the earned afterimage (existing) |

**Recommend 1 plus 3** (earned states keep their afterimage). Where the technique arms something (wavedash then crit), the
**fist orb** takes over until it is spent. Drive: `ring.colour`, `ring.size`, `ring.age`. Cost: one burst; P (the strike mark
shader reused as a ring) now, W later.

### 5.5 Crits

| option | what the player sees |
|---|---|
| 1 | today: impact post pass plus tracer, scaled by strength |
| 2 | tracer plus a contact spark burst (world), post pass only at strength 0.35 and above |
| 3 | add hitstop | rejected: camera and hitstop are not signals |

**Recommend 2.** The armed state (`crit_next`) is the fist orb. Drive: `crit.strength` (size and count of sparks), post `progress`.
Cost: T + 1 burst, P only for strong ones.

### 5.6 Synergies

| option | what the player sees |
|---|---|
| 1 | assembled archetype: HUD pill and nameplate only; when a chain **fires**, a **floor circle** (tonight's spell circle) blossoms under the fighter for about 40 frames in the archetype colour with its motif at the centre (flame, frost, arc, chevron, web, plate, sight, burst, spike) |
| 2 | a persistent archetype ring on the floor | rejected: persistent |
| 3 | the HUD alone | too weak, the owner asked for visuals |

**Recommend 1**, with the circle drawn in (`drawn`) while the chain builds and `blast` when it pays off, as the owner liked the
charge-and-blast. Drive: `circle.colour`, `circle.motif`, `circle.drawn`, `circle.charge`, `circle.blast`. Cost: one pass for
the player now, one world plate later; momentary.

### 5.7 Level-up and reward moments

| option | what the player sees |
|---|---|
| 1 | **fanfare spire** (tonight's `fanfare.wgsl`: light column, spiralling ribbons, floor rings, sparks, star) once per depth cleared and at New Game Plus |
| 2 | a world spire (the existing `DriveLoot_beam_*` moved onto the fighter, with ribbons) |
| 3 | for a drive pickup: the in-world collect burst only |

**Recommend 1 for depth and NG+, 3 for drives**; 2 replaces 1 once world effects are online-safe. The one screen-wide slot: this
wins it. Drive: `prog` (0..1), `tint`, `height`, `radius` from `gd.project`. Cost: P for 150 frames, once.

---

## 6. Draft assets for the later live session

In `_build/audit-20261003/envoy-pass2/drafts/`. **None of the WGSL has been compiled or drawn.** They follow
`docs/shaders.md`: first line `// @module`, `fn mod_fragment(in: Input) -> vec4f`, lower-case params, every param a `vec4f`
read with `.x`, at most 16 names, no `@` in comments, no reserved words (checked by eye against the WGSL list; the Dawn compile
is the real test). Each has a header saying UNTESTED and what a script must feed.

| file | what | params |
|---|---|---|
| `orbiters.wgsl` | up to 8 orbiters on a flattened circle, depth-scaled, newest pops in, 4 silhouettes (orb, star, chevron, shield = the drive shapes), optional depth occlusion | 14 |
| `bone_glow.wgsl` | one shader, three modes pinned to a point a script moves: orb (armed fist), halo (keystone, with up to 6 motes, far half dimmer), arc (charge or time left) | 12 |
| `strike_mark.wgsl` | a small aimed mark: ring, ticks, a cone along the attack, charge tightening, blast (flash, shock ring, streak), reduced from `spell_cast.wgsl` | 10 |
| `look_rules.lua` | the grammar router, the persistent allocator and the burst gate; pure logic, **runs offline**, self-test passes | n/a |

Known risks in the drafts [Mine]: depth units unverified (`depth.z` defaults to 0, occlusion off); the astroid star and the
shield distance functions are my own and may need tuning; `previous_color` is called before any branch (needed for derivative
safety), but the compile will tell; bloom is not included.

---

## 7. How to run the pass

### 7.1 The live loop the owner liked [Owner / Read]

One game window left open in the LAB (not training), a shader or script edited and hot reloaded, a capture to check, repeat.
Post and effect shader bodies reload on save (250 ms poll); **fighter surface shaders do not poll** (call
`gd.fighter_shader` again); effect package JSON and model materials need a scene restart (assumption: not stated). Use the
fly cursor (`gd.fly_target`, `gd.fly_attack`) to position and hit, a CPU in `gd.cpu_mode(port,"stand")` as the target, and the
`synergy fx preview <archetype>` console command that already exists. The window runs on the second monitor for agent runs,
at 3% volume [memory: run-melee-on-the-main-desktop, melee-playtests-run-at-3-percent-volume].

### 7.2 What a session needs prepared

| item | why |
|---|---|
| pass 1's output (piece list, one rule each, `kind/trigger/op` fields stable) | the grammar assigns by field; confirm it reads them |
| the hitbox pre-bake (spec E first form) for the fighters in play | the strike mark and the synergy circle need "where"; learning by watching only works the second time |
| `gd.warm` for fighters and tracers after the surface selection and emitters exist | a cold variant skips or hitches |
| a depth calibration scene (section 2.4) | decides the post-pass occlusion route |
| the six-fighter LAB scene and a depth-12 build | to test the budget under load |
| `gd.perf()` before and after each carrier | the 8.3 ms target; compare with the envoy-perf baseline |
| the drafts copied under a mod's `shaders/` | shaders load relative to the calling mod |

### 7.3 Order to do the kinds in

| step | kind | why this order |
|---|---|---|
| 1 | the governor: cut the equipment layers, the persistent lane, the link flash, the toasts (section 4.5) | subtract before adding; the screen gets quieter at once; no new art |
| 2 | statuses: 2 slots, application stamp, expiry thinning | highest frequency; the look he notices |
| 3 | momentum orbiters | the one natural count |
| 4 | the armed fist (crit_next) | one decision, one place |
| 5 | technique floor ring | uses the strike-mark shader |
| 6 | keystone halo | persistent, needs the dim rule tested against 1 to 5 |
| 7 | crit contact spark and the 0.35 floor | |
| 8 | synergy floor circle (charge and blast) | the look he liked |
| 9 | fanfare for depth clears | rare; last |
| 10 | roll call at stage start | a nice-to-have |

Engine specs B and C can be built in parallel: they are what makes steps 3 to 9 work for opponents and online.

### 7.4 Decisions for the owner first (short questions, my suggested answers)

| # | question | suggested answer |
|---|---|---|
| 1 | Is a screen-space look acceptable on your fighter only, as an interim, while world-space effects are built? | yes |
| 2 | Orbiters: flat silhouettes of the drives (post pass, now), or the drives' own small models (world, offline only, later)? | silhouettes now, models once spec C exists |
| 3 | The budget: 3 loud looks and one dim halo on you, 2 on an opponent, 8 on screen, one screen-wide effect? | yes, tune live |
| 4 | Passive number drives get no look of their own (HUD and identity only)? | yes |
| 5 | Keystone = a halo over the head, one notch each; uniques a gold crown; the drawback a dark counter-notch? | yes, the counter-notch optional |
| 6 | Colour conflicts: blue is defence, ice-blue is chill, white is wild and guarded: elements override family colour on a hit; statuses keep their own colours on the body only? | yes |
| 7 | Cut the link-flash overlay, the crit toast, the pickup pulse, the 6-second archetype toast, the persistent archetype lane? | yes |
| 8 | Spend engine time on B (role names) and C (declarative, rollback-safe effect binding) before Envoy online? | yes; C is the one that matters |
| 9 | Opponents' builds shown less (status, thin halo, nameplate tag), and at 70% in online adversarial? | yes |
| 10 | Keep camera and hitstop out of the signal set? | yes |
| 11 | You said "But also we dont use emitters": do you want Envoy builds to use emitters on fighters (halo, orbit) after all? | yes, as the carriers above; confirm, because I read it as an observation, not a ban |

---

## 8. Credits

Outside ideas I leaned on. Nothing here copies code, art or rules from them; they are design references.

| source | author | link | what I took | belongs in `CREDITS.md`? |
|---|---|---|---|---|
| Path of Exile | Grinding Gear Games | https://www.pathofexile.com/ | the keystone concept (already credited, `CREDITS.md` line 51); the idea that stackable resources are shown as orbs circling the character | already listed; add "orbiting stack indicators" to its line if an orbiter set ships |
| Hades | Supergiant Games | https://www.supergiantgames.com/games/hades/ | the idea of colour-coding each source of power so a boon's origin is read at a glance | add if the family-colour grammar ships (idea credit) |
| Inigo Quilez, 2D distance functions | Inigo Quilez | https://iquilezles.org/articles/distfunctions2d/ | the signed-distance approach to drawing small shapes; my segment-distance helper is the standard formula | add if the distance helpers ship in a release shader |
| WGSL specification | W3C | https://www.w3.org/TR/WGSL/ | reserved words and uniformity rules (already cited in `docs/shaders.md`) | already cited |
| the spell circle, flame, orbit, fanfare examples | made in session with the owner | local scratch (`_build/audit-20261003/frozen-k/`) | the visual targets the drafts are reduced from | own work |

If the Dawn compile or the live session leads to copying anything from a shader reference, record author, link and licence in
the same change (standing rule: always give credit).

---

## 9. What this document does not establish

- Nothing was run; every "today" is read from docs and source. The five things to confirm on screen first: post-pass
  occlusion by depth (2.4), a model in front of a fighter (2.4), a texture-less custom-shader package, `fx_play` on a joint
  following through a KO and respawn, and whether `model_set` every frame forks the LAB rewind timeline.
- Costs in section 4 are budgets, not measurements; none of the drafts has been timed.
- Pass 1's proposal was not available (only its inventory at 22:31, 86 pieces); section 3.3 uses today's pieces. The storyboard
  covers 20 of 86; the rest follow the same fields by rule, which `look_rules.lua` checks only on ten records.
