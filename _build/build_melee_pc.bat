@echo off
rem Links melee-pc.exe from the gwtool-transformed game objects, the platform shims, and the
rem 32-bit Aurora/Dawn/SDL3 libraries built by build_aurora_melee.bat.
rem
rem The two response files are generated (see docs/DEVLOG.md): melee_link_objects.rsp lists every
rem out/*.obj and shimobj/*.obj, melee_link_libs.rsp mirrors the library set Aurora's own
rem "simple" example links with.
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" amd64_x86 >nul
if errorlevel 1 exit /b 1
cd /d C:\gdm\_build\ax86m
rem /BASE + /DYNAMICBASE:NO pin the image above ARAM's 16 MB so a game global's address can never
rem be mistaken for an ARAM offset (see gw_ar_addr in shim_ar.c), and make every run's addresses
rem reproducible so melee-pc.map RVAs match the crash log directly.
rem /OPT:NOICF because /INCREMENTAL:NO turns on identical-COMDAT folding, which makes several
rem thousand small game functions share one address and so report the wrong name when a crash
rem address is looked up in the map. /OPT:REF stays on.
link /nologo /OUT:..\melee-pc.exe /PDB:..\melee-pc.pdb /MAP:..\melee-pc.map /machine:X86 /INCREMENTAL:NO /subsystem:console /LARGEADDRESSAWARE /BASE:0x10000000 /DYNAMICBASE:NO /OPT:REF /OPT:NOICF ^
  @..\melee_link_objects.rsp @..\melee_link_libs.rsp
if errorlevel 1 exit /b 1
echo MELEE_PC_LINK_OK
