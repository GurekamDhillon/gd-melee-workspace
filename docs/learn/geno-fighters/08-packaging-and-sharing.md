# Packet 8: Packaging and sharing (outline)

**Status: unrun outline (notice dated 2026-10-10).** This packet has not been
executed as a walkthrough; source/document references are not gameplay or GUI
verification. Start with [Author a fighter](../author-a-fighter.md) for the current
artist-to-Blender-to-LAB path.

The package checker exists. There is no general packer for an artist-built
fighter; the source-only define exporter has narrower payload limits.

**Goal:** turn your overlay or fighter into a folder someone else can use, without including anything
you may not share.

**Prerequisites:** packets 1 and 3.

## The folder

```
mods/<id>/                 the folder name is the id (lower case, no spaces is safest)
  mod.json                 metadata
  geno.json                your Geno profile(s)
  geno/                    word files your overlays name ("file": "geno/x.txt")
  fx/                      effect packages and fx_bindings.json (packet 5)
  files/                   only for files that answer disc paths (see below)
  scripts/                 Lua scripts, if your mod has any
```

`mod.json` fields, all optional (`docs/mods-packaging.md` section 4): `id`, `name`, `version`,
`kind` (`base`, `fighter`, `stage`, `misc`, or `script`; anything else becomes `misc`), `pack`,
`description`, `requires` and `conflicts` (lists of ids), `hash`, and `engine` (a map of engine
features the mod needs; the only one this build knows is `pobj_palette`). A mod whose `requires` are
not mounting is dropped, and two `base` mods always conflict. The Lua-side fields (`api_version`,
`gameplay`, `rollback_safe`, `entry`, `author`) are read by the scripting layer, not the mod loader
(`_research/vanilla-single-folder-mods-2026-10-03.md` section 1.1).

Without a `files/` folder the whole mod folder is the payload ("legacy layout"): `mod.json` and
`scripts/` are skipped, and everything else, `geno.json` included, is also mounted as a disc path.
That is harmless but adds noise to the netplay mod fingerprint (same note). Players enable mods by
the launcher's Mods tab or by `mods/enabled.txt`; a change applies at the next start.

To share it: zip the folder. The launcher lists local mods and toggles them but has no install
step: the recipient unzips it into `mods/` (`docs/mods-browser.md`, top).

## What must not be in it

- **No disc-derived data, ever.** That includes any file copied from a disc: `MxDt.dat`, `PlCo.dat`,
  menu archives (`MnSlChr.usd`, `IfAll.usd`), any `Pl*.dat` you copied from a disc and edited, models
  and animations of Nintendo games (`CLAUDE.md`, Conventions).
- **No assets from another game** unless you own the right to ship them. The Ultimate and Brawl ports
  here are built locally from the builder's own copies, and only tools and research are published
  (`ports/README.md`).
- **No private paths, tokens or disc locations** in `mod.json` or the descriptions.

### The honest consequence

An overlay containing only authored configuration, word files and original art
can be shared. A table-based added fighter carrying extracted host/table bytes
from a disc cannot. That older limit does not apply to every native define:
the artist pipeline builds a `base: "none"` model/bank/plan from original art
without reading a disc. Share only resources you have the right to distribute.

Run `python -m tools.geno.check path/to/package` on the actual folder you intend
to share, then test a clean install. A passing checker is not a provenance proof.
`python -m tools.geno.export --package SOURCE --out DEST` exists for source-only
defines, but its current archive guard rejects `.dat` files, including original
artist-built models/banks; it is not a packer for the full artist output.
Use a reviewed folder/zip for original artist output, or distribute tools/configs
for locally built source-game ports.

## Credit

The project credits everything it learns from, "whether or not a licence requires it, and that
includes ideas and findings as well as code" (`CREDITS.md`). Do the same: say in your mod's
description or a `CREDITS` file which game, tool or person your numbers and ideas came from. m-ex
publishes no licence: consult it, do not copy it (`tools/mex_port/README.md`, "Attribution requirement").

## Compatibility and online play

- **Vanilla and mod discs.** An overlay that attaches to a retail fighter needs no m-ex tables and
  has been run on a vanilla disc for attributes and a hook (the research note's RUNS case 5). An
  overlay that attaches to an m-ex fighter by its file name needs that fighter to exist on the
  install (`geno: ... which this install does not have - inactive`).
- **Mixing.** Fighter and stage mods from different packs cannot be mixed; at most one base mounts
  (`docs/mods-packaging.md` section 8; README "Known issues").
- **Netplay.** Your overlay's id is mixed into the *target fighter's* identity. Two players with
  different overlays for Kirby see Kirby greyed out for each other, as with two different Kirby mods
  (`melee/docs/geno.md` section 3, point 5). Nothing refuses the connection. Both players need the
  same version of your mod to play it.
- **Rollback.** Do not rely on host state. Geno's state is saved with savestates, so a correct
  overlay is safe by construction (section 4).

## Check before you share

1. The folder contains no file you copied from a disc. Compare file names with what you wrote.
2. `mod.json` has a unique `id` equal to the folder name, a version, and honest `requires`.
3. The package checker passes, and the log shows no unresolved `geno:` warnings
   for your fighter (packet 7).
4. A person with a different, clean install can run it. Test by moving the folder to a fresh mods
   folder (not run by the author).
5. A credits note names your sources.

## Sources

- `docs/mods-packaging.md` sections 1, 2, 4, 6, 8; `docs/mods-browser.md` (the Mods tab).
- `_research/vanilla-single-folder-mods-2026-10-03.md` sections 0, 1.1, 1.5, 2, 4.
- `melee/docs/geno.md` sections 3, 4, 7. `CLAUDE.md` (Conventions); `CREDITS.md`;
  `tools/mex_port/README.md`; `ports/README.md`; `README.md` (Known issues).
