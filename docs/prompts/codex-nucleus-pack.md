# Codex packet: turn an SSBM Nucleus m-ex project into a GD's Melee pack (2026-10-08)

Workspace root `E:\Projects\Melee Workspace`. Workspace worktree ALREADY EXISTS: `E:\Projects\Melee Workspace\worktrees\ws-nucleus-pack`
(branch `ws/nucleus-pack`). Edit files ONLY there. No git writes (the coordinator commits). Python only; no game runs.

Read: `CLAUDE.md`, `tools/CLAUDE.md`, `docs/mods-packaging.md` (section 2.2 "Packs: a mod disc turned into a mods folder"),
`tools/mex_port/make_mod_from_disc.py` (and its tests if any), `_research/nucleus-mod-format-2026-10-08.md`,
`_research/nucleus-modloader-2026-10-08.md` (the permission terms: link back to Nucleus; do not contact its servers).

## Why

SSBM Nucleus (by sc00p, permission granted with a link back) builds an **m-ex project**: an extracted disc folder
(`files/` = the disc's FST files incl. `MxDt.dat`, `PlCo.dat`, `SmSt.dat`, `MnSlChr.usd`, ...; `sys/` = `main.dol`,
`boot.bin`, `bi2.bin`, `apploader.img`; plus `data/` JSON and `project.mexproj`). GD already plays m-ex mod discs as packs:
`make_mod_from_disc.py --vanilla <retail ISO> --mod <mod ISO> --name <n>` diffs the FSTs and writes `_build/packs/<n>/`
with the new/changed files + a `<n>.gdm_pack.json` manifest (size + sha256 per file). Make the same work when the mod side
is a Nucleus project folder, so anything built in Nucleus loads in GD.

## Do

1. Accept a FOLDER as the mod side (`--mod <dir>` where `<dir>/files/` holds the disc tree; also accept `<dir>` being the
   files root itself), producing exactly the same pack shape and manifest as from an ISO: files new vs the vanilla ISO,
   or whose content differs (hash same-size files). Ignore Nucleus project bookkeeping (`data/`, `assets/`,
   `project.mexproj`, `sys/` except note main.dol changes as unsupported). Case-insensitive path matching as the ISO
   path does.
2. Pack metadata: write a `mod.json` beside the files (follow `docs/mods-packaging.md`) with `source: "nucleus"`,
   the project name (from `project.mexproj` `build.name`), and a credit/link "Built with SSBM Nucleus -
   https://ssbmnucleus.net". Report m-ex specifics found (fighter count from `data/fighters/*.json`, stages, whether
   `MxDt.dat` changed).
3. Tests with SYNTHETIC folders and a synthetic tiny ISO/FST fixture only (no disc data in tests or in the repo).
4. Document it in `docs/mods-packaging.md` (2.2) and the tool's help.
5. Then RUN it for real, locally only (output stays under git-ignored `_build/packs/`): vanilla ISO from `.env`
   (`GW_ISO_VANILLA`), mod = `C:\Users\Gurek\AppData\Local\SSBM Nucleus\projects\My_Project`, name `nucleus-my-project`.
   Report file counts (new / modified), total size, MxDt/PlCo changed?, and anything skipped. If your sandbox cannot read
   that folder or the ISO, say so and give the exact command for the coordinator.

## Deliver

Report `E:\Projects\Melee Workspace\_build\tmp\codex-nucleus-pack-report.md`: proposed commit message, files changed,
test results, the real run's numbers (or the command), and the exact command to boot GD with the pack
(`MELEE_MODS_DIR` pointing at a folder containing it, Windows-style path) for the coordinator's in-game check.
