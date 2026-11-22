# Codex packet: Geno Workbench Blender add-on, Task 4 (client, fake_engine, launch)

You are working in the git worktree that is your current directory (wbt4). Edit only inside it.
Your shell is broken on this machine: you cannot run commands, tests or git. Write code and tests only. Do not run git or any
command; do not commit. Do not stop to ask; record choices in the report.

Read first (absolute paths, read-only):
- Plan: E:/Projects/Melee Workspace/docs/superpowers/plans/2026-10-09-geno-workbench-blender.md : read the header (lines 1-110: global constraints, review focus, file structure) and then ONLY Task 4 (lines 447-642). The tests quoted in the plan are exact; copy them verbatim into the test files, then write the implementation so they pass.
- Spec: E:/Projects/Melee Workspace/docs/superpowers/specs/2026-10-09-geno-workbench-design.md (Revision 1 at top).
- fake_engine imports wbspace (mul, mat4_from_12, apply_point etc.); another worker writes tools/blender/geno_workbench/wbspace.py in parallel from the plan's Task 3 interface (lines 186-210) - code against that interface exactly (Mat4 = tuple of 4 tuples of 4 floats; mat4_from_12, mul, apply_point, affine_inverse). Do not write wbspace.py or conftest.py yourself (Task 3 owns conftest.py); your tests rely on that conftest putting the package dir on sys.path.
- Real reply shapes of the Qt MCP server for the fake: E:/Projects/Melee Workspace/tools/release/launcher/qt/workbench/mcp_server.cpp (toolResult, initialize, tools/list) and commands_hitbox.cpp (hitboxJson), commands_*.cpp for list_rows/run_checks; match them.

Rules: Python 3 standard library only in pure modules (no numpy, no bpy outside the bpy-marked modules); localhost only; no disc-derived data; no Co-Authored/commit work.
Mentally execute every test against your code before finishing (you cannot run them). Be careful with exact vertex counts, signs and tolerances.

Final message (your report, at most 40 lines): files written; which tests you believe pass and the ones you are unsure of (and why); untested parts; the exact verification commands for a reviewer (from the plan's "Reviewer verifies" block); any deviation from the plan with the reason.
