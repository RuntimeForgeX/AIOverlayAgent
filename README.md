# AI Overlay Agent

AI Overlay Agent is a Windows desktop assistant that floats above your screen, captures visual context on demand, and sends questions plus optional screenshots to your chosen AI provider.

The project is fully open source. There is no license activation, subscription gate, trial limit, device binding, or online activation server.

## Features

- Always-on-top tkinter overlay with dark, light, and system themes.
- Global hotkeys for showing the overlay, capturing the screen, sending prompts, exporting chats, and navigating responses.
- Screenshot queue with JPEG compression before sending to multimodal models.
- Configurable providers: OpenRouter, OpenAI, Anthropic, and Gemini.
- Model picker in the app header.
- Markdown rendering for AI responses.
- Local chat history, screenshot queue, and preferences under the user's AppData directory.
- Windows display-capture exclusion support for common screen-sharing workflows.
- In-app error reporting without blocking startup dialogs.

## Requirements

- Windows 10 build 19041 or newer, or Windows 11.
- Python 3.10 or newer for development.
- An API key for at least one provider:
  - `OPENROUTER_API_KEY`
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `GEMINI_API_KEY`

## Installation

```bat
git clone https://github.com/your-org/ai-overlay-agent.git
cd ai-overlay-agent
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy the environment template and add your provider key:

```bat
copy .env.example .env
```

Windows environment variables take priority over `.env`.

## Development Setup

Run the app from the repository root:

```bat
python main.py
```

The app starts directly. No activation step is required.

Useful files:

- `config.ini`: provider, model, UI, capture, and hotkey defaults.
- `app_config.ini`: app name, executable name, publisher, and version.
- `USER_GUIDE.md`: end-user setup, configuration, and shortcut guide.
- `USER_GUIDE.html`: single-file browser documentation with copy buttons.
- `src/`: application code.
- `prompts/` and `src/prompts/`: prompt documentation and runtime prompt profiles.

## Build Instructions

Install build-only tools:

```bat
pip install -r requirements_build.txt
```

Build the standalone executable:

```bat
build\build_exe.bat
```

Build the Windows installer after the executable is created:

```bat
build\build_installer.bat
```

The installer build requires Inno Setup 6.

## Usage Guide

For a complete end-user guide, See [USER_GUIDE.html](USER_GUIDE.html).

1. Start the app with `python main.py` or the packaged executable.
2. Select a model from the header dropdown.
3. Type a question and send it.
4. Use screen capture when the model needs visual context.
5. Export the conversation to Markdown when needed.

Default hotkeys are configured in `config.ini`:

| Hotkey | Action |
| --- | --- |
| `Ctrl+Shift+Space` | Show or hide overlay |
| `Ctrl+Shift+S` | Capture screen |
| `Ctrl+Shift+Enter` | Send prompt |
| `Ctrl+Shift+E` | Export chat |
| `Ctrl+Shift+Alt+T` | Toggle click-through |

## Privacy

Screenshots and prompts are sent to the AI provider you configure. Avoid capturing sensitive information unless you are comfortable sending it to that provider. See [PRIVACY.md](PRIVACY.md) for more detail.

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request, and follow the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## FAQ

### Does this project require activation?

No. All licensing and activation code has been removed.

### Which provider should I use?

OpenRouter is convenient if you want one key for multiple model vendors. Direct OpenAI, Anthropic, and Gemini integrations are also available.

### Where is user data stored?

By default, user data is stored in `%APPDATA%\AIOverlayAgent\`.

### Can I build an installer?

Yes. Use the build commands above and install Inno Setup 6 before running `build\build_installer.bat`.

### Does capture exclusion work everywhere?

No capture-exclusion approach is universal. Test with your target recording or screen-sharing tool before relying on it.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
