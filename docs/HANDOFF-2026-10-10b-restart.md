# Handoff, 2026-10-10 (afternoon): restart to load the REA MCP

Supersedes `docs/HANDOFF-2026-10-10-session.md` for the current state; read with `docs/NEXT-SESSION.md`. The owner restarted Claude Code and Codex so the REA MCP loads (`npx rea-agents setup` done for Claude Code + Codex; Ghidra 12.1.4 at `E:\Projects\tools-ext\ghidra_12.1.4_PUBLIC`, `GHIDRA_INSTALL_DIR` set). Nothing is pushed.

## Integration tips
- Workspace `integration/2026-10-01/roguelite-100` at `0e790a6` (Goku dair hitboxes on FOOT_R).
- Game `integration/2026-10-01/roguelite-100-game` at `5dff115b5` (geno css/results art).

## Merged today
Workbench: T1/T2, live fixes, T11 Open in Blender hub, smooth playback (frame cache, ~60 fps), polish (Speed setting, frame-0 fix), fast rebuild (`build.py --auto`, hitbox round trip ~15 s), rebuild-keeps-row, Geno Falcon in the Workbench (HSDRaw + Blender Source Tools, `launch_falcon.py`). Splices, NLA hand-splicing, pose-error fix, CLIPS controls, geno-thrown/combo/retarget, Falcon geno (rebased), geno select/results art. Aurora/Dawn/LLVM 23.1.1/gwtool restored after the 08:48 worktree-removal accident (memory: worktree-remove-junctions). vs_env.bat finds VS by itself.

## Lanes in flight at restart (Claude leads died with the session; Codex processes may still run)
| worktree | branch / tip | state | next |
|---|---|---|---|
| wbhitboxux | ws/wb-hitbox-ux e439097 (+2 dirty) | Claude lead: role dropdown, Add/Delete hitbox + server commands, Spanish strings, live bench; nearly done | finish R3 live check (add jab1 HAND_R f3, rebuild, delete, byte-identical), build launcher, merge |
| stress6 (game) | agent/stress6 42be33a14 (+1 dirty) | Claude lead: overlay slots 512->2560, pool 65536 words, test geno_define_six_full; stage sweep for the heaviest map (incl. ACE) was running (_build/agents/stress6/runs/sw_*) | finish sweep, build 6 retail Geno defines locally, 6-CPU run realtime + turbo soak; owner wants 6 CPUs in one match (classic/adventure-style multi-CPU path) |
| wbfalconmoves | ws/wb-falcon-moves 059f4ab | Codex done; a Claude lead was building/testing (job A) | verify launch_falcon --check, overlays, edit+rebuild, run_checks, round trip |
| anim-bank-reload (game) | agent/anim-bank-reload 3186a4af1 (+1) | Codex done; same lead (job B) | build root animreload, suite >= 367, live clip swap + reload, refusals |
| wbattrs | ws/wb-attributes (12 dirty) | Codex (sol) attribute editor; report present | build launcher + tests, review, commit |
| csprender | ws/csp-render (5 dirty) | Codex (sol) CSProject "Render UI" (Blender 3.5.1, loom/render_button; never commit CSProject files) | when report lands: verify its .blend assumptions, run, check Goku CSPs in game |
| arterr | ws/artist-errors (20 dirty) | Codex (sol) audit R6+R8 | when report lands: test, commit |
| playlab | ws/play-in-lab (8 dirty) | Codex (sol) audit R7 Play in LAB | when report lands: build/test |
| tutorial | ws/author-tutorial (11 dirty) | Codex (sol) audit R5 tutorial; report present | review against code, commit |
| stagebuilder | ws/research-stage-builder | Codex (sol) web research + Claude lead on LOCAL Ultimate export (E:\Ultimate files\workspace; Stage Builder = `sp_edit`; Ghidra project ghidra-projects/Ultimate-Kirby.gpr) as primary source | redo the local half with REA/Ghidra; merge into `_research/stage-builder-ultimate-2026-10-10.md` |

Check Codex: `.omo/evidence/*report*.md` in each worktree and the tail of `.omo/evidence/codex*.jsonl` (`turn.completed`).

## Owner decisions today
- Use Codex as much as possible (memory codex-delegation); Claude leads build/test/merge.
- Aerial lift 120, home grounded, jab1 length = chain into jab2. Workbench playback default 60 fps.
- Gameplay-only fast rebuild yes; native-define hot reload (C) on hold; animation bank reload approved (Codex).
- Stress: 6 full Geno fighters as CPUs in one match, heaviest map incl. ACE.
- Ultimate local export + decomp is the primary source for Ultimate research.
- CSProject: free to use for mods' UI; never commit its files (no license, Nintendo models).

## Research notes added
`_research/hot-reload-2026-10-10.md` (+ Measurements), `_research/authoring-tools-audit-2026-10-10.md` (top 10 R1-R10).

## Owner queue
Try: Goku hitbox editing (Rebuild + reload ~15 s), Falcon in Blender, Speed/Run checks. Goku re-picks/splices, idle verdict, netplay match with Goku, live Geno Falcon look.

## Traps (new today)
- `git worktree remove` follows junctions: check reparse points first (memory worktree-remove-junctions). `C:\Users\Gurek\Desktop\GD's Melee` is a junction to this workspace; use E: paths.
- A lone copied melee-pc.exe crashes: SDL3.dll and webgpu_dawn.dll must sit beside it.
- Blender PrintWindow returns blank for its GPU window; use Blender's own screenshot.
- Codex shell still broken; Codex writes, Claude builds.

## Lane handoffs written before the restart (read these first)
Each lane wrote `.omo/evidence/handoff.md` in its worktree (git-ignored, on disk).
- wbhitboxux (ws/wb-hitbox-ux e439097): R1/R2 done (role dropdown, add/delete, 126 pytest, 23/23 ctest). Blocker: add/delete/edit sync `gameplay.json` windows but goku build reads local `gameplay.full.json` -> patch both when present (owner decision pending, recommended yes). Slots capped at 4; new-hitbox defaults dmg 6 size 3.0 angle 361 kbg 50 bkb 20, 2 frames.
- stress6 (agent/stress6 63e50a3ed WIP): suite 368/368, slots 2560, pool 65536, 6x Geno Falcon CPUs ran clean on FD (pool 30714/65536). Only captain has a retail template, so 6 *different* retail fighters need new templates (owner decision; Codex job). Sweep ~130/371 stages: worst vanilla ext 2 7.60 ms, ACE ext 71 5.86, ACE ext 2 5.80 (`_build/stress6/sweep.csv`). Owed: rest of sweep, realtime + 10-min soak, screenshots. Risks: stage heap 139 KB free with 6 Falcons on FD; snapshot globals +205 KB (netplay unmeasured).
- wbfalconmoves (ws/wb-falcon-moves 059f4ab): 364 rows, hitbox overlays, edit+rebuild 7.5 s, tests pass. Bug: run_checks requests frames past the move end (clamp). Owed: on-screen look.
- anim-bank-reload (agent/anim-bank-reload 3186a4af1): build OK, suite 374/374. Live test result unknown (`_build/animreload-live/out`); refusal checks unverified. Extra worktree `worktrees/animreload` (agent/animreload) from agent_new.sh, not removed. agent_slim not run.
- stagebuilder (ws/research-stage-builder e16476e WIP): local note `_research/stage-builder-ultimate-local-2026-10-10.md` (grid/canvas, layers, 15 materials, gimmicks, cliff thresholds in sp_edit.stdat: max_angle_of_cliff 120, _floor 45, min_angle_of_cliff_wall 85, min_interval_of_cliff 5; Box2D evidence). Loop-to-terrain algorithm NOT found; Ghidra project at E:\ghidra-sb-work\sbproj unfinished (re-import or use REA MCP). Codex web note not merged yet.

## Pending owner items at restart
- Leftover processes from the animreload live test (PIDs 15056 python launch_goku --serve-only, 30692 gd-melee-launcher, 36720 melee-pc from _build/animreload-live): owner to stop.
- `_build/release/GD Melee.exe` was overwritten at 12:26 by a worker's relative -Out path; rebuild from integration or restore.
- New launcher builds not yet installed over `_build/wb-win`: hitbox UX `E:\Projects\wbhitboxux-qt-build\gd-melee-launcher.exe`.
