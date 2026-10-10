# Codex packet WB-12: game workbench mode and wb.* API (2026-10-09)

Your cwd is the game worktree `E:\Projects\Melee Workspace\worktrees\geno-workbench` (branch `agent/geno-workbench`, cut from
`agent/goku-polish`). Read the game `CLAUDE.md`, `pc/platform/CLAUDE.md`, then the plan
`E:\Projects\Melee Workspace\worktrees\ws-geno-workbench\docs\superpowers\plans\2026-10-09-geno-workbench.md`
**Task 12 only** (heading "### Task 12", the section up to "### Task 13") and the spec
`...\ws-geno-workbench\docs\superpowers\specs\2026-10-09-geno-workbench-design.md` for context. Implement Task 12 Steps 2, 4-8 exactly
as specified (Interfaces block and JSON shape are binding: the launcher's `FrameInfo` parses it).

## Rules
- You may only write inside this worktree. You cannot commit; do not try. Do not touch `tools/port/native_test.sh` (it is in another repo;
  the lead adds the `workbench` case: `workbench) sources=(pc/tests/workbench_test.c pc/platform/gw_workbench.c)`).
- The shared build root `E:\Projects\Melee Workspace\_build\agents\geno-workbench` is outside your sandbox: if you cannot run
  `tools/port/build.sh` or the native test, do not fight it. Instead syntax-check what you can (`clang --target=powerpc-unknown-eabi -fsyntax-only`
  for game-side C, plain `clang -fsyntax-only`/`cc` for the pure `gw_workbench.c` + `workbench_test.c`, which you CAN compile and run by hand:
  `cc -I pc/platform pc/tests/workbench_test.c pc/platform/gw_workbench.c -o <worktree>/.wbtest.exe && .wbtest.exe`; delete the exe after).
  The lead builds the game and runs the in-game check.
- `wb` Lua table exists only when `gw_Wb_Enabled()`. Presentation/diagnostic only: never write game state in `ScriptGame_WbFrame`,
  never touch hashed or rollback state, never active in netplay/slippi.
- Use real field names found by the greps listed in Step 7 of the plan. If a joint/hit/hurt/ECB field cannot be read cleanly, fill what you can,
  leave the rest zero and say exactly what in the report.
- Keep every file compilable at every save. No disc-derived data anywhere.
- Step 6 finding about `p2` absent (does an absent p2 seed a default CPU?) must be answered in the report with the code line.
- Write `pc/tests/workbench_check.lua` per Step 10 (in-game check; the lead runs it).

## Report
Write `<worktree>/.omo/evidence/wb-t12-report.md` (max 60 lines): files changed, how each wb.* call behaves, the Step 6/7 findings
(field names used, p2 finding), what you compiled/ran and its output, the exact commands for the lead to build and run the in-game check,
and anything you could not do.
