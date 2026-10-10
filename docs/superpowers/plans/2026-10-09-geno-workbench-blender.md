# Geno Workbench, Revision 1: Blender Add-on Is the Viewer: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Blender 4.x add-on `geno_workbench` that connects to the Geno Workbench, poses the fighter's rig to the engine's exact bone matrices per frame, draws hitboxes, hurtboxes, ECB and floor as Blender objects, steps frames and moves through the engine, lists problems and edits hitboxes through `workbench_core`; plus a true headless engine, a corrected coordinate contract, and a Qt hub (no 3D viewport, "Open in Blender").

**Architecture:** The game exe (workbench mode, now optionally headless) is the source of truth for data only. A launcher process (`gd-melee-launcher --serve`, or the Creator hub's own listener) owns one `Session` (registry, history, engine link) and speaks the existing JSON-RPC (MCP) framing on 127.0.0.1. The add-on is a thin client of that socket: every pose, overlay and edit is a registry command (`load_row`, `set_frame`, `play`, `frame_info`, `list_rows`, `list_hitboxes`, `run_checks`, `edit_hitbox`, `rebuild`, `reload`). The add-on never talks to the game console and never writes package output.

**Tech Stack:** Python 3 stdlib only in all pure modules (importable outside Blender, pytest-able); Blender 4.x `bpy`/`mathutils` in the glue modules; C++17/Qt 6 for the launcher parts; C11 + Lua in the game; no compiled add-on dependencies.

**Spec:** `docs/superpowers/specs/2026-10-09-geno-workbench-design.md` ("Revision 1: Blender is the viewer" at the top wins over the original design below it). Builds on `docs/superpowers/plans/2026-10-09-geno-workbench.md` (tasks 1-15 done, 16 panels finishing; this plan supersedes its Task 15 viewport and Task 17).

## Global Constraints

- Blender add-on: Blender 4.x, Python only, **no compiled or pip dependencies**; pure modules use the standard library only (no numpy), so `pytest` runs them outside Blender.
- Blender authoring space is Z up, the character faces -Y, left is +X, **1 unit = 1 Melee unit** (`tools/geno/artist/blender/skeleton.py` docstring). Engine/glTF model space is Y up, forward +Z. The one mapping used everywhere: **engine (x, y, z) -> Blender (x, -z, y)** (`ports/goku-xv2/tools/render_contacts.py`: "Native model (x,y,z) -> Blender (x,-z,y)"). It lives only in `wbspace.py`.
- Localhost only: the add-on, `--serve` and the hub listener use `127.0.0.1`; `McpClient` refuses any other host. The game console already binds `127.0.0.1`.
- No disc-derived or XV2-derived data in the repo, in fixtures or in tests. The fake engine and the headless Blender self-test use a synthetic fighter built in code. Goku is only used by owner-run live checks (owed).
- All edits go through `workbench_core` (`--wb-call` / MCP / the serve socket); the add-on never writes `gameplay.json`, `moves/*`, the fidelity ledger or built package output.
- The game workbench mode stays inert unless enabled, is never active online, and never touches hashed or rollback state. `MELEE_WB_HEADLESS` is honoured only inside the workbench scene.
- `wb.render` is frozen: kept registered, documented debug-only, no further work. The Qt `render_view`/`set_camera`/`set_overlays` commands stay registered (MCP compatibility) and are described as debug-only.
- Launcher strings follow the bilingual rule: every user-visible string is `t("English", "Spanish")` (new strings may be `t("English", "English")`); `tools/release/launcher/check_qt_strings.py` and the CTest `launcher_qt_strings` must pass. The add-on's own strings are English only (Blender UI), kept in one `STRINGS` dict in `props.py` so they can be translated later.
- Branches: workspace changes on `ws/geno-workbench`; game changes on `agent/geno-workbench` (worktree `worktrees/geno-workbench`). Never edit other worktrees. No push.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Game builds use `tools/port/build.sh` (bridge fixpoint; never raw clang). Netplay is not involved; any local server/socket test binds `127.0.0.1`.
- **Codex rule:** Codex currently cannot run a shell. Tasks marked `Codex-OK` are written without running code; each ends with a "Reviewer verifies" block of exact commands for a Claude reviewer. Tasks marked `Claude-only` need a build or a game run.
- Anything that must be seen on screen or timed in a game nobody watched is reported "owed", never "done".

## Review Focus

Failure modes the spec implies but its tests do not name. Each has a pinned test in the owning task.

1. **Engine or server gone mid-session** (engine killed, socket dropped, server not started, a reply that never comes): every add-on operator returns to Blender within its timeout, shows the error in the panel status line, and leaves the scene as it was; Blender never hangs. Pinned: Task 4 (`test_timeout_does_not_hang`, `test_dropped_socket_is_wberror`), Task 8 (selftest step "server killed").
2. **Skeleton mismatch** (a joint with no Blender bone, a Blender bone with no joint, renamed `.001` bones, a synthesized joint): the pose applies the mapped bones, reports the unmapped counts, and **refuses to calibrate** below 80 percent of non-synthesized joints mapped rather than pose garbage. Pinned: Task 3 (`test_unmapped_report`, `test_suffix_and_case_tolerant`), Task 7.
3. **Old engine without matrices** (`frame_info` schema 1: bone positions only): a clear "engine too old: no bone matrices (schema 2 needed)" error, never a silently wrong pose. Pinned: Task 3 (`test_schema1_rejected`).
4. **Facing and mirroring**: the fighter faces left (-X) as often as right; a joint matrix with negative determinant (mirrored scale) must not be turned into a pose; positions must still match after a facing flip. Pinned: Task 3 (`test_facing_flip_roundtrip`, `test_mirrored_joint_is_skipped`), Task 7 selftest runs both facings.
5. **Stale source after an edit**: `edit_hitbox` changes source only; the engine keeps the old hitbox until `rebuild` + `reload`. The panel must show "stale: rebuild needed" after an edit and clear it only after a successful rebuild+reload, and must not show the old hitbox as if it were the edit. Pinned: Task 9 (`test_edit_marks_stale_until_reload` against the fake engine).

---

## Spec gaps found while planning (the plan assumes the recommendation; flagged in the report)

- **R-a `frame_info` has positions, not matrices.** The game's `gw_Wb_FrameJson` writes `bones[{joint,parent,pos}]` only. Posing an armature "exactly" needs rotation (and scale). Plan: Task 1 adds `schema:2` with a per-bone `mtx` (12 floats, row-major 3x4 world matrix, read from `HSD_JObj.mtx` the same way `pos` is).
- **R-b No root/facing/model-space definition.** The live `compare_hitboxes.py` run showed DIFF 57.8 at frame 10 because `wb` coordinates are world and `check_hitbox_positions.py` poses are model-local. Plan: `frame_info` reports `root {joint, mtx, pos, facing}`; the transform is defined once in `wbspace.world_to_model` (model space = the local frame of the root/TopN joint) and used by the add-on, `compare_hitboxes.py` and the tests. Whether model space also needs the plan's `scale` is measured in Task 11 and recorded, not guessed.
- **R-c ECB is two points.** Only bottom/top are in the JSON; the LAB exposes left/right (`LAB_F_ECB_LEFT_X/Y`, `RIGHT`). Task 1 adds `ecb.left/right` so the diamond is real.
- **R-d No rest/bind pose from the engine.** Joint frames in the engine and bone frames in Blender differ by a fixed per-bone rotation (glTF importer bone orientation, the artist exporter's bone axes). Plan: calibrate once per rig by comparing the engine at a reference frame with the same pose in Blender (default: `Wait`, engine frame 1 vs action frame 0), see `wbspace.calibrate_offsets`. Alternative if calibration proves fragile: have the engine report bind matrices (`wb.rest_info`). Decision 2.
- **R-e The existing MCP socket treats every call as author `agent` with forced proposals and refuses `undo/accept/reject`.** The add-on is the owner's hands. Plan: `McpServer::setAuthor("human")` for the add-on/hub listener (apply directly, history author `human`), stdio `--mcp` for agents stays `agent`. Decision 1.
- **R-f `--wb-call` is stateless** (a new `Session` per process). Per-frame stepping through it would re-read the project every call. Plan: `gd-melee-launcher --serve` (persistent session, prints its port) and the hub's own listener; `--wb-call` stays as the offline fallback (`CliClient`) for list/check/edit.
- **R-g Project art paths.** `workbench.json` has `plan_abs` but nothing that names the artist `.blend`/`.glb`. Plan: optional `art_blend` / `art_glb` (names/paths only, no data), read like `plan_abs`.
- **R-h Inactive hitboxes are not in `frame_info`** (only active hits, `active` always true). v1 draws active hitboxes; the Hitbox panel lists source frame ranges from `list_hitboxes`. Ghost spheres for inactive boxes are out of scope.
- **R-i Add-on location and Blender discovery.** The add-on lives in the repo (`tools/blender/geno_workbench`), not in the release zip. "Open in Blender" finds it from the project's nearest `.git` ancestor (the rule `window.cpp` already uses for `mods_dir`) and finds Blender via the launcher setting `blender_exe`, then `GW_BLENDER`, then `PATH`.
- **R-j `wb.render` leftovers** in commit `ee3807daa` are mixed with the data fix `ScriptGame_WbPrepare`. Task 1 keeps the data part and adds a regression check; separating the commits is Decision 3.
- **R-k Headless engine** (owner addition): `MELEE_WB_HEADLESS=1`, Task 2.

---

## File Structure

### Workspace repo (branch `ws/geno-workbench`)

Add-on package `tools/blender/geno_workbench/` (next to the existing `gd_mission` add-on):

| File | Responsibility | bpy? |
|---|---|---|
| `wbspace.py` | the coordinate contract: engine<->Blender, 3x4 -> 4x4, affine inverse, `world_to_model`, frame_info schema checks, calibration math | no |
| `shapes.py` | sphere/capsule/diamond/floor geometry and `overlay_geometry(info, opts)` (all Blender-space) | no |
| `rigmap.py` | `plan.json` -> joint index to bone name map, mapping report, parent-first order | no |
| `client.py` | `McpClient` (TCP JSON-RPC lines), `CliClient` (`--wb-call`), `WbError` | no |
| `fake_engine.py` | synthetic fighter + frame provider + threaded fake workbench server | no |
| `launch.py` | find launcher/Blender, build argv for `--serve`, `--wb-call`, Blender; parse `WB_SERVE port=N` | no |
| `api.py` | `WbSession`: client + rows + current frame + jointmap + calibration + stale flag; the surface agents call through the Blender MCP | no (takes callbacks) |
| `rig.py` | load the fighter's rig+mesh (`.blend` append or `.glb` import), find armature | yes |
| `pose.py` | calibrate, apply matrices, `verify_pose` numeric check | yes |
| `overlays.py` | collection + reused objects, writes `overlay_geometry` to meshes | yes |
| `props.py` | `PropertyGroup`, `STRINGS` | yes |
| `operators.py` | `geno_wb.*` operators, modal play, coalesced scrub timer | yes |
| `panels.py` | N-panel "Geno" tab: Connect, Fighter, Timeline, Problems, Hitbox | yes |
| `__init__.py`, `bootstrap.py` | `bl_info`/register; `blender --python bootstrap.py -- --project P --port N` | yes |
| `selftest.py` | headless end-to-end test against the fake engine | yes |
| `README.md` | install, headless test, agent recipes | |
| `tests/` | `test_wbspace.py`, `test_shapes.py`, `test_rigmap.py`, `test_client.py`, `test_fake_engine.py`, `test_launch.py`, `test_calibrate.py`, `conftest.py` | |

Other workspace files: `tools/workbench/frame_info_diff.py` + `test_frame_info_diff.py`, `tools/workbench/run_blender_selftest.py` + test, `tools/workbench/compare_hitboxes.py` (modify), `tools/workbench/mcp_smoke.py`, `tools/workbench/acceptance.md`, `docs/workbench.md`, `ports/goku-xv2/workbench.json` (modify), `tools/CLAUDE.md`, `tools/blender/README.md`.

Qt (`tools/release/launcher/qt/workbench/` unless noted): modify `mcp_server.h/.cpp` (author), `workbench_main.cpp` (`--serve`), `engine_link.h/.cpp` (headless env), `project.h/.cpp` (art keys), `workbench_window.h/.cpp` + `CMakeLists.txt` (hub, remove viewport), `commands_view.cpp` (debug-only descriptions); create `hub_panel.h/.cpp`, `blender_launch.h/.cpp`, tests `blender_launch_test.cpp`, extend `mcp_test.cpp`, `engine_link_test.cpp`, `geno_data_test.cpp`/project test, `ui_test.cpp`; delete `viewport.h/.cpp`; `../window.cpp` for the `blender_exe` setting.

### Game repo (branch `agent/geno-workbench`)

`pc/platform/gw_workbench.h/.c` (schema 2 writer, headless gate), `pc/gameworld/script_game.c` (`ScriptGame_JointMtx`, root/facing/ECB accessors), `pc/platform/gw_script.c` (read frame, headless `wb.render` error), `pc/platform/main.c` + `gw_runtime.c` (headless boot), `pc/tests/workbench_test.c`, `pc/tests/workbench_check.lua`, `pc/tests/workbench_headless_check.lua`.

## Task Index and Parallelism

| # | Task | Repo | Who | Group |
|---|---|---|---|---|
| 1 | frame_info schema 2 (matrices, root, facing, ECB sides); keep data fix; freeze render docs | G | Claude-only | B |
| 2 | True headless engine `MELEE_WB_HEADLESS=1` | G | Claude-only | B (after 1) |
| 3 | `wbspace.py`, `shapes.py`, `rigmap.py` + tests | W | Codex-OK | A |
| 4 | `client.py`, `fake_engine.py`, `launch.py` + tests | W | Codex-OK | A |
| 5 | Qt: `--serve`, human author, headless env, project art keys | W | Claude-only (build) | C |
| 6 | Add-on shell: `props`, `api`, `__init__`, `bootstrap`, `operators` connect/rows | W | Codex-OK (needs 3,4) | D |
| 7 | Rig load, calibration, pose apply, numeric check | W | Codex-OK (needs 3,6) | D |
| 8 | Overlays + headless self-test + runner | W | Codex-OK for code, Claude runs (needs 4,6,7) | E |
| 9 | Timeline, move picker, problems, hitbox edit, stale flow, panels | W | Codex-OK (needs 6,7,8) | E |
| 10 | `compare_hitboxes.py` coordinate fix + `frame_info_diff.py` | W | Codex-OK (needs 1,3) | F |
| 11 | Qt hub: remove viewport, "Open in Blender" | W | Claude-only (build) | G (needs 5,8) |
| 12 | Goku `workbench.json`, MCP smoke, acceptance, docs (updated old Task 17) | W | Claude | last |

Parallel groups: **A** = 3 and 4 (disjoint files). **B** = 1 then 2 (game lane, own worktree, runs beside everything else). **C** = 5 (Qt lane) beside A and B. **D** = 6 and 7 after A (6 first; 7 only needs `props.py` from 6, so start it once 6's first commit lands). **E** = 8 and 9 after D (8 owns `overlays.py` and `selftest.py`, 9 owns `operators.py` additions and `panels.py`; they share `api.py` read-only). **F** = 10 after 1+3, any time. **G** = 11 after 5 and 8. 12 last.

---

### Task 1: frame_info schema 2 and data/render separation  (Game repo, Claude-only)

**Files:**
- Modify: `pc/platform/gw_workbench.h`, `pc/platform/gw_workbench.c` (`GwWbBone`, `GwWbFrame`, `gw_Wb_FrameJson`)
- Modify: `pc/gameworld/script_game.c` (new `ScriptGame_JointMtx`, `ScriptGame_FighterFacing` if no accessor exists)
- Modify: `pc/platform/gw_script.c` (`gs_wb_read_frame`, ~line 6961)
- Test: `pc/tests/workbench_test.c`, `pc/tests/workbench_check.lua`

**Interfaces:**
- Produces (JSON, `frame.json` via `@path`; all earlier fields unchanged, additions in bold):

```json
{"schema":2,"row":"jab","motion":57,"frame":6,
 "bones":[{"joint":1,"parent":0,"pos":{"x":0,"y":0,"z":0},"mtx":[1,0,0,0, 0,1,0,0, 0,0,1,0]}],
 "root":{"joint":0,"pos":{"x":-12.5,"y":0,"z":0},"facing":1,"mtx":[0,0,1,-12.5, 0,1,0,0, -1,0,0,0]},
 "hitboxes":[{"slot":0,"joint":8,"active":true,"offset":{},"radius":2.8,"world":{}}],
 "hurtboxes":[{"joint":4,"a":{},"b":{},"radius":1.0}],
 "ecb":{"bottom":{"x":0,"y":0},"top":{"x":0,"y":9},"left":{"x":-3,"y":4.5},"right":{"x":3,"y":4.5}},
 "floorY":0,"lowestY":0}
```

`mtx` = the joint's world matrix `HSD_JObj.mtx[3][4]` flattened row-major (the same matrix whose column 3 is `pos`). `root.joint` = the first joint whose `parent == -1`; `root.mtx` is that joint's `mtx`; `root.pos` = its column 3; `root.facing` = +1/-1 from the fighter's facing direction. Keys of the old schema are untouched, so the already-built C++ `FrameInfo::fromJson` keeps working (it ignores unknown keys; Task 5 adds nothing there, the add-on reads the raw JSON).
- Consumes: nothing. Later tasks (3, 10) read `schema`, `bones[].mtx`, `root`.

- [ ] **Step 1: Failing native test.** In `pc/tests/workbench_test.c` extend the existing frame-JSON test: fill a `GwWbFrame` with two bones whose `m[12]` are known, `root_m[12]`, `facing=-1`, `ecb_lx/ly/rx/ry`; assert the output contains `"schema":2`, `"mtx":[`, `"root":{"joint":0`, `"facing":-1`, `"left":{"x":-3`, and that `gw_Wb_FrameJson` still returns `-1` for `nbones > 160`. Also assert the buffer size needed for 160 bones with matrices fits `char json[65536]` (160 bones * ~260 bytes = ~42 KB): compute the length of a full frame in the test and assert `< 60000`.
- [ ] **Step 2: Run, expect FAIL** — `tools/port/native_test.sh workbench` (case exists from the earlier plan's Task 12). Expected: assertion failures for the missing keys.
- [ ] **Step 3: Implement.** Add `float m[12];` to `GwWbBone`; `int root_joint; float root_m[12]; int facing; float ecb_lx, ecb_ly, ecb_rx, ecb_ry;` to `GwWbFrame`. In `gw_Wb_FrameJson` write `"schema":2,` first, `,"mtx":[%g,...]` after `pos`, the `root` object before `hitboxes`, `left`/`right` in `ecb` (use `wb_number` for every value). In `script_game.c` add

```c
/* Row-major 3x4 world matrix of joint i, as HSD_JObjSetupMatrix left it (read-only, like ScriptGame_JointF). */
void ScriptGame_JointMtx(int slot, int i, float out[12]);
```
reading `j->mtx[r][c]` for r<3, c<4 (zeros for a missing joint). Mirror every place `ScriptGame_WbTargetJoint` is declared and bridged: `grep -rn "WbTargetJoint" pc tools` lists them (declaration in `gw_script.c` line ~487 as `gw_ScriptGame_*`, definition in `script_game.c`, any build list). Facing: find the fighter facing accessor with `grep -n "facing" pc/gameworld/script_game.c | head` (`fp->facing_dir`); expose it as `gw_ScriptGame_FighterF(0, SF_FACING)` if an index exists, else add `ScriptGame_FighterFacing(int slot)` returning +1/-1. In `gs_wb_read_frame` fill `b->m` for every bone, `f->root_joint`/`root_m`/`facing` from the first bone with `parent == -1`, and the four ECB side values with `LAB_F_ECB_LEFT_X/Y`, `LAB_F_ECB_RIGHT_X/Y` (`pc/gameworld/script_lab.h` lines 21-28).
- [ ] **Step 4: Data fix regression + freeze docs.** Keep `ScriptGame_WbPrepare` and its call at `gw_script.c` ~9676 (`if (gw_Wb_Enabled()) gw_ScriptGame_WbPrepare(0);`) exactly as in `ee3807daa`. Add to `workbench_check.lua` a check that after `wb.load` + `wb.frame{motion=<wait>, frame=1}` the `frame.json` bone span (max y minus min y over `bones[].pos`) is greater than 5 (the Entry squash bug measured 0.15), reading the file the reply names. Add a header comment to `gw_workbench.h`: `wb.render, wb.camera presets and view.json are FROZEN (debug only). The viewer is the Blender add-on (docs/superpowers/specs/2026-10-09-geno-workbench-design.md, Revision 1). Do not extend.` Do not edit any render code.
- [ ] **Step 5: Build and run.** `tools/port/build.sh` (use `tools/port/agent_new.sh` build root of this lane), then `tools/port/native_test.sh workbench` -> expected `PASS`. Windowed live check (on screen): `MELEE_SCENE="mode=workbench;p1=geno:goku-xv2/hu;stage=fd" MELEE_CONSOLE_PORT=51726 MELEE_WB_DIR=<dir>` then `python tools/port/gd_prompt.py` style calls (`= wb.load("goku-xv2",0)`, `= wb.row({motion=<wait>})`, `= wb.frame({motion=<wait>,frame=1})`, `= wb.frame_info()`); `grep -c '"mtx"' <dir>/frame.json` -> equals the bone count; `grep -o '"schema":2' <dir>/frame.json` -> one hit. Verify in the exe: `grep -a '"schema":2' _build/melee-pc.exe` (string present).
- [ ] **Step 6: Commit** (game worktree) — `git add pc && git commit -m "workbench: frame_info schema 2 (bone matrices, root, facing, ECB sides); render frozen"`.

**Reviewer verifies:** `git -C worktrees/geno-workbench diff --stat HEAD~1`; the frame.json from Step 5 pasted in the lane report; `git -C worktrees/geno-workbench diff HEAD~1 -- pc/platform/gw_script.c` shows no change in the `gs_wb_render*` functions.

---

### Task 2: True headless workbench engine  (Game repo, Claude-only)

**Definition (owner decision 2026-10-10; supersedes the "no window" wording below): headless = the Dawn null backend, the window placed offscreen (`MELEE_WINDOW_X/Y=30000`), no GPU device. A no-window path is out of scope (Dawn still wants an HWND surface; `SDL_HideWindow` made the null-backend present loop spin). Where this task says "no window", read "offscreen window, no GPU device"; the process check is therefore not `MainWindowHandle == 0` but the absence of `aurora backend` GPU init lines and no visible window.**

**Files:**
- Modify: `pc/platform/gw_workbench.h/.c` (`gw_Wb_Headless()`), `pc/platform/main.c` (boot path), `pc/platform/gw_runtime.c` and the GX/texture/model shims found in Step 1, `pc/platform/gw_script.c` (`l_wb_render` error)
- Create: `pc/tests/workbench_headless_check.lua`
- Test: `pc/tests/workbench_test.c`

**Interfaces:**
- Produces: env `MELEE_WB_HEADLESS=1` (honoured only when the scene gate `gw_Wb_Enabled()` is on); `int gw_Wb_Headless(void)`; log line `workbench: headless (no GPU device: Dawn null backend; window offscreen)`; `wb.render` raises the Lua error `wb.render is unavailable in headless mode (MELEE_WB_HEADLESS=1); use the Blender viewer or run windowed`.
- Consumes: Task 1's `frame_info` schema 2 for the equivalence check.

Context for the implementer: `--test` already runs the engine without a window or GPU (`main.c` ~313-331: `gw_hang_pause(4); gw_apply_fixups(); gw_mem_init();` before `aurora_initialize`), and the draw path has `gw_gx_suppress_draws`. The headless workbench is the same idea but with the scene running: console socket live, `wb.*` data calls working, fighter loaded and animating, hitboxes computed.

- [ ] **Step 1: Find every GPU assumption (write the list into the commit message and a comment block in `gw_workbench.c`).** Run and read:

```bash
grep -n "aurora_initialize\|aurora_update\|aurora_begin_frame\|aurora_end_frame\|gw_frame_init\|gw_gx_init_render_modes\|gw_pcache_guard_run\|AuroraSetViewportPolicy\|gw_set_window\|gw_window_drag_install" pc/platform/main.c pc/platform/gw_*.c pc/platform/shim_vi.c | head -60
grep -n "gw_gx_suppress_draws" -r pc | head -20
grep -n "Screenshot\|GXInitTexObj\|GXLoadTexObj\|GXBeginDisplayList\|aurora::gfx" pc/platform/shim_gx.c pc/platform/shim_vi.c | head -40
```

For each hit decide gate / no-op / leave. Known classes to cover: (a) Aurora/Dawn init, window, swapchain, pipeline cache (`main.c`); (b) per-frame present/`aurora_begin_frame`/`end_frame` and `gw_frame_init`'s driver (the logic loop must still be ticked: see how `gw_test_run_all` and the frame driver call game logic without presenting); (c) texture and model upload (`GXInitTexObj`, display-list creation from `HSD_*` loaders must not call into Aurora; return success without a GPU object); (d) screenshot (`gw_Wb_CaptureScreenshot`, `gw_Screenshot`) and the render poll (`gs_wb_render_poll`); (e) the loading-screen wait on pipeline warm-up (`main.c` ~469 comment) and the vsync/pacing code (`gw_pace_field`): headless pacing is wall-clock 60 Hz without a present, or uncapped with `MELEE_TURBO=1`.
- [ ] **Step 2: Failing native test.** In `workbench_test.c`: `gw_Wb_SetEnabled(0)` then env `MELEE_WB_HEADLESS=1` -> `gw_Wb_Headless() == 0` (gate required); `gw_Wb_SetEnabled(1)` + env set -> `1`; env unset -> `0`. Run `tools/port/native_test.sh workbench` -> FAIL (symbol missing).
- [ ] **Step 3: Implement the gate and boot path.** `gw_Wb_Headless()` = `gw_Wb_Enabled() && getenv("MELEE_WB_HEADLESS") == "1"`. The scene gate is published after `main.c` creates the window today (`gw_sl_publish_workbench`, `gw_runtime.c` ~2392), so read the scene string early: in `main.c`, before `aurora_initialize`, call a new `gw_Wb_PreScan(argc, argv)` that sets a static `headless_requested` when `MELEE_WB_HEADLESS=1` and `MELEE_SCENE` contains `mode=workbench` (or `--workbench` is present); `gw_Wb_Headless()` returns that static ANDed with the scene gate once published. When headless: skip `aurora_initialize`, `gw_window_*`, `AuroraSetViewportPolicy`, `gw_pcache_guard_run`, `gw_gx_init_render_modes` if it touches the GPU (Step 1 decides), keep `gw_apply_fixups(); gw_mem_init();`, set `gw_gx_suppress_draws` for the whole run, and drive the same logic loop the windowed path uses without a present. `l_wb_render` returns the error text above when `gw_Wb_Headless()`.
- [ ] **Step 4: Scripted check `workbench_headless_check.lua`.** Runs under `MELEE_WB_HEADLESS=1`: `wb.load`, `wb.row`, `wb.frame` for `wait`, `jab`, `dair` (dair with `lift=40`), reading `wb.frame_info()` after each, asserting `schema == 2`, bone count > 20, bone span > 5, `pcall(wb.render, {})` fails with the text `unavailable in headless`, prints `HEADLESS_CHECK OK`.
- [ ] **Step 5: Build, run headless and windowed, compare.** `tools/port/build.sh`; then twice with identical `MELEE_SCENE="mode=workbench;p1=geno:goku-xv2/hu;stage=fd"`, `MELEE_TURBO=1`, a distinct `MELEE_CONSOLE_PORT` and `MELEE_WB_DIR` per run: once with `MELEE_WB_HEADLESS=1`, once windowed (on screen). In each, for rows `wait`, `jab`, `dair` and frames 1, 6, 12, save `frame.json` as `<run>/<row>-<frame>.json`. Compare with `tools/workbench/frame_info_diff.py` from Task 10 (until it lands, a one-off `python - <<EOF` that loads two JSON files and prints the max abs difference over `bones[].pos`, `bones[].mtx`, `hitboxes[].world`; tolerance 1e-3). Evidence required in the report:
  `grep -c "aurora backend" <log>` -> `8` (null backend) headless vs `1` windowed (the GPU-device init line is the one that disappears); `grep "workbench: headless" <log>` -> one line; no GPU device is created (log shows the Dawn null backend) and the window is offscreen, not absent; the diff output `max_abs=<value> (tol 1e-3) rows=3 frames=3`.
- [ ] **Step 6: Commit** — `git add pc && git commit -m "workbench: MELEE_WB_HEADLESS true headless data engine (no Aurora/GPU); wb.render errors clearly"`.

**Reviewer verifies:** the headless log (Dawn null backend, offscreen window, no GPU device), the diff table, and `git diff --stat` touching only the files listed. Timing and visual parity of a *windowed* run are unchanged: owed to a run with a monitor (`MELEE_WB_HEADLESS` unset must be byte-identical behaviour; the native test covers the gate only).

---

### Task 3: `wbspace.py`, `shapes.py`, `rigmap.py`  (Workspace repo, Codex-OK)

**Files:**
- Create: `tools/blender/geno_workbench/wbspace.py`, `shapes.py`, `rigmap.py`, `tests/conftest.py`, `tests/test_wbspace.py`, `tests/test_shapes.py`, `tests/test_rigmap.py`, `tests/test_calibrate.py`
- Modify: none (the package `__init__.py` arrives in Task 6; tests import modules directly via `conftest.py`'s `sys.path` insert)

**Interfaces:**
- Produces (`wbspace`):
  - `class SchemaError(ValueError)`
  - `Mat4 = tuple of 4 tuples of 4 floats`
  - `mat4_from_12(m: Sequence[float]) -> Mat4`
  - `mul(a: Mat4, b: Mat4) -> Mat4`, `transpose(a)`, `affine_inverse(a) -> Mat4` (raises `ValueError` when the 3x3 determinant is < 1e-12 in magnitude), `det3(a) -> float`
  - `apply_point(m: Mat4, p: Sequence[float]) -> tuple[float,float,float]`
  - `to_blender_point(p) -> (x, -z, y)`, `from_blender_point(b) -> (bx, bz, -by)`
  - `to_blender_matrix(m: Mat4) -> Mat4` (`C4 @ m @ C4^T`)
  - `world_to_model(root_m: Mat4, p) -> tuple` (`apply_point(affine_inverse(root_m), p)`)
  - `check_schema(info: dict) -> None` (raises `SchemaError` with the text `engine too old: no bone matrices (schema 2 needed)` when `schema < 2` or a bone lacks `mtx`)
  - `bone_matrices(info) -> dict[int, Mat4]` (engine world, keyed by joint index; calls `check_schema`)
  - `root_matrix(info) -> Mat4`
  - `calibrate_offsets(engine_rest: dict[int, Mat4], blender_rest: dict[int, Mat4], root_joint: int) -> Calibration` where both dicts are in **Blender world space** and keyed by joint index; `Calibration(w0: Mat4, k: dict[int, Mat4], scale: float)`
  - `target_matrix(engine_blender_m: Mat4, k: Mat4) -> Mat4` (`engine_blender_m @ k`)
  - `is_mirrored(m: Mat4) -> bool` (`det3 < 0`)
- Produces (`shapes`): `sphere_mesh(c, r, seg=12, rings=4)`, `capsule_mesh(a, b, r, seg=12, rings=4)` -> `(verts: list[tuple], faces: list[tuple[int,...]])`; `diamond(left, bottom, right, top)` -> `(verts, edges)`; `floor_quad(cx, cz_b, y_b, half)`; `overlay_geometry(info: dict, opts: dict | None) -> dict` with keys `hit: list[{slot, active, verts, faces}]`, `hurt: list[{verts, faces}]`, `ecb: {verts, edges}`, `floor: {verts, faces}`, all in **Blender space**, using `wbspace.to_blender_point`. `opts`: `seg`, `rings`, `floor_half` (default 30).
- Produces (`rigmap`): `class JointMap(by_index: dict[int,str], skipped_synth: list[int], missing_bones: list[int], unmapped_bones: list[str])` with `.coverage() -> float` (mapped / non-synth joints) and `.order() -> list[int]` (parent-first joint indices); `load_plan(path) -> dict`; `build_joint_map(plan: dict, bone_names: Iterable[str], aliases: dict[str,str] | None = None) -> JointMap`.
- Consumes: the `plan.json` shape seen in `_build/goku-xv2/author-source/package/mods/goku-xv2/files/plan.json`: `joints: [{index, name, parent, synth}]` (keys also include `roles`, `role_joint`, `scale`).

- [ ] **Step 1: Write the failing tests.**

`tests/conftest.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

`tests/test_wbspace.py`:
```python
import math
import pytest
import wbspace as W

I12 = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]


def roty(deg, t=(0, 0, 0)):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return W.mat4_from_12([c, 0, s, t[0], 0, 1, 0, t[1], -s, 0, c, t[2]])


def close(a, b, eps=1e-9):
    return all(abs(x - y) <= eps for x, y in zip(a, b))


def test_point_axes():
    assert W.to_blender_point((1, 2, 3)) == (1, -3, 2)
    assert W.from_blender_point(W.to_blender_point((1, 2, 3))) == (1, 2, 3)


def test_rotation_converts_to_blender_axes():
    # engine R_y(+90) maps forward +Z to +X; in Blender forward is -Y.
    b = W.to_blender_matrix(roty(90))
    assert close(W.apply_point(b, (0, -1, 0)), (1, 0, 0))


def test_affine_inverse_roundtrip():
    m = roty(33, (4, -2, 7))
    prod = W.mul(m, W.affine_inverse(m))
    for i in range(4):
        for j in range(4):
            assert abs(prod[i][j] - (1.0 if i == j else 0.0)) < 1e-9


def test_singular_inverse_raises():
    with pytest.raises(ValueError):
        W.affine_inverse(W.mat4_from_12([0] * 12))


def test_world_to_model_undoes_root():
    root = roty(90, (-12.5, 0, 0))
    world = W.apply_point(root, (0, 5, 3))
    assert close(W.world_to_model(root, world), (0, 5, 3))


def test_facing_flip_roundtrip():
    for facing in (1, -1):
        root = roty(90 * facing, (7, 0, 0))
        local = (1.5, 8.0, -2.0)
        world = W.apply_point(root, local)
        assert close(W.world_to_model(root, world), local)


def test_schema1_rejected():
    info = {"bones": [{"joint": 1, "parent": 0, "pos": {"x": 0, "y": 0, "z": 0}}]}
    with pytest.raises(W.SchemaError, match="schema 2 needed"):
        W.check_schema(info)
    with pytest.raises(W.SchemaError):
        W.bone_matrices({"schema": 2, "bones": [{"joint": 1, "parent": 0}]})


def test_bone_matrices_and_root():
    info = {"schema": 2, "bones": [{"joint": 3, "parent": 0, "mtx": I12}],
            "root": {"joint": 0, "mtx": I12}}
    assert W.bone_matrices(info)[3][0][0] == 1
    assert W.root_matrix(info)[3] == (0, 0, 0, 1)


def test_mirrored_joint_is_detected():
    assert W.is_mirrored(W.mat4_from_12([-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]))
    assert not W.is_mirrored(W.mat4_from_12(I12))
```

`tests/test_calibrate.py` (pure; proves the K math with a fixed per-bone frame offset and a world move):
```python
import math
import wbspace as W


def rot(axis, deg, t=(0, 0, 0)):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    if axis == "x":
        r = [1, 0, 0, t[0], 0, c, -s, t[1], 0, s, c, t[2]]
    elif axis == "y":
        r = [c, 0, s, t[0], 0, 1, 0, t[1], -s, 0, c, t[2]]
    else:
        r = [c, -s, 0, t[0], s, c, 0, t[1], 0, 0, 1, t[2]]
    return W.mat4_from_12(r)


def near(a, b, eps=1e-9):
    return all(abs(a[i][j] - b[i][j]) < eps for i in range(4) for j in range(4))


def test_calibration_recovers_bone_frame_offsets():
    # local bone frames L (model space), fixed Blender-only offsets R, world placements W0/W1
    L0 = {1: rot("z", 0), 2: rot("y", 20, (0, 0, 5)), 3: rot("x", -35, (1, 0, 8))}
    R = {1: rot("x", 90), 2: rot("z", 15), 3: rot("y", -50)}
    W0 = rot("z", 90, (10, -3, 0))
    engine_rest = {j: W.mul(W0, L0[j]) for j in L0}
    blender_rest = {j: W.mul(L0[j], R[j]) for j in L0}
    cal = W.calibrate_offsets(engine_rest, blender_rest, root_joint=1)
    assert near(cal.w0, W0)
    L1 = {1: rot("z", 0), 2: rot("y", 55, (0, 0, 5)), 3: rot("x", 10, (1, 0, 8))}
    W1 = rot("z", -90, (-4, 2, 0))
    for j in L1:
        engine = W.mul(W1, L1[j])
        assert near(W.target_matrix(engine, cal.k[j]), W.mul(W1, W.mul(L1[j], R[j])))


def test_scale_is_reported():
    L = {1: rot("z", 0)}
    big = tuple(tuple(v * 2 if i < 3 and j < 3 else v for j, v in enumerate(row)) for i, row in enumerate(rot("z", 0)))
    cal = W.calibrate_offsets({1: big}, {1: L[1]}, root_joint=1)
    assert abs(cal.scale - 2.0) < 1e-9
```

`tests/test_shapes.py`:
```python
import shapes as S
import wbspace as W


def test_sphere_counts_and_bounds():
    v, f = S.sphere_mesh((0, 0, 0), 2.0, seg=12, rings=4)
    assert len(v) == 2 + 7 * 12
    xs = [p[0] for p in v]; zs = [p[2] for p in v]
    assert abs(max(xs) - 2.0) < 1e-6 and abs(min(zs) + 2.0) < 1e-6
    assert all(0 <= i < len(v) for face in f for i in face)


def test_capsule_bounds():
    v, f = S.capsule_mesh((0, 0, 0), (0, 0, 5), 1.0, seg=12, rings=4)
    assert len(v) == 2 + 2 * 4 * 12
    zs = [p[2] for p in v]; xs = [p[0] for p in v]
    assert abs(min(zs) + 1) < 1e-6 and abs(max(zs) - 6) < 1e-6 and abs(max(xs) - 1) < 1e-6


def test_capsule_degenerate_equals_sphere():
    assert len(S.capsule_mesh((1, 1, 1), (1, 1, 1), 1.0)[0]) == len(S.sphere_mesh((1, 1, 1), 1.0)[0])


def test_overlay_geometry_is_in_blender_space():
    info = {"schema": 2, "bones": [], "hitboxes": [{"slot": 1, "active": True, "world": {"x": 1, "y": 2, "z": 3}, "radius": 2.0}],
            "hurtboxes": [{"a": {"x": 0, "y": 0, "z": 0}, "b": {"x": 0, "y": 4, "z": 0}, "radius": 1.0}],
            "ecb": {"bottom": {"x": 0, "y": 0}, "top": {"x": 0, "y": 9}, "left": {"x": -3, "y": 4.5}, "right": {"x": 3, "y": 4.5}},
            "floorY": 0.0, "root": {"pos": {"x": 5, "y": 0, "z": 0}}}
    g = S.overlay_geometry(info, {})
    hit = g["hit"][0]
    assert hit["slot"] == 1 and hit["active"]
    cx = sum(p[0] for p in hit["verts"]) / len(hit["verts"])
    cy = sum(p[1] for p in hit["verts"]) / len(hit["verts"])
    cz = sum(p[2] for p in hit["verts"]) / len(hit["verts"])
    assert abs(cx - 1) < 0.2 and abs(cy + 3) < 0.2 and abs(cz - 2) < 0.2   # (1,2,3) -> (1,-3,2)
    assert len(g["hurt"]) == 1 and len(g["ecb"]["verts"]) == 4 and len(g["ecb"]["edges"]) == 4
    assert all(abs(p[2] - 0.0) < 1e-9 for p in g["floor"]["verts"])        # floorY 0 -> Blender z 0
    zs = [p[2] for p in g["ecb"]["verts"]]
    assert min(zs) == 0 and max(zs) == 9


def test_overlay_geometry_tolerates_missing_parts():
    g = S.overlay_geometry({"schema": 2}, {})
    assert g["hit"] == [] and g["hurt"] == [] and g["ecb"]["verts"] == []
```

`tests/test_rigmap.py`:
```python
import rigmap as R

PLAN = {"joints": [
    {"index": 0, "name": "TopN", "parent": None, "synth": True},
    {"index": 1, "name": "b_C_Base", "parent": 0, "synth": False},
    {"index": 2, "name": "b_C_Pelvis", "parent": 1, "synth": False},
    {"index": 3, "name": "b_R_Hand", "parent": 2, "synth": False},
]}


def test_exact_match_skips_synth():
    m = R.build_joint_map(PLAN, ["b_C_Base", "b_C_Pelvis", "b_R_Hand"])
    assert m.by_index == {1: "b_C_Base", 2: "b_C_Pelvis", 3: "b_R_Hand"}
    assert m.skipped_synth == [0] and m.coverage() == 1.0
    assert m.order() == [1, 2, 3]


def test_suffix_and_case_tolerant():
    m = R.build_joint_map(PLAN, ["b_c_base.001", "B_C_Pelvis", "b_R_Hand"])
    assert set(m.by_index) == {1, 2, 3}


def test_unmapped_report():
    m = R.build_joint_map(PLAN, ["b_C_Base", "Extra"])
    assert m.missing_bones == [2, 3] and m.unmapped_bones == ["Extra"]
    assert abs(m.coverage() - 1 / 3) < 1e-9


def test_alias_wins():
    m = R.build_joint_map(PLAN, ["Hand.R", "b_C_Base"], aliases={"b_R_Hand": "Hand.R"})
    assert m.by_index[3] == "Hand.R"


def test_load_plan_roundtrip(tmp_path):
    import json
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(PLAN))
    assert R.load_plan(str(p))["joints"][1]["name"] == "b_C_Base"
```

- [ ] **Step 2: Run, expect FAIL** — `python -m pytest tools/blender/geno_workbench/tests -q` -> `ModuleNotFoundError: No module named 'wbspace'`.
- [ ] **Step 3: Implement `wbspace.py`.** Required semantics (write straightforward stdlib code):
  - `C3 = ((1,0,0),(0,0,-1),(0,1,0))` embedded in a 4x4 `C4`; `to_blender_matrix(m) = mul(mul(C4, m), transpose(C4))`.
  - `affine_inverse`: invert the 3x3 by the adjugate; translation `-R^-1 t`; raise `ValueError("singular matrix")` when `abs(det) < 1e-12`.
  - `check_schema(info)`: `if info.get("schema", 1) < 2 or any("mtx" not in b for b in info.get("bones", []))` raise `SchemaError("engine too old: no bone matrices (schema 2 needed)")`.
  - `root_matrix`: from `info["root"]["mtx"]`, else `SchemaError("frame_info has no root")`.
  - `calibrate_offsets`: `w0 = engine_rest[root] @ inverse(blender_rest[root])`; for every joint present in both dicts, `k[j] = inverse(engine_rest[j]) @ w0 @ blender_rest[j]`; `scale = det3(w0) ** (1/3)` (use `abs(det)`); joints in only one dict are left out of `k`. Return a `Calibration` dataclass.
  - `is_mirrored(m) = det3(m) < 0`.
- [ ] **Step 4: Implement `shapes.py`.** Profile method: build a list of `(axial, radial)` points: bottom hemisphere `i=0..rings`, `theta = (pi/2) * i / rings`, `(-r*cos(theta), r*sin(theta))`; top hemisphere `(L + r*sin(theta), r*cos(theta))`; drop consecutive duplicates (this is what makes the sphere have `2 + (2*rings-1)*seg` vertices and the capsule `2 + 2*rings*seg`). A profile point with radial < 1e-9 becomes one vertex (pole), otherwise `seg` vertices around the axis using two unit vectors perpendicular to the axis (axis = normalized `b - a`, any perpendicular for a zero-length axis; use `(0,0,1)` for a zero-length capsule). Faces: quads between consecutive full rings, triangles at poles. `overlay_geometry`: positions from `wbspace.to_blender_point`; hit sphere at `world`, radius `radius`; hurt capsule from `a` to `b`; ECB diamond from `bottom, right, top, left` (engine x,y with z = `root.pos.z` or 0) mapped to Blender, edges `(0,1),(1,2),(2,3),(3,0)`; floor quad at `floorY` centred on `root.pos.x` with half-size `opts.get("floor_half", 30)`. Missing keys give empty lists.
- [ ] **Step 5: Implement `rigmap.py`.** Name normalisation `norm(n) = re.sub(r"\.\d{3}$", "", n).lower()`. Order of matching per non-synth joint: alias target (`aliases[joint_name]`), exact name, normalised name; first free bone wins, each bone used once. `missing_bones` = non-synth joint indices with no bone, `unmapped_bones` = bone names not used. `coverage` = mapped / max(1, non-synth count). `order()`: parent-first (sort mapped joints by depth through the plan's `parent` chain, ties by index).
- [ ] **Step 6: Run, expect PASS** — `python -m pytest tools/blender/geno_workbench/tests -q` -> all passed. Commit — `git add tools/blender/geno_workbench && git commit -m "geno_workbench: coordinate contract, overlay geometry, joint map (pure, tested)"`.

**Reviewer verifies:** `python -m pytest tools/blender/geno_workbench/tests -q` (expected: 24+ passed, 0 failed); `grep -rn "numpy\|import bpy\|mathutils" tools/blender/geno_workbench/wbspace.py tools/blender/geno_workbench/shapes.py tools/blender/geno_workbench/rigmap.py` -> no output.

---

### Task 4: Client, fake engine, launch helpers  (Workspace repo, Codex-OK)

**Files:**
- Create: `tools/blender/geno_workbench/client.py`, `fake_engine.py`, `launch.py`, `tests/test_client.py`, `tests/test_fake_engine.py`, `tests/test_launch.py`

**Interfaces:**
- Produces (`client`):
  - `class WbError(RuntimeError)`
  - `class McpClient(host="127.0.0.1", port=0, timeout=10.0)`: `connect() -> None`, `close()`, `call(tool: str, args: dict | None = None, timeout: float | None = None) -> dict` (returns the parsed JSON body of `content[0].text`; raises `WbError` for `isError`, JSON-RPC `error`, timeout, dropped socket), `tools() -> list[str]`. Constructor raises `ValueError` unless `host in ("127.0.0.1", "localhost", "::1")`.
  - `class CliClient(exe, project, extra=(), timeout=60.0)`: `call(tool, args=None) -> dict` runs `[exe, "--project", project, *extra, "--wb-call", tool, json.dumps(args or {})]`, parses the last stdout line as the envelope `{"ok":bool,"result"|"error"}`; raises `WbError` on `ok:false`, non-zero exit without envelope, or timeout.
- Produces (`fake_engine`):
  - `synthetic_plan() -> dict` (the `plan.json` shape, 9 joints, names `TopN, b_C_Base, b_C_Pelvis, b_C_Spine1, b_C_Chest, b_C_Head, b_R_Arm1, b_R_Arm2, b_R_Hand`, `synth` true only for joint 0)
  - `rest_world(plan) -> dict[int, Mat4]` (engine-space world matrices at the rest pose, root identity)
  - `synthetic_provider(row: str, frame: int, facing: int = 1, root_x: float = 0.0) -> dict` (a `schema:2` frame_info dict: bones with `mtx`, `root`, a hitbox `slot 0` on joint 8 active frames 5-8 for row `jab` and `dair`, 5 hurtboxes, ECB with four points, `floorY` 0, `lowestY`)
  - `class FakeWorkbench(provider=synthetic_provider, host="127.0.0.1", port=0)`: `start() -> int` (returns the bound port), `stop()`, attributes `.calls: list[tuple[str, dict]]`, `.stale: bool`, `.fail_next: str | None` (the next tool call replies `isError`), `.drop_after: int | None` (close the socket after that many calls). Tools implemented with the **real** reply shapes: `engine_status -> {"status": "running"}`, `engine_restart -> {"status": "running"}`, `list_rows -> {"rows":[{"name","motions","tag","clip","aerial","hitboxes"}]}` (rows `wait`, `jab`, `dair`), `load_row {row}`, `set_frame {frame}` and `play {frames, step}` returning the frame_info dict, `frame_info`, `list_hitboxes {row} -> {"hitboxes":[{"ordinal","line","slot","joint":"HAND_R","damage","size","x","y","z","angle","kbg","fkb","bkb","start_frame","end_frame"}]}`, `run_checks -> {"problems":[{"kind":"wrong_limb","row":"jab","message":"...","ordinal":0}],"engine":true}`, `suggest_hitbox_bone {row,ordinal} -> {"suggested":"HAND_R","current":"FOOT_R","scores":[]}`, `edit_hitbox` (sets `.stale = True`, returns `{"changed":true}`), `rebuild` and `reload` (set `.stale = False`).
- Produces (`launch`): `find_launcher(env=os.environ, root=None) -> str | None` (order: `GW_LAUNCHER`, `<root>/_build/**/gd-melee-launcher[.exe]` newest, PATH); `find_blender(env=os.environ, settings_value="") -> str | None` (order: `settings_value`, `GW_BLENDER`, PATH `blender`); `serve_argv(exe, project, engine_exe="", headless=True) -> list[str]`; `parse_serve_line(line: str) -> int | None` (parses `WB_SERVE port=51877`); `blender_argv(blender, addon_dir, project, port) -> list[str]` (`[blender, "--python", <addon_dir>/bootstrap.py, "--", "--project", project, "--port", str(port)]`); `start_serve(argv, timeout=30.0) -> (subprocess.Popen, int)` reading stdout lines until `parse_serve_line` hits, raising `WbError` on exit or timeout.
- Consumes: `wbspace.mul`, `mat4_from_12`, `to_blender_*` is NOT used here (engine space only).

- [ ] **Step 1: Write the failing tests.**

`tests/test_client.py`:
```python
import json
import socket
import threading
import time
import pytest
import client as C
from fake_engine import FakeWorkbench


def test_rejects_non_local_host():
    with pytest.raises(ValueError):
        C.McpClient(host="8.8.8.8", port=1)


def test_call_roundtrip_and_tools():
    fake = FakeWorkbench(); port = fake.start()
    try:
        c = C.McpClient(port=port); c.connect()
        assert "frame_info" in c.tools()
        assert c.call("engine_status") == {"status": "running"}
        rows = c.call("list_rows")["rows"]
        assert [r["name"] for r in rows] == ["wait", "jab", "dair"]
    finally:
        fake.stop()


def test_tool_error_is_wberror():
    fake = FakeWorkbench(); port = fake.start()
    try:
        c = C.McpClient(port=port); c.connect()
        fake.fail_next = "boom"
        with pytest.raises(C.WbError, match="boom"):
            c.call("engine_status")
        assert c.call("engine_status")["status"] == "running"
    finally:
        fake.stop()


def test_timeout_does_not_hang():
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1)
    port = srv.getsockname()[1]
    threading.Thread(target=lambda: srv.accept(), daemon=True).start()
    c = C.McpClient(port=port, timeout=0.3); c.connect()
    t = time.time()
    with pytest.raises(C.WbError):
        c.call("engine_status")
    assert time.time() - t < 3


def test_dropped_socket_is_wberror():
    fake = FakeWorkbench(); port = fake.start()
    try:
        c = C.McpClient(port=port, timeout=1.0); c.connect()
        fake.drop_after = 0
        with pytest.raises(C.WbError):
            c.call("engine_status")
    finally:
        fake.stop()


def test_connect_refused_is_wberror():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    with pytest.raises(C.WbError):
        C.McpClient(port=port, timeout=0.5).connect()


def test_cli_client_parses_envelope(tmp_path):
    script = tmp_path / "fake_launcher.py"
    script.write_text("import sys,json\nprint('noise')\nprint(json.dumps({'ok': True, 'result': {'args': sys.argv[1:]}}))\n")
    c = C.CliClient(["python", str(script)], "proj", extra=["--engine-port", "5"])
    out = c.call("list_rows", {"a": 1})
    assert out["args"][-3:] == ["--wb-call", "list_rows", '{"a": 1}'] and "--project" in out["args"]


def test_cli_client_error_envelope(tmp_path):
    script = tmp_path / "bad.py"
    script.write_text("import json\nprint(json.dumps({'ok': False, 'error': 'no row'}))\nraise SystemExit(1)\n")
    with pytest.raises(C.WbError, match="no row"):
        C.CliClient(["python", str(script)], "proj").call("x")
```

(`CliClient` accepts `exe` as a string or a list prefix; a string becomes `[exe]`.)

`tests/test_fake_engine.py`:
```python
import wbspace as W
import fake_engine as F


def test_plan_shape():
    p = F.synthetic_plan()
    assert [j["index"] for j in p["joints"]] == list(range(9)) and p["joints"][0]["synth"] is True


def test_schema2_frame_has_matrices_and_root():
    info = F.synthetic_provider("jab", 6)
    assert info["schema"] == 2 and len(info["bones"]) == 9
    m = W.bone_matrices(info)
    assert set(m) == set(range(9)) and "mtx" in info["root"]


def test_hitbox_active_window():
    assert F.synthetic_provider("jab", 4)["hitboxes"] == []
    assert len(F.synthetic_provider("jab", 6)["hitboxes"]) == 1
    assert F.synthetic_provider("jab", 9)["hitboxes"] == []


def test_hitbox_world_matches_bone_chain():
    info = F.synthetic_provider("jab", 6)
    hand = W.bone_matrices(info)[8]
    expect = W.apply_point(hand, (0, 0, 1))
    w = info["hitboxes"][0]["world"]
    assert max(abs(expect[0] - w["x"]), abs(expect[1] - w["y"]), abs(expect[2] - w["z"])) < 1e-6


def test_facing_changes_root_not_local_geometry():
    a, b = F.synthetic_provider("wait", 1, facing=1), F.synthetic_provider("wait", 1, facing=-1)
    ra, rb = W.root_matrix(a), W.root_matrix(b)
    pa = W.world_to_model(ra, tuple(W.bone_matrices(a)[8][i][3] for i in range(3)))
    pb = W.world_to_model(rb, tuple(W.bone_matrices(b)[8][i][3] for i in range(3)))
    assert max(abs(x - y) for x, y in zip(pa, pb)) < 1e-9


def test_pose_changes_with_frame():
    p1 = F.synthetic_provider("jab", 1); p9 = F.synthetic_provider("jab", 9)
    assert W.bone_matrices(p1)[8] != W.bone_matrices(p9)[8]
```

`tests/test_launch.py`:
```python
import launch as L


def test_parse_serve_line():
    assert L.parse_serve_line("WB_SERVE port=51877") == 51877
    assert L.parse_serve_line("garbage") is None


def test_serve_argv():
    a = L.serve_argv("gd.exe", "proj", engine_exe="melee.exe")
    assert a[0] == "gd.exe" and "--serve" in a and a[a.index("--project") + 1] == "proj"
    assert a[a.index("--engine-exe") + 1] == "melee.exe" and "--engine-windowed" not in a
    assert "--engine-windowed" in L.serve_argv("gd.exe", "p", headless=False)


def test_blender_argv():
    a = L.blender_argv("blender", "/x/addon", "proj", 1234)
    assert a[:3] == ["blender", "--python", "/x/addon/bootstrap.py"] and a[-4:] == ["--project", "proj", "--port", "1234"] and "--" in a


def test_find_blender_order(tmp_path):
    assert L.find_blender({"GW_BLENDER": "B"}, settings_value="S") == "S"
    assert L.find_blender({"GW_BLENDER": "B"}) == "B"
    assert L.find_blender({"PATH": ""}) is None


def test_start_serve_reads_port(tmp_path):
    s = tmp_path / "s.py"
    s.write_text("import time,sys\nprint('hello', flush=True)\nprint('WB_SERVE port=4321', flush=True)\ntime.sleep(5)\n")
    p, port = L.start_serve(["python", str(s)], timeout=10)
    try:
        assert port == 4321
    finally:
        p.kill()
```

- [ ] **Step 2: Run, expect FAIL** — `python -m pytest tools/blender/geno_workbench/tests -q` (missing modules).
- [ ] **Step 3: Implement `client.py`.** Newline-delimited JSON-RPC 2.0 over one `socket.create_connection((host, port), timeout)`. `connect()` sends `initialize` then `notifications/initialized` (no reply expected for the notification). `call` sends `tools/call` `{name, arguments}`, reads lines until the reply with the matching `id`, honouring a total deadline (`socket.timeout` -> `WbError("timeout calling <tool>")`; EOF -> `WbError("engine connection closed")`). `isError` true -> `WbError(body.get("error") or text)`. All exceptions from `OSError` become `WbError`. `CliClient` as specified.
- [ ] **Step 4: Implement `fake_engine.py`.** FK in pure Python with `wbspace.mul`. Rest local translations (engine space): j1 `(0,0,0)` under 0, j2 `(0,5,0)`, j3 `(0,1,0)`, j4 `(0,1.5,0)`, j5 `(0,2,0)`, j6 `(-1.5,0,0)` under 4, j7 `(-1.8,0,0)` under 6, j8 `(-1.8,0,0)` under 7. Pose at frame `f`: `t = f - 1`; j3 gets `Ry(1.0*t)`, j6 `Rz(4.0*t)`, j7 `Rz(2.0*t)`, written as local matrices `T * R`. Root (joint 0) world = `T(root_x,0,0) * Ry(90*facing)`. `rows`: `wait` (clip `Wait`, no hitbox), `jab` (clip `Attack11`, aerial false, hitbox slot 0, joint `HAND_R`, frames 5-8, size 2.8), `dair` (aerial true, hitbox frames 5-8). `hitboxes[].world = hand_mtx @ offset(0,0,1)`, `offset {x:0,y:0,z:1}`, `radius 2.8`. Hurtboxes: capsules between joints (4->5), (4->6), (6->7), (7->8), (2->4), radius 1.0, in world space. ECB: bottom `(rx, 0)`, top `(rx, 9)`, left `(rx-3, 4.5)`, right `(rx+3, 4.5)` where `rx` is root x. `floorY 0`, `lowestY` min bone y. Server: `socketserver.ThreadingTCPServer` bound to `127.0.0.1`, one handler loop reading lines; `drop_after`/`fail_next` as specified; the reply to `tools/call` is `{"content":[{"type":"text","text":<compact JSON>}],"isError":bool}` exactly like `McpServer::toolResult`; `tools/list` returns the tool names; unknown tool -> JSON-RPC error `-32602`. The server keeps `current_row`, `frame`, `facing` (settable through `FakeWorkbench.set_facing(f)`).
- [ ] **Step 5: Implement `launch.py`** per the Interfaces block (stdlib only; `start_serve` reads `proc.stdout` line by line in the calling thread with a deadline using a reader thread and a `queue.Queue`).
- [ ] **Step 6: Run, expect PASS** — `python -m pytest tools/blender/geno_workbench/tests -q`. Commit — `git add tools/blender/geno_workbench && git commit -m "geno_workbench: JSON-RPC client, fake engine server, launch helpers"`.

**Reviewer verifies:** `python -m pytest tools/blender/geno_workbench/tests -q` (all pass, run twice to catch port reuse flakiness); the test run opens only `127.0.0.1` sockets (`grep -n "0.0.0.0" tools/blender/geno_workbench/*.py` -> no output).

---

### Task 5: Qt `--serve`, human author, headless env, project art keys  (Workspace repo, Claude-only)

**Files:**
- Modify: `tools/release/launcher/qt/workbench/mcp_server.h/.cpp`, `workbench_main.cpp`, `engine_link.h/.cpp`, `project.h/.cpp`, `commands_view.cpp`
- Test: `tests/mcp_test.cpp`, `tests/engine_link_test.cpp`, the project/`geno_data_test.cpp` test file that covers `plan_abs`

**Interfaces:**
- Produces:
  - `void McpServer::setAuthor(const QString &author)` (`"agent"` default; `"human"` allows `undo/redo/accept/reject`, runs with `propose=false`, `session_.agentProposals=false`, history author `human`).
  - CLI: `gd-melee-launcher --serve --project P [--engine-exe E | --engine-port N] [--engine-windowed] [--serve-port N] [--serve-author human|agent]`. Defaults: author `human`, port `0`, engine headless. After listening it prints exactly one stdout line `WB_SERVE port=<n>` (flushed) and runs the event loop until stdin closes or SIGTERM/Ctrl+C.
  - `EngineLink::Launch::headless` (bool, default `false`); `QProcessEnvironment EngineLink::buildEnvironment(int port) const` (extracted from `start`; inserts `MELEE_WB_HEADLESS=1` when `headless`).
  - `ProjectConfig::artBlend`, `ProjectConfig::artGlb` (QString; from `workbench.json` keys `art_blend`, `art_glb`; resolved exactly like `planAbs`; read-only).
- Consumes: Task 2's env contract `MELEE_WB_HEADLESS`.

- [ ] **Step 1: Failing tests.** `mcp_test.cpp`: `humanServerAllowsUndo` (server with `setAuthor("human")`: `tools/call undo` is not answered with `requires a human author`), `agentServerStillRefusesUndo` (existing behaviour), `humanServerAppliesEditDirectly` (an `edit_hitbox` call on the synthetic fixture returns without a proposal and the History entry has author `human`). `engine_link_test.cpp`: `headlessSetsEnv` (`Launch{headless=true}` -> `buildEnvironment(5000).value("MELEE_WB_HEADLESS") == "1"`; with `headless=false` the variable is absent, and the other variables `MELEE_CONSOLE_PORT`, `MELEE_SCENE`, `MELEE_WB_DIR` are present in both). Project test: `artKeysAreReadOptionally` (absent -> empty strings; present -> stored; a NUL byte -> the same `fail` as `plan_abs`).
- [ ] **Step 2: Run, expect FAIL** — WSL or Windows per `tools/release/launcher/qt/README.md`; the earlier lane used `worktrees/wbbuild.sh`: `cmake --build _build/wb-qt && ctest --test-dir _build/wb-qt -R "mcp|engine_link|geno_data|project" --output-on-failure`. Expected: compile errors for the new API.
- [ ] **Step 3: Implement.** In `McpServer::handle` replace the literal `"agent"`/`true` with members `author_`/`propose_`; only enforce `humanOnlyCommand` when `author_ == "agent"`. `EngineLink::start` builds its environment via `buildEnvironment(port)` (move the existing `env.insert(...)` lines unchanged, add the headless line). `workbench_main.cpp`: add the options to the value-taking list used by `isWorkbenchCli` (line ~30) so a value named `--serve` stays a value; a third mode `ServeMode` next to `McpMode`/`CallMode`; `--serve` requires `--project`; build the session as the other modes do, `McpServer server(*owned.session); server.setAuthor(author); server.listenLocal(port, &err)`, print the line, run `QEventLoop` until stdin EOF (poll with a `QSocketNotifier` on stdin or a 500 ms timer reading `std::cin.peek()`), then `owned.session->engine()->stop()` for an engine this process started (an attached engine is left alone, as in `--wb-call`). `Options` gains `bool headless = true` (false with `--engine-windowed`). `commands_view.cpp`: prefix the descriptions of `set_camera`, `set_overlays`, `render_view` with `Debug only (frozen; the viewer is Blender): `.
- [ ] **Step 4: Run, expect PASS** — same ctest command; then `ctest --test-dir _build/wb-qt` all green and `python tools/release/launcher/check_qt_strings.py` clean.
- [ ] **Step 5: Live smoke** — `gd-melee-launcher --serve --project <synthetic temp dir written by the test fixture helper>` in one shell prints `WB_SERVE port=N`; in another `python tools/blender/geno_workbench/...`: `python - <<EOF` using `client.McpClient(port=N)`: `call("list_rows")` returns the fixture rows. Record both outputs in the lane report.
- [ ] **Step 6: Commit** — `git add tools/release/launcher/qt && git commit -m "workbench: --serve persistent session, human author mode, headless engine env, art keys"`.

**Reviewer verifies:** the ctest summary line (`100% tests passed`), the `WB_SERVE` smoke transcript, `grep -n "setAuthor" tools/release/launcher/qt/workbench/*.cpp`, and that the stdio `--mcp` path still constructs `McpServer` with the default author `agent` (`grep -n "McpServer server" tools/release/launcher/qt/workbench/workbench_main.cpp`).

---

### Task 6: Add-on shell: props, session API, registration, connect panel  (Workspace repo, Codex-OK)

**Files:**
- Create: `tools/blender/geno_workbench/__init__.py`, `props.py`, `api.py`, `operators.py`, `panels.py` (Connect box only for now), `bootstrap.py`, `README.md`
- Test: `tools/blender/geno_workbench/tests/test_api.py`

**Interfaces:**
- Produces (`api.WbSession`, pure Python; every bpy-facing callback is injected, so the class is pytest-able):
  - `WbSession(client_factory: Callable[[], client.McpClient | client.CliClient])`
  - state: `.client`, `.connected: bool`, `.status: str`, `.rows: list[dict]`, `.row: str`, `.frame: int`, `.info: dict | None` (last frame_info), `.hitboxes: list[dict]`, `.problems: list[dict]`, `.stale: bool`, `.last_error: str`
  - methods (each catches `WbError` into `.last_error`/`.status` and returns `bool` success): `connect()`, `disconnect()`, `refresh_rows()`, `load_row(name)`, `set_frame(n)`, `step(n=1)`, `refresh_hitboxes()`, `run_checks()`, `edit_hitbox(**fields)`, `rebuild_reload()`, `suggest_bone(ordinal)`
  - module function `session() -> WbSession` (singleton used by operators and by agents via `bpy` MCP: `import geno_workbench.api as a; a.session().set_frame(8)`).
- Produces (`props.py`): `STRINGS: dict[str,str]`; `class GenoWBProps(bpy.types.PropertyGroup)` with `host` (default `127.0.0.1`), `port` (int), `project` (dir path), `launcher_exe` (file path), `blender_art` (file path override), `row` (string), `frame` (int, `update=` callback `on_frame_changed`), `playing` (bool), `show_hurt`, `show_ecb`, `show_floor`, `show_hit` (bools, default True), `status` (string), `pose_error` (float), `stale` (bool); registered as `Scene.geno_wb`.
- Produces (`operators`): `geno_wb.start_server`, `geno_wb.connect`, `geno_wb.disconnect`, `geno_wb.engine_restart` (calls `engine_restart` tool). Each is a thin wrapper: call the session method, copy `.status` to the property, `report({'ERROR'}, ...)` on failure.
- Consumes: `client.McpClient`, `launch.start_serve/serve_argv/find_launcher`.

- [ ] **Step 1: Failing test `tests/test_api.py`** (pure; uses the fake server):

```python
import api
import client
from fake_engine import FakeWorkbench


def make():
    fake = FakeWorkbench(); port = fake.start()
    s = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
    return fake, s


def test_connect_and_rows():
    fake, s = make()
    try:
        assert s.connect() and s.connected and s.status.startswith("connected")
        assert s.refresh_rows() and [r["name"] for r in s.rows] == ["wait", "jab", "dair"]
    finally:
        fake.stop()


def test_set_frame_stores_info():
    fake, s = make()
    try:
        s.connect(); s.refresh_rows()
        assert s.load_row("jab") and s.set_frame(6)
        assert s.info["frame"] == 6 and s.info["schema"] == 2 and s.row == "jab"
        assert s.step(2) and s.info["frame"] == 8
    finally:
        fake.stop()


def test_error_is_captured_not_raised():
    fake, s = make()
    try:
        s.connect()
        fake.fail_next = "engine busy"
        assert s.set_frame(3) is False
        assert "engine busy" in s.last_error and s.connected
    finally:
        fake.stop()


def test_dropped_connection_marks_disconnected():
    fake, s = make()
    try:
        s.connect()
        fake.drop_after = 0
        assert s.refresh_rows() is False and s.connected is False and "closed" in s.status.lower() or not s.connected
    finally:
        fake.stop()


def test_old_engine_schema_is_reported():
    fake, s = make()
    try:
        s.connect()
        fake.provider = lambda row, frame, **k: {"row": row, "frame": frame, "bones": [{"joint": 1, "parent": 0, "pos": {"x": 0, "y": 0, "z": 0}}]}
        s.load_row("jab")
        assert s.set_frame(2) is True            # the data call itself works
        assert "schema 2 needed" in s.pose_problem()   # but posing is refused with the explanation
    finally:
        fake.stop()
```

(`WbSession.pose_problem() -> str` runs `wbspace.check_schema(self.info)` and returns the message or `""`; `FakeWorkbench.provider` is a settable attribute.)
- [ ] **Step 2: Run, expect FAIL** — `python -m pytest tools/blender/geno_workbench/tests/test_api.py -q`.
- [ ] **Step 3: Implement `api.py`.** `set_frame`/`step` call tools `set_frame {frame}` / `play {frames:n, step:1}`; both return the frame_info dict, store it in `.info`, update `.frame` from it. `load_row` calls `load_row {row}` and sets `.row`. `connect` does `client.connect()`, `engine_status`, sets `status = "connected: <engine status>"`. A `WbError` whose message contains `closed` or `refused` or `timeout` sets `connected = False`. `edit_hitbox(**f)` calls `edit_hitbox` with `row`/`ordinal`/fields and sets `.stale = True` only on success (a result with a `proposal` key sets `.status = "proposal created: accept it in the Creator hub"` and still sets stale False). `rebuild_reload` calls `rebuild` then `reload`, sets `.stale = False` only if both succeed, then `refresh_rows()` and re-sets the current row/frame.
- [ ] **Step 4: Implement the Blender shell.** `__init__.py` with `bl_info = {"name": "Geno Workbench", "blender": (4, 0, 0), "category": "Animation", "description": "Viewer and editor front end for the Geno Workbench engine"}`, `register()`/`unregister()` that import the submodules inside the functions (so `import geno_workbench` works under pytest without `bpy`: wrap `import bpy` in `try/except ImportError` and make `register` a no-op without it), registering `GenoWBProps`, operators, panels, `bpy.types.Scene.geno_wb = PointerProperty(...)`, and removing them in reverse. `operators.start_server`: `launch.start_serve(launch.serve_argv(exe, project), timeout=30)` where `exe = props.launcher_exe or launch.find_launcher(root=<project's .git ancestor>)`; sets `props.port`; stores the Popen in a module global killed on `unregister` and on `disconnect` (only the one this add-on started). `bootstrap.py`: parse args after `--`, add the package parent to `sys.path`, `register()`, set `props.project/port`, call `geno_wb.connect` then `geno_wb.load_fighter` if present (Task 7 adds it; guard with `hasattr(bpy.ops.geno_wb, 'load_fighter')`). `panels.py`: `GENO_WB_PT_connect` in the 3D View N-panel tab "Geno" showing host/port/project/launcher, buttons Start server / Connect / Disconnect / Restart engine, and the status line (`props.status`). `README.md`: install (symlink or copy `tools/blender/geno_workbench` into the Blender add-ons folder, or run through `bootstrap.py`), headless test command, and the agent recipe (`execute_blender_code` snippets calling `geno_workbench.api.session()`).
- [ ] **Step 5: Run, expect PASS** — `python -m pytest tools/blender/geno_workbench/tests -q`. Commit — `git add tools/blender/geno_workbench && git commit -m "geno_workbench: add-on shell, session API, connect panel"`.

**Reviewer verifies:** pytest as above; `python -c "import sys; sys.path.insert(0,'tools/blender'); import geno_workbench"` exits 0 outside Blender; with Blender: `blender --background --python-expr "import sys; sys.path.insert(0,'tools/blender'); import geno_workbench as g; g.register(); print('REG', hasattr(__import__('bpy').types.Scene,'geno_wb')); g.unregister()"` prints `REG True`.

---

### Task 7: Rig loading, calibration, pose application, numeric check  (Workspace repo, Codex-OK)

**Files:**
- Create: `tools/blender/geno_workbench/rig.py`, `pose.py`
- Modify: `operators.py` (add `geno_wb.load_fighter`, `geno_wb.calibrate`, `geno_wb.verify_pose`), `panels.py` (Fighter box), `props.py` (`armature` string, `art_path` etc.)
- Test: covered by Task 8's headless self-test; pure parts already pinned in Task 3

**Interfaces:**
- Produces (`rig.py`, bpy):
  - `find_armature(name: str = "") -> bpy.types.Object | None` (the named object, else the single armature, else the one carrying a `geno` custom property; same rule as `export_fighter.find_armature`)
  - `load_fighter(blend: str = "", glb: str = "") -> bpy.types.Object` (`.blend`: append all objects of the file's scene that are armatures or skinned meshes via `bpy.ops.wm.append`/`bpy.data.libraries.load(link=False)`; `.glb`: `bpy.ops.import_scene.gltf`, then the same clean-up `ports/goku-xv2/tools/artist_blender.py` does: clear `pb.custom_shape`, remove unskinned meshes such as the importer's `Icosphere`; returns the armature; raises `RuntimeError` with a message naming the missing file)
  - `bone_names(arm) -> list[str]`
- Produces (`pose.py`, bpy):
  - `blender_rest_matrices(arm, jointmap, action_name="", frame=0) -> dict[int, Mat4]` (assign the action if given, `scene.frame_set(frame)`, `view_layer.update()`, return `arm.matrix_world @ pb.matrix` as `Mat4` tuples for every mapped joint; restores the previous action/frame)
  - `calibrate(arm, session) -> Calibration` (see Steps; stores it on the module: `pose.CAL`)
  - `apply_frame(arm, info, jointmap, cal) -> ApplyReport` (`posed: int`, `skipped_mirrored: list[int]`, `missing: list[int]`)
  - `verify_pose(arm, info, jointmap, eps=1e-3) -> {"max_err": float, "worst_joint": int, "n": int, "ok": bool}`
- Consumes: `wbspace.*`, `rigmap.build_joint_map/JointMap`, `api.session()`, props `armature`.

Calibration procedure (this is the derived transform; do not change it without changing `test_calibrate.py`): engine joint frame `Mn_j` (Blender-converted engine world matrix) and the rig's pose-bone matrix `B_j` (armature-space, times `matrix_world`). With `Mn_j = W * L_j` (engine world placement W times the joint's model-space frame) and `B_j = L_j * R_j` (R_j = fixed rotation between the engine's joint frame and the Blender bone frame), `calibrate_offsets` recovers `W0` from the root-most mapped joint and `K_j = inv(Mn_j) * W0 * B_j` which equals `R_j` (independent of the pose and of the world placement). Per frame: `target_j = to_blender_matrix(engine_j) * K_j`, assigned as `pb.matrix = arm.matrix_world.inverted() @ target_j` in parent-first order.

- [ ] **Step 1: Implement `rig.py`** per the Interfaces block. For `.blend` use `bpy.data.libraries.load(path, link=False)` to pull `objects` whose type is `ARMATURE` or `MESH`, link them into the current collection; if the file has more than one armature, prefer the one with a `geno` custom property.
- [ ] **Step 2: Implement `pose.calibrate(arm, session)`.** (1) `plan = rigmap.load_plan(<plan path from the session: api.session().plan_path>)` — add `WbSession.plan_path` filled by `api.set_project(project_dir)` which reads `workbench.json` (`plan_abs` resolved against the nearest `.git` ancestor of the project dir, else `plan` relative to the project) — and `jm = rigmap.build_joint_map(plan, bone_names(arm), aliases=<workbench.json art.bone_aliases or {}>)`; (2) if `jm.coverage() < 0.8` raise `RuntimeError("only X percent of engine joints have a bone in <armature>; check the rig or add art.bone_aliases")`; (3) choose the reference row: the first row in `session.rows` whose `clip` is an action in `bpy.data.actions` (prefer clip `Wait`); `session.load_row(row); session.set_frame(1)`; take `engine_rest = {j: to_blender_matrix(m) for j, m in bone_matrices(info).items() if j in jm.by_index}`; (4) `blender_rest = blender_rest_matrices(arm, jm, action_name=<clip>, frame=0)` (when no action matches, use the rest pose: all pose bones identity, which is what the headless self-test uses); (5) `root = jm.order()[0]`; `cal = wbspace.calibrate_offsets(engine_rest, blender_rest, root)`; (6) warn into `session.status` if `abs(cal.scale - 1) > 0.02` ("rig scale differs from the engine by N percent") and if any `K_j` translation column has length > 0.05 ("bone head is not at the joint origin: <names>"); (7) store `pose.CAL = (jm, cal)`.
- [ ] **Step 3: Implement `apply_frame`.** `wbspace.check_schema(info)` first (propagate `SchemaError`, the operator reports it). For `j in jm.order()`: `m = wbspace.bone_matrices(info)[j]`; if `wbspace.is_mirrored(m)` skip and record; `target = wbspace.mul(wbspace.to_blender_matrix(m), cal.k[j])`; `pb = arm.pose.bones[jm.by_index[j]]`; `pb.matrix = arm.matrix_world.inverted() @ Matrix(target)`. After the loop `bpy.context.view_layer.update()`. Joints in `info` that are not in `jm` are counted into `missing`.
- [ ] **Step 4: Implement `verify_pose`.** For each mapped joint compare `arm.matrix_world @ pb.head` with `to_blender_point(bone.pos)` (use `info["bones"][i]["pos"]`); report max error and worst joint; `ok = max_err <= eps`. Also compute `rot_err` as the max over joints of the Frobenius norm of `(pb_world_rot3 - target_rot3)` and include it as `rot_err`.
- [ ] **Step 5: Operators and panel.** `geno_wb.load_fighter` resolves art in this order: `props.blender_art` (a `.blend` or `.glb` path), else `workbench.json` `art_blend` then `art_glb` (the session exposes `.art_blend/.art_glb` from `set_project`), loads, sets `props.armature`, runs `calibrate`; `geno_wb.calibrate` reruns it; `geno_wb.verify_pose` stores `props.pose_error` and reports `OK`/`WARNING`. The Fighter box shows armature name, mapped/unmapped counts, calibration scale, pose error.
- [ ] **Step 6: Hook posing into frame updates.** In `api.WbSession` add `on_frame: list[Callable]` hooks called after every successful `set_frame/step/load_row`; `operators` registers a hook that calls `pose.apply_frame` and `overlays.update` (Task 8) in the main thread, catching `SchemaError`/`RuntimeError` into `props.status`.
- [ ] **Step 7: Commit** — `git add tools/blender/geno_workbench && git commit -m "geno_workbench: rig load, calibration, exact bone-matrix pose, numeric check"`. (Tests: Task 8's self-test; Codex cannot run Blender, so the reviewer runs it.)

**Reviewer verifies:** `python -m pytest tools/blender/geno_workbench/tests -q` still passes; `python tools/workbench/run_blender_selftest.py` (Task 8) prints `GENO_WB_SELFTEST OK` including the line `pose: max_head_err=<1e-3 rot_err=<1e-3 frames=40 facings=2`; read `pose.py` for the parent-first order and the `matrix_world.inverted()` factor.

---

### Task 8: Overlays, headless self-test, runner  (Workspace repo, Codex-OK for code; Claude runs the self-test)

**Files:**
- Create: `tools/blender/geno_workbench/overlays.py`, `selftest.py`, `tools/workbench/run_blender_selftest.py`, `tools/workbench/test_run_blender_selftest.py`
- Modify: `props.py` (overlay toggles already declared in Task 6)

**Interfaces:**
- Produces (`overlays.py`, bpy):
  - `COLLECTION = "GenoWB Overlays"`; object names `GenoWB.hit.<n>` (n<8), `GenoWB.hurt.<n>` (n<24), `GenoWB.ecb`, `GenoWB.floor`
  - `ensure_collection(scene) -> bpy.types.Collection` (idempotent: calling twice never makes `GenoWB Overlays.001`)
  - `update(scene, info: dict, props) -> dict` (`{"hit": n_visible, "hurt": n_visible}`); builds `shapes.overlay_geometry`, writes each mesh with `mesh.clear_geometry(); mesh.from_pydata(verts, edges, faces); mesh.update()`, shows/hides objects with `hide_viewport`/`hide_render`, never deletes between frames (objects are reused)
  - `clear(scene)` removes the collection and its objects and orphan meshes/materials created by the add-on
  - slot colours: slot 0 `(1.0, 0.15, 0.1, 0.55)`, 1 `(1.0, 0.55, 0.1, 0.55)`, 2 `(1.0, 0.9, 0.1, 0.55)`, 3 `(0.9, 0.2, 0.9, 0.55)`; hurtboxes `(0.15, 0.8, 0.4, 0.25)` shown as wire (`display_type = 'WIRE'`); ECB wire `(0.2, 0.6, 1.0, 1.0)`; floor wire `(0.6, 0.6, 0.6, 1.0)`; materials are plain viewport colours (`mat.diffuse_color`), created once and named `GenoWB.slot<n>`, `GenoWB.hurt`, `GenoWB.ecb`, `GenoWB.floor`
- Produces (`selftest.py`): run with `blender --background --python tools/blender/geno_workbench/selftest.py -- --out <dir>`; prints one line per check and `GENO_WB_SELFTEST OK` (exit 0) or `GENO_WB_SELFTEST FAIL <reason>` (exit 1).
- Produces (`run_blender_selftest.py`): `python tools/workbench/run_blender_selftest.py [--blender PATH]` finds Blender via `launch.find_blender`, runs the self-test in a temp dir, streams the `GENO_WB_` lines, exits with its exit code; exits 77 with `SKIP: no Blender` when none is found (pytest wrapper treats 77 as skip).
- Consumes: Tasks 3, 4, 6, 7.

Self-test sequence (all from `selftest.py`; synthetic fighter only, nothing from disc):
1. `FakeWorkbench().start()`; `api.WbSession(lambda: client.McpClient(port=port))`; `connect()`, `refresh_rows()`.
2. Build an armature named `SynthRig` from `fake_engine.synthetic_plan()` and `fake_engine.rest_world()`: for each non-synth joint make an edit bone named after the plan joint, `head = to_blender_point(rest joint position)`, `tail = head + 1 unit toward its first child's head (or +Z in Blender if none)`, `roll = 0`, parents as in the plan (this makes the Blender bone frame differ from the engine joint frame, so calibration is exercised).
3. `jm = rigmap.build_joint_map(plan, bone_names(arm))` -> coverage 1.0; `pose.calibrate` using the rest pose (no action) -> `cal.scale` within 1e-6 of 1; every `K_j` translation length < 1e-6.
4. For `facing in (1, -1)`, rows `wait`, `jab`, `dair`, frames `1..20`: `session.load_row(row)`, `session.set_frame(f)` with the fake set to that facing, `pose.apply_frame`, `pose.verify_pose(eps=1e-3)` must be ok, and `rot_err < 1e-3`. Print `pose: max_head_err=<x> rot_err=<y> frames=40 facings=2` (max over all).
5. Overlays: at jab frame 6, `overlays.update` -> exactly 1 visible `GenoWB.hit.*` whose evaluated world-space centre equals `to_blender_point(world)` within 1e-4 and whose material colour is slot 0's; at frame 4 and 9 zero visible hit objects; 5 visible hurtboxes; ECB object has 4 vertices; floor plane z == 0. `ensure_collection` twice leaves exactly one collection named `GenoWB Overlays`; `clear` removes it.
6. Mirrored joint: mutate one bone's `mtx` row 0 to `-1` times itself in a copied `info`; `apply_frame` reports it in `skipped_mirrored` and does not raise.
7. Server killed: `fake.stop()`; `session.set_frame(3)` returns `False` within 3 s and Blender state (pose of bone 8) is unchanged from before the call.
8. Print the final line.

- [ ] **Step 1: Write `selftest.py`** per the sequence, using `sys.argv` after `--`, adding `tools/blender` to `sys.path`, and a tiny `check(name, cond, detail)` helper that prints `GENO_WB_CHECK <name> OK|FAIL <detail>` and raises on failure; wrap the whole in try/except to print `FAIL` and `sys.exit(1)`.
- [ ] **Step 2: Write `overlays.py`** per the Interfaces block. Name the hit objects' custom property `geno_wb_slot` and `geno_wb_active` so agents (and the self-test) can read them. Hit spheres are shown only for entries in `info["hitboxes"]` (the engine reports active hits only); `props.show_hit/show_hurt/show_ecb/show_floor` toggle visibility.
- [ ] **Step 3: Write `run_blender_selftest.py` and its pytest wrapper** (`test_run_blender_selftest.py`: runs the runner via `subprocess`, `pytest.skip` on exit 77, else asserts `GENO_WB_SELFTEST OK` in stdout).
- [ ] **Step 4: Commit** — `git add tools/blender/geno_workbench tools/workbench && git commit -m "geno_workbench: overlays as a reused Blender collection; headless self-test against the fake engine"`.

**Reviewer verifies:** (Claude, with Blender installed; set `GW_BLENDER` to its exe)
`python tools/workbench/run_blender_selftest.py` -> last line `GENO_WB_SELFTEST OK`, and the `pose:` line shows `max_head_err` and `rot_err` both below `1e-3`. Also `python -m pytest tools/workbench/test_run_blender_selftest.py -q` (passes or skips with 77, never fails). Without Blender: owed to a machine that has it.

---

### Task 9: Timeline, move picker, problems, hitbox edit, stale flow  (Workspace repo, Codex-OK)

**Files:**
- Modify: `tools/blender/geno_workbench/operators.py`, `panels.py`, `props.py`, `api.py`
- Create: `tools/blender/geno_workbench/tests/test_api_edit.py`
- Modify: `tools/blender/geno_workbench/selftest.py` (add the steps below)

**Interfaces:**
- Produces (`api` additions): `WbSession.first_active_frame(row, ordinal) -> int` (from `.hitboxes[ordinal]["start_frame"]`, default 1); `WbSession.goto_problem(i) -> bool` (loads the problem's row, refreshes its hitboxes, sets the frame to the hitbox's `start_frame`); `WbSession.coalesced_set_frame(n)` (stores `pending_frame`; `flush_pending() -> bool` sends only the latest value); `WbSession.edit_fields` constant `EDITABLE = ("bone","damage","size","x","y","z","angle","kbg","fkb","bkb","start_frame","end_frame")`.
- Produces (operators): `geno_wb.refresh_rows`, `geno_wb.load_row` (enum of rows), `geno_wb.step` (`n`, can be negative -> implemented as `set_frame(frame+n)` since the engine cannot rewind), `geno_wb.play` (modal timer, 1/30 s, stops on error or at `props.frame >= 600`), `geno_wb.run_checks`, `geno_wb.goto_problem` (index), `geno_wb.suggest_bone`, `geno_wb.edit_hitbox` (props `row`, `ordinal`, `bone`, `damage`, `size`, `start_frame`, `end_frame`; only fields the user changed are sent), `geno_wb.rebuild_reload`.
- Produces (panels): `GENO_WB_PT_timeline` (move dropdown fed from `session.rows`, frame slider = `props.frame`, buttons `|< -1 Play +1 >|`, the engine frame `info.frame` shown read-only), `GENO_WB_PT_problems` (a `UIList` of `kind  row #ordinal  message`, click = `goto_problem`), `GENO_WB_PT_hitbox` (list of `session.hitboxes` for the current row with `joint`, `size`, `start_frame..end_frame`; fields for the selected one; buttons Suggest limb / Apply / Rebuild + reload; banner `Source edited: rebuild + reload needed` while `session.stale`).
- Consumes: Task 6 `WbSession`, Task 7 hooks.

Behaviour details that must be implemented exactly:
- The add-on frame property `props.frame` is **not** `scene.frame_current`; scrubbing the scene timeline must not drive the engine, and the engine frame never drives the scene timeline (avoids fighting Blender's own action playback). `on_frame_changed` only calls `session.coalesced_set_frame`; a `bpy.app.timers` function polls every 0.05 s, flushes the latest pending frame, and unregisters itself when nothing is pending.
- After `edit_hitbox` succeeds the panel shows the stale banner; the displayed hitbox list is refreshed from `list_hitboxes` (source) but the overlays keep showing the engine's current (old) hitbox until `rebuild_reload` succeeds (the banner says so). `rebuild_reload` failure leaves `stale` True and shows the error.

- [ ] **Step 1: Failing test `tests/test_api_edit.py`:**

```python
import api, client
from fake_engine import FakeWorkbench


def make():
    fake = FakeWorkbench(); port = fake.start()
    s = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
    s.connect(); s.refresh_rows()
    return fake, s


def test_problems_and_goto():
    fake, s = make()
    try:
        assert s.run_checks() and s.problems[0]["kind"] == "wrong_limb"
        assert s.goto_problem(0)
        assert s.row == "jab" and s.info["frame"] == 5      # first active frame of hitbox 0
    finally:
        fake.stop()


def test_edit_marks_stale_until_reload():
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes()
        assert not s.stale
        assert s.edit_hitbox(row="jab", ordinal=0, bone="FOOT_R")
        assert s.stale and fake.stale
        assert s.rebuild_reload()
        assert not s.stale and not fake.stale and s.row == "jab"
    finally:
        fake.stop()


def test_failed_rebuild_keeps_stale():
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes(); s.edit_hitbox(row="jab", ordinal=0, size=3.5)
        fake.fail_next = "build failed"
        assert s.rebuild_reload() is False and s.stale and "build failed" in s.last_error
    finally:
        fake.stop()


def test_only_changed_fields_are_sent():
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes()
        s.edit_hitbox(row="jab", ordinal=0, size=3.5)
        name, args = [c for c in fake.calls if c[0] == "edit_hitbox"][-1]
        assert args == {"row": "jab", "ordinal": 0, "size": 3.5}
    finally:
        fake.stop()


def test_scrub_is_coalesced():
    fake, s = make()
    try:
        s.load_row("jab")
        for n in (3, 4, 5, 9):
            s.coalesced_set_frame(n)
        assert s.flush_pending() and s.info["frame"] == 9
        sets = [c for c in fake.calls if c[0] == "set_frame"]
        assert len(sets) == 1
    finally:
        fake.stop()
```
- [ ] **Step 2: Run, expect FAIL** — `python -m pytest tools/blender/geno_workbench/tests/test_api_edit.py -q`.
- [ ] **Step 3: Implement the `api` additions** so Step 1 passes (the fake's `list_hitboxes` returns `start_frame` 5, so `goto_problem(0)` lands on frame 5; `run_checks` stores `result["problems"]`).
- [ ] **Step 4: Implement operators and panels** per the Interfaces block. `geno_wb.play` is a modal operator with `bpy.types.Operator.modal` and `window_manager.event_timer_add(1/30)`; each tick `session.step(1)`; on `False` it cancels and reports. Add to `selftest.py` after step 7 of Task 8 (re-create the fake server first): scrub 20 `props.frame` values quickly, wait for the timer to flush, assert one engine `set_frame`; run the `edit_hitbox` operator, assert `props.stale`; `rebuild_reload`, assert not stale; print `GENO_WB_CHECK edit-flow OK`.
- [ ] **Step 5: Run, expect PASS** — `python -m pytest tools/blender/geno_workbench/tests -q`. Commit — `git add tools/blender/geno_workbench && git commit -m "geno_workbench: timeline, move picker, problems, hitbox edit with stale flow"`.

**Reviewer verifies:** pytest; `python tools/workbench/run_blender_selftest.py` shows `GENO_WB_CHECK edit-flow OK`; read `operators.py` to confirm no operator calls `time.sleep` or blocks on a socket without the client's timeout (`grep -n "sleep" tools/blender/geno_workbench/operators.py` -> no output).

---

### Task 10: One coordinate contract for the checker, plus a frame_info differ  (Workspace repo, Codex-OK)

**Files:**
- Modify: `tools/workbench/compare_hitboxes.py`, `tools/workbench/test_compare_hitboxes.py`
- Create: `tools/workbench/frame_info_diff.py`, `tools/workbench/test_frame_info_diff.py`

**Interfaces:**
- Produces: `frame_info_diff.diff(a: dict, b: dict) -> dict` returning `{"max_abs": float, "worst": "<field path>", "fields": int}` over `bones[].pos`, `bones[].mtx`, `root.mtx`, `hitboxes[].world`, `hurtboxes[].a/b`, `ecb.*`, and `ok(a, b, tol=1e-3) -> bool`; CLI `python tools/workbench/frame_info_diff.py A.json B.json [--tol 1e-3]` printing `max_abs=<v> worst=<path> fields=<n> OK|DIFF`. Bone lists of different length -> `diff` raises `ValueError("bone count differs: x vs y")`.
- Changes `compare_hitboxes.compare(wb_hits, ref_spheres, tol, to_model=None)`: when `to_model` (a callable on `(x,y,z)`) is given, `wb world` positions pass through it before the distance is taken; the live CLI builds `to_model = lambda p: wbspace.world_to_model(wbspace.root_matrix(info), p)` from the same frame_info and prints which space was compared (`space=model`). New flag `--space world|model` (default `model`). The module imports `wbspace` with `sys.path.insert(0, ROOT/'tools/blender/geno_workbench')`.
- Consumes: Task 1 (`root.mtx`), Task 3 (`wbspace`).

- [ ] **Step 1: Failing tests.** In `test_compare_hitboxes.py` add:

```python
def test_model_space_transform_applied_before_distance():
    wb = [{"slot": 0, "world": {"x": 10.0, "y": 2.0, "z": 0.0}, "radius": 2.0, "active": True}]
    ref = [{"slot": 0, "pos": (0.0, 2.0, 0.0), "radius": 2.0}]
    shift = lambda p: (p[0] - 10.0, p[1], p[2])           # a root offset of x=10
    assert not C.compare(wb, ref, 0.5)[0]["ok"]            # world vs model-local: the 57.8-style mismatch
    assert C.compare(wb, ref, 0.5, to_model=shift)[0]["ok"]
```

`test_frame_info_diff.py`:
```python
import pytest
import frame_info_diff as D


def info(x=0.0):
    return {"bones": [{"joint": 1, "pos": {"x": x, "y": 0, "z": 0}, "mtx": [1, 0, 0, x, 0, 1, 0, 0, 0, 0, 1, 0]}],
            "root": {"mtx": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]}, "hitboxes": [], "hurtboxes": [],
            "ecb": {"bottom": {"x": 0, "y": 0}}}


def test_equal():
    assert D.diff(info(), info())["max_abs"] == 0 and D.ok(info(), info())


def test_difference_found():
    d = D.diff(info(0.0), info(0.25))
    assert abs(d["max_abs"] - 0.25) < 1e-12 and "bones" in d["worst"] and not D.ok(info(0.0), info(0.25))


def test_bone_count_mismatch():
    b = info(); b["bones"].append(dict(b["bones"][0], joint=2))
    with pytest.raises(ValueError, match="bone count differs"):
        D.diff(info(), b)
```
- [ ] **Step 2: Run, expect FAIL** — `python -m pytest tools/workbench -q`.
- [ ] **Step 3: Implement** both modules. In the live CLI of `compare_hitboxes.py`, before comparing, record the residual for the owner-run check: after the `--space model` run, if any line is `DIFF`, also print `hint: if the residual is a constant scale, compare with plan scale <plan.json scale>` — and do not guess a scale in code. (The measurement is Step 4.)
- [ ] **Step 4: Live measurement (Claude with the disc, windowed or headless engine)** — `python tools/workbench/compare_hitboxes.py --port 51726 --row dair --motion 70 --frames 6,9,10 --tol 0.5 --space world` (expect the old DIFF, ~57.8 at frame 10) and then `--space model`. Expected: `OK` for every active slot. If `model` still differs, record per-axis residual and whether it is a constant factor (compare with `plan.json` `scale`) in the lane report as a spec fact; `wbspace.world_to_model` stays the single definition and any extra factor is added there with a test, never at call sites. Owed if no disc machine is available.
- [ ] **Step 5: Run, expect PASS** and commit — `python -m pytest tools/workbench -q`; `git add tools/workbench && git commit -m "workbench: compare_hitboxes uses the shared model-space transform; frame_info differ"`.

**Reviewer verifies:** pytest; `grep -n "world_to_model" tools/workbench/compare_hitboxes.py tools/blender/geno_workbench/*.py` shows the single definition in `wbspace.py` and its use in the comparer (the add-on itself needs only `to_blender_matrix`, because it keeps the world placement); the live transcript (or "owed").

---

### Task 11: Qt hub: remove the viewport, "Open in Blender"  (Workspace repo, Claude-only)

**Files:**
- Create: `tools/release/launcher/qt/workbench/hub_panel.h/.cpp`, `blender_launch.h/.cpp`, `tests/blender_launch_test.cpp`
- Modify: `workbench_window.h/.cpp`, `CMakeLists.txt` (qt/workbench), `tests/ui_test.cpp`, `../window.cpp` (`blender_exe` setting), `../CMakeLists.txt` if sources are listed there
- Delete: `viewport.h`, `viewport.cpp` and every use (`viewport->` in `workbench_window.cpp`, the `render_view` pipeline: `renderPending`, `renderNumber`, `setImage` call sites)

**Interfaces:**
- Produces (`blender_launch.h`):

```cpp
namespace wb {
struct BlenderCommand { QString program; QStringList args; QString error; };
// Search order: setting value, $GW_BLENDER, PATH "blender". Empty when not found.
QString findBlender(const QString &setting, const QProcessEnvironment &env);
// <ancestor containing .git>/tools/blender/geno_workbench, or empty.
QString findAddonDir(const QString &projectDir);
// [blender, "--python", <addon>/bootstrap.py, "--", "--project", P, "--port", N]
BlenderCommand blenderCommand(const QString &blender, const QString &addonDir,
                              const QString &projectDir, quint16 port);
}
```
- Produces (`WorkbenchWindow`): the central widget is `HubPanel` (project name, row/hitbox counts, engine status with Start/Stop/Restart buttons, a headless/windowed toggle bound to `Launch::headless`, the **Open in Blender** button, and a one-line hint `Blender shows the fighter; this window keeps the problems, review and history panels.`); `quint16 WorkbenchWindow::serveForBlender()` starts (once) `McpServer` with `setAuthor("human")` and `listenLocal(0)` on the window's `Session` and returns its port; the Open in Blender button calls it, then `QProcess::startDetached(program, args)`. Existing docks (outliner, inspector, problems, clips, fidelity, review, history, palette) stay. `set_camera`/`set_overlays`/`render_view` stay registered and callable (the palette lists them under "Debug").
- Consumes: Task 5 (`setAuthor`, `Launch::headless`), Task 8 (the add-on's `bootstrap.py`).

- [ ] **Step 1: Failing tests.** `blender_launch_test.cpp`: `findBlenderOrder` (setting beats env beats PATH; none -> empty), `findAddonDir` (temp tree with `.git` dir and `tools/blender/geno_workbench/bootstrap.py` -> found from a nested project dir; none -> empty), `blenderCommandShape` (args exactly `["--python", "<addon>/bootstrap.py", "--", "--project", P, "--port", "1234"]`). `ui_test.cpp`: the window has no `Viewport` child (`findChild<QWidget*>("viewport") == nullptr`), has a button with objectName `openInBlender` that is disabled with a tooltip when `findBlender` is empty, and `serveForBlender()` returns a nonzero port twice with the same value.
- [ ] **Step 2: Run, expect FAIL** — `cmake --build _build/wb-qt && ctest --test-dir _build/wb-qt -R "blender_launch|ui" --output-on-failure`.
- [ ] **Step 3: Implement.** Strings are `t("Open in Blender", "Abrir en Blender")`, `t("Blender not found: set GW_BLENDER or the Blender path in Settings", "No se encontro Blender: define GW_BLENDER o la ruta de Blender en Ajustes")`, `t("Headless engine (no window)", "Motor sin ventana")`, and the hint line (Spanish: `Blender muestra al luchador; esta ventana conserva los paneles de problemas, revision e historial.`). `window.cpp` settings: add a `blender_exe` line edit + Browse in the Creator settings group, stored as `settings_.options["blender_exe"]` like `creator_enabled`. Remove `viewport` use; `WorkbenchWindow::Impl` keeps `FrameInfo` only for the timeline widget's frame readout. The Creator's `LaunchFactory` sets `launch.headless = true` by default; the toggle flips it and restarts the engine.
- [ ] **Step 4: Run, expect PASS** — full `ctest --test-dir _build/wb-qt`; `python tools/release/launcher/check_qt_strings.py`; `ctest -R launcher_qt_strings`.
- [ ] **Step 5: Live check (owed to a human with a monitor and Blender)** — open the Creator on a synthetic or Goku project, click Open in Blender, see the add-on connected (`Geno` N-panel status `connected: running`). Claude can verify the process start only: after the click, the Blender process exists (`Get-Process blender`) and the hub's `serveForBlender` port is listening (`Test-NetConnection 127.0.0.1 -Port <port>`).
- [ ] **Step 6: Commit** — `git add tools/release/launcher/qt && git commit -m "workbench: Creator hub (no viewport), Open in Blender, headless toggle"`.

**Reviewer verifies:** ctest summary; `grep -rn "Viewport\|viewport" tools/release/launcher/qt/workbench/*.cpp tools/release/launcher/qt/workbench/*.h` -> only the debug-command descriptions; `git show --stat HEAD` lists the deleted `viewport.*`.

---

### Task 12: Goku project file, MCP smoke, acceptance, docs  (Workspace repo)

This replaces Task 17 of the first plan. Same files, updated contents.

**Files:**
- Modify: `ports/goku-xv2/workbench.json`, `ports/goku-xv2/README.md` (one paragraph), `tools/CLAUDE.md` (one row), `docs/CLAUDE.md` (one row), `tools/blender/README.md` (one row)
- Create: `tools/workbench/mcp_smoke.py`, `tools/workbench/acceptance.md`, `tools/workbench/CLAUDE.md`, `docs/workbench.md`
- Modify: `docs/superpowers/plans/2026-10-09-geno-workbench.md` (top-of-file notice only)

**Interfaces:**
- Consumes: everything above. `ports/goku-xv2/workbench.json` gains names and paths only:

```json
"art_blend": "_build/goku-xv2/author-source/goku.blend",
"art_glb": "_build/goku-xv2/author-source/goku.glb",
"art": {"bone_aliases": {}}
```
(`art_blend`/`art_glb` resolved against the nearest `.git` ancestor like `plan_abs`; `art.bone_aliases` maps plan joint name -> Blender bone name and starts empty because the glTF importer keeps the XV2 bone names. The file already has `plan_abs`, `mods_dir`, `rebuild`.)

- [ ] **Step 1: `mcp_smoke.py`** (stdlib only, uses `tools/blender/geno_workbench/client.py`): spawn `gd-melee-launcher --serve --project <dir> [--engine-exe ...]` via `launch.start_serve`, `McpClient.call` for `list_rows`, `run_checks`, `list_hitboxes`; also `--mcp` stdio path: `initialize`, `tools/list`, `tools/call list_rows`. `--synth` writes the same synthetic fighter files as `testfixture.h` into a temp dir (copy of the fixture content, no disc data). Command: `python tools/workbench/mcp_smoke.py --exe _build/wb-qt/gd-melee-launcher --synth`; last line `mcp smoke OK`.
- [ ] **Step 2: `acceptance.md`** (owner-watched script; every item "owed" until a human has watched it):
  1. Start the hub on `ports/goku-xv2` (engine headless by default); click **Open in Blender**; the `Geno` panel shows `connected`; Fighter box: armature `GokuExport` mapped >= 95 percent, `pose max_head_err < 1e-3` after `Verify pose` on rows `wait`, `jab`, `dair`.
  2. **Via MCP only** (an agent through `gd-melee-launcher --mcp --project ports/goku-xv2`, plus the Blender MCP for screenshots): `run_checks`; for each of the three `wrong_limb` problems `suggest_hitbox_bone` then `edit_hitbox` (three hitboxes); then `list_clips`, `preview_clip`, `assign_clip` to re-pick `dair`; `rebuild`, `reload`. All proposals are accepted by the owner in the hub review panel (agent author).
  3. The **owner views the result in Blender** (hitbox spheres on the right limbs at the right frames, dair clip) and **then in the game** (`ports/goku-xv2/tools/play.ps1`, windowed).
  4. Record: history ids, `git diff --stat ports/goku-xv2`, `python tools/workbench/compare_hitboxes.py ... --space model` output, and the add-on `Verify pose` numbers.
- [ ] **Step 3: Docs.** `docs/workbench.md`: what it is (Blender viewer + engine data + hub + MCP), the data flow diagram as an ASCII figure, install of the add-on, `workbench.json` schema (with `art_*`), the coordinate contract (engine -> Blender, `world_to_model`), agent recipes (Workbench MCP for data and edits, Blender MCP for views), data-safety rules, and "wb.render is debug-only and frozen". No private paths, no disc locations. `tools/workbench/CLAUDE.md` (10 lines). One row each in `tools/CLAUDE.md`, `docs/CLAUDE.md`, `tools/blender/README.md`. Add this notice at the very top of the first plan: `> Revision 1 (2026-10-09) supersedes this plan's Task 15 viewport and Task 17; see 2026-10-09-geno-workbench-blender.md.`
- [ ] **Step 4: Full verification.**

```bash
cmake --build _build/wb-qt && ctest --test-dir _build/wb-qt --output-on-failure
python tools/release/launcher/check_qt_strings.py
python -m pytest tools/blender/geno_workbench/tests tools/workbench tools/release/launcher/test_check_qt_strings.py ports/goku-xv2/tests/test_ground_modes.py -q
python tools/workbench/run_blender_selftest.py
python tools/workbench/mcp_smoke.py --exe _build/wb-qt/gd-melee-launcher --synth
python tools/check_workspace_paths.py
python tools/port/check_no_disc_text.py
```
Expected: all ctest pass; strings clean; pytest green; `GENO_WB_SELFTEST OK`; `mcp smoke OK`; the two guards report no findings. `git ls-files tools/blender/geno_workbench ports/goku-xv2/workbench.json | xargs grep -il "xenoverse\|\.iso"` -> no output.
- [ ] **Step 5: Commit** — `git add ports/goku-xv2 tools docs && git commit -m "workbench: Blender-viewer acceptance script, MCP smoke, docs, Goku art keys"`.

**Reviewer verifies:** every command above with its output quoted; the acceptance run itself is **owed** to the owner.

---

## Self-Review

**Spec coverage (Revision 1).**
- Game workbench data-only source of truth, bones/hitboxes/hurtboxes/ECB/floor per frame: Task 1 (matrices, root, ECB sides), Task 2 (headless). `wb.render` frozen, debug-only: Task 1 Step 4, Task 5 (descriptions), Task 12 docs.
- Add-on connects to the engine console: via the persistent Session socket (Task 5 `--serve`, Task 11 hub listener, Tasks 4/6 client) instead of the raw console, so staging logic (`lift`, row motion) is not duplicated: flagged as R-f.
- Loads the fighter source rig+mesh: Task 7 (`rig.py`, `art_blend`/`art_glb`, Task 5 keys, Task 12 Goku values).
- Poses the armature to the engine's matrices exactly, numeric check: Tasks 3 (math), 7 (apply, `verify_pose`), 8 (self-test: both facings, 40 frames, `1e-3`). The live Goku run of `Verify pose` is owed (Task 12 acceptance).
- Hitbox spheres by slot/active, hurtbox capsules, ECB, floor in a dedicated collection: Tasks 3 (geometry), 8 (overlays). Inactive ghosts: gap R-h.
- Timeline, move picker, problems with jump-to-frame, scrub/step/play: Task 9. Edits through `workbench_core`, refresh: Tasks 6/9 (`edit_hitbox`, stale flow, `rebuild_reload`).
- Start the engine via `--wb-call engine_status/engine_restart` or directly: `CliClient` (Task 4) for `--wb-call`; `engine_status`/`engine_restart` tools over the socket (Task 6); `start_server` launches `--serve` (Task 6); direct engine spawn is the launcher's job inside `--serve` (Task 5).
- Headless test mode and fake engine with synthetic frame_info, no disc data: Tasks 4, 8.
- Qt Creator tab becomes a hub, viewport placeholder removed, Open in Blender: Task 11.
- Task 17 updated (Goku `workbench.json`, MCP smoke, acceptance via MCP only for 3 hitboxes + dair, owner views in Blender then game): Task 12.
- Owner additions: true headless engine (Task 2); Task 13 coordinate gap (Tasks 1, 3, 10); keep the data part of `ee3807daa` (Task 1 Step 4, R-j, Decision 3).
- Agents drive both MCPs: README recipe (Task 6), `api.session()` surface, acceptance step 2.

**Placeholder scan.** No TBD/TODO. Game-internal unknowns (GPU assumptions, facing accessor, bridge declarations) are explicit grep-and-decide steps with exact commands and acceptance criteria, as in the first plan's Task 12. The scale-factor question of R-b is a measured step (Task 10 Step 4), not a guess.

**Type consistency.** `Mat4` tuples throughout `wbspace`/`shapes`/`fake_engine`; `JointMap.by_index/order/coverage` used identically in Tasks 3, 7, 8; `Calibration(w0, k, scale)`; `WbSession` methods named once in Task 6 and extended (not renamed) in Task 9; JSON keys of `frame_info` identical in Task 1 and Task 4's fake; hitbox keys (`start_frame`, `end_frame`, `joint` as a role string like `HAND_R`) match `hitboxJson` in `commands_hitbox.cpp`; `McpServer::setAuthor` and `Launch::headless` names are the same in Tasks 5 and 11.

**Review Focus coverage.** (1) Task 4 timeout/dropped tests, Task 8 step 7. (2) Task 3 `test_unmapped_report`, `test_suffix_and_case_tolerant`; Task 7 refuse-below-80-percent. (3) Task 3 `test_schema1_rejected`, Task 6 `test_old_engine_schema_is_reported`. (4) Task 3 `test_facing_flip_roundtrip`, `test_mirrored_joint_is_detected`; Task 8 steps 4 and 6. (5) Task 9 `test_edit_marks_stale_until_reload`, `test_failed_rebuild_keeps_stale`.

**Known fragile spots for the executor.** Task 7's `pb.matrix` assignment depends on parent-first order and on `matrix_world.inverted()`; if `verify_pose` fails in Task 8 look there first, not at the test tolerance. Task 2 is the riskiest (boot path without Aurora); do it in its own lane and commit early. The calibration assumes the Blender reference action frame 0 equals engine frame 1 of the same clip; if the live Goku check shows a constant offset, switch the reference to the rest pose or add the engine-side `wb.rest_info` (Decision 2) instead of loosening `eps`.
