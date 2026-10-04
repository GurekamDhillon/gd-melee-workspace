# Seamless in-match stage switching: feasibility (2026-10-03)

Research only. Nothing in a tracked file was edited; no build was run. One experiment ran on the
existing `_build/melee-pc.exe` (section 6). Tags: **VERIFIED** = read in code (file:line), read in
the docs, or observed in the run; **INFERRED** = reasoned, not confirmed. Paths are under `melee/` unless
stated. "ACE" and "Akaneia" mean the m-ex mod discs.

The owner's idea: during a live match, swap the stage (vanilla, m-ex, or one of our levels) for another
behind a full-screen transition, with fighters, percents, held items and the match carrying on, with no
scene change and no loading screen. The owner also pointed at Smash Ultimate's Stage Morph (section 7).

## 0. Answer in ten lines

1. **It already works as a dressed swap on Final Destination.** One Lua probe on today's exe went
   FD -> Battlefield -> Yoshi's Story, hidden behind a full-screen wipe, with the fighters (and the
   CPU's idle state) continuing and no scene change. Load cost was 1.1 ms and 1.7 ms wall (warm file
   cache). VERIFIED (section 6).
2. What it is: the destination's **models** come from its real `GrXxx.dat` (`gd.stage_add_model` reads
   any root-level disc DAT, VERIFIED `pc/gameworld/script_game.c:236-297`), but the **collision** was
   hand-typed script lines, because no call reads a DAT's `coll_data`. That missing call is the main
   thing between "demo" and "all legal stages".
3. Stage code (moving platforms, Randall, Shy Guys, Stadium transformations, hazards, background
   animation) does not come with it: the model is loaded as a static pose (VERIFIED, no animation
   is set up in `ScriptGame_StageAddModel`, `script_game.c:1008-1085`).
4. Recommended first: **Design A**, extended with a DAT-collision reader and a native "stage params"
   apply (camera, blast zones, spawns). Size **M** (S for just the demo). Missions-folder levels are the
   easy case.
5. **True re-initialisation (B) is XL and risky**: the stage loader is written once-per-scene (it zeroes
   `stage_info`, leaks its collision tables to the scene heap, resets the 4-slot archive table).
6. **Pre-loading several stages (C) is how Pokemon Stadium and Big Blue already do it**, but only inside
   one merged collision table; it fits our tables for the static stages but is **L**, and is the right
   long-term answer for stages with code.
7. Online/rollback: every `gd.stage_*` write is refused online (VERIFIED), so A is offline/LAB only.
   An online version must be native, frame-triggered and inside the snapshot: C-shaped, XL.
8. Hardest unknown: **what carries a fighter across**: floor/ledge ids, ECB history, held items, and
   stage-bound items (section 3). The probe showed the easy half (they keep standing if the new
   floor is under them) and the hard half (a fighter outside the new floor falls).
9. Ultimate's rules (section 7) solve exactly the problems the owner's sketch papers over; adopt them.
10. Engine work list: section 8.

## 1. How a stage comes to exist in a match

Order of the match setup, `src/melee/gm/gmvs.c:2270-2294` (VERIFIED):
`Ground_801C0378(0x40)` allocates `Ground_804D6950` (`gr/ground.c:461-466`); `Stage_802251E8` -> the stage
`Init`; items init; `Stage_8022524C` -> `Ground_801C0800`; camera; `Stage_80225298` -> `on_load`; later
`Stage_802252E4` -> `Ground_801C0FB8` (`on_start`). The `Stage_*` wrappers are `gr/stage.c:576-640`.

**Ground_801C0754 (init, `ground.c:647-688`)**: resolves the m-ex row (`Mex_GrSelect`), calls
`Ground_801BFFB0`, sets `stage_info.grkind`, loads the stage file with `grDatFiles_801C6038` (m-ex:
`Mex_GrFunctionInit` relocates the grFunction PPC blob inside the loaded file and overrides the row's
callbacks, `ground.c:664-684`), reads the per-stage param table (`Ground_801C28CC`), and sets the
`on_touch_line` / shadow callbacks. VERIFIED.

**Ground_801BFFB0 (reset, `ground.c:382-451`)**: clears `stage_info`, all `map_gobjs[]`, `x280[]`, `x694[]`,
camera bounds to +-170 x 120/-60, blast zones to +-99999, and `memzero`s the 4-slot archive table
(`grDatFiles_801C6288`, `grdatfiles.c`, `grDatFiles_8049EE10[4]`). VERIFIED. This is "once per scene":
calling it again forgets, rather than frees, what the first call loaded.

**File load (`gr/grdatfiles.c`)**: `grDatFiles_801C6038` gets the stage's `map_head` archive and reads the
public symbols `coll_data`, `grGroundParam`, `itemdata`, `ALDYakuAll`, `map_ptcl`/`map_texg` (particle
banks), `yakumono_param`, `map_plit`, `quake_model_set` into `stage_info` (VERIFIED, `grdatfiles.c`
the `arg1 == 0` block). The file itself is normally a **preload**: `Ground_801C06B8` calls
`lbDvd_800178E8(4, data1, 4,4, ...)` before the scene (`ground.c:624-645`), into the persistent preload
heaps, which the scene change rebuilds (`lb/lbdvd.c:843-900`, `lbHeap_80015900`). VERIFIED. Whether the
`lbArchive_800171CC` path used by init falls back to a synchronous read for a file that was not
preloaded: INFERRED yes (the script loader does its own read, below).

**Per-stage `on_init`** (`Ground_801C0800`, `ground.c:808-915`): sets camera/zoom/blast from `stage_info.param`
(`Ground_801C38D0..801C3960`), registers item spawn data (`itemdata`) and the "random" item table, loads
the particle bank (`psInitDataBankLoad(0x1E,...)`), then **`mpLibLoad(coll)`**, `mpLib_80058820`, the map
GObj creation (`Ground_801C1E94`, `Ground_801C466C`) and `stage_data->on_init()`. Spawn points, camera
bounds and blast zones are filled by `Ground_801C39C0` / `Ground_801C3BB4` from markers in the map
(`grpstadium.c:179-180` shows a stage calling them). VERIFIED.

**Collision tables (`mp/mplib.c:79-81, 887-947`)**: fixed capacity **2048 vertices, 1536 lines, 256 joints**,
allocated with `HSD_MemAlloc` on every `mpLibLoad` and **never freed individually** (no free in
`mplib.c`; grep for `HSD_Free(groundColl*)` is empty). On PC the joint array grows on demand for the
script pool (`ScriptGame_StageJointCapacity`, `script_largemap.inc:9-13`); vertices/lines stay at the
retail limits because `mpIsland` indexes `visited[0x600]` by line id (`script_game.c:433-437`). VERIFIED.

**Heaps**: the stage's DAT in a real match lives in a preload heap; scripted DATs load into **heap 0**
(`lbHeap_80015BD0(0, ...)`, `script_game.c:267`), which is released at scene end (docs: "released at scene
end", `docs/scripting.md:384`). Heap sizes: heap 3 0x51A690, heap 4 0x164B400, heap 5 0x196C800, heap 6 0x20
(`lb/lbheap.c:28-50`); the main heap is "what is left of the arena" and is large (40 MB MEM1 on PC).
VERIFIED. **Two stages at once fit**: the probe held FD (preloaded) + BF (452,171 B) + YS (824,648 B)
simultaneously. VERIFIED (section 6).

**Anything that cannot be freed and redone mid-scene?** Not freed: the `mpLibLoad` tables (leak per call:
tens of KB), the `psInitDataBank` particle bank slot, the 4 archive slots (reset, not freed), stage music
selection, and any `HSD_GObj` user data the stage `on_init` allocated (freed with the GObj, so fine if
the GObjs are destroyed). Whether a GObj-by-class sweep of `HSD_GOBJ_CLASS_STAGE` is safe mid-frame:
INFERRED yes between logic frames, not tried. Stage music and stage effects: see section 3.

## 2. Precedents inside the game

All of them keep **one collision table loaded at scene start** and toggle joints (VERIFIED: `mpJointListAdd`
/ `mpLib_80057BC0` / `mpLib_800575B0` / `mpLib_80057528`, `mp/mplib.c:5445-5588`):

| stage | evidence | what it does |
|---|---|---|
| Pokemon Stadium | `gr/grpstadium.c:179-188, 358-600, 1865, 1878-1881, 2266-2274` | Stadium's whole collision (all transformations' joints) is in the initial table. Each transformation enables its joints (`mpJointListAdd(3)`), disables others (`mpLib_80057BC0`), and loads the transformation's **visual DAT** at runtime (`GrPs1..4.dat`, `grDatFiles_801C6478`) into one of the 4 archive slots. Preloads via `lbDvd_80017740` |
| Big Blue | `gr/grbigblue.c:2566-2573` (27 toggle calls) | a long course in one table; joints on/off as the route advances |
| Great Bay, Mushroom Kingdom II route, Shrine route, Icicle-style scrollers | `grgreatbay.c:520-547`, counts per file via grep: `grshrineroute` 29, `grinishie2` 21, `grkinokoroute` 12, `grrcruise` 10, `grcastle` 15 | same mechanism |
| Target Test layouts | `ground.c:690-806` (`Ground_TTMod_BuildCollData`) | **we already merge a second collision set into the scene's table at init** (our own code) |

Conclusion (VERIFIED for the mechanism, INFERRED for "could carry a different stage"): the carrier of
"stage content changes live" is *joint enable/disable in a preloaded merged table* + *runtime-loaded
visual DATs*. That is design C, and it is exactly what our script pool already is (768 reserved lines,
`script_game.c:388-450`).

## 3. What holds references to the stage

| holder | issue | state |
|---|---|---|
| Fighters | `coll_data.floor.index` (line id), ledge ids, last-ground, ECB history. If the line id is gone the fighter is airborne next frame | Observed: fighters keep standing when a new floor is at the same place; a fighter outside the new floor fell (section 6). Ledge-hang across a swap: not tried, INFERRED breaks (benched/called fighters avoid it: `gd.fighter_bench/call`, `docs/scripting.md:861-875` VERIFIED) |
| Items, projectiles | stage-bound items (Shy Guy-style, stage hazards) reference stage GObjs; held items are fighter-owned (INFERRED safe) | not tried |
| Camera | stage camera bounds, origin and zoom come from `stage_info.cam_info` (`ground.c:393-405`); Lua overrides exist (`gd.stage_set_camera_bounds`, `gd.stage_set_origin`, `gd.camera_params`: `docs/scripting.md:840`, VERIFIED). In the probe the FD camera was kept and BF/YS happened to fit | param swap needed (section 8) |
| Blast zones | `stage_info.blast_zone` (`ground.c:406-410`); "blast-bound writes" exist (`docs/scripting.md:840`) VERIFIED; exact call not enumerated | needs an "apply destination params" |
| Particles/effects | stage `map_ptcl` bank loaded once (`psInitDataBankLoad`), per-stage effects owned by stage GObjs | INFERRED; the destination's bank would not load under A |
| HUD / pause camera | read `stage_info` (bounds); INFERRED fine | n/a |
| Music | m-ex stage BGM list (`Mex_GrBgmCount/Id/Chance`, `ground.c:292-294`) VERIFIED to exist; the track is chosen at match setup | A leaves the host's music playing; switching needs a `gd` audio call (INFERRED a `gd.bgm`-style call exists, not looked up) |
| LAB savestates / rewind | `gw_snap.c` snapshots **all MEM1** plus the game's native globals incl. `pc_gameworld_script_game` (header of `pc/platform/gw_snap.c`, VERIFIED). So heap-0 DATs and the collision tables are covered. Not covered: Lua state, native malloc'd GXMS assets (`gs_stage_models`, `gw_script_model_assets.inc`) | `docs/HANDOFF-2026-10-03-ENGINE-DAY.md` item 10: savestate with reloaded assets "untested" (VERIFIED) |
| Rollback / netplay | scripted stage writes are **refused online** (comment in `pc/platform/gw_script_stage_isolation.inc`: "includes restore: never accepted online"; `ScriptGame_StageIsolate` checks `Netplay_Enabled()/RB_Enabled()/Replay_Active()`, `script_stage_isolation.inc:~30-45`) VERIFIED | online needs a native deterministic version |
| m-ex stage code | `gw_mex_grfunction.c`: PPC grFunction blob relocated **inside the loaded file** by `Mex_GrFunctionInit`; one global `Mex_GrSelect(grkind)` says whose row is current (`ground.c:652-684`) VERIFIED | a second m-ex stage live at once is not supported by the selector (INFERRED) |

## 4. Three designs

### A. Dressed swap on a host stage (what the probe did)

*Build:* Lua only today. Needed: DAT collision reader, destination params (camera, blast, spawns), a
host that can be hidden (only FD today: `gd.stage_hide` doc, `docs/scripting.md:383`; `StageIsolate`
requires `stage_info.grkind == Gr_Kind_Last`, `script_stage_isolation.inc`).

*Works:* static scenery and static collision. Models: `ScriptGame_StageAddModel` loads a `map_head`
**group** (one map GObj branch) as a lit, fogged stage-pass object; BF is 7 groups, YS 4 (probe log:
`group 7 -> unavailable`, `group 4 -> unavailable`). Platform position is user-supplied.
*Lost:* anything with code: Randall, Shy Guys, Stadium transformations, wind, water, background
animation (static pose), per-stage items, the stage's particle bank, per-stage music, stage-specific
blast/camera until we write them.

*DAT collision readable?* The data is there: `coll_data` is a public symbol of the same file, read by
`grdatfiles.c` via `HSD_ArchiveGetPublicAddress(sp14, "coll_data")` (VERIFIED), layout
`struct MapCollData` (`mp/types.h:124-133`: verts, lines, 5 ranges, joints). `script_stage_archive`
already holds the parsed archive (`script_game.c:236-297`). **No Lua call exposes it** (grep of
`gw_script*.c/.inc` and `script_*.inc` for `coll_data` hits only fighter `coll_data`). Offline tooling can
read it: `ports/ir/tools/stage_parts.py` and `experiment/tooling/HSDLib/.../SBM_Coll_Data.cs`;
`_research/stage-model-parts.md` records that Battlefield's floors are one static group and FD's is one
unlinked static group, YS has a separately linked group (Randall), Adventure Mushroom Kingdom has 51
linked groups. (VERIFIED from that note; not re-derived.)

*How far for the legal stages* (INFERRED from `stage-model-parts.md` plus the probe):
- Final Destination, Battlefield: complete (static, no hazards). BF reached in the probe.
- Dream Land: static main + 3 platforms; Whispy and wind are code, lost (INFERRED).
- Yoshi's Story: static geometry works (visual reached in the probe); Randall (a moving, linked collision
  group) and the Shy Guys are lost; clouds are a static pose.
- Fountain of Dreams: platforms rise and fall by code (`grizumi.c`) and the water is animation; static
  at one height under A.
- Pokemon Stadium: the transformations are the stage. Static base only under A; real Stadium needs C.

*m-ex stages (ACE/Akaneia):* the DAT is on the mod disc; `DVDConvertPathToEntrynum` resolves "a mounted
mod's own DAT" (comment, `script_game.c:262`, VERIFIED) so models load by name the same way. Their
code is PPC blobs in the file: not run under A. Static m-ex stages work as well as vanilla ones.

*Mission-folder levels, today:* the easy case. Host must be **FD** (stage_isolate limit). With the
missions mod: wipe; `gd.fighter_bench/call` the fighters; `gd.stage_hide(true)` (needs an own floor
first); load the level's folder via the missions mod (model reload, collision sidecars up to 64 lines
per mesh, `docs/scripting.md:408-445`); to go back, remove the level's instances and floors
(`gd.stage_remove`, `gd.model_despawn`) and `gd.stage_hide(false)`. All steps exist (VERIFIED in the docs);
the combined sequence was not run. A vanilla destination from a mission level is the probe's path.

*Online:* refused (VERIFIED). *LAB:* works; savestate across a switch is **untested** and Lua state is
not in the snapshot (VERIFIED), so a scripted switch must re-derive its state from the game.

Size: **S** for a demo-grade mod using today's calls; **M** with the DAT-collision reader and params.

### B. True in-match re-initialisation

Sequence, fighters benched and logic frozen behind the wipe (all INFERRED except where cited):
1. Bench fighters (`gd.fighter_bench`), release items that reference stage GObjs.
2. Tear down: destroy `HSD_GOBJ_CLASS_STAGE` GObjs and `map_gobjs[]`, stage procs; clear `mpLib` joint
   list; free `Ground`/`user_data`; unload the particle bank; the 4 archive slots.
3. Run `Stage_802251E8` (init), then `Stage_8022524C` (on_init: tables, camera, blast, items),
   `Stage_80225298` (on_load), `Stage_802252E4` (on_start) with the new kind.
4. `fighter_call` everyone to the new spawn points.

Constraints found: `Ground_801BFFB0` zeroes instead of freeing (`ground.c:382-451`); `mpLibLoad`
allocates fresh 2048/1536/256 tables each call without freeing the previous (`mplib.c:908-925`);
`Ground_801C0800` re-registers item tables; the preload heaps are not available mid-scene, so the
destination file goes to heap 0 like a scripted DAT. **Two stages fit in memory** (probe), so a cross-fade
is possible, but nothing in the init path supports two grounds at once (single `stage_info`, single
`mpLib` table, single `Mex_GrSelect`); free-then-load it must be. File load time on PC: 0.45 MB and
0.82 MB read and parsed in 1.1 ms and 1.7 ms (VERIFIED, warm cache; first read from the ISO on a cold
cache not measured). Items in flight and held, camera and music: all need explicit hand-offs (section 3).
It works for m-ex stages in principle (the same init is how they load at all), but the `Mex_GrSelect`
global and the guest-state of the previous blob must be reset (INFERRED). Rollback: everything lives
in MEM1, which is snapshotted (VERIFIED), so a native, frame-triggered B is rollback-clean in principle;
the missing piece is a deterministic trigger and a native free path. Size **XL**; risk **high**.

### C. Pre-loaded multi-stage (the Stadium model)

At match start, build **one merged `MapCollData`** from the host stage and N destination stages (our
`Ground_TTMod_BuildCollData` is the pattern, `ground.c:690-806`), with each stage's joints initially
disabled, preload each stage's visual DAT into heap 0 (we already do 8 x 8 MiB), and "switch" = disable
joint group, enable the other (`mpLib_80057BC0`/`mpJointListAdd`), hide/show the stage's GObjs.
Budgets: 2048 vertices / 1536 lines hold FD+BF+YS+DL+FoD+Stadium base if their collision is small
(FD uses 16 lines; our script pool already takes 768; INFERRED that the six legal stages total
well under the remainder; count them with `stage_parts.py` before committing). Stage code is **kept**
only for the host stage; destination stages' `on_init` would also have to be run (their map GObjs
and callbacks) with `stage_info` being single-instance, so hazards still do not come for free:
INFERRED L-XL to run two stages' callbacks together. m-ex: the grFunction blob for a destination
must be relocated at preload (as `Mex_GrFunctionInit` does for the active one). Mission levels: they are
already scripted content in the same pool. Online: best case of the three, since everything is in
MEM1 and the switch is a deterministic joint toggle on a frame; needs a native trigger (XL).
Size **L** (visual+collision+params, no hazards); **XL** with hazards.

## 5. Which first

**Design A**, with these upgrades, because it is the only one whose core is already shown working and
because every part is reused by C later (the DAT-collision reader becomes the merged-table builder):
a native `coll_data` reader, an "apply destination params" (camera bounds, blast zones, spawn points
from `grGroundParam`/markers), a host-agnostic isolate, and a single atomic `gd.stage_switch` that
does bench -> swap -> place fighters -> params in one call so it is one rewind fork and later one
native, rollback-safe event.

## 6. The experiment

Probe: `_build/audit-20261003/stage-switch/mods/stsw/` (Lua + a 6-line WGSL wipe); data and screenshots
in `.../stage-switch/data/stsw_main/`; log `_build/runs/stsw-2/melee-pc.log`. Run per the brief: second
monitor, vanilla disc, LAB `mode=lab;p1=mario;p2=fox/cpu0;stage=fd`, `MELEE_PAD_IGNORE_ADAPTER=1`,
isolated mods and data dirs, `gd.cpu_mode(2,"stand")` at match start. The run ended itself with
`gd.quit()` (exit 0). A first attempt (`stsw-1`) passed MSYS-style paths in `MELEE_MODS_DIR` (use
`pwd -W` paths), so no mod loaded; its game process outlived `timeout` and I killed it (PID I started).

Timeline (logic frame, from the log), all VERIFIED:
- f=260 `00_fd.png`: Mario x=-60, Fox x=60, both grounded on FD.
- f=300..480: on-screen indicator ("STAGE SWITCH IN 3/2/1", `gd.text`).
- f=480: `gd.post_add` full-screen wipe (`stage="final"`, `duration_frames=120`, `clock=true`): a dark
  curtain with a bright edge sweeps in left to right, then out. Because it is the `final` stage it also
  covers the HUD. `01_wipe_early.png` shows it half way (FD half visible, Mario hidden).
- f=540 (curtain full): `gd.stage_add_platform(0,0,900)` temp floor -> `gd.stage_hide(true)` accepted ->
  `gd.stage_add_model{file='GrNBa.dat', symbol='map_head', group=0..6, joint='root'}` x7 (452,171-byte
  file, "loaded /GrNBa.dat (heap 0)"; groups 7+ refused) -> BF's 4 floors added by hand -> temp floor
  removed. **No scene change, no loading screen**; the whole swap took 1.1 ms of wall time.
- f=580 `02_wipe_late.png`: BF already in place behind the retreating curtain; BF's own background
  replaced FD's starfield.
- f=640 `03_bf.png`: BF with main stage and three platforms, Mario and Fox standing on the main floor
  at the same positions (x=-60/60, y=0, grounded), CPU idle (p2 x unchanged 60.0 -> 60.0, 600 frames).
  Percent/stock fields kept (LAB: 0 / no stocks; nonzero percent not exercised).
- f=800: BF removed (7 models + 4 floors), `GrSt.dat` (824,648 B, 4 groups, 1.7 ms) added with
  guessed floors (112 wide main, platforms at +-59.5, 23.45, top 42).
- f=900 `04_ys.png`: Yoshi's Story visuals are right (sky, trees, clouds, platforms) but static; Mario
  at x=-60 was **outside my 112-wide floor and fell** (y=-140.3, and the LAB logged "SCORE -1" on the HUD);
  Fox ended on a platform. This is the real lesson: fighters outside the new floor need placement.
- `gd.stage_hide(false)` restored FD (accepted).

What the probe proves: models of any root-level disc DAT load mid-match (2 stages in sequence, 3 files
resident), the post-pass wipe hides the swap, the temp floor and host hide work, the CPU keeps idling.
What it does not: DAT collision (typed by hand, hence the Mario fall), camera/blast zone change (FD's
were kept), music (not checked by ear; INFERRED unchanged), items/projectiles, ledges, online, savestates.
**Missing call, exactly:** one that returns or installs a destination DAT's `coll_data` (`gd.stage_add_dat_collision(file)`
or similar) and one that applies its `grGroundParam` camera/blast/spawn values.

## 7. Smash Ultimate's Stage Morph as the design reference

**Sources.** SmashWiki, "Stage Morph", https://www.ssbwiki.com/Stage_Morph, CC BY-SA 4.0 (fetched
2026-10-03). A second search result page (Fandom, Dot Esports) could not be read (402/403); nothing
below relies on it. Nothing in this workspace covers Stage Morph: `ports/ir/`, `_research/ultimate-*.md`
(all fighter notes), `experiment/tooling/ultimate/` (a toolkit README for the extracted game files) and
the Ghidra projects (`sora.gpr`, `Ultimate-Kirby.gpr`; fighter code only) contain no stage-morph logic.
The extracted tree's path index has only an unrelated `stage/bossstage_final3/.../stage_change.shpcanim`
and `ui/replace/mark/mark_0_stage_change.bntx`; I did not open them and did not start any analysis.

What it does for the player:
- **Choice:** "choose two different stages on the stage selection screen". VERIFIED (SmashWiki).
- **Timing:** Off / Random / "Every [interval]" 1:00 to 5:00 in 30 s steps; in stock matches Random
  first fires once roughly half of the total stocks are gone. VERIFIED (SmashWiki).
- **Both loaded at start:** "Both stages are then loaded simultaneously and one runs in the background
  to allow a seamless transition with no loading." VERIFIED (SmashWiki). That is design C.
- **Transition look:** the incoming stage's terrain **rises through the sinking terrain** of the
  current stage, no walk-off temporary floor; "both stages will be frozen until the morph is complete";
  camera controls are disabled. VERIFIED (SmashWiki). Duration: not stated by the source I could read.
  INFERRED a few seconds.
- **Fighters:** if a fighter is not inside the new stage's blast lines when the morph ends they are KO'd
  at once. VERIFIED. Whether fighters can act during the morph: the source says the stages are frozen,
  not the fighters; INFERRED fighters can act and the terrain is the thing frozen/moving.
- **Items:** items that cannot spawn on either stage never appear; stage-specific items "will despawn
  when the stage morphs, even if they are currently being held"; portable items (apples) transfer.
  VERIFIED. Projectiles and hazards: not stated; INFERRED hazards end with their stage.
- **Music:** not stated. INFERRED the destination's.
- **Exclusions:** only in "First to 1 Win" or single-stage Elimination/Best Of modes; **custom stages
  cannot be selected**; banned in tournaments. VERIFIED.
- Special Smash gameplay speed also changes the morph timer (SmashWiki search summary; not on the fetched
  text, treat as INFERRED).

**Mapping.** Ultimate is **design C** (pre-loaded pair, one running in the background), with a transition
that hides the geometry change by animating it instead of by a screen wipe. Closest of ours: C.

What Ultimate's rules solve that we would otherwise invent:
1. *Where fighters go:* nowhere. The terrain is arranged so the old and new geometry overlap through
   the transition; fighters stay put and are judged afterwards. The owner's temp full-screen floor is a
   replacement for that overlap; it removes the KO risk but not the "fighter outside the new floor falls"
   problem we saw. Ultimate accepts the KO; our LAB/online should too, or call fighters to spawn points.
2. *Items:* a clear rule (stage-bound despawn, portable carry). We should copy it, including held ones.
3. *Excluded content:* no custom stages. We should start with: legal vanilla stages plus our own missions
   levels, and allow m-ex stages only if static.
4. *Pacing:* a timer, with a Random that waits for the match to develop. Easy for us (frame trigger).
5. *Frozen world during the morph* matches `gd.hitstop` (the clank job): a timed logic freeze exists.

**Recommended rule set for ours** (INFERRED design, modelled on Ultimate plus the owner's sketch):
- Trigger: every N seconds or random after half the stocks are gone, on a logic frame (so it can be
  deterministic online later). Indicator in the HUD during the last 3 seconds.
- Transition: ~1.5-2 s. `gd.hitstop` freezes logic for the swap (so nothing moves while geometry changes);
  a wipe/flash covers it. Order: indicator -> freeze + wipe in -> bench/hold fighters, swap, place -> wipe out.
- Fighters: keep positions if they stand on the new stage's floor; otherwise `fighter_call` to the nearest
  new floor (kinder than Ultimate's KO, and the probe shows why it is needed). Stage-bound items despawn;
  portable ones stay.
- Params: camera bounds, blast zones, spawns and music from the destination at the swap.
- Exclusions: no mid-hazard stages in version 1 (Stadium, Fountain's moving platforms, YS's Randall are
  frozen at a base pose or excluded), online off until native.

## 8. Engine work, in order

1. **Native `coll_data` reader** (game-side C, `script_game.c` beside `script_stage_archive`): expose a
   destination DAT's lines as script lines/platforms with passthrough/ledge flags (M). Prerequisite for
   all stages. Includes a line-budget check against 768/1536/2048.
2. **Apply-destination-params** from `grGroundParam` / map markers: camera bounds, blast zones, spawns,
   music hook (S-M).
3. **Host-agnostic `stage_isolate`** (today FD only): hide any host's map GObjs and disable its joints
   (M); until then the host must be FD.
4. **One atomic `gd.stage_switch{...}`**: bench fighters, hitstop, swap, `fighter_call` onto new floor,
   despawn stage-bound items, one rewind fork (M). Savestate across it must be tested (item 10 of the
   engine-day handoff is the open one).
5. **Stage model animation** (JObj/material anim playback for loaded groups) so YS/DL backgrounds live (M).
6. **Merged preloaded table (design C)** from `Ground_TTMod_BuildCollData`'s pattern, joint-group toggles
   (L), then running a second stage's `on_init` for hazard stages (XL).
7. **Native, frame-triggered version inside the snapshot** for netplay (XL), after 6.

## 9. Credits

- Nintendo / HAL-lineage Melee: the game; doldecomp/melee decompilation, https://github.com/doldecomp/melee
  (our checkout is a fork), consulted for the stage code citations above.
- Super Smash Bros. Ultimate: design reference only. Nintendo, Bandai Namco Studios and Sora Ltd.
- SmashWiki contributors, "Stage Morph", https://www.ssbwiki.com/Stage_Morph, CC BY-SA 4.0; summarised, not
  copied.
- m-ex (akaneia), https://github.com/akaneia/m-ex, via `_research/mex-stages.md` (stage `grFunction` rows).
- HSDLib by Ploaj, https://github.com/Ploaj/HSDLib (vendored under `experiment/tooling/HSDLib`; its
  licence file not re-checked here), for the `coll_data` layout reference.
- No code from any of these was copied. No disc data was committed; the screenshots contain game art
  and stay under `_build/audit-20261003/stage-switch/` (not for commit).
