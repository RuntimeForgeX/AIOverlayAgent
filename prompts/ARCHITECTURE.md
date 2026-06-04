# System Architecture

## System Overview
The AI Overlay Agent is a modular Python desktop application. It uses Tkinter for the GUI, interfacing directly with Windows `User32.dll` via `ctypes` to manipulate window properties. It uses LangChain and direct vendor SDKs to communicate with LLMs.

## Folder Structure Explanation
- `/src`: Core application code.
  - `/src/ui`: Tkinter components, main app loop (`app.py`), custom cursor logic, markdown rendering, and themes.
  - `/src/services`: Business logic (LLM providers, screen capture, local storage).
  - `/src/utils`: Helper functions, notably `win32_invisibility.py` for Win32 API calls.
  - `/src/config`: Settings management and model routing.
  - `/src/licensing`: JWT-based offline device-bound license verification.
  - `/src/prompts`: Prompt registries and customized agent personas.
- `/build` & `/installer`: Scripts for PyInstaller and Inno Setup to create distributables.
- `/license-server`: A separate Node.js backend for generating and validating license keys.

## API Architecture
The application uses an abstract `APIProvider` base class (in `src/services/llm_provider.py`) to handle LLM communication.
- **LangChain Backend**: Used for OpenRouter, OpenAI, and Anthropic. It normalizes inputs (text, images) into standard `HumanMessage` arrays.
- **Native Backend**: Google Generative AI (`google-generativeai`) is used directly for Gemini models due to specific multimodal requirements.

## Authentication Architecture
- **API Keys**: Stored in `.env` or Windows Environment Variables (`OPENROUTER_API_KEY`, etc.). Read directly by the application on startup.
- **Application Licensing**: Uses RSA-256 JWTs.
  1. The user activates the app by sending a raw token and their hardware fingerprint to the `/license-server`.
  2. The server responds with a signed JWT containing the `device_hash` and `exp`.
  3. The desktop app stores this JWT in `%APPDATA%` and verifies it offline using a bundled public key (`src/licensing/public_key.py`), preventing tampering and checking for clock rollbacks.

## State Management Architecture
- UI State is held within the `OverlayApp` class (Tkinter variables).
- Persistent state (chat history, theme preferences, prompt selections, queued screenshots) is saved to disk in `%APPDATA%` as JSON files via `src/services/storage.py`.
- Saves happen aggressively (e.g., after every message or queue change) to prevent data loss.

## Deployment Architecture
- **Build**: `build_exe.bat` runs PyInstaller to package the Python environment into a standalone `.exe`.
- **Package**: `build_installer.bat` uses Inno Setup to create a Windows installer (`_Setup.exe`).
- **Distribution**: Users install the `.exe` locally.

## External Integrations
- OpenRouter API (Primary LLM Gateway)
- OpenAI API
- Anthropic API
- Google Gemini API

## Design Patterns Used
- **Factory Pattern**: `get_provider()` dynamically returns the correct LLM provider class based on config.
- **Facade Pattern**: `src/utils/win32_invisibility.py` acts as a facade hiding complex `ctypes` and Win32 API calls (like `SetWindowDisplayAffinity`).
- **Observer Pattern**: Hotkeys are registered globally and trigger bound functions in `OverlayApp` asynchronously.
