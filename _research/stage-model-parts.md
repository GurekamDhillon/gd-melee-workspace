# Melee stage model parts: read-only archive survey

**Research date: 2026-09-27.** Complements [_research/map-editing.md](map-editing.md), which remains the broader stage editing note. Counts below come from `GW_ISO_ACE` through `ports/ir/tools/stage_parts.py`; no game was run. The ISO was read through its FST and the extracted meshes/manifests are confined to `_build/tmp/stage-parts/`. No disc bytes or exported assets are tracked here.

## 10-line summary

1. Yes: a Melee stage is split into model groups, JObj branches, DObjs, and PObj geometry, rather than one baked model.
2. `map_head` contains the model groups; `coll_data` is a separate 2D collision graph.
3. Battlefield has 7 model groups, 73 JObjs, 61 mesh-bearing DObjs, and 64 PObjs in its archive.
4. Its main body is group 6/JObj 12 with 22 DObjs; its left, right, and top platforms are JObjs 13, 14, and 15 with 7 DObjs each.
5. Battlefield's main and upper platform floor lines all belong to one static collision group; none has its own JObj-linked collision group.
6. Final Destination has 92 mesh-bearing DObjs and one unlinked static collision group.
7. Yoshi's Story has 195 mesh-bearing DObjs and a separately linked collision group for Randall.
8. Adventure Mushroom Kingdom (`GrNKr`) has 274 mesh-bearing DObjs and 51 collision groups linked to individual JObjs.
9. The tool exports one static-pose OBJ per mesh-bearing DObj, with PObjs as named OBJ groups and a JSON hierarchy beside them.
10. Lua can provide a platform's collision, but showing a ripped mesh in game still needs a model-loading path or a composed stage DAT.

## How the model is organized

`Gr*.dat` is an HSD archive with named public symbols. `map_head` is the visual/point entry, while `coll_data` is the fighter collision entry. The loader resolves them separately ([`grdatfiles.c`](../melee/src/melee/gr/grdatfiles.c), [`SBM_Map_Head.cs`](../experiment/tooling/HSDLib/HSDRaw/Melee/Gr/SBM_Map_Head.cs), [map-editing note](map-editing.md)). The names `GrNBa`, `GrNLa`, `GrSt`, and `GrNKr` are confirmed by the respective `StageData` paths in [`grbattle.c`](../melee/src/melee/gr/grbattle.c), [`grlast.c`](../melee/src/melee/gr/grlast.c), [`grstory.c`](../melee/src/melee/gr/grstory.c), and [`grkinokoroute.c`](../melee/src/melee/gr/grkinokoroute.c).

`map_head` has an array of model groups, corresponding to stage map GObjs. Each group may carry a root JObj, joint/material/shape animation, camera/fog/lights, and collision link records. A JObj tree supplies parent-child transforms and visibility/other flags. A joint can have a linked list of DObjs; each DObj points to one MObj and a linked list of PObjs. The PObj contains GX vertex attributes and display-list primitives. The MObj supplies render mode, material color/state, and a TOBJ chain for textures. Thus a named platform might be one JObj **but several DObjs split by material**, each with one or more PObjs. Some JObjs are transform or marker nodes with no mesh. The archive generally has no useful JObj class names for these four stages, so the manifest uses stable group-local `JOBJ_<index>` labels where names are absent. See [`HSD_JOBJ.cs`](../experiment/tooling/HSDLib/HSDRaw/Common/HSD_JOBJ.cs), [`HSD_DOBJ.cs`](../experiment/tooling/HSDLib/HSDRaw/Common/HSD_DOBJ.cs), [`HSD_POBJ.cs`](../experiment/tooling/HSDLib/HSDRaw/Common/HSD_POBJ.cs), [`HSD_MOBJ.cs`](../experiment/tooling/HSDLib/HSDRaw/Common/HSD_MOBJ.cs), and [`HSD_TOBJ.cs`](../experiment/tooling/HSDLib/HSDRaw/Common/HSD_TOBJ.cs).

Collision does **not** belong to a DObj or PObj. `coll_data` has XY vertices, ordered floor/ceiling/wall lines, and collision groups with line and vertex ranges. A model group's `GrJoint` links can bind a collision-group index to a JObj index so moving collision follows that joint. A group without such a link is still valid static collision. `Ground_InitMapColl` and `Ground_UpdateMapColl` implement the binding/synchronization ([`ground.c`](../melee/src/melee/gr/ground.c), [`SBM_Coll_Data.cs`](../experiment/tooling/HSDLib/HSDRaw/Melee/Gr/SBM_Coll_Data.cs), [`SBM_Map_GOBJ.cs`](../experiment/tooling/HSDLib/HSDRaw/Melee/Gr/SBM_Map_GOBJ.cs)).

## Measured granularity

Here **piece** means a mesh-bearing DObj: it has its own PObj chain and is exported to one OBJ. A PObj is a finer geometry unit and appears as a separate `g pobj_N` inside that OBJ. Counts cover the archive, including background and alternate model groups; they are not a count of platforms or of meshes visible in one match. Triangle counts are nondegenerate triangles triangulated from GX display lists at rest pose.

| Stage / archive | Model groups | JObjs | Mesh DObjs (OBJ files) | PObjs | Triangles | Collision groups | Collision lines | Archive JObj links |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Battlefield `GrNBa` | 7 | 73 | 61 | 64 | 11,766 | 1 | 23 | 0 |
| Final Destination `GrNLa` | 10 | 95 | 92 | 93 | 12,674 | 1 | 16 | 0 |
| Yoshi's Story `GrSt` | 4 | 72 | 195 | 200 | 7,111 | 2 | 29 | 1 |
| Adventure Mushroom Kingdom route `GrNKr` | 4 | 189 | 274 | 274 | 9,355 | 61 | 324 | 51 |

### Battlefield: which platform is separate?

The playable foreground is model group **6**. Its main body is `g6/j12` (world origin `(0,0,0)`, 22 DObjs, 5,489 triangles). The left platform is `g6/j13` (joint origin `(-48.5,34,0)`, 7 DObjs, 142 triangles); the right is `g6/j14` (`(48.5,34,0)`, 7 DObjs, 142 triangles); and the top is `g6/j15` (`(0,68,0)`, 7 DObjs, 142 triangles). The three platforms are separate sibling JObjs, and each is further split into seven DObjs. These are archive rest-pose locations, not unique mesh names supplied by the DAT. The matching floor lines support the identification:

| Floor line | Endpoints (XY) | Visual part | Collision group |
|---:|---|---|---:|
| 1 | `(-75,0)` to `(75,0)` | main body | 0 |
| 2 | `(-72,34)` to `(-25,34)` | left platform | 0 |
| 3 | `(-23.5,68)` to `(23.5,68)` | top platform | 0 |
| 4 | `(25,34)` to `(72,34)` | right platform | 0 |

All four lines are in **the same unlinked static collision group 0**. The small platforms are individually selectable/renderable JObj branches but do not each own a `coll_data` group or a `GrJoint` link. Side and top floor lines carry the pass-through property. The static body also has ledge-edge floor segments 0 and 5. Moving one visual JObj alone would not move its original floor line.

### Other stages' collision ownership

- **Final Destination:** one collision group covers the fixed stage. None of its ten model groups has an archive collision-to-JObj link. Its central floor is line 1 from `(-75,0)` to `(75,0)`, with short ledge portions at either side.
- **Yoshi's Story:** collision group 1 contains the ordinary fixed stage floors/walls. Group 0 is a one-floor moving piece linked to model group 2/JObj 1, a one-DObj quad, identified as Randall by the group callback and its collision update in [`grstory.c`](../melee/src/melee/gr/grstory.c). The archive has one link; the other playable platforms are part of fixed group 1.
- **Adventure Mushroom Kingdom:** collision groups 0–50 are linked one-to-one to model group 3/JObjs 1–51. Each linked JObj has one 12-triangle DObj; the route code's 1–51 joint list and `Ground_InitMapColl` agree with the archive links ([`grkinokoroute.c`](../melee/src/melee/gr/grkinokoroute.c)). Groups 51–60 are unlinked terrain collision. There are also many visual DObjs with no direct collision ownership.

## Tool and export limits

Run `python ports/ir/tools/stage_parts.py` from the workspace root (or pass one or more `Gr*` names). The entry point reads `GW_ISO_ACE` from `.env`, reads each DAT via the shared read-only FST reader, passes DAT bytes to a small .NET 8 helper backed by local HSDLib, and writes only `_build/tmp/stage-parts/<stage>/hierarchy.json` and OBJ files. It does not copy a DAT to disk. The helper build is under `_build/tmp/stage-parts/build/`. `hierarchy.json` records model groups, joint parent/depth/flags/local and world transforms, DObj/PObj triangle counts, MObj and TOBJ identities, texture map slot/image format/dimensions, collision group ranges and links, and line endpoints/flags/material. `M###`, `T###`, and `I###` are traversal IDs for shared HSD objects within one archive, **not** original numeric material/texture names.

OBJ files have transformed static-pose positions and UVs, and keep each PObj as an OBJ group. They do not embed texture images, TEV shading, animation, lighting, or collision. Seven PObjs across these stages use envelope skinning (3 Battlefield, 2 Final Destination, 2 Yoshi's Story); their OBJ vertices use the owning JObj rest transform and may not match their fully evaluated bind pose. This limitation does not affect the Battlefield playable foreground platform JObjs. The manifest is the authoritative list of exports if the tool is rerun after a different disc revision; old OBJ files are not pruned automatically.

## Reusing a piece

For a custom map with Lua collision, the separate Battlefield platform mesh can be isolated from the group 6/JObj 13, 14, or 15 DObjs and positioned with its joint transform. `gd.stage_add_platform(x, y, width, {passthrough=true})` can supply a matching floor line; the left and right examples each span 47 units at `y=34`, and the top spans 47 units at `y=68`. That API already draws its own simple slab and operates only in an active offline match ([`docs/scripting.md`](../docs/scripting.md)). The current Lua API does not load an OBJ, so displaying the imported art needs a native model/renderer hook or an authored stage DAT. Lua's added line also does not alter the stage's camera/blast bounds.

For a native custom stage DAT, use HSDLib or an equivalent serializer to compose selected JObj branches with their DObj/PObj/MObj/TOBJ dependencies, preserve required transforms and texture data, and author a separate `coll_data` with ordered vertices, lines, groups, flags, and bounds. Add `GrJoint` links where collision must follow a moving JObj. The stage also needs general-point JObjs for starts/respawns and camera/blast markers, suitable parameters, a `StageData`/stage-slot registration, and any behavior callbacks or Lua adapter. Reopen the produced DAT in HSDLib and validate links and counts before a Windows game check. The exported OBJs are an inspection/authoring aid, not a directly loadable Melee stage format. Any game-derived art remains local and out of version control.
