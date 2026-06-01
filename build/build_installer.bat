@echo off
setlocal enableextensions enabledelayedexpansion

REM Builds the installer wizard (Setup.exe) using Inno Setup.
REM Prereq: Inno Setup installed (iscc.exe on PATH).

cd /d %~dp0\..

REM Sync installer branding/version from app_config.ini
py -3 build\sync_inno_config.py
if errorlevel 1 (
  echo Failed to generate installer\app_config.issinc
  pause
  exit /b 1
)

for /f "usebackq delims=" %%i in (`py -3 build\print_exe_name.py`) do set EXE_NAME=%%i

if not exist dist\%EXE_NAME% (
  echo Missing dist\%EXE_NAME%
  echo Run build\build_exe.bat first.
  pause
  exit /b 1
)

set "ISCC_PATH1=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
set "ISCC_PATH2=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if exist "!ISCC_PATH1!" (
  set "ISCC=!ISCC_PATH1!"
) else if exist "!ISCC_PATH2!" (
  set "ISCC=!ISCC_PATH2!"
) else (
  echo Inno Setup Compiler not found.
  echo Install Inno Setup using: winget install -e --id JRSoftware.InnoSetup
  echo Then restart your terminal.
  pause
  exit /b 1
)

"!ISCC!" "installer\AIOverlayAgent.iss"
if errorlevel 1 (
  echo.
  echo Installer build failed. See errors above.
  pause
  exit /b 1
)

echo.
echo Built installer(s) under: %CD%\release
echo.
pause
