# Codex packet: Geno Workbench Blender add-on, Task 3 (wbspace, shapes, rigmap)

You are working in the git worktree that is your current directory (wbt3). Edit only inside it.
Your shell is broken on this machine: you cannot run commands, tests or git. Write code and tests only. Do not run git or any
command; do not commit. Do not stop to ask; record choices in the report.

Read first (absolute paths, read-only):
- Plan: E:/Projects/Melee Workspace/docs/superpowers/plans/2026-10-09-geno-workbench-blender.md : read the header (lines 1-110: global constraints, review focus, file structure) and then ONLY Task 3 (lines 186-444). The tests quoted in the plan are exact; copy them verbatim into the test files, then write the implementation so they pass.
- Spec: E:/Projects/Melee Workspace/docs/superpowers/specs/2026-10-09-geno-workbench-design.md (Revision 1 at top).
- Interfaces and tests are fully specified in the plan; files go in tools/blender/geno_workbench/ (create tests/ too). Do NOT create __init__.py (Task 6 does).

Rules: Python 3 standard library only in pure modules (no numpy, no bpy outside the bpy-marked modules); localhost only; no disc-derived data; no Co-Authored/commit work.
Mentally execute every test against your code before finishing (you cannot run them). Be careful with exact vertex counts, signs and tolerances.

Final message (your report, at most 40 lines): files written; which tests you believe pass and the ones you are unsure of (and why); untested parts; the exact verification commands for a reviewer (from the plan's "Reviewer verifies" block); any deviation from the plan with the reason.
