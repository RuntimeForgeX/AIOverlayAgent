# Memory Design
## AI Screen Overlay Agent

This document describes how **conversation memory** works in the shipped application (`ai_overlay.py`). Use it when changing providers, export, or session behavior.

---

## The Core Problem

The selected AI API is **stateless**. The model does not remember prior turns unless we send them again.

Therefore, on **every** API call the app must send:

1. The **system prompt** (via the provider’s system-instruction mechanism — **not** stored in history)
2. The full **`conversation_history`** list for the current session

---

## Where Memory Lives

| Data | Location | Lifetime |
|------|----------|----------|
| Conversation turns | `APIProvider.conversation_history` | Until clear, model switch, or app exit |
| System prompt | `APIProvider.system_prompt` | Loaded at provider init; editable in Settings |
| Session counters | `OverlayApp` fields | Until clear or app exit |
| Persistent chat export | `%APPDATA%\<appdata_folder>\exports\` | On disk after export only |

`appdata_folder` comes from `app_config.ini` (default: `PersonalAiAgentSurya`).

There is **no** database and **no** automatic save of chat between app restarts.

---

## History Structure (LangChain)

History is a Python **list** on the active provider instance:

```python
self.conversation_history = []  # list of LangChain message objects
```

### Message types in history

| Type | Class | When added |
|------|--------|------------|
| User text | `HumanMessage(content="...")` | User sends typed message |
| User screenshot | `HumanMessage(content=[...])` | User triggers capture hotkey |
| Assistant reply | `AIMessage(content="...")` | Successful API response |

### What is **not** in history

- `SystemMessage` — system prompt is prepended only at invoke time:
  ```python
  messages = [SystemMessage(content=self.system_prompt)] + self.conversation_history
  ```
- Token totals, timestamps shown in UI, or session metadata

---

## Message Content Formats

### Text-only user message

```python
HumanMessage(content="How do I fix this error?")
```

### Screenshot user message (Anthropic / OpenAI via LangChain)

```python
HumanMessage(
    content=[
        {"type": "text", "text": "What is shown in this screenshot? ..."},
        {
            "type": "image_url",
            "image_url": {
                "url": "data:image/jpeg;base64,<base64_jpeg_string>"
            },
        },
    ]
)
```

Order in the list: **text first**, then **image_url**. JPEG base64 comes from `capture_and_compress_screenshot()` (max width 1280, quality 82 by default from `config.ini` `[CAPTURE]`).

### Gemini provider

Gemini uses `google.generativeai` directly (not LangChain for the invoke). History still stores `HumanMessage` / `AIMessage` for consistency; the provider converts to native image + text when calling `generate_content`.

### Assistant message

```python
AIMessage(content="The error on line 42 is ...")
```

---

## Message Flow

```
User types or presses capture hotkey
        ↓
(Optional) _ensure_llm() — load API key from env / .env if not ready yet
        ↓
Append user message to conversation_history
        ↓
trim_history() if len > 30
        ↓
Background thread: provider.send_message(...)
        ↓
Prepend SystemMessage + invoke API with full conversation_history
        ↓
On success: append AIMessage(reply), on_response → root.after → update UI
        ↓
On failure: pop last HumanMessage if present, on_error → root.after → in-app ⚠ message
```

**Never** call the API on the Tk main thread.

---

## Error Recovery

If the API call fails **after** the user message was appended:

```python
if self.conversation_history and isinstance(self.conversation_history[-1], HumanMessage):
    self.conversation_history.pop()
on_error(str(e))  # shows in chat panel only — no Windows system dialogs
```

Missing API key (lazy init):

- App **still launches**; `provider.llm` may be `None` until first send.
- First send calls `_ensure_llm()`; if still no key, user sees an in-app message naming the env var (e.g. `GEMINI_API_KEY`).

---

## Memory Reset (Clear)

Triggered by **Ctrl+Shift+C**, Clear button, or equivalent.

1. `provider.clear_history()` → `conversation_history = []`
2. Clear `ScrolledText` chat widget
3. Reset `OverlayApp` counters: `total_input_tokens`, `total_output_tokens`, `message_count`, `screenshot_count`
4. System line in chat: `conversation cleared · memory reset`
5. Status bar: `ready · 0 in / 0 out tokens`

---

## Model / Provider Switch

Changing the header model dropdown:

1. `load_environment()` (refresh keys)
2. Update `config.ini` sections `[API]`, `[API_OPENAI]`, or `[API_GEMINI]`
3. `self.provider = get_provider(self.config)` — **new** empty `conversation_history`
4. Clear chat UI and session counters
5. System line: `✓ switched to <model name>`

Memory does **not** carry across providers.

---

## History Size Management (Auto-Trim)

When `len(conversation_history) > 30`:

```python
conversation_history = conversation_history[:2] + conversation_history[-28:]
```

- **Keep** first 2 messages (early session context)
- **Keep** last 28 messages (recent context)
- **Drop** middle messages silently (no UI notification)

Called via `trim_history()` immediately before each API invoke.

---

## Session Metadata (OverlayApp — Not Sent to API)

Tracked on `OverlayApp`, **not** included in API payloads:

| Field | Meaning |
|-------|---------|
| `started_at` | `datetime` when app opened |
| `message_count` | User turns (text + capture) |
| `screenshot_count` | Capture hotkey uses only |
| `total_input_tokens` | Sum from API metadata (Gemini may report `0`) |
| `total_output_tokens` | Sum from API metadata |

Status bar after each success:

`ready · <input> in / <output> out tokens`

---

## Export (Persistent Memory)

**Hotkey:** Ctrl+Shift+E  
**Folder:** `%APPDATA%\<appdata_folder>\exports\` (created if missing)  
**Filename:** `chat_YYYYMMDD_HHMMSS.md`

### Export content rules

- Header: `# AI Overlay Export`, date, `---`
- For each item in `conversation_history`:
  - `HumanMessage` → `**You:**`
  - `AIMessage` → `**AI:**`
  - String `content` → write as-is
  - List `content` (multimodal):
    - `type == "text"` → write text
    - `type == "image_url"` or image blocks → write `[screenshot]` only (no base64 in file)

Success feedback: in-app system message `✓ Exported to <full path>`.

Implementers iterating history must use **`isinstance(msg, HumanMessage)`** / **`AIMessage`**, not `msg["role"]` dict access.

---

## Configuration and API Keys (Affects Memory Only Indirectly)

Keys are read via `get_api_key()` after `load_environment()`:

1. **Windows user/system environment variables** (already in `os.environ`) — highest priority
2. **Optional `.env` files** (`override=False`) — only set vars not already defined:
   - `%APPDATA%\<appdata_folder>\.env`
   - Next to installed `.exe` (frozen app)
   - Project root `.env` (development)

`config.ini` resolution order:

1. `%APPDATA%\<appdata_folder>\config.ini`
2. Next to `.exe` (frozen)
3. Bundled copy inside the app / PyInstaller extract

---

## Threading and Hotkeys

| Rule | Detail |
|------|--------|
| API work | `threading.Thread(..., daemon=True)` |
| UI updates from API thread | `self.root.after(0, lambda: ...)` |
| Global hotkeys | `keyboard` library — `keyboard.add_hotkey(...)` |
| Hotkey → UI | Always wrap handler with `_schedule_on_main_thread(...)` |
| Packaged builds | PyInstaller `runtime_keyboard_fix.py` hook for 64-bit Windows |

Hotkeys are registered ~200 ms after UI build (`root.after(200, self.register_hotkeys)`). On exit, stored removers unregister hotkeys.

---

## PyInstaller / Installed App Notes

- `prompts/system_prompt.md` is bundled under `prompts/` in the one-file extract (`sys._MEIPASS`).
- Conversation history remains **RAM-only** unless the user exports.
- Rebuild after prompt or memory-behavior changes: `build\build_exe.bat` then `build\build_installer.bat`.

---

## Quick Reference Checklist for Developers

- [ ] System prompt never appended to `conversation_history`
- [ ] Failed turn removes dangling `HumanMessage`
- [ ] `trim_history()` before every invoke when len > 30
- [ ] Screenshot path: withdraw overlay → delay → grab → deiconify → re-apply capture exclusion
- [ ] All chat errors shown in overlay, not `messagebox`
- [ ] Export uses LangChain message types and `%APPDATA%` exports path
