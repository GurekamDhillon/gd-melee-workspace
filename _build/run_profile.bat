@echo off
REM Frame profiler: per-frame timing split, percentiles and a histogram, every ~180 frames.
rem The disc: %1 if given, else GW_ISO_VANILLA (set it in <root>/.env - see SETUP.md).
rem No disc image ships with this repository; supply your own legally dumped NTSC 1.02 copy.
if not "%~1"=="" set "GW_ISO=%~1"
if "%GW_ISO%"=="" set "GW_ISO=%GW_ISO_VANILLA%"
if "%GW_ISO%"=="" (
  echo error: no disc image - pass one as an argument or set GW_ISO_VANILLA 1>&2
  exit /b 1
)
cd /d "%~dp0"
set MELEE_PROFILE=1
"%~dp0melee-pc.exe" --iso "%GW_ISO%"
if exist "%~dp0melee-pc.log" copy /y "%~dp0melee-pc.log" "%~dp0profile-last.log" >nul
