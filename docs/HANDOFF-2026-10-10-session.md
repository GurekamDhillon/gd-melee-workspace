# Session handoff, 2026-10-10 ~00:20 (owner restarting Claude for updates)

Supersedes nothing; read with `docs/NEXT-SESSION.md`. Workspace branch `integration/2026-10-01/roguelite-100`; game branch `integration/2026-10-01/roguelite-100-game`. **Nothing pushed tonight.**

## In flight when the session ended (Claude subagents die with the session; Codex processes may still be running)

| Lane | State | Where | What's next |
|---|---|---|---|
| **Blender Workbench** (plan `docs/superpowers/plans/2026-10-09-geno-workbench-blender.md`, spec revision 1) | T3, T4, T5, T6, T7, T10 merged; **the Blender self-test passes against the fake engine** (`GENO_WB_SELFTEST OK`, Blender 5.2.2, 120 poses, head error 1.07e-6, rotation error 2.8e-7, both facings) at `ws/geno-workbench` `235362d`. The headless engine (Dawn null backend + hidden window) was still being verified when the session ended. The coordinator was wrapping up, so check the branch tips for its last commits. The `agent/geno-workbench-data` game branch holds the clean data fix `6afd0b338`. | worktrees `worktrees/wbt*`, `ws-geno-workbench`, `geno-workbench` | Codex astra was writing **T8** (overlays and the headless Blender self-test) and **T9** (timeline and editing) in `worktrees/wbt8`, `wbt9` from 00:03. Check for `.omo/evidence/*report*`, then build, test and merge. Then the Claude tasks: **T1** (`frame_info` schema 2: per-bone `mtx`, `root{mtx,pos,facing}`, ECB L/R), **T2** (headless engine `MELEE_WB_HEADLESS=1`), **T11** (Qt hub and "Open in Blender"), **T12** (acceptance via MCP only: 3 wrong-limb hitboxes plus the dair re-pick; the owner views it in Blender, then in the game). Follow-up after T9, owner-approved: **NLA hand-splicing** (import XV2 and cross-port clips as actions, lay a recipe out as NLA strips, Bake & export through `tools/geno/artist`, status AUTHORED). |
| **Splice recipes** | **Core done, wiring owed.** `ws/goku-splices` `2557b75` (worktree `worktrees/ws-goku-splices`): `tools/splice.py`, `splices.json`, 20 pytest pass (synthetic data). Also copied, uncommitted, into the live `ports/goku-xv2`. | | **Owed, in order:** (1) `xv2_to_artist.splice_context(source, mesh)` returning resolve/rig/move_rows, with cross-port via `cross_port.tool()` plus the npz; (2) `splice_preview(recipe, file)`, a reduced build (Wait plus the clip); (3) `animations()` bakes recipe rows before the ground logic, padded with `pad_to`; (4) library rows `s<recipe>` in `main()`; (5) SPLICED in `fidelity.classify`; then a rebuild plus gates, CLIPS playback, and tightening 2 weak test asserts. Decisions taken: blends are inserted (strike frames stay exact); recipes are preview-only unless `"wired": true`. The 3 examples (utilt, dair, bair) stay unwired. |
| **LAB CLIPS frame-step controls** | **DONE**: `agent/lab-clips-step` commits `1122be843` and `d8358d07c`, deployed into the Goku package (backup `lab.lua.pre-clipsstep.bak`) | worktree `worktrees/lab-clips-step` | Pad: D-pad â†/â†’ step Â±1 (repeats when held), â†‘/â†“ Â±10, Y pause/play, X first, Z last, START opens the menu. Keys: â†/â†’, CTRLÂ±10, SPACE, HOME/END. Root cause: `pad_neutral` claimed the port, so CLIPS now mirrors the pad to a spare port. Owed: keyboard and panel text on screen; merge the branch. Relaunch with `ports/goku-xv2/tools/clips.ps1`. |

## Done tonight (merged locally unless noted)

- **Workspace integration:** disk hygiene (`60d23da`: run pruning keep 40 / strip 10, disk guard at 20 GB, `disk_report.py`, `agent_slim.py`); Jev v2 (`bb530a8`); Workbench spec and plans (`0dc8350`, `ae3cd74`, `b3150bc`, `2ebdd20`); the Goku source tree `ports/goku-xv2` (`92eb358`, allow-list `.gitignore`, stripped `gameplay.json`, the full local copy as `gameplay.full.json`); the geno schema with toon/shadow_tint plus the artist `scale_bones` (`21a27ce`). Also on integration: an accidental early fast-forward of `ws/wb-t4` (scaffold and task 4; a subset of `ws/geno-workbench`, left as is) and `tools/timing_audit` (rode in with disk hygiene).
- **Game integration** `e337ab6`: the FD black-line fix (Aurora viewport and EFB copy round outward; `MELEE_RESIZE_AT` test hook; `pc/tools/fd_blackline_repro.py`). It also carried the 7 Goku-polish commits, which the owner chose to keep: base-none shadow, toon, LAB CLIPS, the throw no-hang fix, and the LAB pad fix. Aurora libs are rebuilt; the headless suite is 361/361.
- **Branches done, not merged into integration:**
  - `agent/geno-thrown` + `agent/geno-thrown-ws`: victims of a base-none thrower play a stand-in's thrown rows (`thrown_as`, default captain). The owner said the throws look fine.
  - `ws/retarget-tool` (`retarget_melee_anim.py`).
  - `agent/geno-combo` / `ws/geno-combo`: combo graph, `jump_short`, meter HUD.
  - `agent/falcon-geno` / `ws/falcon-geno`.
  - `ws/timing-audit`.
  - `ws/geno-workbench` + `agent/geno-workbench(-data)`.
- **Goku:**
  - Punch list done: ground/hover blend, crouch grounded, the landing-sink ECB fix (TopN in the hip slot), the gi emblem decal, bair reach via thigh scale (gain 0.33), and landing lags all inside the retail ranges.
  - Floating idle `GOK_BAS_STAND_S` (alternates are clips 88/89, switched with `WAIT_CLIP`).
  - uair retune, ki charge loop, throws no longer hang, Luigi bair CROSS-PORT.
  - All gates green.
  - Re-pick shortlists are in `_build/goku-xv2/repick-shortlists.md`.

## Owner decisions on record (also in memory)

- Gameplay numbers (hitbox and frame values) may be committed; assets and dumps never (`gameplay-numbers-policy`).
- Kirby ports are deprecated; Meta Knight and Sora are parked in favour of Goku.
- The Workbench viewer is Blender (`D:\SteamLibrary\steamapps\common\Blender`, not on PATH). The engine is data-only. Add-on edits count as the human's; agents' edits are proposals.
- Scripted test runs use turbo (`MELEE_PAD_SCRIPT` needed, or turbo is refused). Windows stay on screen.
- Codex: sol is the workhorse, astra the stronger model. **The Codex shell sandbox is broken on this machine** (`setup refresh had errors`, os error 32 on `cua_node\...\node_repl.exe`; still broken on 0.162.1; the owner filed a bug, fields in `_build/tmp/codex-issue-fields.md`). So: Codex writes, Claude builds and tests.
- Jev v2: `runparse` first, triage on failures, coverage only as a flagger. Lane reports use one line per requirement: `R<n>: done/owed + evidence`. The key is in the workspace `.env`; load it per command.
- Restart lanes on Sonnet, not Opus. Max about 3 leads at once.

## Waiting on the owner

1. Re-picks for Goku: utilt, fair (vs nair), dair, jumps, grabs. They now want to **splice their own** from the XV2 kit, so the splice recipes and Blender NLA work above serve this. The clips viewer (`ports/goku-xv2/tools/clips.ps1`, console 51726) was paused on `xGOK_ATC_004` f8.
2. Verdicts on the floating idle (STAND_S vs 88/89) and on the walk/run-to-idle snap.
3. ~~An FD drag-resize confirmation on the fixed main build~~ **Confirmed by the owner 2026-10-10: the FD black-line fix (game `e337ab6`) passes the drag-resize test.**
4. A netplay match with Goku (owner chose to replace the automated rollback bench with this): two windows on loopback, with lag.
5. Goku's ledge feels slow to the owner, but the audit measured it as native (act at f7). Get a repro if it recurs.

## Traps hit tonight (avoid)

- Drive E: filled to 0 twice (89 agent build roots, sweeps, `gdm-overflow` junctions). The owner cleaned it up; there are about 448 GB free. Use `agent_slim.py` at the end of each lane, and remove merged worktrees.
- The main checkout gets left on other branches by lanes. Check `git branch --show-current` before every merge.
- Never `taskkill /IM melee-pc.exe`, which kills every lane's game.
- The Creator engine must use the project's `workbench.json` `mods_dir`, or the scene is rejected.
- A built package's geno-lab may carry a stale `lab.lua`. Sync it from the game repo.
- Screenshots: capture the game or launcher window only, never the whole desktop.
- Deleting files and `git reset --hard` are blocked by the auto-mode classifier. Ask the owner.

