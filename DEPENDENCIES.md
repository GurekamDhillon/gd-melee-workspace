# Dependencies

What the project builds against, how each piece is obtained, and its licence.
The port's own dependency details are in the fork's
[`pc/DEPENDENCIES.md`](https://github.com/GurekamDhillon/melee/blob/pc-port/pc/DEPENDENCIES.md);
this file covers the workspace as a whole.

## The build is three things

| Layer | What | Where | Licence |
|---|---|---|---|
| Game | [doldecomp/melee](https://github.com/doldecomp/melee) — the matching decompilation | the `melee` fork, `pc-port` branch | none published upstream |
| Platform | [encounter/aurora](https://github.com/encounter/aurora) — GC/Wii SDK reimplementation | vendored in the fork at `melee/extern/aurora` | MIT |
| Renderer | [encounter/dawn](https://github.com/encounter/dawn) (WebGPU) + SDL3 | fetched at build time by Aurora's CMake | Apache-2.0 / zlib |

## Pinned versions

The pins live in the vendored Aurora's `cmake/AuroraDependencyVersions.cmake`:

- **Aurora**: `encounter/aurora` @ `749d6ee7a22bdfab78c8ece9047bca5d79aa72ca`, plus
  seven port patches — documented in
  [`melee/extern/aurora/PORT_PATCHES.md`](melee/extern/aurora/PORT_PATCHES.md).
  The patched tree is committed in the fork, so a clone builds without a second
  checkout.
- **Dawn**: `encounter/dawn` @ `1155e0ed531126f33a1279afa029349651ca1c93`
  (release `v20260807.225922`).
- **SDL3**: `3.4.10`, prebuilt `encounter/sdl3-build` `v3.4.10` (Windows x86).

## Transitive dependencies

Fetched by the Aurora/Dawn CMake: fmt (MIT), freetype (FTL/GPLv2), libpng, zlib,
zstd (BSD), xxhash (BSD), imgui (MIT), sqlite3 (public domain), tracy (BSD),
googletest (BSD), abseil (Apache-2.0).

## Toolchain (not redistributed)

- clang/LLVM 23, unpacked at `_toolchains/llvm` (~490 MB). The `clang.exe` runs from
  WSL directly.
- MSVC Build Tools — the linker and `vcvarsall`.
- CMake + Ninja — for Aurora.
- Python 3 (standard library only) — `tools/replay` and the research scripts.
- `gwtool` is built from `melee/pc/tools/gwtool`; it has no external dependencies.

## Derived code

`melee/pc/gameworld/gekko_fp.c` reproduces the Gekko `frsqrte`/`fres` estimate
tables from Dolphin Emulator's `Common/FloatUtils.cpp` (GPL-2.0-or-later); it
carries SPDX and attribution headers and is the only GPL-derived source in the port.

## Not dependencies

`dusklight/`, `tp/`, `nod/` and `dawn/` in the workspace are reference checkouts of
other projects. Nothing in the build uses them. The port's Aurora is vendored under
`melee/extern/aurora`, and the bootstrap build (`_build/build_aurora_x86.bat`) was
repointed at that copy rather than at `dusklight/extern/aurora`.
