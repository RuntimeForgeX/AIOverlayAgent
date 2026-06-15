# Technology Stack

## Core Application
- **Programming Language**: Python 3.10+
- **GUI Framework**: Tkinter (built-in Python GUI library)

## Key Libraries & Dependencies
- **LLM Integration**: 
  - `langchain`, `langchain-openai`, `langchain-anthropic`
  - `google-generativeai` (for native Gemini multimodal support)
  - `openai`, `anthropic` (underlying SDKs)
- **Image Processing**: `pillow` (for `ImageGrab` and base64 JPEG compression)
- **Global Hotkeys**: `keyboard`
- **Environment Management**: `python-dotenv`

## Build & Deployment Tools
- **Executable Packaging**: PyInstaller (via `build\build_exe.bat`)
- **Windows Installer**: Inno Setup 6 (via `build\build_installer.bat`)

## Infrastructure Dependencies
- **Operating System**: Windows 10 (Build 2004 or newer) or Windows 11 required for `WDA_EXCLUDEFROMCAPTURE` API to function.

## External Services
- **LLM Providers**: OpenRouter, OpenAI, Anthropic, Google Gemini
