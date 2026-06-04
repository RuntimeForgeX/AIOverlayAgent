# Personal Context System

## Overview
The Personal Context System is an isolated module that allows users to persistently store personal documents (resume, CV, portfolio links, etc.) and have them automatically injected into AI system prompts.

## Architecture
- **Location**: `modules/personal_context/`
- **Isolation**: Operates independently. It is hooked into the main application via `app.py`, which simply calls its UI and injects its output into the LLM prompt.
- **Storage**: All data is stored in `%APPDATA%\PersonalAiAgentSurya\personal_context\`.
  - `files/` — The extracted or copied source files.
  - `index.json` — Metadata about each file (id, name, type, size, text content).
  - `settings.json` — Module settings (enabled toggle, token limit).

## Data Flow
1. User opens the UI and uploads a file (`.pdf`, `.docx`, `.txt`) or pastes text.
2. `parser.py` extracts text from the file using `PyPDF2` or `python-docx`.
3. `storage.py` saves the file, updates `index.json`, and handles CRUD operations.
4. When the user sends a message in the main app, if context is enabled, `context_builder.py` is called.
5. `context_builder.py` sorts items by priority (resume > readme > other) and chunks the text to fit within the `token_limit` (~4 chars/token).
6. The formatted context is temporarily appended to the system prompt before sending to the LLM API.

## Settings
- **Enabled**: Toggles whether the context is injected into API requests.
- **Token Limit**: The maximum number of tokens (estimated) the context block can consume.

## Removal Steps
To completely remove this feature from the codebase:
1. Delete the `modules/personal_context/` directory.
2. In `main.py`, remove the `PersonalContextManager` import and instantiation block.
3. In `src/ui/app.py`, remove the "Context" button from `_quick_buttons`.
4. In `src/ui/app.py`, remove the `open_personal_context` method.
5. In `src/ui/app.py`, remove the context injection block inside the `send_message` method.
