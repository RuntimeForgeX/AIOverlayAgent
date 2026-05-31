# Install AI Overlay Agent on Windows

Complete guide to install and run **AI Overlay Agent** as a desktop app on your system — with Desktop shortcut, Start Menu entry, and optional startup on boot.

---

## What you get after install

- **Desktop shortcut** — `AI Overlay Agent`
- **Start Menu folder** — `AI Overlay Agent`
  - `AI Overlay Agent` — normal launch (no terminal window)
  - `AI Overlay Agent (Debug)` — launch with console logs
- **Optional** — starts automatically when Windows boots
- **Privacy** — overlay is hidden from Google Meet, OBS, Zoom, Teams screen capture

---

## Requirements

| Requirement | Details |
|-------------|---------|
| OS | Windows 10 version 2004+ or Windows 11 |
| Python | 3.10 or higher |
| Internet | Required for AI API calls |
| API key | Anthropic, OpenAI, or Google Gemini |

---

## Step 1 — Install Python (if not already installed)

1. Download Python from [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Run the installer
3. **Important:** check **"Add python.exe to PATH"** at the bottom of the first screen
4. Click **Install Now**
5. Verify in Command Prompt or PowerShell:

   ```bat
   python --version
   ```

   You should see `Python 3.10.x` or higher.

> **Windows Store stub:** If `python --version` opens the Microsoft Store or fails, you don't have real Python on PATH. Either install from python.org (below), or if this project already has a `.venv` folder, just run `install.bat` — it will use the existing virtual environment automatically.

---

## Step 2 — Copy the app to a permanent folder

Do **not** leave the project in Downloads or a temp folder. Shortcuts point to this path permanently.

**Recommended locations:**

```
C:\Apps\ai-overlay-agent
C:\Users\YourName\Apps\ai-overlay-agent
```

**How to copy:**

- **If you downloaded a ZIP:** extract it to the folder above
- **If you use Git:**

  ```bat
  git clone <repo-url> C:\Apps\ai-overlay-agent
  cd C:\Apps\ai-overlay-agent
  ```

> **Note:** If the project is in OneDrive (e.g. `Desktop\personalAgent\ai-overlay-agent`), that works — just don’t move or delete the folder after install, or shortcuts will break.

---

## Step 3 — Run the installer

1. Open the app folder in File Explorer
2. Double-click **`install.bat`**
3. Wait while it:
   - Checks Python
   - Creates a virtual environment (`.venv`)
   - Installs Python packages from `requirements.txt`
   - Creates `.env` from `.env.example` (if missing)
   - Creates Desktop and Start Menu shortcuts

4. When asked:

   ```
   Start AI Overlay Agent when Windows starts? (Y/N):
   ```

   - Type **Y** — app launches every time you log in
   - Type **N** — you launch it manually from Desktop/Start Menu

5. When you see **Installation complete**, press any key to close the window.

---

## Step 4 — Add your API key

1. Open the app folder
2. Open **`.env`** in Notepad (or any text editor)
3. Add your key for the provider you use in `config.ini`:

   **Google Gemini (default in config.ini):**
   ```
   GEMINI_API_KEY=your-actual-gemini-key
   ```

   **OpenAI:**
   ```
   OPENAI_API_KEY=sk-your-actual-openai-key
   ```

   **Anthropic (Claude):**
   ```
   ANTHROPIC_API_KEY=sk-ant-your-actual-key
   ```

4. Save and close `.env`

### Where to get API keys

| Provider | URL |
|----------|-----|
| Google Gemini | [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| OpenAI | [https://platform.openai.com/api/keys](https://platform.openai.com/api/keys) |
| Anthropic | [https://console.anthropic.com](https://console.anthropic.com) |

---

## Step 5 — Configure the app (optional)

Edit **`config.ini`** in the app folder.

**Switch AI provider:**
```ini
[API]
provider = gemini
model = gemini-3-pro
```

Supported providers: `anthropic`, `openai`, `gemini`

**Window size and position:**
```ini
[UI]
width = 500
height = 650
start_x = 60
start_y = 60
opacity = 0.94
```

**Hotkeys:**
```ini
[HOTKEYS]
toggle = ctrl+shift+space
capture = ctrl+shift+s
clear = ctrl+shift+c
focus = ctrl+shift+i
export = ctrl+shift+e
```

Restart the app after changing `config.ini`.

---

## Step 6 — Launch the app

### Normal use (recommended)

- Double-click **AI Overlay Agent** on your Desktop, or
- Start Menu → **AI Overlay Agent**

No terminal window appears. The overlay opens in the top-left of your screen.

### Debug mode (if something goes wrong)

- Start Menu → **AI Overlay Agent (Debug)**

Shows a console with logs (invisibility setup, hotkeys, API errors).

### From the app folder

| File | Purpose |
|------|---------|
| `run.bat` | Launch without console |
| `run_debug.bat` | Launch with console logs |
| `install.bat` | Re-run installer / update dependencies |
| `uninstall.bat` | Remove shortcuts only |

---

## Step 7 — Verify privacy (screen capture invisibility)

1. Start **AI Overlay Agent**
2. Open Google Meet (or OBS) and start **Present entire screen** (share full display, not a single window)
3. The overlay should be **visible to you** but **not visible** in the Meet/OBS preview
4. Open the model dropdown and Settings — those should also be hidden from capture

If the overlay still appears in Meet, use **Debug** mode and check the console for:

```
✓ Capture exclusion applied to N window(s), N verified
```

---

## Daily usage — hotkeys

| Hotkey | Action |
|--------|--------|
| `Ctrl+Shift+Space` | Show / hide overlay |
| `Ctrl+Shift+S` | Hide overlay, capture screen, send to AI |
| `Ctrl+Shift+C` | Clear conversation |
| `Ctrl+Shift+I` | Focus text input |
| `Ctrl+Shift+E` | Export chat to Markdown (`exports/` folder) |

---

## Update or re-install

1. Pull or copy new files into the same app folder
2. Double-click **`install.bat`** again
3. Existing `.env` and settings are kept

---

## Uninstall shortcuts (keep app files)

1. Double-click **`uninstall.bat`**
2. Type **Y** to confirm

This removes:

- Desktop shortcut
- Start Menu folder
- Startup entry (if added)

It does **not** delete the app folder, `.env`, or conversation exports.

To fully remove the app, delete the entire app folder after running `uninstall.bat`.

---

## Manual install (without install.bat)

For developers or if the batch installer fails:

```bat
cd C:\Apps\ai-overlay-agent

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
notepad .env

python ai_overlay.py
```

---

## Troubleshooting

### `Python is not installed or not on PATH`

This often means Windows has the **Microsoft Store python stub** (`WindowsApps\python.exe`) but no real Python install.

**Fix A — You already have a `.venv` folder:** just run `install.bat` again. It uses `.venv\Scripts\python.exe` automatically.

**Fix B — Fresh install:**
- Install Python from [python.org](https://www.python.org/downloads/) (not the Microsoft Store)
- Check **Add python.exe to PATH** during install
- Restart your PC, then run `install.bat` again

### App does not start from Desktop shortcut

- Run **`install.bat`** again (recreates shortcuts)
- Or run **`run_debug.bat`** to see the error message
- Confirm `.env` has a valid API key

### Hotkeys do not work

- Close other apps that may use the same shortcuts
- Run the app as Administrator (right-click → Run as administrator)
- Change hotkeys in `config.ini` and restart

### API errors

- Confirm `.env` is in the same folder as `ai_overlay.py`
- Check your API key is valid and has quota/credits
- Confirm `provider` in `config.ini` matches the key in `.env`

### Overlay visible in Google Meet / OBS

- Use **full screen / entire display** sharing (not a single window)
- Requires Windows 10 2004+ or Windows 11
- Restart the app after install
- Run Debug mode and confirm capture exclusion is verified

### Shortcut broken after moving the folder

- Run **`install.bat`** again from the new location

---

## File layout after install

```
ai-overlay-agent/
├── ai_overlay.py          # Main application
├── config.ini             # Settings (provider, hotkeys, UI)
├── .env                   # Your API keys (never share or commit)
├── .env.example           # Template for .env
├── install.bat            # Windows installer
├── uninstall.bat          # Remove shortcuts
├── run.bat                # Launch (no console)
├── run_debug.bat          # Launch (with console)
├── requirements.txt       # Python dependencies
├── prompts/               # System prompts
├── exports/               # Exported conversations (created on use)
└── .venv/                 # Python virtual environment (created by install)
```

---

## Quick checklist

- [ ] Python 3.10+ installed with PATH enabled
- [ ] App copied to a permanent folder
- [ ] `install.bat` completed successfully
- [ ] API key added to `.env`
- [ ] Desktop shortcut launches the app
- [ ] Overlay hidden from Meet/OBS when sharing full screen
- [ ] Hotkeys work (`Ctrl+Shift+Space`, `Ctrl+Shift+S`)

---

## Support

See also:

- [README.md](README.md) — full feature documentation
- [PRIVACY.md](PRIVACY.md) — how invisibility works
- [INVISIBILITY_TEST.md](INVISIBILITY_TEST.md) — test procedures for capture exclusion
