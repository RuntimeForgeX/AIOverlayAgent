@echo off
REM Launch AI Overlay Agent (no console window)
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)

".venv\Scripts\pythonw.exe" ai_overlay.py
