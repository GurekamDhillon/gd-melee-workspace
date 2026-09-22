# make_package.ps1 - build the folder (and zip) two players need to play GD's Melee online.
#
#   powershell -File tools\netplay\make_package.ps1        -> Desktop\GDMelee-Online\ + .zip
#
# BOTH players must run the SAME package (the handshake refuses a different melee-pc.exe build) and
# the SAME disc (NTSC 1.02; the handshake refuses a different disc). Each supplies their own ISO:
# no disc data is ever in the package.
param(
  [string]$Out = (Join-Path ([Environment]::GetFolderPath("Desktop")) "GDMelee-Online"),
  # your matchmaking server (tools\netplay\server), "host:port"; empty = players swap addresses by hand.
  # Defaults to _build\netplay_server.txt when that file exists.
  [string]$Server = ""
)
$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$build = Join-Path $root "_build"

if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Out | Out-Null
foreach ($f in @("melee-pc.exe", "melee-pc.map", "SDL3.dll", "webgpu_dawn.dll",
                 "initial_pipeline_cache.db", "initial_pipeline_cache.core")) {
  Copy-Item (Join-Path $build $f) $Out
}
Copy-Item (Join-Path $build "ui") (Join-Path $Out "ui") -Recurse
Copy-Item (Join-Path $build "card") (Join-Path $Out "card") -Recurse   # an unlocked save: all characters
Copy-Item (Join-Path $build "card-ace") (Join-Path $Out "card-ace") -Recurse   # the same for the ACE disc
New-Item -ItemType Directory -Force -Path (Join-Path $Out "nomods") | Out-Null
Copy-Item (Join-Path $PSScriptRoot "launch.ps1") $Out
if (-not $Server) {
  $sf = Join-Path $build "netplay_server.txt"
  if (Test-Path $sf) { $Server = (Get-Content $sf -Raw).Trim() }
}
if ($Server) {
  Set-Content -Path (Join-Path $Out "netplay_server.txt") -Value $Server -Encoding ascii
  Write-Output "server:  $Server (room codes)"
} else {
  Write-Output "server:  none - players swap addresses (set -Server or _build\netplay_server.txt for room codes)"
}
# which build this is: both players must run the same one
$rev = (git -C (Join-Path $root "melee") rev-parse --short HEAD 2>$null)
if ($rev) { Set-Content -Path (Join-Path $Out "BUILD.txt") -Value "melee $rev, packaged $(Get-Date -Format 'yyyy-MM-dd HH:mm')" -Encoding ascii }

Set-Content -Path (Join-Path $Out "Play GD Melee.bat") -Encoding ascii -Value @'
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1"
'@
Set-Content -Path (Join-Path $Out "Play GD Melee (keyboard).bat") -Encoding ascii -Value @'
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" -Keyboard
'@
Copy-Item (Join-Path $PSScriptRoot "HOW TO PLAY ONLINE.txt") $Out

$zip = "$Out.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $Out "*") -DestinationPath $zip -CompressionLevel Optimal
$mb = [Math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Output "package: $Out"
Write-Output "zip:     $zip ($mb MB)"
