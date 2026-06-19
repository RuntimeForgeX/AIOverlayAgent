"""Theme adaptation — analyze screenshot with AI and preview result."""

from __future__ import annotations

import json
import re
import tkinter as tk
from tkinter import font as tkfont

from src.ui.styles.themes import COLORS, THEMES, apply_custom_theme, set_active_theme
from src.utils.win32_invisibility import (
    InvisibleTopLevel,
    apply_overlay_window_config,
    present_overlay_window,
)
from src.ui.close_button import create_header_close_button

# ------------------------------------------------------------------
# Prompt sent to the AI
# ------------------------------------------------------------------
THEME_ANALYSIS_PROMPT = (
    "Analyze the UI colors of the application visible in this screenshot. "
    "Return ONLY a valid JSON object with no markdown formatting, no code blocks, "
    "and no extra commentary. Match these exact keys and use hex color values (#RRGGBB):\n\n"
    "bg_main, bg_header, bg_input, bg_chat, accent_green, accent_blue, "
    "text_normal, text_dim, error_red, code_bg, code_fg, border, "
    "heading_fg, bold_fg, italic_fg, blockquote_bg, blockquote_fg, link_fg, "
    "table_header_bg, table_border_fg, thumb_bg, thumb_border, remove_btn_fg, "
    "code_keyword, code_string, code_comment, code_number.\n\n"
    "Choose colors that harmonize with the dominant colors in the screenshot."
)


# ------------------------------------------------------------------
# Parse / validate
# ------------------------------------------------------------------
def parse_ai_theme_response(response_text: str) -> tuple[dict | None, str]:
    """Extract JSON from AI response and return (theme_dict, error_msg)."""
    text = response_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {exc}"

    if not isinstance(data, dict):
        return None, "AI response is not a JSON object"

    success, err = apply_custom_theme(data)
    if not success:
        return None, err

    # Success — but apply_custom_theme already mutated COLORS globally.
    # Return the parsed dict so caller can decide whether to keep it.
    return dict(data), ""


# ------------------------------------------------------------------
# Preview dialog
# ------------------------------------------------------------------
class AdaptThemePreview(InvisibleTopLevel):
    """Preview adapted theme colors with Apply / Cancel buttons."""

    _SAMPLE_TEXT = (
        "Preview\n"
        "Normal text · dim text · error\n"
        "code_keyword code_string code_comment\n"
    )

    def __init__(self, parent, adapted_colors: dict, on_apply, on_cancel):
        super().__init__(parent)
        self.adapted_colors = adapted_colors
        self.on_apply = on_apply
        self.on_cancel = on_cancel
        self.result = False

        self.title("Theme Preview")
        self.geometry("360x420")
        self.configure(bg=adapted_colors.get("bg_main", "#0a0a0f"))
        apply_overlay_window_config(self, opacity=0.96)

        self._build_ui()
        self.show()

    def _build_ui(self):
        c = self.adapted_colors
        bg = c.get("bg_main", "#0a0a0f")

        # Header
        header = tk.Frame(self, bg=c.get("bg_header", "#0f0f1a"), height=36)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Theme Preview",
            fg=c.get("accent_green", "#00ff88"),
            bg=c.get("bg_header", "#0f0f1a"),
            font=("Courier New", 10, "bold"),
        ).pack(side=tk.LEFT, padx=10, pady=6)

        create_header_close_button(header, self._do_cancel).pack(side=tk.RIGHT, padx=(4, 8), pady=4)

        # Color swatches
        swatch_frame = tk.Frame(self, bg=bg)
        swatch_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        keys = [
            ("bg_main", "Main BG"),
            ("bg_header", "Header"),
            ("accent_green", "Accent"),
            ("text_normal", "Text"),
            ("border", "Border"),
            ("error_red", "Error"),
        ]
        for key, label in keys:
            color = c.get(key, "#000000")
            row = tk.Frame(swatch_frame, bg=bg)
            row.pack(fill=tk.X, pady=2)

            box = tk.Label(
                row,
                text="   ",
                bg=color,
                font=("Courier New", 10),
                relief=tk.RIDGE,
                bd=1,
            )
            box.pack(side=tk.LEFT)

            tk.Label(
                row,
                text=f" {label}  {color}",
                fg=c.get("text_normal", "#d4d4d8"),
                bg=bg,
                font=("Courier New", 9),
                anchor="w",
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Text preview
        preview_frame = tk.Frame(self, bg=c.get("bg_chat", bg))
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        preview = tk.Text(
            preview_frame,
            bg=c.get("bg_chat", bg),
            fg=c.get("text_normal", "#d4d4d8"),
            font=("Courier New", 9),
            relief=tk.FLAT,
            highlightthickness=0,
            wrap=tk.WORD,
            height=6,
        )
        preview.pack(fill=tk.BOTH, expand=True)
        preview.insert(tk.END, self._SAMPLE_TEXT)
        preview.config(state=tk.DISABLED)

        preview.tag_config("preview_dim", foreground=c.get("text_dim", "#52525b"))
        preview.tag_config("preview_error", foreground=c.get("error_red", "#f87171"))
        preview.tag_config("preview_accent", foreground=c.get("accent_blue", "#7dd3fc"))

        # Buttons
        btn_frame = tk.Frame(self, bg=bg)
        btn_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        tk.Button(
            btn_frame,
            text="Apply",
            bg=c.get("accent_green", "#00ff88"),
            fg=c.get("bg_main", "#0a0a0f"),
            font=("Courier New", 9, "bold"),
            relief=tk.FLAT,
            command=self._do_apply,
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            btn_frame,
            text="Cancel",
            bg=c.get("bg_header", "#0f0f1a"),
            fg=c.get("text_normal", "#d4d4d8"),
            font=("Courier New", 9),
            relief=tk.FLAT,
            command=self._do_cancel,
        ).pack(side=tk.LEFT, padx=2)

    def _do_apply(self):
        self.result = True
        if self.on_apply:
            self.on_apply()
        self.destroy()

    def _do_cancel(self):
        self.result = False
        if self.on_cancel:
            self.on_cancel()
        self.destroy()