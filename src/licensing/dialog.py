"""License required UI — tkinter, matches overlay dark theme."""

import tkinter as tk
import webbrowser
from tkinter import scrolledtext

from src.licensing.config import get_license_settings
from src.licensing.manager import (
    activate_license,
    license_bypass_enabled,
    license_summary,
    load_license,
    verify_license_offline,
)
from src.ui.styles.themes import COLORS, set_active_theme
from src.ui.close_button import create_header_close_button


class LicenseGate:
    """Modal license gate on the application root window."""

    def __init__(self, root: tk.Tk, config):
        self.root = root
        self.config = config
        self._success = False
        self._settings = get_license_settings(config)
        set_active_theme("dark")

    def run(self) -> bool:
        if license_bypass_enabled():
            return True

        token = load_license(self.config)
        if verify_license_offline(token, self.config).ok:
            return True

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        self.root.mainloop()
        return self._success

    def _build_ui(self):
        self.root.title("License Required")
        self.root.configure(bg=COLORS["bg_main"])
        self.root.resizable(False, False)

        w, h = 520, 420
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        header = tk.Frame(self.root, bg=COLORS["bg_header"], height=48)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(
            header,
            text="● PREMIUM LICENSE REQUIRED",
            font=("Courier New", 11, "bold"),
            fg=COLORS["accent_green"],
            bg=COLORS["bg_header"],
        ).pack(side=tk.LEFT, padx=16, pady=12)
        create_header_close_button(
            header, self._on_quit,
        ).pack(side=tk.RIGHT, padx=(4, 8), pady=8)

        body = tk.Frame(self.root, bg=COLORS["bg_main"], padx=20, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            body,
            text="Activate once online. The app verifies your license offline afterward.",
            font=("Courier New", 9),
            fg=COLORS["text_normal"],
            bg=COLORS["bg_main"],
            wraplength=460,
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        tk.Label(
            body,
            text="Paste license key (raw JWT from admin):",
            font=("Courier New", 9),
            fg=COLORS["text_dim"],
            bg=COLORS["bg_main"],
        ).pack(anchor=tk.W, pady=(14, 4))

        self.key_text = scrolledtext.ScrolledText(
            body,
            height=6,
            font=("Courier New", 9),
            bg=COLORS["bg_input"],
            fg=COLORS["text_normal"],
            insertbackground=COLORS["accent_green"],
            relief=tk.FLAT,
            wrap=tk.WORD,
        )
        self.key_text.pack(fill=tk.BOTH, expand=True)

        btn_row = tk.Frame(body, bg=COLORS["bg_main"])
        btn_row.pack(fill=tk.X, pady=12)

        tk.Button(
            btn_row,
            text="Get License / Activate",
            font=("Courier New", 9, "bold"),
            fg=COLORS["bg_main"],
            bg=COLORS["accent_green"],
            activebackground=COLORS["accent_blue"],
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._open_get_license_url,
        ).pack(side=tk.LEFT)

        tk.Button(
            btn_row,
            text="Activate",
            font=("Courier New", 9, "bold"),
            fg=COLORS["bg_main"],
            bg=COLORS["accent_blue"],
            activebackground=COLORS["accent_green"],
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._on_activate,
        ).pack(side=tk.RIGHT)

        self.status_label = tk.Label(
            body,
            text="",
            font=("Courier New", 8),
            fg=COLORS["text_dim"],
            bg=COLORS["bg_main"],
            wraplength=460,
            justify=tk.LEFT,
        )
        self.status_label.pack(anchor=tk.W)

        existing = license_summary(self.config)
        if existing and "No license" not in existing and "Invalid" not in existing:
            self._set_status(existing, error=False)

    def _set_status(self, message: str, error: bool = True):
        self.status_label.config(
            text=message,
            fg=COLORS["error_red"] if error else COLORS["accent_green"],
        )

    def _open_get_license_url(self):
        url = self._settings.get("get_license_url") or ""
        if url:
            webbrowser.open(url)
        else:
            self._set_status("get_license_url is not set in config.ini [LICENSE].")

    def _on_activate(self):
        raw = self.key_text.get("1.0", tk.END).strip()
        if not raw:
            self._set_status("Paste your license key first.")
            return

        self._set_status("Activating…", error=False)
        self.root.update_idletasks()

        try:
            activate_license(raw, self.config)
        except ValueError as exc:
            self._set_status(str(exc))
            return

        self._set_status(license_summary(self.config), error=False)
        self._success = True
        self.root.after(400, self._finish)

    def _finish(self):
        for child in self.root.winfo_children():
            child.destroy()
        self.root.quit()

    def _on_quit(self):
        self._success = False
        self.root.quit()


def run_license_gate(root: tk.Tk, config) -> bool:
    """Block until license is valid or user closes the window."""
    return LicenseGate(root, config).run()
