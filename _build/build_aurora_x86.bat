@echo off
setlocal
rem Bootstrap: builds the vendored Aurora's "simple" example for 32-bit x86, which fetches Dawn and
rem SDL3 into _build\ax86 for the port build (build_aurora_melee.bat) to reuse. No other checkout.
rem Set GW_AURORA_ROOT to the stable junction; see tools/move_workspace.md.
call "%~dp0..\tools\port\aurora_env.bat"
if errorlevel 1 exit /b 1
call "%~dp0..\tools\port\vs_env.bat" amd64_x86
if errorlevel 1 exit /b 1
if defined GW_VSDIR set "PATH=%GW_VSDIR%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%GW_VSDIR%\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
cmake --version
cmake -S "%GW_ROOT%\melee\extern\aurora" -B "%GW_ROOT%\_build\ax86" -G Ninja ^
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
cmake --build "%GW_ROOT%\_build\ax86" --target simple
if errorlevel 1 exit /b 1
echo AURORA_X86_BUILD_OK
