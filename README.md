# GD's Melee

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/readme/brand/logo_horizontal_dark.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/readme/brand/logo_horizontal_light.png">
    <img alt="GD's Melee" src="docs/readme/brand/logo_horizontal_light.png" width="600">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/GurekamDhillon/gd-melee-workspace/releases/latest"><img alt="Release v0.1.5" src="docs/readme/brand/version.svg" height="28"></a>
  <img alt="Platform: Windows x64" src="docs/readme/brand/windows.svg" height="28">
  <img alt="Netplay: rollback" src="docs/readme/brand/rollback.svg" height="28">
  <img alt="Mods: m-ex compatible" src="docs/readme/brand/mex.svg" height="28">
  <img alt="Replays: Slippi" src="docs/readme/brand/slippi.svg" height="28">
  <a href="LICENSE"><img alt="License: GPL-2.0-or-later" src="https://img.shields.io/badge/license-GPL--2.0--or--later-3a3f4b"></a>
</p>

<p align="center">
  <a href="docs/readme/gameplay.mp4"><img alt="Four seconds of a Fox vs Marth match on Battlefield, running in the port at 3x render scale" src="docs/readme/gameplay.gif" width="480"></a><br>
  <sub>Real gameplay, captured frame by frame from the game's own screenshot hook. <a href="docs/readme/gameplay.mp4">MP4 version</a>.</sub>
</p>

A native PC port of *Super Smash Bros. Melee* (NTSC 1.02, `GALE01`), built **from the matching
decompilation** rather than by emulation or by recompiling the retail binary. It plays online with
**rollback netcode** from a competitive lobby, renders natively in HD, runs **m-ex** mod discs and
loose mods, and can be scripted in **Lua**.

> **Status: public test build (0.1.5).** Expect rough edges and please report bugs: what you did,
> which disc, and the crash report from the `crashlogs` folder (or `melee-pc.log`).

## Quick start

<p><a href="https://github.com/GurekamDhillon/gd-melee-workspace/releases/latest"><img alt="Download for Windows" src="docs/readme/brand/download_windows.svg" height="60"></a></p>

1. **Download** the latest `GDMelee-<version>-win64.zip` from
   [Releases](https://github.com/GurekamDhillon/gd-melee-workspace/releases/latest) and unzip it anywhere.
2. **Point it at your own disc.** Start `GD Melee.exe`, click *Add disc...* and pick your own
   legally dumped *Melee* NTSC 1.02 `.iso` (mod discs such as ACE or Akaneia work too). No game data
   ships with the port.
3. **Play.** Press *PLAY*. For online play: **VERSUS > ONLINE**, then host a room and send the
   code, join one, or press *Random Opponent*.

The launcher is in English and Spanish (it follows Windows by default; English or Spanish can be chosen in the launcher).
Windows SmartScreen warns on first run because the launcher isn't code-signed.

## Features

<table>
  <tr>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_rollback_dark.png">
      <img alt="Rollback netplay: Play a friend with a room code, or press Random Opponent. Rollback hides the lag." src="docs/readme/feature_rollback_light.png" width="400">
    </picture></td>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_lobby_dark.png">
      <img alt="Competitive lobby: Blind picks, starters and counterpicks, 1-2-1 strikes, bans and rematches." src="docs/readme/feature_lobby_light.png" width="400">
    </picture></td>
  </tr>
  <tr>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_hd_dark.png">
      <img alt="HD at any resolution: Native D3D12 rendering at any render scale, with vsync off and ~13 ms input." src="docs/readme/feature_hd_light.png" width="400">
    </picture></td>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_mex_dark.png">
      <img alt="m-ex mod support: Mod discs and loose mods: fighters, stages, items and music, online too." src="docs/readme/feature_mex_light.png" width="400">
    </picture></td>
  </tr>
  <tr>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_roster_dark.png">
      <img alt="94 fighter slots: Room for big m-ex rosters, with their names, emblems and stock icons." src="docs/readme/feature_roster_light.png" width="400">
    </picture></td>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_scripting_dark.png">
      <img alt="Lua scripting + kit UI: Scripts, a console and gd.kit: draw panels in the menus' own style." src="docs/readme/feature_scripting_light.png" width="400">
    </picture></td>
  </tr>
  <tr>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_training_dark.png">
      <img alt="Training on the kit: Training can run through the new character and stage select screens." src="docs/readme/feature_training_light.png" width="400">
    </picture></td>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_launcher_dark.png">
      <img alt="Launcher, EN / ES: Mods browser, diagnostics and crash reports. In English and Spanish." src="docs/readme/feature_launcher_light.png" width="400">
    </picture></td>
  </tr>
  <tr>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_replays_dark.png">
      <img alt="Slippi replays: Frame-accurate playback of .slp replays, straight from the game." src="docs/readme/feature_replays_light.png" width="400">
    </picture></td>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_settings_dark.png">
      <img alt="Settings screen: Video, audio, controls and online options, applied right away." src="docs/readme/feature_settings_light.png" width="400">
    </picture></td>
  </tr>
  <tr>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_ucf_dark.png">
      <img alt="UCF + tournament rules: Universal Controller Fix and tournament rule sets, built in." src="docs/readme/feature_ucf_light.png" width="400">
    </picture></td>
    <td><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/readme/feature_determinism_dark.png">
      <img alt="Deterministic engine: Bit-exact simulation, checked frame by frame with SyncTest." src="docs/readme/feature_determinism_light.png" width="400">
    </picture></td>
  </tr>
</table>

### Features in the current release

**Online**
- Rollback netcode. Play a friend with a short room code, or press **Random Opponent** to be paired
  with anyone searching.
- A competitive lobby in the same room: blind character picks, stage strikes and bans, ready-up and
  rematches, with the set score kept.
- Stages are split into **starters** (Battlefield, Final Destination, Dream Land, Yoshi's Story,
  Fountain of Dreams) and a **counterpick** (Pokémon Stadium). Game 1 strikes over the starters
  1-2-1; the counterpick opens from game 2 for bans and picks.
- The strike cursor skips struck and banned stages in every direction, with wrap-around.
- Sheik can be picked online (press A on Zelda again), and mods work online: you can pick any
  fighter or stage both players have.
- The GameCube adapter follows the window you're using and is only held in the background during an
  online match.

**Mods (m-ex)**
- Mod discs (ACE, Akaneia) and loose mods in the `mods` folder, toggled in the launcher. The
  launcher's Mods tab browses and installs mods; downloads are verified and never run.
- **94 m-ex fighter slots** (up from 31), so big rosters fit.
- The results screen shows m-ex fighters' names, emblems and stock icons.
- m-ex CPUs play from their clone base's CPU tables.

**Menus and screens**
- New main menu, hubs, character select and stage select that list every fighter and stage your
  disc and mods provide, with pages for big rosters.
- **Training can run through the new character and stage select** (`gd.training_select("kit")`,
  or `select=kit` in the scene grammar).
- A **Settings** screen: video, audio, controls, online name and server, mods and gameplay options,
  applied right away and saved.
- Everything unlocked from the start, without a save file (always on online).

**Graphics and input**
- Native D3D12 rendering at any render scale, vsync off, and an experimental uncapped frame rate.
- About 13 ms from controller to screen, steadily.
- GameCube adapter (plug in any time, clones supported) and any gamepad.

**Scripting**
- Lua scripts and a console (the backtick key). Scripts can read the match, draw, wait on the game,
  add console commands, and, if they declare it, drive gameplay (rollback-safe).
- **`gd.kit`**: scripts draw with the menus' own kit (9-slice panels, the kit's fonts and text
  roles, list rows, icons, the palette) over any scene, a match included. Mods can ship their own
  kit art.
- Built-in examples: `tm_lite` (save/load positions on F5-F8), `state_overlay` (frame data),
  `kit_hud`, `scene_setup`. See [`docs/scripting.md`](docs/scripting.md).

**Launcher and reports**
- English and Spanish; the language follows Windows by default.
- Diagnostics tab, short logs, and crash reports with your Windows user name removed. Optional crash
  report upload, off by default; nothing is ever sent automatically.

### Added in 0.1.5

- **The keyboard is hotkeys only.** It no longer plays: controllers play, and the keyboard keeps
  F9, F10, the console and mods' own keys (`gd.key`).
- **"Connect a controller":** a window with no controller shows a notice instead of sitting there
  unplayable.
- **The mouse works in the main menu, settings, online lobby and character and stage select:**
  point, click, right-click to go back and scroll lists. Matches ignore it, and scripts can read
  it with `gd.mouse()`.
- **Items no longer hitch** when they first spawn: their GPU pipelines are compiled in parallel and
  prewarmed at match load.
- **Crash fixes:** m-ex fighters whose motion tables or model part trees are shorter than the
  engine assumed, m-ex costume data (`MEX_GetData`), and the stage select's name model outliving
  its scene.
- **Bit-exact with the console:** matrix maths now rounds exactly like the GameCube's paired-single
  instructions, and six real console replays (Slippi `.slp`) play back matching to the bit, frame
  by frame: action, position, facing, percent, stocks and the RNG.
- **The Geno engine and the LAB mode** (below).

## Screenshots

All captured from the running port (1280x960 window unless noted).

<table>
  <tr>
    <td width="50%"><img alt="Online lobby, game 1 stage striking: starters on the left, Pokémon Stadium as the counterpick, Dream Land struck by P2, the cursor on Battlefield" src="docs/readme/shots/lobby_strikes.png"></td>
    <td width="50%"><img alt="A Fox vs Marth match on Battlefield rendered at 3x (1920x1440)" src="docs/readme/shots/match_hd.jpg"></td>
  </tr>
  <tr>
    <td><img alt="The new character select on the Akaneia disc, with the m-ex fighters in the grid and Dr. Mario picked" src="docs/readme/shots/css.png"></td>
    <td><img alt="The new stage select, page 1 of 2" src="docs/readme/shots/sss.png"></td>
  </tr>
  <tr>
    <td><img alt="The kit_hud example script: a panel drawn with gd.kit over a match, listing both fighters and their percent" src="docs/readme/shots/kit_hud.jpg"></td>
    <td><img alt="Training's character select on the kit: Solo / Training / Characters, with the CPU dummy's card" src="docs/readme/shots/training_kit.png"></td>
  </tr>
  <tr>
    <td><img alt="Wolf vs Charizard, two m-ex fighters, on Final Destination" src="docs/readme/shots/match_mex.jpg"></td>
    <td><img alt="The results screen naming m-ex fighters Wolf and Charizard, with their emblems and portraits" src="docs/readme/shots/results_mex.jpg"></td>
  </tr>
  <tr>
    <td><img alt="The new main menu: Versus, Solo, Collection, Settings, Data" src="docs/readme/shots/main_menu.png"></td>
    <td><img alt="The Settings screen: video, audio, controls, online, mods, gameplay, rumble, screen display, language" src="docs/readme/shots/settings.png"></td>
  </tr>
  <tr>
    <td><img alt="The launcher's Play tab in English" src="docs/readme/shots/launcher_en.png"></td>
    <td><img alt="The launcher's Play tab in Spanish (Jugar)" src="docs/readme/shots/launcher_es.png"></td>
  </tr>
</table>

## The Geno engine

**Geno** is the port's own layer for fighter content that m-ex can't express. A fighter opts in
through a `geno.json` next to its m-ex files; a fighter without one runs exactly as m-ex defines it,
so Geno stays 100% m-ex compatible. Everything it adds lives in the rollback snapshot and is
deterministic, so it works online. Geno adds *character* abilities inside Melee's rules: it never
changes Melee's physics, hitstun, knockback, air dodge or ledge rules.

- **v0, the foundation:** a registry with stable ids (salted into the netplay handshake), a
  per-fighter state block, a script escape in the fighter's own move scripts (variables, if/else,
  calls), attribute overrides, and multi-jump past Melee's table.
- **v1, script features:** script overlays for any subaction, engine values (read, write and
  test), change-action with Brawl-style requirements, rehit, autolink, special-attribute overrides
  and on-land handlers.
- **v2, action states:** brand-new action states with native behaviours: glide, and Brawl-style
  specials such as Mach Tornado and Drill Rush.
- **v3, root motion:** states that follow their animation's root motion on the ground and in the
  air, hidden and intangible values (Dimensional Cape), and Drill Rush rebuilt from Brawl's own code.
- **v4, the model follows the move:** the model pitches with a drill and spins at a tornado's spin
  rate.

The full reference is [`docs/geno.md`](https://github.com/GurekamDhillon/melee/blob/pc-port/docs/geno.md)
in the melee fork.

### LAB, the frame-data lab

**SOLO > LAB** is a game mode of its own for studying any fighter (vanilla, m-ex or Geno): any
fighters and CPUs on any stage, KOs respawn, and the clock never runs out.

- **Display modes** (hitboxes, hurtboxes, ECB, skeleton and more), a HUD drawn in the menus' own
  style, and a full-screen **pause menu** styled after Sakurai's move-list screens.
- **Rewind** a long way back and step frame by frame, a persistent **savestate library**, and **hot
  reload** of a fighter's files mid-match.
- **The state browser:** every action state the fighter has (common, special, m-ex, Geno), played
  from neutral, looped or slowed down, with its script windows beside it.
- **Knockback preview:** where a hitbox will send the victim, with DI, hitstun, tumble and the
  frame it crosses a blast zone, computed by the game's own knockback code.
- **A/B compare:** two fighters, or two versions of one, in lock-step.
- **Frame-data export** and diff.
- **Rollback visualiser:** see what a rollback re-simulates.
- **Vanilla-parity checks** against real Slippi replays recorded on a console: the port plays them
  back and compares every frame.

Training readouts, a configurable dummy, combo analysis and scored drills are implemented for the
upcoming 0.1.6 release; they are not in the published 0.1.5 download.

## Ports: Halberd (Meta Knight)

[`ports/halberd/`](ports/halberd/) is **Halberd**, Meta Knight ported from *Super Smash Bros.
Brawl* as an m-ex fighter on Geno: his normals, grabs and throws, his four specials, glide, six
jumps, and his own effects, sounds and menu art. This repository carries the **research only**:
notes, the character IR, the conversion tools and configs. **No Nintendo assets are included**;
rebuilding him requires your own legally obtained copies of the games. The shared character IR
schema is in [`ports/ir/`](ports/ir/).

## Known issues

- UnclePunch's Training Mode features are not fully ported; LAB and `tm_lite` cover different
  practice workflows. TM-CE and 20XX discs boot, but their disc-specific features don't work.
- Fighter and stage mods from different packs (for example ACE fighters with Akaneia stages) can't
  be mixed yet.
- The uncapped frame rate is experimental: the picture trails the game by one frame.
- Teams mode on the new character select isn't finished, and 4-player local matches have had little
  testing.
- On a 144 Hz monitor, 60 fps looks uneven. Set the display to 120 Hz, or turn on G-Sync/FreeSync.

Each release's notes are in [`tools/release/notes/`](tools/release/notes/).

## What this is

Most "Melee on PC" efforts are either emulation (Dolphin + Slippi) or static recompilation of the
retail binary. This project takes a third road — **compiled decompilation**:

- [`doldecomp/melee`](https://github.com/doldecomp/melee) is a matching decompilation of Melee in
  which every game translation unit is real C that reproduces the original PowerPC behavior.
- Those translation units are retargeted to x86 by `pc/tools/gwtool`: clang's PPC front-end emits
  LLVM IR, and gwtool rewrites every memory access to be big-endian, prefixes every symbol with
  `gw_`, and emits x86 COFF. The result links against a native platform layer.
- The GameCube SDK surface (GX, OS, PAD, CARD, AX, DVD, AR, …) is replaced by native shims over
  [Aurora](https://github.com/encounter/aurora) (a GC/Wii SDK reimplementation on top of
  [Dawn](https://dawn.googlesource.com/dawn)), so rendering goes straight to D3D12 with no emulated
  GPU. Where the SDK's own decompiled source is worth keeping, it is built as a translation unit
  like any other — the THP video decoder is, with its Gekko paired-single IDCT rewritten in
  portable C.
- m-ex content ships PowerPC code inside its data files; the port runs those blobs through a small
  PowerPC interpreter and bridges their calls back to its own native functions.

The payoff over static recompilation is a **fully editable game** — every line of engine code is C
you can change. The price is that all ~980 translation units must be made correct by hand, which is
where most of the engineering goes (see the devlog).

## Status

| Area | State |
|---|---|
| Boot → menus → VS match, Training | working |
| Rendering (GX → D3D12 via Aurora/Dawn), any render scale | working |
| Audio (own AX / DSP-ADPCM mixer over SDL3) | working, incl. both aux buses + AXFX reverb/delay |
| Cutscenes (THP video, own decoder) | working |
| Memory-card saves (GCI) | working |
| GameCube adapter, gamepads (keyboard = hotkeys only), mouse in menus | working |
| Vanilla parity (console Slippi replays, bit-exact) | working |
| Geno engine + LAB mode | public test (0.1.5); LAB training, dummy, combos and drills in upcoming 0.1.6 |
| Frame pacing | hard 60 Hz; experimental uncapped frame rate |
| Rollback netplay + competitive lobby | public test |
| Slippi replay playback | working |
| m-ex discs and loose mods (94 fighter slots) | public test |
| Lua scripting + console | working (API 1) |
| Launcher, release packaging | public test (0.1.5) |
| Widescreen | not started |

## Repository layout

```
docs/DEVLOG.md        engineering log: every hard-won fact, bug and fix (read this first)
docs/HANDOFF.md       current state + next experiment (resume here)
docs/scripting.md     the Lua scripting API, the console and the examples
PORT_BOOTSTRAP.md     project origin and the feasibility analysis
_research/            boot gates, SDK/console invariants, shim surface, port dev quickref
_build/               Windows build scripts (Aurora, per-TU pipeline, link, run)
tools/port/           build.sh (build + bridge fixpoint), run.sh (sandboxed runs)
tools/release/        the launcher, release build/check/publish scripts, release notes
tools/netplay/        the matchmaking server and netplay test drivers
ports/               fighter ports (research only, no assets): halberd/ (Meta Knight), ir/ (character IR)
DEPENDENCIES.md       every third-party component, its version/pin, and its licence
```

The port source itself lives in the `melee` fork of `doldecomp/melee`, on the
[`pc-port`](https://github.com/GurekamDhillon/melee/tree/pc-port) branch, under `pc/`
(`pc/platform` shims, `pc/gameworld`, `pc/tools/gwtool`). That fork is the buildable project; this
repository carries the tooling, launcher, research and engineering log around it.

## Building

Host is Windows with WSL, MSVC Build Tools, clang 23, and CMake/Ninja for Aurora. The exact,
maintained commands are in [`_research/port-dev-quickref.md`](_research/port-dev-quickref.md). In
short:

1. Build Aurora + Dawn + SDL3 — `_build/build_aurora_melee.bat`.
2. Build `melee-pc.exe` — `tools/port/build.sh` compiles changed translation units through the
   retarget pipeline, links, and regenerates the m-ex bridge until it is a fixpoint.
3. Run it against your own disc image — `tools/port/run.sh <name> --iso <path to GALE01 v1.02>`.
4. Package a release — see [`tools/release/README.md`](tools/release/README.md).

## Legal

- **No copyrighted material is included.** You must supply your own legally dumped ISO of
  *Super Smash Bros. Melee* (NTSC 1.02). No ROM, no game assets and no Nintendo SDK code are
  distributed here. The screenshots show the port running on the author's own discs.
- **Ports carry research only.** `ports/` holds notes, tools and configs, never game files; a port
  such as Halberd is built locally from your own legally obtained copy of the source game
  (*Super Smash Bros. Brawl*), and `.gitignore` keeps every built asset out of the repository.
- Not affiliated with, endorsed by or sponsored by Nintendo. *Super Smash Bros.* and *Melee* are
  trademarks of Nintendo.
- The underlying decompilation is a pre-existing, openly published, research-oriented effort.
- The port is licensed **GPL-2.0-or-later** — see [`LICENSE`](LICENSE).

## Credits

- [doldecomp/melee](https://github.com/doldecomp/melee) — the decompilation this is built on.
- [encounter/aurora](https://github.com/encounter/aurora) — GC/Wii SDK reimplementation.
- [google/dawn](https://dawn.googlesource.com/dawn) — WebGPU implementation.
- [TwilitRealm/dusklight](https://github.com/TwilitRealm/dusklight) — precedent for turning a
  GameCube decomp into a native cross-platform port.
- [akaneia/m-ex](https://github.com/akaneia/m-ex) and its contributors — the content-expansion
  framework whose patches are used as the **specification** for behaviors reimplemented in the
  port (no m-ex source is vendored or built; see
  [`DEPENDENCIES.md`](DEPENDENCIES.md#specification-references-not-built)).
- Dolphin Emulator — `pc/gameworld/gekko_fp.c` derives from `Common/FloatUtils.cpp`
  (GPL-2.0-or-later); attribution is in that file.
