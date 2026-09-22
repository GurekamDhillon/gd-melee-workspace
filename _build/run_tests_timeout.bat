@echo off
cd /d C:\gdm\_build
set MELEE_TEST_TIMEOUT=2
melee-pc.exe --test --iso "C:\iso\Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
echo EXITCODE=%ERRORLEVEL%
