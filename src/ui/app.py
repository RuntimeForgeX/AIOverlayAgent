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
import ctypes

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
from src.services.storage import (
    load_theme_preference,
    save_theme_preference,
    save_display_log,
    load_display_log,
    save_screenshot_queue_to_disk,
    load_screenshot_queue_from_disk,
    load_prompt_profile_id,
    save_prompt_profile_id,
    clear_screenshot_queue,
)
from src.prompts import (
    get_all_prompts,
    get_prompt_by_id,
    get_prompt_by_title,
    get_default_prompt_id,
)
from src.services.capture import capture_and_compress_screenshot
from src.utils.win32_invisibility import (
    apply_capture_exclusion,
    apply_invisibility_to_tkinter_window,
    apply_overlay_window_config,
    get_tkinter_hwnd,
    get_window_handle,
    find_window_by_class,
    hide_window_from_taskbar,
    make_window_invisible_to_capture,
    present_overlay_window,
    assign_ephemeral_window_title,
    InvisibleContextMenu,
    InvisibleModelDropdown,
    InvisibleTopLevel,
)
from src.config.models import (
    model_labels,
    build_model_map,
    resolve_model_label,
    apply_model_to_config,
)
from src.services.llm_provider import get_provider, HumanMessage, AIMessage
from src.ui.markdown.renderer import configure_markdown_tags, render_markdown, clean_bmp
from src.ui.cursor import refresh_cursor_policy
from src.ui.close_button import create_header_close_button
# ============================================================================
# MAIN APPLICATION
# ============================================================================

class OverlayApp:
    """Main AI Overlay Application."""
    
    THEME_ICONS = {"dark": "🌙", "light": "☀", "system": "🖥"}
    THEME_CYCLE = ["dark", "light", "system"]
    MAX_QUEUE = 10

    def __init__(self, root, config, personal_context_manager=None, meeting_storage=None):
        self.root = root
        self.config = config
        self.personal_context_manager = personal_context_manager
        self.meeting_storage = meeting_storage
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

        # Load theme preference and apply
        theme_pref = load_theme_preference()
        set_active_theme(theme_pref)

        self.prompt_profiles = get_all_prompts()
        saved_prompt_id = load_prompt_profile_id()
        self.selected_prompt_id = (
            saved_prompt_id
            if get_prompt_by_id(saved_prompt_id)
            else get_default_prompt_id()
        )
        initial_prompt = get_prompt_by_id(self.selected_prompt_id)

        # Build UI first; API client initializes lazily when you send a message
        self.setup_window()
        self.provider = get_provider(
            config, system_prompt=initial_prompt["systemPrompt"]
        )
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
        # Aggressive initial pass + periodic lightweight re-check.
        self.root.after(0, self.apply_main_window_invisibility)
        self.root.after(100, self.apply_main_window_invisibility)
        self.root.after(500, self.apply_main_window_invisibility)
        self.root.after(1500, self._start_invisibility_polling)

        for event in ("<Map>", "<FocusIn>"):
            self.root.bind(
                event,
                lambda e: self.apply_main_window_invisibility(),
                add="+",
            )

    def _start_invisibility_polling(self):
        """Periodic re-polling at 5-second intervals.
        Skipped when window is hidden or invisibility is already confirmed.
        """
        if not self.is_visible:
            self.root.after(5000, self._start_invisibility_polling)
            return
        if not self.window_invisible:
            self.apply_main_window_invisibility()
        self.root.after(5000, self._start_invisibility_polling)

    def setup_window(self):
        """Setup tkinter window with proper invisibility configuration."""
        width = int(get_config_value(self.config, "UI", "width", "500"))
        height = int(get_config_value(self.config, "UI", "height", "650"))
        start_x = int(get_config_value(self.config, "UI", "start_x", "60"))
        start_y = int(get_config_value(self.config, "UI", "start_y", "60"))
        opacity = float(get_config_value(self.config, "UI", "opacity", "0.94"))
        
        self.root.geometry(f"{width}x{height}+{start_x}+{start_y}")
        # Randomize the OS window title: the visible UI header is the "real" title.
        assign_ephemeral_window_title(self.root, hint="overlay")
        self.root.configure(bg=COLORS["bg_main"])
        apply_overlay_window_config(self.root, opacity=opacity)
        self.root.resizable(False, False)
        
        self.window_opacity = opacity

        self.setup_drag()
        self.build_ui()
        refresh_cursor_policy(self.root)
        self.apply_main_window_invisibility()

    def apply_main_window_invisibility(self, verbose=False):
        """Apply capture exclusion to the main overlay and all process windows."""
        self.root.update_idletasks()
        self.root.update()

        hide_window_from_taskbar(self.root)
        success = apply_capture_exclusion(self.root, title=None, verbose=verbose)
        self.window_invisible = success

        hwnd = get_tkinter_hwnd(self.root)
        if hwnd:
            self.window_hwnd = hwnd

        if verbose:
            if self.window_invisible:
                self.add_system_message("[OK] Initialized · INVISIBLE TO RECORDINGS · Ready")
            else:
                self.add_system_message("[WARN] Initialized · INVISIBILITY NOT CONFIRMED · Check console")

    def apply_invisibility_alternative(self):
        """Fallback if primary capture exclusion fails."""
        try:
            hwnd = get_tkinter_hwnd(self.root)
            if not hwnd:
                hwnd = find_window_by_class("Tk")
            if hwnd and hwnd > 0:
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
        
        # Model selector dropdown (OpenRouter + direct APIs)
        models = model_labels()
        self.model_var = tk.StringVar(value=resolve_model_label(self.config))
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

        prompt_titles = [p["title"] for p in self.prompt_profiles]
        initial_prompt_title = get_prompt_by_id(self.selected_prompt_id)["title"]
        self.prompt_var = tk.StringVar(value=initial_prompt_title)
        self.prompt_dropdown = InvisibleModelDropdown(
            self.header_frame,
            self.prompt_var,
            prompt_titles,
            command=self.change_prompt_profile,
            bg=COLORS["bg_header"],
            fg=COLORS["accent_blue"],
            font=("Courier New", 8),
            relief=tk.FLAT,
            activebackground=COLORS["bg_input"],
            activeforeground=COLORS["accent_blue"],
            highlightthickness=0,
            bd=0,
        )
        self.prompt_dropdown.pack(side=tk.RIGHT, padx=5, pady=8)
        
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
            ("📄 Context", self.open_personal_context),
            ("🎤 Meeting", self.open_meeting_assistant),
            ("💾 Export", self.hotkey_export),
            ("✕ Close", self._on_window_close),
        ]
        for text, cmd in btn_defs:
            is_close = text == "✕ Close"
            btn = tk.Button(
                self.buttons_frame,
                text=text,
                bg=COLORS["bg_header"],
                fg=COLORS["error_red"] if is_close else COLORS["text_normal"],
                font=("Courier New", 8, "bold") if is_close else ("Courier New", 8),
                relief=tk.FLAT,
                command=cmd,
            )
            btn.pack(side=tk.LEFT, padx=2)
            self._quick_buttons.append(btn)
        
        # Status bar
        self.status_frame = tk.Frame(self.root, bg=COLORS["border"], height=1)
        self.status_frame.pack(fill=tk.X)

        self.footer_frame = tk.Frame(self.root, bg=COLORS["bg_main"])
        self.footer_frame.pack(fill=tk.X, padx=8, pady=(4, 8))

        self.status_label = tk.Label(
            self.footer_frame,
            text="ready · 0 in / 0 out tokens",
            bg=COLORS["bg_main"],
            fg=COLORS["text_dim"],
            font=("Courier New", 8),
            anchor="w",
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

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

            preview_header = tk.Frame(preview, bg=COLORS["bg_header"])
            preview_header.pack(fill=tk.X)
            tk.Label(
                preview_header,
                text="Screenshot Preview",
                fg=COLORS["accent_green"],
                bg=COLORS["bg_header"],
                font=("Courier New", 10, "bold"),
            ).pack(side=tk.LEFT, padx=10, pady=6)
            create_header_close_button(
                preview_header, preview.destroy,
            ).pack(side=tk.RIGHT, padx=(4, 8), pady=4)

            photo = ImageTk.PhotoImage(image)
            lbl = tk.Label(preview, image=photo, bg=COLORS["bg_main"])
            lbl.image = photo
            lbl.pack(padx=5, pady=5)

            preview.show()
        except Exception:
            self.add_system_message("[WARN] Could not preview screenshot")

    def _show_thumb_context_menu(self, event, idx):
        """Show right-click context menu for a thumbnail (capture-excluded)."""
        items = [("Preview", lambda: self._preview_screenshot(idx), True)]
        if idx > 0:
            items.append(("◀ Move Left", lambda: self._move_screenshot(idx, -1), True))
        if idx < len(self.screenshot_queue) - 1:
            items.append(("Move Right ▶", lambda: self._move_screenshot(idx, 1), True))
        items.append(("─" * 24, lambda: None, False))
        items.append(("✕ Remove", lambda: self._remove_screenshot(idx), True))
        menu = InvisibleContextMenu(self.root, items)
        menu.open_at(event.x_root, event.y_root)

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
            
            # Reconstruct LLM provider conversation history for active context
            if not is_system and self.provider and text.strip():
                if role == "you":
                    self.provider.add_text_message(text)
                elif role == "ai":
                    self.provider.add_assistant_message(text)
                    
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

        # Prompt profile dropdown
        self.prompt_dropdown.configure(bg=c["bg_header"])
        self.prompt_dropdown.button.configure(
            bg=c["bg_header"], fg=c["accent_blue"],
            activebackground=c["bg_input"], activeforeground=c["accent_blue"],
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
            if btn.cget("text") == "✕ Close":
                btn.configure(bg=c["bg_header"], fg=c["error_red"])
            else:
                btn.configure(bg=c["bg_header"], fg=c["text_normal"])

        # Footer / status
        self.status_frame.configure(bg=c["border"])
        self.footer_frame.configure(bg=c["bg_main"])
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
            self.chat_display.insert(tk.END, f"\n{clean_bmp(text)}\n", "system")
        else:
            if role == "you":
                self.chat_display.insert(tk.END, f"\n{timestamp}  ", "timestamp")
                self.chat_display.insert(tk.END, "▶ you\n", "you_label")
                
                # Handle screenshot indicator
                if "[📷" in text or "[Screenshot]" in text:
                    self.chat_display.insert(tk.END, clean_bmp(text) + "\n", "screenshot_tag")
                else:
                    self.chat_display.insert(tk.END, clean_bmp(text) + "\n", "text_normal")
            
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

        # Build display text (screenshot-only sends no default caption)
        if has_screenshots:
            n = len(self.screenshot_queue)
            prefix = f"[📷 ×{n}]" if n > 1 else "[📷]"
            display_text = f"{prefix} {message_text}".strip() if message_text else prefix
        else:
            display_text = message_text
        
        self.add_message_to_display("you", display_text)
        self.status_label.config(text="thinking...")
        
        # Build API message content — only user-typed text (may be empty with screenshots)
        if has_screenshots:
            images = [entry["b64"] for entry in self.screenshot_queue]
            api_text = message_text.strip()
            if not api_text:
                api_text = "Please analyze the screenshot(s)."
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
        
        # Inject personal context if enabled (additive — does not change existing flow)
        if self.personal_context_manager and self.personal_context_manager.is_enabled():
            try:
                from modules.personal_context.context_builder import build_context_block
                context_block = build_context_block(self.personal_context_manager)
                if context_block:
                    # Temporarily augment system prompt with context
                    original_prompt = self.provider.system_prompt
                    self.provider.system_prompt = original_prompt + "\n\n" + context_block
                    
                    # Wrap the send_message call to restore the original prompt afterward
                    def wrapped_on_response(reply, tokens):
                        self.provider.system_prompt = original_prompt
                        self.on_api_response(reply, tokens)
                        
                    def wrapped_on_error(error_text):
                        self.provider.system_prompt = original_prompt
                        self.on_api_error(error_text)
                        
                    # Send in background thread
                    def api_call():
                        try:
                            self.provider.send_message(
                                message_content,
                                wrapped_on_response,
                                wrapped_on_error
                            )
                        except Exception as e:
                            wrapped_on_error(str(e))
                    
                    thread = threading.Thread(target=api_call, daemon=True)
                    thread.start()
                    return
            except Exception as e:
                self.add_system_message(f"[WARN] Failed to inject personal context: {e}")
        
        # Send in background thread (default path)
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
            present_overlay_window(self.root)
            self.is_visible = True
    
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
        
        present_overlay_window(self.root)

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
    
    def change_prompt_profile(self, title):
        """Switch the active system prompt profile."""
        if self.is_sending:
            self.add_system_message("[WARN] Cannot switch prompt profile while AI is thinking.")
            curr_profile = get_prompt_by_id(self.selected_prompt_id)
            if curr_profile:
                self.prompt_var.set(curr_profile["title"])
            return

        profile = get_prompt_by_title(title)
        if not profile:
            self.add_system_message(f"[WARN] Unknown prompt profile: {title}")
            return
        if profile["id"] == self.selected_prompt_id:
            return

        self.selected_prompt_id = profile["id"]
        save_prompt_profile_id(profile["id"])
        if self.provider:
            self.provider.apply_system_prompt(profile["systemPrompt"])
        self.add_system_message(f"[OK] prompt → {profile['title']}")

    def change_model(self, model_name):
        """Change the AI model on the fly."""
        if self.is_sending:
            self.add_system_message("[WARN] Cannot switch model while AI is thinking.")
            self.model_var.set(resolve_model_label(self.config))
            return

        model_map = build_model_map()

        if model_name not in model_map:
            self.add_system_message(f"[WARN] Unknown model: {model_name}")
            return

        provider_name, model_id = model_map[model_name]

        try:
            load_environment()

            try:
                apply_model_to_config(self.config, provider_name, model_id)
            except ValueError as exc:
                self.add_system_message(f"[WARN] {exc}")
                return
            
            # Reinitialize provider and restore selected prompt profile
            profile = get_prompt_by_id(self.selected_prompt_id)
            system_prompt = profile["systemPrompt"] if profile else None
            self.provider = get_provider(self.config, system_prompt=system_prompt)
            
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
    
    def open_personal_context(self):
        """Open the Personal Context manager."""
        if not self.personal_context_manager:
            self.add_system_message("[WARN] Personal Context module not loaded.")
            return
            
        try:
            from modules.personal_context.ui import PersonalContextUI
            if not hasattr(self, '_personal_context_ui'):
                self._personal_context_ui = PersonalContextUI(
                    self.root, 
                    self.personal_context_manager,
                    add_system_message=self.add_system_message
                )
            self._personal_context_ui.open()
        except Exception as e:
            self.add_system_message(f"[WARN] Failed to open Personal Context: {e}")

    def open_meeting_assistant(self):
        """Open the Meeting Assistant."""
        if not self.meeting_storage:
            self.add_system_message("[WARN] Meeting Assistant module not loaded.")
            return
            
        try:
            from modules.meeting_assistant.ui import MeetingAssistantUI
            if not hasattr(self, '_meeting_assistant_ui'):
                self._meeting_assistant_ui = MeetingAssistantUI(
                    self.root,
                    self.meeting_storage,
                    personal_context_manager=self.personal_context_manager,
                    config=self.config,
                    add_system_message=self.add_system_message
                )
            self._meeting_assistant_ui.open()
        except Exception as e:
            self.add_system_message(f"[WARN] Failed to open Meeting Assistant: {e}")
    
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
        # Security: clear any volatile screenshot data on clean exit.
        clear_screenshot_queue()
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


