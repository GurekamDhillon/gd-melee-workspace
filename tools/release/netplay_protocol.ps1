# Release compatibility policy. Keep in step with server/gdmelee_server.py and gw_net.h.
function Get-NetplayProtocol { return 3 }

function Assert-NetplaySource([string]$MeleeDir) {
  $header = Get-Content (Join-Path $MeleeDir 'pc/platform/gw_net.h') -Raw
  $match = [regex]::Match($header, '(?m)^\s*#define\s+GW_NET_PROTOCOL_VERSION\s+(\d+)u?\s*$')
  if (-not $match.Success -or [int]$match.Groups[1].Value -ne (Get-NetplayProtocol)) {
    throw "Netplay protocol mismatch: this release requires protocol $(Get-NetplayProtocol); check pc/platform/gw_net.h and rebuild the game."
  }
}

function Assert-NetplayMetadata([string]$Text) {
  $matches = [regex]::Matches($Text, '(?m)^netplay_protocol\s+(\d+)\s*$')
  if ($matches.Count -ne 1 -or [int]$matches[0].Groups[1].Value -ne (Get-NetplayProtocol)) {
    throw "version.txt must declare netplay_protocol $(Get-NetplayProtocol) exactly once; repackage this release."
  }
}
