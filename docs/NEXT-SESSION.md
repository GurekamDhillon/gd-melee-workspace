# Next session — start here

**Current as of 2026-09-24.** Read [HANDOFF-2026-09-24.md](HANDOFF-2026-09-24.md) for the
current slate and its evidence. It supersedes this file's 2026-09-20 state and the dated
handoffs of 2026-09-20 and 2026-09-21. `HANDOFF.md` remains useful for its §6 Traps and §7
Conventions; its early status sections are historical.

For the newer Slippi work, read [HANDOFF-2026-09-24-SLIPPI.md](HANDOFF-2026-09-24-SLIPPI.md)
first. A complete two-native-client replay has passed public Slippi Direct
matchmaking, with exact processed inputs, game states and finalized checksums;
the Slippi handoff tracks final regression/integration status and remaining scope.
Two additional unchanged public Direct replay runs passed all 9,120 and 9,126
frames exactly; a third long replay was rejected at startup for non-neutral P1
processed input in the initial delay window and does not count as a pass. GD's
earlier one-time cleanup deleted 104 used `.slp` files, including the six old
`parity.local.conf` fixtures (4,396 recordings remained at the time).

## Baseline

- **v0.1.6 is published**, with stage D and corrected launcher online directions. The release
  targets workspace `75f0863` and game `919e345ac`; the strict package passed both disc-data
  guards. See the current handoff for the GitHub release link and validation limits.
- Game `pc-port` is now `1cf87fe4b`, containing the tested experimental Slippi
  replay-pair adapter, the current Discord community links, and the Windows
  title-bar drag fix. Both clients kept advancing during active/inactive window
  movement in a complete exact Direct replay; ACE remained 185/185. It has been pushed
  to `pub/pc-port`; workspace `master` contains the accompanying build/verification
  tools and handoff. Development lanes remain available with their task history.
- The **pre-stage-D executable** passed 185/185 headless tests on vanilla, Akaneia and ACE.
  Stage D has prior GD testing, 47 passing offline Lua checks, passing beta and main builds,
  and **185/185 on ACE** with the merged executable. A controller-enabled live LAB launch
  reached Fox/Fox on FD in `_build/runs/stage_d_lab_gd` without a FATAL log entry; GD said it
  looked good and closed the game.
- The three VPS crash reports remain untouched per GD's instruction.

## Working rules

- **Agents build; GD tests.** Give GD a running game and numeric/log evidence for a visual or
  controller check. No screenshots for verification. Default to ACE, level-0 CPUs and
  `MELEE_VOLUME=3`; use a visible main-desktop game window.
- Check at least 8 GB free RAM before launching; ordinarily keep one `melee-pc` process per
  agent. Kill only a PID you started after checking its executable path.
- Build through `tools/port/build.sh`, never raw clang. Inspect the log for `error` and `FAIL`
  even if the script says OK. The generated m-ex bridge must reach its link-map fixpoint.
- Do not push, publish or merge to `pc-port`/`master` without GD's explicit go. Never commit
  disc-derived data or Nintendo assets. Commit messages end with a `Co-Authored-By` line.

## Historical traps still worth keeping in mind

1. A stale source or copied executable can give a false verification. Confirm the changed
   build was used; `build.sh` now rebuilds stale game TUs and shims, but `_build/runs/<name>`
   contains a copy. `.github/README.md` outranks the root README on GitHub when present.
2. A harness summary can hide a fault. Inspect the run's `melee-pc.log` before dismissing it.
3. Several simultaneous games can contend for caches, memory and volume handling. Use
   separate run and build roots and respect the one-process baseline above.
4. `MELEE_MODS_DIR` names the **parent** of a mod pack. Pointing it at the pack can make a
   green-looking test run prove nothing.

The earlier file's stage/trophy triage and 70/70 count were 2026-09-20 snapshots. Consult
dated research before reviving one of those tasks.
