# Codex packet: Envoy online stage 5, co-op groundwork (finish an interrupted lane) (2026-10-08)

Workspace root `E:\Projects\Melee Workspace`. Worktrees ALREADY EXIST; edit files ONLY there:
- game: `E:\Projects\Melee Workspace\worktrees\envoy-s5` (branch `agent/envoy-s5`)
- workspace: `E:\Projects\Melee Workspace\worktrees\ws-envoy-s5` (branch `ws/envoy-s5`; the stage-5 brief belongs here)
Your sandbox cannot write `.git`: run NO git command that writes. Read-only git is fine. The coordinator commits.
You MAY build (`bash tools/port/build.sh` from the workspace root with `GW_MELEE` = the game worktree and
`GW_BUILD_ROOT=E:/Projects/Melee Workspace/_build/agents/envoy-s5`) and run the HEADLESS suite
(`bash tools/port/run.sh --test <name> --iso "$GW_ISO_VANILLA"`, source `.env`) and Lua/Python tests. Windowed and
netplay game runs crash in your sandbox: do NOT attempt them; write the exact netplay proof commands into the report.

Read: `CLAUDE.md`, `tools/CLAUDE.md`, `_research/envoy-netplay-scoping-2026-10-05.md` (section 5, stage 5),
`melee/pc/scripts/examples/envoy/ONLINE.md`, `COOP.md`, `README.md` (game worktree copies), and the stage-7 plan
(`docs/superpowers/plans/2026-10-08-envoy-online-stage7.md` on the workspace integration branch, read-only via
`git show integration/2026-10-01/roguelite-100:<path>`), including its "Owner decisions" section: shared stocks for the
pair, a lost stage ends the run for both, one continue token per run; run record shared with stage 7.

## State you inherit

Committed on `agent/envoy-s5` (259ee2e6c): run record RN2 (shared with the stage-7 record), saved-run check,
peer-to-peer resume, abandon, interrupted runs, co-op mode word, continue offline. UNCOMMITTED in the game worktree:
`pc/platform/gw_netplay.c`, `pc/scripts/examples/envoy/COOP.md`, `ONLINE.md` (read the diff; finish or fix it).
The lead's last note: "update the plan doc for the unified record". Write/finish the brief
`docs/superpowers/plans/2026-10-08-envoy-online-stage5.md` in the workspace worktree.

## Goal

Stage 5 complete per the scoping study and the owner decisions: both players' run state (seed, depth, loop, bags,
keystones, stage order, shared stocks and the continue token) carried in RN2 and digest-checked like builds;
peer-to-peer resume of an interrupted run; abandon / continue offline leaving both clients consistent; the lobby mode
flag for a co-op run vs the Versus set. Native and Lua unit tests for the record, resume and abandon logic
(pc/tests/envoy_*.lua style suites must all pass: run them). Additive changes to shared files; no protocol bump (the
owner approved an Envoy mode word V2 if needed: you may add it; nothing else).

## Deliver

Report to `E:\Projects\Melee Workspace\_build\tmp\codex-envoy-s5-report.md`: proposed commit messages per worktree at
the top, files changed, build + headless suite + Envoy suite results (quoted), and the exact two-client netplay proof
commands (local server bound to 127.0.0.1 on its own port, `MELEE_NETPLAY_BIND=127.0.0.1`, a unique
`MELEE_NETPLAY_PORT` such as 55100, guests join by room code via Lua, `MELEE_NET_SIM` lag/jitter/loss variant,
disconnect/reconnect for resume) for the coordinator to run.
