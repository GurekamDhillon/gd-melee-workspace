# Launch a seeded scene OFF-SCREEN, drive it with a pad script, capture frames, and report.
#
#   .\selftest.ps1 -Scene "mode=vs;p1=ck:39;p2=ck:38;stage=ext:293" -Disc akaneia
#
# The window opens ON THE MAIN DESKTOP by default so it can be watched. Pass -OffScreen to park it
# at 30000,30000 with the console hidden, for running while the machine is in use; frames come from
# PrintWindow(PW_RENDERFULLCONTENT), which works either way - a separate Windows desktop does NOT
# (the process dies with STATUS_DLL_INIT_FAILED).
#
# It reports, in order: whether the process survived, whether the log shows a fault/assert/spin,
# whether frames advanced, and where the captures landed. Exit code 0 only if all four are good.
param(
  [string]$Scene = "",
  [string]$Disc = "akaneia",
  [string]$Pad = "",
  [int]$Seconds = 25,
  [int[]]$CaptureAt = @(12, 20),
  [string]$Tag = "selftest",
  [double]$Volume = 0.03,
  # VISIBLE ON THE MAIN DESKTOP BY DEFAULT - GD wants to watch these runs. -OffScreen parks the
  # window at 30000,30000 and hides the console, for when the machine is being used for something
  # else; PrintWindow still captures there.
  [switch]$OffScreen,
  # -NoMods points MELEE_MODS_DIR at an empty folder. Needed for any honest claim about a disc's
  # OWN data: the sonic mod overrides /MxDt.dat on EVERY disc, so with mods on even a vanilla run
  # has mexData and an ACE run reads Akaneia's tables.
  [switch]$NoMods,
  # -ModsDir runs against a mods folder OTHER than the shared _build/mods - e.g. a pack
  # built by tools/mex_port/make_mod_from_disc.py in _build/packs. The shared folder is
  # shared: dropping a 350 MB pack into it changes every other agent's run too.
  [string]$ModsDir = "",
  # -ExeDir runs an AGENT's build instead of the main one, so its instrumentation can be
  # exercised without merging it first.
  [string]$ExeDir = "",
  # Share ONE memory card across runs. A per-sandbox card is empty, which means the memcard
  # prompt on boot AND a character-select screen with everything still locked - and a locked
  # roster re-flows the icon grid, which is exactly the kind of thing that gets mistaken for a
  # bug. Point this elsewhere to test first-boot behaviour deliberately.
  [string]$CardPath = "",
  # Drawn on the window itself (MELEE_RUN_LABEL). With four games side by side, an
  # unlabelled window says nothing about what it is testing. Defaults to the tag.
  [string]$Label = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $root "_build"))) { $root = Split-Path -Parent $PSScriptRoot }
$build = Join-Path $root "_build"

# Disc from .env, same source as play.bat / portlib.sh.
$env:GW_ISO_VANILLA = $null; $env:GW_ISO_AKANEIA = $null; $env:GW_ISO_ACE = $null
Get-Content (Join-Path $root ".env") -ErrorAction SilentlyContinue | ForEach-Object {
  if ($_ -match '^\s*(?:export\s+)?(GW_ISO_\w+)\s*=\s*"?([^"]*)"?\s*$') {
    Set-Item -Path ("Env:" + $Matches[1]) -Value $Matches[2]
  }
}
$iso = switch ($Disc) {
  "vanilla" { $env:GW_ISO_VANILLA }
  "akaneia" { $env:GW_ISO_AKANEIA }
  "ace"     { $env:GW_ISO_ACE }
  default   { $Disc }
}
if (-not $iso) { Write-Output "FAIL: no ISO for '$Disc' - set it in $root\.env"; exit 1 }

$sandbox = Join-Path $build "runs\$Tag"
New-Item -ItemType Directory -Force -Path $sandbox | Out-Null
# KILL ONLY THIS SANDBOX'S OWN LEFTOVERS, never every melee-pc on the machine.
# A blanket Stop-Process meant two runs could not coexist: testing a fix by hand while the sweep
# was running had each one shooting the other's process, and the results looked like real crashes
# - a stage that "died mid-audio", another that "ran 360 frames then stopped". Both were just the
# other run starting. Matching on the sandbox path keeps concurrent runs independent.
Get-Process melee-pc -ErrorAction SilentlyContinue | Where-Object {
  try { $_.MainModule.FileName -like (Join-Path $sandbox "*") } catch { $false }
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
$exesrc = if ($ExeDir) { $ExeDir } else { $build }
# Copy only what actually differs. These four are 34 MB together, and a sweep re-copied all of
# them into every sandbox - roughly 15 GB of pointless I/O over a long run, on files that change
# at most once per build. Compare length and write time; that is enough to catch a rebuild and
# cheap enough to be free.
function Sync-RunFile($src, $dstDir) {
  if (-not (Test-Path $src)) { return }
  $s = Get-Item $src
  $d = Join-Path $dstDir $s.Name
  if (Test-Path $d) {
    $t = Get-Item $d
    if ($t.Length -eq $s.Length -and $t.LastWriteTimeUtc -eq $s.LastWriteTimeUtc) { return }
  }
  Copy-Item $src $d -Force
}
foreach ($f in @("melee-pc.exe", "melee-pc.map")) { Sync-RunFile (Join-Path $exesrc $f) $sandbox }
foreach ($f in @("SDL3.dll", "webgpu_dawn.dll", "initial_pipeline_cache.db", "initial_pipeline_cache.core")) { Sync-RunFile (Join-Path $build $f) $sandbox }
if ($ExeDir) { Write-Output "exe    $exesrc" }
# Start each run from an EMPTY pipeline cache. The cache is per-sandbox now, but this harness
# kills the game at the end of every run, and killing a process mid-write can leave its own
# SQLite cache corrupt - after which that sandbox fails at its first draw forever. Deleting
# it costs a few seconds of shader compilation and removes a whole class of phantom result.
# The pipeline seed (initial_pipeline_cache.db) is opened read-only, so it cannot be left corrupt
# and is kept; only the caches a run writes are cleared.
Get-ChildItem $sandbox -Filter "*.db*" -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -notlike "initial_pipeline_cache.db*" } |
  Remove-Item -Force -ErrorAction SilentlyContinue
$log = Join-Path $sandbox "melee-pc.log"
Remove-Item $log -ErrorAction SilentlyContinue

if ($OffScreen) {
  $env:MELEE_WINDOW_X = "30000"
  $env:MELEE_WINDOW_Y = "30000"
} else {
  Remove-Item Env:MELEE_WINDOW_X -ErrorAction SilentlyContinue
  Remove-Item Env:MELEE_WINDOW_Y -ErrorAction SilentlyContinue
}
$env:MELEE_MODS_DIR = if ($ModsDir) { $ModsDir }
  elseif ($NoMods -or $Disc -eq "ace") { Join-Path $build "nomods" }
  else { Join-Path $build "mods" }
Write-Output "mods   $env:MELEE_MODS_DIR"
New-Item -ItemType Directory -Force -Path $env:MELEE_MODS_DIR | Out-Null
$env:MELEE_SKIP_INTRO = "1"
# A PER-SANDBOX CARD, SEEDED FROM THE SHARED UNLOCKED ONE.
#
# Sharing one card directory is what stopped runs being parallelisable: two games writing the same
# save at once is a corruption waiting to happen. But a FRESH card is not an option either - it
# boots with everything locked, which re-flows the CSS grid and produces exactly the "Fox is
# missing" class of phantom bug. So copy the unlocked card in (96 KB) and let each run own it.
if ($CardPath) {
  $env:MELEE_CARD_PATH = $CardPath
} else {
  $cardSrc = Join-Path $build $(if ($Disc -eq "ace") { "card-ace" } else { "card" })
  $cardDst = Join-Path $sandbox "card"
  if (-not (Test-Path $cardDst) -and (Test-Path $cardSrc)) {
    Copy-Item $cardSrc $cardDst -Recurse -Force
  }
  $env:MELEE_CARD_PATH = $cardDst
}
$env:MELEE_RUN_LABEL = if ($Label) { $Label } else { $Tag }
if ($Scene) { $env:MELEE_SCENE = $Scene } else { Remove-Item Env:MELEE_SCENE -ErrorAction SilentlyContinue }
if ($Pad)   { $env:MELEE_PAD_SCRIPT = $Pad } else { Remove-Item Env:MELEE_PAD_SCRIPT -ErrorAction SilentlyContinue }

Write-Output "disc   $iso"
if ($Scene) { Write-Output "scene  $Scene" }
Write-Output "log    $log"

$style = if ($OffScreen) { 'Hidden' } else { 'Normal' }
# The ISO path MUST be quoted here. Start-Process joins -ArgumentList with spaces and does NOT
# quote for you, so "C:/iso/SSBM ACE Build v2.0.0.iso" arrived as "C:/iso/SSBM" and the game ran
# with no disc - which presents as an endless "MxDt.dat not on this disc" and a card wait that
# never completes, i.e. nothing like a path bug. Akaneia has no space in its name, which is why
# only ACE ever looked broken.
$p = Start-Process -FilePath (Join-Path $sandbox "melee-pc.exe") `
      -ArgumentList '--iso', ('"' + $iso + '"') -WorkingDirectory $sandbox `
      -WindowStyle $style -PassThru

# Keep test launches quiet: these run while someone is using the machine, and an off-screen
# window is still audible. Windows remembers per-app levels by exe path, but a fresh sandbox is a
# fresh path, so set it every time. Failure here must not fail the run.
#
# BY PID, not by name: several runs go at once now, and name matching set whichever
# instance Get-Process happened to return first - so a run would quietly leave its own
# audio at full while turning a sibling down.
try {
  & (Join-Path $build "set_app_volume.ps1") -ProcessId $p.Id -Volume $Volume -TimeoutSec 20 |
    Out-Null
} catch { Write-Output "note: could not set volume ($_)" }

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class GwCap {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint f);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out R r);
  [StructLayout(LayoutKind.Sequential)] public struct R { public int L, T, Rt, B; }
}
"@
function Capture($proc, $path) {
  try {
    $proc.Refresh()
    $h = $proc.MainWindowHandle
    if ($h -eq [IntPtr]::Zero) { return $false }
    $r = New-Object GwCap+R
    [void][GwCap]::GetClientRect($h, [ref]$r)
    if ($r.Rt -le 0 -or $r.B -le 0) { return $false }
    $bmp = New-Object System.Drawing.Bitmap($r.Rt, $r.B)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    $ok = [GwCap]::PrintWindow($h, $hdc, 2)   # PW_RENDERFULLCONTENT
    $g.ReleaseHdc($hdc); $g.Dispose()
    if ($ok) { $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png) }
    $bmp.Dispose()
    return $ok
  } catch { return $false }
}

$shots = @()
for ($t = 1; $t -le $Seconds; $t++) {
  Start-Sleep -Seconds 1
  if ($CaptureAt -contains $t) {
    $png = Join-Path $sandbox ("frame_{0:d2}s.png" -f $t)
    if (Capture $p $png) { $shots += $png }
  }
}

$alive = -not $p.HasExited
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue

$lines = @(Get-Content $log -ErrorAction SilentlyContinue)
# An interpreter refusal is a crash too. The first moveset run died on
# "ppc: pc=... outside blob code range" and this line called it "faults/asserts : 0", because the
# pattern list only knew about native faults. Anything that ends a run must be listed here, or
# the suite reports green on a dead process.
$bad = @($lines | Select-String -Pattern ('FATAL|access violation|assertion|spinning|' +
        'not found stage param|panic|outside blob code range|unimplemented opcode|' +
        'resolver returned NULL|no resolver|reported \d+ args|' +
        # An aurora fatal ends the process just as surely as a game fault, and the m-ex
        # item gap below terminates a run with a paragraph of prose and no keyword.
        'aurora fatal|aurora\[fatal\]|is EMPTY \(no state table\)'))
$retrace = @($lines | Select-String -Pattern 'retrace=(\d+)' -AllMatches)
$first = $null; $last = $null
if ($retrace.Count -gt 0) {
  $first = [int]($retrace[0].Matches[0].Groups[1].Value)
  $last  = [int]($retrace[-1].Matches[-1].Groups[1].Value)
}
$draw = @($lines | Select-String -Pattern 'drawcalls=(\d+)' -AllMatches)
$maxdraw = 0
foreach ($d in $draw) { foreach ($m in $d.Matches) { $v = [int]$m.Groups[1].Value; if ($v -gt $maxdraw) { $maxdraw = $v } } }

Write-Output ""
Write-Output ("alive at end      : {0}" -f $alive)
Write-Output ("faults/asserts    : {0}" -f $bad.Count)
foreach ($b in ($bad | Select-Object -First 3)) { Write-Output ("    " + $b.Line.Trim()) }
Write-Output ("frames advanced   : {0} -> {1}" -f $first, $last)
Write-Output ("max drawcalls     : {0}" -f $maxdraw)
foreach ($s in $shots) { Write-Output ("capture           : " + $s) }

$advanced = ($first -ne $null -and $last -gt $first)
if ($alive -and $bad.Count -eq 0 -and $advanced -and $maxdraw -gt 0) { Write-Output "RESULT: OK"; exit 0 }
Write-Output "RESULT: PROBLEM"
exit 1
