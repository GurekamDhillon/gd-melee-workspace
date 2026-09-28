# docs/: the project's own documents

Which document is current, and what goes where.

| file | status | what |
|---|---|---|
| `NEXT-SESSION.md` | **read first** | the current baseline, operating rules and historical traps |
| `RESUME-2026-09-28-e06941cb.md` | landed history | the finished `gd.comm` pickup (game `d6b067d25`) and the paused session's context; the other paused lanes are in `PAUSED-2026-09-27.md` |
| `HANDOFF-2026-09-24.md` | historical baseline | superseded for current state by the 2026-09-27 `NEXT-SESSION.md` |
| `HANDOFF-2026-09-24-SLIPPI.md` | historical test evidence | replay-pair results, not validation of later HEAD |
| `QUEUED-2026-09-26.md`, `QUEUED-2026-09-27.md` | superseded request records | folded into `NEXT-SESSION.md`; lane assignments are historical |
| `HANDOFF.md` | architecture, current traps and conventions | the architecture of m-ex content in the port |
| `HANDOFF-2026-09-20.md`, `-21.md` | superseded snapshots, kept for the record | |
| `DEVLOG.md` | history; the numbered sections are dated, later corrects earlier (§5.2 corrects §1-4) | how each blocker was found and fixed |
| `scripting.md` | current, public | the `gd` scripting API and `gd.kit` (includes the public LAB API; detailed fields in `melee/docs/geno.md` section 14) |
| `MEX_PORT_STATUS.md` | current | implemented surfaces, feature inventory and verification limits |
| `mods-packaging.md`, `mods-browser.md` | current | the mod folder layout; the in-game mod browser design (not built) |
| `ART-BRIEF-menus.md` | the brief the art follows | for `menu/` |
| `readme/` | the README's images, committed PNGs | rebuilt from `menu/pipeline/readme.py` |
| `prompts/` | prompts used to drive agents | |

Deep research lives in `_research/<topic>.md` at the repo root (m-ex, rollback, the frontend, boot,
scene launch...), one file per topic, each with its date and what it supersedes.

## Writing here

- Dated state supersedes undated state. State the winner at the top of both. The 2026-09-27
  `NEXT-SESSION.md` is the consolidated current state; queued request records are retained with
  superseded notices. Replace stale prose rather than appending an "update" below it.
- Check API names against `gw_script.c` registration tables and command flags against the scripts.
  Claims are dated and, where they came from a run, name the run (the exe's commit, the disc).
  A claim verified against a stale exe is the documented failure mode; say how it was verified.
- Public documents (`scripting.md`, the READMEs, release notes) never mention private branches,
  private disc locations or the machine's paths.
- Release notes are not here: `tools/release/notes/<version>.md`.
