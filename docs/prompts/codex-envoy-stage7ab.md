# Codex packet: Envoy online stage 7a/7b, run director + Classic plan (finish an interrupted lane) (2026-10-08)

Workspace root `E:\Projects\Melee Workspace`. Worktrees ALREADY EXIST; edit files ONLY there:
- game: `E:\Projects\Melee Workspace\worktrees\envoy7` (branch `agent/envoy7`)
- workspace: `E:\Projects\Melee Workspace\worktrees\ws-envoy-stage7` (branch `ws/envoy-stage7`)
Your sandbox cannot write `.git`: run NO git command that writes. You MAY build (`bash tools/port/build.sh`, with
`GW_MELEE` = the game worktree, `GW_BUILD_ROOT=E:/Projects/Melee Workspace/_build/agents/envoy7`) and run the HEADLESS
suite (`run.sh --test`) and native tests. Windowed/netplay game runs crash in your sandbox: do not attempt them; write
the exact two-client proof commands into the report. In your sandbox the `mexid_disc_table` headless test fails (the
sandbox cannot read the disc's identity table); it passes outside. Ignore that one, report everything else.

## FIRST: an unfinished merge

The game worktree is IN THE MIDDLE OF A MERGE of `agent/envoy-s5` (stage 5 complete) into `agent/envoy7`.
`pc/platform/gw_netplay.c` has 4 conflict hunks (lines ~4482, 4624, 4754, 4944): all in the native TEST code. HEAD's side
has the stage-7 tests (`test_stagerun_record`, `test_lobby_run`, the run-director tests); the other side has the stage-5
run-record tests (`rnt_*` helpers, resume/abandon/conflict/co-op-word tests). Resolve so BOTH test sets exist and compile,
each function whole (do not interleave statements of two functions), and both are registered. Keep every non-test line
of both sides. Remove all conflict markers. The coordinator will `git add` and commit the merge.

## Then: stage 7a/7b

Read `CLAUDE.md`, `tools/CLAUDE.md`, the brief `worktrees/ws-envoy-stage7/docs/superpowers/plans/2026-10-08-envoy-online-stage7.md`
INCLUDING its "Owner decisions" section, `_research/envoy-netplay-scoping-2026-10-05.md` section 5, and the game
worktree's `pc/scripts/examples/envoy/ONLINE.md`, `COOP.md`. A WIP commit (the last commit before the merge) holds the
interrupted lead's run director (`pc/platform/gw_netdir.h`, `pc/platform/gw_netplay_run.inc`, `pc/tests/netdir_test.c`,
changes in gw_netplay.c / gmfrontend*.c / gmvsmelee.c): read it, finish it.
- 7a: the run director skeleton over GS_VS stages; the stage-end barrier (each peer sends epoch, exit frame, final hash,
  outcome before leaving a scene; refuse/abort on mismatch); a minimal interstitial screen between stages.
- 7b: the Classic plan over the 1P tables: agreed unlock mask = intersection, seeded stage/opponent selection (opponents
  may be human-vs-human placeholders until stage 6 lands CPUs).
- Owner decisions to implement: shared stocks for the pair, a lost stage ends the run for both, one continue token per
  run, Envoy mode word V2 allowed, skip Adventure special stages, run record RN2 (shared with stage 5).
Native tests for the director/barrier/plan; all headless and native tests pass; additive changes; no other protocol
change.

## Deliver

Report to `E:\Projects\Melee Workspace\_build\tmp\codex-envoy7ab-report.md`: merge-resolution summary, proposed commit
messages per worktree, files changed, build + headless + native results (quoted), and the exact two-client loopback
proof commands for the coordinator (local server bound to 127.0.0.1 on its own port, `MELEE_NETPLAY_BIND=127.0.0.1`,
`MELEE_NETPLAY_PORT` in 58xxx, guests join by room code via Lua, with and without `MELEE_NET_SIM`): a 3+ stage
Classic-plan run with identical RN2 records and outcomes and 0 desyncs; a poisoned run refused; shared stocks running out
ending the run on both. The existing driver `tools/netplay/run/run_pair.py` (workspace worktree) is the starting point.
