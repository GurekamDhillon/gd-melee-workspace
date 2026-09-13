@echo off
rem Test build: Aurora "simple" example for 32-bit x86 Windows with Dawn built from source (vendor).
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" amd64_x86
if errorlevel 1 exit /b 1
set "PATH=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
cmake --version
cmake -S C:\gdm\dusklight\extern\aurora -B C:\gdm\_build\ax86 -G Ninja ^
  -DCMAKE_BUILD_TYPE=RelWithDebInfo ^
  -DAURORA_DAWN_PROVIDER=vendor ^
  -DAURORA_SDL3_PROVIDER=package ^
  -DAURORA_SDL3_PACKAGE_URL=https://github.com/encounter/sdl3-build/releases/download/v3.4.10/SDL3-windows-x86.tar.gz ^
  -DDAWN_ENABLE_VULKAN=OFF ^
  -DAURORA_ENABLE_DVD=OFF ^
  -DAURORA_ENABLE_CARD=OFF ^
  -DAURORA_ENABLE_THP=OFF ^
  -DAURORA_ENABLE_RMLUI=OFF
if errorlevel 1 exit /b 1
cmake --build C:\gdm\_build\ax86 --target simple
if errorlevel 1 exit /b 1
echo AURORA_X86_BUILD_OK
