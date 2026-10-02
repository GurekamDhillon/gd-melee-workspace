param(
    [string]$Distribution = 'Ubuntu-22.04',
    [Parameter(Mandatory=$true)][string]$GameCheckout
)
$ErrorActionPreference = 'Stop'
$toolsRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$gameRoot = (Resolve-Path $GameCheckout).Path
$linuxTools = (& wsl.exe -d $Distribution --exec wslpath -u $toolsRoot).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot locate the workspace in WSL.' }
$linuxGame = (& wsl.exe -d $Distribution --exec wslpath -u $gameRoot).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot locate the game checkout in WSL.' }
# Disc paths, UI assets and caches are configured once in the WSL environment file.
& wsl.exe -d $Distribution --cd $linuxTools --exec bash tools/port/check_linux_wsl.sh $linuxGame
exit $LASTEXITCODE
