# ports/skin: costume skins on a retail skeleton

These tools fit a model from another game onto a retail Melee fighter's costume, as a new costume file. Only the
meshes, skin weights and textures change. The retail joint tree and the object slots are copied unchanged, so the
skin cannot change gameplay. `AUDIT_costume_reads.md` explains why that keeps netplay in sync, and `jointdiff.py`
proves it for each built file.

No game data is in this folder. You run the tools on your own files, and the output goes to git-ignored folders.

| File | What it does |
|---|---|
| `skin.py` | The command-line core: `target`, `automap`, `retarget`, `build` (one command, from source to installed costume), `fetch` |
| `costumebuild/` | C# on HSDLib: `build`, `inspect`, `synth`. Writes the costume while keeping the retail joint structs untouched |
| `jointdiff.py` | Compares the joint tree and every non-visual field of two costume files byte for byte. Exits 1 on any difference and prints the first ones |
| `maps/<fighter>.bones.json` | Starter bone maps (names only). `luigi` was checked against the exported Brawl skeleton; `mario`/`drmario` assume the same rig family and are unverified |
| `maps/luigi.groups.example.json` | The object-slot config format |
| `coverage.py`, `coverage.md` | Reads the structure of all 26 targets (names and counts only) |
| `ui.py` | Skin Fitter, a desktop front-end that drives `skin.py` |
| `test_synthetic.py` | End-to-end test on made-up data |
| `AUDIT_costume_reads.md` | What the simulation reads from a costume file |
| `C:/melee-wt/skintool/tools/rust-port/skin_netcheck.sh` (worktree `port/skintool`) | Runs replays and a two-peer session with and without the skin, then reports frame-exact or not |

## Build the C# tool

```
cd ports/skin/costumebuild && dotnet build -c Release      # through scratch/buildlock.sh on the shared PC
```

## Convert a skin (example: a Brawl fighter onto Melee Luigi)

```
set -a; . ./.env; set +a
python ports/skin/skin.py fetch --fighter luigi --costume Nr --out _build/luigi-brawl/melee   # PlCo.dat + PlLgNr.dat
python ports/skin/skin.py target _build/luigi-brawl/melee/PlLgNr.dat --fighter luigi --plco _build/luigi-brawl/melee/PlCo.dat -o _build/luigi-brawl/target.json
#   read target.json "dobjs" (index, owning joint, TObj count), then write groups.json (see maps/luigi.groups.example.json)
python ports/skin/skin.py build --source _build/brawl/disc/files/fighter/luigi --fighter luigi \
    --retail _build/luigi-brawl/melee/PlLgNr.dat --plco _build/luigi-brawl/melee/PlCo.dat \
    --groups _build/luigi-brawl/groups.json --map ports/skin/maps/luigi.bones.json \
    --out _build/luigi-brawl/PlLgXx.dat --install _build/mods-local --name "Brawl Luigi" [--slot Gr]
```

`build` does the following, in order:

1. Exports the `.pac` with `model_export.exe`.
2. Reads the retail costume and names its joints from PlCo's `joint_to_part`.
3. Auto-maps the bones. Map-file entries win; then a same name gives confidence 1.0, a synonym 0.85, and the nearest joint by position 0.2–0.6.
4. Retargets:
   - Weights are summed per target joint, cut to 4 influences, renormalised and rounded to 0.01.
   - The mesh is re-posed per source bone onto the target bind pose (`--repose aim`, the default: each bone's direction is rotated onto the target joint's direction, and translated and scaled by the skeletons' height ratio; `rigid` uses full bind matrices; `none` does not re-pose).
   - Single-bound vertices are stored joint-local, the way HSD draws them.
5. Writes the costume with `costumebuild`:
   - The retail JObjs are kept.
   - Each DObj slot is filled as `replace`, `keep` or `blank` (one zero-area triangle).
   - The retail MObj and TObj chain are kept, so eye-blink texanims still address the same TObjs. Only the images change.
   - CI4/CI8 textures keep their palette as a TLUT.
   - Textures over 256 px are box-downscaled to CMPR (opaque) or RGB5A3 (alpha).
   - `alpha_test` sets an alpha-compare PE (alpha > 128, depth written).
6. Inspects both files, runs `jointdiff`, prints pass/fail checks and the netplay-safe verdict, and writes `<out>_work/checks.json`.
7. With `--install`, copies the file into `MODS/<name>/files/` with a `mod.json`. `--slot Gr` names it as that colour file, for builds that replace a colour rather than add an m-ex costume row. The manifest reuses the fighter's existing UI entries, so no new art is needed.

Check any costume on its own:

```
python ports/skin/jointdiff.py PlLgNr.dat PlLgXx.dat          # exit 0 = skeleton and non-visual fields identical
```

Check netplay (the shared build lock is taken for every engine run):

```
cd C:/melee-wt/skintool && tools/rust-port/skin_netcheck.sh <mods dir> luigi "/e/Projects/Melee Workspace/_build/replays" <out dir>
```

- Replays featuring the fighter are run with and without the skin. They must give the same status, last frame and first divergence.
- Two peers (host without the skin, guest with it) must produce identical hash CSVs. This step is skipped, with a note, when the build's netplay scene cannot pick the fighter. Today it is Falcon vs Fox only (`net.md`).
- No engine reads `MELEE_FORCE_COSTUME` yet. Install the skin over the colour the replays use instead.

## Limits the checks use

| Check | Limit | Why |
|---|---|---|
| Skeleton | bit-identical to retail | gameplay reads joints (audit) |
| Object slots | same DObj count, order and owning joint | the part-visibility tables index them; a short list faults |
| Influences | at most 4 per vertex; fails if more than 0.25 of a vertex's weight had to be dropped | HSD envelopes, same as Halberd |
| Textures | native GX formats only, at most 256 px per side | console texture memory; no PC-only palette POBJs (`--pc-palette` is never used) |
| Triangles, file size | at most 1.6x the retail costume | one player's costume is loaded on every peer; heap headroom for 4 fighters. This is a conservative project limit, not a measured console maximum |

## Coverage

`python ports/skin/coverage.py` writes `coverage.md`: all 26 fighters, including both Ice Climbers, Zelda and Sheik
as separate files, and Game & Watch, whose model is flat (noted). Joints, named common joints, extra joints, DObj
counts and the eye matanim are all read from the retail file, not hard-coded. Every fighter reads.

## Skin Fitter (UI)

```
python ports/skin/ui.py                       # PySide6 (already installed); no server, no network
python ports/skin/test_synthetic.py <dir> && python ports/skin/ui.py --demo <dir>   # the made-up test model
```

The window walks through five steps:

1. **Source**: drop a folder or file anywhere on the window.
2. **Bone map**: two trees with curves drawn between them, coloured by confidence. Click a source bone, then a target joint, to remap it. Save and load map files.
3. **Preview**: a software-rendered view with test poses (bind pose, arms raised, crouch, a run frame) and weight paint per joint.
4. **Checks**: pass/fail badges. The netplay verdict is green only when `jointdiff` passes.
5. **Build**: runs `skin.py build --install` and shows its log.

Keyboard: Ctrl+1..5 or Alt+Left/Right switch steps, Ctrl+O opens a source, Ctrl+S saves the map, and the arrow keys turn the preview.

Screenshots of the synthetic model are in `docs/` (see below).

![source](docs/1_source.png) ![bone map](docs/2_bonemap.png) ![preview](docs/3_preview_arms.png) ![weights](docs/3_preview_weights.png) ![checks](docs/4_checks.png)

## Tests

`python ports/skin/test_synthetic.py` builds a made-up retail costume (`costumebuild synth`) and a made-up 9-bone
source rig. The source rig has twist and helper bones, twice the scale, and different arm angles. It asserts:

- the auto-map;
- weights at most 4 and summing to 1;
- re-posed vertices on the target joints, read back from the written file;
- CI8 with its palette kept;
- a 512 px texture downscaled to 256 px CMPR;
- the alpha-test flag;
- DObj slots kept;
- `jointdiff` passes on the output and fails on a tampered copy.

## Front door (one skin at a time) and autogroups

```
python ports/skin/frontdoor.py
```

The window takes you through the steps in order:

1. Choose an unpacked Brawl folder or a mod build (`pf/fighter/...`). For a disc image it calls `unpack_disc.unpack()` if that module is present.
2. Pick the character.
3. Pick the skin. The window shows its triangles, bones, objects, textures and the largest texture size.
4. Pick the Melee fighter. It is pre-selected by `skin.detect`, which also uses the file and folder names to tell near-identical skeletons apart.
5. Choose "add as a new m-ex costume" or "replace colour XX".
6. Convert. This runs `skin.py build` with no slot config, so `autogroups` is used. The window shows the checks and the netplay verdict, and "Needs review" when autogroups or the bone map is unsure.

"Uninstall what I installed" removes only the folders this window created. Settings, including the Melee disc image, are stored in `%APPDATA%/SkinFitter/settings.json`, and paths are never logged. The demo is `python test_synthetic.py <dir>`, then `python frontdoor.py --demo <dir>/front`.

`brawl_root.py`: `brawl_root(folder)` and `characters(root)` (CLI `--brawl-root`). This is the hook for unpack steps.

`autogroups.py`:

- **`roles`** reads every retail object slot's role from the fighter data, using:
  - `ftData.x8` parts visibility: tables 0/1 are the high-detail and low-detail sets, group 0 is the default and other groups are alternates;
  - the eye texture-animation list `x8.x8`;
  - each slot's dominant joint, region, triangles and texture slots.
- **`tables`** writes `maps/<fighter>.roles.json` for all 26 fighters.
- **`groups`** assigns source objects to slots:
  - the biggest high-detail slot per region gets that region's geometry;
  - **eyes:** static. Retail's animated eye slots are blanked, because their blinks swap in retail images. The source eyes go into a head slot.
  - **hands:** the open hand rides the finger joints. The fist slot (weighted to a non-finger joint, which animations scale to show the fist) gets a rigid copy of the source hand, cut from the body by skin weights. This is inferred from the weights; the animation file is not scanned.
  - **low detail:** one slot gets a reduced copy at the retail low-detail triangle count, and the others are blanked.

  It records a per-slot reason and an overall confidence, and sets `needs_review`.
- `skin.py build` uses autogroups when `--groups` is omitted (pass `--fighter-dat Pl<code>.dat`).
