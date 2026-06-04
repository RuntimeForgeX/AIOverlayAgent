# Project Rules & Conventions

## 1. Coding Standards
- Write clean, PEP8-compliant Python code.
- Use type hinting where it clarifies complex returns (e.g., `def build_model_map() -> dict[str, tuple[str, str]]:`).
- Favor standard library solutions over third-party dependencies unless strictly necessary.

## 2. UI and Component Patterns (CRITICAL)
- **Never use standard Tkinter popups.** Standard `tk.Menu`, `tk.messagebox`, or native dialogues spawn new OS-level windows that do NOT inherit the main window's capture exclusion properties.
- **Use `InvisibleTopLevel`**: Any new window or dropdown must subclass or use `InvisibleTopLevel` to ensure it is hidden from screen captures and the taskbar.
- Ensure `apply_capture_exclusion` or `apply_invisibility_to_tkinter_window` is called on any new UI surface.

## 3. Folder Organization
- `src/ui/`: All Tkinter views, custom widgets, and markdown rendering.
- `src/services/`: External API integrations, local storage operations, and screen capture logic.
- `src/utils/`: Low-level OS hooks (Win32 ctypes).
- `src/config/`: Configuration parsing and model definitions.
- `src/licensing/`: Offline JWT license verification logic.
- `src/prompts/`: Persona configurations.

## 4. Error Handling
- **No Native Error Dialogs**: Do not allow unhandled exceptions to crash the app with a Windows popup.
- Use `src.utils.error_handler.install_in_app_error_handlers` to intercept exceptions and print them directly into the Tkinter chat window. This ensures the stream/recording remains clean.

## 5. API Design Patterns
- **Abstract LLMs**: Do not hardcode specific API calls in the UI. Always route requests through the `APIProvider` subclasses in `src.services.llm_provider`.
- **Multimodal Standard**: Treat all queries as potentially containing images. Ensure the LLM payload accounts for text, a single image, or an array of images.

## 6. Testing & Documentation
- Document any new Win32 API interactions thoroughly, as `ctypes` code is prone to hard crashes.
- Update `MEMORY.md` and `TASKS.md` in the `.ai/` folder whenever completing significant tasks or making architectural decisions.
