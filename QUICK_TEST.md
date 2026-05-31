# Quick Testing Guide - Invisibility Verification

## Current Status ✓
- App is **RUNNING** with improved invisibility
- All Windows API flags applied successfully
- Ready for testing

## Quick Test (2 minutes)

### Step 1: Open Google Meet
1. Go to https://meet.google.com
2. Start/join a meeting
3. Click "Present now" → "Your entire screen"

### Step 2: Look at Preview
The preview window should show your desktop WITHOUT the overlay window visible.

**Expected Result**: Where the overlay window is, you should see:
- The desktop background (or what's behind)
- NOT the "AI OVERLAY" window
- NOT the chat interface
- NOT any overlay controls

### Step 3: Confirm Invisibility
- If you can see the overlay in the preview: **FAIL** - Invisibility not working
- If you DON'T see the overlay in the preview: **PASS** - Invisibility working!

---

## What You'll See

### BEFORE Improvements (WRONG ❌)
```
[Google Meet Preview]
┌─────────────────────────────────────┐
│ AI OVERLAY                          │ ← Visible (BAD)
│ ● AI OVERLAY                        │ ← Visible (BAD)  
│ [Chat Area]                         │ ← Visible (BAD)
│ [Buttons] [Send]                    │ ← Visible (BAD)
│ Desktop Background                  │
└─────────────────────────────────────┘
```

### AFTER Improvements (CORRECT ✓)
```
[Google Meet Preview]
┌─────────────────────────────────────┐
│ Desktop Background                  │
│ (Overlay is here but NOT captured)  │
│ Desktop Background                  │
│ Desktop Background                  │
│ Desktop Background                  │
└─────────────────────────────────────┘
```

---

## Hotkey Test (While Testing)

While the Google Meet preview is open:

1. **Ctrl+Shift+S** - Capture screen and ask AI a question
   - The overlay hides, captures screen, shows again
   - You should see it happen on YOUR screen
   - Google Meet preview should NOT show it

2. **Ctrl+Shift+Space** - Toggle overlay visibility
   - On your screen: overlay appears/disappears
   - Google Meet preview: should remain empty

---

## Test Results

After testing, you should see:

✓ Overlay visible on YOUR screen (in the app window)
✓ Overlay INVISIBLE to Google Meet preview  
✓ Overlay INVISIBLE to recording (if you start recording)
✓ Hotkeys work properly
✓ App responds to commands

---

## If Invisibility Works ✓

Great! The app is ready for:
- Live teaching with AI assistance invisible to students
- Streaming/recording tutorials without AI visible
- Tutoring sessions with invisible AI help
- Any screen sharing where privacy is needed

**Next**: Start using it for teaching!

---

## If Invisibility Doesn't Work ✗

Try these fixes:

1. **Restart the App**
   ```
   - Press Ctrl+C in the terminal
   - Run: .venv\Scripts\python.exe ai_overlay.py
   ```

2. **Update Recording Software**
   - Chrome/Edge/Firefox to latest version
   - Restart browser completely
   - Try Google Meet again

3. **Check Windows Version**
   - Press Win+R, type `winver`
   - Must be Windows 10 build 1803+ (or Windows 11)
   - If older: Some invisibility features unavailable

4. **Update GPU Drivers**
   - NVIDIA/AMD/Intel drivers to latest
   - Restart computer
   - Try again

5. **Try Different Browser**
   - If Chrome doesn't work: Try Edge or Firefox
   - Different browsers may have different behavior

---

## Advanced Test: OBS Studio

If you have OBS installed:

1. Open OBS
2. Click "+" under Sources
3. Add "Display Capture"
4. Select your monitor
5. Look at the preview in OBS
6. Overlay window should NOT appear

Expected: The overlay area should appear transparent/blank, showing what's behind it.

---

## Invisible = Private Teaching ✓

Once invisibility is confirmed, you can:

✓ Answer student questions with AI help they can't see
✓ Debug code with invisible AI assistance
✓ Explain concepts using AI-generated hints
✓ Stream tutorials with AI support viewers don't see
✓ Teach confidently with real-time AI backup

**Important**: Only use for legitimate teaching/learning support!

---

## Contact If Issues

If the overlay remains visible after trying all fixes:
1. Record a screenshot showing overlay in Google Meet preview
2. Check the terminal for error messages
3. Try on a different computer if possible
4. Windows version matters: Windows 11 > Windows 10

---

## Quick Command Reference

| Hotkey | Action |
|--------|--------|
| `Ctrl+Shift+Space` | Toggle overlay visibility |
| `Ctrl+Shift+S` | Capture screen & ask AI |
| `Ctrl+Shift+C` | Clear chat history |
| `Ctrl+Shift+I` | Focus input box |
| `Ctrl+Shift+E` | Export conversation |

---

## You're Ready! 🚀

The app is running with maximum invisibility hardening. Test it with Google Meet and let me know the results!

**Expected outcome**: Nobody sees your AI helper except you.
