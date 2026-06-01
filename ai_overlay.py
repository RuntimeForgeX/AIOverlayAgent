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
import ctypes
import configparser
import keyboard
from datetime import datetime
from pathlib import Path
from PIL import ImageGrab, Image
from dotenv import load_dotenv
import re

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
# COLOR THEME
# ============================================================================

COLORS = {
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
}


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
        # For multimodal, include image as base64 in a more detailed format
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

            # Add user message
            if isinstance(message_content, str):
                self.add_text_message(message_content)
            else:
                self.add_image_message(message_content["image"], message_content["text"])
            
            self.trim_history()
            
            # Prepare messages with system prompt
            messages = [SystemMessage(content=self.system_prompt)] + self.conversation_history
            
            # Call Claude API via LangChain
            response = self.llm.invoke(messages)
            reply = response.content
            self.add_assistant_message(reply)
            
            # Get token usage from response metadata
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

            # Add user message
            if isinstance(message_content, str):
                self.add_text_message(message_content)
            else:
                self.add_image_message(message_content["image"], message_content["text"])
            
            self.trim_history()
            
            # Prepare messages with system prompt
            messages = [SystemMessage(content=self.system_prompt)] + self.conversation_history
            
            # Call OpenAI API via LangChain
            response = self.llm.invoke(messages)
            reply = response.content
            self.add_assistant_message(reply)
            
            # Get token usage from response metadata
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

            if isinstance(message_content, str):
                self.add_text_message(message_content)
                response = self.llm.generate_content(
                    message_content,
                    generation_config=genai.types.GenerationConfig(max_output_tokens=self.max_tokens)
                )
            else:
                base64_image = message_content["image"]
                text = message_content["text"]
                self.add_image_message(base64_image, text)
                
                image_bytes = base64.b64decode(base64_image)
                image = Image.open(io.BytesIO(image_bytes))
                
                response = self.llm.generate_content(
                    [image, text],
                    generation_config=genai.types.GenerationConfig(max_output_tokens=self.max_tokens)
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
# MAIN APPLICATION
# ============================================================================

class OverlayApp:
    """Main AI Overlay Application."""
    
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
        self.window_hwnd = None  # Will store window handle for invisibility reapplication
        self.window_opacity = 0.94
        self.window_invisible = False  # Track if invisibility was successfully applied
        self._hotkeys_registered = False
        self._hotkey_removers = []

        # Section customization
        self.sections_enabled = {
            "mcq": True,
            "cpp": True,
            "sql": True,
            "dsa": True
        }
        
        # Build UI first; API client initializes lazily when you send a message
        self.setup_window()
        self.provider = get_provider(config)
        if not self.provider.is_ready():
            self.status_label.config(text="ready · set API key in environment")

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
        
        # Store opacity for later use
        self.window_opacity = opacity

        # Make draggable and build UI first, then apply capture invisibility
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
        header_frame = tk.Frame(self.root, bg=COLORS["bg_header"], height=40)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        # Title and dot
        title_label = tk.Label(
            header_frame, text="● AI OVERLAY",
            fg=COLORS["accent_green"], bg=COLORS["bg_header"],
            font=("Courier New", 10, "bold")
        )
        title_label.pack(side=tk.LEFT, padx=10, pady=8)
        
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
        model_menu = InvisibleModelDropdown(
            header_frame,
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
        model_menu.pack(side=tk.RIGHT, padx=5, pady=8)
        
        # Opacity slider (placeholder for now)
        opacity_label = tk.Label(
            header_frame, text="[opacity]",
            fg=COLORS["text_dim"], bg=COLORS["bg_header"],
            font=("Courier New", 8)
        )
        opacity_label.pack(side=tk.RIGHT, padx=10, pady=8)
        
        # Chat history panel
        chat_frame = tk.Frame(self.root, bg=COLORS["bg_chat"])
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
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
        self.chat_display.tag_config("you_label", foreground=COLORS["accent_green"], font=("Courier New", 9, "bold"))
        self.chat_display.tag_config("ai_label", foreground=COLORS["accent_blue"], font=("Courier New", 9, "bold"))
        self.chat_display.tag_config("ai_text", foreground=COLORS["accent_blue"])
        self.chat_display.tag_config("timestamp", foreground=COLORS["text_dim"], font=("Courier New", 8))
        self.chat_display.tag_config("error", foreground=COLORS["error_red"])
        self.chat_display.tag_config("code_block", background=COLORS["code_bg"], foreground=COLORS["code_fg"], font=("Courier New", 8))
        self.chat_display.tag_config("system", foreground=COLORS["text_dim"])
        
        # Input frame
        input_frame = tk.Frame(self.root, bg=COLORS["bg_input"])
        input_frame.pack(fill=tk.X, padx=8, pady=8)
        
        self.input_box = tk.Entry(
            input_frame,
            bg=COLORS["bg_input"],
            fg=COLORS["text_normal"],
            font=("Courier New", 9),
            relief=tk.FLAT,
            insertbackground=COLORS["accent_green"]
        )
        self.input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.input_box.bind("<Return>", lambda e: self.send_message())
        
        self.send_button = tk.Button(
            input_frame,
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
        buttons_frame = tk.Frame(self.root, bg=COLORS["bg_main"])
        buttons_frame.pack(fill=tk.X, padx=8, pady=4)
        
        tk.Button(
            buttons_frame,
            text="📷 Capture",
            bg=COLORS["bg_header"],
            fg=COLORS["text_normal"],
            font=("Courier New", 8),
            relief=tk.FLAT,
            command=self.hotkey_capture
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            buttons_frame,
            text="🗑 Clear",
            bg=COLORS["bg_header"],
            fg=COLORS["text_normal"],
            font=("Courier New", 8),
            relief=tk.FLAT,
            command=self.hotkey_clear
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            buttons_frame,
            text="💾 Export",
            bg=COLORS["bg_header"],
            fg=COLORS["text_normal"],
            font=("Courier New", 8),
            relief=tk.FLAT,
            command=self.hotkey_export
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            buttons_frame,
            text="⚙️ Settings",
            bg=COLORS["bg_header"],
            fg=COLORS["text_normal"],
            font=("Courier New", 8),
            relief=tk.FLAT,
            command=self.open_settings
        ).pack(side=tk.LEFT, padx=2)
        
        # Status bar
        status_frame = tk.Frame(self.root, bg=COLORS["border"], height=1)
        status_frame.pack(fill=tk.X)
        
        self.status_label = tk.Label(
            self.root,
            text="ready · 0 in / 0 out tokens",
            bg=COLORS["bg_main"],
            fg=COLORS["text_dim"],
            font=("Courier New", 8)
        )
        self.status_label.pack(fill=tk.X, padx=8, pady=4)
    
    def add_message_to_display(self, role, text, is_system=False):
        """Add a message to the chat display."""
        self.chat_display.config(state=tk.NORMAL)
        
        timestamp = datetime.now().strftime("%H:%M")
        
        if is_system:
            self.chat_display.insert(tk.END, f"\n{text}\n", "system")
        else:
            if role == "you":
                self.chat_display.insert(tk.END, f"\n{timestamp}  ", "timestamp")
                self.chat_display.insert(tk.END, "▶ you\n", "you_label")
                
                # Handle [Screenshot] placeholder
                if "[Screenshot]" in text:
                    parts = text.split("[Screenshot]")
                    self.chat_display.insert(tk.END, parts[0], "text_normal")
                    self.chat_display.insert(tk.END, "[Screenshot]", "ai_label")
                    if len(parts) > 1:
                        self.chat_display.insert(tk.END, parts[1], "text_normal")
                else:
                    self.chat_display.insert(tk.END, text, "text_normal")
                self.chat_display.insert(tk.END, "\n")
            
            else:  # AI response
                self.chat_display.insert(tk.END, f"\n{timestamp}  ", "timestamp")
                self.chat_display.insert(tk.END, "◆ ai\n", "ai_label")
                
                # Parse code blocks
                lines = text.split("\n")
                in_code_block = False
                for line in lines:
                    if line.startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    
                    if in_code_block:
                        self.chat_display.insert(tk.END, line + "\n", "code_block")
                    else:
                        self.chat_display.insert(tk.END, line + "\n", "ai_text")
        
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def add_system_message(self, text):
        """Add a system message."""
        self.add_message_to_display("system", text, is_system=True)
    
    def send_message(self):
        """Send a text message to the AI."""
        if not self.provider:
            return
        
        if self.is_sending:
            return
        
        message_text = self.input_box.get().strip()
        if not message_text:
            return
        
        self.input_box.delete(0, tk.END)
        self.is_sending = True
        self.send_button.config(state=tk.DISABLED)
        self.message_count += 1
        
        # Display user message
        self.add_message_to_display("you", message_text)
        self.status_label.config(text="thinking...")
        
        # Send in background thread
        def api_call():
            try:
                self.provider.send_message(
                    message_text,
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
        """Capture screen and send to AI (Ctrl+Shift+S)."""
        if not self.provider or self.is_sending:
            return
        
        # Hide window, capture, show window
        self.root.withdraw()
        time.sleep(0.25)
        
        base64_image = capture_and_compress_screenshot()
        
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        
        # Re-apply privacy flags after showing window
        apply_invisibility_to_tkinter_window(self.root)
        
        if not base64_image:
            self.add_message_to_display("system", "⚠ Screenshot capture failed", is_system=True)
            return
        
        self.is_sending = True
        self.send_button.config(state=tk.DISABLED)
        self.message_count += 1
        self.screenshot_count += 1
        
        # Display user message
        self.add_message_to_display("you", "[Screenshot] What is this?")
        self.status_label.config(text="sending screenshot...")
        
        # Send in background thread
        def api_call():
            try:
                self.provider.send_message(
                    {"image": base64_image, "text": "What is shown in this screenshot? Analyze it and provide relevant help."},
                    self.on_api_response,
                    self.on_api_error
                )
            except Exception as e:
                self.on_api_error(str(e))
        
        thread = threading.Thread(target=api_call, daemon=True)
        thread.start()
    
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
            if msg["role"] == "user":
                content += "**You:** \n"
            else:
                content += "**AI:** \n"
            
            if isinstance(msg["content"], str):
                content += msg["content"] + "\n"
            else:
                # Content is list with image
                for item in msg["content"]:
                    if item["type"] == "text":
                        content += item["text"] + "\n"
                    elif item["type"] == "image":
                        content += "[screenshot]\n"
        
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
