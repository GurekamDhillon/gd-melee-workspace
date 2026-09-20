@echo off
setlocal
rem Links melee-pc.exe from the gwtool-transformed game objects, the platform shims, and the
rem 32-bit Aurora/Dawn/SDL3 libraries built by build_aurora_melee.bat.
rem
rem The two response files are generated (see docs/DEVLOG.md): melee_link_objects.rsp lists every
rem out/*.obj and shimobj/*.obj, melee_link_libs.rsp mirrors the library set Aurora's own
rem "simple" example links with.
rem
rem NOTHING HERE IS TIED TO A PARTICULAR CHECKOUT PATH. GW_ROOT defaults to this script's own
rem parent directory, so a fresh clone works with no setup and no C:\gdm symlink; tools/port
rem exports GW_ROOT and GW_BUILD_ROOT and those win. See SETUP.md.
rem
rem GW_BUILD_ROOT holds this tree's objects, response file and melee-pc.exe.
rem tools/port/agent_new.sh gives each agent its own, so two agents can link at the same time
rem without overwriting each other.

if "%GW_ROOT%"=="" for %%I in ("%~dp0..") do set "GW_ROOT=%%~fI"
if "%GW_BUILD_ROOT%"=="" set "GW_BUILD_ROOT=%GW_ROOT%\_build"
if "%GW_LINK_OBJECTS%"=="" set "GW_LINK_OBJECTS=%GW_BUILD_ROOT%\melee_link_objects.rsp"
if "%GW_LINK_LIBS%"=="" set "GW_LINK_LIBS=%GW_ROOT%\_build\melee_link_libs.rsp"

rem Find MSVC rather than hardcoding one install. vswhere ships with every VS 2017+ installer and
rem lives at a fixed location; -latest -products * finds BuildTools as well as full VS. Set
rem GW_VCVARSALL yourself to override. Hardcoding a version here is what made this script
rem unusable on any machine but the author's.
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
call "%GW_VCVARSALL%" amd64_x86 >nul
if errorlevel 1 exit /b 1

rem The link runs here because melee_link_libs.rsp names the Aurora/Dawn/SDL3 libraries RELATIVE
rem to this directory; only the outputs follow GW_BUILD_ROOT.
cd /d "%GW_ROOT%\_build\ax86m"
if errorlevel 1 (
  echo error: no Aurora library directory at "%GW_ROOT%\_build\ax86m" - run tools/port/bootstrap.sh 1>&2
  exit /b 1
)

rem /BASE + /DYNAMICBASE:NO pin the image above ARAM's 16 MB so a game global's address can never
rem be mistaken for an ARAM offset (see gw_ar_addr in shim_ar.c), and make every run's addresses
rem reproducible so melee-pc.map RVAs match the crash log directly.
rem /OPT:NOICF because /INCREMENTAL:NO turns on identical-COMDAT folding, which makes several
rem thousand small game functions share one address and so report the wrong name when a crash
rem address is looked up in the map. /OPT:REF stays on.
link /nologo /OUT:"%GW_BUILD_ROOT%\melee-pc.exe" /PDB:"%GW_BUILD_ROOT%\melee-pc.pdb" /MAP:"%GW_BUILD_ROOT%\melee-pc.map" /machine:X86 /INCREMENTAL:NO /subsystem:console /LARGEADDRESSAWARE /BASE:0x10000000 /DYNAMICBASE:NO /OPT:REF /OPT:NOICF ^
  @"%GW_LINK_OBJECTS%" @"%GW_LINK_LIBS%"
if errorlevel 1 exit /b 1
echo MELEE_PC_LINK_OK
