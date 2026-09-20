# Run every scene in the play-test queue back to back and keep each run's log.
#
# Visible by default: GD watches these runs. -OffScreen is opt-in, for a harvest that has to
# run while the machine is being used for something else.
#
#   & "<root>\_build\harvest.ps1"            everything
#   & "<root>\_build\harvest.ps1" -Only wolf just the scenes whose tag matches
param([string]$Only = "", [int]$Seconds = 22, [switch]$Visible)
$ErrorActionPreference = "Continue"
$build = $PSScriptRoot
$out   = Join-Path $build "crashlogs"
New-Item -ItemType Directory -Force -Path $out | Out-Null

# tag, disc, scene. The comment on each says what a PASS would prove.
$queue = @(
  @("wolf",      "akaneia", "mode=vs;p1=ck:34/c0/hu;p2=ck:2/c0/cpu1"),      # tail-call / ftParts
  @("diddy",     "akaneia", "mode=vs;p1=ck:35/c0/hu;p2=ck:2/c0/cpu1"),
  @("charizard", "akaneia", "mode=vs;p1=ck:36/c0/hu;p2=ck:2/c0/cpu1"),
  @("lucas",     "akaneia", "mode=vs;p1=ck:37/c0/hu;p2=ck:2/c0/cpu1"),
  @("sonic",     "akaneia", "mode=vs;p1=ck:38/c0/hu;p2=ck:2/c0/cpu1"),      # known-good control
  @("dedede",    "akaneia", "mode=vs;p1=ck:39/c0/hu;p2=ck:2/c0/cpu1"),
  @("tails",     "akaneia", "mode=vs;p1=ck:40/c0/hu;p2=ck:2/c0/cpu1"),
  @("fox-c45",   "akaneia", "mode=vs;p1=ck:2/c4/hu;p2=ck:2/c5/cpu1"),       # the costume-table fix
  @("purin-c56", "akaneia", "mode=vs;p1=ck:15/c5/hu;p2=ck:15/c6/cpu1"),     # hat path, never run
  @("gw-c45",    "akaneia", "mode=vs;p1=ck:3/c4/hu;p2=ck:3/c5/cpu1"),       # visual only
  @("kirby-dk",  "akaneia", "mode=vs;p1=ck:4/c6/hu;p2=ck:1/c0/cpu1"),       # ftKb copy table
  @("spread",    "akaneia", "mode=vs;p1=ck:0/c6/hu;p2=ck:17/c7/cpu1"),      # 8-costume fighters
  @("refuse-99", "akaneia", "mode=vs;p1=ck:2/c99/hu;p2=ck:2/c0/cpu1"),      # must be refused at parse
  @("refuse-9",  "akaneia", "mode=vs;p1=ck:2/c9/hu;p2=ck:2/c0/cpu1"),       # must fall back to 0
  @("vanilla",   "vanilla", "mode=vs;p1=ck:2/c0/hu;p2=ck:1/c0/cpu1"),       # retail path unchanged
  @("ace-boot",  "ace",     ""),                                            # ACE reaches the CSS
  @("metalsonic","ace",     "mode=vs;p1=ck:41/c0/hu;p2=ck:2/c0/cpu1")       # GObjProc_QueueProc
)

$rows = @()
foreach ($q in $queue) {
  $tag, $disc, $scene = $q
  if ($Only -and $tag -notlike "*$Only*") { continue }
  Write-Output "=== $tag ($disc)"
  $args = @{ Disc = $disc; Tag = "h-$tag"; Seconds = $Seconds; CaptureAt = @([int]($Seconds - 4)); OffScreen = (-not $Visible) }
  if ($scene) { $args["Scene"] = $scene }
  $res = & (Join-Path $build "selftest.ps1") @args 2>&1
  $res | Select-String -Pattern 'alive at end|faults/asserts|frames advanced|RESULT|FATAL|ACCESS_VIOL' |
    ForEach-Object { Write-Output ("    " + $_.Line.Trim()) }
  $log = Join-Path $build "runs\h-$tag\melee-pc.log"
  if (Test-Path $log) { Copy-Item $log (Join-Path $out "$tag.log") -Force }
  $png = Get-ChildItem (Join-Path $build "runs\h-$tag") -Filter *.png -ErrorAction SilentlyContinue
  foreach ($p in $png) { Copy-Item $p.FullName (Join-Path $out "$tag-$($p.Name)") -Force }
  $verdict = if ($res -match "RESULT: OK") { "OK" } else { "PROBLEM" }
  $fatal = ($res | Select-String -Pattern 'FATAL.*' | Select-Object -First 1)
  $rows += [pscustomobject]@{ tag = $tag; disc = $disc; result = $verdict; fault = if ($fatal) { $fatal.Line.Trim() } else { "" } }
}

Write-Output ""
$rows | Format-Table -AutoSize | Out-String -Width 200 | Write-Output
$rows | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $out "summary.json")
Write-Output ("logs: " + $out)
