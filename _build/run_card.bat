@echo off
REM Memory card bring-up: enables the card and logs every CARD call with its result.
REM The log is preserved to card-last.log after each run (melee-pc.log is truncated on launch),
REM so a crash while creating/loading a save is not lost to the next run.
cd /d "%~dp0"
set MELEE_CARD=1
set MELEE_CARD_DIAG=1
"%~dp0melee-pc.exe" --iso "C:\iso\Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
if exist "%~dp0melee-pc.log" copy /y "%~dp0melee-pc.log" "%~dp0card-last.log" >nul
