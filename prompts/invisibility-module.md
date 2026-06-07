# Invisibility Module — Architecture & Hardening Guide

**Scope:** `src/utils/win32_invisibility.py`, `src/ui/app.py`, related overlay code  
**Last Updated:** 2026-06-07

---

## 1. Architecture Overview

The overlay application uses a **two-layer invisibility strategy** on Windows:

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **DWM Display Affinity** | `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` | Removes window content from screen captures |
| **Window Style Hardening** | `WS_EX_TOOLWINDOW` + `WS_EX_NOACTIVATE` | Hides from taskbar; reduces accessibility exposure |

Tkinter is used for the UI layer, but **all capture-sensitive surfaces** are wrapped so that Win32 invisibility is applied before the window becomes visible.

### 1.1 Key Abstractions

```
InvisibleTopLevel          → base capture-excluded popup
  └── InvisibleOverlayPanel  → borderless module panel (Meeting, Context)
  └── InvisibleContextMenu   → right-click menu (replaces native tk.Menu)
  └── InvisibleModelDropdown → selector dropdown
```

### 1.2 Data Flow

```
Tkinter widget created
  ↓
window.withdraw()  (keep invisible)
  ↓
assign_ephemeral_window_title()  (randomize OS title)
  ↓
hide_window_from_taskbar()       (WS_EX_TOOLWINDOW)
  ↓
apply_capture_exclusion()        (WDA_EXCLUDEFROMCAPTURE)
  ↓
window.deiconify()               (now safe to show)
```

---

## 2. Window Lifecycle

### 2.1 Construction

```python
root = tk.Tk()
assign_ephemeral_window_title(root, hint="overlay")
apply_overlay_window_config(root, opacity=0.94)
```

The **Win32 title is randomized** immediately. The visible UI header (e.g. "● AI OVERLAY") is rendered inside Tkinter, not via `SetWindowText()`.

### 2.2 Invisibility Application

```python
hide_window_from_taskbar(root)
apply_capture_exclusion(root, title=None, verbose=False)
```

- `title=None` prevents `FindWindowW()` by title — a detection vector.
- `verbose=False` suppresses console output.

### 2.3 Maintenance Polling

Capture exclusion can be lost during:
- Window restore from minimize
- DWM restart
- Graphics driver reset

The app re-applies exclusion:
- Immediately on `<Map>` and `<FocusIn>` events
- Every 5 seconds via `after()` polling (skipped when hidden)

### 2.4 Destruction

```python
def _on_window_close(self):
    # Unregister global hotkeys
    for remover in self._hotkey_removers:
        remover()
    # Security: clear volatile screenshot queue
    clear_screenshot_queue()
    self.root.destroy()
```

---

## 3. Rendering Lifecycle

```
User presses Ctrl+Shift+S
  ↓
Overlay withdraws itself (hide before capture)
  ↓
PIL.ImageGrab.grab() — window is not visible
  ↓
JPEG compression + base64 encoding
  ↓
Overlay restored via present_overlay_window()
  ↓
Re-applies capture exclusion
```

The overlay **must** be hidden before capture, because `ImageGrab.grab()` captures the entire desktop and would include the overlay if visible.

---

## 4. Security Considerations

### 4.1 Detection Vectors (Mitigated)

| Vector | Status | Mitigation |
|--------|--------|------------|
| `EnumWindows` | **Inherent** | Windows requires HWNDs to be enumerable; no mitigation possible |
| `GetWindowText` | **Mitigated** | Title randomized; reveals no app identity |
| `GetClassName` | **Inherent** | Tkinter uses `"Tk"` / `"TkChild"` classes |
| Process name | **Inherent** | `python.exe` or build executable name is visible in Task Manager |
| `tk.Menu` context menus | **Mitigated** | Replaced with `InvisibleContextMenu` which inherits capture exclusion |

### 4.2 Information Leaks (Mitigated)

| Source | Before | After |
|--------|--------|-------|
| Console prints | Printed HWND values, titles | Gated behind `AI_OVERLAY_DEBUG=1` |
| Error messages | Raw stack traces to stderr | API keys redacted; no stderr in production |
| Window titles | Static "AI OVERLAY" | Ephemeral random titles |
| Storage permissions | Default user permissions | Best-effort owner-only (`0o600`) |

### 4.3 API Key Protection

The error handler (`src/utils/error_handler.py`) redacts common API key patterns before displaying or logging:

- `sk-…` (OpenAI format)
- `sk-proj-…` (OpenAI project keys)
- `sk-ant-…` (Anthropic format)
- Explicit env values for known key names

---

## 5. Known Limitations

These are **inherent to Windows** and cannot be fixed without kernel-level changes:

1. **Process Enumeration** — Any process with `PROCESS_QUERY_INFORMATION` can enumerate the process. The app will always appear in Task Manager.

2. **Window Handle Enumeration** — `EnumWindows` will always find the HWND. This is fundamental to Windows window management.

3. **Tkinter Class Name** — Windows created by Tkinter use the `"Tk"` Win32 class name. Changing this requires modifying Tcl/Tk internals.

4. **OS Version Requirement** — `WDA_EXCLUDEFROMCAPTURE` requires Windows 10 Build 2004+. Older systems fall back to `WDA_MONITOR` (shows black rectangle in capture).

5. **Window-Specific Capture** — Some capture APIs that target a specific window (not the desktop) may still capture the overlay depending on the method used.

---

## 6. Hardening Changes (2026-06-07)

### 6.1 Window Title Randomization

```python
assign_ephemeral_window_title(window, hint="overlay")
# Produces: "overlay-a3f2c1b8d9e4f5a6"
```

### 6.2 Native Context Menu Replacement

Replaced `tk.Menu` with `InvisibleContextMenu`:

```python
items = [
    ("Preview", lambda: self._preview_screenshot(idx), True),
    ("✕ Remove", lambda: self._remove_screenshot(idx), True),
]
menu = InvisibleContextMenu(self.root, items)
menu.open_at(event.x_root, event.y_root)
```

### 6.3 Debug Output Gating

All `print()` statements in the invisibility module are replaced with `_debug_print()` which only emits when `AI_OVERLAY_DEBUG=1` is set.

### 6.4 Error Message Sanitization

API key patterns are redacted from exception traces before display:

```python
text = pat.sub(lambda m: m.group(1)[:4] + "[REDACTED]", text)
```

### 6.5 ctypes Signature Hardening

All `user32` function prototypes now use proper `wintypes` and `ctypes` argtypes/restypes to prevent handle truncation on 64-bit Windows.

### 6.6 Storage Permission Hardening

All persisted files (chat history, preferences, screenshot queue) get best-effort `0o600` permissions via `_set_restrictive_permissions()`.

### 6.7 Invisibility Polling Optimization

- Interval increased from 3s → 5s
- Skipped entirely when overlay is withdrawn (not visible)

---

## 7. Related Files

| File | Role |
|------|------|
| `src/utils/win32_invisibility.py` | Core Win32 invisibility abstractions |
| `src/ui/app.py` | Main overlay; window lifecycle |
| `src/utils/error_handler.py` | Exception interception + key redaction |
| `src/services/storage.py` | Persistence + file permissions |
| `src/services/capture.py` | Screenshot capture (hides overlay first) |

---

## 8. Testing Checklist

- [ ] Window invisible in OBS Studio (Display Capture)
- [ ] Window invisible in Windows Game Bar
- [ ] Window invisible in Google Meet screen share
- [ ] Window invisible in Zoom screen share
- [ ] Right-click context menu is capture-excluded
- [ ] Model dropdown is capture-excluded
- [ ] Hotkeys functional when focus is on another app
- [ ] No API keys appear in error messages
- [ ] Screenshot queue cleared on clean exit
- [ ] App closes without orphan processes
