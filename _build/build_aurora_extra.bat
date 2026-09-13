@echo off
rem Builds the Aurora static libraries the Melee port needs beyond the ones the "simple" example
rem links: the OS module (heap/arena/time/report) and the PAD module (plus SI, which PAD needs).
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" amd64_x86 >nul
if errorlevel 1 exit /b 1
set "PATH=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
cmake --build C:\gdm\_build\ax86m --target aurora_os aurora_pad
if errorlevel 1 exit /b 1
echo AURORA_EXTRA_BUILD_OK
