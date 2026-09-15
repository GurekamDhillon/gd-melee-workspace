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
