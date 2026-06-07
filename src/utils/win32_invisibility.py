import ctypes
import os
import secrets
import tkinter as tk
from ctypes import wintypes

from src.ui.styles.themes import COLORS
from src.ui.cursor import refresh_cursor_policy

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
WS_EX_NOACTIVATE = 0x08000000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
HWND_TOPMOST = -1

# Debug output is a detection vector; keep it opt-in.
_DEBUG_ENV = "AI_OVERLAY_DEBUG"


def _debug_enabled() -> bool:
    return (os.environ.get(_DEBUG_ENV) or "").strip() not in ("", "0", "false", "False")


def _debug_print(msg: str):
    if _debug_enabled():
        print(msg)


# Use WinDLL with use_last_error=True so ctypes.get_last_error() is meaningful.
_user32 = ctypes.WinDLL("user32", use_last_error=True)

# Typedefs
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
LONG_PTR = ctypes.c_ssize_t

# Function prototypes (avoid handle truncation on 64-bit)
_user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
_user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
_user32.GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowDisplayAffinity.restype = wintypes.BOOL

_user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
_user32.EnumWindows.restype = wintypes.BOOL
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD

_user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
_user32.GetAncestor.restype = wintypes.HWND
_user32.GetParent.argtypes = [wintypes.HWND]
_user32.GetParent.restype = wintypes.HWND

_user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
_user32.FindWindowW.restype = wintypes.HWND

_user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.GetWindowLongPtrW.restype = LONG_PTR
_user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
_user32.SetWindowLongPtrW.restype = LONG_PTR

_user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.GetWindowLongW.restype = wintypes.LONG
_user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
_user32.SetWindowLongW.restype = wintypes.LONG

_user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
_user32.SetWindowPos.restype = wintypes.BOOL


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
    """Collect every HWND tied to a tkinter window (outer frame + inner client).

    IMPORTANT: Do not infer title automatically. Window titles are a detection vector.
    If a caller *explicitly* passes a title, we may use it as an additional hint.
    """
    hwnds = set()

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
        try:
            outer = _user32.FindWindowW(None, title)
            if outer:
                hwnds.add(outer)
        except Exception:
            pass

    return hwnds


def collect_process_hwnds():
    """All top-level HWNDs owned by this process."""
    current_pid = os.getpid()
    hwnds = set()

    def enum_proc(hwnd, _lparam):
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if int(pid.value) == int(current_pid):
            hwnds.add(hwnd)
        return True

    cb = WNDENUMPROC(enum_proc)
    _user32.EnumWindows(cb, 0)
    return hwnds


def apply_capture_exclusion(window=None, title=None, verbose=False, process_wide=True):
    """Apply WDA_EXCLUDEFROMCAPTURE to every related HWND.

    Uses DWM display affinity only — do NOT combine with WS_EX_NOREDIRECTIONBITMAP,
    which opts out of DWM and prevents capture exclusion from working.

    process_wide=False is used for popups (Settings, model list) so they are not
    affected later by delayed process-wide passes on the main overlay.
    """
    hwnds = set()
    if window is not None:
        hwnds.update(collect_tk_window_hwnds(window, title))
    if title:
        outer = _user32.FindWindowW(None, title)
        if outer:
            hwnds.add(outer)
    if process_wide:
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
            print(f"  [OK] Capture exclusion applied to {protected} window(s), {verified} verified")
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
    """Hide a window from the Windows taskbar and make it strictly non-activating."""
    try:
        window.attributes("-toolwindow", True)
    except tk.TclError:
        pass

    try:
        window.update_idletasks()
        for hwnd in collect_tk_window_hwnds(window):
            style = _get_window_exstyle(hwnd)
            _set_window_exstyle(hwnd, (style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE) & ~WS_EX_APPWINDOW)
    except Exception as e:
        _debug_print(f"[invisibility] could not hide window from taskbar: {e}")


def make_window_invisible_to_capture(hwnd):
    """Apply capture exclusion to a single HWND."""
    return _apply_capture_exclusion_to_hwnd(hwnd)


def get_window_handle(window_title):
    """Get HWND for a top-level window by title.

    NOTE: Using window titles is a detection vector. Prefer hwnd collection from Tk.
    """
    try:
        hwnd = _user32.FindWindowW(None, window_title)
        if hwnd and hwnd > 0:
            return hwnd
        return None
    except Exception as e:
        _debug_print(f"[invisibility] error getting window handle: {e}")
        return None


def find_window_by_class(class_name):
    """Get HWND for a top-level window by Win32 class name (e.g. 'Tk')."""
    try:
        hwnd = _user32.FindWindowW(class_name, None)
        if hwnd and hwnd > 0:
            return hwnd
        return None
    except Exception:
        return None


def get_tkinter_hwnd(window):
    """Get the primary Win32 HWND for a tkinter widget or window."""
    hwnds = collect_tk_window_hwnds(window)
    if not hwnds:
        return None
    # Prefer the top-level ancestor if present.
    return max(hwnds)


def apply_invisibility_to_tkinter_window(window):
    """Apply capture exclusion and hide from taskbar for a tkinter window."""
    try:
        window.update_idletasks()
        window.update()
        hide_window_from_taskbar(window)
        return apply_capture_exclusion(window, title=None, verbose=False, process_wide=False)
    except Exception as e:
        _debug_print(f"[invisibility] error applying invisibility to window: {e}")
        return False


def apply_overlay_window_config(window, opacity=None):
    """Apply borderless overlay chrome shared by fixed panels (main overlay, modules)."""
    try:
        window.overrideredirect(True)
    except tk.TclError:
        pass
    try:
        window.attributes("-toolwindow", True)
    except tk.TclError:
        pass
    try:
        window.wm_attributes("-topmost", True)
        if opacity is not None:
            window.wm_attributes("-alpha", opacity)
    except tk.TclError:
        pass


def raise_without_activate(window):
    """Raise z-order without activating — keeps fullscreen apps focused."""
    try:
        window.update_idletasks()
        title = window.title() if hasattr(window, "title") else None
        for hwnd in collect_tk_window_hwnds(window, title):
            _user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0,
                0,
                0,
                0,
                SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE,
            )
    except Exception:
        pass


def present_overlay_window(window):
    """Show or re-raise any overlay/toplevel without taskbar flash or focus steal."""
    try:
        window.update_idletasks()
        window.update()
        apply_invisibility_to_tkinter_window(window)
        window.deiconify()
        window.attributes("-topmost", True)
        raise_without_activate(window)
        refresh_cursor_policy(window)
    except tk.TclError:
        pass


def generate_ephemeral_window_title(hint: str = "overlay") -> str:
    """Generate a low-information, hard-to-fingerprint window title."""
    hint = (hint or "overlay").strip().lower()[:16]
    return f"{hint}-{secrets.token_hex(8)}"


def assign_ephemeral_window_title(window, hint: str = "overlay"):
    """Best-effort: overwrite the OS-level window title.

    The overlay has its own in-UI header labels; the Win32 title is unnecessary and
    is a detection vector via GetWindowText().
    """
    try:
        window.title(generate_ephemeral_window_title(hint))
    except Exception:
        pass


class InvisibleTopLevel(tk.Toplevel):
    """Toplevel window hidden until invisibility is applied — no visible flash."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._invisibility_applied = False
        # Title is a detection vector; keep it random.
        assign_ephemeral_window_title(self, hint="panel")
        self.withdraw()
        self.bind("<Map>", self._on_map, add="+")

    def show(self):
        """Apply capture exclusion while hidden, then show (same flow as model dropdown)."""
        self.update_idletasks()
        self.update()
        self._apply_invisibility()
        present_overlay_window(self)

    def _on_map(self, event=None):
        if self._invisibility_applied:
            return
        self._apply_invisibility()

    def _apply_invisibility(self):
        if self._invisibility_applied:
            return
        # Ensure a randomized title even if caller set a descriptive one.
        assign_ephemeral_window_title(self, hint="panel")
        apply_invisibility_to_tkinter_window(self)
        self._invisibility_applied = True


class InvisibleOverlayPanel(InvisibleTopLevel):
    """Borderless fixed panel — Personal Context, Meeting Assistant, etc."""

    def __init__(self, parent, *args, opacity=None, **kwargs):
        super().__init__(parent, *args, **kwargs)
        apply_overlay_window_config(self, opacity=opacity)


class InvisibleContextMenu(InvisibleTopLevel):
    """Simple right-click menu implemented as a capture-excluded toplevel.

    Avoids native tk.Menu which creates a separate OS window that does NOT inherit
    display affinity / capture exclusion reliably.
    """

    def __init__(self, parent, items, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        apply_overlay_window_config(self)
        self.configure(bg=COLORS["bg_input"])
        self._items = list(items)
        self._outside_bind = None

        frame = tk.Frame(
            self,
            bg=COLORS["bg_input"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        frame.pack(fill=tk.BOTH, expand=True)

        for label, callback, enabled in self._items:
            fg = COLORS["text_normal"] if enabled else COLORS["text_dim"]
            row = tk.Label(
                frame,
                text=label,
                bg=COLORS["bg_input"],
                fg=fg,
                font=("Courier New", 8),
                anchor="w",
                padx=10,
                pady=5,
            )
            row.pack(fill=tk.X)

            if enabled:
                row.bind("<Enter>", lambda _e, r=row: r.config(
                    bg=COLORS["accent_green"], fg=COLORS["bg_main"],
                ))
                row.bind("<Leave>", lambda _e, r=row: r.config(
                    bg=COLORS["bg_input"], fg=COLORS["text_normal"],
                ))
                row.bind("<Button-1>", lambda _e, fn=callback: self._invoke(fn))

    def _invoke(self, fn):
        try:
            fn()
        finally:
            self.close()

    def open_at(self, x_root: int, y_root: int):
        self.update_idletasks()
        width = 220
        height = max(1, len(self._items)) * 28 + 2
        self.geometry(f"{width}x{height}+{int(x_root)}+{int(y_root)}")
        self.show()
        refresh_cursor_policy(self)

        root = self.winfo_toplevel()

        def dismiss_if_outside(event):
            if not self.winfo_exists():
                return
            px, py = self.winfo_rootx(), self.winfo_rooty()
            pw, ph = self.winfo_width(), self.winfo_height()
            x, y = event.x_root, event.y_root
            if not (px <= x <= px + pw and py <= y <= py + ph):
                self.close()

        self._outside_bind = root.bind("<Button-1>", dismiss_if_outside, add="+")

    def close(self):
        if self._outside_bind:
            try:
                self.winfo_toplevel().unbind("<Button-1>", self._outside_bind)
            except Exception:
                pass
            self._outside_bind = None
        try:
            self.destroy()
        except Exception:
            pass


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
        apply_overlay_window_config(self._popup)
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
        refresh_cursor_policy(self._popup)

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


