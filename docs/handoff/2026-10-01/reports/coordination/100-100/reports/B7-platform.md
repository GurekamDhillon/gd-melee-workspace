# B7 — Cross-platform delivery, packaging and CI audit

**Scope:** READ-ONLY audit. No file outside this report was created, modified, staged or committed.
**No build was run, no game was launched, console 51701 was never contacted, no frozen lane was touched.**
Everything below is read from tracked sources, committed docs and pre-existing local artefacts.

---

## Summary

The delivery story is in two halves that are wildly uneven.

**Windows is the only place the native project has ever actually built.** The entire Windows
pipeline — toolchain, per-TU gwtool retargeting, MSVC link, and above all the *bridge fixpoint* —
is real, scripted and documented, but it is entirely local: `tools/release/README.md:196-209`
states outright that no GitHub Actions build is feasible, and there is no Windows CI workflow in
either repo. A Windows build is a manual, machine-bound operation gated on ~490 MB of clang plus
a gigabyte-scale Aurora/Dawn/SDL3 tree that is deliberately not in any repo.

**Linux is a working, evidenced port with thin, unexercised delivery.** Every Linux acceptance
claim in `docs/LINUX_PORT_STATUS.md` traces to a real local run directory, and the Ubuntu 22.04
build genuinely completed. But the entire continuous-integration story is *authored and
unregistered*: the self-hosted `melee-linux` runner workflow is gated behind a repository variable
that is not set, `~/.config/melee-linux/build.env` does not exist on this machine, and the docs
themselves warn that workflow files alone prove nothing.

**Three concrete, actionable delivery defects stand out**, and they are all in the gaps between
what is scripted and what is actually wired:

1. **The Windows CI gate does not exist.** `launcher-qt.yml` path-filters exclude `tools/port/**`,
   so *no* change to the game build system is covered by any workflow in any repo.
2. **`.gitignore` does not cover the container formats the release guard forbids.** `.rvz .ciso
   .wia .wbfs .gcz .nkit` are all in `check_release.ps1`'s denylist (`:36-38`) and none is in
   `.gitignore`. The one untracked artefact class currently staged for addition
   (`menu/out_effects_study/effects-assets-study-01.zip`) is exactly the shape this misses.
3. **The Linux packaging path has no equivalent of `check_release.ps1`.** `package_linux.py` has a
   GLIBC portability gate (`:26`, `:85`) but no allowlist, no denylist, no content sniffing and no
   manifest-then-verify round trip. It is a *portability* check, not a *redistribution* check.

On the questions asked directly: **Wayland has real evidence; X11/XWayland has none** — the only
X11 traces in the tree are inside a *cancelled* uncapped benchmark's `settings.json`. **No soak or
lifecycle harness exists.** The uncapped benchmark is correctly dormant: nothing in the launcher,
CI or tools re-enables it, and `certify_rooms.py:1132-1136` actively *refuses* turbo/uncapped runs.
Physical input hardware is honestly declared unverified.

---

## Capability table

| Area | Status | Evidence | Blocker |
|---|---|---|---|
| **Windows build** | Works, machine-bound, no CI | `tools/port/build.sh:1-205`; link via `_build/build_melee_pc.bat:61-64`; last-exe evidence `docs/LINUX_PORT_STATUS.md:20-24` | None for the build. **PENDING** for any fresh-run verification (Windows host unavailable) |
| **Windows prereqs** | Documented and self-checking | `tools/port/bootstrap.sh:24-81` names clang, gwtool, 4 Aurora `.lib`s, imgui, SDL3, `SDL3.dll`, `webgpu_dawn.dll`, 3 disc images, MSVC/vswhere; `SETUP.md:48-59`; `DEPENDENCIES.md:35-43` | ~490 MB clang + GB Aurora tree, not redistributable |
| **Bridge fixpoint** | Automated, proven | `build.sh:126-181` (link → regenerate → recompile header dependents → relink, ≤4 passes, stamp-trusted shortcut at `:117-124`); Linux twin `build_linux.sh:116-151`; ABI audit `build.sh:196-205` | None |
| **Linux build** | Works here | `build_linux.sh:1-164`; toolchain present (`clang 22.1.8`, lld, ninja, cmake, `llvm-readelf` all resolve; `_build/gwtool_linux/gwtool` exists) | None for building. See below for *who last proved it* |
| **Linux build — last recorded result** | **NOT RUN BY ME** | Last recorded: `_build/agents/linux/validated.sha256` (`fb3a8816… melee`), `_build/linux/ubuntu22/validated.sha256` (`7e463a2a…`), and `_build/linux/packages-baseline/validation.txt` recording **201/201 on vanilla, Akaneia and ACE**. Narrative: `docs/LINUX_PORT_STATUS.md:20,39-45` | PENDING for any build by this audit |
| **Qt launcher** | Building and packaged | `build_launcher.sh:1-13` (configure → build → **ctest** → install); test evidence `_build/launcher-qt/launcher-tests.txt` = **9 passed, 0 failed**; deployed prefixes `_build/launcher-package/`, `_build/launcher-relocation-fixed/`, `_build/launcher-qt/game-profile/` | None. **Preserve, do not replace** (assignment `:135`) |
| **Qt launcher packaging** | Portable, plugin-complete | `qt/CMakeLists.txt:40-97` — deploy script, Wayland/offscreen/xcb platform plugins, `qwayland-egl`, systemd-style exclusions; `check_release.ps1:123-124` allowlists exactly those Qt runtime paths | None |
| **CI — workspace repo** | 1 workflow, launcher only | `.github/workflows/launcher-qt.yml` — matrix `ubuntu-22.04` + `windows-2022` (`:15-16`), Qt 6.8.3, `permissions: contents: read` (`:8-9`), artifacts only, no release | **Path filter excludes `tools/port/**`** (`:4`,`:6`) |
| **CI — game repo** | 2 workflows, 1 usable | `melee/worktrees/linux/.github/workflows/linux-port.yml:1-46`: `runs-on: [self-hosted, Linux, X64, melee-linux]` (`:16`), gated `if: vars.LINUX_RUNNER_ENABLED == 'true' && github.event_name != 'pull_request'` (`:15`) → **PRs and forks never run it** | Self-hosted **disc-backed** runner; not registered; `~/.config/melee-linux/build.env` absent |
| **CI — game repo (upstream)** | Not ours | `.github/workflows/build.yml` is upstream decomp CI, `if: github.repository == 'doldecomp/melee'` (`:16`, `:204`, `:239`) — never runs on this fork | n/a |
| **Disc-back requirement** | Yes, private | `ci_linux.sh:6` requires `MELEE_VANILLA_ISO`; `:33-39` hard-fails unless **all three** of vanilla/Akaneia/ACE are set — "three-disc acceptance gate" | Discs can never leave a machine (`SETUP.md:40-43`) |
| **Windows/WSL entry point** | Authored, unexercised | `tools/port/check_linux.ps1:1-14` → `check_linux_wsl.sh` → `ci_linux.sh`; docs call it "optional local check" (`LINUX_CONTINUOUS_CHECKS.md:51-57`) | Requires WSL + Windows host. **PENDING** |
| **Security — `.gitignore` coverage** | **GAP** | Covers `.iso .gcm .dol .dat .usd .ssm .sem .hps .thp .gci .xdelta` (`.gitignore:83-93`) but **not** `.rvz .ciso .wia .wbfs .gcz .nkit .elf .sav`, all of which `check_release.ps1:36-38` forbids | See Gap 2 |
| **Security — tracked tree** | **Clean** | `git ls-files` shows **0** tracked `.iso/.rvz/.dol/.dat/.gci/.elf/.so/.dll/.exe`. Largest tracked files are `docs/readme/gameplay.gif` (3.4 MB), `ports/halberd/.../metaknight.brawl.ir.json` (2.7 MB), Hasklug `.otf` | None |
| **Security — untracked, staged by `git add -A`** | **761 files, not ignored** | `_build/benchmarks/` (incl. 24 MB + 20 MB `dawn_cache.db`), `_build/coordination/`, `_build/deepseek-coordination/` (196 files), `menu/out_roguelite/` (108), `_build/roguelite-bf-kit/` (47), `menu/out_effects_study/effects-assets-study-01.zip` (2.0 MB) | See Gap 2 |
| **Security — `check_release.ps1`** | Strong | Allowlist `:31-35,125-142`; denylist `:36-40`; content sniffing (GC/Wii header, RVZ/WIA/CISO, GCI, HSD, DOL) `:149-159`; `ui/` byte-identical to HEAD blob `:167-175`; `C:\Users\<name>` scan `:107,160-164`; ≤64 MB `:178`; MANIFEST round trip `:190-203` | Windows-only. **No Linux-package equivalent** (Gap 3) |
| **Display — Wayland** | **Real pass** | `launcher-qt.yml:48-64` — headless `weston`, `unset DISPLAY`, explicit `QT_QPA_PLATFORM=wayland`, asserts 4/4 non-empty PNGs (`:64`). Game: `run-HUVH7mk0` 30 s bounded, `exit=124` timeout, clean shutdown (`docs/LINUX_PORT_STATUS.md:31-34,70`). i686 Wayland stack shipped separately from x64 Qt (`package_linux.py:60-70`) | **PENDING** for sustained play, input under Wayland, resize/fullscreen/focus |
| **Display — X11 / XWayland** | **NO EVIDENCE** | Only traces of `x11` anywhere are `"SDL_VIDEODRIVER": "x11"` in the **cancelled** uncapped benchmark's settings (`_build/benchmarks/uncapped-20260930/*/settings.json`). No workflow step, no run, no `DISPLAY` run exists | **PENDING.** Per assignment `:138` and completion plan `:371`, a forced-unavailable-backend abort is a *failure*, not a pass |
| **Display — evidence quality** | Weak | `run-HUVH7mk0/melee-pc.log` records `aurora backend 4` (Vulkan, `aurora.h:21-30`) but **never logs the SDL video driver or compositor**. `certify_rooms.py:880` records `MELEE_BACKEND` but not `WAYLAND_DISPLAY`/`DISPLAY` | Cannot prove *which* backend a run used from its own log |
| **Input — SDL controllers** | Code path present, **untested** | `shim_pad.c:193` hotplug start; `main.c:349` `SDL_HINT_JOYSTICK_DIRECTINPUT`; run logs say `gw: pad: SDL sees 0 controller(s)` — zero controllers ever seen | **PENDING** (no controller attached) |
| **Input — GameCube adapter** | Decode tested; **hardware unverified** | 4-port report/calibration fixtures pass: `tools/port/tests/gc_report.c:1-25` (built by `test_linux_abi.sh:12-13`); raw USB transport via libusb. `docs/LINUX_PORT_STATUS.md:24-25`: "**No physical adapter was available. Hardware behavior remains unverified.**" | **PENDING** — physical adapter |
| **Input — rumble / hotplug / multiport** | Implemented, untested | Rumble `{0x11,p0..p3}` at `gc_adapter.c:25,1134-1148`; hotplug scanner `gc_adapter.c:135,792,945`; 4 ports in decoder fixture. **Zero hardware evidence** | **PENDING** — must not let a virtual pad claim the active port (`:139`) |
| **Install / relocate** | **Partially evidenced, not automated** | Manual: relocated read-only install passed all 3× 201/201 (`_build/linux/baseline-relocated/`, `packages-baseline/validation.txt`, `docs/LINUX_PORT_STATUS.md:43-45`). Layout auto-discovery `main.cpp:39-44` | **No scripted test exists.** PENDING |
| **Writable user data** | Implemented | `launcher_core.cpp:148-166` — `pickUserDir`: portable `userdata/` if writable, else `GenericDataLocation`; Linux `…/melee-linux`. Read-only install correctly falls back. Real child process with Unicode paths + separate cwd asserted in `qt/tests.cpp:95-132` | Covered by unit test; PENDING for a clean-vs-upgraded profile pair |
| **Unicode / spaced paths** | **Covered** | `qt/tests.cpp:40` fixture `"disc ü with spaces.iso"`; `:96` `"game with spaces"` + `"profile ü"`; real `QProcess` child round-trip `:115-131` | None |
| **Upgrade path** | **PENDING** | `legacyMigrationAndSaveIdentity` (`qt/tests.cpp:65-74`) covers `launcher.cfg`→`launcher.json`, stable IDs, unknown-option retention, legacy file retained | No *binary* upgrade (old→new installed profile) test |
| **Soak / lifecycle** | **NONE** | `find _build -iname "*soak*" -o -iname "*lifecycle*"` → **empty**. Required by `:141` and completion plan `:383` ("at least a 60-minute normal-speed soak with repeated transitions… hundreds of room changes") | **GAP 4** |
| **Frame-time target** | Proposed, not agreed | Completion plan `:377`: p95 < 13.5 ms, p99 within 16.67 ms, on "the agreed reference configuration" — *agreed* is aspirational | **No reference hardware recorded.** PENDING |
| **Uncapped benchmark** | **Dormant — do not restart** | No `schedule:`/`cron:` in any workflow. No tool sets `MELEE_FPS=u` (only `certify_rooms.py:1135` *refuses* it). `run.sh:36-37` defaults `--test` to turbo but `--realtime` clears it. Assignment `:140`, `:7`; plan `:381`; handoff `:23` | None. **Do not resurrect** |
| **Perf instrumentation (non-benchmark)** | Available | In-game overlay F4 (frame times/FPS/draw calls), `notes/0.1.7.md:15`; `fx:` per-frame cost lines in live logs (`run-iPfB6jwW/melee-pc.log:1185`) | Usable at normal speed |

---

## Ranked gaps

**Gap 1 — Nothing gates a Windows game build; the entire game pipeline is CI-invisible.**
`launcher-qt.yml:4,6` triggers only on `tools/release/launcher/qt/**`, `build_launcher.*`,
`_build/ui/kit*`, `menu/SourceSans3/**` and itself. `tools/port/**`, `tools/mex_port/**` and every
game-side change are invisible to CI. `tools/release/README.md:196-209` documents *why* there is no
Windows Actions build (toolchain too large, Aurora tree gigabytes, test suite needs a disc) and
concludes "build locally, then package and publish the existing binaries." That is a real, stated
limitation — but it means Milestone 9's "preserve Windows-driven Linux checks" has no Windows half.
*Cheapest mitigation, no discs needed:* a hosted workflow that runs the pure, disc-free checks —
`map_to_msvc.py --self-test` (`ci_linux.sh:23`), `python3 tools/roguelite/test_*.py`, and
`check_strings.py` (`tools/release/README.md:237`) — on every `tools/**` change. This would catch
tooling regressions the current setup cannot see at all.

**Gap 2 — `.gitignore` does not cover the container formats the release guard forbids, and 761
untracked files (including ~45 MB of Dawn/pipeline caches) are one careless `git add -A` from
staging.** `.gitignore:83-93` lists `.iso .gcm .dol .dat .usd .ssm .sem .hps .thp .gci .xdelta`,
but `check_release.ps1:36-38` additionally forbids `.rvz .wia .ciso .wbfs .nkit .gcz .sav .rel .elf`.
Verified by `git check-ignore`: `x/vanilla.rvz`, `x/vanilla.ciso`, `x/vanilla.wia`, `x/vanilla.wbfs`,
`x/vanilla.gcz`, `x/vanilla.nkit`, `x/vanilla.sav`, `x/vanilla.elf` are all **NOT-IGNORED**. The
repo's own rule is "never `git add -A`" (`CLAUDE.md` §7), but the *stated purpose* of the NEVER-COMMIT
block is precisely to remove that reliance — `.gitignore:81-82` says these paths "all existed
untracked-but-unignored, which is one careless add away from shipping." That defence has since
rotted: `_build/benchmarks/`, `_build/coordination/`, `_build/deepseek-coordination/`,
`_build/roguelite-bf-kit/`, `_build/sol-*/`, `menu/out_roguelite/`, `menu/out_effects_study/` and
`menu/out_roguelite_expansion/` are all untracked-and-unignored. **Concrete leak risk:** anyone
following the unqualified `git add -A && git commit` advice commits 24 MB of `dawn_cache.db`
(game-derived render state), a 2 MB `effects-assets-study-01.zip`, and 108 files of `menu/out_roguelite/`.
The ISO extensions themselves are safe; the containers are not. *Mitigation:* add the missing
extensions plus `_build/benchmarks/`, `_build/coordination/`, `_build/deepseek-*/`, and the
`menu/out_*/` render-output trees — and add a CI `git status --porcelain` guard, which is the only
check that survives human error.

**Gap 3 — The Linux package has no disc-data guard.** `check_release.ps1` is thorough
(allowlist, denylist, content sniffing, `ui/` blob equality, personal-path scan, manifest) but is
PowerShell/Windows-only and has no Linux counterpart. `package_linux.py` enforces GLIBC ≤ 2.35
across every ELF (`:26`, `:82-85`) and writes `manifest.json` + `runtime.sha256`, but it has **no
allowlist and no content sniffing**. It copies `build/assets/fonts`, `build/ui`, `tools/port/release/*`,
`tools/port/udev/`, `tools/release/licenses/` and `docs/LINUX_PORT_STATUS.md` wholesale. Today
those inputs are clean — but nothing *enforces* that, and `docs/LINUX_PORT_STATUS.md:24` notes cold
shader caches land next to the build. A future asset or cache file in the wrong directory ships
undetected. The most direct copy of `build_release.ps1`'s Copy-In guard (throw on any source under
`_build/ace|_build/packs|_build/m-ex|…` or with a disc extension) into `package_linux.py` closes
most of it in ~15 lines.

**Gap 4 — No normal-speed soak or repeated-transition lifecycle harness exists.** Nothing matches
`*soak*` or `*lifecycle*` under `_build/`. The longest recorded run is
`_build/agents/linux/run-iPfB6jwW` at `seconds=1800` (`exit=0`) and the certification log
`_build/agents/roguelite-certification/native-certification.log` reaches ~164 656 retrace frames
(~46 min) with `AX: 554400 frames … underruns=31102` before `exit 0`. Both are useful but neither
is a *designed* lifecycle harness with resource/memory/input-ownership tracking across hundreds of
room changes, and neither records a frame-time target against named reference hardware. Note the
31 102 audio underruns in that run — consistent with `LINUX_PORT_STATUS.md:22-23` ("cold shader
compilation caused audible-risk underruns; sustained performance and audio quality are not yet
signed off") and with the plan's "no growing audio underruns" criterion (`:377`). **PENDING** for
the signed-off performance number; the harness itself is buildable.

**Gap 5 — Display-backend evidence is not self-certifying.** The Wayland pass is real and
well-constructed (`launcher-qt.yml:48-64` unsets `DISPLAY`, forces `QT_QPA_PLATFORM=wayland`,
asserts 4 non-empty PNGs — a genuine native-Wayland proof, not a fallback). But (a) there is **zero
X11/XWayland evidence** in any workflow or run directory; and (b) no run log records *which* video
driver or compositor was in use — `melee-pc.log` records `aurora backend 4` (Vulkan) and nothing
else, and `certify_rooms.py:880` records `MELEE_BACKEND` but not the display server. Without a
logged `SDL video driver: wayland` / `x11` / `xwayland` line, no future run can be *proven* to be
native rather than silently falling back. Logging the resolved SDL video driver at startup is a
small, high-value change that converts every future run from ambiguous to auditable.

**Gap 6 — Runner registration is unactioned, so the Linux CI gate is inert.**
`linux-port.yml:15` requires `vars.LINUX_RUNNER_ENABLED == 'true'`; `~/.config/melee-linux/build.env`
does not exist here; `check_linux_wsl.sh:3-4` hard-fails without it. `LINUX_CONTINUOUS_CHECKS.md:48-49`
says it plainly: "Workflow files alone do not register runners, change repository rules or prove
Windows/Linux compatibility." With the gate closed, **a skipped game job must not be read as a pass**
(`LINUX_CONTINUOUS_CHECKS.md:23-24`). Note also the deliberate PR exclusion (`:15`,
`linux-port.yml:13-14`) — correct security posture for a personal disc-bearing runner, but it means
fork PRs get *no* Linux signal. Worth noting the one recorded CI run
(`packages-baseline/validation.txt`: `…/actions/runs/36668852464`) is a **launcher** run.

**Gap 7 — Physical input is entirely unverified, and this is honestly recorded.**
`LINUX_PORT_STATUS.md:24-25` says so in bold. Four-port decode/calibration fixtures pass
(`tools/port/tests/gc_report.c`), but every recorded run logs `gw: pad: SDL sees 0 controller(s)`.
Rumble (`gc_adapter.c:1134-1148`), hotplug (`gc_adapter.c:945`) and multi-port are code-only.
This is a hardware gate, not a code defect — and the docs correctly avoid claiming otherwise.
Remains **PENDING** for physical adapter + SDL controllers.

**Gap 8 — Installed/relocated/upgraded-profile testing is manual, not scripted.** The relocated
read-only Ubuntu install genuinely passed 3× 201/201 with checksums and 170 ELFs at GLIBC ≤ 2.35
(`packages-baseline/validation.txt`, `LINUX_PORT_STATUS.md:43-45`), and writable-user-data fallback
is unit-tested. But no script reproduces it: nothing reruns the package, relocates it, re-verifies
`runtime.sha256` and relaunches. `ci_linux.sh:42` packages and stops. Making
"relocate → checksum → three 201/201 → relaunch" a script would turn a one-time manual result into
a repeatable gate, and it needs no new hardware — only the three discs already required.

---

## Proposed order

1. **Close Gap 2 first — it is the only finding with live data-loss/IP-exposure risk, it costs
   ~10 `.gitignore` lines, and it is independent of every other item.** Extend the NEVER-COMMIT
   block with `.rvz .ciso .wia .wbfs .gcz .nkit .sav .elf .rel`, ignore the current untracked
   `_build/{benchmarks,coordination,deepseek-*,roguelite-*,sol-*,effects-*,model-tests,falco-*}/`
   and `menu/out_{roguelite,roguelite_expansion,effects_study}/`, then add a hosted
   `git status --porcelain` + tracked-disc-extension assertion to CI. **No discs, no build, no
   hardware required.** Note the tracked tree is currently *clean* (0 tracked disc/binary artefacts),
   so this is preventative hardening, not remediation of a live leak.
2. **Gap 1 (cheap half): add the hosted pure-tooling workflow** over `tools/**`. Disc-free, minutes
   of CI, and it makes the game build system visible to CI for the first time. Do this before any
   Windows CI discussion, because the full Windows CI is genuinely blocked
   (`README.md:196-209`) and the docs should keep saying so.
3. **Gap 5: log the resolved SDL video driver at game startup**, and add an X11/XWayland step to
   `launcher-qt.yml` mirroring the existing Wayland step (`:48-64`) — `xvfb-run` or
   `weston-xwayland`, with an assertion that the compositor is actually up, so an unavailable
   backend fails loudly rather than passing by fallback. Turns ambiguity into evidence for every
   future run; do it *before* any new Wayland/X11 acceptance claims are recorded.
4. **Gap 3: port the `build_release.ps1` Copy-In guard into `package_linux.py`.** Small, and it
   closes the asymmetry where the Windows package is triple-guarded and the Linux package is not.
5. **Gap 8: script the relocate/checksum/three-disc/upgrade cycle** as a follow-on step to
   `ci_linux.sh:42`. Reuses existing infra and discs; converts the strongest current evidence from
   a one-off into a repeatable gate. Pair it with a clean-profile-vs-upgraded-profile launcher run.
6. **Gap 6: register the runner or downgrade the claim.** Either set `LINUX_RUNNER_ENABLED` with a
   documented trusted-branch list, or amend `LINUX_CONTINUOUS_CHECKS.md` to state the game CI is
   authored-but-inert. What must *not* happen is the current ambiguity persisting while
   `LINUX_PORT_STATUS.md` reads as though continuous checks are live.
7. **Gap 4: build the normal-speed soak/lifecycle harness** (≥60 min, repeated transitions, resource
   and input-ownership tracking) and **agree the reference hardware + frame-time targets** with the
   user. Only then can the ~31 102 underruns in the 46-minute certification run be read as a pass
   or a failure. Explicitly **normal speed** — reuse `certify_rooms.py:1132-1136`'s existing
   turbo/uncapped refusal rather than adding a new path.
8. **Gap 7 last: physical GameCube adapter and SDL controllers.** Pure hardware gate, no code work
   available, and it cannot be honestly closed by any agent. Book it with the user; until then the
   existing bold "Hardware behavior remains unverified" is the correct and sufficient statement.

**Standing constraint, honoured throughout:** the uncapped/turbo benchmark is CANCELLED. This audit
confirmed nothing re-enables it — no scheduled workflow exists, no tool in the tree sets
`MELEE_FPS=u`, and the only code that inspects it (`certify_rooms.py:1135-1136`) *refuses* to run.
Its residual artefacts under `_build/benchmarks/uncapped-20260930/` should be folded into the
Gap 2 ignore list rather than reused, and its `x11` `SDL_VIDEODRIVER` string must **not** be
mistaken for X11 display evidence (see Gap 5).

---

## Explicitly PENDING (requires hardware or a build this audit did not run)

| Item | Needs |
|---|---|
| Any Windows build verification | Windows host + clang + MSVC + Aurora x86 tree + discs |
| Any Linux build verification by this audit | A build run — **not attempted**; see recorded results above |
| X11 / XWayland backend evidence | XWayland/Xvfb session; no such run exists anywhere |
| Physical GameCube adapter (input, rumble, hotplug, focus handoff, 4 ports) | Physical hardware |
| SDL controller evidence | Physical controller |
| Sustained Wayland gameplay, resize/fullscreen/focus | Long-session hardware run |
| 60-min normal-speed soak + frame-time target vs reference hardware | User-agreed reference hardware |
| Interactive Qt + real game on Windows with existing user data | Windows host + discs |
| Linux `melee-linux` self-hosted runner actually executing | Runner registration + repo variable |
