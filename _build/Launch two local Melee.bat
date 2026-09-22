@echo off
rem Two copies of GD's Melee side by side for online testing on this PC:
rem   left = host (GameCube controller), right = guest (keyboard: WASD move, J select, K back).
rem Starts the matchmaking server on this PC if it isn't running, so room codes work.
rem Running it again closes the previous pair and opens a fresh one.

set "ROOT=C:\Users\Gurek\Desktop\GD's Melee"
powershell -NoProfile -Command "if (-not (Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*gdmelee_server*' })) { Start-Process python -ArgumentList ('\"' + '%ROOT%\tools\netplay\server\gdmelee_server.py' + '\"'), '--port', '51600' -WindowStyle Minimized }"
set "MELEE_NETPLAY_SERVER=127.0.0.1:51600"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\_build\netplay_local.ps1" -Menu -RealNetwork
