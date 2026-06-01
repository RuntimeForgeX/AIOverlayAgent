# AI Overlay Agent

A **Windows desktop AI overlay** that floats on top of your screen, answers questions about what you see (including screenshots), and stays **hidden from screen recording** tools such as OBS, Google Meet, and Zoom when you share your full display.

Built with Python, tkinter, and configurable AI providers (Anthropic, OpenAI, Google Gemini).

---

## Features

- Always-on-top transparent overlay with dark/light/system themes
- **Global hotkeys** work even when the overlay is hidden
- **Screen capture** sent to the AI (JPEG-compressed, multimodal)
- **Capture exclusion** — overlay not shown in typical full-screen recordings (Windows 10 2004+)
- Switch models from the header dropdown (Claude, GPT, Gemini)
- Screenshot queue (up to 10 thumbnails) before sending
- Chat history and screenshot queue persist in `%APPDATA%`
- Export conversation to Markdown
- Errors shown **in the app only** (no Windows popup dialogs)

---

## Requirements

- **Windows 10** (build 19041 / 2004+) or **Windows 11**
- **Python 3.10+** (for development; the installer ships a standalone `.exe`)
- An API key for at least one provider:
  - [Anthropic](https://console.anthropic.com/) — `ANTHROPIC_API_KEY`
  - [OpenAI](https://platform.openai.com/) — `OPENAI_API_KEY`
  - [Google Gemini](https://aistudio.google.com/apikey) — `GEMINI_API_KEY`

---

## Quick start (development)

### 1. Clone and install dependencies

```bat
cd ai-overlay-agent
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API keys

**Option A — Windows Environment Variables (recommended for installs)**

1. Win + R → `sysdm.cpl` → **Advanced** → **Environment Variables**
2. Add e.g. `GEMINI_API_KEY` with your key
3. Restart the app after changing variables

**Option B — `.env` file**

Copy `.env.example` to `.env` in the project root and fill in your keys:

```env
GEMINI_API_KEY=your-key-here
```

Windows environment variables always take priority over `.env`.

### 3. Run

```bat
py -3 main.py
```

Or double-click `run.bat`.

---

## Hotkeys

| Hotkey | Action |
|--------|--------|
| `Ctrl+Shift+Space` | Show / hide overlay |
| `Ctrl+Shift+S` | Capture screen and send to AI |
| `Ctrl+Shift+C` | Clear conversation |
| `Ctrl+Shift+I` | Focus text input |
| `Ctrl+Shift+E` | Export chat to Markdown |

Customize in `config.ini` under `[HOTKEYS]`.

---

## Configuration

| File | Purpose |
|------|---------|
| `config.ini` | Provider, models, hotkeys, UI size, capture quality |
| `app_config.ini` | App name, window title, installer exe name, version |
| `prompts/system_prompt.md` | AI personality (first code block is loaded at runtime) |

**Installed app:** user overrides can live in:

`%APPDATA%\PersonalAiAgentSurya\config.ini` and `.env`

---

## Project structure

```
ai-overlay-agent/
├── main.py                 # Entry point
├── config.ini              # Runtime settings
├── app_config.ini          # Branding / build metadata
├── requirements.txt
├── src/
│   ├── config/             # settings, system prompt loader
│   ├── services/           # LLM providers, capture, storage
│   ├── ui/                 # OverlayApp, themes, markdown, cursor
│   └── utils/              # Win32 invisibility, error handlers
├── prompts/                # PRD, memory design, agent docs
├── build/                  # PyInstaller + Inno Setup scripts
├── installer/              # Windows installer (Inno Setup)
└── release/                # Output: *_Setup.exe (after build)
```

---

## Build installer

```bat
build\build_exe.bat
build\build_installer.bat
```

Output: `release\PersonalAiAgentSurya_Setup.exe`

See [QUICK_BUILD.txt](QUICK_BUILD.txt), [RELEASE_BUILD.md](RELEASE_BUILD.md), and [BUILD_SUMMARY.md](BUILD_SUMMARY.md).

**Prerequisites for installer build:** Inno Setup 6 (`winget install -e --id JRSoftware.InnoSetup`)

---

## Customize AI behavior

Edit `prompts/system_prompt.md` (content inside the first ` ``` ` block), or use **Settings → Edit System Prompt** in the app.

For developers changing memory/API behavior, see `prompts/memory.md` and `prompts/AGENT_INSTRUCTIONS.md`.

---

## Privacy and recording

The overlay uses Windows **display capture exclusion** so it does not appear in many full-screen captures. See [PRIVACY.md](PRIVACY.md) and [INVISIBILITY_TEST.md](INVISIBILITY_TEST.md).

Do not use near sensitive data you do not want sent to your AI provider’s API.

---

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| API errors in chat | Set the correct env var for your provider; restart the app |
| Hotkeys not working (installed exe) | Rebuild after code changes; close other apps using same combos; try Run as administrator once |
| Overlay visible in recording | Share **entire screen/display**, not a single window; Windows 10 2004+ required |
| Build fails with Access denied | Close running app; see `build\prepare_pyinstaller.py` / build uses `%TEMP%` for PyInstaller work files |
| Model switch error | Ensure latest code (`load_environment` imported in `src/ui/app.py`) |

---

## License

See [installer/LICENSE.txt](installer/LICENSE.txt) for installer license text.

---

## Documentation index

| Document | Description |
|----------|-------------|
| [BUILD_SUMMARY.md](BUILD_SUMMARY.md) | What the project contains |
| [RELEASE_BUILD.md](RELEASE_BUILD.md) | Full release build guide |
| [QUICK_BUILD.txt](QUICK_BUILD.txt) | Short build commands |
| [QUICK_TEST.md](QUICK_TEST.md) | Smoke test checklist |
| [INVISIBILITY_TEST.md](INVISIBILITY_TEST.md) | Recording exclusion tests |
| [PRIVACY.md](PRIVACY.md) | Privacy and capture exclusion |
| [prompts/PRD.md](prompts/PRD.md) | Product requirements |
