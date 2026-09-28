@echo off
if "%GW_ROOT%"=="" for %%I in ("%~dp0..") do set "GW_ROOT=%%~fI"
set MELEE_CARD=1
set MELEE_TRAINING=sonic
bash "%GW_ROOT%/tools/port/run.sh" run_training
