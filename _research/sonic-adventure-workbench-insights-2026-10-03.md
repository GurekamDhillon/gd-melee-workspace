# Sonic Adventure workbench: what it is and what we can take (2026-10-03)

Read-only research. Nothing was copied into our tree, nothing was built or launched. The subject is
https://github.com/leevee123/sonic-adventure-workbench , which has **no licence** (GitHub reports none; there is no
LICENSE at its root). So: consult, never copy. Citations are `their-repo path:line` (the "T:" prefix) and our paths.
Quotes are a few lines at most; no decompiled game code or game data is reproduced.

Tags: **CONFIRMED** read in their files. **DOCUMENTED** their own claim, not independently checkable here.
**UNVERIFIED** not shown by anything I could read.

How I read it: a shallow clone sits in `_build/tmp/sa-workbench/repo` (git-ignored, about 2 GB, 32,410 files, because the
repo vendors a whole Dolphin fork and a 45 MB Ghidra export). The Windows checkout partly failed on odd file names, so I read
files with `git show HEAD:<path>`. Line numbers are from those reads. Delete the folder when done.

## 0. Who made it, and what it actually is

- Owner: GitHub account `leevee123` (created 2019-03-02, no name, no bio, one public repo; created this repo 2026-10-03).
  The repo has a single commit by `github-actions[bot]` (2026-10-04 02:00 UTC, "Add custom level library, terrain runtime and
  visual level creator") produced by `.github/workflows/import-source.yml`, which imports a reviewed release zip
  (`ModernGekko-Source-0.5.0.zip`, 28,243 files) after checking its SHA-256 (`docs/pc-port/source-provenance.json`).
  I found no link to our owner and make no claim of one.
- Authorship hints from the files, stated as observations only: `T:native-port/compiler.json` records a compiler path under
  `C:/Users/naync/Documents/Codex/2026-10-01/https-github-com-chasmlol-skycraft-...`, i.e. a Windows user "naync" and a
  Codex-agent session folder; `TOOLS.md` says "Research date: October 2, 2026". The whole thing reads as an AI-agent-driven
  project (prose style, dated verification logs). Treat claims as DOCUMENTED, not audited.
- **The runtime is not theirs.** The game-running core is **ModernGekko** (`ExpansionPak/ModernGekko`, GPL-3.0-or-later,
  `T:native-port/ModernGekko/PROVENANCE.md`), which vendors **RecompCore** (a fork of Dolphin, mostly GPL-2.0-or-later) and
  **DolRecomp** (GPLv3, the PowerPC-to-C translator). `native-port/runtime-sources.json` pins commits and hashes. What is
  original to this repo is small: a Sonic-specific patch layer (`src/runtime/sonic_enhancements.hpp` 24 lines,
  `src/runtime/sonic_levels.hpp` 159 lines), a C# WinForms launcher and installer (`launcher/*.cs`, about 1,500 lines),
  build/benchmark scripts, and the Ghidra/relocation research. The `sadx/` folder is the community `doldecomp/sadx`
  matching-decomp project. `decompiled/` is Ghidra pseudocode.
- Licence consequence: the repo as a whole is unlicensed, but ModernGekko and Dolphin inside it are GPL. We are not importing
  any of it, so this only matters if someone later wants to reuse a GPL piece deliberately (separate decision, with
  GPL obligations on our shipped binaries).
- Side fact worth knowing: ModernGekko's README "Hall of Fame" lists "Literally God / MrPoloGit - Super Smash Bros. Melee"
  (`T:native-port/ModernGekko/README.md`). A Melee recomp exists on the same framework. Unrelated to us, but it is a peer.
- Scope of the claims (README, `T:README.md`): "recomp preview 0.5.0", "playable experimental hybrid", native REL integration,
  full regression coverage and source recovery "remain unfinished". The numbers in `matching-report.json`: 2,428 of 182,356
  configured code bytes matched (1.33 percent of configured units; WORKBENCH.md puts it at about 0.0235 percent of the whole
  game). So it is a research and packaging workbench around a borrowed runtime, not a finished port.

## 1. Architecture: how each project runs the game's code

| | Sonic Adventure workbench (ModernGekko) | Ours |
|---|---|---|
| Source of game logic | The retail binary: a DOL plus 268 REL modules. No source. | The doldecomp C source of Melee, compiled by clang for PowerPC |
| CPU strategy | DolRecomp translates the DOL's PowerPC to **C** (30 chunks, later 37 C files), compiled with clang -O3 ThinLTO into a **DLL** (`gGXSE8P_recomp.dll`) that the Dolphin core loads. Anything outside the translated coverage (all RELs) **falls back to Dolphin's x64 JIT**. A second mode runs everything on the JIT (`MODERNGEKKO_STATICRECOMP=0`). | Game TUs are retargeted at the LLVM-IR level by `pc/tools/gwtool` into native x86 compiled into the exe. No emulated CPU for the game. Mod-disc (m-ex) PowerPC blobs run on our own subset interpreter `melee/pc/platform/gw_ppc.c`. |
| Guest memory | Dolphin's emulated address space; the runtime accesses it by guest address. Native chunks call `get_ram_ptr`. | Guest MEM1 is a literal reservation at `0x80000000`; heap data is directly dereferenceable (big-endian via `gw_r32` etc.), static globals live in native memory (`_research/mex-ppc-interpreter.md` section 2). |
| Endianness | Byte-swapped by the translated code and by Dolphin's memory layer. | Every access rewritten by gwtool; game memory stays big-endian (`melee/CLAUDE.md`, "shim boundary"). |
| Relocatable modules | The central unsolved problem for them. The runtime finds REL images by **scanning guest RAM for header words** (`T:...StaticRecomp/StaticRecompCore_SMC.cpp` `RefreshRelSections`, about line 13), not by tracking the retail loader. `NATIVE-PORT-SONIC.md` lists five concrete defects of this (stale copies, MEM1 bypass of address translation, relocation targets, first-use hash trust, nine modules with 18 impossible branch relocations). | We have no REL problem for the game (it is source). For m-ex fighters we apply the file's own `instructionRelocTable` and `functionRelocTable` ourselves (`mex-ppc-interpreter.md` section 1), so the same class of risk lives in `gw_mex_ftfunction.c`. |
| Self-modifying code and validation | Each native chunk has a hash of its original text; a chunk is only dispatched when `CHUNK_VERIFIED` (`StaticRecompCore_Run.cpp`, lookup table near the top of `Run()`), SMC ranges demote coverage to the JIT, and an optional **lockstep** mode re-runs each native basic block on Dolphin's interpreter and compares registers and memory (`StaticRecompLockstep.h:1-15`, `StaticRecompLockstep_Check.cpp`). | We flush the icache for injected mod code (`mex-ppc-interpreter.md`); no chunk hashing needed since game code is static. The ABI audit (18,827 call sites) and the bridge fixpoint (`CLAUDE.md` fact 2) are our "wrong function silently called" defence. |
| Graphics | Dolphin's VideoCommon: GX command processor, **ubershaders**, Vulkan backend (the tested one); Dolphin shader cache. | Aurora (GX to WebGPU via Dawn, D3D12); per-config generated WGSL, an initial pipeline cache seed (143 pipelines) plus an "urgent pipelines pending" hold (`docs/HANDOFF-2026-09-21.md`). |
| Audio, input | Dolphin's DSP/audio backends (cubeb); controllers via Dolphin's input stack, `-DMODERNGEKKO_GAMECUBE_CONTROLLERS=ON`; the launcher does its own XInput profile (section 5). | Aurora AX shim; SDL3 input, our own remap page (`HANDOFF-2026-10-03-ENGINE-DAY.md`, unrun in game). |
| Mods / extension | `.mgm` **code mods** (native dll/so) with dependency order, imports/exports, entry/return hooks, forced function patches, callbacks, exact disc and CPU ABI check; netplay fingerprint covers every loaded mod binary (`T:native-port/ModernGekko/README.md`, `mod_loader.cpp`, `include/moderngekko/mod_abi.h`). | Lua scripts (`gd.*`), the Geno fighter-extension engine, m-ex PowerPC blobs. |
| Automation | A command-directory protocol: Pad, PadFrames, Pause, SaveState, LoadState, Screenshot, ReadMemory, WriteMemory, Stop (`T:...tools/automation_protocol.hpp`), driven from Python. | `run.sh --test`, the Lua scripting API, console commands, fly cursor. Richer for gameplay; theirs is generic. |

What they do that we do not:
1. Run a game they have no source for. Their whole pipeline exists to avoid needing source; ours needs the decomp.
2. Keep a **validated** coverage map (chunk hashes, SMC demotion, optional lockstep differential) so native code and the
   fallback JIT can mix at run time. We have no mixed mode, so nothing to validate there.
3. Ship a **bring-your-own-disc installer that compiles the native module on the user's machine** with a bundled LLVM
   (`T:launcher/Importer.cs:54-82`): extraction via DolphinTool, SHA-256 of `main.dol` and `_Main.rel` pinned
   (`Importer.cs:15-16`), DolRecomp, clang -O3 -flto=thin, lld link. About 1.5 s launch to first frame afterward.
4. Pin and publish an exact-source provenance record per release (`source-provenance.json`, CI hash check).

What we do that they do not: an accurate decomp-based source port (so we can extend, debug, compile fresh, patch), rollback
netcode (their runtime has Dolphin netplay glue, `tools/netplay_session.cpp`, not a rollback of a retargeted engine),
a real scripting and mod ecosystem, in-engine level and mission authoring, arbitrary aspect ratios.

Honest assessment: **their approach to running code does not transfer to ours.** Our engine is source-compiled; their
engine is an emulator with ahead-of-time translation. The transferable parts are techniques around it (measurement,
verification, packaging, validation), not the CPU strategy.

## 2. Performance: every technique, the evidence, and whether our bottleneck exists

Their performance claims (`T:PERFORMANCE.md`, `T:WORKBENCH.md`), all on one machine, one fixed Chaos 0 scene, Vulkan, 3x
internal resolution, 2026-10-03:

| Case | Original native | Optimised native | JIT ("Fast") |
|---|---|---|---|
| Gameplay throughput, median of 3 | 27.6 fps | 43.4 fps | 60.0 fps |
| Fixed sequence wall time | 13.28 s | 8.55 s | 6.25 s |
| Launch to first frame, warm cache | 22.05 s | 1.49 s | 1.46 s |

Notice what this says: **their translated-native mode is slower than the stock JIT** (43 vs 60 fps) in this scene, and "native
gameplay still slows down". The headline "57 percent faster" is native-vs-older-native. Their own data shows the JIT was the
fast path. Do not read this as "static recompilation beats emulation".

| # | Technique | Where | Evidence they give | Does the bottleneck exist for us? |
|---|---|---|---|---|
| 1 | Rebuild the translated module with clang 23 `-O3 -flto=thin -ffp-contract=off -fno-fast-math` (module ABI 3, CPU ABI 4, 3,536-byte CPU state). The "previous" build was an MSVC module build (`build_runtime.py --module` is "retained for comparison") | `T:native-port/build_module_clang.py`, `compiler.json`, `PERFORMANCE.md` "What changed" | 27.6 to 43.4 fps median of 3; wall time -36 percent. The gain mixes a compiler change and optimisation level; no LTO-only or O3-only split is given | Partly. Our game TUs are already clang (`tools/port/portlib.sh:144` uses `-O2`, no LTO flag found) so this is "try O3 or ThinLTO on game TUs and the retargeted IR". Whether the retargeted game is CPU-bound is not established: the 2026-09-21 profile found the game thread at about 1.3 ms and aurora submit as the long pole (`_research/perf-baseline-2026-09-21.md`). Low expected gain for game code; plausible for `gw_ppc.c` and shims if those are compiled at lower opt. UNVERIFIED |
| 2 | Skip two redundant whole-asset hash scans at local start; keep DOL structure, disc id, DOL/REL hashes; full fingerprints only for preparation and netplay | `PERFORMANCE.md`; `Importer.cs:15-17`; inspection regression test | Launch 22.05 s to 1.49 s, single warm launch each, confounded with async shaders and shader cache; they say cold shader compile was not benchmarked | Unknown. We should check whether our boot hashes or scans the disc or mod assets twice (content stamping of mods is by design, `HANDOFF-2026-10-03-ENGINE-DAY.md` "content-stamped reload"). Cheap to audit |
| 3 | Dolphin **asynchronous ubershaders**, shader cache on, no waiting for all shaders before starting | `T:...src/runtime/dolphin_runtime.cpp:705-711` (`GFX_SHADER_COMPILATION_MODE = AsynchronousUberShaders`, `GFX_WAIT_FOR_SHADERS_BEFORE_STARTING = false`) | None specific: "Cold shader compilation ... not separately benchmarked". It is a stock Dolphin feature. | **Yes: our first-use pipeline compile cost is real** (143-pipeline seed, d3dcompiler thread holding a core for minutes, hold-the-match-until-urgent-pipelines-built, `docs/HANDOFF-2026-09-21.md`). The idea is the right mechanism (draw with a generic shader while the specialised pipeline builds, so no stall and no freeze). Aurora would need an uber vertex/fragment shader; Dolphin's is a reference to consult, not copy (GPL). Size L; evidence from them is zero, evidence from Dolphin's design is general |
| 4 | Pin the process to the largest shared L3 (3D V-Cache aware), opt-in only by exact `=1` env value | `T:...tools/cache_affinity.hpp` (rule split out so it can be tested against synthetic topologies); `tools/pgo_support.*` | No measurement given anywhere | Only on X3D CPUs; our measured bottleneck is not cache. S to try, expect nothing on GD's RTX 5070 box unless it is an X3D. Low |
| 5 | **PGO workflow** for the generated module: Generate/Use modes, merged profile with SHA-256, stale-profile rejection, Windows 260-char path guard | `T:...tools/pgo_support.hpp` (90 lines) | No numbers in any doc | The mechanism applies to anything we compile with clang that runs hot and has a stable workload: `gw_ppc.c` (interpreter, 3,594 lines, 70-200 microseconds per interpreted frame, `_research/rollback-port-design.md` about line 365) and rollback re-simulation of retargeted game code. Gain unknown; M. Do only after a profile says the interpreter or sim is top of the list |
| 6 | **Hybrid fallback with yielding return**: fallback JIT hands control back to covered native code at the next chunk boundary (RecompCore "support mod hooks and yielding fallback jit", `PROVENANCE.md`) | `StaticRecompCore_Run.cpp` | None specific | Our analogue is the m-ex interpreter handing back to native on a bridge call. Already how we work. Nothing to take |
| 7 | **Fixed-sequence benchmark protocol**: restore the same savestate each trial, 60 neutral frames then 360 rendered frames of scripted input, wall time plus the actual frame-count delta, 3 repeats and a median, hashes of exe/DLL/save recorded in `benchmark.json`, fresh output dir required, other copies must be stopped | `T:native-port/benchmark.py:34-60`; `PERFORMANCE.md` "Repeat the measurements" | The method itself is the evidence: reproducible, hashed | **Yes, adopt.** We have `MELEE_PROFILE=1` (percentiles) and a sampler (`tools/port/prof_report.py`), and the in-game savestate. A fixed-savestate multi-trial harness with exe hash and median would make the 120 fps work comparable run to run. S |
| 8 | Dispatch sampling and runtime counters (`STATICRECOMP_DISPATCH_SAMPLES=1`, `--profile`), `smc_failed=0` check on shutdown | `benchmark.py`; `VERIFICATION-SONIC.md` | Used as pass/fail ("smc_failed=0") | Equivalent to our profiler; the pass/fail counter idea (a run fails if a named counter is non-zero) is worth copying into our suite logs. S |
| 9 | Rendered at 3x internal resolution for all comparisons so speed does not depend on lowering quality | `PERFORMANCE.md` | A methodological statement | We should state render scale in every perf run. S |

Our four suspected costs, mapped:
- **Rollback re-simulation**: nothing in their repo addresses it. Dolphin netplay is delay/lockstep (`netplay_session.cpp`),
  and "save states and netplay are refused for custom sessions" (`VERIFICATION-SONIC.md`). Only the benchmark protocol (row 7)
  helps us measure it.
- **Interpreter for mod-disc PowerPC**: they run a JIT as the fallback and found it the **fastest mode** (60 fps). Their way
  out of an interpreter cost is a JIT, which we do not have. PGO (row 5) is the nearest cheap lever. A JIT or decoded-block
  cache is a large project and nothing here quantifies the win for our case. UNVERIFIED.
- **First-use shader or pipeline compiles**: ubershader fallback (row 3) is the matching technique; evidence is only that
  Dolphin ships it.
- **Skinning**: no content in this repo bears on it (they use Dolphin's GX vertex path; no skinning work is described).

## 3. Tooling and verification

What they have (CONFIRMED present):
- **Ghidra automation**: `import_headless.py`, `analyze_game.py`, `ghidra_runtime.py`, `launch_ghidra.py`, `start_ghidra_mcp.py`,
  `layout.py`. Ghidra 12.1.4 plus JDK 21 plus the Cuyler36 GameCube loader; headless project `SonicAdventureDX_Research`.
  Outputs: `decompiled/main.dol/pseudocode.c` (2.5 MB; 2,096 functions, zero failures) and `decompiled/_Main.rel/pseudocode.c`
  (45.5 MB; 30,473 functions, zero failures; REL addresses are an explicit analysis layout in `section-layout.json`).
- **MCP catalogue**: `mcp-catalog.json` is the `tools/list` result of the third-party `mrphrazer/ghidra-headless-mcp`: 212 tools
  (`health.ping`, `project.program.open_existing`, `function.list`, `decomp.function`, `program.close`...). `WORKBENCH.md` says
  initialisation, enumeration and decompiling retail `memcpy` at `0x800031E8` were tested over real stdio. That is the whole
  extent of MCP testing claimed. It is a catalogue of someone else's tool, not their own server.
- **Matching decomp and objdiff**: `sadx/` (doldecomp project, dtk 0.9.2 pinned, 1.8.4 installed), `sadx/objdiff.json`,
  `matching-report.json` (138 units, 26 of 663 functions matched), `scripts/normalize_objdiff.py`. `Open-Objdiff.cmd`.
  All 268 REL modules decoded via SACompGC and checked against community hashes.
- **Relocation audit**: `relocations.py` (91 lines) walks each REL's import table, applies every relocation to an in-memory image
  of the proposed layout, and flags a branch whose target is unaligned, outside a code section or out of range
  (`relocations.py` about lines 4-40). Result `relocation-audit.json`: 268 modules, nine event modules with 18 branch relocations
  that cannot be valid in the static layout; each gets a named `UNRESOLVED_m<id>_s<sec>_<off>` stub in the Ghidra analysis only,
  never in a playable build.
- **VERIFICATION-SONIC.md** (what is actually tested, CONFIRMED to exist and to be specific): 24 launcher/package/validation
  checks; C++ checks of launcher-to-runtime binary parity, vertex colour order, mesh pointer bounds, collision flags, the
  96-piece buffer budget; an authored level driven by **real controller input in both Fast and Native modes** with Sonic's
  coordinates read back from game memory (jump about 15 to 16 units, platform returns him to Y=10000, ramp supports him at
  about Y=10014.8, Z or a fall respawns, finish exits); camera yaw read back (0x8000 to 0x62fd); installer preservation,
  cancel, rollback and registry tests; a fresh install that extracted the RVZ and compiled 37 C files. Strengths: dated, pinned
  versions, each claim states its method, and a "Remaining limits" paragraph that says what is **not** tested (physical
  controller, whole playthrough, audio, other characters). Weakness: self-reported, single machine, and several checks "place
  Sonic at controlled positions to isolate each case" rather than playing a route (they say so).
- Provenance: `source-manifest.json`, `docs/pc-port/source-provenance.json`, `native-port/local-source-changes.json`,
  patches kept as `patches/*.patch` (579 lines).

What fits our agent-driven workflow:
1. **Relocation and opcode pre-audit for m-ex blobs** (their `relocations.py` idea): an offline script that, for every
   fighter `.dat` we can load, applies the `instructionRelocTable` and `functionRelocTable`, checks every patched branch lands
   on a code word, and decodes every instruction against what `gw_ppc.c` implements. Today a missing opcode is a **runtime panic
   with guest PC** (header of `gw_ppc.c`); an audit finds it at ingest. I found no existing opcode-coverage scanner under
   `tools/` or `melee/pc/tools`. S to M.
2. **Differential testing of the interpreter**: their lockstep design (run the same basic block on two engines, capture
   hardware writes without committing them, replay recorded hardware reads, pin the timebase, journal and undo shadow RAM
   writes, `StaticRecompLockstep.h`) is a clean specification of what a differential harness must neutralise. For us the two
   engines already exist for any vanilla function (the retargeted x86 and the same function's PowerPC bytes in `gw_ppc.c`),
   so interpreter correctness could be tested against our own retarget. Caution: their NATIVE-PORT doc lists "compare native
   instructions/state with the reference execution" under **required milestones not yet done**, so the harness exists but no
   result is reported. M to L.
3. **Fixed-input real-controller-path tests** with memory read-back of authoritative values rather than screenshots (matches our
   no-screenshots rule; our fly cursor and `gd.player` fields already do this).
4. **Explicit "Remaining limits" and "not claimed" paragraphs** per verification note; we already do this in handoffs. Keep.
5. **Ghidra MCP for agents**: we already use headless Ghidra projects (`~/ghidra-projects`); registering a headless MCP
   server would let agents call decompile on demand instead of pre-exported text. Their repo shows the server was installed and
   smoke-tested only. S, optional, and only for ports (Sonic/Trail research), not the Melee build.
6. What **not** to adopt: committing 48 MB of Ghidra pseudocode to git. It is game-derived output and conflicts with our rule
   "No disc-derived data is ever committed" (`CLAUDE.md`). Their repo does it for their own reasons and rights position.

## 4. Custom levels

What a `.sadxlevel` is (CONFIRMED, `T:docs/pc-port/CUSTOM-LEVELS-SONIC.md`, `launcher/Levels.cs:52-89`):
- A ZIP containing **exactly one** `level.json`; the loader rejects any extra entry, traversal ids, non-finite numbers, oversize
  dimensions and oversize packages (`Levels.cs` about line 78-79: one entry named `level.json`, at most 262,144 bytes).
- Format id `sadx-workbench-level` v1. A level is a spawn, a finish, and up to **96 pieces**, each a box or a ramp with
  position (within -4000..4000), width/height/depth (2..1000), yaw (-360..360) and an ARGB colour. Nothing else: no models,
  textures, enemies, rings, scripts, moving parts or other characters.
- Pipeline: editor project JSON, to validated package, to install into the user-data folder (`CustomLevels/level-<id>/`), to a
  small little-endian binary `SALEVEL1` (8-byte signature, version, count, spawn and finish floats, 36 bytes per piece) that the
  **runtime validates again independently** (`sonic_levels.hpp` `Level::Load`, about lines 19-43). The two validators are
  tied together by a parity test (launcher versus runtime binary, `VERIFICATION-SONIC.md`; `tests/release/levels.cpp`).
- How it is "played": every frame at the video-end-of-field event the runtime checks that the Emerald Coast act-0 stage REL is
  loaded, then **writes generated Ninja Basic model and collision structures straight into guest RAM over the REL's land table**,
  blanks the SET and camera files so stock objects vanish, and stops the game if that allocation is unloaded
  (`sonic_levels.hpp` `Terrain()`, about lines 46-110; `dolphin_runtime.cpp` about lines 852-880). It reuses Sonic's retail
  collision and movement on the authored geometry; the custom camera is a patch. It is a **guest-memory overwrite of one
  stage**, tied to one disc revision (`GXSE8P` rev 0, DOL and REL SHA-256 checked, `dolphin_runtime.cpp` about line 850).
- The editor: a WinForms canvas (`launcher/LevelEditor.cs`, 105 lines): top and 3D (isometric) projection, grid snap (default 5),
  drag placement, numeric fields, undo/redo as a stack of whole-document byte snapshots, duplicate, start/finish markers
  that switch to top view and snap to a supporting platform, and **Test Play** (save, install, launch, return). The library
  previews a level and edits a copy. A starter level "Skyline Sprint" ships.

Comparison with our mission folders and Blender loop (`docs/superpowers/specs/2026-10-03-mission-folders-and-large-levels-design.md`):

| | Theirs | Ours |
|---|---|---|
| Authoring | In-launcher 2D canvas, boxes and ramps only | Blender add-on exporting meshes, textures, collision, doorways, camera fields; Lua `level.lua` and `mission.lua` |
| Content | 96 coloured primitives | Arbitrary meshes (65,535 indices, 32 collision lines per mesh today), 128 parts, streamed chunks, 50,000-unit range |
| Package | One zip, one json, strictly allow-listed | A folder with scripts, models, chunks; text files loaded in an empty environment and validated before anything changes |
| Validation | Bounded numbers, entry allow-list, size caps, finite checks, **validated twice** with a parity test | Layout validation exists; "a refused folder leaves the running level untouched" is in the spec |
| Game logic | None: goal gate and respawn only | Waves, triggers, checkpoints, objectives, lives, time limit |
| Play loop | Test Play launches the game; falls respawn; finish returns to launcher | 0.6 s Blender save to playable with no match restart |
| Limit that bit them | Per-REL allocation, ray-list capacity, one disc revision | Model cache cap 32 (P3), no culling (P7), floor-only kit collision (P8) |

Ideas worth taking (not copying):
1. **Allow-list the package, not deny-list it.** For anything we distribute as a mission zip: exactly the expected entries,
   extension and size caps, reject traversal, reject non-finite numbers, bound every dimension, cap counts. Their wording is a
   good checklist. S, goes with the mission-folder loader (`gd.mod_read/list/stamp`).
2. **A parity test between the producer and the consumer** of a binary or data format (here: the Blender exporter output
   against the engine's reader). We have the `.gxmesh` writer in `melee/pc/assets_src/*/export.py` and the C reader; a test that
   round-trips and compares would catch format drift. S.
3. **Spawn and finish snapping onto a supporting platform** and "a playable project needs both markers supported by
   geometry" as a hard validation rule, which corresponds to our traversal check (spec section 7). Already planned.
4. **Undo as whole-document snapshots** is the simple robust choice for a small editor; no new idea for Blender (it has its own).
5. Their limits confirm our own P7 and P9: one retail ray-list capacity forced "each mesh is separate for spatial culling"
   (a comment in `sonic_levels.hpp` `Terrain()`). Spatial culling per piece is worth having in the kit renderer.
6. A **library UI with preview and "Edit selected"** copies an installed level to edit; if a Qt mission browser is ever made,
   that flow is clean. Out of scope today.

## 5. Widescreen, controllers, launcher and installer

**Widescreen.** It is Dolphin's feature, switched on by config, not a game-specific implementation:
`dolphin_runtime.cpp` about lines 705-706 set `GFX_ASPECT_RATIO = ForceWide` (or `ForceStandard`) and
`GFX_WIDESCREEN_HACK = widescreen`. The setting is a boolean in `config.ini` ("Widescreen (16:9 projection expansion)"),
applies **at the next launch**, and is **16:9 only**: there is no arbitrary aspect. Dolphin's `Widescreen.cpp` (lines 55-150)
is only the heuristic that decides whether a game is anamorphic from its projection statistics. Their own limits say
"GPU widescreen expansion can differ from game-specific camera/HUD fixes", and an earlier **camera-code patch was removed
because it caused SMC demotion** (`VERIFICATION-SONIC.md`, 0.4.0). What this means for us:
- They never face our black-wedge bug because they do not do arbitrary aspects or our per-material generated shaders. Nothing
  in their repo explains or fixes the culling/wedge at odd aspects (`_build/tmp/codex-arbitrary-aspect-fix1-report.md`).
- A generic Hor+ projection expansion cannot widen the game's own CPU frustum culling; that is why Dolphin-style hacks show
  pop-in at the edges unless the game is patched. In our port the game is source, so widening the cull frustum there (our
  `view_projection_rect`, `melee/pc/tests/view_aspect_cases.h`) is the correct place, and it is something their emulator
  approach cannot do. This is a statement of the general technique, not something their repo demonstrates.
- Confirmed not helpful: no invariant-position or depth-agreement handling to borrow (Dolphin's backends use their own).

**Controller support.** The runtime uses Dolphin input; the **launcher** adds an Xbox profile editor (`launcher/Controller.cs`,
246 lines): XInput probed through `xinput1_4`, `1_3` then `9_1_0` (`Controller.cs:25-40`), device string `XInput/<slot>/Gamepad`,
dead zone default 15 percent, rumble toggle, live stick and button feedback, keyboard bindings retained when switching
profile, and a "Save controls" step. Verification: 15 profile checks plus automated pad commands; physical-controller play
**untested** by their own admission. Compared to ours: our remap page is also unrun in game; their fallback chain across
XInput DLL versions is a small robust detail if we ever call XInput directly (we use SDL3, so probably moot).

**Instant Light Dash** (a setting that changes gameplay) is a one-function guest-memory poke at the video-end-of-field
event: read the Y button from a fixed RAM address, check the player is not hurt, holding, scripted or disabled (flag mask on the
player work struct), and set the existing "dash" request bits. The code credits an existing public cheat as its source and
keeps ring traversal in the retail engine (`sonic_enhancements.hpp:12-20`). The pattern, "request the game's own action rather
than reimplement it, with a guard list of states where it must not fire", is the right shape for our gameplay-changing options
(e.g. tap-jump-off) and is already how our `gd.fighter_mod` works. Note it only works on one pinned revision.

**Launcher and installer** (C# WinForms, .NET Framework 4.7, no Python or Visual Studio for the user):
per-user install in `%LOCALAPPDATA%/Programs/SonicAdventureDX`, Installed apps entry and uninstaller
(`Installation.cs:45-80`), saves, settings and caches **outside** the install folder in a per-installation id folder so
uninstalling keeps saves; "Update game" reuses the imported game and module, backs up replaced files and **rolls back on cancel
or copy failure**; refuses a non-empty unrelated folder; ZIP traversal rejected; app-local VC++ runtime DLLs; the release
packager rejects any ROM, extracted DOL/REL/assets, saves or the private native DLL (`release-tools/package.py`,
`VERIFICATION-SONIC.md` 0.4.0). Ours (`tools/release/`, Qt launcher, `tools/release/test_release_guard.py`,
`check_release.ps1`) already has a release guard. The parts worth checking against ours: (a) data outside the install folder
by default, (b) update with rollback tested by a cancel injected mid-replacement, (c) refusing to overwrite an unrelated
non-empty folder. I did not audit our launcher for these; see section 8.

## 6. Sonic Adventure content for Supertime Envoy and the physics-calibration idea

**Chao Garden logic: no, it adds nothing to `_research/chao-genetics-for-envoy-2026-10-03.md`.** What the repo has for the
GameCube SADX (`GXSE8P`):
- It confirms SADX GC has a Chao stack as separate REL modules: `ChaoMain`, `ChaoMinimal`, `ChaoMotions`, `ChaoStgBlackmarket`,
  `ChaoStgEntrance`, `ChaoStgGarden00SS`, `01EC`, `02MR` (plus day/evening/night variants), `ChaoStgOdekake`, `ChaoStgRace`
  (`T:sadx/config/GXSE8P/rels/`, 268 module folders in all). Useful as a **module map** (which file to look in).
- The symbol files are almost entirely auto-named. `ChaoMain/symbols.txt` has 9,204 lines and 4 non-auto names; the `Main`
  module has 20,164 lines and about 90 non-auto names. In the Ghidra export about 29,500 of 30,473 functions are
  `fn_<module>_<offset>` and only about 795 have real names, mostly runtime and SDK. A search for `AL_`-prefixed gene or stat
  functions found zero identifiers (the SA2B GC decomp already used in our note has `al_gene.c`). The only Chao-related text
  I saw are strings and filenames: `ChaoGC.bin`, `chao_efx_mlt` effect tables, `al_chao_info_c` (a source-file name string),
  `SONICADVENTURE_DX_CHAOGARDEN` (save id), and the `Chaos 0/2/4/6/7` boss names.
- No model, texture or archive **format** documentation for SADX (PVM, `AL_*` files, Ninja Chunk, GVM) is in this repo. The one
  format work is its own Ninja **Basic** attach written by the level runtime (an 8-field mesh/attach layout, `sonic_levels.hpp`),
  and SADX's custom compression handled by the external SACompGC (a decoder checked against the community hashes). Our note's
  conversion path (PRS, Chunk, SAIO in Blender, GVM/GVR) stays as is.
- Verdict: for Chao mechanics and content, **skip this repo**; the earlier note's sources (SA2B CC0, sa2dc, CWE docs) are better.
  The only item that might help is the REL module names when looking for SADX Chao data on the owner's own install.

**Chaos Drive models from SA2** are not covered here (this is SADX GC; Chaos Drives are SA2 items).

**Sonic's movement physics as a calibration source: not usable.** The repo does not expose the physics parameter tables or
movement code clearly:
- Player movement lives in the `Main` module (and the DOL), which is the unnamed bulk above. There are no symbols for the
  character physics table or movement states (`Main/symbols.txt`, about 90 names).
- What it does give: a handful of **fixed RAM addresses for the retail USA revision**, from a public cheat: the player work
  pointer, the Y button bit, a "not in menu" flag, and a flag word in the work struct whose bits 0x0200 and 0x0001 request the
  light dash and whose 0x0004, 0x0800, 0x1000, 0x2000, 0x4000 mark hurt, held, scripted or disabled (`sonic_enhancements.hpp:12-20`).
  That is state, not physics constants. Their verification reads the player's position floats and the action mode (1 to 6) from
  memory, so **observing Sonic's real movement from a running copy is possible with their approach** (the automation
  `ReadMemory` command), which could generate measured acceleration, top speed and jump height curves from the retail game.
  That is a measurement route, not a source of the parameters.
- Better sources for the calibration pair, from our own earlier notes: the SADX PC community decomp or mod loader (`SADXPC`,
  listed as unlicensed in the Chao note's table) which names the physics struct, and Ultimate's own Sonic data already in
  `ports/`. If a measured table from the retail game is wanted, treat it as a derived measurement and follow the project's rule
  that nothing disc-derived is committed.
- Their Chaos 0/2/4 modules (`b_chaos0`, `b_chaos2`, `b_chaos4`) and `Stg01..Stg12` module names are the only stage/boss map.

## 7. Ranked takeaways

| Rank | What | Where it would go | Size | Evidence it would help |
|---|---|---|---|---|
| 1 | Fixed-savestate, multi-trial benchmark harness: same state restored each trial, scripted input, wall time plus real frame delta, median of 3, exe and state hashes in JSON, render scale recorded, named zero-counters as pass/fail | New `tools/port/bench_fixed.py` beside `prof_report.py`; savestate and fly/pad scripting already exist | S | Their method is reproducible and gave clean before/after numbers; our 120 fps work needs comparable runs (`perf-baseline-2026-09-21.md` gives ranges across windows, not trials) |
| 2 | Offline audit of every mod-disc fighter blob: apply the reloc tables, check branch targets, and decode every instruction against what `gw_ppc.c` implements | `tools/mex_port/` (new script) feeding `gw_mex_ftfunction.c` and `gw_ppc.c` | S to M | Their `relocations.py` found 18 impossible branch relocations across nine modules before runtime; ours today fails with a runtime opcode panic (`gw_ppc.c` header) |
| 3 | Allow-list validation plus a producer/consumer parity test for mission packages and `.gxmesh` | `gd.mod_read/list/stamp` loader, `tools/blender/gd_mission/`, `melee/pc/tests/` | S | Their zip allow-list, bounds and "validated twice" parity test are concrete and pass 24 checks; our P9 limits are already enforced ad hoc |
| 4 | Asynchronous generic-shader (ubershader) fallback so a missing pipeline draws instead of stalling or freezing the match | Aurora `lib/gx/shader.cpp` and the loading hold in `gmscene.c` (`urgentPipelinesPending`) | L | Matches a measured cost of ours (first-use compiles, `HANDOFF-2026-09-21.md`). **Their evidence is nil** (cold compile unbenchmarked); the case rests on Dolphin's design |
| 5 | Differential harness: run a function's PowerPC bytes in `gw_ppc.c` and its retargeted x86 twin, compare registers and memory, with hardware effects captured, timebase pinned and shadow writes undone | `melee/pc/platform/gw_test*.c`, new test fixture | M to L | Their lockstep spec lists the required neutralisations; no results reported by them. Our interpreter has no differential oracle today; would find interpreter bugs before GD does |
| 6 | Audit boot for redundant whole-asset or disc hashing; keep full fingerprints for netplay and mod stamping only | startup path in `melee/pc/platform/gw_runtime.c` and mod loader | S | Their 22 s to 1.5 s launch is partly this, but is a single confounded warm run; our boot time was not measured in the files I read. Cheap to check, may be nothing |
| 7 | PGO plus ThinLTO trial for clang-compiled hot runtime code (`gw_ppc.c`, shims), with stale-profile rejection | `tools/port/portlib.sh` (currently `-O2`, no LTO seen) | M | Their gain is native-vs-older-native, mixed with a compiler change, with no PGO numbers. Only worth it after a profile shows these functions on top |
| 8 | "Request the game's own action, guarded by a state mask" as the pattern for gameplay-changing toggles | Settings and `gd.fighter_mod` design notes (tap-jump-off) | S | A 24-line precedent (`sonic_enhancements.hpp`); no measurement, but it matches the netplay-safe design problem we have open |
| 9 | Registering a headless Ghidra MCP server for port research agents | `~/ghidra-projects` workflow, `ports/` research jobs | S | Installed and smoke-tested (212 tools, one decompile) by them; not a proven productivity gain |
| 10 | Update-with-rollback, data-outside-install and refuse-unrelated-folder tests for the Qt launcher | `tools/release/launcher/`, `check_release.ps1` | S (audit first) | Their installer tests (7 preservation/cancel checks, rollback on cancel) are specific; I did not check ours |

Explicitly not worth taking: the CPU strategy (translate-to-C DLL plus JIT fallback), the widescreen implementation,
committing decompiler output, the cache-affinity pinning (no evidence, wrong bottleneck).

## 8. What I could not verify

- Nothing was built or run. All performance numbers are their self-reported figures on an unknown machine; I cannot say what
  CPU/GPU, and "previous build" is described only as the earlier native module (MSVC build per `build_runtime.py --module`).
- Authorship: only the GitHub account and the bot commit. The "naync" and Codex path is an inference from one JSON file.
- Whether their lockstep, SMC demotion and chunk-hash mechanisms actually work well: the code exists
  (`StaticRecompLockstep*.cpp`), and `NATIVE-PORT-SONIC.md` lists verification against the reference as an unmet milestone.
  I read the headers and top of the files, not the algorithms end to end.
- Which of the vendored files are original versus upstream ModernGekko: I used `PROVENANCE.md` and the pinned commit; I did not
  diff against upstream (no network clone of ExpansionPak).
- Their Windows build and installer claims (7 and 24 checks, 37 compiled C files, a fresh install) were not reproduced.
- Level format details at line level (about line numbers above) come from `git show` of dense, minified-style source; treat the
  ranges as approximate.
- Our side: I did not measure our build flags beyond `portlib.sh:144`, did not inspect boot-time hashing, did not audit our Qt
  launcher against section 5, and did not check whether `gw_ppc.c` already has a decode cache.
- The physics-calibration verdict rests on symbol and name counts and substring searches in their Ghidra export; I did not read
  movement code (deliberately). A named physics table might be present under an unnamed function; the point is that this repo
  does not name it.
- ModernGekko GPL status of individual vendored files is as the repo states; not audited.

## 9. Credits (the owner's standing rule: credit ideas as well as code)

No code, data or text from this project was copied into our tree. Ideas credited below.

| Idea | Credit | Link | Licence |
|---|---|---|---|
| Fixed-save benchmark protocol; allow-listed level package and double validation; relocation audit; "request the existing action" gameplay toggle; installer update-with-rollback shape | `leevee123`, repository `sonic-adventure-workbench` (0.5.0, one bot-authored commit dated 2026-10-04) | https://github.com/leevee123/sonic-adventure-workbench | **None stated; all rights reserved by default.** Consulted only. |
| StaticRecomp chunk verification, SMC demotion and lockstep differential design; yielding fallback; mod ABI | ExpansionPak (ModernGekko, RecompCore, DolRecomp), building on `aharonahdoot/RecompCore` ("SpecialK") and the Dolphin Team; as vendored in the repo above | https://github.com/ExpansionPak/ModernGekko , https://github.com/aharonahdoot/RecompCore | GPL-3.0-or-later (ModernGekko, DolRecomp); Dolphin mostly GPL-2.0-or-later. Consulted only; do not copy into a non-GPL tree. |
| Asynchronous ubershaders concept | The Dolphin Team | https://github.com/dolphin-emu/dolphin | GPL-2.0-or-later. Concept only. |
| Instant dash cheat referenced by their code | MetalOverlord666 (the cheat), as credited in `sonic_enhancements.hpp` | https://wiird.gamehacking.org/forum/index.php?topic=9010.0 | Not stated. Not used by us. |
| Matching decomp and tooling named in their TOOLS.md | `doldecomp/sadx`, `encounter/decomp-toolkit`, `encounter/objdiff`, `mrphrazer/ghidra-headless-mcp`, `Cuyler36/Ghidra-GameCube-Loader`, `X-Hax/SACompGC`, `elliotttate/Wind-Waker-Recomp` | see `T:TOOLS.md` | Per project; not used by us |

`CREDITS.md` at the workspace root is the place to add the first row if any idea above is adopted; it was not edited here
(read-only research).
