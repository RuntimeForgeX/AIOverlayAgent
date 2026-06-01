"""
Global cursor policy: one default arrow cursor for the entire application.
"""

from __future__ import annotations

import tkinter as tk

# Windows / Tk default arrow (avoid hand2, crosshair, xterm, etc.)
APP_CURSOR = "arrow"

_CURSOR_OPTION_PATTERNS = (
    "*Cursor",
    "*Button.Cursor",
    "*Label.Cursor",
    "*Entry.Cursor",
    "*Text.Cursor",
    "*Canvas.Cursor",
    "*Checkbutton.Cursor",
    "*Radiobutton.Cursor",
    "*Menubutton.Cursor",
    "*Scale.Cursor",
    "*Listbox.Cursor",
    "*Frame.Cursor",
    "*Toplevel.Cursor",
    "*Menu.Cursor",
)


def apply_global_cursor_defaults(root: tk.Misc, cursor: str = APP_CURSOR) -> None:
    """Set Tk option database defaults before widgets are created."""
    for pattern in _CURSOR_OPTION_PATTERNS:
        root.option_add(pattern, cursor, "interactive")


def _widget_supports_cursor(widget: tk.Misc) -> bool:
    try:
        return "cursor" in widget.keys()
    except tk.TclError:
        return False


def enforce_widget_cursor(widget: tk.Misc, cursor: str = APP_CURSOR) -> None:
    """Force cursor on one widget."""
    if not _widget_supports_cursor(widget):
        return
    try:
        widget.configure(cursor=cursor)
    except tk.TclError:
        pass


def refresh_cursor_policy(root: tk.Misc, cursor: str = APP_CURSOR) -> None:
    """
    Apply cursor to an existing widget tree and lock it on <Enter>
    so hover states cannot switch to pointer/hand cursors.
    """

    def _visit(widget: tk.Misc) -> None:
        enforce_widget_cursor(widget, cursor)

        def _lock(_event=None, w=widget):
            enforce_widget_cursor(w, cursor)

        try:
            widget.bind("<Enter>", _lock, add="+")
        except tk.TclError:
            pass

        for child in widget.winfo_children():
            _visit(child)

    enforce_widget_cursor(root, cursor)
    _visit(root)
