param([string]$MeleeDir = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'netplay_protocol.ps1')
Assert-NetplayMetadata "0.2.2`r`nnetplay_protocol 6`r`n"
foreach ($bad in @('', 'netplay_protocol 4', 'netplay_protocol 5', "netplay_protocol 6`nnetplay_protocol 6")) {
  $rejected = $false
  try { Assert-NetplayMetadata $bad } catch { $rejected = $true }
  if (-not $rejected) { throw "accepted incompatible metadata: $bad" }
}
$server = Get-Content (Join-Path $PSScriptRoot '../netplay/server/gdmelee_server.py') -Raw
$m = [regex]::Match($server, '(?m)^NETPLAY_PROTOCOL = (\d+)')
if (-not $m.Success -or [int]$m.Groups[1].Value -ne (Get-NetplayProtocol)) {
  throw 'server and release protocol disagree'
}
# publish.ps1's release body must take the number from netplay_protocol.ps1, never spell one out
$pub = Get-Content (Join-Path $PSScriptRoot 'publish.ps1') -Raw
if ($pub -notmatch 'Get-NetplayProtocol' -or $pub -match '(?i)protocol\s+\*{0,2}\d') {
  throw 'publish.ps1 hard-codes a netplay protocol number'
}
if (-not $MeleeDir) { $MeleeDir = $env:GW_MELEE }
if (-not $MeleeDir) {
  $candidate = Join-Path $PSScriptRoot '../../melee'
  if (Test-Path (Join-Path $candidate 'pc/platform/gw_net.h')) { $MeleeDir = $candidate }
}
if ($MeleeDir) {
  Assert-NetplaySource $MeleeDir
  Write-Output 'game header, matchmaking server and release policy agree'
} else { Write-Output 'game checkout absent: source agreement not checked (pass -MeleeDir or set GW_MELEE)' }
Write-Output 'netplay source/metadata policy checks passed'
