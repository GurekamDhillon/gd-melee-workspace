@echo off
setlocal
rem Play the current build, without blocking the next link.
rem
rem   play.bat                              vanilla disc, straight to the menu
rem   play.bat akaneia                      Akaneia
rem   play.bat ace                          ACE (mods off, so the disc's own MxDt.dat is used)
rem   play.bat akaneia "mode=training;p1=ck:38;stage=ext:293"    a seeded scene
rem
rem It runs a COPY in _build/runs/play. Running _build/melee-pc.exe directly holds it open, the
rem next link fails with LNK1104, and the build after that silently tests stale code.
rem
rem Disc paths come from <root>/.env (GW_ISO_VANILLA / GW_ISO_AKANEIA / GW_ISO_ACE). See SETUP.md.
rem No disc image ships with this repository.

if "%GW_ROOT%"=="" for %%I in ("%~dp0..") do set "GW_ROOT=%%~fI"

rem .env is shell syntax; pull the three ISO lines out of it without needing bash.
if exist "%GW_ROOT%\.env" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%GW_ROOT%\.env") do (
    set "_k=%%A"
    set "_v=%%B"
    call :setiso
  )
)

set "DISC=%~1"
if "%DISC%"=="" set "DISC=vanilla"
if /i "%DISC%"=="vanilla" set "ISO=%GW_ISO_VANILLA%"
if /i "%DISC%"=="akaneia" set "ISO=%GW_ISO_AKANEIA%"
rem ACE deliberately runs with an EMPTY mods folder: the sonic mod overrides /MxDt.dat on every
rem disc, so with mods on an ACE run reads Akaneia's 96-stage tables and proves nothing.
if /i "%DISC%"=="ace" (
  set "ISO=%GW_ISO_ACE%"
  set "MELEE_MODS_DIR=%GW_ROOT%\_build\nomods"
)
if "%ISO%"=="" (
  echo error: no ISO for "%DISC%" - set GW_ISO_VANILLA/AKANEIA/ACE in "%GW_ROOT%\.env" 1>&2
  exit /b 1
)

if not "%~2"=="" set "MELEE_SCENE=%~2"
if "%MELEE_MODS_DIR%"=="" set "MELEE_MODS_DIR=%GW_ROOT%\_build\mods"
rem WITHOUT THIS THE CARD IS EMPTY. shim_card.c falls back to "card/" NEXT TO THE EXE, and the
rem exe runs from a per-run sandbox - so every launch got a fresh card, which means the memcard
rem prompt on boot AND a fully LOCKED roster. A locked roster re-flows the character grid, and
rem that is what produced an evening of "Fox is missing" / "Sonic is unselectable" reports.
rem Point it at the shared card, which is unlocked. ACE keeps its own, since its roster differs.
if "%MELEE_CARD_PATH%"=="" (
  if /i "%DISC%"=="ace" ( set "MELEE_CARD_PATH=%GW_ROOT%\_build\card-ace" ) else ( set "MELEE_CARD_PATH=%GW_ROOT%\_build\card" )
)
if "%MELEE_SKIP_INTRO%"=="" set "MELEE_SKIP_INTRO=1"

set "SANDBOX=%GW_ROOT%\_build\runs\play"
if not exist "%SANDBOX%" mkdir "%SANDBOX%"
if not exist "%MELEE_MODS_DIR%" mkdir "%MELEE_MODS_DIR%"
rem A previous instance holds the sandbox exe open, and for a moment AFTER it is killed too. A
rem failed copy here is the worst outcome available: the old exe stays and you play a stale build
rem while believing you are testing the new one. So stop it, then retry, then refuse.
taskkill /IM melee-pc.exe /F >nul 2>&1
set /a _try=0
:copyexe
copy /y "%GW_ROOT%\_build\melee-pc.exe" "%SANDBOX%\" >nul 2>&1
if not errorlevel 1 goto copied
set /a _try+=1
if %_try% GEQ 10 (
  echo error: could not copy melee-pc.exe into the sandbox after 10 tries. 1>&2
  echo        Is it still running, or has the build not been run yet? 1>&2
  exit /b 1
)
ping -n 2 127.0.0.1 >nul
goto copyexe
:copied
copy /y "%GW_ROOT%\_build\melee-pc.map" "%SANDBOX%\" >nul 2>&1
copy /y "%GW_ROOT%\_build\SDL3.dll" "%SANDBOX%\" >nul
copy /y "%GW_ROOT%\_build\webgpu_dawn.dll" "%SANDBOX%\" >nul

echo disc    %ISO%
echo mods    %MELEE_MODS_DIR%
if not "%MELEE_SCENE%"=="" echo scene   %MELEE_SCENE%
echo card    %MELEE_CARD_PATH%
echo log     %SANDBOX%\melee-pc.log
echo.
cd /d "%SANDBOX%"
"%SANDBOX%\melee-pc.exe" --iso "%ISO%"
exit /b %errorlevel%

:setiso
set "_k=%_k: =%"
if /i "%_k%"=="exportGW_ISO_VANILLA" call :strip GW_ISO_VANILLA
if /i "%_k%"=="GW_ISO_VANILLA"       call :strip GW_ISO_VANILLA
if /i "%_k%"=="exportGW_ISO_AKANEIA" call :strip GW_ISO_AKANEIA
if /i "%_k%"=="GW_ISO_AKANEIA"       call :strip GW_ISO_AKANEIA
if /i "%_k%"=="exportGW_ISO_ACE"     call :strip GW_ISO_ACE
if /i "%_k%"=="GW_ISO_ACE"           call :strip GW_ISO_ACE
goto :eof

:strip
rem Drop every quote rather than trimming the ends: comparing against a literal quote in batch
rem (if "%x:~0,1%"==""") unbalances the parser and fails with "set was unexpected at this time".
rem Disc paths do not contain quotes, so this is safe and far less fragile.
set _t=%_v%
set _t=%_t:"=%
set "%~1=%_t%"
goto :eof
