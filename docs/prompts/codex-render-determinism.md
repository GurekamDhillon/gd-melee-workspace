# Codex packet: rendering changes game logic offline (2026-10-08)
Worktree exists; edit ONLY it; no git writes: game `E:\Projects\Melee Workspace\worktrees\render-det` (agent/render-det).
Your sandbox can only write inside that worktree: use build root `E:/Projects/Melee Workspace/worktrees/render-det/_wbuild`
(seed it like tools/port/agent_new.sh does, or report that you cannot and give the coordinator the commands) and write the
report to `worktrees/render-det/codex-render-det-report.md`.
Evidence (Falcon parity lane, 2026-10-08): identical inputs from the same savestate give different game outcomes in realtime vs
turbo-with-every-frame-presented, "because render-time particle draws change the logic" — i.e. render-side code consumes the
shared game RNG (HSD_Randi / the seed) or mutates simulation state, and how many frames are rendered changes it. Online, the
per-frame seed resync (gw_Replay_ResyncSeed; RB_GameHashForFrame hashes the effective seed) hides it; offline (replays, savestates,
LAB drills, parity tools, frame-skip/uncapped FPS) it changes results. Also a Falcon Kick flame/particle path drew RNG (found via
`gd.rng()` / `MELEE_RAND_TRACE`, see agent/falcon-geno 44175f776's diagnostics).
Do: find every render/particle/effect path that draws the GAME RNG or writes sim state during draw (MELEE_RAND_TRACE, psDisp*/
efLib/particle generators, camera shake, lbRefract etc.), give render-side randomness its own RNG stream (never the sim seed), keep
the GameCube-visible results identical where Melee itself does it in the sim (careful: some particle RNG IS in the sim on console —
preserve console behaviour for sim-side spawns; only draw/present-side consumption must move). Add a native/--test check: the
same scripted match run with 1x vs 2x presentation (or skipped presents) yields identical per-frame sim hashes. Headless suite and
native tests pass. Report cause list (file:line), fix, tests, commit message, coordinator commands for a realtime-vs-turbo check.
