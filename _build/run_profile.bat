@echo off
REM Frame profiler: per-frame timing split, percentiles and a histogram, every ~180 frames.
cd /d "%~dp0"
set MELEE_PROFILE=1
"%~dp0melee-pc.exe" --iso "C:\iso\Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
if exist "%~dp0melee-pc.log" copy /y "%~dp0melee-pc.log" "%~dp0profile-last.log" >nul
