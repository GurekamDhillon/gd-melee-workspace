# check_compile_linux.ps1 - the Linux COMPILE check, run headless from Windows through WSL.
#
#   powershell -File tools\port\check_compile_linux.ps1                  # the whole game: 993 TUs + the shims
#   powershell -File tools\port\check_compile_linux.ps1 -Quick           # 24 TUs spread over the list + every shim
#   powershell -File tools\port\check_compile_linux.ps1 -Tu src/melee/ft/ftdata.c,src/melee/it/item.c
#   ... -Melee <dir>      the game checkout to compile (default: <workspace>\melee, or $env:GW_MELEE)
#   ... -Distro Debian    the WSL distribution that holds the build environment (default Debian)
#   ... -Lb <path>        the build environment's folder inside that distribution (default ~/lb2)
#   ... -All              ignore what is already compiled and recompile everything
#
# It compiles only (game TUs through clang -> gwtool, and the native shims): no link, no disc image, no
# window, no game started. Exit 0 = pass, 1 = a unit failed to compile (the log names them), 2 = the
# environment is not ready. Objects are kept in <lb>/check, so a second run recompiles only what changed.
# The environment is the rootless Ubuntu 22.04 one of 2026-10-05 (~/lb2/enter.sh: user namespace + chroot,
# no root, nothing installed); this script installs nothing and never uses sudo.
param(
  [string]$Melee = "",
  [string]$Distro = "Debian",
  [string]$Lb = "~/lb2",
  [string[]]$Tu = @(),
  [switch]$Quick,
  [switch]$All
)
$ErrorActionPreference = "Stop"
$ws = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $Melee) { $Melee = if ($env:GW_MELEE) { $env:GW_MELEE } else { Join-Path $ws "melee" } }
if (-not (Test-Path $Melee)) {
  # a worktree has no melee checkout of its own: use the main checkout's
  $common = (git -C $ws rev-parse --path-format=absolute --git-common-dir).Trim()
  $main = Split-Path (Resolve-Path $common).Path -Parent
  $Melee = Join-Path $main "melee"
}
$Melee = (Resolve-Path $Melee).Path
function WslPath([string]$p) { $r = (& wsl.exe -d $Distro --exec wslpath -u $p).Trim(); if ($LASTEXITCODE -ne 0 -or -not $r) { throw "wslpath failed for a path" }; $r }
$lws = WslPath $ws
$lmelee = WslPath $Melee
$lbq = $Lb -replace '^~', '$HOME'

$args2 = @()
if ($Quick) { $args2 += "--quick" }
if ($All) { $args2 += "--all" }
foreach ($t in $Tu) { $args2 += @("--tu", $t) }
# the one command line that runs inside the environment: values are single-quoted for bash
function Q([string]$s) { "'" + $s.Replace("'", "'\''") + "'" }
# The workspace path has an apostrophe (GD's Melee), which the Makefile-style depfiles and xargs cannot carry.
# Inside the environment's own mount namespace both checkouts are bind-mounted at plain paths and used from there.
$inner = "mkdir -p /mnt/cw /mnt/cm && mount --bind $(Q $lws) /mnt/cw && mount --bind $(Q $lmelee) /mnt/cm && " +
         "export GW_ROOT=/mnt/cw GW_MELEE=/mnt/cm GW_GWTOOL=/mnt/h/gwtool/gwtool GW_DEPS_SOURCE_CACHE=/mnt/h/deps " +
         "GW_LIBUSB_BUILD=/mnt/h/outB/libusb GW_BUILD_ROOT=/mnt/h/check GW_AURORA_LINUX_BUILD=/mnt/h/outA/aurora GW_DAWN_GEN_INCLUDE=/mnt/h/outA/aurora/_deps/dawn-build/gen/include GW_JOBS=`${GW_JOBS:-8}; " +
         "bash /mnt/cw/tools/port/check_compile_linux.sh " + (($args2 | ForEach-Object { Q $_ }) -join " ")
$outer = "set -e; cd $lbq; [ -x enter.sh ] || { echo 'no build environment at $Lb (see _build/audit-20261003/linux-build/PROGRESS.md)'; exit 2; }; ./enter.sh bash -c " + (Q $inner)
Write-Output "melee $Melee"
Write-Output "distro $Distro, environment $Lb (compile only, nothing is started with a window)"
& wsl.exe -d $Distro --exec bash -c $outer
exit $LASTEXITCODE
