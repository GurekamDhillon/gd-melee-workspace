# 12. An authored fighter: your own model, skeleton and clips (slice 4, first steps)

Status: the converter and a drawn stand-in exist; a playable fighter on its own skeleton does not yet (see `melee/docs/geno.md` 22.3).

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

Not yet possible: wearing the model as a fighter (the loader still copies Mario's tables: `base: "none"` is slice 4's engine half),
and anything about feel. Credit: Blender, glTF 2.0 (Khronos), HSDLib (Ploaj).
