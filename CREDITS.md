# Credits

This project stands on other people's work. Everything here is credited whether or not a licence
requires it, and that includes ideas and findings as well as code. Licences of bundled libraries are
in `tools/release/THIRD-PARTY-NOTICES.txt`. A project we learn from or start using is added here in
the same change.

## Jev workspace tools (2026-10-07)

[TypeSafe](https://typesafe.ai), creators of Jev (System One), provides the optional
typed choice, score, and noul API used by `tools/jev/` for crash triage, reviewer
finding ranking, and agent-claim checks. The integration follows TypeSafe's
[API reference](https://docs.typesafe.ai/api) and
[Python SDK documentation](https://docs.typesafe.ai/sdk/python); this project's
client and deterministic offline fixtures are original code. No SDK is bundled.

## Online Envoy (2026-10-05)

The rollback vocabulary used to scope Envoy over the port's own netplay (input delay, prediction, rollback depth,
SyncTest) comes from GGPO's documentation and design notes by Tony Cannon, https://www.ggpo.net/ (ideas only; the
port's netcode is its own). The between-game reward arbitration (a host that validates picks against pure
functions of an agreed seed) is our own design; no outside code was used. Path of Exile's keystone idea is
credited in the Envoy rows above.

## Maze stitching (2026-10-03)

GD's direction to stitch hand-built chunks, the project's mission-folder runtime,
Blender exporter and original `bf_floor_4m` kit are the foundations of this packet.
The measured chunk size, streaming behavior, fighter footprint and jump limits
come from `_research/large-levels-and-maze-stitching-2026-10-03.md` and the owner's
maze prompt. The throwaway spike was consulted for its findings, never copied.
Graph growth, sealing, independent checking and data recipes are original code;
the seeded RNG uses the general Park–Miller minimal-standard recurrence.

Draft of 2026-10-03: the "foundations" list is incomplete and is being filled in from the README
and the third-party notices.

## Foundations

| Project | Author | Link | What it gives us |
|---|---|---|---|
| doldecomp/melee | the doldecomp contributors | https://github.com/doldecomp/melee | The matching decompilation the port is built from |
| Aurora | encounter | https://github.com/encounter/aurora | The GameCube SDK reimplementation the port renders through |
| Project Slippi | Fizzi and the Project Slippi team | https://slippi.gg, https://github.com/project-slippi | The replay format, rollback practice and UCF codes the port follows |
| Lua 5.4 | Lua.org, PUC-Rio | https://www.lua.org | The scripting language embedded in the port |
| m-ex | akaneia and contributors | https://github.com/akaneia/m-ex | The content-expansion mod whose behavior the port's m-ex layer reimplements; consulted, never copied (it publishes no licence). See `tools/mex_port/README.md` |

## Work we have learned from (ideas and findings; no code copied)

| Project | Author | Link | Licence as they state it | What we drew on |
|---|---|---|---|---|
| MeleeVS (melee-pc-TagFighter) | Joyastick | https://github.com/Joyastick/melee-pc-TagFighter | Game-side code unlicensed; port code GPL-3.0-or-later | Benching and calling reserve fighters, control hand-off, fighter labels, and the bug history around them. Note: `_research/tagfighter-insights-2026-10-03.md` |
| melee-pc | 999sian and the melee-pc contributors | https://github.com/999sian/melee-pc | Port code GPL-3.0-or-later; game code unlicensed | Whole-memory rollback snapshot design; architecture comparison |
| slippi-ai | Vlad Firoiu (vladfi1) | https://github.com/vladfi1/slippi-ai | MIT; no terms stated for the trained weights | An imitation-learned agent considered as a test opponent. Note: `_research/slippi-ai-for-testing-2026-10-03.md` |
| Phillip | Vlad Firoiu (vladfi1) | https://github.com/vladfi1/phillip | GPL-3.0 | Read to judge its status; not used |
| libmelee | AltF4 and vladfi1 | https://github.com/altf4/libmelee, https://github.com/vladfi1/libmelee | LGPL-3.0 | The game-state field set an agent expects |
| Sonic Adventure 2 decompilations and Chao World Extended | their respective authors (to be named from the repos) | to be filled in | SA2B GameCube decomp CC0; others carry no licence | Chao genetics, growth and breeding rules as design reference. Note: `_research/chao-genetics-for-envoy-2026-10-03.md` |
| sonic-adventure-workbench | leevee123 (GitHub account) | https://github.com/leevee123/sonic-adventure-workbench | No licence stated (ideas only; nothing copied) | Benchmark method (fixed savestate, median of trials, hashes recorded), offline relocation and opcode audit of code blobs, allow-list package validation. Note: `_research/sonic-adventure-workbench-insights-2026-10-03.md` |
| Sonic Adventure / Chao Garden | Sega, Sonic Team | | | The design the companion and garden are modelled on |
| Super Smash Bros. Ultimate (Spirits, Stage Morph) | Nintendo, Bandai Namco Studios, Sora Ltd. | | | Design reference for the Envoy companion (Spirits) and for seamless stage switching (Stage Morph); ideas only |
| Path of Exile | Grinding Gear Games | https://www.pathofexile.com/ | | The model for Envoy's loot: prefix/suffix modifiers on items, uniques, and keystones (rule-changing passives with a drawback); ideas only, no names, rules or numbers copied (`keystones.lua`, `mod_pool.lua`) |

## Fighter surface shading (2026-10-03)

Aurora's generated GX shaders, threaded FIFO, public normal resolve and pipeline
cache are provided by **encounter / Luke Street and the Aurora contributors**
([encounter/aurora](https://github.com/encounter/aurora), MIT; vendored upstream
`cb0e279`). The GD surface extension builds on those local implementations and
retains their licence. The cel edge, rim and dissolve samples are original code;
quantisation, view-normal rim lighting and procedural hash dissolve are general
shader techniques, with no outside sample code copied.

## Controller remapping (2026-10-03)

The editor consults **encounter and the Aurora contributors**' existing PAD
device layouts and public mapping, native button-name and SDL-handle APIs
([Aurora](https://github.com/encounter/aurora), MIT). **The SDL contributors**
provide controller button/axis positions, GUIDs and device polling
([SDL](https://github.com/libsdl-org/SDL), zlib). These local implementations
informed the shim integration; the profile model, conflict resolution, capture
flow and preset descriptions are original code. No external remapping screen
or controller artwork was copied.

## Mod shaders, post processing and kit materials (2026-10-03)

The custom renderer uses the public draw, resolve and offscreen-pass interfaces
of **encounter / Luke Street and the Aurora contributors**
([encounter/aurora](https://github.com/encounter/aurora), MIT). It extends the
existing Geno effects renderer without changing Aurora or `shim_gx`.

WGSL uniformity, explicit-LOD sampling and uniform layout were checked against
the **W3C GPU for the Web Working Group**, including editors **Alan Baker,
Mehmet Oguz Derin and David Neto**,
[WebGPU Shading Language specification](https://www.w3.org/TR/WGSL/).
Validation uses the bundled **Google Dawn/Tint contributors'** implementation
([Dawn](https://dawn.googlesource.com/dawn), BSD-3-Clause).
The grade, vignette, depth outline, bloom, derivative tangent frame and
Fresnel-style glass samples are original implementations of general shader
techniques; no outside shader source was copied.

## Native profiler and benchmark tooling (2026-10-03)

The optional development profiler vendors only the **Tracy 0.14.1 client**, by
**Bartosz Taudul and contributors** ([Tracy](https://github.com/wolfpld/tracy),
BSD-3-Clause). Its bundled **libbacktrace**, by **Ian Lance Taylor / Free Software
Foundation** (BSD-3-Clause), **LZ4**, by **Yann Collet** (BSD-2-Clause), and
**rpmalloc**, by **Mattias Jansson** (public domain), retain their notices.
The client is off by default and excluded from release packaging.

Run-wide bounded percentile samples use **Jeffrey S. Vitter's Algorithm R**
([Random Sampling with a Reservoir](https://www.cs.umd.edu/~samir/498/vitter.pdf));
this is an original implementation of the technique. The private replacement hash
uses **Austin Appleby's MurmurHash3 64-bit finalizer**, released into the public domain
([source](https://github.com/aappleby/smhasher/blob/master/src/MurmurHash3.cpp)).
Chrome Trace JSON interoperability follows **Google / the Perfetto contributors'**
[trace format documentation](https://perfetto.dev/docs/getting-started/other-formats);
no Perfetto library is vendored. GPU timestamps extend **Luke Street / encounter and
Aurora contributors'** MIT renderer and **Google Dawn contributors'** WebGPU backend.
The synthetic benchmark mesh, material grid and clank shader are original assets;
no disc-derived assets are included.


## Static stage switching (2026-10-03)

Stage Morph presentation and placement ideas: Super Smash Bros. Ultimate, Nintendo, Bandai Namco and Sora Ltd. The behavior reference is [SmashWiki: Stage Morph](https://www.ssbwiki.com/Stage_Morph), contributed by SmashWiki editors under CC BY-SA 4.0; this implementation uses an original, simplified static geometry design. Retail DAT layout and game routines are studied in this workspace's Melee decompilation and `_research/seamless-stage-switch-2026-10-03.md`. No disc-derived assets are included.

## Geno author tools (2026-10-03)

`tools/geno/` consults the Melee decompilation contributors' command table and bitfield
definitions in `melee/src/melee/ft/ftaction.c`, and this workspace's Geno registry,
game implementation, LAB command names and `melee/docs/geno.md`. The assembler imports
the existing `ports/ir/tools/acmd_to_ftcmd.py` encoder unchanged; the exporter reuses
`tools/mex_port/mex_hsd.py`'s GCM/HSD readers. Effect-binding validation reuses the
workspace's `ports/ir/schema/fx_bindings.schema.json`, adapting converter-only constraints
to the engine. The starter's original authored choices come from the learner-lane
`tutorial-kirby` overlay and the Geno fighters course. Schema validation uses the
`jsonschema` project's Python library (Julian Berman and contributors). No command
streams, archives or assets from a disc are included in these tools or starter files.

## Feature demos and small showcases (2026-10-03)

`melee/pc/scripts/examples/demos/` follows this project's scripting, mission,
shader and profiling references and native registrations/implementations. The
independent post demos preserve the existing `shader-demo` WGSL techniques.
Gauntlet contains the project's pure seeded maze generator and room recipes
from `examples/missions/scripts/maze.lua` and `maze_set.lua`; its arena,
pickup definition, result UI and presentation shaders are original text/data.
The tiny localhost client follows `melee/pc/scripts/console.py`'s protocol.
LAB inspection reads the engine's motion/timeline and contact tables, whose
underlying Melee behavior comes from the doldecomp/melee contributors.
Each README names its project technique sources. No external source, third-party
asset, texture/model export or disc-derived data was added by this demo packet.


## Demo catalogue fix2 (2026-10-03)

The staged Gauntlet setup, protected fly calls and jab-first training selection follow the project's tested demo-tour audit patches in `_build/audit-20261003/demo-tour/patches/`. The behavior runner adapts that audit's `scenarios.py` and `drive.py`, with owner-state assertions, isolated mounts and complete PNG decoding added here. These are project-authored techniques; no third-party assets or disc-derived data were imported.

## Turbo match rule and the interrupt window (2026-10-04)

Turbo (cancel a connected attack into other actions) is prior art from [Project M](https://github.com/Fracture17/ProjectMCodes) (`Turbo.asm`, "Turbo Mode - On Hit Interrupts" by Magus, Dantarion, standardtoaster and DukeItOut; the Project M Development Team) and [Project+](https://projectplusgame.com) (the Project+ team, whose 2.3.1 "Turbo Mode Adjustments" taught the rules this port starts from: no self-cancel, dash only from jabs and dash attacks, smashes that stay still, no shield or air dodge from the wrong moves, air jumps restored on a hit), and of UnclePunch's Turbo Mode for Melee 20XX (a time window after a hit). The source was consulted for ideas only; this implementation is original and hooks the decompiled Melee fighter code. See `_research/turbo-mode-projectm-2026-10-04.md`. No disc-derived assets are included.
- Original fighter art (2026-10-05): the Courier (`ports/vanilla-original`) was modelled and animated headlessly with [Blender](https://www.blender.org) (Blender Foundation, GPL) and exported with its glTF 2.0 I/O add-on ([Khronos glTF 2.0](https://www.khronos.org/gltf/)); the leg solver is the textbook two-bone law-of-cosines IK; no third-party meshes, textures, motion capture or add-ons.
- Courier animation pass 2 (2026-10-05): follows the twelve principles of animation (anticipation, slow in and slow out, follow-through and overlapping action, arcs, squash and stretch, secondary action, timing) from Frank Thomas and Ollie Johnston, "The Illusion of Life: Disney Animation" (Disney Editions, 1981); the per-key interpolation is the monotone cubic Hermite method of F. N. Fritsch and R. E. Carlson ("Monotone Piecewise Cubic Interpolation", SIAM J. Numer. Anal. 17, 1980); the scarf is a Verlet chain with distance constraints after Thomas Jakobsen, "Advanced Character Physics" (GDC 2001); the walk is built from the textbook heel-strike / foot-flat / heel-off gait phases. All of it is implemented in this repo's own scripts (`ports/vanilla-original/src`); no motion capture, clips, add-ons or assets.
- Geno slice 4, authored-fighter converter (2026-10-05): `ports/ir/tools/authored_fighter.py` reads [glTF 2.0](https://www.khronos.org/gltf/) (Khronos) and `ports/ir/tools/fighterbuild` writes the model files with [HSDLib](https://github.com/Ploaj/HSDLib) (Ploaj); the animation encoder is this repo's `figatree.py`. The retail-costume material convention (texture as diffuse lightmap) was read as numbers from a vanilla costume file, not copied.
- Geno slice 4d (2026-10-05): the guard-pose crash and the held-victim joint were found by reading this repo's decompiled sources (`ftCo_Guard.c`, `ftCo_CatchPull.c`, `ftCo_CapturePulled.c`); no outside project was consulted or used.
- Menu re-unification mockups (2026-10-06): the `b-signal` and `c-atlas` concept boards under `menu/concepts/reunification-2026-10-06/` set their titles in [Barlow Condensed](https://github.com/jpt/barlow) by Jeremy Tribby (SIL OFL 1.1; the licence sits beside the font files in each `fonts/` folder). All three directions use the kit's own [Source Sans 3](https://github.com/adobe-fonts/source-sans) and [Hasklug](https://github.com/ryanoasis/nerd-fonts) (both SIL OFL). The pages are rendered with [Playwright](https://playwright.dev) (Microsoft, Apache 2.0) and headless Chromium. Mockups only: nothing here is in the game.
- Atlas menu system, step 1 (2026-10-06): the game's font atlas and, since step 9 (2026-10-06), the Qt launcher carry [Barlow Condensed](https://github.com/jpt/barlow) by Jeremy Tribby (SIL OFL 1.1; files in `menu/Barlow/`, the licence in `tools/release/licenses/BarlowCondensed-OFL-1.1.txt` and so in the release's `LICENSES/`, and in the launcher's own `launcher/licenses/BarlowCondensed-OFL-1.1.txt`), for the new menus' caps labels and titles, beside Source Sans 3 (Adobe) and Hasklug (Nerd Fonts), both SIL OFL 1.1. The Atlas design is this project's own; nothing is traced from Nintendo or HAL work.
- Atlas menu system, step 9 (2026-10-06): the Qt launcher (`tools/release/launcher/qt/`) is drawn in the Atlas style with [Qt 6](https://www.qt.io) by The Qt Company (LGPL-3.0, dynamically linked; the licence texts ship in the package's `launcher/licenses/`), [Barlow Condensed](https://github.com/jpt/barlow) (Jeremy Tribby) and [Source Sans 3](https://github.com/adobe-fonts/source-sans) (Adobe), both SIL OFL 1.1. Its icons are this project's own paths from the Atlas concept (`menu/concepts/reunification-2026-10-06/c-atlas/parts.py`); nothing is traced from Nintendo or HAL work.
