@echo off
rem Called without setlocal so the compiler environment reaches the caller.
if not "%GW_VCVARSALL%"=="" goto :have_vcvars
set "GW_VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%GW_VSWHERE%" set "GW_VSWHERE=%ProgramFiles%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%GW_VSWHERE%" (
  echo error: vswhere.exe not found - install Visual Studio Build Tools, or set GW_VCVARSALL 1>&2
  exit /b 1
)
for /f "usebackq delims=" %%I in (`"%GW_VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "GW_VSDIR=%%I"
if "%GW_VSDIR%"=="" (
  echo error: no Visual Studio with the C++ x86/x64 tools - install "Desktop development with C++" 1>&2
  exit /b 1
)
set "GW_VCVARSALL=%GW_VSDIR%\VC\Auxiliary\Build\vcvarsall.bat"
:have_vcvars
if not exist "%GW_VCVARSALL%" (
  echo error: vcvarsall.bat not found at "%GW_VCVARSALL%" 1>&2
  exit /b 1
)
call "%GW_VCVARSALL%" %~1 >nul
if errorlevel 1 exit /b 1

