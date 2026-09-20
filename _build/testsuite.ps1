# The moveset/stage sweep.
#
#   & "_build\testsuite.ps1"                  everything, both discs
#   & "_build\testsuite.ps1" -Visible         on the main desktop, so it can be watched
#   & "_build\testsuite.ps1" -Mode movesets   fighters only   (-Mode stages for the stage pass)
#   & "_build\testsuite.ps1" -Unit specials   one move type across every fighter
#   & "_build\testsuite.ps1" -From 12         resume at index 12
#   & "_build\testsuite.ps1" -Plan            print the plan and run nothing
#
# THREE THINGS MAKE THIS CHEAP ENOUGH TO RUN OFTEN:
#
# 1. FOUR FIGHTERS PER MATCH. shim_pad.c broadcasts the pad script to every channel in
#    MELEE_PAD_CHANNELS, so one run tests four fighters at once - a 4x cut, and it exercises what
#    a solo run never does: four fighters allocating articles, effects and item slots together.
# 2. ONE MOVE TYPE PER RUN. A single all-in-one script is all-or-nothing - Diddy died entering a
#    special and took the aerials and everything after it down with him, leaving them untested for
#    that fighter. Seven short units mean a fighter that cannot do specials still gets the rest.
# 3. A DIFFERENT STAGE EVERY RUN. Stage coverage rides along with the moveset pass instead of
#    costing a run each, and whatever stages are left over get a short pass of their own.
#
# Every run carries the motion oracle (MELEE_LOG_MOTION). It is the only honest answer to "did
# that input actually produce a move?" - before it existed, a fighter that performed 33 actions
# and one that stood still for 48 seconds both finished with no fault and both were reported OK.
param(
  [ValidateSet("all", "movesets", "stages")] [string]$Mode = "all",
  [ValidateSet("both", "akaneia", "ace")]    [string]$Disc = "both",
  [string]$Unit = "",
  [int]$From = 0,
  [switch]$Plan,
  [switch]$Visible
)
$ErrorActionPreference = "Continue"
$build = $PSScriptRoot
$out   = Join-Path $build "suite"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$padDir = Join-Path $build "pads"
if (-not (Test-Path (Join-Path $padDir "unit_specials.txt"))) {
  python (Join-Path $build "gen_pad_units.py") $padDir --lead 300 | Out-Null
}
$unitNames = @(Get-ChildItem $padDir -Filter "unit_*.txt" |
                Where-Object { $_.Name -notlike "*.map.txt" } |
                ForEach-Object { $_.BaseName -replace "^unit_", "" } | Sort-Object)
if ($Unit) { $unitNames = @($unitNames | Where-Object { $_ -like "*$Unit*" }) }

$maps = @{}
foreach ($u in $unitNames) {
  $rows = @()
  foreach ($l in (Get-Content (Join-Path $padDir "unit_$u.txt.map.txt") -ErrorAction SilentlyContinue)) {
    if ($l -match "^\s*(\d+)\s+(\d+)\s+(.+)$") {
      $rows += [pscustomobject]@{ a = [int]$Matches[1]; b = [int]$Matches[2]; label = $Matches[3].Trim() }
    }
  }
  $maps[$u] = $rows
}
function ActionAt($unit, [int]$frame) {
  foreach ($m in $maps[$unit]) { if ($frame -ge $m.a -and $frame -lt $m.b) { return $m.label } }
  if ($maps[$unit].Count -and $frame -ge $maps[$unit][-1].b) { return "after the last action" }
  return ""
}
function UnitSeconds($u) {
  $f = 0
  foreach ($l in (Get-Content (Join-Path $padDir "unit_$u.txt"))) {
    if ($l -match "^\s*(\d+)\s+[0-9A-Fa-f]{4}\s") { $f += [int]$Matches[1] }
  }
  return [int][math]::Ceiling($f / 60.0) + 8
}

# Counts come from each disc's OWN boot log. Akaneia has 7 added fighters and 313 externals, ACE
# 31 and 372; sizing one off the other is the mistake this port keeps repeating.
function DiscCounts($disc) {
  $probe = Join-Path $build "runs\probe-$disc\melee-pc.log"
  if (-not (Test-Path $probe)) {
    & (Join-Path $build "selftest.ps1") -Disc $disc -Tag "probe-$disc" -Seconds 14 `
        -CaptureAt @() -OffScreen:(-not $Visible) | Out-Null
  }
  $fk = 0; $st = 0
  foreach ($l in (Get-Content $probe -ErrorAction SilentlyContinue)) {
    if ($l -match "m-ex fighter kinds from MxDt\.dat \(kinds (\d+)\.\.(\d+)\)") { $fk = [int]$Matches[2] - [int]$Matches[1] + 1 }
    if ($l -match "stage tables ready: (\d+) internal, (\d+) external")          { $st = [int]$Matches[2] }
  }
  return @{ fighters = $fk; externals = $st }
}

$discs = if ($Disc -eq "both") { @("akaneia", "ace") } else { @($Disc) }
$runs = @()
foreach ($d in $discs) {
  $c = DiscCounts $d
  # Added fighters are the m-ex slots: ChKind_Mex0 = 0x22 = 34, contiguous. Added stages are
  # EXTERNAL 288 + k (external 288+k -> internal 71+k; _research/mex-stages.md).
  $kinds  = @(34..(34 + $c.fighters - 1))
  $stages = @(288..($c.externals - 1))
  Write-Output ("{0}: {1} added fighters (ck {2}..{3}), {4} added stages (ext {5}..{6})" -f
                $d, $c.fighters, $kinds[0], $kinds[-1], $stages.Count, $stages[0], $stages[-1])

  $si = 0
  $used = @{}
  if ($Mode -ne "stages") {
    for ($g = 0; $g -lt $kinds.Count; $g += 4) {
      $grp = @($kinds[$g..([math]::Min($g + 3, $kinds.Count - 1))])
      $ps = @()
      for ($i = 0; $i -lt $grp.Count; $i++) { $ps += ("p{0}=ck:{1}/c0/hu" -f ($i + 1), $grp[$i]) }
      $chans = -join (0..($grp.Count - 1))
      foreach ($u in $unitNames) {
        $stg = $stages[$si % $stages.Count]; $si++
        $used[$stg] = $true
        $secs = UnitSeconds $u
        $runs += [pscustomobject]@{
          kind = "moveset"; disc = $d; unit = $u; isRetry = $false
          tag = "$d-ck$($grp[0])-$u"
          scene = ("mode=vs;{0};stage=ext:{1}" -f ($ps -join ";"), $stg)
          pad = (Join-Path $padDir "unit_$u.txt"); chans = $chans; kinds = $grp; stage = $stg
          secs = $secs; at = @($secs - 5) }
      }
    }
  }
  if ($Mode -ne "movesets") {
    foreach ($e in $stages) {
      if ($used[$e]) { continue }
      $runs += [pscustomobject]@{
        kind = "stage"; disc = $d; unit = ""; isRetry = $false
        tag = "$d-ext$e"; scene = "mode=training;p1=fox/c0/hu;stage=ext:$e"
        pad = ""; chans = "0"; kinds = @(); stage = $e; secs = 18; at = @(14) }
    }
  }
}

Write-Output ("plan: {0} runs ({1} moveset, {2} stage), about {3:n0} minutes" -f $runs.Count,
  ($runs | Where-Object { $_.kind -eq "moveset" }).Count,
  ($runs | Where-Object { $_.kind -eq "stage" }).Count,
  (($runs | Measure-Object -Property secs -Sum).Sum / 60.0 + $runs.Count * 0.12))
if ($Plan) {
  $runs | Select-Object -First 16 | Format-Table -AutoSize tag, unit, chans, secs, scene |
    Out-String -Width 200 | Write-Output
  exit 0
}

$results = @()
for ($i = $From; $i -lt $runs.Count; $i++) {
  $p = $runs[$i]
  Write-Output ("[{0}/{1}] {2}  {3}" -f ($i + 1), $runs.Count, $p.tag, $p.scene)
  $env:MELEE_LOG_MOTION   = "1"
  $env:MELEE_PAD_CHANNELS = $p.chans
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

  # The motion oracle, per player: how many distinct action states each fighter actually entered.
  # A moveset run where a player shows almost none did not test that fighter, whatever else says.
  $perPlayer = @{}
  foreach ($l in (Get-Content $log -ErrorAction SilentlyContinue)) {
    if ($l -match "^motion: p(\d+) kind=(\d+) \d+ -> (\d+)") {
      $k = "p$($Matches[1])"
      if (-not $perPlayer[$k]) { $perPlayer[$k] = @{} }
      $perPlayer[$k][$Matches[3]] = $true
    }
  }
  $states = ($perPlayer.Keys | Sort-Object | ForEach-Object { "$_=$($perPlayer[$_].Count)" }) -join " "

  $ok = $text -match "RESULT: OK"
  $fault = ""
  $m = [regex]::Match($text, "(?m)^\s*(gw: FATAL.*|ppc: .*|.*unimplemented opcode.*)$")
  if ($m.Success) { $fault = $m.Groups[1].Value.Trim() }
  $lastFrame = 0
  if ($text -match "frames advanced\s*:\s*\d+\s*->\s*(\d+)") { $lastFrame = [int]$Matches[1] }
  $action = if ($p.kind -eq "moveset" -and -not $ok) { ActionAt $p.unit $lastFrame } else { "" }

  $results += [pscustomobject]@{ idx = $i; tag = $p.tag; unit = $p.unit
                                 result = $(if ($ok) { "OK" } else { "PROBLEM" })
                                 states = $states; frame = $lastFrame; action = $action; fault = $fault }
  Write-Output ("      {0}  states[{1}]  frame {2}  {3} {4}" -f $results[-1].result, $states, $lastFrame, $action, $fault)
  # A group run that fails tells you something broke - not WHICH of the four fighters, or whether
  # it was the stage at all. Run 1 of the first sweep died at grTSeak_80223908+0xE8 before a
  # single fighter loaded: the stage, with four healthy fighters blamed for it.
  #
  # So on a group failure, bisect: re-run the same unit for each fighter ALONE on Final
  # Destination. FD is the control - it is retail and every fighter has already reached it. If
  # every solo run then passes, the stage is the culprit and the fighters are fine; if one fails,
  # that fighter owns the crash. The retries are appended to the queue rather than run inline so
  # -From still resumes cleanly, and they are never themselves bisected.
  if ($p.kind -eq "moveset" -and -not $ok -and $p.kinds.Count -gt 1 -and -not $p.isRetry) {
    Write-Output ("      bisecting: {0} solo runs on fd" -f $p.kinds.Count)
    foreach ($k in $p.kinds) {
      $runs += [pscustomobject]@{
        kind = "moveset"; disc = $p.disc; unit = $p.unit; isRetry = $true
        tag = "$($p.disc)-ck$k-$($p.unit)-solo"
        scene = "mode=vs;p1=ck:$k/c0/hu;p2=ck:2/c0/cpu1;stage=fd"
        pad = $p.pad; chans = "0"; kinds = @($k); stage = -1
        secs = $p.secs; at = $p.at }
    }
    $runs += [pscustomobject]@{
      kind = "stage"; disc = $p.disc; unit = ""; isRetry = $true
      tag = "$($p.disc)-ext$($p.stage)-solo"
      scene = "mode=training;p1=fox/c0/hu;stage=ext:$($p.stage)"
      pad = ""; chans = "0"; kinds = @(); stage = $p.stage; secs = 18; at = @(14) }
  }

  $results | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 (Join-Path $out "summary.json")
}

Write-Output ""
Write-Output "==== failures ===="
$results | Where-Object { $_.result -ne "OK" } |
  Format-Table -AutoSize idx, tag, unit, frame, action, fault | Out-String -Width 220 | Write-Output
Write-Output ("{0} of {1} OK.  logs: {2}" -f ($results | Where-Object { $_.result -eq "OK" }).Count, $results.Count, $out)
