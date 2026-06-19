"""Theme adaptation — analyze screenshot with AI and preview result."""

from __future__ import annotations

import json
import re
import tkinter as tk
from tkinter import font as tkfont

from src.ui.styles.themes import COLORS, apply_custom_theme, set_active_theme
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
    "Analyze the screenshot. Extract colors directly from the UI shown in the "
    "screenshot and build a 26-color palette for an overlay window. Every color "
    "must be sampled from the dominant colors visible in the screenshot itself.\n\n"

    "# REQUIRED OUTPUT FORMAT\n"
    "Return ONLY a raw JSON object. No markdown. No code blocks. No extra text.\n\n"

    "# REQUIRED KEYS (26 total)\n"
    "- bg_main\n"
    "- bg_header\n"
    "- bg_input\n"
    "- bg_chat\n"
    "- accent_green\n"
    "- accent_blue\n"
    "- text_normal\n"
    "- text_dim\n"
    "- error_red\n"
    "- code_bg\n"
    "- code_fg\n"
    "- border\n"
    "- heading_fg\n"
    "- bold_fg\n"
    "- italic_fg\n"
    "- blockquote_bg\n"
    "- blockquote_fg\n"
    "- link_fg\n"
    "- table_header_bg\n"
    "- table_border_fg\n"
    "- thumb_bg\n"
    "- thumb_border\n"
    "- remove_btn_fg\n"
    "- code_keyword\n"
    "- code_string\n"
    "- code_comment\n"
    "- code_number\n\n"

    "# INSTRUCTIONS\n"
    "1. Examine the screenshot pixel by pixel.\n"
    "2. Sample background colors from actual background pixels: bg_main, bg_header, "
    "bg_input, bg_chat, code_bg, blockquote_bg, table_header_bg, thumb_bg.\n"
    "3. Sample text colors from actual text pixels: text_normal, text_dim, heading_fg, "
    "bold_fg, italic_fg, code_fg, blockquote_fg, link_fg, remove_btn_fg. "
    "These must be real text colors visible in the screenshot, not guessed or defaulted.\n"
    "4. Sample accent and highlight colors from buttons, links, or highlighted elements: "
    "accent_green, accent_blue, error_red, border, thumb_border, code_keyword, "
    "code_string, code_comment, code_number, table_border_fg.\n"
    "5. Do not invent or default any color. Every hex value must trace back to a visible "
    "pixel in the screenshot.\n"
    "6. All values must be 6-digit hex (#rrggbb format).\n"
    "7. Ensure text is readable against its background (sufficient contrast).\n"
    "8. Return ONLY the JSON object — nothing before or after it."
)


# ------------------------------------------------------------------
# Parse / validate
# ------------------------------------------------------------------
def _strip_markdown(text: str) -> str:
    """Remove markdown code fences and surrounding whitespace."""
    text = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```", "", text)
    return text.strip()


def _extract_json_dict(text: str) -> dict | None:
    """Find the first well-formed JSON object inside arbitrary text."""
    text = _strip_markdown(text)
    start = text.find("{")
    if start == -1:
        return None

    # Use brace-balance to locate the matching closing brace
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

    # Fallback: try the outermost braces
    end = text.rfind("}")
    if end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


def parse_ai_theme_response(response_text: str) -> tuple[dict | None, str]:
    """Extract JSON from AI response and return (theme_dict, error_msg)."""
    data = _extract_json_dict(response_text)
    if data is None:
        return None, "Could not find a valid JSON object in the response"

    if not isinstance(data, dict):
        return None, "AI response is not a JSON object"

    # Strict validation — all keys must come from the AI response.
    # No built-in fallback colors are ever mixed in.
    success, err = apply_custom_theme(data)
    if success:
        return dict(data), ""

    return None, err


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