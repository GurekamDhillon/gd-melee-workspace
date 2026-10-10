# Packet 6: Attributes, animations and the model (outline)

**Status: unrun outline (notice dated 2026-10-10).** This packet has not been
executed as a walkthrough; source/document references are not gameplay or GUI
verification. Start with [Author a fighter](../author-a-fighter.md) for the current
artist-to-Blender-to-LAB path.

The attachment/table workflow below is retained alongside the current native
define/artist route; their resource requirements differ.

**Goal:** know which parts of a fighter come from Geno's JSON, which from the fighter's data files,
and what it takes to change each.

**Prerequisites:** packets 1 and 2.

## What comes from where

| part of a fighter | where it lives | how you change it |
|---|---|---|
| Attributes (walk, dash, jump, air, gravity, weight, shield: named fields) | the fighter's data file, copied in at spawn | Geno `attributes` by name, applied after the file and before the game's own modifiers (`melee/docs/geno.md` section 7). Packet 1 |
| Jumps beyond Melee's table | engine tables | Geno `jumps` (section 10) |
| Special attributes (per-move numbers, up to 265 words) | the data file's special block | Geno `special_attributes` by word index or byte offset (15.5). The reference warns that on a fighter whose clone base's code reads those words, overriding them can break the base (the Meta Knight file leaves it inactive on purpose: its `mk_special_attributes` note) |
| Move scripts | subaction rows in the data file | `subactions` overlays (15.5), packet 3 |
| New action states | Geno rows | `states` (16.1), packet 3 |
| Which animation a common state plays | the state table | `motion_anims` (19.12): up to 8 entries `{"motion": id, "subaction": row}` |
| Animations (the clips) | the animation bank | Author Blender actions and build them with the artist pipeline; source-game ports use packet 9 |
| The model and costumes | costume files named by the define or m-ex tables | Build original art with the artist pipeline; source-game ports use packet 9 |
| Name, presentation, costumes and audio | native define fields, or m-ex table rows for a table-based fighter | Native defines declare their own resources; the older m-ex route uses packets 0 and 9 |

## Attributes

`gd.attrs(port)` in the LAB returns the named attributes with their current values (14.3). Use it to learn
the names and the scale. The LAB's INSPECT mode (`5`, key `A`) compares two fighters' attributes,
differences first, which is a quick way to see how one fighter differs from another (14.9).
`normal_landing_lag` and the `landingair*_lag` fields are included (14.11).

The calibration rule used by the Ultimate pipeline: do not guess conversions. Fit them over fighters
that exist in both games, and note where a fit is poor (`ports/ir/tools/calibrate_attrs.py` and
`attr_apply.py` implement it for the Ultimate port; `ports/README.md` says the same).

## Animations: the limit you will hit

A state selects a row from the fighter's loaded animation bank. Original
Blender actions go through `python -m tools.geno.artist build` to a bank and
native row plan; see [Author a fighter](../author-a-fighter.md). Source-game
ports instead use tools such as `ports/ir/tools/convert_ultimate_anim.py`
and `install_ultimate.py`, with source data you own. After a bank rebuild,
restart the engine process; a match restart keeps its cache.

## The model and costumes

For an original mesh, [the artist pipeline](../../../tools/geno/artist/README.md)
exports Blender art and builds costume archives with `fighterbuild`; no
source-game assets are required. Follow [the tutorial](../author-a-fighter.md).
The Ultimate porting route uses `ports/ir/tools/export_ultimate_mesh.py`,
`plan_parts.py`, `plan_hurtboxes.py` and `fighterbuild`; that route needs
source-game assets, which are never in the repository (`ports/README.md`).

## Costumes

Costume files carry a colour suffix, such as `PlBmBu.dat` in Meta Knight's research mod. An m-ex
row holds the count (capped at 16 per fighter in the engine, from the vanilla-mods research note,
section 4.5). `install_ultimate.py` builds up to eight and `--c00-only` builds the first.
Native artist defines instead declare costume files/labels in their own fighter
resources; see the artist specification and tutorial.

## Check yourself (for the full packet)

- Which of the attribute names does the LAB show for your fighter?
- Why can a Geno state not add an animation?
- What does the pipeline write that Geno does not?

## Sources

- `melee/docs/geno.md` 7, 10, 14.3, 14.9, 14.11, 15.5, 16.1, 19.12.
- `ports/README.md`; `ports/ir/tools/install_ultimate.py` (docstring: steps 1 to 8);
  `ports/ir/tools/calibrate_attrs.py`, `attr_apply.py`, `convert_ultimate_anim.py`,
  `export_ultimate_mesh.py`, `plan_parts.py`, `plan_hurtboxes.py`.
- `ports/halberd/mods-slot/metaknight-slot/geno.json` (`mk_special_attributes` note).
- `_research/vanilla-single-folder-mods-2026-10-03.md` sections 1.3 and 4.5.
