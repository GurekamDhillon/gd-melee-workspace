# Workspace path preparation report

2026-09-27 — workspace branch `codex/ws-paths`.

## Design and scope

Prepare the workspace to move from its current Desktop location to
`E:/Projects/Melee Workspace`, without performing the move. Existing root conventions
remain the interface: script-relative `GW_ROOT`, selected game checkout `GW_MELEE`,
and per-lane `GW_BUILD_ROOT`. Local media/research paths come from exported environment
variables. Aurora has a separate `GW_AURORA_ROOT` junction contract because its CMake/Dawn
configuration must not use a workspace path containing spaces or an apostrophe.

The operator procedure and exact later Windows lane commands are in
[tools/move_workspace.md](tools/move_workspace.md), especially sections 3–7.
No game files were changed. No build, game run, move, junction change, Git worktree
repair, commit or `.env` edit was performed.

## Changes

- Audited tracked scripts/configs/docs throughout the repository, including `_build`,
  `tools/port`, `tools/release`, `tools/netplay`, `menu/pipeline`, `ports`, research notes,
  the link response lists and `.env` consumers. Application branding and the Windows
  Desktop known-folder output destination are not workspace path dependencies.
- Replaced machine-specific workspace roots in Python tools with `__file__`-derived
  defaults and `GW_ROOT`; external inputs use `GW_ISO_*`, `GW_BRAWL_FILES`,
  `GW_ULTIMATE_EXTRACT`, `GW_GHIDRA_PROJECTS` and `GW_MENU_DUMP`. Local extraction
  defaults are ignored. Python entry points require exported settings; they do not
  parse or execute `.env`. Historical documentation uses symbolic roots; historical
  test results and evidence remain historical, not rerun claims.
- Moved shell `.env` loading before derived build defaults. Legacy batch launchers
  derive their workspace root and use `run.sh`; capture/render helpers derive their
  paths locally. Legacy training/target launchers no longer kill every game process.
- Removed the SDL library's junction-specific entry from `melee_link_libs.rsp`.
  Added `tools/port/link_response.py`: relative, quoted lane object lists generated
  from the curated baseline, refreshed on lane creation and before normal linking.
  Cross-drive build roots require absolute entries and are correctly quoted.
  Custom `GW_LINK_OBJECTS` lists are intentionally caller-owned.
- Aurora wrappers require a valid, space/apostrophe-free junction selected by
  `GW_AURORA_ROOT`; no automatic junction creation or repair. Visual Studio discovery
  is shared through `vs_env.bat`; bootstrap uses installation environment folders,
  and Slippi's Bash launcher uses `GW_BASH` or PATH lookup.
- The old changed-TU verifier uses shared path settings and writer functions, preserving
  lane hardlink safety and checking the Windows pipeline exit status. Its non-PC pass
  is syntax-only. It was syntax-checked, not executed against game source here.
- Added the read-only `tools/check_workspace_paths.py`. Default inventory covers
  tracked/nonignored files, private root `.env` locations and both repositories' Git
  pointers/configuration; `--all` adds ignored text/configuration/build files. Windows,
  MSYS and WSL drive paths are detected, including UTF-16 text. `.env` output contains
  only key names/locations, never values. Junctions and Git object databases are not
  recursively traversed. Exit codes: 0 no findings, 1 findings, 2 incomplete inspection.

## Local inventory observed (read-only)

- `.env` has absolute locations for `GW_ISO_VANILLA`, `GW_ISO_AKANEIA`, `GW_ISO_ACE`.
  Values were not printed. The future move may leave external discs where they are;
  update only settings whose targets actually move.
- Workspace and game worktree administrative pointers contain the old absolute root.
  Workspace registrations observed include `ws-paths` and `ws-arena-lock`. Game
  registrations include `alpha`, `beta`, `charlie_slippi`, `echo`, and the `codex-*`
  worktrees. The checker discovers registrations dynamically; re-inventory at cutover
  because other agents can add worktrees while preparation is in progress.
- Build roots observed: `alpha`, `art`, `beta`, `charlie_slippi`, `echo`, `handoff`.
  Old absolute `.rsp` entry counts respectively: 1038, 1037, 1037, 1035, 1037;
  no response file was present under `handoff` at the inspected location.
  These generated files in the main checkout were inspected, not modified.
- Shared `_build/ax86m/CMakeCache.txt` records the existing Aurora junction for its
  source, cache directory and Dawn source. `agents/beta/ax86m_fd/CMakeCache.txt` still
  records the shared `ax86m` cache directory. That copied cache is not a validated
  independently configured lane; the plan requires regeneration through the junction.
- Release and netplay packaging already derive their workspace paths. Their Desktop
  output uses the OS known-folder API and supports `-Out`; no source-root fix was needed.
- Remaining checker hits include `.git` administrative pointers (repair later), private
  settings (review later), intentional move-plan paths, documentation placeholders,
  synthetic test paths and syntax examples. The scanner reports rather than silently
  suppresses these. Existing ignored generated artifacts in the **main checkout** were
  sampled as above; run `--root <main-root> --all` at cutover for the full generated-tree
  inventory. The full `--all` run performed here was on the preparation worktree.

## Verification performed

- `python -B tools/test_workspace_paths.py`: five tests passed. Covers `.env`
  redaction/read-only behavior, Windows/MSYS/WSL patterns, quoted relative lane lists
  under a space/apostrophe path and another root, rejecting unexpected baseline entries,
  and inspecting Python root defaults without importing disc-dependent converters.
- Python AST parsing passed for 56 changed/new Python files; edited JSON parsed.
- `bash -n` passed for six changed shell scripts.
- PowerShell parser passed for the four changed `.ps1` files.
- A synthetic `.env` test confirmed `GW_BUILD_ROOT` and `GW_MELEE` are loaded before
  `GW_EXE` derivation, under a temporary path containing spaces and an apostrophe.
  It did not source private settings.
- The checker completed its worktree `--all` audit with zero unreadable locations.
  Findings are expected while Git pointers still name the unmoved workspace. Counts
  also change as the report and move-plan examples are added.
- `git diff --check` passed. An AST scan found no remaining executable Python string
  constants pointing at the old user/workspace/disc roots.
- Changed game C: none, so PowerPC syntax checking is not applicable. Changed Lua:
  none, so `luac -p` is not applicable. No game code validation is being claimed.

## Untested and required Windows acceptance

No compilation/linking, Aurora configure/build, disc conversion, menu rendering,
release packaging, multiplayer, game boot or visual/controller validation was run.
Batch toolchain discovery and the actual junction cutover need the Windows acceptance
procedure. No executable was produced or checked for embedded paths; binary/debug/cache
contents are outside the text checker's scope. Cross-volume copy integrity and loss of
hardlink sharing need operator verification.

Run **the exact commands in tools/move_workspace.md section 7** after copying,
repairing both repositories and checking/regenerating Aurora caches. That creates the
fresh `ws-move-check` game/build lane under the new root, builds via `build.sh`, requires
the bridge/ABI audit, runs the ACE smoke sandbox, then opens a realtime visible sandbox
for GD. Inspect the fresh run log and process path, and verify menus, mods, controller
input and a level-0 CPU match. The plan separately calls for packaging, netplay and
art/converter checks. Keep the original workspace until GD accepts those results.
