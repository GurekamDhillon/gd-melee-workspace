# tools/release - public releases

How GD's Melee is packaged for people who are not us: a zip with the game, a launcher that asks
for the user's own disc image, and nothing of Nintendo's. Owned by lane charlie.

## One command

```powershell
powershell -File tools\release\publish.ps1 -DryRun   # build + check + show the gh command and notes
powershell -File tools\release\publish.ps1 -Draft    # publish as a draft release (look it over on GitHub, then Publish)
powershell -File tools\release\publish.ps1           # publish for real
```

`publish.ps1` refuses to publish when:
- the tag `v<VERSION>` already exists on the repo (bump `tools/release/VERSION`);
- the workspace commit is not on `origin-ws` (the release notes link to it);
- the melee commit in the exe is not on the public fork `pub`, the melee tree has uncommitted
  changes, or `_build/melee-pc.exe` is older than melee HEAD (`-Strict` build; the GPL source
  offer in the zip points at that commit, so it must be public and must be what was built);
- `check_release.ps1` finds anything it does not recognise.

`-Force` publishes past the provenance checks (never past `check_release.ps1`). `-Repo` picks
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
| `publish.ps1` | build (strict) + check + release notes + `gh release create` |
| `build_launcher.ps1` | compiles the launcher with Windows' own `csc.exe` (.NET Framework 4.x) |
| `launcher/GDMeleeLauncher.cs` | the launcher (C# 5 WinForms, one file) |
| `README-user.txt` | becomes `README.txt` in the zip |
| `THIRD-PARTY-NOTICES.txt`, `licenses/` | become `LICENSES/` in the zip |

`build_release.ps1` packages what is **already built**: `_build/melee-pc.exe`, `melee-pc.map`
(the game reads it for rollback snapshots), `SDL3.dll`, `webgpu_dawn.dll`, the
`initial_pipeline_cache.*` seed, the x86 MSVC runtime (`msvcp140.dll`,
`msvcp140_atomic_wait.dll`, `vcruntime140.dll`, app-local from the newest installed
`VC\Redist\MSVC\<ver>\x86\Microsoft.VC*.CRT` - melee-pc.exe and Dawn import them, and a PC
without the VC++ redistributable would otherwise fail to start), the committed `_build/ui` art,
docs and licences. `-GameDir` packages a lane's build instead.

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

## The launcher

`GD Melee.exe`, a single 50 KB exe that runs on any Windows 10/11 with nothing installed (.NET
Framework 4.8 ships with the OS).

- First run: explains that no game data is included, then asks for the `.iso`.
- Every picked file is probed: disc magic, game ID `GALE01`, revision 2, then the file table.
  Detected: `Melee 1.02 (vanilla)` (1212 FST entries), `ACE (m-ex mod)` (`MxDt.dat` + ACE-only
  files such as `AltSlippiCSS.dat`), `Akaneia (m-ex mod)`, `Training Mode (TM-CE)` (game ID
  `GTME01`) and `20XX` (title) - both allowed with "boots, but its special features aren't
  supported yet" - other m-ex or 1.02 mods (allowed with a warning), and refusals with the reason
  (PAL/NTSC-J, 1.00/1.01, not Melee, not GameCube, Wii, RVZ/WIA/CISO with the Dolphin hint).
- Several discs ("modpacks"): Add disc / Change ISO (keeps the disc's saves) / Rename / Make
  default / Forget. Double-click or PLAY boots the selected one.
- One memory card per disc: `MELEE_CARD_PATH = userdata\saves\<disc id>`.
- Options: unlock everything (`MELEE_UNLOCK_ALL=1`, default on: every character, stage and
  unlockable rule reports unlocked in `gmmain_lib.c` without writing the save; always on in
  netplay), skip intro (`MELEE_SKIP_INTRO`), keyboard only (`MELEE_INPUT=keyboard`; the game's
  own default is keyboard + controllers), "Keyboard plays as" port (`MELEE_KEYBOARD_PORT`), close
  on play.
- Online tab: edits `netplay_server.txt` beside the game (what `gw_netplay.c` reads).
- Mods tab (`launcher/ModsBrowser.cs`): installed mods from `mods/*/mod.json` + `enabled.txt`
  (tick = enabled for the next boot, Remove), and a browser for the sources in `mods/sources.txt`
  (Refresh, Install/Update with requirements, conflicts disabled). HTTPS only, sha256 + size
  checked before opening, zips unpacked entry by entry with path/symlink/size checks into a
  staging folder. Nothing downloaded is executed. Author docs: `docs/mods-browser.md`; schema and
  `make_index.py` in `tools/mods_browser/`. Mods are always loaded (`MELEE_MODS_DIR = mods\`),
  online too - there is deliberately no "mods off for online" switch.
- Also on the Mods tab: "Console socket for tools" (`MELEE_CONSOLE_PORT=51700`, 127.0.0.1) and
  "Open scripts folder". On the Play tab: game volume (`MELEE_VOLUME`, default 50).
- Diagnostics tab: every log switch a player may be asked to turn on, grouped, with tooltips -
  the game's log categories (`MELEE_LOG`, melee `pc/platform/gw_log.c`: watchdog, mex, heap, dvd,
  tex, frontend, audio, snap, the render DIAG block once-per-scene/every/none, scene, everything),
  controllers (`MELEE_PAD_DIAG` 0/1/2, `MELEE_PAD_RELEASE_ON_BLUR`), deeper traces
  (`MELEE_RB_LOG`, `MELEE_GR_TRACE`, `MELEE_MEX_TRACE_CALLS`, `MELEE_CARD_DIAG`, `MELEE_PROFILE`,
  `MELEE_SHOW_FPS`, `MELEE_AURORA_VERBOSE`, `MELEE_PC_TRACE_OSREPORT`), crash-report uploading
  (below), and Open log folder / Open game log / Open or Copy latest crash report / Reset to defaults.
  Anything left at "Game default" is not passed, so the game's own default (and settings.cfg)
  applies.
- About tab: version (first line of `version.txt`), folders, log, licences, source link.
- Crashes: the game writes `crashlogs\crash-<time>.log` (compact, at most 64 KB, user paths already
  `%USERPROFILE%`) and `crash-<time>-full.log` (the whole log). The launcher calls it a crash only
  when a NEW compact report appears during the session and is not marked `during shutdown: yes`;
  closing the window (exit 0, no report) never is one, nor is a fault while tearing down after the
  window was closed. It then says where the report is - it never asks to send it.
- Uploading is opt-in and manual: the Diagnostics tab's "Allow uploading crash reports" (off by
  default, `crash_upload=` in launcher.cfg) with the consent text (what, where, why) enables the
  "Upload last 3 crash logs" button. Only that click sends anything: the three newest compact
  reports (never a -full log, never a shutdown fault) are POSTed to
  `http://<netplay_server.txt>/crash`, each marked with a `.sent` file, and the result is shown.
  There is no automatic upload and no prompt. The receiving end is `crash_upload_server.py`
  (below); it is NOT deployed.
- A non-zero exit without a report offers the log, except when the log shows the window was
  closed first: the current exe faults in `webgpu_dawn.dll` while shutting down after a window
  close (0xC0000005), which is not worth alarming anyone over.
- Settings live in `userdata\launcher.cfg` next to the launcher (portable); if that folder is
  read-only (Program Files) they go to `%LOCALAPPDATA%\GDMelee`, and the game then runs with its
  log and shader cache there too.
- Paths with non-ASCII characters are passed as 8.3 short names (the game takes ANSI paths).

Command line: `--play [disc name]` boots without the window (for shortcuts), `--add-iso <path>`,
`--forget-all`, `--shots <dir>` renders each tab to a PNG and exits (for docs), `--mods` opens on
the Mods tab and reads the sources, `--install-mod <id>...`, `--list-mods`, `--enable-mod <id>`,
`--disable-mod <id>` (results in `userdata/mods.log`, exit code 1 on a failure),
`--upload-crashes` does what the "Upload last 3 crash logs" button does, only with the opt-in on
(result appended to `userdata\crash-upload.txt`, exit code 1 when nothing was sent).

## Crash reports server (not deployed)

`crash_upload_server.py` is plain HTTP on TCP, on the same host:port as the UDP matchmaking server
(TCP and UDP ports do not collide): `POST /crash`, text body starting with the report header, at
most 64 KB. Limits: 3 reports an hour and 10 a day per address (keyed on a salted hash kept only
in memory - addresses are never written), 300 a day overall, 200 MB on disk. Stored as
`<dir>/<date>/<time>-<sha>.log` + `.json` (version, build id, exit path, reason). Standalone:
`python3 crash_upload_server.py --port 51600 --dir /var/lib/gdmelee/crashes`, or from
`gdmelee_server.py`'s event loop with `await start_crash_upload(bind, port, dir)`. Deploying it
needs TCP 51600 open on the VPS and a service unit beside `gdmelee.service`.

## Why no GitHub Actions build

A CI build is not feasible today, so there is no `.github/workflows/release.yml`:
- the compiler is a clang/LLVM 23 build unpacked into `_toolchains/llvm` (~490 MB, in no repo);
- the game links against the Aurora/Dawn/SDL3/ImGui build tree in `_build/ax86m` (gigabytes,
  built by `_build/build_aurora_melee.bat` with MSVC + CMake + Ninja, Dawn alone is a long build);
- the per-TU pipeline (`_build/masstest/pipe_win.sh`, `gwtool`) and the bridge fixpoint in
  `tools/port/build.sh` assume that local layout;
- the test suite needs a disc image, which can never be on a runner.

No disc data is needed to *compile*, so it becomes possible once the toolchain and a prebuilt
Aurora/Dawn are downloadable (e.g. release assets of a toolchain repo) and the build scripts can
run from a clean clone. Until then: build locally, `publish.ps1` uploads.

## Licences in the zip (checked 2026-09-22)

GPL-2.0-or-later port (+ Dolphin-derived `gekko_fp.c`), shipped under GPLv3-or-later terms as a
whole because it links Apache-2.0 abseil; Aurora MIT; Dawn BSD-3 with abseil / SPIRV-Tools /
Vulkan-Headers (Apache-2.0), SPIRV-Headers, DirectX-Headers (MIT), webgpu-headers (BSD-3); SDL3
zlib; ImGui, fmt MIT; FreeType FTL (credit line included); libpng; zlib; zstd BSD-3; xxHash
BSD-2; Tracy BSD-3; SQLite public domain; MSVC runtime under Visual Studio's Distributable Code
terms; UI glyphs from Source Sans 3 and Hasklug (SIL OFL 1.1). Details:
`THIRD-PARTY-NOTICES.txt`. The decompiled game code itself has no upstream licence; that is
stated plainly in the notices rather than papered over.
