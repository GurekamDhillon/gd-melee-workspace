# Codex packet: Geno slice 8, Sora as a define (continue an interrupted lane) (2026-10-08)

Workspace root `E:\Projects\Melee Workspace`. Two worktrees ALREADY EXIST; edit files ONLY there:
- game: `E:\Projects\Melee Workspace\worktrees\geno-s8` (branch `agent/geno-s8`)
- workspace: `E:\Projects\Melee Workspace\worktrees\ws-geno-s8` (branch `ws/geno-s8`)
Your sandbox cannot write `.git`: run NO git command that writes (no commit/add/branch/worktree/merge). The coordinator
commits your work. Read-only git (log, diff, show, status) is fine.

Read: `CLAUDE.md`, `tools/CLAUDE.md`, `ports/README.md`, `ports/ir/`, the brief
`worktrees/ws-geno-s8/docs/superpowers/plans/2026-10-08-geno-slice8-migrations.md` (read it fully: it is your plan),
`melee/docs/geno.md` sections 22-23 (in the game worktree), lesson `docs/learn/geno-fighters/13-fighter-lua.md`.

## State you inherit (a lead was cut off by a rate limit)

Game branch has: fighter.rows (own animation rows 303+, per-row flags/blend, joints to 256, overlays to 192), the nine
unnamed ftCo_DatAttrs fields in the attribute table, slice 5 (format 10 + Lua) merged. Workspace branch has:
`trail_define.py` (an installed Sora to a define package), fighter.rows in the checker and schema, the old-vs-define
parity tools (`moves_check_sora`, `locomotion`, `defense`, `sora_rewind`, `moves_diff`). Its last note: "Now run the
converter against the baseline install." Continue from the brief's task list.

## Rules

- Ultimate/Nintendo-derived data (Sora's models, animations, ACMD dumps, the installed Sora files) is LOCAL-ONLY and
  never committed: follow how `ports/ir` keeps it out of git (git-ignored `_build/` locations); never copy such files into
  tracked paths. Commit-able: code, converters, text definitions you author, docs, tests.
- You MAY build (`bash tools/port/build.sh` with `GW_MELEE` = the game worktree and `GW_BUILD_ROOT` =
  `E:\Projects\Melee Workspace\_build\agents\geno-s8`) and run the HEADLESS suite
  (`bash tools/port/run.sh --test <name> --iso "$GW_ISO_VANILLA"`, source `.env` first). Do NOT try windowed game runs
  (they crash inside your sandbox): instead WRITE the in-game parity commands (moves_check_sora etc.) into the report,
  exactly as the coordinator must run them.
- Changes to shared game files (geno_registry.c, the format, schema) are ADDITIVE; the format stays "geno": 10.

## Goal

Sora fully as a define: base "none", own model/clips/rows, articles and magic models drawn (`show_model`; the article fix
is already cherry-picked), specials expressed in data where possible and in fighter Lua (slice-5 API) where not. Make
the converter produce a define that passes `python -m tools.geno.check` and `python -m tools.geno.schema --check`, the
build passes, the headless suite passes. Record in the brief every gap the format still lacks (as decisions for the
owner: keys you would add and why).

## Deliver

Report to `E:\Projects\Melee Workspace\_build\tmp\codex-geno-s8-report.md`: a proposed commit message per worktree at the
top, files changed, build and suite results (quoted), the exact windowed parity commands to run, gaps/decisions.
