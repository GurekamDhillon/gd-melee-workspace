# Watch Goku's combo route tests on screen (window at 40,40, 60 Hz): the XV2 light string into the heavy finisher, the
# Dragon Rush and ki-volley special cancels, vs Fox. Tables land in _build/goku-xv2/combo/results/watch.md.
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$env:GW_MELEE = Join-Path $root 'worktrees/geno-combo'
$env:GW_BUILD_ROOT = Join-Path $root '_build/agents/geno-combo'
Set-Location -LiteralPath $root
python ports/goku-xv2/combo/combo_apply.py
python ports/goku-xv2/combo/tests/run_combo_tests.py --visible --vs fox --specs light5-finisher,light2-dragon-rush,light1-ki-volley --name watch
