# Nucleus: what is not a loose override, and what each would take (2026-10-10)

Companion to `nucleus-mod-format-2026-10-08.md`. Written by the nucstages lane (R4). Facts about Nucleus are from its public API (`_research/nucleus-public-api-2026-10-08.md`) and from
five real API reads on 2026-10-10 (field shapes only); estimates are engineering guesses, not measured.

## What the in-game browser installs now (loose overrides)

Costumes (new skin slots, see below), stage skins for the retail versus stages, `Ef*Data.dat` effect files, the menu files `MnSlChr` / `MnSlMap` / `IfAll` / `GmPause`, and `.hps` / `.ssm` audio.
Every file is checked by content against the player's own copy of the file it replaces. Real shapes seen: stage posts carry `file_type: stage_dat` with names like `Pumpkin Hill - GrOp.dat` and a
`stage` field; most `effects` posts are NOT effect files but whole fighter files (`PlMs White Streak Color.dat`, `PlFc.dat`, 156 of 163 files in the first 100) and are refused ("ships a whole
fighter file"); `other` posts are menus (`MnSlChr.usd`, `IfAll.dat`, `GmRst.dat` ...), images, patches.

## Extra costume slots: not a gap

A Nucleus costume installs as a `kind: "skin"` mod that appends a NEW costume (index = the fighter's own count + its position; the port allows 255 per fighter, `docs/mods-packaging.md`
section 4b). `like` only picks which retail costume's part visibility it copies; nothing is replaced. So "extra costume slots" is not an unsupported reason anywhere in the browser.

## Custom stages (`custom_stage` posts, m-ex stage packages)

Needs: a stage DAT `GrXx.dat` the game can load (a new `StageData` row: file name, internal id, callbacks), a stage-select icon and name art in `MnSlMap`, rows in the m-ex tables (MxDt `Arch_Map`
/ `stage_desc`), music id, and its m-ex function blob (PPC) which only runs on the interpreted m-ex path. GD already mounts "one stage per mod + a filtered base" (`docs/mods-packaging.md` 2.3,
section 5 split tool). Route: Nucleus custom-stage package (`stage.yml` / `stage.json` + `GrXx.dat` + icons) to `mods/<id>/` of kind `stage` that `requires` an m-ex base, plus the base's MxDt must
have a free SSS slot. Effort: ~3-4 days for the importer (package parse, icon conversion, stage row writer) AND it only works on a disc that already runs m-ex (needs the "boot a patched disc"
path below, or the ACE/Akaneia base). Without an m-ex base it cannot work at all. Unverified: how many Nucleus custom stages are plain `GrXx.dat` + icon vs. carry code.

## MexManager fighter zips

`fighter.json` + `Pl*.dat` + `Pl*AJ.dat` + effect bank + `sound.zip` + costume zips; `fighter.json` has ~60 callbacks as absolute PPC addresses into the clone base's code. Route A (realistic):
unpack into `mods/<id>/files/` + a generated `mod.json` of kind `fighter` that `requires` the base the callbacks were built for (ACE-style filtered base), CSS icon + MxDt fighter rows through the
existing pack-split machinery (`tools/mex_port`). Effort ~1 week for a first fighter, because the callback addresses only make sense against a matching clone base and each fighter needs its
ids remapped into the free fighter slots; the netplay identity is by file content already. Route B: re-author as a Geno define (what Sora needed): per fighter, not an importer. Not generic.

## `.xdelta` patches and `.ssbm` bundles

What is known: a `.xdelta` post is a VCDIFF patch of the vanilla NTSC 1.02 ISO. Nucleus's own `.ssbm` "bundle" is (per the frontend code, `nucleus-ssbm-bundle-2026-10-10.md`) an xdelta of a whole built
m-ex ISO plus optional HD texture pack plus metadata; no sample exists locally and the container is unconfirmed.

Designed path (owner's direction), nothing redistributed:

1. The player presses Install on a patch post. Download the `.xdelta` into the Nucleus cache (`mods/.nucleus/dl`, the existing size-capped cache), at the player's request only.
2. Apply it to the player's OWN vanilla ISO (path from the game's disc setting) writing a patched ISO into the cache (`mods/.nucleus/iso/<post>.iso`, hundreds of MB to 1.4 GB; delete on Remove).
   Decoder: our own VCDIFF decoder (RFC 3284; ~400-600 lines of C, 1-2 days with tests) or xdelta3 itself (Apache-2.0: shippable with its NOTICE; ~3 files of C but it brings its own build
   flags). A prototype exists: `tools/nucleus/vcdiff.py` (stdlib Python, mmap source) decodes everything xdelta3 writes with no secondary compression (default, `-S none`, `-0`..`-9`: byte-identical
   in `tools/nucleus/test_vcdiff.py`). Secondary compression (`-S djw|fgk|lzma`; newer xdelta3 builds use lzma by default on larger inputs) is detected and refused with a clear message; lzma could use
   liblzma (public domain) but the layout was only checked against a hand-built patch, NOT a real xdelta3 lzma patch (the test exe has no lzma). So: unknown until one real Nucleus patch is tried.
3. Classify the patched disc with `tools/nucleus/iso_diff.py VANILLA PATCHED`: file counts and a verdict. `LOOSE-OVERRIDE` (only game files changed/added, `main.dol` identical, no `MxDt.dat`) ->
   write each changed/added file into `mods/nucleus-<post>-disc/files/<disc path>` (a "misc" mod; files run through the same structure checks as the loose installer; conflicts by file as now) and delete
   the patched ISO. `NEEDS-DISC-BOOT` (`main.dol` differs or `MxDt.dat` present: an m-ex disc, a gecko-patched dol) -> keep the ISO and offer "boot this disc" the way ACE / Akaneia are booted
   (the launcher / `MELEE_ISO`); nothing can be mounted loose. Measured: the owner's vanilla vs ACE discs diff as unchanged 1121 / changed 75 / added 990 / removed 13, `MxDt.dat` only on ACE,
   `main.dol` differs: verdict NEEDS-DISC-BOOT, in ~2 s.
4. What works end to end today: steps 2-3 as Python prototypes on synthetic and real discs (decode on plain patches; the diff). What does not: no C implementation in the game yet, no real Nucleus
   patch tried, no lzma, no UI row ("Patch: applies to your ISO"), no gecko/dol-patch handling (a changed `main.dol` is never loose), HD texture packs (Dolphin-only) ignored.
5. Constraints: the patched ISO and every file derived from it stay on the player's machine (git-ignored, never uploaded); no patch is applied to anything but the player's own image; the
   disc-derived files are not committed anywhere. The `.xdelta` itself is Nucleus's file: fetched on request, cached, not redistributed.

## Effort summary

| item | effort | blocked by |
|---|---|---|
| menus beyond the four files (GmRst, IfPrize ...) | hours each | in-game check per file |
| `.xdelta` in the game (C decoder + apply + diff + UI) | ~1 week | a real patch to test lzma; the boot-a-disc UI |
| `.ssbm` | unknown | a sample file or sc00p |
| custom stages | 3-4 days | an m-ex base disc/path |
| MexManager fighter zips | ~1 week per base | matching clone base |
