# gw_net.h is authoritative. Explicit source, GW_MELEE, then <workspace>/melee.
# Without a default checkout, share the standalone server's tested fallback.
function Get-NetplayProtocol([string]$MeleeDir = '') {
  $selected = if ($MeleeDir) { $MeleeDir } else { $env:GW_MELEE }
  $melee = if ($selected) { $selected } else { Join-Path $PSScriptRoot '../../melee' }
  $headerPath = Join-Path $melee 'pc/platform/gw_net.h'
  if (-not $selected -and -not (Test-Path -LiteralPath $headerPath)) {
    $server = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../netplay/server/gdmelee_server.py') -Raw -Encoding UTF8 -ErrorAction Stop
    $fallback = [regex]::Matches($server, '(?m)^FALLBACK_NETPLAY_PROTOCOL[ \t]*=[ \t]*(\d+)\b')
    if ($fallback.Count -ne 1) { throw 'cannot read the standalone server protocol fallback' }
    return [int]$fallback[0].Groups[1].Value
  }
  $header = Get-Content -LiteralPath $headerPath -Raw -Encoding UTF8 -ErrorAction Stop
  $header = [regex]::Replace($header, '(?s)/\*.*?\*/|//[^\r\n]*', '')
  $definitions = [regex]::Matches($header, '(?m)^[ \t]*#[ \t]*define[ \t]+GW_NET_PROTOCOL_VERSION\b([^\r\n]*)')
  if ($definitions.Count -ne 1) { throw "cannot read one numeric GW_NET_PROTOCOL_VERSION from $headerPath" }
  $value = [regex]::Match($definitions[0].Groups[1].Value, '^[ \t]+(\d+)[uU]?[ \t]*$')
  if (-not $value.Success) { throw "cannot read one numeric GW_NET_PROTOCOL_VERSION from $headerPath" }
  return [int]$value.Groups[1].Value
}

function Assert-NetplaySource([string]$MeleeDir) {
  [void](Get-NetplayProtocol -MeleeDir $MeleeDir)
}

function Assert-NetplayMetadata([string]$Text, [string]$MeleeDir = '') {
  $protocol = Get-NetplayProtocol -MeleeDir $MeleeDir
  $matches = [regex]::Matches($Text, '(?m)^netplay_protocol\s+(\d+)\s*$')
  if ($matches.Count -ne 1 -or [int]$matches[0].Groups[1].Value -ne $protocol) {
    throw "version.txt must declare netplay_protocol $protocol exactly once; repackage this release."
  }
}
