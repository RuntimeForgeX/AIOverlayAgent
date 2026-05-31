@echo off
title AI Overlay Agent - Uninstall Shortcuts

cd /d "%~dp0"

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
  "$desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) 'AI Overlay Agent.lnk';" ^
  "$startMenu = Join-Path ([Environment]::GetFolderPath('Programs')) 'AI Overlay Agent';" ^
  "$startup = Join-Path ([Environment]::GetFolderPath('Startup')) 'AI Overlay Agent.lnk';" ^
  "foreach ($p in @($desktop, $startup)) { if (Test-Path $p) { Remove-Item $p -Force; Write-Host ('Removed: ' + $p) } };" ^
  "if (Test-Path $startMenu) { Remove-Item $startMenu -Recurse -Force; Write-Host ('Removed: ' + $startMenu) }"

echo.
echo Done. App files are still in:
echo   %~dp0
echo.
pause
