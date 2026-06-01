# Professional Windows Installer Build Guide

## Overview
This guide will help you create a professional .exe installer (like Git, VSCode, etc.) that end-users can double-click to install the AI Overlay Agent.

## Prerequisites

Before you start, ensure you have:

1. **Inno Setup 6 or later**
   - Download: https://jrsoftware.org/isdl.php
   - During installation, check "Install Inno Setup Compiler (ISCC.exe)"
   - This puts `ISCC.exe` on your PATH

2. **Python 3.10+ with pip**
   - Required for building the executable

3. **PyInstaller**
   - Used to bundle Python app into single .exe file
   - Already listed in requirements_build.txt

## Build Process (Step-by-Step)

### Step 1: Prepare Your Application

```bash
# Navigate to project root
cd c:\Users\surya\OneDrive\Desktop\personalAgent\ai-overlay-agent

# Install build dependencies
pip install -r requirements_build.txt
```

### Step 2: Update App Configuration (if needed)

Edit `app_config.ini` to set:
- App name
- Version number
- Publisher name
- Executable name

Example:
```ini
[app]
name=PersonalAiAgentSurya
version=1.0.0
exe_base_name=PersonalAiAgentSurya
publisher=YourName
```

### Step 3: Build the Application EXE

```bash
# Run the build script
build/build_exe.bat
```

This creates:
- `dist/PersonalAiAgentSurya.exe` (your packaged application)

**What it does:**
- Bundles Python interpreter with your app
- Creates single .exe file (no Python installation required for users)
- Single-file, no console window
- Takes 2-5 minutes

### Step 4: Build the Installer

```bash
# Run the installer builder
build/build_installer.bat
```

This creates:
- `release/PersonalAiAgentSurya_Setup.exe` (distribution installer)

**What it does:**
- Generates app_config.issinc from app_config.ini (automatic version sync)
- Compiles the Inno Setup script (AIOverlayAgent.iss)
- Creates standard Windows installer wizard UI
- Takes 30 seconds to 2 minutes

### Step 5: Test the Installer

```bash
# Run the installer
release/PersonalAiAgentSurya_Setup.exe
```

Walk through the installer:
- ✓ Review License & Post-Install Information
- ✓ Choose installation directory
- ✓ Select optional features (Desktop icon, Start Menu, Startup, etc.)
- ✓ Verify app launches after installation
- ✓ Check shortcuts were created correctly
- ✓ Run the installed app

Test uninstall:
```
Settings > Apps > Apps & Features > PersonalAiAgentSurya > Uninstall
```

## What Users See

### The Installer Shows:
1. **Welcome Screen** - Project name and description
2. **License Agreement** - LICENSE.txt content
3. **Installation Folder** - Default: `C:\Program Files\PersonalAiAgentSurya`
4. **Installation Options** - Choose shortcuts and features
5. **Pre-Installation Notes** - USAGE_GUIDELINES.txt
6. **Progress Bar** - Extracting and installing files
7. **Post-Installation Info** - Setup next steps (API key, documentation)
8. **Launch Button** - Optional: Run app immediately

### After Installation, Users Get:
- **Desktop Shortcut** ✓
- **Start Menu Entry** ✓ 
  - Shortcuts for: App, Documentation, Configuration, Setup API Key, Uninstall
- **Quick Launch Icon** (optional) ✓
- **Startup Shortcut** (optional) ✓
- **Uninstaller** in Add/Remove Programs ✓

## Installer Features (Like Professional Apps)

✓ Modern Windows 10/11 UI style  
✓ License agreement screen  
✓ Custom installation options  
✓ Desktop and Start Menu shortcuts  
✓ Startup folder support  
✓ Registry entries (Programs and Features)  
✓ Built-in uninstaller  
✓ Documentation and config shortcuts  
✓ Post-install instructions  
✓ Works on Windows 10 (2004+) and Windows 11  

## Distributing Your App

### For End Users:

1. **Single Installer File**
   - Share: `release/PersonalAiAgentSurya_Setup.exe` (15-50 MB)
   - Do NOT share the entire project folder
   - Do NOT share source code

2. **Installation Instructions**
   ```
   1. Double-click PersonalAiAgentSurya_Setup.exe
   2. Click Next through the wizard
   3. Choose installation options
   4. Click Install
   5. After installation, add your API key to .env file
   6. Launch from Desktop or Start Menu
   ```

3. **Hosting Options**
   - GitHub Releases
   - Your website
   - Cloud storage (OneDrive, Google Drive)
   - Software distribution platforms

### Installer Size:
- PyInstaller bundle: ~100-200 MB (includes Python)
- Inno Setup compressed: ~60-120 MB (after LZMA compression)
- Downloads faster, minimal user bandwidth

## Troubleshooting

### "ISCC.exe not found" when building installer

**Solution:** Install Inno Setup and verify ISCC.exe is on PATH:
```powershell
# Check if it's installed
where iscc

# If not found, add to PATH or run full path:
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\AIOverlayAgent.iss
```

### Missing .exe file when building installer

**Solution:** Build the app first:
```bash
build/build_exe.bat
```

### Installer says "Python not found"

This only happens with old system-based installers. Your PyInstaller bundle includes Python, so this shouldn't occur. If it does:
- Rebuild with: `build/build_exe.bat`
- Ensure PyInstaller completed successfully

### App crashes after installation

Ensure:
1. API key is properly set in .env file
2. Required dependencies are listed in requirements.txt
3. Check app logs in `%APPDATA%\PersonalAiAgentSurya\`

## Advanced Customization

### Adding Custom Graphics
Edit `installer/AIOverlayAgent.iss`:

```ini
; Add logo image
WizardImageFile=installer\logo.bmp
WizardSmallImageFile=installer\small_logo.bmp

; Inno Setup recommended sizes:
; WizardImageFile: 164x314 pixels
; WizardSmallImageFile: 55x57 pixels
```

### Modifying Installer Text
Edit installer messages in `[Messages]` section of AIOverlayAgent.iss

### Registry Customization
Edit `[Registry]` section to add your own registry entries

## Files Included in Installer

- `PersonalAiAgentSurya.exe` - Main application
- `config.ini` - Configuration template
- `app_config.ini` - App metadata (name, version, etc.)
- `.env.example` - API key template
- `README.md` - Documentation
- `PRIVACY.md` - Privacy information
- `QUICK_TEST.md` - Quick start guide
- `LICENSE.txt` - License agreement
- `POST_INSTALL_INFO.txt` - Installation instructions

## Environment Variables & Registry

After installation:

```
Installation path registry:
  HKEY_CURRENT_USER\Software\PersonalAiAgentSurya\InstallPath

User data stored in:
  %APPDATA%\PersonalAiAgentSurya\
    ├── config.ini (optional user override)
    ├── .env (API keys)
    └── exports/ (chat exports)
```

## Version Updates

When you want to release a new version:

1. Update `app_config.ini`:
   ```ini
   version=1.1.0
   ```

2. Rebuild:
   ```bash
   build/build_exe.bat
   build/build_installer.bat
   ```

3. New installer filename includes version:
   ```
   release/PersonalAiAgentSurya_Setup.exe
   ```

Users can install multiple versions side-by-side (each gets its own folder).

## Security Notes

The .exe installer:
- Does NOT require administrator privileges (unless you set `PrivilegesRequired=admin`)
- Does NOT modify system files
- Stores user data in user AppData folder (not system-wide)
- Can be uninstalled cleanly via Programs and Features
- Does NOT add to system PATH (safe from malware perspective)

## Performance Notes

- First install: 1-2 minutes (file extraction and setup)
- Updates: 30 seconds (differential install available in advanced setups)
- Uninstall: 10-30 seconds

---

**Ready to distribute?** Follow this workflow:

```
1. Edit app_config.ini (version bump)
2. Run: build/build_exe.bat
3. Run: build/build_installer.bat
4. Test: release/PersonalAiAgentSurya_Setup.exe
5. Share: release/PersonalAiAgentSurya_Setup.exe
```

That's it! Your app is ready for distribution like any professional Windows application.
