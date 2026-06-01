@echo off
REM Launch app with console (for logs and troubleshooting)
cd /d "%~dp0"

set "APP_DIR=%~dp0"
set "APP_DIR=%APP_DIR:~0,-1%"
set "APP_NAME=PersonalAiAgentSurya"
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command ^
    "$ini = Join-Path '%APP_DIR%' 'app_config.ini';" ^
    "if (Test-Path $ini) {" ^
    "  $txt = Get-Content -Raw -Encoding UTF8 $ini;" ^
    "  $m = [regex]::Match($txt, '(?im)^\s*name\s*=\s*(.+)\s*$');" ^
    "  if ($m.Success) { $m.Groups[1].Value.Trim() }" ^
    "}"
`) do set "APP_NAME=%%i"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run install.bat first. (%APP_NAME%)
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python ai_overlay.py
pause
