@echo off
title CLAN Build System
echo.
echo ============================================================
echo   CLAN TRACKING SYSTEM  —  FULL BUILD
echo ============================================================
echo.
echo This will build:
echo   1. ClanTracking.exe        (Control Center)
echo   2. ClanDeviceSimulator.exe (Device Simulator)
echo   3. Installer packages      (requires Inno Setup)
echo.
echo Requirements:
echo   - Python installed
echo   - PyInstaller:  py -m pip install pyinstaller
echo   - Inno Setup 6: https://jrsoftware.org/isinfo.php
echo.
pause

:: ── Check PyInstaller ──────────────────────────────────────────
py -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    py -m pip install pyinstaller
)

:: ── Clean previous builds ─────────────────────────────────────
echo.
echo [1/6] Cleaning previous builds...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist
if exist installer_output rmdir /s /q installer_output
mkdir installer_output

:: ── Build main app ────────────────────────────────────────────
echo.
echo [2/6] Building ClanTracking (Control Center)...
py -m PyInstaller tracking_system.spec
if not exist "dist\ClanTracking\ClanTracking.exe" (
    echo ERROR: ClanTracking build failed!
    pause & exit /b 1
)
echo       OK - dist\ClanTracking\ClanTracking.exe

:: ── Build device simulator ────────────────────────────────────
echo.
echo [3/6] Building ClanDeviceSimulator...
py -m PyInstaller device_simulator.spec
if not exist "dist\ClanDeviceSimulator\ClanDeviceSimulator.exe" (
    echo ERROR: ClanDeviceSimulator build failed!
    pause & exit /b 1
)
echo       OK - dist\ClanDeviceSimulator\ClanDeviceSimulator.exe

:: ── Copy helper batch into simulator dist ─────────────────────
echo.
echo [4/6] Copying helper files...
copy run_simulator.bat "dist\ClanDeviceSimulator\" >nul

:: ── Build installers with Inno Setup ─────────────────────────
echo.
echo [5/6] Building installers with Inno Setup...

set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if %ISCC%=="" (
    echo.
    echo WARNING: Inno Setup not found. Skipping installer creation.
    echo          Download from: https://jrsoftware.org/isinfo.php
    echo          Then run manually:  iscc installer_app.iss
    echo                              iscc installer_simulator.iss
    goto :skip_installers
)

%ISCC% installer_app.iss
if errorlevel 1 ( echo ERROR: App installer failed! ) else ( echo       OK - installer_output\ClanTracking_v1.0_Setup.exe )

%ISCC% installer_simulator.iss
if errorlevel 1 ( echo ERROR: Simulator installer failed! ) else ( echo       OK - installer_output\ClanDeviceSimulator_v1.0_Setup.exe )

:skip_installers

:: ── Summary ───────────────────────────────────────────────────
echo.
echo [6/6] Build complete!
echo.
echo ============================================================
echo   OUTPUT FILES
echo ============================================================
echo.
echo   Portable (no install needed):
echo     dist\ClanTracking\ClanTracking.exe
echo     dist\ClanDeviceSimulator\ClanDeviceSimulator.exe
echo.
echo   Installers (if Inno Setup was found):
echo     installer_output\ClanTracking_v1.0_Setup.exe
echo     installer_output\ClanDeviceSimulator_v1.0_Setup.exe
echo.
echo   Share the installer EXE to deploy on any Windows PC.
echo   No Python required on the target machine.
echo ============================================================
echo.
pause
