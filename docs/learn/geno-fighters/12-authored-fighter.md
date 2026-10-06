# 12. From a glTF to a playable fighter (slice 4)

Status: the Courier is a fighter on its own skeleton (`base: "none"`): it stands, walks, jumps and attacks with its own clips, the Striker's moves retargeted by role. The engine half is still being finished (see `melee/docs/geno.md` 22.3 and the list at the end).

You author a fighter in Blender (or anything that writes glTF 2.0) and describe it with three JSON files. The worked example is the
Courier in `ports/vanilla-original/`: `manifest.json` (bones with roles, 179 clips, a clip for each of the engine's 351 motion rows,
costumes), `skeleton.json`, `hurtboxes.json` (15 capsules and an ECB), plus `out/courier.glb` and `out/tex/costume_<name>.png`.

1. Check the package: `python -m tools.geno.check_art <art folder>`. Errors name the file and field.
2. Build the engine files: `tools/geno/build_courier.sh` (Blender is needed only to regenerate the glTF; a player needs nothing).
3. What you get: one model file per costume (palette-skinned, one piece), one animation bank, and `plan.json` with the joint plan, the
   Melee parts table by role, the hurtboxes and the ECB in joint-local space.

Rules the converter follows: glTF Y-up facing +Z is the engine's model space (no axis change); at most 2 bone influences per vertex
(the palette path packs a model into few pieces: a model split into hundreds of pieces cost about 5 ms a frame); a retail-style material
(the texture is the diffuse lightmap); clips are one key per frame, rotations as Euler angles R = Rz Ry Rx; the engine's joint tree has
`TopN`, `TransN`, `XRotN`, `YRotN` on top, so the converter adds the ones your skeleton lacks.

 Credit: Blender, glTF 2.0 (Khronos), HSDLib (Ploaj).

## What the engine needs from the data (learned the hard way)

- **A constant channel is two keys, never one.** The engine's key reader takes a key's interpolation from the key *before* it, so a
  one-key track ends with no interpolation and writes an uninitialised zero to the joint. The converter writes constants as two
  linear keys of the same value. (Symptom: every limb flipped and the hips on the floor.)
- **Rotation is absolute.** A rotation track replaces the joint's rotation; it is not a delta from the bind pose. Rotations are Euler
  angles in a signed 16-bit fixed-point number: 1/4096 rad gives +-8 rad, so a channel that turns more than a turn and a half
  (a scarf in a thrown clip) is written at 1/1024.
- **Rows are played by number too.** Several of the engine's animation rows are reached without any state naming them (the fall
  blend plays two rows by number). The converter writes `row_clips` (the clip for every row by its engine name) and the loader
  gives a row nothing names that clip, else the idle clip: never an empty row.
- **Two states that share one of the donor's rows, with different clips of yours, each get a row.** The idle state owns the idle row
  (the idle picker re-reads it by number).
- **Attributes**: author all of them. Walk and run speed set the animation rate (rate = speed / the reference speed), so
  `slow_walk_max`, `mid_walk_point`, `fast_walk_min` and `run_animation_scaling` are the art's reference speeds from the manifest.
  `model_scaling` is 1.0 when the art is authored in Melee units.
- **Moves**: `python -m tools.geno.courier_moves` retargets the Striker's scripts onto the Courier by role (a hitbox's `joint=` is a
  joint of the fighter's own skeleton) and sets `PUT ANIM_RATE 1.0` (the clips are authored at rate 1.0).

## Hitboxes on your own limbs, grabs and the shield (slice 4d)

- **Hitbox sizes are in your fighter's units.** Mario's sizes (a fist of 4.6) are a third of a 11.7-unit fighter. Give each hitbox the limb
  it strikes with and a size that fits that limb: the Courier's `retarget.json` has `joint`, `x`/`y`/`z` and `size` per hitbox of a move.
  Draw them (the LAB's hitbox display) and check the box is on the fist or foot at the clip's hit frame, not on the body.
- **Check the timing against the pose, not the number.** The engine shows a charge smash's strike pose one frame after the clip's hit
  frame; `delay` in `retarget.json` starts the box a frame later. Compare `gd.player().anim_frame_f` with the joint positions
  (`gd.joints`) on the first active frame.
- **`grab_anchor` is where a held victim attaches** (the engine's `ThrowN`: the victim's centre is moved onto it), so put it in front of
  the chest. It is also the joint the shield bubble hangs from; the engine clears its translation while you guard so the bubble stays on the body.
- **Guarding needs a joint tree of your own.** Guard blends the body toward a pose tree from the fighter's data file; a `none` define uses its
  costume's joint tree. If your skeleton has joints no part table slot covers, they are skipped by that walk.
- **Independence census.** The log line `geno: census kind N: ftData fields still the donor's pointers: ...` lists what a `none` define still
  borrows from Mario; the aim is an empty list (`geno.md` 22.5).

