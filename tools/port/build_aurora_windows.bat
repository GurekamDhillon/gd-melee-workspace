@echo off
setlocal
rem Same x86 toolchain/features as _build/build_aurora_melee.bat, private outputs.
call "%~dp0vs_env.bat" amd64_x86
if errorlevel 1 exit /b 1
cmake -S "%GW_MELEE%/extern/aurora" -B "%GW_AURORA_BUILD%" -G Ninja ^
  -C "%GW_AURORA_BUILD%/source-cache.cmake" ^
  -DCMAKE_BUILD_TYPE=RelWithDebInfo ^
  -DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON ^
  -DAURORA_DAWN_PROVIDER=vendor ^
  -DAURORA_SDL3_PROVIDER=package ^
  -DAURORA_SDL3_PACKAGE_URL=https://github.com/encounter/sdl3-build/releases/download/v3.4.10/SDL3-windows-x86.tar.gz ^
  -DDAWN_ENABLE_VULKAN=OFF ^
  -DAURORA_ENABLE_DVD=OFF ^
  -DAURORA_ENABLE_CARD=ON ^
  -DAURORA_ENABLE_THP=OFF ^
  -DAURORA_ENABLE_RMLUI=OFF
if errorlevel 1 exit /b 1
cmake --build "%GW_AURORA_BUILD%" --parallel %GW_JOBS% --target simple aurora_os aurora_pad aurora_si aurora_card aurora_mtx aurora_gd aurora_ms png_static
if errorlevel 1 exit /b 1
echo AURORA_MELEE_BUILD_OK
