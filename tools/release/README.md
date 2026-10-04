# tools/release - public releases

How GD's Melee is packaged for people who are not us: a zip with the game, a launcher that asks
for the user's own disc image, and nothing of Nintendo's.

## One command

```powershell
powershell -File tools\release\publish.ps1 -DryRun   # package existing binaries + check + show gh command and notes
powershell -File tools\release\publish.ps1 -Draft    # publish as a draft release (look it over on GitHub, then Publish)
powershell -File tools\release\publish.ps1           # publish for real
```

`publish.ps1` packages an existing game build; it does not compile the game. Normal publishing
uses `-Strict` and refuses when:
- the tag `v<VERSION>` already exists on the repo (bump `tools/release/VERSION`);
- the workspace commit is not on `origin-ws` (the release notes link to it);
- the melee commit is not on the public fork `pub`, or the game was built from uncommitted
  source (`-Strict`; the GPL source offer must describe the public source that was built);
- `build-provenance.json` is absent, malformed, or no longer matches the current source snapshot
  and final EXE/map hashes. Rebuild with `tools/port/build.sh` to generate it;
- `check_release.ps1` finds anything it does not recognise.

`-Force` bypasses public-commit and clean-source warnings; it never bypasses the source/artifact
binding or `check_release.ps1`. `-DryRun` skips strict mode, but still requires matching build
provenance and package checks, so it is not a strict-package proof. `-Repo` picks
another repo (default `GurekamDhillon/gd-melee-workspace`; the fork `GurekamDhillon/melee` would
also work). `-Server host:port` bakes a `netplay_server.txt` into the zip; that address is then
public, so it is off by default.

Before publishing: rebuild the exe (`bash tools/port/build.sh`), push `pc-port` to `pub`, push
`master` to `origin-ws`.

## The pieces

| file | what |
|---|---|
| `VERSION` | the release version (`0.1.0` -> tag `v0.1.0`, zip `GDMelee-0.1.0-win64.zip`) |
| `build_release.ps1` | stages `_build/release/GDMelee-<v>-win64/`, writes `version.txt` + `MANIFEST.sha256`, checks the folder, zips it (forward-slash entries, one top folder), checks the zip, writes `<zip>.sha256` |
| `check_release.ps1` | the disc-data guard; runs on a folder or a zip; exit 1 = do not ship |
| `publish.ps1` | package existing binaries (strict unless Force/DryRun) + check + release notes + `gh release create` |
| `build_launcher.ps1` / `build_launcher.sh` | build, test and deploy the native Qt launcher |
| `launcher/qt/` | portable launcher; legacy C# sources retained for reference |
| `README-user.txt` | becomes `README.txt` in the zip |
| `THIRD-PARTY-NOTICES.txt`, `licenses/` | become `LICENSES/` in the zip |

`build_release.ps1` packages what is **already built**: `_build/melee-pc.exe`, `melee-pc.map`
(the game reads it for rollback snapshots), `SDL3.dll`, `webgpu_dawn.dll`, the
`initial_pipeline_cache.*` seed, the x86 MSVC runtime (`msvcp140.dll`,
`msvcp140_atomic_wait.dll`, `vcruntime140.dll`, app-local from the newest installed
`VC\Redist\MSVC\<ver>\x86\Microsoft.VC*.CRT` - melee-pc.exe and Dawn import them, and a PC
without the VC++ redistributable would otherwise fail to start), the committed `_build/ui` art,
docs and licences, the LAB script mod, and Lua examples. To package a lane's build, pair
`-GameDir` with `-MeleeDir` pointing at the checkout that produced that EXE:

```powershell
powershell -File tools\release\build_release.ps1 -GameDir C:\path\build -MeleeDir C:\path\melee -Strict
```

The build records a SHA256 snapshot of recognized source/configuration inputs (including nonignored
untracked source), the game commit and protocol, and final EXE/map hashes. Packaging recomputes these
before copying the stamp. The folder/zip guard independently checks artifact hashes and their
commit/protocol against `version.txt`; changing timestamps cannot relabel an older build.
The guard also requires the engine/runtime/cache files, the complete committed UI, and the deployed
Qt application, Windows platform plugin, x64 CRT and license notices. Manifest entries and zip paths
must be unique.

## Checks before packaging

Build through `tools/port/build.sh`, then use the sandbox runner described in
[tools/port/README.md](../port/README.md). For example, in Git Bash:

```bash
bash tools/port/run.sh --test release-tests --iso "C:/path/game.iso"
bash tools/port/run.sh --test --realtime release-tests-rt --iso "C:/path/game.iso"
```

`--test` sets `MELEE_TURBO=1`; `--realtime` before the sandbox name sets it to 0. Headless
tests have no paced frame loop. For scripted gameplay, turbo accelerates the virtual simulation
clock and may omit presentation/draw work; use realtime for player-facing visual/audio checks.
`MELEE_FPS=u` only uncaps interpolated presentation. `GW_JOBS` is not supported by this workspace
HEAD. Test results must name the actual EXE, renderer, disc and mods being packaged.

## What keeps disc data out

Three independent layers; any one of them failing stops the release.

1. `build_release.ps1` copies from an explicit list only, and `Copy-In` throws on any source under
   `_build/ace`, `_build/packs`, `_build/m-ex`, `_build/hsd_export`, `_build/card*`, `_build/USA`,
   `akaneia-build`, `menu/meleedump`, `melee/orig`, or with a disc extension.
2. `check_release.ps1` on the staged folder: an allowlist (the named binaries, `ui/*.gxtex|json`,
   `LICENSES/*.txt`, a few named docs), a denylist of disc extensions (`.iso .gcm .rvz .dol .dat
   .usd .hps .thp .gci .png ...`) and folder names, content sniffing (GameCube/Wii disc header,
   RVZ/WIA/CISO, a leading game ID as in a GCI save, an HSD archive whose first word is its own
   size, a DOL header), `ui/` byte-identical to `_build/ui` at HEAD, no file over 64 MB, no
   `C:\Users\<name>` paths inside binaries, the licence files present, and every file matching
   `MANIFEST.sha256`.
3. The same check on the finished zip, and once more in `publish.ps1` on the exact upload.

Memory-card saves are **not** shipped (the friends package used to include unlocked-everything
saves): a GCI embeds Melee's own banner and icon graphics. Each player starts a fresh save, and
the launcher's "Unlock every character and stage" (MELEE_UNLOCK_ALL) does in code what the card
did.

## The friends zip

`tools/netplay/make_package.ps1` (and `_build/Build zip for friends.bat`, copied to the Desktop)
is now a wrapper: `build_release.ps1 -Version <VERSION>-friends -Server <_build/netplay_server.txt>`
into `_build/release/friends/`, then copied to `Desktop/GDMelee-Online[.zip]`. Same guard, same
launcher; the old `launch.ps1`, the `nomods` folder and the shipped `card/` saves are gone.

Tested negatives (all caught): an ISO chunk renamed `.txt`, a GCI renamed `.txt`, a DOL chunk, a
fake HSD archive named `.gxtex`, a `.dat`, a file in an `ace/` folder, an unlisted `ui/` file, a
tampered README.

## The Qt launcher

The launcher now uses native C++17 and Qt 6 Widgets on Windows and Linux. The UI consumes
our existing menu kit (`_build/ui/kit.json`, icon masks and Source Sans 3 fonts) through Qt
resources: cobalt/section backgrounds, gold selection plates, hard shadows and the kit's
0.25 shear. `launcher/qt/` contains the application and its core tests. No game artwork is
embedded. The old C# files remain as a reference for deferred online features; the default
build scripts compile Qt.

The current scope is **offline Windows parity**:

- Probe vanilla NTSC-U 1.02, Akaneia and ACE discs; reject unsupported or damaged images.
- Add, rename, change ISO, select a default or forget discs. Stable IDs preserve each disc's
  memory card directory even after a rename or ISO change.
- List local mods, enable/disable with dependency/conflict checks, open mod/script folders,
  and remove mods into a recoverable `.removed` folder.
  `enabled.txt` supports `#` comments. Cyclic requirements are refused; disabling a cyclic mod
  clears invalid cycles and their dependents so an all-enabled folder can be recovered.
- Unlock everything, skip intro, volume, close launcher on play; controller and engine
  diagnostic switches; local log/crash inspection.
- English/Spanish controls. Low-level file/probe errors currently remain English.
- Launch via `QProcess` with separate arguments and isolated working directories. Closing
  the launcher while playing hides it; it remains alive until the game exits, preserving
  process monitoring without terminating the game.

Online matchmaking, remote mod downloads, console sockets and crash uploading are not in
this Qt migration. The underlying game networking code has not been removed.

Settings migrate from `launcher.cfg` to an atomic `launcher.json` on first save; the old
file is retained. IDs and unknown settings are retained. Windows prefers writable portable
`userdata/`, falling back to `%LOCALAPPDATA%/GDMelee`. Linux uses existing writable portable
`userdata/` or `$XDG_DATA_HOME/melee-linux` (default `~/.local/share/melee-linux`).
`--data-dir` overrides this. Saves live at `saves/<disc-id>`, logs at `runs/<session>`.
If existing `mods/` or `scripts/` folders are beside the game, they remain the selected
content folders; otherwise the launcher's user data folders are used.

### Build and test

Linux: install a native 64-bit Qt SDK with Widgets, Test and WaylandClient, plus Wayland/EGL
development packages, CMake and a C++17 compiler:

```sh
bash tools/release/build_launcher.sh _build/launcher-package
```

Windows: install Visual Studio 2022 or 2026 C++ tools, CMake and an MSVC x64 Qt SDK, then:

```powershell
$env:QT_ROOT_DIR = 'C:\Qt\6.8.3\msvc2022_64'
.\tools\release\build_launcher.ps1 -Out '.\_build\release\GD Melee.exe'
```

Compilation supports Qt >=6.2; deployment needs >=6.5 (6.8.3 is pinned in CI).
For system-Qt development only, pass `GW_LAUNCHER_DEPLOY=OFF` to the Linux script.
Both scripts run the core tests before installing. Qt libraries/plugins are placed under
`launcher/`, isolated from the 32-bit game's runtime. Windows `GD Melee.exe` is a small
static-runtime entry point into `launcher/bin/gd-melee-launcher.exe`; Linux's `GD-Melee`
entry script opens that same layout. Copy the whole installed folder, not just the executable.

`.github/workflows/launcher-qt.yml` builds/tests on GitHub-hosted Windows and Linux, with
no discs or private runner needed. Screenshots and build artifacts are workflow artifacts;
the workflow does not tag, create or publish a GitHub Release. Real game/disc validation
is separate; see `docs/LINUX_CONTINUOUS_CHECKS.md`.

Useful command lines:

```sh
gd-melee-launcher --app-dir /path/to/game --data-dir /path/to/profile
gd-melee-launcher --probe /path/to/disc.iso
gd-melee-launcher --add-iso /path/to/disc.iso --play
gd-melee-launcher --play 'My ACE'
gd-melee-launcher --list-mods
gd-melee-launcher --enable-mod my-mod
gd-melee-launcher --disable-mod my-mod
gd-melee-launcher --lang es --shots /path/to/screenshots
```

For headless tests, set `QT_QPA_PLATFORM=offscreen` and `QT_QPA_PLATFORMTHEME=none`.
`--play --test-game` runs the actual game engine suite and propagates its exit code.
Qt runtime deployment follows https://doc.qt.io/qt-6/cmake-deployment.html.

The Windows build selects the newest installed app-local x64 CRT, rather than relying on
`windeployqt` to infer `VCINSTALLDIR`, and tests the deployed executable with SDK/toolset directories
removed from PATH. Vendor build-user roots in copied PE diagnostics are replaced in place.
Modified Qt DLLs are explicitly unsigned: their vendor Authenticode directory/certificate is removed,
as recorded in `launcher/qt-build.txt`. Other signed images requiring redaction are refused;
the original Qt SDK and Microsoft CRT signatures remain unchanged.

Local release regressions (no game build or public service needed):

```powershell
python -m unittest discover -s tools/release -p "test_*.py" -v
python -m unittest discover -s tools/netplay/server -v
```

## Crash reports receiver (legacy clients)

`crash_upload_server.py` is plain HTTP on TCP, on the same host:port as the UDP matchmaking server
(TCP and UDP ports do not collide): `POST /crash`, text body starting with the report header, at
most 64 KB. Limits: 3 reports an hour and 10 a day per address (keyed on a salted hash kept only
in memory - addresses are never written), 300 a day overall, 200 MB on disk. Stored as
`<dir>/<date>/<time>-<sha>.log` + `.json` (version, build id, exit path, reason). Standalone:
`python3 crash_upload_server.py --port 51600 --dir /var/lib/gdmelee/crashes`, or from
`gdmelee_server.py`'s event loop with `await start_crash_upload(bind, port, dir)`. Deploying it
needs TCP 51600 open on the VPS and a service unit beside `gdmelee.service`.
The current Qt launcher only inspects/copies local reports; it has no upload client.

## Why no GitHub Actions build

A CI build is not feasible today, so there is no `.github/workflows/release.yml`:
- the compiler is a clang/LLVM 23 build unpacked into `_toolchains/llvm` (~490 MB, in no repo);
- the game links against the Aurora/Dawn/SDL3/ImGui build tree in `_build/ax86m` (gigabytes,
  built by `_build/build_aurora_melee.bat` with MSVC + CMake + Ninja, Dawn alone is a long build);
- the per-TU pipeline (`_build/masstest/pipe_win.sh`, `gwtool`) and the bridge fixpoint in
  `tools/port/build.sh` assume that local layout;
- the test suite needs a disc image, which can never be on a runner.

A clean-machine recipe also needs the generated include files used by the game pipeline
(`agent_new.sh` copies them from the baseline). Do not assume the tracked sources alone are a
complete build input. Keep locally extracted data out of CI artifacts and releases. Until a
portable recipe is verified: build locally, then package and publish the existing binaries.

## Licences in the zip (checked 2026-09-22)

GPL-2.0-or-later port (+ Dolphin-derived `gekko_fp.c`), shipped under GPLv3-or-later terms as a
whole because it links Apache-2.0 abseil; Aurora MIT; Dawn BSD-3 with abseil / SPIRV-Tools /
Vulkan-Headers (Apache-2.0), SPIRV-Headers, DirectX-Headers (MIT), webgpu-headers (BSD-3); SDL3
zlib; ImGui, fmt MIT; FreeType FTL (credit line included); libpng; zlib; zstd BSD-3; xxHash
BSD-2; Tracy BSD-3; SQLite public domain; MSVC runtime under Visual Studio's Distributable Code
terms; UI glyphs from Source Sans 3 and Hasklug (SIL OFL 1.1). Details:
`THIRD-PARTY-NOTICES.txt`. The decompiled game code itself has no upstream licence; that is
stated plainly in the notices rather than papered over.

## Netplay protocol compatibility

Packaging now requires GW_NET_PROTOCOL_VERSION 3 in the selected game checkout
and writes `netplay_protocol 3` to version.txt. The release guard requires this
entry exactly once in both folder and zip checks. The friends wrapper inherits
these checks. Release VERSION stays independent of the network protocol.

These are source/metadata checks, not proof of the executable's contents. Keep
the existing provenance checks and verify an actual v3 handshake on a Windows
lane before release. Never add metadata to a stale EXE to make a check pass.

Run without building:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/release/test_netplay_protocol.ps1 -MeleeDir ../../melee
python tools/release/launcher/check_strings.py
```

The generated release-notes template in publish.ps1 explains the v3 requirement.
TCP crash upload compatibility is independent and remains unchanged, including
for older launchers; netplay errors must not prevent diagnostic uploads.
