import ctypes
import os
import tkinter as tk
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
    """Get HWND for a top-level window by title."""
    try:
        hwnd = _user32.FindWindowW(None, window_title)
        if hwnd and hwnd > 0:
            return hwnd
        return None
    except Exception as e:
        print(f"Warning: Error getting window handle: {e}")
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
        refresh_cursor_policy(self)

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


