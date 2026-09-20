@echo off
rem Rebuild gwtool.exe. A wrapper around melee\pc\tools\gwtool\build.bat that works from a
rem checkout whose path contains a space or an apostrophe.
rem
rem RUN IT FROM POWERSHELL, by path:
rem
rem   & "<root>\_build\build_gwtool.bat"                    -> the shared _build\gwtool\gwtool.exe
rem   $env:GW_MELEE   = "<root>\worktrees\<agent>"          build that agent's gwtool.cpp
rem   $env:GWTOOL_OUT = "<root>\_build\agents\<agent>\gwtool"  into its own build root
rem
rem NOT through `cmd /c` from Git Bash: cmd strips the outer quotes of its /c argument, so a
rem checkout at "...\GD's Melee" is split on the space and cmd answers
rem "'C:\Users\Gurek\Desktop\GD's' is not recognized". PowerShell's call operator hands the path
rem over intact. The paths inside this file are quoted and are fine either way.
rem
rem It finds the workspace beside itself (%~dp0..), so it is not relocatable: run it where it
rem lives, or set LLVM_ROOT as well.
rem
rem AFTER REBUILDING GWTOOL, REBUILD EVERY GAME TU. The ABI pin (pinInternalAbi) is applied per
rem TU: objects an older gwtool produced keep the private calling conventions the guest->native
rem bridge cannot call, and an exe linked from a mixture is exactly what tools/port/build.sh's
rem `abi` step exists to catch.
rem
rem   cd "$GW_MELEE" && xargs -P 8 -I{} bash _build/masstest/pipe_win.sh {} < _build/masstest/files.txt
rem   bash tools/port/build.sh
setlocal
set "GW_ROOT=%~dp0.."
if "%GW_MELEE%"=="" set "GW_MELEE=%GW_ROOT%\melee"
if "%LLVM_ROOT%"=="" set "LLVM_ROOT=%GW_ROOT%\_toolchains\llvm"
if "%GWTOOL_OUT%"=="" set "GWTOOL_OUT=%GW_ROOT%\_build\gwtool"
set "SRC=%GW_MELEE%\pc\tools\gwtool"
if not exist "%SRC%\gwtool.cpp" (
  echo error: no gwtool.cpp under "%SRC%" - set GW_MELEE to the melee checkout
  exit /b 1
)
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" amd64 >nul
if errorlevel 1 exit /b 1
if not exist "%GWTOOL_OUT%" mkdir "%GWTOOL_OUT%"
for /f "delims=" %%L in ('"%LLVM_ROOT%\bin\llvm-config.exe" --libnames core irreader bitreader bitwriter passes x86codegen x86asmparser x86desc x86info target analysis transformutils support') do set "LLVM_LIBS=%%L"
cl /nologo /c /O2 /MT /std:c++17 /EHs-c- /GR- /Zc:__cplusplus /W3 /wd4244 /wd4267 /wd4291 /wd4624 /wd4141 /wd4146 /wd4996 ^
  /I"%LLVM_ROOT%\include" /DNDEBUG /D_CRT_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_WARNINGS ^
  "%SRC%\gwtool.cpp" "%SRC%\compression_stubs.cpp" /Fo"%GWTOOL_OUT%\\"
if errorlevel 1 exit /b 1
link /nologo /OUT:"%GWTOOL_OUT%\gwtool.exe" "%GWTOOL_OUT%\gwtool.obj" "%GWTOOL_OUT%\compression_stubs.obj" /LIBPATH:"%LLVM_ROOT%\lib" %LLVM_LIBS% ^
  psapi.lib shell32.lib ole32.lib uuid.lib advapi32.lib ws2_32.lib ntdll.lib
if errorlevel 1 exit /b 1
echo GWTOOL_OK %GWTOOL_OUT%\gwtool.exe
