@echo off
REM Diagnostic launch: disables Aurora's consecutive-draw merging.
set MELEE_NO_MERGE=1
"%~dp0melee-pc.exe" --iso "C:\iso\Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
