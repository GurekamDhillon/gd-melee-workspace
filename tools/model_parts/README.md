# Character parts and effects lab

This is an offline diagnostic workflow for finding useful recolour controls in the
**loaded** character model. It preserves raw DObj selections and suggests groups
from measured geometry, skin influences and visible coverage. It does not assume
that character models contain semantic names such as “jacket” or “sword”.

Run these commands from the workspace repository. The inspected game checkout
is `GW_MELEE`, or `melee` by default. The app directory is `GW_BUILD_ROOT`, or
`_build` by default; `--app-dir` selects another build.

## Scan and review

```sh
python3 tools/model_parts/prepare.py --iso /path/to/melee.iso --fighters falco --interactive
MELEE_SCRIPT_DATA_DIR="$(pwd -W)/_build/scripts-data" bash tools/port/run.sh parts-lab --iso /path/to/melee.iso
python3 tools/model_parts/analyze.py _build/scripts-data/character_parts_lab_main --character falco
```

Open `falco-review.html` in that reports directory. Each card highlights its proposed
control in a real captured silhouette. Names are suggestions; classification confidence
describes the joint evidence, not certainty that a surface is a particular garment.
Edit the names, download the review JSON, and apply it:

```sh
python3 tools/model_parts/analyze.py _build/scripts-data/character_parts_lab_main --character falco --reviews /path/to/falco-reviews.json
```

The live mouse panel checks for updated measured controls every three seconds and
accepts them only when geometry, costume index, and the installed asset fingerprint
match. Updating a report preserves the raw-part selection. The grouped
selector includes primary surfaces (average coverage at least 1.5%) and visible
equipment candidates. **Raw parts** exposes every live fighter DObj. Hue, saturation
and brightness immediately change the selected draws; Highlight temporarily previews
them; Rainbow animates all parts. Restore clears colours and stops script-owned FX.
A neutral virtual pad on P4 prevents the no-controller prompt.

```sh
# Scan the 26 stock playable fighter selections and quit when complete:
python3 tools/model_parts/prepare.py --iso /path/to/melee.iso --roster

# Inspect stock costume ordering, including costume-specific hats/accessories:
python3 tools/model_parts/prepare.py --fighters pikachu,pichu,jigglypuff --list-costumes

# Capture a costume independently; outputs are named pikachu-c1-*:
python3 tools/model_parts/prepare.py --iso /path/to/melee.iso --fighters pikachu --costume 1

# Fast smoke check: idle and a real neutral-special input, two angles each:
python3 tools/model_parts/prepare.py --iso /path/to/melee.iso --fighters marth,link --quick

# Reopen the mouse panel and automatically cycle seven additional FX presets:
python3 tools/model_parts/prepare.py --iso /path/to/melee.iso --fighters falco --interactive --no-scan --showcase

# Restore the previously enabled mods:
python3 tools/model_parts/prepare.py --restore
```

Preparation backs up `mods/enabled.txt` once, then enables the diagnostic mod alone.
It installs generated assets beside the executable and never modifies the ISO.
Stock asset filenames and costume ordering come from the game checkout's own tables.
Batch completion is recorded in `batch-done.json`; its `run_id` must match the current
`config.lua`. Manifests, analysis reports, and the analysis summary carry that run ID.
The stock installer does not yet select arbitrary custom fighters
or enumerate every costume automatically. The runtime APIs inspect whatever fighter
is loaded, so custom scripts can inspect custom models too.

## Measurement and grouping

1. Resolve each fighter DObj to its owning joint, shared material objects and
   visibility-model state masks. Add currently fighter-owned HSD item DObjs as
   separate equipment records, with item kind, instance ordinal and tree path.
2. Decode supported rigid, single-bound and envelope-skinned triangle primitives.
   Measure posed world bounds, surface area and triangle-area-weighted joint roles.
   Use the fighter's own common part map; joint numbers are not shared between fighters.
3. Freeze five supported common motions and one neutral special entered by controller
   input. Capture front, back, left, right and two oblique angles. Direct camera edits
   now refresh the actual camera while simulation is paused.
4. Render paired complementary ID palettes at the same pose and camera. Keep normal
   skinning and self-occlusion, suppress other HSD geometry, and reject pixels that
   do not match both palettes. Edge blends, static HUD and backgrounds cannot simply
   count as a matching ID. Warm the first ID pipeline before capturing. Reject
   empty captures and clipped silhouettes.
5. Rank pixel coverage relative to the entire captured fighter silhouette, including
   zero for a part absent from a sample. Suggested groups use coherent common region
   and owner-joint evidence. Their coverage is the union of their member pixels.
   Shared materials are reported separately: draw overrides are independent even
   when two parts share an MObj or material data.
6. Preserve head details and hand surfaces as individual controls. A sword's length
   can provide equipment-candidate evidence, but a wide shield is not a hand simply
   because it follows a hand bone. No automatic hand merging is allowed. Owned item
   models always remain equipment. Hats, tails, hair and ambiguous body surfaces
   remain individually reviewable; low-confidence labels are not invented semantics.
   Draws attached to joints outside the canonical common-body map are flagged as
   attachment candidates, including back-mounted objects; that flag is evidence
   for review, not a guarantee the object is equipment.
7. Treat disjoint visibility-state masks in the same model as alternate geometry
   evidence. Never infer alternates merely because two parts were not visible together.
8. Bind reviewed names to schema, raw costume asset SHA-256, geometry signature and
   costume index. Reject reviews for a different fingerprint. Transient item indices
   appear in reports but are not exported as persistent numeric colour controls.

The report contains every part and proposed control, primary/detail/unseen priorities,
preview images, shared-material relationships, alternate-geometry evidence, sample
metadata, failures and limitations. `analyze.py` exits nonzero for failed captures.
Cancelled/partial scans are explicitly recorded; they must not be mistaken for a
complete roster validation.

## Runtime API

The new APIs are offline only:

```lua
local parts = gd.parts(1, true) -- refresh a snapshot; false/nil uses the cached snapshot
-- parts.geometry_signature / measurement_space / coverage_mode; records use zero-based indices
gd.dobj_solid(1, parts[1].index, gd.rgb(255, 180, 40))
gd.dobj_solid_off(1, parts[1].index)
gd.parts_clear()               -- clear only this script's colours and ID capture
gd.parts_id(1, false)          -- ID palette for the cached snapshot
gd.parts_id(1, true)           -- complementary palette; keep the pose/camera frozen
gd.parts_id_off()
gd.fx_attach("GoldEmbers", 1, 0, 0, 9, 0, 1) -- root joint, local offset, scale
gd.fx_stop()                  -- stop only this script's showcase instances
```

Snapshots are intentionally explicit and shared by the native inspection bridge.
Refresh after a fighter/scene change or before enumerating newly spawned equipment.
Live item records can retire; destruction removes overrides before memory reuse.
Colour calls on a retired snapshot entry return false; the panel marks it expired
and keeps the remaining controls usable. Scan again to inspect newly spawned items.
Lua receives identifiers and scalar metadata, never native joint/material pointers.

Colours are render overrides keyed by DObj. The original MObj, texture data and
compiled material are retained; clearing an override restores ordinary rendering.
Script error/unload and scene cleanup retire overrides. This diagnostic solid fill
does not preserve texture details or texture alpha cutouts. It is not a finished
artist-facing masked tint or a new shader authoring engine.

## Additional effect showcase

`make_presets.py` generates original procedural textures and seven packages:
GoldEmbers, FrostDrift, ElectricSparks, CrimsonSpiral, EmeraldRings, HeatShimmer,
and ShadowPulse. These exercise the existing sprite, warp, distortion and blend
algorithms. They are new compositions and assets, not seven new shader algorithms.
Previous/Next selects them; Rotate cycles them every five seconds. `--showcase`
saves a screenshot halfway through each effect in the reports directory.
Electric Sparks uses short-lived, branched bolt sprites rather than the frost
texture. Shadow Pulse combines a dark layer with a violet rim so it remains
visible against Final Destination. Heat Shimmer is intentionally a subtle moving
distortion; a still image is not a useful measure of its strength.

The larger parametric effects lab is tracked separately in
[`docs/EFFECTS-LAB-PLAN.md`](../../docs/EFFECTS-LAB-PLAN.md).

## Limits and checks

Shape-animation geometry is flagged unsupported instead of supplying false exact
measurements. Texture alpha cutouts are measured as opaque geometry. A neutral
special samples one point in time; it does not enumerate all held weapons, Kirby
   copy hats, detached articles, transformation states, spawned props or accessories.
Non-HSD effects and the second Ice Climber are not part of the selected fighter's
core mesh. These are coverage limits, not evidence those objects do not exist.

Python analysis requires NumPy. Pillow or ImageMagick accelerates PNG reads; a
built-in reader handles the normal noninterlaced 8-bit capture format without them.
The runtime and generated procedural assets have no Python dependency.

```sh
python3 -m unittest discover -s tools/model_parts -p 'test_*.py'
bash tools/port/build.sh
```

Tests cover all 512 palette IDs, complementary rejection, PNG data, missing and
mixed joint roles, independent wide/slender equipment, symmetric meshes, visibility
exclusivity, absent-sample coverage, group union, shared materials and stale reviews.
The Lua mouse workflow also exercises group selection, highlight/restore, raw-part
selection during report refresh, retired items, and effect rotation.
Build validation includes the native/PPC bridge and ABI checks. Screenshots and
reports derived from disc models stay in ignored build output; do not commit them
as original project art.

### Validation checkpoint — 2026-09-30

The local validation folder contains 28 passing character/costume reports. Falco,
Link, Marth, Pikachu costume 1 and Jigglypuff costume 1 passed all 36 capture pairs
each (180 total). The remaining 23 reports use the four-pair smoke scan, not full
pose/costume coverage. The full Falco report exposes 56 raw draws and nine primary
controls; Link exposes 95 raw draws and 20 primary controls. Visual review confirms
separate Link shield/scabbard/sword-hilt candidates and Pikachu hat components.

Actual pointer input and compositor captures verified live grouped recolouring,
Restore All, and effect rotation. Eleven analysis/panel tests pass. Classification
still suggests regions and attachment candidates; it does not automatically know
every garment or weapon name, and these samples do not exhaust costume/equipment
states across the roster.
