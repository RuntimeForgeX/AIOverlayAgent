# Quick Test Checklist

Smoke-test the app in **under 10 minutes** (development or installed build).

---

## Before you start

- [ ] Windows 10 2004+ or Windows 11
- [ ] API key set (`GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`) in env or `.env`
- [ ] `config.ini` provider matches your key (`[API] provider = gemini` etc.)

**Run:**

```bat
py -3 main.py
```

Or launch `dist\PersonalAiAgentSurya.exe` / Start Menu shortcut after install.

---

## 1. Launch

- [ ] Overlay opens with no Windows error popup
- [ ] Status bar shows `ready` (or `ready · set API key in environment` if no key)
- [ ] Chat area visible; header shows model dropdown and theme icon

---

## 2. Hotkeys

| Key | Expected |
|-----|----------|
| `Ctrl+Shift+Space` | Hides overlay; press again to show |
| `Ctrl+Shift+I` | Focuses text input |
| `Ctrl+Shift+C` | Clears chat; system message about reset |

Test hotkeys while **another app** (e.g. Notepad) has focus.

---

## 3. Text chat

- [ ] Type a short question → Enter or Send
- [ ] Status shows `thinking...` then token counts or error in chat
- [ ] With valid key: AI reply appears with markdown/code styling
- [ ] With no key: warning in chat only (no system dialog)

---

## 4. Screenshot

- [ ] `Ctrl+Shift+S` — overlay hides briefly, reappears, thumbnail may appear in queue
- [ ] With valid key: AI responds about screen content
- [ ] Overlay not visible inside the captured image you intended to share (visual check on your monitor)

---

## 5. Model switch

- [ ] Change model in header dropdown (e.g. Gemini → GPT)
- [ ] No `load_environment` or other crash
- [ ] Chat clears; system message confirms switch

---

## 6. Export

- [ ] Send at least one message
- [ ] `Ctrl+Shift+E` — system message with path under `%APPDATA%\...\exports\`
- [ ] `.md` file opens and readable

---

## 7. Settings (optional)

- [ ] Open Settings from quick buttons
- [ ] Toggle a section; Save
- [ ] Edit System Prompt; Save — no crash

---

## 8. Installed build only

- [ ] Run `release\PersonalAiAgentSurya_Setup.exe` — install completes
- [ ] Desktop / Start Menu shortcut launches app
- [ ] Hotkeys work from installed exe (not only `py -3 main.py`)
- [ ] Uninstall removes app from Settings → Apps

---

## Pass criteria

**Pass:** All items in sections 1–5 work; no system error dialogs; errors only in chat panel.

**Investigate:** Hotkeys fail only in `.exe` → rebuild with latest `build\` scripts; see [RELEASE_BUILD.md](RELEASE_BUILD.md).

**Investigate:** Overlay visible in OBS → full display capture, Windows version, [INVISIBILITY_TEST.md](INVISIBILITY_TEST.md).
