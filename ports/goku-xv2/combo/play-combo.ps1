# Play Goku with the combo graph in the LAB (window at 40,40). COMBO mode (key 0) shows the open routes and the true/escapable
# reading; P2 is a Mario CPU. Uses the geno-combo engine and the combo package copy (the Goku package is not touched).
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$isoLine = Get-Content -LiteralPath (Join-Path $root '.env') | Where-Object { $_ -match '^\s*(?:export\s+)?GW_ISO_VANILLA\s*=' } | Select-Object -First 1
$iso = ($isoLine -replace '^\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*','').Trim().Trim('"').Trim("'")
$env:GW_MELEE = Join-Path $root 'worktrees/geno-combo'
$env:GW_BUILD_ROOT = Join-Path $root '_build/agents/geno-combo'
Set-Location -LiteralPath $root
python ports/goku-xv2/combo/combo_apply.py
$mods = Join-Path $root '_build/goku-xv2/combo-package/mods'
(Get-Content (Join-Path $mods 'enabled.txt')) | Where-Object { $_ -ne 'goku-combo-tests' } | Set-Content -Encoding ascii (Join-Path $mods 'enabled.txt')
$env:MELEE_MODS_DIR = $mods
$env:MELEE_SCENE = 'mode=lab;p1=geno:goku-xv2/hu;p2=mario/cpu0;stage=fd;items=off;time=0'
$env:MELEE_WINDOW_X = '40'; $env:MELEE_WINDOW_Y = '40'; $env:MELEE_WINDOW_W = '1600'; $env:MELEE_WINDOW_H = '900'
$env:MELEE_UNATTENDED = '0'; $env:MELEE_MAX_SECONDS = '0'
$env:MELEE_RUN_LABEL = 'Goku XV2 - combo graph LAB'
& 'C:/Program Files/Git/bin/bash.exe' tools/port/run.sh --realtime goku-combo-lab --iso $iso
