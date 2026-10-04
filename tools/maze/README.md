# Hand-built mazes and connected worlds

Python invokes the missions mod's pure Lua generator. It is a call-through, not a second implementation. `maze_check.lua` and `maze_clearance.lua` independently check actual emitted collision, including stitched seams.

## Offline

```powershell
python -B tools/maze/generate.py 7 --size 12 --kit menu/out_roguelite/room-kit --output _build/tmp/my-maze-mod --prepare-mod
python -B tools/maze/world.py 7 --regions 4 --size 12 --kit menu/out_roguelite/room-kit --output _build/tmp/my-world-mod --prepare-mod
lua tools/maze/check.lua _build/tmp/my-world-mod world
python -B tools/maze/world.py 7 --regions 4 --size 12 --reroll-region 2 --region-seed 99 --kit menu/out_roguelite/room-kit --output _build/tmp/rerolled-world --prepare-mod
python -B -m unittest tools.maze.test_maze tools.port.test_missions tools.blender.test_gd_mission
```

Prepared mods require an empty destination. Existing mission folders are never overwritten. Kits are supplied explicitly; no new art or disc data is included. Models resolve from shared `missions/models/` and offline mission `models/`. Editable recipe data lives at `missions/maze-chunks/library.lua` and `<recipe>/level.lua`. Use `--library` for authored recipes; preparation copies all referenced meshes, sidecars and textures.

## Mounted console

`mission maze <seed> [size]`, `mission maze reroll`, `mission maze map`.
`mission world <seed> [regions] [size]`, `mission world reroll`, `mission world map`.
`mission zones` dumps room, transition and region volumes. Fly/tour are fixtures, not traversal proofs. Generation uses a memory overlay; it does not persist changes to the mounted mod. World preparation yields across logic callbacks, then installs once. The HUD shows committed region and region links. Goal completion uses the existing result/cleanup flow, displays a finish panel and pauses the offline game; restart/reroll/stop release only its owned pause. Failed replacement restores that pause.

## Chunk contract and clearance

Grid size stays130x104 (20x16 metres at6.5 units/metre), one slot1 per side. Left/right centres(0,16)/(130,16), doors y0..32; up/down centre(65,104)/(65,0), floor hole x53..77. Unused slots have two collision faces. The floor holes remain open and require a deliberate hop on horizontal routes: checker action `hop`, cost2, rather than walk cost1. Climbing costs one jump per supporting platform plus the exit; dropping costs1. Cost measures actions, not seconds.

Minimum solid-ceiling headroom is50 units:17.97 measured Ganondorf standing height +29 measured Mario full hop +3.03 tolerance. This is a conservative certificate for those measurements, not a native whole-cast acceptance claim. A `crawl` template tag or `crawl:` surface label explicitly allows20-unit standing clearance, without promising a full hop. Elevated platforms stay at least6 units from walls; ascent steps are at most20; drop receivers have a32-unit landing span. Landing/headroom/wall checks include neighbouring chunks. Opaque model collision cannot be proved here: authored recipes must provide explicit collision lines and render-only kit models.

Starter platforms: x29..61 at y20, x69..101 at y40, x49..81 at y60/80/100. High platforms are removed beneath sealed roofs. To retain full-hop clearance at open vertical seams, solid ceiling faces stop at x43/87, while standable floor strips still stop at53/77. This widens the upward ceiling throat without bridging/moving the24-wide floor hole. Ganondorf's11.1-wide body fits inside that throat when standing on the32-wide high platforms. Door markers and floor-hole slots retain their coordinates. The checker refuses invalid recipes with chunk/object names.

Blender markers retain `gd_exit`, `gd_exit_slot=1`, `gd_exit_chunk`, `gd_exit_traversal`; extra slots/sizes remain unsupported. Library recipes supply local `level`, `sides`, `platforms`, spawn, enemy slots/kinds/budgets and tags. Authored geometry/camera/zones are translated without rotations. Role recipes must support their required exits. World connection points must have an exterior connector-capable authored slot; otherwise generation refuses.

## Maze shape

A seeded loop core, self-avoiding main route and branch chains replace the spine/stub bias. Default chosen route length is max(4,ceil(.55*size)), with size8..20 and explicit length4..size. It is a chosen route, not necessarily the shortest route once loops exist. `--no-loops` produces a tree. Recipe selection avoids identical adjacent recipes when alternatives fit; gallery/vault/well/switchback add kit variations. Each map records branches, longest dead end, route turns, cycles and L/R/U/D counts. `lua tools/maze/metrics.lua` emits the1000-seed sample used in the report.

Difficulty uses actual graph distance. Rewards heal25 once; native void setter readback prevents repeated claims. Connected wave regions are capped at8, with at most32 per wave and32 live tracked enemies globally. Spawns wait for their own committed room and installed floor. A boss-room recipe/visible goal is not a native boss actor.

## World limits

Regions2..6, each size8..20; seed is signed31-bit. Stable derived seeds and fixed reserved positions let one region reroll without changing the others' interior layouts; connector routes may rebuild. Each region has its own theme/template mix. A region cycle gives alternatives for3+ regions; at4+ regions the final boss region is a leaf attached to that cycle. Exterior doors may be horizontal or vertical. A* routes connector chunks without overlapping regional bounds or existing chunks. Everything remains one130x104 chunk graph and one mission install.

Capacity is at most512 total chunks, absolute geometry coordinates below40000, and blast edges200 beyond the world. Capacity checks can reject otherwise valid region/size combinations (for example seed17/6/20 exceeds512); use fewer/smaller regions or a real level change. Loader supports4096 chunks but the generator deliberately caps lower; marker cap is512. Mission enemies remain capped at64 total, allocated by fixed regional quotas. Streaming keeps a3x3 window, or two windows for fly; installs one missing chunk per observation frame. Native pools include256 model instances and128 assets; supplied recipes use at most10 rendered pieces per room and share the kit. Budget hooks bound Lua preparation slices; native asset IO, C parsing and gameplay frame time still need game verification.

Whole-world proof requires start-to-goal and every chunk-to-goal reachability. Every regional connector pair is checked inside that region. Connector chains are checked in both directions unless explicitly marked one-way; one-way paths must still leave all chunks able to reach the goal. Region volumes are display membership and do not replace room commitment/camera zones. Console maps show actual opened regional doors and the world graph.

Envoy must embed the new modules, select world seed/region seeds, map campaign state onto region IDs, and supply its boss actor/objective adapter in the final region. It must preserve the shared streaming/zone ownership and completion policy rather than installing a new mission at every portal. Its bundle is outside this task.

## Smooth traversal and covered startup (follow-up 3)

Streaming performs one load **or** one unload per membership frame, nearest missing room first, with current/fly destination priority. Wave spawns, collision-trigger edits and retirement share that frame budget; unloads are last. A committed-room movement observation starts the next cardinal window when the player enters its forward half. This prepares the next room before commitment, extending the usual 3x3 window by one forward strip (up to 12 rooms); fly retains its two-window path. Filling windows takes priority over queued enemy spawns. Ordinary cardinal travel has three preparation callbacks for the new strip; extremely fast movement, pool exhaustion and failed native calls still need native acceptance. Zone commitment refuses uninstalled rooms.

Spawns are queued one per frame; collision triggers replace one matching instance per frame. Initial CPU preparation retries each callback for at most 600, preserving partial reservations. A refusal names the staging step and readiness reason. Warm-up is a staging phase with a 3600-callback timeout and a duration log. It collects all mission enemies, maze recipe enemy kinds, every root/chunk model (including the goal), root/child `warm_items`, and an already registered `drive` item. Models load one per staging callback. Native `gd.warm` jobs hold release until done; declarations use at most 120 descriptors. Without these APIs, an opaque full-screen cover holds the player while temporary enemies/items/models draw for 24 covered draw frames each, then are removed. Cancellation also removes warm objects/jobs. Item fallback requires `item_spawn`/`item_remove`; drive registration must precede declaration. `gd.area_prepare`/`area_activate` are used together when available, otherwise `area_load` remains supported.

For native covered launch, configure `MELEE_SCENE=maze=7,12;p1=fox;stage=fd` or `mission=first;p1=fox;stage=fd`, or add an engine scene declaration such as `"autostart": "maze=7,12;p1=fox;stage=fd"` to the mod manifest. The bundle's `on_launch` retains the request, `on_tick` advances installation while logic is held, and `launch_ready` releases only after handover/warming. Terminal refusal cancels the hold. Only one eligible gameplay director should expose `on_launch` for an explicit scene.

Lua-only fallback declarations: `missions/autostart.lua` containing `return {mission="first"}` or `return {seed=7,size=12}`; alternatively one folder's `level.lua` may set `autostart=true`. This fallback starts at match load and covers its own staging; hiding the host from the first native loading frame requires the engine launch selector. Ambiguous level opt-ins refuse. A manual stop does not retrigger autostart until the next match. Level `warm_items={"drive"}` lists registered item descriptors, not definitions to load.

Offline tests do not establish 8.3 ms gameplay frames or eliminate pipeline stalls in an old executable. See `_build/tmp/codex-maze-fix3-report.md` for the cold-sandbox acceptance procedure.
