@echo off
taskkill /IM melee-pc.exe /F >nul 2>&1
cd /d C:\gdm\_build
set MELEE_CARD=1
start "" "C:\gdm\_build\melee-pc.exe" --iso "C:\iso\Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
