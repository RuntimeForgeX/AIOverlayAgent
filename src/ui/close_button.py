"""Shared header close (X) control — display-only in keyboard HUD mode.

In click-through HUD mode, the close button is purely visual.
The overlay is hidden via Ctrl+Shift+Space, not by clicking.
"""

from __future__ import annotations

import tkinter as tk

from src.ui.styles.themes import COLORS

_CLOSE_FONT = ("Segoe UI", 13, "bold")
_CLOSE_FONT_LARGE = ("Segoe UI", 15, "bold")
_CLOSE_WIDTH = 34
_CLOSE_HEIGHT = 28
_CLOSE_WIDTH_LARGE = 44
_CLOSE_HEIGHT_LARGE = 34


def create_header_close_button(parent, command, colors=None, *, bar_bg=None, large=False):
    """
    Build a close control (display-only — no mouse interaction in HUD mode).
    Pack the returned frame side=RIGHT *after*
    other widgets in the same row so it stays on the far right.
    """
    c = colors or COLORS
    bg = bar_bg if bar_bg is not None else c["bg_header"]
    width = _CLOSE_WIDTH_LARGE if large else _CLOSE_WIDTH
    height = _CLOSE_HEIGHT_LARGE if large else _CLOSE_HEIGHT
    font = _CLOSE_FONT_LARGE if large else _CLOSE_FONT

    frame = tk.Frame(
        parent,
        bg=bg,
        width=width,
        height=height,
        highlightbackground=c["border"],
        highlightthickness=1,
    )
    frame.pack_propagate(False)

    label = tk.Label(
        frame,
        text="X",
        fg=c["text_normal"],
        bg=bg,
        font=font,
        cursor="arrow",
    )
    label.place(relx=0.5, rely=0.5, anchor="center")

    frame._close_label = label  # noqa: SLF001 — theme refresh
    frame._close_colors = c
    frame._close_bar_bg = bg

    # No mouse bindings — all interaction is via keyboard shortcuts

    return frame


def refresh_header_close_button(close_frame: tk.Frame) -> None:
    """Re-apply theme colors after a theme change."""
    label = getattr(close_frame, "_close_label", None)
    if label is None:
        return
    c = COLORS
    bg = getattr(close_frame, "_close_bar_bg", c["bg_header"])
    close_frame._close_colors = c
    close_frame._close_bar_bg = bg
    close_frame.config(bg=bg, highlightbackground=c["border"])
    label.config(fg=c["text_normal"], bg=bg)
