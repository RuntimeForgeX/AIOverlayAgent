@echo off
setlocal enableextensions enabledelayedexpansion

REM Debug version: Build the installer wizard (Setup.exe) using Inno Setup
REM This version shows detailed error messages

title Building AI Overlay Agent Installer...

cd /d %~dp0\..

echo.
echo ========================================
echo   AI Overlay Agent - Installer Builder
echo   DEBUG VERSION (Shows All Errors)
echo ========================================
echo.
echo Working directory: %CD%
echo.

REM Check if we're in the right place
if not exist "build\sync_inno_config.py" (
  echo ERROR: build\sync_inno_config.py not found!
  echo Make sure you're running from the project root folder.
  pause
  exit /b 1
)

REM Sync installer branding/version from app_config.ini
echo [STEP 1] Syncing app config...
py -3 build\sync_inno_config.py 2>&1
if errorlevel 1 (
  echo.
  echo ERROR: Failed to generate installer\app_config.issinc
  echo This usually means:
  echo   - Python is not installed or not on PATH
  echo   - app_config.ini is missing or corrupted
  echo   - Permission issues
  echo.
  pause
  exit /b 1
)
echo [OK] Config synced
echo.

REM Get executable name
echo [STEP 2] Determining executable name...
for /f "usebackq delims=" %%i in (`py -3 build\print_exe_name.py 2^>nul`) do set "EXE_NAME=%%i"
if "!EXE_NAME!"=="" (
  echo ERROR: Could not determine executable name
  pause
  exit /b 1
)
echo [OK] Executable: !EXE_NAME!
echo.

REM Check if exe exists
echo [STEP 3] Checking for built executable...
if not exist "dist\!EXE_NAME!" (
  echo ERROR: Missing dist\!EXE_NAME!
  echo.
  echo SOLUTION: You must build the .exe first!
  echo Run this command:
  echo    build\build_exe.bat
  echo.
  echo Then try this installer builder again.
  pause
  exit /b 1
)
echo [OK] Found: dist\!EXE_NAME!
echo.

REM Check for Inno Setup
echo [STEP 4] Checking for Inno Setup Compiler...

set "ISCC_PATH1=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
set "ISCC_PATH2=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if exist "!ISCC_PATH1!" (
  set "ISCC=!ISCC_PATH1!"
  echo [OK] Found ISCC at: !ISCC!
) else if exist "!ISCC_PATH2!" (
  set "ISCC=!ISCC_PATH2!"
  echo [OK] Found ISCC at: !ISCC!
) else (
  echo ERROR: ISCC.exe not found
  echo.
  echo SOLUTION: Install Inno Setup
  echo   Run in PowerShell:
  echo   winget install -e --id JRSoftware.InnoSetup
  echo.
  echo   Then restart your terminal
  echo.
  pause
  exit /b 1
)
echo.

REM Check installer script
echo [STEP 5] Checking installer script...
if not exist "installer\AIOverlayAgent.iss" (
  echo ERROR: installer\AIOverlayAgent.iss not found
  pause
  exit /b 1
)
echo [OK] Found installer\AIOverlayAgent.iss
echo.

REM Build the installer
echo [STEP 6] Building installer...
echo ========================================
"!ISCC!" "installer\AIOverlayAgent.iss"
if errorlevel 1 (
  echo.
  echo ERROR: ISCC.exe returned an error
  echo Check the messages above for details
  pause
  exit /b 1
)
echo ========================================
echo.
echo [SUCCESS] Installer built!
echo.
echo.
echo ========================================
echo   ✓ INSTALLER CREATED SUCCESSFULLY!
echo ========================================
echo.
echo Location: %CD%\release\PersonalAiAgentSurya_Setup.exe
echo.
echo Next steps:
echo   1. Test the installer:
echo      release\PersonalAiAgentSurya_Setup.exe
echo.
echo   2. Go through the wizard:
echo      - Accept license
echo      - Choose installation folder
echo      - Select optional features
echo      - Click Install
echo.
echo   3. Verify shortcuts were created
echo.
echo   4. Test the installed application
echo.
echo ========================================
echo.
pause
