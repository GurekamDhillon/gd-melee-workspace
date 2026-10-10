# Codex packet WB-12R: review of the Task 12 work (read-only review) (2026-10-09)

Your cwd is the game worktree (branch agent/geno-workbench). The work is the commit "WIP checkpoint: workbench mode and wb.* API" (2217f9acd) on top of agent/goku-polish
(8258d4507): `git diff 8258d4507`-equivalent files: pc/platform/gw_workbench.c/.h, gw_script.c, script_game.c, gw_runtime.c, main.c, pc/tests/workbench_test.c, workbench_check.lua.
The spec is Task 12 in `E:\Projects\Melee Workspace\worktrees\ws-geno-workbench\docs\superpowers\plans\2026-10-09-geno-workbench.md` (Interfaces + JSON shape are binding).

Do NOT edit any source file (the lead is building and running tests in this tree; edits would break the build). REVIEW ONLY. Check carefully and report findings, each with file:line, severity
(blocker/important/minor) and the proposed fix:
1. Never-online gate: `wb` table and every wb.* function unreachable when netplay/slippi/online is active or the mode isn't `workbench`; the predicate matches `gs_require_offline`.
2. No hashed/rollback state touched: ScriptGame_WbFrame and all wb.* paths only read; `wb.frame`/`wb.step` use only the existing gd.set_motion/gd.step machinery; no new fields in any struct that is hashed, journaled or snapshotted.
3. Bridge fixpoint hazards: any non-static function added in files that the bridge maps; any change that moves/edits existing function signatures (the `l_set_motion` refactor into a helper must be behaviour-identical).
4. Lua API conformance with the plan: wb.load/row/frame/step/frame_info/clip/render/reload semantics and return strings (`@<path>`), error strings, 16 KB console reply cap respected (payloads to files), `wb.frame` pending protocol.
5. frame.json shape vs the plan's JSON shape (keys, nesting, `active` booleans, `ecb` nesting, `floorY`, `lowestY`), bone world positions correct (parent/child indices, joint count), hurtbox/ECB fields.
6. Scene parsing: p2-p6 forced none only for the workbench mode; no effect on other modes; `--workbench`/MELEE_WB_MOD behaviour.
7. Any C89/MSVC-clang portability problem, leaks, buffer overruns, unchecked snprintf.
Write the findings to `.omo/evidence/wb-t12-review.md` (max 60 lines, ordered by severity, most important first). Write nothing else.
