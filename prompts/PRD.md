# Product Requirements Document
## Project: AI Screen Overlay Agent (Windows)

---

## What You Are Building

A **Windows desktop overlay** in Python: a floating, always-on-top, semi-transparent window that acts as an AI assistant.

- The AI can **see the screen** via on-demand screenshots (multimodal APIs).
- The user can drive the app with **keyboard shortcuts** (global hotkeys) and minimal mouse use.
- The overlay is **excluded from screen capture** (OBS, Meet, Zoom full-screen share) so viewers do not see the helper.

This is a **native Windows** app (tkinter), not a web app or browser extension.

**Shipped form:** PyInstaller one-file `.exe` + optional Inno Setup installer (`release\*_Setup.exe`).

---

## Core Purpose

1. Float over any app without appearing in recordings (when capture exclusion works)
2. Screenshot on demand and send to a **configurable** provider (Anthropic, OpenAI, or Gemini)
3. Answer questions about code, errors, documents, or UI visible on screen
4. Remember the **session** conversation until cleared or provider switched
5. Stay out of the way — hotkeys work while hidden

---

## Tech Stack (Implemented)

| Layer | Choice |
|-------|--------|
| Language | Python 3.10+ (builds tested on 3.14) |
| UI | tkinter |
| AI (Anthropic / OpenAI) | LangChain — `ChatAnthropic`, `ChatOpenAI` |
| AI (Gemini) | `google-generativeai` |
| Screenshot | Pillow `ImageGrab.grab()` |
| Global hotkeys | **`keyboard`** library + main-thread scheduling |
| Config | `configparser` — `config.ini`, `app_config.ini` |
| API keys | `python-dotenv` + **Windows environment variables** (env wins over `.env`) |
| Capture exclusion | Win32 `SetWindowDisplayAffinity` (`WDA_EXCLUDEFROMCAPTURE`) |
| Packaging | PyInstaller + Inno Setup 6 |

### Default model examples (config.ini)

| Provider | Example model id |
|----------|------------------|
| Anthropic | `claude-opus-4-5`, `claude-3-5-sonnet` |
| OpenAI | `gpt-5.4`, `gpt-4o`, `gpt-4o-mini` |
| Gemini | `gemini-3-pro`, `gemini-2.5-pro` |

Header dropdown maps friendly names to provider + model id (see `change_model` in `ai_overlay.py`).

---

## Features

### Must have (implemented)

- Always on top, adjustable opacity (`-alpha`)
- **Invisible to screen capture** (Windows 10 2004+ / Windows 11)
- Draggable header; scrollable chat; text input + Send / Enter
- Global hotkeys (see table below) via `keyboard`
- Capture flow: hide → delay → screenshot → show → send
- Full session history on every API call (see `memory.md`)
- Token totals in status bar (Gemini may show 0)
- Disable send while waiting; errors in chat panel only
- Lazy API key handling — app starts without key

### Should have (implemented)

- Quick buttons: Capture / Clear / Export / Settings
- Timestamps; code-block styling in AI replies
- JPEG screenshot compression (configurable max width / quality)
- Model selector in header
- Settings: toggle response sections (MCQ, C++, SQL, DSA); edit system prompt in-app
- Export to `%APPDATA%\<appdata_folder>\exports\`

### Nice to have (partial / not implemented)

- Opacity slider (label placeholder `[opacity]` only)
- System tray (`pystray`) — not built
- Region-select capture — not built
- Auto-save chat between sessions — not built (export only)

---

## Window Layout

```
┌──────────────────────────────────────────────┐
│  ● AI OVERLAY          [opacity]  [model ▼] │  ← header (draggable)
├──────────────────────────────────────────────┤
│  chat history (scrollable)                   │
├──────────────────────────────────────────────┤
│  [type a question...              ]  [ ⏎ ]  │
│  [📷 Capture] [🗑 Clear] [💾 Export] [⚙]   │
├──────────────────────────────────────────────┤
│  ready · N in / M out tokens                 │
└──────────────────────────────────────────────┘
```

Window title string comes from `app_config.ini` → `window_title` (default `AI OVERLAY`).

---

## Color Theme (Dark)

```
bg_main:      #0a0a0f
bg_header:    #0f0f1a
bg_input:     #13131f
bg_chat:      #0a0a0f
accent_green: #00ff88
accent_blue:  #7dd3fc
text_normal:  #d4d4d8
text_dim:     #52525b
error_red:    #f87171
code_bg:      #111118
code_fg:      #fbbf24
border:       #1e1e2e
```

---

## Hotkey Summary

| Hotkey | Action |
|--------|--------|
| Ctrl+Shift+Space | Toggle overlay visible / hidden |
| Ctrl+Shift+S | Capture screen and send to AI |
| Ctrl+Shift+C | Clear conversation memory |
| Ctrl+Shift+I | Focus text input |
| Ctrl+Shift+E | Export chat to Markdown |

All hotkeys are **global** (work when overlay is hidden or another app has focus).

Configurable in `config.ini` `[HOTKEYS]`. After install, user may need to **restart the app** if Windows env vars or config changed.

---

## File Structure

```
ai-overlay-agent/
├── ai_overlay.py
├── app_config.ini
├── config.ini
├── .env / .env.example
├── requirements.txt
├── prompts/
│   ├── PRD.md
│   ├── memory.md
│   ├── system_prompt.md
│   ├── AGENT_INSTRUCTIONS.md
│   └── exploitation.md
├── build/                   # PyInstaller + helper scripts
├── installer/               # Inno Setup
├── dist/                    # Built .exe (gitignored)
├── release/                 # Built installer (gitignored)
├── install.bat, run.bat, uninstall.bat
└── README.md, PRIVACY.md, installOnSystem.md, ...
```

User-writable data (not in Program Files):

- `%APPDATA%\<appdata_folder>\config.ini` (optional override)
- `%APPDATA%\<appdata_folder>\.env`
- `%APPDATA%\<appdata_folder>\exports\`

---

## Dependencies (`requirements.txt`)

```
langchain>=0.1.0
langchain-openai>=0.1.0
langchain-anthropic>=0.1.0
langchain-community>=0.1.0
anthropic>=0.25.0
openai>=1.0.0
google-generativeai>=0.8.0
pillow>=10.0.0
keyboard>=0.13.5
python-dotenv>=1.0.0
```

Development: `python -m venv .venv` → activate → `pip install -r requirements.txt`  
Release exe: `build\build_exe.bat` (uses `.venv_build`).

---

## config.ini Format

```ini
[API]
provider = gemini
model = gemini-3-pro
max_tokens = 1500

[API_OPENAI]
model = gpt-4o

[API_GEMINI]
model = gemini-3-pro

[HOTKEYS]
toggle = ctrl+shift+space
capture = ctrl+shift+s
clear = ctrl+shift+c
focus = ctrl+shift+i
export = ctrl+shift+e

[UI]
width = 500
height = 650
start_x = 60
start_y = 60
opacity = 0.94

[CAPTURE]
max_width = 1280
jpeg_quality = 82
hide_delay_ms = 250
```

---

## API Keys

Set **one or more** of:

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

Via **Windows Environment Variables** (recommended for installs) and/or `.env` (see `memory.md` load order).

---

## Use Case: Educational / Streaming

Creators record or share the screen while using the overlay privately. Capture exclusion targets full-screen / display capture on Windows 10 2004+.

---

## Non-Goals

- No web server or browser UI
- No macOS / Linux support in current codebase
- No continuous screen monitoring (on-demand only)
- No keylogging beyond global hotkey registration
- No automating clicks or typing in other apps
- No bypassing DRM content protection
