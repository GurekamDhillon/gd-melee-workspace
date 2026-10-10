# Codex packet WB-5: CommandRegistry and Session (2026-10-09)

Your cwd is a workspace worktree (branch ws/wb-t5, cut from ws/geno-workbench at the Task 1 commit). Read `CLAUDE.md` first.
The plan is `docs/superpowers/plans/2026-10-09-geno-workbench.md` in this worktree: implement **Task 5 only** (its heading up to
the next "### Task"), plus the "Global Constraints" and "Review Focus" sections. The Interfaces block is binding (other tasks code against it).
Spec: `docs/superpowers/specs/2026-10-09-geno-workbench-design.md`.

## Known corrections to the plan text (already applied in the Task 1 commit)
- `wb_test(name)` compiles `tests/<name>_test.cpp` (exe `workbench_<name>`); `find_package(Qt6 ... Test)` is already in workbench/CMakeLists.txt.
- The synthetic fixture uses raw strings with the `JSON` delimiter; keep that if you add fixture content.
- Remove `empty.cpp` / its `else()` branch only if the task says so and your sources exist.

## Rules
- Write only inside this worktree. You cannot commit (the lead commits). Touch only your own files plus the CMakeLists lines your task names
  (`wb_core_sources(...)` / `wb_test(...)` in workbench/CMakeLists.txt). Other tasks edit the same lines in parallel: keep your edit to one or two lines so merges are trivial.
- C++17, Qt 6 Core/Network only in workbench_core. No disc/XV2-derived data. Tests use only the synthetic fixture.
- Write the test first as the plan says. Build/test, if your sandbox lets you run commands, via WSL Linux Qt:
  wsl -e bash -lc 'cd "/mnt/e/Projects/Melee Workspace/worktrees/ws-wb-t5" && cmake -S tools/release/launcher/qt -B _build/wb-qt -G Ninja -DBUILD_TESTING=ON -DLAUNCHER_DEPLOY_QT=OFF && cmake --build _build/wb-qt --target workbench_<test> && ctest --test-dir _build/wb-qt -R workbench_<test> --output-on-failure'
  If you cannot execute commands, review your code by reading and say so in the report; the lead builds.
- Do not stop for design approval; record choices in the report.

## Report
Write `.omo/evidence/wb-t5-report.md` in this worktree (max 40 lines): files, public API as implemented (signatures), deviations from the plan,
what you ran and its output, anything you could not run.
