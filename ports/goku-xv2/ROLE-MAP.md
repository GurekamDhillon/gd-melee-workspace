# Goku bone-role map

This is the single vocabulary mapping used by the source IR and artist adapter.
Anatomical correspondences are inferred from names, hierarchy and bind positions;
they have not been observed in XV2. Left means character-left (+X).

Authorities: [schema BoneRole](../ir/schema/assets.schema.json),
[artist roles, section 4](../../docs/geno-artist-spec.md#4-skeleton-roles),
[parts resolver](../ir/tools/plan_parts.py), and the v0.1
`decoded/chara/GOK/GOK_000.esk.rig.json` BlobRef on
`skel:chara/GOK/GOK_000.esk`. Its raw evidence is
`ev:raw/chara/GOK/GOK_000.esk` in [the source IR](ir/goku.xv2.ir.json).
The render skeleton has 122 joints; the body EAN reference has 130. Match names,
never reuse the EAN joint index as a render or destination joint index.

| Schema BoneRole | Artist role | XV2 bone or destination decision |
|---|---|---|
| `top_n` | `root` | `EXP_GOK_000`; artist also synthesizes its own TopN. |
| `trans_n` | `translation` | `b_C_Base`; rebase the carrier to the feet while preserving bind-space geometry. |
| `hip` | `hips` | `b_C_Pelvis`; preserve bob and put measured pelvis height in the rebased local bind pose. |
| `waist` | `spine` | `b_C_Spine1` |
| `chest` | `chest` | `b_C_Chest` |
| `neck` | `neck` | `b_C_Neck1` |
| `head` | `head` | `b_C_Head`; attachment target for the rigidly baked hair rig. |
| `clavicle_l` / `clavicle_r` | `shoulder.L` / `shoulder.R` | `b_L_Shoulder` / `b_R_Shoulder` |
| `shoulder_l` / `shoulder_r` | `upper_arm.L` / `upper_arm.R` | `b_L_Arm1` / `b_R_Arm1` |
| `arm_l` / `arm_r` | `lower_arm.L` / `lower_arm.R` | `b_L_Arm2` / `b_R_Arm2` |
| `hand_l` / `hand_r` | `hand.L` / `hand.R` | `b_L_Hand` / `b_R_Hand` |
| `leg_l` / `leg_r` | `upper_leg.L` / `upper_leg.R` | `b_L_Leg1` / `b_R_Leg1` |
| `knee_l` / `knee_r` | `lower_leg.L` / `lower_leg.R` | `b_L_Leg2` / `b_R_Leg2` |
| `foot_l` / `foot_r` | `foot.L` / `foot.R` | `b_L_Foot` / `b_R_Foot` |
| `toe_l` / `toe_r` | `toe.L` / `toe.R` | `b_L_Toe` / `b_R_Toe` |
| `thumb_l` / `thumb_r` | `thumb.L` / `thumb.R` | `h_L_Thumb1` / `h_R_Thumb1` |
| `finger_index_l` / `finger_index_r` | `fingers.L` / `fingers.R` | `h_L_Index1` / `h_R_Index1` |
| `hand_item_r` | `item_socket.R` | Source IR points at `b_R_Hand` as an anatomical proxy only. Author an unweighted stable child socket; `g_R_Hand` has source translation animation. |
| `hand_item_l` | `item_socket.L` | Same proxy at `b_L_Hand`; optional destination socket. |
| `throw_n` | `grab_anchor` | Source IR points at `b_C_Chest` as a proxy only. Author an unweighted helper in front of the chest; it carries both the held victim and shield origin in this engine. |
| `jaw` | no consumed artist role | `f_C_Jaw`; source facial information remains in the IR. |
| `eye_l` / `eye_r` | no consumed artist role | `f_L_EyeIris` / `f_R_EyeIris`; source expression information remains in the IR. |
| no asserted source role | `head_top` | Optional authored helper above Head; `g_C_Head` is not evidence of a head-top position. |

All other source bones keep their names and scoped indices; a missing semantic
role is preferable to an invented one. The hair's separate skeleton attaches at
`head`; the belt's separate skeleton attaches at `hip`. Baking those rigs loses
SCD secondary motion and must appear in the conversion loss report.

The target adapter can collapse facial skin weights into Head to fit the
64-weighted-bone piece budget. This loses facial skeletal deformation and must
not be described as preserved expression animation. Merge duplicate remapped
weights before selecting and normalizing the strongest two influences.

The requested 128 loaded-joint ceiling includes the artist pipeline's three
synthesized joints. Destination joint numbers are generated from the converted
skeleton and published with the artist output. Gameplay consumes that map; none
of the source indices above are destination joint indices.
