# Launch the maintained Goku package in a persistent visible Windows LAB session.
$ErrorActionPreference = 'Continue'
$portRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent (Split-Path -Parent $portRoot)
$isoLine = Get-Content -LiteralPath (Join-Path $workspaceRoot '.env') | Where-Object { $_ -match '^\s*(?:export\s+)?GW_ISO_VANILLA\s*=' } | Select-Object -First 1
if (-not $isoLine) { throw 'GW_ISO_VANILLA is missing from workspace .env' }
$gokuIso = ($isoLine -replace '^\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*','').Trim().Trim('"').Trim("'")
# 2026-10-08: the shadow and toon fixes live on agent/goku-polish until merged.
if (Test-Path (Join-Path $workspaceRoot 'worktrees/geno-thrown')) {
  $env:GW_MELEE = Join-Path $workspaceRoot 'worktrees/geno-thrown'
  $env:GW_BUILD_ROOT = Join-Path $workspaceRoot '_build/agents/geno-thrown'
}
$env:MELEE_MODS_DIR = Join-Path $workspaceRoot '_build/goku-xv2/author-source/package/mods'
$env:MELEE_SCENE = 'mode=lab;p1=geno:goku-xv2/hu;p2=mario/cpu0;stage=fd;items=off;time=0'
$env:MELEE_PAD_SCRIPT = Join-Path $portRoot 'lua/lab_preview.lua'
$env:MELEE_TURBO = '0'
$env:MELEE_TURBO_RENDER = '1'
$env:MELEE_WINDOW_X = '100'
$env:MELEE_WINDOW_Y = '80'
$env:MELEE_WINDOW_W = '1920'
$env:MELEE_WINDOW_H = '1080'
$env:MELEE_RENDER_SCALE = '3'
$env:MELEE_UNATTENDED = '0'
$env:MELEE_MAX_SECONDS = '0'
$env:MELEE_RUN_LABEL = 'Goku XV2 v0.2 - LAB thrown poses'
$env:MELEE_CONSOLE_PORT = '51726'
$env:MELEE_VOLUME = '3'
Set-Location -LiteralPath $workspaceRoot
& 'C:/Program Files/Git/bin/bash.exe' tools/port/run.sh --realtime goku-xv2-thrown-play --iso $gokuIso *> '_build/goku-xv2/lab-thrown-launch.log'
exit $LASTEXITCODE

