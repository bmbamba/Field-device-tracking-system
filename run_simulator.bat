@echo off
title CLAN Device Simulator
echo ================================================
echo   CLAN Device Simulator v1.0
echo ================================================
echo.
echo Usage examples:
echo.
echo   Basic drive:
echo   ClanDeviceSimulator.exe --id DEV-0001 --name TOYOTA --type GROUND_VEHICLE
echo.
echo   With destination change after 10s:
echo   ClanDeviceSimulator.exe --id DEV-0001 --name TOYOTA --type GROUND_VEHICLE --newdest 500,400 --divert-after 10
echo.
echo   With route drift (triggers deviation alert):
echo   ClanDeviceSimulator.exe --id DEV-0001 --name TOYOTA --type GROUND_VEHICLE --drift
echo.
echo   Full test (drift + destination change):
echo   ClanDeviceSimulator.exe --id DEV-0001 --name TOYOTA --type GROUND_VEHICLE --newdest 500,400 --divert-after 8 --drift
echo.
echo ================================================
echo   Enter your command below (or close to cancel)
echo ================================================
echo.
set /p CMD="> ClanDeviceSimulator.exe "
ClanDeviceSimulator.exe %CMD%
pause
