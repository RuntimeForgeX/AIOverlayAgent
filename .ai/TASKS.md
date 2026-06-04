# Task Management

## Completed
- [x] Build core transparent Tkinter UI.
- [x] Implement Win32 `WDA_EXCLUDEFROMCAPTURE` API integration for invisibility.
- [x] Add global hotkeys via the `keyboard` module.
- [x] Implement screenshot capture and base64/JPEG compression queue.
- [x] Integrate LangChain for OpenRouter, OpenAI, and Anthropic.
- [x] Integrate `google-generativeai` for native Gemini vision support.
- [x] Build offline device-bound JWT licensing verification.
- [x] Create PyInstaller and Inno Setup build scripts.
- [x] Add local persistence for chat history, settings, and screenshot queues.
- [x] **[2026-06-03]** Generate `.ai` project knowledge system documentation.
- [x] Implement Personal Context System (PDF/DOCX/TXT parsing, storage, context injection).
- [x] Implement Meeting Assistant (WASAPI loopback audio, Whisper transcription, AI suggestions).

## In Progress
- None active.

## Backlog / Technical Debt
- [ ] **Opacity Slider**: The UI has an `[opacity]` label placeholder, but no functional slider. Implement dynamic window opacity adjustment.
- [ ] **Thread Safety**: Some UI updates might occur off the main thread or cause blocking behavior during large API responses. Review Tkinter thread safety.
- [ ] **Installer Code Signing**: The current build process does not include automated code signing, which may cause Windows SmartScreen warnings for users.
- [ ] **Fallback Invisibility**: Fix the warnings triggered by `apply_invisibility_alternative` if the primary title-based hwnd lookup fails.
- [ ] **Test Coverage**: No explicit unit test suite (`pytest`) discovered in the repository. Add core tests for LLM routing and licensing logic.
