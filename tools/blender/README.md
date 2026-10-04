# Melee Break-the-Targets — Blender editor add-on

A Blender 4.x add-on that lets you author *Super Smash Bros. Melee* **Break the
Targets** levels in Blender and round-trip them to/from the native PC port's
`mods/targettest/<name>.tt` level format, so Blender is the level editor.

Files:

- `melee_target_test_io.py` — the add-on. The parse/serialize and coordinate
  layer is pure (no `bpy`), so it is importable outside Blender.
- `test_roundtrip.py` — standalone round-trip test, runnable with plain python3.

## Install

1. `Blender > Edit > Preferences > Add-ons`.
2. Click **Install…** and select `melee_target_test_io.py`.
3. Enable **Import-Export: Melee Break-the-Targets (.tt) I/O**.

## Usage

### Authoring a level

- **Targets** are empties. Name them `target.*`, place them in a collection
  named `targets`, or give them a custom property `melee_role = "target"`.
  Their world location becomes `target x y z`.
- **Platforms** are mesh cubes. Name them `platform.*` or give them a custom
  property `melee_role = "platform"`. Their world location and X/Y extents
  become `platform cx cy cz w d`.
- **Level identity** lives in the scene, shown in the **View3D sidebar →
  Melee TT** panel (also on the Scene properties):
  - `Character` — `ckind` integer or a name like `mario`/`fox`/`zelda`
    (default `mario`). Resolved case-insensitively, identically to the port
    loader.
  - `Level Name` — falls back to the scene name when empty.

### Export / Import

- **File > Export > Melee Break-the-Targets (.tt)** — writes the current scene.
- **File > Import > Melee Break-the-Targets (.tt)** — creates `target.<i>`
  empties and `platform.<i>` cubes. Imported objects carry `melee_role`, so a
  re-export is lossless.

## Coordinate convention

Blender is Z-up; Melee is Y-up (X right, Y up, Z depth). A single mapping is
applied symmetrically on export and import, so a round trip is the identity:

```
melee_x =  blender_x
melee_y =  blender_z     # Blender up  -> Melee up
melee_z = -blender_y     # Blender back -> Melee depth, negated

blender_x =  melee_x
blender_y = -melee_z
blender_z =  melee_y
```

## Platform geometry

A `.tt` `platform` is a horizontal platform whose collision is **2D XY**:

- `cx`, `cz` — platform center.
- `cy` — the **top surface** (the walkable line); on export it is the cube's
  center plus half its vertical extent, on import the cube's center sits half a
  thickness below `cy`.
- `w` — full X extent (`Blender dimensions.x`).
- `d` — full Z-depth extent (`Blender dimensions.y`; display-only in the port).
- The vertical thickness is **not stored**; imported platforms get a default
  `DEFAULT_PLATFORM_THICKNESS = 2.0` (Melee units).

Keep platform cubes **axis-aligned** (no rotation) so the world-space extents
match the object's local extents exactly.

## `.tt` format reference

Line-based text, `#` comments, UTF-8, LF newlines. Blank lines and comments are
ignored; unknown keys are ignored by the loader.

```
# optional comments
name <free text>
character <ckind integer OR name>   # e.g. 8 or mario
target <x> <y> <z>                  # one per target, up to 21
platform <cx> <cy> <cz> <w> <d>     # top surface at cy; X extent w; Z extent d
```

Coordinates are Melee stage units (X right, Y up, Z depth). Integer `character`
values are decimal. A level with no resolvable character or no targets is
skipped by the port loader.

## Test

Run the pure-format round-trip test outside Blender:

```sh
python3 tools/blender/test_roundtrip.py
```

## Mission exporter

`gd_mission/` is a separate Blender add-on for exporting a level and its mission
as one folder. Zip the **gd_mission directory itself**, keeping `gd_mission/__init__.py`
at the zip's root directory. In Blender use **Edit > Preferences > Add-ons >
Install from Disk**, choose that zip and enable **GD Mission exporter**. Alternatively
copy `gd_mission/` to Blender's user `scripts/addons/` directory. Open the 3D View
sidebar with N and select **GD Mission**. Set mission name, output mod folder and
kit models folder; use **Validate**, **Export**, or **Export and send**. Mission and
chunk names use 1–48 ASCII letters, numbers, underscores or hyphens (the engine's
model basename limit).

The checkout's suggested kit directory is `menu/out_roguelite/room-kit/`.
When installed elsewhere, select your exported kit's models directory explicitly.
The add-on copies kit assets; it does not rebuild them. To use the new wall/ceiling
collision, first re-export the kit with `melee/pc/assets_src/bf_interior/export_kit.py`
into a directory of your choosing. That script's normal main command also updates
an editor Lua catalogue: set `--editor` to a disposable copy when preparing assets
without modifying the map editor. No kit assets or example folders were regenerated
by this packet; the automated tests write to temporary directories.

### Scene conventions

Blender is Z-up in metres. Positions are absolute and map to game units as:

```text
game x =  6.5 * Blender X
game y =  6.5 * Blender Z
game z = -6.5 * Blender Y       (visual depth; +Z points toward the camera)
(2, 3, 4) metres -> (13, 26, -19.5) game units
```

The layout always has `units=6.5` (kit `UNIT = 5 * KIT_SCALE`, `KIT_SCALE=1.3`).
Rotation is degrees from `atan2(world local-X.z, world local-X.x)`. Rotation about
Blender Y by -15 degrees exports `rot=15`. Scale axes map Blender X/Z/Y to game
`scale_x/scale_y/scale_z`. Translation, rotation and scale use the world matrix,
including parent transforms. Shear and transforms leaving the game plane are refused.
Floor origins are at the centre of the top collision line; starts are feet positions.
All Lua numbers are rounded to four decimal places.

- **Kit mesh instances:** set custom property `gd_part="bf_floor_4m"` (the spike's
  `kit_part` is also accepted), or name the object `bf_floor_4m`, `bf_floor_4m.001`,
  etc. The part is the exported kit filename stem. `collision` defaults to true;
  `floor_flags` defaults to 3, or 1 for ramps/stairs. Library objects named `KIT_...`
  and objects with `gd_ignore=true` are ignored.
- **Other meshes:** evaluated local geometry (including modifiers), corner normals
  and active UVs export as GXMS v2, with `mesh_<43 hex digits of SHA-256>` names
  based on geometry and collision. Placement does not change the hash. Custom
  meshes use a shared white `gd_neutral.gxtex`; material baking is outside this
  exporter. For custom collision, `gd_collision_lines` is a JSON string such as
  `[["floor",-2,0,2,0,3]]`. Coordinates are local X/Z metres, flags are native
  floor flags. Collision is explicit; mesh faces do not generate collision.
- **Solid ceilings:** default floors, balconies and opening floors are one-way
  platforms with **no underside ceiling**. Set `gd_solid=true` on an individual
  `bf_floor_4m`, `bf_floor_2m`, `bf_balcony_4m` or `bf_floor_opening_4m` mesh instance
  to export a separate hashed variant. It clears top-floor pass-through flags and
  adds right-to-left ceiling lines at local Z=-.4m (game Y=-2.6), preserving the
  opening floor's centre gap. The default mesh/sidecar remains unchanged. The
  property must be boolean and requires `collision=true`; other kit/custom meshes
  are refused. Custom meshes author their ceiling explicitly in `gd_collision_lines`.
- **Mission markers:** empties with `gd_marker` equal to `start`, `enemy`,
  `checkpoint`, `goal`, `trigger` or `wave`. There is one start and one goal.
  An enemy also has `kind` and `wave` (default 1). Set the scene custom property
  `gd_objective` to `reach_goal`, `defeat_all` or `defeat_then_goal`; optional
  `gd_time` is seconds and `gd_lives` is an integer. `objective` is accepted as
  a scene property alias for the spike.
- **Zones:** goal/checkpoint/trigger empties use world scale as half extents:
  width = `2 * abs(world X scale) * 6.5`, height = `2 * abs(world Z scale) * 6.5`.
  Empty display size does not affect export. Keep rectangles axis aligned in XZ.
  Trigger `action` is `wave` (plus `wave`), `message` (plus `text`), `collision`
  (plus `target`, the name of a part object, `radius` in metres, `open` boolean),
  `complete` or `fail`. Set `once=false` for repeated entry. Messages must contain
  1–80 printable UTF-8 bytes; a collision radius cannot exceed 200 game units.
- **Wave rules:** `gd_marker="wave"`, integer `wave`, and either `time` in seconds
  or its X position (with `dir=1` or `-1`). A rule/trigger must name a wave with enemies.
- **Bounds:** empty rectangles or mesh planes tagged `gd_bounds="camera"` or
  `"blast"`; one of each. Mesh planes must be axis aligned in world XZ. Bounds
  are exported as `{left,right,top,bottom}`. Markers, including full zone extents,
  must fit within camera bounds, or blast bounds if camera bounds are absent.
- **Chunks:** empty rectangles or mesh planes tagged `gd_chunk="id"`. Parts go
  into the rectangle containing their origin, using half-open intervals
  `[left,right) × [bottom,top)`, so a shared edge belongs to only one chunk.
  Every part origin must lie in a chunk when chunks exist; interiors cannot overlap.
  The runtime requires equal-size rectangles aligned to one grid, at most 4096;
  validation checks the actual four-place rectangle values written to Lua.
  Without explicit camera/blast bounds, the chunk envelope defines marker bounds.
  Every chunk gets a spawn: first contained checkpoint, then contained mission
  start, then a floor origin plus one metre, otherwise rectangle centre. Author a
  checkpoint in each chunk for a deliberate rebirth position; inspect fallbacks
  in the game. Chunk geometry and spawns retain **absolute game coordinates**.

### Folder format and writing

```text
<output mod>/missions/<name>/
  level.lua                return {version=2, units=6.5, parts=..., camera=..., blast=...}
  mission.lua              return {start=..., enemies=..., objective=..., ...}
  models/                  used kit/custom meshes, collision sidecars, shared atlases
  chunks/<id>/             present only when chunk rectangles exist
    level.lua              version=2, units=6.5, parts in absolute coordinates
    models/                internal directory reference to the root models pool
```

For chunks the root `parts` is empty and root `chunks` contains
`{id="a",rect={left=...,right=...,top=...,bottom=...},spawn={x=...,y=...}}`.
The runtime resolves each id to `chunks/<id>/`. Root models contain all used
meshes and **one copy of each shared colour/glow atlas per mission**, including
assets needed only by chunks. Every chunk's `models/` references the same root
pool; its layout still selects only that chunk's parts. The root mission retains
every marker. Final resolved paths stay inside the mission folder.

The current engine accepts atlas basenames only and resolves them beside each
mesh. The exporter therefore creates relative directory symlinks (`../../models`)
where supported, or an NTFS directory junction on Windows without symlink
privilege. No extra privileges or engine changes are required. Directory references
make the engine resolve every shared atlas and mesh to the same canonical path.
Use copying/archiving tools that preserve directory symlinks. The NTFS junction
fallback contains an absolute path: after moving/copying such a mission, **re-export
at the destination to recreate its references**. An ordinary zip that follows
links into duplicate folders loses this sharing; do not assume it preserves the
asset-memory benefit. The offline tests verify symlink relocation and the actual
Windows junction fallback; native game loading remains an integrator check.

Models are written first, chunk Lua next, root `level.lua` and `mission.lua` last.
Files with changed content are written to `.tmp`, flushed, then renamed. SHA-256
comparison preserves files with unchanged content and their modification times.
Completed generations reuse unchanged files through hardlinks (copy-with-preserved-
timestamps fallback); linked immutable files are replaced rather than truncated.
Thus marker/placement edits do not generate new atlas versions in the engine cache.
A whole generation is staged
in a sibling directory before publication. For an existing mission Windows needs
two directory renames: move old generation aside, publish new, restore old on a
publication failure. A reader may briefly see a missing folder and must retain
its previous level/retry. This prevents partial files but is **not a transactional
snapshot for a reader that already opened the previous generation**. Only root
Lua files and the completed folder are published after every asset is ready.

Validation refuses more than 128 parts without chunks (or 128 per chunk), more
than 64 collision lines or 65,535 indices/vertices per mesh, collision-owning
mirrors, invalid plane transforms/scales, overlapping or malformed chunks,
markers outside bounds, unknown enemy kinds and incomplete objectives. Enemy
kinds are goomba, koopa, redead, like_like, octorok, polar_bear and topi. Runtime
wave, zone, enemy, trigger, time and lives limits are also checked. Budget values
live in `gd_mission/constants.py`. Diagnostics identify source objects. A large
unchunked assembly is refused; automatic section merging is not implemented.

Validate reports estimated pinned asset memory for **one current generation with
all chunks loaded**: each unique canonical mesh blob once plus the GXTX image
byte counts of each colour/glow texture once. It warns at 80% of the 64 MiB budget
and refuses a current generation exceeding it. Sidecar text is not native pinned
image/mesh memory. The estimate cannot see previous scene-pinned revisions or
other mods, so it is a lower bound on a running scene's total. Changed custom
geometry still pins a new mesh revision until scene reset; unchanged atlas
timestamps prevent an 11.2 MiB colour/glow repin on every export.

### Instance names and camera authoring

Every placed part carries its Blender object name in `name`, including parts in
chunk level files. Non-ASCII characters and punctuation become underscores;
names are capped at 48 ASCII characters. Collisions after sanitizing/truncating
receive `_1`, `_2`, etc., with room reserved for the suffix. Names are unique
across the whole mission and remain deterministic for the same scene. Renaming
an object changes its trace label without changing its model content hash.

The sidebar's **Level camera** fields edit scene custom properties. Selecting a
`gd_chunk` rectangle also exposes **Selected chunk camera override** fields.
**Add camera fields** creates editable values; **Use runtime defaults** removes
that scope's settings. There are no settings added merely by registering the
add-on. The underlying custom properties are:

| Property | Exported field | Allowed values |
|---|---|---|
| `gd_camera_mode` | `camera.mode` | `follow`, `chunk`, `shaft` |
| `gd_camera_window_w`, `gd_camera_window_h` | `camera.window.w`, `.h` | both required when either is set; 1..49000 game units |
| `gd_camera_min_dist` | `camera.min_dist` | 1..49000 game units |
| `gd_camera_fov` | `camera.fov` | 1..89 degrees |

These values use game units directly, not Blender metres. Unset fields are
omitted so runtime defaults/inheritance can apply. A chunk's authored settings
are written into its own `level.lua`; level settings stay in the root file.
Existing camera bounds remain in the same table as `left/right/top/bottom`.
If settings are authored without an explicit camera rectangle, the level's
validated bounds (blast bounds or chunk envelope) supply those legacy fields;
a configured chunk includes its own rectangle. With no settings, the exporter
adds no new camera configuration and preserves existing bounds behavior.

The present runtime validator accepts the bounds and instance labels but does
not yet retain the new mode/window/zoom/FOV fields. Camera behavior needs the
integrator's runtime support and native calibration from design section 8.

### Side-view collision and doors

The 2026-10-03 mission-verify runs supersede the earlier guessed wall semantics.
A **solid block's left face** is `left_wall` bottom-to-top and stops a fighter
approaching from the left; its **right face** is `right_wall` top-to-bottom and
stops approach from the right. A room's left interior edge is the right face of
its left wall; room-edge names must not be substituted for block-face names.
Floors go left-to-right and ceilings right-to-left.

`Wall_Doorway_4m` and `Wall_Window_4m` are decorative background bays with **no
collision in the X travel plane**, including no outer/jamb walls or sill floors.
Their 3D openings do not define side-view routes: the door's clear height is
2.6m = 16.9 game units and the window's is 2m = 13 units. No low lintel ceiling
is emitted. The large-levels note recommends 45 units (45/6.5 = 6.9231m) minimum
door clearance; use that conservative authoring policy for separately authored
solid lintels, and verify clearance against the selected fighter's live ECB and
animations. No per-fighter height table was present in the supplied level notes;
the game CPU code's nominal 20-unit box is not a verified per-character height.

For a door that blocks until opened, place a **separate blocker mesh marker**
named `Door_Blocker`, using `gd_part="bf_wall_solid_4m"`, collision enabled and
position/scale sized for the intended barrier. Keep the decorative doorway separate.
Alternatively use a custom blocker mesh with explicitly authored block-face lines.
An ordinary existing collision trigger can target `Door_Blocker` with `open=true`
and a suitable radius; a game-side door controller can own that blocker. This
exporter adds no key, kill, animation or door-controller logic and does not introduce
a new `gd_marker` enum. The blocker is a part object, so the existing part-target
collision mechanism can address it.

**Export and send** sends `mission reload` to localhost on `MELEE_CONSOLE_PORT`,
reads the banner and replies through `>>> ok` or `>>> error`, and reports connection
failure without starting a process. Start Blender with that environment variable
set and select the mission in the game with `mission play <name>` once. Sending
reload does not select a different mission. A failed send leaves the completed
export on disk.

### Offline checks

```sh
python -B -m unittest tools/blender/test_gd_mission.py
```

Pure data tests use ordinary Python and the Lua executable on PATH. Blender tests
run through a helper in the same test file, skip when the configured executable
is absent, create their scene/outputs in temporary directories and never launch
the game. They check scene export, custom hashes, add-on registration, the concurrent
mission runtime's Lua folder loader when available, and actual kit geometry/sidecar
re-export with original floor records preserved. The unchanged atlas bake is not
rerun. Runtime winding/contact, visual rendering, chunk seam traversal, rebirth
positions and live reload must still be checked in the game by the integrator.
# Maze exit markers (2026-10-03)

Maze chunks use the fix3 default **130x104 game units** (20x16 metres).
Add an empty with `gd_exit=left|right|up|down`, `gd_exit_slot=1`,
`gd_exit_chunk=<chunk id>` and `gd_exit_traversal=walk|climb|drop`.
Standard slot centres relative to the chunk's lower-left are left(0,16),
right(130,16), up(65,104), down(65,0). Divide game X/Y by6.5 for Blender X/Z.
Walk applies to side doors; down drops; up climbs or receives a one-way drop.
Collection and Validate reject off-slot markers, duplicates and other sizes or
slot indices. Export writes `size` and `exits` in each chunk level.
The maze library's platform certificate must match the lower chunk's physical
floor spans before an ascent is accepted. See `tools/maze/README.md` for the data
library, preparation, generation and native acceptance limits.
