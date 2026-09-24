# docs/: the project's own documents

Which document is current, and what goes where.

| file | status | what |
|---|---|---|
| `NEXT-SESSION.md` | **read first** | the state of things, the three ways the tree lies to you, what to do first |
| `HANDOFF.md` | current for its §6 Traps and §7 Conventions; its §0-§4 state is dated at the top | the architecture of m-ex content in the port |
| `HANDOFF-2026-09-20.md`, `-21.md` | superseded snapshots, kept for the record | |
| `DEVLOG.md` | history; the numbered sections are dated, later corrects earlier (§5.2 corrects §1-4) | how each blocker was found and fixed |
| `scripting.md` | current, public | the `gd` scripting API and `gd.kit` (the LAB's private API is `melee/docs/geno.md` §14) |
| `MEX_PORT_STATUS.md` | current | what of m-ex works on which disc |
| `mods-packaging.md`, `mods-browser.md` | current | the mod folder layout; the in-game mod browser design (not built) |
| `ART-BRIEF-menus.md` | the brief the art follows | for `menu/` |
| `readme/` | the README's images, committed PNGs | rebuilt from `menu/pipeline/readme.py` |
| `prompts/` | prompts used to drive agents | |

Deep research lives in `_research/<topic>.md` at the repo root (m-ex, rollback, the frontend, boot,
scene launch...), one file per topic, each with its date and what it supersedes.

## Writing here

- A session's handoff is a dated file that says at the top which earlier one it supersedes; then
  `NEXT-SESSION.md` is rewritten to point at it. Do not append a fourth handoff without retiring one.
- Claims are dated and, where they came from a run, name the run (the exe's commit, the disc).
  A claim verified against a stale exe is the documented failure mode; say how it was verified.
- Public documents (`scripting.md`, the READMEs, release notes) never mention private branches,
  disc images or the machine's paths.
- Release notes are not here: `tools/release/notes/<version>.md`.
