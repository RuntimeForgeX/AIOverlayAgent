# Release Build Guide

How to produce a production **`.exe`** and Windows **installer** for AI Overlay Agent.

---

## Prerequisites

1. **Python 3.10+** with `py` launcher on PATH  
2. **Inno Setup 6** — install with:
   ```bat
   winget install -e --id JRSoftware.InnoSetup
   ```
   Default path: `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`  
3. Close any running `PersonalAiAgentSurya.exe` before rebuilding  
4. Optional: pause OneDrive sync on the project folder if PyInstaller reports file locks

---

## One-command flow

From the project root:

```bat
build\build_exe.bat
build\build_installer.bat
```

**Outputs:**

| File | Location |
|------|----------|
| Standalone app | `dist\PersonalAiAgentSurya.exe` |
| Installer | `release\PersonalAiAgentSurya_Setup.exe` |

---

## Step 1 — Build the executable

```bat
build\build_exe.bat
```

This script:

1. Creates/uses `.venv_build`
2. Installs `requirements.txt` + PyInstaller
3. Runs `build\prepare_pyinstaller.py` (cleans old `pyinstaller_build` if possible)
4. Runs PyInstaller with `build\ai_overlay_agent.spec`
   - Entry: `main.py`
   - Work path: `%TEMP%\ai-overlay-agent-pyinstaller`
   - `console=False` (no console window)
   - `runtime_keyboard_fix.py` for hotkeys

**Success:** prints `Built: ...\dist\PersonalAiAgentSurya.exe`

**Failure:** if you see `PermissionError` on `pyinstaller_build`, close the app and retry; the build uses TEMP for work files but may still need to delete a locked folder manually.

---

## Step 2 — Build the installer

```bat
build\build_installer.bat
```

This script:

1. Runs `py -3 build\sync_inno_config.py` (updates `installer\app_config.issinc` from `app_config.ini`)
2. Verifies `dist\PersonalAiAgentSurya.exe` exists
3. Locates `ISCC.exe` (Inno Setup)
4. Compiles `installer\AIOverlayAgent.iss`

**Important:** `build_installer.bat` must quote paths to ISCC when the path contains spaces (e.g. `Inno Setup 6`).

**Debug build** (verbose Inno log):

```bat
build\build_installer_DEBUG.bat
```

---

## Step 3 — Test the release

1. Run `release\PersonalAiAgentSurya_Setup.exe`
2. Complete the wizard (license, folder, shortcuts)
3. Set API key (Windows env var or `.env` next to install / in AppData)
4. Launch from Desktop or Start Menu
5. Verify:
   - [ ] App opens without system error dialogs
   - [ ] Hotkeys work (`Ctrl+Shift+Space`, `Ctrl+Shift+S`, etc.)
   - [ ] Model dropdown switches without errors
   - [ ] Chat + screenshot capture work with valid API key
   - [ ] Overlay hidden in OBS/Meet full-screen share ([INVISIBILITY_TEST.md](INVISIBILITY_TEST.md))

---

## Rebranding a new build

Edit `app_config.ini`:

```ini
[APP]
name = YourAppName
appdata_folder = YourAppName
window_title = YOUR TITLE

[BUILD]
exe_base_name = YourAppName
publisher = Your Company
version = 1.0.1
app_id_guid = {NEW-GUID-HERE}   ; only if you want a separate product line
```

Then rebuild both exe and installer. Change `app_id_guid` only when you intentionally want a side-by-side install (not an upgrade).

---

## Version bump checklist

- [ ] Update `version` in `app_config.ini`
- [ ] Run `build\build_exe.bat`
- [ ] Run `build\build_installer.bat`
- [ ] Test install on a clean VM or second user account
- [ ] Test upgrade over previous installer (same `app_id_guid`)
- [ ] Tag git release with version number

---

## What gets installed

Typical per-user install location:

`%LOCALAPPDATA%\Programs\PersonalAiAgentSurya\`

Includes: `PersonalAiAgentSurya.exe`, `config.ini`, docs, `.env.example`, uninstaller.

User data: `%APPDATA%\PersonalAiAgentSurya\`

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `python` not found | Scripts use `py -3`; install Python 3.10+ |
| Inno Setup not found | Install Inno Setup; restart terminal |
| `You may not specify more than one script filename` | Quote `ISCC` path in `build_installer.bat` |
| `Missing dist\...exe` | Run `build_exe.bat` first |
| Hotkeys dead in exe only | Rebuild with latest spec + `runtime_keyboard_fix.py` |
| HKLM registry fails on install | Installer uses per-user (`PrivilegesRequired=lowest`) — expected |

---

## See also

- [QUICK_BUILD.txt](QUICK_BUILD.txt) — minimal command list  
- [BUILD_SUMMARY.md](BUILD_SUMMARY.md) — architecture summary
