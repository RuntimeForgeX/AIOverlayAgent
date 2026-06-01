@echo off
setlocal EnableDelayedExpansion
title App - Install

cd /d "%~dp0"
set "APP_DIR=%~dp0"
set "APP_DIR=%APP_DIR:~0,-1%"
set "PYTHON="
set "PIP="

REM --- Read app branding from app_config.ini (single source of truth) ---
set "APP_NAME=PersonalAiAgentSurya"
set "EXE_BASE_NAME=PersonalAiAgentSurya"
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command ^
    "$ini = Join-Path '%APP_DIR%' 'app_config.ini';" ^
    "if (Test-Path $ini) {" ^
    "  $txt = Get-Content -Raw -Encoding UTF8 $ini;" ^
    "  $m = [regex]::Match($txt, '(?im)^\s*name\s*=\s*(.+)\s*$');" ^
    "  if ($m.Success) { $m.Groups[1].Value.Trim() }" ^
    "}"
`) do set "APP_NAME=%%i"

for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command ^
    "$ini = Join-Path '%APP_DIR%' 'app_config.ini';" ^
    "if (Test-Path $ini) {" ^
    "  $txt = Get-Content -Raw -Encoding UTF8 $ini;" ^
    "  $m = [regex]::Match($txt, '(?im)^\s*exe_base_name\s*=\s*(.+)\s*$');" ^
    "  if ($m.Success) { $m.Groups[1].Value.Trim() }" ^
    "}"
`) do set "EXE_BASE_NAME=%%i"

set "EXE_NAME=%EXE_BASE_NAME%.exe"
set "PACKAGED_EXE="
if exist "%APP_DIR%\%EXE_NAME%" set "PACKAGED_EXE=%APP_DIR%\%EXE_NAME%"
if exist "%APP_DIR%\dist\%EXE_NAME%" set "PACKAGED_EXE=%APP_DIR%\dist\%EXE_NAME%"

title %APP_NAME% - Install

echo.
echo ========================================
echo   %APP_NAME% - Windows Install
echo ========================================
echo.
echo Install folder: %APP_DIR%
echo.

REM If a packaged exe exists, we can install shortcuts without Python.
if defined PACKAGED_EXE (
    echo [OK] Found packaged executable:
    echo       %PACKAGED_EXE%
    echo.
    goto :install_shortcuts_exe
)

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
exit /b 0
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
    "$startMenu = Join-Path ([Environment]::GetFolderPath('Programs')) '%APP_NAME%';" ^
  "New-Item -ItemType Directory -Force -Path $startMenu | Out-Null;" ^
    "$s1 = $shell.CreateShortcut((Join-Path $desktop ('%APP_NAME%' + '.lnk')));" ^
    "$s1.TargetPath = $pythonw; $s1.Arguments = '\"' + $script + '\"'; $s1.WorkingDirectory = $appDir; $s1.Description = '%APP_NAME%'; $s1.Save();" ^
    "$s2 = $shell.CreateShortcut((Join-Path $startMenu ('%APP_NAME%' + '.lnk')));" ^
    "$s2.TargetPath = $pythonw; $s2.Arguments = '\"' + $script + '\"'; $s2.WorkingDirectory = $appDir; $s2.Description = '%APP_NAME%'; $s2.Save();" ^
    "if (Test-Path $debugBat) {" ^
    "  $s3 = $shell.CreateShortcut((Join-Path $startMenu ('%APP_NAME% (Debug).lnk')));" ^
    "  $s3.TargetPath = $debugBat; $s3.WorkingDirectory = $appDir; $s3.Description = '%APP_NAME% with console logs'; $s3.Save();" ^
    "}"

if errorlevel 1 (
    echo [WARN] Could not create shortcuts. You can still run run.bat manually.
) else (
    echo [OK] Desktop shortcut created: %APP_NAME%
    echo [OK] Start Menu folder created: %APP_NAME%
)
echo.

REM --- Optional: start with Windows ---
set /p STARTUP="Start %APP_NAME% when Windows starts? (Y/N): "
if /i "%STARTUP%"=="Y" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$appDir = '%APP_DIR%';" ^
      "$pythonw = Join-Path $appDir '.venv\Scripts\pythonw.exe';" ^
      "$script = Join-Path $appDir 'ai_overlay.py';" ^
      "$startup = [Environment]::GetFolderPath('Startup');" ^
      "$shell = New-Object -ComObject WScript.Shell;" ^
            "$s = $shell.CreateShortcut((Join-Path $startup ('%APP_NAME%' + '.lnk')));" ^
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
echo   2. Double-click "%APP_NAME%" on Desktop
echo   3. Use Ctrl+Shift+Space to show/hide the overlay
echo.
echo Optional: edit config.ini for model, hotkeys, window size.
echo.
pause
exit /b 0


:install_shortcuts_exe
echo Creating shortcuts (EXE mode)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$appDir = '%APP_DIR%';" ^
    "$exe = '%PACKAGED_EXE%';" ^
    "$shell = New-Object -ComObject WScript.Shell;" ^
    "$desktop = [Environment]::GetFolderPath('Desktop');" ^
    "$startMenu = Join-Path ([Environment]::GetFolderPath('Programs')) '%APP_NAME%';" ^
    "New-Item -ItemType Directory -Force -Path $startMenu | Out-Null;" ^
    "$s1 = $shell.CreateShortcut((Join-Path $desktop ('%APP_NAME%' + '.lnk')));" ^
    "$s1.TargetPath = $exe; $s1.WorkingDirectory = (Split-Path $exe -Parent); $s1.Description = '%APP_NAME%'; $s1.Save();" ^
    "$s2 = $shell.CreateShortcut((Join-Path $startMenu ('%APP_NAME%' + '.lnk')));" ^
    "$s2.TargetPath = $exe; $s2.WorkingDirectory = (Split-Path $exe -Parent); $s2.Description = '%APP_NAME%'; $s2.Save();"

if errorlevel 1 (
        echo [WARN] Could not create shortcuts.
) else (
        echo [OK] Desktop shortcut created: %APP_NAME%
        echo [OK] Start Menu folder created: %APP_NAME%
)

set /p STARTUP="Start %APP_NAME% when Windows starts? (Y/N): "
if /i "%STARTUP%"=="Y" (
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
            "$appDir = '%APP_DIR%';" ^
            "$exe = '%PACKAGED_EXE%';" ^
            "$startup = [Environment]::GetFolderPath('Startup');" ^
            "$shell = New-Object -ComObject WScript.Shell;" ^
            "$s = $shell.CreateShortcut((Join-Path $startup ('%APP_NAME%' + '.lnk')));" ^
            "$s.TargetPath = $exe; $s.WorkingDirectory = (Split-Path $exe -Parent); $s.Save();"
        echo [OK] Added to Windows Startup.
) else (
        echo Skipped startup entry.
)

echo.
echo ========================================
echo   Installation complete (EXE mode)
echo ========================================
echo.
echo Next steps:
echo   1. Copy .env.example to .env (optional) and add your API key
echo   2. Double-click "%APP_NAME%" on Desktop
echo.
pause
