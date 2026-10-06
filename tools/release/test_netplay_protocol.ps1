param([string]$MeleeDir = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'netplay_protocol.ps1')
Assert-NetplayMetadata "0.1.6`r`nnetplay_protocol 5`r`n"
foreach ($bad in @('', 'netplay_protocol 4', 'netplay_protocol 6', "netplay_protocol 5`nnetplay_protocol 5")) {
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
if ($MeleeDir) { Assert-NetplaySource $MeleeDir }
Write-Output 'netplay source/metadata policy checks passed'
