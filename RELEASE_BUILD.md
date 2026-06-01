# Release build (Windows installer .exe)

This project can be shipped as a normal Windows installer wizard (`Setup.exe`) without sharing source code.

## What you get

- **App exe**: `dist/<exe_base_name>.exe` (single-file, no console)
- **Installer**: `release/<name> Setup.exe` (standard Next/Next/Finish wizard)

## Prerequisites (on the build machine)

- Windows 10/11
- Python 3.10+
- Inno Setup 6+ (for the installer UI)
  - After installing, make sure `ISCC.exe` is on PATH (or run it by full path)

## Build steps

## Change the app name (for a new version)

Edit `app_config.ini` (this is the single source of truth for name/version/publisher). Then rebuild.

1) Build the app `.exe`:

- Run `build/build_exe.bat`

2) Build the installer wizard:

- Run `build/build_installer.bat`

## Where user data goes (important)

In packaged builds, the app stores writable files under:

- `%APPDATA%\PersonalAiAgentSurya\`
  - `exports\` (chat exports)
  - `.env` (API keys if the user chooses to create it)
  - `config.ini` (optional per-user override)

## About "hiding" the code

- Shipping an `.exe` (PyInstaller) **prevents casual users** from opening `.py` files.
- It does **not** guarantee perfect secrecy: determined attackers can reverse engineer.
- If you need stronger protection, consider compiling with **Nuitka** (C compilation) and code signing.
