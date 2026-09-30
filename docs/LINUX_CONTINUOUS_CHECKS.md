# Keep Linux working while developing on Windows

There are two checks, with different prerequisites.

## Launcher: hosted Windows and Linux CI

The workspace repository's `.github/workflows/launcher-qt.yml` builds the Qt launcher,
runs migration/disc/mod/process tests, deploys Qt, and renders English/Spanish UI screens.
It runs on GitHub-hosted Windows 2022 and Ubuntu 22.04 when launcher code changes. It needs
no laptop, local runner, discs or secrets. Both checks must pass before merging launcher
changes. Artifacts are build previews, not GitHub Releases.

## Game: trusted disc-backed Linux runner

The game repository's `.github/workflows/linux-port.yml` uses a self-hosted Linux runner
labelled `melee-linux`. It builds the current game commit, checks LLVM ABI/ELF mapping,
runs the vanilla/Akaneia/ACE engine suites and creates a local package. The same entry point,
`tools/port/ci_linux.sh`, runs from WSL2 on the Windows desktop, so the laptop can stay off.
WSL and the runner must be running for jobs to execute.

Both repositories are public. The disc-backed workflow is opt-in and accepts only trusted
pushes to the configured branches or manual runs; it deliberately does not run PR code on
a personal runner. The hosted Qt workflow does handle PRs. Do not treat a skipped game job
as a successful Linux game check.

One-time setup:

1. Prepare Ubuntu 22.04 with LLVM 22.1.8, CMake >=3.25, multilib, a native Qt SDK and the
   dependencies in `tools/port/ubuntu_setup.sh`. That script is for an isolated build
   environment, not an unreviewed host installation.
2. Register a **Linux** GitHub Actions runner in WSL2 or another Linux environment; add
   label `melee-linux`. Set repository variable `LINUX_RUNNER_ENABLED=true` only after
   reviewing which trusted branches may execute there.
3. Set `LINUX_TOOLS_REF` to the reviewed tools commit SHA (the tools repository is public).
4. Keep the three disc images locally. Create `~/.config/melee-linux/build.env`:

   ```bash
   MELEE_VANILLA_ISO='/path/to/vanilla.iso'
   MELEE_AKANEIA_ISO='/path/to/Akaneia.iso'
   MELEE_ACE_ISO='/path/to/ACE.iso'
   GW_JOBS=8
   # Optional override; otherwise uses the tools repo's committed _build/ui:
   # MELEE_UI_ASSETS='/path/to/generated/ui'
   ```

5. Provision libusb 1.0.29 source at `_build/linux/libusb-src` in the tools checkout,
   SHA-256 `5977fc950f8d1395ccea9bd48c06b3f808fd3c2c961b44b0c2e6e29fc3a70a85`.
6. Run the workflow once and inspect the evidence. Workflow files alone do not register
   runners, change repository rules or prove Windows/Linux compatibility.

Optional local check from the Windows tools checkout:

```powershell
.\tools\port\check_linux.ps1 -GameCheckout 'C:\path\to\melee'
```

Prefer WSL's Linux filesystem for build speed. The wrapper also accepts Windows-mounted
checkouts. New custom characters/stages still need gameplay checks: a green engine suite
cannot verify every asset, GPU output, audio quality, save/reload flow or physical controller.
Networking is outside the current parity scope.

GitHub runner reference: https://docs.github.com/en/actions/concepts/runners/self-hosted-runners
