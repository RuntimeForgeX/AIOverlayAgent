# Agent Instructions
## Maintaining and Extending AI Screen Overlay Agent

---

## Purpose of This Folder

The `prompts/` directory is the **source of truth** for product intent, memory behavior, system personality, and low-level Windows implementation notes.

The **running app** is `main.py` → `src/ui/app.py` (`OverlayApp`), plus `config.ini`, `app_config.ini`, build scripts, and an optional Windows installer — not a greenfield single-file prototype.

When you change behavior, update the relevant prompt file **and** the code, then rebuild the `.exe` if shipping to installed users.

---

## Read These Files In This Order

1. **`PRD.md`** — Features, UI, colors, hotkeys, config format, non-goals
2. **`memory.md`** — Conversation history, LangChain messages, export, threading (**read carefully before touching API/memory code**)
3. **`LICENSE.md`** — Premium JWT licensing, config URLs, activation, build, public key (**read before touching `src/licensing/` or startup**)
4. **`system_prompt.md`** — Default AI personality (loaded from first fenced code block in that file)
5. **`exploitation.md`** — Screenshots, capture exclusion (DWM), hotkeys, PyInstaller notes

---

## Repository Layout (Current)

```
ai-overlay-agent/
├── main.py                    # Entry point (license gate → OverlayApp)
├── app_config.ini             # App name, exe name, publisher, version, AppId GUID
├── config.ini                 # Provider, models, hotkeys, UI, capture, LICENSE
├── .env.example               # API key template (user copies to .env or uses Windows env vars)
├── requirements.txt           # Runtime Python dependencies
├── requirements_build.txt     # PyInstaller (build venv only)
├── prompts/                   # This folder (incl. LICENSE.md)
├── src/licensing/             # JWT license gate + offline verify
├── build/
│   ├── ai_overlay_agent.spec
│   ├── build_exe.bat
│   ├── build_installer.bat
│   ├── runtime_keyboard_fix.py   # PyInstaller hook for keyboard on Win64
│   ├── prepare_pyinstaller.py
│   └── sync_inno_config.py
├── installer/                 # Inno Setup script + license texts
├── release/                   # Output: *_Setup.exe (after installer build)
├── install.bat / run.bat / uninstall.bat
└── dist/                      # Output: PersonalAiAgentSurya.exe (after exe build)
```

Do **not** document or rely on `.venv`, `.venv_build`, `pyinstaller_build/`, or `node_modules/` — those are local/build artifacts.

---

## Architecture Rules

### Application structure

- **Primary UI:** `OverlayApp` class in `ai_overlay.py`
- **Providers:** `AnthropicProvider`, `OpenAIProvider`, `GeminiProvider` extending `APIProvider`
- **AI stack:** LangChain (`ChatAnthropic`, `ChatOpenAI`) for Anthropic/OpenAI; `google.generativeai` for Gemini
- **Config:** `configparser` + `get_config_value()` with defaults everywhere
- **Branding:** `app_config.ini` → `APP_NAME`, `WINDOW_TITLE`, `APPDATA_FOLDER`, installer exe name

### UI

- **tkinter only** — no third-party UI frameworks
- Font: **Courier New** throughout
- Colors: `COLORS` dict in `ai_overlay.py` (must match PRD hex values)
- Extra UI beyond original PRD: model dropdown, Settings (response sections), system prompt editor

### Hotkeys

- Library: **`keyboard`** (global hotkeys) — do not replace with another hook library unless explicitly requested
- Read combos from `config.ini` `[HOTKEYS]` with PRD defaults as fallback
- Callbacks **must** use `_schedule_on_main_thread()` — `keyboard` fires on a background thread; Tk is not thread-safe
- Packaged builds: keep `build/runtime_keyboard_fix.py` in the PyInstaller spec `runtime_hooks`
- Register after UI exists: `root.after(200, self.register_hotkeys)`

### Screenshots

- Hide overlay → wait (default 250 ms from config / code) → `ImageGrab.grab()` → show overlay → re-apply capture exclusion
- Compress: max width 1280, JPEG quality 82 (configurable in `[CAPTURE]`)
- Send as base64 JPEG inside LangChain `image_url` content

### API and memory

- Follow **`memory.md`** exactly for history, trim, errors, export paths
- System prompt: `SystemMessage` at invoke time only — never in `conversation_history`
- API calls in **daemon threads**; UI via `root.after(0, ...)`
- **Lazy API init:** missing keys must not crash startup; errors only in chat when user sends a message
- **No `messagebox`** for errors — in-app system messages only

### Environment / API keys

- `load_environment()` at startup: Windows env vars win; `.env` fills missing keys only (`override=False`)
- Keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` via `get_api_key()`

### Capture exclusion (invisibility)

- Use **`SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)`** on all process HWNDs
- Do **not** rely on `WS_EX_NOREDIRECTIONBITMAP` alone — it breaks DWM exclusion (documented in `exploitation.md`)
- Re-apply on show, focus, and periodic poll (Meet/OBS)

### Build and install

```bat
build\build_exe.bat          # → dist\<exe_base_name>.exe
build\build_installer.bat    # → release\<AppName>_Setup.exe
```

Work path for PyInstaller uses `%TEMP%` to avoid OneDrive lock errors.

---

## Quality Checks Before Finishing a Change

- [ ] App launches without API key (status: ready · set API key in environment)
- [ ] All 5 global hotkeys work when installed `.exe` is running (not only from `python ai_overlay.py`)
- [ ] Hotkey handlers update UI without threading errors
- [ ] Screenshot excludes overlay from capture; overlay visible to user locally
- [ ] Full history sent each turn; clear resets list + UI
- [ ] API error removes last user message and shows ⚠ in chat only
- [ ] Export writes to `%APPDATA%\<appdata_folder>\exports\`
- [ ] Model switch clears history and re-inits provider
- [ ] `memory.md` / PRD updated if behavior changed

---

## Git

When the user asks for commits: one logical change per commit; do not commit `.env`, `dist/`, `release/`, or venv folders.
