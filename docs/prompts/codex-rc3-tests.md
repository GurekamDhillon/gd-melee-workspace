# Codex packet: two release-only test failures (2026-10-08)
Worktrees exist; edit ONLY these; no git writes: game `E:\Projects\Melee Workspace\worktrees\rc3-tests` (agent/rc3-tests; build root
`E:/Projects/Melee Workspace/_build/agents/rc3-tests`), workspace `E:\Projects\Melee Workspace\worktrees\ws-rc3-tests` (ws/rc3-tests).
You may build and run the headless suite (also on an extracted release zip); no windowed runs.
1. Linux headless `skins_parse` fails: "skins: refusal 9 (team must be): took 0, messages 1, wanted 'team must be'". The test
   builds its temp path with a `\` separator and reads TEMP. Make the test platform-neutral (path join, TMPDIR/TEMP fallback)
   without weakening what it asserts. Find it from `skins_parse` registration (pc/platform/gw_skins_tests.inc).
   Cross-check by syntax/logic; the coordinator builds Linux.
2. `script_item_events` and `script_lab_events` PASS on the dev build but FAIL in the packaged Windows release zip (rc1 and rc2:
   `_build/release-022rc2-win/GDMelee-0.2.2-rc2-win64`; run its exe headless the same way the dev suite does, e.g.
   `melee-pc.exe` with the test flags from tools/port/run.sh --test, in a scratch copy). Find why (a script/mod/asset missing from
   the package, a dev-only path, an env var run.sh sets). Fix the test if it assumes a dev layout, or the PACKAGING
   (tools/release/build_release.ps1 / package manifest in the ws worktree) if the release really lacks something players need.
Report `E:\Projects\Melee Workspace\_build\tmp\codex-rc3-tests-report.md`: causes with evidence, changes, results, commit messages.
