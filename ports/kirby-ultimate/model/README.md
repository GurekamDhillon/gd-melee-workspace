# Ultimate Kirby body costume converter

`build_model.py` reads Kirby's extracted Ultimate 13.0.2 `model.numshb` and
`model.nusktb`, retargets the normal and puffed body, open-eye mesh, arms, and feet onto
Melee Kirby's existing 46-joint rig, then writes a replacement costume archive.
The costume keeps Kirby's public symbols, joint order, material animation tree,
and low-poly model. It leaves the Melee action logic and collision data alone.

Run from the workspace root on the Windows machine with the local Ultimate
assets and ACE disc:

```powershell
python ports/kirby-ultimate/model/build_model.py --iso "C:/path/to/ACE.iso"
```

Default output: `_build/tmp/ultimate-kirby-model/PlKbNr.dat`, `model-report.json`,
`mesh.json`, and a stock costume copy. All are ignored game-derived output.
`--ultimate-model`, `--ssbh-python`, and `--out-dir` override machine paths.
`--stock-costume` can replace `--iso` when an ignored stock `PlKbNr.dat` is
already available. `inspect_assets.py` inventories the local Ultimate model
and relevant motion files without copying them into the repository.

The model uses Ultimate Kirby's normal `FaceN` body mesh, `Eye1` eye mesh, and
four eye atlases for Melee's stock open/half/closed/hurt texture animation.
Ultimate face expression meshes are not switched yet. The body atlas, arm
atlas, and solid foot skin texture are encoded as Melee RGB5A3. The encoder
takes BGRA bytes; using RGBA swaps red and blue. The default mesh preserves
Ultimate world rest, source triangle winding and outward normals, and culls
back faces. Copying Melee's front-face culling exposed the back of the eye
shell and hid its black pupils. The fixed c00 archive passed a clean LAB idle,
run and jump capture with visible pupils, cheeks, pink body and red feet:
`_build/runs/ultimate-kirby-outward-cullback-sequence/`. The run pose still
turns Kirby's face away from the side camera; animation alignment remains
under investigation. `--mapped-bone-local`, `--winding`, `--invert-normals`,
`--cull`, and `--unlit` retain the earlier diagnostic render paths.

Ultimate c00–c05 map to Melee `PlKbNr/Ye/Bu/Re/Gr/Wh.dat`. Pass the matching
`--costume-file` and `--ultimate-model` directory for another slot. The two
extra Ultimate palettes c06/c07 can be built from the stock Nr skeleton with
`--output-file PlKbOr.dat` and `--output-file PlKbBk.dat`; the resulting
archives expose the Nr joint and matanim symbol names. Game-side costume
table extension is required before those additional archives are selectable.
All seven additional palettes have passed structural conversion; they still
need a clean LAB palette capture before selection.

The body is bound rigidly to Melee Kirby's body joint by default. This avoids
unvalidated Ultimate-to-Melee mouth control mappings during movement. Pass
`--deform-face` to test the mapped face weights as a separate candidate.
For a limb deformation control, pass `--rigid-limbs`; it keeps each limb's
retargeted rest shape and binds an entire arm or foot to one Melee joint.
This removes toe/shoulder envelope blending during animation and must be
visually compared in the LAB before choosing a production binding.
The default `--preserve-world-rest` keeps Ultimate's source world-facing mesh
geometry when assigning Melee weights. This matches the face axis (forward
+Z) and requires the matching right-corrected animation archive. The older
bone-local rebind rotated the face toward +X and is available only as a
diagnostic with `--mapped-bone-local`.

## Hammer article

`build_hammer.py` converts Ultimate Kirby's c00 `model/hammer` wood and metal
mesh pieces and their color textures into the hammer article inside `PlKb.dat`.
Pass the already built movement/side-B fighter archive so its action scripts and
attributes are carried into the result:

```powershell
python ports/kirby-ultimate/model/build_hammer.py `
  --fighter _build/tmp/ultimate-kirby-mods/ultimate-kirby-movement/files/PlKb.dat
```

The ignored output is `_build/tmp/ultimate-kirby-hammer/PlKb.dat` plus a
structural report. The converter preserves the stock hammer article's two
joints, attachment, item parameters, and item states. `verify_hammer.py`
independently parses the resulting archive. The current article conversion
uses c00 source files; all eight Ultimate hammer palettes contain byte-identical
mesh and color textures. It needs a LAB rendering/attachment check before it is
installed in a playable pack.
The default imports both the wood and metallic overlay meshes. `--wood-only`
builds a diagnostic candidate without the metallic layer. Its BGRA-corrected
wood material rendered brown and stayed attached through a clean LAB side-B
swing in `_build/runs/ultimate-kirby-hammer-wood-bgra-sideb-capture/`.
The metal overlay and star art still need a clear camera check.
The source winding/outward-normal, back-face-cull candidate builds both wood
and metal and passed a clean LAB side-B swing without a crash:
`_build/runs/ultimate-kirby-hammer-full-cullback-sideb-capture/`.
The wood head is visibly brown and textured. A native Side B charge/walk
probe showed the head and yellow star after the host restored Kirby's Hammer
accessory callback in the dedicated states. Release poses still need direct
visual review with the latest dedicated animation rows.

## Stone costume forms

`build_stone.py` imports Ultimate Kirby's Stone meshes and color atlases into
the five high/low LOD Stone visibility groups in an already converted costume:

```powershell
python ports/kirby-ultimate/model/build_stone.py `
  --costume _build/tmp/ultimate-kirby-model/PlKbNr.dat
```

The default ignored output is `_build/tmp/ultimate-kirby-stone/PlKbNr.dat`.
The converter retains the 46-joint rig, 42-DObj layout, public joint and
material animation symbols, and all non-Stone geometry. The five existing
Stone states hold Ultimate's 100t, treasure box, Dosun, Kirby statue, and
Puyo block shapes. The sixth Ultimate Hammer statue is extracted into the
ignored `stone-mesh.json`. Pass `--append-sixth` to add it as high/low DObjs
42/43. That layout needs fighter visibility entry 7 and six-form Stone
selection logic in `PlKb.dat` before the statue can display. Ultimate c00–c07
have byte-identical Stone meshes and
color textures, so the same source directory converts all eight costumes.

`--camera-yaw-deg` rotates all Stone mesh positions and normals around the
source attachment Y axis. `--shape-yaws` accepts per-form overrides such as
`dosun=-90,ppon=180`. These are camera-facing diagnostics; preserve texture
UVs and compare each form in a clean LAB view before shipping a rotation.

The c00 candidate passed a native additive-slot LAB spawn and five Stone
activations in `_build/agents/kirby_native/runs/ultimate-kirby-stone-visual/`
with no fatal error. Distinct textured forms were visible, including the
treasure box, Puyo block, and 100t. The remaining two forms need direct
visual capture. All eight palettes have passed structural conversion with both
five-state and six-state layouts. The first six-form live test exposed a host
visibility table that only mapped forms 1-5; the dedicated form-6 mapping is
being tested in the native host lane. A global -90 degree camera trial faced
Dosun correctly but left 100t and the Puyo block sideways, so a per-form
trial is staged separately.

## Warp Star Entry model

`build_warpstar.py --fighter <PlKb.dat>` extracts Ultimate Kirby's c00 Warp
Star and writes the ignored `_build/tmp/ultimate-kirby-warpstar/PlUkWarpStar.dat`.
Its public symbols are `PlyKirbyWarpStar_joint` and
`PlyKirbyWarpStar_animjoint`, matching three-joint
Placement/Have/Rot trees. Placement is an unanimated parent for the fighter's
spawn position. Have/Rot carry the independent 120-frame source Warp Star
trajectory, orientation, and shrink. Rot holds five rigid DObjs (three star
surfaces and two transparent glow quads). Source vertices and motion use the
same 5/4.6 scale as the Kirby body. The material template comes from the
fighter's Hammer article; pass a structurally sound Kirby fighter archive.

The native Entry host must load both symbols, set Placement at Kirby's spawn,
play the Warp Star AnimJoint, and remove the article at frame 120. The source
group7/group8 visibility stays true through the clip, so no separate
visibility animation is required. The converter verifies an HSD round-trip,
but this model still needs an in-game render and timing check.
