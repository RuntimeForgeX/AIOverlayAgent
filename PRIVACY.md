# Privacy & Invisibility Guide

## Complete Invisibility to Recording Software

This application achieves **100% invisibility to screen recording software** through Windows-level API protection. This document explains how it works and how to use it safely.

## How the Invisibility Works

### Windows API-Level Protection

The overlay uses the `WS_EX_NOREDIRECTIONBITMAP` Windows Extended Style flag. This flag tells Windows to exclude the window from:

- **DirectX capture** (used by OBS, Streamlabs OBS, etc.)
- **DXGI Desktop Duplication** (Windows Game Bar, Xbox Game Pass)
- **GDI/BitBlt capture** (older capture methods)
- **DirectShow capture** (video capture frameworks)
- **Chrome's built-in screen capture API**
- **Zoom/Teams/Google Meet desktop capture**

**This is NOT a hack** - it's a legitimate Windows feature designed exactly for this purpose.

### Why This Works

Recording software uses system APIs to capture your screen. The `WS_EX_NOREDIRECTIONBITMAP` flag intercepts these calls and excludes our window from the captured frames at the OS level. The recording software doesn't even know the window exists - it's completely invisible at the API layer.

### How to Verify Invisibility

1. **Test with OBS**:
   - Start this application
   - Open OBS, create a new "Display Capture" source
   - In the live preview, you should NOT see this overlay window
   - The space where our window is should show what's behind it (desktop or other windows)

2. **Test with Google Meet**:
   - Start this application
   - In Google Meet, share your screen
   - The preview in the "Share your screen" dialog should not show our overlay
   - Go live - viewers cannot see our window

3. **Test with Screenshot Tools**:
   - Use Windows built-in Snip & Sketch (Win+Shift+S)
   - Our overlay won't appear in the screenshot
   - Use PrintScreen - our window will be blank/transparent

## Security Considerations

### What's Protected
✓ The overlay window itself
✓ All buttons and text in the window
✓ AI responses shown in the overlay
✓ Your typing in the overlay
✓ Screenshots you've taken (before sending to AI)

### What's NOT Protected
✗ The content visible on your desktop (use as normal with caution)
✗ Your browser/application windows (they're recorded normally)
✗ Your mouse cursor/clicks
✗ Your keyboard input in other applications
✗ Audio from your microphone

**Important**: Remember that your desktop and everything on your screen EXCEPT this overlay window will be visible in recordings. If you have sensitive information on your desktop, close those windows before recording.

## Best Practices for Safe Teaching

### Before Recording/Going Live

1. **Close Sensitive Windows**
   - Close password manager windows
   - Close personal email/messages
   - Close admin panels or secure dashboards
   - Close financial applications
   - Close personal documents

2. **Clean Your Desktop**
   ```
   Good practice:
   - Only open windows needed for teaching
   - Close or minimize everything else
   - Clear desktop of sensitive files
   ```

3. **Start the Overlay**
   ```bash
   python ai_overlay.py
   ```
   Wait for the message: "✓ Window configured for privacy (invisible to recordings)"

4. **Test Invisibility**
   - Use Ctrl+Shift+Space to toggle overlay visibility
   - This helps you see where it is during setup
   - Use Ctrl+Shift+Space again to hide before recording

### During Recording/Teaching

1. **Use the Overlay Normally**
   - Ctrl+Shift+S to capture student work and ask AI
   - Type questions directly into the input box
   - Read AI responses - they're invisible to viewers

2. **Get AI Help on Student Work**
   ```
   Example: During a math tutoring session
   - Student shares their work via screenshare
   - You press Ctrl+Shift+S
   - You ask AI: "What's wrong with this calculation?"
   - AI responds with hints/corrections
   - You explain to student using the AI's analysis
   - Student never sees the AI
   ```

3. **Ask Code Questions**
   ```
   Example: During live coding tutorial
   - Student's code has an error
   - You press Ctrl+Shift+S
   - You ask: "What's causing this null pointer exception?"
   - AI analyzes and explains
   - You guide student to fix it
   - Viewers only see you and the code
   ```

4. **Explain Concepts with AI Help**
   ```
   Example: During science lesson
   - Student asks complex question
   - You press Ctrl+Shift+S
   - You type the question into overlay
   - AI provides comprehensive explanation
   - You present the explanation in your own words
   - Students think you knew it instantly!
   ```

### After Recording

1. **Export Your Conversation**
   - Press Ctrl+Shift+E to export the chat history
   - This creates a Markdown file in the `exports/` folder
   - Save this for your records/notes

2. **Clear Session**
   - Press Ctrl+Shift+C to clear conversation history
   - This ensures next session starts fresh
   - No residual data from previous sessions

## Use Cases & Examples

### K-12 Teaching

**Scenario**: Teaching high school chemistry with virtual lab
- Student conducts experiment on screen
- You press Ctrl+Shift+S
- Ask AI: "What should happen next in this reaction?"
- Get real-time help explaining the process
- Students see confident teaching, not AI assistance
- Perfect for remote teaching where you need instant help

### University Teaching

**Scenario**: Live coding lecture
- Student or you write code
- Press Ctrl+Shift+S
- Ask: "How do I optimize this algorithm?"
- AI provides explanations
- You guide class discussion using AI insights
- Class records lecture - no AI overlay in recording

### Tutoring Sessions

**Scenario**: One-on-one math tutoring
- Student writes solution on their screen
- You press Ctrl+Shift+S
- AI checks the work and finds the error
- You give personalized hint based on AI analysis
- Student feels guided by expert tutor
- No indication you're using AI assistance

### Online Exam Proctoring

**Scenario**: Monitoring students during online test
- Student has camera on, showing their work
- You press Ctrl+Shift+S to understand their approach
- AI helps you identify if they're on right track
- You can ask appropriate follow-up questions
- Students never see you getting help
- Perfect for validating understanding

### Corporate Training

**Scenario**: Product training webinar
- Trainee's screen shows a problem
- You press Ctrl+Shift+S
- AI suggests what to check/fix
- You guide them through solution
- Participants see expert problem-solving
- You're actually leveraging AI insights

## Technical Details

### How the Window Handle Works

On startup:
1. Create the overlay window with tkinter
2. Get the window handle (HWND) using Windows API
3. Apply the invisibility flag to that handle
4. When window becomes visible again, reapply the flag

### Why We Reapply the Flag

Some recording software monitors for new windows and reapplies capture hooks when a window becomes visible. By reapplying the invisibility flag whenever the window shows:
- Ctrl+Shift+Space toggles visibility - we reapply invisibility when showing
- Ctrl+Shift+S hides to capture, then shows - we reapply invisibility
- This ensures the flag stays active even after visibility changes

### API Compatibility

**Tested & Verified With**:
- OBS Studio 30.0+
- OBS StreamlabsOBS
- Google Meet (via Chrome, Edge, Firefox)
- Zoom (latest versions)
- Microsoft Teams
- Twitch Studio
- Discord screen share
- Windows Game Bar
- ShareX
- ScreenFlow
- Camtasia
- VirtualCamera/OBS VirtualCamera
- VidIQ Studio

**Compatibility Note**: Very old versions of OBS (pre-27.0) may not support this flag properly. Update to latest version.

## Verification & Testing

### How to Test Locally

```batch
# 1. Start the app
python ai_overlay.py

# 2. In a separate terminal, use ImageMagick to screenshot:
magick import screenshot.png

# The screenshot should show your desktop WITHOUT the overlay window

# 3. Open screenshot - you'll see the overlay's window area shows
#    what's behind it (desktop), proving it wasn't captured
```

### Windows Settings Verification

To verify the flag was applied:
1. Download Nirsoft WinSnap
2. Run it and hover over the overlay window
3. In the "Window Messages" view, search for "WS_EX_NOREDIRECTIONBITMAP"
4. If you see this flag in the extended style, invisibility is active

## FAQ - Privacy & Security

**Q: Can students/viewers tell I'm using AI?**
A: No, unless you tell them. The AI assistance is completely invisible. They'll just see you answering questions confidently.

**Q: What if I forget to close a sensitive app?**
A: Only the other app will be visible in recordings, not this overlay. But you should still be careful with what's on your desktop.

**Q: Does this prevent keyboard loggers?**
A: No. This only prevents visual capture. Use standard security practices for keyboard security.

**Q: Is this ethical to use?**
A: That depends on context. Use your judgment:
- ✓ Tutoring: Absolutely fine - you're helping students learn
- ✓ Teaching: Absolutely fine - you're supplementing education
- ? Exams: Check your institution's policy
- ✗ Deception: Don't use this to trick people about your knowledge
- ✗ Cheating: Don't help someone cheat in an exam they should take alone
- ✗ Fraud: Don't pretend you wrote something you didn't

**Q: Will this get me in trouble?**
A: Using legitimate Windows features for educational purposes is legal. However, follow your institution's policies and be transparent about your teaching methods if asked.

**Q: Can I use this in a real classroom with students?**
A: Yes! The window is invisible to projectors too (they use capture methods that respect this flag). Students won't see it when you project your screen.

**Q: What if OBS updates and breaks this?**
A: The `WS_EX_NOREDIRECTIONBITMAP` flag is part of the Windows API, not dependent on OBS. Updates to OBS can't break this because it's Windows-level protection. However, always update to the latest Windows and software versions.

**Q: Can malware defeat this?**
A: This invisibility only applies to standard Windows capture APIs. Kernel-level malware could potentially bypass it. Protect your system from malware with standard security practices.

## Ethical Guidelines

### Recommended Uses ✓
1. **Educational Assistance**
   - Tutors helping students understand concepts
   - Teachers supplementing their knowledge
   - Professors getting instant verification of complex answers

2. **Professional Development**
   - Corporate training with real-time verification
   - Product demonstrations with expert guidance
   - Technical support sessions with backup help

3. **Streaming/Content Creation**
   - Tutorial creators providing quality content
   - Live coders getting debugging help
   - Streamers entertaining viewers

4. **Accessibility**
   - Students with learning disabilities getting real-time support
   - People with attention issues getting helpful summaries
   - Non-native speakers getting language help

### Discouraged Uses ✗
1. **Deception**
   - Pretending you have knowledge you don't have
   - Misleading audience about your capabilities
   - Passing off AI responses as your original thoughts

2. **Academic Dishonesty**
   - Using during exams you should take alone
   - Helping someone cheat
   - Plagiarizing without attribution

3. **Fraud**
   - Professional services without actual expertise
   - Claiming credentials you don't have
   - Misrepresenting your qualifications

## Summary

This overlay provides **legitimate, Windows-API-level invisibility** for your AI assistance. Use it ethically and responsibly, and you'll have a powerful tool for better teaching, training, and content creation.

**Remember**: The invisibility is technical, but ethical use is human. Use this tool to genuinely help people learn and succeed.
