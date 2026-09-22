@echo off
rem Package the current build for friends: Desktop\GDMelee-Online.zip. This is the public release
rem (tools\release\build_release.ps1: game, launcher "GD Melee.exe", menu art, docs, licences - no
rem disc data, no save files) with your matchmaking server from _build\netplay_server.txt filled in.
rem Each friend runs "GD Melee.exe" and points it at their own ISO.
rem It packages what is already built; rebuild first if you changed code.
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Gurek\Desktop\GD's Melee\tools\netplay\make_package.ps1"
echo.
pause
