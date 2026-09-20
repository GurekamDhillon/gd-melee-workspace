@echo off
rem Build Aurora's CARD library (kabufuda-based memory card) for the port's 32-bit configuration.
rem GW_ROOT defaults to this script's parent directory, so a fresh clone works with no
rem %GW_ROOT% symlink; tools/port exports it and that wins. See SETUP.md.
if "%GW_ROOT%"=="" for %%I in ("%~dp0..") do set "GW_ROOT=%%~fI"
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" amd64_x86
if errorlevel 1 exit /b 1
set "PATH=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
cmake --build %GW_ROOT%\_build\ax86m --target aurora_card
if errorlevel 1 exit /b 1
echo AURORA_CARD_BUILD_OK
