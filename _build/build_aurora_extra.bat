@echo off
rem Builds the Aurora static libraries the Melee port needs beyond the ones the "simple" example
rem links: the OS module (heap/arena/time/report) and the PAD module (plus SI, which PAD needs).
setlocal
rem Set GW_AURORA_ROOT to the stable junction; see tools/move_workspace.md.
call "%~dp0..\tools\port\aurora_env.bat"
if errorlevel 1 exit /b 1
call "%~dp0..\tools\port\vs_env.bat" amd64_x86
if errorlevel 1 exit /b 1
if defined GW_VSDIR set "PATH=%GW_VSDIR%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%GW_VSDIR%\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
cmake --build "%GW_ROOT%\_build\ax86m" --target aurora_os aurora_pad
if errorlevel 1 exit /b 1
echo AURORA_EXTRA_BUILD_OK
