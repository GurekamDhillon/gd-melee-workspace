# Open the LAB on the REMAKE page with two Gokus (left: the clip being judged, right: the reference for COMPARE).
# Optional arg: a slot number or name fragment to start on. Picks are saved after every change to
# _build/goku-xv2/lab-data/geno-lab_lab/remake-picks.json; `python ports/goku-xv2/tools/remake_sheet.py --sync-picks` copies them
# to ports/goku-xv2/remake-picks.json and into the sheet's owner-pick column.
# GW_MELEE / GW_BUILD_ROOT may be preset (a game checkout whose geno-lab has the REMAKE mode, and its build root).
$ErrorActionPreference = 'Continue'
$portRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent (Split-Path -Parent $portRoot)
$mainRoot = $workspaceRoot
if ((Split-Path -Leaf (Split-Path -Parent $workspaceRoot)) -eq 'worktrees') { $mainRoot = Split-Path -Parent (Split-Path -Parent $workspaceRoot) }
$isoLine = Get-Content -LiteralPath (Join-Path $mainRoot '.env') | Where-Object { $_ -match '^\s*(?:export\s+)?GW_ISO_VANILLA\s*=' } | Select-Object -First 1
if (-not $isoLine) { throw 'GW_ISO_VANILLA is missing from workspace .env' }
$gokuIso = ($isoLine -replace '^\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*','').Trim().Trim('"').Trim("'")
if (-not $env:GW_MELEE) { $env:GW_MELEE = Join-Path $mainRoot 'melee' }   # the integrated game (has the REMAKE mode)
$labSrc = if ($env:GW_LAB_SRC) { $env:GW_LAB_SRC } else { Join-Path $env:GW_MELEE 'pc/geno/mods/geno-lab' }
$pkgMods = Join-Path $mainRoot '_build/goku-xv2/author-source/package/mods'
$mods = Join-Path $mainRoot '_build/goku-xv2/remake-mods'
# the mods dir: the Goku package, with the LAB replaced by this checkout's (REMAKE mode) plus the move map and the picker data
& robocopy $pkgMods $mods /MIR /XD geno-lab /NFL /NDL /NJH /NJS /NP | Out-Null
& robocopy $labSrc (Join-Path $mods 'geno-lab') /MIR /XD missions /NFL /NDL /NJH /NJS /NP | Out-Null
New-Item -ItemType Directory -Force (Join-Path $mods 'geno-lab/missions') | Out-Null
Copy-Item -Force (Join-Path $pkgMods 'geno-lab/missions/*') (Join-Path $mods 'geno-lab/missions')
$env:GW_MAIN = $mainRoot
& python (Join-Path $portRoot 'tools/remake_lab_data.py') --out (Join-Path $mods 'geno-lab/missions/remake-goku.txt')
$env:MELEE_MODS_DIR = $mods
$data = Join-Path $mainRoot '_build/goku-xv2/lab-data'
New-Item -ItemType Directory -Force $data | Out-Null
$env:MELEE_SCRIPT_DATA_DIR = $data
$env:MELEE_SCENE = 'mode=lab;p1=geno:goku-xv2/hu;p2=geno:goku-xv2/cpu0;stage=fd;items=off;time=0'
Remove-Item Env:MELEE_PAD_SCRIPT -ErrorAction SilentlyContinue
$env:MELEE_LAB_MODE = 'remake'
if ($args.Count -gt 0) { $env:MELEE_LAB_SLOT = $args[0] }
$env:MELEE_CPU_IDLE = '1'
$env:MELEE_TURBO = '0'
$env:MELEE_TURBO_RENDER = '1'
if (-not $env:MELEE_WINDOW_X) { $env:MELEE_WINDOW_X = '100'; $env:MELEE_WINDOW_Y = '80' }
if (-not $env:MELEE_WINDOW_W) { $env:MELEE_WINDOW_W = '1920'; $env:MELEE_WINDOW_H = '1080' }
$env:MELEE_RENDER_SCALE = '3'
$env:MELEE_UNATTENDED = '0'
$env:MELEE_MAX_SECONDS = '0'
$env:MELEE_RUN_LABEL = 'Goku XV2 - LAB REMAKE'
if (-not $env:MELEE_CONSOLE_PORT) { $env:MELEE_CONSOLE_PORT = '51726' }
$env:MELEE_VOLUME = '3'
Set-Location -LiteralPath $mainRoot
& 'C:/Program Files/Git/bin/bash.exe' tools/port/run.sh --realtime goku-xv2-remake --iso $gokuIso *> '_build/goku-xv2/lab-remake-launch.log'
exit $LASTEXITCODE
