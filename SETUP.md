# Setting this up on another machine

Nothing here is tied to a particular checkout path. Clone it anywhere, run the checker, fix what
it names.

```
git clone <this repo> gdm && cd gdm
git clone -b pc-port https://github.com/GurekamDhillon/melee.git melee
bash tools/port/bootstrap.sh
```

`bootstrap.sh` changes nothing. It reports each prerequisite as present or missing and exits
non-zero if anything is. Work down its list.

## Layout

```
<root>/                 this repository: build scripts, tools, research notes, handoff
  melee/                the melee fork, pc-port branch (a separate repo)
  _build/               build outputs and third-party libraries (mostly untracked)
  _toolchains/llvm/     clang (untracked)
  .env                  your machine's settings (untracked; see below)
```

The `melee` checkout must sit at `<root>/melee`. Everything else is found relative to the scripts
themselves: `GW_ROOT` defaults to the directory above `tools/port`, so **no `C:\gdm` symlink is
needed** — that was an artefact of the original machine and is gone.

## `.env`

Create `<root>/.env` with your own disc images. It is git-ignored and sourced by
`tools/port/portlib.sh`, so every script picks it up.

```sh
export GW_ISO_VANILLA="D:/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
export GW_ISO_AKANEIA="D:/iso/Akaneia.iso"     # optional, for m-ex content
export GW_ISO_ACE="D:/iso/SSBM ACE Build v2.0.0.iso"   # optional
```

**No disc image is distributed with this repository, and none ever will be.** You must supply
your own legally dumped copy of NTSC 1.02 (`GALE01`). Akaneia and ACE are third-party mod builds
and are likewise yours to obtain; without them the port runs the retail game and simply reports
no m-ex content.

You can also override `GW_CLANG`, `GW_GWTOOL`, `GW_SDL_INCLUDE`, `GW_IMGUI_INCLUDE` or
`GW_VCVARSALL` there if your tools live somewhere unusual.

## The five things not in the repository

| what | why not | how to get it |
|---|---|---|
| clang (`_toolchains/llvm`) | hundreds of MB | any LLVM release that can target `ppc32-none-eabi` **and** `i686-pc-windows-msvc` |
| `gwtool.exe` | build artefact | build `melee/pc/tools/gwtool` |
| Aurora/Dawn/SDL3/ImGui libs (`_build/ax86m`) | gigabytes | `_build/build_aurora_melee.bat` |
| `SDL3.dll`, `webgpu_dawn.dll` | build artefacts | produced by the same Aurora build |
| disc images | Nintendo's | your own dump |

MSVC is located with `vswhere`, so any Visual Studio 2017+ with **Desktop development with C++**
works; set `GW_VCVARSALL` to override.

## Building and running

```sh
bash tools/port/build.sh                                   # relink
bash tools/port/build.sh --tu src/melee/ft/ftdata.c        # a game TU
bash tools/port/build.sh --shim shim_dvd.c                 # a platform shim
bash tools/port/run.sh --test t --iso "$GW_ISO_VANILLA"    # headless tests
bash tools/port/run.sh play --iso "$GW_ISO_AKANEIA"        # play it
```

`build.sh` does compile → link → regenerate the guest→native bridge → compile it → link again,
and then proves the bridge is a fixpoint; a stale bridge does not fail the build and does not
crash at boot, it silently calls the wrong function. `run.sh` runs a *copy* of the exe in a
per-run sandbox so logs, crashlogs and save files never collide.

`MELEE_SCENE` boots straight to any screen, which is the fastest way to check a change:

```sh
MELEE_SCENE="mode=training;p1=fox" ...
MELEE_SCENE="mode=vs;at=css;p1=fox;p2=marth;p3=random;p4=random" ...
MELEE_SCENE="mode=training;p1=ck:38;stage=ext:293" ...   # Sonic on Meta Crystal
```

A number naming a character or stage **must** say which index space it is in (`ck:`/`fk:`/`mex:`,
`ext:`/`int:`); a bare integer is rejected on purpose, because the port juggles four of them and
guessing wrong silently loads the wrong thing.

## Working on it in parallel

```sh
bash tools/port/agent_new.sh <name>     # a git worktree plus its own build root
bash tools/port/agent_rm.sh  <name>     # refuses if there is uncommitted work
```

Each gets its own objects, response file and exe, so two people (or two agents) can build and run
the headless tests at once. Gameplay runs open a window and share one audio device — keep those
serial.

## If something looks wrong

`_research/port-dev-quickref.md` is the command reference and the list of traps that have cost
real time. `docs/HANDOFF.md` is the current state of the work. Both are worth reading before a
first change; several of the entries in them exist because someone assumed instead of dumping.
