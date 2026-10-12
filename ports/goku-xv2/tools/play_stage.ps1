# Owner play: the staged Goku (ws/goku-stage package, combo build) on the staged exe (agent/goku-stage-game), LAB, Battlefield, idle Captain Falcon, sound ON, on screen, realtime.
#   & 'E:\Projects\Melee Workspace\worktrees\gokustage\ports\goku-xv2\tools\play_stage.ps1'
# Env overrides: PLAY_P2 (default captain/cpu0), PLAY_STAGE (default bf), GW_MELEE / GW_BUILD_ROOT (default: the stage game worktree and its build root).
$ErrorActionPreference = 'Continue'
$portRoot = Split-Path -Parent $PSScriptRoot
$wt = Split-Path -Parent (Split-Path -Parent $portRoot)
$mainRoot = $wt
if ((Split-Path -Leaf (Split-Path -Parent $wt)) -eq 'worktrees') { $mainRoot = Split-Path -Parent (Split-Path -Parent $wt) }
$isoLine = Get-Content -LiteralPath (Join-Path $mainRoot '.env') | Where-Object { $_ -match '^\s*(?:export\s+)?GW_ISO_VANILLA\s*=' } | Select-Object -First 1
if (-not $isoLine) { throw 'GW_ISO_VANILLA is missing from the workspace .env' }
$iso = ($isoLine -replace '^\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*','').Trim().Trim('"').Trim("'")
if (-not $env:GW_MELEE) { $env:GW_MELEE = Join-Path $mainRoot 'worktrees/gokustage-game' }
if (-not $env:GW_BUILD_ROOT) { $env:GW_BUILD_ROOT = Join-Path $mainRoot '_build/agents/gokustage' }
$p2 = if ($env:PLAY_P2) { $env:PLAY_P2 } else { 'captain/cpu0' }
$stage = if ($env:PLAY_STAGE) { $env:PLAY_STAGE } else { 'bf' }
$env:MELEE_MODS_DIR = Join-Path $wt '_build/goku-xv2/combo-package/mods'
$env:MELEE_SCENE = "mode=lab;p1=geno:goku-xv2/hu;p2=$p2;stage=$stage;items=off;time=0"
Remove-Item Env:MELEE_PAD_SCRIPT -ErrorAction SilentlyContinue
$env:MELEE_CPU_IDLE = '1'
$env:MELEE_TURBO = '0'
$env:MELEE_TURBO_RENDER = '1'
$env:MELEE_WINDOW_X = '100'; $env:MELEE_WINDOW_Y = '80'; $env:MELEE_WINDOW_W = '1920'; $env:MELEE_WINDOW_H = '1080'
$env:MELEE_RENDER_SCALE = '3'
$env:MELEE_UNATTENDED = '0'
$env:MELEE_MAX_SECONDS = '0'
$env:MELEE_RUN_LABEL = 'Goku (staged) - LAB, Battlefield'
$env:MELEE_VOLUME = '3'
Set-Location -LiteralPath $mainRoot
& 'C:/Program Files/Git/bin/bash.exe' tools/port/run.sh --realtime goku-stage-play --iso $iso
exit $LASTEXITCODE
