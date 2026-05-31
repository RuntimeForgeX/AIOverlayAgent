# AI Overlay Agent

A Windows desktop overlay application that uses AI to help answer questions about what you see on screen. The overlay remains **completely invisible to screen recording software** like OBS, Google Meet, Zoom, and Chrome, making it perfect for recording tutorials, teaching, and streaming without students/viewers seeing the AI assistance.

## Key Feature: Privacy During Teaching & Recording

This is the #1 tool for educators and content creators who need:
- **Secret AI assistance** while teaching or presenting live
- **Zero visibility to viewers** when recording with OBS, Google Meet, Zoom, or any recording software
- **Real-time help** analyzing student work, code errors, or clarifying concepts
- **Undetectable** - recording software cannot capture the overlay window

The overlay uses **Windows API-level invisibility** making it impossible for any third-party screen capture software to detect or record.

## Prerequisites

- Windows 10 or 11
- Python 3.10 or higher
- An API key from Anthropic, OpenAI, or Google Gemini

## Install as a Windows App

**Full step-by-step guide:** [installOnSystem.md](installOnSystem.md)

Use this to install the overlay like a normal desktop app (Desktop shortcut, Start Menu, optional startup).

### Requirements

- Windows 10 (2004+) or Windows 11
- Python 3.10+ ([python.org/downloads](https://www.python.org/downloads/)) — check **Add python.exe to PATH** during install
- An API key from Anthropic, OpenAI, or Google Gemini

### One-time install

1. Download or clone this folder to a permanent location, for example:
   ```
   C:\Apps\ai-overlay-agent
   ```
   Avoid temp folders — shortcuts point to this path.

2. Double-click **`install.bat`**

3. Wait for dependencies to install (first run can take a few minutes).

4. When prompted, choose **Y** if you want the app to start automatically when Windows boots (optional).

5. Open **`.env`** in the app folder and add your API key:
   ```
   GEMINI_API_KEY=your-key-here
   ```
   (Or `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` depending on provider in `config.ini`.)

6. Double-click **`AI Overlay Agent`** on your Desktop (or find it in the Start Menu).

The app runs without a terminal window. Use **AI Overlay Agent (Debug)** in the Start Menu if you need console logs.

### After install

| What | How |
|------|-----|
| Launch app | Desktop or Start Menu → **AI Overlay Agent** |
| Show/hide overlay | `Ctrl+Shift+Space` |
| Capture screen to AI | `Ctrl+Shift+S` |
| Change model / settings | Use the header dropdown and **Settings** button |
| Edit config | `config.ini` in the app folder |
| Remove shortcuts only | Run **`uninstall.bat`** (keeps app files and `.env`) |
| Re-install / update deps | Run **`install.bat`** again |

### Manual install (developers)

1. Clone or download this project:
   ```bash
   git clone <repo-url>
   cd ai-overlay-agent
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API key:
   ```bash
   copy .env.example .env
   ```

5. Edit `.env` and add your API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
   ```

## How to Run

**Installed app:** use the Desktop or Start Menu shortcut.

**From terminal** (development):

```bash
.venv\Scripts\activate
python ai_overlay.py
```

Or double-click **`run_debug.bat`** for console output, **`run.bat`** for no console.

The overlay will appear in the top-left corner of your screen. It will be **invisible to any recording software**.

## Usage Scenarios

### During Online Teaching (Google Meet, Zoom, Teams)
1. Start the overlay before your lesson
2. Share your screen normally - the overlay **won't appear** to students
3. Use Ctrl+Shift+S to capture student work/screen and get AI analysis
4. Ask AI questions silently while teaching
5. Students never see your AI assistant

### Recording Tutorials with OBS
1. Start the overlay application
2. Add screen capture source in OBS - the overlay is automatically hidden
3. Use Ctrl+Shift+S to ask AI about code, errors, or explanations
4. Recorded video will not show the overlay
5. Get professional help while recording, no editing needed

### Live Coding & Streaming
1. Start overlay before streaming
2. Go live on Twitch/YouTube/Facebook - overlay is invisible
3. Get real-time AI help with debugging or explanations
4. Viewers only see your code and screen, not your AI helper
5. Perfect for pair-programming or mentoring streams

### Exam Proctoring / Academic Integrity
- Tutors/instructors can use this to guide students without them seeing the AI
- Students can get hints without AI assistance being obvious to proctors
- Perfect for online learning environments

## Hotkeys

| Hotkey | Action |
|--------|--------|
| `Ctrl+Shift+Space` | Toggle overlay window visible/hidden |
| `Ctrl+Shift+S` | Hide overlay, capture screen, show overlay, send screenshot to AI |
| `Ctrl+Shift+C` | Clear conversation history and memory |
| `Ctrl+Shift+I` | Focus the text input box |
| `Ctrl+Shift+E` | Export current conversation to a Markdown file |

**Quick Tips:**
- Use Ctrl+Shift+Space to toggle visibility when you need to see the overlay during setup, but it stays hidden during recording
- Use Ctrl+Shift+S frequently during teaching to analyze student work in real-time
- Type questions directly while overlay is hidden - your typing won't be captured either

## Configuration

Edit `config.ini` to customize:

- **Provider**: Choose `anthropic`, `openai`, or `gemini`
- **Model**: Set the model name for your chosen provider
- **Max tokens**: Adjust response length (default: 1500)
- **Window size and position**: Customize UI dimensions
- **Hotkeys**: Rebind any keyboard shortcut
- **Screenshot compression**: Adjust JPEG quality and max width
- **Opacity**: Change window opacity (0.0-1.0) for visibility during setup

## AI Behavior

Edit `prompts/system_prompt.md` to customize how the AI behaves. The app loads the system prompt from the first code block in that file. No code changes needed—just restart the app to apply changes.

Variants available:
- **Default**: Concise overlay assistant for coding and general tasks
- **Teacher Mode**: Patient tutor for educational content, good for explaining concepts
- **Developer Mode**: Focus on debugging and code analysis
- **Learning Mode**: Help with writing, documents, and planning
- **Tutor Mode**: Specifically designed for tutoring - explains concepts clearly and concisely

## How the Invisibility Works

The application uses **Windows API-level invisibility** through the `WS_EX_NOREDIRECTIONBITMAP` window style flag. This is a legitimate Windows feature that:

- Prevents the window from being captured by DirectX/GDI screen capture APIs (used by OBS, Chrome, etc.)
- Applies automatically when the application starts
- Reapplies whenever the window becomes visible
- Does not hide the window from Windows itself (you can still interact with it normally)
- Does not affect your actual screen visibility (you see it normally)

**Important:** The recording software simply cannot see this window - it's not hidden, it's just not captured at the API level.

### Verified Compatible With:
✓ OBS (Open Broadcaster Software)
✓ Google Meet  
✓ Zoom
✓ Microsoft Teams
✓ Twitch Studio
✓ Discord Screen Share
✓ Windows Game Bar
✓ ShareX
✓ ScreenFlow
✓ Camtasia
✓ VidIQ
✓ Any DX11/DX12/GDI based screen capture

## Privacy & Security

- **Your data**: Conversation history stays on your computer during the session
- **Screenshots**: Only sent to your chosen API provider (Anthropic/OpenAI/Google)
- **API keys**: Stored in `.env` which is listed in `.gitignore` and never committed to git
- **Sessions**: Clear conversation history with Ctrl+Shift+C between sessions
- **Best practice**: Use Ctrl+Shift+C before and after confidential teaching sessions

**Security reminder**: Never have passwords, credentials, or sensitive personal data visible on your screen when using the overlay or any recording software.

## Troubleshooting

### Overlay Still Visible in Recording
- Ensure you're using a modern Windows version (10 or 11)
- Try updating your graphics drivers
- Restart the application
- For OBS specifically: Make sure you're using a "Display Capture" or "Screen Capture" source, not "Game Capture"

### Window Handle Not Found
- This is a warning only, the app will still work
- The invisibility flag may not have been applied
- Restart the application to try again

### API Connection Issues
- Check your `.env` file has the correct API key
- Verify internet connection
- Check your API provider's status/quota
- See provider-specific instructions below

### Audio/Input Not Detected
- Hotkeys require the application to have focus or be system-wide registered
- Make sure no other application is using the same hotkey combinations
- Edit `config.ini` to use different hotkey combinations if needed

### Performance Issues
- Reduce screenshot resolution in `config.ini`
- Reduce screenshot JPEG quality (higher = better quality, slower = faster compression)
- Check that your API provider isn't rate-limiting
- Close other resource-heavy applications

## API Provider Setup

### Anthropic (Claude)
1. Go to https://console.anthropic.com
2. Create API key
3. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
4. Set in `config.ini`: `provider=anthropic` and `model=claude-opus-4-5`

### OpenAI (ChatGPT)
1. Go to https://platform.openai.com/api/keys
2. Create API key
3. Add to `.env`: `OPENAI_API_KEY=sk-...`
4. Set in `config.ini`: `provider=openai` and `model=gpt-4o`

### Google Gemini
1. Go to https://aistudio.google.com/apikey
2. Create API key
3. Add to `.env`: `GEMINI_API_KEY=...`
4. Set in `config.ini`: `provider=gemini` and `model=gemini-3-pro`

## Advanced Customization

### Custom Hotkeys
Edit the `[HOTKEYS]` section in `config.ini`:
```ini
[HOTKEYS]
toggle = ctrl+alt+o
capture = ctrl+alt+s
clear = ctrl+alt+c
focus = ctrl+alt+i
export = ctrl+alt+e
```

### Custom System Prompts
Edit `prompts/system_prompt.md` and wrap your prompt in a code block:
```
# Teaching Assistant Prompt

This is my custom prompt...
```

### Window Positioning
Auto-position to top-right corner - edit `config.ini`:
```ini
[UI]
start_x = 1280
start_y = 60
width = 500
height = 650
```

## Limitations

- Windows only (uses Windows-specific APIs)
- Requires Python 3.10+
- Requires active internet for API calls
- Screenshots are compressed to JPEG (max 1280px wide by default)
- Conversation history is in-memory only (cleared when app closes, unless exported)

## Use Cases

1. **Online Teaching**: Teach with AI assistance invisible to students
2. **Content Creation**: Tutorial creators can get AI help without editing
3. **Live Coding**: Streamers can debug with AI help viewers don't see
4. **Tutoring**: Tutors can help students with hints they provide invisibly
5. **Exam Prep**: Students can get hints without proctors seeing
6. **Code Review**: Get AI feedback while screen-sharing with team
7. **Customer Support**: Representatives can get script suggestions while customers watch
8. **Medical Training**: Trainers can reference AI assistance during live training
9. **Competitive Programming**: Competitors can get algorithm hints (in appropriate contexts)
10. **Accessibility**: Users with learning disabilities can get real-time help with tests/exams

### Switching Providers

Update `config.ini`:

```ini
[API]
provider = openai
model = gpt-5.4
```

Then add your API key to `.env`:

```
OPENAI_API_KEY=sk-your-key-here
```

### System Prompts for Different Modes

Edit `prompts/system_prompt.md` and swap in one of the provided variants (Developer Mode, Learning Mode, Productivity Mode). Restart the app.

## Troubleshooting

### The app doesn't start
- Check that Python 3.10+ is installed: `python --version`
- Ensure you've activated the virtual environment: `.venv\Scripts\activate`
- Verify dependencies are installed: `pip install -r requirements.txt`

### Hotkeys don't work
- Try running as Administrator
- Check that `config.ini` hotkey bindings are correct
- Make sure another app hasn't captured those hotkeys

### API calls fail
- Check that your `.env` file is in the project root (same folder as `ai_overlay.py`)
- Verify your API key is valid and has credits/quota remaining
- Check internet connection

### Overlay doesn't capture properly
- Close any existing capture tools (OBS, etc.)
- Make sure the overlay window is fully visible
- Wait a moment for the screenshot to process

## Rebuilding from Prompts

This project can be rebuilt from scratch using the prompt files in the `prompts/` folder. If you have a capable AI agent, you can run it with these prompts to generate the entire application again.

## License

This project is provided as-is for educational purposes.
