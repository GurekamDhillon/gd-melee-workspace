@echo off
if "%GW_ROOT%"=="" for %%I in ("%~dp0..") do set "GW_ROOT=%%~fI"
set MELEE_MEX=no_title_demo
bash "%GW_ROOT%/tools/port/run.sh" --test run_tests_mex
echo EXITCODE=%ERRORLEVEL%
