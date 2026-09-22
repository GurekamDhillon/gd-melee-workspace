# make_package.ps1 - the "zip for friends": the public release build with your matchmaking server
# filled in. A thin wrapper over tools\release\build_release.ps1 (the one packaging path, with its
# disc-data guard); the old separate package, its launch.ps1 and its unlocked card files are gone.
#
#   powershell -File tools\netplay\make_package.ps1                 -> Desktop\GDMelee-Online\ + .zip
#   powershell -File tools\netplay\make_package.ps1 -Server host:port
#
# The server address comes from -Server, else _build\netplay_server.txt (git-ignored; it goes
# into the zip's netplay_server.txt and the launcher's Online tab can change it). Friends run
# "GD Melee.exe" and pick their own ISO; "Unlock every character and stage" is on by default and
# netplay unlocks everything for both players anyway, so no save files ship.
# BOTH players must run the same package: the handshake refuses a different melee-pc.exe build.
param(
  [string]$Out = "",
  [string]$Server = ""
)
$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not $Out) { $Out = Join-Path ([Environment]::GetFolderPath("Desktop")) "GDMelee-Online" }
if (-not $Server) {
  $sf = Join-Path $root "_build\netplay_server.txt"
  if (Test-Path $sf) { $Server = (Get-Content $sf -Raw).Trim() }
}
$version = (Get-Content (Join-Path $root "tools\release\VERSION") -Raw).Trim() + "-friends"
$work = Join-Path $root "_build\release\friends"
$buildArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $root "tools\release\build_release.ps1"),
               "-Version", $version, "-OutDir", $work)
if ($Server) { $buildArgs += @("-Server", $Server) }
& powershell @buildArgs
if ($LASTEXITCODE -ne 0) { throw "build_release.ps1 failed" }

$name = "GDMelee-$version-win64"
if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
Copy-Item (Join-Path $work $name) $Out -Recurse
Copy-Item (Join-Path $work "$name.zip") "$Out.zip" -Force
if ($Server) { Write-Output "server:  $Server (room codes)" }
else { Write-Output "server:  none - players swap addresses (set -Server or _build\netplay_server.txt for room codes)" }
Write-Output "package: $Out"
Write-Output "zip:     $Out.zip ($([Math]::Round((Get-Item "$Out.zip").Length / 1MB, 1)) MB)"
