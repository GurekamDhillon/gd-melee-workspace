@echo off
rem Package the current build for friends: Desktop\GDMelee-Online.zip (the game, the menu art, the
rem launchers and instructions - no disc data; each friend points it at their own ISO).
rem Uses _build\netplay_server.txt (your VPS "host:port") for room codes when that file exists.
rem It packages what is already built; rebuild first if you changed code.
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Gurek\Desktop\GD's Melee\tools\netplay\make_package.ps1"
echo.
pause
