@echo off
rem Called without setlocal so the compiler environment reaches the caller.
rem Overrides: GW_VCVARSALL (full path to vcvarsall.bat), GW_VSDIR (install dir used for cmake/ninja).
rem Without them: vswhere (both Program Files dirs), then known install dirs are probed.
if not "%GW_VCVARSALL%"=="" goto :have_vcvars

set "GW_VSWHERE="
for %%P in ("%ProgramFiles(x86)%" "%ProgramFiles%") do (
  if not defined GW_VSWHERE if exist "%%~P\Microsoft Visual Studio\Installer\vswhere.exe" set "GW_VSWHERE=%%~P\Microsoft Visual Studio\Installer\vswhere.exe"
)
set "GW_VSFOUND="
rem An absolute path also works when cmd disables current-directory executable lookup.
rem CALL keeps for /f's cmd /c wrapper from stripping the executable's quotes.
if not defined GW_VSWHERE goto :vswhere_done
for /f "usebackq delims=" %%I in (`call "%GW_VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2^>nul`) do set "GW_VSFOUND=%%I"
:vswhere_done
rem vswhere missing or failing: probe the known layouts, newest first.
if not defined GW_VSFOUND (
  for %%V in (18 2022 2019) do for %%E in (Community Professional Enterprise BuildTools) do for %%R in ("%ProgramFiles%" "%ProgramFiles(x86)%") do (
    if not defined GW_VSFOUND if exist "%%~R\Microsoft Visual Studio\%%V\%%E\VC\Auxiliary\Build\vcvarsall.bat" set "GW_VSFOUND=%%~R\Microsoft Visual Studio\%%V\%%E"
  )
)
if not defined GW_VSFOUND (
  echo error: no Visual Studio with the C++ x86/x64 tools - install "Desktop development with C++", or set GW_VCVARSALL 1>&2
  exit /b 1
)
set "GW_VCVARSALL=%GW_VSFOUND%\VC\Auxiliary\Build\vcvarsall.bat"
:have_vcvars
if not exist "%GW_VCVARSALL%" (
  echo error: vcvarsall.bat not found at "%GW_VCVARSALL%" 1>&2
  exit /b 1
)
call "%GW_VCVARSALL%" %~1 >nul
if errorlevel 1 exit /b 1

rem cmake/ninja: the install that owns vcvarsall may lack them (VS 18 Community). If so, use the
rem first install that has cmake (GW_VSDIR if set and valid, else probe) and put its tools on PATH.
where cmake >nul 2>nul && where ninja >nul 2>nul && goto :tools_ok
set "GW_CMAKEDIR="
if defined GW_VSDIR if exist "%GW_VSDIR%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" set "GW_CMAKEDIR=%GW_VSDIR%"
if not defined GW_CMAKEDIR (
  for %%V in (18 2022 2019) do for %%E in (Community Professional Enterprise BuildTools) do for %%R in ("%ProgramFiles%" "%ProgramFiles(x86)%") do (
    if not defined GW_CMAKEDIR if exist "%%~R\Microsoft Visual Studio\%%V\%%E\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" set "GW_CMAKEDIR=%%~R\Microsoft Visual Studio\%%V\%%E"
  )
)
if defined GW_CMAKEDIR (
  set "GW_VSDIR=%GW_CMAKEDIR%"
  set "PATH=%GW_CMAKEDIR%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%GW_CMAKEDIR%\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
)
:tools_ok
exit /b 0
