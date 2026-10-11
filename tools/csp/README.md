# CSProject UI rendering for Geno fighters

This tool uses a local external copy of [Melee-CSProject](https://github.com/AeonSSB/Melee-CSProject)
with portable **Blender 3.5.1**, then converts its camera renders into a built
Geno package. CSProject, models, textures, renders and portable Blender live
under workspace `_build/`; none are vendored. The template Scene and its
referenced datablocks are appended in memory, and no derived .blend is saved.

The 2026-10-10 packet was implemented with file tools only. Tests and Blender
execution have **not** been run. Read the assumptions below before the first
local render; camera and add-on internals could not be inspected in this lane.

## Backends and framing (2026-10-10)

`--backend csproject` (default) is the template path below. `--backend own` runs
`own_render.py` on current Blender (tested 5.2.2; `--blender`, `GW_BLENDER`, a known Steam
install, or PATH): our own cameras, three sun lamps, world and materials, nothing from
CSProject at runtime. Both write the same camera names (nine template names plus
`Results_SD`, the 52x74 results card) so conversion and publish are shared. Add
`--no-publish` to render and write previews (`<run>/final/c000-<field>.png`, with outline
and shadow applied, at the retail sizes) without touching the package.

Every asset is framed from the fighter's own posed skeleton (`framing.py`), not from the
donor character's camera positions: stock = neck to top of head, icon = chest up, portrait
= waist (spine joint) up, results and large render = floor to top. Joints come from the
built plan's role table (`plan.roles` plus `joints[].name`, with workbench
`art.bone_aliases`; `ui_render.roles` overrides); the top and the horizontal extent come
from the skinned mesh, so hair and outstretched arms are inside the frame. A missing joint
falls back to a fixed body fraction and is listed under `anchors.fallback` in the report.
The CSProject path keeps each template camera's angle and lens and only moves it. Camera
to asset (by name and size): `CSS Icon` 64x56 select tile, `CSP` 136x188 portrait, `STC`
24x24 HUD stock icon, `Render` 1000x1500 large render, `All-Star` 256x230 (use unverified).

Two causes of the old "every camera looks the same, and the pose floats" are fixed in the
CSProject worker: the template binds cameras to timeline markers, so every render switched
to the last bound camera whatever `scene.camera` was (markers are now unbound and camera
animation cleared; the report lists `bound_markers`); and Goku's GLB carries a 2-unit
`Icosphere` helper at the origin that set the floor three units below his feet (bounds now
use only the skinned, textured body meshes). `Wait:0` resolves to the plan bank clip
`Wait` (no `moves/Wait.json`), GLB action `Wait`, sample 0: a real idle stance, near the
rest pose. A retail base without a `Wait` clip uses `Wait1`.

Retail look reference (local only, never committed): `dump_menu_assets.py --only
MnSlChr.usd` into `_build/csp-own/ref`; the 136x188 CSPs there are tight chest-up crops
with a hard offset shadow and white edge light. `contact_sheet.py` lays backends side by
side.

## Preparation and paths

From the workspace root, with git and a host Python that has Pillow:

    python tools/csp/fetch_csproject.py
    python tools/csp/render_ui.py --inspect-template

`GW_ROOT` chooses the workspace and its generated cache; otherwise the tool's
checkout is used. `GW_MELEE` chooses the separate game checkout containing
`pc/tools/png2gx.py`; otherwise `<workspace>/melee` is used. Set it when working
in a linked workspace whose game checkout is elsewhere. `GW_UI_PYTHON` chooses
the host Python used by the Workbench button; it needs Pillow, not bpy.

The fetcher uses a shallow sparse checkout of Resources and one character's
scene directory (Captain Falcon by default). A character directory can include
both poses and local texture dependencies. It records the fetched commit in
`_build/tools-ext/csp/tools.json` and reuses that cache without updating it.
Blender's Windows x64 zip is checked against its official 3.5.1 SHA256 list.
The external add-ons are installed into private cache scripts, passed with
`BLENDER_USER_SCRIPTS`. First fetch uses network; rendering never auto-fetches.

`--character` changes the template character. If scene selection is ambiguous,
`--scene` must give its exact tracked repository path, as listed in the error.
`--revision <commit hash>` pins a fetch. Module discovery fails clearly if
Resources does not expose `loom` and `render_button` as Python modules or
packages, directly or in zips. The extractor preflights paths and refuses escapes
and symlinks. Existing mutable subtrees are checked before git, extraction and
copying; directory links outside the cache or package are refused. Downloads
use fresh temporary files. Cached tools are reused for repeat renders.

## Rendering

Build the fighter package first, then:

    python tools/csp/render_ui.py --project ports/goku-xv2 --costume all --pose Wait:0
    python tools/csp/render_ui.py --project ports/goku-xv2 --costume 0 --pose dair:8

`--project` accepts a directory or workbench.json. Workspace-relative artifact
paths use the workspace root, matching the Workbench. The package defaults to
the parent of the project's files/plan.json. `--package` supplies the actual
built package; this is what the build hook uses. All output paths are resolved
and must stay below workspace `_build`, including symlink resolution.

`--fighter` supplies the artist fighter.json and its ordered costume inputs;
otherwise the project rebuild command's `--fighter` is used. Source GLBs and
costume textures in fighter.json are relative to that file. `--art` overrides
the original fighter's art. A .blend saved after Blender 3.5 uses its adjacent
GLB or the artist source GLB; portable Blender cannot read newer blend files.
A compatible blend appends its selected author Scene and Actions, linking the
collection hierarchy and root objects into the template without changing its
World or render settings. GLB import uses 60 fps.

Pose rows resolve from moves/<row>.json `pick.clip`, named clips in the built
plan, or zero-based plan.row_clips indices. Frame means an animation sample,
not an engine action-frame readout. Unknown clips and out-of-range action
frames fail. GLB track names and blend Action names are used without guessing
suffixes. The local inventory/log explains a missing action. A project
`ui_render.frame_offset` can account for a verified importer time offset.

Each selected costume runs a separate headless Blender process, with loom and
render_button enabled. The worker renders exactly nine selected cameras with
`bpy.ops.render.render`, keeping the template World, lighting and compositor.
It does not call an unverified upstream custom render operator. Host Python
then applies authored stock outline/CSP shadow equivalents and fits package
images without stretching. All nine raw camera PNGs, per-camera settings,
scene inventory, jobs and logs remain under `_build/csp-render/<key>/<run>/`.

## Package contract

| Field | Pixels | Encoding | Costume behavior |
|---|---|---|---|
| icon | 64 × 56 | RGB5A3 | One file from costume zero |
| portrait | 136 × 188 | RGB5A3 | Indexed list |
| stock | 24 × 24 | RGBA8 | Indexed list, no palette |
| results | 52 × 74 | RGB5A3 | Indexed list, no palette |
| emblem | 80 × 64 | RGBA8 | Optional authored PNG, no palette |

The first four fields are always produced. An emblem is not a fighter-camera
render: `--emblem original.png` or `ui_render.emblem` supplies an author's own
image. Without it, an existing emblem declaration is preserved. Never borrow
the CSProject character's series art for an original fighter.

Default field selection uses CSP_SD for portrait/results, Stock_SD for stock,
and CSS_SD if present or Stock_HD/SD for the select icon. Only CSP_HD/SD are
confirmed by the packet; the stock/CSS aliases are explicitly unverified.
Missing or ambiguous names fail and can be replaced through `ui_render.fields`.

Costumes follow the built package's `fighter.costumes` order. Alternate
costumes need distinct local textures, art files, selected objects/collections
or named material hex colors. Unspecified alternates fail instead of copying
costume zero. The source artist costumes must match the package count. For a
subset render, existing list indices stay intact; if no valid file for costume
zero exists for a field, zero is also rendered to repair that field only.
Existing zero art for other fields is retained; explicitly selecting zero or
all replaces all selected fields.
New images have ASCII basenames under 63 characters with a content hash.

Conversion calls game png2gx.py with an explicit format and
`--allow-odd-size`, then checks GXTX version, dimensions, format, tile payload
and absence of a palette. Files are staged inside the package, then published;
only after all conversions succeed is geno.json atomically replaced. A
conversion failure preserves existing files and declarations. Package changes
during rendering/conversion are rejected. A publication I/O failure can leave
unused new content-named files, but does not overwrite earlier art.

## Verified configuration overrides

Put `ui_render` in workbench.json, or point its `scene_config` at a JSON file
relative to the project. `--scene-config` overrides that scene configuration.
Use actual names from template-inventory.json for these supported keys:

- `ui_render.fields`: icon/portrait/stock/results to exact camera object names.
- `ui_render.pose`: default row:frame; absent means Wait:0 for original art.
- `ui_render.frame_offset`: integer animation sample offset, default zero.
- `ui_render.fighter`: workspace-relative artist config override.
- `ui_render.fighter_key`: select one define in a multi-fighter package.
- `ui_render.art`: workspace-relative original .blend/.glb override.
- `ui_render.emblem`: authored image relative to the project.
- `ui_render.costumes`: object keyed by zero-based indices. Each value accepts
  `art`, `texture`, `material_colors`, `objects`, `collections`. Art/texture
  paths are relative to the artist config, or project when there is no config.
- `ui_render.effects`: exact camera names to `outline` (0..32), `shadow`
  ([x,y] pixels or null), `shadow_alpha` (0..255). Set outline 0/shadow null
  to disable an effect already supplied by the template compositor.

Scene configuration accepts:

- `scene`: the template Scene datablock name (default sole Scene or "Scene").
- `camera_names`: explicit ordered list of nine camera objects, when there
  are additional cameras in the scene.
- `fighter_objects`: template fighter mesh/armature names. Without this,
  all template meshes/armatures are considered the donor.
- `keep_objects`: stage/light-card objects to preserve and exclude from bounds.
- `art_scene`: original .blend Scene name (default sole Scene or "Scene").
- `art_objects`: imported original objects to use when the source has scenery.
  `objects`/`collections` costume selectors also accept original names before
  Blender adds a numeric collision suffix; collection membership is retained.
- `fit_height`: target rest height; `yaw_degrees` and `offset` ([x,y,z]) adjust
  alignment. Default aligns floor and horizontal center by uniform height scale.
- `cameras`: object keyed by exact names, with `width`, `height`, and optional
  `crop` = [xmin,ymin,xmax,ymax], normalized bottom-left coordinates.
- `engine`: optional Blender 3.5 renderer override; default keeps the template.

Camera dimensions are read from resolution_x/y on camera object/data or their
loom property group when present, else the Scene resolution. Crop requires an
explicit override; automatic upstream camera-manager crop storage is unknown.
SD twins' authored relationships are retained, rather than recreated by name.
Read each camera_render_settings entry to detect the Scene fallback and verify
all nine camera aspects/crops before relying on the output.

## Retail scene option

    python tools/csp/render_ui.py --project tools/blender/geno_workbench/falcon/project --retail-scene "<local Falcon CSProject scene>" --costume 0

This requires a retail base or explicit define.template. It keeps the local
scene's own fighter and stored CSProject pose. An explicit `--pose` (including
Wait) applies a named Action on one selected donor armature; static template
poses may have no such Action and will fail. For all retail costumes, provide
object/collection visibility or material_colors from the character's local
hex-color documentation via ui_render.costumes, or a compatible local CSProject
.blend in each costume's `art`. The latter selects that whole retail Scene;
GLB art is rejected in retail mode. The text-file format itself
has not been assumed or parsed. Rendered retail data stays local and ignored.

## Build and Workbench hooks

    python ports/goku-xv2/tools/build.py --fighter _build/goku-xv2/author-source/fighter.json --ui

`--ui` is off by default, runs after gameplay audit and before full-build
static checks, and propagates a render failure. `--auto --ui` forces a full
build. `--gameplay-only --ui` is rejected. Later gameplay-only reapplications
preserve completed CSProject art rather than replacing it with legacy PNGs.

The separate **Geno > UI Art** panel provides **Render UI**. It starts host
Python and portable Blender 3.5.1; the interactive Workbench stays on Blender
4.x. It uses the selected move/frame, or Pose override, Project, and Art
override. No server connection is required for direct rendering. The status
shows the job log; polling keeps Blender responsive. Stop UI render and add-on
unregistration request cancellation through a generated file; the host stops
only its own Blender child. The panel does not rebuild the fighter package.

## Tests and first-run assumptions

    python -m pytest tools/csp/tests tools/blender/geno_workbench/tests ports/goku-xv2/tests -q

Pure tests use invented paths and Pillow images. The converter integration
skips without local game png2gx.py. The Blender integration skips unless the
local tools cache and exact Blender 3.5.1 exist; it creates invented rig/GLB and
.blend fixtures, including nested costume collections,
appends the real local template and checks nine renders and enabled add-ons.
A passing integration render is still not owner approval of the appearance.

The lead must verify: upstream repo/add-on archive names and download URLs;
the appended Scene's camera/light/parent/World/compositor dependencies; which
meshes are fighter versus stage/light cards; actual camera names and per-camera
resolution/crop storage; preserved SD/HD constraints; author collection visibility
and name collisions; coordinate orientation
and rest-height fitting; action names and GLB sample timing; directly linked
Principled atlas textures and material names for recolors; the template's
post effects versus this tool's authored outline/shadow; retail stored pose
and costume switching. Donor armatures remain as camera-driver targets,
while their meshes are hidden; inspect helpers that might remain visible.
File Output compositor nodes are redirected into the generated job directory.
The source contract has been read, but no Blender run or in-game check is claimed.

## Falcon: model-part visibility, visor alpha, culling (2026-10-10)

The glTF/DAT import draws every DObj, so a Melee fighter carries more than the game shows. The fighter's
own tables decide (`ftParts_8007487C`, `ftParts_800750C8`, `ftParts_80074B6C` in the decomp: the high-poly set
is shown, the low-poly LOD set and the metal-model parts hidden). `HsdExport --parts PlXx.dat PlXxNr.dat
parts.json` dumps them with the DObj layout, material alpha and cull flags; `falcon/part_visibility.py` picks the
hidden set (pure Python, `tests/test_part_visibility.py`); `make_falcon_art.py` bakes it into falcon.blend
(`geno_part_hidden`, hide_render/hide_viewport, Principled Alpha, backface culling). An existing blend:
`blender -b falcon.blend --python tools/blender/geno_workbench/falcon/apply_blend_parts.py -- parts.json out.blend`,
then `render_ui.py --art out.blend`. The own backend and the Workbench both read the baked flags; single-mesh
art (Goku) carries none and is unchanged (renders byte-identical).
Falcon: the low-poly set was drawn over the high-poly head/body, and the visor (DObj 22, XLU alpha 0.4)
came in opaque black, hiding the eyes. Joint 43's two DObjs (77, 78) are in the game's high-poly table;
the grey shoulder slab is DObj 77 and is NOT a visibility-state bug (see the lane report).
