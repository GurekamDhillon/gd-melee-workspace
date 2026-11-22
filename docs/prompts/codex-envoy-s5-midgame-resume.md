# Codex packet: Envoy stage 5, resume after a MID-GAME disconnect fails (2026-10-08)

Workspace root `E:\Projects\Melee Workspace`. Worktrees ALREADY EXIST; edit ONLY there:
- game `E:\Projects\Melee Workspace\worktrees\envoy-s5` (branch `agent/envoy-s5`, has your earlier stage-5 commit 891b4eab1)
- workspace `E:\Projects\Melee Workspace\worktrees\ws-envoy-s5` (branch `ws/envoy-s5`, has the proof driver)
No git writes (the coordinator commits). You MAY build (`GW_MELEE` = game worktree, `GW_BUILD_ROOT` =
`E:/Projects/Melee Workspace/_build/agents/envoy-s5`), run the headless suite, native tests and the Envoy Lua suites.
No windowed/netplay runs in your sandbox: put the exact re-run command in your report.

## The failure (coordinator ran your proof driver outside the sandbox)

`np_envoy_resume.py set` with `MELEE_NET_SIM='lag=40,jitter=10,loss=2'`: 11 of 12 checks PASS (resume between games,
blackout, fresh-guest-process resume, play on into game 2, and "a mid-match loss keeps the record of the START of that
game"). Then: `TIMEOUT C: resumed after the mid-match loss after 600s` -> `CHECK FAIL C: resumed`. So after a disconnect
DURING a game, the saved records on both sides are correct, but the peers never complete the resume.
Evidence folder: `E:\Projects\Melee Workspace\_build\agents\envoy-s5\np_s5\s5-opus-set\` (host.log, guest logs,
`driver-output.txt` = the driver's full output, *.net.txt). The co-op run passed 9/9; the earlier clean-network control
passed (it exercises a between-games drop).

## Do

Read both peers' logs around the mid-match drop and the reconnect attempt (grep `netplay:`, `envoy`, `run`, `resume`,
`RN2`, `REFUSED`, `lobby`), find why the resume after a mid-game loss stalls (e.g. the lobby/state machine is still in a
match-in-progress phase, the record's "started" flag makes the resume check refuse or wait, the host and guest disagree on
game number/epoch, the guest is held in a results/abandon screen, or the driver waits for a line the code never logs). Fix
the cause in the game (or the driver if the game is right and the driver's expectation is wrong; say which with evidence).
Add/extend a native or Lua test for resume after a mid-game loss. All Envoy Lua suites, headless and native tests pass
(8 native cases already fail on integration: report only NEW failures).

## Deliver

Report `E:\Projects\Melee Workspace\_build\tmp\codex-envoy-s5-midgame-report.md`: root cause with log evidence, proposed
commit messages per worktree, files changed, test results quoted, and the exact command to re-run the set proof
(fresh ports, e.g. `MELEE_NETPLAY_PORT=55150 MELEE_S5_SERVER_PORT=55151`).
