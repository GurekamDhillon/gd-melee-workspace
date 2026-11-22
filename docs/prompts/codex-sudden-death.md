# Codex packet: online sudden death (finish an interrupted lane) (2026-10-08)

Workspace root: `E:\Projects\Melee Workspace`. Game worktree for this lane: `E:\Projects\Melee Workspace\worktrees\sudden-death`
(branch `agent/sudden-death`, from game integration). Its build root: `E:\Projects\Melee Workspace\_build\agents\sudden-death`
(create it with `bash tools/port/agent_new.sh` only if missing; otherwise export `GW_MELEE` to the worktree and
`GW_BUILD_ROOT` to that build root and use `bash tools/port/build.sh` / `bash tools/port/run.sh` from the workspace root).
Read `CLAUDE.md`, `tools/CLAUDE.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md` first.

## The bug (affects released 0.2.x online sets)

A timed-out TIE in an online match sends retail into `GS_SUDDEN_DEATH`, a non-VS scene. The net session closes
there and each peer plays sudden death OFFLINE and alone (logs: `_build/netrun/spike2/`: host 22.7 s, guest 5.3 s).
The set winner is not agreed.

## State you inherit

A previous lane (cut off by a rate limit) left UNCOMMITTED changes in the worktree: `pc/platform/gw_netplay.c`,
`src/melee/gm/gmfrontend_online.inc`, `src/melee/gm/gmvsmelee.c` (+18 lines). Its last note: "Build OK, ABI audit 0.
Verify the artifact has the new text, then run the offline control." Read that diff first (`git -C worktrees/sudden-death
diff -- src pc/platform/gw_netplay.c src/melee/gm`), decide whether it is the right fix, finish it.
`pc/platform/gw_mex_bridge.c` diffs are normal build output: never hand-edit; do not commit them in your fix commit.

## Required behaviour

Online, a tie is resolved IDENTICALLY on both peers: preferably sudden death stays inside the rollback session (both
peers enter it together, synced); if that is not possible, an agreed rule (e.g. the game is a draw and is replayed) with
a clear on-screen message. Offline sudden death is unchanged. No netplay packet layout change and no protocol bump
(if one seems necessary, stop and write that in the report instead).

## Proof (you may build and run the game)

1. `bash tools/port/build.sh` ends `OK` with the ABI audit `reads ECX/EDX in prologue : 0`; `grep -a` finds your new
   log text in the built exe.
2. `bash tools/port/run.sh --test <name> --iso "$GW_ISO_VANILLA"` (source `.env` first): all tests pass.
3. Two-client loopback tie: BOTH clients with `MELEE_NETPLAY_BIND=127.0.0.1`, windows offscreen
   (`MELEE_WINDOW_X=30000 MELEE_WINDOW_Y=30000`), the local matchmaking server
   `python tools/netplay/server/gdmelee_server.py --bind 127.0.0.1` (never netplay.gsd.sh; never bind 0.0.0.0 or the
   Windows Firewall prompt stalls the run), driven by `tools/netplay/np_drive.py --local-server --offscreen` or the
   `tools/netplay/run/run_pair.py` pattern (guest joins by room code via Lua `gd.netplay_act("code", ...)`), a short
   time limit and idle/equal play forcing a tie; with and without `MELEE_NET_SIM` lag/jitter/loss. Both peers reach the
   same outcome and the same next set state; `desyncs 0`.
4. Offline control: an offline timed tie still enters retail sudden death.
Stop every process you start, by its PID.

## Deliver

Commit on `agent/sudden-death` only (message ends `Co-Authored-By: Codex <noreply@openai.com>`). No merge, no push.
Write the report to `E:\Projects\Melee Workspace\_build\tmp\codex-sudden-death-report.md`: result, commit hash, the
quoted log lines proving each proof item, anything unverified.
