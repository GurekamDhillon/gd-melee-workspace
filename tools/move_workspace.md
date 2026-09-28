# Workspace relocation plan

Prepared 2026-09-27 on `codex/ws-paths`. This is a future operator procedure;
no copy, move, junction change, Git repair, build or game run was performed here.
This file supersedes old machine-path examples for relocation only.

## Path design

- `GW_ROOT`: workspace root; scripts derive it from their location unless overridden.
  A workspace worktree has its own root: set `GW_ROOT` explicitly when using shared
  tools/builds from the main checkout. `GW_MELEE` selects the separate game checkout.
- `GW_BUILD_ROOT`: one lane's objects, executable and runs; defaults to
  `$GW_ROOT/_build`. Derived paths are assigned after `portlib.sh` loads `.env`.
- `GW_AURORA_ROOT`: stable, space-free and apostrophe-free junction used by **all**
  Aurora batch wrappers. Set it to `C:/gdm` while retaining the existing junction name.
  Never configure Aurora through `C:/Users/Gurek/Desktop/GD's Melee`, or through
  `E:/Projects/Melee Workspace`. Quoting alone does not fix Dawn's generated commands.
- Disc inputs: `GW_ISO_VANILLA`, `GW_ISO_AKANEIA`, `GW_ISO_ACE`; `GW_ISO` overrides
  the default run disc. No hard-coded fallback disc paths remain in executable tools.
- Research inputs: `GW_BRAWL_FILES` is the extracted Brawl `files` directory;
  `GW_ULTIMATE_EXTRACT` is Ultimate's extracted root containing `fighter`;
  `GW_GHIDRA_PROJECTS` is the directory containing `sora_acmd`.
  Defaults are `_local/brawl/files`, `_local/ultimate`, and the user's
  `ghidra-projects` directory respectively. `_local` is ignored.
- `GW_MENU_DUMP`: extracted menu data, default `_build/meleedump` (ignored).
  Package output still uses Windows' Desktop known-folder API or explicit `-Out`;
  this is a user destination, not a workspace-location dependency.
- Python programs consume exported environment variables; they do not execute `.env`.
  In Git Bash use `set -a; . "$GW_ROOT/.env"; set +a` before invoking them directly.
  `.env` is trusted local shell code, not PowerShell syntax. Never paste its contents
  into a report. An explicit CLI input option, where available, still works.
- The Halberd IR's `${GW_BRAWL_FILES}/...` paths are symbolic provenance, not literal
  filesystem inputs. Its generator emits the same notation. Resolve against that
  variable when following evidence; no general JSON interpolation is implied.

## 1. Freeze and inventory

Stop agents, editors that write the trees, builds, games and local netplay servers.
Stop only processes you own, after inspecting their executable paths. Capture both
repos' `git status --short`, HEAD, and `git worktree list --porcelain`; preserve all
uncommitted and untracked work. Do not prune worktrees during the move.

In PowerShell, record the lists **before** copying. Keep the variables in this shell:

```powershell
$oldRoot = "C:\Users\Gurek\Desktop\GD's Melee"
$newRoot = 'E:\Projects\Melee Workspace'
$workspaceTrees = @(git -C $oldRoot worktree list --porcelain |
  Where-Object { $_.StartsWith('worktree ') } | ForEach-Object { $_.Substring(9) })
$gameTrees = @(git -C "$oldRoot\melee" worktree list --porcelain |
  Where-Object { $_.StartsWith('worktree ') } | ForEach-Object { $_.Substring(9) })
python "$oldRoot\tools\check_workspace_paths.py" --root $oldRoot --all
```

Run the checker from this prepared worktree until its changes are integrated into
main. `--all` scans ignored text, `.rsp`, dependency files, configs and CMake caches;
it can take time on vendored sources. Exit 1 means findings, not an execution failure;
exit 2 means incomplete inspection. It prints `.env` key names and line numbers only.
It does not follow directory junctions, traverse Git object stores, or inspect binary
contents. Audit external worktrees and external build roots with `--root` separately.
Expected hits include test fixtures, documentation examples, the intended junction,
tool installations and Git's absolute administrative pointers. Review every hit;
a zero count is not the move acceptance criterion.

Inventory junctions/reparse points without copying their targets implicitly. Record
external discs, Ghidra projects, Ultimate/Brawl extractions, Blender, tool installations,
user environment variables, shortcuts, scheduled tasks and path-keyed agent memory.
A project rename does not relocate these automatically.

## 2. Copy, retain the original

Copy the **whole workspace**, including hidden files, the main `.git`, `melee/.git`,
all workspace and game worktrees, ignored local assets/mods, saves, `.env`,
`_toolchains`, `experiment`, `_build` libraries/executables/maps and lane/run evidence.
Git clone or `git archive` alone loses ignored assets and uncommitted work.
Copy externally located worktrees separately and record their new paths.

Use an empty destination. Example future PowerShell command:

```powershell
robocopy $oldRoot $newRoot /E /COPY:DAT /DCOPY:DAT /XJ /R:2 /W:2
if ($LASTEXITCODE -ge 8) { throw 'Copy failed; retain original and inspect robocopy output' }
```

`/XJ` excludes junction targets; recreate intentionally excluded junctions separately.
Do not use `/MIR` or remove the source. Cross-volume copying normally expands hardlinks:
allow space for every lane's objects, or archive and later recreate expendable lanes.
Never assume copied objects retain hardlinks. Compare counts and hashes of important
files (both Git directories, source changes, assets, executables, saves) before cutover.

## 3. Re-point the Aurora junction

Inspect `Get-Item -LiteralPath 'C:\gdm' | Format-List FullName,LinkType,Target`.
Confirm it is the expected **junction**, not a real directory or another target.
Only after the copy is verified and all users have stopped, remove the junction entry
and recreate `C:\gdm` pointing at `$newRoot`. Do this in PowerShell with a checked
`DirectoryInfo.Delete()` on the junction itself (no recursive deletion), then
`New-Item -ItemType Junction -Path 'C:\gdm' -Target $newRoot`.
If it is missing or not a junction, stop and resolve that discrepancy first.
Set `GW_AURORA_ROOT=C:/gdm`. Confirm `C:\gdm\melee\extern\aurora` reaches the new copy.
Keep the original workspace as a rollback copy; do not use it for further work after repair.

## 4. Repair both repositories' worktrees

The main workspace and game each own separate worktree registrations. Their copied
`.git/worktrees/*/gitdir` files and worktrees' `.git` files contain absolute old paths.
Repair from the **new main checkout of each repo**, passing **that repo's** moved
worktrees, including those outside the main workspace. Example for trees under `$oldRoot`:

```powershell
function Convert-MovedTree([string]$tree) {
  $prefix = $oldRoot.Replace('\', '/').TrimEnd('/') + '/'
  $path = $tree.Replace('\', '/')
  if (-not $path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "External worktree needs an explicit new-path mapping: $tree"
  }
  Join-Path $newRoot $path.Substring($prefix.Length)
}
$workspaceMoved = @($workspaceTrees | Select-Object -Skip 1 | ForEach-Object { Convert-MovedTree $_ })
$gameMoved = @($gameTrees | Select-Object -Skip 1 | ForEach-Object { Convert-MovedTree $_ })
if ($workspaceMoved.Count) { git -C $newRoot worktree repair @workspaceMoved }
if ($LASTEXITCODE) { throw 'Workspace worktree repair failed' }
if ($gameMoved.Count) { git -C "$newRoot\melee" worktree repair @gameMoved }
if ($LASTEXITCODE) { throw 'Game worktree repair failed' }
git -C $newRoot worktree list --porcelain
git -C "$newRoot\melee" worktree list --porcelain
```

Map external entries explicitly before running repair. Check `git status`, HEAD and
`git rev-parse --git-common-dir` in every moved worktree. Inspect nested submodules'
`.git` pointers too; relative pointers survive intact copies, absolute ones require
repair for their owning repository. Update exact `safe.directory` exceptions only if
Git asks; do not disable ownership checks globally. Do not hand-edit or prune registrations.

## 5. Local settings and generated paths

Privately edit the copied `.env`: remove old-root overrides, update any moved ISO path,
and preserve paths for discs that stay where they are. Update persistent/user/shell
`GW_ROOT`, `GW_MELEE`, `GW_BUILD_ROOT`, `GW_OUT`, `GW_SHIMOBJ`, `GW_LINK_OBJECTS`,
`GW_LINK_LIBS`, toolchain/include overrides, `MELEE_MODS_DIR`, replay paths, custom
Dawn cache seeds and controller/script inputs. Open fresh shells afterward.
No `.env` content belongs in Git or this report.

Existing lanes observed during preparation: `alpha`, `art`, `beta`, `charlie_slippi`,
`echo`, `handoff`. Five have old absolute response entries; `handoff` has no response
list at the inspected location. For every retained lane regenerate explicitly:

```powershell
Get-ChildItem -LiteralPath "$newRoot\_build\agents" -Directory | ForEach-Object {
  python "$newRoot\tools\port\link_response.py" --root $newRoot --build-root $_.FullName
  if ($LASTEXITCODE) { throw 'Lane response generation failed' }
}
```

`build.sh` also refreshes its default lane response file before linking. Custom
`GW_LINK_OBJECTS` lists remain caller-owned: inspect/regenerate those yourself.
Do not bulk substitute object names; the baseline response list is curated.
Relative library paths are evaluated from `_build/ax86m`, not the invocation directory.
Absolute dependency/hash records can force recompilation after moving. Let the supported
build pipeline refresh them; do not backdate sources to conceal staleness. Old sandbox
EXEs are copies: start fresh runs, and retain old logs only as historical evidence.

## 6. Aurora CMake cache

Inspect `CMAKE_HOME_DIRECTORY`, `CMAKE_CACHEFILE_DIR`, `Dawn_SOURCE_DIR`, `build.ninja`,
and dependency sub-build caches in `_build/ax86`, `_build/ax86m` and custom lane builds.
The current shared cache uses `C:/gdm`; retaining that alias may preserve valid paths,
but verify all entries. The copied beta `ax86m_fd` cache still identifies the shared
`ax86m` cache directory and must not be treated as an independent configured build.

If any cache uses an old real path, a different alias or a copied build directory,
archive that generated tree outside the active build location and configure a fresh
one **through the junction**. Do not fix CMakeCache.txt with search-and-replace:
Ninja, generated headers and nested caches also embed paths. Preserve downloaded
sources before archiving; `_build/ax86` supplies sources used by `ax86m`.
If both trees are invalid, rebuild `ax86` first, then `ax86m`. Future PowerShell:

```powershell
$env:GW_AURORA_ROOT = 'C:/gdm'
& "$newRoot\_build\build_aurora_x86.bat"   # only when bootstrap regeneration is needed
if ($LASTEXITCODE) { throw 'Aurora bootstrap failed' }
& "$newRoot\_build\build_aurora_melee.bat"
if ($LASTEXITCODE) { throw 'Aurora build failed' }
```

These commands are for the later Windows validation, not this code-only task.
The wrappers reject a missing or unsafe `GW_AURORA_ROOT`; normal game linking continues
through `GW_ROOT`. Preserve the junction spelling/case consistently across configure/build.

## 7. Exact Windows lane test (later, GD's machine)

After the changes are integrated, the copy/repair completed and Aurora validated,
use **Git Bash on Windows**. Choose a fresh lane name; abort if it already exists:

```bash
export GW_ROOT='E:/Projects/Melee Workspace'
export GW_AURORA_ROOT='C:/gdm'
cd "$GW_ROOT"
set -a
. "$GW_ROOT/.env"
set +a
# Ensure .env did not restore old roots; review privately without printing disc values.
export GW_ROOT='E:/Projects/Melee Workspace'
export GW_MELEE="$GW_ROOT/melee"
unset GW_BUILD_ROOT GW_OUT GW_SHIMOBJ GW_LINK_OBJECTS GW_EXE GW_MAP
bash "$GW_ROOT/tools/port/agent_new.sh" ws-move-check || exit 1
export GW_MELEE="$GW_ROOT/worktrees/ws-move-check"
export GW_BUILD_ROOT="$GW_ROOT/_build/agents/ws-move-check"
cd "$GW_MELEE"
bash "$GW_ROOT/tools/port/build.sh" || exit 1
MELEE_VOLUME=3 bash "$GW_ROOT/tools/port/run.sh" --test ws-move-smoke \
  --iso "${GW_ISO_ACE:?Set the ACE disc privately in .env}" || exit 1
MELEE_VOLUME=3 bash "$GW_ROOT/tools/port/run.sh" --realtime ws-move-visible \
  --iso "$GW_ISO_ACE"
```

Require a successful bridge fixpoint/EXE ABI audit, fresh lane EXE/map, and a passing
smoke log in `_build/agents/ws-move-check/runs/ws-move-smoke/melee-pc.log`.
Read failures in full; do not dismiss them from the harness summary. GD then checks
visible menus, controller input, intended mods and a level-0 CPU match; exit normally.
Confirm the running process points into the new lane's run directory. Also exercise
release packaging with an explicit temporary `-Out` (no publish), netplay's local
pair using its supported wrapper, and one requested menu/converter output against
known inputs before deleting the rollback copy. These are additional manual checks,
not prerequisites claimed completed by this patch.

## Acceptance checklist

- [ ] Both repos and every worktree retain their HEAD and dirty/untracked work.
- [ ] `.git` pointers resolve to the new owning repos, never the old backup.
- [ ] Aurora alias resolves to the new root; caches were verified or regenerated via it.
- [ ] All retained/custom lane lists and configuration roots refer to intended new locations.
- [ ] `.env` stays ignored and private; all required external inputs exist.
- [ ] Checker `--all` completed without unreadable locations; each hit has an explanation.
- [ ] Supported lane build/ABI audit and smoke log pass; GD completes visible checks.
- [ ] Packaging/netplay/menu/converter consumers have their separate checks recorded.
- [ ] Retain the original until GD accepts the new workspace; retire it separately afterward.
