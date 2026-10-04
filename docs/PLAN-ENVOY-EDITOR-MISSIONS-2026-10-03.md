# SuperTime Envoy, missions and the stage builder: how I'm looking at it

Written 2026-10-03 for GD to read through. **GD's reply the same day: "I still want maze style
generation. Hand built levels are important as well. Blender works fine on both side. Lgtm".** So
the direction is approved with one change, recorded in section 4a: levels are hand-built AND mazes
are generated, both from pieces authored in Blender. Everything else is still a proposal until the
written spec that follows step 0 is approved. It supersedes the Envoy direction in
`HANDOFF-AUDIT-REPAIRS-2026-10-03.md` ("a design conversation before any rewrite"); the problems
recorded in `ENVOY-PROBLEMS-2026-10-02.md` remain the requirements this plan has to answer.

The short version:

1. **Hand-built levels and generated mazes, both made of pieces someone built.** What stops is
   generating geometry from formulas; the generator's job becomes arranging authored pieces.
2. Move level authoring to **Blender**, keep the game as the place levels are loaded, played and
   tuned. The in-game editor stops growing.
3. Make the **mission** the unit everything shares: one folder holding a level's geometry, its
   collision and what happens in it. The builder writes it, the runtime plays it, Envoy sequences it.
4. Rebuild Envoy as a **small run structure on top of missions**, with one clear loop, and throw
   away most of the old 16,000 lines.
5. Build it in thin, playable slices that you test with a controller, because every time I have
   certified something from tests alone it turned out wrong in your hands.

---

## 1. Where things actually stand

Facts, with how each is known.

| Area | State | How I know |
|---|---|---|
| Old Envoy (`melee/pc/scripts/examples/roguelite`) | 31 Lua modules, 16,073 lines. Passes 304 tests. Not accepted. | Your sessions (`ENVOY-PROBLEMS-2026-10-02.md`); the geometry review; a native run with real input |
| Its levels | Seven "authored" rooms: three share about 80% of their geometry, five use the same staircase climb, the seed only shifts floor holes | Independent review with its own reachability code |
| Its traversal | A real fighter crosses room one in about 10 seconds with three jumps: the 18-unit staircase is no obstacle | Native run, Falco, real pad input |
| Its admission test | An analytical jump graph, never real collision | Reading the code |
| In-game map editor (`map_editor`) | About 2,300 lines of Lua. Places kit parts, undo, save/load, bounds, spawns. Mouse click-to-place could not have worked on the real camera until 2026-10-03 (matrix inverse bug) | Found and fixed by the mission lane |
| Mission layer (added 2026-10-03) | Start, enemy waves (timed, positional, trigger-spawned), checkpoints, goal zone, trigger zones, three objectives, lives, time limit. 65 stub tests | Verified natively: full sample run, death and respawn, lives, time-out, restart, both samples completed with real input |
| What nobody has looked at | The mission HUD, banners, marker overlay, the editor's panels and gizmos | I cannot judge UI by eye; you have not been asked to |
| Kit art | One kit: `bf_interior`, 23 parts (floors, walls, ramps, stairs, balconies, doors, glass), authored in Blender, exported by `export_kit.py` | The files |
| Enemies the engine can spawn | Seven kinds: goomba, koopa, redead, like_like, octorok, polar_bear, topi. At most 32 alive at once | `gw_script.c`, the scripting doc |
| Engine limits | 128 placed models across all scripts; up to 200 scripted collision lines; one stage loaded at a time | The editor README and scripting doc |
| Vanilla disc | The LAB, the editor and a mission sample all run on the vanilla disc today. The editor breaks "one folder": its models and samples must be copied in from outside | The vanilla investigation's runs |

## 2. What went wrong, and what I take from it

These are the lessons I'm designing around. Each one is something that actually happened.

1. **Generated geometry was the wrong bet.** The generator produced variations of one idea and an
   analytical check declared them traversable. More generator work would produce more of the same.
   Level quality has to come from someone building levels and playing them.
2. **Tests passed while the game was wrong.** 304 green tests sat on top of a level that plays in
   ten seconds. Engine stand-ins proved the code ran, not that the game was good or even visible.
   From here, a slice is done when it has been played, not when its tests pass.
3. **I can't see UI.** Every editor panel, HUD line and menu was shipped unjudged. The mouse bug
   survived for that reason. Anything visual needs your eyes, so there should be less of it, and
   what there is should be simple.
4. **The loop was never clear.** You said you did not understand the game loop. Genes, a
   collection, fusion, exports, upgrades, a command tree and a route graph arrived before a single
   level was fun to walk through. The order was backwards.
5. **Too much, too early.** A persistence layer with dual checkpoints and transactional economy
   was built for a game whose core had not been played.

## 3. Principles

- **Geometry is built, not computed.** Every piece of floor a player stands on was placed by a
  person in Blender. Generation arranges, connects and dresses those pieces (a maze), or picks
  whole levels; it never invents geometry.
- **One loop, sayable in one sentence**, before any system is added to it.
- **Play first.** Each slice ends with you holding a controller. I measure what can be measured;
  you judge what can only be seen or felt.
- **General capabilities over Envoy-specific code.** Anything Envoy needs from the engine or the
  builder should be usable by any mission or mode (your standing preference).
- **One folder, vanilla disc.** A level pack, the builder's output and Envoy itself each live in
  one folder and run on the vanilla disc.
- **Small files with one job each.** The old `main.lua` was 1,752 lines and near Lua's 200-local
  limit; so is the editor. Nothing new gets built that way.

## 4. The three projects and how they fit

```
   Blender (authoring)                 the game
   ┌──────────────────┐    exports    ┌─────────────────────────────────────┐
   │ kit parts        │ ───────────▶  │ mission folder                      │
   │ level layout     │   one folder  │  level.lua  (parts, collision,      │
   │ mission markers  │               │              bounds, spawns)        │
   └──────────────────┘               │  mission.lua (enemies, triggers,    │
            ▲                         │              objective)             │
            │ hot reload              │  models/     (only what it uses)    │
            └──────────────────────── │                                     │
                                      │ mission runtime ── plays ONE mission│
                                      │ Envoy ── sequences missions into a  │
                                      │          run: pick, reward, finish  │
                                      └─────────────────────────────────────┘
```

The mission folder is the contract. If that format is right, the three projects can move
independently, and the authoring tool can change later without touching the game.

### 4a. Decided 2026-10-03: two kinds of level, one kit of pieces

- **Hand-built levels:** a whole level laid out in Blender, exported as one mission folder.
- **Generated mazes:** the game assembles a level from hand-built **chunks**. A chunk is a
  room-sized piece of real geometry with marked connection points (where it can join another
  chunk, and at what height and facing). The generator lays chunks out as a maze with branches,
  loops and dead ends, and the player physically walks through the result.
- My assumption, to be confirmed: a maze is **one continuous level**, not separate rooms joined by
  doors. The earlier door graph was the thing you rejected.
- Both kinds use the same mission markers (enemies, triggers, pickups, goal), so a chunk can carry
  its own encounter and a maze can place the goal and rewards where the layout makes them matter:
  rewards in dead ends, the exit far from the entrance.
- What makes this different from the old generator: it checked an analytical jump graph over
  computed rectangles. Here connectivity is by construction (chunks join only at authored
  connection points that were built to be walked through), and every chunk has been played on its
  own before it enters the pool.
- The open engine question is the same one as for large hand-built levels, and bigger: a maze of
  many chunks needs geometry and collision loaded and unloaded as the player moves. That is the
  second investigation in step 0.

### Project A: authoring (the stage and mission builder)

**My view: author in Blender, test in the game.**

- The kit already comes out of Blender. Layout would live in the same file as the art.
- Blender already has selection, snapping, duplication, undo, grouping and a real viewport. The
  in-game editor has been re-implementing those one at a time, unseen.
- I can drive Blender directly, so I can build and check geometry there myself, which I cannot do
  with the in-game UI.

What it would be:

- **A Blender add-on** with: a kit library to drop parts from; collision derived from the parts
  (as the kit sidecars do now) plus hand-drawn collision lines where needed; mission markers as
  ordinary Blender objects (start, enemy, checkpoint, goal, trigger zone, camera bounds, blast
  zone); a validator (model and line budgets, unreachable goal, markers outside bounds); and
  "Export mission", which writes one folder.
- **In the game:** `mission load <folder>`, `mission reload` (re-read the folder without
  restarting), and the existing `map mission test` idea: play from a chosen point.
- **The in-game editor is frozen**, not deleted: it stays as a way to nudge a marker or spawn
  against real collision. No new panels, gizmos or tools.

What I don't know yet:

- How smooth the Blender-to-game loop is. A save-and-reload loop of a few seconds would make this
  clearly better than editing in-game; if reload needs a match restart it's merely acceptable.
  This is the first thing I would prototype and time.
- Whether you want to do the level building yourself in Blender, or want me to build levels and
  you to play and direct. Both work; it changes how much polish the add-on's UI needs.

The alternative, kept honest: a standalone editor program. It only makes sense if people without
Blender should make levels. It is a much larger build, and the mission-folder format means it
could be added later without redoing anything.

### Project B: the mission runtime (what a level can do)

This exists and works for the basics. My view is that it needs a short list of additions to carry
an SSE-style level, and one piece of restructuring.

Restructure first: the runtime currently lives inside the editor mod and is embedded into its
main script. It should be its own small module that the editor, Envoy and any other mode load,
and it should read the mission folder, not the editor's document.

Additions, in the order I think they matter:

| Capability | Why | Size |
|---|---|---|
| **Scrolling/large levels** | SSE levels are wider than one screen. Today a level sits inside one stage's bounds. Needs camera bounds and blast zones that follow the player through a long level, and parts loaded as you move (the 128-model limit) | Large; the main engine question |
| **Enemy placement that reads well** | Enemies that hold a position, patrol a span, or guard a ledge, instead of only spawning at a point | Medium |
| **Locked arenas** | "Defeat these to continue": camera locks, exits close, then open. The trigger zones and collision toggles are most of this already | Small |
| **Doors and level exits** | A goal that leads somewhere, so Envoy can chain levels | Small |
| **Pickups** | Healing, a temporary power, a key. Rewards inside a level give routes a purpose | Medium |
| **Hazards and moving platforms** | Variety in traversal | Medium, later |
| **A boss** | A clear finish. A fighter with a rule set (stocks, scale, a script) is the cheap version | Medium |

The large-level question deserves its own short investigation before anything is promised: what
the engine can do about camera, blast zones and streaming parts in and out. Your memory notes say
custom large maps are planned and that loading models anywhere from Lua is the end goal, so this
is the general capability to build, not an Envoy feature.

### Project C: SuperTime Envoy (the run)

**The loop I would propose, in one sentence:** *choose a fighter, fight through a handful of
levels picked from a pool, take one reward between each, beat the boss; lose your lives and the
run ends.*

Everything else is optional until that sentence is fun.

How I'd shape it:

- **Levels:** a run mixes generated mazes and hand-built levels: mazes for exploration, hand-built
  levels for set pieces and the boss. Both come from tagged pools (length, difficulty, theme), and
  the same level or chunk can appear with different enemy sets.
- **Between levels:** one screen, three choices, pick one. The simplest reward system that still
  makes runs differ. Examples: heal, an extra life, a stat nudge, a temporary ability.
- **Failure and finish:** a fixed number of lives for the run; a boss at the end; a results screen.
- **Persistence:** nothing at first beyond "best run". The old dual-checkpoint economy does not
  come back until there is something worth saving.
- **Menus:** one start screen and one reward screen. Both built on the kit's existing menu
  drawing, kept plain enough that I can describe exactly what is on them for you to check.

What I would **keep** from the old Envoy: very little code. Worth harvesting as ideas or small
pieces: the enemy behaviour work (`encounter_behaviors`, `boss_behaviors`), the feedback and
presentation helpers, and the save codec if persistence returns. What I would **drop**: the gene
and collection economy, fusion, exports, the command tree, the route and topology generators, the
room recipes and certification, and the 1,752-line director.

That is a lot to drop, and whether to drop the gene system is your call, not mine. I'm
recommending it because you told me the loop was confusing and that system is most of the
confusion, but you may have wanted it.

## 5. The order I would build it in

Each step ends with something you play. Nothing later starts until the earlier one has been in
your hands.

| Step | What you get | What it proves |
|---|---|---|
| **0. Two short investigations** (no gameplay) | A timed Blender-to-game reload loop; an answer on large scrolling levels | Whether the authoring plan is as good as I think; how big a level can be |
| **1. One level, built in Blender, played as a mission** | A single hand-built level with enemies and a goal, exported as one folder, on the vanilla disc | The whole pipeline end to end; whether a hand-built level is fun to move through |
| **2. That level made good** | Arenas that lock, enemies that hold ground, pickups, a checkpoint that feels right | The mission runtime's additions, driven by what the level actually needs |
| **3. Three levels and a boss** | Enough content for a run | The authoring workflow at small scale; where it hurts |
| **4. The run** | Start screen, level sequence, reward choice, lives, boss, results | The loop |
| **5. Variety** | Enemy variants per level, more rewards, more levels | Whether runs differ enough to replay |
| **6. Packaging** | Envoy as one folder; level packs as folders; all on vanilla | Your standing rule |

I'd expect steps 0 and 1 to be days, not weeks, and to tell us most of what we need to know. I
don't have a reliable estimate for the rest, and I would rather say so than invent one: it depends
almost entirely on how the large-level question and the Blender loop turn out.

## 6. How I would work, given what has gone wrong

- **You see it early.** A level you can walk through in step 1, ugly, before any system exists.
- **I measure, you judge.** I can verify positions, timings, enemy counts, completion, performance
  and that nothing errors. I cannot verify that a level reads well, a menu makes sense or a fight
  is fun. I'll say which is which every time.
- **Screenshots for visuals.** For layout and UI I'll take screenshots and describe exactly what
  is in them, so a blank or broken screen can't pass unnoticed again.
- **Subagents for breadth, on Sonnet,** each in its own files, each required to prove its work in
  the running game. Engine changes and the final build stay with me.
- **The fly cursor is a first-class test tool** (GD, 2026-10-03: "yes make fly a first-class test
  tool"). The mission runtime and the Blender loop get commands built on it: fly to the next
  enemy, checkpoint, trigger or goal; fly to a marker by name; clear the current wave with the
  every-frame hitbox; drop to the floor and hand back to normal control at any point. A level or
  maze can then be toured and smoke-tested in seconds, by you with a controller or by a probe.
  Probes use it for setup and keep real pad input for the behaviour under test, and say which was
  which.
- **Test windows take your controller.** The game stalls with a hidden window, so my test runs
  are visible and compete for the adapter. I'll pause them when you want to play.

## 7. Risks and things I don't know

| Risk | Why it matters | What I'd do |
|---|---|---|
| Large levels may not fit the engine | SSE-style levels are the heart of the request; one stage's bounds may be too small | Investigate first (step 0). Fallback: levels as a chain of screen-sized areas joined by real doors, each hand-built |
| 128-model and 200-line limits | A big level in kit parts can exceed both | Batch parts into larger exported meshes per level section; load and unload sections |
| Seven enemy kinds | Thin for a roguelike | Variants by rule (scale, speed, health, behaviour), fighters as enemies, a boss as a scripted fighter |
| Blender loop slower than hoped | Would weaken the authoring plan | Time it before committing; keep the in-game nudge tools |
| I rebuild the same confusion | A second unclear loop would be worse than the first | One-sentence loop; no system added until the previous slice has been played |
| Envoy's art | Only one kit exists | Decide later whether Envoy needs its own kit; `vk_concepts` exists in the art sources |
| Netplay | Missions and Envoy are offline today | Out of scope until the single-player loop works |

## 8. What I need from you

In rough order of how much they change the plan:

1. ~~Where do levels come from?~~ **Answered:** hand-built levels and maze generation, both.
   Still to confirm: a maze is one continuous level stitched from chunks, not rooms behind doors.
2. ~~Blender for authoring?~~ **Answered:** yes, and both of us build in it.
3. **Is the gene and collection system gone?** Or is there a part of it you want kept.
4. **How long is a level, and a run?** A level of one to three minutes and a run of fifteen to
   twenty is my assumption.
5. **Solo only for now?** I'm assuming one player against enemies, with fighters as occasional
   opponents.
6. **Does Envoy need its own look,** or is the existing kit fine to start?

If the answers to 1 and 2 are "hand-built" and "Blender", the next thing I do is step 0: the two
investigations, with nothing built into the game until you've read their results.

## 9. Step 0 results so far (2026-10-03)

**Large levels and maze stitching: done.** Note: `_research/large-levels-and-maze-stitching-2026-10-03.md`
(every claim tagged VERIFIED or INFERRED). Throwaway code: `_build/spikes/large-levels/`.

- Levels can be very large today with no engine change: the hard limit is 50,000 units on any axis
  (the game asserts beyond it); 10,060 units were run with real input and storeys up to y=3,120 hold.
- What actually binds: the default blast zone (must be extended per level), render cost (every
  loaded model is drawn, on screen or not: about 25-45k triangles loaded at once for the 8.3 ms
  target), and the pools, which are larger than documented (256 instances, 768 collision lines,
  32 assets).
- Streaming works and is cheap: `gd.area_load` / `gd.area_unload` cost 0.05-0.14 ms per chunk with
  a flat heap. So a maze of many chunks is feasible by keeping a window loaded around the player.
- The kit has floor collision only: walls, ceilings and door frames need lines added to the kit
  sidecars and exporter.
- A KO respawns at the host stage's point, so chunks need their own spawn points.
- A toy maze of stitched chunks was walked through door seams with real input; a chunk format is
  proposed in the note (120 x 100 cells, typed ports, door and shaft rules, per-chunk budgets).
- Not tested: enemies far from the origin (the biggest unknown left), ceiling collision, and
  complex vertical traversal by script. GD decided complex traversal tests go to GD by hand until a
  shared traversal bot exists; two levels are packaged for that (section 10 of the note).

**Blender-to-game loop: done.** Note: `_research/blender-to-game-level-loop-2026-10-03.md`.
Throwaway code: `_build/spikes/blender-loop/`.

- Save in Blender to playable in the running game: about 0.6 s for a geometry or marker change,
  0.8 s with new part types, with no match restart (vanilla disc, LAB). The export is 0.5 s; the
  game side is under 0.2 s. So the authoring plan holds.
- A reload restarts the mission (parts and enemies respawn, P1 returns to the start); a refused
  layout leaves the old level running. Hence a "play from marker" command is needed.
- What stands in the way of a one-folder mission today: scripts can only read their own
  `scripts-data` folder and models only load from a mod's `models/`; the editor refuses any part
  not in its generated palette; models are cached by path for the whole scene (a re-export under
  the same name is ignored) with a cap of 32 assets.
- Limits measured: the editor refuses more than 128 parts; a merged mesh may carry at most 32
  collision lines and 65,535 indices; mirroring a part that owns collision is refused; the
  Final Destination slab is still drawn and solid under a level.

**GD played the toy maze and the vertical level (2026-10-03):** "Seemed fine, camera wasn't great.
Idk, look at how other 1P modes do camera stuff (Except we REQUIRE Cstick for attacks, C stick is
NOT for camera)". A third investigation is running on how Melee's 1P modes frame the player
(Adventure's scrolling stages, the Underground Maze, the escape shaft); its note will be
`_research/camera-for-large-levels-2026-10-03.md`. Complex traversal tests are GD's by hand until
a shared traversal bot exists.

**Next:** when the camera note lands, write the spec (`docs/superpowers/specs/`) for GD's review,
with the fly-based test commands and the traversal bot as their own items. Nothing is built
before that.

## 10. Correction, 2026-10-03: the gene system stays

GD: "/home/gd/projects/rust-port-testing in WSL has a lot of things from Sonic Adventure DX/2 we
can attempt to use for the genes dealio. It was based on Chao Garden anyways."

So section 4's recommendation to drop the gene and collection economy is withdrawn. Envoy's genes
were modelled on the Chao Garden, and that idea is part of the game. What changes is how it is
built: from the real Chao mechanics as reference (genes with two alleles, stat grades, growth,
evolution, breeding and inheritance), kept small and understandable, on top of the mission and run
structure, and added only after the basic run is fun.

Reference material: that WSL folder is GD's Sonic Adventure 2 Rust reimplementation; its
`modding-tools/` holds Chao World Extended and its API examples, Chao modding docs, the SA2 and SADX
decompilations and related tools. Research note: `_research/chao-genetics-for-envoy-2026-10-03.md`
(in progress when this was written). Rules that apply: consult, never copy (as with m-ex); nothing
from those games is committed or shipped in a mod; anything taken from the user's own installs
stays local, like the Ultimate fighters.

## 11. Envoy's shape, agreed in conversation 2026-10-03 (third spec, not yet written)

Research: `_research/chao-genetics-for-envoy-2026-10-03.md` (real Chao mechanics cited to code;
why the old gene system confused; three alternative shapes).

GD on the recommended "one companion" shape: "sure that works, but I also want a hub area with more
of the garden mechanics. Also I think enemies dropping our own flavour/variation on chaos drives
would be interesting."

- **One Chao-like companion** with a few readable stats, each with a grade (E-S) and a level; DNA
  with two alleles per trait, blended by the real rules when breeding.
- **A hub area, the garden**, where the companion lives between runs and where the garden mechanics
  happen: raising, feeding, evolution, aging and reincarnation, breeding and eggs. The hub is a
  hand-built level, authored in Blender and loaded as a mission folder.
- **Enemies drop our own variation on chaos drives.** Picking them up in a run feeds the
  companion's stats; different enemies can drop different kinds, so the levels chosen shape how it
  grows.
- **Runs** are mazes and hand-built levels ending in a boss (sections 4a and Project C).
- Duplication is closed structurally (nest cap, a parent must complete a run before mating again,
  mating costs the parent a life), not by patching menus.
- Build order: the run first, then companion levels and type, then grades and lives, then the hub's
  breeding. Creature models: static tinted in the hub first, animation later.
- Chao assets: GD considers shipping them acceptable ("Sonic assets/fangames/mods are very
  acceptable from Sega"). Packaging is still open: a separate asset mod folder (recommended) or
  committed with an explicit exception to CLAUDE.md's rule.

Open: whether the companion visibly follows the fighter in levels or stays in the hub (asked);
how long a companion lives; whether Hero/Dark alignment exists; one companion or a small team.

