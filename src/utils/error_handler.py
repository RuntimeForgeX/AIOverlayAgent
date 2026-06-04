
import sys
import traceback
import tkinter as tk
from datetime import datetime

def _format_exception_message(exc_type, exc_value, exc_traceback):
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    return "".join(lines)

def install_in_app_error_handlers(app):
    def tk_exception_handler(*args):
        # Tk 8.6 / Python 3.14+ may pass (exc, val, tb) or (self, exc, val, tb).
        if len(args) < 3:
            return
        exc_type, exc_value, exc_traceback = args[-3:]
        msg = _format_exception_message(exc_type, exc_value, exc_traceback)
        app.add_system_message(f"**UI Error:**\n```text\n{msg}\n```")
        print(f"Tkinter Error: {msg}", file=sys.stderr)

    def sys_exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        msg = _format_exception_message(exc_type, exc_value, exc_traceback)
        app.add_system_message(f"**System Error:**\n```text\n{msg}\n```")
        print(f"System Error: {msg}", file=sys.stderr)

    tk.Tk.report_callback_exception = tk_exception_handler
    sys.excepthook = sys_exception_handler
