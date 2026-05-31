# Agent Instructions
## How To Build This Project From These Prompts

---

## You Are An AI Agent

You have been given a folder of prompt files.  
Your job is to read all of them and build the complete working application.  
Do not ask clarifying questions. Everything you need is in these files.  
Build it completely, from scratch, in one pass.

---

## Read These Files In This Order

1. `PRD.md` — Read this first. It defines everything: what to build, all features, UI layout, colors, file structure, dependencies.
2. `memory.md` — Read this second. It defines how conversation history works and all data structures.
3. `system_prompt.md` — Read this third. Extract the system prompt string from the first code block.
4. `exploitation.md` — Read this last. It gives you the exact technical implementation details for every capability.

---

## What To Produce

Create these files exactly:

```
ai-overlay-agent/
├── ai_overlay.py         ← the complete working application (single Python file)
├── config.ini            ← configuration file with all settings from PRD.md
├── requirements.txt      ← pip dependencies from PRD.md
├── README.md             ← setup and usage instructions
└── .env.example          ← example showing ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY
```

Do NOT create the prompts/ folder — that is already provided.

When you build the project from these prompt files, make a git commit after each completed change or logically grouped change set so the work is preserved incrementally.

---

## Rules For Building ai_overlay.py

### Structure
- Single file. No imports from local modules.
- All code in one `OverlayApp` class plus a `if __name__ == "__main__":` entry point.
- Class methods named exactly as described in PRD.md architecture section.

### UI
- Use tkinter only. No third-party UI libraries.
- Implement every widget described in the PRD.md layout section.
- Use the exact hex color values from PRD.md color theme section.
- Font: "Courier New" throughout — monospace fits the dark terminal aesthetic.

### Hotkeys
- Register all 5 hotkeys from PRD.md hotkey table.
- Use the keyboard library for global hotkeys.
- Read hotkey strings from config.ini, with hardcoded defaults as fallback.

### Screenshot
- Hide window → wait 250ms → capture → show window. Always in this order.
- Compress screenshot as described in exploitation.md section 1.
- Encode as base64 JPEG before sending to API.

### API calls
- Always run in a background daemon thread.
- Always pass full conversation_history as messages.
- Always pass the system prompt through the provider's native system-instruction mechanism.
- Read provider, model, and max_tokens from config.ini.
- Support the latest stable Anthropic, OpenAI, and Gemini model families through a configurable provider setting.
- On success: append reply to history, update UI via root.after().
- On error: remove last user message from history, show error in chat.

### Memory
- Follow memory.md exactly for all data structures and flow.
- Implement auto-trim at 30 messages as described in exploitation.md.

### System prompt loading
- Try to load from prompts/system_prompt.md at startup.
- Parse first fenced code block content.
- Fall back to hardcoded default string if file not found.

### Export
- Implement as described in exploitation.md section 8.
- Create exports/ folder if needed.

### Config loading
- Use configparser to read config.ini.
- Every configparser call must have a fallback value so app works even without config.ini.

### API key
- Load from .env using python-dotenv.
- Fall back to the environment variable that matches the configured provider: ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY.
- If none are found, print a clear warning but do not crash on launch.

---

## Rules For README.md

Include exactly:
1. One-line description of what the app is
2. Prerequisites (Python 3.10+, Windows 10/11)
3. Installation steps (git clone / download → python -m venv .venv → activate venv → pip install -r requirements.txt → create .env)
4. How to run (python ai_overlay.py)
5. Hotkeys table (copy from PRD.md)
6. How to customize AI behavior (edit prompts/system_prompt.md)
7. Note about these prompt files being usable to rebuild the project with any AI

---

## Quality Checks Before Finishing

Before you consider the build complete, verify:

- [ ] App launches without errors when API key is not set (just shows warning)
- [ ] All 5 hotkeys are registered
- [ ] Overlay stays on top of other windows
- [ ] Screenshot hides overlay, captures, shows overlay again
- [ ] API responses appear in chat with correct colors and labels
- [ ] Conversation history is passed correctly on every API call
- [ ] Clear resets both UI and history list
- [ ] Export creates a readable Markdown file
- [ ] All colors match the hex values in PRD.md
- [ ] No tkinter calls from background threads (use root.after)
- [ ] Config.ini controls model, max_tokens, hotkeys, UI dimensions
- [ ] Overlay is invisible to OBS, Chrome screen share, and other screen capture software (test by recording with OBS or Chrome)
- [ ] Overlay remains visible to the user on their own screen while being hidden from recordings

When you make changes to any prompt file, create a git commit for those prompt changes before moving on to the next task.