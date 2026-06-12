"""
Global cursor policy for the AI Overlay HUD.

Since the overlay operates in click-through mode (WS_EX_TRANSPARENT),
the OS cursor never interacts with overlay widgets. These functions
are retained as no-ops to avoid breaking existing call sites.
"""

from __future__ import annotations

import tkinter as tk

# The overlay is click-through; cursor setting is cosmetic only.
APP_CURSOR = "arrow"


def apply_global_cursor_defaults(root: tk.Misc, cursor: str = APP_CURSOR) -> None:
    """Set Tk option database defaults (cosmetic only in click-through mode)."""
    root.option_add("*Cursor", cursor, "interactive")


def enforce_widget_cursor(widget: tk.Misc, cursor: str = APP_CURSOR) -> None:
    """Force cursor on one widget (no-op in click-through mode)."""
    pass


def refresh_cursor_policy(root: tk.Misc, cursor: str = APP_CURSOR) -> None:
    """No-op — click-through windows don't display a custom cursor."""
    pass
