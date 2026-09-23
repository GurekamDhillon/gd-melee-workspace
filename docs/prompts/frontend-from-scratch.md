# Build GD's Melee's frontend from scratch

You're designing and building the entire graphical frontend (every menu, screen and transition) for **GD's Melee**. It's a native Windows PC port of *Super Smash Bros. Melee* (NTSC 1.02), built from the community's matching decompilation rather than by emulation. The gameplay, netcode, mods and settings all work. The menus work too, but they run on a small, limited renderer. Replace them with something extraordinary.

**There are no design constraints.** Art direction, motion language, layout system, rendering techniques and interaction model are all yours to invent. Make players stop and stare. The only limits are the engineering and legal ones below. Treat them as hard walls; everything inside them is open.

---

## 1. The codebase you're working in

- **Repos.** The workspace is `GD's Melee/` (tools, art pipeline, build scripts). The game is `GD's Melee/melee/`, branch `pc-port`.
- **Game code** is `melee/src/`. It's the decompiled C, retargeted to x86 by our `gwtool` pipeline. Game code calls unprefixed names, and the linker binds them to `gw_*` native functions. Guest data is big-endian, so use the `gw_r32`-style accessors and never cast guest pointers.
- **Native platform code** is `melee/pc/platform/`: plain C/C++ compiled for x86 by clang.
- **Target:** 32-bit x86 Windows (i686).
- **Rendering:** the game's GameCube GX calls go through **Aurora** (`melee/extern/aurora`, our fork) to **WebGPU via Dawn**.
  - SDL3 handles the window and input.
  - Dear ImGui is already linked and composited over the game's frame: see `pc/platform/gw_overlay.cpp`, `aurora::begin_frame()` and `aurora::end_frame()`. That is the proof that a host-side renderer can draw over or instead of the game's output.
  - Aurora already supports a render-scale framebuffer (`VISetFrameBufferScale`), in-between frame interpolation, present-time stats, and a non-blocking screenshot (`gw_Screenshot(path)` in `shim_vi.h`).
- **Today's frontend,** for reference only (you're replacing it; you're not bound by it):
  - `src/melee/gm/gmfrontend.c` plus its `gmfrontend_*.inc` files. It's a small player that draws pre-rendered textured quads through GX, with JSON layouts and state tables.
  - Hard caps: 512 quads, 128 textures, 16 tracks, 6 keyframes per track.
  - Fixed 640×480, 4:3 logical space. No custom shaders; mostly baked text.
  - Its art comes from `menu/pipeline/*.py` (HTML/SVG → Chromium → PNG → GX textures in `_build/ui/`).
- **Building:**
  - `bash tools/port/build.sh --tu src/... --shim file.c` rebuilds the changed files and links. A single-file change takes about 77 s; a new game or shim file must also be added to `_build/melee_link_objects.rsp`.
  - Aurora is rebuilt through the `C:\gdm` junction path (`GW_ROOT=C:/gdm cmd //c "C:\gdm\_build\build_aurora_melee.bat"`). Building it through the real path, which contains an apostrophe, poisons the cmake cache.
- **Testing:**
  - `bash tools/port/run.sh --test tests --iso <iso>` runs the headless suite, currently 118/118 on vanilla, ACE and Akaneia discs. It must stay green.
  - The headless tests must never require your UI to render.
- **Scripting and console:**
  - A sandboxed Lua 5.4 engine (`pc/platform/gw_script.c`, API `gd.*`, docs in `docs/scripting.md`).
  - An in-game console (backtick key), plus a localhost socket (`MELEE_CONSOLE_PORT`, client `pc/scripts/console.py`) that tools and tests drive.

## 2. Hard requirements

### Legal and provenance
1. **Never commit, export or redistribute Nintendo data.** That covers ISOs, DOLs and DAT/USD files, and textures or audio decoded from the disc. Everything you commit must be original work.
2. **Displaying disc assets at runtime is allowed.** Fighter portraits, stage previews and name art can be read from the user's own disc at runtime, which is what the current CSS/SSS do. They must never be written into the repo or a release.
3. **Licences:** dependencies and fonts must be permissively licensed (MIT, BSD, zlib, Apache-2.0, OFL for fonts), and you add their notices to `tools/release/THIRD-PARTY-NOTICES.txt` plus `tools/release/licenses/`.
   - m-ex has no licence: reimplement behaviour, never copy its code or asm.
   - No GPL code without the owner's explicit approval.
4. **Release guard:** the release zip is checked by `tools/release/check_release.ps1`. Any new runtime asset files must be allowlisted there.

### Engine and runtime
5. **Never touch the simulation.** The game runs at a fixed 60 Hz, deterministically, for rollback netplay. The UI must never write game state that affects the simulation, and must never run during rollback re-simulation. Menus sit outside the match, so this is mostly about not breaking the scene hand-offs.
6. **Input latency is sacred.** The pacing work samples the controller right after the frame wait, and a finished frame is submitted as soon as it's drawn. Your UI's per-frame CPU and GPU cost must not delay the pad sample or the game's frame. Measure with `MELEE_INPUT_PROFILE=1` and `MELEE_SHOW_FPS=1`.
7. **Resolution independence.** Render at native window resolution, at any aspect ratio (16:9, 21:9, 4:3), at any window size, and at uncapped fps. It must also look right at render scales from 1× to 4×.
8. **Controller-first.**
   - Everything must work with a GameCube controller (via adapter), an SDL gamepad and the keyboard.
   - The CSS supports four local players at once, each with their own cursor.
   - Text entry (player names, room codes) uses the keyboard; while typing, the keyboard-as-controller mapping must stand down (the existing `gw_TextEntryUntil` mechanism in `shim_pad.c`).
9. **Mods everywhere.**
   - Rosters and stage lists are dynamic: 25 fighters and 30 stages on vanilla, 45 and 101 on ACE, plus loose mods.
   - Enumerate at runtime through `gw_uigen.h` (`gw_UI_FighterCount/At`, `gw_UI_StageCount/At`) and the m-ex runtime (`gw_Mex_*`); names come from `gw_Netplay_FighterName` / `StageNameExt`.
   - Design for 100+ items gracefully.
10. **Testable by scripts.** This is non-negotiable: we lost hours to menus a script couldn't read.
    - Every screen must expose its state to Lua through `gd.menu()`: screen id, focused element id, per-player cursor positions and selections on the CSS/SSS, the current page, and modal/text-entry state.
    - Values must be current, never stale from a previous screen.
    - Screen transitions must report a clear "transitioning / ready" flag, so automation can wait for a specific state before its next input.
11. **Replaceable in stages.** Put the new frontend behind a switch (for example `MELEE_FRONTEND=next` plus a Settings option) until it reaches full parity, then make it the default. The old one stays reachable until then.
12. **Moddable.** Modders should be able to restyle and add screens or settings rows, ideally declaratively and/or through the Lua `gd` API, with the same sandbox rules: no file or network access outside the mod's own folder.

### Functional parity: every screen must exist and work
- **Boot:** title and attract flow (Start skips to the main menu).
- **Main menu:** 1P, VERSUS, and ONLINE (currently inside VERSUS).
  - SETTINGS pages: Video, Audio, Controls, Online, Mods, Gameplay, Rumble, Screen Display, Language.
  - Data pages: Records, VS Records, Erase Data.
- **VS Melee:** match setup (mode, stock/time, items, damage ratio, handicap, stage select on/off, friendly fire, pause, teams).
- **Character select:**
  - Four ports; human, CPU (level) or off; costumes with no duplicates; teams; Random.
  - Pages for big rosters; name tags.
  - CPU fighter pick by a human; START once ready.
- **Stage select:** pages, preview and name, Random, lock state (unlocked when the disc ships the file or unlock-all is on).
- **Loading screen** before matches: both fighters, the stage, real progress, player names online.
- **Results screen:** real stats, and back to the menus or to the online lobby.
- **Online:**
  - Host a Room (the code is shown and copied), Join a Room (code entry, paste), and Random Opponent (search timer, cancel).
  - The waiting room.
  - **The competitive lobby:**
    - Game 1: blind character picks, a coin flip, then 1-2-2 stage strikes over the legal list, or the "All Stages" rule of winner bans 2 and loser picks.
    - Game 2 and later: winner bans 2, loser picks, then characters (winner, then loser).
    - Then ready-up, a countdown, the match, results, and back to the lobby with the same room.
    - Leaving works at every step.
    - Fighters and stages the opponent doesn't have are greyed out, with a hint.
- **Mods:** a list with enable/disable for the next boot, status (active, missing requirement, conflict) and a restart-needed notice.
- **Pause and in-match overlays,** optional but welcome.

## 3. The interfaces you drive (they already exist; call them, don't reimplement them)

All of these are native `gw_*` functions. Game code calls them without the `gw_` prefix.

- **Netplay (`gw_netplay.c`):**
  - Rooms: `MenuBegin(host, ck, color, stocks, minutes, delay)`, `MenuPoll`, `MenuStatus`, `RoomCode`, `CopyCode`.
  - Code entry: `CodeChar/Move/FirstEmpty/Paste/Keys`.
  - Connection: `Rejoin`, `Leave`, `Ping`, `IsHost`, `PeerLeft`.
  - Random matchmaking: `RandomBegin/Cancel/Status/Seconds`.
  - The lobby (getters for phase, turn, stages, players, ready and countdown, plus actions), `SetStageMode` / `StageMode`, `PlayerName`, `ServerName`, `ReloadServer`.
  - The lobby is host-authoritative. The UI only displays state and sends actions.
- **Online availability (`gw_mexid.h`):** `MexId_OnlineFighter(ck)` / `MexId_OnlineStage(ext)` (1 = both players have it, 0 = not in common, -1 = the peer's list hasn't arrived yet), plus the id-mapping functions.
- **Video:** `gw_Video_RenderScale/SetRenderScale`, `FrameRate/SetFrameRate` (60 / 0 = uncapped / N), `Vsync/SetVsync`, `ShowFps/SetShowFps`. They apply live and persist.
- **Audio:** `gw_Audio_Volume/SetVolume` (percent).
- **Settings:** `gw_settings.c` (`settings.cfg`), covering input device, player name, server, delay, stage-list preset and unlock-all.
- **Mods (`gw_mods.h`):**
  - Listing: `Mods_Count`, `Id/Name/Version/Kind/Pack/Description/Requires(i)`, `Find`.
  - State: `IsActive`, `Status/StatusText`, `IsEnabled`.
  - Changing: `SetEnabled(i, on)` (cascades), `Save`, `RestartNeeded`.
- **Scenes:** the game's scene flow (`GM_FRONTEND` mode, `gmFrontend_Route`, the `gmvsmelee.c` hand-offs for CSS/SSS/results) and the scene launcher grammar (`mode=vs;at=css|sss|match;p1=ck:N;...;stage=ext:N`, set with `gw_SceneLaunch_SetText`).
  - Your UI decides what the player picked, then hands off to the game to load the match.
- **Captures and debugging:** `gw_Screenshot(path)`, `MELEE_SHOT_AT="<frame>:<path>"`, and the console's `shot` / `label` commands.

## 4. Where to build it

Build a **native UI layer in the platform code** that renders through Aurora's Dawn/WebGPU device, composited in the way `gw_overlay.cpp` composites ImGui, or replacing the game's menu rendering entirely while a menu scene is active. You own the renderer: custom WGSL shaders, SDF text, blur, bloom, particles, 3D, render-to-texture, whatever you need.

- **Beyond flat art:** it's fine to render the game's own 3D fighter or stage models into a texture, for example live fighters on the CSS, as long as you use the game's own loading and drawing path at runtime.
- **Library or custom:** embed a permissively licensed UI library (RmlUi, Yoga, ThorVG, FreeType/HarfBuzz, msdfgen and so on) or write your own. Justify the choice.
- **Aurora patches** go in `extern/aurora` and are recorded in `extern/aurora/PORT_PATCHES.md`.

## 5. Deliverables
1. **`docs/frontend-next.md`:** the architecture (scene graph, layout, animation, input, text, theming, scripting hooks, how it hooks into the game's scene flow), the art direction, and the performance budget with measurements.
2. **The UI layer:** its renderer, the screens listed above, full parity, behind the switch.
3. **An asset pipeline** for your original art and fonts: reproducible from source, with provenance recorded.
4. **Tests:**
   - Headless tests for the non-rendering logic: navigation state machines, lobby display rules, roster pagination.
   - A Lua or console-driven walkthrough that visits every screen by waiting on `gd.menu()` state (never frame counts) and takes exact screenshots with `gw_Screenshot`.
5. **Measured numbers:** frame-time and input-latency before and after (`MELEE_INPUT_PROFILE`), showing no regression.

## 6. Working rules
- **Commits:**
  - Use `GIT_MASTER=1 git -c user.name="GD" -c user.email="gd@gsd.sh" commit`.
  - Subjects are prefixed `pc:` in `melee/` and `menu:` / `tools:` / `docs:` / `build:` in the workspace.
  - Stage files explicitly (never `git add -A`).
  - Never push; the owner pushes. Never touch the `origin` remote of `melee/` (upstream doldecomp).
- **Test windows:**
  - Test on the ACE disc with ACE fighters as well as vanilla. ISOs are in `C:/iso`.
  - Windows go on the main desktop, never off-screen, at `MELEE_VOLUME=3`, with `MELEE_RUN_LABEL` set to what you're testing.
  - Close them when done. Kill only your own processes, never by image name.
- **Pitfalls that cost us time:**
  - Git checks text files out with CRLF line endings on Windows. Strip `\r` when shell scripts read lists.
  - Backslash escapes (`\r`, `\n`, `\0`, `\1`) written through heredoc Python can land as real control bytes. Check edited files for stray control bytes.
  - A silent exit with nothing in the log is a fastfail; catch it with `cdbX86` plus the map file.
  - Several m-ex fighters on an m-ex stage can exhaust the game heap (`lbMemory ALLOC_FAIL`). Don't let your UI's memory use make that worse: keep your textures outside the game heap.
- **Honesty:** report failing tests, unverified behaviour and skipped steps plainly.

---

Now go. Surprise us.
