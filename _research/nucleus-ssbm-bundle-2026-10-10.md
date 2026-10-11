# SSBM Nucleus `.ssbm` "mod bundle": what the local install shows (2026-10-10)

Read-only study of the owner's local SSBM Nucleus 0.8.11 (by sc00p, MIT per its package.json; permission and
terms in `_research/nucleus-modloader-2026-10-08.md`). Follow-up to `_research/nucleus-mod-format-2026-10-08.md`,
which listed `.ssbm` as "format unknown". Nothing was run or launched, no network request, no backend call, nothing
inside the install or vault was modified, no Nucleus code copied. Credentials seen in the bundle exist and were
neither recorded nor used.

## What was looked at

- `%LOCALAPPDATA%\Programs\SSBM Nucleus\resources\app.asar` (Electron app): a COPY was unpacked in the scratchpad and
  the frontend JS (StorageViewer, MexPanel pages) and `electron/` were searched for `.ssbm`, `bundle`, manifest names.
- `resources\backend\mex_backend.exe`: a PyInstaller one-file executable (Python 3.12 era, cookie version 312). Only its
  archive table of contents was read. The Flask application code is inside the compressed PYZ; opening that was
  not done (see "Still unknown"), so the backend's bundle reader/writer was NOT read.
- The vault (`%LOCALAPPDATA%\SSBM Nucleus\storage`): `bundles/` exists and is EMPTY; `metadata.json` has only the
  keys `characters` and `stages`. Searched the vault, install, Downloads and Documents (and the profile to depth 6)
  for `*.ssbm`: **no `.ssbm` sample file exists on this machine.**

## Verdict on the container: not confirmed from a sample

There is no sample and the backend code was not read, so the byte-level container (magic, archive type,
compression) is **unknown**. What the UI proves is below. Do not write an importer from guesses.

## What the app code proves about a bundle

1. **It is not a costume or stage package.** Bundles live in the vault under *Patches -> Bundles* next to xdelta
   patches. The import dialog is titled "Import Patch or Bundle", file picker `.xdelta,.ssbm`, caption
   "Supports .xdelta patches and .ssbm mod bundles".
2. **How one is made** (MexPanel export flow, three steps): export the user's m-ex project to an ISO, build an
   xdelta patch of that ISO against the vanilla 1.02 ISO, and (optionally) package an auto-built Dolphin HD
   texture pack ("HD portraits"). The export request carries: `name`, `description`, `buildName`,
   `vanillaIsoPath`, `exportedIsoPath`, optional `texturePackPath`. So a bundle is essentially
   **"xdelta patch of a whole built ISO + metadata + optional HD portrait textures"**, i.e. a way to share a full
   m-ex build, not individual disc files.
3. **Routes (frontend -> local backend):** `/bundle/preview` (multipart `file`), `/bundle/import` (multipart `file`),
   `/bundle/list`, `/bundle/install/<id>` (builds an ISO from the stored bundle: "Install on the bundle to build"),
   `/bundle/update/<id>`, `/bundle/update-image/<id>` (cover), `/bundle/delete/<id>`, `/bundle/export`
   (multipart: name, description, buildName, vanillaIsoPath, exportedIsoPath, texturePackPath).
   Progress events: `bundle_import_progress|complete|error`, `bundle_export_progress|complete|error` (keyed by
   `import_id` / `export_id`).
4. **Manifest fields the preview UI reads** (names only): top-level `manifest` with `name`, `description`,
   `created` (a date string); top-level `texture_count`. The list rows read `id`, `name`, `size_mb` (or `size`),
   `texture_count`, `imageUrl`. Export result: `size_mb`, `texture_count`, `path`, `warnings`. The word
   "manifest" being a nested object suggests a manifest file inside the container, but its filename is not visible
   in the frontend.
5. **What is NOT recorded as far as the UI shows:** no per-file kind/target table (costume vs stage), no hashes,
   no version/compat fields, no encryption or signature mention anywhere in the bundle UI or flow. These may still exist
   inside the container; the UI simply does not surface them.

## Implication for GD's Melee

Even if the container turns out to be a plain archive (zip is likely but unverified), its payload is an
**xdelta against the vanilla NTSC 1.02 ISO** (plus HD portrait textures). That is not a list of loose
costume/stage files, so:

- There is no per-file "kind/target" to map onto `mods/<id>/files/`. A bundle cannot be unpacked into loose
  overrides; the payload only means something applied to the player's own vanilla ISO (patch output is a whole
  m-ex ISO built on Nucleus's m-ex base). That is the "whole-ISO builds" class already ruled out in
  `nucleus-mod-format-2026-10-08.md` ("Cannot work"). A user-local "apply xdelta to my ISO, then diff into a mod"
  route exists in principle but is out of scope and must never redistribute disc data.
- **Recommendation: do not build a `.ssbm` importer for v1. Keep deferring it.** It does not serve the
  costume/stage-skin goal; the useful Nucleus content (`character_dat`, `stage_dat`) arrives as plain `.zip/.7z/.dat`
  files, which our zip-reading C code and DAT sniffing already cover.

## If a bundle importer is ever wanted (steps, contingent on verification)

1. Obtain a real `.ssbm` (export one yourself from Nucleus on a throwaway project, or ask sc00p for the format;
   it was already on the question list). Open a COPY and check the first 4 bytes: `PK\x03\x04` = zip.
2. If zip with stored/deflate entries only: our central-directory reader suffices. List entries; read the manifest
   entry (name to be confirmed) as JSON for `name`, `description`, `created`; the patch entry is an xdelta3 stream
   (VCDIFF magic `D6 C3 C4`); texture entries are PNG/DDS under some folder.
3. If it uses 7z, zstd or any compression other than stored/deflate, or is encrypted, a C reader is not
   available; do the unpacking in the launcher (Python or C#), not in the game.
4. Importer output would be: manifest metadata, a path to the patch, a texture-pack folder. Applying the patch
   requires the player's vanilla ISO and xdelta3; never ship or commit the result.
5. Attribution: show "from SSBM Nucleus" with a link (the permission's condition).

## Still unknown (exactly)

- The container type, magic bytes, compression, and any encryption of a `.ssbm`.
- The manifest's filename and full field list, whether it has a version/format field or hashes.
- How the texture entries are named, and how the xdelta is named inside.
- The backend's reader/writer was not inspected: PYZ decompression of the PyInstaller backend was deliberately not
  pursued (the tool environment declined it as a credential-leak risk, since that code embeds secrets).

## Cheapest way to settle it

Create a test bundle with Nucleus itself on the owner's machine (Export -> Bundle) and inspect that single file
with `file`/a zip lister; that needs no backend analysis and no secrets handling. Or ask sc00p for a one-paragraph
format description.
