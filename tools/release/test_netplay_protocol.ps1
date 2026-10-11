param([string]$MeleeDir = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'netplay_protocol.ps1')
$protocol = Get-NetplayProtocol -MeleeDir $MeleeDir
Assert-NetplayMetadata "fixture`r`nnetplay_protocol $protocol`r`n" -MeleeDir $MeleeDir
foreach ($bad in @('', "netplay_protocol $($protocol - 1)", "netplay_protocol $($protocol + 1)", "netplay_protocol $protocol`nnetplay_protocol $protocol")) {
  $rejected = $false
  try { Assert-NetplayMetadata $bad -MeleeDir $MeleeDir } catch { $rejected = $true }
  if (-not $rejected) { throw "accepted incompatible metadata: $bad" }
}
$server = Get-Content (Join-Path $PSScriptRoot '../netplay/server/gdmelee_server.py') -Raw
$m = [regex]::Match($server, '(?m)^FALLBACK_NETPLAY_PROTOCOL = (\d+)')
if (-not $m.Success -or [int]$m.Groups[1].Value -ne $protocol) {
  throw 'standalone server fallback and game protocol disagree; update the fallback after changing gw_net.h'
}
# publish.ps1's release body must take the number from netplay_protocol.ps1, never spell one out
$pub = Get-Content (Join-Path $PSScriptRoot 'publish.ps1') -Raw
if ($pub -notmatch 'Get-NetplayProtocol' -or $pub -match '(?i)protocol\s+\*{0,2}\d') {
  throw 'publish.ps1 hard-codes a netplay protocol number'
}
if ($MeleeDir) { Assert-NetplaySource $MeleeDir }
Write-Output 'netplay source/metadata policy checks passed'
