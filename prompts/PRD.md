# Product Requirements Document (PRD)

## Product Purpose
The AI Overlay Agent is a discreet, always-available AI assistant for Windows. It provides contextual help based on the user's screen while ensuring the assistant itself remains entirely hidden from screen shares, recordings, and streams (e.g., OBS, Zoom, Meet, Teams).

## Core Features
1. **Screen Invisibility**: The application UI must not appear in full-screen captures.
2. **Context-Aware Assistance**: The user can take screenshots of their current screen and send them to multimodal LLMs (GPT-4o, Claude Opus, Gemini Pro) for analysis.
3. **Always-On-Top UI**: The interface must float above all other applications, be transparent, and be quickly toggleable via hotkeys.
4. **Global Hotkeys**: The user can interact with the app (capture screen, toggle visibility) regardless of which window currently has focus.
5. **Customizable Personas**: The user can switch between different system prompts (e.g., Default, C++ DSA, Python DSA) quickly.

## User Workflows
- **Onboarding**: The user installs the app, enters their OpenRouter/OpenAI API key in the environment or `.env` file, and launches the app.
- **Quick Question**: The user presses `Ctrl+Shift+Space` to summon the overlay, types a query, and presses Enter.
- **Visual Question**: The user encounters a bug or a complex diagram, presses `Ctrl+Shift+S` to capture the screen (adding it to the queue), types a question, and hits Enter.
- **Model Switching**: The user clicks the header dropdown to switch from a fast model (e.g., Gemini) to a more capable one (e.g., Claude Opus) on the fly.
- **Theme Switching**: The user clicks the theme icon to toggle between dark, light, and system themes.

## User Roles
- **User**: Can use all application features, capture screens, and chat with AI.

## Functional Requirements
- **Capture**: Must compress screenshots to base64 JPEG format before sending to APIs to minimize payload size.
- **Queueing**: Must allow queueing up to 10 screenshots before sending.
- **Persistence**: Must save chat history and the screenshot queue across application restarts.
- **Markdown**: Must render markdown (bold, code blocks, lists) in the chat UI.
- **Extensibility**: Must allow new prompt templates to be added easily via `src/prompts/`.

## Non-Functional Requirements
- **Performance**: The overlay must be lightweight and not consume significant CPU/RAM while idle.
- **Compatibility**: Windows 10 (2004+) or Windows 11 only.
- **Security**: Must keep API keys local. Must not trigger native Windows dialogs that would bypass the invisibility API.

## Future Opportunities
- **Automated Context**: Automatically scraping text from the active window using OCR or accessibility APIs instead of relying purely on screenshots.
- **Cloud Sync**: Optional sync for chat history across devices.
- **Plugin System**: Allowing local tools (like terminal execution or file reading) to be invoked by the AI.
