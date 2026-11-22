# Codex packet: up to 255 costumes per fighter (skins step 1) (2026-10-08)

Workspace root `E:\Projects\Melee Workspace`. Game worktree ALREADY EXISTS: `E:\Projects\Melee Workspace\worktrees\skins255`
(branch `agent/skins255`, from game integration); build root `E:\Projects\Melee Workspace\_build\agents\skins255`.
Edit files ONLY in that worktree. Your sandbox cannot write `.git`: run NO git command that writes. You MAY build
(`bash tools/port/build.sh` with `GW_MELEE` = the worktree and `GW_BUILD_ROOT` = the build root) and run the headless
suite (`run.sh --test`, source `.env`) and native tests. Windowed runs crash in your sandbox: write the exact windowed
check commands into the report. In the sandbox `mexid_disc_table` may fail (disc identity unreadable); ignore it.

## Why

The owner wants players to install costumes freely. Today GD caps every fighter at **16 costumes**:
`src/melee/ft/ftdata.c:1756` and `:1806` clamp `if (ncost > 16) ncost = 16;` and the tables are static `[16]` arrays
(`ftData_MexCostumeLists[Ft_Kind_Max - Ft_Kind_Mex0][16]`, `ftData_MexCostumeStrings`, the retail-extension `strs[..][16]`
/ `lists[..][16]`). m-ex's own count is a `u8` (`gw_mex_ftfunction_runtime.c:1885`) and the costume id is a `u8`
everywhere it travels (character select `mncharsel.c:1441, 2262, 2389`, `player.c:730`, saves, replays, netplay), so
**255 per fighter** needs no format or protocol change.

## Do

1. Remove the 16 cap: size every per-fighter costume table from the real count (up to 255), retail-extension path too,
   without wasting memory for fighters with few costumes (allocate per fighter at boot from the heap the port uses for
   these tables, or a pool sized from the summed counts). Keep the retail lists exactly as they are for retail costumes.
2. Find every OTHER place that assumes <= 16 (or <= 6) costumes and would break above it: grep `costume` across
   `src/melee/mn/` (character select door/cursor/stepper, CSP lookups), `src/melee/pl/`, `src/melee/gm/`, `src/melee/if/`
   (stock icons), `src/melee/ft/`, the Atlas select (`gmfrontend_atlas_select.inc`, `Ui_Art*`), results, Kirby costume
   tables (`kirbyCostumes`), team costume indices, CPU/random costume picks, save/replay/netplay code (`gw_netplay.c`
   costume fields, Slippi `.slp` writer). Fix or bound each one; list them all in the report with file:line.
3. Tests: a native/headless test that loads a fighter with, e.g., 64 costumes (synthetic m-ex costume table or a test
   hook) and checks every costume index resolves its file/joint/matanim strings; and that a retail fighter is unchanged.
   All headless and native tests pass (note: several native tests were already failing on integration before this
   work, e.g. `mex-items-query`: compare against integration and report only NEW failures).

Do not change the netplay protocol or the u8 width. No disc data committed.

## Deliver

Report to `E:\Projects\Melee Workspace\_build\tmp\codex-skins255-report.md`: proposed commit message, files changed,
every <=16/<=6 assumption found and what you did, build + headless + native results (quoted), and the exact windowed check
for the coordinator (character select with a fighter that has more than 16 costumes: stepping through all of them).
