param([string]$MeleeDir = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'netplay_protocol.ps1')
Assert-NetplayMetadata "0.1.6`r`nnetplay_protocol 3`r`n"
foreach ($bad in @('', 'netplay_protocol 2', 'netplay_protocol 4', "netplay_protocol 3`nnetplay_protocol 3")) {
  $rejected = $false
  try { Assert-NetplayMetadata $bad } catch { $rejected = $true }
  if (-not $rejected) { throw "accepted incompatible metadata: $bad" }
}
$server = Get-Content (Join-Path $PSScriptRoot '../netplay/server/gdmelee_server.py') -Raw
$m = [regex]::Match($server, '(?m)^NETPLAY_PROTOCOL = (\d+)')
if (-not $m.Success -or [int]$m.Groups[1].Value -ne (Get-NetplayProtocol)) {
  throw 'server and release protocol disagree'
}
if ($MeleeDir) { Assert-NetplaySource $MeleeDir }
Write-Output 'netplay source/metadata policy checks passed'
