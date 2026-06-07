
import os
import re
import sys
import traceback
import tkinter as tk

# Patterns that may leak sensitive API keys in error traces.
_SENSITIVE_KEY_PATTERNS = [
    re.compile(r'(sk-[a-zA-Z0-9]{20,})'),
    re.compile(r'(sk-proj-[a-zA-Z0-9_-]{20,})'),
    re.compile(r'(sk-ant-[a-zA-Z0-9_-]{20,})'),
]

def _redact_sensitive(text: str) -> str:
    """Replace API key-like strings with [REDACTED]."""
    for pat in _SENSITIVE_KEY_PATTERNS:
        text = pat.sub(lambda m: m.group(1)[:4] + "[REDACTED]", text)
    # Also catch explicit env values for common key names.
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY",
                "GEMINI_API_KEY"):
        val = os.environ.get(key)
        if val and len(val) > 8:
            text = text.replace(val, val[:4] + "[REDACTED]")
    return text


def _format_exception_message(exc_type, exc_value, exc_traceback):
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    raw = "".join(lines)
    return _redact_sensitive(raw)


def install_in_app_error_handlers(app):
    def tk_exception_handler(*args):
        # Tk 8.6 / Python 3.14+ may pass (exc, val, tb) or (self, exc, val, tb).
        if len(args) < 3:
            return
        exc_type, exc_value, exc_traceback = args[-3:]
        msg = _format_exception_message(exc_type, exc_value, exc_traceback)
        app.add_system_message(f"**UI Error:**\n```text\n{msg}\n```")
        # Avoid stderr output in production; it may end up in logs / consoles.

    def sys_exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        msg = _format_exception_message(exc_type, exc_value, exc_traceback)
        app.add_system_message(f"**System Error:**\n```text\n{msg}\n```")

    tk.Tk.report_callback_exception = tk_exception_handler
    sys.excepthook = sys_exception_handler
