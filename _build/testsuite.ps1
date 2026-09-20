# The moveset/stage sweep. Drives every ADDED fighter through its whole moveset on Final
# Destination, and loads every ADDED stage with Fox, keeping a log and a frame for each.
#
#   & "_build\testsuite.ps1"                       everything, both discs
#   & "_build\testsuite.ps1" -Mode movesets        fighters only
#   & "_build\testsuite.ps1" -Mode stages -Disc ace
#   & "_build\testsuite.ps1" -From 12              resume at index 12 of the plan
#   & "_build\testsuite.ps1" -Plan                 print the plan and exit, running nothing
#
#   & "_build	estsuite.ps1" -Visible              run ON THE MAIN DESKTOP, so it can be watched
#
# Off-screen by default, because it is an hour and a half of unattended runs. -Visible puts every
# window on the main desktop instead, so the whole suite becomes a thing you can sit and watch.
#
# WHY A FRAME MAP: a pad script cannot log, so a crash would otherwise say only "Dedede died".
# pad_moveset.txt.map.txt gives frame-range -> action, and every run's retrace= counter is in its
# log, so this script converts the last retrace into the action that was executing. That is the
# difference between "Dedede is broken" and "Dedede's double jump is broken".
param(
  [ValidateSet("all", "movesets", "stages")] [string]$Mode = "all",
  [ValidateSet("both", "akaneia", "ace")]    [string]$Disc = "both",
  [int]$From = 0,
  [switch]$Plan,
  [switch]$Visible
)
$ErrorActionPreference = "Continue"
$build = $PSScriptRoot
$root  = Split-Path -Parent $build
$out   = Join-Path $build "suite"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$pad = Join-Path $build "pad_moveset.txt"
if (-not (Test-Path $pad)) { python (Join-Path $build "gen_pad_moveset.py") $pad --lead 300 | Out-Null }

# frame -> action, read back from the generator's map file.
$map = @()
foreach ($l in (Get-Content ($pad + ".map.txt") -ErrorAction SilentlyContinue)) {
  if ($l -match '^\s*(\d+)\s+(\d+)\s+(.+)$') {
    $map += [pscustomobject]@{ a = [int]$Matches[1]; b = [int]$Matches[2]; label = $Matches[3].Trim() }
  }
}
function ActionAt([int]$frame) {
  foreach ($m in $map) { if ($frame -ge $m.a -and $frame -lt $m.b) { return $m.label } }
  if ($map.Count -and $frame -ge $map[-1].b) { return "after the last action" }
  return ""
}

# ---- the plan -------------------------------------------------------------------------------
# Added fighters are the m-ex slots: ChKind_Mex0 = 0x22 = 34, contiguous from there. Added stages
# are EXTERNAL 288 + k (external 288+k -> internal 71+k on both discs; _research/mex-stages.md).
# Both counts come from the disc's own boot log rather than being hardcoded - ACE and Akaneia
# differ, and sizing one off the other is the mistake this port keeps making.
function DiscCounts($disc) {
  $probe = Join-Path $build "runs\probe-$disc\melee-pc.log"
  if (-not (Test-Path $probe)) {
    & (Join-Path $build "selftest.ps1") -Disc $disc -Tag "probe-$disc" -Seconds 14 -CaptureAt @() -OffScreen:(-not $Visible) | Out-Null
  }
  $log = Get-Content $probe -ErrorAction SilentlyContinue
  $fk = 0; $st = 0
  foreach ($l in $log) {
    if ($l -match 'm-ex fighter kinds from MxDt\.dat \(kinds (\d+)\.\.(\d+)\)') { $fk = [int]$Matches[2] - [int]$Matches[1] + 1 }
    if ($l -match 'stage tables ready: (\d+) internal, (\d+) external')          { $st = [int]$Matches[2] }
  }
  return @{ fighters = $fk; externals = $st }
}

$discs = if ($Disc -eq "both") { @("akaneia", "ace") } else { @($Disc) }
$runs = @()
foreach ($d in $discs) {
  $c = DiscCounts $d
  Write-Output ("{0}: {1} added fighters, {2} external stages" -f $d, $c.fighters, $c.externals)
  if ($Mode -ne "stages") {
    for ($i = 0; $i -lt $c.fighters; $i++) {
      $ck = 34 + $i
      $runs += [pscustomobject]@{ kind = "moveset"; disc = $d; tag = "$d-ck$ck"
                                  scene = "mode=training;p1=ck:$ck/c0/hu;stage=fd"
                                  pad = $pad; secs = 58; at = @(20, 40, 54) }
    }
  }
  if ($Mode -ne "movesets") {
    for ($e = 288; $e -lt $c.externals; $e++) {
      $runs += [pscustomobject]@{ kind = "stage"; disc = $d; tag = "$d-ext$e"
                                  scene = "mode=training;p1=fox/c0/hu;stage=ext:$e"
                                  pad = ""; secs = 20; at = @(15) }
    }
  }
}

Write-Output ("plan: {0} runs, about {1:n0} minutes" -f $runs.Count,
              (($runs | Measure-Object -Property secs -Sum).Sum / 60.0 + $runs.Count * 0.12))
if ($Plan) { $runs | Format-Table -AutoSize | Out-String -Width 200 | Write-Output; exit 0 }

# ---- run ------------------------------------------------------------------------------------
$results = @()
for ($i = $From; $i -lt $runs.Count; $i++) {
  $p = $runs[$i]
  Write-Output ("[{0}/{1}] {2}  {3}" -f ($i + 1), $runs.Count, $p.tag, $p.scene)
  $a = @{ Scene = $p.scene; Disc = $p.disc; Tag = "s-$($p.tag)"; Seconds = $p.secs
          CaptureAt = $p.at; OffScreen = (-not $Visible) }
  if ($p.pad) { $a["Pad"] = $p.pad }
  $res = & (Join-Path $build "selftest.ps1") @a 2>&1
  $text = $res | Out-String

  $dir = Join-Path $build "runs\s-$($p.tag)"
  $log = Join-Path $dir "melee-pc.log"
  if (Test-Path $log) { Copy-Item $log (Join-Path $out "$($p.tag).log") -Force }
  foreach ($png in (Get-ChildItem $dir -Filter *.png -ErrorAction SilentlyContinue)) {
    Copy-Item $png.FullName (Join-Path $out "$($p.tag)-$($png.Name)") -Force
  }

  $ok = $text -match "RESULT: OK"
  $fault = ""
  $m = [regex]::Match($text, '(?m)^\s*(gw: FATAL.*|ppc: .*|.*unimplemented opcode.*)$')
  if ($m.Success) { $fault = $m.Groups[1].Value.Trim() }
  $lastFrame = 0
  if ($text -match 'frames advanced\s*:\s*\d+\s*->\s*(\d+)') { $lastFrame = [int]$Matches[1] }
  $action = if ($p.kind -eq "moveset" -and -not $ok) { ActionAt $lastFrame } else { "" }

  $results += [pscustomobject]@{ idx = $i; tag = $p.tag; kind = $p.kind; result = $(if ($ok) { "OK" } else { "PROBLEM" })
                              lastFrame = $lastFrame; action = $action; fault = $fault }
  Write-Output ("      {0}  frame {1}  {2} {3}" -f $results[-1].result, $lastFrame, $action, $fault)
  $results | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 (Join-Path $out "summary.json")
}

Write-Output ""
Write-Output "==== failures ===="
$results | Where-Object { $_.result -ne "OK" } | Format-Table -AutoSize idx, tag, kind, lastFrame, action, fault |
  Out-String -Width 220 | Write-Output
Write-Output ("{0} of {1} OK.  logs: {2}" -f ($results | Where-Object { $_.result -eq "OK" }).Count, $results.Count, $out)
