# Geno artist specification: an original fighter from Blender to `base: "none"`

Status: authoritative as of 2026-10-08 (workspace `tools/geno/artist`, game `docs/geno.md` 22). It replaces the scattered statements in
`ports/vanilla-original/README.md`, `docs/learn/geno-fighters/12-authored-fighter.md` and `geno.md` 22.3, and says where they were wrong (section 14).
The workflow, the commands and the starter are in `tools/geno/artist/README.md`; the clip list is `docs/geno-artist-checklist.md`.

## 1. How to read a rule

Every rule carries a tag. Know which kind you are looking at before you fight it.

| tag | meaning | if you need to break it |
|---|---|---|
| **ENGINE** | the game rejects it, crashes or misdraws without it; cited to a game-repo file | change the engine (game repo) |
| **CONVERTER** | the importer (`tools/geno/artist`, `ports/ir/tools/authored_fighter.py`, `fighterbuild`) refuses it today | change the converter; the engine may already cope |
| **COURIER** | how the sample fighter (`ports/vanilla-original`) was built; a good habit, not a rule | ignore it |
| **STARTER** | what `blender/make_starter.py` generates; copy or replace | replace it |

Anything marked **measured** was observed in the game, not read from code.

## 2. Scale, axes, units

| rule | tag | detail |
|---|---|---|
| 1 Blender unit = 1 Melee unit (not a metre) | ENGINE | model space is Melee units; the Courier is 11.7 to the helmet, 12.4 to the crest. Fighters are 8 to 20 units tall. The validator warns outside 6..24 and suggests `art.scale`. |
| Soles on the ground plane (z = 0 in Blender, y = 0 in glTF) | ENGINE | the fighter's origin is at its feet; the ECB and landing assume it (warned beyond 0.5 units). |
| Blender: Z up, the character faces **-Y**, its **left is +X** | ENGINE (via the exporter) | glTF export with "+Y Up" gives glTF Y-up facing **+Z**, left +X, which is HSD model space: no axis change, no flip (geno.md 22.3, "Facts that cost time"). |
| Armature object at the origin, no rotation, scale 1, no parent | CONVERTER | `convert.build_plan` asserts the planned skeleton equals the glTF's (error `ARMATURE_TRANSFORM`); apply transforms. |
| Bone scale 1 in the rest pose, never animated | CONVERTER / ENGINE | scale is dropped from clips; a rest scale breaks the inverse binds. |
| One uniform `art.scale` | CONVERTER | applied to translations, vertices and inverse binds; no clip ever scales a bone. |

## 3. Rest pose

| rule | tag | detail |
|---|---|---|
| Any rest pose works | ENGINE | clips store **absolute** local rotations (not deltas from the rest), so the rest pose only matters for the skin and the guard blend (below). |
| A-pose, arms about 30-38 degrees from vertical, feet flat, legs straight | COURIER / STARTER | keeps rest weights out of the armpit and gives the shield/guard code a sensible joint tree. |
| The costume's joint tree is used for the **rest** of the guard blend | ENGINE (measured, geno.md 22.5) | the shield pose itself comes from your `Guard`/`GuardOn` clip at frame 0 (2026-10-08 correction), not the rest pose. |
| Right-side bones on -X, left on +X | ENGINE (hitboxes retarget by side) | the validator warns `SIDE_SWAPPED`. |

## 4. Skeleton roles

A **role** says what a bone is for. Bones are matched to roles by (in order): `fighter.json` `roles`, the sidecar the Blender export writes
(`<glb>.geno.json`, from the armature's `geno` custom property), the glTF armature extras, a bone named exactly like a role, and last a
name guess (reported as a warning, never silent). `.L` is the character's left (+X).

Sided roles: `shoulder`, `upper_arm`, `lower_arm`, `hand`, `thumb`, `fingers`, `upper_leg`, `lower_leg`, `foot`, `toe`, `item_socket` (`.L`/`.R`).

| role | Melee part | needed | note |
|---|---|---|---|
| `translation` | TransN | **ENGINE required** | the root-motion carrier; origin at the feet. The converter puts the synthesized `XRotN` (and `YRotN`) under it. |
| `hips` | HipN | **ENGINE required** | animated with translation (bob); the converter lifts the pivot joints to its rest height (measured: a tumbling fighter spun about its feet without it). |
| `head` | HeadN | **ENGINE required** | |
| `upper_arm.L/R` | LShoulderJ/RShoulderJ | **ENGINE required** | ftData ECB/hurtbox/IK fields name them |
| `lower_arm.L/R` | LArmJ/RArmJ | **ENGINE required** | |
| `upper_leg.L/R`, `lower_leg.L/R`, `foot.L/R` | LLegJ/LKneeJ/LFootJ (and R) | **ENGINE required** | |
| `item_socket.R` | RHaveN | **ENGINE required** | where a held item attaches |
| `grab_anchor` | ThrowN | **ENGINE required** | a held victim is moved onto it **and** the shield bubble hangs from it (one joint, two jobs; geno.md 22.5). Put it in front of the chest. |
| `spine` | WaistN | recommended | falls back to `hips`; the "centre" of the body for coin/IK fields |
| `chest` | BustN | recommended | |
| `neck`, `shoulder.X`, `hand.X` | NeckN, LShoulderN, LHandN | recommended | optional parts (plan_parts `OPTIONAL`) |
| `thumb.X`, `fingers.X` | LThumbNa, L1stNa | optional | hitboxes on a missing finger use the hand |
| `item_socket.L` | LHaveN | optional | reported "unresolved" and harmless (Kirby has none either) |
| `head_top` | (ftData x8/x44 field) | recommended | the joint above the head; falls back to the head's only child, else the head |
| `toe.X`, `root`, `victim_anchor`, `camera_focus`, `shield_origin`, `reflect_origin`, `absorb_origin`, `cloth_1..4` | none | optional | **not read by the engine today** (the registry never reads `role_joint`/`roles`); kept in `plan.json` for the future. The Courier's checker demanded them (`check_art.py:18`); that was a converter choice. |

Joint budget: **ENGINE** `GPL_MAX_JOINTS` is 256 (`pc/geno/geno_plan.h:6`) and the part limit 255 (`plan_parts.py` `limits`). The plan adds
3 joints (`TopN`, `XRotN`, `YRotN`), so export at most **252 bones**. Exactly one bone per role; extras are plain joints.

The 54-slot Melee parts table is derived from roles by `plan_parts.py`; the `ftData` joint fields (`x8 x30 x34 x38 x44 x54 x58`) resolve from it
and **every entry must resolve or the plan is refused** (`geno_define_registry.inc:823`, "unresolved role").

## 5. Skinning

| rule | tag | detail |
|---|---|---|
| One skinned mesh, one primitive, one material slot | CONVERTER | the palette path builds one piece (`fighterbuild --pc-palette 64`). A model split into hundreds of pieces cost about 5 ms a frame (12-authored-fighter.md). Join the body (Ctrl+J), one Armature modifier. |
| At most **2** bone influences per vertex | **CONVERTER** | `authored_fighter.py:252` / `convert.py`. The glTF carries 4 and the engine's envelope format is not 2-limited, but anything above 2 is untested. `art.reduce_influences: true` moves the extra weight onto the two strongest. The Courier README's "limit 4" described the exporter, not the contract. |
| Weights sum to 1, no unweighted vertex | ENGINE | an unweighted vertex sits at the model origin. The validator lists vertex indices. |
| Weighted bones per piece <= 64 | CONVERTER | `--pc-palette 64` (`fighterbuild/Program.cs:56`); more is untested. |
| Helpers (translation, sockets, anchors) carry no weight | STARTER | they animate independently of the body (`WEIGHTED_HELPER`). |
| Triangles | none enforced | the Courier has 2,580; the validator warns over 8,000. |
| Normals, UVs required | CONVERTER | UVs should lie in 0..1: textures are `ClampToEdge`, not tiled. |

## 6. Materials, textures, costumes

| rule | tag | detail |
|---|---|---|
| The material is "the texture is the diffuse lightmap" (TOBJ `0x00050010`, REPLACE, ambient/diffuse 179) | ENGINE (geno.md 22.3) | built by `fighterbuild`; flat base colours, vertex colours, normal maps, emission, transparency are **ignored/unsupported** (`FLAT_COLOR`, `ALPHA`). Bake colour into the texture. |
| One texture per costume, same UVs | CONVERTER | `fighter.json` `costumes[].texture` (PNG, RGBA); a costume without a file uses the image embedded in the glb. |
| Texture size: multiple of 4, up to 1024; 64-256 is typical | CONVERTER / GX | the Courier's is 128x64 |
| Team colours | ENGINE | a costume may declare `team: red/blue/green`, each once; undeclared teams use costumes 0, 1, 2 (geno.md 22.6) |
| Menu icon, portrait, stock icon | presentation | optional; without them the select screen shows letters and `DISC ART` (never Mario's face). The generator `ui_art.py` is Courier-only; not part of this pipeline yet. |
| Two files in one process with the same name share one load | ENGINE (geno.md 22.3) | costume files must have distinct names (`Gn<Token>_<costume>.dat` does) |

## 7. Collision: hurtboxes, ECB, hitboxes, sockets

| thing | tag | detail |
|---|---|---|
| Hurtboxes | ENGINE | 1..15 capsules (`geno_define_registry.inc:826`), each: joint, joint-local endpoints a/b, radius, height `high/mid/low`, grabbable. Declared in `fighter.json` `hurtboxes` (list), the armature `geno` property, or **generated** from the skeleton and the mesh weights when absent (a proposal: check in the LAB). Endpoints are rest-pose glTF coordinates in the config; the converter makes them joint-local. |
| ECB | ENGINE: **not read today** | `plan.json` keeps `ecb` but the registry never parses it; ECB offsets, IK lengths and ledge snap are the donor's numbers (geno.md 22.4 "Open"). Author nothing for it yet. |
| Hitboxes | ENGINE | not part of the model. They come from the move scripts: the default is the Striker's 32 scripts retargeted **by role** (`mario_joint_roles.json`), sizes and offsets scaled by height/11.7, animation rate forced to 1.0. Override per hitbox in `fighter.json` `moves.hitboxes` (by joint name) and `moves.delay`. |
| Smash strike pose shows one frame after the clip's hit frame | ENGINE (measured, geno.md 22.5) | the four charge smashes get `delay 1` by default. |
| Sockets | ENGINE | only `item_socket.R` and `grab_anchor` are consumed. Everything else is documentation until the engine reads it. Draw them in the LAB: INSPECT mode `J` joint numbers, `S` skeleton. |

## 8. Control rigs

Your own rig (IK legs, FK/IK switch, custom shapes, corrective bones) is welcome **for animating**. Only the **export skeleton** is exported
(select the deform armature + mesh; hide or delete the control rig from the export selection), because the game needs plain keys on the export bones.

1. Keep one armature that is the export skeleton: bones named as in the starter (or mapped in `roles`), no constraints/drivers.
2. Animate on your control rig. Name actions after engine rows (checklist).
3. Bake: `blender/control_rig.py` `bake(ctrl, export, bone_map=None, actions=None)` adds Copy Transforms from each control bone to its export bone,
   bakes every frame with visual keying (`bpy.ops.nla.bake`), and leaves `<Action>_baked` on the export skeleton with the `geno_*` properties copied.
   Tested on the starter (`blender/selftest.py bake`: the hand lands within 0.02 units of the control rig's).
4. Rename or keep the `_baked` actions (the exporter exports every action with a fake user; delete the unbaked ones from the export armature).
5. Do not export a control rig: `NO_ARMATURE`/`MESH_COUNT` stop it, and `CLIP_TARGET` warns when a clip animates a bone that is not in the skin.

Tested: a rigid-bone copy of the starter as the control rig. Not tested: IK/drivers (Blender's visual keying handles them; the bake only needs the result).

## 9. Inspecting it in the LAB

Run the printed command (it opens `mode=lab` with your fighter as P1 and Mario as P2). In the LAB (geno.md 14.9; TAB changes mode, F3 help):

| to inspect | LAB mode and key |
|---|---|
| skeleton, joint numbers (the numbers `hitbox joint=N` and `plan.json` use) | INSPECT (mode 5): `S` skeleton, `J` joint chips |
| hurtboxes, hitboxes, labels | HITBOXES (mode 2): `B` boxes, `L` labels; `U` hurtbox states, `W` swept hitboxes |
| ECB (donor numbers today) | HITBOXES `E`, or `gd.debug_stage(gd.stage_draw.ECB)` |
| animation timing | FRAMES (mode 3): action/frame chip, move timeline, scrub `Q`/`E`, `HOME` replay |
| sockets | INSPECT `J`, compare `gd.joints(1, true)` positions with the grab/item |
| clip actually playing | `gd.player(1).anim_name` (the bank clip name; a placeholder shows the clip it borrows), `anim_frame_f` |
| exact data | `gd.hurtboxes(1)`, `gd.hitboxes(1)`, `gd.timeline(1)` |

`python -m tools.geno.artist.proof_report` summarises a scripted run of idle/walk/run/jump/jab/shield/grab (`proof.lua`).

**When to restart**: the game reads a define's `geno.json`, `plan.json`, models and bank **once at start** (geno.md 22). After every rebuild, quit and relaunch;
a LAB hot reload (geno.md 14.10) is for Lua/scripts, not for new model or bank files. A different `MELEE_MODS_DIR` needs a new process anyway.

## 10. Animation export

| rule | tag | detail |
|---|---|---|
| 60 fps, one key per frame on **every** animated bone, linear interpolation | CONVERTER | frame i is t = i/60 s. `CLIP_FPS`, `CLIP_UNBAKED` explain how to export. Starter/exporter settings: NLA tracks, "Always Sample Animations", no animation optimisation, Y up, extras on. |
| Rotation keys on every animated bone; translation only on `hips` (always) and `translation` (root-motion clips only) | **ENGINE (measured)** | "a translation track on any other joint zeroed that joint's offset" (`authored_fighter.py` comment, 12-authored-fighter.md). The validator warns `CLIP_TRANSLATE`. |
| Constant channels are written as two keys | ENGINE (geno.md 22.4 "The pose bug") | done by the converter; you do nothing. |
| Rotation is absolute, stored as Euler R = Rz Ry Rx, 1/4096 rad (1/1024 for channels turning more than 1.5 turns) | ENGINE / converter | max encode error is reported (0.0005 rad on the Courier). |
| One clip <= 128 KB encoded | ENGINE (geno.md 22.3) | the converter checks the encoded size and names the clip |
| Clip name <= 31 characters; <= 256 clips | ENGINE | `geno_plan.h:9`, `gn_plan_parse` |
| frames = key count; the animation runs frames 0..n-1 and a loop wraps from n-1 to 0 | CONVERTER (tree frames = n-1) | for a loop, end one step **before** the first pose (do not repeat frame 0). The validator warns `LOOP_SEAM` if the wrap jumps more than the clip's own steps. |
| Action naming | CONVERTER | an action named like an engine row (`Wait`, `Attack11`...) serves it. Anything else needs `fighter.json` `clips.map` or the custom property `geno_rows="RowA,RowB"`. |
| Hit frames | CONVERTER | custom property `geno_hit_frames` (JSON list) or a pose marker named `hit` on the action; compared with the move script's first hitbox frame (`HIT_FRAME`). |
| Loop flag | CONVERTER | `geno_loop` property, else the action's cyclic flag; the table also knows which rows loop. |
| Root motion | CONVERTER | `geno_root_motion` property or `clips.root_motion`; only rolls, getups and ledge moves. Everything else is in place: the engine moves the fighter. |
| Locomotion reference speed | ENGINE | walk/run clips play at rate = ground speed / reference speed. The importer **measures** the planted foot's speed (`loco.py`, within 5% of the Courier's hand-made numbers) and writes `slow_walk_max`, `mid_walk_point`, `fast_walk_min`, `run_animation_scaling`. `LOCO_RATE` warns when the top speed would play the clip faster than ~3.5x. |
| A move ends when its clip ends | ENGINE (measured on a prototype fighter) | a clip shorter than its move script cuts the move off. Placeholders are therefore **held on their last pose to the script length** (`<Row>_pad`); your own short clip is warned (`CLIP_SHORT_FOR_MOVE`). |
| Every one of the 351 motion rows needs a clip or an explicit "no animation" | ENGINE | the importer fills each with the first available fallback, else `Wait`, and lists them as placeholders. Only `Wait` is mandatory. |

## 11. Files and configuration

`fighter.json` (JSON; whole-line `//` comments allowed):

```json
{ "schema": "geno-artist/1", "key": "my-fighter", "name": "My Fighter",
  "art": { "blend": "my.blend", "glb": "art/my.glb", "scale": 1.0, "reduce_influences": false },
  "roles": { "Pelvis": "hips" },                       // only for bones the exporter's role table does not cover
  "costumes": [ { "name": "default", "texture": "art/tex/default.png" }, { "name": "red", "team": "red", "texture": "art/tex/red.png" } ],
  "clips": { "map": { "Idle": ["Wait"] }, "root_motion": ["EscapeF"], "loop": { "Idle": true }, "ignore": ["Scratch"] },
  "hurtboxes": "auto",                                  // or a list of {id, bone, a, b, radius, height, grabbable}
  "attributes": { "walk_max_vel": 0.95 },               // over the 46 defaults (data/default_attributes.json)
  "moves": { "hitbox_scale": 0.85, "delay": {}, "hitboxes": {} }, "output": "../_build/artist/my-fighter" }
```

Derived, never hand-kept: bones, hierarchy, rest pose, roles (armature), clip names/lengths/loops/hit frames/root motion (sidecar), row map (name + fallbacks),
hurtboxes and ECB (skeleton + weights), locomotion speeds (measured), file names and symbols (from `key`: token `MyFighter` gives `GnMyFighter_<costume>.dat`,
`GnMyFighterAJ.dat`, `PlyMyFighter_Share_ACTION_<Clip>_figatree`).

Outputs (never committed): `build/` (plan.json, mesh_*.json, models, bank, `build-report.md`) and `mods/` (`enabled.txt`, `geno-lab/`, `<key>/`).
No disc data is read at any point.

## 12. What the engine still takes from Mario

A `none` define borrows the donor's action scripts, callbacks and the unnamed attribute fields; the census line names the `ftData` fields still the donor's
(`x18 x1C x24 x2C x48 x5C`). Item grips, effects on missing parts and Kirby's copy are not exercised. ECB, IK lengths and ledge snap are the donor's numbers.
Presentation art, own audio, AI and records are separate, optional blocks (geno.md 22.6, 22.7).

## 13. Not supported (say so rather than discover it)

Multiple meshes or materials per fighter, transparency, vertex colours, bone scale, translation on limbs, more than 15 hurtboxes, more than 252 bones,
per-bone IK in the export, shape keys, cloth/dynamics bones (they animate as normal bones), a second skin, `.gltf` with external buffers (export `.glb`).

## 14. Contradictions found in the docs, and what the code says

| statement | where | what the code does |
|---|---|---|
| "the converter adds [`TransN`] ... the ones your skeleton lacks" | `12-authored-fighter.md:17`, `authored_fighter.py:10` | It synthesizes only `TopN`, `XRotN` and `YRotN`. **`TransN` is your `translation` bone and is required**; without it `build_plan` fails (`next()` on a missing `trans`). |
| "at most 2 influences" vs "(limit 4)" | `12-authored-fighter.md:14`, `ports/vanilla-original/README.md:36`, `validate.py` of the Courier checks 4 | The converter refuses >2 (`authored_fighter.py:252`, "the Courier contract"); 4 is the exporter's setting. 2 is a CONVERTER rule, not an engine one. |
| 12 roles required | `check_art.py:18` | The engine needs 15 roles (section 4) and reads none of `victim_anchor`, `camera_focus`, `shield_origin`, `reflect_origin`, `absorb_origin`, `root`. |
| "What is left (the engine side, none of it started)" | `geno.md:2651` (22.3) | Done in 22.4-22.5: registry, loader, files, roles, rollback, guard. 22.3 is now annotated. |
| 255 bones | `check_art.py:21` (`MAX_BONES`) | The plan adds 3 joints to a 255-part limit: 252 bones. |
| the ECB is part of the authored data | `hurtboxes.json`, `12-authored-fighter.md` | Not read by the engine (`gn_plan_parse` has no `ecb`; geno.md 22.4 "Open"). |
| "clip longer than 0x20000 / 4 frames" | `check_art.py:76` | The limit is the **encoded** size (128 KB); the converter checks that after encoding. |
| the Courier's special clips are `NCharge`, `SLunge`, `Rise`, `Counter` | Courier manifest | They are aliases of the engine rows `SpecialN`, `SpecialS`, `SpecialHi`, `SpecialLw` (+`Air`); name yours after the rows. |
| `plan.json` `roles` | Courier output | Courier role names (`hand`); the general importer writes canonical ones (`hand.L`). The engine reads neither. |
