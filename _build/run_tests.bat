@echo off
if "%GW_ROOT%"=="" for %%I in ("%~dp0..") do set "GW_ROOT=%%~fI"
bash "%GW_ROOT%/tools/port/run.sh" --test run_tests
echo EXITCODE=%ERRORLEVEL%
