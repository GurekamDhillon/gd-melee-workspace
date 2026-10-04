# Packet 6: Attributes, animations and the model (outline)

**Status: outline.** It states what is data you can edit and what needs tools this course does not
provide. No step was run.

**Goal:** know which parts of a fighter come from Geno's JSON, which from the fighter's data files,
and what it takes to change each.

**Prerequisites:** packets 1 and 2.

## What comes from where

| part of a fighter | where it lives | how you change it |
|---|---|---|
| Attributes (walk, dash, jump, air, gravity, weight, shield: 40 fields) | the fighter's data file, copied in at spawn | Geno `attributes` by name, applied after the file and before the game's own modifiers (`melee/docs/geno.md` section 7). Packet 1 |
| Jumps beyond Melee's table | engine tables | Geno `jumps` (section 10) |
| Special attributes (per-move numbers, up to 265 words) | the data file's special block | Geno `special_attributes` by word index or byte offset (15.5). The reference warns that on a fighter whose clone base's code reads those words, overriding them can break the base (the Meta Knight file leaves it inactive on purpose: its `mk_special_attributes` note) |
| Move scripts | subaction rows in the data file | `subactions` overlays (15.5), packet 3 |
| New action states | Geno rows | `states` (16.1), packet 3 |
| Which animation a common state plays | the state table | `motion_anims` (19.12): up to 8 entries `{"motion": id, "subaction": row}` |
| Animations (the clips) | the animation file | not Geno. Convert and install them with the pipeline (packet 9) |
| The model and costumes | the costume files | not Geno. The pipeline builds them (packet 9) |
| Name, icon, costume count, sound bank, results | m-ex table rows | not Geno. m-ex rows built by the installer (packets 0 and 9) |

## Attributes

`gd.attrs(port)` in the LAB prints every attribute with its current value (14.3). Use it to learn
the names and the scale. The LAB's INSPECT mode (`5`, key `A`) compares two fighters' attributes,
differences first, which is a quick way to see how one fighter differs from another (14.9).
`normal_landing_lag` and the `landingair*_lag` fields are included (14.11).

The calibration rule used by the Ultimate pipeline: do not guess conversions. Fit them over fighters
that exist in both games, and note where a fit is poor (`ports/ir/tools/calibrate_attrs.py` and
`attr_apply.py` implement it for the Ultimate port; `ports/README.md` says the same).

## Animations: the limit you will hit

A Geno state plays a subaction row that already exists (packet 2). To have new animations the
fighter's `AJ` file needs new clips and the data file needs rows that name them. In this tree that is
produced by the port tools, from source-game data you own:
`ports/ir/tools/convert_ultimate_anim.py` (clips) and `install_ultimate.py` (rows, installation).
A person working by hand has no editor in the tree for these files. Packet 10 records this.

## The model and costumes

Models are built by `ports/ir/tools/export_ultimate_mesh.py` and the `fighterbuild` project (C#),
with parts planned by `plan_parts.py` and hurtboxes by `plan_hurtboxes.py`. They need the source
game's assets, which are never in the repository (`ports/README.md`). A model-making guide for
authors who bring their own mesh does not exist yet.

## Costumes

Costume files carry a colour suffix, such as `PlBmBu.dat` in Meta Knight's research mod. An m-ex
row holds the count (capped at 16 per fighter in the engine, from the vanilla-mods research note,
section 4.5). `install_ultimate.py` builds up to eight and `--c00-only` builds the first.

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
