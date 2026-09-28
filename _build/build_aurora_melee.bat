@echo off
setlocal
rem EVERY PATH HERE IS QUOTED. An unquoted %GW_ROOT% splits on the space in a checkout like
rem "GD's Melee" and cmake reports the source dir as <split-path>. That is the
rem fifth distinct quoting bug this tree has hit for the same reason; quote unconditionally.
rem Build the port's own Aurora copy for 32-bit x86, reusing the already-downloaded Dawn/SDL3 sources.
rem Set GW_AURORA_ROOT to the stable junction; see tools/move_workspace.md.
call "%~dp0..\tools\port\aurora_env.bat"
if errorlevel 1 exit /b 1
call "%~dp0..\tools\port\vs_env.bat" amd64_x86
if errorlevel 1 exit /b 1
if defined GW_VSDIR set "PATH=%GW_VSDIR%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%GW_VSDIR%\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
cmake -S "%GW_ROOT%\melee\extern\aurora" -B "%GW_ROOT%\_build\ax86m" -G Ninja ^
  -DCMAKE_BUILD_TYPE=RelWithDebInfo ^
  -DAURORA_DAWN_PROVIDER=vendor ^
  -DAURORA_SDL3_PROVIDER=package ^
  -DAURORA_SDL3_PACKAGE_URL=https://github.com/encounter/sdl3-build/releases/download/v3.4.10/SDL3-windows-x86.tar.gz ^
  -DDAWN_ENABLE_VULKAN=OFF ^
  -DAURORA_ENABLE_DVD=OFF ^
  -DAURORA_ENABLE_CARD=ON ^
  -DAURORA_ENABLE_THP=OFF ^
  -DAURORA_ENABLE_RMLUI=OFF ^
  "-DFETCHCONTENT_SOURCE_DIR_DAWN=%GW_ROOT:\=/%/_build/ax86/_deps/dawn-src" ^
  "-DFETCHCONTENT_SOURCE_DIR_SDL3_PREBUILT=%GW_ROOT:\=/%/_build/ax86/_deps/sdl3_prebuilt-src"
if errorlevel 1 exit /b 1
rem The port also links aurora_os/pad/si/card, which the "simple" example does not pull in;
rem build them explicitly or they go stale across Aurora updates.
cmake --build "%GW_ROOT%\_build\ax86m" --target simple aurora_os aurora_pad aurora_si aurora_card
if errorlevel 1 exit /b 1
echo AURORA_MELEE_BUILD_OK
