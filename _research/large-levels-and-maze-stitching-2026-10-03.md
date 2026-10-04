# Large levels and maze stitching: what the engine can do today (spike, 2026-10-03)

Question: how large can a playable level be, what stops it being larger, and what is the smallest set
of changes for long scrolling levels and a maze stitched from many chunks?
Tags: **VERIFIED** = ran it in the game (vanilla disc, FD host stage, LAB, Falco) or read the cited code;
**INFERRED** = reasoned, not run. **FIXTURE** = the fly cursor / `gd.teleport` placed the fighter;
**REAL** = scripted pad input (`gd.input`) under test.

Throwaway code (do not keep): `_build/spikes/large-levels/` (`mods/spike/scripts/main.lua` holds experiments
A, B, C, D, D2, E, E2, F, PB, PE; `run.sh`; `parts/E.lua`; results in `data/spike_main/res_*.txt` and PNGs).
Nothing tracked was edited. Sandboxes: `lls-hello, lls-a1, lls-a2, lls-a3, lls-f1, lls-f2, lls-b1, lls-c1, lls-c2,
lls-c3, lls-d1, lls-d2, lls-e1..e4, lls-pe1, lls-pe2, lls-pb1, lls-pb2` (all under `_build/runs/`).

## 1. Answer in short

- **Today, with no engine change, a level can be about 100,000 units wide and 100,000 tall in principle, but
  the hard ceiling is |x|,|y|,|z| < 50,000**: the game asserts and crashes beyond it
  (`melee/src/melee/lb/lbvector.c:388`, world-to-screen projection; VERIFIED by crash in `lls-f2` at x about 49,970
  with the fly cursor on). Walking is exact at 20,000 (step 1.5000 every frame) and at 49,850 (VERIFIED).
  In practice a fighter runs 1.5 units/frame, so 10,000 units is 110 seconds of running (VERIFIED, 10,060 units
  walked in one go, no stall, constant speed).
- **Vertical:** storeys 260 units apart up to y=3,120 all hold collision and land correctly (VERIFIED, FIXTURE for
  placement). Real jump-climbing between storeys: shaft with three pass-through platforms was climbed with REAL input
  twice in the toy maze (`lls-e3`), but that was incidental; **NOT TESTED BY SCRIPT as a deliverable, left for the owner.**
- **What actually bounds a level** is not space but (a) the blast zone and camera rectangle (default FD: blast
  -246..246 x -140..188; a fighter put at x=300 is KO'd within 20 frames, VERIFIED), which a gameplay mod can replace;
  (b) render cost, which is proportional to the **total triangles of every loaded model, visible or not** (no culling,
  VERIFIED), so a big level must be streamed; and (c) the 256 model-instance pool, 768 collision lines and 32 asset slots.
- **Streaming works and is cheap today:** `gd.area_load(name, builder)` / `gd.area_unload(name)` add or remove a whole
  chunk (models + lines + platforms) in **0.05-0.14 ms** each, with no heap growth over 42 loads / 36 unloads, and a
  fighter standing on removed collision falls, one falling onto re-added collision lands (all VERIFIED).
- **A maze stitched from chunks works as one continuous space** (toy maze, 4x4, streamed 3x3 window): walking through
  door openings across three chunk seams had 0 airborne frames; walls stop the fighter; the camera follows
  (VERIFIED). The lessons are about chunk design (section 6), not engine blockers.

## 2. Stage space (question 1)

| Fact | Evidence |
|---|---|
| Camera bounds and blast zones are rectangles in `stage_info`; `gd.stage_set_camera_bounds(l,r,t,b)` and `gd.stage_set_blast_bounds(...)` replace them (arena-hooks). Offset by an origin `(cam_x_offset, cam_y_offset)`. | `melee/pc/gameworld/script_arena.inc:30-62`, `melee/pc/platform/gw_script_arena.inc:57-67` (VERIFIED code); used in every run (VERIFIED) |
| `gd.stage_set_origin(x,y,{frames=N})` only moves that offset (and so the bounds) over N frames, modelled on `grKinokoRoute_80207C88`'s 60-tick tween. It moves **nothing** else: not fighters, not geometry. It is a scrolling camera/blast window, not a world shift. | `script_arena.inc:21-31,170-182`; `Ground_801C38BC` is just two stores, `src/melee/gr/ground.c:2682-2686` (VERIFIED code) |
| Melee's own scrolling stages do the same: fighters stay in real world coordinates; the stage script calls `Ground_801C38BC` each frame to drag the camera/bounds offset (Mushroom Kingdom adventure `grkinokoroute.c:124,427,476,489,498`; Big Blue route `grbigblueroute.c:1180`). Rainbow Cruise animates a camera jobj and carries fighters on moving collision. | code read (VERIFIED); behaviour not run |
| With no bounds change a fighter teleported to x=300 is KO'd at once and respawns at the **host stage's respawn point** (about x=16, y=45 on FD) | `lls-a2` P0 (VERIFIED). Use `gd.stage_set_spawn`. |
| Hard coordinate cap: `HSD_ASSERT(pos3d->x>-50000 && <50000)` (same for y and z) in the projection helper. API calls accept +/-100,000 but the game dies past 50,000. | `lbvector.c:388`; crash in `lls-f2` (VERIFIED) |
| Float precision is fine to 50,000: run step exactly 1.5000, standing y exactly 0.0, camera follows | `lls-f2` (VERIFIED) |
| Camera far plane is raised to 200,000 when `stage_set_*` via `gd.stage_bounds` ("largemap") or `gd.camera_bounds(true)`. The match camera frames the fighter so content is always near; no far-plane problem seen. | `src/melee/cm/camera.c:83-90,1241-1252` (code); runs (VERIFIED) |
| `gd.stage_isolate(true)` hid FD's scenery and collision; result was a black void with only our geometry, background stars, HUD | screenshots `A_mid.png` etc. (VERIFIED) |
| Fighters + camera at 10,000 units: camera eye tracks x-30 (z 131), no lag in steady state. After a 30,000-unit teleport the camera needs a few dozen frames to catch up, and an **off-screen indicator bubble** (red ring, fighter portrait, arrow) shows meanwhile (`B_s12.png`, VERIFIED). | `lls-a3`, `lls-b1` |

## 3. Scripted content limits (question 2)

| Limit | Current value | Where defined | What raising it costs |
|---|---|---|---|
| Model instances | **256** (docs say 128: stale). "model instance pool full (256)" seen at the 256th (VERIFIED) | `melee/pc/gameworld/script_model.h:5` | BSS array in `script_game.c` snapshot domain; linear. Not the real constraint (see render cost) |
| Collision lines in one model sidecar | 32 | `script_model.h:6` | per-model; merge parts into one sidecar only up to 32 |
| Scripted collision lines total | **768** (docs say 200; `stage_add_line` 512 + 255 model floors + 1 = 768/768 reached, then "collision line capacity unavailable", VERIFIED) | `script_game.c:74`; cap = min(768, (2048-verts)/2, 1536-lines, 1024-joints), `script_game.c:404-409` | mpLib hard limits: 2048 verts, 1536 lines (mpIsland `visited[0x600]`), joint array reallocated per scene by `ScriptGame_StageJointCapacity` (`script_largemap.inc:11`). About 1536 less the host stage's base lines is the ceiling without touching mpIsland |
| Scene-pinned assets | 32; 64 MiB budget; kit atlas 5.6 MiB (plus 5.6 MiB glow) dominates, 2 assets = 11.2 MiB (VERIFIED `asset_bytes`) | `script_model.h:4`, `gw_script_model_assets.inc:6` | assets are never evicted until scene end ("not an eviction cache") so a maze needs a fixed vocabulary of <=32 meshes plus a shared atlas |
| Areas (named streamable groups) | 64 | `script_game.c:77` | trivial |
| Targets / enemies | 128 / 32 | `script_game.c:76,78` | enemy cap is by design |
| HSD heap free during tests | about 9.33 MB, unchanged across streaming (VERIFIED) | `gd.stage_stats().heap_free` | model mesh/atlas bytes are outside it |
| Coordinates | API +/-100,000, game +/-50,000 | `gw_script.c` `gs_stage_num`; `lbvector.c:388` | needs a floating-origin rebase to exceed |

**Add/remove cost (VERIFIED, `gd.time()` around the call):** `area_load` of a chunk with 1 floor model, 1 ceiling line,
1 platform, 6 visual models (7-12 objects): avg 0.092 ms, max 0.140 ms (n=42). `area_unload`: avg 0.048 ms,
max 0.117 ms (n=36). In the maze, avg 0.055-0.070 ms. No hitches visible in `gd.perf` max-frame during the 7,600-unit
streamed run (`lls-c3`: all frames 16.7 ms paced, logic 0.6-0.9 ms). Heap unchanged.

## 4. Camera, HUD, enemies (questions 3 and 4)

- The match camera follows a fighter at any x/y inside the camera bounds (VERIFIED to 10,060 and to y=3,120).
  The camera is **clamped to the camera rectangle**, so for enclosed rooms the rectangle is the framing tool; a per-chunk
  rectangle moved with `stage_set_origin(...,{frames=N})` is the Melee-style way (INFERRED, not run). A script can also own
  the camera (`gd.camera_set/follow/bounds`, `docs/scripting.md` "Camera"); not exercised beyond `camera_get`.
- HUD (damage % and stock icon bottom-left) is screen-fixed and unaffected (VERIFIED, every screenshot).
  Off-screen bubble works at long range (VERIFIED, `B_s12.png`).
- Blast-zone KO follows whatever rectangle you set (VERIFIED: a KO below the maze at y<-300, fall counted, respawn at the
  host's respawn point x=16,y=45 mid-air, `lls-e4`).
- Enemies far from the origin: **NOT TESTED**. Code facts only: 7 kinds, 32 live cap (`script_game.c:78-79`). Whether
  `Item`/`ItCo` enemy AI has activation ranges or culls far items was not investigated; this is the biggest unknown left.
- Stage content API requires an offline gameplay mod; netplay/rewind are out of scope (every `gd.stage_*` call forks the LAB
  timeline; noted, not tested).

## 5. Performance (question 5)

Render cost is **per index of every loaded instance, regardless of visibility** (VERIFIED, `lls-d1`, `lls-d2`,
run with `MELEE_FPS=u`; `logic_ms` is the cost, because `total_ms` is paced to the display).

| Scene | logic_ms | Indices alive |
|---|---|---|
| base (1 floor) | 0.6-0.7 | 708 |
| 32 stairs (2,532 idx each), visible | 8.4 | 81k |
| 64 stairs | 16.2 | 162k |
| 128 stairs | 24.3 (16.9 in a second run) | 324k |
| 255 stairs **off-screen** at x=8000 | 36.8 | 646k |
| 256 beams (336 idx), visible | 8.95 | 86k |
| 128 stairs after one `model_move` each (unbatched) | 13.1 (visible and off-screen: same) | 324k |
| 255 beams unbatched | 4.4 | 86k |
| `gd.stage_view(false)` with 256 instances | 0.59 | hidden by that switch |

Reading: about 50-100 ns per index per frame, off-screen costs the same as on-screen, so there is no culling. At the
8.3 ms (120 fps) target roughly **70-140k indices (25-45k triangles) of loaded model geometry** total. Per-instance
overhead is negligible (beams and stairs cost the same per index), so **merging parts into one mesh buys instance slots and
sidecar lines, not frame time**; only fewer triangles or not loading them does. `model_move` once (unbatched) was
cheaper in these two samples (beams 4.4 vs 9.0 ms), probably GPU transform instead of CPU batching; one sample each, treat as a lead,
not a result. Draw calls: 1,577 with 768 lines + 256 instances; that run cost 15.9 ms logic (mostly the instances).
The cost of 768 lines alone was not isolated (INFERRED small: the slab draws are the debug strokes).
The kit's heaviest parts: stairs 2,532 idx, wall_window 2,592, wall_doorway 2,406. A kit chunk of a floor, a back wall and a beam
is under 2,500 indices; 9 loaded chunks about 22k indices (about 2 ms by this rate), comfortable.

## 6. Experiments, one line each

| | What | Result |
|---|---|---|
| A | one stretched `bf_floor_4m` per 2,600 units (`scale_x`=100, one collision line), run right with REAL input | 2,000 and 10,060 units: no failure; seams between 2,600-unit instances crossed at a constant 1.5 u/frame; camera follows; screenshots `A_mid/A_end`: purple slab, fighter, HUD, black void. Default bounds: instant KO at x=300 |
| B | 13 floors, 260 apart to y=3,120, FIXTURE fly + `place`, bounds widened | collision holds at every storey (y landed 260, 1040, 2080, 3120 after the 40-unit drop); cam follows (eye y within about 255 of floor); off-screen bubble appears during catch-up; walked off an edge at y=3,120 and fell 620+ units, no KO inside the widened bounds. Real jump-climbing NOT TESTED BY SCRIPT |
| C | 200-wide chunks (floor, ceiling line, platform, 6 visual models) streamed in a window -1..+3 / -2, 5,061 REAL frames to x=7,600 | no fall, no hitch; add/remove 0.05-0.14 ms; heap flat; standing on unloaded collision falls, re-adding catches (landed on the platform at y=25) |
| D, D2 | budget, see section 5 | |
| E | toy 4x4 maze, DFS spanning tree + 2 loops (seed 7), 9-chunk window, door openings 50 high, shaft with 3 pass-through platforms | real climb through two stacked shafts succeeded with scripted jumps (`lls-e3`); first versions exposed design flaws below |
| E2 | REAL walk through 3 door seams on row 0 | 0 airborne frames over 330 units, stopped at the closed east wall x=478 (wall at 480) |
| F | fighters at x=20,000 / 50,000 / 90,000 | 20,000 and 49,850 fine; any use past 50,000 crashes (assertion) |

Not cleanly measured: ceiling collision (my E2 jump test never reached the ceiling; the shaft climbs passed through ceiling
gaps without bonking, which only shows the gap is open). Treat ceilings as INFERRED to work like the other line kinds; the
sidecar loader and the `ceiling` kind exist and `stage_add_line` accepted them.

## 7. What stitching taught (experiment E)

1. **Kit sidecars carry floor lines only.** Every kit wall, beam and corner has `"lines":[]`
   (`bf_wall_solid_4m.coll.json` etc., checked all 24 parts). Walls, ceilings and door frames need either hand-written
   `stage_add_line` calls or sidecars with `left_wall`/`right_wall`/`ceiling` lines. A chunk format must carry them.
2. **Wall line direction convention (VERIFIED by the fighter stopping at the wall):** the normal faces the open side. A
   room's left edge is `right_wall` drawn top to bottom; its right edge is `left_wall` bottom to top; ceiling right to left.
3. **Ports must be typed and offset.** My first maze put the up-shaft and down-shaft of a cell at the same x, so the
   walk-to-shaft route fell through the floor hole of the cell's own down-shaft. Same for a horizontal route crossing a
   floor gap. Fix: a vertical port occupies a fixed x lane, and lanes alternate by row parity so a cell with both an up and
   a down port has them in different lanes; the author must also keep door routes clear of lanes (or require a jump).
4. **Floors are one-sided** (a floor from below is passable), so a chunk's underside needs ceiling lines.
5. **Adjacent chunks' floor lines are not linked** yet seams are walked with zero airborne frames when endpoints coincide
   exactly (x=120, 240 in E2; 2,600-unit seams in A). `gd.stage_link` (`script_stage_seams.inc`, 0.05 tolerance) exists for
   `stage_add_line` floors; whether it accepts model-owned floor lines was not tested.
6. **Camera inside enclosed chunks:** `E_shaft3.png`: a back wall tile (`bf_wall_solid_4m` stretched `scale_x/scale_y`, z=-10)
   fills the view, a red wall bar (the wall line, debug draw) is at the left edge, gold floor and violet pass-through slabs
   (debug draw: solid gold, pass-through cyan/violet) show under the fighter. The default camera frames the fighter tightly
   (z about 131-145); room-sized framing needs a camera rectangle per chunk.
7. **Respawn:** a KO respawns at the host stage's point (about 16,45). A maze needs per-chunk checkpoints through
   `gd.stage_set_spawn`.
8. Debug slabs are the only floor visuals unless the chunk spawns floor models; they are tall slabs and read as "gold
   block". A chunk needs real floor meshes.

## 8. Recommended chunk format

- **Grid:** cell 120 wide x 100 tall in game units (about 4.6 kit "4m" widths); every chunk occupies exactly one cell, origin at the
  bottom-left, floor at y=0, ceiling at y=100. Larger rooms occupy a rectangle of cells whose interior walls are omitted.
- **Ports (connection points)** declared in the chunk file, each with `{side, kind, lane}`:
  `west`/`east` door: opening from y=0 to y=50 on the shared wall, both sides open together; `up`/`down` shaft: a gap in
  the floor/ceiling at lane A (x 15-55) or lane B (x 65-105); lane = parity of the lower row, so a stacked pair always agrees.
- **Height changes:** only through shafts (pass-through platforms at 28/56/84, 26 wide, alternating sides of the lane centre)
  or ramps/stairs authored to exactly 100 units of rise per cell; all door floors at y=0 so seams are level.
- **Enclosure:** four walls and a ceiling as real lines (left edge `right_wall`, right edge `left_wall`, ceiling right to left),
  doors and gaps as omitted segments, never as extra lines. Unused ports are closed by the generator by simply emitting the full line.
- **Budget per chunk:** <= 12 lines, <= 8 instances, <= 2,500 indices; 3x3 window means 9 loaded chunks, 108 lines, 72 instances, about 22k indices.
- **Loading:** `area_load("m<x>_<y>", builder)`; keep all chunks within |50,000| (a 4x4 to 40x40 maze at this size is at most 4,800 units).
- **Contents:** enemy/pickup/trigger markers in chunk-local coordinates, a `checkpoint` point per chunk, per-chunk `camera` rectangle.
- **Validation that must be automatic:** ports of adjacent chunks line up, no route crosses a lane, door height >= 45.

## 9. Ranked changes

Sizes S/M/L. Rank 1 is first because it needs no engine edit.

| # | Change | Where | Size | Risk |
|---|---|---|---|---|
| 1 | **Chunk manager in Lua** over `gd.area_load/unload`: window of chunks around the player, a chunk-file loader (models, lines, platforms, ports, markers), checkpoints via `gd.stage_set_spawn`, bounds per chunk | new Lua module (Envoy/Project B runtime) | S-M | Enemy behaviour at far coordinates untested; area builders cannot yield and run synchronously (cheap today) |
| 2 | **Skip or hide unseen models in the batcher**: frustum or distance cull, or a "visible=false costs nothing" guarantee (untested whether hidden instances skip CPU transform) | `melee/pc/gameworld/script_model.inc` / `script_model_order.inc` | M | The renderer batches per camera pass (refraction etc.); changing it touches draw order and the snapshot-stored `batched` flag. Needed only for hand-built levels bigger than the streaming window or big meshes |
| 3 | **Wall and ceiling lines in kit sidecars and the Blender exporter**, and door-frame parts with collision | exporter + `*.coll.json` (`pc/tests/model_export_test.py` contract) | S-M | sidecar limit 32 lines/part |
| 4 | **Per-chunk camera framing**: a documented recipe (`stage_set_camera_bounds` + `stage_set_origin(..., {frames})`) or a `gd.camera_room{...}` helper that eases the rectangle and the zoom | Lua first; `camera.c` if zoom needs clamping | S-M | Camera rectangles fight the default zoom in small rooms; needs a play-test (screenshots do not show feel) |
| 5 | **Floating-origin rebase** or just a documented 50,000 limit; fix the assert path only if a level must exceed it | `lbvector.c:388` callers; or Lua offsets all coordinates | L (rebase) / S (document) | Rebase touches fighters, items, camera and savestates; avoid, keep levels < 40,000 |
| 6 | Raise 256 instances / 32 assets / 768 lines | `script_model.h`, `script_game.c:74` | S | The ceilings are mpLib (1536 lines) and mesh asset retention; not needed if streaming |
| 7 | Verify `gd.stage_link` on model-owned floors, or emit chunk floors with coincident endpoints (works today) | `script_stage_seams.inc` | S | low |

**Closed-loop traversal controller.** Yes, one is needed to validate chunk connections automatically (doors, shafts, gaps,
drop-throughs), because hand playing 100 chunks is not viable and my open-loop scripts failed for the reasons below. It would
take waypoints and emit real pad input (walk, run, short hop, full hop, double jump, drop through, retry) and report arrival
and time. **Do not build it yet.** Reads that are missing today: the **floor/line under the fighter** (id, kind, endpoints,
pass-through flag; `gd.floor_below` exists in the registration table, `gw_script.c`, not exercised here), **ledge and wall
contact** (the fighter's collision flags: grounded, on pass-through, touching wall left/right, ceiling), jump counters and
vertical speed (`vy` exists on the player table; double-jump remaining does not), and the **current ECB** extents. Until
then run the fly cursor to each port and drop the fighter, as this spike did (FIXTURE), and treat real traversal as a play-test.

## 10. For the owner to play (by hand)

Mods folder: `<workspace>\_build\spikes\large-levels\mods` (mod `spike`). It reads
`data/spike_main/which.txt`. Commands from the workspace root in Git Bash:

```
set -a && . ./.env && set +a
W="$(pwd -W)/_build/spikes/large-levels"
printf 'PE' > "$W/data/spike_main/which.txt"        # PE = toy maze, PB = vertical storeys
export MELEE_MODS_DIR="$W/mods" MELEE_SCRIPT_DATA_DIR="$W/data" MELEE_FPS=60 MELEE_PAD_IGNORE_ADAPTER=1 \
  MELEE_SCENE="mode=lab;p1=falco;stage=fd" MELEE_RUN_LABEL='large level spike'
tools/port/run.sh --realtime owner-play-1 --iso "$GW_ISO_VANILLA"
```

(`PE` and `PB` stay running; edit `which.txt` for the other. They do not quit. I launched each with a 300-frame limit,
`PE300` and `PB300`, which exited cleanly.)

- **PB** (storeys): 13 floors, 104 wide, at y = 0, 260, ... 3,120, x=0. In the console: `= gd.fly(1,true)` then
  `= gd.teleport(1,0,1080)` (storey 4), `= gd.teleport(1,0,2080)` (storey 8), `= gd.teleport(1,0,3120)` (top); `= gd.fly(1,'place')`
  lands. Try: jump between storeys (260 is deliberately too high; see whether you want a lower gap), run off the edge, watch the camera.
  Note a script-controlled fly cursor accepts targets only within +/-10,000; teleport to go further.
- **PE** (maze): 4x4 cells of 120x100, origin of cell (cx,cy) = (120cx, 100cy), seed 7, start (20,0). Cells stream in a 3x3 window. Row map
  (W/E/U/D = open sides): row3 `[-E--][WE--][WE-D][W--D]`, row2 `[-E-D][W--D][--UD][--UD]`, row1 `[--UD][-EUD][W-UD][--UD]`,
  row0 `[--U-][-EU-][WEU-][W-U-]`. Try: climb the shaft from cell (0,0) to (0,1) (three pass-through platforms, jump onto each,
  exit right of the gap); walk the row-0 doors from cell (1,0) east to the closed wall at x=480; fall through a gap and see the
  cell below load; jump at the ceiling; KO off the bottom (respawn is at the host point near 16,45, a known gap).
  Jump to a cell: `= gd.fly(1,true)`, `= gd.teleport(1,120*2+20,100*1+10)`, `= gd.fly(1,'place')`.
- What I could not judge from here: how the climb and the camera framing feel.

## 11. Gaps, honestly

Enemies far from the origin; ceiling collision as a deliberate test; hidden-instance cost (`visible=false`); `stage_link` on
model lines; savestates and netplay (out of scope); feel of the camera in small rooms; the `gd.log` volume drop (data files used
instead). Doc drift to fix: `docs/scripting.md` says 128 instances and 200 lines; the code and runs say 256 and 768.
