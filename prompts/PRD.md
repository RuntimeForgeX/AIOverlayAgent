# Product Requirements Document
## Project: AI Screen Overlay Agent (Windows)

---

## What You Are Building

A **Windows desktop overlay application** written in Python.  
It is a floating, transparent, always-on-top window that acts as an AI assistant.  
The AI can **see the user's screen** via screenshots and respond with text answers.  
The user controls everything with **keyboard shortcuts only** — no mouse required.

This is NOT a web app. NOT a browser extension. It is a native Windows Python desktop app.

---

## Core Purpose

Give the user an AI co-pilot that:
1. Floats invisibly over any other app
2. Can screenshot the screen on demand and send it to a configurable AI model
3. Answers questions about what it sees (code, errors, documents, UI, anything)
4. Remembers the conversation within the session
5. Never steals focus or interrupts workflow

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.10+ |
| UI Framework | tkinter (built-in, no install needed) |
| AI Backend | Anthropic, OpenAI, or Gemini API (configurable latest model family) |
| Screenshot | Pillow — `ImageGrab.grab()` |
| Hotkeys | `keyboard` library (global, works even when app is hidden) |
| Image encoding | base64 (for sending to API) |
| Config | `configparser` reading `config.ini` |
| API key | `python-dotenv` loading `.env` file |

### Recommended model defaults

Use the latest stable model family available from the selected provider, for example:
- Anthropic: Claude Opus class model such as `claude-opus-4-5`
- OpenAI: GPT-5 class model such as `gpt-5.4`
- Gemini: Gemini Pro class model such as `gemini-2.5-pro`

---

## All Features To Build

### Must Have
- Floating window, always on top (`root.attributes("-topmost", True)`)
- Adjustable transparency (`root.attributes("-alpha", 0.92)`)
- **Invisible to screen capture and recording software** (OBS, Chrome screen share, ScreenFlow, etc.) so the overlay does not appear in recorded videos or shared screens
- Draggable window (click-drag on header bar)
- Scrollable chat history panel
- Text input bar at the bottom
- Send button + Enter key to submit
- Global hotkey: **Ctrl+Shift+Space** → toggle show/hide window
- Global hotkey: **Ctrl+Shift+S** → hide window → take screenshot → show window → send to AI
- Global hotkey: **Ctrl+Shift+C** → clear conversation memory
- Global hotkey: **Ctrl+Shift+I** → focus the text input box
- Global hotkey: **Ctrl+Shift+E** → export chat to a `.md` file
- When capturing screen with the app hotkey (Ctrl+Shift+S): hide the overlay first, wait 250ms, screenshot, then show overlay again (so overlay does not appear in the screenshot)
- Remain invisible to external screen capture and recording tools (OBS, Chrome, streaming software) at all times so viewers never see the overlay
- Send full conversation history on every API call (the selected model has no memory — we pass it manually)
- Show token usage in status bar after each response
- Loading indicator (dot color changes) while waiting for API response
- Disable send button while AI is thinking

### Should Have
- Opacity slider in the header bar
- Quick action buttons: Capture / Clear / Export
- Timestamp on every message
- Code blocks in AI responses rendered with different background color
- Screenshot compression before sending (resize to max 1280px width, JPEG quality 82) to save tokens and speed up response
- Status bar at bottom showing current state (ready / thinking / error / token count)
- Export saves to `exports/` folder with timestamp filename

### Nice to Have
- System tray icon (requires `pystray`)
- Region selection capture (user drags to select part of screen)
- Auto-trim conversation history if it gets too long (keep first 2 + last 18 messages)
- Load system prompt from `prompts/system_prompt.md` file at startup

---

## Window Layout

Build the UI in exactly this order top to bottom:

```
┌──────────────────────────────────────────────┐
│  ● AI OVERLAY              [opacity slider]  │  ← header frame (draggable)
├──────────────────────────────────────────────┤
│                                              │
│  12:01  ▶ you                                │
│  [Screenshot] what is this error?            │
│                                              │
│  12:01  ◆ ai                                 │
│  The error on line 42 is a TypeError...      │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │  result = items[index]               │    │  ← code block (yellow bg)
│  └──────────────────────────────────────┘    │
│                                              │
├──────────────────────────────────────────────┤
│  [type a question...              ]  [ ⏎ ]  │  ← input bar
│  [📷 Capture]  [🗑 Clear]  [💾 Export]      │  ← quick buttons
├──────────────────────────────────────────────┤
│  ready · 320 in / 85 out tokens              │  ← status bar
└──────────────────────────────────────────────┘
```

---

## Color Theme (Dark)

```
bg_main:      #0a0a0f
bg_header:    #0f0f1a
bg_input:     #13131f
bg_chat:      #0a0a0f
accent_green: #00ff88   ← used for "you" label, dot, send button
accent_blue:  #7dd3fc   ← used for "ai" label and AI response text
text_normal:  #d4d4d8
text_dim:     #52525b   ← timestamps, status bar, system messages
error_red:    #f87171
code_bg:      #111118
code_fg:      #fbbf24
border:       #1e1e2e
```

---

## Message Display Rules

- Every message has a timestamp like `12:04` in `text_dim` color
- User messages: label `▶ you` in `accent_green`, message text in `text_normal`
- AI messages: label `◆ ai` in `accent_blue`, message text in `accent_blue`
- System/info messages: no label, full line in `text_dim`
- Error messages: prefix `⚠` in `error_red`
- Code blocks in AI text (between ``` and ```) rendered with `code_bg` background and `code_fg` text

---

## Hotkey Summary

| Hotkey | Action |
|--------|--------|
| Ctrl+Shift+Space | Toggle window visible/hidden |
| Ctrl+Shift+S | Capture screen + send to AI |
| Ctrl+Shift+C | Clear all conversation memory |
| Ctrl+Shift+I | Focus the text input box |
| Ctrl+Shift+E | Export chat to markdown file |

All hotkeys must be **global** — they must work even when the overlay window is hidden or another app is in focus.

---

## File Structure To Create

```
ai-overlay-agent/
├── ai_overlay.py          ← main application (single file)
├── config.ini             ← user configuration
├── .env                   ← API key (user creates this)
├── requirements.txt       ← pip dependencies
├── prompts/
│   ├── PRD.md             ← this file
│   ├── memory.md          ← session memory design
│   ├── system_prompt.md   ← AI system prompt
│   └── exploitation.md    ← technical capabilities reference
└── exports/               ← auto-created folder for exported chats
```

---

## Dependencies (requirements.txt content)

```
anthropic>=0.25.0
openai>=1.0.0
google-genai>=0.8.0
pillow>=10.0.0
keyboard>=0.13.5
python-dotenv>=1.0.0
```

### Local Python setup

Use a virtual environment for all development and runtime work:
1. `python -m venv .venv`
2. Activate the venv with `.venv\Scripts\activate`
3. Run `pip install -r requirements.txt` inside the venv

---

## config.ini Format

```ini
[API]
provider = anthropic
model = claude-opus-4-5
max_tokens = 1500

[API_OPENAI]
model = gpt-5.4

[API_GEMINI]
model = gemini-2.5-pro

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

## .env Format (user must create this)

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-openai-key-here
GEMINI_API_KEY=your-gemini-key-here
```

---

## Use Case: Educational Content Creation

This app is designed for content creators, educators, and YouTubers who want to:
- Record tutorial and coding videos without showing the helper overlay to viewers
- Share their screen during live streams while keeping the AI assistant invisible to the audience
- Teach programming concepts with the overlay providing real-time AI help, unseen by students
- Present code reviews or debugging sessions cleanly, with the overlay hidden from recording

The invisibility to recording software is a core feature, not an edge case.

---

## Non-Goals (Do NOT Build These)

- No web server, no Flask, no browser UI
- No macOS or Linux support
- No real-time continuous screen monitoring (only on-demand capture)
- No keylogging or mouse tracking beyond what hotkeys require
- No bypassing DRM or screen recording detection
- No auto-clicking or automating other applications