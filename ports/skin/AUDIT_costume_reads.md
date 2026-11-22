# What gameplay reads from a fighter costume file (decomp audit)

Source: the decomp in the `pc-port` / `rust-port` trees (`src/melee/ft/`, checked in `C:/melee-wt/skintool`).
This is the basis for the netplay rule in `ports/skin`: **a skin may change meshes, weights, materials and
textures, and nothing else.** `jointdiff.py` enforces that rule mechanically.

## The costume file is loaded as one joint tree

`Fighter_UnkUpdateCostumeJoint_800686E4` (`ft/fighter.c`) takes
`CostumeListsForeachCharacter[kind].costume_list[costume_id].joint`, which is the costume's `*_Share_joint` symbol.
It instantiates that tree (`HSD_JObjLoadJoint`), and `ftParts_80073758` then indexes every joint into `fp->parts[]`
in depth-first order. Everything the simulation knows about the body comes through those joints.

| What the costume file holds | Read by the simulation? | Where |
|---|---|---|
| Joint count and depth-first order | **yes**: `fp->parts[i]` and the figatree track order assume it | `ftParts_80073758`, `ftanim.c` |
| Hierarchy (child/next) | **yes**: a joint's world matrix is its parents' product | HSD JObj update |
| Rest SRT of each joint (rotation, scale, translation) | **yes**: animation tracks override only animated channels. Unanimated channels keep the costume's rest value, and `ftAnim_8006FA58/8006FB88/8006F994` copy rest transforms from `fp->x108_costume_joint` (TransN and others) | `ft/ftanim.c` |
| Joint flags (classical scaling, hidden, skeleton bits) | **yes**: they change matrix composition | HSD JObj |
| Inverse bind matrices | indirectly: they are only used for skinning (visual). They are still kept identical so the file matches retail byte for byte in every joint field | — |
| `x8AC_animSkeleton` (the blend skeleton) | **yes**: built from the costume joint | `ftanim.c:992` `ftParts_8007482C` |
| World positions of joints, and through them hurtboxes, ECB/environment bones, hitbox attach points, item hold (`HaveN`), throw/grab (`ThrowN`), camera box | **yes**: hurtbox and ECB *definitions* (bone index, offsets, radius) live in `PlXx.dat` (ftData), not the costume, but the bone positions they ride on come from the joint tree above | `ftcoll`, `ftcamera`, `ftCommon` |
| DObj count and order | **only for visibility**: `ftParts` part-visibility tables index DObjs by global order (`FT_DOBJ_AT`) and set or clear `HSD_DObj` hidden flags. A missing DObj faults (`ftparts.c` 600-700 note). Not read by the simulation, but it must be preserved or the game crashes | `ft/ftparts.c` |
| PObj geometry, skin weights, envelopes | no (render only) | — |
| MObj/TObj/images/palettes, material animation (`*_matanim_joint`: eye blinks) | no (render only). The texanim addresses TObjs by DObj/TObj order, so keeping the retail TObj chains keeps blinks working | `ftparts`, `ftmetal.c` |
| Metal and low-poly | Metal swaps every MObj for a global metal material (`ftmetal.c`: `HSD_DObjModifyFlags`), so it is render only. Low-poly/alternate models are other DObjs switched by the same visibility tables | `ft/ftmetal.c`, `ftparts.c` |

## Consequences for a skin

1. The joint tree must be bit-identical to retail: count, order, parent of each joint, flags, SRT, inverse-bind presence and value. This is what `jointdiff.py` diffs.
2. The DObj count, order and owning joint must match retail. Otherwise visibility, hand swaps and model-part switches address the wrong objects or fault. `skin.py` only fills retail DObj slots: `replace`, `keep` or `blank`.
3. Everything else may differ freely without affecting the simulation, so peers with and without the skin stay in sync.
4. Memory is the remaining cross-player risk: the costume is loaded into the fighter heap for everyone who sees it. If the file is much larger than retail, one player's skin can exhaust another player's heap. `skin.py` therefore checks file size, triangles and textures against the retail costume. This applies on console, Slippi Dolphin and the port alike.

Not verified here: m-ex's own costume-table code. It uses the same `costume_list[].joint` path, but m-ex's added costume rows were not read in this audit.
