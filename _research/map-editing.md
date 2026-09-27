# Melee stage maps and an editor for GD's Melee

**Research date:** 2026-09-27. This note describes the current decomp and local tooling; it supersedes undated map-editor assumptions, while [_research/mex-stages.md](mex-stages.md) remains the detailed m-ex table/slot reference. Research only: no stage was built or run. Paths below are relative to the workspace root. Names such as `UnkStageDat` reflect incomplete decomp naming; the archive symbols and field layouts are firmer evidence than guessed names.

## 1. Stage files and loading

### Archive versus live stage

A `Gr*.dat` is an HSD archive with several **public symbols**, not one monolithic map object. `map_head` is the entry to model groups, point joints, splines, lights, and associated animation data; `coll_data` is the 2D collision graph. The loader also looks up `grGroundParam`, `itemdata`, `ALDYakuAll`, `map_ptcl`, `map_texg`, `yakumono_param`, `map_plit`, and `quake_model_set`. A symbol can be absent. `itemdata` describes stage item/article resources; it is not the same thing as the item-spawn point joints. See [`grDatFiles_801C6038`](../melee/src/melee/gr/grdatfiles.c#L49), [`UnkStageDat` and `UnkStageDat_x8_t`](../melee/src/melee/gr/types.h#L2030), and [HSDRaw's `SBM_Map_Head`](../experiment/tooling/HSDLib/HSDRaw/Melee/Gr/SBM_Map_Head.cs).

`map_head` contains an array of map model groups. A group can carry a JObj model tree, joint/material/shape animations, camera/fog/light data, and a list of `GrJoint` records linking collision-group IDs to JObj indices. It also holds general-point JObjs and splines. The 3D display tree is thus related to, but separate from, the 2D collision graph; editing a mesh does not automatically change where a fighter stands. See [`UnkStageDat_x8_t`, `UnkStageDat`, `GrJoint`](../melee/src/melee/gr/types.h#L105) and [HSDRaw's `SBM_Map_GOBJ`](../experiment/tooling/HSDLib/HSDRaw/Melee/Gr/SBM_Map_GOBJ.cs).

The `coll_data` structure has XY vertices, 16-byte lines indexed into those vertices, five global line ranges, and collision joints/groups. A line has two vertex indices, adjacency indices for both ends, and high/low flag words. The ranges classify **floor, ceiling, right wall, left wall, and dynamic** lines. Each `MapJoint` has its own ranges, bounds, and contiguous vertex span; runtime `CollJoint` adds the bound JObj and callbacks. A compiler must preserve the ordering and adjacency expected by collision queries, rather than merely writing unordered segments. See [`MapLine`, `MapLineGroup`, `MapJoint`, `MapCollData`](../melee/src/melee/mp/types.h#L47) and [HSDRaw's `SBM_Coll_Data`](../experiment/tooling/HSDLib/HSDRaw/Melee/Gr/SBM_Coll_Data.cs).

**General points** are JObjs assigned a numeric point type. The decomp copies them into `stage_info.x280[261]`; `Ground_801C2D24` resolves a point's world position and includes fallback behavior for missing multiplayer starts/respawns. HSDRaw labels types 0–3 player starts, 4–7 respawns, 127–146 item spawn points, 148–150 camera data, 151–152 blast bounds, 199+ targets, and 252+ bumpers. The decomp specifically reads point IDs `0x94`–`0x96` for camera configuration and `0x97`–`0x98` for blast bounds. These ranges are conventions used by the loaders and stage code, not generic named properties in `coll_data`. See [`Ground_801C34AC`](../melee/src/melee/gr/ground.c#L2519), [`Ground_801C2D24`](../melee/src/melee/gr/ground.c#L2190), [`Ground_801C39C0`](../melee/src/melee/gr/ground.c#L2758), [`Ground_801C3BB4`](../melee/src/melee/gr/ground.c#L2865), and [HSDRaw's point enum](../experiment/tooling/HSDLib/HSDRaw/Melee/Gr/SBM_GeneralPoint.cs).

The live `StageInfo` stores camera limits, blast-zone bounds, internal `grkind`, up to 64 map GObj pointers, the point-JObj table, collision data, params, and stage-object resources. `grGroundParam` can carry a row per external `StKind` using that ground. The stage's C callbacks instantiate and update **yakumono** (the moving/destructible/interactive stage objects); the archive supplies their model/animation/parameter data, not a general event script. See [`StageInfo`, `StageCallbacks`, `StageData`, `GroundParam`](../melee/src/melee/gr/types.h#L19), [`Ground_801C0754`](../melee/src/melee/gr/ground.c#L640), and [`Ground_801C0800`](../melee/src/melee/gr/ground.c#L809).

### Selection and load path

`StKind` is the external stage ID used by match/mode setup. `GrKind` selects the internal ground implementation and its `StageData` row. `stage_id_map[]` converts between them, so several external mode IDs may share ground code, while the Adventure route grounds have separate internal kinds. The important route kinds are `KinokoRoute` (`0x1f`), `ShrineRoute` (`0x20`), `ZebesRoute` (`0x21`), and `BigBlueRoute` (`0x22`). See [`GrKind`/`StKind`](../melee/src/melee/gr/forward.h#L59), [`stage_id_map` and `Stage_8022519C`](../melee/src/melee/gr/stage.c#L358), and [`stage_datas`](../melee/src/melee/gr/ground.c#L166).

There are at least three different meanings of a “stage list”:

| List | What it controls | Source |
|---|---|---|
| `StageData` rows | Internal `GrKind` → file path (`/Gr*.dat`), map-GObj callbacks, init/load/start routines, and collision JObj links | [`StageData`](../melee/src/melee/gr/types.h#L105), [`stage_datas`](../melee/src/melee/gr/ground.c#L166) |
| VS stage select | Icons/availability; the retail static menu has 29 selectable stages plus Random, and the port has m-ex expansion paths | [`mnstagesel.static.h`](../melee/src/melee/mn/mnstagesel.static.h#L11), [_research/mex-stages.md](mex-stages.md) |
| 1P Adventure | An ordered scene/match state machine, including route maps, fights, bonus rounds, and mode-specific rules; it is **not** the VS menu order | [`gm_Mode_Adventure_States` and scene IDs](../melee/src/melee/gm/gmadventure.c#L40), [`gm_803DE650`](../melee/src/melee/gm/gmadventure.c#L699) |

On entering a stage, ground setup resolves `StKind` to `GrKind`, chooses the `StageData`, loads its archive, finds `map_head` and the other public symbols, reads the applicable params, loads `coll_data` into `mpLibLoad`, and runs stage init/load/start callbacks. Up to four archive records can be live in `grDatFiles`, although that is an archive-slot count, not a streaming system. See [`Ground_801C0754`](../melee/src/melee/gr/ground.c#L640), [`Ground_801C0800`](../melee/src/melee/gr/ground.c#L809), [`grDatFiles_801C6038`/`grDatFiles_801C62B4`](../melee/src/melee/gr/grdatfiles.c#L49), and [`mpLibLoad`](../melee/src/melee/mp/mplib.c#L883).

The retail VS stage IDs occupy external `StKind` `0x02`–`0x20` (the 29 selectable entries are an icon subset), while Adventure's special route entries are later IDs: `0x3B` Mushroom Kingdom, `0x3F` Underground Maze, `0x42` Brinstar escape, and `0x49` F-Zero/Big Blue. Other Adventure scenes reuse VS ground implementations. The **Adventure scene IDs** are a third numbering scheme: `gmadventure.c` groups twelve themed blocks (Mushroom Kingdom, Kongo Jungle, Underground Maze, Brinstar, Green Greens, Corneria, Pokémon Stadium, F-Zero, Onett, Icicle Mountain, Battlefield, Final Destination), with fights/cutscenes inside each block. Keep all three IDs distinct in tooling. See [`StKind`](../melee/src/melee/gr/forward.h#L145), [`stage_id_map`](../melee/src/melee/gr/stage.c#L358), [VS icons](../melee/src/melee/mn/mnstagesel.static.h#L11), and [Adventure scene enum](../melee/src/melee/gm/gmadventure.c#L40).

## 2. Static platforms, pass-through, and ledges

A basic platform needs a visible JObj/mesh and a **floor collision line** at the intended standing height. The two need to agree in world space but can be authored separately. For a solid block, add the other appropriate ceiling/wall lines and adjacency; a one-way platform can consist of a floor edge alone. The port's Target Test platform extension provides a small concrete construction: it appends two vertices, one `MapLine` flagged `CollLine_Floor | LINE_FLAG_PLATFORM`, and a `MapJoint` whose floor range points to that line. See [`Ground_TTMod_BuildCollData`](../melee/src/melee/gr/ground.c#L690) and [`Ground_TTMod_InitLines`](../melee/src/melee/gr/ground.c#L794).

`LINE_FLAG_PLATFORM` (bit 8) marks the floor as **pass-through**. The collision checks use that bit when deciding whether a fighter may pass through/drop through the floor; it does not mean “a visual platform.” `LINE_FLAG_LEDGE` (bit 9) marks a line eligible for ledge handling; ledge checks inspect this flag and endpoint/geometry conditions. It does not by itself make an arbitrary edge a valid grab. The collision-kind bits are floor `1`, ceiling `2`, right wall `4`, left wall `8`. Keep material/physics and ledge flags explicit in the editor rather than inferring them from colors or meshes. See [`CollLine_*`, `LINE_FLAG_*`](../melee/src/melee/mp/forward.h#L64), [pass-through check](../melee/src/melee/mp/mpcoll.c#L1465), and [ledge query](../melee/src/melee/mp/mplib.c#L3330).

## 3. Moving platforms and their collision

The stage archive's collision link maps a collision-group ID to a model JObj index (`GrJoint`/HSDRaw `CollisionLinks`). When the stage creates a map GObj, `Ground_InitMapColl` binds those collision joints to the JObjs through `mpLib_800552B0`. `Ground_UpdateMapColl` and `mpLib_80055E9C` then transform the group's source XY vertices using the JObj state and refresh runtime line positions/bounds. The normal update path animates the JObj and then runs the stage GObj callback; helpers explicitly resync wind and map collision. A moving visual without this binding leaves its floor behind. See [`Ground_InitMapColl`/`Ground_UpdateMapColl`](../melee/src/melee/gr/ground.c#L2255), [`mpLib_80055E9C`](../melee/src/melee/mp/mplib.c#L4855), [`HSD_JObjAnimAll` update path](../melee/src/melee/gr/ground.c#L1425), and [`gr/inlines.h`](../melee/src/melee/gr/inlines.h#L30).

Examples worth importing into an editor test corpus:

| Stage | What the code demonstrates | Source |
|---|---|---|
| Fountain of Dreams (`grIzumi`) | Animated/up-and-down platforms with yakumono state and collision resync | [`grIzumi` setup and update](../melee/src/melee/gr/grizumi.c#L302) |
| Rainbow Cruise (`grRCruise`) | Model animation/scrolling scenery with linked moving collision | [`grRCruise`](../melee/src/melee/gr/grrcruise.c#L250) |
| Brinstar (`grZebes`) | Multiple stage-object updates, including moving/destructible collision | [`grZebes`](../melee/src/melee/gr/grzebes.c#L385) |
| Big Blue VS and Adventure route | Vehicle/road collision and a separately scripted progression stage | [`grBigBlue`](../melee/src/melee/gr/grbigblue.c#L412), [`grBigBlueRoute`](../melee/src/melee/gr/grbigblueroute.c#L380) |
| Mushroom Kingdom route | Side-scrolling map GObjs and camera/progression driven updates | [`grKinokoRoute`](../melee/src/melee/gr/grkinokoroute.c#L348) |

For a new moving platform, author (1) a model JObj, (2) a collision joint with its own vertex span and line ranges, (3) a `GrJoint` link from group ID to that JObj, (4) animation or a deterministic per-frame transform, and (5) per-frame collision sync after the transform. Validate its floor direction, endpoint/ledge flags, bounding box, hiding/disabling behavior, fighter carrying (`mpGetSpeed`), and replay/rollback determinism. The last items are engineering requirements inferred from [`CollJoint`](../melee/src/melee/mp/types.h#L108), [`mpLib_80055E9C`](../melee/src/melee/mp/mplib.c#L4855), and [`mpGetSpeed`](../melee/src/melee/mp/mplib.c#L5124); the decomp does not supply a reusable “moving platform component.”

## 4. 1P Adventure scripting: mode, stage, and data

Adventure behavior is split across **`gm` progression**, **`gr` stage callbacks**, and **archive data**. `gmadventure.c` defines the scene sequence, opponent/match setup, timers and transitions. A route's `gr*.c` code owns local camera/checkpoint state, marker tests, map-object visibility, enemy requests, and collision callbacks. `Gr*.dat` supplies marker JObjs, collision, models, and yakumono parameters. This is executable C behavior, not a generic event track encoded in `map_head`. See [`gm_Mode_Adventure_States`](../melee/src/melee/gm/gmadventure.c#L119), [`gm_801B4064`](../melee/src/melee/gm/gmadventure.c#L1302), [`StageCallbacks`](../melee/src/melee/gr/types.h#L105), and [`grDatFiles_801C6038`](../melee/src/melee/gr/grdatfiles.c#L49).

The archive load itself goes through [`lbArchive_80016DBC`/`lbArchive_800171CC`](../melee/src/melee/lb/lbarchive.c#L127). Ground setup registers stage `itemdata` through the item system ([`Ground_801C0800`](../melee/src/melee/gr/ground.c#L809)); route enemies are item objects created by functions such as [`it_8027B5B0`](../melee/src/melee/it/itzako.c#L53). Mid-route fighter encounters are configured by [`gm_801674C4`](../melee/src/melee/gm/gm_1601.c#L3471); normal player allocation reaches [`Fighter_Create`](../melee/src/melee/ft/fighter.c#L994) through [`player.c`](../melee/src/melee/pl/player.c#L232). These are separate spawn mechanisms and should become separate editor actions.

The reusable marker mechanism tests a fighter against point-JObj-centered regions, including point IDs `0x99`–`0xB2` and `0xBD`–`0xC6`. `Ground_801C3D44`/`Ground_801C3DB4` arm/query this machinery. The route code also directly compares player/camera X against authored points and tracks counters. `grZakoGenerator` spawns stage enemies from point markers when their positions are relevant to the camera/blast region; item/fighter creation goes through separate `it`/`gm` paths. See [`Ground` marker scan](../melee/src/melee/gr/ground.c#L990), [`Ground_801C3D44`/`Ground_801C3DB4`](../melee/src/melee/gr/ground.c#L2948), and [`grZakoGenerator`](../melee/src/melee/gr/grzakogenerator.c#L147).

| Segment | Trigger → action → advancement | Source |
|---|---|---|
| Mushroom Kingdom route | Per-frame camera/fighter progress and marker proximity change phases, move checkpoint/respawn state, and start the **mid-level Yoshi fight** with `gm_801674C4(0x11, 0xA, 3, 0xB3, ...)`. The stage pauses/stops ordinary enemy generation around the encounter and resumes/advances after its completion callback; `gm` later uses flagpole completion time to choose a later opponent variation. | [`grKinokoRoute_80207C88`](../melee/src/melee/gr/grkinokoroute.c#L348), [`gm_801674C4`](../melee/src/melee/gm/gm_1601.c#L3471), [`gm_801B44A0`](../melee/src/melee/gm/gmadventure.c#L1413) |
| Underground Maze | Authored point regions and local state gate encounters; the stage toggles model/collision visibility, starts the Link encounter via `gm_801674C4`, changes respawn/checkpoint, and manages the enemy generator. | [`grShrineRoute`](../melee/src/melee/gr/grshrineroute.c#L415) |
| Brinstar escape | The route reads a timer parameter, counts down in its camera/event callback, and a collision callback marks reaching the terminal region; Adventure match setup also supplies the escape time limit and timeout/exit handling. | [`grZebesRoute`](../melee/src/melee/gr/grzebesroute.c#L160), [`gmadventure.c`](../melee/src/melee/gm/gmadventure.c#L857), [`gm_801B47FC`/`gm_801B4860`](../melee/src/melee/gm/gmadventure.c#L1490) |
| F-Zero / Big Blue route | Route callback follows player/camera X, updates checkpoints and stage state while the stage's car/road objects run; mode code selects the route scene and next match. The route and VS Big Blue have distinct `gr` files. | [`grBigBlueRoute`](../melee/src/melee/gr/grbigblueroute.c#L380), [`gmadventure.c`](../melee/src/melee/gm/gmadventure.c#L1049), [`grBigBlue`](../melee/src/melee/gr/grbigblue.c#L412) |

The general pattern to preserve in a new scripting layer is **guarded, one-shot state transitions**: a camera/progress threshold, spatial point region, timer, defeat/completion callback, or collision-joint touch changes a stage phase; that phase spawns fighters/enemies/items, enables objects, sets checkpoints, and ultimately signals the mode scene to advance. The existing completion/status hooks are [`Ground_801C5740`/`Ground_801C5750`/`Ground_801C5764`](../melee/src/melee/gr/ground.c#L3956). A map editor should expose such events explicitly rather than hide them in arbitrary model names.

## 5. Existing tools and local assets

| Tool/source | Useful today | Limit |
|---|---|---|
| [HSDLib/HSDRaw and HSDRaw Viewer](https://github.com/Ploaj/HSDLib); local [`experiment/tooling/HSDLib`](../experiment/tooling/HSDLib) | Parses Melee `map_head`, model groups, points and `coll_data`; Viewer has collision rendering and COLL/SSF import/export plus SVG export ([collision menu](../experiment/tooling/HSDLib/HSDRawViewer/ContextMenus/Melee/CollDataContextMenu.cs)). Strong format reference and import/inspection base. | A DAT/asset editor, not an Adventure event editor or large-map runtime. Check its license and project status before embedding code. |
| [m-ex](https://github.com/akaneia/m-ex) and [mexTool](https://github.com/akaneia/mexTool) | Expanded stage slots, tables, and code payload integration; local [_research/mex-stages.md](mex-stages.md), [`tools/mex_port/README.md`](../tools/mex_port/README.md), and [`gw_mex_grfunction.c`](../melee/pc/platform/gw_mex_grfunction.c) document our port path. | Stage registration/runtime expansion, not a geometry or trigger editor. Our notes say consult m-ex code but do not vendor it. |
| Local [Target Test Blender tooling](../tools/blender/README.md) | Existing authoring flow for `.tt` targets and simple static platforms. | Specific to Target Test; no general `Gr*.dat` authoring. |
| [Geno scripting](../docs/scripting.md) and [LAB API](../melee/docs/geno.md) | Lua lifecycle/debug draw and existing game scripting context. | Current documented API does not yet establish a general runtime stage-authoring contract. The sibling `worktrees/codex-stage-lua` report and `gd.stage_add_platform`, `gd.stage_add_line`, `gd.spawn_target` were not present in the searched files on 2026-09-27; treat them as in-flight until that branch reports its signatures and constraints. |

**“Stage Builder” naming caveat:** no verified open-source *Melee* Stage Builder source was located in this pass. HSDRaw Viewer is the concrete Melee stage/collision editor found here. Nintendo's similarly named builders for later Smash games do not establish a Melee DAT format or usable source base. Do not plan an import format around an unidentified tool.

## 6. Proposed map editor and runtime

### One editable map IR

Use a versioned, text-serializable map IR (JSON/YAML on disk; typed objects in the editor), separate from HSD archive offsets. Give every object a stable ID and explicit coordinate units. Suggested top-level records:

```text
map: metadata, mode/slot targets, bounds, asset references, version
visuals: mesh/model trees, transforms, materials, animation references, culling groups
collision: vertices + directed line segments, kind, material, pass_through,
           ledge_left/right, adjacency, collision group, visibility
platforms: visual ID + collision group ID + static transform or keyframed path
           (frame times, easing, loop/ping-pong, start phase)
points: P1–P4 starts, respawns/checkpoints, item spawns, enemy spawns, targets
camera: initial framing, min/max bounds, optional progress rail/regions
blast: per-region or whole-stage left/right/top/bottom
triggers: spatial region, x/camera threshold, timer, KO, line touch, and phase guards
events: ordered actions + Lua handler name; saveable deterministic phase/state
```

The editor should show the visual mesh and collision overlay independently; let authors inspect line direction, one-way behavior, ledge endpoints, joint link, camera window, blast zone, and spawn safety at a selected frame. Keyframed platforms need the same transform sampled by both rendering and collision. Trigger execution should run on a fixed simulation frame with deterministic ordering and serialized state for rollback/replay; scripts should request bounded engine operations (spawn fighter/enemy/item, toggle object/collision, set checkpoint, set timer, mark scene complete). This design follows the observed data/code split above; it is a proposal, not an existing file format.

### Two output paths from the same IR

1. **Archive path for finished stages.** Compile visual/JObj groups and animations into HSD `map_head`; pack ordered vertices/lines/groups into `coll_data`; emit general-point JObjs, camera/blast markers, and `grGroundParam`/yakumono params as needed. Allocate/register a `StKind`→`GrKind` and `StageData` slot (possibly through our m-ex port). A small native stage adapter loads the Lua event program and dispatches on load, frame, collision touch, and scene completion. Validate the emitted DAT by reopening it with HSDRaw and checking group/point/line round trips. This still requires native integration: data alone cannot reproduce arbitrary Adventure C callbacks.
2. **Runtime path for grayboxing.** Once the sibling stage-Lua worktree publishes a report and API contract, compile the same IR into calls such as `gd.stage_add_platform`, `gd.stage_add_line`, and `gd.spawn_target`, plus Lua triggers. Confirm ownership/lifetime, collision group and flag exposure, update order, network determinism, and array limits before promising moving platforms or large maps through this path. Until then these names are requested/in-flight APIs, not demonstrated capabilities.

### Large-map constraints to design around

- **Collision capacity:** `mplib.c` has fixed runtime arrays sized for **2048 vertices, 1536 lines, and 256 joints**; `MapLine` indices are `u16`, but the smaller actual arrays and signed `s16` range fields bind first. `mpLibLoad` populates them. The compiler must reject over-budget maps and count joint/line groups after compilation, including hidden regions. See [`mplib.c` static arrays](../melee/src/melee/mp/mplib.c#L77), [`mpLibLoad`](../melee/src/melee/mp/mplib.c#L883), and [`MapLineRange`](../melee/src/melee/mp/types.h#L92). Do not assume a large file can simply be loaded.
- **Object and point capacity:** `StageInfo` has 64 map-GObj slots and a 261-entry point-JObj table. Reserve IDs deliberately for route markers, item spawns, targets and camera/blast markers; validate duplicate/out-of-range assignments. See [`StageInfo`](../melee/src/melee/gr/types.h#L19) and [`Ground_801C34AC`](../melee/src/melee/gr/ground.c#L2519).
- **Camera and death plane:** the archived camera and blast markers initialize finite bounds. A long route needs authored camera progress, safe respawns, and a deliberate blast-zone policy. Merely widening the bounds can produce unusable zoom; the Adventure routes demonstrate camera/checkpoint code layered over stage parameters. See [`Ground_801C39C0`/`Ground_801C3BB4`](../melee/src/melee/gr/ground.c#L2758), [`grKinokoRoute`](../melee/src/melee/gr/grkinokoroute.c#L348), and [`grBigBlueRoute`](../melee/src/melee/gr/grbigblueroute.c#L380).
- **Memory and streaming:** collision is loaded as a stage-wide graph and archive slots are finite; spatial bounding checks/culling exist, but that is not evidence of seamless collision/asset streaming. Begin with region activation and hidden/inactive yakumono inside the existing budget. True streaming would need a native collision replacement/relocation design, safe timing, camera/respawn continuity, and deterministic synchronization. Measure asset memory, texture/model size, animation cost, update time, and draw cost on Windows before setting a map-size target. See [`mpLibLoad`](../melee/src/melee/mp/mplib.c#L883), [`grDatFiles_801C62B4`](../melee/src/melee/gr/grdatfiles.c#L140), and [`mpLib_80055E9C`](../melee/src/melee/mp/mplib.c#L4855).

### Staged build plan

1. **Format audit:** use an original-compatible, legally sourced sample stage to produce a read-only inspector for models, points, collision groups, bounds and links; compare with HSDRaw and the decomp. Keep disc-derived assets out of version control.
2. **Static graybox:** define/validate the IR; author one room with floors, walls, pass-throughs, ledges, spawn/respawn, camera and blast bounds; export through the runtime Lua path if its API is ready, otherwise through a minimal DAT/adapter path.
3. **Motion:** add keyframed JObj-linked platforms and per-frame collision sync; test carrying, ledges, hiding, and rollback at path endpoints.
4. **Adventure slice:** reproduce one Mushroom Kingdom-style threshold → encounter → checkpoint → exit chain with deterministic Lua events; expose enemy/item/fighter spawn and scene-advance hooks explicitly.
5. **Long route:** author several regions; instrument collision counts, memory, frame cost and camera behavior; choose activation or native streaming only from measurements.
6. **Editor round trip:** add timeline/trigger UI, import existing `Gr*.dat` subset, compile and reopen output, then package validation messages with source-object IDs for authors.

## 10-line summary

1. `Gr*.dat` is an HSD archive; `map_head` and `coll_data` are separate public symbols.
2. Model/JObj trees, animations, collision groups, and general-point JObjs jointly define a stage.
3. `StKind` selects an external stage; `GrKind` and `StageData` select its ground code and archive.
4. A static platform pairs visible geometry with directed floor collision and explicit flags.
5. Pass-through and ledge behavior are line flags, with additional collision rules at runtime.
6. Moving collision follows a linked JObj and must be synchronized after animation each frame.
7. Adventure events live mainly in `gm` progression and `gr` callbacks, using authored point markers.
8. HSDRaw and m-ex provide format/editing and slot infrastructure, but no complete event editor.
9. Build one validated map IR with archive and, when proven, Lua runtime output paths.
10. Large maps require measured collision/memory budgets, camera/checkpoint design, and deterministic events.
