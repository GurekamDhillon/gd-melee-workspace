# Mission folders, large levels and the Blender loop: design

Date: 2026-10-03. Status: **draft for GD's review; nothing in it is built.** First of three specs
from `docs/PLAN-ENVOY-EDITOR-MISSIONS-2026-10-03.md` (direction approved by GD the same day:
hand-built levels and maze-style generation, authored in Blender). The other two follow this one:
the maze generator, and SuperTime Envoy's run structure. The camera is section 8.

Evidence this design rests on (measured in the running game, vanilla disc):
`_research/large-levels-and-maze-stitching-2026-10-03.md` and
`_research/blender-to-game-level-loop-2026-10-03.md`.

## 1. Goal

A level is **one folder**. Blender writes it, the game loads it from anywhere inside a mod, plays
it, reloads it in under a second, and can hold levels far larger than a stage by keeping only the
part around the player loaded. Everything here is a general capability: hand-built levels, maze
chunks, Envoy and any other mode use the same pieces.

Success means GD can: build a level in Blender, press export, see it in the running game in about
a second, fly to any marker, play from there with a controller, and ship the result as one folder
that runs on the vanilla disc.

Out of scope for this spec: the maze generator, Envoy's run, rewards, menus, new enemies, netplay.

## 2. What exists and what was measured

- Levels can already be huge: the hard limit is 50,000 units on any axis; 10,060 units were run
  with real input; floors hold at every height tested (to 3,120).
- Streaming works: `gd.area_load` / `gd.area_unload` cost 0.05-0.14 ms per chunk, heap flat.
- Blender save to playable: about 0.6 s (0.8 s with new part types), no match restart.
- The mission runtime (waves, checkpoints, goal, triggers, objectives, lives, time limit) works
  and was verified natively; it lives inside the map editor mod today.
- GD played a toy maze of stitched chunks and a 13-storey level: "Seemed fine, camera wasn't great."

What does not work, each found by a run:

| # | Problem | Evidence |
|---|---|---|
| P1 | A level cannot be one folder: scripts read only `scripts-data/<script id>/`, models load only from a mod's `models/`, the editor accepts only a plain file name | Blender note, obstacle 1 |
| P2 | The editor refuses any part not in its generated palette | `unknown kit part` |
| P3 | Models are cached by path for the whole scene and never freed; a re-export under the same name is ignored; cap of 32 assets | `model cache full (32 scene-pinned assets)` |
| P4 | A reload restarts the mission from the start | Blender note |
| P5 | The host stage (Final Destination's slab) is still drawn and solid under a level | Blender note, screenshot |
| P6 | Default blast zones KO a fighter at x=300; a KO respawns at the host stage's point | Large-levels note |
| P7 | Every loaded model is drawn whether on screen or not (no culling): about 25-45k triangles loaded at once for the 8.3 ms target | Large-levels note |
| P8 | The kit has floor collision only; walls, ceilings and door frames have none | Large-levels note |
| P9 | Limits: editor refuses more than 128 parts; a mesh may carry at most 32 collision lines and 65,535 indices; mirroring a part that owns collision is refused; `gd.fly_target` accepts only +/-10,000 | Both notes |
| P10 | Not yet tested: enemies far from the origin, ceiling collision | Large-levels note |

## 3. The mission folder (the contract)

```
<mod>/missions/<name>/
  level.lua        geometry: parts or sections, collision, bounds, blast zones, spawns
  mission.lua      what happens: enemies, waves, triggers, checkpoints, goal, objective
  models/          only the models this level uses
  chunks/          optional: streamed sections for a large level (one sub-folder each)
```

- `level.lua` keeps today's layout format (`version`, `units`, `parts`, bounds, spawns) so
  existing layouts load unchanged; `mission.lua` is today's `mission` table moved to its own file
  (a `mission` table inside `level.lua` still loads).
- Paths inside a mission folder are relative to it. Nothing outside the folder is referenced, so
  the folder can be copied, zipped or shipped inside a mod as it is.
- A large level lists `chunks`, each with a rectangle in level space and its own `level.lua` and
  models; the runtime loads the chunks near the player. A small level has no chunks.
- Text files are data loaded in an empty environment and validated before anything changes, as
  layouts are today. A refused folder leaves the running level untouched.

## 4. Engine work

In dependency order. Sizes are S (hours), M (a day or two), L (several days); they are estimates
from the investigations, not commitments.

| # | Change | Where | Size | Fixes |
|---|---|---|---|---|
| E1 | Read files and load models from a mission folder inside any mounted mod: a script may open `missions/<name>/...` under its own mod (and, read-only, under another mod named in its manifest) | `gw_script.c` data and model path resolution, `gw_mods.c` | M | P1 |
| E2 | Model assets keyed by content, freed when no instance uses them; a changed file under the same name loads as a new asset; raise the asset cap or make it follow memory | `script_model*.inc`, `gw_script_model_*.inc` | M | P3 |
| E3 | Hide the host stage: a call that stops drawing the host stage's models and disables its collision for the match, restored on match end | `script_game.c` / stage hooks | S-M | P5 |
| E4 | Per-level blast zones and respawn: bounds set from the level; the respawn point follows the mission's checkpoints wherever the level is | Mostly Lua over existing `stage_set_*` calls; verify the rebirth platform far from the origin | S | P6 |
| E5 | Skip drawing model instances outside the camera's view | `script_model_order.inc` / the batcher | M | P7 |
| E6 | Wall, ceiling and door-frame collision in the kit sidecars and the exporter | `export_kit.py`, the sidecar reader | S-M | P8 |
| E7 | Raise or document the limits that bite: parts per level (128), lines per mesh (32), `fly_target` range (10,000) | Editor Lua, model sidecar reader, `geno_lab_mode.c` | S each | P9 |
| E8 | Reads a traversal bot needs: floor under the fighter, wall and ledge contact, pass-through state, jumps left | `script_lab.h`, `script_game.c`, `gw_script.c` | S-M | Traversal bot (section 7) |

Each engine change lands with a headless test where one can express it, and with a native run on
the vanilla disc that shows the problem gone. Changes are additive: a level or mod that does not
use them behaves as before.

## 5. Mission runtime

- Moves out of the editor mod into its own module that the editor, Envoy and other modes load.
  The pure state machine (`mission.lua`, already separate) is unchanged.
- Loads a mission folder (E1), builds the part catalogue from the folder's `models/` (fixes P2),
  hides the host stage (E3), applies bounds and blast zones (E4).
- **Chunk streaming:** a small manager keeps the chunks around the player loaded (a 3x3 window by
  default) using `area_load` / `area_unload`. Each chunk carries its own spawn point, so a KO
  returns the player to the chunk they were in.
- **Reload:** watches `level.lua` and `mission.lua` (polled every 15 frames) and reloads
  atomically; `mission reload` does the same on demand. A reload keeps the match, the fighter and
  unchanged assets.
- **Play from a marker** (fixes P4): `mission play from <marker>` starts with the state the
  mission would have on reaching that marker (earlier waves cleared, checkpoint set), so a tweak
  near the end does not mean replaying the start.

## 6. Fly-based test commands (first-class, per GD)

Built on the existing debug fly cursor; usable from the console, a controller shortcut and probes.

- `mission fly next|prev` and `mission fly <marker>`: fly to the next enemy, checkpoint, trigger
  or goal, or to a marker by name.
- `mission clear`: defeat the current wave with the every-frame hitbox.
- `mission drop`: land on the floor below and return to normal control.
- `mission tour`: visit every marker and chunk in order and log what loaded, for a smoke test of a
  whole level or maze in seconds.

Probes use these for setup and keep real pad input for the behaviour under test, and say which was
which in their evidence.

## 7. Traversal checking

- **By GD, by hand,** for anything complex: jumps with timing, vertical routes, whether a route is
  fair. This is the rule until the bot below exists and has earned trust.
- **A shared traversal bot** (its own piece of work, after E8): waypoints in, real pad inputs out,
  closed-loop (walk, run, short hop, full hop, double jump, drop through, retry), reporting
  whether it arrived and how long it took. Its bar for use: it completes the vertical test level's
  routes and the toy maze's shaft reliably. Until it meets that bar no agent may report a
  traversal verdict from a hand-written input script.
- The bot proves a route is possible. It does not say a route is good.

## 8. Camera

GD, after playing the toy maze and the vertical level: "camera wasn't great ... look at how other
1P modes do camera stuff (Except we REQUIRE Cstick for attacks, C stick is NOT for camera)".
Evidence: `_research/camera-for-large-levels-2026-10-03.md` (decomp citations plus recordings from
Adventure's stages, a versus stage, the toy maze and the vertical level).

**How Melee's own levels do it.** Adventure's side-scrolling stages use the ordinary camera. The
stage moves its "origin" to the player every frame (a 10-unit leash and a vertical clamp), and the
camera bounds and blast zones are stored relative to that origin, so the camera lives in a small
window that travels with the player. Measured windows: Mushroom Kingdom 249 x 177, the Underground
Maze 167 x 97, the Brinstar escape shaft 150 x 180 with x locked. Zoom is each stage's fixed
minimum distance and never changes while moving. Look-ahead is the fighter's camera box extended
in the facing direction, not velocity.

**Why ours looked wrong.** The camera's yaw and pitch are computed from the player's distance to
the origin, which stayed at 0, so far from the centre the view was skewed (the eye sat 41 units to
the side at the maze's far end); and the zoom was Final Destination's, unrelated to the chunk size.

**C-stick: fixed rule.** The C-stick becomes a camera zoom only under Classic, Adventure and
All-Star (`gm_IsCurrently1PMode`), and the same gate removes C-stick attacks. Missions and Envoy
never run under those three modes; the LAB, versus, Target Test and Training keep C-stick attacks.
Verified: in the LAB a C-stick input gives a smash attack and the camera does not move. Each mode
we ship gets that check as a test.

**Design.**
- One camera for all cases: the standard camera, single subject, with the origin following the
  player the way Adventure does.
- Long levels: origin follows the player with a 10-unit leash, clamped at the level's ends; window
  about 250 x 180; fixed zoom per level. Works from Lua today.
- Maze chunks: window = the chunk's rectangle plus a small margin; the origin eases to the chunk
  centre over 30-60 frames when the player crosses a door. Needs a settable minimum zoom distance,
  or the view is wider than the room and shows void.
- Tall sections: the escape-shaft pattern: origin x fixed, origin y follows the player, window
  150 x 180. Works from Lua today.
- Camera rectangles and zoom are authored per level and per chunk in Blender, as markers.

**Engine work added by this section.**

| # | Change | Size |
|---|---|---|
| E9 | `gd.camera_params{min_dist, max_depth, fov, fixed_zoom, track_smooth, track_ratio, tilt, pan, yaw_gain, pitch_gain}` writing the stage's camera info, restored on unload. Zero yaw and pitch gains remove the skew | S |
| E10 | Stop the per-call log line and LAB-timeline fork on origin and bounds calls, which now run every frame | S |
| E11 | Later: a fixed-camera mode for auto-scroll sections, per-chunk rectangle tweens as data, per-fighter camera box and look-ahead scale | M |

**Open.** The prototype's two maze variants still showed void (the view was wider or taller than a
120 x 100 chunk), and the reported `fov` seems to understate the real vertical field at 16:9 by
about half; both need E9 and a calibration run. Nobody has judged the result by eye yet: GD plays
the maze again once E9 is in.

## 9. Blender add-on

- A kit library to place parts from; mission markers as ordinary objects (start, enemy, wave,
  checkpoint, goal, trigger zone, camera and blast bounds, chunk rectangles).
- **Export mission:** writes models first and `level.lua` / `mission.lua` last, each by rename, so
  the game never reads a half-written folder. Non-kit meshes are named by content hash.
- **Send to game:** asks the running game to reload over the console socket.
- **Validate:** budgets (parts, lines per mesh, triangles per chunk), markers outside bounds, a
  goal with no route marked to it, chunk rectangles that overlap.
- Authoring is kit-part instances first; the exporter merges parts into section meshes only when
  a level passes the part limit, within the 32-line and 65,535-index limits per mesh.
- The in-game map editor is frozen: it keeps working for nudging markers and spawns against real
  collision, and gets no new tools.

## 10. Order of work

1. E1, E2, E3 and the runtime's folder loading and reload: the smallest set that makes "one
   folder, export, see it in a second" real. Ends with GD playing a Blender-built level.
2. E4, E6 and the fly-based test commands.
3. Chunk streaming and E5, proved on a long level and on the toy maze.
4. The Blender add-on proper (library, markers, validate, send to game), replacing the spike's
   throwaway exporter.
5. E7, E8 and the traversal bot.
6. The camera: E9 and E10, then the per-level and per-chunk camera markers, then GD plays the maze
   again.

Each step ends with something GD plays on the vanilla disc. Engine changes and the final build
stay in one lane; well-specified pieces (the add-on, the bot) can go to Codex with tests and are
verified in the game before they are trusted; game-driving and Blender look work go to Sonnet
agents.

## 11. Risks and open questions

- **Enemies far from the origin** are untested (P10). If they misbehave, large levels need either
  an engine fix or enemy spawning tied to the loaded window. Tested in step 2.
- **Culling (E5)** touches the renderer's batching; it must not change what is drawn for anything
  on screen. It gets a screenshot comparison.
- **Hiding the host stage (E3)** may interact with stage-specific code (hazards, moving parts).
  Final Destination and Battlefield are the supported hosts at first.
- **Savestates, rewind and netplay** with mission folders are out of scope and unverified.
- **One-folder mods on vanilla** for fighters is a separate design
  (`_research/vanilla-single-folder-mods-2026-10-03.md`); mission folders satisfy the rule on their
  own because they carry no disc-derived data.

## 12. Decisions for GD

1. Approve this spec's scope and order, or change them.
2. Chunk size for mazes: the toy maze used 120 x 100. GD played it and said it "seemed fine";
   confirm that is the size to design around, or name another.
3. Host stage: is an empty void behind a level acceptable at first, with backgrounds added later?
