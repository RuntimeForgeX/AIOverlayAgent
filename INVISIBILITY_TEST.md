# Invisibility Test Guide

Verify that the overlay is **hidden from screen recording and sharing** while remaining visible to you locally.

---

## Requirements

- Windows **10 build 19041+** (2004) or **Windows 11**
- AI Overlay Agent running (`main.py` or installed exe)
- A capture tool: **OBS Studio**, **Google Meet**, **Zoom**, or **Windows Snipping Tool** (full screen)

---

## How it works (short)

The app sets **DWM display affinity** `WDA_EXCLUDEFROMCAPTURE` on all HWNDs belonging to the process. See [PRIVACY.md](PRIVACY.md).

On startup you may see in chat (verbose/dev):

`[OK] Initialized · INVISIBLE TO RECORDINGS · Ready`

If you see `INVISIBILITY NOT CONFIRMED`, exclusion may not be active — check Windows version and logs.

---

## Test A — OBS (recommended)

1. Start **OBS Studio** → add **Display Capture** (full monitor).
2. Start AI Overlay Agent; position overlay clearly on screen (bright content helps).
3. Look at the OBS preview:
   - **Pass:** Overlay is **not** visible (desktop shows; overlay area empty or shows desktop behind).
   - **Fail:** Overlay appears in preview.
4. Start recording 30 seconds; review file — same pass/fail criteria.

**Tips:**

- Use **Display Capture**, not Window Capture of another app only.
- Re-toggle overlay visibility (`Ctrl+Shift+Space`) and check OBS again (re-applies flags).

---

## Test B — Google Meet / Zoom

1. Join a test meeting or use “Preview” / test call.
2. Share **Entire screen** or **Display** (not single application window).
3. Ask a friend or second device whether they see the overlay on your shared screen.
   - **Pass:** They do not see the overlay.
   - **Fail:** They see the floating panel.

---

## Test C — Local visibility (control)

1. With overlay visible, confirm **you** see it on your physical monitor.
2. This confirms exclusion is not “hiding from user” — only from capture pipeline.

---

## Test D — Screenshot hotkey

1. Open Notepad or a browser with obvious content.
2. Press `Ctrl+Shift+S`.
3. **Pass:** AI describes Notepad/browser — overlay was hidden during capture and not in the image sent to AI.

---

## Test E — After hide/show

1. `Ctrl+Shift+Space` to hide overlay → show again.
2. Repeat Test A or B without restarting the app.
3. **Pass:** Still excluded from capture (flags re-applied on show/focus/poll).

---

## Common failures

| Symptom | Likely cause |
|---------|----------------|
| Visible in OBS window capture of Chrome only | Wrong capture mode — use **display** capture |
| Visible on old Windows 10 | Need build 19041+ |
| Black rectangle in capture | Partial exclusion; update Windows / retry |
| Works in dev, not in exe | Rebuild; run app once and re-test |
| Intermittent in Meet | Re-focus overlay; wait for 3s poll re-apply |

---

## Checklist

- [ ] OBS display capture — overlay absent
- [ ] Meet/Zoom full screen share — overlay absent for viewers
- [ ] User still sees overlay locally
- [ ] `Ctrl+Shift+S` captures content without overlay in AI analysis
- [ ] Hide/show cycle does not break exclusion

---

## Reporting issues

Note: Windows version, capture app, share mode (full screen vs window), installed vs `py -3 main.py`, and whether chat said `INVISIBLE TO RECORDINGS` or `NOT CONFIRMED`.
