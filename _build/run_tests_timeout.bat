@echo off
if "%GW_ROOT%"=="" for %%I in ("%~dp0..") do set "GW_ROOT=%%~fI"
set MELEE_TEST_TIMEOUT=2
bash "%GW_ROOT%/tools/port/run.sh" --test run_tests_timeout
echo EXITCODE=%ERRORLEVEL%
