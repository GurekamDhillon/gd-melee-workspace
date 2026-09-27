# ports/

Fighter conversion tools, research, schemas and hand-written configurations for GD's Melee.
Generated game models, animations, textures, effects, sounds and UI art stay local and ignored.
Build them from your own source files; this repository does not supply game assets.

## Ports and names

| Port | Source and tools | Runtime scope |
|---|---|---|
| Halberd | Brawl Meta Knight; `halberd/tools/build_mk_slot.py` and model/animation/effect/sound tools under `halberd/` | m-ex slot plus Geno states for specials, glide and root motion; configs in `halberd/mods-slot/metaknight-slot/` |
| Ultimate Kirby | Ultimate source key `kirby`; `ir/tools/install_ultimate.py kirby` | own skeleton/costumes/animations on a Melee host; Kirby is the default host, not a full automatic translation of Ultimate's fighter code |
| Sora (`ultimate-trail`) | Ultimate source key `trail`; `ir/tools/install_ultimate.py trail` and `trail_*` generators | translated ACMD moves, Geno magic/physical specials, effect packages/bindings and Ultimate UI art; completeness is defined by the generated audits, not by the install succeeding |

The installer defaults to display names **Ultimate Kirby** and **Ultimate Trail**, manifest ids
`ultimate-kirby-slot` and `ultimate-trail-slot`, and scene tokens `ultimatekirby` and
`ultimatetrail`. `--name` changes the installed name and printed token. Sora's source/UI label
is a separate choice (`trail` / `SORA`); do not guess its scene token from a folder name.

Ultimate installs default to m-ex internal 52 / external 51, the same slot used by Halberd.
They are alternative replacements at those defaults, not three independently installed slots.
Choose compatible slot/files before combining packs. Point `MELEE_MODS_DIR` at their parent.

## Shared IR and Ultimate pipeline

`ir/schema/` describes fighters from Melee, Brawl and Ultimate. `ir/tools/validate.py` checks
schema/references/evidence; `build_melee_fighter.py` builds IR for any retail Melee fighter.
The Ultimate tools plan parts, convert meshes and animation, translate ACMD and install the result.
See [ir/README.md](ir/README.md) and [the Ultimate schema notes](ir/schema/engines/ultimate.md).

The install command needs generated IR, source assets and Melee host data.
Run `python ports/ir/tools/install_ultimate.py --help` for the complete argument list.
Relevant switches in this revision:

| Switch | Effect |
|---|---|
| `--host kirby` / `--host marth` | choose the Melee behaviour/data host (Kirby default; other registered hosts are listed in help) |
| `--moveset file --acmd file` | supply translated moves and source for the default ACMD audit; missing/stale audit inputs fail the install |
| `--geno file --row-clips file --extra-files dir` | ship generated specials/overlays, motion-row clips and article files |
| `--pc-palette 64` | emit PC palette POBJs and require engine `pobj_palette: 1` |
| `--c00-only` | only the first costume; otherwise available c00-c07 costumes are included |
| `--tex-format auto` | opt-in CMPR/RGB5A3 selection where alpha permits; default conversion is unchanged |
| `--jobs N` | parallel clip conversion; unrelated to the unmerged `GW_JOBS` build-script proposal |
| `--skip-acmd-audit` | deliberate unaudited install; writes skipped markers, not a passing audit |

Sora's `trail_magic_geno.py` and `trail_specials_geno.py` generate the Geno profile;
`ultimate_vfx_geno.py` imports effect packages and `trail_fx_bindings.py` binds them to actions.
The no-drop conversion path rejects unhandled gameplay commands, records allowed losses and
checks installed hitbox positions. Read `INSTALL.json`, `conversion_losses.json` and
`hitbox_positions.json` for each output. A fallback clip, approximate host feature or skipped
audit is not source-game parity. The Aerial Sweep carry-profile experiment was reverted.

## Halberd limits

[halberd/README.md](halberd/README.md) documents its pipeline and move approximations. Tuning,
Final Smash, sword hiding and entrance work remain distinct from conversion. Its old three-player
OOM report predates the PC fighter-heap increase; remeasure before treating it as a current cap.
The stable v1/v2 encoding copies cover their original subset; current game `pc/geno/geno.h`
and `docs/geno.md` also define v3-v5.5 additions.

## Folders

| Folder | What it is |
|---|---|
| [`halberd/`](halberd/) | **Halberd**: Meta Knight from *Super Smash Bros. Brawl*. |
| [`kirby-ultimate/`](kirby-ultimate/) | **Ultimate Kirby proof of life**: walk, run, crouch, six jumps, and uncharged ground/aerial side B on Melee Kirby, verified in the LAB. |
| [`ir/`](ir/) | The character IR schema, validator and Ultimate tools shared by every port. |
