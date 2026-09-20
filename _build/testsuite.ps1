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
  # ON THE MAIN DESKTOP ALWAYS. GD watches these runs; a sweep nobody can see is a sweep
  # whose mistakes nobody catches - the four-identical-windows confusion that produced the
  # run label was only noticed because the runs were visible. -OffScreen is opt-in now.
  [switch]$OffScreen,
  [ValidateRange(1,8)] [int]$Parallel = 4
)
$ErrorActionPreference = "Continue"
$build = $PSScriptRoot
$out   = Join-Path $build "suite"
New-Item -ItemType Directory -Force -Path $out | Out-Null

# ONE SWEEP AT A TIME, ENFORCED.
#
# Two sweeps ran concurrently for two hours because one was believed stopped and was not. They
# use the same tags, so they shared sandbox directories, overwrote the same summary.json, killed
# each other's game processes (the per-sandbox kill matches when the sandbox IS the same) and
# wrote each other's pipeline caches. The result was a summary full of runs that failed for no
# reason anyone could name. Nothing in the tooling objected.
$lockFile = Join-Path $out "sweep.lock"
if (Test-Path $lockFile) {
  $held = Get-Content $lockFile -ErrorAction SilentlyContinue
  $pidLine = ($held | Where-Object { $_ -match "^pid=(\d+)" })
  $stale = $true
  if ($pidLine -and ($pidLine -match "^pid=(\d+)")) {
    $stale = -not (Get-Process -Id ([int]$Matches[1]) -ErrorAction SilentlyContinue)
  }
  if (-not $stale) {
    Write-Output "REFUSING TO START: another sweep is already running."
    $held | ForEach-Object { Write-Output ("  " + $_) }
    Write-Output "Stop it first, or delete $lockFile if you are certain it is dead."
    exit 2
  }
  Write-Output "note: clearing a stale sweep lock from a process that is gone"
}
Set-Content -Encoding utf8 $lockFile @("pid=$PID", "started=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
try {

# SNAPSHOT THE BUILD ONCE, AND TEST ONLY THAT.
#
# selftest.ps1 copies _build\melee-pc.exe per run, so a rebuild part-way through a sweep silently
# splits the results: earlier runs tested one binary, later runs another, and the summary says
# nothing about it. That happened twice in one night - both times while fixing bugs the sweep had
# just found, which is exactly when a rebuild is most likely.
#
# So the sweep takes its own immutable copy up front and points every run at it with -ExeDir.
# Rebuilding mid-sweep is now harmless, and build.txt records what was actually under test.
$snapshot = Join-Path $out "build"
New-Item -ItemType Directory -Force -Path $snapshot | Out-Null
foreach ($f in @("melee-pc.exe", "melee-pc.map", "SDL3.dll", "webgpu_dawn.dll")) {
  $src = Join-Path $build $f
  if (Test-Path $src) { Copy-Item $src $snapshot -Force }
}
$exeHash = (Get-FileHash (Join-Path $snapshot "melee-pc.exe") -Algorithm SHA256).Hash.Substring(0, 16)
$stamp = "{0}  sha256:{1}  {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $exeHash,
         (git -C $PSScriptRoot\..\melee rev-parse --short HEAD 2>$null)
Set-Content -Encoding utf8 (Join-Path $out "build.txt") $stamp
Write-Output ("build under test: " + $stamp)

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
        -CaptureAt @() -OffScreen:$OffScreen | Out-Null
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

  # STAGES FIRST, THEN MOVESETS ON STAGES THAT SURVIVED.
  #
  # Rotating an untested stage into every moveset run was the single biggest cost in the sweep:
  # most added stages are still broken, so most GROUP runs died on the stage, and each one queued
  # five bisect retries to prove the fighters were innocent. 109 planned runs became 410.
  #
  # Testing every stage first with Fox costs 109 short runs and yields the healthy set. The
  # moveset runs then rotate over THAT, so a moveset failure means a fighter - which is the whole
  # point of the exercise - and the bisect tail all but disappears. Stage variety is kept; only
  # the broken ones are left out, and they are reported in their own right by the stage pass.
  if ($Mode -ne "movesets") {
    foreach ($e in $stages) {
      $runs += [pscustomobject]@{
        kind = "stage"; disc = $d; unit = ""; isRetry = $false; phase = 1
        tag = "$d-ext$e"; scene = "mode=training;p1=fox/c0/hu;stage=ext:$e"
        pad = ""; chans = "0"; kinds = @(); stage = $e; secs = 18; at = @(14) }
    }
  }
  if ($Mode -ne "stages") {
    for ($g = 0; $g -lt $kinds.Count; $g += 4) {
      $grp = @($kinds[$g..([math]::Min($g + 3, $kinds.Count - 1))])
      $ps = @()
      for ($i = 0; $i -lt $grp.Count; $i++) { $ps += ("p{0}=ck:{1}/c0/hu" -f ($i + 1), $grp[$i]) }
      $chans = -join (0..($grp.Count - 1))
      foreach ($u in $unitNames) {
        $secs = UnitSeconds $u
        # stage is resolved at RUN time from the healthy set; -1 means "pick then".
        $runs += [pscustomobject]@{
          kind = "moveset"; disc = $d; unit = $u; isRetry = $false; phase = 2
          tag = "$d-ck$($grp[0])-$u"
          scene = ""
          pad = (Join-Path $padDir "unit_$u.txt"); chans = $chans; kinds = $grp; stage = -1
          players = ($ps -join ";")
          secs = $secs; at = @($secs - 5) }
      }
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

# ---- execution -------------------------------------------------------------------------------
#
# Runs go out in WAVES of -Parallel. Every shared resource a run touches is now per-sandbox - the
# exe, the map, the DLLs, the pipeline cache, the memory card, the log - so N games at once are
# independent, and this box has 20 cores against one game's appetite for about one and a half.
# A run is ~26s wall clock of which only ~18s is the game, so the serial sweep spent most of its
# time waiting; four at a time turns 78 minutes into about 20.
#
# Phase 1 (stages) must finish before phase 2 (movesets), because phase 2 picks its stage from
# whatever phase 1 proved healthy. Within a phase there are no dependencies at all.
# Scale the in-game spin watchdog with the load. It calls a spin after N seconds at the same
# PC, which is right for one game alone and wrong for four sharing the CPU - a stage that
# loads fine solo reported "spinning" at frame 240 under -Parallel 4. A false fault in an
# unattended sweep is worse than no check, so give it room proportional to the contention.
$env:MELEE_SPIN_SECONDS = [string](4 * [math]::Max(1, $Parallel))
Write-Host ("spin watchdog: {0}s (scaled for -Parallel {1})" -f $env:MELEE_SPIN_SECONDS, $Parallel)

$results = @()
$stageCursor = 0

function Complete-Run($p, $text) {
  $dir = Join-Path $build "runs\s-$($p.tag)"
  $log = Join-Path $dir "melee-pc.log"
  if (Test-Path $log) { Copy-Item $log (Join-Path $out "$($p.tag).log") -Force }
  foreach ($png in (Get-ChildItem $dir -Filter *.png -ErrorAction SilentlyContinue)) {
    Copy-Item $png.FullName (Join-Path $out "$($p.tag)-$($png.Name)") -Force
  }
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
  # The LOG is the primary record; selftest's console output prints only the first three matches
  # and is wrapped, which is how 52 access violations once recorded an empty reason.
  $fault = ""
  if (Test-Path $log) {
    $hit = Select-String -Path $log -Pattern ("gw: FATAL|^ppc: |unimplemented opcode|" +
            "assertion .* failed|access violation|panic|spinning|outside blob code range|" +
            "resolver returned NULL|unmapped vtx attr|aurora fatal|" +
            "is EMPTY \(no state table\)") | Select-Object -First 1
    if ($hit) { $fault = $hit.Line.Trim() }
    if (-not $fault) {
      $asrt = Select-String -Path $log -Pattern "in (src/[\w/]+\.c) on line (\d+)" |
               Select-Object -First 1
      if ($asrt) { $fault = "assert " + $asrt.Matches[0].Groups[1].Value + ":" +
                            $asrt.Matches[0].Groups[2].Value }
    }
  }
  $lastFrame = 0
  if ($text -match "frames advanced\s*:\s*\d+\s*->\s*(\d+)") { $lastFrame = [int]$Matches[1] }
  $action = if ($p.kind -eq "moveset" -and -not $ok) { ActionAt $p.unit $lastFrame } else { "" }
  $row = [pscustomobject]@{ tag = $p.tag; unit = $p.unit; kind = $p.kind; disc = $p.disc
                            stage = $p.stage; result = $(if ($ok) { "OK" } else { "PROBLEM" })
                            states = $states; frame = $lastFrame; action = $action; fault = $fault }
  # Write-HOST, not Write-Output: anything written to the pipeline inside a function becomes
  # part of its RETURN VALUE, so these progress lines were being collected as results and a
  # 25-run pass reported "9 of 75 OK".
  Write-Host ("      {0,-7} {1,-34} states[{2}] {3} {4}" -f $row.result, $p.tag, $states, $action, $fault)
  return $row
}

function Invoke-Wave($batch) {
  $jobs = @()
  foreach ($p in $batch) {
    Write-Host ("  -> {0}  {1}" -f $p.tag, $p.scene)
    $jobs += @{ p = $p; job = (Start-Job -ScriptBlock {
      param($st, $a, $chans)
      $env:MELEE_LOG_MOTION = "1"
      $env:MELEE_PAD_CHANNELS = $chans
      & $st @a 2>&1 | Out-String
    } -ArgumentList (Join-Path $build "selftest.ps1"), $p.args, $p.chans) }
  }
  $rows = @()
  foreach ($j in $jobs) {
    $text = (Receive-Job $j.job -Wait -AutoRemoveJob) -join "`n"
    $rows += Complete-Run $j.p $text
  }
  return $rows
}

function Run-Phase($list, $label) {
  if ($list.Count -eq 0) { return }
  Write-Host ""
  Write-Host ("==== {0}: {1} runs, {2} at a time ====" -f $label, $list.Count, $Parallel)
  for ($i = 0; $i -lt $list.Count; $i += $Parallel) {
    $batch = @($list[$i..([math]::Min($i + $Parallel - 1, $list.Count - 1))])
    foreach ($p in $batch) {
      if ($p.kind -eq "moveset" -and $p.stage -eq -1) {
        $healthy = @($script:results | Where-Object { $_.kind -eq "stage" -and $_.result -eq "OK" -and
                                                      $_.disc -eq $p.disc } | ForEach-Object { $_.stage })
        if ($healthy.Count -gt 0) {
          $p.stage = $healthy[$script:stageCursor % $healthy.Count]; $script:stageCursor++
          $p.scene = ("mode=vs;{0};stage=ext:{1}" -f $p.players, $p.stage)
        } else {
          $p.scene = ("mode=vs;{0};stage=fd" -f $p.players)
        }
      }
      # A caption the watcher can read at a glance: which disc, what is being tested, where, and
      # with whom. Two runs on the same stage testing different move types are indistinguishable
      # without it, which reads as a repeated test.
      $who = if ($p.kinds.Count) { "ck " + ($p.kinds -join ",") } else { "fox" }
      $what = if ($p.unit) { $p.unit } else { "stage load" }
      $where = if ($p.stage -ge 0) { "ext:$($p.stage)" } else { "fd" }
      $label = "{0}  |  {1}  |  {2}  |  {3}" -f $p.disc.ToUpper(), $what, $where, $who
      $p | Add-Member -NotePropertyName args -NotePropertyValue @{
        Scene = $p.scene; Disc = $p.disc; Tag = "s-$($p.tag)"; Seconds = $p.secs
        CaptureAt = $p.at; OffScreen = $OffScreen; ExeDir = $snapshot
        Label = $label; Pad = $p.pad } -Force
      if (-not $p.pad) { $p.args.Remove("Pad") }
    }
    Write-Host ("[{0}-{1} / {2}]" -f ($i + 1), [math]::Min($i + $Parallel, $list.Count), $list.Count)
    $script:results += Invoke-Wave $batch
    $script:results | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 (Join-Path $out "summary.json")
  }
}

Run-Phase @($runs | Where-Object { $_.phase -eq 1 } | Select-Object -Skip $From) "phase 1 - stages"
Run-Phase @($runs | Where-Object { $_.phase -eq 2 }) "phase 2 - movesets"

Write-Output ""
Write-Output "==== failures ===="
$results | Where-Object { $_.result -ne "OK" } |
  Format-Table -AutoSize tag, unit, stage, frame, action, fault | Out-String -Width 220 | Write-Output
Write-Output ("{0} of {1} OK.  logs: {2}" -f ($results | Where-Object { $_.result -eq "OK" }).Count, $results.Count, $out)

} finally {
  Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
}
