# Codex packet: Envoy stage 5, abandon after a resume (third pass) (2026-10-08)

Same worktrees and rules as `docs/prompts/codex-envoy-s5-midgame-resume.md` (read it). Since the last pass the set proof
(driver fixed to retry a console still starting up) now PASSES every A/B/C check incl. the mid-game resume (14 of 16).
Two later checks, never reached before, FAIL (evidence `E:\Projects\Melee Workspace\_build\agents\envoy-s5\np_s5\s5-opus-set4\`,
`driver-output.txt` there):
- `CHECK FAIL D: and both start the same new run: game 1, 0-0, one new seed, no picks seed 1488769113 / 1488769113 game 2/2`:
  after ABANDON both sides start the same new seed, but the new run reports game 2, not game 1 (the game counter, and
  check score/picks too, is not reset when a run is abandoned after a resume).
- `TIMEOUT E: both in the lobby again after 400s` -> `CHECK FAIL E: lobby again`: after that, the two clients do not both
  return to the lobby.
Find both causes (logs: host.log, guest logs, around the abandon and after), fix in the game (or the driver, with
evidence), add tests, keep all Envoy Lua suites, headless and native tests passing (native should now be 58/58 on
integration; report any failure), report to `_build/tmp/codex-envoy-s5-abandon-report.md` with the re-run command
(ports 55180/55181). Note the driver at worktrees/ws-envoy-s5/tools/netplay/np_envoy_resume.py has an uncommitted
coordinator fix (Con: retry the first read): keep it.
