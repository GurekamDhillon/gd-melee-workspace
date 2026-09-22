# netsim.ps1 - set the simulated network conditions for netplay_local.ps1's two windows, live.
# Both copies re-read runs\netsim.txt every second, so this takes effect mid-match; each window's
# title shows what is in force.
#
#   powershell -File _build\netsim.ps1 bad
#   powershell -File _build\netsim.ps1 "lag=80,jitter=20,loss=3"
#   powershell -File _build\netsim.ps1 off
#
# Values are per direction (each copy delays what it sends), so the round trip is twice the lag.
param([Parameter(Position = 0)][string]$Setting = "off")

$presets = [ordered]@{
  "off"   = "off"                                                   # loopback as is (~0 ms)
  "lan"   = "lag=2,jitter=1"                                        # same house, wired
  "good"  = "lag=15,jitter=3"                                       # ~30 ms ping, clean
  "wifi"  = "lag=20,jitter=12,loss=2,burst=3"                       # ~40 ms, jittery, bursty loss
  "far"   = "lag=45,jitter=5,loss=1"                                # ~90 ms, cross-country
  "bad"   = "lag=60,jitter=20,loss=5,burst=2,dup=1"                 # ~120 ms and unreliable
  "awful" = "lag=100,jitter=40,loss=10,burst=3,dup=2,spike=5000:300" # ~200 ms, spikes every 5 s
}

$value = if ($presets.Contains($Setting)) { $presets[$Setting] } else { $Setting }
$file = Join-Path $PSScriptRoot "runs\netsim.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $file) | Out-Null
Set-Content -Path $file -Value $value -Encoding ascii
if ($presets.Contains($Setting)) {
  Write-Output "network: $Setting ($value)"
} else {
  Write-Output "network: $value"
}
