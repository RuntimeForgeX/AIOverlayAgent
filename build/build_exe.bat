@echo off
setlocal enableextensions

REM Builds a single-file Windows .exe using PyInstaller.
REM Output: dist\<exe name from app_config.ini>

cd /d %~dp0\..

if not exist .venv_build (
  py -3 -m venv .venv_build
)

call .venv_build\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

pyinstaller --noconfirm --clean --workpath pyinstaller_build --distpath dist build\ai_overlay_agent.spec

for /f "usebackq delims=" %%i in (`python build\print_exe_name.py`) do set EXE_NAME=%%i
echo.
echo Built: %CD%\dist\%EXE_NAME%
echo.
pause
