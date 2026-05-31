@echo off
REM Launch AI Overlay Agent with console (for logs and troubleshooting)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python ai_overlay.py
pause
