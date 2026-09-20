@echo off
rem The disc: %1 if given, else GW_ISO_VANILLA (set it in <root>/.env - see SETUP.md).
rem No disc image ships with this repository; supply your own legally dumped NTSC 1.02 copy.
if not "%~1"=="" set "GW_ISO=%~1"
if "%GW_ISO%"=="" set "GW_ISO=%GW_ISO_VANILLA%"
if "%GW_ISO%"=="" (
  echo error: no disc image - pass one as an argument or set GW_ISO_VANILLA 1>&2
  exit /b 1
)
taskkill /IM melee-pc.exe /F >nul 2>&1
cd /d "%~dp0"
set MELEE_CARD=1
start "" "%~dp0melee-pc.exe" --iso "%GW_ISO%"
