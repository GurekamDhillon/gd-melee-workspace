# Play the remade Goku in the LAB (combo package: ki meter, Homing, Down B ki charge).
#   & 'E:\Projects\Melee Workspace\worktrees\gokup1\ports\goku-xv2\tools\play_remake.ps1'        # LAB, Goku vs a Mario CPU on FD, window at 40,40
# Optional: -Picker opens the REMAKE picker instead (the owner's picks show as taken; swap one, then remake_sheet.py --sync-picks and rebuild).
# Env overrides: GW_MELEE (game checkout with the geno-11 engine + REMAKE mode), GW_BUILD_ROOT (its build root with melee-pc.exe).
# Controls (Scheme A, Melee buttons only): B = Kamehameha (hold to charge); Down B tap = vanish counter, Down B hold = ki charge (only below 100);
# Up B = flight while the ki lasts (2 s at 100 ki; steer with the stick; B ends it, A / C-stick = an aerial: a hit keeps air control, a miss = the special fall).
# Rolls and the spot dodge are Instant Transmission teleports. Feet on the floor: no hover. Smashes charge (hold A).
# shield + B (stick neutral) = homing dash strike (20 ki); Side B = knockback attack (Rush); D-pad Down (or Y under CSS layout B) = ki blast (5 ki).
# Every move that has XV2 hit data carries a labelled HB-SAMPLE hitbox (REMAKE-SAMPLES.md): starting points, not final.
param([switch]$Picker)
$ErrorActionPreference = 'Continue'
$portRoot = Split-Path -Parent $PSScriptRoot
$wsRoot = Split-Path -Parent (Split-Path -Parent $portRoot)
$mainRoot = $wsRoot
if ((Split-Path -Leaf (Split-Path -Parent $wsRoot)) -eq 'worktrees') { $mainRoot = Split-Path -Parent (Split-Path -Parent $wsRoot) }
$isoLine = Get-Content -LiteralPath (Join-Path $mainRoot '.env') | Where-Object { $_ -match '^\s*(?:export\s+)?GW_ISO_VANILLA\s*=' } | Select-Object -First 1
if (-not $isoLine) { throw 'GW_ISO_VANILLA is missing from workspace .env' }
$iso = ($isoLine -replace '^\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*','').Trim().Trim('"').Trim("'")
if (-not $env:GW_MELEE) { $env:GW_MELEE = Join-Path $mainRoot 'worktrees/gokup1-game' }
if (-not $env:GW_BUILD_ROOT) { $env:GW_BUILD_ROOT = Join-Path $mainRoot '_build/agents/gokup1' }
Set-Location -LiteralPath $wsRoot
python ports/goku-xv2/combo/combo_apply.py
$mods = Join-Path $wsRoot '_build/goku-xv2/combo-package/mods'
(Get-Content (Join-Path $mods 'enabled.txt')) | Where-Object { $_ -ne 'goku-combo-tests' } | Set-Content -Encoding ascii (Join-Path $mods 'enabled.txt')
$env:MELEE_MODS_DIR = $mods
$p2 = if ($env:PLAY_P2) { $env:PLAY_P2 } else { 'mario/cpu0' }
$stage = if ($env:PLAY_STAGE) { $env:PLAY_STAGE } else { 'fd' }
$env:MELEE_SCENE = "mode=lab;p1=geno:goku-xv2/hu;p2=$p2;stage=$stage;items=off;time=0"
$env:MELEE_WINDOW_X = '40'; $env:MELEE_WINDOW_Y = '40'; $env:MELEE_WINDOW_W = '1600'; $env:MELEE_WINDOW_H = '900'
$env:MELEE_UNATTENDED = '0'; $env:MELEE_MAX_SECONDS = '0'
$env:MELEE_RUN_LABEL = 'Goku XV2 - remake phase 1 LAB'
if ($Picker) {
  python ports/goku-xv2/tools/remake_lab_data.py --out (Join-Path $mods 'geno-lab/missions/remake-slots.txt')
  $data = Join-Path $wsRoot '_build/goku-xv2/lab-data'
  New-Item -ItemType Directory -Force (Join-Path $data 'geno-lab_lab') | Out-Null
  $dst = Join-Path $data 'geno-lab_lab/remake-picks.json'
  if (-not (Test-Path $dst)) { Copy-Item (Join-Path $portRoot 'remake-picks.json') $dst }   # the owner's own saved picks are never overwritten
  $env:MELEE_SCRIPT_DATA_DIR = $data
  $env:MELEE_LAB_MODE = 'remake'
  $env:MELEE_CPU_IDLE = '1'
}
& 'C:/Program Files/Git/bin/bash.exe' tools/port/run.sh --realtime goku-remake-lab --iso $iso
