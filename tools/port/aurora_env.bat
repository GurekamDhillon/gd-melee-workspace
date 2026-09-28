@echo off
rem GW_AURORA_ROOT must be the stable junction path, without spaces or apostrophes.
if "%GW_AURORA_ROOT%"=="" (
  echo error: set GW_AURORA_ROOT to the Aurora junction; see tools/move_workspace.md 1>&2
  exit /b 1
)
powershell -NoProfile -Command "if ($env:GW_AURORA_ROOT -match '[\s'']') { exit 1 }; if ((Get-Item -LiteralPath $env:GW_AURORA_ROOT -ErrorAction Stop).LinkType -ne 'Junction') { exit 1 }; if (-not (Test-Path -LiteralPath ($env:GW_AURORA_ROOT + '/melee/extern/aurora'))) { exit 1 }"
if errorlevel 1 exit /b 1
set "GW_ROOT=%GW_AURORA_ROOT%"
exit /b 0
