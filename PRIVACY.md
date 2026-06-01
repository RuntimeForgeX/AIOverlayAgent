# Privacy and Screen Capture

How AI Overlay Agent handles visibility, recordings, and data sent to AI providers.

---

## What “invisible to recording” means

On **Windows 10 version 2004+** and **Windows 11**, the app uses the Windows API:

`SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)`

This tells the compositor to **exclude the overlay window** from many screen-capture and sharing pipelines (OBS, Zoom/Meet/Teams when sharing a **full display**, etc.).

- You still **see** the overlay on your monitor.
- Viewers of a typical **full-screen** share often **do not** see the overlay.

This is **not** encryption or anti-screenshot DRM. It does not block:

- Phone cameras pointed at your monitor
- Physical photographs of the screen
- All third-party tools (behavior varies by app and share mode)
- **Single-window** share of another app (the overlay is a separate window)

---

## What the app can see

| Data | Sent off your PC? |
|------|-------------------|
| Text you type in the overlay | Yes — to your configured AI provider |
| Screenshots you capture (`Ctrl+Shift+S` or queue + send) | Yes — as JPEG to the provider API |
| Conversation history for the session | Yes — included in each API request until cleared |
| Your display when you are **not** capturing | No |

Screenshots are compressed (max width 1280px, JPEG) before upload.

---

## What stays local

- API keys: Windows environment variables and/or `.env` on your machine (see load order in `prompts/memory.md`)
- Optional persistence in `%APPDATA%\PersonalAiAgentSurya\`:
  - `chat_history.json` (UI display log)
  - `screenshot_queue.json` (queued thumbnails as base64)
  - `preferences.json` (theme)
  - `exports\` (Markdown files you export)

The app does **not** upload chat history to a separate cloud service — only to the AI provider you configure when you send messages.

---

## API keys

Keys are read from:

1. **Windows user/system environment variables** (highest priority)
2. **`.env` files** (only for variables not already set):
   - `%APPDATA%\PersonalAiAgentSurya\.env`
   - Next to the installed `.exe`
   - Project root `.env` (development)

Never commit `.env` to git. Do not share installer bundles containing real keys.

---

## Errors and logging

- API and UI errors are shown **inside the overlay chat**, not as Windows message boxes.
- `run_debug.bat` or running from a console may print technical logs (invisibility setup, etc.) — the release `.exe` uses `console=False`.

---

## Responsible use

- Do not capture screens showing passwords, banking, medical records, or confidential documents unless you accept sending that content to your AI provider.
- Inform others if you use AI assistance during live sessions where policy requires disclosure.
- Comply with your organization’s policies on AI tools and screen sharing.

---

## Technical reference

Implementation: `src/utils/win32_invisibility.py`  
Do **not** rely on `WS_EX_NOREDIRECTIONBITMAP` alone — it breaks DWM-based exclusion in this app.

Test procedure: [INVISIBILITY_TEST.md](INVISIBILITY_TEST.md)
