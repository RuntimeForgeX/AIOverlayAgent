@echo off
title App - Uninstall Shortcuts

cd /d "%~dp0"

set "APP_DIR=%~dp0"
set "APP_DIR=%APP_DIR:~0,-1%"

REM --- Read app branding from app_config.ini (single source of truth) ---
set "APP_NAME=PersonalAiAgentSurya"
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command ^
  "$ini = Join-Path '%APP_DIR%' 'app_config.ini';" ^
  "if (Test-Path $ini) {" ^
  "  $txt = Get-Content -Raw -Encoding UTF8 $ini;" ^
  "  $m = [regex]::Match($txt, '(?im)^\s*name\s*=\s*(.+)\s*$');" ^
  "  if ($m.Success) { $m.Groups[1].Value.Trim() }" ^
  "}"
`) do set "APP_NAME=%%i"

title %APP_NAME% - Uninstall Shortcuts

echo.
echo This removes Desktop / Start Menu / Startup shortcuts.
echo It does NOT delete the app folder or your .env file.
echo.

set /p CONFIRM="Remove shortcuts? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Cancelled.
    pause
    exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$names = @('%APP_NAME%', 'AI Overlay Agent');" ^
  "$desktopDir = [Environment]::GetFolderPath('Desktop');" ^
  "$programsDir = [Environment]::GetFolderPath('Programs');" ^
  "$startupDir = [Environment]::GetFolderPath('Startup');" ^
  "foreach ($n in $names) {" ^
  "  $desktop = Join-Path $desktopDir ($n + '.lnk');" ^
  "  $startup = Join-Path $startupDir ($n + '.lnk');" ^
  "  $startMenu = Join-Path $programsDir $n;" ^
  "  foreach ($p in @($desktop, $startup)) { if (Test-Path $p) { Remove-Item $p -Force; Write-Host ('Removed: ' + $p) } }" ^
  "  if (Test-Path $startMenu) { Remove-Item $startMenu -Recurse -Force; Write-Host ('Removed: ' + $startMenu) }" ^
  "}"

echo.
echo Done. App files are still in:
echo   %~dp0
echo.
pause
