# SSBM Nucleus: how it packages and installs mods, and what GD's Melee can load (2026-10-08)

Read-only study of the owner's local install of SSBM Nucleus 0.8.11 (by sc00p, MIT per its package.json), done while
waiting on sc00p about API access. Permission and terms: `_research/nucleus-modloader-2026-10-08.md` (link back to
Nucleus; no scraping or backend calls until an access method is agreed). Nothing was run, no network request was made,
none of its code was copied. The bundle contains credentials (an embedded backend anon key, Patreon OAuth, an updater
public key): they exist and are deliberately not recorded or used.

## What Nucleus is

An Electron app + a compiled local Python (Flask) backend + the .NET **MexManager CLI** (`mexcli`). It is a
**costume/stage vault manager that builds m-ex ISOs**, not a loose-file mod loader:

1. **Import** a mod into the vault (`%LOCALAPPDATA%\SSBM Nucleus\storage`, SQLite `vault.db` + `metadata.json`).
2. **Install** it into an **m-ex project** made from the user's vanilla NTSC 1.02 ISO (`mexcli create <iso>`; it checks
   the 1.02 MD5 and skips other discs).
3. **Export** a new ISO from the project (`mexcli export`, `wit`), or a Dolphin texture pack; or create/apply `.xdelta`
   patches against the user's vanilla ISO.

## Mod package format (there is no single one)

| kind (website `files[].kind`) | what it is |
|---|---|
| `character_dat` "Costume" | a costume `.dat`/`.usd` (+ CSP png, stock png), often a mexTool export zip; type detected by **content**, not name |
| `stage_dat` "Stage skin" | a stage file (+ screenshot); tournament stages via Dynamic Alternate Stages stubs |
| `xdelta` "Patch" | an xdelta3 patch against the vanilla ISO |
| (import types) | `.zip/.7z/.rar` (zips of zips), menu files (MnSlChr, MnSlMap, IfAll, GmPause), effect files (Ef*Data, PlFx, diffed vs vanilla), images (CSS doors, pause pics, glyphs), `.ssbm` "mod bundle" (format not documented locally), MexManager **fighter zips**, custom stage packages (`stage.yml`/`stage.json`) |

MexManager fighter zip: `fighter.json` + `Pl*.dat` + `Pl*AJ.dat` + effect bank + `sound.zip` (ssm) + costume zips.
`fighter.json` carries name, series, sound bank, announcer/music ids, trophies, bone lookup (~50 named bones), costumes
(file, jointSymbol, materialSymbol, CSP/icon), Kirby costumes, file paths/symbols, and **~60 callbacks as absolute PPC
addresses** into clone-base code.

Website post fields seen in the UI: `post_id` (unique id), title, author, images (media host), download/like counts,
`default_file_id`, variants, `files[{file_id, kind, character, colour, ...}]`, tags/category/creator, `effect_type`.
**No version, dependency, conflict, or game-compatibility fields; no checksums or signatures on mods.**

## What GD's Melee can do with each kind

GD loads mods as `mods/<id>/mod.json` + `files/` overlaid on disc paths (shim_dvd), m-ex data from the player's disc,
and Geno defines (`geno.json`). See `docs/mods-packaging.md`, `docs/mods-browser.md`, `melee/docs/geno.md`.

**Loads directly as a loose override (v1 scope):**
- **Costume DAT replacing a retail colour slot** (`PlXxYy.dat/.usd`): re-root under `mods/<id>/files/`. The importer must
  detect fighter + colour from the DAT's content (as Nucleus does) and pick the retail filename; joint/material symbols
  must match the slot. Costumes are excluded from the netplay identity hash, so a costume swap stays safe online.
- **Stage skins** for the tournament stages (`GrNBa`, `GrNLa`, `GrSt`, `GrOp`, `GrPs`, `GrIz`) replacing the retail file.
- Effect files, menu replacements, audio (`.hps`/`.ssm`): plain disc files; menu files are global and conflict.

**Needs conversion (later):**
- **Extra costumes beyond the retail slots:** Nucleus appends via m-ex costume tables; GD needs a Geno/define costume
  entry or a rebuilt costume list.
- **MexManager fighter zips:** split files into `mods/<id>/files/` and translate `fighter.json`. The PPC callback block
  only works on GD's interpreted m-ex path with a matching base, so the realistic route is GD's existing "filtered base"
  m-ex model, not a pure Geno define, unless the fighter is re-authored for Geno (as Sora was in slice 8).
- **Custom stages:** GrXx.dat + SSS icon + MxDt stage rows; same base-pack restriction.
- **`.xdelta`:** a patch against the vanilla ISO, not a mod unit; usable only by patching the player's own ISO and
  diffing it into a mod locally (never redistributed). **`.ssbm`:** format unknown; do not attempt without it.

**Cannot work:** Gecko codes / DOL patches / m-ex core in `main.dol`, PPC function pointers without the code they point
into, Dolphin texture-pack mode, whole-ISO builds.

## A generalized "load from a Nucleus package" adapter (plan)

1. Importer: sniff archive type (zip/7z/rar) and DAT content; classify fighter+colour / stage; choose the target filename.
2. Unpack into `mods/<id>/files/` with a generated `mod.json` (id from `nucleus-<post_id>`, name, authors, kind,
   `source: nucleus`, link `https://ssbmnucleus.net/post/<post_id>`, sha256 + size computed by us, since Nucleus has none).
3. Conflicts (Nucleus has no system): reuse GD's mod set resolution: two mods for one colour slot, menu files, a second
   m-ex base.
4. Netplay: costume/stage-skin overrides follow the existing identity rules (costumes excluded; stage files hashed).
5. Credit: every Nucleus mod shows "from SSBM Nucleus" with its post link (the permission's condition).
6. Catalogue: there is nothing local to read; it depends on sc00p exposing an index (ideally a `gdmelee-mods.json`-style
   list with post_id, files, kind, character, colour, download URL, size) or an agreed API. Do not use the bundled
   backend key or the assistant routes.

**Recommended v1:** costume DATs and tournament-stage skins (`character_dat`, `stage_dat`) as loose overrides, imported
from files the player already downloaded with Nucleus (its vault on disk) or from a URL sc00p's API provides; defer
fighters, custom stages, xdelta and bundles.

## Questions for sc00p (when the API is discussed)

- An index endpoint: fields for files (kind, character, colour slot, size, hash), stable download URLs, rate limits, auth.
- Whether mods can carry compatibility (vanilla 1.02 / m-ex base / Slippi-safe) and a version.
- The `.ssbm` bundle format, if bundles should be supported.
- Preferred attribution wording and link format.
