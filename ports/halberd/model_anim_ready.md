# Meta Knight Phases 2 and 3 are ready (model + animations)

For the Phase 1 agent (the `mods-slot/metaknight-slot` owner) and for GD. Everything is local and nothing is committed.

## What to copy where

Run this after every `tools/build_mk_slot.py`. That script rewrites `PlBm.dat`, `PlCo.dat` and `MxDt.dat`, so the install has to be repeated each time:

```
python ports/halberd/model/tools/install_mk.py ports/halberd/mods-slot/metaknight-slot
#   --scripts=phase1  (default) your scripts still use Kirby's joint numbers: bones are remapped (see below)
#   --scripts=mk      your scripts already use MK's joints: nothing is remapped
#   --no-vis          leave ModelVis out of the scripts (only do this if you emit it yourself from anim/vis_events.json)
```

I have not run it on the real slot. I only ran it on a copy (`model/test/mods/metaknight-slot`). It is append-only (existing bytes and offsets stay put) and it writes `<mod>/MK_INSTALL.json`.

| file (into `<mod>/files/`) | from | what |
|---|---|---|
| `PlBmNr.dat`, `PlBmYe.dat`, `PlBmBu.dat`, `PlBmRe.dat`, `PlBmGr.dat`, `PlBmWh.dat` | `model/out/` | Costumes. Brawl 00 is Nr, 05 is Ye, 03 is Bu, 01 is Re, 02 is Gr, 04 is Wh. Publics are `PlyMetaknight5K_Share_joint` and `PlyMetaknight5K_Share_matanim_joint`. |
| `PlBmAJ.dat` | `anim/out/` | MK clips only (4.9 MB, 268 figatrees). No Kirby clips are inside. |
| `PlBm.dat` (patched in place) | your file | The ftData joint fields (x8, x1C, x20, x30, x34, x38, x44, x54, x58, x5C), the motion table, the script bone remap, ModelVis events, and the demo-table hole. |
| `PlCo.dat` (patched) | your file | Parts table [4][52] is MK's (105 joints). The insert-slot table [5][52] is NULL: Kirby's copy-hat slots must go. |
| `MxDt.dat` (patched) | your file | Row 52/51 anim file is `PlBmAJ.dat`; costumes 0-5 point at the files above and the MK symbols. This is done by `brawl-kirby/tools/mxdt_clone.py`, run with src = dst. |

## Skeleton contract (please build scripts against this)

- There are 105 joints in DFS order. **Joints 0-76 are FitMetaknight00's bones with the same indices as Brawl**, so a Brawl hitbox or hurtbox bone id *is* the Melee joint.
- Joints 77-103 are the merged cape article (`Mt` + the article bone name).
- Joint 104 is `TransN2`.
- The full list is in `model/work/skeleton.json` and `model/converter_report.json`.
- Hitboxes: write the Brawl bone id directly (use_common = 0) with the Brawl offset. Your current writer uses Kirby joint numbers plus scaled offsets. `--scripts=phase1` maps those joint numbers back to MK joints by name (31 becomes RHaveN 40, 2 becomes XRotN 3, 36 becomes LFootJ 68, and so on), but the offsets stay scaled.
- Hurtboxes are MK's 9 Brawl capsules on joints 73, 69, 6, 36, 11, 72, 68, 38 and 13. A "hurtbox bone state" command must name one of those joints, or the engine asserts `illegal parts` (`ftcoll.c:3129`). That assert is how the first in-game run died, on Kirby's inherited foot bones. The remap now sends inherited Kirby bones to these joints.
- GFX and hurtbox-state bones inherited from Kirby's scripts are Kirby *part slots*. The remap sends them to MK through the role table.
- Visibility (`anim/vis_events.json`, `melee_modelvis_suggested` per row), using script command 0x7C:
  - **ModelVis(0, v)** is the cape: 0 closed cape, 1 wings, 2 the merged cape article (shield, rolls, spot dodge, Dimensional Cape, Wait3, up taunt).
  - **ModelVis(1, v)** is the body: 0 body, 1 mantle ball.
  - The sword is always drawn.
  - Kirby's clone OnDeath sets both models to 0 at spawn. Kirby's multi-jump ModelVis(0, 1) therefore gives MK his wings.
  - `install_mk.py` inserts these events into copies of your row scripts as a stopgap.
- Clip lengths are Brawl's, not Kirby's. Retime from `anim/out/motion_rows.json` (`frames` per row).
- Smash attacks are Start + attack joined. The script's SmashCharge frame must be 21 for fsmash, 4 for usmash and 1 for dsmash.
- Special rows get MK's specials:
  - Kirby 305/320 SpecialN start, 306/308/321 SpecialNSpin, 307 SpecialNEnd.
  - 322 SpecialSStart and 323 SpecialAirSStart.
  - 324 SpecialHi, 325/329 SpecialHiLoop, 326/327/330/331 SpecialHiEnd, 328 SpecialAirHiStart.
  - 332 SpecialLwStart, 333 SpecialLw, 334 SpecialLwEnd, and the air versions on 335-337.
- Extras are in `PlBmAJ.dat` but no row points at them yet. For a new m-ex row, use the symbol `PlyKirby5K_Share_ACTION_<clip>_figatree` with the offset and size from `motion_rows.json` `extras`. They are:
  - Glide: GlideStart, GlideDirection, GlideWing, GlideAttack, GlideEnd, GlideLanding.
  - Specials: SpecialSDrill, SpecialSEnd, SpecialAirSEnd, SpecialAirNEnd, SpecialLwF/B, SpecialAirLwF/B.
  - Moves and taunts: AttackS3S2, AttackS3S3, AppealHi, AppealS, Wait3.
  - Holds and misc: AttackS4Hold, AttackHi4Hold, AttackLw4Hold, and more.
- 152 rows that share a clip were **renamed** to that clip's symbol. Examples are the copy-ability and inhale rows (a still pose) and the six Swing1 rows. Don't assert on Kirby names in those rows.

## Status

- In-game run: training (`p1=mexext:51`) and a CPU-9 VS match on a copy of the slot, with main exe port 51763/51764.
- MK's own model and clips play in every state I drove, with no crash.
- The results screen asserted "Demo Status error" (`ftdata.c:2129`). This is **not a model/animation bug**. The port counts an m-ex fighter's demo motions only up to the first one with no script, and Kirby's demo table has a script-less hole at entry 4. So every Kirby clone gets 4 demo motions, **brawl-kirby-slot included** (its `PlBk.dat` has the same hole). `install_mk.py` gives the hole an End script. The results screen still uses Kirby's win poses on MK's tree (the demo motion archive is Kirby's).
- Full report: `model/converter_report.json`. Rebuild everything: `python model/tools/build_p23.py`.

## Visuals pass (eyes, shine, results poses, cape, drill) - 2026-09-23

- **Both eyes.** Brawl's eye material `medama` has three layers: the body on TexCoord2, then one eye per TexCoord0 / TexCoord1 island (the other UV set lands on the texture's transparent border). mkbuild used to keep TexCoord0 only, so the -x eye was blank. The eye DObj now has three TObjs: skin (REPLACE), then two `COLORMAP_ALPHA_MASK` eye layers on TEX1 / TEX2, as Yoshi's eyes. It is unlit (Brawl `C1ColorEnabled` false). `brawl_matdump.exe uvs` dumps the third UV set (`model/brawl/eye_uvs.json`). `mkbuild eyecheck` (run by build_model.py) verifies both layers, opposite sides, mirror error 0.024.
- **Eye animation.** `anim/tools/mk_eyes.py` turns 111 SRT0 clips (Brawl Maya texture SRT converted to HSD TObj SRT) into 848 quantised states (<= 0.008 uv). The costume matanim holds them per eye TObj (frame k = state k). `tools/build_mk_visuals.py` (slot build step 9) merges SetTexAnim(0 + 1, state) into every Brawl-clip row and overlay. Kirby's blink subroutine is inlined and its eye commands are dropped. ftData x8 costume TObjs = [6, 5].
- **Shine.** armer (shoulder pads) and kenn_akai (gem) get a REFLECTION + COLORMAP_ADD layer, with Brawl's TEV factor baked into the sphere map. Specular appears only on `mask` (Brawl channel 1 colour).
- **Results.** `anim/out/GmRstMBm.dat` (`ftDemoResultMotionFileMetaknightBm`) holds Win1/2/3, their Waits and Lose on MK's tree, with the J02Win1/J02Win2 cape article merged. install_mk writes them to demo rows 0-3 and 5-9, with visibility and eye scripts, and points MxDt result_file[51] and demo strings[52] at them.
- **No-cape state.** Cape model 0 now has an empty state 3 (up taunt 21-75, cape vanish 12, Win1 end).
- **Cape vanish.** `build_mk_effects.cape_warp_colanim` adds common colour-anim 95 (violet, fading) with each MantleStart / MantleEnd burst.
- **Drill.** The blue streak generator gets DirVec (Brawl: Directional particles, direction = speed).
- **geno.json.** Slot build step 10 moves every overlay's words to `geno/sub_NNN.txt`: 2384 -> 403 JSON nodes, under the parser's 2048.
- **Checks.**
  - `tools/ingame_visuals.py` (needs the Lab `gd.dobjs`, private/geno 56a31aac9).
  - `tools/ingame_results.py` (VS match to the results screen; written, not run yet).
