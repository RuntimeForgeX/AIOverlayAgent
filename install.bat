@echo off
setlocal EnableDelayedExpansion
title AI Overlay Agent - Install

cd /d "%~dp0"
set "APP_DIR=%~dp0"
set "APP_DIR=%APP_DIR:~0,-1%"
set "PYTHON="
set "PIP="

echo.
echo ========================================
echo   AI Overlay Agent - Windows Install
echo ========================================
echo.
echo Install folder: %APP_DIR%
echo.

REM --- Find Python (venv first, then system) ---
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
    set "PIP=.venv\Scripts\pip.exe"
    goto :found_python
)

REM py launcher
where py >nul 2>&1
if not errorlevel 1 (
    py -3 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON=py -3"
        goto :found_python
    )
)

REM python on PATH — skip Windows Store stub in WindowsApps
where python >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%p in ('where python 2^>nul') do (
        echo %%p | findstr /i "\\WindowsApps\\" >nul
        if errorlevel 1 (
            "%%p" --version >nul 2>&1
            if not errorlevel 1 (
                set "PYTHON=%%p"
                goto :found_python
            )
        )
    )
)

REM Common install folders
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%d\python.exe" (
        set "PYTHON=%%d\python.exe"
        goto :found_python
    )
)
for /d %%d in ("C:\Python*") do (
    if exist "%%d\python.exe" (
        set "PYTHON=%%d\python.exe"
        goto :found_python
    )
)

REM PowerShell search (excludes WindowsApps stub)
for /f "delims=" %%p in ('powershell -NoProfile -Command ^
  "$c=@();" ^
  "$c+=Get-ChildItem -Path \"$env:LOCALAPPDATA\\Programs\\Python\" -Filter python.exe -Recurse -ErrorAction SilentlyContinue;" ^
  "$c+=Get-ChildItem -Path \"C:\\Program Files\\Python*\" -Filter python.exe -Recurse -ErrorAction SilentlyContinue;" ^
  "$c+=Get-Command python -ErrorAction SilentlyContinue | Where-Object { $_.Source -notmatch 'WindowsApps' } | ForEach-Object { Get-Item $_.Source };" ^
  "$p=$c | Select-Object -First 1 -ExpandProperty FullName;" ^
  "if ($p) { Write-Output $p }"') do (
    set "PYTHON=%%p"
    goto :found_python
)

echo [ERROR] Python 3.10+ not found.
echo.
echo The Windows Store "python" shortcut is not a real install.
echo.
echo Fix options:
echo   1. Install Python from https://www.python.org/downloads/
echo      ^(check "Add python.exe to PATH" during install^)
echo   2. Or if .venv was deleted, restore this folder from backup
echo.
pause
exit /b 1

:found_python
for /f "tokens=*" %%v in ('"%PYTHON%" --version 2^>^&1') do set PYVER=%%v
echo [OK] Using !PYVER!
echo       Path: !PYTHON!
echo.

REM --- Virtual environment ---
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    "%PYTHON%" -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)
echo.

set "PYTHON=.venv\Scripts\python.exe"
set "PIP=.venv\Scripts\pip.exe"

REM --- Dependencies ---
echo Installing dependencies (may take a few minutes)...
"%PYTHON%" -m pip install --upgrade pip >nul
"%PIP%" install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.
echo.

REM --- Environment file ---
if not exist ".env" (
    copy /Y ".env.example" ".env" >nul
    echo [OK] Created .env from .env.example
    echo       ^> Open .env and add your API key before first run.
) else (
    echo [OK] .env already exists.
)
echo.

REM --- Desktop + Start Menu shortcuts ---
echo Creating shortcuts...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$appDir = '%APP_DIR%';" ^
  "$pythonw = Join-Path $appDir '.venv\Scripts\pythonw.exe';" ^
  "$script = Join-Path $appDir 'ai_overlay.py';" ^
  "$debugBat = Join-Path $appDir 'run_debug.bat';" ^
  "$shell = New-Object -ComObject WScript.Shell;" ^
  "$desktop = [Environment]::GetFolderPath('Desktop');" ^
  "$startMenu = Join-Path ([Environment]::GetFolderPath('Programs')) 'AI Overlay Agent';" ^
  "New-Item -ItemType Directory -Force -Path $startMenu | Out-Null;" ^
  "$s1 = $shell.CreateShortcut((Join-Path $desktop 'AI Overlay Agent.lnk'));" ^
  "$s1.TargetPath = $pythonw; $s1.Arguments = '\"' + $script + '\"'; $s1.WorkingDirectory = $appDir; $s1.Description = 'AI Overlay Agent'; $s1.Save();" ^
  "$s2 = $shell.CreateShortcut((Join-Path $startMenu 'AI Overlay Agent.lnk'));" ^
  "$s2.TargetPath = $pythonw; $s2.Arguments = '\"' + $script + '\"'; $s2.WorkingDirectory = $appDir; $s2.Description = 'AI Overlay Agent'; $s2.Save();" ^
  "$s3 = $shell.CreateShortcut((Join-Path $startMenu 'AI Overlay Agent (Debug).lnk'));" ^
  "$s3.TargetPath = $debugBat; $s3.WorkingDirectory = $appDir; $s3.Description = 'AI Overlay Agent with console logs'; $s3.Save();"

if errorlevel 1 (
    echo [WARN] Could not create shortcuts. You can still run run.bat manually.
) else (
    echo [OK] Desktop shortcut created: AI Overlay Agent
    echo [OK] Start Menu folder created: AI Overlay Agent
)
echo.

REM --- Optional: start with Windows ---
set /p STARTUP="Start AI Overlay Agent when Windows starts? (Y/N): "
if /i "%STARTUP%"=="Y" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$appDir = '%APP_DIR%';" ^
      "$pythonw = Join-Path $appDir '.venv\Scripts\pythonw.exe';" ^
      "$script = Join-Path $appDir 'ai_overlay.py';" ^
      "$startup = [Environment]::GetFolderPath('Startup');" ^
      "$shell = New-Object -ComObject WScript.Shell;" ^
      "$s = $shell.CreateShortcut((Join-Path $startup 'AI Overlay Agent.lnk'));" ^
      "$s.TargetPath = $pythonw; $s.Arguments = '\"' + $script + '\"'; $s.WorkingDirectory = $appDir; $s.Save();"
    echo [OK] Added to Windows Startup.
) else (
    echo Skipped startup entry.
)
echo.

echo ========================================
echo   Installation complete
echo ========================================
echo.
echo Next steps:
echo   1. Edit .env and add your API key
echo   2. Double-click "AI Overlay Agent" on Desktop
echo   3. Use Ctrl+Shift+Space to show/hide the overlay
echo.
echo Optional: edit config.ini for model, hotkeys, window size.
echo.
pause
