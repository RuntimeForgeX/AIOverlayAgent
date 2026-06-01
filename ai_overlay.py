#!/usr/bin/env python3
"""
AI Screen Overlay Agent - A Windows desktop overlay for AI-assisted coding and learning.
Invisible to screen recording software like OBS and Chrome.
"""

import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import os
import sys
import base64
import io
import json
import ctypes
import configparser
import keyboard
from datetime import datetime
from pathlib import Path
from PIL import ImageGrab, Image, ImageTk
from dotenv import load_dotenv
import re

# Windows registry for system theme detection
try:
    import winreg
    _winreg_available = True
except ImportError:
    _winreg_available = False

# LangChain imports
try:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
except ImportError as e:
    print(f"Warning: LangChain not fully installed: {e}")
    ChatOpenAI = ChatAnthropic = None
    HumanMessage = AIMessage = SystemMessage = None

# Gemini via native library (fallback)
try:
    import google.generativeai as genai
    genai_available = True
except ImportError:
    genai_available = False


# ============================================================================
# THEME SYSTEM
# ============================================================================

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
COLORS = dict(THEMES["dark"])
_current_theme_name = "dark"


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


# ============================================================================
# CONFIGURATION
# ============================================================================

def is_frozen_app():
    """True when running from a packaged executable (PyInstaller, etc.)."""
    return bool(getattr(sys, "frozen", False))


def get_resource_root():
    """Base folder for bundled, read-only resources."""
    if is_frozen_app() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # PyInstaller onefile temp extract
    return Path(__file__).parent


def load_app_config():
    """Load app metadata from app_config.ini (bundled or alongside exe)."""
    defaults = {
        "name": "PersonalAiAgentSurya",
        "appdata_folder": "PersonalAiAgentSurya",
        "window_title": "AI OVERLAY",
    }

    cp = configparser.ConfigParser()

    candidates = [
        get_resource_root() / "app_config.ini",
    ]
    if is_frozen_app():
        try:
            candidates.append(Path(sys.executable).parent / "app_config.ini")
        except Exception:
            pass
    candidates.append(Path(__file__).parent / "app_config.ini")

    for path in candidates:
        try:
            if path.exists():
                cp.read(path, encoding="utf-8")
                break
        except Exception:
            continue

    return {
        "name": cp.get("APP", "name", fallback=defaults["name"]).strip(),
        "appdata_folder": cp.get(
            "APP", "appdata_folder", fallback=defaults["appdata_folder"]
        ).strip(),
        "window_title": cp.get(
            "APP", "window_title", fallback=defaults["window_title"]
        ).strip(),
    }


APP_META = load_app_config()
APP_NAME = APP_META.get("name") or "PersonalAiAgentSurya"
APPDATA_FOLDER = APP_META.get("appdata_folder") or APP_NAME
WINDOW_TITLE = APP_META.get("window_title") or "AI OVERLAY"


def get_user_data_root(app_name=None):
    """Per-user writable data folder (AppData\\Roaming)."""
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / (app_name or APPDATA_FOLDER)


def get_candidate_dotenv_files(app_name=None):
    """Optional .env locations (used only when a key is not already in the environment)."""
    candidates = []
    try:
        candidates.append(get_user_data_root(app_name) / ".env")
    except Exception:
        pass
    try:
        if is_frozen_app():
            candidates.append(Path(sys.executable).parent / ".env")
    except Exception:
        pass
    candidates.append(Path(__file__).parent / ".env")
    return candidates


def load_environment():
    """
    Load API keys and secrets into os.environ.

    Windows user/system environment variables are already in os.environ and always win.
    .env files only fill in keys that are not already set (override=False).
    """
    for dotenv_file in get_candidate_dotenv_files():
        try:
            if dotenv_file.is_file():
                load_dotenv(dotenv_path=dotenv_file, override=False, encoding="utf-8")
        except Exception:
            pass


def get_api_key(name):
    """Read an API key from the process environment (system env or .env)."""
    value = os.environ.get(name)
    if value is None:
        value = os.getenv(name)
    if not value:
        return None
    value = value.strip()
    return value or None


def api_key_env_name(provider_name):
    """Environment variable name for the configured provider."""
    mapping = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    return mapping.get((provider_name or "").lower(), "ANTHROPIC_API_KEY")

def load_config():
    """Load configuration from config.ini with fallbacks."""
    config = configparser.ConfigParser()

    # Prefer per-user config so installs work under Program Files.
    user_config = get_user_data_root() / "config.ini"
    exe_side_config = None
    if is_frozen_app():
        try:
            exe_side_config = Path(sys.executable).parent / "config.ini"
        except Exception:
            exe_side_config = None
    bundled_config = get_resource_root() / "config.ini"

    if user_config.exists():
        config.read(user_config)
    elif exe_side_config and exe_side_config.exists():
        config.read(exe_side_config)
    elif bundled_config.exists():
        config.read(bundled_config)
    
    return config


def get_config_value(config, section, key, default):
    """Safely get a config value with default fallback."""
    try:
        if section == "HOTKEYS":
            return config.get(section, key, fallback=default)
        elif section in ["API", "API_OPENAI", "API_GEMINI", "UI", "CAPTURE"]:
            return config.get(section, key, fallback=default)
    except:
        pass
    return default


# ============================================================================
# PERSISTENCE HELPERS
# ============================================================================

def save_theme_preference(theme_name):
    """Save theme preference to AppData."""
    prefs_file = get_user_data_root() / "preferences.json"
    prefs_file.parent.mkdir(parents=True, exist_ok=True)
    prefs = {}
    try:
        if prefs_file.exists():
            prefs = json.loads(prefs_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    prefs["theme"] = theme_name
    try:
        prefs_file.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_theme_preference():
    """Load theme preference from AppData."""
    prefs_file = get_user_data_root() / "preferences.json"
    try:
        if prefs_file.exists():
            prefs = json.loads(prefs_file.read_text(encoding="utf-8"))
            return prefs.get("theme", "dark")
    except Exception:
        pass
    return "dark"


def save_display_log(display_log):
    """Save chat display log to AppData."""
    history_file = get_user_data_root() / "chat_history.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Keep at most 200 messages
        trimmed = display_log[-200:]
        history_file.write_text(json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_display_log():
    """Load chat display log from AppData."""
    history_file = get_user_data_root() / "chat_history.json"
    try:
        if history_file.exists():
            return json.loads(history_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def save_screenshot_queue_to_disk(queue):
    """Save up to 5 queued screenshots to AppData."""
    queue_file = get_user_data_root() / "screenshot_queue.json"
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = [{"b64": entry["b64"]} for entry in queue[:5]]
        queue_file.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def load_screenshot_queue_from_disk():
    """Load queued screenshots from AppData."""
    queue_file = get_user_data_root() / "screenshot_queue.json"
    try:
        if queue_file.exists():
            data = json.loads(queue_file.read_text(encoding="utf-8"))
            return [entry["b64"] for entry in data if "b64" in entry]
    except Exception:
        pass
    return []


# ============================================================================
# SYSTEM PROMPT LOADING
# ============================================================================

def load_system_prompt():
    """Load system prompt from prompts/system_prompt.md or return default."""
    default_prompt = """You are an AI assistant embedded as a transparent overlay on the user's Windows desktop.
You are called "Overlay AI".

## What you can do
- See screenshots of the user's screen when they share one using Ctrl+Shift+S
- Remember the full conversation history within this session
- Help with any task that is visible on screen: code, errors, documents, UI, forms, images
- Answer general knowledge questions even without a screenshot

## How to respond
- Be CONCISE. The user reads your responses in a small floating panel.
- Lead with the answer immediately. Do not preamble or repeat the question back.
- If a screenshot is provided: be specific. Reference exact text, line numbers, button labels, filenames you can see.
- If you see code with an error: give the diagnosis and the fix in one response.
- If you see a terminal: read the exact output and tell the user what to do next.
- If you see a UI: describe what the user should click or type to achieve their goal.
- If you see a document or article: summarize the key points or answer questions about it.
- Use markdown code blocks with language tags for any code you write.
- If no screenshot is attached and the question needs one, say: "Press Ctrl+Shift+S to share your screen."

## Tone
- Direct and practical, like a senior developer sitting next to the user
- No filler phrases: never start with "Great question!", "Certainly!", "Of course!", "Sure!"
- Short by default. Expand only if the user asks for more detail.
- Never apologize for being concise.

## Language
- Always respond in the same language the user writes in
- Default to English if unclear"""
    
    prompt_path = get_resource_root() / "prompts" / "system_prompt.md"
    
    if not prompt_path.exists():
        return default_prompt
    
    try:
        content = prompt_path.read_text(encoding="utf-8")
        # Extract content between first ``` and closing ```
        match = re.search(r'```\n(.*?)\n```', content, re.DOTALL)
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"Warning: Could not load system prompt: {e}")
    
    return default_prompt


# ============================================================================
# SCREENSHOT CAPTURE AND COMPRESSION
# ============================================================================

def capture_and_compress_screenshot(max_width=1280, jpeg_quality=82):
    """Capture screen, compress to JPEG, encode as base64."""
    try:
        # Capture screenshot
        screenshot = ImageGrab.grab()
        
        # Resize if needed
        if screenshot.width > max_width:
            ratio = max_width / screenshot.width
            new_height = int(screenshot.height * ratio)
            screenshot = screenshot.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to JPEG and compress
        jpeg_buffer = io.BytesIO()
        screenshot.convert("RGB").save(jpeg_buffer, format="JPEG", quality=jpeg_quality)
        jpeg_buffer.seek(0)
        
        # Encode to base64
        base64_image = base64.b64encode(jpeg_buffer.read()).decode("utf-8")
        return base64_image
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None


# ============================================================================
# WIN32 API FOR INVISIBILITY
# ============================================================================

WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011
GA_ROOT = 2
GA_ROOTOWNER = 3
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020

_user32 = ctypes.windll.user32
_user32.SetWindowDisplayAffinity.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
_user32.SetWindowDisplayAffinity.restype = ctypes.c_bool
_user32.GetWindowDisplayAffinity.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
_user32.GetWindowDisplayAffinity.restype = ctypes.c_bool


def _apply_capture_exclusion_to_hwnd(hwnd):
    """Exclude one HWND from screen capture via DWM (Meet, OBS, Zoom, Teams)."""
    if not hwnd or hwnd <= 0:
        return False
    if _user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE):
        return True
    return bool(_user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR))


def _get_window_display_affinity(hwnd):
    affinity = ctypes.c_ulong()
    if _user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(affinity)):
        return affinity.value
    return WDA_NONE


def collect_tk_window_hwnds(window, title=None):
    """Collect every HWND tied to a tkinter window (outer frame + inner client)."""
    hwnds = set()

    if title is None and hasattr(window, "title"):
        try:
            title = window.title()
        except Exception:
            pass

    if window is not None:
        try:
            window.update_idletasks()
            inner = window.winfo_id()
            if inner and inner > 0:
                hwnds.add(inner)
                root_hwnd = _user32.GetAncestor(inner, GA_ROOT)
                if root_hwnd:
                    hwnds.add(root_hwnd)
                root_owner = _user32.GetAncestor(inner, GA_ROOTOWNER)
                if root_owner:
                    hwnds.add(root_owner)
                parent = _user32.GetParent(inner)
                while parent:
                    hwnds.add(parent)
                    parent = _user32.GetParent(parent)
        except Exception:
            pass

    if title:
        outer = _user32.FindWindowW(None, title)
        if outer:
            hwnds.add(outer)

    return hwnds


def collect_process_hwnds():
    """All top-level HWNDs owned by this process."""
    current_pid = os.getpid()
    hwnds = set()

    def enum_proc(hwnd, _lparam):
        pid = ctypes.c_ulong()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == current_pid:
            hwnds.add(hwnd)
        return True

    enum_windows = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    _user32.EnumWindows(enum_windows(enum_proc), 0)
    return hwnds


def apply_capture_exclusion(window=None, title=None, verbose=True):
    """Apply WDA_EXCLUDEFROMCAPTURE to every related HWND.

    Uses DWM display affinity only — do NOT combine with WS_EX_NOREDIRECTIONBITMAP,
    which opts out of DWM and prevents capture exclusion from working.
    """
    hwnds = set()
    if window is not None:
        hwnds.update(collect_tk_window_hwnds(window, title))
    if title:
        outer = _user32.FindWindowW(None, title)
        if outer:
            hwnds.add(outer)
    hwnds.update(collect_process_hwnds())

    protected = 0
    verified = 0
    for hwnd in hwnds:
        if _apply_capture_exclusion_to_hwnd(hwnd):
            protected += 1
            if _get_window_display_affinity(hwnd) == WDA_EXCLUDEFROMCAPTURE:
                verified += 1

    if verbose:
        if protected:
            print(f"  ✓ Capture exclusion applied to {protected} window(s), {verified} verified")
            if verified < protected:
                print("  ! Some windows may show as black in capture (upgrade Windows 10 to 2004+ for full exclusion)")
        else:
            err = ctypes.get_last_error()
            print(f"  ! Capture exclusion failed (error {err})")

    return protected > 0


def _get_window_exstyle(hwnd):
    style = _user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    if style == 0:
        style = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    return style


def _set_window_exstyle(hwnd, style):
    if not _user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style):
        _user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    _user32.SetWindowPos(
        hwnd, 0, 0, 0, 0, 0,
        SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
    )


def hide_window_from_taskbar(window):
    """Hide a window from the Windows taskbar and Alt+Tab switcher."""
    try:
        window.attributes("-toolwindow", True)
    except tk.TclError:
        pass

    try:
        window.update_idletasks()
        title = window.title() if hasattr(window, "title") else None
        for hwnd in collect_tk_window_hwnds(window, title):
            style = _get_window_exstyle(hwnd)
            _set_window_exstyle(hwnd, (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW)
    except Exception as e:
        print(f"Warning: Could not hide window from taskbar: {e}")


def make_window_invisible_to_capture(hwnd):
    """Apply capture exclusion to a single HWND."""
    return _apply_capture_exclusion_to_hwnd(hwnd)


def get_window_handle(window_title):
    """Get HWND for a tkinter window by title."""
    try:
        hwnd = _user32.FindWindowW(None, window_title)
        if hwnd and hwnd > 0:
            return hwnd
        print(f"Warning: Could not find window with title '{window_title}'")
        return None
    except Exception as e:
        print(f"Warning: Error getting window handle: {e}")
        return None


def get_tkinter_hwnd(window):
    """Get the primary Win32 HWND for a tkinter widget or window."""
    hwnds = collect_tk_window_hwnds(window)
    if not hwnds:
        return None
    outer = None
    try:
        title = window.title() if hasattr(window, "title") else None
        if title:
            outer = _user32.FindWindowW(None, title)
    except Exception:
        pass
    return outer or max(hwnds)


def apply_invisibility_to_tkinter_window(window):
    """Apply capture exclusion and hide from taskbar for a tkinter window."""
    try:
        window.update_idletasks()
        window.update()
        hide_window_from_taskbar(window)
        title = window.title() if hasattr(window, "title") else None
        return apply_capture_exclusion(window, title, verbose=False)
    except Exception as e:
        print(f"Warning: Error applying invisibility to window: {e}")
        return False


class InvisibleTopLevel(tk.Toplevel):
    """Toplevel window hidden until invisibility is applied — no visible flash."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._invisibility_applied = False
        self.withdraw()
        self.bind("<Map>", self._on_map, add="+")

    def show(self):
        """Reveal the window, then apply capture invisibility."""
        self.deiconify()
        self.attributes("-topmost", True)
        self.update_idletasks()
        self.update()
        self._apply_invisibility()

    def _on_map(self, event=None):
        """Re-apply privacy flags whenever the window is shown."""
        apply_invisibility_to_tkinter_window(self)
        self._invisibility_applied = True

    def _apply_invisibility(self):
        apply_invisibility_to_tkinter_window(self)
        self._invisibility_applied = True


class InvisibleModelDropdown(tk.Frame):
    """Model selector using a capture-excluded Toplevel popup (not native OptionMenu)."""

    def __init__(self, master, variable, values, command=None, **btn_kwargs):
        super().__init__(master, bg=btn_kwargs.get("bg", COLORS["bg_header"]))
        self.variable = variable
        self.values = list(values)
        self.command = command
        self._popup = None
        self._outside_bind = None

        self.button = tk.Button(
            self,
            textvariable=variable,
            command=self._toggle_popup,
            **btn_kwargs,
        )
        self.button.pack()

    def _toggle_popup(self):
        if self._popup and self._popup.winfo_exists():
            try:
                if self._popup.winfo_viewable():
                    self._close_popup()
                    return
            except tk.TclError:
                self._popup = None
        self._open_popup()

    def _close_popup(self):
        if self._outside_bind:
            try:
                self.winfo_toplevel().unbind("<Button-1>", self._outside_bind)
            except Exception:
                pass
            self._outside_bind = None
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None

    def _open_popup(self):
        self._close_popup()
        root = self.winfo_toplevel()

        self._popup = InvisibleTopLevel(root)
        self._popup.overrideredirect(True)
        self._popup.configure(bg=COLORS["bg_input"])

        frame = tk.Frame(
            self._popup,
            bg=COLORS["bg_input"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        frame.pack(fill=tk.BOTH, expand=True)

        for value in self.values:
            row = tk.Label(
                frame,
                text=value,
                bg=COLORS["bg_input"],
                fg=COLORS["text_normal"],
                font=("Courier New", 8),
                anchor="w",
                padx=10,
                pady=4,
                cursor="hand2",
            )
            row.pack(fill=tk.X)

            def on_select(selected=value):
                self.variable.set(selected)
                if self.command:
                    self.command(selected)
                self._close_popup()

            row.bind("<Button-1>", lambda _e, fn=on_select: fn())
            row.bind(
                "<Enter>",
                lambda _e, r=row: r.config(bg=COLORS["accent_green"], fg=COLORS["bg_main"]),
            )
            row.bind(
                "<Leave>",
                lambda _e, r=row: r.config(bg=COLORS["bg_input"], fg=COLORS["text_normal"]),
            )

        self.update_idletasks()
        bx = self.button.winfo_rootx()
        by = self.button.winfo_rooty() + self.button.winfo_height()
        width = max(self.button.winfo_width(), 150)
        height = len(self.values) * 26 + 4
        self._popup.geometry(f"{width}x{height}+{bx}+{by}")
        self._popup.show()

        def dismiss_if_outside(event):
            if not self._popup or not self._popup.winfo_exists():
                return
            px, py = self._popup.winfo_rootx(), self._popup.winfo_rooty()
            pw, ph = self._popup.winfo_width(), self._popup.winfo_height()
            bx2, by2 = self.button.winfo_rootx(), self.button.winfo_rooty()
            bw, bh = self.button.winfo_width(), self.button.winfo_height()
            x, y = event.x_root, event.y_root
            in_popup = px <= x <= px + pw and py <= y <= py + ph
            in_button = bx2 <= x <= bx2 + bw and by2 <= y <= by2 + bh
            if not in_popup and not in_button:
                self._close_popup()

        self._outside_bind = self.winfo_toplevel().bind("<Button-1>", dismiss_if_outside, add="+")


# ============================================================================
# API PROVIDERS (USING LANGCHAIN)
# ============================================================================

class APIProvider:
    """Base class for AI API providers using LangChain."""
    
    def __init__(self, config):
        self.config = config
        self.conversation_history = []
        self.system_prompt = load_system_prompt()
        self.llm = None
        self._api_key_env = api_key_env_name(
            get_config_value(config, "API", "provider", "anthropic")
        )
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the LangChain LLM. Implemented by subclasses."""
        raise NotImplementedError

    def is_ready(self):
        return self.llm is not None

    def _ensure_llm(self):
        """Try to initialize the client (e.g. after keys were added to the environment)."""
        if self.llm is not None:
            return True
        load_environment()
        self._initialize_llm()
        return self.llm is not None

    def _missing_key_message(self):
        return (
            f"{self._api_key_env} is not set. "
            f"Add it in Windows Environment Variables or a .env file, then try again."
        )
    
    def send_message(self, message_content, on_response, on_error):
        """Send message to AI. Implemented by subclasses."""
        raise NotImplementedError
    
    def add_text_message(self, text):
        """Add a text message to history."""
        self.conversation_history.append(HumanMessage(content=text))
    
    def add_image_message(self, base64_image, text):
        """Add a screenshot message to history."""
        self.conversation_history.append(
            HumanMessage(
                content=[
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ]
            )
        )

    def add_multi_image_message(self, images_b64, text):
        """Add a multi-image message to history."""
        content = [{"type": "text", "text": text}]
        for b64 in images_b64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        self.conversation_history.append(HumanMessage(content=content))
    
    def add_assistant_message(self, text):
        """Add AI response to history."""
        self.conversation_history.append(AIMessage(content=text))
    
    def trim_history(self):
        """Keep first 2 messages and last 28 messages if history exceeds 30."""
        if len(self.conversation_history) > 30:
            self.conversation_history = (
                self.conversation_history[:2] +
                self.conversation_history[-28:]
            )
    
    def clear_history(self):
        """Clear all conversation history."""
        self.conversation_history = []

    def _add_user_content(self, message_content):
        """Add user content to history based on format."""
        if isinstance(message_content, str):
            self.add_text_message(message_content)
        elif isinstance(message_content, dict):
            if "images" in message_content:
                self.add_multi_image_message(
                    message_content["images"], message_content["text"]
                )
            else:
                self.add_image_message(
                    message_content["image"], message_content["text"]
                )


class AnthropicProvider(APIProvider):
    """Anthropic Claude API provider using LangChain."""
    
    def _initialize_llm(self):
        """Initialize Claude via LangChain."""
        api_key = get_api_key("ANTHROPIC_API_KEY")
        if not api_key:
            self.llm = None
            return

        model_name = get_config_value(self.config, "API", "model", "claude-opus-4-5")
        self.max_tokens = int(get_config_value(self.config, "API", "max_tokens", "1500"))
        
        self.llm = ChatAnthropic(
            model=model_name,
            max_tokens=self.max_tokens,
            temperature=0.7
        )
    
    def send_message(self, message_content, on_response, on_error):
        """Send message to Claude via LangChain."""
        try:
            if not self._ensure_llm():
                on_error(self._missing_key_message())
                return

            self._add_user_content(message_content)
            self.trim_history()
            
            messages = [SystemMessage(content=self.system_prompt)] + self.conversation_history
            response = self.llm.invoke(messages)
            reply = response.content
            self.add_assistant_message(reply)
            
            tokens = {
                "input": response.response_metadata.get("usage", {}).get("input_tokens", 0),
                "output": response.response_metadata.get("usage", {}).get("output_tokens", 0)
            }
            
            on_response(reply, tokens)
            
        except Exception as e:
            if self.conversation_history and isinstance(self.conversation_history[-1], HumanMessage):
                self.conversation_history.pop()
            on_error(str(e))


class OpenAIProvider(APIProvider):
    """OpenAI GPT API provider using LangChain."""
    
    def _initialize_llm(self):
        """Initialize GPT via LangChain."""
        api_key = get_api_key("OPENAI_API_KEY")
        if not api_key:
            self.llm = None
            return

        model_name = get_config_value(self.config, "API_OPENAI", "model", "gpt-4-turbo")
        self.max_tokens = int(get_config_value(self.config, "API", "max_tokens", "1500"))
        
        self.llm = ChatOpenAI(
            model=model_name,
            max_tokens=self.max_tokens,
            temperature=0.7
        )
    
    def send_message(self, message_content, on_response, on_error):
        """Send message to OpenAI via LangChain."""
        try:
            if not self._ensure_llm():
                on_error(self._missing_key_message())
                return

            self._add_user_content(message_content)
            self.trim_history()
            
            messages = [SystemMessage(content=self.system_prompt)] + self.conversation_history
            response = self.llm.invoke(messages)
            reply = response.content
            self.add_assistant_message(reply)
            
            tokens = {
                "input": response.response_metadata.get("usage", {}).get("prompt_tokens", 0),
                "output": response.response_metadata.get("usage", {}).get("completion_tokens", 0)
            }
            
            on_response(reply, tokens)
            
        except Exception as e:
            if self.conversation_history and isinstance(self.conversation_history[-1], HumanMessage):
                self.conversation_history.pop()
            on_error(str(e))


class GeminiProvider(APIProvider):
    """Google Gemini API provider (native API)."""
    
    def _initialize_llm(self):
        """Initialize Gemini using native google.generativeai library."""
        if not genai_available:
            self.llm = None
            return

        api_key = get_api_key("GEMINI_API_KEY")
        if not api_key:
            self.llm = None
            return

        genai.configure(api_key=api_key)
        model_name = get_config_value(self.config, "API_GEMINI", "model", "gemini-2.5-pro")
        self.max_tokens = int(get_config_value(self.config, "API", "max_tokens", "1500"))
        self.llm = genai.GenerativeModel(model_name, system_instruction=self.system_prompt)
    
    def send_message(self, message_content, on_response, on_error):
        """Send message to Gemini via native API."""
        try:
            if not self._ensure_llm():
                if not genai_available:
                    on_error("google-generativeai is not installed in this build.")
                else:
                    on_error(self._missing_key_message())
                return

            gen_config = genai.types.GenerationConfig(max_output_tokens=self.max_tokens)

            if isinstance(message_content, str):
                self.add_text_message(message_content)
                response = self.llm.generate_content(
                    message_content, generation_config=gen_config
                )
            elif isinstance(message_content, dict) and "images" in message_content:
                images_b64 = message_content["images"]
                text = message_content["text"]
                self.add_multi_image_message(images_b64, text)
                pil_images = []
                for b64 in images_b64:
                    pil_images.append(Image.open(io.BytesIO(base64.b64decode(b64))))
                response = self.llm.generate_content(
                    pil_images + [text], generation_config=gen_config
                )
            else:
                base64_image = message_content["image"]
                text = message_content["text"]
                self.add_image_message(base64_image, text)
                image = Image.open(io.BytesIO(base64.b64decode(base64_image)))
                response = self.llm.generate_content(
                    [image, text], generation_config=gen_config
                )
            
            reply = response.text
            self.add_assistant_message(reply)
            
            tokens = {"input": 0, "output": 0}
            on_response(reply, tokens)
            
        except Exception as e:
            if self.conversation_history and isinstance(self.conversation_history[-1], HumanMessage):
                self.conversation_history.pop()
            on_error(str(e))


def get_provider(config):
    """Factory function to create the appropriate API provider using LangChain."""
    provider_name = get_config_value(config, "API", "provider", "anthropic").lower()
    
    if provider_name == "openai":
        return OpenAIProvider(config)
    elif provider_name == "gemini":
        return GeminiProvider(config)
    else:  # Default to Anthropic
        return AnthropicProvider(config)


# ============================================================================
# MARKDOWN RENDERER
# ============================================================================

# Keywords for syntax highlighting (covers Python, JS, TS, C, C++, Java, SQL, Rust, Go)
_KEYWORDS = {
    "def", "class", "import", "from", "if", "elif", "else", "for", "while",
    "return", "try", "except", "finally", "with", "as", "yield", "lambda",
    "pass", "break", "continue", "and", "or", "not", "in", "is", "None",
    "True", "False", "raise", "async", "await", "del", "global", "nonlocal",
    "function", "const", "let", "var", "new", "this", "typeof", "instanceof",
    "throw", "catch", "switch", "case", "default", "export", "extends",
    "implements", "interface", "enum", "type", "void",
    "int", "float", "double", "char", "bool", "string", "long", "short",
    "unsigned", "signed", "struct", "union", "typedef", "sizeof", "static",
    "extern", "inline", "virtual", "override", "public", "private", "protected",
    "abstract", "final", "package", "include", "define", "ifdef", "endif",
    "namespace", "using", "template", "typename",
    "SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP",
    "ALTER", "TABLE", "INDEX", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER",
    "ON", "NULL", "INTO", "VALUES", "SET", "ORDER", "BY", "GROUP",
    "HAVING", "LIMIT", "OFFSET", "DISTINCT", "COUNT", "SUM", "AVG", "MAX",
    "MIN", "LIKE", "BETWEEN", "EXISTS",
    "fn", "mut", "pub", "mod", "use", "crate", "impl", "trait",
    "match", "loop", "move", "ref", "self", "Self", "super", "where",
    "func", "go", "defer", "chan", "select", "range", "map", "make",
    "null", "undefined", "true", "false", "nil",
    "print", "println", "printf", "require", "module", "exports",
}

_KEYWORD_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(kw) for kw in sorted(_KEYWORDS, key=len, reverse=True)) + r')\b'
)

INLINE_RE = re.compile(r'(`[^`]+`|\*\*[^*]+?\*\*|\*[^*]+?\*)')


def configure_markdown_tags(widget, colors):
    """Configure text widget tags for markdown rendering."""
    c = colors

    # Headings
    widget.tag_config("md_h1", foreground=c["heading_fg"],
                      font=("Courier New", 14, "bold"), spacing1=8, spacing3=4)
    widget.tag_config("md_h2", foreground=c["heading_fg"],
                      font=("Courier New", 12, "bold"), spacing1=6, spacing3=3)
    widget.tag_config("md_h3", foreground=c["heading_fg"],
                      font=("Courier New", 10, "bold"), spacing1=4, spacing3=2)

    # Inline
    widget.tag_config("md_bold", foreground=c["bold_fg"],
                      font=("Courier New", 9, "bold"))
    widget.tag_config("md_italic", foreground=c["italic_fg"],
                      font=("Courier New", 9, "italic"))
    widget.tag_config("md_inline_code", foreground=c["code_fg"],
                      background=c["code_bg"], font=("Courier New", 9))

    # Code block
    widget.tag_config("code_block", background=c["code_bg"], foreground=c["code_fg"],
                      font=("Courier New", 8), lmargin1=16, lmargin2=16, rmargin=8,
                      spacing1=1, spacing3=1)
    widget.tag_config("code_lang", foreground=c["text_dim"],
                      font=("Courier New", 7, "italic"), lmargin1=16)

    # Syntax highlighting (applied on top of code_block)
    widget.tag_config("code_keyword", foreground=c["code_keyword"])
    widget.tag_config("code_string", foreground=c["code_string"])
    widget.tag_config("code_comment", foreground=c["code_comment"])
    widget.tag_config("code_number", foreground=c["code_number"])

    # Ensure syntax tags override code_block foreground
    for tag_name in ("code_keyword", "code_string", "code_comment", "code_number"):
        widget.tag_raise(tag_name, "code_block")

    # Blockquote
    widget.tag_config("md_blockquote", foreground=c["blockquote_fg"],
                      background=c["blockquote_bg"], font=("Courier New", 9, "italic"),
                      lmargin1=20, lmargin2=20)

    # Lists
    widget.tag_config("md_list", foreground=c["text_normal"],
                      font=("Courier New", 9), lmargin1=20, lmargin2=30)

    # Table
    widget.tag_config("md_table", foreground=c["text_normal"],
                      font=("Courier New", 8), background=c["code_bg"],
                      lmargin1=8, lmargin2=8)
    widget.tag_config("md_table_header", foreground=c["heading_fg"],
                      font=("Courier New", 8, "bold"),
                      background=c["table_header_bg"], lmargin1=8, lmargin2=8)

    # Horizontal rule
    widget.tag_config("md_hr", foreground=c["border"],
                      font=("Courier New", 7), spacing1=4, spacing3=4)

    # Link
    widget.tag_config("md_link", foreground=c["link_fg"],
                      font=("Courier New", 9, "underline"))


def render_markdown(widget, text, colors):
    """Parse markdown text and insert into a tkinter Text widget with formatting."""
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Fenced code block
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines):
                if lines[i].strip() == "```" or lines[i].strip().startswith("```") and len(lines[i].strip()) == 3:
                    break
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # skip closing ```
            _render_code_block(widget, "\n".join(code_lines), lang)
            continue

        # Heading
        if stripped.startswith("### "):
            widget.insert(tk.END, stripped[4:] + "\n", "md_h3")
        elif stripped.startswith("## "):
            widget.insert(tk.END, stripped[3:] + "\n", "md_h2")
        elif stripped.startswith("# "):
            widget.insert(tk.END, stripped[2:] + "\n", "md_h1")

        # Horizontal rule
        elif re.match(r'^[-*_]{3,}\s*$', stripped):
            widget.insert(tk.END, "─" * 40 + "\n", "md_hr")

        # Blockquote
        elif stripped.startswith("> "):
            widget.insert(tk.END, "  │ ", "md_blockquote")
            _render_inline_text(widget, stripped[2:], "md_blockquote")
            widget.insert(tk.END, "\n")

        # Unordered list
        elif re.match(r'^[\s]*[-*+]\s', line):
            indent = len(line) - len(line.lstrip())
            text_content = re.sub(r'^[\s]*[-*+]\s', '', line)
            prefix = "  " * (indent // 2) + "  • "
            widget.insert(tk.END, prefix, "md_list")
            _render_inline_text(widget, text_content, "md_list")
            widget.insert(tk.END, "\n")

        # Ordered list
        elif re.match(r'^[\s]*\d+\.\s', line):
            match_obj = re.match(r'^[\s]*(\d+)\.\s(.*)$', line)
            if match_obj:
                indent = len(line) - len(line.lstrip())
                num = match_obj.group(1)
                text_content = match_obj.group(2)
                prefix = "  " * (indent // 2) + f"  {num}. "
                widget.insert(tk.END, prefix, "md_list")
                _render_inline_text(widget, text_content, "md_list")
                widget.insert(tk.END, "\n")

        # Table
        elif "|" in stripped and stripped.startswith("|"):
            table_lines = [line]
            i += 1
            while i < len(lines) and "|" in lines[i].strip() and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            _render_table(widget, table_lines)
            continue

        # Empty line
        elif not stripped:
            widget.insert(tk.END, "\n")

        # Normal paragraph
        else:
            _render_inline_text(widget, line, "ai_text")
            widget.insert(tk.END, "\n")

        i += 1


def _render_inline_text(widget, text, base_tag):
    """Render text with inline markdown (bold, italic, code) into the widget."""
    parts = INLINE_RE.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            widget.insert(tk.END, part[1:-1], "md_inline_code")
        elif part.startswith("**") and part.endswith("**") and len(part) > 3:
            widget.insert(tk.END, part[2:-2], "md_bold")
        elif part.startswith("*") and part.endswith("*") and len(part) > 1 and not part.startswith("**"):
            widget.insert(tk.END, part[1:-1], "md_italic")
        else:
            widget.insert(tk.END, part, base_tag)


def _render_code_block(widget, code_text, lang):
    """Render a fenced code block with syntax highlighting."""
    if lang:
        widget.insert(tk.END, f"  {lang}\n", "code_lang")

    # Record start position for syntax highlighting
    start_idx = widget.index(tk.END)

    for code_line in code_text.split("\n"):
        widget.insert(tk.END, f"  {code_line}\n", "code_block")

    end_idx = widget.index(tk.END)

    # Apply syntax highlighting
    _apply_syntax_highlighting(widget, start_idx, end_idx)

    widget.insert(tk.END, "\n")


def _apply_syntax_highlighting(widget, start, end):
    """Apply basic syntax highlighting to a code range."""
    try:
        text = widget.get(start, end)
        if not text.strip():
            return

        # Keywords
        for match in _KEYWORD_PATTERN.finditer(text):
            s, e = match.span()
            widget.tag_add("code_keyword", f"{start}+{s}c", f"{start}+{e}c")

        # Strings (double and single quoted)
        for match in re.finditer(r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', text):
            s, e = match.span()
            widget.tag_add("code_string", f"{start}+{s}c", f"{start}+{e}c")

        # Comments (# or //)
        for match in re.finditer(r'(#[^\n]*|//[^\n]*)', text):
            s, e = match.span()
            widget.tag_add("code_comment", f"{start}+{s}c", f"{start}+{e}c")

        # Numbers
        for match in re.finditer(r'\b(\d+\.?\d*(?:e[+-]?\d+)?)\b', text, re.IGNORECASE):
            s, e = match.span()
            widget.tag_add("code_number", f"{start}+{s}c", f"{start}+{e}c")
    except Exception:
        pass  # Syntax highlighting is non-critical


def _render_table(widget, table_lines):
    """Render a markdown table as monospace-aligned text."""
    rows = []
    has_separator = False
    for line in table_lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.match(r'^[-:]+$', c.strip()) for c in cells if c.strip()):
            has_separator = True
            continue
        rows.append(cells)

    if not rows:
        return

    max_cols = max(len(r) for r in rows)
    col_widths = [0] * max_cols
    for row in rows:
        for j, cell in enumerate(row):
            if j < max_cols:
                col_widths[j] = max(col_widths[j], len(cell))

    for idx, row in enumerate(rows):
        tag = "md_table_header" if idx == 0 and has_separator else "md_table"
        line_parts = []
        for j in range(max_cols):
            cell = row[j] if j < len(row) else ""
            line_parts.append(cell.ljust(col_widths[j]))
        widget.insert(tk.END, "  │ " + " │ ".join(line_parts) + " │\n", tag)

        if idx == 0 and has_separator:
            sep_parts = ["─" * w for w in col_widths]
            widget.insert(tk.END, "  ├─" + "─┼─".join(sep_parts) + "─┤\n", "md_table")

    widget.insert(tk.END, "\n")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class OverlayApp:
    """Main AI Overlay Application."""
    
    THEME_ICONS = {"dark": "🌙", "light": "☀", "system": "🖥"}
    THEME_CYCLE = ["dark", "light", "system"]
    MAX_QUEUE = 10

    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.is_sending = False
        self.is_visible = True
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.message_count = 0
        self.screenshot_count = 0
        self.started_at = datetime.now()
        self.window_hwnd = None
        self.window_opacity = 0.94
        self.window_invisible = False
        self._hotkeys_registered = False
        self._hotkey_removers = []
        self.display_log = []
        self.screenshot_queue = []  # list of {"b64": str, "photo": PhotoImage}
        self._loading_history = False
        self._quick_buttons = []

        # Section customization
        self.sections_enabled = {
            "mcq": True,
            "cpp": True,
            "sql": True,
            "dsa": True
        }
        
        # Load theme preference and apply
        theme_pref = load_theme_preference()
        set_active_theme(theme_pref)

        # Build UI first; API client initializes lazily when you send a message
        self.setup_window()
        self.provider = get_provider(config)
        if not self.provider.is_ready():
            self.status_label.config(text="ready · set API key in environment")

        # Load persisted chat history
        self._load_display_log()

        # Load persisted screenshot queue
        self._load_screenshot_queue_from_disk()

        # Register hotkeys after the Win32 window exists
        self.root.after(200, self.register_hotkeys)
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Re-apply capture exclusion after the window is fully realized in mainloop
        self.setup_invisibility_maintenance()

        print("AI Overlay Agent started")

    def setup_invisibility_maintenance(self):
        """Keep capture exclusion active (required for Meet/OBS after window is shown)."""
        self.root.after(0, lambda: self.apply_main_window_invisibility(verbose=False))
        self.root.after(100, lambda: self.apply_main_window_invisibility(verbose=False))
        self.root.after(500, lambda: self.apply_main_window_invisibility(verbose=False))
        self.root.after(1500, self._start_invisibility_polling)

        for event in ("<Map>", "<FocusIn>"):
            self.root.bind(
                event,
                lambda e: self.apply_main_window_invisibility(verbose=False),
                add="+",
            )

    def _start_invisibility_polling(self):
        self.apply_main_window_invisibility(verbose=False)
        self.root.after(3000, self._start_invisibility_polling)
    
    def setup_window(self):
        """Setup tkinter window with proper invisibility configuration."""
        width = int(get_config_value(self.config, "UI", "width", "500"))
        height = int(get_config_value(self.config, "UI", "height", "650"))
        start_x = int(get_config_value(self.config, "UI", "start_x", "60"))
        start_y = int(get_config_value(self.config, "UI", "start_y", "60"))
        opacity = float(get_config_value(self.config, "UI", "opacity", "0.94"))
        
        self.root.geometry(f"{width}x{height}+{start_x}+{start_y}")
        self.root.title(WINDOW_TITLE)
        self.root.configure(bg=COLORS["bg_main"])
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", opacity)
        try:
            self.root.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        self.root.resizable(False, False)
        
        self.window_opacity = opacity

        self.setup_drag()
        self.build_ui()
        self.apply_main_window_invisibility()

    def apply_main_window_invisibility(self, verbose=True):
        """Apply capture exclusion to the main overlay and all process windows."""
        if verbose:
            print("\n[INVISIBILITY SETUP]")
        self.root.update_idletasks()
        self.root.update()

        hide_window_from_taskbar(self.root)
        success = apply_capture_exclusion(self.root, WINDOW_TITLE, verbose=verbose)
        self.window_invisible = success

        hwnd = get_tkinter_hwnd(self.root)
        if hwnd:
            self.window_hwnd = hwnd
            if verbose:
                print(f"Primary window handle: {hwnd}")

        if verbose:
            if success:
                print("✓ Invisibility configuration complete\n")
            else:
                print("⚠ Invisibility may be incomplete\n")
                self.apply_invisibility_alternative()

        if verbose:
            if self.window_invisible:
                self.add_system_message("✓ Initialized · INVISIBLE TO RECORDINGS · Ready")
            else:
                self.add_system_message("⚠ Initialized · INVISIBILITY NOT CONFIRMED · Check console")

    def apply_invisibility_alternative(self):
        """Fallback if title-based lookup fails."""
        try:
            hwnd = _user32.FindWindowW("Tk", None)
            if hwnd and hwnd > 0:
                print(f"Found window by class name: {hwnd}")
                self.window_hwnd = hwnd
                if apply_capture_exclusion(verbose=False):
                    self.window_invisible = True
        except Exception:
            pass
    
    def setup_drag(self):
        """Make window draggable by header bar."""
        self.drag_data = {"x": 0, "y": 0}
        
        def start_drag(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
        
        def drag_motion(event):
            delta_x = event.x - self.drag_data["x"]
            delta_y = event.y - self.drag_data["y"]
            x = self.root.winfo_x() + delta_x
            y = self.root.winfo_y() + delta_y
            self.root.geometry(f"+{x}+{y}")
        
        self.root.bind("<Button-1>", start_drag, add="+")
        self.root.bind("<B1-Motion>", drag_motion, add="+")
    
    def build_ui(self):
        """Build the UI layout."""
        # Header frame
        self.header_frame = tk.Frame(self.root, bg=COLORS["bg_header"], height=40)
        self.header_frame.pack(fill=tk.X, padx=0, pady=0)
        self.header_frame.pack_propagate(False)
        
        # Title and dot
        self.title_label = tk.Label(
            self.header_frame, text="● AI OVERLAY",
            fg=COLORS["accent_green"], bg=COLORS["bg_header"],
            font=("Courier New", 10, "bold")
        )
        self.title_label.pack(side=tk.LEFT, padx=10, pady=8)
        
        # Model selector dropdown
        models = [
            "Gemini 3 Pro",
            "Gemini 2.5 Pro",
            "GPT-5.4",
            "GPT-4o",
            "GPT-4o Mini",
            "GPT-4 Turbo",
            "Claude 3.5 Sonnet",
            "Claude 4.5 Opus",
            "Claude 4 Sonnet"
        ]
        self.model_var = tk.StringVar(value="Gemini 3 Pro")
        self.model_dropdown = InvisibleModelDropdown(
            self.header_frame,
            self.model_var,
            models,
            command=self.change_model,
            bg=COLORS["bg_header"],
            fg=COLORS["accent_green"],
            font=("Courier New", 8),
            relief=tk.FLAT,
            activebackground=COLORS["bg_input"],
            activeforeground=COLORS["accent_green"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.model_dropdown.pack(side=tk.RIGHT, padx=5, pady=8)
        
        # Opacity slider (placeholder for now)
        self.opacity_label = tk.Label(
            self.header_frame, text="[opacity]",
            fg=COLORS["text_dim"], bg=COLORS["bg_header"],
            font=("Courier New", 8)
        )
        self.opacity_label.pack(side=tk.RIGHT, padx=5, pady=8)

        # Theme toggle button
        theme_icon = self.THEME_ICONS.get(_current_theme_name, "🌙")
        self.theme_btn = tk.Label(
            self.header_frame, text=theme_icon,
            fg=COLORS["text_dim"], bg=COLORS["bg_header"],
            font=("Courier New", 10), cursor="hand2",
        )
        self.theme_btn.pack(side=tk.RIGHT, padx=5, pady=8)
        self.theme_btn.bind("<Button-1>", lambda e: self._cycle_theme())
        
        # Chat history panel
        self.chat_frame = tk.Frame(self.root, bg=COLORS["bg_chat"])
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        self.chat_display = scrolledtext.ScrolledText(
            self.chat_frame,
            bg=COLORS["bg_chat"],
            fg=COLORS["text_normal"],
            font=("Courier New", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.FLAT,
            highlightthickness=0
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags
        self._configure_chat_tags()

        # Thumbnail strip (hidden by default)
        self.thumb_strip_frame = tk.Frame(self.root, bg=COLORS["bg_input"])
        # Do not pack yet — shown when screenshots are queued

        self.thumb_canvas = tk.Canvas(
            self.thumb_strip_frame, bg=COLORS["bg_input"],
            height=62, highlightthickness=0
        )
        self.thumb_inner_frame = tk.Frame(self.thumb_canvas, bg=COLORS["bg_input"])

        self.thumb_canvas.pack(fill=tk.X, expand=True)
        self.thumb_canvas_window = self.thumb_canvas.create_window(
            (0, 0), window=self.thumb_inner_frame, anchor="nw"
        )

        def _on_thumb_frame_configure(event):
            self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all"))

        self.thumb_inner_frame.bind("<Configure>", _on_thumb_frame_configure)

        # Horizontal mousewheel scrolling on thumbnail strip
        def _on_thumb_mousewheel(event):
            self.thumb_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

        self.thumb_canvas.bind("<MouseWheel>", _on_thumb_mousewheel)
        self.thumb_inner_frame.bind("<MouseWheel>", _on_thumb_mousewheel)

        # Input frame
        self.input_frame = tk.Frame(self.root, bg=COLORS["bg_input"])
        self.input_frame.pack(fill=tk.X, padx=8, pady=8)
        
        self.input_box = tk.Entry(
            self.input_frame,
            bg=COLORS["bg_input"],
            fg=COLORS["text_normal"],
            font=("Courier New", 9),
            relief=tk.FLAT,
            insertbackground=COLORS["accent_green"]
        )
        self.input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.input_box.bind("<Return>", lambda e: self.send_message())
        
        self.send_button = tk.Button(
            self.input_frame,
            text="⏎",
            bg=COLORS["accent_green"],
            fg=COLORS["bg_main"],
            font=("Courier New", 10, "bold"),
            relief=tk.FLAT,
            width=3,
            command=self.send_message
        )
        self.send_button.pack(side=tk.LEFT, padx=2, pady=5)
        
        # Quick buttons frame
        self.buttons_frame = tk.Frame(self.root, bg=COLORS["bg_main"])
        self.buttons_frame.pack(fill=tk.X, padx=8, pady=4)
        
        self._quick_buttons = []
        btn_defs = [
            ("📷 Capture", self.hotkey_capture),
            ("🗑 Clear", self.hotkey_clear),
            ("💾 Export", self.hotkey_export),
            ("⚙️ Settings", self.open_settings),
        ]
        for text, cmd in btn_defs:
            btn = tk.Button(
                self.buttons_frame,
                text=text,
                bg=COLORS["bg_header"],
                fg=COLORS["text_normal"],
                font=("Courier New", 8),
                relief=tk.FLAT,
                command=cmd,
            )
            btn.pack(side=tk.LEFT, padx=2)
            self._quick_buttons.append(btn)
        
        # Status bar
        self.status_frame = tk.Frame(self.root, bg=COLORS["border"], height=1)
        self.status_frame.pack(fill=tk.X)
        
        self.status_label = tk.Label(
            self.root,
            text="ready · 0 in / 0 out tokens",
            bg=COLORS["bg_main"],
            fg=COLORS["text_dim"],
            font=("Courier New", 8)
        )
        self.status_label.pack(fill=tk.X, padx=8, pady=4)

    def _configure_chat_tags(self):
        """Configure all text tags on the chat display."""
        c = COLORS
        self.chat_display.tag_config("you_label", foreground=c["accent_green"],
                                     font=("Courier New", 9, "bold"))
        self.chat_display.tag_config("ai_label", foreground=c["accent_blue"],
                                     font=("Courier New", 9, "bold"))
        self.chat_display.tag_config("ai_text", foreground=c["accent_blue"])
        self.chat_display.tag_config("text_normal", foreground=c["text_normal"])
        self.chat_display.tag_config("timestamp", foreground=c["text_dim"],
                                     font=("Courier New", 8))
        self.chat_display.tag_config("error", foreground=c["error_red"])
        self.chat_display.tag_config("system", foreground=c["text_dim"])
        self.chat_display.tag_config("screenshot_tag", foreground=c["accent_blue"],
                                     font=("Courier New", 9, "italic"))

        configure_markdown_tags(self.chat_display, c)
    
    # ------------------------------------------------------------------
    # Thumbnail / screenshot queue
    # ------------------------------------------------------------------

    def _create_thumbnail_photo(self, b64_image, size=(60, 45)):
        """Create a thumbnail PhotoImage from base64 JPEG."""
        try:
            image_bytes = base64.b64decode(b64_image)
            image = Image.open(io.BytesIO(image_bytes))
            image.thumbnail(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception:
            return None

    def _add_screenshot_to_queue(self, b64_image):
        """Add a screenshot to the queue and update the thumbnail strip."""
        if len(self.screenshot_queue) >= self.MAX_QUEUE:
            self.add_system_message(f"⚠ Queue full (max {self.MAX_QUEUE})")
            return

        photo = self._create_thumbnail_photo(b64_image)
        if photo is None:
            return

        entry = {"b64": b64_image, "photo": photo}
        self.screenshot_queue.append(entry)
        self._rebuild_thumbnail_strip()
        self._save_screenshot_queue()

    def _remove_screenshot(self, idx):
        """Remove a screenshot from the queue."""
        if 0 <= idx < len(self.screenshot_queue):
            self.screenshot_queue.pop(idx)
            self._rebuild_thumbnail_strip()
            self._save_screenshot_queue()
            n = len(self.screenshot_queue)
            self.status_label.config(
                text=f"screenshot removed · {n} pending" if n else "ready"
            )

    def _move_screenshot(self, idx, direction):
        """Move a screenshot left (-1) or right (+1) in the queue."""
        new_idx = idx + direction
        if 0 <= new_idx < len(self.screenshot_queue):
            self.screenshot_queue[idx], self.screenshot_queue[new_idx] = \
                self.screenshot_queue[new_idx], self.screenshot_queue[idx]
            self._rebuild_thumbnail_strip()
            self._save_screenshot_queue()

    def _preview_screenshot(self, idx):
        """Open a full-size preview of a queued screenshot."""
        if idx >= len(self.screenshot_queue):
            return
        b64 = self.screenshot_queue[idx]["b64"]
        try:
            image_bytes = base64.b64decode(b64)
            image = Image.open(io.BytesIO(image_bytes))
            image.thumbnail((800, 600), Image.Resampling.LANCZOS)

            preview = InvisibleTopLevel(self.root)
            preview.title("Screenshot Preview")
            preview.geometry(f"{image.width}x{image.height + 50}")
            preview.configure(bg=COLORS["bg_main"])

            photo = ImageTk.PhotoImage(image)
            lbl = tk.Label(preview, image=photo, bg=COLORS["bg_main"])
            lbl.image = photo
            lbl.pack(padx=5, pady=5)

            tk.Button(
                preview, text="Close", command=preview.destroy,
                bg=COLORS["accent_green"], fg=COLORS["bg_main"],
                font=("Courier New", 9, "bold"), relief=tk.FLAT,
            ).pack(pady=5)

            preview.show()
        except Exception:
            self.add_system_message("⚠ Could not preview screenshot")

    def _show_thumb_context_menu(self, event, idx):
        """Show right-click context menu for a thumbnail."""
        menu = tk.Menu(
            self.root, tearoff=0,
            bg=COLORS["bg_input"], fg=COLORS["text_normal"],
            activebackground=COLORS["accent_green"],
            activeforeground=COLORS["bg_main"],
            font=("Courier New", 8),
        )
        menu.add_command(label="Preview", command=lambda: self._preview_screenshot(idx))
        if idx > 0:
            menu.add_command(label="◀ Move Left", command=lambda: self._move_screenshot(idx, -1))
        if idx < len(self.screenshot_queue) - 1:
            menu.add_command(label="Move Right ▶", command=lambda: self._move_screenshot(idx, 1))
        menu.add_separator()
        menu.add_command(label="✕ Remove", command=lambda: self._remove_screenshot(idx))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _rebuild_thumbnail_strip(self):
        """Rebuild the thumbnail strip from the screenshot queue."""
        for widget in self.thumb_inner_frame.winfo_children():
            widget.destroy()

        for i, entry in enumerate(self.screenshot_queue):
            # Regenerate photo if missing (e.g. after persistence load)
            if entry.get("photo") is None:
                entry["photo"] = self._create_thumbnail_photo(entry["b64"])
            if entry["photo"] is None:
                continue

            container = tk.Frame(
                self.thumb_inner_frame, bg=COLORS["thumb_bg"],
                highlightbackground=COLORS["thumb_border"], highlightthickness=1,
            )
            container.pack(side=tk.LEFT, padx=3, pady=3)

            img_label = tk.Label(container, image=entry["photo"], bg=COLORS["thumb_bg"])
            img_label.image = entry["photo"]
            img_label.pack(side=tk.LEFT, padx=2, pady=2)

            remove_lbl = tk.Label(
                container, text="×", fg=COLORS["remove_btn_fg"],
                bg=COLORS["thumb_bg"], font=("Courier New", 9, "bold"),
                cursor="hand2",
            )
            remove_lbl.pack(side=tk.LEFT, padx=(0, 3))
            remove_lbl.bind("<Button-1>", lambda e, idx=i: self._remove_screenshot(idx))

            # Double-click to preview, right-click for context menu
            img_label.bind("<Double-Button-1>", lambda e, idx=i: self._preview_screenshot(idx))
            img_label.bind("<Button-3>", lambda e, idx=i: self._show_thumb_context_menu(e, idx))
            container.bind("<Button-3>", lambda e, idx=i: self._show_thumb_context_menu(e, idx))

        if self.screenshot_queue:
            # Pack the strip above the input frame
            self.thumb_strip_frame.pack(fill=tk.X, padx=8, pady=(0, 4),
                                        before=self.input_frame)
        else:
            self.thumb_strip_frame.pack_forget()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _save_display_log(self):
        """Save display log to disk."""
        if self._loading_history:
            return
        save_display_log(self.display_log)

    def _load_display_log(self):
        """Load persisted chat display history and replay into the chat."""
        history = load_display_log()
        if not history:
            return
        self._loading_history = True
        for entry in history:
            role = entry.get("role", "system")
            text = entry.get("text", "")
            is_system = entry.get("is_system", False) or role == "system"
            self.add_message_to_display(role, text, is_system=is_system)
        self.display_log = list(history)
        self._loading_history = False

    def _save_screenshot_queue(self):
        """Save queued screenshots to disk."""
        save_screenshot_queue_to_disk(self.screenshot_queue)

    def _load_screenshot_queue_from_disk(self):
        """Load queued screenshots from disk and rebuild the strip."""
        b64_list = load_screenshot_queue_from_disk()
        for b64 in b64_list:
            photo = self._create_thumbnail_photo(b64)
            self.screenshot_queue.append({"b64": b64, "photo": photo})
        if self.screenshot_queue:
            self._rebuild_thumbnail_strip()
            n = len(self.screenshot_queue)
            self.status_label.config(text=f"restored {n} queued screenshot(s)")

    # ------------------------------------------------------------------
    # Theme management
    # ------------------------------------------------------------------

    def _cycle_theme(self):
        """Cycle through dark → light → system themes."""
        try:
            idx = self.THEME_CYCLE.index(_current_theme_name)
        except ValueError:
            idx = 0
        next_theme = self.THEME_CYCLE[(idx + 1) % len(self.THEME_CYCLE)]
        set_active_theme(next_theme)
        save_theme_preference(next_theme)
        self.theme_btn.config(text=self.THEME_ICONS.get(next_theme, "🌙"))
        self._apply_theme()
        self.add_system_message(f"theme → {next_theme}")

    def _apply_theme(self):
        """Apply current COLORS to all widgets."""
        c = COLORS

        # Root
        self.root.configure(bg=c["bg_main"])

        # Header
        self.header_frame.configure(bg=c["bg_header"])
        self.title_label.configure(fg=c["accent_green"], bg=c["bg_header"])
        self.theme_btn.configure(fg=c["text_dim"], bg=c["bg_header"])
        self.opacity_label.configure(fg=c["text_dim"], bg=c["bg_header"])

        # Model dropdown
        self.model_dropdown.configure(bg=c["bg_header"])
        self.model_dropdown.button.configure(
            bg=c["bg_header"], fg=c["accent_green"],
            activebackground=c["bg_input"], activeforeground=c["accent_green"],
        )

        # Chat
        self.chat_frame.configure(bg=c["bg_chat"])
        self.chat_display.configure(bg=c["bg_chat"], fg=c["text_normal"])
        self._configure_chat_tags()  # reconfigure all tags with new colors

        # Thumbnail strip
        self.thumb_strip_frame.configure(bg=c["bg_input"])
        self.thumb_canvas.configure(bg=c["bg_input"])
        self.thumb_inner_frame.configure(bg=c["bg_input"])

        # Input
        self.input_frame.configure(bg=c["bg_input"])
        self.input_box.configure(
            bg=c["bg_input"], fg=c["text_normal"],
            insertbackground=c["accent_green"],
        )
        self.send_button.configure(bg=c["accent_green"], fg=c["bg_main"])

        # Quick buttons
        self.buttons_frame.configure(bg=c["bg_main"])
        for btn in self._quick_buttons:
            btn.configure(bg=c["bg_header"], fg=c["text_normal"])

        # Status
        self.status_frame.configure(bg=c["border"])
        self.status_label.configure(bg=c["bg_main"], fg=c["text_dim"])

        # Rebuild thumbnails with new colors
        self._rebuild_thumbnail_strip()

    # ------------------------------------------------------------------
    # Chat display
    # ------------------------------------------------------------------

    def add_message_to_display(self, role, text, is_system=False):
        """Add a message to the chat display with markdown rendering for AI."""
        self.chat_display.config(state=tk.NORMAL)
        
        timestamp = datetime.now().strftime("%H:%M")
        
        if is_system:
            self.chat_display.insert(tk.END, f"\n{text}\n", "system")
        else:
            if role == "you":
                self.chat_display.insert(tk.END, f"\n{timestamp}  ", "timestamp")
                self.chat_display.insert(tk.END, "▶ you\n", "you_label")
                
                # Handle screenshot indicator
                if "[📷" in text or "[Screenshot]" in text:
                    self.chat_display.insert(tk.END, text + "\n", "screenshot_tag")
                else:
                    self.chat_display.insert(tk.END, text + "\n", "text_normal")
            
            else:  # AI response — full markdown rendering
                self.chat_display.insert(tk.END, f"\n{timestamp}  ", "timestamp")
                self.chat_display.insert(tk.END, "◆ ai\n", "ai_label")
                render_markdown(self.chat_display, text, COLORS)
        
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

        # Persist to display log
        if not self._loading_history:
            self.display_log.append({
                "role": role,
                "text": text,
                "is_system": is_system,
            })
            self._save_display_log()
    
    def add_system_message(self, text):
        """Add a system message."""
        self.add_message_to_display("system", text, is_system=True)

    # ------------------------------------------------------------------
    # Send / receive
    # ------------------------------------------------------------------
    
    def send_message(self):
        """Send a text message (optionally with queued screenshots) to the AI."""
        if not self.provider:
            return
        
        if self.is_sending:
            return
        
        message_text = self.input_box.get().strip()
        has_screenshots = len(self.screenshot_queue) > 0

        if not message_text and not has_screenshots:
            return
        
        self.input_box.delete(0, tk.END)
        self.is_sending = True
        self.send_button.config(state=tk.DISABLED)
        self.message_count += 1

        # Build display text
        if has_screenshots:
            n = len(self.screenshot_queue)
            prefix = f"[📷 ×{n}] " if n > 1 else "[📷] "
            display_text = prefix + (message_text or "Analyze screenshot")
        else:
            display_text = message_text
        
        self.add_message_to_display("you", display_text)
        self.status_label.config(text="thinking...")
        
        # Build API message content
        if has_screenshots:
            images = [entry["b64"] for entry in self.screenshot_queue]
            api_text = message_text or "What is shown in these screenshots? Analyze them and provide relevant help."
            if len(images) == 1:
                message_content = {"image": images[0], "text": api_text}
            else:
                message_content = {"images": images, "text": api_text}
            # Clear queue
            self.screenshot_queue.clear()
            self._rebuild_thumbnail_strip()
            self._save_screenshot_queue()
        else:
            message_content = message_text
        
        # Send in background thread
        def api_call():
            try:
                self.provider.send_message(
                    message_content,
                    self.on_api_response,
                    self.on_api_error
                )
            except Exception as e:
                self.on_api_error(str(e))
        
        thread = threading.Thread(target=api_call, daemon=True)
        thread.start()
    
    def on_api_response(self, response_text, tokens):
        """Handle successful API response."""
        self.total_input_tokens += tokens["input"]
        self.total_output_tokens += tokens["output"]
        
        self.root.after(0, lambda: self._update_ui_after_response(response_text))
    
    def _update_ui_after_response(self, response_text):
        """Update UI after API response (must be called from main thread)."""
        self.add_message_to_display("ai", response_text)
        self.is_sending = False
        self.send_button.config(state=tk.NORMAL)
        self.input_box.focus()
        self.status_label.config(
            text=f"ready · {self.total_input_tokens} in / {self.total_output_tokens} out tokens"
        )
    
    def on_api_error(self, error_text):
        """Handle API error."""
        self.root.after(0, lambda: self._update_ui_after_error(error_text))
    
    def _update_ui_after_error(self, error_text):
        """Update UI after API error (must be called from main thread)."""
        self.add_message_to_display("system", f"⚠ Error: {error_text}", is_system=True)
        self.is_sending = False
        self.send_button.config(state=tk.NORMAL)
        self.input_box.focus()
        self.status_label.config(text="error · check message above")

    # ------------------------------------------------------------------
    # Hotkeys
    # ------------------------------------------------------------------
    
    def hotkey_toggle(self):
        """Toggle window visible/hidden (Ctrl+Shift+Space)."""
        if self.is_visible:
            self.root.withdraw()
            self.is_visible = False
        else:
            self.root.deiconify()
            self.root.attributes("-topmost", True)
            self.is_visible = True

            # Re-apply privacy flags when window becomes visible again
            apply_invisibility_to_tkinter_window(self.root)
    
    def hotkey_capture(self):
        """Capture screen and queue for sending (Ctrl+Shift+S)."""
        if not self.provider:
            return
        
        # Hide window, capture, show window
        self.root.withdraw()
        time.sleep(0.25)
        
        max_w = int(get_config_value(self.config, "CAPTURE", "max_width", "1280"))
        quality = int(get_config_value(self.config, "CAPTURE", "jpeg_quality", "82"))
        base64_image = capture_and_compress_screenshot(max_width=max_w, jpeg_quality=quality)
        
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        
        # Re-apply privacy flags after showing window
        apply_invisibility_to_tkinter_window(self.root)
        
        if not base64_image:
            self.add_system_message("⚠ Screenshot capture failed")
            return
        
        self.screenshot_count += 1
        self._add_screenshot_to_queue(base64_image)
        n = len(self.screenshot_queue)
        self.status_label.config(text=f"screenshot queued · {n} pending")
    
    def hotkey_clear(self):
        """Clear conversation history (Ctrl+Shift+C)."""
        if self.provider:
            self.provider.clear_history()
        
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.message_count = 0
        self.screenshot_count = 0

        # Clear screenshot queue
        self.screenshot_queue.clear()
        self._rebuild_thumbnail_strip()
        self._save_screenshot_queue()

        # Clear display log
        self.display_log.clear()
        self._save_display_log()
        
        self.add_system_message("conversation cleared · memory reset")
        self.status_label.config(text="ready · 0 in / 0 out tokens")
    
    def hotkey_focus(self):
        """Focus input box (Ctrl+Shift+I)."""
        self.input_box.focus()
    
    def hotkey_export(self):
        """Export conversation to Markdown (Ctrl+Shift+E)."""
        if not self.provider or not self.provider.conversation_history:
            self.add_system_message("⚠ No conversation to export")
            return
        
        # Create exports directory in a writable per-user location
        exports_dir = get_user_data_root() / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = exports_dir / f"chat_{timestamp}.md"
        
        # Build markdown content
        content = "# AI Overlay Export\n\n"
        content += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "---\n"
        
        for msg in self.provider.conversation_history:
            content += "\n"
            if isinstance(msg, HumanMessage):
                content += "**You:**\n"
            elif isinstance(msg, AIMessage):
                content += "**AI:**\n"
            else:
                continue

            if isinstance(msg.content, str):
                content += msg.content + "\n"
            elif isinstance(msg.content, list):
                for item in msg.content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            content += item["text"] + "\n"
                        elif item.get("type") == "image_url":
                            content += "[screenshot]\n"
            else:
                content += str(msg.content) + "\n"
        
        # Write file
        filename.write_text(content, encoding="utf-8")

        self.add_system_message(f"✓ Exported to {filename}")
    
    def change_model(self, model_name):
        """Change the AI model on the fly."""
        model_map = {
            "Gemini 3 Pro": ("gemini", "gemini-3-pro"),
            "Gemini 2.5 Pro": ("gemini", "gemini-2.5-pro"),
            "GPT-5.4": ("openai", "gpt-5.4"),
            "GPT-4o": ("openai", "gpt-4o"),
            "GPT-4o Mini": ("openai", "gpt-4o-mini"),
            "GPT-4 Turbo": ("openai", "gpt-4-turbo"),
            "Claude 3.5 Sonnet": ("anthropic", "claude-3-5-sonnet"),
            "Claude 4.5 Opus": ("anthropic", "claude-opus-4-5"),
            "Claude 4 Sonnet": ("anthropic", "claude-sonnet-4")
        }
        
        if model_name not in model_map:
            self.add_system_message(f"⚠ Unknown model: {model_name}")
            return
        
        provider_name, model_id = model_map[model_name]
        
        try:
            load_environment()

            # Update config
            self.config.set("API", "provider", provider_name)
            if provider_name == "anthropic":
                self.config.set("API", "model", model_id)
            elif provider_name == "openai":
                self.config.set("API_OPENAI", "model", model_id)
            elif provider_name == "gemini":
                self.config.set("API_GEMINI", "model", model_id)
            
            # Reinitialize provider
            self.provider = get_provider(self.config)
            
            # Clear conversation for new provider
            self.provider.clear_history()
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
            self.total_input_tokens = 0
            self.total_output_tokens = 0
            self.message_count = 0
            self.screenshot_count = 0

            # Clear screenshot queue
            self.screenshot_queue.clear()
            self._rebuild_thumbnail_strip()
            self._save_screenshot_queue()

            # Clear display log
            self.display_log.clear()
            self._save_display_log()
            
            self.add_system_message(f"✓ switched to {model_name}")
            self.status_label.config(text="ready · 0 in / 0 out tokens")
            
        except Exception as e:
            self.add_system_message(f"⚠ Error switching model: {str(e)}")
            self.model_var.set("Claude 4.5 Opus")  # Reset dropdown
    
    def open_settings(self):
        """Open settings window for customization."""
        settings_window = InvisibleTopLevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x500")
        settings_window.configure(bg=COLORS["bg_main"])
        
        # Title
        title = tk.Label(
            settings_window,
            text="Response Sections",
            fg=COLORS["accent_green"],
            bg=COLORS["bg_main"],
            font=("Courier New", 12, "bold")
        )
        title.pack(pady=10)
        
        # Section toggles
        sections = [
            ("📋 MCQ", "mcq", "Multiple Choice Questions"),
            ("💻 C++", "cpp", "C++ Code & Solutions"),
            ("📊 SQL", "sql", "SQL Queries & Code"),
            ("🧠 DSA", "dsa", "Data Structures & Algorithms")
        ]
        
        var_refs = {}
        for label, key, desc in sections:
            frame = tk.Frame(settings_window, bg=COLORS["bg_input"])
            frame.pack(fill=tk.X, padx=15, pady=8)
            
            var = tk.BooleanVar(value=self.sections_enabled[key])
            var_refs[key] = var
            
            cb = tk.Checkbutton(
                frame,
                text=f"{label} - {desc}",
                variable=var,
                bg=COLORS["bg_input"],
                fg=COLORS["text_normal"],
                selectcolor=COLORS["bg_input"],
                activebackground=COLORS["bg_input"],
                activeforeground=COLORS["accent_green"],
                font=("Courier New", 9)
            )
            cb.pack(anchor=tk.W)
        
        # Edit prompt button
        tk.Button(
            settings_window,
            text="📝 Edit System Prompt",
            bg=COLORS["accent_green"],
            fg=COLORS["bg_main"],
            font=("Courier New", 10, "bold"),
            relief=tk.FLAT,
            command=self.edit_system_prompt
        ).pack(pady=15, padx=15, fill=tk.X)
        
        # Save button
        def save_sections():
            for key, var in var_refs.items():
                self.sections_enabled[key] = var.get()
            self.add_system_message(f"✓ Sections updated")
            settings_window.destroy()
        
        tk.Button(
            settings_window,
            text="Save Settings",
            bg=COLORS["accent_blue"],
            fg=COLORS["bg_main"],
            font=("Courier New", 10, "bold"),
            relief=tk.FLAT,
            command=save_sections
        ).pack(pady=10, padx=15, fill=tk.X)

        settings_window.show()
    
    def edit_system_prompt(self):
        """Edit the system prompt."""
        prompt_window = InvisibleTopLevel(self.root)
        prompt_window.title("Edit System Prompt")
        prompt_window.geometry("600x500")
        prompt_window.configure(bg=COLORS["bg_main"])
        
        # Title
        title = tk.Label(
            prompt_window,
            text="System Prompt Editor",
            fg=COLORS["accent_green"],
            bg=COLORS["bg_main"],
            font=("Courier New", 12, "bold")
        )
        title.pack(pady=10)
        
        # Prompt text editor
        editor = tk.Text(
            prompt_window,
            bg=COLORS["bg_input"],
            fg=COLORS["text_normal"],
            font=("Courier New", 9),
            wrap=tk.WORD,
            relief=tk.FLAT
        )
        editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Load current prompt
        current_prompt = self.provider.system_prompt if self.provider else ""
        editor.insert(1.0, current_prompt)
        
        # Save button
        def save_prompt():
            new_prompt = editor.get(1.0, tk.END).strip()
            if self.provider:
                self.provider.system_prompt = new_prompt
                self.add_system_message("✓ System prompt updated")
            prompt_window.destroy()
        
        tk.Button(
            prompt_window,
            text="Save Prompt",
            bg=COLORS["accent_green"],
            fg=COLORS["bg_main"],
            font=("Courier New", 10, "bold"),
            relief=tk.FLAT,
            command=save_prompt
        ).pack(pady=10, padx=10, fill=tk.X)

        prompt_window.show()
    
    def _schedule_on_main_thread(self, callback):
        """Run a hotkey handler on the Tk main thread (required for UI updates)."""
        try:
            self.root.after(0, callback)
        except tk.TclError:
            pass

    def _on_window_close(self):
        for remover in self._hotkey_removers:
            try:
                remover()
            except Exception:
                pass
        self._hotkey_removers.clear()
        self.root.destroy()

    def _warmup_keyboard_listener(self):
        """Initialize the keyboard hook thread (needed for some PyInstaller builds)."""
        try:
            keyboard.start_recording()
            keyboard.stop_recording()
        except Exception:
            pass

    def register_hotkeys(self):
        """Register global hotkeys via the keyboard library."""
        if self._hotkeys_registered:
            return

        toggle_key = get_config_value(self.config, "HOTKEYS", "toggle", "ctrl+shift+space")
        capture_key = get_config_value(self.config, "HOTKEYS", "capture", "ctrl+shift+s")
        clear_key = get_config_value(self.config, "HOTKEYS", "clear", "ctrl+shift+c")
        focus_key = get_config_value(self.config, "HOTKEYS", "focus", "ctrl+shift+i")
        export_key = get_config_value(self.config, "HOTKEYS", "export", "ctrl+shift+e")

        bindings = [
            (toggle_key, self.hotkey_toggle),
            (capture_key, self.hotkey_capture),
            (clear_key, self.hotkey_clear),
            (focus_key, self.hotkey_focus),
            (export_key, self.hotkey_export),
        ]

        self._warmup_keyboard_listener()

        failed = []
        for combo, handler in bindings:
            try:
                remover = keyboard.add_hotkey(
                    combo,
                    lambda h=handler: self._schedule_on_main_thread(h),
                    suppress=False,
                )
                self._hotkey_removers.append(remover)
            except Exception:
                failed.append(combo)

        if failed:
            self.add_system_message(
                "⚠ Could not register hotkeys (in use or blocked): " + ", ".join(failed)
            )
        elif self._hotkey_removers:
            self._hotkeys_registered = True
        else:
            self.status_label.config(text="ready · hotkeys unavailable")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def _format_exception_message(exc_value):
    """Short, user-facing error text (no stack traces in the overlay)."""
    if exc_value is None:
        return "Unknown error"
    return str(exc_value).strip() or exc_value.__class__.__name__


def install_in_app_error_handlers(root, app):
    """Route uncaught errors to the chat panel instead of OS dialogs."""

    def show_in_app(exc_value):
        msg = _format_exception_message(exc_value)
        if hasattr(app, "add_system_message"):
            app.add_system_message(f"⚠ Error: {msg}")
            if hasattr(app, "status_label"):
                app.status_label.config(text="error · check message above")
        if hasattr(app, "is_sending"):
            app.is_sending = False
        if hasattr(app, "send_button"):
            try:
                app.send_button.config(state=tk.NORMAL)
            except tk.TclError:
                pass

    def handle_exception(exc_type, exc_value, exc_tb):
        root.after(0, lambda: show_in_app(exc_value))

    sys.excepthook = handle_exception

    def tk_callback_exception(exc, val, tb):
        handle_exception(exc, val, tb)

    root.report_callback_exception = tk_callback_exception

    def threading_exception_hook(args):
        if args.exc_value is not None:
            handle_exception(args.exc_type, args.exc_value, args.exc_traceback)

    threading.excepthook = threading_exception_hook


if __name__ == "__main__":
    # System/user environment variables first; optional .env fills missing keys only
    load_environment()

    # Load configuration
    config = load_config()

    # Create root window
    root = tk.Tk()

    # Create app
    app = OverlayApp(root, config)
    install_in_app_error_handlers(root, app)

    # Start event loop
    root.mainloop()
