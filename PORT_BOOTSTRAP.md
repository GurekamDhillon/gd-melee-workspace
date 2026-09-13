# Bootstrap notes: Melee native Vulkan/PC port investigation

Written by a prior Claude Code session on 2026-09-10, for whichever agent picks this up next.
Nothing described here has been *built* yet — this is a workspace assembled for research and
a first feasibility pass. Treat every claim below as "true as of the research session that wrote
it" and re-verify anything load-bearing (see "Before you trust this" at the bottom).

## The idea

[doldecomp/melee](https://github.com/doldecomp/melee) is a WIP matching decompilation of Super
Smash Bros. Melee (GameCube, GALE01). It currently only builds a `main.dol` that runs on real
hardware / Dolphin, using the original Metrowerks/CodeWarrior toolchain and Nintendo's real
Dolphin SDK (`extern/dolphin`).

[TwilitRealm/dusklight](https://github.com/TwilitRealm/dusklight) already did the analogous thing
for a *different* GameCube decomp — [zeldaret/tp](https://github.com/zeldaret/tp) (Twilight
Princess) — turning a matching decomp into a real cross-platform native PC/Android/iOS build with
a modern Vulkan/D3D12/Metal renderer, by swapping the real GameCube SDK for a reimplemented one
(Aurora) sitting on top of WebGPU (Dawn), plus an app shell (Borealis).

**Open question this workspace exists to answer:** can the same swap (real GX/OS/SDK →
Aurora/Borealis/Dawn) be done to melee, to get a native (non-emulated) Vulkan-capable PC port of
Melee? Nobody has done this. This is greenfield.

## Repo map (all siblings in this folder)

| Dir | What it is | Why it's here |
|---|---|---|
| `melee/` | doldecomp/melee — **the actual port target** | This is the repo that would get forked/modified |
| `dusklight/` | TwilitRealm/dusklight — **the reference precedent** | Study this to see *how* a GC decomp gets turned into a PC port. Its git history is a direct continuation of zeldaret/tp's history (6,954 commits back to 2020-08-29) — meaning the actual "portification" diff is reconstructable via git, not just readable as a finished snapshot. |
| `dusklight/extern/aurora` | encounter/aurora, submodule, checked out at `749d6ee` | Reimplements the real GC/Wii SDK surface: `gx` (rendering), `gd`, `si`, `vi`, `pad`, `mtx`, `os`, `dvd`, `thp`, `card`. This is the library that would need to satisfy whatever SDK calls melee makes. **This is the crux of the whole feasibility question** — see below. |
| `dusklight/extern/borealis` | encounter/borealis, submodule, checked out at `0bdba6c` | App shell: windowing, input, HTTP, logging, crash reporting (Sentry), auto-update, RmlUi-based UI. Game-agnostic. |
| `dusklight/mods/{cosmetics,randomizer}` | TwilitRealm's own submodules | Dusklight-specific mod content, not relevant to the port question, included only for completeness. |
| `tp/` | zeldaret/tp, standalone clone of upstream | The **pre-port baseline**. Diffing `tp` against `dusklight` (or walking dusklight's git log from the point it diverges) shows exactly which changes were needed to go from "matching GC decomp" to "native PC port." This is the single most useful artifact for planning the melee equivalent. |
| `nod/` | encounter/nod, standalone clone | Reads ISO/RVZ/WIA/WBFS/CISO/GCZ disc dumps. Used by dusklight to let users load their own legally-dumped game. Would be needed the same way for a melee port. |
| `dawn/` | encounter/dawn fork, **partial + sparse clone** (headers/docs only, ~17MB) | Google's WebGPU implementation; Aurora sits on top of it, and Dawn is what actually talks to Vulkan/D3D12/Metal. Widen on demand with `git -C dawn sparse-checkout add <path>` (e.g. `src/dawn/native/vulkan`) if you need to read backend implementation, then narrow back with `git -C dawn sparse-checkout set include docs` — don't leave it wide, the full tree (with `third_party/`) is multiple GB. |

Not cloned: Google's upstream `google/dawn` (dusklight uses encounter's fork + prebuilt releases via
Nix, not upstream directly — the fork is the more relevant one to have).

## What we already know (condensed from a full research pass on both `melee/` and `dusklight/`)

### How dusklight's graphics path actually works
The decompiled TP game code is **unmodified** — it still issues the same `GX*` fixed-function
calls it always did. What changed is what those calls link against:
- **Aurora** implements the GX/OS/VI/PAD/SI/DVD/CARD/THP API surface, translating GX fixed-function
  state (TEV stages, display lists, texture objects, vertex formats) into WebGPU pipeline/draw
  calls.
- **Dawn** is what actually dispatches those WebGPU calls to a real backend: D3D12, Vulkan 1.1+,
  Metal (best-effort D3D11 / OpenGL ES for older hardware).
- **Borealis** provides everything a real GameCube didn't need to provide itself (window, input
  routing, HTTP, logging, crash reporting, auto-update, RmlUi menu shell).
- Game-code-side changes are narrow and clearly marked: `#if TARGET_PC` blocks (original code kept
  inline alongside), `#if AVOID_UB` for undefined-behavior fixes, and a blanket swap of
  `new`/`delete` for `JKR_NEW`/`JKR_DELETE` macros to sidestep the original's custom heap-tree
  allocator.
- Build system: CMake 3.25+ with per-platform presets (`CMakePresets.json`), `files.cmake`
  enumerating sources, custom `cmake/` modules for mod-hooking (funchook+capstone), symbol
  exports, and platform packaging (Windows/macOS/iOS/tvOS/Android/Linux AppImage).

### The one real unknown for melee specifically
TP (Nintendo EAD) sits on **JSystem**, Nintendo's own middleware, above GX. Melee (HAL) sits on
**`sysdolphin`/baselib** — commonly called "HSD" — HAL's own middleware, also above GX, but a
different codebase from JSystem. Aurora sits *below* both (at the raw GX/OS level), so in
principle it shouldn't matter which middleware is on top — but Aurora's actual GX coverage was
presumably built out driven by the games already ported (TP, and whatever else encounter/aurora
has been used for). **Nobody has checked whether Aurora's GX implementation covers every call HSD
makes.** This is the first concrete thing to investigate:
1. Enumerate what GX (and OS/VI/PAD/etc.) entry points `melee/src/sysdolphin/baselib` actually
   calls (grep `melee/src/sysdolphin` and `melee/extern/dolphin` for `GX`-prefixed symbols).
2. Cross-reference against what `dusklight/extern/aurora` actually implements (its headers /
   `src/`).
3. Any gap is either (a) already covered because JSystem uses the same subset, or (b) new work
   needed in Aurora itself.

### melee's current state (relevant to portability)
- Builds via `configure.py` (Python) + `ninja`, not CMake. Toolchain is pinned Metrowerks
  CodeWarrior binaries (`compilers_tag` in `configure.py`), fetched automatically.
- Critically: CI already produces a **fully linked DOL in non-matching mode**
  (`ninja` with `--linkable`), meaning the codebase is substantially "all C" already, even where
  individual functions aren't yet byte-matched to the original assembly. That's the actual
  prerequisite for a source port — recompilable C, not raw ASM blobs — and it looks like melee
  already clears that bar to a large degree. (Verify current fraction — check
  `decomp.dev/doldecomp/melee` for the live number, not fetched during this research pass.)
- Module layout: `src/melee/{cm,db,ef,ft,gm,gr,if,it,lb,mn,mp,pl,sc,ty,vi}` (two-letter HAL module
  abbreviations), `src/sysdolphin/baselib` (HSD), `src/MSL`/`src/MetroTRK`/`src/Runtime`
  (Metrowerks runtime), `extern/dolphin` (real Dolphin SDK, would be the thing to swap out).
- No repo-wide license (expected — it reproduces Nintendo/HAL's proprietary code). A port would
  sit in the same legal posture as the decomp itself.

### What Aurora/Borealis do *not* cover
Audio. Dusklight's audio path is TP's own decomp'd audio code (`Z2AudioLib`) plus an in-tree
`libs/freeverb` DSP addition — not something Aurora or Borealis provide. Melee has its own HAL
audio engine; a PC port would need separate work here, unrelated to the graphics question, and
this workspace has not investigated it at all.

### Why this matters more than "just" a tech demo
Melee's competitive/speedrunning community cares about frame-exact determinism (rollback netcode,
TAS-perfect physics, hitbox timing). Getting a picture on screen via Aurora doesn't mean the port
is "real Melee" — that also depends on the underlying decomp being faithful, which is a separate
(and harder, ongoing) axis of progress from the graphics-backend swap this workspace is scoped to.

## Concrete next steps, roughly in order

1. **Reconstruct the actual tp → dusklight portification diff.** Since dusklight's git history
   literally continues tp's, find the commit(s)/range where PC-port infrastructure was introduced
   and read the real diff, not just the finished state. This turns "read two READMEs" into "see
   the actual patch that did this to a comparable decomp."
2. **GX coverage audit** (see above) — the load-bearing feasibility question.
3. **Spike**: try getting melee's `configure.py`/build to produce a fully linkable, non-matching
   build locally, so you have a concrete baseline of "how much of melee is real recompilable C
   today" rather than relying on this note.
4. Sketch what a `melee` → `melee-pc`-style fork's CMake setup would look like, using
   `dusklight/CMakeLists.txt`, `dusklight/files.cmake`, and `dusklight/cmake/*.cmake` as a
   template — most of that scaffolding is game-agnostic already.
5. Punt on audio and on match-percentage/determinism concerns explicitly rather than silently
   ignoring them — they're real scope, just not graphics-backend scope.

## Before you trust this

- All of the above (except the file/dir listings, which were verified directly) came from two
  research-agent passes plus one conversational analysis, not from actually attempting a build or
  reading Aurora's/HSD's source function-by-function. Treat "Aurora probably covers X" as a
  hypothesis, not a verified fact.
- Versions move: submodule commits, Dawn's pinned release tag, and melee's decomp-completion
  percentage will all have moved on by the time this is read. Re-check rather than citing this
  file's numbers as current.
- If you're picking this up as a *fresh* agent with no memory of the conversation that produced
  this file: there is no other persisted context beyond what's written here and in each repo's own
  README/docs. This file is the map; it is not a substitute for reading the actual code it points
  at.
