"""
Personal Context UI — Tkinter panel for managing stored context documents.

Uses InvisibleOverlayPanel / InvisibleTopLevel from win32_invisibility for
taskbar-free, non-activating, capture-excluded windows.
"""

import tkinter as tk
from tkinter import scrolledtext, filedialog
from datetime import datetime

from src.ui.styles.themes import COLORS
from src.ui.close_button import create_header_close_button
from src.utils.win32_invisibility import InvisibleTopLevel, InvisibleOverlayPanel, present_overlay_window


def _format_size(size_bytes: int) -> str:
    """Format file size for display."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _format_date(iso_date: str) -> str:
    """Format ISO date for display."""
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_date[:16] if len(iso_date) >= 16 else iso_date


class PersonalContextUI:
    """UI panel for the Personal Context System."""

    def __init__(self, parent, manager, add_system_message=None):
        self.parent = parent
        self.manager = manager
        self.add_system_message = add_system_message or (lambda msg: None)
        self.window = None

    def open(self):
        """Open the personal context management window."""
        if self.window and self.window.winfo_exists():
            present_overlay_window(self.window)
            return

        self.window = InvisibleOverlayPanel(self.parent)
        self.window.title("Personal Context Manager")
        self.window.geometry("620x600")
        self.window.configure(bg=COLORS["bg_main"])

        self._build_ui()
        self.window.show()

    def _add_dialog_header(self, window, title, on_close=None):
        """Title bar with a visible close control for sub-dialogs."""
        on_close = on_close or window.destroy
        c = COLORS
        header = tk.Frame(window, bg=c["bg_header"])
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text=title,
            fg=c["accent_green"],
            bg=c["bg_header"],
            font=("Courier New", 11, "bold"),
        ).pack(side=tk.LEFT, padx=10, pady=8)
        create_header_close_button(header, on_close, colors=c).pack(
            side=tk.RIGHT, padx=(4, 8), pady=6,
        )

    def _build_ui(self):
        """Build all UI components."""
        win = self.window
        c = COLORS

        # ---- Header ----
        header = tk.Frame(win, bg=c["bg_header"])
        header.pack(fill=tk.X)

        header.bind("<Button-1>", self._start_move)
        header.bind("<B1-Motion>", self._do_move)

        title_label = tk.Label(
            header, text="📄 Personal Context",
            fg=c["accent_green"], bg=c["bg_header"],
            font=("Courier New", 12, "bold"),
        )
        title_label.pack(side=tk.LEFT, padx=10, pady=8)
        title_label.bind("<Button-1>", self._start_move)
        title_label.bind("<B1-Motion>", self._do_move)

        # Enable toggle
        self._enabled_var = tk.BooleanVar(value=self.manager.is_enabled())
        enable_cb = tk.Checkbutton(
            header, text="Enable",
            variable=self._enabled_var,
            command=self._toggle_enabled,
            bg=c["bg_header"], fg=c["accent_green"],
            selectcolor=c["bg_header"],
            activebackground=c["bg_header"],
            activeforeground=c["accent_green"],
            font=("Courier New", 9),
        )
        enable_cb.pack(side=tk.RIGHT, padx=10, pady=8)

        create_header_close_button(
            header, self.window.destroy, colors=c,
        ).pack(side=tk.RIGHT, padx=(4, 8), pady=6)

        # ---- Search bar ----
        search_frame = tk.Frame(win, bg=c["bg_main"])
        search_frame.pack(fill=tk.X, padx=10, pady=(8, 4))

        tk.Label(
            search_frame, text="🔍",
            fg=c["text_dim"], bg=c["bg_main"],
            font=("Courier New", 10),
        ).pack(side=tk.LEFT, padx=(0, 5))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_list())
        search_entry = tk.Entry(
            search_frame,
            textvariable=self._search_var,
            bg=c["bg_input"], fg=c["text_normal"],
            font=("Courier New", 9),
            relief=tk.FLAT,
            insertbackground=c["accent_green"],
        )
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ---- Action buttons ----
        btn_frame = tk.Frame(win, bg=c["bg_main"])
        btn_frame.pack(fill=tk.X, padx=10, pady=4)

        for text, cmd in [
            ("📎 Upload File", self._upload_file),
            ("📝 Paste Text", self._paste_text),
        ]:
            tk.Button(
                btn_frame, text=text, command=cmd,
                bg=c["bg_header"], fg=c["text_normal"],
                font=("Courier New", 8), relief=tk.FLAT,
            ).pack(side=tk.LEFT, padx=2)

        # ---- Items list (scrollable) ----
        list_container = tk.Frame(win, bg=c["bg_chat"])
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        self._list_canvas = tk.Canvas(
            list_container, bg=c["bg_chat"], highlightthickness=0,
        )
        scrollbar = tk.Scrollbar(
            list_container, orient=tk.VERTICAL,
            command=self._list_canvas.yview,
        )
        self._list_inner = tk.Frame(self._list_canvas, bg=c["bg_chat"])
        self._list_canvas.create_window((0, 0), window=self._list_inner, anchor="nw")
        self._list_canvas.configure(yscrollcommand=scrollbar.set)

        def _on_frame_configure(event):
            self._list_canvas.configure(scrollregion=self._list_canvas.bbox("all"))

        self._list_inner.bind("<Configure>", _on_frame_configure)

        self._list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mousewheel scrolling
        def _on_mousewheel(event):
            self._list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self._list_canvas.bind("<MouseWheel>", _on_mousewheel)
        self._list_inner.bind("<MouseWheel>", _on_mousewheel)

        # ---- Status bar ----
        self._status_label = tk.Label(
            win, text="",
            bg=c["bg_main"], fg=c["text_dim"],
            font=("Courier New", 8),
        )
        self._status_label.pack(fill=tk.X, padx=10, pady=4)

        self._refresh_list()

    def _refresh_list(self):
        """Refresh the items list display."""
        for widget in self._list_inner.winfo_children():
            widget.destroy()

        c = COLORS
        query = self._search_var.get().strip() if hasattr(self, "_search_var") else ""
        items = self.manager.search_items(query) if query else self.manager.get_all_items()

        if not items:
            tk.Label(
                self._list_inner,
                text="No context items. Upload a file or paste text.",
                fg=c["text_dim"], bg=c["bg_chat"],
                font=("Courier New", 9),
            ).pack(pady=20)
            self._update_status(0)
            return

        for item in items:
            self._create_item_row(item)

        self._update_status(len(items))

    def _create_item_row(self, item: dict):
        """Create a single item row in the list."""
        c = COLORS

        row = tk.Frame(
            self._list_inner, bg=c["bg_input"],
            highlightbackground=c["border"], highlightthickness=1,
        )
        row.pack(fill=tk.X, padx=2, pady=2)

        # Bind mousewheel to row and all children
        def _on_mousewheel(event):
            self._list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        row.bind("<MouseWheel>", _on_mousewheel)

        # Info section
        info_frame = tk.Frame(row, bg=c["bg_input"])
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=4)
        info_frame.bind("<MouseWheel>", _on_mousewheel)

        type_icons = {"pdf": "📕", "docx": "📘", "txt": "📝"}
        icon = type_icons.get(item.get("type", "txt"), "📄")

        name_label = tk.Label(
            info_frame,
            text=f"{icon} {item['name']}",
            fg=c["text_normal"], bg=c["bg_input"],
            font=("Courier New", 9, "bold"),
            anchor="w",
        )
        name_label.pack(anchor=tk.W)
        name_label.bind("<MouseWheel>", _on_mousewheel)

        meta_text = (
            f"{item.get('type', 'txt').upper()} · "
            f"{_format_size(item.get('size', 0))} · "
            f"{_format_date(item.get('date_added', ''))}"
        )
        meta_label = tk.Label(
            info_frame, text=meta_text,
            fg=c["text_dim"], bg=c["bg_input"],
            font=("Courier New", 7),
            anchor="w",
        )
        meta_label.pack(anchor=tk.W)
        meta_label.bind("<MouseWheel>", _on_mousewheel)

        # Action buttons
        btn_frame = tk.Frame(row, bg=c["bg_input"])
        btn_frame.pack(side=tk.RIGHT, padx=4, pady=4)
        btn_frame.bind("<MouseWheel>", _on_mousewheel)

        item_id = item["id"]
        actions = [
            ("👁", lambda iid=item_id: self._view_item(iid)),
            ("✏", lambda iid=item_id: self._edit_item(iid)),
            ("✎", lambda iid=item_id: self._rename_item(iid)),
            ("✕", lambda iid=item_id: self._delete_item(iid)),
        ]
        for text, cmd in actions:
            btn = tk.Label(
                btn_frame, text=text,
                fg=c["text_dim"], bg=c["bg_input"],
                font=("Courier New", 10),
                cursor="arrow",
            )
            btn.pack(side=tk.LEFT, padx=3)
            btn.bind("<Button-1>", lambda e, fn=cmd: fn())
            btn.bind(
                "<Enter>",
                lambda e, b=btn: b.config(fg=c["accent_green"]),
            )
            btn.bind(
                "<Leave>",
                lambda e, b=btn: b.config(fg=c["text_dim"]),
            )
            btn.bind("<MouseWheel>", _on_mousewheel)

    def _update_status(self, count: int):
        enabled_text = "ON" if self.manager.is_enabled() else "OFF"
        self._status_label.config(
            text=f"{count} item(s) · context {enabled_text} · "
                 f"token limit: {self.manager.get_token_limit()}"
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _toggle_enabled(self):
        enabled = self._enabled_var.get()
        self.manager.set_enabled(enabled)
        state = "enabled" if enabled else "disabled"
        self.add_system_message(f"[OK] Personal context {state}")
        self._refresh_list()

    def _upload_file(self):
        """Open file dialog to upload PDF/DOCX/TXT."""
        file_path = filedialog.askopenfilename(
            parent=self.window,
            title="Select file to add as context",
            filetypes=[
                ("Supported files", "*.pdf *.docx *.doc *.txt *.md"),
                ("PDF files", "*.pdf"),
                ("Word documents", "*.docx *.doc"),
                ("Text files", "*.txt *.md"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            item = self.manager.add_file(file_path)
            self.add_system_message(f"[OK] Added context: {item['name']}")
            self._refresh_list()
        except Exception as e:
            self.add_system_message(f"[WARN] Failed to add file: {e}")

    def _paste_text(self):
        """Open a dialog to paste text content."""
        dialog = InvisibleTopLevel(self.window)
        dialog.title("Paste Text Content")
        dialog.geometry("500x400")
        dialog.configure(bg=COLORS["bg_main"])
        c = COLORS
        self._add_dialog_header(dialog, "Paste Text Content")

        tk.Label(
            dialog, text="Name:",
            fg=c["text_normal"], bg=c["bg_main"],
            font=("Courier New", 9),
        ).pack(padx=10, pady=(10, 2), anchor=tk.W)

        name_entry = tk.Entry(
            dialog,
            bg=c["bg_input"], fg=c["text_normal"],
            font=("Courier New", 9), relief=tk.FLAT,
            insertbackground=c["accent_green"],
        )
        name_entry.pack(fill=tk.X, padx=10, pady=(0, 8))
        name_entry.insert(0, "Pasted Text")

        tk.Label(
            dialog, text="Content:",
            fg=c["text_normal"], bg=c["bg_main"],
            font=("Courier New", 9),
        ).pack(padx=10, pady=(0, 2), anchor=tk.W)

        text_editor = scrolledtext.ScrolledText(
            dialog,
            bg=c["bg_input"], fg=c["text_normal"],
            font=("Courier New", 9), wrap=tk.WORD,
            relief=tk.FLAT,
        )
        text_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        def save():
            name = name_entry.get().strip() or "Pasted Text"
            text = text_editor.get("1.0", tk.END).strip()
            if not text:
                return
            try:
                item = self.manager.add_text(text, name)
                self.add_system_message(f"[OK] Added context: {item['name']}")
                self._refresh_list()
                dialog.destroy()
            except Exception as e:
                self.add_system_message(f"[WARN] Failed to save text: {e}")

        tk.Button(
            dialog, text="Save", command=save,
            bg=c["accent_green"], fg=c["bg_main"],
            font=("Courier New", 10, "bold"), relief=tk.FLAT,
        ).pack(fill=tk.X, padx=10, pady=8)

        dialog.show()

    def _view_item(self, item_id: str):
        """View the full text content of an item."""
        item = self.manager.get_item(item_id)
        if not item:
            return

        viewer = InvisibleTopLevel(self.window)
        viewer.title(f"View: {item['name']}")
        viewer.geometry("550x450")
        viewer.configure(bg=COLORS["bg_main"])
        c = COLORS
        self._add_dialog_header(
            viewer,
            f"📄 {item['name']} ({item.get('type', 'txt').upper()})",
        )

        text_display = scrolledtext.ScrolledText(
            viewer,
            bg=c["bg_input"], fg=c["text_normal"],
            font=("Courier New", 9), wrap=tk.WORD,
            relief=tk.FLAT, state=tk.NORMAL,
        )
        text_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        text_display.insert("1.0", item.get("text_content", "(empty)"))
        text_display.config(state=tk.DISABLED)

        viewer.show()

    def _edit_item(self, item_id: str):
        """Edit the text content of an item."""
        item = self.manager.get_item(item_id)
        if not item:
            return

        editor_win = InvisibleTopLevel(self.window)
        editor_win.title(f"Edit: {item['name']}")
        editor_win.geometry("550x450")
        editor_win.configure(bg=COLORS["bg_main"])
        c = COLORS
        self._add_dialog_header(editor_win, f"✏ Editing: {item['name']}")

        text_editor = scrolledtext.ScrolledText(
            editor_win,
            bg=c["bg_input"], fg=c["text_normal"],
            font=("Courier New", 9), wrap=tk.WORD,
            relief=tk.FLAT,
        )
        text_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        text_editor.insert("1.0", item.get("text_content", ""))

        def save():
            new_text = text_editor.get("1.0", tk.END).strip()
            self.manager.update_item_text(item_id, new_text)
            self.add_system_message(f"[OK] Updated: {item['name']}")
            self._refresh_list()
            editor_win.destroy()

        tk.Button(
            editor_win, text="Save Changes", command=save,
            bg=c["accent_green"], fg=c["bg_main"],
            font=("Courier New", 10, "bold"), relief=tk.FLAT,
        ).pack(fill=tk.X, padx=10, pady=8)

        editor_win.show()

    def _rename_item(self, item_id: str):
        """Rename a context item."""
        item = self.manager.get_item(item_id)
        if not item:
            return

        rename_win = InvisibleTopLevel(self.window)
        rename_win.title("Rename")
        rename_win.geometry("350x120")
        rename_win.configure(bg=COLORS["bg_main"])
        c = COLORS
        self._add_dialog_header(rename_win, "Rename")

        tk.Label(
            rename_win, text="New name:",
            fg=c["text_normal"], bg=c["bg_main"],
            font=("Courier New", 9),
        ).pack(padx=10, pady=(10, 2), anchor=tk.W)

        name_entry = tk.Entry(
            rename_win,
            bg=c["bg_input"], fg=c["text_normal"],
            font=("Courier New", 9), relief=tk.FLAT,
            insertbackground=c["accent_green"],
        )
        name_entry.pack(fill=tk.X, padx=10, pady=(0, 8))
        name_entry.insert(0, item["name"])
        name_entry.select_range(0, tk.END)

        def save():
            new_name = name_entry.get().strip()
            if new_name:
                self.manager.rename_item(item_id, new_name)
                self.add_system_message(f"[OK] Renamed to: {new_name}")
                self._refresh_list()
            rename_win.destroy()

        name_entry.bind("<Return>", lambda e: save())

        tk.Button(
            rename_win, text="Save", command=save,
            bg=c["accent_green"], fg=c["bg_main"],
            font=("Courier New", 9, "bold"), relief=tk.FLAT,
        ).pack(fill=tk.X, padx=10, pady=4)

        rename_win.show()

    def _delete_item(self, item_id: str):
        """Delete a context item with confirmation."""
        item = self.manager.get_item(item_id)
        if not item:
            return

        confirm_win = InvisibleTopLevel(self.window)
        confirm_win.title("Confirm Delete")
        confirm_win.geometry("350x120")
        confirm_win.configure(bg=COLORS["bg_main"])
        c = COLORS
        self._add_dialog_header(confirm_win, "Confirm Delete")

        tk.Label(
            confirm_win,
            text=f"Delete \"{item['name']}\"?",
            fg=c["error_red"], bg=c["bg_main"],
            font=("Courier New", 10, "bold"),
        ).pack(pady=(15, 5))

        btn_frame = tk.Frame(confirm_win, bg=c["bg_main"])
        btn_frame.pack(pady=10)

        def confirm():
            self.manager.delete_item(item_id)
            self.add_system_message(f"[OK] Deleted: {item['name']}")
            self._refresh_list()
            confirm_win.destroy()

        tk.Button(
            btn_frame, text="Delete", command=confirm,
            bg=c["error_red"], fg="#ffffff",
            font=("Courier New", 9, "bold"), relief=tk.FLAT,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="Cancel", command=confirm_win.destroy,
            bg=c["bg_header"], fg=c["text_normal"],
            font=("Courier New", 9), relief=tk.FLAT,
        ).pack(side=tk.LEFT, padx=5)

        confirm_win.show()

    # ------------------------------------------------------------------
    # Window Movement
    # ------------------------------------------------------------------
    def _start_move(self, event):
        self.window.x = event.x
        self.window.y = event.y

    def _do_move(self, event):
        x = self.window.winfo_x() - self.window.x + event.x
        y = self.window.winfo_y() - self.window.y + event.y
        self.window.geometry(f"+{x}+{y}")

