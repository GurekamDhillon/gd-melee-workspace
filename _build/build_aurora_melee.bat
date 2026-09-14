@echo off
rem Build the port's own Aurora copy for 32-bit x86, reusing the already-downloaded Dawn/SDL3 sources.
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" amd64_x86
if errorlevel 1 exit /b 1
set "PATH=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
cmake -S C:\gdm\melee\extern\aurora -B C:\gdm\_build\ax86m -G Ninja ^
  -DCMAKE_BUILD_TYPE=RelWithDebInfo ^
  -DAURORA_DAWN_PROVIDER=vendor ^
  -DAURORA_SDL3_PROVIDER=package ^
  -DAURORA_SDL3_PACKAGE_URL=https://github.com/encounter/sdl3-build/releases/download/v3.4.10/SDL3-windows-x86.tar.gz ^
  -DDAWN_ENABLE_VULKAN=OFF ^
  -DAURORA_ENABLE_DVD=OFF ^
  -DAURORA_ENABLE_CARD=ON ^
  -DAURORA_ENABLE_THP=OFF ^
  -DAURORA_ENABLE_RMLUI=OFF ^
  -DFETCHCONTENT_SOURCE_DIR_DAWN=C:/gdm/_build/ax86/_deps/dawn-src ^
  -DFETCHCONTENT_SOURCE_DIR_SDL3_PREBUILT=C:/gdm/_build/ax86/_deps/sdl3_prebuilt-src
if errorlevel 1 exit /b 1
cmake --build C:\gdm\_build\ax86m --target simple
if errorlevel 1 exit /b 1
echo AURORA_MELEE_BUILD_OK
