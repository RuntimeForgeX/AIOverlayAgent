@echo off
setlocal enableextensions enabledelayedexpansion

REM Builds a single-file Windows .exe using PyInstaller.
REM Output: dist\<exe name from app_config.ini>

cd /d %~dp0\..

if not exist .venv_build (
  py -3 -m venv .venv_build
)

call .venv_build\Scripts\activate.bat
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
python -m pip install pyinstaller -q

REM Remove old in-repo work folder (OneDrive often locks it)
py -3 build\prepare_pyinstaller.py

REM Work files in %%TEMP%% — avoids PermissionError under OneDrive project folder
set "PYI_WORK=%TEMP%\ai-overlay-agent-pyinstaller"
if not exist "%PYI_WORK%" mkdir "%PYI_WORK%"

echo.
echo Building... (work path: %PYI_WORK%)
echo Close PersonalAiAgentSurya.exe if the build fails with "Access is denied".
echo.

REM Do not use --clean: it tries to delete locked cache dirs and fails on Windows
pyinstaller --noconfirm ^
  --workpath "%PYI_WORK%\build" ^
  --distpath dist ^
  build\ai_overlay_agent.spec

if errorlevel 1 (
  echo.
  echo BUILD FAILED — see errors above.
  echo Tip: close the running app, wait a few seconds, run this script again.
  echo.
  pause
  exit /b 1
)

for /f "usebackq delims=" %%i in (`py -3 build\print_exe_name.py`) do set "EXE_NAME=%%i"

if not exist "dist\!EXE_NAME!" (
  echo.
  echo BUILD FAILED — dist\!EXE_NAME! was not created.
  echo.
  pause
  exit /b 1
)

echo.
echo Built: %CD%\dist\!EXE_NAME!
echo.
pause
