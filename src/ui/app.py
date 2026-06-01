import tkinter as tk
import time
import os
import io
import json
import base64
import threading
from datetime import datetime
from PIL import Image, ImageTk
from tkinter import scrolledtext
import keyboard

from src.ui.styles.themes import COLORS, _current_theme_name, set_active_theme, detect_system_theme
from src.config.settings import (
    get_config_value,
    WINDOW_TITLE,
    APP_NAME,
    is_frozen_app,
    get_resource_root,
    get_user_data_root,
    load_environment,
)
from src.services.storage import load_theme_preference, save_theme_preference, save_display_log, load_display_log, save_screenshot_queue_to_disk, load_screenshot_queue_from_disk
from src.services.capture import capture_and_compress_screenshot
from src.utils.win32_invisibility import (
    apply_capture_exclusion,
    apply_invisibility_to_tkinter_window,
    get_tkinter_hwnd,
    get_window_handle,
    find_window_by_class,
    hide_window_from_taskbar,
    make_window_invisible_to_capture,
    InvisibleModelDropdown,
    InvisibleTopLevel,
)
from src.services.llm_provider import get_provider, HumanMessage, AIMessage
from src.ui.markdown.renderer import configure_markdown_tags, render_markdown
from src.ui.cursor import refresh_cursor_policy
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
        refresh_cursor_policy(self.root)
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
                print("[OK] Invisibility configuration complete\n")
            else:
                print("[WARN] Invisibility may be incomplete\n")
                self.apply_invisibility_alternative()

        if verbose:
            if self.window_invisible:
                self.add_system_message("[OK] Initialized · INVISIBLE TO RECORDINGS · Ready")
            else:
                self.add_system_message("[WARN] Initialized · INVISIBILITY NOT CONFIRMED · Check console")

    def apply_invisibility_alternative(self):
        """Fallback if title-based lookup fails."""
        try:
            hwnd = get_tkinter_hwnd(self.root) or get_window_handle(WINDOW_TITLE)
            if not hwnd:
                hwnd = find_window_by_class("Tk")
            if hwnd and hwnd > 0:
                print(f"Found fallback window handle: {hwnd}")
                self.window_hwnd = hwnd
                if make_window_invisible_to_capture(hwnd):
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
            font=("Courier New", 10),
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
            self.add_system_message(f"[WARN] Queue full (max {self.MAX_QUEUE})")
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
            refresh_cursor_policy(preview)
        except Exception:
            self.add_system_message("[WARN] Could not preview screenshot")

    def _show_thumb_context_menu(self, event, idx):
        """Show right-click context menu for a thumbnail."""
        menu = tk.Menu(
            self.root, tearoff=0,
            bg=COLORS["bg_input"], fg=COLORS["text_normal"],
            activebackground=COLORS["accent_green"],
            activeforeground=COLORS["bg_main"],
            font=("Courier New", 8),
            cursor="arrow",
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

        refresh_cursor_policy(self.thumb_strip_frame)

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
        refresh_cursor_policy(self.root)

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
        self.add_message_to_display("system", f"[WARN] Error: {error_text}", is_system=True)
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
            self.add_system_message("[WARN] Screenshot capture failed")
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
            self.add_system_message("[WARN] No conversation to export")
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
            if HumanMessage is not None and isinstance(msg, HumanMessage):
                content += "**You:**\n"
            elif AIMessage is not None and isinstance(msg, AIMessage):
                content += "**AI:**\n"
            elif type(msg).__name__ == "HumanMessage":
                content += "**You:**\n"
            elif type(msg).__name__ == "AIMessage":
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

        self.add_system_message(f"[OK] Exported to {filename}")
    
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
            self.add_system_message(f"[WARN] Unknown model: {model_name}")
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
            
            self.add_system_message(f"[OK] switched to {model_name}")
            self.status_label.config(text="ready · 0 in / 0 out tokens")
            
        except Exception as e:
            self.add_system_message(f"[WARN] Error switching model: {str(e)}")
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
            self.add_system_message(f"[OK] Sections updated")
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
        refresh_cursor_policy(settings_window)
    
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
                self.add_system_message("[OK] System prompt updated")
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
        refresh_cursor_policy(prompt_window)
    
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
                "[WARN] Could not register hotkeys (in use or blocked): " + ", ".join(failed)
            )
        elif self._hotkey_removers:
            self._hotkeys_registered = True
        else:
            self.status_label.config(text="ready · hotkeys unavailable")


