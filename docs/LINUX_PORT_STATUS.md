# Linux port implementation status

Current scope (2026-09-29): **Windows parity for offline play and custom content**,
plus a shared Qt launcher. Networking is excluded from acceptance. This is development
support, not a release or a claim of completed parity.

The game is a 32-bit i686 Linux executable for x86-64 Linux, using Vulkan/SDL3.
The launcher is a separate native 64-bit Qt app. Target portable baseline: Ubuntu 22.04,
glibc 2.35. The local Arch build requires newer glibc and is not that portable baseline.

## Implemented and exercised

- 993 game translation units and 51 native sources compile and link with LLVM 22.1.8.
- Linux target ABI with guest i64/f64 aggregate layout retained; executable at 0x10000000.
- Atomic build outputs, explicit manifests, content-based dependency fingerprints,
  genuine LLD map conversion, bridge C/header fixpoint and ELF ABI audit.
- All 18,828 bridge function targets resolve; 2,272 local targets audited.
- Linux synchronization, monotonic waits/timers, path handling, safe fixed mappings,
  ELF code ranges and coordinated m-ex instruction-fetch fault routing.
- Existing engine tests: vanilla, Akaneia and ACE each passed 201/201.
- Vanilla graphical boot/CPU match and Akaneia Sonic CPU match ran and shut down cleanly;
  audio device and voices active. Cold shader compilation caused audible-risk underruns;
  sustained performance and audio quality are not yet signed off.
- Raw USB transport implemented with libusb; four-port report/calibration fixtures pass.
  **No physical adapter was available. Hardware behavior remains unverified.**
- Qt launcher core tests pass: legacy settings migration, stable save IDs, malformed disc
  rejection, installed-mod dependencies/conflicts, crash classification and real child
  process argument/environment handling, including Unicode paths.
- Qt recognizes the three real discs. Vanilla and ACE engine tests also passed 201/201
  when launched through Qt. The menu-kit UI uses committed original fonts, icons and tokens.
- Native Wayland: the deployed Qt launcher rendered all four tabs with X11 disabled;
  the game presented about 1,700 frames in a 30-second forced-Wayland run and shut down
  cleanly at the timeout. SDL's dynamically loaded i686 Wayland/keyboard libraries are
  explicitly included in packaging. This check does not certify input or sustained play.
- Hosted Windows/Linux Qt CI and a Windows-to-WSL game-check entry point are authored.
  Remote CI results, runner registration and repository requirements are separate evidence.

## Remaining acceptance work

- Complete the Ubuntu 22.04 dependency/game build and validate a relocated, read-only
  package on the target distribution matrix. Local packaging is not portable certification.
- Validate the Qt launcher on Windows, including runtime deployment and existing user data.
- Longer gameplay, ACE modded fighter/stage play, menu/results/rematch paths, game save/reload
  and relaunch, representative loose custom content, audio quality and SDL controllers.
- Physical raw GameCube adapter: inputs, rumble, hotplug, focus handoff and shutdown.
- Full English/Spanish error-message coverage; Qt control labels are translated but some
  core file/probe errors remain English.

Slippi, UPnP and Windows-only sampling/PAGE_GUARD diagnostics remain outside this port.
Prior local GD netplay checks are retained as development evidence, not current acceptance.
No release tags or GitHub Releases are authorized.

## Local evidence (not committed)

Under `_build/agents/linux`:
- `run-Yuat5Yr5`: vanilla suite, 201/201.
- `run-zwI3A0u2`: Akaneia suite, 201/201.
- `run-yQ2DbzEU`: ACE suite, 201/201.
- `run-czKgijdg`: vanilla CPU match.
- `run-gD46sKNg`: Akaneia Sonic CPU match.
- `run-HUVH7mk0`: native Wayland graphical startup, X11 disabled; bounded timeout.
- `netplay-swh166sq`: 3,925 shared confirmed frames, no hash mismatch.
- `netplay-zq26diqe`: 4,138 shared confirmed frames, no hash mismatch with delay/loss.

Under `_build/launcher-qt`:
- `game-profile/runs/59bc7a21-5a81-4fd4-871e-9c53c6d7e0c7`: Qt-launched vanilla, 201/201.
- `ace-tests/runs/63089de3-b9d6-45c6-b285-dfec431f6e80`: Qt-launched ACE, 201/201.
- `kit-shots/`: rendered launcher screens.
- `wayland-shots/`: deployed launcher rendered on the native Wayland session.

Tests describe their recorded executable, not every later source change. Each game build
must regenerate its own bridge from its own link map. The generated bridge's addresses
are build-specific and are not a portable source change.

## Workspace

Game checkout: `melee/worktrees/linux` (`agent/linux`). Tools and launcher: this repository.
Native game build: `_build/agents/linux`; Ubuntu build: `_build/linux/ubuntu22`.
Qt: `tools/release/launcher/qt`; instructions: `tools/release/README.md`.
Continuous checks: `docs/LINUX_CONTINUOUS_CHECKS.md`.
