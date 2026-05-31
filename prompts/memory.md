# Memory Design
## AI Screen Overlay Agent

---

## The Core Problem

The selected AI API is **completely stateless**.  
The model remembers nothing between API calls.  
Therefore, the application must manually pass the entire conversation history on every single request.

---

## The Solution: conversation_history List

Maintain one Python list in memory:

```
conversation_history = []
```

This list holds every message ever sent in the current session.  
On every API call, pass the entire list as the `messages` parameter.  
When the user clears chat, set this list back to `[]`.

---

## Message Format Rules

The list must follow the internal canonical message format used by the app. The provider adapter translates it into the selected API's schema.

### Text-only message (user typed a question):
```
{
    "role": "user",
    "content": "How do I fix this error?"
}
```

### Screenshot message (user pressed capture hotkey):
```
{
    "role": "user",
    "content": [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": "<base64 string of compressed JPEG screenshot>"
            }
        },
        {
            "type": "text",
            "text": "What is wrong on my screen?"
        }
    ]
}
```

### AI response message:
```
{
    "role": "assistant",
    "content": "The error you see is a NullPointerException on line 42..."
}
```

---

## Message Flow

```
User action (type or capture)
        ↓
Append user message to conversation_history
        ↓
Call the selected provider API with full conversation_history
        ↓
Get reply from API
        ↓
Append assistant reply to conversation_history
        ↓
Display reply in chat panel
        ↓
[Repeat for every turn]
```

---

## Error Recovery

If the API call fails, remove the last user message from history.  
This prevents the history from getting out of sync (user message without a reply).

```
on API error:
    if last message in history has role == "user":
        remove it from history
    show error message in chat panel
```

---

## Memory Reset

Three things happen when user clears:

1. Set `conversation_history = []`
2. Clear the chat display widget
3. Show system message: "conversation cleared · memory reset"

---

## History Size Management

Large-context models from Anthropic, OpenAI, and Gemini support long histories.  
A screenshot uses roughly 1,000–2,000 tokens.  
A text message uses roughly 50–200 tokens.

For safety, implement auto-trimming when history exceeds 30 messages:
- Always keep the first 2 messages (they set early context)
- Keep the most recent 28 messages
- Drop everything in between silently

---

## Session Metadata (Track Separately)

Keep a second dict for session stats — do NOT include this in API calls:

```
session = {
    "started_at": datetime when app launched,
    "message_count": integer, increments each turn,
    "screenshot_count": integer, increments each capture,
    "total_input_tokens": running total from API responses,
    "total_output_tokens": running total from API responses
}
```

Show token totals in the status bar after each response.

---

## Persistent Memory (Export Only)

The app does NOT save memory between sessions by default.  
When the user exports (Ctrl+Shift+E), save to a Markdown file.

Export rules:
- Save to `exports/` folder (create if not exists)
- Filename: `chat_YYYYMMDD_HHMMSS.md`
- For messages with screenshots: write `[screenshot]` as placeholder — do NOT save the base64 image data (too large, not useful in a text file)
- For text messages: write the content as-is

---

## The system Prompt Is NOT In History

The system prompt is passed using the provider's native system-instruction field in every API call.  
It is never added to `conversation_history`.  
This means it takes no space in the visible chat history but always influences AI behavior.

---

## Threading Rule

All API calls must run in a background thread.  
Never call the provider API on the main thread — it will freeze the UI.

Pattern:
```
threading.Thread(target=api_call_function, args=(question,), daemon=True).start()
```

All UI updates from background threads must use `root.after(0, callback)` — never update tkinter widgets directly from a background thread.