# ============================================================================
# THEME SYSTEM
# ============================================================================

# Attempt to import Windows registry module for system theme detection.
try:
    import winreg
    _winreg_available = True
except Exception:
    _winreg_available = False

THEMES = {
    "dark": {
        "bg_main": "#0a0a0f",
        "bg_header": "#0f0f1a",
        "bg_input": "#13131f",
        "bg_chat": "#0a0a0f",
        "accent_green": "#00ff88",
        "accent_blue": "#7dd3fc",
        "text_normal": "#d4d4d8",
        "text_dim": "#52525b",
        "error_red": "#f87171",
        "code_bg": "#111118",
        "code_fg": "#fbbf24",
        "border": "#1e1e2e",
        "heading_fg": "#e0e7ff",
        "bold_fg": "#f0f0f5",
        "italic_fg": "#c4b5fd",
        "blockquote_bg": "#12121e",
        "blockquote_fg": "#a1a1aa",
        "link_fg": "#60a5fa",
        "table_header_bg": "#161625",
        "table_border_fg": "#2e2e42",
        "thumb_bg": "#161625",
        "thumb_border": "#2a2a3c",
        "remove_btn_fg": "#f87171",
        "code_keyword": "#c678dd",
        "code_string": "#98c379",
        "code_comment": "#5c6370",
        "code_number": "#d19a66",
    },
    "light": {
        "bg_main": "#f8f9fa",
        "bg_header": "#e9ecef",
        "bg_input": "#ffffff",
        "bg_chat": "#f8f9fa",
        "accent_green": "#16a34a",
        "accent_blue": "#2563eb",
        "text_normal": "#1f2937",
        "text_dim": "#6b7280",
        "error_red": "#dc2626",
        "code_bg": "#f1f5f9",
        "code_fg": "#7c3aed",
        "border": "#d1d5db",
        "heading_fg": "#111827",
        "bold_fg": "#111827",
        "italic_fg": "#4338ca",
        "blockquote_bg": "#f3f4f6",
        "blockquote_fg": "#4b5563",
        "link_fg": "#2563eb",
        "table_header_bg": "#e5e7eb",
        "table_border_fg": "#9ca3af",
        "thumb_bg": "#e5e7eb",
        "thumb_border": "#d1d5db",
        "remove_btn_fg": "#dc2626",
        "code_keyword": "#7c3aed",
        "code_string": "#16a34a",
        "code_comment": "#9ca3af",
        "code_number": "#d97706",
    },
}

# Global mutable reference to current theme colors
COLORS = dict(THEMES["light"])
_current_theme_name = "light"


def set_active_theme(name):
    """Update the global COLORS dict to the chosen theme."""
    global COLORS, _current_theme_name
    resolved = name
    if name == "system":
        resolved = detect_system_theme()
    if resolved not in THEMES:
        resolved = "dark"
    _current_theme_name = name  # preserve "system" label
    COLORS.clear()
    COLORS.update(THEMES[resolved])


def detect_system_theme():
    """Read Windows personalization registry to detect light/dark preference."""
    if not _winreg_available:
        return "dark"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if value == 1 else "dark"
    except Exception:
        return "dark"


